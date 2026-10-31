"""The standalone training acceptance audit rejects damaged or misleading evidence."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

import ppo_training_support as training_fixtures  # noqa: E402

from gameai.provenance import REPO_ROOT  # noqa: E402
from spire.ppo import training  # noqa: E402

training_setup = training_fixtures.setup

SCRIPT = REPO_ROOT / "scripts/audit_ppo_training.py"
SPEC = importlib.util.spec_from_file_location("audit_training_script", SCRIPT)
audit_script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_script)


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value) + "\n")


@pytest.fixture
def saved_run(tmp_path, training_setup):
    config, _ = training_setup
    output = tmp_path / "train"
    training.train(output, config)
    return output


def rewrite_checkpoint(run, change):
    """Rehash a semantically forged checkpoint, bypassing only the bytes check."""
    pointer = read(run / "training-state.json")
    old_path = run / pointer["path"]
    payload = torch.load(old_path, map_location="cpu", weights_only=True)
    change(payload)
    temporary = run / "checkpoints" / "rewrite.tmp"
    torch.save(payload, temporary)
    digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
    path = temporary.with_name(f"{pointer['generation']:06d}-{digest}.pt")
    temporary.rename(path)
    old_path.unlink()
    pointer.update(path=str(path.relative_to(run)), sha256=digest)
    write(run / "training-state.json", pointer)


def test_saved_training_audit_reconstructs_behavior_and_parameter_changes(saved_run):
    report = audit_script.audit_training(saved_run)
    assert report["valid"], report["errors"]
    assert all(report["checks"].values())
    assert report["completed_episodes"] == report["consumed_transitions"] == 2
    assert report["updates"] == 1
    assert report["parameter_changes"]["actor"]["changed_elements"] > 0
    assert report["parameter_changes"]["context"]["changed_elements"] > 0
    assert report["max_recorded_logprob_error"] <= 1e-6
    assert report["max_recorded_value_error"] <= 1e-6
    assert "probe_deadline_retained" not in report["checks"]


@pytest.mark.parametrize("damage", ["missing", "bytes", "record"])
def test_damaged_artifact_fails_closed(saved_run, damage):
    summary = read(saved_run / "training.json")
    path = Path(summary["artifact_path"])
    if damage == "missing":
        path.unlink()
    elif damage == "bytes":
        path.write_bytes(path.read_bytes() + b"tampered")
    else:
        record = read(path.with_suffix(".json"))
        record["sha256"] = "0" * 64
        write(path.with_suffix(".json"), record)
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert any("artifact" in error.lower() for error in report["errors"])


@pytest.mark.parametrize("target", ["current", "ancestor"])
@pytest.mark.parametrize("damage", ["missing", "bytes"])
def test_missing_or_tampered_checkpoint_fails_closed(saved_run, target, damage):
    if target == "current":
        path = saved_run / read(saved_run / "training-state.json")["path"]
    else:
        initial = read(saved_run / "training.json")["initial_artifact"]
        ancestor = initial["training_checkpoint_sha256"]
        (path,) = (saved_run / "checkpoints").glob(f"*-{ancestor}.pt")
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(path.read_bytes() + b"tampered")
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert any("checkpoint" in error.lower() for error in report["errors"])


def test_duplicate_ingestion_rejected_even_with_valid_checkpoint_digest(saved_run):
    def duplicate(payload):
        ids = payload["training"]["consumed_ids"]
        ids.append(ids[0])

    rewrite_checkpoint(saved_run, duplicate)
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert not report["checks"]["consumed_ids_unique"]
    assert not report["checks"]["consumption_matches_audited_episodes"]


def test_forged_behavior_probability_rejected(saved_run):
    trace = saved_run / "runs/attempt-0000/episode-0000/trace.jsonl"
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    decision = next(event for event in events if event["kind"] == "decision")
    decision["behavior"]["old_logprob"] += 0.1
    trace.write_text("".join(json.dumps(event) + "\n" for event in events))
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert not report["checks"]["behavior_probabilities_match"]


def test_final_export_must_equal_final_committed_policy(saved_run):
    def mutate_model(payload):
        payload["learner"]["policy"]["model"]["actor.0.weight"][0, 0] += 0.1

    rewrite_checkpoint(saved_run, mutate_model)
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert not report["checks"]["final_export_matches_checkpoint"]


def test_nonfinite_metrics_produce_valid_json_failure_report(saved_run, tmp_path, capsys):
    def mutate_metrics(payload):
        payload["training"]["update_history"][0]["loss"] = float("nan")

    rewrite_checkpoint(saved_run, mutate_metrics)
    output = tmp_path / "audit.json"
    assert audit_script.main([str(saved_run), str(output)]) == 1
    report = read(output)
    assert not report["valid"]
    assert not report["checks"]["optimizer_metrics_finite"]
    assert json.loads(capsys.readouterr().out) == report


def test_cli_is_read_only_and_returns_nonzero_on_missing_input(saved_run, tmp_path, capsys):
    checkpoint = saved_run / "training-state.json"
    before = checkpoint.read_bytes()
    with pytest.raises(SystemExit) as error:
        audit_script.main([str(saved_run), str(checkpoint)])
    assert error.value.code == 2
    assert checkpoint.read_bytes() == before
    output = tmp_path / "missing.json"
    assert audit_script.main([str(tmp_path / "missing-run"), str(output)]) == 1
    assert not read(output)["valid"]
    capsys.readouterr()


def test_resume_deadline_cannot_be_extended_in_rehashed_checkpoint(saved_run):
    def extend(payload):
        payload["training"]["deadline_unix"] += 60

    rewrite_checkpoint(saved_run, extend)
    pointer = read(saved_run / "training-state.json")
    pointer["deadline_unix"] += 60
    write(saved_run / "training-state.json", pointer)
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert not report["checks"]["deadline_retained"]


@pytest.mark.parametrize("damage", ["missing", "changed"])
def test_captured_suite_must_match_checkpoint(saved_run, damage):
    path = saved_run / "suite.json"
    if damage == "missing":
        path.unlink()
    else:
        suite = read(path)
        suite["game_seed"] = "DIFFERENT"
        write(path, suite)
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert "suite" in report["errors"][0].lower()


def test_optimizer_metrics_cannot_be_omitted(saved_run):
    def remove_metrics(payload):
        del payload["training"]["update_history"][0]["loss"]

    rewrite_checkpoint(saved_run, remove_metrics)
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert "Missing numeric PPO metrics" in report["errors"][0]


def test_summary_status_and_deadline_are_verified(saved_run):
    path = saved_run / "training.json"
    summary = read(path)
    summary.update(status="completed", stop_reason="invented", deadline_unix=-1)
    write(path, summary)
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert not report["checks"]["summary_status_and_budget_match"]


def test_episode_source_must_match_training_provenance(saved_run):
    path = saved_run / "runs/attempt-0000/manifest.json"
    manifest = read(path)
    manifest["source_revision"] = "f" * 40
    write(path, manifest)
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert "source_revision differs from training" in report["errors"][0]


@pytest.fixture
def pending_run(tmp_path, training_setup, monkeypatch):
    config, _ = training_setup
    clock = [1000.0]
    collect = training.run_episode

    def collect_then_expire(*args, **kwargs):
        result = collect(*args, **kwargs)
        clock[0] += config["time_budget_seconds"] + 1
        return result

    monkeypatch.setattr(training.time, "time", lambda: clock[0])
    monkeypatch.setattr(training, "run_episode", collect_then_expire)
    output = tmp_path / "pending"
    result = training.train(output, config)
    assert result["status"] == "budget_exhausted"
    assert result["pending_batch_steps"] == 1
    return output


def test_budget_exhaustion_can_retain_complete_unconsumed_batch(pending_run):
    report = audit_script.audit_training(pending_run)
    assert report["valid"], report["errors"]
    assert report["updates"] == report["consumed_transitions"] == 0
    assert report["unconsumed_completed_transitions"] == 1
    assert report["checks"]["pending_behavior_matches_current_model"]


@pytest.mark.parametrize("damage", ["drop", "repeat", "step_count"])
def test_pending_batch_must_account_for_complete_unconsumed_episodes(pending_run, damage):
    def mutate(payload):
        state = payload["training"]
        if damage == "drop":
            state["batch_runs"], state["batch_steps"] = [], 0
        elif damage == "repeat":
            state["batch_runs"] *= 2
        else:
            state["batch_steps"] += 1

    rewrite_checkpoint(pending_run, mutate)
    report = audit_script.audit_training(pending_run)
    assert not report["valid"]
    failed = [key for key, valid in report["checks"].items() if not valid]
    assert any(
        key.startswith("pending_") or key == "all_completed_runs_accounted_for" for key in failed
    )


def test_pending_batch_cannot_include_consumed_episode(saved_run):
    def mutate(payload):
        state = payload["training"]
        state["batch_runs"] = [state["update_history"][0]["runs"][0]]
        state["batch_steps"] = 1

    rewrite_checkpoint(saved_run, mutate)
    report = audit_script.audit_training(saved_run)
    assert not report["valid"]
    assert not report["checks"]["pending_disjoint_from_consumed"]
    assert not report["checks"]["pending_behavior_matches_current_model"]


@pytest.fixture
def saved_catalog_run(tmp_path, training_setup, monkeypatch):
    config, _ = training_setup
    config = training_fixtures.make_catalog_config(config, monkeypatch)
    output = tmp_path / "catalog-training"
    training.train(output, config)
    return output


def test_catalog_audit_reconstructs_round_robin_reservations_and_child_scenarios(saved_catalog_run):
    report = audit_script.audit_training(saved_catalog_run)
    assert report["valid"], report["errors"]
    assert report["checks"]["catalog_reservations_match_checkpoints"]
    assert report["checks"]["summary_catalog_matches_checkpoint"]
    assert report["consumed_transitions"] == 2


@pytest.mark.parametrize("damage", ["cursor", "assignment", "schedule", "path"])
def test_catalog_checkpoint_assignment_forgery_is_rejected(saved_catalog_run, damage):
    def mutate(payload):
        state = payload["training"]
        if damage == "cursor":
            state["scenario_cursor"] += 1
        elif damage == "assignment":
            state["attempts"][0]["scenario"]["scenario_id"] = "cultist-second"
        elif damage == "schedule":
            state["attempts"][0]["scenario"]["schedule_index"] = 1
        else:
            state["attempts"][0]["run"] = "runs/attempt-0001"

    rewrite_checkpoint(saved_catalog_run, mutate)
    report = audit_script.audit_training(saved_catalog_run)
    assert not report["valid"]
    assert any(
        "cursor" in error.lower() or "assignment" in error.lower() for error in report["errors"]
    )


@pytest.mark.parametrize("filename", ["manifest.json", "environment.json"])
def test_catalog_child_assignment_provenance_cannot_drift(saved_catalog_run, filename):
    path = saved_catalog_run / "runs/attempt-0000" / filename
    record = read(path)
    record["scenario"]["scenario_id"] = "cultist-second"
    write(path, record)
    report = audit_script.audit_training(saved_catalog_run)
    assert not report["valid"]
    assert "scenario differs from reserved catalog assignment" in report["errors"][0]


def test_catalog_pending_reservation_forgery_in_historical_checkpoint_rejected(saved_catalog_run):
    checkpoint = None
    for path in sorted((saved_catalog_run / "checkpoints").glob("*.pt")):
        payload = torch.load(path, map_location="cpu", weights_only=True)
        if payload["training"]["pending_scenario"] is not None:
            checkpoint = path
            break
    assert checkpoint is not None
    payload["training"]["pending_scenario"]["scenario_id"] = "cultist-second"
    temporary = checkpoint.with_suffix(".tmp")
    torch.save(payload, temporary)
    actual = hashlib.sha256(temporary.read_bytes()).hexdigest()
    replacement = checkpoint.with_name(f"{payload['training']['generation']:06d}-{actual}.pt")
    temporary.rename(replacement)
    checkpoint.unlink()
    report = audit_script.audit_training(saved_catalog_run)
    assert not report["valid"]
    assert "Pending scenario differs from round-robin reservation" in report["errors"][0]


def test_coherent_catalog_episode_with_wrong_actual_start_is_rejected(saved_catalog_run):
    run = saved_catalog_run / "runs/attempt-0000"
    episode = run / "episode-0000"
    trace = episode / "trace.jsonl"
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    result = read(episode / "result.json")
    start = next(
        event for event in events if event["kind"] == "observation" and event["sequence"] == 2
    )
    start["raw"]["game_state"]["current_hp"] = 79
    start["raw"]["game_state"]["combat_state"]["player"]["current_hp"] = 79
    public = training_fixtures.decision_from_message(
        start["raw"], session_id=result["session_id"], sequence=2
    ).to_dict()
    next(event for event in events if event["kind"] == "decision")["decision"] = public
    result["starting_hp"] = 79
    result["combat_start_sha256"] = training_fixtures.normalized_observation_fingerprint(
        public["observation"]
    )
    events[-1]["result"] = result
    trace.write_text("".join(json.dumps(event) + "\n" for event in events))
    write(episode / "result.json", result)
    write(episode / "combat_start.json", public["observation"])
    manifest = read(run / "manifest.json")
    manifest["episodes"] = [result]
    write(run / "manifest.json", manifest)
    assert audit_script.audit_run(run)["valid"]  # Coherent; wrong for its assigned scenario.
    report = audit_script.audit_training(saved_catalog_run)
    assert not report["valid"]
    assert "Actual combat start differs from assigned scenario" in report["errors"][0]
