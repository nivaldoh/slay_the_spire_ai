"""The job loop in twwarhammer3/battle/play.py against a fake mailbox and game: episodes,
restarts, failures, objectives and register rows. Some tests end by reading the job back with
digest or stats, which checks what play writes for them."""
import csv
import json
from contextlib import nullcontext

import pytest
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation, observation

from gameai.ledger import BudgetExhausted
from gameai.llm import APIError
from twwarhammer3.battle import commander, digest, llm, play, report, setup, stats
from twwarhammer3.battle.scripted import AttackNearest, Hold
from twwarhammer3.protocol import MailboxTimeout, PolicyFailure


def test_episode_decides_waits_for_the_ack_and_the_interval_then_records_the_result(tmp_path):
    mailbox = FakeMailbox([
        bridge_observation(0, 0, phase="Loading", enemy=False),
        bridge_observation(1, 0, phase="Deployment"),
        bridge_observation(2, 1000),
        bridge_observation(3, 2000, ack=True),
        bridge_observation(4, 4000),
        bridge_observation(5, 6500),
        bridge_observation(6, 7500, ack=True),
        bridge_observation(7, 9000, result="won"),
    ])
    result = play.play_episode(tmp_path / "episode-0000", CONFIG, AttackNearest, mailbox,
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
        play.play(tmp_path / "job", config, makers={"attack_nearest": Hold})
    with pytest.raises(ValueError, match="unpaused at 1x"):
        play.play_episode(tmp_path / "episode", config, Hold, FakeMailbox([]), not_battle=None)
    assert not (tmp_path / "job").exists()
    assert not (tmp_path / "episode").exists()


def test_a_refused_benchmark_declaration_creates_no_job_directory(tmp_path, harness):
    config = {**CONFIG, "scenario": "brt-cavalry-emp-assault", "episode_timeout": 1200}
    with pytest.raises(ValueError, match="exceed a finite game timer"):
        play.play(tmp_path / "job", config, makers={"attack_nearest": Hold})
    assert not (tmp_path / "job").exists()


def test_uncommitted_sources_create_no_job_directory(tmp_path, harness, monkeypatch):
    def refuse(purpose, paths):
        raise ValueError(f"Commit implementation changes before {purpose}")

    monkeypatch.setattr(play, "committed_revision", refuse)
    with pytest.raises(ValueError, match="Commit implementation changes"):
        play.play(tmp_path / "job", CONFIG, makers={"attack_nearest": Hold})
    assert not (tmp_path / "job").exists()


@pytest.mark.parametrize("change", [{"awaiting_orders": True}, {"speed": 0.5}])
def test_incompatible_live_observation_stops_before_a_policy_decision(tmp_path, change):
    mailbox = FakeMailbox([bridge_observation(0, 0), {**bridge_observation(1, 1000), **change}])
    result = play.play_episode(tmp_path / "e", CONFIG, Hold, mailbox, not_battle=None)
    assert result["status"] == "unsupported_or_invalid"
    assert "unpaused 1x" in result["error"]
    assert result["decisions"] == 0 and mailbox.requests == []


def test_default_has_no_wait_and_uses_ack_observation_for_next_decision(tmp_path):
    mailbox = FakeMailbox([
        bridge_observation(0, 0), bridge_observation(1, 1000),
        bridge_observation(2, 2000, ack=True), bridge_observation(3, 3000, ack=True, result="won"),
    ])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0}, Hold,
                               mailbox, not_battle=None)
    assert [r[1] for r in mailbox.requests] == [1, 2]
    assert result["decisions"] == 2 and result["delays_ms"] == [500, 500]
    events = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").read_text().splitlines()]
    assert [e["kind"] for e in events][-2:] == ["ack", "result"]
    observations = [e for e in events if e["kind"] == "observation"]
    assert observations[1]["since_previous_applied_ms"] == 500


# JUDGEMENT: Acknowledgement identity — Codex, 2026-10-23: propose wrong/repeated-request checks.
# Happy-path acknowledgements alone miss premature dispatch across the mailbox identity boundary.
# This component check does not establish live delivery or order effects.
def test_unrelated_and_repeated_acks_do_not_complete_the_pending_request(tmp_path):
    class Reader(Hold):
        def __init__(self):
            self.seen, self.feedback = [], []

        def decide(self, observation):
            self.seen.append(observation["seq"])
            return [{"unit": "f1", "type": "halt"}]

        def acknowledge(self, ack, latency):
            self.feedback.append(ack)

    first_ack = {"request": "r1", "based_on": 1, "applied_ms": 2500,
                 "results": [{"index": 1, "unit": "f1", "ok": True}]}
    second_ack = {"request": "r2", "based_on": 3, "applied_ms": 4500,
                  "results": [{"index": 1, "unit": "f1", "ok": True}]}
    mailbox = FakeMailbox([
        bridge_observation(0, 0), bridge_observation(1, 1000),
        {**bridge_observation(2, 2000), "orders": {**first_ack, "request": "unrelated",
                                                 "applied_ms": 1500}},
        {**bridge_observation(3, 3000), "orders": first_ack},
        {**bridge_observation(4, 4000), "orders": first_ack},
        {**bridge_observation(5, 5000, result="won"), "orders": second_ack},
    ])
    reader = Reader()

    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0},
                               lambda: reader, mailbox, not_battle=None)

    assert result["status"] == "won"
    assert reader.seen == [1, 3]
    assert mailbox.requests == [
        ("b1", 1, [{"unit": "f1", "type": "halt"}]),
        ("b1", 3, [{"unit": "f1", "type": "halt"}]),
    ]
    assert reader.feedback == [first_ack, second_ack]
    assert result["delays_ms"] == [1500, 1500]


