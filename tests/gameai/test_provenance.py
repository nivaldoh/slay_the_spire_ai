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
