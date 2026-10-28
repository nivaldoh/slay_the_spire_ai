"""Readable digests of saved full-run evidence, for reviewing a model's mistakes.

    python -m spire digest runs/fullrun/<job>                      per-seed table
    python -m spire digest runs/fullrun/<job>/run-0000             floors and mistake flags
    python -m spire digest runs/fullrun/<job>/run-0000 --picks     also every choice and reason
    python -m spire digest runs/fullrun/<job>/run-0000 --floor N   one floor, turn by turn

A job prints the per-seed table used in docs/spire/fullrun/log.md. A run prints one line per
floor (HP change, room), flags that count recurring mistakes and point at their floors, and
the model's final notes; --picks adds its noncombat choices and reasons. It only reads
evidence.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from spire.fullrun.llm import incoming_damage

ROOMS = {"MonsterRoomElite": "elite", "MonsterRoomBoss": "boss", "EventRoom": "event fight"}


def _decisions(run: Path):
    for line in (run / "trace.jsonl").open():
        record = json.loads(line)
        if record["kind"] == "decision":
            decision = record["decision"]
            chosen = next(c for c in decision["candidates"] if c["id"] == record["choice_id"])
            yield decision["observation"], chosen, record["behavior"]


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


def _per_floor(counts: Counter) -> str:
    return ", ".join(f"F{floor}" + (f" x{n}" if n > 1 else "") for floor, n in counts.items())


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


def table_row(run: Path) -> str:
    result = json.loads((run / "result.json").read_text())
    llm = result.get("llm", {})
    killed = last_fight(run) if result["status"] == "lost" else result.get("error") or ""
    return (
        f"| {result['seed']} | {result['status']} | {result.get('act')} / "
        f"{result.get('floor')} | {killed} | {result['decisions']} | {llm.get('calls', 0)} | "
        f"${llm.get('usd', 0):.3f} | {result.get('elapsed_seconds', 0):,.0f} s |"
    )


def job_table(job: Path) -> str:
    manifest = json.loads((job / "manifest.json").read_text())
    return "\n".join([
        f"{job.name}: source {manifest['source_revision'][:7]}, {manifest['status']}",
        "| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |",
        "|---|---|---|---|---:|---:|---:|---:|",
        *(table_row(run) for run in sorted(job.glob("run-*"))),
    ])


# JUDGEMENT?: Mistake flags — assistant, 2026-10-12 (flagged by Claude, 2026-10-28): the counts
# below (idle energy with a playable card, exposed turns, skipped rewards, potions, the last turn)
# point the review loop to floors. Other flags would point its next change elsewhere.
def flags(run: Path) -> list[str]:
    """Counts of mistakes that recur across runs, with the floors to look at."""
    idle: Counter = Counter()
    exposed: Counter = Counter()
    skips: Counter = Counter()
    potions: list[str] = []
    last_end = "none"
    observation: dict = {}
    for observation, chosen, behavior in _decisions(run):
        floor, command = observation.get("floor"), chosen["command"]
        combat = observation.get("combat_state")
        if observation.get("screen_type") == "CARD_REWARD" and command == "skip":
            skips[floor] += 1
        elif command.startswith("potion use"):
            room = ROOMS.get(observation.get("room_type"), "hallway") if combat else "no combat"
            name = observation["potions"][int(command.split()[2])]["name"]
            potions.append(f"F{floor} {room} {name}")
        elif command == "end" and combat:
            player = combat["player"]
            incoming, block = incoming_damage(combat["monsters"]), player.get("block", 0)
            last_end = (f"F{floor} T{combat['turn']}, incoming {incoming} against {block} block "
                        f"and {player['current_hp']} HP")
            playable = any(card.get("is_playable") for card in combat.get("hand", []))
            if behavior.get("type") == "llm" and player.get("energy") and playable:
                idle[floor] += 1
                if incoming > block:
                    exposed[floor] += 1
    repeated = Counter({floor: n for floor, n in skips.items() if n > 1})
    held = [p["name"] for p in observation.get("potions", []) if p.get("id") != "Potion Slot"]
    return [
        f"Turns ended with energy and a playable card: {sum(idle.values())}"
        + (f" ({_per_floor(idle)})" if idle else "")
        + f"; with attacks exceeding block: {sum(exposed.values())}"
        + (f" ({_per_floor(exposed)})" if exposed else ""),
        f"Card rewards skipped: {sum(skips.values())}"
        + (f", repeatedly on {_per_floor(repeated)}" if repeated else ""),
        f"Potions used: {'; '.join(potions) or 'none'}. Held at the end: "
        f"{', '.join(held) or 'none'}",
        f"Last end turn: {last_end}",
    ]


def floor_detail(run: Path, floor: int) -> None:
    turn = None
    for observation, chosen, behavior in _decisions(run):
        if observation.get("floor") != floor:
            continue
        combat = observation.get("combat_state")
        reason = f"  ({behavior['reason']})" if behavior.get("reason") else ""
        if not combat:
            turn = None
            print(f"{observation.get('screen_type')} -> {chosen['label']}{reason}")
            continue
        if combat["turn"] != turn:
            turn = combat["turn"]
            print(f"T{turn} {_creatures(combat)}")
        if chosen["command"] == "end":
            player = combat["player"]
            incoming = incoming_damage(combat["monsters"])
            print(f"    -> end turn at hp{player['current_hp']} blk{player.get('block', 0)} "
                  f"e{player.get('energy')}, incoming {incoming}{reason}")
        else:
            print(f"    -> {chosen['label']}{reason}")


def digest(run: Path, picks: bool = False) -> None:
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
    for observation, chosen, behavior in _decisions(run):
        entry = floors.setdefault(observation.get("floor"), {"hp": [], "room": "", "picks": []})
        entry["hp"].append(observation.get("current_hp"))
        combat = observation.get("combat_state")
        if combat:
            names = ", ".join(sorted({m["name"] for m in combat["monsters"]}))
            entry["room"] = f"{observation.get('room_type')} {names}, {combat['turn']} turns"
        elif behavior.get("type") == "llm":
            screen = observation.get("screen_type")
            entry["picks"].append(f"{screen}: {chosen['label']} ({behavior.get('reason')})")
        notes = behavior.get("notes", notes)
    for floor, entry in floors.items():
        print(f"F{floor} HP {entry['hp'][0]}->{entry['hp'][-1]} {entry['room']}")
        for pick in entry["picks"] if picks else ():
            print(f"    {pick}")
    for line in flags(run):
        print(line)
    print(f"Final notes: {notes}")


def main(path: Path, floor: int | None = None, picks: bool = False) -> None:
    if (path / "manifest.json").exists():
        print(job_table(path))
    elif floor is None:
        digest(path, picks)
    else:
        floor_detail(path, floor)
