"""The game-neutral Windows ownership helpers, with a second game's conflict rules."""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from gameai import windows, windows_game

WH3 = {"names": ["Warhammer3.exe"]}


@pytest.mark.parametrize(("path", "expected"), [
    (Path("/mnt/c/wh3-agent"), "C:/wh3-agent"),
    (Path("/mnt/d/Games/Total War"), "D:/Games/Total War"),
])
def test_windows_path_spells_drive_paths(path, expected):
    assert windows.windows_path(path) == expected


@pytest.mark.parametrize("path", [Path("/home/niv/x"), Path("/mnt"), Path("/mnt/drive/x")])
def test_windows_path_rejects_paths_outside_a_drive(path):
    with pytest.raises(ValueError):
        windows.windows_path(path)


def test_runtime_lock_is_exclusive_per_directory(tmp_path):
    with windows.RuntimeLock(tmp_path / "one"):
        with pytest.raises(RuntimeError, match="another controller"):
            with windows.RuntimeLock(tmp_path / "one"):
                pytest.fail("second controller acquired the lock")
        with windows.RuntimeLock(tmp_path / "two"):
            pass


def test_probe_timeout_is_bounded_and_reported(monkeypatch):
    run = Mock(side_effect=subprocess.TimeoutExpired("python", 8))
    monkeypatch.setattr(windows.subprocess, "run", run)
    assert windows.probe(["python", "--version"]) == {
        "status": "unavailable",
        "error": "TimeoutExpired",
    }
    assert run.call_args.kwargs["timeout"] == 8


@pytest.mark.parametrize(("process", "conflicts"), [
    ({"Name": "Warhammer3.exe"}, True),
    ({"Name": "warhammer3.exe", "ExecutablePath": "C:/Games/WH3/Warhammer3.exe"}, True),
    ({"Name": "launcher.exe", "ExecutablePath": "C:/Games/WH3/launcher/launcher.exe"}, True),
    ({"Name": "java.exe"}, False),
    ({"Name": "steam.exe", "ExecutablePath": "C:/Steam/steam.exe"}, False),
])
def test_rules_without_hosts_match_only_the_game_and_its_folder(process, conflicts):
    assert windows_game.is_game_process(process, Path("C:/Games/WH3"), WH3) == conflicts


def test_process_filter_names_every_rule_process(monkeypatch):
    query = Mock(return_value=b'[{"ProcessId": 7, "Name": "Warhammer3.exe"}]')
    monkeypatch.setattr(windows_game.subprocess, "check_output", query)
    assert windows_game.conflicting_games(Path("C:/Games/WH3"), WH3) == [
        {"ProcessId": 7, "Name": "Warhammer3.exe"}
    ]
    assert "Name='Warhammer3.exe'" in query.call_args.args[0][-1]


def test_owned_game_runs_the_supervisor_with_the_rules_and_command(tmp_path, monkeypatch):
    read_end, write_end = os.pipe()
    os.write(write_end, b'{"pid": 5, "command": ["x"]}\n')
    os.close(write_end)
    started = {}

    class FakePopen:
        def __init__(self, command, **kwargs):
            started["command"] = command
            self.stdout = os.fdopen(read_end, "rb")

        def communicate(self, *args, **kwargs):
            self.stdout.close()
            return "", ""

    monkeypatch.setattr(windows.subprocess, "Popen", FakePopen)
    runtime = Path("/mnt/c/wh3-agent")
    game = windows.OwnedGame(
        tmp_path / "game.log", runtime_dir=runtime, game_dir="C:/Games/WH3",
        command=["C:/Games/WH3/Warhammer3.exe", "mods.txt;"], rules=WH3, timeout=30,
    )
    with game:
        assert game.info == {"pid": 5, "command": ["x"]}
    command = started["command"]
    assert command[:2] == [str(windows.WINDOWS_PYTHON), "C:/wh3-agent/windows_game.py"]
    assert command[command.index("--rules") + 1] == json.dumps(WH3)
    assert command[command.index("--") + 1:] == ["C:/Games/WH3/Warhammer3.exe", "mods.txt;"]
    assert command[command.index("--log") + 1] == "C:/wh3-agent/" + game.windows_log.name
