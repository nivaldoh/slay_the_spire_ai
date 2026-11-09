"""A first observation of the siege attack ksl-emp-siege-a-v1 on Helmgart, for offline tests.

``mode``'s capture points, gate, tickets, role and timeout winner are copied (values unchanged)
from the first observation with units, at 5.3 s, of
runs/twwarhammer3/battle/smoke-siege-attack-kho5-dwf5-probe_abilities-20261014-0830/episode-0000/
trace.jsonl, the only recorded siege the player attacked; ``objectives`` is a placeholder (the
game's text is not copied). ``SLOTS`` holds that battle's slot rows at 59.9 s and 200.3 s, the
attacker's list of the defender's eight tower slots, copied unchanged; ``mode`` has no slots,
since the opt-in leaves them out. Not recorded, because no battle has read them: the
fortification pieces (a sketch along the wall that final-izmail.md, Map and starts, draws
through the four Fort Tower points and the gate, each tower's owner its point's holder), the
vehicle and its crew, the Kislev roster's starts, ranges and ammunition, and the three visible
defenders. These carry the roster's types for their ids (e2 Halberdiers, e5 and e6 Handgunners)
and stand at (-49, -21), (164, -73) and (212, -73), where defenders stood on the wall in the
2026-11-03 Helmgart checkpoint reading (runs/twwarhammer3/siege-905-20261103); that battle's unit
types are not copied.
"""

from copy import deepcopy

from twwarhammer3.battle.setup import scenarios

SCENARIO = scenarios()["ksl-emp-siege-a-v1"]
POINTS = [
    {"contested": False, "holder": "enemy", "id": "c1", "key": "major_key_building_leadership",
     "locked": False, "name": "Key Building", "percent": 100, "victory": True, "x": 0, "z": 310},
    {"contested": False, "holder": "enemy", "id": "c2", "key": "capture_point_gate_only",
     "locked": False, "name": "Gatehouse", "percent": 100, "victory": False, "x": -2, "z": -22.5},
    {"contested": False, "id": "c3", "key": "capture_point_tower_only", "locked": False,
     "name": "Fort Tower", "percent": 100, "victory": False, "x": 188, "z": -81},
    {"contested": False, "id": "c4", "key": "capture_point_tower_only", "locked": False,
     "name": "Fort Tower", "percent": 100, "victory": False, "x": 58, "z": -31},
    {"contested": False, "id": "c5", "key": "capture_point_tower_only", "locked": False,
     "name": "Fort Tower", "percent": 100, "victory": False, "x": -62, "z": -31},
    {"contested": False, "holder": "enemy", "id": "c6", "key": "capture_point_tower_only",
     "locked": False, "name": "Fort Tower", "percent": 100, "victory": False, "x": -192,
     "z": -81},
    {"contested": False, "holder": "enemy", "id": "c7", "key": "minor_point_supplies",
     "locked": False, "name": "Minor Supply Location", "percent": 100, "victory": True, "x": -1,
     "z": 155},
    {"contested": False, "holder": "enemy", "id": "c8", "key": "minor_point_supplies",
     "locked": False, "name": "Minor Supply Location", "percent": 100, "victory": True,
     "x": -320, "z": 320},
    {"contested": False, "holder": "enemy", "id": "c9", "key": "minor_point_supplies",
     "locked": False, "name": "Minor Supply Location", "percent": 100, "victory": True, "x": 320,
     "z": 320}]
WALLS = [(-330, -100), (-250, -95), (-190, -88), (-120, -55), (-75, -28), (5, -20), (75, -30),
         (130, -60), (190, -88), (250, -95), (330, -100)]
TOWERS = [(-192, -81), (-62, -31), (58, -31), (188, -81)]
FORTIFICATIONS = (
    [{"id": "g1", "kind": "gate", "x": -32, "z": -16, "hp": 100}]
    + [{"id": f"w{index}", "kind": "wall", "x": x, "z": z, "hp": 100}
       for index, (x, z) in enumerate(WALLS, 1)]
    + [{"id": f"t{index}", "kind": "tower", "x": x, "z": z, "hp": 100,
        "owner": "enemy" if index == 1 else "none"}
       for index, (x, z) in enumerate(TOWERS, 1)])
