"""The siege-attack interface (scenario field siege_assault) and the ksl-emp-siege-a-v1 declaration.

Reference: the 2026-11-08 siege-attack design (runs/siege-evals-20261108/final-izmail.md,
Infrastructure I2-I5) and portfolio.md S10; the getters and orders are CA's
battle_building.html, battle_unit.html and battle_unitcontroller.html (besiege_building and
attack_building(building, piece index, move fast)), and lib_battle_manager.lua, which puts every
gate building in the wall list too. The Lua tests run the mod's real definitions under Lua 5.1
against a fake engine; no battle has read any of these getters (integration.md, Unverified), so
they show what the mod does with the documented answers, not that the engine gives them. The
Python tests show that only a siege the player attacks with the opt-in gets the new fields,
orders, prompt lines and reply schema, and that every other request is unchanged.
"""

import hashlib
import json
from copy import deepcopy

import pytest
from lupa.lua51 import LuaError
from wh3_fixtures import FakeSend, observation, opening
from wh3_lua import load_battle, runtime
from wh3_siege_attack import first_observation, later

from gameai.ledger import Ledger
from twwarhammer3.battle import escalade, llm, play, setup
from twwarhammer3.protocol import IllegalActionError, ProtocolError, validate_orders

# Marker lines for ksl-emp-siege-a-v1's values in configs/twwarhammer3/scenarios.json, which
# cannot carry a comment (docs/judgement.md).
# JUDGEMENT: Siege attack construction profile — Claude, 2026-11-08 (siege-attack design, Settings
# and Rosters): ksl-emp-siege-a-v1 map, rosters, expect, rank 0 and engine starts. Other forces,
# timer or placement change the difficulty; every reading of the battle and its gate rest on it.
# JUDGEMENT: Siege attack equipment — Claude, 2026-11-08 (design, Equipment): ksl-emp-siege-a-v1
# siege_equipment one ksl ram, no tower. A tower or no ram changes the gate and ladder decisions;
# D1, the Gate only control and the Horse rule rest on it.
# JUDGEMENT?: Siege attack withheld names — Claude, 2026-11-08: ksl-emp-siege-a-v1 withheld (1790
# sources' people, places and sides, and "escalade", the witness's tactic). A shorter list lets
# more names into a job; the neutral-naming check rests on it.
JOB = "siege-r1-003"
# The structured-output part of the request llm sent for wh3_fixtures.opening() (a siege
# defence) before the siege orders existed, hashed at e918091 plus this branch's earlier work.
OPENING_TEXT_SHA256 = "f11459d3bccdf46c4623ad4abd87478550b111204d8a5805ba01ffa9e9ee4c5e"


def test_the_declaration_passes_plays_checks_and_names_no_history():
    scenario = setup.load_scenario({"scenario": "ksl-emp-siege-a-v1"})
    config = {"episodes": 1, "start_timeout": 900, "episode_timeout": None, "run_timeout": None}
    setup.fill_timeouts(scenario, config)
    setup.validate_declaration(scenario, config)
    assert (scenario["status"], scenario["split"]) == ("prototype_not_admitted", "development")
    assert setup.expected_mode(scenario) == {"type": "settlement_standard", "role": "attacker"}
    assert sorted(setup.battle_units(scenario["player"])) == sorted(escalade.ARMY.elements())
    assert play.battle_session(scenario) == {"benchmark": "behaviour-defaults",
                                             "private_record": True, "siege_assault": True}
    steps = str(setup.scenario_steps(scenario))
    assert "ksl_battering_ram" in steps and "emp_battering_ram" not in steps
    setup.check_job(scenario, JOB)
    for job in ("bench-izmail-r1", "escalade-r1"):
        with pytest.raises(ValueError, match="withheld"):
            setup.check_job(scenario, job)
    # The rest of the declaration reaches manifests and reports: it names no withheld word.
    text = json.dumps({key: value for key, value in scenario.items() if key != "withheld"})
    assert [word for word in scenario["withheld"] if word in text.lower()] == []


