"""Frozen, narrowly scoped original-engine development suites."""

import hashlib
import io
import json
import re
from pathlib import Path

from gameai.provenance import write_json
from spire import policies
from spire.combat.evidence import summarize_run
from spire.combat.rollout import rollout
from spire.protocol import OBSERVATION_CONTRACT


def load_suite(path: Path) -> dict:
    suite = json.loads(path.read_text())
    if not isinstance(suite, dict):
        raise ValueError("Suite must be a JSON object")
    supported_declarations = {
        "character": "IRONCLAD",
        "class": "IRONCLAD",
        "ascension": 0,
        "ascension_level": 0,
        "observation_version": OBSERVATION_CONTRACT,
        "observation_contract": OBSERVATION_CONTRACT,
    }
    allowed = {
        "schema_version", "purpose", "id", "description", "game_seed", "policy_seed",
        "episodes", "expected_start_sha256", *supported_declarations,
    }
    if extra := suite.keys() - allowed:
        raise ValueError(f"Unsupported suite fields: {', '.join(sorted(extra))}")
    for key, expected in supported_declarations.items():
        if key in suite and (type(suite[key]) is not type(expected) or suite[key] != expected):
            raise ValueError(f"Unsupported suite {key}: expected {expected!r}")
    if suite.get("schema_version") != 1 or suite.get("purpose") != "development":
        raise ValueError("Only declared schema-1 development suites are implemented")
    if not isinstance(suite.get("id"), str) or not suite["id"]:
        raise ValueError("Suite requires a stable identifier")
    if not re.fullmatch(r"[A-Z0-9]+", suite.get("game_seed", "")):
        raise ValueError("Suite seed must use uppercase ASCII letters and numbers")
    if not re.fullmatch(r"[a-f0-9]{64}", suite.get("expected_start_sha256", "")):
        raise ValueError("Suite must pin the normalized combat start")
    if type(suite.get("episodes")) is not int or suite["episodes"] <= 0:
        raise ValueError("Suite episodes must be positive")
    if type(suite.get("policy_seed")) is not int:
        raise ValueError("Suite must fix the first policy RNG seed")
    return suite


def _neural_artifact(
    checkpoint: Path,
) -> tuple[object, dict, bytes, Path, Path | None, bytes | None]:
    """Load a weights-only envelope and validate its optional adjacent export record."""
    import torch

    from spire.ppo.learning import (
        ENCODER_VERSION,
        LEARNER_VERSION,
        REWARD_VERSION,
        CandidateActorCritic,
        NeuralPolicy,
    )

    checkpoint = checkpoint.resolve()
    if checkpoint.suffix == ".json":
        record_path, artifact_path = checkpoint, checkpoint.with_suffix(".pt")
    elif checkpoint.suffix == ".pt":
        artifact_path = checkpoint
        candidate = checkpoint.with_suffix(".json")
        record_path = candidate if candidate.exists() else None
    else:
        raise ValueError(
            "checkpoint must be a frozen policy .pt or its adjacent .json export record"
        )
    artifact_bytes = artifact_path.read_bytes()
    file_hash = hashlib.sha256(artifact_bytes).hexdigest()
    record_bytes = record_path.read_bytes() if record_path is not None else None
    record = json.loads(record_bytes) if record_bytes is not None else {}
    if record_path is not None and record.get("sha256") != file_hash:
        raise ValueError("frozen policy file SHA-256 differs from export record")
    envelope = torch.load(io.BytesIO(artifact_bytes), map_location="cpu", weights_only=True)
    if not isinstance(envelope, dict) or envelope.get("schema_version") != 1:
        raise ValueError("unsupported frozen policy artifact schema")
    if envelope.get("learner_version") != LEARNER_VERSION:
        raise ValueError("frozen policy learner version mismatch")
    for name in ("model_sha256", "training_checkpoint_sha256"):
        if not re.fullmatch(r"[a-f0-9]{64}", envelope.get(name, "")):
            raise ValueError(f"frozen policy requires a valid {name}")
    policy = NeuralPolicy(CandidateActorCritic())
    policy.load_state_dict(envelope["policy"])
    if policy.model_sha256 != envelope["model_sha256"]:
        raise ValueError("frozen policy tensor SHA-256 differs from envelope")
    if record_path is not None:
        for name, expected in {
            "model_sha256": policy.model_sha256,
            "training_checkpoint_sha256": envelope["training_checkpoint_sha256"],
            "behavior_version": policy.behavior_version,
            "learner_version": LEARNER_VERSION,
            "encoder_version": ENCODER_VERSION,
            "reward_version": REWARD_VERSION,
        }.items():
            if record.get(name) != expected:
                raise ValueError(f"frozen policy export record {name} mismatch")
        if type(record.get("updates")) is not int or record["updates"] < 0:
            raise ValueError("frozen policy export record requires a valid update count")
        if Path(record.get("path", "")).name != artifact_path.name:
            raise ValueError("frozen policy export record names a different artifact")
    policy.deterministic = False
    policy.model.eval()
    policy.model.requires_grad_(False)
    updates = record.get("updates")
    initialized = updates == 0 if updates is not None else policy.behavior_version == "initial"
    metadata = {
        "type": "neural",
        "name": "neural",
        "path": str(artifact_path),
        "sha256": file_hash,
        "model_sha256": policy.model_sha256,
        "training_checkpoint_sha256": envelope["training_checkpoint_sha256"],
        "source_revision": record.get("source_revision"),
        "training_suite_sha256": record.get("suite_sha256"),
        "behavior_version": policy.behavior_version,
        "learner_version": LEARNER_VERSION,
        "encoder_version": ENCODER_VERSION,
        "reward_version": REWARD_VERSION,
        "updates": updates,
        "consumed_transitions": record.get("consumed_transitions"),
        "randomly_initialized": initialized,
        "sampling": "stochastic_per_episode_seed",
        "record_path": str(record_path) if record_path is not None else None,
        "record_sha256": hashlib.sha256(record_bytes).hexdigest() if record_bytes else None,
        "snapshot_path": f"frozen-artifact/{artifact_path.name}",
    }
    return policy, metadata, artifact_bytes, artifact_path, record_path, record_bytes


