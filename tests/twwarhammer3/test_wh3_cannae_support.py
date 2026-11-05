"""The alternate B witness supports a visible horse fight without private event data."""

from copy import deepcopy

import pytest
from test_wh3_cannae import opening

from twwarhammer3.battle.cannae import CentreSupport, WingSupport
from twwarhammer3.protocol import PolicyFailure, validate_orders


def test_support_assigns_northern_greatswords_and_two_knights_to_the_same_horse():
    view, policy = opening(), WingSupport()
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert {o["unit"]: o["target"] for o in orders} == {
        "left": "north", "right": "e3", "k1": "north", "k2": "north", "k3": "south"}
    assert all(o["type"] == "attack" for o in orders)
    assert not policy.routes


def test_current_visibility_routing_crossing_and_rally_change_only_permitted_targets():
    view, policy = opening(), WingSupport()
    policy.decide(view)
    north = deepcopy(view["enemy"][0])
    view["enemy"][0]["state"] = ["routing"]
    view["time_ms"] += 10000
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert {o["unit"]: o["target"] for o in orders if o["unit"] in {"k1", "k2"}} == {
        "k1": "south", "k2": "south"}
    assert not any(o.get("target") == "north" for o in orders)
    view["enemy"] = [u for u in view["enemy"] if u["id"] != "north"]
    view["enemy_roster"] = [north]  # remembered roster is not a visible contact
    view["time_ms"] += 10000
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert not any(o.get("target") == "north" for o in orders)
    north["z"] = -450  # the same horse rallies across the original wing boundary
    view["enemy"].append(north)
    view["time_ms"] += 10000
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert policy.enemy_wings["north"] == "north"
    assert {o["unit"] for o in orders if o.get("target") == "north"} == {"left", "k1", "k2"}


@pytest.mark.parametrize("horse,expected", (("north", {"left", "k1", "k2"}),
                                          ("south", {"k1", "k2", "k3"})))
def test_a_role_without_a_permitted_target_does_not_attack_the_other_wing(horse, expected):
    view, policy = opening(), WingSupport()
    view["enemy"] = [u for u in view["enemy"] if u["id"] == horse]
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert {o["unit"] for o in orders} == expected


def test_a_target_lost_from_view_does_not_win_over_a_nearer_contact_when_it_reappears():
    view, policy = opening(), WingSupport()
    policy.decide(view)
    north = deepcopy(view["enemy"][0])
    view["enemy"] = []
    view["time_ms"] += 10000
    assert policy.decide(view) == []
    near = {**north, "id": "near_north", "x": 0}
    view["enemy"] = [north, near]
    view["time_ms"] += 10000
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert {o["unit"]: o["target"] for o in orders} == {
        "left": "near_north", "k1": "near_north", "k2": "near_north"}


def test_support_ignores_private_draws_and_retains_own_roles_after_reordering_and_crossing():
    view, other = opening(), opening()
    other["friendly"].reverse()
    other.update(evaluation={"reserve": {"count": 2, "side": "south"}},
                 setup={"winner": "enemy"}, final={"result": "lost"})
    first, second = WingSupport(), WingSupport()
    assert first.decide(view) == second.decide(other)
    for state in (view, other):
        for u in state["friendly"]:
            u["z"] *= -1
        state["time_ms"] += 10000
    assert first.decide(view) == second.decide(other)
    assert first.groups == second.groups
    assert first.groups["left"] == ["left"]


def test_centre_variant_changes_only_the_northern_knights_second_commitment():
    view, wing, centre = opening(), WingSupport(), CentreSupport()
    assert wing.decide(view) == centre.decide(view)
    view["enemy"][0]["state"] = ["routing"]
    view["time_ms"] += 10000
    old_orders, new_orders = wing.decide(view), centre.decide(view)
    validate_orders(old_orders, view)
    validate_orders(new_orders, view)
    assert {o["unit"]: o["target"] for o in old_orders if o["unit"] in {"k1", "k2"}} == {
        "k1": "south", "k2": "south"}
    assert {o["unit"]: o["target"] for o in new_orders if o["unit"] in {"k1", "k2"}} == {
        "k1": "e0", "k2": "e0"}
    assert [o for o in old_orders if o["unit"] not in {"k1", "k2"}] == [
        o for o in new_orders if o["unit"] not in {"k1", "k2"}]
    assert centre.metadata()["type"] == "cannae_centre_support"
    assert centre.metadata()["cavalry_priority"] == "infantry"


def test_centre_variant_keeps_the_other_horse_fallback_when_infantry_is_not_visible():
    view, policy = opening(), CentreSupport()
    view["enemy"] = [u for u in view["enemy"] if u["id"] == "south"]
    orders = policy.decide(view)
    validate_orders(orders, view)
    assert {o["unit"]: o["target"] for o in orders} == {
        "k1": "south", "k2": "south", "k3": "south"}
    assert policy.metadata()["cavalry_priority"] == "south"


@pytest.mark.parametrize("change", ("duplicate", "identity", "type", "missing"))
def test_support_refuses_changed_own_identity_before_updating_orders(change):
    view, policy = opening(), WingSupport()
    policy.decide(view)
    before = deepcopy(policy.sent)
    if change == "duplicate":
        view["friendly"].append(deepcopy(view["friendly"][0]))
    elif change == "identity":
        view["friendly"][0]["id"] = "foreign"
    elif change == "type":
        view["friendly"][0]["type"] = "artillery"
    else:
        view["friendly"].pop()
    with pytest.raises(PolicyFailure):
        policy.decide(view)
    assert policy.sent == before
