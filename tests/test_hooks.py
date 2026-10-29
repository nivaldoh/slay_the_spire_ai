"""The Claude Code hooks in scripts/hooks/ (docs/workflow.md, stage 4), without Claude Code.

References: AGENTS.md (no `ruff format` on hand-formatted files; commit nothing in this tree
while a WH3 queue runs; check.py before each commit) and Claude Code's hook contract (exit 2
blocks; `stop_hook_active` marks a stop that follows a block).
"""
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/hooks" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pre_bash, stop_check = load("pre_bash"), load("stop_check")
NOTE = "cat > note.md <<'EOF'\nNever run ruff format here; git commit only after check.py.\nEOF"


@pytest.mark.parametrize("command,queue,blocked", [
    ("uv run --locked ruff format src/twwarhammer3/battle/play.py", False, True),
    ("cd x && .venv/bin/ruff format .", False, True),
    ("uv run ruff format --diff src", False, False),
    ("ruff format --check .", False, False),
    ("grep -n 'ruff format' AGENTS.md", False, False),
    ("uv run --locked ruff check .", False, False),
    ("git status\nuv run ruff format src", False, True),  # a newline separates commands
    ("ruff format src; echo it's done", False, True),  # unclosed quote: read as text
    (NOTE, False, False),  # a heredoc body is text
    (NOTE, True, False),
    ("git commit -q -F - <<'EOF'\nIt's the plan's fix\nEOF", False, False),
    ("git commit -q -F - <<'EOF'\nIt's the plan's fix\nEOF", True, True),
    ("git commit -q -m 'x'", False, False),
    ("git commit -q -m 'x'", True, True),
    ("git status\ngit commit -qm x", True, True),
    ("git add a.py && git -C . commit -m x", True, True),
    ("git log --oneline -3; git status --short", True, False),
    ("echo done | git -c core.pager=cat rebase main", True, True),
    ("GIT_AUTHOR_DATE=now timeout 60 git commit -m x", True, True),
    ("if true; then git commit -m x; fi", True, True),
    ("{ git merge main; }", True, True),
    ("git -C /tmp/elsewhere commit -m x", True, False),  # another tree's HEAD
    ("git diff 'unclosed", False, False),
    ('git commit -m "Refuse x\n\n- never ruff format here"', False, False),  # quoted newline
    ("# it's a note\ncat <<'EOF' > n.md\nruff format\nEOF", False, False),  # a comment's quote
    ("cat <<'END-NOTE' > n.md\nruff format\nEND-NOTE", False, False),
    ("git checkout -- src/a.py", True, False),
    ("git reset", True, False),
    ("git reset --hard HEAD~1", True, True),
    ("git checkout main", True, True),
    ("uv run ruff -q format src", False, True),  # options before format
    ("ruff --config pyproject.toml format src", False, True),
    ("echo a#b; uv run ruff format src", False, True),  # `#` inside a word
    ("n=${#a[@]}; git commit -m x", True, True),
    ("wc -c <<< hello\nuv run ruff format src", False, True),  # a here-string
    ("echo $((1<<2))\ngit commit -m y", True, True),  # a shift
    ("(cd /tmp && git status) && git commit -m x", True, True),  # a subshell's cd ends
    ("nice -n 10 git commit -m x", True, True),
    ("env -u FOO git commit -m x", True, True),
    ("git reset HEAD", True, False),
    ("git grep -n -e ruff -e format", False, False),  # ruff as a pattern, not the program
    ("echo ruff does not format", False, False),
    ("uvx ruff format x.py", False, True),
    ("cat >runs/x.txt<<'EOF'\nruff format is banned\nEOF", False, False),  # heredoc after a word
])
def test_bash_hook_refuses_ruff_format_and_head_moves_during_a_queue(command, queue, blocked):
    assert (pre_bash.refusal(command, queue=queue) is not None) is blocked


