"""Only the diagnostics' commitments; game execution still needs the live checks."""

import math
from copy import deepcopy

from twwarhammer3.battle.calibration import (
    Bodyguard,
    BraceFacing,
    CasterSkirmish,
    CentralDefence,
    CoordinatedRush,
    CornerHold,
    CounterBattery,
    Crossfire,
    CrossKite,
    FeintFlank,
    FocusFire,
    HammerAnvil,
    MonsterTarget,
    SpellWindow,
)
from twwarhammer3.battle.scripted import distance
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
    for cls in (FeintFlank, CrossKite, Bodyguard, Crossfire, SpellWindow, HammerAnvil,
                CornerHold, FocusFire, MonsterTarget, BraceFacing, CounterBattery):
        obs = {"time_ms": 1000, "friendly": [unit("f1", "horse", 0, 0)],
               "enemy": [], "evaluation": {"enemy": [unit("e1", "hidden", 5, 5)]},
               "enemy_roster": [unit("e1", "hidden", 5, 5)]}
        policy = cls()
        assert policy.decide(obs) == []
        obs["enemy"] = obs["enemy_roster"]
        obs["friendly"][0]["state"] = ["routing"]
        assert policy.decide(obs) == []


def test_kiting_prefers_slayers_over_a_nearer_decoy():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "horse_archer", 0, 100, ammo=10),
                                         unit("f2", "horse_archer", 20, 100, ammo=10)],
           "enemy": [unit("e1", "dwarf_warrior", 0, 60), unit("e2", "slayers", 0, 0)]}
    original = deepcopy(obs)
    orders = CrossKite().decide(obs)
    validate_orders(orders, obs)
    # Posts flank the Slayers (z 0), not the nearer decoy (z 60).
    assert len(orders) == 2 and all(order["z"] < 50 for order in orders)
    assert obs == original


def test_kiting_posts_avoid_restricted_cells_and_refused_moves():
    # Live S2 decoy: one post sat inside the map's central rock and was refused 144 times.
    rows = ["." * 32 for _ in range(32)]
    obs = {"time_ms": 1000, "friendly": [unit("f1", "horse_archer", 0, 100, ammo=10),
                                         unit("f2", "horse_archer", 20, 100, ammo=10)],
           "enemy": [unit("e1", "slayers", 0, 0)],
           "terrain": {"rows": rows, "cell_m": 32, "x0": -496, "z0": -496,
                       "bounds": {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}}}
    policy = CrossKite()
    first = {order["unit"]: order for order in policy.decide(obs)}
    block = first["f2"]
    row, column = round((block["z"] + 496) / 32), round((block["x"] + 496) / 32)
    rows[row] = rows[row][:column] + "#" + rows[row][column + 1:]
    policy.sent.clear()
    moved = {order["unit"]: order for order in policy.decide(obs)}["f2"]
    assert distance(moved, block) > 20
    policy.acknowledge({"applied_ms": 2000, "results": [
        {"unit": "f1", "ok": False, "error": "unreachable"}]}, {})
    again = {order["unit"]: order for order in policy.decide(obs)}["f1"]
    assert distance(again, first["f1"]) > 20


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


def pinned_guns(reach):
    gun = {"class": "missile", "ammo": 20, "range": reach, "behaviours": {"fire_at_will": False}}
    return {"time_ms": 1000, "friendly": [unit("f1", "spearmen", 0, 0, state=["melee"]),
            unit("f2", "handgunners", -20, -60, **gun), unit("f3", "handgunners", 20, -60, **gun)],
            "enemy": [unit("e1", "warriors", 0, 10, bearing=180, state=["melee"])]}


def gun_orders(policy, obs):
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    return {order["unit"]: order for order in orders if order["unit"] != "f1"}


