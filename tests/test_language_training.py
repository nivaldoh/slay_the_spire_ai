"""CPU-only causal toy models exercise transactions; no model download or game launch."""

import copy
import fcntl
import importlib.util
import json
import random
import shutil
import weakref
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
import test_demonstrations

torch = pytest.importorskip("torch")
functional = torch.nn.functional

from spire import language_policy as policy  # noqa: E402
from spire import language_training as training  # noqa: E402
from spire.demonstrations import DemonstrationSource, export_demonstrations  # noqa: E402

REAL_EXPORT = training._export
REAL_DECLARATION = policy.create_declaration
REAL_VALIDATE = policy.validate_declaration
evidence_run = test_demonstrations.evidence_run
run = test_demonstrations.run


class Tokenizer:
    eos_token_id = 1

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs == {
            "tokenize": False,
            "add_generation_prompt": True,
            "enable_thinking": False,
        }
        assert len(messages) == 1 and messages[0]["role"] == "user"
        return "P:" + messages[0]["content"]

    def __call__(self, text, *, add_special_tokens):
        assert add_special_tokens is False
        return {"input_ids": [ord(character) % 14 + 2 for character in text]}


class ToyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.base = torch.nn.Parameter(torch.randn(16, 6), requires_grad=False)
        self.projection = torch.nn.Parameter(torch.randn(6, 16), requires_grad=False)
        self.lora_A = torch.nn.Parameter(torch.randn(6, 2) * 0.1)
        self.lora_B = torch.nn.Parameter(torch.zeros(2, 16))

    def forward(self, input_ids, attention_mask, labels):
        features = self.base[input_ids]
        # Exercise restoration of both Python and Torch RNG, without using CUDA.
        features = features + torch.randn_like(features) * (random.random() * 0.01)
        logits = features @ (self.projection + self.lora_A @ self.lora_B)
        loss = functional.cross_entropy(
            logits[:, :-1].reshape(-1, 16), labels[:, 1:].reshape(-1), ignore_index=-100
        )
        return SimpleNamespace(loss=loss, logits=logits)


@pytest.fixture
def toy(tmp_path, monkeypatch):
    directory = tmp_path / "dataset"
    directory.mkdir()
    (directory / "manifest.json").write_text("{}")
    (directory / "train.jsonl").write_text("evidence\n")
    base = tmp_path / "base"
    base.mkdir()
    examples = [
        {
            "prompt": f"S{index}",
            "completion": '{"a":0}',
            "id": str(index),
            "origin": {"transition_id": index},
        }
        for index in range(3)
    ]
    pins = {
        "manifest_sha256": training._sha(directory / "manifest.json"),
        "files": {"train.jsonl": training._sha(directory / "train.jsonl")},
        "examples_sha256": "e" * 64,
        "development_reuse": True,
        "research_scope": "diagnostic_development",
        "origin_files": {},
    }
    monkeypatch.setattr(training, "_source", lambda: {"revision": "a" * 40, "files": {}})
    monkeypatch.setattr(training, "verify_dataset", lambda _: (copy.deepcopy(examples), pins))
    monkeypatch.setattr(training, "_load_tokenizer", lambda _: Tokenizer())
    models = []

    def model_loader(config):
        model = ToyModel()
        models.append(model)
        return model, {"peft_type": "LORA", "task_type": "CAUSAL_LM", **training.LORA}

    monkeypatch.setattr(training, "_load_model", model_loader)
    monkeypatch.setattr(
        training,
        "_adapter",
        lambda model: training._cpu(
            {name: value for name, value in model.state_dict().items() if "lora_" in name}
        ),
    )
    monkeypatch.setattr(
        training,
        "_restore_adapter",
        lambda model, state: model.load_state_dict(state, strict=False),
    )
    monkeypatch.setattr(training, "_resource_snapshot", lambda _: {"available_mib": 1000})
    monkeypatch.setattr(
        policy, "create_declaration", lambda path, **kwargs: {"base": str(path), **kwargs}
    )
    monkeypatch.setattr(policy, "validate_declaration", lambda _: None)
    monkeypatch.setattr(policy, "gpu_lease", nullcontext)
    monkeypatch.setattr(
        training,
        "_export",
        lambda output, payload, pointer, job: {
            "checkpoint_sha256": pointer["sha256"],
            "adapter_sha256": training.tensor_hash(payload["adapter"]),
        },
    )
    config = {
        "base_snapshot": str(base),
        "dataset": str(directory),
        "seed": 7,
        "max_updates": 3,
        "time_budget_seconds": 600,
        "max_tokens": 1024,
        "batch_size": 2,
        "max_sequence_tokens": 32,
        "learning_rate": 0.01,
    }
    return SimpleNamespace(config=config, examples=examples, models=models, dataset=directory)


