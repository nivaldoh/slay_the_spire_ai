"""Scripted witnesses and foils for the construction test on Cannae C v2 (stage 2).

Spec: docs/twwarhammer3/communication-structure.md ("The battle: Cannae C", "Stages" row 2).
The witnesses port cannae.py WingSupport (role priorities, horse wings labelled at their first
known position, a target kept while it qualifies) from its global view to five captains who see
160 m and share contacts by text. Code reference: SMAC smac/env/starcraft2/starcraft2.py
get_agent_action_heuristic keeps a target until it is unavailable; here a captain attacks only a
target in its own view and runs toward one it knows only from a message.

The foils play the v1 silent arm and send nothing: they know their start points (the v1 command
block's `rendezvous`), the clock and the terrain bounds. Members are zero-argument classes, so a
`local_team` controller file names them as `twwarhammer3.battle.local_scripts:<Class>`.
"""

from copy import deepcopy

# Rests on JUDGEMENT src/twwarhammer3/battle/cannae.py Cannae witness development rules
# (the centre's 90 m and the 10 s retry), B support witness and Enemy wing labels.
from twwarhammer3.battle.cannae import CLOSE_M, RETRY_MS
from twwarhammer3.battle.llm import ARRIVED_M
from twwarhammer3.battle.local_command import able, distance

CAVALRY_GROUPS = ("decisive_cavalry", "containing_cavalry")
# JUDGEMENT: Witness contact age — Claude, 2026-11-08: a peer witness forgets a contact 20 s after
# its latest sighting. A shorter age stops cavalry chasing reports, a longer one sends them to old
# positions; the peer witness's stage 2 wins rest on it.
CONTACT_MS = 20000
# JUDGEMENT: Overview refresh — Claude, 2026-11-08: the overview commander re-sends an unchanged
# target with its new position every 3 s. Sending only on change, or more often, changes how
# stale a captain's moves are; the overview witness's stage 2 wins rest on it.
REFRESH_MS = 3000
# JUDGEMENT: Foil timetable — Claude, 2026-11-08: (start ms, metres east): cavalry 220 m at 0 s,
# Greatswords 120 m at 20 s, centre 60 m at 60 s. Other offsets or times change how strong the
# schedule foil is; the stage 2 reading that foils lose rests on it.
SCHEDULE = {"centre": (60000, 60), "left_infantry": (20000, 120), "right_infantry": (20000, 120),
            "decisive_cavalry": (0, 220), "containing_cavalry": (0, 220)}


def attack(unit, target):
    return {"unit": unit, "type": "attack", "target": target, "mode": "auto", "run": True,
            "queue": False}


def move(unit, point):
    return {"unit": unit, "type": "move", "x": point["x"], "z": point["z"], "facing": None,
            "width": None, "run": True, "queue": False}


def text(to, body):
    return {"channel": "text", "to": to, "text": body}


def midline(start_points):
    """The z between the two Greatsword start points (-250 on C v2): north is above it."""
    return (start_points["left_infantry"]["z"] + start_points["right_infantry"]["z"]) / 2


def role_targets(role, unit, known, wings):
    """WingSupport's target set for one regiment of a group (cannae.py WingSupport.decide)."""
    infantry = [e for e in known if e.get("class") == "infantry"]
    cavalry = [e for e in known if e.get("class") == "cavalry"]
    north = [e for e in cavalry if wings.get(e["id"]) == "north"]
    south = [e for e in cavalry if wings.get(e["id"]) == "south"]
    if role == "centre":
        return known if known and min(distance(unit, e) for e in known) <= CLOSE_M else []
    if role == "left_infantry":
        return north or infantry
    if role == "right_infantry":
        return infantry
    if role == "decisive_cavalry":
        return north or south or infantry
    return south or infantry


