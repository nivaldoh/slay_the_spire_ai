"""Readable digest of a saved full-run trace, for reviewing a model's mistakes.

Usage:
    python scripts/play_digest.py runs/<job>/run-0000 [--floor N]

Without --floor it prints one line per floor (HP change, room) followed by the
noncombat choices and the model's reasons. --floor N prints that floor's decisions
turn by turn. It only reads evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _decisions(run: Path):
    for line in (run / "trace.jsonl").open():
        record = json.loads(line)
        if record["kind"] == "decision":
            decision = record["decision"]
            chosen = next(c for c in decision["candidates"] if c["id"] == record["choice_id"])
            yield decision["observation"], chosen["label"], record["behavior"]


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
        for m in combat["monsters"]
        if not m.get("is_gone") and m.get("current_hp", 0) > 0
    )
    return f"hp{player['current_hp']} blk{player.get('block', 0)} e{player.get('energy')}" + (
        f"{powers} | {enemies}"
    )


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", type=Path)
    parser.add_argument("--floor", type=int)
    args = parser.parse_args()
    if args.floor is None:
        digest(args.run)
    else:
        floor_detail(args.run, args.floor)


if __name__ == "__main__":
    main()
