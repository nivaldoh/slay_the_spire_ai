"""Recorder ownership and retained failures with fake processes, never a real game."""

import copy
import json
import shutil
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
        tmp_path, monkeypatch, capsys, bad_setup):
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
    # A land battle teleports its friendly side at Deployed: no siege start check.
    assert "start_check" not in manifest and "Siege:" not in capsys.readouterr().out


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


@pytest.mark.parametrize("key,value", [("type", "land_domination"), ("role", "attacker")])
def test_a_manual_battle_in_another_mode_than_declared_ends_the_attempt(
        tmp_path, monkeypatch, key, value):
    """The owner starts the battle by hand, so the mode is read back, not assumed. Wrong version
    (2026-11-13 refusal sweep): without the refusal a battle of another type or role is recorded
    as this scenario's demonstration."""
    state = readback()
    state["mode"][key] = value
    output, consumed = fake_recording(tmp_path, monkeypatch, [state, ending()])
    with pytest.raises(ProtocolError, match=f"manual setup: wrong {key}"):
        manual_demo.record(output, "ffmpeg.exe", 3600)
    assert json.loads((output / "manifest.json").read_text())["status"] == "failure"
    assert len(consumed) == 1


def test_a_manual_battle_must_be_at_1x_when_its_setup_is_read_back(tmp_path, monkeypatch):
    """Only the owner pauses, after the setup readback. Wrong version (2026-11-13 refusal sweep):
    without the refusal a battle paused at its readback is recorded, since play allows 0 later."""
    state = readback()
    state["speed"] = 0
    output, consumed = fake_recording(tmp_path, monkeypatch, [state, ending()])
    with pytest.raises(ProtocolError, match="manual setup must start at 1x"):
        manual_demo.record(output, "ffmpeg.exe", 3600)
    assert json.loads((output / "manifest.json").read_text())["status"] == "failure"


def test_a_source_change_during_a_manual_attempt_ends_it(tmp_path, monkeypatch):
    """The source changes after the setup readback. Wrong versions (2026-11-13 refusal sweep and
    review): without the refusal, or checking only at the readback, the attempt keeps the
    fingerprints of source files that changed under it."""
    output, consumed = fake_recording(tmp_path, monkeypatch, [readback(), ending()])
    reads = []

    def fingerprints(*args):  # read for the manifest, at the readback, then at the ending
        reads.append(True)
        return {"source": "hash" if len(reads) <= 2 else "edited"}

    monkeypatch.setattr(manual_demo, "source_fingerprints", fingerprints)
    with pytest.raises(RuntimeError, match="source changed during manual attempt"):
        manual_demo.record(output, "ffmpeg.exe", 3600)
    assert json.loads((output / "manifest.json").read_text())["status"] == "failure"


def test_a_capture_that_stops_before_the_battle_ends_fails_the_attempt(tmp_path, monkeypatch):
    """Wrong version (2026-11-13 refusal sweep): without the refusal the attempt returns as a
    stopped recording with no engine ending, and no error."""
    states = [readback()]
    output, consumed = fake_recording(tmp_path, monkeypatch, states)

    fake = manual_demo.subprocess.Popen
    assert fake.__module__ == __name__  # fake_recording's Process, never the real Popen

    class Stops(fake):
        def poll(self):
            return None if states else 0

    monkeypatch.setattr(manual_demo.subprocess, "Popen", Stops)
    with pytest.raises(RuntimeError, match="capture stopped before an engine ending"):
        manual_demo.record(output, "ffmpeg.exe", 3600)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "failure" and "engine_ending" not in manifest


