"""Local command groups admit direct controllers and their declared configuration only.

Reference: communication-structure.md Composition and the shipped peer controller file.
Keep parent-specific refusals separate from validity of the same child on its own.
"""

import json
from copy import deepcopy

import pytest
from wh3_graph_fixtures import attack_graph

from twwarhammer3.battle import setup
from twwarhammer3.controllers import configured


@pytest.fixture
def local_declaration(tmp_path, monkeypatch):
    raw = json.loads((setup.SCENARIOS_PATH.parent / "controllers/cannae-peer-model.json")
                     .read_text())
    path = tmp_path / "local.json"
    config = {"scenario": "emp-envelopment-c-peer-v2", "provider": "anthropic",
              "model": "claude-haiku-5-5", "effort": "low"}

    def unexpected(*args, **kwargs):
        pytest.fail("data-only local declaration loading touched a model or credentials")

    monkeypatch.setattr(configured, "api_key", unexpected)
    monkeypatch.setattr(configured, "Model", unexpected)

    def load(value):
        path.write_text(json.dumps(value))
        return configured.load(path, dict(config))[0]

    assert load(raw)["type"] == "local_team"
    return raw, load


def test_local_declaration_refuses_an_undeclared_shared_setting(local_declaration):
    raw, load = local_declaration
    raw["shared_private_memory"] = True
    with pytest.raises(ValueError, match="local_team needs only its five members"):
        load(raw)


@pytest.mark.parametrize("kind", ["team", "local_team", "graph", "graph_llm"])
def test_valid_compositions_cannot_be_nested_inside_a_local_member(local_declaration, kind):
    raw, load = local_declaration
    if kind == "team":
        child = {"type": "team", "members": {
            "line": {"unit_types": None, "controller": {"type": "hold"}},
            "horse": {"unit_types": ["horse"], "controller": {"type": "hold"}}}}
    elif kind == "local_team":
        child = deepcopy(raw)
    else:
        child = {"type": kind, "graph": attack_graph()}
    assert load(child)["type"] == kind  # its contents are valid outside this parent
    raw["members"]["centre"] = child
    with pytest.raises(ValueError, match="local_team members must be direct local controllers"):
        load(raw)


@pytest.mark.parametrize("kind", ["commander", "team_llm_rules",
    "commander@claude-haiku-5-5/low", "team_llm_rules@claude-haiku-5-5/low"])
def test_other_model_interfaces_cannot_replace_a_local_model(local_declaration, kind):
    raw, load = local_declaration
    assert load({"type": kind}) == {"type": kind}
    raw["members"]["centre"] = {"type": kind}
    with pytest.raises(ValueError, match="local_team model members use llm or llm_rules"):
        load(raw)


@pytest.mark.parametrize("kind", ["llm", "llm_rules", "hold",
    "llm@claude-haiku-5-5/low", "llm_rules@claude-haiku-5-5/low",
    "twwarhammer3.scenarios.local_scripts:PeerWitness"])
def test_supported_direct_member_interfaces_still_load_without_models(local_declaration, kind):
    raw, load = local_declaration
    raw["members"]["centre"] = {"type": kind}
    assert load(raw)["members"]["centre"]["controller"] == {"type": kind}


@pytest.mark.parametrize("leaf,error", [
    pytest.param("llm_rules@gpt-6-luna/ultra", ValueError, id="effort-the-provider-lacks"),
    pytest.param("twwarhammer3.controllers.scripted:NoSuchPolicy", AttributeError,
                 id="class-that-does-not-exist"),
])
def test_a_team_leaf_the_job_cannot_play_is_refused_at_load(tmp_path, leaf, error):
    """configured.load checks each leaf as play checks a policy name, before anything launches.
    Wrong version: the leaf check skipped, so the composition loads and fails only later."""
    spec = {"type": "team", "members": {
        "rest": {"unit_types": None, "controller": {"type": "hold"}},
        "leaf": {"unit_types": ["wh_main_emp_cav_empire_knights"], "controller": {"type": leaf}}}}
    path = tmp_path / "team.json"
    path.write_text(json.dumps(spec))
    with pytest.raises(error):
        configured.load(path, {"provider": "openai"})
