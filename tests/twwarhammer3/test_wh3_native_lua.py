"""The battle script's experimental native multiplayer modes (session ``multiplayer``): the
whole script runs under Lua 5.1 against a stub engine whose mutators record and raise; and
the policy view without their evaluator-only ``native`` identities.

Alliance 1 has two armies of two same-type units each and the local player owns army 2
(``local_army() == 2``); alliance 2 is the enemy. These are stub values: live local_army
values, ui ids across peers and order replication need the plan's live checks
(docs/twwarhammer3/native-multiplayer.md, steps 4 and 5).
"""
import json

import pytest
from wh3_lua import BATTLE, MOD, runtime

from twwarhammer3.battle import play
from twwarhammer3.engine import worker

BRIDGE = "C:/wh3-agent/bridge/"

# A stub object answers only the methods it lists. Any other method is taken for a mutator:
# it records "<kind>:<name>" in `trapped` and raises, so the script's pcalls cannot hide it.
ENGINE = r"""
trapped, calls, files, phases, callbacks = {}, {}, {}, {}, {}
now, decided, is_multiplayer = 1000, false, true
speed = 1  -- battle:current_battle_speed()
function trap(kind, methods)
    return setmetatable(methods, {__index = function(_, name)
        return function()
            trapped[#trapped + 1] = kind .. ":" .. name
            error("mutator " .. kind .. ":" .. name)
        end
    end})
end
function const(value) return function() return value end end
function list(kind, items)
    return trap(kind, {count = const(#items), item = function(_, i) return items[i] end})
end
function position(x, z) return {get_x = const(x), get_z = const(z)} end

UNIT_READS = {"unique_ui_id", "type", "unit_class", "is_commanding_unit", "can_fly",
    "is_currently_flying", "bearing", "number_of_men_alive", "initial_number_of_men",
    "unary_hitpoints", "is_routing", "is_shattered", "is_wavering", "is_in_melee",
    "is_under_missile_attack", "is_moving", "is_idle", "is_hidden", "is_unstable", "is_crumbling",
    "is_rampaging", "is_moving_fast", "missile_range", "slow_speed", "fast_speed", "ammo_left",
    "starting_ammo", "fatigue_state", "ordered_width", "can_use_behaviour", "is_behaviour_active",
    "owned_non_passive_special_abilities", "can_perform_special_ability", "current_target",
    "ordered_position", "is_leaving_battle", "is_deployed", "is_deploying", "is_valid_target",
    "alliance_index", "can_reach_position", "is_visible_to_alliance"}
-- Every unit has the same type; x nil makes its position unreadable. `alliance` is its
-- alliance_index, which the script reads only for reinforcement army units.
function unit(id, x, alliance)
    local values = {unique_ui_id = id, type = "wh_main_emp_inf_spearmen_0",
        unit_class = "inf_mel", number_of_men_alive = 60, initial_number_of_men = 60,
        bearing = 0, unary_hitpoints = 1, is_routing = false, is_shattered = false,
        is_in_melee = false, is_moving = false,
        is_deployed = true, is_valid_target = true, can_reach_position = true,
        is_visible_to_alliance = true, alliance_index = alliance}
    local methods = {position = function()
        return x and position(x, 7.654321) or error("position unreadable")
    end}
    for _, name in ipairs(UNIT_READS) do methods[name] = const(values[name]) end
    return trap("unit", methods)
end
function army(faction, winds, unique_id, units)
    return trap("army", {units = function() return list("units", units) end,
        faction_key = const(faction), winds_of_magic_current = const(winds),
        winds_of_magic_reserve = const(0), unique_id = const(unique_id)})
end
function controller()
    return trap("controller", {
        add_units = function(_, unit) calls[#calls + 1] = {"add_units", unit:unique_ui_id()} end,
        take_control = function() calls[#calls + 1] = {"take_control"} end,
        release_control = function() calls[#calls + 1] = {"release_control"} end,
        goto_location = function(_, point, run)
            calls[#calls + 1] = {"goto_location", point.x, point.z, run}
        end,
    })
end
-- Lets `object` (an army) create controllers, recording each.
function grant(object)
    object.create_unit_controller = function()
        calls[#calls + 1] = {"create"}
        return controller()
    end
end
allies = army("allied_faction", 10, 501, {unit(11, 1), unit(12, 2)})
own = army("own_faction", 20, 502, {unit(21, 3.123456), unit(22, 4)})
enemy = army("enemy_faction", 30, 503, {unit(31, 5), unit(32, nil)})
alliances = list("alliances", {
    trap("alliance", {armies = function() return list("armies", {allies, own}) end}),
    trap("alliance", {armies = function() return list("armies", {enemy}) end}),
})
reinforcement_armies = {}  -- none unless a test sets some
battle = trap("battle", {
    time_elapsed_ms = function() return now end,
    current_battle_speed = function() return speed end,
    is_multiplayer = function() return is_multiplayer end,
    is_replay = const(false), is_from_campaign = const(false), is_quest_battle = const(false),
    is_tutorial = const(false), is_spectator = const(false),
    battle_boundaries = function() return position(-64, -64), position(64, 64) end,
    get_terrain_height = const(0), is_area_clear = const(true),
    reinforcements = function()
        return trap("reinforcements", {
            reinforcement_army_count = function() return #reinforcement_armies end,
            reinforcement_army = function(_, k)
                return trap("reinforcement", {army = const(reinforcement_armies[k])})
            end})
    end,
    remaining_conflict_time = const(-1), battle_outcome_decided = function() return decided end,
    victorious_alliance = const(1), local_alliance = const(1), is_draw = const(false),
})
bm = trap("bm", {
    battle = battle,
    register_phase_change_callback = function(_, phase, fn) phases[phase] = fn end,
    repeat_real_callback = function(_, fn, ms, name) callbacks[name] = fn end,
    repeat_callback = function(_, fn, ms, name) callbacks[name] = fn end,
    remove_process = function(_, name) callbacks[name] = nil end,
    get_current_phase_name = const("Deployed"), alliances = const(alliances),
    local_alliance = const(1), local_army = const(2),
    -- As vanilla lib_battle_manager.lua: army 1 of the local alliance.
    get_player_alliance = function() return alliances:item(1) end, get_player_army = const(allies),
    get_first_non_player_army = const(enemy),
})
common = trap("common", {get_context_value = function(_, _, expression)
    -- The one context expression the script evaluates for its effect (apply_build).
    if string.find(expression, "PrimaryAction", 1, true) then
        trapped[#trapped + 1] = "common:PrimaryAction"
    end
end})
core = trap("core", {get_ui_root = function() return trap("uicomponent", {}) end})
function find_uicomponent() return trap("uicomponent", {}) end
twwarhammer3_ui = trap("ui", {find = function() return trap("uicomponent", {}) end})
function v(x, y, z) return {x = x, y = y, z = z} end
io = {open = function(path, mode)
    if mode == "r" then
        return files[path] and {read = function() return files[path] end, close = function() end}
    end
    if mode == "w" or not files[path] then files[path] = "" end
    return {write = function(_, text) files[path] = files[path] .. text; return true end,
            close = function() end}
end}
os.remove = function(path)
    if not files[path] then return nil, "no such file" end
    files[path] = nil
    return true
end
os.rename = function(from, to) files[to], files[from] = files[from], nil; return true end
"""


