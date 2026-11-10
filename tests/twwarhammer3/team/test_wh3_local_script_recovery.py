"""Scripted witnesses retry rejected orders without waiting for an idle-order refresh.

Contract: local_scripts._Member retries orders dropped by the engine; LocalTeam returns
each member's engine acknowledgement. A rejected order must not be remembered as applied.
The two cases distinguish rejection recovery from repeating every accepted command.
"""

from copy import deepcopy

import pytest

from twwarhammer3.battle import local_scripts


@pytest.mark.parametrize("accepted", [False, True])
def test_peer_retries_a_rejected_order_before_the_idle_retry_interval(monkeypatch, accepted):
    monkeypatch.setattr(local_scripts, "THINK_S", 0)
    member = local_scripts.PeerWitness()
    observation = {
        "time_ms": 1000,
        "friendly": [{"id": "f5", "x": 0, "z": 0, "men": 90, "state": ["idle"]}],
        "enemy": [{"id": "e1", "class": "infantry", "x": 20, "z": 0,
                   "men": 90, "state": []}],
        "command": {
            "member": "left_infantry",
            "start_points": {"left_infantry": {"z": 100}, "right_infantry": {"z": -100}},
            "rules": {"recipients": ["centre"], "text_bytes": 240},
            "received": [],
        },
    }
    first = member.decide(observation)
    assert first == [{"unit": "f5", "type": "attack", "target": "e1", "mode": "auto",
                      "run": True, "queue": False}]
    member.acknowledge({"results": [{"index": 1, "unit": "f5", "ok": accepted}]}, {})
    later = deepcopy(observation)
    later["time_ms"] += 1
    later["friendly"][0].update(state=["moving"], target="e1")
    assert member.decide(later) == ([] if accepted else first)
