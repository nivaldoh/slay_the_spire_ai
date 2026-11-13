"""Scripted witness and two controls for the two-front land defence (ksl-nor-lines-a-v1, -b-v1).

Design: final-alesia.md "Witness and its arms" in runs/siege-evals-20261108 (untracked). Every arm
reads public state only: its own units, the visible enemies, the terrain grid and the battle time.
W also reads COST, a fixed table of lobby costs that no model is told (see its marker).
Roles bind once, at the first observation, from each unit's type and start position, never from
unit ids or later positions:
- the Kossars, Armoured Kossars and Streltsi split at the midpoint of their start z into the inner
  line (three regiments, north) and the outer line (five, south). The outer line's two westmost
  regiments are its west sector and its two eastmost the east sector; the middle one is in neither;
- the Tzar Guard and the Boyar are the reserve, the two Winged Lancers the Lancers.
Each regiment keeps its start position as its post. It attacks a visible enemy only when that
enemy is within LEASH_M of its post, and goes back when it is more than RETURN_M from it. The line
regiments set guard and fire at will on and skirmish off.

The arms differ in one rule, the side the reserve and the Lancers go to:
- LinesWitness (W): the side whose visible relief units cost more (COST);
- LinesByMen (M): the side whose visible relief units have more men;
- LinesCentral (C): neither; the reserve and the Lancers keep their start posts.
W and M choose the first time TRIGGER_UNITS enemies stand more than AHEAD_M ahead of the outer
line, the sides split at the outer line's centre x, and switch only when the other side scores
SWITCH times as much. A tie chooses nothing yet. The reserve then posts behind the chosen sector.
The Lancers wait at their posts until ENGAGED_UNITS relief units on that side are in melee, then
ride round the line's end to REAR_M behind one of them, measured along the outer line's front,
and charge, with calibration.HammerAnvil's cycle and values. Target keeping follows SMAC
smac/env/starcraft2/starcraft2.py get_agent_action_heuristic (keep a target until it is
unavailable), as cannae.py does.

Options for owner question 4 in lines-eval.md, built beside the three arms on 2026-11-09 and in
no plan until the owner picks them:
- LinesNoCounterstroke (N) and LinesNoCounterstrokeByMen (NM): W and M with the Lancers kept on
  their start leash, as in C, so the two differ only in the reserve's orders;
- LinesCornerCamp: a control that stands the whole army in two ranks at CornerHold's corner post.
Offline tests show what the scripts order, not what the engine does with the orders.
"""

from collections import Counter
from copy import deepcopy

from twwarhammer3.battle.calibration import (
    CornerHold,
    SmallDiagnostic,
    _centre,
    _direction,
    _keep,
    _offset,
)
from twwarhammer3.battle.evidence_rules import ids_by_type, in_melee
from twwarhammer3.battle.scripted import distance
from twwarhammer3.protocol import PolicyFailure, visible_enemies

KOSSARS = "wh3_main_ksl_inf_kossars_1"
ARMOURED = "wh3_main_ksl_inf_armoured_kossars_0"
STRELTSI = "wh3_main_ksl_inf_streltsi_0"
GUARD = "wh3_main_ksl_inf_tzar_guard_0"
BOYAR = "wh3_main_ksl_cha_boyar_0"
LANCERS = "wh3_main_ksl_cav_winged_lancers_0"
ARMY = Counter({KOSSARS: 3, ARMOURED: 3, STRELTSI: 2, GUARD: 1, BOYAR: 1, LANCERS: 2})
LINE = (KOSSARS, ARMOURED, STRELTSI)
LINE_BEHAVIOURS = {"defend": True, "fire_at_will": True, "skirmish": False}

