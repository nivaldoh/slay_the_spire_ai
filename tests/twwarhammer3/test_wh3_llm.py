import json

import pytest
from wh3_fixtures import FakeSend, observation

from gameai.ledger import BudgetExhausted, Ledger
from twwarhammer3.battle import llm
from twwarhammer3.protocol import PolicyFailure

SHAPES = {branch["properties"]["type"]["enum"][0]: set(branch["properties"])
          for branch in llm.REPLY_SCHEMA["properties"]["orders"]["items"]["anyOf"]}


def reply(orders, reason="go", notes=None):
    # Every order has exactly its type's fields, as the strict reply schema requires.
    assert all(set(order) == SHAPES[order["type"]] for order in orders)
    return json.dumps({"orders": orders, "reason": reason, "notes": notes})


def policy(tmp_path, *replies, budget=1.0):
    send = FakeSend(*replies)
    agent = llm.LLMPolicy("gpt-6-luna", "low", Ledger(tmp_path / "ledger.jsonl", budget),
                          send=send, system_prompt="Command well.")
    agent.fake = send
    return agent


def test_prompt_shows_units_timing_delay_and_last_seen(tmp_path):
    orders = [{"unit": "f2", "type": "attack", "target": "e1", "mode": "auto", "run": False,
               "queue": False}]
    agent = policy(tmp_path, reply(orders, notes="hold the line"), reply([]))
    assert agent.decide(observation()) == orders
    prompt = agent.metadata()["prompt"]
    assert "f2 chaos_warriors_0 (infantry) at (0, -40) facing 0, 110/120 men, hp 93%" in prompt
    assert "heading to (0, 20)" in prompt and "e1 dwarf_warriors_0 (infantry)" in prompt
    assert "Enemy roster: e1 dwarf_warriors_0, e2 grudge_thrower" in prompt
    assert "battle time 30 s, 3000 s left" in prompt and "Last orders: none yet." in prompt
    agent.acknowledge({"request": "r1", "results": [{"unit": "f2", "ok": True}],
                       "applied_ms": 34200}, {"think_s": 3.2, "delay_ms": 4200})
    agent.decide(observation(time_ms=45000, visible=()))
    prompt = agent.metadata()["prompt"]
    assert "Battle notes:\nhold the line" in prompt
    assert "issued to the engine 4.2 s after the state you saw (you took 3.2 s to reply)" in prompt
    assert "Last orders: f2 issued." in prompt
    assert "Last seen, not visible now:\n- e1 at (100, 200) 15 s ago, 90 men" in prompt
    assert "30 s: f2 attack e1 (go)" in prompt
    assert agent.totals["calls"] == 2


def test_invalid_orders_are_retried_with_feedback_then_dropped_from_the_last_reply(tmp_path):
    bad = {"unit": "f9", "type": "halt"}
    good = {"unit": "f2", "type": "halt"}
    agent = policy(tmp_path, reply([bad]), reply([bad]), reply([good, bad]), reply([]))
    assert agent.decide(observation()) == [good]  # the battle goes on without the bad order
    assert "unknown friendly unit 'f9'" in agent.fake.bodies[1]["input"][0]["content"]
    assert len(agent.metadata()["attempts"]) == 3
    assert agent.metadata()["dropped"] == ["f9 halt: unknown friendly unit 'f9'"]
    agent.decide(observation(time_ms=45000))
    assert "f2 halt; dropped as still invalid: f9 halt: unknown friendly unit 'f9'" in (
        agent.metadata()["prompt"])


def test_a_reply_that_is_not_json_after_the_retries_is_a_policy_failure(tmp_path):
    agent = policy(tmp_path, "not json", "not json", "not json")
    with pytest.raises(PolicyFailure) as failure:
        agent.decide(observation())
    assert failure.value.failure["kind"] == "invalid_reply"
    assert len(failure.value.failure["attempts"]) == 3


