"""Stages B and E: every arm on the same tasks, reported with uncertainty.

Arms: a scripted heuristic, the untouched models, game-reward RL, and RL plus dynamics
prediction. Each reports its win rate with a Wilson interval, invalid replies, tokens and
cost; floors and HP are diagnostics. Held-out claims use only validation or test tasks,
and the real game confirms any simulator result.
"""

from __future__ import annotations

import math
from pathlib import Path

from spire.openweight.rollout import Episode
from spire.openweight.tasks import Task


def wilson_interval(wins: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0 or not 0 <= wins <= total:
        raise ValueError("Need 0 <= wins <= total and total > 0")
    rate = wins / total
    center = (rate + z * z / (2 * total)) / (1 + z * z / total)
    margin = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total))
    margin /= 1 + z * z / total
    return max(0.0, center - margin), min(1.0, center + margin)


def summarize(episodes: list[Episode]) -> dict:
    raise NotImplementedError


def evaluate(output: Path, arm: str, tasks: list[Task]) -> dict:
    raise NotImplementedError