def evaluate(
    policy: str,
    suite_path: Path,
    output: Path,
    *,
    checkpoint: Path | None = None,
) -> dict:
    suite = load_suite(suite_path)
    suite_bytes = suite_path.read_bytes()
    if json.loads(suite_bytes) != suite:
        raise ValueError("suite changed while preparing evaluation")
    if (policy == "neural") != (checkpoint is not None):
        raise ValueError("neural evaluation requires a checkpoint; builtin policies do not use one")
    frozen = None
    policy_factory = None
    artifact_path = record_path = None
    artifact_bytes = record_bytes = None
    policy_source = Path(policies.__file__)
    source_bytes = policy_source.read_bytes()
    if checkpoint is not None:
        frozen, artifact, artifact_bytes, artifact_path, record_path, record_bytes = (
            _neural_artifact(checkpoint)
        )

        def policy_factory(seed):
            if frozen.model_sha256 != artifact["model_sha256"]:
                raise ValueError("frozen policy weights changed before the next episode")
            if artifact_path.read_bytes() != artifact_bytes:
                raise ValueError("frozen policy file changed before the next episode")
            # Rollout has created its evidence directory, but no game has started.
            snapshot = output / artifact["snapshot_path"]
            if not snapshot.exists():
                snapshot.parent.mkdir(exist_ok=True)
                with snapshot.open("xb") as handle:
                    handle.write(artifact_bytes)
                if record_bytes is not None:
                    snapshot.with_suffix(".json").write_bytes(record_bytes)
            frozen.reset_sampling(seed)
            return frozen
    else:
        artifact = {
            "type": "builtin",
            "name": policy,
            "policy_source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "weights": None,
        }
    resolved = {
        "policy": policy,
        **{
            key: suite[key]
            for key in (
                "game_seed",
                "policy_seed",
                "episodes",
                "expected_start_sha256",
            )
        },
        "max_actions": 500,
        "episode_timeout": 180,
        "bridge_timeout": 45,
        "policy_artifact": artifact,
    }
    manifest = rollout(output, resolved, policy_factory=policy_factory)
    report = summarize_run(output)
    consistency_errors = []
    if suite_path.read_bytes() != suite_bytes:
        consistency_errors.append("suite file changed during evaluation")
    if frozen is not None:
        if frozen.model_sha256 != artifact["model_sha256"]:
            consistency_errors.append("frozen policy weights changed during evaluation")
        if not artifact_path.exists() or artifact_path.read_bytes() != artifact_bytes:
            consistency_errors.append("frozen policy artifact file changed during evaluation")
        if record_path is not None and (
            not record_path.exists() or record_path.read_bytes() != record_bytes
        ):
            consistency_errors.append("frozen policy export record changed during evaluation")
        snapshot = output / artifact["snapshot_path"]
        if not snapshot.exists() or snapshot.read_bytes() != artifact_bytes:
            consistency_errors.append("frozen policy evidence snapshot is missing or changed")
    else:
        artifact["source_revision"] = manifest["source_revision"]
        if policy_source.read_bytes() != source_bytes:
            consistency_errors.append("builtin policy source changed during evaluation")
    result = {
        "schema_version": 1,
        "suite": suite,
        "suite_sha256": hashlib.sha256(suite_bytes).hexdigest(),
        "policy_artifact": artifact,
        "evaluation_source_revision": manifest["source_revision"],
        "valid": report["valid"] and manifest["status"] == "completed" and not consistency_errors,
        "consistency_errors": consistency_errors,
        "audit": report,
    }
    write_json(output / "evaluation.json", result)
    return result
