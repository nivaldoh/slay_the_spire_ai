"""The two-front defence witness and its arms (battle/lines.py) on made-up observations built
from the ksl-nor-lines-a-v1 and -b-v1 declarations.

Reference: final-alesia.md "Witness and its arms" and deciding check 8 in runs/siege-evals-20261108
(untracked), and portfolio.md S8 for the ablation diff (wh3_ablation.py). Offline only: these show
what the scripts order on made-up positions, not what the engine or the native AI does with them.
"""

import itertools
import math
from copy import deepcopy

import pytest
import wh3_ablation
from wh3_ablation import assert_ablation

from twwarhammer3.battle import calibration, lines, play, setup
from twwarhammer3.protocol import PolicyFailure, validate_orders

A = setup.scenarios()["ksl-nor-lines-a-v1"]
B = setup.scenarios()["ksl-nor-lines-b-v1"]
ARMS = (lines.LinesWitness, lines.LinesByMen, lines.LinesCentral)
# The mirror axis of the two cases; rests on JUDGEMENT docs/twwarhammer3/lines-eval.md Lines
# layout.
MIRROR_X = 130
LINE = {"wh3_main_ksl_inf_kossars_1", "wh3_main_ksl_inf_armoured_kossars_0",
        "wh3_main_ksl_inf_streltsi_0"}
# Assumed men at large scale (table num_men x 0.75, unread in battle).
MEN = {"wh_main_nor_inf_chaos_marauders_0": 90, "wh_dlc08_nor_inf_marauder_spearman_0": 90,
       "wh_dlc08_nor_inf_marauder_hunters_0": 68, "wh_main_nor_cav_marauder_horsemen_0": 45,
       "wh_dlc08_nor_inf_marauder_champions_0": 75, "wh_dlc08_nor_inf_marauder_berserkers_0": 75,
       "wh_dlc08_nor_mon_fimir_0": 12}
HEAVY = {"wh_dlc08_nor_inf_marauder_champions_0", "wh_dlc08_nor_inf_marauder_berserkers_0",
         "wh_dlc08_nor_mon_fimir_0"}
# Unit ids follow declaration order: f4 the Boyar, f5 the Tzar Guard, f6 and f7 the Lancers,
# f8 and f9 the west sector, e5 and e6 the case-a Champions.
MOVERS = {"f4", "f5", "f6", "f7"}
RESERVE, LANCERS = {"f4", "f5"}, {"f6", "f7"}
POSTS = {"west": {"x": 35, "z": -265}, "east": {"x": 225, "z": -265}}
BOYAR_POSTS = {"west": {"x": 35, "z": -250}, "east": {"x": 225, "z": -250}}
WAYPOINTS = {"west": {"x": -100, "z": -305}, "east": {"x": 360, "z": -305}}
JOB = "lines-r1-017"


