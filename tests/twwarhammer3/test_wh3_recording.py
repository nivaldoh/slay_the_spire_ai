import json
from pathlib import Path

import pytest

from twwarhammer3.battle import replay
from twwarhammer3.battle.recording import copy_recording

SOURCE = Path("src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua")


def test_battle_script_parses_as_lua51_and_flushes_before_result_publication():
    lua = pytest.importorskip("lupa.lua51").LuaRuntime()
    compile_lua = lua.eval("function(source) return assert(loadstring(source)) end")
    source = SOURCE.read_text()
    assert compile_lua(source)
    finish = source.split("local function finish()", 1)[1].split("local function restart()", 1)[0]
    assert finish.index("record_replay(battle_time(), true)") < finish.index(
        "publish_observation(battle_time())")


def test_copy_keeps_interrupted_bytes_and_cannot_cross_rematches(tmp_path):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode-0000"
    bridge.mkdir()
    episode.mkdir()
    data = {"recorder": 1, "job": "job", "battle": "one", "time_ms": 0}
    raw = json.dumps(data) + '\n{"recorder":'
    (bridge / "replay-one.jsonl").write_text(raw)
    (bridge / "replay-two.jsonl").write_text(json.dumps({**data, "battle": "two"}))
    result = copy_recording(bridge, episode, job="job", battle="one")
    assert result["status"] == "copied"
    assert (episode / "replay.jsonl").read_text() == raw
    assert (
        copy_recording(bridge, episode, job="other", battle="one")["status"] == "identity_mismatch"
    )
    assert (
        copy_recording(bridge, episode, job="job", battle="../one")["status"] == "missing_battle_id"
    )
    assert copy_recording(bridge, episode, job="job", battle="absent")["status"] == "missing"


def test_recorder_gaps_terminal_frames_and_visibility_keep_stable_ids(tmp_path):
    episode = tmp_path / "episode-0000"
    episode.mkdir()
    base = {
        "job": "j",
        "battle": "b",
        "recorder": 1,
        "time_ms": 0,
        "friendly": [{"id": "f1", "x": 1, "z": 2}],
        "enemy": [{"id": "e1", "x": 3, "z": 4}],
        "enemy_roster": [{"id": "e1"}],
    }
    records = [
        base,
        {**base, "time_ms": 1000, "enemy": []},
        {**base, "time_ms": 4000},
        {**base, "time_ms": 4300, "terminal": True, "result": "won"},
        {**base, "time_ms": 5000, "battle": "wrong"},
    ]
    (episode / "trace.jsonl").write_text(
        json.dumps({"kind": "battle", "observation": {**base, "seq": 0}})
    )
    (episode / "replay.jsonl").write_text("\n".join(map(json.dumps, records)) + "\n{")
    payload = replay.build(episode, {"config": {}, "scenario": {}})
    frames = [f for f in payload["frames"] if f["source"]["file"] == "replay.jsonl"]
    assert [f["time_ms"] for f in frames] == [0, 1000, 4000, 4300]
    assert frames[1]["enemy"] == []
    assert frames[0]["enemy"][0]["id"] == frames[2]["enemy"][0]["id"] == "e1"
    assert frames[-1]["result"] == "won"
    assert len(payload["warnings"]) == 2
    assert not any(e["kind"] == "death" for e in payload["events"])


def test_lua_recorder_is_independent_public_throttled_and_failure_isolated():
    lua = pytest.importorskip("lupa.lua51").LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
        session = {job = 'j', record_replay = true}
        BRIDGE = '/unused/'
        state = {battle = 'b', friendly_ids = {'f1'}, enemy_ids = {'e1'},
            friendly = {f1 = {unit = {}}}, enemy = {e1 = {unit = {}, initial = true}},
            army_abilities = {}, seq = 123}
        bm = {battle = {}}
        function bm:get_current_phase_name() return 'Deployed' end
        function bm:get_player_army() return {} end
        function get(unit, key, default) return default end
        function mode_section() return {supplies = 42} end
        function unit_record(id) return {id = id, x = 3, z = 4, men = 2, secret = 'hidden'} end
        function enemy_observation(id, entry)
            entry.seen = true
            return {id = id}, unit_record(id)
        end
        function clean_error(e) return tostring(e) end
        logs, writes = 0, 0
        function log(e) logs = logs + 1 end
        json = {encode = function(frame) saved = frame; return 'frame' end}
        io = {open = function()
            return {write = function() writes = writes + 1; return true end,
                    close = function() end}
        end}
    """)
    source = SOURCE.read_text().split("local function record_replay(now, terminal)", 1)[1]
    fn = lua.execute(
        "local function record_replay(now, terminal)"
        + source.split("\nlocal function apply_army_ability", 1)[0]
        + "\nreturn record_replay"
    )
    fn(1000, False)
    g = lua.globals()
    assert g.writes == 1 and g.state.seq == 123
    assert g.state.enemy.e1.seen is None
    assert g.saved.friendly[1].secret is None
    assert g.saved.enemy[1].id == "e1"
    fn(1500, False)
    assert g.writes == 1
    fn(2000, False)
    assert g.writes == 2
    fn(2300, True)
    assert g.writes == 3 and g.saved.terminal is True
    lua.execute("io.open = function() error('disk failure') end")
    fn(3000, False)
    assert g.logs == 1
    lua.execute("session.record_replay = false")
    fn(4000, False)
    assert g.logs == 1
