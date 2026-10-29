"""Functions of the battle script, mod/script/battle/mod/twwarhammer3_battle.lua, run under
Lua 5.1 against stubbed engine state.

These exercise the Lua computation only; actual geometry, reachability and engine values
still need game probes.
"""
import json

import pytest
from lupa.lua51 import LuaError
from wh3_lua import MOD, load_battle, runtime


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


def test_flight_precedes_infantry_and_only_a_character_commander_is_a_lord():
    lua = runtime()
    lua.execute("function get(unit, key, default) return unit[key] or default end")
    _, classify = load_battle(lua, "CLASSES", "unit_class")
    # Screamers reported inf_mel in the original engine; the old prefix rule said infantry.
    screamer = lua.table_from({"unit_class": "inf_mel", "can_fly": True})
    assert classify(screamer) == "flying"
    screamer["is_commanding_unit"] = True
    assert classify(screamer) == "flying"
    assert classify(lua.table_from({"unit_class": "com", "can_fly": True,
                                    "is_commanding_unit": True})) == "lord"
    assert classify(lua.table_from({"unit_class": "inf_mel"})) == "infantry"


def test_lordless_commanding_regiments_keep_their_combat_class():
    lua = runtime()
    lua.execute("function get(unit, key, default) return unit[key] or default end")
    _, classify = load_battle(lua, "CLASSES", "unit_class")
    for raw, missile_range, expected in (("cav_mel", 0, "cavalry"),
                                          ("cav_mis", 140, "missile_cavalry"),
                                          ("art_fld", 290, "artillery"),
                                          ("inf_mel", 0, "infantry")):
        unit = lua.table_from({"unit_class": raw, "missile_range": missile_range,
                               "is_commanding_unit": True})
        assert classify(unit) == expected


FLIGHT_GET = """
    function get(unit, key, default)
        if unit[key] == nil then return default end
        return unit[key]
    end
"""


def test_whole_unit_counts_separate_death_routing_withdrawal_absence_and_failed_queries():
    lua = runtime()
    lua.execute(FLIGHT_GET)
    strength, evaluate = load_battle(lua, "strength", "evaluation")
    units = [
        {"number_of_men_alive": 60},
        {"number_of_men_alive": 0},
        {"number_of_men_alive": 40, "is_routing": True},
        {"number_of_men_alive": 20, "is_shattered": True, "is_leaving_battle": True},
        {"number_of_men_alive": 50, "is_leaving_battle": True},
        {"number_of_men_alive": 70, "is_deployed": False},
        {"number_of_men_alive": 80, "is_deploying": True},
        {},  # failed headcount read must never become a destroyed unit
    ]
    entries = lua.table_from({str(i): {"unit": {"type": "same_type", "initial_number_of_men": 100,
                                              "is_deployed": True, **unit}}
                              for i, unit in enumerate(units)}, recursive=True)
    total = strength(entries)
    assert dict(total["units"]) == {"registered": 8, "destroyed": 1, "alive": 6, "active": 1,
                                    "routed": 2, "leaving": 2, "absent": 2, "unknown": 1}
    assert total["men"] == 320 and total["men0"] == 800
    assert total["active_men"] == 260  # historical headcount definition stays unchanged
    assert total["by_type"]["same_type"]["men"] == 320
    # A returning/replenished unit changes state, not the registered denominator.
    entries["5"]["unit"]["is_deployed"] = True
    entries["1"]["unit"]["number_of_men_alive"] = 10
    assert strength(entries)["units"]["registered"] == 8
    assert strength(entries)["units"]["active"] == 3
    lua.globals().state = lua.table_from({"friendly": entries, "enemy": {},
                                         "objective_totals": {}}, recursive=True)
    assert evaluate()["version"] == 2


