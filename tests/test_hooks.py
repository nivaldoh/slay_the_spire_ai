"""The Claude Code hooks in scripts/hooks/ (docs/workflow.md, stage 4), without Claude Code.

References: AGENTS.md (no `ruff format` on hand-formatted files; commit nothing in this tree
while a WH3 queue runs; check.py before each commit) and Claude Code's hook contract (exit 2
blocks; `stop_hook_active` marks a stop that follows a block).
"""
import importlib.util
import json
import os
import signal
import subprocess
import sys
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
    ("uvx ruff@0.6.9 format src", False, True),  # uvx's way to pin a version
    ("uvx ruff@latest format --check .", False, False),
    ("uvx ruff==0.6.9 format src", False, True),
    ("uvx 'ruff>=0.6' format src", False, True),
    ("uvx ruff-api format x.py", False, False),  # another package
    ("uvx 'ruff >= 0.6' format src", False, True),
    ("uvx 'ruff[all]==0.6.9' format src", False, True),
    ("uvx Ruff format src", False, True),
    ("cat >runs/x.txt<<'EOF'\nruff format is banned\nEOF", False, False),  # heredoc after a word
    ("uv run --locked --extra llm ruff format src/x.py", False, True),
    ("uv run --locked -q ruff format x.py", False, True),
    ("find src -name '*.py' -exec ruff format {} +", False, True),
    ("ls *.py | xargs -P 4 ruff format", False, True),
    ("echo $((x<<2))\ngit commit -m y", True, True),  # a shift inside (( )) hides nothing
    ("git switch main", True, True),
    ("git pull", True, True),
    ("git cherry-pick abc", True, True),
    ("git revert HEAD", True, True),
    ("git am fix.patch", True, True),
])
def test_bash_hook_refuses_ruff_format_and_head_moves_during_a_queue(command, queue, blocked,
                                                                    tmp_path, monkeypatch):
    # A main checkout of its own: run from a linked worktree, the repository's own root has a
    # .git file, which the hook rightly treats as another tree.
    monkeypatch.setattr(pre_bash, "ROOT", tmp_path)
    (tmp_path / ".git").mkdir()
    assert (pre_bash.refusal(command, queue=queue, cwd=tmp_path) is not None) is blocked


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
    assert stop_check.main(recorder(runs, True), {"session_id": "B"}) == 0  # B's pass ...
    (repo / "a.py").write_text("a = 3\n")
    assert stop_check.main(recorder(runs, False), a_stop) == 2  # ... ends A's old flag too


def test_a_pass_by_any_session_ends_the_old_block_flags(repo):
    repo, _ = repo
    runs = []
    (repo / "a.py").write_text("a = 2\n")
    assert stop_check.main(recorder(runs, False), {"session_id": "A"}) == 2  # A is flagged
    assert stop_check.main(recorder(runs, True), {"session_id": "B"}) == 0  # B's check passes
    (repo / "a.py").write_text("a = 3\n")
    assert stop_check.main(recorder(runs, False),
                           {"session_id": "A", "stop_hook_active": True}) == 2  # checked again


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


@pytest.mark.parametrize("sub", ["play", "launch", "menu", "rl"])
def test_each_wh3_game_command_is_a_game_job(tmp_path, sub):
    (tmp_path / "30").mkdir()
    (tmp_path / "30/cmdline").write_bytes(f"/v/bin/python\0-m\0twwarhammer3\0{sub}\0".encode())
    assert stop_check.game_job_running(tmp_path)


@pytest.mark.parametrize("stdin,code", [
    (json.dumps({"tool_input": {"command": "uv run ruff format x.py"}}), 2),
    (json.dumps({"tool_input": {"command": "ls"}}), 0),
    ("not json", 0),
])
def test_the_bash_hook_blocks_through_exit_2_only(stdin, code):
    done = subprocess.run([sys.executable, str(ROOT / "scripts/hooks/pre_bash.py")], input=stdin,
                          capture_output=True, text=True)
    assert done.returncode == code and ("ruff format" in done.stderr) is (code == 2)


def test_both_tools_register_the_stop_and_bash_hooks():
    for name in (".claude/settings.json", ".codex/hooks.json"):
        config = json.loads((ROOT / name).read_text())["hooks"]
        assert "stop_check.py" in json.dumps(config.get("Stop"))
        assert "pre_bash.py" in json.dumps(config.get("PreToolUse"))


