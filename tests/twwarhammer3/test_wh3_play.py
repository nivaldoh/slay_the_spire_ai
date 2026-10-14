import argparse
import csv
import json
import sys
from collections import deque
from contextlib import nullcontext
from pathlib import Path

import pytest

from gameai.ledger import BudgetExhausted
from twwarhammer3.__main__ import add_session_arguments, main
from twwarhammer3.battle import commander, controllers, digest, llm, play, stats
from twwarhammer3.battle.scripted import AttackNearest, Hold
from twwarhammer3.protocol import BattleRestarted, MailboxTimeout, PolicyFailure


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
        self.directory = Path("no-bridge")  # no menu dumps unless a test makes one
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
                              "results": [{"unit": o["unit"], "ok": True, "index": i + 1}
                                          for i, o in enumerate(orders)]}
        return item

    def write_orders(self, battle, based_on, orders, say=None):
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


@pytest.mark.parametrize("option", [["--model", "gpt-6-lunar"], ["--effort", "max"]])
def test_cli_rejects_an_unknown_model_or_effort_before_launch(tmp_path, monkeypatch, capsys,
                                                               option):
    output = tmp_path / "job"
    monkeypatch.setattr(sys, "argv", [
        "twwarhammer3", "play", "--scenario", "random", "--output", str(output), *option])
    with pytest.raises(SystemExit):
        main()
    assert "invalid choice" in capsys.readouterr().err
    assert not output.exists()


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


@pytest.mark.parametrize("status", ["won", "lost", "draw"])
def test_expired_countdown_preserves_engine_outcome_after_timer_resets(tmp_path, status):
    timer = {"observed_ms": 1204100, "remaining_ms": 945.6787109375,
             "deadline_ms": 1205045.6787109375, "expired": True, "source": "countdown_deadline"}
    terminal = {**observation(2, 1205200, result=status), "remaining_ms": -1, "timer": timer}
    mailbox = FakeMailbox([observation(0, 0), terminal])
    result = play.play_episode(tmp_path / "e", CONFIG, Hold(), mailbox, not_battle=None)
    assert result["status"] == status and result["ended_by"] == "time_limit"
    assert result["timer"] == timer and result["remaining_ms"] == -1
    assert not mailbox.requests


def test_unlimited_or_unexpired_timer_does_not_imply_timeout(tmp_path):
    for name, timer in (("unlimited", None), ("early", {"expired": False})):
        terminal = {**observation(2, 3000, result="lost"), "remaining_ms": -1, "timer": timer}
        result = play.play_episode(tmp_path / name, CONFIG, Hold(),
                                   FakeMailbox([observation(0, 0), terminal]), not_battle=None)
        assert result["status"] == "lost" and result["ended_by"] == "engine_result"


def test_illegal_scripted_orders_are_counted_and_not_sent(tmp_path):
    class Broken(Hold):
        def __init__(self):
            self.feedback = []

        def decide(self, observation):
            return [{"unit": "f9", "type": "halt"}]

        def acknowledge(self, ack, latency):
            self.feedback.append((ack, latency))

    mailbox = FakeMailbox([observation(0, 0), observation(1, 1000),
                           observation(2, 2000, ack=True), observation(3, 3000, result="draw")])
    policy = Broken()
    result = play.play_episode(tmp_path / "e", CONFIG, policy, mailbox, not_battle=None)
    assert result["status"] == "draw" and result["invalid"] == 1
    assert mailbox.requests[0][2] == []
    assert "f9" in policy.feedback[0][0]["validation_error"]
    assert policy.feedback[0][0]["results"][0]["ok"] is False
    assert policy.feedback[0][1]["delay_ms"] == 500


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


def test_the_observation_a_failing_decision_saw_is_kept_in_the_trace(tmp_path):
    class Failing(Hold):
        def decide(self, observation):
            raise PolicyFailure("no reply", failure={"kind": "invalid_reply"})

    mailbox = FakeMailbox([observation(0, 0), observation(1, 1000)])
    result = play.play_episode(tmp_path / "e", CONFIG, Failing(), mailbox, not_battle=None)
    assert result["status"] == "policy_failure"
    kinds = [json.loads(line)["kind"] for line in (tmp_path / "e/trace.jsonl").open()]
    assert kinds[-1] == "observation"


