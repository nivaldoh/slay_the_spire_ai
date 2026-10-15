import base64
import gzip
import io
import json
import re
import sys
from copy import deepcopy

import pytest
from make_wh3_report_demo import demo_report, pair_jobs
from PIL import Image
from wh3_fixtures import configured_job, embedded, make_job

from twwarhammer3.battle import report, report_html


def test_curated_suite_titles_distinguish_related_challenges():
    notes = json.loads(report_html.NOTES_PATH.read_text())["scenarios"]
    names = ("dwf-sla-taurox", "dwf-sla-herald", "dwf-sla-herald-hard",
             "brt-cavalry-emp-pikes", "brt-cavalry-emp-pegasus")
    titles = [notes[name]["title"] for name in names]
    assert len(set(titles)) == len(names)


def test_unnamed_historical_modes_use_saved_config_and_readable_armies(tmp_path):
    jobs = []
    for mode in ("siege", "survival"):
        job = configured_job(tmp_path, mode, scenario={"battle_type": mode,
            "player": {"faction": "wh_main_dwf_dwarfs", "units": ["lord", "infantry"]},
            "enemy": None})
        path = job / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["config"]["scenario"] = f"{mode}-pilot"
        path.write_text(json.dumps(manifest))
        jobs.append(job)
    data = report_html.display_data(report.collect(jobs))
    assert [scenario["name"] for scenario in data["scenarios"]] == ["siege-pilot", "survival-pilot"]
    survival = data["scenarios"][1]
    assert survival["battle_type"] == "survival"
    assert survival["armies"] == {"friendly": "Dwarfs · 2 units", "enemy": "Waves"}
    assert survival["group"] == "Other battle types (pilots)"  # no notes and no family
    # The declaration is evidence: do not write a synthetic name into it.
    assert "name" not in data["report"]["groups"][0]["definition"]["scenario"]


def test_one_row_per_commander_and_the_collector_groups_stay_intact(tmp_path):
    jobs = [configured_job(tmp_path, "a"), configured_job(tmp_path, "b", model="model-b"),
            configured_job(tmp_path, "c", effort="high")]
    source = report.collect(jobs)
    original = deepcopy(source)
    data = embedded(report_html.render(source))
    assert source == original
    (scenario,) = data["scenarios"]
    assert [(row["name"], row["detail"], row["battles"], row["harnesses"])
            for row in scenario["rows"]] == [
        ("model-a", "high reasoning · no tactical advice", ["g2-t0"], 1),
        ("model-a", "low reasoning · no tactical advice", ["g0-t0"], 1),
        ("model-b", "low reasoning · no tactical advice", ["g1-t0"], 1)]
    assert len(data["report"]["groups"]) == 3
    assert all(not group["paired"] for group in data["report"]["groups"])
    assert [group["controllers"] for group in data["report"]["groups"]] == [
        group["controllers"] for group in source["groups"]]


@pytest.mark.parametrize("field,value", [
    ("source", "other"), ("game", {"steam_build_id": "different", "sha256": "different"}),
    ("track", "other-interface"), ("observe_ms", 2000), ("tick_ms", 500),
    ("interval_ms", 1000), ("scenario", {"name": "frozen", "map": "other"}), ("source", None),
    ("recorder", {"version": 1, "enabled": True}), ("imagery", {"enabled": True}),
])
def test_the_harness_changes_with_anything_that_shapes_play(tmp_path, field, value):
    source = report.collect([configured_job(tmp_path, "a"),
                             configured_job(tmp_path, "b", model="model-b")])
    source["groups"][1]["definition"][field] = value
    jobs = {job["instance"]: job for job in source["jobs"]}
    first, second = (report_html.harness(group["definition"], jobs[group["trials"][0]["instance"]])
                     for group in source["groups"])
    assert first != second