def battle(session, setup=""):
    """The whole battle script loaded with `session` as its session.json; `setup` is Lua run
    after the stub engine is made."""
    lua = runtime()
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())
    lua.execute(ENGINE + setup)
    lua.globals().files[BRIDGE + "session.json"] = json.dumps({"schema": 1, "job": "j", **session})
    lua.execute(BATTLE.read_text())
    return lua.globals()


def observation(g):
    return json.loads(g.files[BRIDGE + "observation.json"])


def logged(g):
    return [line.split("] ", 1)[1] for line in (g.files[BRIDGE + "mod.log"] or "").splitlines()]


def send(g, name, message):
    g.files[BRIDGE + name] = json.dumps({"schema": 1, "job": "j", **message})
    g.callbacks["twwarhammer3_poll"]()


def inactive(g):
    return (len(g.phases) == len(g.callbacks) == 0 and g.twwarhammer3_inject is None
            and g.files[BRIDGE + "observation.json"] is None)


def test_without_multiplayer_army_one_is_ours_and_controlled_from_the_start():
    # Single-player stays as it was: army 1 (not local_army()), controllers at registration.
    g = battle({}, """
        is_multiplayer = false
        grant(allies)
        bm.modify_battle_speed = function(_, ...) calls[#calls + 1] = {"speed", ...} end
    """)
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    seen = observation(g)
    assert [unit["x"] for unit in seen["friendly"]] == [1, 2]
    assert [unit["id"] for unit in seen["enemy"]] == ["e1", "e2"] and "native" not in seen
    assert [list(call.values()) for call in g.calls.values()] == [
        ["create"], ["add_units", 11], ["take_control"],
        ["create"], ["add_units", 12], ["take_control"], ["speed", 1, True]]
    assert len(g.trapped) == 0 and g.twwarhammer3_inject is not None


