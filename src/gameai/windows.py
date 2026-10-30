"""Windows game processes owned from WSL or native Windows Python: one controller lock, a
supervised launch, probes.

``NATIVE`` picks the side at import time (owner, 2026-10-30: WSL2 for local development;
hosted machines will likely run Windows directly). Under WSL, Windows paths are spelled
through ``/mnt/<drive>`` and Windows Python is a separate executable; natively they are the
paths and interpreter themselves. PySC2 picks its install paths by platform the same way
(``pysc2/run_configs/platforms.py`` at 0df53d38c153972f1e368572ba65b1442a0fd41f: ``Windows``
spells the game folder ``C:/...``, ``Cygwin`` ``/cygdrive/c/...``).
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

NATIVE = sys.platform == "win32"
if NATIVE:
    import msvcrt
else:
    import fcntl
    import select

WINDOWS_PYTHON = Path(sys.executable) if NATIVE else Path("/mnt/c/Python313/python.exe")


def windows_path(path: Path) -> str:
    """The Windows spelling ("C:/...") of a drive path, for python.exe arguments; under WSL
    the path lies under /mnt/<drive>."""
    if NATIVE:
        return path.as_posix()
    parts = path.parts
    if len(parts) < 3 or parts[:2] != ("/", "mnt") or len(parts[2]) != 1:
        raise ValueError(f"not a Windows drive path: {path}")
    return f"{parts[2].upper()}:/" + "/".join(parts[3:])


class RuntimeLock:
    """One controller at a time, held around runtime preparation and the owned game.

    The OS releases the lock (flock, or a byte lock through msvcrt natively) if the
    controller dies; a file's existence is not a lock.
    """

    def __init__(self, directory: Path):
        self.directory = directory

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self._file = (self.directory / "owner.lock").open("a+")
        try:
            if NATIVE:
                # msvcrt.locking locks bytes from the current position (Python docs).
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self._file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._file.close()
            raise RuntimeError("another controller owns the game runtime") from exc
        return self

    def __exit__(self, *_):
        self._file.close()


def probe(command: list[str], timeout: float = 8) -> dict:
    """Run a bounded version or resource probe."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "error": type(exc).__name__}
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "output": (result.stdout or result.stderr).strip()[:4096],
    }


class OwnedGame:
    """A game process with a Windows-side watchdog and controller-lifetime cleanup.

    ``windows_game.py`` must already be copied into ``runtime_dir``. ``command`` is the
    Windows command line the supervisor runs from ``game_dir``; ``rules`` names the
    processes it refuses to overlap (see ``windows_game.is_game_process``).
    """

    def __init__(
        self, log_path: Path, *, runtime_dir: Path, game_dir: str, command: list[str],
        rules: dict, timeout: float = 600,
    ):
        # Windows writes the log to the runtime folder; close() copies it to log_path.
        self.log_path = log_path
        self.runtime_dir = runtime_dir
        self.windows_log = runtime_dir / f"game-{os.getpid()}-{uuid.uuid4().hex}.log"
        self.game_dir = game_dir
        self.command = command
        self.rules = rules
        self.timeout = timeout
        self.process = None
        self.info = None
        self.supervisor_stderr = ""

    def __enter__(self):
        # Python.exe takes Windows paths for the script and its arguments.
        runtime = windows_path(self.runtime_dir)
        command = [
            str(WINDOWS_PYTHON), f"{runtime}/windows_game.py",
            "--game-dir", self.game_dir,
            "--log", f"{runtime}/{self.windows_log.name}",
            "--timeout", str(self.timeout),
            "--rules", json.dumps(self.rules),
            "--", *self.command,
        ]
        pipe = subprocess.PIPE
        self.process = subprocess.Popen(command, stdin=pipe, stdout=pipe, stderr=pipe, text=True)
        try:
            self.info = self._startup_message()
            return self
        except BaseException as exc:
            self.close()
            if isinstance(exc, Exception) and self.supervisor_stderr.strip():
                raise RuntimeError(f"{exc}: {self.supervisor_stderr.strip()}") from exc
            raise

    def _startup_message(self, timeout: float = 15) -> dict:
        """Read the supervisor's first line without blocking past the deadline."""
        if NATIVE:
            # select() takes only sockets on Windows: read the line in a thread instead.
            lines = []
            reader = threading.Thread(
                target=lambda: lines.append(self.process.stdout.readline()), daemon=True
            )
            reader.start()
            reader.join(timeout)
            if reader.is_alive():
                raise TimeoutError("Windows supervisor did not report startup before deadline")
            if not lines[0].endswith("\n"):
                raise RuntimeError("Windows supervisor closed stdout before reporting startup")
            return json.loads(lines[0])
        deadline = time.monotonic() + timeout
        line = b""
        while b"\n" not in line:
            remaining = max(0, deadline - time.monotonic())
            if not select.select([self.process.stdout], [], [], remaining)[0]:
                raise TimeoutError("Windows supervisor did not report startup before deadline")
            chunk = os.read(self.process.stdout.fileno(), 4096)
            if not chunk:
                # Do not block reading stderr from a process which only closed stdout.
                raise RuntimeError("Windows supervisor closed stdout before reporting startup")
            line += chunk
        return json.loads(line.split(b"\n", 1)[0])

    def close(self) -> None:
        if self.process is None:
            return
        process, self.process = self.process, None
        try:
            _, self.supervisor_stderr = process.communicate("stop\n", timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            _, self.supervisor_stderr = process.communicate(timeout=5)
        finally:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            if self.windows_log.exists():
                shutil.copy2(self.windows_log, self.log_path)
            if self.supervisor_stderr:
                self.log_path.with_name("supervisor.stderr.log").write_text(self.supervisor_stderr)

    def __exit__(self, *_):
        self.close()
