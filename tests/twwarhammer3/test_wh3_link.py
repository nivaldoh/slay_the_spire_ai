"""The worker <-> coordinator link (engine/link.py): fake workers over real loopback HTTP,
with lease clocks set by hand and poll bounds of a fraction of a second. The worker's poll
timeout (1 s here) must outlast the coordinator's poll bound. Followed: PySC2
0df53d38c153972f1e368572ba65b1442a0fd41f ``pysc2/tests/multi_player_test.py``: separate
clients with explicit identities against one host, closed after each test."""

import contextlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urlsplit

import pytest

from twwarhammer3.engine.link import (
    MAX_BODY,
    Coordinator,
    LinkRefused,
    WorkerLink,
    request,
    token_sha256,
)

TOKENS = {"A": "token-for-a-3b9f0c", "B": "token-for-b-81d2e4"}
EXPECTED = {"steam_build": "25961564", "exe_sha256": "9b" * 32, "pack_sha256": "4c" * 32,
            "source_revision": "9c8e157"}


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def manifest():
    return {"match": "m1", "attempt": "a1", "expected": EXPECTED,
            "clients": {client: {"token_sha256": token_sha256(token)}
                        for client, token in TOKENS.items()}}


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def coordinator(tmp_path, clock):
    with Coordinator(manifest(), tmp_path / "a1", ttl_s=15, poll_s=0.3, clock=clock) as served:
        assert urlsplit(served.url).hostname == "127.0.0.1"  # the bound address
        yield served


def worker(coordinator, client="A", stops=None, clock=None, **settings):
    stops = [] if stops is None else stops
    return WorkerLink(coordinator.url, TOKENS[client], match="m1", attempt="a1", client=client,
                      manifest=settings.pop("manifest", EXPECTED),
                      stop=lambda: stops.append(client), clock=clock or Clock(),
                      **{"heartbeat_s": 0.1, "poll_s": 1.0, **settings})


def call(coordinator, method, path, token=None, **fields):
    body = {"match": "m1", "attempt": "a1", "client": "A", **fields}
    token = TOKENS[body["client"]] if token is None else token
    if method == "GET":
        return request(coordinator.url, "GET", f"{path}?{urlencode(body)}", token)
    return request(coordinator.url, "POST", path, token, body)


def every_request(generation):
    return (("POST", "/hello", {"heartbeat": 0, "manifest": EXPECTED}),
            ("POST", "/events", {"generation": generation, "heartbeat": 9,
                                 "events": [{"seq": 1, "kind": "forged"}]}),
            ("GET", "/next", {"generation": generation, "after": 0}),
            ("POST", "/command-status", {"generation": generation, "seq": 1,
                                         "status": "submitted", "time_ns": 1, "monotonic_ns": 1}))


def records(coordinator, kind=None):
    lines = (coordinator.directory / "match.jsonl").read_text().splitlines()
    return [row for row in map(json.loads, lines) if kind in (None, row["kind"])]


def stored_events(coordinator, client="A"):
    path = coordinator.directory / f"events-{client}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_a_wrong_token_or_identity_gets_401_or_403_and_no_data(coordinator):
    link = worker(coordinator)
    link.hello()
    link.event("observation", {"secret": "own units"})
    link.beat()
    coordinator.submit("A", {"orders": "secret move"})
    for method, path, fields in every_request(link.generation):
        for token, identity, code in (("wrong", {}, 401), ("", {}, 401),
                                      (None, {"match": "m2"}, 403),
                                      (None, {"attempt": "a0"}, 403),
                                      (TOKENS["A"], {"client": "C"}, 403)):
            status, reply = call(coordinator, method, path, token, **fields, **identity)
            assert (status, set(reply)) == (code, {"schema", "error"}), (path, token, identity)
            assert "secret" not in json.dumps(reply)
    assert [row["event"]["kind"] for row in stored_events(coordinator)] == ["observation"]
    assert link.next_command() == {"seq": 1, "body": {"orders": "secret move"}}


