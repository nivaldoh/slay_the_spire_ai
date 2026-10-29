"""Claude Code Stop hook (docs/workflow.md, stage 4): run scripts/check.py when the tree changed
since its last pass, and keep the turn going while it fails.

The tree's identity is HEAD, the index, the diff against HEAD and the untracked files'
contents (ignored files such as runs/ are left out). A pass is remembered per identity in
runs/checks/, so an unchanged tree is not rechecked; a failure is rerun at the next fresh
stop, in case it was a timing flake. Exit 2 blocks the stop and shows the failure. This hook
never blocks twice in a row: a stop after its own block (`stop_hook_active`, which another
Stop hook such as /goal's also sets, so the hook remembers its last answer) goes through with a
warning, so a failure Claude cannot fix (another session's change, a file a play job keeps
writing) costs one turn, not the session. A timed-out check is killed with its tests and not
retried on the same tree; a check that cannot run warns and lets the stop through. While a
game job runs (a WH3 or Spire play, launch, menu, RL phase, rollout, training, evaluation or
replay, or the queue), the check is skipped so its load stays off the game.
"""
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "runs" / "checks" / "stop-hook.json"
TIMEOUT_S = 600
CHECK_COMMAND = ["uv", "run", "--locked", "python", "scripts/check.py"]
# Commands that start or drive a game (`spire replay` is on the spire-restore-replay branch).
GAME_COMMANDS = {"twwarhammer3": ("play", "launch", "menu", "rl"),
                 "spire": ("play", "rollout", "train", "evaluate", "replay")}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def tree_identity() -> str:
    digest = hashlib.sha256(git("rev-parse", "HEAD"))
    digest.update(git("diff", "--cached", "--binary"))
    digest.update(git("diff", "HEAD", "--binary"))
    for name in sorted(git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0")):
        if name and (ROOT / name.decode()).is_file():
            digest.update(name + b"\0" + (ROOT / name.decode()).read_bytes())
    return digest.hexdigest()


def game_job_running(proc: Path = Path("/proc")) -> bool:
    """A Python process running a command of GAME_COMMANDS or the queue."""
    for cmdline in proc.glob("[0-9]*/cmdline"):
        try:
            argv = cmdline.read_bytes().decode(errors="replace").split("\0")
        except OSError:
            continue
        if not argv or not Path(argv[0]).name.startswith("python"):
            continue
        if any(Path(arg).name == "wh3_queue.py" for arg in argv[1:]):
            return True
        for i, arg in enumerate(argv[:-2]):
            if arg == "-m" and argv[i + 2] in GAME_COMMANDS.get(argv[i + 1], ()):
                return True
    return False


def run_check() -> tuple[bool, str]:
    process = subprocess.Popen(CHECK_COMMAND, cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               start_new_session=True)
    try:
        out, err = process.communicate(timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)  # uv, check.py and the tests they started
        process.communicate()
        raise
    report = out.strip() or err.strip()[-2000:]
    return process.returncode == 0, report


def read_cache() -> dict:
    try:
        value = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def remember(cache: dict, session: str, *, block: bool = False, **value) -> None:
    """Write a verdict, keeping other Claude sessions' block flags (they share the tree)."""
    blocked = [s for s in cache.get("blocked", []) if s != session] + ([session] if block else [])
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({**value, "blocked": blocked}))


def say(message: str) -> int:
    print(json.dumps({"systemMessage": message}))
    return 0


def main(check=run_check, event: dict | None = None, jobs=None) -> int:
    event, jobs = event or {}, jobs or game_job_running
    try:
        identity = tree_identity()
        cache = read_cache()
        if cache.get("passed") == identity:
            return 0
        session = str(event.get("session_id", ""))
        if event.get("stop_hook_active") and session in cache.get("blocked", []):
            remember(cache, session, **{k: v for k, v in cache.items() if k != "blocked"})
            return say("scripts/check.py still failed at the last stop; stopping anyway "
                       "(see runs/checks/)")
        if cache.get("timed_out") == identity:
            return say("scripts/check.py timed out on this tree before; not rerun")
        if jobs():
            return say("a game job runs: scripts/check.py skipped to keep its load off the game")
        try:
            passed, report = check()
        except subprocess.TimeoutExpired:
            remember(cache, session, timed_out=identity)
            return say(f"scripts/check.py timed out after {TIMEOUT_S} s; not rerun on this tree")
        remember(cache, session, block=not passed,
                 **({"passed": identity} if passed else {"failed": identity}))
        if passed:
            return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return say(f"stop hook could not run check.py: {error}")
    print("scripts/check.py fails on the current tree. Fix it if the failure is yours; if it "
          "comes from another session's change, say so and stop:\n" + report, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        stdin_event = json.load(sys.stdin)
    except ValueError:
        stdin_event = {}
    sys.exit(main(event=stdin_event if isinstance(stdin_event, dict) else {}))
