"""Full-run stopping and saved evidence with a fake game and bridge.

References: AGENTS.md's failure taxonomy, evidence requirements and source-change refusal.
The job contract in play.py stops after outcomes outside SCORED.
These checks exercise the Python loop; they do not test Windows process termination.
"""

import json
import time
from copy import deepcopy

import pytest
from fullrun_support import CONFIG, DEATH, MENU, ScriptedPolicy
from spire_messages import combat_message, message

from spire.decisions import Choice
from spire.engine.bridge import BridgeDisconnected
from spire.fullrun import play

# JUDGEMENT: Stop-path checks — Codex, 2026-10-23: simulated disconnect, interruption and
# source change check saved evidence and stopping; live checks could also test process exit.
# These component checks are proposed, not an agreed verification method.


def test_bridge_disconnect_saves_the_failure_and_stops_before_the_next_seed(tmp_path, harness):
    sessions, sent = harness

    def disconnect():
        raise BridgeDisconnected("relay connection closed")

    sessions += [[MENU, combat_message(), disconnect], [MENU, DEATH]]
    job = tmp_path / "job"
    config = {**CONFIG, "results": str(tmp_path / "results.csv")}

    manifest = play.play(job, config, policy_factory=ScriptedPolicy)

    assert manifest["status"] == "stopped"
    [result] = manifest["runs"]
    assert result["status"] == "infrastructure_failure"
    assert result["error_type"] == "BridgeDisconnected"
    assert result["error"] == "relay connection closed"
    assert sent == ["START IRONCLAD 0 SEEDA", "end"]
    assert not (job / "run-0001").exists()
    assert json.loads((job / "run-0000/result.json").read_text()) == result
    assert json.loads((job / "manifest.json").read_text()) == manifest


def test_interruption_keeps_finished_and_partial_runs(tmp_path, harness):
    sessions, sent = harness

    def interrupt():
        raise KeyboardInterrupt

    sessions += [[MENU, DEATH], [MENU, combat_message(), interrupt], [MENU, DEATH]]
    job = tmp_path / "job"
    config = {**CONFIG, "seeds": ["SEEDA", "SEEDB", "SEEDC"],
              "results": str(tmp_path / "results.csv")}

    with pytest.raises(KeyboardInterrupt):
        play.play(job, config, policy_factory=ScriptedPolicy)

    manifest = json.loads((job / "manifest.json").read_text())
    assert manifest["status"] == "interrupted"
    [finished] = manifest["runs"]
    assert (finished["seed"], finished["status"]) == ("SEEDA", "lost")
    assert json.loads((job / "run-0000/result.json").read_text()) == finished
    partial = json.loads((job / "run-0001/result.json").read_text())
    assert (partial["seed"], partial["status"], partial["actions"]) == ("SEEDB", "interrupted", 2)
    assert sent == ["START IRONCLAD 0 SEEDA", "START IRONCLAD 0 SEEDB", "end"]
    assert not (job / "run-0002").exists()


def test_source_change_preserves_the_finished_run_and_prevents_the_next_launch(
        tmp_path, harness, monkeypatch):
    sessions, sent = harness

    def change_sources():
        monkeypatch.setattr(play, "source_fingerprints", lambda paths: {
            "src/spire/fullrun/play.py": "changed"})

    sessions += [[MENU, change_sources, DEATH], [MENU, DEATH]]
    job = tmp_path / "job"
    config = {**CONFIG, "results": str(tmp_path / "results.csv")}

    with pytest.raises(RuntimeError, match="Implementation changed"):
        play.play(job, config, policy_factory=ScriptedPolicy)

    manifest = json.loads((job / "manifest.json").read_text())
    assert manifest["status"] == "interrupted"
    [finished] = manifest["runs"]
    assert (finished["seed"], finished["status"]) == ("SEEDA", "lost")
    assert json.loads((job / "run-0000/result.json").read_text()) == finished
    assert sent == ["START IRONCLAD 0 SEEDA"]
    assert not (job / "run-0001").exists()


