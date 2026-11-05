"""Recorder ownership and retained failures with fake processes, never a real game."""

import copy
import json
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from test_wh3_support_timing import ending, view

from gameai.provenance import sha256
from twwarhammer3.battle import manual_demo, setup
from twwarhammer3.engine import manual_capture
from twwarhammer3.engine.mailbox import require_realtime
from twwarhammer3.protocol import ProtocolError


def test_observer_settings_do_not_relax_automatic_play():
    s = manual_demo.settings(setup.scenarios()["emp-support-timing-v1"])
    assert s["multiplayer"] == "observe" and s["autostart"] is False
    assert s["stills"] is False and s["record_replay"] is True
    assert s["benchmark"] == "behaviour-defaults" and s["deployment"]
    assert "pause" not in s and "speed" not in s
    with pytest.raises(ValueError, match="unpaused at 1x"):
        require_realtime({"pause": True})


def readback():
    obs = view()
    obs["mode"] = {"type": "land_normal", "role": "defender"}
    obs["terrain"] = {"rows": ["..."]}
    obs["armies"] = {side: {"faction": "wh_main_emp_empire"} for side in ("player", "enemy")}
    obs["setup"] = {"unit_scale": .75, "realism": False, "player_defends": True,
                    "army_ai_stats_modifiers": [1., 1.],
                    "unit_experience": {"friendly": [
                        {"type": "wh_main_emp_inf_swordsmen", "rank": 0},
                        {"type": "wh_main_emp_cav_empire_knights", "rank": 0}],
                        "enemy": [{"type": "wh_main_emp_inf_greatswords", "rank": 0}]},
                    "deployment_reading": {"friendly": [
                        {"id": "f9", "type": "wh_main_emp_inf_swordsmen", "x": 0, "z": 0},
                        {"id": "f2", "type": "wh_main_emp_cav_empire_knights", "x": -100, "z": 60}],
                        "enemy": [{"id": "e8", "type": "wh_main_emp_inf_greatswords",
                                   "x": 0, "z": -160}]},
                    "benchmark_behaviours": {"friendly": {
                        "f9": {"supported": ["defend"], "defend": False},
                        "f2": {"supported": ["defend"], "defend": False}},
                        "enemy": {"e8": {"supported": ["defend"], "defend": True}}}}
    return obs


def test_defaults_are_checked_without_adopting_a_benchmark_scorer():
    scenario = setup.scenarios()["emp-support-timing-v1"]
    obs = readback()
    checks = setup.check_battle(scenario, obs)
    assert checks["benchmark_behaviours"]["enemy"]["e8"]["defend"] is True
    obs["setup"]["benchmark_behaviours"]["friendly"]["f9"]["defend"] = True
    with pytest.raises(ProtocolError, match="friendly/f9 defend"):
        setup.check_battle(scenario, obs)


def test_a_start_far_from_its_declared_formation_is_recorded_and_stops_no_job():
    scenario = setup.scenarios()["emp-support-timing-v1"]  # swordsmen declared at 180, width 40
    obs = readback()
    obs["setup"]["deployment_reading"]["friendly"][0].update(bearing=350, width=10)
    assert setup.check_battle(scenario, obs)["deployment_formation"]["f9"] == {
        "bearing_error_deg": 170, "width_difference_m": -30}


