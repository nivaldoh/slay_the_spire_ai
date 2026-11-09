"""The camp witness and its controls (camp.py) on scripted emp-chd-camp-v1 timelines.

Every unit record comes from the battle Lua's own unit_record (loaded by name, engine reads
stubbed, encoded by the mod's JSON codec), and every unit starts at its declared placement in
scenarios.json. Offline only: this shows which orders the scripts give, not what they do in a
game.
"""

import json
import random
from collections import Counter
from copy import deepcopy
from functools import cache

import pytest
import wh3_lua
from wh3_ablation import assert_ablation
from wh3_lua import load_battle

from twwarhammer3.battle import camp, controllers, play
from twwarhammer3.battle.setup import scenarios
from twwarhammer3.protocol import HIDDEN_KEYS, PolicyFailure, validate_orders

SCENARIO = scenarios()["emp-chd-camp-v1"]
# Labels for the declared placements, in deployment order.
FRIENDLY = ("general", "knights_a", "knights_b", "reiksguard", "priest", "flagellants_a",
            "flagellants_b", "flagellants_c", "company_a", "company_b")
ENEMY = ("overseer", "cannon_west", "cannon_east", "rockets", "guard_a", "guard_b", "wolves_a",
         "wolves_b", "centaurs", "cutthroats_a", "cutthroats_b")
START = dict(zip(FRIENDLY + ENEMY, SCENARIO["deployment"]["friendly"]
                 + SCENARIO["deployment"]["enemy"], strict=True))
MOUNTED = FRIENDLY[:4]
LEVIES = FRIENDLY[4:]
IDS = {**{label: f"f{index}" for index, label in enumerate(FRIENDLY, 1)},
       **{label: f"e{index}" for index, label in enumerate(ENEMY, 1)}}
_draw = random.Random(11)
SHUFFLED = {**dict(zip(FRIENDLY, _draw.sample([IDS[label] for label in FRIENDLY], 10))),
            **dict(zip(ENEMY, _draw.sample([IDS[label] for label in ENEMY], 11)))}
LIST_ORDER = _draw.sample(FRIENDLY + ENEMY, 21)
# Engine classes recorded in traces: Magma Cannon missile_chariot, Bull Centaurs infantry, Wolf
# Raiders and Empire Knights cavalry. The others are unrecorded guesses; no camp rule reads class.
CLASS = {"wh_main_emp_cha_general_1": "lord", "wh_main_emp_cav_empire_knights": "cavalry",
         "wh_main_emp_cav_reiksguard": "cavalry", "wh_main_emp_cha_warrior_priest_0": "hero",
         "wh_dlc04_emp_inf_flagellants_0": "infantry",
         "wh_dlc04_emp_inf_free_company_militia_0": "infantry",
         "wh3_dlc23_chd_cha_overseer": "lord", "wh3_dlc23_chd_veh_magma_cannon": "missile_chariot",
         "wh3_dlc23_chd_veh_deathshrieker_rocket_launcher": "artillery",
         "wh3_dlc23_chd_inf_infernal_guard": "infantry",
         "wh3_dlc23_chd_cav_hobgoblin_wolf_raiders_spears": "cavalry",
         "wh3_dlc23_chd_cav_bull_centaurs_axe": "infantry",
         "wh3_dlc23_chd_inf_hobgoblin_cutthroats": "infantry"}
# Men at large scale, from the design's roster tables.
MEN = {"wh_main_emp_cha_general_1": 1, "wh_main_emp_cav_empire_knights": 45,
       "wh_main_emp_cav_reiksguard": 45, "wh_main_emp_cha_warrior_priest_0": 1,
       "wh_dlc04_emp_inf_flagellants_0": 90, "wh_dlc04_emp_inf_free_company_militia_0": 90,
       "wh3_dlc23_chd_cha_overseer": 1, "wh3_dlc23_chd_veh_magma_cannon": 1,
       "wh3_dlc23_chd_veh_deathshrieker_rocket_launcher": 1,
       "wh3_dlc23_chd_inf_infernal_guard": 75,
       "wh3_dlc23_chd_cav_hobgoblin_wolf_raiders_spears": 45,
       "wh3_dlc23_chd_cav_bull_centaurs_axe": 12, "wh3_dlc23_chd_inf_hobgoblin_cutthroats": 105}
