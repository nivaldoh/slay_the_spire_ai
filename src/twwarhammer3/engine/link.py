"""The private link between a match coordinator and its workers, one per game client.

The coordinator is an HTTP server on 127.0.0.1 only; Tailscale Serve is to add HTTPS in
front of it later (docs/twwarhammer3/native-multiplayer.md, "Proposed worker connection").
Workers connect out to it. Only the standard library is used, so a worker also runs under
native Windows Python. A request body is one JSON object with ``schema``; every request
carries its client's bearer token and ``match``, ``attempt`` and ``client``. The manifest
holds each token's sha256 (``token_sha256``), never the token.

- ``POST /hello`` with the worker's ``manifest`` fields: a lease ``generation`` when every
  field in the coordinator's ``expected`` matches, else 409 naming the differing ``fields``.
  A client's second hello in an attempt fails the attempt and gets an evidence-only
  generation (``actuation`` false): its events are kept, commands need a new attempt.
- ``POST /events`` with ``heartbeat`` and numbered ``events``: each ``seq`` is stored once,
  ``ack`` is the highest contiguous one, and a ``seq`` resent with other content fails the
  attempt. A heartbeat above the generation's last accepted one renews the lease
  (``lease``: ``renewed``); a repeated or older one does not (``stale``); ``ended`` tells the
  worker to stop.
- ``GET /next?after=<seq>``: the client's queued command at once, or ``"command": null``
  after the poll bound; one waiting poll per client.
- ``POST /command-status``: ``rejected``, ``submitted`` or ``unknown`` for a delivered
  command, final once set; the same report again is accepted (a retried lost reply).
  ``applied`` waits for a calibrated native witness.

The operator calls ``Coordinator.submit``: a client has at most one command without a final
status, and a delivered command is never delivered again. The attempt fails when a lease
lapses (no new heartbeat within the TTL on the coordinator's clock), a client says hello
again, or an event conflicts: every lease ends, queued commands become ``fenced`` and
delivered ones without a status ``unknown``. A coordinator refuses a directory that holds an
earlier coordinator's record, so a restart needs a new attempt.

The worker times its lease on its own monotonic clock: the send time of the last heartbeat
whose reply renewed it, plus the TTL. When that passes, it calls ``stop`` once (stop the
owned game) and takes no more commands; it keeps sending evidence until ``close``.

Evidence: ``match.jsonl`` (the manifest, then hellos, commands, statuses and failures) and
``events-<client>.jsonl`` (each event as the worker sent it, with the ``time_ns`` and
``monotonic_ns`` it took on its own host). ``coordinator_ns`` is the coordinator's receipt
clock, not a source time. Refusals: 400 malformed, 401 unknown token, 403 another client,
match or attempt, 409 refused by state, 413 too large; their body is ``{"schema", "error"}``
(a manifest refusal adds ``fields``).

Followed: PySC2 0df53d38c153972f1e368572ba65b1442a0fd41f, ``pysc2/env/sc2_env.py`` and
``pysc2/tests/multi_player_test.py``: one client per player with explicit identity, and every
owned process closed after a failure (here the worker's ``stop`` and ``Coordinator.close``).
Kubernetes client-go ``tools/leaderelection/leaderelection.go``, recalled, not fetched this
session (no commit pinned): the holder times its lease on its own clock, never on the other
side's timestamps, and gives up through one callback when it cannot renew in time. client-go
stamps its observed time after the update returns; the worker takes the send time instead,
so at equal clock rates it stops no later than the coordinator, which renews on receipt.
"""

import hashlib
import hmac
import http.client
import json
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

SCHEMA = 1
# The next three rest on JUDGEMENT docs/twwarhammer3/native-multiplayer.md Worker link.
HEARTBEAT_S = 2.0
LEASE_TTL_S = 15.0
LONG_POLL_S = 10.0
# JUDGEMENT?: link size limits — Claude, 2026-10-30: 1 MiB a request, 16 MiB of unacknowledged
# events a worker (largest stored observation 42 KB, 641 traces; none multiplayer). Smaller ones
# refuse big observations or lose evidence sooner in an outage; the worker's refusals rest on it.
MAX_BODY = 1 << 20
SPOOL_BYTES = 16 << 20
WORKER_STATUSES = ("rejected", "submitted", "unknown")
NETWORK_ERRORS = (OSError, http.client.HTTPException, json.JSONDecodeError)
ROUTES = {("POST", "/hello"): "_hello", ("POST", "/events"): "_events",
          ("GET", "/next"): "_next", ("POST", "/command-status"): "_status"}


