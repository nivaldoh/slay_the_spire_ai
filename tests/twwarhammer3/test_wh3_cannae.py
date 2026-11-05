"""The witness follows public cues; accepted movement alone cannot advance its route."""

from copy import deepcopy

import pytest

from twwarhammer3.battle.cannae import GREATSWORDS, KNIGHTS, SWORDS, Envelop
from twwarhammer3.protocol import PolicyFailure, validate_orders


def unit(identity, kind, x, z, **extra):
    return {"id": identity, "type": kind, "class": "cavalry" if kind == KNIGHTS else "infantry",
            "men": 90, "state": [], "x": x, "z": z, **extra}


def opening():
    return {"time_ms": 5000,
            "terrain": {"bounds": {"min_x": -512, "max_x": 512,
                                    "min_z": -512, "max_z": 512}},
            "friendly": [unit(f"s{i}", SWORDS, 70, z)
                         for i, z in enumerate((-175, -225, -275, -325))] + [
                unit("left", GREATSWORDS, 0, -125), unit("right", GREATSWORDS, 0, -375),
                unit("k1", KNIGHTS, -45, -85), unit("k2", KNIGHTS, -100, -85),
                unit("k3", KNIGHTS, -45, -425)],
            "enemy": [unit("north", KNIGHTS, 260, -95), unit("south", KNIGHTS, 260, -415)] + [
                unit(f"e{i}", SWORDS, 245, z) for i, z in enumerate((-175, -225, -275, -325))]}


def contact(view):
    view["time_ms"] += 40000
    view["friendly"][0]["state"] = ["melee"]
    for enemy in view["enemy"]:
        if enemy["type"] == SWORDS:
            enemy["x"] = 85
    return view


def test_opening_uses_two_to_one_wing_and_one_containing_horse_without_committing_reserves():
    view = opening()
    policy = Envelop()
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert {o["unit"]: o["target"] for o in orders} == {
        "k1": "north", "k2": "north", "k3": "south"}


def test_binding_and_complete_decisions_ignore_private_data_and_own_list_reordering():
    view, other = opening(), opening()
    other["friendly"].reverse()
    other.update(evaluation={"reserve": {"region": "outside"}}, setup={"winner": "enemy"},
                 final={"result": "lost"})
    first, second = Envelop(), Envelop()
    assert first.decide(view) == second.decide(other)
    for u in other["friendly"]:
        u["z"] *= -1  # stable identities, never rebind roles from later positions
    second.decide(other)
    assert first.groups == second.groups
    with pytest.raises(PolicyFailure, match="four Swordsmen"):
        Envelop().decide({**view, "friendly": view["friendly"][:-1]})


def test_contact_starts_both_outside_flanks_and_accepted_orders_do_not_prove_arrival():
    policy, view = Envelop(), opening()
    policy.decide(view)
    orders = policy.decide(contact(view))
    validate_orders(orders, view)
    moves = {o["unit"]: o for o in orders if o["type"] == "move"}
    assert set(moves) == {"left", "right"}
    assert moves["left"]["z"] > -175 and moves["right"]["z"] < -325
    policy.acknowledge({"results": [{"unit": i, "ok": True} for i in moves]}, {})
    for _ in range(10):
        view["time_ms"] += 1000
        policy.decide(view)
    assert all(policy.routes[i]["next"] == 0 and not policy.routes[i]["arrivals"]
               and policy.routes[i]["status"] == "pending" for i in moves)


def test_actual_waypoints_allow_inward_attack_only_after_all_points_arrived():
    policy, view = Envelop(), contact(opening())
    policy.decide(view)
    left = next(u for u in view["friendly"] if u["id"] == "left")
    points = deepcopy(policy.routes["left"]["points"])
    for index, point in enumerate(points):
        view["time_ms"] += 1000
        left.update(point)
        orders = policy.decide(view)
        validate_orders(orders, view)
        assert len(policy.routes["left"]["arrivals"]) == index + 1
        if index < len(points) - 1:
            assert not any(o["unit"] == "left" and o["type"] == "attack" for o in orders)
    assert policy.routes["left"]["status"] == "arrived"
    assert any(o["unit"] == "left" and o["type"] == "attack" for o in orders)


def test_routed_north_horse_redirects_to_other_wing_without_calling_it_dead():
    policy, view = Envelop(), opening()
    policy.decide(view)
    view["enemy"][0]["state"] = ["routing"]
    view["time_ms"] += 10000
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert policy.cavalry_stage == "other_wing"
    assert {o["unit"] for o in orders if o["type"] == "move"} == {"k1", "k2"}
    assert policy.routes["k1"]["points"][-1]["z"] == -415
    assert "dead" not in str(policy.metadata())


