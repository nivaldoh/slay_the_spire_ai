"""API policy accounting, memory and parsing with a fake client; no network."""

import io
import json
import urllib.error

import pytest
from test_fullgame import combat_message, message

from spire import fullgame, llm
from spire.protocol import PolicyFailure

USAGE = {"input_tokens": 1000, "input_tokens_details": {"cached_tokens": 400},
         "output_tokens": 200, "output_tokens_details": {"reasoning_tokens": 150}}


class FakeClient:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.bodies = []

    def create(self, body):
        self.bodies.append(body)
        text = self.replies.pop(0)
        text = text if isinstance(text, str) else json.dumps(text)
        return {"id": f"resp-{len(self.bodies)}", "status": "completed", "usage": USAGE,
                "output": [{"type": "reasoning"}, {"type": "message", "content": [
                    {"type": "output_text", "text": text}]}]}


def reply(choice, notes=None):
    return {"choice": choice, "reason": "because", "notes": notes}


def decision():
    return fullgame.decision_from_message(combat_message(), session_id="s", sequence=1)


def policy(tmp_path, *replies, budget=1.0):
    ledger = llm.Ledger(tmp_path / "spend.jsonl", budget)
    return llm.LLMPolicy("gpt-6-luna", "low", ledger, client=FakeClient(*replies),
                         system_prompt="Play well.")


def test_usage_cost_prices_uncached_cached_and_output_tokens():
    expected = (600 * 10 + 400 * 1 + 200 * 50) / 1e6
    assert llm.usage_cost("gpt-6-astra", USAGE) == pytest.approx(expected)


def test_choice_updates_notes_history_ledger_and_metadata(tmp_path):
    agent = policy(tmp_path, reply(1, notes="Jaw Worm hits hard."), reply(0))
    first = decision()
    assert agent.choose(first) == first.candidates[1]
    metadata = agent.choice_metadata(first.id)
    assert metadata["reason"] == "because" and metadata["notes"] == "Jaw Worm hits hard."
    assert "Choices:\n0: play Strike (1 attack) -> Jaw Worm [1]" in metadata["prompt"]
    body = agent.client.bodies[0]
    assert body["reasoning"] == {"effort": "low"} and body["store"] is False
    assert body["text"]["format"]["strict"] is True
    agent.choose(decision())
    second_prompt = agent.client.bodies[1]["input"][0]["content"]
    assert "Run notes:\nJaw Worm hits hard." in second_prompt
    assert "floor 3: play Defend (1 skill) (because)" in second_prompt
    assert agent.totals["calls"] == 2 and agent.totals["reasoning_tokens"] == 300
    lines = (tmp_path / "spend.jsonl").read_text().splitlines()
    assert [json.loads(line)["response_id"] for line in lines] == ["resp-1", "resp-2"]
    assert llm.Ledger(tmp_path / "spend.jsonl", 1.0).spent == pytest.approx(agent.totals["usd"])


def test_invalid_replies_are_retried_then_fail_as_policy_failure(tmp_path):
    agent = policy(tmp_path, "not json", reply(99), reply(2))
    assert agent.choose(decision()).command == "potion use 0 1"
    attempts = agent._metadata["attempts"]
    assert [bool(a.get("error")) for a in attempts] == [True, True, False]
    assert "previous reply was invalid" in agent.client.bodies[2]["input"][0]["content"]
    failing = policy(tmp_path, reply(-1), reply(-1), reply(-1))
    with pytest.raises(PolicyFailure) as error:
        failing.choose(decision())
    assert len(error.value.failure["attempts"]) == 3


def test_budget_refuses_a_call_before_sending(tmp_path):
    agent = policy(tmp_path, reply(0), budget=0.0001)
    with pytest.raises(llm.BudgetExhausted):
        agent.choose(decision())
    assert agent.client.bodies == []
    assert not (tmp_path / "spend.jsonl").exists()


