import json
from copy import deepcopy

import pytest

from twwarhammer3.battle import setup
from twwarhammer3.protocol import ProtocolError


def test_an_entry_copies_its_base_chain_merging_dicts_and_replacing_the_rest(tmp_path,
                                                                              monkeypatch):
    army = {"subculture": "a", "faction": "fa", "units": ["lord", "inf"], "mounts": {"0": "m"}}
    path = tmp_path / "scenarios.json"
    path.write_text(json.dumps({
        "one": {"name": "one", "player": army, "enemy": None, "expect": {"x": 1, "y": 2}},
        "two": {"base": "one", "name": "two", "player": {"units": ["lord"]},
                "expect": {"y": 3}, "note": "added"},
        "three": {"base": "two", "name": "three", "enemy": [army, army]},
    }))
    monkeypatch.setattr(setup, "SCENARIOS_PATH", path)
    resolved = setup.scenarios()
    assert resolved["two"] == {"name": "two", "enemy": None, "expect": {"x": 1, "y": 3},
                               "note": "added", "player": {**army, "units": ["lord"]}}
    assert list(resolved["two"]["player"]) == list(army)  # a merged dict keeps its order
    assert resolved["three"] == {**resolved["two"], "name": "three", "enemy": [army, army]}
    assert setup.load_scenario({"scenario": "three"}) == resolved["three"]


def test_every_named_scenario_resolves_and_recruits_its_rosters():
    for name, scenario in setup.scenarios().items():
        assert "base" not in scenario and scenario.get("name", name) == name
        if not scenario.get("random"):
            steps = setup.scenario_steps(scenario)
            actual = [(s["slot"], s["recruit"], s.get("reinforcements", False))
                      for s in steps if "recruit" in s]
            expected = [(slot, unit, reserve)
                        for slot, side in enumerate(setup.sides(scenario))
                        for reserve, units in ((False, side["units"]),
                                               (True, side.get("reinforcements")))
                        for unit in units or []]
            assert actual == expected, name


def test_timerless_declaration_ignores_hidden_lobby_timer_but_requires_fixed_pool():
    scenario = setup.scenarios()["ksl-reserves-survival"]
    config = {"episode_timeout": None, "run_timeout": None, "start_timeout": 600, "episodes": 2}
    setup.fill_timeouts(scenario, config)
    setup.validate_declaration(scenario, config)
    assert config["episode_timeout"] == 3900
    assert not any("SetTimeLimit" in str(step) or "TimeLimitSeconds" in str(step)
                   for step in setup.menu_checks(scenario))
    assert any(s.get("expression", "").endswith("IsTimeLimitUsed") and s["expect"] is False
               for s in setup.menu_checks(scenario))
    scenario["player"]["reinforcements"] = None
    with pytest.raises(ValueError, match="reinforcement pools"):
        setup.validate_declaration(scenario, config)


def test_explicit_reinforcements_are_selected_after_starting_army_and_verified():
    scenario = setup.scenarios()["ksl-reserves-survival"]
    steps = setup.scenario_steps(scenario)
    switch = next(i for i, step in enumerate(steps)
                  if "SetIsRecruitingReinforcements(true)" in step.get("command", ""))
    main = [s for s in steps[:switch] if "recruit" in s]
    reserve = [s for s in steps[switch:] if "recruit" in s]
    assert len(main) == 10 and all(not s.get("reinforcements") for s in main)
    assert len(reserve) == 7 and all(s["reinforcements"] for s in reserve)
    verify = next(s for s in steps if "ReinforcingUnitList.JoinString" in s.get("expression", ""))
    assert "expect" not in verify  # The lobby sorts by unit class; check_menu compares counts.
    assert verify["required"]
    assert not any("button_autogen_reinforcements" in str(s) for s in steps)


def test_recruitment_card_namespace_can_differ_from_banner():
    steps = setup.scenario_steps(setup.scenarios()["chd-reserve-grn-siege"])
    assert any(s.get("expression") == setup.LOBBY + "PlayerSlotList.At(0).FactionRecordContext.Key"
               and s["expect"] == "wh3_dlc23_chd_astragoth" for s in steps)
    recruits = [s for s in steps if "recruit" in s and s["slot"] == 0]
    assert recruits and all(s["faction"] == "wh3_dlc23_chd_legion_of_azgorh" for s in recruits)


