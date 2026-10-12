"""Stages C and D: GRPO on game outcomes, with an optional ECHO dynamics term.

Each step draws tasks from the current curriculum stage, plays a group of attempts per
task, scores them with ``rewards`` and turns each attempt's sampled tokens into training
data weighted by its group-relative advantage. With ``echo_alpha > 0``, each decision's
dynamics target joins as tokens with constant advantage alpha for the first
``echo_steps`` steps (stage D's third arm; ECHO's authors suggest it only early on). A
group whose rewards are all equal teaches nothing and is skipped.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from pathlib import Path

from spire.openweight.rollout import Episode
from spire.openweight.tasks import Stage, Task


@dataclass(frozen=True)
class GRPOConfig:
    model: str
    stage: Stage
    steps: int
    tasks_per_step: int = 8
    group_size: int = 8
    learning_rate: float = 1e-5
    lora_rank: int = 32
    echo_alpha: float = 0.0
    echo_steps: int = 0


def group_advantages(rewards: list[float]) -> list[float]:
    """Reward minus the group mean, over the group's deviation; zeros if all are equal."""
    mean = statistics.fmean(rewards)
    deviation = statistics.pstdev(rewards)
    if deviation == 0:
        return [0.0] * len(rewards)
    return [(reward - mean) / deviation for reward in rewards]


def training_data(episode: Episode, advantage: float, *, echo_alpha: float) -> list[dict]:
    """One sequence per decision: sampled tokens weighted by the episode's advantage, then,
    if echo_alpha > 0, the rendered dynamics target weighted by echo_alpha."""
    raise NotImplementedError


def train(output: Path, config: GRPOConfig, tasks: list[Task]) -> dict:
    """A budgeted, resumable job in runs/openweight/<job>, like spire.ppo.training."""
    raise NotImplementedError
