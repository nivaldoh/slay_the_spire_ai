"""The siege attack's descriptive readings (battle/escalade_readings.py, design I8).

Reference: final-izmail.md (runs/siege-evals-20261108), Measurements and checks 7 and 8, with
the portfolio's corrections (contact is the engine's melee flag, a breach is hp 0 or less).
SMOKE copies, in the private record's unit fields, two observations of the only recorded siege
the player attacked (runs/twwarhammer3/battle/smoke-siege-attack-kho5-dwf5-probe_abilities-
20261014-0830/episode-0000/trace.jsonl, 5.3 s and 714.5 s, positions and men as recorded): no
unit carried the melee flag in its 776 observations, though 6 friendly-enemy pairs stood within
40 m, 364 pair readings in all. The 714.5 s copy holds two of the pairs, f3 with e2 (21.9 m) and
with e5 (10.1 m, the closest in the battle). All five defenders were visible then, so the
copy holds every enemy; a live private record would hold hidden ones too. CREW copies the
player-side ram crew's recorded course from the 2026-11-03 Altdorf checkpoint launch (below).
Offline only: these readings have read no battle with the new interface.
"""

from copy import deepcopy

from wh3_siege_attack import DEFENDERS, FORTIFICATIONS

from twwarhammer3.battle import escalade_readings as readings
from twwarhammer3.battle.escalade import front_line


def unit(identity, x, z, men):
    return {"id": identity, "x": x, "z": z, "men": men, "melee": False, "routing": False}


SMOKE = [
    {"time_ms": 5300,
     "friendly": [unit("f1", -211.6, -254.6, 1), unit("f2", -224.5, -228.8, 75),
                  unit("f3", -192.6, -228.0, 75), unit("f4", -243.5, -191.2, 45),
                  unit("f5", -206.5, -257.4, 1)],
     "enemy": [unit("e1", -285.9, -88.4, 1), unit("e2", -2.0, -23.2, 75),
               unit("e3", -245.5, -75.0, 75), unit("e4", -217.4, -71.4, 60),
               unit("e5", -4.1, 89.0, 24)]},
    {"time_ms": 714500,
     "friendly": [unit("f1", -211.6, -254.6, 1), unit("f2", -140.6, -117.3, 13),
                  unit("f3", -234.1, -81.3, 29), unit("f4", -252.4, -355.7, 19),
                  unit("f5", -206.3, -256.7, 1)],
     "enemy": [unit("e1", -237.7, -26.2, 1), unit("e2", -213.8, -73.2, 75),
               unit("e3", -18.9, -19.9, 75), unit("e4", -211.2, -31.4, 57),
               unit("e5", -232.0, -71.4, 24)]},
]
PIECES = {piece["id"]: piece for piece in FORTIFICATIONS}
SECTORS = readings.sectors({"west": "w3", "centre": "w5", "east": "w9"}, PIECES)


def test_reallocation_counts_engine_melee_flags_never_close_centres():
    """Wrong version: a proximity contact detector (the smoke's pairs within 40 m, none in
    melee, must count no contact)."""
    assert SECTORS == {"west": (-250, -130), "centre": (-135, -15), "east": (130, 250)}
    empty = {name: {"melee": [], "far": []} for name in SECTORS}
    assert readings.reallocation(SMOKE, SECTORS, 600000) == empty
    assert readings.reallocation(SMOKE, SECTORS, None) is None
    # Flags set by hand on the 714.5 s copy: e2 fights in West, where it was 128 m (along x)
    # away at the start; e3 fights in Centre, 110.5 m from where it started in West. A flag on a
    # unit with no men, or after the window, does not count.
    flagged = deepcopy(SMOKE)
    enemy = {u["id"]: u for u in flagged[1]["enemy"]}
    enemy["e2"]["melee"] = enemy["e3"]["melee"] = True
    late = deepcopy(flagged[1])
    late["time_ms"] = 720600
    late["enemy"][3].update(melee=True)  # e4 in West, after 120 s
    dead = deepcopy(flagged[1])
    dead["enemy"][0].update(melee=True, men=0)  # e1 in West, flag kept with no men
    reading = readings.reallocation(flagged + [dead, late], SECTORS, 600000)
    assert reading == {"west": {"melee": ["e2"], "far": []},
                       "centre": {"melee": ["e3"], "far": []}, "east": {"melee": [], "far": []}}
    # Measured from the end of staging instead, a unit that started far away counts as far.
    far = readings.reallocation(flagged, {"east": (128, 248), "centre": (-92, 28)}, 600000)
    assert far == {"east": {"melee": [], "far": []}, "centre": {"melee": ["e3"], "far": ["e3"]}}


