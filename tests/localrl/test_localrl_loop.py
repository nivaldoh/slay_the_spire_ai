"""Rewards, the loop-breaking mask and the agent's boundary for the local RL loop."""

import json
import math

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from spire.decisions import Choice  # noqa: E402
from spire.localrl import learn, research  # noqa: E402
from spire.localrl.collect import Link  # noqa: E402
from spire.localrl.policy import LocalPolicy  # noqa: E402
from spire.protocol import Decision, ProtocolError  # noqa: E402

CONFIG = {"hp_weight": 2.0, "win_bonus": 10.0, "gamma": 0.5, "lam": 1.0}


def step(floor, hp, top=80):
    return {"observation": {"floor": floor, "hp": hp, "max_hp": top}}


def test_rewards_count_floors_and_hp_and_death_loses_the_potential():
    steps = [step(1, 80), step(1, 40), step(2, 40)]
    values = learn.rewards(steps, "lost", 2, CONFIG)
    assert values == pytest.approx([2.0 * -0.5, 1.0, 2.0 * -0.5])


def test_win_bonus_and_a_floor_gained_on_the_last_step():
    values = learn.rewards([step(50, 40)], "won", 51, CONFIG)
    assert values == pytest.approx([11.0])


def test_advantages_match_a_hand_calculation():
    # With lam 1 and terminal, GAE is the discounted return minus the estimate.
    values, estimates = [1.0, 2.0], [0.5, 0.25]
    expected = [1.0 + 0.5 * 2.0 - 0.5, 2.0 - 0.25]
    assert learn.advantages(values, estimates, CONFIG, terminal=True) == pytest.approx(expected)


def test_truncated_run_bootstraps_from_its_last_estimate():
    result = learn.advantages([1.0], [4.0], CONFIG, terminal=False)
    assert result == pytest.approx([1.0 + 0.5 * 4.0 - 4.0])


def decision(identity, labels):
    observation = {"floor": 1, "act": 1, "current_hp": 10, "max_hp": 10, "gold": 0, "deck": [],
                   "relics": [], "potions": [], "act_boss": "x", "screen_type": "MAP"}
    return Decision(identity, observation, tuple(
        Choice(f"{identity}:{i}", identity, label, label) for i, label in enumerate(labels)))


def test_a_repeated_state_never_repeats_its_choice_until_all_are_tried(monkeypatch):
    monkeypatch.setattr("spire.localrl.policy.render", lambda observation, labels: "same")
    monkeypatch.setattr("spire.localrl.policy.lite", lambda observation: {})
    policy = LocalPolicy(None, temperature=1.0, seed=1)
    chosen = [policy.choose(decision(f"d{i}", ["a", "b", "c"])).label for i in range(3)]
    assert sorted(chosen) == ["a", "b", "c"]
    assert policy.choose(decision("d3", ["a", "b", "c"])).label in {"a", "b", "c"}


def test_agent_cannot_reach_protected_values_or_leave_a_range():
    current = {"updates": 2, "runs_per_update": 6, "method": "ppo"}
    reply = json.dumps({"hypothesis": "h", "reasoning": "r", "config_json": '{"lr": 1e-5}'})
    assert research.parse_reply(reply, current)["changes"] == {"lr": 1e-5}
    bad = ('{"eval_seeds": []}', '{"win_bonus": 99}', '{"lr": 1}', '{"updates": 1.5}',
           '{"updates": 4, "runs_per_update": 10}')
    for changes in bad:
        text = json.dumps({"hypothesis": "h", "reasoning": "r", "config_json": changes})
        with pytest.raises(ValueError):
            research.parse_reply(text, current)


def test_gate_keeps_a_paired_gain_and_rejects_a_mixed_one():
    base = {"a": 5, "b": 5, "c": 5, "d": 5}
    assert research.compare({"a": 6, "b": 6, "c": 5, "d": 5}, base)["keep"]
    assert not research.compare({"a": 9, "b": 4, "c": 4, "d": 5}, base)["keep"]
    assert not research.compare(base, base)["keep"]
    assert math.isclose(research.compare({"a": 6, "b": 5, "c": 5, "d": 5}, base)["mean_gain"], 0.25)


class FakeBridge:
    def __init__(self, messages):
        self.messages, self.sent = list(messages), []

    def receive(self):
        return self.messages.pop(0)

    def send(self, command):
        self.sent.append(command)


def test_link_leaves_the_death_screen_and_replays_the_menu_message_for_the_next_run():
    menu = {"ready_for_command": True, "in_game": False}
    bridge = FakeBridge([
        {"ready_for_command": False},
        {"ready_for_command": True, "in_game": True, "available_commands": ["proceed"]},
        menu,
    ])
    link = Link(bridge)
    link.to_menu()
    assert bridge.sent == ["proceed", "proceed"]
    assert link.receive() is menu
    bridge.messages.append({"next": True})
    assert link.receive() == {"next": True}


def test_link_refuses_a_screen_it_cannot_leave():
    bridge = FakeBridge([{"ready_for_command": True, "in_game": True, "available_commands": []}])
    with pytest.raises(ProtocolError):
        Link(bridge).to_menu()
