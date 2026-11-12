"""Public-state witness and controls for the siege attack (ksl-emp-siege-a-v1, Helmgart).

Rules from the 2026-11-08 siege-attack design (runs/siege-evals-20261108/final-izmail.md,
Witness "Escalade v1" and Controls C3-C9). ``Escalade`` (escalade, the witness):
- Groups, fixed at the first observation by type and start x, never by id: Centre (the ram's
  crew from ``mode.vehicles``, the middle Kossars (Spears), the western Streltsi, the Little
  Grom), West and East (the two westmost and two eastmost remaining Armoured Kossars and the
  westmost and eastmost Kossars (Spears)), Reserve (the other Armoured Kossars and Streltsi, the
  Boyar) and Horse (the Winged Lancers). A crew of one of these types leaves its type's list
  first, and the groups fill from the units that remain.
- Targets from ``mode.fortifications``: West the wall piece nearest c6, East the one nearest
  c3, Centre's Kossars the one nearest c5, the crew and the Grom the gate g1.
- Phase 1: each group goes to its staging spots STAGING_M south of its target, the Horse
  HORSE_M south of g1. Phase 2, when every unit of West, Centre and East stands within ARRIVE_M
  of its spot or at PHASE2_MS: every climber besieges its target, the crew besieges g1, the
  Grom attacks g1 (attack_building) and the Streltsi shoot the visible enemy nearest them
  within their range of g1. Phase 3: a unit on the wall (``on_wall``) or inside the front line
  goes to the first victory point not held by us of c7, then the nearer of c8 and c9, then c1.
- A siege order goes only to a piece listed in this observation's ``mode.fortifications`` and
  not at 0% (protocol's rule). Once its target reads 0% (gate_breached) a climber or the crew
  goes in as in phase 3 and the Grom stops; while the list is missing, they get no order.
- Horse: once the gate is breached (evidence_rules.gate_breached on the public gate nearest g1:
  hp 0 or less, whatever ``destroyed`` says) or c2 is ours, it goes to c7, then c1.
- Reserve: RESERVE_MS after phase 2 it joins the group that lost the largest share of its men
  since phase 2, if over RESERVE_LOSS, else the group with most units on the wall, and besieges
  that group's climbing target. Phase 4: once INSIDE_UNITS of our units are inside the front
  line, every unit attacks the visible enemy nearest it that is not routing.

The controls change one rule each, so tests/twwarhammer3/wh3_ablation.py can diff their orders
against the witness: ``Concentrate`` (C6, D1's arm: West's and East's targets become the wall
pieces nearest c5 and c4, in the gate recess), ``CavalryEarly`` (C7, D2's arm: the Lancers
ride to g1 at the start and attack visible enemies within EARLY_M), ``Piecemeal`` (C8: each
group besieges as soon as it is staged), ``ShootOnly`` (C4: a unit with ammunition shoots from
SHOOT_M south of its target until it has none, then plays as the witness) and ``GateOnly``
(C5: no ladders; the infantry, its Streltsi holding their fire, waits STAGING_M south of g1
until the gate is breached, then enters). ``BesiegeNearest`` (C3) is its own plan, and
``EscaladeReplay`` (C9) replays a witness win (replay_schedule) with its siege orders.
``OrderProbe`` is stage 2's order-effect probe: a diagnostic, not an arm.

Witness version 2, options for owner question 6 on escalade-eval.md (the second look's owner
question 2), built beside version 1 on 2026-11-09 and in no plan until the owner picks them;
version 1 stays the default. ``EscaladeV2``, ``ConcentrateV2``, ``CavalryEarlyV2``,
``PiecemealV2``, ``ShootOnlyV2`` and ``GateOnlyV2`` are their version 1 classes with three
changes (``Version2``), and ``BesiegeNearestV2`` takes (b) only; each writes version 2 in its
metadata. (a) Phase 3 goes to c7, then c1 (VICTORY_TIERS_V2). (b) g1 counts as fallen once the
public gate nearest it, its door, reads hp 0 or less (``door_view``), so the crew walks in, and a
unit whose last accepted order besieges or attacks g1 and that gets no new one, the Grom among
them, gets a halt until it or another replacement is accepted (``door_halts``): in the one
recording, a standing attack_building kept firing until the
building itself read 0, and whether a halt ends one is unread. Validation still accepts an order
on g1 above 0%. (c) West's and East's staging rows (in ``GateOnly`` the reserve's as well) move
south, whole metres at a time, until every spot stands STAGING_M or more from every listed piece
and SPACING_M or more from every spot placed before.

Every arm reads only what play.public passes: its own units (``on_wall``, ``can_climb``,
``can_siege``), the visible enemies and ``mode`` (capture points, gates, fortifications and
vehicles), never ``evaluation``, ``setup``, ``native``, ``final`` or the job. The front line is
the southernmost fortification centre in each FRONT_COLUMN_M column (``front_line``), which
nothing has checked against the fort. Unplayed: no game has run these scripts, so nothing here
shows what their orders achieve; the siege orders' effects (climbing, the ram, the gun's damage)
are unread until stage 2.

Code reference: SMAC smac/env/starcraft2/starcraft2.py get_agent_action_heuristic keeps a target
until it is unavailable, as camp.py and wall_defence.py do.
"""

