"""battle/checkpoint.py rules the other checkpoint tests left open: boundaries of its refusals,
statuses and attribution clauses, and the records a step run writes (no game).

Each wrong version these tests catch passed every test before (cleanup 2026-11-02).
"""
import json

import pytest
from test_wh3_checkpoint_rl import (
    INJECTED,
    LUA_ERROR,
    RESTORE,
    Agent,
    Reader,
    T,
    attempt_logs,
    observation,
    rows,
    write_attempt,
)

from gameai.provenance import sha256
from twwarhammer3.battle import checkpoint


def test_a_restore_runs_lua_at_tick_1_and_after_its_checkpoint_but_not_at_it(tmp_path,
                                                                            monkeypatch):
    # run(): "A restore's lua_at may hold only tick-1 setup and orders after the checkpoint:
    # earlier inputs come from the replay." The checkpoint tick is not after the checkpoint.
    (tmp_path / "user/replays").mkdir(parents=True)
    (tmp_path / "user/replays/cp.replay").write_bytes(b"checkpoint")
    monkeypatch.setattr(checkpoint.runtime, "user_dir", lambda: tmp_path / "user")
    launched = []
    monkeypatch.setattr(checkpoint, "run_in_game",
                        lambda plan, output, replay_sha256: launched.append(plan["lua_at"]))

    def lua_at(*ticks):
        return [{"tick": tick, "label": f"at-{tick}", "lua": ""} for tick in ticks]
    restore = {"name": "cp", "tick": 1200}
    checkpoint.run({"checkpoint": restore, "lua_at": lua_at(1, 1201)}, tmp_path / "run")
    assert launched == [lua_at(1, 1201)]
    with pytest.raises(ValueError, match="only at tick 1 and after its checkpoint"):
        checkpoint.run({"checkpoint": restore, "lua_at": lua_at(1200)}, tmp_path / "run")
    assert len(launched) == 1


def test_reading_differences_name_a_missing_field_a_shorter_list_and_an_element():
    # differences(): "Paths where two readings differ"; compare() and the handover check of
    # assess() count a reading as equal only without any. READING_LUA leaves `script` out (nil)
    # in a battle without a checkpoint script.
    reading = {"units": [{"men": 60}, {"men": 40}], "script": {"fires": 1}}
    assert list(checkpoint.differences(reading, {"units": [{"men": 60}]})) == [
        ".script", ".units"]
    assert list(checkpoint.differences(
        reading, {**reading, "units": [{"men": 60}, {"men": 39}]})) == [".units[1].men"]


def test_classify_names_the_fault_row_and_reads_the_lua_event_of_the_injection_tick():
    # checkpoint-rl-plan.md, "Exposing checkpoint errors": every detector writes its reason; a
    # fault before `restored`, or no `restored`, is restore_failure. Stage 1: an error row at
    # the injection tick "with no lua event for that tick before it" is injection_failed; a
    # fault after the handover is otherwise restore_fault. A tick-1 setup Lua event is not the
    # injection's.
    fault = {"event": "error", "tick": 1150, "message": "tick 1150 differs"}
    for stream in (rows(insert=[(1150, fault)]), rows(restored=False, insert=[(1150, fault)])):
        verdict = checkpoint.classify(stream, [], {"checkpoint": RESTORE}, None)
        assert (verdict["status"], verdict["reason"]) == ("restore_failure", fault)
    after_lua = {"event": "error", "tick": T, "message": "Error: hook failed"}
    verdict = checkpoint.classify(rows(lua_at=T, insert=[(T, after_lua)]), [], INJECTED, None)
    assert verdict["status"] == "restore_fault"
    setup = {"event": "lua", "tick": 1, "label": "setup", "value": None}
    verdict = checkpoint.classify(rows(insert=[(1, setup), (T, LUA_ERROR)]), [], INJECTED, None)
    assert verdict["status"] == "injection_failed"


