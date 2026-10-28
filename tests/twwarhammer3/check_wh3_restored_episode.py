"""Check checkpoint-RL step runs (proposed, not agreed): a restored battle runs to its engine
ending, an order handed to the mod at an exact tick applies when the grid rule says and is
attributed, and identical attempts are identical (docs/twwarhammer3/checkpoint-rl-plan.md,
stage 1). Seven launches here, about 35 minutes, no paid model calls; the plan's step 4 (the
agreed Land check, four launches) runs separately with check_wh3_checkpoint.py.

uv run --locked python tests/twwarhammer3/check_wh3_restored_episode.py \\
    --output runs/twwarhammer3/rl/stage1-NAME

1. One hold source battle of emp-handgunners-grn-savage-orcs through the `rl checkpoint`
   code to its engine ending: saves every 300 ticks from 600, readings every 100 ticks,
   observe_ms 300, observations logged. The late rung is the latest save at least 60 s
   before the ending.
2. Three no-injection restores of the late rung to the ending; the first is its reference.
3. Two identical attempts injecting the attack_nearest batch at T = S + 2, and one moving
   the handgunners 60 m directly away from their nearest visible enemy.

Pass rules are in assess(). Recount saved evidence without launching: --recount OUTPUT;
continue an interrupted output, reusing its finished runs: --resume.

JUDGEMENT: stage1_check — Claude, 2026-10-25: these eleven launches and pass rules, versus
the handoff's live checks; competes with checkpoint-rl.md `verification_plan`. What stages 2
to 4 may build on rests on this.
"""
import argparse
import json
import math
import sys
from pathlib import Path

from gameai.provenance import sha256, write_json
from twwarhammer3.battle import checkpoint
from twwarhammer3.battle.scripted import AttackNearest, distance
from twwarhammer3.engine import runtime
from twwarhammer3.protocol import visible_enemies

SCENARIO = "emp-handgunners-grn-savage-orcs"
GUNS = "f2"
SOURCE_LIMITS = {"game_timeout_s": 1500, "agent_seconds": 1450, "episode_timeout_s": 1400}
RESTORES, ATTEMPTS = ("restore-a", "restore-b", "restore-c"), ("attack-a", "attack-b", "move")


def declaration(root: str) -> dict:
    return {"root": root, "scenario": SCENARIO, "saves": {"first": 600, "every": 300,
                                                         "last": 12000},
            "readings_every": 100, "late_margin_s": 60, "limits": SOURCE_LIMITS}


def restore_plan(record: dict) -> dict:
    return {"observe_ms": 300, "readings": {"every": 100, "lua": checkpoint.READING_LUA},
            "limits": checkpoint.limits_covering(record)}


def move_away(context: dict, unit_id: str, metres: float = 60) -> list[dict]:
    """One move of the unit ``metres`` directly away from its nearest visible enemy, the
    point clamped inside the public terrain bounds."""
    unit = next(u for u in context["friendly"] if u["id"] == unit_id)
    enemy = min(visible_enemies(context).values(), key=lambda e: distance(unit, e))
    length = distance(unit, enemy)
    x = unit["x"] + metres * (unit["x"] - enemy["x"]) / length
    z = unit["z"] + metres * (unit["z"] - enemy["z"]) / length
    bounds = context["terrain"]["bounds"]
    return [{"unit": unit_id, "type": "move", "x": round(min(max(x, bounds["min_x"]),
                                                              bounds["max_x"]), 1),
             "z": round(min(max(z, bounds["min_z"]), bounds["max_z"]), 1), "run": False}]


def replay_hashes() -> dict:
    return {path.name: sha256(path) for path in sorted((runtime.user_dir() / "replays").glob("*"))
            if path.is_file()}


def finished(directory: Path) -> bool:
    """A run of an earlier, interrupted invocation that wrote its attempt; a directory
    without one stops the check (launched() refuses it) for a look by hand."""
    return (directory / "attempt.json").exists()


def run(output: Path, resume: bool) -> None:
    output.mkdir(parents=True, exist_ok=resume)
    library = output / "checkpoints"
    root = output.name
    if not finished(library / root / "source"):
        write_json(output / "replays-before.json", replay_hashes())
        checkpoint.checkpoint_root(declaration(root), library)
        write_json(output / "replays-after.json", replay_hashes())
    late = checkpoint.late_rung(library / root)
    write_json(output / "late-rung.json", {"record": str(late)})
    record = json.loads(late.read_text())
    for name in RESTORES:
        if not finished(output / name):
            checkpoint.restore_episode(late, restore_plan(record), output / name)
    reference = output / RESTORES[0]
    context = checkpoint.context_of(reference, checkpoint.injection_for(
        reference, record, [], "probe")["context_ms"])
    batches = {"attack-a": AttackNearest().decide(context),
               "attack-b": AttackNearest().decide(context), "move": move_away(context, GUNS)}
    write_json(output / "batches.json", batches)
    for name in ATTEMPTS:
        if finished(output / name):
            continue
        injection = checkpoint.injection_for(reference, record, batches[name], f"{root}-{name}")
        checkpoint.restore_episode(late, {**restore_plan(record), "injection": injection,
                                          "reference": str(reference)}, output / name)


def load(run_dir: Path) -> dict:
    return json.loads((run_dir / "attempt.json").read_text())


