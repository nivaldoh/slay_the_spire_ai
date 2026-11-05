"""Pilot02 regression: roster is raw; decision logging strips private keys.

Reference: AGENTS.md information boundary and play.public. Shared sensor fields must
agree; a missing private field is projection, whereas two different values conflict.
"""
import copy

import pytest
from test_wh3_support_timing import ending, episode, view

from twwarhammer3.battle.support_evidence import annotate


@pytest.mark.parametrize('raw_first', [True, False])
def test_compatible_public_and_raw_observations_preserve_event_evidence(tmp_path, raw_first):
    public = view(1000)
    raw = copy.deepcopy(public)
    raw.update(setup={'unit_scale': .75}, evaluation={'friendly': {'men': 135}},
               native={'friendly': [{'id': 'f9', 'ui_id': 1001}]})
    copies = [raw, public] if raw_first else [public, raw]
    report = annotate(episode(tmp_path, [*copies, view(2000, melee=True), ending()]))
    assert report['engine_result'] == 'won'
    assert report['H'] == pytest.approx(.6)
    assert report['cue']['interval_ms'] == [1000, 2000]
    assert not report['issues']


def test_different_private_values_are_still_a_conflict(tmp_path):
    first = view()
    first['evaluation'] = {'friendly': {'men': 135}}
    second = copy.deepcopy(first)
    second['evaluation']['friendly']['men'] = 100
    report = annotate(episode(tmp_path, [first, second, ending()]))
    assert report['engine_result'] == 'won' and report['H'] is None
    assert any('conflicting observation' in issue for issue in report['issues'])
