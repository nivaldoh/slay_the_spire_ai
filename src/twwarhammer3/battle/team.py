"""Two independent, trusted scripted members sharing one army and one mailbox.

Members have bounded decide/close calls and short acknowledge/metadata callbacks.
This adapter is not a sandbox or a factory for paid model controllers. One whole
member batch is selected per request; the play loop remains the only mailbox writer.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from math import cos, radians, sin
from threading import Event
from time import monotonic

from twwarhammer3.protocol import IllegalActionError, PolicyFailure, ProtocolError, validate_orders

INPUT_VERSION = "script-team-v1"
SWORD = "wh_main_emp_inf_swordsmen"
KNIGHT = "wh_main_emp_cav_empire_knights"


class TeamHarnessError(ProtocolError):
    """A partition or dispatcher fault, distinct from a member's bad decision."""


def project(observation, owned):
    """Explicit public contract, including only currently visible target identities."""
    def fields(value, keys):
        return {key: deepcopy(value[key]) for key in keys if key in value}

    visible = {unit["id"] for unit in observation.get("enemy", [])}

    def unit(row):
        result = fields(row, ("id", "type", "x", "z", "bearing", "men", "state"))
        if row.get("target") in visible:
            result["target"] = row["target"]
        return result

    result = fields(observation, ("schema", "battle", "seq", "phase", "time_ms", "speed",
                                  "remaining_ms"))
    result["input_version"] = INPUT_VERSION
    result["friendly"] = [unit(row) for row in observation["friendly"] if row["id"] == owned]
    result["allies"] = [unit(row) for row in observation["friendly"] if row["id"] != owned]
    result["enemy"] = [unit(row) for row in observation.get("enemy", [])]
    result["mode"] = fields(observation.get("mode") or {}, ("type", "role", "scoring"))
    terrain = observation.get("terrain") or {}
    result["terrain"] = fields(terrain, ("x0", "z0", "cell_m", "rows", "sample_width_m",
                                         "sampled_ms"))
    result["terrain"]["bounds"] = fields(terrain.get("bounds") or {},
                                          ("min_x", "max_x", "min_z", "max_z"))
    return result


@dataclass
class Member:
    unit_type: str
    policy: object
    unit: str | None = None
    future: object = None
    call: dict | None = None
    ready: dict | None = None
    count: int = 0