def test_only_a_two_sided_siege_the_player_attacks_can_opt_in():
    base = setup.scenarios()["ksl-emp-siege-a-v1"]
    config = {"episodes": 1, "start_timeout": 900, "episode_timeout": None, "run_timeout": None}
    setup.fill_timeouts(base, config)
    for wrong in ({"attacker": "enemy"}, {"battle_type": "classic"}, {"siege_assault": 1},
                  {"enemy": [base["enemy"]] * 2}):
        with pytest.raises(ValueError, match="siege_assault"):
            setup.validate_declaration({**base, **wrong}, config)
    for name in ("siege-attack-kho5-dwf5", "cth-emp-siege-a-v1", "chd-reserve-grn-siege"):
        assert "siege_assault" not in play.battle_session(setup.scenarios()[name])


# A fake engine: a unit or building answers each getter it names with that value (a function of
# the call's arguments, or ERROR to fail); a getter it does not name is missing.
ENGINE = """
    ERROR = {}
    function point(x, y, z)
        return {get_x = function() return x end, get_y = function() return y end,
                get_z = function() return z end}
    end
    function fake(values)
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
    function soldier(values)
        local unit = {position = point(0, 0, 0), is_routing = false, is_shattered = false,
                      is_in_melee = false, is_moving = false, is_hidden = false, bearing = 0,
                      number_of_men_alive = 60, unary_hitpoints = 1}
        for key, value in pairs(values) do unit[key] = value end
        return fake(unit)
    end
    function building(name, x, z, gate, health, owner, pivot)
        return fake{name = name, central_position = point(x, 345, z),
                    position = pivot or point(x, 345, z), has_gate = gate, health = health,
                    alliance_owner_id = owner}
    end
    slot_rows, contexts, logged = {}, {}, {}
    common = {get_context_value = function(context, id, expression)
        local army = expression:match('^ToggleableSlotList%((ArmyList%.At%(%d+%))%)')
        if army then return slot_rows[army] end
        return contexts[expression]
    end}
    function log(text) logged[#logged + 1] = text end
    CAPTURE_POINTS, TICKETS, GATES, SLOT_LIST = 'capture points', 'tickets', 'gates', 'slots'
    SLOTS, SLOT_SETUP, POOL, ZONES, BEHAVIOURS = 'slot rows', 'slot setup', 'pool', 'zones', {}
    -- The gate's pivot lies 15 m from its centre; the wall list holds the gate too, as
    -- lib_battle_manager.lua builds it, and no list is in x order.
    gate = building('gate', -32, -16, true, 1, nil, point(-40, 330, -30))
    walls = {east = building('east', 100, -31, false, 0.5), middle = building('middle', -150, -75,
             false, 0), west = building('west', -300, -95, false, 1),
             climb = building('climb', 248.8, -116, false, 1)}
    towers = {building('t188', 188, -81, false, 1, 2), building('t-62', -62, -31, false, 1, -1),
              building('t58', 58, -31, false, 1, 1)}
    lists = {gate = {gate}, wall = {walls.east, gate, walls.climb, walls.middle, walls.west},
             tower = towers}
    bm = {battle = {}}
    function bm:get_fort_gate_buildings() return lists.gate end
    function bm:get_fort_wall_buildings() return lists.wall end
    function bm:get_fort_tower_buildings() return lists.tower end
    function bm:local_alliance() return 1 end
    state = {info = {role = 'attacker', alliances = 2, player_alliance = 0, army_id = 7},
             slots = {}, friendly = {}, friendly_ids = {}, enemy = {}, enemy_ids = {},
             known = {}, enemy_by_ui = {}, started = true, alliance = 'us'}
"""
NAMES = ("get", "get_context", "context_rows", "round", "clean_error", "plain", "side",
         "read_slots", "pool_rows", "crew_reading", "setup_fortifications",
         "fortification_reading", "siege_vehicles", "enemy_structures", "mode_section",
         "siege_unit", "unit_record", "visible_to_player", "enemy_observation", "apply_siege",
         "apply_order")
