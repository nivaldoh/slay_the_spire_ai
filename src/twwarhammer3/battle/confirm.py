"""The closed-loop check of checkpoint RL (checkpoint-rl-plan.md, stage 4): the trained choice
executed through the real path and compared with its audit attempt.

``score`` runs in its own model process and writes prelaunch.json; ``launch`` runs after that
process has exited and the GPU lease is free, executes the chosen batch in one step run and
writes confirm.json; ``clauses`` re-derives the verdict from the records alone.

JUDGEMENT: stage4_check — Claude, 2026-10-26: overfit to 0.95 after U 300 updates, a 2-launch
closed loop with a deranged control; versus overfitting alone (competes with checkpoint-rl.md
`verification_plan`). Whether the first method counts as working rests on this.
"""
import json
import math
from pathlib import Path

from gameai.provenance import sha256, write_json
from twwarhammer3.battle import checkpoint
from twwarhammer3.battle.candidates import candidates, describe, slot_to_candidate

THETA_FIT = 0.95


def overfit_passed(evaluation: dict, task: dict, theta: float = THETA_FIT) -> bool:
    """Mass on the training target's winners at least theta, averaged over the evaluation
    orderings, and the argmax a winner under every one of them."""
    result = evaluation["metrics"]["tasks"][task["hash"]]
    return result["mass"] >= theta and all(result["hits"])


def chosen(rows: list[dict]) -> int:
    """The candidate with the highest ordering-averaged probability."""
    n = len(rows[0]["permutation"])
    averaged = [0.0] * n
    for row in rows:
        for slot, value in enumerate(row["slot_log_probs"]):
            averaged[slot_to_candidate(row["permutation"], slot)] += math.exp(value) / len(rows)
    return max(range(n), key=averaged.__getitem__)


def score(plan: dict, output: Path) -> dict:
    """Model process: reload the adapter, rescore the rung's task under its evaluation
    orderings and run every pre-launch check; writes prelaunch.json."""
    from twwarhammer3.battle import rl

    rl.refuse_beside_game()
    declaration = json.loads(Path(plan["adapter"]).read_text())
    evaluation = json.loads(Path(plan["evaluation"]).read_text())
    tasks = rl.read_task_set(Path(plan["task_set"]))
    table_path = Path(plan["table"])
    table = json.loads(table_path.read_text())
    rung = table["rungs"][plan.get("rung", 0)]
    task = next(t for t in tasks["tasks"] if t["provenance"].get("tick") == rung["tick"]
                and t["provenance"].get("root") == rung["root"])
    output.mkdir(parents=True)
    write_json(output / "plan.json", plan)
    with rl.gpu_lease(rl.GPU_LOCK_PATH):
        model, tokenizer = rl.load_adapter(declaration, trainable=False)
        model.eval()
        scorer = rl.CandidateScorer(model, tokenizer, temperature=declaration["temperature"],
                                    token_cap=declaration["token_cap"])
        rows = rl.score_orderings(scorer, task)
    recorded = evaluation["scored"][task["hash"]]
    deviation = max(abs(a - b) for row, old in zip(rows, recorded)
                    for a, b in zip(row["slot_log_probs"], old["slot_log_probs"]))
    pick = chosen(rows)
    identifier = task["candidates"][pick]["id"]
    true_rewards = dict(zip([c["id"] for c in rung["candidates"]], rung["rewards"]))
    target = task["rewards"][pick] == 1
    checks = {
        "table_sha256": sha256(table_path) == plan["table_sha256"],
        "mapping": rung["mapping"] == task["mapping"],
        "tensors": True,  # load_adapter refused any difference from the declaration
        "reload": deviation <= plan["tolerance"],
        "same_choice": pick == chosen(recorded),
        "overfit": overfit_passed(evaluation, task, plan.get("theta_fit", THETA_FIT)),
        "reward": (target and true_rewards[identifier] == 0) if plan.get("control")
        else true_rewards[identifier] == 1}
    result = {"checks": checks, "pass": all(checks.values()), "deviation": deviation,
              "chosen": identifier, "rows": rows, "task": task["hash"],
              "rung": {"root": rung["root"], "tick": rung["tick"], "record": rung["record"],
                       "reference": rung["reference"]}}
    write_json(output / "prelaunch.json", result)
    return result


