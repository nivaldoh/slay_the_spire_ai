"""Owner's 2026-11-04 placement repair: translate starts, preserve the battle."""

from twwarhammer3.battle import manual_demo, setup, support_timing


def test_current_revision_translates_all_starts_and_preserves_other_settings():
    versions = setup.scenarios()
    original, translated = versions['emp-support-timing-v1'], versions['emp-support-timing-v2']
    assert support_timing.SCENARIO == manual_demo.SCENARIO == 'emp-support-timing-v2'
    assert translated['scenario_version'] == 2
    for side in ('friendly', 'enemy'):
        before, after = original['deployment'][side], translated['deployment'][side]
        assert len(before) == len(after)
        for old, new in zip(before, after, strict=True):
            assert new == {**old, 'z': old['z'] - 160}
    assert [(u['x'], u['z']) for u in translated['deployment']['friendly']] == [
        (0, -160), (-100, -100)]
    assert [(u['x'], u['z']) for u in translated['deployment']['enemy']] == [(0, -320)]
    changed = {'name', 'scenario_version', 'deployment'}
    assert {k: v for k, v in translated.items() if k not in changed} == {
        k: v for k, v in original.items() if k not in changed}
    setup.validate_declaration(translated, {'episodes': 1, 'start_timeout': 900,
                                           'episode_timeout': 1320, 'run_timeout': 2280})