FORT = [{"id": "g1", "kind": "gate", "x": -32, "z": -16, "hp": 100},
        {"id": "w1", "kind": "wall", "x": -300, "z": -95, "hp": 100},
        {"id": "w2", "kind": "wall", "x": -150, "z": -75, "hp": 0},
        {"id": "w3", "kind": "wall", "x": 100, "z": -31, "hp": 50},
        {"id": "w4", "kind": "wall", "x": 248.8, "z": -116, "hp": 100},
        {"id": "t1", "kind": "tower", "x": -62, "z": -31, "hp": 100, "owner": "none"},
        {"id": "t2", "kind": "tower", "x": 58, "z": -31, "hp": 100, "owner": "us"},
        {"id": "t3", "kind": "tower", "x": 188, "z": -81, "hp": 100, "owner": "enemy"}]


def mod():
    lua = runtime()
    lua.execute("json = nil" + ENGINE)
    return lua, dict(zip(NAMES, load_battle(lua, *NAMES), strict=True))


def rows(table):
    return [dict(row.items()) for row in table.values()]


def test_fortification_ids_are_given_once_by_centre_and_kept_with_their_building():
    """Wrong versions: ids reassigned in list order after a piece leaves the list; the gate
    counted as a wall piece too; towers dropped; position() (a pivot) used for the centre."""
    lua, fn = mod()
    g = lua.globals()
    assert dict(fn["setup_fortifications"]().items()) == {"gate": 1, "wall": 5, "tower": 3}
    assert rows(fn["fortification_reading"]()) == FORT
    # A piece leaves its list and the rest reorder: every id still names its own building.
    lua.execute("lists.wall = {walls.west, walls.climb, gate, walls.east}"
                "; lists.tower = {towers[3], towers[1]}")
    assert rows(fn["fortification_reading"]()) == FORT
    assert g.state.fortifications.by_id.w3.building.name(None) == "east"
    assert g.state.fortifications.by_id.t3.building.name(None) == "t188"


def test_a_defender_or_an_unreadable_building_sets_up_no_siege_fields():
    """Wrong version: the new fields in a defender siege's observation."""
    for setup_lua, error in (("state.info.role = 'defender'", "attacking"),
                             ("walls.west = building('west', -300, -95, ERROR, 1)"
                              "; lists.wall = {walls.west}", "has_gate")):
        lua, fn = mod()
        lua.execute(setup_lua)
        with pytest.raises(LuaError, match=error):
            fn["setup_fortifications"]()
        g = lua.globals()
        assert g.state.fortifications is None
        section = dict(fn["mode_section"]().items())
        assert not {"fortifications", "vehicles", "enemy_structures"} & set(section)
        lua.execute("unit = soldier{is_on_top_of_wall = true, can_climb_walls = true}"
                    "; state.friendly.f1 = {unit = unit, ui_id = '1', setup = {}}")
        record = dict(fn["unit_record"]("f1", g.unit, True, "infantry").items())
        assert not {"on_wall", "can_climb", "can_siege"} & set(record)


# Positions read in the 2026-11-03 Helmgart checkpoint battle (siege-905-20261103, unit 1013):
# climbing a ladder at ground height at 100 s, at the wall top at 130 s; on_wall is the getter's.
UNDER = "point(223.2, 330.0, -117.4)"
ON_TOP = "point(248.8, 345.0, -116.0)"


