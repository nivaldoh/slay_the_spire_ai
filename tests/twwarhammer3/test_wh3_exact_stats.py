"""Small-sample win-rate statistics, checked against published values or a second computation.

Sources of the expected values: Fisher's tea table (3 of 4 against 1 of 4, p = 34/70) and
Newcombe 1998's worked example (56/70 against 48/80) are published. The other Fisher values
agree with scipy.stats.fisher_exact 1.18.1, the other intervals with statsmodels 0.15.0
confint_proportions_2indep(method="newcomb"), and the powers and gate chances with a separate
brute force in exact fractions (runs/siege-evals-20261108/scratch/P1-exact-stats, not in Git).
These establish the arithmetic only, not that a plan's assumptions hold in live battles.
"""
import pytest

from twwarhammer3.battle import exact_stats


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
