"""Plan attribution and ledger/failure totals, from hand-built attempt records."""

import json

import pytest

from gameai.provenance import REPO_ROOT
from twwarhammer3.battle import benchmark, suite


def attempts(tmp_path, results, *, args=(), config=None):
    jobs = []
    for index, result in enumerate(results):
        directory = tmp_path / f"job-{index}"
        episode = directory / "episode-0000"
        episode.mkdir(parents=True)
        jobs.append({"output": str(directory), "scenario": "s", "controller": "configured",
                     "arm": "gap", "args": list(args)})
        (directory / "manifest.json").write_text(json.dumps({
            "source_revision": "frozen", "scenario": {}, "config": {
                "scenario": "s", "policy": "configured", "episodes": 1, **(config or {})}}))
        (episode / "result.json").write_text(json.dumps({
            "policy": "configured", "battle": f"b-{index}", **result}))
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"benchmark": benchmark.SUITE, "source_revision": "frozen",
                                "scenarios": {"s": {}}, "jobs": jobs}))
    return path


@pytest.mark.parametrize("field,actual", [
    ("provider", "openrouter"), ("provider", None),
    ("controller_config", "runs/different-graphs"), ("controller_config", None)])
def test_explicit_provider_and_graph_path_must_match_the_plan(tmp_path, field, actual):
    # benchmark-implementation.md: compare frozen complete controllers, including provider.
    config = {"provider": "anthropic", "controller_config": "runs/planned-graphs"}
    config[field] = actual
    plan = attempts(tmp_path, [{"status": "won"}], config=config, args=[
        "--provider", "anthropic", "--controller-config", "runs/planned-graphs"])
    data = benchmark.collect(plan)
    row, = data["rows"]
    assert not row["evidence_matches_plan"]
    assert row["outcome"] is None and row["recorded_engine_outcome"] == "won"
    assert data["engine_completed"] == 1 and data["completed"] == 0
    assert data["error_categories"]["provenance"] == 1


@pytest.mark.parametrize("equals", [False, True])
def test_equivalent_graph_paths_and_cli_spellings_still_match(tmp_path, equals):
    args = ["--provider", "anthropic", "--controller-config", "runs/planned-graphs"]
    if equals:
        args = ["--provider=anthropic", "--controller-config=runs/planned-graphs"]
    plan = attempts(tmp_path, [{"status": "won"}], args=args, config={
        "provider": "anthropic", "controller_config": str(REPO_ROOT / "runs/planned-graphs")})
    assert benchmark.collect(plan)["rows"][0]["evidence_matches_plan"]


@pytest.mark.parametrize("args", [["--prov", "anthropic"],
                                  ["--controller-c", "runs/planned-graphs"]])
def test_abbreviated_play_options_cannot_hide_a_foreign_controller(tmp_path, args):
    # Play uses argparse's unambiguous prefix syntax, even though generators use long names.
    plan = attempts(tmp_path, [{"status": "won"}], args=args, config={
        "provider": "openrouter", "controller_config": "runs/different-graphs"})
    assert not benchmark.collect(plan)["rows"][0]["evidence_matches_plan"]


def test_failure_totals_keep_incomplete_attempts_and_all_provider_faults(tmp_path):
    # $1 win plus $2 incomplete attempt = $3 per win. Each failure is distinct:
    # malformed model reply, transport failure, provider's failed response.
    plan = attempts(tmp_path, [
        {"status": "won", "llm": {"usd": 1}},
        {"status": "provider_error", "llm": {"usd": 2}, "failure": {"attempts": [
            {"response_id": "bad", "error": "invalid JSON"},
            {"transport_error": "HTTP 503"},
            {"response_id": "failed", "status": "failed", "error": "server_error"}]}}])
    data = suite.gather([plan])
    failed = data["rows"][1]
    assert failed["outcome"] is None
    assert failed["bad_replies"] == 1 and failed["call_failures"] == 2
    arm = data["summary"]["arms"]["gap"]
    assert arm["planned"] == 2 and arm["completed"] == arm["wins"] == 1
    assert arm["bad_replies"] == 1 and arm["call_failures"] == 2
    assert arm["usd_total"] == arm["usd_per_win"] == 3
    # Retaining failures must not turn them into invented losses.
    assert arm["losses"] == 0


