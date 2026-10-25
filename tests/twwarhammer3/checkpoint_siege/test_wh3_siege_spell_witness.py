"""The siege check needs an actual buff and its expiry, even if two runs match each other."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_wh3_checkpoint_siege import SPELL, fixture, spell_witnesses
from wh3_lua import runtime


def spell_history():
    values = {}
    for tick, effect, armour in ((50, "", 30), (350, SPELL, 90), (800, "", 30)):
        unit = {"id": "1002", "side": 1, "index": 2, "effects": effect,
                "stats": f"stat_armour={armour:.2f}/{armour:.2f}"}
        values[tick] = {"battle": {"units": [unit]}}
    return values


def test_named_buff_changes_armour_then_expires():
    result = spell_witnesses(spell_history())
    assert result["pass"] and result["active_ticks"] == [350]
    assert result["first_expired_tick"] == 800


def test_a_different_unit_at_the_same_index_cannot_witness_the_buff():
    values = spell_history()
    values[350]["battle"]["units"][0]["id"] = "1003"
    values[800]["battle"]["units"][0]["id"] = "1004"
    assert not spell_witnesses(values)["pass"]


@pytest.mark.parametrize("wrong", ["other_ability", "no_armour_change", "still_active"])
def test_matching_runs_cannot_substitute_for_a_spell_witness(wrong):
    values = copy.deepcopy(spell_history())
    if wrong == "other_ability":
        values[350]["battle"]["units"][0]["effects"] = "wh_main_anc_arcane_item_power_stone"
    elif wrong == "no_armour_change":
        values[350]["battle"]["units"][0]["stats"] = "stat_armour=30.00/30.00"
    else:
        values[800]["battle"]["units"][0]["effects"] = SPELL
    assert not spell_witnesses(values)["pass"]


@pytest.mark.parametrize("matching_id", [True, False])
def test_numeric_unit_readings_keep_identity_and_existing_display_fields(matching_id):
    from lupa.lua51 import LuaError

    lua = runtime()
    lua.globals().actual_id = 1002 if matching_id else 1003
    lua.execute('''
        queries = 0
        battle = {units = {{side=1, index=2, id='1002', stats='scalar_speed=48.00/48.00',
                           morale='0.12|Confident'}}}
        local unit = {
            unique_ui_id = function() return actual_id end,
            slow_speed = function() queries=queries+1; return 1.8999999761581 end,
            fast_speed = function() queries=queries+1; return 4.8000001907349 end,
        }
        local units = {item = function(_, i) assert(i == 2); return unit end}
        local army = {units = function() return units end}
        local armies = {item = function(_, i) assert(i == 1); return army end}
        local alliance = {armies = function() return armies end}
        local alliances = {item = function(_, i) assert(i == 1); return alliance end}
        bm = {alliances = function() return alliances end}
        common = {get_context_value = function(kind, id, expression)
            assert(kind == 'CcoBattleUnit' and id == '1002' and expression == 'MoralePercent')
            queries=queries+1; return 0.12345678912345
        end}
    ''')
    if not matching_id:
        with pytest.raises(LuaError, match="unit UI id changed"):
            lua.execute(fixture("live_units.lua"))
        assert lua.globals().queries == 0
        return
    lua.execute(fixture("live_units.lua"))
    unit = lua.globals().battle["units"][1]
    assert unit["slow_speed"] == 1.8999999761581
    assert unit["fast_speed"] == 4.8000001907349
    assert unit["morale_percent"] == 0.12345678912345
    assert unit["stats"] == "scalar_speed=48.00/48.00"
    assert unit["morale"] == "0.12|Confident"
