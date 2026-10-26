"""The closed-loop check's clauses and pre-launch rules on synthetic records (no game, no
model): each fixture breaks one thing (checkpoint-rl-plan.md, stage 4)."""
import json
import math
from pathlib import Path

import pytest

from twwarhammer3.battle import checkpoint, confirm
from twwarhammer3.battle.candidates import describe

LISTED = [{"id": "noop", "orders": [], "description": "no new orders"},
          {"id": "attack_nearest", "orders": [{"unit": "f1", "type": "attack", "target": "e1",
                                               "run": False}]},
          {"id": "fall_back_f2", "orders": [{"unit": "f2", "type": "move", "x": 1.0, "z": 2.0,
                                             "run": False}]}]
for item in LISTED:
    item["description"] = describe(item["orders"])
REWARDS = [0, 1, 0]


def attempt_dir(path: Path, *, ending="won", bump=None, applied=210400, orders=None):
    (path / "native").mkdir(parents=True)
    rows = [{"event": "tick", "tick": t, "checksum": t + (t == bump)} for t in range(2101, 2990)]
    (path / "native/native.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (path / "observations.jsonl").write_text("")
    attempt = {"status": ending, "engine_ending": {"result": ending, "battle_ms": 298000},
               "reward": int(ending == "won"), "attribution": {"applied_ms": applied},
               "plan": {"injection": {"orders": orders if orders is not None
                                      else LISTED[1]["orders"]}}}
    (path / "attempt.json").write_text(json.dumps(attempt))
    return path


def rows(chosen_slot_line=None):
    """Two evaluation orderings whose argmax slot shows attack_nearest."""
    out = []
    for permutation in ([1, 2, 0], [2, 0, 1]):
        slot = permutation.index(1)
        logs = [math.log(0.9 if k == slot else 0.05) for k in range(3)]
        out.append({"permutation": permutation, "slot_log_probs": logs, "argmax_slot": slot,
                    "argmax_candidate": 1, "argmax_line": chosen_slot_line
                    or LISTED[1]["description"]})
    return out


def build(tmp_path, *, line=None, live=None, audit=None, table_reward=1, executed=None):
    audited = attempt_dir(tmp_path / "audit-1", **(audit or {}))
    table = {"rungs": [{"root": "r", "tick": 2100, "candidates": LISTED,
                        "rewards": [0, table_reward, 0], "attempts": [
                            {"candidate": "attack_nearest", "repeat": 0,
                             "attempt": str(audited), "applied_ms": 210400,
                             "batch_hash": checkpoint.digest(LISTED[1]["orders"])}]}]}
    (tmp_path / "table.json").write_text(json.dumps(table))
    output = tmp_path / "confirm"
    output.mkdir()
    (output / "plan.json").write_text(json.dumps({"table": str(tmp_path / "table.json")}))
    (output / "prelaunch.json").write_text(json.dumps({"chosen": "attack_nearest",
                                                       "rows": rows(line)}))
    attempt_dir(output / "attempt", orders=executed, **(live or {}))
    return output


def test_a_clean_closed_loop_passes_every_clause(tmp_path):
    assert confirm.clauses(build(tmp_path)) == {
        "a_lines_and_batch": True, "b_reproduces_audit": True,
        "c_table_matches_attempt": True, "d_live_win": True}


@pytest.mark.parametrize("change,clause", [
    ({"line": LISTED[2]["description"]}, "a_lines_and_batch"),
    ({"executed": LISTED[2]["orders"]}, "a_lines_and_batch"),
    ({"live": {"bump": 2500}}, "b_reproduces_audit"),
    ({"live": {"applied": 210700}}, "b_reproduces_audit"),
    ({"table_reward": 0}, "c_table_matches_attempt"),
    ({"live": {"ending": "lost"}}, "d_live_win"),
])
def test_each_fixture_fails_only_its_clause(tmp_path, change, clause):
    result = confirm.clauses(build(tmp_path, **change))
    failed = [name for name, ok in result.items() if not ok]
    if clause == "d_live_win":
        assert "d_live_win" in failed and "a_lines_and_batch" not in failed
    else:
        assert failed == [clause]


def test_the_choice_is_the_ordering_averaged_argmax_and_overfit_needs_every_ordering():
    assert confirm.chosen(rows()) == 1
    two_winners = rows()
    two_winners[1]["slot_log_probs"] = [math.log(0.05), math.log(0.05), math.log(0.9)]
    assert confirm.chosen(two_winners) in (1, 2)
    evaluation = {"metrics": {"tasks": {"t": {"mass": 0.96, "hits": [1, 1, 1]}}}}
    assert confirm.overfit_passed(evaluation, {"hash": "t"})
    evaluation["metrics"]["tasks"]["t"]["hits"] = [1, 0, 1]
    assert not confirm.overfit_passed(evaluation, {"hash": "t"})
    evaluation["metrics"]["tasks"]["t"].update(hits=[1, 1, 1], mass=0.94)
    assert not confirm.overfit_passed(evaluation, {"hash": "t"})


def test_the_curriculum_rule_reads_the_rungs_mass_on_winners():
    from twwarhammer3.battle import rl

    evaluation = {"metrics": {"tasks": {"t": {"mass": 0.8, "hits": [0, 1]}}}}
    assert rl.curriculum_passed(evaluation, {"hash": "t"})
    evaluation["metrics"]["tasks"]["t"]["mass"] = 0.79
    assert not rl.curriculum_passed(evaluation, {"hash": "t"})
