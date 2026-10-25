"""Exact live readings, retained cache diagnostics, and distinct siege-check inputs."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_wh3_checkpoint_siege import (
    CASES,
    assess_case,
    changed_order_recorded,
    compare_runs,
    fixture_declaration,
    source_plan,
)


def sample():
    return [{"event": "tick", "tick": 1, "checksum": 7},
            {"event": "reading", "tick": 1, "value": {
                "battle": {"units": [{"id": "1002", "side": 1, "men": 75, "hp": 1,
                    "stats": "stat_armour=30.00/30.00;scalar_speed=48.00/48.00",
                    "slow_speed": 1.8999999761581, "fast_speed": 4.8000001907349,
                    "morale_percent": 0.12345678912345}]},
                "siege": {"gates": [{"gate_hp": 9000}], "stats": "unrelated field"}}}]


@pytest.mark.parametrize("cached_stat", ["speed", "armour"])
def test_infocard_text_is_diagnostic_with_the_original_failure_retained(cached_stat):
    source, restored = sample(), sample()
    restored[1]["value"]["battle"]["units"][0]["stats"] = (
        "stat_armour=30.00/30.00;scalar_speed=60.00/60.00" if cached_stat == "speed" else
        "stat_armour=27.00/27.00;scalar_speed=48.00/48.00")
    original = copy.deepcopy(source)
    result = compare_runs(source, restored)
    assert source == original
    assert not result["readings_unequal"] and result["live_getters_complete"]
    assert result["strict_comparison"]["readings_unequal"] == [1]
    assert [row["tick"] for row in result["cached_stats"]] == [1]


@pytest.mark.parametrize("changed", ["speed", "morale", "gate", "other_stats"])
def test_live_values_and_every_other_field_still_compare_exactly(changed):
    restored = sample()
    value = restored[1]["value"]
    unit = value["battle"]["units"][0]
    if changed == "speed":
        unit["fast_speed"] = 4.8000006675720
    elif changed == "morale":
        unit["morale_percent"] = 0.12345678912346
    elif changed == "gate":
        value["siege"]["gates"][0]["gate_hp"] -= 1
    else:
        value["siege"]["stats"] = "a stats field outside battle.units"
    assert compare_runs(sample(), restored)["readings_unequal"] == [1]


@pytest.mark.parametrize("invalid", [None, float("inf")])
def test_matching_missing_or_nonfinite_native_getters_cannot_pass(invalid):
    source = sample()
    source[1]["value"]["battle"]["units"][0]["fast_speed"] = invalid
    result = compare_runs(source, source)
    assert not result["live_getters_complete"] and len(result["missing_live_getters"]) == 2


@pytest.mark.parametrize("names", [("source", "a", "a", "changed"),
                                  ("source", "a", "b", "source"),
                                  ("source", "a", "b", "a")])
def test_reusing_one_run_cannot_count_as_an_independent_restore(tmp_path, names):
    source, a, b, changed = [tmp_path / name for name in names]
    with pytest.raises(ValueError, match="distinct run directories"):
        assess_case(source, [a, b], changed, 1100, 1200, "helmgart-defender", "post-spell")


def test_changed_control_needs_the_recorded_extra_order_at_its_declared_tick():
    order = {"event": "lua", "label": "changed_flyer_move", "tick": 1200}
    assert changed_order_recorded([order], 1200)
    assert not changed_order_recorded([], 1200)
    assert not changed_order_recorded([{**order, "tick": 1300}], 1200)
    assert not changed_order_recorded([{**order, "label": "another_order"}], 1200)


@pytest.mark.parametrize("wrong", ["map", "role", "equipment"])
def test_a_recorded_plan_must_match_the_case_it_is_claimed_to_test(wrong):
    case = CASES["helmgart-defender"]
    plan = source_plan("test", case)
    assert fixture_declaration(plan, case)["pass"]
    if wrong == "map":
        plan["scenario"]["map"] = CASES["capital-attacker"]["map"]
    elif wrong == "role":
        plan["scenario"]["attacker"] = "player"
    else:
        expression = ('CustomBattleLobbyContext.PlayerSlotList.At(1).'
                      'SiegeEquipmentList.Count(Key == "emp_siege_tower_15m")')
        final = [s for s in plan["lobby_steps"] if s.get("expression") == expression][-1]
        final["expect"] = 2
    assert not fixture_declaration(plan, case)["pass"]
