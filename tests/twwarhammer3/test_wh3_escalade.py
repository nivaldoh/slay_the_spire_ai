"""The siege attack's witness and controls (battle/escalade.py) for ksl-emp-siege-a-v1, on the
offline Helmgart fixture wh3_siege_attack.py (the declaration is test_wh3_siege_assault.py's).

Reference: the 2026-11-08 siege-attack design (runs/siege-evals-20261108/final-izmail.md,
Settings, Rosters, Controls, Witness "Escalade v1", Infrastructure I7) and portfolio.md's
corrections (gate_breached; the private record in place of I6). Offline only: these show what
the scripts order on a fixture whose fortification pieces nobody has read, not what the engine
does with the orders, that the cards recruit or that a ram goes to the gate.
"""

import math
import random
from copy import deepcopy
from itertools import combinations

import pytest
from wh3_ablation import assert_ablation, run
from wh3_siege_attack import FORTIFICATIONS, SCENARIO, first_observation, later

from twwarhammer3.battle import escalade, play
from twwarhammer3.battle.replay_schedule import digest
from twwarhammer3.protocol import PolicyFailure, validate_orders


def staged(observation, orders, time_ms, **changes):
    """``observation`` at ``time_ms`` with every unit moved to its last move order's point."""
    moves = {o["unit"]: {"x": o["x"], "z": o["z"]} for o in orders if o["type"] == "move"}
    for identity, fields in changes.items():
        moves[identity] = {**moves.get(identity, {}), **fields}
    return later(observation, time_ms, **moves)


@pytest.mark.parametrize("seed", [3, 11])
def test_groups_follow_type_and_start_x_never_the_engines_ids(seed):
    """Wrong version: groups by id order (the engine need not number units in roster order)."""
    ids = [f"f{index}" for index in range(1, 14)]
    random.Random(seed).shuffle(ids)
    observation = first_observation(ids=ids)
    policy = escalade.Escalade()
    policy.decide(play.public(observation, {}))
    place = {unit["id"]: (unit["type"][len("wh3_main_ksl_"):], unit["x"])
             for unit in observation["friendly"]}
    groups = {name: sorted(place[i] for i in members)
              for name, members in policy.metadata()["groups"].items()}
    assert groups == {
        "centre": [("inf_armoured_kossars_0", 0.0), ("inf_kossars_1", 20.0),
                   ("inf_streltsi_0", -60.0), ("veh_little_grom_0", -20.0)],
        "west": [("inf_armoured_kossars_0", -200.0), ("inf_armoured_kossars_0", -100.0),
                 ("inf_kossars_1", -150.0)],
        "east": [("inf_armoured_kossars_0", 100.0), ("inf_armoured_kossars_0", 200.0),
                 ("inf_kossars_1", 150.0)],
        "reserve": [("cha_boyar_0", 0.0), ("inf_streltsi_0", 60.0)],
        "horse": [("cav_winged_lancers_0", 0.0)]}
    # The crew (the Armoured Kossars at x 0) leaves its type, so no fifth one joins the reserve.
    crew = observation["mode"]["vehicles"][0]["crew"]
    assert policy.metadata()["jobs"][crew] == "ram"


def sequence():
    """Witness-shaped battle: staging at 5.3 s, every group staged at 60 s, West down 40% and f2
    on the wall at 125 s, the gate at hp 0 with ``destroyed`` false at 136 s (as two recorded
    gates read; g1 at 0% in mode.fortifications too, and East's piece w9; over RETRY_MS after
    125 s, so an order kept on either would be resent), six units inside at 140 s."""
    start = first_observation()
    first = escalade.Escalade().decide(play.public(start, {}))
    ready = staged(start, first, 60000)
    hurt = later(ready, 125000, f2={"men": 30, "on_wall": True}, f3={"men": 30},
                 f7={"men": 40})
    gates = [{"destroyed": False, "hp": 0, "name": "Gatehouse", "x": -32, "z": -16}]
    broken = later(hurt, 136000, mode={"gates": gates})
    for piece in broken["mode"]["fortifications"]:
        if piece["id"] in ("g1", "w9"):
            piece["hp"] = 0
    inside = {f"f{i}": {"z": 40.0, "x": -20.0 + 8 * i} for i in (2, 3, 4, 5, 6, 7)}
    crowded = later(broken, 140000, **inside)
    return [start, ready, hurt, broken, crowded]


