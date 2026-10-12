"""Frozen local Qwen language policy over the public, ordered legal choices."""

from __future__ import annotations

import copy
import ctypes
import fcntl
import gc
import hashlib
import importlib.metadata
import json
import os
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path

from spire.language.demonstrations import FORMAT_VERSION, parse_completion, render_prompt
from spire.protocol import Decision, IllegalActionError, PolicyFailure

MODEL_ID = "Qwen/Qwen3-0.6B"
REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
PARSER_VERSION = "single-json-choice-v1"
MAX_PROMPT_TOKENS = 2048
DECODER = {
    "enable_thinking": False,
    "max_new_tokens": 12,
    "do_sample": False,
    "num_beams": 1,
    "skip_special_tokens": False,
    "strip_one_terminal_eos": True,
    "eos_token_ids": [151645, 151643],
}
BASE_FILES = {
    "README.md": "1ab64a26fcb3b461423b89a433a8c858f1bf8d4086f979cbb3ff878d47cf20e9",
    "tokenizer.json": "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
    "config.json": "660db3b73d788119c04535e48cf9be5f55bc3100841a718637ae695b442f27dd",
    "LICENSE": "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e",
    "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    "merges.txt": "8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5",
    "tokenizer_config.json": "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101",
    "generation_config.json": "2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2",
    "model.safetensors": "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b",
}
DEPENDENCIES = ("torch", "transformers", "peft", "accelerate", "safetensors")
GPU_LOCK_PATH = Path(f"/tmp/spire-language-gpu-{os.getuid()}.lock")


@contextmanager
def gpu_lease():
    """Nonblocking cross-process ownership for local language GPU work."""
    with GPU_LOCK_PATH.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another local language process owns the GPU lease") from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def file_inventory(directory: Path) -> dict[str, str]:
    if not directory.is_dir():
        raise ValueError(f"Missing language artifact directory: {directory}")
    if any(path.is_dir() for path in directory.iterdir()):
        raise ValueError("Language artifact directories must contain only flat files")
    return {path.name: file_sha256(path) for path in sorted(directory.iterdir()) if path.is_file()}


def create_declaration(
    base_snapshot: Path,
    *,
    adapter_directory: Path | None = None,
    provenance: dict | None = None,
) -> dict:
    """Return a declaration to save outside the optional adapter directory."""
    value = {
        "schema_version": 1,
        "type": "language",
        "base": {
            "id": MODEL_ID,
            "revision": REVISION,
            "directory": str(base_snapshot.resolve()),
            "files": file_inventory(base_snapshot),
        },
        "adapter": None,
        "prompt_format": FORMAT_VERSION,
        "parser_version": PARSER_VERSION,
        "decoder": copy.deepcopy(DECODER),
        "max_prompt_tokens": MAX_PROMPT_TOKENS,
        "provenance": copy.deepcopy(provenance or {}),
    }
    if adapter_directory is not None:
        value["adapter"] = {
            "directory": str(adapter_directory.resolve()),
            "files": file_inventory(adapter_directory),
        }
    validate_declaration(value)
    return value


def validate_declaration(value: dict) -> None:
    expected = {
        "schema_version",
        "type",
        "base",
        "adapter",
        "prompt_format",
        "parser_version",
        "decoder",
        "max_prompt_tokens",
        "provenance",
    }
    if not isinstance(value, dict) or value.keys() != expected:
        raise ValueError("Unknown or missing language declaration fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("Unsupported language declaration schema")
    for key, expected_value in {
        "type": "language",
        "prompt_format": FORMAT_VERSION,
        "parser_version": PARSER_VERSION,
        "decoder": DECODER,
        "max_prompt_tokens": MAX_PROMPT_TOKENS,
    }.items():
        # JSON serialization also distinguishes booleans from integer 0/1.
        if json.dumps(value[key], sort_keys=True) != json.dumps(expected_value, sort_keys=True):
            raise ValueError(f"Unsupported language {key}")
    if not isinstance(value["provenance"], dict):
        raise ValueError("Language provenance must be an object")
    base = value["base"]
    if (
        not isinstance(base, dict)
        or base.keys() != {"id", "revision", "directory", "files"}
        or base["id"] != MODEL_ID
        or base["revision"] != REVISION
        or base["files"] != BASE_FILES
    ):
        raise ValueError("Language base must match the exact pinned Qwen snapshot")
    for label in ("base", "adapter"):
        record = value[label]
        if record is None and label == "adapter":
            continue
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("directory"), str)
            or not Path(record["directory"]).is_absolute()
        ):
            raise ValueError(f"Language {label} requires an absolute local directory")
        if label == "adapter" and record.keys() != {"directory", "files"}:
            raise ValueError("Unknown language adapter fields")
        if file_inventory(Path(record["directory"])) != record["files"]:
            raise ValueError(f"Language {label} files changed or differ from declaration")
    if value["adapter"] is not None:
        adapter = value["adapter"]
        if not {"adapter_config.json", "adapter_model.safetensors"} <= adapter["files"].keys():
            raise ValueError("Language adapter requires PEFT config and safetensors")
        config = json.loads((Path(adapter["directory"]) / "adapter_config.json").read_text())
        if config.get("peft_type") != "LORA" or config.get("task_type") != "CAUSAL_LM":
            raise ValueError("Only causal language LoRA adapters are supported")


