"""Training tasks: curriculum stages, game seeds and their splits.

A task is one episode's start. Training, validation and final-test seeds stay apart from
the start, including combat snapshots taken from those seeds. Declarations will live in
``configs/openweight/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Stage(StrEnum):
    """Curriculum order; each stage starts once the previous one shows a measured gain."""

    FIGHT = "fight"  # single fights from fixed starts
    ACT1_ENCOUNTERS = "act1_encounters"  # varied Act 1 hallway, elite and boss fights
    ACT1 = "act1"  # Neow through the Act 1 boss
    FULL_RUN = "full_run"


class Split(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


@dataclass(frozen=True)
class Task:
    id: str
    stage: Stage
    split: Split
    game_seed: str
    # Where the episode starts if not at the run's first decision: a combat snapshot
    # (simulator) or a recorded prefix of choices to replay (real game).
    start: str | None = None


def check_splits(tasks: list[Task]) -> None:
    """A game seed belongs to one split, whatever stage or start uses it."""
    owner: dict[str, Split] = {}
    for task in tasks:
        split = owner.setdefault(task.game_seed, task.split)
        if split != task.split:
            raise ValueError(f"Seed {task.game_seed} is in both {split} and {task.split}")


def load_tasks(path: Path) -> list[Task]:
    """Read a task declaration. Not designed yet; first-combat catalogs are one model."""
    raise NotImplementedError