def test_on_wall_and_the_climb_and_siege_abilities_are_the_engines_readings():
    """Wrong versions: on_wall filled from distance to a wall piece; climbing shown; a hidden
    enemy's on_wall shown; can_climb re-read or a failed read shown as false."""
    lua, fn = mod()
    fn["setup_fortifications"]()
    lua.execute(f"""
        under = soldier{{position = {UNDER}, is_on_top_of_wall = false, is_climbing_ladder = true,
                         can_climb_walls = true, has_attribute = function(key) return false end}}
        top = soldier{{position = {ON_TOP}, is_on_top_of_wall = true, is_climbing_ladder = false,
                       can_climb_walls = ERROR, has_attribute = function(key)
                           return key == 'can_siege' end}}
        state.friendly = {{f1 = {{unit = under, ui_id = '1', setup = {{}}}},
                          f2 = {{unit = top, ui_id = '2', setup = {{}}}}}}
        seen = soldier{{position = point(5, 345, -20), is_on_top_of_wall = true,
                        is_visible_to_alliance = function() return true end}}
        hidden = soldier{{position = point(9, 345, -20), is_on_top_of_wall = true,
                          is_visible_to_alliance = function() return false end}}
        state.enemy = {{e1 = {{unit = seen, initial = true}},
                       e2 = {{unit = hidden, initial = true}}}}
    """)
    g = lua.globals()
    under = dict(fn["unit_record"]("f1", g.under, True, "infantry").items())
    top = dict(fn["unit_record"]("f2", g.top, True, "infantry").items())
    assert (under["on_wall"], under["can_climb"], under["can_siege"]) == (False, True, False)
    assert (top["on_wall"], top["can_siege"]) == (True, True) and "can_climb" not in top
    assert not [record for record in (under, top) if "climbing" in record]
    # Read once: a later answer does not change a kept reading.
    lua.execute("under = soldier{is_on_top_of_wall = false, can_climb_walls = false}")
    assert dict(fn["unit_record"]("f1", g.under, True, "infantry").items())["can_climb"] is True
    roster, record = fn["enemy_observation"]("e1", g.state.enemy.e1)
    assert dict(record.items())["on_wall"] is True and "on_wall" not in dict(roster.items())
    roster, record = fn["enemy_observation"]("e2", g.state.enemy.e2)
    assert record is None and "on_wall" not in dict(roster.items())


def test_the_mode_lists_our_crewed_vehicles_and_only_finished_enemy_structures():
    """Wrong version: unbuilt enemy slots (or their options, or our own) listed."""
    lua, fn = mod()
    fn["setup_fortifications"]()
    lua.execute("""
        state.friendly.f3 = {unit = soldier{}, ui_id = '2002', setup = {}}
        state.known = {[2002] = 'f3', [3001] = 'e1'}
        contexts = {['VehicleList.Size'] = 2, ['VehicleList.At(0).CategoryName'] = 'battering_ram',
            ['VehicleList.At(0).Position.x'] = 0.04, ['VehicleList.At(0).Position.z'] = -231,
            ['VehicleList.At(0).UnitContext.UniqueUiId'] = 2002,
            ['VehicleList.At(1).CategoryName'] = 'battering_ram',
            ['VehicleList.At(1).UnitContext.UniqueUiId'] = 3001,
            ['ArmyList.Size'] = 2, ['ArmyList.At(0).UniqueID'] = 7, ['ArmyList.At(1).UniqueID'] = 9}
        slot_rows = {['ArmyList.At(0)'] = 'tower|1|2|1|false|false',
            ['ArmyList.At(1)'] = 'tower|10|20|2|false|false;tower|30|40|-1|false|false;'
                .. 'barricade|50|60|1|true|false;tower|70|80|0|false|true'}
    """)
    section = dict(fn["mode_section"]().items())
    assert rows(section["fortifications"]) == FORT
    assert rows(section["vehicles"]) == [{"id": "v1", "category": "battering_ram", "x": 0,
                                         "z": -231, "crew": "f3"}]
    assert rows(section["enemy_structures"]) == [
        {"type": "tower", "x": 10, "z": 20}, {"type": "tower", "x": 70, "z": 80,
                                               "destroyed": True}]
    # A list that cannot be read is left out, never shown empty.
    lua.execute("contexts['VehicleList.Size'] = nil; contexts['ArmyList.Size'] = nil")
    section = dict(fn["mode_section"]().items())
    assert "vehicles" not in section and "enemy_structures" not in section
    assert list(lua.globals().logged.values()) == [
        "vehicles failed: unreadable VehicleList.Size",
        "enemy_structures failed: unreadable ArmyList.Size"]


