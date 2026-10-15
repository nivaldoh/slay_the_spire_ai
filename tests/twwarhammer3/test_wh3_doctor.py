"""The read-only checks of twwarhammer3/engine/doctor.py over a fake Steam install."""
from wh3_fixtures import fake_install

from twwarhammer3.engine import doctor, runtime, startup


def test_doctor_reports_blockers_without_launching(tmp_path, monkeypatch):
    fake_install(tmp_path, monkeypatch)
    monkeypatch.setattr(doctor, "probe", lambda command: {"status": "ok", "output": "3.13"})
    monkeypatch.setattr(runtime, "conflicting_games", lambda game_dir, rules: [{"ProcessId": 9}])
    monkeypatch.setattr(runtime, "preferences", lambda: {"gfx_unit_size": "2"})
    report = doctor.collect_diagnostics()
    text = "\n".join(report["blockers"])
    assert "pinned hash" in text and "PIDs 9" in text
    assert report["mod"]["files"] == ["script\\battle\\mod\\twwarhammer3_battle.lua"]
    assert "gfx_unit_size=2" in doctor.render_diagnostics(report)
    monkeypatch.setattr(runtime, "conflicting_games", lambda game_dir, rules: [])
    monkeypatch.setitem(runtime.PINS, "Warhammer3.exe", report["game"]["sha256"])
    assert doctor.collect_diagnostics()["status"] == "ready"


def test_doctor_reports_missing_installed_and_changed_startup_without_writing(tmp_path,
                                                                              monkeypatch):
    fake_install(tmp_path, monkeypatch)
    monkeypatch.setattr(doctor, "probe", lambda command: {"status": "ok", "output": "3.13"})
    preferences = runtime.user_dir() / "scripts/preferences.script.txt"
    before = preferences.read_bytes()
    missing = doctor.collect_diagnostics()
    assert not missing["startup"]["enabled"]
    assert missing["startup"]["pack"]["sha256"] is None
    assert preferences.read_bytes() == before
    assert not runtime.RUNTIME_DIR.exists()
    runtime.prepare_runtime()
    installed = doctor.collect_diagnostics()
    assert installed["startup"]["enabled"]
    assert "installed (all launches)" in doctor.render_diagnostics(installed)
    path = runtime.GAME_DIR / "data" / startup.PACK_NAME
    path.write_bytes(b"broken")
    assert not doctor.collect_diagnostics()["startup"]["enabled"]
    assert path.read_bytes() == b"broken"
    runtime.prepare_runtime()
    assert doctor.collect_diagnostics()["startup"]["enabled"]
    preferences.write_bytes(before)
    assert not doctor.collect_diagnostics()["startup"]["enabled"]
    assert preferences.read_bytes() == before
