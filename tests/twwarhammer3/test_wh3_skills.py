from twwarhammer3.battle import skills
from twwarhammer3.battle.skills import Skills
from twwarhammer3.protocol import validate_orders


def unit(unit_id, kind, x, z, **fields):
    return {"id": unit_id, "type": f"t_{kind}", "class": kind, "x": float(x), "z": float(z),
            "bearing": 0, "men": 50, "men0": 50, "hp": 1.0, "state": [], **fields}


def shooter(unit_id="f1", x=0, z=0, kind="missile", **fields):
    return unit(unit_id, kind, x, z, **{"ammo": 20, "ammo0": 20, "range": 150, **fields})


def observation(friendly, enemy, time_ms=10000):
    return {"time_ms": time_ms, "friendly": friendly, "enemy": enemy,
            "enemy_roster": [{"id": e["id"], "type": e["type"]} for e in enemy]}


def step(executor, friendly, enemy, time_ms=10000):
    state = observation(friendly, enemy, time_ms)
    orders = executor.decide(state)
    validate_orders(orders, state)
    return orders


def attack(unit_id, target, mode="melee", run=False):
    return {"unit": unit_id, "type": "attack", "target": target, "mode": mode, "run": run,
            "queue": False}


def test_defaults_follow_the_unit_class():
    executor = Skills()
    kinds = ["lord", "hero", "infantry", "monster", "missile", "artillery", "missile_chariot",
             "cavalry", "missile_cavalry", "chariot"]
    friendly = [unit(f"f{i}", kind, 0, 0) for i, kind in enumerate(kinds)]
    step(executor, friendly, [])
    assert [executor.assignments[f"f{i}"]["skill"] for i in range(len(kinds))] == [
        "charge", "charge", "engage", "engage", "shoot", "shoot", "shoot", "charge", "charge",
        "charge"]


def test_engage_walks_at_the_nearest_live_enemy_and_keeps_its_target():
    executor = Skills()
    far, near = unit("e1", "infantry", 0, 100), unit("e2", "infantry", 0, 80)
    assert step(executor, [unit("f1", "infantry", 0, 0)], [far, near]) == [attack("f1", "e2")]
    # Once fighting e2 it keeps it, even with another enemy now nearer.
    closer = unit("e1", "infantry", 0, 50)
    assert step(executor, [unit("f1", "infantry", 0, 10, target="e2")], [closer, near]) == []
    routing = dict(near, state=["routing"])
    assert step(executor, [unit("f1", "infantry", 0, 10, target="e2")], [closer, routing]) == [
        attack("f1", "e1")]
    # Routers are chased only when nothing else is in sight.
    assert step(Skills(), [unit("f1", "infantry", 0, 0)], [routing]) == [attack("f1", "e2")]


def test_free_units_go_for_the_enemy_lord_in_melee_nearby():
    lord = unit("e1", "lord", 0, 35, commander=True, state=["melee"])
    other = unit("e2", "infantry", 0, 20)
    assert step(Skills(), [unit("f1", "infantry", 0, 0)], [lord, other]) == [
        attack("f1", "e1", run=False)]
    far_lord = dict(lord, z=200.0)
    assert step(Skills(), [unit("f1", "infantry", 0, 0)], [far_lord, other]) == [
        attack("f1", "e2", run=True)]


def test_running_starts_inside_30_m_with_one_resend_and_stays_on():
    executor = Skills()
    enemy = unit("e1", "infantry", 0, 50)
    assert step(executor, [unit("f1", "infantry", 0, 0)], [enemy]) == [attack("f1", "e1")]
    assert step(executor, [unit("f1", "infantry", 0, 25, target="e1")], [enemy]) == [
        attack("f1", "e1", run=True)]
    assert step(executor, [unit("f1", "infantry", 0, 15, target="e1")], [dict(enemy, z=60.0)]) == []


def test_units_in_melee_are_left_alone_except_by_a_move():
    executor = Skills()
    fighting = unit("f1", "infantry", 0, 0, state=["melee"], target="e1")
    enemy = unit("e1", "infantry", 0, 5, state=["melee"])
    assert step(executor, [fighting], [enemy]) == []
    executor.assign(fighting, {"skill": "move", "x": 0, "z": -60}, 10)
    orders = step(executor, [fighting], [enemy])
    assert orders[0]["type"] == "move" and orders[0]["run"] is True
    assert executor.phase["f1"] == "moving"


def test_shoot_prefers_the_largest_block_in_range_over_shooters():
    executor = Skills()
    enemies = [unit("e1", "missile", 0, 100, men=80), unit("e2", "infantry", 0, 140, men=60),
               unit("e3", "infantry", 0, 120, men=40), unit("e4", "infantry", 0, 300, men=99)]
    assert step(executor, [shooter()], enemies) == [attack("f1", "e2", "ranged")]
    assert executor.phase["f1"] == "shooting e2 (3 in range)"


