"""Read-only launch check and environment record; never a game launch.

Blockers are what would stop ``prepare_runtime`` or the Windows supervisor. Passing
does not prove a working bridge; only a recorded run does. Runs save this report as
``environment.json``, whose ``game.sha256`` and ``mods.<jar>.sha256`` evidence reads.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from gameai.provenance import sha256
from gameai.windows import probe
from gameai.windows_game import conflicting_games
from spire.engine import runtime


def _preferences(path: Path) -> dict | None:
    """A preferences file's JSON object, or None if it is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def collect_profile(game_dir: Path) -> dict:
    """Read only the allowlisted profile facts needed to attribute an episode."""
    preferences = game_dir / "preferences"
    slots = _preferences(preferences / "STSSaveSlots")
    slot = str((slots or {}).get("DEFAULT_SLOT", "0"))
    if slot not in {"0", "1", "2"}:
        return {"status": "unavailable", "error": "InvalidSaveSlot"}
    # Slot zero is unprefixed; the game prefixes slots 1 and 2 with their number.
    unlocks_path = preferences / (("" if slot == "0" else slot + "_") + "STSUnlockProgress")
    unlocks = _preferences(unlocks_path) or {}
    settings = _preferences(preferences / "STSGameplaySettings") or {}
    level = unlocks.get("IRONCLADUnlockLevel")
    return {
        "status": "ok" if slots is not None and level is not None else "unavailable",
        "slot": int(slot),
        "ironclad_unlock_level": level,
        "ironclad_unlock_progress": unlocks.get("IRONCLADProgress"),
        "unlock_file_sha256": sha256(unlocks_path) if unlocks_path.is_file() else None,
        "upload_data_enabled": settings.get("Upload Data"),
        "fast_mode_enabled": settings.get("Fast Mode"),
    }


def collect_diagnostics() -> dict:
    """Inspect what a launch needs without changing files, settings or processes."""
    blockers = []
    jar = runtime.GAME_DIR / "desktop-1.0.jar"
    game = {"path": str(jar), "sha256": sha256(jar) if jar.is_file() else None}
    if game["sha256"] is None:
        blockers.append(f"Game jar is missing: {jar}")
    manifest = runtime.GAME_DIR.parent.parent / "appmanifest_646570.acf"
    build = re.search(r'"buildid"\s+"(\d+)"', manifest.read_text()) if manifest.is_file() else None
    game["steam_build_id"] = build.group(1) if build else None

    mods = {}
    for name, (_, expected) in runtime.PINS.items():
        workshop, *copies = runtime.mod_paths(name)
        digest = sha256(workshop) if workshop.is_file() else None
        mods[name] = {"path": str(workshop), "sha256": digest}
        # A launch creates missing copies but refuses a changed original or a differing copy.
        if digest != expected:
            blockers.append(f"{workshop} is missing or differs from the pinned {name}")
        for path in copies:
            if path.is_file() and sha256(path) != expected:
                blockers.append(f"{path} differs from the pinned {name}")

    probes = {
        "windows_python": probe([str(runtime.WINDOWS_PYTHON), "--version"]),
        "bundled_java": probe([str(runtime.GAME_DIR / "jre/bin/java.exe"), "-version"]),
    }
    blockers += [f"{key} did not run" for key, probe in probes.items() if probe["status"] != "ok"]
    profile = collect_profile(runtime.GAME_DIR)
    if profile["status"] != "ok":
        blockers.append("The active profile's Ironclad unlock state is unreadable")
    try:
        bridge_host = runtime.wsl_bridge_host()
    except RuntimeError as exc:
        bridge_host = None
        blockers.append(str(exc))
    try:
        conflicts = conflicting_games(Path(runtime.WINDOWS_GAME_DIR), runtime.CONFLICTS)
        if conflicts:
            pids = ", ".join(str(process["ProcessId"]) for process in conflicts)
            blockers.append(f"A game or JVM is already running (PIDs {pids})")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        blockers.append(f"Cannot list Windows processes: {exc}")

    nvidia = shutil.which("nvidia-smi")
    return {
        "schema_version": 2,
        "collected_at": datetime.now(UTC).isoformat(),
        "status": "blocked" if blockers else "ready",
        "blockers": blockers,
        "game": game,
        "mods": mods,
        "profile": profile,
        "runtime": {"platform": platform.platform(), "python": platform.python_version(), **probes},
        "bridge_host": bridge_host,
        "resources": {
            "cpu_threads": os.cpu_count(),
            "memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
            "gpu": probe([nvidia, "--query-gpu=name,driver_version,memory.total",
                           "--format=csv,noheader,nounits"]) if nvidia else None,
        },
    }


def render_diagnostics(report: dict) -> str:
    lines = [f"Setup: {report['status']}", f"Game build: {report['game']['steam_build_id']}"]
    for name, mod in report["mods"].items():
        pinned = mod["sha256"] == runtime.PINS[name][1]
        lines.append(f"{name}: {'pinned hash' if pinned else 'missing or changed'}")
    lines += [f"Blocked: {blocker}" for blocker in report["blockers"]]
    return "\n".join(lines)
