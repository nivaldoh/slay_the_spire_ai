"""The evaluator-only private record (portfolio S3) and the battle-side equipment check (S4).

The Lua tests run the real definitions of mod/script/battle/mod/twwarhammer3_battle.lua under
Lua 5.1 against a fake engine; which of its getters a live battle has read is listed in
integration.md (Unverified). The record must hold every unit, hidden enemies included, while
the observation and the replay keep only what the player sees; a failed read is absent, never
false; a vehicle's crew is the unit whose unique ui id the vehicle reports, not the first unit of
its type. The Python tests check that an episode keeps the file, that no controller input
carries it, and that the battle's equipment must be the declared pieces.
"""
import json
from copy import deepcopy

import pytest
from lupa.lua51 import LuaError
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation
from wh3_lua import MOD, load_battle, runtime

from twwarhammer3.battle import play, setup
from twwarhammer3.battle.scripted import Hold
from twwarhammer3.protocol import ProtocolError

# A fake engine. A unit answers each getter it names with that value (a function of the call's
# arguments, or ERROR to fail); a getter it does not name is missing, as on an engine without it.
ENGINE = """
    ERROR = {}
    PLAYER, ENEMY = {name = 'player alliance'}, {name = 'enemy alliance'}
    function point(x, y, z)
        return {get_x = function() return x end, get_y = function() return y end,
                get_z = function() return z end}
    end
    function fake_unit(values)
        return setmetatable({}, {__index = function(_, method)
            local value = values[method]
            if value == nil then return nil end
            return function(_, ...)
                if value == ERROR then error('engine refused ' .. method) end
                if type(value) == 'function' then return value(...) end
                return value
            end
        end})
    end
    -- The getters unit_record requires, so the observation and the replay read the unit.
    function soldier(values)
        local unit = {position = point(0, 0, 0), is_routing = false, is_shattered = false,
                      is_in_melee = false, is_moving = false, is_hidden = false, bearing = 90,
                      number_of_men_alive = 100, unary_hitpoints = 1}
        for key, value in pairs(values) do unit[key] = value end
        return fake_unit(unit)
    end
    contexts = {}
    common = {get_context_value = function(context, id, expression) return contexts[expression] end}
    BRIDGE, BEHAVIOURS = '/bridge/', {}
    GATES, CAPTURE_POINTS, TICKETS = 'gates', 'capture points', 'tickets'
    written, logged = {}, {}
    io = {open = function(path, mode)
        assert(mode == 'a')
        return {write = function(_, text) written[path] = (written[path] or '') .. text
                                           return true end,
                close = function() end}
    end}
    function log(text) logged[#logged + 1] = text end
"""

