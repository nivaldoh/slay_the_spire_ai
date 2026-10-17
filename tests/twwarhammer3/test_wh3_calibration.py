"""Only the diagnostics' commitments; game execution still needs the live checks."""

import math
from copy import deepcopy

from twwarhammer3.battle.calibration import (
    Bodyguard,
    CasterSkirmish,
    CentralDefence,
    CoordinatedRush,
    Crossfire,
    CrossKite,
    FeintFlank,
    HammerAnvil,
    SpellWindow,
)
from twwarhammer3.protocol import validate_orders


def unit(uid, kind, x, z, speed=5, **extra):
    return {"id": uid, "type": kind, "x": x, "z": z, "men": 30, "men0": 30,
            "speed": [2, speed], "class": "infantry", "state": [], **extra}


def test_feint_flank_waits_for_rear_position_then_withdraws_after_contact():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "horse", 0, 100),
            unit("f2", "horse", 10, 100)], "enemy": [unit("e1", "halberds", 0, 0)]}
    policy = FeintFlank()
    first = policy.decide(obs)
    validate_orders(first, obs)
    assert all(order["type"] == "move" for order in first)
    flank = next(order for order in first if order["unit"] == "f2")
    obs["friendly"][1].update(x=flank["x"], z=flank["z"])
    rear = next(order for order in policy.decide(obs) if order["unit"] == "f2")
    assert rear["z"] < 0
    obs["friendly"][1].update(x=rear["x"], z=rear["z"])
    charge = policy.decide(obs)
    validate_orders(charge, obs)
    assert len(charge) == 2 and all(order["type"] == "attack" for order in charge)
    obs["friendly"][1].update(x=0, z=-5, state=["melee"])
    obs["time_ms"] = 11000
    policy.decide(obs)
    obs["time_ms"] = 18000
    retreat = policy.decide(obs)
    validate_orders(retreat, obs)
    assert policy.phase == "withdraw" and all(order["type"] == "move" for order in retreat)


def test_small_diagnostics_do_not_use_hidden_enemies_or_order_routers():
    for cls in (FeintFlank, CrossKite, Bodyguard, Crossfire, SpellWindow, HammerAnvil):
        obs = {"time_ms": 1000, "friendly": [unit("f1", "horse", 0, 0)],
               "enemy": [], "evaluation": {"enemy": [unit("e1", "hidden", 5, 5)]},
               "enemy_roster": [unit("e1", "hidden", 5, 5)]}
        policy = cls()
        assert policy.decide(obs) == []
        obs["enemy"] = obs["enemy_roster"]
        obs["friendly"][0]["state"] = ["routing"]
        assert policy.decide(obs) == []


def test_kiting_uses_melee_when_ammunition_is_gone_and_retries_refusals():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "horse_archer", 0, 40, ammo=10,
           behaviours={"skirmish": False, "fire_at_will": True})],
           "enemy": [unit("e1", "slayers", 0, 0)]}
    policy = CrossKite()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert orders[-1]["type"] == "move" and orders[-1]["z"] > 100
    assert not any(o["type"] == "move" for o in policy.decide(obs))
    policy.acknowledge({"results": [{"unit": "f1", "ok": False}]}, {})
    assert policy.decide(obs)[-1]["type"] == "move"
    obs["friendly"][0]["ammo"] = 0
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert orders[-1]["mode"] == "melee"


def test_bodyguard_prioritises_cavalry_over_closer_infantry():
    obs = {"time_ms": 1000, "friendly": [
           unit("f1", "helblaster", 0, 0, ammo=100, range=290, **{"class": "artillery"}),
           unit("f2", "halberds", 0, 20)], "enemy": [
           unit("e1", "infantry", 0, 20),
           unit("e2", "yeomen", 40, 0, **{"class": "cavalry"})]}
    original = deepcopy(obs)
    orders = Bodyguard().decide(obs)
    validate_orders(orders, obs)
    assert len(orders) == 2 and all(order["target"] == "e2" for order in orders)
    assert obs == original


def test_bodyguard_keeps_the_gun_home_and_stops_chasing_a_departing_target():
    obs = {"time_ms": 1000, "friendly": [
           unit("f1", "helblaster", 0, 0, ammo=100, range=290, **{"class": "artillery"}),
           unit("f2", "halberds", 0, 20)],
           "enemy": [unit("e1", "yeomen", 0, 500, **{"class": "cavalry"})]}
    policy = Bodyguard()
    assert all(order["unit"] != "f1" for order in policy.decide(obs))
    obs["enemy"][0]["z"] = 200
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert next(order for order in orders if order["unit"] == "f1")["type"] == "attack"
    obs["enemy"][0]["z"] = 400
    assert next(order for order in policy.decide(obs) if order["unit"] == "f1") == {
        "unit": "f1", "type": "halt"}