def test_the_witness_stages_assaults_together_sends_its_reserve_and_holds_the_horse():
    observations = sequence()
    batches = run(escalade.Escalade, observations)
    for orders, observation in zip(batches, observations, strict=True):
        validate_orders(orders, observation)
    by_unit = [{order["unit"]: order for order in orders} for orders in batches]
    # Phase 1: staging 150 m south of each target, walking; the Horse 300 m south of g1.
    assert {i: (by_unit[0][i]["x"], by_unit[0][i]["z"]) for i in ("f2", "f3", "f7")} == {
        "f2": (-230.0, -238), "f7": (-190.0, -238), "f3": (-150.0, -238)}
    # Each spot faces its target w3 (-190, -88): atan(40 / 150) is 15 degrees either side of north
    # (40 m and 150 m rest on JUDGEMENT escalade.py Escalade thresholds).
    assert {i: by_unit[0][i]["facing"] for i in ("f2", "f3", "f7")} == {
        "f2": 15, "f7": 0, "f3": 345}
    assert (by_unit[0]["f12"]["x"], by_unit[0]["f12"]["z"]) == (-32.0, -316)
    assert not {"f1", "f11"} & set(by_unit[0])  # the reserve waits for its decision
    # Phase 2, in one decision: ladders on w3, w5 and w9, the crew and the Grom at g1, the
    # Streltsi on the defender within its range of g1.
    assert {i: (o["type"], o.get("target")) for i, o in by_unit[1].items() if i != "f12"} == {
        "f2": ("besiege", "w3"), "f3": ("besiege", "w3"), "f7": ("besiege", "w3"),
        "f8": ("besiege", "w5"), "f5": ("besiege", "w9"), "f6": ("besiege", "w9"),
        "f9": ("besiege", "w9"), "f4": ("besiege", "g1"), "f13": ("attack_building", "g1"),
        "f10": ("attack", "e2")}
    # 65 s after phase 2 West has lost the most (over 30%): the reserve climbs West's piece,
    # and the unit on the wall goes for c7. The Lancers still wait.
    assert {i: (by_unit[2][i]["type"], by_unit[2][i].get("target")) for i in ("f1", "f11")} == {
        "f1": ("besiege", "w3"), "f11": ("besiege", "w3")}
    assert (by_unit[2]["f2"]["type"], by_unit[2]["f2"]["x"], by_unit[2]["f2"]["z"]) == (
        "move", -1, 155)
    assert "f12" not in by_unit[2]
    # The gate at hp 0 releases the Horse, whatever ``destroyed`` says. A unit whose target
    # reads 0% walks in to c7 (validation refuses an order on it), and the Grom stops.
    assert {i: (by_unit[3][i]["type"], by_unit[3][i]["x"], by_unit[3][i]["z"])
            for i in ("f12", "f4", "f5", "f6", "f9")} == dict.fromkeys(
        ("f12", "f4", "f5", "f6", "f9"), ("move", -1, 155))
    assert "f13" not in by_unit[3]
    # Six units inside: everyone attacks the visible enemy nearest it (f10, resent its attack
    # on e2 at 136 s, keeps it).
    assert {o["type"] for o in batches[4]} == {"attack"} and set(by_unit[4]) == {
        f"f{i}" for i in range(1, 14)} - {"f10"} and by_unit[3]["f10"]["target"] == "e2"
    meta = escalade.Escalade()
    run(lambda: meta, observations)
    assert meta.metadata() | {"groups": None, "jobs": None, "targets": None} == {
        "type": "escalade", "version": 1, "groups": None, "jobs": None, "targets": None,
        "phase2_ms": {"west": 60000, "centre": 60000, "east": 60000}, "phase2_reason": "staged",
        "reserve": "west", "reserve_ms": 125000, "gate_open_ms": 136000, "phase4_ms": 140000}