def test_attack_on_an_unseen_enemy_is_invalid(tmp_path):
    bad = [{"unit": "f1", "type": "attack", "target": "e2", "mode": "auto", "run": False,
            "queue": False}]
    good = [{"unit": "f1", "type": "move", "x": 5.0, "z": 5.0, "facing": None, "width": None,
             "run": True, "queue": False}]
    agent = policy(tmp_path, reply(bad), reply(good))
    assert agent.decide(observation()) == good
    assert agent.metadata()["attempts"][0]["error"].startswith("f1: target 'e2' is not visible")


def test_budget_refuses_before_sending(tmp_path):
    agent = policy(tmp_path, reply([]), budget=0.0)
    with pytest.raises(BudgetExhausted):
        agent.decide(observation())
    assert agent.totals["calls"] == 0


def test_request_uses_the_strict_schema(tmp_path):
    agent = policy(tmp_path, reply([]))
    agent.decide(observation())
    body = agent.fake.bodies[0]
    assert body["text"]["format"]["schema"] == llm.REPLY_SCHEMA
    assert body["instructions"] == "Command well."


@pytest.mark.parametrize(("key", "short"), [
    ("wh3_main_kho_inf_chaos_warriors_0", "chaos_warriors_0"),
    ("wh_main_dwf_art_grudge_thrower", "grudge_thrower"),
    ("wh3_dlc20_chs_cav_marauder_horsemen_mkho_throwing_axes",
     "marauder_horsemen_mkho_throwing_axes"),
    ("odd", "odd"),
])
def test_short_type_strips_the_game_prefix(key, short):
    assert llm.short_type(key) == short


def test_dead_enemies_leave_last_seen_and_moves_can_face(tmp_path):
    move = [{"unit": "f2", "type": "move", "x": 0.0, "z": 30.0, "facing": 180.0, "width": None,
             "run": False, "queue": False}]
    agent = policy(tmp_path, reply(move), reply([]))
    agent.decide(observation())
    later = observation(time_ms=45000, visible=())
    later["enemy_roster"][0]["dead"] = True
    agent.decide(later)
    prompt = agent.metadata()["prompt"]
    assert "e1 dwarf_warriors_0 (destroyed)" in prompt and "Last seen" not in prompt
    assert "30 s: f2 move (0, 30) facing 180 (go)" in prompt
    assert "f1 herald_of_khorne_0 (lord) at (10, -40) facing 0, 1/1 men, hp 100%" in prompt


def test_a_bad_facing_is_invalid(tmp_path):
    bad = [{"unit": "f2", "type": "move", "x": 0.0, "z": 30.0, "facing": "north", "width": None,
            "run": False, "queue": False}]
    agent = policy(tmp_path, reply(bad), reply([]))
    agent.decide(observation())
    assert "facing must be a number" in agent.metadata()["attempts"][0]["error"]


def test_dead_friendly_units_are_one_line_and_enemy_range_shows():
    observation_ = observation()
    observation_["friendly"][0].update(men=0, state=["idle", "melee"])
    observation_["enemy"][0]["range"] = 160
    text = llm.render_state(observation_, {})
    assert "- f1 herald_of_khorne_0: destroyed\n" in text
    assert ("e1 dwarf_warriors_0 (infantry) at (100, 200) facing 180, 90/100 men, hp 90%,"
            " range 160") in text


def test_barriers_and_casting_limits_are_distinct_from_health_and_readiness():
    state = observation()
    state["friendly"][0]["barrier"] = {"hp": 0, "max_hp": 600}
    state["enemy"][0]["barrier"] = {"hp": 220, "max_hp": 400}
    state["friendly"][0]["abilities"] = [{
        "key": "test_spell", "target": "Ground", "cast_range": 150.0,
        "radius": 8.0, "duration_s": 12, "mana": 9, "ready": True,
    }]
    text = llm.render_state(state, {})
    assert "barrier 0/600" in text and "hp 90%, barrier 220/400" in text
    assert ("test_spell (Ground; cast range 150 m; radius 8 m; duration 12 s; "
            "9 magic; ready)") in text


