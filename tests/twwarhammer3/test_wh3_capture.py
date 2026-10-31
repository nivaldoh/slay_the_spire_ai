"""Presentation evidence in twwarhammer3/battle/capture.py: copying the replay recording and
the stills out of the bridge, and the passive screenshot thread."""
import json
import threading
from types import SimpleNamespace

import pytest

from twwarhammer3.battle import capture


def test_copy_keeps_interrupted_bytes_and_cannot_cross_rematches(tmp_path):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode-0000"
    bridge.mkdir()
    episode.mkdir()
    data = {"recorder": 1, "job": "job", "battle": "one", "time_ms": 0}
    raw = json.dumps(data) + '\n{"recorder":'
    (bridge / "replay-one.jsonl").write_text(raw)
    (bridge / "replay-two.jsonl").write_text(json.dumps({**data, "battle": "two"}))
    result = capture.copy_recording(bridge, episode, job="job", battle="one")
    assert result["status"] == "copied"
    assert (episode / "replay.jsonl").read_text() == raw
    copy = capture.copy_recording
    assert copy(bridge, episode, job="other", battle="one")["status"] == "identity_mismatch"
    assert copy(bridge, episode, job="job", battle="../one")["status"] == "missing_battle_id"
    assert copy(bridge, episode, job="job", battle="absent")["status"] == "missing"



@pytest.mark.parametrize("field", ["job", "battle"])
@pytest.mark.parametrize("destination_exists", [False, True], ids=["missing", "existing"])
def test_rejected_replay_identity_cannot_create_or_overwrite_evidence(tmp_path, field,
                                                                    destination_exists):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode"
    bridge.mkdir()
    episode.mkdir()
    header = {"recorder": 1, "job": "job", "battle": "b"}
    header[field] = "another"
    raw = json.dumps(header).encode() + b'\n{"partial":'
    source, destination = bridge / "replay-b.jsonl", episode / "replay.jsonl"
    source.write_bytes(raw)
    if destination_exists:
        destination.write_bytes(b"unrelated replay already in the episode")
    before = destination.read_bytes() if destination.exists() else None

    result = capture.copy_recording(bridge, episode, job="job", battle="b")

    assert result["status"] == "identity_mismatch"
    assert source.read_bytes() == raw
    after = destination.read_bytes() if destination.exists() else None
    assert after == before


def test_capture_copy_keeps_failures_and_checks_battle_identity(tmp_path):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode"
    bridge.mkdir()
    episode.mkdir()
    (bridge / "still-b-opening.tga").write_bytes(b"captured")
    (bridge / "imagery-b.json").write_text(json.dumps({
        "job": "job", "battle": "b", "names": {"f1": "Lord"}, "stills": [
            {"file": "still-b-opening.tga", "trigger": "opening", "time_ms": 1000},
            {"file": "still-b-contact.tga", "trigger": "first_contact"},
            {"file": "../private.tga"},
            {"status": "capture_failed", "error": "camera unavailable"},
        ],
    }))
    assert capture.copy_presentation(bridge, episode, job="other", battle="b")["status"] == (
        "identity_mismatch")
    assert not list(episode.iterdir())
    result = capture.copy_presentation(bridge, episode, job="job", battle="b")
    assert result == {"status": "copied", "stills": 4, "names": 1}
    shots = json.loads((episode / "stills.json").read_text())
    assert len(shots) == 4
    assert shots[0]["time_ms"] == 1000
    assert (episode / shots[0]["file"]).read_bytes() == b"captured"
    assert all(shot["status"] == "capture_failed" for shot in shots[1:])
    assert all("file" not in shot for shot in shots[1:])
    assert [shot.get("trigger") for shot in shots] == ["opening", "first_contact", None, None]
    assert shots[3]["error"] == "camera unavailable"
    assert json.loads((episode / "unit_names.json").read_text()) == {"f1": "Lord"}


