"""Replaying a recorded run with a fake game and bridge (state-restore.md, Plan step 2).

Reference: the plan's step 2 (send the recorded commands, stop at the first difference and
before the command that ended the run) and its "same state" rule. These exercise the Python
loop only; whether the real game replays is what step 2 measures.
"""

import json
from contextlib import nullcontext
from copy import deepcopy
from unittest.mock import Mock

import pytest
from fullrun_support import DEATH, MENU
from spire_messages import combat_message

from spire.fullrun import replay

START = "START IRONCLAD 0 SEEDA"


class LaunchAttempted(Exception):
    pass


def hand(uuid):
    return combat_message(hand=[{"id": "Strike_R", "uuid": uuid, "cost": 1}])


def autosave(path, **fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"floor_num": 1, "gold": 99, "play_time": 10, **fields}))


@pytest.fixture
def game(monkeypatch, tmp_path):
    """A recorded run (menu, START, a turn, end, death) and a fake game that replays it."""
    sessions, sent = [], []
    record = tmp_path / "record"
    autosave(record / "saves/0001.autosave", play_time=500)
    events = [{"kind": "observation", "raw": MENU}, {"kind": "action", "command": START},
              {"kind": "observation", "raw": hand("a")},
              {"kind": "save_snapshot", "file": "saves/0001.autosave"},
              {"kind": "action", "command": "end"}, {"kind": "observation", "raw": hand("b")},
              {"kind": "action", "command": "end"}, {"kind": "observation", "raw": DEATH}]
    (record / "trace.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    preferences = tmp_path / "game/preferences"
    preferences.mkdir(parents=True)
    for name in ("STSUnlockProgress", "STSDataVagabond"):
        (preferences / name).write_text("{}")
        (preferences / f"{name}.backUp").write_text("{}")

    class FakeBridge:
        def __init__(self, **kwargs):
            self.address, self.messages = (kwargs["host"], kwargs["port"]), iter(sessions.pop(0))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def receive(self):
            item = next(self.messages)
            while callable(item):  # something the game does between two messages
                item()
                item = next(self.messages)
            return deepcopy(item)

        def send(self, command):
            sent.append(command)

    class FakeGame:
        info = {"pid": 1}

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(replay, "BridgeServer", FakeBridge)
    monkeypatch.setattr(replay, "OwnedGame", FakeGame)
    monkeypatch.setattr(replay, "RuntimeLock", nullcontext)
    monkeypatch.setattr(replay, "wsl_bridge_host", Mock(return_value="172.18.0.1"))
    monkeypatch.setattr(replay, "prepare_runtime", Mock(return_value={"mods": {}}))
    monkeypatch.setattr(replay, "collect_profile", Mock(return_value={"slot": 0}))
    monkeypatch.setattr(replay, "committed_revision", Mock(return_value="rev"))
    monkeypatch.setattr(replay, "GAME_DIR", tmp_path / "game")
    monkeypatch.setattr(replay, "_save_path",
                        lambda profile: tmp_path / "game/saves/IRONCLAD.autosave")
    return sessions, sent, record / "trace.jsonl", tmp_path


CONFIG = {"run_timeout": 100, "bridge_timeout": 30}


def test_a_faithful_replay_sends_every_command_but_the_one_that_ended_the_run(game):
    sessions, sent, trace, tmp_path = game
    save = tmp_path / "game/saves/IRONCLAD.autosave"
    # New card UUIDs and a later play time, as in any new launch: neither is a difference.
    sessions.append([MENU, lambda: autosave(save, play_time=20), hand("x"), hand("y")])

    result = replay.replay(trace, tmp_path / "out", CONFIG)

    assert sent == [START, "end"]
    assert result["status"] == "replayed"
    assert (result["stop_before"], result["sent"], result["save_differences"]) == (2, 2, [])
    assert json.loads((tmp_path / "out/result.json").read_text()) == result
    assert (tmp_path / "out/preferences-before/STSUnlockProgress").exists()


def test_the_replay_stops_at_the_first_differing_state(game):
    sessions, sent, trace, tmp_path = game
    save = tmp_path / "game/saves/IRONCLAD.autosave"
    different = hand("x")
    different["game_state"]["current_hp"] -= 1
    sessions.append([MENU, lambda: autosave(save, gold=98), different])

    result = replay.replay(trace, tmp_path / "out", CONFIG)

    assert sent == [START]
    assert (result["status"], result["first_difference"]) == ("differed", 1)
    assert result["save_differences"] == [{"snapshot": 1, "fields": ["gold"]}]


def test_a_missing_autosave_is_reported(game):
    sessions, sent, trace, tmp_path = game
    sessions.append([MENU, hand("x"), hand("y")])

    result = replay.replay(trace, tmp_path / "out", CONFIG)

    assert result["status"] == "replayed"
    assert result["save_differences"] == [{"snapshot": 1, "missing": True}]


def test_a_replay_that_differs_at_the_menu_compares_no_autosave(game):
    sessions, sent, trace, tmp_path = game
    sessions.append([{**MENU, "available_commands": ["state"]}])

    result = replay.replay(trace, tmp_path / "out", CONFIG)

    assert (sent, result["first_difference"], result["save_differences"]) == ([], 0, [])


def test_a_trace_cut_after_a_command_replays_up_to_its_last_recorded_state(game):
    sessions, sent, trace, tmp_path = game
    lines = trace.read_text().splitlines()
    trace.write_text("\n".join(lines[:-1]) + "\n")  # no state after the last command
    sessions.append([MENU, hand("x"), hand("y")])

    result = replay.replay(trace, tmp_path / "out", CONFIG)

    assert sent == [START, "end"]
    assert (result["status"], result["stop_before"]) == ("replayed", 2)


def test_the_same_state_rule_ignores_only_uuids_and_the_library_book_text():
    library = combat_message()
    library["game_state"]["screen_state"] = {"event_id": "The Library", "body_text": "a",
                                             "options": [{"text": "Read"}, {"text": "Sleep"}]}
    goop = deepcopy(library)
    goop["game_state"]["screen_state"]["event_id"] = "World of Goop"

    def same(raw, edit):
        other = deepcopy(raw)
        edit(other["game_state"]["screen_state"])
        return replay.settled(raw) == replay.settled(other)

    assert same(library, lambda screen: screen.update(body_text="b"))
    assert not same(library, lambda screen: screen["options"].pop())
    assert not same(goop, lambda screen: screen.update(body_text="b"))


def test_an_output_inside_the_full_run_jobs_is_refused(game):
    sessions, sent, trace, tmp_path = game
    with pytest.raises(ValueError, match="outside runs/fullrun/"):
        replay.replay(trace, replay.JOBS_ROOT / "replay-test-never-created", CONFIG)
    assert not (replay.JOBS_ROOT / "replay-test-never-created").exists()


@pytest.mark.parametrize("slot,prefix", [(0, ""), (1, "1_")])
@pytest.mark.parametrize("name", ["STSUnlockProgress", "STSDataVagabond"])
def test_a_profile_without_its_recovery_copies_is_refused_before_launch(game, monkeypatch, slot,
                                                                         prefix, name):
    sessions, sent, trace, tmp_path = game
    preferences = tmp_path / "game/preferences"

    def lock():
        raise LaunchAttempted
    monkeypatch.setattr(replay, "RuntimeLock", lock)
    monkeypatch.setattr(replay, "collect_profile", Mock(return_value={"slot": slot}))
    for protected in ("STSUnlockProgress", "STSDataVagabond"):
        (preferences / f"{prefix}{protected}").write_text("{}")
        (preferences / f"{prefix}{protected}.backUp").write_text("{}")
    (preferences / f"{prefix}{name}.backUp").unlink()
    with pytest.raises(RuntimeError, match=f"{prefix}{name} has no .backUp"):
        replay.replay(trace, tmp_path / "out", CONFIG)
    (preferences / f"{prefix}{name}").write_bytes(b"")
    (preferences / f"{prefix}{name}.backUp").write_bytes(b"")
    with pytest.raises(RuntimeError, match=f"{prefix}{name} and its .backUp are both empty"):
        replay.replay(trace, tmp_path / "out", CONFIG)
    monkeypatch.setattr(replay, "collect_profile", Mock(return_value={"status": "unavailable"}))
    with pytest.raises(RuntimeError, match="save slot is unreadable"):
        replay.replay(trace, tmp_path / "out", CONFIG)
    assert not (tmp_path / "out").exists()
