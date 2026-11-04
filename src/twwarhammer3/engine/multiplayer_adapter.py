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
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from gameai import windows
from twwarhammer3.engine import multiplayer_probe as probe
from twwarhammer3.engine import runtime

AGENT = Path(__file__).with_suffix(".js")
OPERATIONS = ("ready_deployment",)
REQUEST_S = 30.0  # as REQUEST_MS in the agent; rests on the Request bound above
FRIDA_PYTHON = runtime.RUNTIME_DIR / "checkpoint-frida-venv/Scripts/python.exe"
CAPTURES = runtime.RUNTIME_DIR / "native-capture"


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


def source_path() -> str:
    """This checkout's ``src`` as the Windows Python spells it."""
    source = Path(__file__).resolve().parents[2]
    if windows.NATIVE:
        return str(source)
    return subprocess.check_output(["wslpath", "-w", str(source)], text=True).strip()


class Helper:
    """The caller's side: the Windows Frida process beside one owned game. It writes to a
    Windows folder (WSL paths are slow from there), then ``close`` copies the evidence out."""

    def __init__(self, pid: int, name: str, evidence: Path, *, seconds: float,
                 run=subprocess.Popen):
        self.native, self.evidence = CAPTURES / name, evidence
        self.position, self.pending, self.rows = 0, b"", []
        code = (f"import sys; sys.path.insert(0, {source_path()!r}); "
                "from twwarhammer3.engine.multiplayer_adapter import main; "
                "raise SystemExit(main())")
        self.process = run([str(FRIDA_PYTHON), "-c", code, "--pid", str(pid),
                            "--output", windows.windows_path(self.native),
                            "--seconds", str(seconds)],
                           stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                           stderr=subprocess.STDOUT, text=True)

    def poll(self) -> list[dict]:
        """New rows of native.jsonl; a line still being written waits for the next poll."""
        path = self.native / "native.jsonl"
        if not path.exists():
            return []
        with path.open("rb") as file:
            file.seek(self.position)
            data = file.read()
        self.position += len(data)
        *lines, self.pending = (self.pending + data).split(b"\n")
        rows = [json.loads(line) for line in lines if line]
        self.rows += rows
        return rows

    def wait_ready(self, seconds: float = 40) -> None:
        deadline = time.monotonic() + seconds
        while True:
            self.poll()
            if any(row.get("event") == "adapter_ready" for row in self.rows):
                return
            if self.process.poll() is not None:
                raise RuntimeError("the adapter helper exited before it was ready")
            if time.monotonic() > deadline:
                raise TimeoutError("the adapter helper was not ready")
            time.sleep(0.2)

    def request(self, operation: str) -> str:
        request = uuid.uuid4().hex
        self.process.stdin.write(json.dumps({"operation": operation, "request": request}) + "\n")
        self.process.stdin.flush()
        return request

    def result(self, request: str, statuses: tuple, seconds: float) -> dict | None:
        """The first row for ``request`` with one of ``statuses``, or None after ``seconds``."""
        deadline = time.monotonic() + seconds
        while True:
            self.poll()
            for row in self.rows:
                if (row.get("event") == "operation_result" and row.get("request") == request
                        and row.get("status") in statuses):
                    return row
            if time.monotonic() > deadline or self.process.poll() is not None:
                return None
            time.sleep(0.1)

    def close(self) -> None:
        """Ask the helper to detach, then keep every row it wrote; never touches the game."""
        if self.native.exists():
            (self.native / "STOP").touch()
        try:
            self.process.stdin.close()
        except OSError:
            pass
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        if self.native.exists():
            shutil.copytree(self.native, self.evidence, dirs_exist_ok=True)


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
