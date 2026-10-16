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
            assert len([s for s in steps if s.get("dblclick")]) == sum(
                len(side["units"]) + len(side.get("reinforcements") or [])
                for side in setup.sides(scenario))


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
    assert sum(bool(s.get("dblclick")) for s in steps[:switch]) == 10
    assert sum(bool(s.get("dblclick")) for s in steps[switch:]) == 7
    verify = next(s for s in steps if "ReinforcingUnitList.JoinString" in s.get("expression", ""))
    assert "expect" not in verify  # The lobby sorts by unit class; check_menu compares counts.
    assert verify["required"]
    assert not any("button_autogen_reinforcements" in str(s) for s in steps)


def test_recruitment_card_namespace_can_differ_from_banner():
    steps = setup.scenario_steps(setup.scenarios()["chd-reserve-grn-siege"])
    assert any(s.get("find", [""])[-1] == "CcoFactionRecordwh3_dlc23_chd_astragoth" for s in steps)
    cards = [s["find"][0] for s in steps if s.get("dblclick")]
    assert all(":wh3_dlc23_chd_legion_of_azgorh:" in card for card in cards[:9])


def test_variants_differ_from_their_base_only_where_declared():
    scenarios = setup.scenarios()
    hard, base = scenarios["brt-cavalry-emp-pikes-hard"], scenarios["brt-cavalry-emp-pikes"]
    assert hard["expect"] == {**base["expect"], "ai_stats_modifier": "1.1"}
    assert {**hard, "name": base["name"], "expect": base["expect"]} == base
    siege = scenarios["siege-kho5-dwf5"]
    assert {**siege, "battle_type": None, "map": None, "attacker": None} == {
        **scenarios["kho5-dwf5"], "battle_type": None, "map": None, "attacker": None}


def test_scenario_steps_pick_each_race_and_recruit_the_lord_first():
    steps = setup.scenario_steps(setup.load_scenario({"scenario": "kho5-dwf5"}))
    races = [s["find"][1] for s in steps if s.get("find", [""])[0] == "button_select_race"]
    assert races == ["CcoSubcultureRecordwh3_main_sc_kho_khorne",
                     "CcoSubcultureRecordwh_main_sc_dwf_dwarfs"]
    factions = [s["find"][1] for s in steps if s.get("find", [""])[0] == "dropdown_context_scroll"]
    assert factions == ["CcoFactionRecordwh3_main_kho_khorne", "CcoFactionRecordwh_main_dwf_dwarfs"]
    cards = [s["find"][0] for s in steps if s.get("dblclick")]
    assert cards[0] == ("CcoUnitsCustomBattlePermissionRecord"
                        "wh3_main_kho_cha_herald_of_khorne_0:wh3_main_kho_khorne:1")
    assert cards[5].endswith("wh_main_dwf_cha_lord_0:wh_main_dwf_dwarfs:1")
    assert len(cards) == 10 and all(card.endswith(":0") for card in cards[1:5] + cards[6:])
    assert steps[-4]["find"] == ["start_button_frame", "button_start_battle"]
    assert steps[-1] == {"log": setup.NOT_STARTED}


def test_mount_is_selected_after_recruitment_and_pinned_budget_before_it():
    scenario = setup.load_scenario({"scenario": "brt-cavalry-emp-pikes"})
    steps = setup.scenario_steps(scenario)
    recruit = next(i for i, s in enumerate(steps) if s.get("dblclick"))
    mount = next(i for i, s in enumerate(steps) if "ChangeMount(" in s.get("command", ""))
    budgets = [i for i, s in enumerate(steps) if "SetCustomFundsAmount(" in s.get("command", "")]
    assert budgets[0] < recruit < mount < budgets[-1]
    assert steps[mount + 2]["expect"] == "wh_main_brt_cha_lord_4"
    assert steps[mount + 2]["required"]


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


def test_a_benchmark_needs_the_declared_realism_preference():
    benchmark = setup.load_scenario({"scenario": "brt-cavalry-emp-assault"})
    setup.check_preferences(benchmark, {"preferences": {"battle_realism_mode": "false"}})
    setup.check_preferences({}, {})
    with pytest.raises(ProtocolError, match="battle_realism_mode: 'true'"):
        setup.check_preferences(benchmark, {"preferences": {"battle_realism_mode": "true"}})


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
        selected = [s for s in checks if s.get('expression', '').endswith('BattleTypeRecordContext.Key')]
        assert selected[0]['expect'] == mode
        assert not any('MapContext.BattleTypeString' in str(s) for s in checks)
