"""The committed results register, docs/twwarhammer3/results.csv, and its summary.

One row per episode, appended by ``play`` as each episode ends, from the job's manifest
and the episode's result.json. The register is committed history: rows are only appended.
"""

import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

from gameai.provenance import REPO_ROOT
from twwarhammer3.battle.benchmark import evaluate
from twwarhammer3.battle.controllers import policy_parts

RESULTS_PATH = REPO_ROOT / "docs/twwarhammer3/results.csv"
JOBS_ROOT = REPO_ROOT / "runs/twwarhammer3/battle"
FIELDS = [
    "date", "job", "episode", "scenario", "policy", "model", "effort", "harness", "source",
    "mode", "speed", "interval_s", "outcome", "battle_s", "own_left", "enemy_left",
    "decisions", "invalid", "delay_s", "usd", "battle_type", "victory_held", "supplies_left",
    "key_held", "reinforcements_by_type", "own_active", "enemy_active", "added_age_s",
    "ended_by", "provider", "configuration", "case",
]


def harness_version(job: str) -> str:
    """The version in a job name like ``llm-luna-v15-kho-...``; other names record none."""
    match = re.search(r"-v(\d+(?:\.\d+)*)-", job)
    return match.group(1) if match else ""


def left(result: dict, side: str):
    """The share of a side's men alive at the end (routing ones included), or ''."""
    final = (result.get("final") or {}).get(side) or {}
    return round(final["men"] / final["men0"], 2) if final.get("men0") else ""


def configuration(result: dict) -> str:
    """What the policy name leaves out: a composition's spec digest or an external class's
    source hash, 12 hex as the report labels them. Blank for every other policy."""
    card = result.get("card") or {}
    value = {"composed": (card.get("disclosure") or {}).get("configuration_sha256"),
             "external": card.get("source_sha256")}.get(card.get("kind"))
    return (value or "")[:12]


def members(result: dict, field: str) -> str:
    """The model, effort or provider a composition's member cards declare, joined by +."""
    cards = ((result.get("card") or {}).get("disclosure") or {}).get("member_controllers") or {}
    return "+".join(sorted({card[field] for card in cards.values() if card.get(field)}))


def reserve_case(manifest: dict, episode: Path) -> str:
    """This episode's own reserve draw as region/side/count; blank for a job without draws."""
    draws = manifest.get("reserve_draws")
    if not draws:
        return ""
    draw = draws[int(episode.name.split("-")[-1])]
    return f"{draw['region']}/{draw['side']}/{draw['count']}"


def row(job: Path, episode: Path) -> dict:
    manifest = json.loads((job / "manifest.json").read_text())
    result = json.loads((episode / "result.json").read_text())
    config = manifest["config"]
    if manifest.get("scenario", {}).get("benchmark"):
        result = {**result, "status": evaluate(result)["outcome"] or result["status"]}
    # A rotation's llm_rules@gpt-6-luna is policy llm_rules with its own model and effort.
    policy, model, effort = policy_parts(result.get("policy", config.get("policy", "")), config)
    provider = config.get("provider", "openai") if model else ""
    if policy == "configured":
        # Declared, not ran: these are the member cards, and two gap jobs of 2026-11-01 declare
        # Haiku yet recorded no model call. The job's flags are never read: every Cannae job has
        # a --model, and most of them have no model member.
        model, effort, provider = (members(result, field)
                                   for field in ("model", "effort", "provider"))
    delays = result.get("delays_ms") or []
    own, enemy = active_left(result, "friendly"), active_left(result, "enemy")
    return {
        "date": manifest["created_at"][:10],
        "job": job.name,
        "episode": episode.name,
        "scenario": config.get("scenario", ""),
        "policy": policy,
        "model": model or "",
        "effort": effort or "",
        "provider": provider,
        "harness": harness_version(job.name),
        "source": manifest["source_revision"][:7],
        "mode": "paused" if config.get("pause") else "realtime",
        "speed": config.get("speed", 1),
        "interval_s": config.get("interval_ms", 0) / 1000,
        "outcome": result["status"],
        "battle_s": round(result["battle_ms"] / 1000) if "battle_ms" in result else "",
        "own_left": left(result, "friendly"),
        "enemy_left": left(result, "enemy"),
        "decisions": result.get("decisions", 0),
        "invalid": result.get("invalid", 0),
        "delay_s": round(statistics.mean(delays) / 1000, 2) if delays else "",
        "usd": round((result.get("llm") or {}).get("usd", 0), 4),
        "battle_type": (manifest.get("scenario") or {}).get("battle_type", "classic"),
        "victory_held": (result.get("objectives") or {}).get("victory_held", ""),
        "supplies_left": (result.get("objectives") or {}).get("supplies_left", ""),
        "key_held": (result.get("objectives") or {}).get("key_held", ""),
        "reinforcements_by_type": json.dumps(result["objectives"]["reinforcements_by_type"],
                                            sort_keys=True)
        if (result.get("objectives") or {}).get("reinforcements_by_type") else "",
        "own_active": own if own == "" else round(own, 3),
        "enemy_active": enemy if enemy == "" else round(enemy, 3),
        "added_age_s": result.get("delay_ms", 0) / 1000,
        "ended_by": result.get("ended_by", ""),
        "configuration": configuration(result),
        "case": reserve_case(manifest, episode),
    }


