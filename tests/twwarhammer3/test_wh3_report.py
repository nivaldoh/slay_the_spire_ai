"""The paired benchmark collector and its text rendering in twwarhammer3/battle/report.py."""
import json

import pytest
from wh3_fixtures import make_job

from twwarhammer3.battle import report


def test_report_clusters_repeats_and_exposes_failures_missing_pairs_and_versions(tmp_path):
    a = make_job(tmp_path, "a", [("hold", -.1, "lost"), ("skills", .1, "won"),
                                 ("skills", .3, "won")])
    b = make_job(tmp_path, "b", [("hold", -.2, "lost"), ("skills", .1, "won")])
    c = make_job(tmp_path, "c", [("hold", 0, "policy_failure")])
    other = make_job(tmp_path, "other", [("hold", 0, "won")], revision="r2")
    result = report.collect([a, b, c, other, a])
    assert len(result["groups"]) == 2
    group = result["groups"][0]
    assert len(group["trials"]) == 6
    hold, skills = group["controllers"]
    assert hold["trials"] == 3 and hold["valid"] == 2
    assert hold["outcomes"]["policy_failure"] == 1
    assert skills["win_ci95"] is None  # correlated repeated wins cannot be independent samples
    comparison = group["paired"][0]
    assert comparison["n"] == 2 and comparison["mean"] == pytest.approx(-.3)
    assert comparison["unpaired_instances"] == [str(c.resolve())]
    assert "Paired active-strength" in report.render(result)


def test_intervals_and_missing_active_strength():
    assert report.wilson(0, 0) is None
    assert report.wilson(0, 10)[1] == pytest.approx(.27754, abs=1e-5)
    assert report.mean_interval([1])["ci95"] is None
    summary = report.mean_interval([0, 1, 2])
    assert summary["mean"] == 1
    assert summary["ci95"][1] == pytest.approx(1 + 4.303 / (3 ** .5))


def test_start_flag_sensitivity_keeps_primary_trials_and_deltas(tmp_path):
    jobs = [make_job(tmp_path, name, [("hold", 0, "lost"), ("skills", margin, "won")])
            for name, margin in (("a", .1), ("b", .2), ("flagged", .5))]
    path = jobs[-1] / "episode-0001/result.json"
    comparison = {"flagged": True, "units": {"friendly/f1": {"distance_m": 4.8}}}
    path.write_text(json.dumps({**json.loads(path.read_text()), "start_comparison": comparison}))
    result = report.collect(jobs)
    group = result["groups"][0]
    assert len(group["trials"]) == 6
    assert group["trials"][-1]["start_comparison"] == comparison
    assert group["controllers"][1]["start_flagged_trials"] == 1
    paired = group["paired"][0]
    assert paired["n"] == 3 and paired["mean"] == pytest.approx(-.8 / 3)
    sensitivity = paired["without_flagged_starts"]
    assert sensitivity["n"] == 2 and sensitivity["mean"] == pytest.approx(-.15)
    assert sensitivity["excluded_instances"] == [str(jobs[-1].resolve())]
    assert "Primary results above retain these launches" in report.render(result)


def test_report_distinguishes_snapshot_age_from_command_age_and_missing_timestamps(tmp_path):
    events = [
        {"kind": "decision", "time_ms": 5000, "decision_time_ms": 13000},
        {"kind": "ack", "ack": {"results": [{"ok": True}]},
         "latency": {"delay_ms": 15000}},
        {"kind": "decision", "time_ms": 20000, "decision_time_ms": 26000},
        {"kind": "decision", "time_ms": 30000},  # legacy record: age unknown
    ]
    (tmp_path / "trace.jsonl").write_text("".join(json.dumps(event) + "\n" for event in events))
    metrics = report.trial_metrics(tmp_path, {})
    assert metrics["snapshot_age_at_decision_s"]["n"] == 2
    assert metrics["snapshot_age_at_decision_s"]["mean"] == 7
    assert metrics["order_age_s"]["mean"] == 15


def test_rollout_throughput_includes_setup_failures_and_unknown_job_duration(tmp_path):
    played = make_job(tmp_path, "played", [("hold", 0, "lost"), ("skills", .2, "won")])
    failed = make_job(tmp_path, "failed", [])
    for job, status, wall in ((played, "completed", 3600), (failed, "setup_failure", 1800)):
        path = job / "manifest.json"
        manifest = json.loads(path.read_text())
        path.write_text(json.dumps({**manifest, "status": status, "wall_seconds": wall}))
    result = report.collect([played, failed])
    assert result["throughput"] == {"started_trials": 2, "valid_trials": 2, "job_wall_s": 5400,
                                    "valid_trials_per_wall_hour": pytest.approx(4 / 3)}
    assert "including setup, resets and failures; 1.33 valid trials/h" in report.render(result)
    partial = make_job(tmp_path, "partial", [])
    result = report.collect([played, failed, partial])
    assert result["throughput"]["valid_trials_per_wall_hour"] is None
    assert "throughput unavailable" in report.render(result)


def test_timer_win_retains_engine_outcome_and_labels_non_timer_win_rate(tmp_path):
    job = make_job(tmp_path, "timer", [("hold", -.7, "won")])
    path = job / "episode-0000/result.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "ended_by": "time_limit",
                                "battle_ms": 247700}))
    result = report.collect([job])
    group = result["groups"][0]
    trial = group["trials"][0]
    assert trial["outcome"] == "time_limit" and trial["engine_outcome"] == "won"
    assert trial["battle_ms"] == 247700  # the report's durations use the battle clock in ms
    assert trial["valid"]
    controller = group["controllers"][0]
    assert controller["win_rate"] == 0
    assert controller["time_limit_engine_outcomes"] == {"won": 1}
    text = report.render(result)
    assert "Non-timer win rate" in text and "time_limit (engine won)" in text


def test_typical_order_delay_is_the_median_of_per_trial_medians_and_jobs_keep_their_start(
        tmp_path):
    job = make_job(tmp_path, "ages", [("hold", 0, "won")] * 3)
    manifest = json.loads((job / "manifest.json").read_text())
    manifest["created_at"] = "2026-10-15T01:00:00Z"
    (job / "manifest.json").write_text(json.dumps(manifest))
    for episode, delays in (("episode-0000", [1000, 3000, 9000]), ("episode-0001", [5000])):
        acks = [{"kind": "ack", "ack": {"results": [{"ok": True}]}, "latency": {"delay_ms": delay}}
                for delay in delays] + [{"kind": "ack", "ack": {"results": []},
                                         "latency": {"delay_ms": 60000}}]  # empty: no age
        (job / episode / "trace.jsonl").write_text("".join(json.dumps(a) + "\n" for a in acks))
    result = report.collect([job])
    assert result["groups"][0]["controllers"][0]["order_age_median_s"] == 4  # median of 3 and 5
    assert result["jobs"][0]["created_at"] == "2026-10-15T01:00:00Z"
    assert report.collect([make_job(tmp_path, "none", [("hold", 0, "won")])])["groups"][0][
        "controllers"][0]["order_age_median_s"] is None