def test_mask_includes_completion_and_exactly_one_eos_only():
    example = {"prompt": "state", "completion": '{"a":0}', "id": "id"}
    encoded = training.tokenize_example(example, Tokenizer(), 24)
    prefix = Tokenizer()("P:state", add_special_tokens=False)["input_ids"]
    completion = Tokenizer()('{"a":0}', add_special_tokens=False)["input_ids"] + [1]
    assert encoded["labels"] == [-100] * len(prefix) + completion + [-100] * 9
    assert encoded["input_ids"] == prefix + completion + [1] * 9
    assert encoded["supervised_tokens"] == len(completion)
    assert all(
        label == -100
        for label, attention in zip(encoded["labels"], encoded["attention_mask"], strict=True)
        if not attention
    )
    with pytest.raises(ValueError, match="no truncation"):
        training.tokenize_example(example, Tokenizer(), 10)


def test_reexport_validates_real_audited_public_teacher(tmp_path, run):
    directory = tmp_path / "dataset"
    export_demonstrations(
        directory,
        [DemonstrationSource(run, "train", "heuristic", "public")],
        purpose="supervised_finetuning",
    )
    examples, pins = training.verify_dataset(directory)
    assert len(examples) == 1 and examples[0]["completion"] == '{"a":0}'
    assert pins["origin_files"] and examples[0]["origin"]["source_role"] == "heuristic"
    row = json.loads((directory / "train.jsonl").read_text())
    row["completion"] = '{"a":1}'
    (directory / "train.jsonl").write_text(json.dumps(row) + "\n")
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["files"]["train.jsonl"] = training._sha(directory / "train.jsonl")
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="independent engine/teacher"):
        training.verify_dataset(directory)


def test_reexport_accepts_heuristic_relabels_of_other_behavior(tmp_path, run):
    test_demonstrations.non_heuristic_behavior(run)
    directory = tmp_path / "dataset"
    export_demonstrations(
        directory,
        [DemonstrationSource(run, "train", "heuristic_relabel", "public")],
        purpose="supervised_finetuning",
    )
    examples, _ = training.verify_dataset(directory)
    assert examples[0]["completion"] == '{"a":0}'
    assert examples[0]["origin"]["behavior_policy"] == "random"
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["sources"][0]["teacher_information"] = "verified_public_builtin"
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="public heuristic"):
        training.verify_dataset(directory)


@pytest.mark.parametrize("change", ["smoke", "privileged", "random", "held_out"])
def test_rejects_ineligible_dataset_declarations_before_loading(tmp_path, run, change):
    directory = tmp_path / "dataset"
    manifest = export_demonstrations(
        directory,
        [DemonstrationSource(run, "train", "heuristic", "public")],
        purpose="supervised_finetuning",
    )
    if change == "smoke":
        manifest["purpose"] = "smoke"
    else:
        key = {
            "privileged": "teacher_information",
            "random": "source_role",
            "held_out": "original_purpose",
        }[change]
        manifest["sources"][0][key] = change
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="smoke dataset|public heuristic"):
        training.verify_dataset(directory)


