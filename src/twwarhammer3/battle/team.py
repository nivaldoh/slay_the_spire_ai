"""Two independent members sharing one army and one mailbox, each owning declared units.

A member is declared by one unit type (exactly one unit of it), a tuple of types (one or
more units) or None (every unit nobody else declares); a new friendly unit joins the member
declaring its type or the one owning the rest, else the episode ends. Each sees ``project``:
its own units, its teammate's as allies and the public battle state, never the teammate's
feedback. It may give any order to its own units and aim abilities at its teammate's; only
the named army owner gives army-level orders.
Members have bounded decide/close calls and short acknowledge/metadata callbacks; this
adapter is not a sandbox. One whole member batch is selected per request; the play loop
remains the only mailbox writer. A failed member call follows the single controller's
rule: no valid reply or a provider error is a forfeit and the member is asked again; a key,
credit or budget stop or any other exception ends the episode. At cleanup a forfeit is
only discarded, a stop still ends the job, and a member bug is a policy failure even after
the battle ended (a single controller's call that straddles the end keeps the result).
``ModelTeam`` (the policy ``team_llm_rules``) has two model members sharing the job's ledger.
"""
import hashlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait
from copy import deepcopy
from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path
from threading import Event
from time import time

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError
from gameai.provenance import sha256
from twwarhammer3.battle import llm
from twwarhammer3.protocol import (
    IllegalActionError,
    PolicyFailure,
    ProtocolError,
    refused,
    validate_orders,
)

INPUT_VERSION = "team-v3"
SWORD = "wh_main_emp_inf_swordsmen"
KNIGHT = "wh_main_emp_cav_empire_knights"
CLOSE_WAIT_S = 30  # cleanup waits this long for a running member call, then abandons it
UNIT_FIELDS = ("id", "type", "alliance", "class", "x", "z", "bearing", "men", "men0", "hp",
               "barrier", "can_fly", "flying", "ammo", "ammo0", "range", "speed", "fatigue",
               "morale", "flight", "width", "attack_mode", "behaviours", "abilities",
               "command_queue", "navigation", "dest", "state", "error")
# A teammate's unit shows what an enemy's shows, its condition (owner, 2026-10-27) and a
# visible target: never its orders, queue or navigation.
ALLY_FIELDS = ("id", "type", "class", "alliance", "x", "z", "bearing", "men", "men0", "hp",
               "barrier", "can_fly", "flying", "range", "speed", "state", "ammo", "ammo0",
               "fatigue", "morale")
ARMY_MODE = ("slots", "reinforcements", "spawn_zones", "supplies")  # the army owner's
# The model team (``team_llm_rules``): the Knights, and every other unit with the army orders.
PARTITION = {"cavalry": (KNIGHT,), "line": None}
ARMY_OWNER = "line"
TEAM_NOTE = ("Team: a teammate model commands the allied units below at the same time. You"
             " order only Your units; Ally abilities may target allied units. You see allied units'"
             " condition, state and visible targets, not the teammate's orders, feedback or"
             " notes.")


class TeamHarnessError(ProtocolError):
    """A partition or dispatcher fault, distinct from a member's bad decision."""


def project(observation, owned, *, army=False):
    """Explicit public contract, including only currently visible target identities.

    ``owned`` (a set of unit ids) is ``friendly``, the other friendly units are ``allies``;
    ``army`` adds the army's abilities and the purchase parts of ``mode``."""
    def fields(value, keys):
        return {key: deepcopy(value[key]) for key in keys if key in value}

    visible = {unit["id"] for unit in observation.get("enemy", [])}

    def unit(row, keys=UNIT_FIELDS):
        result = fields(row, keys)
        if row.get("target") in visible:
            result["target"] = row["target"]
        return result

    result = fields(observation, ("schema", "battle", "seq", "phase", "time_ms", "speed",
                                  "remaining_ms", "enemy_roster", "magic"))
    result["input_version"] = INPUT_VERSION
    result["friendly"] = [unit(row) for row in observation["friendly"] if row["id"] in owned]
    result["allies"] = [unit(row, ALLY_FIELDS) for row in observation["friendly"]
                        if row["id"] not in owned]
    result["enemy"] = [unit(row) for row in observation.get("enemy", [])]
    mode = observation.get("mode") or {}
    result["mode"] = fields(mode, [key for key in mode if army or key not in ARMY_MODE])
    if army and "army" in observation:
        result["army"] = deepcopy(observation["army"])
    if observation.get("terrain"):
        terrain = observation["terrain"]
        result["terrain"] = fields(terrain, ("x0", "z0", "cell_m", "rows", "sample_width_m",
                                             "sampled_ms"))
        result["terrain"]["bounds"] = fields(terrain.get("bounds") or {},
                                              ("min_x", "max_x", "min_z", "max_z"))
    return result