LINE = front_line(FORTIFICATIONS)


def frames(*steps):
    return [{"time_ms": 1000 * index, "friendly": [dict(u) for u in step]}
            for index, step in enumerate(steps)]


def test_an_entry_is_the_engines_on_wall_reading_or_a_crossing_at_the_gate():
    """Wrong versions: a unit standing under the wall counted as on the wall; a unit whose first
    readable position is already inside, beside the gate, counted as a gate entry (an
    outside-to-inside crossing is required)."""
    # f6 waits at the foot of the wall at the 2026-11-03 climber's ground-height position.
    under = {"id": "f6", "x": 223.2, "z": -117.4, "on_wall": False}
    history = frames(
        [{"id": "f1", "x": -190, "z": -110, "on_wall": False},
         {"id": "f2", "x": -30, "z": -40, "on_wall": False},
         {"id": "f3", "x": 200, "z": -120, "on_wall": False}, under,
         {"id": "f7", "x": 0, "z": 100, "on_wall": False},
         {"id": "f8", "x": None, "z": None, "on_wall": False}],
        [{"id": "f1", "x": -190, "z": -88, "on_wall": True},
         {"id": "f2", "x": -30, "z": 0, "on_wall": False},
         {"id": "f3", "x": 200, "z": -60, "on_wall": False}, under,
         {"id": "f7", "x": 0, "z": 120, "on_wall": False},
         {"id": "f8", "x": -30, "z": 0, "on_wall": False}])
    assert readings.entry_routes(history, PIECES["g1"], LINE) == {"f1": "ladder", "f2": "gate"}


def gate(hp, destroyed=False):
    return {"mode": {"gates": [{"name": "Gatehouse", "x": -32, "z": -16, "hp": hp,
                                "destroyed": destroyed}]}}


def test_lancer_losses_stop_when_the_gate_reads_hp_zero_whatever_destroyed_says():
    """Wrong versions: losses still counted after the gate fell; a breach read from
    ``destroyed`` (two recorded gates read hp 0 with destroyed false to the end); the first
    listed gate read in place of the one nearest g1."""
    observations = [{"time_ms": t, "friendly": [{"id": "f12", "men": men}], **gate(hp)}
                    for t, men, hp in ((5000, 45, 100), (60000, 40, 50), (90000, 30, 0),
                                       (120000, 10, 0))]
    reading = {"men0": 45, "lost": 5, "share": 5 / 45, "breach_ms": 90000}
    assert readings.lancer_losses(observations, {"f12"}, PIECES["g1"]) == reading
    assert readings.lancer_losses([], {"f12"}, PIECES["g1"]) is None
    # A map with several gates (the Altdorf checkpoint read six) lists a broken far one first.
    far = {"name": "Gatehouse", "x": 138, "z": 394, "hp": 0, "destroyed": True}
    for observation in observations:
        observation["mode"]["gates"].insert(0, dict(far))
    assert readings.lancer_losses(observations, {"f12"}, PIECES["g1"]) == reading


def test_wall_to_point_runs_from_the_first_on_wall_to_the_first_victory_point_held():
    def point(holder):
        return {"id": "c7", "victory": True, **({"holder": holder} if holder else {})}

    observations = [
        {"time_ms": 100000, "friendly": [{"id": "f2", "on_wall": False}],
         "mode": {"capture_points": [point("enemy"), {"id": "c4", "holder": "us"}]}},
        {"time_ms": 130000, "friendly": [{"id": "f2", "on_wall": True}],
         "mode": {"capture_points": [point(None)]}},
        {"time_ms": 175000, "friendly": [{"id": "f2", "on_wall": False}],
         "mode": {"capture_points": [point("us")]}}]
    assert readings.wall_to_point(observations) == {"on_wall_ms": 130000, "held_ms": 175000,
                                                    "delta_ms": 45000}


GARRISON = [{"id": identity, "type": kind, "x": float(x), "z": float(z), "men": 67, "on_wall": True}
            for identity, kind, x, z in DEFENDERS]


