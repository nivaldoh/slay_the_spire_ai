"""The siege-attack interface (scenario field siege_assault) and the ksl-emp-siege-a-v1 declaration.

Reference: the 2026-11-08 siege-attack design (runs/siege-evals-20261108/final-izmail.md,
Infrastructure I2-I5) and portfolio.md S10; the getters and orders are CA's
battle_building.html, battle_unit.html and battle_unitcontroller.html (besiege_building and
attack_building(building, piece index, move fast)), and lib_battle_manager.lua, which puts every
gate building in the wall list too. The Lua tests run the mod's real definitions under Lua 5.1
against a fake engine; no battle has read any of these getters (integration.md, Unverified), so
they show what the mod does with the documented answers, not that the engine gives them. The
Python tests show that only a siege the player attacks with the opt-in gets the new fields,
orders, prompt lines and reply schema, that only the llm controller is offered the siege orders
(the commander and a team member read the fort as facts), and that every other request is
unchanged.
"""

import hashlib
import json
from copy import deepcopy

import pytest
from lupa.lua51 import LuaError
from wh3_fixtures import FakeSend, observation, opening
from wh3_lua import load_battle, runtime
from wh3_siege_attack import SLOTS, first_observation, later

from gameai.ledger import Ledger
from twwarhammer3.battle import commander, configured, controllers, escalade, llm, play, setup, team
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
    counted as a wall piece too; towers dropped; position() (a pivot) used for the centre; an
    unreadable health given as hp 0, which every reader takes for a destroyed piece."""
    lua, fn = mod()
    g = lua.globals()
    lua.execute("walls.west = building('west', -300, -95, false, ERROR)"
                "; lists.wall = {walls.east, gate, walls.climb, walls.middle, walls.west}")
    fort = deepcopy(FORT)
    del fort[1]["hp"]  # w1, the west piece, whose health() fails
    assert dict(fn["setup_fortifications"]().items()) == {"gate": 1, "wall": 5, "tower": 3}
    assert rows(fn["fortification_reading"]()) == fort
    # A piece leaves its list and the rest reorder: every id still names its own building.
    lua.execute("lists.wall = {walls.west, walls.climb, gate, walls.east}"
                "; lists.tower = {towers[3], towers[1]}")
    assert rows(fn["fortification_reading"]()) == fort
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
    enemy's on_wall shown; can_climb re-read or a failed read shown as false; an enemy given
    can_climb or can_siege."""
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
                        can_climb_walls = true, has_attribute = function(key) return true end,
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
    record = dict(record.items())
    assert record["on_wall"] is True and not {"can_climb", "can_siege"} & set(record)
    assert "on_wall" not in dict(roster.items())
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


