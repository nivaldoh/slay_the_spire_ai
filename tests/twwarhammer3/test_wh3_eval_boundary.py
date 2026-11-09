"""What the six 2026-11-08 evaluation battles hand their controllers, for the parts the other
boundary tests leave out.

Reference: portfolio S2 in runs/siege-evals-20261108/portfolio.md (untracked) and
evaluation-guidelines.md 4.5: build controller inputs from public fields only, and test that by
changing only hidden data and checking that every controller input stays the same.

These checks are not repeated here because other files already make them. The land
declarations' own text and play.public adding nothing for them are in
test_wh3_land_eval_declarations.py. The cth-emp-siege-a-v1 view and prompt (scanned for its
withheld words), its one briefing sentence, its prompt under changed evaluation, setup, native
and final, and the absent sentence for cth-emp-siege-a-all-v1 are in test_wh3_waves.py, which
also refuses historical job names for both siege-defence declarations, as
test_wh3_siege_assault.py does for ksl-emp-siege-a-v1. The camp, lines and wall-defence scripts'
orders with hidden sections present and changed are in test_wh3_camp.py, test_wh3_lines.py and
test_wh3_wall_defence.py, and test_wh3_evade.py and test_wh3_replay_schedule.py check that Evade
and ReplaySchedule read no hidden key. test_wh3_private_record.py checks that a generic episode's
controller input carries no hidden enemy from the private record, and that the mod's observation
lists only the visible enemy.

setup.check_job refuses a job name that holds one of a declaration's withheld words; every new
declaration, the three land ones included, now has that list (test_wh3_land_eval_declarations.py
checks the land refusals). The checks here read only the fixtures' jobs, and show only that the
scan finds a withheld word put into a job.

Offline only. The first observations are fixtures, and each one's source is named where it is
built, so nothing here shows what a live battle's observation holds or that the Lua hides what
the game hides. The real mailbox is not used: a change there is not covered.
"""

import json
import re
import unicodedata
from copy import deepcopy
from functools import cache

import pytest
import test_wh3_camp
import test_wh3_escalade
import test_wh3_lines
import test_wh3_wall_defence
import wh3_helmgart
import wh3_siege_attack
from test_wh3_land_eval_declarations import WITHHELD as LAND_WITHHELD
from test_wh3_private_record import battle as private_battle
from wh3_ablation import run
from wh3_fixtures import CONFIG, FakeMailbox

from twwarhammer3.battle import escalade, llm, play, reference, reserve, wall_defence
from twwarhammer3.battle.replay_schedule import PLACE, VERSION, digest
from twwarhammer3.battle.scripted import AttackNearest, RushNearest
from twwarhammer3.battle.setup import scenarios
from twwarhammer3.battle.skills import Skills
from twwarhammer3.protocol import HIDDEN_KEYS

CAMP, LINES_A, LINES_B = "emp-chd-camp-v1", "ksl-nor-lines-a-v1", "ksl-nor-lines-b-v1"
WAVES, ALL, ATTACK = "cth-emp-siege-a-v1", "cth-emp-siege-a-all-v1", "ksl-emp-siege-a-v1"
SCENARIOS = scenarios()
# The words no controller input may hold. The land declarations' withheld field (the same list
# as test_wh3_land_eval_declarations.py WITHHELD)
# rests on JUDGEMENT? docs/twwarhammer3/lines-eval.md Withheld names.
# cth-emp-siege-a-all-v1's field rests on JUDGEMENT? tests/twwarhammer3/test_wh3_waves.py
# Withheld words, and ksl-emp-siege-a-v1's field
# rests on JUDGEMENT? tests/twwarhammer3/test_wh3_siege_assault.py Siege attack withheld names.
WORDS = {name: SCENARIOS[name].get("withheld") or list(LAND_WITHHELD)
         for name in (CAMP, LINES_A, LINES_B, ALL, ATTACK)}
# The case of the two-front battle says which side the heavy relief group attacks, so no input
# may name it, the job included (lines-eval.md check 6). The check
# rests on JUDGEMENT docs/twwarhammer3/lines-eval.md Lines deciding checks.
CASES = {LINES_A: "a", LINES_B: "b"}
# Fields of a private record unit (private_unit in the battle Lua, listed in
# capture.copy_private_record) that the mod's unit_record never gives an enemy: height, the
# flags as booleans (the observation lists them in state), climbing, visibility and ammunition.
PRIVATE_ONLY = {"y", "routing", "shattered", "melee", "hidden", "climbing", "visible", "ammo",
                "ammo0"}