def stream_evidence(run_dir: Path) -> dict:
    """Seq gaps after the handover and off-grid observations, from the raw logs."""
    rows, logged = checkpoint.read_rows(run_dir), checkpoint.read_observations(run_dir)
    restored = next((i for i, r in enumerate(rows) if r.get("event") == "restored"), -1)
    grid = checkpoint.grid_ms(checkpoint.CONFIG["tick_ms"])
    start = checkpoint.mod_start_ms((run_dir / "mod.log").read_text())
    return {"gaps_after_handover": checkpoint.seq_gaps(
                [r for r in logged if r["native_rows"] > restored], grid),
            "off_grid": checkpoint.off_grid([r["observation"] for r in logged], start, grid)}


def assess(output: Path) -> dict:
    root = output.name
    late = Path(json.loads((output / "late-rung.json").read_text())["record"])
    record = json.loads(late.read_text())
    source_dir = output / "checkpoints" / root / "source"
    source = load(source_dir)
    rows = checkpoint.read_rows(source_dir)
    ending = source.get("engine_ending") or {}
    end_ms = ending.get("battle_ms", 0)
    planned = [item["tick"] for item in source["plan"]["save_at"]]
    records = sorted(int(path.parent.name)
                     for path in (output / "checkpoints" / root).glob("*/record.json"))
    replays = [json.loads((output / f"replays-{w}.json").read_text()) for w in ("before", "after")]
    checks = {"late_rung": record["tick"], "source": {
        "status": source["status"],
        "engine_ending": source["status"] in checkpoint.SCORED,
        "mod_log_agrees": f"result {source['status']}" in (source_dir / "mod.log").read_text(),
        "saves_before_ending": [t for t in planned if 100 * t < end_ms] == [
            t for t in records if 100 * t < end_ms],
        "saves_not_reached": source["runner_end"].get("not_saved"),
        "on_grid": stream_evidence(source_dir)["off_grid"] == [],
        "replays_unchanged": all(replays[1].get(k) == v for k, v in replays[0].items()),
        "ticks_after_result": sum(1 for r in rows[source["end_row"]:] if r.get("event") == "tick"),
        "late_fault": source.get("late_fault")}}
    checks["source"]["pass"] = all(checks["source"][k] for k in (
        "engine_ending", "mod_log_agrees", "saves_before_ending", "on_grid", "replays_unchanged"))
    handover, context_ms = 100 * record["tick"], 100 * record["tick"] + 100
    for name in RESTORES + ATTEMPTS:
        attempt = load(output / name)
        evidence = {**attempt["restore_evidence"], **stream_evidence(output / name)}
        logged = checkpoint.read_observations(output / name)
        checks[name] = {
            "status": attempt["status"], "reason": attempt.get("reason"),
            "late_fault": attempt.get("late_fault"),
            "replay_unchanged": attempt.get("replay_unchanged"),
            "gaps_after_handover": evidence.get("gaps_after_handover"),
            "context_logged": any(r["observation"]["time_ms"] == context_ms for r in logged),
            "on_grid": evidence.get("off_grid") == [],
            "rebuild_observations": evidence.get("rebuild_observations"),
            "clock_ratio": evidence.get("clock_ratio"),
            "launch_s": round(attempt["ended_wall"] - attempt["started_wall"], 1),
            "walls": evidence.get("walls"), "attribution": attempt.get("attribution")}
        checks[name]["pass"] = (attempt["status"] in checkpoint.SCORED
                                and not attempt.get("late_fault")
                                and attempt.get("replay_unchanged") is True
                                and evidence.get("gaps_after_handover") == []
                                and checks[name]["context_logged"] and checks[name]["on_grid"])
    pairs = {f"{a}~{b}": checkpoint.compare_attempts(output / a, output / b, handover)
             for a, b in (("restore-a", "restore-b"), ("restore-a", "restore-c"),
                          ("attack-a", "attack-b"))}
    for name, result in pairs.items():
        result["pass"] = (result["checksum_mismatches"] == 0 and result["ticks"] > 0
                          and not result["observations_unequal"]
                          and not result["observations_one_side"]
                          and not result["readings_unequal"] and result["endings_equal"])
    checks["pairs"] = pairs
    checks["restores_vs_source"] = checkpoint.compare_attempts(source_dir, output / "restore-a",
                                                               handover)
    applied = [(load(output / n).get("attribution") or {}).get("applied_ms") for n in ATTEMPTS]
    move = load(output / "move").get("attribution") or {}
    checks["injections"] = {
        "attributed": all((load(output / n).get("attribution") or {}).get("status", "x") is None
                          for n in ATTEMPTS),
        "applied_ms": applied, "expected_applied_ms": handover + 400,
        "applied_equal": len(set(applied)) == 1 and applied[0] == handover + 400,
        "move_witness": move.get("witness"),
        "move_diverges_after_apply": (move.get("first_divergence") or 0) * 100
        >= (move.get("applied_ms") or math.inf)}
    checks["injections"]["pass"] = (checks["injections"]["attributed"]
                                    and checks["injections"]["applied_equal"]
                                    and move.get("witness") == {GUNS: "shown"}
                                    and checks["injections"]["move_diverges_after_apply"])
    checks["pass"] = (checks["source"]["pass"] and checks["injections"]["pass"]
                      and all(checks[n]["pass"] for n in RESTORES + ATTEMPTS)
                      and all(p["pass"] for p in pairs.values()))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recount", type=Path, help="assess an existing output without launching")
    parser.add_argument("--resume", action="store_true", help="reuse the output's finished runs")
    args = parser.parse_args()
    output = (args.recount or args.output).resolve()
    if not args.recount:
        run(output, args.resume)
    checks = assess(output)
    if not args.recount:
        write_json(output / "checks.json", checks)
    print(json.dumps(checks, indent=1, default=str))
    return 0 if checks["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
