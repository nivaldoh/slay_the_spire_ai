from pathlib import Path

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
    monkeypatch.setattr(controllers, "api_key", lambda provider="openai": "test-only")
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


JOB = {"model": "gpt-6-sol", "effort": "low"}  # the job's --model and --effort


@pytest.mark.parametrize("name,parts", [
    ("llm_rules", ("llm_rules", "gpt-6-sol", "low")),
    ("llm_rules@gpt-6-luna", ("llm_rules", "gpt-6-luna", "low")),
    ("commander@gpt-6-luna/medium", ("commander", "gpt-6-luna", "medium")),
    ("rush_nearest", ("rush_nearest", None, None)),
    ("twwarhammer3.battle.scripted:AttackNearest",
     ("twwarhammer3.battle.scripted:AttackNearest", None, None)),
])
def test_a_model_policy_name_can_carry_its_own_model_and_effort(name, parts):
    assert controllers.policy_parts(name, JOB) == parts


@pytest.mark.parametrize("policy,error", [
    ("hold@gpt-6-luna", "only commander, llm, llm_rules take @MODEL"),
    ("twwarhammer3.battle.scripted:AttackNearest@gpt-6-luna", "only commander"),
    ("llm_rules@gpt-6-lunar", "with a model in"), ("llm_rules@", "with a model in"),
    ("llm_rules@gpt-6-luna/minimal", "an effort in none, low"),
    ("llm_rules@gpt-6-luna/", "an effort in"),
    ("llm_rules,llm_rules@gpt-6-sol", "duplicate"),
    ("llm_rules@gpt-6-sol/low,llm_rules", "duplicate"),
    ("llm_rules@gpt-6-luna,llm_rules@gpt-6-luna/low", "duplicate"),
])
def test_bad_suffixes_and_controllers_with_the_same_effective_model_are_refused(policy, error):
    with pytest.raises(ValueError, match=error):
        controllers.rotation({**JOB, "policy": policy})


def test_one_rotation_pairs_models_and_efforts_of_the_same_policy():
    names = ["llm_rules", "llm_rules@gpt-6-luna", "llm_rules@gpt-6-luna/medium",
             "llm_rules@gpt-6-sol/high", "rush_nearest"]
    config = {**JOB, "policy": ",".join(names), "rotation_seed": 5}
    trials = controllers.rotation(config)
    assert config["episodes"] == 5 and sorted(t["policy"] for t in trials) == sorted(names)


def test_cards_and_makers_use_each_controllers_model_and_effort(tmp_path, monkeypatch):
    built = []

    class Fake:
        def __init__(self, model, effort, ledger, *, send, system_prompt, provider="openai"):
            built.append(self)
            self.model, self.effort, self.ledger = model, effort, ledger
            self.send, self.system_prompt = send, system_prompt

    class FakeCommander(Fake):
        pass

    monkeypatch.setattr(controllers, "api_key", lambda provider="openai": "test-only")
    monkeypatch.setattr(llm, "LLMPolicy", Fake)
    monkeypatch.setattr(commander, "CommanderPolicy", FakeCommander)
    config = {**JOB, "policy": "llm_rules,llm_rules@gpt-6-luna/medium,commander@gpt-6-luna,hold",
              "ledger": str(tmp_path / "spend.jsonl"), "budget_usd": 1}
    makers = controllers.factories(config)
    assert set(makers) == set(config["policy"].split(","))
    sol, luna, planner = (makers[name]() for name in config["policy"].split(",")[:3])
    assert (sol.model, sol.effort, type(sol)) == ("gpt-6-sol", "low", Fake)
    assert (luna.model, luna.effort) == ("gpt-6-luna", "medium")
    assert (planner.model, planner.effort, type(planner)) == ("gpt-6-luna", "low", FakeCommander)
    assert sol.system_prompt == luna.system_prompt == llm.RULES_PROMPT_PATH.read_text()
    assert planner.system_prompt == commander.PROMPT_PATH.read_text()
    assert sol.ledger is luna.ledger is planner.ledger and sol.send is luna.send is planner.send
    card = controllers.card("llm_rules@gpt-6-luna/medium", luna, config)
    assert (card["name"], card["kind"], card["model"], card["effort"], card["cost_source"]) == (
        "llm_rules@gpt-6-luna/medium", "model", "gpt-6-luna", "medium", "WH3 ledger")
    card = controllers.card("commander@gpt-6-luna", planner, config)
    assert (card["kind"], card["model"], card["effort"], card["timing"]) == (
        "hybrid", "gpt-6-luna", "low", "asynchronous")
    card = controllers.card("hold", makers["hold"](), config)
    assert (card["kind"], card["model"], card["effort"]) == ("scripted", None, None)


def test_recorded_versions_match_the_logs_on_main_table():
    # b12 recorded v17/v4 for v18/v5 battles because this constant lagged the log.
    log = (Path(__file__).parents[2] / "docs/twwarhammer3/log.md").read_text()
    table = log.split("## On main", 1)[1].split("\n## ", 1)[0]
    for name in ("llm", "commander"):
        row = next(line for line in table.splitlines() if line.startswith(f"| `{name}` |"))
        assert row.split("|")[2].split()[0] == controllers.VERSIONS[name]
    assert controllers.VERSIONS["llm_rules"] == controllers.VERSIONS["llm"]


def test_openrouter_rotation_keeps_vendor_model_ids_and_final_effort_suffix(tmp_path, monkeypatch):
    names = ["llm_rules@z-ai/glm-5.3", "llm_rules@moonshotai/kimi-k3/high",
             "commander@stepfun/step-5-preview"]
    config = {"provider": "openrouter", "policy": ",".join(names), "effort": "low",
              "ledger": str(tmp_path / "router.jsonl"), "budget_usd": .25}
    assert controllers.policy_parts(names[0], config) == ("llm_rules", "z-ai/glm-5.3", "low")
    assert controllers.policy_parts(names[1], config) == ("llm_rules", "moonshotai/kimi-k3", "high")
    assert len(controllers.rotation(config)) == 3
    selected = []
    monkeypatch.setattr(controllers, "api_key", lambda provider: selected.append(provider) or "key")
    makers = controllers.factories(config)
    policy = makers[names[0]]()
    assert selected == ["openrouter"] and policy.api.provider == "openrouter"
    card = controllers.card(names[0], policy, config)
    assert card["provider"] == "openrouter" and card["routing"]["provider"]["require_parameters"]
    assert config["model_routing"]["z-ai/glm-5.3"] == card["routing"]
    with pytest.raises(ValueError, match="invalid choice"):
        controllers.rotation({**config, "provider": "openai"})
    with pytest.raises(ValueError, match="cannot exceed"):
        controllers.factories({**config, "budget_usd": 51})


@pytest.mark.parametrize("policy", ["llm_rules@z-ai/glm-5.3/", "llm_rules@z-ai/glm-5.3/medium",
                                   "llm_rules@", "llm_rules@gpt-6-luna"])
def test_openrouter_rejects_unsupported_settings_before_launch(policy):
    with pytest.raises(ValueError, match="invalid choice"):
        controllers.rotation({"policy": policy, "provider": "openrouter", "effort": "low"})
