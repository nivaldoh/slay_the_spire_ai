"""Every script packed into the game must compile as Lua 5.1, the game's Lua version."""
import pytest
from wh3_lua import MOD, runtime


@pytest.mark.parametrize("path", sorted(MOD.rglob("*.lua")), ids=lambda path: path.name)
def test_mod_script_compiles_as_lua51(path):
    compile_lua = runtime().eval("function(source, name) assert(loadstring(source, name)) end")
    compile_lua(path.read_text(), "=" + path.name)  # raises with the file, line and error


def test_experience_setter_matches_sorted_types_duplicates_and_refuses_game_rejection():
    lua = runtime()
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_ui.lua").read_text())
    lua.execute('''
        ranks, calls, refused = {sword = {0, 0}, missile = {0}}, 0, false
        local function target(expr)
            assert(string.find(expr, "PlayerSlotList.At(1)", 1, true))
            local unit, index = string.match(expr,
                'Filter%(UnitRecordContext.Key == "(.-)"%).At%((%d+)%)')
            return ranks[unit], tonumber(index) + 1
        end
        common = {
            get_context_value = function(context, id, expr)
                local values, index = target(expr)
                return values[index]
            end,
            call_context_command = function(context, id, expr)
                assert(context == "CcoFrontendRoot" and id == "")
                local values, index = target(expr)
                calls = calls + 1
                if not refused then
                    values[index] = values[index]
                        + (string.find(expr, "IncreaseExperience", 1, true) and 1 or -1)
                end
            end,
        }
    ''')
    run = lua.globals().twwarhammer3_ui.run
    def step(rows):
        return lua.table_from({"slot": 1, "experience": [
            {"type": unit, "rank": rank} for unit, rank in rows]}, recursive=True)
    run(step([("sword", 3), ("missile", 1), ("sword", 9)]), "")
    assert list(lua.globals().ranks.sword.values()) == [3, 9]
    assert list(lua.globals().ranks.missile.values()) == [1]
    run(step([("sword", 0), ("sword", 0), ("missile", 0)]), "")
    assert list(lua.globals().ranks.sword.values()) == [0, 0]
    assert lua.globals().calls == 26
    run(step([("sword", 0)]), "")
    assert lua.globals().calls == 26
    lua.globals().refused = True
    with pytest.raises(Exception, match="experience did not change"):
        run(step([("sword", 1)]), "")