def test_silence_is_an_infrastructure_failure_and_a_new_battle_a_restart(tmp_path):
    result = play.play_episode(tmp_path / "a", CONFIG, Hold,
                               FakeMailbox([bridge_observation(0, 0)]), not_battle=None)
    assert result["status"] == "infrastructure_failure" and "no observation" in result["error"]
    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(0, 0, battle="b2")])
    result = play.play_episode(tmp_path / "b", CONFIG, Hold, mailbox, not_battle=None)
    assert result["status"] == "infrastructure_failure" and "b2" in result["error"]


@pytest.mark.parametrize("status", ["won", "lost", "draw"])
def test_expired_countdown_preserves_engine_outcome_after_timer_resets(tmp_path, status):
    timer = {"observed_ms": 1204100, "remaining_ms": 945.6787109375,
             "deadline_ms": 1205045.6787109375, "expired": True, "source": "countdown_deadline"}
    terminal = {**bridge_observation(2, 1205200, result=status), "remaining_ms": -1, "timer": timer}
    mailbox = FakeMailbox([bridge_observation(0, 0), terminal])
    result = play.play_episode(tmp_path / "e", CONFIG, Hold, mailbox, not_battle=None)
    assert result["status"] == status and result["ended_by"] == "time_limit"
    assert result["timer"] == timer and result["remaining_ms"] == -1
    assert not mailbox.requests


def test_unlimited_or_unexpired_timer_does_not_imply_timeout(tmp_path):
    for name, timer in (("unlimited", None), ("early", {"expired": False})):
        terminal = {**bridge_observation(2, 3000, result="lost"), "remaining_ms": -1,
                    "timer": timer}
        result = play.play_episode(tmp_path / name, CONFIG, Hold,
                                   FakeMailbox([bridge_observation(0, 0), terminal]),
                                   not_battle=None)
        assert result["status"] == "lost" and result["ended_by"] == "engine_result"


@pytest.mark.parametrize("order, error", [
    ({"unit": "f9", "type": "halt"}, "f9"),
    ({"unit": "f1", "type": "halt", "x": float("nan")}, "finite"),
])
def test_illegal_scripted_orders_are_counted_and_not_sent(tmp_path, order, error):
    class Broken(Hold):
        def __init__(self):
            self.feedback = []

        def decide(self, observation):
            return [order]

        def acknowledge(self, ack, latency):
            self.feedback.append((ack, latency))

    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000),
                           bridge_observation(2, 2000, ack=True),
                           bridge_observation(3, 3000, result="draw")])
    policy = Broken()
    result = play.play_episode(tmp_path / "e", CONFIG, lambda: policy, mailbox, not_battle=None)
    assert result["status"] == "draw" and result["invalid"] == 1
    assert [request[2] for request in mailbox.requests] == [[]]
    assert error in policy.feedback[0][0]["validation_error"]
    assert policy.feedback[0][0]["results"][0]["ok"] is False
    assert policy.feedback[0][1]["delay_ms"] == 500


def test_quiet_decisions_of_a_fast_policy_are_logged_once_per_observe_interval(tmp_path):
    class Fast(Hold):
        closed = False

        def decide(self, observation):
            return [{"unit": "f1", "type": "halt"}] if observation["time_ms"] == 1500 else []

        def close(self):
            self.closed = True

    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 250)]
                          + [bridge_observation(i, 250 * i, ack=True) for i in range(2, 9)]
                          + [bridge_observation(9, 2250, ack=True, result="won")])
    policy = Fast()
    result = play.play_episode(tmp_path / "e", {**CONFIG, "interval_ms": 0}, lambda: policy,
                               mailbox, not_battle=None)
    assert result["decisions"] == 8 and len(result["delays_ms"]) == 8 and policy.closed
    events = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").read_text().splitlines()]
    assert [e["time_ms"] for e in events if e["kind"] == "decision"] == [250, 1250, 1500]
    assert [e["kind"] for e in events].count("observation") == 3
    assert [e["kind"] for e in events].count("ack") == 3


def test_a_failed_decision_sends_nothing_and_the_controller_is_asked_again(tmp_path):
    # The battle never waits. The report still counts the failed response: it once missed
    # bench-b23-s1-kimi-low-20261017's, whose failure dict had dropped the attempts.
    attempt = {"response_id": "r1", "status": "failed", "seconds": 2,
               "error": "openrouter returned a failed response r1"}

    class Flaky(Hold):
        def __init__(self):
            self.seen = []

        def decide(self, observation):
            self.seen.append(observation["seq"])
            if len(self.seen) == 1:
                raise PolicyFailure("No valid reply after declared retries")
            if len(self.seen) == 2:
                error = APIError(attempt["error"], retryable=True)
                error.attempt, error.attempts = attempt, [attempt]
                raise error
            return []

    policy = Flaky()
    mailbox = FakeMailbox([bridge_observation(i, 1000 * i) for i in range(4)]
                          + [bridge_observation(4, 4000, ack=True),
                             bridge_observation(5, 5000, result="won")])
    result = play.play_episode(tmp_path / "e", CONFIG, lambda: policy, mailbox, not_battle=None)
    assert result["status"] == "won" and policy.seen == [1, 2, 3]
    assert [r[1] for r in mailbox.requests] == [3] and result["decisions"] == 1
    events = [json.loads(line) for line in (tmp_path / "e/trace.jsonl").open()]
    assert [e["kind"] for e in events] == ["battle", "roster"] + ["observation", "forfeit"] * 2 + [
        "observation", "decision", "ack", "result"]
    assert events[5]["failure"] == {"method": "decide", "error_type": "APIError",
                                    "attempts": [attempt]}
    metrics = report.trial_metrics(tmp_path / "e", result)
    assert metrics["reply_validation"]["failed_responses"] == 1