@pytest.mark.parametrize("mode", ["observe", "control"])
def test_the_session_an_owned_worker_writes_activates_the_battle_script(mode):
    # engine/worker.py run() publishes {**SESSION, "multiplayer": mode} as session.json.
    g = battle({**worker.SESSION, "multiplayer": mode})
    [line] = logged(g)
    assert line.startswith("loaded battle ") and not inactive(g)
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    assert observation(g)["native"]["mode"] == mode


@pytest.mark.parametrize("value,shown", [("spectate", "spectate"), (True, "true")])
def test_an_unknown_multiplayer_mode_stays_inactive(value, shown):
    g = battle({"multiplayer": value})
    assert logged(g) == [f"inactive: multiplayer {shown}"] and inactive(g)


@pytest.mark.parametrize("mode", ["observe", "control"])
@pytest.mark.parametrize("field,value", [("autostart", True), ("stills", True),
                                         ("custom", {"kind": "battery_evacuation"})])
def test_multiplayer_modes_refuse_fields_that_change_the_battle_or_the_camera(mode, field, value):
    g = battle({"multiplayer": mode, field: value})
    assert logged(g) == [f"inactive: multiplayer {mode} forbids {field}"] and inactive(g)


@pytest.mark.parametrize("multiplayer", [True, False])
def test_observe_shows_the_local_army_as_friendly_and_never_acts(multiplayer):
    # A single-player battle is allowed too, for a local passive check.
    g = battle({"multiplayer": "observe"}, f"is_multiplayer = {str(multiplayer).lower()}")
    assert g.twwarhammer3_inject is None
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    assert list(g.trapped.values()) == []
    seen = observation(g)
    # friendly is army 2 (local_army) only; army 1's units are allies, in neither list.
    assert [(unit["id"], unit["x"]) for unit in seen["friendly"]] == [("f1", 3.1), ("f2", 4)]
    assert [unit["id"] for unit in seen["enemy"]] == ["e1", "e2"]
    assert [unit["id"] for unit in seen["enemy_roster"]] == ["e1", "e2"]
    assert seen["armies"]["player"]["faction"] == "own_faction" and seen["magic"]["current"] == 20
    native = seen["native"]
    assert {key: value for key, value in native.items() if key != "units"} == {
        "mode": "observe", "is_multiplayer": multiplayer, "is_spectator": False,
        "local_alliance": 1, "local_army": 2, "army_unique_id": 502}
    rows = {(unit["alliance"], unit["army"], unit["index"]): unit for unit in native["units"]}
    assert {key: (row.get("id"), row.get("owner")) for key, row in rows.items()} == {
        (1, 1, 1): ("a1", "allied"), (1, 1, 2): ("a2", "allied"), (1, 2, 1): ("f1", "own"),
        (1, 2, 2): ("f2", "own"), (2, 1, 1): ("e1", "enemy"), (2, 1, 2): (None, None)}
    assert rows[1, 2, 1] == {"id": "f1", "ui_id": 21, "type": "wh_main_emp_inf_spearmen_0",
                             "alliance": 1, "army": 2, "index": 1, "owner": "own",
                             "x": 3.123456, "z": 7.654321}
    assert rows[2, 1, 2] == {"alliance": 2, "army": 1, "index": 2, "error": "position unreadable"}

    # Orders, a message and battle-time UI steps are deleted unread.
    send(g, "menu.json", {"request": "m1", "steps": [{"click": ["button_battle_start"]}]})
    send(g, "orders.json", {"battle": seen["battle"], "request": "r1", "based_on": seen["seq"],
                            "orders": [{"unit": "f1", "type": "move", "x": 0, "z": 0}],
                            "say": "hi"})
    assert g.files[BRIDGE + "orders.json"] is None and g.files[BRIDGE + "menu.json"] is None
    g.callbacks["twwarhammer3_tick"]()
    g.decided = True
    g.phases["VictoryCountdown"]()
    final = observation(g)
    assert final["result"] == "won" and "orders" not in final
    lines = logged(g)
    assert "multiplayer: dropped menu.json" in lines and "observe: dropped orders.json" in lines
    assert not [line for line in lines if "failed" in line]
    assert list(g.trapped.values()) == [] and len(g.calls) == 0


