"""Pure configuration boundaries exposed by the live-goal factory extraction.

Refusal-sweep regressions: unknown fields must not silently change authority, bad
partitions must fail before a model/game, and paid leaves retain their budget gates.
"""

import json
from copy import deepcopy

import pytest
from wh3_graph_goal_support import configuration

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


@pytest.mark.parametrize("provider,model,budget", [
    ("openrouter", "z-ai/glm-5.3", 50), ("anthropic", "claude-haiku-5-5", 200),
])
def test_goal_budget_may_reach_its_own_providers_allowance(
        tmp_path, monkeypatch, provider, model, budget):
    # AGENTS.md: the owner's $50 on OpenRouter ("cannot exceed $50", so $50 itself is allowed)
    # and the Anthropic key's separate $200; the OpenRouter cap is not another provider's.
    path, config, raw = configuration(tmp_path)
    raw["model"] = config["model"] = model
    path.write_text(json.dumps(raw))
    config.update(provider=provider, budget_usd=budget)
    monkeypatch.setattr(configured, "api_key", lambda p: "test-only")
    assert callable(configured.factory(path, config))


@pytest.mark.parametrize("unit_types", [[], "spear"])
def test_member_unit_types_must_be_a_nonempty_list_of_types(tmp_path, unit_types):
    # Only null means "the rest" (graph_author INSTRUCTIONS). An empty list owns nothing, and
    # text would become one-letter types at build time (tuple("spear")).
    path, config, raw = configuration(tmp_path, team=True)
    raw["members"]["line"]["unit_types"] = unit_types
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="distinct unit_types"):
        configured.load(path, config)


def test_goal_member_without_effort_uses_the_job_effort_else_low(tmp_path):
    # __main__ --effort: "the reasoning effort of a model policy named without /EFFORT", default
    # "low"; graph_author.load_template passes no job effort at all.
    path, config, raw = configuration(tmp_path)
    del raw["effort"]
    path.write_text(json.dumps(raw))
    config["effort"] = "medium"
    value, _, goals, _ = configured.load(path, config)
    assert value["effort"] == "medium" and goals == {("claude-haiku-5-5", "medium")}
    del config["effort"]
    value, _, goals, _ = configured.load(path, config)
    assert value["effort"] == "low" and goals == {("claude-haiku-5-5", "low")}


def test_configured_team_stops_direct_model_requests_after_close(tmp_path, monkeypatch):
    # Team cleanup sets the shared stop event: no new paid request may leave afterward.
    from gameai.llm import APIError

    path, config, _ = configuration(tmp_path, team=True)
    sent = []
    monkeypatch.setattr(configured, "api_key", lambda provider: "test-only")
    monkeypatch.setattr(controllers, "api_key", lambda provider: "test-only")

    def post(key, body, **kwargs):
        sent.append(body)
        return {"id": "canned"}

    monkeypatch.setattr(controllers, "post", post)
    policy = configured.factory(path, config)()
    try:
        api = policy.members["cavalry"].policy.api
        body = {"input": "canned"}
        assert api.send(body) == {"id": "canned"}
        policy.close()
        with pytest.raises(APIError, match="team closed; request not sent"):
            api.send(body)
        assert sent == [body]
    finally:
        policy.close()
