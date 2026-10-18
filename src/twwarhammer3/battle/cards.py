"""Tactic cards: a declared battle, its controls, a frozen signature, its board and verdict.

A card ([tactic-cards.md](../../../docs/twwarhammer3/tactic-cards.md)) is a minimal battle
that only one tactic should win. Its foils (naive plays) must lose and its witness (a
disclosed scripted bot) must win. Both are declared here with the admission rule before
a confirmation round, so the board and the verdict come from the job evidence alone.
The launch is the sampling unit: a confirmation round plays each control once per launch.
"""

import json
import statistics
from collections import defaultdict
from pathlib import Path

from twwarhammer3.battle.report import wilson
from twwarhammer3.battle.stats import JOBS_ROOT

WITNESS = "twwarhammer3.battle.calibration:SnapHitAndRun"
CARDS = {
    "chariot": {
        "scenario": "grn-chariot-emp-swordsmen-hard",
        "tactic": "cycle charging: charge, pull out, charge again instead of grinding",
        # hold is no foil here: the AI defends, so standing still loses on the timer by the
        # mode's rule (1205 s, bench-b32-chariothard-floor-hold-20261018).
        "foils": ("attack_nearest", "rush_nearest"),
        # (controller, added age s, decision interval s) -> wins required in the round
        # Admission gate. The same witness at model pace (5 s age, one decision per 5 s,
        # as models made about 0.2 a second) is the card's reported reference, not a gate:
        # it won 1 of 2 in E2 (decided 2026-10-18 17:45 UTC, during its third launch).
        "witnesses": {(WITNESS, 5, 0): 4},
        "foil_launches": 10,  # a foil that wins 20% of battles passes 10 of 10 losses 11%
        "witness_launches": 5,
        "cycles": 1,  # each witness win shows at least this many cycles
    },
}
MERGE_S = 3  # melee-flag gaps shorter than this are one engagement (1 Hz frames flicker)


def outcome(episode: dict) -> str:
    """won, lost or excluded (rerun). Invalid replies are the controller's loss; provider,
    harness and budget stops are not."""
    status = episode.get("status")
    if status == "won" and episode.get("ended_by") != "time_limit":
        return "won"
    if status in ("won", "lost", "draw"):
        return "lost"
    if status == "policy_failure" and str(episode.get("error")).startswith("No valid reply"):
        return "lost"
    return "excluded"


def engagements(frames: list[dict], unit_id: str) -> list[list[float]]:
    """[start, end] battle seconds of each run of the unit's melee flag."""
    spans = []
    for frame in frames:
        unit = next((u for u in frame.get("friendly", []) if u.get("id") == unit_id), None)
        if unit is None or "melee" not in unit.get("state", []):
            continue
        now = frame.get("time_ms", 0) / 1000
        if spans and now - spans[-1][1] < MERGE_S:
            spans[-1][1] = now
        else:
            spans.append([now, now])
    return spans


def cycles(episode_dir: Path) -> int | None:
    """Engagements, other than the last, in which the controller's own move order took effect.

    A cycle is a deliberate pull-out followed by a new charge: an attack-only play scores 0
    even when the engine carries its unit out of melee and it charges again.
    """
    replay, trace = episode_dir / "replay.jsonl", episode_dir / "trace.jsonl"
    if not replay.exists() or not trace.exists():
        return None
    frames = [json.loads(line) for line in replay.open() if line.strip()]
    moves, applied = {}, []
    for line in trace.open():
        record = json.loads(line)
        if record.get("kind") == "decision":
            moves[record.get("request")] = record.get("orders") or []
        elif record.get("kind") == "ack":
            ack = record.get("ack") or {}
            orders = moves.pop(record.get("request"), [])
            for result in ack.get("results", []):
                index = result.get("index", 0) - 1
                if result.get("ok") and 0 <= index < len(orders) \
                        and orders[index].get("type") == "move":
                    applied.append((orders[index]["unit"], ack.get("applied_ms", 0) / 1000))
    units = {unit["id"] for unit in (frames[0].get("friendly", []) if frames else [])}
    return sum(1 for unit in units for start, end in engagements(frames, unit)[:-1]
               if any(who == unit and start <= when <= end + 1 for who, when in applied))


def jobs(paths: list[Path]) -> list[Path]:
    """Job directories, with a directory of queue plans expanded to the plans' outputs."""
    found = []
    for path in paths:
        plans = sorted(p for p in path.glob("*.json") if not p.name.endswith("-state.json"))
        if (path / "manifest.json").exists() or not plans:
            found.append(path)
            continue
        for plan in plans:
            found += [Path(job["output"]) for job in json.loads(plan.read_text()).get("jobs", [])]
    return found


