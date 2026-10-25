"""Ground-fire fixture input and rejection of sources missing required siege witnesses."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_wh3_checkpoint_siege as siege
from wh3_lua import runtime


def test_ground_fire_is_capital_only_and_not_reissued_after_its_checkpoint():
    for name, case in siege.CASES.items():
        plan = siege.source_plan(name, case)
        orders = [r for r in plan["lua_at"] if r["label"] == "cannon_ground_fire"]
        if name != "capital-attacker":
            assert not orders
            continue
        assert len(orders) == 1 and orders[0]["tick"] == 200
        for changed in (False, True):
            restored = siege.restore_plan(plan, {"tick": 1100}, changed)
            assert not any(r["label"] == "cannon_ground_fire" for r in restored["lua_at"])


def test_ground_fire_uses_two_documented_arguments_and_a_100m_terrain_target():
    lua = runtime()
    lua.execute('''
        function v(x, y, z)
            return {get_x=function() return x end, get_y=function() return y end,
                    get_z=function() return z end}
        end
        local cannon = {type=function() return "wh_main_emp_art_great_cannon" end,
                        position=function() return v(10, 5, 20) end,
                        ammo_left=function() return 22 end}
        local enemy = {position=function() return v(310, 90, 420) end}
        controller = {add_units=function(_, u) assert(u == cannon) end,
                      take_control=function() controlled=true end,
                      attack_location=function(self, ...)
                          assert(select('#', ...) == 2)
                          shot, move_fast = ...
                      end}
        local friendly = {units=function() return {item=function(_, i)
                              assert(i == 8); return cannon end} end,
                          create_unit_controller=function() return controller end}
        local hostile = {units=function() return {item=function(_, i)
                             assert(i == 1); return enemy end} end}
        bm = {alliances=function() return {item=function(_, side)
                  return {armies=function() return {item=function(_, i)
                      assert(i == 1); return side == 1 and friendly or hostile end} end}
              end} end,
              battle={battle_boundaries=function() return v(-500, 0, -500), v(500, 0, 500) end,
                      get_terrain_height=function(_, x, z)
                          assert(x == 70 and z == 100); return 17 end,
                      time_elapsed_ms=function() return 20000 end}}
        twwarhammer3_json = {encode=function(value) return value end}
        checkpoint_controllers = {"existing"}
    ''')
    event = lua.execute(siege.fixture("ground_fire.lua"))
    state = lua.globals()
    assert state.controlled and state.move_fast is False
    assert (state.shot.get_x(), state.shot.get_y(), state.shot.get_z()) == (70, 17, 100)
    assert event.ammo_before == 22 and event.ms == 20000
    assert (event.target.x, event.target.y, event.target.z) == (70, 17, 100)
    assert state.checkpoint_controllers[1] == "existing"
    assert lua.eval("checkpoint_controllers[2] == controller")


def test_missing_source_witness_is_saved_and_stops_before_any_restore(tmp_path, monkeypatch):
    calls = []
    original = siege.checkpoint.AGENT
    directory = tmp_path / "capital-attacker"
    monkeypatch.setattr(siege.runtime, "user_dir", lambda: tmp_path / "user")
    monkeypatch.setattr(siege.checkpoint, "run", lambda plan, path: calls.append(path))
    monkeypatch.setattr(siege.checkpoint, "events", lambda path: [])
    monkeypatch.setattr(siege.checkpoint, "saved", lambda path, name: {"tick": 1100})
    monkeypatch.setattr(siege.land, "completeness", lambda *a, **kw: {"pass": True})
    monkeypatch.setattr(siege, "witnesses", lambda *a: {
        "checks": {"spent_ammo": False}, "pass": False})
    with pytest.raises(siege.ProtocolError, match="source siege witnesses failed"):
        siege.run_case(directory, siege.CASES["capital-attacker"])
    assert calls == [directory / "source"]
    assert siege.checkpoint.AGENT == original
    checks = json.loads((directory / "source-witnesses.json").read_text())
    assert checks["states"]["post-spell"]["tick"] == 1100
    assert checks["states"]["post-spell"]["checks"] == {"spent_ammo": False}
    assert not checks["pass"]
