"""Public-state witness and controls for the walled siege defence (cth-emp-siege-a-v1 and its
all-at-once arm cth-emp-siege-a-all-v1, Helmgart).

The witness (``WallWitness``, wall_witness) plays four rules, from the 2026-11-08 siege defence
design (runs/siege-evals-20261108/final-haengju.md, Witness):
1. build: at each decision, order the cheapest option on every usable empty building slot until
   the engine accepts it (``mode.slots``; one acceptance per slot).
2. fire: the archers, crossbowmen, rockets and cannon keep fire at will off, and turn it on only
   while a visible enemy that is not routing stands within FIRE_M of the wall line or inside it.
3. reserve: the Lord and both Jade Warriors go to the supply point RESERVE_POINT. They attack the
   nearest enemy that has been inside the wall line for BREACH_DECISIONS decisions in a row, and
   go back to that point once no visible enemy is inside.
4. fallback: once the Gatehouse capture point is enemy-held or a gate is breached
   (evidence_rules.gate_breached: hp 0 or less, whatever ``destroyed`` says), every unit goes to
   its spot near the Key Building KEEP_POINT and attacks visible enemies within KEEP_M of it.
   The fallback is kept to the end; the reserve rule stops then.
The wall line runs through WALL_ENDS and the public capture points WALL_POINTS; "inside" is
INSIDE_M or more north (higher z) of it. The controls are the witness with rules removed or
moved, one class each: ``HoldBuild`` (build only), ``KeepOnly`` (build, and the fallback from
the first decision), ``WFire``, ``WReserve`` and ``WNoFallback`` (one rule removed each).

Every arm reads only what play.public passes: its own units, the visible enemies, the public
``enemy_roster`` (for one cue) and ``mode`` (capture points, gates, slots and supplies), never
``evaluation``, ``setup``, ``native``, ``final``, ``reserve_briefing`` or the job. Roles bind
once, at the first observation, from each unit's type key (never its class or id); the fallback
spots go to units in the order of their type and start position. Unplayed: no game has run these
scripts, so nothing here shows what their orders achieve.

Each arm records two sets of first times. ``cues`` are the design's decision cues (Decisions 1-3),
which decide whether an ablation counts (Controls: "the removed rule's cue occurred"):
- fire: a visible enemy unit within CUE_NEAR_M of the wall line or inside it, while at least
  CUE_FAR_UNITS units of the public enemy roster have never been seen within CUE_FAR_M of it;
- reserve: exactly one visible, non-routing enemy has been inside the line for BREACH_DECISIONS
  decisions in a row (two such enemies at once are the design's reversal case, not the cue);
- fallback: the fallback rule's own trigger, the Gatehouse or a gate (never keep_only's start).
``triggers`` are when each rule's own trigger first fired (FIRE_M, any breaching enemy, the
fallback); they describe the play and count nothing.

Code reference: SMAC smac/env/starcraft2/starcraft2.py get_agent_action_heuristic keeps a target
until it is unavailable, as camp.py and cannae.py do.
"""

import math
from collections import Counter
from copy import deepcopy

from twwarhammer3.battle.evidence_rules import gate_breached, holds
from twwarhammer3.battle.local_command import able
from twwarhammer3.battle.scripted import distance
from twwarhammer3.protocol import PolicyFailure, friendly_units, visible_enemies

LORD = "wh3_main_cth_cha_lord_magistrate_0"
JADE = "wh3_main_cth_inf_jade_warriors_0"
SPEARMEN = "wh3_main_cth_inf_peasant_spearmen_1"
ARCHERS = "wh3_main_cth_inf_peasant_archers_0"
CROSSBOWS = "wh3_main_cth_inf_jade_warrior_crossbowmen_0"
ROCKETS = "wh3_main_cth_art_fire_rain_rocket_battery_0"
CANNON = "wh3_main_cth_art_grand_cannon_0"
ARMY = Counter({LORD: 1, JADE: 2, SPEARMEN: 2, ARCHERS: 2, CROSSBOWS: 1, ROCKETS: 1, CANNON: 1})
MISSILE = (ARCHERS, CROSSBOWS, ROCKETS, CANNON)
RESERVE = (LORD, JADE)
# Helmgart's capture points by id, with the key each must carry (recorded first observation of
# bench-b12-siege-baselines-20261016/episode-0001); another map is refused.
POINT_KEYS = {"c1": "major_key_building_leadership", "c2": "capture_point_gate_only",
              "c3": "capture_point_tower_only", "c4": "capture_point_tower_only",
              "c5": "capture_point_tower_only", "c6": "capture_point_tower_only",
              "c7": "minor_point_supplies"}