class LinkRefused(RuntimeError):
    """The other side refused a request, or the operator's command cannot be queued."""


def token_sha256(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def request(url: str, method: str, path: str, token: str, body: dict | None = None,
            timeout: float = HEARTBEAT_S) -> tuple[int, dict]:
    """One request to the coordinator; returns the status and the reply object."""
    parts = urlsplit(url)
    kind = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    connection = kind(parts.hostname, parts.port, timeout=timeout)
    try:
        data = None if body is None else json.dumps({"schema": SCHEMA, **body}).encode()
        connection.request(method, path, data, {"Authorization": f"Bearer {token}",
                                                "Content-Type": "application/json"})
        response = connection.getresponse()
        return response.status, json.loads(response.read() or b"{}")
    finally:
        connection.close()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.coordinator.handle(self)

    do_POST = do_GET

    def log_message(self, format, *args):
        """Nothing goes to stderr: the evidence is the coordinator's directory."""


class Coordinator:
    """One attempt's coordinator, serving on 127.0.0.1 from construction until ``close``.

    ``manifest``: ``{"match", "attempt", "expected": {field: value}, "clients": {client:
    {"token_sha256"}}}``. ``clock`` times leases; the poll bound uses real time.
    """

    def __init__(self, manifest: dict, directory: Path, *, port: int = 0,
                 ttl_s: float = LEASE_TTL_S, poll_s: float = LONG_POLL_S, clock=time.monotonic):
        self.manifest, self.ttl_s, self.poll_s, self._clock = manifest, ttl_s, poll_s, clock
        self._tokens = {client: entry["token_sha256"]
                        for client, entry in manifest["clients"].items()}
        if not all(re.fullmatch(r"[A-Za-z0-9_-]+", client) for client in self._tokens):
            raise ValueError("client names are letters, digits, _ and -")
        self.directory = Path(directory)
        if (self.directory / "match.jsonl").exists():
            raise FileExistsError(f"{self.directory} holds an earlier coordinator's record")
        self.directory.mkdir(parents=True, exist_ok=True)
        self._cond = threading.Condition()
        self._leases = {}  # generation -> {"client", "beat", "renewed", "actuation"}
        self._stored = {client: {} for client in self._tokens}  # seq -> canonical text
        self._acks = dict.fromkeys(self._tokens, 0)
        self._commands = {}  # client -> its latest {"seq", "body", "state"}
        self._polling, self._helloed = set(), set()
        self._failed, self._closing = None, False
        self._server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
        self._server.coordinator = self
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._record("manifest", manifest=manifest)
        threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05},
                         daemon=True).start()  # close() waits up to one poll interval

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self) -> None:
        with self._cond:
            self._expire()
            self._closing = True
            self._record("closed", failed=self._failed)
            self._cond.notify_all()
        self._server.shutdown()
        self._server.server_close()

    @property
    def failed(self) -> str | None:
        """Why the attempt failed, or None while it runs."""
        with self._cond:
            self._expire()
            return self._failed

    def submit(self, client: str, body: dict) -> int:
        """Queue one command for ``client``; returns its seq."""
        with self._cond:
            self._expire()
            if self._failed:
                raise LinkRefused(f"attempt failed: {self._failed}")
            if not any(lease["client"] == client and lease["actuation"]
                       for lease in self._leases.values()):
                raise LinkRefused(f"client {client} holds no lease")
            previous = self._commands.get(client)
            if previous and previous["state"] in ("queued", "delivered"):
                raise LinkRefused(f"command {previous['seq']} of {client} has no final status")
            seq = previous["seq"] + 1 if previous else 1
            self._commands[client] = {"seq": seq, "body": body, "state": "queued"}
            self._record("command", client=client, seq=seq, body=body)
            self._cond.notify_all()
            return seq

    def handle(self, handler: BaseHTTPRequestHandler) -> None:
        try:
            code, reply = self._answer(handler)
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            code, reply = 400, {"error": f"malformed request: {error!r}"}
        data = json.dumps({"schema": SCHEMA, **reply}).encode()
        handler.send_response(code)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    def _answer(self, handler) -> tuple[int, dict]:
        parts = urlsplit(handler.path)
        name = ROUTES.get((handler.command, parts.path))
        if name is None:
            return 404, {"error": "no such request"}
        scheme, _, token = handler.headers.get("Authorization", "").partition(" ")
        digest = token_sha256(token)
        client = next((client for client, expected in self._tokens.items()
                       if scheme == "Bearer" and hmac.compare_digest(digest, expected)), None)
        if client is None:
            return 401, {"error": "unknown token"}
        if handler.command == "GET":
            body = dict(parse_qsl(parts.query))
        else:
            length = int(handler.headers["Content-Length"])
            if length > MAX_BODY:
                handler.close_connection = True
                return 413, {"error": f"body over {MAX_BODY} bytes"}
            body = json.loads(handler.rfile.read(max(length, 0)))
            if body.get("schema") != SCHEMA:
                return 400, {"error": f"schema must be {SCHEMA}"}
        if (body.get("client"), body.get("match"), body.get("attempt")) != (
                client, self.manifest["match"], self.manifest["attempt"]):
            return 403, {"error": "not this token's client, match and attempt"}
        with self._cond:
            self._expire()
            return getattr(self, name)(client, body)

    def _hello(self, client, body):
        reported, expected = body["manifest"], self.manifest["expected"]
        differing = [field for field in expected if reported.get(field) != expected[field]]
        if differing:
            self._record("hello_refused", client=client, differing=differing, reported=reported)
            return 409, {"error": "manifest differs: " + ", ".join(differing), "fields": differing}
        # JUDGEMENT?: rehello — Claude, 2026-10-30: a client's second hello fails the whole attempt
        # (every client's commands fenced); refusing only that client would let the others play on.
        if client in self._helloed:
            self._fail(f"client {client} said hello again: actuation needs a new attempt")
        self._helloed.add(client)
        generation = secrets.token_hex(8)
        actuation = self._failed is None
        self._leases[generation] = {"client": client, "beat": body["heartbeat"],
                                    "renewed": self._clock(), "actuation": actuation}
        self._record("hello", client=client, generation=generation, actuation=actuation,
                     reported=reported)
        return 200, {"generation": generation, "heartbeat": body["heartbeat"],
                     "ttl_s": self.ttl_s, "actuation": actuation, "ack": self._acks[client]}

    def _events(self, client, body):
        generation = body["generation"]
        lease = self._lease(client, generation)
        if lease is None:
            return 409, {"error": "unknown generation"}
        stored, new = self._stored[client], {}
        for event in body["events"]:
            seq, text = event["seq"], json.dumps(event, sort_keys=True)
            if type(seq) is not int or seq < 1:
                raise ValueError("an event seq is a positive integer")
            if stored.get(seq, new.get(seq, text)) != text:
                self._fail(f"event {seq} of client {client} was resent with other content")
                return 409, {"error": f"event {seq} differs from the one stored"}
            if seq not in stored:
                new[seq] = (text, event)
        with open(self.directory / f"events-{client}.jsonl", "a", encoding="utf-8") as handle:
            for seq, (text, event) in new.items():
                stored[seq] = text
                handle.write(json.dumps({"coordinator_ns": time.time_ns(),
                                         "generation": generation, "event": event}) + "\n")
        while self._acks[client] + 1 in stored:
            self._acks[client] += 1
        heartbeat = body["heartbeat"]
        reply = {"ack": self._acks[client], "generation": generation, "heartbeat": heartbeat,
                 "ttl_s": self.ttl_s}
        if not lease["actuation"] or self._failed:
            return 200, {**reply, "lease": "ended",
                         "reason": self._failed or "evidence only: a new attempt is needed"}
        if heartbeat > lease["beat"]:
            lease["beat"], lease["renewed"] = heartbeat, self._clock()
            return 200, {**reply, "lease": "renewed"}
        return 200, {**reply, "lease": "stale"}

    def _next(self, client, body):
        lease = self._lease(client, body["generation"])
        if lease is None:
            return 409, {"error": "unknown generation"}
        if client in self._polling:
            return 409, {"error": "a poll for this client is already waiting"}
        after, end = int(body["after"]), time.monotonic() + self.poll_s
        self._polling.add(client)
        try:
            while True:
                if not lease["actuation"] or self._failed:
                    return 409, {"error": "no actuation: " + (self._failed or "evidence only")}
                command = self._commands.get(client)
                if command and command["state"] == "queued" and command["seq"] > after:
                    command["state"] = "delivered"
                    self._record("delivered", client=client, seq=command["seq"],
                                 generation=body["generation"])
                    return 200, {"command": {"seq": command["seq"], "body": command["body"]}}
                remaining = end - time.monotonic()
                if remaining <= 0 or self._closing:
                    return 200, {"command": None}
                self._cond.wait(remaining)
                self._expire()
        finally:
            self._polling.discard(client)

    def _status(self, client, body):
        if self._lease(client, body["generation"]) is None:
            return 409, {"error": "unknown generation"}
        seq, status = body["seq"], body["status"]
        if status not in WORKER_STATUSES:
            return 400, {"error": f"a worker reports one of {', '.join(WORKER_STATUSES)}"}
        command = self._commands.get(client)
        if not command or command["seq"] != seq or command["state"] in ("queued", "fenced"):
            return 409, {"error": f"command {seq} was not delivered"}
        if command["state"] == status:
            return 200, {"seq": seq, "status": status}
        fields = {"client": client, "seq": seq, "status": status, "time_ns": body["time_ns"],
                  "monotonic_ns": body["monotonic_ns"]}
        if command["state"] != "delivered":
            self._record("late_status", state=command["state"], **fields)
            return 409, {"error": f"command {seq} is already {command['state']}"}
        command["state"] = status
        self._record("status", generation=body["generation"], **fields)
        return 200, {"seq": seq, "status": status}

    def _lease(self, client, generation):
        lease = self._leases.get(generation)
        return lease if lease and lease["client"] == client else None

    def _expire(self):
        now = self._clock()
        for lease in self._leases.values():
            if lease["actuation"] and not self._failed and now - lease["renewed"] >= self.ttl_s:
                self._fail(f"no new heartbeat from client {lease['client']} in {self.ttl_s} s")

    def _fail(self, reason):
        if self._failed:
            return
        self._failed = reason
        self._record("failed", reason=reason)
        for client, command in self._commands.items():
            if command["state"] in ("queued", "delivered"):
                command["state"] = "fenced" if command["state"] == "queued" else "unknown"
                self._record(command["state"], client=client, seq=command["seq"])
        self._cond.notify_all()

    def _record(self, kind, **fields):
        with open(self.directory / "match.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"coordinator_ns": time.time_ns(), "kind": kind, **fields})
                         + "\n")


