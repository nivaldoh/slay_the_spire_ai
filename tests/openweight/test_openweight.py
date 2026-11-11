"""The open-weight skeleton's working pieces; everything else raises NotImplementedError."""

import json

import pytest

from spire.decisions import Choice
from spire.engine.bridge import BridgeError
from spire.openweight.env import EpisodeFailed, RealGame, Step
from spire.openweight.evaluate import wilson_interval
from spire.openweight.grpo import group_advantages
from spire.openweight.rewards import fight_reward, run_reward
from spire.openweight.rollout import run_episode, run_group
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


def _decision(sequence, floor=1):
    observation = {"act": 1, "floor": floor, "current_hp": 70, "max_hp": 80, "gold": 99}
    choices = tuple(Choice(f"d{sequence}:{i}", f"d{sequence}", f"choose {i}", f"option {i}")
                    for i in range(2))
    return Decision(f"d{sequence}", observation, choices)


def _fake_run(monkeypatch, plays, result):
    """A stand-in for play_run that asks ``plays`` questions and then reports ``result``."""
    def play_run(directory, config, policy):
        seen.update(config=config, directory=directory)
        for index in range(plays):
            choice = policy.choose(_decision(index, floor=index + 1))
            seen.setdefault("commands", []).append(choice.command)
        if isinstance(result, Exception):
            raise result
        return result
    seen = {}
    monkeypatch.setattr("spire.fullrun.play.play_run", play_run)
    return seen


@pytest.fixture(autouse=True)
def committed_tree(monkeypatch):
    monkeypatch.setattr("spire.openweight.env.committed_revision", lambda *_: "abc123")
    monkeypatch.setattr("spire.openweight.env.source_fingerprints", lambda *_: {"a.py": "1"})


def _task(**fields):
    return Task(**{"id": "t", "stage": Stage.FULL_RUN, "split": Split.TRAIN, "game_seed": "ABC",
                   **fields})


def test_real_game_turns_a_run_into_reset_and_step(monkeypatch, tmp_path):
    result = {"status": "lost", "act": 1, "floor": 2, "current_hp": 0, "max_hp": 80, "gold": 5}
    seen = _fake_run(monkeypatch, 2, result)
    env = RealGame(tmp_path)
    first = env.reset(_task())
    middle = env.step(first.candidates[1])
    assert middle.decision.id == "d1" and middle.outcome is None and middle.summary["floor"] == 2
    last = env.step(middle.decision.candidates[0])
    assert last.decision is None and last.outcome == "lost" and last.summary["current_hp"] == 0
    assert seen["commands"] == ["choose 1", "choose 0"] and seen["config"]["seed"] == "ABC"
    env.close()


def test_a_failed_run_is_never_an_outcome(monkeypatch, tmp_path):
    _fake_run(monkeypatch, 1, {"status": "infrastructure_failure", "error": "bridge"})
    env = RealGame(tmp_path)
    decision = env.reset(_task())
    with pytest.raises(EpisodeFailed, match="bridge"):
        env.step(decision.candidates[0])


def test_an_exception_in_the_run_reaches_the_caller(monkeypatch, tmp_path):
    _fake_run(monkeypatch, 0, OSError("lost the pipe"))
    with pytest.raises(EpisodeFailed, match="lost the pipe"):
        RealGame(tmp_path).reset(_task())


def test_close_ends_an_unfinished_run(monkeypatch, tmp_path):
    def play_run(directory, config, policy):
        with pytest.raises(BridgeError):
            policy.choose(_decision(0))
        ended.append(True)
        return {"status": "policy_failure"}
    ended = []
    monkeypatch.setattr("spire.fullrun.play.play_run", play_run)
    env = RealGame(tmp_path)
    env.reset(_task())
    env.close()
    assert ended == [True]


def test_reset_ends_the_unfinished_run_first(monkeypatch, tmp_path):
    def play_run(directory, config, policy):
        running.append(directory)
        try:
            policy.choose(_decision(0))
        except BridgeError:
            ended.append(directory)
            running.remove(directory)
        return {"status": "policy_failure"}
    running, ended = [], []
    monkeypatch.setattr("spire.fullrun.play.play_run", play_run)
    env = RealGame(tmp_path)
    env.reset(_task())
    first = running[0]
    env.reset(_task())
    assert ended == [first] and len(running) == 1
    env.close()