# JUDGEMENT: Wall witness thresholds — Claude, 2026-11-08 (siege defence design, Witness): the
# values below. Other distances, breach count, points or a fallback that ends change what the
# witness and its ablations win; the fire, reserve and fallback contrasts and the gate rest on them.
WALL_ENDS = ((-384, -81), (384, -81))  # the line's ends, at the side walls' z
WALL_POINTS = ("c6", "c5", "c2", "c4", "c3")  # in x order, west to east
INSIDE_M = 10  # an enemy this far or more north of the wall line is inside
FIRE_M = 60  # missile units fire at will while an able enemy is this close to the line or inside
BREACH_DECISIONS = 2  # decisions in a row inside before the reserve attacks an enemy
GATEHOUSE = "c2"  # enemy-held, it starts the fallback, as does a breached gate
RESERVE_POINT = "c7"  # where the reserve waits
KEEP_POINT = "c1"  # where everyone falls back to
KEEP_SPOT_M = 40  # each unit's fallback spot, on a ring this far around KEEP_POINT
KEEP_M = 100  # after the fallback, units attack only enemies this close to KEEP_POINT
RUN = True  # the reserve and the fallback move and attack at a run
RETRY_MS = 10000  # an unchanged move or attack is resent after this long once it lapsed
ARRIVED_M = 15  # a unit idle farther than this from its move's point has dropped the move
# JUDGEMENT?: Ablation cues — Claude, 2026-11-08 (design Decisions 1-3, Controls): an ablation
# counts on its decision's cue, not its rule's trigger; a roster unit never seen counts as not
# yet within CUE_FAR_M. Triggers or hidden data count other battles; the ablation counts rest on it.
CUE_NEAR_M = 150  # decision 1's cue: a visible enemy this close to the wall line or inside it
CUE_FAR_M, CUE_FAR_UNITS = 300, 10  # while this many roster units were never seen this close

RULES = frozenset({"build", "fire", "reserve", "fallback"})


def _nearest(unit, enemies):
    """The enemy nearest ``unit``; ties go to the smaller x, then z, never to id or list order."""
    return min(enemies, key=lambda e: (distance(unit, e), e["x"], e["z"]), default=None)


def _segment_distance(x, z, a, b):
    (ax, az), (bx, bz) = a, b
    dx, dz = bx - ax, bz - az
    share = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)))
    return math.hypot(x - ax - share * dx, z - az - share * dz)


def wall_line(points):
    """The public wall line, west to east: WALL_ENDS around WALL_POINTS ({id: {"x", "z"}})."""
    return [WALL_ENDS[0], *((points[name]["x"], points[name]["z"]) for name in WALL_POINTS),
            WALL_ENDS[1]]


def wall_distance(line, unit):
    """Metres from ``unit`` to the nearest point of ``line``."""
    return min(_segment_distance(unit["x"], unit["z"], a, b) for a, b in zip(line, line[1:]))


def inside(line, unit):
    """INSIDE_M or more north of ``line`` at the unit's x (its ends held flat beyond it)."""
    x = min(max(unit["x"], line[0][0]), line[-1][0])
    for (ax, az), (bx, bz) in zip(line, line[1:]):
        if ax <= x <= bx:
            return unit["z"] >= az + (bz - az) * (x - ax) / (bx - ax) + INSIDE_M
    return False


