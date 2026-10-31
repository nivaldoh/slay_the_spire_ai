"""Source attribution using real files and Git; never launches either game."""

import hashlib
import os
import subprocess

import pytest

from gameai import provenance


def test_fingerprints_cover_only_the_scope_and_skip_bytecode(tmp_path, monkeypatch):
    for name in ("game/a.py", "game/__pycache__/a.pyc", "game/data/notes.md", "other/b.py",
                 "uv.lock"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(name)
    monkeypatch.setattr(provenance, "REPO_ROOT", tmp_path)

    fingerprints = provenance.source_fingerprints(("game", "uv.lock", "missing"))

    assert list(fingerprints) == ["game/a.py", "game/data/notes.md", "uv.lock"]
    assert fingerprints["uv.lock"] == provenance.sha256(tmp_path / "uv.lock")


@pytest.fixture
def source_repo(tmp_path, monkeypatch):
    # Isolate Git from user hooks/signing and any enclosing repository environment.
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    def git(*args):
        return subprocess.check_output(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgSign=false",
             "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
            cwd=tmp_path, text=True, stderr=subprocess.PIPE,
        ).strip()

    git("init", "--quiet")
    for name in ("src/chosen/policy.py", "src/other/policy.py", "docs/notes.md",
                 "scripts/driver.py", "configs/setup.json", "pyproject.toml", "uv.lock",
                 ".python-version"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("original\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "Initial source")
    monkeypatch.setattr(provenance, "REPO_ROOT", tmp_path)
    return tmp_path, git("rev-parse", "HEAD"), git


def test_clean_scoped_repository_returns_its_committed_revision(source_repo):
    _, revision, _ = source_repo

    assert provenance.committed_revision("test launch", ("src/chosen", "uv.lock")) == revision


@pytest.mark.parametrize("change", [
    "edited", "staged", "deleted", "staged-deletion", "untracked", "new-directory", "renamed",
])
def test_uncommitted_scoped_files_refuse_attribution(source_repo, change):
    root, _, git = source_repo
    path = root / "src/chosen/policy.py"
    changed = "src/chosen/policy.py"
    if change in {"edited", "staged"}:
        path.write_text("changed\n")
        if change == "staged":
            git("add", changed)
    elif change in {"deleted", "staged-deletion"}:
        path.unlink()
        if change == "staged-deletion":
            git("add", "-u")
    elif change in {"untracked", "new-directory"}:
        changed = "src/chosen/new.py" if change == "untracked" else "src/chosen/new/policy.py"
        added = root / changed
        added.parent.mkdir(parents=True, exist_ok=True)
        added.write_text("new\n")
    else:
        git("mv", changed, "src/chosen/renamed.py")

    message = "Commit implementation changes before test launch"
    with pytest.raises(ValueError, match=message) as error:
        provenance.committed_revision("test launch", ("src/chosen", "uv.lock"))

    # Git may summarize a wholly untracked directory rather than listing its children.
    assert ("src/chosen/new/" if change == "new-directory" else changed) in str(error.value)


@pytest.mark.parametrize("changed", ["src/other/policy.py", "docs/notes.md", "docs/new.md"])
def test_changes_outside_explicit_scope_do_not_block_attribution(source_repo, changed):
    root, revision, _ = source_repo
    (root / changed).write_text("outside scope\n")

    assert provenance.committed_revision("test launch", ("src/chosen", "uv.lock")) == revision


def test_explicit_scope_checks_a_standalone_file_after_a_directory(source_repo):
    root, _, _ = source_repo
    (root / "uv.lock").write_text("changed dependency\n")

    with pytest.raises(ValueError, match="uv.lock"):
        provenance.committed_revision("test launch", ("src/chosen", "uv.lock"))


@pytest.mark.parametrize("changed", [
    "src/chosen/policy.py", "scripts/driver.py", "configs/setup.json", "pyproject.toml",
    "uv.lock", ".python-version",
])
def test_default_scope_refuses_source_changes(source_repo, changed):
    root, _, _ = source_repo
    path = root / changed
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("changed\n")

    with pytest.raises(ValueError, match=changed):
        provenance.committed_revision("test launch")


def test_fingerprints_follow_bytes_even_when_size_and_timestamp_match(tmp_path, monkeypatch):
    # Pattern: huggingface/datasets tests/test_fingerprint.py, test_hash_simple:
    # identical values repeat their identity; changed values do not.
    source = tmp_path / "src/policy.py"
    source.parent.mkdir()
    source.write_bytes(b"abc")
    original_stat = source.stat()
    monkeypatch.setattr(provenance, "REPO_ROOT", tmp_path)
    expected = {"src/policy.py": hashlib.sha256(b"abc").hexdigest()}

    assert provenance.source_fingerprints(("src",)) == expected
    source.write_bytes(b"def")
    os.utime(source, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    assert provenance.source_fingerprints(("src",)) == {
        "src/policy.py": hashlib.sha256(b"def").hexdigest()}

    source.write_bytes(b"abc")
    assert provenance.source_fingerprints(("src",)) == expected
