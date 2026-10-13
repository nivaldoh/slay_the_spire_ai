import argparse
import csv
import json
from collections import deque
from contextlib import nullcontext

import pytest

from gameai.ledger import BudgetExhausted
from twwarhammer3.__main__ import add_session_arguments
from twwarhammer3.battle import commander, digest, play, stats
from twwarhammer3.battle.scripted import AttackNearest, Hold
from twwarhammer3.protocol import BattleRestarted, MailboxTimeout


def observation(seq, time_ms, *, battle="b1", phase="Deployed", result=None, ack=False,
                awaiting=False, enemy=True):
    final = {"friendly": {"men": 50, "men0": 100}, "enemy": {"men": 9, "men0": 90}}
    return {
        "schema": 1, "job": "job", "battle": battle, "seq": seq, "phase": phase,
        "time_ms": time_ms, "speed": 1, "awaiting_orders": awaiting, "remaining_ms": 100000,
        "armies": {"player": {"faction": "kho"}, "enemy": {"faction": "dwf"}},
        "friendly": [{"id": "f1", "type": "kho_inf_a", "class": "infantry", "x": 0.0, "z": 0.0,
                      "men": 100, "men0": 100, "hp": 1.0, "state": ["melee"], "target": "e1"}],
        "enemy_roster": [{"id": "e1", "type": "dwf_inf_b"}],
        "enemy": [{"id": "e1", "type": "dwf_inf_b", "class": "infantry", "x": 50.0, "z": 50.0,
                   "men": 90, "men0": 90, "hp": 1.0, "state": []}] if enemy else [],
        "orders": None, "result": result, "ack": ack, "final": final if result else None,
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

    def read_observation(self):
        return None

    def log_offset(self, name="mod.log"):
        return 0

    def log_since(self, offset, name="mod.log"):
        if name == "menu.log":
            return "frontend loaded\n" + (self.menu_outcome + "\n" if self.menu else "")
        return "[0] loaded battle b1\n"


CONFIG = {"policy": "attack_nearest", "episodes": 1, "scenario": "kho5-dwf5", "speed": 1.0,
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
    text = digest.digest(tmp_path / "episode-0000")
    assert "episode-0000: won at 9 s battle time; 2 decisions, 0 invalid" in text
    assert "     1s  us 1/1u 100m  seen 1/1u 90m  f1 attack e1  [delay 0.5s]" in text


@pytest.mark.parametrize("change", [{"pause": True}, {"speed": 0.5}, {"speed": 2}])
def test_non_realtime_jobs_and_episodes_are_rejected_before_starting(tmp_path, change):
    config = {**CONFIG, **change}
    with pytest.raises(ValueError, match="unpaused at 1x"):
        play.play(tmp_path / "job", config, policy_factory=Hold)
    with pytest.raises(ValueError, match="unpaused at 1x"):
        play.play_episode(tmp_path / "episode", config, Hold(), FakeMailbox([]), not_battle=None)
    assert not (tmp_path / "job").exists()
    assert not (tmp_path / "episode").exists()


@pytest.mark.parametrize("arguments", [["--pause"], ["--speed", "0.5"], ["--speed", "2"]])
def test_cli_cannot_request_paused_or_changed_speed_battles(arguments):
    parser = argparse.ArgumentParser()
    add_session_arguments(parser)
    default = parser.parse_args([])
    assert default.speed == 1 and not default.pause
    with pytest.raises(SystemExit):
        parser.parse_args(arguments)


@pytest.mark.parametrize("change", [{"awaiting_orders": True}, {"speed": 0.5}])
def test_incompatible_live_observation_stops_before_a_policy_decision(tmp_path, change):
    mailbox = FakeMailbox([observation(0, 0), {**observation(1, 1000), **change}])
    result = play.play_episode(tmp_path / "e", CONFIG, Hold(), mailbox, not_battle=None)
    assert result["status"] == "unsupported_or_invalid"
    assert "unpaused 1x" in result["error"]
    assert result["decisions"] == 0 and mailbox.requests == []


def test_default_has_no_wait_and_uses_ack_observation_for_next_decision(tmp_path):
    parser = argparse.ArgumentParser()
    add_session_arguments(parser)
    assert parser.parse_args([]).interval_ms == 0
    mailbox = FakeMailbox([
        observation(0, 0), observation(1, 1000), observation(2, 2000, ack=True),
        observation(3, 3000, ack=True, result="won"),
    ])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0}, Hold(),
                               mailbox, not_battle=None)
    assert [r[1] for r in mailbox.requests] == [1, 2]
    assert result["decisions"] == 2 and result["delays_ms"] == [500, 500]
    events = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").read_text().splitlines()]
    assert [e["kind"] for e in events][-2:] == ["ack", "result"]
    observations = [e for e in events if e["kind"] == "observation"]
    assert observations[1]["since_previous_applied_ms"] == 500


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


