"""The initial mirror benchmark: limits, first-ending condition and a planned-attempt report.

Report layout follows SWE-bench's swebench/harness/reporting.py: enumerate the frozen
plan, then join evidence, keeping missing attempts. No donor code. Historical cards
retain their own evaluator; this module only reads the versioned mirror profile.
"""

import json
import math
import signal
import subprocess
from collections import Counter
from pathlib import Path

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError, post
from gameai.provenance import REPO_ROOT, write_json

VERSION = "mirror-v1"
SUITE = "suite-v1"  # the coordination suite; its plan, measures and report are in suite.py
SCENARIO = "emp-mirror-cavalry-v1"
# Values below rest on JUDGEMENT benchmark-implementation.md Simple condition score,
# Starter limits and inputs, No-retry scope and accounting, and Starter repetition.
CALL_LIMIT = 200
BATTLE_USD = 2
# JUDGEMENT: Suite limits — Claude, 2026-11-04, overnight goal: no call cap (a team makes about
# twice a single controller's calls and a battle can last 20 minutes), $1.50 a battle at Haiku.
# Lower limits end long or many-member battles early and change what they can show.
SUITE_CALL_LIMIT = 5000
SUITE_BATTLE_USD = 1.5
READ_TIMEOUT_S = 60
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


class BattleBudget:
    """An episode's allowance layered over the existing cumulative ledger, without resetting it.

    The initial profile permits one synchronous model only. Reservations count uncertain
    calls too, so failures cannot evade the call or dollar cap.
    """

    def __init__(self, ledger, call_limit=CALL_LIMIT, battle_usd=BATTLE_USD):
        self.ledger, self.path = ledger, ledger.path
        self.started_spent, self.calls = ledger.spent, 0
        self.call_limit, self.battle_usd = call_limit, battle_usd

    def reserve(self, usd):
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


def evaluate(result: dict | None) -> dict:
    """Only engine-completed attempts have a rank; errors never invent a loss."""
    result = result or {}
    ending = result.get("engine_ending") or {}
    outcome = ending.get("result")
    if outcome not in OUTCOMES:
        outcome = result.get("status") if result.get("status") in OUTCOMES else None
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
        allowed |= {"skills", "team_llm_rules", "commander", "configured"}
    names = config["policy"].split(",")
    if (len(names) != 1 or names[0].partition("@")[0] not in allowed
            or config.get("episodes") != 1 or config.get("attach")
            or config.get("interval_ms", 0) or str(config.get("delay_seconds", "0")) != "0"
            or config.get("start_timeout") != 900 or config.get("episode_timeout") != 1320
            or config.get("observe_ms") != 1000 or config.get("tick_ms") != 250):
        raise ValueError(f"{scenario['benchmark']} requires one fresh launch/battle, a frozen"
                         " controller, no added waits, 900/1320 s caps and 1000/250 ms"
                         " observation/tick")


def make_plan(output: Path, stage: str, budget_usd: float) -> dict:
    """Write a queue plan without launching or paying; the existing queue executes it once."""
    from twwarhammer3.battle.setup import scenarios

    if output.exists():
        raise ValueError(f"plan already exists: {output}")
    if not math.isfinite(budget_usd) or not 0 < budget_usd <= 200:
        raise ValueError("budget must be a positive cumulative ledger cap, at most $200")
    controllers = (["hold", "attack_nearest", "rush_nearest"] if stage == "pilot" else
                   [f"llm_rules@{MODEL}/{EFFORT}"] * 5)
    jobs = []
    for index, controller in enumerate(controllers):
        directory = output.parent / f"{output.stem}-{index + 1:02d}"
        args = ["--scenario", SCENARIO, "--policy", controller, "--episodes", "1",
                "--provider", "anthropic", "--budget-usd", str(budget_usd), "--stills",
                "--start-timeout", "900", "--episode-timeout", "1320", "--run-timeout", "2280"]
        jobs.append({"output": str(directory.resolve()), "args": args, "controller": controller})
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       cwd=REPO_ROOT, text=True).strip()
    plan = {"benchmark": VERSION, "source_revision": revision, "stage": stage,
            "scenario": scenarios()[SCENARIO],
            "purpose": "exploratory initial mirror benchmark; no reliable ranking claim",
            "preparation_usd": 0, "cumulative_ledger_cap_usd": budget_usd,
            "keep_going": stage == "model", "jobs": jobs}
    write_json(output, plan)
    return plan


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else None