def test_the_replay_recorder_reads_magic_from_the_local_army():
    # replay.py merges recorder and observation frames into one timeline: both must say 20.
    g = battle({"multiplayer": "observe", "record_replay": True})
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    replay = g.files[BRIDGE + f"replay-{observation(g)['battle']}.jsonl"]
    frame = json.loads(replay.splitlines()[-1])
    assert [unit["id"] for unit in frame["friendly"]] == ["f1", "f2"]
    assert frame["magic"]["current"] == observation(g)["magic"]["current"] == 20
    assert list(g.trapped.values()) == []


def test_control_takes_an_own_unit_only_at_its_accepted_move_and_refuses_the_rest():
    g = battle({"multiplayer": "control"}, "grant(own)")
    assert g.twwarhammer3_inject is None
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    assert list(g.trapped.values()) == [] and len(g.calls) == 0  # no controller at startup
    seen = observation(g)
    orders = [{"unit": "f1", "type": "move", "x": 10, "z": 20},
              {"unit": "a1", "type": "move", "x": 10, "z": 20},
              {"unit": "e1", "type": "move", "x": 10, "z": 20},
              {"unit": "f2", "type": "halt"},
              {"unit": "f2", "type": "attack", "target": "e1"},
              {"unit": "f1", "type": "move", "x": 30, "z": 40, "queue": True},
              {"unit": "army", "type": "ability", "ability": "aa", "x": 1, "z": 2},
              {"unit": "f1", "type": "move", "x": 50, "z": 60, "run": True}]
    send(g, "orders.json", {"battle": seen["battle"], "request": "r1", "based_on": seen["seq"],
                            "orders": orders, "say": "hello"})
    g.callbacks["twwarhammer3_tick"]()
    results = observation(g)["orders"]["results"]
    assert [result.get("error") for result in results] == [
        None, "unknown_unit", "unknown_unit", *["unsupported_in_multiplayer"] * 4, None]
    # One controller, for f1 (army 2's first unit), taken at its first accepted move.
    assert [list(call.values()) for call in g.calls.values()] == [
        ["create"], ["add_units", 21], ["take_control"],
        ["goto_location", 10, 20, False], ["goto_location", 50, 60, True]]

    for request, control in (("r2", "restart"), ("r3", "start")):
        send(g, "orders.json", {"battle": seen["battle"], "request": request, "control": control})
        assert f"multiplayer: refused control {control}" in logged(g)
    send(g, "menu.json", {"request": "m1", "steps": [{"click": ["button_battle_start"]}]})
    assert g.files[BRIDGE + "menu.json"] is None and "multiplayer: dropped menu.json" in logged(g)
    assert set(g.callbacks) == {"twwarhammer3_poll", "twwarhammer3_tick"}
    assert list(g.trapped.values()) == []  # no advice, speed change, phase end, restart or click


