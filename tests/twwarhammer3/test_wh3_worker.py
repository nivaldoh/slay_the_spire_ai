"""The native multiplayer worker and coordinator command (engine/worker.py): a real Coordinator on
127.0.0.1, the worker on a thread, and a fake game thread that publishes observation.json into a
temporary bridge and answers orders.json as the battle Lua does (it deletes the request, drops
another job's or battle's, and acknowledges in the next observation's ``orders``). Followed:
PySC2 0df53d38c153972f1e368572ba65b1442a0fd41f ``pysc2/tests/multi_player_test.py``: separate
clients with explicit identities against one host, closed after each test."""

import hashlib
import json
import os
import queue
import stat
import sys
import threading
import time

import pytest
from wh3_fixtures import bridge_observation, fake_install

from twwarhammer3.__main__ import main
from twwarhammer3.engine import runtime, worker
from twwarhammer3.engine.link import Coordinator, LinkRefused, WorkerLink, token_sha256

TOKEN = "token-for-a-5e1f0c"
MOVE = {"unit": "f1", "type": "move", "x": 10.0, "z": 20.0}
EVALUATION = {"enemy": {"men": 90, "men0": 90}}


def wait_for(condition, timeout=5.0):
    limit = time.monotonic() + timeout
    while not (value := condition()):
        assert time.monotonic() < limit, "timed out"
        time.sleep(0.01)
    return value


def records(coordinator, kind):
    lines = (coordinator.directory / "match.jsonl").read_text().splitlines()
    return [row for row in map(json.loads, lines) if row["kind"] == kind]


def events(coordinator, kind, count=0):
    """The data of client A's events of ``kind``, once there are at least ``count``."""
    def read():
        path = coordinator.directory / "events-A.jsonl"
        rows = path.read_text().splitlines() if path.exists() else []
        return [row["data"] for row in (json.loads(line)["event"] for line in rows)
                if row["kind"] == kind]
    return wait_for(lambda: len(rows := read()) >= count and rows) if count else read()


def status(coordinator, seq):
    return wait_for(lambda: [row["status"] for row in records(coordinator, "status")
                             if row["seq"] == seq])[0]


class FakeGame:
    """Publishes ``job``'s observations; answers each request for its battle like the Lua."""

    def __init__(self, bridge, job, *, ack=True):
        self.bridge, self.job, self.ack = bridge, job, ack
        self.battle, self.seq, self.requests, self.written = "b1", 0, [], {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def publish(self, seq, battle="b1", orders=None):
        self.battle, self.seq = battle, seq
        path = self.bridge / "observation.json"
        observation = {**bridge_observation(seq, 1000 * seq, battle=battle), "job": self.job,
                       "orders": orders, "evaluation": EVALUATION}
        path.with_suffix(".tmp").write_text(json.dumps(observation))
        os.replace(path.with_suffix(".tmp"), path)
        self.written.setdefault((battle, seq), path.stat().st_mtime_ns)

    def close(self):
        self._stop.set()
        self._thread.join()

    def _serve(self):
        path = self.bridge / "orders.json"
        while not self._stop.wait(0.01):
            try:
                message = json.loads(path.read_text())
            except FileNotFoundError:
                continue
            path.unlink()
            if (message["job"], message["battle"]) != (self.job, self.battle):
                continue
            self.requests.append(message)
            if self.ack:
                results = [{"index": index, "unit": order["unit"], "ok": True}
                           for index, order in enumerate(message["orders"], 1)]
                self.publish(self.seq + 1, self.battle, {
                    "request": message["request"], "based_on": message["based_on"],
                    "applied_ms": 1000 * self.seq, "results": results})


@pytest.fixture
def install(tmp_path, monkeypatch):
    """A fake game install whose executable matches the pins, and runs/ under tmp_path."""
    root = fake_install(tmp_path / "install", monkeypatch)
    monkeypatch.setitem(runtime.PINS, "Warhammer3.exe",
                        hashlib.sha256(b"not the game").hexdigest())
    monkeypatch.setattr(worker, "ROOT", tmp_path / "runs")
    return root


def serve(tmp_path, **expected):
    manifest = {"match": "m1", "attempt": "a1",
                "expected": {**worker.expected_manifest(), **expected},
                "clients": {"A": {"token_sha256": token_sha256(TOKEN)}}}
    return Coordinator(manifest, tmp_path / "a1", ttl_s=0.5, poll_s=0.3)


def start(coordinator, bridge, *, mode="control", attach=True, ack_s=2.0):
    result = []

    def run():
        result.append(worker.run(coordinator.url, TOKEN, match="m1", attempt="a1", client="A",
                                 mode=mode, attach=attach, bridge=bridge, max_s=30, ack_s=ack_s,
                                 heartbeat_s=0.05, poll_s=1.0))

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, result


def borrowed_bridge(tmp_path, mode="control"):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "session.json").write_text(json.dumps({"schema": 1, "job": "live",
                                                     "enabled": True, "multiplayer": mode}))
    (bridge / "mod.log").write_text("[0] earlier job\n")
    return bridge


