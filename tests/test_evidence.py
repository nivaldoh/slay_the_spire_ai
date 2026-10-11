"""Adversarial record checks, independent of proof that a real engine ran."""

import copy
import json

import pytest

from spire.evidence import (
    EvidenceError,
    audit_run,
    load_transitions,
    normalized_observation_fingerprint,
)
from spire.protocol import decision_from_message


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def read(path):
    return json.loads(path.read_text())


def events(directory):
    return [json.loads(line) for line in (directory / "trace.jsonl").read_text().splitlines()]


def write_events(directory, values):
    (directory / "trace.jsonl").write_text("".join(json.dumps(v) + "\n" for v in values))


def set_result(run, **changes):
    """Change all claimed-result copies, so engine evidence must catch tampering."""
    directory = run / "episode-0000"
    result = read(directory / "result.json")
    result.update(changes)
    write(directory / "result.json", result)
    trace = events(directory)
    trace[-1]["result"] = result
    write_events(directory, trace)
    manifest = read(run / "manifest.json")
    manifest["episodes"][0] = result
    write(run / "manifest.json", manifest)


def combat_message():
    return {
        "in_game": True,
        "ready_for_command": True,
        "available_commands": ["play", "end"],
        "game_state": {
            "class": "IRONCLAD",
            "ascension_level": 0,
            "floor": 1,
            "act": 1,
            "seed": 999,
            "current_hp": 80,
            "max_hp": 80,
            "room_phase": "COMBAT",
            "room_type": "MonsterRoom",
            "screen_type": "NONE",
            "screen_name": "NONE",
            "is_screen_up": False,
            "combat_state": {
                "turn": 1,
                "player": {"current_hp": 80, "max_hp": 80, "block": 0, "energy": 3},
                "hand": [
                    {
                        "id": "Strike_R",
                        "uuid": "private-card-id",
                        "name": "Strike",
                        "cost": 1,
                        "has_target": True,
                        "is_playable": True,
                        "upgrades": 0,
                    }
                ],
                "monsters": [
                    {
                        "id": "Louse",
                        "name": "Louse",
                        "current_hp": 6,
                        "max_hp": 6,
                        "block": 0,
                        "intent": "ATTACK",
                        "move_adjusted_damage": 5,
                        "move_hits": 1,
                        "is_gone": False,
                        "half_dead": False,
                        "move_id": 2,
                    }
                ],
            },
        },
    }


def make_episode(run, index=0, ending_hp=80, outcome="won"):
    directory = run / f"episode-{index:04d}"
    directory.mkdir()
    session = f"session-{index}"
    raw = combat_message()
    decision = decision_from_message(raw, session_id=session, sequence=2)
    action = decision.candidates[0]
    prefix_id = f"{session}:1:prefix"
    public = decision.to_dict()["observation"]
    terminal = copy.deepcopy(raw)
    terminal["game_state"].update(
        current_hp=ending_hp, room_phase="COMPLETE", screen_type="COMBAT_REWARD"
    )
    terminal["game_state"].pop("combat_state")
    if outcome == "lost":
        terminal["game_state"].update(
            screen_type="GAME_OVER", screen_name="DEATH", screen_state={"victory": False}
        )
    result = {
        "episode": index,
        "session_id": session,
        "status": outcome,
        "seed": "ABC",
        "policy": "random",
        "policy_seed": index,
        "actions": 2,
        "combat_actions": 1,
        "invalid_actions": 0,
        "floor": 1,
        "starting_hp": 80,
        "ending_hp": ending_hp,
        "turns": 1,
        "reset_seconds": 2.2,
        "combat_seconds": 2.8,
        "elapsed_seconds": 5.0,
        "combat_start_sha256": normalized_observation_fingerprint(public),
    }
    trace = [
        {"kind": "launch", "elapsed": 0.1, "pid": 123},
        {
            "kind": "observation",
            "elapsed": 1.0,
            "sequence": 1,
            "previous_action_id": None,
            "raw": {"in_game": False, "ready_for_command": True, "available_commands": ["start"]},
        },
        {
            "kind": "action",
            "elapsed": 1.1,
            "sequence": 1,
            "action_id": prefix_id,
            "command": "START IRONCLAD 0 ABC",
        },
        {
            "kind": "observation",
            "elapsed": 2.0,
            "sequence": 2,
            "previous_action_id": prefix_id,
            "raw": raw,
        },
        {
            "kind": "execution",
            "elapsed": 2.1,
            "sequence": 2,
            "action_id": prefix_id,
            "status": "next_stable_state",
        },
        {
            "kind": "decision",
            "elapsed": 2.3,
            "decision": decision.to_dict(),
            "selected_action_id": action.id,
        },
        {
            "kind": "action",
            "elapsed": 2.4,
            "sequence": 2,
            "action_id": action.id,
            "command": action.command,
        },
        {
            "kind": "observation",
            "elapsed": 4.0,
            "sequence": 3,
            "previous_action_id": action.id,
            "raw": terminal,
        },
        {
            "kind": "execution",
            "elapsed": 4.1,
            "sequence": 3,
            "action_id": action.id,
            "status": "next_stable_state",
        },
        {"kind": "terminal", "elapsed": 4.2, "sequence": 3, "outcome": outcome},
        {"kind": "result", "elapsed": 5.0, "result": result},
    ]
    write(directory / "result.json", result)
    write(directory / "combat_start.json", public)
    write(directory / "deployment.json", {"fixture": True})
    write_events(directory, trace)
    return result


