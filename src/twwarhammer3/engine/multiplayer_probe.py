"""Bounded Windows-side passive reference capture for multiplayer foundation stage 1.

Run with the existing Windows Frida Python, while the caller owns the game process.
Attach before entering a new battle: already-constructed sessions are deliberately not
guessed from memory. This diagnostic cannot issue commands or decide readiness/synchrony.
The worker/runner integration follows the native operation discovery; this is not a way
to borrow a game for operational matches. No launch, cleanup of games, or cloud spending.
"""

import argparse
import ctypes
import hashlib
import json
import math
import sys
import threading
import time
from pathlib import Path

from twwarhammer3.engine import runtime

AGENT = Path(__file__).with_suffix(".js")


def process_executable(pid: int) -> Path:
    """Read the actual process image path; never hash only a presumed install path."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                 wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return Path(buffer.value)
    finally:
        kernel.CloseHandle(handle)


def capture(device, pid: int, output: Path, *, seconds: float) -> int:
    """Read-only attachment; caller retains ownership. A probe error exits nonzero."""
    if pid <= 0 or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("positive pid and finite positive capture seconds are required")
    exe = process_executable(pid)
    with exe.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    if exe.name.lower() != "warhammer3.exe" or digest != runtime.PINS["Warhammer3.exe"]:
        raise RuntimeError(f"unsupported multiplayer probe executable: {exe} sha256={digest}")
    source = AGENT.read_text(encoding="utf-8")
    output.mkdir(parents=True)  # a fresh capture; never overwrite failed evidence
    (output / "manifest.json").write_text(json.dumps({
        "pid": pid, "executable": str(exe), "exe_sha256": digest,
        "agent_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "seconds": seconds, "diagnostic_only": True,
    }, indent=2), encoding="utf-8")
    stopped, failed, ready = threading.Event(), threading.Event(), threading.Event()
    lock = threading.Lock()
    with (output / "native.jsonl").open("x", encoding="utf-8", buffering=1) as log:
        def write(row):
            with lock:
                log.write(json.dumps({"received_wall_ns": time.time_ns(),
                                      "received_perf_ns": time.perf_counter_ns(), **row}) + "\n")

        def message(row, data):
            payload = (row["payload"] if row.get("type") == "send"
                       else {"event": "frida_error", "message": row})
            write(payload)
            if payload.get("event") in ("probe_error", "frida_error"):
                failed.set()
                stopped.set()
            if payload.get("event") == "ready":
                ready.set()

        def detached(reason, crash):
            failed.set()
            stopped.set()
            # frida.Session's optional Crash is an attribute object, not JSON.
            write({"event": "detached", "reason": reason,
                   "crash": None if crash is None else {
                       "summary": str(crash.summary), "report": str(crash.report)}})

        session = None
        try:
            session = device.attach(pid)
            session.on("detached", detached)
            script = session.create_script(source)
            script.on("message", message)
            script.load()
            deadline = time.monotonic() + seconds
            while not stopped.is_set() and time.monotonic() < deadline:
                if (output / "STOP").exists():
                    break
                stopped.wait(min(0.2, max(0, deadline - time.monotonic())))
        except Exception as error:
            write({"event": "capture_error", "message": str(error)})
            failed.set()
        finally:
            if session is not None:
                try:
                    session.off("detached", detached)
                    session.detach()  # unload hooks before the log closes; never kill the game
                except Exception as error:
                    write({"event": "detach_error", "message": str(error)})
                    failed.set()
            write({"event": "capture_stopped", "ready": ready.is_set(),
                   "failed": failed.is_set()})
    return 1 if failed.is_set() or not ready.is_set() else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True, help="caller's owned WH3 process")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("run under the Windows Frida Python")
    import frida

    return capture(frida.get_local_device(), args.pid, args.output, seconds=args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