def test_register_deduplicates_returning_units_and_includes_late_arrivals():
    lua = runtime()
    lua.execute(FLIGHT_GET + """
        state = {known = {}, enemy = {}, enemy_ids = {}, enemy_by_ui = {}}
        bm = {local_alliance = function() return 1 end}
        function unit_class() return "infantry" end
        function log() end
    """)
    register, strength = load_battle(lua, "register", "strength")
    unit = lua.table_from({"unique_ui_id": 10, "number_of_men_alive": 40, "is_deployed": True})
    register(unit, 2, None)
    lua.globals().state["started_ms"] = 1000
    register(unit, 2, None)
    register(lua.table_from({"unique_ui_id": 11, "number_of_men_alive": 30,
                              "is_deployed": True}), 2, None)
    counts = strength(lua.globals().state["enemy"])["units"]
    assert counts["registered"] == counts["alive"] == counts["active"] == 2


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



@pytest.mark.parametrize("kind", [None, "is_multiplayer", "is_replay", "is_from_campaign",
                                  "is_quest_battle", "is_tutorial"])
def test_an_enabled_session_hooks_only_custom_battles(kind):
    # The mod list persists for ordinary launches, so an owner's own campaign battle loads
    # this script too, possibly beside a session file a stopped job left enabled.
    lua = runtime()
    lua.execute("""
        BRIDGE = "bridge/"
        function read_json(path)
            return {schema = 1, job = "j", enabled = true, autostart = true}
        end
        logged, hooked, published = {}, {}, {}
        function log(text) logged[#logged + 1] = text end
        function publish(name) published[#published + 1] = name end
        function guarded(name, fn) return fn end
        state = {}
        battle = {}
        bm = {battle = battle,
              register_phase_change_callback = function(_, phase) hooked[#hooked + 1] = phase end,
              repeat_real_callback = function(_, _, _, name) hooked[#hooked + 1] = name end}
    """)
    if kind:
        lua.execute(f"function battle:{kind}() return true end")
    _, load = load_battle(lua, "get", "load")
    load()
    hooked, published = list(lua.globals().hooked.values()), list(lua.globals().published.values())
    if kind:
        assert hooked == [] and published == []
        assert list(lua.globals().logged.values()) == [f"inactive: {kind}"]
    else:
        assert "Deployed" in hooked and published == ["observation.json"]


@pytest.mark.parametrize("session", ["nil", "{schema = 1, job = 'j', enabled = false}"])
def test_without_an_enabled_session_the_battle_script_hooks_nothing(session):
    # The owner's own custom battles: no session file, or one a job switched off.
    lua = runtime()
    lua.execute(f"""
        BRIDGE = "bridge/"
        function read_json(path) return {session} end
        hooked, published = {{}}, {{}}
        function publish(name) published[#published + 1] = name end
        bm = {{battle = {{}},
              register_phase_change_callback = function(_, phase) hooked[#hooked + 1] = phase end,
              repeat_real_callback = function(_, _, _, name) hooked[#hooked + 1] = name end}}
    """)
    _, load = load_battle(lua, "get", "load")
    load()
    assert list(lua.globals().hooked.values()) == list(lua.globals().published.values()) == []

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
    with pytest.raises(LuaError, match="flight_change_unavailable"):
        apply(entry, land)
    unit["is_currently_flying"] = False  # subsequent engine observation confirms landing
    apply(entry, land)
    assert lua.globals().toggles == 1
    lua.globals().allowed = True
    apply(entry, lua.table_from({"flying": True}))
    assert lua.globals().toggles == 2
    unit["can_fly"] = False
    with pytest.raises(LuaError, match="cannot_fly"):
        apply(entry, land)


