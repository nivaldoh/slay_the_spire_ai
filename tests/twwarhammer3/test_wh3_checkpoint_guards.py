"""battle/checkpoint.py's refusals before a launch, and its saved-replay checks, offline.

Removing any of these passed every test before (runs/refusal-sweep-20261029/wh3-checkpoint.txt).
The runtime lock, the first step of a launch, is stubbed to raise, so a missing guard fails the
test instead of starting the game.
"""
import json

import pytest

from gameai.provenance import sha256
from twwarhammer3.battle import checkpoint

SOURCE = {"scenario": "brt-cavalry-emp-assault", "stop_tick": 10}
RESTORE = {"checkpoint": {"name": "saved", "tick": 1200}, "stop_tick": 2000}


class LaunchAttempted(Exception):
    pass


@pytest.fixture
def offline(tmp_path, monkeypatch):
    (tmp_path / "user/replays").mkdir(parents=True)
    environment = {"blockers": [], "game": {"sha256": checkpoint.EXE_SHA256,
                                            "steam_build_id": 25961564}}
    monkeypatch.setattr(checkpoint.runtime, "user_dir", lambda: tmp_path / "user")
    monkeypatch.setattr(checkpoint, "collect_diagnostics", lambda: environment)
    monkeypatch.setattr(checkpoint, "conflicting_games", lambda *args: False)
    monkeypatch.setattr(checkpoint, "committed_revision", lambda *args: "rev")
    monkeypatch.setattr(checkpoint, "source_fingerprints", lambda *args: {})

    def lock():
        raise LaunchAttempted("a launch was attempted")
    monkeypatch.setattr(checkpoint.runtime, "RuntimeLock", lock)
    return tmp_path, environment, monkeypatch


def launch(plan, output):
    with checkpoint.launched(plan, output, None, checkpoint.CONFIG, checkpoint.LIMITS):
        pass


def test_a_clean_source_plan_reaches_the_launch(offline):
    tmp_path, _, _ = offline
    with pytest.raises(LaunchAttempted):
        launch(SOURCE, tmp_path / "run")


@pytest.mark.parametrize("case,error,message", [
    ("replay_exists", FileExistsError, "replay sv already exists"),
    ("blocked", RuntimeError, "another game is running"),
    ("other_build", RuntimeError, "supports Steam build 25961564 only"),
    ("spire_running", RuntimeError, "Slay the Spire is running"),
    ("lobby_steps_on_restore", ValueError, "lobby_steps apply only to source battles"),
])
def test_each_prelaunch_refusal_stops_before_the_runtime_lock(offline, case, error, message):
    tmp_path, environment, monkeypatch = offline
    plan = dict(SOURCE)
    if case == "replay_exists":
        (tmp_path / "user/replays/sv.replay").write_text("x")
        plan["save_at"] = [{"tick": 5, "name": "sv"}]
    elif case == "blocked":
        environment["blockers"] = ["another game is running"]
    elif case == "other_build":
        environment["game"]["sha256"] = "0" * 64
    elif case == "spire_running":
        monkeypatch.setattr(checkpoint, "conflicting_games", lambda *args: True)
    else:
        plan = {**RESTORE, "lobby_steps": [{"log": "x"}]}
    with pytest.raises(error, match=message):
        launch(plan, tmp_path / "run")


def test_a_restore_plan_with_lua_before_its_checkpoint_is_refused(offline):
    tmp_path, _, _ = offline
    plan = {**RESTORE, "lua_at": [{"tick": 500, "label": "early", "lua": ""}]}
    with pytest.raises(ValueError, match="only at tick 1 and after its checkpoint"):
        checkpoint.run(plan, tmp_path / "run")


def test_an_injected_message_that_would_end_the_lua_string_is_refused():
    assert checkpoint.inject_lua({"say": "hi"}).startswith("return twwarhammer3_inject([==[")
    with pytest.raises(ValueError, match="cannot be quoted as a Lua long string"):
        checkpoint.inject_lua({"say": "]==] os.exit()"})


def library_record(tmp_path, monkeypatch):
    directory = tmp_path / "library/1200"
    directory.mkdir(parents=True)
    (directory / "saved.replay").write_bytes(b"replay bytes")
    monkeypatch.setattr(checkpoint, "pack_sha256", lambda: "pack")
    record = {"name": "saved", "tick": 1200, "usable": True, "late": True,
              "replay": "saved.replay", "replay_sha256": sha256(directory / "saved.replay"),
              "exe_sha256": checkpoint.EXE_SHA256, "pack_sha256": "pack",
              "agent_sha256": sha256(checkpoint.AGENT)}
    (directory / "record.json").write_text(json.dumps(record))
    return directory


def test_a_saved_replay_that_differs_from_its_record_or_would_overwrite_is_refused(offline):
    tmp_path, _, monkeypatch = offline
    directory = library_record(tmp_path, monkeypatch)
    (tmp_path / "user/replays/saved.replay").write_bytes(b"replay bytes")
    with pytest.raises(FileExistsError):
        checkpoint.restore_episode(directory / "record.json", {}, tmp_path / "run")
    (tmp_path / "user/replays/saved.replay").unlink()
    (directory / "saved.replay").write_bytes(b"changed bytes")
    with pytest.raises(ValueError, match="^saved.replay differs from its record"):
        checkpoint.restore_episode(directory / "record.json", {}, tmp_path / "run")
    assert not (tmp_path / "user/replays/saved.replay").exists()


def test_a_library_without_a_usable_late_save_is_refused(tmp_path, monkeypatch):
    directory = library_record(tmp_path, monkeypatch)
    record = json.loads((directory / "record.json").read_text())
    (directory / "record.json").write_text(json.dumps({**record, "late": False}))
    with pytest.raises(ValueError, match="no usable late save"):
        checkpoint.late_rung(tmp_path / "library")


def test_setting_bystander_replays_aside_refuses_unsafe_states(offline):
    # The owner's other saved replays wait aside during a restore and must all come back.
    tmp_path, _, _ = offline
    replays = tmp_path / "user/replays"
    with pytest.raises(FileNotFoundError):
        with checkpoint.only_replay("missing"):
            pass
    (replays / "saved.replay").write_text("restore me")
    (replays / "mine.replay").write_text("the owner's")
    (replays / "checkpoint-aside").mkdir()
    (replays / "checkpoint-aside/left.replay").write_text("from an interrupted run")
    with pytest.raises(RuntimeError, match="interrupted run are still in"):
        with checkpoint.only_replay("saved"):
            pass
    assert (replays / "mine.replay").read_text() == "the owner's"
    (replays / "checkpoint-aside/left.replay").unlink()
    with pytest.raises(FileNotFoundError, match="checkpoint-aside"):
        with checkpoint.only_replay("saved"):
            (replays / "checkpoint-aside/mine.replay").unlink()  # lost while set aside