def test_flying_lord_keeps_role_and_reports_airborne_or_grounded_state():
    state = observation()
    state["friendly"][0].update(can_fly=True, flying=True)
    text = llm.render_state(state, {})
    assert "(lord)" in text and "can fly, airborne" in text
    state["friendly"][0]["flying"] = False
    assert "can fly, on the ground" in llm.render_state(state, {})


def test_visible_enemy_speed_is_reported_with_its_flight_capability():
    state = observation()
    state["enemy"][0].update(speed=[10.5, 10.5], can_fly=True, flying=True)
    text = llm.render_state(state, {})
    enemy_line = next(line for line in text.splitlines() if line.startswith("- e1 "))
    assert "can fly, airborne" in enemy_line and "walk 10.5 run 10.5" in enemy_line


def test_prompt_shows_changes_and_the_order_behind_each_target(tmp_path):
    orders = [{"unit": "f2", "type": "attack", "target": "e1", "mode": "auto", "run": False,
               "queue": False}]
    agent = policy(tmp_path, reply(orders), reply([]))
    agent.decide(observation())
    agent.acknowledge({"request": "r1", "results": [{"unit": "f2", "ok": True}],
                       "applied_ms": 34000}, {"think_s": 3.0, "delay_ms": 4000})
    later = observation(time_ms=40000)
    later["friendly"][1].update(men=104, hp=0.85, target="e2", dest=None)
    later["friendly"][0]["target"] = "e1"
    later["enemy"][0].update(men=85, x=0.0, z=-10.0)
    agent.decide(later)
    prompt = agent.metadata()["prompt"]
    assert "110/120 men" not in prompt and "104/120 men (-6), hp 85% (-8)" in prompt
    assert "target e2, game's choice; your order at 30 s was e1 30 m" in prompt
    assert "f1 herald_of_khorne_0" in prompt and "target e1 32 m, game's choice" in prompt
    assert "85/100 men (-5), hp 90%" in prompt


def test_lapsed_orders_are_forgotten_and_dropped_moves_reported(tmp_path):
    orders = [{"unit": "f1", "type": "move", "x": 10.0, "z": 60.0, "facing": None,
               "width": None, "run": False, "queue": False},
              {"unit": "f2", "type": "attack", "target": "e1", "mode": "auto", "run": False,
               "queue": False}]
    agent = policy(tmp_path, reply(orders), reply([]))
    agent.decide(observation())
    agent.acknowledge({"request": "r1", "results": [{"unit": "f1", "ok": True},
                                                    {"unit": "f2", "ok": True}],
                       "applied_ms": 34000}, {"think_s": 3.0, "delay_ms": 4000})
    later = observation(time_ms=40000)
    later["friendly"][1].update(state=["idle"], dest=None)
    agent.decide(later)
    prompt = agent.metadata()["prompt"]
    assert "stopped 100 m short of your move (30 s)" in prompt
    assert "your order" not in prompt.split("f2 chaos_warriors_0")[1].split("\n")[0]
    assert agent.ordered == {"f1": dict(orders[0], time_s=30.0)}


def test_units_without_a_target_show_no_order_and_their_nearest_enemy():
    observation_ = observation()
    observation_["friendly"][0]["state"] = []
    observation_["friendly"].append({**observation_["friendly"][1], "id": "f3",
                                     "state": ["routing"], "dest": None})
    text = llm.render_state(observation_, {})
    assert "fresh, no order, nearest enemy e1 256 m" in text
    assert "heading to (0, 20), nearest enemy e1 260 m" in text
    assert "nearest" not in text.split("- f3 ")[1].split("\n")[0]


