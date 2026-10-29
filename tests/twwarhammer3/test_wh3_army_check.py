"""Offline checks for live army-check orchestration; no game is launched."""
import json
import sys
from contextlib import nullcontext
from types import SimpleNamespace

import check_wh3_army_setup as army_check
import pytest


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


@pytest.mark.parametrize("blocked", [True, False], ids=["blocker", "warning-only"])
def test_army_check_honors_diagnostics_before_launch(tmp_path, monkeypatch, capsys, blocked):
    environment = {"game": {"steam_build_id": "test-build"},
                   "blockers": ["Windows Python unavailable"] if blocked else [],
                   "warnings": ["Warhammer3.exe differs from the pinned hash (game updated?)"]}
    monkeypatch.setattr(army_check, "collect_diagnostics", lambda: environment)
    launched = []

    def launch(output):
        launched.append(output.name)
        raise RuntimeError("launch boundary")

    monkeypatch.setattr(army_check, "launch_phase", launch)
    args = SimpleNamespace(output=tmp_path, integration=True, baseline_steps=None)
    expected = "Windows Python unavailable" if blocked else "launch boundary"
    with pytest.raises(RuntimeError, match=expected):
        army_check.run_checks(args)

    assert launched == ([] if blocked else ["save"])
    assert json.loads((tmp_path / "environment.json").read_text()) == environment
    assert "WARNING: " + environment["warnings"][0] in capsys.readouterr().out


@pytest.mark.parametrize("spire_running", [True, False])
def test_each_army_launch_checks_spire_before_preparation(tmp_path, monkeypatch, spire_running):
    queries, prepared = [], []

    def conflicts(directory, rules):
        queries.append((directory, rules))
        return [{"ProcessId": 42}] if spire_running else []

    def prepare():
        prepared.append(True)
        raise RuntimeError("preparation boundary")

    monkeypatch.setattr(army_check, "conflicting_games", conflicts, raising=False)
    monkeypatch.setattr(army_check, "RuntimeLock", nullcontext)
    monkeypatch.setattr(army_check, "prepare_runtime", prepare)
    expected = "Slay the Spire is running" if spire_running else "preparation boundary"
    with pytest.raises(RuntimeError, match=expected):
        with army_check.launch_phase(tmp_path):
            pytest.fail("must not launch a real game")

    assert len(queries) == 1
    assert str(queries[0][0]) == army_check.spire_runtime.WINDOWS_GAME_DIR
    assert queries[0][1]["names"] == ["SlayTheSpire.exe"]
    assert prepared == ([] if spire_running else [True])


def stats_case(*, attack_shift=0, flat_ranks=False):
    """A lobby readback (two armies, swordsmen at ranks 0, 3 and 9) and the battle's stats."""
    sword = army_check.SWORD
    ranks = {0: (30, 20, 50), 3: (33, 22, 55), 9: (39, 26, 60)}
    if flat_ranks:
        ranks = {rank: ranks[0] for rank in ranks}
    lobby = ";".join(f"{sword}:{rank}:stat_melee_attack={a}/stat_melee_defence={d}/"
                     f"stat_morale={m}" for rank, (a, d, m) in ranks.items())
    log = ('x.UnitList.JoinString(UnitRecordContext.Key + ":" + ExperienceLevel) = '
           + lobby + "\n") * 2
    # Battle morale sits 4 below the lobby's (the side-wide offset); attack and defence match.
    army = ";".join(f"{sword}:stat_melee_attack={a + attack_shift}/stat_melee_defence={d}/"
                    f"stat_morale={m - 4}" for a, d, m in ranks.values())
    return log, {"setup": {"unit_base_stats": f"p@{army}@@e@{army}"}}


# agreed-checks.md, saved armies and experience: attack and defence exact between lobby and
# battle start, ranks raise the stats, leadership compared relative to rank zero.
def test_battle_stats_follow_the_lobby_readback():
    evidence = army_check.check_stats(*stats_case())
    assert [e["battle"][9]["stat_morale"] for e in evidence] == [56, 56]


@pytest.mark.parametrize("case", [{"attack_shift": 1}, {"flat_ranks": True}],
                         ids=["attack-off-by-one", "ranks-raise-nothing"])
def test_battle_stats_reject_a_shifted_attack_and_ranks_without_effect(case):
    with pytest.raises(AssertionError):
        army_check.check_stats(*stats_case(**case))
