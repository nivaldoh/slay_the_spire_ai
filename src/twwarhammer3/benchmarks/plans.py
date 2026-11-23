"""Benchmark plans: write a frozen plan of play jobs, then read every planned attempt back.

Layout follows SWE-bench's swebench/harness/reporting.py: enumerate the frozen plan, then join
evidence, keeping missing attempts. No donor code. The plan's report is report.plan_report
(mirror) or suite.report (coordination suite).
"""

import argparse
import json
import math
import subprocess
from collections import Counter
from pathlib import Path

from gameai.provenance import REPO_ROOT, write_json
from twwarhammer3.battle import setup
from twwarhammer3.benchmarks.exact_stats import win_rate_if_resolved
from twwarhammer3.benchmarks.profile import (
    EFFORT,
    LAUNCH_ARGS,
    MODEL,
    OUTCOMES,
    SCENARIO,
    SUITE,
    VERSION,
    evaluate,
    recorded_outcome,
)


def make_plan(output: Path, stage: str, budget_usd: float) -> dict:
    """Write a queue plan without launching or paying; the existing queue executes it once."""
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
                *LAUNCH_ARGS]
        jobs.append({"output": str(directory.resolve()), "args": args, "controller": controller})
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       cwd=REPO_ROOT, text=True).strip()
    plan = {"benchmark": VERSION, "source_revision": revision, "stage": stage,
            "scenario": setup.scenarios()[SCENARIO],
            "purpose": "exploratory initial mirror benchmark; no reliable ranking claim",
            "preparation_usd": 0, "cumulative_ledger_cap_usd": budget_usd,
            "keep_going": stage == "model", "jobs": jobs}
    write_json(output, plan)
    return plan


def read_json(path):
    return json.loads(path.read_text()) if path.exists() else None


def controller_matches(job, config):
    """Compare the controller's explicit plan options; old plans may omit these arguments.

    Graph paths identify the declared artifact. Older plans did not freeze content hashes,
    so this cannot detect an artifact edited in place.
    """
    # Match play's argparse spelling rules, including unambiguous option prefixes.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--provider")
    parser.add_argument("--controller-config")
    expected, _ = parser.parse_known_args(list(map(str, job.get("args") or [])))
    if expected.provider is not None and config.get("provider") != expected.provider:
        return False
    if expected.controller_config is not None:
        actual = config.get("controller_config")
        if (not actual or (REPO_ROOT / actual).resolve()
                != (REPO_ROOT / expected.controller_config).resolve()):
            return False
    return config.get("policy") == job["controller"]


def attempt_counts(rows: list[dict]) -> dict:
    """Account for planned rows after the caller attributes or deduplicates evidence."""
    outcomes = Counter(row["outcome"] for row in rows if row["outcome"])
    completed = sum(outcomes.values())
    started = sum(bool(row.get("started", row["outcome"])) for row in rows)
    # JUDGEMENT: Unresolved plan count — Codex, 2026-11-23: count matched result labels.
    # Counting trace-only starts or foreign records would change the reported unresolved total.
    labels = Counter(row.get("outcome_label") for row in rows)
    # JUDGEMENT: Outside the win rate — Codex, 2026-11-23: all attempts without a counted ending.
    # Restricting this count to setup and provenance failures would omit other excluded attempts.
    excluded = len(rows) - completed
    return {
        "planned": len(rows), "started": started, "never_started": len(rows) - started,
        "engine_completed": sum(bool(row.get("recorded_engine_outcome", row["outcome"]))
                                for row in rows),
        "completed": completed, "excluded": excluded,
        "forfeited": labels["forfeit"], "unresolved": labels["unresolved"],
        "outcomes": {key: outcomes[key] for key in OUTCOMES},
    }


def collect(plan_path: Path) -> dict:
    """One row per planned attempt, including queue failures before an episode exists."""
    plan = json.loads(plan_path.read_text())
    if plan.get("benchmark") not in (VERSION, SUITE):
        raise ValueError("not a benchmark plan")
    expected_profile = plan.get("scenario")
    if expected_profile is None and plan["benchmark"] == VERSION:
        # Earlier initial plans named only the source. Read that frozen profile rather
        # than silently judging an old attempt against today's changed settings. Those
        # revisions all predate the 2026-11-15 split of that file into scenarios/.
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
        resolved = directory.resolve()
        manifest = read_json(directory / "manifest.json") or {}
        result = read_json(directory / "episode-0000/result.json")
        errors = []
        execution = executions.get(str(resolved))
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
                    if (observed.get("job") in (directory.name, resolved.name)
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
                   and controller_matches(job, config)
                   and (not result or result.get("policy") == job["controller"])
                   and config.get("episodes") == 1 and not trace_mismatch)
        if manifest and not matches:
            errors.append({"category": "provenance",
                           "detail": "source/profile/controller/battle differs"})
        measured = evaluate(result)
        recorded = recorded_outcome(result)
        if not matches:
            measured = {**evaluate(None), "outcome_label": None}
        if result and not measured["outcome"]:
            errors.append({"category": "incomplete", "detail": result.get("status")})
        if measured["outcome"] and measured["condition"] is None:
            errors.append({"category": "measurement", "detail": measured["unavailable"]})
        # evaluate skips a trial stopped during its final copying; recorded_engine_outcome
        # keeps what the engine ended.
        if (result or {}).get("interrupted_copy"):
            errors.append({"category": "interrupted_copy", "detail": result["interrupted_copy"]})
        # Match the path used by report.collect for this recording, including symlink aliases.
        rows.append({"output": str(resolved if matches else directory),
                     "controller": job["controller"],
                     "scenario": scenario, "arm": job.get("arm"),
                     "started": bool(result_battle or traced_battle),
                     "status": (result or manifest).get("status", "never_started"),
                     "source_revision": manifest.get("source_revision"),
                     "evidence_matches_plan": matches,
                     "recorded_controller": config.get("policy"),
                     "recorded_engine_outcome": recorded,
                     "engine_ending": (result or {}).get("engine_ending"),
                     "queue_execution": execution,
                     "not_started_reason": (state.get("error") or state.get("stopped")
                                            or "queue has not reached this attempt")
                     if not (result_battle or traced_battle) else None,
                     "llm": (result or {}).get("llm"), "errors": errors, **measured})
    counts = attempt_counts(rows)
    wins, completed = counts["outcomes"]["won"], counts["completed"]
    return {"version": plan["benchmark"], "plan": str(plan_path.resolve()), "queue_state": state,
            **counts,
            "win_rate_completed": wins / completed if completed else None,
            "win_rate_if_resolved": win_rate_if_resolved(wins, completed, counts["unresolved"]),
            "completion_rate": completed / len(rows) if rows else None,
            "error_categories": dict(Counter(e["category"] for row in rows for e in row["errors"])),
            "rows": rows}