def test_provider_failed_response_counts_even_when_battle_finishes(tmp_path):
    plan = attempts(tmp_path, [{"status": "won", "failure": {"attempts": [
        {"response_id": "failed", "status": "failed", "error": "server_error"}]}}])
    arm = suite.gather([plan])["summary"]["arms"]["gap"]
    assert arm["bad_replies"] == 0 and arm["call_failures"] == 1


def test_numeric_queue_arguments_use_the_same_spelling_as_at_launch(tmp_path):
    plan = attempts(tmp_path, [{"status": "won"}], args=[
        "--episodes", 1, "--provider", "anthropic"], config={"provider": "anthropic"})
    assert benchmark.collect(plan)["rows"][0]["evidence_matches_plan"]


def test_trace_failures_survive_a_missing_result_without_inventing_cost(tmp_path):
    plan = attempts(tmp_path, [{}])
    episode = tmp_path / "job-0/episode-0000"
    (episode / "result.json").unlink()
    events = [
        {"kind": "battle", "observation": {"job": "job-0", "battle": "b"}},
        {"kind": "model_exchange", "id": "bad", "attempts": [
            {"response_id": "bad", "error": "invalid JSON"}]},
        {"kind": "model_exchange", "id": "network", "attempts": [
            {"transport_error": "HTTP 503"}]}]
    (episode / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    data = suite.gather([plan])
    row, = data["rows"]
    assert row["started"] and row["evidence_matches_plan"]
    assert row["outcome"] is None and row["usd"] is None
    arm = data["summary"]["arms"]["gap"]
    assert arm["bad_replies"] == arm["call_failures"] == 1
    assert arm["completed"] == arm["losses"] == 0


@pytest.mark.parametrize("missing", ["own", "taken"])
def test_missing_tiebreak_cannot_become_a_zero_or_an_available_case_mean(missing):
    # Missing readings are unavailable (benchmark-implementation.md); zero is a real reading.
    complete = {"scenario": "s", "arm": "single", "outcome": "won", "own": 10, "taken": 20}
    unknown = {**complete, "arm": "team", missing: None}
    repeated = [unknown, {**complete, "arm": "team", "own": 0}]
    assert suite.scenario_value(repeated) == (1, None)
    pair = suite.paired([*repeated, complete], "team", "single", ["s"])
    assert (pair["better"], pair["worse"], pair["tied"], pair["unavailable"]) == (0, 0, 0, 1)
    assert pair["sign_test_p"] is None
    pair = suite.paired([{**unknown, missing: 0}, complete], "team", "single", ["s"])
    assert pair["worse"] == 1 and pair["unavailable"] == 0
    # Missing condition cannot discard a known difference in win rate.
    pair = suite.paired([unknown, {**complete, "outcome": "lost"}], "team", "single", ["s"])
    assert pair["better"] == 1 and pair["unavailable"] == 0


def test_report_flags_missing_comparison_and_keeps_known_wins(tmp_path):
    plan = attempts(tmp_path, [{"status": "won"}, {"status": "won"}])
    declared = json.loads(plan.read_text())
    declared["jobs"][1]["arm"] = "single"
    plan.write_text(json.dumps(declared))
    data = suite.report([plan], tmp_path / "report")
    assert data["completed"] == 2 and all(r["outcome"] == "won" for r in data["rows"])
    assert data["summary"]["arms"]["gap"]["paired"]["unavailable"] == 1
    assert "unavailable tie-break on 1" in (tmp_path / "report.txt").read_text()