def test_completed_updates_change_only_adapter_and_consume_unique_occurrences(tmp_path, toy):
    output = tmp_path / "run"
    result = training.train_language(output, toy.config)
    payload, _ = training.load_checkpoint(output)
    state = payload["state"]
    assert result["stop_reason"] == "update_limit" and result["updates"] == 3
    assert state["charged_tokens"] == state["committed_tokens"] == 3 * 2 * 32
    assert len(state["consumed"]) == len({training._json(x) for x in state["consumed"]}) == 6
    assert {item["epoch"] for item in state["consumed"]} == {0, 1}
    assert result["initial_adapter_sha256"] != result["adapter_sha256"]
    assert all(
        item["finite_gradients"] and item["finite_optimizer"] and item["changed_elements"] > 0
        for item in state["history"]
    )
    assert toy.models[0].base.grad is None and toy.models[0].projection.grad is None
    torch.manual_seed(toy.config["seed"])
    untouched = ToyModel()
    assert torch.equal(untouched.base, toy.models[0].base)
    assert torch.equal(untouched.projection, toy.models[0].projection)


def test_accumulation_is_supervised_token_mean(toy):
    torch.manual_seed(2)
    random.seed(3)
    model = ToyModel()
    optimizer = torch.optim.AdamW([model.lora_A, model.lora_B], lr=0.01)
    examples = [
        training.tokenize_example({**toy.examples[0], "completion": completion}, Tokenizer(), 32)
        for completion in ('{"a":0}', "x")
    ]
    rng = training._rng()
    with torch.no_grad():
        losses = [
            float(
                model(
                    **{
                        key: torch.tensor([example[key]])
                        for key in ("input_ids", "attention_mask", "labels")
                    }
                ).loss
            )
            for example in examples
        ]
    expected = sum(
        loss * item["supervised_tokens"] for loss, item in zip(losses, examples, strict=True)
    ) / sum(x["supervised_tokens"] for x in examples)
    training._restore_rng(rng)
    metrics = training._optimizer_step(model, optimizer, examples, toy.config)
    assert metrics["loss"] == pytest.approx(expected, rel=1e-6)


def assert_tensors_equal(left, right):
    if isinstance(left, torch.Tensor):
        assert torch.equal(left, right)
    elif isinstance(left, dict):
        assert left.keys() == right.keys()
        for key in left:
            assert_tensors_equal(left[key], right[key])
    elif isinstance(left, (tuple, list)):
        assert len(left) == len(right)
        for first, second in zip(left, right, strict=True):
            assert_tensors_equal(first, second)
    else:
        assert left == right


@pytest.mark.parametrize("point", ["before_update", "after_optimizer", "after_commit"])
def test_resume_matches_uninterrupted_adapter_optimizer_rng_and_cursor(
    tmp_path, toy, monkeypatch, point
):
    reference = tmp_path / "reference"
    training.train_language(reference, toy.config)
    expected, _ = training.load_checkpoint(reference)
    output = tmp_path / "interrupted"
    original_step, original_summary = training._optimizer_step, training._summary
    calls = 0

    def interrupted_step(*args):
        nonlocal calls
        calls += 1
        if calls == 2 and point == "before_update":
            raise KeyboardInterrupt()
        result = original_step(*args)
        if calls == 2 and point == "after_optimizer":
            raise KeyboardInterrupt()
        return result

    def interrupted_summary(*args):
        result = original_summary(*args)
        if point == "after_commit" and args[2] == "running" and result["updates"] == 2:
            raise KeyboardInterrupt()
        return result

    monkeypatch.setattr(training, "_optimizer_step", interrupted_step)
    monkeypatch.setattr(training, "_summary", interrupted_summary)
    with pytest.raises(KeyboardInterrupt):
        training.train_language(output, toy.config)
    previous, _ = training.load_checkpoint(output)
    original_deadline = previous["state"]["deadline_unix"]
    monkeypatch.setattr(training, "_optimizer_step", original_step)
    monkeypatch.setattr(training, "_summary", original_summary)
    result = training.train_language(output, resume=True)
    actual, _ = training.load_checkpoint(output)
    for key in ("adapter", "optimizer", "rng"):
        assert_tensors_equal(actual[key], expected[key])
    for key in ("sampler", "consumed", "history"):
        assert_tensors_equal(actual["state"][key], expected["state"][key])
    assert result["deadline_unix"] == original_deadline
    assert result["charged_tokens"] == 192 + (0 if point == "after_commit" else 64)
    assert result["committed_tokens"] == 192
    assert sum(item["status"] == "abandoned_before_commit" for item in result["reservations"]) == (
        0 if point == "after_commit" else 1
    )


