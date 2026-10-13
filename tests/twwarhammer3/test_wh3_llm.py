import json

import pytest

from gameai.ledger import BudgetExhausted, Ledger
from twwarhammer3.battle import llm
from twwarhammer3.protocol import PolicyFailure

USAGE = {"input_tokens": 100, "output_tokens": 20,
         "input_tokens_details": {"cached_tokens": 0},
         "output_tokens_details": {"reasoning_tokens": 5}}


class FakeSend:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.bodies = []

    def __call__(self, body):
        self.bodies.append(body)
        text = self.replies.pop(0)
        return {"id": "resp", "status": "completed", "usage": USAGE,
                "output": [{"type": "message", "content": [{"type": "output_text",
                                                             "text": text}]}]}


def reply(orders, reason="go", notes=None):
    return json.dumps({"orders": orders, "reason": reason, "notes": notes})


def observation(time_ms=30000, visible=("e1",)):
    enemy = [{"id": "e1", "type": "wh_main_dwf_inf_dwarf_warriors_0", "class": "infantry",
              "x": 100.0, "z": 200.0, "bearing": 180, "men": 90, "men0": 100, "hp": 0.9,
              "state": ["moving"]},
             {"id": "e2", "type": "wh_main_dwf_art_grudge_thrower", "class": "artillery",
              "x": 150.0, "z": 260.0, "bearing": 180, "men": 4, "men0": 4, "hp": 1.0,
              "state": []}]
    return {
        "schema": 1, "job": "j", "battle": "b", "seq": 3, "phase": "Deployed",
        "time_ms": time_ms, "speed": 1, "remaining_ms": 3000000, "awaiting_orders": False,
        "armies": {"player": {"faction": "wh3_main_kho_khorne"},
                   "enemy": {"faction": "wh_main_dwf_dwarfs"}},
        "friendly": [
            {"id": "f1", "type": "wh3_main_kho_cha_herald_of_khorne_0", "class": "lord",
             "commander": True, "x": 10.0, "z": -40.0, "bearing": 0, "men": 1, "men0": 1,
             "hp": 1.0, "ammo": 0, "ammo0": 0, "range": 0, "speed": [2.0, 4.0],
             "fatigue": "fresh", "state": ["idle"]},
            {"id": "f2", "type": "wh3_main_kho_inf_chaos_warriors_0", "class": "infantry",
             "commander": False, "x": 0.0, "z": -40.0, "bearing": 0, "men": 110, "men0": 120,
             "hp": 0.93, "ammo": 0, "ammo0": 0, "range": 0, "speed": [1.8, 3.6],
             "fatigue": "active", "state": ["moving"], "dest": [0.0, 20.0]},
        ],
        "enemy_roster": [{"id": "e1", "type": "wh_main_dwf_inf_dwarf_warriors_0"},
                         {"id": "e2", "type": "wh_main_dwf_art_grudge_thrower"}],
        "enemy": [unit for unit in enemy if unit["id"] in visible],
        "orders": None, "result": None,
    }


def policy(tmp_path, *replies, budget=1.0):
    send = FakeSend(*replies)
    agent = llm.LLMPolicy("gpt-6-luna", "low", Ledger(tmp_path / "ledger.jsonl", budget),
                          send=send, system_prompt="Command well.")
    agent.fake = send
    return agent


def test_prompt_shows_units_timing_delay_and_last_seen(tmp_path):
    orders = [{"unit": "f2", "type": "attack", "x": None, "z": None, "target": "e1", "run": False}]
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


def test_invalid_orders_are_retried_with_feedback_then_fail(tmp_path):
    bad = [{"unit": "f9", "type": "halt", "x": None, "z": None, "target": None, "run": False}]
    agent = policy(tmp_path, reply(bad), reply(bad), reply(bad))
    with pytest.raises(PolicyFailure) as failure:
        agent.decide(observation())
    assert failure.value.failure["kind"] == "invalid_reply"
    assert len(failure.value.failure["attempts"]) == 3
    assert "unknown friendly unit 'f9'" in agent.fake.bodies[1]["input"][0]["content"]