def control_results(g, orders):
    """The results of one control-mode request of `orders`, sent once the battle is deployed."""
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    seen = observation(g)
    send(g, "orders.json", {"battle": seen["battle"], "request": "r1", "based_on": seen["seq"],
                            "orders": orders})
    g.callbacks["twwarhammer3_tick"]()
    return [result.get("error") for result in observation(g)["orders"]["results"]]


def test_control_takes_a_controller_only_after_a_move_passes_validation():
    g = battle({"multiplayer": "control"}, """
        grant(own)
        own:units():item(2).number_of_men_alive = const(0)
    """)
    errors = control_results(g, [{"unit": "f1", "type": "move", "x": "north", "z": 20},
                                 {"unit": "f2", "type": "move", "x": 10, "z": 20}])
    assert errors == ["bad_position", "unit_dead"]
    assert len(g.calls) == 0 and list(g.trapped.values()) == []


def test_control_refuses_a_queued_order_as_unsupported_whatever_precedes_it():
    # Single-player checks the queue's predecessor first (test_wh3_battle_lua.py).
    g = battle({"multiplayer": "control"}, "grant(own)")
    errors = control_results(g, [{"unit": "f1", "type": "move", "x": 1, "z": 2, "queue": True},
                                 {"unit": "f2", "type": "move", "x": "north", "z": 2},
                                 {"unit": "f2", "type": "move", "x": 1, "z": 2, "queue": True}])
    assert errors == ["unsupported_in_multiplayer", "bad_position", "unsupported_in_multiplayer"]
    assert len(g.calls) == 0


def test_reinforcement_armies_of_the_local_alliance_are_allies_and_the_others_enemies():
    # Rests on JUDGEMENT? engine/mailbox.py "Multiplayer allied reinforcements".
    g = battle({"multiplayer": "observe"}, """
        reinforcement_armies = {army("own_faction", 0, 504, {unit(41, 6, 1)}),
                                army("enemy_faction", 0, 505, {unit(51, 8, 2)})}
    """)
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    seen = observation(g)
    assert [unit["id"] for unit in seen["friendly"]] == ["f1", "f2"]
    assert [unit["id"] for unit in seen["enemy"]] == ["e1", "e2", "e3"]
    rows = [row for row in seen["native"]["units"] if row.get("ui_id") in (41, 51)]
    assert [(row["id"], row["alliance"], row.get("army"), row["index"], row["owner"])
            for row in rows] == [("a3", 1, "r1", 1, "allied"), ("e3", 2, "r2", 1, "enemy")]
    assert list(g.trapped.values()) == []


def test_the_policy_view_drops_the_native_identities():
    native = {"mode": "control", "units": [{"id": "a1", "ui_id": 11, "owner": "allied"}]}
    view = play.public({"seq": 4, "friendly": [], "evaluation": {}, "native": native}, {})
    assert view == {"seq": 4, "friendly": []}


