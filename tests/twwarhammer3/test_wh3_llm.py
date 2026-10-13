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
    assert "took effect 4.2 s after the state you saw (you took 3.2 s to reply)" in prompt
    assert "Last orders: f2 applied." in prompt
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