def test_presentation_files_model_and_prose_leave_the_harness_alone(tmp_path):
    code = {"src/twwarhammer3/battle/llm.py": "a", "src/twwarhammer3/battle/report.py": "a",
            "configs/twwarhammer3/report_notes.json": "a"}
    definition = {"source": "r1", "track": "t", "model": "m", "evaluator_version": 1,
                  "scenario": {"name": "s", "brief": "old", "status": "draft"}}
    job = {"provenance": {"source_files": code}}
    base = report_html.harness(definition, job)
    assert base == report_html.harness(
        {**definition, "source": "r2", "model": "other", "evaluator_version": 2,
         "scenario": {"name": "s", "brief": "new", "status": "admitted"}},
        {"provenance": {"source_files": {**code, "src/twwarhammer3/battle/report.py": "b",
                                         "configs/twwarhammer3/report_notes.json": "b"}}})
    assert base != report_html.harness(definition, {"provenance": {"source_files": {
        **code, "src/twwarhammer3/battle/llm.py": "b"}}})
    # Without file hashes the revision stands in for the code.
    assert report_html.harness(definition, None) != report_html.harness(
        {**definition, "source": "r2"}, None)


def test_a_row_keeps_battles_from_several_harnesses_and_counts_them(tmp_path):
    jobs = [configured_job(tmp_path, "a"), configured_job(tmp_path, "b", source_revision="r2")]
    data = report_html.display_data(report.collect(jobs))
    (row,) = data["scenarios"][0]["rows"]
    assert row["battles"] == ["g0-t0", "g1-t0"] and row["harnesses"] == 2
    assert data["battles"]["g0-t0"]["harness"] != data["battles"]["g1-t0"]["harness"]


def test_progress_is_the_enemy_share_dead_or_out_of_the_fight(tmp_path):
    job = make_job(tmp_path, "progress", [("hold", 0, "lost"), ("hold", 0, "won")])
    for name, final in (("episode-0000", {"friendly": {"men0": 200, "men": 50},
                                          "enemy": {"men0": 500, "men": 300, "active_men": 125}}),
                        ("episode-0001", {"friendly": {"men0": 200}, "enemy": {"men0": 500}})):
        path = job / name / "result.json"
        path.write_text(json.dumps({**json.loads(path.read_text()), "final": final}))
    battles = report_html.display_data(report.collect([job]))["battles"]
    assert (battles["g0-t0"]["progress"], battles["g0-t0"]["own_left"]) == (.75, .25)
    # Unknown is not zero: nothing recorded leaves both unknown.
    assert (battles["g0-t1"]["progress"], battles["g0-t1"]["own_left"]) == (None, None)


def test_commanders_get_readable_names_kinds_and_families():
    def name(policy, **trial):
        return report_html.commander({"policy": policy, **trial},
                                     {"model": "gpt-6-sol", "effort": "low"})

    assert name("llm_rules") == {"kind": "model", "family": "gpt-6-sol", "name": "gpt-6-sol",
                                 "detail": "low reasoning · no tactical advice",
                                 "prompt": "no tactical advice"}
    assert name("llm_rules@gpt-6-luna/medium")["detail"] == "medium reasoning · no tactical advice"
    assert name("commander", card={"kind": "hybrid", "model": "gpt-6-luna"})["family"] == (
        "gpt-6-luna")
    assert name("rush_nearest", delay_ms=6000) == {
        "kind": "scripted", "family": "Scripted", "name": "Charge nearest",
        "detail": "scripted: every unit runs at the nearest visible enemy · "
                  "+6 s added observation age"}
    assert name("terrain_probe:TerrainProbe") == {
        "kind": "diagnostic", "family": None, "name": "Diagnostic probe",
        "detail": "TerrainProbe"}


