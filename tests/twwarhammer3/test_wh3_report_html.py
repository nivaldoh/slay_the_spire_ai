import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from test_wh3_benchmark import make_job

from twwarhammer3.battle import report, report_html

DEMO = Path(__file__).parents[1] / "fixtures/wh3_field_report_demo.json"


def embedded(html):
    return json.loads(re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>', html, re.S)[1])


def configured_job(tmp_path, name, model="model-a", effort="low", **changes):
    job = make_job(tmp_path, name, [("llm_rules", .3, "won")])
    path = job / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(track="obs-v3/act-v2/live-1x")
    manifest["config"].update(model=model, effort=effort, observe_ms=1000, tick_ms=250,
                              interval_ms=0)
    manifest.update(changes)
    path.write_text(json.dumps(manifest))
    (job / "environment.json").write_text(json.dumps({
        "game": {"steam_build_id": "123", "sha256": "game-hash"}}))
    return job


def test_compatible_models_and_efforts_display_together_without_pooling_or_new_pairs(tmp_path):
    jobs = [configured_job(tmp_path, "a"), configured_job(tmp_path, "b", model="model-b"),
            configured_job(tmp_path, "c", effort="high")]
    source = report.collect(jobs)
    original = deepcopy(source)
    data = embedded(report_html.render(source))
    assert source == original
    assert len(data["comparisons"]) == 1
    assert data["comparisons"][0]["groups"] == [0, 1, 2]
    assert "model" not in data["comparisons"][0]["definition"]
    assert len(data["report"]["groups"]) == 3
    assert all(not group["paired"] for group in data["report"]["groups"])
    assert [group["controllers"] for group in data["report"]["groups"]] == [
        group["controllers"] for group in source["groups"]]


@pytest.mark.parametrize("field,value", [
    ("source", "other"), ("game", {"steam_build_id": "different", "sha256": "different"}),
    ("track", "other-interface"), ("observe_ms", 2000), ("tick_ms", 500),
    ("interval_ms", 1000), ("scenario", {"name": "other"}), ("source", None),
    ("game", {}), ("track", ""),
    ("recorder", {"version": 1, "enabled": True}),
])
def test_incompatible_or_unknown_definitions_remain_separate(tmp_path, field, value):
    source = report.collect([configured_job(tmp_path, "a"),
                             configured_job(tmp_path, "b", model="model-b")])
    source["groups"][1]["definition"][field] = value
    data = report_html.display_data(source)
    assert len(data["comparisons"]) == 2
    assert [view["groups"] for view in data["comparisons"]] == [[0], [1]]


def test_timer_missing_metrics_repeats_and_setup_only_interruption_are_preserved(tmp_path):
    job = make_job(tmp_path, "repeat", [("hold", .2, "won"), ("hold", -.1, "won")])
    path = job / "episode-0001/result.json"
    result = json.loads(path.read_text())
    result.update(ended_by="time_limit")
    result.pop("final")
    path.write_text(json.dumps(result))
    interrupted = make_job(tmp_path, "interrupted", [])
    path = interrupted / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(status="interrupted", error="KeyboardInterrupt", wall_seconds=64.48)
    manifest["scenario"] = {"name": "historical", "brief": "Historical brief"}
    path.write_text(json.dumps(manifest))
    source = report.collect([job, interrupted])
    data = embedded(report_html.render(source, {
        "historical": {"brief": "NEW", "status": "admitted"},
        "unrun": {"brief": "Current only", "status": "prototype_not_admitted"}}))
    group = data["report"]["groups"][0]
    summary = group["controllers"][0]
    assert summary == source["groups"][0]["controllers"][0]
    assert summary["win_rate"] == .5 and summary["win_ci95"] is None
    assert summary["time_limit_engine_outcomes"] == {"won": 1}
    assert group["trials"][1]["metrics"]["margin"] is None
    assert data["report"]["jobs"][1]["error"] == "KeyboardInterrupt"
    assert data["report"]["throughput"]["started_trials"] == 2
    historical = data["comparisons"][1]
    assert historical["definition"]["scenario"]["brief"] == "Historical brief"
    assert historical["jobs"] == [1] and historical["groups"] == []
    assert data["comparisons"][2]["metadata_origin"].startswith("Current catalogue")


def test_safe_embedding_portable_ids_and_no_remote_dependencies(tmp_path):
    hostile = '</script><script>alert("x")</script>&<img src=x onerror=alert(1)>@@STYLE@@\u2028'
    source = report.collect([configured_job(tmp_path, "job", scenario={"name": hostile})])
    source["groups"][0]["trials"][0]["error"] = hostile
    html = report_html.render(source)
    data = embedded(html)
    assert data["comparisons"][0]["definition"]["scenario"]["name"] == hostile
    assert data["report"]["groups"][0]["trials"][0]["error"] == hostile
    assert hostile not in html and "\\u003c/script\\u003e" in html
    assert str(tmp_path) not in html
    assert data["report"]["groups"][0]["trials"][0]["instance"] == "job"
    assert 'default-src \'none\'' in html
    assert not re.search(r'<(?:script|link|img)\b[^>]*(?:src|href)=', html)
    script = (report_html.ASSETS / "report.js").read_text()
    assert "innerHTML" not in script and "fetch(" not in script


def test_duplicate_job_basenames_keep_pair_identifiers_distinct(tmp_path):
    jobs = []
    for name in ("a", "b"):
        root = tmp_path / name
        root.mkdir()
        jobs.append(make_job(root, "same", [("hold", 0, "lost"), ("skills", .3, "won")]))
    data = report_html.display_data(report.collect(jobs))
    group = data["report"]["groups"][0]
    keys = group["paired"][0]["differences_by_instance"]
    assert len(keys) == 2 and all(key.startswith("same-") for key in keys)
    assert set(keys) == {job["instance"] for job in data["report"]["jobs"]}


def test_demo_is_explicit_and_cannot_mix_with_recorded_evidence(tmp_path):
    demo = json.loads(DEMO.read_text())
    data = embedded(report_html.render(demo))
    assert data["evidence_kind"] == "synthetic"
    assert len(data["comparisons"]) == 1
    assert {group["definition"]["model"] for group in data["report"]["groups"]} == {
        "Demo controller A", "Demo controller B", "Demo controller C"}
    assert {trial["delay_ms"] for group in demo["groups"] for trial in group["trials"]} == {
        0, 6000, 10000}
    recorded = report.collect([configured_job(tmp_path, "real")])
    recorded["groups"].append(demo["groups"][0])
    with pytest.raises(ValueError, match="separate reports"):
        report_html.render(recorded)
    demo["jobs"][0].pop("evidence_kind")
    with pytest.raises(ValueError, match="separate reports"):
        report_html.render(demo)


def test_prepooled_different_controller_cards_are_refused(tmp_path):
    job = make_job(tmp_path, "mixed", [("llm", .1, "won"), ("llm", .2, "won")])
    source = report.collect([job])
    for index, trial in enumerate(source["groups"][0]["trials"]):
        trial["card"] = {"kind": "model", "model": f"different-{index}"}
    with pytest.raises(ValueError, match="mixed controller identities"):
        report_html.render(source)


def test_cli_collects_once_and_preserves_text_and_json(tmp_path, monkeypatch, capsys):
    from twwarhammer3.__main__ import main

    source = report.collect([configured_job(tmp_path, "a")])
    calls = []

    def collect(jobs):
        calls.append(jobs)
        return source

    monkeypatch.setattr(report, "collect", collect)
    monkeypatch.setattr(report_html, "SCENARIOS", tmp_path / "absent.json")
    output = tmp_path / "nested/report.html"
    json_output = tmp_path / "report.json"
    monkeypatch.setattr("sys.argv", ["wh3", "stats", "--report", "a", "--report-html",
                                    str(output), "--report-json", str(json_output)])
    assert main() == 0
    assert len(calls) == 1
    assert json.loads(json_output.read_text()) == source
    assert capsys.readouterr().out == report.render(source) + "\n"
    assert embedded(output.read_text())["report"]["groups"][0]["controllers"] == source[
        "groups"][0]["controllers"]


def test_html_cli_requires_report(monkeypatch, capsys):
    from twwarhammer3.__main__ import main

    monkeypatch.setattr("sys.argv", ["wh3", "stats", "--report-html", "report.html"])
    with pytest.raises(SystemExit, match="2"):
        main()
    assert "--report-html requires --report JOB..." in capsys.readouterr().err