def test_map_rendering_lists_only_reachable_nodes():
    nodes = [
        {"x": 0, "y": 1, "symbol": "M", "children": [{"x": 0, "y": 2}]},
        {"x": 3, "y": 1, "symbol": "?", "children": [{"x": 3, "y": 2}]},
        {"x": 0, "y": 2, "symbol": "R", "children": []},
        {"x": 3, "y": 2, "symbol": "E", "children": []},
    ]
    raw = message(["choose"], screen_type="MAP", map=nodes, choice_list=["x=0"],
                  screen_state={"current_node": {"x": 0, "y": 0},
                                "next_nodes": [{"x": 0, "y": 1, "symbol": "M"}]})
    text = llm.render_state(fullgame.decision_from_message(raw, session_id="s",
                                                           sequence=1).to_dict()["observation"])
    assert "y=1: 0M>0" in text and "y=2: 0R>boss" in text
    assert "3?" not in text and "3E" not in text


def test_combat_rendering_shows_intents_dead_enemies_and_piles():
    text = llm.render_state(decision().to_dict()["observation"])
    assert "Combat (event), turn 2. Energy 3." in text
    assert "[0] Louse: dead" in text
    assert "[1] Jaw Worm: HP 30/44, block 0, intent ATTACK 11; powers: Strength 3" in text
    assert "Draw pile (2): Anger (0 attack), Bash (2 attack)" in text
    assert "Incoming attack damage this turn: 11, against your 0 block and 70 HP." in text


def test_event_text_markup_is_removed():
    assert llm._clean("You find #ygold. NL The @ghost@ ~waves~.") == (
        "You find gold.\nThe ghost waves."
    )


def test_api_key_file_and_transient_retry_without_leaking_the_key(tmp_path, monkeypatch):
    key_file = tmp_path / "key"
    key_file.write_text("sk-test-secret\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SPIRE_OPENAI_KEY_FILE", str(key_file))
    assert llm.api_key() == "sk-test-secret"
    responses = [
        urllib.error.HTTPError("u", 503, "busy", {}, io.BytesIO(b"busy")),
        io.BytesIO(b'{"id": "ok"}'),
        urllib.error.HTTPError("u", 401, "no", {}, io.BytesIO(b"bad key sk-test-secret")),
    ]

    def urlopen(request, timeout):
        assert request.headers["Authorization"] == "Bearer sk-test-secret"
        value = responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)
    client = llm.ResponsesClient(llm.api_key())
    assert client.create({}) == {"id": "ok"}
    with pytest.raises(llm.APIError) as error:
        client.create({})
    assert "sk-test-secret" not in str(error.value) and "<key>" in str(error.value)


def test_combat_rendering_names_the_room_and_omits_an_empty_selection():
    raw = combat_message()
    raw["game_state"].update(room_type="MonsterRoomBoss", act_boss="Slime Boss")
    observation = fullgame.decision_from_message(raw, session_id="s", sequence=1).observation
    text = llm.render_state(dict(observation))
    assert text.startswith("Act 1, floor 3. Act boss: Slime Boss, on floor 16. HP 70/80,")
    assert "Combat (boss), turn 2." in text
    grid = message(["confirm"], screen_type="GRID", screen_state={
        "confirm_up": True, "for_upgrade": True, "num_cards": 1, "selected_cards": []})
    observation = fullgame.decision_from_message(grid, session_id="s", sequence=1).observation
    assert "Choose 1 card(s) to upgrade.\n" in llm.render_state(dict(observation)) + "\n"


def test_rules_notes_appear_only_for_present_noted_enemies():
    raw = combat_message()
    raw["game_state"]["combat_state"]["monsters"][1].update(id="SlimeBoss", name="Slime Boss")
    raw["game_state"]["combat_state"]["player"]["powers"] = [
        {"id": "Corruption", "name": "Corruption", "amount": -1}]
    observation = fullgame.decision_from_message(raw, session_id="s", sequence=1).observation
    notes = {"SlimeBoss": "It splits at half HP.", "FuzzyLouseNormal": "Gone, so omitted."}
    text = llm.render_state(dict(observation), notes)
    assert "Enemy rules:\n  Slime Boss: It splits at half HP." in text
    assert "Gone, so omitted." not in text and "powers: Corruption\n" in text
    assert set(json.loads(llm.MONSTER_NOTES_PATH.read_text())) >= {
        "Lagavulin", "SlimeBoss", "AcidSlime_L", "SpikeSlime_L"}
