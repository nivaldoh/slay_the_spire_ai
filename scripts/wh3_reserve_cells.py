"""Print one row per reserve episode and a tally per cell from saved jobs, read-only.

    uv run python scripts/wh3_reserve_cells.py JOB [JOB ...]

Reads each job's manifest.json and episode result.json, never the register, so jobs from
before its case column read the same as new ones. Version is the scenario name, case the
episode's own reserve draw, launch the game's process id: episodes of one launch rematch and
are not independent. Harness is the job name's version, or its source revision without one.
An outcome is the engine's, marked when the timer ended the battle. A job with no reserve_draws
stops the script before anything prints.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from twwarhammer3.battle import stats

COLUMNS = ("version", "policy", "model", "effort", "harness", "mode", "age/interval s", "case",
           "launch", "outcome", "seconds", "invalid", "own men", "enemy men")


def men(result: dict, side: str):
    """The side's men at the end; a failed episode may have no final count."""
    return ((result.get("final") or {}).get(side) or {}).get("men", "")


def cells(job: Path) -> list[tuple]:
    """One row of COLUMNS per episode of a job, in episode order."""
    manifest = json.loads((job / "manifest.json").read_text())
    if not manifest.get("reserve_draws"):
        raise SystemExit(f"{job}: no reserve_draws, so this job has no reserve cells")
    rows = []
    for episode in sorted(path for path in job.glob("episode-*") if path.is_dir()):
        result = json.loads((episode / "result.json").read_text())
        record = stats.row(job, episode)
        # cannae-comparison.md: "Engine wins remain wins, including alternative tactics and
        # timer endings", with the first-ending condition shown beside them.
        outcome = record["outcome"] + " (time_limit)" * (record["ended_by"] == "time_limit")
        rows.append((
            record["scenario"],
            " ".join(filter(None, (record["policy"].split(":")[-1], record["configuration"]))),
            *stats.conditions(record), record["case"],
            (manifest.get("game") or {}).get("pid", ""), outcome,
            result["battle_ms"] / 1000 if "battle_ms" in result else "",
            result.get("invalid", ""), men(result, "friendly"), men(result, "enemy")))
    return rows


def table(header: tuple, rows: list) -> str:
    return "\n".join("| " + " | ".join(map(str, row)) + " |"
                     for row in (header, ("---",) * len(header), *rows))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("jobs", type=Path, nargs="+", metavar="JOB", help="a job directory")
    args = parser.parse_args(argv)
    rows = [row for job in args.jobs for row in cells(job)]
    # Rests on JUDGEMENT? src/twwarhammer3/battle/stats.py Summary identity.
    # JUDGEMENT?: Cell tally — Claude, 2026-11-05: a cell keeps apart all a summary row does, the
    # revision too, so a repeat at a later commit is a new cell. By policy and case alone v2's Hold
    # wins pool with v3's Hold losses. Every wins-per-cell reading rests on this key.
    cell = COLUMNS.index("launch")
    tally = defaultdict(Counter)
    for row in rows:
        tally[row[:cell]][row[COLUMNS.index("outcome")]] += 1
    print(table(COLUMNS, rows))
    print()
    print(table((*COLUMNS[:cell], "attempts", "outcomes"), [
        (*cell, sum(outcomes.values()),
         ", ".join(f"{name} {count}" for name, count in sorted(outcomes.items())))
        for cell, outcomes in sorted(tally.items())]))


if __name__ == "__main__":
    main()
