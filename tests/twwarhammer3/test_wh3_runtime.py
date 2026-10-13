import pytest

from twwarhammer3.engine import doctor, runtime


@pytest.fixture
def setup(tmp_path, monkeypatch):
    game = tmp_path / "steamapps/common/game"
    game.mkdir(parents=True)
    (game / "Warhammer3.exe").write_bytes(b"not the game")
    (tmp_path / "steamapps/appmanifest_1142710.acf").write_text('"buildid"\t\t"25823491"\n')
    source = tmp_path / "mod/script/battle/mod"
    source.mkdir(parents=True)
    (source / "twwarhammer3_battle.lua").write_text("out('loaded')")
    monkeypatch.setattr(runtime, "GAME_DIR", game)
    monkeypatch.setattr(runtime, "STEAM_MANIFEST", tmp_path / "steamapps/appmanifest_1142710.acf")
    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path / "mnt/c/wh3-agent")
    monkeypatch.setattr(runtime, "BRIDGE_DIR", tmp_path / "mnt/c/wh3-agent/bridge")
    monkeypatch.setattr(runtime, "MOD_SOURCE", tmp_path / "mod")
    monkeypatch.setattr(runtime.windows, "windows_path", lambda path: "C:/wh3-agent/mods")
    return tmp_path


def test_prepare_runtime_builds_the_pack_and_mod_list(setup):
    record = runtime.prepare_runtime()
    pack = setup / "mnt/c/wh3-agent/mods/twwarhammer3.pack"
    assert pack.read_bytes().startswith(b"PFH5")
    assert record["pack"]["files"] == ["script\\battle\\mod\\twwarhammer3_battle.lua"]
    assert record["steam_build_id"] == "25823491"
    assert (setup / "steamapps/common/game/twwarhammer3_mods.txt").read_text() == (
        'add_working_directory "C:/wh3-agent/mods";\nmod "twwarhammer3.pack";\n'
    )
    assert (setup / "mnt/c/wh3-agent/windows_game.py").is_file()
    assert (setup / "mnt/c/wh3-agent/bridge").is_dir()


def test_prepare_runtime_refuses_an_unpinned_build(setup):
    runtime.STEAM_MANIFEST.write_text('"buildid"\t\t"99"\n')
    with pytest.raises(RuntimeError, match="not the pinned"):
        runtime.prepare_runtime()
    assert not (setup / "steamapps/common/game/twwarhammer3_mods.txt").exists()


def test_preferences_keep_only_gameplay_relevant_keys(tmp_path):
    path = tmp_path / "preferences.script.txt"
    path.write_text(
        'gfx_fullscreen true; # gfx_fullscreen <bool> #\nx_res 1920;\n'
        'gfx_unit_size 2; # 0 - small #\nbattle_ai_stats_modifier 1.1; # float #\n'
        'gfx_gpu "NVIDIA"; # private #\n'
    )
    assert runtime.preferences(path) == {
        "gfx_fullscreen": "true", "x_res": "1920", "gfx_unit_size": "2",
        "battle_ai_stats_modifier": "1.1",
    }


def test_owned_game_runs_the_executable_with_the_mod_list(tmp_path):
    game = runtime.OwnedGame(tmp_path / "game.log", timeout=10)
    assert game.command == [runtime.WINDOWS_GAME_DIR + r"\Warhammer3.exe", "twwarhammer3_mods.txt;"]
    assert game.rules == {"names": ["Warhammer3.exe"]}


def test_doctor_reports_blockers_without_launching(setup, monkeypatch):
    monkeypatch.setattr(doctor, "probe", lambda command: {"status": "ok", "output": "3.13"})
    monkeypatch.setattr(doctor, "conflicting_games", lambda game_dir, rules: [{"ProcessId": 9}])
    monkeypatch.setattr(runtime, "preferences", lambda: {"gfx_unit_size": "2"})
    report = doctor.collect_diagnostics()
    text = "\n".join(report["blockers"])
    assert "pinned hash" in text and "PIDs 9" in text
    assert report["mod"]["files"] == ["script\\battle\\mod\\twwarhammer3_battle.lua"]
    assert "gfx_unit_size=2" in doctor.render_diagnostics(report)
    monkeypatch.setattr(doctor, "conflicting_games", lambda game_dir, rules: [])
    monkeypatch.setitem(runtime.PINS, "Warhammer3.exe", report["game"]["sha256"])
    assert doctor.collect_diagnostics()["status"] == "ready"