def test_startup_rank_query_failure_keeps_observation_ticks_and_does_not_invent_rank_zero():
    lua = runtime()
    lua.execute("""
        local function unit(id)
            return {type = function() return 'swordsmen' end,
                    unique_ui_id = function() return id end}
        end
        state = {friendly_ids = {'f1', 'f2'}, enemy_ids = {}, army_abilities = {},
                 friendly = {f1 = {unit = unit(1001)}, f2 = {unit = unit(1002)}}}
        session = {tick_ms = 250}
        callbacks, ticks = 0, 0
        function tick() ticks = ticks + 1 end
        bm = {
            get_player_alliance = function() return {} end,
            alliances = function() return {count = function() return 2 end} end,
            modify_battle_speed = function(_, speed, lock) assert(speed == 1 and lock) end,
            repeat_callback = function(_, callback, interval, name)
                assert(interval == 250 and name == 'twwarhammer3_tick')
                callbacks, scheduled = callbacks + 1, callback
            end,
        }
        common = {get_context_value = function(context, id, expression)
            if context == 'CcoBattleUnit' and expression == 'ExperienceLevel' then
                if id == '1001' then error('unit context unavailable') end
                assert(id == '1002')
                return 3
            end
        end}
        function battle_info() return {type = 'land_normal', alliances = 2} end
        function battle_time() return 500 end
        function read_slots() end
        function scan() end
        function setup_custom() end
        function context_rows() return {} end
        function read_terrain() return {rows = {'..'}} end
        function sample_objectives() end
        function log() end
    """)
    _, _, start = load_battle(lua, "get", "get_context", "start")
    start()
    g = lua.globals()
    assert g.state.started and g.state.force_observe
    assert g.callbacks == 1
    g.scheduled()
    assert g.ticks == 1
    ranks = g.state.setup.unit_experience.friendly
    assert ranks[1]["rank"] is None and ranks[2]["rank"] == 3
    start()
    assert g.callbacks == 1


@pytest.fixture
def order_dispatch():
    """Record engine calls using the extracted CA unitcontroller signatures.

    docs/twwarhammer3/integration.md#moves-and-attacks adds the harness's attack-mode
    and failed-predecessor contract; acknowledgements establish submission, not execution.
    """
    lua = runtime()
    lua.execute("""
        calls = {}
        local controller = {}
        for _, name in ipairs({'goto_location', 'goto_location_q',
                'goto_location_angle_width', 'goto_location_angle_width_q',
                'attack_unit', 'attack_unit_q', 'melee'}) do
            controller[name] = function(_, ...) calls[#calls + 1] = {name, ...} end
        end
        local function unit()
            return {alive = 50, visible = true, reachable = true, range = 150,
                    number_of_men_alive = function(self) return self.alive end,
                    can_reach_position = function(self, point)
                        assert(point.y == 7)
                        return self.reachable
                    end,
                    ammo_left = function() return 20 end,
                    missile_range = function(self) return self.range end}
        end
        state = {started = true,
            friendly = {f1 = {unit = unit(), controller = controller},
                        f2 = {unit = unit(), controller = controller}},
            enemy = {e1 = {unit = unit()}}}
        state.enemy.e1.unit.id = 'enemy-1'
        bm = {battle = {get_terrain_height = function() return 7 end}}
        function vector(x, y, z) return {x = x, y = y, z = z} end
        function visible_to_player(target) return target.visible end
        function battle_time() return 1234 end
        function log() end
    """)
    _, _, _, apply, batch = load_battle(lua, "get", "round", "clean_error",
                                       "apply_order", "apply_pending")
    return lua, apply, batch


@pytest.mark.parametrize("formation,run", [(False, False), (True, True)])
def test_moves_submit_immediate_and_native_queued_methods_with_engine_arguments(
        order_dispatch, formation, run):
    lua, _, batch = order_dispatch
    shape = {"facing": 60, "width": 20} if formation else {}
    orders = [{"unit": "f1", "type": "move", "x": 10, "z": 20, "run": run, **shape},
              {"unit": "f1", "type": "move", "x": 30, "z": 40,
               "run": not run, "queue": True, **shape}]
    g = lua.globals()
    g.state.pending = lua.table_from({"request": "r1", "based_on": 7, "orders": orders},
                                    recursive=True)
    batch(1234)
    name = "goto_location_angle_width" if formation else "goto_location"
    for call, method, point, fast in zip(g.calls.values(), [name, name + "_q"],
                                       [(10, 20), (30, 40)], [run, not run], strict=True):
        assert call[1] == method
        assert dict(call[2]) == {"x": point[0], "y": 7, "z": point[1]}
        assert list(call.values())[2:] == ([60, 20, fast] if formation else [fast])
    ack = g.state.applied
    assert ack.request == "r1" and ack.based_on == 7 and ack.applied_ms == 1234
    assert [dict(result) for result in ack.results.values()] == [
        {"index": 1, "unit": "f1", "ok": True, "queued": False},
        {"index": 2, "unit": "f1", "ok": True, "queued": True}]
    assert [order["x"] for order in g.state.friendly.f1.command_queue.values()] == [10, 30]


