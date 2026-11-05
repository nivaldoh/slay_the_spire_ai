"""Regressions from independent review's counterexamples, before live verification.

Reference: owner plan: failed reads stay unknown; six primary attempts are fresh launches
with identical settings apart from the declared arm; first-ending HP is frozen.
"""
import argparse
import copy
import json
import sys

import pytest
from test_wh3_support_timing import ending, episode, view
from wh3_lua import load_battle, runtime

from twwarhammer3.battle import support_evidence as evidence
from twwarhammer3.battle import support_timing as timing


def test_contact_annotation_requires_usable_infantry(tmp_path):
    report = evidence.annotate(episode(tmp_path, [view(), view(2000, melee=True, routed=True)]))
    assert report['cue']['label'] == 'unclear'


def test_conflicting_sequence_is_unknown_but_keeps_engine_ending(tmp_path):
    first = view(2000, cavalry=True)
    second = view(2000)
    report = evidence.annotate(episode(tmp_path, [view(), first, second, ending()]))
    assert report['engine_result'] == 'won'
    assert report['H'] is None
    assert any('conflicting observation' in issue for issue in report['issues'])


def test_identical_duplicate_observations_are_harmless(tmp_path):
    first = view()
    report = evidence.annotate(episode(tmp_path, [first, copy.deepcopy(first), ending()]))
    assert not report['issues']
    assert report['H'] == pytest.approx(.6)


@pytest.mark.parametrize('stamp', [None, 500, 5001])
def test_terminal_time_must_fit_between_last_live_and_first_ending(tmp_path, stamp):
    terminal = ending()
    terminal['final']['benchmark']['time_ms'] = stamp
    report = evidence.annotate(episode(tmp_path, [view(1000), terminal]))
    assert report['engine_result'] == 'won' and report['H'] is None
    assert any('first-ending time' in issue for issue in report['issues'])


def test_frozen_terminal_can_precede_delivery_without_being_stale(tmp_path):
    terminal = ending()
    terminal['final']['benchmark']['time_ms'] = 4900
    report = evidence.annotate(episode(tmp_path, [view(4000), terminal]))
    assert report['H'] == pytest.approx(.6)
    assert not report['issues']


def test_conflicting_terminal_copies_cannot_select_the_more_favourable(tmp_path):
    terminal = ending()
    directory = episode(tmp_path, [view(), terminal])
    changed = copy.deepcopy(terminal['final']['benchmark'])
    changed['units'][0]['hp'] = 0
    (directory / 'result.json').write_text(json.dumps({'status': 'won',
        'engine_ending': {'result': 'won', 'battle_ms': 5000}, 'terminal_condition': changed}))
    report = evidence.annotate(directory)
    assert report['engine_result'] == 'won' and report['H'] is None
    assert any('conflicting terminal' in issue for issue in report['issues'])


def comparison(tmp_path, monkeypatch):
    monkeypatch.setattr(timing, 'committed_revision', lambda *a: 'frozen')
    monkeypatch.setattr(timing, 'source_fingerprints', lambda *a: {'src': 'hash'})
    path = tmp_path / 'plan.json'
    plan = timing.make_plan(path)
    for job in plan['jobs']:
        if job['arm'] not in ('contact', 'delayed'):
            continue
        directory = tmp_path / f"block-{job['block']}-{job['arm']}"
        directory.mkdir()
        start, terminal = view(), ending()
        start['battle'] = terminal['battle'] = directory.name
        for unit in terminal['final']['benchmark']['units']:
            unit['hp'] = .7 if job['arm'] == 'contact' else .4
        ep = episode(directory, [start, terminal])
        policy = job['args'][job['args'].index('--policy') + 1]
        (ep / 'result.json').write_text(json.dumps({'status': 'won', 'setup_checks': {'ok': True},
                                                  'policy': policy}))
        manifest = {key: plan[key] for key in ('source_revision', 'source_files', 'scenario')}
        manifest.update(setup_checks={'ok': True}, config={
            'policy': policy, 'episodes': 1, 'observe_ms': 1000, 'tick_ms': 250, 'interval_ms': 0,
            'start_timeout': 900, 'episode_timeout': 1320, 'run_timeout': 2280,
            'speed': 1, 'pause': False, 'delay_seconds': '0', 'record_replay': True,
            'stills': False, 'attach': False})
        (directory / 'manifest.json').write_text(json.dumps(manifest))
    assert evidence.summarize(path)['proposed_numerical_contrast'] is True
    return path, plan


@pytest.mark.parametrize('key,value', [('interval_ms', 60000), ('delay_seconds', '12'),
                                      ('observe_ms', 3000), ('stills', True)])
def test_comparison_rejects_changed_run_configuration(tmp_path, monkeypatch, key, value):
    path, _ = comparison(tmp_path, monkeypatch)
    manifest_path = tmp_path / 'block-1-delayed/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['config'][key] = value
    manifest_path.write_text(json.dumps(manifest))
    report = evidence.summarize(path)
    assert report['proposed_numerical_contrast'] is False
    assert any('config' in issue for a in report['attempts'] for issue in a.get('issues', []))


def test_comparison_rejects_missing_run_configuration(tmp_path, monkeypatch):
    path, _ = comparison(tmp_path, monkeypatch)
    mp = tmp_path / 'block-1-delayed/manifest.json'
    manifest = json.loads(mp.read_text())
    del manifest['config']
    mp.write_text(json.dumps(manifest))
    assert evidence.summarize(path)['proposed_numerical_contrast'] is False


