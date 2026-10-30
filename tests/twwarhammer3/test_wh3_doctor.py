"""The read-only checks of twwarhammer3/engine/doctor.py over a fake Steam install."""
from wh3_fixtures import fake_install

from twwarhammer3.engine import doctor, runtime, startup


def test_doctor_reports_blockers_without_launching(tmp_path, monkeypatch):
    fake_install(tmp_path, monkeypatch)
    monkeypatch.setattr(doctor, "probe", lambda command: {"status": "ok", "output": "3.13"})
    monkeypatch.setattr(runtime, "conflicting_games", lambda game_dir, rules: [{"ProcessId": 9}])
    monkeypatch.setattr(runtime, "preferences", lambda: {"gfx_unit_size": "2"})
    report = doctor.collect_diagnostics()
    assert report["blockers"] == ["The game is already running (PIDs 9)"]
    # A game update warns but never blocks (owner, 2026-10-18).
    assert report["warnings"] == ["Warhammer3.exe differs from the pinned hash (game updated?)"]
    assert report["mod"]["files"] == ["script\\battle\\mod\\twwarhammer3_battle.lua"]
    text = doctor.render_diagnostics(report)
    assert "gfx_unit_size=2" in text and "Warning: Warhammer3.exe differs" in text
    monkeypatch.setattr(runtime, "conflicting_games", lambda game_dir, rules: [])
    assert doctor.collect_diagnostics()["status"] == "ready"
    monkeypatch.setitem(runtime.PINS, "Warhammer3.exe", report["game"]["sha256"])
    assert doctor.collect_diagnostics()["warnings"] == []
    (runtime.GAME_DIR / "Warhammer3.exe").unlink()
    assert doctor.collect_diagnostics()["blockers"] == ["Warhammer3.exe is missing"]


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


def test_doctor_reports_a_missing_appdata_on_native_windows(tmp_path, monkeypatch):
    user_dir = runtime.user_dir
    fake_install(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime, "user_dir", user_dir)
    monkeypatch.setattr(runtime.windows, "NATIVE", True)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(doctor, "probe", lambda command: {"status": "ok", "output": "3.13"})
    user_dir.cache_clear()
    report = doctor.collect_diagnostics()
    assert report["status"] == "blocked"
    assert report["blockers"][0] == (
        "Cannot read the game preferences: APPDATA is not set, so the game's user folder is "
        "unknown")