class TeamPolicy:
    """One unit per member; oldest completed batch first, no teammate barrier."""

    timing = "asynchronous"

    def __init__(self, members, *, stop=None, max_age_ms=5000, executor=None, clock=monotonic):
        if len(members) != 2 or len({kind for kind, _ in members.values()}) != 2:
            raise TeamHarnessError("the scripted team needs two distinct unit types")
        self.members = {name: Member(kind, policy) for name, (kind, policy) in members.items()}
        self.stop = stop if stop is not None else Event()
        self.pool = executor if executor is not None else ThreadPoolExecutor(max_workers=2)
        self.clock, self.max_age_ms = clock, max_age_ms
        self.battle = self.selected = None
        self.events = []
        self.closed = False
        self.last_selected = None
        self.behavior = {"type": "team", "member": None}
        self.card = {"input_version": INPUT_VERSION, "members": {
            name: {"unit_type": kind, "class": f"{type(policy).__module__}:{type(policy).__name__}"}
            for name, (kind, policy) in members.items()}, "actions": ["move", "attack", "halt"],
            "max_age_ms": max_age_ms, "batching": "one member per request",
            "partition": "one unit of each declared type", "paid_calls": False}

    def _event(self, event, name=None, **fields):
        call = self.members[name].call if name else None
        self.events.append({"event": event, "member": name,
                            "decision": call["decision"] if call else None, **fields})

    def drain_events(self):
        events, self.events = self.events, []
        return events

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
        if len(roster) != 2 or len({row["id"] for row in roster}) != 2:
            self._fault("team requires exactly two distinct friendly units")
        for name, member in self.members.items():
            matches = [row["id"] for row in roster if row["type"] == member.unit_type]
            if len(matches) != 1 or (member.unit is not None and matches[0] != member.unit):
                self._fault(f"{name}: expected one stable {member.unit_type} unit")
        if self.battle is None:
            self.battle = observation["battle"]
            for name, member in self.members.items():
                member.unit = next(row["id"] for row in roster if row["type"] == member.unit_type)
            self._event("partition", battle=self.battle, ownership={
                name: member.unit for name, member in self.members.items()})

    def _work(self, member, observation):
        started = self.clock()
        orders = member.policy.decide(observation)
        behavior = member.policy.metadata()
        return {"orders": deepcopy(orders), "behavior": deepcopy(behavior),
                "started": started, "completed": self.clock()}

    def _collect(self, name, member):
        try:
            member.ready = member.future.result()
        except Exception as exc:
            self._event("failed", name, error=f"{type(exc).__name__}: {exc}")
            member.future = None
            raise PolicyFailure(f"team {name}/{member.call['decision']}: {exc}",
                                failure={"member": name, "decision": member.call["decision"],
                                         "error_type": type(exc).__name__}) from exc
        member.future = None
        self._event("completed", name, **member.ready)

    def _validate(self, name, member, observation):
        orders = member.ready["orders"]
        if observation["time_ms"] - member.call["source_ms"] >= self.max_age_ms:
            raise IllegalActionError("member reply expired before dispatch")
        if isinstance(orders, list):
            for order in orders:
                if isinstance(order, dict) and (
                    order.get("unit") != member.unit
                    or order.get("type") not in ("move", "attack", "halt")
                ):
                    raise IllegalActionError(f"{name} may only move, attack or halt {member.unit}")
        validate_orders(orders, project(observation, member.unit))

    def _feedback(self, name, ack, source):
        member = self.members[name]
        ready, call = member.ready, member.call
        latency = {"think_s": ready["completed"] - ready["started"],
                   "roundtrip_s": self.clock() - call["delivered"], "source": source}
        if source == "engine":
            latency["delay_ms"] = ack["applied_ms"] - call["source_ms"]
            latency["transport_overage"] = latency["delay_ms"] >= self.max_age_ms
        self._event("feedback", name, source=source, ack=deepcopy(ack), latency=latency)
        try:
            member.policy.acknowledge(deepcopy(ack), dict(latency))
        except Exception as exc:
            raise PolicyFailure(f"team {name} acknowledge: {exc}",
                                failure={"member": name, "method": "acknowledge"}) from exc
        member.ready = member.call = None

    def decide(self, observation):
        if self.closed or self.selected is not None:
            self._fault("team decision while closed or awaiting selected-member feedback")
        self._partition(observation)
        self.behavior = {"type": "team", "member": None}
        for name, member in self.members.items():
            if member.future is not None and member.future.done():
                self._collect(name, member)
            if member.ready is not None:
                try:
                    self._validate(name, member, observation)
                except IllegalActionError as exc:
                    orders = member.ready["orders"]
                    ack = {"validation_error": str(exc), "results": [
                        {"index": i + 1, "unit": order.get("unit"), "ok": False, "error": str(exc)}
                        for i, order in enumerate(orders) if isinstance(order, dict)
                    ] if isinstance(orders, list) else []}
                    self._feedback(name, ack, "local")
            if member.call is None:
                view = project(observation, member.unit)
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
        self.behavior = {"type": "team", "member": name, **member.call,
                         "worker": member.ready["behavior"]}
        self._event("selected", name, dispatch_seq=observation["seq"],
                    dispatch_ms=observation["time_ms"], selected_at=self.clock())
        return deepcopy(member.ready["orders"])

    def acknowledge(self, ack, latency):
        if self.selected is None:  # an idle adapter poll, not a completed member call
            return
        source = "outer_validation" if ack.get("validation_error") else "engine"
        if source != "engine":
            ack = {key: value for key, value in ack.items() if key != "applied_ms"}
        self._feedback(self.selected, ack, source)
        self.selected = None

    def metadata(self):
        return deepcopy(self.behavior)

    def close(self):
        self.closed = True
        self.stop.set()
        self.pool.shutdown(wait=True)
        failures = []
        for name, member in self.members.items():
            if member.future is not None:
                try:
                    self._collect(name, member)
                except PolicyFailure as exc:
                    failures.append(exc)
            if member.call is not None:
                self._event("discarded", name, selected=name == self.selected,
                            reason="episode_closed", closed_at=self.clock())
            try:
                close = getattr(member.policy, "close", None)
                if close:
                    close()
            except Exception as exc:
                self._event("close_failed", name, error=str(exc))
                failures.append(exc)
        if failures:
            raise PolicyFailure(f"team cleanup: {failures[0]}") from failures[0]


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