class _Member:
    """Order bookkeeping shared by every member here; no messages unless a subclass sets them."""

    def __init__(self):
        self.now = 0
        self.sent, self.last_sent, self.targets = {}, {}, {}
        self.messages = []

    def _send(self, unit, order):
        # cannae.py Envelop._send: repeat an order only when the engine dropped it.
        identity = unit["id"]
        states = unit.get("state") or []
        lapsed = (order["type"] == "attack" and (not unit.get("target") or "idle" in states)
                  or order["type"] == "move" and "idle" in states)
        if self.sent.get(identity) == order and not (
                lapsed and self.now - self.last_sent[identity] >= RETRY_MS):
            return []
        self.sent[identity], self.last_sent[identity] = order, self.now
        return [deepcopy(order)]

    def _pick(self, unit, candidates):
        # cannae.py Envelop._attack: keep the regiment's target while it qualifies, else nearest.
        target = next((c for c in candidates if c["id"] == self.targets.get(unit["id"])), None)
        target = target or min(candidates, key=lambda c: distance(unit, c), default=None)
        if target is None:
            self.targets.pop(unit["id"], None)
        else:
            self.targets[unit["id"]] = target["id"]
        return target

    def _act(self, unit, target, visible):
        """Attack a target in the own view by id; run toward one known only from a message.

        None when neither applies (the target is in view but unable, or the regiment already
        stands at its reported position), so the caller can fall back.
        """
        row = visible.get(target["id"])
        if row is not None:
            return self._send(unit, attack(unit["id"], target["id"])) if able(row) else None
        if distance(unit, target) > ARRIVED_M:
            return self._send(unit, move(unit["id"], {"x": target["x"], "z": target["z"]}))
        return None

    def _nearest(self, unit, enemies):
        nearest = min(enemies, key=lambda e: distance(unit, e), default=None)
        return self._send(unit, attack(unit["id"], nearest["id"])) if nearest else []

    def drain_messages(self):
        messages, self.messages = self.messages, []
        return messages

    def acknowledge(self, ack, latency):
        for result in ack.get("results", []):
            if not result.get("ok"):
                self.sent.pop(result.get("unit"), None)


class PeerWitness(_Member):
    """Peer arm captain: a contact table from its own view and peers' reports, WingSupport roles."""

    def __init__(self):
        super().__init__()
        self.mid_z = None
        self.contacts, self.wings, self.told = {}, {}, {}
        self.replies = 0

    def _learn(self, identity, kind, x, z, time_ms, fit):
        old = self.contacts.get(identity)
        if old is not None and old["time_ms"] >= time_ms:
            return
        self.contacts[identity] = {"id": identity, "class": kind, "x": x, "z": z,
                                   "time_ms": time_ms, "able": fit}
        if kind == "cavalry":
            self.wings.setdefault(identity, "north" if z >= self.mid_z else "south")

    def _read(self, body):
        """Learn a peer's report "seen T;ID CLASS X Z;..."; ignore any other text."""
        head, *parts = body.split(";") if isinstance(body, str) else [""]
        word, _, time_ms = head.partition(" ")
        if word != "seen":
            return
        try:
            time_ms = int(time_ms)
            rows = [part.split(" ") for part in parts]
            rows = [(identity, kind, float(x), float(z)) for identity, kind, x, z in rows]
        except ValueError:
            return
        for identity, kind, x, z in rows:
            self._learn(identity, kind, x, z, time_ms, True)

    def _report(self, peer, seen, limit):
        wanted = "cavalry" if peer in CAVALRY_GROUPS else "infantry"
        body = f"seen {self.now}"
        for enemy in sorted(seen, key=lambda e: (e.get("class") != wanted, e["id"])):
            part = f";{enemy['id']} {enemy.get('class')} {round(enemy['x'])} {round(enemy['z'])}"
            if len((body + part).encode("utf-8")) > limit:
                break
            body += part
        return body

    def decide(self, observation):
        command = observation["command"]
        role, rules = command["member"], command["rules"]
        self.now = observation["time_ms"]
        if self.mid_z is None:
            self.mid_z = midline(command["start_points"])
        visible = {e["id"]: e for e in observation.get("enemy", [])
                   if e.get("x") is not None and e.get("z") is not None}
        for enemy in visible.values():
            self._learn(enemy["id"], enemy.get("class"), enemy["x"], enemy["z"], self.now,
                        able(enemy))
        for record in command["received"]:
            self._read(record.get("text"))
        self.contacts = {identity: c for identity, c in self.contacts.items()
                         if self.now - c["time_ms"] <= CONTACT_MS}
        known = [c for c in self.contacts.values() if c["able"]]
        seen = [e for e in visible.values() if able(e)]
        orders = []
        for unit in observation["friendly"]:
            if not able(unit):
                continue
            target = self._pick(unit, role_targets(role, unit, known, self.wings))
            action = self._act(unit, target, visible) if target else None
            # JUDGEMENT?: Witness centre — Claude, 2026-11-08: with no known enemy within 90 m
            # the centre holds (WingSupport), not the card's nearest-visible fallback. Engaging
            # at 160 m changes when the centre fights; the peer witness's wins rest on it.
            if action is None and role != "centre":
                action = self._nearest(unit, seen)
            orders += action or []
        # JUDGEMENT: Peer witness reports — Claude, 2026-11-08: own-view contacts only, the
        # recipient's class first, to the two peers told longest ago (one status when none).
        # Relaying or picking peers by need changes what reaches whom; the witness rests on it.
        peers = sorted(rules["recipients"], key=lambda peer: (self.told.get(peer, -1), peer))
        peers = peers[:2] if seen else peers[:1]
        self.messages = [text(peer, self._report(peer, seen, rules["text_bytes"]) if seen
                              else f"status {self.now} clear") for peer in peers]
        self.replies += 1
        self.told.update({peer: self.replies for peer in peers})
        return orders

    def metadata(self):
        return deepcopy({"type": "peer_witness", "version": 1, "contacts": self.contacts,
                         "wings": self.wings, "targets": self.targets})


