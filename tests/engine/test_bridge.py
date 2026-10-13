"""Transport contracts, including the actual standalone relay subprocess."""

from __future__ import annotations

import socket
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from gameai.provenance import REPO_ROOT
from spire.engine.bridge import (
    BridgeDisconnected,
    BridgeError,
    BridgeProtocolError,
    BridgeServer,
    BridgeTimeout,
)

RELAY = REPO_ROOT / "src/spire/engine/windows_relay.py"


def test_fragmented_and_coalesced_states_keep_framing_and_unicode():
    with BridgeServer(timeout=1) as bridge, socket.create_connection(bridge.address) as relay:
        assert bridge.address[0] == "127.0.0.1"
        relay.sendall(b'{"x":')
        relay.sendall(' "é"}\r\n{"next": true}\n'.encode())
        assert bridge.receive() == {"x": "é"}
        assert bridge.receive() == {"next": True}
        bridge.send("PLAY 1 0")
        assert relay.recv(1024) == b"PLAY 1 0\n"


@pytest.mark.parametrize(
    ("line", "message"),
    [
        (b"not json\n", "UTF-8 JSON"),
        (b"\xff\n", "UTF-8 JSON"),
        (b"[]\n", "JSON object"),
        (b"null\n", "JSON object"),
        (b"\n", "UTF-8 JSON"),
        (b'{"x":123456}\n', "byte limit"),
    ],
)
def test_invalid_states_end_session(line, message):
    with BridgeServer(timeout=1, max_line_bytes=12) as bridge:
        with socket.create_connection(bridge.address) as relay:
            relay.sendall(line)
            with pytest.raises(BridgeProtocolError, match=message):
                bridge.receive()
        with pytest.raises(BridgeDisconnected):
            bridge.receive()
        with pytest.raises(BridgeDisconnected):
            bridge.send("STATE")


def test_line_byte_limit_includes_newline():
    with BridgeServer(max_line_bytes=3) as bridge:
        with socket.create_connection(bridge.address) as relay:
            relay.sendall(b"{}\n")
            assert bridge.receive() == {}


@pytest.mark.parametrize("command", ["", " ", "STATE\nEND", "STATE\r", "STATE\0", None])
def test_commands_cannot_inject_additional_protocol_lines(command):
    with BridgeServer() as bridge:
        with pytest.raises(BridgeProtocolError):
            bridge.send(command)


def test_oversized_command_invalidates_session():
    with BridgeServer(max_line_bytes=3) as bridge:
        with pytest.raises(BridgeProtocolError, match="byte limit"):
            bridge.send("STATE")


@pytest.mark.parametrize("partial", [b"", b'{"unfinished":'])
def test_disconnect_never_returns_a_partial_state(partial):
    with BridgeServer(timeout=1) as bridge:
        with socket.create_connection(bridge.address) as relay:
            bridge.accept()
            relay.sendall(partial)
        expected = BridgeProtocolError if partial else BridgeDisconnected
        with pytest.raises(expected):
            bridge.receive()
        # The listening socket closes after the first accept. A stale session
        # cannot accidentally attach a replacement game process.
        with pytest.raises(OSError):
            socket.create_connection(bridge.address, timeout=0.1)


def test_connection_and_partial_state_timeouts_are_terminal():
    with BridgeServer(timeout=0.03) as bridge:
        with pytest.raises(BridgeTimeout, match="connection"):
            bridge.accept()
        with pytest.raises(BridgeDisconnected):
            bridge.accept()
    with BridgeServer(timeout=0.03) as bridge:
        with socket.create_connection(bridge.address) as relay:
            relay.sendall(b'{"x":')
            with pytest.raises(BridgeTimeout, match="complete game state"):
                bridge.receive()
            with pytest.raises(BridgeDisconnected):
                bridge.receive()


def test_context_cannot_be_reused_and_closing_releases_port():
    bridge = BridgeServer()
    with pytest.raises(BridgeError, match="not started"):
        _ = bridge.address
    with bridge:
        address = bridge.address
    bridge.close()
    with pytest.raises(BridgeError, match="cannot be reused"):
        with bridge:
            pass
    with socket.socket() as replacement:
        replacement.bind(address)