# JUDGEMENT: Lines witness rules — Claude, 2026-11-08 (final-alesia.md Witness rules 1-5): the
# values below. Other leashes, trigger, hysteresis or Lancer values change what W, M and C win;
# the W against M contrast and the witness gate rest on them.
LEASH_M = 40  # a regiment attacks only enemies this close to its post
RETURN_M = 15  # and goes back to its post when farther from it than this
AHEAD_M = 60  # an enemy first seen this far ahead of the outer line is a relief unit
TRIGGER_UNITS = 6  # W and M choose a side once this many enemies stand that far ahead
SWITCH = 1.3  # and switch only when the other side scores this many times as much
RESERVE_BEHIND_M = 30  # the Tzar Guard's post behind the chosen sector's centre
BOYAR_BEHIND_M = 15  # the Boyar's post behind the Tzar Guard's
ENGAGED_UNITS = 2  # relief units in melee on the chosen side before the Lancers ride
OUTSIDE_M = 110  # the Lancers' waypoint past the line's end regiment (20 m half width + 90 m)
OUTSIDE_AHEAD_M = 10  # and this far ahead of the outer line
# HammerAnvil's values: charge from REAR_M behind the target after arriving within ARRIVED_M of
# each point; pull out after CONTACT_S of melee, or the target's rout, to RETREAT_M from the
# nearest enemy; wait again after REGROUP_S[1] s, or REGROUP_S[0] s once none is within CLEAR_M.
REAR_M = 70
ARRIVED_M = 25
CONTACT_S = 8
RETREAT_M = 120
REGROUP_S = (10, 20)
CLEAR_M = 80

# JUDGEMENT: Lines side weights — Claude, 2026-11-08: W weighs a relief unit by its lobby cost,
# which no model is told (lines-eval.md Lines briefing), so W knows more than a model does. A
# public weight changes what W against M measures; that contrast and W's side choice rest on it.
# main_units_tables multiplayer_cost, read 2026-11-08 with scripts/wh3_db.py, for every enemy type.
COST = {
    "wh_main_nor_inf_chaos_marauders_0": 400,
    "wh_dlc08_nor_inf_marauder_spearman_0": 425,
    "wh_dlc08_nor_inf_marauder_hunters_0": 550,
    "wh_main_nor_cav_marauder_horsemen_0": 600,
    "wh_dlc08_nor_inf_marauder_berserkers_0": 750,
    "wh_dlc08_nor_inf_marauder_champions_0": 1000,
    "wh_dlc08_nor_mon_fimir_0": 1150,
}


