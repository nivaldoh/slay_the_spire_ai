"""Helmgart's recorded first observation, for the walled siege defence tests.

Copied (fields trimmed, values unchanged) from the first observation with units, at 5.2 s, of
runs/twwarhammer3/battle/bench-b12-siege-baselines-20261016/episode-0001/trace.jsonl, a Chaos
Dwarf garrison on battle_preset_wh2_dlc13_minor_settlement_empire_fort. Two parts are not the
recording's: ``mode.objectives`` is a placeholder (the game's own text is not copied), and the
garrison is cth-emp-siege-a-v1's Cathay roster standing on the recorded Chaos Dwarf starts (the
engine's Cathay start is unread until stage 1), with the tenth unit at the Key Building.
"""

from copy import deepcopy

from twwarhammer3.battle.setup import scenarios

SCENARIO = scenarios()["cth-emp-siege-a-v1"]
OPTIONS = [{"cost": 500, "name": "tower_piercing_1"}, {"cost": 900, "name": "tower_piercing_2"},
           {"cost": 1400, "name": "tower_magic_3"}, {"cost": 2000, "name": "tower_magic_4"}]
MODE = {
    "type": "settlement_standard", "role": "defender", "timeout_winner": "us",
    "objectives": "Objectives: (placeholder for the engine's siege objective text)",
    "capture_points": [
        {"contested": False, "holder": "us", "id": "c1", "key": "major_key_building_leadership",
         "locked": False, "name": "Key Building", "percent": 100, "victory": True, "x": 0,
         "z": 310},
        {"contested": False, "holder": "us", "id": "c2", "key": "capture_point_gate_only",
         "locked": False, "name": "Gatehouse", "percent": 100, "victory": False, "x": -2,
         "z": -22.5},
        {"contested": False, "id": "c3", "key": "capture_point_tower_only", "locked": False,
         "name": "Fort Tower", "percent": 100, "victory": False, "x": 188, "z": -81},
        {"contested": False, "id": "c4", "key": "capture_point_tower_only", "locked": False,
         "name": "Fort Tower", "percent": 100, "victory": False, "x": 58, "z": -31},
        {"contested": False, "holder": "us", "id": "c5", "key": "capture_point_tower_only",
         "locked": False, "name": "Fort Tower", "percent": 100, "victory": False, "x": -62,
         "z": -31},
        {"contested": False, "id": "c6", "key": "capture_point_tower_only", "locked": False,
         "name": "Fort Tower", "percent": 100, "victory": False, "x": -192, "z": -81},
        {"contested": False, "holder": "us", "id": "c7", "key": "minor_point_supplies",
         "locked": False, "name": "Minor Supply Location", "percent": 100, "victory": True,
         "x": -1, "z": 155},
        {"contested": False, "holder": "us", "id": "c8", "key": "minor_point_supplies",
         "locked": False, "name": "Minor Supply Location", "percent": 100, "victory": True,
         "x": -320, "z": 320},
        {"contested": False, "holder": "us", "id": "c9", "key": "minor_point_supplies",
         "locked": False, "name": "Minor Supply Location", "percent": 100, "victory": True,
         "x": 320, "z": 320}],
    "gates": [{"destroyed": False, "hp": 100, "name": "Gatehouse", "x": -32, "z": -16}],
    "slots": [{"id": slot, "options": OPTIONS, "type": "tower", "usable": True, "x": x, "z": z}
              for slot, x, z in (("s1", 55.200000762939, 191.69999694824),
                                 ("s2", -56.200000762939, 191.69999694824),
                                 ("s3", -111, 352.89999389648), ("s4", 110, 353),
                                 ("s5", 289, 187), ("s6", -299, 191),
                                 ("s7", 127.69999694824, 96.900001525879),
                                 ("s8", -131.19999694824, 96.800003051758))],
    "supplies": 6000,
    "tickets": [{"per_s": 5, "score": 0, "side": "us", "tickets": 1000}],
}
TERRAIN = {"bounds": {"max_x": 384, "max_z": 384, "min_x": -384, "min_z": -640}, "cell_m": 32,
           "sample_width_m": 16, "sampled_ms": 4900, "x0": -368, "z0": -624, "rows": [
               "########...........#####", "#######............#####",
               "######.#...........#####", "######...............###",
               "########.........#...###", "####..##.........##.####",
               "####................####", "####................####",
               "####................####", "###.................####",
               "###.................####", "###.................####",
               "###.................####", "###.................####",
               "###.................####", "####................####",
               "####...............#####", "#########......#########",
               "##......#......#.....###", "##......########......##",
               "#....#............#....#", "#....#............#....#",
               "#.#.................##.#", "..#..###........###..#..",
               ".....###........###.....", "..#..####....##.###.##..",
               "..#..##..##..###.##..#..", "....#...#......#..##....",
               ".##.....#.#..#.#.....###", ".##.......#..#.......##.",
               ".##.......#..#.......##.", ".##.....#......#.....##."]}
