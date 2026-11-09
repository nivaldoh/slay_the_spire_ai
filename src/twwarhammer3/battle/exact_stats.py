"""Small-sample statistics for win rates: tests, an interval, power and gate error rates.

fisher(), mcnemar(), plan_power() (evaluation-guidelines.md 7.4) and gate_pass() (2.7) are
exact: each adds the chances of every possible outcome, and nothing is simulated. Tests are
two-sided with classic exact p-values. newcombe() is not exact: it combines two Wilson
intervals (report.wilson, z = 1.96), which rest on a normal approximation (7.2: one Wilson
interval's coverage can fall to about 84% for rates near 0 or 1), and it is for separate
launches only. The paired Newcombe interval 7.2 names for shared launches is not built yet.
Exact one-sided bounds and the sign test stay in suite.py.
"""

import math

from twwarhammer3.battle import suite
from twwarhammer3.battle.report import wilson

# scipy.stats.fisher_exact (scipy/stats/_stats_py.py, 1.18.1) counts a table whose chance is
# within this relative margin of the observed table's as no more likely than it.
RELATIVE_TOLERANCE = 1e-14


def binomial(launches: int, rate: float) -> list[float]:
    """The chance of each win count 0..launches for independent launches at a true rate."""
    return [math.comb(launches, wins) * rate ** wins * (1 - rate) ** (launches - wins)
            for wins in range(launches + 1)]


def fisher(wins_a: int, launches_a: int, wins_b: int, launches_b: int) -> float:
    """Two-sided Fisher exact p-value for two win rates from separate launches.

    With the total wins fixed, every split of them between the arms has a hypergeometric
    chance; the p-value adds the chances of all splits no more likely than the observed one
    (the classic definition, as scipy.stats.fisher_exact, scipy/stats/_stats_py.py). It is
    not twice a one-sided p and not a mid-p.
    """
    wins = wins_a + wins_b
    every = math.comb(launches_a + launches_b, wins)
    chances = [math.comb(launches_a, x) * math.comb(launches_b, wins - x) / every
               for x in range(max(0, wins - launches_b), min(wins, launches_a) + 1)]
    observed = chances[wins_a - max(0, wins - launches_b)]
    return min(1.0, sum(c for c in chances if c <= observed * (1 + RELATIVE_TOLERANCE)))


def newcombe(wins_a: int, launches_a: int, wins_b: int, launches_b: int) -> list[float] | None:
    """95% interval for rate A minus rate B from separate launches, None if an arm has none.

    Newcombe 1998 method 10, the hybrid score interval: each end combines the two Wilson
    intervals' distances from their rates. As statsmodels'
    confint_proportions_2indep(method="newcomb") (statsmodels/stats/proportion.py), with
    report.wilson's z of 1.96. Unlike a normal (Wald) interval it does not shrink to a point
    when both arms win nothing.
    """
    if not launches_a or not launches_b:
        return None
    low_a, high_a = wilson(wins_a, launches_a)
    low_b, high_b = wilson(wins_b, launches_b)
    rate_a, rate_b = wins_a / launches_a, wins_b / launches_b
    return [rate_a - rate_b - math.hypot(rate_a - low_a, high_b - rate_b),
            rate_a - rate_b + math.hypot(high_a - rate_a, rate_b - low_b)]


def plan_power(launches: int, rate_a: float, rate_b: float, alpha: float = .05) -> float:
    """Chance that fisher() on `launches` separate launches per arm gives p < alpha, when the
    arms truly win at rate_a and rate_b; a rejection in either direction counts.

    Exact: it adds the chance of every pair of win counts whose test rejects.
    """
    chance_a, chance_b = binomial(launches, rate_a), binomial(launches, rate_b)
    return sum(chance_a[a] * chance_b[b] for a in range(launches + 1)
               for b in range(launches + 1) if fisher(a, launches, b, launches) < alpha)


def gate_pass(need: int, launches: int, rate: float) -> float:
    """Chance that a controller winning at true rate `rate` wins at least `need` of `launches`
    separate launches: how often a witness gate passes it. One minus this is how often the
    gate fails a witness that good. A foil gate "loses all n" passes a foil winning at rate
    r with gate_pass(n, n, 1 - r).
    """
    return sum(binomial(launches, rate)[need:])


def mcnemar(pairs) -> dict:
    """Exact two-sided McNemar test for arms A and B played on the same starts.

    Each pair is (A won, B won) for one shared start, such as two checkpoint branches. Only
    the starts exactly one arm won carry information, and their split is tested with
    suite.sign_test (two-sided, rounded to 4 places). Returns the four joint counts and p,
    which is None when no start was won by exactly one arm.
    """
    counts = {"both": 0, "only_a": 0, "only_b": 0, "neither": 0}
    for won_a, won_b in pairs:
        key = ("neither", "only_b", "only_a", "both")[2 * bool(won_a) + bool(won_b)]
        counts[key] += 1
    return {**counts, "p": suite.sign_test(counts["only_a"], counts["only_b"])}
