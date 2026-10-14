import json

import pytest

from twwarhammer3.battle import controllers, report, setup
from twwarhammer3.battle.llm import render_state
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


def test_rules_controller_uses_its_own_prompt_and_shared_budget(tmp_path, monkeypatch):
    from gameai import llm as transport
    from twwarhammer3.battle import llm

    monkeypatch.setattr(transport, "api_key", lambda: "test-only")
    config = {"policy": "llm,llm_rules", "model": "gpt-6-luna", "effort": "low",
              "ledger": str(tmp_path / "spend.jsonl"), "budget_usd": 1}
    makers = controllers.factories(config)
    original, rules = makers["llm"](), makers["llm_rules"]()
    assert original.api.instructions == llm.SYSTEM_PROMPT_PATH.read_text()
    assert rules.api.instructions == llm.RULES_PROMPT_PATH.read_text()
    assert rules.api.instructions != original.api.instructions
    assert rules.api.ledger is original.api.ledger
    rules.notes = "previous battle"
    assert makers["llm_rules"]().notes == ""
    card = controllers.card("llm_rules", rules, config)
    assert (card["kind"], card["model"], card["cost_source"]) == (
        "model", "gpt-6-luna", "WH3 ledger")
    with pytest.raises(ValueError, match="require --budget-usd"):
        controllers.factories({**config, "policy": "llm_rules", "budget_usd": None})


def test_setup_rejects_roster_multiplicity_factions_and_settings():
    scenario = {"expect": {"unit_scale": .75, "realism": False, "player_defends": True,
                           "ai_stats_modifier": "1.1"},
                "player": {"faction": "p", "units": ["lord", "inf", "inf"]},
                "enemy": {"faction": "e", "units": ["lord"]}}
    state = {"setup": {**scenario["expect"], "army_ai_stats_modifiers": [1.1, 1.1]},
             "armies": {"player": {"faction": "p"}, "enemy": {"faction": "e"}},
             "terrain": {"rows": [".."]},
             "friendly": [{"type": t} for t in ("lord", "inf", "inf")],
             "enemy_roster": [{"type": "lord"}]}
    assert setup.check_battle(scenario, state)["friendly_roster"] == {"lord": 1, "inf": 2}
    with pytest.raises(ProtocolError, match="roster mismatch"):
        setup.check_battle(scenario, {**state, "friendly": state["friendly"][:2]})
    with pytest.raises(ProtocolError, match="unit_scale"):
        setup.check_battle(scenario, {**state, "setup": {**state["setup"], "unit_scale": 1}})
    with pytest.raises(ProtocolError, match="faction"):
        setup.check_battle(scenario, {**state, "armies": {"player": {"faction": "wrong"}}})
    with pytest.raises(ProtocolError, match="army AI modifiers"):
        setup.check_battle(scenario, {**state, "setup": {**state["setup"],
                                                       "army_ai_stats_modifiers": [1., 1.]}})
    with pytest.raises(ProtocolError, match="terrain grid is missing"):
        setup.check_battle(scenario, {**state, "terrain": None})


def test_map_gate_and_required_steps(tmp_path):
    scenario = {"map": "intended", "expect": {"battle_type": "land_normal",
                "difficulty": "ai_level_very_hard", "funds": "funds_large", "time_limit_s": 3600,
                "ai_stats_modifier": "1.0"}}
    lines = [f"step {i}: {step['expression']} = {step['expect']}"
             for i, step in enumerate(setup.menu_checks(scenario)) if "expression" in step]
    (tmp_path / "menu.log").write_text("\n".join(lines))
    (tmp_path / "map_list.txt").write_text("  CcoCustomBattleMapintended <selected>\n")
    assert setup.check_menu(scenario, tmp_path)["map"] == "intended"
    (tmp_path / "map_list.txt").write_text("  CcoCustomBattleMapother <selected>\n")
    with pytest.raises(ProtocolError, match="setup map"):
        setup.check_menu(scenario, tmp_path)


def test_mounted_roster_rejects_an_unmounted_lord():
    from twwarhammer3.battle import play

    scenario = play.load_scenario({"scenario": "brt-cavalry-emp-pikes"})
    wanted = setup.battle_units(scenario["player"])
    assert wanted[0] == "wh_main_brt_cha_lord_4"
    assert wanted[1:] == scenario["player"]["units"][1:]
    state = {"setup": {**scenario["expect"], "army_ai_stats_modifiers": [1., 1.]},
             "armies": {side: {"faction": scenario[side]["faction"]}
                        for side in ("player", "enemy")},
             "terrain": {"rows": [".."]},
             "friendly": [{"type": t} for t in wanted],
             "enemy_roster": [{"type": t} for t in scenario["enemy"]["units"]]}
    setup.check_battle(scenario, state)
    state["friendly"][0]["type"] = scenario["player"]["units"][0]
    with pytest.raises(ProtocolError, match="friendly roster mismatch"):
        setup.check_battle(scenario, state)