def test_unseen_opening_horse_is_not_assumed_already_defeated_and_route_failure_is_retained():
    policy, view = Envelop(), opening()
    view["enemy"] = [u for u in view["enemy"] if u["class"] == "infantry"]
    assert not {o["unit"] for o in policy.decide(view)} & {"k1", "k2"}
    assert policy.cavalry_stage == "own_wing"
    policy.decide(contact(view))
    policy.acknowledge({"results": [{"unit": "left", "ok": False, "error": "blocked"}]}, {})
    view["time_ms"] += 1000
    assert any(o["unit"] == "left" and o["type"] == "move" for o in policy.decide(view))
    view["time_ms"] += 180000
    policy.decide(view)
    assert policy.routes["left"]["status"] == "deadline"
    assert not policy.routes["left"]["arrivals"]


def test_duplicate_initial_rows_and_changed_bound_types_fail_before_orders():
    view = opening()
    view["friendly"].append(deepcopy(view["friendly"][0]))
    with pytest.raises(PolicyFailure, match="roster"):
        Envelop().decide(view)
    policy, view = Envelop(), opening()
    policy.decide(view)
    view["friendly"][6]["type"] = "artillery"
    with pytest.raises(PolicyFailure, match="identity"):
        policy.decide(view)


def test_seen_enemy_horse_keeps_its_wing_identity_when_it_crosses_the_centre():
    policy, view = Envelop(), opening()
    policy.decide(view)
    view["time_ms"] += 10000
    view["enemy"][0]["z"] = -430
    orders = policy.decide(view)
    assert policy.cavalry_stage == "own_wing"
    assert not any(o["type"] == "move" and o["unit"] in {"k1", "k2"} for o in orders)
    assert policy.targets["k1"] == policy.targets["k2"] == "north"


def test_first_visible_routed_horse_keeps_its_wing_label_after_rallying_across_centre():
    policy, view = Envelop(), opening()
    view["enemy"][0]["state"] = ["routing"]
    policy.decide(view)
    assert policy.enemy_wings["north"] == "north"
    view["enemy"][0].update(state=[], z=-430)
    view["time_ms"] += 10000
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert policy.enemy_wings["north"] == "north"


@pytest.mark.parametrize("current_x", (150, 400))
def test_cavalry_already_among_infantry_exits_outward_before_crossing_the_rear(current_x):
    # a-envelop-01/c4db660: accepted inward exit orders reached no waypoint before rout.
    # Proposed v2 route contract: exit beyond the visible infantry rear/current cavalry
    # position, rather than heading west back through the contested centre.
    policy, view = Envelop(), opening()
    policy.decide(view)
    view["time_ms"] = 165400
    for u in view["friendly"]:
        if u["id"] in {"k1", "k2"}:
            u.update(x=current_x, z=-205, state=["melee"])
    for u in view["enemy"]:
        if u["class"] == "cavalry":
            u["state"] = ["routing"]
        else:
            u["x"] = 120 if u["id"] in {"e0", "e2"} else 170
    orders = policy.decide(view)
    validate_orders(orders, view)
    for identity in ("k1", "k2"):
        first = policy.routes[identity]["points"][0]
        assert first["x"] > 170 and first["x"] > current_x
        assert first["z"] > -175


@pytest.mark.parametrize("edge", ("cavalry_x", "infantry_x", "infantry_z"))
def test_map_clipping_cannot_turn_a_failed_exit_into_a_backwards_or_inside_move(edge):
    policy, view = Envelop(), opening()
    policy.decide(view)
    view["time_ms"] = 165400
    for u in view["friendly"]:
        if u["id"] in {"k1", "k2"}:
            u.update(x=500 if edge == "cavalry_x" else 150, z=-205, state=["melee"])
    for u in view["enemy"]:
        if u["class"] == "cavalry":
            u["state"] = ["routing"]
        elif edge == "infantry_x":
            u["x"] = 500
        elif edge == "infantry_z":
            u["z"] = 500
    orders = policy.decide(view)
    validate_orders(orders, view)
    for identity in ("k1", "k2"):
        assert policy.routes[identity]["status"] == "no_exit"
        assert not policy.routes[identity]["arrivals"]
        assert not any(o["unit"] == identity and o["type"] == "move" for o in orders)
    # A rejected candidate route is neither completed nor an army-wide stop. On the next
    # input, the ordinary eligible-target fallback remains available to that regiment.
    view["time_ms"] += 1000
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert {o["unit"] for o in orders if o["type"] == "attack"} >= {"k1", "k2"}
