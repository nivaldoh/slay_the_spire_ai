"""Bounded completion-only LoRA training on independently audited public demonstrations."""

from __future__ import annotations

import copy
import fcntl
import gc
import hashlib
import importlib.metadata
import json
import math
import os
import random
import resource
import signal
import tempfile
import time
import traceback
import uuid
from contextlib import contextmanager
from pathlib import Path

import torch

from gameai.lm import _json, tensor_hash  # noqa: F401  (re-exported)
from gameai.provenance import committed_revision, source_fingerprints, write_json
from spire.language.demonstrations import DemonstrationSource, export_demonstrations

VERSION = "public-heuristic-completion-lora-v1"
LORA = {
    "r": 8,
    "lora_alpha": 16,
    "lora_dropout": 0.0,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    "bias": "none",
    "task_type": "CAUSAL_LM",
}


class TrainingDeadline(BaseException):
    """Abort uncommitted work; the checkpoint pointer remains authoritative."""


def _sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _read(path: Path):
    return json.loads(path.read_text())


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _source() -> dict:
    return {
        "revision": committed_revision("language training"),
        "files": source_fingerprints(),
    }


def _dependencies() -> dict:
    result = {}
    for name in ("torch", "transformers", "peft", "accelerate", "safetensors"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def _config(value: dict) -> dict:
    from spire.language.policy import DECODER, MAX_PROMPT_TOKENS

    required = {
        "base_snapshot",
        "dataset",
        "seed",
        "max_updates",
        "time_budget_seconds",
        "max_tokens",
        "batch_size",
        "max_sequence_tokens",
        "learning_rate",
    }
    optional = {"min_available_mib", "max_gpu_gib"}
    _require(
        type(value) is dict and required <= value.keys() and not value.keys() - required - optional,
        "Unknown or missing training configuration",
    )
    result = {"min_available_mib": 700.0, "max_gpu_gib": 10.0, **value}
    for key in ("seed", "max_updates", "max_tokens", "batch_size", "max_sequence_tokens"):
        _require(
            type(result[key]) is int and result[key] >= (0 if key == "seed" else 1),
            f"Invalid {key}",
        )
    for key in ("time_budget_seconds", "learning_rate", "min_available_mib", "max_gpu_gib"):
        _require(
            type(result[key]) in (int, float) and math.isfinite(result[key]) and result[key] > 0,
            f"Invalid {key}",
        )
    for key in ("base_snapshot", "dataset"):
        result[key] = str(Path(result[key]).resolve())
    _require(
        result["seed"] < 2**64
        and result["max_sequence_tokens"] <= MAX_PROMPT_TOKENS + DECODER["max_new_tokens"]
        and result["max_tokens"] >= result["batch_size"] * result["max_sequence_tokens"],
        "Seed, sequence or first-batch token budget is unsupported",
    )
    return result


def verify_dataset(directory: Path) -> tuple[list[dict], dict]:
    """Re-export from original engine evidence, rejecting self-asserted dataset hashes."""
    directory = directory.resolve()
    manifest = _read(directory / "manifest.json")
    _require(
        manifest.get("schema_version") == 1 and manifest.get("status") == "completed",
        "Dataset is not a completed supported export",
    )
    _require(manifest.get("purpose") == "supervised_finetuning", "A smoke dataset cannot train")
    sources = manifest["sources"]
    _require(bool(sources), "No demonstration sources")
    teachers = {
        "heuristic": "verified_public_builtin",
        "heuristic_relabel": "public_builtin_relabel",
    }
    for source in sources:
        _require(
            teachers.get(source["source_role"]) == source["teacher_information"]
            and source["split"] != "test"
            and source["original_purpose"] in {"rollout", "training", "development"},
            "Only public heuristic origins without held-out evidence may train",
        )
    declared = [
        DemonstrationSource(Path(item["run"]), item["split"], item["source_role"], "public")
        for item in sources
    ]
    with tempfile.TemporaryDirectory(prefix="spire-sft-audit-") as temporary:
        target = Path(temporary) / "export"
        rebuilt = export_demonstrations(target, declared, purpose="supervised_finetuning")
        _require(rebuilt == manifest, "Dataset differs from independent engine/teacher re-export")
        for name, expected in manifest["files"].items():
            path = (directory / name).resolve()
            _require(
                path.is_relative_to(directory) and _sha(path) == expected,
                f"Dataset evidence changed: {name}",
            )
    rows = [_read_line(line) for line in (directory / "train.jsonl").read_text().splitlines()]
    origins = [_read_line(line) for line in (directory / "origins.jsonl").read_text().splitlines()]
    origins = [item for item in origins if item["split"] == "train"]
    _require(len(rows) == len(origins) > 0, "Training examples lack origin labels")
    examples, ids = [], set()
    for index, (row, origin) in enumerate(zip(rows, origins, strict=True)):
        _require(
            origin["row"] == index and set(row) == {"prompt", "completion"},
            "Example/origin order differs",
        )
        identity = hashlib.sha256(
            _json(
                {key: origin[key] for key in ("origin_run_sha256", "session_id", "transition_id")}
            )
        ).hexdigest()
        _require(identity not in ids, "Duplicate originating transition")
        ids.add(identity)
        examples.append({**row, "id": identity, "origin": origin})
    pins = {
        "manifest_sha256": _sha(directory / "manifest.json"),
        "files": manifest["files"],
        "examples_sha256": hashlib.sha256(_json(examples)).hexdigest(),
        "development_reuse": manifest["development_reuse"],
        "research_scope": manifest["research_scope"],
        "origin_files": {
            str(_origin_path(Path(source["run"]), name)): expected
            for source in sources
            for name, expected in source["files"].items()
        },
    }
    return examples, pins


def _origin_path(run: Path, name: str) -> Path:
    if name.startswith("catalog-suite/"):
        filename = name.removeprefix("catalog-suite/")
        _require(filename == f"{run.name}.json", "Unexpected catalog suite evidence path")
        return run.parent.parent / "suites" / filename
    path = (run / name).resolve()
    _require(path.is_relative_to(run.resolve()), "Origin evidence path escapes run")
    return path


def _read_line(line: str):
    return json.loads(line)


def tokenize_example(example: dict, tokenizer, max_sequence_tokens: int) -> dict:
    from spire.language.policy import DECODER, MAX_PROMPT_TOKENS

    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": example["prompt"]}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    prefix = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    target = tokenizer(example["completion"], add_special_tokens=False)["input_ids"]
    _require(type(tokenizer.eos_token_id) is int, "Tokenizer has no EOS token")
    target = [*target, tokenizer.eos_token_id]
    _require(
        bool(prefix)
        and len(prefix) <= MAX_PROMPT_TOKENS
        and 1 < len(target) <= DECODER["max_new_tokens"]
        and len(prefix) + len(target) <= max_sequence_tokens,
        "An example exceeds the frozen prompt/completion/sequence budget; no truncation",
    )
    padding = max_sequence_tokens - len(prefix) - len(target)
    return {
        "id": example["id"],
        "input_ids": prefix + target + [tokenizer.eos_token_id] * padding,
        "attention_mask": [1] * (len(prefix) + len(target)) + [0] * padding,
        "labels": [-100] * len(prefix) + target + [-100] * padding,
        "supervised_tokens": len(target),
        "input_tokens": len(prefix) + len(target),
    }


def _cpu(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: _cpu(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_cpu(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_cpu(item) for item in value)
    return copy.deepcopy(value)


def _finite(value) -> bool:
    if isinstance(value, torch.Tensor):
        return bool(torch.isfinite(value).all())
    if isinstance(value, dict):
        return all(_finite(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return all(_finite(item) for item in value)
    return not isinstance(value, (float, int)) or math.isfinite(value)


def _adapter(model) -> dict:
    from peft import get_peft_model_state_dict

    return _cpu(get_peft_model_state_dict(model))


def _restore_adapter(model, state: dict) -> None:
    from peft import set_peft_model_state_dict

    set_peft_model_state_dict(model, state)
    _require(tensor_hash(_adapter(model)) == tensor_hash(state), "Adapter restore differs")


def _load_tokenizer(snapshot: str):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False)


def _load_model(config: dict):
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM

    _require(torch.cuda.is_available(), "Real language training requires CUDA and the llm extra")
    torch.cuda.set_per_process_memory_fraction(0.70)
    torch.cuda.reset_peak_memory_stats()
    model = AutoModelForCausalLM.from_pretrained(
        config["base_snapshot"],
        local_files_only=True,
        dtype=torch.bfloat16,
        device_map={"": "cuda:0"},
        attn_implementation="sdpa",
        trust_remote_code=False,
    )
    model = get_peft_model(model, LoraConfig(**LORA))
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    trainable = [name for name, p in model.named_parameters() if p.requires_grad]
    _require(
        trainable and all("lora_" in name for name in trainable),
        "Unexpected trainable base parameter",
    )
    with tempfile.TemporaryDirectory(prefix="spire-lora-config-") as temporary:
        model.peft_config["default"].save_pretrained(temporary)
        adapter_config = _read(Path(temporary) / "adapter_config.json")
    return model, adapter_config


def _resource_snapshot(config: dict) -> dict:
    fields = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    memory = int(fields["MemAvailable"].split()[0]) / 1024
    result = {
        "available_mib": memory,
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    _require(memory >= config["min_available_mib"], "Available RAM below training guard")
    if torch.cuda.is_initialized():
        torch.cuda.synchronize()
        peak = torch.cuda.max_memory_reserved() / 2**20
        result.update(
            cuda_peak_reserved_mib=peak,
            cuda_peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
        )
        _require(peak < config["max_gpu_gib"] * 1024, "GPU memory guard reached")
    return result


@contextmanager
def _deadline(deadline_unix: float):
    remaining = deadline_unix - time.time()
    if remaining <= 0:
        raise TrainingDeadline()
    _require(not signal.getitimer(signal.ITIMER_REAL)[0], "Training needs an unused process alarm")
    previous = signal.getsignal(signal.SIGALRM)

    def expire(*_):
        raise TrainingDeadline()

    signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, remaining)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _optimizer_step(model, optimizer, examples: list[dict], config: dict) -> dict:
    before = _adapter(model)
    supervised = sum(item["supervised_tokens"] for item in examples)
    trainable = [p for p in model.parameters() if p.requires_grad]
    model.train()
    optimizer.zero_grad(set_to_none=True)
    loss_total = 0.0
    device = next(model.parameters()).device
    for example in examples:
        batch = {
            key: torch.tensor([example[key]], device=device)
            for key in ("input_ids", "attention_mask", "labels")
        }
        result = model(**batch)
        loss = result.loss * (example["supervised_tokens"] / supervised)
        _require(bool(torch.isfinite(loss)), "Nonfinite completion loss")
        loss_total += float(loss.detach())
        loss.backward()
        del result, loss, batch
        _resource_snapshot(config)
    _require(
        all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in trainable),
        "Nonfinite adapter gradient",
    )
    norm = torch.nn.utils.clip_grad_norm_(trainable, 1.0)
    _require(bool(torch.isfinite(norm)) and float(norm) > 0, "No finite nonzero adapter gradient")
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    after = _adapter(model)
    changed = sum(int((before[key] != value).sum()) for key, value in after.items())
    _require(
        changed > 0 and _finite(after) and _finite(optimizer.state_dict()),
        "Update did not produce changed finite adapter/optimizer state",
    )
    return {
        "loss": loss_total,
        "gradient_norm": float(norm),
        "changed_elements": changed,
        "finite_gradients": True,
        "finite_optimizer": True,
        "before_sha256": tensor_hash(before),
        "after_sha256": tensor_hash(after),
        "supervised_tokens": supervised,
        "input_tokens": sum(item["input_tokens"] for item in examples),
        "resources": _resource_snapshot(config),
    }


def _rng() -> dict:
    return {
        "python": random.getstate(),
        "torch": torch.get_rng_state(),
        "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else [],
    }


def _restore_rng(value: dict) -> None:
    random.setstate(value["python"])
    torch.set_rng_state(value["torch"])
    if value["cuda"]:
        torch.cuda.set_rng_state_all(value["cuda"])


def _atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}-{uuid.uuid4().hex}.tmp")
    with temporary.open("xb") as handle:
        handle.write(_json(value) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _commit(output: Path, payload: dict) -> dict:
    payload["state"]["generation"] += 1
    temporary = output / "checkpoints" / f".{uuid.uuid4().hex}.tmp"
    with temporary.open("xb") as handle:
        torch.save(payload, handle)
        handle.flush()
        os.fsync(handle.fileno())
    identity = _sha(temporary)
    name = f"{payload['state']['generation']:06d}-{identity}.pt"
    temporary.replace(output / "checkpoints" / name)
    _fsync_directory(output / "checkpoints")
    pointer = {
        "path": f"checkpoints/{name}",
        "sha256": identity,
        "generation": payload["state"]["generation"],
        "updates": payload["state"]["updates"],
        "deadline_unix": payload["state"]["deadline_unix"],
    }
    _atomic_json(output / "checkpoint.json", pointer)
    return pointer


def load_checkpoint(output: Path) -> tuple[dict, dict]:
    pointer = _read(output / "checkpoint.json")
    path = (output / pointer["path"]).resolve()
    _require(
        path.is_relative_to(output.resolve()) and _sha(path) == pointer["sha256"],
        "Checkpoint pointer or content changed",
    )
    payload = torch.load(path, map_location="cpu", weights_only=True)
    _require(
        payload["version"] == VERSION and payload["schema_version"] == 1,
        "Checkpoint version mismatch",
    )
    state = payload["state"]
    for key in ("generation", "updates", "deadline_unix"):
        _require(state[key] == pointer[key], f"Checkpoint {key} differs from pointer")
    _require(
        _finite(payload["adapter"])
        and _finite(payload["optimizer"])
        and tensor_hash(payload["adapter"]) == state["adapter_sha256"],
        "Checkpoint has invalid adapter/optimizer tensors",
    )
    reservations = state["reservations"]
    _require(
        all(
            item["status"] in {"reserved", "committed", "abandoned_before_commit"}
            and type(item["tokens"]) is int
            and item["tokens"] > 0
            for item in reservations
        ),
        "Invalid checkpoint token reservation",
    )
    committed = [item for item in reservations if item["status"] == "committed"]
    pending = [index for index, item in enumerate(reservations) if item["status"] == "reserved"]
    _require(
        pending == ([] if state["pending"] is None else [state["pending"]])
        and (not pending or pending == [len(reservations) - 1]),
        "Invalid pending reservation",
    )
    _require(
        state["charged_tokens"] == sum(item["tokens"] for item in reservations)
        and state["committed_tokens"] == sum(item["tokens"] for item in committed)
        and state["updates"] == len(committed) == len(state["history"])
        and [item["update"] for item in committed] == list(range(1, state["updates"] + 1)),
        "Checkpoint budget accounting differs",
    )
    consumed = [occurrence for item in committed for occurrence in item["occurrences"]]
    _require(
        state["consumed"] == consumed and len({_json(item) for item in consumed}) == len(consumed),
        "Checkpoint consumed example accounting differs",
    )
    previous = state["initial_adapter_sha256"]
    for index, metrics in enumerate(state["history"], 1):
        _require(
            _finite(metrics)
            and metrics["update"] == index
            and metrics["before_sha256"] == previous
            and metrics["changed_elements"] > 0
            and metrics["gradient_norm"] > 0
            and metrics["finite_gradients"] is True
            and metrics["finite_optimizer"] is True,
            "Checkpoint update metrics differ",
        )
        previous = metrics["after_sha256"]
    _require(previous == state["adapter_sha256"], "Checkpoint adapter history differs")
    job = _read(output / "job.json")
    _require(
        state["job_sha256"] == _sha(output / "job.json"), "Checkpoint belongs to a different job"
    )
    _validate_schedule(state, job)
    return payload, pointer


def _initial_sampler(seed: int, count: int) -> dict:
    generator = random.Random(seed)
    order = list(range(count))
    generator.shuffle(order)
    return {"epoch": 0, "position": 0, "order": order, "rng": generator.getstate()}


def _validate_schedule(state: dict, job: dict) -> None:
    config = job["config"]
    ids = job["example_ids"]
    _require(bool(ids) and len(set(ids)) == len(ids), "Invalid frozen example identities")
    _require(
        state["updates"] <= config["max_updates"]
        and state["charged_tokens"] <= config["max_tokens"]
        and state["deadline_unix"] == job["deadline_unix"],
        "Checkpoint exceeds frozen job budgets",
    )
    replay = {"sampler": _initial_sampler(config["seed"], len(ids))}
    examples = [{"id": identity} for identity in ids]
    for reservation in state["reservations"]:
        plan = _plan_batch(replay, examples, config["batch_size"])
        _require(
            reservation["occurrences"] == plan["occurrences"]
            and reservation["tokens"] == config["batch_size"] * config["max_sequence_tokens"],
            "Checkpoint occurrences differ from frozen deterministic schedule",
        )
        if reservation["status"] == "committed":
            replay["sampler"] = plan["after_sampler"]
    _require(state["sampler"] == replay["sampler"], "Checkpoint sampler differs from replay")


def _plan_batch(state: dict, examples: list[dict], batch_size: int) -> dict:
    sampler = copy.deepcopy(state["sampler"])
    generator = random.Random()
    generator.setstate(sampler["rng"])
    indices, occurrences = [], []
    for _ in range(batch_size):
        if sampler["position"] == len(examples):
            sampler["epoch"] += 1
            sampler["position"] = 0
            generator.shuffle(sampler["order"])
        index = sampler["order"][sampler["position"]]
        indices.append(index)
        occurrences.append(
            {
                "example_id": examples[index]["id"],
                "epoch": sampler["epoch"],
                "position": sampler["position"],
            }
        )
        sampler["position"] += 1
    sampler["rng"] = generator.getstate()
    return {"indices": indices, "occurrences": occurrences, "after_sampler": sampler}


def _verify_frozen(job: dict, *, base: bool = False) -> None:
    from spire.language.policy import validate_declaration

    _require(_source() == job["source"], "Training implementation changed")
    _require(_dependencies() == job["dependencies"], "Training dependency versions changed")
    directory = Path(job["config"]["dataset"])
    pins = job["dataset"]
    _require(
        _sha(directory / "manifest.json") == pins["manifest_sha256"], "Dataset manifest changed"
    )
    for name, expected in pins["files"].items():
        _require(_sha(directory / name) == expected, "Dataset file changed")
    for name, expected in pins["origin_files"].items():
        _require(_sha(Path(name)) == expected, "Originating game evidence changed")
    if base:
        validate_declaration(job["base"])


def prepare_run(output: Path, config: dict, *, started_unix: float | None = None) -> dict:
    """Freeze the source, dataset/base pins and absolute budget before GPU work."""
    from spire.language.policy import create_declaration

    config = _config(config)
    started = time.time() if started_unix is None else started_unix
    _require(
        type(started) in (int, float) and math.isfinite(started) and 0 <= started <= time.time(),
        "Invalid launch start time",
    )
    source = _source()
    examples, dataset = verify_dataset(Path(config["dataset"]))
    declaration = create_declaration(Path(config["base_snapshot"]))
    job = {
        "schema_version": 1,
        "version": VERSION,
        "config": config,
        "source": source,
        "dependencies": _dependencies(),
        "dataset": dataset,
        "base": declaration,
        "lora": LORA,
        "started_unix": started,
        "deadline_unix": started + config["time_budget_seconds"],
        "example_ids": [item["id"] for item in examples],
        "loss": "completion_and_eos_only_token_mean",
        "microbatch_size": 1,
        "token_accounting": "reserved_padded_forward_tokens_including_abandoned_updates",
    }
    _verify_frozen(job, base=True)
    output.mkdir(parents=True, exist_ok=False)
    (output / "checkpoints").mkdir()
    (output / "artifacts").mkdir()
    _atomic_json(output / "job.json", job)
    return job


def _export(output: Path, payload: dict, pointer: dict, job: dict) -> dict:
    from safetensors.torch import load_file, save_file

    from spire.language.policy import create_declaration

    state = payload["state"]
    target = output / "artifacts" / f"update-{state['updates']:06d}-{pointer['sha256']}"
    provenance = {
        "trainer_version": VERSION,
        "training_checkpoint_sha256": pointer["sha256"],
        "training_job_sha256": state["job_sha256"],
        "source_revision": job["source"]["revision"],
        "source_files_sha256": hashlib.sha256(_json(job["source"]["files"])).hexdigest(),
        "dataset_manifest_sha256": job["dataset"]["manifest_sha256"],
        "updates": state["updates"],
        "adapter_sha256": state["adapter_sha256"],
        "consumed_example_ids_sha256": hashlib.sha256(_json(state["consumed"])).hexdigest(),
        "scope": "Public heuristic imitation; no gameplay performance claim",
    }
    adapter_config = {**payload["adapter_config"], "inference_mode": True}
    if target.exists():
        record = _read(target / "export.json")
        _require(
            record["checkpoint_sha256"] == pointer["sha256"]
            and record["adapter_sha256"] == state["adapter_sha256"]
            and record["declaration"] == str(target / "policy.json")
            and set(record["files"])
            == {"adapter/adapter_config.json", "adapter/adapter_model.safetensors", "policy.json"},
            "Export checkpoint or inventory differs",
        )
        for name, expected in record["files"].items():
            _require(_sha(target / name) == expected, "Existing export changed")
        adapter = target / "adapter"
        _require(
            tensor_hash(load_file(adapter / "adapter_model.safetensors"))
            == state["adapter_sha256"],
            "Existing export adapter differs from checkpoint",
        )
        _require(
            _read(adapter / "adapter_config.json") == adapter_config,
            "Existing export adapter configuration differs",
        )
        expected = create_declaration(
            Path(job["config"]["base_snapshot"]), adapter_directory=adapter, provenance=provenance
        )
        _require(
            _read(target / "policy.json") == expected,
            "Existing export declaration differs from training provenance",
        )
        return {"directory": str(target), **record}
    temporary = output / "artifacts" / f".export-{uuid.uuid4().hex}"
    adapter = temporary / "adapter"
    adapter.mkdir(parents=True)
    save_file(payload["adapter"], str(adapter / "adapter_model.safetensors"))
    _require(
        tensor_hash(load_file(adapter / "adapter_model.safetensors")) == state["adapter_sha256"],
        "Exported adapter does not reproduce checkpoint tensors",
    )
    write_json(adapter / "adapter_config.json", adapter_config)
    declaration = create_declaration(
        Path(job["config"]["base_snapshot"]), adapter_directory=adapter, provenance=provenance
    )
    declaration["adapter"]["directory"] = str(target / "adapter")
    write_json(temporary / "policy.json", declaration)
    record = {
        "checkpoint_sha256": pointer["sha256"],
        "adapter_sha256": state["adapter_sha256"],
        "declaration": str(target / "policy.json"),
        "files": {
            str(path.relative_to(temporary)): _sha(path)
            for path in sorted(temporary.rglob("*"))
            if path.is_file()
        },
    }
    write_json(temporary / "export.json", record)
    for path in temporary.rglob("*"):
        if path.is_file():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
    _fsync_directory(adapter)
    _fsync_directory(temporary)
    temporary.replace(target)
    _fsync_directory(output / "artifacts")
    return {"directory": str(target), **record}


def _summary(output: Path, job: dict, reason: str, resources: dict) -> dict:
    result = {
        "schema_version": 1,
        "version": VERSION,
        "stop_reason": reason,
        "deadline_unix": job["deadline_unix"],
        "job_sha256": _sha(output / "job.json"),
        "source_revision": job["source"]["revision"],
        "dataset_manifest_sha256": job["dataset"]["manifest_sha256"],
        "resources": resources,
        "elapsed_seconds": time.time() - job["started_unix"],
        "scope": "Computational supervised imitation; no gameplay evaluation claim",
        "status": {
            "running": "running",
            "update_limit": "completed",
            "token_limit": "stopped",
            "deadline": "stopped",
            "finalized": "stopped",
        }.get(reason, "interrupted"),
        "cleanup_overrun_seconds": max(0.0, time.time() - job["deadline_unix"]),
    }
    if (output / "checkpoint.json").exists():
        payload, pointer = load_checkpoint(output)
        state = payload["state"]
        result.update(
            checkpoint=pointer,
            updates=state["updates"],
            consumed_examples=len(state["consumed"]),
            charged_tokens=state["charged_tokens"],
            committed_tokens=state["committed_tokens"],
            pending=state["pending"],
            adapter_sha256=state["adapter_sha256"],
            history=state["history"],
            initial_adapter_sha256=state["initial_adapter_sha256"],
            reservations=state["reservations"],
            model_parameters=state["model_parameters"],
            trainable_parameters=state["trainable_parameters"],
            trainable_dtypes=state["trainable_dtypes"],
        )
        if reason in {"update_limit", "token_limit", "deadline", "finalized"}:
            result["artifact"] = _export(output, payload, pointer, job)
    result["elapsed_seconds"] = time.time() - job["started_unix"]
    result["cleanup_overrun_seconds"] = max(0.0, time.time() - job["deadline_unix"])
    _atomic_json(output / "training.json", result)
    return result


def train_language(
    output: Path,
    config: dict | None = None,
    *,
    resume: bool = False,
    started_unix: float | None = None,
    finalize_only: bool = False,
) -> dict:
    """Train once under the GPU lease. The CLI adds an external resource watchdog."""
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with (output.parent / f".{output.name}.training.lock").open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another process owns this language training run") from error
        try:
            return _train_language(
                output,
                config,
                resume=resume,
                started_unix=started_unix,
                finalize_only=finalize_only,
            )
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _train_language(
    output: Path,
    config: dict | None,
    *,
    resume: bool,
    started_unix: float | None = None,
    finalize_only: bool = False,
) -> dict:
    from spire.language.policy import gpu_lease

    output = Path(output).resolve()
    _require(not finalize_only or resume, "Finalization requires an existing job")
    if resume:
        _require(started_unix is None, "Resume retains the original launch time")
        job = _read(output / "job.json")
        _require(job["version"] == VERSION and job["lora"] == LORA, "Training job version differs")
        _require(
            _config(job["config"]) == job["config"]
            and job["deadline_unix"] == job["started_unix"] + job["config"]["time_budget_seconds"],
            "Training job budget differs",
        )
        if config is not None:
            _require(
                _config(config) == job["config"], "Resume cannot change configuration or budgets"
            )
    else:
        _require(config is not None, "New training requires explicit configuration")
        job = prepare_run(output, config, started_unix=started_unix)
    config = job["config"]
    job_hash = _sha(output / "job.json")
    _verify_frozen(job, base=True)
    payload = None
    if (output / "checkpoint.json").exists():
        payload, _ = load_checkpoint(output)
        _require(
            payload["state"]["job_sha256"] == job_hash, "Checkpoint belongs to a different job"
        )
        _require(
            payload["state"]["deadline_unix"] == job["deadline_unix"]
            and payload["state"]["updates"] <= config["max_updates"]
            and payload["state"]["charged_tokens"] <= config["max_tokens"],
            "Checkpoint exceeds frozen job budgets",
        )
        if payload["state"]["pending"] is not None:
            pending = payload["state"]["pending"]
            payload["state"]["reservations"][pending]["status"] = "abandoned_before_commit"
            payload["state"]["pending"] = None
            _commit(output, payload)
    resources, reason = {}, "initializing"
    model = optimizer = None
    try:
        if finalize_only:
            _require(payload is not None, "No committed checkpoint exists to finalize")
            reason = "deadline" if time.time() >= job["deadline_unix"] else "finalized"
            return _summary(output, job, reason, resources)
        if time.time() >= job["deadline_unix"]:
            return _summary(output, job, "deadline", resources)
        if payload is not None and payload["state"]["updates"] >= config["max_updates"]:
            return _summary(output, job, "update_limit", resources)
        if (
            payload is not None
            and payload["state"]["charged_tokens"]
            + config["batch_size"] * config["max_sequence_tokens"]
            > config["max_tokens"]
        ):
            return _summary(output, job, "token_limit", resources)
        with gpu_lease(), _deadline(job["deadline_unix"]):
            try:
                resources = _resource_snapshot(config)
                torch.set_num_threads(1)
                random.seed(config["seed"])
                torch.manual_seed(config["seed"])
                tokenizer = _load_tokenizer(config["base_snapshot"])
                examples, pins = verify_dataset(Path(config["dataset"]))
                _require(pins == job["dataset"], "Verified dataset identity changed")
                encoded = [
                    tokenize_example(item, tokenizer, config["max_sequence_tokens"])
                    for item in examples
                ]
                model, adapter_config = _load_model(config)
                optimizer = torch.optim.AdamW(
                    [p for p in model.parameters() if p.requires_grad],
                    lr=config["learning_rate"],
                    weight_decay=0.01,
                )
                if payload is None:
                    state = {
                        "generation": 0,
                        "updates": 0,
                        "job_sha256": job_hash,
                        "deadline_unix": job["deadline_unix"],
                        "charged_tokens": 0,
                        "committed_tokens": 0,
                        "consumed": [],
                        "history": [],
                        "reservations": [],
                        "pending": None,
                        "sampler": _initial_sampler(config["seed"], len(encoded)),
                        "adapter_sha256": tensor_hash(_adapter(model)),
                        "model_parameters": sum(p.numel() for p in model.parameters()),
                        "trainable_parameters": sum(
                            p.numel() for p in model.parameters() if p.requires_grad
                        ),
                        "trainable_dtypes": sorted(
                            {str(p.dtype) for p in model.parameters() if p.requires_grad}
                        ),
                    }
                    state["initial_adapter_sha256"] = state["adapter_sha256"]
                    payload = {
                        "schema_version": 1,
                        "version": VERSION,
                        "state": state,
                        "adapter": _adapter(model),
                        "adapter_config": adapter_config,
                        "optimizer": _cpu(optimizer.state_dict()),
                        "rng": _cpu(_rng()),
                    }
                    _commit(output, payload)
                else:
                    state = payload["state"]
                    _restore_adapter(model, payload["adapter"])
                    optimizer.load_state_dict(payload["optimizer"])
                    _restore_rng(payload["rng"])
                while True:
                    _verify_frozen(job)
                    _require(_sha(output / "job.json") == job_hash, "Training job changed")
                    if state["updates"] >= config["max_updates"]:
                        reason = "update_limit"
                        break
                    charge = config["batch_size"] * config["max_sequence_tokens"]
                    if state["charged_tokens"] + charge > config["max_tokens"]:
                        reason = "token_limit"
                        break
                    plan = _plan_batch(state, encoded, config["batch_size"])
                    state["charged_tokens"] += charge
                    state["pending"] = len(state["reservations"])
                    state["reservations"].append(
                        {"status": "reserved", "tokens": charge, "occurrences": plan["occurrences"]}
                    )
                    _commit(output, payload)  # Charge before any forward computation.
                    metrics = _optimizer_step(
                        model, optimizer, [encoded[i] for i in plan["indices"]], config
                    )
                    _verify_frozen(job)
                    if time.time() >= job["deadline_unix"]:
                        raise TrainingDeadline()
                    state["updates"] += 1
                    state["committed_tokens"] += charge
                    state["consumed"].extend(plan["occurrences"])
                    _require(
                        len({_json(item) for item in state["consumed"]}) == len(state["consumed"]),
                        "An example occurrence was consumed twice",
                    )
                    state["sampler"] = plan["after_sampler"]
                    state["reservations"][state["pending"]].update(
                        status="committed", update=state["updates"]
                    )
                    state["pending"] = None
                    state["history"].append({"update": state["updates"], **metrics})
                    payload.update(
                        adapter=_adapter(model),
                        optimizer=_cpu(optimizer.state_dict()),
                        rng=_cpu(_rng()),
                    )
                    state["adapter_sha256"] = tensor_hash(payload["adapter"])
                    _commit(output, payload)
                    resources = _resource_snapshot(config)
                    _summary(output, job, "running", resources)
            except BaseException as error:
                # Tracebacks from forward/backward can keep CUDA tensors alive across lease exit.
                traceback.clear_frames(error.__traceback__)
                raise
            finally:
                model = optimizer = None
                gc.collect()
                if torch.cuda.is_initialized():
                    torch.cuda.empty_cache()
    except TrainingDeadline:
        reason = "deadline"
    except BaseException as exc:
        _summary(output, job, f"{type(exc).__name__}: {exc}", resources)
        raise
    _verify_frozen(job, base=True)
    return _summary(output, job, reason, resources)