def test_abandoned_update_spends_tokens_without_advancing_consumed_cursor(
    tmp_path, toy, monkeypatch
):
    output = tmp_path / "run"
    config = {**toy.config, "max_tokens": 64}
    original = training._optimizer_step

    def interrupted(*args):
        original(*args)
        raise KeyboardInterrupt()

    monkeypatch.setattr(training, "_optimizer_step", interrupted)
    with pytest.raises(KeyboardInterrupt):
        training.train_language(output, config)
    monkeypatch.setattr(
        training, "_load_model", lambda _: pytest.fail("No tokens left for GPU work")
    )
    result = training.train_language(output, resume=True)
    assert result["stop_reason"] == "token_limit" and result["updates"] == 0
    assert result["charged_tokens"] == 64 and result["committed_tokens"] == 0
    assert result["consumed_examples"] == 0


def test_resume_cannot_extend_budget_and_completed_resume_loads_no_model(
    tmp_path, toy, monkeypatch
):
    output = tmp_path / "run"
    first = training.train_language(output, toy.config)
    with pytest.raises(ValueError, match="cannot change"):
        training.train_language(output, {**toy.config, "time_budget_seconds": 1000}, resume=True)
    monkeypatch.setattr(training, "_load_model", lambda _: pytest.fail("Already complete"))
    second = training.train_language(output, resume=True)
    assert first["checkpoint"] == second["checkpoint"]
    assert first["artifact"] == second["artifact"]


def test_deadline_after_optimizer_discards_update_and_preserves_original_budget(
    tmp_path, toy, monkeypatch
):
    output = tmp_path / "run"
    original = training._optimizer_step

    def expired(*args):
        original(*args)
        deadline = json.loads((output / "job.json").read_text())["deadline_unix"]
        monkeypatch.setattr(training.time, "time", lambda: deadline + 1)

    monkeypatch.setattr(training, "_optimizer_step", expired)
    result = training.train_language(output, toy.config)
    assert result["stop_reason"] == "deadline" and result["updates"] == 0
    assert result["charged_tokens"] == 64 and result["committed_tokens"] == 0
    assert result["cleanup_overrun_seconds"] >= 1
    monkeypatch.setattr(training, "_load_model", lambda _: pytest.fail("Deadline has expired"))
    second = training.train_language(output, resume=True)
    assert second["deadline_unix"] == result["deadline_unix"]
    assert second["updates"] == 0 and second["pending"] is None


@pytest.mark.parametrize("kind", ["dataset", "source", "checkpoint", "job"])
def test_resume_rejects_changed_frozen_inputs(tmp_path, toy, monkeypatch, kind):
    output = tmp_path / "run"
    training.train_language(output, toy.config)
    if kind == "dataset":
        (toy.dataset / "train.jsonl").write_text("changed")
    elif kind == "source":
        monkeypatch.setattr(training, "_source", lambda: {"revision": "changed"})
    elif kind == "checkpoint":
        pointer = json.loads((output / "checkpoint.json").read_text())
        (output / pointer["path"]).write_bytes(b"corrupted")
    else:
        job = json.loads((output / "job.json").read_text())
        job["config"]["max_updates"] += 1
        (output / "job.json").write_text(json.dumps(job))
    monkeypatch.setattr(training, "_load_model", lambda _: pytest.fail("Frozen input changed"))
    with pytest.raises(ValueError):
        training.train_language(output, resume=True)