def battle(scenario, steps=45, ids=None):
    """Observations 2 s apart of a made-up fight. Each enemy walks straight at the nearest line
    regiment's start (town side 3 m/s, relief 3.5, the Horsemen 7) and stops 3 m short, where it
    and that regiment read melee. The relief is out of sight at the first observation; friendly
    units stay at their starts. ``ids`` renames friendly units and reverses their list."""
    friendly = [dict(p, id=f"f{i}") for i, p in enumerate(scenario["deployment"]["friendly"], 1)]
    enemy = [dict(p, id=f"e{i}") for i, p in enumerate(scenario["deployment"]["enemy"], 1)]
    line = [unit for unit in friendly if unit["type"] in LINE]
    observations = []
    for step in range(steps):
        seconds, fighting, seen = 1 + 2 * step, set(), []
        for unit in enemy:
            goal = min(line, key=lambda own: math.dist((own["x"], own["z"]),
                                                       (unit["x"], unit["z"])))
            gap = math.dist((goal["x"], goal["z"]), (unit["x"], unit["z"]))
            speed = (7.0 if "horsemen" in unit["type"] else 3.0 if unit["z"] > -165 else 3.5)
            walked = min(speed * seconds, gap - 3)
            if walked == gap - 3:
                fighting |= {unit["id"], goal["id"]}
            if step == 0 and unit["z"] < -295:
                continue
            seen.append({"id": unit["id"], "type": unit["type"], "class": "infantry",
                         "x": unit["x"] + (goal["x"] - unit["x"]) * walked / gap,
                         "z": unit["z"] + (goal["z"] - unit["z"]) * walked / gap,
                         "bearing": unit["bearing"], "men": MEN[unit["type"]],
                         "men0": MEN[unit["type"]], "hp": 1.0,
                         "state": ["melee"] if unit["id"] in fighting else ["moving"]})
        own = [{"id": unit["id"], "type": unit["type"], "class": "infantry", "x": unit["x"],
                "z": unit["z"], "bearing": unit["bearing"], "men": 60, "men0": 60, "hp": 1.0,
                "state": ["melee"] if unit["id"] in fighting else [], "target": None,
                "behaviours": ({"defend": False, "fire_at_will": False, "skirmish": True}
                               if unit["type"] in LINE else {})} for unit in friendly]
        if ids:
            own = [dict(unit, id=ids[unit["id"]]) for unit in reversed(own)]
        observations.append({
            "schema": 1, "job": JOB, "battle": "b1", "seq": step + 1, "phase": "Deployed",
            "time_ms": 1000 * seconds, "speed": 1, "remaining_ms": 1200000 - 1000 * seconds,
            "mode": {"type": "land_normal", "role": "defender", "timeout_winner": "us"},
            "terrain": {"bounds": {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}},
            "friendly": own, "enemy": seen,
            "enemy_roster": [{"id": unit["id"], "type": unit["type"]} for unit in enemy]})
    return observations


def run(make, observations):
    """The policy after the run, and its orders at each observation (wh3_ablation.run: what
    play.public hands a controller, every order acknowledged as applied). Every batch must pass
    the order checks play applies before sending it."""
    made = []
    decisions = wh3_ablation.run(lambda: made.append(make()) or made[-1], observations)
    for observation, orders in zip(observations, decisions, strict=True):
        validate_orders(orders, play.public(observation, {}))
    return made[0], decisions


def raw_run(make, observations):
    """Orders from the observations as given, hidden keys included, as a replay tool that does
    not strip them would hand a controller."""
    policy, decisions = make(), []
    for observation in observations:
        orders = deepcopy(policy.decide(deepcopy(observation)))
        decisions.append(orders)
        policy.acknowledge({"request": "r", "based_on": observation["seq"],
                            "applied_ms": observation["time_ms"],
                            "results": [{"index": index, "unit": order["unit"], "ok": True}
                                        for index, order in enumerate(orders, 1)]}, {})
    return decisions


def normal(orders):
    """Orders as a sorted list of item tuples, floats rounded, facing taken modulo 360."""
    rows = []
    for order in orders:
        row = dict(order)
        if row.get("facing") is not None:
            row["facing"] = round(row["facing"], 4) % 360
        rows.append(tuple(sorted((key, round(value, 4) if isinstance(value, float) else value)
                                 for key, value in row.items())))
    return sorted(rows, key=repr)


def first_move(decisions, unit):
    return next((order for orders in decisions for order in orders
                 if order["unit"] == unit and order["type"] == "move"), None)


def at(point, order):
    """Whether ``order`` exists and its destination is within 0.5 m of ``point``."""
    return order is not None and math.dist((point["x"], point["z"]),
                                           (order["x"], order["z"])) < 0.5


def test_witness_takes_the_costlier_side_and_the_men_arm_the_lighter_one_in_both_cases():
    """W sends the reserve and the Lancers to the heavy group's side in both cases, M to the
    light group's (more men, less cost) and C nowhere. The Tzar Guard posts 30 m behind the
    sector, the Boyar 15 m behind it. Wrong versions: M's rule flag unwired (M goes where W
    goes); W weighing by men; W reading the case from anything but positions; the Boyar posted
    in front of the Tzar Guard."""
    for scenario, heavy, light in ((A, "west", "east"), (B, "east", "west")):
        observations = battle(scenario)
        for arm, side in ((lines.LinesWitness, heavy), (lines.LinesByMen, light)):
            policy, decisions = run(arm, observations)
            assert policy.metadata()["side"] == side, (scenario["name"], arm)
            assert at(POSTS[side], first_move(decisions, "f5"))
            assert at(BOYAR_POSTS[side], first_move(decisions, "f4"))
            assert at(WAYPOINTS[side], first_move(decisions, "f6"))
        policy, decisions = run(lines.LinesCentral, observations)
        assert policy.metadata()["side"] is None
        assert not [order for orders in decisions for order in orders if order["unit"] in MOVERS]


