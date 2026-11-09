"""The waves profile (reserve version 3), its Lua hold and release, the two siege declarations
(cth-emp-siege-a-v1 and its all-at-once arm cth-emp-siege-a-all-v1) and what their controllers
may read.

Reference: the 2026-11-08 siege defence design (runs/siege-evals-20261108/final-haengju.md,
untracked: Settings, Rosters, Map and placements, Scripted divisions, Public briefing,
Infrastructure items 1-3 and 10); the Lua hold follows Cannae B's (setup_reserve, after the
SMACv2 wrapper's reset, which reserve.py names). Lua runs under lupa's Lua 5.1 with a fake engine
whose controllers record their calls. Offline only: nothing here shows that the engine holds a
unit, that is_under_missile_attack reads true under fire, that a teleport works in a siege or
that the native AI attacks after a release.
"""

import json
import re
from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace

import pytest
import wh3_lua
from wh3_fixtures import CONFIG, FakeMailbox
from wh3_helmgart import SCENARIO, first_observation
from wh3_lua import load_battle

from twwarhammer3.battle import llm, play, reserve, setup
from twwarhammer3.protocol import ProtocolError

# Marker lines and pointers for values of the three entries in configs/twwarhammer3/scenarios.json,
# which cannot carry a comment (docs/judgement.md). The design they copy from is untracked
# (final-haengju.md).
# cth-emp-siege-a-all-v1's player, enemy, map and expect (very hard, 1.0, 0.75, 1,200 s, 20,000
# funds) rest on JUDGEMENT docs/twwarhammer3/haengju-eval.md Construction profile.
# JUDGEMENT: Cathay lobby faction — Claude, 2026-11-08: wh3_main_cth_cathay_mp, the only faction
# whose custom-battle permissions list these cards. The design's example western_provinces would
# need it as recruitment_faction and may bring faction effects; recruitment rests on it.
# JUDGEMENT: Siege staging — Claude, 2026-11-08 (design's staging points, bearing 0): scenarios.json
# enemy deployment, slots 1-4 D1, 5-8 D2, 9-13 D3, 14-18 D4, 32 m regiments and a 20 m General.
# Other points or widths change arrival times and visibility; the division sequence rests on it.
# cth-emp-siege-a-v1's reserve, released at 150, 300 and 450 s and on damage,
# rests on JUDGEMENT docs/twwarhammer3/haengju-eval.md Division schedule.
# JUDGEMENT: Siege toggles — Claude, 2026-11-08 (design: engine defaults): no behaviour_defaults, so
# the engine's own toggles (defend and fire at will on in the recorded siege) stay. That field would
# turn defend and skirmish off for every garrison unit; decision 1's fire baseline rests on it.
# JUDGEMENT?: All-at-once briefing — Claude, 2026-11-08: cth-emp-siege-a-all-v1 has no reserve, so
# no briefing sentence. Showing it there keeps model inputs equal across the arms; any model
# comparison of the arms rests on it (the witness reads no briefing).
# JUDGEMENT?: Withheld words — Claude, 2026-11-08: scenarios.json cth-emp-siege-a-all-v1 withheld,
# the design's historical names. A longer list refuses more job names; the job-name guard and the
# boundary test below rest on it.
# JUDGEMENT?: Map screen entry — Claude, 2026-11-09: scenarios.json cth-emp-siege-a-all-gates-v1 is
# the all-at-once arm on Eagle Gate with engine starts on both sides. Authored enemy starts there
# would change the opening it reads; stage 1d's map choice rests on it.

WAVES = "cth-emp-siege-a-v1"
ALL = "cth-emp-siege-a-all-v1"
# The Eagle Gate screen; its map rests on JUDGEMENT docs/twwarhammer3/haengju-eval.md Eagle Gate
# screen.
SCREEN = "cth-emp-siege-a-all-gates-v1"
GUN, SWORD = "wh_main_emp_inf_handgunners", "wh_main_emp_inf_swordsmen"
HALB, GREAT = "wh_main_emp_inf_halberdiers", "wh_main_emp_inf_greatswords"
GENERAL, XBOW = "wh_main_emp_cha_general_0", "wh_main_emp_inf_crossbowmen"
SPEAR = "wh_main_emp_inf_spearmen_0"
# The design's division table (Rosters), by hand.
DIVISIONS = {1: [SPEAR, SPEAR, SPEAR, SWORD], 2: [GUN, GUN, SWORD, SWORD],
             3: [HALB, HALB, GREAT, GREAT, GENERAL], 4: [GREAT, GREAT, SWORD, SWORD, XBOW]}
