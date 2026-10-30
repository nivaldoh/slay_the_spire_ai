"""A native multiplayer worker joins one game client's mailbox to the match coordinator's link
(``engine/link.py``); ``serve`` runs the coordinator for one match attempt. Plan:
docs/twwarhammer3/native-multiplayer.md, "Architecture", "Identity, timing and evidence
contract", "Proposed worker connection" and steps 4 and 5.

The coordinator (``serve``) records the attempt under
``runs/twwarhammer3/native-multiplayer/<match>/<attempt>/`` and writes each client's token to
``runs/twwarhammer3/native-multiplayer/tokens/<match>-<attempt>-<client>.token`` (owner-only
on Linux; on Windows the folder's access rules decide), printing only its path. Every worker
must report the same four fields (``expected_manifest``): the pinned Steam build and
``Warhammer3.exe`` sha256, the sha256 of the mod pack built in memory from this checkout's mod
source, and ``source_sha256`` over the files of ``play.SOURCES`` (no git, so a VM needs none;
a checkout that converts line endings differs). Operator commands are JSON lines on stdin,
``{"client", "body"}``; EOF or Ctrl-C closes the attempt.

A worker (``run``) says hello with the four fields measured on its own host and touches neither
the game nor the bridge before the coordinator accepts it. Owned (default): it takes
``RuntimeLock``, prepares the runtime, resets the mailbox, publishes ``session.json`` (job
``<match>.<attempt>.<client>``, the ``multiplayer`` mode) and runs the game through
``OwnedGame``. ``--attach`` borrows a running game's bridge and its session's job, and must find
the same ``multiplayer`` mode there; it launches, resets and writes nothing. Each new observation
``(battle, seq)`` goes to the coordinator as an ``observation`` event, whole (evaluator sections
included: evidence for the coordinator, never a policy view) with the file's write time. In
``control`` a command body ``{"based_on", "orders"}`` is accepted only with unqueued ``move``
orders that ``protocol.validate_orders`` allows in the latest observation; it is written to
``orders.json`` and reported ``submitted`` only once an observation's ``orders.request`` names it.
Without that acknowledgement within ``ACK_S`` its effect is unknown and the worker stops. When
the lease ends, the worker closes an owned game, removes its session, closes the link and exits
1; a borrowed game keeps running. An owned game that exits ends the worker too (1); on that or
another planned end (``--max-minutes``, Ctrl-C) it sends its spooled events once more.

Followed: PySC2 0df53d38c153972f1e368572ba65b1442a0fd41f, ``pysc2/env/sc2_env.py`` and
``pysc2/tests/multi_player_test.py``: one process per player with an explicit identity, and
every owned process closed after a failure.
"""

import contextlib
import hashlib
import json
import os
import platform
import re
import secrets
import sys
import threading
import time
from pathlib import Path

from gameai import windows
from gameai.provenance import REPO_ROOT, sha256, source_fingerprints
from twwarhammer3.battle.play import SOURCES
from twwarhammer3.engine import pack, runtime
from twwarhammer3.engine.link import Coordinator, LinkRefused, WorkerLink, token_sha256
from twwarhammer3.engine.mailbox import Mailbox
from twwarhammer3.protocol import IllegalActionError, validate_orders

ROOT = REPO_ROOT / "runs/twwarhammer3/native-multiplayer"
MODES = ("observe", "control")
# JUDGEMENT?: worker session — Claude, 2026-10-30: play's default rates (an observation every
# 1000 ms of battle time, a 250 ms Lua tick), no replay frames, no menu.json steps. Other rates
# change the timing evidence of plan steps 4-5 and how soon an order is acknowledged.
SESSION = {"enabled": True, "observe_ms": 1000, "tick_ms": 250, "record_replay": False}
# JUDGEMENT?: acknowledgement bound — Claude, 2026-10-30: 10 s for the game to acknowledge a written
# request (the Lua reads orders.json every 200 ms and answers at its next tick). A shorter bound
# stops a match on a slow frame; a longer one acts on an unknown effect later.
ACK_S = 10.0
# JUDGEMENT?: worker run bound — Claude, 2026-10-30: 240 minutes, launch's default game timeout;
# the worker and its owned game stop then. A shorter bound can cut a long match short.
MAX_MINUTES = 240


