"""The Massed horse draft (emp-wing-horse-*-v1): its entries pass C's pre-launch refusals.

Reference: the 2026-11-08 design ("Massed horse" and "Late horse" in
runs/comm-build-20261108/battles-research.json) and docs/twwarhammer3/communication-structure.md
"Massed horse variant". Each draw is C v2's battle with the friendly Knights moved and both enemy
Knights on one wing; the arms reuse C's groups and controller files. Offline only: none of this
shows a placement in the engine, which regiment the native AI attacks, a timing or a win.
"""

import pytest

from twwarhammer3.battle import configured, local_team, setup
from twwarhammer3.battle import local_command as local

DRAWS = ("south", "north", "south-far")
ARMS = (("silent", 1), ("peer", 2), ("muted", 2))
KNIGHTS = "wh_main_emp_cav_empire_knights"
CONTROLLERS = setup.SCENARIOS_PATH.parent / "controllers"
# The C cards' limits (start 600 s, episode 1,320 s, job 2,000 s).
C_LIMITS = {"start_timeout": 600, "episodes": 1, "episode_timeout": 1320, "run_timeout": 2000}


def battle(draw, arm=None):
    return setup.scenarios()[f"emp-wing-horse-{draw}{f'-{arm}' if arm else ''}-v1"]


def test_the_draws_differ_from_each_other_only_in_the_enemy_knights_start_points():
    """Wrong versions: a north or far override that drops the friendly placements, a draw with
    a moved or retyped enemy infantry regiment (the draw would show through more than the horse),
    or a roster that is not A v2's."""
    a_v2 = setup.scenarios()["emp-envelopment-a-v2"]
    draws = [battle(draw) for draw in DRAWS]
    for scenario in draws:
        assert scenario["player"] == a_v2["player"] and scenario["enemy"] == a_v2["enemy"]
        friendly, enemy = scenario["deployment"]["friendly"], scenario["deployment"]["enemy"]
        assert friendly[:6] == a_v2["deployment"]["friendly"][:6]
        assert enemy[:8] == a_v2["deployment"]["enemy"][:8]
        assert [p["type"] for p in enemy[8:]] == [KNIGHTS, KNIGHTS]
    for scenario in draws[1:]:
        changed = {key for key in {*draws[0], *scenario} if draws[0].get(key) != scenario.get(key)}
        assert changed == {"name", "calibration_change", "deployment"}
        assert scenario["deployment"]["friendly"] == draws[0]["deployment"]["friendly"]
        assert scenario["deployment"]["enemy"][:8] == draws[0]["deployment"]["enemy"][:8]
        assert scenario["deployment"]["enemy"][8:] != draws[0]["deployment"]["enemy"][8:]


@pytest.mark.parametrize("draw", DRAWS)
@pytest.mark.parametrize("arm, version", ARMS)
def test_each_arm_passes_setup_its_declaration_and_binds_the_five_groups(draw, arm, version):
    """Wrong versions: an arm that changes more than C's family and communication fields, a
    declaration the C limits refuse, or placements the 25 m bind cannot tell apart."""
    scenario = battle(draw, arm)
    physical = battle(draw)
    assert {k: v for k, v in scenario.items() if k not in ("name", "family", "communication")} == {
        k: v for k, v in physical.items() if k not in ("name", "family")}
    assert scenario["family"] == "limited_command"
    assert scenario["communication"] == {"version": version, "arm": arm}
    config = dict(C_LIMITS)
    setup.fill_timeouts(scenario, config)
    setup.validate_declaration(scenario, config)
    assert config == C_LIMITS
    assert local_team.declaration(scenario) == arm
    placements = scenario["deployment"]["friendly"]
    rows = [{"id": f"f{i + 1}", "type": p["type"], "x": p["x"] + 3, "z": p["z"] - 4}
            for i, p in enumerate(placements)]
    assert local.bind(placements, rows) == {
        name: tuple(f"f{i + 1}" for i in slots) for name, slots in local.GROUP_SLOTS.items()}


@pytest.mark.parametrize("draw", DRAWS)
@pytest.mark.parametrize("arm, path", [
    ("silent", "cannae-local-rush-think"), ("silent", "cannae-local-concentrate"),
    ("peer", "cannae-peer-witness"), ("muted", "cannae-muted-witness")])
def test_the_foils_and_peer_witness_load_on_their_arm(draw, arm, path):
    """Wrong version: an entry whose arm play's controller check refuses for these files."""
    name = f"emp-wing-horse-{draw}-{arm}-v1"
    config = {"policy": "configured", "controller_config": str(CONTROLLERS / f"{path}.json"),
              "scenario": name}
    frozen = configured.load(config["controller_config"], config)[0]
    assert set(frozen["members"]) == local_team.member_names(arm)
    local_team.validate_config(setup.scenarios()[name], config)
