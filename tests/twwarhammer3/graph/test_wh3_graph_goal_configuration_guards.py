"""Pure configuration boundaries exposed by the live-goal factory extraction.

Refusal-sweep regressions: unknown fields must not silently change authority, bad
partitions must fail before a model/game, and paid leaves retain their budget gates.
"""

import json
from copy import deepcopy

import pytest
from test_wh3_graph_goal_factory import configuration

from twwarhammer3.battle import configured, controllers, team


@pytest.mark.parametrize("change,message", [
    ("type", "needs a type"), ("graph_extra", "type and graph"),
    ("team_extra", "unknown team"), ("age", "max_age_ms"),
    ("member_extra", "unit_types and controller"), ("overlap", "distinct unit_types"),
    ("nested", "nested teams"), ("army", "invalid army owner"),
    ("rest", "multiple rest"),
])
def test_data_loader_refuses_ambiguous_authority(tmp_path, change, message):
    path, config, raw = configuration(tmp_path, team=True)
    if change == "type":
        del raw["type"]
    elif change == "graph_extra":
        raw["members"]["line"]["controller"]["arbitrary_tool"] = "x"
    elif change == "team_extra":
        raw["shared_private_memory"] = True
    elif change == "age":
        raw["max_age_ms"] = 0
    elif change == "member_extra":
        raw["members"]["line"]["other_units"] = ["foreign"]
    elif change == "overlap":
        raw["members"]["cavalry"]["unit_types"] = ["foot"]
    elif change == "nested":
        raw["members"]["cavalry"]["controller"] = deepcopy(raw)
    elif change == "army":
        raw["army_owner"] = "absent-member"
    else:
        raw["members"]["line"]["unit_types"] = None
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match=message):
        configured.load(path, config)


def test_artifact_directory_must_have_its_manifest(tmp_path):
    with pytest.raises(ValueError, match="needs manifest"):
        configured.load(tmp_path, {})


@pytest.mark.parametrize("provider,budget,message", [
    ("anthropic", None, "require --budget-usd"),
    ("openrouter", 51, "cannot exceed"),
])
def test_goal_budget_gates_precede_model_preparation(
        tmp_path, monkeypatch, provider, budget, message):
    path, config, raw = configuration(tmp_path)
    config.update(provider=provider, budget_usd=budget)
    if provider == "openrouter":
        raw["model"] = config["model"] = "z-ai/glm-5.3"
        path.write_text(json.dumps(raw))
    keys = []
    monkeypatch.setattr(configured, "api_key", lambda p: keys.append(p) or "test-only")
    with pytest.raises(ValueError, match=message):
        configured.factory(path, config)
    assert not keys


def test_builtin_team_leaf_is_closed_and_refused_inside_a_configured_team(tmp_path, monkeypatch):
    path, config, raw = configuration(tmp_path, team=True)
    raw["members"]["line"]["controller"] = {"type": "hold"}
    raw["members"]["cavalry"]["controller"] = {"type": "team_llm_rules"}
    path.write_text(json.dumps(raw))
    nested = []

    def make(*args, **kwargs):
        hold = controllers.controller_class("hold")
        policy = team.TeamPolicy({"a": (("foot",), hold()), "b": (None, hold())})
        nested.append(policy)
        return policy

    monkeypatch.setattr(controllers, "api_key", lambda provider: "test-only")
    monkeypatch.setattr(team, "ModelTeam", make)
    result = None
    try:
        with pytest.raises(ValueError, match="nested teams"):
            result = configured.factory(path, config)()
        assert len(nested) == 1 and nested[0].closed
    finally:
        if result is not None:
            result.close()
        for policy in nested:
            policy.close()
