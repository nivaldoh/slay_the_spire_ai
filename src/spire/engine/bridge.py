"""One-session TCP transport for the CommunicationMod relay.

The relay sends unmodified JSON lines and receives command lines. It handles
CommunicationMod's ``ready`` handshake itself, after connecting. Any failure
closes the session for good.
"""

from __future__ import annotations

import json
import socket

DEFAULT_MAX_LINE_BYTES = 4 * 1024 * 1024


class BridgeError(RuntimeError):
    """Infrastructure failure, never an ordinary gameplay outcome."""


class BridgeTimeout(BridgeError):
    """The relay did not connect or complete an operation before its timeout."""


class BridgeDisconnected(BridgeError):
    """The bridge session has ended and cannot be reused."""


class BridgeProtocolError(BridgeError):
    """A line violates the CommunicationMod transport contract."""


class BridgeServer:
    """Listen for one relay; close for good on disconnect, timeout or invalid input.

    Enter the context before launching the relay. The first ``receive`` or ``send``
    accepts the connection. ``timeout`` is a socket inactivity limit, not an episode
    budget. The line byte limit includes the newline.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0, timeout: float = 30.0,
                 *, max_line_bytes: int = DEFAULT_MAX_LINE_BYTES) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.max_line_bytes = max_line_bytes
        self.address: tuple[str, int] | None = None
        self._listener: socket.socket | None = None
        self._connection: socket.socket | None = None
        self._reader = None

    def __enter__(self) -> BridgeServer:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Rebind the fixed port while the last episode's connection is in
            # TIME_WAIT; this never shares a live listener.
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.settimeout(self.timeout)
            listener.bind((self.host, self.port))
            listener.listen(1)
        except OSError as exc:
            listener.close()
            raise BridgeError(f"could not listen for relay: {exc}") from exc
        self._listener = listener
        self.address = listener.getsockname()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def accept(self) -> None:
        if self._connection is not None:
            return
        if self._listener is None:
            raise BridgeDisconnected("bridge session is closed; create a new server")
        try:
            self._connection, _ = self._listener.accept()
        except OSError as exc:
            raise self._socket_failure(exc, "waiting for relay connection") from exc
        # One session: no second relay can attach, even after a failure.
        self._listener.close()
        self._listener = None
        self._connection.settimeout(self.timeout)
        self._reader = self._connection.makefile("rb")

    def receive(self) -> dict:
        """Return the next complete JSON object, never a partial state."""
        self.accept()
        try:
            line = self._reader.readline(self.max_line_bytes + 1)
        except OSError as exc:
            raise self._socket_failure(exc, "waiting for a complete game state") from exc
        if not line:
            self.close()
            raise BridgeDisconnected("relay disconnected before the next game state")
        if len(line) > self.max_line_bytes:
            raise self._protocol_failure("game state exceeds the line byte limit")
        if not line.endswith(b"\n"):
            raise self._protocol_failure("relay disconnected in the middle of a game state")
        try:
            value = json.loads(line.decode("utf-8"))
        except ValueError as exc:
            raise self._protocol_failure(f"game state is not a UTF-8 JSON object: {exc}") from exc
        if not isinstance(value, dict):
            raise self._protocol_failure("game state must be a JSON object")
        return value

    def send(self, command: str) -> None:
        """Send exactly one command line."""
        if not command.strip() or any(character in command for character in "\r\n\0"):
            raise self._protocol_failure(f"command must be one nonempty line: {command!r}")
        self.accept()
        try:
            self._connection.sendall((command + "\n").encode("utf-8"))
        except OSError as exc:
            raise self._socket_failure(exc, "sending command") from exc

    def _socket_failure(self, exc: OSError, action: str) -> BridgeError:
        self.close()
        if isinstance(exc, TimeoutError):
            return BridgeTimeout(f"timed out {action}")
        return BridgeDisconnected(f"failed {action}: {exc}")

    def _protocol_failure(self, message: str) -> BridgeProtocolError:
        self.close()
        return BridgeProtocolError(message)

    def close(self) -> None:
        """Release every socket; safe to call repeatedly."""
        for resource in (self._reader, self._connection, self._listener):
            if resource is not None:
                resource.close()
        self._reader = self._connection = self._listener = None
