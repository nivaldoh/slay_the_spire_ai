import base64
import gzip
import io
import json
import re
import sys
from copy import deepcopy

import pytest
from make_wh3_report_demo import demo_report
from PIL import Image
from wh3_fixtures import configured_job, embedded, make_job

from twwarhammer3.battle import report, report_html


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
    demo = demo_report(tmp_path / "demo")
    data = embedded(report_html.render(demo))
    assert data["evidence_kind"] == "synthetic"
    assert len(data["comparisons"]) == 1
    assert {group["definition"]["model"] for group in data["report"]["groups"]} == {
        "Demo controller A", "Demo controller B", "Demo controller C"}
    assert {trial["delay_ms"] for group in demo["groups"] for trial in group["trials"]} == {
        0, 6000, 10000}
    assert len(data["report"]["jobs"]) == 7 and data["report"]["throughput"]["valid_trials"] == 18
    assert json.loads(gzip.decompress(base64.b64decode(data["replays"]["g0-t0"])))[
        "evidence_kind"] == "synthetic"
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


def test_recorded_stills_embed_once_per_controller_and_keep_failure_metadata(tmp_path,
                                                                            monkeypatch):
    job = make_job(tmp_path, "pictured", [("hold", .1, "won"), ("hold", .2, "won")])
    for name in ("episode-0000", "episode-0001"):
        episode = job / name
        (episode / "trace.jsonl").write_text(json.dumps({"kind": "observation", "observation": {
            "seq": 0, "time_ms": 0, "friendly": [{"id": "f1", "type": "demo"}], "enemy": []}}))
        Image.new("RGB", (20, 10), "blue").save(episode / "opening.png")
        (episode / "stills.json").write_text(json.dumps([
            {"file": "opening.png", "time_ms": 0, "trigger": "opening", "visibility": "unverified"},
            {"status": "capture_failed", "error": "unsupported API"}]))
        (episode / "unit_names.json").write_text(json.dumps({"f1": "Localised name"}))
    data = embedded(report_html.render(report.collect([job])))
    payloads = [json.loads(gzip.decompress(base64.b64decode(data["replays"][f"g0-t{i}"])))
                for i in range(2)]
    assert payloads[0]["stills"][0]["image"].startswith("data:image/webp;base64,")
    assert payloads[0]["stills"][0]["policy_input"] is False
    assert payloads[0]["stills"][1]["status"] == "capture_failed"
    assert payloads[1]["stills"][0]["status"] == "metadata_only_nonfeatured_trial"
    assert "image" not in payloads[1]["stills"][0]
    assert payloads[0]["roster"][0]["name"] == "Localised name"
    # Without Pillow the report refuses to drop the images silently.
    monkeypatch.setitem(sys.modules, "PIL", None)
    with pytest.raises(RuntimeError, match="needs Pillow"):
        report_html.render(report.collect([job]))


def test_stills_resize_preserve_provenance_and_report_failures(tmp_path):
    Image.new("RGB", (2000, 1500), "blue").save(tmp_path / "opening.tga")
    entries = [{"file": "opening.tga", "time_ms": 1000, "visibility": "unverified"},
               {"file": "missing.tga", "time_ms": 2000},
               {"status": "capture_failed", "error": "unsupported API"}]
    output = report_html.stills(tmp_path, entries, embed=True)
    assert output[0]["original_size"] == [2000, 1500]
    assert max(output[0]["size"]) <= 1600 and output[0]["size"][1] <= 1000
    assert output[0]["time_ms"] == 1000 and output[0]["policy_input"] is False
    assert output[0]["visibility"] == "unverified"
    data = base64.b64decode(output[0]["image"].split(",")[1])
    with Image.open(io.BytesIO(data)) as decoded:
        assert decoded.format == "WEBP"
    assert output[1]["status"] == "error"
    assert output[2]["status"] == "capture_failed"
    assert "image" not in report_html.stills(tmp_path, entries, embed=False)[0]


def test_detailed_still_fits_the_image_budget(tmp_path):
    Image.effect_noise((2000, 1500), 100).convert("RGB").save(tmp_path / "detail.png")
    assert report_html.webp(tmp_path / "detail.png")["bytes"] <= report_html.MAX_STILL_BYTES


def test_featured_trial_is_earliest_completed_model_even_when_it_loses(tmp_path):
    jobs = [configured_job(tmp_path, "later-win"), configured_job(tmp_path, "earlier-loss")]
    for index, job in enumerate(jobs):
        path = job / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["created_at"] = "2026-10-15T12:00:00Z" if index == 0 else "2026-10-14T12:00:00Z"
        path.write_text(json.dumps(manifest))
        episode = job / "episode-0000"
        (episode / "trace.jsonl").write_text(json.dumps({"kind": "observation", "observation": {
            "seq": 0, "time_ms": 0, "friendly": [], "enemy": []}}))
        path = episode / "result.json"
        result = json.loads(path.read_text())
        result["status"] = "won" if index == 0 else "lost"
        path.write_text(json.dumps(result))
    data = embedded(report_html.render(report.collect(jobs)))
    assert data["featured"]["comparison-1"] == "g0-t1"
