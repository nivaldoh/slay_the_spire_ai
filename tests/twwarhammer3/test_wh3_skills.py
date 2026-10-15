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
    assert step(executor, [unit("f1", "infantry", 0, 0)], []) == []  # the post is pinned here
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
    # A routing unit's rejection is retried later; an unreachable point is given up.
    executor.acknowledge({"results": [{"index": 1, "unit": "f1", "ok": False,
                                       "error": "unit_routing"}]}, {})
    assert executor.assignments["f1"]["skill"] == "move"
    executor.acknowledge({"results": [{"index": 1, "unit": "f1", "ok": False,
                                       "error": "unreachable"}]}, {})
    assert executor.assignments["f1"]["skill"] == "hold"
    assert step(executor, [unit("f1", "infantry", 0, 0)], [], 20000) == []
    assert (executor.assignments["f1"]["x"], executor.assignments["f1"]["z"]) == (0, 0)


def test_routing_and_destroyed_units_get_no_orders():
    enemy = unit("e1", "infantry", 0, 50)
    friendly = [unit("f1", "infantry", 0, 0, state=["routing"]), unit("f2", "infantry", 0, 0,
                                                                      men=0)]
    executor = Skills()
    assert step(executor, friendly, [enemy]) == []
    assert executor.phase == {"f1": "routing", "f2": "destroyed"}
    assert skills.default_skill({"class": "flying"}) == "engage"


def test_the_last_target_sent_wins_over_the_lagging_observed_one():
    # Regression (skills-v1-kho-smoke): the ack observation still shows the previous target,
    # and preferring it made a Skullcannon alternate e1/e5 every tick without firing.
    executor = Skills()
    lord, gun = unit("e1", "lord", 0, 140, state=["melee"]), unit("e5", "artillery", 0, 145)
    assert step(executor, [shooter(target="e1")], [lord, gun]) == [attack("f1", "e5", "ranged")]
    lord["state"] = []
    assert step(executor, [shooter(target="e1")], [lord, gun], 10300) == []
    assert step(executor, [shooter(target="e5")], [lord, gun], 10600) == []


def test_charge_without_a_post_halts_the_previous_skills_order():
    executor = Skills()
    enemy = unit("e1", "infantry", 0, 200)
    assert step(executor, [unit("f1", "infantry", 0, 0)], [enemy]) == [attack("f1", "e1")]
    executor.assign(unit("f1", "infantry", 0, 40), {"skill": "charge"}, 11)
    walking = unit("f1", "infantry", 0, 40, target="e1")
    assert step(executor, [walking], [enemy], 11000) == [{"unit": "f1", "type": "halt"}]
    assert step(executor, [walking], [enemy], 11300) == []
    assert executor.phase["f1"] == "waiting for melee"


def test_an_attack_the_game_redirected_is_sent_again_after_two_seconds():
    executor = Skills()
    executor.assign(shooter(), {"skill": "shoot", "target": "e1"}, 10)
    enemies = [unit("e1", "infantry", 0, 100), unit("e2", "infantry", 0, 120, men=99)]
    assert step(executor, [shooter()], enemies) == [attack("f1", "e1", "ranged")]
    assert step(executor, [shooter(target="e2")], enemies, 11000) == []
    assert step(executor, [shooter(target="e2")], enemies, 12000) == [
        attack("f1", "e1", "ranged")]


def test_a_unit_moving_without_a_target_is_still_carrying_out_its_attack():
    # Regression (skills-v1.1-random-a): the engine shows no target while a shooter moves
    # to fire or evades, and the executor re-sent the same attack every 2 s.
    executor = Skills()
    enemy = unit("e1", "cavalry", 0, 100, men=6)
    assert step(executor, [shooter()], [enemy], 10000) == [attack("f1", "e1", "ranged")]
    assert step(executor, [shooter(state=["moving", "running"])], [enemy], 13000) == []
    assert step(executor, [shooter(state=["idle"])], [enemy], 14000) == [
        attack("f1", "e1", "ranged")]


def test_a_shooter_gives_up_on_a_target_in_range_it_never_fires_at():
    executor = Skills()
    chariot, block = unit("e1", "chariot", 0, 100, men=6), unit("e2", "infantry", 0, 140)
    executor.assign(shooter(), {"skill": "shoot", "target": "e1"}, 10)
    assert step(executor, [shooter()], [chariot, block], 10000) == [attack("f1", "e1", "ranged")]
    # A shot (ammunition spent) restarts the clock.
    assert step(executor, [shooter(ammo=19, state=["moving"])], [chariot, block], 20000) == []
    assert step(executor, [shooter(ammo=19, state=["moving"])], [chariot, block], 34000) == []
    assert step(executor, [shooter(ammo=19, state=["moving"])], [chariot, block], 35000) == [
        attack("f1", "e2", "ranged")]
    assert executor.phase["f1"] == "shooting e2 (1 in range); skipping e1 (no shot fired)"
    # The named target is skipped until SKIP_S has passed.
    assert step(executor, [shooter(ammo=19, target="e2")], [chariot, block], 64000) == []
    assert step(executor, [shooter(ammo=19, target="e2")], [chariot, block], 65000) == [
        attack("f1", "e1", "ranged")]


