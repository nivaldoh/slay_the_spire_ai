"""Tinker transport, prices and spend: infrastructure, like ``spire.fullrun.api``.

Tinker trains LoRA adapters remotely and samples from them; the game, any simulator and the
orchestration stay on this machine. The SDK is not a dependency yet. When the pilot starts,
add it as its own extra with a pinned version, and pin ``verifiers`` too if its recipe is
used, since its main branch removed the v0 API.
"""

from __future__ import annotations

from dataclasses import dataclass

from spire.fullrun.api import Ledger
from spire.provenance import REPO_ROOT

# USD per million tokens (prefill, sample, train), from the Tinker catalog on 2026-10-12.
# Keys are display names; confirm the catalog IDs in models.json before the first call.
PRICES = {
    "Qwen3.6-35B-A3B": (0.45, 1.335, 1.177),
    "GLM-5.3": (3.78, 12.15, 14.58),
    "GLM-5.3-Flash": (0.84, 2.11, 5.58),
    "Qwen3.8-27B": (0.6975, 5.595, 4.103),
}
# Apart from the OpenAI ledger, so neither track's cap absorbs the other's spend.
LEDGER_PATH = REPO_ROOT / "runs/tinker-spend.jsonl"


@dataclass(frozen=True)
class Sample:
    prompt_tokens: tuple[int, ...]
    tokens: tuple[int, ...]
    logprobs: tuple[float, ...]  # behavior log-probabilities, for the GRPO update
    text: str


class TinkerSession:
    """One base model and one LoRA adapter: samples from its current weights, and updates.

    Every call is priced and charged to the ledger, and refused if it could exceed the cap.
    """

    def __init__(self, model: str, ledger: Ledger, *, lora_rank: int = 32):
        if model not in PRICES:
            raise ValueError(f"No declared price for model {model}")
        self.model, self.ledger, self.lora_rank = model, ledger, lora_rank

    def sample(self, prompt: str, count: int, *, temperature: float = 1.0) -> list[Sample]:
        raise NotImplementedError

    def train_step(self, data: list[dict], *, learning_rate: float) -> dict:
        raise NotImplementedError

    def save(self, name: str) -> str:
        """Save the adapter; returns the remote path to record in the job's manifest."""
        raise NotImplementedError
