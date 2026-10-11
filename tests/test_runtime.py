"""Ownership regressions; optional Windows probes use disposable Python trees."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from spire import runtime

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "windows_game.py"
SPEC = importlib.util.spec_from_file_location("windows_game", SCRIPT)
WINDOWS_GAME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WINDOWS_GAME)


def test_runtime_lock_uses_kernel_ownership_and_releases_on_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path)
    with pytest.raises(LookupError):
        with runtime.RuntimeLock():
            with pytest.raises(RuntimeError, match="another controller"):
                with runtime.RuntimeLock():
                    pytest.fail("second controller acquired the lock")
            raise LookupError("runner failed")
    # The lock file persists but the kernel no longer reports an owner.
    assert (tmp_path / "owner.lock").exists()
    with runtime.RuntimeLock():
        pass


def test_owned_game_close_is_idempotent_and_copies_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path)
    game = runtime.OwnedGame(tmp_path / "evidence" / "game.log")
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
    game = runtime.OwnedGame(tmp_path / "game.log")
    process = Mock()
    process.communicate.side_effect = [subprocess.TimeoutExpired("supervisor", 15), ("", "")]
    game.process = process
    game.close()
    process.kill.assert_called_once_with()
    assert process.communicate.call_count == 2
    assert game.process is None


def test_episode_logs_are_unique_even_in_same_controller(tmp_path):
    first = runtime.OwnedGame(tmp_path / "first.log")
    second = runtime.OwnedGame(tmp_path / "second.log")
    assert first.windows_log != second.windows_log


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_timeout_validation_precedes_game_mutations(tmp_path, timeout):
    with pytest.raises(ValueError, match="timeout"):
        runtime.OwnedGame(tmp_path / "game.log", timeout=timeout)
    with pytest.raises(ValueError, match="timeout"):
        runtime.prepare_runtime("127.0.0.1", 8765, timeout=timeout)


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
        game = runtime.OwnedGame(tmp_path / "game.log")
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
        game = runtime.OwnedGame(tmp_path / "game.log")
        game.process = process
        assert game._startup_message(timeout=1) == {"pid": 123, "command": []}
        process.wait(timeout=2)
        game.process = None


@pytest.mark.parametrize(
    ("process", "conflicts"),
    [
        ({"Name": "SlayTheSpire.exe"}, True),
        ({"Name": "java.exe", "ExecutablePath": "C:/games/SlayTheSpire/jre/bin/java.exe"}, True),
        ({"Name": "javaw.exe", "CommandLine": "java -jar C:/mods/ModTheSpire.jar"}, True),
        ({"Name": "java.exe", "CommandLine": 'java -jar "C:/games/desktop-1.0.jar"'}, True),
        ({"Name": "java.exe"}, True),
        (
            {
                "Name": "java.exe",
                "ExecutablePath": "C:/jdk/bin/java.exe",
                "CommandLine": "java -jar unrelated.jar",
            },
            False,
        ),
    ],
)
def test_existing_user_game_is_identified_without_killing_processes(process, conflicts):
    assert WINDOWS_GAME.is_game_process(process, Path("C:/games/SlayTheSpire")) == conflicts


def test_process_probe_preserves_powershell_failure(monkeypatch):
    failed = Mock(side_effect=subprocess.CalledProcessError(1, "powershell"))
    monkeypatch.setattr(WINDOWS_GAME.subprocess, "check_output", failed)
    with pytest.raises(subprocess.CalledProcessError):
        WINDOWS_GAME.conflicting_games(Path("C:/games/SlayTheSpire"))


@pytest.mark.skipif(
    os.environ.get("SPIRE_TEST_WINDOWS") != "1" or not runtime.WINDOWS_PYTHON.exists(),
    reason="set SPIRE_TEST_WINDOWS=1 on WSL to test actual Windows process ownership",
)
def test_windows_job_kills_owned_children_and_refuses_duplicate_supervisor(tmp_path):
    script = runtime.windows_path(SCRIPT)
    identity = runtime.windows_path(tmp_path / "disposable-game-identity")
    child_code = (
        "import subprocess,sys,time; "
        "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']); "
        "print(p.pid,flush=True); time.sleep(30)"
    )
    owner_code = (
        "import runpy,sys,json,subprocess,os;from pathlib import Path; "
        "m=runpy.run_path(sys.argv[1]); o=m['WindowsOwnership'](Path(sys.argv[2])); "
        "p=subprocess.Popen([sys.executable,'-u','-c',sys.argv[3]],"
        "stdout=subprocess.PIPE,text=True); "
        "print(json.dumps({'pid':os.getpid(),'child':p.pid,'grandchild':int(p.stdout.readline())}),"
        "flush=True); os.read(sys.stdin.fileno(),1)"
    )
    command = [str(runtime.WINDOWS_PYTHON), "-u", "-c", owner_code, script, identity, child_code]
    with subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as owner:
        game = runtime.OwnedGame(tmp_path / "probe.log")
        game.process = owner
        try:
            info = game._startup_message(timeout=10)
            duplicate = subprocess.run(
                command, input="", capture_output=True, text=True, timeout=10
            )
            assert duplicate.returncode != 0
            assert "another Windows supervisor" in duplicate.stderr
            # Abrupt supervisor death must also terminate the JVM-equivalent and relay-equivalent.
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
                    str(runtime.WINDOWS_PYTHON),
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
