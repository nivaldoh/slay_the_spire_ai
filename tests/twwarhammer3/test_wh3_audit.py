"""The branch audit's table, from attempt records alone (checkpoint-rl-plan.md, stage 2)."""
import json
from pathlib import Path

from twwarhammer3.battle import audit, checkpoint
from twwarhammer3.battle.candidates import candidates

CONTEXT = {"phase": "Deployed", "time_ms": 210100, "terrain": {"bounds": {
    "min_x": -512, "max_x": 512, "min_z": -512, "max_z": 512}},
    "friendly": [{"id": "f1", "class": "infantry", "range": 0, "ammo": 0, "men": 90, "x": 0,
                  "z": 0, "state": []},
                 {"id": "f2", "class": "missile", "range": 145, "ammo": 900, "men": 68, "x": 10,
                  "z": 0, "state": []}],
    "enemy": [{"id": "e1", "men": 80, "x": 40, "z": 0, "state": []}]}


def write_audit(tmp_path: Path, outcomes: dict, repeat_ending="won", refused=()):
    tmp_path.mkdir(parents=True, exist_ok=True)
    record = tmp_path / "record.json"
    record.write_text(json.dumps({"root": "root", "tick": 2100}))
    output = tmp_path / "audit"
    output.mkdir()
    plan = {"name": "a", "rungs": [{"record": str(record)}], "repeat": ["attack_nearest"]}
    (output / "plan.json").write_text(json.dumps(plan))
    listed = candidates(CONTEXT)["candidates"]
    jobs = [(None, 0)] + [(c, 0) for c in listed] + [(listed[1], 1)]
    for index, (candidate, repeat) in enumerate(jobs):
        run = output / f"attempt-{index:04d}"
        (run / "native").mkdir(parents=True)
        result = "won" if candidate is None else outcomes[candidate["id"]]
        if repeat:
            result = repeat_ending
        attempt = {"plan": {"record": str(record)}, "status": result,
                   "engine_ending": {"result": result, "battle_ms": 298000}}
        if candidate is not None:
            attempt["plan"].update(candidate=candidate["id"], repeat=repeat, injection={
                "orders": candidate["orders"], "context": CONTEXT, "context_hash": "h"})
            attempt["attribution"] = {"applied_ms": 210400, "status": None}
            if candidate["id"] in refused:
                attempt.update(status="injection_failed", attribution={
                    "clause": "results", "reason": {"refused": [{"ok": False}]}})
        attempt["reward"] = checkpoint.reward(attempt) if attempt["status"] != (
            "injection_failed") else None
        (run / "attempt.json").write_text(json.dumps(attempt))
        rows = [{"event": "tick", "tick": t, "checksum": t + (result == "lost")}
                for t in range(2101, 2990)]
        (run / "native/native.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        (run / "observations.jsonl").write_text("")
    return output


OUTCOMES = {"noop": "won", "attack_nearest": "won", "rush_nearest": "lost",
            "fall_back_f2": "lost", "charge_f1": "won"}


def test_a_rung_with_winners_and_losers_and_a_matching_repeat_passes(tmp_path):
    table = audit.table(write_audit(tmp_path, OUTCOMES))
    rung = table["rungs"][0]
    assert table["pass"] and rung["rewards"] == [1, 1, 0, 0, 1]
    assert [c["id"] for c in rung["candidates"]] == list(OUTCOMES)
    assert rung["launches"] == 7 and rung["statuses"] == {"won": 4, "lost": 2}
    assert rung["repeats"][0]["match"] and rung["reference"].endswith("attempt-0000")


def test_a_flat_rung_a_repeat_that_differs_and_a_refusal_are_reported(tmp_path):
    flat = audit.table(write_audit(tmp_path / "flat", {k: "won" for k in OUTCOMES}))
    assert not flat["pass"] and not flat["rungs"][0]["verdict"]["winner_and_loser"]
    differs = audit.table(write_audit(tmp_path / "differs", OUTCOMES, repeat_ending="lost"))
    assert not differs["rungs"][0]["verdict"]["repeats_match"]
    refused = audit.table(write_audit(tmp_path / "refused", OUTCOMES, refused=("charge_f1",)))
    rung = refused["rungs"][0]
    assert rung["refused"] == ["charge_f1"] and len(rung["candidates"]) == 4
    assert rung["verdict"]["applied_or_refused"] and refused["pass"]