# The battle's page is docs/twwarhammer3/escalade-eval.md. Its one claim is D1, Escalade against
# Concentrate; CavalryEarly's D2 and the other controls stay descriptive or shortcuts (rests on
# JUDGEMENT docs/twwarhammer3/escalade-eval.md Escalade claim).
import math
from collections import Counter
from copy import deepcopy

from twwarhammer3.battle.evidence_rules import gate_breached, holds
from twwarhammer3.battle.local_command import able
from twwarhammer3.battle.replay_schedule import ReplaySchedule
from twwarhammer3.battle.scripted import distance
from twwarhammer3.protocol import SIEGE_ORDER_TYPES, PolicyFailure, friendly_units, visible_enemies

BOYAR = "wh3_main_ksl_cha_boyar_0"
ARMOURED = "wh3_main_ksl_inf_armoured_kossars_0"
SPEARS = "wh3_main_ksl_inf_kossars_1"
STRELTSI = "wh3_main_ksl_inf_streltsi_0"
LANCERS = "wh3_main_ksl_cav_winged_lancers_0"
GROM = "wh3_main_ksl_veh_little_grom_0"
ARMY = Counter({BOYAR: 1, ARMOURED: 5, SPEARS: 3, STRELTSI: 2, LANCERS: 1, GROM: 1})
# Helmgart's capture points by id, with the key each must carry (the 2026-10-14 attack smoke's
# first observation); another map is refused.
POINT_KEYS = {"c1": "major_key_building_leadership", "c2": "capture_point_gate_only",
              **dict.fromkeys(("c3", "c4", "c5", "c6"), "capture_point_tower_only"),
              **dict.fromkeys(("c7", "c8", "c9"), "minor_point_supplies")}
GATE = "g1"
GATEHOUSE = "c2"
ASSAULT = ("west", "centre", "east")  # the groups that stage; also the reserve's tie order

# JUDGEMENT: Escalade thresholds — Claude, 2026-11-08 (siege-attack design, Witness): the design's
# values below, and SPACING_M, RUN and the targets' points, which it leaves open. Other values
# change what the witness and its controls win; the D1 contrast and the witness gate rest on them.
TARGET_POINTS = {"west": "c6", "east": "c3", "centre": "c5"}  # each climbing target: the
# wall piece nearest this capture point; the crew and the Grom take GATE
STAGING_M = 150  # staging spots this far south of the target
SPACING_M = 40  # a group's units side by side this far apart along x, in x order
ARRIVE_M = 20  # a unit this close to its staging spot is staged
PHASE2_MS = 150000  # phase 2 starts at this battle time if a group is not staged by then
HORSE_M = 300  # the Horse waits this far south of g1
RESERVE_MS = 60000  # the reserve's decision, this long after phase 2
RESERVE_LOSS = 0.30  # a group that lost more than this share of its men since phase 2 gets it
INSIDE_UNITS = 6  # phase 4 starts once this many of our units are inside the front line
# JUDGEMENT?: Victory order — Claude, 2026-11-09: in 23 Helmgart traces (player defending), all
# 4 ticket drains began once c1 fell; c7 is on the gate-to-c1 route, c8/c9 add about 520 m a unit
# (1,160 m via both). Alternative ((c7,), (c1,)); phase 3 and phase 4 with no enemy seen rest on it.
VICTORY_TIERS = (("c7",), ("c8", "c9"), ("c1",))  # phase 3's order of victory points
RUN = True  # besiege, attack and phase 3 at a run; staging at a walk
# JUDGEMENT?: Front line — Claude, 2026-11-08: the southernmost fortification centre in each 40 m
# column of x, a unit 10 m north of it inside. No battle has read the pieces; phase 3, phase 4
# and the entry-route reading rest on it, and the fort's real pieces may need another rule.
FRONT_COLUMN_M = 40
INSIDE_M = 10
# JUDGEMENT: Control parameters — Claude, 2026-11-08 (design, Controls): Cavalry early's 50 m, Shoot
# only's 120 m and Concentrate's recess pieces (nearest c5 and c4). Other values or one piece
# change what the controls test; D1's and D2's contrasts and the shortcut screen rest on them.
EARLY_M = 50  # Cavalry early attacks visible enemies this close to the Lancers
GATE_FRONT_M = 20  # Cavalry early rides to this far south of g1's centre
SHOOT_M = 120  # Shoot only fires from this far south of its target
CONCENTRATE_POINTS = {"west": "c5", "east": "c4", "centre": "c5"}
RETRY_MS = 10000  # an unchanged move or attack is resent after this long once it lapsed
ARRIVED_M = 15  # a unit idle farther than this from its move's point has dropped the move


def _nearest(unit, others):
    """The one of ``others`` nearest ``unit``; ties go to the smaller x, then z, never to id."""
    return min(others, key=lambda o: (distance(unit, o), o["x"], o["z"]), default=None)


def bearing(start, end):
    """Degrees from ``start`` to ``end``: 0 north (+z), 90 east (+x)."""
    return round(math.degrees(math.atan2(end["x"] - start["x"], end["z"] - start["z"])) % 360)


def front_line(fortifications):
    """The front of the fort, west to east: the southernmost fortification centre in each
    FRONT_COLUMN_M column of x (gates, wall pieces and towers alike)."""
    columns = {}
    for piece in fortifications:
        column = math.floor(piece["x"] / FRONT_COLUMN_M)
        if column not in columns or piece["z"] < columns[column][1]:
            columns[column] = (piece["x"], piece["z"])
    return [columns[column] for column in sorted(columns)]


