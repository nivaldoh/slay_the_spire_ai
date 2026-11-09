"""Public-state witness and controls for the camp attack land battle (emp-chd-camp-v1).

The levies (Warrior Priest, Flagellants, Free Company) attack the nearest enemy from the first
decision. The mounted group (General, Empire Knights, Reiksguard) waits at its start until the
cue: one cover unit (Wolf Raiders or Bull Centaurs) has fought beside the levies for a set time.
Without a cue it starts at the fallback time. The four arms differ in one rule each:

- ``CampStrike`` (camp_strike, the witness): the mounted group takes the war machines first.
- ``CampSupport`` (camp_support): it takes the cover units fighting the levies first.
- ``CampStrikeFixed`` (camp_strike_fixed): CampStrike, starting at a fixed time instead.
- ``CampStrikeNow`` (camp_strike_now): CampStrike, starting at the first decision.

When its first list is empty, every arm attacks the nearest enemy, preferring enemies in melee
beside the levies. Rules from the 2026-11-08 camp-attack design (runs/siege-evals-20261108,
Witness and Arms and controls). Units are chosen by type key, never by class: the Magma Cannon
reads missile_chariot and the Bull Centaurs read infantry. It reads only what play.public passes
(never ``evaluation``, ``setup``, ``native`` or ``final``) and never the job. Unplayed: no game
has run it, so nothing here shows what the orders achieve.

Code reference: SMAC smac/env/starcraft2/starcraft2.py get_agent_action_heuristic keeps a target
until it is unavailable, as cannae.py does.
"""

from collections import Counter
from copy import deepcopy

from twwarhammer3.battle.evidence_rules import in_melee
from twwarhammer3.battle.local_command import able
from twwarhammer3.battle.scripted import distance
from twwarhammer3.protocol import PolicyFailure, friendly_units, visible_enemies

# JUDGEMENT: Camp groups — Claude, 2026-11-08 (camp design): groups by emp-chd-camp-v1's type keys,
# ATTACK's modes; the design sets no run for the Free Company, no mode for the mounted group. Groups
# by class, or the Free Company at a run, change both arms' play; every camp arm rests on it.
MOUNTED = {"wh_main_emp_cha_general_1": 1, "wh_main_emp_cav_empire_knights": 2,
           "wh_main_emp_cav_reiksguard": 1}
LEVIES = {"wh_main_emp_cha_warrior_priest_0": 1, "wh_dlc04_emp_inf_flagellants_0": 3,
          "wh_dlc04_emp_inf_free_company_militia_0": 2}
COVER = {"wh3_dlc23_chd_cav_hobgoblin_wolf_raiders_spears", "wh3_dlc23_chd_cav_bull_centaurs_axe"}
GUNS = {"wh3_dlc23_chd_veh_magma_cannon", "wh3_dlc23_chd_veh_deathshrieker_rocket_launcher"}
# Attack mode and run setting of each friendly type.
ATTACK = {"wh_main_emp_cha_warrior_priest_0": ("melee", True),
          "wh_dlc04_emp_inf_flagellants_0": ("melee", True),
          "wh_dlc04_emp_inf_free_company_militia_0": ("auto", False),
          **dict.fromkeys(MOUNTED, ("auto", True))}

# JUDGEMENT: Camp thresholds — Claude, 2026-11-08 (camp design cue rule): the cue is one cover unit
# in melee within 30 m of a levy for 10 s; fallback 180 s; retry 10 s; unseen gun dropped at 15 m;
# no T_fixed yet. Other values or one streak for all cover change when arms split; D1 rests on them.
CUE_M = 30
CUE_HOLD_MS = 10000
FALLBACK_MS = 180000
RETRY_MS = 10000
LOST_M = 15
FIXED_CUE_MS = None  # T_fixed: the median cue time of stage 3's launches, set before stage 5
# While it is None, CampStrikeFixed() raises. play builds the controller only after the game has
# launched (the check before launch only imports the class), so a camp_strike_fixed job started
# then ends every episode as a policy failure: start none before T_fixed is set.

# JUDGEMENT: Camp target rules — Claude, 2026-11-08: units attack visible able enemies only, keeping
# a target until it is dead, routing, shattered or unseen (the design says so for mounted units).
# Levies taking routing or nearer enemies change both arms' play; every camp arm rests on it.