def test_delayed_policy_gets_old_public_state_but_results_use_current_evaluation(tmp_path):
    class Reader(Hold):
        def __init__(self):
            self.times = []

        def decide(self, observation):
            assert "evaluation" not in observation and "final" not in observation
            assert "setup" not in observation
            self.times.append(observation["time_ms"])
            return []

    states = [observation(0, 0)] + [observation(i, i * 1000, ack=True) for i in range(1, 6)]
    for state in states:
        state["evaluation"] = {"friendly": {"men0": 100, "active_men": 40},
                               "enemy": {"men0": 100, "active_men": 20}}
        state["setup"] = {"private": True}
    reader = Reader()
    mailbox = FakeMailbox(states)
    result = play.play_episode(tmp_path / "e", {**CONFIG, "delay_ms": 2000, "interval_ms": 0},
                               reader, mailbox, not_battle=None)
    assert reader.times == [1000, 2000, 3000]
    assert [request[1] for request in mailbox.requests] == [1, 2, 3]
    assert result["delays_ms"] == [2500, 2500]
    assert result["status"] == "infrastructure_failure"
    assert result["final_time_ms"] == 5000 and result["final"]["enemy"]["active_men"] == 20


def test_controller_exception_stops_rotation_and_is_recorded(tmp_path, harness):
    class Broken(Hold):
        def decide(self, observation):
            raise ValueError("bad controller")

    harness.append(FakeMailbox([observation(0, 0), observation(1, 1000)]))
    job = tmp_path / "job"
    result = play.play(job, {**CONFIG, "episodes": 2, "results": str(tmp_path / "results.csv")},
                       policy_factory=Broken)
    assert result["status"] == "stopped" and len(result["episodes"]) == 1
    assert result["episodes"][0]["status"] == "policy_failure"
    assert harness[0].controls == []


def test_interrupted_trial_is_kept_in_manifest_and_register(tmp_path, harness):
    class Interrupted(Hold):
        def decide(self, observation):
            raise KeyboardInterrupt

    harness.append(FakeMailbox([observation(0, 0), observation(1, 1000)]))
    job, register = tmp_path / "job", tmp_path / "results.csv"
    with pytest.raises(KeyboardInterrupt):
        play.play(job, {**CONFIG, "results": str(register)}, policy_factory=Interrupted)
    manifest = json.loads((job / "manifest.json").read_text())
    assert manifest["episodes"][0]["status"] == "interrupted"
    assert next(csv.DictReader(register.open()))["outcome"] == "interrupted"


def test_tick_integrals_override_controller_sample_bias():
    result = {}
    play.track_objectives(result, {
        "mode": {"capture_points": [{"id": "c1", "holder": "enemy", "victory": True}]},
        "evaluation": {"objectives": {"c1": {"key": "major_key_building", "held_ms": 9000,
                                                "observed_ms": 10000}}},
    })
    assert result["objectives"]["victory_held"] == .9
    assert result["objectives"]["key_held"] == .9
    assert result["objectives"]["method"] == "engine_tick_time_weighted"


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
    assert mailbox.menu == play.scenario_steps(play.load_scenario({"scenario": "kho5-dwf5"}))
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
    assert b"\r" not in results.read_bytes()  # LF like Spire's register, not csv's CRLF
    assert rebuilt.read_bytes() == results.read_bytes()


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
    assert manifest["status"] == "setup_failure" and manifest["episodes"] == []
    assert "failed" in (tmp_path / "job/menu.log").read_text()