def fake_recording(tmp_path, monkeypatch, states):
    output, bridge = tmp_path / "attempt", tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "mod.log").write_text("owned attempt\n")
    consumed = []

    class Mailbox:
        sessions = []

        def __init__(self, directory, job):
            self.job = job

        def reset(self):
            pass

        def owned_session(self, settings):
            assert settings["multiplayer"] == "observe"
            self.sessions.append(settings)
            return nullcontext()

        def read_observation(self):
            consumed.append(True)
            return copy.deepcopy(states.pop(0))
        # No write_orders/write_control implementation: an accidental call fails the test.

    class Process:
        def __init__(self, command, **kwargs):
            (output / "capture-ready.json").write_text('{}')
            self.returncode = None

        def poll(self):
            return self.returncode

        def wait(self, timeout):
            assert (output / "stop-capture").exists()
            (output / "capture-result.json").write_text('{"status":"stopped"}')
            self.returncode = 0

    # These recorded synthetic states describe v1; recorder workflow tests keep that setup.
    monkeypatch.setattr(manual_demo, "SCENARIO", "emp-support-timing-v1")
    monkeypatch.setattr(manual_demo, "BRIDGE_DIR", bridge)
    monkeypatch.setattr(manual_demo, "committed_revision", lambda *a: "r1")
    monkeypatch.setattr(manual_demo, "source_fingerprints", lambda *a: {"source": "hash"})
    monkeypatch.setattr(manual_demo, "collect_diagnostics", lambda: {})
    monkeypatch.setattr(manual_demo, "RuntimeLock", nullcontext)
    monkeypatch.setattr(manual_demo, "prepare_runtime", lambda: {"pack": "hash"})
    monkeypatch.setattr(manual_demo, "OwnedGame", lambda *a, **k: nullcontext(
        SimpleNamespace(info={"pid": 123})))
    monkeypatch.setattr(manual_demo, "Mailbox", Mailbox)
    monkeypatch.setattr(manual_demo, "windows_name", str)
    monkeypatch.setattr(manual_demo.windows, "windows_path", str)
    monkeypatch.setattr(manual_demo.subprocess, "Popen", Process)
    monkeypatch.setattr(manual_demo, "start_frontend", lambda *a: None)
    monkeypatch.setattr(manual_demo, "check_menu", lambda *a: {"passed": True})
    monkeypatch.setattr(manual_demo.time, "sleep", lambda *a: None)
    return output, consumed


@pytest.mark.parametrize("bad_setup", [False, True])
def test_record_keeps_success_and_failed_setup_and_never_sends_orders(
        tmp_path, monkeypatch, bad_setup):
    states = [readback(), ending()]
    if bad_setup:
        states[0]["setup"]["unit_scale"] = .5
    output, consumed = fake_recording(tmp_path, monkeypatch, states)
    if bad_setup:
        with pytest.raises(ProtocolError, match="unit_scale"):
            manual_demo.record(output, "ffmpeg.exe", 3600)
    else:
        manual_demo.record(output, "ffmpeg.exe", 3600)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == ("failure" if bad_setup else "engine_ended")
    assert (output / "mod.log").read_text() == "owned attempt\n"
    assert (output / "stop-capture").exists()
    assert manifest["pause_intervals"] is None
    assert len(consumed) == (1 if bad_setup else 2)
    if not bad_setup:
        assert set(manifest["setup_checks"]["deployment_formation"]) == {"f9", "f2", "e8"}
    raw = json.loads((output / "initial-observation.json").read_text())
    assert raw["setup"]["unit_scale"] == (.5 if bad_setup else .75)


@pytest.mark.parametrize("name,used", [("emp-envelopment-a-v1", "emp-envelopment-a-v1"),
                                       (None, "emp-support-timing-v1")])  # fake_recording's default
def test_record_uses_the_named_scenario_in_every_step(tmp_path, monkeypatch, name, used):
    output, _ = fake_recording(tmp_path, monkeypatch, [readback(), ending()])
    seen = {}

    def seeing(step, result):
        return lambda scenario, *a, **k: seen.update({step: scenario}) or result

    monkeypatch.setattr(manual_demo, "validate_declaration", seeing("validation", None))
    monkeypatch.setattr(manual_demo, "scenario_steps", seeing("steps", []))
    monkeypatch.setattr(manual_demo, "check_menu", seeing("menu", {"passed": True}))
    monkeypatch.setattr(manual_demo, "check_battle", seeing("battle", {"passed": True}))
    monkeypatch.setattr(manual_demo, "expected_mode", seeing("mode", {}))
    monkeypatch.setattr("sys.argv", ["manual_demo", "record", "--output", str(output),
                                     "--ffmpeg", "ffmpeg.exe", "--timeout", "3600",
                                     *(["--scenario", name] if name else [])])
    assert manual_demo.main() == 0
    scenario = setup.scenarios()[used]
    assert seen == dict.fromkeys(("validation", "steps", "menu", "battle", "mode"), scenario)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["scenario"] == scenario
    assert manifest["session"] == manual_demo.settings(scenario)
    assert manual_demo.Mailbox.sessions == [manual_demo.settings(scenario)]


# setup_reserve asserts no multiplayer mode, so B's two held slots would fall to native AI.
# check_menu and check_battle read expect, so kho5-dwf5 would otherwise fail after its launch.
@pytest.mark.parametrize("name,why", [("emp-envelopment-b-v3", "the mod refuses reserve"),
                                      ("emp-battery-wef-evacuation", "the mod refuses custom"),
                                      ("kho5-dwf5", "it declares no expect")])
