"""Source provenance for attributable evidence.

Every game launch records the committed revision and a hash of each implementation
file, and refuses to start while files in its source scope have uncommitted edits.
Each game's play loop passes its own scope, so edits to the other game do not touch its
jobs. Spire's first-combat tools keep the repository-wide default, which covers every
game.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = ("src", "scripts", "configs", "pyproject.toml", "uv.lock", ".python-version")


def sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def write_json(path: Path, value: dict) -> None:
    """Replace atomically, so a reader never sees a partial document."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True)


def source_fingerprints(paths: tuple[str, ...] = SOURCE_PATHS) -> dict[str, str]:
    """A hash of every file in scope; a directory covers all files outside __pycache__."""
    files = []
    for name in paths:
        path = REPO_ROOT / name
        files += [p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
        files += [path] if path.is_file() else []
    return {str(path.relative_to(REPO_ROOT)): sha256(path) for path in sorted(files)}


def committed_revision(purpose: str, paths: tuple[str, ...] = SOURCE_PATHS) -> str:
    """HEAD of a clean checkout; refuses uncommitted edits in scope."""
    status = git("status", "--porcelain", "--", *paths)
    if status:
        raise ValueError(f"Commit implementation changes before {purpose}: {status}")
    return git("rev-parse", "HEAD").strip()
