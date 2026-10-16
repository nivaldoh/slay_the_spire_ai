"""Only the diagnostics' commitments; game execution still needs the live checks."""

from copy import deepcopy

from twwarhammer3.battle.calibration import CentralDefence, CoordinatedRush
from twwarhammer3.protocol import validate_orders


def unit(uid, kind, x, z, speed=5, **extra):
    return {"id": uid, "type": kind, "x": x, "z": z, "men": 30, "men0": 30,
            "speed": [2, speed], "class": "infantry", "state": [], **extra}


def test_central_defence_uses_an_owned_point_and_keeps_its_initial_commitment():
    obs = {"time_ms": 1000, "friendly": [
        unit("f1", "lord", 0, 0, commander=True), unit("f2", "screen", 0, 10),
        unit("f3", "gun", 0, -10, ammo=20, **{"class": "missile"})],
        "enemy": [unit("e1", "enemy", 0, 400)],
        "mode": {"capture_points": [
            {"id": "c1", "x": 0, "z": 100, "victory": True, "holder": "us"},
            {"id": "c2", "x": 0, "z": 0, "victory": True, "holder": "enemy"}]}}
    original = deepcopy(obs)
    policy = CentralDefence()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert obs == original and policy.point["id"] == "c1"
    assert policy.assignments["f2"]["z"] > policy.assignments["f3"]["z"]
    assert policy.assignments["f1"]["z"] < policy.assignments["f3"]["z"]
    obs["mode"]["capture_points"][0]["holder"] = "enemy"
    policy.decide(obs)
    assert policy.point["id"] == "c1"


def test_mobile_units_follow_actual_screen_progress_then_release_on_contact():
    obs = {"time_ms": 1000, "friendly": [
        unit("f1", "skavenslaves_0", 0, 0, speed=5),
        unit("f2", "doomwheel", 10, 0, speed=10),
        unit("f3", "rat_ogres", -10, 0, speed=8)],
        "enemy": [unit("e1", "defender", 0, 500)]}
    policy = CoordinatedRush()
    first = policy.decide(obs)
    validate_orders(first, obs)
    following = [o for o in first if o["type"] == "move"]
    assert {o["unit"] for o in following} == {"f2", "f3"}
    assert all(o["z"] == -25 and o["run"] for o in following)
    assert [o["unit"] for o in first if o["type"] == "attack"] == ["f1"]
    assert not any(o["type"] == "move" for o in policy.decide(obs))
    obs["friendly"][0].update(z=300)
    # The old speed estimate released here, but actual contact can still be far away.
    following = [o for o in policy.decide(obs) if o["unit"] in {"f2", "f3"}]
    assert all(o["type"] == "move" and o["z"] == 275 for o in following)
    assert policy.metadata()["released_s"] == {}
    obs["friendly"][0].update(state=["melee"])
    obs["time_ms"] = 61000
    released = policy.decide(obs)
    assert {o["unit"] for o in released if o["type"] == "attack"} == {"f1", "f2", "f3"}
    assert policy.metadata()["released_s"] == {"f2": 61, "f3": 61}
    obs["friendly"][0].update(state=["routing"])
    assert not any(o["type"] == "halt" for o in policy.decide(obs))


def test_no_visible_target_does_not_release_mobile_units_using_roster_or_hidden_state():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "clanrats", 0, 0),
           unit("f2", "doomwheel", 0, 0, speed=10)], "enemy": [],
           "enemy_roster": [unit("e1", "enemy", 0, 10)],
           "evaluation": {"enemy": [unit("e1", "enemy", 0, 10)]}}
    policy = CoordinatedRush()
    assert policy.decide(obs) == [{"unit": "f2", "type": "halt"}]
    assert policy.metadata()["released_s"] == {}