def tensor_sha256(model) -> str:
    """Hash exact tensor contents without copying the entire model into host memory."""
    result = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        result.update(json.dumps([name, str(tensor.dtype), list(tensor.shape)]).encode())
        flat = tensor.detach().reshape(-1)
        for chunk in flat.split(1024 * 1024):
            data = chunk.contiguous().cpu()
            result.update(ctypes.string_at(data.data_ptr(), data.numel() * data.element_size()))
    return result.hexdigest()


def decode_completion(tokenizer, token_ids: list[int]) -> tuple[str, str]:
    """Keep all special tokens except one final declared end-of-sequence token."""
    content = token_ids
    if content and content[-1] in DECODER["eos_token_ids"]:
        content = content[:-1]
    return (
        tokenizer.decode(content, skip_special_tokens=False),
        tokenizer.decode(token_ids, skip_special_tokens=False),
    )


def candidate_completions(tokenizer, count: int) -> list[list[int]]:
    """Token IDs of each canonical ``{"a":N}`` completion followed by the training EOS."""
    if type(count) is not int or count < 1:
        raise ValueError("Candidate scoring requires at least one legal choice")
    return [
        tokenizer(json.dumps({"a": index}, separators=(",", ":")), add_special_tokens=False)[
            "input_ids"
        ]
        + [tokenizer.eos_token_id]
        for index in range(count)
    ]


def candidate_log_probs(model, prompt_ids: list[int], completions: list[list[int]]):
    """Return each completion's summed token log-probability after one shared prompt.

    Sequences are right-padded so every completion starts at the same position; only
    the logits that predict completion tokens are materialized. Gradients flow unless
    the caller disables them. Normalizing the result over legal choices gives a policy
    whose sampling and probability calculations use the same masked candidate set.
    """
    import torch

    device = next(model.parameters()).device
    width = max(len(tokens) for tokens in completions)
    rows = [prompt_ids + tokens + [tokens[-1]] * (width - len(tokens)) for tokens in completions]
    mask = [
        [1] * (len(prompt_ids) + len(tokens)) + [0] * (width - len(tokens))
        for tokens in completions
    ]
    output = model(
        input_ids=torch.tensor(rows, device=device),
        attention_mask=torch.tensor(mask, device=device),
        logits_to_keep=width + 1,
    )
    # Kept position j predicts token len(prompt) + j; the last kept position is unused.
    log_probs = torch.log_softmax(output.logits[:, :width].float(), dim=-1)
    targets = torch.tensor(
        [tokens + [0] * (width - len(tokens)) for tokens in completions], device=device
    )
    picked = log_probs.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
    valid = torch.tensor(
        [[1.0] * len(tokens) + [0.0] * (width - len(tokens)) for tokens in completions],
        device=device,
    )
    return (picked * valid).sum(dim=-1)


def _verify_adapter_tensors(restored: dict, saved: dict) -> None:
    """PEFT permits missing keys; require complete, exactly restored adapter values."""
    import torch

    if restored.keys() != saved.keys():
        raise ValueError("Restored language adapter tensor keys differ from safetensors")
    for name, expected in saved.items():
        actual = restored[name].detach().cpu()
        # PEFT's documented inference loader may promote half-precision adapters
        # to float32. This promotion is lossless; all other dtype changes fail.
        promoted = (
            expected.dtype in {torch.float16, torch.bfloat16} and actual.dtype == torch.float32
        )
        if (
            (actual.dtype != expected.dtype and not promoted)
            or actual.shape != expected.shape
            or not torch.equal(actual, expected)
        ):
            raise ValueError(f"Restored language adapter tensor differs: {name}")


def _load_adapter(model, directory: str):
    from peft import PeftModel, get_peft_model_state_dict
    from safetensors.torch import load_file

    saved = load_file(str(Path(directory) / "adapter_model.safetensors"), device="cpu")
    model = PeftModel.from_pretrained(
        model,
        directory,
        is_trainable=False,
        local_files_only=True,
    )
    _verify_adapter_tensors(get_peft_model_state_dict(model), saved)
    return model


def load_local_model(declaration: dict):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError("Language inference requires the llm CUDA environment")
    snapshot = declaration["base"]["directory"]
    tokenizer = AutoTokenizer.from_pretrained(
        snapshot, local_files_only=True, trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        snapshot,
        local_files_only=True,
        dtype=torch.bfloat16,
        device_map={"": "cuda:0"},
        attn_implementation="sdpa",
        trust_remote_code=False,
    )
    if declaration["adapter"] is not None:
        model = _load_adapter(model, declaration["adapter"]["directory"])
    return model, tokenizer