@pytest.mark.parametrize("before,changes,group", [
    # West's 217 men: 90 lost (41%) decides; 15 lost (7%) does not, and East has one up.
    ({}, {"f2": {"men": 30}, "f3": {"men": 30}, "f9": {"on_wall": True}}, "west"),
    ({}, {"f2": {"men": 60}, "f9": {"on_wall": True}}, "east"),
    ({}, {}, "west"),  # nothing lost, nobody up: the first group in West, Centre, East order
    # West lost 100 (46% from the start) while staging; East's 70 (32%) since phase 2 decide.
    ({"f2": {"men": 25}, "f3": {"men": 25}}, {"f5": {"men": 40}, "f6": {"men": 40}}, "east"),
])
def test_the_reserve_joins_the_worst_hit_group_over_30_percent_else_the_most_on_the_wall(
        before, changes, group):
    """Wrong version: losses counted from the battle's start, not since phase 2."""
    start = first_observation()
    policy = escalade.Escalade()
    ready = staged(start, policy.decide(play.public(start, {})), 60000, **before)
    policy.decide(play.public(ready, {}))
    policy.decide(play.public(later(ready, 120000, **changes), {}))
    assert (policy.metadata()["reserve"], policy.metadata()["reserve_ms"]) == (group, 120000)


def timed():
    """Phase 2 by the clock (no group staged), so the arms start it together: start, 150 s,
    Centre down a third at 215 s, the Centre's Kossars on the wall at 220 s."""
    start = first_observation()
    clock = later(start, 150000)
    hurt = later(clock, 215000, f4={"men": 40}, f8={"men": 40}, f10={"men": 40})
    climbed = later(hurt, 220000, f8={"on_wall": True})
    near = later(climbed, 225000, e2={"x": 5.0, "z": -280.0, "on_wall": False})
    return [start, clock, hurt, climbed, near]


def test_concentrate_changes_only_where_west_and_east_climb():
    """Wrong version: a Concentrate foil that also drops the reserve rule (the order diff must
    fail it); the reserve here joins Centre, whose target both arms share."""
    observations = timed()
    groups = escalade.Escalade()
    groups.decide(play.public(observations[0], {}))
    flanks = groups.metadata()["groups"]["west"] + groups.metadata()["groups"]["east"]
    changed = assert_ablation(escalade.Escalade, escalade.Concentrate, observations, units=flanks)
    assert {0, 1} <= set(changed)  # staging and the ladders differ at once
    concentrate = run(escalade.Concentrate, observations)
    assert {(o["unit"], o["target"]) for o in concentrate[1] if o["unit"] in flanks} == {
        ("f2", "w5"), ("f3", "w5"), ("f7", "w5"), ("f5", "w7"), ("f6", "w7"), ("f9", "w7")}
    reserve = {(o["unit"], o["type"], o["target"]) for o in concentrate[2]
               if o["unit"] in ("f1", "f11")}
    assert reserve == {("f1", "besiege", "w5"), ("f11", "besiege", "w5")}


def test_cavalry_early_changes_only_the_lancers():
    observations = timed()
    assert assert_ablation(escalade.Escalade, escalade.CavalryEarly, observations,
                           units=["f12"])
    early = run(escalade.CavalryEarly, observations)
    assert [(o["x"], o["z"]) for o in early[0] if o["unit"] == "f12"] == [(-32, -36)]
    # An enemy 49 m from the Lancers: they attack it before the gate falls; at 51 m they hold
    # (EARLY_M's 50 m rests on JUDGEMENT escalade.py Control parameters).
    attack = {"unit": "f12", "type": "attack", "target": "e2", "mode": "auto", "run": True,
              "queue": False}
    for gap, expected in ((49, [attack]), (51, [])):
        lancers = later(observations[0], 60000, f12={"x": -32.0, "z": -36.0},
                        e2={"x": -32.0 + gap, "z": -36.0})
        policy = escalade.CavalryEarly()
        policy.decide(play.public(observations[0], {}))
        assert [o for o in policy.decide(play.public(lancers, {}))
                if o["unit"] == "f12" and o["type"] == "attack"] == expected


def degraded():
    """Reads the guards must survive: at the start f2's ``can_climb`` absent (its getter failed;
    the Lua comment above siege_unit) and f8's false; at 150 s, phase 2 by the clock, the Grom out
    of ammunition while g1 reads hp 100; at 165 s, over RETRY_MS after phase 2's orders so that
    unchanged ones are rebuilt, the mode section failed to read (the mod then sends only its
    error, without fortifications, capture points or vehicles: pcall(mode_section) in
    twwarhammer3_battle.lua)."""
    start = first_observation()
    units = {unit["id"]: unit for unit in start["friendly"]}
    del units["f2"]["can_climb"]
    units["f8"]["can_climb"] = False
    clock = later(start, 150000, f13={"ammo": 0})
    blind = later(clock, 165000)
    blind["mode"] = {"error": "mode_section failed"}
    return [start, clock, blind]


