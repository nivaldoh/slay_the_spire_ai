import argparse
import base64
import io
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from twwarhammer3.battle import imagery, visual_probe
from twwarhammer3.battle.setup import validate_declaration


def test_recorder_defaults_on_and_can_be_disabled_independently_of_stills():
    from twwarhammer3.__main__ import add_session_arguments, session_from

    parser = argparse.ArgumentParser()
    add_session_arguments(parser)
    assert session_from(parser.parse_args([]))["record_replay"] is True
    config = session_from(parser.parse_args(["--no-record-replay", "--stills"]))
    assert config["record_replay"] is False and config["stills"] is True


def test_capture_copy_keeps_failures_and_checks_battle_identity(tmp_path):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode"
    bridge.mkdir()
    episode.mkdir()
    (bridge / "still-b-opening.tga").write_bytes(b"captured")
    (bridge / "imagery-b.json").write_text(json.dumps({
        "job": "job", "battle": "b", "names": {"f1": "Lord"}, "stills": [
            {"file": "still-b-opening.tga", "trigger": "opening", "time_ms": 1000},
            {"file": "still-b-contact.tga", "trigger": "first_contact"},
            {"file": "../private.tga"},
            {"status": "capture_failed", "error": "camera unavailable"},
        ],
    }))
    assert imagery.copy_presentation(bridge, episode, job="other", battle="b")["status"] == (
        "identity_mismatch")
    assert not list(episode.iterdir())
    result = imagery.copy_presentation(bridge, episode, job="job", battle="b")
    assert result == {"status": "copied", "stills": 4, "names": 1}
    shots = json.loads((episode / "stills.json").read_text())
    assert shots[0]["time_ms"] == 1000
    assert (episode / shots[0]["file"]).read_bytes() == b"captured"
    assert all(shot["status"] == "capture_failed" for shot in shots[1:])
    assert all("file" not in shot for shot in shots[1:])
    assert json.loads((episode / "unit_names.json").read_text()) == {"f1": "Lord"}


def test_passive_capture_runs_outside_caller_and_joins_evidence(tmp_path, monkeypatch):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode"
    bridge.mkdir()
    episode.mkdir()
    (bridge / "observation.json").write_text(json.dumps({"job": "j", "battle": "b"}))
    (bridge / "imagery-b.json").write_text(json.dumps({"job": "j", "battle": "b", "stills": [
        {"trigger": "opening", "status": "capture_ready", "time_ms": 1000}], "names": {}}))
    entered, release = threading.Event(), threading.Event()

    def capture(*args, **kwargs):
        entered.set()
        assert release.wait(2)
        (bridge / "still-b-opening.png").write_bytes(b"image")
        return SimpleNamespace(stdout=json.dumps({"status": "captured",
            "file": "still-b-opening.png", "time_ms": 1100, "grab_wall_s": .04}))

    monkeypatch.setattr(imagery, "windows_path", str)
    monkeypatch.setattr(imagery.subprocess, "run", capture)
    with imagery.PassiveCapture(bridge, job="j", pid=123, enabled=True):
        assert entered.wait(2)
        # The caller remains free to submit orders while the screenshot is blocked.
        assert not release.is_set()
        release.set()
        result = imagery.copy_presentation(bridge, episode, job="j", battle="b")
    assert result["status"] == "copied"
    shot = json.loads((episode / "stills.json").read_text())[0]
    assert shot["time_ms"] == 1100 and shot["grab_wall_s"] == .04
    assert shot["status"] == "captured" and shot["policy_input"] is False


def test_passive_capture_refuses_another_foreground_process(tmp_path, monkeypatch):
    grab = pytest.importorskip("PIL.ImageGrab")
    from twwarhammer3.engine import windows_capture

    user = Mock()
    user.GetForegroundWindow.return_value = 42
    user.GetWindowThreadProcessId.side_effect = lambda _, owner: setattr(owner._obj, "value", 999)
    monkeypatch.setattr(windows_capture.ctypes, "WinDLL", lambda *a, **k: user, raising=False)
    screenshot = Mock()
    monkeypatch.setattr(grab, "grab", screenshot)
    with pytest.raises(RuntimeError, match="not foreground"):
        windows_capture.capture(123, tmp_path / "shot.png", tmp_path / "observation.json", "j", "b")
    screenshot.assert_not_called()
    assert not (tmp_path / "shot.png").exists()