def battles(card: dict, directories: list[Path]) -> list[dict]:
    rows = []
    for job in directories:
        try:
            manifest = json.loads((job / "manifest.json").read_text())
        except (OSError, ValueError):
            continue
        if (manifest.get("scenario") or {}).get("name") != card["scenario"]:
            continue
        setup = json.dumps([manifest["scenario"].get(key) for key in (
            "map", "player", "enemy", "expect", "attacker", "battle_type")], sort_keys=True)
        for episode in manifest.get("episodes", []):
            control = episode.get("card") or {}
            rows.append({
                "job": job.name, "outcome": outcome(episode),
                "controller": episode.get("policy") or control.get("name"),
                "age_s": round((episode.get("delay_ms") or 0) / 1000),
                "interval_s": round((manifest["config"].get("interval_ms") or 0) / 1000),
                "setup": (setup, manifest["deployment"].get("steam_build_id"),
                          manifest["deployment"]["pack"].get("sha256")),
                "source": control.get("source_sha256") or control.get("version"),
                "battle_s": episode.get("battle_s"),
                "order_age_s": statistics.median(episode["delays_ms"]) / 1000
                if episode.get("delays_ms") else None,
                "cycles": cycles(job / str(episode.get("episode"))),
            })
    return rows


def board(name: str, paths: list[Path] | None = None) -> str:
    """The card's table over the given jobs (default: every job of its scenario) and, for
    given jobs, the admission verdict under the declared rule."""
    card = CARDS[name]
    default = paths is None
    directories = sorted(JOBS_ROOT.iterdir()) if default else jobs(paths)
    rows = battles(card, [d for d in directories if d.is_dir()])
    cells = defaultdict(list)
    for row in rows:
        cells[(row["controller"], row["age_s"], row["interval_s"])].append(row)
    lines = [f"Card {name}: {card['scenario']} ({card['tactic']})",
             f"{len(rows)} battles; a cell mixing setups or controller sources is marked *",
             "controller                 age pace   n won excl  win [95%]        cycles  "
             "no-cycle wins  battle s  order age s"]
    for key in sorted(cells, key=lambda k: (k[0] not in card["foils"], str(k))):
        group = cells[key]
        scored = [row for row in group if row["outcome"] != "excluded"]
        won = sum(row["outcome"] == "won" for row in scored)
        ci = wilson(won, len(scored))
        mixed = "*" if len({row["setup"] for row in group}) > 1 or len(
            {row["source"] for row in group}) > 1 else ""
        label = key[0].removeprefix("twwarhammer3.battle.calibration:")[:25] + mixed

        def median(field, digits=0):
            values = [row[field] for row in scored if row[field] is not None]
            return f"{statistics.median(values):.{digits}f}" if values else "-"

        interval = f"[{ci[0]:.2f}, {ci[1]:.2f}]" if ci else "-"
        win = f"{won / len(scored):.2f} {interval}" if scored else "-"
        bare = sum(row["outcome"] == "won" and not row["cycles"] for row in scored)
        lines.append(f"{label:26} {key[1]:3} {key[2]:4} {len(scored):3} {won:3} "
                     f"{len(group) - len(scored):4}  {win:18} {median('cycles'):>5}  {bare:13}"
                     f"  {median('battle_s'):>8}  {median('order_age_s', 1):>11}")
    lines.append("cycles (median): deliberate pull-outs followed by a new charge; a win without"
                 " one did not use the tactic")
    if not default:
        lines += verdict(card, cells)
    return "\n".join(lines)


def verdict(card: dict, cells: dict) -> list[str]:
    need, problems = card["foil_launches"], []
    for foil in card["foils"]:
        scored = [r for r in cells.get((foil, 0, 0), []) if r["outcome"] != "excluded"]
        wins = sum(r["outcome"] == "won" for r in scored)
        if wins:
            problems.append(f"{foil} won {wins} of {len(scored)}")
        elif len(scored) < need:
            problems.append(f"{foil} has {len(scored)} of {need} launches")
    need = card["witness_launches"]
    for key, required in card["witnesses"].items():
        scored = [r for r in cells.get(key, []) if r["outcome"] != "excluded"]
        wins = [r for r in scored if r["outcome"] == "won"]
        label = f"witness at {key[1]} s age, {key[2]} s interval"
        if len(scored) < need:
            problems.append(f"{label} has {len(scored)} of {need} launches")
        elif len(wins) < required:
            problems.append(f"{label} won {len(wins)} of {len(scored)}, needs {required}")
        if any((r["cycles"] or 0) < card["cycles"] for r in wins):
            problems.append(f"{label}: a win shows fewer than {card['cycles']} cycles")
    for key in [(foil, 0, 0) for foil in card["foils"]] + list(card["witnesses"]):
        group = cells.get(key, [])
        if len({r["setup"] for r in group}) > 1 or len({r["source"] for r in group}) > 1:
            problems.append(f"{key[0]} at {key[1]} s/{key[2]} s mixes setups or sources")
    wins = ", ".join(f"{n} of {need} at {k[1]} s age/{k[2]} s interval"
                     for k, n in card["witnesses"].items())
    rule = (f"Rule: every foil loses at 0 s in each of {card['foil_launches']} launches; "
            f"the witness wins {wins}, each win with at least {card['cycles']} cycle.")
    return ["", rule, "Verdict: " + ("admitted" if not problems else "not admitted: "
                                     + "; ".join(problems))]