class OverviewWitnessCommander(_Member):
    """Overview arm commander: WingSupport's assignment from the global view, one target each."""

    def __init__(self):
        super().__init__()
        self.mid_z = None
        self.wings, self.assigned, self.told = {}, {}, {}

    def _assignment(self, group, target):
        identity = target["id"] if target else None
        told = self.told.get(group)
        due = identity is not None and told is not None and self.now - told >= REFRESH_MS
        if identity == self.assigned.get(group) and not due:
            return None
        self.assigned[group], self.told[group] = identity, self.now
        if identity is None:
            return f"target none {self.now}"
        return f"target {identity} {round(target['x'])} {round(target['z'])} {self.now}"

    def decide(self, observation):
        command = observation["command"]
        self.now = observation["time_ms"]
        if self.mid_z is None:
            self.mid_z = midline(command["start_points"])
        units = {u["id"]: u for u in observation.get("allies", [])}
        visible = [e for e in observation.get("enemy", [])
                   if e.get("x") is not None and e.get("z") is not None]
        for enemy in (e for e in visible if e.get("class") == "cavalry"):
            self.wings.setdefault(enemy["id"], "north" if enemy["z"] >= self.mid_z else "south")
        known = [e for e in visible if able(e)]
        self.messages = []
        for group, identities in command["groups"].items():
            # JUDGEMENT?: Overview group target — Claude, 2026-11-08: a captain's one target is
            # the WingSupport target of its first regiment, in group order, that has one. One
            # target per regiment changes the centre's fight; the overview witness rests on it.
            target = None
            for identity in identities:
                unit = units.get(identity)
                if unit is not None and able(unit):
                    picked = self._pick(unit, role_targets(group, unit, known, self.wings))
                    target = target or picked
            if group not in command["rules"]["recipients"]:
                continue
            body = self._assignment(group, target)
            if body is not None:
                self.messages.append(text(group, body))
        return []

    def metadata(self):
        return deepcopy({"type": "overview_witness_commander", "version": 1,
                         "assigned": self.assigned, "wings": self.wings})