def test_attribution_passes_with_a_setup_lua_event_and_a_divergence_at_the_applied_tick():
    # Stage 1: the clause reads "the lua event for the injection"; checksums must equal the
    # reference's up to applied_ms, "a difference before it is a fault". The restored-episode
    # check counts a divergence at the applied tick as after the apply
    # (first_divergence * 100 >= applied_ms). A tick-1 setup Lua returns nothing (null).
    stream, logged, reference, injection = attempt_logs(diverge=1204)
    setup = {"event": "lua", "tick": 1, "label": "setup", "value": None}
    verdict = checkpoint.attribute([setup, *stream], logged, reference, injection)
    assert verdict["status"] is None and verdict["first_divergence"] == 1204


def test_a_failed_attribution_clause_records_the_mods_reply_and_only_the_refused_results():
    # Stage 1: `accepted: false` fails the accepted clause; "injection_failed (... the reason
    # included: `refused` for an engine refusal". The refusal shape is the mod's
    # (twwarhammer3_battle.lua inject); a run that never reached the tick has no lua event.
    refusal = {"accepted": False, "reason": "a request is pending"}
    stream, logged, reference, injection = attempt_logs()
    for row in stream:
        if row.get("event") == "lua":
            row["value"] = refusal
    verdict = checkpoint.attribute(stream, logged, reference, injection)
    assert (verdict["status"], verdict["clause"], verdict["reason"]) == (
        "injection_failed", "accepted", refusal)
    stream = [row for row in stream if row.get("event") != "lua"]
    verdict = checkpoint.attribute(stream, logged, reference, injection)
    assert (verdict["status"], verdict["clause"], verdict["reason"]) == (
        "injection_failed", "accepted", None)
    orders = [{"unit": "f1", "type": "attack", "target": "e1", "run": False},
              {"unit": "f2", "type": "halt"}]
    refused = {"index": 2, "unit": "f2", "ok": False, "error": "unreachable"}
    ack = {"request": "r1", "based_on": 400, "applied_ms": 120400,
           "results": [{"index": 1, "unit": "f1", "ok": True}, refused]}
    verdict = checkpoint.attribute(*attempt_logs(orders, ack=ack))
    assert (verdict["clause"], verdict["reason"]) == ("results", {"refused": [refused]})


def test_a_step_run_is_refused_at_the_handover_time_and_by_limits_without_the_rebuild():
    # checkpoint-rl-plan.md, step run: before launch it refuses "a T ... with a context before
    # the handover" (decision 2: the context's time_ms "must be later than the handover
    # (100 × S)") and "a plan whose limits cannot contain the rung's remaining_ms plus the
    # measured overhead and a margin"; a restore also rebuilds its ticks before the handover
    # (the comment on OVERHEAD_S, limits_covering). A source plan rebuilds nothing.
    # Rests on JUDGEMENT src/twwarhammer3/battle/checkpoint.py dispatch: the grid rule.
    # A mod start of 4800 ms puts a grid time on 120000 ms, the handover of a save at 1200.
    with pytest.raises(ValueError, match="precedes the handover"):
        checkpoint.decision_times(4800, 300, 1200, 1201)
    assert checkpoint.decision_times(4800, 300, 1200, 1204) == (120300, 120600)
    limits = {"game_timeout_s": 300, "agent_seconds": 300, "episode_timeout_s": 300}
    spare_s = 5  # what 300 s leaves after the battle, the overhead and the margin
    remaining_ms = 1000 * (300 - checkpoint.OVERHEAD_S - checkpoint.MARGIN_S - spare_s)
    source = {"remaining_ms": remaining_ms, "limits": limits}
    assert checkpoint.limits_for(source) == limits
    restore = {"name": "cp", "tick": round(2 * spare_s / checkpoint.REBUILD_S_PER_TICK)}
    with pytest.raises(ValueError, match="cannot contain"):
        checkpoint.limits_for({**source, "checkpoint": restore})


