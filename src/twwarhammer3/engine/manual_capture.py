"""Windows-only passive video/state capture for an owned manual demonstration.

Uses FFmpeg's documented gfxcapture hwnd input. It never focuses a window, sends input,
changes speed or orders units. A stopped battle clock is a possible pause OR a stall;
only independently labelled video establishes pause intervals. Run via manual_demo.py.
"""

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

# Direct invocation by Windows Python from the source tree (including a WSL UNC path).
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gameai.windows import open_shared


def window_for_pid(pid):
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    matches = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def visit(hwnd, _):
        owner = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user.IsWindowVisible(hwnd):
            matches.append(hwnd)
        return True

    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.EnumWindows(visit, 0)
    return matches[0] if matches else None


def video_command(ffmpeg, hwnd, output):
    return [str(ffmpeg), "-hide_banner", "-loglevel", "warning", "-n", "-filter_complex",
            f"gfxcapture=hwnd={hwnd}:max_framerate=30:dup_frames=1,"
            "hwdownload,format=bgra,fps=30,crop=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-progress", str(output / "video-progress.txt"), str(output / "video.mkv")]


def read_snapshot(path, job):
    try:
        with open_shared(path) as file:
            observation = json.loads(file.read())
            stamp = os.fstat(file.fileno()).st_mtime_ns
        if observation.get("job") == job:
            return observation, stamp
    except (OSError, ValueError):
        pass
    return None, None


def capture(args):
    output = args.output
    deadline = time.monotonic() + args.timeout
    video = None
    status = {"status": "starting", "clock": "Windows time_ns and monotonic_ns",
              "pause_intervals": None, "pause_status": "unknown until video labels are supplied"}
    try:
        with (output / "capture.jsonl").open("x", buffering=1) as journal, (
                output / "trace.jsonl").open("x", buffering=1) as trace, (
                output / "video.log").open("x") as log:
            last = None
            while time.monotonic() < deadline and not (output / "stop-capture").exists():
                if video is None:
                    hwnd = window_for_pid(args.pid)
                    if hwnd:
                        command = video_command(args.ffmpeg, hwnd, output)
                        status.update(command=command, video_started_windows_ns=time.time_ns())
                        video = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
                elif video.poll() is not None:
                    raise RuntimeError(f"video process exited {video.returncode}; see video.log")
                progress = output / "video-progress.txt"
                if progress.exists() and any(line.startswith("frame=") and
                                            int(line.split("=", 1)[1]) > 0
                                            for line in progress.read_text().splitlines()):
                    if status["status"] == "starting":
                        status["status"] = "recording"
                        (output / "capture-ready.json").write_text(json.dumps(status))
                observation, stamp = read_snapshot(args.bridge / "observation.json", args.job)
                row = {"windows_ns": time.time_ns(), "monotonic_ns": time.monotonic_ns(),
                       "written_windows_ns": stamp,
                       "battle": (observation or {}).get("battle"),
                       "seq": (observation or {}).get("seq"),
                       "time_ms": (observation or {}).get("time_ms"),
                       "speed": (observation or {}).get("speed")}
                journal.write(json.dumps(row) + "\n")
                identity = (row["battle"], row["seq"])
                if observation and identity != last:
                    trace.write(json.dumps({"kind": "observation", "observation": observation,
                                            **row}) + "\n")
                    last = identity
                # Rests on JUDGEMENT docs/twwarhammer3/support-timing.md Manual sampling.
                time.sleep(.2)
            status["status"] = "stopped" if (output / "stop-capture").exists() else "timeout"
    except BaseException as exc:
        status.update(status="capture_failure", error=str(exc))
        raise
    finally:
        if video is not None:
            try:
                video.communicate(b"q\n", timeout=10)
            except subprocess.TimeoutExpired:
                video.kill()
                video.communicate()
                status.update(status="capture_failure", error="video did not finalize within 10 s")
            status["video_exit_code"] = video.returncode
            if video.returncode:
                status.update(status="capture_failure", error="video failed; see video.log")
        status["finished_windows_ns"] = time.time_ns()
        (output / "capture-result.json").write_text(json.dumps(status, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True, type=Path)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--job", required=True)
    parser.add_argument("--timeout", required=True, type=float)
    capture(parser.parse_args())


if __name__ == "__main__":
    main()
