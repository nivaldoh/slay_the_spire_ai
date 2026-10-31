"""Presentation evidence in twwarhammer3/battle/capture.py: copying the replay recording and
the stills out of the bridge, and the passive screenshot thread."""
import json
import threading
from pathlib import Path
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


@pytest.mark.parametrize("failure", [
    "os-error", "empty-os-error", "timeout", "bad-json", "non-object", "deep-json",
])
def test_passive_capture_records_backend_failure_and_keeps_later_requests(
    tmp_path, monkeypatch, failure
):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "observation.json").write_text(json.dumps({"job": "j", "battle": "b"}))
    def publish(triggers):
        (bridge / "imagery-b.json").write_text(json.dumps({
            "job": "j", "battle": "b", "stills": [
                {"trigger": trigger, "status": "capture_ready"} for trigger in triggers],
        }))

    worker = capture.PassiveCapture(bridge, job="j", pid=123, enabled=True)
    # The ending request arrives on the next poll, after the opening failure. Honor real
    # stop requests, but bound broken workers without a native process or thread timing.
    polls = iter([("opening",), ("opening", "ending")])

    def next_poll(_):
        triggers = next(polls, None)
        if worker.stop.is_set() or triggers is None:
            worker.stop.set()
            return True
        publish(triggers)
        return False

    monkeypatch.setattr(worker.stop, "wait", next_poll)
    monkeypatch.setattr(capture, "windows_path", str)
    called = []

    def screenshot(command, **kwargs):
        opening = command[3].endswith("-opening.png")
        called.append("opening" if opening else "ending")
        if opening:
            if failure == "os-error":
                raise OSError("capture backend unavailable")
            if failure == "empty-os-error":
                raise OSError()
            if failure == "timeout":
                raise capture.subprocess.TimeoutExpired("capture", 1)
            reply = {"bad-json": "not JSON", "non-object": "[]", "deep-json": "[" * 100_000}
            return SimpleNamespace(stdout=reply[failure])
        (bridge / "still-b-ending.png").write_bytes(b"image")
        return SimpleNamespace(stdout=json.dumps({
            "status": "captured", "file": "still-b-ending.png"}))

    monkeypatch.setattr(capture.subprocess, "run", screenshot)
    worker.run()

    failed_path, success_path = bridge / "capture-b-opening.json", bridge / "capture-b-ending.json"
    assert failed_path.is_file(), "backend failure must produce capture metadata"
    assert success_path.is_file(), "one failed request must not prevent a later ready capture"
    failed, success = json.loads(failed_path.read_text()), json.loads(success_path.read_text())
    assert {key: failed.get(key) for key in ("job", "battle", "trigger", "status")} == {
        "job": "j", "battle": "b", "trigger": "opening", "status": "capture_failed"}
    assert failed.get("error")
    assert {key: success.get(key) for key in ("job", "battle", "trigger", "status", "file")} == {
        "job": "j", "battle": "b", "trigger": "ending", "status": "captured",
        "file": "still-b-ending.png"}
    assert (bridge / "still-b-ending.png").read_bytes() == b"image"
    assert sorted(called) == ["ending", "opening"]