# Version 2 of the witness and every arm (escalade-eval.md, owner question 6), built beside
# version 1 and in no plan until the owner picks it.
V2 = (escalade.EscaladeV2, escalade.ConcentrateV2, escalade.CavalryEarlyV2, escalade.PiecemealV2,
      escalade.ShootOnlyV2, escalade.GateOnlyV2, escalade.BesiegeNearestV2)


@pytest.mark.parametrize("make", [escalade.Escalade, escalade.Concentrate,
                                  escalade.CavalryEarly, escalade.Piecemeal,
                                  escalade.ShootOnly, escalade.GateOnly,
                                  escalade.BesiegeNearest, *V2])
def test_every_arm_orders_only_what_validation_accepts(make):
    """Also on degraded() reads, where one refused order would void each batch (play.py) and
    the arm would rebuild it at every decision. Wrong versions: a besiege on a piece this
    observation does not list, attack_building without ammunition, a ladder for a unit whose
    ``can_climb`` is not true."""
    for observations in (sequence(), timed(), degraded()):
        batches = run(make, observations)
        for orders, observation in zip(batches, observations, strict=True):
            validate_orders(orders, observation)
    # degraded()'s Grom, out of ammunition at 150 s, is not ordered at g1.
    assert not [o for o in batches[1] if o["unit"] == "f13" and o["type"] == "attack_building"]


def test_the_controls_play_their_own_rule():
    observations = sequence()
    # Gate only: no ladders at all; everyone waits south of g1, enters once it breaks; its
    # Streltsi hold their fire in phase 2, where the witness's shoot (timed(), by the clock).
    gate = run(escalade.GateOnly, observations)
    assert not [o for orders in gate for o in orders
                if o["type"] == "besiege" and o["target"] != "g1"]
    shots = [[o["unit"] for o in orders if o["type"] == "attack"]
             for make in (escalade.Escalade, escalade.GateOnly) for orders in run(make, timed())]
    assert shots[1] == ["f10"] and not any(shots[5:])
    assert {o["unit"] for o in gate[3] if o["type"] == "move" and (o["x"], o["z"]) == (-1, 155)} \
        >= {"f1", "f3", "f5", "f6", "f7", "f9", "f11"}
    # Shoot only: a unit with ammunition walks to 120 m south of its target and shoots ranged;
    # out of ammunition, it climbs as the witness does.
    shoot = escalade.ShootOnly()
    first = shoot.decide(play.public(observations[0], {}))
    assert {(o["unit"], o["x"], o["z"]) for o in first if o["unit"] in ("f2", "f13")} == {
        ("f2", -230.0, -208), ("f13", -52.0, -136)}
    there = later(observations[0], 60000, f2={"x": -230.0, "z": -208.0, "range": 35},
                  e2={"x": -225.0, "z": -180.0, "on_wall": False},
                  f9={"ammo": 0})
    orders = {o["unit"]: o for o in shoot.decide(play.public(there, {}))}
    assert orders["f2"] == {"unit": "f2", "type": "attack", "target": "e2", "mode": "ranged",
                            "run": True, "queue": False}
    # Besiege nearest: every climber at its nearest wall piece from the first decision.
    nearest = {o["unit"]: (o["type"], o.get("target")) for o in
               run(escalade.BesiegeNearest, observations)[0]}
    assert nearest["f2"] == ("besiege", "w3") and nearest["f6"] == ("besiege", "w9")
    assert nearest["f4"] == ("besiege", "g1") and nearest["f13"] == ("attack_building", "g1")
    assert nearest["f12"][0] == nearest["f1"][0] == "attack"
    # Piecemeal: West staged alone at 60 s besieges; the others are still walking.
    start = observations[0]
    walk = escalade.Escalade().decide(play.public(start, {}))
    west = {"f2", "f3", "f7"}
    alone = staged(start, [o for o in walk if o["unit"] in west], 60000)
    piece = escalade.Piecemeal()
    piece.decide(play.public(start, {}))
    kinds = {o["unit"]: o["type"] for o in piece.decide(play.public(alone, {}))}
    assert {kinds[i] for i in west} == {"besiege"} and kinds["f8"] == "move"
    together = escalade.Escalade()
    together.decide(play.public(start, {}))
    together.decide(play.public(alone, {}))
    assert together.metadata()["phase2_ms"] == {}