def test_a_siege_attack_lists_no_slot_and_a_defence_keeps_its_slots():
    """Wrong versions: the slots left out only in render_mode, so the scripts, the commander and
    team members of the attack still read the defender's slots and build timers; the slots left
    out by role, not by the opt-in, which also drops them from a siege attacked without it. The
    stub's slot list returns the eight rows the 2026-10-14 attack smoke read at 59.9 s
    (wh3_siege_attack)."""
    recorded = SLOTS[59900]
    lists = {"slots.Size": len(recorded),
             "slot setup": ";".join(f"{slot['type']}|{slot['x']}|{slot['z']}|"
                                    for slot in recorded),
             "slot rows": ";".join(f"{-1 if 'options' in slot else 0}"
                                   f"|{str('building_s' in slot).lower()}"
                                   f"|{slot.get('building_s', 0)}|false|false"
                                   for slot in recorded)}
    sections = {}
    for role, opt_in in (("attacker", True), ("attacker", False), ("defender", False)):
        lua, fn = mod()
        lua.execute(f"state.info.role = '{role}'")
        for key, value in lists.items():
            lua.globals().contexts[key] = value
        if opt_in:
            fn["setup_fortifications"]()
        sections[role, opt_in] = dict(fn["mode_section"]().items())
    assert "slots" not in sections["attacker", True]
    for kept in (("attacker", False), ("defender", False)):
        assert [slot["id"] for slot in rows(sections[kept]["slots"])] == [
            f"s{index}" for index in range(1, 9)]


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
    """Wrong versions: a non-climber accepted on a wall, an order on a destroyed target; a
    non-climber refused on a tower (only a wall piece needs climbing, as SIEGE_ORDERS tells the
    model and the mod's apply_siege checks)."""
    validate_orders([{"unit": "f2", "type": "besiege", "target": "w3", "run": True},
                     {"unit": "f12", "type": "besiege", "target": "g1", "run": True},
                     {"unit": "f13", "type": "attack_building", "target": "g1", "run": False}],
                    SIEGE)
    validate_orders([{"unit": "f12", "type": "besiege", "target": "t1", "run": True}], SIEGE)
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
    and role attacker): wh3_fixtures.observation() with that mode, one decision."""
    state = observation()
    state["mode"] = {"type": "land_normal", "role": "attacker", "timeout_winner": "enemy",
                     "objectives": "Objectives: (placeholder for the engine's objective text)"}
    return [state]


def siege_attack_without_opt_in():
    """A siege the player attacks without siege_assault, as the 2026-10-14 attack smoke read
    it: the fixture without the fields only the opt-in adds, then 10 s on with the enemy's
    tickets down 45, which the opt-in's ticket change would show."""
    state = first_observation()
    for key in ("fortifications", "vehicles", "enemy_structures"):
        del state["mode"][key]
    for unit in state["friendly"] + state["enemy"]:
        for key in ("on_wall", "can_climb", "can_siege"):
            unit.pop(key, None)
    return [state, later(state, 15300, mode={"tickets": [
        dict(state["mode"]["tickets"][0], tickets=955)]})]


def siege_attack_during_a_defender_build():
    """siege_attack_without_opt_in with the slot rows that smoke read at 59.9 s: the attacker's
    list gives no option name for s6, the tower the defender is building, and v22 shows it as
    "building None, 69 s left"."""
    states = siege_attack_without_opt_in()
    for state in states:
        state["mode"]["slots"] = deepcopy(SLOTS[59900])
    return states


# The whole request llm sent at each decision with e918091's code, before the siege orders
# existed; the siege cases re-frozen that way (e918091's play.public and llm) on the 2026-11-09
# fixture.
BODY_SHA256 = {
    "land_attack": ["a30bf9dbe83ed0d88af0fc929112775927485e8647fe58c1d8f1f2ee2ff29854"],
    "siege_attack_without_opt_in": [
        "66ff4981dc7df431c887e5974ce3c90797ba0cb4c4323c69fc8ab0cae10060dc",
        "4a567d98c9399f1547d26833c6ea65c478072f53014e25a92d690fe400f65487"],
    "siege_attack_during_a_defender_build": [
        "06c88417de35a5bd303c9916062290e681d5a6923b63a7488dec910658151d19",
        "07bd87085a3bdf8758ad255cec2d1dbedcd8a5d731fcf396585e791774849168"]}


@pytest.mark.parametrize("make", [land_attack, siege_attack_without_opt_in,
                                  siege_attack_during_a_defender_build])
def test_a_battle_the_player_attacks_without_the_opt_in_sends_the_same_request(make, tmp_path):
    """Wrong versions: the siege schema or orders for every battle the player attacks; the
    ticket change shown without the opt-in; a build without an option name shown differently
    from v22."""
    states = make()
    agent, send = model(tmp_path, *[WAIT] * len(states))
    for state in states:
        agent.decide(play.public(state, {}))
    assert all(body["text"]["format"]["schema"] == llm.REPLY_SCHEMA for body in send.bodies)
    assert [hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            for body in send.bodies] == BODY_SHA256[make.__name__]


# The fort as facts, in every controller's state under the opt-in.
FORT_LINES = ("Fortifications:\n- g1 gate at (-32, -16): 100% health",
              "- t1 tower at (-192, -81): 100% health, held by enemy",
              "- t2 tower at (-62, -31): 100% health, held by nobody",
              "Your siege vehicles: v1 battering_ram at (0, -231), crewed by f4.",
              "Enemy-built structures: none.")