def test_artillery_waits_longer_and_out_of_range_time_does_not_count():
    executor = Skills()
    far, near = unit("e1", "infantry", 0, 200), unit("e1", "infantry", 0, 100)
    gun = shooter(kind="artillery")
    assert step(executor, [gun], [near], 10000) == [attack("f1", "e1", "ranged")]
    aiming = dict(gun, target="e1")
    assert step(executor, [aiming], [near], 39000) == []
    assert step(executor, [aiming], [near], 40000) == [{"unit": "f1", "type": "halt"}]
    assert executor.phase["f1"] == "holding fire; skipping e1 (no shot fired)"
    walker = Skills()
    assert step(walker, [shooter()], [far], 10000) == [attack("f1", "e1", "ranged")]
    assert step(walker, [shooter(state=["moving"])], [far], 40000) == []
    assert step(walker, [shooter(state=["moving"])], [near], 54000) == []
    assert walker.phase["f1"] == "shooting e1 (1 in range)"


def test_the_ability_probe_builds_the_cheapest_option_on_each_usable_slot_once():
    state = observation([unit("f1", "infantry", 0, 0)], [])
    state["mode"] = {"supplies": 1200, "slots": [
        {"id": "s1", "usable": True, "options": [{"name": "tower_piercing_1", "cost": 500},
                                                 {"name": "tower_cannon_4", "cost": 2000}]},
        {"id": "s2", "usable": False, "options": [{"name": "tower_piercing_1", "cost": 500}]},
        {"id": "s3", "usable": True, "options": [{"name": "barricade_1", "cost": 900}]},
        {"id": "s4", "usable": True, "built": "tower_piercing_1"},
    ]}
    probe = skills.ProbeAbilities()
    builds = [o for o in probe.decide(state) if o["type"] == "build"]
    assert builds == [{"unit": "army", "type": "build", "slot": "s1",
                       "option": "tower_piercing_1"}]  # s3 costs more than is left
    validate_orders(builds, state)
    assert not [o for o in probe.decide(state) if o["type"] == "build" and o["slot"] == "s1"]


def test_the_ability_probe_calls_in_the_cheapest_affordable_reinforcement_every_10_s():
    state = observation([unit("f1", "infantry", 0, 0)], [], time_ms=10000)
    state["mode"] = {"supplies": 500, "spawn_zones": [{"id": 14, "x": 320, "z": 0}],
                     "reinforcements": [{"type": "warriors", "cost": 900},
                                        {"type": "marauders", "cost": 400}]}
    probe = skills.ProbeAbilities()
    calls = [o for o in probe.decide(state) if o["type"] == "reinforce"]
    assert calls == [{"unit": "army", "type": "reinforce", "reinforcement": "marauders",
                      "zone": 14}]
    validate_orders(calls, state)
    assert not [o for o in probe.decide(state) if o["type"] == "reinforce"]
    state["time_ms"] = 20000
    assert [o["reinforcement"] for o in probe.decide(state)
            if o["type"] == "reinforce"] == ["marauders"]


def test_the_ability_probe_casts_ready_abilities_once_per_five_seconds():
    probe = skills.ProbeAbilities()
    state = {"time_ms": 10000, "friendly": [
        {"id": "f1", "x": 0.0, "z": 0.0, "men": 1, "state": ["melee"], "target": "e2",
         "abilities": [{"key": "roar", "can_use": True, "ready": True, "target": "Self"},
                       {"key": "bolt", "can_use": True, "ready": True, "target": "Enemy"}]},
        {"id": "f2", "x": 5.0, "z": 9.0, "men": 80, "state": ["melee"], "target": "e2"}],
        "enemy": [{"id": "e2", "x": 3.0, "z": 3.0}], "enemy_roster": [{"id": "e2"}],
        "army": {"abilities": [{"key": "horn", "target": "Ground, Ally", "ready": True},
                               {"key": "rage", "target": "Ally", "ready": True},
                               {"key": "blade", "target": "Ground", "ready": False}]}}
    orders = probe.decide(state)
    validate_orders(orders, state)
    assert [order for order in orders if order["type"] == "ability"] == [
        {"unit": "f1", "type": "ability", "ability": "roar", "target": None, "x": None,
         "z": None},
        {"unit": "army", "type": "ability", "ability": "horn", "target": None, "x": 5.0,
         "z": 9.0},
        {"unit": "army", "type": "ability", "ability": "rage", "target": "f2", "x": None,
         "z": None}]
    assert not [o for o in probe.decide(dict(state, time_ms=14000)) if o["type"] == "ability"]
    assert len([o for o in probe.decide(dict(state, time_ms=15000))
                if o["type"] == "ability"]) == 3