def test_a_capture_that_exits_before_it_is_ready_ends_the_attempt(tmp_path, monkeypatch):
    """Wrong version (2026-11-13 refusal sweep): without the refusal the recorder waits forever
    for a video that cannot start (here the 100th wait fails the test). Every launch step is a
    fake."""
    output, _ = fake_recording(tmp_path, monkeypatch, [])

    class Exited:
        def __init__(self, command, **kwargs):
            self.returncode = 1

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode

    waits = []

    def sleep(seconds):
        waits.append(seconds)
        assert len(waits) < 100, "still waiting for a capture that exited"

    monkeypatch.setattr(manual_demo.subprocess, "Popen", Exited)
    monkeypatch.setattr(manual_demo.time, "sleep", sleep)
    with pytest.raises(RuntimeError, match="video did not become ready"):
        manual_demo.record(output, "ffmpeg.exe", 3600)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "failure" and "video did not become ready" in manifest["error"]
    assert (output / "stop-capture").exists() and waits == []


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


@pytest.mark.parametrize("change", [{"reviewer": ""}, {"complete": False}, {"complete": "yes"},
                                    {"video_sha256": "0" * 64}])
def test_pause_labels_name_a_reviewer_say_complete_and_match_the_video(tmp_path, change):
    """Wrong version (2026-11-13 refusal sweep): without the refusal anonymous, partial or
    other-video labels are attached to the attempt."""
    (tmp_path / "video.mkv").write_bytes(b"fake video")
    (tmp_path / "video-progress.txt").write_text("out_time_us=20000000\n")
    labels = {"reviewer": "owner", "complete": True,
              "video_sha256": sha256(tmp_path / "video.mkv"), "intervals": [], **change}
    path = tmp_path / "labels-input.json"
    path.write_text(json.dumps(labels))
    with pytest.raises(ValueError, match="need reviewer, complete=true and matching"):
        manual_demo.label_pauses(tmp_path, path)
    assert not (tmp_path / "pause-labels.json").exists()


def test_no_pause_labels_attach_to_a_video_without_a_duration(tmp_path):
    """Wrong version (2026-11-13 refusal sweep): without the refusal a labelling with no pauses
    is attached to a video whose length was never read, as if it had been watched."""
    (tmp_path / "video.mkv").write_bytes(b"fake video")
    (tmp_path / "video-progress.txt").write_text("out_time_us=0\n")
    labels = {"reviewer": "owner", "complete": True,
              "video_sha256": sha256(tmp_path / "video.mkv"), "intervals": []}
    path = tmp_path / "labels-input.json"
    path.write_text(json.dumps(labels))
    with pytest.raises(ValueError, match="video duration unavailable"):
        manual_demo.label_pauses(tmp_path, path)
    assert not (tmp_path / "pause-labels.json").exists()


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


def test_an_owner_recording_keeps_the_private_record_its_scenario_turns_on(tmp_path, monkeypatch):
    # Haengju's held-and-released check reads the private record of the owner's recording.
    name = "emp-support-timing-v1"
    output, _ = fake_recording(tmp_path, monkeypatch, [readback(), ending()])
    scenario = {**setup.scenarios()[name], "private_record": True}
    monkeypatch.setattr(manual_demo, "scenarios", lambda: {name: scenario})
    raw = json.dumps({"private_record": 1, "job": output.name, "battle": "b1"}) + "\n"
    (tmp_path / "bridge/private-b1.jsonl").write_text(raw)
    manual_demo.record(output, "ffmpeg.exe", 3600)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["private_record"]["status"] == "copied"
    assert (output / "private.jsonl").read_text() == raw
    assert manual_demo.Mailbox.sessions[-1]["private_record"] is True


@pytest.mark.parametrize("held", [True, False])
def test_a_waves_scenario_is_recorded_and_its_hold_checked_at_the_first_observation(
        tmp_path, monkeypatch, held):
    # The observer session now runs the waves hold (test_wh3_waves checks the Lua side); a
    # first observation without its evidence is a hold the mod skipped, and ends the attempt.
    from test_wh3_waves import WAVES, start
    from test_wh3_waves import observation as waves_observation

    first = readback()
    lua, _ = start(mode="observe")
    if held:
        first.update(waves_observation(lua))
        first["setup"]["reserve"] = {"ok": True}
    output, _ = fake_recording(tmp_path, monkeypatch, [first, ending()])
    monkeypatch.setattr(manual_demo, "check_battle", lambda *a: {"passed": True})
    monkeypatch.setattr(manual_demo, "expected_mode", lambda *a: {})
    profile = setup.scenarios()[WAVES]["reserve"]
    if held:
        manual_demo.record(output, "ffmpeg.exe", 3600, WAVES)
    else:
        with pytest.raises(ProtocolError, match="reserve"):
            manual_demo.record(output, "ffmpeg.exe", 3600, WAVES)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == ("engine_ended" if held else "failure")
    assert manual_demo.Mailbox.sessions[-1]["reserve"] == profile
    assert manual_demo.Mailbox.sessions[-1]["multiplayer"] == "observe"
    if held:
        assert [unit["slot"] for unit in manifest["reserve"]["units"]] == list(range(5, 19))
    # The all-at-once arm has no hold and no reserve in its session.
    assert "reserve" not in manual_demo.settings(setup.scenarios()["cth-emp-siege-a-all-v1"])


