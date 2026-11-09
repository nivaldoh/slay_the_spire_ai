"""The walled siege defence witness and its controls (wall_defence.py) on scripted Helmgart
timelines.

Every observation starts from wh3_helmgart's recorded Helmgart first observation (capture points,
gate, slots, supplies and the garrison's recorded starts); the timelines move units by hand.
Offline only: this shows which orders the scripts give, not what the engine does with them.
"""

import random
from copy import deepcopy

import pytest
from wh3_ablation import assert_ablation
from wh3_helmgart import GARRISON, SCENARIO, first_observation, garrison

from twwarhammer3.battle import controllers, play, wall_defence
from twwarhammer3.protocol import HIDDEN_KEYS, PolicyFailure, validate_orders

SPEAR = "wh_main_emp_inf_spearmen_0"
LABELS = ("lord", "jade_a", "jade_b", "spear_a", "archers_a", "archers_b", "crossbows",
          "spear_b", "cannon", "rockets")  # GARRISON's order
IDS = {label: f"f{index}" for index, label in enumerate(LABELS, 1)}
_draw = random.Random(3)
SHUFFLED = dict(zip(LABELS, _draw.sample(list(IDS.values()), len(LABELS))))
MISSILE = ("archers_a", "archers_b", "crossbows", "cannon", "rockets")
RESERVE = ("lord", "jade_a", "jade_b")
C7 = (-1, 155)
# The fire at will state each frame shows: on by engine default, then as the witness last set it.
FIRE_ON = {5, 85, 90, 105, 110, 135}


def enemy(identity, kind, x, z, *states):
    return {"id": identity, "type": kind, "class": "infantry", "x": x, "z": z, "bearing": 0,
            "men": 90, "men0": 90, "hp": 1, "state": list(states)}


def breach(t, cue="gatehouse"):
    """D1 approaches from 30 s; e2 stands 50 m from the wall line at 80-85 s and routs there
    at 90 s; e3 is inside, 23 m north of the line, at 100-105 s and dead from 110 s; from 120 s
    the Gatehouse is enemy-held (``cue`` "gatehouse") or the gate reads hp 0 with destroyed
    false (``cue`` "gate"; "none": hp 50); e4 stands 51 m from the Key Building from 130 s."""
    spear, sword = "wh_main_emp_inf_spearmen_0", "wh_main_emp_inf_swordsmen"
    z = -400 + 4 * (t - 30)
    seen = []
    if t >= 30:
        seen = [enemy("e2", spear, -44, min(z, -80)), enemy("e3", spear, -4, min(z, -200)),
                enemy("e4", spear, 36, min(z, -200)), enemy("e5", sword, 76, min(z, -200))]
    if 80 <= t:
        seen[0] = enemy("e2", spear, -44, -80, *(["routing"] if t >= 90 else []))
    if 100 <= t < 110:
        seen[1] = enemy("e3", spear, -4, 0, "melee")
    elif t >= 110:
        seen.pop(1)
    if t >= 130:
        seen = [unit if unit["id"] != "e4" else enemy("e4", spear, 10, 260, "moving")
                for unit in seen]
    return seen, (cue if t >= 120 else None)


def frame(t, cue="gatehouse", ids=IDS, order=LABELS, moving_from=120, last=135):
    observation = first_observation()
    time_ms = t * 1000
    observation.update(time_ms=time_ms, seq=t, remaining_ms=1200000 - time_ms)
    units = {label: unit for label, unit in zip(LABELS, garrison([ids[name] for name in LABELS]),
                                                strict=True)}
    for label in MISSILE:
        units[label]["behaviours"]["fire_at_will"] = t in FIRE_ON
    for index, label in enumerate(RESERVE):
        if 5 < t < 20:
            units[label]["state"] = ["moving", "running"]
        elif t >= 20:
            units[label].update(x=C7[0] + 10 * (index - 1), z=C7[1])
    if t > moving_from:
        for unit in units.values():
            unit["state"] = ["moving", "running"]
    observation["friendly"] = [units[label] for label in order]
    observation["enemy"], fallen = breach(t, cue)
    mode = observation["mode"]
    if fallen == "gatehouse":
        mode["capture_points"][1]["holder"] = "enemy"
    elif fallen in ("gate", "none"):
        mode["gates"][0].update(hp=0 if fallen == "gate" else 50, destroyed=False)
    # Hidden sections that know more than the public ones: e3 stays behind the wall, unseen.
    observation["evaluation"]["enemy"] = {"e3": {"x": -4, "z": 40}}
    observation["native"] = {"units": [{"id": "e3", "x": -4, "z": 40}]}
    if t != 5:
        observation.pop("setup")
    if t == last:
        observation.update(result="won", final={"result": "won"})
    return observation