WALL_ARMS = (wall_defence.WallWitness, wall_defence.HoldBuild, wall_defence.KeepOnly,
             wall_defence.WFire, wall_defence.WReserve, wall_defence.WNoFallback)
# The generic floors and controls each battle's page lists that no other file runs with hidden
# sections: hold gives no orders, and Evade and ReplaySchedule have their own tests.
LINES_FLOORS = (AttackNearest, RushNearest, Skills, reference.Concentrate)
FLOORS = {CAMP: (RushNearest,), LINES_A: LINES_FLOORS, LINES_B: LINES_FLOORS,
          WAVES: (AttackNearest, RushNearest), ALL: (AttackNearest, RushNearest),
          ATTACK: (AttackNearest, RushNearest)}

# The public parts of the first observation with units (5.2 s, land_normal, defender) of
# runs/twwarhammer3/battle/screen1-wolves-hold-l1/episode-0000/trace.jsonl, on the land battles'
# map battle_preset_qb_wh2_dlc17_taurox_rune_tortured_axes. The attacker's first observation on
# that map in speed-probe-20261031 (5.3 s) has the same rows and magic. The objective text is a
# placeholder: the game's text is not copied.
TERRAIN = {"bounds": {"max_x": 512, "max_z": 512, "min_x": -512, "min_z": -512}, "cell_m": 32,
           "sample_width_m": 16, "sampled_ms": 4900, "x0": -496, "z0": -496, "rows": [
               "#####...........................", "#####...........................",
               "######..........................", "#######.........................",
               "#######.........................", "########........................",
               "#########.......................", "#########.......................",
               ".########.......................", "..#######.......................",
               "...#####........................", "................................",
               "................................", "................................",
               "................................", "..............####..............",
               ".............#######............", ".............########...........",
               ".............#########..........", "..............##########........",
               "...............#########........", ".................#######.......#",
               "...................####........#", ".............................###",
               ".........................#######", ".........................#######",
               ".........................#######", ".........................#######",
               ".........................#######", "..........................######",
               "..........................######", "..........................######"]}
OBJECTIVES = "Objectives: (placeholder for the engine's objective text)"


def land(observation, name):
    """A land battle's first observation: the script tests' units at the declared starts, with
    the recorded map's terrain, magic and the scenario's factions."""
    observation = deepcopy(observation)
    observation["mode"] = {**observation["mode"], "objectives": OBJECTIVES}
    observation.update(terrain=deepcopy(TERRAIN), magic={"current": 12, "reserve": 68},
                       armies={side: {"faction": SCENARIOS[name][side]["faction"]}
                               for side in ("player", "enemy")})
    return observation


def first(name):
    """The first observation with units the scenario's controllers are tested on, hidden
    sections included: the camp at 2 s (unit records from the battle Lua's unit_record, with
    evaluation, native and setup), the lines at 1 s (with the other case's private reading),
    the recorded Helmgart defence and the Helmgart attack fixture."""
    if name == CAMP:
        return land(test_wh3_camp.cue()[0], name)
    if name in CASES:
        other = SCENARIOS[LINES_B if name == LINES_A else LINES_A]
        start = test_wh3_lines.battle(SCENARIOS[name], 1)[0]
        return land(test_wh3_lines.hidden(start, other), name)
    return wh3_siege_attack.first_observation() if name == ATTACK else (
        wh3_helmgart.first_observation())


def public_part(observation):
    return {key: value for key, value in observation.items() if key not in HIDDEN_KEYS}


def inputs(observation, scenario):
    """A script's input (play.public) and the model's rendered prompt for it."""
    view = play.public(deepcopy(observation), scenario)
    return view, llm.render_prompt(view, "", [], {}, None, None)