def test_a_hello_with_other_manifest_fields_gets_no_lease_and_names_them(coordinator):
    reported = {**EXPECTED, "exe_sha256": "00" * 32}
    del reported["pack_sha256"]
    status, reply = call(coordinator, "POST", "/hello", heartbeat=0, manifest=reported)
    assert status == 409 and reply["fields"] == ["exe_sha256", "pack_sha256"]
    assert "generation" not in reply
    with pytest.raises(LinkRefused, match="source_revision"):
        worker(coordinator, manifest={**EXPECTED, "source_revision": "dirty"}).hello()
    with pytest.raises(LinkRefused, match="no lease"):
        coordinator.submit("A", {})
    assert [row["differing"] for row in records(coordinator, "hello_refused")] == [
        ["exe_sha256", "pack_sha256"], ["source_revision"]]


def test_a_worker_cannot_poll_or_post_as_another_client(coordinator):
    a, b = worker(coordinator, "A"), worker(coordinator, "B")
    a.hello()
    b.hello()
    coordinator.submit("B", {"orders": "for b"})
    for method, path, fields in every_request(b.generation):
        status, reply = call(coordinator, method, path, TOKENS["A"], **{**fields, "client": "B"})
        assert (status, set(reply)) == (403, {"schema", "error"}), path
    assert not (coordinator.directory / "events-B.jsonl").exists()
    assert b.next_command() == {"seq": 1, "body": {"orders": "for b"}}


def test_events_are_kept_once_acknowledged_contiguously_and_a_conflict_fails_the_attempt(
        coordinator):
    link = worker(coordinator)
    link.hello()
    events = {seq: {"seq": seq, "kind": "observation", "time_ns": seq, "monotonic_ns": seq,
                    "data": {}} for seq in (1, 2, 3)}

    def post(*seqs, heartbeat, change=None):
        sent = [{**events[seq], **(change or {})} for seq in seqs]
        return call(coordinator, "POST", "/events", generation=link.generation,
                    heartbeat=heartbeat, events=sent)

    assert post(1, 1, 3, heartbeat=1)[1]["ack"] == 1
    assert post(2, heartbeat=2)[1]["ack"] == 3
    assert post(2, 3, heartbeat=3)[1]["ack"] == 3
    assert [row["event"]["seq"] for row in stored_events(coordinator)] == [1, 3, 2]
    status, reply = post(2, heartbeat=4, change={"data": {"other": 1}})
    assert (status, set(reply)) == (409, {"schema", "error"})
    assert "event 2 of client A" in coordinator.failed
    assert len(stored_events(coordinator)) == 3
    with pytest.raises(LinkRefused, match="attempt failed"):
        coordinator.submit("A", {})


def test_a_long_poll_returns_a_command_at_once_else_nothing_after_its_bound(tmp_path):
    with Coordinator(manifest(), tmp_path / "a1", poll_s=0.5) as coordinator:
        a, b = worker(coordinator, "A"), worker(coordinator, "B")
        a.hello()
        b.hello()
        start = time.monotonic()
        assert a.next_command() is None
        assert 0.45 <= time.monotonic() - start < 1.5
        with ThreadPoolExecutor(2) as pool:
            b_waits = pool.submit(b.next_command)
            a_waits = pool.submit(a.next_command)
            time.sleep(0.05)
            start = time.monotonic()
            coordinator.submit("A", {"n": 1})
            assert a_waits.result()["seq"] == 1 and time.monotonic() - start < 0.25
            coordinator.submit("B", {"n": 1})
            assert b_waits.result()["seq"] == 1 and time.monotonic() - start < 0.25
            a.report(1, "submitted")
            coordinator.submit("A", {"n": 2})
            start = time.monotonic()
            assert a.next_command()["seq"] == 2 and time.monotonic() - start < 0.25
            a.report(2, "submitted")
            a_waits = pool.submit(a.next_command)
            time.sleep(0.05)
            status, reply = call(coordinator, "GET", "/next", generation=a.generation, after=2)
            assert status == 409 and "already waiting" in reply["error"]
            assert a_waits.result() is None