def test_two_peers_owning_different_armies_compare_exact_through_the_real_seam(tmp_path):
    # The whole offline seam: each client's battle script (this stub engine) publishes
    # observation.json; the real Mailbox reads it from disk, Worker.watch sends it over
    # loopback to the real coordinator, and compare-peers reads what the coordinator wrote.
    # Owners and aliases differ by client (A owns army 1, B army 2); identities must not.
    from twwarhammer3.battle.peers import compare
    from twwarhammer3.engine.link import Coordinator, WorkerLink, token_sha256
    from twwarhammer3.engine.mailbox import Mailbox

    games = {"A": battle({"multiplayer": "observe"}, "bm.local_army = const(1)"),
             "B": battle({"multiplayer": "observe"})}
    manifest = {"match": "m1", "attempt": "a1", "expected": {},
                "clients": {client: {"token_sha256": token_sha256(f"token-{client}")}
                            for client in games}}
    with Coordinator(manifest, tmp_path / "a1", clock=lambda: 0.0) as coordinator:
        for client, g in games.items():
            link = WorkerLink(coordinator.url, f"token-{client}", match="m1", attempt="a1",
                              client=client, manifest={}, stop=lambda: None, clock=lambda: 0.0)
            link.hello()
            link.event("session", {"multiplayer": "observe"})  # worker.run's first event
            bridge = tmp_path / f"bridge-{client}"
            bridge.mkdir()
            mailbox = Mailbox(bridge, job="j")
            game_worker = worker.Worker(link, mailbox, "observe")
            g.phases["Deployed"]()
            for now in (1000, 2000):
                g.now = now
                g.callbacks["twwarhammer3_tick"]()
                (bridge / "observation.json").write_text(g.files[BRIDGE + "observation.json"])
                game_worker.watch()
            link.beat()
            assert list(g.trapped.values()) == []
    summary = compare(tmp_path / "a1")
    assert {client: counts["observations"] for client, counts in summary["clients"].items()} == {
        "A": 2, "B": 2}
    [pair] = summary["pairs"]
    assert pair["compared_times"] == 2 and pair["first_difference_ms"] is None
    # Six rows a time: five read on both sides, one failed read (2, 1, 2) on both.
    assert pair["units_compared"] == pair["exact"] == 10
    assert pair["failed_rows"] == {"A": 2, "B": 2}
    assert pair["missing"] == {"A": [], "B": []} and pair["differences"] == []


@pytest.mark.parametrize("multiplayer", [None, "observe", "control"])
def test_each_observation_carries_the_engines_speed_reading(multiplayer):
    # Single-player sets 1x itself (modify_battle_speed); the reading is the engine's after.
    g = battle({"multiplayer": multiplayer} if multiplayer else {}, "" if multiplayer else """
        is_multiplayer = false
        grant(allies)
        bm.modify_battle_speed = function(_, ...) calls[#calls + 1] = {"speed", ...} end
    """)
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    assert observation(g)["speed"] == 1
    g.speed, g.now = 0.5, 2000
    g.callbacks["twwarhammer3_tick"]()
    assert observation(g)["speed"] == 0.5
    assert list(g.trapped.values()) == []


def published_times(g, move, ticks):
    """Battle times of the observations published as the tick runs at each of `ticks`, with
    one move acknowledged at the second tick (the tick then applies it and publishes)."""
    g.now = ticks[0]
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    times, seen = [observation(g)["time_ms"]], observation(g)
    for k, now in enumerate(ticks[1:]):
        if k == 0:
            send(g, "orders.json", {"battle": seen["battle"], "request": "r1",
                                    "based_on": seen["seq"], "orders": [move]})
        g.now = now
        g.callbacks["twwarhammer3_tick"]()
        if observation(g)["time_ms"] != times[-1]:
            times.append(observation(g)["time_ms"])
    return times


TICKS = [1000, 1300, 1600, 1900, 2200, 2500, 2800, 3100]


def test_multiplayer_observations_keep_a_grid_that_an_acknowledgement_does_not_move():
    # Two clients publish at the same battle times only if an order's acknowledgement (here
    # at 1300) does not push the regular observation back (mp-next-steps.md, step 2).
    g = battle({"multiplayer": "control", "observe_ms": 1000}, "grant(own)")
    move = {"unit": "f1", "type": "move", "x": 10, "z": 20}
    assert published_times(g, move, TICKS) == [1000, 1300, 2200, 3100]


def test_single_player_observation_timing_is_unchanged():
    # Outside multiplayer the acknowledgement still restarts the 1000 ms wait.
    g = battle({"observe_ms": 1000}, """
        is_multiplayer = false
        grant(allies)
        bm.modify_battle_speed = function() end
    """)
    move = {"unit": "f1", "type": "move", "x": 10, "z": 20}
    assert published_times(g, move, TICKS) == [1000, 1300, 2500]


