import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from gameai.provenance import sha256
from spire.engine import doctor, runtime


@pytest.fixture
def setup(tmp_path, monkeypatch):
    game = tmp_path / "steamapps/common/game"
    preferences = game / "preferences"
    preferences.mkdir(parents=True)
    (game / "desktop-1.0.jar").write_bytes(b"test game; not original engine evidence")
    (tmp_path / "steamapps/appmanifest_646570.acf").write_text('"buildid"\t\t"10180494"\n')
    (preferences / "STSSaveSlots").write_text(json.dumps({"DEFAULT_SLOT": "0"}))
    (preferences / "STSUnlockProgress").write_text(json.dumps(
        {"IRONCLADUnlockLevel": "3", "IRONCLADProgress": "817", "private_field": "do-not-expose"}
    ))
    (preferences / "STSGameplaySettings").write_text(json.dumps(
        {"Upload Data": "true", "Fast Mode": "true", "private_setting": "do-not-expose"}
    ))
    pins = {}
    for name in runtime.PINS:
        jar = tmp_path / "workshop" / name / name
        jar.parent.mkdir(parents=True)
        jar.write_bytes(name.encode())
        pins[name] = (name, sha256(jar))
    monkeypatch.setattr(runtime, "PINS", pins)
    monkeypatch.setattr(runtime, "GAME_DIR", game)
    monkeypatch.setattr(runtime, "WORKSHOP_DIR", tmp_path / "workshop")
    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path / "runtime")
    monkeypatch.setattr(runtime, "wsl_bridge_host", lambda: "172.18.34.183")
    monkeypatch.setattr(doctor, "conflicting_games", lambda game_dir, rules: [])
    monkeypatch.setattr(doctor, "probe", Mock(return_value={"status": "ok", "output": "v"}))
    return tmp_path


def blockers(report):
    return "\n".join(report["blockers"])


def test_ready_report_records_pins_without_private_fields_or_writes(setup):
    files = [path for path in setup.rglob("*") if path.is_file()]
    before = {path: path.read_bytes() for path in files}
    report = doctor.collect_diagnostics()
    assert report["status"] == "ready" and report["blockers"] == []
    # First-combat catalogs and reports read these two keys from environment.json.
    assert report["game"]["sha256"] == sha256(runtime.GAME_DIR / "desktop-1.0.jar")
    assert report["game"]["steam_build_id"] == "10180494"
    assert {name: mod["sha256"] for name, mod in report["mods"].items()} == {
        name: pin for name, (_, pin) in runtime.PINS.items()
    }
    assert report["profile"]["ironclad_unlock_level"] == "3"
    assert report["profile"]["upload_data_enabled"] == "true"
    assert "do-not-expose" not in json.dumps(report)
    assert json.loads(json.dumps(report)) == report
    assert "Setup: ready" in doctor.render_diagnostics(report)
    assert before == {path: path.read_bytes() for path in files}
    assert not (setup / "runtime").exists()


def test_changed_workshop_jar_or_differing_copy_blocks_but_missing_copy_does_not(setup):
    (setup / "workshop/CommunicationMod.jar/CommunicationMod.jar").write_bytes(b"update")
    copy = runtime.GAME_DIR / "mods/BaseMod.jar"
    copy.parent.mkdir()
    copy.write_bytes(b"user-installed BaseMod")
    report = doctor.collect_diagnostics()
    assert report["status"] == "blocked"
    assert len(report["blockers"]) == 2
    assert "CommunicationMod.jar is missing or differs" in blockers(report)
    assert f"{copy} differs" in blockers(report)
    assert "missing or changed" in doctor.render_diagnostics(report)


def test_missing_prerequisites_block(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "GAME_DIR", tmp_path / "game")
    monkeypatch.setattr(runtime, "WORKSHOP_DIR", tmp_path / "workshop")
    monkeypatch.setattr(runtime, "RUNTIME_DIR", tmp_path / "runtime")
    monkeypatch.setattr(doctor, "probe", lambda command: {"status": "unavailable"})
    monkeypatch.setattr(
        runtime, "wsl_bridge_host", Mock(side_effect=RuntimeError("Cannot discover eth0"))
    )
    failed = Mock(side_effect=subprocess.CalledProcessError(1, "powershell"))
    monkeypatch.setattr(doctor, "conflicting_games", failed)
    report = doctor.collect_diagnostics()
    assert report["status"] == "blocked"
    text = blockers(report)
    for expected in ("Game jar is missing", "ModTheSpire.jar is missing", "windows_python",
                     "bundled_java", "unlock state", "Cannot discover eth0",
                     "Cannot list Windows processes"):
        assert expected in text
    assert report["game"]["sha256"] is None


def test_running_game_blocks(setup, monkeypatch):
    monkeypatch.setattr(doctor, "conflicting_games", lambda game_dir, rules: [{"ProcessId": 42}])
    assert "PIDs 42" in blockers(doctor.collect_diagnostics())


def test_corrupt_preferences_block(setup):
    (runtime.GAME_DIR / "preferences/STSUnlockProgress").write_text("not JSON")
    report = doctor.collect_diagnostics()
    assert report["profile"]["status"] == "unavailable"
    assert "unlock state" in blockers(report)


def test_profile_reads_the_active_slot_and_rejects_unknown_slots(tmp_path):
    preferences = tmp_path / "preferences"
    preferences.mkdir()
    (preferences / "STSSaveSlots").write_text(json.dumps({"DEFAULT_SLOT": "2"}))
    (preferences / "2_STSUnlockProgress").write_text(json.dumps({"IRONCLADUnlockLevel": "5"}))
    profile = doctor.collect_profile(tmp_path)
    assert profile["status"] == "ok"
    assert (profile["slot"], profile["ironclad_unlock_level"]) == (2, "5")
    (preferences / "STSSaveSlots").write_text(json.dumps({"DEFAULT_SLOT": "../x"}))
    assert doctor.collect_profile(tmp_path)["status"] == "unavailable"
    assert doctor.collect_profile(Path(tmp_path / "absent"))["status"] == "unavailable"
