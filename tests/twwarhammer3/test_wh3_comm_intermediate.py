"""Intermediate-force declaration from communication-structure.md's development card.

Rests on JUDGEMENT docs/twwarhammer3/communication-structure.md Intermediate C force.

The independent change is enemy authored slots 0 and 3: Greatswords to Swordsmen.
All other physical fields and the existing local-command interface must be retained.
These checks cannot establish live placement, winnability or a communication benefit.
"""

from copy import deepcopy

import pytest

from twwarhammer3.battle import configured, local_team, setup

ARMS = ("peer", "relay", "overview", "muted", "muted-overview", "silent")
BASE = "emp-envelopment-c-mid-v3"


def test_intermediate_force_changes_only_the_two_outer_enemy_front_regiments():
    scenarios = setup.scenarios()
    old, actual = scenarios["emp-envelopment-a-v2"], scenarios[BASE]
    expected = deepcopy(old)
    expected.update(name=BASE, scenario_version=3, family="limited_command",
                    calibration_change=actual["calibration_change"])
    assert old["enemy"]["units"][:4] == ["wh_main_emp_inf_greatswords"] * 4
    for slot in (0, 3):
        expected["enemy"]["units"][slot] = "wh_main_emp_inf_swordsmen"
        expected["deployment"]["enemy"][slot]["type"] = "wh_main_emp_inf_swordsmen"
    assert actual == expected


@pytest.mark.parametrize("arm", ARMS)
def test_every_arm_retains_one_physical_setup_and_passes_normal_declaration_checks(arm):
    scenarios = setup.scenarios()
    scenario = scenarios[f"emp-envelopment-c-mid-{arm}-v3"]
    expected = {**scenarios[BASE], "name": scenario["name"],
                "communication": {"version": 1 if arm == "silent" else 2,
                                  "arm": arm.replace("-", "_")}}
    assert scenario == expected
    config = {"start_timeout": 600, "episode_timeout": 1320, "run_timeout": 2000, "episodes": 1}
    setup.validate_declaration(scenario, config)
    assert local_team.declaration(scenario) == arm.replace("-", "_")


@pytest.mark.parametrize("arm, controller", [
    ("peer", "peer-witness"), ("relay", "relay-witness"), ("overview", "overview-witness"),
    ("muted", "muted-witness"), ("muted-overview", "muted-overview-witness"),
    ("silent", "local-rush-think"), ("silent", "local-concentrate"),
])
def test_screen_controllers_load_on_their_declared_arm(arm, controller):
    name = f"emp-envelopment-c-mid-{arm}-v3"
    path = setup.SCENARIOS_PATH.parent / "controllers" / f"cannae-{controller}.json"
    config = {"policy": "configured", "controller_config": str(path), "scenario": name}
    frozen = configured.load(path, config)[0]
    assert set(frozen["members"]) == local_team.member_names(arm.replace("-", "_"))
    local_team.validate_config(setup.scenarios()[name], config)