def battle(cue="gatehouse", ids=IDS, order=LABELS, moving_from=120):
    """Frames every 5 s; every unit reads moving after ``moving_from`` s (an order to move)."""
    return [frame(t, cue, ids, order, moving_from) for t in range(5, 136, 5)]


def decisions(policy, observations, view=lambda observation: play.public(observation, {})):
    """Each batch the policy gives on what it may read of each observation, checked by
    validate_orders as play checks it, every order then acknowledged as applied."""
    batches = []
    for request, observation in enumerate(observations, 1):
        seen = view(deepcopy(observation))
        batch = policy.decide(seen)
        validate_orders(batch, seen)
        batches.append(batch)
        policy.acknowledge({"request": f"r{request}", "results": [
            {"index": index, "unit": order["unit"], "ok": True}
            for index, order in enumerate(batch, 1)]}, {})
    return batches


def named(batches, observations, ids=IDS):
    """Battle second -> sorted (unit label, order type, target or point or setting)."""
    label = {identity: name for name, identity in ids.items()} | {"army": "army"}
    result = {}
    for observation, batch in zip(observations, batches, strict=True):
        rows = sorted((label[o["unit"]], o["type"],
                       o.get("target") or o.get("slot") or o.get("enabled")
                       if o["type"] != "move" else (o["x"], o["z"])) for o in batch)
        if rows:
            result[observation["time_ms"] // 1000] = rows
    return result


def fire(enabled):
    return [(label, "behaviour", enabled) for label in MISSILE]


def test_the_witness_builds_rations_fire_answers_a_breach_and_falls_back():
    policy = wall_defence.WallWitness()
    observations = battle()
    orders = named(decisions(policy, observations), observations)
    spots = {row[0]: row[2] for row in orders[120]}
    assert set(spots) == set(LABELS) and len(set(spots.values())) == 10
    assert all(((x - 0) ** 2 + (z - 310) ** 2) ** .5 <= 80 for x, z in spots.values())
    assert orders == {
        5: sorted([("army", "build", f"s{n}") for n in range(1, 9)] + fire(False)
                  + [(label, "move", C7) for label in RESERVE]),
        80: sorted(fire(True)),  # e2 50 m from the wall line
        90: sorted(fire(False)),  # e2 routs
        100: sorted(fire(True)),  # e3 inside, first decision
        105: sorted((label, "attack", "e3") for label in RESERVE),  # second decision inside
        110: sorted(fire(False) + [(label, "move", C7) for label in RESERVE]),  # e3 dead
        120: sorted((label, "move", spots[label]) for label in LABELS),  # Gatehouse lost
        130: sorted(fire(True) + [(label, "attack", "e4") for label in LABELS])}
    assert policy.metadata()["cues"] == {"fire_ms": 80000, "reserve_ms": 105000,
                                         "fallback_ms": 120000}
    assert policy.metadata()["triggers"] == {"fire_ms": 80000, "breach_ms": 105000,
                                             "fallback_ms": 120000}
    assert policy.metadata()["builds_accepted"] == [f"s{n}" for n in range(1, 9)]
    first = decisions(wall_defence.WallWitness(), observations[:1])[0]
    assert {o["option"] for o in first if o["type"] == "build"} == {"tower_piercing_1"}
    assert all(o["run"] is True for o in first if o["type"] == "move")


@pytest.mark.parametrize("cue,reason", [("gate", "gate"), ("none", None)])
def test_a_gate_at_hp_0_starts_the_fallback_though_it_reads_not_destroyed(cue, reason):
    policy = wall_defence.WallWitness()
    observations = battle(cue)
    orders = named(decisions(policy, observations), observations)
    assert policy.metadata()["fallback_reason"] == reason
    assert (120 in orders) is (reason is not None)


def test_each_ablation_differs_from_the_witness_only_in_its_rule():
    reserve = {IDS[label] for label in RESERVE}
    for cue in ("gatehouse", "gate", "none"):
        observations = battle(cue)
        fallback_ms = 120000 if cue != "none" else None
        assert_ablation(wall_defence.WallWitness, wall_defence.WFire, observations, rules={
            "fire at will": lambda observation, order: order["type"] == "behaviour"})
        assert_ablation(wall_defence.WallWitness, wall_defence.WReserve, observations, rules={
            "reserve before the fallback": lambda observation, order, at=fallback_ms:
                order["unit"] in reserve and (at is None or observation["time_ms"] < at)})
        assert_ablation(wall_defence.WallWitness, wall_defence.HoldBuild, observations, rules={
            "everything but builds": lambda observation, order: order["type"] != "build"})
        if fallback_ms:
            assert_ablation(wall_defence.WallWitness, wall_defence.WNoFallback, observations,
                            rules={"from the fallback cue": lambda observation, order:
                                   observation["time_ms"] >= fallback_ms})
    # Each ablation still records the cue of the rule it lacks.
    for make, cue in ((wall_defence.WFire, "fire_ms"), (wall_defence.WReserve, "reserve_ms"),
                      (wall_defence.WNoFallback, "fallback_ms")):
        policy = make()
        decisions(policy, battle())
        assert policy.metadata()["cues"][cue] is not None


def test_keep_only_holds_the_key_building_from_the_first_decision():
    observations = battle(moving_from=5)
    policy = wall_defence.KeepOnly()
    orders = named(decisions(policy, observations), observations)
    plain = battle()
    witness = named(decisions(wall_defence.WallWitness(), plain), plain)
    assert orders[5] == sorted([("army", "build", f"s{n}") for n in range(1, 9)] + witness[120])
    assert orders[130] == sorted((label, "attack", "e4") for label in LABELS)
    assert set(orders) == {5, 130}
    assert policy.metadata()["fallback_reason"] == "start"
    # Its own start is no decision cue: the Gatehouse falls at 120 s.
    assert policy.metadata()["triggers"]["fallback_ms"] == 5000
    assert policy.metadata()["cues"]["fallback_ms"] == 120000


def placed(observations, identity, x, z, seconds, kind="wh_main_emp_inf_spearmen_0", *states):
    """The timeline with enemy ``identity`` standing at (x, z) at each of ``seconds``."""
    for observation in observations:
        if observation["time_ms"] // 1000 in seconds:
            observation["enemy"] = [e for e in observation["enemy"] if e["id"] != identity] + [
                enemy(identity, kind, x, z, *states)]
    return observations


def cues(make, observations):
    policy = make()
    decisions(policy, observations)
    return policy.metadata()["cues"], policy.metadata()["triggers"]


def test_an_ablation_counts_on_the_designs_decision_cues_not_on_its_rules_triggers():
    # Decision 1: e2 halts 101 m from the wall line, inside the cue's 150 m but beyond the
    # fire rule's 60 m, while 14 of the 18 roster units were never seen within 300 m.
    short = placed(battle(), "e2", -44, -130, range(80, 100))
    assert cues(wall_defence.WFire, short)[0]["fire_ms"] == 80000
    assert cues(wall_defence.WFire, short)[1]["fire_ms"] == 100000  # e3 inside
    # Eight more units seen 250 m out leave only 6 roster units never within 300 m: no cue.
    crowd = battle()
    for number in range(6, 14):
        placed(crowd, f"e{number}", -200 + 40 * number, -280, range(30, 136))
    assert cues(wall_defence.WFire, crowd) == (
        {"fire_ms": None, "reserve_ms": 105000, "fallback_ms": 120000},
        {"fire_ms": 80000, "breach_ms": 105000, "fallback_ms": 120000})
    # Decision 2: e3 and e4 inside together for two decisions are the design's reversal case,
    # not its cue; e6, inside routing at 110 s and rallied at 115 s, is not yet confirmed; e4
    # alone inside for two decisions from 130 s is the cue.
    double = placed(battle(), "e4", 36, 0, (100, 105))
    placed(double, "e6", -30, 0, (110,), SPEAR, "routing")
    placed(double, "e6", -30, 0, (115,), SPEAR)
    assert cues(wall_defence.WReserve, double)[0]["reserve_ms"] == 135000
    assert cues(wall_defence.WReserve, double)[1]["breach_ms"] == 105000


def test_the_reserve_holds_its_place_while_an_unconfirmed_enemy_is_inside():
    # e3 dies at 110 s as e6 comes inside: the reserve stays where it is (it goes back to c7
    # only once no visible enemy is inside), then attacks e6 at its second decision inside.
    observations = placed(battle(), "e6", -30, 0, (110, 115), kind="wh_main_emp_inf_swordsmen")
    orders = named(decisions(wall_defence.WallWitness(), observations), observations)
    assert 110 not in orders
    assert [row for row in orders[115] if row[0] in RESERVE] == [
        (label, "attack", "e6") for label in sorted(RESERVE)]


def test_inside_means_ten_metres_north_of_the_wall_line_through_the_public_points():
    policy = wall_defence.WallWitness()
    policy.decide(play.public(frame(5), {}))
    # At x = -4 the line runs from c5 (-62, -31) to c2 (-2, -22.5): z = -31 + 8.5 * 58 / 60.
    line = -31 + 8.5 * 58 / 60
    assert not policy.inside({"x": -4, "z": line + 9.9})
    assert policy.inside({"x": -4, "z": line + 10.1})
    # The ends are flat at z = -81 out to the map's sides, and beyond them.
    assert policy.inside({"x": -400, "z": -70}) and not policy.inside({"x": 300, "z": -72})
    assert abs(policy.wall_distance({"x": 188, "z": -141}) - 60) < 1e-9  # straight below c3


class Public(dict):
    """An observation that fails the test when a hidden key is read."""

    def __getitem__(self, key):
        assert key not in HIDDEN_KEYS, key
        return super().__getitem__(key)

    def get(self, key, default=None):
        assert key not in HIDDEN_KEYS, key
        return super().get(key, default)


ARMS = [wall_defence.WallWitness, wall_defence.HoldBuild, wall_defence.KeepOnly,
        wall_defence.WFire, wall_defence.WReserve, wall_defence.WNoFallback]


@pytest.mark.parametrize("make", ARMS)
def test_no_arm_reads_a_hidden_section_or_the_briefing(make):
    # The hidden sections place e3 behind the wall, unseen, so a read that slips past the guard
    # still changes orders; the waves briefing reaches them through play.public's scenario.
    observations = battle()
    assert all(key in observations[0] for key in ("evaluation", "native", "setup"))
    assert decisions(make(), observations, view=Public) == decisions(make(), observations)
    briefed = decisions(make(), observations, view=lambda o: play.public(o, SCENARIO))
    assert briefed == decisions(make(), observations)


def test_roles_bind_by_type_and_frozen_start_never_by_id_or_list_order():
    assert [unit["type"] for unit in garrison()] == GARRISON
    assert any(SHUFFLED[label] != IDS[label] for label in LABELS)
    order = tuple(random.Random(4).sample(LABELS, len(LABELS)))
    for make in ARMS:
        plain = battle()
        mixed = battle(ids=SHUFFLED, order=order)
        assert named(decisions(make(), mixed), mixed, SHUFFLED) == named(
            decisions(make(), plain), plain)
    short = play.public(frame(5), {})
    short["friendly"] = short["friendly"][1:]
    with pytest.raises(PolicyFailure, match="ten placed units") as refused:
        wall_defence.WallWitness().decide(short)
    assert not play.is_forfeit(refused.value)  # the episode ends; the army does not just stand
    elsewhere = play.public(frame(5), {})
    elsewhere["mode"]["capture_points"][6]["key"] = "capture_point_tower_only"
    with pytest.raises(PolicyFailure, match="capture points"):
        wall_defence.WallWitness().decide(elsewhere)
    for make in ARMS:
        name = f"twwarhammer3.battle.wall_defence:{make.__name__}"
        assert controllers.controller_class(name) is make