def test_case_b_gives_the_mirror_image_of_case_a_orders():
    """Case b mirrors every enemy placement and the friendly army is its own mirror image, so
    each arm's orders in b must be its case-a orders mirrored about x = 130, unit for mirrored
    unit. Wrong versions: a side rule, waypoint or post that favours one side."""
    friendly = A["deployment"]["friendly"]
    slot = {(p["type"], p["x"], p["z"]): f"f{i}" for i, p in enumerate(friendly, 1)}
    twin = {f"f{i}": slot[(p["type"], 2 * MIRROR_X - p["x"], p["z"])]
            for i, p in enumerate(friendly, 1)}
    for arm in ARMS:
        policy_a, orders_a = run(arm, battle(A))
        policy_b, orders_b = run(arm, battle(B))
        sides = {None: None, "west": "east", "east": "west"}
        assert policy_b.metadata()["side"] == sides[policy_a.metadata()["side"]]
        lopsided = 0
        for step, (left, right) in enumerate(zip(orders_a, orders_b, strict=True)):
            mirrored = [{**order, "unit": twin[order["unit"]],
                         **({"x": 2 * MIRROR_X - order["x"]} if "x" in order else {}),
                         **({"facing": (360 - order["facing"]) % 360}
                            if order.get("facing") is not None else {})} for order in left]
            assert normal(mirrored) == normal(right), (arm, step)
            lopsided += normal(mirrored) != normal(left)
        assert lopsided, f"{arm.__name__}: no step tells the two cases apart"


def test_each_arm_changes_only_the_reserve_and_lancer_orders_and_never_follows_the_job():
    """M and C differ from W only in the Boyar's, the Tzar Guard's and the Lancers' orders, and
    where both side rules agree W and M give the same orders throughout. Wrong versions: an arm
    flag that also changes the lines; an unwired M (no order differs); orders that follow the
    job name, which reaches controllers."""
    observations = battle(A)
    for arm in (lines.LinesByMen, lines.LinesCentral):
        assert assert_ablation(lines.LinesWitness, arm, observations, units=MOVERS)
    agreed = deepcopy(A)  # a Fimir and a Spearmen swap places: the west is heavier both ways
    enemy = agreed["deployment"]["enemy"]
    fimir = next(p for p in enemy if p["type"] == "wh_dlc08_nor_mon_fimir_0")
    spear = next(p for p in enemy if (p["x"], p["z"]) == (205, -445))
    fimir["type"], spear["type"] = spear["type"], fimir["type"]
    observations = battle(agreed)
    for arm in (lines.LinesWitness, lines.LinesByMen):
        assert run(arm, observations)[0].metadata()["side"] == "west"
    assert assert_ablation(lines.LinesWitness, lines.LinesByMen, observations) == []


def hidden(observation, other):
    """``observation`` carrying the hidden keys a recorded one has. Their contents point the
    other way: the private reading puts every enemy at its place in ``other``, and the true
    strength makes the heavy types the larger by men."""
    friendly = other["deployment"]["friendly"]
    return {**observation,
            "evaluation": {"version": 2, "friendly": {"men": 720, "men0": 720},
                           "enemy": {"men": 890, "men0": 890, "active_men": 890,
                                     "by_type": {key: {"men": 900 if key in HEAVY else 10}
                                                 for key in MEN}}},
            "setup": {"deployment_reading": {
                "friendly": [dict(p, id=f"f{i}") for i, p in enumerate(friendly, 1)],
                "enemy": [dict(p, id=f"e{i}")
                          for i, p in enumerate(other["deployment"]["enemy"], 1)]}},
            "final": {"friendly": {"men": 1}, "enemy": {"men": 1}},
            "native": {"local_alliance": 1, "local_army": 1}}