class OverviewWitnessCaptain(_Member):
    """Overview arm captain: the commander's latest target, else a local 90 m fight, else hold."""

    def __init__(self):
        super().__init__()
        self.target = None

    def _read(self, body):
        """Keep the commander's "target ID X Z T", or drop the target on "target none T"."""
        words = body.split(" ") if isinstance(body, str) else []
        try:
            if words[:2] == ["target", "none"] and len(words) == 3:
                self.target = None
            elif words[:1] == ["target"] and len(words) == 5:
                self.target = {"id": words[1], "x": float(words[2]), "z": float(words[3]),
                               "time_ms": int(words[4])}
        except ValueError:
            pass

    def decide(self, observation):
        command = observation["command"]
        self.now = observation["time_ms"]
        for record in command["received"]:
            if record.get("sender") == "commander":
                self._read(record.get("text"))
        visible = {e["id"]: e for e in observation.get("enemy", [])}
        seen = [e for e in visible.values() if able(e)]
        orders, fit = [], [u for u in observation["friendly"] if able(u)]
        for unit in fit:
            action = self._act(unit, self.target, visible) if self.target else None
            if action is None:
                action = self._nearest(unit, [e for e in seen if distance(unit, e) <= CLOSE_M])
            orders += action
        self.messages = [text("commander", f"status {self.now} units {len(fit)} seen {len(seen)}")]
        return orders

    def metadata(self):
        return deepcopy({"type": "overview_witness_captain", "version": 1,
                         "target": self.target})


class _Foil(_Member):
    """A captain that sends nothing; its timetable point is fixed by public knowledge only."""

    def __init__(self):
        super().__init__()
        self.starts = {}

    def _point(self, name, rendezvous):
        raise NotImplementedError

    def decide(self, observation):
        command = observation["command"]
        name, rendezvous = command["member"], command["rendezvous"]
        self.now = observation["time_ms"]
        point, home = self._point(name, rendezvous), rendezvous[name]
        bounds = (observation.get("terrain") or {}).get("bounds") or {}
        enemies = [e for e in observation.get("enemy", []) if able(e)]
        orders = []
        for unit in observation["friendly"]:
            start = self.starts.setdefault(unit["id"], {"x": unit["x"], "z": unit["z"]})
            if not able(unit):
                continue
            # JUDGEMENT: Foil engagement — Claude, 2026-11-08: a foil regiment attacks the nearest
            # visible enemy whenever one is in view, and follows its timetable only when none is.
            # Finishing the move first changes both foils' fights; the stage 2 reading rests on it.
            if enemies:
                orders += self._nearest(unit, enemies)
            elif point is not None:
                # Each regiment keeps its offset from the group's start point.
                goal = {"x": start["x"] + point["x"] - home["x"],
                        "z": start["z"] + point["z"] - home["z"]}
                if {"min_x", "max_x", "min_z", "max_z"} <= set(bounds):
                    for axis in ("x", "z"):
                        goal[axis] = min(bounds[f"max_{axis}"] - ARRIVED_M,
                                         max(bounds[f"min_{axis}"] + ARRIVED_M, goal[axis]))
                goal = {axis: round(value, 1) for axis, value in goal.items()}
                if distance(unit, goal) > ARRIVED_M:
                    orders += self._send(unit, move(unit["id"], goal))
        return orders

    def metadata(self):
        return {"type": self.kind, "version": 1}


class FixedSchedule(_Foil):
    """Each group runs a marked distance east of its start at a marked time (SCHEDULE)."""

    kind = "fixed_schedule"

    def _point(self, name, rendezvous):
        start_ms, east_m = SCHEDULE[name]
        home = rendezvous[name]
        return None if self.now < start_ms else {"x": home["x"] + east_m, "z": home["z"]}


class CentralConcentration(_Foil):
    """Every group runs to the centre group's start point at once."""

    kind = "central_concentration"

    def _point(self, name, rendezvous):
        return rendezvous["centre"]