def folded(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()


def found(view, prompt, words):
    """The withheld words in any key or value of ``view`` or in ``prompt``."""
    text = folded(json.dumps(view, ensure_ascii=False) + "\n" + prompt)
    return [word for word in words if word in text]


def planted(observation, words):
    """``observation`` with every hidden section replaced by one that names each withheld word
    and puts an unseen enemy e99 at (999.5, -999.5)."""
    note, unseen = " ".join(words), {"id": "e99", "x": 999.5, "z": -999.5}
    return {**observation,
            "evaluation": {"version": 2, "note": note, "enemy": {"men": 1, "men0": 1}},
            "setup": {"note": note, "deployment_reading": {"enemy": [unseen]}},
            "native": {"units": [unseen]}, "final": {"result": "won", "note": note}}


@pytest.mark.parametrize("name", list(WORDS))
def test_controller_inputs_name_no_history_add_nothing_and_ignore_hidden_sections(name):
    """Wrong versions: a historical name or the lines case in a fixture's job; a benchmark or
    scoring tag in mode (play.public copies scenario["benchmark"] there); a briefing for a battle
    that has none; a hidden section that reaches the view or the prompt."""
    scenario, observation, words = SCENARIOS[name], first(name), WORDS[name]
    assert all(key in observation for key in ("evaluation", "setup"))
    view, prompt = inputs(observation, scenario)
    assert view == public_part(observation)
    assert inputs(planted(observation, words), scenario) == (view, prompt)
    assert inputs(public_part(observation), scenario) == (view, prompt)
    assert found(view, prompt, words) == []
    assert CASES.get(name) not in re.split(r"[^a-z0-9]+", view["job"].lower())
    # The scan reads the job and the mode: one withheld word in either is found.
    word = words[0]
    assert found(*inputs({**observation, "job": f"{word}-r1"}, scenario), words) == [word]
    assert found(*inputs(observation, {**scenario, "benchmark": f"{word}-v1"}), words) == [word]


def test_the_two_lines_cases_differ_in_a_view_only_by_enemy_positions_bearings_and_states():
    """lines-eval.md check 6: the case reaches a controller only through where the enemy stands.
    Wrong versions: a job, tag, briefing or other field that differs between the cases."""
    views = [inputs(first(name), SCENARIOS[name])[0] for name in CASES]
    assert views[0] != views[1]
    for view in views:
        for unit in view["enemy"]:
            for key in ("x", "z", "bearing", "state"):
                unit.pop(key)
    assert views[0] == views[1]


class Guarded(dict):
    """An observation that fails the test when a hidden key is read or looked up."""

    def __getitem__(self, key):
        assert key not in HIDDEN_KEYS, key
        return super().__getitem__(key)

    def get(self, key, default=None):
        assert key not in HIDDEN_KEYS, key
        return super().get(key, default)

    def __contains__(self, key):
        assert key not in HIDDEN_KEYS, key
        return super().__contains__(key)


def decisions(make, observations, view):
    """The orders a fresh policy gives on ``view`` of each observation, every order then
    acknowledged as applied (the acknowledgement wh3_ablation.run gives)."""
    policy, batches = make(), []
    for request, observation in enumerate(observations, 1):
        orders = deepcopy(policy.decide(view(deepcopy(observation))))
        batches.append(orders)
        policy.acknowledge({"request": f"r{request}", "based_on": observation["seq"],
                            "applied_ms": observation["time_ms"],
                            "results": [{"index": index, "unit": order["unit"], "ok": True,
                                         "queued": False}
                                        for index, order in enumerate(orders, 1)]},
                           {"think_s": 0.0, "roundtrip_s": 0.0, "delay_ms": 0})
    return batches


def hiding(observations, x, z):
    """Copies whose hidden sections put every roster enemy at (x, z), each at full strength:
    the evaluation and native lists, a private first reading in setup and the last one's final."""
    copies = []
    for observation in deepcopy(observations):
        units = [{"id": unit["id"], "type": unit["type"], "x": x, "z": z, "men": 67}
                 for unit in observation["enemy_roster"]]
        observation.update(evaluation={"version": 2, "enemy": {"men": 67 * len(units)},
                                       "units": units},
                           native={"units": units},
                           setup={"deployment_reading": {"enemy": units}})
        copies.append(observation)
    copies[-1]["final"] = {"result": "won", "enemy": {"men": 0}}
    return copies


@cache
def witness_schedule():
    """A schedule of the escalade witness's orders on test_wh3_escalade.sequence(), as
    replay_schedule.build records a won episode: each batch at the battle time of the
    observation it answered (every order applied), each enemy target with its last public
    place."""
    observations, seen, batches = test_wh3_escalade.sequence(), {}, []
    for request, (observation, orders) in enumerate(
            zip(observations, run(escalade.Escalade, observations), strict=True), 1):
        seen.update({enemy["id"]: {key: enemy.get(key) for key in PLACE}
                     for enemy in observation["enemy"]})
        entries = [{"order": order, **({"target": seen[order["target"]]}
                                       if order.get("target") in seen else {})}
                   for order in orders]
        if entries:
            batches.append({"time_ms": observation["time_ms"], "request": f"r{request}",
                            "orders": entries})
    start = {unit["id"]: {key: unit[key] for key in PLACE} for unit in observations[0]["friendly"]}
    return {"version": VERSION, "scenario_sha256": digest(SCENARIOS[ATTACK]),
            "source": {"job": "escalade-witness"}, "start": start, "batches": batches}


class WitnessReplay(escalade.EscaladeReplay):
    """EscaladeReplay (control C9 on escalade-eval.md) over witness_schedule()."""

    def __init__(self):
        super().__init__(deepcopy(witness_schedule()), scenario=SCENARIOS[ATTACK])


SIEGE_ARMS = (escalade.Escalade, escalade.Concentrate, escalade.CavalryEarly,
              escalade.Piecemeal, escalade.ShootOnly, escalade.GateOnly, escalade.BesiegeNearest,
              WitnessReplay)


def timelines(name):
    """The script tests' battles on ``name``: the camp cue battle, the lines fight for that case,
    the wall-defence frames, or the escalade sequence and its clock-timed variant."""
    if name == CAMP:
        return [test_wh3_camp.cue()]
    if name in CASES:
        return [test_wh3_lines.battle(SCENARIOS[name])]
    if name == ATTACK:
        return [test_wh3_escalade.sequence(), test_wh3_escalade.timed()]
    return [test_wh3_wall_defence.battle()]


@pytest.mark.parametrize("name,make", [(ATTACK, make) for make in SIEGE_ARMS]
                         + [(name, make) for name, makes in FLOORS.items() for make in makes],
                         ids=lambda value: getattr(value, "__name__", value))
def test_no_scripted_control_reads_a_hidden_section(name, make):
    """Hidden sections that place every roster enemy at (-32, -16), the Helmgart gate, or at
    (330, -100) change no order of the escalade witness, its controls and its replay, or of the
    generic floors the battle's page lists, and none of them reads one. Wrong version: a script
    that reads evaluation (or setup, native or final) when an observation carries it, as a
    replay tool that does not strip hidden keys would hand it over."""
    scenario = SCENARIOS[name]
    for observations in timelines(name):
        expected = decisions(make, observations, lambda o: play.public(o, scenario))
        assert any(expected)
        assert decisions(make, hiding(observations, -32, -16), Guarded) == expected
        assert decisions(make, hiding(observations, 330, -100), lambda o: o) == expected


def private_record(observations, shift):
    """A private record for ``observations``: one frame per observation with every own unit and
    every roster enemy, hidden ones included, ``shift`` metres from a far corner, with the
    record's own fields and a raw gate reading. Shifts 0 and 37 differ in every value but the
    ids, types and frame fields."""
    def unit(record, index):
        return {"id": record["id"], "type": record["type"], "x": 700.5 + shift + index,
                "y": 12.5 + shift, "z": -300.5 - shift, "men": 60 + shift,
                "routing": shift > 0, "shattered": shift > 0, "melee": shift == 0,
                "hidden": shift > 0, "on_wall": shift == 0, "climbing": shift > 0,
                "visible": shift == 0, "ammo": shift, "ammo0": 20 + shift}

    frames = []
    for observation in observations:
        frames.append({"private_record": 1, "job": observation["job"],
                       "battle": observation["battle"], "time_ms": observation["time_ms"],
                       "friendly": [unit(u, i) for i, u in enumerate(observation["friendly"])],
                       "enemy": [unit(u, i) for i, u in enumerate(observation["enemy_roster"])],
                       "gates": [{"name": "Gatehouse", "x": -32, "z": -16, "raw_hp": 9000 - shift,
                                  "raw_max_hp": 9000, "destroyed": False}],
                       "sample_cpu_ms": 1})
    return "".join(json.dumps(frame) + "\n" for frame in frames)


def episode(path, make, observations, scenario, record):
    """play_episode of ``make`` on ``observations`` with ``record`` as the battle's private
    record in the bridge folder: the result, what the controller was handed and the orders
    sent. The first observation is also the new-battle signal, as the mailbox gives it."""
    bridge = path / "bridge"
    bridge.mkdir(parents=True)
    (bridge / f"private-{observations[0]['battle']}.jsonl").write_text(record)
    handed = []

    class Handed(make):
        def decide(self, observation):
            handed.append(deepcopy(observation))
            return super().decide(observation)

    frames = [deepcopy(observations[0]), deepcopy(observations[0])]
    frames += [{**deepcopy(observation), "ack": True} for observation in observations[1:]]
    mailbox = FakeMailbox(frames, job=observations[0]["job"])
    mailbox.directory = bridge
    result = play.play_episode(path / "episode", {**CONFIG, "interval_ms": 0}, Handed, mailbox,
                               not_battle=None, scenario=scenario)
    return result, handed, mailbox.requests


def siege_battle(name):
    """The scripts' timelines: the wall-defence frames every 5 s from 5 s to the won result at
    135 s, or the escalade sequence (5.3 s to 140 s) and a won result 5 s later."""
    if name != ATTACK:
        return test_wh3_wall_defence.battle()
    observations = test_wh3_escalade.sequence()
    end = wh3_siege_attack.later(observations[-1], observations[-1]["time_ms"] + 5000)
    end.update(result="won", final={"result": "won"})
    return [*observations, end]


@pytest.mark.parametrize("name,make", [(WAVES, make) for make in WALL_ARMS]
                         + [(ALL, make) for make in WALL_ARMS]
                         + [(ATTACK, make) for make in SIEGE_ARMS],
                         ids=lambda value: getattr(value, "__name__", value))
def test_the_private_record_changes_no_controller_input_or_order(name, make, tmp_path,
                                                                 monkeypatch):
    """Two episodes whose private records differ in every unit value hand the scenario's scripts
    the same inputs, so the same prompts, and send the same orders; no input has a private-only
    field on an enemy, and the play loop's inputs carry the waves sentence or no briefing.
    Wrong versions: the play loop copying the record's enemies, or one of their fields, into
    observation["enemy"]; a briefing that returns the waves profile. The declaration's lobby
    check (expect) is left out because the fixtures carry no lobby readings, and the waves
    evidence check is test_wh3_waves' (the fixture's evaluation binds no held unit)."""
    monkeypatch.setattr(reserve, "check", lambda scenario, observation: None)
    scenario = {key: value for key, value in deepcopy(SCENARIOS[name]).items() if key != "expect"}
    observations = siege_battle(name)
    runs = [episode(tmp_path / str(shift), make, observations, scenario,
                    private_record(observations, shift)) for shift in (0, 37)]
    for result, handed, sent in runs:
        assert (result["status"], result["private_record"]["status"]) == ("won", "copied")
        assert handed and any(orders for _, _, orders in sent)
    (_, handed, sent), (_, other_handed, other_sent) = runs
    assert other_handed == handed and other_sent == sent
    assert not [key for view in handed for unit in view["enemy"] for key in unit
                if key in PRIVATE_ONLY]
    # The sentence rests on JUDGEMENT docs/twwarhammer3/haengju-eval.md Public presentation.
    briefing = reserve.WAVES_BRIEFING if name == WAVES else None
    assert [view.get("reserve_briefing") for view in handed] == [briefing] * len(handed)


def test_the_mods_observation_is_the_same_with_and_without_the_private_record():
    """test_wh3_private_record's siege at 1 s (e1 visible on the wall, e2 hidden behind it): the
    public part of the mod's observation does not change when the private record is switched
    off, and no enemy record has a private-only field. Wrong version: unit_record or
    enemy_observation copying a private_unit field (visible, y, ammo) into the enemy record."""
    lua, fn = private_battle()
    encode = lua.globals().json.encode
    fn["record_private"](1000, False)
    recorded = json.loads(encode(fn["observation"](1000)))
    lua.execute("session.private_record = nil")
    plain = json.loads(encode(fn["observation"](1000)))
    assert plain["seq"] == recorded["seq"] + 1  # each observation takes the next number
    assert play.public(recorded, {}) == play.public({**plain, "seq": recorded["seq"]}, {})
    assert [unit["id"] for unit in recorded["enemy"]] == ["e1"]
    assert not [key for unit in recorded["enemy"] for key in unit if key in PRIVATE_ONLY]
