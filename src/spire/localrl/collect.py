"""Play complete runs on the real game, one JVM across many runs, and keep steps for the learner.

``fullrun.play`` starts a fresh JVM per run so that traces stay byte-identical. Training wants
something else: every new Windows process from WSL needs a 512 KB contiguous kernel block for
its socket (dmesg, ``page allocation failure: order:7`` in ``hvs_probe``), which fails under
memory pressure and stalls launches for minutes. So one JVM plays many runs, returning to the
main menu after each death, as spirecomm's own loop does. The run loop is ``fullrun.play``'s.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from contextlib import ExitStack
from pathlib import Path

from gameai.provenance import REPO_ROOT, write_json
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
from spire.localrl.policy import LocalPolicy, Scorer
from spire.protocol import BridgeCommandError, ProtocolError

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
MENU_SECONDS = 60
FAILURES = (BridgeError, ProtocolError, RuntimeError, OSError, subprocess.SubprocessError)
SEED_ATTEMPTS = 3


def revision() -> dict:
    def git(*arguments):
        return subprocess.check_output(["git", *arguments], cwd=REPO_ROOT, text=True).strip()
    return {"commit": git("rev-parse", "HEAD"),
            "dirty": bool(git("status", "--porcelain", "--", "src/spire/localrl"))}


class Link:
    """The bridge, with the main-menu state put back for the next run to read first."""

    def __init__(self, bridge):
        self.bridge, self.waiting = bridge, None

    def receive(self) -> dict:
        message, self.waiting = self.waiting, None
        return message or self.bridge.receive()

    def send(self, command: str) -> None:
        self.bridge.send(command)

    def to_menu(self) -> None:
        """From the death or victory screen back to the main menu."""
        deadline = time.monotonic() + MENU_SECONDS
        self.bridge.send("proceed")
        while time.monotonic() < deadline:
            message = self.bridge.receive()
            if "error" in message:
                raise BridgeCommandError(message["error"])
            if not message.get("ready_for_command"):
                continue
            if not message.get("in_game"):
                self.waiting = message
                return
            if "proceed" not in message.get("available_commands", ()):
                raise ProtocolError(f"Cannot leave {message.get('available_commands')}")
            self.bridge.send("proceed")
        raise ProtocolError("The main menu did not return")


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

        def event(kind: str, **fields) -> None:
            record = {"kind": kind, "elapsed": time.monotonic() - started, **fields}
            trace.write(json.dumps(record, sort_keys=True) + "\n")

        saves = SaveSnapshots(_save_path(profile), directory / "saves", event)
        try:
            _drive(link, policy, {**RUN, "seed": seed}, session_id,
                   started + RUN["run_timeout"], result, event, saves)
        finally:
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

    def __init__(self, directory: Path):
        self.directory, self.count, self.stack, self.link = directory, 0, None, None
        directory.mkdir(parents=True, exist_ok=True)

    def _try_open(self) -> None:
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
        write_json(directory / "deployment.json",
                   prepare_runtime(*bridge.address, timeout=RUN["bridge_timeout"]))
        self.stack.enter_context(OwnedGame(directory / "game.log", timeout=JVM_SECONDS))
        self.link = Link(bridge)

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
               temperature: float, label: str, seed_offset: int = 0) -> list[dict]:
    """Play each seed once, in order. A lost link is not an outcome: the seed is played again
    in a new JVM, with a different sampling seed in case the state itself caused the failure."""
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "job.json", {"label": label, "seeds": seeds, "temperature": temperature,
                                     "revision": revision(), "started": time.time()})
    results = []
    for index, seed in enumerate(seeds):
        for attempt in range(SEED_ATTEMPTS):
            policy = LocalPolicy(scorer, temperature=temperature,
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
        except FAILURES as error:
            print(f"leaving the run: {type(error).__name__}: {error}"[:200], flush=True)
            game.restart()
    return results
