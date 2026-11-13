"""The B plan's private draw and bounded Lua authority; not engine effect evidence."""

import json
from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace

import pytest
import wh3_lua
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation
from wh3_lua import load_battle, runtime

from twwarhammer3.battle import play, reserve, setup
from twwarhammer3.battle.play import public
from twwarhammer3.battle.scripted import Hold
from twwarhammer3.protocol import ProtocolError


def scenario():
    return setup.scenarios()["emp-envelopment-b-v1"]


def test_reserve_catalogue_is_fresh_private_reproducible_and_leaves_the_opening_fixed(monkeypatch):
    base = scenario()
    original = deepcopy(base)
    seeds = iter((813, 927))
    monkeypatch.setattr(reserve.secrets, "randbits", lambda bits: next(seeds))
    first, second = reserve.materialize(base), reserve.materialize(base)
    assert first["seed"] == "813" and second["seed"] == "927"
    assert first == reserve.materialize(base, seed=813)
    draws = [reserve.materialize(base, seed=i) for i in range(100)]
    assert {(d["region"], d["side"], d["count"]) for d in draws} == set(reserve.CATALOGUE)
    assert base == original
    instances = [reserve.episode_scenario(base, d) for d in draws]
    assert all(s["deployment"] == original["deployment"] for s in instances)
    instances[0]["reserve"]["route"][0]["x"] = 12345
    assert draws[0]["route"][0]["x"] != 12345
    assert base == original


def test_complete_policy_inputs_do_not_depend_on_future_assignment_and_a_nested_plant_is_detected():
    base = scenario()
    inputs = []
    for seed in range(20):
        draw = reserve.materialize(base, seed=seed)
        raw = {"schema": 1, "friendly": [], "enemy": [], "enemy_roster": [],
               "mode": {"type": "land_normal"}, "job": "neutral-job", "time_ms": 10000,
               "evaluation": {"reserve": draw}, "setup": {"reserve": draw},
               "final": {"reserve": draw}}
        inputs.append(public(raw, reserve.episode_scenario(base, draw)))
    assert all(value == inputs[0] for value in inputs)
    # A plausible wrong implementation copying a private field into nested public mode
    # must make this differential audit fail; top-level filtering alone cannot catch it.
    planted = deepcopy(inputs[0])
    planted["mode"]["reserve_seed"] = draw["seed"]
    with pytest.raises(AssertionError):
        assert planted == inputs[0]