def dispatch():
    lua, fn = mod()
    fn["setup_fortifications"]()
    lua.execute("""
        calls = {}
        controller = {}
        for _, name in ipairs({'besiege_building', 'attack_building', 'goto_location'}) do
            controller[name] = function(_, target, ...)
                calls[#calls + 1] = {name, target.name and target:name() or target, ...}
            end
        end
        climber = fake{number_of_men_alive = 50, is_routing = false, is_shattered = false,
                       can_climb_walls = true, ammo_left = 6,
                       has_attribute = function(key) return false end}
        gun = fake{number_of_men_alive = 2, is_routing = false, is_shattered = false,
                   can_climb_walls = false, ammo_left = 22,
                   has_attribute = function(key) return key == 'can_siege' end}
        state.friendly = {f1 = {unit = climber, controller = controller},
                          f2 = {unit = gun, controller = controller}}
    """)
    return lua, fn["apply_order"]


def test_siege_orders_go_to_the_kept_building_object_with_the_whole_piece():
    """Wrong versions: besiege sent as goto_location to the centre; attack_building sent to the
    building at the same index of another list; ids re-read after a piece leaves its list."""
    lua, apply = dispatch()
    g = lua.globals()
    lua.execute("lists.wall = {walls.west}; lists.tower = {towers[2]}")
    for order in ({"unit": "f1", "type": "besiege", "target": "w3", "run": True},
                  {"unit": "f2", "type": "besiege", "target": "g1"},
                  {"unit": "f2", "type": "attack_building", "target": "t3", "run": False}):
        assert dict(apply(lua.table_from(order)).items()) == {"unit": order["unit"], "ok": True,
                                                              "queued": False}
    assert [list(call.values()) for call in g.calls.values()] == [
        ["besiege_building", "east", 1, True], ["besiege_building", "gate", 1, False],
        ["attack_building", "t188", 1, False]]
    assert g.state.friendly.f2.order == "attack_building"


@pytest.mark.parametrize("order,setup_lua,error", [
    ({"unit": "f1", "type": "besiege", "target": "w9"}, "", "unknown_target"),
    ({"unit": "f1", "type": "besiege", "target": "w2"}, "", "target_destroyed"),
    ({"unit": "f2", "type": "besiege", "target": "w1"}, "", "cannot_climb"),
    ({"unit": "f1", "type": "attack_building", "target": "g1"}, "", "cannot_siege"),
    ({"unit": "f2", "type": "attack_building", "target": "g1"},
     "gun = fake{number_of_men_alive = 2, ammo_left = 0, has_attribute = function() return true"
     " end}; state.friendly.f2.unit = gun", "no_ammunition"),
    ({"unit": "f1", "type": "besiege", "target": "w1"}, "state.fortifications = nil",
     "unknown_type"),
    ({"unit": "f1", "type": "besiege", "target": "w1"},  # can_climb_walls fails: unknown
     "state.friendly.f1.unit = fake{number_of_men_alive = 50, can_climb_walls = ERROR}",
     "cannot_climb"),
])
def test_each_siege_refusal_names_its_reason_and_calls_no_engine_order(order, setup_lua, error):
    lua, apply = dispatch()
    lua.execute(setup_lua)
    assert dict(apply(lua.table_from(order)).items()) == {"unit": order["unit"], "ok": False,
                                                          "error": error}
    assert len(lua.globals().calls) == 0


SIEGE = first_observation()


