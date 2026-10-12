"""The job watcher reads a (fake) job's evidence and reports one event at a time."""

import os
import time

from test_play import CONFIG, DEATH, MENU, NEOW, ScriptedPolicy, harness

from spire.fullrun import play, watch
from spire.provenance import write_json

__all__ = ["harness"]


def test_each_finished_run_is_one_event_with_its_log_row(tmp_path, harness):
    sessions, _ = harness
    sessions += [[MENU, NEOW, DEATH], [MENU, NEOW, DEATH]]
    play.play(tmp_path / "job", CONFIG, policy_factory=ScriptedPolicy)
    assert watch.check(tmp_path / "job", 0).startswith("| SEEDA | lost | ")
    assert watch.check(tmp_path / "job", 1).endswith(" job completed")
    assert watch.check(tmp_path / "job", 2) == "job completed"


def test_a_running_job_reports_only_a_stale_trace(tmp_path):
    job = tmp_path / "job"
    (job / "run-0000").mkdir(parents=True)
    write_json(job / "manifest.json", {"status": "running", "runs": []})
    trace = job / "run-0000/trace.jsonl"
    trace.write_text("")
    assert watch.check(job, 0) is None
    stale = time.time() - watch.STALL_SECONDS - 5
    os.utime(trace, (stale, stale))
    assert watch.check(job, 0).startswith("STALL: run-0000 trace unchanged for ")


def test_a_job_that_never_writes_a_manifest_reports_its_log(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, "START_SECONDS", 0)
    (tmp_path / "job.log").write_text("Traceback\nRuntimeError: uncommitted source\n")
    assert watch.next_event(tmp_path / "job", poll=0) == (
        "NOT STARTED: Traceback | RuntimeError: uncommitted source"
    )
