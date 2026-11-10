"""One owner per friendly id, including class/type selectors that can overlap.

Reference: the owner-agreed team ownership contract and configured-factory reproduction.
These are offline components; no engine movement or team-strength claim.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wh3_fixtures import CONFIG, FakeMailbox
from wh3_team_fixtures import Script, Workers, state

from twwarhammer3.battle import configured, play, team


def roster(seq=1, time_ms=10000):
    observation = state(seq, time_ms)
    observation["friendly"][0]["class"] = "infantry"
    observation["friendly"][1]["class"] = "cavalry"
    return observation


def partition(selectors, workers):
    return team.TeamPolicy({name: (kinds, Script()) for name, kinds in selectors.items()},
                           executor=workers, clock=lambda: 0)


@pytest.mark.parametrize("unowned", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_overlapping_selectors_refuse_before_workers_even_if_counts_balance(unowned, reverse):
    selectors = {"class_owner": ("class:infantry",), "type_owner": (team.SWORD,)}
    if reverse:
        selectors = dict(reversed(selectors.items()))
    workers = Workers()
    policy = partition(selectors, workers)
    observation = roster()
    if not unowned:
        observation["friendly"].pop()  # overlap without an unowned unit to mask it
    try:
        with pytest.raises(team.TeamHarnessError, match="multiple members"):
            policy.decide(observation)
        assert not workers.tasks
    finally:
        policy.close()


def test_disjoint_class_and_type_selectors_still_dispatch_their_own_units():
    workers = Workers()
    policy = partition({"line": ("class:infantry",), "horse": (team.KNIGHT,)}, workers)
    try:
        assert policy.decide(roster()) == []
        assert policy.members["line"].units == {"f2"}
        assert policy.members["horse"].units == {"f1"}
        workers.finish(0)
        workers.finish(1)
        assert policy.decide(roster(2, 11000)) == [
            {"unit": "f2", "type": "move", "x": 10, "z": 20, "run": True}]
        assert [[u["id"] for u in member.policy.inputs[0]["friendly"]]
                for member in policy.members.values()] == [["f2"], ["f1"]]
    finally:
        policy.close()


def test_disjoint_assignments_still_refuse_an_unowned_unit():
    workers = Workers()
    policy = partition({"line": ("class:infantry",), "horse": (team.KNIGHT,)}, workers)
    observation = roster()
    observation["friendly"].append({"id": "f3", "type": "wh_main_emp_inf_crossbowmen",
                                    "class": "missile", "men": 90})
    try:
        with pytest.raises(team.TeamHarnessError, match="leaves friendly units unowned"):
            policy.decide(observation)
        assert not workers.tasks
    finally:
        policy.close()


@pytest.mark.parametrize("unowned", [False, True])
def test_a_later_reinforcement_cannot_create_overlapping_ownership(unowned):
    workers = Workers()
    policy = partition({"line": ("class:infantry",),
                        "mixed": (team.KNIGHT, team.SWORD)}, workers)
    first = roster()
    first["friendly"][0]["type"] = "wh_main_emp_inf_spearmen_0"
    try:
        policy.decide(first)
        workers.finish(0)
        workers.finish(1)
        later = roster(2, 11000)
        later["friendly"][0]["type"] = "wh_main_emp_inf_spearmen_0"
        later["friendly"].append({"id": "f3", "type": team.SWORD,
                                  "class": "infantry", "men": 100})
        if unowned:
            later["friendly"].append({"id": "f4", "type": "wh_main_emp_inf_crossbowmen",
                                      "class": "missile", "men": 90})
        with pytest.raises(team.TeamHarnessError, match="multiple members"):
            policy.decide(later)
        assert len(workers.tasks) == 2  # no new member input submitted
    finally:
        policy.close()


def test_configured_overlap_keeps_the_existing_harness_failure_class(tmp_path, monkeypatch):
    path = tmp_path / "mixed.json"
    path.write_text(json.dumps({"type": "team", "members": {
        "line": {"unit_types": ["class:infantry"], "controller": {"type": "hold"}},
        "other": {"unit_types": [team.SWORD], "controller": {"type": "hold"}}}}))
    workers = Workers()
    monkeypatch.setattr(team, "ThreadPoolExecutor", lambda **kwargs: workers)
    mailbox = FakeMailbox([roster(0, 0), roster(1, 1000)])
    result = play.play_episode(tmp_path / "episode", {**CONFIG, "interval_ms": 0},
                               configured.factory(path, {}), mailbox, not_battle=None)
    assert result["status"] == "unsupported_or_invalid"
    assert "multiple members" in result["error"]
    assert not workers.tasks