def inside(line, unit):
    """INSIDE_M or more north of ``line`` at the unit's x (its ends held flat beyond it)."""
    x = min(max(unit["x"], line[0][0]), line[-1][0])
    for (ax, az), (bx, bz) in zip(line, line[1:]):
        if ax <= x <= bx and bx > ax:
            return unit["z"] >= az + (bz - az) * (x - ax) / (bx - ax) + INSIDE_M
    return unit["z"] >= line[0][1] + INSIDE_M  # a single column, or x on a vertical step


def groups(friendly, crew):
    """Each group's unit ids from the first observation's own units, by type and start x (then
    z), never by id; ``crew`` (the ram's crew id or None) goes to Centre and leaves its type."""
    ordered = sorted(friendly, key=lambda u: (u["x"], u["z"]))

    def of(key):
        return [u["id"] for u in ordered if u["type"] == key and u["id"] != crew]

    armoured, spears, streltsi = of(ARMOURED), of(SPEARS), of(STRELTSI)
    return {"centre": ([crew] if crew else []) + spears[1:-1] + streltsi[:1] + of(GROM),
            "west": armoured[:2] + spears[:1], "east": armoured[-2:] + spears[-1:],
            "reserve": armoured[2:-2] + streltsi[1:] + of(BOYAR), "horse": of(LANCERS)}


