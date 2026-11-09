"""The siege attack's witness and controls (battle/escalade.py) for ksl-emp-siege-a-v1, on the
offline Helmgart fixture wh3_siege_attack.py (the declaration is test_wh3_siege_assault.py's).

Reference: the 2026-11-08 siege-attack design (runs/siege-evals-20261108/final-izmail.md,
Settings, Rosters, Controls, Witness "Escalade v1", Infrastructure I7) and portfolio.md's
corrections (gate_breached; the private record in place of I6). Offline only: these show what
the scripts order on a fixture whose fortification pieces nobody has read, not what the engine
does with the orders, that the cards recruit or that a ram goes to the gate.
"""

import random

import pytest
from wh3_ablation import assert_ablation, run
from wh3_siege_attack import SCENARIO, first_observation, later

from twwarhammer3.battle import escalade, play
from twwarhammer3.battle.replay_schedule import digest
from twwarhammer3.protocol import validate_orders


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
    # An enemy within 50 m of the Lancers: they attack it before the gate falls.
    lancers = later(observations[0], 60000, f12={"x": -32.0, "z": -36.0},
                    e2={"x": -20.0, "z": -40.0})
    policy = escalade.CavalryEarly()
    policy.decide(play.public(observations[0], {}))
    assert [o for o in policy.decide(play.public(lancers, {})) if o["unit"] == "f12"] == [
        {"unit": "f12", "type": "attack", "target": "e2", "mode": "auto", "run": True,
         "queue": False}]


@pytest.mark.parametrize("make", [escalade.Escalade, escalade.Concentrate,
                                  escalade.CavalryEarly, escalade.Piecemeal,
                                  escalade.ShootOnly, escalade.GateOnly,
                                  escalade.BesiegeNearest])
def test_every_arm_orders_only_what_validation_accepts(make):
    for observations in (sequence(), timed()):
        for orders, observation in zip(run(make, observations), observations,
                                       strict=True):
            validate_orders(orders, observation)


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
