"""Functions of the battle script, mod/script/battle/mod/twwarhammer3_battle.lua, run under
Lua 5.1 against stubbed engine state.

These exercise the Lua computation only; actual geometry, reachability and engine values
still need game probes.
"""
import pytest
from wh3_lua import battle_source, load_battle, runtime


def test_terrain_grid_uses_engine_bounds_without_math_huge():
    lua = runtime()
    lua.execute("""
        math.huge = nil  -- missing in the game
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
    terrain = load_battle(lua, "read_terrain")()
    assert terrain["x0"] == terrain["z0"] == -16
    assert list(terrain["rows"].values()) == [".#", ".."]
    assert terrain["cell_m"] == 32 and terrain["sample_width_m"] == 16
    assert terrain["sampled_ms"] == 4900
    assert dict(terrain["bounds"]) == {"min_x": -32, "max_x": 32, "min_z": -32, "max_z": 32}


def test_flight_precedes_the_infantry_category_but_keeps_commanding_role():
    lua = runtime()
    lua.execute("function get(unit, key, default) return unit[key] or default end")
    _, classify = load_battle(lua, "CLASSES", "unit_class")
    # Screamers reported inf_mel in the original engine; the old prefix rule said infantry.
    screamer = lua.table_from({"unit_class": "inf_mel", "can_fly": True})
    assert classify(screamer) == "flying"
    screamer["is_commanding_unit"] = True
    assert classify(screamer) == "lord"
    assert classify(lua.table_from({"unit_class": "inf_mel"})) == "infantry"


FLIGHT_GET = """
    function get(unit, key, default)
        if unit[key] == nil then return default end
        return unit[key]
    end
"""


def test_morale_warning_and_flight_readiness_are_friendly_only():
    lua = runtime()
    lua.execute(FLIGHT_GET + """
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
    record = load_battle(lua, "unit_record")
    unit = lua.table_from({"can_fly": True, "is_currently_flying": True})
    friendly = record("f1", unit, True, "lord")
    assert dict(friendly["morale"]) == {"fraction": .3, "effect": "You must attack by land!"}
    assert dict(friendly["flight"]) == {"can_toggle": False, "cooldown_s": 6.5}
    enemy = record("e1", unit, False, "lord")
    assert enemy["morale"] is None and enemy["flight"] is None
    assert lua.globals().morale_queries == 1


def test_ownership_integrates_time_across_changes_and_ignores_duplicate_samples():
    lua = runtime()
    lua.execute("""
        state = {info = {player_alliance = 0, alliances = 2}, objective_totals = {}}
        function context_rows() return rows end
        function points(first, second)
            rows = {
                {"key_building", "", "0", "0", tostring(first), "false", "false", "1", "true"},
                {"minor_point", "", "0", "0", tostring(second), "false", "false", "1", "true"},
                {"not_a_goal", "", "0", "0", "0", "false", "false", "1", "false"},
            }
        end
    """)
    _, sample = load_battle(lua, "side", "sample_objectives")
    lua.execute("points(0, 1)")
    sample(0)
    sample(900)
    lua.execute("points(1, 0)")
    sample(1000)
    sample(4000)
    sample(4000)  # terminal sampling at the same game time adds nothing
    totals = lua.globals().state["objective_totals"]
    assert set(totals.keys()) == {"c1", "c2"}
    assert totals["c1"]["held_ms"] == 1000 and totals["c2"]["held_ms"] == 3000
    assert totals["c1"]["observed_ms"] == totals["c2"]["observed_ms"] == 4000
    # Snapshot voting would give 2/5 for c1. Actual ownership was 1/4 of the time.
    assert totals["c1"]["held_ms"] / totals["c1"]["observed_ms"] == .25


def test_hidden_arrivals_and_deaths_do_not_update_public_enemy_state():
    lua = runtime()
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
    enemy_observation = load_battle(lua, "enemy_observation")

    def observe():
        return enemy_observation("e7", lua.globals().entry)

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


# A finished finite countdown becomes -1 in the live engine (b8 hold at 1205 s).
def countdown():
    lua = runtime()
    lua.execute("""
        state = {finished = false}
        bm = {battle = {remaining_conflict_time = -1, battle_outcome_decided = false}}
        function get(object, key, default) return object[key] end
    """)
    sample, terminal = load_battle(lua, "sample_countdown", "terminal_countdown")
    return lua.globals(), sample, terminal


def test_terminal_reset_retains_last_live_countdown_without_exposing_it_early():
    g, sample, terminal = countdown()
    g.bm.battle.remaining_conflict_time = .9456787109375
    assert sample(1204100) == pytest.approx(945.6787109375)
    assert terminal(1204100) is None
    g.bm.battle.battle_outcome_decided = True
    g.state.finished = True
    g.bm.battle.remaining_conflict_time = -1
    assert sample(1205200) == -1
    result = dict(terminal(1205200))
    assert result == {"observed_ms": 1204100, "remaining_ms": pytest.approx(945.6787109375),
                      "deadline_ms": pytest.approx(1205045.6787109375), "expired": True,
                      "source": "countdown_deadline"}


def test_early_victory_unlimited_and_timer_extension_are_not_expiry():
    g, sample, terminal = countdown()
    sample(1000)  # no finite timer
    g.state.finished = True
    assert terminal(2000) is None
    g.state.finished = False
    g.bm.battle.remaining_conflict_time = 1
    sample(2000)
    g.bm.battle.remaining_conflict_time = 10  # an extended countdown replaces the old one
    sample(2900)
    g.bm.battle.battle_outcome_decided = True
    g.bm.battle.remaining_conflict_time = -1
    sample(3100)
    g.state.finished = True
    assert terminal(3100)["expired"] is False
    assert terminal(3100)["deadline_ms"] == 12900


def test_disabling_a_live_timer_clears_its_old_deadline():
    g, sample, terminal = countdown()
    g.bm.battle.remaining_conflict_time = 1
    sample(1000)
    g.bm.battle.remaining_conflict_time = -1
    sample(1500)  # still no decided outcome
    g.state.finished = True
    assert terminal(3000) is None


def test_flight_checks_live_state_and_refuses_blocked_changes():
    lua = runtime()
    lua.execute(FLIGHT_GET + """
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
    apply = load_battle(lua, "apply_flight")
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


def test_battle_script_flushes_replay_before_result_publication():
    finish = battle_source("finish")
    assert finish.index("record_replay(battle_time(), true)") < finish.index(
        "publish_observation(battle_time())")


def test_lua_recorder_is_independent_public_throttled_and_failure_isolated():
    lua = runtime()
    lua.execute("""
        session = {job = 'j', record_replay = true}
        BRIDGE = '/unused/'
        state = {battle = 'b', friendly_ids = {'f1'}, enemy_ids = {'e1'},
            friendly = {f1 = {unit = {}}}, enemy = {e1 = {unit = {}, initial = true}},
            army_abilities = {}, seq = 123}
        bm = {battle = {}}
        function bm:get_current_phase_name() return 'Deployed' end
        function bm:get_player_army() return {} end
        function get(unit, key, default) return default end
        function mode_section() return {supplies = 42} end
        function unit_record(id) return {id = id, x = 3, z = 4, men = 2, secret = 'hidden'} end
        function enemy_observation(id, entry)
            entry.seen = true
            return {id = id}, unit_record(id)
        end
        function clean_error(e) return tostring(e) end
        logs, writes = 0, 0
        function log(e) logs = logs + 1 end
        json = {encode = function(frame) saved = frame; return 'frame' end}
        io = {open = function()
            return {write = function() writes = writes + 1; return true end,
                    close = function() end}
        end}
    """)
    record = load_battle(lua, "record_replay")
    record(1000, False)
    g = lua.globals()
    assert g.writes == 1 and g.state.seq == 123
    assert g.state.enemy.e1.seen is None
    assert g.saved.friendly[1].secret is None
    assert g.saved.enemy[1].id == "e1"
    record(1500, False)
    assert g.writes == 1
    record(2000, False)
    assert g.writes == 2
    record(2300, True)
    assert g.writes == 3 and g.saved.terminal is True
    lua.execute("io.open = function() error('disk failure') end")
    record(3000, False)
    assert g.logs == 1
    lua.execute("session.record_replay = false")
    record(4000, False)
    assert g.logs == 1


def test_lua_presentation_never_queries_hidden_enemy_positions_or_policy_memory():
    lua = runtime()
    lua.execute('''
        session = {job='j', stills=true}
        queried = {}
        function unit(id, visible)
            return {id=id, visible=visible, is_under_missile_attack=function() return true end,
                position=function()
                queried[id] = true
                return {get_x=function() return 1 end, get_z=function() return 2 end}
            end}
        end
        state = {battle='b', seq=99, friendly_ids={'f1'}, enemy_ids={'e1','e2','e3'},
            friendly={f1={unit=unit('f1',true)}},
            enemy={e1={unit=unit('e1',false),initial=true},
                   e2={unit=unit('e2',true)}, e3={unit=unit('e3',false)}}}
        function get(object, name, default)
            if name == 'unique_ui_id' then return object.id end
            if object[name] then return object[name]() end
            return default
        end
        function visible_to_player(unit) return unit.visible end
        function plain(text) return text end
        function clean_error(text) return text end
        function log(text) error(text) end
        common={get_context_value=function(_, id)
            if id=='e3' then error('unseen reinforcement') end
            if id=='e1' then error('name unavailable') end
            return id .. ' readable'
        end}
        function twwarhammer3_imagery(frame, names) saved, saved_names = frame, names end
    ''')
    sample = load_battle(lua, "record_imagery")
    sample(1000, False)
    g = lua.globals()
    assert g.state.seq == 99 and g.state.enemy.e2.seen is None
    assert g.queried.f1 and g.queried.e2
    assert g.queried.e1 is None and g.queried.e3 is None
    assert len(g.saved.enemy) == 1 and g.saved.enemy[1].id == "e2"
    assert g.saved.friendly[1].state[1] == "under_fire"
    assert g.saved_names.f1 == "f1 readable" and g.saved_names.e1 is None