class Escalade:
    """escalade: three sectors staged and assaulted together, the ram and the gun at the gate,
    the Lancers held until the gate is breached, one reserve (module docstring)."""

    arm = "escalade"
    target_points = TARGET_POINTS
    ladders = True  # GateOnly: no wall piece is besieged
    together = True  # Piecemeal: each group starts phase 2 on its own
    victory_tiers = VICTORY_TIERS  # Version2: VICTORY_TIERS_V2

    def __init__(self):
        self.groups = self.jobs = self.points = self.pieces = self.line = None
        self.targets, self.spots = {}, {}
        self.phase2 = {}  # group -> battle ms its phase 2 started
        self.phase2_reason = None
        self.men0 = {}
        self.reserve = self.reserve_ms = None
        self.gate_open_ms = self.phase4_ms = None
        self.sent, self.last_sent, self.kept = {}, {}, {}
        self.fort = {}  # this observation's mode.fortifications by id
        self.now = 0

    # Binding, once, at the first observation.
    def _bind(self, observation):
        friendly = observation.get("friendly") or []
        mode = observation.get("mode") or {}
        if (Counter(u.get("type") for u in friendly) != ARMY
                or any(u.get("x") is None or u.get("z") is None for u in friendly)):
            # The cause ends the episode: a bare PolicyFailure is a forfeit, and the army would
            # stand for the whole battle.
            raise PolicyFailure("escalade needs the declared thirteen placed units") \
                from ValueError(dict(Counter(u.get("type") for u in friendly)))
        points = {p.get("id"): p for p in mode.get("capture_points") or []}
        if any((points.get(name) or {}).get("key") != key for name, key in POINT_KEYS.items()):
            raise PolicyFailure("escalade needs Helmgart's capture points") \
                from ValueError(sorted(points))
        pieces = {p["id"]: p for p in mode.get("fortifications") or []}
        walls = [p for p in pieces.values() if p.get("kind") == "wall"]
        if GATE not in pieces or not walls:
            raise PolicyFailure("escalade needs mode.fortifications with g1 and wall pieces") \
                from ValueError(sorted(pieces))
        self.points = {name: {"x": points[name]["x"], "z": points[name]["z"]}
                       for name in POINT_KEYS}
        self.pieces = {name: {"x": p["x"], "z": p["z"], "kind": p.get("kind")}
                       for name, p in pieces.items()}
        self.line = front_line(pieces.values())
        ids = {u["id"] for u in friendly}
        crew = next((v.get("crew") for v in mode.get("vehicles") or [] if v.get("crew") in ids),
                    None)
        self.groups = groups(friendly, crew)
        self.jobs = {identity: "climb" for name in ASSAULT for identity in self.groups[name]}
        self.jobs.update({identity: "reserve" for identity in self.groups["reserve"]})
        self.jobs.update({identity: "horse" for identity in self.groups["horse"]})
        units = {u["id"]: u for u in friendly}
        for identity in self.groups["centre"]:
            kind = units[identity]["type"]
            self.jobs[identity] = ("ram" if identity == crew else "gun" if kind == GROM
                                   else "shoot" if kind == STRELTSI else "climb")
        # Each climbing target is the wall piece nearest its point; ties go to the smaller id.
        for name in ASSAULT:
            point = self.points[self.target_points[name]]
            self.targets[name] = min(walls, key=lambda p: (distance(p, point), p["id"]))["id"]
        gate = self.pieces[GATE]
        for name in ASSAULT:
            anchor = (gate if name == "centre" or not self.ladders
                      else self.pieces[self.targets[name]])
            self._stage(name, [units[i] for i in self.groups[name]], anchor)
        if not self.ladders:  # the reserve waits with the infantry
            self._stage("reserve", [units[i] for i in self.groups["reserve"]], gate)
        for identity in self.groups["horse"]:
            self.spots[identity] = self._spot(gate, 0, 1, HORSE_M)

    def _spot(self, anchor, index, count, south):
        spot = {"x": round(anchor["x"] + (index - (count - 1) / 2) * SPACING_M, 1),
                "z": round(anchor["z"] - south, 1)}
        spot["facing"] = bearing(spot, anchor)
        return spot

    def _stage(self, name, members, anchor, south=STAGING_M):
        members = sorted(members, key=lambda u: (u["x"], u["z"]))
        for index, unit in enumerate(members):
            self.spots[unit["id"]] = self._spot(anchor, index, len(members), south)

    # Sending, with cannae.py Envelop._send's rule: repeat an order only when the engine dropped it.
    def _send(self, unit, order):
        identity, idle = unit["id"], "idle" in (unit.get("state") or [])
        lapsed = (idle and distance(unit, order) > ARRIVED_M if order["type"] == "move"
                  else idle or order["type"] == "attack" and not unit.get("target"))
        if self.sent.get(identity) == order and not (
                lapsed and self.now - self.last_sent[identity] >= RETRY_MS):
            return []
        self.sent[identity], self.last_sent[identity] = order, self.now
        return [order]

    def _move(self, unit, spot, run=RUN):
        self.kept.pop(unit["id"], None)
        return self._send(unit, {"unit": unit["id"], "type": "move", "x": spot["x"],
                                 "z": spot["z"], "facing": spot.get("facing"), "width": None,
                                 "run": run, "queue": False})

    def _attack(self, unit, target, mode="auto"):
        self.kept[unit["id"]] = target["id"]
        return self._send(unit, {"unit": unit["id"], "type": "attack", "target": target["id"],
                                 "mode": mode, "run": RUN, "queue": False})

    def _siege(self, unit, kind, target):
        self.kept.pop(unit["id"], None)
        return self._send(unit, {"unit": unit["id"], "type": kind, "target": target, "run": RUN})

    def _target(self, unit, enemies):
        """The enemy this unit attacks: the one it already attacks while still able and visible,
        else the nearest."""
        kept = next((e for e in enemies if e["id"] == self.kept.get(unit["id"])), None)
        return kept or _nearest(unit, enemies)

    # Cues.
    def _breached(self, mode):
        """The public gate nearest g1 is breached, or the Gatehouse point is ours."""
        gates = [g for g in mode.get("gates") or [] if g.get("x") is not None]
        gate = _nearest(self.pieces[GATE], gates)
        point = next((p for p in mode.get("capture_points") or [] if p.get("id") == GATEHOUSE), {})
        return bool(gate and gate_breached(gate)) or holds(point, "us")

    def _staged(self, name, units):
        members = [units[i] for i in self.groups[name] if i in units and able(units[i])]
        return all(distance(u, self.spots[u["id"]]) <= ARRIVE_M for u in members)

    def _start_phase2(self, units):
        names = [name for name in ASSAULT if name not in self.phase2]
        if self.together:
            if not names:
                return
            if all(self._staged(name, units) for name in ASSAULT):
                reason = "staged"
            elif self.now >= PHASE2_MS:
                reason = "time"
            else:
                return
            self.phase2_reason = self.phase2_reason or reason
            started = names
        else:
            started = [name for name in names
                       if self._staged(name, units) or self.now >= PHASE2_MS]
        for name in started:
            self.phase2[name] = self.now
            self.men0[name] = sum((units.get(i) or {}).get("men") or 0 for i in self.groups[name])

    def _choose_reserve(self, units):
        """RESERVE_MS after the first phase 2: the group that lost the largest share of its men
        if over RESERVE_LOSS, else the one with most units on the wall; ties in ASSAULT order."""
        if self.reserve is not None or not self.phase2:
            return
        if self.now < min(self.phase2.values()) + RESERVE_MS:
            return
        started = [name for name in ASSAULT if name in self.phase2]

        def loss(name):
            now = sum((units.get(i) or {}).get("men") or 0 for i in self.groups[name])
            return 1 - now / self.men0[name] if self.men0[name] else 0

        def on_wall(name):
            return sum(1 for i in self.groups[name] if (units.get(i) or {}).get("on_wall"))

        worst = max(started, key=lambda name: (loss(name), -ASSAULT.index(name)))
        self.reserve = (worst if loss(worst) > RESERVE_LOSS else
                        max(started, key=lambda name: (on_wall(name), -ASSAULT.index(name))))
        self.reserve_ms = self.now

    def _victory_point(self, unit, mode):
        held = {p.get("id"): p for p in mode.get("capture_points") or []}
        for tier in self.victory_tiers:
            open_points = [name for name in tier if not holds(held.get(name, {}), "us")]
            if open_points:
                return min((self.points[name] for name in open_points),
                           key=lambda p: (distance(unit, p), p["x"]))
        return self.points[self.victory_tiers[-1][-1]]

    # Each unit's order.
    # JUDGEMENT?: After a target falls — Claude, 2026-11-08: a climber or crew whose target reads 0%
    # walks in (phase 3), the Grom stops, C3's units attack; the design is silent. The Grom firing
    # in the town ("light guns for the town") changes the late battle; checks 5 and 6 rest on it.
    def _besiege(self, unit, target, mode):
        """Besiege ``target`` while this observation lists it above 0%; once it reads 0% walk
        in as in phase 3; while it is not listed, no order (protocol._validate_siege's rule)."""
        piece = self.fort.get(target)
        if piece is None:
            return []
        if gate_breached(piece):
            return self._move(unit, self._victory_point(unit, mode))
        return self._siege(unit, "besiege", target)

    def _climb(self, unit, group, mode):
        """Besiege ``group``'s climbing target, or stand at the unit's spot if it cannot climb."""
        if self.ladders and unit.get("can_climb") is True:
            return self._besiege(unit, self.targets[group], mode)
        return self._move(unit, self.spots.get(unit["id"]) or self.spots[self.groups[group][0]],
                          run=False)

    def _assault(self, unit, job, group, enemies, mode):
        if group not in self.phase2:
            return self._move(unit, self.spots[unit["id"]], run=False)
        if job == "ram":
            return self._besiege(unit, GATE, mode)
        if job == "gun":
            gate = self.fort.get(GATE)
            if (gate is not None and not gate_breached(gate) and unit.get("can_siege") is True
                    and unit.get("ammo")):
                return self._siege(unit, "attack_building", GATE)
            return []
        if not self.ladders:  # GateOnly: the Streltsi wait with the rest of the infantry
            return self._move(unit, self.spots[unit["id"]], run=False)
        if job == "shoot":
            gate, reach_m = self.pieces[GATE], unit.get("range") or 0
            reach = [e for e in enemies if distance(e, gate) <= reach_m]
            return self._attack(unit, self._target(unit, reach)) if reach else []
        return self._climb(unit, group, mode)

    def _horse(self, unit, enemies, mode):
        if self.gate_open_ms is None:
            return self._move(unit, self.spots[unit["id"]], run=False)
        c7 = next((p for p in mode.get("capture_points") or [] if p.get("id") == "c7"), {})
        return self._move(unit, self.points["c1" if holds(c7, "us") else "c7"])

    def _unit(self, unit, job, group, enemies, mode, entered):
        """The order for one able unit (a list of at most one)."""
        if self.phase4_ms is not None and enemies:
            return self._attack(unit, self._target(unit, enemies))
        if job == "horse":
            return self._horse(unit, enemies, mode)
        if unit.get("on_wall") or inside(self.line, unit) or (entered and job != "gun"):
            return self._move(unit, self._victory_point(unit, mode))
        if job == "reserve":
            if not self.ladders:
                return self._move(unit, self.spots[unit["id"]], run=False)
            if self.reserve is None:
                return []
            return self._climb(unit, self.reserve, mode)
        return self._assault(unit, job, group, enemies, mode)

    def decide(self, observation):
        self.now = observation["time_ms"]
        if self.groups is None:
            self._bind(observation)
        mode = observation.get("mode") or {}
        self.fort = {p.get("id"): p for p in mode.get("fortifications") or []}
        units = friendly_units(observation)
        enemies = [e for e in visible_enemies(observation).values() if able(e)]
        if self.gate_open_ms is None and self._breached(mode):
            self.gate_open_ms = self.now
        self._start_phase2(units)
        self._choose_reserve(units)
        inside_now = sum(1 for u in units.values() if able(u) and inside(self.line, u))
        if self.phase4_ms is None and inside_now >= INSIDE_UNITS:
            self.phase4_ms = self.now
        # GateOnly's infantry enters once the gate is breached.
        entered = not self.ladders and self.gate_open_ms is not None
        orders = []
        for name, members in self.groups.items():
            for identity in members:
                unit = units.get(identity)
                if unit is not None and able(unit):
                    orders += self._order(unit, self.jobs[identity], name, enemies, mode, entered)
        return orders

    def _order(self, unit, job, group, enemies, mode, entered):
        return self._unit(unit, job, group, enemies, mode, entered)

    def acknowledge(self, ack, latency):
        for result in ack.get("results", []):
            if not result.get("ok"):
                self.sent.pop(result.get("unit"), None)

    def metadata(self):
        return deepcopy({"type": self.arm, "version": 1, "groups": self.groups, "jobs": self.jobs,
                         "targets": self.targets, "phase2_ms": self.phase2,
                         "phase2_reason": self.phase2_reason, "reserve": self.reserve,
                         "reserve_ms": self.reserve_ms, "gate_open_ms": self.gate_open_ms,
                         "phase4_ms": self.phase4_ms})


