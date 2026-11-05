"""Matched B information treatment follows the activated draw, without a live-arm leak."""

import json
from copy import deepcopy

import pytest
from wh3_fixtures import FakeSend, observation

from gameai.ledger import Ledger
from twwarhammer3.battle import llm, play, reserve, setup, team


def base(announced=False):
    return setup.scenarios()["emp-envelopment-b-announced-v2" if announced
                             else "emp-envelopment-b-v2"]


def test_announced_control_changes_only_disclosure_and_uses_identical_draws():
    live, announced = base(), base(True)
    assert {k: v for k, v in live.items() if k != "name"} == {
        k: v for k, v in announced.items() if k not in {"name", "reserve_information"}}
    assert reserve.sequence(live, 8, seed=106) == reserve.sequence(announced, 8, seed=106)


def test_public_rules_invariant_but_announced_choice_matches_same_episode_activation():
    ordinary_inputs = []
    choices = set()
    for draw in reserve.sequence(base(), 8, seed=106):
        choices.add((draw["region"], draw["side"], draw["count"]))
        raw = {"time_ms": 10000, "friendly": [], "enemy": [], "mode": {},
               "evaluation": {"reserve": {"config": draw}}, "setup": {"reserve": draw},
               "final": {"reserve": draw}}
        live = play.public(raw, reserve.episode_scenario(base(), draw))
        announced = play.public(raw, reserve.episode_scenario(base(True), draw))
        ordinary_inputs.append(live)
        public = announced["reserve_briefing"]
        assert public["rules"] == live["reserve_briefing"]["rules"]
        assert public["commitment"] == {key: draw[key]
                                         for key in ("region", "side", "count", "route",
                                                     "trigger_ms")}
        assert not set(public["commitment"]) & {"seed", "slots", "units", "latest"}
        public["commitment"]["route"][0]["x"] = 99999
        assert draw["route"][0]["x"] != 99999
    assert choices == set(reserve.CATALOGUE)
    assert all(view == ordinary_inputs[0] for view in ordinary_inputs)
    planted = deepcopy(ordinary_inputs[0])
    planted["mode"]["future_side"] = draw["side"]
    with pytest.raises(AssertionError):
        assert planted == ordinary_inputs[0]


def test_rules_describe_fixed_v1_and_conditional_v2_release_without_promising_an_arrival_time():
    v1 = reserve.briefing(setup.scenarios()["emp-envelopment-b-v1"])["rules"]
    v2 = reserve.briefing(base())["rules"]
    assert v1["trigger_ms"] == v2["trigger_ms"] == 45000
    assert v1["release"] == {"bound_ms": 165000}
    assert v2["release"] == {"bound_ms": 360000, "arrival_m": 25, "unavailable": True}
    assert "commitment" not in reserve.briefing(base())


@pytest.mark.parametrize("teammate", (False, True))
def test_actual_model_requests_receive_matching_announcement_without_live_leak(tmp_path, teammate):
    live_prompts = []
    for index, draw in enumerate(reserve.sequence(base(), 2, seed=106)):
        for announced in (False, True):
            raw = observation(time_ms=10000)
            raw["evaluation"] = {"reserve": {"config": draw, "latest": "private"}}
            view = play.public(raw, reserve.episode_scenario(base(announced), draw))
            if teammate:
                view = team.project(view, {"f2"})
            send = FakeSend(json.dumps({"orders": [], "reason": "hold", "notes": None}))
            cls = team.TeamLLM if teammate else llm.LLMPolicy
            policy = cls("gpt-6-luna", "low", Ledger(tmp_path / f"{index}-{announced}.jsonl", 1),
                         send=send)
            policy.decide(view)
            prompt = send.bodies[0]["input"][0]["content"]
            disclosure = reserve.briefing(reserve.episode_scenario(base(announced), draw))
            assert json.dumps(disclosure, sort_keys=True) in prompt
            assert draw["seed"] not in prompt and "private" not in prompt
            if not announced:
                live_prompts.append(prompt)
                assert '"commitment"' not in prompt
    assert live_prompts[0] == live_prompts[1]