def test_hidden_fields_change_no_order():
    """Hidden keys are stripped before a controller sees an observation, but the scripts must
    not depend on them where a tool forgets to strip them. Wrong versions: a witness that reads
    evaluation (true men or totals) or the private first reading in setup."""
    observations = battle(A)
    for arm in ARMS:
        expected = raw_run(arm, observations)
        assert raw_run(arm, [hidden(o, B) for o in observations]) == expected, arm
        assert raw_run(arm, [hidden(o, A) for o in observations]) == expected, arm


def test_roles_bind_once_by_type_and_start_position_not_by_id():
    """Renaming and reordering the friendly units renames the orders and changes nothing else,
    a regiment that has moved goes back to its own start, and any army but the declared one, or
    a unit not seen at binding, is refused. Wrong versions: roles by id order; roles or posts
    read again from current positions; no check of the army."""
    renamed = {f"f{i}": f"f{13 - i}" for i in range(1, 13)}
    back = {new: old for old, new in renamed.items()}
    observations, permuted = battle(A), battle(A, ids=renamed)
    for arm in ARMS:
        expected = run(arm, observations)[1]
        got = run(arm, permuted)[1]
        for step, (left, right) in enumerate(zip(expected, got, strict=True)):
            assert normal(left) == normal([{**o, "unit": back[o["unit"]]} for o in right]), step
    moved = deepcopy(observations[:3])
    for observation in moved[1:]:
        streltsi = next(u for u in observation["friendly"] if u["id"] == "f9")
        streltsi["z"] += 30
    order = first_move(run(lines.LinesWitness, moved)[1], "f9")
    assert at({"x": 60, "z": -295}, order)
    other = deepcopy(observations[0])  # a second Tzar Guard in place of a Lancer
    next(u for u in other["friendly"] if u["id"] == "f6")["type"] = "wh3_main_ksl_inf_tzar_guard_0"
    with pytest.raises(PolicyFailure, match="declared Kislev army"):
        lines.LinesWitness().decide(other)
    policy, stranger = lines.LinesWitness(), deepcopy(observations[1])
    policy.decide(deepcopy(observations[0]))
    stranger["friendly"][0]["id"] = "f99"
    with pytest.raises(PolicyFailure, match="did not bind"):
        policy.decide(stranger)


def test_the_line_regiments_must_stand_three_north_and_five_south():
    """The middle Kossars (f10) start on the inner line: four north, four south. Wrong version
    (2026-11-13 refusal sweep): without the refusal the roles are bound with four regiments in
    each line, so the sectors and posts come from another formation."""
    first = deepcopy(battle(A)[0])
    next(u for u in first["friendly"] if u["id"] == "f10")["z"] = -165
    with pytest.raises(PolicyFailure, match="three regiments north, five south"):
        lines.LinesWitness().decide(first)


def test_the_witness_refuses_a_relief_unit_it_has_no_lobby_cost_for():
    """Scoring by lobby cost needs every relief type's cost. Wrong version (2026-11-13 refusal
    sweep): without the refusal the unknown type fails as a KeyError instead."""
    first, later = battle(A)[:2]
    policy = lines.LinesWitness()
    policy.decide(deepcopy(first))
    frame = deepcopy(later)
    relief = {"e5", "e8", "e9", "e10", "e11", "e12"}
    frame["enemy"] = [u for u in frame["enemy"] if u["id"] in relief | {"e1", "e2", "e3", "e4"}]
    next(u for u in frame["enemy"] if u["id"] == "e8")["type"] = "wh_dlc08_nor_mon_war_mammoth_0"
    with pytest.raises(PolicyFailure, match="no lobby cost for 'wh_dlc08_nor_mon_war_mammoth_0'"):
        policy.decide(frame)

