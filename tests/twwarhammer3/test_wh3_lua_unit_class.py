"""A flying unit's roster category must not hide its movement capability."""
from pathlib import Path

import pytest


def test_flight_precedes_the_infantry_category_but_keeps_commanding_role():
    lua51 = pytest.importorskip("lupa.lua51")
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute("function get(unit, key, default) return unit[key] or default end")
    path = Path(__file__).resolve().parents[2] / (
        "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua")
    source = "local CLASSES = " + path.read_text().split("local CLASSES = ", 1)[1].split(
        "local function unit_record", 1)[0]
    classify = lua.execute(source + "return unit_class")
    # Screamers reported inf_mel in the original engine; the old prefix rule said infantry.
    screamer = lua.table_from({"unit_class": "inf_mel", "can_fly": True})
    assert classify(screamer) == "flying"
    screamer["is_commanding_unit"] = True
    assert classify(screamer) == "lord"
    assert classify(lua.table_from({"unit_class": "inf_mel"})) == "infantry"