# A siege at its first observation: f1 on our side, e1 visible, e2 hidden behind the walls and
# crewing the ram; the gate reads raw hp 0 with destroyed false, as two recorded gates did.
BATTLE = """
    session = {job = 'j', record_replay = true, private_record = true}
    state = {battle = 'b', seq = 0, alliance = PLAYER, army_abilities = {}, setup = {},
             info = {alliances = 2, player_alliance = 0}, enemy_by_ui = {},
             friendly_ids = {'f1'}, enemy_ids = {'e1', 'e2'},
             known = {[1001] = 'f1', [1002] = 'e1', [1003] = 'e2'}}
    state.friendly = {f1 = {ui_id = '1001', setup = {}, unit = soldier{
        type = 'ksl_inf_streltsi', position = point(10, 50, 20), ammo_left = 20,
        starting_ammo = 30, is_on_top_of_wall = false, is_climbing_ladder = false,
        is_visible_to_alliance = function(alliance) return alliance == ENEMY end}}}
    state.enemy = {
        e1 = {initial = true, unit = soldier{
            type = 'wh_main_emp_inf_handgunners', position = point(100, 60, 200),
            number_of_men_alive = 80, ammo_left = 12, starting_ammo = 20,
            is_on_top_of_wall = true, is_climbing_ladder = false,
            is_visible_to_alliance = function(alliance) return alliance == PLAYER end}},
        e2 = {initial = true, unit = soldier{
            type = 'wh_main_emp_inf_swordsmen', position = point(777.7, 12.5, -333.3),
            number_of_men_alive = 60, is_in_melee = true, ammo_left = 0, starting_ammo = 0,
            is_on_top_of_wall = true, is_climbing_ladder = false,
            is_visible_to_alliance = function() return false end}},
    }
    -- vehicle_item is 1-based, as the 2026-10-25 live reading indexed it.
    ram = fake_unit{vehicle_key = 'ksl_battering_ram', position = point(502.2, 91.9, -550.2)}
    bm = {battle = {assault_equipment = function()
        return {vehicle_count = function() return 1 end,
                vehicle_item = function(_, index) return ({ram})[index] end}
    end}}
    function bm:get_current_phase_name() return 'Deployed' end
    function bm:get_first_non_player_army() return {} end
    function bm:get_non_player_alliance() return ENEMY end
    function bm:local_alliance() return 1 end
    contexts = {
        ['VehicleList.Size'] = 1, ['VehicleList.At(0).CategoryName'] = 'battering_ram',
        ['VehicleList.At(0).Position.x'] = 502.2, ['VehicleList.At(0).Position.z'] = -550.2,
        ['VehicleList.At(0).UnitContext.UniqueUiId'] = 1003,
        gates = 'Gatehouse|503|-94|0|9000|false',
        ['capture points'] = 'key_building|Plaza|0|0|1|false|false|1|true;'
            .. 'tower|Tower|10|10|-1|false|false|0|true',
        tickets = '0|0|0|0|0;1|412|-1.5|0|500',
    }
    -- Engine reads the observation and the replay take beyond the units.
    function sample_countdown() return -1 end
    function terminal_countdown() return nil end
    function player_army() return {} end
    function mode_section() return {} end
    function evaluation() return {} end
    function battle_speed() return 1 end
    function army_abilities() return {} end
"""

NAMES = ("get", "get_context", "context_rows", "round", "clean_error", "plain", "side",
         "visible_to_player", "unit_record", "enemy_observation", "position_fields",
         "equipment_reading", "observation", "record_replay", "private_unit", "crew_reading",
         "record_private")


def battle():
    lua = runtime()
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())
    lua.execute("json = twwarhammer3_json" + ENGINE + BATTLE)
    return lua, dict(zip(NAMES, load_battle(lua, *NAMES), strict=True))


def lines(lua, name):
    return [json.loads(line) for line in (lua.globals().written[f"/bridge/{name}-b.jsonl"]
                                          or "").splitlines()]


