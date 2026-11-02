"""Regression from the first mirror pilot: commands apply after their startup callback.

Saved evidence: at 5300 ms friendly f4 skirmish=False, but setup's synchronous cached
readback still said True. Read fresh flags in the published setup, without reissuing orders.
"""

from wh3_lua import load_battle, runtime


def test_setup_toggle_evidence_uses_publish_time_readback():
    lua = runtime()
    lua.execute("""
        state = {seq=0, friendly_ids={}, enemy_ids={}, army_abilities={},
                 setup={benchmark_behaviours={friendly={f4={skirmish=true}}}}}
        session = {benchmark='mirror-v1'}
        reads=0
        function benchmark_behaviours(apply)
            assert(apply==false, 'readback must not reissue startup changes')
            reads=reads+1
            return {friendly={f4={skirmish=false}}}
        end
        bm={get_current_phase_name=function() return 'Deployed' end,
            get_first_non_player_army=function() return {} end}
        function get(unit,key,default) return default end
        function player_army() return {} end
        function battle_speed() return 1 end
        function sample_countdown() return 1199700 end
        function terminal_countdown() return nil end
        function evaluation() return {} end
        function mode_section() return {} end
    """)
    read = load_battle(lua, "observation")
    record = read(5300)
    assert record["setup"]["benchmark_behaviours"]["friendly"]["f4"]["skirmish"] is False
    assert lua.globals().reads == 1
    # Once ordinary controller orders have begun, setup evidence is no longer published.
    lua.globals().state["applied"] = lua.table_from({"request": "r1"})
    assert read(5600)["setup"] is None
    assert lua.globals().reads == 1
    # A fresh read must never hide a startup application/release failure.
    lua.globals().state["applied"] = None
    lua.globals().state["setup"]["benchmark_behaviours"] = lua.table_from({
        "error": "enemy release_control failed"})
    error_record = read(5900)
    assert error_record["setup"]["benchmark_behaviours"]["error"] == "enemy release_control failed"
    assert lua.globals().reads == 1