def test_one_command_in_flight_and_a_delivered_command_is_never_delivered_again(coordinator):
    link = worker(coordinator)
    link.hello()
    assert coordinator.submit("A", {"n": 1}) == 1
    with pytest.raises(LinkRefused, match="no final status"):
        coordinator.submit("A", {"n": 2})
    assert link.next_command() == {"seq": 1, "body": {"n": 1}}
    with pytest.raises(LinkRefused, match="no final status"):
        coordinator.submit("A", {"n": 2})
    # The poll's reply was lost and the worker asks again from 0: nothing comes.
    status, reply = call(coordinator, "GET", "/next", generation=link.generation, after=0)
    assert (status, reply["command"]) == (200, None)
    link.report(1, "rejected")
    assert coordinator.submit("A", {"n": 2}) == 2
    assert [row["seq"] for row in records(coordinator, "delivered")] == [1]


def test_a_lost_status_reply_is_resent_and_kept_once_and_applied_is_refused(coordinator,
                                                                           monkeypatch):
    link = worker(coordinator)
    link.hello()
    coordinator.submit("A", {"n": 1})
    link.next_command()
    sent, post = [], link._post

    def lose_first_reply(path, body, timeout):
        reply = post(path, body, timeout)
        sent.append(body)
        if len(sent) == 1:
            coordinator.submit("A", {"n": 2})  # the operator saw the status first
            raise ConnectionResetError("the reply was lost")
        return reply

    monkeypatch.setattr(link, "_post", lose_first_reply)
    link.report(1, "submitted")
    assert [(body["seq"], body["status"]) for body in sent] == [(1, "submitted")] * 2
    assert [row["status"] for row in records(coordinator, "status")] == ["submitted"]
    monkeypatch.undo()
    assert link.next_command() == {"seq": 2, "body": {"n": 2}}
    with pytest.raises(LinkRefused, match="already submitted"):
        link.report(1, "rejected")
    status, _ = call(coordinator, "POST", "/command-status", generation=link.generation, seq=1,
                     status="applied", time_ns=1, monotonic_ns=1)
    assert status == 400
    with pytest.raises(ValueError, match="applied"):
        link.report(1, "applied")


def test_the_coordinator_ends_a_lease_without_a_new_heartbeat_and_fences_commands(
        coordinator, clock):
    stops = []
    a, b = (worker(coordinator, client, stops, clock) for client in "AB")
    a.hello()
    b.hello()
    coordinator.submit("A", {"n": 1})
    a.next_command()
    clock.t = 10
    a.beat()
    b.beat()
    clock.t = 20
    b.beat()
    # A's status report, poll and replayed heartbeat are no new heartbeat: none renews.
    a.report(1, "submitted")
    assert a.next_command() is None
    replay = {"generation": a.generation, "heartbeat": 1, "events": []}
    assert call(coordinator, "POST", "/events", **replay)[1]["lease"] == "stale"
    coordinator.submit("A", {"n": 2})
    coordinator.submit("B", {"n": 1})
    b.next_command()
    clock.t = 24.9
    assert coordinator.failed is None
    clock.t = 25
    assert coordinator.failed == "no new heartbeat from client A in 15 s"
    assert {(row["client"], row["kind"]) for row in records(coordinator)
            if row["kind"] in ("unknown", "fenced")} == {("A", "fenced"), ("B", "unknown")}
    with pytest.raises(LinkRefused, match="attempt failed"):
        coordinator.submit("B", {"n": 2})
    with pytest.raises(LinkRefused, match="no actuation"):
        b.next_command()
    b.beat()
    assert stops == ["B"]


