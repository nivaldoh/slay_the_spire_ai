"""Spire's runtime: the WSL endpoint, deployment, the lock, relay stderr and conflicts.

The game-neutral supervisor and ``OwnedGame`` are tested in tests/gameai/test_windows.py.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from gameai import windows_game
from gameai.provenance import sha256
from spire.engine import runtime


def interface(address="172.18.34.183"):
    return {
        "ifname": "eth0", "flags": ["UP"],
        "addr_info": [{"family": "inet", "scope": "global", "local": address}],
    }


def test_wsl_endpoint_discovers_current_private_eth0_address_each_time(monkeypatch):
    query = Mock(side_effect=[
        json.dumps([interface("172.18.34.183")]),
        json.dumps([interface("10.1.2.3")]),
    ])
    monkeypatch.setattr(runtime.subprocess, "check_output", query)
    assert runtime.wsl_bridge_host() == "172.18.34.183"
    assert runtime.wsl_bridge_host() == "10.1.2.3"
    assert query.call_count == 2
    query.assert_called_with(
        ["ip", "-4", "-j", "address", "show", "dev", "eth0"],
        text=True, stderr=subprocess.PIPE, timeout=5,
    )


@pytest.mark.parametrize("data", [
    [], {}, [None], [interface(), interface()],
    [{**interface(), "flags": []}],
    [{**interface(), "addr_info": []}],
    [{**interface(), "addr_info": interface()["addr_info"] * 2}],
    [{**interface(), "addr_info": [{"family": "inet6", "scope": "global", "local": "::1"}]}],
    [{**interface(), "addr_info": [{"family": "inet", "scope": "host", "local": "127.0.0.1"}]}],
    [interface(None)], [interface(1)], [interface("invalid")], [interface("0.0.0.0")],
    [interface("127.0.0.1")], [interface("169.254.1.2")], [interface("224.0.0.1")],
    [interface("8.8.8.8")], [interface("::1")],
])
def test_wsl_endpoint_rejects_missing_ambiguous_or_unsupported_address(monkeypatch, data):
    monkeypatch.setattr(
        runtime.subprocess, "check_output", lambda *args, **kwargs: json.dumps(data)
    )
    with pytest.raises(RuntimeError, match="usable private IPv4"):
        runtime.wsl_bridge_host()


@pytest.mark.parametrize("problem", [
    FileNotFoundError("ip"), subprocess.TimeoutExpired("ip", 5),
    subprocess.CalledProcessError(1, "ip"),
])
def test_wsl_endpoint_query_failure_has_no_fallback(monkeypatch, problem):
    query = Mock(side_effect=problem)
    monkeypatch.setattr(runtime.subprocess, "check_output", query)
    with pytest.raises(RuntimeError, match="usable private IPv4"):
        runtime.wsl_bridge_host()
    query.assert_called_once()


def test_wsl_endpoint_rejects_malformed_json(monkeypatch):
    monkeypatch.setattr(runtime.subprocess, "check_output", lambda *args, **kwargs: "not json")
    with pytest.raises(RuntimeError, match="usable private IPv4"):
        runtime.wsl_bridge_host()


def test_deployment_config_and_record_use_exact_listener_endpoint(tmp_path, monkeypatch):
    game = tmp_path / "game"
    game.mkdir()
    monkeypatch.setattr(runtime, "GAME_DIR", game)
    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path / "runtime")
    monkeypatch.setattr(runtime, "PINS", {})
    config = tmp_path / "communication/config.properties"
    monkeypatch.setattr(runtime, "communication_config", lambda: config)
    deployment = runtime.prepare_runtime("172.18.34.183", 19876, timeout=45)
    assert deployment["relay"] == {"host": "172.18.34.183", "port": 19876, "timeout": 45}
    assert "--host 172.18.34.183 --port 19876 --timeout 45\n" in config.read_text()
    assert "127.0.0.1" not in config.read_text() and "0.0.0.0" not in config.read_text()


def pin_jars(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "GAME_DIR", tmp_path / "game")
    monkeypatch.setattr(runtime, "WORKSHOP_DIR", tmp_path / "workshop")
    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path / "runtime")
    monkeypatch.setattr(runtime, "communication_config", lambda: tmp_path / "config.properties")
    pins = {}
    for index, name in enumerate(["ModTheSpire.jar", "BaseMod.jar"]):
        jar = tmp_path / "workshop" / str(index) / name
        jar.parent.mkdir(parents=True)
        jar.write_bytes(name.encode())
        pins[name] = (str(index), sha256(jar))
    monkeypatch.setattr(runtime, "PINS", pins)
    (tmp_path / "game").mkdir()


def test_deployment_copies_pinned_jars_where_the_launch_uses_them(tmp_path, monkeypatch):
    pin_jars(tmp_path, monkeypatch)
    deployment = runtime.prepare_runtime("172.18.34.183", 19876)
    assert deployment["mods"] == {name: pin for name, (_, pin) in runtime.PINS.items()}
    assert (tmp_path / "runtime/mods/ModTheSpire.jar").read_bytes() == b"ModTheSpire.jar"
    assert (tmp_path / "runtime/mods/BaseMod.jar").read_bytes() == b"BaseMod.jar"
    assert (tmp_path / "game/mods/BaseMod.jar").read_bytes() == b"BaseMod.jar"
    # The loader runs from the runtime folder, never from the game's mods.
    assert not (tmp_path / "game/mods/ModTheSpire.jar").exists()


@pytest.mark.parametrize("changed", ["workshop/1/BaseMod.jar", "game/mods/BaseMod.jar"])
def test_deployment_refuses_a_changed_jar_without_overwriting(tmp_path, monkeypatch, changed):
    pin_jars(tmp_path, monkeypatch)
    (tmp_path / changed).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / changed).write_bytes(b"Workshop update")
    with pytest.raises(RuntimeError, match="BaseMod.jar"):
        runtime.prepare_runtime("172.18.34.183", 19876)
    assert (tmp_path / changed).read_bytes() == b"Workshop update"
    assert not (tmp_path / "config.properties").exists()


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


@pytest.mark.parametrize("truncate", [False, True])
def test_owned_game_preserves_only_current_relay_stderr(tmp_path, truncate):
    game = runtime.OwnedGame(tmp_path / "episode" / "game.log")
    game.relay_stderr = tmp_path / "communication_mod_errors.log"
    old = b"an earlier episode disconnected\n"
    game.relay_stderr.write_bytes(old)
    game._relay_stderr_offset = len(old)
    error = b"WinError 10061\n"
    game.relay_stderr.write_bytes(error if truncate else old + error)
    process = Mock()
    process.communicate.return_value = ("", "supervisor exited\n")
    game.process = process
    game.close()
    assert (game.log_path.parent / "communication-mod.stderr.log").read_bytes() == error
    assert (game.log_path.parent / "supervisor.stderr.log").read_text() == "supervisor exited\n"
    assert game.relay_stderr.read_bytes() == (error if truncate else old + error)


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
    game_dir = Path("C:/games/SlayTheSpire")
    assert windows_game.is_game_process(process, game_dir, runtime.CONFLICTS) == conflicts


def test_communication_config_queries_windows_once_per_process(monkeypatch):
    calls = []

    def fake_output(command, **kwargs):
        calls.append((command, kwargs.get("timeout")))
        if command[0] == "wslpath":
            return "/mnt/c/Users/test/AppData/Local\n"
        return "C:\\Users\\test\\AppData\\Local\n"

    runtime.communication_config.cache_clear()
    monkeypatch.setattr(runtime.subprocess, "check_output", fake_output)
    try:
        first = runtime.communication_config()
        assert runtime.communication_config() == first
    finally:
        runtime.communication_config.cache_clear()
    assert first == Path(
        "/mnt/c/Users/test/AppData/Local/ModTheSpire/CommunicationMod/config.properties"
    )
    assert [timeout for command, timeout in calls if command[0] != "wslpath"] == [30]