@pytest.mark.parametrize("late", [[{"unit": "f1", "type": "halt"}], ValueError("late bug")])
def test_a_battle_that_ends_during_a_call_keeps_its_result(tmp_path, monkeypatch, late):
    now = [100.0]
    monkeypatch.setattr(play.time, "time", lambda: now[0])
    mailbox = FakeMailbox([bridge_observation(i, 1000 * i) for i in range(3)]
                          + [bridge_observation(3, 3000, result="won")])
    mailbox.read_observation = lambda: mailbox.queue[0]  # what the game shows now

    class Slow(Hold):
        def decide(self, observation):
            while not mailbox.queue[0].get("result"):  # the battle goes on meanwhile
                mailbox.queue.popleft()
            now[0] += 30  # the result sat unread while the call went on
            if isinstance(late, Exception):
                raise late
            return late

    result = play.play_episode(tmp_path / "e", CONFIG, Slow, mailbox, not_battle=None)
    assert result["status"] == "won" and result["battle_s"] == 3
    assert mailbox.requests == [] and result["decisions"] == 0
    # The clock ratio stops at the last observation of the running battle: the wall time
    # of the straddling call is not charged to the battle clock.
    assert result["active_wall_s"] == 0
    assert result["elapsed_seconds"] == 30


def test_a_passed_episode_deadline_does_not_hide_a_result_that_is_there(tmp_path):
    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000, result="lost")])
    result = play.play_episode(tmp_path / "e", {**CONFIG, "episode_timeout": 0}, Hold, mailbox,
                               not_battle=None)
    assert result["status"] == "lost"


@pytest.mark.parametrize("method", ["acknowledge", "close"])
def test_a_controller_failure_after_the_ending_keeps_the_engine_result(tmp_path, method):
    class Late(AttackNearest):
        def acknowledge(self, ack, latency):
            if method == "acknowledge":
                raise ValueError("late bug")

        def close(self):
            if method == "close":
                raise ValueError("late bug")

    # The last observation both ends the battle and acknowledges the decision's orders.
    timer = {"expired": True, "source": "countdown_deadline"}
    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000),
                           {**bridge_observation(2, 2000, ack=True, result="won"),
                            "timer": timer}])
    play.play_episode(tmp_path / "e", CONFIG, Late, mailbox, not_battle=None)
    result = json.loads((tmp_path / "e/result.json").read_text())
    assert len(mailbox.requests) == 1
    assert result["status"] == "policy_failure" and "late bug" in result["error"]
    assert result["engine_ending"] == {"result": "won", "ended_by": "time_limit",
                                       "battle_ms": 2000, "timer": timer}
    # The scored fields are still set only after the acknowledgement, as before.
    assert ("ended_by" in result) == (method == "close")


def test_delayed_policy_gets_old_public_state_but_results_use_current_evaluation(tmp_path):
    class Reader(Hold):
        def __init__(self):
            self.inputs = []

        def decide(self, observation):
            assert "evaluation" not in observation and "final" not in observation
            assert "setup" not in observation
            self.inputs.append((observation["time_ms"], observation["friendly"][0]["x"]))
            return []

    states = [bridge_observation(0, 0)] + [bridge_observation(i, i * 1000, ack=True)
                                         for i in range(1, 6)]
    for state in states:
        # Different public positions and private totals distinguish an old policy basis
        # from current scoring evidence. Populate every excluded field, including final.
        state["friendly"][0]["x"] = state["seq"] * 10
        state["evaluation"] = {"version": 2, "friendly": {"men0": 100, "active_men": 40},
                               "enemy": {"men0": 100, "active_men": 100 - 16 * state["seq"],
                                         "units": {"registered": 5, "destroyed": 2}}}
        state["setup"] = {"private": True}
        state["final"] = {"private": "must not reach a controller"}
    reader = Reader()
    mailbox = FakeMailbox(states)
    result = play.play_episode(tmp_path / "e", {**CONFIG, "delay_ms": 2000, "interval_ms": 0},
                               lambda: reader, mailbox, not_battle=None)
    assert reader.inputs == [(1000, 10), (2000, 20), (3000, 30)]
    assert [request[1] for request in mailbox.requests] == [1, 2, 3]
    assert result["delays_ms"] == [2500, 2500]
    assert result["status"] == "infrastructure_failure"
    assert result["final_time_ms"] == 5000 and result["final"]["enemy"]["active_men"] == 20
    assert result["final"]["version"] == 2
    assert result["final"]["enemy"]["units"]["destroyed"] == 2


def test_a_contact_scored_scenario_tells_the_controller_its_scoring(tmp_path):
    class Reader(Hold):
        def __init__(self):
            self.modes = []

        def decide(self, observation):
            self.modes.append(observation.get("mode"))
            return []

    def states():
        out = [bridge_observation(0, 0)] + [bridge_observation(1, 1000, ack=True)]
        for state in out:
            state["mode"] = {"type": "land_normal", "role": "defender", "timeout_winner": "us"}
        return out

    for scenario, expected in (({"scoring": "contact"}, "contact"), ({}, None)):
        reader, observations = Reader(), states()
        play.play_episode(tmp_path / str(expected), CONFIG, lambda: reader,
                          FakeMailbox(observations), not_battle=None, scenario=scenario)
        assert reader.modes and all(mode.get("scoring") == expected for mode in reader.modes)
        assert all("scoring" not in state["mode"] for state in observations)  # a copy only