def test_a_save_before_the_result_that_never_lands_is_recorded_not_saved(tmp_path,
                                                                         monkeypatch):
    # checkpoint-rl-plan.md, step run: at the result it "waits, bounded, for the saved rows of
    # declared saves before the result's tick"; not_saved lists the declared saves the agent
    # did not write. The agent's first row, `ready`, has no tick (checkpoint_agent.js).
    monkeypatch.setattr(checkpoint, "SAVE_SETTLE_S", 0.3)
    log = tmp_path / "native.jsonl"
    log.write_text("")
    ticks = [{"event": "tick", "tick": t, "checksum": t} for t in range(1, 952)]
    written = [{"event": "ready", "base": "0x1"}, *ticks[:600],
               {"event": "saved", "tick": 600, "name": "s600"}, *ticks[600:]]
    script = [(written, {**observation(95000, 300), "result": "lost"})]
    saves = [{"tick": t, "name": f"s{t}"} for t in (600, 900, 1200)]
    end = checkpoint.follow(log, Agent(), Reader(log, script), tmp_path, {"save_at": saves},
                            {"episode_timeout_s": 5})
    assert end == {"by": "result", "tick": 951, "saves": [600, 900], "not_saved": [900, 1200]}


def test_a_copy_gone_after_the_run_marks_its_library_entry_suspect(tmp_path, monkeypatch):
    # restore_episode(): "A copy that changed marks the library entry SUSPECT, refusing later
    # restores"; release() hashes a missing copy as None, a change.
    (tmp_path / "user/replays").mkdir(parents=True)
    monkeypatch.setattr(checkpoint.runtime, "user_dir", lambda: tmp_path / "user")
    monkeypatch.setattr(checkpoint, "pack_sha256", lambda: "pack")
    directory = tmp_path / "library/1200"
    directory.mkdir(parents=True)
    (directory / "cp.replay").write_bytes(b"checkpoint")
    record = {**RESTORE, "replay": "cp.replay", "replay_sha256": sha256(directory / "cp.replay"),
              "usable": True, "exe_sha256": checkpoint.EXE_SHA256, "pack_sha256": "pack",
              "agent_sha256": sha256(checkpoint.AGENT), "remaining_ms": 60000,
              "mod_start_ms": 4900, "grid_ms": 300, "reading": {}}
    (directory / "record.json").write_text(json.dumps(record))

    def episode(plan, output, replay_sha256, release):
        (tmp_path / "user/replays/cp.replay").unlink()
        return release()
    monkeypatch.setattr(checkpoint, "episode", episode)
    result = checkpoint.restore_episode(directory / "record.json", {}, tmp_path / "out")
    assert result == {"replay_unchanged": False}
    with pytest.raises(ValueError, match="suspect"):
        checkpoint.restore_episode(directory / "record.json", {}, tmp_path / "out")


def test_the_attempt_comparator_reads_rows_without_a_tick_and_attempts_without_an_ending(
        tmp_path):
    # compare_attempts(): "compare()'s fields up to the earlier engine-ending tick"; with no
    # ending on either side, every tick. Agent rows such as `ready` and `detached` carry no
    # tick (checkpoint_agent.js).
    def stream():
        return [{"event": "ready", "base": "0x1"},
                *({"event": "tick", "tick": t, "checksum": 7 * t} for t in range(1, 1301)),
                {"event": "detached", "reason": "application-requested"}]
    for name, ending, last_tick in (("ended", {"result": "won", "battle_ms": 125000}, 1250),
                                    ("stopped", None, 1300)):
        a = write_attempt(tmp_path / f"{name}-a", stream(), [], ending)
        b = write_attempt(tmp_path / f"{name}-b", stream(), [], ending)
        result = checkpoint.compare_attempts(a, b, 120000)
        assert (result["checksum_mismatches"], result["last_tick"]) == (0, last_tick)