@pytest.mark.parametrize("failure,status", [
    (MailboxTimeout("frontend did not report in"), "infrastructure_failure"),
    (RuntimeError("source changed"), "infrastructure_failure"),
    (KeyboardInterrupt(), "interrupted"),
])
def test_startup_failure_preserves_its_cause(tmp_path, harness, monkeypatch, failure, status):
    harness.append(FakeMailbox([]))

    def fail(*args):
        raise failure

    monkeypatch.setattr(play, "start_frontend", fail)
    with pytest.raises(type(failure)):
        play.play(tmp_path / "job", {**CONFIG, "results": str(tmp_path / "r.csv")},
                  policy_factory=Hold)
    manifest = json.loads((tmp_path / "job/manifest.json").read_text())
    assert manifest["status"] == status and manifest["episodes"] == []
    assert manifest["error"] == (str(failure) or type(failure).__name__)
    assert manifest["error_type"] == type(failure).__name__


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
    steps = play.scenario_steps(play.load_scenario({"scenario": "kho5-dwf5"}))
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
    assert steps[-4]["find"] == ["start_button_frame", "button_start_battle"]
    assert steps[-1] == {"log": play.NOT_STARTED}
    for name, scenario in json.loads(play.SCENARIOS_PATH.read_text()).items():
        if not scenario.get("random"):
            steps = play.scenario_steps(scenario)
            assert len([s for s in steps if s.get("dblclick")]) == sum(
                len(side["units"]) for side in play.sides(scenario))


def test_mount_is_selected_after_recruitment_and_pinned_budget_before_it():
    scenario = play.load_scenario({"scenario": "brt-cavalry-emp-pikes"})
    steps = play.scenario_steps(scenario)
    recruit = next(i for i, s in enumerate(steps) if s.get("dblclick"))
    mount = next(i for i, s in enumerate(steps) if "ChangeMount(" in s.get("command", ""))
    budgets = [i for i, s in enumerate(steps) if "SetCustomFundsAmount(" in s.get("command", "")]
    assert budgets[0] < recruit < mount < budgets[-1]
    assert steps[mount + 2]["expect"] == "wh_main_brt_cha_lord_4"
    assert steps[mount + 2]["required"]


def test_battle_type_scenarios_select_the_type_slots_and_roles():
    scenarios = json.loads(play.SCENARIOS_PATH.read_text())
    steps = play.scenario_steps(scenarios["siege-kho5-dwf5"])
    finds = [s.get("find") for s in steps]
    assert ["map_type_list", "CcoBattleTypeRecordsiege"] in finds
    # A survival battle before this one removed the AI slot; it is added back only then.
    add = [s for s in steps if s.get("find") == ["bottom_team_parent", "button_add_ai"]]
    assert [s["when"] for s in add] == [play.LOBBY + "PlayerSlotList.Size < 2"]
    swap = next(s for s in steps if s.get("find", [""])[-1] == "button_swap_attacker_defender")
    assert swap["when"] == play.PLAYER_ATTACKS  # the player defends: swap only if attacking
    assert finds.index(swap["find"]) < finds.index(["teams_parent",
                                                    "CcoCustomBattlePlayerSlotslot1"])

    ffa = play.scenario_steps(scenarios["ffa-kho5-dwf5-emp5-kho5"])
    add = [s["when"] for s in ffa if s.get("find") == ["bottom_team_parent", "button_add_ai"]]
    assert add == [play.LOBBY + f"PlayerSlotList.Size < {n}" for n in (2, 3, 4)]
    slots = [s["find"][1] for s in ffa if s.get("find", [""])[0] == "teams_parent"]
    assert slots == [f"CcoCustomBattlePlayerSlotslot{n}" for n in (0, 1, 2, 3, 0)]
    assert not any("swap" in s.get("find", [""])[-1] for s in ffa)

    survival = play.scenario_steps(scenarios["survival-kho5"])
    assert not any(s.get("find") == ["bottom_team_parent", "button_add_ai"] for s in survival)
    removes = [s for s in survival if s.get("find", [""])[-1] == "button_remove"]
    assert removes[-1]["find"][0] == "CcoCustomBattlePlayerSlotslot1"
    assert removes[-1]["when"] == play.LOBBY + "PlayerSlotList.Size > 1"


