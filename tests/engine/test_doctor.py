import hashlib
import json
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from spire.engine import doctor


@pytest.fixture
def setup(tmp_path, monkeypatch):
    game = tmp_path / "game"
    mods = tmp_path / "mods"
    preferences = game / "preferences"
    preferences.mkdir(parents=True)
    mods.mkdir()
    (game / "desktop-1.0.jar").write_bytes(b"test game; not original engine evidence")
    (preferences / "STSSaveSlots").write_text(json.dumps({"DEFAULT_SLOT": "0"}))
    (preferences / "STSUnlockProgress").write_text(
        json.dumps(
            {
                "IRONCLADUnlockLevel": "3",
                "IRONCLADProgress": "817",
                "private_field": "do-not-expose",
            }
        )
    )
    (preferences / "STSGameplaySettings").write_text(
        json.dumps({"Upload Data": "true", "Fast Mode": "true", "private_setting": "do-not-expose"})
    )
    config = tmp_path / "config.properties"
    config.write_text("# local command\ncommand=python relay.py --token do-not-expose\n")
    monkeypatch.setenv("SPIRE_COMMUNICATION_CONFIG", str(config))
    monkeypatch.setenv("SPIRE_WINDOWS_PYTHON", str(tmp_path / "python.exe"))
    monkeypatch.setattr(doctor, "_probe", Mock(return_value={"status": "ok", "output": "version"}))
    monkeypatch.setattr(doctor, "_resources", lambda path: {"cpu_threads": 4})
    monkeypatch.setattr(doctor, "_processes", lambda: {"status": "ok", "entries": []})
    pins = {}
    for name, expected in doctor.PINNED_MODS.items():
        path = mods / name
        with zipfile.ZipFile(path, "w") as jar:
            jar.writestr("ModTheSpire.json", json.dumps({"version": expected["version"]}))
            if name == "ModTheSpire.jar":
                jar.writestr("META-INF/version.prop", "version=" + expected["version"] + "\r\n")
        pins[name] = {
            "version": expected["version"],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    monkeypatch.setattr(doctor, "PINNED_MODS", pins)
    return game, mods, config


def test_available_files_do_not_claim_runtime_verification(setup):
    game, mods, _ = setup
    report = doctor.collect_diagnostics(game, mods)
    assert report["schema_version"] == 1
    assert report["status"] == "ready_for_probe"
    assert report["blockers"] == []
    assert doctor.exit_code(report) == 0
    assert report["capabilities"]["pinned_mods_verified"] is True
    assert report["capabilities"]["original_engine_bridge"] == "unverified"
    assert report["capabilities"]["combat_completion"] == "unverified"
    assert report["capabilities"]["deterministic_reset"] == "unverified"
    assert "unverified" in doctor.render_diagnostics(report)
    assert json.loads(json.dumps(report)) == report


def test_same_version_with_different_hash_blocks_setup(setup):
    game, mods, _ = setup
    with zipfile.ZipFile(mods / "CommunicationMod.jar", "a") as jar:
        jar.writestr("extra.txt", "Workshop update or tampering")
    report = doctor.collect_diagnostics(game, mods)
    mod = report["mods"]["CommunicationMod.jar"]
    assert mod["version_matches"] is True
    assert mod["hash_matches"] is False
    assert report["capabilities"]["pinned_mods_verified"] is False
    assert {item["code"] for item in report["blockers"]} == {"mod_hash_mismatch"}
    assert doctor.exit_code(report) == 1


def test_missing_prerequisites_are_actionable(tmp_path, monkeypatch):
    monkeypatch.setenv("SPIRE_COMMUNICATION_CONFIG", str(tmp_path / "absent.properties"))
    monkeypatch.setattr(doctor, "_probe", lambda cmd: {"status": "unavailable"})
    monkeypatch.setattr(doctor, "_resources", lambda path: {})
    monkeypatch.setattr(doctor, "_processes", lambda: {"status": "unavailable"})
    report = doctor.collect_diagnostics(tmp_path / "game", tmp_path / "mods")
    assert report["status"] == "blocked"
    codes = {item["code"] for item in report["blockers"]}
    assert codes == {
        "game_unavailable",
        "mod_missing",
        "windows_python_unavailable",
        "bundled_java_unavailable",
        "profile_unverified",
        "communication_command_missing",
    }
    assert all(item["remediation"] for item in report["blockers"])


def test_read_only_report_excludes_private_preferences_and_command(setup):
    game, mods, config = setup
    files = [*game.rglob("*"), *mods.rglob("*"), config]
    before = {str(path): path.read_bytes() for path in files if path.is_file()}
    report = doctor.collect_diagnostics(game, mods)
    assert "do-not-expose" not in json.dumps(report)
    assert report["profile"]["ironclad_unlock_level"] == "3"
    assert report["profile"]["upload_data_enabled"] == "true"
    assert report["profile"]["modded_upload_behavior"] == "unverified"
    assert before == {name: Path(name).read_bytes() for name in before}


@pytest.mark.parametrize("contents", ["command=\n", "# command=python relay.py\n", "other=x\n"])
def test_config_exists_without_usable_command_is_blocked(setup, contents):
    game, mods, config = setup
    config.write_text(contents)
    report = doctor.collect_diagnostics(game, mods)
    assert report["configuration"]["present"] is True
    assert report["configuration"]["command_configured"] is False
    assert "communication_command_missing" in {item["code"] for item in report["blockers"]}


def test_version_probe_failure_is_not_hidden_by_file_availability(setup, monkeypatch):
    game, mods, _ = setup

    def probe(command):
        return {"status": "failed" if command[-1] == "-version" else "ok"}

    monkeypatch.setattr(doctor, "_probe", probe)
    report = doctor.collect_diagnostics(game, mods)
    assert report["capabilities"]["game_files_available"] is True
    assert {item["code"] for item in report["blockers"]} == {"bundled_java_unavailable"}


def test_corrupt_preferences_produce_blocker(setup):
    game, mods, _ = setup
    (game / "preferences/STSUnlockProgress").write_text("not JSON")
    report = doctor.collect_diagnostics(game, mods)
    assert report["profile"]["status"] == "unavailable"
    assert "JSONDecodeError" in report["profile"]["errors"]
    assert "profile_unverified" in {item["code"] for item in report["blockers"]}


def test_invalid_jar_is_diagnostic_not_crash(setup):
    game, mods, _ = setup
    (mods / "BaseMod.jar").write_bytes(b"not a jar")
    report = doctor.collect_diagnostics(game, mods)
    assert report["mods"]["BaseMod.jar"]["metadata_error"] == "BadZipFile"
    assert "mod_hash_mismatch" in {item["code"] for item in report["blockers"]}


def test_probe_timeout_is_bounded_and_reported(monkeypatch):
    import subprocess

    run = Mock(side_effect=subprocess.TimeoutExpired("python", 8))
    monkeypatch.setattr(doctor.subprocess, "run", run)
    assert doctor._probe(["python", "--version"]) == {
        "status": "unavailable",
        "error": "TimeoutExpired",
    }
    assert run.call_args.kwargs["timeout"] == 8


def test_environment_paths_override_defaults(setup, monkeypatch):
    game, mods, _ = setup
    monkeypatch.setenv("SPIRE_GAME_DIR", str(game))
    monkeypatch.setenv("SPIRE_MODS_DIR", str(mods))
    report = doctor.collect_diagnostics()
    assert report["game"]["path"] == str(game / "desktop-1.0.jar")
    assert report["status"] == "ready_for_probe"