class WallWitness:
    """wall_witness: build, fire, reserve and fallback rules (module docstring)."""

    arm = "wall_witness"
    rules = RULES
    fallback_from_start = False

    def __init__(self):
        self.roles = None
        self.line = self.points = None
        self.spots = {}
        self.streaks, self.cue_streaks = {}, {}
        self.seen_near = set()
        self.accepted = set()
        self.sent, self.last_sent, self.targets = {}, {}, {}
        self.batch = []
        self.cues = {"fire_ms": None, "reserve_ms": None, "fallback_ms": None}
        self.triggers = {"fire_ms": None, "breach_ms": None, "fallback_ms": None}
        self.fallback_reason = None
        self.now = 0

    def _bind(self, observation):
        """Bind once, at the first observation: roles from type keys, the wall line and points
        from the public capture points, and the fallback spots in order of type and start."""
        friendly = observation.get("friendly") or []
        if (Counter(unit.get("type") for unit in friendly) != ARMY
                or any(unit.get("x") is None or unit.get("z") is None for unit in friendly)):
            # The cause ends the episode: a bare PolicyFailure is a forfeit, and the army would
            # stand for the whole battle.
            raise PolicyFailure("wall defence needs the declared ten placed units") \
                from ValueError(dict(Counter(unit.get("type") for unit in friendly)))
        points = {point.get("id"): point for point in
                  (observation.get("mode") or {}).get("capture_points") or []}
        if any((points.get(name) or {}).get("key") != key for name, key in POINT_KEYS.items()):
            raise PolicyFailure("wall defence needs Helmgart's capture points") \
                from ValueError(sorted(points))
        self.points = {name: {"x": points[name]["x"], "z": points[name]["z"]}
                       for name in POINT_KEYS}
        self.line = wall_line(self.points)
        ordered = sorted(friendly, key=lambda u: (u["type"], u["x"], u["z"]))
        self.roles = {"missile": [u["id"] for u in ordered if u["type"] in MISSILE],
                      "reserve": [u["id"] for u in ordered if u["type"] in RESERVE]}
        keep = self.points[KEEP_POINT]
        for index, unit in enumerate(ordered):
            angle = 2 * math.pi * index / len(ordered)
            self.spots[unit["id"]] = {"x": round(keep["x"] + KEEP_SPOT_M * math.sin(angle), 1),
                                      "z": round(keep["z"] + KEEP_SPOT_M * math.cos(angle), 1)}

    def wall_distance(self, unit):
        return wall_distance(self.line, unit)

    def inside(self, unit):
        return inside(self.line, unit)

    def _send(self, unit, order):
        # cannae.py Envelop._send: repeat a move or attack only when the engine dropped it.
        identity, idle = unit["id"], "idle" in (unit.get("state") or [])
        lapsed = (idle and distance(unit, order) > ARRIVED_M if order["type"] == "move"
                  else idle or not unit.get("target"))
        if self.sent.get(identity) == order and not (
                lapsed and self.now - self.last_sent[identity] >= RETRY_MS):
            return []
        self.sent[identity], self.last_sent[identity] = order, self.now
        return [order]

    def _attack(self, unit, target):
        self.targets[unit["id"]] = target["id"]
        return self._send(unit, {"unit": unit["id"], "type": "attack", "target": target["id"],
                                 "mode": "auto", "run": RUN, "queue": False})

    def _move(self, unit, spot):
        self.targets.pop(unit["id"], None)
        return self._send(unit, {"unit": unit["id"], "type": "move", "x": spot["x"],
                                 "z": spot["z"], "run": RUN, "queue": False})

    def _kept(self, identity, enemies):
        return next((e for e in enemies if e["id"] == self.targets.get(identity)), None)

    def _builds(self, mode):
        if "build" not in self.rules:
            return []
        orders, left = [], mode.get("supplies")
        for slot in sorted(mode.get("slots") or [], key=lambda s: s["id"]):
            if (slot["id"] in self.accepted or not slot.get("usable") or slot.get("built")
                    or slot.get("building_s") is not None or not slot.get("options")):
                continue
            option = min(slot["options"], key=lambda o: (o.get("cost") or 0, o["name"]))
            cost = option.get("cost") or 0
            if left is not None and cost > left:
                continue
            left = None if left is None else left - cost
            orders.append({"unit": "army", "type": "build", "slot": slot["id"],
                           "option": option["name"]})
        return orders

    def _cues(self, observation, visible, enemies):
        """Record the first decision at which each of decisions 1 and 2's cues occurred."""
        close = [e for e in visible if self.inside(e) or self.wall_distance(e) <= CUE_FAR_M]
        self.seen_near.update(e["id"] for e in close)
        far = sum(unit.get("id") not in self.seen_near
                  for unit in observation.get("enemy_roster") or [])
        if self.cues["fire_ms"] is None and far >= CUE_FAR_UNITS and any(
                self.inside(e) or self.wall_distance(e) <= CUE_NEAR_M for e in close):
            self.cues["fire_ms"] = self.now
        self.cue_streaks = {e["id"]: self.cue_streaks.get(e["id"], 0) + 1
                            for e in enemies if self.inside(e)}
        confirmed = [n for n in self.cue_streaks.values() if n >= BREACH_DECISIONS]
        if self.cues["reserve_ms"] is None and len(confirmed) == 1:
            self.cues["reserve_ms"] = self.now

    def _fire(self, units, enemies):
        near = any(self.inside(e) or self.wall_distance(e) <= FIRE_M for e in enemies)
        if near and self.triggers["fire_ms"] is None:
            self.triggers["fire_ms"] = self.now
        if "fire" not in self.rules:
            return []
        orders = []
        for identity in self.roles["missile"]:
            unit = units.get(identity)
            behaviours = (unit or {}).get("behaviours") or {}
            if unit is not None and able(unit) and "fire_at_will" in behaviours \
                    and behaviours["fire_at_will"] is not near:
                orders.append({"unit": identity, "type": "behaviour",
                               "behaviour": "fire_at_will", "enabled": near})
        return orders

    def _reserve(self, units, enemies, visible):
        inside = {e["id"] for e in visible if self.inside(e)}
        self.streaks = {identity: self.streaks.get(identity, 0) + 1 for identity in inside}
        breaching = [e for e in enemies if self.streaks.get(e["id"], 0) >= BREACH_DECISIONS]
        if breaching and self.triggers["breach_ms"] is None:
            self.triggers["breach_ms"] = self.now
        if "reserve" not in self.rules or self.fallback_reason is not None:
            return []
        orders = []
        for identity in self.roles["reserve"]:
            unit = units.get(identity)
            if unit is None or not able(unit):
                continue
            if breaching:
                orders += self._attack(unit, self._kept(identity, breaching)
                                       or _nearest(unit, breaching))
            elif not inside:
                orders += self._move(unit, self.points[RESERVE_POINT])
        return orders

    def _fallback(self, observation, units, enemies):
        mode = observation.get("mode") or {}
        gatehouse = next((p for p in mode.get("capture_points") or []
                          if p.get("id") == GATEHOUSE), {})
        cue = ("gatehouse" if holds(gatehouse, "enemy") else
               "gate" if any(gate_breached(g) for g in mode.get("gates") or []) else None)
        if cue and self.cues["fallback_ms"] is None:
            self.cues["fallback_ms"] = self.now
        reason = "start" if self.fallback_from_start else cue
        if reason and self.triggers["fallback_ms"] is None:
            self.triggers["fallback_ms"] = self.now
        if "fallback" not in self.rules:
            return []
        if reason and self.fallback_reason is None:
            self.fallback_reason = reason
        if self.fallback_reason is None:
            return []
        keep = self.points[KEEP_POINT]
        near = [e for e in enemies if distance(e, keep) <= KEEP_M]
        orders = []
        for identity, spot in self.spots.items():
            unit = units.get(identity)
            if unit is None or not able(unit):
                continue
            target = self._kept(identity, near) or _nearest(unit, near)
            orders += self._attack(unit, target) if target else self._move(unit, spot)
        return orders

    def decide(self, observation):
        self.now = observation["time_ms"]
        if self.roles is None:
            self._bind(observation)
        units = friendly_units(observation)
        visible = list(visible_enemies(observation).values())
        enemies = [e for e in visible if able(e)]
        self._cues(observation, visible, enemies)
        orders = self._builds(observation.get("mode") or {})
        fallback = self._fallback(observation, units, enemies)
        orders += self._fire(units, enemies)
        orders += self._reserve(units, enemies, visible)
        orders += fallback
        self.batch = orders
        return orders

    def acknowledge(self, ack, latency):
        for result in ack.get("results", []):
            index = result.get("index")
            order = self.batch[index - 1] if isinstance(index, int) and \
                0 < index <= len(self.batch) else {}
            if order.get("type") == "build" and result.get("ok"):
                self.accepted.add(order["slot"])
            if not result.get("ok"):
                self.sent.pop(result.get("unit"), None)

    def metadata(self):
        return deepcopy({"type": self.arm, "version": 1, "rules": sorted(self.rules),
                         "roles": self.roles, "cues": self.cues, "triggers": self.triggers,
                         "fallback_reason": self.fallback_reason,
                         "builds_accepted": sorted(self.accepted)})


class HoldBuild(WallWitness):
    """hold_build: the cheapest building on every usable slot, then no orders."""

    arm = "hold_build"
    rules = frozenset({"build"})


class KeepOnly(WallWitness):
    """keep_only: builds as hold_build, and every unit at its spot near the Key Building from
    the first decision, attacking only enemies within KEEP_M of it."""

    arm = "keep_only"
    rules = frozenset({"build", "fallback"})
    fallback_from_start = True


class WFire(WallWitness):
    """w_fire: the witness without its fire rule (fire at will stays as the engine has it)."""

    arm = "w_fire"
    rules = RULES - {"fire"}


class WReserve(WallWitness):
    """w_reserve: the witness without its reserve rule (the Lord and the Jade Warriors stay
    until the fallback)."""

    arm = "w_reserve"
    rules = RULES - {"reserve"}


class WNoFallback(WallWitness):
    """w_nofallback: the witness without its fallback rule."""

    arm = "w_nofallback"
    rules = RULES - {"fallback"}
