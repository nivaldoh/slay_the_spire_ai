"""Physical enemy percentages stay separate from the engine outcome and win score.

Reference: communication-structure.md Measures. Of 200 starting soldiers, 170 alive and
150 active means 30 dead and 20 other soldiers inactive: killed=15%, taken=25%.
An outcome awarded at the timer does not change those counts.
"""

import pytest

from twwarhammer3.battle import suite


@pytest.mark.parametrize("outcome", ["won", "lost", "draw"])
def test_timer_outcome_does_not_replace_enemy_totals_with_the_win_score(outcome):
    result = {"status": outcome,
              "engine_ending": {"result": outcome, "ended_by": "time_limit"},
              "final": {"enemy": {"men0": 200, "men": 170, "active_men": 150}}}
    assert suite.taken(result) == 25
    assert suite.killed(result) == 15


def test_timer_win_without_enemy_totals_does_not_invent_physical_measures():
    result = {"status": "won", "engine_ending": {"result": "won", "ended_by": "time_limit"}}
    assert suite.taken(result) is None
    assert suite.killed(result) is None