def test_bodyguard_keeps_its_target_between_two_equidistant_riders():
    obs = {"time_ms": 1000, "friendly": [
           unit("f1", "helblaster", 0, 0, ammo=100, range=290, **{"class": "artillery"}),
           unit("f2", "halberds", 0, 20)], "enemy": [
           unit("e1", "yeomen", 0, 250, **{"class": "cavalry"}),
           unit("e2", "yeomen", 10, 251, **{"class": "cavalry"})]}
    policy = Bodyguard()
    first = next(order for order in policy.decide(obs) if order["unit"] == "f1")["target"]
    other = "e2" if first == "e1" else "e1"
    # Live S4 (bench-b17-s4-bodyguard) flipped the gun between e2 and e3 five times in 2 s.
    for step in range(6):
        obs["time_ms"] += 300
        rider = next(enemy for enemy in obs["enemy"] if enemy["id"] == other)
        rider["z"] -= 2
        assert all(order.get("target", first) == first for order in policy.decide(obs))
    rider["z"] = 150
    obs["time_ms"] += 300
    assert next(order for order in policy.decide(obs) if order["unit"] == "f1")["target"] == other


def test_routing_refusal_is_newer_than_a_delayed_snapshot():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "horse", 0, 100)],
           "enemy": [unit("e1", "halberds", 0, 0)]}
    policy = FeintFlank()
    assert policy.decide(obs)
    policy.acknowledge({"applied_ms": 6000, "results": [
        {"unit": "f1", "ok": False, "error": "unit_routing"}]}, {})
    # The live delayed run repeatedly retried a known router from five-second-old state.
    obs["time_ms"] = 5000
    assert policy.decide(obs) == []
    obs["time_ms"] = 7000
    obs["friendly"][0]["state"] = ["routing"]
    assert policy.decide(obs) == []
    obs["friendly"][0]["state"] = []  # rallied: later public evidence permits orders again
    assert policy.decide(obs)


def test_flanking_waits_for_a_rally_instead_of_charging_alone():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "horse", 0, 50),
           unit("f2", "horse", 50, 50, state=["routing"])],
           "enemy": [unit("e1", "halberds", 0, 0)]}
    policy = FeintFlank()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert orders[0]["type"] == "move" and orders[0]["z"] > 100
    assert policy.phase == "rally"
    obs["friendly"][1]["state"] = []
    policy.decide(obs)
    assert policy.phase == "side"


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


def caster_state():
    return {"time_ms": 1000, "magic": {"current": 20}, "friendly": [
        unit("f1", "kairos_fateweaver", 0, 0, flying=True, can_fly=True,
             barrier={"hp": 900, "max_hp": 900}, flight={"can_toggle": True},
             abilities=[{"key": CasterSkirmish.BLUE_FIRE, "target": "Enemy", "mana": 6,
                         "cast_range": 175, "ready": True, "can_use": True},
                        {"key": CasterSkirmish.FIRESTORM, "target": "Ground", "mana": 15,
                         "cast_range": 150, "ready": True, "can_use": True}]),
        unit("f2", "chosen", 0, -50)],
        "enemy": [unit("e1", "catapult", 0, 500, **{"class": "artillery"})]}


def test_caster_approaches_casts_once_then_returns_and_recovers():
    obs, policy = caster_state(), CasterSkirmish()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert orders == [{"unit": "f1", "type": "move", "run": True, "x": 0, "z": 360}]
    assert policy.assignments["f2"]["z"] == -50
    obs["friendly"][0].update(z=350)  # stop short of the goal, still safely in cast range
    obs["time_ms"] = 2000
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert orders[-1] == {"unit": "f1", "type": "ability",
                           "ability": policy.BLUE_FIRE, "target": "e1"}
    obs["time_ms"] = 3000
    assert policy.decide(obs) == []  # stale ready flag does not cause an immediate recast
    obs["time_ms"] = 8000
    obs["friendly"][0]["abilities"][0]["ready"] = False
    assert policy.decide(obs)[-1]["z"] == 0
    obs["friendly"][0]["barrier"]["hp"] = 100
    obs["friendly"][0]["abilities"][0]["ready"] = True
    policy.decide(obs)
    assert policy.metadata()["recovering"]
    obs["time_ms"] = 12000
    obs["friendly"][0]["barrier"]["hp"] = 800
    assert policy.decide(obs)[-1]["type"] == "ability"


