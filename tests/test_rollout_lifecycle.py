"""Runner lifecycle regressions; these mocked states do not certify the engine."""

import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from spire import doctor, rollout
from spire.bridge import BridgeDisconnected


def combat_message():
    return {
        "ready_for_command": True,
        "in_game": True,
        "available_commands": ["play"],
        "game_state": {
            "class": "IRONCLAD",
            "ascension_level": 0,
            "floor": 1,
            "current_hp": 80,
            "room_phase": "COMBAT",
            "room_type": "MonsterRoom",
            "screen_type": "NONE",
            "combat_state": {
                "turn": 1,
                "player": {"current_hp": 80, "max_hp": 80, "energy": 1, "block": 0},
                "hand": [
                    {
                        "id": "Strike_R",
                        "cost": 1,
                        "has_target": True,
                        "is_playable": True,
                    }
                ],
                "monsters": [
                    {
                        "id": "Cultist",
                        "current_hp": 6,
                        "max_hp": 50,
                        "block": 0,
                        "is_gone": False,
                        "half_dead": False,
                        "intent": "BUFF",
                    }
                ],
            },
        },
    }


def terminal_message(outcome="won"):
    state = {
        "floor": 1,
        "current_hp": 80 if outcome == "won" else 0,
        "room_phase": "COMPLETE",
        "room_type": "MonsterRoom",
        "screen_type": "COMBAT_REWARD",
    }
    if outcome == "lost":
        state.update(screen_type="GAME_OVER", screen_name="DEATH", screen_state={"victory": False})
    return {
        "ready_for_command": True,
        "in_game": True,
        "available_commands": ["proceed"],
        "game_state": state,
    }


def read_trace(directory):
    return [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]


@pytest.fixture
def config():
    return {
        "policy": "random",
        "policy_seed": 0,
        "game_seed": "TEST1",
        "episodes": 2,
        "max_actions": 10,
        "episode_timeout": 100,
        "bridge_timeout": 30,
    }


@pytest.fixture
def harness(monkeypatch):
    state = SimpleNamespace(sessions=[], bridges=[], games=[], received=0, clock=0.0)

    class FakeBridge:
        address = ("127.0.0.1", 12345)

        def __init__(self, **kwargs):
            self.messages = iter(state.sessions.pop(0))
            self.commands = []
            self.closed = False
            state.bridges.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

        def receive(self):
            state.received += 1
            message = next(self.messages)
            if callable(message):
                message = message()
            if isinstance(message, BaseException):
                raise message
            return deepcopy(message)

        def send(self, command):
            self.commands.append(command)

    class FakeGame:
        info = {"pid": 12345}

        def __init__(self, *args, **kwargs):
            self.closed = False
            state.games.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.closed = True

    monkeypatch.setattr(rollout, "BridgeServer", FakeBridge)
    monkeypatch.setattr(rollout, "OwnedGame", FakeGame)
    monkeypatch.setattr(rollout, "prepare_runtime", Mock(return_value={"mods": {}}))
    monkeypatch.setattr(
        rollout,
        "collect_profile",
        Mock(
            return_value={
                "slot": 0,
                "ironclad_unlock_level": "3",
                "unlock_file_sha256": "profile-before-episode",
            }
        ),
    )
    monkeypatch.setattr(doctor, "collect_diagnostics", lambda: {"schema_version": 1})
    monkeypatch.setattr(rollout.time, "monotonic", lambda: state.clock)

    def git_output(command, **kwargs):
        return "test-revision\n" if command[:3] == ["git", "rev-parse", "HEAD"] else ""

    monkeypatch.setattr(rollout.subprocess, "check_output", git_output)
    return state


@pytest.mark.parametrize("outcome", ["won", "lost"])
def test_terminal_response_after_final_allowed_action_is_not_truncated(
    tmp_path, config, harness, outcome
):
    config["max_actions"] = 1
    initial = combat_message()
    if outcome == "lost":
        initial["available_commands"] = ["end"]
    harness.sessions = [[initial, terminal_message(outcome)]]
    directory = tmp_path / "episode"
    result = rollout.run_episode(directory, config, 0)
    assert result["status"] == outcome
    assert result["actions"] == 1
    assert harness.received == 2
    trace = read_trace(directory)
    action = next(event for event in trace if event["kind"] == "action")
    execution = next(event for event in trace if event["kind"] == "execution")
    assert action["action_id"] == execution["action_id"]
    assert execution["status"] == "next_stable_state"
    assert any(event["kind"] == "terminal" and event["outcome"] == outcome for event in trace)
    assert harness.bridges[0].commands == (["play 1 0"] if outcome == "won" else ["end"])
    assert harness.games[0].closed and harness.bridges[0].closed


def test_step_truncation_records_response_but_sends_no_extra_action(tmp_path, config, harness):
    config["max_actions"] = 1
    harness.sessions = [[combat_message(), combat_message()]]
    directory = tmp_path / "episode"
    result = rollout.run_episode(directory, config, 0)
    assert (result["status"], result["reason"]) == ("truncated", "action_limit")
    assert harness.received == 2
    assert len(harness.bridges[0].commands) == 1
    trace = read_trace(directory)
    assert sum(event["kind"] == "execution" for event in trace) == 1
    assert not any(event["kind"] == "terminal" for event in trace)