def test_controller_exception_stops_rotation_and_is_recorded(tmp_path, harness):
    class Broken(Hold):
        def decide(self, observation):
            raise ValueError("bad controller")

    harness.append(FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000)]))
    job = tmp_path / "job"
    result = play.play(job, {**CONFIG, "episodes": 2, "results": str(tmp_path / "results.csv")},
                       makers={"attack_nearest": Broken})
    assert result["status"] == "stopped" and len(result["episodes"]) == 1
    assert result["episodes"][0]["status"] == "policy_failure"
    assert harness[0].controls == []


def test_interrupted_trial_is_kept_in_manifest_and_register(tmp_path, harness):
    class Interrupted(Hold):
        def decide(self, observation):
            raise KeyboardInterrupt

    harness.append(FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000)]))
    job, register = tmp_path / "job", tmp_path / "results.csv"
    with pytest.raises(KeyboardInterrupt):
        play.play(job, {**CONFIG, "results": str(register)}, makers={"attack_nearest": Interrupted})
    manifest = json.loads((job / "manifest.json").read_text())
    assert manifest["episodes"][0]["status"] == "interrupted"
    assert next(csv.DictReader(register.open()))["outcome"] == "interrupted"


def test_objective_shares_are_the_engine_tick_integrals_not_the_observed_holder():
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



def test_a_job_stops_before_its_next_episode_when_its_source_changes(
        tmp_path, harness, monkeypatch):
    # AGENTS.md: a play job stops before its next episode if a file in its scope changes, so
    # every episode belongs to one revision. Removing the stop passed every test before
    # (runs/refusal-sweep-20261029/play.txt).
    mailbox = FakeMailbox([
        bridge_observation(0, 0), bridge_observation(1, 1000),
        bridge_observation(2, 2000, ack=True), bridge_observation(3, 3000, result="won"),
        bridge_observation(0, 0, battle="b2"), bridge_observation(3, 4000, battle="b2",
                                                                  result="lost")])
    harness.append(mailbox)
    calls = []  # the manifest's fingerprints, then one check before each episode
    monkeypatch.setattr(play, "source_fingerprints", lambda paths: calls.append(1) or (
        {} if len(calls) <= 2 else {"src/twwarhammer3/battle/play.py": "edited"}))
    job = tmp_path / "attack-v1-20261013"
    with pytest.raises(RuntimeError, match="Implementation changed during the job"):
        play.play(job, {**CONFIG, "episodes": 2, "results": str(tmp_path / "results.csv")},
                  makers={"attack_nearest": AttackNearest})
    assert json.loads((job / "episode-0000/result.json").read_text())["status"] == "won"
    assert not (job / "episode-0001").exists() and mailbox.controls == []

def test_job_plays_episodes_with_restarts_and_records_rows(tmp_path, harness):
    mailbox = FakeMailbox([
        bridge_observation(0, 0), bridge_observation(1, 1000),
        bridge_observation(2, 2000, ack=True), bridge_observation(3, 3000, result="won"),
        bridge_observation(0, 0, battle="b2"), bridge_observation(1, 500, battle="b2"),
        bridge_observation(2, 1500, battle="b2", ack=True),
        bridge_observation(3, 4000, battle="b2", result="lost"),
    ])
    harness.append(mailbox)
    results = tmp_path / "results.csv"
    config = {**CONFIG, "episodes": 2, "results": str(results)}
    manifest = play.play(tmp_path / "attack-v1-20261013", config,
                         makers={"attack_nearest": AttackNearest})
    assert manifest["status"] == "completed"
    assert [e["status"] for e in manifest["episodes"]] == ["won", "lost"]
    assert mailbox.controls == [("b1", "restart")]
    assert mailbox.menu == setup.scenario_steps(setup.load_scenario({"scenario": "kho5-dwf5"}))
    # The mod's switches stay on; the decision interval is the controller's, not the mod's.
    assert mailbox.session == {"enabled": True, "autostart": True, "menu": True, "speed": 1.0,
                               "pause": False, "observe_ms": 1000, "tick_ms": 250,
                               "record_replay": False, "stills": False}
    assert mailbox.job == "attack-v1-20261013"
    rows = list(csv.DictReader(results.open()))
    assert [(r["episode"], r["outcome"], r["policy"], r["model"], r["harness"], r["mode"],
             r["own_left"], r["enemy_left"]) for r in rows] == [
        ("episode-0000", "won", "attack_nearest", "", "1", "realtime", "0.5", "0.1"),
        ("episode-0001", "lost", "attack_nearest", "", "1", "realtime", "0.5", "0.1"),
    ]
    table = stats.summary(results)
    assert ("| kho5-dwf5 | attack_nearest |  |  | 1 | realtime | 0/5 | 2 | 1 | 1 | 0 | 0 | 4 |"
            " 0.50 | 0.10 |" in table)
    assert b"\r" not in results.read_bytes()  # LF like Spire's register, not csv's CRLF


@pytest.mark.parametrize("stop", [
    BudgetExhausted("cap"), APIError("HTTP 402: no credits"), APIError("HTTP 401: bad key"),
    APIError("Reported cost exceeded reservation; charged actual cost and stopped")])
