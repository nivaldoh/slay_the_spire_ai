"""The plan runner runs play jobs serially from a frozen revision and records its state."""

import importlib.util
import json
import os
import signal
import subprocess
import sys

import pytest

from gameai.provenance import REPO_ROOT

SPEC = importlib.util.spec_from_file_location("wh3_queue_script",
                                              REPO_ROOT / "scripts/wh3_queue.py")
queue = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(queue)

HEAD = "a" * 40
# Stands in for play: records its arguments in the output directory, then exits with the
# code passed as --exit (0 by default).
FAKE_PLAY = [sys.executable, "-c", (
    "import json, pathlib, sys; args = sys.argv[1:]; out = pathlib.Path(args[-1]); "
    "out.mkdir(); (out / 'args.json').write_text(json.dumps(args)); "
    "sys.exit(int(args[args.index('--exit') + 1]) if '--exit' in args else 0)")]


@pytest.fixture
def head(monkeypatch):
    revisions = [HEAD]
    monkeypatch.setattr(queue, "committed_revision",
                        lambda purpose, paths: revisions[0] if len(revisions) == 1
                        else revisions.pop(0))
    return revisions


def plan(tmp_path, *jobs, revision=HEAD):
    path = tmp_path / "screen-plan.json"
    path.write_text(json.dumps({"source_revision": revision, "jobs": [
        {"output": str(tmp_path / name), "args": args} for name, args in jobs]}))
    return path


def state(tmp_path):
    return json.loads((tmp_path / "screen-plan-state.json").read_text())


def test_runs_jobs_in_order_and_records_state(tmp_path, head):
    path = plan(tmp_path, ("a", ["--scenario", "kho5-dwf5", "--episodes", 2]),
                ("b", ["--policy", "hold"]))

    assert queue.run(path, FAKE_PLAY) == 0

    assert json.loads((tmp_path / "a/args.json").read_text()) == [
        "--scenario", "kho5-dwf5", "--episodes", "2", "--output", str(tmp_path / "a")]
    assert json.loads((tmp_path / "b/args.json").read_text())[:2] == ["--policy", "hold"]
    saved = state(tmp_path)
    assert saved["status"] == "completed" and saved["pid"] == os.getpid()
    assert saved["source_revision"] == HEAD and saved["error"] is None
    assert saved["completed"] == [{"output": str(tmp_path / "a"), "exit_code": 0},
                                  {"output": str(tmp_path / "b"), "exit_code": 0}]


def test_stops_at_the_first_failed_job_and_never_reruns(tmp_path, head):
    path = plan(tmp_path, ("a", ["--exit", "3"]), ("b", []))

    assert queue.run(path, FAKE_PLAY) == 1

    assert not (tmp_path / "b").exists()
    saved = state(tmp_path)
    assert saved["status"] == "failed" and saved["current_job"] is None
    assert saved["completed"] == [{"output": str(tmp_path / "a"), "exit_code": 3}]
    with pytest.raises(SystemExit, match="a plan runs once"):
        queue.run(path, FAKE_PLAY)


@pytest.mark.parametrize("comparison,stops", [
    ({"missing_or_changed": [], "resource_or_loadout_changes": {
        "friendly/f2/men": {"before": 45, "after": 44}}}, True),
    ({"missing_or_changed": ["enemy/e3"], "resource_or_loadout_changes": {}}, True),
    ({"missing_or_changed": [], "resource_or_loadout_changes": {},
      "units": {"friendly/f1": {"distance_m": 3.0, "bearing_deg": 0}}}, False),
])
def test_a_changed_rematch_start_stops_the_plan_but_geometry_does_not(tmp_path, head,
                                                                     comparison, stops):
    # The G1 rule: geometry flags stay in the result; other start changes stop later jobs.
    result = json.dumps({"start_comparison": {"flagged": True, **comparison}})
    fake = [sys.executable, "-c", (
        "import pathlib, sys; out = pathlib.Path(sys.argv[-1]) / 'episode-0001'; "
        f"out.mkdir(parents=True); (out / 'result.json').write_text({result!r})")]
    path = plan(tmp_path, ("a", []), ("b", []))

    assert queue.run(path, fake) == (1 if stops else 0)

    assert (tmp_path / "b").exists() is not stops
    saved = state(tmp_path)
    assert saved["status"] == ("failed" if stops else "completed")
    assert ("started differently" in (saved["error"] or "")) is stops


def test_checks_the_source_again_before_each_job(tmp_path, head):
    head[:] = [HEAD, HEAD, "b" * 40]  # a commit lands while the first job runs
    path = plan(tmp_path, ("a", []), ("b", []))

    assert queue.run(path, FAKE_PLAY) == 1

    assert (tmp_path / "a").exists() and not (tmp_path / "b").exists()
    assert "HEAD is " + "b" * 40 in state(tmp_path)["error"]


@pytest.mark.parametrize("problem", ["revision", "uncommitted", "output"])
def test_refuses_to_start(tmp_path, head, monkeypatch, problem):
    path = plan(tmp_path, ("a", []), ("b", []), revision="abc1234" if problem == "revision"
                else HEAD)
    if problem == "uncommitted":
        def dirty(purpose, paths):
            assert "src/twwarhammer3" in paths and "scripts/wh3_queue.py" in paths
            raise ValueError("Commit implementation changes before running a plan: M x")
        monkeypatch.setattr(queue, "committed_revision", dirty)
    if problem == "output":
        (tmp_path / "b").mkdir()

    with pytest.raises(SystemExit):
        queue.run(path, FAKE_PLAY)

    assert not (tmp_path / "a").exists()
    assert not (tmp_path / "screen-plan-state.json").exists()


def test_sigterm_interrupts_the_running_job_once(tmp_path, head):
    # The job signals the runner, then waits; the runner must pass it SIGINT.
    job = [sys.executable, "-c",
           "import os, signal, time; os.kill(os.getppid(), signal.SIGTERM); time.sleep(30)"]
    path = plan(tmp_path, ("a", []), ("b", []))

    assert queue.run(path, job) == 130

    saved = state(tmp_path)
    assert saved["status"] == "interrupted"
    assert saved["completed"] == [{"output": str(tmp_path / "a"), "exit_code": -signal.SIGINT}]
    assert signal.getsignal(signal.SIGTERM) == signal.SIG_DFL
    assert signal.getsignal(signal.SIGINT) == signal.default_int_handler


def test_a_stop_while_a_job_starts_still_interrupts_it(tmp_path, head, monkeypatch):
    class StoppedWhileStarting(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            os.kill(os.getpid(), signal.SIGTERM)  # handled before the runner holds the job
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(queue.subprocess, "Popen", StoppedWhileStarting)
    path = plan(tmp_path, ("a", []), ("b", []))

    assert queue.run(path, [sys.executable, "-c", "import time; time.sleep(30)"]) == 130

    assert state(tmp_path)["completed"] == [{"output": str(tmp_path / "a"),
                                             "exit_code": -signal.SIGINT}]
