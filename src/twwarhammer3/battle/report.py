"""Recompute benchmark comparisons from trials, clustered by launch instance.

Repeated rematches of one controller are averaged within their instance for paired
inference. Incompatible scenario definitions, builds and source revisions never pool.
Small samples are exploratory; no missing active-strength value is imputed.
"""

import itertools
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from twwarhammer3.battle.stats import active_left

OUTCOMES = {"won", "lost", "draw"}
T95 = (0, 12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262,
       2.228, 2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093,
       2.086, 2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042)


def mean_interval(values: list[float]) -> dict:
    n = len(values)
    result = {"n": n, "mean": statistics.mean(values) if n else None, "ci95": None,
              "detectable_difference_80pct": None}
    if n > 1:
        error = statistics.stdev(values) / math.sqrt(n)
        # Conservative critical value beyond the table's 30 degrees of freedom.
        critical = T95[min(n - 1, 30)]
        result["ci95"] = [result["mean"] - critical * error, result["mean"] + critical * error]
        result["detectable_difference_80pct"] = (critical + 0.842) * error
    return result


def wilson(wins: int, count: int) -> list[float] | None:
    if not count:
        return None
    z, p = 1.96, wins / count
    scale = 1 + z * z / count
    centre = (p + z * z / (2 * count)) / scale
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / scale
    return [max(0, centre - radius), min(1, centre + radius)]


def trial_metrics(directory: Path, result: dict) -> dict:
    kinds, rejections, ages, plan_ages, calls, snapshot_ages = Counter(), Counter(), [], [], [], []
    processing, models, seen_calls = [], set(), set()
    trace = directory / "trace.jsonl"
    if trace.exists():
        with trace.open() as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except ValueError:
                    kinds["incomplete_trace_lines"] += 1
                    continue
                kind = event.get("kind")
                if kind == "decision":
                    kinds["logged_decisions"] += 1
                    kinds["orders"] += len(event.get("orders") or [])
                    if (event.get("decision_time_ms") is not None
                            and event.get("time_ms") is not None):
                        snapshot_ages.append((event["decision_time_ms"] - event["time_ms"]) / 1000)
                    meta = event.get("behavior") or {}
                    if meta.get("plan_age_s") is not None:
                        plan_ages.append(meta["plan_age_s"])
                    for attempt in meta.get("attempts") or []:
                        response_id = attempt.get("response_id")
                        if response_id and response_id in seen_calls:
                            continue
                        if response_id:
                            seen_calls.add(response_id)
                        if attempt.get("seconds") is not None:
                            calls.append(attempt["seconds"])
                        if attempt.get("provider_processing_ms") is not None:
                            processing.append(attempt["provider_processing_ms"] / 1000)
                        if attempt.get("actual_model"):
                            models.add(attempt["actual_model"])
                elif kind == "ack":
                    # Empty batches do not count as action latency.
                    if (event.get("ack") or {}).get("results"):
                        ages.append(event["latency"]["delay_ms"] / 1000)
                    for order in event["ack"].get("results") or []:
                        if not order.get("ok"):
                            rejections["engine: " + str(order.get("error", "unknown"))] += 1
                elif kind == "invalid":
                    rejections["validation: " + str(event.get("error", "unknown"))] += 1
    own, enemy = active_left(result, "friendly"), active_left(result, "enemy")
    duration = (result.get("battle_ms", 0) - result.get("start_time_ms", 0)) / 1000
    return {
        "margin": own - enemy if own != "" and enemy != "" else None,
        "order_age_s": distribution(ages), "plan_age_s": distribution(plan_ages),
        "snapshot_age_at_decision_s": distribution(snapshot_ages),
        "call_seconds": distribution(calls), "rejections": dict(rejections),
        "provider_processing_seconds": distribution(processing), "actual_models": sorted(models),
        "decisions_per_battle_s": result.get("decisions", 0) / duration if duration > 0 else None,
        "trace": dict(kinds),
    }


def distribution(values: list[float]) -> dict:
    ordered = sorted(values)
    return {"n": len(values), "mean": statistics.mean(values) if values else None,
            "p50": statistics.median(values) if values else None,
            "p90": ordered[math.ceil(len(values) * 0.9) - 1] if values else None}


