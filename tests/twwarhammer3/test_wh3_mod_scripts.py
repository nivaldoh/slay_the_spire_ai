"""Every script packed into the game must compile as Lua 5.1, the game's Lua version."""
import json
import sys

import check_wh3_army_setup as army_check
import pytest
from wh3_lua import MOD, runtime


@pytest.mark.parametrize("path", sorted(MOD.rglob("*.lua")), ids=lambda path: path.name)
def test_mod_script_compiles_as_lua51(path):
    compile_lua = runtime().eval("function(source, name) assert(loadstring(source, name)) end")
    compile_lua(path.read_text(), "=" + path.name)  # raises with the file, line and error


def test_experience_setter_matches_sorted_types_duplicates_and_refuses_game_rejection():
    lua = runtime()
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_ui.lua").read_text())
    lua.execute('''
        ranks, calls, refused = {sword = {0, 0}, missile = {0}}, 0, false
        local function target(expr)
            assert(string.find(expr, "PlayerSlotList.At(1)", 1, true))
            local unit, index = string.match(expr,
                'Filter%(UnitRecordContext.Key == "(.-)"%).At%((%d+)%)')
            return ranks[unit], tonumber(index) + 1
        end
        common = {
            get_context_value = function(context, id, expr)
                local values, index = target(expr)
                return values[index]
            end,
            call_context_command = function(context, id, expr)
                assert(context == "CcoFrontendRoot" and id == "")
                local values, index = target(expr)
                calls = calls + 1
                if not refused then
                    values[index] = values[index]
                        + (string.find(expr, "IncreaseExperience", 1, true) and 1 or -1)
                end
            end,
        }
    ''')
    run = lua.globals().twwarhammer3_ui.run
    def step(rows):
        return lua.table_from({"slot": 1, "experience": [
            {"type": unit, "rank": rank} for unit, rank in rows]}, recursive=True)
    run(step([("sword", 3), ("missile", 1), ("sword", 9)]), "")
    assert list(lua.globals().ranks.sword.values()) == [3, 9]
    assert list(lua.globals().ranks.missile.values()) == [1]
    run(step([("sword", 0), ("sword", 0), ("missile", 0)]), "")
    assert list(lua.globals().ranks.sword.values()) == [0, 0]
    assert lua.globals().calls == 26
    run(step([("sword", 0)]), "")
    assert lua.globals().calls == 26
    lua.globals().refused = True
    with pytest.raises(Exception, match="experience did not change"):
        run(step([("sword", 1)]), "")


@pytest.fixture
def recruit_context():
    """Independent lobby state for the CA permission/funds binding and sorted armies."""
    lua = runtime()
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())
    lua.execute((MOD / "script/_lib/mod/twwarhammer3_ui.lua").read_text())
    slot = "CustomBattleLobbyContext.PlayerSlotList.At(1)."
    unit = 'DatabaseRecordContext("CcoMainUnitRecord", "hero")'
    permission = (unit + '.CustomBattlePermissionsContext('
                  'DatabaseRecordContext("CcoFactionRecord", "banner"))')
    state = {"allowed": True, "general": False, "main_funds": 300, "reserve_funds": 300,
             "accept_recruitment": True, "mounted_type": "hero_horse",
             "commands": [], "queries": [],
             "pools": {"UnitList": ["hero", "hero_horse", "lord"],
                       "ReinforcingUnitList": ["sword"]}}

    def value(context, identifier, expression):
        assert context == "CcoFrontendRoot" and identifier == ""
        state["queries"].append(expression)
        answers = {unit + ".Cost": 300, permission + ".IsGeneralUnit": state["general"],
                   slot + "FundsRemaining(true)": state["main_funds"],
                   slot + "FundsRemaining(false)": state["reserve_funds"]}
        for reserve in ("true", "false"):
            answers[slot + f"CanRecruitUnit({unit}, {reserve})"] = state["allowed"]
            answers[slot + f"TooltipForUnit({unit}, {reserve})"] = "unit unavailable"
        if expression in answers:
            return answers[expression]
        for pool, army in state["pools"].items():
            prefix = slot + pool
            if expression == prefix + ".Size":
                return len(army)
            count = prefix + ".Count(UnitRecordContext.Key == "
            if expression.startswith(count) and expression.endswith(")"):
                return army.count(json.loads(expression[len(count):-1]))
        raise AssertionError("unexpected recruitment query: " + expression)

    def command(context, identifier, expression):
        assert context == "CcoFrontendRoot" and identifier == ""
        state["commands"].append(expression)
        for reserve, pool in (("false", "UnitList"), ("true", "ReinforcingUnitList")):
            army = state["pools"][pool]
            if expression == slot + f"RecruitUnit({permission}, {reserve})":
                if state["accept_recruitment"]:
                    army.append("hero")
                    army.sort()  # The new card's recruitment index is not its lobby index.
                return
            selected = slot + pool + '.FirstContext(UnitRecordContext.Key == "hero").'
            if expression == (selected + "ChangeMount(" + selected + 'AvailableMountsList.'
                              'FirstContext(MountedUnitContext.Key == "hero_horse"))'):
                if state["mounted_type"]:
                    army[army.index("hero")] = state["mounted_type"]
                    army.sort()
                return
        raise AssertionError("unexpected recruitment command: " + expression)

    lua.globals().common = lua.table_from({"get_context_value": value,
                                           "call_context_command": command})

    def run(**fields):
        return lua.globals().twwarhammer3_ui.run(lua.table_from(
            {"recruit": "hero", "faction": "banner", "slot": 1, **fields}), "")

    return run, state


