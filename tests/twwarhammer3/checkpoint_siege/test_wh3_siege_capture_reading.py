"""Refresh a capture point before recording its existing snapshot fields."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wh3_lua import runtime


def test_fill_getter_runs_before_the_capture_snapshot_and_keeps_every_field():
    lua = runtime()
    lua.execute('''
        calls = {}
        refreshed = false
        local values = {
            Key='minor_point_supplies', ScriptId='supply1', DisplayName='Minor Supply Location',
            ['Position.x']=12, ['Position.y']=3, ['Position.z']=45,
            CurrentHolderAlliance=0, OriginalOwnerAlliance=0,
            ['HoldingArmyContext.UniqueID']=1, ['ContestingArmycontext.UniqueID']=2,
            IsContested=true, IsLocked=false, IsEnabled=true, ContributesToVictory=true,
            CanCurrentOwnerBuild=true,
        }
        common = {get_context_value = function(kind, id, expression)
            assert(kind == 'CcoBattleRoot' and id == '')
            calls[#calls+1] = expression
            local prefix = 'CapturePointList.At(0).'
            assert(string.sub(expression, 1, #prefix) == prefix)
            local field = string.sub(expression, #prefix+1)
            if field == 'FillPercent' then refreshed=true; return 0.375 end
            if field == 'CapturePercent' then return refreshed and 0.375 or 1 end
            if field == 'IsNeutral' then return not refreshed end
            assert(values[field] ~= nil, 'unexpected getter '..field)
            return values[field]
        end}
    ''')
    source = Path(__file__).with_name("reading.lua").read_text()
    # Execute the reader definitions, without unrelated vehicle/building/army mocks.
    read_capture = lua.execute(source.split("local captures = {}", 1)[0] + "\nreturn read_capture")
    row = read_capture(0)
    assert lua.globals().calls[1] == "CapturePointList.At(0).FillPercent"
    expected = {"index": 0, "key": "minor_point_supplies", "script_id": "supply1",
                "name": "Minor Supply Location", "holder_alliance": 0, "original_alliance": 0,
                "holder_army": 1, "contesting_army": 2, "fill_percent": .375,
                "capture_percent": .375, "contested": True, "locked": False, "enabled": True,
                "neutral": False, "victory": True, "owner_can_build": True}
    assert {key: value for key, value in row.items() if key != "position"} == expected
    assert dict(row["position"].items()) == {"x": 12, "y": 3, "z": 45}