def test_budget_exhaustion_stops_the_job(tmp_path, harness, stop):
    class Broke(Hold):
        def decide(self, observation):
            raise stop

    harness.append(FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000),
                                bridge_observation(0, 0, battle="b2")]))
    config = {**CONFIG, "episodes": 2, "results": str(tmp_path / "r.csv")}
    manifest = play.play(tmp_path / "job", config, makers={"attack_nearest": Broke})
    assert manifest["status"] == "stopped"
    assert manifest["episodes"][0]["status"] == "budget_exhausted"
    assert harness[0].controls == []


def test_a_failed_menu_step_stops_the_job_before_any_episode(tmp_path, harness):
    mailbox = FakeMailbox([bridge_observation(0, 0)])
    mailbox.menu_outcome = "step 1: not found within 240000 ms: button_battle\nfailed"
    harness.append(mailbox)
    with pytest.raises(play.ProtocolError, match="not found within 240000 ms"):
        play.play(tmp_path / "job", {**CONFIG, "results": str(tmp_path / "r.csv")},
                  makers={"attack_nearest": Hold})
    manifest = json.loads((tmp_path / "job/manifest.json").read_text())
    assert manifest["status"] == "setup_failure" and manifest["episodes"] == []
    assert "failed" in (tmp_path / "job/menu.log").read_text()


@pytest.mark.parametrize("early_completion", ["done", "menu another-request: done"])
def test_frontend_waits_for_its_own_terminal_marker_and_preserves_a_later_failure(
        tmp_path, monkeypatch, early_completion):
    mailbox = FakeMailbox([])
    settled = False
    reason = "step 1: failed: insufficient funds for swordsmen"

    def logs(offset, name="menu.log"):
        if mailbox.menu is None:
            return "frontend loaded\n"
        return reason + "\n" + early_completion + "\n" + (
            "menu menu-r: failed\n" if settled else "")

    def next_poll(seconds):
        nonlocal settled
        settled = True

    monkeypatch.setattr(mailbox, "log_since", logs)
    monkeypatch.setattr(play.time, "sleep", next_poll)
    with pytest.raises(play.ProtocolError, match="insufficient funds for swordsmen") as caught:
        play.start_frontend(mailbox, CONFIG, tmp_path, [{"log": "probe"}])
    assert settled and str(caught.value) == "custom battle setup failed: " + reason
    assert "menu menu-r: failed" in (tmp_path / "menu.log").read_text()


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
                  makers={"attack_nearest": Hold})
    manifest = json.loads((tmp_path / "job/manifest.json").read_text())
    assert manifest["status"] == status and manifest["episodes"] == []
    assert manifest["error"] == (str(failure) or type(failure).__name__)
    assert manifest["error_type"] == type(failure).__name__


def test_a_battle_observation_ends_the_menu_wait(tmp_path, harness):
    # The frontend script unloads with the loading screen, before it can log "done".
    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000, result="won")])
    mailbox.menu_outcome = "step 36: found start_button_frame/button_start_battle, clicked"
    mailbox.read_observation = lambda: bridge_observation(0, 0)
    harness.append(mailbox)
    manifest = play.play(tmp_path / "job", {**CONFIG, "results": str(tmp_path / "r.csv")},
                         makers={"attack_nearest": Hold})
    assert [e["status"] for e in manifest["episodes"]] == ["won"]


@pytest.mark.parametrize("change", [{"pause": True}, {"speed": 0.5}])
def test_attach_rejects_an_old_non_realtime_session(tmp_path, monkeypatch, harness, change):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "session.json").write_text(json.dumps({**CONFIG, **change, "job": "old"}))
    monkeypatch.setattr(play, "BRIDGE_DIR", bridge)
    with pytest.raises(ValueError, match="unpaused at 1x"):
        play.play(tmp_path / "job", {**CONFIG, "attach": True}, makers={"attack_nearest": Hold})
    manifest = json.loads((tmp_path / "job/manifest.json").read_text())
    assert manifest["status"] == "infrastructure_failure" and manifest["episodes"] == []
    assert manifest["error_type"] == "ValueError" and "unpaused at 1x" in manifest["error"]
    assert (bridge / "session.json").exists()


def test_attach_preserves_the_launch_owners_session(tmp_path, monkeypatch, harness):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    session = bridge / "session.json"
    original = json.dumps({"job": "launch-owner", "speed": 1, "pause": False})
    session.write_text(original)
    monkeypatch.setattr(play, "BRIDGE_DIR", bridge)
    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000, result="won")])
    mailbox.reset = lambda: pytest.fail("attach must not reset the launch owner's bridge")
    mailbox.owned_session = lambda _: pytest.fail("attach borrows session activation")
    harness.append(mailbox)
    result = play.play(tmp_path / "attached", {**CONFIG, "attach": True,
                                               "results": str(tmp_path / "r.csv")},
                       makers={"attack_nearest": Hold})
    assert result["status"] == "completed" and session.read_text() == original


@pytest.mark.parametrize("policy,prompt", [
    ("commander", commander.PROMPT_PATH), ("llm", llm.SYSTEM_PROMPT_PATH),
    ("llm_rules", llm.RULES_PROMPT_PATH),
])
def test_model_jobs_snapshot_their_prompt_and_record_their_model(tmp_path, harness, policy, prompt):
    harness.append(FakeMailbox([bridge_observation(0, 0),
                                bridge_observation(1, 1000, result="won")]))
    results = tmp_path / "r.csv"
    config = {**CONFIG, "policy": policy, "model": "gpt-6-luna", "effort": "low",
              "results": str(results)}
    job = tmp_path / f"{policy}-luna-v1-20261013"
    assert play.play(job, config, makers={policy: Hold})["status"] == "completed"
    assert (job / f"{policy}_prompt.md").read_bytes() == prompt.read_bytes()
    manifest = json.loads((job / "manifest.json").read_text())
    assert manifest[f"{policy}_prompt_sha256"] == play.sha256(prompt)
    item = next(csv.DictReader(results.open()))
    assert (item["policy"], item["model"], item["effort"], item["harness"]) == (
        policy, "gpt-6-luna", "low", "1")
    assert f"policy {policy} gpt-6-luna/low" in digest.digest(job)