def test_caster_uses_visible_clusters_and_waits_for_takeoff():
    obs, policy = caster_state(), CasterSkirmish()
    obs["friendly"][0].update(z=400, flying=False)
    assert policy.decide(obs) == [{"unit": "f1", "type": "flight", "flying": True}]
    obs["friendly"][0]["flying"] = True
    obs["enemy"] += [unit("e2", "screen", 10, 500), unit("e3", "screen", -10, 500)]
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert orders[-1] == {"unit": "f1", "type": "ability",
                           "ability": policy.FIRESTORM, "x": 0, "z": 500}


def by_unit(orders, uid):
    return [order for order in orders if order["unit"] == uid]


def test_crossfire_waits_behind_the_pin_then_flanks_and_shoots_only_its_target():
    gun = {"class": "missile", "ammo": 20, "behaviours": {"fire_at_will": True}}
    obs = {"time_ms": 1000, "friendly": [unit("f1", "spearmen", 0, 0),
           unit("f2", "handgunners", -20, -10, **gun), unit("f3", "handgunners", 20, -10, **gun)],
           "enemy": [unit("e1", "warriors", 0, 150, bearing=180),
                     unit("e2", "warriors", 150, 200, bearing=180)]}
    original = deepcopy(obs)
    policy = Crossfire()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert obs == original
    assert by_unit(orders, "f1")[0]["target"] == "e1"
    for uid in ("f2", "f3"):
        hold_fire, move = by_unit(orders, uid)
        assert hold_fire["behaviour"] == "fire_at_will" and hold_fire["enabled"] is False
        assert move["type"] == "move" and move["z"] < 0  # behind the spearmen, no shots
    obs["enemy"][0].update(z=10, state=["melee"])
    obs["friendly"][0]["state"] = ["melee"]
    for gun_unit in obs["friendly"][1:]:
        gun_unit["behaviours"] = {"fire_at_will": False}
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    posts = {uid: by_unit(orders, uid)[0] for uid in ("f2", "f3")}
    assert round(posts["f2"]["x"], 1) == 98.5 and round(posts["f3"]["x"], 1) == -98.5
    assert all(round(math.dist((p["x"], p["z"]), (0, 10))) == 100 for p in posts.values())
    for uid, post in posts.items():
        obs["friendly"][int(uid[1]) - 1].update(x=post["x"], z=post["z"])
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert [(o["unit"], o["target"], o["mode"]) for o in orders if o["unit"] != "f1"] == [
        ("f2", "e1", "ranged"), ("f3", "e1", "ranged")]
    obs["enemy"][1].update(x=posts["f2"]["x"], z=30)  # a second unit closes on one gun
    obs["friendly"][2]["ammo"] = 0
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    evade = by_unit(orders, "f2")[0]
    assert evade["type"] == "move" and round(math.dist(
        (evade["x"], evade["z"]), (posts["f2"]["x"], 30))) == 120
    assert by_unit(orders, "f3")[0]["mode"] == "melee"


def spell(key, mana, kinds, cast_range=200):
    return {"key": key, "mana": mana, "target": kinds, "cast_range": cast_range,
            "ready": True, "can_use": True}


def wizard_state(magic=12):
    abilities = [spell("wh_main_spell_fire_the_burning_head", 10, "Ground"),
                 spell("wh_main_spell_fire_flame_storm", 13, "Ground"),
                 spell("wh_main_spell_fire_fireball_upgraded", 8, "Enemy", 300),
                 spell("wh_main_spell_fire_fireball", 5, "Enemy", 300)]
    return {"time_ms": 1000, "magic": {"current": magic, "reserve": 68},
            "friendly": [unit("f1", "wizard", 0, -60, abilities=abilities,
                              **{"class": "hero"}), unit("f2", "spearmen", 0, 0)],
            "enemy": [unit("e1", "swordsmen", 0, 100), unit("e2", "swordsmen", 30, 110)]}


