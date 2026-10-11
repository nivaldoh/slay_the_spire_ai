"""Neural/PPO correctness; these tests make no original-engine performance claim."""

import copy
import io
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from spire.learning import (  # noqa: E402
    POWER_IDS,
    CandidateActorCritic,
    NeuralPolicy,
    PPOTrainer,
    Transition,
    _powers,
    complete_episode_advantages,
    decision_from_dict,
    terminal_reward,
)
from spire.protocol import decision_from_message  # noqa: E402


@pytest.fixture(autouse=True)
def cpu_threads():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def raw_state(*, session_variant=0):
    def card(identifier, cost=1):
        return {
            "id": identifier,
            "cost": cost,
            "upgrades": 0,
            "is_playable": True,
            "has_target": identifier != "Defend_R",
            "uuid": f"private-{session_variant}",
        }

    def monster(hp, damage):
        return {
            "id": "RedLouse",
            "current_hp": hp,
            "max_hp": 15,
            "block": 0,
            "intent": "ATTACK",
            "move_adjusted_damage": damage,
            "move_hits": 1,
            "is_gone": False,
            "half_dead": False,
            "powers": [{"id": "Curl Up", "amount": 4}],
        }

    return {
        "in_game": True,
        "ready_for_command": True,
        "available_commands": ["play", "end"],
        "game_state": {
            "class": "IRONCLAD",
            "ascension_level": 0,
            "room_phase": "COMBAT",
            "screen_type": "NONE",
            "floor": 1,
            "current_hp": 65,
            "max_hp": 80,
            "seed": session_variant,
            "combat_state": {
                "turn": 1,
                "hand": [card("Strike_R"), card("Strike_R"), card("Defend_R"), card("Bash", 2)],
                "draw_pile": [card("Strike_R"), card("Defend_R")],
                "discard_pile": [],
                "exhaust_pile": [],
                "monsters": [monster(15, 5), monster(8, 7)],
                "player": {"current_hp": 65, "max_hp": 80, "block": 2, "energy": 3, "powers": []},
            },
        },
    }


def decision(sequence=0, raw=None):
    return decision_from_message(raw or raw_state(), session_id="fixture", sequence=sequence)


def collect(policy, *, first_sequence=0, count=4, reward=1.2):
    transitions = []
    for index in range(count):
        state = decision(first_sequence + index)
        action = policy.choose(state)
        record = policy.choice_metadata(state.id)
        transitions.append(
            Transition(
                state,
                action.id,
                record["old_logprob"],
                record["old_value"],
                reward if index == count - 1 else 0.0,
                index == count - 1,
                record["behavior_version"],
                tuple(record["candidate_ids"]),
                record["model_sha256"],
            )
        )
    return transitions


def test_tiny_model_and_heterogeneous_padding_masks():
    model = CandidateActorCritic(seed=3)
    assert sum(parameter.numel() for parameter in model.parameters()) < 50000
    full = decision()
    end_only = replace(full, candidates=(full.candidates[-1],))
    logits, values, mask = model.batch([full, end_only])
    distribution = torch.distributions.Categorical(logits=logits)
    assert logits.shape == mask.shape == (2, len(full.candidates))
    assert values.shape == (2,)
    assert torch.isfinite(values).all() and torch.isfinite(distribution.entropy()).all()
    assert distribution.probs[1, 0] == 1
    assert torch.equal(distribution.probs[~mask], torch.zeros_like(distribution.probs[~mask]))
    assert mask[0].all() and int(mask[1].sum()) == 1


def test_sampling_keeps_duplicate_card_identities_and_never_returns_padding():
    policy = NeuralPolicy(CandidateActorCritic(seed=3), seed=19)
    state = decision()
    logits, _ = policy.model(state)
    # Two distinct Strikes against the first monster remain two equally scored candidates.
    assert logits[0] == logits[2]
    assert state.candidates[0].id != state.candidates[2].id
    sampled = {policy.choose(state).id for _ in range(100)}
    assert sampled == {candidate.id for candidate in state.candidates}
    record = policy.choice_metadata(state.id)
    probabilities = torch.distributions.Categorical(logits=logits)
    expected = probabilities.log_prob(torch.tensor(record["selected_index"]))
    assert record["old_logprob"] == float(expected.detach())
    assert len(record["candidate_ids"]) == len(state.candidates)
    with pytest.raises(ValueError, match="metadata"):
        policy.choice_metadata("some-other-decision")


