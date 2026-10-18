"""Standalone stdlib relay launched by CommunicationMod on Windows.

``runtime.prepare_runtime`` configures this CommunicationMod command (paths must not
contain spaces):
    C:/Python313/python.exe C:/spire-agent/windows_relay.py --host H --port P --timeout S

Connect before emitting ``ready``. Game state goes to the runner unchanged; every later
stdout byte is a command from the runner. The runner's bridge enforces the line limit.
Diagnostics go to stderr. There is deliberately no reconnection: reconnecting could
reuse stale state. ``--timeout`` bounds the connection only: a model may think longer
than any idle limit, and the Windows supervisor ends the relay with the game.
"""

from __future__ import annotations

import argparse
import os
import queue
import socket
import sys
import threading


class RelayError(RuntimeError):
    pass


def relay(connection: socket.socket) -> None:
    failures: queue.SimpleQueue[Exception] = queue.SimpleQueue()

    def forward_game_states() -> None:
        # os.read avoids a daemon thread holding Python's buffered-stdin lock during
        # interpreter shutdown if the runner disconnects while the game is silent.
        try:
            while chunk := os.read(sys.stdin.fileno(), 65536):
                connection.sendall(chunk)
            failures.put(RelayError("CommunicationMod disconnected"))
        except OSError as exc:
            failures.put(exc)
        # Wake the command loop below, so the relay exits.
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
            # Forward only complete lines: never a command cut short by a disconnect.
            while (line := commands.readline()).endswith(b"\n"):
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
        raise RelayError("runner disconnected")
    except (OSError, RelayError) as exc:
        # Prefer the actual stdin/send error over the shutdown it triggers.
        if not failures.empty():
            raise failures.get() from exc
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--timeout", type=float, required=True)
    args = parser.parse_args()
    if os.name == "nt":
        import msvcrt

        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    try:
        with socket.create_connection((args.host, args.port), args.timeout) as connection:
            connection.settimeout(None)
            relay(connection)
    except (OSError, RelayError) as exc:
        print(f"windows_relay: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