def test_capabilities_are_visible_and_queued_attack_is_not_mistaken_for_active(tmp_path):
    obs = observation()
    unit = obs["friendly"][0]
    unit.update(width=25, ammo=5, behaviours={"fire_at_will": False},
                abilities=[{"key": "buff", "can_use": True, "last_issued_ms": 12300}],
                attack_mode="melee")
    orders = [
        {"unit": "f1", "type": "behaviour", "behaviour": "fire_at_will", "enabled": True},
        {"unit": "f1", "type": "move", "x": 50, "z": 20, "facing": None, "width": 30,
         "run": False, "queue": False},
        {"unit": "f1", "type": "attack", "target": "e1", "mode": "melee", "run": False,
         "queue": True},
    ]
    agent = policy(tmp_path, reply(orders), reply([]))
    agent.decide(obs)
    agent.acknowledge({"results": [
        {"unit": "f1", "index": 1, "ok": True},
        {"unit": "f1", "index": 2, "ok": True},
        {"unit": "f1", "index": 3, "ok": True, "queued": True},
    ]}, {"think_s": 2, "delay_ms": 2300})
    unit["command_queue"] = orders[1:]
    agent.decide(obs)
    prompt = agent.metadata()["prompt"]
    assert "formation width 25 m" in prompt and "fire_at_will=off" in prompt
    assert "buff (readiness unknown; last issued 12 s)" in prompt
    assert "last requested attack mode melee" in prompt
    assert "f1 #3 queued" in prompt and "completion unconfirmed" in prompt
    assert "attack e1 melee [queued]" in prompt
    assert not agent.ordered


def test_a_toggle_ack_does_not_replace_the_previous_movement_order(tmp_path):
    obs = observation()
    obs["friendly"][0]["behaviours"] = {"fire_at_will": True}
    move = {"unit": "f1", "type": "move", "x": 50, "z": 20, "facing": None, "width": None,
            "run": False, "queue": False}
    toggle = {"unit": "f1", "type": "behaviour", "behaviour": "fire_at_will", "enabled": False}
    agent = policy(tmp_path, reply([move, toggle]))
    agent.decide(obs)
    agent.acknowledge({"results": [{"unit": "f1", "index": 1, "ok": True},
                                    {"unit": "f1", "index": 2, "ok": True}]}, {})
    assert agent.ordered["f1"]["type"] == "move"


def test_a_rejected_queued_attack_keeps_the_successful_move_in_memory(tmp_path):
    move = {"unit": "f1", "type": "move", "x": 50, "z": 20, "facing": None, "width": None,
            "run": False, "queue": False}
    attack = {"unit": "f1", "type": "attack", "target": "e1", "mode": "auto", "run": False,
              "queue": True}
    agent = policy(tmp_path, reply([move, attack]))
    agent.decide(observation())
    agent.acknowledge({"results": [{"unit": "f1", "index": 1, "ok": True},
                                    {"unit": "f1", "index": 2, "ok": False,
                                     "error": "target_not_visible"}]}, {})
    assert agent.ordered["f1"]["type"] == "move"


def test_magic_state_is_player_only_and_unknown_values_are_not_zero():
    obs = observation()
    obs["magic"] = {"current": 23.5, "reserve": 42}
    assert "Winds of Magic: 23.5 available, 42 reserve" in llm.render_state(obs, {})
    obs["magic"] = {"reserve": 42}
    assert "Winds of Magic: unknown available, 42 reserve" in llm.render_state(obs, {})


def test_an_ability_with_half_a_ground_point_is_described_without_crashing():
    order = {"unit": "f1", "type": "ability", "ability": "roar", "target": None, "x": 10.0,
             "z": None, "facing": None, "width": None}
    assert llm.describe_orders([order]) == "f1 ability roar at self"


