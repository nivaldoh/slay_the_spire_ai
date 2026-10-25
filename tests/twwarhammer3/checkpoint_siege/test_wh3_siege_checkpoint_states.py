"""A siege state must have occurred by handover, even when later readings contain it."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_wh3_checkpoint_siege import (
    CANNON,
    CASES,
    CAVALRY,
    GELT,
    GUNS,
    SWORDS,
    checkpoint_witnesses,
)


def history():
    values = {}
    for tick in (50, 100, 150):
        before = tick == 50
        units = [{"id": kind, "type": kind, "side": 1, "men": 10, "hp": 1, "ammo": 0}
                 for kind in (GUNS, GELT, SWORDS, CAVALRY, CANNON)]
        units[0].update(ammo=10 if before else 9, hp=1 if before else .8)
        values[tick] = {
            "battle": {"units": units},
            "siege": {"climbing": [{"climbing": not before}],
                      "gates": [{"gate_hp": 9000 if before else 0, "gate_max_hp": 9000}]},
            "native_gates": [{"hp": 9000 if before else 0, "max_hp": 9000}],
        }
    return values


def test_checkpoint_witnesses_require_the_declared_unit_and_gate_states():
    values = history()
    checks = checkpoint_witnesses(values, 100, CASES["helmgart-field"], "late")
    assert checks == {"spent_ammo": True, "damaged_units": True,
                      "living_friendly_types_at_checkpoint": True, "climbing_at_checkpoint": True,
                      "destroyed_gate_at_checkpoint": True,
                      "native_destroyed_gate_at_checkpoint": True}
    open_gate = copy.deepcopy(values)
    open_gate[100]["siege"]["gates"][0]["gate_hp"] = 7000
    open_gate[100]["native_gates"][0]["hp"] = 7000
    checks = checkpoint_witnesses(open_gate, 100, CASES["helmgart-field"], "gate-open")
    assert checks == {"spent_ammo": True, "damaged_units": True,
                      "living_friendly_types_at_checkpoint": True, "climbing_at_checkpoint": True}


@pytest.mark.parametrize("missing", ["spent_ammo", "damaged_units", "climbing_at_checkpoint",
                                     "destroyed_gate_at_checkpoint",
                                     "native_destroyed_gate_at_checkpoint"])
def test_later_source_states_do_not_supply_a_missing_checkpoint_witness(missing):
    values = history()
    current = values[100]
    if missing == "spent_ammo":
        current["battle"]["units"][0]["ammo"] = 10
    elif missing == "damaged_units":
        current["battle"]["units"][0]["hp"] = 1
    elif missing == "climbing_at_checkpoint":
        current["siege"]["climbing"][0]["climbing"] = False
    elif missing == "destroyed_gate_at_checkpoint":
        current["siege"]["gates"][0]["gate_hp"] = 7000
    else:
        current["native_gates"][0]["hp"] = 7000
    checks = checkpoint_witnesses(values, 100, CASES["helmgart-field"], "late")
    assert checks[missing] is False
    assert not all(checks.values())


def test_a_gate_with_no_known_hitpoint_capacity_does_not_witness_destruction():
    values = history()
    values[100]["siege"]["gates"][0]["gate_max_hp"] = 0
    values[100]["native_gates"][0]["max_hp"] = 0
    checks = checkpoint_witnesses(values, 100, CASES["helmgart-field"], "late")
    assert checks["destroyed_gate_at_checkpoint"] is False
    assert checks["native_destroyed_gate_at_checkpoint"] is False


@pytest.mark.parametrize("missing", ["absent", "no_men", "no_hp", "enemy_only"])
def test_an_initial_unit_type_must_still_be_alive_and_friendly_at_checkpoint(missing):
    values = history()
    units = values[100]["battle"]["units"]
    unit = next(u for u in units if u["type"] == CANNON)
    if missing == "absent":
        units.remove(unit)
    elif missing == "no_men":
        unit["men"] = 0
    elif missing == "no_hp":
        unit["hp"] = 0
    else:
        unit["side"] = 2
    checks = checkpoint_witnesses(values, 100, CASES["helmgart-field"], "late")
    assert checks["living_friendly_types_at_checkpoint"] is False
