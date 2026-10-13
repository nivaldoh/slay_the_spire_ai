"""Screenshots and input on the Windows desktop, for driving a game's menus from WSL.

Runs under Windows python.exe: ``windows_desktop.py screenshot C:/x.png``,
``click X Y``, ``dblclick X Y``, ``move X Y``, ``key NAME`` (enter, escape, space, tab,
f1..f12, a letter or digit) and ``type TEXT``. Coordinates are screen pixels.
"""

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes

INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
MOUSEEVENTF_MOVE, MOUSEEVENTF_ABSOLUTE = 0x0001, 0x8000
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
KEYEVENTF_KEYUP = 0x0002
KEYS = {
    "enter": 0x0D, "escape": 0x1B, "space": 0x20, "tab": 0x09, "backspace": 0x08,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    **{f"f{n}": 0x6F + n for n in range(1, 13)},
}


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class KeyboardInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class InputUnion(ctypes.Union):
    _fields_ = [("mi", MouseInput), ("ki", KeyboardInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", InputUnion)]


user32 = ctypes.WinDLL("user32", use_last_error=True) if sys.platform == "win32" else None


def send(*inputs: Input) -> None:
    array = (Input * len(inputs))(*inputs)
    if user32.SendInput(len(inputs), array, ctypes.sizeof(Input)) != len(inputs):
        raise ctypes.WinError(ctypes.get_last_error())


def mouse(flags: int, x: int = 0, y: int = 0) -> Input:
    return Input(INPUT_MOUSE, InputUnion(mi=MouseInput(x, y, 0, flags, 0, None)))


def keyboard(code: int, flags: int = 0) -> Input:
    return Input(INPUT_KEYBOARD, InputUnion(ki=KeyboardInput(code, 0, flags, 0, None)))


def move(x: int, y: int) -> None:
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    send(mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
               x * 65535 // (width - 1), y * 65535 // (height - 1)))


def click(x: int, y: int) -> None:
    move(x, y)
    time.sleep(0.1)
    send(mouse(MOUSEEVENTF_LEFTDOWN))
    time.sleep(0.05)
    send(mouse(MOUSEEVENTF_LEFTUP))


def dblclick(x: int, y: int) -> None:
    click(x, y)
    time.sleep(0.08)
    send(mouse(MOUSEEVENTF_LEFTDOWN))
    time.sleep(0.05)
    send(mouse(MOUSEEVENTF_LEFTUP))


def key(name: str) -> None:
    code = KEYS.get(name.lower()) or (ord(name.upper()) if len(name) == 1 else None)
    if code is None:
        raise ValueError(f"unknown key {name}")
    send(keyboard(code))
    time.sleep(0.05)
    send(keyboard(code, KEYEVENTF_KEYUP))


def screenshot(path: str) -> None:
    script = (
        "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
        "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
        "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height; "
        "$g=[System.Drawing.Graphics]::FromImage($bmp); "
        "$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); "
        f"$bmp.Save('{path}',[System.Drawing.Imaging.ImageFormat]::Png)"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], check=True, timeout=30)


def main(argv: list[str]) -> int:
    command, arguments = argv[0], argv[1:]
    if command == "screenshot":
        screenshot(arguments[0])
    elif command in ("click", "dblclick", "move"):
        action = {"click": click, "dblclick": dblclick, "move": move}[command]
        action(int(arguments[0]), int(arguments[1]))
    elif command == "key":
        key(arguments[0])
    elif command == "type":
        for character in " ".join(arguments):
            key(character if character != " " else "space")
    else:
        raise SystemExit(f"unknown command {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
