"""Full-run lifecycle with a fake bridge and game; these states do not certify the engine."""

import json
from contextlib import nullcontext
from copy import deepcopy
from unittest.mock import Mock

import pytest
from test_decisions import combat_message, message

from spire.engine import doctor
from spire.fullrun import play
from spire.ledger import BudgetExhausted

MENU = {"ready_for_command": True, "in_game": False, "available_commands": ["start", "state"],
        "game_state": {}}
NEOW = message(["choose", "key", "click", "wait", "state"], screen_type="EVENT",
               choice_list=["talk"], screen_state={"options": [{"text": "[Talk]"}]})
DEATH = message(["proceed"], screen_type="GAME_OVER", screen_name="DEATH", current_hp=0,
                screen_state={"victory": False, "score": 42})


def unsettled():
    raw = combat_message()
    raw["game_state"]["combat_state"]["monsters"][1]["intent"] = "DEBUG"
    return raw


class ScriptedPolicy:
    def __init__(self, error=None):
        self.error, self.seen, self.totals = error, [], {"calls": 0}

    def choose(self, decision):
        if self.error:
            raise self.error
        self.seen.append(decision)
        self.totals["calls"] += 1
        return decision.candidates[-1]

    def choice_metadata(self, decision_id):
        return {"type": "scripted"}


@pytest.fixture
def harness(monkeypatch):
    sessions, sent = [], []

    class FakeBridge:
        def __init__(self, **kwargs):
            self.address, self.messages = (kwargs["host"], kwargs["port"]), iter(sessions.pop(0))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def receive(self):
            return deepcopy(next(self.messages))

        def send(self, command):
            sent.append(command)

    class FakeGame:
        info = {"pid": 1}

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(play, "BridgeServer", FakeBridge)
    monkeypatch.setattr(play, "OwnedGame", FakeGame)
    monkeypatch.setattr(play, "RuntimeLock", nullcontext)
    monkeypatch.setattr(play, "wsl_bridge_host", Mock(return_value="172.18.0.1"))
    monkeypatch.setattr(play, "prepare_runtime", Mock(return_value={"mods": {}}))
    monkeypatch.setattr(play, "collect_profile", Mock(return_value={"slot": 0}))
    monkeypatch.setattr(doctor, "collect_diagnostics", lambda: {"schema_version": 1})
    monkeypatch.setattr(play, "_committed_source",
                        lambda: {"source_revision": "test", "source_files": {}})
    monkeypatch.setattr(play, "source_fingerprints", lambda: {})
    return sessions, sent


CONFIG = {"seeds": ["SEEDA", "SEEDB"], "max_actions": 50, "run_timeout": 100,
          "bridge_timeout": 30}


def test_run_starts_settles_forces_single_choices_and_ends_on_death(tmp_path, harness):
    sessions, sent = harness
    sessions.append([MENU, NEOW, unsettled(), combat_message(), DEATH])
    agent = ScriptedPolicy()
    result = play.play_run(tmp_path / "run", {**CONFIG, "seed": "SEEDA"}, agent)
    assert sent == ["START IRONCLAD 0 SEEDA", "choose 0", "wait 60", "end"]
    assert (result["status"], result["score"], result["current_hp"]) == ("lost", 42, 0)
    assert (result["decisions"], result["policy_calls"], result["settle_waits"]) == (2, 1, 1)
    assert result["llm"] == {"calls": 1}
    trace = [json.loads(line) for line in (tmp_path / "run/trace.jsonl").read_text().splitlines()]
    decisions = [event for event in trace if event["kind"] == "decision"]
    assert [d["behavior"]["type"] for d in decisions] == ["forced", "scripted"]
    assert "seed" not in decisions[1]["decision"]["observation"]


def test_budget_exhaustion_ends_the_run_and_stops_the_job(tmp_path, harness):
    sessions, sent = harness
    sessions.append([MENU, combat_message()])
    manifest = play.play(tmp_path / "job", CONFIG,
                         policy_factory=lambda: ScriptedPolicy(BudgetExhausted("cap")))
    assert manifest["status"] == "stopped"
    assert [run["status"] for run in manifest["runs"]] == ["budget_exhausted"]
    assert sent == ["START IRONCLAD 0 SEEDA"]
    assert (tmp_path / "job/system_prompt.md").read_text().startswith("You are playing")
