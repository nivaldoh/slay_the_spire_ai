"""benchmark.benchmark_outcome (version 1) on episodes that play.play_episode writes against a
fake mailbox, one per row of benchmark.md's outcome table. Until 2026-11-15 each case also
checked the tactic cards' own outcome rule, deleted with their module (owner: "Delete all of
it"; tag wh3-legacy-20261115)."""
import json

import pytest
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError
from twwarhammer3.battle import benchmark, play, setup
from twwarhammer3.battle.scripted import Hold
from twwarhammer3.battle.team import TeamHarnessError

TIMER = {"expired": True, "source": "countdown_deadline"}


def _ending(result, timer=None):
    return [bridge_observation(0, 0), bridge_observation(1, 1000),
            {**bridge_observation(2, 2000, ack=True, result=result), "timer": timer}]


def _wrong_role():
    state = bridge_observation(2, 1000)
    state["mode"] = {"type": "settlement_standard", "role": "attacker"}
    return [bridge_observation(1, 0), state]


class _Bug(Hold):
    def decide(self, observation):
        raise ValueError("controller bug")


class _Late(Hold):
    def decide(self, observation):
        return [{"unit": "f1", "type": "halt"}]

    def acknowledge(self, ack, latency):
        raise ValueError("late bug")


class _CloseStops(Hold):
    def close(self):
        raise BudgetExhausted("a member's call ended with a stop")


class _CloseFails(Hold):
    def close(self):
        raise ValueError("cleanup bug")


class _Spent(Hold):
    def decide(self, observation):
        raise BudgetExhausted("ledger cap")


class _Provider(Hold):
    def metadata(self):  # outside decide, an APIError ends the battle
        raise APIError("openrouter returned a failed response r1")


def _broken():
    raise ValueError("bad prompt file")


def _no_team():
    raise TeamHarnessError("a team needs two members with distinct unit types")


class _Crashing(FakeMailbox):
    def wait_observation(self, **kwargs):
        raise RuntimeError("our own bug")


# (case, controller, mailbox, config change, scenario, benchmark outcome)
CASES = [
    ("contact win", Hold, lambda: FakeMailbox(_ending("won")), {}, None, "won"),
    ("timer win", Hold, lambda: FakeMailbox(_ending("won", TIMER)), {}, None, "won"),
    ("timer loss", Hold, lambda: FakeMailbox(_ending("lost", TIMER)), {}, None, "lost"),
    ("draw", Hold, lambda: FakeMailbox(_ending("draw")), {}, None, "draw"),
    ("error after the ending", _Late, lambda: FakeMailbox(_ending("won")), {}, None, "won"),
    ("stop at cleanup after the ending", _CloseStops, lambda: FakeMailbox(_ending("lost", TIMER)),
     {}, None, "lost"),
    ("controller bug in the battle", _Bug, lambda: FakeMailbox(_ending("won")), {}, None,
     "forfeit"),
    ("provider error ends the battle", _Provider, lambda: FakeMailbox(_ending("won")), {}, None,
     "unresolved"),
    ("not built", _broken, lambda: FakeMailbox(_ending("won")), {}, None, "not_built"),
    ("team refused at construction", _no_team, lambda: FakeMailbox(_ending("won")), {}, None,
     "setup_or_game_failure"),
    ("no battle starts", Hold, lambda: FakeMailbox([]), {}, None, "never_started"),
    ("game silent", Hold, lambda: FakeMailbox([bridge_observation(0, 0)]), {}, None,
     "unresolved"),
    ("wrong role", Hold, lambda: FakeMailbox(_wrong_role()), {}, "siege-kho5-dwf5",
     "setup_or_game_failure"),
    ("budget stop", _Spent, lambda: FakeMailbox(_ending("won")), {}, None, "unresolved"),
    ("wall cap", Hold, lambda: FakeMailbox(_ending("won")), {"episode_timeout": -1}, None,
     "unresolved"),
    ("wall cap, then a cleanup bug", _CloseFails, lambda: FakeMailbox(_ending("won")),
     {"episode_timeout": -1}, None, "unresolved"),
    ("our own exception", Hold, lambda: _Crashing(_ending("won")), {}, None, "unresolved"),
]


