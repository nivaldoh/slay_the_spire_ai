"""The public all-air morale warning and normal flight controls must reach the policy."""
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / (
    "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua")


def runtime():
    lua = pytest.importorskip("lupa.lua51").LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
        function get(unit, key, default)
            if unit[key] == nil then return default end
            return unit[key]
        end
    """)
    return lua


def test_morale_warning_and_flight_readiness_are_friendly_only():
    lua = runtime()
    lua.execute("""
        function round(value) return value end
        function plain(text) return string.gsub(text, "%[%[.-%]%]", "") end
        state = {friendly = {f1 = {ui_id = "1001", setup = {}}}}
        BEHAVIOURS = {}
        morale_queries = 0
        function context_rows(context, id, expression)
            if string.find(expression, "MoralePercent") then
                morale_queries = morale_queries + 1
                return {{"0.3", "[[col:red]]You must attack by land![[/col]]"}}
            elseif string.find(expression, "CanToggleFlying") then
                return {{"false", "6.5"}}
            end
            return {}
        end
    """)
    source = "local function unit_record" + SOURCE.read_text().split(
        "local function unit_record", 1)[1].split("\n-- Line of sight", 1)[0]
    record = lua.execute(source + "\nreturn unit_record")
    unit = lua.table_from({"can_fly": True, "is_currently_flying": True})
    friendly = record("f1", unit, True, "lord")
    assert dict(friendly["morale"]) == {"fraction": .3, "effect": "You must attack by land!"}
    assert dict(friendly["flight"]) == {"can_toggle": False, "cooldown_s": 6.5}
    enemy = record("e1", unit, False, "lord")
    assert enemy["morale"] is None and enemy["flight"] is None
    assert lua.globals().morale_queries == 1


def test_flight_checks_live_state_and_refuses_blocked_changes():
    lua = runtime()
    lua.execute("""
        allowed, toggles = true, 0
        common = {
            get_context_value = function(context, id, field)
                assert(context == "CcoBattleUnit" and id == "1001" and field == "CanToggleFlying")
                return allowed
            end,
            call_context_command = function(context, id, command)
                assert(context == "CcoBattleUnit" and id == "1001" and command == "ToggleFlying")
                toggles = toggles + 1
            end,
        }
    """)
    source = "local function apply_flight" + SOURCE.read_text().split(
        "local function apply_flight", 1)[1].split("local function apply_order", 1)[0]
    apply = lua.execute(source + "\nreturn apply_flight")
    unit = lua.table_from({"can_fly": True, "is_currently_flying": True})
    entry = lua.table_from({"unit": unit, "ui_id": "1001"})
    land = lua.table_from({"flying": False})
    apply(entry, land)
    assert lua.globals().toggles == 1
    lua.globals().allowed = False
    with pytest.raises(Exception, match="flight_change_unavailable"):
        apply(entry, land)
    unit["is_currently_flying"] = False  # subsequent engine observation confirms landing
    apply(entry, land)
    assert lua.globals().toggles == 1
    lua.globals().allowed = True
    apply(entry, lua.table_from({"flying": True}))
    assert lua.globals().toggles == 2
    unit["can_fly"] = False
    with pytest.raises(Exception, match="cannot_fly"):
        apply(entry, land)
