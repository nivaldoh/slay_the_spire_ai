"""The scripted baselines in twwarhammer3/battle/scripted.py."""
import pytest
from wh3_fixtures import bridge_observation

from twwarhammer3.battle import controllers


@pytest.mark.parametrize("name,running", [("attack_nearest", False), ("rush_nearest", True)])
def test_nearest_baselines_reorder_lapsed_attacks_and_skip_the_dead(name, running):
    policy = controllers.controller_class(name)()
    first = bridge_observation(1, 1000)
    assert policy.decide(first) == [{"unit": "f1", "type": "attack", "target": "e1",
                                     "run": running}]
    assert policy.metadata()["type"] == name
    assert policy.decide(first) == []
    lapsed = bridge_observation(2, 6000)
    lapsed["friendly"][0].update(state=["idle"], target=None)
    assert [o["target"] for o in policy.decide(lapsed)] == ["e1"]
    dead = bridge_observation(3, 9000)
    dead["friendly"][0].update(men=0, state=[], target=None)
    assert policy.decide(dead) == []