def test_the_private_record_keeps_hidden_enemies_that_the_observation_and_replay_drop():
    lua, fn = battle()
    g = lua.globals()
    fn["record_private"](1000, False)
    # Policy memory is untouched: seeing e2 privately must not reveal it or its death later.
    assert (g.state.enemy.e1.seen, g.state.enemy.e2.seen) == (None, None)
    frame, = lines(lua, "private")
    assert (frame["private_record"], frame["job"], frame["battle"], frame["time_ms"]) == (
        1, "j", "b", 1000)
    assert [unit["id"] for unit in frame["enemy"]] == ["e1", "e2"]
    assert frame["enemy"][1] == {
        "id": "e2", "type": "wh_main_emp_inf_swordsmen", "x": 777.7, "y": 12.5, "z": -333.3,
        "men": 60, "routing": False, "shattered": False, "melee": True, "hidden": False,
        "on_wall": True, "climbing": False, "visible": False, "ammo": 0, "ammo0": 0}
    assert (frame["enemy"][0]["ammo"], frame["enemy"][0]["ammo0"]) == (12, 20)
    # Each side's visibility is to the other alliance: f1 is seen by the enemy, e1 by us.
    assert frame["friendly"][0]["visible"] is True and frame["enemy"][0]["visible"] is True
    assert frame["equipment"] == [{"key": "ksl_battering_ram", "x": 502.2, "y": 91.9,
                                   "z": -550.2}]
    assert frame["vehicles"] == [{"category": "battering_ram", "x": 502.2, "z": -550.2,
                                  "crew": "e2"}]
    assert frame["gates"] == [{"name": "Gatehouse", "x": 503, "z": -94, "raw_hp": 0,
                               "raw_max_hp": 9000, "destroyed": False}]
    assert frame["captures"] == [{"id": "c1", "key": "key_building", "holder": "enemy"},
                                 {"id": "c2", "key": "tower"}]
    assert frame["tickets"] == [{"side": "us", "tickets": 0, "per_s": 0, "starting": 0},
                                {"side": "enemy", "tickets": 412, "per_s": -1.5,
                                 "starting": 500}]
    assert "errors" not in frame and frame["sample_cpu_ms"] >= 0

    # The replay frame and the mailbox observation show only the visible enemy.
    fn["record_replay"](1000, False)
    replay = g.written["/bridge/replay-b.jsonl"]
    assert [unit["id"] for unit in json.loads(replay)["enemy"]] == ["e1"]
    observation = fn["observation"](1000)
    text = g.json.encode(observation)
    assert [unit["id"] for unit in json.loads(text)["enemy"]] == ["e1"]
    assert "777.7" not in replay and "777.7" not in text and "-333.3" not in text
    # The setup's equipment readback (hidden from policies) is the same reading.
    assert json.loads(text)["setup"]["assault_equipment"] == frame["equipment"]

    # One frame per engine second, a terminal frame always, and a failed section is absent.
    fn["record_private"](1500, False)
    g.contexts["VehicleList.Size"] = None
    g.contexts["gates"] = None
    fn["record_private"](1600, True)
    first, last = lines(lua, "private")
    assert last["terminal"] is True and "terminal" not in first
    assert "vehicles" not in last and "gates" not in last and last["captures"]
    assert last["errors"] == ["vehicles: unreadable VehicleList.Size",
                              "gates: unreadable context list"]
    assert list(g.logged.values()) == []

    # Off without the scenario's opt-in: no file and no setup readback, as before this record.
    lua.execute("session.private_record = nil; state.setup = {}; written = {}")
    fn["record_private"](3000, False)
    assert list(g.written.values()) == []
    assert "assault_equipment" not in json.loads(g.json.encode(fn["observation"](3000)))["setup"]


def test_a_getter_that_fails_or_answers_another_type_leaves_its_field_absent_not_false():
    lua, fn = battle()
    lua.execute("""
        unit = fake_unit{type = 'ksl_inf_kossars', number_of_men_alive = 0,
            position = {get_x = function() return 1 end, get_z = function() return 2 end,
                        get_y = function() error('no height') end},
            is_routing = false, is_shattered = false, is_hidden = false,
            is_in_melee = ERROR, is_on_top_of_wall = ERROR, is_climbing_ladder = false,
            is_visible_to_alliance = function() return 'yes' end, ammo_left = ERROR}
    """)
    record = fn["private_unit"]("e3", lua.globals().unit, lua.globals().ENEMY)
    # starting_ammo is missing, the others fail; false and 0 are readings and stay.
    assert dict(record.items()) == {"id": "e3", "type": "ksl_inf_kossars", "x": 1, "z": 2,
                                    "men": 0, "routing": False, "shattered": False,
                                    "hidden": False, "climbing": False}
    lua.execute("ram = fake_unit{vehicle_key = ERROR, position = point(1, 2, 3)}")
    vehicle, = fn["equipment_reading"]().values()
    assert dict(vehicle.items()) == {"x": 1, "y": 2, "z": 3}
    # Without the opposing alliance a friendly unit has no visible field, not our own view.
    lua.execute("function bm:get_non_player_alliance() error('no alliance') end")
    fn["record_private"](1000, False)
    frame, = lines(lua, "private")
    assert "visible" not in frame["friendly"][0] and frame["enemy"][0]["visible"] is True
    assert frame["errors"] == ["opponent: unreadable get_non_player_alliance"]


