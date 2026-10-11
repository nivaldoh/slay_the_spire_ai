"""Read-only setup diagnostics; file availability is not an engine integration test."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Workshop artifacts inspected on 2026-10-11; see docs/state.md for provenance.
PINNED_MODS = {
    "ModTheSpire.jar": {
        "version": "3.30.3",
        "sha256": "541b5e8a875d2a404a5a6d54f4a6f814284b0cf71acb9245239d9c5ef50ea604",
    },
    "BaseMod.jar": {
        "version": "5.56.0",
        "sha256": "c3353c10e64c621b723e9fd7d0502dfa796f828b101b68513594a5f5ef83fbaf",
    },
    "CommunicationMod.jar": {
        "version": "1.2.1",
        "sha256": "12b99249eccfd5245ddb0b6b7575e1a1dfba0ce0ed6fad5bd5bbd4a303897ef5",
    },
}


def _drive_root() -> Path:
    return Path(os.environ.get("SystemDrive", "C:") + "/") if os.name == "nt" else Path("/mnt/c")


def _probe(command: list[str]) -> dict[str, Any]:
    """Run a bounded, read-only version/resource probe, never a game launch."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "error": type(exc).__name__}
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "output": (result.stdout or result.stderr).strip()[:4096],
    }


def _file_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if not info["exists"]:
        return info
    try:
        with path.open("rb") as stream:
            info["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        info["size_bytes"] = path.stat().st_size
    except OSError as exc:
        info["error"] = type(exc).__name__
    return info


def _jar_info(path: Path, expected: dict[str, str]) -> dict[str, Any]:
    info = _file_info(path)
    info["expected"] = dict(expected)
    info["hash_matches"] = info.get("sha256") == expected["sha256"]
    if not info["exists"] or "error" in info:
        return info
    try:
        with zipfile.ZipFile(path) as jar:
            metadata = json.loads(jar.read("ModTheSpire.json"))
            if not isinstance(metadata, dict):
                raise ValueError("Mod descriptor is not an object")
            for key in ("modid", "version", "sts_version", "mts_version"):
                if key in metadata:
                    info[key] = metadata[key]
            if path.name == "ModTheSpire.jar":
                properties = jar.read("META-INF/version.prop").decode("utf-8")
                match = re.search(r"^version\s*=\s*(\S+)", properties, flags=re.MULTILINE)
                if match:
                    info["version"] = match.group(1)
    except (OSError, KeyError, ValueError, UnicodeError, zipfile.BadZipFile) as exc:
        info["metadata_error"] = type(exc).__name__
    info["version_matches"] = info.get("version") == expected["version"]
    return info


def _json_preferences(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}, "InvalidObject"
        return data, None
    except (OSError, ValueError, UnicodeError) as exc:
        return {}, type(exc).__name__


def _profile(game_dir: Path) -> dict[str, Any]:
    preferences = game_dir / "preferences"
    slots, slots_error = _json_preferences(preferences / "STSSaveSlots")
    slot = str(slots.get("DEFAULT_SLOT", "0"))
    # Slot zero is unprefixed; the game prefixes slots 1 and 2 with their number.
    prefix = "" if slot == "0" else slot + "_"
    if slot not in {"0", "1", "2"}:
        return {"status": "unavailable", "error": "InvalidSaveSlot"}
    unlocks_path = preferences / (prefix + "STSUnlockProgress")
    unlocks, unlocks_error = _json_preferences(unlocks_path)
    settings, settings_error = _json_preferences(preferences / "STSGameplaySettings")
    result: dict[str, Any] = {
        "status": "ok" if not slots_error and not unlocks_error else "unavailable",
        "slot": int(slot),
        "ironclad_unlock_level": unlocks.get("IRONCLADUnlockLevel"),
        "ironclad_unlock_progress": unlocks.get("IRONCLADProgress"),
        "unlock_file_sha256": _file_info(unlocks_path).get("sha256"),
        "upload_data_enabled": settings.get("Upload Data"),
        "fast_mode_enabled": settings.get("Fast Mode"),
        "modded_upload_behavior": "unverified",
    }
    errors = [error for error in (slots_error, unlocks_error, settings_error) if error]
    if errors:
        result["errors"] = errors
    if result["ironclad_unlock_level"] is None:
        result["status"] = "unavailable"
    return result


def _configuration_paths() -> list[Path]:
    override = os.environ.get("SPIRE_COMMUNICATION_CONFIG")
    if override:
        return [Path(override)]
    paths = []
    if os.environ.get("LOCALAPPDATA"):
        paths.append(Path(os.environ["LOCALAPPDATA"]) / "ModTheSpire")
    if os.name != "nt":
        paths.extend((_drive_root() / "Users").glob("*/AppData/Local/ModTheSpire"))
    return [path / "CommunicationMod" / "config.properties" for path in paths]


def _configuration() -> dict[str, Any]:
    paths = _configuration_paths()
    entries = []
    for path in paths:
        entry: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
        if entry["exists"]:
            try:
                content = path.read_text(encoding="utf-8")
                # Report presence only: commands may contain credentials or private paths.
                match = re.search(r"^\s*command\s*[=:]\s*(.*)$", content, flags=re.MULTILINE)
                entry["command_configured"] = bool(match and match.group(1).strip())
            except (OSError, UnicodeError) as exc:
                entry["error"] = type(exc).__name__
        entries.append(entry)
    return {
        "candidates": entries,
        "present": any(entry["exists"] for entry in entries),
        "command_configured": any(entry.get("command_configured", False) for entry in entries),
        "command_execution": "unverified",
    }


def _resources(game_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"cpu_threads": os.cpu_count()}
    try:
        memory = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                memory[key] = int(value.split()[0]) * 1024
        result["memory_bytes"] = memory
    except (OSError, ValueError):
        result["memory_bytes"] = None
    result["disk"] = {}
    for name, path in (("workspace", Path.cwd()), ("game", game_dir)):
        try:
            usage = shutil.disk_usage(path)
            result["disk"][name] = {"total_bytes": usage.total, "free_bytes": usage.free}
        except OSError:
            result["disk"][name] = {"status": "unavailable"}
    nvidia = shutil.which("nvidia-smi")
    result["gpu"] = (
        _probe(
            [
                nvidia,
                "--query-gpu=name,driver_version,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ]
        )
        if nvidia
        else {"status": "unavailable"}
    )
    return result


def _processes() -> dict[str, Any]:
    tasklist = _drive_root() / "Windows/System32/tasklist.exe"
    if not tasklist.is_file():
        return {"status": "unavailable", "reason": "Windows tasklist is unavailable"}
    entries = []
    failures = []
    # Keep process command lines and unrelated processes out of diagnostics.
    for executable in ("steam.exe", "SlayTheSpire.exe", "java.exe", "javaw.exe"):
        result = _probe([str(tasklist), "/FO", "CSV", "/NH", "/FI", f"IMAGENAME eq {executable}"])
        if result["status"] != "ok":
            failures.append(executable)
            continue
        for row in csv.reader(io.StringIO(result["output"])):
            if len(row) >= 2 and row[0].lower() == executable.lower():
                entries.append({"name": row[0], "pid": row[1]})
    return {
        "status": "partial" if failures else "ok",
        "entries": entries,
        "failed_queries": failures,
        "java_processes_are_not_proof_of_game": True,
    }


def collect_diagnostics(game_dir: Path | None = None, mods_dir: Path | None = None) -> dict:
    """Inspect setup without changing files, settings, or launching the game.

    SPIRE_GAME_DIR, SPIRE_MODS_DIR, SPIRE_WINDOWS_PYTHON, and
    SPIRE_COMMUNICATION_CONFIG can override the local Windows/WSL defaults.
    A successful report means prerequisites are ready for a runtime probe, not
    that a bridge handshake, combat, or deterministic reset has been verified.
    """
    drive = _drive_root()
    game_dir = Path(
        game_dir
        or os.environ.get(
            "SPIRE_GAME_DIR", drive / "Program Files (x86)/Steam/steamapps/common/SlayTheSpire"
        )
    )
    mods_dir = Path(mods_dir or os.environ.get("SPIRE_MODS_DIR", drive / "spire-agent/mods"))
    windows_python = Path(os.environ.get("SPIRE_WINDOWS_PYTHON", drive / "Python313/python.exe"))
    java = game_dir / "jre/bin/java.exe"
    runtime = {
        "platform": platform.platform(),
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "windows_python": {
            "path": str(windows_python),
            **_probe([str(windows_python), "--version"]),
        },
        "bundled_java": {"path": str(java), **_probe([str(java), "-version"])},
    }
    game = _file_info(game_dir / "desktop-1.0.jar")
    steam_manifest = game_dir.parent.parent / "appmanifest_646570.acf"
    try:
        match = re.search(r'"buildid"\s+"(\d+)"', steam_manifest.read_text(encoding="utf-8"))
        game["steam_build_id"] = match.group(1) if match else None
    except (OSError, UnicodeError):
        game["steam_build_id"] = None
    mods = {name: _jar_info(mods_dir / name, expected) for name, expected in PINNED_MODS.items()}
    profile = _profile(game_dir)
    configuration = _configuration()
    blockers = []

    def block(code: str, message: str, remediation: str) -> None:
        blockers.append({"code": code, "message": message, "remediation": remediation})

    if not game["exists"] or "error" in game:
        block(
            "game_unavailable",
            "Game jar is missing or unreadable.",
            "Set SPIRE_GAME_DIR to the existing Steam SlayTheSpire directory.",
        )
    for name, info in mods.items():
        if not info["exists"]:
            block(
                "mod_missing",
                f"Pinned {name} is missing.",
                f"Copy the documented Workshop artifact to {mods_dir / name}.",
            )
        elif not info["hash_matches"]:
            block(
                "mod_hash_mismatch",
                f"{name} differs from the recorded artifact.",
                "Restore the pinned jar or audit the update before changing its expected hash.",
            )
        elif not info.get("version_matches", False):
            block(
                "mod_version_unverified",
                f"Could not verify {name}'s embedded version.",
                "Inspect the jar metadata and confirm the documented mod version.",
            )
    for key, label in (("windows_python", "Windows Python"), ("bundled_java", "Bundled Java")):
        if runtime[key]["status"] != "ok":
            block(
                f"{key}_unavailable",
                f"{label} did not execute its version command.",
                "Check the executable path and Windows interop from the current runtime.",
            )
    if profile["status"] != "ok":
        block(
            "profile_unverified",
            "The active profile's Ironclad unlock state is unavailable.",
            "Inspect STSSaveSlots and the active slot's STSUnlockProgress before collecting runs.",
        )
    if not configuration["command_configured"]:
        block(
            "communication_command_missing",
            "No readable CommunicationMod command is configured.",
            "Configure the relay command; use SPIRE_COMMUNICATION_CONFIG for a custom config path.",
        )

    return {
        "schema_version": 1,
        "collected_at": datetime.now(UTC).isoformat(),
        "status": "blocked" if blockers else "ready_for_probe",
        "runtime": runtime,
        "resources": _resources(game_dir),
        "game": game,
        "mods": mods,
        "profile": profile,
        "configuration": configuration,
        "processes": _processes(),
        "capabilities": {
            "game_files_available": game["exists"] and "error" not in game,
            "pinned_mods_verified": all(
                info.get("hash_matches") and info.get("version_matches") for info in mods.values()
            ),
            "original_engine_bridge": "unverified",
            "combat_completion": "unverified",
            "deterministic_reset": "unverified",
        },
        "blockers": blockers,
        "required_verifications": [
            "Observe the CommunicationMod readiness handshake and live game state.",
            "Complete and record an original-engine combat and a second seeded episode.",
            "Replay a fixed seed and action prefix to check deterministic reset.",
        ],
    }


def exit_code(report: dict) -> int:
    """Zero means setup prerequisites pass; runtime capabilities remain unverified."""
    return 1 if report["blockers"] else 0


def render_diagnostics(report: dict) -> str:
    lines = [
        f"Setup: {report['status']}",
        "Original-engine bridge: unverified (read-only inspection)",
    ]
    for name, mod in report["mods"].items():
        lines.append(
            f"{name}: version={mod.get('version', 'unknown')} "
            f"pinned_hash={'match' if mod['hash_matches'] else 'not verified'}"
        )
    for blocker in report["blockers"]:
        lines.append(f"[{blocker['code']}] {blocker['message']} {blocker['remediation']}")
    return "\n".join(lines)
