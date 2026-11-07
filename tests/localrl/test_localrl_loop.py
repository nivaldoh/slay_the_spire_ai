"""Rewards, the loop-breaking mask and the agent's boundary for the local RL loop."""

import inspect
import json
import math

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from spire.decisions import Choice  # noqa: E402
from spire.localrl import collect, learn, research  # noqa: E402
from spire.localrl import policy as policy_module  # noqa: E402
from spire.localrl.link import Link  # noqa: E402
from spire.localrl.policy import LocalPolicy, playable  # noqa: E402
from spire.localrl.train import read_offline  # noqa: E402
from spire.protocol import Decision, ProtocolError  # noqa: E402

CONFIG = {"hp_weight": 2.0, "win_bonus": 10.0, "gamma": 0.5, "lam": 1.0}


def step(floor, hp, top=80):
    return {"observation": {"floor": floor, "hp": hp, "max_hp": top}}


def test_rewards_count_floors_and_shape_hp_with_the_discount():
    steps = [step(1, 80), step(1, 40), step(2, 40)]
    values = learn.rewards(steps, "lost", 2, CONFIG)
    assert values == pytest.approx([2.0 * (0.25 - 1.0), 1.0 + 2.0 * (0.25 - 0.5), 2.0 * -0.5])


def test_shaping_sums_to_the_start_potential_whatever_the_path():
    """The Ng, Harada and Russell property: the discounted shaping depends only on the start."""
    config = {**CONFIG, "gamma": 0.9, "win_bonus": 0.0}
    for path in ([80, 10, 70, 30], [80, 80, 80, 80], [80, 5, 5, 60]):
        steps = [step(1, hp) for hp in path]
        values = learn.rewards(steps, "lost", 1, config)
        assert learn.discounted(values, 0.9)[0] == pytest.approx(-2.0)


def test_a_win_ends_at_zero_potential_and_keeps_its_floor_and_bonus():
    assert learn.rewards([step(50, 40)], "won", 51, CONFIG) == pytest.approx([1.0 + 10.0 - 1.0])


def test_advantages_match_a_hand_calculation():
    # With lam 1 and terminal, GAE is the discounted return minus the estimate.
    values, estimates = [1.0, 2.0], [0.5, 0.25]
    expected = [1.0 + 0.5 * 2.0 - 0.5, 2.0 - 0.25]
    assert learn.advantages(values, estimates, CONFIG, terminal=True) == pytest.approx(expected)


def test_lambda_mixes_the_later_error():
    config = {**CONFIG, "lam": 0.5}
    first, second = 1.0 + 0.5 * 0.25 - 0.5, 2.0 - 0.25
    result = learn.advantages([1.0, 2.0], [0.5, 0.25], config, terminal=True)
    assert result == pytest.approx([first + 0.5 * 0.5 * second, second])


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


def test_run_level_screens_only_go_to_the_run_adapter():
    rest = {"screen_type": "REST"}
    assert policy_module.run_level(rest, ["discard potion X", "rest: heal", "smith: upgrade"])
    assert not policy_module.run_level(rest, ["discard potion X", "proceed"])  # leaving the site
    grid = {"screen_type": "GRID", "screen_state": {"for_upgrade": True}}
    assert policy_module.run_level(grid, ["select Bash (2 attack)", "cancel"])
    assert not policy_module.run_level(grid, ["confirm confirm"])  # the choice is already made
    transform = {"screen_type": "GRID", "screen_state": {"for_transform": True}}
    assert not policy_module.run_level(transform, ["select Bash (2 attack)"])
    assert not policy_module.run_level({"screen_type": "MAP"}, ["go to monster at x=1, y=2"])
    fought = {"screen_type": "COMBAT_REWARD"}
    assert policy_module.run_level(fought, ["take 11 gold", "proceed, leaving any remaining"])
    assert not policy_module.run_level(fought, ["proceed, leaving any remaining rewards"])


def test_a_routed_step_is_greedy_frozen_and_read_by_the_run_scorer(monkeypatch):
    monkeypatch.setattr("spire.localrl.policy.render", lambda observation, labels: "one")
    monkeypatch.setattr("spire.localrl.policy.lite", lambda observation: {})

    class Fixed:
        def __init__(self, best):
            self.best = best

        def encode(self, prompt):
            return [1]

        def logits(self, encoded, counts):
            return [torch.tensor([9.0 if i == self.best else 0.0 for i in range(counts[0])])]

    policy = LocalPolicy(Fixed(0), temperature=1.0, seed=1, run_scorer=Fixed(1))
    game = {"floor": 1, "act": 1, "current_hp": 10, "max_hp": 10, "gold": 0, "deck": [],
            "relics": [], "potions": [], "act_boss": "x", "screen_type": "REST",
            "screen_state": {}}
    rest = Decision("d", game, tuple(Choice(f"d:{i}", "d", label, label)
                                     for i, label in enumerate(["rest: heal", "smith: upgrade"])))
    assert policy.choose(rest).label == "smith: upgrade"
    assert policy.steps[-1]["frozen"] is True and policy.steps[-1]["log_prob"] == 0.0
    game = {**game, "screen_type": "MAP"}
    other = Decision("e", game, tuple(Choice(f"e:{i}", "e", label, label)
                                      for i, label in enumerate(["a", "b"])))
    policy.choose(other)
    assert policy.steps[-1]["frozen"] is False


