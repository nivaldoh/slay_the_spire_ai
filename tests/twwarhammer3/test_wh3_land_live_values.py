"""Owner-approved live-value comparison; synthetic logs do not prove game mechanics."""
import copy
import sys

import pytest
from test_wh3_checkpoint import battle, check, source, write

from twwarhammer3.battle import checkpoint


def runs():
    result = {"source": source(), "restore-a": battle(), "restore-b": battle(),
              "changed": battle(changed_from=1304)}
    for rows in result.values():
        for row in rows:
            if row.get("event") == "reading":
                row["value"]["units"][0]["stats"] = "stat_morale=60/60"
    return result


def unit(rows, tick=1400):
    return next(r["value"]["units"][0] for r in rows
                if r.get("event") == "reading" and r["tick"] == tick)


def test_cached_panel_difference_is_diagnostic_and_does_not_mutate_raw_logs(tmp_path):
    logs = runs()
    unit(logs["restore-a"])["stats"] = "stat_morale=50/50"
    before = copy.deepcopy(logs)
    result = check.assess(write(tmp_path, logs))
    assert result["pass"]
    restored = result["restore-a"]
    assert restored["readings_unequal"] == []
    assert restored["strict_comparison"]["readings_unequal"] == [1400]
    assert restored["cached_stats"] == [{"tick": 1400, "units": [{
        "id": "unit", "source": "stat_morale=60/60", "restore": "stat_morale=50/50"}]}]
    assert logs == before
    assert checkpoint.compare(logs["source"], logs["restore-a"])["readings_unequal"] == [1400]


@pytest.mark.parametrize("field", ["morale_percent", "slow_speed", "fast_speed"])
def test_one_changed_live_value_fails_despite_equal_native_checksums(tmp_path, field):
    logs = runs()
    unit(logs["restore-b"])[field] += 0.25
    result = check.assess(write(tmp_path, logs))
    assert result["restore-b"]["checksum_mismatches"] == 0
    assert result["restore-b"]["readings_unequal"] == [1400]
    assert not result["pass"]


@pytest.mark.parametrize("value", [None, "4", True, float("inf"), float("nan")])
def test_equal_but_unavailable_or_non_numeric_live_getters_cannot_pass(tmp_path, value):
    logs = runs()
    for rows in logs.values():
        unit(rows)["fast_speed"] = value
    result = check.assess(write(tmp_path, logs))
    assert not result["pass"]
    assert not result["restore-a"]["live_getters_complete"]
    assert "fast_speed" in result["restore-a"]["missing_live_getters"][0]["fields"]


def test_missing_getters_in_all_runs_cannot_revalidate_old_evidence(tmp_path):
    logs = runs()
    for rows in logs.values():
        for row in rows:
            if row.get("event") == "reading":
                for field in ("slow_speed", "fast_speed", "morale_percent"):
                    row["value"]["units"][0].pop(field)
    result = check.assess(write(tmp_path, logs))
    assert not result["pass"]
    assert not result["restore-a"]["live_getters_complete"]


def test_dead_units_may_lack_getters_but_their_other_fields_remain_exact(tmp_path):
    logs = runs()
    for rows in logs.values():
        u = unit(rows)
        u.update(men=0, hp=0)
        for field in ("slow_speed", "fast_speed", "morale_percent"):
            u.pop(field)
    result = check.assess(write(tmp_path, logs))
    assert result["pass"]
    unit(logs["restore-a"])["x"] += 1
    assert not check.assess(write(tmp_path / "wrong", logs))["pass"]


def test_empty_unit_readings_cannot_satisfy_the_live_getter_contract(tmp_path):
    logs = runs()
    for rows in logs.values():
        next(r for r in rows if r.get("event") == "reading" and r["tick"] == 1400)[
            "value"]["units"] = []
    assert not check.assess(write(tmp_path, logs))["pass"]


def test_land_plans_add_live_getters_while_preserving_the_base_used_by_siege(tmp_path):
    plan = check.plans(tmp_path)
    assert check.READING == checkpoint.READING_LUA
    reading = plan["source"]["readings"]["lua"]
    assert all(field in reading for field in ("slow_speed", "fast_speed", "morale_percent"))
    assert plan["source"]["readings"] == plan["restore"]["readings"] == plan["changed"]["readings"]


@pytest.mark.parametrize("state_field", ["men", "hp"])
def test_unavailable_state_is_not_evidence_that_live_getters_are_optional(tmp_path, state_field):
    logs = runs()
    for rows in logs.values():
        u = unit(rows)
        u.pop(state_field)
        for field in ("slow_speed", "fast_speed", "morale_percent"):
            u.pop(field)
    result = check.assess(write(tmp_path, logs))
    assert not result["pass"]
    assert not result["restore-a"]["live_getters_complete"]


def test_every_unit_needs_live_values_not_just_the_first(tmp_path):
    logs = runs()
    for rows in logs.values():
        for row in rows:
            if row.get("event") == "reading":
                other = dict(row["value"]["units"][0], id="second")
                row["value"]["units"].append(other)
    assert check.assess(write(tmp_path / "valid", logs))["pass"]
    for rows in logs.values():
        u = next(r["value"]["units"][1] for r in rows
                 if r.get("event") == "reading" and r["tick"] == 1400)
        for field in ("slow_speed", "fast_speed", "morale_percent"):
            u.pop(field)
    result = check.assess(write(tmp_path / "missing", logs))
    assert not result["pass"]
    assert any(missing.get("id") == "second"
               for missing in result["restore-a"]["missing_live_getters"])


def test_historical_raw_recount_keeps_its_exact_rule_and_method_label(tmp_path):
    logs = runs()
    for rows in logs.values():
        for row in rows:
            if row.get("event") == "reading":
                for field in ("slow_speed", "fast_speed", "morale_percent"):
                    row["value"]["units"][0].pop(field)
    output = write(tmp_path / "old", logs)
    raw = check.assess(output, legacy_raw=True)
    assert raw["pass"] and raw["reading_comparison"] == "raw-v1"
    current = check.assess(output)
    assert not current["pass"] and current["reading_comparison"] == "live-values-v1"
    unit(logs["restore-a"])["stats"] = "stat_morale=50/50"
    assert not check.assess(write(tmp_path / "different", logs), legacy_raw=True)["pass"]


def test_legacy_raw_option_requires_recount_before_any_launch(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["check", "--legacy-raw-recount", "--output", "new"])
    with pytest.raises(SystemExit) as error:
        check.main()
    assert error.value.code == 2
    assert "--legacy-raw-recount requires --recount" in capsys.readouterr().err
