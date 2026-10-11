"""One-session TCP transport for the CommunicationMod subprocess relay.

The relay sends unmodified JSON lines and receives command lines. There is no
TCP-side readiness message: the relay handles CommunicationMod's ``ready``
handshake itself, after connecting. All failures invalidate the session.
"""

from __future__ import annotations

import json
import math
import socket
from typing import BinaryIO

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
    """Listen for one relay, closing permanently on disconnect or invalid input.

    Enter the context before launching the Windows relay. ``address`` contains
    the bound port (including when port=0). ``accept`` may be called explicitly;
    otherwise the first ``receive`` or ``send`` accepts the connection. Timeout
    is a socket inactivity limit, not a game episode budget. The byte limit
    includes the newline delimiter. This class is intended for one runner thread.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        timeout: float = 30.0,
        *,
        max_line_bytes: int = DEFAULT_MAX_LINE_BYTES,
    ) -> None:
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        if type(max_line_bytes) is not int or max_line_bytes < 2:
            raise ValueError("max_line_bytes must be at least 2")
        self.host = host
        self.port = port
        self.timeout = timeout
        self.max_line_bytes = max_line_bytes
        self._listener: socket.socket | None = None
        self._connection: socket.socket | None = None
        self._reader: BinaryIO | None = None
        self._address: tuple[str, int] | None = None
        self._closed = False

    @property
    def address(self) -> tuple[str, int]:
        if self._address is None:
            raise BridgeError("bridge has not started; enter its context first")
        return self._address

    def __enter__(self) -> BridgeServer:
        if self._closed or self._listener is not None or self._connection is not None:
            raise BridgeError("bridge contexts cannot be reused")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Reuse the WSL listening address after a previous episode's TCP
            # connection enters TIME_WAIT; this does not share a live listener.
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.settimeout(self.timeout)
            listener.bind((self.host, self.port))
            listener.listen(1)
        except OSError as exc:
            listener.close()
            self.close()
            raise BridgeError(f"could not listen for relay: {exc}") from exc
        self._listener = listener
        self._address = listener.getsockname()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def accept(self) -> None:
        if self._closed:
            raise BridgeDisconnected("bridge session is closed; create a new server")
        if self._connection is not None:
            return
        if self._listener is None:
            raise BridgeError("bridge has not started; enter its context first")
        try:
            connection, _ = self._listener.accept()
            connection.settimeout(self.timeout)
            self._connection = connection
            self._reader = connection.makefile("rb")
            # A session never accepts a second connection, including after failure.
            self._listener.close()
            self._listener = None
        except TimeoutError as exc:
            self.close()
            raise BridgeTimeout("timed out waiting for relay connection") from exc
        except OSError as exc:
            self.close()
            raise BridgeDisconnected(f"could not accept relay: {exc}") from exc

    def receive(self) -> dict:
        """Receive a complete UTF-8 JSON object, without exposing partial states."""
        self.accept()
        assert self._reader is not None
        try:
            line = self._reader.readline(self.max_line_bytes + 1)
        except TimeoutError as exc:
            self.close()
            raise BridgeTimeout("timed out waiting for a complete game state") from exc
        except OSError as exc:
            self.close()
            raise BridgeDisconnected(f"could not receive game state: {exc}") from exc
        if not line:
            self.close()
            raise BridgeDisconnected("relay disconnected before the next game state")
        if len(line) > self.max_line_bytes:
            self._protocol_error("game state exceeds the configured line byte limit")
        if not line.endswith(b"\n"):
            self._protocol_error("relay disconnected in the middle of a game state")
        try:
            value = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.close()
            raise BridgeProtocolError(f"game state is not a UTF-8 JSON object: {exc}") from exc
        if not isinstance(value, dict):
            self._protocol_error("game state must be a JSON object")
        return value

    def send(self, command: str) -> None:
        """Send exactly one command; never insert or accept additional delimiters."""
        if not isinstance(command, str) or not command.strip():
            self._protocol_error("command must be a nonempty string")
        if any(delimiter in command for delimiter in ("\r", "\n", "\0")):
            self._protocol_error("command contains a forbidden CR, LF, or NUL delimiter")
        try:
            line = (command + "\n").encode("utf-8")
        except UnicodeEncodeError as exc:
            self.close()
            raise BridgeProtocolError("command is not valid UTF-8") from exc
        if len(line) > self.max_line_bytes:
            self._protocol_error("command exceeds the configured line byte limit")
        self.accept()
        assert self._connection is not None
        try:
            self._connection.sendall(line)
        except TimeoutError as exc:
            self.close()
            raise BridgeTimeout("timed out sending command") from exc
        except OSError as exc:
            self.close()
            raise BridgeDisconnected(f"could not send command: {exc}") from exc

    def _protocol_error(self, message: str) -> None:
        self.close()
        raise BridgeProtocolError(message)

    def close(self) -> None:
        """Idempotently release sockets; a closed server cannot be restarted."""
        self._closed = True
        if self._reader is not None:
            self._reader.close()
            self._reader = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        if self._listener is not None:
            self._listener.close()
            self._listener = None
