"""Time-weighted ownership must not depend on the number of observed snapshots."""
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / (
    "src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua")


def test_ownership_integrates_time_across_changes_and_ignores_duplicate_samples():
    lua51 = pytest.importorskip("lupa.lua51")
    lua = lua51.LuaRuntime()
    lua.execute("""
        state = {info = {player_alliance = 0, alliances = 2}, objective_totals = {}}
        function context_rows() return rows end
        function points(first, second)
            rows = {
                {"key_building", "", "0", "0", tostring(first), "false", "false", "1", "true"},
                {"minor_point", "", "0", "0", tostring(second), "false", "false", "1", "true"},
                {"not_a_goal", "", "0", "0", "0", "false", "false", "1", "false"},
            }
        end
    """)
    source = SOURCE.read_text().split("local function side(alliance_id)", 1)[1]
    function = "local function side(alliance_id)" + source.split(
        "\n-- Evaluation only:", 1)[0]
    sample = lua.execute(function + "\nreturn sample_objectives")
    lua.execute("points(0, 1)")
    sample(0)
    sample(900)
    lua.execute("points(1, 0)")
    sample(1000)
    sample(4000)
    sample(4000)  # terminal sampling at the same game time adds nothing
    totals = lua.globals().state["objective_totals"]
    assert set(totals.keys()) == {"c1", "c2"}
    assert totals["c1"]["held_ms"] == 1000 and totals["c2"]["held_ms"] == 3000
    assert totals["c1"]["observed_ms"] == totals["c2"]["observed_ms"] == 4000
    # Snapshot voting would give 2/5 for c1. Actual ownership was 1/4 of the time.
    assert totals["c1"]["held_ms"] / totals["c1"]["observed_ms"] == .25