class Concentrate(Escalade):
    """concentrate (C6, D1's arm): the witness, except that West's and East's climbing targets
    are the wall pieces nearest c5 and c4, in the gate recess, staged as the witness stages."""

    arm = "concentrate"
    target_points = CONCENTRATE_POINTS


class CavalryEarly(Escalade):
    """cavalry_early (C7, D2's arm): the witness, except that until the gate is breached the
    Lancers ride to GATE_FRONT_M south of g1 from the start and attack the visible enemy nearest
    them within EARLY_M."""

    arm = "cavalry_early"

    def _horse(self, unit, enemies, mode):
        if self.gate_open_ms is not None:
            return super()._horse(unit, enemies, mode)
        near = [e for e in enemies if distance(unit, e) <= EARLY_M]
        if near:
            return self._attack(unit, self._target(unit, near))
        gate = self.pieces[GATE]
        return self._move(unit, {"x": gate["x"], "z": round(gate["z"] - GATE_FRONT_M, 1),
                                 "facing": 0})


class Piecemeal(Escalade):
    """piecemeal (C8, exploratory): the witness, except that each group besieges as soon as it
    is staged (or at PHASE2_MS), and the reserve's clock starts with the first group."""

    arm = "piecemeal"
    together = False


class ShootOnly(Escalade):
    """shoot_only (C4): every unit with ammunition stands SHOOT_M south of its target (the
    reserve's: g1) and attacks, ranged, the visible enemy nearest it within its range; once its
    ammunition is gone it plays as the witness."""

    arm = "shoot_only"

    def _bind(self, observation):
        super()._bind(observation)
        units = friendly_units(observation)
        self.firing = {}
        for name in (*ASSAULT, "reserve"):
            anchor = (self.pieces[GATE] if name in ("centre", "reserve")
                      else self.pieces[self.targets[name]])
            members = sorted((units[i] for i in self.groups[name]),
                             key=lambda u: (u["x"], u["z"]))
            for index, unit in enumerate(members):
                self.firing[unit["id"]] = self._spot(anchor, index, len(members), SHOOT_M)

    def _order(self, unit, job, group, enemies, mode, entered):
        if not unit.get("ammo") or unit["id"] not in self.firing:
            return super()._order(unit, job, group, enemies, mode, entered)
        spot = self.firing[unit["id"]]
        reach = [e for e in enemies if distance(unit, e) <= (unit.get("range") or 0)]
        if distance(unit, spot) <= ARRIVED_M and reach:
            return self._attack(unit, self._target(unit, reach), mode="ranged")
        return self._move(unit, spot, run=False)


