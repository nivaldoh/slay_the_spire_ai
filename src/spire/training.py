"""Bounded original-engine PPO with atomic checkpoints and explicit recovery.

Every attempt is a separate auditable run. A crashed game is never restored or
silently reused; completed evidence can be recovered before launching a new game.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import random
import resource
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from spire.evaluation import load_suite
from spire.evidence import EvidenceError, audit_run, load_transitions
from spire.rollout import run_episode, source_fingerprints, write_json


class _TrainingDeadline(TimeoutError):
    """Interrupt an atomic CPU update so its pre-update checkpoint can be restored."""


@contextmanager
def _update_deadline(deadline: float):
    remaining = deadline - time.time()
    if remaining <= 0:
        raise _TrainingDeadline("Training deadline reached")
    if signal.getitimer(signal.ITIMER_REAL)[0]:
        raise RuntimeError("Training requires ownership of the process alarm timer")
    previous = signal.getsignal(signal.SIGALRM)

    def expired(signum, frame):
        raise _TrainingDeadline("Training deadline reached during optimizer update")

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, remaining)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_config(config: dict) -> dict:
    resolved = {
        "batch_steps": 128,
        "episode_timeout": 180,
        "bridge_timeout": 45,
        "max_actions": 500,
        "seed": 0,
        "torch_num_threads": 1,
        **config,
    }
    resolved["suite_path"] = str(Path(resolved["suite_path"]).resolve())
    for key in ("total_episodes", "batch_steps", "max_updates", "max_actions", "torch_num_threads"):
        if type(resolved.get(key)) is not int or resolved[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    for key in ("time_budget_seconds", "episode_timeout", "bridge_timeout"):
        value = resolved.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if type(resolved["seed"]) is not int:
        raise ValueError("seed must be an integer")
    return resolved


@contextmanager
def _training_lock():
    path = Path(f"/tmp/spire-training-{os.getuid()}.lock")
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another training process owns the local training lock") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _provenance() -> dict:
    from spire.doctor import collect_diagnostics

    paths = ["src", "scripts", "configs", "pyproject.toml", "uv.lock", ".python-version"]
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", *paths], text=True)
    if dirty:
        raise ValueError("Commit implementation changes before training: " + dirty)
    return {
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_status": dirty,
        "source_files": source_fingerprints(),
        "environment": collect_diagnostics(),
        "command": [sys.executable, *sys.argv],
    }


def _make_trainer(config: dict):
    import torch

    from spire.learning import CandidateActorCritic, NeuralPolicy, PPOTrainer

    torch.set_num_threads(config["torch_num_threads"])
    return PPOTrainer(
        NeuralPolicy(CandidateActorCritic(config["seed"]), seed=config["seed"]),
        seed=config["seed"],
    )


def _save_checkpoint(output: Path, state: dict, trainer) -> dict:
    import torch

    state["generation"] += 1
    payload = {
        "schema_version": 1,
        "training": copy.deepcopy(state),
        "learner": trainer.state_dict(),
        "python_rng": random.getstate(),
        "torch_rng": torch.get_rng_state(),
    }
    temporary = output / "checkpoints" / "checkpoint.tmp"
    with temporary.open("wb") as handle:
        torch.save(payload, handle)
        handle.flush()
        os.fsync(handle.fileno())
    digest = _digest(temporary)
    path = temporary.with_name(f"{state['generation']:06d}-{digest}.pt")
    os.replace(temporary, path)
    pointer = {
        "path": str(path.relative_to(output)),
        "sha256": digest,
        "generation": state["generation"],
        "phase": state["phase"],
        "deadline_unix": state["deadline_unix"],
    }
    write_json(output / "training-state.json", pointer)
    write_json(
        output / "metrics.json",
        {
            "attempts": state["next_attempt"],
            "completed_episodes": state["completed_episodes"],
            "updates": state["updates"],
            "consumed_transitions": len(state["consumed_ids"]),
            "phase": state["phase"],
            "stop_reason": state.get("stop_reason"),
            "history": state["update_history"],
        },
    )
    return pointer


def _load_checkpoint(output: Path) -> tuple[dict, dict, dict]:
    import torch

    pointer = json.loads((output / "training-state.json").read_text())
    path = (output / pointer["path"]).resolve()
    if not path.is_relative_to(output.resolve()) or _digest(path) != pointer["sha256"]:
        raise EvidenceError("Training checkpoint path or SHA-256 is invalid")
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if payload["schema_version"] != 1:
        raise ValueError("Unsupported training checkpoint schema")
    if payload["training"]["generation"] != pointer["generation"]:
        raise EvidenceError("Checkpoint generation differs from pointer")
    return payload["training"], payload, pointer


def _ensure_artifact(output: Path, state: dict, trainer, checkpoint: dict) -> bool:
    import torch

    from spire.learning import ENCODER_VERSION, LEARNER_VERSION, REWARD_VERSION

    model_hash = trainer.policy.model_sha256
    if state.get("artifact") and state["artifact"]["model_sha256"] == model_hash:
        record = state["artifact"]
        if _digest(output / record["path"]) != record["sha256"]:
            raise EvidenceError("Frozen policy artifact SHA-256 changed")
        return False
    path = output / "artifacts" / f"policy-{state['updates']:04d}-{model_hash}.pt"
    payload = {
        "schema_version": 1,
        "policy": trainer.policy.state_dict(),
        "model_sha256": model_hash,
        "training_checkpoint_sha256": checkpoint["sha256"],
        "learner_version": LEARNER_VERSION,
    }
    if path.exists():
        existing = torch.load(path, map_location="cpu", weights_only=True)
        actual = trainer.policy.model.state_dict()
        saved = existing["policy"]["model"]
        if (
            existing["model_sha256"] != model_hash
            or existing["schema_version"] != 1
            or existing["learner_version"] != LEARNER_VERSION
            or existing["policy"]["behavior_version"] != trainer.policy.behavior_version
            or existing["policy"]["encoder_version"] != ENCODER_VERSION
            or saved.keys() != actual.keys()
            or any(not torch.equal(saved[key], value) for key, value in actual.items())
        ):
            raise EvidenceError("Existing immutable artifact conflicts with current model")
        ancestry = existing["training_checkpoint_sha256"]
        ancestors = list((output / "checkpoints").glob(f"*-{ancestry}.pt"))
        if len(ancestors) != 1 or _digest(ancestors[0]) != ancestry:
            raise EvidenceError("Orphan artifact has no valid checkpoint ancestor")
    else:
        ancestry = checkpoint["sha256"]
        temporary = path.with_suffix(".tmp")
        with temporary.open("wb") as handle:
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    record = {
        "path": str(path.relative_to(output)),
        "sha256": _digest(path),
        "model_sha256": model_hash,
        "behavior_version": trainer.policy.behavior_version,
        "training_checkpoint_sha256": ancestry,
        "learner_version": LEARNER_VERSION,
        "encoder_version": ENCODER_VERSION,
        "reward_version": REWARD_VERSION,
        "source_revision": state["provenance"]["source_revision"],
        "suite_sha256": state["suite_sha256"],
        "updates": state["updates"],
        "consumed_transitions": len(state["consumed_ids"]),
        "data_runs": [run for update in state["update_history"] for run in update["runs"]],
    }
    write_json(path.with_suffix(".json"), record)
    record["record_path"] = str(path.with_suffix(".json").relative_to(output))
    state["artifact"] = record
    if state.get("initial_artifact") is None:
        state["initial_artifact"] = dict(record)
    return True


def _episode_config(state: dict, remaining: float) -> dict:
    config, suite = state["config"], state["suite"]
    return {
        "policy": "neural",
        "policy_seed": config["seed"],
        "episodes": 1,
        "game_seed": suite["game_seed"],
        "expected_start_sha256": suite["expected_start_sha256"],
        "max_actions": config["max_actions"],
        "episode_timeout": min(config["episode_timeout"], remaining),
        "bridge_timeout": min(config["bridge_timeout"], remaining),
    }


def _prepare_attempt(output: Path, state: dict) -> Path:
    index = state["next_attempt"]
    directory = output / "runs" / f"attempt-{index:04d}"
    state["next_attempt"] += 1
    state["pending_episode"] = str(directory.relative_to(output))
    state["phase"] = "collecting"
    return directory


def _initialize_attempt(directory: Path, state: dict, trainer, remaining: float) -> None:
    directory.mkdir()
    provenance = state["provenance"]
    manifest = {
        "schema_version": 1,
        "status": "running",
        "engine": "original",
        "scope": "first_combat",
        "observation_version": "ironclad-starter-combat-v1",
        "prefix_version": "neow-maxhp-or-gold-leftmost-settled-v2",
        "reset": "owned_jvm_restart_then_seeded_start",
        "episodes": [],
        "config": _episode_config(state, remaining),
        "behavior_model_sha256": trainer.policy.model_sha256,
        "behavior_version": trainer.policy.behavior_version,
        "training_batch": state["updates"],
        "training_attempt": state["next_attempt"] - 1,
        **{
            key: provenance[key]
            for key in (
                "source_revision",
                "source_status",
                "source_files",
                "command",
            )
        },
    }
    write_json(directory / "manifest.json", manifest)
    write_json(directory / "environment.json", provenance["environment"])
    (directory / "source.patch").write_text("")


def _close_attempt(directory: Path) -> dict | None:
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text())
    result_path = directory / "episode-0000" / "result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else None
    manifest["episodes"] = [result] if result is not None else []
    manifest["status"] = (
        "completed" if result and result["status"] in ("won", "lost") else "interrupted"
    )
    write_json(manifest_path, manifest)
    return result


def _join_episode(directory: Path, trainer) -> tuple[list, list[str], list[dict]]:
    from spire.learning import ENCODER_VERSION, Transition, decision_from_dict, terminal_reward

    audit = audit_run(directory)
    if not audit["valid"] or audit["metrics"]["valid_gameplay_episodes"] != 1:
        raise EvidenceError(f"Training requires one audited complete episode: {audit['issues']}")
    transitions = load_transitions(directory)
    if len(transitions) != audit["episodes"][0]["combat_actions"]:
        raise EvidenceError("Some selected combat actions have no ingestible transition")
    records = {}
    for line in (directory / "episode-0000" / "trace.jsonl").read_text().splitlines():
        event = json.loads(line)
        if event["kind"] == "decision":
            identity = event["selected_action_id"]
            if identity in records:
                raise EvidenceError("Duplicate behavior metadata")
            records[identity] = event["behavior"]
    episode, identities, replay = [], [], []
    for data in transitions:
        metadata = records[data["action_id"]]
        candidate_ids = tuple(candidate["id"] for candidate in data["candidates"])
        index = metadata.get("selected_index")
        if (
            type(index) is not int
            or not 0 <= index < len(candidate_ids)
            or metadata["decision_id"] != data["action"]["decision_id"]
            or metadata["selected_action_id"] != data["action_id"]
            or tuple(metadata["candidate_ids"]) != candidate_ids
            or candidate_ids[metadata["selected_index"]] != data["action_id"]
            or metadata["model_sha256"] != trainer.policy.model_sha256
            or metadata["behavior_version"] != trainer.policy.behavior_version
            or metadata["encoder_version"] != ENCODER_VERSION
            or metadata["observation_contract"] != data["observation"]["contract"]
            or metadata["deterministic"]
        ):
            raise EvidenceError("Behavior metadata does not match frozen audited candidates")
        decision = decision_from_dict(
            {
                "id": data["action"]["decision_id"],
                "observation": data["observation"],
                "candidates": data["candidates"],
            }
        )
        reward = 0.0
        if data["terminal"]:
            after = data["next_observation"]
            reward = terminal_reward(data["outcome"], after["current_hp"], after["max_hp"])
        episode.append(
            Transition(
                decision=decision,
                action_id=data["action_id"],
                old_logprob=metadata["old_logprob"],
                old_value=metadata["old_value"],
                reward=reward,
                terminated=data["terminal"],
                behavior_version=metadata["behavior_version"],
                candidate_ids=candidate_ids,
                model_sha256=metadata["model_sha256"],
            )
        )
        identities.append(data["transition_id"])
        replay.append({"decision": decision, "action_id": data["action_id"], "metadata": metadata})
    if not episode or not episode[-1].terminated or any(t.terminated for t in episode[:-1]):
        raise EvidenceError("Training episode is not complete")
    return episode, identities, replay


def _accept_attempt(output: Path, state: dict, trainer, *, recovering: bool) -> bool:
    relative = state["pending_episode"]
    directory = output / relative
    result = _close_attempt(directory)
    if result and result["status"] in ("won", "lost"):
        episode, ids, replay = _join_episode(directory, trainer)
        if set(ids) & set(state["consumed_ids"]):
            raise EvidenceError("Recovered episode was already consumed")
        if relative in state["batch_runs"]:
            raise EvidenceError("Recovered episode is already in the batch")
        if recovering:
            # The checkpoint predates collection. Replaying audited public
            # decisions restores the sampler exactly, without replaying the game.
            for item in replay:
                action = trainer.policy.choose(item["decision"])
                if action.id != item["action_id"] or (
                    trainer.policy.choice_metadata(item["decision"].id) != item["metadata"]
                ):
                    raise EvidenceError(
                        "Recovered sampling sequence differs from recorded behavior"
                    )
        state["batch_runs"].append(relative)
        state["batch_steps"] += len(episode)
        state["completed_episodes"] += 1
        state["attempts"].append({"run": relative, "status": result["status"]})
        accepted = True
    else:
        state["attempts"].append(
            {
                "run": relative,
                "status": result["status"] if result else "interrupted",
                "recovered_abandoned": recovering,
            }
        )
        accepted = False
    state["pending_episode"] = None
    state["phase"] = "ready"
    return accepted


def _summary(output: Path, state: dict, checkpoint: dict) -> dict:
    import torch

    artifact = state.get("artifact")
    initial = state.get("initial_artifact")
    result = {
        "status": (
            "completed"
            if state.get("stop_reason") in ("episode_limit", "update_limit")
            else state.get("stop_reason") or "running"
        ),
        "stop_reason": state.get("stop_reason"),
        "output": str(output.resolve()),
        "attempts": state["next_attempt"],
        "completed_episodes": state["completed_episodes"],
        "updates": state["updates"],
        "consumed_transitions": len(state["consumed_ids"]),
        "pending_batch_steps": state["batch_steps"],
        "deadline_unix": state["deadline_unix"],
        "checkpoint": checkpoint,
        "artifact_record": str(output / artifact["record_path"]) if artifact else None,
        "artifact_path": str(output / artifact["path"]) if artifact else None,
        "initial_artifact": initial,
        "initial_artifact_record": str(output / initial["record_path"]) if initial else None,
        "model_sha256": artifact["model_sha256"] if artifact else None,
        "attempt_records": state["attempts"],
        "update_history": state["update_history"],
        "config": state["config"],
        "suite_sha256": state["suite_sha256"],
        "source_revision": state["provenance"]["source_revision"],
        "resources": {
            "device": "cpu",
            "torch_version": torch.__version__,
            "torch_num_threads": torch.get_num_threads(),
            "elapsed_wall_seconds": max(0, time.time() - state["started_unix"]),
            "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "scope": "Training on a diagnostic development scenario; no held-out performance claim",
    }
    write_json(output / "training.json", result)
    return result


def train(output: Path, config: dict | None = None, resume: bool = False) -> dict:
    """Train within one absolute deadline; resume never replenishes any budget."""
    import torch

    output = Path(output).resolve()
    with _training_lock():
        if resume:
            state, payload, checkpoint = _load_checkpoint(output)
            config = state["config"] if config is None else _resolve_config(config)
            if config != state["config"]:
                raise ValueError("Resume configuration differs from checkpoint")
            if _digest(Path(config["suite_path"])) != state["suite_sha256"]:
                raise EvidenceError("Suite changed since training started")
            trainer = _make_trainer(config)
            trainer.load_state_dict(payload["learner"])
            random.setstate(payload["python_rng"])
            torch.set_rng_state(payload["torch_rng"])
        else:
            if config is None:
                raise ValueError("A new training run requires an explicit configuration")
            config = _resolve_config(config)
            started = time.time()
            suite = load_suite(Path(config["suite_path"]))
            provenance = _provenance()
            output.mkdir(parents=True, exist_ok=False)
            for name in ("checkpoints", "artifacts", "runs"):
                (output / name).mkdir()
            write_json(output / "suite.json", suite)
            random.seed(config["seed"])
            torch.manual_seed(config["seed"])
            trainer = _make_trainer(config)
            state = {
                "config": config,
                "suite": suite,
                "suite_sha256": _digest(Path(config["suite_path"])),
                "provenance": provenance,
                "started_unix": started,
                "deadline_unix": started + config["time_budget_seconds"],
                "generation": 0,
                "phase": "ready",
                "next_attempt": 0,
                "completed_episodes": 0,
                "updates": 0,
                "batch_runs": [],
                "batch_steps": 0,
                "consumed_ids": [],
                "pending_episode": None,
                "attempts": [],
                "update_history": [],
                "artifact": None,
                "initial_artifact": None,
            }
            checkpoint = _save_checkpoint(output, state, trainer)
        if source_fingerprints() != state["provenance"]["source_files"]:
            raise EvidenceError("Source files changed since the training checkpoint")
        if _ensure_artifact(output, state, trainer, checkpoint):
            checkpoint = _save_checkpoint(output, state, trainer)
        try:
            if state["pending_episode"] is not None:
                _accept_attempt(output, state, trainer, recovering=True)
                checkpoint = _save_checkpoint(output, state, trainer)
            # An interrupted update restores its before-update checkpoint and
            # the same unconsumed batch, optimizer state and RNG streams.
            state["phase"] = "ready"
            state["stop_reason"] = None
            while True:
                remaining = state["deadline_unix"] - time.time()
                if remaining <= 0:
                    state["stop_reason"] = "budget_exhausted"
                    break
                if state["updates"] >= config["max_updates"]:
                    state["stop_reason"] = "update_limit"
                    break
                if source_fingerprints() != state["provenance"]["source_files"]:
                    state["stop_reason"] = "source_changed"
                    break
                collect_done = state["next_attempt"] >= config["total_episodes"]
                if state["batch_runs"] and (
                    state["batch_steps"] >= config["batch_steps"] or collect_done
                ):
                    batch, batch_ids = [], []
                    for relative in state["batch_runs"]:
                        episode, ids, _ = _join_episode(output / relative, trainer)
                        batch.append(episode)
                        batch_ids.extend(ids)
                    if len(batch_ids) != len(set(batch_ids)) or set(batch_ids) & set(
                        state["consumed_ids"]
                    ):
                        raise EvidenceError("Batch would consume a transition more than once")
                    state["phase"] = "updating"
                    checkpoint = _save_checkpoint(output, state, trainer)
                    try:
                        with _update_deadline(state["deadline_unix"]):
                            metrics = trainer.update(batch)
                    except _TrainingDeadline:
                        state, payload, checkpoint = _load_checkpoint(output)
                        trainer.load_state_dict(payload["learner"])
                        random.setstate(payload["python_rng"])
                        torch.set_rng_state(payload["torch_rng"])
                        state["stop_reason"] = "budget_exhausted"
                        break
                    if not metrics["parameters_changed"]:
                        raise EvidenceError("Training update did not change model weights")
                    state["consumed_ids"].extend(batch_ids)
                    state["updates"] += 1
                    state["update_history"].append({**metrics, "runs": list(state["batch_runs"])})
                    state["batch_runs"], state["batch_steps"] = [], 0
                    state["phase"] = "ready"
                    checkpoint = _save_checkpoint(output, state, trainer)
                    _ensure_artifact(output, state, trainer, checkpoint)
                    checkpoint = _save_checkpoint(output, state, trainer)
                    _summary(output, state, checkpoint)
                    continue
                if collect_done:
                    state["stop_reason"] = "episode_limit"
                    break
                directory = _prepare_attempt(output, state)
                checkpoint = _save_checkpoint(output, state, trainer)
                remaining = state["deadline_unix"] - time.time()
                if remaining <= 0:
                    _accept_attempt(output, state, trainer, recovering=True)
                    state["stop_reason"] = "budget_exhausted"
                    break
                _initialize_attempt(directory, state, trainer, remaining)
                episode_config = json.loads((directory / "manifest.json").read_text())["config"]
                run_episode(directory / "episode-0000", episode_config, 0, policy=trainer.policy)
                accepted = _accept_attempt(output, state, trainer, recovering=False)
                checkpoint = _save_checkpoint(output, state, trainer)
                _summary(output, state, checkpoint)
                if not accepted:
                    state["stop_reason"] = (
                        "budget_exhausted"
                        if time.time() >= state["deadline_unix"]
                        else "episode_failure"
                    )
                    break
        except BaseException:
            # Preserve the last committed checkpoint. In particular, never save
            # partially updated weights or a sampler advanced by an uncommitted episode.
            committed, _, checkpoint = _load_checkpoint(output)
            committed["stop_reason"] = "interrupted"
            _summary(output, committed, checkpoint)
            raise
        state["phase"] = "stopped"
        checkpoint = _save_checkpoint(output, state, trainer)
        _ensure_artifact(output, state, trainer, checkpoint)
        return _summary(output, state, checkpoint)