def test_a_crew_is_the_unit_with_the_vehicles_unique_ui_id_not_the_first_of_its_type():
    lua, fn = battle()
    # Two Armoured Kossars, and the second crews the ram (Izmail I3's must-fail case).
    lua.execute("""
        state.friendly_ids = {'f2', 'f3'}
        state.friendly = {
            f2 = {unit = soldier{type = 'ksl_inf_armoured_kossars'}},
            f3 = {unit = soldier{type = 'ksl_inf_armoured_kossars'}}}
        state.known = {[2001] = 'f2', [2002] = 'f3'}
        contexts = {
            ['VehicleList.Size'] = 3, ['VehicleList.At(0).CategoryName'] = 'battering_ram',
            ['VehicleList.At(0).Position.x'] = 10, ['VehicleList.At(0).Position.z'] = 20,
            ['VehicleList.At(0).UnitContext.UniqueUiId'] = 2002,
            ['VehicleList.At(0).UnitContext.UnitRecordContext.Key'] = 'ksl_inf_armoured_kossars',
            ['VehicleList.At(1).UnitContext.UniqueUiId'] = 9999}
    """)
    rows = [dict(row.items()) for row in fn["crew_reading"]().values()]
    # A unit scan() never registered keeps its raw id; a vehicle whose reads fail has none.
    assert rows == [{"category": "battering_ram", "x": 10, "z": 20, "crew": "f3"},
                    {"crew_ui_id": 9999}, {}]
    lua.execute("contexts['VehicleList.Size'] = nil")
    with pytest.raises(LuaError, match="unreadable VehicleList.Size"):
        fn["crew_reading"]()


def test_the_episode_keeps_the_private_record_and_no_controller_input_carries_it(tmp_path):
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    hidden = {"id": "e9", "type": "wh_main_emp_inf_swordsmen", "x": 777.7, "z": -333.3,
              "visible": False}
    raw = json.dumps({"private_record": 1, "job": "job", "battle": "b1", "time_ms": 0,
                      "friendly": [], "enemy": [hidden]}) + '\n{"partial":'
    (bridge / "private-b1.jsonl").write_text(raw)
    seen = []

    class Reader(Hold):
        def decide(self, observation):
            seen.append(json.dumps(observation))
            return []

    def run(name, scenario):
        mailbox = FakeMailbox([bridge_observation(0, 0), bridge_observation(1, 1000),
                               bridge_observation(2, 2000, ack=True, result="won")])
        mailbox.directory = bridge
        return play.play_episode(tmp_path / name, CONFIG, Reader, mailbox, not_battle=None,
                                 scenario=scenario)

    result = run("episode", {"private_record": True})
    assert result["status"] == "won"
    assert result["private_record"] == {"status": "copied", "file": "private.jsonl",
                                        "version": 1, "bytes": len(raw)}
    assert (tmp_path / "episode/private.jsonl").read_text() == raw
    assert seen and not any("777.7" in text or '"e9"' in text for text in seen)
    # Without the field nothing is copied and the result has no such key, as before.
    result = run("plain", {})
    assert "private_record" not in result
    assert not (tmp_path / "plain/private.jsonl").exists()


RAM = {"key": "ksl_battering_ram", "x": 502.2, "y": 91.9, "z": -550.2}