def test_compact_timing_and_route_keep_only_what_the_page_draws():
    def unit(uid, x, **extra):
        return {"id": uid, "x": x, "z": 0.123456, "men": 10, "men0": 10, "hp": 0.99999,
                "abilities": [{"key": "a"}], "morale": {"fraction": 1}, "state": ["idle"],
                **extra}
    frames = [{"time_ms": t * 1000, "seq": t, "phase": "Deployed", "magic": {"current": 1},
               "mode": {"role": "attacker", "objectives": "long text"}, "enemy_roster": [],
               "friendly": [unit("f1", x)], "enemy": [unit("e1", 500.0)]}
              for t, x in enumerate((0.0, 2.0, 7.0, 20.0, 21.0))]
    frames[-1]["friendly"][0].update(men=0)
    move = {"unit": "f1", "side": "friendly", "from": [0.04, 0.0], "to": [20.0, 0.0],
            "metres": 20.0004}
    decisions = [
        {"orders": [{"unit": "f1"}], "age_s": 4.25, "plan_age_s": None, "after_frame": 3,
         "time_ms": 1000, "applied_ms": 5250, "displacements": [move]},
        # Kept orders; a commander's plan is older than the executor's observation.
        {"orders": [], "age_s": 3.0, "after_frame": 3, "time_ms": 6000, "applied_ms": 9000,
         "plan_age_s": 2.0, "displacements": []},
        {"orders": [{"unit": "f1"}], "age_s": None, "time_ms": 9000,
         "displacements": []},  # unacknowledged
    ]
    payload = {"frames": frames, "decisions": decisions, "recorder_version": 1,
               "roster": [{"id": "f1", "glyph": "cavalry"}, {"id": "e1", "glyph": "infantry"}],
               "summary": {"rejections": 2}}
    original = deepcopy(payload)
    compacted = report_html.compact(payload)
    assert payload == original  # the build output is not modified
    assert compacted["frames"][0]["friendly"][0] == {
        "id": "f1", "x": 0.0, "z": 0.1, "men": 10, "men0": 10, "hp": 1.0, "state": ["idle"]}
    assert compacted["frames"][0]["mode"] == {"role": "attacker"}
    assert "magic" not in compacted["frames"][0]
    assert compacted["decisions"][0]["displacements"][0]["from"] == [0.0, 0.0]
    # A plan adoption makes it a commander battle: only adoptions are the model's replies.
    assert report_html.timing(compacted) == {
        "ages": [4.2], "plans": [2.0], "moved": [20], "decisions": 3, "batches": 1,
        "rejected": 2, "replies": [[4000, 9000]]}
    blocking = deepcopy(compacted)
    blocking["decisions"][1].pop("plan_age_s")
    assert report_html.timing(blocking)["replies"] == [[1000, 5250], [6000, 9000]]
    # Distance needs the 1 Hz recorder: sparse controller observations would overstate it.
    assert report_html.timing({**compacted, "recorder_version": None})["moved"] == []
    assert report_html.route(compacted) == {
        "friendly": [{"id": "f1", "glyph": "cavalry", "end": "down",
                      "path": [[0, 0], [7, 0], [20, 0], [21, 0]]}],
        "enemy": [{"id": "e1", "glyph": "infantry", "at": [500, 0]}]}


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
    data = embedded(report_html.render(source))
    group = data["report"]["groups"][0]
    summary = group["controllers"][0]
    assert summary == source["groups"][0]["controllers"][0]
    assert summary["win_rate"] == .5 and summary["win_ci95"] is None
    assert summary["time_limit_engine_outcomes"] == {"won": 1}
    assert group["trials"][1]["metrics"]["margin"] is None
    assert data["battles"]["g0-t1"]["progress"] is None
    assert data["report"]["jobs"][1]["error"] == "KeyboardInterrupt"
    assert data["report"]["throughput"]["started_trials"] == 2
    # No placeholders for unrun catalogue scenarios; the stopped launch is listed on its own.
    assert [scenario["name"] for scenario in data["scenarios"]] == ["frozen"]
    assert data["setup_only"] == [{"job": 1, "scenario": "historical", "title": "historical"}]


def test_safe_embedding_portable_ids_and_no_remote_dependencies(tmp_path):
    hostile = '</script><script>alert("x")</script>&<img src=x onerror=alert(1)>@@STYLE@@\u2028'
    source = report.collect([configured_job(tmp_path, "job", scenario={"name": hostile})])
    source["groups"][0]["trials"][0]["error"] = hostile
    html = report_html.render(source)
    data = embedded(html)
    assert data["report"]["groups"][0]["definition"]["scenario"]["name"] == hostile
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
    # One row per demo controller and added age, each holding both launches.
    rows = data["scenarios"][0]["rows"]
    assert len(rows) == 9 and {row["name"] for row in rows} == {
        "Demo controller A", "Demo controller B", "Demo controller C"}
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


