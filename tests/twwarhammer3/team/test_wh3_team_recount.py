"""Offline team-check provenance and launch guards; no live movement is exercised."""
import hashlib
import importlib.util
import json
from pathlib import Path

import check_wh3_team as check
import pytest

from gameai.windows_game import is_game_process


def test_recount_is_read_only_and_saved_verdict_identifies_the_bytes_it_read(tmp_path, monkeypatch):
    evidence = tmp_path / "live"
    evidence.mkdir()
    original = {"checks.json": b'{"passed": false, "original": true}\n',
                "plan.json": b'{"check_sha256": "original-checker"}\n'}
    for index in range(1, 5):
        original.update({
            f"probe-{index}/episode/trace.jsonl": b'{ "kind": "test-event" }\n',
            f"probe-{index}/observations.jsonl": b'{ "observation": "test-sample" }\n',
            f"probe-{index}/manifest.json":
                b'{"closed": true, "remaining_pids": [], "result": {"status": "truncated"}}\n',
        })
    for relative, payload in original.items():
        path = evidence / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def assess(events, samples, slow):
        # Substitute only the movement judgement; this test exercises the saved-file boundary.
        assert events == [{"kind": "test-event"}]
        assert samples == [{"observation": "test-sample"}]
        assert slow in ("infantry", "cavalry")
        return {"passed": True, "reason": "test witness"}

    monkeypatch.setattr(check, "assess", assess)
    results = check.recount(evidence)
    assert len(results) == 4 and all(row["passed"] for row in results)
    assert {str(p.relative_to(evidence)): p.read_bytes() for p in evidence.rglob("*")
            if p.is_file()} == original

    destination = tmp_path / "recount.json"
    assert check.recount(evidence, destination=destination) == results
    saved = json.loads(destination.read_bytes())
    assert saved["passed"] and saved["probes"] == results
    assert saved["evidence"] == {
        "directory": str(evidence.resolve()),
        "files": {relative: hashlib.sha256(payload).hexdigest()
                  for relative, payload in original.items() if relative != "checks.json"},
    }
    assert saved["checker"]["path"] == str(Path(check.__file__).resolve())
    assert saved["checker"]["sha256"] == (
        hashlib.sha256(Path(check.__file__).read_bytes()).hexdigest())
    assert saved["checker"]["revision"]
    with pytest.raises(FileExistsError):
        check.recount(evidence, destination=evidence / "checks.json")
    assert {str(p.relative_to(evidence)): p.read_bytes() for p in evidence.rglob("*")
            if p.is_file()} == original


def test_recount_keeps_missing_evidence_failed_and_records_what_was_missing(tmp_path):
    evidence = tmp_path / "incomplete"
    evidence.mkdir()
    destination = tmp_path / "recount.json"

    results = check.recount(evidence, destination=destination)

    assert len(results) == 4 and not any(row["passed"] for row in results)
    assert all("FileNotFoundError" in row["reason"] for row in results)
    assert list(evidence.iterdir()) == []
    saved = json.loads(destination.read_bytes())
    assert saved["passed"] is False
    assert saved["evidence"]["files"] == {
        "plan.json": None,
        **{f"probe-{i}/episode/trace.jsonl": None for i in range(1, 5)},
    }


def test_recount_identifies_a_saved_copy_of_the_checker(tmp_path):
    # Running an old checker must identify that copy, not the current canonical path.
    payload = Path(check.__file__).read_bytes() + b"\n# A distinct saved checker.\n"
    path = tmp_path / "saved_checker.py"
    path.write_bytes(payload)
    spec = importlib.util.spec_from_file_location("saved_checker", path)
    copied = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(copied)
    destination = tmp_path / "recount.json"

    copied.recount(tmp_path / "missing", destination=destination)

    identity = json.loads(destination.read_bytes())["checker"]
    assert identity["path"] == str(path.resolve())
    assert identity["sha256"] == hashlib.sha256(payload).hexdigest()


def test_live_team_check_recognizes_a_spire_jvm_by_its_windows_directory(tmp_path, monkeypatch):
    process = {"Name": "java.exe", "CommandLine": "java.exe -jar launcher.jar",
               "ExecutablePath": check.spire_runtime.WINDOWS_GAME_DIR + r"\jre\bin\java.exe"}

    def conflicts(directory, rules):
        return [process] if is_game_process(process, directory, rules) else []

    monkeypatch.setattr(check, "committed_revision", lambda *args: "test-revision")
    monkeypatch.setattr(check, "source_fingerprints", lambda *args: {})
    monkeypatch.setattr(check, "collect_diagnostics", lambda: {
        "blockers": [], "warnings": [], "game": {"steam_build_id": "test-build"}})
    monkeypatch.setattr(check, "conflicting_games", conflicts)
    monkeypatch.setattr(check, "RuntimeLock", lambda: pytest.fail("must refuse before launch"))

    with pytest.raises(RuntimeError, match="Slay the Spire is running"):
        check.run(tmp_path / "check")
