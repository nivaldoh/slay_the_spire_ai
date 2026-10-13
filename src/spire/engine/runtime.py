"""Windows game setup and process ownership from WSL."""

import functools
import ipaddress
import json
import os
import shutil
import subprocess
from pathlib import Path

from gameai import windows
from gameai.provenance import sha256
from gameai.windows import WINDOWS_PYTHON  # noqa: F401  (re-exported for doctor and tests)

GAME_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/SlayTheSpire")
WINDOWS_GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\SlayTheSpire"
WORKSHOP_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/workshop/content/646570")
RUNTIME_DIR = Path("/mnt/c/spire-agent")
# Processes a launch refuses to overlap: the game itself, or a JVM running it.
CONFLICTS = {
    "names": ["SlayTheSpire.exe"],
    "hosts": ["java.exe", "javaw.exe"],
    "markers": ["modthespire.jar", "desktop-1.0.jar"],
}
# The exclusive runtime's fixed port, below both ephemeral ranges. The exact WSL eth0
# address bypasses Windows localhost forwarding for game runs.
BRIDGE_PORT = 19876
# Workshop item ID and SHA-256 of each pinned jar; docs/integration.md has the versions.
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


class RuntimeLock(windows.RuntimeLock):
    """One controller at a time, held around prepare_runtime and OwnedGame."""

    def __init__(self):
        super().__init__(RUNTIME_DIR)


def wsl_bridge_host() -> str:
    """Return the one private IPv4 address of active WSL eth0, queried each episode.

    WSL addresses change. Never fall back to loopback, which goes through Windows
    localhost forwarding, or bind every interface.
    """
    try:
        output = subprocess.check_output(
            ["ip", "-4", "-j", "address", "show", "dev", "eth0"],
            text=True, stderr=subprocess.PIPE, timeout=5,
        )
        (interface,) = json.loads(output)
        (address,) = [
            ipaddress.IPv4Address(item["local"])
            for item in interface["addr_info"] if item["scope"] == "global"
        ]
        private = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
        if "UP" not in interface["flags"] or not any(
            address in ipaddress.IPv4Network(network) for network in private
        ):
            raise ValueError("eth0 is down or its address is not private")
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


def mod_paths(name: str) -> list[Path]:
    """A pinned jar's Workshop original, then the copies a launch makes and uses."""
    paths = [WORKSHOP_DIR / PINS[name][0] / name, RUNTIME_DIR / "mods" / name]
    # The loader runs from RUNTIME_DIR; ModTheSpire loads the other mods from the game folder.
    if name != "ModTheSpire.jar":
        paths.append(GAME_DIR / "mods" / name)
    return paths


def prepare_runtime(host: str, port: int, *, timeout: float = 120) -> dict:
    """Verify pinned jars, deploy scripts, and configure the authorized game bridge."""
    (RUNTIME_DIR / "mods").mkdir(parents=True, exist_ok=True)
    (GAME_DIR / "mods").mkdir(exist_ok=True)
    for name, (_, expected) in PINS.items():
        workshop, *copies = mod_paths(name)
        # ModTheSpire can prefer a newer Workshop version, so check the original every launch.
        if sha256(workshop) != expected:
            raise RuntimeError(f"Workshop hash changed for {name}: {workshop}")
        for path in copies:
            if not path.exists():
                shutil.copy2(workshop, path)
            # Never overwrite a differing copy; audit a changed jar before re-pinning it.
            if sha256(path) != expected:
                raise RuntimeError(f"{path} differs from the pinned {name}; refusing overwrite")
    shutil.copy2(Path(__file__).with_name("windows_relay.py"), RUNTIME_DIR / "windows_relay.py")
    supervisor = Path(windows.__file__).with_name("windows_game.py")
    shutil.copy2(supervisor, RUNTIME_DIR / "windows_game.py")
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
        "mods": {name: expected for name, (_, expected) in PINS.items()},
        "config": str(config),
        "runtime": str(RUNTIME_DIR),
        "relay": {"host": host, "port": port, "timeout": timeout},
    }


class OwnedGame(windows.OwnedGame):
    """The modded JVM under the Windows supervisor, plus this launch's relay stderr."""

    def __init__(self, log_path: Path, *, timeout: float = 600):
        command = [
            WINDOWS_GAME_DIR + r"\jre\bin\java.exe", "-Xmx1G", "-Dfile.encoding=UTF-8",
            "-jar", "C:/spire-agent/mods/ModTheSpire.jar",
            "--skip-launcher", "--skip-intro", "--mods", "basemod,CommunicationMod",
        ]
        super().__init__(
            log_path, runtime_dir=RUNTIME_DIR, game_dir=WINDOWS_GAME_DIR, command=command,
            rules=CONFLICTS, timeout=timeout,
        )
        self.relay_stderr = GAME_DIR / "communication_mod_errors.log"
        self._relay_stderr_offset = None

    def __enter__(self):
        # CommunicationMod appends all relay stderr to one game-directory file.
        # Capture only this launch's suffix before a later launch can obscure it.
        exists = self.relay_stderr.exists()
        self._relay_stderr_offset = self.relay_stderr.stat().st_size if exists else 0
        return super().__enter__()

    def close(self) -> None:
        if self.process is None:
            return
        super().close()
        if self._relay_stderr_offset is not None and self.relay_stderr.exists():
            relay_stderr = self.relay_stderr.read_bytes()
            # A reset/truncated log belongs wholly to this launch.
            if len(relay_stderr) >= self._relay_stderr_offset:
                relay_stderr = relay_stderr[self._relay_stderr_offset:]
            self.log_path.with_name("communication-mod.stderr.log").write_bytes(relay_stderr)
