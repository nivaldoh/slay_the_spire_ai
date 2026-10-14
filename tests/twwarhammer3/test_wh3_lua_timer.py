"""A finished finite countdown becomes -1 in the live engine (b8 hold at 1205 s)."""
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / (
    "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua")


def runtime():
    lua = pytest.importorskip("lupa.lua51").LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
        state = {finished = false}
        bm = {battle = {remaining_conflict_time = -1, battle_outcome_decided = false}}
        function get(object, key, default) return object[key] end
    """)
    source = "local function sample_countdown" + SOURCE.read_text().split(
        "local function sample_countdown", 1)[1].split("local function observation", 1)[0]
    sample, terminal = lua.execute(source + "\nreturn sample_countdown, terminal_countdown")
    return lua.globals(), sample, terminal


def test_terminal_reset_retains_last_live_countdown_without_exposing_it_early():
    g, sample, terminal = runtime()
    g.bm.battle.remaining_conflict_time = .9456787109375
    assert sample(1204100) == pytest.approx(945.6787109375)
    assert terminal(1204100) is None
    g.bm.battle.battle_outcome_decided = True
    g.state.finished = True
    g.bm.battle.remaining_conflict_time = -1
    assert sample(1205200) == -1
    result = dict(terminal(1205200))
    assert result == {"observed_ms": 1204100, "remaining_ms": pytest.approx(945.6787109375),
                      "deadline_ms": pytest.approx(1205045.6787109375), "expired": True,
                      "source": "countdown_deadline"}


def test_early_victory_unlimited_and_timer_extension_are_not_expiry():
    g, sample, terminal = runtime()
    sample(1000)  # no finite timer
    g.state.finished = True
    assert terminal(2000) is None
    g.state.finished = False
    g.bm.battle.remaining_conflict_time = 1
    sample(2000)
    g.bm.battle.remaining_conflict_time = 10  # an extended countdown replaces the old one
    sample(2900)
    g.bm.battle.battle_outcome_decided = True
    g.bm.battle.remaining_conflict_time = -1
    sample(3100)
    g.state.finished = True
    assert terminal(3100)["expired"] is False
    assert terminal(3100)["deadline_ms"] == 12900


def test_disabling_a_live_timer_clears_its_old_deadline():
    g, sample, terminal = runtime()
    g.bm.battle.remaining_conflict_time = 1
    sample(1000)
    g.bm.battle.remaining_conflict_time = -1
    sample(1500)  # still no decided outcome
    g.state.finished = True
    assert terminal(3000) is None