@pytest.mark.parametrize("declared,reading,passes", [
    ({"ksl_battering_ram": 1, "ksl_siege_tower_15m": 0}, [RAM], True),
    ({}, [], True),
    ({"ksl_battering_ram": 1}, [{**RAM, "key": "emp_battering_ram"}], False),
    ({"ksl_battering_ram": 1}, [], False),
    ({"ksl_battering_ram": 1}, [RAM, RAM], False),
    ({}, [{**RAM, "key": "emp_battering_ram"}], False),
    ({"ksl_battering_ram": 1}, [[]], False),
    ({"ksl_battering_ram": 1}, {"error": "assault_equipment: attempt to call a nil value"}, False),
    ({"ksl_battering_ram": 1}, None, False),
], ids=["declared", "none", "other-faction-ram", "lost", "extra", "engine-added", "unreadable-key",
        "failed-reading", "no-reading"])
def test_the_battle_must_hold_exactly_the_declared_siege_equipment(declared, reading, passes):
    scenario = {"expect": {"time_limit_s": 1200, "unit_scale": .75, "realism": False,
                           "player_defends": False, "ai_stats_modifier": "1.0"},
                "player": {"faction": "p", "units": ["lord"]},
                "enemy": {"faction": "e", "units": ["lord"]},
                "siege_equipment": declared}
    state = {"setup": {**scenario["expect"], "army_ai_stats_modifiers": [1.0, 1.0]},
             "armies": {"player": {"faction": "p"}, "enemy": {"faction": "e"}},
             "terrain": {"rows": [".."]}, "friendly": [{"type": "lord"}],
             "enemy_roster": [{"type": "lord"}]}
    if reading is not None:
        state["setup"]["assault_equipment"] = reading
    if passes:
        wanted = {key: count for key, count in declared.items() if count}
        assert setup.check_battle(scenario, state)["siege_equipment"] == wanted
    else:
        with pytest.raises(ProtocolError, match="assault equipment"):
            setup.check_battle(scenario, state)


def test_the_private_record_is_a_two_sided_opt_in_that_siege_equipment_needs():
    base = deepcopy(setup.scenarios()["chd-reserve-grn-siege"])
    siege = {**base, "attacker": "player", "siege_equipment": {"ksl_battering_ram": 1}}
    config = {"episode_timeout": None, "run_timeout": None, "start_timeout": 600, "episodes": 1}
    setup.fill_timeouts(siege, config)
    setup.validate_declaration({**siege, "private_record": True}, config)
    for scenario in (siege, {**siege, "private_record": 1}, {**base, "private_record": False},
                     {**base, "enemy": None, "private_record": True},
                     {**base, "enemy": [base["enemy"]] * 2, "private_record": True}):
        with pytest.raises(ValueError, match="private_record"):
            setup.validate_declaration(scenario, config)
    assert play.battle_session({**base, "private_record": True})["private_record"] is True
    assert "private_record" not in play.battle_session(base)


def test_an_opted_in_battle_flushes_its_private_record_before_the_result():
    """The unchanged flush test in test_wh3_battle_lua.py covers a battle without the record;
    wrong version: the terminal private frame written after the result releases the harness."""
    lua = runtime()
    lua.execute("""
        session = {private_record = true}
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
        function record_replay() calls[#calls + 1] = 'replay' end
        function record_imagery() calls[#calls + 1] = 'imagery' end
        function record_private(now, terminal)
            assert(now == 1234 and terminal == true)
            calls[#calls + 1] = 'private'
        end
        function publish_observation() calls[#calls + 1] = 'result' end
    """)
    _, finish = load_battle(lua, "get", "finish")
    finish()
    calls = list(lua.globals().calls.values())
    assert calls[-1] == "result"
    assert sorted(calls[:-1]) == ["imagery", "private", "replay"]


def test_a_new_job_removes_a_leftover_private_record(tmp_path):
    """Wrong version: a private file from the last battle left in the bridge for the next."""
    from twwarhammer3.engine.mailbox import Mailbox
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "private-1-2.5.jsonl").write_text("old")
    Mailbox(bridge, job="job-b").reset()
    assert list(bridge.iterdir()) == []
