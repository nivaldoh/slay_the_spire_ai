"""Frozen artifact/RNG evaluation contracts; no real game processes are launched."""

import hashlib
import json
from contextlib import nullcontext
from unittest.mock import Mock

import pytest

torch = pytest.importorskip("torch")

from gameai import provenance  # noqa: E402
from spire.combat import evaluation, rollout  # noqa: E402
from spire.engine import doctor  # noqa: E402
from spire.engine.bridge import BridgeDisconnected  # noqa: E402
from spire.ppo.learning import (  # noqa: E402
    ENCODER_VERSION,
    LEARNER_VERSION,
    REWARD_VERSION,
    CandidateActorCritic,
    NeuralPolicy,
    decision_from_dict,
)
from spire.protocol import OBSERVATION_CONTRACT  # noqa: E402


@pytest.fixture(autouse=True)
def cpu_threads():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


@pytest.fixture
def state():
    return decision_from_dict(
        {
            "id": "evaluation:0",
            "observation": {
                "contract": OBSERVATION_CONTRACT,
                "combat_state": {
                    "player": {"current_hp": 80, "max_hp": 80, "energy": 3},
                    "monsters": [],
                    "hand": [{"id": "Defend_R", "cost": 1, "is_playable": True}],
                    "draw_pile": [],
                    "discard_pile": [],
                    "exhaust_pile": [],
                },
            },
            "candidates": [
                {
                    "id": "evaluation:0:play:0",
                    "decision_id": "evaluation:0",
                    "command": "play 1",
                    "kind": "play",
                    "hand_index": 0,
                    "card_id": "Defend_R",
                },
                {
                    "id": "evaluation:0:end",
                    "decision_id": "evaluation:0",
                    "command": "end",
                    "kind": "end",
                },
            ],
        }
    )


@pytest.fixture
def artifact(tmp_path, state):
    policy = NeuralPolicy(CandidateActorCritic(seed=13), seed=987)
    for _ in range(5):
        policy.choose(state)
    path = tmp_path / "training" / "artifacts" / "policy-0000-fixture.pt"
    path.parent.mkdir(parents=True)
    payload = {
        "schema_version": 1,
        "policy": policy.state_dict(),
        "model_sha256": policy.model_sha256,
        "training_checkpoint_sha256": "a" * 64,
        "learner_version": LEARNER_VERSION,
    }
    torch.save(payload, path)
    record = {
        "path": "artifacts/" + path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "model_sha256": policy.model_sha256,
        "training_checkpoint_sha256": "a" * 64,
        "behavior_version": policy.behavior_version,
        "learner_version": LEARNER_VERSION,
        "encoder_version": ENCODER_VERSION,
        "reward_version": REWARD_VERSION,
        "source_revision": "training-source",
        "suite_sha256": "b" * 64,
        "updates": 0,
        "consumed_transitions": 0,
    }
    path.with_suffix(".json").write_text(json.dumps(record))
    return path, payload, record


@pytest.fixture
def suite(tmp_path):
    path = tmp_path / "suite.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "frozen-test-suite",
                "purpose": "development",
                "game_seed": "TEST1",
                "expected_start_sha256": "c" * 64,
                "episodes": 3,
                "policy_seed": 1000,
            }
        )
    )
    return path


@pytest.fixture
def fake_runner(monkeypatch, state):
    captured = {"episodes": []}
    monkeypatch.setattr(doctor, "collect_diagnostics", lambda: {})
    monkeypatch.setattr(rollout, "source_fingerprints", lambda: {"source": "stable"})
    monkeypatch.setattr(
        provenance.subprocess,
        "check_output",
        lambda command, **kwargs: "evaluation-source" if "rev-parse" in command else "",
    )
    monkeypatch.setattr(evaluation, "summarize_run", lambda output: {"valid": True})

    def episode(directory, config, index, *, policy=None, policy_seed=None):
        assert policy is not None
        assert policy_seed == 1000 + index
        assert not policy.model.training
        assert all(not parameter.requires_grad for parameter in policy.model.parameters())
        snapshot = directory.parent / config["policy_artifact"]["snapshot_path"]
        assert snapshot.exists()  # Snapshot precedes the first possible game launch.
        draws = [policy.choose(state).id for _ in range(20)]
        captured["episodes"].append({"seed": policy_seed, "draws": draws, "policy": policy})
        result = {"episode": index, "status": "won", "policy_seed": policy_seed}
        if hook := captured.get("hook"):
            hook(index, policy)
        return result

    monkeypatch.setattr(rollout, "run_episode", episode)
    return captured


@pytest.mark.parametrize("use_record", [False, True])
def test_evaluation_freezes_artifact_and_resets_stochastic_rng_per_suite_episode(
    tmp_path,
    state,
    artifact,
    suite,
    fake_runner,
    use_record,
):
    path, payload, record = artifact
    output = tmp_path / "evaluation"
    result = evaluation.evaluate(
        "neural",
        suite,
        output,
        checkpoint=path.with_suffix(".json") if use_record else path,
    )
    assert result["valid"] and result["consistency_errors"] == []
    assert result["policy_artifact"]["sha256"] == record["sha256"]
    assert result["policy_artifact"]["model_sha256"] == payload["model_sha256"]
    assert result["policy_artifact"]["training_checkpoint_sha256"] == "a" * 64
    assert result["policy_artifact"]["source_revision"] == "training-source"
    assert result["policy_artifact"]["randomly_initialized"] is True
    assert result["evaluation_source_revision"] == "evaluation-source"
    assert (output / result["policy_artifact"]["snapshot_path"]).read_bytes() == path.read_bytes()
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["config"]["policy_artifact"]["sha256"] == record["sha256"]
    for index, capture in enumerate(fake_runner["episodes"]):
        independent = NeuralPolicy(CandidateActorCritic())
        independent.load_state_dict(payload["policy"])
        independent.deterministic = False
        independent.reset_sampling(1000 + index)
        assert capture["draws"] == [independent.choose(state).id for _ in range(20)]