class WorkerLink:
    """One worker's side: ``hello``, spooled ``event``s sent with heartbeats, command polls
    and status reports. ``manifest`` holds this client's build facts for the coordinator to
    compare. ``stop`` is called once, when the lease lapses or the coordinator ends it."""

    def __init__(self, url: str, token: str, *, match: str, attempt: str, client: str,
                 manifest: dict, stop, clock=time.monotonic, heartbeat_s: float = HEARTBEAT_S,
                 poll_s: float = LONG_POLL_S, spool_bytes: int = SPOOL_BYTES):
        self.url, self._token = url, token
        self.identity = {"match": match, "attempt": attempt, "client": client}
        self.manifest, self._stop_callback, self._clock = manifest, stop, clock
        self.heartbeat_s, self.poll_s, self.spool_bytes = heartbeat_s, poll_s, spool_bytes
        self.generation = self.deadline = None  # the deadline is on this host's clock
        self._heartbeat = self._renewed = self._after = 0
        self._next_event, self._room = 1, 0
        self._spool, self._spool_size = [], 0  # unacknowledged (event, encoded size)
        self._lock = threading.Lock()
        self._stopped = False
        self._closed = threading.Event()
        self._threads = []

    def hello(self) -> dict:
        sent = self._clock()
        status, reply = self._post("/hello", {"heartbeat": 0, "manifest": self.manifest},
                                   self.heartbeat_s)
        if status != 200:
            raise LinkRefused(f"hello refused ({status}): {reply.get('error')}")
        with self._lock:
            self.generation, self._next_event = reply["generation"], reply["ack"] + 1
            self._room = MAX_BODY - len(json.dumps({"schema": SCHEMA, **self.identity,
                                                    "generation": self.generation,
                                                    "heartbeat": 10**15, "events": []}))
            if reply["actuation"]:
                self.deadline = sent + reply["ttl_s"]
        if not reply["actuation"]:
            self._stop()
        self.live()
        return reply

    def event(self, kind: str, data: dict) -> dict:
        """Spool one event stamped with this host's clocks; raises when it cannot be kept."""
        with self._lock:
            if self.generation is None:
                raise RuntimeError("hello first: it sets where event numbers continue")
            event = {"seq": self._next_event, "kind": kind, "time_ns": time.time_ns(),
                     "monotonic_ns": time.monotonic_ns(), "data": data}
            size = len(json.dumps(event))
            if size > self._room:
                raise ValueError(f"event {event['seq']} is too large for one request")
            if self._spool_size + size > self.spool_bytes:
                raise OverflowError(f"over {self.spool_bytes} bytes of unacknowledged events")
            self._spool.append((event, size))
            self._spool_size += size
            self._next_event += 1
            return event

    def beat(self) -> None:
        """One POST /events: the next heartbeat and as many spooled events as fit."""
        with self._lock:
            self._heartbeat += 1
            heartbeat, room, events = self._heartbeat, self._room, []
            for event, size in self._spool:
                room -= size + 2
                if room < 0:
                    break
                events.append(event)
        sent = self._clock()
        try:
            status, reply = self._post("/events", {"generation": self.generation,
                                                   "heartbeat": heartbeat, "events": events},
                                       self._timeout())
        except NETWORK_ERRORS:
            self.live()
            return
        if status == 200:
            with self._lock:
                self._spool = [(event, size) for event, size in self._spool
                               if event["seq"] > reply["ack"]]
                self._spool_size = sum(size for _, size in self._spool)
                if (reply["lease"] == "renewed" and reply["generation"] == self.generation
                        and reply["heartbeat"] == heartbeat > self._renewed
                        and not self._stopped and self.deadline is not None
                        and self._clock() < self.deadline):
                    self.deadline, self._renewed = sent + reply["ttl_s"], heartbeat
        if status != 200 or reply["lease"] == "ended":
            self._stop()  # an unknown generation (a restarted coordinator) or a failed attempt
        self.live()

    def live(self) -> bool:
        """Whether this worker may act on a command now; calls ``stop`` once it has lapsed."""
        with self._lock:
            if self._stopped or self.deadline is None:
                return False
            if self._clock() < self.deadline:
                return True
        self._stop()
        return False

    def next_command(self) -> dict | None:
        """One long poll: the command, or None when none came or the lease lapsed meanwhile."""
        if not self.live():
            return None
        query = urlencode({**self.identity, "generation": self.generation, "after": self._after})
        status, reply = request(self.url, "GET", f"/next?{query}", self._token,
                                timeout=self.poll_s + self.heartbeat_s)
        if status != 200:
            raise LinkRefused(f"poll refused ({status}): {reply.get('error')}")
        command = reply["command"]
        if command is None:
            return None
        self._after = command["seq"]
        return command if self.live() else None  # too late: its status becomes unknown

    def report(self, seq: int, status: str) -> None:
        """POST /command-status, resent unchanged after a network failure."""
        if status not in WORKER_STATUSES:
            raise ValueError(f"a worker reports one of {WORKER_STATUSES}, not {status!r}")
        body = {"generation": self.generation, "seq": seq, "status": status,
                "time_ns": time.time_ns(), "monotonic_ns": time.monotonic_ns()}
        while True:
            try:
                code, reply = self._post("/command-status", body, self.heartbeat_s)
            except NETWORK_ERRORS:
                if self._closed.wait(self.heartbeat_s):
                    raise
                continue
            if code != 200:
                raise LinkRefused(f"status of command {seq} refused ({code}): "
                                  f"{reply.get('error')}")
            return

    def start(self, on_command) -> None:
        """Heartbeats and command polls on separate threads until ``close``.
        ``on_command(command)`` returns "submitted" or "rejected"; if it raises, the command's
        effect is unknown and the worker stops."""
        for target in (self._beat_loop, lambda: self._poll_loop(on_command)):
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            self._threads.append(thread)

    def close(self) -> None:
        self._closed.set()
        for thread in self._threads:
            thread.join(self.poll_s + self.heartbeat_s)

    def _beat_loop(self):
        while not self._closed.wait(self._timeout()):
            self.beat()

    def _poll_loop(self, on_command):
        while not self._closed.is_set() and self.live():
            try:
                command = self.next_command()
            except (LinkRefused, *NETWORK_ERRORS):
                self._closed.wait(self.heartbeat_s)
                continue
            if command is None:
                continue
            try:
                status = on_command(command)
            except Exception:
                self._stop()
                self.report(command["seq"], "unknown")
                raise
            self.report(command["seq"], status)

    def _timeout(self) -> float:
        """A heartbeat interval, cut at the deadline: a later reply cannot renew."""
        with self._lock:
            left = self.heartbeat_s
            if self.deadline is not None and not self._stopped:
                left = self.deadline - self._clock()
        return max(0.01, min(self.heartbeat_s, left))

    def _stop(self):
        with self._lock:
            stopped, self._stopped = self._stopped, True
        if not stopped:
            self._stop_callback()

    def _post(self, path, body, timeout):
        return request(self.url, "POST", path, self._token, {**self.identity, **body}, timeout)