@pytest.mark.parametrize("bad_request", [
    "observation-job", "imagery-job", "imagery-battle", "pending",
])
def test_passive_capture_waits_for_matching_ready_request(tmp_path, monkeypatch, bad_request):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    worker = capture.PassiveCapture(bridge, job="j", pid=123, enabled=True)
    poll = 0

    def next_poll(_):
        nonlocal poll
        if worker.stop.is_set() or poll == 2:
            worker.stop.set()
            return True
        poll += 1
        observation = {"job": "j", "battle": "b"}
        record = {"job": "j", "battle": "b", "stills": [
            {"trigger": "opening", "status": "capture_ready"}]}
        if poll == 1:
            if bad_request == "observation-job":
                observation["job"] = "other-job"
            elif bad_request == "imagery-job":
                record["job"] = "other-job"
            elif bad_request == "imagery-battle":
                record["battle"] = "other-battle"
            else:
                record["stills"][0]["status"] = "pending"
        (bridge / "observation.json").write_text(json.dumps(observation))
        (bridge / "imagery-b.json").write_text(json.dumps(record))
        return False

    calls = []

    def screenshot(command, **kwargs):
        calls.append((poll, command[-2:]))
        (bridge / "still-b-opening.png").write_bytes(b"ready image")
        return SimpleNamespace(stdout=json.dumps({
            "status": "captured", "file": "still-b-opening.png"}))

    monkeypatch.setattr(worker.stop, "wait", next_poll)
    monkeypatch.setattr(capture, "windows_path", str)
    monkeypatch.setattr(capture.subprocess, "run", screenshot)
    worker.run()

    assert calls == [(2, ["j", "b"])], "only the later matching ready request may capture"
    metadata = json.loads((bridge / "capture-b-opening.json").read_text())
    assert {key: metadata.get(key) for key in ("job", "battle", "trigger", "status", "file")} == {
        "job": "j", "battle": "b", "trigger": "opening", "status": "captured",
        "file": "still-b-opening.png"}
    assert (bridge / metadata["file"]).read_bytes() == b"ready image"


@pytest.mark.parametrize("component", ["battle", "trigger"])
def test_passive_capture_cannot_write_through_a_path_component(tmp_path, monkeypatch, component):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    bad_battle = "unsafe/../../outside" if component == "battle" else "b"
    bad_trigger = "unsafe/../../outside" if component == "trigger" else "opening"
    bad_record_path = bridge / f"imagery-{bad_battle}.json"
    bad_image = bridge / f"still-{bad_battle}-{bad_trigger}.png"
    bad_callback = bridge / f"capture-{bad_battle}-{bad_trigger}.json"
    bad_paths = [bad_record_path, bad_image, bad_callback]
    # Existing intermediates and outside destinations expose actual unwanted writes.
    # Every possible write remains confined to this test's own temporary directory.
    for path in bad_paths:
        parts = path.relative_to(bridge).parts
        if len(parts) > 1:
            (bridge / parts[0]).mkdir(exist_ok=True)
        assert path.resolve().is_relative_to(tmp_path)
    bad_record = {"job": "j", "battle": bad_battle, "stills": [
        {"trigger": bad_trigger, "status": "capture_ready"}]}
    bad_record_path.write_text(json.dumps(bad_record))
    bad_image.write_bytes(b"outside image")
    bad_callback.write_bytes(b"outside callback")
    outside = {path.resolve() for path in bad_paths if path.resolve().parent == tmp_path}
    assert len(outside) == (3 if component == "battle" else 2)
    before = {path: path.read_bytes() for path in outside}
    worker = capture.PassiveCapture(bridge, job="j", pid=123, enabled=True)
    poll = 0

    def next_poll(_):
        nonlocal poll
        if worker.stop.is_set() or poll == 2:
            worker.stop.set()
            return True
        poll += 1
        battle = bad_battle if poll == 1 else "b"
        record = bad_record if poll == 1 else {"job": "j", "battle": "b", "stills": [
            {"trigger": "opening", "status": "capture_ready"}]}
        (bridge / "observation.json").write_text(json.dumps({"job": "j", "battle": battle}))
        (bridge / f"imagery-{battle}.json").write_text(json.dumps(record))
        return False

    calls = []

    def screenshot(command, **kwargs):
        output = Path(command[3])
        assert output.resolve().is_relative_to(tmp_path)
        calls.append(output.resolve())
        output.write_bytes(b"capture")
        return SimpleNamespace(stdout=json.dumps({"status": "captured", "file": output.name}))

    monkeypatch.setattr(worker.stop, "wait", next_poll)
    monkeypatch.setattr(capture, "windows_path", str)
    monkeypatch.setattr(capture.subprocess, "run", screenshot)
    worker.run()

    assert {path: path.read_bytes() for path in outside} == before
    expected = bridge / "still-b-opening.png"
    assert calls == [expected.resolve()]
    metadata = json.loads((bridge / "capture-b-opening.json").read_text())
    assert metadata["status"] == "captured" and metadata["file"] == expected.name
    assert expected.read_bytes() == b"capture"


