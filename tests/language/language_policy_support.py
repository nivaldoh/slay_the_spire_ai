"""Shared synthetic fixtures; pattern: huggingface/datasets tests/utils.py."""

import json
from pathlib import Path

import pytest
import torch

from spire.language import policy as language  # noqa: E402


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.tensor([1.0, 2.0]))
        self.register_buffer("buffer", torch.tensor([3.0]))
        self.calls = []

    def generate(self, **kwargs):
        assert not self.training and not torch.is_grad_enabled()
        self.calls.append(kwargs)
        return torch.cat([kwargs["input_ids"], torch.tensor([[len(self.calls), 4, 151645]])], dim=1)


class TinyTokenizer:
    eos_token_id = 151645

    def __init__(self, response='{"a": 0}', tokens=13):
        self.response = response
        self.tokens = tokens
        self.messages = []
        self.responses = {}

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs == {
            "tokenize": False,
            "add_generation_prompt": True,
            "enable_thinking": False,
        }
        self.messages = messages
        return "<user>" + messages[0]["content"] + "<assistant><think></think>"

    def __call__(self, prompt, **kwargs):
        assert kwargs == {"add_special_tokens": False, "return_tensors": "pt"}
        return {
            "input_ids": torch.ones((1, self.tokens), dtype=torch.long),
            "attention_mask": torch.ones((1, self.tokens), dtype=torch.long),
        }

    def decode(self, tokens, *, skip_special_tokens):
        assert skip_special_tokens is False
        eos = bool(tokens and tokens[-1] == self.eos_token_id)
        key = tuple(tokens[:-1] if eos else tokens)
        return self.responses.setdefault(key, self.response) + ("<eos>" if eos else "")


@pytest.fixture
def declaration(tmp_path, monkeypatch):
    snapshot = tmp_path / "base"
    snapshot.mkdir()
    for name in language.BASE_FILES:
        (snapshot / name).write_text(name)
    monkeypatch.setattr(language, "BASE_FILES", language.file_inventory(snapshot))
    return language.create_declaration(snapshot)


@pytest.fixture
def adapter_declaration(tmp_path, declaration):
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text(
        json.dumps({"peft_type": "LORA", "task_type": "CAUSAL_LM"})
    )
    (adapter / "adapter_model.safetensors").write_bytes(b"test adapter")
    return language.create_declaration(
        Path(declaration["base"]["directory"]),
        adapter_directory=adapter,
        provenance={"synthetic": True, "updates": 1},
    )