def collect(jobs: list[Path]) -> dict:
    groups = defaultdict(list)
    seen = set()
    job_records = []
    for job in jobs:
        job = job.resolve()
        if job in seen:
            continue
        seen.add(job)
        manifest = json.loads((job / "manifest.json").read_text())
        config = manifest["config"]
        scenario = manifest.get("scenario") or {}
        job_records.append({"instance": str(job), "recorded_status": manifest.get("status"),
                            "created_at": manifest.get("created_at"),
                            "planned_trials": manifest.get("trials"),
                            "wall_seconds": manifest.get("wall_seconds"),
                            "setup_checks": manifest.get("setup_checks"),
                            "error": manifest.get("error")})
        environment_path = job / "environment.json"
        environment = json.loads(environment_path.read_text()) if environment_path.exists() else {}
        signature = json.dumps({"scenario": scenario, "source": manifest.get("source_revision"),
                                "game": environment.get("game"),
                                "track": manifest.get("track"),
                                "recorder": manifest.get("recorder"),
                                "imagery": manifest.get("imagery"),
                                "observe_ms": config.get("observe_ms"),
                                "tick_ms": config.get("tick_ms"),
                                "interval_ms": config.get("interval_ms"),
                                "model": config.get("model"), "effort": config.get("effort")},
                               sort_keys=True)
        # Retain setup-only jobs in graphical reports, including their historical
        # scenario. These fields are additive; the statistics below are unchanged.
        job_records[-1]["definition"] = json.loads(signature)
        job_records[-1]["provenance"] = {
            "prompt_sha256": {key: value for key, value in manifest.items()
                              if key.endswith("prompt_sha256")},
            "source_files": manifest.get("source_files"),
        }
        for directory in sorted(job.glob("episode-*")):
            if not directory.is_dir():
                continue
            path = directory / "result.json"
            index = int(directory.name.split("-")[-1])
            declared = (manifest.get("trials") or [{}] * (index + 1))[index]
            result = json.loads(path.read_text()) if path.exists() else {"status": "missing_result"}
            policy = result.get("policy", declared.get("policy", config["policy"]))
            delay = result.get("delay_ms", declared.get("delay_ms", 0))
            label = f"{policy} / +{delay / 1000:g}s"
            card = result.get("card") or {}
            if card.get("kind") == "external":
                label += " / " + str(card.get("source_sha256", "unknown"))[:12]
            outcome = "time_limit" if result.get("ended_by") == "time_limit" else result["status"]
            metrics = trial_metrics(directory, result)
            protected = scenario.get("protected") or []
            totals = (result.get("final") or {}).get("friendly", {}).get("by_type") or {}
            denominator = sum(totals.get(key, {}).get("men0", 0) for key in protected)
            protected_left = (sum(totals.get(key, {}).get("active_men", 0) for key in protected)
                              / denominator if denominator else None)
            groups[signature].append({
                "instance": str(job), "episode": directory.name, "controller": label,
                "policy": policy, "delay_ms": delay, "outcome": outcome,
                "engine_outcome": result["status"] if result["status"] in OUTCOMES else None,
                "ended_by": result.get("ended_by"),
                "valid": result["status"] in OUTCOMES,
                "setup_checked": bool(manifest.get("setup_checks") and result.get("setup_checks")),
                "start_flagged": (result.get("start_comparison") or {}).get("flagged"),
                "start_comparison": result.get("start_comparison"),
                "card": result.get("card"), "metrics": metrics, "protected_left": protected_left,
                "objectives": result.get("objectives"), "llm": result.get("llm") or {},
                "wall_s": result.get("elapsed_seconds"), "battle_s": result.get("battle_s"),
                "battle_ms": result.get("battle_ms"),
                "clock_ratio": result.get("clock_ratio"),
                "error": result.get("error"),
            })
    output = []
    for signature, trials in groups.items():
        controllers = sorted({trial["controller"] for trial in trials})
        summaries, paired = [], []
        for controller in controllers:
            items = [trial for trial in trials if trial["controller"] == controller]
            outcomes = Counter(trial["outcome"] for trial in items)
            valid = sum(trial["valid"] for trial in items)
            instance_counts = Counter(trial["instance"] for trial in items if trial["valid"])
            means = {}
            for field in ("margin", "decisions_per_battle_s"):
                values = [trial["metrics"][field] for trial in items
                          if trial["metrics"][field] is not None
                          and (field != "margin" or trial["valid"])]
                means[field] = statistics.mean(values) if values else None
            for field in ("order_age_s", "plan_age_s", "call_seconds",
                          "snapshot_age_at_decision_s"):
                values = [trial["metrics"][field]["mean"] for trial in items
                          if trial["metrics"][field]["mean"] is not None]
                means[field] = statistics.mean(values) if values else None
            for field in ("victory_held", "key_held", "supplies_left"):
                values = [(trial.get("objectives") or {}).get(field) for trial in items
                          if trial["valid"]]
                values = [value for value in values if value is not None]
                means[field] = statistics.mean(values) if values else None
            # Typical order delay: the median of each battle's median order age.
            medians = [trial["metrics"]["order_age_s"]["p50"] for trial in items
                       if trial["metrics"]["order_age_s"]["p50"] is not None]
            summaries.append({
                "controller": controller, "trials": len(items), "valid": valid,
                "instances": len({trial["instance"] for trial in items}),
                "outcomes": dict(outcomes), "win_rate": outcomes["won"] / valid if valid else None,
                "time_limit_engine_outcomes": dict(Counter(
                    trial["engine_outcome"] for trial in items
                    if trial["outcome"] == "time_limit" and trial["engine_outcome"])),
                # Wilson assumes one Bernoulli trial per instance. Do not report it
                # on correlated rematch repeats; retain the raw rate and denominator.
                "win_ci95": wilson(outcomes["won"], valid)
                if max(instance_counts.values(), default=0) <= 1 else None,
                "usd": sum(trial["llm"].get("usd", 0) for trial in items),
                "wall_s": sum(trial["wall_s"] or 0 for trial in items),
                "unchecked_trials": sum(not trial["setup_checked"] for trial in items),
                "start_flagged_trials": sum(bool(trial["start_flagged"]) for trial in items),
                "means": means,
                "order_age_median_s": statistics.median(medians) if medians else None,
                "input_tokens": sum(trial["llm"].get("input_tokens", 0) for trial in items),
                "output_tokens": sum(trial["llm"].get("output_tokens", 0) for trial in items),
            })
        flagged_instances = {trial["instance"] for trial in trials if trial["start_flagged"]}
        for a, b in itertools.combinations(controllers, 2):
            instances = defaultdict(lambda: defaultdict(list))
            for trial in trials:
                margin = trial["metrics"]["margin"]
                if trial["controller"] in (a, b) and trial["valid"] and margin is not None:
                    instances[trial["instance"]][trial["controller"]].append(margin)
            differences = {instance: statistics.mean(values[a]) - statistics.mean(values[b])
                           for instance, values in instances.items() if a in values and b in values}
            unflagged = {instance: value for instance, value in differences.items()
                         if instance not in flagged_instances}
            paired.append({"a": a, "b": b, **mean_interval(list(differences.values())),
                           "differences_by_instance": differences,
                           "without_flagged_starts": {
                               **mean_interval(list(unflagged.values())),
                               "differences_by_instance": unflagged,
                               "excluded_instances": sorted(
                                   differences.keys() & flagged_instances)},
                           "unpaired_instances": sorted(set(t["instance"] for t in trials)
                                                        - differences.keys())})
        output.append({"definition": json.loads(signature), "controllers": summaries,
                       "paired": paired, "trials": trials})
    trials = [trial for group in output for trial in group["trials"]]
    valid = sum(trial["valid"] for trial in trials)
    walls = [job["wall_seconds"] for job in job_records]
    total_wall = sum(walls) if all(value is not None for value in walls) else None
    throughput = {"started_trials": len(trials), "valid_trials": valid,
                  "job_wall_s": total_wall,
                  "valid_trials_per_wall_hour": valid * 3600 / total_wall if total_wall else None}
    return {"schema": 1, "groups": output, "jobs": job_records,
            "throughput": throughput,
            "limitations": "Exploratory comparisons. Whole latency includes network and retries. "
            "Added age is a minimum: available buffered snapshots can be older, especially "
            "when a synchronous controller blocks observation reads. Actual age at decision "
            "and at order issuance are reported separately. "
            "Orders are issued/queued, not confirmed to have taken effect. Engine timing has a "
            "roughly 0.3 s floor. Visibility-filtered observations are not verified "
            "player-equivalent. "
            "Active margin counts routing/shattered men as lost but does not weight unit value. "
            "Pair intervals use launch means (Student t), not independent rematches. "
            "A detectable difference is an approximate 80%-power estimate from the observed SD; "
            "a null result does not establish no latency effect. "
            "Provider costs can be self-reported. "
            "Inspect setup checks, start flags and missing pairs before drawing conclusions."}