@pytest.mark.parametrize("mounts", [{"-1": "horse"}, {"2": "horse"},
                                   {"00": "horse"}, {"0": ""}, {0: "horse"}])
def test_bad_mount_declarations_are_refused(mounts):
    with pytest.raises(ValueError, match="mounts must map"):
        setup.battle_units({"units": ["lord", "infantry"], "mounts": mounts})


def test_start_comparison_uses_circular_bearings_and_reports_missing_units():
    initial = {"friendly": {"f1": {"type": "a", "x": 0, "z": 0, "bearing": 359}}}
    same = {"friendly": {"f1": {"type": "a", "x": .1, "z": 0, "bearing": 1}}}
    result = setup.compare_starts(initial, same)
    assert not result["flagged"] and result["units"]["friendly/f1"]["bearing_deg"] == 2
    assert setup.compare_starts(initial, {})["flagged"]


def test_start_comparison_detects_changed_magic_or_spells_at_identical_positions():
    from copy import deepcopy

    state = {"friendly": [{"id": "f1", "type": "caster", "x": 1, "z": 2, "bearing": 0,
                           "hp": 1, "men": 1, "men0": 1,
                           "abilities": [{"key": "spell_a", "mana": 6}, {"key": "spell_b"}]}],
             "magic": {"current": 20, "reserve": 60}}
    first = setup.fingerprint(state)
    reordered = deepcopy(state)
    reordered["friendly"][0]["abilities"].reverse()
    assert not setup.compare_starts(first, setup.fingerprint(reordered))["flagged"]
    changed = deepcopy(state)
    changed["magic"]["reserve"] = 30
    changed["friendly"][0]["abilities"][0]["key"] = "spell_c"
    result = setup.compare_starts(first, setup.fingerprint(changed))
    assert result["flagged"]
    assert set(result["resource_or_loadout_changes"]) == {"resources", "friendly/f1/abilities"}
    assert result["units"]["friendly/f1"]["distance_m"] == 0


def test_custom_roster_budget_is_verified_before_scoring(tmp_path):
    scenario = {"map": "intended", "expect": {"battle_type": "land_normal",
                "difficulty": "ai_level_very_hard", "funds": "funds_custom",
                "funds_amount": 30000, "time_limit_s": 1200, "ai_stats_modifier": "1.0"}}
    lines = [f"{step['expression']} = {step['expect']}"
             for step in setup.menu_checks(scenario) if "expression" in step]
    log = "\n".join(lines)
    (tmp_path / "menu.log").write_text(log)
    (tmp_path / "map_list.txt").write_text("CcoCustomBattleMapintended <selected>\n")
    assert setup.check_menu(scenario, tmp_path)["funds_amount"] == 30000
    (tmp_path / "menu.log").write_text(log.replace("CustomBudgetAmount = 30000",
                                                 "CustomBudgetAmount = 10000"))
    with pytest.raises(ProtocolError, match="funds_amount"):
        setup.check_menu(scenario, tmp_path)


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


def test_rollout_throughput_includes_setup_failures_and_unknown_job_duration(tmp_path):
    played = make_job(tmp_path, "played", [("hold", 0, "lost"), ("skills", .2, "won")])
    failed = make_job(tmp_path, "failed", [])
    for job, status, wall in ((played, "completed", 3600), (failed, "setup_failure", 1800)):
        path = job / "manifest.json"
        manifest = json.loads(path.read_text())
        path.write_text(json.dumps({**manifest, "status": status, "wall_seconds": wall}))
    result = report.collect([played, failed])
    assert result["throughput"] == {"started_trials": 2, "valid_trials": 2, "job_wall_s": 5400,
                                    "valid_trials_per_wall_hour": pytest.approx(4 / 3)}
    assert "including setup, resets and failures; 1.33 valid trials/h" in report.render(result)
    partial = make_job(tmp_path, "partial", [])
    result = report.collect([played, failed, partial])
    assert result["throughput"]["valid_trials_per_wall_hour"] is None
    assert "throughput unavailable" in report.render(result)


def test_terrain_and_rejected_move_alternatives_reach_both_model_renderers():
    state = {"terrain": {"x0": -16, "z0": -16, "cell_m": 32, "sample_width_m": 16,
                         "rows": [".#", ".."]},
             "friendly": [{"id": "f1", "type": "inf", "men": 10, "men0": 10,
                           "hp": 1, "x": 0, "z": 0, "state": [], "navigation": {
                               "rejected": {"x": 100, "z": 100}, "sampled_ms": 5000,
                               "alternatives": [{"x": 84, "z": 100}]}}]}
    text = render_state(state, {})
    assert "columns increase x and rows increase z by 32 m" in text
    assert "Narrow crossings can lie between samples" in text
    assert "unreachable move (100,100)" in text and "(84,100)" in text