def lua_frame(base, draw):
    """The real Lua observation one tick before the trigger under `draw`, through the mod's
    JSON encoder: the raw frame and its play.public view. Only engine reads are stubbed."""
    lua, tick = engine(draw)
    lua.execute("""
        SLOT_LIST, BEHAVIOURS = 'slots', {}
        function context_rows() return {} end
        function get_context() return nil end
        function bm:get_current_phase_name() return 'Deployed' end
        function bm:get_player_army() return {} end
        function bm:get_first_non_player_army() return {} end
        bm.battle.current_battle_speed = function() return 1 end
        bm.battle.remaining_conflict_time = function() return 1200 end
        session.job = 'neutral-job'
        state.battle, state.seq, state.alliance = 'b1', 0, 1
        state.info = {alliances = 2, type = 'land_normal', role = 'defender'}
        state.army_abilities, state.slots, state.objective_totals = {}, {}, {}
        state.setup = {reserve = {ok = true}}
        for _, entry in pairs(state.enemy) do
            local u = entry.unit
            entry.initial = true
            function u:is_in_melee() return false end
            function u:is_moving() return false end
            function u:bearing() return 270 end
            function u:unary_hitpoints() return 1 end
            function u:is_visible_to_alliance() return true end
        end
        state.friendly.f1 = {unit = state.enemy.e1.unit, ui_id = 'f1', setup = {}}
        state.friendly_ids[1] = 'f1'
    """)
    *_, observation = load_battle(lua, "strength", "evaluation", "visible_to_player",
                                  "unit_record", "enemy_observation", "mode_section",
                                  "sample_countdown", "terminal_countdown", "battle_speed",
                                  "player_army", "deployment_reading", "observation")
    codec = lua.execute((wh3_lua.MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())
    now = draw["trigger_ms"] - 1
    tick(now)
    raw = json.loads(codec.encode(observation(now)))
    return raw, public(raw, reserve.episode_scenario(base, draw))


def test_real_lua_observation_before_the_trigger_is_identical_under_every_draw():
    base = setup.scenarios()["emp-envelopment-b-v3"]
    draws = {(d["region"], d["side"], d["count"]): d
             for d in (reserve.materialize(base, seed=seed) for seed in range(100))}
    assert set(draws) == set(reserve.CATALOGUE)
    frames = [lua_frame(base, draw) for draw in draws.values()]
    # The draw is live in this Lua: its private section carries it, its public view must not.
    assert [raw["evaluation"]["reserve"]["config"]["seed"] for raw, _ in frames] == [
        draw["seed"] for draw in draws.values()]
    views = [view for _, view in frames]
    assert {"e3", "e4"} <= {unit["id"] for unit in views[0]["enemy"]}
    assert "error" not in views[0]["mode"] and "error" not in views[0]["friendly"][0]
    assert all(view == views[0] for view in views)


def test_job_activates_and_saves_each_fresh_draw_before_launch_or_rematch(tmp_path, monkeypatch):
    events = []

    class Mailbox(FakeMailbox):
        def __init__(self, directory, *, job):
            super().__init__([], job=job)

        def write_session(self, value):
            super().write_session(value)
            events.append(("session", value["reserve"]["seed"]))

        def write_control(self, battle, control):
            events.append((control, battle))

    box = Mailbox(None, job="neutral-job")
    seeds = iter((2, 7))
    monkeypatch.setattr(reserve.secrets, "randbits", lambda bits: next(seeds))
    monkeypatch.setattr(play, "Mailbox", lambda *a, **k: box)
    monkeypatch.setattr(play, "RuntimeLock", nullcontext)
    monkeypatch.setattr(play, "OwnedGame", lambda *a, **k: nullcontext(SimpleNamespace(info={})))
    monkeypatch.setattr(play, "PassiveCapture", lambda *a, **k: nullcontext())
    monkeypatch.setattr(play, "prepare_runtime", lambda: {})
    monkeypatch.setattr(play, "collect_diagnostics", lambda: {})
    monkeypatch.setattr(play, "committed_revision", lambda *a: "frozen-revision")
    monkeypatch.setattr(play, "source_fingerprints", lambda *a: {})
    monkeypatch.setattr(play, "start_frontend", lambda *a: events.append(("launch", "2")))
    monkeypatch.setattr(play, "check_menu", lambda *a: {})
    monkeypatch.setattr(play, "record", lambda *a: None)

    def episode(directory, config, maker, mailbox, **kwargs):
        draw = kwargs["scenario"]["reserve"]
        assert mailbox.session["reserve"] == draw
        events.append(("episode", draw["seed"]))
        directory.mkdir()
        result = {"status": "won", "battle": f"b{config['slot']}"}
        (directory / "result.json").write_text(json.dumps(result))
        return result

    monkeypatch.setattr(play, "play_episode", episode)
    config = {**CONFIG, "scenario": "emp-envelopment-b-v1", "episodes": 2,
              "episode_timeout": 1320, "run_timeout": 3000,
              "results": str(tmp_path / "results.csv"), "seed": 999, "rotation_seed": 123}
    manifest = play.play(tmp_path / "job", config, makers={"attack_nearest": lambda: None})
    assert events == [("session", "2"), ("launch", "2"), ("session", "2"),
                      ("episode", "2"), ("session", "7"), ("restart", "b0"), ("episode", "7")]
    saved = json.loads((tmp_path / "job/manifest.json").read_text())
    assert saved["source_revision"] == "frozen-revision" and saved["status"] == "completed"
    assert [d["seed"] for d in saved["reserve_draws"]] == ["2", "7"]
    assert manifest["reserve_draws"] == saved["reserve_draws"]


def engine(draw):
    lua = runtime()
    lua.globals().config = lua.table_from(draw, recursive=True)
    lua.execute("""
        commands, callbacks, controllers = {}, {}, {}
        function log() end
        function clean_error(e) return tostring(e) end
        function get(obj, method, default, ...)
            if not obj[method] then return default end
            local ok, value = pcall(obj[method], obj, ...)
            if ok and value ~= nil then return value end
            return default
        end
        function round(n) return n end
        function vector(x,y,z) return {x=x,y=y,z=z} end
        bm = {battle={get_terrain_height=function() return 0 end},
            callback=function(_, fn) callbacks[#callbacks+1] = fn end}
        local army = {}
        function army:create_unit_controller()
            local c = {released=0}
            function c:add_units(u) self.unit=u end
            function c:take_control() self.taken=true end
            function c:halt() self.held=true end
            function c:teleport_to_location() end
            function c:release_control() self.released=self.released+1 end
            function c:goto_location(p, run)
                commands[#commands+1]={unit=self.unit.key,x=p.x,z=p.z,queue=false,run=run}
            end
            function c:goto_location_q(p, run)
                commands[#commands+1]={unit=self.unit.key,x=p.x,z=p.z,queue=true,run=run}
            end
            controllers[#controllers+1]=c
            return c
        end
        state = {enemy={}, enemy_ids={}, friendly={}, friendly_ids={}}
        session = {reserve=config, deployment={enemy={}}}
        for i=1,10 do
            local id = 'e'..(11-i)
            local kind = i<=8 and 'wh_main_emp_inf_swordsmen' or 'knight'
            local u = {key=id}
            function u:type() return kind end
            function u:number_of_men_alive() return 90 end
            function u:is_routing() return false end
            function u:is_shattered() return false end
            function u:position()
                return {get_x=function() return i*10 end, get_z=function() return 0 end}
            end
            state.enemy[id]={unit=u,army=army}
            state.enemy_ids[i]=id
            session.deployment.enemy[i]={type=kind,x=i*10,z=0,bearing=270,width=40}
        end
    """)
    setup_reserve, teleport, _, tick = load_battle(lua, "authored_entry", "setup_reserve",
                                                "teleport_units", "reserve_disposition",
                                                "tick_reserve")[1:]
    setup_reserve()
    teleport(lua.globals().session["deployment"])
    lua.execute("for _, fn in ipairs(callbacks) do fn() end")
    return lua, tick


@pytest.mark.parametrize("region", ("centre", "outside"))
@pytest.mark.parametrize("count", (1, 2))
def test_lua_holds_exact_enemy_slots_then_routes_once_on_engine_time_and_releases(region, count):
    draw = next(d for seed in range(100) if (d := reserve.materialize(scenario(), seed=seed))
                and (d["region"], d["count"]) == (region, count))
    lua, tick = engine(draw)
    private = lua.globals().state["reserve"]["evidence"]
    assert [(u["slot"], u["id"]) for u in private["units"].values()] == [(7, "e4"), (8, "e3")]
    controlled = list(lua.globals().controllers.values())
    assert [c["released"] for c in controlled[:2]] == [0, 0]
    assert all(c["released"] == 1 for c in controlled[2:])
    tick(draw["trigger_ms"] - 1)
    assert len(lua.globals().commands) == 0
    tick(draw["trigger_ms"])
    tick(draw["trigger_ms"] + 250)
    commands = list(lua.globals().commands.values())
    assert len(commands) == count * len(draw["route"])
    expected_ids = {"e4", "e3"} if count == 2 else {"e4"}
    assert {c["unit"] for c in commands} == expected_ids
    assert all(c["run"] is True for c in commands)
    assert len(private["orders"]) == count
    assert private["triggered_ms"] == draw["trigger_ms"]
    # Fake engine accepts orders without moving: keep separate actual position evidence.
    assert private["initial"]["units"][1]["x"] == private["latest"]["units"][1]["x"]
    tick(draw["release_ms"])
    tick(draw["release_ms"] + 250)
    assert all(c["released"] == 1 for c in controlled)


def test_terminal_lua_never_triggers_an_event():
    draw = reserve.materialize(scenario(), seed=1)
    lua, tick = engine(draw)
    lua.globals().state["finished"] = True
    tick(draw["trigger_ms"] + 1000)
    assert len(lua.globals().commands) == 0


def test_lua_trigger_fires_on_engine_time_after_a_policy_order_too():
    draw = reserve.materialize(scenario(), seed=1)
    lua, tick = engine(draw)
    apply_pending = load_battle(lua, "apply_pending")  # the real order path sets each state field
    lua.execute("function apply_order(order) return {unit = order.unit, ok = true} end")
    lua.globals().state["pending"] = lua.table_from(
        {"request": "r1", "based_on": 1, "orders": [{"unit": "f1", "type": "halt"}]},
        recursive=True)
    apply_pending(draw["trigger_ms"] - 500)
    assert lua.globals().state["applied"]["results"][1]["ok"] is True
    tick(draw["trigger_ms"])
    assert lua.globals().state["reserve"]["evidence"]["triggered_ms"] == draw["trigger_ms"]


@pytest.mark.parametrize("condition", ("destroyed", "routing", "shattered", "unreadable"))
def test_prevented_reserves_do_not_receive_orders_and_unknown_state_is_an_error(condition):
    draw = reserve.materialize(scenario(), seed=1)
    lua, tick = engine(draw)
    lua.globals().condition = condition
    lua.execute("""
        for _, entry in ipairs(state.reserve.entries) do
            function entry.unit:number_of_men_alive()
                if condition == 'destroyed' then return 0 end
                if condition == 'unreadable' then error('read failed') end
                return 90
            end
            function entry.unit:is_routing() return condition == 'routing' end
            function entry.unit:is_shattered() return condition == 'shattered' end
        end
    """)
    tick(draw["trigger_ms"])
    assert len(lua.globals().commands) == 0
    orders = lua.globals().state["reserve"]["evidence"]["orders"]
    assert len(orders) == draw["count"]
    for order in orders.values():
        assert order["ok"] is (condition != "unreadable")
        assert order["issued_ms"] is None
        assert order["disposition"] == (None if condition == "unreadable" else condition)


def test_private_intermediate_positions_survive_without_entering_policy_inputs(tmp_path):
    draw = reserve.materialize(scenario(), seed=1)
    units = [{"slot": slot, "id": identity, "type": "wh_main_emp_inf_swordsmen"}
             for slot, identity in ((7, "e4"), (8, "e3"))]
    rows = []
    for i, x in enumerate((355, 123.456789, 355)):
        row = bridge_observation(i, i * 1000)
        row["enemy_roster"] = [{"id": u["id"], "type": u["type"]} for u in units]
        row["evaluation"] = {"reserve": {"config": draw, "units": units, "orders": [],
                              "latest": {"time_ms": i * 1000, "units": [{"x": x}]}}}
        rows.append(row)
    rows[-1]["result"] = "won"
    result = play.play_episode(tmp_path / "episode", CONFIG, Hold, FakeMailbox(rows),
                               not_battle=None, scenario={"reserve": draw})
    assert result["status"] == "won"
    path = tmp_path / "episode/trace.jsonl"
    trace = [json.loads(line) for line in path.read_text().splitlines()]
    private = [r["evidence"]["latest"]["units"][0]["x"] for r in trace if r["kind"] == "reserve"]
    initial = trace[0]["observation"]["evaluation"]["reserve"]["latest"]["units"][0]["x"]
    assert [initial, *private] == [355, 123.456789, 355]
    for row in trace:
        if row["kind"] == "observation":
            assert "123.456789" not in json.dumps(row["observation"])


@pytest.mark.parametrize("damage", ("config", "identity", "submission", "setup", "effect"))
def test_bad_private_interventions_are_reported(damage):
    base = scenario()
    draw = reserve.materialize(base, seed=1)
    instance = reserve.episode_scenario(base, draw)
    evidence = {"config": deepcopy(draw), "units": [
        {"slot": 7, "id": "e4", "type": "wh_main_emp_inf_swordsmen"},
        {"slot": 8, "id": "e3", "type": "wh_main_emp_inf_swordsmen"}], "orders": []}
    observation = {"setup": {"reserve": {"ok": True}}, "evaluation": {"reserve": evidence},
                   "enemy_roster": [{"id": "e4", "type": "wh_main_emp_inf_swordsmen"},
                                    {"id": "e3", "type": "wh_main_emp_inf_swordsmen"}]}
    assert reserve.check(instance, observation) == evidence
    if damage == "config":
        evidence["config"]["seed"] = "foreign episode"
    elif damage == "identity":
        evidence["units"][1]["id"] = "e4"
    elif damage == "submission":
        evidence["orders"] = [{"ok": False}]
    elif damage == "setup":
        observation["setup"]["reserve"]["ok"] = False
    else:
        evidence["error"] = "native adapter failed"
    with pytest.raises(ProtocolError, match="reserve"):
        reserve.check(instance, observation)


@pytest.mark.parametrize("profile", [
    {"version": 3, "slots": [7, 8]},  # a version with no catalogue draw
    {"version": 1, "slots": [8, 7]},  # the same slots in another order
    {"version": 1, "slots": [7, 8], "seed": "7"},  # a draw's private key in the declaration
])
def test_a_reserve_declaration_other_than_the_two_supported_profiles_is_refused(profile):
    """materialize accepts exactly the v1 and v2 profiles on slots 7 and 8. Wrong version
    (2026-11-13 refusal sweep): without the refusal an unknown version is drawn with v2's 360 s
    bound but no arrival rule, and the other two are drawn as declared (the seed overwritten)."""
    with pytest.raises(ValueError, match="unsupported reserve profile"):
        reserve.materialize({**deepcopy(scenario()), "reserve": profile}, seed=1)


def test_reserve_slots_that_place_another_unit_type_are_refused():
    """Slots 8 and 9 swap places (Swordsmen and Knights): the roster is unchanged, so only a check
    of the type each held slot places finds it. Wrong version (2026-11-13 refusal sweep): without
    the refusal a draw is made for a hold that would bind a Knights regiment."""
    entry = deepcopy(scenario())
    enemy = entry["deployment"]["enemy"]
    enemy[7], enemy[8] = enemy[8], enemy[7]
    with pytest.raises(ValueError, match="must bind the declared swordsmen"):
        reserve.materialize(entry, seed=1)