def test_line_regiments_set_guard_and_keep_a_leash_from_their_own_posts():
    """At the first decision each of the eight line regiments sets guard and fire at will on and
    skirmish off, and no other unit gets a setting. An outer regiment pulled 40 m out of line
    goes back to its post facing south and does not attack an enemy 25 m from it but 65 m from
    the post; an inner one pulled out goes back facing north. Wrong versions: skirmish left on,
    guard off or no settings sent; the leash measured from where the regiment stands; both
    lines facing the same way."""
    observations = battle(A)
    first = run(lines.LinesWitness, observations[:1])[1][0]
    settings = sorted((o["unit"], o["behaviour"], o["enabled"])
                      for o in first if o["type"] == "behaviour")
    wanted = {"defend": True, "fire_at_will": True, "skirmish": False}
    assert settings == sorted((f"f{i}", key, value) for i in (1, 2, 3, 8, 9, 10, 11, 12)
                              for key, value in wanted.items())
    policy = lines.LinesWitness()
    for observation in observations[:2]:
        policy.decide(deepcopy(observation))
    frame = deepcopy(observations[1])
    frame.update(seq=3, time_ms=5000)
    next(u for u in frame["friendly"] if u["id"] == "f9").update(z=-335)
    next(u for u in frame["friendly"] if u["id"] == "f2").update(z=-195)
    next(u for u in frame["enemy"] if u["id"] == "e5").update(x=60, z=-360)
    orders = policy.decide(frame)
    for unit, post, facing in (("f9", {"x": 60, "z": -295}, 180), ("f2", {"x": 130, "z": -165}, 0)):
        given = [o for o in orders if o["unit"] == unit and o["type"] != "behaviour"]
        assert [o["type"] for o in given] == ["move"] and at(post, given[0]), unit
        assert given[0]["facing"] == pytest.approx(facing), unit


def test_the_side_is_chosen_only_once_six_enemies_stand_ahead_of_the_outer_line():
    """Case a with the relief coming into sight a few units at a time: with the four east units
    and one west Champion ahead (east 2,000 against west 1,000) W chooses nothing; once the
    Fimir shows too (west 2,150) W chooses the west and the reserve heads there. Wrong versions:
    a trigger on fewer than six units (it chooses the east and keeps it, as 2,150 is under
    1.3 x 2,000) or on more."""
    first, later = battle(A)[:2]
    policy = lines.LinesWitness()
    policy.decide(deepcopy(first))
    sides, reserve = [], []
    for index, relief in enumerate(({"e5", "e9", "e10", "e11", "e12"},
                                    {"e5", "e8", "e9", "e10", "e11", "e12"})):
        frame = deepcopy(later)
        frame.update(seq=2 + index, time_ms=3000 + 2000 * index)
        frame["enemy"] = [u for u in frame["enemy"]
                          if u["id"] in relief | {"e1", "e2", "e3", "e4"}]
        orders = policy.decide(frame)
        sides.append(policy.metadata()["side"])
        reserve.append([order for order in orders if order["unit"] == "f5"])
    assert sides == [None, "west"]
    assert reserve[0] == [] and at(POSTS["west"], reserve[1][0])


def test_a_tie_chooses_no_side_and_the_cue_counts_every_enemy_ahead():
    """Six relief units ahead, in pairs of one type on each side (1,400 by cost and 248 men a
    side), choose no side for W or M. Six enemies ahead, two of them first seen 35 m ahead and
    so not relief units, are enough for W to choose the west's two Champions (2,000) over the
    east's two Spearmen (850). Wrong versions: a tie that picks a side; a cue that counts only
    relief units."""
    first, later = battle(A)[:2]
    tie = deepcopy(later)
    kinds = {unit["id"]: unit["type"] for unit in tie["enemy"]}
    for west, east in (("e5", "e9"), ("e6", "e10"), ("e7", "e11")):
        kind = kinds[east]
        next(u for u in tie["enemy"] if u["id"] == west).update(type=kind, men=MEN[kind],
                                                                men0=MEN[kind])
    tie["enemy"] = [unit for unit in tie["enemy"] if unit["id"] not in ("e8", "e12")]
    for arm in (lines.LinesWitness, lines.LinesByMen):
        policy = arm()
        for observation in (first, tie):
            policy.decide(deepcopy(observation))
        assert policy.metadata()["side"] is None, arm
    near, ahead = deepcopy(first), deepcopy(later)
    near["enemy"] += [dict(unit, z=-330) for unit in later["enemy"] if unit["id"] in ("e7", "e8")]
    ahead["enemy"] = [dict(unit, z=-400) if unit["id"] in ("e7", "e8") else unit
                      for unit in ahead["enemy"] if unit["id"] not in ("e11", "e12")]
    policy = lines.LinesWitness()
    for observation in (near, ahead):
        policy.decide(deepcopy(observation))
    assert policy.metadata()["side"] == "west"