def test_attack_on_an_unseen_enemy_is_invalid(tmp_path):
    bad = [{"unit": "f1", "type": "attack", "x": None, "z": None, "target": "e2", "run": False}]
    good = [{"unit": "f1", "type": "move", "x": 5.0, "z": 5.0, "target": None, "run": True}]
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
    move = [{"unit": "f2", "type": "move", "x": 0.0, "z": 30.0, "facing": 180.0, "target": None,
             "run": False}]
    agent = policy(tmp_path, reply(move), reply([]))
    agent.decide(observation())
    later = observation(time_ms=45000, visible=())
    later["enemy_roster"][0]["dead"] = True
    later["awaiting_orders"] = True
    agent.decide(later)
    prompt = agent.metadata()["prompt"]
    assert "e1 dwarf_warriors_0 (destroyed)" in prompt and "Last seen" not in prompt
    assert "30 s: f2 move (0, 30) facing 180 (go)" in prompt
    assert "The battle is paused until you reply" in prompt
    assert "f1 herald_of_khorne_0 (lord) at (10, -40) facing 0, 1/1 men, hp 100%" in prompt


def test_a_bad_facing_is_invalid(tmp_path):
    bad = [{"unit": "f2", "type": "move", "x": 0.0, "z": 30.0, "facing": "north", "target": None,
            "run": False}]
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


def test_prompt_shows_changes_and_the_order_behind_each_target(tmp_path):
    orders = [{"unit": "f2", "type": "attack", "x": None, "z": None, "facing": None,
               "target": "e1", "run": False}]
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
               "target": None, "run": False},
              {"unit": "f2", "type": "attack", "x": None, "z": None, "facing": None,
               "target": "e1", "run": False}]
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
        {"unit": "f1", "type": "move", "x": 50, "z": 20, "width": 30},
        {"unit": "f1", "type": "attack", "target": "e1", "mode": "melee", "queue": True},
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
    move = {"unit": "f1", "type": "move", "x": 50, "z": 20}
    toggle = {"unit": "f1", "type": "behaviour", "behaviour": "fire_at_will", "enabled": False}
    agent = policy(tmp_path, reply([move, toggle]))
    agent.decide(obs)
    agent.acknowledge({"results": [{"unit": "f1", "index": 1, "ok": True},
                                    {"unit": "f1", "index": 2, "ok": True}]}, {})
    assert agent.ordered["f1"]["type"] == "move"


def test_a_rejected_queued_attack_keeps_the_successful_move_in_memory(tmp_path):
    move = {"unit": "f1", "type": "move", "x": 50, "z": 20}
    attack = {"unit": "f1", "type": "attack", "target": "e1", "queue": True}
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
         "cost": 200, "unlocked": True, "button": "inactive", "ready": False, "timer": "1:02"},
        {"key": "blade_of_khorne", "target": "Ground", "cooldown_s": 120, "cost": 300,
         "unlocked": False, "button": "inactive", "ready": False}]}
    text = llm.render_state(state, {})
    assert ("abilities foe_seeker (Self; ready; cooldown 60 s); deadly_onslaught (Self;"
            " recharging, 42 s left; cooldown 90 s; last issued 61 s); spell (Enemy; 8 magic;"
            " not available now; 2 uses left); banner (Around self; active now)") in text
    assert text.startswith(
        'Army abilities (order with unit "army"; points 71, next unlock at 100):'
        " horn_of_khorne (Ground, Ally; radius 35 m; ready; cooldown 90 s); relentless_rage"
        " (Ally; recharging, 1:02 left; cooldown 90 s); blade_of_khorne (Ground; locked,"
        " unlocks at 300 points; cooldown 120 s)\n")


def test_engine_permission_wins_over_readiness_and_unlocks_may_be_complete():
    assert llm.render_ability({"key": "roar", "can_use": False, "ready": True}) == (
        "roar (blocked)")
    assert llm.render_army({"currency": 320, "abilities": [
        {"key": "horn", "unlocked": True, "ready": True}]}) == (
        'Army abilities (order with unit "army"; points 320): horn (ready)')
