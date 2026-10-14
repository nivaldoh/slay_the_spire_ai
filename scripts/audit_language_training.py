"""Read-only CPU audit of saved SFT evidence; no model loading or gameplay-quality claim.

Usage: python scripts/audit_language_training.py RUN [OUTPUT.json]
The optional report must be outside RUN. Audit stopped jobs; do not audit a live writer.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import random
import subprocess
from pathlib import Path

import torch

from gameai.provenance import REPO_ROOT, SOURCE_PATHS
from spire.language import training
from spire.language.policy import file_inventory, validate_declaration


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def json_hash(value):
    return hashlib.sha256(training._json(value)).hexdigest()


def finite(value):
    if isinstance(value, torch.Tensor):
        return bool(torch.isfinite(value).all())
    if isinstance(value, dict):
        return all(finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(finite(item) for item in value)
    return not isinstance(value, (int, float)) or math.isfinite(value)


def within(root, value):
    path = (root / value).resolve()
    require(path.is_relative_to(root), f"Evidence path leaves run: {value}")
    return path


def archived_source(revision):
    """Hashes of the committed files in the scope that training fingerprints."""
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", revision, "--", *SOURCE_PATHS],
        cwd=REPO_ROOT, text=True,
    ).splitlines()
    return {
        name: hashlib.sha256(
            subprocess.check_output(["git", "show", f"{revision}:{name}"], cwd=REPO_ROOT)
        ).hexdigest()
        for name in names
    }


def _optimizer(payload):
    state, optimizer = payload["state"], payload["optimizer"]
    require(finite(optimizer), "Nonfinite optimizer state")
    groups = optimizer["param_groups"]
    ids = [identity for group in groups for identity in group["params"]]
    require(len(ids) == len(set(ids)) == len(payload["adapter"]), "Optimizer parameter IDs differ")
    require(
        set(optimizer["state"]) == (set(ids) if state["updates"] else set()),
        "Optimizer moments missing or unexpected",
    )
    # This pinned trainer uses one group from trainable model.parameters(); PEFT's
    # LoRA state dictionary preserves that same module/parameter traversal order.
    parameters = dict(zip(ids, payload["adapter"].values(), strict=True))
    for identity, moments in optimizer["state"].items():
        parameter = parameters[identity]
        require(
            set(moments) == {"step", "exp_avg", "exp_avg_sq"}
            and float(moments["step"]) == state["updates"]
            and moments["exp_avg"].shape == moments["exp_avg_sq"].shape == parameter.shape
            and moments["exp_avg"].dtype == moments["exp_avg_sq"].dtype == parameter.dtype,
            "Optimizer update counter or moments differ",
        )


def _checkpoints(root, job, payload, pointer, checks):
    state = payload["state"]
    found, initial, history_states, reservations, generations = {}, None, set(), set(), set()
    job_hash = digest(root / "job.json")
    for path in sorted((root / "checkpoints").glob("*.pt")):
        identity = digest(path)
        saved = torch.load(path, map_location="cpu", weights_only=True)
        stage = saved["state"]
        require(
            path.name == f"{stage['generation']:06d}-{identity}.pt",
            "Checkpoint filename/content mismatch",
        )
        require(
            saved["schema_version"] == 1
            and saved["version"] == training.VERSION
            and stage["job_sha256"] == job_hash
            and stage["deadline_unix"] == job["deadline_unix"],
            "Checkpoint source/job/deadline lineage differs",
        )
        require(
            finite(saved["adapter"])
            and training.tensor_hash(saved["adapter"]) == stage["adapter_sha256"],
            "Checkpoint adapter is nonfinite or changed",
        )
        _optimizer(saved)
        require(
            stage["initial_adapter_sha256"] == state["initial_adapter_sha256"],
            "Checkpoint initial adapter lineage differs",
        )
        found[identity] = path
        if stage["generation"] <= state["generation"]:
            generations.add(stage["generation"])
        if stage["generation"] == 1:
            require(
                initial is None
                and stage["updates"] == 0
                and stage["charged_tokens"] == 0
                and not stage["consumed"],
                "Initial checkpoint is not a unique unused adapter",
            )
            initial = saved["adapter"]
        count = stage["updates"]
        if count <= state["updates"] and stage["history"] == state["history"][:count]:
            expected = (
                state["history"][count - 1]["after_sha256"]
                if count
                else (state["initial_adapter_sha256"])
            )
            if stage["adapter_sha256"] == expected:
                history_states.add(count)
        # A durable reserved checkpoint must precede each recorded committed/abandoned attempt.
        if stage["pending"] is not None:
            index = stage["pending"]
            if index < len(state["reservations"]):
                actual = stage["reservations"][index]
                expected = state["reservations"][index]
                if actual["status"] == "reserved" and all(
                    actual[key] == expected[key] for key in ("tokens", "occurrences")
                ):
                    reservations.add(index)
    require(
        pointer["sha256"] in found and initial is not None, "Missing initial/current checkpoint"
    )
    require(
        generations == set(range(1, state["generation"] + 1)),
        "Checkpoint generation history has a gap",
    )
    require(
        history_states == set(range(state["updates"] + 1)),
        "A committed update lacks matching checkpoint tensor ancestry",
    )
    require(
        reservations == set(range(len(state["reservations"]))),
        "A token reservation lacks durable pre-update evidence",
    )
    require(initial.keys() == payload["adapter"].keys(), "Initial/final adapter keys differ")
    changed = 0
    for name, tensor in payload["adapter"].items():
        require(
            tensor.shape == initial[name].shape and tensor.dtype == initial[name].dtype,
            "Initial/final adapter tensor layout differs",
        )
        changed += int((tensor != initial[name]).sum())
    require(bool(changed) == bool(state["updates"]), "Declared updates lack actual adapter changes")
    checks.update(
        checkpoint_ancestry=True,
        reserved_before_updates=True,
        finite_adapter_and_optimizer=True,
        initial_to_final_changes_verified=True,
    )
    return found, changed


def _exports(root, job, checkpoints, summary, checks):
    from safetensors.torch import load_file

    exports = []
    for directory in sorted((root / "artifacts").glob("update-*")):
        record = read(directory / "export.json")
        identity = record["checkpoint_sha256"]
        require(identity in checkpoints, "Export checkpoint ancestor is absent")
        payload = torch.load(checkpoints[identity], map_location="cpu", weights_only=True)
        state = payload["state"]
        require(
            directory.name == f"update-{state['updates']:06d}-{identity}"
            and record["adapter_sha256"] == state["adapter_sha256"],
            "Export identity differs from checkpoint",
        )
        require(
            set(record["files"])
            == {"adapter/adapter_config.json", "adapter/adapter_model.safetensors", "policy.json"},
            "Export inventory differs",
        )
        for name, expected in record["files"].items():
            require(digest(within(root, str(directory / name))) == expected, "Export file changed")
        adapter = directory / "adapter"
        require(
            training.tensor_hash(load_file(adapter / "adapter_model.safetensors"))
            == state["adapter_sha256"],
            "Export tensor contents differ from checkpoint",
        )
        require(
            read(adapter / "adapter_config.json")
            == {**payload["adapter_config"], "inference_mode": True},
            "Export LoRA config differs",
        )
        expected = copy.deepcopy(job["base"])
        expected["adapter"] = {"directory": str(adapter), "files": file_inventory(adapter)}
        expected["provenance"] = {
            "trainer_version": training.VERSION,
            "training_checkpoint_sha256": identity,
            "training_job_sha256": state["job_sha256"],
            "source_revision": job["source"]["revision"],
            "source_files_sha256": json_hash(job["source"]["files"]),
            "dataset_manifest_sha256": job["dataset"]["manifest_sha256"],
            "updates": state["updates"],
            "adapter_sha256": state["adapter_sha256"],
            "consumed_example_ids_sha256": json_hash(state["consumed"]),
            "scope": "Public heuristic imitation; no gameplay performance claim",
        }
        require(
            read(directory / "policy.json") == expected
            and record["declaration"] == str(directory / "policy.json"),
            "Export declaration/base/data/source lineage differs",
        )
        exports.append({"directory": str(directory), **record})
    if "artifact" in summary:
        require(summary["artifact"] in exports, "Summary export record differs or is absent")
        require(
            summary["artifact"]["checkpoint_sha256"] == summary["checkpoint"]["sha256"],
            "Summary export is not the current checkpoint",
        )
    checks["published_exports_match_checkpoint_and_job"] = True
    return exports


def _supervision(root, job, checks):
    invocations = []
    for path in sorted(root.glob("watchdog-*.json")):
        value = read(path)
        require(value["schema_version"] == 1 and finite(value), "Invalid supervisor metrics")
        start, deadline = value["started_unix"], value["deadline_unix"]
        require(
            deadline == job["deadline_unix"] and start >= job["started_unix"],
            "Supervisor changed original launch/deadline",
        )
        require(
            type(value["finalize_only"]) is bool
            and type(value["polls"]) is int
            and value["polls"] >= 0
            and value["elapsed_seconds"] >= 0,
            "Invalid supervisor invocation fields",
        )
        expected = start + 30 if value["finalize_only"] else deadline
        require(
            value["supervision_deadline_unix"] == expected,
            "Supervisor extended collection/finalization budget",
        )
        require(value["finalize_only"] or start < deadline, "Collection began after deadline")
        if value["finalize_only"]:
            require(value["maximum_gpu_used_mib"] is None, "CPU finalization queried GPU")
        else:
            require(
                type(value["maximum_gpu_used_mib"]) in (int, float)
                and value["maximum_gpu_used_mib"] >= 0,
                "Missing supervisor GPU measurement",
            )
        require(
            abs(
                value["cleanup_overrun_seconds"]
                - max(0, start + value["elapsed_seconds"] - deadline)
            )
            < 0.05,
            "Supervisor cleanup overrun is inconsistent",
        )
        require(
            start + value["elapsed_seconds"] <= expected + 13,
            "Supervisor exceeded bounded cleanup allowance",
        )
        low_ram = value["minimum_available_mib"] < job["config"]["min_available_mib"]
        high_gpu = value["maximum_gpu_used_mib"] is not None and (
            value["maximum_gpu_used_mib"] >= job["config"]["max_gpu_gib"] * 1024
        )
        require(not low_ram or value["stop_reason"] == "low_ram", "RAM guard breach was ignored")
        require(
            not high_gpu or value["stop_reason"] in {"gpu_memory", "low_ram"},
            "GPU guard breach was ignored",
        )
        require(value["stop_reason"] != "job_deadline_changed", "Supervisor detected modified job")
        invocations.append({"file": path.name, "sha256": digest(path), **value})
    require(bool(invocations), "Missing supervised invocation evidence")
    require(
        min(item["started_unix"] for item in invocations) == job["started_unix"],
        "Initial supervisor invocation is absent",
    )
    ordered = sorted(invocations, key=lambda item: item["started_unix"])
    require(
        all(
            left["started_unix"] + left["elapsed_seconds"] <= right["started_unix"] + 0.05
            for left, right in zip(ordered, ordered[1:])
        ),
        "Supervisor invocations overlap",
    )
    checks["supervisor_budgets_and_resource_guards"] = True
    return invocations


def _audit(root, report):
    job = read(root / "job.json")
    checks = report["checks"]
    require(
        job["schema_version"] == 1
        and job["version"] == training.VERSION
        and job["lora"] == training.LORA
        and training._config(job["config"]) == job["config"],
        "Unsupported frozen training contract",
    )
    require(
        finite(job)
        and job["deadline_unix"] == job["started_unix"] + job["config"]["time_budget_seconds"]
        and job["microbatch_size"] == 1
        and job["loss"] == "completion_and_eos_only_token_mean"
        and job["token_accounting"] == "reserved_padded_forward_tokens_including_abandoned_updates",
        "Job budget/loss differs",
    )
    require(
        job["source"]["files"] == archived_source(job["source"]["revision"]),
        "Source fingerprints differ from recorded Git revision",
    )
    for name in ("training.py", "policy.py", "demonstrations.py"):
        require(
            digest(Path(training.__file__).with_name(name))
            == job["source"]["files"][f"src/spire/language/{name}"],
            "Auditor requires the recorded canonical validators",
        )
    checks["frozen_contract_and_archived_source"] = True
    examples, pins = training.verify_dataset(Path(job["config"]["dataset"]))
    require(
        pins == job["dataset"] and [item["id"] for item in examples] == job["example_ids"],
        "Dataset/origin identity differs from independently audited examples",
    )
    require(
        job["base"]["adapter"] is None
        and job["base"]["base"]["directory"] == job["config"]["base_snapshot"],
        "Training base differs from pinned unadapted declaration",
    )
    validate_declaration(job["base"])
    checks["independent_dataset_and_pinned_base"] = True
    payload, pointer = training.load_checkpoint(root)
    state = payload["state"]
    require(
        all(
            type(state[key]) is int and state[key] >= 0
            for key in (
                "generation",
                "updates",
                "charged_tokens",
                "committed_tokens",
                "model_parameters",
                "trainable_parameters",
            )
        ),
        "Invalid checkpoint counter types",
    )
    require(
        state["trainable_parameters"]
        == sum(tensor.numel() for tensor in payload["adapter"].values())
        and state["trainable_dtypes"]
        == sorted({str(tensor.dtype) for tensor in payload["adapter"].values()})
        and state["model_parameters"] > state["trainable_parameters"],
        "Saved trainable parameter counts/dtypes differ from adapter tensors",
    )
    adapter_config = payload["adapter_config"]
    require(
        all(
            adapter_config[key] == value
            for key, value in training.LORA.items()
            if key != "target_modules"
        )
        and sorted(adapter_config["target_modules"]) == sorted(training.LORA["target_modules"]),
        "Checkpoint LoRA configuration differs from fixed contract",
    )
    random.Random().setstate(payload["rng"]["python"])
    torch.Generator(device="cpu").set_state(payload["rng"]["torch"])
    require(
        all(
            value.dtype == torch.uint8 and value.ndim == 1 and value.numel()
            for value in payload["rng"]["cuda"]
        ),
        "Invalid saved CUDA RNG bytes",
    )
    for group in payload["optimizer"]["param_groups"]:
        require(
            group["lr"] == job["config"]["learning_rate"]
            and group["weight_decay"] == 0.01
            and tuple(group["betas"]) == (0.9, 0.999)
            and group["eps"] == 1e-8,
            "Optimizer configuration differs from fixed contract",
        )
    for item in state["history"]:
        require(
            all(type(item[name]) in (int, float) for name in ("loss", "gradient_norm"))
            and 0
            < item["supervised_tokens"]
            <= item["input_tokens"]
            <= job["config"]["batch_size"] * job["config"]["max_sequence_tokens"],
            "Invalid update loss/token metrics",
        )
        require(
            item["resources"]["available_mib"] >= job["config"]["min_available_mib"]
            and item["resources"].get("cuda_peak_reserved_mib", 0)
            < job["config"]["max_gpu_gib"] * 1024,
            "A committed update exceeded resource guards",
        )
    checks["canonical_checkpoint_accounting_rng_and_optimizer"] = True
    checkpoints, changed = _checkpoints(root, job, payload, pointer, checks)
    summary = read(root / "training.json")
    require(
        summary["version"] == training.VERSION
        and summary["schema_version"] == 1
        and finite(summary)
        and summary["checkpoint"] == pointer
        and summary["job_sha256"] == digest(root / "job.json")
        and summary["source_revision"] == job["source"]["revision"]
        and summary["dataset_manifest_sha256"] == pins["manifest_sha256"]
        and summary["deadline_unix"] == job["deadline_unix"],
        "Summary lineage differs",
    )
    for name in (
        "updates",
        "charged_tokens",
        "committed_tokens",
        "pending",
        "adapter_sha256",
        "history",
        "initial_adapter_sha256",
        "reservations",
        "model_parameters",
        "trainable_parameters",
        "trainable_dtypes",
    ):
        require(summary[name] == state[name], f"Summary {name} differs from committed state")
    require(
        summary["consumed_examples"] == len(state["consumed"]), "Summary consumed count differs"
    )
    require(
        summary["status"] in {"completed", "stopped", "interrupted"},
        "Audit requires a stopped job with an authoritative final summary",
    )
    reason = summary["stop_reason"]
    normal = reason in {"update_limit", "token_limit", "deadline", "finalized"}
    require(
        summary["status"]
        == ("completed" if reason == "update_limit" else "stopped" if normal else "interrupted"),
        "Summary stop status differs",
    )
    require(not normal or "artifact" in summary, "Stopped job lacks its committed export")
    if reason == "update_limit":
        require(state["updates"] == job["config"]["max_updates"], "Update-limit claim is premature")
    if reason == "token_limit":
        require(
            state["charged_tokens"]
            + job["config"]["batch_size"] * job["config"]["max_sequence_tokens"]
            > job["config"]["max_tokens"],
            "Token-limit claim is premature",
        )
    if reason == "deadline":
        require(
            summary["elapsed_seconds"] >= job["config"]["time_budget_seconds"],
            "Deadline claim is premature",
        )
    checks["summary_matches_committed_stop"] = True
    exports = _exports(root, job, checkpoints, summary, checks)
    invocations = _supervision(root, job, checks)
    last = max(invocations, key=lambda item: item["started_unix"])
    summary_time = job["started_unix"] + summary["elapsed_seconds"]
    require(
        summary["elapsed_seconds"] >= 0
        and last["started_unix"] <= summary_time + 0.05
        and summary_time <= last["started_unix"] + last["elapsed_seconds"] + 0.05,
        "Summary elapsed time is outside final supervised invocation",
    )
    require(
        abs(summary["cleanup_overrun_seconds"] - max(0, summary_time - job["deadline_unix"]))
        < 0.05,
        "Summary cleanup overrun differs",
    )
    require(
        not normal or last["exit_code"] == 0, "Normal final summary lacks successful worker exit"
    )
    checks["summary_within_final_supervised_invocation"] = True
    report.update(
        source_revision=job["source"]["revision"],
        checkpoint=pointer,
        stop_reason=reason,
        updates=state["updates"],
        changed_adapter_elements=changed,
        charged_tokens=state["charged_tokens"],
        committed_tokens=state["committed_tokens"],
        consumed_examples=len(state["consumed"]),
        dataset_manifest_sha256=pins["manifest_sha256"],
        reservations={
            status: sum(item["status"] == status for item in state["reservations"])
            for status in ("committed", "reserved", "abandoned_before_commit")
        },
        checkpoint_count=len(checkpoints),
        exports=exports,
        invocations=invocations,
        deadline_unix=job["deadline_unix"],
        history=state["history"],
    )


def audit_language_training(run: Path) -> dict:
    torch.set_num_threads(1)
    root = Path(run).resolve()
    result = {
        "schema_version": 1,
        "run": str(root),
        "valid": False,
        "errors": [],
        "checks": {},
        "scope": "Saved supervised-imitation integrity; no learning or gameplay-quality claim",
    }
    try:
        before = {
            str(path.relative_to(root)): digest(path) for path in root.rglob("*") if path.is_file()
        }
        _audit(root, result)
        after = {
            str(path.relative_to(root)): digest(path) for path in root.rglob("*") if path.is_file()
        }
        require(before == after, "Training evidence changed during read-only audit")
        result["checks"]["evidence_unchanged_during_audit"] = True
        result["valid"] = True
    except Exception as error:
        result["errors"].append(f"{type(error).__name__}: {error}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()
    if args.output and args.output.resolve().is_relative_to(args.run.resolve()):
        parser.error("Audit output must be outside the input run")
    result = audit_language_training(args.run)
    encoded = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end="")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