MODE = {
    "type": "settlement_standard", "role": "attacker", "timeout_winner": "enemy",
    "objectives": "Objectives: (placeholder for the engine's siege objective text)",
    "capture_points": POINTS,
    "gates": [{"destroyed": False, "hp": 100, "name": "Gatehouse", "x": -32, "z": -16}],
    "tickets": [{"per_s": 5, "score": 0, "side": "enemy", "tickets": 1000}],
    "fortifications": FORTIFICATIONS,
    "vehicles": [{"id": "v1", "category": "battering_ram", "x": 0, "z": -231, "crew": "f4"}],
    "enemy_structures": [],
}
SLOTS = {
    59900: [
        {"id": "s1", "type": "tower", "usable": False, "x": 55.200000762939, "z": 191.69999694824},
        {"id": "s2", "type": "tower", "usable": False, "x": -56.200000762939, "z": 191.69999694824},
        {"id": "s3", "type": "tower", "usable": False, "x": -111, "z": 352.89999389648},
        {"id": "s4", "type": "tower", "usable": False, "x": 110, "z": 353},
        {"id": "s5", "type": "tower", "usable": False, "x": 289, "z": 187, "options": []},
        {"id": "s6", "type": "tower", "usable": False,
         "x": -299, "z": 191, "building_s": 69.300003051758},
        {"id": "s7", "type": "tower", "usable": False,
         "x": 127.69999694824, "z": 96.900001525879, "options": []},
        {"id": "s8", "type": "tower", "usable": False, "x": -131.19999694824, "z": 96.800003051758},
    ],
    200300: [
        {"id": "s1", "type": "tower", "usable": False, "x": 55.200000762939, "z": 191.69999694824},
        {"id": "s2", "type": "tower", "usable": False, "x": -56.200000762939, "z": 191.69999694824},
        {"id": "s3", "type": "tower", "usable": False, "x": -111, "z": 352.89999389648},
        {"id": "s4", "type": "tower", "usable": False, "x": 110, "z": 353},
        {"id": "s5", "type": "tower", "usable": False,
         "x": 289, "z": 187, "building_s": 40.299999237061},
        {"id": "s6", "type": "tower", "usable": False, "x": -299, "z": 191},
        {"id": "s7", "type": "tower", "usable": False, "x": 127.69999694824, "z": 96.900001525879},
        {"id": "s8", "type": "tower", "usable": False, "x": -131.19999694824, "z": 96.800003051758},
    ],
}
# (type, x, z, men, ammo, range, can_climb, can_siege), f1..f13 in roster order.
ROSTER = [
    ("wh3_main_ksl_cha_boyar_0", 0, -260, 1, 0, 0, True, False),
    *[("wh3_main_ksl_inf_armoured_kossars_0", x, -230, 75, 6, 35, True, False)
      for x in (-200, -100, 0, 100, 200)],
    *[("wh3_main_ksl_inf_kossars_1", x, -215, 67, 20, 150, True, False) for x in (-150, 20, 150)],
    *[("wh3_main_ksl_inf_streltsi_0", x, -240, 67, 20, 160, True, False) for x in (-60, 60)],
    ("wh3_main_ksl_cav_winged_lancers_0", 0, -300, 45, 0, 0, False, False),
    ("wh3_main_ksl_veh_little_grom_0", -20, -270, 2, 22, 300, False, True),
]
DEFENDERS = [("e2", "wh_main_emp_inf_halberdiers", -49, -21),
             ("e5", "wh_main_emp_inf_handgunners", 164, -73),
             ("e6", "wh_main_emp_inf_handgunners", 212, -73)]


def army(ids=None):
    """Own unit records (the fields a script reads), ids f1..f13 unless ``ids`` gives them."""
    ids = ids or [f"f{index}" for index in range(1, len(ROSTER) + 1)]
    return [{"id": identity, "type": kind, "class": "infantry", "x": float(x), "z": float(z),
             "bearing": 0, "men": men, "men0": men, "hp": 1.0, "state": ["idle"], "ammo": ammo,
             "ammo0": ammo, "range": reach, "on_wall": False, "can_climb": climb,
             "can_siege": siege}
            for identity, (kind, x, z, men, ammo, reach, climb, siege) in zip(ids, ROSTER,
                                                                               strict=True)]


def first_observation(job="bench-ksl-a-hold-20261108", ids=None):
    """The mailbox-shaped first observation (module docstring): hidden sections included."""
    friendly = army(ids)
    mode = deepcopy(MODE)
    mode["vehicles"][0]["crew"] = friendly[3]["id"]  # the Armoured Kossars at x 0
    return {
        "schema": 1, "job": job, "battle": "1792200000-1.5", "seq": 1, "phase": "Deployed",
        "time_ms": 5300, "speed": 1, "awaiting_orders": False, "remaining_ms": 1194700,
        "armies": {"player": {"faction": "wh3_main_ksl_kislev"},
                   "enemy": {"faction": "wh_main_emp_empire"}},
        "friendly": friendly,
        "enemy_roster": [{"id": f"e{index}", "type": kind}
                         for index, kind in enumerate(SCENARIO["enemy"]["units"], 1)],
        "enemy": [{"id": identity, "type": kind, "class": "infantry", "x": float(x),
                   "z": float(z), "bearing": 180, "men": 67, "men0": 67, "hp": 1.0,
                   "state": ["idle"], "range": 0, "on_wall": True}
                  for identity, kind, x, z in DEFENDERS],
        "magic": {}, "mode": mode, "orders": None, "result": None,
        "evaluation": {"version": 2, "private_note": "hidden garrison strength"},
        "setup": {"siege_assault": {"ok": True, "lists": {"gate": 1, "wall": 12, "tower": 4}},
                  "private_note": "staging pocket"},
    }


def later(observation, time_ms, **changes):
    """A copy at ``time_ms``: ``changes`` maps a unit id to fields to set on it (own or visible
    enemy), and ``mode`` to fields to set on mode."""
    state = deepcopy(observation)
    state["time_ms"], state["seq"] = time_ms, state["seq"] + 1
    state["remaining_ms"] = 1200000 - time_ms
    state["mode"].update(changes.pop("mode", {}))
    units = {unit["id"]: unit for unit in state["friendly"] + state["enemy"]}
    for identity, fields in changes.items():
        units[identity].update(fields)
    return state