@pytest.fixture
def run(tmp_path):
    directory = tmp_path / "run"
    directory.mkdir()
    result = make_episode(directory)
    write(
        directory / "manifest.json",
        {
            "schema_version": 1,
            "status": "completed",
            "source_revision": "a" * 40,
            "engine": "original",
            "scope": "first_combat",
            "config": {"episodes": 1, "game_seed": "ABC", "policy": "random", "policy_seed": 0},
            "episodes": [result],
        },
    )
    write(directory / "environment.json", {"fixture": True})
    (directory / "source.patch").write_text("")
    return directory


def test_verified_win_yields_one_safe_unique_transition(run):
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    assert audit["metrics"]["wins"] == 1
    assert audit["metrics"]["valid_gameplay_episodes"] == 1
    transitions = load_transitions(run)
    assert len(transitions) == 1
    assert transitions[0]["terminal"]
    assert transitions[0]["outcome"] == "won"
    serialized = json.dumps(transitions)
    assert '"seed"' not in serialized
    assert "private-card-id" not in serialized
    assert "move_id" not in serialized


def test_external_policy_rng_does_not_claim_an_episode_seed(run):
    set_result(run, policy_rng="externally_checkpointed", policy_seed=None)
    assert audit_run(run)["valid"]
    set_result(run, policy_seed=0)
    assert not audit_run(run)["valid"]


@pytest.mark.parametrize("change", ["outcome", "hp", "counts", "time"])
def test_changing_all_result_copies_cannot_override_engine_evidence(run, change):
    changes = {
        "outcome": {"status": "lost"},
        "hp": {"ending_hp": 1},
        "counts": {"actions": 99},
        "time": {"reset_seconds": 4.0},
    }
    set_result(run, **changes[change])
    assert not audit_run(run)["valid"]
    with pytest.raises(EvidenceError):
        load_transitions(run)


@pytest.mark.parametrize("kind", ["action", "decision", "execution", "terminal"])
def test_missing_combat_events_fail_audit(run, kind):
    directory = run / "episode-0000"
    trace = events(directory)
    index = next(i for i in range(5, len(trace)) if trace[i]["kind"] == kind)
    trace.pop(index)
    write_events(directory, trace)
    assert not audit_run(run)["valid"]


