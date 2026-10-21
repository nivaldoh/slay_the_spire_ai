"""Skip startup videos for every launch, including Steam, without desktop input.

The movie pack auto-loads from data/. The main cinematic remains available in the
viewer: its startup playback is disabled by the profile preference instead.
"""

import hashlib
import os
import re
from pathlib import Path

from gameai.provenance import sha256
from twwarhammer3.engine import pack

PACK_NAME = "zzz_twwarhammer3_skip_intro.pack"
ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
PREFERENCE = "fe_game_intro_video_enabled"
SETTING = re.compile(rb"(?m)^([ \t]*fe_game_intro_video_enabled[ \t]+)([^\s;]+)(?=[ \t]*;)")
LANGUAGES = ("br", "cn", "cz", "de", "en", "es", "fr", "it", "kr", "pl", "ru", "tr", "zh")


def movie_files() -> dict[str, bytes]:
    """Five splash clips and all localized warnings; deliberately excludes gam_int."""
    blank = (ASSET_DIR / "blank.ca_vp8").read_bytes()
    paths = [f"movies\\startup_movie_{index:02d}.ca_vp8" for index in range(1, 6)]
    paths += [f"movies\\epilepsy_warning\\epilepsy_warning_{lang}.ca_vp8" for lang in LANGUAGES]
    return dict.fromkeys(paths, blank)


def disable_cinematic(path: Path) -> None:
    """Set the setting to false, appending it when absent; other bytes and newlines stay."""
    original = path.read_bytes()
    updated, count = SETTING.subn(rb"\g<1>false", original)
    if not count:
        newline = b"\r\n" if b"\r\n" in original else b"\n"
        separator = b"" if not original or original.endswith(b"\n") else newline
        updated = original + separator + PREFERENCE.encode() + b" false;" + newline
    if updated != original:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(updated)
        os.replace(temporary, path)


def status(game_dir: Path, preferences_path: Path) -> dict:
    """Read-only evidence of the installed pack and effective cinematic preference."""
    path = game_dir / "data" / PACK_NAME
    files = movie_files()
    expected = hashlib.sha256(pack.pack_bytes(files, pack_type=pack.MOVIE)).hexdigest()
    installed = sha256(path) if path.is_file() else None
    settings = list(SETTING.finditer(preferences_path.read_bytes()))
    value = settings[-1].group(2).decode("utf-8", "replace") if settings else None
    return {
        "enabled": installed == expected and value == "false",
        "pack": {"path": str(path), "sha256": installed, "expected_sha256": expected,
                 "files": sorted(files)},
        "preferences_path": str(preferences_path),
        PREFERENCE: value,
    }


def install(game_dir: Path, preferences_path: Path) -> dict:
    """Install while stopped; the caller checks processes and holds the runtime lock."""
    disable_cinematic(preferences_path)
    pack.write_pack(game_dir / "data" / PACK_NAME, movie_files(), pack_type=pack.MOVIE)
    return status(game_dir, preferences_path)