def test_declared_armies_verify_recruitment_before_attempting_readiness():
    scenario = setup.scenarios()["emp-battery-skv-evacuation"]
    steps = setup.scenario_steps(scenario)
    start = next(i for i, step in enumerate(steps)
                 if step.get("find") == ["start_button_frame", "button_start_battle"])
    for slot, army in enumerate(setup.sides(scenario)):
        expression = f"{setup.LOBBY}PlayerSlotList.At({slot}).UnitList.Size"
        check = next(i for i, step in enumerate(steps) if step.get("expression") == expression)
        assert check < start
        assert steps[check]["expect"] == len(army["units"])
        assert steps[check]["required"] is True


def test_variants_differ_from_their_base_only_where_declared():
    scenarios = setup.scenarios()
    hard, base = scenarios["brt-cavalry-emp-pikes-hard"], scenarios["brt-cavalry-emp-pikes"]
    assert hard["expect"] == {**base["expect"], "ai_stats_modifier": "1.1"}
    assert {**hard, "name": base["name"], "expect": base["expect"]} == base
    siege = scenarios["siege-kho5-dwf5"]
    assert {**siege, "battle_type": None, "map": None, "attacker": None} == {
        **scenarios["kho5-dwf5"], "battle_type": None, "map": None, "attacker": None}


def test_a_step_named_after_its_base_keeps_the_base_family_as_its_split_group():
    # Final review: the S9 Trolls step declared its own family, which split S9's jobs into
    # two export groups (docs/posttraining.md: a group must not leak across splits).
    entries = json.loads(setup.SCENARIOS_PATH.read_text())
    scenarios = setup.scenarios()
    steps = [(name, entry["base"]) for name, entry in entries.items()
             if entry.get("base") and name.startswith(entry["base"] + "-")]
    assert ("grn-giant-ksl-streltsi-trolls", "grn-giant-ksl-streltsi") in steps
    assert [(name, base) for name, base in steps
            if scenarios[name].get("family") != scenarios[base].get("family")] == []


def test_scenario_steps_pick_each_race_faction_and_preserve_recruitment_order():
    steps = setup.scenario_steps(setup.load_scenario({"scenario": "kho5-dwf5"}))
    races = [s["expect"] for s in steps
             if s.get("expression", "").endswith("SubcultureContext.Key")]
    assert races == ["wh3_main_sc_kho_khorne", "wh_main_sc_dwf_dwarfs"]
    factions = [s["expect"] for s in steps
                if s.get("expression", "").endswith("FactionRecordContext.Key")]
    assert factions == ["wh3_main_kho_khorne", "wh_main_dwf_dwarfs"]
    commands = [s.get("command", "") for s in steps]
    assert sum("SetSubculture(" in value for value in commands) == 2
    assert sum("SetFaction(" in value for value in commands) == 2
    recruits = [s for s in steps if "recruit" in s]
    assert recruits[0]["recruit"] == "wh3_main_kho_cha_herald_of_khorne_0"
    assert recruits[5]["recruit"] == "wh_main_dwf_cha_lord_0"
    assert len(recruits) == 10
    assert steps[-4]["find"] == ["start_button_frame", "button_start_battle"]
    assert steps[-1] == {"log": setup.NOT_STARTED}


def test_a_lordless_roster_preserves_its_units_without_adding_a_lord():
    steps = setup.scenario_steps(setup.load_scenario({"scenario": "ksl-raiders-emp-halberds"}))
    recruits = [s["recruit"] for s in steps if "recruit" in s]
    assert recruits == ["wh3_main_ksl_cav_horse_raiders_0"] * 2 + ["wh_main_emp_inf_halberdiers"]
    sizes = [s["expect"] for s in steps if s.get("expression", "").endswith("UnitList.Size")]
    assert sizes == [2, 1]