def test_action_must_match_selected_candidate_and_raw_observation(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace[6]["command"] = "end"
    write_events(directory, trace)
    assert "Selected command was changed" in str(audit_run(run)["issues"])


def test_policy_observation_cannot_be_rewritten_or_contain_private_fields(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace[5]["decision"]["observation"]["seed"] = 999
    write_events(directory, trace)
    assert "Decision differs from raw state" in str(audit_run(run)["issues"])


def test_stale_action_sequence_is_rejected(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace[6]["sequence"] = 1
    write_events(directory, trace)
    assert "stale observation sequence" in str(audit_run(run)["issues"])


def test_second_outstanding_command_is_rejected(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace.insert(7, copy.deepcopy(trace[6]))
    write_events(directory, trace)
    assert "outstanding command" in str(audit_run(run)["issues"])


def test_execution_must_reference_actual_pending_action(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace[8]["action_id"] = "other-session:2:play:0:0"
    write_events(directory, trace)
    assert "different action" in str(audit_run(run)["issues"])


def test_duplicate_execution_cannot_duplicate_ingestion(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace.insert(9, copy.deepcopy(trace[8]))
    write_events(directory, trace)
    assert "Duplicate execution" in str(audit_run(run)["issues"])


def test_manifest_result_linkage_is_verified(run):
    manifest = read(run / "manifest.json")
    manifest["episodes"][0]["ending_hp"] = 999
    write(run / "manifest.json", manifest)
    assert "Manifest result differs" in str(audit_run(run)["issues"])


def test_missing_manifest_episode_is_detected(run):
    manifest = read(run / "manifest.json")
    manifest["episodes"] = []
    write(run / "manifest.json", manifest)
    assert "absent from manifest" in str(audit_run(run)["issues"])


def test_adding_same_run_to_ingestion_twice_fails(run):
    with pytest.raises(EvidenceError, match="Duplicate transition ingestion"):
        load_transitions([run, run])


def test_reset_and_shared_action_prefix_comparison(run):
    second = make_episode(run, 1)
    manifest = read(run / "manifest.json")
    manifest["episodes"].append(second)
    manifest["config"]["episodes"] = 2
    write(run / "manifest.json", manifest)
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    compare = audit["reset_comparison"]
    assert compare["all_initial_states_equal"]
    assert compare["comparisons"][0]["shared_combat_actions"] == 1
    assert compare["comparisons"][0]["shared_action_states_equal"]
    assert len(load_transitions(run)) == 2


def test_equal_reset_does_not_hide_different_shared_action_successor(run):
    second = make_episode(run, 1, ending_hp=75)
    manifest = read(run / "manifest.json")
    manifest["episodes"].append(second)
    manifest["config"]["episodes"] = 2
    write(run / "manifest.json", manifest)
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    pair = audit["reset_comparison"]["comparisons"][0]
    assert pair["initial_state_equal"]
    assert not pair["shared_action_states_equal"]
    assert pair["differences"] == [{"step": 0, "state": "next_observation"}]


def test_clean_truncation_is_not_a_loss_and_only_completed_transitions_ingest(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace = trace[:7] + [trace[-1]]
    write_events(directory, trace)
    set_result(run, status="truncated", ending_hp=None, reason="action_limit")
    manifest = read(run / "manifest.json")
    manifest["status"] = "stopped"
    write(run / "manifest.json", manifest)
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    assert audit["metrics"]["truncated"] == 1
    assert audit["metrics"]["losses"] == 0
    assert audit["metrics"]["win_rate"] is None
    assert load_transitions(run) == []


def test_interrupted_partial_trace_is_not_accepted_or_scored(run):
    directory = run / "episode-0000"
    trace = events(directory)
    write_events(directory, trace[:7])
    result = read(directory / "result.json")
    result["status"] = "interrupted"
    write(directory / "result.json", result)
    audit = audit_run(run)
    assert not audit["valid"]
    assert audit["metrics"]["interrupted"] == 1
    assert audit["metrics"]["losses"] == 0
    assert audit["metrics"]["valid_gameplay_episodes"] == 0


def test_bridge_rejection_is_not_a_gameplay_loss(run):
    directory = run / "episode-0000"
    trace = events(directory)
    action_id = trace[6]["action_id"]
    trace[7]["raw"] = {"error": "illegal target", "ready_for_command": True}
    trace[8] = {
        "kind": "execution",
        "elapsed": 4.1,
        "action_id": action_id,
        "status": "rejected",
        "error": "illegal target",
    }
    trace.pop(9)
    write_events(directory, trace)
    set_result(
        run,
        status="unsupported_or_invalid",
        invalid_actions=1,
        error_type="BridgeCommandError",
        error="illegal target",
        ending_hp=None,
    )
    manifest = read(run / "manifest.json")
    manifest["status"] = "stopped"
    write(run / "manifest.json", manifest)
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    assert audit["metrics"]["invalid_actions"] == 1
    assert audit["metrics"]["losses"] == 0
    assert load_transitions(run) == []


def test_unstable_intermediate_observation_retains_outstanding_action(run):
    directory = run / "episode-0000"
    trace = events(directory)
    unstable = copy.deepcopy(trace[7])
    unstable["elapsed"] = 3.0
    unstable["raw"]["ready_for_command"] = False
    for index in (7, 8, 9):
        trace[index]["sequence"] = 4
    trace.insert(7, unstable)
    write_events(directory, trace)
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    assert load_transitions(run)[0]["next_sequence"] == 4


def test_hp_zero_without_terminal_engine_state_is_not_a_loss(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace[7]["raw"] = combat_message()
    trace[7]["raw"]["game_state"]["current_hp"] = 0
    trace[9]["outcome"] = "lost"
    write_events(directory, trace)
    set_result(run, status="lost", ending_hp=0)
    audit = audit_run(run)
    assert not audit["valid"]
    assert audit["metrics"]["losses"] == 0


def test_fake_unlock_terminal_does_not_count_as_loss(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace[7]["raw"]["game_state"].update(
        screen_type="GAME_OVER", screen_name="UNLOCK", screen_state={"victory": False}
    )
    write_events(directory, trace)
    audit = audit_run(run)
    assert not audit["valid"]


def test_fingerprint_accepts_immutable_protocol_observation():
    decision = decision_from_message(combat_message(), session_id="x", sequence=0)
    assert normalized_observation_fingerprint(decision.observation) == (
        normalized_observation_fingerprint(decision.to_dict()["observation"])
    )


def add_settling_action(run):
    directory = run / "episode-0000"
    trace = events(directory)
    stable_raw = copy.deepcopy(trace[3]["raw"])
    trace[3]["raw"]["available_commands"].append("wait")
    trace[3]["raw"]["game_state"]["combat_state"]["monsters"][0]["intent"] = "DEBUG"
    settled = decision_from_message(stable_raw, session_id="session-0", sequence=3)
    selected = settled.candidates[0]
    trace[5]["decision"] = settled.to_dict()
    trace[5]["selected_action_id"] = selected.id
    trace[6].update(action_id=selected.id, sequence=3)
    trace[7].update(previous_action_id=selected.id, sequence=4)
    trace[8].update(action_id=selected.id, sequence=4)
    trace[9]["sequence"] = 4
    settle_id = "session-0:2:settle"
    trace[5:5] = [
        {
            "kind": "action",
            "elapsed": 2.15,
            "sequence": 2,
            "action_id": settle_id,
            "command": "WAIT 60",
            "role": "settle",
        },
        {
            "kind": "observation",
            "elapsed": 2.2,
            "sequence": 3,
            "previous_action_id": settle_id,
            "raw": stable_raw,
        },
        {
            "kind": "execution",
            "elapsed": 2.25,
            "sequence": 3,
            "action_id": settle_id,
            "status": "next_stable_state",
        },
    ]
    write_events(directory, trace)
    set_result(run, actions=3)
    manifest = read(run / "manifest.json")
    manifest["prefix_version"] = "neow-maxhp-or-gold-leftmost-settled-v2"
    write(run / "manifest.json", manifest)


def test_initial_debug_settling_is_audited_and_not_ingested_as_policy(run):
    add_settling_action(run)
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    episode = audit["episodes"][0]
    assert episode["actions"] == 3
    assert episode["combat_actions"] == 1
    assert episode["initial_intents_settled"]
    transitions = load_transitions(run)
    assert len(transitions) == 1
    assert transitions[0]["sequence"] == 3
    assert transitions[0]["command"] == "play 1 0"


@pytest.mark.parametrize("change", ["no_debug", "wrong_wait"])
def test_settling_cannot_hide_arbitrary_nonpolicy_actions(run, change):
    add_settling_action(run)
    directory = run / "episode-0000"
    trace = events(directory)
    if change == "no_debug":
        trace[3]["raw"]["game_state"]["combat_state"]["monsters"][0]["intent"] = "BUFF"
    else:
        trace[5]["command"] = "WAIT 1000"
    write_events(directory, trace)
    assert not audit_run(run)["valid"]


def test_settled_contract_rejects_initial_debug_policy_decision(run):
    directory = run / "episode-0000"
    trace = events(directory)
    raw = trace[3]["raw"]
    raw["game_state"]["combat_state"]["monsters"][0]["intent"] = "DEBUG"
    generated = decision_from_message(raw, session_id="session-0", sequence=2).to_dict()
    trace[5]["decision"] = generated
    write_events(directory, trace)
    write(directory / "combat_start.json", generated["observation"])
    set_result(
        run, combat_start_sha256=normalized_observation_fingerprint(generated["observation"])
    )
    manifest = read(run / "manifest.json")
    manifest["prefix_version"] = "neow-maxhp-or-gold-leftmost-settled-v2"
    write(run / "manifest.json", manifest)
    assert "initial DEBUG policy decision" in str(audit_run(run)["issues"])


def test_malformed_or_physically_truncated_jsonl_fails_closed(run):
    path = run / "episode-0000" / "trace.jsonl"
    path.write_text(path.read_text().rstrip("\n"))
    audit = audit_run(run)
    assert not audit["valid"]
    assert audit["metrics"]["losses"] == 0
    with pytest.raises(EvidenceError):
        load_transitions(run)


def test_observed_engine_terminal_cannot_be_reclassified_as_unsupported(run):
    directory = run / "episode-0000"
    trace = events(directory)
    trace.pop(9)
    write_events(directory, trace)
    set_result(run, status="unsupported_or_invalid")
    manifest = read(run / "manifest.json")
    manifest["status"] = "stopped"
    write(run / "manifest.json", manifest)
    assert "missing its terminal event" in str(audit_run(run)["issues"])
