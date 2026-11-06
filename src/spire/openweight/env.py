"""One step interface over the engines a policy is trained or judged on.

Tinker's cookbook and Verifiers both drive environments step by step, so this is what
they would wrap. Every backend hands out the public full-run ``Decision`` built by
``spire.decisions``, never engine state.

- ``RealGame``: the original game through CommunicationMod, one controller at a time and
  about 38 s per combat. ``spire.fullrun.play.play_run`` calls its policy; this backend
  inverts that loop with a worker thread and keeps the same trace.
- ``Simulator``: sts_lightspeed, the candidate for fast training. Its search reads the
  game's RNG and it loads saves only into combat, so it needs an audited adapter and
  parity checks against ``RealGame`` before any of its results count.
"""

from __future__ import annotations

import json
import queue
import sys
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from gameai.provenance import committed_revision, source_fingerprints, write_json
from spire.decisions import Choice
from spire.engine.bridge import BridgeError
from spire.openweight.tasks import Stage, Task
from spire.protocol import Decision

OUTCOMES = ("won", "lost", "truncated")
SUMMARY = ("act", "floor", "current_hp", "max_hp", "gold")


@dataclass(frozen=True)
class Step:
    decision: Decision | None  # the next decision; None once the episode has ended
    outcome: str | None = None  # engine-confirmed "won" or "lost" (of the fight, for fights)
    summary: dict = field(default_factory=dict)  # act, floor, HP, ... for rewards


class Environment(Protocol):
    def reset(self, task: Task) -> Decision: ...

    def step(self, choice: Choice) -> Step: ...

    def close(self) -> None: ...


class EpisodeFailed(RuntimeError):
    """The game or its bridge failed; never a gameplay outcome, so it never scores."""


class _Handover:
    """The policy ``play_run`` calls: hands each decision out and waits for the choice."""

    def __init__(self) -> None:
        self.decisions: queue.Queue[Decision | None] = queue.Queue()
        self.choices: queue.Queue[Choice | None] = queue.Queue()

    def choose(self, decision: Decision) -> Choice:
        self.decisions.put(decision)
        choice = self.choices.get()
        if choice is None:  # Ending a run early is not the policy's failure.
            raise BridgeError("Environment closed")
        return choice

    def choice_metadata(self, decision_id: str) -> dict:
        return {"type": "environment"}


class RealGame:
    """The original engine: the reference for parity and for final evaluation.

    ``play_run`` keeps its loop, trace and failure handling; a worker thread runs it, and
    ``reset`` and ``step`` trade decisions with it. This adds no speed: an episode still
    pays a fresh game launch. Forced single-choice decisions stay inside ``play_run``, as
    they do for every policy. One complete run per episode: a mid-run start needs the
    restore work in docs/spire/state-restore.md, so a task with ``start`` is refused.
    """

    def __init__(self, directory: Path, *, run_timeout: float = 3600.0,
                 bridge_timeout: float = 300.0, max_actions: int = 4000) -> None:
        self.directory = directory
        self.limits = {"run_timeout": run_timeout, "bridge_timeout": bridge_timeout,
                       "max_actions": max_actions}
        self._handover: _Handover | None = None
        self._worker: threading.Thread | None = None
        self._result: dict | None = None
        self._failure: BaseException | None = None
        self._episodes = 0
        self._live = False

    def _record_job(self) -> None:
        """Keep what `play` keeps, and refuse uncommitted or changed source as it does."""
        from spire.fullrun.play import SOURCES

        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / "manifest.json"
        source = source_fingerprints(SOURCES)
        if path.exists():
            if json.loads(path.read_text())["source_files"] != source:
                raise EpisodeFailed("Source changed since this environment's job began")
            return
        write_json(path, {
            "schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
            "source_revision": committed_revision("attributable runs", SOURCES),
            "source_files": source, "command": [sys.executable, *sys.argv],
            "config": self.limits, "engine": "original", "scope": "environment",
        })

    def _next_run(self, task: Task) -> Path:
        """A fresh directory, past any earlier environment's runs in this job."""
        while True:
            run = self.directory / f"{task.id}-{self._episodes:04d}"
            self._episodes += 1
            if not run.exists():
                return run

    def _play(self, run: Path, config: dict) -> None:
        from spire.fullrun.play import play_run

        try:
            self._result = play_run(run, config, self._handover)
        except BaseException as error:  # noqa: BLE001 - reported to the caller by ``_next``.
            self._failure = error
        finally:
            self._handover.decisions.put(None)

    def _next(self) -> Step:
        decision = self._handover.decisions.get()
        if decision is not None:
            game = decision.observation
            return Step(decision, summary={key: game.get(key) for key in SUMMARY})
        self._live = False
        self._worker.join()
        if self._failure is not None:
            raise EpisodeFailed(str(self._failure)) from self._failure
        status = self._result.get("status")
        if status not in OUTCOMES:
            raise EpisodeFailed(f"{status}: {self._result.get('error')}")
        return Step(None, status, {key: self._result.get(key) for key in SUMMARY})

    def reset(self, task: Task) -> Decision:
        if task.start is not None:
            raise ValueError("A mid-run start needs restore, which has never run live")
        if task.stage is not Stage.FULL_RUN:
            raise ValueError(f"RealGame plays complete runs, not stage {task.stage}")
        self.close()
        self._record_job()
        run = self._next_run(task)
        self._handover, self._result, self._failure = _Handover(), None, None
        config = {**self.limits, "seed": task.game_seed}
        self._worker = threading.Thread(target=self._play, args=(run, config), daemon=True)
        self._live = True
        self._worker.start()
        step = self._next()
        if step.decision is None:
            raise EpisodeFailed("The run ended before its first decision")
        return step.decision

    def step(self, choice: Choice) -> Step:
        if not self._live:
            raise RuntimeError("step called with no live episode")
        self._handover.choices.put(choice)
        return self._next()

    def close(self) -> None:
        """End any unfinished run; ``play_run`` then closes its game."""
        if self._worker is not None and self._worker.is_alive():
            self._handover.choices.put(None)
            self._worker.join()
        self._worker, self._live = None, False


class Simulator:
    """sts_lightspeed; nothing it produces counts until parity with RealGame is audited."""

    def reset(self, task: Task) -> Decision:
        raise NotImplementedError

    def step(self, choice: Choice) -> Step:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
