"""The game-neutral Windows ownership helpers and supervisor, with WH3's conflict rules.

The tests that start Windows Python (the job object, a native-Windows controller) run only
with GAMEAI_TEST_WINDOWS=1 on WSL.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from gameai import windows, windows_game

WH3 = {"names": ["Warhammer3.exe"]}
SCRIPT = Path(windows_game.__file__)


def owned_game(tmp_path, log="game.log"):
    return windows.OwnedGame(
        tmp_path / log, runtime_dir=tmp_path, game_dir="C:/Games/WH3",
        command=["C:/Games/WH3/Warhammer3.exe"], rules=WH3,
    )


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


def test_owned_game_close_is_idempotent_and_copies_evidence(tmp_path):
    game = owned_game(tmp_path, "evidence/game.log")
    game.windows_log.write_text("game evidence")
    process = Mock()
    process.communicate.return_value = ("", "supervisor diagnostics")
    game.process = process
    game.close()
    game.close()
    process.communicate.assert_called_once_with("stop\n", timeout=15)
    assert game.process is None
    assert game.supervisor_stderr == "supervisor diagnostics"
    assert game.log_path.read_text() == "game evidence"


def test_owned_game_force_stops_only_its_supervisor(tmp_path):
    game = owned_game(tmp_path)
    process = Mock()
    process.communicate.side_effect = [subprocess.TimeoutExpired("supervisor", 15), ("", "")]
    game.process = process
    game.close()
    process.kill.assert_called_once_with()
    assert process.communicate.call_count == 2
    assert game.process is None


def test_episode_logs_are_unique_even_in_same_controller(tmp_path):
    first = owned_game(tmp_path, "first.log")
    second = owned_game(tmp_path, "second.log")
    assert first.windows_log != second.windows_log


@pytest.mark.parametrize("output", ["", '{"pid":', "x" * 70000])
def test_startup_handshake_does_not_block_on_missing_or_partial_json(tmp_path, output):
    with subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys,time;sys.stdout.write(sys.argv[1]);sys.stdout.flush();time.sleep(10)",
            output,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        game = owned_game(tmp_path)
        game.process = process
        try:
            with pytest.raises((TimeoutError, RuntimeError)):
                game._startup_message(timeout=0.1)
        finally:
            process.kill()
            process.communicate(timeout=2)
            game.process = None


def test_startup_handshake_reads_complete_json(tmp_path):
    with subprocess.Popen(
        [sys.executable, "-c", 'print(\'{"pid": 123, "command": []}\')'],
        stdout=subprocess.PIPE,
        text=True,
    ) as process:
        game = owned_game(tmp_path)
        game.process = process
        assert game._startup_message(timeout=1) == {"pid": 123, "command": []}
        process.wait(timeout=2)
        game.process = None


def test_process_probe_preserves_powershell_failure(monkeypatch):
    failed = Mock(side_effect=subprocess.CalledProcessError(1, "powershell"))
    monkeypatch.setattr(windows_game.subprocess, "check_output", failed)
    with pytest.raises(subprocess.CalledProcessError):
        windows_game.conflicting_games(Path("C:/Games/WH3"), WH3)


def start_supervisor(tmp_path, timeout):
    """Run windows_game.main with a fake game; the job object and process query need Windows."""
    game = tmp_path / "game/game.exe"
    game.parent.mkdir(parents=True)
    game.write_text("#!/bin/sh\nexec sleep 30\n")
    game.chmod(0o755)
    code = (
        "import importlib.util,sys; "
        "spec=importlib.util.spec_from_file_location('g',sys.argv[1]); "
        "g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g); "
        "g.join_kill_on_close_job=lambda:None; g.conflicting_games=lambda game_dir,rules:[]; "
        "sys.argv=sys.argv[1:]; sys.exit(g.main())"
    )
    arguments = ["--game-dir", str(tmp_path / "game"), "--log", str(tmp_path / "game.log"),
                 "--timeout", str(timeout), "--", str(game), "--windowed"]
    return subprocess.Popen(
        [sys.executable, "-c", code, str(SCRIPT), *arguments],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )


@pytest.mark.parametrize("stop", ["controller_eof", "hard_timeout"])
def test_supervisor_stops_the_game_on_controller_eof_or_hard_timeout(tmp_path, stop):
    with start_supervisor(tmp_path, 0.5 if stop == "hard_timeout" else 30) as supervisor:
        try:
            game = json.loads(supervisor.stdout.readline())["pid"]
            if stop == "controller_eof":
                supervisor.stdin.close()
            assert supervisor.wait(timeout=10) == 0
            assert json.loads(supervisor.stdout.readline())["exit_code"] != 0
            with pytest.raises(ProcessLookupError):
                os.kill(game, 0)
        finally:
            supervisor.kill()


ON_WINDOWS = pytest.mark.skipif(
    os.environ.get("GAMEAI_TEST_WINDOWS") != "1" or not windows.WINDOWS_PYTHON.exists(),
    reason="set GAMEAI_TEST_WINDOWS=1 on WSL to test actual Windows process ownership",
)


@ON_WINDOWS
def test_windows_job_kills_owned_children_when_the_supervisor_dies(tmp_path):
    script = subprocess.check_output(["wslpath", "-w", str(SCRIPT)], text=True).strip()
    child_code = (
        "import subprocess,sys,time; "
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']); "
        "print(p.pid,flush=True); time.sleep(30)"
    )
    owner_code = (
        "import runpy,sys,json,subprocess,os;from pathlib import Path; "
        "m=runpy.run_path(sys.argv[1]); m['join_kill_on_close_job'](); "
        "p=subprocess.Popen([sys.executable,'-u','-c',sys.argv[2]],"
        "stdout=subprocess.PIPE,text=True); "
        "print(json.dumps({'pid':os.getpid(),'child':p.pid,'grandchild':int(p.stdout.readline())}),"
        "flush=True); os.read(sys.stdin.fileno(),1)"
    )
    command = [str(windows.WINDOWS_PYTHON), "-u", "-c", owner_code, script, child_code]
    with subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as owner:
        game = owned_game(tmp_path, "probe.log")
        game.process = owner
        try:
            info = game._startup_message(timeout=10)
            # Abrupt supervisor death must also terminate the game and its own children.
            owner.kill()
            owner.communicate(timeout=5)
            probe = (
                "import ctypes,sys,json;from ctypes import wintypes; "
                "k=ctypes.WinDLL('kernel32',use_last_error=True); "
                "k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]; "
                "k.OpenProcess.restype=wintypes.HANDLE; "
                "k.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]; "
                "k.CloseHandle.argtypes=[wintypes.HANDLE]; results=[]; "
                "exec('for pid in sys.argv[1:]:\\n h=k.OpenProcess(0x100000,False,int(pid))"
                "\\n results.append(not h or k.WaitForSingleObject(h,5000)==0)"
                "\\n if h:k.CloseHandle(h)'); print(json.dumps(results))"
            )
            result = subprocess.check_output(
                [
                    str(windows.WINDOWS_PYTHON),
                    "-c",
                    probe,
                    str(info["child"]),
                    str(info["grandchild"]),
                ],
                text=True,
                timeout=15,
            )
            assert json.loads(result) == [True, True]
        finally:
            if owner.poll() is None:
                owner.kill()
                owner.communicate(timeout=5)
            game.process = None


# Runs in native Windows Python (a cloud worker's controller) and prints what it saw.
NATIVE_CONTROLLER = r"""
import ctypes, json, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from gameai import windows

