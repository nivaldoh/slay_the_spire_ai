"""A missing result is not a missing start; partial and stopped traces retain identity."""
import json

import pytest

from twwarhammer3.battle import benchmark, setup


def pending_attempt(tmp_path, *, terminal=False, trace_job=None):
    job = tmp_path / "attempt"
    episode = job / "episode-0000"
    episode.mkdir(parents=True)
    profile = setup.scenarios()[benchmark.SCENARIO]
    plan = {"benchmark": benchmark.VERSION, "source_revision": "frozen", "scenario": profile,
            "jobs": [{"output": str(job), "controller": "hold"}]}
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    (job / "manifest.json").write_text(json.dumps({
        "source_revision": "frozen", "scenario": profile, "status": "running",
        "config": {"scenario": benchmark.SCENARIO, "policy": "hold", "episodes": 1}}))
    (episode / "trace.jsonl").write_text(json.dumps({"kind": "battle", "observation": {
        "job": trace_job or job.name, "battle": "battle-1", "phase": "Loading"}}) + "\n")
    if terminal:
        path.with_name("plan-state.json").write_text(json.dumps({
            "status": "failed", "completed": [{"output": str(job), "exit_code": 1}]}))
    return path


@pytest.mark.parametrize("terminal", [False, True])
def test_a_matching_battle_trace_counts_a_started_attempt_without_a_result(tmp_path, terminal):
    data = benchmark.collect(pending_attempt(tmp_path, terminal=terminal))
    assert data["planned"] == data["started"] == 1
    assert data["never_started"] == data["completed"] == 0
    assert data["rows"][0]["outcome"] is None and data["rows"][0]["condition"] is None
    assert data["rows"][0]["evidence_matches_plan"] is True
    assert "provenance" not in data["error_categories"]
    if terminal:
        assert data["rows"][0]["queue_execution"]["exit_code"] == 1
        assert data["error_categories"]["queue"] == 1


def test_a_foreign_battle_trace_cannot_start_this_attempt(tmp_path):
    data = benchmark.collect(pending_attempt(tmp_path, trace_job="other-job"))
    assert data["started"] == data["completed"] == 0
    assert data["rows"][0]["evidence_matches_plan"] is False
    assert data["error_categories"]["provenance"] == 1


def test_a_partial_final_trace_line_keeps_the_known_start_and_error(tmp_path):
    plan = pending_attempt(tmp_path, terminal=True)
    trace = tmp_path / "attempt/episode-0000/trace.jsonl"
    with trace.open("a") as stream:
        stream.write('{"kind":')
    data = benchmark.collect(plan)
    assert data["started"] == 1 and data["completed"] == 0
    assert data["error_categories"]["trace"] == 1