@pytest.mark.parametrize("filename", [
    "still-b-nested/../../private.tga",
    "still-other-opening.tga",
], ids=["directory-escape", "foreign-battle"])
@pytest.mark.parametrize("destination_exists", [False, True], ids=["missing", "existing"])
def test_capture_rejects_foreign_files_without_changing_the_destination(
    tmp_path, filename, destination_exists
):
    bridge, episode = tmp_path / "bridge", tmp_path / "output" / "episode"
    bridge.mkdir()
    episode.mkdir(parents=True)
    # Separate parents keep a removed guard from being masked by SameFileError. Both
    # intermediate directories exist, so the traversal path also resolves without error.
    (bridge / "still-b-nested").mkdir()
    (episode / "still-b-nested").mkdir()
    source, destination = bridge / filename, episode / filename
    source.write_bytes(b"foreign capture")
    if destination_exists:
        destination.write_bytes(b"unrelated destination")
    before = destination.read_bytes() if destination.exists() else None
    (bridge / "imagery-b.json").write_text(json.dumps({
        "job": "job", "battle": "b", "stills": [
            {"file": filename, "status": "captured", "trigger": "opening"}],
    }))

    result = capture.copy_presentation(bridge, episode, job="job", battle="b")

    assert source.read_bytes() == b"foreign capture"
    after = destination.read_bytes() if destination.exists() else None
    assert after == before
    assert result == {"status": "copied", "stills": 1, "names": 0}
    shot, = json.loads((episode / "stills.json").read_text())
    assert shot["status"] == "capture_failed" and "file" not in shot
    assert shot["policy_input"] is False


def test_passive_capture_runs_outside_caller_and_joins_evidence(tmp_path, monkeypatch):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode"
    bridge.mkdir()
    episode.mkdir()
    (bridge / "observation.json").write_text(json.dumps({"job": "j", "battle": "b"}))
    (bridge / "imagery-b.json").write_text(json.dumps({"job": "j", "battle": "b", "stills": [
        {"trigger": "opening", "status": "capture_ready", "time_ms": 1000}], "names": {}}))
    entered, release = threading.Event(), threading.Event()

    def screenshot(*args, **kwargs):
        entered.set()
        assert release.wait(2)
        (bridge / "still-b-opening.png").write_bytes(b"image")
        return SimpleNamespace(stdout=json.dumps({"status": "captured",
            "file": "still-b-opening.png", "time_ms": 1100, "grab_wall_s": .04}))

    monkeypatch.setattr(capture, "windows_path", str)
    monkeypatch.setattr(capture.subprocess, "run", screenshot)
    with capture.PassiveCapture(bridge, job="j", pid=123, enabled=True):
        assert entered.wait(2)
        # The caller remains free to submit orders while the screenshot is blocked.
        assert not release.is_set()
        release.set()
    result = capture.copy_presentation(bridge, episode, job="j", battle="b")
    assert result["status"] == "copied"
    shot = json.loads((episode / "stills.json").read_text())[0]
    assert shot["time_ms"] == 1100 and shot["grab_wall_s"] == .04
    assert shot["status"] == "captured" and shot["policy_input"] is False


def test_presentation_copy_waits_for_pending_passive_capture(tmp_path, monkeypatch):
    bridge, episode = tmp_path / "bridge", tmp_path / "episode"
    bridge.mkdir()
    episode.mkdir()
    (bridge / "imagery-b.json").write_text(json.dumps({
        "job": "j", "battle": "b", "names": {}, "stills": [
            {"trigger": "opening", "status": "capture_ready", "time_ms": 1000}],
    }))
    elapsed = 0.0

    def now():
        nonlocal elapsed
        elapsed += .1  # Bounded polling even if the callback never gets read.
        return elapsed

    def finish_capture(_seconds):
        (bridge / "still-b-opening.png").write_bytes(b"image")
        (bridge / "capture-b-opening.json").write_text(json.dumps({
            "job": "j", "battle": "b", "trigger": "opening", "status": "captured",
            "file": "still-b-opening.png", "time_ms": 1100, "grab_wall_s": .04,
        }))

    # Model a callback arriving while the copier waits; no wall-clock race or worker.
    monkeypatch.setattr(capture, "time", SimpleNamespace(monotonic=now, sleep=finish_capture))

    result = capture.copy_presentation(bridge, episode, job="j", battle="b")

    assert result["status"] == "copied"
    shot = json.loads((episode / "stills.json").read_text())[0]
    assert shot["status"] == "captured" and shot["policy_input"] is False
    assert shot["time_ms"] == 1100 and shot["grab_wall_s"] == .04
    assert (episode / shot["file"]).read_bytes() == b"image"