def test_crossfire_fixes_each_post_when_the_pin_starts():
    # Live S3 r3: posts recomputed from the target's live bearing moved with it.
    obs, policy = pinned_guns(reach=60), Crossfire()  # the target is 73 m away: go to posts
    first = gun_orders(policy, obs)
    assert round(first["f2"]["x"], 1) == 98.5 and round(first["f3"]["x"], 1) == -98.5
    obs["time_ms"] = 5000
    obs["enemy"][0].update(x=10, z=20, bearing=90)
    policy.sent.clear()
    spots = {uid: (order["x"], order["z"]) for uid, order in gun_orders(policy, obs).items()}
    assert spots == {uid: (order["x"], order["z"]) for uid, order in first.items()}
    assert policy.metadata()["pin"] == {"id": "e1", "x": 0, "z": 10, "bearing": 180}
    obs["enemy"][0]["state"] = []  # the pin breaks; the next one fixes new posts
    gun_orders(policy, obs)
    obs["enemy"][0]["state"] = ["melee"]
    again = gun_orders(policy, obs)
    assert policy.metadata()["pin"]["bearing"] == 90 and again["f2"]["z"] > 100


def test_crossfire_guns_shoot_a_target_in_range_from_where_they_stand():
    obs = pinned_guns(reach=145)
    orders = gun_orders(Crossfire(), obs)
    assert [(o["type"], o["mode"], o["target"]) for o in orders.values()] == [
        ("attack", "ranged", "e1")] * 2


def test_crossfire_guns_shoot_an_attacker_while_it_stays_in_range():
    # Live S3 r3: guns ran 120 m from hunters within 50 m without firing, then turned back.
    obs, policy = pinned_guns(reach=145), Crossfire()
    obs["enemy"].append(unit("e2", "warriors", -20, -100))  # 40 m from f2, 57 m from f3
    orders = gun_orders(policy, obs)
    assert (orders["f2"]["target"], orders["f2"]["mode"]) == ("e2", "ranged")
    assert orders["f3"]["target"] == "e1"
    obs["enemy"][1]["z"] = -160  # backs off to 100 m: still in range, still the target
    policy.sent.clear()
    assert gun_orders(policy, obs)["f2"]["target"] == "e2"
    obs["enemy"][1]["z"] = -300  # out of range: back to the pinned target
    assert gun_orders(policy, obs)["f2"]["target"] == "e1"
    assert policy.metadata()["attackers"] == {}


def test_crossfire_without_spearmen_shoots_the_nearest_in_range_or_halts():
    # Live S3 r3: with the line routed, guns kept chasing posts beside a pursuing target.
    obs, policy = pinned_guns(reach=145), Crossfire()
    obs["friendly"][0]["state"] = ["routing"]
    obs["enemy"][0].update(x=0, z=200, state=[])
    obs["enemy"].append(unit("e2", "warriors", -60, -110))  # 64 m from f2, 94 m from f3
    orders = gun_orders(policy, obs)
    assert [(o["unit"], o["type"], o["target"]) for o in orders.values()] == [
        ("f2", "attack", "e2"), ("f3", "attack", "e2")]
    obs["enemy"][1].update(x=-60, z=-400)
    obs["time_ms"] = 3000
    assert gun_orders(policy, obs) == {"f2": {"unit": "f2", "type": "halt"},
                                       "f3": {"unit": "f3", "type": "halt"}}
    obs["time_ms"] = 9000
    assert gun_orders(policy, obs) == {}


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


def answer(orders, applied_ms, ok=True):
    """An acknowledgement that accepts (or refuses) every order, applied at ``applied_ms``."""
    return {"applied_ms": applied_ms, "results": [
        {"index": index, "unit": order["unit"], "ok": ok, **({} if ok else {"error": "x"})}
        for index, order in enumerate(orders, 1)]}


def wizard_orders(policy, obs, applied_ms=None, ok=True):
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    if applied_ms is not None:
        policy.acknowledge(answer(orders, applied_ms, ok), {})
    return by_unit(orders, "f1")


def cast_from_post(policy, obs, applied_ms):
    """The wizard walks to its post, then casts Fireball at e1 at 2 s (only it is affordable)."""
    (post,) = wizard_orders(policy, obs, 1300)
    assert post["type"] == "move" and (post["x"], post["z"]) == (0, -100)
    obs.update(time_ms=2000, magic={"current": 6})
    obs["friendly"][0].update(z=-80, state=[])
    (cast,) = wizard_orders(policy, obs, applied_ms)
    assert cast == {"unit": "f1", "type": "ability", "ability": "wh_main_spell_fire_fireball",
                    "target": "e1"}
    return cast