@pytest.mark.parametrize("mode,missile_range,primary", [
    ("auto", 150, True), ("ranged", 150, True), ("melee", 150, False), ("melee", 0, True),
])
def test_attacks_choose_primary_or_secondary_and_queued_attacks_keep_current_move_mode(
        order_dispatch, mode, missile_range, primary):
    lua, apply, batch = order_dispatch
    g = lua.globals()
    g.state.friendly.f1.unit.range = missile_range
    attack = {"unit": "f1", "type": "attack", "target": "e1", "mode": mode, "run": True}
    assert apply(lua.table_from(attack))["ok"]
    assert list(g.calls[1].values()) == ["melee", mode == "melee"]
    assert g.calls[2][1] == "attack_unit" and g.calls[2][2]["id"] == "enemy-1"
    assert list(g.calls[2].values())[2:] == [primary, True]
    lua.execute("calls = {}")
    g.state.pending = lua.table_from({"orders": [
        {"unit": "f1", "type": "move", "x": 10, "z": 20}, {**attack, "queue": True}]},
        recursive=True)
    batch(1234)
    assert [call[1] for call in g.calls.values()] == ["goto_location", "attack_unit_q"]
    assert g.calls[2][2]["id"] == "enemy-1"
    assert list(g.calls[2].values())[2:] == [primary, True]
    assert g.state.applied.results[2]["ok"] and g.state.applied.results[2]["queued"]


@pytest.mark.parametrize("alive,visible,error", [
    (0, True, "target_dead"), (50, False, "target_not_visible"),
])
def test_attack_rechecks_dead_and_hidden_targets_before_any_engine_call(
        order_dispatch, alive, visible, error):
    lua, apply, _ = order_dispatch
    g = lua.globals()
    g.state.enemy.e1.unit.alive, g.state.enemy.e1.unit.visible = alive, visible
    result = apply(lua.table_from({"unit": "f1", "type": "attack", "target": "e1"}))
    assert dict(result) == {"unit": "f1", "ok": False, "error": error}
    assert len(g.calls) == 0 and g.state.friendly.f1.command is None


def test_failed_or_missing_move_predecessor_blocks_queued_successors_but_not_other_units(
        order_dispatch):
    lua, _, batch = order_dispatch
    g = lua.globals()
    g.state.friendly.f1.unit.reachable = False
    g.state.pending = lua.table_from({"orders": [
        {"unit": "f1", "type": "move", "x": 10, "z": 20},
        {"unit": "f1", "type": "move", "x": 30, "z": 40, "queue": True},
        {"unit": "f1", "type": "attack", "target": "e1", "queue": True},
        {"unit": "f2", "type": "move", "x": 50, "z": 60}]}, recursive=True)
    batch(1234)
    results = list(g.state.applied.results.values())
    assert [result["index"] for result in results] == [1, 2, 3, 4]
    assert [result["error"] for result in results] == [
        "unreachable", "queue_predecessor_failed_or_missing",
        "queue_predecessor_failed_or_missing", None]
    assert [result["ok"] for result in results] == [False, False, False, True]
    assert len(g.calls) == 1 and g.calls[1][1] == "goto_location"
    assert dict(g.calls[1][2]) == {"x": 50, "y": 7, "z": 60}
    lua.execute("calls = {}")
    g.state.friendly.f1.unit.reachable = True
    g.state.pending = lua.table_from({"orders": [
        {"unit": "f1", "type": "move", "x": 30, "z": 40, "queue": True}]}, recursive=True)
    batch(1500)
    assert g.state.applied.results[1]["error"] == "queue_predecessor_failed_or_missing"
    assert len(g.calls) == 0