def test_bridge_disconnect_keeps_pending_action_evidence_and_is_not_loss(tmp_path, config, harness):
    harness.sessions = [[combat_message(), BridgeDisconnected("connection lost")]]
    directory = tmp_path / "episode"
    result = rollout.run_episode(directory, config, 0)
    assert result["status"] == "infrastructure_failure"
    assert result["error_type"] == "BridgeDisconnected"
    assert result["invalid_actions"] == 0
    trace = read_trace(directory)
    assert sum(event["kind"] == "action" for event in trace) == 1
    assert not any(event["kind"] in {"terminal", "execution"} for event in trace)
    assert json.loads((directory / "result.json").read_text()) == result


def test_watchdog_disconnect_at_deadline_is_time_truncation(tmp_path, config, harness):
    def expire():
        harness.clock = config["episode_timeout"]
        return BridgeDisconnected("watchdog stopped game")

    harness.sessions = [[combat_message(), expire]]
    result = rollout.run_episode(tmp_path / "episode", config, 0)
    assert (result["status"], result["reason"]) == ("truncated", "episode_time_limit")


def test_unsupported_card_is_not_a_loss_or_sent_to_engine(tmp_path, config, harness):
    unsupported = combat_message()
    unsupported["game_state"]["combat_state"]["hand"][0]["id"] = "Corruption"
    harness.sessions = [[unsupported]]
    result = rollout.run_episode(tmp_path / "episode", config, 0)
    assert result["status"] == "unsupported_or_invalid"
    assert result["error_type"] == "UnsupportedStateError"
    assert harness.bridges[0].commands == []


def test_engine_rejection_is_attributed_to_the_pending_action(tmp_path, config, harness):
    harness.sessions = [
        [combat_message(), {"error": "Not enough energy", "ready_for_command": True}]
    ]
    directory = tmp_path / "episode"
    result = rollout.run_episode(directory, config, 0)
    assert result["status"] == "unsupported_or_invalid"
    assert result["invalid_actions"] == 1
    assert result["error_type"] == "BridgeCommandError"
    trace = read_trace(directory)
    action = next(event for event in trace if event["kind"] == "action")
    rejected = next(event for event in trace if event["kind"] == "execution")
    assert rejected["status"] == "rejected"
    assert rejected["action_id"] == action["action_id"]


def test_each_episode_records_its_own_profile_before_launch(tmp_path, config, harness, monkeypatch):
    profiles = [{"ironclad_unlock_level": "3"}, {"ironclad_unlock_level": "4"}]
    monkeypatch.setattr(rollout, "collect_profile", Mock(side_effect=profiles))
    harness.sessions = [[combat_message(), terminal_message()] for _ in range(2)]
    output = tmp_path / "run"
    result = rollout.rollout(output, config)
    assert result["status"] == "completed"
    for index, expected in enumerate(profiles):
        assert json.loads((output / f"episode-{index:04d}/profile.json").read_text()) == expected


def test_interruption_preserves_completed_episode_and_records_partial_episode(
    tmp_path, config, harness
):
    harness.sessions = [
        [combat_message(), terminal_message()],
        [combat_message(), KeyboardInterrupt()],
    ]
    output = tmp_path / "run"
    with pytest.raises(KeyboardInterrupt):
        rollout.rollout(output, config)
    manifest = json.loads((output / "manifest.json").read_text())
    complete_path = output / "episode-0000/result.json"
    completed_bytes = complete_path.read_bytes()
    assert manifest["status"] == "interrupted"
    assert [episode["status"] for episode in manifest["episodes"]] == ["won"]
    assert json.loads(completed_bytes)["status"] == "won"
    partial = json.loads((output / "episode-0001/result.json").read_text())
    assert partial["status"] == "interrupted"
    assert partial["actions"] == 1
    assert all(game.closed for game in harness.games)
    assert all(bridge.closed for bridge in harness.bridges)
    with pytest.raises(FileExistsError):
        rollout.rollout(output, config)
    assert complete_path.read_bytes() == completed_bytes


def test_infrastructure_failure_stops_batch_without_silent_retry(tmp_path, config, harness):
    harness.sessions = [[BridgeDisconnected("no game state")]]
    output = tmp_path / "run"
    result = rollout.rollout(output, config)
    assert result["status"] == "stopped"
    assert [episode["status"] for episode in result["episodes"]] == ["infrastructure_failure"]
    assert not (output / "episode-0001").exists()


def test_dirty_source_prevents_attributed_launch(tmp_path, config, harness, monkeypatch):
    monkeypatch.setattr(
        rollout.subprocess, "check_output", lambda *args, **kwargs: " M src/spire/x.py"
    )
    output = tmp_path / "run"
    with pytest.raises(ValueError, match="Commit implementation changes"):
        rollout.rollout(output, config)
    assert not output.exists()
    assert harness.games == []
