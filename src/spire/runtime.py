"""Local Windows game setup and bounded process ownership from WSL."""

import hashlib
import json
import math
import os
import select
import shutil
import subprocess
from pathlib import Path

GAME_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/SlayTheSpire")
WORKSHOP_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/workshop/content/646570")
RUNTIME_DIR = Path("/mnt/c/spire-agent")
WINDOWS_PYTHON = Path("/mnt/c/Python313/python.exe")
PINS = {
    "ModTheSpire.jar": (
        "1605060445",
        "541b5e8a875d2a404a5a6d54f4a6f814284b0cf71acb9245239d9c5ef50ea604",
    ),
    "BaseMod.jar": (
        "1605833019",
        "c3353c10e64c621b723e9fd7d0502dfa796f828b101b68513594a5f5ef83fbaf",
    ),
    "CommunicationMod.jar": (
        "2131373661",
        "12b99249eccfd5245ddb0b6b7575e1a1dfba0ce0ed6fad5bd5bbd4a303897ef5",
    ),
}


def sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def windows_path(path: Path) -> str:
    return subprocess.check_output(["wslpath", "-w", str(path.resolve())], text=True).strip()


def communication_config() -> Path:
    output = subprocess.check_output(
        [str(WINDOWS_PYTHON), "-c", "import os; print(os.environ['LOCALAPPDATA'])"],
        text=True,
        timeout=10,
    ).strip()
    local = subprocess.check_output(["wslpath", "-u", output], text=True).strip()
    return Path(local) / "ModTheSpire/CommunicationMod/config.properties"


def prepare_runtime(host: str, port: int, *, timeout: float = 120) -> dict:
    """Verify pinned jars, deploy scripts, and configure the authorized game bridge."""
    if any(character.isspace() for character in host) or not 0 < port < 65536:
        raise ValueError("invalid bridge address")
    source_root = Path(__file__).resolve().parents[2]
    mods_dir = RUNTIME_DIR / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)
    game_mods = GAME_DIR / "mods"
    game_mods.mkdir(exist_ok=True)
    hashes = {}
    # MTS can prefer newer Workshop versions, so validate those on every launch too.
    for name, (workshop_id, expected) in PINS.items():
        original = WORKSHOP_DIR / workshop_id / name
        actual = sha256(original)
        if actual != expected:
            raise RuntimeError(f"Workshop hash changed for {name}: {actual}")
        pinned = mods_dir / name
        if not pinned.exists():
            shutil.copy2(original, pinned)
        if sha256(pinned) != expected:
            raise RuntimeError(f"Pinned hash mismatch: {pinned}")
        if name != "ModTheSpire.jar":
            target = game_mods / name
            if target.exists() and sha256(target) != expected:
                raise RuntimeError(f"Existing game mod differs; refusing overwrite: {target}")
            if not target.exists():
                shutil.copy2(pinned, target)
        hashes[name] = actual
    for script in ("windows_relay.py", "windows_game.py"):
        shutil.copy2(source_root / "scripts" / script, RUNTIME_DIR / script)
    config = communication_config()
    config.parent.mkdir(parents=True, exist_ok=True)
    backup = config.with_suffix(".properties.pre-spire-agent")
    if config.exists() and not backup.exists():
        shutil.copy2(config, backup)
    content = (
        "# Managed by spire.runtime; original saved beside this file if present.\n"
        "runAtGameStart=true\n"
        "maxInitializationTimeout=30\n"
        "command=C:/Python313/python.exe C:/spire-agent/windows_relay.py "
        f"--host {host} --port {port} --timeout {timeout}\n"
    )
    temporary = config.with_suffix(".properties.tmp")
    temporary.write_text(content, encoding="ascii")
    os.replace(temporary, config)
    return {"mods": hashes, "config": str(config), "runtime": str(RUNTIME_DIR)}


class OwnedGame:
    """A game process with a Windows-side watchdog and controller-lifetime cleanup."""

    def __init__(self, log_path: Path, *, timeout: float = 600):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        # Windows writes logs to the local runtime folder; copy the final log to evidence.
        self.log_path = log_path
        self.windows_log = RUNTIME_DIR / f"game-{os.getpid()}.log"
        self.timeout = timeout
        self.process = None
        self.info = None

    def __enter__(self):
        command = [
            str(WINDOWS_PYTHON),
            str(RUNTIME_DIR / "windows_game.py"),
            "--game-dir",
            windows_path(GAME_DIR),
            "--loader",
            "C:/spire-agent/mods/ModTheSpire.jar",
            "--log",
            windows_path(self.windows_log),
            "--timeout",
            str(self.timeout),
        ]
        # Python.exe needs a Windows script path even though its executable is a WSL path.
        command[1] = "C:/spire-agent/windows_game.py"
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            readable, _, _ = select.select([self.process.stdout], [], [], 15)
            if not readable:
                raise TimeoutError("Windows supervisor did not report startup within 15 seconds")
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("Windows supervisor failed: " + self.process.stderr.read())
            self.info = json.loads(line)
            return self
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self.process is not None:
            try:
                self.process.communicate("stop\n", timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.communicate(timeout=5)
            if self.windows_log.exists():
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.windows_log, self.log_path)
            self.process = None

    def __exit__(self, *_):
        self.close()