def test_shoot_holds_fire_once_when_its_target_enters_melee_unless_named():
    executor = Skills()
    enemy = unit("e1", "infantry", 0, 100)
    assert step(executor, [shooter()], [enemy]) == [attack("f1", "e1", "ranged")]
    fighting = dict(enemy, state=["melee"])
    assert step(executor, [shooter(target="e1")], [fighting]) == [{"unit": "f1", "type": "halt"}]
    assert step(executor, [shooter()], [fighting]) == []
    executor.assign(shooter(), {"skill": "shoot", "target": "e1"}, 10)
    assert step(executor, [shooter()], [fighting]) == [attack("f1", "e1", "ranged")]


def test_shoot_walks_to_its_spot_and_artillery_never_advances():
    executor = Skills()
    executor.assign(shooter(), {"skill": "shoot", "x": 50, "z": 0}, 10)
    orders = step(executor, [shooter()], [unit("e1", "infantry", 50, 100)])
    assert orders == [{"unit": "f1", "type": "move", "x": 50, "z": 0, "facing": 0, "width": None,
                       "run": False, "queue": False}]
    far = unit("e1", "infantry", 0, 600)
    assert step(Skills(), [shooter(kind="artillery")], [far]) == []
    # Without a spot, a missile unit closes on a target out of range; the engine walks it.
    assert step(Skills(), [shooter()], [far]) == [attack("f1", "e1", "ranged")]


def test_a_shooter_out_of_ammunition_charges_and_artillery_idles():
    fighting = unit("e1", "infantry", 0, 100, state=["melee"])
    assert step(Skills(), [shooter(ammo=0)], [fighting]) == [attack("f1", "e1", run=False)]
    assert step(Skills(), [shooter(kind="artillery", ammo=0)], [fighting]) == []


def test_charge_waits_for_melee_then_runs_in_when_mounted():
    executor = Skills()
    enemy = unit("e1", "infantry", 0, 100)
    horse, lord = unit("f1", "cavalry", 0, 0), unit("f2", "lord", 10, 0)
    assert step(executor, [horse, lord], [enemy]) == []
    assert executor.phase["f1"] == "waiting for melee"
    fighting = dict(enemy, state=["melee"])
    assert step(executor, [horse, lord], [fighting]) == [
        attack("f1", "e1", run=True), attack("f2", "e1", run=False)]
    named = Skills()
    named.assign(horse, {"skill": "charge", "target": "e2", "x": 0, "z": -50}, 10)
    orders = step(named, [horse], [fighting, unit("e2", "missile", 50, 120)])
    assert orders[0]["type"] == "move" and (orders[0]["x"], orders[0]["z"]) == (0, -50)
    assert named.phase["f1"] == "waiting: e2 not in melee, moving to post"


def test_hold_returns_to_its_post_and_fights_near_it():
    executor = Skills()
    executor.assign(unit("f1", "infantry", 0, 0), {"skill": "hold"}, 10)
    away = unit("f1", "infantry", 0, 30)
    orders = step(executor, [away], [unit("e1", "infantry", 0, 200)])
    assert orders[0]["type"] == "move" and (orders[0]["x"], orders[0]["z"]) == (0, 0)
    assert step(executor, [away], [unit("e1", "infantry", 0, 35)]) == [
        attack("f1", "e1", "auto", run=True)]


def test_orders_repeat_only_after_they_lapse_for_two_seconds():
    executor = Skills()
    enemy = unit("e1", "infantry", 0, 100)
    assert step(executor, [unit("f1", "infantry", 0, 0)], [enemy], 10000) == [attack("f1", "e1")]
    # The engine has not shown the target yet: no repeat within REPEAT_S.
    assert step(executor, [unit("f1", "infantry", 0, 0, state=["idle"])], [enemy], 11000) == []
    assert step(executor, [unit("f1", "infantry", 0, 5, target="e1")], [enemy], 13000) == []
    assert step(executor, [unit("f1", "infantry", 0, 5, state=["idle"])], [enemy], 13500) == [
        attack("f1", "e1")]


def test_a_rejected_move_turns_into_holding_where_the_unit_stands():
    executor = Skills()
    executor.assign(unit("f1", "infantry", 0, 0), {"skill": "move", "x": 500, "z": 500}, 10)
    assert step(executor, [unit("f1", "infantry", 0, 0)], [])[0]["type"] == "move"
    executor.acknowledge({"results": [{"index": 1, "unit": "f1", "ok": False}]}, {})
    assert executor.assignments["f1"]["skill"] == "hold"
    assert step(executor, [unit("f1", "infantry", 0, 0)], [], 20000) == []


def test_routing_and_destroyed_units_get_no_orders():
    enemy = unit("e1", "infantry", 0, 50)
    friendly = [unit("f1", "infantry", 0, 0, state=["routing"]), unit("f2", "infantry", 0, 0,
                                                                      men=0)]
    executor = Skills()
    assert step(executor, friendly, [enemy]) == []
    assert executor.phase == {"f1": "routing", "f2": "destroyed"}
    assert skills.default_skill({"class": "flying"}) == "engage"
