"""The full-run results register: one CSV row per played run, committed with the log.

    python -m spire stats             milestones per character, ascension, model, effort, harness
    python -m spire stats --rebuild   rewrite the register from every job under runs/fullrun

`spire play` appends a row after each run. Rows come only from saved evidence (the job's
manifest, the run's result and the first in-game state in its trace), so a rebuild
reproduces them. The harness version comes from the job name, <model>-v<N>-<seeds>-<date>.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from gameai.provenance import REPO_ROOT

RESULTS_PATH = REPO_ROOT / "docs/spire/fullrun/results.csv"
JOBS_ROOT = REPO_ROOT / "runs/fullrun"
FIELDS = ["date", "job", "run", "seed", "character", "ascension", "model", "effort",
          "harness", "source", "outcome", "act", "floor", "score", "usd"]
GROUP = ("character", "ascension", "model", "effort", "harness")


def _start(run: Path) -> dict:
    """The engine's character and ascension, from the run's first in-game observation."""
    trace = run / "trace.jsonl"
    if trace.exists():
        with trace.open() as lines:
            for line in lines:
                raw = json.loads(line).get("raw") or {}
                if raw.get("in_game") and raw.get("game_state"):
                    state = raw["game_state"]
                    return {"character": state.get("class"),
                            "ascension": state.get("ascension_level")}
    return {}


def row(job: Path, run: Path) -> dict:
    manifest = json.loads((job / "manifest.json").read_text())
    result = json.loads((run / "result.json").read_text())
    harness = re.search(r"-v(\d+(?:\.\d+)*)-", job.name)
    usd = result.get("llm", {}).get("usd")
    return {
        "date": manifest["created_at"][:10],
        "job": job.name,
        "run": run.name,
        "seed": result["seed"],
        **_start(run),
        "model": manifest["config"].get("model"),
        "effort": manifest["config"].get("effort"),
        "harness": f"v{harness[1]}" if harness else None,
        "source": manifest["source_revision"][:7],
        "outcome": result["status"],
        "act": result.get("act"),
        "floor": result.get("floor"),
        "score": result.get("score"),
        "usd": None if usd is None else f"{usd:.4f}",
    }


def record(path: Path, job: Path, run: Path) -> None:
    """Append one run's row, with the header first in a new register."""
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerow(row(job, run))


def rebuild(root: Path, path: Path) -> None:
    """Rewrite the register from every saved job, in the order ``record`` appends."""
    jobs = sorted((json.loads((job / "manifest.json").read_text())["created_at"], job)
                  for job in root.iterdir() if (job / "manifest.json").exists())
    path.unlink(missing_ok=True)
    for _, job in jobs:
        for run in sorted(job.glob("run-*")):
            if (run / "result.json").exists():
                record(path, job, run)


# JUDGEMENT: Milestones — assistant, 2026-10-12 (flagged by Claude, 2026-10-28): runs, acts reached
# and best floor count every register row, unscored failures included; the mean floor counts only
# won and lost runs. Other choices change every version comparison in `spire stats`.
def summary(path: Path) -> str:
    """Milestones per group: runs reaching each act count however they ended, while
    finished runs (and the mean floor) are only engine-confirmed wins and deaths."""
    with path.open(newline="") as handle:
        groups: dict[tuple, list[dict]] = {}
        for entry in csv.DictReader(handle):
            groups.setdefault(tuple(entry[key] for key in GROUP), []).append(entry)
    lines = [
        "| Character | Asc | Model | Effort | Harness | Runs | Finished | Act 2 | Act 3 | Act 4 "
        "| Wins | Best floor | Mean floor |",
        "|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, runs in groups.items():
        acts = [int(run["act"] or 0) for run in runs]
        finished = [int(run["floor"] or 0) for run in runs if run["outcome"] in ("won", "lost")]
        cells = [
            *key, len(runs), len(finished), *(sum(act >= n for act in acts) for n in (2, 3, 4)),
            sum(run["outcome"] == "won" for run in runs),
            max(int(run["floor"] or 0) for run in runs),
            f"{sum(finished) / len(finished):.1f}" if finished else "",
        ]
        lines.append("| " + " | ".join(map(str, cells)) + " |")
    return "\n".join(lines)
