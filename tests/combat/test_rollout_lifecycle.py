"""Runner lifecycle regressions; these mocked states do not certify the engine."""

import json
import socket
from unittest.mock import Mock

import pytest
from combat_support import combat_message, harness, terminal_message

from gameai import provenance
from spire.combat import rollout
from spire.engine.bridge import BridgeDisconnected, BridgeServer

__all__ = ["harness"]


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


def test_initial_debug_intent_settles_before_policy_decision(tmp_path, config, harness):
    initial = combat_message()
    initial["available_commands"].append("wait")
    initial["game_state"]["combat_state"]["monsters"][0]["intent"] = "DEBUG"
    harness.sessions = [[initial, combat_message(), terminal_message()]]
    result = rollout.run_episode(tmp_path / "episode", config, 0)
    assert result["status"] == "won"
    assert harness.bridges[0].commands == ["WAIT 60", "play 1 0"]
    trace = read_trace(tmp_path / "episode")
    decisions = [event for event in trace if event["kind"] == "decision"]
    assert len(decisions) == 1
    assert (
        decisions[0]["decision"]["observation"]["combat_state"]["monsters"][0]["intent"] == "BUFF"
    )


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


def test_occupied_bridge_port_records_failure_before_deployment_or_game_launch(
    tmp_path, config, harness, monkeypatch
):
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        monkeypatch.setattr(rollout, "BRIDGE_PORT", occupied.getsockname()[1])
        monkeypatch.setattr(rollout, "wsl_bridge_host", lambda: "127.0.0.1")
        monkeypatch.setattr(rollout, "BridgeServer", BridgeServer)
        result = rollout.run_episode(tmp_path / "episode", config, 0)
    assert result["status"] == "infrastructure_failure"
    assert result["error_type"] == "BridgeError"
    assert result["actions"] == 0
    assert not harness.games
    rollout.prepare_runtime.assert_not_called()
    assert not any(event["kind"] == "launch" for event in read_trace(tmp_path / "episode"))


def test_endpoint_discovery_failure_preserves_zero_action_attempt_without_launch(
    tmp_path, config, harness, monkeypatch
):
    monkeypatch.setattr(
        rollout, "wsl_bridge_host", Mock(side_effect=RuntimeError("eth0 is ambiguous"))
    )
    directory = tmp_path / "episode"
    result = rollout.run_episode(directory, config, 0)
    assert result["status"] == "infrastructure_failure" and result["actions"] == 0
    assert result["error"] == "eth0 is ambiguous"
    assert not harness.bridges and not harness.games
    rollout.prepare_runtime.assert_not_called()
    assert [event["kind"] for event in read_trace(directory)] == ["result"]


def test_each_episode_rediscovers_endpoint_and_deploys_exact_bound_address(
    tmp_path, config, harness
):
    rollout.wsl_bridge_host.side_effect = ["172.18.34.183", "172.18.35.192"]
    harness.sessions = [[BridgeDisconnected("probe")], [BridgeDisconnected("probe")]]
    for index in range(2):
        rollout.run_episode(tmp_path / f"episode-{index}", config, index)
    assert rollout.wsl_bridge_host.call_count == 2
    assert [bridge.address for bridge in harness.bridges] == [
        ("172.18.34.183", 19876), ("172.18.35.192", 19876),
    ]
    assert [call.args for call in rollout.prepare_runtime.call_args_list] == [
        bridge.address for bridge in harness.bridges
    ]
    assert all(
        call.kwargs == {"timeout": config["bridge_timeout"]}
        for call in rollout.prepare_runtime.call_args_list
    )


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
    assert [episode["status"] for episode in manifest["episodes"]] == ["won", "interrupted"]
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
        provenance.subprocess, "check_output", lambda *args, **kwargs: " M src/spire/x.py"
    )
    output = tmp_path / "run"
    with pytest.raises(ValueError, match="Commit implementation changes"):
        rollout.rollout(output, config)
    assert not output.exists()
    assert harness.games == []