def render(report: dict) -> str:
    lines = [f"Job {Path(job['instance']).name}: recorded status {job['recorded_status']}; "
             f"error={job['error'] or 'none'}" for job in report.get("jobs", [])]
    throughput = report.get("throughput") or {}
    rate, wall = throughput.get("valid_trials_per_wall_hour"), throughput.get("job_wall_s")
    if wall is not None:
        frequency = f"{rate:.2f}" if rate is not None else "unavailable"
        lines += ["", f"All supplied jobs: {throughput['valid_trials']} valid / "
                  f"{throughput['started_trials']} started trials; {wall / 3600:.2f} job wall h "
                  f"including setup, resets and failures; {frequency} valid trials/h."]
    else:
        lines += ["", "Whole-job throughput unavailable: at least one job lacks final wall timing."]
    lines.append("")
    for group in report["groups"]:
        definition = group["definition"]
        scenario = definition["scenario"]
        lines += [f"Scenario: {scenario.get('name') or scenario.get('map', 'unlabelled')}; "
                  f"source {str(definition['source'])[:7]}", "",
                  "| Controller / added age | Instances | Started | Valid | W/L/D/time | Other | "
                  "Non-timer win rate [95% CI] | USD | Wall h | Unchecked |",
                  "|" + "---|" * 10]
        for row in group["controllers"]:
            outcomes = row["outcomes"]
            rate = row["win_rate"]
            interval = row["win_ci95"]
            ci = f" [{interval[0]:.2f}, {interval[1]:.2f}]" if interval else " [unavailable]"
            lines.append("| " + " | ".join([
                row["controller"], str(row["instances"]), str(row["trials"]), str(row["valid"]),
                "/".join(str(outcomes.get(key, 0))
                         for key in ("won", "lost", "draw", "time_limit")),
                str(row["trials"] - row["valid"]), f"{rate:.2f}{ci}" if rate is not None else "—",
                f"{row['usd']:.4f}", f"{row['wall_s'] / 3600:.2f}", str(row["unchecked_trials"]),
            ]) + " |")
        lines += ["", "Means: gameplay over valid trials; timing over all recorded trials. "
                  "Median order age: the median of each trial's median. "
                  "Unavailable values excluded.", "",
                  "| Controller | Margin | Decisions/s | Snapshot age at decision s | "
                  "Order age s | Median order age s | Plan age s | Call s | Victory held | "
                  "Key held | Supplies left | Tokens in/out |",
                  "|" + "---|" * 12]
        for row in group["controllers"]:
            means = {**row["means"], "median": row["order_age_median_s"]}
            values = [means[key] for key in
                      ("margin", "decisions_per_battle_s", "snapshot_age_at_decision_s",
                       "order_age_s", "median", "plan_age_s", "call_seconds", "victory_held",
                       "key_held", "supplies_left")]
            lines.append("| " + " | ".join([
                row["controller"],
                *(f"{value:.3f}" if value is not None else "—" for value in values),
                f"{row['input_tokens']}/{row['output_tokens']}",
            ]) + " |")
        lines += ["", "Paired active-strength margin (A minus B; one mean per launch):", "",
                  "| A | B | Paired instances | Mean | 95% CI | Detectable difference | Unpaired |",
                  "|" + "---|" * 7]
        for row in group["paired"]:
            ci = row["ci95"]
            difference = row["detectable_difference_80pct"]
            lines.append("| " + " | ".join([
                row["a"], row["b"], str(row["n"]),
                f"{row['mean']:.3f}" if row["mean"] is not None else "—",
                f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci else "unavailable",
                f"{difference:.3f}" if difference is not None else "unavailable",
                str(len(row["unpaired_instances"])),
            ]) + " |")
        for row in group["paired"]:
            sensitivity = row["without_flagged_starts"]
            if sensitivity["excluded_instances"]:
                ci = sensitivity["ci95"]
                interval = f"[{ci[0]:.3f}, {ci[1]:.3f}]" if ci else "unavailable"
                mean = sensitivity["mean"]
                lines += ["", "Sensitivity excluding launches with flagged starts: "
                          f"{row['a']} minus {row['b']}; n={sensitivity['n']}, "
                          f"mean={mean if mean is not None else 'unavailable'}, 95% CI {interval}. "
                          "Primary results above retain these launches."]
        lines += ["", "Trials (JSON report retains objective and rejection breakdowns):", ""]
        for trial in group["trials"]:
            age = trial["metrics"]["order_age_s"]["mean"]
            outcome = trial["outcome"]
            if outcome == "time_limit":
                outcome += f" (engine {trial['engine_outcome']})"
            lines.append(f"- {Path(trial['instance']).name}/{trial['episode']}: "
                         f"{trial['controller']}, {outcome}; "
                         f"order age {age if age is not None else 'unavailable'} s; "
                         f"start flagged={trial['start_flagged']}; "
                         f"error={trial['error'] or 'none'}")
        lines.append("")
    return "\n".join([*lines, report["limitations"]])