def test_a_siege_attack_shows_the_fort_and_offers_the_siege_orders(tmp_path):
    agent, send = model(tmp_path, CLIMB)
    view = play.public(SIEGE, setup.scenarios()["ksl-emp-siege-a-v1"])
    assert agent.decide(view) == json.loads(CLIMB)["orders"]
    body = send.bodies[0]
    assert body["text"]["format"]["schema"] == llm.SIEGE_REPLY_SCHEMA
    kinds = [item["properties"]["type"]["enum"][0] for item in
             body["text"]["format"]["schema"]["properties"]["orders"]["items"]["anyOf"]]
    assert kinds[-2:] == ["besiege", "attack_building"]
    prompt = body["input"][0]["content"]
    for line in FORT_LINES + (llm.SIEGE_ORDERS,):
        assert line in prompt
    assert "can climb walls" in prompt and "cannot climb walls" in prompt
    assert "e2 halberdiers (infantry) at (-49, -21)" in prompt and "on the wall" in prompt
    assert "Building slots" not in prompt and "None" not in prompt
    # Nothing hidden, historical or about ladders' engine effect reaches the model.
    lowered = prompt.lower()
    for word in setup.scenarios()["ksl-emp-siege-a-v1"]["withheld"] + [
            "climbing", "hidden garrison", "staging pocket", "ladder"]:
        assert word not in lowered
    assert llm.describe_orders(json.loads(CLIMB)["orders"]) == "f2 besiege w3 run"


def test_the_commander_and_team_members_see_the_fort_but_no_siege_order(tmp_path, monkeypatch):
    """Wrong versions: a controller told of besiege or attack_building, which its reply schema
    cannot express (the commander's plans), or offered them on a team member's projected view,
    which has no can_climb (a team_llm_rules member, and a configured team's llm_rules leaf, a
    plain LLMPolicy); a member's gate besiege accepted though its schema has no siege order."""
    plan = json.dumps({"assignments": [], "abilities": [], "reason": "wait", "notes": None})
    send = FakeSend(plan)
    planner = commander.CommanderPolicy("gpt-6-luna", "low",
                                        Ledger(tmp_path / "ledger.jsonl", 1.0), send=send)
    view = play.public(SIEGE, setup.scenarios()["ksl-emp-siege-a-v1"])
    try:
        planner.decide(view)
        planner.pending.result(timeout=5)
    finally:
        planner.close()
    gate = json.dumps({"orders": [{"unit": "f2", "type": "besiege", "target": "g1", "run": True}],
                       "reason": "gate", "notes": None})
    member_send, configured_send = FakeSend(gate, gate, gate), FakeSend(gate, gate, gate)
    monkeypatch.setattr(controllers, "api_key", lambda provider: "test-only")
    monkeypatch.setattr(controllers, "post", lambda key, body, **options: configured_send(body))
    path, ledger = tmp_path / "controller.json", tmp_path / "configured.jsonl"
    path.write_text(json.dumps({"type": "team", "army_owner": "rest", "members": {
        "climbers": {"unit_types": ["wh3_main_ksl_inf_armoured_kossars_0"],
                     "controller": {"type": "llm_rules@gpt-6-luna/low"}},
        "rest": {"unit_types": None, "controller": {"type": "llm_rules@gpt-6-luna/low"}}}}))
    ledger.touch()
    built = configured.factory(path, {"policy": "configured", "controller_config": str(path),
                                      "scenario": "ksl-emp-siege-a-v1", "provider": "openai",
                                      "budget_usd": 1, "ledger": str(ledger)})()
    try:
        members = [team.TeamLLM("gpt-6-luna", "low", Ledger(tmp_path / "member.jsonl", 1.0),
                                send=member_send), built.members["climbers"].policy]
        assert type(members[1]) is llm.LLMPolicy
        for member in members:
            assert member.decide(team.project(view, {"f2"})) == []
            assert "unknown order type 'besiege'" in member.metadata()["dropped"][0]
    finally:
        built.close()
    for body, schema in ((send.bodies[0], commander.REPLY_SCHEMA),
                         (member_send.bodies[0], llm.REPLY_SCHEMA),
                         (configured_send.bodies[0], llm.REPLY_SCHEMA)):
        assert body["text"]["format"]["schema"] == schema
        prompt = body["input"][0]["content"]
        for line in FORT_LINES:
            assert line in prompt
        for word in ("besiege", "attack_building", "Siege orders"):
            assert word not in prompt
    assert "can climb walls" in send.bodies[0]["input"][0]["content"]