@pytest.mark.parametrize("mailbox_file", ["observation.json", "imagery-b.json"])
@pytest.mark.parametrize("failure", ["missing", "half-json", "locked"])
def test_passive_capture_retries_transient_mailbox_reads(
    tmp_path, monkeypatch, mailbox_file, failure
):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    target = bridge / mailbox_file
    worker = capture.PassiveCapture(bridge, job="j", pid=123, enabled=True)
    poll = 0

    def next_poll(_):
        nonlocal poll
        if worker.stop.is_set() or poll == 2:
            worker.stop.set()
            return True
        poll += 1
        (bridge / "observation.json").write_text(json.dumps({"job": "j", "battle": "b"}))
        (bridge / "imagery-b.json").write_text(json.dumps({
            "job": "j", "battle": "b", "stills": [
                {"trigger": "opening", "status": "capture_ready"}]}))
        if poll == 1:
            if failure == "missing":
                target.unlink()
            elif failure == "half-json":
                target.write_text('{"job":')
        return False

    open_path = Path.open
    denied = False

    def open_mailbox(path, mode="r", *args, **kwargs):
        nonlocal denied
        if failure == "locked" and path == target and "r" in mode and not denied:
            denied = True
            raise PermissionError("mailbox writer holds the file")
        return open_path(path, mode, *args, **kwargs)

    calls = []

    def screenshot(command, **kwargs):
        calls.append(command[-2:])
        (bridge / "still-b-opening.png").write_bytes(b"ready capture")
        return SimpleNamespace(stdout=json.dumps({
            "status": "captured", "file": "still-b-opening.png"}))

    monkeypatch.setattr(worker.stop, "wait", next_poll)
    monkeypatch.setattr(Path, "open", open_mailbox)
    monkeypatch.setattr(capture, "windows_path", str)
    monkeypatch.setattr(capture.subprocess, "run", screenshot)
    worker.run()

    assert calls == [["j", "b"]], "a later usable mailbox must capture exactly once"
    assert denied == (failure == "locked")
    metadata = json.loads((bridge / "capture-b-opening.json").read_text())
    assert {key: metadata.get(key) for key in ("job", "battle", "trigger", "status", "file")} == {
        "job": "j", "battle": "b", "trigger": "opening", "status": "captured",
        "file": "still-b-opening.png"}
    assert (bridge / metadata["file"]).read_bytes() == b"ready capture"


def test_passive_capture_deduplicates_a_ready_request_but_not_a_new_battle(
    tmp_path, monkeypatch
):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    worker = capture.PassiveCapture(bridge, job="j", pid=123, enabled=True)
    battles = iter(["b", "b", "c"])

    def next_poll(_):
        battle = next(battles, None)
        if worker.stop.is_set() or battle is None:
            worker.stop.set()
            return True
        (bridge / "observation.json").write_text(json.dumps({"job": "j", "battle": battle}))
        (bridge / f"imagery-{battle}.json").write_text(json.dumps({
            "job": "j", "battle": battle, "stills": [
                {"trigger": "opening", "status": "capture_ready"}]}))
        return False

    calls = []

    def screenshot(command, **kwargs):
        calls.append(command[-1])
        output = Path(command[3])
        output.write_bytes(f"capture-{len(calls)}".encode())
        return SimpleNamespace(stdout=json.dumps({
            "status": "captured", "file": output.name, "time_ms": len(calls)}))

    monkeypatch.setattr(worker.stop, "wait", next_poll)
    monkeypatch.setattr(capture, "windows_path", str)
    monkeypatch.setattr(capture.subprocess, "run", screenshot)
    worker.run()

    assert calls == ["b", "c"], "one capture per request, including the new battle's opening"
    for index, battle in enumerate(["b", "c"], 1):
        metadata = json.loads((bridge / f"capture-{battle}-opening.json").read_text())
        assert {key: metadata.get(key) for key in (
            "status", "file", "time_ms", "job", "battle", "trigger")} == {
                "status": "captured", "file": f"still-{battle}-opening.png", "time_ms": index,
                "job": "j", "battle": battle, "trigger": "opening"}
        assert (bridge / metadata["file"]).read_bytes() == f"capture-{index}".encode()