def test_lancers_wait_for_two_engaged_relief_units_then_ride_round_the_end_and_charge():
    """With the west chosen, the Lancers hold while one west relief unit and two town-side units
    west of the split are in melee (rests on JUDGEMENT? lines.py Relief membership). Once two
    relief units are, they ride to the outside waypoint, then to 70 m behind the one nearer the
    sector centre (e6, listed after e5) along the outer line's front, charge it, and pull out
    120 m from the nearest enemy after 8 s of melee. They ride again after 10 s once no enemy is
    within 80 m, else after 20 s. Wrong versions: Lancers that ride at the side choice or count
    town-side melee; a target by list order; a rear point beside the target or in front of it;
    a charge or a withdrawal that never ends; a withdrawal that ignores the enemies near it; an
    8 s clock that starts at the charge, so a charge with no rider in melee for 8 s ends."""
    start = battle(A)[:2]
    spots = {"e5": (5, -298), "e6": (55, -298)}  # 30 m and 20 m from the sector centre (35, -295)

    def frame(seconds, engaged, riders=None, melee=False):
        observation = deepcopy(start[1])
        observation.update(seq=seconds, time_ms=1000 * seconds)
        for unit in observation["enemy"]:
            if unit["id"] in engaged:
                unit.update(**dict(zip("xz", spots.get(unit["id"], (unit["x"], unit["z"])))),
                            state=["melee"])
        for unit in observation["friendly"]:
            if unit["id"] in ("f6", "f7") and riders:
                unit.update(x=riders[0], z=riders[1], state=["melee"] if melee else [])
        return observation

    def step(policy, observation):
        given = [o for o in policy.decide(observation) if o["unit"] in ("f6", "f7")]
        return policy.metadata()["lancers"]["phase"], given

    policy = lines.LinesWitness()
    for observation in start:
        policy.decide(deepcopy(observation))
    both = ("e5", "e6")
    steps = [step(policy, frame(5, ("e1", "e2", "e5"))), step(policy, frame(7, both)),
             step(policy, frame(9, both, (-95, -300)))]
    rear = steps[2][1][0]
    steps.append(step(policy, frame(11, both, (rear["x"], rear["z"]))))
    idle = deepcopy(policy)  # charging from 11 s with no rider in melee
    steps += [step(policy, frame(13, both, (55, -303), True)),
              step(policy, frame(21, both, (55, -303), True))]
    assert [phase for phase, _ in steps] == ["wait", "side", "rear", "charge", "charge",
                                              "withdraw"]
    assert steps[0][1] == [] and steps[4][1] == []
    assert len(steps[1][1]) == 2 and all(at(WAYPOINTS["west"], o) for o in steps[1][1])
    assert len(steps[2][1]) == 2 and all(at({"x": 55, "z": -368}, o) for o in steps[2][1])
    assert [(o["type"], o["target"]) for o in steps[3][1]] == [("attack", "e6")] * 2
    retreat = steps[5][1][0]
    assert retreat["type"] == "move" and at({"x": 55, "z": -418}, retreat)
    assert step(idle, frame(19, both, (55, -340)))[0] == "charge"
    clear, near = deepcopy(policy), policy  # riders 159 m from any enemy, or at the retreat point
    assert step(clear, frame(29, both, (-120, -200)))[0] == "withdraw"
    phase, given = step(clear, frame(31, both, (-120, -200)))
    assert phase == "side" and len(given) == 2 and all(at(WAYPOINTS["west"], o) for o in given)
    assert step(near, frame(31, both, (55, -418)))[0] == "withdraw"
    assert step(near, frame(41, both, (55, -418)))[0] == "side"