def refuse_to_launch(monkeypatch):
    def launch(*args, **kwargs):
        raise AssertionError("the worker locked, prepared or launched")

    for name in ("RuntimeLock", "prepare_runtime", "OwnedGame"):
        monkeypatch.setattr(runtime, name, launch)


def interrupted():
    raise KeyboardInterrupt
    yield


def test_the_coordinator_command_prints_token_paths_only_and_submits_stdin_commands(
        tmp_path, install, monkeypatch, capsys):
    lines = queue.Queue()
    monkeypatch.setattr(sys, "stdin", iter(lines.get, None))
    command = ["wh3", "coordinator", "--match", "m1", "--attempt", "a1", "--clients", "A,B"]
    monkeypatch.setattr(sys, "argv", command)
    returned = []
    thread = threading.Thread(target=lambda: returned.append(main()), daemon=True)
    thread.start()
    output = []

    def printed(text):
        captured = capsys.readouterr()
        output.append(captured.out + captured.err)
        return text in "".join(output)

    wait_for(lambda: printed("serving http://127.0.0.1:"))
    started = "".join(output)
    root = tmp_path / "runs"
    paths = {client: root / "tokens" / f"m1-a1-{client}.token" for client in "AB"}
    assert all(f"token for {client}: {path}\n" in started for client, path in paths.items())
    assert {stat.S_IMODE(path.stat().st_mode) for path in paths.values()} == {0o600}
    tokens = [path.read_text().strip() for path in paths.values()]
    url = started.split("serving ")[1].strip()
    manifest = json.loads((root / "m1/a1/match.jsonl").read_text().splitlines()[0])["manifest"]
    assert manifest["expected"] == worker.expected_manifest()
    WorkerLink(url, tokens[0], match="m1", attempt="a1", client="A",
               manifest=worker.host_manifest(), stop=lambda: None).hello()
    for line in ('{"client": "A", "body": {"based_on": 1, "orders": []}}', "not json",
                 '{"client": "B", "body": {}}'):
        lines.put(line + "\n")
    lines.put(None)
    thread.join(5)
    printed("")
    text = "".join(output)
    assert returned == [0]
    assert "queued command 1 for A" in text and "refused: client B holds no lease" in text
    assert text.count("refused: ") == 2 and text.endswith("closed\n")
    evidence = "".join(path.read_text() for path in (root / "m1/a1").iterdir())
    assert token_sha256(tokens[0]) in evidence
    assert not [token for token in tokens if token in evidence + text]
    assert not runtime.RUNTIME_DIR.exists()  # the expected pack was built in memory only
    monkeypatch.setattr(sys, "stdin", iter([]))
    with pytest.raises(SystemExit):  # an earlier record of this attempt
        main()
    monkeypatch.setattr(sys, "stdin", interrupted())
    monkeypatch.setattr(sys, "argv", [*command[:5], "a2", *command[6:]])
    assert main() == 0  # Ctrl-C closes the attempt
    assert json.loads((root / "m1/a2/match.jsonl").read_text().splitlines()[-1])["kind"] == "closed"


