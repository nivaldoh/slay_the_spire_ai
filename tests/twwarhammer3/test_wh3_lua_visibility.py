"""Execute the enemy observation boundary against hidden state transitions in Lua."""
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / (
    "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua")


def test_hidden_arrivals_and_deaths_do_not_update_public_enemy_state():
    lua51 = pytest.importorskip("lupa.lua51")
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
        state = {info = {alliances = 2}}
        function get(object, method, default) return object[method] or default end
        function visible_to_player(unit) return unit.visible end
        function unit_record(id, unit, friendly, class)
            assert(not friendly and unit.visible and unit.number_of_men_alive > 0)
            return {id = id, men = unit.number_of_men_alive}
        end
        function clean_error(err) return tostring(err) end
        unit = {type = "summon", number_of_men_alive = 30, visible = false}
        entry = {unit = unit}
    """)
    source = SOURCE.read_text().split("local function enemy_observation(id, entry)", 1)[1]
    function = "local function enemy_observation(id, entry)" + source.split(
        "\nlocal function observation(now)", 1)[0]
    observe = lua.execute(function +
                          "\nreturn function() return enemy_observation('e7', entry) end")

    # A newly registered hidden summon is private evaluation state only.
    assert observe() == (None, None)
    # A lobby unit remains in the public roster even when initially hidden.
    lua.execute("entry.initial = true")
    roster, record = observe()
    assert roster["type"] == "summon" and record is None
    lua.execute("entry.initial = nil; unit.visible = true")
    roster, record = observe()
    assert roster["id"] == record["id"] == "e7" and record["men"] == 30

    # Seeing a unit previously must not reveal its subsequent death in fog.
    lua.execute("unit.visible = false; unit.number_of_men_alive = 0")
    roster, record = observe()
    assert roster["dead"] is None and record is None
    # A death actually visible to the alliance may be retained as knowledge.
    lua.execute("unit.visible = true")
    roster, record = observe()
    assert roster["dead"] is True and record is None
    lua.execute("unit.visible = false")
    assert observe()[0]["dead"] is True
