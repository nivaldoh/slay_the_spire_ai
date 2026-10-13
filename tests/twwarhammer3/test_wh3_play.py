import csv
import json
from collections import deque
from contextlib import nullcontext

import pytest

from gameai.ledger import BudgetExhausted
from twwarhammer3.battle import play, stats
from twwarhammer3.battle.scripted import AttackNearest, Hold
from twwarhammer3.protocol import BattleRestarted, MailboxTimeout


def observation(seq, time_ms, *, battle="b1", phase="Deployed", result=None, ack=False,
                awaiting=False, enemy=True):
    return {
        "schema": 1, "job": "job", "battle": battle, "seq": seq, "phase": phase,
        "time_ms": time_ms, "speed": 1, "awaiting_orders": awaiting, "remaining_ms": 100000,
        "armies": {"player": {"faction": "kho"}, "enemy": {"faction": "dwf"}},
        "friendly": [{"id": "f1", "type": "kho_inf_a", "class": "infantry", "x": 0.0, "z": 0.0,
                      "men": 100, "men0": 100, "hp": 1.0, "state": []}],
        "enemy_roster": [{"id": "e1", "type": "dwf_inf_b"}],
        "enemy": [{"id": "e1", "type": "dwf_inf_b", "class": "infantry", "x": 50.0, "z": 50.0,
                   "men": 90, "men0": 90, "hp": 1.0, "state": []}] if enemy else [],
        "orders": None, "result": result, "ack": ack,
    }


class FakeMailbox:
    def __init__(self, observations, *, job="job"):
        self.queue = deque(observations)
        self.job = job
        self.requests = []
        self.controls = []
        self.pending = None
        self.menu = None
        self.menu_outcome = "step 1: found button_battle, clicked\ndone"

    def reset(self):
        pass

    def write_session(self, session):
        self.session = session

    def write_menu(self, steps):
        self.menu = steps

    def wait_new_battle(self, *, not_battle, timeout):
        if not self.queue:
            raise MailboxTimeout("no battle")
        return self.queue.popleft()

    def wait_observation(self, *, battle, after_seq, timeout):
        if not self.queue:
            raise MailboxTimeout("no observation")
        item = dict(self.queue.popleft())
        if item["battle"] != battle:
            raise BattleRestarted(item)
        if self.pending and item.pop("ack", False):
            request, orders = self.pending
            self.pending = None
            item["orders"] = {"request": request, "based_on": 0,
                              "applied_ms": item["time_ms"] - 500,
                              "results": [{"unit": o["unit"], "ok": True} for o in orders]}
        return item

    def write_orders(self, battle, based_on, orders):
        request = f"r{len(self.requests) + 1}"
        self.requests.append((battle, based_on, orders))
        self.pending = (request, orders)
        return request

    def write_control(self, battle, control):
        self.controls.append((battle, control))
        return "c"

    def log_offset(self, name="mod.log"):
        return 0

    def log_since(self, offset, name="mod.log"):
        if name == "menu.log":
            return "frontend loaded\n" + (self.menu_outcome + "\n" if self.menu else "")
        return "[0] loaded battle b1\n"


CONFIG = {"policy": "attack_nearest", "episodes": 1, "scenario": "small", "speed": 1.0,
          "pause": False, "interval_ms": 5000, "observe_ms": 1000, "tick_ms": 250,
          "autostart": True, "menu": True, "start_timeout": 5, "observation_timeout": 5,
          "episode_timeout": 100, "run_timeout": 100, "attach": False, "results": ""}


def test_episode_decides_waits_for_the_ack_and_the_interval_then_records_the_result(tmp_path):
    mailbox = FakeMailbox([
        observation(0, 0, phase="Loading", enemy=False),
        observation(1, 0, phase="Deployment"),
        observation(2, 1000),
        observation(3, 2000, ack=True),
        observation(4, 4000),
        observation(5, 6500),
        observation(6, 7500, ack=True),
        observation(7, 9000, result="won"),
    ])
    result = play.play_episode(tmp_path / "episode-0000", CONFIG, AttackNearest(), mailbox,
                               not_battle=None)
    assert result["status"] == "won" and result["battle_s"] == 9
    assert result["decisions"] == 2 and result["invalid"] == 0
    assert result["delays_ms"] == [500, 500] and result["delay_s"] == 0.5
    assert result["scenario"] == "kho(1) vs dwf(1)"
    assert [r[1] for r in mailbox.requests] == [2, 5]
    attack = {"unit": "f1", "type": "attack", "target": "e1", "run": False}
    assert mailbox.requests[0][2] == [attack]
    assert mailbox.requests[1][2] == []
    kinds = [json.loads(line)["kind"] for line in (tmp_path / "episode-0000/trace.jsonl").open()]
    assert kinds == ["battle", "roster", "observation", "decision", "ack", "observation",
                     "decision", "ack", "result"]
    assert (tmp_path / "episode-0000/mod.log").read_text() == "[0] loaded battle b1\n"
    assert json.loads((tmp_path / "episode-0000/result.json").read_text())["status"] == "won"


def test_pause_mode_decides_only_when_the_game_awaits_orders(tmp_path):
    mailbox = FakeMailbox([
        observation(0, 0), observation(1, 1000), observation(2, 2000, awaiting=True),
        observation(3, 2500, ack=True), observation(4, 3000, result="lost"),
    ])
    config = {**CONFIG, "pause": True}
    result = play.play_episode(tmp_path / "e", config, AttackNearest(), mailbox, not_battle=None)
    assert result["status"] == "lost" and result["decisions"] == 1
    assert mailbox.requests[0][1] == 2


