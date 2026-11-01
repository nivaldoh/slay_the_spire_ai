"""Live-goal composition, authority and budget integration; canned calls only."""

import json
from copy import deepcopy

import pytest
from test_wh3_graph_goals import spec, state

from gameai.ledger import BudgetExhausted, Ledger
from gameai.provenance import sha256
from twwarhammer3.battle import configured, controllers, graph, graph_author, graph_goals


def configuration(tmp_path, *, team=False):
    leaf = {"type": "graph_llm", "graph": spec(), "model": "claude-haiku-5-5",
            "effort": "low", "task": "Prefer a useful public target.", "max_requests": 1}
    value = {"type": "team", "members": {
        "line": {"unit_types": ["foot"], "controller": leaf},
        "cavalry": {"unit_types": None, "controller": {"type": "llm"}}}} if team else leaf
    path = tmp_path / "controller.json"
    path.write_text(json.dumps(value))
    ledger = tmp_path / "test-ledger.jsonl"
    ledger.touch()
    config = {"policy": "configured", "controller_config": str(path), "provider": "anthropic",
              "model": "claude-haiku-5-5", "effort": "low", "budget_usd": 5, "ledger": str(ledger)}
    return path, config, value


def test_goal_configuration_is_resolved_without_a_key_or_model_instance(tmp_path, monkeypatch):
    path, config, _ = configuration(tmp_path)

    def unexpected(*args, **kwargs):
        pytest.fail("data-only loading touched credentials or a model")

    monkeypatch.setattr(configured, "api_key", unexpected)
    monkeypatch.setattr(configured, "Model", unexpected)
    value, leaves, goals, artifact = configured.load(path, config)
    assert value["type"] == "graph_llm" and value["model"] == "claude-haiku-5-5"
    assert not leaves and goals == {("claude-haiku-5-5", "low")} and artifact is None
    assert config["controller_spec"] == value


def test_goal_direct_team_and_rotation_share_one_ledger_and_fresh_instances(tmp_path, monkeypatch):
    monkeypatch.setattr(configured, "api_key", lambda provider: "test-only")
    monkeypatch.setattr(controllers, "api_key", lambda provider: "test-only")
    _, config, _ = configuration(tmp_path, team=True)
    config["policy"] = "configured,llm"
    makers = controllers.factories(config)
    policy, direct, fresh = makers["configured"](), makers["llm"](), makers["configured"]()
    try:
        goal = policy.members["line"].policy
        other = policy.members["cavalry"].policy
        assert goal.api.ledger is other.api.ledger is direct.api.ledger
        goal.api.ledger.reserve(3)
        with pytest.raises(BudgetExhausted):
            direct.api.ledger.reserve(3)
        goal.api.ledger.release(3)
        new = fresh.members["line"].policy
        assert new is not goal and new.api is not goal.api and new.api.ledger is goal.api.ledger
        assert new.counter == 0 and new.hint is None and new.controller != goal.controller
        disclosure = policy.card["member_controllers"]["line"]
        assert disclosure["model"] == "claude-haiku-5-5" and disclosure["provider"] == "anthropic"
        assert disclosure["cost_source"] == "WH3 ledger"
        assert policy.card["paid_calls"] is True
        assert set(policy.card["model_prompts"]) == {"llm", "graph_llm@claude-haiku-5-5/low"}
    finally:
        policy.close()
        fresh.close()


def test_root_goal_uses_the_configured_shorter_transport(tmp_path, monkeypatch):
    monkeypatch.setattr(configured, "api_key", lambda provider: "test-only")
    sent = []

    def post(key, body, **kwargs):
        sent.append((key, body, kwargs))
        return {"id": "canned-goal", "status": "completed", "usage": {
            "input_tokens": 0, "output_tokens": 0}, "output": [{"type": "message", "content": [
                {"type": "output_text", "text": '{"target":"far","reason":"test"}'}]}]}

    monkeypatch.setattr(configured, "post", post)
    path, config, _ = configuration(tmp_path)
    policy = configured.factory(path, config)()
    try:
        policy.decide(state())
        policy.pending[1].result(timeout=2)
        policy.decide(state(2, 1100))
        assert policy.hint["target"] == "far" and len(sent) == 1
        key, body, options = sent[0]
        assert key == "test-only" and body["max_output_tokens"] == graph_goals.MAX_OUTPUT_TOKENS
        assert options == {"attempts": 1, "provider": "anthropic", "record_transport": True,
                           "timeout_s": graph_goals.READ_TIMEOUT_S}
        assert controllers.card("configured", policy, config)["cost_source"] == "WH3 ledger"
    finally:
        policy.close()


