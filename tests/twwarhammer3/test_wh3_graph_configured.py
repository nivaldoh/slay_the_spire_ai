"""Composition, frozen inputs and paid-leaf accounting through normal factories."""

import json

import pytest
from test_wh3_graph import move_graph

from gameai.ledger import BudgetExhausted
from twwarhammer3.battle import controllers, graph, llm, team


def specification(a, b):
    return {"type": "team", "army_owner": "line", "members": {
        "line": {"unit_types": None, "controller": a},
        "cavalry": {"unit_types": [team.KNIGHT], "controller": b}}}


def write_config(tmp_path, spec, **options):
    path = tmp_path / "controller.json"
    path.write_text(json.dumps(spec))
    return {"policy": "configured", "controller_config": str(path), **options}


def test_graph_and_script_can_be_swapped_and_factory_freezes_each_episode(tmp_path):
    config = write_config(tmp_path, specification({"type": "graph", "graph": move_graph()},
                                                 {"type": "hold"}))
    assert controllers.rotation(config)[0]["policy"] == "configured"
    make = controllers.factories(config)["configured"]
    a, b = make(), make()
    try:
        assert isinstance(a, team.TeamPolicy)
        assert isinstance(a.members["line"].policy, graph.GraphPolicy)
        assert a.members["line"].policy is not b.members["line"].policy
        assert a.card["member_controllers"]["line"]["disclosure"]["catalog"] == "wh3-skills-v1"
        assert a.card["configuration"] == config["controller_spec"]
        assert controllers.card("configured", a, config)["kind"] == "composed"
        # File edits after preparation cannot change an episode's frozen graph.
        (tmp_path / "controller.json").write_text('{"type":"hold"}')
        assert make().card["configuration"] == a.card["configuration"]
    finally:
        a.close()
        b.close()


def test_two_model_types_share_budget_and_cannot_skip_missing_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(controllers, "api_key", lambda provider: "test-only")
    config = write_config(tmp_path, specification({"type": "llm_rules"}, {"type": "llm"}),
                          provider="anthropic", model="claude-haiku-5-5", effort="low",
                          ledger=str(tmp_path / "spend.jsonl"), budget_usd=5)
    with pytest.raises(FileNotFoundError, match="No spend ledger"):
        controllers.factories(config)
    (tmp_path / "spend.jsonl").touch()
    make = controllers.factories(config)["configured"]
    policy, fresh = make(), make()
    try:
        a, b = (m.policy for m in policy.members.values())
        assert isinstance(a, llm.LLMPolicy) and isinstance(b, llm.LLMPolicy)
        assert a.api.ledger is b.api.ledger
        assert a.api.provider == b.api.provider == "anthropic"
        assert policy.card["paid_calls"] is True
        assert set(policy.card["model_prompts"]) == {"llm", "llm_rules"}
        a.notes = "old episode"
        assert fresh.members["line"].policy.notes == ""
        assert controllers.card("configured", policy, config)["cost_source"] == "WH3 ledger"
    finally:
        policy.close()
        fresh.close()


def test_composed_and_direct_model_policies_share_inflight_reservations(tmp_path, monkeypatch):
    monkeypatch.setattr(controllers, "api_key", lambda provider: "test-only")
    path = tmp_path / "spend.jsonl"
    path.touch()
    config = write_config(tmp_path, {"type": "llm_rules"},
                          provider="anthropic", model="claude-haiku-5-5", effort="low",
                          ledger=str(path), budget_usd=5)
    config["policy"] = "configured,llm"
    makers = controllers.factories(config)
    a, b = makers["configured"](), makers["llm"]()
    a.api.ledger.reserve(3)
    with pytest.raises(BudgetExhausted):
        b.api.ledger.reserve(3)
    a.api.ledger.release(3)
    a.api.ledger.charge(3, synthetic=True)
    with pytest.raises(BudgetExhausted):
        b.api.ledger.reserve(3)


@pytest.mark.parametrize("spec", [
    {"type": "configured"}, {"type": "hold,skills"}, {"type": "graph", "graph": {}},
    {"type": "team", "members": {}},
    specification({"type": "hold", "unexpected": 1}, {"type": "hold"}),
])
def test_bad_compositions_fail_before_game_start(tmp_path, spec):
    with pytest.raises(ValueError):
        controllers.factories(write_config(tmp_path, spec))