def test_a_random_scenario_draws_a_map_and_races_and_autogenerates_both_armies():
    config = {"scenario": "random", "seed": 7}
    draw = play.load_scenario(config)
    assert draw == play.load_scenario({"scenario": "random", "seed": 7})
    catalogue = json.loads(play.CATALOGUE_PATH.read_text())
    assert draw["map"] in catalogue["maps"]
    for side in ("player", "enemy"):
        assert draw[side]["subculture"] in catalogue["races"]
        assert draw[side]["units"] is None and "faction" not in draw[side]
    steps = play.scenario_steps(draw)
    finds = [s.get("find") for s in steps]
    # The faction only changes banner colours, so a draw leaves it to the game.
    assert not any(f and f[0] == "dropdown_context_scroll" for f in finds)
    assert ["map_type_list", "CcoBattleTypeRecordclassic"] in finds
    assert ["map_listview", "CcoCustomBattleMap" + draw["map"]] in finds
    assert finds.count(["clear_autogen_parent", "button_autogen"]) == 2
    assert not any(s.get("dblclick") for s in steps)
    unseeded = {"scenario": "random", "seed": None}
    play.load_scenario(unseeded)
    assert isinstance(unseeded["seed"], int)
    assert "wh_dlc03_sc_bst_beastmen" not in catalogue["races"]


@pytest.mark.parametrize("name,running", [("attack_nearest", False), ("rush_nearest", True)])
def test_nearest_baselines_reorder_lapsed_attacks_and_skip_the_dead(name, running):
    policy = controllers.controller_class(name)()
    first = observation(1, 1000)
    assert policy.decide(first) == [{"unit": "f1", "type": "attack", "target": "e1",
                                     "run": running}]
    assert policy.metadata()["type"] == name
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
    assert manifest["status"] == "infrastructure_failure" and manifest["episodes"] == []
    assert manifest["error_type"] == "ValueError" and "unpaused at 1x" in manifest["error"]


@pytest.mark.parametrize("policy,prompt", [
    ("commander", commander.PROMPT_PATH), ("llm", llm.SYSTEM_PROMPT_PATH),
    ("llm_rules", llm.RULES_PROMPT_PATH),
])
def test_model_jobs_snapshot_their_prompt_and_record_their_model(tmp_path, harness, policy, prompt):
    harness.append(FakeMailbox([observation(0, 0), observation(1, 1000, result="won")]))
    results = tmp_path / "r.csv"
    config = {**CONFIG, "policy": policy, "model": "gpt-6-luna", "effort": "low",
              "results": str(results)}
    job = tmp_path / f"{policy}-luna-v1-20261013"
    assert play.play(job, config, policy_factory=Hold)["status"] == "completed"
    assert (job / "system_prompt.md").read_bytes() == prompt.read_bytes()
    item = next(csv.DictReader(results.open()))
    assert (item["policy"], item["model"], item["effort"], item["harness"]) == (
        policy, "gpt-6-luna", "low", "1")
    assert f"policy {policy} gpt-6-luna/low" in digest.digest(job)


def test_random_jobs_record_their_draw_and_keep_the_menu_dumps(tmp_path, harness):
    mailbox = FakeMailbox([observation(0, 0), observation(1, 1000, result="won")])
    mailbox.directory = tmp_path / "bridge"
    mailbox.directory.mkdir()
    (mailbox.directory / "map_list.txt").write_text("list_box\n")
    mailbox.menu_outcome = "step 4: dumped 1 lines to map_list.txt\ndone"
    harness.append(mailbox)
    config = {**CONFIG, "scenario": "random", "seed": 3, "results": str(tmp_path / "r.csv")}
    job = tmp_path / "job"
    manifest = play.play(job, config, policy_factory=Hold)
    assert manifest["scenario"] == play.load_scenario({"scenario": "random", "seed": 3})
    assert mailbox.menu == play.scenario_steps(manifest["scenario"])
    assert (job / "map_list.txt").read_text() == "list_box\n"
    assert f"seed 3: {manifest['scenario']['player']['subculture']} vs" in digest.digest(job)


