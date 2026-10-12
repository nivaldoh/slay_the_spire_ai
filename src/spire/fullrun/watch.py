"""Wait for a full-run job's next event, so a background watcher wakes once per event.

    python -m spire watch runs/fullrun/<job>

Prints one line and exits when a run finishes (its row of the log table), when the newest
trace is unchanged for STALL_SECONDS while the job runs, when the job is not running, or when
no manifest appears within START_SECONDS (the runner refused; the job's log says why). It
only reads evidence.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from spire.fullrun.digest import table_row

STALL_SECONDS = 90
START_SECONDS = 60


def check(job: Path, seen: int) -> str | None:
    """The event line if anything happened since `seen` runs had finished, else None."""
    path = job / "manifest.json"
    if not path.exists():
        return None
    manifest = json.loads(path.read_text())
    status = manifest["status"]
    if len(manifest["runs"]) > seen:
        row = table_row(job / f"run-{seen:04d}")
        return row + ("" if status == "running" else f" job {status}")
    if status != "running":
        return f"job {status}"
    traces = list(job.glob("run-*/trace.jsonl"))
    if traces:
        newest = max(traces, key=lambda trace: trace.stat().st_mtime)
        age = time.time() - newest.stat().st_mtime
        if age > STALL_SECONDS:
            return f"STALL: {newest.parent.name} trace unchanged for {age:.0f} s"
    return None


def next_event(job: Path, poll: float = 15) -> str:
    path = job / "manifest.json"
    seen = len(json.loads(path.read_text())["runs"]) if path.exists() else 0
    started = time.monotonic()
    while (event := check(job, seen)) is None:
        if not path.exists() and time.monotonic() - started > START_SECONDS:
            log = job.with_name(f"{job.name}.log")
            tail = log.read_text().splitlines()[-3:] if log.exists() else ["no log"]
            return "NOT STARTED: " + " | ".join(tail)
        time.sleep(poll)
    return event