def test_a_refused_worker_reported_its_host_and_touched_neither_game_nor_bridge(
        tmp_path, install, monkeypatch):
    refuse_to_launch(monkeypatch)
    expected = worker.expected_manifest()  # from the pins, as the coordinator command has it
    runtime.STEAM_MANIFEST.write_text('"buildid"\t\t"26000001"\n')  # Steam updated the game
    (runtime.GAME_DIR / "Warhammer3.exe").write_bytes(b"an updated game")
    with serve(tmp_path) as coordinator:
        with pytest.raises(LinkRefused, match="manifest differs: steam_build_id, exe_sha256"):
            worker.run(coordinator.url, TOKEN, match="m1", attempt="a1", client="A",
                       mode="control", attach=False, bridge=runtime.BRIDGE_DIR, max_s=30)
        reported = records(coordinator, "hello_refused")[0]["reported"]
    assert set(reported) == {*expected, "platform", "python", "native"}
    assert {field: reported[field] for field in expected} == {
        **expected, "steam_build_id": "26000001",
        "exe_sha256": hashlib.sha256(b"an updated game").hexdigest()}
    assert not (install / "mnt").exists()  # no runtime folder, lock or bridge


@pytest.mark.parametrize("ending", ["lease", "game exit"])
def test_an_owned_worker_runs_its_game_with_its_session_and_closes_both_when_lease_or_game_ends(
        tmp_path, install, monkeypatch, ending):
    bridge = runtime.BRIDGE_DIR
    bridge.mkdir(parents=True)
    (bridge / "mod.log").write_text("[0] earlier job\n")
    calls, returncode = [], []

    def prepare():
        calls.append(("prepare", (runtime.RUNTIME_DIR / "owner.lock").exists()))
        return {"pack": "prepared"}

    class Game:
        def __init__(self, log_path, *, timeout):
            calls.append(("game", log_path, timeout))
            self.info, self.process = {"pid": 7}, self

        def __enter__(self):
            return self

        def __exit__(self, *_):
            calls.append(("closed", (bridge / "session.json").exists()))

        def poll(self):
            return returncode[0] if returncode else None

    monkeypatch.setattr(runtime, "prepare_runtime", prepare)
    monkeypatch.setattr(runtime, "OwnedGame", Game)
    with serve(tmp_path) as coordinator:
        thread, result = start(coordinator, bridge, mode="observe", attach=False)
        session = wait_for(lambda: (bridge / "session.json").exists()
                           and json.loads((bridge / "session.json").read_text()))
        assert session == {"schema": 1, "job": "m1.a1.A", "enabled": True,
                           "multiplayer": "observe", "observe_ms": 1000, "tick_ms": 250,
                           "record_replay": False}
        assert not (bridge / "mod.log").exists()  # reset
        game = FakeGame(bridge, "m1.a1.A")
        game.publish(1)
        events(coordinator, "observation", 1)
        assert events(coordinator, "session") == [{"owned": True, "session": {
            key: value for key, value in session.items() if key not in ("schema", "job")}}]
        assert events(coordinator, "game") == [{"pid": 7}]
        if ending == "game exit":
            returncode.append(3)
            thread.join(5)
            assert events(coordinator, "game_exited", 1) == [{"returncode": 3}]
    thread.join(5)
    game.close()
    assert result == [1]
    assert calls == [("prepare", True),
                     ("game", tmp_path / "runs/m1/a1/worker-A/game.log", 30),
                     ("closed", True)]
    assert not (bridge / "session.json").exists()


