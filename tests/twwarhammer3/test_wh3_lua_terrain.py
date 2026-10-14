"""Execute the terrain sampler with the game's missing math.huge constant reproduced.

Run with `uv run --with lupa pytest tests/twwarhammer3/test_wh3_lua_terrain.py`.
This exercises Lua computation; actual geometry and reachability still need game probes.
"""
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / (
    "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua")


def test_terrain_grid_uses_engine_bounds_without_math_huge():
    lua51 = pytest.importorskip("lupa.lua51")
    lua = lua51.LuaRuntime()
    lua.execute("""
        math.huge = nil
        function vector(x, y, z) return {x = x, y = y, z = z} end
        function battle_time() return 4900 end
        local function corner(x, z)
            return {get_x = function() return x end, get_z = function() return z end}
        end
        bm = {battle = {
            battle_boundaries = function()
                return corner(-32, 32), corner(32, 32), corner(-32, -32), corner(32, -32)
            end,
            get_terrain_height = function(_, x, z) return 7 end,
            is_area_clear = function(_, point, bearing, width, depth)
                assert(point.y == 7 and bearing == 0 and width == 16 and depth == 16)
                return point.x < 0 or point.z > 0
            end,
        }}
    """)
    source = SOURCE.read_text().split("local function read_terrain()", 1)[1]
    function = "local function read_terrain()" + source.split("\n-- From the land_units", 1)[0]
    terrain = lua.execute(function + "\nreturn read_terrain()")
    assert terrain["x0"] == terrain["z0"] == -16
    assert list(terrain["rows"].values()) == [".#", ".."]
    assert terrain["cell_m"] == 32 and terrain["sample_width_m"] == 16
    assert terrain["sampled_ms"] == 4900
    assert dict(terrain["bounds"]) == {"min_x": -32, "max_x": 32, "min_z": -32, "max_z": 32}
