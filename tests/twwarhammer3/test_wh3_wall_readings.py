"""The walled siege defence's evaluator readings (wall_readings.py).

HELMGART is cut from runs/twwarhammer3/battle/bench-b12-siege-baselines-20261016/episode-0001/
trace.jsonl (the Chaos Dwarf hold baseline, lost at 708.7 s): the observations just before and at
each change of the Gatehouse c2, Fort Tower c3, supply point c7, Key Building c1 and the
defender's tickets, fields trimmed, values unchanged. A recorded holder of None has no
``holder`` key. Counted by hand from that trace: c3 neutral at 5.2 s and enemy-held from 64.9 s,
c2 enemy-held from 336.7 s, c7 from 467.8 s, c1 from 699.1 s, tickets first below 1,000 at
700.3 s. The other cases are written by hand. Offline only: no stage 1 battle exists yet.
"""

import copy
import json

import pytest
from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation
from wh3_helmgart import MODE, first_observation

from twwarhammer3.battle import play, setup, wall_defence, wall_readings
from twwarhammer3.battle.scripted import Hold

HOLDERS = {  # time_ms -> holders of c1, c2, c3, c7 (None: neutral)
    5200: ("us", "us", None, "us"), 63700: ("us", "us", None, "us"),
    64900: ("us", "us", "enemy", "us"), 335500: ("us", "us", "enemy", "us"),
    336700: ("us", "enemy", None, "us"), 466600: ("us", "enemy", None, "us"),
    467800: ("us", "enemy", None, "enemy"), 697900: ("us", "enemy", None, "enemy"),
    699100: ("enemy", "enemy", None, "enemy"), 700300: ("enemy", "enemy", None, "enemy")}
TICKETS = {700300: 990}