def test_quiet_decisions_of_a_fast_policy_are_logged_once_per_observe_interval(tmp_path):
    class Fast(Hold):
        closed = False

        def decide(self, observation):
            return [{"unit": "f1", "type": "halt"}] if observation["time_ms"] == 1500 else []

        def close(self):
            self.closed = True

    mailbox = FakeMailbox([observation(0, 0), observation(1, 250)]
                          + [observation(i, 250 * i, ack=True) for i in range(2, 9)]
                          + [observation(9, 2250, ack=True, result="won")])
    policy = Fast()
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0}, policy, mailbox,
                               not_battle=None)
    assert result["decisions"] == 8 and len(result["delays_ms"]) == 8 and policy.closed
    events = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").read_text().splitlines()]
    assert [e["time_ms"] for e in events if e["kind"] == "decision"] == [250, 1250, 1500]
    assert [e["kind"] for e in events].count("observation") == 3
    assert [e["kind"] for e in events].count("ack") == 3


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
    assert mailbox.menu == play.scenario_steps("kho5-dwf5")
    assert mailbox.session["interval_ms"] == 5000 and mailbox.job == "attack-v1-20261013"
    rows = list(csv.DictReader(results.open()))
    assert [(r["episode"], r["outcome"], r["policy"], r["model"], r["harness"], r["mode"],
             r["own_left"], r["enemy_left"]) for r in rows] == [
        ("episode-0000", "won", "attack_nearest", "", "1", "realtime", "0.5", "0.1"),
        ("episode-0001", "lost", "attack_nearest", "", "1", "realtime", "0.5", "0.1"),
    ]
    table = stats.summary(results)
    assert ("| kho5-dwf5 | attack_nearest |  |  | 1 | realtime | 2 | 1 | 1 | 0 | 0 | 4 | 0.50 |"
            " 0.10 |" in table)
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


def test_a_battle_observation_ends_the_menu_wait(tmp_path, harness):
    # The frontend script unloads with the loading screen, before it can log "done".
    mailbox = FakeMailbox([observation(0, 0), observation(1, 1000, result="won")])
    mailbox.menu_outcome = "step 36: found start_button_frame/button_start_battle, clicked"
    mailbox.read_observation = lambda: observation(0, 0)
    harness.append(mailbox)
    manifest = play.play(tmp_path / "job", {**CONFIG, "results": str(tmp_path / "r.csv")},
                         policy_factory=Hold)
    assert [e["status"] for e in manifest["episodes"]] == ["won"]


def test_scenario_steps_pick_each_race_and_recruit_the_lord_first():
    steps = play.scenario_steps("kho5-dwf5")
    races = [s["find"][1] for s in steps if s.get("find", [""])[0] == "button_select_race"]
    assert races == ["CcoSubcultureRecordwh3_main_sc_kho_khorne",
                     "CcoSubcultureRecordwh_main_sc_dwf_dwarfs"]
    factions = [s["find"][1] for s in steps if s.get("find", [""])[0] == "dropdown_context_scroll"]
    assert factions == ["CcoFactionRecordwh3_main_kho_khorne", "CcoFactionRecordwh_main_dwf_dwarfs"]
    cards = [s["find"][0] for s in steps if s.get("dblclick")]
    assert cards[0] == ("CcoUnitsCustomBattlePermissionRecord"
                        "wh3_main_kho_cha_herald_of_khorne_0:wh3_main_kho_khorne:1")
    assert cards[5].endswith("wh_main_dwf_cha_lord_0:wh_main_dwf_dwarfs:1")
    assert len(cards) == 10 and all(card.endswith(":0") for card in cards[1:5] + cards[6:])
    assert steps[-1]["find"] == ["start_button_frame", "button_start_battle"]
    for name in json.loads(play.SCENARIOS_PATH.read_text()):
        assert len([s for s in play.scenario_steps(name) if s.get("dblclick")]) == 10


def test_attack_nearest_reorders_a_lapsed_attack_and_skips_the_dead():
    policy = AttackNearest()
    first = observation(1, 1000)
    assert [o["unit"] for o in policy.decide(first)] == ["f1"]
    assert policy.decide(first) == []
    lapsed = observation(2, 6000)
    lapsed["friendly"][0].update(state=["idle"], target=None)
    assert [o["target"] for o in policy.decide(lapsed)] == ["e1"]
    dead = observation(3, 9000)
    dead["friendly"][0].update(men=0, state=[], target=None)
    assert policy.decide(dead) == []


@pytest.mark.parametrize("change", [{"pause": True}, {"speed": 0.5}])
def test_attach_rejects_an_old_non_realtime_session(tmp_path, monkeypatch, harness, change):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "session.json").write_text(json.dumps({**CONFIG, **change, "job": "old"}))
    monkeypatch.setattr(play, "BRIDGE_DIR", bridge)
    with pytest.raises(ValueError, match="unpaused at 1x"):
        play.play(tmp_path / "job", {**CONFIG, "attach": True}, policy_factory=Hold)
    manifest = json.loads((tmp_path / "job/manifest.json").read_text())
    assert manifest["status"] == "interrupted" and manifest["episodes"] == []


def test_commander_jobs_snapshot_their_prompt_and_record_their_model(tmp_path, harness):
    harness.append(FakeMailbox([observation(0, 0), observation(1, 1000, result="won")]))
    results = tmp_path / "r.csv"
    config = {**CONFIG, "policy": "commander", "model": "gpt-6-luna", "effort": "low",
              "results": str(results)}
    job = tmp_path / "commander-luna-v1-20261013"
    assert play.play(job, config, policy_factory=Hold)["status"] == "completed"
    assert (job / "system_prompt.md").read_bytes() == commander.PROMPT_PATH.read_bytes()
    item = next(csv.DictReader(results.open()))
    assert (item["policy"], item["model"], item["effort"], item["harness"]) == (
        "commander", "gpt-6-luna", "low", "1")
    assert "policy commander gpt-6-luna/low" in digest.digest(job)
