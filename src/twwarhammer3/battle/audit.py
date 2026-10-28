"""The branch audit of checkpoint RL (checkpoint-rl-plan.md, stage 2): every candidate of a
rung executed once from its checkpoint, a declared repeat, and a no-injection reference;
``table.json`` holds each candidate's engine ending and reward. ``table`` rebuilds it from
the attempts alone, so a recount needs no game.
"""
import json
from pathlib import Path

from gameai.provenance import sha256, write_json
from twwarhammer3.battle import checkpoint
from twwarhammer3.battle.candidates import candidates, mapping_hash

# Statuses after which an audit stops: the restore path itself failed.
STOPS = ("restore_failure", "restore_fault", "infrastructure", "interrupted")


def step_plan(plan: dict) -> dict:
    return {"observe_ms": 300, "readings": {"every": 100, "lua": checkpoint.READING_LUA},
            "limits": plan["limits"]}


def audit(plan: dict, output: Path) -> dict:
    """Plan: name, rungs [{record, reference (an attempt directory, or none to run one),
    tick (default save tick + 2)}], repeat [candidate ids], limits. Stops at the first attempt
    whose restore failed; returns the table."""
    output.mkdir(parents=True)
    write_json(output / "plan.json", plan)
    count = 0

    def next_directory():
        nonlocal count
        count += 1
        return output / f"attempt-{count - 1:04d}"

    for rung in plan["rungs"]:
        record_path = Path(rung["record"])
        record = json.loads(record_path.read_text())
        reference = Path(rung["reference"]) if rung.get("reference") else None
        if reference is None:
            reference = next_directory()
            checkpoint.restore_episode(record_path, step_plan(plan), reference)
        if json.loads((reference / "attempt.json").read_text())["status"] not in checkpoint.SCORED:
            raise RuntimeError(f"the reference {reference} has no engine ending")
        probe = checkpoint.injection_for(reference, record, [], "probe", rung.get("tick"))
        listed = candidates(probe["context"])["candidates"]
        jobs = [(c, 0) for c in listed] + [(c, 1) for c in listed if c["id"] in plan["repeat"]]
        for candidate, repeat in jobs:
            request = f"{plan['name']}-{record['tick']}-{candidate['id']}-{repeat}"
            injection = checkpoint.injection_for(reference, record, candidate["orders"], request,
                                                 rung.get("tick"))
            directory = next_directory()
            attempt = checkpoint.restore_episode(
                record_path, {**step_plan(plan), "injection": injection,
                              "reference": str(reference), "candidate": candidate["id"],
                              "repeat": repeat}, directory)
            if attempt["status"] in STOPS:
                raise RuntimeError(f"{directory}: {attempt['status']} ({attempt.get('reason')})")
    result = table(output)
    write_json(output / "table.json", result)
    return result


def refused(attempt: dict) -> bool:
    attribution = attempt.get("attribution") or {}
    return attempt["status"] == "injection_failed" and attribution.get("clause") == "results" \
        and "refused" in (attribution.get("reason") or {})


def table(output: Path) -> dict:
    """The audit's reward table, from its plan and attempt records only."""
    plan = json.loads((output / "plan.json").read_text())
    attempts = sorted(output.glob("attempt-*/attempt.json"))
    rungs = []
    for rung in plan["rungs"]:
        record = json.loads(Path(rung["record"]).read_text())
        mine = [(path, json.loads(path.read_text())) for path in attempts]
        mine = [(p, a) for p, a in mine if a["plan"].get("record") == str(Path(rung["record"]))]
        references = [(p, a) for p, a in mine if "injection" not in a["plan"]]
        reference = Path(rung["reference"]) if rung.get("reference") else references[0][0].parent
        branches = [(p, a) for p, a in mine if "injection" in a["plan"]]
        hashes = {a["plan"]["injection"]["context_hash"] for _, a in branches}
        rows, comparisons = [], []
        for path, attempt in branches:
            injection = attempt["plan"]["injection"]
            rows.append({"candidate": attempt["plan"]["candidate"],
                         "repeat": attempt["plan"]["repeat"],
                         "batch_hash": checkpoint.digest(injection["orders"]),
                         "attempt": str(path.parent), "attempt_sha256": sha256(path),
                         "applied_ms": (attempt.get("attribution") or {}).get("applied_ms"),
                         "status": attempt["status"], "flags": (attempt.get("attribution")
                                                                or {}).get("flags"),
                         "engine_ending": attempt.get("engine_ending"),
                         "reward": attempt.get("reward"), "refused": refused(attempt)})
        listed = candidates(branches[0][1]["plan"]["injection"]["context"])["candidates"] \
            if branches else []
        firsts = {r["candidate"]: r for r in rows if r["repeat"] == 0}
        for r in rows:
            if r["repeat"]:
                pair = checkpoint.compare_attempts(Path(firsts[r["candidate"]]["attempt"]),
                                                   Path(r["attempt"]), 100 * record["tick"])
                comparisons.append({"candidate": r["candidate"], "match": (
                    pair["checksum_mismatches"] == 0 and not pair["observations_unequal"]
                    and not pair["observations_one_side"] and pair["endings_equal"]
                    and firsts[r["candidate"]]["applied_ms"] == r["applied_ms"]), **{
                    k: pair[k] for k in ("ticks", "checksum_mismatches", "first_mismatch",
                                         "observations_unequal", "endings_equal")}})
        scored = [c for c in listed if c["id"] in firsts and not firsts[c["id"]]["refused"]]
        rewards = [firsts[c["id"]]["reward"] for c in scored]
        statuses = {}
        for r in rows:
            statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        verdict = {
            "endings": all(r["engine_ending"] for r in rows),
            "applied_or_refused": all(r["status"] in checkpoint.SCORED or r["refused"]
                                      for r in rows),
            "repeats_match": all(c["match"] for c in comparisons),
            "one_context": len(hashes) == 1,
            "all_candidates": set(firsts) == {c["id"] for c in listed},
            "winner_and_loser": 1 in rewards and 0 in rewards}
        verdict["pass"] = all(verdict.values())
        rungs.append({
            "record": rung["record"], "root": record["root"], "tick": record["tick"],
            "reference": str(reference), "context_hash": sorted(hashes),
            "context": branches[0][1]["plan"]["injection"]["context"] if branches else None,
            "candidates": scored, "mapping": mapping_hash(scored),
            "rewards": rewards, "refused": [c["id"] for c in listed if c["id"] in firsts
                                            and firsts[c["id"]]["refused"]],
            "attempts": rows, "repeats": comparisons, "statuses": statuses,
            "launches": len(rows) + len(references), "verdict": verdict})
    return {"name": plan["name"], "rungs": rungs,
            "pass": all(r["verdict"]["pass"] for r in rungs)}