# The engine numbers enemy units e1..e18 in roster order here (General first), so slot k and
# roster index k disagree: binding slot 5 (Handgunners) by index would take e5, a Swordsmen unit.
# Binding by slot and type in deployment order gives these, worked out by hand.
BOUND = {1: ["e10", "e11", "e6", "e7"], 2: ["e12", "e13", "e14", "e15", "e1"],
         3: ["e16", "e17", "e8", "e9", "e18"]}
TICK = 250


def scenario():
    return deepcopy(setup.scenarios()[WAVES])


def test_the_declarations_differ_only_in_the_hold_and_place_the_whole_enemy_roster():
    waves, every = setup.scenarios()[WAVES], setup.scenarios()[ALL]
    assert {key for key in waves.keys() | every.keys()
            if waves.get(key) != every.get(key)} == {"name", "brief", "reserve"}
    assert "reserve" not in every and "behaviour_defaults" not in waves
    config = {"episode_timeout": 1320, "run_timeout": 30000, "start_timeout": 900, "episodes": 1}
    for entry in (waves, every):
        setup.validate_declaration(entry, config)
    placed = [p["type"] for p in waves["deployment"]["enemy"]]
    assert placed == [kind for division in DIVISIONS.values() for kind in division]
    assert "friendly" not in waves["deployment"]  # the engine places the garrison
    assert [group["types"] for group in waves["reserve"]["groups"]] == [
        DIVISIONS[2], DIVISIONS[3], DIVISIONS[4]]
    assert [group["release_ms"] for group in waves["reserve"]["groups"]] == [
        150000, 300000, 450000]
    assert waves["siege_equipment"] == {} and waves["private_record"] is True
    # One enemy unit left out of the deployment is an incomplete roster.
    short = deepcopy(waves)
    short["deployment"]["enemy"].pop(2)
    with pytest.raises(ValueError, match="whole roster"):
        setup.validate_declaration(short, config)


def test_the_map_screen_is_the_all_at_once_arm_on_another_siege_map_with_engine_starts():
    """Stage 1d's one hold launch. Wrong versions: Helmgart's enemy points kept on another map
    (the mod would teleport units onto them) or the waves hold, which binds them; a map key not in
    the lobby's siege list; a roster or setting changed with the map; a withheld word in the new
    text."""
    every, screen = setup.scenarios()[ALL], setup.scenarios()[SCREEN]
    assert {key for key in every.keys() | screen.keys() if every.get(key) != screen.get(key)} == {
        "name", "brief", "calibration_change", "map", "deployment"}
    siege = json.loads(setup.CATALOGUE_PATH.read_text())["battle_type_maps"]["siege"]
    assert screen["map"] in siege and screen["map"] != every["map"]
    config = {"episode_timeout": 1320, "run_timeout": 30000, "start_timeout": 900, "episodes": 1}
    setup.validate_declaration(screen, config)
    assert play.battle_session(screen) == {"private_record": True}
    text = json.dumps({key: value for key, value in screen.items() if key != "withheld"})
    assert [word for word in screen["withheld"] if word in text.lower()] == []