def test_a_scenario_the_observer_cannot_run_is_refused_before_any_output(
        tmp_path, monkeypatch, name, why):
    output, _ = fake_recording(tmp_path, monkeypatch, [])
    with pytest.raises(ValueError, match=f"{name} cannot be recorded: {why}"):
        manual_demo.record(output, "ffmpeg.exe", 3600, name)
    assert not output.exists()
    assert manual_demo.Mailbox.sessions == []


def test_capture_identity_and_windows_timestamps_are_preserved(tmp_path):
    path = tmp_path / "observation.json"
    path.write_text(json.dumps({"job": "ours", "seq": 1, "time_ms": 10}))
    obs, stamp = manual_capture.read_snapshot(path, "ours")
    assert obs["seq"] == 1 and stamp == path.stat().st_mtime_ns
    assert manual_capture.read_snapshot(path, "foreign") == (None, None)
    command = manual_capture.video_command("ffmpeg.exe", 123, tmp_path)
    assert command[command.index("-filter_complex") + 1].startswith(
        "gfxcapture=hwnd=123:max_framerate=30:dup_frames=1,hwdownload,format=bgra")
    assert "-n" in command and "-y" not in command


def test_pause_labels_require_independent_bounded_video_intervals_and_cannot_overwrite(tmp_path):
    (tmp_path / "video.mkv").write_bytes(b"fake video")
    (tmp_path / "video-progress.txt").write_text("out_time_us=20000000\n")
    labels = {"reviewer": "owner", "complete": True,
              "video_sha256": sha256(tmp_path / "video.mkv"),
              "intervals": [{"start_s": 3, "end_s": 6, "evidence": "pause icon in video"}]}
    path = tmp_path / "labels-input.json"
    path.write_text(json.dumps(labels))
    manual_demo.label_pauses(tmp_path, path)
    saved = json.loads((tmp_path / "pause-labels.json").read_text())
    assert saved["intervals"] == labels["intervals"]
    with pytest.raises(FileExistsError):
        manual_demo.label_pauses(tmp_path, path)
    labels["intervals"][0]["end_s"] = 50
    path.write_text(json.dumps(labels))
    with pytest.raises(ValueError, match="invalid/overlapping"):
        manual_demo.label_pauses(tmp_path, path)


@pytest.mark.parametrize("mirror", [False, True])
def test_unreadable_supported_or_required_toggles_are_rejected(mirror):
    scenario = setup.scenarios()["emp-support-timing-v1"]
    obs = readback()
    if mirror:
        scenario["benchmark"] = "mirror-v1"
        obs["setup"]["benchmark_behaviours"]["enemy"]["e8"] = {"supported": []}
    else:
        obs["setup"]["benchmark_behaviours"]["enemy"]["e8"] = {
            "supported": ["formed_attack"], "formed_attack": "unreadable"}
    with pytest.raises(ProtocolError, match="unreadable"):
        setup.check_battle(scenario, obs)


@pytest.mark.parametrize("speed", [0, .5, 2])
def test_manual_play_only_allows_normal_speed_and_owner_pauses(tmp_path, monkeypatch, speed):
    changed = view(2000)
    changed["speed"] = speed
    output, _ = fake_recording(tmp_path, monkeypatch, [readback(), changed, ending()])
    if speed == 0:
        manual_demo.record(output, "ffmpeg.exe", 3600)
    else:
        with pytest.raises(ProtocolError, match="requires 1x or an owner pause"):
            manual_demo.record(output, "ffmpeg.exe", 3600)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == ("engine_ended" if speed == 0 else "failure")
    if speed != 0:
        raw = json.loads((output / "last-observation.json").read_text())
        assert raw["speed"] == speed


def test_restarted_manual_battle_keeps_original_identity_and_does_not_claim_foreign_win(
        tmp_path, monkeypatch):
    foreign = ending()
    foreign["battle"] = "b2"
    output, _ = fake_recording(tmp_path, monkeypatch, [readback(), foreign])
    copied_battles = []
    monkeypatch.setattr(manual_demo, "copy_recording", lambda *a, **k:
                        copied_battles.append(k["battle"]) or {"status": "absent"})
    with pytest.raises(ProtocolError, match="restarted"):
        manual_demo.record(output, "ffmpeg.exe", 3600)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["battle"] == "b1" and "engine_ending" not in manifest
    assert copied_battles == ["b1"]
    assert json.loads((output / "last-observation.json").read_text())["battle"] == "b2"
