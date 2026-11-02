"""Owner's 2026-11-02 choice: pin our toggles; record the AI's, without controlling it."""

import json
from copy import deepcopy

import pytest
from wh3_lua import load_battle, runtime

from twwarhammer3.battle import benchmark, setup
from twwarhammer3.protocol import ProtocolError


def test_friendly_scope_never_acquires_or_commands_enemy_units():
    lua = runtime()
    lua.execute("""
        function unit()
            return {skirmish=true,
                can_use_behaviour=function(self,key) return key=='skirmish' end,
                is_behaviour_active=function(self,key) return self[key] end}
        end
        friendly, enemy = unit(), unit()
        state={friendly_ids={'f1'},enemy_ids={'e1'},friendly={f1={unit=friendly,
            controller={change_behaviour_active=function(self,key,value) friendly[key]=value end}}},
            enemy={e1={unit=enemy,army={create_unit_controller=function()
                error('enemy control must never be acquired') end}}}}
    """)
    _, _, change = load_battle(lua, "BEHAVIOURS", "get", "benchmark_behaviours")
    measured = change(True, False, "friendly")
    assert measured["friendly"]["f1"]["skirmish"] is False
    assert measured["enemy"]["e1"]["skirmish"] is True
    assert lua.globals().enemy["skirmish"] is True


def test_current_enemy_choices_are_recorded_and_our_wrong_toggles_still_refuse():
    profile = setup.scenarios()[benchmark.SCENARIO]
    state = {"setup": {"unit_scale": .75, "realism": False, "player_defends": False,
                       "army_ai_stats_modifiers": [1, 1], "unit_experience": {},
                       "benchmark_behaviours": {}}, "terrain": {"rows": ["...."]},
             "armies": {side: {"faction": army["faction"]}
                        for side, army in (("player", profile["player"]),
                                          ("enemy", profile["enemy"]))}}
    for side, army, prefix in (("friendly", profile["player"], "f"),
                               ("enemy", profile["enemy"], "e")):
        roster = [{"id": f"{prefix}{i}", "type": key}
                  for i, key in enumerate(army["units"], 1)]
        state["friendly" if side == "friendly" else "enemy_roster"] = roster
        state["setup"]["unit_experience"][side] = [{"type": u["type"], "rank": 0} for u in roster]
        toggles = state["setup"]["benchmark_behaviours"][side] = {}
        for unit in roster:
            flags = {"defend": False}
            if "crossbowmen" in unit["type"]:
                flags.update(fire_at_will=True, skirmish=side == "enemy")
            toggles[unit["id"]] = {"supported": list(flags), **flags}
    actual = setup.check_battle(profile, state)
    assert actual["benchmark_behaviours"]["enemy"]["e4"]["skirmish"] is True
    wrong = deepcopy(state)
    wrong["setup"]["benchmark_behaviours"]["friendly"]["f4"]["skirmish"] = True
    with pytest.raises(ProtocolError, match="friendly/f4 skirmish"):
        setup.check_battle(profile, wrong)
    missing = deepcopy(state)
    missing["setup"]["benchmark_behaviours"]["enemy"]["e4"] = {"supported": []}
    with pytest.raises(ProtocolError, match="enemy/e4"):
        setup.check_battle(profile, missing)


def test_later_profile_edits_do_not_rewrite_a_frozen_attempt(tmp_path, monkeypatch):
    profile = setup.scenarios()[benchmark.SCENARIO]
    job = tmp_path / "job"
    episode = job / "episode-0000"
    episode.mkdir(parents=True)
    plan = {"benchmark": benchmark.VERSION, "scenario": profile, "source_revision": "frozen",
            "jobs": [{"output": str(job), "controller": "hold"}]}
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    (job / "manifest.json").write_text(json.dumps({"source_revision": "frozen", "scenario": profile,
        "config": {"scenario": benchmark.SCENARIO, "policy": "hold", "episodes": 1}}))
    (episode / "result.json").write_text(json.dumps({
        "status": "won", "policy": "hold", "battle": "b"}))
    monkeypatch.setattr(setup, "scenarios", lambda: {
        benchmark.SCENARIO: {**profile, "scenario_version": 999}})
    data = benchmark.collect(plan_path)
    assert data["rows"][0]["evidence_matches_plan"] is True
    assert data["completed"] == 1 and "provenance" not in data["error_categories"]