def test_a_new_reset_gets_a_new_directory(monkeypatch, tmp_path):
    seen = _fake_run(monkeypatch, 1, {"status": "lost"})
    env = RealGame(tmp_path)
    env.reset(_task())
    first = seen["directory"]
    env.reset(_task())
    env.close()
    assert seen["directory"] != first


@pytest.mark.parametrize("fields", [{"start": "a-prefix"}, {"stage": Stage.FIGHT}])
def test_starts_the_game_cannot_do_are_refused(tmp_path, fields):
    with pytest.raises(ValueError):
        RealGame(tmp_path).reset(_task(**fields))


def test_run_episode_plays_through_real_game(monkeypatch, tmp_path):
    _fake_run(monkeypatch, 3, {"status": "won", "floor": 3})

    class First:
        def choose(self, decision):
            return decision.candidates[0]

        def choice_metadata(self, decision_id):
            return {}

    env = RealGame(tmp_path)
    episode = run_episode(env, _task(), First(), max_actions=10)
    assert episode.outcome == "won" and len(episode.steps) == 3


@pytest.mark.parametrize("close_first", [False, True])
def test_step_after_the_end_raises_instead_of_hanging(monkeypatch, tmp_path, close_first):
    _fake_run(monkeypatch, 1, {"status": "lost"})
    env = RealGame(tmp_path)
    decision = env.reset(_task())
    env.step(decision.candidates[0])
    if close_first:
        env.close()
    with pytest.raises(RuntimeError, match="no live episode"):
        env.step(decision.candidates[0])


def test_step_after_a_failed_reset_raises(monkeypatch, tmp_path):
    _fake_run(monkeypatch, 0, OSError("no game"))
    env = RealGame(tmp_path)
    with pytest.raises(EpisodeFailed):
        env.reset(_task())
    with pytest.raises(RuntimeError, match="no live episode"):
        env.step(_decision(0).candidates[0])


def test_a_new_environment_on_the_same_directory_keeps_earlier_runs(monkeypatch, tmp_path):
    seen = _fake_run(monkeypatch, 1, {"status": "lost"})
    first = RealGame(tmp_path)
    first.reset(_task())
    first.close()
    seen["directory"].mkdir()
    made = seen["directory"]
    second = RealGame(tmp_path)
    second.reset(_task())
    second.close()
    assert seen["directory"] != made


def test_one_failed_attempt_leaves_the_group_and_the_rest_still_play(monkeypatch, tmp_path):
    attempts = []

    def play_run(directory, config, policy):
        attempts.append(directory)
        if len(attempts) == 2:
            return {"status": "infrastructure_failure", "error": "relay"}
        policy.choose(_decision(0))
        return {"status": "lost"}

    class First:
        def choose(self, decision):
            return decision.candidates[0]

        def choice_metadata(self, decision_id):
            return {}

    monkeypatch.setattr("spire.fullrun.play.play_run", play_run)
    episodes = run_group(lambda: RealGame(tmp_path), _task(), First, 3, max_actions=10)
    assert len(attempts) == 3 and [e.outcome for e in episodes] == ["lost", "lost"]


def test_a_real_game_job_records_its_source(monkeypatch, tmp_path):
    _fake_run(monkeypatch, 1, {"status": "lost"})
    env = RealGame(tmp_path / "job", max_actions=7)
    env.reset(_task())
    env.close()
    manifest = json.loads((tmp_path / "job" / "manifest.json").read_text())
    assert manifest["source_revision"] == "abc123" and manifest["source_files"] == {"a.py": "1"}
    assert manifest["config"]["max_actions"] == 7 and manifest["engine"] == "original"


def test_source_that_changed_during_a_job_is_refused(monkeypatch, tmp_path):
    _fake_run(monkeypatch, 1, {"status": "lost"})
    first = RealGame(tmp_path)
    first.reset(_task())
    first.close()
    monkeypatch.setattr("spire.openweight.env.source_fingerprints", lambda *_: {"a.py": "2"})
    with pytest.raises(EpisodeFailed, match="Source changed"):
        RealGame(tmp_path).reset(_task())
