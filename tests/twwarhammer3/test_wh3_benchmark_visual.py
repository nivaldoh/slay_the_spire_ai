"""The mirror contract presented through the existing report, independently of legacy scores."""

import json
from copy import deepcopy

from wh3_fixtures import configured_job, embedded

from twwarhammer3.battle import benchmark, report, report_html


def mirror_job(tmp_path, name, *, version=5, hp=.6, outcome="lost"):
    scenario = {"name": benchmark.SCENARIO, "benchmark": benchmark.VERSION,
                "scenario_version": version, "brief": "Win the battle."}
    job = configured_job(tmp_path, name, scenario=scenario)
    path = job / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["config"].update(policy="llm_rules", scenario=benchmark.SCENARIO, episodes=1)
    path.write_text(json.dumps(manifest))
    path = job / "episode-0000/result.json"
    result = json.loads(path.read_text())
    result.update(status=outcome, battle=name, engine_ending={"result": outcome},
                  start={"friendly": {f"f{i}": {} for i in range(1, 6)}},
                  benchmark={"version": benchmark.VERSION, "units": [
                      {"id": f"f{i}", "hp": hp, "men": 50, "wavering": False,
                       "routing": True, "shattered": False, "departed": False}
                      for i in range(1, 6)]})
    path.write_text(json.dumps(result))
    return job


def plan_for(tmp_path, job):
    manifest = json.loads((job / "manifest.json").read_text())
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps({"benchmark": benchmark.VERSION, "source_revision": "r1",
        "scenario": manifest["scenario"], "jobs": [
            {"output": str(job), "controller": "llm_rules"},
            {"output": str(tmp_path / "never-started"), "controller": "hold"}]}))
    return path


def test_plan_report_reuses_visual_page_without_changing_raw_plan_contract(tmp_path):
    job = mirror_job(tmp_path, "completed")
    plan = plan_for(tmp_path, job)
    expected = benchmark.collect(plan)
    output = tmp_path / "visual"
    assert benchmark.report(plan, output) == expected
    assert json.loads((tmp_path / "visual.json").read_text()) == expected
    page = (tmp_path / "visual.html").read_text()
    assert 'id="map"' in page and 'id="benchmark-results"' in page
    data = embedded(page)
    planned, = data["benchmark_plans"]
    assert planned["planned"] == 2 and planned["completed"] == 1
    assert planned["never_started"] == 1
    complete, missing = planned["rows"]
    assert complete["condition"] == 30  # five .6-health routing units, factor .5
    assert complete["battle_key"] in data["battles"]
    assert missing["battle_key"] is None and missing["outcome"] is None


def test_visual_data_retains_condition_and_separates_profiles_even_with_a_legacy_core(tmp_path):
    old = mirror_job(tmp_path, "v4", version=4, outcome="won", hp=.02)
    current = mirror_job(tmp_path, "v5")
    legacy = configured_job(tmp_path, "legacy", scenario={"name": "legacy"})
    source = report.collect([old, current, legacy])
    original = deepcopy(source)
    data = report_html.display_data(source, {"scenarios": {"legacy": {"core_candidate": True}}})
    mirror = [s for s in data["scenarios"] if s["name"] == benchmark.SCENARIO]
    assert len(mirror) == 2
    assert {s["scenario_version"] for s in mirror} == {4, 5}
    assert all(len(s["battles"]) == 1 for s in mirror)
    scores = [data["battles"][s["battles"][0]]["benchmark"] for s in mirror]
    assert {s["condition"] for s in scores} == {1, 30}
    assert next(s for s in scores if s["outcome"] == "won")["rank"] > next(
        s for s in scores if s["outcome"] == "lost")["rank"]
    assert source == original


def test_plan_join_keeps_missing_measurements_and_rejects_foreign_evidence(tmp_path):
    job = mirror_job(tmp_path, "completed")
    plan = plan_for(tmp_path, job)
    result_path = job / "episode-0000/result.json"
    result = json.loads(result_path.read_text())
    result["benchmark"]["units"][0].pop("hp")
    result_path.write_text(json.dumps(result))
    source = report.collect([], benchmark_plans=[plan])
    data = report_html.display_data(source)
    row = data["benchmark_plans"][0]["rows"][0]
    assert row["outcome"] == "lost" and row["condition"] is None
    assert row["battle_key"] in data["battles"]
    path = job / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["source_revision"] = "foreign-source"
    path.write_text(json.dumps(manifest))
    data = report_html.display_data(report.collect([], benchmark_plans=[plan]))
    assert data["scenarios"] == []
    assert data["benchmark_plans"][0]["rows"][0]["battle_key"] is None
    assert data["benchmark_plans"][0]["rows"][0]["evidence_matches_plan"] is False


def test_a_plan_with_no_launches_still_has_a_visual_attempt_report(tmp_path):
    job = mirror_job(tmp_path, "foreign")
    plan = plan_for(tmp_path, job)
    declaration = json.loads(plan.read_text())
    declaration["jobs"] = declaration["jobs"][1:]
    plan.write_text(json.dumps(declaration))
    source = report.collect([], benchmark_plans=[plan])
    data = embedded(report_html.render(source))
    assert data["scenarios"] == []
    assert data["benchmark_plans"][0]["never_started"] == 1


def test_combined_plan_names_remain_distinct_after_local_paths_are_removed(tmp_path):
    plans = []
    for name, version in [("pilot", 4), ("model", 5)]:
        job = mirror_job(tmp_path, name, version=version)
        original = plan_for(tmp_path, job)
        path = tmp_path / name / "plan.json"
        path.write_text(original.read_text())
        plans.append(path)
    data = report_html.display_data(report.collect([], benchmark_plans=plans))
    names = [plan["plan"] for plan in data["benchmark_plans"]]
    assert len(set(names)) == 2
    assert all("/" not in name for name in names)


def test_a_damaged_trace_keeps_the_attempt_score_and_recording_error(tmp_path):
    job = mirror_job(tmp_path, "interrupted-write")
    plan = plan_for(tmp_path, job)
    (job / "episode-0000/trace.jsonl").write_text('{"kind": "decision"')
    output = tmp_path / "damaged"
    raw = benchmark.report(plan, output)
    assert raw["completed"] == 1 and raw["error_categories"]["trace"] == 1
    data = embedded((tmp_path / "damaged.html").read_text())
    row = data["benchmark_plans"][0]["rows"][0]
    assert row["outcome"] == "lost" and row["condition"] == 30
    assert any(error["category"] == "trace" for error in row["errors"])
