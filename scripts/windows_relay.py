"""Standalone stdlib relay launched by CommunicationMod on Windows.

Example CommunicationMod command (paths must not contain spaces):
    C:/Python/python.exe C:/spire/windows_relay.py --host 127.0.0.1 --port 8765

Connect before emitting ``ready``. Every later stdout byte is a command from
the runner. Diagnostics go to stderr. Run Java with -Dfile.encoding=UTF-8.
There is deliberately no reconnection: reconnecting could reuse stale state.
"""

from __future__ import annotations

import argparse
import math
import os
import queue
import socket
import sys
import threading
from collections.abc import Iterator
from typing import BinaryIO

DEFAULT_MAX_LINE_BYTES = 4 * 1024 * 1024


class RelayError(RuntimeError):
    pass


def read_line(stream: BinaryIO, max_line_bytes: int, origin: str) -> bytes:
    line = stream.readline(max_line_bytes + 1)
    if not line:
        raise RelayError(f"{origin} disconnected")
    if len(line) > max_line_bytes:
        raise RelayError(f"{origin} line exceeds configured byte limit")
    if not line.endswith(b"\n"):
        raise RelayError(f"{origin} disconnected in the middle of a line")
    return line


def game_lines(max_line_bytes: int) -> Iterator[bytes]:
    # os.read avoids a daemon thread holding Python's buffered-stdin lock during
    # interpreter shutdown if the runner disconnects while the game is silent.
    pending = bytearray()
    while True:
        chunk = os.read(sys.stdin.fileno(), min(65536, max_line_bytes + 1 - len(pending)))
        if not chunk:
            suffix = " in the middle of a line" if pending else ""
            raise RelayError(f"CommunicationMod disconnected{suffix}")
        pending.extend(chunk)
        while (boundary := pending.find(b"\n")) >= 0:
            if boundary + 1 > max_line_bytes:
                raise RelayError("CommunicationMod line exceeds configured byte limit")
            line = bytes(pending[: boundary + 1])
            del pending[: boundary + 1]
            yield line
        if len(pending) > max_line_bytes:
            raise RelayError("CommunicationMod line exceeds configured byte limit")


def relay(connection: socket.socket, max_line_bytes: int) -> None:
    failures: queue.SimpleQueue[Exception] = queue.SimpleQueue()

    def forward_game_states() -> None:
        try:
            for line in game_lines(max_line_bytes):
                connection.sendall(line)
        except (OSError, RelayError) as exc:
            failures.put(exc)
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    # CommunicationMod waits for this flushed line before sending game state.
    sys.stdout.buffer.write(b"ready\n")
    sys.stdout.buffer.flush()
    threading.Thread(target=forward_game_states, daemon=True).start()
    try:
        with connection.makefile("rb") as commands:
            while True:
                line = read_line(commands, max_line_bytes, "runner")
                if b"\0" in line or b"\r" in line:
                    raise RelayError("runner command contains a forbidden CR or NUL delimiter")
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
    except (OSError, RelayError) as exc:
        # Prefer the actual stdin/send error over the shutdown it triggers.
        if not failures.empty():
            raise failures.get() from exc
        raise


def positive_seconds(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("timeout must be positive and finite")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--connect-timeout", type=positive_seconds, default=5.0)
    parser.add_argument("--timeout", type=positive_seconds, default=30.0)
    parser.add_argument("--max-line-bytes", type=int, default=DEFAULT_MAX_LINE_BYTES)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if args.max_line_bytes < 2:
        parser.error("max-line-bytes must be at least 2")
    if os.name == "nt":
        import msvcrt

        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    try:
        with socket.create_connection((args.host, args.port), args.connect_timeout) as connection:
            connection.settimeout(args.timeout)
            relay(connection, args.max_line_bytes)
    except (OSError, RelayError) as exc:
        print(f"windows_relay: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
