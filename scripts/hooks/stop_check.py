"""Claude Code Stop hook (docs/workflow.md, stage 4): run scripts/check.py when the tree changed
since its last pass, and keep the turn going while it fails.

The tree's identity is HEAD, the index, the diff against HEAD and the untracked files'
contents (ignored files such as runs/ are left out). A pass is remembered per identity in
runs/checks/, so an unchanged tree is not rechecked; a failure is rerun at the next stop, in
case it was a timing flake. Exit 2 blocks the stop and shows the failure. A stop that follows
a block (`stop_hook_active`) on the same failing tree goes through with a warning, so a
failure Claude cannot fix (another session's change) does not hold the turn forever. A check
that cannot run warns and lets the stop through; a timed-out check is killed with its tests.
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


def main(check=run_check, event: dict | None = None) -> int:
    event = event or {}
    try:
        identity = tree_identity()
        cache = read_cache()
        if cache.get("passed") == identity:
            return 0
        if event.get("stop_hook_active") and cache.get("failed") == identity:
            print(json.dumps({"systemMessage": "scripts/check.py still fails on an unchanged "
                              "tree; stopping anyway (see runs/checks/)"}))
            return 0
        passed, report = check()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps({"passed" if passed else "failed": identity}))
        if passed:
            return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"systemMessage": f"stop hook could not run check.py: {error}"}))
        return 0
    print("scripts/check.py fails on the current tree. Fix it if the failure is yours; if it "
          "comes from another session's change, say so and stop:\n" + report, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        stdin_event = json.load(sys.stdin)
    except ValueError:
        stdin_event = {}
    sys.exit(main(event=stdin_event if isinstance(stdin_event, dict) else {}))
