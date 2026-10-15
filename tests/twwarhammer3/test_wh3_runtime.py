"""Pinned install checks, pack and mod-list deployment in twwarhammer3/engine/runtime.py."""
import pytest
from wh3_fixtures import fake_install

from twwarhammer3.engine import runtime, startup


@pytest.fixture
def install(tmp_path, monkeypatch):
    return fake_install(tmp_path, monkeypatch)


def test_prepare_runtime_builds_the_pack_and_mod_list(install):
    record = runtime.prepare_runtime()
    pack = install / "mnt/c/wh3-agent/mods/twwarhammer3.pack"
    assert pack.read_bytes().startswith(b"PFH5")
    assert record["pack"]["files"] == ["script\\battle\\mod\\twwarhammer3_battle.lua"]
    assert record["steam_build_id"] == "25823491"
    assert record["startup"]["enabled"]
    assert record["startup"][startup.PREFERENCE] == "false"
    assert record["startup"]["pack"]["sha256"] == record["startup"]["pack"]["expected_sha256"]
    assert (install / "steamapps/common/game/twwarhammer3_mods.txt").read_text() == (
        'add_working_directory "C:/wh3-agent/mods";\nmod "twwarhammer3.pack";\n'
    )
    assert (install / "mnt/c/wh3-agent/windows_game.py").is_file()
    assert (install / "mnt/c/wh3-agent/bridge").is_dir()


def test_prepare_runtime_refuses_an_unpinned_build(install):
    runtime.STEAM_MANIFEST.write_text('"buildid"\t\t"99"\n')
    with pytest.raises(RuntimeError, match="not the pinned"):
        runtime.prepare_runtime()
    assert not (install / "steamapps/common/game/twwarhammer3_mods.txt").exists()


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


def test_prepare_runtime_is_idempotent(install):
    first = runtime.prepare_runtime()
    path = runtime.GAME_DIR / "data" / startup.PACK_NAME
    preferences = runtime.user_dir() / "scripts/preferences.script.txt"
    before = (path.stat().st_mtime_ns, preferences.stat().st_mtime_ns)
    assert runtime.prepare_runtime() == first
    assert (path.stat().st_mtime_ns, preferences.stat().st_mtime_ns) == before


@pytest.mark.parametrize("probe_fails", [False, True])
def test_prepare_runtime_checks_game_is_stopped_before_writing(install, monkeypatch, probe_fails):
    def conflicts(*args):
        if probe_fails:
            raise OSError("cannot list processes")
        return [{"ProcessId": 99}]

    monkeypatch.setattr(runtime, "conflicting_games", conflicts)
    preferences = runtime.user_dir() / "scripts/preferences.script.txt"
    before = preferences.read_bytes()
    with pytest.raises((RuntimeError, OSError), match="running|cannot list"):
        runtime.prepare_runtime()
    assert preferences.read_bytes() == before
    assert not (runtime.GAME_DIR / "data" / startup.PACK_NAME).exists()
    assert not runtime.RUNTIME_DIR.exists()
    assert not (runtime.GAME_DIR / runtime.MOD_LIST).exists()