def test_the_first_on_wall_per_group_reads_our_units_never_the_garrison():
    """Wrong version: the garrison's units on the wall counted as ours."""
    def frame(time_s, on_wall=()):
        return {"time_ms": 1000 * time_s, "enemy": deepcopy(GARRISON),
                "friendly": [{"id": identity, "x": 0.0, "z": -200.0, "on_wall": identity in on_wall}
                             for identity in ("f2", "f3", "f5", "f8")]}

    history = [frame(5), frame(130, {"f3"}), frame(140, {"f3", "f8"})]
    assert readings.first_on_wall(history[:1]) == {"all": None}
    assert readings.first_on_wall(history) == {"all": 130000}
    groups = {"west": ["f2", "f3"], "centre": ["f8"], "east": ["f5"]}
    assert readings.first_on_wall(history, groups) == {"west": 130000, "centre": 140000,
                                                       "east": None}


def on(piece, identity, dx=0):
    """An own unit reading on_wall at a fixture piece's centre, ``dx`` metres along x."""
    return {"id": identity, "x": PIECES[piece]["x"] + dx, "z": PIECES[piece]["z"], "on_wall": True}


def test_wall_sections_count_the_sections_held_never_the_units():
    """Wrong versions: units on the wall counted in place of sections; the garrison counted."""
    one = [{"time_ms": 130000, "enemy": GARRISON,
            "friendly": [on("w3", "f2", -5), on("w3", "f3"), on("w3", "f7", 5)]}]
    assert readings.wall_sections(one, FORTIFICATIONS) == {"first_ms": 130000, "sections": 1}
    # The witness's targets w3, w5 and w9 lie in the 120 m bins -2, -1 and 1; Concentrate's w5,
    # w5 and w7 in -1, -1 and 0. A unit that reaches w11 121 s after the first reading is late.
    spread = [{"time_ms": 130000, "friendly": [on("w3", "f2")]},
              {"time_ms": 200000, "friendly": [on("w3", "f2"), on("w5", "f8"), on("w9", "f5")]},
              {"time_ms": 251000, "friendly": [on("w11", "f6")]}]
    assert readings.wall_sections(spread, FORTIFICATIONS) == {"first_ms": 130000, "sections": 3}
    recess = [{"time_ms": 140000, "friendly": [on("w5", "f2"), on("w5", "f8"), on("w7", "f5")]}]
    assert readings.wall_sections(recess, FORTIFICATIONS) == {"first_ms": 140000, "sections": 2}
    assert readings.wall_sections([{"time_ms": 5000, "enemy": GARRISON, "friendly": [
        {"id": "f2", "x": 0, "z": -230, "on_wall": False}]}], FORTIFICATIONS) is None


# The player-side ram crew of the 2026-11-03 Altdorf checkpoint launch (runs/twwarhammer3/
# siege-905-20261103/capital-attacker/source/native/native.jsonl: unit 1002 and VehicleList item
# 0, read every 5 s), every 10 s from its scripted besiege_building at 10 s: (s, crew x, crew z,
# ram x, ram z). The ram moved 223 m in these 180 s. The script besieged the last gate building in
# its list; the engine set the crew's destination to (108.1, 407.2), 32.7 m from the Gatehouse at
# (138, 394), the nearest of the six listed, which stands in for g1 here.
CREW = [(10, -409.0, 325.9, -392.4, 326.1), (20, -400.7, 323.2, -386.0, 328.6),
        (30, -388.8, 329.5, -372.6, 334.5), (40, -375.1, 334.6, -360.8, 339.9),
        (50, -363.5, 338.9, -349.4, 345.1), (60, -352.0, 343.6, -337.4, 350.4),
        (70, -339.8, 349.4, -326.1, 355.6), (80, -329.3, 354.0, -315.3, 360.4),
        (90, -318.5, 358.6, -304.3, 365.3), (100, -307.5, 363.7, -293.4, 370.2),
        (110, -297.0, 368.4, -283.2, 374.7), (120, -287.2, 372.5, -273.2, 379.1),
        (130, -277.2, 376.7, -263.2, 383.5), (140, -268.0, 380.2, -252.3, 388.4),
        (150, -255.5, 383.7, -240.6, 393.4), (160, -247.4, 386.2, -228.3, 398.5),
        (170, -231.2, 397.1, -215.4, 404.3), (180, -221.0, 404.6, -202.2, 410.4),
        (190, -203.8, 410.0, -188.4, 416.5)]