class GateOnly(Escalade):
    """gate_only (C5): no ladders. The infantry (the Streltsi hold their fire) and the reserve
    wait STAGING_M south of g1, the crew besieges and the Grom attacks g1 in phase 2, and once
    the gate is breached (or the Gatehouse point is ours, the Horse's cue) every unit but the
    Grom goes in to the victory points; the Horse plays as the witness."""

    arm = "gate_only"
    ladders = False


class BesiegeNearest:
    """besiege_nearest (C3): from the first decision every unit that can climb besieges the wall
    piece nearest its start, the ram's crew besieges g1 and the Grom attacks it, the Lancers and
    the Boyar attack the visible enemy nearest them, and a unit on the wall or inside the front
    line, or whose target reads 0%, attacks the visible enemy nearest it. No staging, timing or
    reserve."""

    arm = "besiege_nearest"

    def __init__(self):
        self.plan = self.line = None
        self.sent, self.last_sent, self.kept = {}, {}, {}
        self.fort = {}
        self.now = 0

    _send = Escalade._send
    _attack = Escalade._attack
    _siege = Escalade._siege
    _target = Escalade._target

    def _bind(self, observation):
        friendly = observation.get("friendly") or []
        mode = observation.get("mode") or {}
        pieces = {p["id"]: p for p in mode.get("fortifications") or []}
        walls = [p for p in pieces.values() if p.get("kind") == "wall"]
        if GATE not in pieces or not walls:
            raise PolicyFailure("besiege_nearest needs mode.fortifications with g1 and walls") \
                from ValueError(sorted(pieces))
        self.line = front_line(pieces.values())
        ids = {u["id"] for u in friendly}
        crew = next((v.get("crew") for v in mode.get("vehicles") or [] if v.get("crew") in ids),
                    None)
        self.plan = {}
        for unit in friendly:
            if unit["id"] == crew:
                self.plan[unit["id"]] = ("besiege", GATE)
            elif unit.get("type") == GROM:
                self.plan[unit["id"]] = ("attack_building", GATE)
            elif unit.get("type") in (LANCERS, BOYAR) or unit.get("can_climb") is not True:
                self.plan[unit["id"]] = ("attack", None)
            else:
                nearest = min(walls, key=lambda p: (distance(p, unit), p["id"]))
                self.plan[unit["id"]] = ("besiege", nearest["id"])

    def decide(self, observation):
        self.now = observation["time_ms"]
        if self.plan is None:
            self._bind(observation)
        self.fort = {p.get("id"): p
                     for p in (observation.get("mode") or {}).get("fortifications") or []}
        units = friendly_units(observation)
        enemies = [e for e in visible_enemies(observation).values() if able(e)]
        orders = []
        for identity, (kind, target) in self.plan.items():
            unit = units.get(identity)
            if unit is None or not able(unit):
                continue
            piece = self.fort.get(target)
            if (kind == "attack" or piece is not None and gate_breached(piece)
                    or unit.get("on_wall") or inside(self.line, unit)):
                if enemies:
                    orders += self._attack(unit, self._target(unit, enemies))
            elif piece is None:  # mode.fortifications not read this time: protocol refuses
                continue
            elif kind == "attack_building":
                if unit.get("can_siege") is True and unit.get("ammo"):
                    orders += self._siege(unit, kind, target)
            else:
                orders += self._siege(unit, kind, target)
        return orders

    acknowledge = Escalade.acknowledge

    def metadata(self):
        return deepcopy({"type": self.arm, "version": 1, "plan": self.plan})