def _types(kinds):
    return (kinds,) if isinstance(kinds, str) else tuple(kinds or ())


@dataclass
class Member:
    kinds: object  # a unit type, a tuple of types, or None for every undeclared unit
    policy: object
    units: frozenset = frozenset()
    future: object = None
    call: dict | None = None
    ready: dict | None = None
    count: int = 0
    decisions: int = 0
    local_refusals: int = 0
    running_at_close: bool = False  # its call outlived cleanup: cost and count left the record

    @property
    def unit(self):
        """The partition record: a one-type member's unit id, else its sorted unit ids."""
        return next(iter(self.units)) if isinstance(self.kinds, str) else sorted(self.units)


class TeamPolicy:
    """Units partitioned by declared type; oldest completed batch first, no teammate barrier."""

    timing = "asynchronous"

    def __init__(self, members, *, stop=None, max_age_ms=5000, army_owner=None, executor=None,
                 clock=time):  # play.py's clock; WSL's monotonic clock drifts from it
        declared = [kind for kinds, _ in members.values() for kind in _types(kinds)]
        rest = [name for name, (kinds, _) in members.items() if kinds is None]
        if (len(members) != 2 or len(declared) != len(set(declared)) or len(rest) > 1
                or army_owner not in (None, *members)):
            raise TeamHarnessError("a team needs two members with distinct unit types,"
                                   " at most one of them owning the rest")
        self.members = {name: Member(kinds, policy) for name, (kinds, policy) in members.items()}
        self.declared = set(declared)
        self.stop = stop if stop is not None else Event()
        self.pool = executor if executor is not None else ThreadPoolExecutor(max_workers=2)
        self.clock, self.max_age_ms, self.army_owner = clock, max_age_ms, army_owner
        self.battle = self.selected = None
        self.events = []
        self.closed = False
        self.last_selected = None
        self.behavior = {"type": "team", "member": None}
        self.delays_ms, self.think_s = [], []
        self.card = {"input_version": INPUT_VERSION, "members": {
            name: {"unit_types": kinds,
                   "class": f"{type(policy).__module__}:{type(policy).__name__}"}
            for name, (kinds, policy) in members.items()},
            "actions": "every order for its own units; army orders only for army_owner",
            "army_owner": army_owner, "max_age_ms": max_age_ms, "close_wait_s": CLOSE_WAIT_S,
            "batching": "one member per request",
            "partition": "declared unit types; a None member owns the rest", "paid_calls": False}

    def _event(self, event, name=None, **fields):
        call = self.members[name].call if name else None
        self.events.append({"event": event, "member": name,
                            "decision": call["decision"] if call else None, **fields})

    def drain_events(self):
        events, self.events = self.events, []
        return events

    def drain_exchanges(self):
        """Each member's model exchanges, tagged with the member."""
        for name, member in self.members.items():
            api = getattr(member.policy, "api", None)
            if hasattr(api, "drain_exchanges"):
                for exchange in api.drain_exchanges():
                    yield {**exchange, "member": name}

    def _totals(self, member):
        # A copy: a call abandoned at cleanup may still add to the member's totals.
        return Counter(getattr(member.policy, "totals", {}))

    @property
    def totals(self):
        """Both members' model call totals (calls, usd, tokens)."""
        total = Counter()
        for member in self.members.values():
            total.update(self._totals(member))
        return total

    def records(self):
        """The episode's decisions, engine delays and think times, counted per member batch."""
        rows = {}
        for name, member in self.members.items():
            totals = self._totals(member)  # one snapshot, so usd and calls agree
            rows[name] = {"decisions": member.decisions, "local_refusals": member.local_refusals,
                          "usd": totals["usd"], "calls": totals["calls"],
                          "running_at_close": member.running_at_close}
        return {"decisions": sum(row["decisions"] for row in rows.values()),
                "delays_ms": list(self.delays_ms), "think_s": list(self.think_s),
                "local_refusals": sum(row["local_refusals"] for row in rows.values()),
                "members": rows}

    def _fault(self, message):
        self._event("fault", error=message)
        raise TeamHarnessError(message)

    def _partition(self, observation):
        roster = observation.get("friendly")
        if not isinstance(roster, list) or any(
            not isinstance(row, dict) or not isinstance(row.get("id"), str)
            or not isinstance(row.get("type"), str) or "error" in row for row in roster
        ):
            self._fault("team received an incomplete friendly roster")
        if self.battle is not None and observation["battle"] != self.battle:
            self._fault("team received a different battle")
        if len({row["id"] for row in roster}) != len(roster):
            self._fault("team received duplicate friendly unit ids")
        owned = 0
        for name, member in self.members.items():
            units = frozenset(row["id"] for row in roster if (
                row["type"] in _types(member.kinds) if member.kinds is not None
                else row["type"] not in self.declared))
            if not units or (isinstance(member.kinds, str) and len(units) != 1) or (
                    self.battle is not None and not units >= member.units):
                self._fault(f"{name}: expected stable units of {member.kinds or 'the rest'}")
            owned += len(units)
            member.units = units
        if owned != len(roster):
            self._fault("team leaves friendly units unowned")
        if self.battle is None:
            self.battle = observation["battle"]
            self._event("partition", battle=self.battle, ownership={
                name: member.unit for name, member in self.members.items()})

    def _work(self, member, observation):
        from twwarhammer3.battle.play import policy_call  # play imports this module

        started = self.clock()
        orders = policy_call(member.policy, "decide", observation)
        behavior = member.policy.metadata()
        return {"orders": deepcopy(orders), "behavior": deepcopy(behavior),
                "started": started, "completed": self.clock(), "view": observation}

    def _collect(self, name, member):
        """Take a finished call. A forfeit (no valid reply, a provider error) clears it, so
        the member is asked again; a budget stop or any other failure is raised."""
        from twwarhammer3.battle.play import is_forfeit  # play imports this module

        try:
            member.ready = member.future.result()
        except Exception as exc:
            member.future = None
            forfeit = isinstance(exc, PolicyFailure) and is_forfeit(exc)
            if forfeit and self.closed:
                return  # after the episode a forfeit is only an unsent call: close() discards it
            self._event("failed", name, error=f"{type(exc).__name__}: {exc}",
                        **({"failure": exc.failure} if isinstance(exc, PolicyFailure) else {}))
            if isinstance(exc, BudgetExhausted):
                raise
            if forfeit:
                member.call = None
                return
            raise PolicyFailure(f"team {name}/{member.call['decision']}: {exc}",
                                failure={"member": name, "decision": member.call["decision"],
                                         "error_type": type(exc.__cause__ or exc).__name__}
                                ) from exc
        member.future = None
        self._event("completed", name, orders=member.ready["orders"],
                    started=member.ready["started"], completed=member.ready["completed"])
        self._member_events(name)

    def _member_events(self, name):
        drain = getattr(self.members[name].policy, "drain_events", None)
        if drain is not None:
            self.events.extend({"event": "member_event", "member": name, "record": record}
                               for record in drain())

    def _validate(self, member, observation):
        if (self.max_age_ms is not None
                and observation["time_ms"] - member.call["source_ms"] >= self.max_age_ms):
            raise IllegalActionError("member reply expired before dispatch")
        # The view the member decided on, as the single controller's batch is checked on its
        # basis: its units, and the army only for the army owner. The engine refuses each
        # order the battle has made stale since.
        validate_orders(member.ready["orders"], member.ready["view"])
        guard = getattr(member.policy, "dispatch_guard", None)
        if guard is not None:
            latest = project(observation, member.units,
                             army=member is self.members.get(self.army_owner))
            guard(member.ready["orders"], latest)

    def _feedback(self, name, ack, source):
        member = self.members[name]
        ready, call = member.ready, member.call
        latency = {"think_s": ready["completed"] - ready["started"],
                   "roundtrip_s": self.clock() - call["delivered"], "source": source}
        if source == "engine":
            latency["delay_ms"] = ack["applied_ms"] - call["source_ms"]
            if self.max_age_ms is not None:
                latency["transport_overage"] = latency["delay_ms"] >= self.max_age_ms
            self.delays_ms.append(latency["delay_ms"])
        member.decisions += 1
        member.local_refusals += source == "local"
        self.think_s.append(round(latency["think_s"], 3))
        self._event("feedback", name, source=source, ack=deepcopy(ack), latency=latency)
        member.ready = member.call = None
        try:
            member.policy.acknowledge(deepcopy(ack), dict(latency))
            self._member_events(name)
        except Exception as exc:
            raise PolicyFailure(f"team {name} acknowledge: {exc}",
                                failure={"member": name, "method": "acknowledge"}) from exc

    def decide(self, observation):
        if self.closed or self.selected is not None:
            self._fault("team decision while closed or awaiting selected-member feedback")
        self._partition(observation)
        self.behavior = {"type": "team", "member": None}
        for name, member in self.members.items():  # a stop ends the episode before any new call
            if member.future is not None and member.future.done():
                self._collect(name, member)
        for name, member in self.members.items():
            if member.ready is not None:
                try:
                    self._validate(member, observation)
                except IllegalActionError as exc:
                    self._feedback(name, refused(member.ready["orders"], str(exc)), "local")
            if member.call is None:
                view = project(observation, member.units, army=name == self.army_owner)
                if name != self.army_owner and all(u.get("men") == 0 for u in view["friendly"]):
                    continue  # its units are all destroyed: nothing to order, so no call
                member.count += 1
                member.call = {"decision": f"{name}-{member.count}", "source_seq": view["seq"],
                               "source_ms": view["time_ms"], "delivered": self.clock()}
                self._event("input", name, **member.call, observation=deepcopy(view))
                member.future = self.pool.submit(self._work, member, view)
        ready = [(name, member) for name, member in self.members.items()
                 if member.ready is not None]
        if not ready:
            return []
        name, member = min(ready, key=lambda pair: (pair[1].ready["completed"],
                                                   pair[0] == self.last_selected))
        self.selected = self.last_selected = name
        # Flat, so readers of a single controller's behaviour find the member's prompt.
        self.behavior = {**member.ready["behavior"], "member": name, **member.call}
        return deepcopy(member.ready["orders"])

    def acknowledge(self, ack, latency):
        if self.selected is None:  # an idle adapter poll, not a completed member call
            return
        self._feedback(self.selected, ack, "engine")
        self.selected = None

    def metadata(self):
        return deepcopy(self.behavior)

    def close(self):
        """Stop new work, wait up to CLOSE_WAIT_S for running calls, record what was never
        sent or acknowledged, and close every member whose call is not still running. A key,
        credit or budget stop from a collected call is raised after that."""
        self.closed = True
        self.stop.set()
        self.pool.shutdown(wait=False)
        started = self.clock()
        wait([member.future for member in self.members.values() if member.future is not None],
             timeout=CLOSE_WAIT_S)
        failures = []
        for name, member in self.members.items():
            running = member.running_at_close = (member.future is not None
                                                 and not member.future.done())
            if member.future is not None and not running:
                try:
                    self._collect(name, member)
                except (BudgetExhausted, PolicyFailure) as exc:
                    failures.append(exc)
            if member.call is not None:
                self._event("discarded", name, selected=name == self.selected,
                            reason="episode_closed", closed_at=self.clock(), running=running,
                            **({"waited_s": self.clock() - started} if running else {}))
            if running:
                continue  # its worker still uses it
            try:
                close = getattr(member.policy, "close", None)
                if close:
                    close()
                self._member_events(name)
            except Exception as exc:
                self._event("close_failed", name, error=str(exc))
                failures.append(exc)
        for exc in failures:
            if isinstance(exc, BudgetExhausted):
                raise exc
        if failures:
            raise PolicyFailure(f"team cleanup: {failures[0]}",
                                failure=getattr(failures[0], "failure", None)) from failures[0]