def test_a_linked_worktree_inside_the_repo_is_another_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(pre_bash, "ROOT", tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / "runs/scratch/src").mkdir(parents=True)
    (tmp_path / "home/wt").mkdir(parents=True)
    (tmp_path / "home/wt/.git").write_text("gitdir: elsewhere\n")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "runs/scratch/.git").write_text("gitdir: ../../.git/worktrees/scratch\n")
    assert pre_bash.refusal("git -C runs/scratch commit -m x", queue=True, cwd=tmp_path) is None
    assert pre_bash.refusal("cd runs/scratch && git commit -m x", queue=True, cwd=tmp_path) is None
    assert pre_bash.refusal("git -C runs/scratch/src commit -m x", queue=True, cwd=tmp_path) is None
    assert pre_bash.refusal("cd ~/wt && git commit -m x", queue=True, cwd=tmp_path) is None
    # Claude Code's own commit form, in another worktree, during a queue
    claude = 'cd ~/wt && git commit -m "$(cat <<\'EOF\'\nFix it\'s check\n\nEOF\n)"'
    assert pre_bash.refusal(claude, queue=True, cwd=tmp_path) is None
    assert pre_bash.refusal(claude.replace("cd ~/wt", "cd ."), queue=True, cwd=tmp_path)
    assert pre_bash.refusal("git commit -m x", queue=True, cwd=tmp_path)
    assert pre_bash.refusal("git -C runs commit -m x", queue=True, cwd=tmp_path)


def test_only_a_python_process_running_the_queue_script_is_a_queue(tmp_path):
    def proc(pid, *argv):
        (tmp_path / pid).mkdir()
        (tmp_path / pid / "cmdline").write_bytes("\0".join(argv).encode() + b"\0")
    proc("12", "/bin/bash", "-c", "until ! pgrep -f scripts/wh3_queue.py; do sleep 9; done")
    proc("13", "grep", "-n", "scripts/wh3_queue.py", "AGENTS.md")
    assert not pre_bash.queue_running(tmp_path)
    proc("14", "/repo/.venv/bin/python", "scripts/wh3_queue.py", "plan.json")
    assert pre_bash.queue_running(tmp_path)


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
    monkeypatch.setattr(stop_check, "game_job_running", lambda: False)
    return tmp_path, git


def recorder(runs, verdict):
    def run():
        runs.append(verdict)
        return verdict, f"result    {'PASSED' if verdict else 'FAILED'}"
    return run


def test_stop_hook_checks_a_changed_tree_once_and_reruns_a_failure(repo, capsys):
    repo, git = repo
    runs = []
    assert stop_check.main(recorder(runs, True)) == 0
    assert stop_check.main(recorder(runs, True)) == 0 and runs == [True]  # unchanged: not rerun
    (repo / "runs/scratch.log").write_text("ignored files do not count")
    assert stop_check.main(recorder(runs, True)) == 0 and runs == [True]
    for change in (lambda: (repo / "a.py").write_text("a = 2\n"),
                   lambda: (repo / "new.py").write_text("b = 1\n"),
                   lambda: (repo / "new.py").write_text("b = 2\n")):
        change()
        assert stop_check.main(recorder(runs, False)) == 2
        assert "FAILED" in capsys.readouterr().err
        assert stop_check.main(recorder(runs, False)) == 2  # a failure is rerun, not cached
    assert runs == [True] + [False] * 6
    assert stop_check.main(recorder(runs, True)) == 0
    for change in (lambda: (repo / "new.py").write_text("b = 3\n"),  # new untracked content
                   lambda: git("add", "a.py")):  # a staged change
        assert stop_check.main(recorder(runs, True)) == 0
        change()
        assert stop_check.main(recorder(runs, False)) == 2


def test_the_stop_hook_never_blocks_twice_in_a_row_but_keeps_checking(repo, capsys):
    # Under /goal every stop after the first carries stop_hook_active, whichever hook blocked.
    repo, _ = repo
    runs, active = [], {"stop_hook_active": True}
    (repo / "a.py").write_text("a = 2\n")
    assert stop_check.main(recorder(runs, False), active) == 2
    (repo / "a.py").write_text("a = 3\n")  # e.g. a play job appending to results.csv
    assert stop_check.main(recorder(runs, False), active) == 0
    assert "still failed" in capsys.readouterr().out and runs == [False]
    assert stop_check.main(recorder(runs, True), active) == 0 and runs == [False, True]
    (repo / "a.py").write_text("a = 4\n")
    assert stop_check.main(recorder(runs, False), active) == 2  # a new failure blocks again
    assert stop_check.main(recorder(runs, False), active) == 0  # the next stop goes through
    assert stop_check.main(recorder(runs, False), {}) == 2  # a fresh turn's stop checks again