def test_larger_and_corner_candidates_declare_their_slots_lords_and_roles():
    config = {"episode_timeout": 2520, "run_timeout": 99999, "start_timeout": 600,
              "episodes": 1}
    for name in ("emp-pitched-grn-20", "ksl-ffa-grn-dwf-12", "dwf-longbeards-emp-swordsmen"):
        scenario = setup.load_scenario({"scenario": name})
        setup.validate_declaration(scenario, config)
    steps = setup.scenario_steps(setup.load_scenario({"scenario": "ksl-ffa-grn-dwf-12"}))
    adds = [s["when"] for s in steps if s.get("find") == ["bottom_team_parent", "button_add_ai"]]
    assert adds == [f"{setup.LOBBY}PlayerSlotList.Size < {n}" for n in (2, 3, 4)]
    pitched = setup.scenarios()["emp-pitched-grn-20"]
    assert len(pitched["player"]["units"]) == len(pitched["enemy"]["units"]) == 20
    corner = setup.scenarios()["dwf-longbeards-emp-swordsmen"]
    assert corner["player"]["lord"] is corner["enemy"]["lord"] is False
    assert corner["attacker"] == "enemy" and corner["expect"]["player_defends"] is True


def test_free_for_all_scenarios_declare_four_sides():
    # The lobby refused a three-army free-for-all: "Free-For-All requires 4 teams" (L2, b23).
    for name, scenario in setup.scenarios().items():
        if scenario.get("battle_type") == "free_for_all":
            count = (1 + scenario.get("enemies", 1) if scenario.get("random")
                     else len(setup.sides(scenario)))
            assert count == 4, name


def test_mount_stays_attached_to_its_recruited_type_with_budget_already_set():
    scenario = setup.load_scenario({"scenario": "brt-cavalry-emp-pikes"})
    steps = setup.scenario_steps(scenario)
    mounted = next(i for i, s in enumerate(steps) if "mount" in s)
    budgets = [i for i, s in enumerate(steps) if "SetCustomFundsAmount(" in s.get("command", "")]
    assert budgets[0] < mounted < budgets[-1]
    assert steps[mounted]["recruit"] == scenario["player"]["units"][0]
    assert steps[mounted]["mount"] == "wh_main_brt_cha_lord_4"
    assert steps[mounted]["required"]


def test_battle_type_scenarios_select_the_type_slots_and_roles():
    scenarios = setup.scenarios()
    steps = setup.scenario_steps(scenarios["siege-kho5-dwf5"])
    finds = [s.get("find") for s in steps]
    assert ["map_type_list", "CcoBattleTypeRecordsiege"] in finds
    # A survival battle before this one removed the AI slot; it is added back only then.
    add = [s for s in steps if s.get("find") == ["bottom_team_parent", "button_add_ai"]]
    assert [s["when"] for s in add] == [setup.LOBBY + "PlayerSlotList.Size < 2"]
    swap = next(s for s in steps if s.get("find", [""])[-1] == "button_swap_attacker_defender")
    assert swap["when"] == setup.PLAYER_ATTACKS  # the player defends: swap only if attacking
    assert finds.index(swap["find"]) < finds.index(["teams_parent",
                                                    "CcoCustomBattlePlayerSlotslot1"])

    ffa = setup.scenario_steps(scenarios["ffa-kho5-dwf5-emp5-kho5"])
    add = [s["when"] for s in ffa if s.get("find") == ["bottom_team_parent", "button_add_ai"]]
    assert add == [setup.LOBBY + f"PlayerSlotList.Size < {n}" for n in (2, 3, 4)]
    slots = [s["find"][1] for s in ffa if s.get("find", [""])[0] == "teams_parent"]
    assert slots == [f"CcoCustomBattlePlayerSlotslot{n}" for n in (0, 1, 2, 3, 0)]
    assert not any("swap" in s.get("find", [""])[-1] for s in ffa)

    survival = setup.scenario_steps(scenarios["survival-kho5"])
    assert not any(s.get("find") == ["bottom_team_parent", "button_add_ai"] for s in survival)
    removes = [s for s in survival if s.get("find", [""])[-1] == "button_remove"]
    assert removes[-1]["find"][0] == "CcoCustomBattlePlayerSlotslot1"
    assert removes[-1]["when"] == setup.LOBBY + "PlayerSlotList.Size > 1"


def test_domination_and_survival_sides_get_an_autogenerated_reinforcing_army():
    scenarios = setup.scenarios()
    for name, count in (("domination-kho5-dwf5", 2), ("survival-kho5", 1), ("siege-kho5-dwf5", 0)):
        finds = [s.get("find") for s in setup.scenario_steps(scenarios[name])]
        assert finds.count(["clear_autogen_reinforcement_parent",
                            "button_autogen_reinforcements"]) == count