def test_the_recorder_refuses_a_job_named_after_the_history(tmp_path, monkeypatch):
    fake_recording(tmp_path, monkeypatch, [])
    output = tmp_path / "haengju-demo-1"
    with pytest.raises(ValueError, match="withheld word"):
        manual_demo.record(output, "ffmpeg.exe", 3600, "cth-emp-siege-a-v1")
    assert not output.exists() and manual_demo.Mailbox.sessions == []


@pytest.mark.parametrize("failed", [False, True])
def test_a_waves_recording_checks_its_releases_again_at_the_end_and_keeps_the_attempt(
        tmp_path, monkeypatch, failed):
    # Releases come after the first observation; one the mod could not make (a getter failed)
    # is kept in the manifest beside the owner's ending, which still stands.
    from test_wh3_waves import TICK, WAVES, start, ticks
    from test_wh3_waves import observation as waves_observation

    lua, tick = start(mode="observe")
    first = readback()
    first.update(waves_observation(lua))
    ticks(tick, TICK, 150000)
    last = ending()
    last.update(waves_observation(lua))
    if failed:
        last["evaluation"]["reserve"]["releases"][0].update(ok=False, error="men: unreadable")
    output, _ = fake_recording(tmp_path, monkeypatch, [first, last])
    monkeypatch.setattr(manual_demo, "check_battle", lambda *a: {"passed": True})
    monkeypatch.setattr(manual_demo, "expected_mode", lambda *a: {})
    manual_demo.record(output, "ffmpeg.exe", 3600, WAVES)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "engine_ended" and manifest["reserve"]["releases"] == []
    if failed:
        assert manifest["reserve_final"] == {"error": "reserve release failed: men: unreadable"}
    else:
        assert [(r["group"], r["reason"], r["released_ms"])
                for r in manifest["reserve_final"]["releases"]] == [(1, "time", 150000)]


GARRISON, IZMAIL = ["f1", "f2", "f3"], ["f1", "f2", "f3", "e1", "e2"]


def private_record(shift=None, by=(0, 0), battle="b1"):
    """Two private-record frames: the start of a Haengju-like garrison f1-f3 and two enemy units,
    with ``shift`` (a unit id, or "all") moved by ``by`` metres, then every unit 200 m on from the
    unshifted start. Only the first frame is a start."""
    places = {"f1": (-40, 120), "f2": (0, 120), "f3": (40, 120),
              "e1": (-60, -300), "e2": (60, -300)}
    frames = []
    for time_ms, moved, (dx, dz) in ((1000, shift, by), (2000, "all", (200, 0))):
        frame = {"private_record": 1, "job": "attempt", "battle": battle, "time_ms": time_ms,
                 "friendly": [], "enemy": []}
        for unit_id, (x, z) in places.items():
            ox, oz = (dx, dz) if moved in (unit_id, "all") else (0, 0)
            side = "friendly" if unit_id.startswith("f") else "enemy"
            frame[side].append({"id": unit_id, "x": x + ox, "y": 3.5, "z": z + oz})
        frames.append(frame)
    return frames


def jsonl(frames):
    return "".join(json.dumps(frame) + "\n" for frame in frames)