def test_the_worker_lease_runs_from_the_send_time_of_its_last_renewed_heartbeat(
        coordinator, clock, monkeypatch):
    stops, own = [], Clock()
    link = worker(coordinator, stops=stops, clock=own)
    post = link._post

    def reply_at(arrival):
        def send(path, body, timeout):
            reply = post(path, body, timeout)
            own.t = arrival
            return reply
        return send

    monkeypatch.setattr(link, "_post", reply_at(3))
    link.hello()
    assert link.deadline == 15
    own.t = 4
    monkeypatch.setattr(link, "_post", reply_at(14))
    link.beat()
    assert link.deadline == 19
    own.t = 18.9
    assert link.live() and stops == []
    own.t = 19
    assert not link.live() and stops == ["A"]
    coordinator.submit("A", {"n": 1})
    assert link.next_command() is None
    assert records(coordinator, "delivered") == []
    monkeypatch.undo()
    clock.t = 10  # the stopped worker's beat carries evidence but renews nothing
    link.beat()
    clock.t = 15
    assert coordinator.failed == "no new heartbeat from client A in 15 s"
    link.beat()
    assert not link.live() and stops == ["A"]


def test_a_command_whose_poll_returns_after_the_worker_deadline_is_not_taken(
        coordinator, clock, monkeypatch):
    stops, own = [], Clock()
    link = worker(coordinator, stops=stops, clock=own)
    link.hello()
    coordinator.submit("A", {"n": 1})

    def reply_at_15(*args, **kwargs):
        reply = request(*args, **kwargs)
        own.t = 15
        return reply

    monkeypatch.setattr("twwarhammer3.engine.link.request", reply_at_15)
    assert link.next_command() is None and stops == ["A"]
    clock.t = 15
    assert coordinator.failed
    assert [row["seq"] for row in records(coordinator, "unknown")] == [1]


def test_late_old_or_ended_replies_and_unanswered_heartbeats_do_not_renew(coordinator, clock,
                                                                         monkeypatch):
    stops, own = [], Clock()
    link = worker(coordinator, stops=stops, clock=own)
    link.hello()
    post = link._post

    def altered(arrival=None, **changes):
        def send(path, body, timeout):
            status, reply = post(path, body, timeout)
            own.t = own.t if arrival is None else arrival
            return status, {**reply, **{key: change(reply[key]) for key, change in
                                        changes.items()}}
        return send

    def unanswered(path, body, timeout):
        raise ConnectionRefusedError("no coordinator")

    own.t = 2
    for send in (altered(heartbeat=lambda n: n - 1), altered(generation=lambda g: "0" * 16),
                 unanswered):
        monkeypatch.setattr(link, "_post", send)
        link.beat()
        assert link.deadline == 15 and stops == []
    own.t = 14.5
    monkeypatch.setattr(link, "_post", altered(arrival=15.5))
    link.beat()
    assert link.deadline == 15 and stops == ["A"]
    monkeypatch.undo()
    b_stops, b_clock = [], Clock()
    b = worker(coordinator, "B", b_stops, b_clock)
    b.hello()
    clock.t, b_clock.t = 16, 1  # the coordinator has expired both leases; B's clock is behind
    b.beat()
    assert b.deadline == 15 and b_stops == ["B"]


def test_after_a_coordinator_restart_the_worker_finds_its_generation_unknown_and_stops(
        tmp_path, clock):
    first = Coordinator(manifest(), tmp_path / "a1", poll_s=0.3, clock=clock)
    stops = []
    link = worker(first, stops=stops, clock=clock)
    link.hello()
    link.event("observation", {})
    first.submit("A", {"n": 1})
    link.next_command()
    first.close()
    assert [row["kind"] for row in records(first)][-2:] == ["unknown", "closed"]
    port = urlsplit(first.url).port
    with Coordinator(manifest(), tmp_path / "restarted", port=port, clock=clock) as second:
        link.beat()
        assert stops == ["A"] and not link.live()
        assert not (second.directory / "events-A.jsonl").exists()
    with pytest.raises(FileExistsError):
        Coordinator(manifest(), tmp_path / "a1", clock=clock)


