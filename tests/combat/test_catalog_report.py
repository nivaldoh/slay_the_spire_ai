"""Catalog reports use real child audits with only the game transport substituted."""

import json
import shutil

import pytest
import test_catalog

from spire import provenance
from spire.combat import catalog, catalog_report
from spire.engine.bridge import BridgeDisconnected

declaration = test_catalog.declaration
runtime_harness = test_catalog.runtime_harness
run_setup = test_catalog.run_setup


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data))


def refill(runtime, output):
    for child in read(output / "catalog-manifest.json")["children"]:
        trace = output / child["directory"] / "episode-0000/trace.jsonl"
        runtime.sessions.append([
            event["raw"] for line in trace.read_text().splitlines()
            if (event := json.loads(line))["kind"] == "observation"
        ])


@pytest.fixture
def completed(run_setup):
    path, output, runtime = run_setup
    assert catalog.evaluate_catalog("random", path, output)["valid"]
    return path, output, runtime


def test_matching_schedules_allow_different_policies_and_report_equal_scenario_macro(completed):
    path, output, runtime = completed
    refill(runtime, output)
    other = output.with_name("heuristic")
    assert catalog.evaluate_catalog("heuristic", path, other)["valid"]
    report = catalog_report.compare_catalogs([output, other])
    assert report["valid"] and report["same_protocol"]
    assert report["comparison_issues"] == report["protocol_differences"] == []
    for run in report["runs"]:
        assert run["metrics"]["win_rate"] == 0.75  # Three Cultist wins, one Jaw Worm loss.
        assert run["macro"]["win_rate"] == 0.5  # Each of the two scenarios has equal weight.
        assert run["scenarios"]["cultist-a"]["metrics"]["wins"] == 3
        assert run["scenarios"]["jaw-a"]["metrics"]["losses"] == 1
    text = catalog_report.render_catalog_report(report)
    assert "Macro win rate" in text and "0.500" in text
    assert "cultist-a" in text and "jaw-a" in text
    assert "not a controlled comparison" not in text


def test_saved_summary_cannot_override_authoritative_child_audits(completed):
    _, output, _ = completed
    write(output / "catalog-evaluation.json", {"valid": True, "metrics": {"wins": 999}})
    report = catalog_report.compare_catalogs([output])
    assert report["valid"] and report["runs"][0]["metrics"]["wins"] == 3
    trace = output / "runs/attempt-0000/episode-0000/trace.jsonl"
    trace.write_text(trace.read_text() + "{}\n")
    changed = catalog_report.compare_catalogs([output])
    assert not changed["valid"] and not changed["same_protocol"]
    assert changed["runs"][0]["metrics"]["wins"] == 2
    assert changed["runs"][0]["macro"]["win_rate"] is None
    assert any("evidence" in issue.lower() for issue in changed["comparison_issues"])


def test_source_revision_may_change_between_matched_policy_evaluations(completed, monkeypatch):
    path, output, runtime = completed
    refill(runtime, output)
    monkeypatch.setattr(provenance.subprocess, "check_output", lambda command, **kwargs:
                        "b" * 40 if command[:3] == ["git", "rev-parse", "HEAD"] else "")
    other = output.with_name("new-policy-revision")
    assert catalog.evaluate_catalog("heuristic", path, other)["valid"]
    report = catalog_report.compare_catalogs([output, other])
    assert report["valid"] and report["same_protocol"]
    assert report["runs"][0]["source_revision"] != report["runs"][1]["source_revision"]


@pytest.mark.parametrize("change", ["game_seed", "policy_seed", "schedule_order"])
def test_completed_different_schedules_do_not_share_a_protocol(completed, change):
    path, output, runtime = completed
    refill(runtime, output)
    data = read(path)
    if change == "game_seed":
        data["scenarios"][0]["game_seed"] = "XYZ"
    elif change == "policy_seed":
        data["schedule"][0]["policy_seed"] = 20
    else:
        data["schedule"][0], data["schedule"][1] = data["schedule"][1], data["schedule"][0]
    write(path, data)
    other = output.with_name("different-schedule")
    assert catalog.evaluate_catalog("heuristic", path, other)["valid"]
    report = catalog_report.compare_catalogs([output, other])
    assert report["valid"] and not report["same_protocol"]
    assert "catalog" in report["protocol_differences"]
    assert "catalog_sha256" in report["protocol_differences"]


def test_fixed_catalog_hash_includes_snapshot_bytes(completed):
    path, output, runtime = completed
    refill(runtime, output)
    path.write_text(json.dumps(read(path), indent=2))
    other = output.with_name("different-bytes")
    assert catalog.evaluate_catalog("random", path, other)["valid"]
    report = catalog_report.compare_catalogs([output, other])
    assert report["valid"] and not report["same_protocol"]
    assert report["protocol_differences"] == ["catalog_sha256"]


