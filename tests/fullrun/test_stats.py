"""The results register reads saved evidence alone; no engine is involved."""

import json

from spire.fullrun import stats

MENU = {"kind": "observation", "raw": {"in_game": False}}
START = {"kind": "observation",
         "raw": {"in_game": True, "game_state": {"class": "IRONCLAD", "ascension_level": 0}}}


def save_job(root, name, created_at, *results, started=True):
    job = root / name
    job.mkdir(parents=True)
    (job / "manifest.json").write_text(json.dumps({
        "created_at": created_at, "source_revision": "0123456789abcdef",
        "config": {"model": "gpt-6-luna", "effort": "low"}}))
    for index, result in enumerate(results):
        run = job / f"run-{index:04d}"
        run.mkdir()
        (run / "result.json").write_text(json.dumps({"seed": "SEEDA", "status": "lost", **result}))
        trace = [{"kind": "launch"}, MENU, *([START] if started else [])]
        (run / "trace.jsonl").write_text("".join(json.dumps(r) + "\n" for r in trace))
    return job


def record_all(path, *jobs):
    for job in jobs:
        for run in sorted(job.glob("run-*")):
            stats.record(path, job, run)


def test_a_row_reads_the_manifest_result_and_first_in_game_state(tmp_path):
    job = save_job(tmp_path, "llm-luna-v9-dev-20261012", "2026-10-12T21:56:59+00:00",
                   {"act": 2, "floor": 29, "score": 290, "llm": {"usd": 0.098643}})
    assert stats.row(job, job / "run-0000") == {
        "date": "2026-10-12", "job": "llm-luna-v9-dev-20261012", "run": "run-0000",
        "seed": "SEEDA", "character": "IRONCLAD", "ascension": 0, "model": "gpt-6-luna",
        "effort": "low", "harness": "v9", "source": "0123456", "outcome": "lost", "act": 2,
        "floor": 29, "score": 290, "usd": "0.0986",
    }
    point = save_job(tmp_path, "llm-luna-v1.1-dev-20261012", "2026-10-12T04:23:00+00:00", {})
    assert stats.row(point, point / "run-0000")["harness"] == "v1.1"


def test_a_run_that_never_started_leaves_its_unknowns_empty(tmp_path):
    job = save_job(tmp_path, "llm-smoke-20261012-a", "2026-10-12T04:01:00+00:00",
                   {"status": "infrastructure_failure"}, started=False)
    row = stats.row(job, job / "run-0000")
    assert "character" not in row and "ascension" not in row
    assert (row["harness"], row["outcome"], row["act"], row["usd"]) == (
        None, "infrastructure_failure", None, None)
    stats.record(tmp_path / "results.csv", job, job / "run-0000")
    assert (tmp_path / "results.csv").read_text().splitlines()[1] == (
        "2026-10-12,llm-smoke-20261012-a,run-0000,SEEDA,,,gpt-6-luna,low,,0123456,"
        "infrastructure_failure,,,,")


def test_rebuild_reproduces_the_appended_register_in_job_start_order(tmp_path):
    jobs = tmp_path / "jobs"
    # Named to sort before the earlier job: the register follows start times, not names.
    later = save_job(jobs, "a-v3-dev", "2026-10-12T06:00:00+00:00", {"act": 1, "floor": 6})
    earlier = save_job(jobs, "b-v2-dev", "2026-10-12T05:00:00+00:00",
                       {"act": 1, "floor": 16}, {"act": 2, "floor": 33})
    (jobs / "b-v2-dev.log").write_text("")
    (jobs / "unfinished").mkdir()
    record_all(tmp_path / "live.csv", earlier, later)
    (earlier / "run-0002").mkdir()  # a run with no result yet
    stats.rebuild(jobs, tmp_path / "rebuilt.csv")
    live = (tmp_path / "live.csv").read_text()
    assert (tmp_path / "rebuilt.csv").read_text() == live
    lines = live.splitlines()
    assert lines[0] == ",".join(stats.FIELDS)
    assert [line.split(",")[1:3] for line in lines[1:]] == [
        ["b-v2-dev", "run-0000"], ["b-v2-dev", "run-0001"], ["a-v3-dev", "run-0000"]]


def test_summary_counts_milestones_and_finished_runs_per_group(tmp_path):
    v8 = save_job(tmp_path, "llm-luna-v8-dev-20261012", "2026-10-12T19:40:00+00:00",
                  {"act": 1, "floor": 16}, {"act": 4, "floor": 54},
                  {"status": "truncated", "act": 3, "floor": 40})
    v9 = save_job(tmp_path, "llm-luna-v9-dev-20261012", "2026-10-12T21:56:00+00:00",
                  {"status": "won", "act": 3, "floor": 51},
                  {"status": "infrastructure_failure", "act": 2, "floor": 20})
    record_all(tmp_path / "results.csv", v8, v9)
    assert stats.summary(tmp_path / "results.csv").splitlines()[2:] == [
        "| IRONCLAD | 0 | gpt-6-luna | low | v8 | 3 | 2 | 2 | 2 | 1 | 0 | 54 | 35.0 |",
        "| IRONCLAD | 0 | gpt-6-luna | low | v9 | 2 | 1 | 2 | 1 | 0 | 1 | 51 | 51.0 |",
    ]
