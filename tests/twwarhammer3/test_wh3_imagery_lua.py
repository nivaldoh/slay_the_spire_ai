"""The stills director, mod/script/_lib/mod/twwarhammer3_imagery.lua, under Lua 5.1 with a stubbed
camera and battle clock: which moments it picks, how it aims and what a failure records."""
import pytest
from wh3_lua import MOD, runtime


def test_loading_the_shared_mod_scripts_touches_no_file():
    # Battle, frontend and campaign loads all run _lib/mod at top level (integration.md),
    # including the owner's own campaigns while the mod list is active.
    lua = runtime()
    lua.execute("""
        touched = {}
        io.open = function(path) touched[#touched + 1] = "open " .. path; return nil, "blocked" end
        os.remove = function(path) touched[#touched + 1] = "remove " .. path end
        os.rename = function(path) touched[#touched + 1] = "rename " .. path end
    """)
    for path in sorted((MOD / "script/_lib/mod").glob("*.lua")):
        lua.execute(path.read_text())
    assert list(lua.globals().touched.values()) == []

@pytest.fixture
def imagery_lua():
    lua = runtime()
    lua.execute('''
        clock_ms, captures, callbacks = 1000, 0, {}
        function v(x, y, z)
            return {get_x = function() return x end, get_y = function() return y end,
                    get_z = function() return z end}
        end
        camera = {position = function() return position end, target = function() return target end,
            move_to = function(_, p, t) position, target = p, t end}
        bm = {battle = {get_terrain_height = function() return 20 end,
                       enable_cinematic_camera = function(_, value) cinematic = value end,
                       time_elapsed_ms = function() return clock_ms end},
              camera = function() return camera end,
              repeat_real_callback = function(_, fn, interval, name) callbacks[name] = fn end,
              remove_real_callback = function(_, name) callbacks[name] = nil end}
        common = {take_screenshot = function() error('Native capture must not run') end}
        twwarhammer3_json = {encode = function(record) saved = record; return 'json' end}
        io = {open = function() return {write = function() end, close = function() end} end}
        os.remove = function() end
        os.rename = function() return true end
        function sample(time, units, terminal, enemies)
            clock_ms = time
            twwarhammer3_imagery({job = 'j', battle = 'b', time_ms = time,
                friendly = units, enemy = enemies or {}, terminal = terminal}, {f1 = 'Lord'})
        end
    ''')
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_imagery.lua").read_text())
    return lua


def test_lua_capture_triggers_use_public_cluster_and_keep_camera_failures(imagery_lua):
    lua = imagery_lua
    lua.execute("sample(1000, {{id='f1', x=0, z=0, men=1, state={}}})")
    g = lua.globals()
    assert g.saved.stills[1].status == "pending" and g.captures == 0
    assert g.cinematic is True
    lua.execute("clock_ms = 1500; callbacks.wh3_still_opening()")
    assert g.saved.stills[1].time_ms == 1500 and g.captures == 0
    assert g.saved.stills[1].status == "capture_ready"
    lua.execute('''sample(35000, {
        {x=0,z=0,men=1,state={'melee'}}, {x=10,z=10,men=1,state={'melee'}},
        {x=20,z=20,men=1,state={'melee'}}, {x=1000,z=1000,men=1,state={'melee'}}})''')
    assert g.saved.stills[2].trigger == "first_contact"
    assert g.target.get_x() == g.target.get_z() == 10
    lua.execute("callbacks.wh3_still_first_contact()")
    lua.execute("sample(36000, {{x=0,z=0,men=1,state={'routing'}}})")
    assert g.saved.stills[3].status == "throttled" and g.captures == 0
    lua.execute('''
        camera.move_to = function() error('camera unavailable') end
        sample(37000, {{x=0,z=0,men=1,state={}}}, true)
        sample(38000, {{x=0,z=0,men=1,state={}}}, true)
    ''')
    assert len(g.saved.stills) == 4
    assert g.saved.stills[4].status == "capture_failed"
    assert "camera unavailable" in g.saved.stills[4].error


def test_approach_still_precedes_contact_and_shares_its_slot(imagery_lua):
    lua = imagery_lua
    lua.execute('''
        sample(1000, {{id='f1',x=0,z=0,men=10}}, false, {{id='e1',x=150,z=0,men=10}})
        sample(35000, {{id='f1',x=0,z=0,men=10}}, false, {{id='e1',x=90,z=0,men=10}})
        callbacks.wh3_still_approach()
    ''')
    shot = lua.globals().saved.stills[2]
    assert shot.trigger == "approach" and shot.distance_m == 90
    assert list(shot.focus_units.values()) == ["f1", "e1"]
    assert shot.requested_camera.position[2] == 48  # 28 m above the target terrain
    assert shot.requested_camera.target[2] == 23
    assert shot.requested_camera.position[1] < 0  # behind the friendly formation
    lua.execute('''
        sample(70000, {{id='f1',x=0,z=0,men=10,state={'melee','under_fire'}}})
        sample(100000, {{id='f1',x=0,z=0,men=10,state={'routing'}}})
        sample(101000, {{id='f1',x=0,z=0,men=10}}, true)
    ''')
    assert len(lua.globals().saved.stills) == 4


@pytest.mark.parametrize("change", ["hidden", "retreat", "routing", "melee"])
def test_approach_requires_recent_visible_closing_units(imagery_lua, change):
    lua = imagery_lua
    lua.execute('''
        friends = {{id='f1',x=0,z=0,men=10}}
        enemies = {{id='e1',x=90,z=0,men=10}}
        sample(1000, friends, false, enemies)
    ''')
    if change == "hidden":
        lua.execute("sample(34000, friends); enemies[1].x = 80")
    elif change == "retreat":
        lua.execute("enemies[1].x = 95")
    elif change == "routing":
        lua.execute("enemies[1].x = 80; enemies[1].state = {'routing'}")
    else:
        lua.execute("enemies[1].x = 80; friends[1].state = {'melee'}")
    lua.execute("sample(35000, friends, false, enemies)")
    assert all(shot.trigger != "approach" for shot in lua.globals().saved.stills.values())


def test_incoming_fire_uses_action_slot_without_inventing_approach(imagery_lua):
    lua = imagery_lua
    lua.execute('''
        sample(1000, {{id='f1',x=0,z=0,men=10}})
        sample(35000, {{id='f1',x=0,z=0,men=10,state={'under_fire'}}})
        sample(70000, {{id='f1',x=0,z=0,men=10,state={'melee'}}})
    ''')
    assert len(lua.globals().saved.stills) == 2
    assert lua.globals().saved.stills[2].trigger == "incoming_fire"


def test_early_fire_defers_action_capture_instead_of_consuming_slot(imagery_lua):
    lua = imagery_lua
    lua.execute('''
        sample(5000, {{id='f1',x=0,z=0,men=10}})
        sample(16000, {{id='f1',x=10,z=20,men=10,state={'under_fire'}}})
        sample(17000, {{id='f1',x=10,z=20,men=10,state={'under_fire'}}})
    ''')
    assert len(lua.globals().saved.stills) == 2
    assert lua.globals().saved.stills[2].status == "throttled"
    lua.execute('''
        sample(35000, {{id='f1',x=10,z=20,men=10,state={'under_fire'}},
                       {id='f2',x=1000,z=1000,men=10}})
        callbacks.wh3_still_incoming_fire()
    ''')
    g = lua.globals()
    assert len(g.saved.stills) == 2
    assert g.saved.stills[2].status == "capture_ready"
    assert g.saved.stills[2].deferred_from.time_ms == 16000
    assert g.target.get_x() == 10 and g.target.get_z() == 20