def test_same_run_has_nonblocking_exclusive_owner(tmp_path, toy):
    output = tmp_path / "run"
    with (tmp_path / ".run.training.lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="owns this language training run"):
            training.train_language(output, toy.config)
    assert not output.exists()


def test_checkpoint_accounting_rejects_rehashed_duplicate_consumption(tmp_path, toy):
    output = tmp_path / "run"
    training.train_language(output, toy.config)
    payload, _ = training.load_checkpoint(output)
    payload["state"]["consumed"].append(payload["state"]["consumed"][0])
    training._commit(output, payload)
    with pytest.raises(ValueError, match="consumed example accounting"):
        training.load_checkpoint(output)


@pytest.mark.parametrize("change", ["permutation", "invented_id", "epoch", "rng"])
def test_checkpoint_sampler_is_replayed_from_frozen_job(tmp_path, toy, change):
    output = tmp_path / "run"
    training.train_language(output, toy.config)
    payload, _ = training.load_checkpoint(output)
    state = payload["state"]
    if change == "permutation":
        state["sampler"]["order"] = [0, 0, 0]
    elif change == "invented_id":
        state["consumed"][0]["example_id"] = "not-in-frozen-dataset"
        state["reservations"][0]["occurrences"][0]["example_id"] = "not-in-frozen-dataset"
    elif change == "epoch":
        state["sampler"]["epoch"] += 1
    else:
        state["sampler"]["rng"] = random.Random(912).getstate()
    training._commit(output, payload)
    with pytest.raises(ValueError, match="sampler differs|deterministic schedule"):
        training.load_checkpoint(output)


def test_worker_startup_is_inside_frozen_absolute_budget(tmp_path, toy):
    output = tmp_path / "run"
    started = training.time.time() - 12
    result = training.train_language(output, toy.config, started_unix=started)
    assert result["deadline_unix"] == started + toy.config["time_budget_seconds"]
    assert result["elapsed_seconds"] >= 12
    with pytest.raises(ValueError, match="original launch time"):
        training.train_language(output, resume=True, started_unix=training.time.time())


def test_future_launch_time_cannot_extend_budget(tmp_path, toy):
    with pytest.raises(ValueError, match="Invalid launch start"):
        training.train_language(
            tmp_path / "run", toy.config, started_unix=training.time.time() + 30
        )


def test_catalog_suite_origin_is_watched_at_actual_parent_location(tmp_path, run, monkeypatch):
    child = tmp_path / "catalog" / "children" / "attempt-0000"
    shutil.copytree(run, child)
    suites = child.parent.parent / "suites"
    suites.mkdir()
    suite = suites / f"{child.name}.json"
    suite.write_text("{}")
    directory = tmp_path / "dataset"
    export_demonstrations(
        directory,
        [DemonstrationSource(child, "train", "heuristic", "public")],
        purpose="supervised_finetuning",
    )
    _, pins = training.verify_dataset(directory)
    assert str(suite) in pins["origin_files"]
    monkeypatch.setattr(training, "_source", lambda: {})
    job = {
        "source": {},
        "dependencies": training._dependencies(),
        "dataset": pins,
        "config": {"dataset": str(directory)},
    }
    training._verify_frozen(job)
    suite.write_text('{"changed":true}')
    with pytest.raises(ValueError, match="Originating game evidence"):
        training._verify_frozen(job)


def test_pointer_publish_failure_recovers_without_consuming_orphan_update(
    tmp_path, toy, monkeypatch
):
    output = tmp_path / "run"
    original = training._atomic_json

    def fail_pointer(path, value):
        if path.name == "checkpoint.json" and value["updates"] == 1:
            raise OSError("simulated failed atomic pointer publication")
        return original(path, value)

    monkeypatch.setattr(training, "_atomic_json", fail_pointer)
    with pytest.raises(OSError, match="pointer publication"):
        training.train_language(output, toy.config)
    payload, pointer = training.load_checkpoint(output)
    assert pointer["updates"] == 0 and payload["state"]["consumed"] == []
    assert payload["state"]["charged_tokens"] == 64
    assert len(list((output / "checkpoints").glob("*.pt"))) == 3
    monkeypatch.setattr(training, "_atomic_json", original)
    result = training.train_language(output, resume=True)
    assert result["updates"] == 3 and result["charged_tokens"] == 256
    assert result["committed_tokens"] == 192


@pytest.mark.parametrize("tamper", [None, "weights", "provenance"])
def test_real_safetensors_export_roundtrip_and_authoritative_reuse(
    tmp_path, toy, monkeypatch, tamper
):
    safetensors = pytest.importorskip("safetensors.torch")
    monkeypatch.setattr(training, "_export", REAL_EXPORT)
    monkeypatch.setattr(policy, "create_declaration", REAL_DECLARATION)
    monkeypatch.setattr(policy, "validate_declaration", REAL_VALIDATE)
    # Only the tiny fake base inventory is substituted. Use the real shared declaration verifier.
    monkeypatch.setattr(policy, "BASE_FILES", {})
    output = tmp_path / "run"
    result = training.train_language(output, toy.config)
    artifact = Path(result["artifact"]["directory"])
    declaration = json.loads((artifact / "policy.json").read_text())
    REAL_VALIDATE(declaration)
    payload, _ = training.load_checkpoint(output)
    assert (
        training.tensor_hash(safetensors.load_file(artifact / "adapter/adapter_model.safetensors"))
        == payload["state"]["adapter_sha256"]
    )
    assert declaration["provenance"]["adapter_sha256"] == payload["state"]["adapter_sha256"]
    assert Path(declaration["adapter"]["directory"]).parent == artifact
    assert "policy.json" not in declaration["adapter"]["files"]
    if tamper is None:
        again = training.train_language(output, resume=True)
        assert again["artifact"] == result["artifact"]
        return
    if tamper == "weights":
        path = artifact / "adapter/adapter_model.safetensors"
        weights = safetensors.load_file(path)
        safetensors.save_file({name: tensor + 0.1 for name, tensor in weights.items()}, str(path))
        declaration["adapter"]["files"][path.name] = training._sha(path)
    else:
        declaration["provenance"]["updates"] += 1
    (artifact / "policy.json").write_text(json.dumps(declaration))
    record = json.loads((artifact / "export.json").read_text())
    record["files"] = {name: training._sha(artifact / name) for name in record["files"]}
    (artifact / "export.json").write_text(json.dumps(record))
    with pytest.raises(
        ValueError, match="differs from checkpoint|differs from training provenance"
    ):
        training.train_language(output, resume=True)


def load_script():
    spec = importlib.util.spec_from_file_location(
        "train_language_script", Path(__file__).resolve().parents[1] / "scripts/train_language.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_exception_drops_model_references_before_lease_exit(tmp_path, toy, monkeypatch):
    references = []

    def load_model(_):
        model = ToyModel()
        references.append(weakref.ref(model))
        return model, {}

    @contextmanager
    def lease():
        try:
            yield
        finally:
            assert references and references[0]() is None

    def fail_update(model, optimizer, examples, config):
        raise RuntimeError("simulated forward failure retains model in traceback")

    monkeypatch.setattr(training, "_load_model", load_model)
    monkeypatch.setattr(policy, "gpu_lease", lease)
    monkeypatch.setattr(training, "_optimizer_step", fail_update)
    with pytest.raises(RuntimeError, match="simulated forward failure"):
        training.train_language(tmp_path / "run", toy.config)


def test_actual_cpu_peft_resume_preserves_keys_optimizer_and_causal_update(monkeypatch):
    transformers = pytest.importorskip("transformers")
    peft = pytest.importorskip("peft")
    monkeypatch.setattr(training, "_resource_snapshot", lambda _: {"available_mib": 1000})
    torch.set_num_threads(1)

    def create_model():
        torch.manual_seed(32)
        model = transformers.Qwen3ForCausalLM(
            transformers.Qwen3Config(
                vocab_size=32,
                hidden_size=16,
                intermediate_size=32,
                num_hidden_layers=1,
                num_attention_heads=2,
                num_key_value_heads=1,
                head_dim=8,
                max_position_embeddings=64,
            )
        )
        model = peft.get_peft_model(model, peft.LoraConfig(**training.LORA))
        model.config.use_cache = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=0.01)
        return model, optimizer

    model, optimizer = create_model()
    examples = [
        training.tokenize_example(
            {"prompt": "S0", "completion": '{"a":0}', "id": "0"}, Tokenizer(), 32
        )
    ]
    training._optimizer_step(model, optimizer, examples, {})
    saved_adapter, saved_optimizer, saved_rng = (
        training._adapter(model),
        training._cpu(optimizer.state_dict()),
        training._cpu(training._rng()),
    )
    training._optimizer_step(model, optimizer, examples, {})
    expected_adapter, expected_optimizer = (
        training._adapter(model),
        training._cpu(optimizer.state_dict()),
    )
    recovered, recovered_optimizer = create_model()
    training._restore_adapter(recovered, saved_adapter)
    recovered_optimizer.load_state_dict(saved_optimizer)
    training._restore_rng(saved_rng)
    training._optimizer_step(recovered, recovered_optimizer, examples, {})
    assert_tensors_equal(training._adapter(recovered), expected_adapter)
    assert_tensors_equal(recovered_optimizer.state_dict(), expected_optimizer)
    missing = dict(saved_adapter)
    missing.pop(next(iter(missing)))
    with pytest.raises(ValueError, match="Adapter restore differs"):
        training._restore_adapter(recovered, missing)


def test_watchdog_reaps_worker_that_exits_between_poll_and_signal(monkeypatch):
    script = load_script()
    waited = []
    process = SimpleNamespace(
        pid=123, poll=lambda: None, wait=lambda timeout: waited.append(timeout)
    )

    def exited(*args):
        raise ProcessLookupError()

    monkeypatch.setattr(script.os, "killpg", exited)
    script.stop_worker(process)
    assert waited == [5]


def test_watchdog_stops_one_worker_on_resource_failure_without_retry(tmp_path, monkeypatch):
    script = load_script()
    output = tmp_path / "run"
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"time_budget_seconds": 60}))
    process = SimpleNamespace(returncode=None, pid=123, poll=lambda: None)
    calls = []

    def spawn(command, **kwargs):
        output.mkdir()
        calls.append((command, kwargs))
        return process

    def stop(value):
        assert value is process
        process.returncode = -2

    memory = iter([1000, 600])
    monkeypatch.setattr(script, "available_mib", lambda: next(memory))
    monkeypatch.setattr(script, "gpu_used_mib", lambda: 100)
    monkeypatch.setattr(script.subprocess, "Popen", spawn)
    monkeypatch.setattr(script, "stop_worker", stop)
    result = script.supervise(
        SimpleNamespace(output=output, config=config, resume=False, finalize=False)
    )
    assert result == 2 and len(calls) == 1
    assert calls[0][1]["start_new_session"] is True
    assert calls[0][1]["env"]["HF_HUB_OFFLINE"] == "1"
    record = json.loads(next(output.glob("watchdog-*.json")).read_text())
    assert record["stop_reason"] == "low_ram" and record["minimum_available_mib"] == 600


