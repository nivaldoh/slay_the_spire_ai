"""Candidate scoring helpers for local language models (WH3 checkpoint RL).

Copied unchanged from spire.language (policy, sampling, training). Spire keeps its own
copies: scripts/audit_language_training.py requires those files byte-identical to the
sources recorded with each training job. Torch is imported lazily, so game phases that
import this module never initialise CUDA.
"""

from __future__ import annotations

import ctypes
import fcntl
import hashlib
import json
import math
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def gpu_lease(path: Path):
    """Nonblocking cross-process ownership for local language GPU work."""
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another local language process owns the GPU lease") from error
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


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


def normalized(scores: list[float], temperature: float) -> list[float]:
    scaled = [score / temperature for score in scores]
    peak = max(scaled)
    log_total = peak + math.log(sum(math.exp(value - peak) for value in scaled))
    return [value - log_total for value in scaled]


def _json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def tensor_hash(tensors: dict) -> str:
    result = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        result.update(_json([name, str(tensor.dtype), list(tensor.shape)]))
        buffer = tensor.detach().cpu().contiguous()
        result.update(ctypes.string_at(buffer.data_ptr(), buffer.numel() * buffer.element_size()))
    return result.hexdigest()


def verify_adapter_tensors(restored: dict, saved: dict) -> None:
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