def test_the_expected_mode_follows_the_battle_type_and_attacker():
    scenarios = setup.scenarios()
    assert setup.expected_mode(scenarios["siege-kho5-dwf5"]) == {
        "type": "settlement_standard", "role": "defender"}
    assert setup.expected_mode(scenarios["kho5-dwf5"]) == {}


def test_a_random_scenario_draws_a_map_and_races_and_autogenerates_both_armies():
    config = {"scenario": "random", "seed": 7}
    draw = setup.load_scenario(config)
    assert draw == setup.load_scenario({"scenario": "random", "seed": 7})
    catalogue = json.loads(setup.CATALOGUE_PATH.read_text())
    assert draw["map"] in catalogue["maps"]
    for side in ("player", "enemy"):
        assert draw[side]["subculture"] in catalogue["races"]
        assert draw[side]["units"] is None and "faction" not in draw[side]
    steps = setup.scenario_steps(draw)
    finds = [s.get("find") for s in steps]
    # The faction only changes banner colours, so a draw leaves it to the game.
    assert not any(f and f[0] == "dropdown_context_scroll" for f in finds)
    assert ["map_type_list", "CcoBattleTypeRecordclassic"] in finds
    assert ["map_listview", "CcoCustomBattleMap" + draw["map"]] in finds
    assert finds.count(["clear_autogen_parent", "button_autogen"]) == 2
    assert not any(s.get("dblclick") for s in steps)
    unseeded = {"scenario": "random", "seed": None}
    setup.load_scenario(unseeded)
    assert isinstance(unseeded["seed"], int)
    assert "wh_dlc03_sc_bst_beastmen" not in catalogue["races"]


def test_random_draws_of_battle_types_and_the_old_classic_draws_stay_the_same():
    # A draw played before battle types existed (seed 2028855463, 2026-10-13).
    assert setup.load_scenario({"scenario": "random", "seed": 2028855463}) == {
        "map": "battle_preset_devastation_volcano_01_09",
        "player": {"subculture": "wh2_main_sc_def_dark_elves", "units": None},
        "enemy": {"subculture": "wh3_main_sc_nur_nurgle", "units": None}}
    catalogue = json.loads(setup.CATALOGUE_PATH.read_text())
    siege = setup.load_scenario({"scenario": "random-siege", "seed": 5})
    assert siege["map"] in catalogue["battle_type_maps"]["siege"]
    assert siege["battle_type"] == "siege" and siege["attacker"] == "enemy"
    assert setup.expected_mode(siege) == {"type": "settlement_standard", "role": "defender"}
    ffa = setup.load_scenario({"scenario": "random-ffa", "seed": 5})
    assert len(setup.sides(ffa)) == 4
    survival = setup.load_scenario({"scenario": "random-survival", "seed": 5})
    assert survival["enemy"] is None and survival["player"]["reinforcements"] is None
    steps = setup.scenario_steps(survival)
    finds = [s.get("find") for s in steps]
    assert finds.count(["clear_autogen_reinforcement_parent",
                        "button_autogen_reinforcements"]) == 1
    domination = setup.load_scenario({"scenario": "random-domination", "seed": 5})
    assert all("reinforcements" in side for side in setup.sides(domination))


def test_unset_timeouts_become_the_least_a_benchmark_accepts():
    benchmark = setup.load_scenario({"scenario": "brt-cavalry-emp-assault"})
    config = {"episodes": 3, "start_timeout": 900, "episode_timeout": None, "run_timeout": None}
    setup.fill_timeouts(benchmark, config)
    assert config["episode_timeout"] == benchmark["expect"]["time_limit_s"] + 120 == 1320
    assert config["run_timeout"] == 8 * 3600
    setup.validate_declaration(benchmark, config)
    many = {**config, "episodes": 30, "run_timeout": None}
    setup.fill_timeouts(benchmark, many)
    assert many["run_timeout"] == 900 + 30 * (1320 + 60)
    setup.validate_declaration(benchmark, many)
    other = {**config, "episode_timeout": None, "run_timeout": 60}
    setup.fill_timeouts({}, other)
    assert (other["episode_timeout"], other["run_timeout"]) == (3900, 60)
    with pytest.raises(ValueError, match="exceed a finite game timer"):
        setup.validate_declaration(benchmark, {**config, "episode_timeout": 1200})
    with pytest.raises(ValueError, match="own launch"):
        setup.validate_declaration(benchmark, {**config, "attach": True})