def test_six_rows_cannot_reuse_two_launches(tmp_path, monkeypatch):
    path, plan = comparison(tmp_path, monkeypatch)
    for job in plan['jobs']:
        if job['arm'] in ('contact', 'delayed'):
            job['output'] = str(tmp_path / f"block-1-{job['arm']}")
    path.write_text(json.dumps(plan))
    report = evidence.summarize(path)
    assert report['proposed_numerical_contrast'] is False
    assert any('reused' in issue for a in report['attempts'] for issue in a.get('issues', []))


def test_copied_battle_in_distinct_directories_is_not_a_fresh_launch(tmp_path, monkeypatch):
    path, _ = comparison(tmp_path, monkeypatch)
    copied = tmp_path / 'block-2-contact/episode-0000/trace.jsonl'
    copied.write_bytes((tmp_path / 'block-1-contact/episode-0000/trace.jsonl').read_bytes())
    assert evidence.summarize(path)['proposed_numerical_contrast'] is False


@pytest.mark.parametrize('method', ['number_of_men_alive', 'unary_hitpoints', 'is_in_melee',
                                    'is_routing', 'is_shattered', 'is_moving',
                                    'bearing', 'position'])
@pytest.mark.parametrize('failure', ['missing', 'throws'])
def test_failed_core_native_getter_cannot_fabricate_support_or_geometry(method, failure):
    lua = runtime()
    lua.execute('''
        state={friendly={f1={ui_id='100',setup={}}},enemy_by_ui={}}
        BEHAVIOURS={}
        function context_rows() return {} end
        function plain(v) return v end
        unit={type=function() return 'wh_main_emp_inf_swordsmen' end,
          position=function() return {get_x=function() return 0 end,
            get_z=function() return 0 end} end,
          number_of_men_alive=function() return 60 end,
          unary_hitpoints=function() return 1 end, bearing=function() return 180 end,
          is_in_melee=function() return false end, is_routing=function() return false end,
          is_shattered=function() return false end, is_moving=function() return false end}
    ''')
    _, _, record = load_battle(lua, 'get', 'round', 'unit_record')
    assert record('f1', lua.globals().unit, True, 'infantry')['men'] == 60
    lua.globals().unit[method] = None if failure == 'missing' else lua.eval(
        "function() error('engine read failed') end")
    ok, error = lua.eval('function(f,u) return pcall(f,"f1",u,true,"infantry") end')(
        record, lua.globals().unit)
    assert ok is False and method in str(error)


def test_generated_jobs_parse_with_the_actual_cli(tmp_path, monkeypatch):
    from twwarhammer3 import __main__ as cli

    monkeypatch.setattr(timing, 'committed_revision', lambda *a: 'frozen')
    monkeypatch.setattr(timing, 'source_fingerprints', lambda *a: {})
    plan = timing.make_plan(tmp_path / 'plan.json')
    parse = argparse.ArgumentParser.parse_args

    class Parsed(Exception):
        pass

    def stop_after_parse(parser, *args, **kwargs):
        parsed = parse(parser, *args, **kwargs)
        assert parsed.stills is False and parsed.pause is False and parsed.speed == 1
        assert parsed.episodes == 1 and parsed.delay_seconds == '0'
        raise Parsed

    monkeypatch.setattr(argparse.ArgumentParser, 'parse_args', stop_after_parse)
    for job in plan['jobs']:
        monkeypatch.setattr(sys, 'argv', ['wh3', 'play', *job['args'], '--output', job['output']])
        with pytest.raises(Parsed):
            cli.main()


def test_non_object_trace_row_is_an_issue_without_erasing_ending(tmp_path):
    directory = episode(tmp_path, [view(), ending()])
    with (directory / 'trace.jsonl').open('a') as file:
        file.write('\n[]\n')
    report = evidence.annotate(directory)
    assert report['engine_result'] == 'won'
    assert any('trace row is not an object' in issue for issue in report['issues'])


def test_multiple_battles_in_one_trace_are_a_measurement_failure(tmp_path):
    terminal = ending()
    terminal['battle'] = 'different-battle'
    report = evidence.annotate(episode(tmp_path, [view(), terminal]))
    assert report['H'] is None
    assert any('multiple battles' in issue for issue in report['issues'])


def test_nonfinite_position_is_not_a_usable_route():
    lua = runtime()
    lua.execute('''
        function get(obj,key,default)
            if obj[key] ~= nil then return obj[key] end
            return default
        end
        unit={position={get_x=function() return 0/0 end, get_z=function() return 0 end},
          is_routing=false,is_shattered=false,is_in_melee=false,is_moving=false}
    ''')
    _, record = load_battle(lua, 'round', 'unit_record')
    ok, error = lua.eval('function(f,u) return pcall(f,"f1",u,true,"infantry") end')(
        record, lua.globals().unit)
    assert ok is False and 'get_x' in str(error)


def test_recorded_first_ending_also_bounds_the_frozen_hp(tmp_path):
    terminal = ending()
    terminal['final']['benchmark']['time_ms'] = 4000
    directory = episode(tmp_path, [view(), terminal])
    (directory / 'result.json').write_text(json.dumps({'status': 'won',
        'engine_ending': {'result': 'won', 'battle_ms': 2000},
        'terminal_condition': terminal['final']['benchmark']}))
    report = evidence.annotate(directory)
    assert report['engine_result'] == 'won' and report['H'] is None
    assert any('first-ending time' in issue for issue in report['issues'])