def check_names(*names: str) -> None:
    if not all(re.fullmatch(r"[A-Za-z0-9_-]+", name) for name in names):
        raise ValueError("match and attempt names are letters, digits, _ and -")


def source_sha256() -> str:
    """sha256 over play.SOURCES' file hashes, keyed by POSIX path so WSL and Windows agree."""
    files = {Path(name).as_posix(): digest
             for name, digest in source_fingerprints(SOURCES).items()}
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def pack_sha256() -> str:
    """The pack this checkout's mod source builds, hashed in memory (nothing is installed)."""
    return hashlib.sha256(pack.pack_bytes(runtime.mod_files())).hexdigest()


def expected_manifest() -> dict:
    return {"steam_build_id": runtime.PINS["steam_build_id"],
            "exe_sha256": runtime.PINS["Warhammer3.exe"],
            "pack_sha256": pack_sha256(), "source_sha256": source_sha256()}


def host_manifest() -> dict:
    """The expected fields as this host has them, plus informational platform facts."""
    exe = runtime.GAME_DIR / "Warhammer3.exe"
    return {"steam_build_id": runtime.steam_build_id(),
            "exe_sha256": sha256(exe) if exe.is_file() else None,
            "pack_sha256": pack_sha256(), "source_sha256": source_sha256(),
            "platform": platform.platform(), "python": platform.python_version(),
            "native": windows.NATIVE}


