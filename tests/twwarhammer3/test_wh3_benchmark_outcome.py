"""cards.benchmark_outcome (version 1) on episodes that play.play_episode writes against a fake
mailbox, one per row of benchmark.md's outcome table, beside the card rule (cards.outcome),
whose answers stay as they were."""
import json

import pytest
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError
from twwarhammer3.battle import cards, play, setup
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


# (case, controller, mailbox, config change, scenario, benchmark outcome, card rule)
CASES = [
    ("contact win", Hold, lambda: FakeMailbox(_ending("won")), {}, None, "won", "won"),
    ("timer win", Hold, lambda: FakeMailbox(_ending("won", TIMER)), {}, None, "won", "lost"),
    ("timer loss", Hold, lambda: FakeMailbox(_ending("lost", TIMER)), {}, None, "lost", "lost"),
    ("draw", Hold, lambda: FakeMailbox(_ending("draw")), {}, None, "draw", "lost"),
    ("error after the ending", _Late, lambda: FakeMailbox(_ending("won")), {}, None, "won",
     "forfeit"),
    ("stop at cleanup after the ending", _CloseStops, lambda: FakeMailbox(_ending("lost", TIMER)),
     {}, None, "lost", "excluded"),
    ("controller bug in the battle", _Bug, lambda: FakeMailbox(_ending("won")), {}, None,
     "forfeit", "forfeit"),
    ("provider error ends the battle", _Provider, lambda: FakeMailbox(_ending("won")), {}, None,
     "unresolved", "forfeit"),
    ("not built", _broken, lambda: FakeMailbox(_ending("won")), {}, None, "not_built",
     "excluded"),
    ("team refused at construction", _no_team, lambda: FakeMailbox(_ending("won")), {}, None,
     "setup_or_game_failure", "excluded"),
    ("no battle starts", Hold, lambda: FakeMailbox([]), {}, None, "never_started", "excluded"),
    ("game silent", Hold, lambda: FakeMailbox([bridge_observation(0, 0)]), {}, None,
     "unresolved", "excluded"),
    ("wrong role", Hold, lambda: FakeMailbox(_wrong_role()), {}, "siege-kho5-dwf5",
     "setup_or_game_failure", "excluded"),
    ("budget stop", _Spent, lambda: FakeMailbox(_ending("won")), {}, None, "unresolved",
     "excluded"),
    ("wall cap", Hold, lambda: FakeMailbox(_ending("won")), {"episode_timeout": -1}, None,
     "unresolved", "forfeit"),
    ("wall cap, then a cleanup bug", _CloseFails, lambda: FakeMailbox(_ending("won")),
     {"episode_timeout": -1}, None, "unresolved", "forfeit"),
    ("our own exception", Hold, lambda: _Crashing(_ending("won")), {}, None, "unresolved",
     "excluded"),
]


@pytest.mark.parametrize("case, make, mailbox, change, scenario, expected, card", CASES,
                         ids=[case[0] for case in CASES])
def test_each_ending_play_writes_gets_its_row(tmp_path, case, make, mailbox, change, scenario,
                                              expected, card):
    loaded = setup.load_scenario({"scenario": scenario}) if scenario else None
    play.play_episode(tmp_path / "e", {**CONFIG, **change}, make, mailbox(), not_battle=None,
                      scenario=loaded)
    result = json.loads((tmp_path / "e/result.json").read_text())
    assert (cards.benchmark_outcome(result), cards.outcome(result)) == (expected, card)


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
    assert result["status"] == "interrupted" and cards.outcome(result) == "excluded"
    assert cards.benchmark_outcome(result) == expected


def test_no_result_never_started_and_old_key_or_credit_failures_are_unresolved():
    assert cards.benchmark_outcome(None) == "never_started"
    assert cards.benchmark_outcome({"status": "missing_result"}) == "never_started"  # report's
    # Key and credit failures from before b35, which a policy failure carried: still to settle.
    for code in (401, 402):
        assert cards.benchmark_outcome({"status": "policy_failure", "battle": "b", "error":
                                        f"decide: APIError: HTTP {code}: no"}) == "unresolved"


def test_a_record_from_before_the_kept_ending_is_read_by_its_status():
    # Before b47 (2026-10-21) result.json had no engine_ending: all 3 register timer wins.
    for status in ("won", "lost", "draw"):
        assert cards.benchmark_outcome({"status": status, "ended_by": "time_limit",
                                        "battle": "b"}) == status