def test_only_a_view_with_the_climb_fields_is_offered_the_siege_orders(tmp_path):
    """Wrong version: a team member told apart by input_version, so a projected view without it
    (no can_climb, which validation reads for a wall besiege) is offered the siege orders."""
    view = play.public(SIEGE, setup.scenarios()["ksl-emp-siege-a-v1"])
    projected = team.project(view, {"f2", "f13"})
    del projected["input_version"]
    assert not [unit for unit in projected["friendly"] if "can_climb" in unit]
    for state, schema in ((projected, llm.REPLY_SCHEMA), (view, llm.SIEGE_REPLY_SCHEMA)):
        agent, send = model(tmp_path, WAIT)
        agent.decide(state)
        body = send.bodies[0]
        assert body["text"]["format"]["schema"] == schema
        prompt = body["input"][0]["content"]
        assert FORT_LINES[0] in prompt
        assert (llm.SIEGE_ORDERS in prompt) is (schema is llm.SIEGE_REPLY_SCHEMA)


def test_an_accepted_siege_order_replaces_the_move_the_prompt_says_a_unit_holds(tmp_path):
    move = json.dumps({"orders": [{"unit": "f2", "type": "move", "x": -230, "z": -238,
                                   "facing": None, "width": None, "run": False,
                                   "queue": False}], "reason": "stage", "notes": None})
    agent, _ = model(tmp_path, move, CLIMB)
    view = play.public(SIEGE, {})
    for expected in ("move", "besiege"):
        agent.decide(view)
        agent.acknowledge({"request": "r", "applied_ms": 5300, "results": [
            {"index": 1, "unit": "f2", "ok": True}]}, {"think_s": 1, "delay_ms": 0})
        assert {unit: order["type"] for unit, order in agent.ordered.items()} == {"f2": expected}


def unit_row(body, unit):
    return next(line for line in body["input"][0]["content"].splitlines()
                if line.startswith(f"- {unit} "))


def turn(agent, state, accepted=()):
    """One decision on ``state``, then an ack accepting ``accepted``'s orders in reply order."""
    agent.decide(play.public(state, setup.scenarios()["ksl-emp-siege-a-v1"]))
    agent.acknowledge({"request": "r", "applied_ms": state["time_ms"], "results": [
        {"index": index, "unit": unit, "ok": True, "queued": False}
        for index, unit in enumerate(accepted, 1)]}, {"think_s": 1, "delay_ms": 0})


def test_the_prompt_keeps_an_accepted_siege_order_until_a_new_order_or_the_state_ends_it(
        tmp_path):
    """Wrong versions: the order dropped once accepted, so the row reads "no order" (which the
    system prompt says means the unit stands until ordered); the order kept after a later
    accepted move, once its besieger is on the wall, or once its target is at 0%."""
    sieges = json.dumps({"orders": [
        {"unit": "f2", "type": "besiege", "target": "w3", "run": True},
        {"unit": "f3", "type": "besiege", "target": "w3", "run": True},
        {"unit": "f5", "type": "besiege", "target": "w3", "run": True},
        {"unit": "f13", "type": "attack_building", "target": "g1", "run": False}],
        "reason": "climb", "notes": None})
    move = json.dumps({"orders": [{"unit": "f2", "type": "move", "x": -100, "z": -120,
                                   "facing": None, "width": None, "run": False,
                                   "queue": False}], "reason": "back", "notes": None})
    agent, send = model(tmp_path, sieges, move, WAIT, WAIT, WAIT)
    turn(agent, SIEGE, ("f2", "f3", "f5", "f13"))
    climbing = later(SIEGE, 15000, f2={"x": -190.0, "z": -160.0, "state": ["moving", "running"]},
                     f13={"ammo": 19})
    turn(agent, climbing, ("f2",))
    unsure = " (the state cannot confirm it is still carried out)"
    assert "last siege order: besiege w3 at 5 s" + unsure in unit_row(send.bodies[1], "f2")
    assert "no order" not in unit_row(send.bodies[1], "f2")
    assert "last siege order: attack building g1 at 5 s" + unsure in unit_row(send.bodies[1], "f13")
    # The accepted move replaces f2's besiege: heading to its point, then no order once there.
    heading = later(climbing, 25000, f2={"x": -150.0, "z": -140.0, "dest": [-100.0, -120.0]})
    turn(agent, heading)
    assert "heading to (-100, -120)" in unit_row(send.bodies[2], "f2")
    assert "last siege order" not in unit_row(send.bodies[2], "f2")
    # f5 is on the wall, so its besiege is done; f3, still below, keeps its line.
    arrived = later(heading, 35000, f2={"x": -100.0, "z": -120.0, "dest": None, "state": []},
                    f5={"on_wall": True})
    turn(agent, arrived)
    assert "no order" in unit_row(send.bodies[3], "f2")
    assert "last siege order" not in unit_row(send.bodies[3], "f5")
    assert "last siege order: besiege w3" in unit_row(send.bodies[3], "f3")
    # w3 at 0%: the besiege on it is no longer shown; f13's on g1 still is.
    fallen = later(arrived, 45000)
    fallen["mode"]["fortifications"][3]["hp"] = 0
    turn(agent, fallen)
    assert "last siege order" not in unit_row(send.bodies[4], "f3")
    assert "no order" in unit_row(send.bodies[4], "f3")
    assert "last siege order: attack building g1" in unit_row(send.bodies[4], "f13")