FLAGS = {"melee": "is_in_melee", "routing": "is_routing", "moving": "is_moving",
         "running": "is_moving_fast", "idle": "is_idle"}

LUA = wh3_lua.runtime()
LUA.execute("""
    function context_rows() return {} end
    function plain(text) return text end
    BEHAVIOURS = {}
    state = {friendly = {}, enemy_by_ui = {}}
    function own(id) state.friendly[id] = {ui_id = id, setup = {}} end
    function stub(kind, x, z, men, flags, target)
        local position = {get_x = function() return x end, get_z = function() return z end}
        local unit = {type = function() return kind end, position = function() return position end,
                      bearing = function() return 0 end, unary_hitpoints = function() return 1 end,
                      number_of_men_alive = function() return men end,
                      initial_number_of_men = function() return men end}
        for _, flag in ipairs({"is_routing", "is_shattered", "is_in_melee", "is_moving",
                               "is_idle", "is_moving_fast"}) do
            local value = flags[flag] == true
            unit[flag] = function() return value end
        end
        if target then
            state.enemy_by_ui[target] = target
            unit.current_target = function()
                return {unique_ui_id = function() return target end}
            end
        end
        return unit
    end
""")
*_, UNIT_RECORD = load_battle(LUA, "get", "round", "unit_record")
CODEC = LUA.execute((wh3_lua.MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())


def record(identity, kind, x, z, *, men, flags=(), target=None, mine):
    """The battle Lua's unit record for a stub unit (``target`` an enemy id)."""
    unit = LUA.globals().stub(kind, x, z, men, LUA.table_from({FLAGS[f]: True for f in flags}),
                              target)
    if mine:
        LUA.globals().own(identity)
    return json.loads(CODEC.encode(UNIT_RECORD(identity, unit, mine, CLASS[kind])))


def frame(time_s, changes, ids, order, last):
    """The observation at ``time_s``: every unit at its declared start unless ``changes``
    (label -> x, z, flags, target label, hidden, dead) says otherwise, with hidden sections
    shaped like a mailbox observation's that tell where every enemy is."""
    rows, roster, private = {"friendly": [], "enemy": []}, [], []
    for label in order:
        place, change = START[label], changes.get(label, {})
        kind, mine = place["type"], label in FRIENDLY
        row = record(ids[label], kind, change.get("x", place["x"]), change.get("z", place["z"]),
                     men=0 if change.get("dead") else MEN[kind], flags=change.get("flags", ()),
                     target=ids.get(change.get("target")), mine=mine)
        private.append({"id": row["id"], "type": kind, "x": row["x"], "z": row["z"],
                        "men": row["men"], "owner": "own" if mine else "enemy"})
        if not mine:
            roster.append({"id": row["id"], "type": kind, **({"dead": True}
                                                              if change.get("dead") else {})})
        if mine or not (change.get("hidden") or change.get("dead")):
            rows["friendly" if mine else "enemy"].append(row)
    strength = {}
    for unit in private:
        side = strength.setdefault("friendly" if unit["owner"] == "own" else "enemy",
                                   {"men": 0, "by_type": {}})
        side["men"] += unit["men"]
        side["by_type"].setdefault(unit["type"], {"men": 0})["men"] += unit["men"]
    time_ms = time_s * 1000
    return {"schema": 1, "job": "camp-check", "battle": "b1", "seq": time_s // 2,
            "phase": "Deployed", "time_ms": time_ms, "speed": 1, "awaiting_orders": False,
            "remaining_ms": 1200000 - time_ms,
            "armies": {"player": {"faction": "wh_main_emp_empire"},
                       "enemy": {"faction": "wh3_dlc23_chd_astragoth"}},
            **rows, "enemy_roster": roster, "magic": {},
            "mode": {"type": "land_normal", "role": "attacker", "timeout_winner": "enemy"},
            "terrain": {"bounds": {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}},
            "orders": None, "result": "lost" if last else None,
            "evaluation": {"version": 2, **strength}, "native": {"units": private},
            **({"setup": {"deployment_reading": {"enemy": private}}} if time_s == 2 else {}),
            **({"final": {"result": "lost", **strength}} if last else {})}


def at(x, z, *flags):
    return {"x": x, "z": z, "flags": flags}


def opening(t, mounted_from):
    """Levies advancing; the mounted group idle at its start, then moving with a target."""
    changes = {label: {"flags": ("moving",)} for label in LEVIES}
    for label in MOUNTED:
        changes[label] = ({"flags": ("moving", "running"), "target": "cannon_east"}
                          if t >= mounted_from else {"flags": ("idle",)})
    if t >= 20:  # Cutthroats (not cover) fight the north Flagellants from 20 s
        changes["cutthroats_a"] = at(-140, -245, "melee")
        changes["flagellants_a"] = {"flags": ("melee",)}
    return changes


def cue_battle(t):
    """Only the Bull Centaurs (class infantry) fight beside a levy, 19 m from the south
    Flagellants from 40 s, routing from 90 s. The mounted group rides past the Deathshrieker
    (16-21 m from it, 31-35 m from the east Magma Cannon) at 70-78 s and stands east of the guns
    from 80 s; the east Magma Cannon routs at 80 s, the Deathshrieker leaves sight at 90 s, the
    west Magma Cannon dies at 100 s, the mounted group stands on the Deathshrieker's last spot
    at 104 s (unseen, it has moved 11 m) and sees it again, 20 m from that spot, at 114 s."""
    changes = opening(t, 52)
    if t >= 40:
        changes["centaurs"] = at(-135, -335, "melee", *(("routing",) if t >= 90 else ()))
        changes["flagellants_c"] = {"flags": ("melee",)}
    places = ([(140, -460), (145, -460), (140, -465), (145, -465)] if 70 <= t < 80 else
              [(190, -440), (210, -440), (190, -455), (210, -455)] if 80 <= t < 104 else
              [(120, -460), (134, -460), (120, -474), (134, -474)] if t >= 104 else [])
    for label, (x, z) in zip(MOUNTED, places):
        changes[label].update(x=x, z=z)
    if t >= 80:
        changes["cannon_east"] = {"flags": ("routing",)}
    if t >= 90:
        changes["rockets"] = at(140, -485) if t >= 114 else {"x": 135, "z": -478,
                                                             "hidden": True}
    if t >= 100:
        changes["cannon_west"] = {"dead": True}
    return changes


def no_cue_battle(t):
    """Cover near the levies in every way but the cue, then the 180 s fallback: Wolf Raiders
    idle 20 m from a levy (30-42 s); the Bull Centaurs fighting the knights at their start
    (50-62 s); Wolf Raiders in melee 20 m from a levy for one observation (70 s), then 40 m
    from the nearest levy (80-92 s); the Bull Centaurs fighting beside a levy for 8 s
    (100-108 s); two Wolf Raiders units there for 6 s each, back to back (120-134 s); Wolf
    Raiders fighting 19 m from a levy for 12 s, out of sight at 146 s (140-152 s); Wolf Raiders
    fighting 20 m from the Warrior Priest, dead from 156 s, and 66 m from every live levy
    (156-168 s)."""
    changes = opening(t, 182)
    windows = [(30, 42, "wolves_a", at(-130, -323, "idle")),
               (50, 62, "centaurs", at(395, -60, "melee")),
               (50, 62, "knights_a", {"flags": ("melee",)}),
               (70, 70, "wolves_b", at(-135, -290, "melee")),
               (80, 92, "wolves_a", at(-110, -323, "melee")),
               (100, 108, "centaurs", at(-135, -335, "melee")),
               (120, 126, "wolves_a", at(-135, -335, "melee")),
               (128, 134, "wolves_b", at(-140, -340, "melee")),
               (140, 152, "wolves_a", at(-135, -335, "melee")),
               (146, 146, "wolves_a", {"x": -135, "z": -335, "hidden": True}),
               (156, 184, "priest", {"dead": True}),
               (156, 168, "wolves_b", at(-150, -389, "melee"))]
    for start, stop, label, change in windows:
        if start <= t <= stop:
            changes[label] = change
    return changes


@cache
def battle(events, end_s, ids=tuple(IDS.items()), order=FRIENDLY + ENEMY):
    ids = dict(ids)
    return tuple(frame(t, events(t), ids, order, t == end_s) for t in range(2, end_s + 1, 2))


def cue():
    return battle(cue_battle, 124)


def no_cue():
    return battle(no_cue_battle, 184)


def decisions(policy, observations, view=lambda observation: play.public(observation, {})):
    """Each batch the policy gives on what it may read of each observation, checked by
    validate_orders as play checks it (a queued attack after an attack fails there)."""
    batches = []
    for observation in observations:
        seen = view(deepcopy(observation))
        batch = policy.decide(seen)
        validate_orders(batch, seen)
        batches.append(batch)
    return batches


def named(batches, ids=IDS):
    label = {identity: name for name, identity in ids.items()}
    return [[{**order, "unit": label[order["unit"]],
              **({"target": label[order["target"]]} if "target" in order else {})}
             for order in batch] for batch in batches]


def mounted(batches, observations):
    """Battle second -> mounted label -> (order type, target label or move point)."""
    result = {}
    for observation, batch in zip(observations, named(batches), strict=True):
        rows = {order["unit"]: (order["type"], order.get("target") or (order["x"], order["z"]))
                for order in batch if order["unit"] in MOUNTED}
        if rows:
            result[observation["time_ms"] // 1000] = rows
    return result


def start(policy):
    return {key: policy.metadata()[key] for key in ("cue_ms", "start_ms", "start_reason")}


def every(target):
    return dict.fromkeys(MOUNTED, target)


def test_the_cue_needs_one_cover_unit_in_melee_beside_a_levy_for_ten_seconds():
    # A detector keyed on class cavalry misses the Bull Centaurs and waits for the fallback; a
    # one-observation cue fires at 40 s here and at 70 s in the second battle.
    policy = camp.CampStrike()
    assert min(mounted(decisions(policy, cue()), cue()), default=None) == 50
    assert start(policy) == {"cue_ms": 50000, "start_ms": 50000, "start_reason": "cue"}
    # Idle cover, cover fighting the knights, 40 m, 8 s, 6 s for each of two units, 12 s broken
    # by one observation out of sight, or 12 s beside a dead levy only: no cue.
    policy = camp.CampStrike()
    assert min(mounted(decisions(policy, no_cue()), no_cue()), default=None) == 180
    assert start(policy) == {"cue_ms": None, "start_ms": 180000, "start_reason": "fallback"}


def test_the_strike_takes_war_machines_by_key_and_retargets_only_when_one_is_lost():
    batches = decisions(camp.CampStrike(), cue())
    assert mounted(batches, cue()) == {
        # Class missile_chariot, nearest by key; kept at 70-78 s, though the Deathshrieker is
        # nearer then.
        50: every(("attack", "cannon_east")),
        80: every(("attack", "rockets")),  # the east cannon routs
        90: every(("attack", "cannon_west")),  # the rockets leave sight
        100: every(("move", (127, -470))),  # the west cannon dies: the rockets' last spot
        # Unseen there, so the nearest enemy fighting beside the levies, not the Overseer
        # 15 m away; the routing Bull Centaurs are no target.
        104: every(("attack", "cutthroats_a")),
        114: every(("attack", "rockets"))}  # seen again: war machines come first
    # Levies keep the Cutthroats they took first, though the Bull Centaurs come nearer at 40 s.
    assert {order["target"] for batch in named(batches) for order in batch
            if order["unit"] in LEVIES} == {"cutthroats_a"}
    first = named(batches)[0]
    assert {order["unit"]: (order["mode"], order["run"]) for order in first} == {
        "priest": ("melee", True), "flagellants_a": ("melee", True),
        "flagellants_b": ("melee", True), "flagellants_c": ("melee", True),
        "company_a": ("auto", False), "company_b": ("auto", False)}
    # The mounted group runs to every target and spot (the design's travel times assume it).
    assert {(order["type"], order.get("mode"), order["run"]) for batch in named(batches)
            for order in batch if order["unit"] in MOUNTED} == {("attack", "auto", True),
                                                               ("move", None, True)}


def test_the_support_arm_differs_only_in_what_the_mounted_group_attacks_first():
    ids = set(IDS[label] for label in MOUNTED)
    for observations, start_ms in ((cue(), 50000), (no_cue(), 180000)):
        assert_ablation(camp.CampStrike, camp.CampSupport, observations, rules={
            "mounted targets once started": lambda observation, order, start_ms=start_ms:
                order["unit"] in ids and observation["time_ms"] >= start_ms})
    assert mounted(decisions(camp.CampSupport(), cue()), cue()) == {
        50: every(("attack", "centaurs")), 90: every(("attack", "cutthroats_a"))}


def test_the_timing_controls_differ_only_in_when_the_mounted_group_starts():
    ids = set(IDS[label] for label in MOUNTED)
    # Each starts from the same spots as the witness, before the cue at 50 s or after it, so
    # once both have started their orders must be the witness's.
    for make, started_ms in ((lambda: camp.CampStrikeFixed(30000), 50000),
                             (lambda: camp.CampStrikeFixed(60000), 60000),
                             (camp.CampStrikeNow, 50000)):
        assert_ablation(camp.CampStrike, make, cue(), rules={
            "mounted start": lambda observation, order, started_ms=started_ms:
                order["unit"] in ids and observation["time_ms"] <= started_ms})
    early, late = camp.CampStrikeFixed(30000), camp.CampStrikeFixed(60000)
    now = camp.CampStrikeNow()
    decisions(early, cue())
    decisions(now, cue())
    # A T_fixed after the cue: the mounted group still waits for it.
    assert min(mounted(decisions(late, cue()), cue())) == 60
    assert (start(early), start(late), start(now)) == (
        {"cue_ms": 50000, "start_ms": 30000, "start_reason": "fixed"},
        {"cue_ms": 50000, "start_ms": 60000, "start_reason": "fixed"},
        {"cue_ms": 50000, "start_ms": 2000, "start_reason": "now"})
    if camp.FIXED_CUE_MS is None:
        with pytest.raises(ValueError, match="T_fixed"):
            camp.CampStrikeFixed()


class Public(dict):
    """An observation that fails the test when a hidden key is read."""

    def __getitem__(self, key):
        assert key not in HIDDEN_KEYS, key
        return super().__getitem__(key)

    def get(self, key, default=None):
        assert key not in HIDDEN_KEYS, key
        return super().get(key, default)


@pytest.mark.parametrize("make", [camp.CampStrike, camp.CampSupport, camp.CampStrikeNow,
                                  lambda: camp.CampStrikeFixed(30000)])
def test_no_arm_reads_a_hidden_section(make):
    # Each observation carries evaluation and native, the first setup and the last final. They
    # place the hidden Deathshrieker 11 m from its last public spot, so a read that slips past
    # the guard (through items(), say) still changes orders.
    for observations in (cue(), no_cue()):
        assert all(key in observations[0] for key in ("evaluation", "native", "setup"))
        assert decisions(make(), observations, view=Public) == decisions(make(), observations)


def test_binding_is_by_type_and_start_never_by_id_or_list_order():
    friendly = Counter(place["type"] for place in SCENARIO["deployment"]["friendly"])
    assert friendly == Counter({**camp.MOUNTED, **camp.LEVIES})
    assert set(camp.ATTACK) == set(friendly)
    assert camp.COVER | camp.GUNS <= {place["type"] for place in SCENARIO["deployment"]["enemy"]}
    assert any(SHUFFLED[label] != IDS[label] for label in MOUNTED)
    for make in (camp.CampStrike, camp.CampSupport):
        shuffled = battle(cue_battle, 124, tuple(SHUFFLED.items()), tuple(LIST_ORDER))
        assert named(decisions(make(), shuffled), SHUFFLED) == named(decisions(make(), cue()))
    short = deepcopy(cue()[0])
    short["friendly"] = [unit for unit in short["friendly"] if unit["id"] != IDS["reiksguard"]]
    with pytest.raises(PolicyFailure, match="ten placed units") as refused:
        camp.CampStrike().decide(play.public(short, {}))
    assert not play.is_forfeit(refused.value)  # the episode ends; the army does not just stand
    for name in ("CampStrike", "CampSupport", "CampStrikeFixed", "CampStrikeNow"):
        assert controllers.controller_class(f"twwarhammer3.battle.camp:{name}").__name__ == name
