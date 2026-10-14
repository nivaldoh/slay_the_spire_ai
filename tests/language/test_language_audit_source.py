"""The SFT audit compares training fingerprints with the same committed files."""

import importlib.util
import subprocess

import pytest

pytest.importorskip("torch")

from gameai import provenance  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "audit_language_source_script", provenance.REPO_ROOT / "scripts/audit_language_training.py"
)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_archived_source_covers_every_fingerprinted_file(tmp_path, monkeypatch):
    # WH3 ships Lua scripts and assets under src/; training fingerprints them too.
    for name in ("src/game/mod/battle.lua", "src/game/assets/blank.ca_vp8", "src/spire/a.py",
                 "scripts/tool.py", "configs/game/prompt.md", "pyproject.toml", "uv.lock",
                 ".python-version", "docs/notes.md"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(name)
    git = ["git", "-C", str(tmp_path), "-c", "user.name=test", "-c", "user.email=test@example",
           "-c", "commit.gpgsign=false"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "source"], check=True)
    monkeypatch.setattr(provenance, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)

    archived = audit.archived_source("HEAD")

    assert archived == provenance.source_fingerprints()
    assert "src/game/mod/battle.lua" in archived and "docs/notes.md" not in archived