def test_the_replay_keeps_its_fortification_targets_and_drops_unlisted_ones():
    start = first_observation()
    schedule = {"version": 1, "scenario_sha256": digest(SCENARIO), "source": {"job": "w"},
                "start": {unit["id"]: {key: unit[key] for key in ("type", "x", "z")}
                          for unit in start["friendly"]},
                "batches": [{"time_ms": 100000, "request": "r9", "orders": [
                    {"order": {"unit": "f2", "type": "besiege", "target": "w3", "run": True}},
                    {"order": {"unit": "f3", "type": "besiege", "target": "w99", "run": True}},
                    {"order": {"unit": "f13", "type": "attack_building", "target": "g1",
                               "run": False}}]}]}
    replay = escalade.EscaladeReplay(schedule, scenario=SCENARIO)
    assert replay.decide(play.public(start, {})) == []
    orders = replay.decide(play.public(later(start, 100000), {}))
    assert orders == [{"unit": "f2", "type": "besiege", "target": "w3", "run": True},
                      {"unit": "f13", "type": "attack_building", "target": "g1", "run": False}]
    assert replay.unmatched == 1
    # The same batch after g1 fell (0% in mode.fortifications): its gun order is dropped.
    replay = escalade.EscaladeReplay(schedule, scenario=SCENARIO)
    replay.decide(play.public(start, {}))
    fallen = later(start, 100000)
    fallen["mode"]["fortifications"][0]["hp"] = 0
    assert [o["unit"] for o in replay.decide(play.public(fallen, {}))] == ["f2"]
    assert replay.unmatched == 2


def holding(observation, **holders):
    """A copy of ``observation`` whose named capture points are held by "us" or "enemy", or are
    neutral (None: no ``holder`` key, as evidence_rules.holds reads it)."""
    state = deepcopy(observation)
    for point in state["mode"]["capture_points"]:
        if point["id"] in holders:
            point.pop("holder", None)
            if holders[point["id"]] is not None:
                point["holder"] = holders[point["id"]]
    return state


def test_phase_2_waits_for_every_able_unit_on_its_spot_or_150_s():
    """Wrong versions: the clock at 120 s; a group staged once any of its units arrives; a dead
    unit that never reaches its spot holding phase 2 back."""
    # 150 s and the 20 m that count as on the spot rest on JUDGEMENT escalade.py Escalade
    # thresholds.
    start = first_observation()
    walk = escalade.Escalade().decide(play.public(start, {}))

    def phase2(observation):
        policy = escalade.Escalade()
        policy.decide(play.public(start, {}))
        policy.decide(play.public(observation, {}))
        return policy.metadata()["phase2_ms"], policy.metadata()["phase2_reason"]

    assert phase2(later(start, 149900)) == ({}, None)
    # f2 (West) 30 m east of its spot at (-230, -238), every other unit on its own.
    assert phase2(staged(start, walk, 60000, f2={"x": -200.0})) == ({}, None)
    assert phase2(staged(start, walk, 60000, f2={"x": -200.0, "men": 0})) == (
        dict.fromkeys(escalade.ASSAULT, 60000), "staged")


def test_the_horse_rides_once_the_gatehouse_is_ours_to_c7_then_c1():
    """Wrong versions: only a breached gate releases the Horse; the Horse stays on c7."""
    start = first_observation()
    gatehouse = holding(later(start, 60000), c2="us")  # g1 still reads hp 100
    supply = holding(later(gatehouse, 65000), c7="us")
    policy = escalade.Escalade()
    rides = [[(o["x"], o["z"]) for o in policy.decide(play.public(observation, {}))
              if o["unit"] == "f12"] for observation in (start, gatehouse, supply)]
    assert rides[1:] == [[(-1, 155)], [(0, 310)]]
    assert policy.metadata()["gate_open_ms"] == 60000


