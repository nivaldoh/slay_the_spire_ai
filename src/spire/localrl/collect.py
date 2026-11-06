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
# Generous for a weak policy: it dies early, and a loop ends at the action limit.
RUN = {"run_timeout": 2700, "bridge_timeout": 90, "max_actions": 1500}
MAX_FAILURES = 12
RETRY_SECONDS = 30
JVM_SECONDS = 14 * 3600
MENU_SECONDS = 60
FAILURES = (BridgeError, ProtocolError, RuntimeError, OSError, subprocess.SubprocessError)


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
        stack, self.stack, self.link = self.stack, None, None
        if stack is not None:
            stack.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *arguments):
        self.close()


def play_seeds(game: Game, output: Path, seeds: list[str], scorer: Scorer | None, *,
               temperature: float, label: str, seed_offset: int = 0) -> list[dict]:
    """Play each seed once, in order. A lost link is not an outcome: the seed is played again
    in a new JVM."""
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "job.json", {"label": label, "seeds": seeds, "temperature": temperature,
                                     "revision": revision(), "started": time.time()})
    results = []
    for index, seed in enumerate(seeds):
        for attempt in range(MAX_FAILURES):
            policy = LocalPolicy(scorer, temperature=temperature, seed=seed_offset + index)
            run = output / f"run-{index:04d}-{attempt}"
            try:
                result = one_run(run, seed, policy, game.link)
                keep = _keep(result, run, label, temperature, policy)
                if result["status"] == "truncated":
                    game.close()  # still in a run, so only a new JVM leaves it
                    game.open()
                else:
                    game.link.to_menu()
                break
            except FAILURES as error:
                note = f"{type(error).__name__}: {error}"[:200]
                print(json.dumps({"seed": seed, "status": "infrastructure", "error": note}),
                      flush=True)
                game.close()
                game.open()
        else:
            raise RuntimeError(f"Seed {seed} failed {MAX_FAILURES} times")
        with (output / "results.jsonl").open("a") as file:
            file.write(json.dumps(keep) + "\n")
        print(json.dumps({k: keep.get(k) for k in ("seed", "status", "floor", "decisions",
                                                   "elapsed_seconds")}), flush=True)
        results.append(keep)
    return results
