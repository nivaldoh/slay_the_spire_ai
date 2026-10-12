"""Source provenance for attributable evidence.

Every game launch records the committed revision and a hash of each implementation
file, and refuses to start while files under ``SOURCE_PATHS`` have uncommitted edits.
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


def source_fingerprints() -> dict[str, str]:
    paths = list((REPO_ROOT / "src").rglob("*.py")) + list((REPO_ROOT / "scripts").rglob("*.py"))
    paths += [path for path in (REPO_ROOT / "configs").rglob("*") if path.is_file()]
    paths += [REPO_ROOT / name for name in ("pyproject.toml", "uv.lock", ".python-version")]
    return {str(path.relative_to(REPO_ROOT)): sha256(path) for path in sorted(paths)}


def committed_revision(purpose: str) -> str:
    """HEAD of a clean checkout; refuses uncommitted implementation edits."""
    status = git("status", "--porcelain", "--", *SOURCE_PATHS)
    if status:
        raise ValueError(f"Commit implementation changes before {purpose}: {status}")
    return git("rev-parse", "HEAD").strip()
