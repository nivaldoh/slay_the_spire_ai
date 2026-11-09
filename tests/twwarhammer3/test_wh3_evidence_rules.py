"""Evidence rules on records copied from recorded traces (fields trimmed, values unchanged).

Sources, all under runs/twwarhammer3/battle/ or runs/coord-suite-20261104/:
- HELMGART: bench-b12-siege-baselines-20261016/episode-0001/trace.jsonl, Chaos Dwarfs defend
  Helmgart against Greenskins (hold baseline, lost at 708.7 s).
- GAEAN: smoke-random-siege-skills-20261014-0511/episode-0000/trace.jsonl (siege defence).
- ATTACK: smoke-siege-attack-kho5-dwf5-probe_abilities-20261014-0830/episode-0000/trace.jsonl
  (siege attack; 0 melee flags in 777 unit-bearing records).
- BREAKOUT: round-1a/coord-breakout--rush--1 (manifest.json scenario version 1, episode-0000
  trace.jsonl and replay.jsonl).
"""

import pytest

from twwarhammer3.battle import evidence_rules as rules
from twwarhammer3.protocol import ProtocolError


def frame(friendly, enemy):
    return {"friendly": friendly, "enemy": enemy}


# ATTACK at 714.5 s: the closest friendly-enemy pair of the battle, 10.1 m apart, neither flagged.
ATTACK_714 = frame(
    [{"id": "f3", "type": "wh3_main_kho_inf_chaos_warriors_0", "class": "infantry",
      "x": -234.10000610352, "z": -81.300003051758, "men": 29, "state": ["idle"]}],
    [{"id": "e5", "type": "wh_main_dwf_art_grudge_thrower", "class": "artillery",
      "x": -232, "z": -71.400001525879, "men": 24, "state": ["moving", "running"]}])
# HELMGART at 246.4 s: f3 fights at full strength; 15 of 16 enemies are visible, the nearest
# (e14, also in melee) 41.8 m away and the next (e10) 50.7 m. The other 13 are farther.
HELMGART_246 = frame(
    [{"id": "f3", "type": "wh3_dlc23_chd_inf_chaos_dwarf_warriors", "class": "infantry",
      "x": -104.80000305176, "z": -38.799999237061, "men": 75, "state": ["melee", "idle"]}],
    [{"id": "e10", "type": "wh_main_grn_inf_orc_big_uns", "class": "infantry",
      "x": -149.89999389648, "z": -61.900001525879, "men": 26, "state": ["moving", "running"]},
     {"id": "e14", "type": "wh_main_grn_inf_orc_arrer_boyz", "class": "missile",
      "x": -141.39999389648, "z": -59, "men": 68, "state": ["melee"]}])
# HELMGART at 333.1 s: f6 and e4 stand 1.7 m apart and neither is flagged; e3, 1.8 m from f6, is.
HELMGART_333 = frame(
    [{"id": "f6", "type": "wh3_dlc23_chd_inf_chaos_dwarf_blunderbusses", "class": "missile",
      "x": -85.199996948242, "z": -21.5, "men": 60, "state": ["idle"]}],
    [{"id": "e3", "type": "wh_main_grn_inf_goblin_spearmen", "class": "infantry",
      "x": -86.900001525879, "z": -20.89999961853, "men": 39,
      "state": ["routing", "melee", "moving", "running"]},
     {"id": "e4", "type": "wh_main_grn_inf_goblin_spearmen", "class": "infantry",
      "x": -85.699996948242, "z": -19.89999961853, "men": 4,
      "state": ["routing", "shattered", "moving", "running"]}])
# HELMGART at 703.9 s: the whole friendly army, the enemy e5 and the nearest enemies of f3 (e12,
# 33.9 m) and f9 (e8, 29.1 m). The Magma Cannon f9 has had no men since 413.8 s and still reads
# melee. e5 reads melee 167.7 m from f1, the nearest friendly.
HELMGART_704 = frame(
    [{"id": uid, "x": x, "z": z, "men": men, "state": state} for uid, x, z, men, state in [
        ("f1", 198.89999389648, 356.70001220703, 1, ["routing", "shattered", "moving", "running"]),
        ("f2", -24.89999961853, -23.200000762939, 54, ["under_fire", "idle"]),
        ("f3", -104.80000305176, -38.799999237061, 45, ["melee", "idle"]),
        ("f4", -256.60000610352, -116.19999694824, 39, ["idle"]),
        ("f5", -53.400001525879, -23.200000762939, 50, ["under_fire", "idle"]),
        ("f6", -85.599998474121, -21.39999961853, 60, ["idle"]),
        ("f7", -276.79998779297, -124.69999694824, 40, ["idle"]),
        ("f8", -337.60000610352, 76.199996948242, 3, ["wavering", "idle"]),
        ("f9", -13.60000038147, 100.5, 0, ["routing", "shattered", "melee"])]],
    [{"id": uid, "x": x, "z": z, "men": men, "state": state} for uid, x, z, men, state in [
        ("e5", 255.10000610352, 198.69999694824, 16, ["melee", "moving", "running"]),
        ("e8", -10.699999809265, 71.5, 89, ["moving", "running"]),
        ("e12", -93.199996948242, -6.9000000953674, 58, ["moving", "running"])]])


