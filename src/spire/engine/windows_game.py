"""Own one Windows JVM and stop it on controller EOF or a hard time limit."""

import argparse
import ctypes
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path


def join_kill_on_close_job() -> None:
    """Put this supervisor in a job that kills every member when its handle closes.

    Join before creating the JVM, so no child is ever outside the job. The handle
    is never closed explicitly: Windows closes it when this process exits, normally
    or by force, and then kills every remaining descendant.
    """
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE

    class BasicLimits(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimits),
            ("IoInfo", ctypes.c_uint64 * 6),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    limits = ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())


def conflicting_games(game_dir: Path) -> list[dict]:
    """Read process metadata and refuse overlap; never terminate an existing game."""
    query = (
        "$ErrorActionPreference='Stop'; "
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
        "@(Get-CimInstance Win32_Process -Filter "
        "\"Name='java.exe' OR Name='javaw.exe' OR Name='SlayTheSpire.exe'\" | "
        "Select-Object ProcessId,Name,ExecutablePath,CommandLine) | ConvertTo-Json -Compress"
    )
    output = subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", query], timeout=10
    ).decode("utf-8-sig").strip()
    processes = json.loads(output) if output else []
    if isinstance(processes, dict):
        processes = [processes]
    return [process for process in processes if is_game_process(process, game_dir)]


def is_game_process(process: dict, game_dir: Path) -> bool:
    name = (process.get("Name") or "").lower()
    executable = (process.get("ExecutablePath") or "").lower().replace("/", "\\")
    command = (process.get("CommandLine") or "").lower().replace("/", "\\")
    game_path = str(game_dir).lower().replace("/", "\\").rstrip("\\") + "\\"
    return (
        name == "slaythespire.exe"
        or executable.startswith(game_path)
        or "modthespire.jar" in command
        or "desktop-1.0.jar" in command
        or game_path in command
        # An inaccessible JVM cannot be safely classified as unrelated.
        or (name in {"java.exe", "javaw.exe"} and not executable and not command)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", required=True)
    parser.add_argument("--loader", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args()
    game_dir = Path(args.game_dir)
    join_kill_on_close_job()
    conflicts = conflicting_games(game_dir)
    if conflicts:
        print(
            "windows_game: refusing overlap with existing game/JVM PIDs "
            + ", ".join(str(process["ProcessId"]) for process in conflicts),
            file=sys.stderr,
            flush=True,
        )
        return 1
    command = [
        str(game_dir / "jre/bin/java.exe"), "-Xmx1G", "-Dfile.encoding=UTF-8", "-jar", args.loader,
        "--skip-launcher", "--skip-intro", "--mods", "basemod,CommunicationMod",
    ]
    stop = threading.Event()

    def watch_controller() -> None:
        # EOF also means the WSL controller disappeared. Never leave an orphan JVM.
        os.read(sys.stdin.fileno(), 1)
        stop.set()

    with Path(args.log).open("wb") as log:
        process = subprocess.Popen(command, cwd=game_dir, stdout=log, stderr=subprocess.STDOUT)
        try:
            print(json.dumps({"pid": process.pid, "command": command}), flush=True)
            threading.Thread(target=watch_controller, daemon=True).start()
            deadline = time.monotonic() + args.timeout
            while process.poll() is None and time.monotonic() < deadline:
                if stop.wait(0.2):
                    break
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        print(json.dumps({"exit_code": process.returncode}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