def test_sampling_in_fights_only_keeps_other_screens_greedy(monkeypatch):
    monkeypatch.setattr("spire.localrl.policy.render", lambda observation, labels: "one")
    monkeypatch.setattr("spire.localrl.policy.lite", lambda observation: {})

    class Even:
        def encode(self, prompt):
            return [1]

        def logits(self, encoded, counts):
            return [torch.zeros(counts[0])]

    policy = LocalPolicy(Even(), temperature=1.0, seed=3, sample_fights_only=True)
    game = {"floor": 1, "act": 1, "current_hp": 10, "max_hp": 10, "gold": 0, "deck": [],
            "relics": [], "potions": [], "act_boss": "x", "screen_type": "MAP"}
    labels = ["a", "b", "c"]
    choices = tuple(Choice(f"d:{i}", "d", label, label) for i, label in enumerate(labels))
    policy.choose(Decision("d", game, choices))
    assert policy.steps[-1]["log_prob"] == 0.0  # the greedy path records no sampling
    policy.tried.clear()
    fight = {**game, "combat_state": {"turn": 1, "player": {}, "hand": [], "monsters": []}}
    monkeypatch.setattr("spire.localrl.policy.render", lambda observation, labels: "two")
    policy.choose(Decision("e", fight, tuple(Choice(f"e:{i}", "e", x, x)
                                             for i, x in enumerate(labels))))
    assert policy.steps[-1]["log_prob"] == pytest.approx(math.log(1 / 3))


def test_potion_exploration_fires_only_in_hard_fights(monkeypatch):
    monkeypatch.setattr("spire.localrl.policy.render", lambda observation, labels: "one")
    monkeypatch.setattr("spire.localrl.policy.lite", lambda observation: {})

    class NeverPotion:
        def encode(self, prompt):
            return [1]

        def logits(self, encoded, counts):
            return [torch.tensor([9.0] + [0.0] * (counts[0] - 1))]

    def fight(room, identity):
        game = {"floor": 1, "act": 1, "current_hp": 10, "max_hp": 10, "gold": 0, "deck": [],
                "relics": [], "potions": [], "act_boss": "x", "screen_type": "NONE",
                "room_type": room, "combat_state": {"turn": 1, "player": {}, "hand": [],
                                                    "monsters": []}}
        labels = ["play Strike", "use potion Fire Potion"]
        return Decision(identity, game, tuple(Choice(f"{identity}:{i}", identity, x, x)
                                              for i, x in enumerate(labels)))

    policy = LocalPolicy(NeverPotion(), temperature=0, seed=1, potion_explore=1.0)
    assert policy.choose(fight("MonsterRoomBoss", "a")).label == "use potion Fire Potion"
    assert policy.steps[-1]["explored"] is True
    policy.tried.clear()
    assert policy.choose(fight("MonsterRoom", "b")).label == "play Strike"
    assert policy.steps[-1]["explored"] is False


def test_a_decision_that_reached_no_state_leaves_the_learner():
    class Policy:
        steps = [{"prompt": "state", "index": 2}]
        tried = {collect.hashlib.sha256(b"state").hexdigest(): {2}}

    key = next(iter(Policy.tried))
    collect.forget_step(Policy, "play 1", forced=True, error=None)  # a forced move is no step
    collect.forget_step(Policy, "wait 60", forced=False, error=None)
    assert len(Policy.steps) == 1
    collect.forget_step(Policy, "play 1", forced=False, error=None)
    assert Policy.steps == [] and Policy.tried[key] == set()


def test_a_rejected_decision_stays_tried_so_it_is_not_offered_again():
    class Policy:
        steps = [{"prompt": "state", "index": 2}]
        tried = {collect.hashlib.sha256(b"state").hexdigest(): {2}}

    collect.forget_step(Policy, "choose 2", forced=False, error="Index out of bounds")
    assert Policy.steps == [] and list(Policy.tried.values()) == [{2}]