def test_export_record_file_hash_mismatch_stops_before_rollout(
    tmp_path, artifact, suite, monkeypatch
):
    path, _, record = artifact
    record["sha256"] = "0" * 64
    path.with_suffix(".json").write_text(json.dumps(record))
    launch = Mock()
    monkeypatch.setattr(evaluation, "rollout", launch)
    with pytest.raises(ValueError, match="file SHA-256"):
        evaluation.evaluate("neural", suite, tmp_path / "evaluation", checkpoint=path)
    launch.assert_not_called()


def test_tensor_hash_mismatch_without_record_stops_before_rollout(
    tmp_path,
    artifact,
    suite,
    monkeypatch,
):
    path, payload, _ = artifact
    path.with_suffix(".json").unlink()
    first_tensor = next(iter(payload["policy"]["model"].values()))
    first_tensor.add_(1)
    torch.save(payload, path)
    launch = Mock()
    monkeypatch.setattr(evaluation, "rollout", launch)
    with pytest.raises(ValueError, match="tensor SHA-256"):
        evaluation.evaluate("neural", suite, tmp_path / "evaluation", checkpoint=path)
    launch.assert_not_called()


@pytest.mark.parametrize("target", ["weights", "file", "record", "suite", "snapshot"])
def test_mutations_after_last_episode_invalidate_evaluation_and_keep_original_identity(
    tmp_path,
    artifact,
    suite,
    fake_runner,
    target,
):
    path, payload, record = artifact
    output = tmp_path / "evaluation"
    original_bytes = path.read_bytes()

    def tamper(index, policy):
        if index != 2:
            return
        if target == "weights":
            with torch.no_grad():
                next(policy.model.parameters()).add_(1)
        elif target == "file":
            path.write_bytes(b"changed file")
        elif target == "record":
            path.with_suffix(".json").write_text("{}")
        elif target == "suite":
            suite.write_text("{}")
        else:
            (output / "frozen-artifact" / path.name).write_bytes(b"changed snapshot")

    fake_runner["hook"] = tamper
    result = evaluation.evaluate("neural", suite, output, checkpoint=path)
    assert not result["valid"] and result["consistency_errors"]
    assert result["policy_artifact"]["sha256"] == record["sha256"]
    assert result["policy_artifact"]["model_sha256"] == payload["model_sha256"]
    if target != "snapshot":
        assert (output / result["policy_artifact"]["snapshot_path"]).read_bytes() == original_bytes
    assert json.loads((output / "evaluation.json").read_text())["valid"] is False


def test_weight_mutation_between_episodes_prevents_next_launch(
    tmp_path, artifact, suite, fake_runner
):
    def tamper(index, policy):
        with torch.no_grad():
            next(policy.model.parameters()).add_(1)

    fake_runner["hook"] = tamper
    with pytest.raises(ValueError, match="before the next episode"):
        evaluation.evaluate("neural", suite, tmp_path / "evaluation", checkpoint=artifact[0])
    assert len(fake_runner["episodes"]) == 1
    manifest = json.loads((tmp_path / "evaluation/manifest.json").read_text())
    assert manifest["status"] == "interrupted"


def test_neural_rollout_requires_explicit_factory_before_creating_output(tmp_path):
    with pytest.raises(ValueError, match="policy factory"):
        rollout.rollout(tmp_path / "run", {"policy": "neural", "game_seed": "TEST1"})
    assert not (tmp_path / "run").exists()


def test_checkpoint_and_builtin_policy_cannot_be_mixed(tmp_path, artifact, suite):
    with pytest.raises(ValueError, match="builtin"):
        evaluation.evaluate("random", suite, tmp_path / "evaluation", checkpoint=artifact[0])


def test_standalone_envelope_does_not_invent_training_source(
    tmp_path, artifact, suite, fake_runner
):
    path, _, _ = artifact
    path.with_suffix(".json").unlink()
    result = evaluation.evaluate("neural", suite, tmp_path / "evaluation", checkpoint=path)
    assert result["valid"]
    assert result["policy_artifact"]["source_revision"] is None
    assert result["policy_artifact"]["record_path"] is None


def test_injected_episode_records_evaluation_seed_in_result_and_trace(tmp_path, monkeypatch):
    monkeypatch.setattr(rollout, "collect_profile", lambda *args: {})
    monkeypatch.setattr(rollout, "RuntimeLock", nullcontext)
    monkeypatch.setattr(rollout, "wsl_bridge_host", lambda: "172.18.34.183")
    monkeypatch.setattr(rollout, "BridgeServer", Mock(side_effect=BridgeDisconnected("test stop")))
    config = {
        "policy": "neural",
        "policy_seed": 1000,
        "game_seed": "TEST1",
        "episode_timeout": 10,
        "bridge_timeout": 2,
    }
    result = rollout.run_episode(
        tmp_path / "episode",
        config,
        2,
        policy=NeuralPolicy(CandidateActorCritic()),
        policy_seed=1002,
    )
    assert result["policy_seed"] == 1002
    assert result["policy_rng"] == "per_episode_seed"
    trace = [
        json.loads(line) for line in (tmp_path / "episode/trace.jsonl").read_text().splitlines()
    ]
    assert trace[-1]["result"] == result
