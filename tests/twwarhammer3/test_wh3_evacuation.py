import pytest
from wh3_lua import load_battle, runtime

from twwarhammer3.battle import setup


def goal_runtime():
    lua = runtime()
    lua.execute('''
        units = {
            f7 = {men = 30, x = 0, z = 0}, f8 = {men = 30, x = 100, z = 0}
        }
        state = {friendly = {}, custom = {kind = "battery_evacuation", status = "pending",
            zone = {x = 0, z = 0, radius = 20}, deadline_ms = 900000,
            assets = {{id = "f7"}, {id = "f8"}}}}
        for id, u in pairs(units) do
            function u:number_of_men_alive() return self.men end
            function u:is_routing() return self.routing or false end
            function u:is_shattered() return self.shattered or false end
            function u:is_leaving_battle() return false end
            function u:is_deployed() return true end
            function u:position()
                local unit = self
                return {get_x = function() return unit.x end, get_z = function() return unit.z end}
            end
            state.friendly[id] = {unit = u}
        end
        endings = {}
        bm = {local_alliance = function() return 1 end,
              battle = {force_battle_end = function(self, winner, reason, immediate, force)
                  endings[#endings + 1] = {winner, reason, immediate, force}
              end}}
    ''')
    get, clean_error, sample = load_battle(lua, "get", "clean_error", "sample_custom")
    return lua, sample


def test_partial_extraction_does_not_secure_or_remove_an_asset():
    lua, sample = goal_runtime()
    sample(1000)
    assert lua.eval('state.custom.extracted') == 1
    assert lua.eval('state.custom.status') == 'pending'
    lua.execute('units.f7.x = 100; units.f8.x = 0')
    sample(2000)
    assert lua.eval('state.custom.extracted') == 1
    assert lua.eval('#endings') == 0
    lua.execute('units.f7.x = 0')
    sample(3000)
    assert lua.eval('state.custom.status') == 'success'
    assert lua.eval('endings[1][1]') == 1
    assert lua.eval('endings[1][2]') == 'scripted'
    sample(4000)
    assert lua.eval('#endings') == 1


@pytest.mark.parametrize('change, now, native, status, reason, endings', [
    ('units.f7.men = 0', 1000, None, 'failed', 'asset_lost', 1),
    ('', 900000, None, 'failed', 'deadline', 1),
    ('', 1000, 'won', 'success', 'native_ending', 0),
    ('units.f7.men = 0', 1000, 'won', 'failed', 'asset_lost', 0),
    ('', 1000, 'lost', 'failed', 'native_ending', 0),
    ('', 1000, 'draw', 'failed', 'native_ending', 0),
    ('', 900001, 'won', 'failed', 'native_ending', 0),
    ('units.f8.x = 0; units.f8.routing = true', 1000, None, 'pending', None, 0),
])
def test_custom_endings_and_native_early_endings(change, now, native, status, reason, endings):
    lua, sample = goal_runtime()
    lua.execute(change)
    sample(now, native)
    assert lua.eval('state.custom.status') == status
    assert lua.eval('state.custom.reason') == reason
    assert lua.eval('#endings') == endings
    if status == 'failed' and endings:
        assert lua.eval('endings[1][1]') == 2


def test_new_battle_does_not_reuse_custom_progress():
    lua, sample = goal_runtime()
    lua.execute('units.f8.x = 0')
    sample(1000)
    fresh, sample = goal_runtime()
    sample(1000)
    assert fresh.eval('state.custom.status') == 'pending'
    assert fresh.eval('#endings') == 0


@pytest.mark.parametrize('mutation', [
    lambda goal: goal.update(assets=['f7', 'f7']),
    lambda goal: goal.update(assets=['f7', 'e8']),
    lambda goal: goal.update(deadline_s=1200),
    lambda goal: goal['zone'].update(x=float('nan')),
    lambda goal: goal['zone'].update(radius=0),
    lambda goal: goal['deployment']['enemy'].append(goal['deployment']['enemy'][0]),
])
def test_invalid_authored_objectives_are_rejected(mutation):
    scenario = setup.scenarios()['emp-battery-wef-evacuation']
    mutation(scenario['custom'])
    with pytest.raises(ValueError):
        setup.validate_custom(scenario)


def test_engine_ending_exception_is_reported_without_fabricating_a_game_result():
    lua, sample = goal_runtime()
    lua.execute('units.f8.x = 0; bm.battle.force_battle_end = function() error("unavailable") end')
    sample(1000)
    assert 'unavailable' in lua.eval('state.custom.ending_error')
    assert lua.eval('state.result') is None
