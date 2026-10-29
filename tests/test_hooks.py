"""The Claude Code hooks in scripts/hooks/ (docs/workflow.md, stage 4), without Claude Code.

References: AGENTS.md (no `ruff format` on hand-formatted files; commit nothing while a WH3
queue runs; check.py before each commit) and Claude Code's hook contract (exit 2 blocks).
"""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/hooks" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pre_bash, stop_check = load("pre_bash"), load("stop_check")


@pytest.mark.parametrize("command,queue,blocked", [
    ("uv run --locked ruff format src/twwarhammer3/battle/play.py", False, True),
    ("cd x && .venv/bin/ruff format .", False, True),
    ("uv run ruff format --diff src", False, False),
    ("ruff format --check .", False, False),
    ("grep -n 'ruff format' AGENTS.md", False, False),
    ("uv run --locked ruff check .", False, False),
    ("git commit -q -m 'x'", False, False),
    ("git commit -q -m 'x'", True, True),
    ("git add a.py && git -C /repo commit -m x", True, True),
    ("git log --oneline -3; git status --short", True, False),
    ("echo done | git -c core.pager=cat rebase main", True, True),
    ("git diff 'unclosed", False, False),
])
def test_bash_hook_refuses_ruff_format_and_head_moves_during_a_queue(command, queue, blocked):
    assert (pre_bash.refusal(command, queue=queue) is not None) is blocked


def test_a_running_queue_is_found_in_proc(tmp_path):
    (tmp_path / "12").mkdir()
    (tmp_path / "12/cmdline").write_bytes(b"python\0scripts/wh3_queue.py\0plan.json\0")
    (tmp_path / "13").mkdir()
    (tmp_path / "13/cmdline").write_bytes(b"python\0-m\0pytest\0")
    assert pre_bash.queue_running(tmp_path)
    (tmp_path / "12/cmdline").write_bytes(b"bash\0")
    assert not pre_bash.queue_running(tmp_path)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / ".gitignore").write_text("runs/\n")
    (tmp_path / "a.py").write_text("a = 1\n")
    git("add", ".")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    monkeypatch.setattr(stop_check, "ROOT", tmp_path)
    monkeypatch.setattr(stop_check, "CACHE", tmp_path / "runs/checks/stop-hook.json")
    return tmp_path


def test_stop_hook_checks_a_changed_tree_once_and_reruns_a_failure(repo, capsys):
    runs = []

    def check(verdict):
        def run():
            runs.append(verdict)
            return verdict, f"result    {'PASSED' if verdict else 'FAILED'}"
        return run
    assert stop_check.main(check(True)) == 0
    assert stop_check.main(check(True)) == 0 and runs == [True]  # unchanged: not rerun
    (repo / "runs/scratch.log").write_text("ignored files do not count")
    assert stop_check.main(check(True)) == 0 and runs == [True]
    for change in (lambda: (repo / "a.py").write_text("a = 2\n"),
                   lambda: (repo / "new.py").write_text("b = 1\n"),
                   lambda: (repo / "new.py").write_text("b = 2\n")):
        change()
        assert stop_check.main(check(False)) == 2
        assert "FAILED" in capsys.readouterr().err
        assert stop_check.main(check(False)) == 2  # a failure is rerun, not cached
    assert runs == [True] + [False] * 6
    assert stop_check.main(check(True)) == 0 and stop_check.main(check(False)) == 0
    (repo / "new.py").write_text("b = 3\n")  # new untracked content after a pass is rechecked
    assert stop_check.main(check(False)) == 2


def test_stop_hook_lets_the_stop_through_when_the_check_cannot_run(repo, capsys):
    def broken():
        raise subprocess.TimeoutExpired("check.py", 600)
    assert stop_check.main(broken) == 0
    assert "could not run check.py" in json.loads(capsys.readouterr().out)["systemMessage"]
