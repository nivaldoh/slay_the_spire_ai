"""Golden prompts: the exact input each model controller sends for one compact battle.

``prompts/llm.txt`` is the second decision of ``llm`` (after notes, a salvaged reply and
an acknowledgement), ``prompts/llm_opening.txt`` the opening decision (``llm`` and
``llm_rules`` send the same input; they differ only in the system prompt) and
``prompts/commander.txt`` the commander's request after it adopted its first plan and
``prompts/team_member.txt`` the opening input of a ``team_llm_rules`` member that owns the
lord. The system prompts are the files in ``configs/twwarhammer3/``. A refactor must leave these
bytes unchanged; after a deliberate prompt change, regenerate and review the diff:
``WH3_WRITE_PROMPTS=1 uv run --locked pytest tests/twwarhammer3/test_wh3_prompts.py``.
That command authors expectations; it does not verify them. Then rerun with
``env -u WH3_WRITE_PROMPTS uv run --locked pytest -ra tests/twwarhammer3/test_wh3_prompts.py``.
Use a disposable ``--basetemp`` under ``runs/`` for both commands.
"""

import json
import os
from pathlib import Path

from wh3_fixtures import FakeSend, opening

from gameai.ledger import Ledger
from twwarhammer3.battle import team
from twwarhammer3.battle.commander import CommanderPolicy
from twwarhammer3.battle.llm import LLMPolicy

PROMPTS = Path(__file__).with_name("prompts")


def check(name: str, prompt: str) -> None:
    path = PROMPTS / f"{name}.txt"
    if os.environ.get("WH3_WRITE_PROMPTS") == "1":
        path.write_text(prompt)
    assert prompt == path.read_text()


def later() -> dict:
    """15 s on: the lord is on its way, f2 fights e1, f3's move proved unreachable and the
    grudge thrower is out of sight."""
    state = opening()
    state.update(time_ms=45000, remaining_ms=855000)
    state["magic"]["current"] = 15
    lord, warriors, cannon = state["friendly"][:3]
    lord.update(z=10.0, state=["moving", "running"], dest=[0.0, -20.0],
                command_queue=[
                    {"unit": "f1", "type": "move", "x": 0, "z": -20, "run": True},
                    {"unit": "f1", "type": "attack", "target": "e1", "mode": "melee",
                     "run": True, "queue": True}])
    lord["abilities"][0].update(ready=False, active=True, last_issued_ms=33100)
    warriors.update(z=-30.0, men=104, hp=0.85, state=["melee"], dest=None, target="e1")
    cannon["navigation"] = {"rejected": {"x": 200, "z": 300}, "sampled_ms": 33400,
                            "alternatives": [{"x": 180, "z": 260}, {"x": 150, "z": 240}]}
    state["enemy"] = state["enemy"][:2]
    state["enemy"][0].update(z=-35.0, men=82, hp=0.8, state=["melee"], target="f2")
    state["mode"]["capture_points"][1]["percent"] = 70
    return state


ORDERS = [
    {"unit": "f1", "type": "move", "x": 0, "z": -20, "facing": 180, "width": None, "run": True,
     "queue": False},
    {"unit": "f1", "type": "attack", "target": "e1", "mode": "melee", "run": True,
     "queue": True},
    {"unit": "f2", "type": "attack", "target": "e1", "mode": "melee", "run": False,
     "queue": False},
    {"unit": "f3", "type": "move", "x": 200, "z": 300, "facing": None, "width": None,
     "run": False, "queue": False},
    {"unit": "f1", "type": "ability", "ability": "roar", "target": None, "x": None, "z": None,
     "facing": None, "width": None},
    {"unit": "army", "type": "build", "slot": "s1", "option": "tower_arrow_1"},
    {"unit": "f9", "type": "halt"},  # never valid: the reply is salvaged without it
]


