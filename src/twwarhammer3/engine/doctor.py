"""Read-only launch check and environment record; never a game launch.

Blockers are what would stop ``prepare_runtime`` or the Windows supervisor. Jobs save
this report as ``environment.json``.
"""

import os
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from gameai.provenance import sha256
from gameai.windows import probe
from gameai.windows_game import conflicting_games
from twwarhammer3.engine import runtime, startup


def collect_diagnostics() -> dict:
    blockers = []
    exe = runtime.GAME_DIR / "Warhammer3.exe"
    game = {
        "path": str(exe),
        "sha256": sha256(exe) if exe.is_file() else None,
        "steam_build_id": runtime.steam_build_id(),
    }
    if game["sha256"] != runtime.PINS["Warhammer3.exe"]:
        blockers.append("Warhammer3.exe is missing or differs from the pinned hash")
    if game["steam_build_id"] != runtime.PINS["steam_build_id"]:
        blockers.append(f"Steam build {game['steam_build_id']} is not the pinned build")
    probes = {"windows_python": probe([str(runtime.WINDOWS_PYTHON), "--version"])}
    blockers += [f"{key} did not run" for key, item in probes.items() if item["status"] != "ok"]
    try:
        preferences = runtime.preferences()
    except (OSError, subprocess.SubprocessError) as exc:
        preferences = None
        blockers.append(f"Cannot read the game preferences: {exc}")
    try:
        startup_status = startup.status(
            runtime.GAME_DIR, runtime.user_dir() / "scripts/preferences.script.txt"
        )
    except (OSError, subprocess.SubprocessError) as exc:
        startup_status = {"enabled": False, "error": str(exc)}
        blockers.append(f"Cannot inspect the startup skip: {exc}")
    try:
        conflicts = conflicting_games(Path(runtime.WINDOWS_GAME_DIR), runtime.CONFLICTS)
        if conflicts:
            pids = ", ".join(str(process["ProcessId"]) for process in conflicts)
            blockers.append(f"The game is already running (PIDs {pids})")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        blockers.append(f"Cannot list Windows processes: {exc}")
    mod_log = runtime.GAME_DIR / "lua_mod_log.txt"
    files = sorted(runtime.mod_files())
    nvidia = shutil.which("nvidia-smi")
    return {
        "schema_version": 1,
        "collected_at": datetime.now(UTC).isoformat(),
        "status": "blocked" if blockers else "ready",
        "blockers": blockers,
        "game": game,
        "preferences": preferences,
        "startup": startup_status,
        "mod": {
            "files": files,
            "seen_in_mod_log": mod_log.is_file() and "twwarhammer3" in mod_log.read_text(
                errors="replace"
            ),
        },
        "runtime": {"platform": platform.platform(), "python": platform.python_version(), **probes},
        "resources": {
            "cpu_threads": os.cpu_count(),
            "memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
            "gpu": probe([nvidia, "--query-gpu=name,driver_version,memory.total",
                          "--format=csv,noheader,nounits"]) if nvidia else None,
        },
    }


def render_diagnostics(report: dict) -> str:
    lines = [f"Setup: {report['status']}", f"Game build: {report['game']['steam_build_id']}"]
    if report["preferences"]:
        lines.append("Preferences: " + ", ".join(
            f"{key}={value}" for key, value in sorted(report["preferences"].items())
        ))
    lines.append(f"Mod files: {', '.join(report['mod']['files'])}")
    startup_status = report["startup"]
    lines.append("Startup skip: " + ("installed (all launches)" if startup_status["enabled"]
                                    else "needs preparation"))
    if "pack" in startup_status:
        lines.append(f"Startup pack: {startup_status['pack']['path']} "
                     f"(sha256={startup_status['pack']['sha256'] or 'missing'})")
    lines += [f"Blocked: {blocker}" for blocker in report["blockers"]]
    return "\n".join(lines)
