"""Checkpoint RL step runs without the game: statuses, the grid rule, attribution, the public
projection, library refusals, the end rule and the comparator (checkpoint-rl-plan.md, stage 1).

Streams are synthetic in the agent's row shapes; the real restore-a stream and the recount use
runs/twwarhammer3/checkpoint-check-20261025c/ and skip when it is absent.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from gameai.provenance import REPO_ROOT, sha256
from twwarhammer3.battle import checkpoint, play

EVIDENCE = REPO_ROOT / "runs/twwarhammer3/checkpoint-check-20261025c"
RESTORE = {"name": "cp", "tick": 1200, "checksum": 1, "lua_seed": 2, "seed_at_tick": 3}
T = 1202


def rows(*, stop=2000, restored=True, name="cp", tick=1200, lua_at=None, insert=()):
    """ready, restoring, a checksum per tick, restored at 1200, done, one late tick, detach.
    ``insert`` adds (after_tick, row) pairs."""
    out = [{"event": "ready"}, {"event": "restoring", "name": "cp", "tick": 1200}]
    extra = {}
    for after, row in insert:
        extra.setdefault(after, []).append(row)
    for t in range(1, stop + 1):
        out.append({"event": "tick", "tick": t, "checksum": 7 * t})
        if t == 1200 and restored:
            out.append({"event": "restored", "name": name, "tick": tick, "lua_seed_matches": True})
        if t == lua_at:
            out.append({"event": "lua", "tick": t, "label": "inject", "value": {"accepted": True}})
        out += extra.get(t, [])
    return out + [{"event": "done", "tick": stop}, {"event": "tick", "tick": stop + 1},
                  {"event": "detached", "reason": "application-requested"}]


def classify(stream, logged=(), plan=None):
    return checkpoint.classify(stream, list(logged), plan or {"checkpoint": RESTORE}, None)


INJECTED = {"checkpoint": RESTORE, "injection": {"tick": T}}
LUA_ERROR = {"event": "error", "tick": T, "message": "Error: Lua inject: [string \"=inject\"]:1:"
             " attempt to call global 'twwarhammer3_inject' (a nil value)"}


@pytest.mark.parametrize("stream,plan,status,late", [
    (rows(restored=False), None, "restore_failure", False),
    (rows(name="other"), None, "restore_failure", False),
    (rows(tick=1199), None, "restore_failure", False),
    (rows(insert=[(1150, {"event": "error", "tick": 1150, "message": "tick 1150 differs"})]),
     None, "restore_failure", False),
    (rows(lua_at=T, insert=[(1500, {"event": "error", "tick": 1500, "message": "x"})]), INJECTED,
     "restore_fault", False),
    (rows(insert=[(T, LUA_ERROR)]), INJECTED, "injection_failed", False),
    (rows(insert=[(T, {**LUA_ERROR, "message": "SyntaxError: Unexpected token"})]), INJECTED,
     "injection_failed", False),
    (rows(insert=[(1600, {"event": "detached", "reason": "process-terminated"})]), None,
     "restore_fault", False),
    (rows() + [{"event": "frida_error", "message": {"type": "error"}}], None, "stopped", True),
    (rows(), None, "stopped", False),
])
def test_statuses_follow_the_event_stream(stream, plan, status, late):
    verdict = classify(stream, plan=plan)
    assert verdict["status"] == status and bool(verdict["late_fault"]) is late


def test_a_won_result_observation_before_done_is_an_engine_result_and_the_tail_is_ignored():
    stream = rows()
    end = next(i for i, r in enumerate(stream) if r.get("tick") == 1800) + 1
    result = {"phase": "Complete", "result": "won", "time_ms": 180000, "remaining_ms": 900000}
    verdict = classify(stream, [{"native_rows": end, "observation": result}])
    assert verdict["status"] == "won" and verdict["late_fault"] is None
    assert verdict["engine_ending"] == {"result": "won", "ended_by": "engine_result",
                                        "battle_ms": 180000, "timer": None}


def test_negative_controls_an_observation_only_watcher_and_a_message_prefix_rule_misclassify():
    # A checksum fault leaves the game playing a replay that looks live, the mod publishing.
    stream = rows(insert=[(1150, {"event": "error", "tick": 1150, "message": "differs"})])
    result = {"phase": "Complete", "result": "won", "time_ms": 190000, "remaining_ms": 1}
    logged = [{"native_rows": len(stream) - 3, "observation": result}]
    assert classify(stream, logged)["status"] == "restore_failure"
    assert play.engine_ending(result)["result"] == "won"  # what reading only observations gives

    def prefix_rule(row):
        return "injection_failed" if row["message"].startswith("Error: Lua inject:") else "fault"
    syntax = {**LUA_ERROR, "message": "SyntaxError: Unexpected token"}
    assert prefix_rule(syntax) == "fault"
    assert classify(rows(insert=[(T, syntax)]), plan=INJECTED)["status"] == "injection_failed"


@pytest.mark.skipif(not EVIDENCE.exists(), reason="checkpoint-check-20261025c evidence absent")
def test_the_real_restore_stream_cut_before_restored_is_a_restore_failure():
    stream = checkpoint.read_rows(EVIDENCE / "restore-a")
    restored = next(i for i, r in enumerate(stream) if r.get("event") == "restored")
    plan = {"checkpoint": {"name": "checkpoint-check-20261025c-1200", "tick": 1200}}
    assert checkpoint.classify(stream, [], plan, None)["status"] == "stopped"
    assert checkpoint.classify(stream[:restored], [], plan, None)["status"] == "restore_failure"


def test_grid_rule_from_the_start_time_not_the_spacing():
    assert checkpoint.grid_ms(250) == 300
    times = [0, 4900, 5200, 6400, 7600, 7700]
    logged = [{"phase": "Loading" if t == 0 else "Deployed", "time_ms": t} for t in times]
    logged.append({"phase": "Complete", "result": "won", "time_ms": 7750})
    assert checkpoint.off_grid(logged, 4900, 300) == [7700]
    assert checkpoint.decision_times(4900, 300, 1200, 1202) == (120100, 120400)
    with pytest.raises(ValueError, match="on the mod's grid"):
        checkpoint.decision_times(4900, 300, 1200, 1201)
    with pytest.raises(ValueError, match="precedes the handover"):
        checkpoint.decision_times(4900, 300, 1200, 1200)
    log = "[100] loaded battle 1-2 for job x\n[4900] started: land"
    assert checkpoint.mod_start_ms(log) == 4900


def unit(uid, x, z, **fields):
    return {"id": uid, "type": "t", "x": x, "z": z, "men": 60, "state": [], "ammo": 0,
            "abilities": [], **fields}


def observation(t, seq, friendly=None, **fields):
    return {"schema": 1, "job": "j", "battle": "b", "seq": seq, "phase": "Deployed",
            "time_ms": t, "friendly": friendly or [unit("f1", 0, 0), unit("f2", 10, 0)],
            "enemy": [unit("e1", 100, 0)], "enemy_roster": [{"id": "e1", "type": "t"}], **fields}


ORDERS = [{"unit": "f1", "type": "attack", "target": "e1", "run": False}]


def attempt_logs(orders=ORDERS, *, ack=None, applied=120400, diverge=1205, hide_context=False,
                 change_context=False, target="e1", end_ms=None):
    """An attempt whose batch is acknowledged at ``applied`` and changes the battle from
    tick ``diverge``; returns (rows, logged, reference_rows, injection)."""
    context = observation(120100, 400)
    reference = [{"event": "tick", "tick": t, "checksum": 7 * t} for t in range(1, 1300)]
    stream = [dict(r) for r in reference]
    for r in stream:
        if diverge is not None and r["tick"] >= diverge:
            r["checksum"] += 1
    stream.insert(T, {"event": "lua", "tick": T, "label": "inject", "value": {"accepted": True}})
    logged = []
    for k, t in enumerate(range(119800, 126000, 300)):
        o = copy.deepcopy(context) if t == 120100 else observation(t, 399 + k)
        o["seq"] = 399 + k
        if t == 120100 and change_context:
            o["friendly"][0]["x"] = 1
        if t >= applied:
            o["orders"] = ack or {"request": "r1", "based_on": 400, "applied_ms": applied,
                                  "results": [{"index": i + 1, "unit": order["unit"], "ok": True}
                                              for i, order in enumerate(orders)]}
            o["friendly"][0]["target"] = target
        if t == 120100 and hide_context:
            continue
        logged.append({"native_rows": 0, "observation": o})
    if end_ms:
        logged.append({"native_rows": 0, "observation": {**observation(end_ms, 999),
                                                          "result": "won"}})
    injection = {"tick": T, "request": "r1", "based_on": 400, "orders": orders,
                 "context_ms": 120100, "applied_ms": 120400, "context": context,
                 "context_hash": checkpoint.projected_hash(context)}
    return stream, logged, reference, injection


def attribute(**kwargs):
    return checkpoint.attribute(*attempt_logs(**kwargs))


def test_attribution_passes_a_clean_attempt_and_names_each_failed_clause():
    clean = attribute()
    assert clean["status"] is None and clean["first_divergence"] == 1205
    assert clean["witness"] == {"f1": "shown"} and clean["flags"] == []
    bad_ack = {"request": "r1", "based_on": 400, "applied_ms": 120400}
    cases = {
        "context": (dict(change_context=True), "injection_failed"),
        "reader miss": (dict(hide_context=True), "infrastructure"),
        "acknowledged": (dict(ack={**bad_ack, "request": "other"}), "injection_failed"),
        "based_on": (dict(ack={**bad_ack, "based_on": 401}), "injection_failed"),
        "count": (dict(ack={**bad_ack, "results": []}), "injection_failed"),
        "refused": (dict(ack={**bad_ack, "results": [{"index": 1, "unit": "f1", "ok": False,
                                                      "error": "unreachable"}]}),
                    "injection_failed"),
        "applied_ms": (dict(applied=120700), "injection_failed"),
        "before_ending": (dict(applied=120700, end_ms=120700), "injection_failed"),
        "early": (dict(diverge=1203), "injection_failed"),
        "witness": (dict(target=None), "injection_failed"),
    }
    clauses = {}
    for name, (kwargs, status) in cases.items():
        verdict = attribute(**kwargs)
        assert verdict["status"] == status, name
        clauses[name] = verdict["clause"]
    assert clauses == {"context": "context", "reader miss": "context",
                       "acknowledged": "acknowledged", "based_on": "acknowledged",
                       "count": "results", "refused": "results", "applied_ms": "applied_ms",
                       "before_ending": "applied_ms", "early": "divergence_before_apply",
                       "witness": "witness"}
    # Equal to the result observation's time: the ending check alone.
    stream, logged, reference, injection = attempt_logs(end_ms=120400)
    logged = [r for r in logged if r["observation"]["time_ms"] < 120400 or
              r["observation"].get("result")]
    logged[-1]["observation"]["orders"] = {"request": "r1", "based_on": 400,
                                           "applied_ms": 120400,
                                           "results": [{"index": 1, "unit": "f1", "ok": True}]}
    assert checkpoint.attribute(stream, logged, reference, injection)["clause"] == "before_ending"


def test_attribution_flags_no_effect_and_an_unchanged_witness_and_checks_the_noop():
    assert attribute(diverge=None)["flags"] == ["no_effect"]
    stream, logged, reference, injection = attempt_logs()
    injection["context"]["friendly"][0]["target"] = "e1"
    assert checkpoint.attribute(stream, logged, reference, injection)["flags"] == [
        "witness: unchanged"]
    assert attribute(orders=[], diverge=None)["status"] is None
    assert attribute(orders=[])["clause"] == "noop"


def test_negative_control_a_request_and_all_ok_predicate_accepts_a_short_ack():
    _, logged, _, _ = attempt_logs(ack={"request": "r1", "based_on": 400, "applied_ms": 120400,
                                        "results": []})
    ack = next(r["observation"]["orders"] for r in logged if r["observation"].get("orders"))
    assert ack["request"] == "r1" and all(r.get("ok") for r in ack["results"])
    assert attribute(ack=ack)["status"] == "injection_failed"


def test_the_public_projection_drops_launch_ids_and_mod_memory_only():
    hidden = observation(5200, 1, evaluation={"sentinel": 1}, final={"sentinel": 2},
                         setup={"sentinel": 3})
    view = play.public(hidden, {})
    assert "sentinel" not in json.dumps(view)
    one = observation(5200, 7, friendly=[unit("f1", 0, 0, dest=[5, 5], attack_mode="melee",
                                              command_queue=[{}], navigation={"a": 1},
                                              abilities=[{"key": "k", "last_issued_ms": 9}])],
                      orders={"request": "r"}, army={"abilities": [{"key": "a",
                                                                   "last_issued_ms": 4}]})
    other = observation(5200, 3, friendly=[unit("f1", 0, 0, abilities=[{"key": "k"}])],
                        army={"abilities": [{"key": "a"}]})
    other.update(job="restore-a", battle="other")
    assert checkpoint.projected_hash(one) == checkpoint.projected_hash(other)
    assert checkpoint.digest(play.public(one, {})) != checkpoint.digest(play.public(other, {}))
    other["enemy_roster"] = [{"id": "e1", "type": "t", "dead": True}]
    assert checkpoint.projected_hash(one) != checkpoint.projected_hash(other)


def test_reward_reads_the_engine_ending_of_a_scored_attempt_only():
    won = {"status": "won", "engine_ending": {"result": "won", "ended_by": "time_limit"}}
    assert checkpoint.reward(won) == 1
    assert checkpoint.reward({**won, "late_fault": [{"event": "error"}]}) == 1
    assert checkpoint.reward({"status": "lost", "engine_ending": {"result": "lost"}}) == 0
    for status in ("stopped", "restore_fault", "injection_failed", "infrastructure"):
        assert checkpoint.reward({**won, "status": status}) is None
    with pytest.raises(ValueError):
        checkpoint.reward({"status": "won", "engine_ending": {"result": "lost"}})


@pytest.fixture
def game(tmp_path, monkeypatch):
    """A replays folder, a Frida venv path and environment hashes; no game."""
    replays = tmp_path / "user/replays"
    replays.mkdir(parents=True)
    (replays / "bystander.replay").write_bytes(b"other")
    frida = tmp_path / "python.exe"
    frida.write_text("")
    monkeypatch.setattr(checkpoint.runtime, "user_dir", lambda: tmp_path / "user")
    monkeypatch.setattr(checkpoint, "FRIDA_PYTHON", frida)
    monkeypatch.setattr(checkpoint, "pack_sha256", lambda: "pack")
    library = tmp_path / "library/1200"
    library.mkdir(parents=True)
    replay = library / "cp-abc.replay"
    replay.write_bytes(b"checkpoint")
    record = {**RESTORE, "replay": replay.name, "replay_sha256": sha256(replay), "usable": True,
              "exe_sha256": checkpoint.EXE_SHA256, "pack_sha256": "pack",
              "agent_sha256": sha256(checkpoint.AGENT), "remaining_ms": 60000,
              "mod_start_ms": 4900, "grid_ms": 300, "reading": {"time_ms": 120000}}
    (library / "record.json").write_text(json.dumps(record))
    return tmp_path, library / "record.json", replays


LIMITS = {"game_timeout_s": 300, "agent_seconds": 300, "episode_timeout_s": 300}


def test_records_and_launches_are_refused_before_any_game(game, monkeypatch):
    tmp_path, record_path, replays = game
    launched = []
    monkeypatch.setattr(checkpoint, "episode", lambda plan, output, sha, release: launched.append(
        (plan, sorted(p.name for p in replays.glob("*.replay")))) or release())
    plan = {"limits": LIMITS}
    record = json.loads(record_path.read_text())
    for key, value in (("exe_sha256", "x"), ("pack_sha256", "x"), ("agent_sha256", "x"),
                       ("usable", False), ("replay_sha256", "0" * 64)):
        record_path.write_text(json.dumps({**record, key: value}))
        with pytest.raises(ValueError):
            checkpoint.restore_episode(record_path, plan, tmp_path / "out")
    record_path.write_text(json.dumps(record))
    assert launched == []
    checkpoint.restore_episode(record_path, plan, tmp_path / "out")
    assert launched[0][1] == ["cp-abc.replay"] and launched[0][0]["checkpoint"] == RESTORE
    assert sorted(p.name for p in replays.glob("*.replay")) == ["bystander.replay"]
    # A copy that changed during the run marks the entry suspect; later restores refuse.
    def tamper(plan, output, sha, release):
        (replays / "cp-abc.replay").write_bytes(b"changed")
        return release()
    monkeypatch.setattr(checkpoint, "episode", tamper)
    result = checkpoint.restore_episode(record_path, plan, tmp_path / "out")
    assert result["replay_unchanged"] is False
    with pytest.raises(ValueError, match="suspect"):
        checkpoint.restore_episode(record_path, plan, tmp_path / "out")


@pytest.mark.parametrize("error", [RuntimeError("game gone"), KeyboardInterrupt()])
def test_the_copy_leaves_and_bystanders_return_after_an_exception_or_interrupt(game, monkeypatch,
                                                                               error):
    tmp_path, record_path, replays = game

    def fail(plan, output, sha, release):
        assert sorted(p.name for p in replays.glob("*.replay")) == ["cp-abc.replay"]
        raise error
    monkeypatch.setattr(checkpoint, "episode", fail)
    with pytest.raises(type(error)):
        checkpoint.restore_episode(record_path, {"limits": LIMITS}, tmp_path / "out")
    assert sorted(p.name for p in replays.glob("*.replay")) == ["bystander.replay"]
    assert not (replays / "checkpoint-aside").exists()


def test_step_run_refusals_need_no_game(game, monkeypatch):
    tmp_path, _, replays = game
    context = observation(120100, 400)
    plan = {"checkpoint": RESTORE, "mod_start_ms": 4900, "grid_ms": 300, "remaining_ms": 60000,
            "limits": LIMITS, "injection": {"tick": T, "orders": ORDERS, "context": context,
                                            "context_ms": 120100, "applied_ms": 120400}}
    checkpoint.refuse(plan)
    for change in ({"tick": 1201}, {"applied_ms": 120700},
                   {"orders": [{"unit": "f9", "type": "halt"}]}):
        with pytest.raises(Exception):
            checkpoint.refuse({**plan, "injection": {**plan["injection"], **change}})
    with pytest.raises(FileExistsError):
        checkpoint.refuse({**plan, "save_at": [{"tick": 1500, "name": "bystander"}]})
    (replays / "checkpoint-aside").mkdir()
    (replays / "checkpoint-aside/away.replay").write_bytes(b"")
    with pytest.raises(FileExistsError):
        checkpoint.refuse({**plan, "save_at": [{"tick": 1500, "name": "away"}]})
    checkpoint.limits_for(plan)
    with pytest.raises(ValueError, match="cannot contain"):
        checkpoint.limits_for({**plan, "remaining_ms": 250000})
    record = {"tick": 2100, "remaining_ms": 994797}
    checkpoint.limits_for({**plan, "checkpoint": record, "remaining_ms": 994797,
                           "limits": checkpoint.limits_covering(record)})
    monkeypatch.setattr(checkpoint, "FRIDA_PYTHON", tmp_path / "missing.exe")
    with pytest.raises(FileNotFoundError):
        checkpoint.refuse(plan)


class Agent:
    def poll(self):
        return None


class Reader:
    """observation.json as the mod rewrites it: each read returns the next observation."""
    def __init__(self, log, script):
        self.log, self.script = log, list(script)

    def read_observation(self):
        if not self.script:
            return None
        rows, observation = self.script.pop(0)
        with self.log.open("a") as handle:
            handle.writelines(json.dumps(r) + "\n" for r in rows)
        return observation


def test_a_source_run_ends_at_its_result_and_records_saves_it_never_reached(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoint, "SAVE_SETTLE_S", 0.3)
    log = tmp_path / "native.jsonl"
    log.write_text("")
    saves = [{"tick": t, "name": f"s{t}"} for t in (600, 900, 1200)]
    ticks = [{"event": "tick", "tick": t, "checksum": t} for t in range(1, 1000)]
    script = [(ticks[:599], observation(59800, 190)),
              ([ticks[599], {"event": "saved", "tick": 600, "name": "s600"}] + ticks[600:950],
               {**observation(95000, 300), "result": "lost"}),
              ([ticks[950]], None), ([{"event": "saved", "tick": 900, "name": "s900"}], None)]
    end = checkpoint.follow(log, Agent(), Reader(log, script), tmp_path,
                            {"save_at": saves}, {"episode_timeout_s": 30})
    assert end["by"] == "result" and end["saves"] == [600, 900] and end["not_saved"] == [1200]
    logged = checkpoint.read_observations(tmp_path)
    assert [r["observation"]["seq"] for r in logged] == [190, 300]
    assert logged[1]["native_rows"] == 951


def write_attempt(run: Path, stream, logged, ending=None):
    (run / "native").mkdir(parents=True)
    (run / "native/native.jsonl").write_text("".join(json.dumps(r) + "\n" for r in stream))
    (run / "observations.jsonl").write_text("".join(json.dumps(r) + "\n" for r in logged))
    (run / "attempt.json").write_text(json.dumps({"engine_ending": ending}))
    return run


def test_the_attempt_comparator_finds_each_difference_up_to_the_earlier_ending(tmp_path):
    def run(name, *, tick_change=None, obs_change=None, reading_change=None, ending_ms=150000,
            result="won", drop_reading=None):
        stream = []
        for t in range(1, 1600):
            stream.append({"event": "tick", "tick": t,
                           "checksum": 7 * t + (t == tick_change)})
            if t % 100 == 0 and t != drop_reading:
                stream.append({"event": "reading", "tick": t,
                               "value": {"x": t + (t == reading_change)}})
        logged = [{"native_rows": 0, "observation": observation(
            t, k, friendly=[unit("f1", 1 if t == obs_change else 0, 0)])}
            for k, t in enumerate(range(120100, 150100, 300))]
        ending = {"result": result, "battle_ms": ending_ms}
        return write_attempt(tmp_path / name, stream, logged, ending)

    base = run("a")
    same = checkpoint.compare_attempts(base, run("b"), 120000)
    assert same["checksum_mismatches"] == 0 and not same["readings_unequal"]
    assert same["observations"] == 100 and not same["observations_unequal"]
    assert same["endings_equal"] and same["ticks_uncompared"] == 2 * 99
    assert same["readings_uncompared"] == 2 * 0 + 0
    assert checkpoint.compare_attempts(base, run("c", tick_change=1300), 120000)[
        "first_mismatch"] == 1300
    assert checkpoint.compare_attempts(base, run("d", obs_change=130000), 120000)[
        "observations_unequal"] == [130000]
    assert checkpoint.compare_attempts(base, run("e", reading_change=1400), 120000)[
        "readings_unequal"] == [1400]
    assert not checkpoint.compare_attempts(base, run("f", result="lost"), 120000)["endings_equal"]
    assert checkpoint.compare_attempts(base, run("g", drop_reading=1300), 120000)[
        "readings_one_side"] == [1300]
    late = checkpoint.compare_attempts(base, run("h", ending_ms=140000, tick_change=1450), 120000)
    assert late["checksum_mismatches"] == 0 and late["last_tick"] == 1400


@pytest.mark.skipif(not EVIDENCE.exists(), reason="checkpoint-check-20261025c evidence absent")
def test_the_recount_of_the_agreed_check_is_unchanged():
    source = checkpoint.events(EVIDENCE / "source")
    changed = checkpoint.compare(source, checkpoint.events(EVIDENCE / "changed"))
    assert (changed["ticks"], changed["checksum_mismatches"]) == (2001, 699)
    script = REPO_ROOT / "tests/twwarhammer3/check_wh3_checkpoint.py"
    done = subprocess.run([sys.executable, str(script), "--recount", str(EVIDENCE)],
                          capture_output=True, text=True)
    assert done.returncode == 0 and json.loads(done.stdout)["pass"] is True