def test_contact_is_the_engines_melee_flag_never_centre_distance():
    # A distance rule fails one of these: at 1.7 m or more it puts an unflagged pair in contact,
    # under 41.8 m it misses the Helmgart fight at 246.4 s. The flag counts only on its own unit,
    # never on a neighbour (e3 and f6). The flag plus a distance under 167.7 m drops e5.
    assert rules.in_melee(ATTACK_714) == set()
    assert rules.in_melee(HELMGART_333) == {"e3"}
    assert rules.in_melee(HELMGART_246) == {"f3", "e14"}
    assert "e5" in rules.in_melee(HELMGART_704)


def test_a_unit_with_no_men_left_is_not_in_contact_although_it_keeps_the_flag():
    assert rules.in_melee(HELMGART_704) == {"f3", "e5"}


def gate(hp, x=-32, z=-16):
    return {"destroyed": False, "hp": hp, "name": "Gatehouse", "x": x, "z": z}


def test_a_gate_is_breached_at_public_hp_zero_although_it_never_reads_destroyed():
    # HELMGART: hp 1 at 251.2 s, 0 at 258.4 s and at the result (708.7 s), destroyed false.
    assert [rules.gate_breached(gate(hp)) for hp in (1, 0, 0)] == [False, True, True]
    # GAEAN: four gates share the name; (503,-94) read hp 3 at 174.4 s and 0 from 179.5 s.
    gaean = [gate(100, -142, 454), gate(99, -142, 214), gate(0, 503, -94), gate(100, 263, -94)]
    assert [(g["x"], g["z"]) for g in gaean if rules.gate_breached(g)] == [(503, -94)]
    gaean[2]["hp"] = 3
    assert not any(rules.gate_breached(g) for g in gaean)
    # A gate whose maximum is unreadable has no hp, and it is not breached.
    assert not rules.gate_breached({"name": "Gatehouse", "x": -32, "z": -16, "destroyed": False})


def tickets(role, side, count, per_s, score):
    return {"role": role, "tickets": [{"per_s": per_s, "score": score, "side": side,
                                       "tickets": count}]}


def test_tickets_come_from_the_defenders_row_in_either_role():
    # HELMGART, we defend: 1000 at 699.1 s, when c1 turned enemy, and 990 at 700.3 s.
    assert rules.defender_tickets(tickets("defender", "us", 1000, 0, 4462)) == 1000
    assert rules.defender_tickets(tickets("defender", "us", 990, 0, 4462)) == 990
    # ATTACK at 5.3 s, we attack: the only row is the enemy's.
    assert rules.defender_tickets(tickets("attacker", "enemy", 1000, 5, 0)) == 1000


# HELMGART capture points (id, key, holder; a neutral point has no holder key).
def points(holders):
    keys = ["major_key_building_leadership", "capture_point_gate_only"] + [
        "capture_point_tower_only"] * 4 + ["minor_point_supplies"] * 3
    return [{"id": f"c{i}", "key": key, **({"holder": holders[i - 1]} if holders[i - 1] else {})}
            for i, key in enumerate(keys, 1)]


def test_a_neutral_capture_point_is_held_by_neither_side():
    start = points(["us", "us", None, None, "us", None, "us", "us", "us"])  # 5.2 s
    gatehouse = points(["us", "enemy", None, None, "us", None, "us", "us", "us"])  # 336.7 s
    key = points(["enemy", "enemy", None, None, "us", None, "enemy", "enemy", "enemy"])  # 699.1 s

    def held(state, side):
        return [p["id"] for p in state if rules.holds(p, side)]
    assert held(start, "enemy") == []
    assert held(start, "us") == ["c1", "c2", "c5", "c7", "c8", "c9"]
    assert held(gatehouse, "enemy") == ["c2"]
    assert held(key, "enemy") == ["c1", "c2", "c7", "c8", "c9"]