def test_the_recorded_ram_crew_acted_on_its_besiege_though_the_ram_never_reached_the_gate():
    """Wrong versions: 'acted on' read as the ram within 15 m of the gate within 180 s (the ram
    stood 327 m from it at 190 s); the start distance taken from an earlier frame; no 60 s or
    120 s window; an unread unit read as not acted on. The trace rows are play's ("decision"
    orders, "ack" results by index). Made up: f3 stands 20 m from w1 and reads climbing at 100 s;
    f4, a gun ordered at g1, fires from where it stands and reads not acted on; f6's refused
    besiege is not listed; f7 stood 100 m farther at 5 s, before its order, then stands; f8 comes
    60 m nearer at 80 s and climbs at 140 s, both after their windows; f9 is never read."""
    view = {"kind": "observation", "observation": {"time_ms": 9500, "mode": {"fortifications": [
        {"id": "g1", "kind": "gate", "x": 138, "z": 394, "hp": 100},
        {"id": "w1", "kind": "wall", "x": -300, "z": 330, "hp": 100}]}}}
    orders = [{"unit": "f2", "type": "besiege", "target": "g1", "run": True},
              {"unit": "f3", "type": "besiege", "target": "w1", "run": True},
              {"unit": "f4", "type": "attack_building", "target": "g1", "run": False},
              {"unit": "f5", "type": "move", "x": -300, "z": 200, "run": False}] + [
              {"unit": identity, "type": "besiege", "target": "w1", "run": True}
              for identity in ("f7", "f8", "f9")]
    trace = [view, {"kind": "decision", "request": "r1", "time_ms": 9500, "orders": orders},
             {"kind": "ack", "request": "r1", "ack": {"request": "r1", "applied_ms": 10000,
                                                      "results": [{"index": i, "ok": True}
                                                                  for i in range(1, 8)]}},
             {"kind": "decision", "request": "r2", "time_ms": 15000, "orders": [
                 {"unit": "f6", "type": "besiege", "target": "w1", "run": True}]},
             {"kind": "ack", "request": "r2", "ack": {"request": "r2", "applied_ms": 15300,
                                                      "results": [{"index": 1, "ok": False}]}}]
    frames = [{"time_ms": 5000, "friendly": [{"id": "f7", "x": -300.0, "z": 130.0,
                                              "climbing": False}]}] + [
        {"time_ms": 1000 * s, "vehicles": [{"category": "battering_ram", "x": rx, "z": rz,
                                            "crew": "f2"}],
         "friendly": [{"id": "f2", "x": x, "z": z, "climbing": False},
                      {"id": "f3", "x": -300.0, "z": 310.0, "climbing": s >= 100},
                      {"id": "f4", "x": 162.0, "z": 94.0, "climbing": False},
                      {"id": "f6", "x": -300.0, "z": 300.0, "climbing": False},
                      {"id": "f7", "x": -300.0, "z": 230.0, "climbing": False},
                      {"id": "f8", "x": -300.0, "z": 260.0 if s >= 80 else 200.0,
                       "climbing": s >= 140}]}
        for s, x, z, rx, rz in CREW]
    late = {"type": "besiege", "target": "w1", "applied_ms": 10000, "closed_ms": None,
            "climbing_ms": None}
    assert readings.siege_order_acted_on(trace, frames) == [
        {"unit": "f2", "type": "besiege", "target": "g1", "applied_ms": 10000, "start_m": 551.2,
         "closed_ms": 60000, "climbing_ms": None, "acted_on": True},
        {"unit": "f3", "type": "besiege", "target": "w1", "applied_ms": 10000, "start_m": 20.0,
         "closed_ms": None, "climbing_ms": 100000, "acted_on": True},
        {"unit": "f4", "type": "attack_building", "target": "g1", "applied_ms": 10000,
         "start_m": 301.0, "closed_ms": None, "climbing_ms": None, "acted_on": False},
        {"unit": "f7", **late, "start_m": 100.0, "acted_on": False},
        {"unit": "f8", **late, "start_m": 130.0, "acted_on": False},
        {"unit": "f9", **late, "start_m": None, "acted_on": None}]