@pytest.mark.parametrize("case, make, mailbox, change, scenario, expected", CASES,
                         ids=[case[0] for case in CASES])
def test_each_ending_play_writes_gets_its_row(tmp_path, case, make, mailbox, change, scenario,
                                              expected):
    loaded = setup.load_scenario({"scenario": scenario}) if scenario else None
    play.play_episode(tmp_path / "e", {**CONFIG, **change}, make, mailbox(), not_battle=None,
                      scenario=loaded)
    result = json.loads((tmp_path / "e/result.json").read_text())
    assert benchmark.benchmark_outcome(result) == expected


@pytest.mark.parametrize("case, make, mailbox, change, scenario, expected", CASES,
                         ids=[case[0] for case in CASES])
def test_only_an_engine_label_counts_in_a_win_rate(tmp_path, case, make, mailbox, change,
                                                   scenario, expected):
    """benchmark.md, Outcome and score: an attempt has an outcome only when the engine ended it;
    the owner on the unresolved rows, 2026-11-15: "Unresolved battles can be kept out of the
    counts". Wrong version: evaluate reads a forfeit or an unresolved stop as a loss."""
    loaded = setup.load_scenario({"scenario": scenario}) if scenario else None
    play.play_episode(tmp_path / "e", {**CONFIG, **change}, make, mailbox(), not_battle=None,
                      scenario=loaded)
    result = json.loads((tmp_path / "e/result.json").read_text())
    counted = expected if expected in ("won", "lost", "draw") else None
    assert benchmark.evaluate(result)["outcome"] == counted


def test_a_trial_stopped_during_its_final_copying_is_an_operator_stop_whatever_the_engine_said():
    """Owner, 2026-11-13: "interrupted, readers skip it (Recommended)". Wrong version: the label
    keeps the engine's win while evaluate skips the trial, so the two disagree."""
    result = {"status": "interrupted", "battle": "b", "engine_ending": {"result": "won"},
              "interrupted_copy": "imagery"}
    assert benchmark.benchmark_outcome(result) == "operator_stop"
    assert benchmark.benchmark_outcome({**result, "interrupted_copy": None}) == "won"


class _StoppedLate(Hold):
    def decide(self, observation):
        return [{"unit": "f1", "type": "halt"}]

    def acknowledge(self, ack, latency):
        raise KeyboardInterrupt


class _Stopped(Hold):
    def decide(self, observation):
        raise KeyboardInterrupt


@pytest.mark.parametrize("make, expected", [(_Stopped, "operator_stop"), (_StoppedLate, "won")])
def test_an_operator_stop_is_shown_apart_unless_the_engine_had_ended(tmp_path, make, expected):
    with pytest.raises(KeyboardInterrupt):
        play.play_episode(tmp_path / "e", CONFIG, make, FakeMailbox(_ending("won")),
                          not_battle=None)
    result = json.loads((tmp_path / "e/result.json").read_text())
    assert result["status"] == "interrupted"
    assert benchmark.benchmark_outcome(result) == expected


def test_no_result_never_started_and_old_key_or_credit_failures_are_unresolved():
    assert benchmark.benchmark_outcome(None) == "never_started"
    assert benchmark.benchmark_outcome({"status": "missing_result"}) == "never_started"  # report's
    # Key and credit failures from before b35, which a policy failure carried: still to settle.
    for code in (401, 402):
        assert benchmark.benchmark_outcome({"status": "policy_failure", "battle": "b", "error":
                                        f"decide: APIError: HTTP {code}: no"}) == "unresolved"


def test_a_record_from_before_the_kept_ending_is_read_by_its_status():
    # Before b47 (2026-10-21) result.json had no engine_ending: all 3 register timer wins.
    for status in ("won", "lost", "draw"):
        assert benchmark.benchmark_outcome({"status": status, "ended_by": "time_limit",
                                        "battle": "b"}) == status