def test_a_battle_with_the_wrong_role_is_not_scored(tmp_path):
    scenario = json.loads(play.SCENARIOS_PATH.read_text())["siege-kho5-dwf5"]
    expect = play.expected_mode(scenario)
    assert expect == {"type": "settlement_standard", "role": "defender"}
    assert play.expected_mode(json.loads(play.SCENARIOS_PATH.read_text())["kho5-dwf5"]) == {}
    state = observation(2, 1000)
    state["mode"] = {"type": "settlement_standard", "role": "attacker"}
    result = play.play_episode(tmp_path / "e", CONFIG, Hold(),
                               FakeMailbox([observation(1, 0), state]), not_battle=None,
                               expect=expect)
    assert result["status"] == "unsupported_or_invalid"
    assert result["mode"] == {"type": "settlement_standard", "role": "attacker"}
    assert "role is 'attacker'" in result["error"]
    wrong_type = observation(2, 1000)
    wrong_type["mode"] = {"type": "land_normal", "role": "defender"}
    result = play.play_episode(tmp_path / "f", CONFIG, Hold(),
                               FakeMailbox([observation(1, 0), wrong_type]), not_battle=None,
                               expect=expect)
    assert "type is 'land_normal', the scenario wants 'settlement_standard'" in result["error"]


def test_a_start_click_that_starts_no_battle_stops_the_job_with_the_lobbys_reason(
        tmp_path, harness):
    mailbox = FakeMailbox([])
    mailbox.directory = tmp_path / "bridge"
    mailbox.directory.mkdir()
    (mailbox.directory / "army_player.txt").write_text("recruited army\n")
    mailbox.menu_outcome = (
        "step 44: dumped 1 lines to army_player.txt\n"
        "step 45: found start_button_frame/button_start_battle, clicked\nstep 46: wait 20000 ms"
        "\nstep 47: CustomBattleLobbyContext.ReadyStatusText = [[col:red]]You must select some"
        " reinforcing units.[[/col]]\n\n[[col:red]]Players preventing ready up:"
        f"\nstep 48: log {play.NOT_STARTED}\ndone")
    harness.append(mailbox)
    with pytest.raises(play.ProtocolError,
                       match="did not start: You must select some reinforcing units."):
        play.play(tmp_path / "job", {**CONFIG, "results": str(tmp_path / "r.csv")},
                  policy_factory=Hold)
    assert (tmp_path / "job/army_player.txt").read_text() == "recruited army\n"


def test_domination_and_survival_sides_get_an_autogenerated_reinforcing_army():
    scenarios = json.loads(play.SCENARIOS_PATH.read_text())
    for name, count in (("domination-kho5-dwf5", 2), ("survival-kho5", 1), ("siege-kho5-dwf5", 0)):
        finds = [s.get("find") for s in play.scenario_steps(scenarios[name])]
        assert finds.count(["clear_autogen_reinforcement_parent",
                            "button_autogen_reinforcements"]) == count


def test_episodes_measure_victory_points_held_supplies_left_and_purchases():
    result = {}
    for holders, supplies in ((["us", "us"], 900), (["us", "enemy"], 1200), ([None, "enemy"], 300)):
        play.track_objectives(result, {"mode": {"supplies": supplies, "capture_points": [
            {"id": f"c{i}", "holder": holder, "victory": True} for i, holder in enumerate(holders)
        ] + [{"id": "c9", "holder": "enemy", "victory": False}]}})
    assert result["objectives"]["samples"] == 3 and result["objectives"]["victory_held"] == 0.5
    assert result["objectives"]["supplies_left"] == 300
    long = {}
    for held in [True] * 2000 + [False] * 2000:  # a long battle: no rounding drift
        play.track_objectives(long, {"mode": {"capture_points": [
            {"id": "c1", "holder": "us" if held else "enemy", "victory": True}]}})
    assert long["objectives"]["victory_held"] == 0.5
    play.track_objectives(result, {"mode": {}})  # no objectives: nothing changes
    assert result["objectives"]["samples"] == 3
    empty = {}
    play.track_objectives(empty, {"mode": {"type": "land_normal"}})
    assert empty == {}
    siege = {}
    for key_holder in ("us", "enemy", "us", "us"):
        play.track_objectives(siege, {"mode": {"capture_points": [
            {"id": "c1", "key": "major_key_building_leadership", "holder": key_holder,
             "victory": True},
            {"id": "c2", "key": "minor_point_supplies", "holder": "us", "victory": True}]}})
    assert siege["objectives"]["key_held"] == 0.75
    assert siege["objectives"]["victory_held"] == 0.875
    conquest = {}
    play.track_objectives(conquest, {"mode": {"tickets": [{"side": "us", "tickets": 600},
                                                          {"side": "enemy", "tickets": 87}]}})
    assert conquest["objectives"]["tickets"] == {"us": 600, "enemy": 87}