def launch(plan: dict, output: Path) -> dict:
    """Game process: the chosen candidate's batch, rebuilt from candidates(context), injected
    at the audit's tick in one step run; then the four clauses."""
    from twwarhammer3.battle import rl

    with rl.gpu_lease(rl.GPU_LOCK_PATH):  # no model process may hold it now
        pass
    prelaunch = json.loads((output / "prelaunch.json").read_text())
    if not prelaunch["pass"]:
        raise RuntimeError(f"pre-launch checks failed: {prelaunch['checks']}")
    table = json.loads(Path(plan["table"]).read_text())
    rung = table["rungs"][plan.get("rung", 0)]
    record_path = Path(rung["record"])
    record = json.loads(record_path.read_text())
    reference = Path(rung["reference"])
    listed = candidates(rung["context"])["candidates"]
    batch = next(c for c in listed if c["id"] == prelaunch["chosen"])["orders"]
    audit_plan = json.loads((Path(rung["attempts"][0]["attempt"]) / "attempt.json")
                            .read_text())["plan"]
    injection = checkpoint.injection_for(reference, record, batch,
                                         f"confirm-{output.name}-{prelaunch['chosen']}",
                                         audit_plan["injection"]["tick"])
    checkpoint.restore_episode(record_path, {
        "observe_ms": 300, "readings": {"every": 100, "lua": checkpoint.READING_LUA},
        "limits": checkpoint.limits_covering(record), "injection": injection,
        "reference": str(reference), "candidate": prelaunch["chosen"]}, output / "attempt")
    result = {"plan": plan, "chosen": prelaunch["chosen"], "clauses": clauses(output)}
    result["pass"] = all(result["clauses"].values()) if not plan.get("control") else (
        all(v for k, v in result["clauses"].items() if k != "d_live_win")
        and result["clauses"]["d_live_win"] is False)
    write_json(output / "confirm.json", result)
    return result


def clauses(output: Path) -> dict:
    """(a) to (d) from prelaunch.json, the table, the audit attempt and the live attempt."""
    prelaunch = json.loads((output / "prelaunch.json").read_text())
    plan = json.loads((output / "plan.json").read_text())
    table = json.loads(Path(plan["table"]).read_text())
    rung = table["rungs"][plan.get("rung", 0)]
    listed = rung["candidates"]
    live = json.loads((output / "attempt" / "attempt.json").read_text())
    executed = live["plan"]["injection"]["orders"]
    audited = next(a for a in rung["attempts"] if a["candidate"] == prelaunch["chosen"]
                   and a["repeat"] == 0)
    audit_attempt = json.loads((Path(audited["attempt"]) / "attempt.json").read_text())
    lines = all(row["argmax_line"] == describe(
        listed[slot_to_candidate(row["permutation"], row["argmax_slot"])]["orders"])
        for row in prelaunch["rows"])
    pair = checkpoint.compare_attempts(Path(audited["attempt"]), output / "attempt",
                                       100 * rung["tick"])
    rewards = dict(zip([c["id"] for c in listed], rung["rewards"]))
    return {
        "a_lines_and_batch": lines and checkpoint.digest(executed) == audited["batch_hash"],
        "b_reproduces_audit": (pair["checksum_mismatches"] == 0 and pair["ticks"] > 0
                               and pair["endings_equal"] and not pair["observations_unequal"]
                               and (live.get("attribution") or {}).get("applied_ms")
                               == audited["applied_ms"]),
        "c_table_matches_attempt": rewards[prelaunch["chosen"]] == checkpoint.reward(
            audit_attempt),
        "d_live_win": live.get("reward") == 1}
