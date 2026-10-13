"""Where the game and the harness live on Windows, and how a launch is prepared.

A launch builds the mod pack from ``src/twwarhammer3/mod`` into ``C:/wh3-agent/mods``,
writes a mod list into the game folder, copies the Windows supervisor, and starts
``Warhammer3.exe <mod list>;`` the way third-party mod managers do. The in-game
scripts stay inert unless ``C:/wh3-agent/bridge/session.json`` enables them.
"""

import functools
import re
import shutil
import subprocess
from pathlib import Path

from gameai import windows
from gameai.provenance import sha256
from gameai.windows import WINDOWS_PYTHON  # noqa: F401  (re-exported for the doctor)
from twwarhammer3.engine import pack

GAME_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Total War WARHAMMER III")
WINDOWS_GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III"
STEAM_MANIFEST = GAME_DIR.parent.parent / "appmanifest_1142710.acf"
RUNTIME_DIR = Path("/mnt/c/wh3-agent")
BRIDGE_DIR = RUNTIME_DIR / "bridge"
MOD_SOURCE = Path(__file__).resolve().parents[1] / "mod"
PACK_NAME = "twwarhammer3.pack"
MOD_LIST = "twwarhammer3_mods.txt"
# Patch 9.0 (build 4366297, 2026-10-07); docs/twwarhammer3/integration.md records the pins.
PINS = {
    "steam_build_id": "25823491",
    "Warhammer3.exe": "518c4f292f275142df13b96b9db704a3db7b4870b2c519df83d850596ecc822a",
}
CONFLICTS = {"names": ["Warhammer3.exe"]}
PREFERENCE_KEYS = (
    "gfx_fullscreen", "x_res", "y_res", "gfx_unit_size", "battle_ai_stats_modifier",
    "battle_realism_mode", "multithreaded_model_enabled",
)


def steam_build_id() -> str | None:
    if not STEAM_MANIFEST.is_file():
        return None
    match = re.search(r'"buildid"\s+"(\d+)"', STEAM_MANIFEST.read_text())
    return match.group(1) if match else None


@functools.cache
def user_dir() -> Path:
    """The game's roaming user folder, resolved once per process through Windows Python."""
    output = subprocess.check_output(
        [str(windows.WINDOWS_PYTHON), "-c", "import os; print(os.environ['APPDATA'])"],
        text=True, timeout=30,
    ).strip()
    local = subprocess.check_output(["wslpath", "-u", output], text=True).strip()
    return Path(local) / "The Creative Assembly/Warhammer3"


def preferences(path: Path | None = None) -> dict:
    """The gameplay-relevant lines of ``preferences.script.txt`` (``key value; # comment``)."""
    path = path or user_dir() / "scripts/preferences.script.txt"
    values = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"\s*(\w+)\s+(.*?);", line)
        if match and match.group(1) in PREFERENCE_KEYS:
            values[match.group(1)] = match.group(2).strip().strip('"')
    return values


def mod_files() -> dict[str, bytes]:
    return pack.files_in(MOD_SOURCE)


def mod_list_text(working_directory: str) -> str:
    return f'add_working_directory "{working_directory}";\nmod "{PACK_NAME}";\n'


def prepare_runtime() -> dict:
    """Check the build pin, build and install the pack and mod list, deploy the supervisor."""
    build = steam_build_id()
    if build != PINS["steam_build_id"]:
        raise RuntimeError(f"Steam build {build} is not the pinned {PINS['steam_build_id']}")
    mods = RUNTIME_DIR / "mods"
    mods.mkdir(parents=True, exist_ok=True)
    BRIDGE_DIR.mkdir(exist_ok=True)
    files = mod_files()
    pack.write_pack(mods / PACK_NAME, files)
    (GAME_DIR / MOD_LIST).write_text(mod_list_text(windows.windows_path(mods)), encoding="ascii")
    supervisor = Path(windows.__file__).with_name("windows_game.py")
    shutil.copy2(supervisor, RUNTIME_DIR / "windows_game.py")
    return {
        "steam_build_id": build,
        "pack": {"path": str(mods / PACK_NAME), "sha256": sha256(mods / PACK_NAME),
                 "files": sorted(files)},
        "mod_list": str(GAME_DIR / MOD_LIST),
        "runtime": str(RUNTIME_DIR),
    }


class RuntimeLock(windows.RuntimeLock):
    def __init__(self):
        super().__init__(RUNTIME_DIR)


class OwnedGame(windows.OwnedGame):
    """``Warhammer3.exe`` with the mod list, under the Windows supervisor."""

    def __init__(self, log_path: Path, *, timeout: float):
        super().__init__(
            log_path, runtime_dir=RUNTIME_DIR, game_dir=WINDOWS_GAME_DIR,
            command=[WINDOWS_GAME_DIR + r"\Warhammer3.exe", MOD_LIST + ";"],
            rules=CONFLICTS, timeout=timeout,
        )