# play.py truncates a run at the action limit or the run-time limit (defaults 4,000 actions and
# 5 h) and counts it as scored, so the job goes on. No doc states this: rests on JUDGEMENT
# src/spire/fullrun/play.py Scored runs. A decision in flight at the deadline is still sent.
def test_action_limit_truncates_the_run_and_the_job_goes_on(tmp_path, harness):
    sessions, sent = harness
    sessions += [[MENU, combat_message(), combat_message()], [MENU, DEATH]]
    job = tmp_path / "job"
    config = {**CONFIG, "max_actions": 2, "results": str(tmp_path / "results.csv")}

    manifest = play.play(job, config, policy_factory=ScriptedPolicy)

    assert manifest["status"] == "completed"
    truncated, finished = manifest["runs"]
    assert (truncated["status"], truncated["reason"], truncated["actions"]) == (
        "truncated", "action_limit", 2)
    assert (finished["seed"], finished["status"]) == ("SEEDB", "lost")
    assert sent == ["START IRONCLAD 0 SEEDA", "end", "START IRONCLAD 0 SEEDB"]
    assert json.loads((job / "run-0000/result.json").read_text()) == truncated


def test_run_time_limit_truncates_the_run_and_the_job_goes_on(tmp_path, harness, monkeypatch):
    sessions, sent = harness

    class Clock:  # play's monotonic clock, moved forward by the game below
        now = 0.0

        def __getattr__(self, name):
            return getattr(time, name)

        def monotonic(self):
            return self.now

    clock = Clock()
    monkeypatch.setattr(play, "time", clock)
    sessions += [[MENU, lambda: setattr(clock, "now", CONFIG["run_timeout"] + 1),
                  combat_message()], [MENU, DEATH]]
    job = tmp_path / "job"
    config = {**CONFIG, "results": str(tmp_path / "results.csv")}

    manifest = play.play(job, config, policy_factory=ScriptedPolicy)

    assert manifest["status"] == "completed"
    truncated, finished = manifest["runs"]
    assert (truncated["status"], truncated["reason"]) == ("truncated", "run_time_limit")
    assert (finished["seed"], finished["status"]) == ("SEEDB", "lost")
    assert sent == ["START IRONCLAD 0 SEEDA", "end", "START IRONCLAD 0 SEEDB"]
    assert json.loads((job / "run-0000/result.json").read_text()) == truncated


class Outsider(ScriptedPolicy):
    def choose(self, decision):
        return Choice(id="x", decision_id=decision.id, command="play 9", label="not offered")


def guard_case(name):
    """(session after the menu, policy, error, commands sent) for one loop guard."""
    debug = combat_message()
    debug["game_state"]["combat_state"]["monsters"][1]["intent"] = "DEBUG"
    settings = message(["key", "state"], screen_name="SETTINGS")
    no_flag = deepcopy(DEATH)
    del no_flag["game_state"]["screen_state"]["victory"]
    start = "START IRONCLAD 0 SEEDA"
    return {
        "choice_not_offered": ([combat_message()], Outsider,
                               "Choice is not a current candidate", [start]),
        "bridge_error": ([{"error": "Invalid command: play 9"}], ScriptedPolicy,
                         "Invalid command: play 9", [start]),
        "menu_without_outcome": ([combat_message(), MENU], ScriptedPolicy,
                                 "Main menu reached without a run outcome", [start, "end"]),
        "intents_never_settle": ([debug] * 5, ScriptedPolicy, "Enemy intents did not settle",
                                 [start] + ["wait 60"] * 3),
        "settings_never_close": ([settings] * 5, ScriptedPolicy,
                                 "The settings screen did not close", [start] + ["key cancel"] * 3),
        "game_over_without_flag": ([no_flag], ScriptedPolicy,
                                   "Game-over screen lacks a boolean victory flag", [start]),
    }[name]


# Removing any of these stops passed every test before (runs/refusal-sweep-20261029/spire-*.txt):
# a choice the game did not offer would be sent, and a run with no outcome would go on or score.
@pytest.mark.parametrize("name", ["choice_not_offered", "bridge_error", "menu_without_outcome",
                                  "intents_never_settle", "settings_never_close",
                                  "game_over_without_flag"])
def test_each_loop_guard_ends_the_run_unscored(tmp_path, harness, name):
    session, policy, error, commands = guard_case(name)
    sessions, sent = harness
    sessions.append([MENU, *session])
    config = {**CONFIG, "seeds": ["SEEDA"], "results": str(tmp_path / "results.csv")}
    manifest = play.play(tmp_path / "job", config, policy_factory=policy)
    run, = manifest["runs"]
    assert (run["status"], run["error"]) == ("unsupported_or_invalid", error)
    assert sent == commands


def test_a_save_that_is_not_a_json_object_is_refused():
    with pytest.raises(ValueError, match="A save file holds a JSON object"):
        play.decode_save(b'[{"floor": 3}]')