def test_silence_is_an_infrastructure_failure_and_a_new_battle_a_restart(tmp_path):
    result = play.play_episode(tmp_path / "a", CONFIG, Hold(), FakeMailbox([observation(0, 0)]),
                               not_battle=None)
    assert result["status"] == "infrastructure_failure" and "no observation" in result["error"]
    mailbox = FakeMailbox([observation(0, 0), observation(0, 0, battle="b2")])
    result = play.play_episode(tmp_path / "b", CONFIG, Hold(), mailbox, not_battle=None)
    assert result["status"] == "infrastructure_failure" and "b2" in result["error"]


def test_illegal_scripted_orders_are_counted_and_not_sent(tmp_path):
    class Broken(Hold):
        def decide(self, observation):
            return [{"unit": "f9", "type": "halt"}]

    mailbox = FakeMailbox([observation(0, 0), observation(1, 1000),
                           observation(2, 2000, ack=True), observation(3, 3000, result="draw")])
    result = play.play_episode(tmp_path / "e", CONFIG, Broken(), mailbox, not_battle=None)
    assert result["status"] == "draw" and result["invalid"] == 1
    assert mailbox.requests[0][2] == []


@pytest.fixture
def harness(tmp_path, monkeypatch):
    boxes = []

    class FakeGame:
        info = {"pid": 1}

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def mailbox_factory(directory, *, job):
        boxes[0].job = job
        return boxes[0]

    monkeypatch.setattr(play, "RuntimeLock", nullcontext)
    monkeypatch.setattr(play, "OwnedGame", FakeGame)
    monkeypatch.setattr(play, "prepare_runtime", lambda: {"pack": {}})
    monkeypatch.setattr(play, "collect_diagnostics", lambda: {"status": "ready"})
    monkeypatch.setattr(play, "committed_revision", lambda purpose, paths: "abc1234def")
    monkeypatch.setattr(play, "source_fingerprints", lambda paths: {})
    monkeypatch.setattr(play, "Mailbox", mailbox_factory)
    menu = tmp_path / "menu.json"
    menu.write_text(json.dumps([{"find": ["button_battle"], "click": True}]))
    monkeypatch.setattr(play, "MENU_PATH", menu)
    return boxes


def test_job_plays_episodes_with_restarts_and_records_rows(tmp_path, harness):
    mailbox = FakeMailbox([
        observation(0, 0), observation(1, 1000), observation(2, 2000, ack=True),
        observation(3, 3000, result="won"),
        observation(0, 0, battle="b2"), observation(1, 500, battle="b2"),
        observation(2, 1500, battle="b2", ack=True),
        observation(3, 4000, battle="b2", result="lost"),
    ])
    harness.append(mailbox)
    results = tmp_path / "results.csv"
    config = {**CONFIG, "episodes": 2, "results": str(results)}
    manifest = play.play(tmp_path / "attack-v1-20261013", config, policy_factory=AttackNearest)
    assert manifest["status"] == "completed"
    assert [e["status"] for e in manifest["episodes"]] == ["won", "lost"]
    assert mailbox.controls == [("b1", "restart")]
    assert mailbox.menu == [{"find": ["button_battle"], "click": True}]
    assert mailbox.session["interval_ms"] == 5000 and mailbox.job == "attack-v1-20261013"
    rows = list(csv.DictReader(results.open()))
    assert [(r["episode"], r["outcome"], r["model"], r["harness"], r["mode"]) for r in rows] == [
        ("episode-0000", "won", "attack_nearest", "1", "realtime"),
        ("episode-0001", "lost", "attack_nearest", "1", "realtime"),
    ]
    table = stats.summary(results)
    assert "| small | attack_nearest |  | 1 | realtime | 2 | 1 | 1 | 0 | 0 |" in table
    rebuilt = tmp_path / "rebuilt.csv"
    assert stats.rebuild(tmp_path, rebuilt) == 2
    assert rebuilt.read_text() == results.read_text()


def test_budget_exhaustion_stops_the_job(tmp_path, harness):
    class Broke(Hold):
        def decide(self, observation):
            raise BudgetExhausted("cap")

    harness.append(FakeMailbox([observation(0, 0), observation(1, 1000),
                                observation(0, 0, battle="b2")]))
    config = {**CONFIG, "episodes": 2, "results": str(tmp_path / "r.csv")}
    manifest = play.play(tmp_path / "job", config, policy_factory=Broke)
    assert manifest["status"] == "stopped"
    assert manifest["episodes"][0]["status"] == "budget_exhausted"
    assert harness[0].controls == []


def test_a_failed_menu_step_stops_the_job_before_any_episode(tmp_path, harness):
    mailbox = FakeMailbox([observation(0, 0)])
    mailbox.menu_outcome = "step 1: not found within 240000 ms: button_battle\nfailed"
    harness.append(mailbox)
    with pytest.raises(play.ProtocolError, match="not found within 240000 ms"):
        play.play(tmp_path / "job", {**CONFIG, "results": str(tmp_path / "r.csv")},
                  policy_factory=Hold)
    manifest = json.loads((tmp_path / "job/manifest.json").read_text())
    assert manifest["status"] == "interrupted" and manifest["episodes"] == []
    assert "failed" in (tmp_path / "job/menu.log").read_text()
