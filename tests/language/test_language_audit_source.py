"""The SFT audit compares training fingerprints with the same committed files."""

import hashlib
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


def test_archived_source_uses_the_requested_commit_despite_later_changes(tmp_path, monkeypatch):
    # The audit contract compares fingerprints to the saved revision, not today's checkout
    # (docs/spire/first-combat/language-training.md, stopped-run audit).
    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(tmp_path), "-c", "user.name=test", "-c",
             "user.email=test@example", "-c", "commit.gpgsign=false", *args],
            text=True,
        ).strip()

    first = {"src/shared.py": b"original\n", "src/removed.bin": b"\x00\xff\r\n"}
    second = {"src/shared.py": b"next version\n", "src/added.bin": b"\xfe\x00\n"}
    (tmp_path / "src").mkdir()
    git("init", "-q")
    revisions = []
    for snapshot in (first, second):
        for path in (tmp_path / "src").iterdir():
            path.unlink()
        for name, data in snapshot.items():
            (tmp_path / name).write_bytes(data)
        git("add", "-A")
        git("commit", "-q", "-m", "source snapshot")
        revisions.append(git("rev-parse", "HEAD"))

    (tmp_path / "src/shared.py").write_bytes(b"uncommitted changes\n")
    (tmp_path / "src/added.bin").unlink()
    (tmp_path / "src/untracked.py").write_bytes(b"new, never committed\n")
    monkeypatch.setattr(audit, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(provenance, "REPO_ROOT", tmp_path)

    for revision, snapshot in zip(revisions, (first, second), strict=True):
        assert audit.archived_source(revision) == {
            name: hashlib.sha256(data).hexdigest() for name, data in snapshot.items()
        }
