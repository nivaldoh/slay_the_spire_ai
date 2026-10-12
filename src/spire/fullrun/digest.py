"""Readable digests of saved full-run evidence, for reviewing a model's mistakes.

    python -m spire digest runs/fullrun/<job>                      per-seed table
    python -m spire digest runs/fullrun/<job>/run-0000             floors and choices
    python -m spire digest runs/fullrun/<job>/run-0000 --floor N   one floor, turn by turn

A job prints the per-seed table used in docs/fullrun/log.md. A run prints one line per
floor (HP change, room) followed by its noncombat choices and the model's reasons. It
only reads evidence.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOMS = {"MonsterRoomElite": "elite", "MonsterRoomBoss": "boss", "EventRoom": "event fight"}


def _decisions(run: Path):
    for line in (run / "trace.jsonl").open():
        record = json.loads(line)
        if record["kind"] == "decision":
            decision = record["decision"]
            chosen = next(c for c in decision["candidates"] if c["id"] == record["choice_id"])
            yield decision["observation"], chosen["label"], record["behavior"]


def _alive(combat: dict) -> list[dict]:
    return [m for m in combat["monsters"] if not m.get("is_gone") and m.get("current_hp", 0) > 0]


def _intent(monster: dict) -> str:
    damage, hits = monster.get("move_adjusted_damage"), monster.get("move_hits", 1)
    if not damage:
        return monster["intent"]
    return f"{monster['intent']} {damage}" + (f"x{hits}" if hits > 1 else "")


def _creatures(combat: dict) -> str:
    player = combat["player"]
    powers = "".join(f" {p['name']}{p['amount']}" for p in player["powers"])
    enemies = "; ".join(
        f"{m['name']} {m['current_hp']} blk{m.get('block', 0)} {_intent(m)}"
        for m in _alive(combat)
    )
    return f"hp{player['current_hp']} blk{player.get('block', 0)} e{player.get('energy')}" + (
        f"{powers} | {enemies}"
    )


def last_fight(run: Path) -> str:
    """The enemies still standing at the run's last combat decision, and the room kind."""
    observation = None
    for candidate, _, _ in _decisions(run):
        if candidate.get("combat_state"):
            observation = candidate
    if observation is None:
        return ""
    counts = Counter(m["name"] for m in _alive(observation["combat_state"]))
    names = ", ".join(f"{n}x {name}" if n > 1 else name for name, n in counts.items())
    room = ROOMS.get(observation.get("room_type"))
    return names + (f" ({room})" if room else "")


def job_table(job: Path) -> str:
    rows = [
        "| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for run in sorted(job.glob("run-*")):
        result = json.loads((run / "result.json").read_text())
        llm = result.get("llm", {})
        killed = last_fight(run) if result["status"] == "lost" else result.get("error") or ""
        rows.append(
            f"| {result['seed']} | {result['status']} | {result.get('act')} / "
            f"{result.get('floor')} | {killed} | {result['decisions']} | {llm.get('calls', 0)} | "
            f"${llm.get('usd', 0):.3f} | {result.get('elapsed_seconds', 0):,.0f} s |"
        )
    manifest = json.loads((job / "manifest.json").read_text())
    return "\n".join([
        f"{job.name}: source {manifest['source_revision'][:7]}, {manifest['status']}", *rows,
    ])


def floor_detail(run: Path, floor: int) -> None:
    for observation, label, behavior in _decisions(run):
        if observation.get("floor") == floor:
            combat = observation.get("combat_state")
            where = f"T{combat['turn']} {_creatures(combat)}" if combat else None
            reason = f"  ({behavior['reason']})" if behavior.get("reason") else ""
            print(f"{where or observation.get('screen_type')} -> {label}{reason}")


def digest(run: Path) -> None:
    result = json.loads((run / "result.json").read_text())
    llm = result.get("llm", {})
    print(
        f"{run.name} seed {result['seed']}: {result['status']} at act {result.get('act')} "
        f"floor {result.get('floor')} (score {result.get('score')}), {result['decisions']} "
        f"decisions, {llm.get('calls', 0)} calls, ${llm.get('usd', 0):.4f}, "
        f"{result.get('elapsed_seconds', 0):.0f} s"
    )
    floors: dict[int, dict] = {}
    notes = ""
    for observation, label, behavior in _decisions(run):
        entry = floors.setdefault(observation.get("floor"), {"hp": [], "room": "", "picks": []})
        entry["hp"].append(observation.get("current_hp"))
        combat = observation.get("combat_state")
        if combat:
            names = ", ".join(sorted({m["name"] for m in combat["monsters"]}))
            entry["room"] = f"{observation.get('room_type')} {names}, {combat['turn']} turns"
        elif behavior.get("type") == "llm":
            screen = observation.get("screen_type")
            entry["picks"].append(f"{screen}: {label} ({behavior.get('reason')})")
        notes = behavior.get("notes", notes)
    for floor, entry in floors.items():
        print(f"F{floor} HP {entry['hp'][0]}->{entry['hp'][-1]} {entry['room']}")
        for pick in entry["picks"]:
            print(f"    {pick}")
    print(f"Final notes: {notes}")


def main(path: Path, floor: int | None = None) -> None:
    if (path / "manifest.json").exists():
        print(job_table(path))
    elif floor is None:
        digest(path)
    else:
        floor_detail(path, floor)