def test_a_unit_inside_the_front_line_or_on_the_wall_goes_to_c7_even_while_neutral():
    """Wrong versions: only ``on_wall`` starts phase 3; a neutral point is passed over as held."""
    # c7 first rests on JUDGEMENT? escalade.py Victory order.
    start = first_observation()
    # f2 15 m north of the front line's point at w4 (-120, -55), not on the wall; then f3 on the
    # wall at w3 with c7 neutral.
    inside = later(start, 60000, f2={"x": -120.0, "z": -40.0})
    neutral = holding(later(inside, 65000, f3={"x": -190.0, "z": -88.0, "on_wall": True}),
                      c7=None)
    batches = run(escalade.Escalade, [start, inside, neutral])
    assert [(o["x"], o["z"]) for o in batches[1] if o["unit"] == "f2"] == [(-1, 155)]
    assert [(o["x"], o["z"]) for o in batches[2] if o["unit"] == "f3"] == [(-1, 155)]
    # A fort read as g1 and one wall piece, both in the 40 m column floor(x / 40) = -1, has a
    # front line of one point, w1 (-10, -20); f2 20 m north of it is inside as well (the
    # column rule rests on JUDGEMENT? escalade.py Front line).
    narrow = first_observation()
    narrow["mode"]["fortifications"] = [
        {"id": "g1", "kind": "gate", "x": -32, "z": -16, "hp": 100},
        {"id": "w1", "kind": "wall", "x": -10, "z": -20, "hp": 100}]
    batches = run(escalade.Escalade, [narrow, later(narrow, 60000, f2={"x": -20.0, "z": 0.0})])
    assert [(o["x"], o["z"]) for o in batches[1] if o["unit"] == "f2"] == [(-1, 155)]


def test_phase_4_needs_six_able_units_inside_and_survives_no_visible_enemy():
    """Wrong versions: five inside are enough; a unit on the wall counts as inside; phase 4
    attacks with no enemy in view (a TypeError, which ends the episode)."""
    # Six rests on JUDGEMENT escalade.py Escalade thresholds (INSIDE_UNITS).
    start = first_observation()
    five = later(start, 60000, **{f"f{i}": {"x": -20.0 + 8 * i, "z": 40.0} for i in range(2, 7)})
    walled = later(five, 65000, f7={"x": -190.0, "z": -88.0, "on_wall": True})
    six = later(walled, 70000, f7={"x": 36.0, "z": 40.0, "on_wall": False})
    six["enemy"] = []
    policy, phase4 = escalade.Escalade(), []
    for observation in (start, five, walled, six):
        validate_orders(policy.decide(play.public(observation, {})), observation)
        phase4.append(policy.metadata()["phase4_ms"])
    assert phase4 == [None, None, None, 70000]


def test_the_streltsi_hold_fire_at_an_enemy_beyond_their_range_of_the_gate():
    """Wrong version: they shoot the visible enemy nearest them wherever it stands."""
    start = first_observation()
    # e2 sorties to (-150, -200): about 100 m from the western Streltsi f10 but 218 m from g1,
    # beyond their 160 m range of it (and SHOOT_M); e5 and e6 stand over 200 m from g1.
    clock = later(start, 150000, e2={"x": -150.0, "z": -200.0, "on_wall": False})
    assert not [o for o in run(escalade.Escalade, [start, clock])[1] if o["unit"] == "f10"]


def test_front_line_keeps_the_southernmost_piece_in_each_40_m_column():
    """Worked by hand from the fixture: in the columns floor(x / 40) = -5, -2, 1 and 4 a wall
    piece and a tower share the column, and the southern one stays (w3, t2, t3, w9). This pins
    the rule under the JUDGEMENT? Front line marker on the fixture's sketch pieces, not the real
    fort, whose pieces no battle has read."""
    assert escalade.front_line(FORTIFICATIONS) == [
        (-330, -100), (-250, -95), (-190, -88), (-120, -55), (-62, -31), (-32, -16), (5, -20),
        (58, -31), (130, -60), (190, -88), (250, -95), (330, -100)]


def test_piecemeals_reserve_clock_starts_with_its_first_group():
    """West staged at 60 s and East at 100 s: the reserve decides RESERVE_MS after West's phase
    2. Wrong version: after the last group's."""
    # RESERVE_MS's 60 s rests on JUDGEMENT escalade.py Escalade thresholds.
    start = first_observation()
    walk = escalade.Escalade().decide(play.public(start, {}))
    west = staged(start, [o for o in walk if o["unit"] in ("f2", "f3", "f7")], 60000)
    east = staged(west, [o for o in walk if o["unit"] in ("f5", "f6", "f9")], 100000)
    policy = escalade.Piecemeal()
    run(lambda: policy, [start, west, east, later(east, 120000)])
    meta = policy.metadata()
    assert meta["phase2_ms"] == {"west": 60000, "east": 100000}
    assert (meta["reserve"], meta["reserve_ms"]) == ("west", 120000)