def test_a_controller_that_failed_to_build_keeps_the_report(tmp_path):
    job = make_job(tmp_path, "failed", [("llm", .1, "won"), ("llm", .2, "won")])
    source = report.collect([job])
    first, failed = source["groups"][0]["trials"]
    first["card"] = {"kind": "model", "model": "gpt-6-sol"}
    failed.update(card=None, valid=False, outcome="policy_failure",
                  error="controller construction")
    data = embedded(report_html.render(source))
    assert data["report"]["groups"][0]["trials"][1]["error"] == "controller construction"


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
    assert data["scenarios"][0]["featured"] == "g0-t1"
    assert data["scenarios"][0]["featured_reason"] == "first_model_run"


def test_diagnostic_probes_stay_in_the_data_but_off_the_page(tmp_path):
    job = make_job(tmp_path, "probe", [("hold", 0, "lost"), ("terrain_probe:Probe", 0, "lost")])
    data = report_html.display_data(report.collect([job]))
    (scenario,) = data["scenarios"]
    assert scenario["battles"] == ["g0-t0"] and data["diagnostics"] == ["g0-t1"]
    assert [row["name"] for row in scenario["rows"]] == ["Hold position"]
    assert data["battles"]["g0-t1"]["commander"]["kind"] == "diagnostic"
    only = make_job(tmp_path, "only-probe", [("terrain_probe:Probe", 0, "lost")])
    assert report_html.display_data(report.collect([only]))["scenarios"] == []


def test_a_controlled_set_needs_the_same_commanders_in_several_launches_of_one_harness(
        tmp_path):
    shared = [make_job(tmp_path, f"shared-{n}", [("hold", 0, "lost"), ("skills", 0, "won")])
              for n in range(3)]
    alone = make_job(tmp_path, "alone", [("hold", 0, "lost")])
    other = make_job(tmp_path, "other", [("hold", 0, "lost"), ("skills", 0, "won")],
                     revision="r2")
    data = report_html.display_data(report.collect([*shared, alone, other]))
    controlled = data["scenarios"][0]["controlled"]
    assert controlled["launches"] == 3 and controlled["once"]
    assert {data["report"]["groups"][int(key[1])]["trials"][int(key.split("t")[1])]["instance"]
            for key in controlled["battles"]} == {"shared-0", "shared-1", "shared-2"}
    extras = [make_job(tmp_path, f"extra-{n}", [("hold", 0, "lost"), ("skills", 0, "won"),
                                                    (extra, 0, "lost")])
              for n, extra in enumerate(("attack_nearest", "rush_nearest"))]
    core = report_html.display_data(report.collect(extras))["scenarios"][0]["controlled"]
    assert core["launches"] == 2 and len(core["battles"]) == 4  # hold and skills in both
    single = report_html.display_data(report.collect([shared[0], alone]))
    assert single["scenarios"][0]["controlled"] is None  # one launch is an example, not a set


def traced_job(tmp_path, name, created_at, **changes):
    """A configured job whose one battle has a trace and a model controller card."""
    job = configured_job(tmp_path, name, created_at=created_at, **changes)
    episode = job / "episode-0000"
    (episode / "trace.jsonl").write_text(json.dumps({"kind": "observation", "observation": {
        "seq": 0, "time_ms": 0, "friendly": [], "enemy": []}}))
    path = episode / "result.json"
    path.write_text(json.dumps({**json.loads(path.read_text()),
                                "card": {"kind": "model", "source_sha256": "code"}}))
    return job