@pytest.mark.parametrize("scale,key,realism,condition", [
    (.25, "unit_scale_small", True, "!"), (1, "unit_scale_ultra", False, ""),
])
def test_declared_lobby_settings_are_set_and_read_back(scale, key, realism, condition):
    scenario = setup.load_scenario({"scenario": "brt-cavalry-emp-assault"})
    scenario["expect"].update(unit_scale=scale, realism=realism)
    steps = setup.menu_checks(scenario)
    commands = [s.get("command", "") for s in steps]
    assert any("SetDifficultyLevelSettingContext(" in value
               and 'Key == "ai_level_very_hard"' in value for value in commands)
    assert any("SetUnitScaleSettingContext(" in value and f'Key == "{key}"' in value
               for value in commands)
    toggle = next(s for s in steps if "ToggleRealismMode()" in s.get("command", ""))
    assert toggle["when"] == condition + setup.SETTINGS + "IsRealismMode"
    readbacks = {s["expression"]: s["expect"] for s in steps if "expression" in s}
    assert readbacks[setup.SETTINGS + "DifficultyLevelSettingContext.Key"] == "ai_level_very_hard"
    assert readbacks[setup.SETTINGS + "UnitScaleSettingContext.Key"] == key
    assert readbacks[setup.SETTINGS + "IsRealismMode"] is realism


def test_explicit_ai_modifier_is_applied_after_difficulty_resets_its_default():
    # Live integration r1: selecting very hard reset the modifier from 1.0 to 1.1.
    scenario = setup.load_scenario({"scenario": "brt-cavalry-emp-pikes"})
    scenario["expect"].update(difficulty="ai_level_very_hard", ai_stats_modifier="1.0")
    commands = [s.get("command", "") for s in setup.menu_checks(scenario)]
    difficulty = next(i for i, value in enumerate(commands)
                      if "SetDifficultyLevelSettingContext(" in value)
    modifier = commands.index(setup.SETTINGS + "SetBattleAiStatsModifier(1)")
    assert difficulty < modifier, "difficulty must not overwrite the explicit AI modifier"