def test_an_attached_worker_sends_each_new_observation_and_leaves_the_borrowed_game(
        tmp_path, install, monkeypatch):
    refuse_to_launch(monkeypatch)
    bridge = borrowed_bridge(tmp_path, "observe")
    before = {path.name: path.read_text() for path in bridge.iterdir()}
    game = FakeGame(bridge, "live")
    with serve(tmp_path) as coordinator:
        thread, result = start(coordinator, bridge, mode="observe")
        for seq, battle, total in ((0, "b1", 1), (1, "b1", 2), (1, "b1", 2), (1, "b2", 3)):
            game.publish(seq, battle)
            events(coordinator, "observation", total)
            time.sleep(0.15)  # longer than the worker's mailbox poll
        sent = events(coordinator, "observation")
    thread.join(5)
    game.close()
    assert result == [1]
    keys = [(row["observation"]["battle"], row["observation"]["seq"]) for row in sent]
    assert keys == [("b1", 0), ("b1", 1), ("b2", 1)]
    assert [row["written_ns"] for row in sent] == [game.written[key] for key in keys]
    assert sent[0]["observation"]["evaluation"] == EVALUATION  # evidence for the coordinator
    assert {path.name: path.read_text() for path in bridge.iterdir()
            if path.name != "observation.json"} == before


@pytest.mark.parametrize("mode", ["control", "observe"])
def test_only_valid_moves_are_written_and_reported_submitted_on_the_games_acknowledgement(
        tmp_path, install, monkeypatch, mode):
    refuse_to_launch(monkeypatch)
    bridge = borrowed_bridge(tmp_path, mode)
    game = FakeGame(bridge, "live")
    game.publish(1)
    commands = [{"based_on": 1, "orders": [MOVE]},
                {"based_on": 1, "orders": [{"unit": "f1", "type": "attack", "target": "e1"}]},
                {"based_on": 1, "orders": [MOVE, {**MOVE, "queue": True}]},
                {"based_on": 1, "orders": [{**MOVE, "unit": "f9"}]},
                {"based_on": 1, "orders": [MOVE], "say": "hello"}]
    with serve(tmp_path) as coordinator:
        thread, result = start(coordinator, bridge, mode=mode)
        events(coordinator, "observation", 1)
        statuses = []
        for seq, body in enumerate(commands, 1):
            coordinator.submit("A", body)
            statuses.append(status(coordinator, seq))
        reports = events(coordinator, "command", 6 if mode == "control" else 5)
    thread.join(5)
    game.close()
    assert result == [1]
    if mode == "observe":
        assert statuses == ["rejected"] * 5 and game.requests == []
        assert {row["reason"] for row in reports} == {"observe mode takes no commands"}
        return
    assert statuses == ["submitted"] + ["rejected"] * 4
    assert [(row["status"], row.get("reason")) for row in reports[2:]] == [
        ("rejected", "multiplayer control takes unqueued move orders only"),
        ("rejected", "multiplayer control takes unqueued move orders only"),
        ("rejected", "unknown friendly unit 'f9'"),
        ("rejected", 'a command is {"based_on", "orders"}')]
    [request] = game.requests
    assert (request["job"], request["battle"], request["based_on"], request["orders"]) == (
        "live", "b1", 1, [MOVE])
    assert [row["status"] for row in reports[:2]] == ["written", "submitted"]
    assert reports[0]["request"] == reports[1]["ack"]["request"] == request["request"]


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
def test_a_request_the_game_takes_but_never_acknowledges_is_unknown_and_stops_the_worker(
        tmp_path, install, monkeypatch):
    refuse_to_launch(monkeypatch)
    bridge = borrowed_bridge(tmp_path)
    game = FakeGame(bridge, "live", ack=False)
    game.publish(1)
    with serve(tmp_path) as coordinator:
        thread, result = start(coordinator, bridge, ack_s=0.3)
        events(coordinator, "observation", 1)
        coordinator.submit("A", {"based_on": 1, "orders": [MOVE]})
        assert status(coordinator, 1) == "unknown"
        thread.join(5)
        assert result == [1] and len(game.requests) == 1
        assert [row["status"] for row in events(coordinator, "command", 1)] == ["written"]
    game.close()
