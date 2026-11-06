"""Play complete runs on the real game, one JVM across many runs, and keep steps for the learner.

``fullrun.play`` starts a fresh JVM per run so that traces stay byte-identical. Training wants
something else: every new Windows process from WSL needs a 512 KB contiguous kernel block for
its socket (dmesg, ``page allocation failure: order:7`` in ``hvs_probe``), which fails under
memory pressure and stalls launches for minutes. So one JVM plays many runs, returning to the
main menu after each death, as spirecomm's own loop does. The run loop is ``fullrun.play``'s.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from contextlib import ExitStack
from pathlib import Path

from gameai.provenance import REPO_ROOT, sha256, write_json
from spire.engine.bridge import BridgeError, BridgeServer
from spire.engine.doctor import collect_profile
from spire.engine.runtime import (
    BRIDGE_PORT,
    GAME_DIR,
    OwnedGame,
    RuntimeLock,
    prepare_runtime,
    wsl_bridge_host,
)
from spire.fullrun.play import SaveSnapshots, _drive, _save_path, _summary
from spire.localrl.link import SPEED_GAP_SECONDS, Link
from spire.localrl.policy import LocalPolicy, Scorer
from spire.protocol import ProtocolError

SCORED = {"won", "lost", "truncated"}
# JUDGEMENT: Run limits — Claude, 2026-11-06, owner away: 1,500 actions or 45 minutes, then the
# run counts as truncated at its floor. A weak policy dies long before; a stronger one needs more.
RUN = {"run_timeout": 2700, "bridge_timeout": 90, "max_actions": 1500}
# JUDGEMENT: Launch retries — Claude, 2026-11-06, owner away: about 30 minutes of retries, not
# docs/autonomy.md's two failed launches, because one stall took 8 minutes. Fewer ends the night.
MAX_FAILURES = 40
RETRY_SECONDS = 30
# The game rewrites preference files by deleting them first, and a JVM killed at the death
# screen lost the owner's STSUnlockProgress (2026-11-06). Wait this long before any close.
SETTLE_SECONDS = 5
JVM_SECONDS = 14 * 3600
FAILURES = (BridgeError, ProtocolError, RuntimeError, OSError, subprocess.SubprocessError)
SEED_ATTEMPTS = 3
# ModTheSpire's log window keeps all log text on the 1 GB heap: OutOfMemoryError from run 77 of
# one JVM in round 2 (runs/spire-rl-20261106b/handoff.md), and the command reader died of it.
MAX_RUNS_PER_JVM = 60


def revision() -> dict:
    def git(*arguments):
        return subprocess.check_output(["git", *arguments], cwd=REPO_ROOT, text=True).strip()
    return {"commit": git("rev-parse", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--", "src/spire/localrl"))}


def forget_step(policy, command: str, forced: bool, error: str | None) -> None:
    """A decision that reached no game state is no step for the learner."""
    if forced or command.startswith(("START", "wait", "key", "state")):
        return
    steps = getattr(policy, "steps", [])
    if steps:
        step = steps.pop()
        if error is None:  # never tried on the game, so the state may offer it again
            key = hashlib.sha256(step["prompt"].encode()).hexdigest()
            policy.tried[key].discard(step["index"])


def one_run(directory: Path, seed: str, policy: LocalPolicy, link: Link) -> dict:
    """``fullrun.play.play_run`` without the launch."""
    directory.mkdir(exist_ok=False)
    started = time.monotonic()
    session_id = uuid.uuid4().hex
    result = {"seed": seed, "session_id": session_id, "status": "interrupted", "actions": 0,
              "decisions": 0, "policy_calls": 0, "settle_waits": 0, **_summary({})}
    profile = collect_profile(GAME_DIR)
    write_json(directory / "profile.json", profile)
    with (directory / "trace.jsonl").open("x", buffering=1) as trace:

        latest = {"forced": False}

        def event(kind: str, **fields) -> None:
            if kind == "decision":
                latest["forced"] = fields["behavior"].get("type") == "forced"
            record = {"kind": kind, "elapsed": time.monotonic() - started, **fields}
            trace.write(json.dumps(record, sort_keys=True) + "\n")

        saves = SaveSnapshots(_save_path(profile), directory / "saves", event)

        def dropped(command: str, error: str | None) -> None:
            event("dropped", command=command, error=error)
            forget_step(policy, command, latest["forced"], error)

        link.dropped = dropped
        link.superseded = lambda message: event("superseded", raw=message)
        try:
            _drive(link, policy, {**RUN, "seed": seed}, session_id,
                   started + RUN["run_timeout"], result, event, saves)
        finally:
            link.dropped = link.superseded = None
            result.update(elapsed_seconds=time.monotonic() - started)
            write_json(directory / "result.json", result)
    return result


def _keep(result: dict, directory: Path, label: str, temperature: float, policy) -> dict:
    keep = {key: result.get(key) for key in (
        "seed", "status", "act", "floor", "current_hp", "max_hp", "decisions", "actions",
        "elapsed_seconds", "score", "deck_size")}
    keep.update(label=label, temperature=temperature, directory=str(directory))
    with (directory / "steps.jsonl").open("w") as file:
        for step in policy.steps:
            file.write(json.dumps(step) + "\n")
    return keep


class Game:
    """One JVM kept open across runs and across cycles; a failure reopens it.

    Open it before loading the model: a launch needs that free block of kernel memory.
    """

    def __init__(self, directory: Path, speed: tuple[float, int] | None = None):
        """``speed`` is (game seconds per frame, frames a second) and needs SPIRE_SPEED_JAR,
        built by ``speedmod/build.sh``.

        JUDGEMENT: Training speed mod — Claude, 2026-11-06: fixed frame step and no display cap,
        so animations end sooner. Only useful if a run's decisions and outcomes stay the same;
        floors at a speed count only where `runs/spire-rl-20261106b/speed-check` shows that.
        """
        self.directory, self.count, self.stack, self.link = directory, 0, None, None
        self.speed, self.runs = speed, 0
        directory.mkdir(parents=True, exist_ok=True)

    def _try_open(self) -> None:
        self.runs = 0
        self.count += 1
        directory = self.directory / f"jvm-{self.count:03d}"
        while directory.exists():
            self.count += 1
            directory = self.directory / f"jvm-{self.count:03d}"
        directory.mkdir()
        self.stack = ExitStack()
        self.stack.enter_context(RuntimeLock())
        bridge = self.stack.enter_context(BridgeServer(
            host=wsl_bridge_host(), port=BRIDGE_PORT, timeout=RUN["bridge_timeout"]))
        deployment = prepare_runtime(*bridge.address, timeout=RUN["bridge_timeout"])
        deployment["speed"] = self.speed
        if self.speed:
            jar = Path(os.environ["SPIRE_SPEED_JAR"])
            shutil.copy2(jar, GAME_DIR / "mods" / "spirespeed.jar")
            deployment["speed_jar"] = sha256(jar)
        write_json(directory / "deployment.json", deployment)
        self.stack.enter_context(OwnedGame(directory / "game.log", timeout=JVM_SECONDS,
                                           speed=self.speed))
        self.link = Link(bridge, SPEED_GAP_SECONDS if self.speed else 0)

    def open(self) -> None:
        for attempt in range(1, MAX_FAILURES + 1):
            try:
                return self._try_open()
            except FAILURES as error:
                self.close()
                print(f"launch {attempt} failed: {type(error).__name__}: {error}"[:200], flush=True)
                if attempt == MAX_FAILURES:
                    raise
                time.sleep(RETRY_SECONDS)

    def close(self) -> None:
        if self.link is not None:  # at the menu or, if that failed, at the death screen
            time.sleep(SETTLE_SECONDS)
        stack, self.stack, self.link = self.stack, None, None
        if stack is not None:
            try:
                stack.close()
            except FAILURES as error:
                print(f"closing the game: {type(error).__name__}: {error}"[:200], flush=True)

    def restart(self) -> None:
        self.close()
        self.open()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *arguments):
        self.close()


def play_seeds(game: Game, output: Path, seeds: list[str], scorer: Scorer | None, *,
               temperature: float, label: str, seed_offset: int = 0,
               prompt: int = 1) -> list[dict]:
    """Play each seed once, in order. A lost link is not an outcome: the seed is played again
    in a new JVM, with a different sampling seed in case the state itself caused the failure."""
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "job.json", {"label": label, "seeds": seeds, "temperature": temperature,
                                     "adapter": scorer.fingerprint() if scorer else None,
                                     "speed": game.speed, "prompt": prompt,
                                     "revision": revision(),
                                     "started": time.time()})
    results = []
    for index, seed in enumerate(seeds):
        for attempt in range(SEED_ATTEMPTS):
            policy = LocalPolicy(scorer, temperature=temperature, prompt=prompt,
                                 seed=seed_offset + index + 1000 * attempt)
            run = output / f"run-{index:04d}-{attempt}"
            try:
                result = one_run(run, seed, policy, game.link)
            except Exception as error:  # the run did not finish, so it is not an outcome
                note = f"{type(error).__name__}: {error}"[:200]
                print(json.dumps({"seed": seed, "status": "infrastructure", "error": note}),
                      flush=True)
                game.restart()
                continue
            keep = _keep(result, run, label, temperature, policy)
            break
        else:
            raise RuntimeError(f"Seed {seed} failed {SEED_ATTEMPTS} times")
        with (output / "results.jsonl").open("a") as file:
            file.write(json.dumps(keep) + "\n")
        print(json.dumps({k: keep.get(k) for k in ("seed", "status", "floor", "decisions",
                                                   "elapsed_seconds")}), flush=True)
        results.append(keep)
        # The run is on record from here: leaving the screen can cost a JVM, never the seed.
        try:
            if result["status"] == "truncated":
                game.restart()  # still in a run, so only a new JVM leaves it
            else:
                game.link.to_menu()
                game.runs += 1
                if game.runs >= MAX_RUNS_PER_JVM:
                    game.restart()
        except FAILURES as error:
            print(f"leaving the run: {type(error).__name__}: {error}"[:200], flush=True)
            game.restart()
    return results