def test_random_jobs_record_their_draw_and_keep_the_menu_dumps(tmp_path, harness):
    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000, result="won")])
    mailbox.directory = tmp_path / "bridge"
    mailbox.directory.mkdir()
    (mailbox.directory / "map_list.txt").write_text("list_box\n")
    mailbox.menu_outcome = "step 4: dumped 1 lines to map_list.txt\ndone"
    harness.append(mailbox)
    config = {**CONFIG, "scenario": "random", "seed": 3, "results": str(tmp_path / "r.csv")}
    job = tmp_path / "job"
    manifest = play.play(job, config, makers={"attack_nearest": Hold})
    assert manifest["scenario"] == setup.load_scenario({"scenario": "random", "seed": 3})
    assert mailbox.menu == setup.scenario_steps(manifest["scenario"])
    assert (job / "map_list.txt").read_text() == "list_box\n"
    assert f"seed 3: {manifest['scenario']['player']['subculture']} vs" in digest.digest(job)


def test_a_battle_with_the_wrong_role_is_not_scored(tmp_path):
    scenario = setup.load_scenario({"scenario": "siege-kho5-dwf5"})
    state = bridge_observation(2, 1000)
    state["mode"] = {"type": "settlement_standard", "role": "attacker"}
    result = play.play_episode(tmp_path / "e", CONFIG, Hold,
                               FakeMailbox([bridge_observation(1, 0), state]), not_battle=None,
                               scenario=scenario)
    assert result["status"] == "unsupported_or_invalid"
    assert result["mode"] == {"type": "settlement_standard", "role": "attacker"}
    assert "role is 'attacker'" in result["error"]
    wrong_type = bridge_observation(2, 1000)
    wrong_type["mode"] = {"type": "land_normal", "role": "defender"}
    result = play.play_episode(tmp_path / "f", CONFIG, Hold,
                               FakeMailbox([bridge_observation(1, 0), wrong_type]), not_battle=None,
                               scenario=scenario)
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
        f"\nstep 48: log {setup.NOT_STARTED}\ndone")
    harness.append(mailbox)
    with pytest.raises(play.ProtocolError,
                       match="did not start: You must select some reinforcing units."):
        play.play(tmp_path / "job", {**CONFIG, "results": str(tmp_path / "r.csv")},
                  makers={"attack_nearest": Hold})
    assert (tmp_path / "job/army_player.txt").read_text() == "recruited army\n"


def test_episodes_measure_victory_points_held_supplies_left_and_purchases():
    points = [{"id": "c1", "holder": "us", "victory": True},
              {"id": "c2", "holder": "enemy", "victory": True}]

    def state(supplies, held_ms, observed_ms):
        return {"mode": {"supplies": supplies, "capture_points": points},
                "evaluation": {"objectives": {
                    "c1": {"key": "major_key_building_leadership", "held_ms": held_ms[0],
                           "observed_ms": observed_ms},
                    "c2": {"key": "minor_point_supplies", "held_ms": held_ms[1],
                           "observed_ms": observed_ms}}}}

    result = {}
    play.track_objectives(result, state(900, (0, 0), 0))  # the first tick has no time yet
    assert result["objectives"] == {"victory_held": None, "supplies_left": 900}
    play.track_objectives(result, state(300, (3000, 4000), 4000))
    assert result["objectives"]["victory_held"] == 0.875
    assert result["objectives"]["key_held"] == 0.75
    assert result["objectives"]["supplies_left"] == 300
    play.track_objectives(result, {"mode": {}})  # no objectives: nothing changes
    assert result["objectives"]["victory_held"] == 0.875
    empty = {}
    play.track_objectives(empty, {"mode": {"type": "land_normal"}})
    assert empty == {}
    conquest = {}
    play.track_objectives(conquest, {"mode": {"tickets": [{"side": "us", "tickets": 600},
                                                          {"side": "enemy", "tickets": 87}]}})
    assert conquest["objectives"]["tickets"] == {"us": 600, "enemy": 87}


def test_acknowledged_builds_and_reinforcements_are_counted(tmp_path):
    class Buyer(Hold):
        def decide(self, observation):
            return [{"unit": "army", "type": "build", "slot": "s1", "option": "tower_1"},
                    {"unit": "army", "type": "reinforce", "reinforcement": "hounds", "zone": 6}]

    states = [bridge_observation(0, 0), bridge_observation(1, 1000),
              bridge_observation(2, 2000, ack=True), bridge_observation(3, 3000, result="lost")]
    for state in states:
        state["mode"] = {"supplies": 2000, "spawn_zones": [{"id": 6, "x": 0, "z": 0}],
                         "reinforcements": [{"type": "hounds", "cost": 500}],
                         "slots": [{"id": "s1", "usable": True,
                                    "options": [{"name": "tower_1", "cost": 500}]}]}
    result = play.play_episode(tmp_path / "e", CONFIG, Buyer, FakeMailbox(states),
                               not_battle=None)
    assert result["objectives"]["build"] == 1 and result["objectives"]["reinforce"] == 1
    assert result["objectives"]["supplies_left"] == 2000


