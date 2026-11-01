"""Training transactions with synthetic collectors; these never launch the game."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from ppo_training_support import (  # noqa: E402
    catalog_setup,
    read,
    setup,
    write,
)

from spire.combat.evidence import EvidenceError  # noqa: E402
from spire.ppo import training  # noqa: E402
from spire.ppo.learning import PPOTrainer  # noqa: E402

__all__ = ["catalog_setup", "setup"]


def test_actual_neural_update_creates_audited_data_and_stable_artifact(tmp_path, setup):
    config, calls = setup
    output = tmp_path / "train"
    result = training.train(output, config)
    assert result["status"] == "completed"
    assert result["updates"] == 1
    assert result["consumed_transitions"] == 2
    assert result["completed_episodes"] == len(calls) == 2
    assert result["initial_artifact"]["model_sha256"] != result["model_sha256"]
    assert result["update_history"][0]["parameters_changed"]
    record = read(Path(result["artifact_record"]))
    assert training._digest(Path(result["artifact_path"])) == record["sha256"]
    state, payload, _ = training._load_checkpoint(output)
    assert len(state["consumed_ids"]) == len(set(state["consumed_ids"])) == 2
    assert payload["learner"]["optimizer"]["state"]
    assert "python_rng" in payload and "torch_rng" in payload


def test_resume_completed_job_never_recollects_or_reingests(tmp_path, setup):
    config, calls = setup
    output = tmp_path / "train"
    original = training.train(output, config)
    resumed = training.train(output, resume=True)
    assert len(calls) == 2
    assert resumed["model_sha256"] == original["model_sha256"]
    assert resumed["consumed_transitions"] == 2
    assert resumed["updates"] == 1
    assert resumed["artifact_path"] == original["artifact_path"]


def test_recorded_learning_rate_controls_optimizer_and_cannot_change_on_resume(tmp_path, setup):
    config, calls = setup
    config["learning_rate"] = 0.003
    output = tmp_path / "train"
    result = training.train(output, config)
    state, payload, _ = training._load_checkpoint(output)
    assert state["config"]["learning_rate"] == 0.003
    assert payload["learner"]["config"]["learning_rate"] == 0.003
    assert {group["lr"] for group in payload["learner"]["optimizer"]["param_groups"]} == {0.003}
    resumed = training.train(output, resume=True)
    assert resumed["model_sha256"] == result["model_sha256"]
    assert len(calls) == 2
    with pytest.raises(ValueError, match="Resume configuration differs"):
        training.train(output, {**config, "learning_rate": 0.0003}, resume=True)


@pytest.mark.parametrize("rate", [0, -0.1, float("nan"), float("inf"), True, "0.003"])
def test_invalid_learning_rate_is_rejected_before_creating_run(tmp_path, setup, rate):
    config, calls = setup
    output = tmp_path / "train"
    with pytest.raises(ValueError, match="learning_rate"):
        training.train(output, {**config, "learning_rate": rate})
    assert not output.exists()
    assert calls == []


def test_legacy_unconfigured_learning_rate_preserves_trainer_default():
    trainer = training._make_trainer({"seed": 0, "torch_num_threads": 1})
    assert trainer.config["learning_rate"] == 0.0003
    assert trainer.optimizer.param_groups[0]["lr"] == 0.0003


def test_completed_uncheckpointed_episode_restores_sampler_and_optimizer_exactly(
    tmp_path, setup, monkeypatch
):
    config, calls = setup
    uninterrupted = training.train(tmp_path / "uninterrupted", config)
    original_collector = training.run_episode
    crashed = False

    def crash_after_collection(*args, **kwargs):
        nonlocal crashed
        value = original_collector(*args, **kwargs)
        if not crashed:
            crashed = True
            raise KeyboardInterrupt
        return value

    output = tmp_path / "resumed"
    monkeypatch.setattr(training, "run_episode", crash_after_collection)
    with pytest.raises(KeyboardInterrupt):
        training.train(output, config)
    checkpoint, _, _ = training._load_checkpoint(output)
    assert checkpoint["phase"] == "collecting"
    assert checkpoint["pending_episode"] == "runs/attempt-0000"
    resumed = training.train(output, resume=True)
    assert len(calls) == 4  # two reference attempts, two recovered-run attempts
    assert resumed["model_sha256"] == uninterrupted["model_sha256"]
    assert resumed["consumed_transitions"] == 2


def test_interrupted_optimizer_rolls_back_to_preupdate_without_recollecting(
    tmp_path, setup, monkeypatch
):
    config, calls = setup
    reference = training.train(tmp_path / "reference", config)
    original_update = PPOTrainer.update
    interrupted = False

    def crash_after_update(self, episodes):
        nonlocal interrupted
        metrics = original_update(self, episodes)
        if not interrupted:
            interrupted = True
            raise KeyboardInterrupt
        return metrics

    monkeypatch.setattr(PPOTrainer, "update", crash_after_update)
    output = tmp_path / "resumed"
    with pytest.raises(KeyboardInterrupt):
        training.train(output, config)
    state, _, _ = training._load_checkpoint(output)
    assert state["phase"] == "updating"
    assert state["updates"] == 0 and state["consumed_ids"] == []
    assert read(output / "training.json")["updates"] == 0
    resumed = training.train(output, resume=True)
    assert len(calls) == 4
    assert resumed["model_sha256"] == reference["model_sha256"]
    assert resumed["updates"] == 1
    assert resumed["consumed_transitions"] == 2


def test_interrupted_preparation_reserves_index_before_writing_any_files(
    tmp_path, setup, monkeypatch
):
    config, calls = setup
    original_initialize = training._initialize_attempt

    def interrupt(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(training, "_initialize_attempt", interrupt)
    output = tmp_path / "resumed"
    with pytest.raises(KeyboardInterrupt):
        training.train(output, config)
    state, _, _ = training._load_checkpoint(output)
    assert state["next_attempt"] == 1
    assert not (output / "runs/attempt-0000").exists()
    monkeypatch.setattr(training, "_initialize_attempt", original_initialize)
    result = training.train(output, resume=True)
    assert len(calls) == 1
    assert calls[0].endswith("attempt-0001/episode-0000")
    assert result["attempt_records"][0]["recovered_abandoned"]
    assert result["completed_episodes"] == result["consumed_transitions"] == 1


def test_partial_live_episode_is_preserved_and_new_index_is_used(tmp_path, setup, monkeypatch):
    config, calls = setup
    original_collect = training.run_episode

    def interrupt(directory, config, episode, *, policy):
        directory.mkdir()
        (directory / "trace.jsonl").write_text('{"kind":"unfinished"')
        raise KeyboardInterrupt

    monkeypatch.setattr(training, "run_episode", interrupt)
    output = tmp_path / "resumed"
    with pytest.raises(KeyboardInterrupt):
        training.train(output, config)
    trace = output / "runs/attempt-0000/episode-0000/trace.jsonl"
    before = trace.read_bytes()
    monkeypatch.setattr(training, "run_episode", original_collect)
    result = training.train(output, resume=True)
    assert trace.read_bytes() == before
    assert result["completed_episodes"] == 1
    assert result["consumed_transitions"] == 1
    assert len(calls) == 1


def test_expired_absolute_budget_is_not_replenished_on_resume(tmp_path, setup, monkeypatch):
    config, calls = setup
    config["time_budget_seconds"] = 10
    clock = [100.0]
    monkeypatch.setattr(training, "time", SimpleNamespace(time=lambda: clock[0]))
    original_collect = training.run_episode

    def consume_budget(*args, **kwargs):
        assert args[1]["episode_timeout"] <= 10
        clock[0] += 20
        return original_collect(*args, **kwargs)

    monkeypatch.setattr(training, "run_episode", consume_budget)
    output = tmp_path / "train"
    first = training.train(output, config)
    assert first["status"] == "budget_exhausted"
    assert first["deadline_unix"] == 110
    assert first["updates"] == 0
    clock[0] = 1000
    resumed = training.train(output, resume=True)
    assert resumed["deadline_unix"] == 110
    assert resumed["status"] == "budget_exhausted"
    assert resumed["updates"] == 0
    assert len(calls) == 1


def test_resume_rejects_budget_extension_or_changed_suite(tmp_path, setup):
    config, _ = setup
    output = tmp_path / "train"
    training.train(output, config)
    with pytest.raises(ValueError, match="configuration differs"):
        training.train(output, {**config, "time_budget_seconds": 2000}, resume=True)
    Path(config["suite_path"]).write_text("{}")
    with pytest.raises(EvidenceError, match="Suite changed"):
        training.train(output, resume=True)


def test_corrupt_checkpoint_is_rejected_before_loading(tmp_path, setup):
    config, _ = setup
    output = tmp_path / "train"
    training.train(output, config)
    pointer = read(output / "training-state.json")
    path = output / pointer["path"]
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(EvidenceError, match="SHA-256"):
        training.train(output, resume=True)


def test_changed_source_stops_before_next_collection(tmp_path, setup, monkeypatch):
    config, calls = setup
    original_collect = training.run_episode

    def collect_then_change(*args, **kwargs):
        value = original_collect(*args, **kwargs)
        monkeypatch.setattr(training, "source_fingerprints", lambda: {"source": "different"})
        return value

    monkeypatch.setattr(training, "run_episode", collect_then_change)
    result = training.train(tmp_path / "train", config)
    assert result["status"] == "source_changed"
    assert len(calls) == 1
    assert result["updates"] == 0


def test_training_lock_rejects_second_owner(setup):
    with training._training_lock():
        with pytest.raises(RuntimeError, match="Another training process"):
            with training._training_lock():
                pytest.fail("Second owner acquired lock")


def test_behavior_tampering_cannot_enter_optimizer(tmp_path, setup, monkeypatch):
    config, _ = setup
    original_collect = training.run_episode

    def tamper(*args, **kwargs):
        value = original_collect(*args, **kwargs)
        path = args[0] / "trace.jsonl"
        trace = [json.loads(line) for line in path.read_text().splitlines()]
        trace[5]["behavior"]["model_sha256"] = "f" * 64
        path.write_text("".join(json.dumps(event) + "\n" for event in trace))
        return value

    monkeypatch.setattr(training, "run_episode", tamper)
    output = tmp_path / "train"
    with pytest.raises(EvidenceError, match="Behavior metadata"):
        training.train(output, config)
    state, _, _ = training._load_checkpoint(output)
    assert state["updates"] == 0
    assert state["consumed_ids"] == []


def test_deadline_interrupt_discards_partial_optimizer_work(tmp_path, setup, monkeypatch):
    config, calls = setup
    clock = [100.0]
    monkeypatch.setattr(training, "time", SimpleNamespace(time=lambda: clock[0]))
    original_update = PPOTrainer.update

    def expired_after_update(self, episodes):
        original_update(self, episodes)
        clock[0] = 2000.0
        raise training._TrainingDeadline("synthetic timer interrupt")

    monkeypatch.setattr(PPOTrainer, "update", expired_after_update)
    output = tmp_path / "train"
    result = training.train(output, config)
    assert result["status"] == "budget_exhausted"
    assert result["updates"] == result["consumed_transitions"] == 0
    assert result["model_sha256"] == result["initial_artifact"]["model_sha256"]
    assert result["pending_batch_steps"] == 2
    state, payload, _ = training._load_checkpoint(output)
    assert payload["learner"]["update_count"] == 0
    assert len(state["batch_runs"]) == 2
    resumed = training.train(output, resume=True)
    assert resumed["updates"] == 0
    assert len(calls) == 2


def test_real_alarm_interrupts_cpu_update_window():
    import signal
    import time

    previous = signal.getsignal(signal.SIGALRM)
    with pytest.raises(training._TrainingDeadline):
        with training._update_deadline(time.time() + 0.02):
            time.sleep(0.1)
    assert signal.getsignal(signal.SIGALRM) == previous
    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0


def test_orphan_artifact_preserves_original_checkpoint_ancestry(tmp_path, setup, monkeypatch):
    config, _ = setup
    original = training._ensure_artifact

    def crash_after_artifact(*args, **kwargs):
        original(*args, **kwargs)
        raise KeyboardInterrupt

    output = tmp_path / "train"
    monkeypatch.setattr(training, "_ensure_artifact", crash_after_artifact)
    with pytest.raises(KeyboardInterrupt):
        training.train(output, config)
    orphan = next((output / "artifacts").glob("*.pt"))
    original_payload = torch.load(orphan, weights_only=True)
    original_ancestry = original_payload["training_checkpoint_sha256"]
    original_bytes = orphan.read_bytes()
    monkeypatch.setattr(training, "_ensure_artifact", original)
    result = training.train(output, resume=True)
    initial_record = read(Path(result["initial_artifact_record"]))
    assert initial_record["training_checkpoint_sha256"] == original_ancestry
    assert orphan.read_bytes() == original_bytes
    assert result["updates"] == 1


def test_catalog_assignments_cycle_unique_scenarios_without_policy_metadata(
    tmp_path, catalog_setup
):
    config, calls = catalog_setup
    config.update(total_episodes=5, batch_steps=5)
    output = tmp_path / "catalog-training"
    result = training.train(output, config)
    state, _, _ = training._load_checkpoint(output)
    assert len(calls) == result["scenario_cursor"] == 5
    assert result["uses_evaluation_policy_seeds"] is False
    assert result["training_policy_rng"] == "externally_checkpointed"
    assert state["pending_scenario"] is None
    assert [item["scenario"]["scenario_id"] for item in state["attempts"]] == [
        "cultist-first",
        "cultist-second",
        "cultist-first",
        "cultist-second",
        "cultist-first",
    ]
    for index, attempt in enumerate(state["attempts"]):
        run = output / attempt["run"]
        manifest, environment = read(run / "manifest.json"), read(run / "environment.json")
        assert manifest["schema_version"] == 1
        assert manifest["scenario"] == environment["scenario"] == attempt["scenario"]
        assert manifest["scenario"]["cursor"] == index
        assert manifest["scenario"]["schedule_index"] == (0 if index % 2 == 0 else 2)
        assert manifest["config"]["game_seed"] == ("ABC" if index % 2 == 0 else "DEF")
        assert manifest["config"]["policy_seed"] == config["seed"]
        events = [
            json.loads(line) for line in (run / "episode-0000/trace.jsonl").read_text().splitlines()
        ]
        for event in events:
            if event["kind"] == "decision":
                public = json.dumps(event["decision"])
                assert "scenario_id" not in public and "game_seed" not in public
                assert "cultist-first" not in public and "cultist-second" not in public


def test_catalog_schedule_policy_seeds_do_not_reseed_training_sampler(
    tmp_path, setup, catalog_setup
):
    single_config, _ = setup
    catalog_config, _ = catalog_setup
    single = training.train(tmp_path / "single", single_config)
    catalog = training.train(tmp_path / "catalog", catalog_config)
    assert single["model_sha256"] == catalog["model_sha256"]
    single_state, _, _ = training._load_checkpoint(tmp_path / "single")
    assert "scenario_cursor" not in single_state
    assert "scenario_schedule" not in single


def test_catalog_reservation_survives_crash_before_attempt_files(
    tmp_path, catalog_setup, monkeypatch
):
    config, calls = catalog_setup
    config.update(total_episodes=4, batch_steps=4)
    original = training._initialize_attempt

    def interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(training, "_initialize_attempt", interrupt)
    output = tmp_path / "resumed"
    with pytest.raises(KeyboardInterrupt):
        training.train(output, config)
    before, _, _ = training._load_checkpoint(output)
    assert before["scenario_cursor"] == 1
    assert before["pending_scenario"] == {
        "cursor": 0,
        "scenario_id": "cultist-first",
        "schedule_index": 0,
    }
    assert not (output / "runs/attempt-0000").exists()
    monkeypatch.setattr(training, "_initialize_attempt", original)
    result = training.train(output, resume=True)
    after, _, _ = training._load_checkpoint(output)
    assert result["completed_episodes"] == len(calls) == 3
    assert result["scenario_cursor"] == 4
    assert result["deadline_unix"] == before["deadline_unix"]
    assert [attempt["scenario"]["scenario_id"] for attempt in after["attempts"]] == [
        "cultist-first",
        "cultist-second",
        "cultist-first",
        "cultist-second",
    ]
    assert after["attempts"][0]["status"] == "interrupted"


def test_catalog_completed_recovery_restores_sampler_and_assignment_exactly(
    tmp_path, catalog_setup, monkeypatch
):
    config, calls = catalog_setup
    reference = training.train(tmp_path / "reference", config)
    collect = training.run_episode
    crashed = False

    def interrupt(*args, **kwargs):
        nonlocal crashed
        result = collect(*args, **kwargs)
        if not crashed:
            crashed = True
            raise KeyboardInterrupt
        return result

    monkeypatch.setattr(training, "run_episode", interrupt)
    output = tmp_path / "resumed"
    with pytest.raises(KeyboardInterrupt):
        training.train(output, config)
    before, _, _ = training._load_checkpoint(output)
    result = training.train(output, resume=True)
    assert result["model_sha256"] == reference["model_sha256"]
    assert result["consumed_transitions"] == 2
    assert result["scenario_cursor"] == 2
    assert result["deadline_unix"] == before["deadline_unix"]
    assert len(calls) == 4


def test_catalog_recovery_rejects_changed_reserved_scenario(tmp_path, catalog_setup, monkeypatch):
    config, _ = catalog_setup
    collect = training.run_episode

    def interrupt(*args, **kwargs):
        collect(*args, **kwargs)
        raise KeyboardInterrupt

    monkeypatch.setattr(training, "run_episode", interrupt)
    output = tmp_path / "resumed"
    with pytest.raises(KeyboardInterrupt):
        training.train(output, config)
    path = output / "runs/attempt-0000/manifest.json"
    manifest = read(path)
    manifest["scenario"]["scenario_id"] = "cultist-second"
    write(path, manifest)
    with pytest.raises(EvidenceError, match="differs from checkpoint reservation"):
        training.train(output, resume=True)
    state, _, _ = training._load_checkpoint(output)
    assert state["consumed_ids"] == [] and state["updates"] == 0


def test_catalog_monster_declaration_is_checked_before_ingestion(tmp_path, catalog_setup):
    config, _ = catalog_setup
    path = Path(config["suite_path"])
    catalog = read(path)
    catalog["scenarios"][0].update(encounter_family="jaw_worm", monster_ids=["JawWorm"])
    write(path, catalog)
    output = tmp_path / "mismatched"
    with pytest.raises(EvidenceError, match="Observed monsters"):
        training.train(output, config)
    state, _, _ = training._load_checkpoint(output)
    assert state["consumed_ids"] == [] and state["updates"] == 0


def test_catalog_actual_start_pin_is_checked_before_ingestion(tmp_path, catalog_setup):
    config, _ = catalog_setup
    path = Path(config["suite_path"])
    catalog = read(path)
    catalog["scenarios"][0]["expected_start_sha256"] = "1234567890abcdef" * 4
    write(path, catalog)
    output = tmp_path / "wrong-start"
    with pytest.raises(EvidenceError, match="Actual combat start differs"):
        training.train(output, config)
    state, _, _ = training._load_checkpoint(output)
    assert state["consumed_ids"] == [] and state["updates"] == 0


def test_catalog_pending_batch_is_revalidated_before_optimizer(
    tmp_path, catalog_setup, monkeypatch
):
    config, calls = catalog_setup
    config["batch_steps"] = 1
    save = training._save_checkpoint
    crashed = False

    def interrupt_after_accept(output, state, trainer):
        nonlocal crashed
        pointer = save(output, state, trainer)
        if state["batch_runs"] and not crashed:
            crashed = True
            raise KeyboardInterrupt
        return pointer

    monkeypatch.setattr(training, "_save_checkpoint", interrupt_after_accept)
    output = tmp_path / "resumed"
    with pytest.raises(KeyboardInterrupt):
        training.train(output, config)
    path = output / "runs/attempt-0000/manifest.json"
    manifest = read(path)
    manifest["scenario"]["scenario_id"] = "cultist-second"
    write(path, manifest)
    with pytest.raises(EvidenceError, match="Completed attempt differs"):
        training.train(output, resume=True)
    state, _, _ = training._load_checkpoint(output)
    assert state["consumed_ids"] == [] and state["updates"] == 0
    assert len(calls) == 1
