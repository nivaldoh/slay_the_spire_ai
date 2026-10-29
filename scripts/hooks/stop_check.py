"""Claude Code Stop hook (docs/workflow.md, stage 4): run scripts/check.py when the tree changed
since its last run, and keep the turn going while it fails.

The tree's identity is HEAD, the diff against it and the untracked files' contents (ignored
files such as runs/ are left out). A pass is remembered per identity in runs/checks/, so an
unchanged tree is not rechecked; a failure is rerun at the next stop, in case it was a timing
flake. Exit 2 blocks the stop and shows the failure (Claude Code lets a stop through after
eight blocks in a row); a check that cannot run warns and lets the stop through.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "runs" / "checks" / "stop-hook.json"


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def tree_identity() -> str:
    digest = hashlib.sha256(git("rev-parse", "HEAD"))
    digest.update(git("diff", "HEAD", "--binary"))
    for name in sorted(git("ls-files", "--others", "--exclude-standard", "-z").split(b"\0")):
        if name and (ROOT / name.decode()).is_file():
            digest.update(name + b"\0" + (ROOT / name.decode()).read_bytes())
    return digest.hexdigest()


def run_check() -> tuple[bool, str]:
    result = subprocess.run(["uv", "run", "--locked", "python", "scripts/check.py"], cwd=ROOT,
                            capture_output=True, text=True, timeout=600)
    return result.returncode == 0, result.stdout.strip()


def main(check=run_check) -> int:
    try:
        identity = tree_identity()
        if CACHE.exists() and json.loads(CACHE.read_text()).get("passed") == identity:
            return 0
        passed, report = check()
        if passed:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps({"passed": identity}))
            return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"systemMessage": f"stop hook could not run check.py: {error}"}))
        return 0
    print("scripts/check.py fails on the current tree; fix it before stopping:\n" + report,
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
