"""Prompt rendering, memory, parsing and accounting with a fake transport; no network."""

import json

import pytest
from test_decisions import card, combat_message, message

from gameai.ledger import BudgetExhausted, Ledger
from spire import decisions
from spire.fullrun import llm
from spire.protocol import PolicyFailure

USAGE = {"input_tokens": 1000, "input_tokens_details": {"cached_tokens": 400},
         "output_tokens": 200, "output_tokens_details": {"reasoning_tokens": 150}}


class FakeSend:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.bodies = []

    def __call__(self, body):
        self.bodies.append(body)
        text = self.replies.pop(0)
        text = text if isinstance(text, str) else json.dumps(text)
        return {"id": f"resp-{len(self.bodies)}", "status": "completed", "usage": USAGE,
                "output": [{"type": "reasoning"}, {"type": "message", "content": [
                    {"type": "output_text", "text": text}]}]}


def reply(choice, notes=None):
    return {"choice": choice, "reason": "because", "notes": notes}


def decision():
    return decisions.decision_from_message(combat_message(), session_id="s", sequence=1)


def policy(tmp_path, *replies, budget=1.0):
    ledger = Ledger(tmp_path / "spend.jsonl", budget)
    return llm.LLMPolicy("gpt-6-luna", "low", ledger, send=FakeSend(*replies),
                         system_prompt="Play well.")


def test_choice_updates_notes_history_ledger_and_metadata(tmp_path):
    agent = policy(tmp_path, reply(1, notes="Jaw Worm hits hard."), reply(0))
    first = decision()
    assert agent.choose(first) == first.candidates[1]
    metadata = agent.choice_metadata(first.id)
    assert metadata["reason"] == "because" and metadata["notes"] == "Jaw Worm hits hard."
    assert "Choices:\n0: play Strike (1 attack) -> Jaw Worm [1]" in metadata["prompt"]
    body = agent.api.send.bodies[0]
    assert body["reasoning"] == {"effort": "low", "summary": "auto"} and body["store"] is False
    exchange = next(agent.api.drain_exchanges())
    assert exchange["prompt"] == metadata["prompt"]
    assert exchange["attempts"][0]["request"] == body and "output" in exchange["attempts"][0]
    assert body["text"]["format"]["strict"] is True
    agent.choose(decision())
    second_prompt = agent.api.send.bodies[1]["input"][0]["content"]
    assert "Run notes:\nJaw Worm hits hard." in second_prompt
    assert "floor 3: play Defend (1 skill) (because)" in second_prompt
    assert agent.totals["calls"] == 2 and agent.totals["reasoning_tokens"] == 300
    lines = (tmp_path / "spend.jsonl").read_text().splitlines()
    assert [json.loads(line)["response_id"] for line in lines] == ["resp-1", "resp-2"]
    assert Ledger(tmp_path / "spend.jsonl", 1.0).spent == pytest.approx(agent.totals["usd"])


def test_invalid_replies_are_retried_then_fail_as_policy_failure(tmp_path):
    agent = policy(tmp_path, "not json", reply(99), reply(2))
    assert agent.choose(decision()).command == "potion use 0 1"
    attempts = agent._metadata["attempts"]
    assert [bool(a.get("error")) for a in attempts] == [True, True, False]
    assert "previous reply was invalid" in agent.api.send.bodies[2]["input"][0]["content"]
    failing = policy(tmp_path, reply(-1), reply(-1), reply(-1))
    with pytest.raises(PolicyFailure) as error:
        failing.choose(decision())
    assert len(error.value.failure["attempts"]) == 3