def test_infrastructure_failure_keeps_attempts_and_unattempted_schedule_visible(run_setup):
    path, output, runtime = run_setup
    runtime.sessions[1] = [BridgeDisconnected("synthetic socket failure")]
    catalog.evaluate_catalog("random", path, output)
    report = catalog_report.compare_catalogs([output])
    assert not report["valid"] and not report["same_protocol"]
    run = report["runs"][0]
    assert run["metrics"]["infrastructure_failures"] == 1
    assert run["metrics"]["losses"] == 0
    assert run["attempts_started"] == 2 and run["unattempted"] == 2
    assert run["macro"]["win_rate"] is None
    assert any("Incomplete catalog" in issue for issue in report["comparison_issues"])
    text = catalog_report.render_catalog_report(report)
    assert "Infra failures" in text and "Unattempted" in text
    assert "not a controlled comparison" in text


def test_failure_before_child_evidence_still_reports_started_attempt(run_setup, monkeypatch):
    path, output, _ = run_setup

    def fail(*args, **kwargs):
        raise OSError("synthetic deployment failure")

    monkeypatch.setattr(catalog.evaluation, "evaluate", fail)
    catalog.evaluate_catalog("random", path, output)
    report = catalog_report.compare_catalogs([output])
    run = report["runs"][0]
    assert not report["same_protocol"]
    assert run["attempts_started"] == 1 and run["unattempted"] == 3
    assert run["metrics"]["losses"] == 0 and run["orchestration_failures"] == 1
    assert "Orchestration failures" in catalog_report.render_catalog_report(report)


def refresh_child_hashes(output):
    manifest = read(output / "catalog-manifest.json")
    for child in manifest["children"]:
        child["files"] = catalog._files(output / child["directory"])
    write(output / "catalog-manifest.json", manifest)


@pytest.mark.parametrize("field,value", [
    ("max_actions", 250), ("episode_timeout", 60), ("bridge_timeout", 15),
])
def test_changed_auditable_child_limits_break_comparability(completed, field, value):
    _, output, _ = completed
    other = output.with_name("other-limits")
    shutil.copytree(output, other)
    for child in read(other / "catalog-manifest.json")["children"]:
        path = other / child["directory"] / "manifest.json"
        data = read(path)
        data["config"][field] = value
        write(path, data)
    refresh_child_hashes(other)
    report = catalog_report.compare_catalogs([output, other])
    assert report["valid"] and not report["same_protocol"]
    assert "rollout_config" in report["protocol_differences"]


def test_mixed_child_limits_cannot_claim_even_one_complete_protocol(completed):
    _, output, _ = completed
    path = output / "runs/attempt-0001/manifest.json"
    data = read(path)
    data["config"]["max_actions"] = 250
    write(path, data)
    refresh_child_hashes(output)
    report = catalog_report.compare_catalogs([output])
    assert not report["same_protocol"]
    assert any("protocols differ within" in issue for issue in report["comparison_issues"])


def test_changed_engine_pins_break_comparability(completed):
    _, output, _ = completed
    other = output.with_name("other-engine")
    shutil.copytree(output, other)
    manifest = read(other / "catalog-manifest.json")
    manifest["engine_pins"]["game"] = test_catalog.digest("different-game")
    for child in manifest["children"]:
        path = other / child["directory"] / "environment.json"
        data = read(path)
        data["game"]["sha256"] = manifest["engine_pins"]["game"]
        write(path, data)
    write(other / "catalog-manifest.json", manifest)
    refresh_child_hashes(other)
    report = catalog_report.compare_catalogs([output, other])
    assert report["valid"] and not report["same_protocol"]
    assert "engine_pins" in report["protocol_differences"]


@pytest.mark.parametrize("field,value", [
    ("observation_version", "privileged-v2"), ("prefix_version", "unsettled-v1"),
    ("reset", "snapshot"), ("engine", "simulator"),
])
def test_child_contract_changes_are_rejected_by_authoritative_audit(completed, field, value):
    _, output, _ = completed
    path = output / "runs/attempt-0000/manifest.json"
    data = read(path)
    data[field] = value
    write(path, data)
    refresh_child_hashes(output)
    report = catalog_report.compare_catalogs([output])
    assert not report["valid"] and not report["same_protocol"]
    assert report["comparison_issues"]


def test_report_handles_missing_catalog_and_empty_comparison(tmp_path):
    result = catalog_report.compare_catalogs([tmp_path / "missing"])
    assert not result["valid"] and not result["same_protocol"]
    assert "Cannot audit catalog" in catalog_report.render_catalog_report(result)
    result = catalog_report.compare_catalogs([])
    assert not result["valid"] and not result["same_protocol"]