def test_a_restarted_worker_may_send_evidence_but_not_take_commands_in_the_same_attempt(
        coordinator, clock):
    stops = []
    first = worker(coordinator, stops=stops, clock=clock)
    first.hello()
    first.event("observation", {"n": 1})
    first.event("observation", {"n": 2})
    first.beat()
    coordinator.submit("A", {"n": 1})
    first.next_command()
    second = worker(coordinator, stops=stops, clock=clock)
    assert second.hello()["actuation"] is False
    assert stops == ["A"] and not second.live()
    second.event("observation", {"n": 3})
    second.beat()
    assert [row["event"]["data"]["n"] for row in stored_events(coordinator)] == [1, 2, 3]
    assert [row["event"]["seq"] for row in stored_events(coordinator)] == [1, 2, 3]
    with pytest.raises(LinkRefused, match="said hello again"):
        coordinator.submit("A", {"n": 2})
    assert call(coordinator, "GET", "/next", generation=second.generation, after=0)[0] == 409
    assert [row["seq"] for row in records(coordinator, "unknown")] == [1]
    first.beat()
    assert stops == ["A", "A"]


def test_evidence_keeps_the_workers_timestamps_and_only_token_hashes(coordinator, clock,
                                                                    capfd):
    link = worker(coordinator, clock=clock)
    link.hello()
    before = (time.time_ns(), time.monotonic_ns())
    event = link.event("observation", {"tick": 5})
    after = (time.time_ns(), time.monotonic_ns())
    link.beat()
    coordinator.submit("A", {"n": 1})
    link.next_command()
    link.report(1, "submitted")
    call(coordinator, "POST", "/events", "not-a-token", generation=link.generation,
         heartbeat=9, events=[])
    clock.t = 16
    assert coordinator.failed
    assert before[0] <= event["time_ns"] <= after[0]
    assert before[1] <= event["monotonic_ns"] <= after[1]
    assert [row["event"] for row in stored_events(coordinator)] == [event]
    kinds = [row["kind"] for row in records(coordinator)]
    assert kinds[0] == "manifest" and {"hello", "command", "delivered", "status",
                                       "failed"} <= set(kinds)
    output = capfd.readouterr()
    text = "".join(path.read_text() for path in coordinator.directory.iterdir())
    text += output.out + output.err
    assert token_sha256(TOKENS["A"]) in text
    assert not [token for token in (*TOKENS.values(), "not-a-token") if token in text]


def test_a_running_worker_heartbeats_through_long_polls_and_reports_commands(tmp_path):
    coordinator = Coordinator(manifest(), tmp_path / "a1", ttl_s=0.5, poll_s=0.8)
    stops, handled = [], []
    link = worker(coordinator, stops=stops, clock=time.monotonic)
    link.hello()
    link.start(lambda command: handled.append(command) or "submitted")
    try:
        time.sleep(1.0)  # a poll waits longer than the lease lasts
        assert link.live() and stops == [] and coordinator.failed is None
        coordinator.submit("A", {"n": 1})
        limit = time.monotonic() + 2
        while not records(coordinator, "status") and time.monotonic() < limit:
            time.sleep(0.01)
        assert handled == [{"seq": 1, "body": {"n": 1}}]
        assert [row["status"] for row in records(coordinator, "status")] == ["submitted"]
    finally:
        coordinator.close()
        link.close()


def test_events_too_large_to_send_or_keep_are_refused(coordinator):
    link = worker(coordinator, spool_bytes=10_000)
    link.hello()
    with pytest.raises(ValueError, match="too large"):
        link.event("observation", {"blob": "x" * MAX_BODY})
    link.event("observation", {"blob": "x" * 6000})
    with pytest.raises(OverflowError):
        link.event("observation", {"blob": "x" * 6000})
    # Another sender's: 413, unread, so the connection may be cut while it still sends.
    big = [{"seq": 1, "kind": "observation", "data": {"blob": "x" * MAX_BODY}}]
    with contextlib.suppress(ConnectionError):
        assert call(coordinator, "POST", "/events", generation=link.generation, heartbeat=1,
                    events=big)[0] == 413
    assert not (coordinator.directory / "events-A.jsonl").exists()
