"""Small-sample statistics for win rates: tests, an interval, power and gate error rates.

fisher(), mcnemar(), plan_power() (evaluation-guidelines.md 7.4) and gate_pass() (2.7) are
exact: each adds the chances of every possible outcome, and nothing is simulated. Tests are
two-sided with classic exact p-values. newcombe() is not exact: it combines two Wilson
intervals (report.wilson, z = 1.96), which rest on a normal approximation (7.2: one Wilson
interval's coverage can fall to about 84% for rates near 0 or 1), and it is for separate
launches only. The paired Newcombe interval 7.2 names for shared launches is not built yet.
Exact one-sided bounds and the sign test stay in suite.py.

Two options for the owner sit beside the current method and change nothing by default
(second look of 2026-11-09, owner question 4). boschloo() is an exact test that could replace
fisher() in a round (4(b)); it adds exact chances too, but searches the arms' common rate on a
grid. plan_power() and verdict_fixed() take either as `test`, and fisher stays the default.
verdict_fixed() says when a round could stop because no remaining launch can change its verdict
(4(c)); without that option a round plays every planned launch.
"""

import bisect
import functools
import math

from twwarhammer3.battle import suite
from twwarhammer3.battle.report import wilson

# scipy.stats.fisher_exact (scipy/stats/_stats_py.py, 1.18.1) counts a table whose chance is
# within this relative margin of the observed table's as no more likely than it.
RELATIVE_TOLERANCE = 1e-14
# boschloo() searches the common true rate on this many evenly spaced rates, 0 and 1 included.
BOSCHLOO_GRID = 2001


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


# JUDGEMENT: Boschloo option — Claude, 2026-11-09 (second look owner question 4(b)): two-sided p
# is twice the smaller one-sided p, as scipy, over a 2001-rate grid. Ordering tables by fisher()'s
# two-sided p gives other p-values; any round decided by boschloo() rests on this.
def boschloo(wins_a: int, launches_a: int, wins_b: int, launches_b: int) -> float:
    """Two-sided Boschloo exact p-value for two win rates from separate launches.

    Fisher's one-sided p orders the tables in each direction. A one-sided p-value is the
    largest chance, over a common true rate of both arms, of a table no larger in that order
    than the observed one; the rate is searched on BOSCHLOO_GRID evenly spaced rates. The
    two-sided p is twice the smaller one-sided p, at most 1, as
    scipy.stats.boschloo_exact(alternative="two-sided") (scipy/stats/_hypotests.py, 1.18.1),
    which finds the largest chance with an optimizer instead of a grid. Unlike fisher(), it
    does not fix the total wins.
    """
    return _boschloo_p_values(launches_a, launches_b)[wins_a, wins_b]


@functools.cache
def _boschloo_p_values(launches_a: int, launches_b: int) -> dict:
    """boschloo() for every table at these arm sizes, computed together."""
    tables = [(a, b) for a in range(launches_a + 1) for b in range(launches_b + 1)]
    chances = [(binomial(launches_a, rate), binomial(launches_b, rate))
               for rate in (i / (BOSCHLOO_GRID - 1) for i in range(BOSCHLOO_GRID))]

    def ways(a, b, x):  # ways to give A x of the a + b wins
        return math.comb(launches_a, x) * math.comb(launches_b, a + b - x)

    def one_sided(tail) -> dict:
        # tail(a, b): the wins A may hold, given a + b in all, for a table at least as extreme.
        # Each rank is one division of two integers, so equal ranks are equal floats and the
        # relative tolerance of 1e-13 scipy allows for its rounding is not needed.
        order = {(a, b): sum(ways(a, b, x) for x in tail(a, b))
                 / math.comb(launches_a + launches_b, a + b) for a, b in tables}
        ranked = sorted(tables, key=order.get)
        ranks = [order[table] for table in ranked]
        largest = [0.0] * (len(ranked) + 1)
        for chance_a, chance_b in chances:
            total = 0.0
            for k, (a, b) in enumerate(ranked, 1):
                total += chance_a[a] * chance_b[b]
                largest[k] = max(largest[k], total)
        return {table: largest[bisect.bisect_right(ranks, order[table])] for table in tables}

    fewer = one_sided(lambda a, b: range(max(0, a + b - launches_b), a + 1))
    more = one_sided(lambda a, b: range(a, min(a + b, launches_a) + 1))
    return {table: min(1.0, 2 * min(fewer[table], more[table])) for table in tables}


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


def plan_power(launches: int, rate_a: float, rate_b: float, alpha: float = .05,
               test=fisher) -> float:
    """Chance that `test` (fisher() or boschloo()) on `launches` separate launches per arm gives
    p < alpha, when the arms truly win at rate_a and rate_b; a rejection in either direction
    counts. With rate_a equal to rate_b it is the test's false-pass rate at that rate.

    Exact: it adds the chance of every pair of win counts whose test rejects.
    """
    chance_a, chance_b = binomial(launches, rate_a), binomial(launches, rate_b)
    return sum(chance_a[a] * chance_b[b] for a in range(launches + 1)
               for b in range(launches + 1) if test(a, launches, b, launches) < alpha)


# JUDGEMENT: Fixed-verdict stop — Claude, 2026-11-09 (second look owner question 4(c)): a round may
# stop once every completion gives one verdict, reporting counts only. Playing every planned launch
# keeps the interval and effect estimate; any round stopped by verdict_fixed() rests on this.
def verdict_fixed(wins_a: int, played_a: int, wins_b: int, played_b: int, planned: int,
                  test=fisher, alpha: float = .05) -> bool:
    """True when every way the unplayed launches of a round of `planned` launches per arm can
    end gives the same verdict (`test` p < alpha, or not), so the rest cannot change it.

    It tries every completion: each arm may win any number of its unplayed launches. A round
    stopped here reports its counts and its unplayed launches as not needed, with no Newcombe
    interval or effect estimate, as gates do. evaluation-guidelines.md 7.4 allows this stop for
    gates only, so using it in a round changes 7.4. A futility look at 8 per arm is a separate
    option and is not built here.
    """
    return len({test(wins_a + more_a, planned, wins_b + more_b, planned) < alpha
                for more_a in range(planned - played_a + 1)
                for more_b in range(planned - played_b + 1)}) == 1


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