def test_llm_prompt_after_an_acknowledged_salvaged_reply(tmp_path):
    first = json.dumps({"orders": ORDERS, "reason": "meet them at the gate",
                        "notes": "e3 shells the walls; kill it when the gate holds"})
    agent = LLMPolicy("gpt-6-luna", "low", Ledger(tmp_path / "ledger.jsonl", 1.0),
                      send=FakeSend(first, first, first, json.dumps(
                          {"orders": [], "reason": "wait", "notes": None})))
    assert agent.decide(opening()) == ORDERS[:-1]
    agent.acknowledge({"request": "r1", "applied_ms": 33100, "results": [
        {"index": 1, "unit": "f1", "ok": True},
        {"index": 2, "unit": "f1", "ok": True, "queued": True},
        {"index": 3, "unit": "f2", "ok": True},
        {"index": 4, "unit": "f3", "ok": False, "error": "unreachable"},
        {"index": 5, "unit": "f1", "ok": True},
        {"index": 6, "unit": "army", "ok": True}]}, {"think_s": 2.4, "delay_ms": 3100})
    agent.decide(later())
    check("llm", agent.metadata()["prompt"])


def test_llm_opening_prompt(tmp_path):
    agent = LLMPolicy("gpt-6-luna", "low", Ledger(tmp_path / "ledger.jsonl", 1.0),
                      send=FakeSend(json.dumps({"orders": [], "reason": "wait", "notes": None})))
    agent.decide(opening())
    check("llm_opening", agent.metadata()["prompt"])


def test_team_member_prompt(tmp_path):
    send = FakeSend(json.dumps({"orders": [], "reason": "wait", "notes": None}))
    member = team.TeamLLM("gpt-6-luna", "low", Ledger(tmp_path / "ledger.jsonl", 1.0), send=send)
    member.decide(team.project(opening(), {"f1"}))
    prompt = member.metadata()["prompt"]
    assert send.bodies[0]["input"][0]["content"] == prompt
    check("team_member", prompt)


def test_commander_prompt_after_its_first_plan(tmp_path):
    plan = {"assignments": [
        {"unit": "f1", "skill": "charge", "target": "e1", "x": 0, "z": 0},
        {"unit": "f2", "skill": "hold", "target": None, "x": -20, "z": 0},
        {"unit": "f3", "skill": "shoot", "target": "e3", "x": None, "z": None},
        {"unit": "f9", "skill": "engage", "target": None, "x": None, "z": None}],
        "abilities": [
            {"unit": "army", "type": "ability", "ability": "horn_of_khorne", "target": None,
             "x": 10, "z": -35, "facing": None, "width": None},
            {"unit": "f1", "type": "ability", "ability": "roar", "target": None, "x": None,
             "z": None, "facing": None, "width": None}],
        "reason": "hold the gate", "notes": "e3 shells the walls"}
    agent = CommanderPolicy("gpt-6-luna", "low", Ledger(tmp_path / "ledger.jsonl", 1.0),
                            send=FakeSend(json.dumps(plan), json.dumps(plan)))
    try:
        agent.decide(opening())
        agent.pending.result(timeout=5)
        agent.acknowledge({"results": [{"index": 1, "unit": "f2", "ok": False,
                                        "error": "unit_in_melee"}]}, {})
        agent.decide(later())
    finally:
        agent.close()
    check("commander", agent.metadata()["prompt"])


def test_custom_objective_rules_and_progress_without_private_placements():
    from twwarhammer3.battle.llm import render_mode

    mode = {'type': 'land_ambush', 'custom': {
        'rules': 'Bring both batteries into the circle before 900 seconds.',
        'zone': {'x': 190, 'z': 300, 'radius': 45}, 'deadline_ms': 900000,
        'status': 'pending', 'extracted': 1,
        'assets': [{'id': 'f7', 'alive': True, 'in_zone': True},
                   {'id': 'f8', 'alive': True, 'in_zone': False}],
        'deployment': {'enemy': [{'x': 999, 'z': 888}]},
    }}
    check('evacuation_mode', render_mode(mode))
    assert '999' not in render_mode(mode)
