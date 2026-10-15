"""Run a frozen plan of ``twwarhammer3 play`` jobs one at a time.

    uv run python scripts/wh3_queue.py PLAN.json

A plan names the full commit its jobs run on and, per job, the output directory
(relative to the repository root) and the other ``play`` arguments. Other keys, such as
a purpose, are for the reader:

    {
      "source_revision": "<full sha of HEAD>",
      "jobs": [
        {"output": "runs/twwarhammer3/battle/hold-kho5-20261015",
         "args": ["--scenario", "kho5-dwf5", "--policy", "hold"]},
        {"output": "runs/twwarhammer3/battle/llm-kho5-20261015",
         "args": ["--scenario", "kho5-dwf5", "--policy", "llm", "--budget-usd", "25"]}
      ]
    }

The runner refuses to start unless HEAD is that revision with no uncommitted changes in
the play source scope or this script, no job output exists and the plan has no state
file. It runs ``uv run python -m twwarhammer3 play ARGS --output OUTPUT`` per job,
checking the source again before each, and keeps PLAN-state.json beside the plan: its
pid, status (running, completed, failed or interrupted), the current job and each
finished job's exit code. It stops at the first job that exits nonzero, or whose rematch
started with a missing or changed unit or changed strength, loadout or resources
(``start_comparison`` in an episode's result.json; position and bearing flags alone do
not stop it), and never retries; a later attempt is a new plan. SIGINT or SIGTERM passes
one SIGINT to the running job, which records its own interruption, and marks the plan
interrupted.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from gameai.provenance import REPO_ROOT, committed_revision, write_json
from twwarhammer3.battle.play import SOURCES

PLAY = ["uv", "run", "python", "-m", "twwarhammer3", "play"]
SCOPE = (*SOURCES, "scripts/wh3_queue.py")
EXIT_CODES = {"completed": 0, "failed": 1, "interrupted": 130}


def source_error(revision: str) -> str | None:
    try:
        head = committed_revision("running a plan", SCOPE)
    except ValueError as exc:
        return str(exc)
    return None if head == revision else f"The plan is frozen to {revision!r}, HEAD is {head}"


def start_change(output: Path) -> str | None:
    """The first rematch whose start differs from the job's first one beyond geometry."""
    for path in sorted(output.glob("episode-*/result.json")):
        start = json.loads(path.read_text()).get("start_comparison") or {}
        changed = [*start.get("missing_or_changed", []),
                   *start.get("resource_or_loadout_changes", {})]
        if changed:
            return f"{path.parent} started differently: {', '.join(changed)}"
    return None


def run(plan_path: Path, play: list[str] = PLAY) -> int:
    plan = json.loads(plan_path.read_text())
    state_path = plan_path.with_name(plan_path.stem + "-state.json")
    if state_path.exists():
        raise SystemExit(f"{state_path} exists: a plan runs once, so write a new plan")
    if error := source_error(plan["source_revision"]):
        raise SystemExit(error)
    for job in plan["jobs"]:
        if (REPO_ROOT / job["output"]).exists():
            raise SystemExit(f"Output already exists: {job['output']}")
    state = {"pid": os.getpid(), "source_revision": plan["source_revision"], "completed": []}
    child, stopping, signalled = None, False, None

    def save(**values):
        state.update(values, updated_at=datetime.now(UTC).isoformat())
        write_json(state_path, state)

    def stop(signum, frame):
        nonlocal stopping, signalled
        if not stopping:
            stopping, signalled = True, child
            if child:
                child.send_signal(signal.SIGINT)  # uv passes it on to play

    handlers = {signum: signal.signal(signum, stop) for signum in (signal.SIGINT, signal.SIGTERM)}
    try:
        for job in plan["jobs"]:
            error = None if stopping else source_error(plan["source_revision"])
            if stopping or error:
                break
            save(status="running", current_job=job["output"])
            print("START", job["output"], flush=True)
            # Its own session: a terminal Ctrl+C reaches the job once, through stop().
            child = subprocess.Popen([*play, *map(str, job["args"]), "--output", job["output"]],
                                     cwd=REPO_ROOT, start_new_session=True)
            if stopping and signalled is not child:  # the stop came while this job started
                child.send_signal(signal.SIGINT)
            code = child.wait()
            state["completed"].append({"output": job["output"], "exit_code": code})
            if code:
                error = f"{job['output']} exited with {code}"
                break
            if error := start_change(REPO_ROOT / job["output"]):
                break
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
    status = "interrupted" if stopping else "failed" if error else "completed"
    save(status=status, current_job=None, error=error)
    print(status.upper(), error or "", flush=True)
    return EXIT_CODES[status]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("plan", type=Path, help="plan JSON; its state file goes beside it")
    return run(parser.parse_args().plan)


if __name__ == "__main__":
    sys.exit(main())