def test_the_profile_is_returned_unchanged_takes_no_seed_and_is_saved_in_manifest_and_register(
        tmp_path, monkeypatch):
    base = scenario()
    assert reserve.materialize(base) == base["reserve"] == reserve.sequence(base, 3)[2]
    assert reserve.sequence(base, 3) == [base["reserve"]] * 3
    with pytest.raises(ValueError, match="no random draw"):
        reserve.sequence(base, 1, seed=7)
    sessions = []

    class Mailbox(FakeMailbox):
        def __init__(self, directory, *, job):
            super().__init__([], job=job)

        def write_session(self, value):
            super().write_session(value)
            sessions.append(deepcopy(value["reserve"]))

        def write_control(self, battle, control):
            pass

    for name, value in (("Mailbox", Mailbox), ("RuntimeLock", nullcontext),
                        ("OwnedGame", lambda *a, **k: nullcontext(SimpleNamespace(info={}))),
                        ("PassiveCapture", lambda *a, **k: nullcontext()),
                        ("prepare_runtime", dict), ("collect_diagnostics", dict),
                        ("committed_revision", lambda *a: "r1"),
                        ("source_fingerprints", lambda *a: {}), ("start_frontend", lambda *a: None),
                        ("check_menu", lambda *a: {})):
        monkeypatch.setattr(play, name, value)

    def episode(directory, config, maker, mailbox, **kwargs):
        assert kwargs["scenario"]["reserve"] == base["reserve"]
        directory.mkdir()
        result = {"status": "won", "battle": f"b{config['slot']}"}
        (directory / "result.json").write_text(json.dumps(result))
        return result

    monkeypatch.setattr(play, "play_episode", episode)
    config = {**CONFIG, "scenario": WAVES, "policy": "hold", "episodes": 2,
              "episode_timeout": 1320, "run_timeout": 30000,
              "results": str(tmp_path / "results.csv"), "seed": 1, "rotation_seed": 1}
    play.play(tmp_path / "bench-cths-a-hold-20261108", config, makers={"hold": lambda: None})
    saved = json.loads((tmp_path / "bench-cths-a-hold-20261108/manifest.json").read_text())
    assert saved["reserve_draws"] == [base["reserve"]] * 2
    assert saved["scenario"]["reserve"] == base["reserve"]
    assert sessions and all(value == base["reserve"] for value in sessions)
    # The real register writer: a Cannae B case of region/side/count raised KeyError 'region' on
    # the first episode here, so play stopped with one episode and no row.
    register = (tmp_path / "results.csv").read_text().splitlines()
    assert [line.rsplit(",", 1)[-1] for line in register] == ["case", "waves", "waves"]


def broken(change):
    entry = scenario()
    change(entry, entry["reserve"]["groups"])
    return entry


@pytest.mark.parametrize("entry,message", [
    (broken(lambda s, g: g[1]["slots"].__setitem__(0, 5)), "in two groups"),
    (broken(lambda s, g: (g[2]["slots"].append(19), g[2]["types"].append(XBOW))),
     "not an enemy deployment slot"),
    (broken(lambda s, g: (g[0].update(release_ms=300000), g[1].update(release_ms=150000))),
     "in group order"),
    (broken(lambda s, g: g[0].update(release_ms=-1)), "0 or more"),
    (broken(lambda s, g: g[0].update(release_ms=150000.5)), "whole milliseconds"),
    (broken(lambda s, g: g[0]["types"].reverse()), "slot 5 places"),
    # Slots 5 (Handgunners) and 7 (Swordsmen) swap places: the roster is unchanged, so only a
    # check of the placement each slot names finds it.
    (broken(lambda s, g: s["deployment"]["enemy"].insert(4, s["deployment"]["enemy"].pop(6))),
     "slot 5 places wh_main_emp_inf_swordsmen"),
    (broken(lambda s, g: g.append({"slots": [], "types": [], "release_ms": 500000})),
     "one declared type per slot"),
    (broken(lambda s, g: s["reserve"].update(version=2)), "unsupported waves profile"),
    (broken(lambda s, g: s["reserve"].update(seed="7")), "unsupported waves profile"),
    (broken(lambda s, g: s.update(custom={"kind": "battery_evacuation", "version": 1})),
     "unsupported waves profile"),
])
def test_a_profile_that_would_hold_the_wrong_units_or_times_is_refused(entry, message):
    with pytest.raises(ValueError, match=message):
        reserve.materialize(entry)