def test_spell_window_sends_the_wizard_nothing_until_its_cast_lands():
    # Live S5 b23: the flee move right after each Fireball cancelled it (and refunded the
    # magic once it was taken); 4 of 177 Fireball orders completed in the fresh episode.
    obs, policy = wizard_state(magic=0), SpellWindow()
    cast_from_post(policy, obs, 2300)
    obs["enemy"][0].update(z=-35, state=["moving"], bearing=180)  # 45 m off, running at it
    obs["time_ms"] = 3500
    assert wizard_orders(policy, obs, 3800) == []  # b24 fled here
    # Magic taken: the rest cannot pay for another Fireball, so it reads not ready while it
    # is still being cast (live S5 b23: 6 such casts, 1.2-4.8 s before 5 of them landed).
    obs.update(time_ms=4700, magic={"current": 1})
    obs["friendly"][0]["abilities"][3]["ready"] = False
    assert wizard_orders(policy, obs, 5000) == []
    obs["friendly"][0]["abilities"][3]["recharge_s"] = 28.2  # on cooldown: it landed
    obs["time_ms"] = 5900
    (flee,) = wizard_orders(policy, obs, 6200)
    assert flee["type"] == "move" and flee["z"] < -80
    assert policy.metadata()["hold"] is None


def test_spell_window_keeps_its_post_move_through_a_cast():
    obs, policy = wizard_state(magic=0), SpellWindow()
    cast_from_post(policy, obs, 2300)
    obs["friendly"][0]["abilities"][3].update(ready=False, recharge_s=28.2)
    obs.update(time_ms=4100, magic={"current": 1})
    assert wizard_orders(policy, obs, 4400) == []  # landed; the post move is not re-sent
    obs["friendly"][0]["state"] = ["idle"]  # the cast is over and the wizard stands short
    obs["time_ms"] = 4700
    (post,) = wizard_orders(policy, obs, 5000)
    assert post["type"] == "move" and (post["x"], post["z"]) == (0, -100)


def test_spell_window_releases_a_cast_that_never_lands_after_six_seconds():
    obs, policy = wizard_state(magic=0), SpellWindow()
    cast = cast_from_post(policy, obs, 7300)  # a 5 s old view: it applied at 7.3 s
    assert policy.metadata()["hold"] == {"unit": "f1", "ability": cast["ability"],
                                         "time_s": 2, "applied_s": 7.3}
    obs["enemy"][0].update(z=-35)  # within 50 m: b24 fled at once
    for time_ms in (3500, 7300, 13200):  # the hold counts from when the order applied
        obs["time_ms"] = time_ms
        assert wizard_orders(policy, obs, time_ms + 5300) == []
    obs["time_ms"] = 13300  # 6 s on, the spell still ready: no cast happened; cast again
    assert wizard_orders(policy, obs, 18600, ok=False) == [cast]
    obs["time_ms"] = 14500  # that cast was refused: no hold, the wizard steps away
    (flee,) = wizard_orders(policy, obs)
    assert flee["type"] == "move" and flee["z"] < -80


def test_spell_window_flees_melee_contact_while_a_cast_is_pending():
    obs, policy = wizard_state(magic=0), SpellWindow()
    cast_from_post(policy, obs, 2300)
    obs["enemy"][0].update(z=-77, state=["melee"])
    obs["time_ms"] = 3000
    assert wizard_orders(policy, obs, 3300) == []  # no contact yet in the wizard's state
    obs["friendly"][0]["state"] = ["melee"]
    obs["time_ms"] = 3600
    (flee,) = wizard_orders(policy, obs, 3900)
    assert flee["type"] == "move" and round(flee["z"]) == -197
    assert policy.metadata()["hold"] is None