def test_expired_resume_supervisor_finalizes_checkpoint_without_gpu(tmp_path, toy, monkeypatch):
    output = tmp_path / "run"
    original = training.train_language(output, toy.config)
    deadline = original["deadline_unix"]
    script = load_script()
    monkeypatch.setattr(script.time, "time", lambda: deadline + 5)
    monkeypatch.setattr(script, "available_mib", lambda: 1000)
    monkeypatch.setattr(
        script, "gpu_used_mib", lambda: pytest.fail("Finalization does not query GPU")
    )
    monkeypatch.setattr(training, "_load_model", lambda _: pytest.fail("No model on finalization"))
    monkeypatch.setattr(policy, "gpu_lease", lambda: pytest.fail("No GPU lease on finalization"))
    completed = []

    def spawn(command, **kwargs):
        assert "--finalize" in command and "--resume" in command
        completed.append(training.train_language(output, resume=True, finalize_only=True))
        return SimpleNamespace(returncode=0, poll=lambda: 0)

    monkeypatch.setattr(script.subprocess, "Popen", spawn)
    assert (
        script.supervise(SimpleNamespace(output=output, config=None, resume=True, finalize=False))
        == 0
    )
    assert completed[0]["artifact"] == original["artifact"]
    assert completed[0]["deadline_unix"] == deadline
    record = json.loads(next(output.glob("watchdog-*.json")).read_text())
    assert record["finalize_only"] is True and record["deadline_unix"] == deadline
    assert record["supervision_deadline_unix"] == deadline + 5 + script.FINALIZATION_SECONDS