class LanguagePolicy:
    def __init__(self, declaration: dict, *, loader=None):
        self.declaration = copy.deepcopy(declaration)
        validate_declaration(self.declaration)
        self._lease = gpu_lease() if loader is None else nullcontext()
        self._lease.__enter__()
        self.model = None
        try:
            self.model, self.tokenizer = (loader or load_local_model)(self.declaration)
            self.model.eval()
            self.model.requires_grad_(False)
            self.model_sha256 = tensor_sha256(self.model)
            self._last_id = None
            self._last_metadata = None
            self.verify_frozen()
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self._lease is not None:
            import torch

            self.model = None
            self.tokenizer = None
            gc.collect()
            if torch.cuda.is_initialized():
                torch.cuda.empty_cache()
            self._lease.__exit__(None, None, None)
            self._lease = None

    @classmethod
    def from_declaration(cls, path: Path, *, loader=None):
        return cls(json.loads(path.read_bytes()), loader=loader)

    def verify_frozen(self) -> None:
        validate_declaration(self.declaration)
        if self.model.training or any(p.requires_grad for p in self.model.parameters()):
            raise ValueError("Language model is no longer frozen for evaluation")
        if tensor_sha256(self.model) != self.model_sha256:
            raise ValueError("Frozen language model tensors changed")

    def choice_metadata(self, decision_id: str) -> dict:
        if decision_id != self._last_id or self._last_metadata is None:
            raise ValueError("No language completion for this decision")
        return copy.deepcopy(self._last_metadata)

    def encode_decision(self, decision: Decision):
        rendered = render_prompt(decision)
        prompt = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": rendered}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        encoded = self.tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
        return rendered, prompt, encoded

    def candidate_log_probs(self, decision: Decision) -> list[float]:
        """Normalized log-probabilities over the decision's legal choices, without sampling."""
        import torch

        _, _, encoded = self.encode_decision(decision)
        prompt = encoded["input_ids"][0].tolist()
        if len(prompt) > MAX_PROMPT_TOKENS:
            raise ValueError("Language prompt exceeds 2048 tokens")
        completions = candidate_completions(self.tokenizer, len(decision.candidates))
        with torch.inference_mode():
            scores = candidate_log_probs(self.model, prompt, completions)
        return torch.log_softmax(scores, dim=0).tolist()

    def choose(self, decision: Decision):
        import torch

        if self.model.training or any(p.requires_grad for p in self.model.parameters()):
            raise ValueError("Language model is no longer frozen for evaluation")
        started = time.monotonic()
        rendered, prompt, encoded = self.encode_decision(decision)
        tokens = encoded["input_ids"].shape[1]
        metadata = {
            "type": "language",
            "prompt_format": FORMAT_VERSION,
            "parser_version": PARSER_VERSION,
            "prompt_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
            "chat_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_tokens": tokens,
            "completion_tokens": 0,
            "max_prompt_tokens": MAX_PROMPT_TOKENS,
            "completion_token_ids": [],
            "raw_completion": None,
            "completion": None,
            "inference_seconds": time.monotonic() - started,
        }
        self._last_id, self._last_metadata = decision.id, metadata

        def failure(kind, message):
            fields = {
                key: metadata[key]
                for key in (
                    "prompt_sha256",
                    "prompt_tokens",
                    "max_prompt_tokens",
                    "completion_tokens",
                    "raw_completion",
                    "completion",
                    "inference_seconds",
                    "completion_token_ids",
                )
            }
            fields.update(kind=kind)
            return PolicyFailure(message, failure=fields)

        if tokens > MAX_PROMPT_TOKENS:
            raise failure("context_limit", "Language prompt exceeds 2048 tokens")
        device = next(self.model.parameters()).device
        inputs = {
            key: value.to(device)
            for key, value in encoded.items()
            if key in ("input_ids", "attention_mask")
        }
        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=12,
                do_sample=False,
                num_beams=1,
                num_return_sequences=1,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=DECODER["eos_token_ids"],
            )
        completion = generated[0, tokens:]
        text, raw = decode_completion(self.tokenizer, completion.tolist())
        metadata.update(
            completion_tokens=completion.numel(),
            completion_token_ids=completion.tolist(),
            completion=text,
            raw_completion=raw,
            inference_seconds=time.monotonic() - started,
        )
        try:
            action = parse_completion(decision, metadata["completion"])
        except IllegalActionError as error:
            raise failure("invalid_completion", str(error)) from error
        metadata["selected_index"] = decision.candidates.index(action)
        return action


def dependency_versions() -> dict[str, str]:
    return {name: importlib.metadata.version(name) for name in DEPENDENCIES}