def test_spell_window_fireballs_an_enemy_charging_the_wizard_instead_of_a_flame_storm():
    # Live S5 b23: six Flame Storms on a Swordsmen unit chasing the wizard killed about 2 men.
    fireball = {"ability": "wh_main_spell_fire_fireball", "target": "e2"}
    storm = {"ability": "wh_main_spell_fire_flame_storm", "x": 30, "z": 110}
    for bearing, spell_order in ((190, fireball), (230, fireball), (100, storm)):
        obs, policy = wizard_state(magic=20), SpellWindow()
        obs["enemy"][0].update(z=20, state=["melee"])
        obs["friendly"][1]["state"] = ["melee"]
        obs["enemy"][1].update(state=["moving", "running"], bearing=bearing)  # 190: at f1
        orders = policy.decide(obs)
        validate_orders(orders, obs)
        assert by_unit(orders, "f1") == [{"unit": "f1", "type": "ability", **spell_order}]


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


REFUSED_EVERYWHERE = [{"x": x, "z": z} for x in range(-150, 151, 20)
                      for z in range(-140, 161, 20)]


def test_moves_step_off_restricted_cells_or_hold():
    # Live S6: HammerAnvil's wait post inside the central rock was refused 147 times.
    rows = ["." * 32 for _ in range(32)]
    rows[16] = "." * 16 + "#" + "." * 15  # the cell holding (16, 16)
    obs = {"time_ms": 1000, "friendly": [unit("f1", "knights", 200, 200)],
           "enemy": [unit("e1", "swordsmen", 0, 0)],
           "terrain": {"rows": rows, "cell_m": 32, "x0": -496, "z0": -496,
                       "bounds": {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}}}
    policy = CrossKite()
    policy.observe(obs)
    order = policy.move(obs["friendly"][0], {"x": 16, "z": 16}, obs["enemy"][0])[0]
    spot = (order["x"], order["z"])
    assert spot != (16, 16) and math.dist(spot, (16, 16)) <= 64
    policy.sent.clear()
    policy.unreachable = REFUSED_EVERYWHERE
    assert policy.move(obs["friendly"][0], {"x": 16, "z": 16}, obs["enemy"][0]) == []


