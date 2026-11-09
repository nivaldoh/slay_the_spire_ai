"""Small-sample win-rate statistics, checked against published values or a second computation.

Sources of the expected values: Fisher's tea table (3 of 4 against 1 of 4, p = 34/70) and
Newcombe 1998's worked example (56/70 against 48/80) are published. The other Fisher values
agree with scipy.stats.fisher_exact 1.18.1, the other intervals with statsmodels 0.15.0
confint_proportions_2indep(method="newcomb"), and the powers and gate chances with a separate
brute force in exact fractions (runs/siege-evals-20261108/scratch/P1-exact-stats, not in Git).
The Boschloo values come from scipy.stats.boschloo_exact 1.18.1 (BOSCHLOO_SCIPY below).
These establish the arithmetic only, not that a plan's assumptions hold in live battles.
"""
import re

import pytest

from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import exact_stats

# (wins_a, launches_a, wins_b, launches_b): two-sided p from scipy.stats.boschloo_exact 1.18.1 at
# n=256 (runs/siege-evals-20261108/scratch3/stats-method-options/boschloo_reference.py, not in
# Git); scipy's default n=32 and a 200001-rate grid of the same regions agree to 8 places.
BOSCHLOO_SCIPY = {
    (3, 4, 1, 4): .2890625, (1, 4, 3, 4): .2890625, (2, 8, 7, 12): .19147349,
    (0, 10, 6, 14): .01565759, (0, 10, 5, 10): .01277924, (8, 10, 3, 10): .04138947,
    (10, 16, 4, 16): .04139898, (4, 16, 10, 16): .04139898, (11, 16, 5, 16): .05010653,
    (6, 16, 1, 16): .05022586, (12, 16, 8, 16): .16867052, (5, 16, 0, 16): .0202436,
    (16, 16, 11, 16): .0202436, (8, 16, 8, 16): .93718076, (0, 16, 0, 16): 1.0,
    (9, 11, 3, 9): .04643716,
}


def test_fisher_adds_every_table_no_more_likely_than_the_observed_one():
    # Fisher's tea table: tables 0..4 of 4 have chances 1, 16, 36, 16, 1 in 70, so the
    # two-sided p is 34/70; one-sided it is 17/70 (0.243), a mid-p would be below 0.4.
    assert exact_stats.fisher(3, 4, 1, 4) == pytest.approx(34 / 70, abs=1e-12)
    assert exact_stats.fisher(1, 4, 3, 4) == pytest.approx(34 / 70, abs=1e-12)
    # Unequal arms make the tails unequal: twice the smaller one-sided p would be 0.314.
    assert round(exact_stats.fisher(2, 8, 7, 12), 4) == .1968
    # Unequal arms after a failed launch: ranking tables by the gap between the two rates
    # instead of by their chance gives 0.0501 here and loses the 5% result.
    assert round(exact_stats.fisher(0, 10, 6, 14), 4) == .0239
    assert exact_stats.fisher(0, 10, 0, 10) == 1


def test_fisher_matches_the_guideline_values_at_ten_launches_per_arm():
    assert round(exact_stats.fisher(0, 10, 5, 10), 4) == .0325
    assert round(exact_stats.fisher(0, 10, 4, 10), 4) == .0867
    assert round(exact_stats.fisher(8, 10, 3, 10), 4) == .0698


def test_newcombe_hybrid_score_interval_matches_published_and_statsmodels_values():
    assert [round(end, 4) for end in exact_stats.newcombe(56, 70, 48, 80)] == [.0524, .3339]
    # evaluation-guidelines.md 7.3: 4 of 10 against 0 of 10 is +4 to +69 points.
    assert [round(end, 3) for end in exact_stats.newcombe(4, 10, 0, 10)] == [.038, .687]
    assert [round(end, 3) for end in exact_stats.newcombe(0, 10, 4, 10)] == [-.687, -.038]
    # A Wald interval gives 0 to 0 here.
    assert [round(end, 3) for end in exact_stats.newcombe(0, 10, 0, 10)] == [-.278, .278]
    assert exact_stats.newcombe(0, 0, 1, 2) is None


def test_plan_power_matches_an_exact_brute_force():
    cases = {(10, .2, .7): .426, (10, .1, .6): .474, (10, 0, .5): .623, (10, .1, .8): .841,
             (14, .2, .7): .646, (16, .2, .7): .740}
    assert {case: round(exact_stats.plan_power(*case), 3) for case in cases} == cases
    # With no real difference the test rejects, in either direction, 1.3% of the time
    # (evaluation-guidelines.md 7.2: "at most about 1.3%").
    assert round(exact_stats.plan_power(10, .5, .5), 4) == .0128
    assert exact_stats.plan_power(10, 0, 0) == 0


