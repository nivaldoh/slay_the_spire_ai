import pytest

from twwarhammer3.battle import commander, controllers, llm


def test_rotation_pairs_all_controllers_and_delays_in_a_repeatable_order():
    config = {"policy": "hold,skills", "delay_seconds": "0,6,10", "rotation_seed": 13}
    trials = controllers.rotation(config)
    assert trials == controllers.rotation(dict(config))
    assert len(trials) == 6 and config["episodes"] == 6
    assert {(t["policy"], t["delay_ms"]) for t in trials} == {
        (name, delay) for name in ("hold", "skills") for delay in (0, 6000, 10000)}
    config["episodes"] = 12
    repeated = controllers.rotation(config)
    assert sorted(tuple(t.items()) for t in repeated[:6]) == sorted(
        tuple(t.items()) for t in repeated[6:])


@pytest.mark.parametrize("change", [
    {"delay_seconds": "nan"}, {"delay_seconds": "-1"}, {"delay_seconds": "0,0"},
    {"policy": "typo"}, {"episodes": 0}, {"policy": "hold,skills", "episodes": 1},
])
def test_invalid_rotation_is_refused_before_launch(change):
    with pytest.raises(ValueError):
        controllers.rotation({"policy": "hold", **change})


def test_importable_controller_and_fresh_instances():
    name = "twwarhammer3.battle.scripted:AttackNearest"
    makers = controllers.factories({"policy": name})
    a, b = makers[name](), makers[name]()
    a.targets["f1"] = "e1"
    assert b.targets == {}
    record = controllers.card(name, a, {})
    assert len(record["source_sha256"]) == 64 and record["kind"] == "external"
    with pytest.raises(ValueError, match="must be a class"):
        controllers.controller_class("twwarhammer3.battle.scripted:distance")


def test_each_model_controller_gets_its_own_prompt_and_the_shared_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(controllers, "api_key", lambda: "test-only")
    assert controllers.MODEL_POLICIES == frozenset({"llm", "llm_rules", "commander"})
    config = {"policy": "llm,llm_rules,commander", "model": "gpt-6-luna", "effort": "low",
              "ledger": str(tmp_path / "spend.jsonl"), "budget_usd": 1}
    makers = controllers.factories(config)
    original, rules, planner = makers["llm"](), makers["llm_rules"](), makers["commander"]()
    assert original.api.instructions == llm.SYSTEM_PROMPT_PATH.read_text()
    assert rules.api.instructions == llm.RULES_PROMPT_PATH.read_text()
    assert planner.api.instructions == commander.PROMPT_PATH.read_text()
    assert isinstance(planner, commander.CommanderPolicy) and isinstance(rules, llm.LLMPolicy)
    assert rules.api.ledger is original.api.ledger is planner.api.ledger
    planner.close()
    rules.notes = "previous battle"
    assert makers["llm_rules"]().notes == ""
    card = controllers.card("llm_rules", rules, config)
    assert (card["kind"], card["model"], card["cost_source"]) == (
        "model", "gpt-6-luna", "WH3 ledger")
    with pytest.raises(ValueError, match="require --budget-usd"):
        controllers.factories({**config, "policy": "llm_rules", "budget_usd": None})
