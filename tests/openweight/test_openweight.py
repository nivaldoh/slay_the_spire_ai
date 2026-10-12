"""The open-weight skeleton's working pieces; everything else raises NotImplementedError."""

import pytest

from spire.fullrun.decisions import Choice
from spire.openweight.env import Step
from spire.openweight.evaluate import wilson_interval
from spire.openweight.grpo import group_advantages
from spire.openweight.rewards import fight_reward, run_reward
from spire.openweight.rollout import run_episode
from spire.openweight.tasks import Split, Stage, Task, check_splits
from spire.protocol import Decision, PolicyFailure

TASK = Task("fight-a", Stage.FIGHT, Split.TRAIN, "SEEDA")


def decision(sequence):
    decision_id = f"s:{sequence}"
    return Decision(decision_id, {"floor": 1}, (Choice(f"{decision_id}:0", decision_id, "end",
                                                       "end turn"),))


class FakeEnv:
    def __init__(self, length):
        self.length, self.sequence = length, 0

    def reset(self, task):
        return decision(0)

    def step(self, choice):
        self.sequence += 1
        if self.sequence == self.length:
            return Step(None, "won", {"current_hp": 50})
        return Step(decision(self.sequence))


class FirstChoice:
    def __init__(self, fail=False):
        self.fail = fail

    def choose(self, decision):
        if self.fail:
            raise PolicyFailure("bad reply", failure={})
        return decision.candidates[0]

    def choice_metadata(self, decision_id):
        return {"decision_id": decision_id}


def test_any_win_beats_any_loss_and_infrastructure_is_not_scored():
    assert fight_reward("won", 1, 80) > fight_reward("lost", 80, 80) == 0.0
    assert fight_reward("won", 80, 80) > fight_reward("won", 40, 80)
    assert run_reward("won") == 1.0 and run_reward("truncated") == 0.0
    with pytest.raises(ValueError):
        fight_reward("interrupted", 80, 80)


def test_group_advantages_center_rewards_and_skip_ties():
    advantages = group_advantages([0.0, 1.0, 1.5, 1.5])
    assert sum(advantages) == pytest.approx(0.0)
    assert advantages[0] < advantages[1] < advantages[2] == advantages[3]
    assert group_advantages([1.0, 1.0]) == [0.0, 0.0]


def test_a_seed_belongs_to_one_split():
    check_splits([TASK, Task("fight-b", Stage.ACT1, Split.TRAIN, "SEEDA")])
    with pytest.raises(ValueError, match="SEEDA"):
        check_splits([TASK, Task("test-a", Stage.FIGHT, Split.TEST, "SEEDA")])


def test_wilson_interval_contains_the_rate():
    assert wilson_interval(0, 12)[0] == 0.0
    low, high = wilson_interval(6, 12)
    assert low < 0.5 < high


def test_episode_records_steps_until_the_outcome():
    episode = run_episode(FakeEnv(3), TASK, FirstChoice(), max_actions=10)
    assert episode.outcome == "won" and episode.summary == {"current_hp": 50}
    assert [step["policy"]["decision_id"] for step in episode.steps] == ["s:0", "s:1", "s:2"]
    assert episode.steps[0]["next_observation"] == {"floor": 1}
    assert episode.steps[-1]["next_observation"] is None


def test_episode_truncates_and_scores_policy_failures():
    assert run_episode(FakeEnv(5), TASK, FirstChoice(), max_actions=2).outcome == "truncated"
    failed = run_episode(FakeEnv(5), TASK, FirstChoice(fail=True), max_actions=2)
    assert failed.outcome == "policy_failure" and failed.steps == []