def test_an_unreadable_cache_means_check_again(repo):
    repo, _ = repo
    runs = []
    (repo / "runs/checks").mkdir(parents=True)
    for content in ("", "{trunc", "[]", '{"failed": "x", "blocked": true}'):  # last: old format
        (repo / "runs/checks/stop-hook.json").write_text(content)
        assert stop_check.main(recorder(runs, False), {"stop_hook_active": True}) == 2
        (repo / "runs/checks/stop-hook.json").unlink()
    assert runs == [False] * 4


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


def test_the_stop_check_gives_up_before_the_tools_stop_the_hook():
    # Past the tool's own timeout the tool kills the hook, which then gives no answer
    for name in (".claude/settings.json", ".codex/hooks.json"):
        stop = json.loads((ROOT / name).read_text())["hooks"]["Stop"]
        timeouts = [h["timeout"] for group in stop for h in group["hooks"]
                    if "stop_check.py" in h["command"]]
        assert timeouts and all(stop_check.TIMEOUT_S < t for t in timeouts), name


def test_stop_hook_does_not_accept_a_tree_changed_during_a_passing_check(repo, capsys):
    repo, _ = repo
    before = stop_check.tree_identity()
    calls = []

    def edited_during_check():
        calls.append((repo / "a.py").read_text())
        (repo / "a.py").write_text("a = (\n")  # a concurrent editor, after the test read
        return True, "result    PASSED"

    session = {"session_id": "editor"}
    assert stop_check.main(edited_during_check, session) == 2
    report = capsys.readouterr().err
    assert "changed" in report and "unchecked" in report
    cache = stop_check.read_cache()
    assert "passed" not in cache
    assert stop_check.tree_identity() != before

    # Preserve the existing single-block escape, without claiming the check passed.
    assert stop_check.main(edited_during_check, {**session, "stop_hook_active": True}) == 0
    assert "pass" in json.loads(capsys.readouterr().out)["systemMessage"]
    assert calls == ["a = 1\n"]

    # A fresh stop must check the edited tree, even if the file has since been repaired.
    (repo / "a.py").write_text("a = 2\n")
    assert stop_check.main(recorder(calls, True), session) == 0
    assert stop_check.read_cache()["passed"] == stop_check.tree_identity()
    assert stop_check.main(recorder(calls, True), session) == 0
    assert calls == ["a = 1\n", True]