def test_setup_rejects_roster_multiplicity_factions_and_settings():
    scenario = {"expect": {"time_limit_s": 1200, "unit_scale": .75, "realism": False,
                           "player_defends": True,
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
    scenario = {"map": "intended", "player": {}, "expect": {"battle_type": "land_normal",
                "difficulty": "ai_level_very_hard", "funds": "funds_large", "time_limit_s": 3600,
                "ai_stats_modifier": "1.0", "unit_scale": .75, "realism": False}}
    lines = [f"step {i}: {step['expression']} = {step['expect']}"
             for i, step in enumerate(setup.menu_checks(scenario)) if "expression" in step]
    (tmp_path / "menu.log").write_text("\n".join(lines))
    (tmp_path / "map_list.txt").write_text("  CcoCustomBattleMapintended <selected>\n")
    assert setup.check_menu(scenario, tmp_path)["map"] == "intended"
    (tmp_path / "map_list.txt").write_text("  CcoCustomBattleMapother <selected>\n")
    with pytest.raises(ProtocolError, match="setup map"):
        setup.check_menu(scenario, tmp_path)


def test_mounted_roster_rejects_an_unmounted_lord():
    scenario = setup.load_scenario({"scenario": "brt-cavalry-emp-pikes"})
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


@pytest.mark.parametrize("experience", [None, [3], {"-1": 3}, {"2": 3}, {"00": 3},
                                        {0: 3}, {"0": True}, {"0": 1.5}, {"0": -1}, {"0": 10}])
def test_invalid_experience_is_refused_before_building_menu_steps(experience):
    army = {"units": ["lord", "swordsmen"], "experience": experience}
    with pytest.raises(ValueError, match="experience must map"):
        setup.scenario_steps({"player": army})


def test_presets_reuse_only_identical_fixed_armies_on_the_same_build():
    scenario = setup.scenarios()["grn-chariot-emp-swordsmen"]
    name = setup.army_preset_name(scenario, scenario["enemy"], "build1")
    assert name and name == setup.army_preset_name(deepcopy(scenario), scenario["enemy"], "build1")
    for field, value in (("units", ["other"]), ("experience", {"1": 3}),
                         ("mounts", {"0": "mounted"}), ("faction", "other")):
        changed = {**scenario["enemy"], field: value}
        assert setup.army_preset_name(scenario, changed, "build1") != name
    assert setup.army_preset_name(scenario, scenario["enemy"], "build2") != name
    assert setup.army_preset_name(scenario, {**scenario["enemy"], "units": None}, "build1") is None
    random_pool = {**scenario["enemy"], "reinforcements": None}
    assert setup.army_preset_name(scenario, random_pool, "build1") is None
    steps = setup.scenario_steps(scenario, build_id="build1")
    recruits = [s for s in steps if "recruit" in s]
    assert recruits and all(s.get("when", "").startswith("!") for s in recruits)
    checks = [s for s in steps if "UnitList.Count(" in s.get("expression", "")]
    assert checks and all(s["required"] and "when" not in s for s in checks)


def test_experience_is_assigned_after_recruitment_with_types_including_mounted_variants():
    army = {"subculture": "a", "faction": "a", "units": ["lord", "sword", "missile", "sword"],
            "mounts": {"0": "horse"}, "experience": {"2": 1, "3": 9}}
    steps = setup.scenario_steps({"player": army})
    change = next(i for i, step in enumerate(steps) if "experience" in step)
    assert change > max(i for i, step in enumerate(steps) if "recruit" in step)
    assert steps[change]["experience"] == [{"type": u, "rank": r} for u, r in
        zip(["horse", "sword", "missile", "sword"], [0, 0, 1, 9], strict=True)]


def test_battle_rank_check_rejects_correct_types_with_wrong_or_missing_ranks():
    scenario = setup.scenarios()["grn-chariot-emp-swordsmen"]
    scenario["enemy"]["experience"] = {"1": 3}
    ranks = {"friendly": [{"type": scenario["player"]["units"][0], "rank": 0}],
             "enemy": [{"type": u, "rank": r} for u, r in
                       zip(scenario["enemy"]["units"], [3, 0], strict=True)]}
    state = {"setup": {**scenario["expect"], "army_ai_stats_modifiers": [1., 1.],
                        "unit_experience": ranks},
             "armies": {side: {"faction": scenario[side]["faction"]}
                        for side in ("player", "enemy")}, "terrain": {"rows": [".."]},
             "friendly": [{"type": u, "id": f"f{i}"}
                          for i, u in enumerate(scenario["player"]["units"])],
             "enemy_roster": [{"type": u} for u in scenario["enemy"]["units"]]}
    setup.check_battle(scenario, state)  # order can change on load
    before = setup.fingerprint(deepcopy(state))
    ranks["enemy"][0]["rank"] = 0
    with pytest.raises(ProtocolError, match="enemy experience"):
        setup.check_battle(scenario, state)
    assert setup.compare_starts(before, setup.fingerprint(state))["flagged"]
    del state["setup"]["unit_experience"]
    with pytest.raises(ProtocolError, match="friendly experience"):
        setup.check_battle(scenario, state)


def test_start_comparison_uses_circular_bearings_and_reports_missing_units():
    initial = {"friendly": {"f1": {"type": "a", "x": 0, "z": 0, "bearing": 359}}}
    same = {"friendly": {"f1": {"type": "a", "x": .1, "z": 0, "bearing": 1}}}
    result = setup.compare_starts(initial, same)
    assert not result["flagged"] and result["units"]["friendly/f1"]["bearing_deg"] == 2
    assert setup.compare_starts(initial, {})["flagged"]


def test_start_comparison_detects_changed_magic_or_spells_at_identical_positions():
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
    scenario = {"map": "intended", "player": {}, "expect": {"battle_type": "land_normal",
                "difficulty": "ai_level_very_hard", "funds": "funds_custom",
                "funds_amount": 30000, "time_limit_s": 1200, "ai_stats_modifier": "1.0",
                "unit_scale": .75, "realism": False}}
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


def test_lobby_pool_readback_accepts_reordering_but_rejects_missing_copies(tmp_path):
    scenario = setup.scenarios()['ksl-reserves-survival']
    lines = [f"{s['expression']} = {s['expect']}" for s in setup.menu_checks(scenario)
             if 'expression' in s]
    expr = (setup.LOBBY + 'PlayerSlotList.At(0).'
            'ReinforcingUnitList.JoinString(UnitRecordContext.Key, ";")')
    pool = list(reversed(scenario['player']['reinforcements']))
    (tmp_path / 'map_list.txt').write_text(f"CcoCustomBattleMap{scenario['map']} <selected>\n")
    (tmp_path / 'menu.log').write_text('\n'.join(lines + [expr + ' = ' + ';'.join(pool)]))
    assert setup.check_menu(scenario, tmp_path)['reinforcements_slot0']
    (tmp_path / 'menu.log').write_text('\n'.join(lines + [expr + ' = ' + ';'.join(pool[:-1])]))
    with pytest.raises(ProtocolError, match='reinforcement pool'):
        setup.check_menu(scenario, tmp_path)


def test_fort_and_survival_verify_selected_mode_instead_of_generic_map_type():
    for name, mode in [('chd-reserve-grn-siege', 'siege'),
                       ('ksl-reserves-survival', 'survival'),
                       ('emp-battery-wef-evacuation', 'ambush')]:
        checks = setup.menu_checks(setup.scenarios()[name])
        selected = [s for s in checks
                    if s.get('expression', '').endswith('BattleTypeRecordContext.Key')]
        assert selected[0]['expect'] == mode
        assert not any('MapContext.BattleTypeString' in str(s) for s in checks)


def test_second_small_batch_declares_lordless_rosters_sides_and_headroom():
    config = {"episode_timeout": 1320, "run_timeout": 99999, "start_timeout": 600,
              "episodes": 1}
    sides = {"dwf-thunderers-grn-trolls": (3, 3, True), "grn-giant-ksl-streltsi": (1, 2, False),
             "skv-spears-sla-hellstriders": (3, 2, True), "dwf-cannon-grn-lobbers": (2, 4, False)}
    for name, (player, enemy, defends) in sides.items():
        scenario = setup.load_scenario({"scenario": name})
        setup.validate_declaration(scenario, config)
        declared = setup.scenarios()[name]
        assert declared["player"]["lord"] is declared["enemy"]["lord"] is False
        counts = len(declared["player"]["units"]), len(declared["enemy"]["units"])
        assert counts == (player, enemy)
        assert declared["expect"]["player_defends"] is defends
        assert (declared["attacker"] == "enemy") is defends
        steps = setup.scenario_steps(scenario)
        sizes = [s["expect"] for s in steps if s.get("expression", "").endswith("UnitList.Size")]
        assert sizes == [player, enemy]


def declared(name):
    scenario = setup.load_scenario({"scenario": name})
    config = {"episodes": 1, "start_timeout": 900, "episode_timeout": 1320,
              "run_timeout": 8 * 3600}
    return scenario, config


# Removing any one of these declaration checks passed every test before
# (runs/refusal-sweep-20261029/setup.txt); each case breaks one declared field.
@pytest.mark.parametrize("name,change,message", [
    ("brt-cavalry-emp-assault", lambda s, c: s.pop("map"), "must pin its map"),
    ("brt-cavalry-emp-assault", lambda s, c: s["player"].update(faction=None), "pin factions"),
    ("brt-cavalry-emp-assault", lambda s, c: s["expect"].update(battle_type="siege_normal"),
     "battle type does not match"),
    ("brt-cavalry-emp-assault", lambda s, c: s["expect"].pop("unit_scale"),
     "missing expect.unit_scale"),
    ("brt-cavalry-emp-assault",
     lambda s, c: s["expect"].update(funds="funds_custom", funds_amount=0), "custom funds"),
    ("brt-cavalry-emp-assault", lambda s, c: c.update(run_timeout=60), "run timeout must cover"),
    ("ksl-reserves-survival", lambda s, c: s["expect"].update(timer_enabled=True),
     "timer_enabled false"),
    ("ksl-reserves-survival", lambda s, c: c.update(episode_timeout=0),
     "positive episode wall limit"),
    ("emp-battery-wef-evacuation", lambda s, c: s["custom"].update(version=2),
     "unsupported custom objective"),
    ("emp-battery-wef-evacuation", lambda s, c: s["custom"].update(rules=" "),
     "requires public rules"),
    ("emp-battery-wef-evacuation", lambda s, c: s["custom"]["deployment"].update(ally=[]),
     "unknown deployment side"),
    ("emp-battery-wef-evacuation",
     lambda s, c: s["custom"]["deployment"]["friendly"][0].update(width=0),
     "width must be positive"),
])
def test_each_broken_declaration_is_refused_before_launch(name, change, message):
    scenario, config = declared(name)
    setup.validate_declaration(scenario, config)
    change(scenario, config)
    with pytest.raises(ValueError, match=message):
        setup.validate_declaration(scenario, config)

def test_a_nonpositive_ai_stats_modifier_is_refused():
    scenario, _ = declared("brt-cavalry-emp-assault")
    scenario["expect"]["ai_stats_modifier"] = "0"
    with pytest.raises(ValueError, match="AI stats modifier"):
        setup.menu_checks(scenario)


def started():
    """A minimal declared scenario with a custom evacuation and the readbacks that pass it."""
    goal = {"kind": "battery_evacuation", "version": 1, "assets": ["f2", "f3"],
            "zone": {"x": 0, "z": 0, "radius": 30}, "deadline_s": 600, "rules": "Save them.",
            "deployment": {"friendly": [{"id": "f2", "x": 10, "z": 10}]}}
    scenario = {"expect": {"time_limit_s": 1200, "unit_scale": .75, "realism": False,
                           "player_defends": True, "ai_stats_modifier": "1.1"},
                "player": {"faction": "p", "units": ["lord", "gun", "gun"],
                           "reinforcements": ["knights"]},
                "enemy": {"faction": "e", "units": ["lord"]}, "custom": goal}
    state = {"setup": {**scenario["expect"], "army_ai_stats_modifiers": [1.1, 1.1],
                       "custom": {"ok": True, "deployment": {
                           "friendly": [{"id": "f2", "x": 10.5, "z": 10}]}}},
             "armies": {"player": {"faction": "p"}, "enemy": {"faction": "e"}},
             "terrain": {"rows": [".."], "bounds": {"min_x": -99, "max_x": 99,
                                                    "min_z": -99, "max_z": 99}},
             "friendly": [{"id": "f1", "type": "lord"},
                          {"id": "f2", "type": "gun", "class": "artillery"},
                          {"id": "f3", "type": "gun", "class": "artillery"}],
             "enemy_roster": [{"type": "lord"}],
             "mode": {"reinforcements": [{"type": "knights"}],
                      "custom": {**{k: goal[k] for k in ("kind", "version", "zone", "rules")},
                                 "deadline_ms": 600000,
                                 "assets": [{"id": "f2"}, {"id": "f3"}]}}}
    return scenario, state


# Removing any one of these startup checks passed every test before
# (runs/refusal-sweep-20261029/setup.txt); each case breaks one readback.
@pytest.mark.parametrize("change,message", [
    (lambda s, o: (s["expect"].update(time_limit_s=None), o.update(remaining_ms=30000)),
     "finite battle countdown"),
    (lambda s, o: o["mode"].update(reinforcements=[{"type": "spearmen"}]), "reinforcement pool"),
    (lambda s, o: o["setup"]["custom"].update(ok=False), "custom setup failed"),
    (lambda s, o: o["mode"]["custom"].update(rules="Other."), "does not match its declaration"),
    (lambda s, o: o["friendly"][1].update({"class": "infantry"}), "not artillery"),
    (lambda s, o: o["setup"]["custom"]["deployment"]["friendly"][0].update(x=40),
     "authored deployment failed"),
    (lambda s, o: o["terrain"]["bounds"].update(min_x=5), "outside the battlefield"),
])
def test_each_broken_startup_readback_stops_the_job(change, message):
    scenario, state = started()
    setup.check_battle(scenario, state)
    change(scenario, state)
    with pytest.raises(ProtocolError, match=message):
        setup.check_battle(scenario, state)


def test_a_failed_menu_step_stops_setup(tmp_path):
    (tmp_path / "menu.log").write_text("step 3: button_battle not found: lobby changed\n")
    with pytest.raises(ProtocolError, match="failed menu step"):
        setup.check_menu({"map": "m"}, tmp_path)