def active_left(result: dict, side: str):
    """The unrounded share of a side's men neither routing nor shattered at the end, or ''."""
    final = (result.get("final") or {}).get(side) or {}
    if final.get("men0") and "active_men" in final:
        return final["active_men"] / final["men0"]
    return ""


def record(path: Path, job: Path, episode: Path) -> None:
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    if not new:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader) if reader.fieldnames != FIELDS else None
        if rows is not None:  # a register from before newer columns: rewrite its header
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, FIELDS, restval="", lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerow(row(job, episode))


def conditions(item: dict) -> tuple[str, str, str, str, str]:
    """Model, effort, harness, mode and age/interval of a row, recorded or from row(): what
    still keeps apart two rows of one scenario and policy."""
    model = item["model"]
    if item.get("provider") == "openrouter":
        model += " (OpenRouter)"
    # Jobs named without -vN- have no harness version: their source tells them apart.
    # Added age and decision interval are conditions (a blank age, before b1, was 0).
    timing = (f"{float(item.get('added_age_s') or 0):g}/"
              f"{float(item.get('interval_s') or 0):g}")
    return model, item["effort"], item["harness"] or item["source"], item["mode"], timing


def summary(path: Path) -> str:
    groups = defaultdict(list)
    with path.open(newline="") as handle:
        for item in csv.DictReader(handle):
            # JUDGEMENT?: Summary identity — Claude, 2026-11-05: rows pool only inside one scenario
            # and reserve case and one policy and configuration (the job, for configured rows from
            # before that column). Pooling across them changes every rate this table shows.
            identity = item.get("configuration") or (
                item["job"] if item["policy"] == "configured" else "")
            groups[(" ".join(filter(None, (item["scenario"], item.get("case")))),
                    " ".join(filter(None, (item["policy"], identity))),
                    *conditions(item))].append(item)
    lines = ["| Scenario | Policy | Model | Effort | Harness | Mode | Age/interval s | Episodes | "
             "Won | Lost | Draw | Other | Mean battle s | Own left | Enemy left | Mean delay s | "
             "USD |", "|" + "---|" * 17]
    for key, items in sorted(groups.items()):
        outcomes = [item["outcome"] for item in items]
        battle = [float(item["battle_s"]) for item in items if item["battle_s"]]
        delays = [float(item["delay_s"]) for item in items if item["delay_s"]]
        own = [float(item["own_left"]) for item in items if item.get("own_left")]
        enemy = [float(item["enemy_left"]) for item in items if item.get("enemy_left")]
        usd = sum(float(item["usd"] or 0) for item in items)
        lines.append("| " + " | ".join([
            *key, str(len(items)), str(outcomes.count("won")), str(outcomes.count("lost")),
            str(outcomes.count("draw")),
            str(sum(o not in ("won", "lost", "draw") for o in outcomes)),
            f"{statistics.mean(battle):.0f}" if battle else "",
            f"{statistics.mean(own):.2f}" if own else "",
            f"{statistics.mean(enemy):.2f}" if enemy else "",
            f"{statistics.mean(delays):.1f}" if delays else "", f"{usd:.2f}",
        ]) + " |")
    return "\n".join(lines)
