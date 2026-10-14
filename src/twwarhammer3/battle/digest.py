"""Readable digests of saved battle evidence, for reviewing a policy's mistakes.

    python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>                 episode table
    python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>/episode-0000    decision lines

An episode prints one line per decision that sent orders or carries a model's reason:
battle time, both sides' strength in the state the policy saw (units still fighting / men;
enemies as seen of the roster), the measured delay, the orders, the engine's rejections,
a commander's adopted plan with its age and the model's reason; then the final state and
the model's last notes. It only reads evidence.
"""

import json
from pathlib import Path

from twwarhammer3.battle.commander import describe_plan
from twwarhammer3.battle.llm import describe_orders, short_type
from twwarhammer3.battle.stats import MODEL_POLICIES, row


def _strength(observation: dict) -> str:
    friendly = [u for u in observation.get("friendly", []) if u.get("men")]
    fighting = [u for u in friendly if not {"routing", "shattered"} & set(u.get("state", []))]
    enemy = observation.get("enemy", [])
    roster = len(observation.get("enemy_roster", []))
    return (f"us {len(fighting)}/{len(friendly)}u {sum(u['men'] for u in friendly)}m"
            f"  seen {len(enemy)}/{roster}u {sum(u.get('men', 0) for u in enemy)}m")


def _objectives(observation: dict) -> str:
    """Tickets and the holders of capture points, for battle types that have them."""
    mode = observation.get("mode") or {}
    parts = []
    if mode.get("tickets"):
        parts.append("tickets " + " ".join(f"{row['side']} {row['tickets']}"
                                           for row in mode["tickets"])
                     + (f" of {mode['tickets_goal']}" if mode.get("tickets_goal") else ""))
    if mode.get("capture_points"):
        holders = [point.get("holder") or "-" for point in mode["capture_points"]]
        parts.append("points " + ",".join(holders))
    if mode.get("supplies") is not None:
        parts.append(f"supplies {mode['supplies']}")
    return ("  " + "; ".join(parts)) if parts else ""


def _units(observation: dict) -> list[str]:
    lines = []
    for side in ("friendly", "enemy"):
        for unit in observation.get(side, []):
            lines.append(f"  {unit['id']} {short_type(unit.get('type'))}: {unit.get('men')}/"
                         f"{unit.get('men0')} men at ({unit.get('x') or 0:.0f},"
                         f" {unit.get('z') or 0:.0f}) " + " ".join(unit.get("state") or []))
    return lines


def episode_digest(episode: Path) -> str:
    path = episode / "result.json"
    result = json.loads(path.read_text()) if path.exists() else {"status": "running"}
    delays = result.get("delays_ms") or []
    llm = result.get("llm") or {}
    error = f"; error: {result['error']}" if result.get("error") else ""
    measures = result.get("objectives") or {}
    if measures:
        held = measures.get("victory_held")
        key = measures.get("key_held")
        error = (f"; victory points held {held:.0%}" if held is not None else "") + (
            f", key building {key:.0%}" if key is not None else "") + "".join(
            f", {label} {measures[key]}" for key, label in (
                ("supplies_left", "supplies left"), ("build", "built"),
                ("reinforce", "reinforced"), ("tickets", "tickets")) if key in measures) + error
    lines = [
        f"{episode.name}: {result['status']} at {result.get('battle_s', '?')} s battle time;"
        f" {result.get('decisions', 0)} decisions, {result.get('invalid', 0)} invalid;"
        f" delay mean {result.get('delay_s')} s max {max(delays, default=0) / 1000:.1f} s;"
        f" ${llm.get('usd', 0):.4f}{error}",
    ]
    observation, last, notes = None, None, None
    pending = {}
    for raw in (episode / "trace.jsonl").open():
        record = json.loads(raw)
        kind = record["kind"]
        if kind in ("observation", "battle", "roster", "result"):
            last = record["observation"]
            if kind == "observation":
                observation = last
        elif kind == "decision":
            behavior = record.get("behavior") or {}
            notes = behavior.get("notes", notes)
            if not record["orders"] and not behavior.get("reason"):
                continue
            pending[record["request"]] = len(lines)
            reason = f" | {behavior['reason']}" if behavior.get("reason") else ""
            plan = (f"  plan ({behavior['plan_age_s']:.1f} s old): "
                    f"{describe_plan(behavior['plan'])}" if "plan" in behavior else "")
            lines.append(f"{record['time_ms'] / 1000:6.0f}s  {_strength(observation)}"
                         f"{_objectives(observation)}"
                         f"  {describe_orders(record['orders'])}{plan}{reason}")
        elif kind == "ack" and record["request"] in pending:
            index = pending.pop(record["request"])
            rejected = [f"{r['unit']} {r.get('error')}" for r in record["ack"].get("results", [])
                        if not r.get("ok")]
            delay = record["latency"]["delay_ms"] / 1000
            lines[index] += f"  [delay {delay:.1f}s" + (
                f"; rejected {', '.join(rejected)}]" if rejected else "]")
        elif kind == "invalid":
            lines.append(f"        invalid: {record['error']}")
    if last:
        lines.append(f"final at {last.get('time_ms', 0) / 1000:.0f} s: {_strength(last)}"
                     f"{_objectives(last)}")
        lines += _units(last)
    if notes:
        lines.append("notes: " + notes.replace("\n", " / "))
    return "\n".join(lines)


DIGEST_COLUMNS = ("episode", "outcome", "battle_s", "own_left", "enemy_left", "decisions",
                  "invalid", "delay_s", "usd")


def _draw(manifest: dict) -> str:
    """A random job's draw: seed, map and both races."""
    scenario = manifest.get("scenario") or {}
    if "seed" not in manifest["config"] or not scenario.get("map"):
        return ""
    return (f" (seed {manifest['config']['seed']}: {scenario['player']['subculture']} vs"
            f" {scenario['enemy']['subculture']} on {scenario['map']})")


def job_digest(job: Path) -> str:
    manifest = json.loads((job / "manifest.json").read_text())
    config = manifest["config"]
    lines = [f"{job.name}: {manifest['status']}, policy {config['policy']}"
             + (f" {config['model']}/{config['effort']}"
                if config["policy"] in MODEL_POLICIES else "")
             + f", scenario {config['scenario']}" + _draw(manifest)
             + f", source {manifest['source_revision'][:7]}",
             "| " + " | ".join(DIGEST_COLUMNS) + " |", "|" + "---|" * len(DIGEST_COLUMNS)]
    for result in sorted(job.glob("episode-*/result.json")):
        item = row(job, result.parent)
        lines.append("| " + " | ".join(str(item[column]) for column in DIGEST_COLUMNS) + " |")
    return "\n".join(lines)


def digest(path: Path) -> str:
    return episode_digest(path) if (path / "trace.jsonl").exists() else job_digest(path)
