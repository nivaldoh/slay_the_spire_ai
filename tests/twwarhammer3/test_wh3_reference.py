"""The scripted reference: it gathers, then one target at a time, cavalry last."""
import pytest

from twwarhammer3.battle.reference import Concentrate


def unit(id, x, z=0, kind="infantry", state=(), men=90, **extra):
    return {"id": id, "x": x, "z": z, "class": kind, "state": list(state), "men": men, **extra}


def view(friendly, enemy):
    return {"friendly": friendly, "enemy": enemy, "time_ms": 1000}


def test_two_groups_far_from_any_enemy_run_to_their_shared_centre():
    orders = Concentrate().decide(view([unit("a", -200), unit("b", 200)], [unit("e", 0, 500)]))
    assert [(o["unit"], o["type"], o["x"], o["run"]) for o in orders] == [
        ("a", "move", 0, True), ("b", "move", 0, True)]


def test_an_enemy_close_to_a_unit_ends_the_gathering():
    orders = Concentrate().decide(view([unit("a", -200), unit("b", 200)], [unit("e", 190, 20)]))
    assert {o["type"] for o in orders} == {"attack"} and {o["target"] for o in orders} == {"e"}


def test_every_unit_takes_the_one_target_and_keeps_it_while_it_stands():
    policy = Concentrate()
    near, far = unit("near", 0, 40), unit("far", 0, 90)
    first = policy.decide(view([unit("a", 0), unit("b", 30)], [near, far]))
    assert {o["target"] for o in first} == {"near"}
    moved = [unit("a", 0, 10, target="near"), unit("b", 30, 10, target="near")]
    closer = {**far, "z": 12}
    assert policy.decide(view(moved, [near, closer])) == []  # same target, nothing to resend
    near["state"] = ["routing"]
    assert {o["target"] for o in policy.decide(view(moved, [near, closer]))} == {"far"}


def test_cavalry_waits_for_contact_and_shooters_fire():
    policy = Concentrate()
    army = [unit("a", 0), unit("k", 10, kind="cavalry"), unit("g", 20, kind="missile", ammo=20)]
    orders = {o["unit"]: o for o in policy.decide(view(army, [unit("e", 0, 60)]))}
    assert set(orders) == {"a", "g"} and orders["g"]["mode"] == "ranged"
    army[0]["state"] = ["melee"]
    assert "k" in {o["unit"] for o in policy.decide(view(army, [unit("e", 0, 60)]))}


@pytest.mark.parametrize("state", [["routing"], ["shattered"]])
def test_a_broken_unit_is_never_ordered(state):
    army = [unit("a", 0), unit("b", 10, state=state)]
    assert {o["unit"] for o in Concentrate().decide(view(army, [unit("e", 0, 60)]))} == {"a"}


def test_a_refused_order_is_sent_again():
    policy = Concentrate()
    army = [unit("a", 0, target="e")]
    assert policy.decide(view(army, [unit("e", 0, 60)]))
    assert policy.decide(view(army, [unit("e", 0, 60)])) == []
    policy.acknowledge({"results": [{"ok": False, "unit": "a"}]}, {})
    assert policy.decide(view(army, [unit("e", 0, 60)]))