def test_escalade_refuses_fortifications_without_the_gate():
    """Wrong version: wall pieces alone suffice. The episode still ends as a policy failure
    (play.policy_call wraps the KeyError that follows), but its error then reads 'decide:
    KeyError' instead of naming the missing g1."""
    start = first_observation()
    start["mode"]["fortifications"] = [p for p in start["mode"]["fortifications"]
                                       if p["id"] != "g1"]
    with pytest.raises(PolicyFailure, match="g1"):
        escalade.Escalade().decide(play.public(start, {}))


def test_the_order_probe_sends_assault_luas_orders_at_10_s_and_resends_only_to_idle_units():
    """OrderProbe (stage 2's probe, a port of checkpoint_siege/assault.lua) on the attack
    fixture: f2 still busy at 20 s, g1 at 0% at 31 s; and on degraded(). Wrong versions: a probe
    that gives the Grom a wall besiege (validation refuses it: the Grom cannot climb); one that
    orders a routing unit (validation refuses it, and play voids the whole batch); one that picks
    the ram's crew as a climber (its g1 besiege replaces the wall one, so no Armoured Kossars
    climbs)."""
    start = first_observation()
    tick = later(start, 10000)
    soon = later(tick, 15000)  # within RETRY_MS of the first send
    busy = later(soon, 20000, f2={"state": ["moving"]})
    fallen = later(busy, 31000)
    fallen["mode"]["fortifications"][0]["hp"] = 0  # g1
    observations = [start, tick, soon, busy, fallen]
    probe = escalade.OrderProbe()
    batches = run(lambda: probe, observations)
    for orders, observation in zip(batches, observations, strict=True):
        validate_orders(orders, observation)
    assert batches[1] == [{"unit": "f2", "type": "besiege", "target": "w3", "run": True},
                          {"unit": "f7", "type": "besiege", "target": "w3", "run": True},
                          {"unit": "f4", "type": "besiege", "target": "g1", "run": True},
                          {"unit": "f13", "type": "attack_building", "target": "g1",
                           "run": False}]
    assert [[o["unit"] for o in orders] for orders in batches] == [
        [], ["f2", "f7", "f4", "f13"], [], ["f7", "f4", "f13"], ["f7"]]
    assert probe.metadata()["sent_ms"] == {"f2": [10000], "f7": [10000, 20000, 31000],
                                           "f4": [10000, 20000], "f13": [10000, 20000]}
    # f2 routing at 10 s gets no order; with f2 as the ram's crew, f3 climbs in its place.
    crewed = first_observation()
    crewed["mode"]["vehicles"][0]["crew"] = "f2"
    for observations, expected in (
            ([start, later(start, 10000, f2={"state": ["routing"]})],
             [("f7", "w3"), ("f4", "g1"), ("f13", "g1")]),
            ([crewed, later(crewed, 10000)],
             [("f3", "w3"), ("f7", "w3"), ("f2", "g1"), ("f13", "g1")])):
        orders = run(escalade.OrderProbe, observations)[1]
        validate_orders(orders, observations[1])
        assert [(o["unit"], o["target"]) for o in orders] == expected
    # degraded(): f2 cannot climb, the Grom has no ammunition, then the mode section failed.
    observations = degraded()
    batches = run(escalade.OrderProbe, observations)
    for orders, observation in zip(batches, observations, strict=True):
        validate_orders(orders, observation)
    assert [[o["unit"] for o in orders] for orders in batches] == [[], ["f7", "f4"], []]


def test_version_2_goes_from_c7_straight_to_c1():
    """A unit inside the front line with c7 ours: version 2 runs to c1, version 1 to c8, the
    nearer of c8 and c9. Wrong versions: version 2 with version 1's tiers; version 2's tiers
    leaking into version 1."""
    # Rests on JUDGEMENT escalade.py Witness v2 victory order and JUDGEMENT? Victory order.
    start = first_observation()
    inside = holding(later(start, 60000, f2={"x": -120.0, "z": -40.0}), c7="us")
    goes = {make.__name__: [(o["x"], o["z"]) for o in run(make, [start, inside])[1]
                            if o["unit"] == "f2"]
            for make in (escalade.Escalade, escalade.EscaladeV2)}
    assert goes == {"Escalade": [(-320, 320)], "EscaladeV2": [(0, 310)]}