def test_an_older_register_gets_the_new_columns_before_the_next_row(tmp_path, harness):
    results = tmp_path / "r.csv"
    old_fields = stats.FIELDS[:stats.FIELDS.index("battle_type")]
    results.write_text(",".join(old_fields) + "\n" + ",".join(["x"] * len(old_fields)) + "\n")
    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000, result="won")])
    harness.append(mailbox)
    play.play(tmp_path / "job", {**CONFIG, "results": str(results)},
              makers={"attack_nearest": Hold})
    rows = list(csv.DictReader(results.open()))
    assert list(rows[0]) == stats.FIELDS and rows[0]["battle_type"] == ""
    assert rows[1]["battle_type"] == "classic" and rows[1]["outcome"] == "won"


def test_captions_show_what_a_model_saw_and_decided():
    state = observation(36000)
    plan = {"type": "commander", "model": "gpt-6-luna", "reason": "Wait.", "plan_age_s": 6.0,
            "plan": [{"unit": "f1", "skill": "charge", "target": None, "x": None, "z": None}]}
    assert play.caption(state, plan, []) == (
        "36 s: gpt-6-luna plan from the state at 30 s\nWait.\nf1 charge")
    direct = {"type": "llm", "model": "gpt-6-luna", "reason": "Go."}
    order = {"unit": "f2", "type": "attack", "target": "e1", "mode": "melee", "run": False}
    assert play.caption(state, direct, [order]) == (
        "36 s: gpt-6-luna saw us 2/2u 111m  seen 1/2u 90m\nGo.\nf2 attack e1 melee")
    assert play.caption(state, {"type": "commander"}, []) is None


def test_a_job_rotating_two_models_of_one_policy_snapshots_its_prompt_once(tmp_path, harness):
    harness.append(FakeMailbox([
        bridge_observation(0, 0), bridge_observation(1, 1000, result="won"),
        bridge_observation(0, 0, battle="b2"), bridge_observation(1, 1000, battle="b2",
                                                                  result="lost"),
    ]))
    results = tmp_path / "r.csv"
    names = ["llm_rules", "llm_rules@gpt-6-luna/medium"]
    config = {**CONFIG, "policy": ",".join(names), "episodes": None, "rotation_seed": 1,
              "model": "gpt-6-sol", "effort": "low", "results": str(results)}
    job = tmp_path / "pair-v1-20261015"
    manifest = play.play(job, config, makers={name: Hold for name in names})
    assert manifest["status"] == "completed"
    assert sorted(path.name for path in job.glob("*_prompt.md")) == ["llm_rules_prompt.md"]
    assert "llm_rules_prompt_sha256" in manifest
    cards = {e["policy"]: (e["card"]["model"], e["card"]["effort"]) for e in manifest["episodes"]}
    assert cards == {"llm_rules": ("gpt-6-sol", "low"),
                     "llm_rules@gpt-6-luna/medium": ("gpt-6-luna", "medium")}
    rows = {(r["policy"], r["model"], r["effort"]) for r in csv.DictReader(results.open())}
    assert rows == {("llm_rules", "gpt-6-sol", "low"), ("llm_rules", "gpt-6-luna", "medium")}
    lines = digest.digest(job).splitlines()
    order = [trial["policy"] for trial in manifest["trials"]]
    assert lines[0].startswith("pair-v1-20261015: completed, policy llm_rules gpt-6-sol/low,"
                               "llm_rules@gpt-6-luna/medium gpt-6-luna/medium, scenario")
    assert [line.split(" | ")[1] for line in lines[3:]] == order


@pytest.mark.parametrize('ready', [True, False])
def test_waits_briefly_for_native_reinforcement_context_before_any_policy_call(
        tmp_path, monkeypatch, ready):
    def state(seq, ms, pool, **extra):
        o = bridge_observation(seq, ms, **extra)
        o['mode'] = {'type': 'survival', 'reinforcements': pool}
        return o
    checks = []
    def check(scenario, o):
        checks.append(o['seq'])
        if not o['mode']['reinforcements']:
            raise play.ProtocolError('reinforcement pool missing')
        return {'reinforcements': True}
    monkeypatch.setattr(play, 'check_battle', check)
    scenario = {'battle_type': 'survival', 'expect': {'time_limit_s': None},
                'player': {'reinforcements': ['reserve']}}
    pool = [{'type': 'reserve', 'cost': 500}]
    mailbox = FakeMailbox([
        bridge_observation(0, 0, phase='Loading'),
        state(1, 5600, []),
        state(2, 6000 if ready else 10600, pool if ready else []),
        state(3, 7000 if ready else 11600, pool, result='won'),
    ])
    result = play.play_episode(tmp_path / 'episode', CONFIG, Hold, mailbox,
                               not_battle=None, scenario=scenario)
    assert checks == [2]
    assert [r[1] for r in mailbox.requests] == ([2] if ready else [])
    assert result['status'] == ('won' if ready else 'unsupported_or_invalid')
    rows = [json.loads(line) for line in (tmp_path / 'episode/trace.jsonl').open()]
    assert any(r['kind'] == 'setup_wait' and r['observation']['seq'] == 1 for r in rows)


@pytest.mark.parametrize('error', [None, 'unavailable'])
def test_unconfirmed_custom_ending_is_an_infrastructure_condition_not_a_win(tmp_path, error):
    o = bridge_observation(1, 7000)
    o['mode'] = {'custom': {'status': 'success', 'ending': 'scripted',
                           'completed_ms': 1000, 'ending_error': error}}
    result = play.play_episode(tmp_path / 'episode', CONFIG, Hold,
                               FakeMailbox([bridge_observation(0, 0), o]), not_battle=None)
    assert result['status'] == 'unsupported_or_invalid'
    assert 'custom ending' in result['error']
    assert result['custom_objective']['status'] == 'success'