class EscaladeReplay(ReplaySchedule):
    """escalade_replay (C9, exploratory): replay_schedule.ReplaySchedule over a witness win,
    whose besiege and attack_building orders keep their fortification ids (ids follow kind and
    centre, so they name the same pieces on the same map) and are dropped when the target is
    not listed now or reads 0% (gate_breached)."""

    def decide(self, observation):
        self._fortifications = {p.get("id"): p for p in
                                (observation.get("mode") or {}).get("fortifications") or []}
        return super().decide(observation)

    def _remap(self, entry, friendly, enemies):
        order = entry["order"]
        if order.get("type") not in SIEGE_ORDER_TYPES:
            return super()._remap(entry, friendly, enemies)
        unit = self.units.get(order["unit"])
        piece = self._fortifications.get(order.get("target"))
        if unit not in friendly or piece is None or gate_breached(piece):
            return None
        return {**order, "unit": unit}


# A port of tests/twwarhammer3/checkpoint_siege/assault.lua (the 2026-11-03 siege checkpoint,
# runs/twwarhammer3/siege-905-20261103), sent as the mod's besiege and attack_building orders in
# place of its unit controllers, with its timing and its move-fast flags.
class OrderProbe:
    """order_probe: stage 2's order-effect probe (escalade-eval.md, step 0b), a diagnostic and
    not an arm; no ablation diff or screen uses it. At order_ms the westmost Armoured Kossars and
    the westmost Kossars (Spears) besiege the wall piece nearest their start and the ram's crew
    besieges g1, all three at a run, and the Grom attacks g1 (attack_building, not at a run). No
    other order is given. A siege order is resent only when its unit reads idle RETRY_MS after
    the last send (Escalade._send). An order validation would refuse (a target not listed now or
    at 0%, a wall for a unit without can_climb, the Grom without can_siege or ammunition) is not
    sent. The metadata lists the battle times at which each unit's order was sent."""

    arm = "order_probe"
    order_ms = 10000  # assault.lua's bm:callback delay

    def __init__(self):
        self.plan = None
        self.sent, self.last_sent, self.kept = {}, {}, {}
        self.sent_ms = {}  # unit -> the battle ms of each send
        self.now = 0

    _send = Escalade._send
    acknowledge = Escalade.acknowledge

    def _bind(self, observation):
        friendly = sorted(observation.get("friendly") or [], key=lambda u: (u["x"], u["z"]))
        mode = observation.get("mode") or {}
        pieces = {p["id"]: p for p in mode.get("fortifications") or []}
        walls = [p for p in pieces.values() if p.get("kind") == "wall"]
        if GATE not in pieces or not walls:
            raise PolicyFailure("order_probe needs mode.fortifications with g1 and walls") \
                from ValueError(sorted(pieces))
        ids = {u["id"] for u in friendly}
        crew = next((v.get("crew") for v in mode.get("vehicles") or [] if v.get("crew") in ids),
                    None)
        self.plan = {}  # unit -> (order type, target, run)
        # JUDGEMENT?: Probe units — Claude, 2026-11-09: assault.lua's one wall besieger (item 5)
        # becomes the westmost Armoured Kossars and Kossars (Spears) at the start; another pick
        # (list order) may climb another piece. Stage 2's check 3 readings rest on it.
        for kind in (ARMOURED, SPEARS):
            climber = next((u for u in friendly if u["type"] == kind and u["id"] != crew), None)
            if climber is not None:
                wall = min(walls, key=lambda p, u=climber: (distance(p, u), p["id"]))
                self.plan[climber["id"]] = ("besiege", wall["id"], True)
        if crew is not None:
            self.plan[crew] = ("besiege", GATE, True)
        for unit in friendly:
            if unit["type"] == GROM:
                self.plan[unit["id"]] = ("attack_building", GATE, False)

    def decide(self, observation):
        self.now = observation["time_ms"]
        if self.plan is None:
            self._bind(observation)
        if self.now < self.order_ms:
            return []
        fort = {p.get("id"): p
                for p in (observation.get("mode") or {}).get("fortifications") or []}
        units = friendly_units(observation)
        orders = []
        for identity, (kind, target, run) in self.plan.items():
            unit, piece = units.get(identity), fort.get(target)
            if unit is None or not able(unit) or piece is None or gate_breached(piece):
                continue
            if (kind == "besiege" and piece.get("kind") == "wall"
                    and unit.get("can_climb") is not True):
                continue
            if kind == "attack_building" and (unit.get("can_siege") is not True
                                              or not unit.get("ammo")):
                continue
            sent = self._send(unit, {"unit": identity, "type": kind, "target": target, "run": run})
            if sent:
                self.sent_ms.setdefault(identity, []).append(self.now)
            orders += sent
        return orders

    def metadata(self):
        return deepcopy({"type": self.arm, "version": 1, "plan": self.plan,
                         "sent_ms": self.sent_ms})


# Witness version 2 (module docstring): options for owner question 6 on escalade-eval.md, in no
# plan until the owner picks them; version 1 above stays the default.
# JUDGEMENT: Witness v2 victory order — Claude, 2026-11-09 (owner question 6(a)): c7, then c1, on
# the 4 drains recorded with the player defending. Keeping c8 and c9 (v1) adds about 520 m a unit;
# version 2's phase 3, and phase 4 with no enemy in view, rest on it.
VICTORY_TIERS_V2 = (("c7",), ("c1",))


