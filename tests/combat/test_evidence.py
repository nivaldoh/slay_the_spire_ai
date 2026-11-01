"""Adversarial record checks, independent of proof that a real engine ran."""

import copy
import json

import pytest
from combat_evidence import (
    combat_message,
    events,
    make_episode,
    make_language_success,
    make_policy_failure,
    read,
    run,
    set_result,
    write,
    write_events,
)

from spire.combat.evidence import (
    EvidenceError,
    audit_run,
    load_transitions,
    normalized_observation_fingerprint,
)
from spire.protocol import decision_from_message

__all__ = ["run"]


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


def test_successful_language_action_requires_verifiable_public_behavior(run):
    make_language_success(run)
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    assert audit["metrics"]["wins"] == audit["metrics"]["policy_attempts"] == 1
    assert audit["metrics"]["policy_failures"] == 0
    assert len(load_transitions(run)) == 1


@pytest.mark.parametrize(
    "change",
    [
        None,
        {"type": "heuristic"},
        {"prompt_format": "unknown"},
        {"parser_version": "unknown"},
        {"prompt_sha256": "0" * 64},
        {"chat_prompt_sha256": "not-a-hash"},
        {"chat_prompt_sha256": "G" * 64},
        {"max_prompt_tokens": True},
        {"max_prompt_tokens": 2049},
        {"prompt_tokens": True},
        {"prompt_tokens": 0},
        {"prompt_tokens": 2049},
        {"completion_tokens": True},
        {"completion_tokens": 0},
        {"completion_tokens": 13},
        {"completion_token_ids": [1, 2]},
        {"completion_token_ids": [1, 2, 3, 4, 5, True]},
        {"completion_token_ids": [1, 2, 3, 4, 5, -1]},
        {"completion_token_ids": "123456"},
        {"raw_completion": None},
        {"completion": None},
        {"completion": '{"a":1}'},
        {"completion": '{"a":0} explanation'},
        {"selected_index": True},
        {"selected_index": 1},
        {"inference_seconds": True},
        {"inference_seconds": -1},
        {"inference_seconds": float("inf")},
    ],
)
def test_language_success_cannot_hide_missing_or_inconsistent_behavior(run, change):
    make_language_success(run)
    directory = run / "episode-0000"
    trace = events(directory)
    if change is None:
        trace[5].pop("behavior")
    else:
        trace[5]["behavior"].update(change)
    write_events(directory, trace)
    audit = audit_run(run)
    assert not audit["valid"]
    assert audit["metrics"]["wins"] == audit["metrics"]["policy_attempts"] == 0


def test_policy_failure_retains_acknowledged_prefix_but_ppo_requires_complete_episode(run):
    make_policy_failure(run, after_action=True)
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    assert audit["episodes"][0]["starting_hp"] == 80
    assert audit["episodes"][0]["turns"] == 2
    assert audit["metrics"]["policy_attempts"] == audit["metrics"]["policy_failures"] == 1
    assert audit["metrics"]["valid_gameplay_episodes"] == 0
    (transition,) = load_transitions(run)
    assert transition["ingestible"] and not transition["terminal"]
    pytest.importorskip("torch")
    from spire.ppo.training import _join_episode

    with pytest.raises(EvidenceError, match="Training requires one audited complete episode"):
        _join_episode(run, None)


@pytest.mark.parametrize("kind", ["invalid_completion", "context_limit"])
def test_policy_failure_preserves_start_and_counts_separately(run, kind):
    make_policy_failure(run, kind=kind)
    audit = audit_run(run)
    assert audit["valid"], audit["issues"]
    metrics = audit["metrics"]
    assert metrics["policy_failures"] == metrics["policy_attempts"] == 1
    assert metrics["policy_attempt_win_rate"] == 0
    assert metrics["wins"] == metrics["losses"] == metrics["infrastructure_failures"] == 0
    assert metrics["invalid_actions"] == metrics["unsupported"] == 0
    assert metrics["win_rate"] is None
    assert audit["episodes"][0]["starting_hp"] == 80
    assert audit["episodes"][0]["combat_start_sha256"]
    assert not load_transitions(run)


@pytest.mark.parametrize(
    "change",
    [
        {"completion": '{"a":0}'},
        {"prompt_sha256": "0" * 64},
        {"prompt_tokens": True},
        {"completion_tokens": 13},
        {"max_prompt_tokens": 9999},
        {"inference_seconds": -1},
        {"kind": "invented_failure"},
        {"completion": None},
    ],
)
def test_policy_failure_cannot_hide_legal_output_or_invalid_metadata(run, change):
    make_policy_failure(run, **change)
    assert not audit_run(run)["valid"]


def test_context_failure_requires_actual_declared_overflow(run):
    make_policy_failure(run, kind="context_limit", prompt_tokens=2048)
    assert not audit_run(run)["valid"]


def test_policy_failure_requires_bound_decision_and_matching_result(run):
    make_policy_failure(run)
    directory = run / "episode-0000"
    trace = events(directory)
    trace[-2]["decision"]["id"] = "another-session:2"
    write_events(directory, trace)
    assert not audit_run(run)["valid"]


def test_policy_failure_status_cannot_replace_missing_event(run):
    set_result(run, status="policy_failure")
    assert not audit_run(run)["valid"]


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
