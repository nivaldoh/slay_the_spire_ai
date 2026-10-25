"""Construction must survive recorded replay input, without a restoring script rebuilding it."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_wh3_checkpoint_siege import CASES, fixture, restore_plan, source_plan, witnesses
from wh3_lua import runtime


def test_source_tower_inputs_cannot_be_reissued_by_restoring_either_saved_state():
    plan = source_plan("test", CASES["helmgart-field"])
    builds = [r for r in plan["lua_at"] if r["label"] == "build_field_towers"]
    assert len(builds) == 1 and builds[0]["tick"] == 100
    for tick in (550, 2200):
        for changed in (False, True):
            restored = restore_plan(plan, {"tick": tick}, changed)
            assert not any(r["label"] == "build_field_towers" for r in restored["lua_at"])


def test_ownership_setup_registers_only_the_two_ownership_callbacks():
    lua = runtime()
    lua.execute('''
        callbacks = {}
        bm = {local_alliance=function() return 1 end,
              alliances=function(self) return self end, item=function(self) return self end,
              armies=function(self) return self end,
              callback=function(_, fn, ms) callbacks[#callbacks+1] = ms end,
              battle={time_elapsed_ms=function() return 100 end}}
        twwarhammer3_json = {encode=function(value) return value end}
    ''')
    lua.execute(fixture("field.lua").replace("ATTACK_SIDE", "2").replace(
        "TRANSFER_OWNERSHIP", "true"))
    assert list(lua.globals().callbacks.values()) == [90000, 180000]


def build_actions():
    return [{"event": "build_tower", "slot": slot, "option": slot, "ok": True,
             "cost": cost, "supplies_before": 5000, "supplies_after": 5000-cost}
            for slot, cost in ((0, 1400), (1, 500))]


def field_values(actions):
    return {2200: {"battle": {"units": []}, "siege": {
        "assault_equipment": [], "vehicles": [], "gates": [], "captures": [], "climbing": [],
        "armies": [{"id": side, "alliance": side, "supplies": 0, "slots": []}
                   for side in (0, 1)], "actions": actions}}}


def test_persistent_reading_actions_are_not_evidence_of_source_build_inputs():
    result = witnesses(field_values(build_actions()), 2200, CASES["helmgart-field"], "late")
    assert not result["checks"]["two_tower_builds_spent_supplies"]


@pytest.mark.parametrize("wrong", [None, "option", "cost", "debit", "late", "failed"])
def test_source_lua_events_witness_the_selected_options_and_supply_costs(wrong):
    actions = build_actions()
    event = {"event": "lua", "tick": 100, "label": "build_field_towers",
             "value": {"actions": actions}}
    if wrong == "option":
        actions[0]["option"] = 1
    elif wrong == "cost":
        actions[0].update(cost=500, supplies_after=4500)
    elif wrong == "debit":
        actions[0]["supplies_after"] += 1
    elif wrong == "late":
        event["tick"] = 2250
    elif wrong == "failed":
        actions[0]["ok"] = False
    result = witnesses(field_values([]), 2200, CASES["helmgart-field"], "late", [event])
    assert result["checks"]["two_tower_builds_spent_supplies"] is (wrong is None)