def test_scenarios_feature_the_selected_run_and_follow_the_notes_order(tmp_path):
    later = traced_job(tmp_path, "later", "2026-10-15T00:00:00Z")
    earlier = traced_job(tmp_path, "earlier", "2026-10-14T00:00:00Z")
    elsewhere = traced_job(tmp_path, "elsewhere", "2026-10-13T00:00:00Z",
                           scenario={"name": "elsewhere"})
    stopped = make_job(tmp_path, "stopped", [])
    source = report.collect([later, earlier, elsewhere, stopped])
    highlight = {"time_ms": 0, "title": "Opening", "units": ["f1"]}
    notes = {"scenarios": {"elsewhere": {"title": "Elsewhere", "group": "Challenges"},
                           "frozen": {"title": "Frozen pass", "group": "Pilots",
                                      "question": "Can it cross?", "challenge": "Cross."}},
             "runs": {"later/episode-0000": {"selected": True, "highlights": [highlight]}}}
    data = embedded(report_html.render(source, notes))
    assert [scenario["name"] for scenario in data["scenarios"]] == ["elsewhere", "frozen"]
    frozen = data["scenarios"][1]
    assert {key: frozen[key] for key in ("title", "question", "challenge", "group", "featured",
                                         "featured_reason", "setup_only_jobs")} == {
        "title": "Frozen pass", "question": "Can it cross?", "challenge": "Cross.",
        "group": "Pilots", "featured": "g0-t0", "featured_reason": "selected",
        "setup_only_jobs": [3]}
    # The two launches share one collector group; battles go by job start, never by outcome.
    assert frozen["battles"] == ["g0-t1", "g0-t0"]
    payloads = [json.loads(gzip.decompress(base64.b64decode(data["replays"][key])))
                for key in ("g0-t0", "g0-t1")]
    assert payloads[0]["highlights"] == [highlight] and payloads[0]["selected"] is True
    assert payloads[1]["highlights"] == [] and payloads[1]["selected"] is False
    scenario = report_html.display_data(source)["scenarios"][1]  # without notes
    assert (scenario["featured"], scenario["featured_reason"]) == ("g0-t1", "first_model_run")
    assert (scenario["title"], scenario["question"]) == ("frozen", None)


def test_a_job_without_a_recorded_scenario_still_gets_a_readable_title(tmp_path):
    # Older random-battle jobs (runs/twwarhammer3/battle/attack-*) record no scenario.
    random_battle = configured_job(tmp_path, "random", scenario=None)
    stopped = make_job(tmp_path, "stopped", [])
    path = stopped / "manifest.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "scenario": None}))
    data = report_html.display_data(report.collect([random_battle]))
    assert data["scenarios"][0]["title"] == "No scenario recorded"
    data = report_html.display_data(report.collect([stopped]))
    assert data["setup_only"] == [{"job": 0, "scenario": None, "title": "No scenario recorded"}]


def test_two_models_of_one_policy_are_two_controllers_paired_within_each_launch(tmp_path):
    # check_wh3_report_browser.cjs reads the page's names of these controllers.
    jobs = pair_jobs(tmp_path)
    source = report.collect(jobs)
    pooled, high = source["groups"]  # pair-c ran on --effort high
    assert [row["controller"] for row in pooled["controllers"]] == [
        "llm_rules / +0s", "llm_rules@gpt-6-luna/medium / +0s"]
    (paired,) = pooled["paired"]
    assert paired["n"] == 2 and paired["mean"] == pytest.approx(.1)
    assert paired["unpaired_instances"] == []
    assert {trial["instance"] for trial in high["trials"]} == {str(jobs[2])}
    data = embedded(report_html.render(source))
    assert data["scenarios"][0]["featured_reason"] == "first_model_run"
    assert [(trial["policy"], *[(trial["card"] or {}).get(key) for key in ("model", "effort")])
            for group in data["report"]["groups"] for trial in group["trials"]] == [
        ("llm_rules", "gpt-6-sol", "low"), ("llm_rules@gpt-6-luna/medium", "gpt-6-luna", "medium"),
    ] * 2 + [("llm_rules", "gpt-6-sol", "high"), ("llm_rules@gpt-6-luna/medium", None, None)]
    # The page finds the prompt and the readable name by the base policy name.
    assert data["prompts"]["pair-a"] == {"llm_rules_prompt.md": "Invented rules-only prompt."}
    assert "llm_rules" in data["model_policies"]
    assert report_html._model_trial({"policy": "commander@gpt-6-luna", "card": {"kind": "hybrid"}})
    assert not report_html._model_trial({"policy": "hold", "card": {"kind": "scripted"}})
