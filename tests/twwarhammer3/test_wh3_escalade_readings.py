"""The siege attack's descriptive readings (battle/escalade_readings.py, design I8).

Reference: final-izmail.md (runs/siege-evals-20261108), Measurements and checks 7 and 8, with
the portfolio's corrections (contact is the engine's melee flag, a breach is hp 0 or less).
SMOKE copies, in the private record's unit fields, two observations of the only recorded siege
the player attacked (runs/twwarhammer3/battle/smoke-siege-attack-kho5-dwf5-probe_abilities-
20261014-0830/episode-0000/trace.jsonl, 5.3 s and 714.5 s, positions and men as recorded): no
unit carried the melee flag in its 776 observations, though 364 friendly-enemy pairs stood
within 40 m, f3 and e5 10.1 m apart at 714.5 s. All five defenders were visible then, so the
copy holds every enemy; a live private record would hold hidden ones too. Offline only: these
readings have read no battle with the new interface.
"""

from copy import deepcopy

from wh3_siege_attack import FORTIFICATIONS

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
    """Wrong version: a unit standing under the wall counted as on the wall."""
    # f6 waits at the foot of the wall at the 2026-11-03 climber's ground-height position.
    under = {"id": "f6", "x": 223.2, "z": -117.4, "on_wall": False}
    history = frames(
        [{"id": "f1", "x": -190, "z": -110, "on_wall": False},
         {"id": "f2", "x": -30, "z": -40, "on_wall": False},
         {"id": "f3", "x": 200, "z": -120, "on_wall": False}, under,
         {"id": "f7", "x": 0, "z": 100, "on_wall": False}],
        [{"id": "f1", "x": -190, "z": -88, "on_wall": True},
         {"id": "f2", "x": -30, "z": 0, "on_wall": False},
         {"id": "f3", "x": 200, "z": -60, "on_wall": False}, under,
         {"id": "f7", "x": 0, "z": 120, "on_wall": False}])
    assert readings.entry_routes(history, PIECES["g1"], LINE) == {"f1": "ladder", "f2": "gate"}


def gate(hp, destroyed=False):
    return {"mode": {"gates": [{"name": "Gatehouse", "x": -32, "z": -16, "hp": hp,
                                "destroyed": destroyed}]}}


def test_lancer_losses_stop_when_the_gate_reads_hp_zero_whatever_destroyed_says():
    """Wrong versions: losses still counted after the gate fell; a breach read from
    ``destroyed`` (two recorded gates read hp 0 with destroyed false to the end)."""
    observations = [{"time_ms": t, "friendly": [{"id": "f12", "men": men}], **gate(hp)}
                    for t, men, hp in ((5000, 45, 100), (60000, 40, 50), (90000, 30, 0),
                                       (120000, 10, 0))]
    assert readings.lancer_losses(observations, {"f12"}, PIECES["g1"]) == {
        "men0": 45, "lost": 5, "share": 5 / 45, "breach_ms": 90000}
    assert readings.lancer_losses([], {"f12"}, PIECES["g1"]) is None


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