@pytest.mark.parametrize("orders,error", [
    ([{"unit": "f12", "type": "besiege", "target": "w3", "run": True}], "cannot climb"),
    ([{"unit": "f2", "type": "besiege", "target": "w99", "run": True}], "not a fortification"),
    ([{"unit": "f2", "type": "attack_building", "target": "g1", "run": False}],
     "cannot attack buildings"),
    ([{"unit": "f2", "type": "besiege", "target": "w3", "run": True},
      {"unit": "f2", "type": "move", "x": 0, "z": 0}], "ordered twice"),
    ([{"unit": "f2", "type": "move", "x": 0, "z": 0},
      {"unit": "f2", "type": "besiege", "target": "w3", "queue": True}], "queued"),
    ([{"unit": "f9", "type": "besiege", "target": "w3", "run": "yes"}], "booleans"),
])
def test_validation_refuses_siege_orders_the_observation_does_not_allow(orders, error):
    """Wrong versions: a non-climber accepted on a wall, an order on a destroyed target."""
    validate_orders([{"unit": "f2", "type": "besiege", "target": "w3", "run": True},
                     {"unit": "f12", "type": "besiege", "target": "g1", "run": True},
                     {"unit": "f13", "type": "attack_building", "target": "g1", "run": False}],
                    SIEGE)
    with pytest.raises(IllegalActionError, match=error):
        validate_orders(orders, SIEGE)


def test_a_destroyed_target_a_routing_unit_or_a_battle_without_fortifications_is_refused():
    """Wrong version: a unit whose climbing was never read accepted on a wall."""
    broken = later(SIEGE, 60000, f2={"state": ["routing"]}, f13={"ammo": 0})
    broken["mode"]["fortifications"][3]["hp"] = 0  # w3 at 0%, whatever any flag says
    del broken["friendly"][6]["can_climb"]  # f7's can_climb_walls read failed
    for order, error in (({"unit": "f3", "type": "besiege", "target": "w3"}, "destroyed"),
                         ({"unit": "f2", "type": "besiege", "target": "g1"}, "routing"),
                         ({"unit": "f7", "type": "besiege", "target": "w5"}, "cannot climb"),
                         ({"unit": "f13", "type": "attack_building", "target": "g1"},
                          "cannot attack buildings")):
        with pytest.raises(IllegalActionError, match=error):
            validate_orders([order], broken)
    defence = opening()
    defence["friendly"][1].update(can_climb=True)
    with pytest.raises(IllegalActionError, match="unknown order type"):
        validate_orders([{"unit": "f2", "type": "besiege", "target": "g1"}], defence)


def model(tmp_path, *replies):
    send = FakeSend(*replies)
    return llm.LLMPolicy("gpt-6-luna", "low", Ledger(tmp_path / "ledger.jsonl", 1.0),
                         send=send), send


WAIT = json.dumps({"orders": [], "reason": "wait", "notes": None})
CLIMB = json.dumps({"orders": [{"unit": "f2", "type": "besiege", "target": "w3", "run": True}],
                    "reason": "climb", "notes": None})


def test_other_battles_send_the_same_request_and_prompt_as_before(tmp_path):
    """Wrong version: the new fields, orders or schema in a defender siege's request."""
    agent, send = model(tmp_path, WAIT)
    agent.decide(opening())
    body = send.bodies[0]
    text = json.dumps(body["text"], sort_keys=True).encode()
    assert hashlib.sha256(text).hexdigest() == OPENING_TEXT_SHA256
    assert body["text"]["format"]["schema"] == llm.REPLY_SCHEMA
    for word in ("besiege", "attack_building", "Fortifications", "on the wall", "climb"):
        assert word not in body["input"][0]["content"]
    # A defender's model cannot order a siege: off its schema the order is dropped.
    agent, _ = model(tmp_path, CLIMB, CLIMB, CLIMB)
    assert agent.decide(opening()) == []
    assert "unknown order type" in agent.metadata()["dropped"][0]


def land_attack():
    """A land battle the player attacks (239 of 461 recorded first observations read land_normal
    and role attacker): wh3_fixtures.observation() with that mode."""
    state = observation()
    state["mode"] = {"type": "land_normal", "role": "attacker", "timeout_winner": "enemy",
                     "objectives": "Objectives: (placeholder for the engine's objective text)"}
    return state