def test_stills_resize_preserve_provenance_and_report_failures(tmp_path):
    image = pytest.importorskip("PIL.Image")
    source = tmp_path / "opening.tga"
    image.new("RGB", (2000, 1500), "blue").save(source)
    entries = [{"file": "opening.tga", "time_ms": 1000, "visibility": "unverified"},
               {"file": "missing.tga", "time_ms": 2000}, {"file": "../private.png"},
               {"status": "capture_failed", "error": "unsupported API"}]
    output = imagery.stills(tmp_path, entries, embed=True)
    assert output[0]["original_size"] == [2000, 1500]
    assert max(output[0]["size"]) <= 1600 and output[0]["size"][1] <= 1000
    assert output[0]["time_ms"] == 1000 and output[0]["policy_input"] is False
    assert output[0]["visibility"] == "unverified"
    data = base64.b64decode(output[0]["image"].split(",")[1])
    with image.open(io.BytesIO(data)) as decoded:
        assert decoded.format == "WEBP"
    assert output[1]["status"] == output[2]["status"] == "error"
    assert output[3]["status"] == "capture_failed"
    assert "image" not in imagery.stills(tmp_path, entries, embed=False)[0]


def test_probe_commands_are_scripted_and_keep_normal_game_timing(tmp_path):
    for case in ("off", "on", "imagery"):
        command = visual_probe.command(tmp_path / case, case)
        assert command[command.index("--policy") + 1] == "rush_nearest"
        assert "--pause" not in command and "--speed" not in command
        assert ("--record-replay" in command) == (case != "off")


def test_detailed_still_fits_the_nine_trial_image_budget(tmp_path):
    image = pytest.importorskip("PIL.Image")
    source = tmp_path / "detail.png"
    image.effect_noise((2000, 1500), 100).convert("RGB").save(source)
    result = imagery.webp(source)
    assert result["bytes"] <= imagery.MAX_STILL_BYTES
    # Four stills per controller, nine trials, base64 overhead and 0.5 MB replay each.
    assert 9 * (4 * imagery.MAX_STILL_BYTES + 500_000) * 4 / 3 < 20 * 1024 * 1024


def test_probe_rejects_existing_output_before_touching_runtime(tmp_path):
    with pytest.raises(ValueError, match="new directory"):
        visual_probe.run(tmp_path, "imagery")


def test_probe_timeouts_satisfy_declared_benchmark_requirements(tmp_path):
    scenarios = json.loads(Path("configs/twwarhammer3/scenarios.json").read_text())
    for case in ("off", "on", "imagery"):
        command = visual_probe.command(tmp_path / case, case)
        scenario = scenarios[command[command.index("--scenario") + 1]]
        validate_declaration(scenario, {
            "menu": True, "start_timeout": 900, "episodes": 1,
            "episode_timeout": float(command[command.index("--episode-timeout") + 1]),
            "run_timeout": float(command[command.index("--run-timeout") + 1]),
        }, {"preferences": {"battle_realism_mode": "false"}})


def test_imagery_probe_is_valid_lua51():
    lua = pytest.importorskip("lupa.lua51").LuaRuntime()
    compile_lua = lua.eval("function(source) return assert(loadstring(source)) end")
    assert compile_lua(visual_probe.LUA)