class LinesWitness(SmallDiagnostic):
    """W: hold both lines; send the reserve and the Lancers to the side whose relief costs more."""

    arm = "W"
    rule = "cost"

    def __init__(self):
        super().__init__()
        self.roles = self.posts = self.facing = self.types = None
        self.sectors, self.reserve_posts, self.waypoints = {}, {}, {}
        self.forward = self.outer = None
        # JUDGEMENT?: Relief membership — Claude, 2026-11-08: an enemy is a relief unit when first
        # seen more than AHEAD_M ahead of the outer line, kept by id. Scoring every enemy by its
        # current side lets the town-side group start the Lancers or switch the side.
        self.first = {}
        self.side = self.side_s = self.scores = None
        self.switches = []
        self.targets = {}
        self.lancers = {"phase": "wait", "target": None, "contact_s": None, "since_s": None,
                        "retreat": None, "threat": None, "charges": 0}

    # Every refusal here carries a cause, which ends the episode (play.is_forfeit): a bare
    # PolicyFailure is a forfeit, and the army would stand on its last orders and could win at
    # the timer (owner, 2026-11-13: "End the battle"; as Evade and Escalade do). Rests on
    # JUDGEMENT? play.py Forfeit split, which reads a bare PolicyFailure as a forfeit.
    def _bind(self, units):
        if Counter(u.get("type") for u in units) != ARMY or any(
                u.get("x") is None or u.get("z") is None for u in units):
            raise PolicyFailure("the lines witness needs the declared Kislev army, placed") \
                from ValueError(dict(Counter(u.get("type") for u in units)))
        line = [u for u in units if u["type"] in LINE]
        middle = (max(u["z"] for u in line) + min(u["z"] for u in line)) / 2
        inner = [u for u in line if u["z"] > middle]
        outer = sorted((u for u in line if u["z"] <= middle), key=lambda u: u["x"])
        if len(inner) != 3 or len(outer) != 5:
            raise PolicyFailure("the lines witness needs three regiments north, five south") \
                from ValueError({"north": len(inner), "south": len(outer)})
        self.roles = {"inner": [u["id"] for u in inner], "outer": [u["id"] for u in outer],
                      "reserve": ids_by_type(units, {GUARD, BOYAR}),
                      "lancers": ids_by_type(units, {LANCERS})}
        self.types = {u["id"]: u["type"] for u in units}
        self.posts = {u["id"]: {"x": u["x"], "z": u["z"]} for u in units}
        inner_centre, self.outer = _centre(inner), _centre(outer)
        self.forward = _direction(inner_centre, self.outer)  # the outer line's front
        back = (-self.forward[0], -self.forward[1])
        self.facing = {u["id"]: back if u["id"] in self.roles["inner"] else self.forward
                       for u in units}
        for side, regiments, end in (("west", outer[:2], outer[0]),
                                     ("east", outer[-2:], outer[-1])):
            centre = self.sectors[side] = _centre(regiments)
            self.reserve_posts[side] = {
                GUARD: _offset(centre, self.forward, -RESERVE_BEHIND_M),
                BOYAR: _offset(centre, self.forward, -RESERVE_BEHIND_M - BOYAR_BEHIND_M)}
            outside = _offset(end, _direction(self.outer, end), OUTSIDE_M)
            self.waypoints[side] = _offset(outside, self.forward, OUTSIDE_AHEAD_M)

    def _ahead(self, unit):
        """Metres ``unit`` stands ahead of the outer line's start centre, along its front."""
        return ((unit["x"] - self.outer["x"]) * self.forward[0]
                + (unit["z"] - self.outer["z"]) * self.forward[1])

    def _side_of(self, unit):
        split = self.outer["x"]
        return "west" if unit["x"] < split else "east" if unit["x"] > split else None

    def _weight(self, enemy):
        if self.rule == "men":
            return enemy.get("men") or 0
        if enemy.get("type") not in COST:
            raise PolicyFailure(f"the lines witness has no lobby cost for {enemy.get('type')!r}") \
                from KeyError(enemy.get("type"))
        return COST[enemy["type"]]

    def _choose(self, relief, enemies):
        scores = {"west": 0, "east": 0}
        for enemy in relief:
            side = self._side_of(enemy)
            if side:
                scores[side] += self._weight(enemy)
        if self.side is None:
            ahead = sum(self._ahead(enemy) > AHEAD_M for enemy in enemies)
            if ahead >= TRIGGER_UNITS and scores["west"] != scores["east"]:
                self.side = max(scores, key=scores.get)
                self.side_s, self.scores = self.now, scores
            return
        other = "east" if self.side == "west" else "west"
        if scores[other] > SWITCH * scores[self.side]:
            self.switches.append({"time_s": self.now, "to": other, "scores": scores})
            self.side = other
            if self.lancers["phase"] in ("side", "rear"):
                self.lancers.update(phase="wait", target=None)

    def _leash(self, unit, post, enemies, facing):
        near = [enemy for enemy in enemies if distance(post, enemy) <= LEASH_M]
        if near:
            target = _keep(near, self.targets.get(unit["id"]), unit)
            self.targets[unit["id"]] = target["id"]
            return self.attack(unit, target)
        self.targets.pop(unit["id"], None)
        if distance(unit, post) > RETURN_M:
            return self.move(unit, post, _offset(post, facing, 50))
        return []

    def _settings(self, unit):
        have = unit.get("behaviours") or {}
        return [{"unit": unit["id"], "type": "behaviour", "behaviour": key, "enabled": value}
                for key, value in LINE_BEHAVIOURS.items() if key in have and have[key] != value]

    def _lancers(self, riders, relief, enemies, melee):
        """HammerAnvil's cycle on the chosen side: wait, ride to the outside waypoint, then to
        REAR_M behind an engaged relief unit, charge, pull out, and wait again."""
        state = self.lancers
        if self.side is None or not riders:
            return self._home(riders, enemies)
        mine = [enemy for enemy in relief if self._side_of(enemy) == self.side]
        group, sector = _centre(riders), self.sectors[self.side]
        target = next((enemy for enemy in mine if enemy["id"] == state["target"]), None)
        if target is None and state["phase"] in ("side", "rear"):
            state.update(phase="wait", target=None)
        if state["phase"] == "withdraw":
            elapsed = self.now - state["since_s"]
            if elapsed >= REGROUP_S[1] or elapsed >= REGROUP_S[0] and all(
                    distance(group, enemy) >= CLEAR_M for enemy in enemies):
                state.update(phase="wait", target=None)
        engaged = [enemy for enemy in mine if enemy["id"] in melee]
        if state["phase"] == "wait" and len(engaged) >= ENGAGED_UNITS:
            target = min(engaged, key=lambda enemy: distance(sector, enemy))
            state.update(phase="side", target=target["id"])
        if state["phase"] == "side" and distance(group, self.waypoints[self.side]) < ARRIVED_M:
            state["phase"] = "rear"
        # JUDGEMENT?: Lancers' rear point — Claude, 2026-11-08: REAR_M past the target along the
        # outer line's front. HammerAnvil's reading, away from the regiment the target fights,
        # differs when a target meets a regiment at an angle; where the charge lands rests on it.
        rear = target and _offset(target, self.forward, REAR_M)
        if state["phase"] == "rear" and distance(group, rear) < ARRIVED_M:
            state.update(phase="charge", contact_s=None, charges=state["charges"] + 1)
        if state["phase"] == "charge":
            if state["contact_s"] is None and any(unit["id"] in melee for unit in riders):
                state["contact_s"] = self.now
            if target is None or (state["contact_s"] is not None
                                  and self.now - state["contact_s"] >= CONTACT_S):
                threat = min(enemies, key=lambda enemy: distance(group, enemy), default=None)
                if threat is None:
                    state.update(phase="wait", target=None)
                else:
                    state.update(phase="withdraw", since_s=self.now,
                                 threat={"x": threat["x"], "z": threat["z"]},
                                 retreat=_offset(threat, _direction(threat, group), RETREAT_M))
        phase = state["phase"]
        if phase == "wait":
            return self._home(riders, enemies)
        if phase == "charge":
            return [order for unit in riders for order in self.attack(unit, target)]
        goal, look = {"side": (self.waypoints[self.side], target), "rear": (rear, target),
                      "withdraw": (state["retreat"], state["threat"])}[phase]
        return [order for unit in riders for order in self.move(unit, goal, look)]

    def _home(self, riders, enemies):
        return [order for unit in riders for order in self._leash(
            unit, self.posts[unit["id"]], enemies, self.facing[unit["id"]])]

    def decide(self, observation):
        everyone = observation.get("friendly") or []
        if self.posts is None:
            if not everyone:
                return []
            self._bind(everyone)
        elif any(unit.get("id") not in self.posts for unit in everyone):
            unbound = sorted(str(u.get("id")) for u in everyone if u.get("id") not in self.posts)
            raise PolicyFailure("the lines witness saw a unit it did not bind") \
                from ValueError(unbound)
        units, enemies = self.observe(observation)
        own = {unit["id"]: unit for unit in units}
        for enemy in visible_enemies(observation).values():
            if enemy.get("x") is not None and enemy.get("z") is not None:
                self.first.setdefault(enemy["id"], self._ahead(enemy) > AHEAD_M)
        relief = [enemy for enemy in enemies if self.first.get(enemy["id"])]
        if self.rule:
            self._choose(relief, enemies)
        orders = []
        for identity in self.roles["inner"] + self.roles["outer"]:
            if identity in own:
                unit = own[identity]
                orders += self._settings(unit) + self._leash(
                    unit, self.posts[identity], enemies, self.facing[identity])
        for identity in self.roles["reserve"]:
            if identity in own:
                post = (self.reserve_posts[self.side][self.types[identity]] if self.side
                        else self.posts[identity])
                orders += self._leash(own[identity], post, enemies, self.facing[identity])
        riders = [own[identity] for identity in self.roles["lancers"] if identity in own]
        return orders + self._lancers(riders, relief, enemies, in_melee(observation))

    def metadata(self):
        return deepcopy({"type": "lines", "arm": self.arm, "rule": self.rule,
                         "roles": self.roles, "side": self.side, "side_s": self.side_s,
                         "scores": self.scores, "switches": self.switches,
                         "lancers": {key: self.lancers[key]
                                     for key in ("phase", "target", "charges")}})