def collect(plan_path: Path) -> dict:
    """One row per planned attempt, including queue failures before an episode exists."""
    plan = json.loads(plan_path.read_text())
    if plan.get("benchmark") not in (VERSION, SUITE):
        raise ValueError("not a benchmark plan")
    expected_profile = plan.get("scenario")
    if expected_profile is None and plan["benchmark"] == VERSION:
        # Earlier initial plans named only the source. Read that frozen profile rather
        # than silently judging an old attempt against today's changed settings.
        source = subprocess.check_output([
            "git", "show", f"{plan['source_revision']}:configs/twwarhammer3/scenarios.json"],
            cwd=REPO_ROOT, text=True)
        expected_profile = json.loads(source)[SCENARIO]
    state = read_json(plan_path.with_name(plan_path.stem + "-state.json")) or {}
    executions = {str((REPO_ROOT / row["output"]).resolve()): row
                  for row in state.get("completed", [])}
    rows = []
    for job in plan["jobs"]:
        scenario = job.get("scenario", SCENARIO)
        profile = (plan["scenarios"][scenario] if plan["benchmark"] == SUITE
                   else expected_profile)
        directory = REPO_ROOT / job["output"]
        manifest = read_json(directory / "manifest.json") or {}
        result = read_json(directory / "episode-0000/result.json")
        errors = []
        execution = executions.get(str(directory.resolve()))
        if execution and execution.get("exit_code"):
            errors.append({"category": "queue", "detail": execution})
        trace = directory / "episode-0000/trace.jsonl"
        traced_battle, trace_mismatch = None, False
        if trace.exists():
            for line in trace.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except ValueError as exc:
                    errors.append({"category": "trace", "detail": str(exc)})
                    continue
                if event["kind"] == "battle":
                    observed = event.get("observation") or {}
                    identity = observed.get("battle")
                    if (observed.get("job") == directory.name
                            and isinstance(identity, str) and identity):
                        if traced_battle and traced_battle != identity:
                            trace_mismatch = True
                        traced_battle = identity
                    else:
                        trace_mismatch = True
                if event["kind"] in ("forfeit", "invalid"):
                    errors.append({"category": event["kind"], "detail": event.get("error")})
                if event["kind"] == "model_exchange" and event.get("error"):
                    errors.append({"category": "model_exchange", "detail": event["error"]})
                if event["kind"] == "ack":
                    errors.extend({"category": "engine_order_refusal", "detail": r.get("error")}
                                  for r in event.get("ack", {}).get("results", [])
                                  if not r.get("ok"))
        for source, label in ((manifest, "job"), (result or {}, "episode")):
            if source.get("error"):
                errors.append({"category": label, "detail": source["error"]})
        for label in ("recording", "imagery"):
            artifact = (result or {}).get(label) or {}
            if artifact.get("status") not in (None, "copied"):
                errors.append({"category": label, "detail": artifact})
        for shot in read_json(directory / "episode-0000/stills.json") or []:
            if shot.get("status") != "captured":
                errors.append({"category": "screenshot", "detail": shot})
        config = manifest.get("config") or {}
        result_battle = (result or {}).get("battle")
        if result_battle and traced_battle and result_battle != traced_battle:
            trace_mismatch = True
        matches = (manifest.get("source_revision") == plan["source_revision"]
                   and config.get("scenario") == scenario
                   and manifest.get("scenario") == profile
                   and config.get("policy") == job["controller"]
                   and (not result or result.get("policy") == job["controller"])
                   and config.get("episodes") == 1 and not trace_mismatch)
        if manifest and not matches:
            errors.append({"category": "provenance",
                           "detail": "source/profile/controller/battle differs"})
        measured = evaluate(result)
        recorded_outcome = measured["outcome"]
        if not matches:
            measured = evaluate(None)
        if result and not measured["outcome"]:
            errors.append({"category": "incomplete", "detail": result.get("status")})
        if measured["outcome"] and measured["condition"] is None:
            errors.append({"category": "measurement", "detail": measured["unavailable"]})
        rows.append({"output": str(directory), "controller": job["controller"],
                     "scenario": scenario, "arm": job.get("arm"),
                     "started": bool(result_battle or traced_battle),
                     "status": (result or manifest).get("status", "never_started"),
                     "source_revision": manifest.get("source_revision"),
                     "evidence_matches_plan": matches,
                     "recorded_controller": config.get("policy"),
                     "recorded_engine_outcome": recorded_outcome,
                     "engine_ending": (result or {}).get("engine_ending"),
                     "queue_execution": execution,
                     "not_started_reason": (state.get("error") or state.get("stopped")
                                            or "queue has not reached this attempt")
                     if not (result_battle or traced_battle) else None,
                     "llm": (result or {}).get("llm"), "errors": errors, **measured})
    counts = Counter(row["outcome"] for row in rows if row["outcome"])
    completed = sum(counts.values())
    return {"version": plan["benchmark"], "plan": str(plan_path.resolve()), "queue_state": state,
            "planned": len(rows),
            "started": sum(r["started"] for r in rows), "completed": completed,
            "engine_completed": sum(bool(r["recorded_engine_outcome"]) for r in rows),
            "never_started": sum(not r["started"] for r in rows),
            "outcomes": {key: counts[key] for key in OUTCOMES},
            "win_rate_completed": counts["won"] / completed if completed else None,
            "completion_rate": completed / len(rows) if rows else None,
            "error_categories": dict(Counter(e["category"] for row in rows for e in row["errors"])),
            "rows": rows}


def report(plan_path: Path, output: Path) -> dict:
    from twwarhammer3.battle import report as trials
    from twwarhammer3.battle import report_html

    if json.loads(plan_path.read_text()).get("benchmark") == SUITE:
        from twwarhammer3.battle import suite

        return suite.report([plan_path], output)
    visual = trials.collect([], benchmark_plans=[plan_path])
    data = visual["benchmark_plans"][0]
    text = (f"{VERSION}: {data['completed']}/{data['planned']} engine-completed; "
            f"{data['never_started']} never started; outcomes {data['outcomes']}.\n"
            "Rank completed battles by win > draw > loss, then own condition; "
            "unavailable condition has no tie-break. No aggregate controller ranking.\n"
            "Error categories count recorded events, which can describe the same failure.\n")
    for row in data["rows"]:
        text += (f"{row['controller']}: {row['outcome'] or row['status']}; "
                 f"condition {row['condition']}; errors {len(row['errors'])}; {row['output']}\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    def artifact(suffix):
        return output.with_name(output.name + suffix)

    report_html.write(artifact(".html"), visual)
    write_json(artifact(".json"), data)
    artifact(".txt").write_text(text)
    return data