# JUDGEMENT: Terminal recording check — Codex, 2026-10-23, proposes executing finish with
# recording callbacks instead of source inspection. This tests ordering and repeat calls;
# actual file flushing and live capture need separate evidence.
def test_battle_script_flushes_replay_before_result_publication():
    # Publishing the result releases the Python loop to copy the recording.
    lua = runtime()
    lua.execute("""
        state = {friendly = {}}
        bm = {battle = {
            battle_outcome_decided = function() return true end,
            victorious_alliance = function() return 1 end,
            local_alliance = function() return 1 end,
        }, remove_process = function() end}
        function battle_time() return 1234 end
        function sample_custom() end
        function sample_objectives() end
        function evaluation() return {} end
        function log() end
        calls = {}
        function record_replay(now, terminal)
            assert(now == 1234 and terminal == true)
            calls[#calls + 1] = 'replay'
        end
        function record_imagery(now, terminal)
            assert(now == 1234 and terminal == true)
            calls[#calls + 1] = 'imagery'
        end
        function publish_observation(now)
            assert(now == 1234 and state.finished and state.result == 'won')
            calls[#calls + 1] = 'result'
        end
    """)
    _, finish = load_battle(lua, "get", "finish")

    finish()
    calls = list(lua.globals().calls.values())
    assert calls[-1] == "result"
    assert sorted(calls[:-1]) == ["imagery", "replay"]
    finish()
    assert list(lua.globals().calls.values()) == calls


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


def injector(lua):
    """The mod's checkpoint-RL entry point with the real JSON codec; returns a caller that
    decodes its reply."""
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())
    lua.execute("json = twwarhammer3_json")
    inject = load_battle(lua, "inject")
    return lambda text: json.loads(inject(text))


def test_an_injected_request_is_applied_and_acknowledged_like_a_mailbox_request(order_dispatch):
    lua, _, apply_pending = order_dispatch
    inject = injector(lua)
    lua.execute("function clean_error(err) return tostring(err) end")
    message = {"request": "audit-attack_nearest-0", "based_on": 812,
               "orders": [{"unit": "f1", "type": "move", "x": 10, "z": 20, "run": False}]}
    assert inject(json.dumps(message)) == {"accepted": True}
    g = lua.globals()
    assert g.state.pending.request == "audit-attack_nearest-0" and g.state.pending.based_on == 812
    apply_pending(4321)
    ack = g.state.applied
    assert (ack.request, ack.based_on, ack.applied_ms) == ("audit-attack_nearest-0", 812, 4321)
    assert [dict(r) for r in ack.results.values()] == [
        {"index": 1, "unit": "f1", "ok": True, "queued": False}]
    assert g.state.pending is None
    # An empty batch (the no-op candidate) is still a request with an acknowledgement.
    assert inject(json.dumps({**message, "request": "noop", "orders": []})) == {"accepted": True}
    apply_pending(4621)
    assert g.state.applied.request == "noop" and len(g.state.applied.results) == 0


@pytest.mark.parametrize("case,reason", [
    ("not_started", "not started"), ("finished", "finished"), ("pending", "a request is pending"),
    ("not_json", "malformed message"), ("no_request", "malformed message"),
    ("text_based_on", "malformed message"), ("no_orders", "malformed message"),
    ("raises", "boom"),
])
def test_injection_refusals_return_a_reason_raise_nothing_and_keep_pending(case, reason):
    lua = runtime()
    lua.execute("""
        state = {started = true, finished = false}
        function clean_error(err)
            return string.match(tostring(err), ":%d+: (.*)$") or tostring(err)
        end
    """)
    inject = injector(lua)
    g = lua.globals()
    message = {"request": "r", "based_on": 3, "orders": []}
    if case == "not_started":
        g.state.started = False
    elif case == "finished":
        g.state.finished = True
    elif case == "pending":
        lua.execute("state.pending = {request = 'earlier'}")
    elif case == "raises":
        lua.execute("setmetatable(state, {__index = function() error('boom') end})")
        lua.execute("state.started = nil")
    text = {"not_json": "{orders: [", "no_request": json.dumps({"based_on": 3, "orders": []}),
            "text_based_on": json.dumps({**message, "based_on": "3"}),
            "no_orders": json.dumps({"request": "r", "based_on": 3})}.get(case, json.dumps(message))
    assert inject(text) == {"accepted": False, "reason": reason}
    pending = lua.eval("rawget(state, 'pending')")
    assert (pending.request if pending else None) == ("earlier" if case == "pending" else None)