kernel = ctypes.WinDLL("kernel32")
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
report = {
    "python": str(windows.WINDOWS_PYTHON),
    "paths": [windows.windows_path(Path(p)) for p in ("C:/wh3-agent", r"D:\Games\Total War")],
}
with tempfile.TemporaryDirectory() as root:
    root = Path(root)
    with windows.RuntimeLock(root):
        try:
            with windows.RuntimeLock(root):
                report["second_lock"] = "acquired"
        except RuntimeError:
            report["second_lock"] = "refused"
    with windows.RuntimeLock(root):
        report["relocked"] = True
    shutil.copy2(Path(windows.__file__).with_name("windows_game.py"), root)
    game = windows.OwnedGame(
        root / "out/game.log", runtime_dir=root, game_dir=str(root),
        command=[sys.executable, "-c", "import time; time.sleep(60)"],
        rules={"names": ["no-such-game.exe"]}, timeout=120,
    )
    with game:
        pid = game.info["pid"]
    handle = kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
    report["child_stopped"] = not handle or kernel.WaitForSingleObject(handle, 5000) == 0
    report["log_copied"] = (root / "out/game.log").is_file()
    with subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                          stdout=subprocess.PIPE, text=True) as silent:
        game.process = silent
        start = time.monotonic()
        try:
            game._startup_message(timeout=1)
        except TimeoutError:
            report["deadline_s"] = time.monotonic() - start
        silent.kill()
        game.process = None
print(json.dumps(report))
"""


@ON_WINDOWS
def test_native_windows_controller_locks_and_owns_a_child_without_wsl_tools():
    # Windows Python reaches this checkout's source through its UNC spelling.
    source = subprocess.check_output(
        ["wslpath", "-w", str(Path(windows.__file__).parents[1])], text=True
    ).strip()
    output = subprocess.check_output(
        [str(windows.WINDOWS_PYTHON), "-B", "-c",
         "import sys; sys.path.insert(0, sys.argv[1])\n" + NATIVE_CONTROLLER, source],
        text=True, timeout=120,
    )
    report = json.loads(output)
    assert 1 <= report.pop("deadline_s") < 5
    assert report == {
        "python": "C:\\Python313\\python.exe",
        "paths": ["C:/wh3-agent", "D:/Games/Total War"],
        "second_lock": "refused",
        "relocked": True,
        "child_stopped": True,
        "log_copied": True,
    }