@pytest.mark.parametrize("interruption", [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize("stage", ["running", "handle", "constructor"])
def test_interrupted_stop_hook_kills_and_reaps_its_check(repo, interruption, stage):
    repo, _ = repo
    script = repo / "scripts/hooks/stop_check.py"
    script.parent.mkdir(parents=True)
    script.write_bytes((ROOT / "scripts/hooks/stop_check.py").read_bytes())
    (repo / "runs").mkdir(exist_ok=True)
    child_file = repo / "runs/check-child.pid"
    uv = repo / "bin/uv"
    uv.parent.mkdir()
    # Substitute only uv, so the real hook's entry point, signal handling and process
    # cleanup run without invoking the suite or depending on its duration.
    uv.write_text(f"#!{sys.executable}\nimport os, time\nfrom pathlib import Path\n"
                  f"ready = Path({str(child_file)!r})\npending = ready.with_suffix('.tmp')\n"
                  "pending.write_text(str(os.getpid()))\npending.replace(ready)\ntime.sleep(60)\n")
    uv.chmod(0o755)
    event = repo / "event.json"
    event.write_text("{}")
    child = None
    command = [sys.executable, str(script)]
    if stage != "running":
        # Pause after construction or signal at its return, before the handle is stored.
        # Both are real interruption windows; the child must be owned before exit.
        boundary = script.read_text().splitlines().index(
            "        out, err = process.communicate(timeout=TIMEOUT_S)") + 1
        condition = (f"event == 'line' and frame.f_code.co_filename == {str(script)!r} "
                     f"and frame.f_lineno == {boundary}" if stage == "handle" else
                     "event == 'return' and frame.f_code.co_name == '__init__' "
                     "and isinstance(frame.f_locals.get('self'), subprocess.Popen) "
                     "and frame.f_back.f_code.co_name == 'run_check'")
        action = ("        while True: time.sleep(0.01)\n" if stage == "handle" else
                  f"        while not Path({str(child_file)!r}).exists(): time.sleep(0.01)\n"
                  f"        os.kill(os.getpid(), {int(interruption)})\n")
        trace = ("import os, runpy, subprocess, sys, time\nfrom pathlib import Path\n"
                 "def trace(frame, event, arg):\n"
                 f"    if {condition}:\n" + action +
                 "    return trace\n"
                 f"sys.settrace(trace)\nrunpy.run_path({str(script)!r}, run_name='__main__')\n")
        command = [sys.executable, "-c", trace]
    with event.open() as stdin:
        process = subprocess.Popen(command, stdin=stdin,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env={**os.environ, "PATH": f"{uv.parent}:{os.environ['PATH']}"})
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                child = int(child_file.read_text())
                break
            except (OSError, ValueError):
                if process.poll() is not None:
                    break
                time.sleep(0.01)
        assert child is not None, "hook did not start its stub check"
        if stage != "constructor":
            process.send_signal(interruption)
        process.communicate(timeout=5)
        assert process.returncode != 0
        with pytest.raises(ProcessLookupError):
            os.kill(child, 0)
        assert not (repo / "runs/checks/stop-hook.json").exists()
    finally:
        # A broken implementation must fail the test without leaving its stub running.
        # Find an unpublished child while the hook still owns it (Linux/WSL, like /proc
        # in the production game-job guard); killing the hook first would orphan it.
        children = Path(f"/proc/{process.pid}/task/{process.pid}/children")
        try:
            owned = [int(pid) for pid in children.read_text().split()]
        except FileNotFoundError:
            owned = []
        if process.poll() is None:
            process.terminate()
        for pid in {*owned, *([child] if child is not None else [])}:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)


def test_the_git_hook_refuses_a_commit_until_check_py_passed_on_this_tree(tmp_path):
    (tmp_path / "scripts/githooks").mkdir(parents=True)
    for name in ("scripts/check.py", "scripts/githooks/pre-commit"):
        (tmp_path / name).write_bytes((ROOT / name).read_bytes())
    (tmp_path / "scripts/githooks/pre-commit").chmod(0o755)
    # as in the repository: the record and bytecode are ignored
    (tmp_path / ".gitignore").write_text("runs/\n__pycache__/\n")
    (tmp_path / "a.py").write_text("x = 1\n")

    def git(*args, cwd=tmp_path):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd,
                              capture_output=True, text=True)
    git("init", "-q")
    git("config", "core.hooksPath", "scripts/githooks")
    git("add", ".")
    refused = git("commit", "-qm", "base")
    assert refused.returncode != 0 and "check.py" in refused.stderr  # no record yet
    spec = importlib.util.spec_from_file_location("check_copy", tmp_path / "scripts/check.py")
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    (tmp_path / "runs/checks").mkdir(parents=True)
    record = tmp_path / "runs/checks/last-pass.json"
    record.write_text(json.dumps({"tree": check.tree_content(tmp_path)}))
    assert git("commit", "-qm", "base").returncode == 0
    (tmp_path / "a.py").write_text("x = 2\n")
    # any spelling: from another directory, with -C and -am
    assert git("-C", str(tmp_path), "commit", "-qam", "edit", cwd=ROOT).returncode != 0
    record.write_text(json.dumps({"tree": check.tree_content(tmp_path)}))
    assert git("commit", "-qam", "edit").returncode == 0
    with (tmp_path / "scripts/check.py").open("a") as script:
        script.write("def broken(:\n")
    record.write_text(json.dumps({"tree": check.tree_content(tmp_path)}))
    assert git("commit", "-qam", "broken").returncode != 0  # a broken check.py refuses
    (tmp_path / "scripts/check.py").write_bytes((ROOT / "scripts/check.py").read_bytes())
    linked = tmp_path.parent / "linked"
    assert git("worktree", "add", "-q", str(linked)).returncode == 0
    (linked / "a.py").write_text("x = 3\n")
    # a linked worktree needs its own record: the main checkout's does not count there
    assert git("commit", "-qam", "there", cwd=linked).returncode != 0
    (linked / "runs/checks").mkdir(parents=True)
    (linked / "runs/checks/last-pass.json").write_text(
        json.dumps({"tree": check.tree_content(linked)}))
    assert git("commit", "-qam", "there", cwd=linked).returncode == 0


LIVE_CHECKER_SCRIPTS = [
    "tests/twwarhammer3/check_wh3_army_setup.py",
    "tests/twwarhammer3/check_wh3_checkpoint.py",
    "tests/twwarhammer3/check_wh3_checkpoint_siege.py",
    "tests/twwarhammer3/check_wh3_restored_episode.py",
    "tests/twwarhammer3/team/check_wh3_team.py",
]


