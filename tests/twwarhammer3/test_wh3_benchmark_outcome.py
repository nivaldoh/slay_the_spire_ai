"""benchmark.benchmark_outcome (version 2) on episodes that play.play_episode writes against a
fake mailbox, one per row of benchmark.md's outcome table. Until 2026-11-15 each case also
checked the tactic cards' own outcome rule, deleted with their module (owner: "Delete all of
it"; tag wh3-legacy-20261115)."""
import json

import pytest
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError
from twwarhammer3.battle import play, setup
from twwarhammer3.benchmarks import profile as benchmark
from twwarhammer3.controllers.scripted import Hold
from twwarhammer3.controllers.team import TeamHarnessError

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


def _played(tmp_path, make, mailbox, change, scenario):
    loaded = setup.load_scenario({"scenario": scenario}) if scenario else None
    play.play_episode(tmp_path / "e", {**CONFIG, **change}, make, mailbox(), not_battle=None,
                      scenario=loaded)
    return json.loads((tmp_path / "e/result.json").read_text())


SETTLED = [case for case in CASES if case[5] in ("won", "lost", "draw", "unresolved")]
UNSETTLED = [case for case in CASES if case not in SETTLED]


@pytest.mark.parametrize("case, make, mailbox, change, scenario, expected", SETTLED,
                         ids=[case[0] for case in SETTLED])
def test_an_engine_ending_counts_and_an_unresolved_stop_does_not(tmp_path, case, make, mailbox,
                                                                 change, scenario, expected):
    """benchmark.md, Outcome and score: the engine's won, lost or draw is the outcome; the owner
    on the unresolved rows, 2026-11-15: "Unresolved battles can be kept out of the counts".
    Wrong version: evaluate reads an unresolved stop as a loss."""
    result = _played(tmp_path, make, mailbox, change, scenario)
    counted = expected if expected in ("won", "lost", "draw") else None
    assert benchmark.evaluate(result)["outcome"] == counted


@pytest.mark.parametrize("case, make, mailbox, change, scenario, expected", UNSETTLED,
                         ids=[case[0] for case in UNSETTLED])
def test_the_other_labels_have_no_outcome_as_before(tmp_path, case, make, mailbox, change,
                                                    scenario, expected):
    """Not a rule the owner has settled. A forfeit, a controller that cannot be built, a setup
    or game failure and a battle that never started had no outcome in evaluate before
    2026-11-15 and have none now. benchmark.md calls a forfeit "not a win" and leaves its
    denominator open; if the owner counts it as a non-win, this test changes with that rule."""
    assert benchmark.evaluate(_played(tmp_path, make, mailbox, change, scenario))["outcome"] is None


def test_an_operator_stop_in_mid_battle_has_no_outcome():
    """benchmark.md, Outcome and score: an operator stop is "shown separately". Wrong version:
    evaluate reads it as a loss."""
    stopped = {"status": "interrupted", "battle": "b"}
    assert benchmark.benchmark_outcome(stopped) == "operator_stop"
    assert benchmark.evaluate(stopped)["outcome"] is None


def test_a_trial_the_engine_ended_but_whose_final_copying_was_stopped_is_an_operator_stop():
    """Owner, 2026-11-13: "interrupted, readers skip it (Recommended)". Wrong versions: the label
    keeps the engine's win while evaluate skips the trial; the rule applies only under status
    `interrupted`, so a late controller error with a cut copy still counts as the engine's win;
    the rule also relabels a forfeit, which benchmark.md says stays "labelled forfeit"."""
    stopped = {"status": "interrupted", "battle": "b", "engine_ending": {"result": "won"},
               "interrupted_copy": "imagery"}
    assert benchmark.benchmark_outcome(stopped) == "operator_stop"
    assert benchmark.benchmark_outcome({**stopped, "interrupted_copy": None}) == "won"
    # As play writes it when the controller fails after the ending and the copy is then cut.
    late = {"status": "policy_failure", "error": "acknowledge: ValueError: late bug",
            "battle": "b", "engine_ending": {"result": "won"}, "interrupted_copy": "recording"}
    assert benchmark.benchmark_outcome(late) == "operator_stop"
    assert benchmark.evaluate(late)["outcome"] is None
    forfeit = {"status": "policy_failure", "error": "decide: ValueError: controller bug",
               "battle": "b", "interrupted_copy": "recording"}
    assert benchmark.benchmark_outcome(forfeit) == "forfeit"


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