def test_the_injection_entry_point_exists_only_after_an_enabled_session_loads():
    lua = runtime()
    lua.execute("""
        BRIDGE = "bridge/"
        enabled = false
        function read_json(path) return {schema = 1, job = "j", enabled = enabled} end
        function log() end
        function publish() end
        function guarded(name, fn) return fn end
        function inject() end
        state = {}
        bm = {battle = {}, register_phase_change_callback = function() end,
              repeat_real_callback = function() end}
    """)
    _, load = load_battle(lua, "get", "load")
    load()
    assert lua.globals().twwarhammer3_inject is None
    lua.execute("enabled = true")
    load()
    assert lua.eval("twwarhammer3_inject == inject")


ABILITY = ("u = state.friendly.f1.unit; u.owned_non_passive_special_abilities = function()"
           " return {'a1'} end; u.can_perform_special_ability = function() return true end; ")


# The mod's own refusals are the last check before the engine: units and targets change while
# a model thinks, after Python validated the batch. Removing any one of these passed the whole
# WH3 suite before this test (runs/refusal-sweep-20261029/battle-lua.txt).
@pytest.mark.parametrize("error,setup,order", [
    ("unit_dead", "state.friendly.f1.unit.alive = 0", {"type": "halt"}),
    ("unit_routing", "state.friendly.f1.unit.is_routing = function() return true end",
     {"type": "halt"}),
    ("bad_position", "", {"type": "move", "x": 10}),
    ("bad_width", "", {"type": "move", "x": 10, "z": 20, "width": -5}),
    ("unknown_target", "", {"type": "attack", "target": "e9"}),
    ("bad_attack_mode", "", {"type": "attack", "target": "e1", "mode": "magic"}),
    ("no_ammunition", "state.friendly.f1.unit.ammo_left = function() return 0 end",
     {"type": "attack", "target": "e1", "mode": "ranged"}),
    ("bad_flying", "", {"type": "flight", "flying": "yes"}),
    ("cannot_fly", "", {"type": "flight", "flying": True}),
    ("unavailable_behaviour", "", {"type": "behaviour", "behaviour": "skirmish", "enabled": True}),
    ("bad_enabled", "state.friendly.f1.unit.can_use_behaviour = function() return true end",
     {"type": "behaviour", "behaviour": "skirmish", "enabled": "yes"}),
    ("unavailable_ability", "", {"type": "ability", "ability": "a1"}),
    ("ambiguous_ability_target", ABILITY,
     {"type": "ability", "ability": "a1", "x": 1, "z": 2, "target": "e1"}),
    ("bad_position", ABILITY, {"type": "ability", "ability": "a1", "x": 1}),
    ("unknown_target", ABILITY, {"type": "ability", "ability": "a1", "target": "e9"}),
    ("target_dead", ABILITY + "state.enemy.e1.unit.alive = 0",
     {"type": "ability", "ability": "a1", "target": "e1"}),
    ("target_not_visible", ABILITY + "state.enemy.e1.unit.visible = false",
     {"type": "ability", "ability": "a1", "target": "e1"}),
    ("unknown_type", "", {"type": "dance"}),
])
def test_each_mod_refusal_names_its_reason_and_reaches_no_engine_call(
        order_dispatch, error, setup, order):
    lua, _, _ = order_dispatch
    _, _, _, _, apply = load_battle(lua, "BEHAVIOURS", "get", "clean_error", "apply_flight",
                                    "apply_order")
    lua.execute(setup)
    result = apply(lua.table_from({"unit": "f1", **order}))
    assert dict(result) == {"unit": "f1", "ok": False, "error": error}
    assert len(lua.globals().calls) == 0