@pytest.mark.parametrize("script", LIVE_CHECKER_SCRIPTS)
def test_direct_live_checkers_are_game_jobs_except_help_and_recount(tmp_path, script):
    (tmp_path / "31").mkdir()
    cmdline = tmp_path / "31/cmdline"
    for arguments, running in [
        ([script, "--help"], False),
        ([script, "-h"], False),
        ([script, "--recount", "runs/saved"], False),
        ([script, "--recount=runs/saved"], False),
        ([script, "--output", "runs/live-check"], True),
        (["/repo/" + script, "--output", "runs/live-check"], True),
    ]:
        cmdline.write_bytes("\0".join(["/repo/.venv/bin/python", *arguments, ""]).encode())
        assert stop_check.game_job_running(tmp_path) is running


@pytest.mark.parametrize("flags", [
    ["-u", "-B"], ["-W", "ignore"], ["-X", "dev"], ["-Wignore", "-Xdev"], ["--"],
])
def test_direct_live_checkers_allow_ordinary_python_flags(tmp_path, flags):
    (tmp_path / "32").mkdir()
    arguments = ["/repo/.venv/bin/python3", *flags,
                 "tests/twwarhammer3/check_wh3_checkpoint.py", "--output", "runs/live-check", ""]
    (tmp_path / "32/cmdline").write_bytes("\0".join(arguments).encode())
    assert stop_check.game_job_running(tmp_path)


@pytest.mark.parametrize("arguments", [
    ["reader.py", "tests/twwarhammer3/check_wh3_checkpoint.py"],
    ["-c", "print('tests/twwarhammer3/check_wh3_checkpoint.py')"],
    ["-c", "pass", "tests/twwarhammer3/check_wh3_checkpoint.py"],
    ["-cpass", "tests/twwarhammer3/check_wh3_checkpoint.py"],
    ["-m", "json.tool", "tests/twwarhammer3/check_wh3_checkpoint.py"],
    ["-mjson.tool", "tests/twwarhammer3/check_wh3_checkpoint.py"],
    ["-W", "tests/twwarhammer3/check_wh3_checkpoint.py", "reader.py"],
    ["-h", "tests/twwarhammer3/check_wh3_checkpoint.py"],
    ["--help", "tests/twwarhammer3/check_wh3_checkpoint.py"],
])
def test_a_checker_path_in_python_reader_arguments_is_not_a_game_job(tmp_path, arguments):
    (tmp_path / "33").mkdir()
    (tmp_path / "33/cmdline").write_bytes(
        "\0".join(["/repo/.venv/bin/python", *arguments, ""]).encode())
    assert not stop_check.game_job_running(tmp_path)


@pytest.mark.parametrize("flags,running", [
    (["-BuW", "ignore"], True),
    (["-BuX", "dev"], True),
    (["-BuWignore", "-Xdev"], True),
    (["-?"], False),
    (["-Bh"], False),
    (["--help-env"], False),
    (["--help-xoptions"], False),
    (["--help-all"], False),
    (["-Bucpass"], False),
    (["-Bumjson.tool"], False),
    (["--unknown-python-flag"], False),
])
def test_live_checkers_follow_python_grouped_options_and_exits(tmp_path, flags, running):
    (tmp_path / "34").mkdir()
    arguments = ["/repo/.venv/bin/python", *flags,
                 "tests/twwarhammer3/check_wh3_checkpoint.py", "--output", "runs/live-check", ""]
    (tmp_path / "34/cmdline").write_bytes("\0".join(arguments).encode())
    assert stop_check.game_job_running(tmp_path) is running


@pytest.mark.parametrize("options,running", [
    (["--rec", "runs/saved"], False),
    (["--rec=runs/saved"], False),
    (["--he"], False),
    (["-hh"], False),
    (["--re", "runs/saved"], False),  # ambiguous between recount and resume: argparse exits
    (["--resume", "--output", "runs/live-check"], True),
    (["--res", "--output", "runs/live-check"], True),
])
def test_live_checker_argparse_prefixes_keep_resume_live(tmp_path, options, running):
    (tmp_path / "35").mkdir()
    arguments = ["/repo/.venv/bin/python", "tests/twwarhammer3/check_wh3_restored_episode.py",
                 *options, ""]
    (tmp_path / "35/cmdline").write_bytes("\0".join(arguments).encode())
    assert stop_check.game_job_running(tmp_path) is running