def test_the_side_switches_only_once_the_other_side_leads_by_30_percent():
    """W chose the west (3,900 against 2,000). With both west Champions routing the west scores
    1,900 and W stays; once the Berserkers rout too it scores 1,150, the east leads by more than
    30% and the reserve heads for the east post. Wrong versions: a switch on any lead; a side
    that never switches; routing units still counted."""
    start = battle(A)[:2]
    policy = lines.LinesWitness()
    for observation in start:
        policy.decide(deepcopy(observation))
    sides, reserve = [], []
    for index, gone in enumerate(({"e5", "e6"}, {"e5", "e6", "e7"})):
        frame = deepcopy(start[1])
        frame.update(seq=3 + index, time_ms=5000 + 2000 * index)
        for unit in frame["enemy"]:
            if unit["id"] in gone:
                unit["state"] = ["routing"]
        orders = policy.decide(frame)
        sides.append(policy.metadata()["side"])
        reserve.append([order for order in orders if order["unit"] == "f5"])
    assert sides == ["west", "east"]
    assert reserve[0] == [] and at(POSTS["east"], reserve[1][0])


def test_the_arms_without_the_counterstroke_differ_only_in_the_reserve():
    """Owner question 4 (b) and (c): N and NM keep the Lancers on their start leash, so they
    differ only in the Boyar's and the Tzar Guard's orders, and N differs from W, and NM from M,
    only in the Lancers' orders (so each keeps its arm's side). The built W and M fail the
    reserve-only check, since their Lancers follow the chosen side. With the Lancers 30 m off
    their posts, N gives them C's orders back to the posts. Wrong versions: N or NM Lancers that
    follow the side; NM's rule flag unwired; an N whose reserve leaves W's; N's Lancers given no
    orders."""
    observations = battle(A)
    assert assert_ablation(lines.LinesNoCounterstroke, lines.LinesNoCounterstrokeByMen,
                           observations, units=RESERVE)
    with pytest.raises(AssertionError, match="outside units"):
        assert_ablation(lines.LinesWitness, lines.LinesByMen, observations, units=RESERVE)
    for arm, without in ((lines.LinesWitness, lines.LinesNoCounterstroke),
                         (lines.LinesByMen, lines.LinesNoCounterstrokeByMen)):
        assert assert_ablation(arm, without, observations, units=LANCERS)
    pushed = deepcopy(observations)
    for observation in pushed[1:]:
        for unit in observation["friendly"]:
            if unit["id"] in LANCERS:
                unit["z"] += 30
    assert first_move(run(lines.LinesCentral, pushed)[1], "f6")
    assert assert_ablation(lines.LinesCentral, lines.LinesNoCounterstroke, pushed, units=RESERVE)


def test_the_corner_camp_takes_cornerholds_post_and_spreads_the_army():
    """Owner question 4's corner-camp control takes the post CornerHold takes on the same
    observations, both with the relief out of sight at the first decision and with all 12
    enemies in sight, as check 5 expects (the post nearer the army than the enemy is then the
    other corner). It sends all 12 units to spots no two of which lie within 20 m; play's order
    checks accept every batch. Wrong versions: CornerHold's own spots (every unit on one of two
    points 32 m apart); ranks behind the post, which the 30 m map margin squeezes together; a
    post chosen without the visible enemy."""
    for observations, post in ((battle(A), {"x": 482, "z": -482}),
                               (battle(A)[1:], {"x": 482, "z": 482})):
        policy, decisions = run(lines.LinesCornerCamp, observations)
        corner = run(calibration.CornerHold, observations)[0].metadata()["corner"]
        assert policy.metadata()["corner"] == corner == post
        moves = [order for order in decisions[0] if order["type"] == "move"]
        assert sorted(order["unit"] for order in moves) == sorted(f"f{i}" for i in range(1, 13))
        assert min(math.dist((a["x"], a["z"]), (b["x"], b["z"]))
                   for a, b in itertools.combinations(moves, 2)) >= 20