def condition(unit):
    """An allied unit's ammunition, fatigue and leadership, worded as for one's own units."""
    parts = [f"ammo {unit['ammo']}/{unit['ammo0']}"] if unit.get("ammo0") else []
    parts.append(unit.get("fatigue") or "fresh")
    if morale := unit.get("morale"):
        fraction = morale.get("fraction")
        amount = f"{fraction:.0%}" if fraction is not None else "unknown"
        parts.append(f"leadership {amount}; largest effect: {morale.get('effect') or 'unknown'}")
    return ", ".join(parts)


def team_section(view):
    """The prompt's last section for a model member: its teammate's units."""
    allies = [f"- {unit['id']} {llm.short_type(unit.get('type'))}: destroyed"
              if not unit.get("men") else f"- {llm.render_unit(unit, False)}, {condition(unit)}"
              for unit in view["allies"]]
    return f"\n\n{TEAM_NOTE}\nAllied units:\n" + ("\n".join(allies) or "- none")


class TeamLLM(llm.LLMPolicy):
    """The ``llm`` controller on a member's view, with its teammate's units appended."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.section = ""
        ask = self.api.ask
        # Per instance, so every attempt (retries too) sends exactly the recorded prompt.
        self.api.ask = lambda prompt, *rest: ask(prompt + self.section, *rest)

    def decide(self, observation):
        self.section = team_section(observation)
        return super().decide(observation)

    def metadata(self):
        metadata = dict(super().metadata())
        metadata["prompt"] += self.section
        metadata["prompt_sha256"] = hashlib.sha256(metadata["prompt"].encode()).hexdigest()
        return metadata


class ModelTeam(TeamPolicy):
    """Two model members on one army (``PARTITION``), one model, effort and ledger. Each
    plays the rules prompt on its own view; no age limit, like the single controller.

    Once cleanup starts no new model call or reply retry is sent, but a request already
    sent may still retry its transport (up to ``TRANSPORT_ATTEMPTS`` times), and the job
    process, so the next queued job, waits for it at exit. A call abandoned at cleanup
    reaches only the ledger (its cost and response id): its exchange, cost and call count
    reach no trace or result, whose member row says ``running_at_close``."""

    def __init__(self, model, effort, ledger, *, send, system_prompt, provider="openai",
                 **options):
        stop = Event()

        def guarded(body):  # no new call or reply retry once cleanup starts
            if stop.is_set():
                raise APIError("team closed; request not sent")
            return send(body)

        super().__init__({name: (kinds, TeamLLM(model, effort, ledger, send=guarded,
                                                provider=provider, system_prompt=system_prompt))
                          for name, kinds in PARTITION.items()},
                         stop=stop, max_age_ms=None, army_owner=ARMY_OWNER, **options)
        self.card.update(paid_calls=True, member_source_sha256=sha256(Path(llm.__file__)))


class _MoveOnce:
    """One 20 m forward move, with a cooperative first-decision delay."""

    def __init__(self, stop, delay):
        self.stop, self.delay = stop, delay
        self.moved = False

    def decide(self, observation):
        if self.moved:
            return []
        self.moved = True
        if self.stop.wait(self.delay):
            return []
        unit = observation["friendly"][0]
        angle = radians(unit["bearing"])
        return [{"unit": unit["id"], "type": "move", "x": unit["x"] + 20 * sin(angle),
                 "z": unit["z"] + 20 * cos(angle), "run": True}]

    def acknowledge(self, ack, latency):
        pass

    def metadata(self):
        return {"type": "move_once", "delay_s": self.delay, "distance_m": 20}


class DelayInfantry(TeamPolicy):
    """$0 diagnostic: infantry waits 3 s; cavalry moves independently."""

    def __init__(self):
        stop = Event()
        super().__init__({"infantry": (SWORD, _MoveOnce(stop, 3)),
                          "cavalry": (KNIGHT, _MoveOnce(stop, 0))}, stop=stop)


class DelayCavalry(TeamPolicy):
    """$0 diagnostic: cavalry waits 3 s; infantry moves independently."""

    def __init__(self):
        stop = Event()
        super().__init__({"infantry": (SWORD, _MoveOnce(stop, 0)),
                          "cavalry": (KNIGHT, _MoveOnce(stop, 3))}, stop=stop)
