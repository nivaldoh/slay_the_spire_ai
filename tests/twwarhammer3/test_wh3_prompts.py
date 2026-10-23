"""Golden prompts: the exact input each model controller sends for one compact battle.

``prompts/llm.txt`` is the second decision of ``llm`` (after notes, a salvaged reply and
an acknowledgement), ``prompts/llm_opening.txt`` the opening decision (``llm`` and
``llm_rules`` send the same input; they differ only in the system prompt) and
``prompts/commander.txt`` the commander's request after it adopted its first plan. The
system prompts are the files in ``configs/twwarhammer3/``. A refactor must leave these
bytes unchanged; after a deliberate prompt change, regenerate and review the diff:
``WH3_WRITE_PROMPTS=1 uv run --locked pytest tests/twwarhammer3/test_wh3_prompts.py``.
That command authors expectations; it does not verify them. Then rerun with
``env -u WH3_WRITE_PROMPTS uv run --locked pytest -ra tests/twwarhammer3/test_wh3_prompts.py``.
Use a disposable ``--basetemp`` under ``runs/`` for both commands.
"""

import json
import os
from pathlib import Path

from wh3_fixtures import FakeSend

from gameai.ledger import Ledger
from twwarhammer3.battle.commander import CommanderPolicy
from twwarhammer3.battle.llm import LLMPolicy

PROMPTS = Path(__file__).with_name("prompts")


def check(name: str, prompt: str) -> None:
    path = PROMPTS / f"{name}.txt"
    if os.environ.get("WH3_WRITE_PROMPTS") == "1":
        path.write_text(prompt)
    assert prompt == path.read_text()


def opening() -> dict:
    """A siege defence at 30 s with every section the renderer has."""
    return {
        "time_ms": 30000, "speed": 1, "remaining_ms": 870000, "phase": "Deployed",
        "terrain": {"x0": -48, "z0": -48, "cell_m": 32, "sample_width_m": 8,
                    "rows": ["..##", "...#", "...."]},
        "mode": {
            "type": "settlement_standard", "role": "defender", "timeout_winner": "us",
            "objectives": "Hold the victory point until the timer runs out.",
            "tickets": [{"side": "us", "tickets": 600, "per_s": 2},
                        {"side": "enemy", "tickets": 150, "per_s": 0}],
            "tickets_goal": 1000,
            "capture_points": [
                {"id": "c1", "name": "Victory Point", "x": 0, "z": 64, "holder": "us",
                 "percent": 100, "victory": True},
                {"id": "c2", "name": "Key Building", "x": 96, "z": 0, "holder": None,
                 "percent": 40, "contested": True}],
            "gates": [{"name": "Gatehouse", "x": 0, "z": -64, "hp": 80, "destroyed": False}],
            "supplies": 900,
            "reinforcements": [{"type": "wh3_main_kho_inf_chaos_warriors_0", "cost": 600}],
            "spawn_zones": [{"id": 3, "x": 0, "z": 96, "usable": True}],
            "slots": [{"id": "s1", "type": "tower", "x": -32, "z": 0, "usable": True,
                       "options": [{"name": "tower_arrow_1", "cost": 300}]}],
        },
        "army": {"currency": 120, "next_unlock": 200, "abilities": [
            {"key": "horn_of_khorne", "target": "Ground", "radius": 35, "cooldown_s": 90,
             "unlocked": True, "ready": True}]},
        "magic": {"current": 23.5, "reserve": 40},
        "friendly": [
            {"id": "f1", "type": "wh3_main_kho_cha_bloodthirster_0", "class": "lord",
             "commander": True, "x": 0.0, "z": 40.0, "bearing": 180, "men": 1, "men0": 1,
             "hp": 0.9, "ammo": 0, "ammo0": 0, "range": 0, "speed": [3.0, 5.5],
             "fatigue": "fresh", "state": ["idle"], "can_fly": True, "flying": False,
             "flight": {"can_toggle": True, "cooldown_s": 0},
             "barrier": {"hp": 300, "max_hp": 600},
             "morale": {"fraction": 0.85, "effect": "Winning combat"},
             "abilities": [
                 {"key": "roar", "target": "Self", "cooldown_s": 60, "can_use": True,
                  "ready": True},
                 {"key": "blood_rage", "target": "Self", "can_use": True, "ready": False,
                  "recharge_s": 21.6, "last_issued_ms": 20000}]},
            {"id": "f2", "type": "wh3_main_kho_inf_chaos_warriors_0", "class": "infantry",
             "x": -20.0, "z": 30.0, "bearing": 180, "men": 110, "men0": 120, "hp": 0.92,
             "ammo": 0, "ammo0": 0, "range": 0, "speed": [1.8999999761581, 3.6],
             "fatigue": "active", "state": ["moving"], "dest": [-20.0, 0.0], "width": 30,
             "attack_mode": "melee", "behaviours": {"defend": False}},
            {"id": "f3", "type": "wh3_main_kho_veh_skullcannon_0", "class": "missile_chariot",
             "x": 20.0, "z": 50.0, "bearing": 180, "men": 7, "men0": 7, "hp": 1.0,
             "ammo": 18, "ammo0": 20, "range": 200, "speed": [4.0, 6.0], "fatigue": "fresh",
             "state": []},
            {"id": "f4", "type": "wh3_main_kho_mon_khornataurs_0", "class": "monster",
             "men": 0, "men0": 6},
        ],
        "enemy": [
            {"id": "e1", "type": "wh_main_dwf_inf_dwarf_warriors_0", "class": "infantry",
             "x": 10.0, "z": -40.0, "bearing": 0, "men": 90, "men0": 100, "hp": 0.9,
             "speed": [1.5, 3.0], "state": ["moving"]},
            {"id": "e2", "type": "wh_main_grn_inf_orc_boyz", "class": "infantry",
             "alliance": 3, "x": 150.0, "z": 0.0, "bearing": 270, "men": 120, "men0": 120,
             "hp": 1.0, "state": ["idle"], "target": "e1"},
            {"id": "e3", "type": "wh_main_dwf_art_grudge_thrower", "class": "artillery",
             "x": 0.0, "z": -200.0, "bearing": 0, "men": 4, "men0": 4, "hp": 1.0,
             "range": 400, "state": []},
        ],
        "enemy_roster": [
            {"id": "e1", "type": "wh_main_dwf_inf_dwarf_warriors_0"},
            {"id": "e2", "type": "wh_main_grn_inf_orc_boyz", "alliance": 3},
            {"id": "e3", "type": "wh_main_dwf_art_grudge_thrower"},
            {"id": "e4", "type": "wh_main_dwf_inf_quarrellers_0", "dead": True},
        ],
    }


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