def test_acknowledged_builds_and_reinforcements_are_counted(tmp_path):
    class Buyer(Hold):
        def decide(self, observation):
            return [{"unit": "army", "type": "build", "slot": "s1", "option": "tower_1"},
                    {"unit": "army", "type": "reinforce", "reinforcement": "hounds", "zone": 6}]

    states = [observation(0, 0), observation(1, 1000), observation(2, 2000, ack=True),
              observation(3, 3000, result="lost")]
    for state in states:
        state["mode"] = {"supplies": 2000, "spawn_zones": [{"id": 6, "x": 0, "z": 0}],
                         "reinforcements": [{"type": "hounds", "cost": 500}],
                         "slots": [{"id": "s1", "usable": True,
                                    "options": [{"name": "tower_1", "cost": 500}]}]}
    result = play.play_episode(tmp_path / "e", CONFIG, Buyer(), FakeMailbox(states),
                               not_battle=None)
    assert result["objectives"]["build"] == 1 and result["objectives"]["reinforce"] == 1
    assert result["objectives"]["supplies_left"] == 2000


def test_random_draws_of_battle_types_and_the_old_classic_draws_stay_the_same():
    # A draw played before battle types existed (seed 2028855463, 2026-10-13).
    assert play.load_scenario({"scenario": "random", "seed": 2028855463}) == {
        "map": "battle_preset_devastation_volcano_01_09",
        "player": {"subculture": "wh2_main_sc_def_dark_elves", "units": None},
        "enemy": {"subculture": "wh3_main_sc_nur_nurgle", "units": None}}
    catalogue = json.loads(play.CATALOGUE_PATH.read_text())
    siege = play.load_scenario({"scenario": "random-siege", "seed": 5})
    assert siege["map"] in catalogue["battle_type_maps"]["siege"]
    assert siege["battle_type"] == "siege" and siege["attacker"] == "enemy"
    assert play.expected_mode(siege) == {"type": "settlement_standard", "role": "defender"}
    ffa = play.load_scenario({"scenario": "random-ffa", "seed": 5})
    assert len(play.sides(ffa)) == 4
    survival = play.load_scenario({"scenario": "random-survival", "seed": 5})
    assert survival["enemy"] is None and survival["player"]["reinforcements"] is None
    steps = play.scenario_steps(survival)
    finds = [s.get("find") for s in steps]
    assert finds.count(["clear_autogen_reinforcement_parent",
                        "button_autogen_reinforcements"]) == 1
    domination = play.load_scenario({"scenario": "random-domination", "seed": 5})
    assert all("reinforcements" in side for side in play.sides(domination))


def test_an_older_register_gets_the_new_columns_before_the_next_row(tmp_path, harness):
    results = tmp_path / "r.csv"
    old_fields = stats.FIELDS[:stats.FIELDS.index("battle_type")]
    results.write_text(",".join(old_fields) + "\n" + ",".join(["x"] * len(old_fields)) + "\n")
    mailbox = FakeMailbox([observation(0, 0), observation(1, 1000, result="won")])
    harness.append(mailbox)
    play.play(tmp_path / "job", {**CONFIG, "results": str(results)}, policy_factory=Hold)
    rows = list(csv.DictReader(results.open()))
    assert list(rows[0]) == stats.FIELDS and rows[0]["battle_type"] == ""
    assert rows[1]["battle_type"] == "classic" and rows[1]["outcome"] == "won"
