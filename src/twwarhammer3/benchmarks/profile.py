"""The initial mirror benchmark's profile: limits, the one-call transport, the per-battle
budget and the first-ending condition. Plans and their reading are in benchmark_plans.py.
The tactic cards had their own evaluator until it was deleted on 2026-11-15; this module reads
the versioned profile and labels an episode's outcome.
"""

import math
import signal
import threading

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError, post

VERSION = "mirror-v1"
SUITE = "suite-v1"  # the coordination suite; its plan, measures and report are in suite.py
SCENARIO = "emp-mirror-cavalry-v1"
# Values below rest on JUDGEMENT benchmark-implementation.md Simple condition score,
# Starter limits and inputs, No-retry scope and accounting, and Starter repetition.
CALL_LIMIT = 200
BATTLE_USD = 2
# JUDGEMENT: Suite limits — Claude, 2026-11-04, overnight goal: no real call cap (a team makes
# about twice a single controller's calls and a battle can last 20 minutes), $3 a battle at Haiku
# (one model cost $0.49 on the longest battle, so three members come near $1.50).
# Lower limits end long or many-member battles early and change what they can show.
SUITE_CALL_LIMIT = 5000
SUITE_BATTLE_USD = 3
READ_TIMEOUT_S = 60
# One battle per fresh launch: the play limits every benchmark plan passes and validate_config
# requires (seconds).
START_TIMEOUT_S, EPISODE_TIMEOUT_S, RUN_TIMEOUT_S = 900, 1320, 2280
LAUNCH_ARGS = ["--start-timeout", str(START_TIMEOUT_S), "--episode-timeout",
               str(EPISODE_TIMEOUT_S), "--run-timeout", str(RUN_TIMEOUT_S)]
FACTORS = {"wavering": .8, "routing": .5, "shattered": 0}
OUTCOMES = {"won": 2, "draw": 1, "lost": 0}
# JUDGEMENT: Initial model screen — Codex, 2026-11-02, under the owner's cheap-Anthropic
# request: Haiku 5.5 low, five attempts, $2 cumulative WH3 Anthropic ledger cap, no preparation
# calls. Other efforts/models/repeats change this exploratory screen's cost and meaning.
MODEL = "claude-haiku-5-5"
EFFORT = "low"


def send_once(key, body, *, provider):
    """One synchronous WSL request, bounded in total as well as per socket read.

    Only direct controllers are admitted to this first profile: this runs on the main
    thread, where SIGALRM can interrupt a server that keeps trickling response bytes.
    A timeout may have been billed; Model charges its reservation once, without resending.
    """
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise APIError("benchmark needs an unused request deadline timer; request not sent")

    def expired(signum, frame):
        raise APIError("benchmark decision request exceeded its deadline", uncertain_attempts=1)

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, READ_TIMEOUT_S)
    try:
        return post(key, body, attempts=1, timeout_s=READ_TIMEOUT_S,
                    provider=provider, record_transport=True)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


# One lock for every BattleBudget: team members share a budget and leaves have their own on
# one ledger; each calls from its own thread, and only one may pass the allowance check at once.
_RESERVE_LOCK = threading.Lock()


class BattleBudget:
    """An episode's allowance layered over the existing cumulative ledger, without resetting it.

    The initial profile permits one synchronous model only. Reservations count uncertain
    calls too, so failures cannot evade the call or dollar cap.
    """

    def __init__(self, ledger, call_limit=CALL_LIMIT, battle_usd=BATTLE_USD, version=VERSION):
        self.ledger, self.path = ledger, ledger.path
        self.started_spent, self.calls = ledger.spent, 0
        self.call_limit, self.battle_usd, self.version = call_limit, battle_usd, version

    def reserve(self, usd):
        with _RESERVE_LOCK:
            if self.calls >= self.call_limit:
                raise BudgetExhausted(f"Benchmark reached {self.call_limit} decision calls")
            if self.ledger.spent - self.started_spent + self.ledger.held + usd > self.battle_usd:
                raise BudgetExhausted(
                    f"Benchmark next call exceeds ${self.battle_usd} battle allowance")
            self.ledger.reserve(usd)
            self.calls += 1

    def release(self, usd):
        self.ledger.release(usd)

    def charge(self, usd, **fields):
        self.ledger.charge(usd, **fields)