def test_lua_capture_triggers_use_public_cluster_and_keep_camera_failures():
    lua = pytest.importorskip("lupa.lua51").LuaRuntime()
    lua.execute('''
        clock_ms, captures, callbacks = 1000, 0, {}
        function v(x, y, z)
            return {get_x = function() return x end, get_y = function() return y end,
                    get_z = function() return z end}
        end
        camera = {position = function() return position end, target = function() return target end,
            change_height_range = function() end,
            move_to = function(_, p, t) position, target = p, t end}
        bm = {battle = {get_terrain_height = function() return 20 end,
                       time_elapsed_ms = function() return clock_ms end},
              camera = function() return camera end,
              repeat_real_callback = function(_, fn, interval, name) callbacks[name] = fn end,
              remove_real_callback = function(_, name) callbacks[name] = nil end}
        common = {take_screenshot = function() error('Native capture must not run') end}
        twwarhammer3_json = {encode = function(record) saved = record; return 'json' end}
        io = {open = function() return {write = function() end, close = function() end} end}
        os.remove = function() end
        os.rename = function() return true end
        function sample(time, units, terminal)
            clock_ms = time
            twwarhammer3_imagery({job = 'j', battle = 'b', time_ms = time,
                friendly = units, enemy = {}, terminal = terminal}, {f1 = 'Lord'})
        end
    ''')
    source = Path("src/twwarhammer3/mod/script/_lib/mod/twwarhammer3_imagery.lua")
    lua.execute(source.read_text())
    lua.execute("sample(1000, {{id='f1', x=0, z=0, men=1, state={}}})")
    g = lua.globals()
    assert g.saved.stills[1].status == "pending" and g.captures == 0
    lua.execute("clock_ms = 1500; callbacks.wh3_still_opening()")
    assert g.saved.stills[1].time_ms == 1500 and g.captures == 0
    assert g.saved.stills[1].status == "capture_ready"
    lua.execute('''sample(35000, {
        {x=0,z=0,men=1,state={'melee'}}, {x=10,z=10,men=1,state={'melee'}},
        {x=20,z=20,men=1,state={'melee'}}, {x=1000,z=1000,men=1,state={'melee'}}})''')
    assert g.saved.stills[2].trigger == "first_contact"
    assert g.target.get_x() == g.target.get_z() == 10
    lua.execute("callbacks.wh3_still_first_contact()")
    lua.execute("sample(36000, {{x=0,z=0,men=1,state={'routing'}}})")
    assert g.saved.stills[3].status == "throttled" and g.captures == 0
    lua.execute('''
        camera.move_to = function() error('camera unavailable') end
        sample(37000, {{x=0,z=0,men=1,state={}}}, true)
        sample(38000, {{x=0,z=0,men=1,state={}}}, true)
    ''')
    assert len(g.saved.stills) == 4
    assert g.saved.stills[4].status == "capture_failed"
    assert "camera unavailable" in g.saved.stills[4].error


def test_lua_presentation_never_queries_hidden_enemy_positions_or_policy_memory():
    lua = pytest.importorskip("lupa.lua51").LuaRuntime()
    lua.execute('''
        session = {job='j', stills=true}
        queried = {}
        function unit(id, visible)
            return {id=id, visible=visible, position=function()
                queried[id] = true
                return {get_x=function() return 1 end, get_z=function() return 2 end}
            end}
        end
        state = {battle='b', seq=99, friendly_ids={'f1'}, enemy_ids={'e1','e2','e3'},
            friendly={f1={unit=unit('f1',true)}},
            enemy={e1={unit=unit('e1',false),initial=true},
                   e2={unit=unit('e2',true)}, e3={unit=unit('e3',false)}}}
        function get(object, name, default)
            if name == 'unique_ui_id' then return object.id end
            if object[name] then return object[name]() end
            return default
        end
        function visible_to_player(unit) return unit.visible end
        function plain(text) return text end
        function clean_error(text) return text end
        function log(text) error(text) end
        common={get_context_value=function(_, id)
            if id=='e3' then error('unseen reinforcement') end
            if id=='e1' then error('name unavailable') end
            return id .. ' readable'
        end}
        function twwarhammer3_imagery(frame, names) saved, saved_names = frame, names end
    ''')
    source = Path("src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua").read_text()
    body = source.split("local function record_imagery(now, terminal)", 1)[1].split(
        "local function apply_army_ability", 1)[0]
    sample = lua.execute("local function record_imagery(now, terminal)" + body +
                         "\nreturn record_imagery")
    sample(1000, False)
    g = lua.globals()
    assert g.state.seq == 99 and g.state.enemy.e2.seen is None
    assert g.queried.f1 and g.queried.e2
    assert g.queried.e1 is None and g.queried.e3 is None
    assert len(g.saved.enemy) == 1 and g.saved.enemy[1].id == "e2"
    assert g.saved_names.f1 == "f1 readable" and g.saved_names.e1 is None