def test_version_2_counts_g1_fallen_once_its_door_reads_hp_0():
    """At 165 s, after phase 2 by the clock, the door reads hp 0 while the gatehouse building
    reads 10%, as the 2026-11-03 Helmgart checkpoint read them (door 0 from 120 s, building
    3,061 to 423 hit points until 150 s). Version 2's crew walks to c7 and its Grom, whose
    attack_building on g1 the engine would keep in force (door_halts), gets a halt;
    BesiegeNearestV2's attack the visible enemy nearest them, and with none in view both get a
    halt. Version 1 still orders g1, and validation, left unchanged, accepts that. Wrong versions:
    version 2 keyed on g1's own hp; no order for the Grom once g1 counts as fallen."""
    # Rests on JUDGEMENT escalade.py Witness v2 door rule.
    start = first_observation()
    gates = [{"destroyed": False, "hp": 0, "name": "Gatehouse", "x": -32, "z": -16}]
    door = later(start, 165000, mode={"gates": gates})
    door["mode"]["fortifications"][0]["hp"] = 10  # g1
    unseen = deepcopy(door)
    unseen["enemy"] = []
    seen = {}
    for make, last in ((escalade.Escalade, door), (escalade.EscaladeV2, door),
                       (escalade.BesiegeNearest, door), (escalade.BesiegeNearestV2, door),
                       (escalade.BesiegeNearestV2, unseen)):
        orders = run(make, [start, later(start, 150000), last])[2]
        validate_orders(orders, last)
        seen[make.__name__, last is unseen] = {
            o["unit"]: (o["type"], (o["x"], o["z"]) if o["type"] == "move" else o.get("target"))
            for o in orders if o["unit"] in ("f4", "f13")}
    halt = ("halt", None)
    assert seen == {
        ("Escalade", False): {"f4": ("besiege", "g1"), "f13": ("attack_building", "g1")},
        ("EscaladeV2", False): {"f4": ("move", (-1, 155)), "f13": halt},
        ("BesiegeNearest", False): {"f4": ("besiege", "g1"), "f13": ("attack_building", "g1")},
        ("BesiegeNearestV2", False): {"f4": ("attack", "e2"), "f13": ("attack", "e2")},
        ("BesiegeNearestV2", True): {"f4": halt, "f13": halt}}
    assert {make().metadata()["version"] for make in V2} == {2}


@pytest.mark.parametrize("make", [escalade.EscaladeV2, escalade.ConcentrateV2,
                                  escalade.CavalryEarlyV2, escalade.PiecemealV2,
                                  escalade.GateOnlyV2])
def test_version_2_staging_spots_stand_40_m_apart(make):
    """Phase 1's move orders on the fixture (ShootOnlyV2's are its firing spots, version 1's).
    Wrong version: version 1's staging, whose Concentrate pairs stand 15.7 m apart and whose
    GateOnly West and East rows share their spots."""
    # 40 m rests on JUDGEMENT escalade.py Witness v2 staging.
    spots = [(o["x"], o["z"]) for o in run(make, [first_observation()])[0] if o["type"] == "move"]
    assert len(spots) >= 11 and min(math.dist(a, b) for a, b in combinations(spots, 2)) >= 40


def test_version_2_flank_rows_stand_off_the_pieces_as_the_witness_does():
    """Each flank group's spot nearest a listed piece, in EscaladeV2 and ConcentrateV2: 150 m or
    more, and the two arms within 10 m. Wrong version: version 1's rows 150 m south of the target
    (Concentrate's 117 and 119 m against the witness's 144 m). ConcentrateV2 still differs from
    EscaladeV2 only in West's and East's orders."""
    # 150 m rests on JUDGEMENT escalade.py Witness v2 staging.
    start = first_observation()
    pieces = [(p["x"], p["z"]) for p in FORTIFICATIONS]
    standoff = {}
    for make in (escalade.EscaladeV2, escalade.ConcentrateV2):
        policy = make()
        orders = policy.decide(play.public(start, {}))
        for name in ("west", "east"):
            members = policy.metadata()["groups"][name]
            standoff[name, make.__name__] = min(math.dist((o["x"], o["z"]), p) for p in pieces
                                                for o in orders if o["unit"] in members)
    assert min(standoff.values()) >= 150
    assert all(abs(standoff[name, "EscaladeV2"] - standoff[name, "ConcentrateV2"]) <= 10
               for name in ("west", "east"))
    groups = escalade.EscaladeV2()
    groups.decide(play.public(start, {}))
    flanks = groups.metadata()["groups"]["west"] + groups.metadata()["groups"]["east"]
    assert {0, 1} <= set(assert_ablation(escalade.EscaladeV2, escalade.ConcentrateV2, timed(),
                                         units=flanks))