# BREAKOUT version 1 enemy placements (manifest.json): slots 1-2 west, 3-4 east, 5-7 south.
BREAKOUT = {"deployment": {"enemy": [
    {"type": "wh_main_grn_inf_goblin_spearmen", "x": -60, "z": -257, "bearing": 90, "width": 40},
    {"type": "wh_main_grn_inf_orc_boyz", "x": -60, "z": -303, "bearing": 90, "width": 40},
    {"type": "wh_main_grn_inf_orc_boyz", "x": 360, "z": -303, "bearing": 270, "width": 40},
    {"type": "wh_main_grn_inf_goblin_spearmen", "x": 360, "z": -257, "bearing": 270, "width": 40},
    {"type": "wh_main_grn_inf_orc_arrer_boyz", "x": 104, "z": -475, "bearing": 0, "width": 40},
    {"type": "wh_main_grn_inf_orc_boyz", "x": 150, "z": -475, "bearing": 0, "width": 40},
    {"type": "wh_main_grn_inf_goblin_spearmen", "x": 196, "z": -475, "bearing": 0, "width": 40},
]}}
SPEAR, BOYZ, ARRER = ("wh_main_grn_inf_goblin_spearmen", "wh_main_grn_inf_orc_boyz",
                      "wh_main_grn_inf_orc_arrer_boyz")
# BREAKOUT trace at 5.2 s, the only record with the private reading (engine ids, not slot order).
BREAKOUT_FIRST = {"setup": {"deployment_reading": {"enemy": [
    {"id": "e1", "type": SPEAR, "x": -63.799999237061, "z": -257.20001220703},
    {"id": "e2", "type": SPEAR, "x": 363.70001220703, "z": -257.10000610352},
    {"id": "e3", "type": SPEAR, "x": 196.19999694824, "z": -477.89999389648},
    {"id": "e4", "type": BOYZ, "x": -64.300003051758, "z": -302.70001220703},
    {"id": "e5", "type": BOYZ, "x": 365, "z": -302.70001220703},
    {"id": "e6", "type": BOYZ, "x": 149.69999694824, "z": -480.10000610352},
    {"id": "e7", "type": ARRER, "x": 104, "z": -479.79998779297}]}}}
# BREAKOUT replay at 94 s: the east spearmen e2 has run to x 180, beside the south group.
BREAKOUT_94 = {"recorder": 1, "time_ms": 94000, "enemy": [
    {"id": "e1", "type": SPEAR, "x": -37.900001525879, "z": -248.30000305176, "state": ["melee"]},
    {"id": "e2", "type": SPEAR, "x": 180.19999694824, "z": -246,
     "state": ["under_fire", "moving", "running"]},
    {"id": "e3", "type": SPEAR, "x": 128.30000305176, "z": -269.60000610352,
     "state": ["melee", "under_fire"]},
    {"id": "e4", "type": BOYZ, "x": 28.89999961853, "z": -269.70001220703,
     "state": ["moving", "running"]},
    {"id": "e5", "type": BOYZ, "x": 268, "z": -253.30000305176, "state": ["moving", "running"]},
    {"id": "e6", "type": BOYZ, "x": 114.30000305176, "z": -326.79998779297,
     "state": ["moving", "running"]},
    {"id": "e7", "type": ARRER, "x": 111.09999847412, "z": -408.5, "state": []}]}
GROUPS = {"west": [1, 2], "east": [3, 4], "south": [5, 6, 7]}


def test_groups_are_bound_by_the_private_first_reading_and_never_regrouped_later():
    assert rules.group_ids(BREAKOUT, BREAKOUT_FIRST, "enemy", GROUPS) == {
        "west": ["e1", "e4"], "east": ["e5", "e2"], "south": ["e7", "e6", "e3"]}
    # A later frame has no private reading; grouping it by position would put e2 in the south.
    with pytest.raises(ProtocolError, match="unread for enemy"):
        rules.group_ids(BREAKOUT, BREAKOUT_94, "enemy", GROUPS)


def test_units_are_selected_by_type_key_because_classes_mislead():
    # HELMGART at 5.2 s, the whole friendly army as the engine classes it.
    army = [{"id": f"f{i}", "type": key, "class": cls} for i, (key, cls) in enumerate([
        ("wh3_dlc23_chd_cha_overseer", "lord"),
        ("wh3_dlc23_chd_inf_chaos_dwarf_warriors", "infantry"),
        ("wh3_dlc23_chd_inf_chaos_dwarf_warriors", "infantry"),
        ("wh3_dlc23_chd_inf_infernal_guard", "infantry"),
        ("wh3_dlc23_chd_inf_chaos_dwarf_blunderbusses", "missile"),
        ("wh3_dlc23_chd_inf_chaos_dwarf_blunderbusses", "missile"),
        ("wh3_dlc23_chd_inf_infernal_guard_fireglaives", "missile"),
        ("wh3_dlc23_chd_cav_bull_centaurs_axe", "infantry"),
        ("wh3_dlc23_chd_veh_magma_cannon", "missile_chariot")], 1)]
    assert rules.ids_by_type(army, {"wh3_dlc23_chd_veh_magma_cannon"}) == ["f9"]
    assert rules.ids_by_type(army, {"wh3_dlc23_chd_cav_bull_centaurs_axe"}) == ["f8"]
