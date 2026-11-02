"""The owner's latest roster/role confirmation, and readable AI gun settings."""
from collections import Counter
from copy import deepcopy

import pytest

from twwarhammer3.battle import benchmark, setup
from twwarhammer3.protocol import ProtocolError

CANNON = "wh_main_emp_art_great_cannon"
SWORD = "wh_main_emp_inf_swordsmen"


def test_confirmed_armies_and_enemy_attack_are_explicit():
    profile = setup.scenarios()[benchmark.SCENARIO]
    # Owner, 2026-11-02: "add 2 swordsmen to the enemy side" after version4.
    assert Counter(profile["enemy"]["units"]) == {SWORD: 6, CANNON: 1}
    assert profile["attacker"] == "enemy" and profile["expect"]["player_defends"] is True
    assert Counter(profile["player"]["units"]) == {
        SWORD: 3, "wh_main_emp_inf_crossbowmen": 1, "wh_main_emp_cav_empire_knights": 1}


def test_enemy_cannon_fire_choice_is_free_but_its_readback_is_required():
    profile = setup.scenarios()[benchmark.SCENARIO]
    state = {"setup": {"unit_scale": .75, "realism": False, "player_defends": True,
                       "army_ai_stats_modifiers": [1, 1], "unit_experience": {},
                       "benchmark_behaviours": {}}, "terrain": {"rows": ["...."]},
             "armies": {side: {"faction": army["faction"]}
                        for side, army in (("player", profile["player"]),
                                           ("enemy", profile["enemy"]))}}
    gun_id = None
    for side, army, prefix in (("friendly", profile["player"], "f"),
                               ("enemy", profile["enemy"], "e")):
        roster = [{"id": f"{prefix}{i}", "type": key}
                  for i, key in enumerate(army["units"], 1)]
        state["friendly" if side == "friendly" else "enemy_roster"] = roster
        state["setup"]["unit_experience"][side] = [{"type": u["type"], "rank": 0} for u in roster]
        toggles = state["setup"]["benchmark_behaviours"][side] = {}
        for unit in roster:
            flags = {"defend": False}
            if "crossbowmen" in unit["type"]:
                flags.update(fire_at_will=True, skirmish=False)
            if unit["type"] == CANNON:
                flags["fire_at_will"] = False  # a valid AI choice; do not force it on
                gun_id = unit["id"]
            toggles[unit["id"]] = {"supported": list(flags), **flags}
    actual = setup.check_battle(profile, state)
    assert actual["benchmark_behaviours"]["enemy"][gun_id]["fire_at_will"] is False
    assert "skirmish" not in actual["benchmark_behaviours"]["enemy"][gun_id]
    missing = deepcopy(state)
    del missing["setup"]["benchmark_behaviours"]["enemy"][gun_id]["fire_at_will"]
    missing["setup"]["benchmark_behaviours"]["enemy"][gun_id]["supported"] = ["defend"]
    with pytest.raises(ProtocolError, match="fire_at_will"):
        setup.check_battle(profile, missing)
