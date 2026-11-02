"""checkpoint.assess, witness, source_records and episode on hand-made run files, without the
game (checkpoint-rl-plan.md)."""
import contextlib
import json

import pytest

from twwarhammer3.battle import checkpoint


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def restore_run(run, handover_value):
    """A restore of save tick 1200 that reaches a won result; its rebuild reading at 1100
    matches the source, the one at the save tick is ``handover_value``."""
    rows = [{"event": "reading", "tick": 1100, "value": {"men": [120, 80]}},
            {"event": "ready", "wall_time": 1}, {"event": "restoring", "wall_time": 2},
            {"event": "restored", "name": "r-1200", "tick": 1200, "wall_time": 3},
            {"event": "reading", "tick": 1200, "value": handover_value},
            *({"event": "tick", "tick": t, "checksum": t} for t in range(1201, 1206)),
            {"event": "reading", "tick": 1300, "value": {"men": [90, 40]}}]
    jsonl(run / "native/native.jsonl", rows)
    observation = {"battle": "b", "seq": 1, "time_ms": 120300, "phase": "Deployed"}
    jsonl(run / "observations.jsonl", [
        {"read_wall": 1.0, "native_rows": len(rows), "observation": observation},
        {"read_wall": 2.0, "native_rows": len(rows),
         "observation": {**observation, "seq": 2, "time_ms": 120600, "result": "won"}}])
    plan = {"checkpoint": {"name": "r-1200", "tick": 1200}, "grid_ms": 300,
            "reading": {"men": [120, 80]}}
    return checkpoint.assess(run, plan, {"by": "result"})


def test_a_restore_whose_handover_reading_differs_is_a_restore_fault_without_reward(tmp_path):
    # checkpoint-rl-plan.md: an unequal handover reading is restore_fault; only won, lost and
    # draw carry a reward.
    same = restore_run(tmp_path / "same", {"men": [120, 80]})
    assert (same["status"], same["reward"]) == ("won", 1)
    assert same["restore_evidence"]["handover_reading_equal"] is True
    other = restore_run(tmp_path / "other", {"men": [120, 79]})
    assert (other["status"], other["reason"], other["reward"]) == (
        "restore_fault", "handover reading differs", None)
    assert other["restore_evidence"]["handover_reading_equal"] is False


def window(record):
    return [{"time_ms": 120400, "friendly": [{"id": "f1", **record}]}]


def test_a_move_is_witnessed_by_its_dest_on_the_x_z_plane_and_a_halt_by_no_moving_state():
    # Distances rest on JUDGEMENT src/twwarhammer3/battle/checkpoint.py witness (dest_m 1).
    # The mod publishes dest as [x, z] (twwarhammer3_battle.lua: get_x(), get_z()).
    move = {"unit": "f1", "type": "move", "x": 10.0, "z": 20.0, "run": False}
    dest_m = checkpoint.WITNESS["dest_m"]
    assert checkpoint.witness(move, None, window({"dest": [10.6, 20.6]}), dest_m) == "shown"
    assert checkpoint.witness(move, None, window({"dest": [10.8, 20.8]}), dest_m) is None
    assert checkpoint.witness(move, None, window({"dest": [20.0, 10.0]}), dest_m) is None
    assert checkpoint.witness(move, None, window({}), dest_m) is None
    assert checkpoint.witness(move, {"id": "f1", "dest": [10.0, 20.0]},
                              window({"dest": [10.0, 20.0]}), dest_m) == "unchanged"
    assert checkpoint.witness(move, None, [{"time_ms": 0, "friendly": []}], dest_m) is None
    halt = {"unit": "f1", "type": "halt"}
    assert checkpoint.witness(halt, {"id": "f1", "state": ["moving"]},
                              window({"state": ["idle"]}), dest_m) == "shown"
    assert checkpoint.witness(halt, None, window({"state": ["moving"]}), dest_m) is None
    assert checkpoint.witness(halt, None, [{"time_ms": 0, "friendly": []}], dest_m) is None


def test_source_records_mark_saves_at_the_ending_unusable_and_late_by_the_margin(tmp_path):
    source, ticks = tmp_path / "source", (600, 900, 1200)
    jsonl(source / "native/native.jsonl", [
        *({"event": "reading", "tick": t, "value": {"remaining_s": 300 - t / 10}} for t in ticks),
        *({"event": "saved", "name": f"r-{t}", "tick": t, "checksum": t, "lua_seed": 1,
           "seed_at_tick": 1} for t in ticks)])
    jsonl(source / "observations.jsonl", [{"read_wall": 0, "native_rows": 0, "observation": {
        "friendly": [{"id": "f1"}], "enemy_roster": [{}, {}],
        "armies": {"player": {"faction": "emp"}, "enemy": {"faction": "grn"}}}}])
    (source / "replays").mkdir()
    for t in ticks:
        (source / "replays" / f"r-{t}.replay").write_bytes(b"replay %d" % t)
    # The battle ended at 120 s, the time of tick 1200.
    (source / "attempt.json").write_text(json.dumps({
        "status": "won", "engine_ending": {"result": "won", "battle_ms": 120000},
        "plan": {"scenario": {"inline": True}, "grid_ms": 300, "observe_ms": 300},
        "manifest": {"deployment": {"pack": {"sha256": "p"}}, "agent_sha256": "a",
                     "source_revision": "rev"},
        "restore_evidence": {"mod_start_ms": 4900}}))
    library = tmp_path / "library"
    records = checkpoint.source_records(source, library, root="r", late_margin_s=30)
    assert [(r["tick"], r["usable"], r["late"]) for r in records] == [
        (600, True, True), (900, True, True), (1200, False, False)]
    assert [r["remaining_ms"] for r in records] == [240000, 210000, 180000]
    first = records[0]
    assert first["replay"] == f"r-600-{first['replay_sha256'][:12]}.replay"
    assert (library / "600" / first["replay"]).read_bytes() == b"replay 600"
    assert first["scenario_key"] == "emp(1) vs grn(2)"
    # The latest record that is both usable and late.
    assert checkpoint.late_rung(library) == library / "900/record.json"


@pytest.mark.parametrize("failure,status,by", [
    (RuntimeError("the game is gone"), "infrastructure", "exception"),
    (KeyboardInterrupt(), "interrupted", "interrupt")])
def test_a_step_run_stopped_by_an_exception_is_written_unscored(tmp_path, monkeypatch, failure,
                                                                status, by):
    output = tmp_path / "attempt"

    @contextlib.contextmanager
    def launched(*args):
        # The battle ended before the failure: assessing it would score a win.
        jsonl(output / "observations.jsonl", [{"read_wall": 1, "native_rows": 0, "observation": {
            "seq": 1, "time_ms": 1000, "phase": "Deployed", "result": "won"}}])
        raise failure
        yield

    # refuse and move_saves would read the game's user folder through Windows Python.
    monkeypatch.setattr(checkpoint, "refuse", lambda plan: None)
    monkeypatch.setattr(checkpoint, "limits_for", lambda plan: {})
    monkeypatch.setattr(checkpoint, "launched", launched)
    monkeypatch.setattr(checkpoint, "move_saves", lambda plan, output: [])
    with pytest.raises(type(failure)):
        checkpoint.episode({}, output)
    attempt = json.loads((output / "attempt.json").read_text())
    assert (attempt["status"], attempt["runner_end"]["by"]) == (status, by)
    assert "reward" not in attempt and "restore_evidence" not in attempt