def write_token(path: Path, token: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as file:
        file.write(token + "\n")


def serve(match: str, attempt: str, clients: list[str], *, port: int = 0) -> int:
    """Serve one attempt until stdin ends; 1 when the attempt failed."""
    check_names(match, attempt)
    tokens = {client: secrets.token_urlsafe(32) for client in clients}
    manifest = {"match": match, "attempt": attempt, "expected": expected_manifest(),
                "clients": {client: {"token_sha256": token_sha256(token)}
                            for client, token in tokens.items()}}
    with Coordinator(manifest, ROOT / match / attempt, port=port) as coordinator:
        for client, token in tokens.items():
            path = ROOT / "tokens" / f"{match}-{attempt}-{client}.token"
            write_token(path, token)
            print(f"token for {client}: {path}", flush=True)
        print(f"serving {coordinator.url}", flush=True)
        with contextlib.suppress(KeyboardInterrupt):
            for line in sys.stdin:
                if not line.strip():
                    continue
                try:
                    command = json.loads(line)
                    seq = coordinator.submit(command["client"], command["body"])
                except (ValueError, KeyError, TypeError, LinkRefused) as error:
                    print(f"refused: {error}", flush=True)
                    continue
                print(f"queued command {seq} for {command['client']}", flush=True)
        failed = coordinator.failed
    print("closed" + (f": {failed}" if failed else ""), flush=True)
    return 1 if failed else 0


class Worker:
    """The observation side (``watch``, one thread) and the command side (``on_command``, the
    link's poll thread) of one client."""

    def __init__(self, link: WorkerLink, mailbox: Mailbox, mode: str, *, ack_s: float = ACK_S):
        self.link, self.mailbox, self.mode, self.ack_s = link, mailbox, mode, ack_s
        self.latest = self._seen = None
        self._changed = threading.Condition()

    def watch(self) -> None:
        observation = self.mailbox.read_observation()
        if observation is None or (observation.get("battle"), observation.get("seq")) == self._seen:
            return
        self._seen = observation.get("battle"), observation.get("seq")
        self.link.event("observation", {"written_ns": self.mailbox.written_ns,
                                        "observation": observation})
        with self._changed:
            self.latest = observation
            self._changed.notify_all()

    def refusal(self, body, observation: dict | None) -> str | None:
        if self.mode != "control":
            return "observe mode takes no commands"
        if not isinstance(body, dict) or set(body) != {"based_on", "orders"}:
            return 'a command is {"based_on", "orders"}'
        orders = body["orders"]
        if not isinstance(orders, list) or not all(
                isinstance(order, dict) and order.get("type") == "move" and "queue" not in order
                for order in orders):
            return "multiplayer control takes unqueued move orders only"
        if observation is None:
            return "no observation yet"
        try:
            validate_orders(orders, observation)
        except IllegalActionError as error:
            return str(error)
        return None

    def on_command(self, command: dict) -> str:
        """"rejected", or "submitted" once the game acknowledges; raises when it does not."""
        seq, body = command["seq"], command["body"]
        with self._changed:
            observation = self.latest
        reason = self.refusal(body, observation)
        if reason:
            self.link.event("command", {"seq": seq, "status": "rejected", "reason": reason})
            return "rejected"
        request = self.mailbox.write_orders(observation["battle"], body["based_on"],
                                            body["orders"], timeout=self.ack_s)
        self.link.event("command", {"seq": seq, "status": "written", "request": request})
        deadline = time.monotonic() + self.ack_s
        with self._changed:
            while (self.latest.get("orders") or {}).get("request") != request:
                if not self._changed.wait(max(0.0, deadline - time.monotonic())):
                    raise TimeoutError(f"request {request} was not acknowledged in {self.ack_s} s")
            ack = self.latest["orders"]
        self.link.event("command", {"seq": seq, "status": "submitted", "request": request,
                                    "ack": ack})
        return "submitted"


def run(url: str, token: str, *, match: str, attempt: str, client: str, mode: str,
        attach: bool, bridge: Path, max_s: float, ack_s: float = ACK_S,
        **link_settings) -> int:
    """One worker until its lease ends (1), its owned game exits (1) or ``max_s`` passes (0)."""
    check_names(match, attempt)
    if mode not in MODES:
        raise ValueError(f"mode is one of {MODES}")
    stopped = threading.Event()
    link = WorkerLink(url, token, match=match, attempt=attempt, client=client,
                      manifest=host_manifest(), stop=stopped.set, **link_settings)
    link.hello()  # a refusal raises before anything local is touched
    deadline = time.monotonic() + max_s
    try:
        if stopped.is_set():  # an evidence-only hello: this attempt takes no commands
            print("worker: hello gave no actuation", file=sys.stderr)
            return 1
        if attach:
            live = json.loads((bridge / "session.json").read_text())
            if live.get("multiplayer") != mode:
                raise RuntimeError(f"the running session's multiplayer is "
                                   f"{live.get('multiplayer')!r}, not {mode!r}")
        mailbox = Mailbox(bridge, job=live["job"] if attach else f"{match}.{attempt}.{client}")
        worker = Worker(link, mailbox, mode, ack_s=ack_s)
        link.start(worker.on_command)
        with contextlib.ExitStack() as stack:
            game = None
            if attach:
                link.event("session", {"owned": False, "session": live})
            else:
                stack.enter_context(runtime.RuntimeLock())
                link.event("runtime", runtime.prepare_runtime())
                mailbox.reset()
                session = {**SESSION, "multiplayer": mode}
                stack.enter_context(mailbox.owned_session(session))
                link.event("session", {"owned": True, "session": session})
                log = ROOT / match / attempt / f"worker-{client}" / "game.log"
                game = stack.enter_context(runtime.OwnedGame(log, timeout=max_s))
                link.event("game", game.info)
            while not stopped.is_set():
                if time.monotonic() >= deadline:
                    print("worker: run bound reached", file=sys.stderr)
                    return 0
                if game is not None and game.process.poll() is not None:
                    link.event("game_exited", {"returncode": game.process.poll()})
                    print("worker: the game exited", file=sys.stderr)
                    return 1
                worker.watch()
                stopped.wait(mailbox.poll)
            print("worker: the lease ended", file=sys.stderr)
            return 1
    finally:
        link.close()
        if not stopped.is_set():
            link.beat()  # a planned end: send what is still spooled