@pytest.mark.parametrize("allowed,remaining,error", [
    (False, 1000, "cannot recruit.*unit unavailable"), (True, 299, "insufficient funds"),
])
def test_recruitment_permission_and_cost_are_separate_checks_before_mutation(
        recruit_context, allowed, remaining, error):
    run, state = recruit_context
    state.update(allowed=allowed, main_funds=remaining)
    before = {pool: list(army) for pool, army in state["pools"].items()}
    with pytest.raises(Exception, match=error):
        run()
    assert state["commands"] == [] and state["pools"] == before


@pytest.mark.parametrize("reserve,general,main,reserves,charged_main", [
    (False, False, 300, 0, True), (True, False, 0, 300, False), (True, True, 300, 0, True),
])
def test_recruitment_passes_explicit_reserve_and_uses_the_correct_funds_pool(
        recruit_context, reserve, general, main, reserves, charged_main):
    run, state = recruit_context
    state.update(general=general, main_funds=main, reserve_funds=reserves)
    before = {pool: list(army) for pool, army in state["pools"].items()}
    run(reinforcements=reserve)  # Cost equal to remaining funds must be accepted.
    selected = "ReinforcingUnitList" if reserve else "UnitList"
    for pool, army in state["pools"].items():
        assert sorted(army) == sorted(before[pool] + (["hero"] if pool == selected else []))
    assert len(state["commands"]) == 1
    assert state["commands"][0].endswith(", " + str(reserve).lower() + ")")
    funds = [query for query in state["queries"] if "FundsRemaining(" in query]
    assert len(funds) == 1 and funds[0].endswith("(" + str(charged_main).lower() + ")")


@pytest.mark.parametrize("mounted_type", ["hero_horse", None, "hero_dragon"])
def test_mounts_select_a_matching_duplicate_and_require_both_type_count_changes(
        recruit_context, mounted_type):
    run, state = recruit_context
    state["mounted_type"] = mounted_type
    if mounted_type == "hero_horse":
        run(mount="hero_horse")
        assert state["pools"]["UnitList"] == ["hero", "hero_horse", "hero_horse", "lord"]
    else:
        with pytest.raises(Exception, match="mount did not change"):
            run(mount="hero_horse")
        assert state["pools"]["UnitList"] == sorted(
            ["hero", mounted_type or "hero", "hero_horse", "lord"])
    assert len(state["commands"]) == 2
    assert ('.UnitList.FirstContext(UnitRecordContext.Key == "hero").ChangeMount('
            in state["commands"][1])


def test_recruitment_requires_the_game_to_add_a_card_before_mounting(recruit_context):
    run, state = recruit_context
    state["accept_recruitment"] = False
    with pytest.raises(Exception, match="recruitment did not add"):
        run(mount="hero_horse")
    assert len(state["commands"]) == 1
    assert state["pools"]["UnitList"] == ["hero", "hero_horse", "lord"]


@pytest.mark.parametrize("failure", [None, KeyboardInterrupt()])
def test_live_checker_restores_saved_settings_after_teardown_even_on_interruption(
        tmp_path, monkeypatch, failure):
    output, events = tmp_path / "check", []
    original = {"difficulty": "ai_level_normal", "realism": False}

    def checks(args):
        assert args.integration
        (args.output / "original-settings.json").write_text(json.dumps(original))
        events.append("checks")
        try:
            if failure is not None:
                raise failure
        finally:
            events.append("game teardown")

    def restore(directory):
        assert events == ["checks", "game teardown"]
        assert directory == output
        assert json.loads((directory / "original-settings.json").read_text()) == original
        events.append("restored")

    monkeypatch.setattr(sys, "argv", ["army-check", "--integration", "--output", str(output)])
    monkeypatch.setattr(army_check, "run_checks", checks)
    monkeypatch.setattr(army_check, "restore_settings", restore)
    if failure is None:
        army_check.main()
    else:
        with pytest.raises(KeyboardInterrupt) as caught:
            army_check.main()
        assert caught.value is failure
    assert events == ["checks", "game teardown", "restored"]


@pytest.mark.parametrize("primary", [None, RuntimeError("battle check failed")])
def test_live_checker_records_restore_failure_and_preserves_the_primary_exception(
        tmp_path, monkeypatch, capsys, primary):
    output = tmp_path / "check"
    recovery = OSError("settings could not be restored")

    def checks(args):
        (args.output / "original-settings.json").write_text("{}")
        if primary is not None:
            raise primary

    def restore(directory):
        assert directory == output
        raise recovery

    monkeypatch.setattr(sys, "argv", ["army-check", "--integration", "--output", str(output)])
    monkeypatch.setattr(army_check, "run_checks", checks)
    monkeypatch.setattr(army_check, "restore_settings", restore)
    with pytest.raises(type(primary or recovery)) as caught:
        army_check.main()
    assert caught.value is (primary or recovery)
    assert json.loads((output / "restore-error.json").read_text()) == {
        "error": "settings could not be restored", "error_type": "OSError"}
    assert "setting restoration failed: settings could not be restored" in capsys.readouterr().err


def test_live_checker_does_not_restore_without_an_original_snapshot(tmp_path, monkeypatch):
    def fail_before_snapshot(args):
        raise RuntimeError("lobby never opened")

    monkeypatch.setattr(sys, "argv", ["army-check", "--integration", "--output",
                                      str(tmp_path / "check")])
    monkeypatch.setattr(army_check, "run_checks", fail_before_snapshot)
    monkeypatch.setattr(army_check, "restore_settings",
                        lambda output: pytest.fail("no saved settings"))
    with pytest.raises(RuntimeError, match="lobby never opened"):
        army_check.main()
