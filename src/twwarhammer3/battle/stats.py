"""The committed results register, docs/twwarhammer3/results.csv, and its summary.

One row per episode, appended by ``play`` as each episode ends. Rows come only from the
job's manifest and the episode's result.json, so the register can be rebuilt from
runs/twwarhammer3/battle.
"""

import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

from gameai.provenance import REPO_ROOT

RESULTS_PATH = REPO_ROOT / "docs/twwarhammer3/results.csv"
JOBS_ROOT = REPO_ROOT / "runs/twwarhammer3/battle"
FIELDS = [
    "date", "job", "episode", "scenario", "model", "effort", "harness", "source", "mode",
    "speed", "interval_s", "outcome", "battle_s", "decisions", "invalid", "delay_s", "usd",
]


def harness_version(job: str) -> str:
    match = re.search(r"-v(\d+(?:\.\d+)*)-", job)
    return match.group(1) if match else ""


def row(job: Path, episode: Path) -> dict:
    manifest = json.loads((job / "manifest.json").read_text())
    result = json.loads((episode / "result.json").read_text())
    config = manifest["config"]
    llm = config.get("policy") == "llm"
    delays = result.get("delays_ms") or []
    return {
        "date": manifest["created_at"][:10],
        "job": job.name,
        "episode": episode.name,
        "scenario": config.get("scenario", ""),
        "model": config.get("model", "") if llm else config.get("policy", ""),
        "effort": config.get("effort", "") if llm else "",
        "harness": harness_version(job.name),
        "source": manifest["source_revision"][:7],
        "mode": "paused" if config.get("pause") else "realtime",
        "speed": config.get("speed", 1),
        "interval_s": config.get("interval_ms", 0) / 1000,
        "outcome": result["status"],
        "battle_s": round(result.get("battle_ms", 0) / 1000),
        "decisions": result.get("decisions", 0),
        "invalid": result.get("invalid", 0),
        "delay_s": round(statistics.mean(delays) / 1000, 2) if delays else "",
        "usd": round((result.get("llm") or {}).get("usd", 0), 4),
    }


def record(path: Path, job: Path, episode: Path) -> None:
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row(job, episode))


def rebuild(root: Path, path: Path) -> int:
    rows = []
    for manifest in sorted(root.glob("*/manifest.json")):
        job = manifest.parent
        created = json.loads(manifest.read_text())["created_at"]
        for result in sorted(job.glob("episode-*/result.json")):
            rows.append((created, row(job, result.parent)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        writer.writeheader()
        for _, item in sorted(rows, key=lambda pair: pair[0]):
            writer.writerow(item)
    return len(rows)


def summary(path: Path) -> str:
    groups = defaultdict(list)
    with path.open(newline="") as handle:
        for item in csv.DictReader(handle):
            groups[(item["scenario"], item["model"], item["effort"], item["harness"],
                    item["mode"])].append(item)
    lines = ["| Scenario | Model | Effort | Harness | Mode | Episodes | Won | Lost | Draw | "
             "Other | Mean battle s | Mean delay s | USD |", "|" + "---|" * 13]
    for key, items in sorted(groups.items()):
        outcomes = [item["outcome"] for item in items]
        battle = [float(item["battle_s"]) for item in items if item["battle_s"]]
        delays = [float(item["delay_s"]) for item in items if item["delay_s"]]
        usd = sum(float(item["usd"] or 0) for item in items)
        lines.append("| " + " | ".join([
            *key, str(len(items)), str(outcomes.count("won")), str(outcomes.count("lost")),
            str(outcomes.count("draw")),
            str(sum(o not in ("won", "lost", "draw") for o in outcomes)),
            f"{statistics.mean(battle):.0f}" if battle else "",
            f"{statistics.mean(delays):.1f}" if delays else "", f"{usd:.2f}",
        ]) + " |")
    return "\n".join(lines)
