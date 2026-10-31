"""Shared synthetic fixtures; pattern: huggingface/datasets tests/utils.py."""

import copy
import importlib.util
import random
from contextlib import nullcontext
from types import SimpleNamespace

import demonstration_support as demo_fixtures
import pytest
import torch

from gameai.provenance import REPO_ROOT  # noqa: E402
from spire.language import policy, training  # noqa: E402

functional = torch.nn.functional

REAL_EXPORT = training._export
REAL_DECLARATION = policy.create_declaration
REAL_VALIDATE = policy.validate_declaration
evidence_run = demo_fixtures.evidence_run
run = demo_fixtures.run


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


def load_script():
    spec = importlib.util.spec_from_file_location(
        "train_language_script", REPO_ROOT / "scripts/train_language.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