def test_step_ring_stays_inside_the_map_and_off_map_points_are_blocked():
    # Live S3 r3 (b23): 13 of 14 refusals were ring points at x -514/-546, past min_x -512.
    bounds = {"min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}
    obs = {"time_ms": 1000, "friendly": [unit("f1", "handgunners", -400, -255)],
           "enemy": [unit("e1", "warriors", 0, 0)],
           "terrain": {"rows": [], "cell_m": 32, "x0": -496, "z0": -496, "bounds": bounds}}
    policy = Crossfire()
    policy.observe(obs)
    policy.unreachable = [{"x": -482, "z": -255}, {"x": -450, "z": -255}]
    (order,) = policy.move(obs["friendly"][0], {"x": -600, "z": -255}, obs["enemy"][0])
    assert (order["x"], order["z"]) == (-482, -223)  # b23: (-514, -255)
    # Every on-map spot within two cells of (-482, -255) is restricted: hold, not step off it.
    rows = ["." * 32 for _ in range(32)]
    rows[5:12] = ["###" + "." * 29] * 7
    obs["terrain"]["rows"] = rows
    policy = Crossfire()
    policy.observe(obs)
    assert policy.move(obs["friendly"][0], {"x": -600, "z": -255}, obs["enemy"][0]) == []
    # Posts are not clamped: one past the map's edge is blocked (b23: open), so the next is used.
    assert policy.open_point([{"x": -514, "z": 0}, {"x": -450, "z": 0}]) == {"x": -450, "z": 0}


def test_with_every_post_refused_guns_shoot_and_knights_charge_from_where_they_are():
    # Live S3 re-run: with all rotated posts refused, the old fallback retried one 434 times.
    gun = {"class": "missile", "ammo": 20, "behaviours": {"fire_at_will": False}}
    obs = {"time_ms": 1000, "friendly": [unit("f1", "spearmen", 0, 0, state=["melee"]),
           unit("f2", "handgunners", -20, -60, **gun)],
           "enemy": [unit("e1", "warriors", 0, 10, bearing=180, state=["melee"])]}
    policy = Crossfire()
    policy.unreachable = REFUSED_EVERYWHERE
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert [(o["type"], o.get("mode")) for o in by_unit(orders, "f2")] == [("attack", "ranged")]
    obs = {"time_ms": 1000, "friendly": [unit("f1", "swordsmen", 0, 0, state=["melee"]),
           unit("f2", "knights", 40, -20, **{"class": "cavalry"})],
           "enemy": [unit("e1", "swordsmen", 0, 10, state=["melee"])]}
    policy = HammerAnvil()
    policy.unreachable = REFUSED_EVERYWHERE
    charge = by_unit(policy.decide(obs), "f2")[0]
    assert charge["type"] == "attack" and charge["target"] == "e1" and policy.phase == "charge"


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


def corner_terrain():
    rows = ["." * 25 for _ in range(25)]
    rows[0] = "#" + rows[0][1:]  # the sample holding the south-west corner post
    return {"x0": -384, "z0": -384, "cell_m": 32, "sample_width_m": 8, "rows": rows,
            "bounds": {"min_x": -400, "max_x": 400, "min_z": -400, "max_z": 400}}


def test_corner_hold_takes_its_own_side_corner_past_blocked_cells_and_faces_out():
    obs = {"time_ms": 1000, "terrain": corner_terrain(),
           "friendly": [unit("f1", "longbeards", -300, -310), unit("f2", "longbeards", -310, -300)],
           "enemy": [unit("e1", "swordsmen", 300, 300), unit("e2", "swordsmen", 320, 280)]}
    original = deepcopy(obs)
    policy = CornerHold()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert obs == original
    # 30 m inside the south-west corner is restricted; one 32 m step toward the centre.
    assert all(math.isclose(policy.corner[axis], -370 + 32 / math.sqrt(2)) for axis in "xz")
    assert [order["type"] for order in orders] == ["move", "move"]
    for order in orders:
        assert math.isclose(math.hypot(order["x"] - policy.corner["x"],
                                       order["z"] - policy.corner["z"]), 16, abs_tol=1e-6)
        assert 40 < order["facing"] < 50
    corner = dict(policy.corner)
    obs["enemy"][0].update(x=-300, z=300)
    policy.decide(obs)
    assert policy.corner == corner  # chosen once


def test_corner_hold_clamps_its_line_holds_and_fights_only_in_contact():
    obs = {"time_ms": 1000, "terrain": {**corner_terrain(), "rows": []},
           "friendly": [unit("f1", "longbeards", -330, -330), unit("f2", "longbeards", -340, -320)],
           "enemy": [unit("e1", "swordsmen", -370, 300)]}
    policy = CornerHold()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert policy.corner == {"x": -370, "z": -370}
    assert all(-370 <= order["x"] and -370 <= order["z"] for order in orders)
    for order in orders:
        next(u for u in obs["friendly"] if u["id"] == order["unit"]).update(
            x=order["x"], z=order["z"])
    obs["time_ms"] = 5000
    del obs["terrain"]  # later observations may omit the terrain snapshot
    assert policy.decide(obs) == []
    obs["enemy"][0].update(x=obs["friendly"][0]["x"] + 5, z=obs["friendly"][0]["z"] + 5)
    obs["friendly"][0]["state"] = ["melee"]
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert orders == [{"unit": "f1", "type": "attack", "run": True, "mode": "melee",
                       "target": "e1"}]


def test_focus_fire_commits_every_gun_to_the_weakest_enemy_and_backs_off_contact():
    gun = {"class": "missile", "ammo": 10, "range": 145}
    obs = {"time_ms": 1000, "friendly": [unit("f1", "thunderers", 0, 0, **gun),
           unit("f2", "thunderers", 20, 0, **gun), unit("f3", "warriors", 10, 20)],
           "enemy": [unit("e1", "trolls", 0, 100), unit("e2", "trolls", 30, 110, men=6)]}
    original = deepcopy(obs)
    policy = FocusFire()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    shots = [order for order in orders if order["unit"] in ("f1", "f2")]
    assert len(shots) == 2 and all(o["target"] == "e2" and o["mode"] == "ranged" for o in shots)
    assert next(order for order in orders if order["unit"] == "f3")["target"] == "e1"
    assert obs == original
    obs["time_ms"] = 2000
    obs["enemy"][0]["men"] = 3  # weaker now, but the committed target stays
    policy.decide(obs)
    assert policy.target == "e2"
    obs["time_ms"] = 6000
    obs["enemy"][0].update(x=0, z=30)
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    retreat = next(order for order in orders if order["unit"] == "f1")
    assert retreat["type"] == "move" and retreat["z"] < -30


def test_monster_target_goes_round_the_spears_then_leaves_their_melee():
    obs = {"time_ms": 1000, "friendly": [unit("f1", "giant", 0, 0)],
           "enemy": [unit("e1", "wh3_main_ksl_inf_kossars_1", 0, 200),
                     unit("e2", "wh3_main_ksl_inf_streltsi_0", 40, 260)]}
    original = deepcopy(obs)
    policy = MonsterTarget()
    [order] = policy.decide(obs)
    validate_orders([order], obs)
    # 60 m beyond the riflemen, on the side away from the spears.
    assert order["type"] == "move" and math.hypot(order["x"] - 73.3, order["z"] - 309.9) < 1
    assert obs == original
    obs["time_ms"] = 2000
    obs["friendly"][0].update(x=73, z=309)
    [order] = policy.decide(obs)
    assert order == {"unit": "f1", "type": "attack", "run": True, "mode": "melee",
                     "target": "e2"}
    caught = MonsterTarget()
    obs["friendly"][0].update(x=0, z=195, state=["melee"])
    assert caught.decide(obs) == []
    obs["time_ms"] = 12000
    assert caught.decide(obs)[0]["target"] == "e2"


def test_brace_facing_turns_posts_to_the_riders_and_only_fights_contact():
    obs = {"time_ms": 1000, "friendly": [unit(f"f{n}", "clanrats", 10 * (n - 1), 0, bearing=180)
                                         for n in (1, 2, 3)],
           "enemy": [unit("e1", "hellstriders", 10, 300, **{"class": "cavalry"})]}
    original = deepcopy(obs)
    policy = BraceFacing()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    assert [(round(o["x"]), round(o["z"])) for o in orders] == [(30, 10), (-10, 10), (10, -20)]
    for order in orders:
        toward = math.degrees(math.atan2(10 - order["x"], 300 - order["z"]))
        assert order["type"] == "move" and not order["run"]
        assert abs((order["facing"] - toward + 180) % 360 - 180) < 1
    assert obs == original
    near = BraceFacing()
    obs["enemy"][0].update(x=10, z=50)
    assert near.decide(obs) == []  # within 60 m: stand braced, no chase
    obs["friendly"][0].update(state=["melee"])
    obs["friendly"][2].update(x=40, z=0)
    obs["enemy"][0].update(x=0, z=5)
    orders = near.decide(obs)
    validate_orders(orders, obs)
    assert {order["unit"] for order in orders} == {"f1", "f2", "f3"}
    assert all(order["type"] == "attack" and order["target"] == "e1" for order in orders)


def test_counter_battery_shoots_artillery_first_and_holds_infantry_by_the_gun():
    obs = {"time_ms": 1000, "friendly": [
           unit("f1", "cannon", 0, 0, ammo=20, range=300, **{"class": "artillery"}),
           unit("f2", "warriors", 10, 0)],
           "enemy": [unit("e1", "lobber", 0, 280, **{"class": "artillery"}),
                     unit("e2", "goblins", 20, 200)]}
    original = deepcopy(obs)
    policy = CounterBattery()
    orders = policy.decide(obs)
    validate_orders(orders, obs)
    shot, wait = orders
    assert shot["target"] == "e1" and shot["mode"] == "ranged"
    assert wait["type"] == "move" and round(wait["x"]) == -30 and round(wait["z"]) == 0
    assert obs == original
    far = CounterBattery()
    obs["enemy"][0]["z"] = 400
    move = far.decide(obs)[0]
    assert move["type"] == "move" and round(move["z"]) == 130
    obs["enemy"][0]["state"] = ["routing"]
    obs["time_ms"] = 5000
    orders = far.decide(obs)
    validate_orders(orders, obs)
    assert {order["target"] for order in orders if order["type"] == "attack"} == {"e2"}