def _nearest(unit, enemies):
    """The enemy nearest ``unit``; ties go to the smaller x, then z, never to id or list order."""
    return min(enemies, key=lambda e: (distance(unit, e), e["x"], e["z"]), default=None)


class CampStrike:
    """camp_strike: levies attack the nearest enemy from the start; at the cue (a cover unit
    fighting beside the levies for 10 s) or at 180 s, the mounted group attacks the nearest war
    machine, follows a hidden one to where it was last seen, then the nearest enemy."""

    arm = "camp_strike"
    first_keys = GUNS

    def __init__(self):
        self.roles = None
        self.streaks = {}
        self.cue_ms = self.start_ms = self.start_reason = None
        self.guns = {}
        self.targets, self.sent, self.last_sent = {}, {}, {}
        self.now = 0

    def _bind(self, friendly):
        """Bind once, at the first observation: each unit's group from its type, each group in
        order of its units' start positions. Neither ids nor list order change a group."""
        wanted = Counter({**MOUNTED, **LEVIES})
        if (Counter(unit.get("type") for unit in friendly) != wanted
                or any(unit.get("x") is None or unit.get("z") is None for unit in friendly)):
            # The cause ends the episode: a bare PolicyFailure is a forfeit, and the army would
            # stand for the whole battle.
            raise PolicyFailure("camp witness needs the declared ten placed units") \
                from ValueError(dict(Counter(unit.get("type") for unit in friendly)))

        def group(keys):
            return [unit["id"] for unit in sorted((u for u in friendly if u["type"] in keys),
                                                  key=lambda u: (u["x"], u["z"]))]

        self.roles = {"levies": group(LEVIES), "mounted": group(MOUNTED)}

    def _start(self):
        """Why the mounted group starts at this observation, or None while it waits."""
        if self.cue_ms is not None:
            return "cue"
        return "fallback" if self.now >= FALLBACK_MS else None

    def _first(self, enemies, engaged):
        """The mounted group's first list: visible able targets, and remembered spots to ride
        to when none is visible."""
        return ([e for e in enemies if e.get("type") in GUNS],
                [gun for gun in self.guns.values() if gun["chase"]])

    def _watch_guns(self, observation, visible, units):
        # A gun seen dead (enemy_roster), seen unable, or unseen while one of our able units
        # stands within LOST_M of its last spot is not chased; seen able again, it is.
        for enemy in visible:
            if enemy.get("type") in GUNS:
                self.guns[enemy["id"]] = {"x": enemy["x"], "z": enemy["z"], "chase": able(enemy)}
        seen = {enemy["id"] for enemy in visible}
        dead = {row["id"] for row in observation.get("enemy_roster") or [] if row.get("dead")}
        ours = [unit for unit in units.values() if able(unit)]
        for identity, gun in self.guns.items():
            if identity in dead or identity not in seen and any(
                    distance(unit, gun) <= LOST_M for unit in ours):
                gun["chase"] = False

    def _send(self, unit, order):
        # cannae.py Envelop._send: repeat an order only when the engine dropped it.
        identity, states = unit["id"], unit.get("state") or []
        lapsed = "idle" in states or order["type"] == "attack" and not unit.get("target")
        if self.sent.get(identity) == order and not (
                lapsed and self.now - self.last_sent[identity] >= RETRY_MS):
            return []
        self.sent[identity], self.last_sent[identity] = order, self.now
        return [order]

    def _attack(self, unit, target):
        if target is None:
            return []
        self.targets[unit["id"]] = target["id"]
        mode, run = ATTACK[unit["type"]]
        return self._send(unit, {"unit": unit["id"], "type": "attack", "target": target["id"],
                                 "mode": mode, "run": run, "queue": False})

    def _kept(self, identity, enemies):
        return next((e for e in enemies if e["id"] == self.targets.get(identity)), None)

    def _mounted(self, unit, enemies, engaged):
        current = self._kept(unit["id"], enemies)
        first, spots = self._first(enemies, engaged)
        if current is not None and current.get("type") in self.first_keys:
            return self._attack(unit, current)
        if first:
            return self._attack(unit, _nearest(unit, first))
        if spots:
            spot = _nearest(unit, spots)
            self.targets.pop(unit["id"], None)
            return self._send(unit, {"unit": unit["id"], "type": "move", "x": spot["x"],
                                     "z": spot["z"], "run": True, "queue": False})
        fighting = [e for e in enemies if e["id"] in engaged]
        return self._attack(unit, current or _nearest(unit, fighting or enemies))

    def decide(self, observation):
        self.now = observation["time_ms"]
        units = friendly_units(observation)
        if self.roles is None:
            self._bind(observation.get("friendly") or [])
        visible = list(visible_enemies(observation).values())
        enemies = [e for e in visible if able(e)]
        # Enemies the engine flags in melee within CUE_M of a levy unit with men left; the
        # distance test is the camp's own. Rests on JUDGEMENT evidence_rules.py Contact rule.
        levies = [units[i] for i in self.roles["levies"] if units.get(i, {}).get("men", 0) > 0]
        fighting = in_melee({"friendly": [], "enemy": visible})
        engaged = {e["id"] for e in visible if e["id"] in fighting
                   and any(distance(e, levy) <= CUE_M for levy in levies)}
        # A cover unit's streak starts at its first observation in that state and ends at the
        # first observation without it, out of sight included.
        # JUDGEMENT?: Routing cover — Claude, 2026-11-08: a routing cover unit flagged in melee
        # still counts toward the cue. Counting able cover only delays or removes some cues; the
        # cue time and so both arms' start rest on it.
        self.streaks = {e["id"]: self.streaks.get(e["id"], self.now) for e in visible
                        if e.get("type") in COVER and e["id"] in engaged}
        if self.cue_ms is None and any(self.now - since >= CUE_HOLD_MS
                                       for since in self.streaks.values()):
            self.cue_ms = self.now
        self._watch_guns(observation, visible, units)
        if self.start_ms is None and (reason := self._start()) is not None:
            self.start_ms, self.start_reason = self.now, reason
        orders = []
        for identity in self.roles["levies"]:
            unit = units.get(identity)
            if unit is not None and able(unit):
                orders += self._attack(unit, self._kept(identity, enemies)
                                       or _nearest(unit, enemies))
        if self.start_ms is not None:
            for identity in self.roles["mounted"]:
                unit = units.get(identity)
                if unit is not None and able(unit):
                    orders += self._mounted(unit, enemies, engaged)
        return orders

    def acknowledge(self, ack, latency):
        for result in ack.get("results", []):
            if not result.get("ok"):
                self.sent.pop(result.get("unit"), None)

    def metadata(self):
        return deepcopy({"type": self.arm, "version": 1, "roles": self.roles,
                         "cue_ms": self.cue_ms, "start_ms": self.start_ms,
                         "start_reason": self.start_reason, "targets": self.targets})