def test_a_potion_cannot_be_taken_with_every_slot_full():
    labels = ["take potion Blood Potion", "take 12 gold", "proceed, leaving any remaining rewards"]
    full = {"potions": [{"id": "BloodPotion"}, {"id": "Regen Potion"}]}
    room = {"potions": [{"id": "BloodPotion"}, {"id": "Potion Slot"}]}
    assert playable(full, labels) == [1, 2]
    assert playable(room, labels) == [0, 1, 2]
    assert playable(full, ["take potion Blood Potion"]) == [0]


def test_a_potion_cannot_be_bought_with_every_slot_full():
    labels = ["buy Armaments (1 skill) for 23 gold", "buy Fire Potion for 50 gold", "leave"]
    potions = [{"name": "Fire Potion"}]
    full = {"potions": [{"id": "A"}, {"id": "B"}], "screen_state": {"potions": potions}}
    room = {"potions": [{"id": "A"}, {"id": "Potion Slot"}], "screen_state": {"potions": potions}}
    assert playable(full, labels) == [0, 2]
    assert playable(room, labels) == [0, 1, 2]


def test_agent_cannot_reach_protected_values_or_leave_a_range():
    current = {"updates": 2, "runs_per_update": 6, "method": "ppo"}
    reply = json.dumps({"hypothesis": "h", "reasoning": "r", "config_json": '{"lr": 1e-5}'})
    assert research.parse_reply(reply, current)["changes"] == {"lr": 1e-5}
    bad = ('{"eval_seeds": []}', '{"win_bonus": 99}', '{"hp_weight": 1}', '{"lr": 1}',
           '{"updates": 1.5}',
           '{"updates": 4, "runs_per_update": 10}', '[]', 'null', '3', '{"updates": Infinity}')
    for changes in bad:
        text = json.dumps({"hypothesis": "h", "reasoning": "r", "config_json": changes})
        with pytest.raises(ValueError):
            research.parse_reply(text, current)


def test_integer_values_arrive_as_integers():
    assert research.validate({"epochs": 2.0, "awr_rows": 2e3}) == {"epochs": 2, "awr_rows": 2000}
    assert type(research.validate({"epochs": 2.0})["epochs"]) is int


def test_a_restart_does_not_relabel_old_floors_with_the_current_card_pool():
    source = inspect.getsource(research.main)
    assert source.count('state["card_pool"] = card_pool()') == 2
    assert source.index('state["card_pool"] = card_pool()') > source.index(
        'if not state["incumbent_evaluation"]:')


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


class FakeGame:
    speed = None
    runs = 0

    def __init__(self, fail_menu=False):
        self.restarts, self.fail_menu = 0, fail_menu
        self.link = self

    def restart(self):
        self.restarts += 1

    def to_menu(self):
        if self.fail_menu:
            raise ProtocolError("menu lost")


def fake_run(outcomes, calls):
    def run(directory, seed, policy, link):
        directory.mkdir()
        calls.append(seed)
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        (directory / "result.json").write_text(json.dumps({"status": outcome}))
        return {"status": outcome, "seed": seed, "floor": 3}
    return run


def test_a_finished_run_survives_a_lost_menu_and_is_not_replayed(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(collect, "one_run", fake_run(["lost", "lost"], calls))
    monkeypatch.setattr(collect, "revision", dict)
    game = FakeGame(fail_menu=True)
    results = collect.play_seeds(game, tmp_path, ["A", "B"], None, temperature=1.0, label="t")
    assert calls == ["A", "B"] and [r["seed"] for r in results] == ["A", "B"]
    assert game.restarts == 2
    assert len(list(tmp_path.glob("run-*/steps.jsonl"))) == 2


def test_a_lost_link_replays_the_seed_and_leaves_no_steps_behind(tmp_path, monkeypatch):
    calls = []
    outcomes = [OSError("link"), "lost"]
    monkeypatch.setattr(collect, "one_run", fake_run(outcomes, calls))
    monkeypatch.setattr(collect, "revision", dict)
    game = FakeGame()
    results = collect.play_seeds(game, tmp_path, ["A"], None, temperature=1.0, label="t")
    assert calls == ["A", "A"] and len(results) == 1 and game.restarts == 1
    assert [path.parent.name for path in tmp_path.glob("run-*/steps.jsonl")] == ["run-0000-1"]


def test_a_truncated_run_needs_a_new_jvm(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "one_run", fake_run(["truncated"], []))
    monkeypatch.setattr(collect, "revision", dict)
    game = FakeGame()
    collect.play_seeds(game, tmp_path, ["A"], None, temperature=1.0, label="t")
    assert game.restarts == 1


def test_a_failed_offline_run_bootstraps_instead_of_dying(tmp_path):
    row = {"group": "G", "status": "infrastructure_failure", "final_floor": 3, "count": 2}
    path = tmp_path / "rows.jsonl"
    path.write_text(json.dumps(row) + "\n")
    assert read_offline(path)[0]["status"] == "truncated"