def suite_budget(ledger):
    return BattleBudget(ledger, SUITE_CALL_LIMIT, SUITE_BATTLE_USD, SUITE)


def condition(ids: list[str], units: list[dict], size: int | None = 5) -> dict:
    """Equal tactical-unit weights; no entity/cost weighting or missing-as-dead inference.

    ``size`` is the original unit count a profile requires; None takes any nonempty army."""
    rows, missing = [], []
    by_id = {unit.get("id"): unit for unit in units}
    if (not ids or size not in (None, len(ids)) or len(set(ids)) != len(ids)
            or len(by_id) != len(units)):
        return {"condition": None, "units": [], "unavailable": ["invalid original/unit identities"]}
    for uid in ids:
        raw = by_id.get(uid)
        row = {"id": uid, "raw": raw, "factor": None, "contribution": None}
        rows.append(row)
        if raw is None:
            missing.append(uid)
            continue
        # An explicit failed read invalidates even otherwise plausible values.
        if raw.get("error"):
            missing.append(uid)
            continue
        men, hp = raw.get("men"), raw.get("hp")
        if type(men) not in (int, float) or not math.isfinite(men) or men < 0:
            missing.append(uid)
            continue
        if (type(hp) not in (int, float) or not math.isfinite(hp) or not 0 <= hp <= 1
                or any(type(raw.get(key)) is not bool for key in (*FACTORS, "departed"))):
            missing.append(uid)
            continue
        factor = min([1, *(value for key, value in FACTORS.items() if raw[key])])
        if men == 0 or raw["departed"]:
            factor = 0
        row.update(factor=factor, contribution=hp * factor)
    return {"condition": None if missing else 100 * sum(r["contribution"] for r in rows) / len(ids),
            "units": rows, "unavailable": missing}


# One label per episode from its evidence, with errors and missing runs kept apart from losses.
# Shaped like SWE-bench's run report (swebench/harness/reporting.py, make_run_report). It came
# from cards.py on 2026-11-15, when the tactic cards and their own outcome rule were deleted
# (tag wh3-legacy-20261115). A changed rule gets a new version. Version 2 (2026-11-15): a trial
# the engine ended but whose final copying was stopped is an operator stop, where version 1
# kept the engine's result; every other label is version 1's. evaluate takes its outcome from
# this label, so the label and the counted outcome cannot disagree.
BENCHMARK_OUTCOME_VERSION = 2