class CampSupport(CampStrike):
    """camp_support: camp_strike, except that the mounted group attacks the cover units
    fighting beside the levies first, and never rides to a hidden war machine."""

    arm = "camp_support"
    first_keys = COVER

    # JUDGEMENT?: Support last spot — Claude, 2026-11-08: B never rides to an unseen cover unit's
    # last spot. Reading the design's "B does the same" as including that ride changes B's play
    # once engaged cover leaves sight; the camp_strike/camp_support contrast rests on it.
    def _first(self, enemies, engaged):
        return [e for e in enemies if e.get("type") in COVER and e["id"] in engaged], []


class CampStrikeFixed(CampStrike):
    """camp_strike_fixed: camp_strike, except that the mounted group starts at a fixed battle
    time, read from no cue."""

    arm = "camp_strike_fixed"

    def __init__(self, fixed_ms=None):
        super().__init__()
        self.fixed_ms = FIXED_CUE_MS if fixed_ms is None else fixed_ms
        if self.fixed_ms is None:
            raise ValueError("camp_strike_fixed needs T_fixed: set camp.FIXED_CUE_MS from"
                             " stage 3's cue times before stage 5")

    def _start(self):
        return "fixed" if self.now >= self.fixed_ms else None

    def metadata(self):
        return {**super().metadata(), "fixed_ms": self.fixed_ms}


class CampStrikeNow(CampStrike):
    """camp_strike_now: camp_strike, except that the mounted group starts at the first
    decision."""

    arm = "camp_strike_now"

    def _start(self):
        return "now"