def test_budget_refuses_a_call_before_sending(tmp_path):
    agent = policy(tmp_path, reply(0), budget=0.0001)
    with pytest.raises(BudgetExhausted):
        agent.choose(decision())
    assert agent.api.send.bodies == []
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
    text = llm.render_state(decisions.decision_from_message(raw, session_id="s",
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


def test_combat_rendering_names_the_room_and_omits_an_empty_selection():
    raw = combat_message()
    raw["game_state"].update(room_type="MonsterRoomBoss", act_boss="Slime Boss")
    observation = decisions.decision_from_message(raw, session_id="s", sequence=1).observation
    text = llm.render_state(dict(observation))
    assert text.startswith("Act 1, floor 3. Act boss: Slime Boss, on floor 16. HP 70/80,")
    assert "Combat (boss), turn 2." in text
    grid = message(["confirm"], screen_type="GRID", screen_state={
        "confirm_up": True, "for_upgrade": True, "num_cards": 1, "selected_cards": []})
    observation = decisions.decision_from_message(grid, session_id="s", sequence=1).observation
    assert "Choose 1 card(s) to upgrade.\n" in llm.render_state(dict(observation)) + "\n"


def test_rules_notes_appear_only_for_present_noted_enemies():
    raw = combat_message()
    raw["game_state"]["combat_state"]["monsters"][1].update(id="SlimeBoss", name="Slime Boss")
    raw["game_state"]["combat_state"]["player"]["powers"] = [
        {"id": "Corruption", "name": "Corruption", "amount": -1}]
    observation = decisions.decision_from_message(raw, session_id="s", sequence=1).observation
    notes = {"SlimeBoss": "It splits at half HP.", "FuzzyLouseNormal": "Gone, so omitted."}
    text = llm.render_state(dict(observation), notes)
    assert "Enemy rules:\n  Slime Boss: It splits at half HP." in text
    assert "Gone, so omitted." not in text and "powers: Corruption\n" in text
    assert set(json.loads(llm.MONSTER_NOTES_PATH.read_text())) >= {
        "Lagavulin", "SlimeBoss", "AcidSlime_L", "SpikeSlime_L"}


def test_skipped_card_rewards_are_named_on_that_floors_reward_screens(tmp_path):
    offer = message(["choose", "skip"], screen_type="CARD_REWARD", choice_list=["cleave"],
                    screen_state={"cards": [card("Cleave")]})
    rewards = message(["choose", "proceed"], screen_type="COMBAT_REWARD", choice_list=["card"],
                      screen_state={"rewards": [{"reward_type": "CARD"}]})
    agent = policy(tmp_path, reply(1), reply(0), reply(1), reply(0))
    for sequence, raw in enumerate([offer, rewards, offer, rewards]):
        agent.choose(decisions.decision_from_message(raw, session_id="s", sequence=sequence))
    prompts = [body["input"][0]["content"] for body in agent.api.send.bodies]
    line = "Card rewards you skipped on this floor (reopening one shows the same cards): "
    assert line not in prompts[0]
    assert prompts[1].count(line + "Cleave (1 attack)\n") == 1
    assert line + "Cleave (1 attack)\n" in prompts[3]
    rewards["game_state"]["floor"] = 4
    later = decisions.decision_from_message(rewards, session_id="s", sequence=5)
    assert agent._reminders(later.observation) == []


def test_cards_show_the_ethereal_and_exhaust_keywords():
    ghost = {**card("Ghostly", "Apparition", kind="SKILL", target=False),
             "ethereal": True, "exhausts": True}
    raw = combat_message(hand=[ghost, card("Strike_R", "Strike")], exhaust_pile=[ghost])
    observation = decisions.decision_from_message(raw, session_id="s", sequence=1).observation
    text = llm.render_state(dict(observation))
    assert "Hand: Apparition (1 skill, ethereal, exhausts), Strike (1 attack)\n" in text
    assert "Exhaust pile (1): Apparition (1 skill, ethereal, exhausts)" in text


def hand_select(turn, relics=()):
    raw = combat_message(turn=turn)
    raw["available_commands"] = ["choose", "confirm"]
    raw["game_state"].update(
        screen_type="HAND_SELECT", choice_list=["strike", "defend"],
        relics=[{"id": name, "name": name, "counter": -1} for name in relics],
        screen_state={"hand": [card("Strike_R", "Strike"), card("Defend_R", "Defend")],
                      "max_cards": 99, "selected": [], "can_pick_zero": True})
    return raw


def test_hand_selections_name_their_source():
    agent = llm.LLMPolicy("gpt-6-luna", "low", None, send=FakeSend(),
                          system_prompt="Play well.")

    def reminders(raw):
        observation = decisions.decision_from_message(raw, session_id="s", sequence=1).observation
        return agent._reminders(observation)

    assert reminders(hand_select(1, ["Gambling Chip"])) == [
        "This selection is Gambling Chip's: the chosen cards are discarded, then you draw "
        "that many."]
    assert reminders(hand_select(2, ["Gambling Chip"])) == []
    agent.last_action = (3, 2, "play Armaments (1 skill)")
    assert reminders(hand_select(2)) == [
        "This selection is for Armaments (1 skill), which you just played."]
    assert reminders(hand_select(3)) == []
    agent.last_action = (3, 1, "use potion Gambler's Brew")
    assert reminders(hand_select(1, ["Gambling Chip"])) == [
        "This selection is for the potion Gambler's Brew, which you just used."]


def test_the_last_action_skips_hand_selections_and_keeps_floor_and_turn(tmp_path):
    agent = policy(tmp_path, reply(1), reply(0))
    agent.choose(decision())
    assert agent.last_action == (3, 2, "play Defend (1 skill)")
    agent.choose(decisions.decision_from_message(hand_select(2), session_id="s", sequence=2))
    assert agent.last_action == (3, 2, "play Defend (1 skill)")
    prompt = agent.api.send.bodies[1]["input"][0]["content"]
    assert ("Selected: none\nThis selection is for Defend (1 skill), which you just played."
            in prompt)