def test_spell_window_aims_burning_head_along_a_clear_pair_and_spaces_casts():
    obs, policy = wizard_state(), SpellWindow()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert by_unit(orders, "f2")[0]["target"] == "e1"
    (cast,) = by_unit(orders, "f1")
    assert cast["ability"] == "wh_main_spell_fire_the_burning_head" and "target" not in cast
    assert round(math.dist((cast["x"], cast["z"]), (0, 100))) == 15
    toward = math.degrees(math.atan2(30 - cast["x"], 110 - cast["z"])) % 360
    assert abs(cast["facing"] - toward) < 1e-6
    obs["time_ms"] = 3000
    assert not any(o["type"] == "ability" for o in policy.decide(obs))
    obs.update(time_ms=7000, magic={"current": 6})  # only the cheaper Fireball is affordable
    (cast,) = by_unit(policy.decide(obs), "f1")
    assert cast == {"unit": "f1", "type": "ability", "ability": "wh_main_spell_fire_fireball",
                    "target": "e1"}


def test_spell_window_keeps_area_spells_off_its_own_melee():
    obs, policy = wizard_state(magic=20), SpellWindow()
    obs["enemy"][0].update(z=20, state=["melee"])
    obs["friendly"][1]["state"] = ["melee"]
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    (cast,) = by_unit(orders, "f1")  # no pair is clear of the spearmen: storm the free unit
    assert cast == {"unit": "f1", "type": "ability",
                    "ability": "wh_main_spell_fire_flame_storm", "x": 30, "z": 110}
    obs["friendly"][0]["abilities"][1]["ready"] = False
    obs["enemy"][1].update(x=20, z=30)  # now beside the spearmen: missiles only
    obs["time_ms"] = 7000
    (cast,) = by_unit(policy.decide(obs), "f1")
    assert cast["ability"] == "wh_main_spell_fire_fireball" and cast["target"] == "e2"
    obs.update(time_ms=13000, magic={"current": 0})
    obs["enemy"][1].update(x=0, z=-30)  # an enemy reached the wizard: step away
    move = by_unit(policy.decide(obs), "f1")[0]
    assert move["type"] == "move" and move["z"] < -60


def test_hammer_anvil_waits_for_the_pin_rides_to_the_rear_charges_and_pulls_out():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "swordsmen", 0, 0),
           unit("f2", "knights", 40, -20, **{"class": "cavalry"})],
           "enemy": [unit("e1", "swordsmen", 0, 100), unit("e2", "swordsmen", -80, 120),
                     unit("e3", "swordsmen", 80, 140)]}
    policy = HammerAnvil()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert by_unit(orders, "f1")[0]["target"] == "e1"
    post = by_unit(orders, "f2")[0]
    assert (round(post["x"]), round(post["z"])) == (60, -40) and policy.phase == "wait"
    obs["enemy"][0].update(z=10, state=["melee"])
    obs["friendly"][0]["state"] = ["melee"]
    side = by_unit(policy.decide(obs), "f2")[0]
    assert (round(side["x"]), round(side["z"])) == (90, 10) and policy.phase == "side"
    obs["friendly"][1].update(x=90, z=10)
    rear = by_unit(policy.decide(obs), "f2")[0]
    assert (round(rear["x"]), round(rear["z"])) == (0, 80)
    obs["friendly"][1].update(x=0, z=80)
    charge = by_unit(policy.decide(obs), "f2")[0]
    assert charge["type"] == "attack" and charge["target"] == "e1" and policy.charges == 1
    obs["friendly"][1]["state"] = ["melee"]
    obs["time_ms"] = 3000
    policy.decide(obs)
    obs["time_ms"] = 11000
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert policy.phase == "withdraw" and by_unit(orders, "f2")[0]["type"] == "move"
    obs["friendly"][1].update(state=[], x=0, z=300)
    obs["time_ms"] = 22000
    policy.decide(obs)
    assert policy.phase == "side"  # the pin still holds: the next cycle starts at once


def test_hammer_anvil_pulls_out_when_its_charge_target_routs_and_moves_on():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "swordsmen", 0, 0, state=["melee"]),
           unit("f2", "knights", 0, 80, **{"class": "cavalry"})],
           "enemy": [unit("e1", "swordsmen", 0, 10, state=["melee"]),
                     unit("e2", "swordsmen", -80, 120)]}
    policy = HammerAnvil()
    policy.target, policy.phase = "e1", "charge"
    assert by_unit(policy.decide(obs), "f2")[0]["target"] == "e1"
    obs["enemy"][0]["state"] = ["routing"]
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert by_unit(orders, "f1")[0]["target"] == "e2"  # no chasing the router
    assert policy.phase == "withdraw" and by_unit(orders, "f2")[0]["type"] == "move"