# Which failures end a battle rests on JUDGEMENT src/twwarhammer3/protocol.py Operator errors
# and Forfeit split; a truncation on JUDGEMENT src/twwarhammer3/battle/play.py Wall cap.
# JUDGEMENT: Benchmark-outcome rows — Claude, 2026-10-31: statuses map to benchmark.md's outcome
# rows of that date; provider, budget, wall-cap and unknown-cause stops stay unresolved. Another
# mapping moves episodes into or out of the denominator of any reader adopting version 1.
def benchmark_outcome(result: dict | None) -> str:
    """won, lost or draw as the engine ended it (timer endings included; a later error or stop
    keeps it, unless the final copying was stopped: then operator_stop); forfeit (the
    controller's own code failed for good in the battle); not_built; operator_stop or
    setup_or_game_failure (shown separately); never_started (no result, or no battle began); or
    unresolved (provider, key, credit, budget and wall-cap stops, a silent or restarted game, an
    exception in our own code). Only won, lost and draw count in a win rate (evaluate); the
    owner on unresolved, 2026-11-15: "Unresolved battles can be kept out of the counts"."""
    if result is None or result.get("status") in (None, "missing_result"):
        return "never_started"
    # Owner, 2026-11-13: "interrupted, readers skip it (Recommended)". A Ctrl-C during the final
    # copying may have cut the copies, so a trial the engine ended is an operator stop instead of
    # its result. A trial with no engine result keeps its own label (a forfeit stays a forfeit).
    if result.get("interrupted_copy") and recorded_outcome(result):
        return "operator_stop"
    status, error = result["status"], str(result.get("error"))
    ending = (result.get("engine_ending") or {}).get("result")
    if ending in ("won", "lost", "draw"):
        return ending
    if status in ("won", "lost", "draw"):
        return status
    if status == "interrupted":
        return "operator_stop"
    # A protocol refusal names its cause (a failed setup check, a paused or slowed battle, a
    # failed custom ending); so does a team's partition or dispatcher fault (TeamHarnessError).
    if status == "unsupported_or_invalid":
        return "setup_or_game_failure"
    if status == "policy_failure" and error.startswith("controller construction:"):
        return "not_built"
    if not result.get("battle"):
        return "never_started"
    # A provider error (an APIError; HTTP 401 and 402 were policy failures before b35) and a
    # wall cap, even one a failed cleanup followed, are still to settle.
    if (status == "policy_failure" and "APIError" not in error
            and result.get("reason") != "episode_timeout"):
        return "forfeit"
    return "unresolved"


def recorded_outcome(result: dict | None) -> str | None:
    """won, lost or draw as the engine ended the battle, else as the status says, else None."""
    result = result or {}
    outcome = (result.get("engine_ending") or {}).get("result")
    if outcome not in OUTCOMES:
        outcome = result.get("status") if result.get("status") in OUTCOMES else None
    return outcome


def evaluate(result: dict | None) -> dict:
    """Only an attempt that benchmark_outcome labels won, lost or draw has an outcome and a
    rank; errors never invent a loss. Every other label (forfeit, not_built, operator_stop,
    setup_or_game_failure, never_started, unresolved) is in neither the numerator nor the
    denominator of a win rate. Every benchmark reader takes the outcome from here."""
    result = result or {}
    label = benchmark_outcome(result)
    outcome = label if label in OUTCOMES else None
    measured = result.get("benchmark") or {}
    version = SUITE if measured.get("version") == SUITE else VERSION
    scored = {"condition": None, "units": [], "unavailable": ["no first-ending measurement"]}
    if outcome and measured.get("version") == version and result.get("setup_checks"):
        scored = condition(list((result.get("start") or {}).get("friendly", {})),
                           measured.get("units") or [], None if version == SUITE else 5)
    return {"version": version, "outcome": outcome, **scored,
            "rank": [OUTCOMES[outcome], scored["condition"]]
            if outcome and scored["condition"] is not None else None}


def validate_config(scenario, config):
    """A profile has one frozen controller and one battle per fresh launch."""
    if not scenario.get("benchmark"):
        return
    if scenario["benchmark"] not in (VERSION, SUITE):
        raise ValueError("unknown benchmark version")
    allowed = {"hold", "attack_nearest", "rush_nearest", "llm_rules"}
    if scenario["benchmark"] == SUITE:
        allowed |= {"llm", "skills", "team_llm_rules", "commander", "configured",
                    "twwarhammer3.controllers.reference:Concentrate"}
    names = config["policy"].split(",")
    if (len(names) != 1 or names[0].partition("@")[0] not in allowed
            or config.get("episodes") != 1 or config.get("attach")
            or config.get("interval_ms", 0) or str(config.get("delay_seconds", "0")) != "0"
            or config.get("start_timeout") != START_TIMEOUT_S
            or config.get("episode_timeout") != EPISODE_TIMEOUT_S
            or config.get("observe_ms") != 1000 or config.get("tick_ms") != 250):
        raise ValueError(f"{scenario['benchmark']} requires one fresh launch/battle, a frozen"
                         f" controller, no added waits, {START_TIMEOUT_S}/{EPISODE_TIMEOUT_S} s"
                         " caps and 1000/250 ms observation/tick")
