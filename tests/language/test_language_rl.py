"""Outcome-based language updates on CPU toy models; no game, download or GPU lease."""

import dataclasses
import math

import pytest
from test_rollout_lifecycle import combat_message

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")
peft = pytest.importorskip("peft")

from spire.language import rl  # noqa: E402
from spire.language.training import _adapter, tensor_hash  # noqa: E402
from spire.protocol import Decision, decision_from_message  # noqa: E402

CONFIG = {
    "initial_declaration": "/tmp/policy.json",
    "catalog": "/tmp/catalog.json",
    "seed": 0,
    "iterations": 2,
    "group_size": 2,
    "temperature": 1.0,
    "learning_rate": 1e-3,
    "time_budget_seconds": 600,
}


def test_rewards_and_group_advantages_follow_audited_outcomes():
    won = {"status": "won", "transitions": [{"next_observation": {"current_hp": 40, "max_hp": 80}}]}
    assert rl.episode_reward(won) == 1.125
    assert rl.episode_reward({"status": "lost", "transitions": []}) == -1.0
    with pytest.raises(ValueError):
        rl.episode_reward({"status": "interrupted", "transitions": []})
    assert rl.group_advantages([1.0, 1.0]) == [0.0, 0.0]
    assert rl.group_advantages([1.25, 0.75, -1.0]) == pytest.approx([0.9167, 0.4167, -1.3333], 1e-3)


@pytest.mark.parametrize(
    "change", [{"group_size": 1}, {"temperature": 0}, {"extra": 1}, {"iterations": True}]
)
def test_invalid_configuration_rejected(change):
    with pytest.raises(ValueError):
        rl.validate_config({**CONFIG, **change})


def test_policy_seeds_are_distinct_across_schedule():
    config = rl.validate_config(CONFIG)
    seeds = {rl.policy_seed(config, i, s, m) for i in range(10) for s in range(3) for m in range(8)}
    assert len(seeds) == 240


class FixedScorer(rl.Scorer):
    """Bypass chat templating: each decision maps to fixed token IDs."""

    def encode(self, decision):
        count = len(decision.candidates)
        return [3, 5, 7, 11], [[1 + index, 31] for index in range(count)]


@pytest.fixture
def toy():
    torch.manual_seed(0)
    config = transformers.Qwen3Config(
        vocab_size=32,
        hidden_size=16,
        intermediate_size=32,
        num_hidden_layers=1,
        num_attention_heads=2,
        num_key_value_heads=1,
        head_dim=8,
    )
    model = peft.get_peft_model(
        transformers.Qwen3ForCausalLM(config),
        peft.LoraConfig(
            r=2, lora_alpha=4, target_modules=["q_proj", "v_proj"], init_lora_weights=False
        ),
    )
    scorer = FixedScorer(model, None, 1.0)
    trainable = [p for p in model.parameters() if p.requires_grad]
    return scorer, torch.optim.AdamW(trainable, lr=5e-2)


def batch_item(scorer, decision, index, advantage):
    with torch.no_grad():
        recorded = scorer.log_policy(decision).float().tolist()
    return decision, decision.candidates[index], {"candidate_log_probs": recorded}, advantage


def adapter_hash(scorer):
    return tensor_hash(_adapter(scorer.model))


def decision():
    """Three distinct choices; the scorer only needs their count and identities."""
    original = decision_from_message(combat_message(), session_id="s", sequence=1)
    action = original.candidates[0]
    candidates = tuple(dataclasses.replace(action, id=f"{action.id}-{index}") for index in range(3))
    return Decision(original.id, original.observation, candidates)


def test_positive_advantage_raises_chosen_probability(toy):
    scorer, optimizer = toy
    current = decision()
    item = batch_item(scorer, current, 0, 1.0)
    before = math.exp(item[2]["candidate_log_probs"][0])
    result = rl.reinforce_step(scorer, optimizer, [item], expected_adapter=adapter_hash(scorer))
    with torch.no_grad():
        after = math.exp(scorer.log_policy(current)[0])
    assert result["updated"] and result["changed_elements"] > 0
    assert result["max_behavior_deviation"] < 1e-6
    assert result["adapter_after_sha256"] == tensor_hash(_adapter(scorer.model))
    assert after > before and result["mean_behavior_to_updated_kl"] > 0


def test_zero_advantages_leave_adapter_unchanged(toy):
    scorer, optimizer = toy
    current = decision()
    before = tensor_hash(_adapter(scorer.model))
    result = rl.reinforce_step(
        scorer, optimizer, [batch_item(scorer, current, 0, 0.0)], expected_adapter=before
    )
    assert not result["updated"] and result["adapter_after_sha256"] == before
    assert tensor_hash(_adapter(scorer.model)) == before


def test_behavior_from_other_weights_is_rejected_before_update(toy):
    scorer, optimizer = toy
    current = decision()
    item = batch_item(scorer, current, 0, 1.0)
    width = len(item[2]["candidate_log_probs"])
    item[2]["candidate_log_probs"] = [-math.log(width)] * width
    before = tensor_hash(_adapter(scorer.model))
    with pytest.raises(ValueError, match="Recomputed behavior"):
        rl.reinforce_step(scorer, optimizer, [item], expected_adapter=adapter_hash(scorer))
    assert tensor_hash(_adapter(scorer.model)) == before


def test_saved_adapter_hash_matches_committed_tensors(toy, tmp_path):
    from safetensors.torch import load_file

    scorer, _ = toy
    scorer.model.save_pretrained(tmp_path / "adapter")
    saved = load_file(str(tmp_path / "adapter/adapter_model.safetensors"))
    assert tensor_hash(saved) == tensor_hash(_adapter(scorer.model))


def test_learner_must_hold_the_collection_adapter_before_any_recompute(toy):
    scorer, optimizer = toy
    item = batch_item(scorer, decision(), 0, 1.0)
    with pytest.raises(ValueError, match="Learner adapter differs"):
        rl.reinforce_step(scorer, optimizer, [item], expected_adapter="0" * 64)


def test_nonfinite_recorded_behavior_cannot_pass_association(toy):
    scorer, optimizer = toy
    item = batch_item(scorer, decision(), 0, 0.0)
    item[2]["candidate_log_probs"][1] = float("nan")
    with pytest.raises(ValueError, match="Nonfinite"):
        rl.reinforce_step(scorer, optimizer, [item], expected_adapter=adapter_hash(scorer))