def test_abilities_show_target_cost_and_readiness_and_army_abilities_their_unlocks():
    state = observation()
    state["friendly"][0]["abilities"] = [
        {"key": "foe_seeker", "can_use": True, "ready": True, "target": "Self", "cooldown_s": 60},
        {"key": "deadly_onslaught", "can_use": True, "ready": False, "recharge_s": 41.6,
         "target": "Self", "cooldown_s": 90, "last_issued_ms": 61000},
        {"key": "spell", "can_use": True, "ready": False, "target": "Enemy", "mana": 8,
         "uses": 2},
        {"key": "banner", "can_use": True, "ready": False, "active": True,
         "target": "Around self"}]
    state["army"] = {"currency": 71, "next_unlock": 100, "abilities": [
        {"key": "horn_of_khorne", "target": "Ground, Ally", "radius": 35, "cooldown_s": 90,
         "cost": 100, "unlocked": True, "button": "active", "ready": True},
        {"key": "relentless_rage", "target": "Ally", "radius": 0, "cooldown_s": 90,
         "cost": 200, "unlocked": True, "button": "inactive", "ready": False, "timer": "62"},
        {"key": "blade_of_khorne", "target": "Ground", "cooldown_s": 120, "cost": 300,
         "unlocked": False, "button": "inactive", "ready": False}]}
    text = llm.render_state(state, {})
    assert ("abilities foe_seeker (Self; ready; cooldown 60 s); deadly_onslaught (Self;"
            " recharging, 42 s left; cooldown 90 s; last issued 61 s); spell (Enemy; 8 magic;"
            " not available now; 2 uses left); banner (Around self; active now)") in text
    assert text.startswith(
        'Army abilities (order with unit "army"; points 71, next unlock at 100):'
        " horn_of_khorne (Ground, Ally; radius 35 m; ready; cooldown 90 s); relentless_rage"
        " (Ally; recharging, 62 s left; cooldown 90 s); blade_of_khorne (Ground; locked,"
        " unlocks at 300 points; cooldown 120 s)\n")


def test_engine_permission_wins_over_readiness_and_unlocks_may_be_complete():
    assert llm.render_ability({"key": "roar", "can_use": False, "ready": True}) == (
        "roar (blocked)")
    assert llm.render_army({"currency": 320, "abilities": [
        {"key": "horn", "unlocked": True, "ready": True}]}) == (
        'Army abilities (order with unit "army"; points 320): horn (ready)')
    assert llm.render_ability({"key": "horn", "unlocked": True, "button": "selected_inactive",
                               "timer": "28", "ready": False}) == "horn (active now, 28 s left)"


def test_the_mode_section_states_role_objectives_tickets_and_points():
    battle = {
        "type": "conquest", "role": "defender", "timeout_winner": "us",
        "objectives": "Objectives: reach 500 victory tickets by seizing capture points.",
        "tickets": [{"side": "us", "tickets": 11, "per_s": 1, "score": 1080},
                    {"side": "enemy", "tickets": 87, "per_s": 0, "score": 700}],
        "tickets_goal": 600,
        "capture_points": [{"id": "domination_1", "name": "Victory Location", "x": 256.0,
                            "z": 0.0, "holder": None, "contested": True, "locked": False,
                            "percent": 40, "victory": True}],
    }
    text = llm.render_state({"mode": battle, "friendly": [], "enemy": []}, {})
    assert text.startswith("Battle: conquest; you are the defender; if time runs out, you win.")
    assert "Tickets (600 wins): you 11 (+1/s), enemy 87 (+0/s)." in text
    assert ("- domination_1 Victory Location at (256, 0): held by nobody, 40% captured,"
            " contested, counts for victory") in text
    assert llm.render_mode(None) is None
    assert llm.render_mode({"type": "land_normal", "role": "attacker",
                              "timeout_winner": "enemy"}) == (
        "Battle: land_normal; you are the attacker; if time runs out, enemy wins.")