def codec(lua):
    return lua.execute((wh3_lua.MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())


def engine(profile, *, mode=None, native_mp=False):
    """The battle Lua's own waves functions on a fake engine. Enemy ids follow the roster
    (BOUND's note); each controller records its calls. Two friendly units exist, and reading
    any field of either raises: Lua 5.1's ipairs reads raw, so an empty table that raises on
    reads would let a loop over the friendly ids pass unseen."""
    lua = wh3_lua.runtime()
    globals_ = lua.globals()
    globals_.config = lua.table_from(profile, recursive=True)
    globals_.placements = lua.table_from(SCENARIO["deployment"]["enemy"], recursive=True)
    globals_.roster = lua.table_from(SCENARIO["enemy"]["units"])
    globals_.mode, globals_.native_mp = mode, native_mp
    lua.execute("""
        callbacks, controllers, units = {}, {}, {}
        function log() end
        function v(x, y, z) return {x = x, y = y, z = z} end
        bm = {battle = {is_multiplayer = function() return native_mp end,
                        get_terrain_height = function() return 0 end},
              callback = function(_, fn) callbacks[#callbacks + 1] = fn end}
        local army = {}
        function army:create_unit_controller()
            local c = {calls = {}}
            local function note(name) c.calls[#c.calls + 1] = name end
            function c:add_units(u) self.unit = u; note('add_units') end
            function c:take_control() note('take_control') end
            function c:halt() note('halt') end
            function c:release_control() note('release_control') end
            function c:teleport_to_location() note('teleport') end
            controllers[#controllers + 1] = c
            return c
        end
        local forbidden = {__index = function(_, key) error('read friendly ' .. tostring(key)) end}
        state = {enemy = {}, enemy_ids = {}, multiplayer = mode, friendly_ids = {'f1', 'f2'},
                 friendly = {f1 = setmetatable({}, forbidden), f2 = setmetatable({}, forbidden)}}
        session = {reserve = config, deployment = {enemy = placements}, tick_ms = 250}
        for i, kind in ipairs(roster) do
            local u = {key = 'e' .. i, kind = kind, men = 90, fire = false, x = i * 10, z = -500}
            function u:type() return self.kind end
            function u:number_of_men_alive()
                if self.men == 'error' then error('read failed') end
                return self.men
            end
            function u:is_under_missile_attack()
                if self.fire == 'error' then error('read failed') end
                return self.fire
            end
            function u:position()
                local s = self
                return {get_x = function() return s.x end, get_z = function() return s.z end}
            end
            units[u.key] = u
            state.enemy[u.key] = {unit = u, army = army}
            state.enemy_ids[i] = u.key
        end
    """)
    loaded = load_battle(lua, "clean_error", "get", "round", "vector", "authored_entry",
                         "setup_waves", "tick_waves", "setup_reserve", "reserve_disposition",
                         "tick_reserve", "teleport_units")
    return lua, loaded[7], loaded[9], loaded[10]


def start(profile=None, **options):
    """setup_reserve, then the authored teleport and its release callbacks, as start() runs."""
    lua, setup_reserve, tick_reserve, teleport = engine(profile or SCENARIO["reserve"], **options)
    setup_reserve()
    teleport(lua.globals().session["deployment"])
    lua.execute("for _, fn in ipairs(callbacks) do fn() end")
    return lua, tick_reserve


def calls(lua):
    """Enemy id -> the calls on its controllers, in order."""
    result = {}
    for controller in lua.globals().controllers.values():
        result.setdefault(controller["unit"]["key"], []).extend(controller["calls"].values())
    return result


def released(lua):
    return {identity for identity, made in calls(lua).items()
            if made[-1] == "release_control" and "halt" in made}


def evidence(lua):
    return json.loads(codec(lua).encode(lua.globals().state["reserve"]["evidence"]))


def observation(lua, ms=None):
    """What reserve.check reads of an observation carrying this Lua's evidence, with time_ms ms
    when given."""
    result = {"setup": {"reserve": {"ok": True}}, "evaluation": {"reserve": evidence(lua)},
              "enemy_roster": [{"id": f"e{index}", "type": kind}
                               for index, kind in enumerate(SCENARIO["enemy"]["units"], 1)]}
    if ms is not None:
        result["time_ms"] = ms
    return result


def ticks(tick, start_ms, stop_ms):
    for now in range(start_ms, stop_ms + 1, TICK):
        tick(now)


def test_setup_takes_and_halts_exactly_the_held_groups_by_slot_and_type():
    lua, _ = start()
    made = calls(lua)
    held = {identity for group in BOUND.values() for identity in group}
    for identity in held:
        assert made[identity][:3] == ["add_units", "take_control", "halt"], identity
        assert "release_control" not in made[identity]
    # D1 (slots 1-4) is borrowed only to teleport it, then handed back.
    for identity in ("e2", "e3", "e4", "e5"):
        assert made[identity] == ["add_units", "take_control", "teleport", "release_control"]
    units = evidence(lua)["units"]
    assert [(u["group"], u["slot"], u["type"]) for u in units] == [
        (group, slot, kind) for group, slots in ((1, range(5, 9)), (2, range(9, 14)),
                                                 (3, range(14, 19)))
        for slot, kind in zip(slots, DIVISIONS[group + 1], strict=True)]
    assert [u["id"] for u in units] == [identity for group in BOUND.values()
                                        for identity in group]
    assert reserve.check(scenario(), observation(lua, 1000))["units"] == units


def test_each_group_is_released_at_its_time_and_not_a_tick_earlier():
    lua, tick = start()
    ticks(tick, 1000, 150000 - TICK)
    tick(149999)
    assert released(lua) == set()
    tick(150000)
    assert released(lua) == set(BOUND[1])
    ticks(tick, 150250, 299750)
    assert released(lua) == set(BOUND[1])
    tick(300000)
    tick(450000)
    assert released(lua) == set(BOUND[1]) | set(BOUND[2]) | set(BOUND[3])
    records = evidence(lua)["releases"]
    assert [(r["group"], r["reason"], r["released_ms"]) for r in records] == [
        (1, "time", 150000), (2, "time", 300000), (3, "time", 450000)]
    # Positions as the engine gives them (the fake puts unit e<i> at x = 10 i, z = -500).
    assert records[0]["units"][0] == {"id": "e10", "x": 100, "z": -500, "men": 90}
    reserve.check(scenario(), observation(lua, 450000))


@pytest.mark.parametrize("hit", ["men", "fire"])
def test_damage_to_one_held_group_releases_only_that_group(hit):
    lua, tick = start()
    ticks(tick, 1000, 40000)
    target = lua.globals().units[BOUND[2][3]]  # a Greatswords unit of the second group
    if hit == "men":
        target["men"] = 89
    else:
        target["fire"] = True
    tick(40250)
    assert released(lua) == set(BOUND[2])
    record = evidence(lua)["releases"][0]
    assert (record["group"], record["reason"], record["released_ms"]) == (2, "damage", 40250)
    assert record["damaged"] == [{"id": BOUND[2][3], "men": 89 if hit == "men" else 90,
                                  "men0": 90, "under_fire": hit == "fire"}]
    ticks(tick, 40500, 149750)
    assert released(lua) == set(BOUND[2])
    tick(150000)
    assert released(lua) == set(BOUND[1]) | set(BOUND[2])
    reserve.check(scenario(), observation(lua, 150000))
    # Past group 2's own 300 s, its damage release still counts as its release.
    tick(300000)
    reserve.check(scenario(), observation(lua, 300000))


def test_a_destroyed_held_unit_is_not_released_and_its_group_is():
    lua, tick = start()
    lua.globals().units[BOUND[3][4]]["men"] = 0
    tick(1000)
    assert released(lua) == set(BOUND[3][:4])
    assert "release_control" not in calls(lua)[BOUND[3][4]]
    unit = evidence(lua)["releases"][0]["units"][4]
    assert unit["destroyed"] is True and unit["men"] == 0


def test_without_release_on_damage_a_shot_group_waits_for_its_time():
    profile = {**deepcopy(SCENARIO["reserve"]), "release_on_damage": False}
    lua, tick = start(profile)
    lua.globals().units[BOUND[1][0]]["fire"] = True
    ticks(tick, 1000, 149750)
    assert released(lua) == set()
    tick(150000)
    assert released(lua) == set(BOUND[1])


@pytest.mark.parametrize("reading", [("men", "error"), ("men", None), ("fire", "error"),
                                     ("fire", None), ("fire", "yes")])
def test_an_unreadable_damage_getter_is_an_error_never_no_damage(reading):
    lua, tick = start()
    field, value = reading
    unit = lua.globals().units[BOUND[2][0]]
    unit[field] = value
    tick(1000)
    record = evidence(lua)["releases"][0]
    assert record["group"] == 2 and record["ok"] is False and "reason" not in record
    assert "unreadable waves" in record["error"]
    with pytest.raises(ProtocolError, match="reserve release failed"):
        reserve.check(scenario(), observation(lua, 1000))


@pytest.mark.parametrize("mode,native_mp,version,error", [
    ("observe", False, 3, None), (None, False, 3, None),
    ("control", False, 3, "observer session"), ("observe", True, 3, "single-player battle"),
    ("observe", None, 3, "single-player battle"),  # is_multiplayer unreadable
    ("observe", False, 2, "plain single-player")])
def test_waves_also_run_under_the_owners_observer_session_and_versions_1_2_do_not(
        mode, native_mp, version, error):
    profile = SCENARIO["reserve"]
    if version == 2:
        profile = {"version": 2, "slots": [7, 8]}
    lua, setup_reserve, _, _ = engine(profile, mode=mode, native_mp=native_mp)
    if error:
        with pytest.raises(Exception, match=error):
            setup_reserve()
        return
    setup_reserve()
    made = calls(lua)
    assert all(made[identity] == ["add_units", "take_control", "halt"]
               for group in BOUND.values() for identity in group)


def test_a_slot_the_mod_cannot_bind_leaves_no_unit_held():
    # Python refuses such a profile first; the mod still refuses it whole, never half held.
    profile = deepcopy(SCENARIO["reserve"])
    profile["groups"][2]["types"][4] = SWORD  # slot 18 places the Crossbowmen
    lua, setup_reserve, _, _ = engine(profile)
    with pytest.raises(Exception, match="waves slot 18 binds wh_main_emp_inf_crossbowmen"):
        setup_reserve()
    assert len(lua.globals().controllers) == 0 and lua.globals().state["reserve"] is None


def test_the_mod_refuses_waves_beside_a_custom_objective():
    # Python refuses such a scenario first ("unsupported waves profile" above).
    lua, setup_reserve, _, _ = engine(SCENARIO["reserve"])
    lua.globals().session["custom"] = lua.table_from({"kind": "battery_evacuation"})
    with pytest.raises(Exception, match="without a custom objective"):
        setup_reserve()
    assert len(lua.globals().controllers) == 0


def test_the_evidence_check_refuses_a_hold_bound_or_released_wrongly():
    """Wrong versions of the overdue rule: `>` for `>=` (the 450 s case) and the rule applied to
    the result observation, which finish() writes after tick_reserve has stopped."""
    lua, tick = start()
    tick(150000)
    good = observation(lua, 150000)
    assert reserve.check(scenario(), good)

    def damaged(change):
        copy = deepcopy(good)
        change(copy, copy["evaluation"]["reserve"])
        return copy

    for change in (
            lambda o, e: o["setup"]["reserve"].update(ok=False),
            lambda o, e: o["evaluation"].pop("reserve"),  # the mod skipped the hold
            lambda o, e: e["config"]["groups"][0].update(release_ms=1),
            lambda o, e: e.update(error="tick failed"),
            lambda o, e: e["units"][0].update(id="e5"),  # a Swordsmen unit in a Handgunner slot
            lambda o, e: e["units"][1].update(id="e10"),  # one unit held twice
            lambda o, e: e["units"].reverse(),
            lambda o, e: e["releases"].append(deepcopy(e["releases"][0])),
            lambda o, e: e["releases"][0].update(released_ms=149750),
            lambda o, e: e["releases"][0].update(reason="arrived"),
            # A mod that would release group 1 for time only at 400 s: the first observation
            # after 150 s lacks the release.
            lambda o, e: (o.update(time_ms=150300), e["releases"].clear()),
            lambda o, e: e["releases"][0].update(reason="damage"),  # no damaged unit named
            lambda o, e: e["releases"][0].update(reason="damage", damaged=[])):
        with pytest.raises(ProtocolError, match="reserve"):
            reserve.check(scenario(), damaged(change))
    no_damage = scenario()
    no_damage["reserve"]["release_on_damage"] = False
    shot = deepcopy(good)
    shot["evaluation"]["reserve"]["config"]["release_on_damage"] = False
    shot["evaluation"]["reserve"]["releases"][0]["reason"] = "damage"
    with pytest.raises(ProtocolError, match="released as 'damage'"):
        reserve.check(no_damage, shot)
    # Groups 1 and 2 released, group 3 due at 450 s and still held.
    tick(300000)
    for ms in (450000, 460000):
        with pytest.raises(ProtocolError, match="group 3 still held"):
            reserve.check(scenario(), observation(lua, ms))
    assert reserve.check(scenario(), {**observation(lua, 460000), "result": "won"})


# What no controller input may hold: the scenario's withheld names, the profile's keys and
# numbers, release times in seconds, group and staging labels.
PROFILE_TERMS = [r"release_ms", r"release_on_damage", r"\bgroups\b",
                 r"150000|300000|450000", r"\b(150|300|450) ?s\b", r"staging", r"pocket",
                 r"\bD[1-4]\b", r"\bwaves?\b"]


def withheld(text):
    words = [re.escape(word) for word in SCENARIO["withheld"]]
    return [term for term in [*words, *PROFILE_TERMS] if re.search(term, text, re.IGNORECASE)]


def inputs(observation, entry):
    """A script's input (play.public) and the model's rendered prompt for it."""
    view = play.public(deepcopy(observation), entry)
    return view, llm.render_prompt(view, "", [], {}, None, None)


def test_controllers_read_only_the_agreed_sentence_and_nothing_hidden():
    view, prompt = inputs(first_observation(), scenario())
    assert view["reserve_briefing"] == reserve.WAVES_BRIEFING == (
        "The attacking army is drawn up in several divisions, which may attack at different"
        " times.")
    assert "benchmark" not in view["mode"] and "scoring" not in view["mode"]
    assert withheld(prompt) == [] and withheld(json.dumps(view)) == []
    assert reserve.WAVES_BRIEFING in prompt
    # The all-at-once arm shows no sentence at all.
    every, _ = inputs(first_observation(), setup.scenarios()[ALL])
    assert "reserve_briefing" not in every
    # The check finds what it looks for: the profile itself, and a historical job name.
    assert withheld(json.dumps(scenario()["reserve"]))
    assert withheld(json.dumps(inputs(first_observation("haengju-hold"), scenario())[0]))


def test_controller_inputs_do_not_change_when_only_hidden_sections_do():
    view, prompt = inputs(first_observation(), scenario())
    lua, tick = start()
    tick(150000)
    changed = first_observation()
    changed["evaluation"] = observation(lua)["evaluation"]
    changed["setup"] = {"reserve": {"ok": True}, "deployment_reading": {"enemy": [
        {"id": "e10", "type": GUN, "x": -120, "z": -530}]}}
    changed["native"] = {"units": [{"id": "e10", "x": -120, "z": -530}]}
    changed["final"] = {"reserve": "released at 150 s"}
    assert inputs(changed, scenario()) == (view, prompt)


def test_a_job_named_after_the_history_is_refused_before_launch(tmp_path):
    config = {**CONFIG, "scenario": WAVES, "policy": "hold", "episode_timeout": 1320,
              "run_timeout": 30000, "seed": 1, "rotation_seed": 1}
    for job in ("haengju-hold-20261108", "bench-Konishi-a", "w-gwon-yul"):
        with pytest.raises(ValueError, match="withheld word"):
            play.play(tmp_path / job, deepcopy(config), makers={"hold": lambda: None})
        assert not (tmp_path / job).exists()
    for job in ("bench-cths-a-hold-20261108", "bench-cths-a-wfire-20261108"):
        setup.check_job(scenario(), job)


def test_an_attached_job_is_refused_when_the_running_games_job_names_the_history(
        tmp_path, monkeypatch):
    # play --attach observes under the job `launch` started, whatever its own folder is called.
    # Both siege declarations pin a lobby (expect), which attach never runs; a declaration with
    # withheld words and no expect is refused on the running game's job.
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "session.json").write_text(json.dumps({"job": "haengju-a", "speed": 1,
                                                     "pause": False}))
    for name, value in (("BRIDGE_DIR", bridge), ("collect_diagnostics", dict),
                        ("committed_revision", lambda *a: "r1"),
                        ("source_fingerprints", lambda *a: {}),
                        ("Mailbox", lambda *a, **k: pytest.fail("a refused job reads nothing"))):
        monkeypatch.setattr(play, name, value)
    config = {**CONFIG, "scenario": ALL, "policy": "hold", "attach": True,
              "episode_timeout": 1320, "run_timeout": 30000, "seed": 1, "rotation_seed": 1,
              "results": str(tmp_path / "results.csv")}
    with pytest.raises(ValueError, match="its own launch and menu checks"):
        play.play(tmp_path / "bench-cths-a-hold-20261108", deepcopy(config),
                  makers={"hold": lambda: None})
    unpinned = {key: value for key, value in setup.scenarios()[ALL].items() if key != "expect"}
    monkeypatch.setattr(play, "load_scenario", lambda config: deepcopy(unpinned))
    output = tmp_path / "bench-cths-a-hold-20261109"
    with pytest.raises(ValueError, match="withheld word"):
        play.play(output, config, makers={"hold": lambda: None})
    assert json.loads((output / "manifest.json").read_text())["status"] == (
        "infrastructure_failure")