def test_the_overview_prints_plan_power_for_its_grid_and_launch_counts():
    """historical-evals.md rule 1 prints the round's power for witness rates 0.7-0.9 against
    drops of 30, 40 and 50 points at 16, 24 and 32 launches per arm, and the fewest launches per
    arm that reach 80%. Wrong versions: a grid computed at 15 per arm; a row left out; a count
    one launch short of 80%."""
    page = (REPO_ROOT / "docs/twwarhammer3/historical-evals.md").read_text()
    rows = re.findall(r"^ *\| (\d+) \| (0\.\d) \| (0\.\d{3}) \| (0\.\d{3}) \| (0\.\d{3}) \|$",
                      page, re.M)
    grid = {(int(launches), float(rate)): [float(power) for power in powers]
            for launches, rate, *powers in rows}
    assert len(rows) == len(grid) == 9
    assert sorted(grid) == [(launches, rate) for launches in (16, 24, 32) for rate in (.7, .8, .9)]
    for (launches, rate), powers in grid.items():
        assert powers == [round(exact_stats.plan_power(launches, rate, round(rate - drop, 2)), 3)
                          for drop in (.3, .4, .5)], (launches, rate)
    counts = re.findall(r"(\d+) for (0\.\d) against\s+(0\.\d)", page)
    assert len(counts) == 4
    for launches, rate_a, rate_b in counts:
        powers = [exact_stats.plan_power(n, float(rate_a), float(rate_b))
                  for n in range(1, int(launches) + 1)]
        assert powers[-1] >= .8 > max(powers[:-1]), (launches, rate_a, rate_b)


def test_boschloo_matches_scipy_boschloo_exact_on_vendored_tables():
    """Wrong versions: one direction's p alone; fisher()'s conditional p returned as Boschloo's
    (0.486 on the tea table, 0.073 on 10 of 16 against 4 of 16)."""
    assert ({table: exact_stats.boschloo(*table) for table in BOSCHLOO_SCIPY}
            == pytest.approx(BOSCHLOO_SCIPY, abs=1e-6))


def test_boschloo_rejects_a_superset_of_fisher_within_five_percent_at_16_per_arm():
    """Second look S4, whose region scipy reproduced: 134 of the 289 tables against Fisher's
    122, every Fisher rejection included, and a worst false-pass rate over the 2001 common rates
    of 0.0414, where Fisher's is 0.0202 at 0.5. Power at 0.7 against 0.2 is 0.823 (Fisher 0.740)."""
    tables = [(a, b) for a in range(17) for b in range(17)]
    fisher = {(a, b) for a, b in tables if exact_stats.fisher(a, 16, b, 16) < .05}
    boschloo = {(a, b) for a, b in tables if exact_stats.boschloo(a, 16, b, 16) < .05}
    assert (len(fisher), len(boschloo)) == (122, 134) and fisher < boschloo
    sizes = [exact_stats.plan_power(16, rate, rate, test=exact_stats.boschloo)
             for rate in (i / 2000 for i in range(2001))]
    assert round(max(sizes), 4) == .0414
    assert round(exact_stats.plan_power(16, .5, .5), 4) == .0202
    assert round(exact_stats.plan_power(16, .7, .2, test=exact_stats.boschloo), 3) == .823


def test_verdict_fixed_tries_every_completion_of_a_round():
    """Rounds of 16 per arm. Wrong versions: a stop that tries only the all-won and all-lost
    completions fires at 4 of 8 each, though 12 against 4 would still pass; one that tries
    only each arm's all-won and all-lost fires when A has not played and B won 5 of 10, where
    every such corner passes but 5 against 5 does not."""
    fixed = exact_stats.verdict_fixed
    assert not fixed(0, 0, 0, 0, 16)
    assert not fixed(4, 8, 4, 8, 16)
    assert not fixed(0, 0, 5, 10, 16)
    assert fixed(12, 12, 0, 12, 16)  # every completion passes
    assert fixed(5, 10, 5, 10, 16)  # none passes: 11 against 5 gives 0.076
    assert fixed(3, 16, 9, 16, 16)
    # Fisher passes no completion of 9 of 15 against 4 of 15; Boschloo passes 10 against 4.
    assert fixed(9, 15, 4, 15, 16)
    assert not fixed(9, 15, 4, 15, 16, test=exact_stats.boschloo)


def test_gate_error_rates_match_the_guideline_table():
    assert exact_stats.gate_pass(4, 5, .5) == pytest.approx(.1875)
    assert 1 - exact_stats.gate_pass(4, 5, .8) == pytest.approx(.26272)
    assert round(exact_stats.gate_pass(10, 10, 1 - .2), 4) == .1074  # a foil winning 20%
    assert round(exact_stats.gate_pass(10, 14, .5), 4) == .0898
    assert round(1 - exact_stats.gate_pass(10, 14, .7), 4) == .4158


def test_mcnemar_tests_only_the_starts_exactly_one_arm_won():
    # evaluation-guidelines.md 7.2: both 0, only A 6, only B 2, neither 12 gives p = 0.29.
    pairs = [(True, False)] * 6 + [(False, True)] * 2 + [(False, False)] * 12
    result = exact_stats.mcnemar(pairs)
    assert result == {"both": 0, "only_a": 6, "only_b": 2, "neither": 12, "p": .2891}
    # Starts both arms won change nothing; treating the arms as separate launches would.
    assert exact_stats.mcnemar(pairs + [(True, True)] * 30)["p"] == .2891
    assert exact_stats.mcnemar([(True, True), (False, False)])["p"] is None
