"""One step interface over the engines a policy is trained or judged on.

Tinker's cookbook and Verifiers both drive environments step by step, so this is what
they would wrap. Every backend hands out the public full-run ``Decision`` built by
``spire.fullrun.decisions``, never engine state.

- ``RealGame``: the original game through CommunicationMod, one controller at a time and
  about 38 s per combat. ``spire.fullrun.play.play_run`` calls its policy; this backend
  must invert that loop (a worker thread or a generator) and keep the same trace.
- ``Simulator``: sts_lightspeed, the candidate for fast training. Its search reads the
  game's RNG and it loads saves only into combat, so it needs an audited adapter and
  parity checks against ``RealGame`` before any of its results count.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from spire.fullrun.decisions import Choice
from spire.openweight.tasks import Task
from spire.protocol import Decision


@dataclass(frozen=True)
class Step:
    decision: Decision | None  # the next decision; None once the episode has ended
    outcome: str | None = None  # engine-confirmed "won" or "lost" (of the fight, for fights)
    summary: dict = field(default_factory=dict)  # act, floor, HP, ... for rewards


class Environment(Protocol):
    def reset(self, task: Task) -> Decision: ...

    def step(self, choice: Choice) -> Step: ...

    def close(self) -> None: ...


class RealGame:
    """The original engine: the reference for parity and for final evaluation."""

    def reset(self, task: Task) -> Decision:
        raise NotImplementedError

    def step(self, choice: Choice) -> Step:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class Simulator:
    """sts_lightspeed; nothing it produces counts until parity with RealGame is audited."""

    def reset(self, task: Task) -> Decision:
        raise NotImplementedError

    def step(self, choice: Choice) -> Step:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