@pytest.mark.parametrize("field,value", [("max_requests", 0), ("task", 3), ("model", []),
                                        ("effort", "unknown")])
def test_bad_goal_options_fail_before_credentials(tmp_path, monkeypatch, field, value):
    path, config, raw = configuration(tmp_path)
    raw[field] = value
    path.write_text(json.dumps(raw))
    monkeypatch.setattr(configured, "api_key", lambda provider: pytest.fail("key read too early"))
    with pytest.raises(ValueError):
        configured.factory(path, config)


def test_goals_cannot_skip_a_missing_ledger(tmp_path, monkeypatch):
    path, config, _ = configuration(tmp_path)
    (tmp_path / "test-ledger.jsonl").unlink()
    monkeypatch.setattr(configured, "api_key", lambda provider: pytest.fail("key read too early"))
    with pytest.raises(FileNotFoundError, match="No spend ledger"):
        configured.factory(path, config)


@pytest.mark.parametrize("repair", [False, True])
def test_author_preserves_goal_authority_and_repairs_selectors(tmp_path, monkeypatch, repair):
    _, _, leaf = configuration(tmp_path)
    template = {"type": "team", "members": {
        "line": {"unit_types": ["foot"], "controller": leaf},
        "cavalry": {"unit_types": None, "controller": {"type": "graph", "graph": spec()}}}}
    path = tmp_path / "template.json"
    path.write_text(json.dumps(template))
    monkeypatch.setattr(configured, "api_key", lambda provider: pytest.fail("live key read"))
    replies = [json.dumps({"tasks": [{"member": name, "task": "Choose a public target."}
                                     for name in ("line", "cavalry")]})]
    if repair:
        replies.append(json.dumps({"graph_json": json.dumps({"version": graph.VERSION,
            "entry": "end", "nodes": {"end": {"op": "end", "inputs": {}, "next": {}}}})}))
    replies.extend([json.dumps({"graph_json": json.dumps(spec())})] * 2)
    requests = []

    def send(body):
        requests.append(deepcopy(body))
        return {"id": f"canned-author-{len(requests)}", "status": "completed", "usage": {
            "input_tokens": 0, "output_tokens": 0}, "output": [{"type": "message", "content": [
                {"type": "output_text", "text": replies.pop(0)}]}]}

    book = Ledger(tmp_path / "author-test-ledger.jsonl", 5)
    artifact = tmp_path / "artifact"
    manifest = graph_author.generate(path, "Control each group with its fixed graph.", artifact,
                                     book, model="claude-haiku-5-5", send=send)
    candidate, _ = graph_author.load_artifact(artifact)
    live = candidate["members"]["line"]["controller"]
    assert live == leaf and len(requests) == 3 + int(repair)
    assert manifest["authority"]["members"]["line"]["controller"] == {
        key: value for key, value in leaf.items() if key != "graph"}
    if repair:
        calls = [json.loads(s) for s in (artifact / "calls.jsonl").read_text().splitlines()]
        line = next(row for row in calls if row["role"] == "line")
        assert "select_target" in line["attempts"][0]["error"]
    # An author artifact does not let a changed planner cap hide behind its graph hash.
    live["max_requests"] = 2
    (artifact / "controller.json").write_text(json.dumps(candidate))
    manifest["controller_sha256"] = sha256(artifact / "controller.json")
    (artifact / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="authority"):
        graph_author.load_artifact(artifact)
