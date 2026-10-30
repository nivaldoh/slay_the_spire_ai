"""Shared Stop hook (docs/workflow.md, stage 4): run scripts/check.py when the tree changed
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
replay, the queue or a known live-check script), the check is skipped to keep load off the game.
Help and evidence recounts of live-check scripts stay offline.
If the tree changes during a passing check, its final state is unchecked: block once and
remember no pass, so a fresh stop must check again.
Timeouts and interruptions kill and reap the check process group. SIGTERM uses the same
cleanup as Ctrl-C; SIGKILL cannot run Python cleanup.
"""
import getopt
import hashlib
import json
import os
import runpy
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
LIVE_CHECKERS = {"check_wh3_army_setup.py", "check_wh3_checkpoint.py",
                 "check_wh3_checkpoint_siege.py", "check_wh3_restored_episode.py",
                 "check_wh3_team.py"}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def tree_identity() -> str:
    digest = hashlib.sha256(git("rev-parse", "HEAD"))
    digest.update(git("diff", "--cached", "--binary"))
    digest.update(git("diff", "HEAD", "--binary"))
    for name in sorted(git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0")):
        if name:
            path = ROOT / name.decode()
            if path.is_symlink():
                digest.update(name + b"\0symlink\0" + os.fsencode(os.readlink(path)))
            elif path.is_file():
                digest.update(name + b"\0" + path.read_bytes())
    return digest.hexdigest()


def game_job_running(proc: Path = Path("/proc")) -> bool:
    """A Python game command, queue, or direct live checker (not help or recount)."""
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
        # CPython 3.13 `python --help`; Lib/getopt.py stops at the first script argument.
        try:
            options, script = getopt.getopt(
                argv[1:], "bBdEhiIOPqRsSuvVx?W:X:c:m:",
                ["help", "version", "help-env", "help-xoptions", "help-all",
                 "check-hash-based-pycs="])
        except getopt.GetoptError:
            continue
        if any(option in ("-c", "-m", "-h", "-?", "-V", "--version")
               or option.startswith("--help") for option, _ in options):
            continue
        if script and Path(script[0]).name in LIVE_CHECKERS:
            # Lib/argparse.py accepts long-option prefixes; --resume still runs the game.
            checker_options = [arg.split("=", 1)[0] for arg in script[1:]]
            if not any(option.startswith("-h") or (option.startswith("--") and len(option) > 2
                       and ("--help".startswith(option) or "--recount".startswith(option)))
                       for option in checker_options):
                return True
    return False


def run_check() -> tuple[bool, str]:
    process = None
    pending = []

    def defer(signum, _frame):
        pending.append(signum)

    try:
        # Popen can start the child before returning its handle. Defer interruption just
        # across construction, then deliver it with ownership established. Unlike blocking
        # signals with pthread_sigmask, this leaves the child's signal mask unchanged.
        handlers = {sig: signal.signal(sig, defer) for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            process = subprocess.Popen(CHECK_COMMAND, cwd=ROOT,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                       start_new_session=True)
        finally:
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
        if pending:
            signal.raise_signal(pending[0])
        out, err = process.communicate(timeout=TIMEOUT_S)
        passed = process.returncode == 0 and completed_check_pass()
    except BaseException:  # timeout, Ctrl-C or SIGTERM: no detached check left running
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)  # uv, check.py and the tests they started
            except ProcessLookupError:
                pass
            process.communicate()
        raise
    report = out.strip() or err.strip()[-2000:]
    if process.returncode == 0 and not passed:
        report = "scripts/check.py exited 0 without a matching completed pass record.\n" + report
    return passed, report


def read_cache() -> dict:
    try:
        value = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(value, dict):
        return {}
    if not isinstance(value.get("blocked"), list):  # a cache written before block flags per session
        value["blocked"] = []
    return value


def remember(cache: dict, session: str, *, block: bool = False, **value) -> None:
    """Write a verdict, keeping other Claude sessions' block flags (they share the tree)."""
    # A pass clears every session's flag: the failure the flags were for is gone.
    kept = [] if "passed" in value else [s for s in cache.get("blocked", []) if s != session]
    blocked = kept + ([session] if block else [])
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({**value, "blocked": blocked}))


def say(message: str) -> int:
    print(json.dumps({"systemMessage": message}))
    return 0


def completed_check_pass() -> bool:
    """A completed pass on current contents; rests on JUDGEMENT? scripts/check.py Checked tree
    and Concurrent passes."""
    try:
        gate = runpy.run_path(str(ROOT / "scripts/check.py"))
        record = json.loads((ROOT / gate["CHECKED"]).read_text())
        return isinstance(record, dict) and record.get("tree") == gate["tree_content"](ROOT)
    except SystemExit as error:
        if error.code == 143:  # also a reader could raise it; preserve the SIGTERM handler
            raise
        return False
    except Exception:
        return False


def main(check=run_check, event: dict | None = None, jobs=None) -> int:
    event, jobs = event or {}, jobs or game_job_running
    try:
        identity = tree_identity()
        cache = read_cache()
        if cache.get("passed") == identity:
            return 0
        session = str(event.get("session_id", ""))
        proven = completed_check_pass()
        current = tree_identity()
        if proven and current == identity:
            remember(cache, session, passed=identity)
            return 0
        identity = current
        if event.get("stop_hook_active") and session in cache.get("blocked", []):
            remember(cache, session, **{k: v for k, v in cache.items() if k != "blocked"})
            return say("scripts/check.py still failed to establish a pass at the last stop; "
                       "stopping anyway "
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
        if passed and tree_identity() != identity:
            passed = False
            report = ("The tree changed during scripts/check.py; the final tree is unchecked.\n"
                      + report)
        remember(cache, session, block=not passed,
                 **({"passed": identity} if passed else {"failed": identity}))
        if passed:
            return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return say(f"stop hook could not run check.py: {error}")
    print("scripts/check.py has no pass for the current tree. Fix failures that are yours; "
          "if another session changed it, say so and stop:\n" + report, file=sys.stderr)
    return 2


if __name__ == "__main__":
    # As in scripts/check.py's plants_main: termination must run the cleanup above.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    try:
        stdin_event = json.load(sys.stdin)
    except ValueError:
        stdin_event = {}
    sys.exit(main(event=stdin_event if isinstance(stdin_event, dict) else {}))