def test_hand_enemy_and_candidate_permutations_preserve_semantic_scores():
    model = CandidateActorCritic(seed=11)
    original = decision()
    raw = raw_state()
    raw["game_state"]["combat_state"]["hand"].reverse()
    raw["game_state"]["combat_state"]["monsters"].reverse()
    raw["game_state"]["combat_state"]["draw_pile"].reverse()
    permuted = decision(1, raw)
    old_logits, old_value = model(original)
    new_logits, new_value = model(permuted)
    torch.testing.assert_close(old_value, new_value, rtol=0, atol=1e-7)
    for index, action in enumerate(original.candidates):
        hand_index = None if action.hand_index is None else 3 - action.hand_index
        target_index = None if action.target_index is None else 1 - action.target_index
        equivalent = next(
            i
            for i, other in enumerate(permuted.candidates)
            if (other.kind, other.hand_index, other.target_index)
            == (action.kind, hand_index, target_index)
        )
        torch.testing.assert_close(old_logits[index], new_logits[equivalent], rtol=0, atol=1e-7)
    reversed_candidates = replace(original, candidates=tuple(reversed(original.candidates)))
    reversed_logits, reversed_value = model(reversed_candidates)
    torch.testing.assert_close(reversed_logits, old_logits.flip(0))
    torch.testing.assert_close(reversed_value, old_value)


def test_seed_session_uuid_names_and_unordered_draw_positions_are_not_features():
    model = CandidateActorCritic(seed=5)
    raw = raw_state(session_variant=123987)
    raw["game_state"]["combat_state"]["draw_pile"].reverse()
    for monster in raw["game_state"]["combat_state"]["monsters"]:
        monster["name"] = "irrelevant localized name"
        monster["move_id"] = 99
    other = decision_from_message(raw, session_id="different-session", sequence=98)
    for first, second in zip(model(decision()), model(other), strict=True):
        torch.testing.assert_close(first, second)


def test_rehydrate_public_decision_preserves_and_freezes_exact_candidates():
    state = decision()
    serialized = state.to_dict()
    restored = decision_from_dict(serialized)
    assert restored == state
    serialized["observation"]["combat_state"]["player"]["energy"] = 99
    assert restored.observation["combat_state"]["player"]["energy"] == 3
    serialized = state.to_dict()
    serialized["candidates"].append(serialized["candidates"][0])
    with pytest.raises(ValueError, match="unique"):
        decision_from_dict(serialized)


def test_empty_piles_single_end_action_and_nonfinite_feature_handling():
    state = decision().to_dict()
    state["candidates"] = state["candidates"][-1:]
    combat = state["observation"]["combat_state"]
    for pile in ("hand", "draw_pile", "discard_pile", "exhaust_pile", "monsters"):
        combat[pile] = []
    model = CandidateActorCritic()
    logits, value = model(decision_from_dict(state))
    assert logits.shape == (1,) and value.shape == ()
    assert torch.isfinite(logits).all() and torch.isfinite(value)
    combat["player"]["energy"] = float("nan")
    with pytest.raises(ValueError, match="nonfinite"):
        model(decision_from_dict(state))


def test_engine_weak_power_has_a_named_feature_channel():
    fixture = json.loads(
        (Path(__file__).parent / "fixtures/engine_starter_transitions.json").read_text()
    )
    transition = next(item for item in fixture["transitions"] if item["id"] == "weak_strike")
    public = decision_from_message(transition["before"], session_id="engine-fixture", sequence=0)
    powers = _powers(public.observation["combat_state"]["player"])
    assert powers[POWER_IDS.index("Weakened")] == 0.2
    assert powers[-2:] == [0.0, 0.0]


def test_complete_episode_gae_stops_at_each_terminal():
    policy = NeuralPolicy(CandidateActorCritic())
    episode = collect(policy, count=2, reward=1)
    episode = [replace(episode[0], old_value=0.2), replace(episode[1], old_value=0.3)]
    advantage, returns = complete_episode_advantages([episode, episode])
    torch.testing.assert_close(advantage, torch.tensor([0.765, 0.7, 0.765, 0.7]))
    torch.testing.assert_close(returns, torch.tensor([0.965, 1, 0.965, 1]))
    with pytest.raises(ValueError, match="complete"):
        complete_episode_advantages([episode[:-1]])


@pytest.mark.parametrize("outcome", ["truncated", "infrastructure_failure", "interrupted"])
def test_reward_never_converts_incomplete_game_to_loss(outcome):
    with pytest.raises(ValueError, match="terminal"):
        terminal_reward(outcome, 65, 80)


def test_terminal_reward_contract():
    assert terminal_reward("won", 80, 80) == 1.25
    assert terminal_reward("won", 40, 80) == 1.125
    assert terminal_reward("lost", 0, 80) == -1
    with pytest.raises(ValueError):
        terminal_reward("won", 100, 80)


def test_ppo_changes_weights_on_complete_behavior_episodes_with_finite_metrics():
    policy = NeuralPolicy(CandidateActorCritic(seed=9), seed=22)
    trainer = PPOTrainer(policy, epochs=3, minibatch_size=3)
    actor_before = {name: value.clone() for name, value in policy.model.actor.state_dict().items()}
    episodes = [
        collect(policy, count=5, reward=1.2),
        collect(policy, first_sequence=10, count=4, reward=-1),
    ]
    result = trainer.update(episodes)
    assert result["parameters_changed"]
    assert any(
        not torch.equal(value, policy.model.actor.state_dict()[name])
        for name, value in actor_before.items()
    )
    assert result["episodes"] == 2 and result["transitions"] == 9
    assert result["optimizer_steps"] > 0 and result["update"] == 1
    assert all(
        math.isfinite(result[key])
        for key in ("loss", "policy_loss", "value_loss", "entropy", "approx_kl", "gradient_norm")
    )
    assert trainer.optimizer.state
    with pytest.raises(ValueError, match="stale"):
        trainer.update(episodes)


