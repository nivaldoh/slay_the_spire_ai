"""Typed direct operations for one owned client, on top of the passive capture.

Run under the Windows Frida Python, like ``multiplayer_probe``. Without this module's agent
the capture stays passive. Requests arrive one JSON object per stdin line,
``{"operation": ..., "request": ...}``; every result is a row in the capture's ``native.jsonl``.
Stage 1 of docs/twwarhammer3/multiplayer-control-foundation.md: experimental until a live
reference and the other client's readback back it. The caller still owns the game.

JUDGEMENT?: Request bound — Claude, 2026-11-04: a request waits at most 30 s for a battle
frame, then expires unsubmitted. The acknowledgement bound (10 s) is the worker's; a longer
one could act on an old request after the phase moved on, and the guards would still apply.
"""

import argparse
import json
import sys
import threading
from pathlib import Path

from twwarhammer3.engine import multiplayer_probe as probe

AGENT = Path(__file__).with_suffix(".js")
OPERATIONS = ("ready_deployment",)


class Adapter:
    """Feeds stdin lines to the agent; a refused line is evidence, never a crash."""

    def __init__(self, lines):
        self.lines = lines
        self.source = AGENT.read_text(encoding="utf-8")

    def start(self, script, write) -> threading.Thread:
        def feed():
            for line in self.lines:
                try:
                    request = json.loads(line)
                    if request["operation"] not in OPERATIONS:
                        raise ValueError("unknown operation")
                    answer = script.exports_sync.submit(request["operation"], request["request"])
                except (ValueError, KeyError, TypeError) as error:
                    write({"event": "request_refused", "line": line.strip(),
                           "message": str(error)})
                    continue
                except Exception as error:  # the attachment ended under a late request
                    write({"event": "request_failed", "line": line.strip(),
                           "message": str(error)})
                    return
                write({"event": "request_answer", "request": request["request"], "answer": answer})

        thread = threading.Thread(target=feed, daemon=True)
        thread.start()
        return thread


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True, help="caller's owned WH3 process")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("run under the Windows Frida Python")
    import frida

    return probe.capture(frida.get_local_device(), args.pid, args.output, seconds=args.seconds,
                         adapter=Adapter(sys.stdin))


if __name__ == "__main__":
    raise SystemExit(main())