def test_a_siege_shows_the_defenders_tickets_without_a_goal_and_the_gate():
    mode = {"type": "settlement_standard", "role": "defender", "timeout_winner": "us",
            "tickets": [{"side": "us", "tickets": 1000, "per_s": 5, "score": 728}],
            "capture_points": [{"id": "c1", "key": "major_key_building_leadership",
                                "name": "Key Building", "x": 0, "z": 310, "holder": "us",
                                "percent": 100, "victory": True}],
            "gates": [{"name": "Gatehouse", "x": -32, "z": -16, "hp": 37, "destroyed": False}],
            "supplies": 8034}
    text = llm.render_mode(mode)
    assert "Tickets: you 1000." in text  # a defender's tickets have no goal and no income
    assert "- c1 Key Building at (0, 310): held by you, counts for victory" in text
    assert "Gatehouse at (-32, -16): 37% health." in text
    assert text.endswith("Supplies: 8034.")


def test_building_slots_show_options_progress_and_build_orders_are_described():
    text = llm.render_mode({"type": "settlement_standard", "supplies": 900, "slots": [
        {"id": "s1", "type": "tower", "x": 55.2, "z": 191.7, "usable": True,
         "options": [{"name": "tower_piercing_1", "cost": 500}]},
        {"id": "s2", "type": "tower", "x": -56, "z": 192, "usable": True,
         "built": "tower_piercing_1", "building_s": 74.9},
        {"id": "s3", "type": "barricade", "x": 0, "z": 0, "usable": False,
         "options": [{"name": "barricade_1", "cost": 300}]},
    ]})
    assert "- s1 tower at (55, 192): empty, options tower_piercing_1 500" in text
    assert "- s2 tower at (-56, 192): building tower_piercing_1, 75 s left" in text
    assert "- s3 barricade at (0, 0): empty, options barricade_1 300 (cannot build now)" in text
    assert llm.describe_orders([{"unit": "army", "type": "build", "slot": "s1",
                                 "option": "tower_piercing_1"}]) == (
        "army build tower_piercing_1 on s1")


def test_the_reinforcement_pool_and_spawn_zones_are_listed():
    pool = [{"type": "wh3_main_kho_inf_chaos_warriors_1", "cost": 900}]
    text = llm.render_mode({"type": "survival", "supplies": 1120, "reinforcements": pool,
                            "spawn_zones": [{"id": 14, "x": 320, "z": 0, "usable": True},
                                            {"id": 9, "x": 0, "z": 246, "usable": False}]})
    assert "): wh3_main_kho_inf_chaos_warriors_1 900." in text
    assert "Your spawn zones: 14 at (320, 0), 9 at (0, 246) (refuses purchases now)." in text
    assert llm.describe_orders([{"unit": "army", "type": "reinforce", "zone": 14,
                                 "reinforcement": "wh3_main_kho_inf_chaos_warriors_1"}]) == (
        "army reinforce chaos_warriors_1 at zone 14")


def test_public_morale_warning_and_flight_control_are_rendered():
    unit = {"id": "f1", "type": "caster", "men": 1, "men0": 1, "hp": 1,
            "can_fly": True, "flying": True,
            "flight": {"can_toggle": True, "cooldown_s": 0},
            "morale": {"fraction": .3, "effect": "You must attack by land!"}}
    text = llm.render_unit(unit, True)
    assert "leadership 30%; largest effect: You must attack by land!" in text
    assert "airborne" in text and "flight change available; cooldown 0 s" in text
    assert llm.describe_orders([{"unit": "f1", "type": "flight", "flying": False}]) == "f1 land"


def test_terrain_and_rejected_move_alternatives_reach_both_model_renderers():
    state = {"terrain": {"x0": -16, "z0": -16, "cell_m": 32, "sample_width_m": 16,
                         "rows": [".#", ".."]},
             "friendly": [{"id": "f1", "type": "inf", "men": 10, "men0": 10,
                           "hp": 1, "x": 0, "z": 0, "state": [], "navigation": {
                               "rejected": {"x": 100, "z": 100}, "sampled_ms": 5000,
                               "alternatives": [{"x": 84, "z": 100}]}}]}
    text = llm.render_state(state, {})
    assert "columns increase x and rows increase z by 32 m" in text
    assert "Narrow crossings can lie between samples" in text
    assert "unreachable move (100,100)" in text and "(84,100)" in text