def test_server_can_rebind_same_port_after_server_initiated_close():
    port = 0
    for index in range(3):
        with BridgeServer(port=port, timeout=1) as bridge:
            port = bridge.address[1]
            relay = socket.create_connection(bridge.address)
            relay.settimeout(1)
            relay.sendall(f'{{"episode":{index}}}\n'.encode())
            assert bridge.receive() == {"episode": index}
            # The server closes first, so its address can enter TIME_WAIT.
        try:
            assert relay.recv(1) == b""
        finally:
            relay.close()


def test_address_reuse_does_not_allow_two_live_listeners():
    with BridgeServer(timeout=1) as original:
        with pytest.raises(BridgeError, match="could not listen"):
            with BridgeServer(port=original.address[1], timeout=1):
                pytest.fail("a second listener must not take ownership")
        with socket.create_connection(original.address) as relay:
            relay.sendall(b'{"original":true}\n')
            assert original.receive() == {"original": True}


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_timeout_must_be_bounded(timeout):
    with pytest.raises(ValueError):
        BridgeServer(timeout=timeout)


def launch_relay(address, *args):
    return subprocess.Popen(
        [
            sys.executable,
            str(RELAY),
            "--host",
            address[0],
            "--port",
            str(address[1]),
            "--timeout",
            "1",
            *args,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_real_relay_handshake_and_bidirectional_bytes():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(2)
        with launch_relay(listener.getsockname()) as process:
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    # Readiness must precede the first state, not wait for it.
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        ready = executor.submit(process.stdout.readline)
                        assert ready.result(timeout=2) == b"ready\n"
                    state = '{"name":"é","x":1}\r\n'.encode()
                    process.stdin.write(state)
                    process.stdin.flush()
                    with connection.makefile("rb") as states:
                        assert states.readline() == state
                    connection.sendall(b"PLAY 1 0\nEND\n")
                stdout, stderr = process.communicate(timeout=3)
                assert stdout == b"PLAY 1 0\nEND\n"
                assert process.returncode == 1
                assert b"windows_relay:" in stderr
                assert b"Fatal Python error" not in stderr
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=2)


def test_relay_does_not_claim_readiness_if_connection_fails():
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        # Bound but not listening: connecting fails deterministically.
        with launch_relay(reserved.getsockname(), "--connect-timeout", "0.05") as process:
            stdout, stderr = process.communicate(timeout=2)
            assert stdout == b""
            assert b"windows_relay:" in stderr
            assert process.returncode == 1


def test_relay_rejects_oversized_game_line_without_forwarding_it():
    with BridgeServer(timeout=2, max_line_bytes=100) as bridge:
        with launch_relay(bridge.address, "--max-line-bytes", "8") as process:
            try:
                bridge.accept()
                process.stdin.write(b"123456789\n")
                process.stdin.flush()
                with pytest.raises(BridgeDisconnected):
                    bridge.receive()
                stdout, stderr = process.communicate(timeout=3)
                assert stdout == b"ready\n"
                assert b"byte limit" in stderr
                assert process.returncode == 1
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=2)


def test_relay_timeout_exits_even_if_game_stdin_remains_open():
    with BridgeServer(timeout=2) as bridge:
        with launch_relay(bridge.address, "--timeout", "0.05") as process:
            try:
                bridge.accept()
                process.wait(timeout=2)
                stdout, stderr = process.communicate(timeout=2)
                assert stdout == b"ready\n"
                assert b"timed out" in stderr
                assert process.returncode == 1
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=2)


def test_second_client_cannot_be_accepted_after_first_session():
    with BridgeServer(timeout=1) as bridge:
        with socket.create_connection(bridge.address):
            bridge.accept()
            with pytest.raises(OSError):
                socket.create_connection(bridge.address, timeout=0.1)


def test_send_first_accepts_relay():
    with BridgeServer(timeout=1) as bridge:
        result = []

        def connect_and_read():
            with socket.create_connection(bridge.address) as relay:
                result.append(relay.recv(32))

        thread = threading.Thread(target=connect_and_read)
        thread.start()
        bridge.send("STATE")
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert result == [b"STATE\n"]