def test_sessions_sharing_the_tree_keep_their_own_block_flags(repo, capsys):
    repo, _ = repo
    runs = []
    (repo / "a.py").write_text("a = 2\n")
    assert stop_check.main(recorder(runs, False), {"session_id": "A"}) == 2
    b_stop = {"session_id": "B", "stop_hook_active": True}  # B's /goal hook blocked before
    assert stop_check.main(recorder(runs, False), b_stop) == 2  # B's own first block
    a_stop = {"session_id": "A", "stop_hook_active": True}
    assert stop_check.main(recorder(runs, False), a_stop) == 0  # A's flag survived B's write
    assert runs == [False, False] and "still failed" in capsys.readouterr().out


def test_no_check_runs_beside_a_game_job_and_a_timeout_is_not_retried(repo, capsys):
    repo, _ = repo
    runs = []
    (repo / "a.py").write_text("a = 2\n")
    assert stop_check.main(recorder(runs, False), jobs=lambda: True) == 0
    assert "game job runs" in capsys.readouterr().out and runs == []

    def hangs():
        runs.append("hang")
        raise subprocess.TimeoutExpired("check.py", 600)
    assert stop_check.main(hangs) == 0 and stop_check.main(hangs) == 0
    assert runs == ["hang"] and "not rerun" in capsys.readouterr().out
    (repo / "a.py").write_text("a = 3\n")
    assert stop_check.main(recorder(runs, False)) == 2  # a new tree is checked again


def test_a_game_job_is_a_python_process_running_one(tmp_path):
    def proc(pid, *argv):
        (tmp_path / pid).mkdir()
        (tmp_path / pid / "cmdline").write_bytes("\0".join(argv).encode() + b"\0")
    proc("21", "/bin/bash", "-c", "uv run python -m twwarhammer3 play --output x")
    proc("22", "/repo/.venv/bin/python", "-m", "twwarhammer3", "stats")
    assert not stop_check.game_job_running(tmp_path)
    proc("23", "/repo/.venv/bin/python3", "-m", "spire", "rollout", "--output", "x")
    assert stop_check.game_job_running(tmp_path)


def test_an_unreadable_cache_means_check_again(repo):
    repo, _ = repo
    runs = []
    (repo / "runs/checks").mkdir(parents=True)
    for content in ("", "{trunc", "[]"):
        (repo / "runs/checks/stop-hook.json").write_text(content)
        assert stop_check.main(recorder(runs, False)) == 2
    assert runs == [False] * 3


def test_stop_hook_lets_the_stop_through_when_the_check_cannot_run(repo, capsys):
    def broken():
        raise FileNotFoundError("uv")
    assert stop_check.main(broken) == 0
    assert "could not run check.py" in json.loads(capsys.readouterr().out)["systemMessage"]


def test_a_timed_out_check_is_killed_with_its_children_and_stderr_is_reported(repo, monkeypatch):
    repo, _ = repo
    pids = repo / "pids"
    monkeypatch.setattr(stop_check, "TIMEOUT_S", 1)
    monkeypatch.setattr(stop_check, "CHECK_COMMAND", [
        "bash", "-c", f"sleep 60 & echo $! > {pids}; sleep 60"])
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        stop_check.run_check()
    assert time.monotonic() - started < 10  # not waiting on an orphaned child's output
    child = int(pids.read_text())
    time.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)
    monkeypatch.setattr(stop_check, "CHECK_COMMAND",
                        ["bash", "-c", "echo 'lock out of date' >&2; exit 2"])
    assert stop_check.run_check() == (False, "lock out of date")