class LinesByMen(LinesWitness):
    """M: the witness with men in place of lobby cost when it chooses the side."""

    arm = "M"
    rule = "men"


class LinesCentral(LinesWitness):
    """C: the witness without a side; the reserve and the Lancers keep their start posts."""

    arm = "C"
    rule = None


# JUDGEMENT: Lines arms without the counterstroke — Claude, 2026-11-09 (owner question 4 (b), (c)):
# N and NM keep the Lancers on C's start leash. Both riding to the first melee's side would also
# leave only the reserve to differ; P1 under option (b) or (c) rests on it.
class LinesNoCounterstroke(LinesWitness):
    """N: the witness without rule 6; the Lancers keep their start posts on the leash, as in C."""

    arm = "N"

    def _lancers(self, riders, relief, enemies, melee):
        return self._home(riders, enemies)


class LinesNoCounterstrokeByMen(LinesNoCounterstroke):
    """NM: N with men in place of lobby cost when it chooses the side."""

    arm = "NM"
    rule = "men"


# JUDGEMENT: Lines corner camp — Claude, 2026-11-09 (owner question 4): CornerHold's post, then two
# ranks of six by unit id, 40 m apart across, 130 and 100 m out. Another layout changes whether a
# camp lasts to the timer; the stage 3a corner-camp control rests on it.
CAMP_ACROSS_M = 40  # between neighbours in a rank, a regiment's declared width
CAMP_FRONT_M = 130  # the front rank's distance from the post toward the map centre
CAMP_DEPTH_M = 30  # and each later rank's distance behind the one before
CAMP_RANK = 6  # units in a rank


