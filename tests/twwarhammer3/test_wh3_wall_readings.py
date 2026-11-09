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
from wh3_helmgart import MODE

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
    for time_ms, ammo, z in ((100000, 22, -235), (105000, 15, -230), (110000, 9, -200)):
        observations.append({"time_ms": time_ms,
                             "friendly": [{**archers, "ammo": ammo},
                                          {"id": "f1", "x": 0, "z": 0, "ammo": 0, "ammo0": 0}],
                             "enemy": [unit("e10", -4, z)]})
    # At x = -4 the line is at z -22.8, so e10 stands about 212, 207, 177, then 147 m from it.
    observations.append({**copy.deepcopy(observations[-1]), "time_ms": 115000,
                         "enemy": [unit("e10", -4, -170)]})
    observations[-1]["friendly"][0]["ammo"] = 4
    result = wall_readings.approach_ammunition(observations, {"D2": ["e10"], "D3": ["e12"]},
                                               LINE)
    assert result == {"D2": {"time_ms": 115000, "ammo": 4, "ammo0": 22}, "D3": None}


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


def test_damage_releases_are_read_from_the_trace_play_writes(tmp_path):
    """The rows are the trace.jsonl that play.play_episode writes for hand-made observations
    carrying waves evidence in the mod's shape. Wrong version: the releases read from the last
    row's or the last logged view's ``evaluation``, which play's views never carry."""
    profile = setup.scenarios()["cth-emp-siege-a-v1"]["reserve"]
    held = [{"group": number, "slot": slot, "type": kind, "id": f"e{slot}"}
            for number, group in enumerate(profile["groups"], 1)
            for slot, kind in zip(group["slots"], group["types"], strict=True)]
    shot = {"group": 2, "reason": "damage", "released_ms": 40250, "ok": True,
            "damaged": [{"id": "e11", "men": 89, "men0": 90, "under_fire": False}],
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
        {"group": 2, "time_ms": 40250, "damaged": ["e11"], "friendly_in_range": ["f9"]}]


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