READY = """
    phase = "Deployment"
    bm.get_current_phase_name = function() return phase end
    clicks, hidden_clicks = 0, 0
    function component(id, shown, children, click)
        return {Id = const(id), Visible = const(shown), ChildCount = const(#children),
                Find = function(_, i) return children[i + 1] end, SimulateLClick = click}
    end
    function UIComponent(uic) return uic end
    -- A hidden panel holds a button of the same id before the shown one (2026-11-03).
    ui_root = component("root", true, {
        component("deployment_sp", false, {component("button_battle_start", true, {},
            function() hidden_clicks = hidden_clicks + 1 end)}),
        component("hud", true, {component("button_battle_start", true, {},
            function() clicks = clicks + 1 end)})})
    core.get_ui_root = function() return ui_root end
    twwarhammer3_ui.dump = function(step, directory) files[directory .. step.dump] = "tree" end
"""


def ready(g, request="q1"):
    loading = observation(g)
    send(g, "orders.json", {"battle": loading["battle"], "request": request, "control": "ready"})
    return observation(g)


def test_control_ready_presses_this_clients_start_battle_in_multiplayer_deployment():
    g = battle({"multiplayer": "control"}, READY)
    seen = ready(g)
    assert g.clicks == 1 and g.hidden_clicks == 0 and list(g.trapped.values()) == []
    assert g.files[BRIDGE + "ready_ui.txt"] == "tree"
    assert seen["seq"] == 1 and seen["phase"] == "Deployment"
    assert seen["orders"]["request"] == "q1"
    assert seen["orders"]["results"] == [{"index": 1, "control": "ready", "ok": True}]
    assert "multiplayer ready: clicked" in logged(g)
    # A second press could un-ready this client, so a repeat is refused.
    seen = ready(g, "q1b")
    assert g.clicks == 1 and seen["orders"]["results"][0]["error"] == "already_ready"
    # Once the battle has started it no longer clicks.
    g.phase = "Deployed"
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    send(g, "orders.json", {"battle": seen["battle"], "request": "q2", "control": "ready"})
    g.callbacks["twwarhammer3_tick"]()
    assert g.clicks == 1
    assert observation(g)["orders"]["results"][0]["error"] == "not_deployment"


@pytest.mark.parametrize("mode,setup,expected", [
    ("control", "is_multiplayer = false", "multiplayer ready: single_player"),
    ("observe", "", "observe: dropped orders.json"),
])
def test_ready_is_refused_in_single_player_and_in_observe(mode, setup, expected):
    g = battle({"multiplayer": mode}, READY + setup)
    ready(g)
    assert g.clicks == 0 and expected in logged(g) and list(g.trapped.values()) == []


LEAVE = READY + """
    context_calls = {}
    common.call_context_command = function(context, id, command)
        context_calls[#context_calls + 1] = context .. "|" .. id .. "|" .. command
    end
"""


def leave(g, request="l1"):
    send(g, "orders.json", {"battle": observation(g)["battle"], "request": request,
                            "control": "leave"})
    return observation(g)


def test_control_leave_calls_quit_once_and_replies_at_once_in_a_running_battle():
    g = battle({"multiplayer": "control"}, LEAVE)
    g.phase = "Deployed"
    g.phases["Deployed"]()
    g.callbacks["twwarhammer3_tick"]()
    seen = leave(g)
    assert list(g.context_calls.values()) == ["CcoBattleRoot||QuitToMainMenu"]
    assert seen["orders"]["request"] == "l1"
    assert seen["orders"]["results"] == [{"index": 1, "control": "leave", "ok": True}]
    assert leave(g, "l2")["orders"]["results"][0]["error"] == "already_leaving"
    assert len(g.context_calls) == 1
    assert list(g.trapped.values()) == []


def test_leave_reports_a_refused_command_and_is_refused_outside_multiplayer_control():
    g = battle({"multiplayer": "control"}, LEAVE + """
        common.call_context_command = function() error("no such context") end""")
    assert "no such context" in leave(g)["orders"]["results"][0]["error"]
    assert "already_leaving" not in str(leave(g, "l2")["orders"]["results"])
    g = battle({"multiplayer": "control"}, LEAVE + "is_multiplayer = false")
    assert leave(g)["orders"]["results"][0]["error"] == "single_player"
    assert len(g.context_calls) == 0
    g = battle({"multiplayer": "observe"}, LEAVE)
    leave(g)
    assert len(g.context_calls) == 0 and "observe: dropped orders.json" in logged(g)