class LinesCornerCamp(CornerHold):
    """Corner camp control: the whole army in two ranks across the nearest safe corner."""

    card = {"purpose": "Can the army win the two-front defence at the timer by camping in a "
                       "corner, without sending the reserve to either side?",
            "knowledge": "CornerHold's post rule, from the public map bounds and blocked terrain "
                         "cells, chosen once. The units, sorted by id once, stand in ranks of six "
                         "facing the map centre, 40 m apart across; the front rank stands 130 m "
                         "from the post toward the map centre and the next 30 m behind it, so on "
                         "a square corner the back rank's ends touch the 30 m line along each "
                         "edge. A unit in melee attacks the nearest enemy within 20 m and does "
                         "not move. No elevation, path search or hidden state."}

    def __init__(self):
        super().__init__()
        self.spots = None

    def decide(self, observation):
        units, enemies = self.observe(observation)
        if not units:
            return []
        if self.corner is None:
            self.corner = self.choose(observation.get("terrain") or {}, _centre(units), enemies)
            if self.corner is None:
                return []
        if self.spots is None:
            front = _direction(self.corner, self.middle)
            ids = sorted(unit["id"] for unit in units)
            self.spots = {identity: _offset(
                self.corner, front, CAMP_FRONT_M - CAMP_DEPTH_M * (index // CAMP_RANK),
                CAMP_ACROSS_M * (index % CAMP_RANK - (CAMP_RANK - 1) / 2))
                for index, identity in enumerate(ids)}
        orders = []
        for unit in units:
            if "melee" in unit.get("state", []):
                near = min(enemies, key=lambda enemy: distance(unit, enemy), default=None)
                if near and distance(unit, near) <= 20:
                    orders += self.attack(unit, near)
                continue
            if unit["id"] in self.spots:
                orders += self.move(unit, self.spots[unit["id"]], self.middle)
        return orders

    def metadata(self):
        return {"type": "lines_corner_camp", "corner": self.corner}