# Haengju's garrison is engine-placed and its enemy teleported; Izmail places both armies. A mean
# offset over 3 or 5 units stays under 25 m, and a friendly-only reading misses e1.
@pytest.mark.parametrize("moved,ids", [("f2", GARRISON), ("e1", IZMAIL)])
def test_demo_start_reads_one_engine_placed_unit_moved_40_m_as_own_deployment(moved, ids):
    holds = [private_record(), private_record("all", (3, -4))]
    demo = private_record(moved, (40, 0))
    assert manual_demo.demo_start(demo, holds, ids) == "own deployment"


def test_demo_start_needs_every_unit_within_25_m_of_every_hold():
    holds = [private_record(), private_record("all", (3, -4))]
    demo = private_record("all", (14, 14))  # 19.8 m and 21.1 m from the two holds
    assert manual_demo.demo_start(demo, holds, IZMAIL) == "same start"
    # 10 m from the first hold and 30 m from the second; rests on JUDGEMENT?
    # src/twwarhammer3/battle/manual_demo.py Every hold a reference.
    holds = [private_record(), private_record("all", (20, 0))]
    demo = private_record("all", (-10, 0))
    assert manual_demo.demo_start(demo, holds, IZMAIL) == "own deployment"


@pytest.mark.parametrize("holds", [
    [], [private_record()], [private_record(), private_record("f2", (0, 30))]],
    ids=["no reference", "one hold", "holds 30 m apart"])
def test_demo_start_without_a_repeated_engine_start_is_not_comparable(holds):
    assert manual_demo.demo_start(private_record(), holds, GARRISON) == "start not comparable"


def test_a_siege_recording_tells_the_owner_and_labels_its_start_in_the_manifest(
        tmp_path, monkeypatch, capsys):
    name = "ksl-emp-siege-a-v1"  # no deployment: the engine places both armies
    output, _ = fake_recording(tmp_path, monkeypatch, [readback(), ending()])
    monkeypatch.setattr(manual_demo, "check_battle", lambda *a: {"passed": True})
    monkeypatch.setattr(manual_demo, "expected_mode", lambda *a: {})
    episodes = []
    for job, scenario, policy in (("holds", name, "hold"), ("holds", name, "hold"),
                                  ("other", "cth-emp-siege-a-v1", "hold"),
                                  ("scripted", name, "attack_nearest")):
        (tmp_path / job).mkdir(exist_ok=True)
        (tmp_path / job / "manifest.json").write_text(json.dumps({"scenario": {"name": scenario}}))
        episode = tmp_path / job / f"episode-{len(episodes):04d}"
        episode.mkdir()
        (episode / "result.json").write_text(json.dumps({"policy": policy}))
        (episode / "private.jsonl").write_text(jsonl(private_record(battle=f"h{len(episodes)}")))
        episodes.append(episode)
    shutil.copytree(tmp_path / "holds", tmp_path / "copied")  # the same battle under another path
    other = "is not a hold episode of ksl-emp-siege-a-v1"
    for wrong, why in ((episodes[2], other), (episodes[3], other),
                       (episodes[0], "repeats an earlier hold"),
                       (tmp_path / "copied/episode-0000", "repeats an earlier hold")):
        with pytest.raises(ValueError, match=why):
            manual_demo.record(output, "ffmpeg.exe", 3600, name, [episodes[0], wrong])
    assert not output.exists()
    (tmp_path / "bridge/private-b1.jsonl").write_text(jsonl(private_record("e2", (0, 40))))
    manual_demo.record(output, "ffmpeg.exe", 3600, name, episodes[:2])
    assert "without moving any unit" in capsys.readouterr().out
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["start_check"] == {"label": "own deployment", "units": IZMAIL,
                                       "references": [str(path) for path in episodes[:2]]}
    # Haengju's enemy is teleported, a null deployment teleports nobody, and a land battle
    # without a deployment is not checked here.
    assert [manual_demo.engine_placed(setup.scenarios()[key])
            for key in ("cth-emp-siege-a-v1", "cth-emp-siege-a-all-gates-v1",
                          "emp-mirror-cavalry-v1")] == [["friendly"], ["friendly", "enemy"], []]