def siege_attack_without_opt_in():
    """A siege the player attacks without siege_assault, as the 2026-10-14 attack smoke read
    it: the fixture without the fields only the opt-in adds."""
    state = first_observation()
    for key in ("fortifications", "vehicles", "enemy_structures"):
        del state["mode"][key]
    for unit in state["friendly"] + state["enemy"]:
        for key in ("on_wall", "can_climb", "can_siege"):
            unit.pop(key, None)
    return state


# The whole request llm sent for each at e918091, before the siege orders existed.
BODY_SHA256 = {
    "land_attack": "a30bf9dbe83ed0d88af0fc929112775927485e8647fe58c1d8f1f2ee2ff29854",
    "siege_attack_without_opt_in":
        "3e8ba3257c7f93b93f7bd2c980109a3a883ea58edca1ab1ea2845bf411005e11"}


@pytest.mark.parametrize("make", [land_attack, siege_attack_without_opt_in])
def test_a_battle_the_player_attacks_without_the_opt_in_sends_the_same_request(make, tmp_path):
    """Wrong version: the siege schema or orders for every battle the player attacks."""
    agent, send = model(tmp_path, WAIT)
    agent.decide(play.public(make(), {}))
    body = send.bodies[0]
    assert body["text"]["format"]["schema"] == llm.REPLY_SCHEMA
    text = json.dumps(body, sort_keys=True).encode()
    assert hashlib.sha256(text).hexdigest() == BODY_SHA256[make.__name__]


# The model's siege prompt and orders wait on the owner: the llm.py change that adds them
# changes every llm controller's card identity (runs/siege-evals-20261108/parked/).


def test_the_battle_check_requires_the_siege_setup_to_have_read_the_fort():
    scenario = setup.scenarios()["ksl-emp-siege-a-v1"]
    state = deepcopy(SIEGE)
    state["setup"].update(unit_scale=.75, realism=False, player_defends=False,
                          army_ai_stats_modifiers=[1.0, 1.0],
                          assault_equipment=[{"key": "ksl_battering_ram"}],
                          benchmark_behaviours={"friendly": {}, "enemy": {}})
    state["terrain"] = {"rows": [".."]}
    state["enemy_roster"] = [{"id": f"e{i}", "type": kind}
                             for i, kind in enumerate(scenario["enemy"]["units"], 1)]
    state["setup"]["unit_experience"] = {
        "friendly": [{"type": u["type"], "rank": 0} for u in state["friendly"]],
        "enemy": [{"type": u["type"], "rank": 0} for u in state["enemy_roster"]]}
    toggles = state["setup"]["benchmark_behaviours"]
    toggles["friendly"] = {u["id"]: {"supported": []} for u in state["friendly"]}
    toggles["enemy"] = {u["id"]: {"supported": []} for u in state["enemy_roster"]}
    checks = setup.check_battle(scenario, state)
    assert checks["siege_assault"] == {"lists": {"gate": 1, "wall": 12, "tower": 4},
                                       "fortifications": {"gate": 1, "wall": 11, "tower": 4}}
    # A setup that read ok while the engine listed no wall piece (or no gate) must stop as a
    # setup failure. Without this check Escalade refuses at its first decision, and the battle
    # is scored as the witness's forfeit.
    for missing in ("wall", "gate"):
        partial = deepcopy(state)
        partial["mode"]["fortifications"] = [piece for piece in state["mode"]["fortifications"]
                                             if piece["kind"] != missing]
        with pytest.raises(ProtocolError, match="siege assault"):
            setup.check_battle(scenario, partial)
    for broken in ({"ok": False, "error": "siege assault needs the player attacking"}, None):
        state["setup"]["siege_assault"] = broken
        with pytest.raises(ProtocolError, match="siege assault"):
            setup.check_battle(scenario, state)