@pytest.mark.parametrize("corruption", ["logprob", "value", "mapping", "duplicate", "hash"])
def test_behavior_corruption_rejected_before_any_optimizer_step(corruption):
    policy = NeuralPolicy(CandidateActorCritic(seed=3))
    trainer = PPOTrainer(policy)
    episode = collect(policy)
    original_hash = policy.model_sha256
    if corruption == "logprob":
        episode[0] = replace(episode[0], old_logprob=episode[0].old_logprob + 0.01)
    elif corruption == "value":
        episode[0] = replace(episode[0], old_value=episode[0].old_value + 0.01)
    elif corruption == "mapping":
        episode[0] = replace(episode[0], candidate_ids=tuple(reversed(episode[0].candidate_ids)))
    elif corruption == "duplicate":
        episode.insert(0, episode[0])
    else:
        episode[0] = replace(episode[0], model_sha256="wrong hash")
    with pytest.raises(ValueError):
        trainer.update([episode])
    assert policy.model_sha256 == original_hash
    assert trainer.optimizer.state == {}
    assert trainer.update_count == 0


def test_policy_and_optimizer_checkpoint_resume_reproduce_samples_and_next_update():
    policy = NeuralPolicy(CandidateActorCritic(seed=4), seed=123)
    trainer = PPOTrainer(policy, epochs=2, minibatch_size=2, seed=77)
    trainer.update([collect(policy)])
    checkpoint = trainer.state_dict()
    serialized = io.BytesIO()
    torch.save(checkpoint, serialized)
    serialized.seek(0)
    restored = PPOTrainer(
        NeuralPolicy(CandidateActorCritic(seed=99)), epochs=2, minibatch_size=2, seed=0
    )
    restored.load_state_dict(torch.load(serialized, weights_only=True))
    assert restored.policy.model_sha256 == policy.model_sha256
    left = collect(policy, first_sequence=100)
    right = collect(restored.policy, first_sequence=100)
    assert [item.action_id for item in left] == [item.action_id for item in right]
    assert [item.old_logprob for item in left] == [item.old_logprob for item in right]
    first_result, second_result = trainer.update([left]), restored.update([right])
    assert first_result == second_result
    assert trainer.policy.model_sha256 == restored.policy.model_sha256
    # A state dictionary is a snapshot; subsequent updates cannot silently mutate it.
    restored.load_state_dict(checkpoint)
    assert restored.update_count == 1
    assert restored.policy.model_sha256 == first_result["before_sha256"]


def test_single_transition_and_single_candidate_update_are_finite():
    policy = NeuralPolicy(CandidateActorCritic())
    state = decision()
    state = replace(state, candidates=(state.candidates[-1],))
    action = policy.choose(state)
    metadata = policy.choice_metadata(state.id)
    transition = Transition(
        state,
        action.id,
        metadata["old_logprob"],
        metadata["old_value"],
        -1,
        True,
        metadata["behavior_version"],
        tuple(metadata["candidate_ids"]),
        metadata["model_sha256"],
    )
    result = PPOTrainer(policy, epochs=1).update([[transition]])
    assert math.isfinite(result["loss"]) and result["entropy"] == 0
    assert result["parameters_changed"]


def test_deterministic_evaluation_does_not_advance_sampling_rng_or_train():
    policy = NeuralPolicy(CandidateActorCritic(), deterministic=True)
    before = policy.generator.get_state().clone()
    actions = [policy.choose(decision()).id for _ in range(5)]
    assert len(set(actions)) == 1
    assert torch.equal(policy.generator.get_state(), before)
    with pytest.raises(ValueError, match="deterministic"):
        PPOTrainer(policy).update([collect(policy)])


def test_evaluation_sampler_reset_is_independent_of_training_history():
    policy = NeuralPolicy(CandidateActorCritic(), seed=0)
    state = decision()
    for _ in range(5):
        policy.choose(state)
    policy.reset_sampling(1024)
    first = [policy.choose(state).id for _ in range(10)]
    policy.reset_sampling(1024)
    with pytest.raises(ValueError, match="metadata"):
        policy.choice_metadata(state.id)
    second = [policy.choose(state).id for _ in range(10)]
    assert first == second


def test_configuration_and_checkpoint_versions_fail_closed():
    policy = NeuralPolicy(CandidateActorCritic())
    with pytest.raises(ValueError):
        PPOTrainer(policy, learning_rate=float("nan"))
    trainer = PPOTrainer(policy)
    state = copy.deepcopy(trainer.state_dict())
    state["reward_version"] = "another-reward"
    with pytest.raises(ValueError, match="contract"):
        trainer.load_state_dict(state)
