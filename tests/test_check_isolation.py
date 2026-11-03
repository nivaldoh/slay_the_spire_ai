"""Concurrent gates must preserve another gate's scratch, across PID namespaces too.

Two subprocesses share a disposable checkout and report namespace-local PIDs. The first
test waits on a file so the second gate has a real live run to collide with; no game runs.
"""

import importlib.util
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check.py"


@pytest.mark.parametrize("failure", ["directory", "flock"])
def test_lock_failure_invalidates_the_previous_pass(tmp_path, monkeypatch, failure):
    spec = importlib.util.spec_from_file_location("gate_lock_failure", SCRIPT)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["check.py"])
    receipt = tmp_path / gate.CHECKED
    receipt.parent.mkdir(parents=True)
    receipt.write_text('{"tree": "previous pass"}\n')
    if failure == "directory":
        (receipt.parent / "gate.lock").mkdir()
    else:
        def denied(*_args):
            raise OSError("lock unavailable")
        monkeypatch.setattr(gate.fcntl, "flock", denied)
    with pytest.raises(OSError):
        gate.main()
    assert not receipt.exists(), "a failed lock attempt left the old pass available"


def wait_for(path, processes, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.exists():
            return True
        if any(process.poll() is not None for process in processes):
            return False
        time.sleep(0.01)
    return False


@pytest.mark.parametrize("terminate_first", [False, True])
def test_overlapping_gates_keep_active_scratch_and_release_after_exit(tmp_path, terminate_first):
    repo, marks = tmp_path / "repo", tmp_path / "marks"
    (repo / "tests").mkdir(parents=True)
    (repo / "docs").mkdir()
    marks.mkdir()
    (repo / ".gitignore").write_text("runs/\n__pycache__/\n.pytest_cache/\n.ruff_cache/\n")
    (repo / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
    (repo / "docs/state.md").write_text("# State\n")
    (repo / "docs/agreed-checks.md").write_text("")
    (repo / "docs/page.md").write_text("JUDGE" + "MENT: Example — Test, 2026-11-02: fixture.\n")
    (repo / "tests/test_wait.py").write_text(
        "import os\nimport time\nfrom pathlib import Path\n\n"
        "def test_wait():\n"
        "    marks = Path(os.environ['GATE_MARKS'])\n"
        "    label = os.environ['GATE_LABEL']\n"
        "    (marks / (label + '.running')).touch()\n"
        "    deadline = time.monotonic() + 20\n"
        "    while not (marks / (label + '.release')).exists():\n"
        "        assert time.monotonic() < deadline, 'parent did not release test'\n"
        "        time.sleep(0.01)\n")
    for args in (("init", "-q"), ("add", "."),
                 ("-c", "user.name=test", "-c", "user.email=test@test", "commit", "-qm", "base")):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    runner = tmp_path / "gate.py"
    runner.write_text(
        "import importlib.util\nimport os\nimport sys\nfrom pathlib import Path\n"
        "spec = importlib.util.spec_from_file_location('gate', sys.argv[1])\n"
        "gate = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(gate)\n"
        "gate.ROOT = Path(sys.argv[2])\n"
        "marks, label = Path(os.environ['GATE_MARKS']), os.environ['GATE_LABEL']\n"
        "gate.os.getpid = lambda: int(os.environ['GATE_PID'])\n"
        "original_run = gate.subprocess.run\n"
        "def run(command, *args, **kwargs):\n"
        "    if '-m' in command and 'pytest' in command:\n"
        "        (marks / (label + '.pytest')).touch()\n"
        "    return original_run(command, *args, **kwargs)\n"
        "gate.subprocess.run = run\n"
        "sys.argv = ['check.py']\n(marks / (label + '.entered')).touch()\n"
        "sys.exit(gate.main())\n")
    processes = []
    try:
        for label in ("first", "second"):
            # Equal PIDs reproduce two sandboxes; different invisible PIDs exercise pruning.
            pid = 999999900 + (label == "second" and terminate_first)
            process = subprocess.Popen(
                [sys.executable, str(runner), str(SCRIPT), str(repo)],
                env={**os.environ, "GATE_MARKS": str(marks), "GATE_LABEL": label,
                     "GATE_PID": str(pid)}, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, start_new_session=True)
            processes.append(process)
            assert wait_for(marks / f"{label}.entered", [process])
            if label == "first":
                assert wait_for(marks / "first.running", [process])
        entered_while_first_runs = wait_for(marks / "second.pytest", processes, seconds=1)
        if terminate_first:
            os.killpg(processes[0].pid, signal.SIGTERM)
        else:
            (marks / "first.release").touch()
        (marks / "second.release").touch()
        outputs = [process.communicate(timeout=15) for process in processes]
        assert not entered_while_first_runs, "second gate entered pytest during the active check"
        if not terminate_first:
            assert processes[0].returncode == 0, outputs[0]
        assert processes[1].returncode == 0, outputs[1]
        assert "1 passed" in outputs[1][0]
    finally:
        for label in ("first", "second"):
            (marks / f"{label}.release").touch()
        for process in processes:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