ARMY = """
    state.army_abilities, state.army_issued = {{key = 'aa'}}, {}
    state.slots = {{id = 's1', names = {[2] = 'tower'}}}
    SLOT_LIST, POOL, currency, built_index, can_purchase = 'Slots', 'Pool', 100, 0, false
    function get_context(expression)
        if expression == 'PlayerArmyContext.GlobalCurrency' then return currency end
        if expression:find('CurrentIndex') then return built_index end
        if expression:find('CanPurchaseUnit') then return can_purchase end
    end
    function pool_rows() return {{'knights', '300'}} end
    common = {call_context_command = function() end}
"""


# The army's orders (abilities, siege building, reinforcements) and their refusals, from the
# same sweep: removing any one of these passed the whole WH3 suite before this test.
@pytest.mark.parametrize("error,setup,order", [
    ("unavailable_ability", "", {"type": "ability", "ability": "zz"}),
    ("ambiguous_ability_target", "", {"type": "ability", "ability": "aa", "target": "e1", "x": 1}),
    ("unknown_target", "", {"type": "ability", "ability": "aa", "target": "e9"}),
    ("target_dead", "state.enemy.e1.unit.alive = 0",
     {"type": "ability", "ability": "aa", "target": "e1"}),
    ("target_not_visible", "state.enemy.e1.unit.visible = false",
     {"type": "ability", "ability": "aa", "target": "e1"}),
    ("bad_position", "", {"type": "ability", "ability": "aa"}),
    ("unknown_slot", "", {"type": "build", "slot": "s9", "option": "tower"}),
    ("unknown_option", "", {"type": "build", "slot": "s1", "option": "wall"}),
    ("not_built", "", {"type": "build", "slot": "s1", "option": "tower"}),
    ("bad_zone", "", {"type": "reinforce", "zone": "x", "reinforcement": "knights"}),
    ("not_in_pool", "", {"type": "reinforce", "zone": 1, "reinforcement": "giants"}),
    ("cannot_purchase_there", "", {"type": "reinforce", "zone": 1, "reinforcement": "knights"}),
    ("not_purchased", "can_purchase = true",
     {"type": "reinforce", "zone": 1, "reinforcement": "knights"}),
])
def test_each_army_order_refusal_names_its_reason(order_dispatch, error, setup, order):
    lua, _, _ = order_dispatch
    lua.execute(ARMY + setup)
    *_, apply = load_battle(lua, "get", "clean_error", "apply_army_ability", "apply_build",
                            "apply_reinforce", "apply_order")
    result = apply(lua.table_from({"unit": "army", **order}))
    assert dict(result) == {"unit": "army", "ok": False, "error": error}


# apply_order also refuses by returning a result, before any order code runs; turning these
# off one at a time passed the WH3 suite (final review, runs/final-review-20261029/).
@pytest.mark.parametrize("order,started,error", [
    ({"unit": "f9", "type": "halt"}, True, "unknown_unit"),
    ({"unit": "f1", "type": "halt"}, False, "deployment"),
    ({"unit": "army", "type": "ability", "ability": "aa"}, False, "deployment"),
    ({"unit": "army", "type": "build", "slot": "s1", "option": "tower"}, False, "deployment"),
    ({"unit": "army", "type": "reinforce", "zone": 1, "reinforcement": "knights"}, False,
     "deployment"),
])
def test_orders_for_unknown_units_or_before_deployment_ends_are_refused(
        order_dispatch, order, started, error):
    lua, apply, _ = order_dispatch
    lua.globals().state.started = started
    result = apply(lua.table_from(order))
    assert dict(result) == {"unit": order["unit"], "ok": False, "error": error}
    assert len(lua.globals().calls) == 0
