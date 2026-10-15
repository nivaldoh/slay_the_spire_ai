"""One passive screenshot on Windows. Never activate windows or send desktop input."""

import ctypes
import json
import sys
import time
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path


def capture(pid: int, output: Path, observation: Path, job: str, battle: str) -> dict:
    from PIL import ImageGrab

    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user.SetProcessDPIAware()
    window = user.GetForegroundWindow()
    owner = wintypes.DWORD()
    user.GetWindowThreadProcessId(window, ctypes.byref(owner))
    if owner.value != pid:
        raise RuntimeError("Game is not foreground; skipped desktop capture")
    rectangle, origin = wintypes.RECT(), wintypes.POINT()
    if not user.GetClientRect(window, ctypes.byref(rectangle)) or not user.ClientToScreen(
            window, ctypes.byref(origin)):
        raise ctypes.WinError(ctypes.get_last_error())
    bounds = (origin.x, origin.y, origin.x + rectangle.right, origin.y + rectangle.bottom)
    before = json.loads(observation.read_text())
    if before.get("job") != job or before.get("battle") != battle:
        raise RuntimeError("Battle changed before capture")
    began, wall = time.perf_counter(), datetime.now(UTC).isoformat()
    image = ImageGrab.grab(bbox=bounds, all_screens=True)
    grab_s = time.perf_counter() - began
    if user.GetForegroundWindow() != window:
        raise RuntimeError("Foreground changed during capture; discarded image")
    after = json.loads(observation.read_text())
    if after.get("job") != job or after.get("battle") != battle:
        raise RuntimeError("Battle changed during capture; discarded image")
    image.save(output)
    return {"status": "captured", "file": output.name, "backend": "passive_windows_pillow",
            "captured_at": wall, "grab_wall_s": grab_s, "total_wall_s": time.perf_counter() - began,
            "size": list(image.size), "time_ms": before.get("time_ms"),
            "capture_interval_ms": [before.get("time_ms"), after.get("time_ms")],
            "time_basis": "Public observations bracketing passive capture; not exact frame time",
            "policy_input": False}


if __name__ == "__main__":
    try:
        result = capture(int(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]),
                         sys.argv[4], sys.argv[5])
    except Exception as exc:
        result = {"status": "capture_failed", "error": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(result), flush=True)
