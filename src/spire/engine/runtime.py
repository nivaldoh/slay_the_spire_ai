"""Local Windows game setup and bounded process ownership from WSL."""

import functools
import ipaddress
import json
import math
import os
import select
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from gameai.provenance import sha256

GAME_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/SlayTheSpire")
WORKSHOP_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/workshop/content/646570")
RUNTIME_DIR = Path("/mnt/c/spire-agent")
WINDOWS_PYTHON = Path("/mnt/c/Python313/python.exe")
# The exclusive runtime's fixed port, below both ephemeral ranges. The exact WSL eth0
# address bypasses Windows localhost forwarding for game runs.
BRIDGE_PORT = 19876
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


class RuntimeLock:
    """Exclusive WSL ownership covering deployment as well as the game lifetime.

    Hold this context around prepare_runtime and OwnedGame. The kernel releases
    it if the controller dies; file existence or a remembered PID is not a lock.
    """

    def __init__(self):
        self._file = None

    def __enter__(self):
        import fcntl

        if self._file is not None:
            raise RuntimeError("runtime lock context cannot be reentered")
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self._file = (RUNTIME_DIR / "owner.lock").open("a+")
        try:
            fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._file.close()
            self._file = None
            raise RuntimeError("another controller owns the game runtime") from exc
        return self

    def __exit__(self, *_):
        if self._file is not None:
            self._file.close()
            self._file = None


def windows_path(path: Path) -> str:
    return subprocess.check_output(["wslpath", "-w", str(path.resolve())], text=True).strip()


def wsl_bridge_host() -> str:
    """Discover the current WSL NAT endpoint without using localhost forwarding.

    The supported runtime has one private global IPv4 address on active eth0.
    Reject missing or ambiguous endpoints before deployment; never fall back to
    loopback or bind every interface. Query each episode because WSL IPs change.
    """
    try:
        interfaces = json.loads(subprocess.check_output(
            ["ip", "-4", "-j", "address", "show", "dev", "eth0"],
            text=True, stderr=subprocess.PIPE, timeout=5,
        ))
        if (
            not isinstance(interfaces, list) or len(interfaces) != 1
            or interfaces[0]["ifname"] != "eth0" or "UP" not in interfaces[0]["flags"]
        ):
            raise ValueError("eth0 is absent or inactive")
        addresses = [
            item["local"] for item in interfaces[0]["addr_info"]
            if item["family"] == "inet" and item["scope"] == "global"
        ]
        if len(addresses) != 1 or not isinstance(addresses[0], str):
            raise ValueError("eth0 requires one global IPv4 address")
        address = ipaddress.IPv4Address(addresses[0])
        if not any(address in ipaddress.IPv4Network(network) for network in (
            "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        )):
            raise ValueError("eth0 requires a private NAT address")
        return str(address)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("Cannot discover one usable private IPv4 address on WSL eth0") from exc


@functools.cache
def communication_config() -> Path:
    """Resolve the per-user config path once per process.

    The Windows interop call can stall under host memory pressure; a long training
    job therefore makes it once rather than before every game.
    """
    output = subprocess.check_output(
        [str(WINDOWS_PYTHON), "-c", "import os; print(os.environ['LOCALAPPDATA'])"],
        text=True,
        timeout=30,
    ).strip()
    local = subprocess.check_output(["wslpath", "-u", output], text=True).strip()
    return Path(local) / "ModTheSpire/CommunicationMod/config.properties"


def prepare_runtime(host: str, port: int, *, timeout: float = 120) -> dict:
    """Verify pinned jars, deploy scripts, and configure the authorized game bridge."""
    if any(character.isspace() for character in host) or not 0 < port < 65536:
        raise ValueError("invalid bridge address")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
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
        shutil.copy2(Path(__file__).with_name(script), RUNTIME_DIR / script)
    config = communication_config()
    config.parent.mkdir(parents=True, exist_ok=True)
    backup = config.with_suffix(".properties.pre-spire-agent")
    if config.exists() and not backup.exists():
        shutil.copy2(config, backup)
    content = (
        "# Managed by spire.engine.runtime; original saved beside this file if present.\n"
        "runAtGameStart=true\n"
        "maxInitializationTimeout=30\n"
        "command=C:/Python313/python.exe C:/spire-agent/windows_relay.py "
        f"--host {host} --port {port} --timeout {timeout}\n"
    )
    temporary = config.with_suffix(".properties.tmp")
    temporary.write_text(content, encoding="ascii")
    os.replace(temporary, config)
    return {
        "mods": hashes,
        "config": str(config),
        "runtime": str(RUNTIME_DIR),
        "relay": {"host": host, "port": port, "timeout": timeout},
    }


class OwnedGame:
    """A game process with a Windows-side watchdog and controller-lifetime cleanup."""

    def __init__(self, log_path: Path, *, timeout: float = 600):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive and finite")
        # Windows writes logs to the local runtime folder; copy the final log to evidence.
        self.log_path = log_path
        self.windows_log = RUNTIME_DIR / f"game-{os.getpid()}-{uuid.uuid4().hex}.log"
        self.timeout = timeout
        self.process = None
        self.info = None
        self._entered = False
        self.supervisor_stderr = ""
        self.relay_stderr = GAME_DIR / "communication_mod_errors.log"
        self._relay_stderr_offset = None

    def __enter__(self):
        if self._entered:
            raise RuntimeError("OwnedGame contexts cannot be reused")
        self._entered = True
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
        # CommunicationMod appends all relay stderr to one game-directory file.
        # Capture only this launch's suffix before a later launch can obscure it.
        self._relay_stderr_offset = (
            self.relay_stderr.stat().st_size if self.relay_stderr.exists() else 0
        )
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.info = self._startup_message()
            if not isinstance(self.info, dict) or not isinstance(self.info.get("pid"), int):
                raise RuntimeError("Windows supervisor returned an invalid startup message")
            return self
        except BaseException as exc:
            self.close()
            if isinstance(exc, Exception) and self.supervisor_stderr.strip():
                raise RuntimeError(f"{exc}: {self.supervisor_stderr.strip()}") from exc
            raise

    def _startup_message(self, timeout: float = 15) -> dict:
        """Bound the complete handshake, including malformed partial output."""
        deadline = time.monotonic() + timeout
        line = bytearray()
        while b"\n" not in line:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Windows supervisor did not report startup before deadline")
            readable, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not readable:
                raise TimeoutError("Windows supervisor did not report startup before deadline")
            chunk = os.read(self.process.stdout.fileno(), 4096)
            if not chunk:
                # Do not block reading stderr from a process which only closed stdout.
                raise RuntimeError("Windows supervisor closed stdout before reporting startup")
            line.extend(chunk)
            if len(line) > 65536:
                raise RuntimeError("Windows supervisor startup message exceeds byte limit")
        return json.loads(line.split(b"\n", 1)[0])

    def close(self) -> None:
        if self.process is not None:
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
                if self._relay_stderr_offset is not None and self.relay_stderr.exists():
                    with self.relay_stderr.open("rb") as source:
                        # A reset/truncated log belongs wholly to this launch.
                        if self.relay_stderr.stat().st_size >= self._relay_stderr_offset:
                            source.seek(self._relay_stderr_offset)
                        self.log_path.with_name("communication-mod.stderr.log").write_bytes(
                            source.read()
                        )
                if self.supervisor_stderr:
                    self.log_path.with_name("supervisor.stderr.log").write_text(
                        self.supervisor_stderr
                    )

    def __exit__(self, *_):
        self.close()
