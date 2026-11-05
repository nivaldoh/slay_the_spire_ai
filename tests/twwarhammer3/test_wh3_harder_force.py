"""A and C v2 change only the four front enemy regiments; no live game or difficulty claim.

Reference: the owner's 2026-11-05 choice to give A and C emp-envelopment-b-v3's four front
Greatswords (docs/owner-direction.md). B3 also moved two rear regiments for its reserve; v2
must not.
"""

import pytest

from twwarhammer3.battle import local_team, setup

GREATSWORDS, SWORDSMEN = "wh_main_emp_inf_greatswords", "wh_main_emp_inf_swordsmen"


def test_a_v2_is_a_v1_with_only_the_four_front_regiments_changed():
    old, new = (setup.scenarios()[f"emp-envelopment-a-v{version}"] for version in (1, 2))
    changed = {key for key in {*old, *new} if old.get(key) != new.get(key)}
    assert changed == {"name", "scenario_version", "enemy", "deployment", "calibration_change"}
    assert new["deployment"]["friendly"] == old["deployment"]["friendly"]
    assert {k: v for k, v in new["enemy"].items() if k != "units"} == {
        k: v for k, v in old["enemy"].items() if k != "units"}
    types = [placement["type"] for placement in new["deployment"]["enemy"]]
    assert types[:4] == [GREATSWORDS] * 4 and SWORDSMEN not in types[:4]
    assert types == new["enemy"]["units"]
    places = [{k: v for k, v in placement.items() if k != "type"}
              for placement in new["deployment"]["enemy"]]
    assert places == [{k: v for k, v in placement.items() if k != "type"}
                      for placement in old["deployment"]["enemy"]]
    assert "reserve" not in new


@pytest.mark.parametrize("suffix, arm", [("", "bounded"), ("-silent", "silent"), ("-fast", "fast"),
                                         ("-global", "global")])
def test_each_c_arm_keeps_its_channel_rules_on_the_harder_force(suffix, arm):
    all_scenarios = setup.scenarios()
    old, new = (all_scenarios[f"emp-envelopment-c{suffix}-v{version}"] for version in (1, 2))
    assert new["communication"] == old["communication"] == {"version": 1, "arm": arm}
    assert new["enemy"] == all_scenarios["emp-envelopment-a-v2"]["enemy"]
    assert new["deployment"] == all_scenarios["emp-envelopment-a-v2"]["deployment"]
    assert new["family"] == old["family"] and local_team.declaration(new) == arm