def helmgart(attacker_row=False):
    observations = []
    for time_ms, holders in HOLDERS.items():
        points = [{"id": name, **({"holder": holder} if holder else {})}
                  for name, holder in zip(("c1", "c2", "c3", "c7"), holders, strict=True)]
        rows = [{"per_s": 5, "score": 0, "side": "us", "tickets": TICKETS.get(time_ms, 1000)}]
        if attacker_row:  # written by hand: a falling attacker row listed first
            rows.insert(0, {"per_s": 1, "score": 0, "side": "enemy",
                            "tickets": 1000 - time_ms // 1000})
        observations.append({"time_ms": time_ms, "mode": {"role": "defender",
                                                          "capture_points": points,
                                                          "tickets": rows}})
    return observations


@pytest.mark.parametrize("attacker_row", [False, True])
def test_holder_times_and_ticket_onset_match_the_recorded_hold_baseline(attacker_row):
    observations = helmgart(attacker_row)
    assert wall_readings.enemy_held(observations, ("c1", "c2", "c3", "c7")) == {
        "c1": 699100, "c2": 336700, "c3": 64900, "c7": 467800}
    assert wall_readings.ticket_onset(observations) == 700300


def test_the_gate_c2_and_fallback_times_come_from_the_observations_and_the_witness_trace(tmp_path):
    """Helmgart fixture observations shaped like the hold baseline: the gate first below 100 at
    70.9 s, then hp 0 with destroyed false from 258.4 s, and c2 enemy-held from 336.7 s, played by
    WallWitness through play.play_episode. Wrong version: the gate read by ``destroyed``."""
    rows = []
    for seq, time_ms, hp, holder in ((1, 5200, 100, "us"), (2, 70900, 97, "us"),
                                     (3, 258400, 0, "us"), (4, 336700, 0, "enemy"),
                                     (5, 340000, 0, "enemy")):
        row = {**first_observation(job="job"), "seq": seq, "time_ms": time_ms, "ack": seq > 1}
        row["mode"]["gates"][0].update(hp=hp, destroyed=False)
        row["mode"]["capture_points"][1]["holder"] = holder
        if seq > 1:
            row.pop("setup")
        if seq == 5:
            row.update(result="lost", final={"friendly": {"men": 50, "men0": 734},
                                             "enemy": {"men": 900, "men0": 1463}})
        rows.append(row)
    play.play_episode(tmp_path / "episode", {**CONFIG, "interval_ms": 0},
                      wall_defence.WallWitness, FakeMailbox(rows), not_battle=None, scenario={})
    lines = (tmp_path / "episode/trace.jsonl").read_text().splitlines()
    trace = [json.loads(line) for line in lines]
    assert wall_readings.gate_timeline(rows, trace) == {
        "gate_ms": 258400, "c2_ms": 336700, "fallback_ms": 258400, "fallback_reason": "gate"}


LINE = wall_defence.wall_line({point["id"]: point for point in MODE["capture_points"]})


def unit(identity, x, z, **fields):
    return {"id": identity, "x": x, "z": z, "men": 90, "state": [], **fields}


def test_a_division_is_first_seen_in_the_public_enemy_list_never_the_private_record():
    divisions = {"D2": ["e10", "e11"], "D3": ["e12", "e1"]}
    observations = [
        {"time_ms": 5000, "enemy": []},
        {"time_ms": 10000, "enemy": [unit("e11", -80, -400)]},
        {"time_ms": 15000, "enemy": [unit("e11", -80, -380)]},
        {"time_ms": 20000, "enemy": [unit("e1", 40, -500), unit("e11", -80, -360)]}]
    # Recorded observations also carry hidden sections that list every unit from the start, as
    # the private record does: the first reading in setup, and native.
    every = [unit(identity, 0, -600) for identity in ("e1", "e10", "e11", "e12")]
    observations[0]["setup"] = {"deployment_reading": {"enemy": every}}
    for observation in observations:
        observation["native"] = {"units": every}
    assert wall_readings.first_sightings(observations, divisions) == {"D2": 10000, "D3": 20000}


def test_ammunition_is_read_at_each_divisions_first_approach_within_150_m_of_the_wall():
    archers = {"id": "f5", "x": -55, "z": -23, "ammo": 22, "ammo0": 22, "range": 140}
    observations = []
    for time_ms, ammo, z in ((100000, 22, -235), (105000, 15, -230), (110000, 9, -200),
                             (112500, 6, -176)):
        observations.append({"time_ms": time_ms,
                             "friendly": [{**archers, "ammo": ammo},
                                          {"id": "f1", "x": 0, "z": 0, "ammo": 0, "ammo0": 0}],
                             "enemy": [unit("e10", -4, z)]})
    # e10 stands about 210, 205, 175, 151.7, 145.8, then 135.9 m from the wall line: the first
    # approach is at 115,000 ms, and the later one does not replace it.
    for time_ms, ammo, z in ((115000, 4, -170), (120000, 0, -160)):
        observations.append({**copy.deepcopy(observations[-1]), "time_ms": time_ms,
                             "enemy": [unit("e10", -4, z)]})
        observations[-1]["friendly"][0]["ammo"] = ammo
    # D4's e15 is first seen at 120,000 ms already inside the line at (-4, 150), about 173 m
    # north of it: that is its approach, however far it stands from the line (rests on
    # JUDGEMENT? wall_readings.py Approach distance).
    observations[-1]["enemy"].append(unit("e15", -4, 150))
    result = wall_readings.approach_ammunition(
        observations, {"D2": ["e10"], "D3": ["e12"], "D4": ["e15"]}, LINE)
    assert result == {"D2": {"time_ms": 115000, "ammo": 4, "ammo0": 22}, "D3": None,
                      "D4": {"time_ms": 120000, "ammo": 0, "ammo0": 22}}


SQUARE = [(-100, -40), (100, -40), (100, 100), (-100, 100)]


def test_a_breach_is_an_on_wall_reading_or_two_frames_inside_the_private_polygon():
    def frames(*rows):
        return [{"time_ms": 1000 * second, "enemy": enemies} for second, enemies in rows]

    # A centre inside for one frame (a squad jump), then out, then in for two frames.
    jumpy = frames((1, [unit("e3", 0, -60)]), (2, [unit("e3", 0, -30)]),
                   (3, [unit("e3", 0, -60)]), (4, [unit("e3", 0, -20)]),
                   (5, [unit("e3", 0, -10)]))
    assert wall_readings.breach(jumpy, SQUARE) == {"time_ms": 5000, "id": "e3", "by": "polygon"}
    assert wall_readings.breach(jumpy) is None  # no polygon before stage 1, no on_wall reading
    climbed = frames((1, [unit("e4", 0, -90, on_wall=False)]),
                     (2, [unit("e4", 0, -85, on_wall=True)]))
    assert wall_readings.breach(climbed, SQUARE) == {"time_ms": 2000, "id": "e4",
                                                     "by": "on_wall"}


def private_unit(identity, x, z, men=90, **flags):
    """A unit of a private-record frame, every field record_private writes (capture.py)."""
    return {"id": identity, "type": "wh_main_emp_inf_swordsmen", "x": x, "y": 0.0, "z": z,
            "men": men, "routing": False, "shattered": False, "melee": False, "hidden": False,
            "on_wall": False, "climbing": False, "visible": False, "ammo": 0, "ammo0": 0, **flags}


def private_frame(time_ms, enemy, friendly=()):
    return {"private_record": 1, "job": "job", "battle": "b1", "time_ms": time_ms,
            "friendly": list(friendly), "enemy": enemy, "sample_cpu_ms": 0.4}


def test_a_divisions_men_lost_are_counted_until_one_of_its_units_reads_melee_or_on_wall():
    """Private-record frames by hand. Wrong versions: losses counted after the first melee; the
    melee flag of a unit with no men left read as contact (the flag outlives the men); a cut-off
    per unit, which counts e3's losses after e1's contact."""
    def frame(second, d1, d2, d3):
        return private_frame(1000 * second, [
            *(private_unit(f"e{slot}", 40 * slot, -300, men, **flags)
              for slot, (men, flags) in enumerate(d1, 1)),
            private_unit("e5", 0, -530, d2[0], **d2[1]), private_unit("e9", 0, -595, d3)])

    calm = {}
    frames = [frame(1, ((90, calm), (90, calm), (90, calm)), (90, calm), 90),
              frame(2, ((85, calm), (90, calm), (90, calm)), (90, calm), 90),
              frame(3, ((80, calm), (0, {"melee": True}), (90, calm)), (88, calm), 90),  # e2 shot
              frame(4, ((70, {"melee": True}), (0, {"melee": True}), (90, calm)), (88, calm), 85),
              # e3, still on the approach, loses 30 men after e1's contact.
              frame(5, ((50, {"melee": True}), (0, calm), (60, calm)), (85, {"on_wall": True}), 80)]
    divisions = {"D1": ["e1", "e2", "e3"], "D2": ["e5"], "D3": ["e9"]}
    assert wall_readings.division_missile_losses(frames, divisions) == {
        "D1": {"men_lost": 100, "contact_ms": 4000}, "D2": {"men_lost": 2, "contact_ms": 5000},
        "D3": {"men_lost": 10, "contact_ms": None}}


def test_damage_releases_are_read_from_the_trace_play_writes(tmp_path):
    """The rows are the trace.jsonl that play.play_episode writes for hand-made observations
    carrying waves evidence in the mod's shape. Wrong versions: the releases read from the last
    row's or the last logged view's ``evaluation``, which play's views never carry; the distance
    to the nearest garrison unit in place of D1's."""
    profile = setup.scenarios()["cth-emp-siege-a-v1"]["reserve"]
    held = [{"group": number, "slot": slot, "type": kind, "id": f"e{slot}"}
            for number, group in enumerate(profile["groups"], 1)
            for slot, kind in zip(group["slots"], group["types"], strict=True)]
    # e11 lost a man; e12 was only flagged under missile attack; e13 was flagged and lost men.
    shot = {"group": 2, "reason": "damage", "released_ms": 40250, "ok": True,
            "damaged": [{"id": "e11", "men": 89, "men0": 90, "under_fire": False},
                        {"id": "e12", "men": 90, "men0": 90, "under_fire": True},
                        {"id": "e13", "men": 80, "men0": 90, "under_fire": True}],
            "units": [{"id": f"e{slot}", "x": x, "z": -595, "men": 90}
                      for slot, x in zip(range(9, 14), (-20, 10, 100, 130, 160), strict=True)]}
    on_time = {"group": 1, "reason": "time", "released_ms": 150000, "ok": True,
               "units": [{"id": f"e{slot}", "x": 0, "z": -400, "men": 90} for slot in range(5, 9)]}
    cannon = {"id": "f9", "type": "wh3_main_cth_art_grand_cannon_0", "class": "artillery",
              "x": 100.0, "z": -160.0, "men": 12, "men0": 12, "hp": 1.0, "state": [],
              "range": 450}
    archers = {**cannon, "id": "f5", "type": "wh3_main_cth_inf_peasant_archers_0",
               "class": "infantry", "x": -55.0, "z": -23.0, "range": 140}
    # The cannon is out of range of e11 (895 m) in the battle row, the start roster and the
    # views after the release; only the view at 40,000 ms has it in range.
    rows = []
    for seq, time_ms, releases, z in ((0, 5000, [], 300), (1, 20000, [], 300),
                                      (2, 40000, [], -160), (3, 41000, [shot], 300),
                                      (4, 150500, [shot, on_time], 300)):
        row = bridge_observation(seq, time_ms, ack=seq in (2, 3),
                                 result="won" if seq == 4 else None)
        row["friendly"] = [{**cannon, "z": float(z)}, archers]
        row["enemy_roster"] = [{"id": unit["id"], "type": unit["type"]} for unit in held]
        row["evaluation"] = {"reserve": {"config": profile, "units": held, "releases": releases}}
        rows.append(row)
    result = play.play_episode(tmp_path / "episode", {**CONFIG, "interval_ms": 0}, Hold,
                               FakeMailbox(rows), not_battle=None, scenario={"reserve": profile})
    assert result["status"] == "won"
    lines = (tmp_path / "episode/trace.jsonl").read_text().splitlines()
    trace = [json.loads(line) for line in lines]
    views = [row["observation"] for row in trace if row["kind"] == "observation"]
    assert [view["time_ms"] for view in views] == [20000, 40000, 41000]
    assert not any("evaluation" in view for view in views)
    # The view at 40,000 ms, before the release at 40,250, has the cannon 435 m from e11.
    assert wall_readings.damage_releases(trace) == [
        {"group": 2, "time_ms": 40250, "damaged": ["e11", "e12", "e13"],
         "friendly_in_range": ["f9"]}]
    # In the frame at 40,000 ms, the last before the release, the nearest D1 unit with men left
    # is e3, 272.6 m from e11; dead e2 stands 35 m from it and the cannon 435 m. By 41,000 ms e3
    # has come within 25 m.
    held_units = [private_unit(f"e{slot}", x, -595) for slot, x in
                  zip(range(9, 14), (-20, 10, 100, 130, 160), strict=True)]
    garrison = [private_unit("f9", 100, -160), private_unit("f5", -55, -23)]
    frames = [private_frame(40000, [private_unit("e1", -44, -300), private_unit("e2", 100, -560, 0),
                                    private_unit("e3", 36, -330), private_unit("e4", 76, -200),
                                    *held_units], garrison),
              private_frame(41000, [private_unit("e3", 100, -570), *held_units], garrison)]
    assert wall_readings.release_distances(trace, frames, ["e1", "e2", "e3", "e4"]) == [
        {"group": 2, "time_ms": 40250, "damaged": [
            {"id": "e11", "lost_men": True, "d1_m": 272.6},
            {"id": "e12", "lost_men": False, "d1_m": 281.2},
            {"id": "e13", "lost_men": True, "d1_m": 292.6}]}]


def test_the_reserve_response_runs_from_the_breach_to_its_first_accepted_attack_and_melee():
    # Rows in trace.jsonl's shape (decision orders, ack results by one-based index), by hand.
    def sent(request, time_ms, orders, oks):
        return [{"kind": "decision", "request": request, "time_ms": time_ms, "orders": orders},
                {"kind": "ack", "request": request, "ack": {
                    "request": request, "applied_ms": time_ms + 300, "results": [
                        {"index": index, "unit": order["unit"], "ok": ok}
                        for index, (order, ok) in enumerate(zip(orders, oks, strict=True), 1)]}}]

    def attack(identity):
        return {"unit": identity, "type": "attack", "target": "e3"}

    lord, jade, archers = wall_defence.LORD, wall_defence.JADE, wall_defence.ARCHERS
    # The reserve is f4 (the Lord), f2 and f6 (Jade Warriors), found by type; f1 is archers.
    trace = [*sent("r1", 95000, [attack("f4")], [True]),  # before the breach
             *sent("r2", 100000, [attack("f1"), attack("f2")], [True, False]),  # archers; refused
             *sent("r3", 105000, [{"unit": "f4", "type": "move", "x": 0, "z": 0},
                                  attack("f6")], [True, True])]
    kinds = {"f1": archers, "f2": jade, "f4": lord, "f6": jade}

    def frame(time_ms, melee=(), dead=()):
        return {"time_ms": time_ms, "enemy": [], "friendly": [
            unit(identity, 0, 0, type=kind, men=0 if identity in dead else 90,
                 state=["melee"] if identity in melee else []) for identity, kind in kinds.items()]}

    frames = [frame(99000, melee=["f4"]), frame(100000, melee=["f2"], dead=["f2"]),
              frame(101000, melee=["f1"]), frame(108000, melee=["f6"])]
    breached = {"time_ms": 100000, "id": "e3", "by": "on_wall"}
    assert wall_readings.reserve_response(trace, frames, breached) == {
        "attack_ms": 5300, "melee_ms": 8000}
    assert wall_readings.reserve_response(trace[:4], frames[:3], breached) == {
        "attack_ms": None, "melee_ms": None}
    assert wall_readings.reserve_response(trace, frames, None) is None
