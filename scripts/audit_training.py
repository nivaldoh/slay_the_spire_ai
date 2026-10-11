"""Audit saved PPO evidence without launching a game or modifying the run.

Usage: uv run --extra train python scripts/audit_training.py RUN [OUTPUT.json]
The optional report must be outside RUN. Exit 1 means invalid evidence. This
checks data flow and artifact integrity; it does not establish policy quality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
from pathlib import Path

import torch

from spire.evidence import audit_run, load_transitions
from spire.learning import CandidateActorCritic, NeuralPolicy, decision_from_dict, model_sha256


class AuditError(ValueError):
    """Saved evidence violates the training contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def run_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    require(path.is_relative_to(root), f"Evidence path leaves run: {relative}")
    return path


def same_tensors(left: dict, right: dict) -> bool:
    return left.keys() == right.keys() and all(
        torch.equal(left[key], value) for key, value in right.items()
    )


def load_policy(snapshot: dict) -> NeuralPolicy:
    policy = NeuralPolicy(CandidateActorCritic())
    policy.load_state_dict(snapshot)
    return policy


def finite_numbers(value) -> bool:
    if isinstance(value, dict):
        return all(finite_numbers(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return all(finite_numbers(item) for item in value)
    if torch.is_tensor(value):
        return bool(torch.isfinite(value).all())
    return not isinstance(value, (int, float)) or math.isfinite(value)


def parameter_changes(initial: dict, current: dict) -> dict:
    require(initial.keys() == current.keys(), "Initial/current tensor names differ")
    changes = {}
    for prefix in ("actor", "critic", "context", "cards", "monsters"):
        names = [key for key in initial if key.startswith(prefix + ".")]
        require(bool(names), f"Missing {prefix} tensors")
        delta = torch.cat(
            [(current[key].double() - initial[key].double()).reshape(-1) for key in names]
        )
        changes[prefix] = {
            "tensors": len(names),
            "changed_tensors": sum(not torch.equal(current[key], initial[key]) for key in names),
            "elements": delta.numel(),
            "changed_elements": int(torch.count_nonzero(delta)),
            "l2_delta": float(torch.linalg.vector_norm(delta)),
            "max_abs_delta": float(delta.abs().max()),
        }
    return changes


def catalog_assignment(catalog: dict, cursor: int) -> tuple[dict, dict]:
    from spire.catalog import resolve_child_suite

    scenario_id = catalog["scenarios"][cursor % len(catalog["scenarios"])]["id"]
    schedule_index = next(
        index
        for index, item in enumerate(catalog["schedule"])
        if item["scenario_id"] == scenario_id
    )
    context = {
        "catalog_id": catalog["id"],
        "cursor": cursor,
        "scenario_id": scenario_id,
        "schedule_index": schedule_index,
        "training_policy_rng": "externally_checkpointed",
        "uses_evaluation_policy_seeds": False,
    }
    return context, resolve_child_suite(catalog, schedule_index)


def audit_catalog_reservations(state: dict, expected_catalog: dict) -> None:
    require(state["suite"] == expected_catalog, "Checkpoint catalog changed")
    cursor, pending = state["scenario_cursor"], state["pending_scenario"]
    require(
        type(cursor) is int and cursor == state["next_attempt"] and cursor >= 0,
        "Catalog cursor differs from reserved attempts",
    )
    require(state["scenario_schedule"] == "round_robin_scenarios_v1", "Unknown scenario schedule")
    require(
        (pending is None) == (state["pending_episode"] is None), "Pending scenario/episode mismatch"
    )
    require(
        len(state["attempts"]) == cursor - int(pending is not None),
        "Catalog cursor omits attempt records",
    )
    for index, attempt in enumerate(state["attempts"]):
        expected, _ = catalog_assignment(expected_catalog, index)
        require(
            attempt["scenario"] == expected and attempt["run"] == f"runs/attempt-{index:04d}",
            "Attempt differs from round-robin scenario assignment",
        )
    if pending is not None:
        context, _ = catalog_assignment(expected_catalog, cursor - 1)
        require(
            pending == {key: context[key] for key in ("cursor", "scenario_id", "schedule_index")}
            and state["pending_episode"] == f"runs/attempt-{cursor - 1:04d}",
            "Pending scenario differs from round-robin reservation",
        )


def _audit(root: Path, report: dict) -> None:
    pointer = read_json(root / "training-state.json")
    checkpoint_path = run_path(root, pointer["path"])
    require(digest(checkpoint_path) == pointer["sha256"], "Current checkpoint digest mismatch")
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    state = payload["training"]
    require(payload["schema_version"] == 1, "Unsupported checkpoint schema")
    require(state["generation"] == pointer["generation"], "Checkpoint generation mismatch")
    require(state["phase"] == pointer["phase"], "Checkpoint phase mismatch")
    require(state["deadline_unix"] == pointer["deadline_unix"], "Pointer deadline mismatch")
    require(state["phase"] == "stopped", "Audit requires a stopped training checkpoint")
    require(
        read_json(root / "suite.json") == state["suite"], "Captured suite differs from checkpoint"
    )
    current = payload["learner"]["policy"]
    current_hash = model_sha256(load_policy(current).model)
    report.update(
        checkpoint=pointer,
        source_revision=state["provenance"]["source_revision"],
        updates=state["updates"],
        attempts=state["next_attempt"],
        completed_episodes=state["completed_episodes"],
        consumed_transitions=len(state["consumed_ids"]),
        model_sha256=current_hash,
    )

    # Verify actual checkpoint bytes, including every artifact's eventual ancestor.
    checkpoints = {}
    for path in sorted((root / "checkpoints").glob("*.pt")):
        actual = digest(path)
        saved = torch.load(path, map_location="cpu", weights_only=True)
        stage = saved["training"]
        require(
            path.name == f"{stage['generation']:06d}-{actual}.pt",
            f"Checkpoint filename/digest mismatch: {path.name}",
        )
        require(actual not in checkpoints, "Duplicate checkpoint digest")
        checkpoints[actual] = {"path": path, "payload": saved}
    require(pointer["sha256"] in checkpoints, "Current checkpoint absent from checkpoint history")
    require(bool(checkpoints), "No checkpoint history")
    earliest = min(checkpoints.values(), key=lambda item: item["payload"]["training"]["generation"])
    original = earliest["payload"]["training"]
    checks = report["checks"]
    catalog = state["suite"] if state["suite"]["schema_version"] == 2 else None
    if catalog is not None:
        from spire.catalog import validate_catalog

        validate_catalog(catalog)
        for item in checkpoints.values():
            audit_catalog_reservations(item["payload"]["training"], catalog)
        checks["catalog_reservations_match_checkpoints"] = True
    checks["deadline_retained"] = all(
        item["payload"]["training"]["deadline_unix"] == original["deadline_unix"]
        and item["payload"]["training"]["started_unix"] == original["started_unix"]
        and item["payload"]["training"]["config"] == state["config"]
        for item in checkpoints.values()
    )
    checks["original_budget_matches_deadline"] = math.isclose(
        original["deadline_unix"] - original["started_unix"],
        state["config"]["time_budget_seconds"],
        rel_tol=0,
        abs_tol=1e-6,
    )
    report.update(
        checkpoint_count=len(checkpoints),
        original_deadline_unix=original["deadline_unix"],
        original_started_unix=original["started_unix"],
    )
    checks["parameters_finite"] = finite_numbers(current["model"])
    checks["optimizer_state_finite"] = finite_numbers(payload["learner"]["optimizer"])
    for update in state["update_history"]:
        require(
            all(
                type(update.get(key)) in (int, float)
                for key in (
                    "loss",
                    "policy_loss",
                    "value_loss",
                    "entropy",
                    "approx_kl",
                    "gradient_norm",
                )
            ),
            "Missing numeric PPO metrics",
        )
        require(
            type(update.get("optimizer_steps")) is int and update["optimizer_steps"] > 0,
            "Missing positive optimizer step count",
        )
    checks["optimizer_metrics_finite"] = finite_numbers(state["update_history"])
    require(checks["parameters_finite"], "Nonfinite checkpoint parameters")
    require(checks["optimizer_metrics_finite"], "Nonfinite optimizer metrics")
    report["update_history"] = state["update_history"]
    checks["update_count_matches_history"] = (
        state["updates"] == len(state["update_history"]) == payload["learner"]["update_count"]
    )

    policies, artifacts = {}, {}
    for path in sorted((root / "artifacts").glob("*.pt")):
        envelope = torch.load(path, map_location="cpu", weights_only=True)
        record = read_json(path.with_suffix(".json"))
        require(envelope["schema_version"] == 1, "Unsupported artifact schema")
        require(run_path(root, record["path"]) == path, "Artifact record path mismatch")
        require(digest(path) == record["sha256"], f"Artifact digest mismatch: {path.name}")
        policy = load_policy(envelope["policy"])
        actual = model_sha256(policy.model)
        require(
            actual == envelope["model_sha256"] == record["model_sha256"],
            f"Artifact model digest mismatch: {path.name}",
        )
        require(finite_numbers(envelope["policy"]["model"]), "Nonfinite artifact parameters")
        ancestry = record["training_checkpoint_sha256"]
        require(ancestry == envelope["training_checkpoint_sha256"], "Artifact ancestry mismatch")
        require(ancestry in checkpoints, f"Missing ancestor checkpoint: {ancestry}")
        ancestor = checkpoints[ancestry]["payload"]
        require(
            same_tensors(envelope["policy"]["model"], ancestor["learner"]["policy"]["model"]),
            "Artifact tensors differ from ancestor checkpoint",
        )
        require(record["updates"] == ancestor["training"]["updates"], "Artifact update mismatch")
        require(
            record["consumed_transitions"] == len(ancestor["training"]["consumed_ids"]),
            "Artifact consumed counter mismatch",
        )
        require(
            record["data_runs"]
            == [run for update in ancestor["training"]["update_history"] for run in update["runs"]],
            "Artifact data ancestry mismatch",
        )
        for key in ("source_revision", "suite_sha256"):
            expected = state["provenance"][key] if key == "source_revision" else state[key]
            require(record[key] == expected, f"Artifact {key} mismatch")
        require(
            record["learner_version"]
            == envelope["learner_version"]
            == ancestor["learner"]["learner_version"],
            "Artifact learner version mismatch",
        )
        require(
            record["reward_version"] == ancestor["learner"]["reward_version"],
            "Artifact reward version mismatch",
        )
        for key in ("behavior_version", "encoder_version"):
            require(record[key] == envelope["policy"][key], f"Artifact {key} mismatch")
        policies[actual] = policy
        artifacts[record["path"]] = {**record, "ancestor_file": checkpoints[ancestry]["path"].name}
    for name in ("initial_artifact", "artifact"):
        referenced = state[name]
        require(
            referenced is not None and referenced["path"] in artifacts, f"Missing referenced {name}"
        )
        record = artifacts[referenced["path"]]
        require(
            all(
                record.get(key) == value
                for key, value in referenced.items()
                if key != "record_path"
            ),
            f"Checkpoint {name} differs from artifact record",
        )
        require(
            run_path(root, referenced["record_path"])
            == run_path(root, referenced["path"]).with_suffix(".json"),
            f"Checkpoint {name} record path mismatch",
        )
    final = artifacts[state["artifact"]["path"]]
    checks["final_export_matches_checkpoint"] = final[
        "model_sha256"
    ] == current_hash and same_tensors(
        policies[final["model_sha256"]].model.state_dict(), current["model"]
    )
    initial = policies[state["initial_artifact"]["model_sha256"]].model.state_dict()
    changes = parameter_changes(initial, current["model"])
    report["parameter_changes"] = changes
    checks["actor_changed_after_updates"] = (
        not state["updates"] or changes["actor"]["changed_elements"] > 0
    )
    report["artifacts"] = list(artifacts.values())
    checks["artifact_integrity"] = True

    consumed = state["consumed_ids"]
    consumed_runs = [run for update in state["update_history"] for run in update["runs"]]
    checks["consumed_runs_unique"] = len(consumed_runs) == len(set(consumed_runs))
    checks["consumed_ids_unique"] = len(consumed) == len(set(consumed))
    attempt_runs = [attempt["run"] for attempt in state["attempts"]]
    checks["attempt_runs_unique"] = len(attempt_runs) == len(set(attempt_runs))
    checks["attempt_count_matches_records"] = state["next_attempt"] == len(attempt_runs)
    checks["no_pending_episode"] = state["pending_episode"] is None
    checks["consumed_runs_linked"] = set(consumed_runs) <= set(attempt_runs)
    transitions_by_run, behavior_by_run, completed_ids, excluded_actions = {}, {}, [], []
    audits, logprob_errors, value_errors = [], [], []
    for attempt_index, attempt in enumerate(state["attempts"]):
        run = run_path(root, attempt["run"])
        scenario_suite = state["suite"]
        if catalog is not None:
            context, scenario_suite = catalog_assignment(catalog, attempt_index)
            manifest_path, environment_path = run / "manifest.json", run / "environment.json"
            if manifest_path.exists():
                require(
                    read_json(manifest_path).get("scenario") == context,
                    "Episode scenario differs from reserved catalog assignment",
                )
            if environment_path.exists() or attempt["status"] in ("won", "lost"):
                require(
                    read_json(environment_path).get("scenario") == context,
                    "Environment scenario differs from reserved catalog assignment",
                )
        audited = audit_run(run)
        audits.append(
            {
                "run": attempt["run"],
                "recorded_status": attempt["status"],
                "valid": audited["valid"],
                "issues": audited["issues"],
                "metrics": audited["metrics"],
            }
        )
        trace = run / "episode-0000" / "trace.jsonl"
        events = (
            [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
        )
        decisions = [event for event in events if event["kind"] == "decision"]
        if attempt["status"] not in ("won", "lost"):
            # Interrupted physical evidence can be incomplete, but never contributes data.
            excluded_actions.extend(event["selected_action_id"] for event in decisions)
            require(attempt["run"] not in consumed_runs, "Incomplete attempt consumed by optimizer")
            continue
        require(
            audited["valid"], f"Invalid completed episode: {attempt['run']}: {audited['issues']}"
        )
        manifest = read_json(run / "manifest.json")
        for key in ("source_revision", "source_files", "source_status", "command"):
            require(
                manifest[key] == state["provenance"][key], f"Episode {key} differs from training"
            )
        expected_config = {
            "policy": "neural",
            "policy_seed": state["config"]["seed"],
            "episodes": 1,
            "game_seed": scenario_suite["game_seed"],
            "expected_start_sha256": scenario_suite["expected_start_sha256"],
            "max_actions": state["config"]["max_actions"],
        }
        require(
            all(manifest["config"][key] == value for key, value in expected_config.items()),
            "Episode scenario config differs from training",
        )
        result = read_json(run / "episode-0000" / "result.json")
        require(result["status"] == attempt["status"], "Attempt/result outcome mismatch")
        transitions = load_transitions(run)
        if catalog is not None:
            require(
                audited["episodes"][0]["combat_start_sha256"]
                == scenario_suite["expected_start_sha256"],
                "Actual combat start differs from assigned scenario",
            )
            declared = next(
                item for item in catalog["scenarios"] if item["id"] == context["scenario_id"]
            )
            require(
                [
                    monster["id"]
                    for monster in transitions[0]["observation"]["combat_state"]["monsters"]
                ]
                == declared["monster_ids"],
                "Observed monsters differ from assigned scenario",
            )
        ids = [transition["transition_id"] for transition in transitions]
        transitions_by_run[attempt["run"]] = ids
        completed_ids.extend(ids)
        behavior_by_run[attempt["run"]] = {event["behavior"]["model_sha256"] for event in decisions}
        require(
            behavior_by_run[attempt["run"]] == {manifest["behavior_model_sha256"]},
            "Episode manifest behavior model mismatch",
        )
        for event in decisions:
            behavior = event["behavior"]
            require(
                finite_numbers([behavior["old_logprob"], behavior["old_value"]]),
                "Nonfinite recorded behavior probability or value",
            )
            policy = policies[behavior["model_sha256"]]
            decision = decision_from_dict(event["decision"])
            require(behavior["decision_id"] == decision.id, "Behavior decision ID mismatch")
            require(
                behavior["candidate_ids"] == [action.id for action in decision.candidates],
                "Behavior candidate IDs differ from audited decision",
            )
            require(
                type(behavior["selected_index"]) is int
                and 0 <= behavior["selected_index"] < len(decision.candidates),
                "Behavior selected index outside candidate list",
            )
            require(
                behavior["selected_action_id"]
                == event["selected_action_id"]
                == decision.candidates[behavior["selected_index"]].id,
                "Behavior action mismatch",
            )
            for key, expected in (
                ("behavior_version", policy.behavior_version),
                ("encoder_version", policy.state_dict()["encoder_version"]),
                ("observation_contract", decision.observation["contract"]),
                ("deterministic", False),
            ):
                require(behavior[key] == expected, f"Behavior {key} mismatch")
            with torch.no_grad():
                logits, value = policy.model(decision)
                logprob = torch.log_softmax(logits, dim=0)[behavior["selected_index"]]
            logprob_errors.append(abs(float(logprob) - behavior["old_logprob"]))
            value_errors.append(abs(float(value) - behavior["old_value"]))
    expected_ids = [
        identity for run in consumed_runs for identity in transitions_by_run.get(run, [])
    ]
    checks["consumption_matches_audited_episodes"] = expected_ids == consumed
    previous_hash = state["initial_artifact"]["model_sha256"]
    for index, update in enumerate(state["update_history"], 1):
        require(update["update"] == index, "Update history numbering mismatch")
        require(update["before_sha256"] == previous_hash, "Update model ancestry mismatch")
        require(update["after_sha256"] in policies, "Missing updated model artifact")
        require(
            update["parameters_changed"] and update["after_sha256"] != previous_hash,
            "Update did not change model parameters",
        )
        require(update["episodes"] == len(update["runs"]), "Update episode counter mismatch")
        require(
            update["transitions"] == sum(len(transitions_by_run[run]) for run in update["runs"]),
            "Update transition counter mismatch",
        )
        require(
            all(behavior_by_run[run] == {previous_hash} for run in update["runs"]),
            "Optimizer batch mixes behavior models",
        )
        previous_hash = update["after_sha256"]
    checks["update_model_chain_matches_checkpoint"] = previous_hash == current_hash
    pending = state["batch_runs"]
    checks["pending_runs_unique"] = len(pending) == len(set(pending))
    checks["pending_disjoint_from_consumed"] = not set(pending) & set(consumed_runs)
    checks["all_completed_runs_accounted_for"] = set(pending) | set(consumed_runs) == set(
        transitions_by_run
    )
    checks["pending_steps_match_evidence"] = state["batch_steps"] == sum(
        len(transitions_by_run.get(run, [])) for run in pending
    )
    checks["pending_behavior_matches_current_model"] = all(
        behavior_by_run.get(run) == {current_hash} for run in pending
    )
    checks["completed_transition_ids_unique"] = len(completed_ids) == len(set(completed_ids))
    checks["completed_count_matches_evidence"] = state["completed_episodes"] == len(
        transitions_by_run
    )
    checks["interrupted_attempt_excluded"] = not any(
        identity.endswith("/" + action) for identity in consumed for action in excluded_actions
    )
    checks["behavior_probabilities_match"] = all(error <= 1e-6 for error in logprob_errors)
    checks["behavior_values_match"] = all(error <= 1e-6 for error in value_errors)
    report.update(
        attempt_audits=audits,
        completed_episode_transitions=len(completed_ids),
        unconsumed_completed_transitions=len(set(completed_ids) - set(consumed)),
        excluded_decisions=len(excluded_actions),
        max_recorded_logprob_error=max(logprob_errors, default=0),
        max_recorded_value_error=max(value_errors, default=0),
    )
    summary = read_json(root / "training.json")
    checks["summary_matches_checkpoint"] = (
        all(
            summary[key] == report[key]
            for key in (
                "updates",
                "attempts",
                "completed_episodes",
                "consumed_transitions",
                "model_sha256",
            )
        )
        and summary["checkpoint"] == pointer
    )
    stop_reason = state["stop_reason"]
    require(
        stop_reason
        in {
            "episode_limit",
            "update_limit",
            "budget_exhausted",
            "source_changed",
            "episode_failure",
        },
        "Unknown committed stop reason",
    )
    expected_status = (
        "completed" if stop_reason in {"episode_limit", "update_limit"} else stop_reason
    )
    checks["summary_status_and_budget_match"] = (
        summary["status"] == expected_status
        and summary["stop_reason"] == stop_reason
        and summary["deadline_unix"] == state["deadline_unix"]
        and summary["pending_batch_steps"] == state["batch_steps"]
        and summary["update_history"] == state["update_history"]
    )
    if catalog is not None:
        checks["summary_catalog_matches_checkpoint"] = (
            summary["catalog_id"] == catalog["id"]
            and summary["scenario_cursor"] == state["scenario_cursor"]
            and summary["scenario_schedule"] == state["scenario_schedule"]
            and summary["training_policy_rng"] == "externally_checkpointed"
            and summary["uses_evaluation_policy_seeds"] is False
        )
    report["status"] = expected_status
    probe = root / "interruption-probe.json"
    if probe.exists():
        saved = read_json(probe)
        first_trace = root / "runs/attempt-0000/episode-0000/trace.jsonl"
        checks["probe_completed_trace_unchanged"] = (
            digest(first_trace) == saved["completed_trace_sha256"]
        )
        checks["probe_deadline_retained"] = (
            saved["checkpoint_before"]["deadline_unix"] == original["deadline_unix"]
        )
    checks["pointer_still_current"] = read_json(root / "training-state.json") == pointer


def audit_training(run: Path) -> dict:
    """Return a JSON-safe report; malformed or incomplete evidence is invalid."""
    root = Path(run).resolve()
    report = {"schema_version": 1, "run": str(root), "valid": False, "checks": {}, "errors": []}
    torch.set_num_threads(1)
    try:
        _audit(root, report)
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        RuntimeError,
        EOFError,
        pickle.UnpicklingError,
    ) as error:
        report["errors"].append(f"{type(error).__name__}: {error}")
    report["errors"].extend(
        f"Failed check: {key}" for key, valid in report["checks"].items() if not valid
    )
    report["valid"] = not report["errors"]
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args(argv)
    if args.output and args.output.resolve().is_relative_to(args.run.resolve()):
        parser.error("Report output must be outside the audited run")
    report = audit_training(args.run)
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
