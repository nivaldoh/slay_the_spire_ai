import json

import pytest

from twwarhammer3.battle import controllers, report, setup
from twwarhammer3.protocol import ProtocolError


def test_rotation_pairs_all_controllers_and_delays_in_a_repeatable_order():
    config = {"policy": "hold,skills", "delay_seconds": "0,6,10", "rotation_seed": 13}
    trials = controllers.rotation(config)
    assert trials == controllers.rotation(dict(config))
    assert len(trials) == 6 and config["episodes"] == 6
    assert {(t["policy"], t["delay_ms"]) for t in trials} == {
        (name, delay) for name in ("hold", "skills") for delay in (0, 6000, 10000)}
    config["episodes"] = 12
    repeated = controllers.rotation(config)
    assert sorted(tuple(t.items()) for t in repeated[:6]) == sorted(
        tuple(t.items()) for t in repeated[6:])


@pytest.mark.parametrize("change", [
    {"delay_seconds": "nan"}, {"delay_seconds": "-1"}, {"delay_seconds": "0,0"},
    {"policy": "typo"}, {"episodes": 0}, {"policy": "hold,skills", "episodes": 1},
])
def test_invalid_rotation_is_refused_before_launch(change):
    with pytest.raises(ValueError):
        controllers.rotation({"policy": "hold", **change})


def test_importable_controller_and_fresh_instances():
    name = "twwarhammer3.battle.scripted:AttackNearest"
    makers = controllers.factories({"policy": name})
    a, b = makers[name](), makers[name]()
    a.targets["f1"] = "e1"
    assert b.targets == {}
    record = controllers.card(name, a, {})
    assert len(record["source_sha256"]) == 64 and record["kind"] == "external"
    with pytest.raises(ValueError, match="must be a class"):
        controllers.controller_class("twwarhammer3.battle.scripted:_distance")


def test_setup_rejects_roster_multiplicity_factions_and_settings():
    scenario = {"expect": {"unit_scale": .75, "realism": False, "player_defends": True},
                "player": {"faction": "p", "units": ["lord", "inf", "inf"]},
                "enemy": {"faction": "e", "units": ["lord"]}}
    state = {"setup": dict(scenario["expect"]),
             "armies": {"player": {"faction": "p"}, "enemy": {"faction": "e"}},
             "friendly": [{"type": t} for t in ("lord", "inf", "inf")],
             "enemy_roster": [{"type": "lord"}]}
    assert setup.check_battle(scenario, state)["friendly_roster"] == {"lord": 1, "inf": 2}
    with pytest.raises(ProtocolError, match="roster mismatch"):
        setup.check_battle(scenario, {**state, "friendly": state["friendly"][:2]})
    with pytest.raises(ProtocolError, match="unit_scale"):
        setup.check_battle(scenario, {**state, "setup": {**state["setup"], "unit_scale": 1}})
    with pytest.raises(ProtocolError, match="faction"):
        setup.check_battle(scenario, {**state, "armies": {"player": {"faction": "wrong"}}})


def test_map_gate_and_required_steps(tmp_path):
    scenario = {"map": "intended", "expect": {"battle_type": "land_normal",
                "difficulty": "ai_level_very_hard", "funds": "funds_large", "time_limit_s": 3600}}
    lines = [f"step {i}: {step['expression']} = {step['expect']}"
             for i, step in enumerate(setup.menu_checks(scenario))]
    (tmp_path / "menu.log").write_text("\n".join(lines))
    (tmp_path / "map_list.txt").write_text("  CcoCustomBattleMapintended <selected>\n")
    assert setup.check_menu(scenario, tmp_path)["map"] == "intended"
    (tmp_path / "map_list.txt").write_text("  CcoCustomBattleMapother <selected>\n")
    with pytest.raises(ProtocolError, match="setup map"):
        setup.check_menu(scenario, tmp_path)


def test_start_comparison_uses_circular_bearings_and_reports_missing_units():
    initial = {"friendly": {"f1": {"type": "a", "x": 0, "z": 0, "bearing": 359}}}
    same = {"friendly": {"f1": {"type": "a", "x": .1, "z": 0, "bearing": 1}}}
    result = setup.compare_starts(initial, same)
    assert not result["flagged"] and result["units"]["friendly/f1"]["bearing_deg"] == 2
    assert setup.compare_starts(initial, {})["flagged"]


def make_job(tmp_path, name, results, *, revision="r1"):
    job = tmp_path / name
    job.mkdir()
    (job / "manifest.json").write_text(json.dumps({
        "config": {"policy": "hold,skills"}, "scenario": {"name": "frozen"},
        "source_revision": revision, "setup_checks": {"map": "checked"},
    }))
    for index, (policy, margin, status) in enumerate(results):
        episode = job / f"episode-{index:04d}"
        episode.mkdir()
        (episode / "result.json").write_text(json.dumps({
            "policy": policy, "status": status, "elapsed_seconds": 100,
            "setup_checks": {"rosters": "checked"},
            "final": {"friendly": {"men0": 100, "active_men": 50 + margin * 100},
                      "enemy": {"men0": 100, "active_men": 50}},
        }))
    return job


def test_report_clusters_repeats_and_exposes_failures_missing_pairs_and_versions(tmp_path):
    a = make_job(tmp_path, "a", [("hold", -.1, "lost"), ("skills", .1, "won"),
                                 ("skills", .3, "won")])
    b = make_job(tmp_path, "b", [("hold", -.2, "lost"), ("skills", .1, "won")])
    c = make_job(tmp_path, "c", [("hold", 0, "policy_failure")])
    other = make_job(tmp_path, "other", [("hold", 0, "won")], revision="r2")
    result = report.collect([a, b, c, other, a])
    assert len(result["groups"]) == 2
    group = result["groups"][0]
    assert len(group["trials"]) == 6
    hold, skills = group["controllers"]
    assert hold["trials"] == 3 and hold["valid"] == 2
    assert hold["outcomes"]["policy_failure"] == 1
    assert skills["win_ci95"] is None  # correlated repeated wins cannot be independent samples
    comparison = group["paired"][0]
    assert comparison["n"] == 2 and comparison["mean"] == pytest.approx(-.3)
    assert comparison["unpaired_instances"] == [str(c.resolve())]
    assert "Paired active-strength" in report.render(result)


def test_intervals_and_missing_active_strength():
    assert report.wilson(0, 0) is None
    assert report.wilson(0, 10)[1] == pytest.approx(.27754, abs=1e-5)
    assert report.mean_interval([1])["ci95"] is None
    summary = report.mean_interval([0, 1, 2])
    assert summary["mean"] == 1
    assert summary["ci95"][1] == pytest.approx(1 + 4.303 / (3 ** .5))
