"""Readable digests of saved battle evidence, for reviewing a policy's mistakes.

    python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>                 episode table
    python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>/episode-0000    decision lines

An episode prints one line per decision: battle time, both sides' strength in the state
the policy saw (units still fighting / men; enemies as seen of the roster), the measured
delay, the orders, the engine's rejections and the model's reason; then the final state
and the model's last notes. It only reads evidence.
"""

import json
from pathlib import Path

from twwarhammer3.battle.llm import describe_orders, short_type


def _strength(observation: dict) -> str:
    friendly = [u for u in observation.get("friendly", []) if u.get("men")]
    fighting = [u for u in friendly if not {"routing", "shattered"} & set(u.get("state", []))]
    enemy = observation.get("enemy", [])
    roster = len(observation.get("enemy_roster", []))
    return (f"us {len(fighting)}/{len(friendly)}u {sum(u['men'] for u in friendly)}m"
            f"  seen {len(enemy)}/{roster}u {sum(u.get('men', 0) for u in enemy)}m")


def _units(observation: dict) -> list[str]:
    lines = []
    for side in ("friendly", "enemy"):
        for unit in observation.get(side, []):
            lines.append(f"  {unit['id']} {short_type(unit.get('type'))}: {unit.get('men')}/"
                         f"{unit.get('men0')} men at ({unit.get('x') or 0:.0f},"
                         f" {unit.get('z') or 0:.0f}) " + " ".join(unit.get("state") or []))
    return lines


def episode_digest(episode: Path) -> str:
    result = json.loads((episode / "result.json").read_text())
    delays = result.get("delays_ms") or []
    llm = result.get("llm") or {}
    error = f"; error: {result['error']}" if result.get("error") else ""
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
            pending[record["request"]] = len(lines)
            reason = f" | {behavior['reason']}" if behavior.get("reason") else ""
            lines.append(f"{record['time_ms'] / 1000:6.0f}s  {_strength(observation)}"
                         f"  {describe_orders(record['orders'])}{reason}")
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
        lines.append(f"final at {last.get('time_ms', 0) / 1000:.0f} s: {_strength(last)}")
        lines += _units(last)
    if notes:
        lines.append("notes: " + notes.replace("\n", " / "))
    return "\n".join(lines)


def job_digest(job: Path) -> str:
    manifest = json.loads((job / "manifest.json").read_text())
    config = manifest["config"]
    lines = [f"{job.name}: {manifest['status']}, policy {config['policy']}"
             + (f" {config['model']}/{config['effort']}" if config["policy"] == "llm" else "")
             + f", scenario {config['scenario']}, source {manifest['source_revision'][:7]}",
             "| episode | outcome | battle s | decisions | invalid | delay s | usd |",
             "|---|---|---|---|---|---|---|"]
    for episode in manifest["episodes"]:
        lines.append(f"| {episode['episode']} | {episode['status']} | {episode.get('battle_s', '')}"
                     f" | {episode.get('decisions', 0)} | {episode.get('invalid', 0)}"
                     f" | {episode.get('delay_s') or ''}"
                     f" | {(episode.get('llm') or {}).get('usd', 0):.4f} |")
    return "\n".join(lines)


def digest(path: Path) -> str:
    return episode_digest(path) if (path / "result.json").exists() else job_digest(path)