# JUDGEMENT: Witness v2 door rule — Claude, 2026-11-09 (owner question 6(b)): g1 counts as fallen
# once its door reads hp 0, and a unit still on a g1 siege order is halted. Keying on the building
# (v1) keeps both at an open gate until it falls; version 2's breach play and checks 5-6 rest on it.
def door_view(observation, breached=False):
    """``observation`` with g1 at hp 0 in mode.fortifications once the public gate nearest g1 (its
    door) reads hp 0 or less, else ``observation`` itself. ``breached`` retains a breach seen
    earlier, so a missing door read cannot restart attacks on g1. Rules keyed on g1 at 0% then
    treat it as fallen; validation reads the true list, so this only takes orders on g1 away."""
    mode = observation.get("mode") or {}
    pieces = mode.get("fortifications") or []
    gate = next((p for p in pieces if p.get("id") == GATE), None)
    if gate is None or gate_breached(gate):
        return observation
    if not breached:
        door = _nearest(gate, [g for g in mode.get("gates") or [] if g.get("x") is not None])
        if not door or not gate_breached(door):
            return observation
    fallen = [{**p, "hp": 0} if p is gate else p for p in pieces]
    return {**observation, "mode": {**mode, "fortifications": fallen}}


def door_halts(policy, view, orders):
    """Retry pending door halts for able units that get no replacement order this decision.

    The engine keeps a standing attack_building in force: in
    siege-905-20261103's helmgart-defender recording the AI's Great Cannon, ordered once at 10 s,
    went from 55 to 52 ammunition between the readings at 120 s (the door's first at 0) and 150 s
    (the building's first at 0), then stayed at 52 to 240 s. Whether a halt ends such an order is
    unread."""
    if not policy.breached:
        return []
    units, halts = friendly_units(view), []
    replaced = {order["unit"] for order in orders}
    for identity in policy.gate_orders:
        unit = units.get(identity)
        if unit is not None and able(unit) and identity not in replaced:
            halts += policy._send(unit, {"unit": identity, "type": "halt"})
    return halts


class _DoorBreach:
    """V2's door view and halt delivery, shared by the witness and BesiegeNearest."""

    def __init__(self):
        super().__init__()
        # Last accepted g1 orders, preserving insertion order when issuing their halts.
        self.gate_orders = {}
        self.breached = False

    def decide(self, observation):
        view = door_view(observation, self.breached)
        gate = next((p for p in (view.get("mode") or {}).get("fortifications") or []
                     if p.get("id") == GATE), None)
        if gate is not None and gate_breached(gate):
            self.breached = True
        orders = super().decide(view)
        return orders + door_halts(self, view, orders)

    def acknowledge(self, ack, latency):
        super().acknowledge(ack, latency)
        for result in ack.get("results", []):
            if result.get("ok"):
                identity = result.get("unit")
                order = self.sent.get(identity) or {}
                if order.get("type") in SIEGE_ORDER_TYPES and order.get("target") == GATE:
                    self.gate_orders[identity] = None
                else:
                    self.gate_orders.pop(identity, None)


class Version2(_DoorBreach):
    """Version 2's three changes (module docstring), mixed in before a version 1 Escalade class."""

    victory_tiers = VICTORY_TIERS_V2

    # JUDGEMENT: Witness v2 staging — Claude, 2026-11-09 (owner question 6(c)): flank rows go south
    # to 150 m from every piece, 40 m from earlier spots (fixture approach: Concentrate 188-194 m,
    # Escalade 156-161 m). V1's rows (117 m off, 16 m apart) change D1, whose contrast rests on it.
    def _bind(self, observation):
        super()._bind(observation)
        placed = [self.spots[i] for name in ("horse", "centre") for i in self.groups[name]]
        for name in ("west", "east") if self.ladders else ("west", "east", "reserve"):
            anchor = self.pieces[self.targets[name] if self.ladders else GATE]
            row = [self.spots[i] for i in self.groups[name]]
            z = row[0]["z"]
            while not self._clear(row, z, placed):
                z = round(z - 1, 1)
            for spot in row:
                spot.update(z=z, facing=bearing({"x": spot["x"], "z": z}, anchor))
            placed += row

    def _clear(self, row, z, placed):
        """Whether ``row``'s spots, moved to ``z``, stand STAGING_M or more from every listed piece
        and SPACING_M or more from every spot in ``placed``."""
        spots = [{"x": spot["x"], "z": z} for spot in row]
        return (all(distance(s, p) >= STAGING_M for s in spots for p in self.pieces.values())
                and all(distance(s, p) >= SPACING_M for s in spots for p in placed))

    def metadata(self):
        return {**super().metadata(), "version": 2}


class EscaladeV2(Version2, Escalade):
    """escalade, version 2."""


class ConcentrateV2(Version2, Concentrate):
    """concentrate, version 2: D1's arm B against EscaladeV2."""


class CavalryEarlyV2(Version2, CavalryEarly):
    """cavalry_early, version 2."""


class PiecemealV2(Version2, Piecemeal):
    """piecemeal, version 2."""


class ShootOnlyV2(Version2, ShootOnly):
    """shoot_only, version 2; its firing spots are version 1's."""


class GateOnlyV2(Version2, GateOnly):
    """gate_only, version 2: its West, East and reserve rows also move south (rule (c))."""


class BesiegeNearestV2(_DoorBreach, BesiegeNearest):
    """besiege_nearest, version 2: once g1's door reads hp 0 (door_view) its crew and Grom attack
    the visible enemy nearest them, as for a target at 0%, and with none in view get a halt
    (door_halts)."""

    def metadata(self):
        return {**super().metadata(), "version": 2}