@pytest.mark.parametrize("stuck,message", [("frontend", "frontend script did not report in"),
                                           ("steps", "custom battle steps did not finish")])
def test_a_setup_that_never_finishes_times_out(tmp_path, monkeypatch, stuck, message):
    # Without these timeouts a stuck menu would hold an unattended queue forever; removing
    # either passed every test before (runs/refusal-sweep-20261029/play.txt).
    class Stuck(FakeMailbox):
        def log_since(self, offset, name="mod.log"):
            return "" if stuck == "frontend" else "frontend loaded\nstep 1: waiting\n"

        def read_observation(self):
            return None
    waits = []

    def sleep(seconds):
        waits.append(seconds)
        assert len(waits) < 100, "still waiting: no timeout"
    monkeypatch.setattr(play.time, "sleep", sleep)
    with pytest.raises(MailboxTimeout, match=message):
        play.start_frontend(Stuck([]), {**CONFIG, "start_timeout": 0}, tmp_path, [{"log": "x"}])


def test_a_custom_ending_error_invalidates_the_episode_before_any_later_result(tmp_path):
    # Removing this stop passed every test before (runs/refusal-sweep-20261029/play.txt).
    broken = bridge_observation(1, 1000)
    broken["mode"] = {**(broken.get("mode") or {}), "custom": {"ending_error": "script crashed"}}
    mailbox = FakeMailbox([bridge_observation(0, 0), broken,
                           bridge_observation(2, 2000, result="won")])
    result = play.play_episode(tmp_path / "e", CONFIG, Hold, mailbox, not_battle=None)
    assert result["status"] == "unsupported_or_invalid"
    assert result["error"] == "custom ending failed: script crashed"


def test_a_controller_that_fails_to_construct_is_a_policy_failure(tmp_path):
    # Removing this conversion passed every test (runs/refusal-sweep-20261029/play-ast.txt).
    def broken():
        raise ValueError("bad prompt file")
    mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000)])
    result = play.play_episode(tmp_path / "e", CONFIG, broken, mailbox, not_battle=None)
    assert result["status"] == "policy_failure"
    assert result["error"] == "controller construction: bad prompt file"


@pytest.mark.parametrize("reads,step_s,pause_ms,line", [
    (300, 1, 0, "1x by the Windows clock: 1.0000 battle s per s over 298 s, stretches of at"
                " least 30 s (longest 30 s) 1.0000-1.0000 (band 0.99-1.01)"),
    # 1.5 s paused in a 298 s battle: 0.995 overall, inside the band; its stretch is not.
    (300, 1, 1500, "WARNING: not 1x by the Windows clock: 0.9950 battle s per s over 300 s,"
                   " stretches of at least 30 s (longest 32 s) 0.9524-1.0000, outside 0.99-1.01;"
                   " tell the owner"),
    # A policy reading every 150 s: the same pause stays inside the band, and the line says
    # how long its stretches were (the limit in play.py's 1x windows marker).
    (4, 150, 1500, "1x by the Windows clock: 0.9950 battle s per s over 302 s, stretches of at"
                   " least 30 s (longest 152 s) 0.9901-1.0000 (band 0.99-1.01)"),
    (20, 1, 0, None),  # 18 s from the start: too short to judge
    (300, 1, None, None),  # no observation files, so no write times
])
def test_battle_time_per_windows_second_is_recorded_and_digest_flags_a_pause(
        tmp_path, reads, step_s, pause_ms, line):
    class Stamped(FakeMailbox):
        def wait_observation(self, **kwargs):
            observation = super().wait_observation(**kwargs)
            if pause_ms is not None:  # the file's NTFS time: battle time, the pause added
                ms = observation["time_ms"]
                self.written_ns = (ms + (pause_ms if ms >= 150000 + step_s * 500 else 0)) * 10**6
            return observation

    mailbox = Stamped([bridge_observation(i, step_s * 1000 * i) for i in range(reads)]
                      + [bridge_observation(reads, step_s * 1000 * reads, result="won")])
    job = tmp_path / "job"
    job.mkdir()
    result = play.play_episode(job / "episode-0000", CONFIG, Hold, mailbox, not_battle=None)
    (job / "manifest.json").write_text(json.dumps({
        "status": "completed", "created_at": "2026-10-29T00:00:00", "source_revision": "abc1234",
        "config": {"policy": "hold", "scenario": "s", "model": None, "effort": None,
                   "seed": None}}))
    episode, header = digest.digest(job / "episode-0000"), digest.digest(job).splitlines()[0]
    if line is None:
        assert "windows_clock_ratio" not in result and "Windows clock" not in episode
    else:
        assert line in episode.splitlines()
    assert header.startswith("WARNING") == (line or "").startswith("WARNING")


@pytest.mark.parametrize("ratio,stretches,inside", [
    (0.99, [0.99, 1.01], True), (0.9899, None, False), (1.0101, None, False),
    (1.0, [0.9899, 1.0], False), (1.0, [1.0, 1.0101], False),
])
def test_the_band_includes_its_edges(ratio, stretches, inside):
    result = {"windows_clock_ratio": ratio, "windows_clock_s": 60}
    if stretches:
        result.update(windows_clock_range=stretches, windows_clock_longest_s=30)
    assert digest.ran_at_1x(result) is inside
