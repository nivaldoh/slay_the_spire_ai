"""Regression from the first mirror pilot: commands apply after their startup callback.

Saved evidence: at 5300 ms friendly f4 skirmish=False, but setup's synchronous cached
readback still said True. Read fresh flags in the published setup, without reissuing orders.
"""

import pytest
from wh3_lua import load_battle, runtime

from twwarhammer3.battle import benchmark, play, setup
from twwarhammer3.protocol import ProtocolError


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


def test_enemy_handover_waits_for_toggle_application_and_post_release_readback():
    lua = runtime()
    lua.execute("""
        callbacks, commands, releases = {}, {}, 0
        session={tick_ms=250}
        bm={callback=function(self, fn, delay)
            assert(delay==250)
            callbacks[#callbacks+1]=fn
        end}
        unit={values={skirmish=true},
            can_use_behaviour=function(self,key) return self.values[key]~=nil end,
            is_behaviour_active=function(self,key) return self.values[key] end}
        controller={add_units=function() end, take_control=function() end,
            change_behaviour_active=function(self,key,value) commands[key]=value end,
            release_control=function()
                assert(unit.values.skirmish==false, 'released before queued change applied')
                releases=releases+1
            end}
        state={friendly_ids={},enemy_ids={'e1'},friendly={},
            enemy={e1={unit=unit,army={create_unit_controller=function() return controller end}}},
            setup={benchmark_behaviours={}}}
    """)
    _, _, apply = load_battle(lua, "BEHAVIOURS", "get", "benchmark_behaviours")
    apply(True, True)
    assert lua.globals().releases == 0
    assert lua.globals().state["benchmark_release_pending"] == 1
    # Engine applies the queued change before its next timed callback.
    lua.globals().unit["values"]["skirmish"] = False
    lua.globals().callbacks[1]()
    assert lua.globals().releases == 1
    assert lua.globals().state["benchmark_release_pending"] == 1
    lua.globals().callbacks[2]()
    assert lua.globals().state["benchmark_release_pending"] == 0


def test_no_policy_orders_during_enemy_handover(tmp_path):
    from wh3_fixtures import CONFIG, FakeMailbox, bridge_observation

    from twwarhammer3.battle.scripted import Hold

    waiting = bridge_observation(2, 5300)
    waiting["setup"] = {"benchmark_release_pending": 1}
    ready = bridge_observation(3, 5600)
    ready["setup"] = {"benchmark_release_pending": 0}
    mailbox = FakeMailbox([bridge_observation(0, 0, phase="Loading"), waiting, ready,
                           bridge_observation(4, 5900, result="won")])
    result = play.play_episode(tmp_path / "episode", CONFIG, Hold, mailbox,
                               not_battle=None, scenario={"benchmark": benchmark.VERSION})
    assert result["start_time_ms"] == 5600
    assert [request[1] for request in mailbox.requests] == [3]


def test_setup_refuses_a_release_error_even_when_toggle_data_is_present():
    profile = setup.scenarios()[benchmark.SCENARIO]
    with pytest.raises(ProtocolError, match="enemy release failed"):
        setup.check_battle(profile, {"setup": {"benchmark_behaviours": {
            "error": "enemy release failed", "friendly": {}, "enemy": {}}}})