def test_a_siege_order_leaves_the_prompt_once_the_gun_is_empty_the_unit_routs_or_the_target_goes(
        tmp_path):
    """Wrong versions: an attack_building kept after the gun's ammunition reaches 0; a besiege
    kept after its unit routs, so it shows again once the unit rallies; a besiege kept once
    mode.fortifications no longer lists its target. Once the order ends, the row reads "no
    order"."""
    sieges = json.dumps({"orders": [
        {"unit": "f6", "type": "besiege", "target": "w1", "run": True},
        {"unit": "f7", "type": "besiege", "target": "w4", "run": True},
        {"unit": "f13", "type": "attack_building", "target": "g1", "run": False}],
        "reason": "climb", "notes": None})
    agent, send = model(tmp_path, sieges, WAIT, WAIT, WAIT)
    turn(agent, SIEGE, ("f6", "f7", "f13"))
    held = later(SIEGE, 15000)
    turn(agent, held)
    assert [unit_row(send.bodies[1], unit).count("last siege order") for unit in
            ("f6", "f7", "f13")] == [1, 1, 1]
    ended = later(held, 25000, f7={"state": ["routing"]}, f13={"ammo": 0})
    ended["mode"]["fortifications"] = [piece for piece in ended["mode"]["fortifications"]
                                       if piece["id"] != "w1"]
    turn(agent, ended)
    assert "no order" in unit_row(send.bodies[2], "f6")
    assert "no order" in unit_row(send.bodies[2], "f13")
    turn(agent, later(ended, 35000, f7={"state": ["idle"]}))
    assert "no order" in unit_row(send.bodies[3], "f7")


def test_a_siege_attack_shows_the_ticket_change_since_the_last_decision(tmp_path):
    """Wrong versions: the change counted from the starting count; "+0" shown for an unchanged
    count (in 20 of the 24 recorded siege traces the count never left 1,000). Outside the opt-in
    no change is shown (siege_attack_without_opt_in's second request hash)."""
    agent, send = model(tmp_path, WAIT, WAIT, WAIT, WAIT)
    scenario = setup.scenarios()["ksl-emp-siege-a-v1"]
    for time_ms, count in ((5300, 1000), (15300, 955), (25300, 910), (35300, 910)):
        tickets = [dict(SIEGE["mode"]["tickets"][0], tickets=count)]
        agent.decide(play.public(later(SIEGE, time_ms, mode={"tickets": tickets}), scenario))
    assert [next(line for line in body["input"][0]["content"].splitlines()
                 if line.startswith("Tickets")) for body in send.bodies] == [
        "Tickets: enemy 1000.", "Tickets: enemy 955 (-45 since your last turn).",
        "Tickets: enemy 910 (-45 since your last turn).", "Tickets: enemy 910."]


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