# The recorded garrison's starts (f1..f9: Overseer, two Warriors, Infernal Guard, two
# Blunderbusses, Fireglaives, Bull Centaurs, Magma Cannon), given to the Cathay roster in order.
STARTS = [(140, -21), (-20, -23.200000762939), (-104.80000305176, -38.799999237061),
          (-256.60000610352, -109), (-55.200000762939, -23.200000762939),
          (-85.599998474121, -21.39999961853), (-276.60000610352, -123.19999694824),
          (-3, -1.7000000476837), (-0.60000002384186, 85.199996948242), (0, 300)]
GARRISON = ["wh3_main_cth_cha_lord_magistrate_0", "wh3_main_cth_inf_jade_warriors_0",
            "wh3_main_cth_inf_jade_warriors_0", "wh3_main_cth_inf_peasant_spearmen_1",
            "wh3_main_cth_inf_peasant_archers_0", "wh3_main_cth_inf_peasant_archers_0",
            "wh3_main_cth_inf_jade_warrior_crossbowmen_0", "wh3_main_cth_inf_peasant_spearmen_1",
            "wh3_main_cth_art_grand_cannon_0", "wh3_main_cth_art_fire_rain_rocket_battery_0"]
MISSILE = {"wh3_main_cth_inf_peasant_archers_0", "wh3_main_cth_inf_jade_warrior_crossbowmen_0",
           "wh3_main_cth_art_grand_cannon_0", "wh3_main_cth_art_fire_rain_rocket_battery_0"}


def garrison(ids=None):
    """Friendly unit records in the recorded shape (``unit_record`` fields a script reads)."""
    ids = ids or [f"f{index}" for index in range(1, len(GARRISON) + 1)]
    units = []
    for identity, kind, (x, z) in zip(ids, GARRISON, STARTS, strict=True):
        missile = kind in MISSILE
        units.append({
            "id": identity, "type": kind, "class": "missile" if missile else "infantry",
            "x": x, "z": z, "bearing": 183, "men": 90, "men0": 90, "hp": 1, "state": ["idle"],
            "ammo": 22 if missile else 0, "ammo0": 22 if missile else 0,
            "range": 140 if missile else 0,
            "behaviours": {"defend": True, **({"fire_at_will": True, "skirmish": False}
                                              if missile else {})}})
    return units


def first_observation(job="bench-cths-a-hold-20261108"):
    """Helmgart's first observation for cth-emp-siege-a-v1, mailbox-shaped: the public part as
    recorded (see the module docstring), no enemy visible, the scenario's enemy roster, and
    hidden sections that hold the waves profile and its evidence."""
    roster = [{"id": f"e{index}", "type": kind}
              for index, kind in enumerate(SCENARIO["enemy"]["units"], 1)]
    profile = deepcopy(SCENARIO["reserve"])
    return {
        "schema": 1, "job": job, "battle": "1792135808-1142.2449951172", "seq": 1,
        "phase": "Deployed", "time_ms": 5200, "speed": 1, "awaiting_orders": False,
        "remaining_ms": 1199600,
        "armies": {"player": {"faction": "wh3_main_cth_cathay_mp"},
                   "enemy": {"faction": "wh_main_emp_empire"}},
        "friendly": garrison(), "enemy_roster": roster, "enemy": [],
        "magic": {"current": 12, "reserve": 68}, "mode": deepcopy(MODE),
        "terrain": deepcopy(TERRAIN), "orders": None, "result": None,
        "evaluation": {"version": 2, "reserve": {"config": profile, "units": [], "releases": []}},
        "setup": {"reserve": {"ok": True}, "private_note": "staging pocket"},
    }
