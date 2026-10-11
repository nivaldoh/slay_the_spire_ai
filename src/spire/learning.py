"""Small public-information candidate scorer and complete-episode PPO on CPU.

The runner owns engine interaction, trace auditing, budgets and checkpoint files.
This module never reads raw bridge observations or reconstructs game mechanics.
"""

from __future__ import annotations

import copy
import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import torch
from torch import Tensor, nn
from torch.distributions import Categorical
from torch.nn import functional as F

from spire.protocol import OBSERVATION_CONTRACT, Action, Decision, validate_action

ENCODER_VERSION = "starter-set-scorer-v1"
REWARD_VERSION = "combat-terminal-health-v1"
LEARNER_VERSION = "complete-episode-ppo-v1"
CARD_IDS = ("Strike_R", "Defend_R", "Bash")
POWER_IDS = (
    "Strength",
    "Dexterity",
    "Weakened",
    "Vulnerable",
    "Frail",
    "Curl Up",
    "Ritual",
    "Artifact",
    "Metallicize",
    "Barricade",
)
INTENTS = (
    "ATTACK",
    "ATTACK_BUFF",
    "ATTACK_DEBUFF",
    "ATTACK_DEFEND",
    "BUFF",
    "DEBUFF",
    "STRONG_DEBUFF",
    "DEFEND",
    "DEFEND_BUFF",
    "DEFEND_DEBUFF",
    "ESCAPE",
    "SLEEP",
    "STUN",
    "NONE",
    "UNKNOWN",
    "DEBUG",
    "MAGIC",
)
CARD_DIM = len(CARD_IDS) + 1 + 6
POWER_DIM = len(POWER_IDS) + 2
MONSTER_DIM = 7 + len(INTENTS) + 1 + POWER_DIM
PLAYER_DIM = 7 + POWER_DIM


def _scalar(value: Any, scale: float = 1.0) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite public observation feature")
    return number / scale


def _one_hot(value: str, vocabulary: tuple[str, ...]) -> list[float]:
    return [float(value == item) for item in vocabulary] + [float(value not in vocabulary)]


def _powers(creature: Mapping) -> list[float]:
    result = [0.0] * POWER_DIM
    for power in creature.get("powers", ()):
        identifier = power.get("id")
        if identifier in POWER_IDS:
            result[POWER_IDS.index(identifier)] += _scalar(power.get("amount", 0), 10)
        else:
            result[-2] += _scalar(power.get("amount", 0), 10)
            result[-1] += 0.1
    return result


def _card(card: Mapping) -> list[float]:
    return _one_hot(card.get("id"), CARD_IDS) + [
        _scalar(card.get("cost", 0), 3),
        _scalar(card.get("upgrades", 0), 3),
        float(bool(card.get("is_playable"))),
        float(bool(card.get("has_target"))),
        float(bool(card.get("exhausts"))),
        float(bool(card.get("ethereal"))),
    ]


def _monster(monster: Mapping) -> list[float]:
    return (
        [
            _scalar(monster.get("current_hp", 0), 100),
            _scalar(monster.get("max_hp", 0), 100),
            _scalar(monster.get("block", 0), 30),
            _scalar(monster.get("move_adjusted_damage", 0), 30),
            _scalar(monster.get("move_hits", 0), 5),
            float(bool(monster.get("is_gone"))),
            float(bool(monster.get("half_dead"))),
        ]
        + _one_hot(monster.get("intent"), INTENTS)
        + _powers(monster)
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def decision_from_dict(data: Mapping) -> Decision:
    """Rehydrate an already-audited public Decision, never a raw bridge message."""
    decision = Decision(
        str(data["id"]),
        _freeze(data["observation"]),
        tuple(Action(**dict(candidate)) for candidate in data["candidates"]),
    )
    if decision.observation.get("contract") != OBSERVATION_CONTRACT:
        raise ValueError("observation contract mismatch")
    identifiers = [candidate.id for candidate in decision.candidates]
    if len(set(identifiers)) != len(identifiers) or not identifiers:
        raise ValueError("candidate identities must be unique and nonempty")
    for candidate in decision.candidates:
        validate_action(decision, candidate)
    return decision


class CandidateActorCritic(nn.Module):
    """Shared set encoders and one score per exact legal action candidate."""

    def __init__(self, seed: int = 0):
        super().__init__()
        # Initialization must not perturb the runner's global torch RNG.
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.cards = nn.Sequential(nn.Linear(CARD_DIM, 16), nn.Tanh())
            self.monsters = nn.Sequential(nn.Linear(MONSTER_DIM, 16), nn.Tanh())
            self.context = nn.Sequential(nn.Linear(5 * 16 + PLAYER_DIM, 64), nn.Tanh())
            self.actor = nn.Sequential(nn.Linear(64 + 16 + 16 + 2, 32), nn.Tanh(), nn.Linear(32, 1))
            self.critic = nn.Sequential(nn.Linear(64, 32), nn.Tanh(), nn.Linear(32, 1))
            nn.init.orthogonal_(self.actor[-1].weight, gain=0.01)
            nn.init.zeros_(self.actor[-1].bias)

    def forward(self, decision: Decision) -> tuple[Tensor, Tensor]:
        if decision.observation.get("contract") != OBSERVATION_CONTRACT:
            raise ValueError("observation contract mismatch")
        if not decision.candidates:
            raise ValueError("cannot score an empty candidate set")
        if next(self.parameters()).device.type != "cpu":
            raise ValueError("this initial learner deliberately supports CPU only")
        combat = decision.observation["combat_state"]
        player = combat["player"]
        piles = {}
        for name in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
            features = torch.tensor([_card(card) for card in combat[name]], dtype=torch.float32)
            piles[name] = self.cards(features.reshape(-1, CARD_DIM))
        features = torch.tensor(
            [_monster(item) for item in combat["monsters"]], dtype=torch.float32
        )
        monsters = self.monsters(features.reshape(-1, MONSTER_DIM))
        player_features = torch.tensor(
            [
                _scalar(player.get("current_hp", 0), 100),
                _scalar(player.get("max_hp", 0), 100),
                _scalar(player.get("block", 0), 30),
                _scalar(player.get("energy", 0), 3),
                _scalar(combat.get("turn", 0), 10),
                _scalar(combat.get("cards_discarded_this_turn", 0), 10),
                _scalar(combat.get("times_damaged", 0), 10),
                *_powers(player),
            ],
            dtype=torch.float32,
        )
        context = self.context(
            torch.cat(
                [
                    *(pile.sum(dim=0) / 10 for pile in piles.values()),
                    monsters.sum(dim=0) / 5,
                    player_features,
                ]
            )
        )
        zero = torch.zeros(16)
        candidates = []
        for candidate in decision.candidates:
            if candidate.kind == "end":
                card, target, kind = zero, zero, [0.0, 1.0]
            elif candidate.kind == "play":
                if type(candidate.hand_index) is not int or not (
                    0 <= candidate.hand_index < len(piles["hand"])
                ):
                    raise ValueError("candidate hand index is invalid")
                if combat["hand"][candidate.hand_index].get("id") != candidate.card_id:
                    raise ValueError("candidate card identity does not match hand")
                card = piles["hand"][candidate.hand_index]
                target = zero
                if candidate.target_index is not None:
                    if type(candidate.target_index) is not int or not (
                        0 <= candidate.target_index < len(monsters)
                    ):
                        raise ValueError("candidate target index is invalid")
                    target = monsters[candidate.target_index]
                kind = [1.0, 0.0]
            else:
                raise ValueError("unsupported action kind")
            candidates.append(torch.cat([context, card, target, torch.tensor(kind)]))
        logits = self.actor(torch.stack(candidates)).squeeze(-1)
        value = self.critic(context).squeeze(-1)
        if not torch.isfinite(logits).all() or not torch.isfinite(value):
            raise ValueError("model produced nonfinite output")
        return logits, value

    def batch(self, decisions: Sequence[Decision]) -> tuple[Tensor, Tensor, Tensor]:
        if not decisions:
            raise ValueError("cannot score an empty batch")
        outputs = [self(decision) for decision in decisions]
        width = max(len(logits) for logits, _ in outputs)
        logits = torch.stack(
            [F.pad(row, (0, width - len(row)), value=-math.inf) for row, _ in outputs]
        )
        mask = (
            torch.arange(width)[None, :]
            < torch.tensor([len(decision.candidates) for decision in decisions])[:, None]
        )
        return logits, torch.stack([value for _, value in outputs]), mask


def model_sha256(model: nn.Module) -> str:
    digest = hashlib.sha256(ENCODER_VERSION.encode())
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode())
        digest.update(str(tuple(tensor.shape)).encode())
        # byte view avoids a NumPy runtime dependency.
        digest.update(
            bytes(tensor.detach().cpu().contiguous().view(torch.uint8).flatten().tolist())
        )
    return digest.hexdigest()


class NeuralPolicy:
    name = "neural"

    def __init__(
        self,
        model: CandidateActorCritic,
        *,
        seed: int = 0,
        deterministic: bool = False,
        behavior_version: str = "initial",
    ):
        self.model = model
        self.deterministic = deterministic
        self.behavior_version = behavior_version
        self.generator = torch.Generator(device="cpu").manual_seed(seed)
        self._last: dict | None = None

    @property
    def model_sha256(self) -> str:
        return model_sha256(self.model)

    def reset_sampling(self, seed: int) -> None:
        """Start an evaluation episode's sampler independently of training history."""
        self.generator.manual_seed(seed)
        self._last = None

    def choose(self, decision: Decision) -> Action:
        with torch.no_grad():
            logits, value = self.model(decision)
            distribution = Categorical(logits=logits)
            index = (
                int(logits.argmax())
                if self.deterministic
                else int(torch.multinomial(distribution.probs, 1, generator=self.generator).item())
            )
            action = decision.candidates[index]
            self._last = {
                "decision_id": decision.id,
                "selected_action_id": action.id,
                "selected_index": index,
                "candidate_ids": [item.id for item in decision.candidates],
                "old_logprob": float(distribution.log_prob(torch.tensor(index))),
                "old_value": float(value),
                "model_sha256": self.model_sha256,
                "behavior_version": self.behavior_version,
                "encoder_version": ENCODER_VERSION,
                "observation_contract": OBSERVATION_CONTRACT,
                "deterministic": self.deterministic,
            }
        return action

    def choice_metadata(self, decision_id: str) -> dict:
        if self._last is None or self._last["decision_id"] != decision_id:
            raise ValueError("no choice metadata for that decision")
        return copy.deepcopy(self._last)

    def state_dict(self) -> dict:
        return copy.deepcopy(
            {
                "encoder_version": ENCODER_VERSION,
                "observation_contract": OBSERVATION_CONTRACT,
                "model": self.model.state_dict(),
                "generator": self.generator.get_state(),
                "deterministic": self.deterministic,
                "behavior_version": self.behavior_version,
            }
        )

    def load_state_dict(self, state: Mapping) -> None:
        if state["encoder_version"] != ENCODER_VERSION or (
            state["observation_contract"] != OBSERVATION_CONTRACT
        ):
            raise ValueError("checkpoint encoder or observation contract mismatch")
        self.model.load_state_dict(state["model"], strict=True)
        self.generator.set_state(state["generator"])
        self.deterministic = bool(state["deterministic"])
        self.behavior_version = state["behavior_version"]
        self._last = None


@dataclass(frozen=True)
class Transition:
    decision: Decision
    action_id: str
    old_logprob: float
    old_value: float
    reward: float
    terminated: bool
    behavior_version: str
    candidate_ids: tuple[str, ...]
    model_sha256: str


def terminal_reward(outcome: str, ending_hp: float, max_hp: float) -> float:
    """Engine-reported postcombat HP includes Burning Blood healing."""
    if outcome not in ("won", "lost"):
        raise ValueError("training reward requires a true engine terminal outcome")
    if not math.isfinite(max_hp) or max_hp <= 0 or not math.isfinite(ending_hp):
        raise ValueError("invalid terminal health")
    if not 0 <= ending_hp <= max_hp:
        raise ValueError("terminal health outside its declared range")
    return 1.0 + 0.25 * ending_hp / max_hp if outcome == "won" else -1.0


def complete_episode_advantages(
    episodes: Sequence[Sequence[Transition]],
    *,
    gamma: float = 1.0,
    gae_lambda: float = 0.95,
) -> tuple[Tensor, Tensor]:
    advantages, returns = [], []
    for episode in episodes:
        if not episode or not episode[-1].terminated or any(t.terminated for t in episode[:-1]):
            raise ValueError("PPO requires complete episodes with one final true termination")
        next_value, advantage = 0.0, 0.0
        episode_advantages = []
        for transition in reversed(episode):
            delta = transition.reward + gamma * next_value - transition.old_value
            advantage = delta + gamma * gae_lambda * advantage
            episode_advantages.append(advantage)
            next_value = transition.old_value
        episode_advantages.reverse()
        advantages.extend(episode_advantages)
        returns.extend(a + t.old_value for a, t in zip(episode_advantages, episode, strict=True))
    return torch.tensor(advantages, dtype=torch.float32), torch.tensor(returns, dtype=torch.float32)


class PPOTrainer:
    """One frozen behavior version per update, no old replay or interrupted episodes."""

    def __init__(
        self,
        policy: NeuralPolicy,
        *,
        learning_rate: float = 3e-4,
        epochs: int = 4,
        minibatch_size: int = 32,
        gamma: float = 1.0,
        gae_lambda: float = 0.95,
        clip_coef: float = 0.2,
        entropy_coef: float = 0.01,
        value_coef: float = 0.5,
        max_grad_norm: float = 0.5,
        target_kl: float = 0.02,
        seed: int = 0,
    ):
        self.policy = policy
        self.config = dict(
            learning_rate=learning_rate,
            epochs=epochs,
            minibatch_size=minibatch_size,
            gamma=gamma,
            gae_lambda=gae_lambda,
            clip_coef=clip_coef,
            entropy_coef=entropy_coef,
            value_coef=value_coef,
            max_grad_norm=max_grad_norm,
            target_kl=target_kl,
        )
        if (
            type(epochs) is not int
            or type(minibatch_size) is not int
            or epochs < 1
            or minibatch_size < 1
            or learning_rate <= 0
            or max_grad_norm <= 0
        ):
            raise ValueError("invalid PPO update budget or optimizer configuration")
        if any(not math.isfinite(float(value)) for value in self.config.values()):
            raise ValueError("PPO configuration must be finite")
        if not (0 <= gamma <= 1 and 0 <= gae_lambda <= 1 and 0 < clip_coef < 1):
            raise ValueError("invalid PPO discount, GAE or clip coefficient")
        if entropy_coef < 0 or value_coef < 0 or target_kl <= 0:
            raise ValueError("invalid PPO loss coefficient or KL bound")
        self.optimizer = torch.optim.Adam(policy.model.parameters(), lr=learning_rate, eps=1e-5)
        self.generator = torch.Generator(device="cpu").manual_seed(seed)
        self.update_count = 0

    def update(self, episodes: Sequence[Sequence[Transition]]) -> dict:
        transitions = [transition for episode in episodes for transition in episode]
        if not transitions:
            raise ValueError("cannot update without transitions")
        if self.policy.deterministic:
            raise ValueError("PPO cannot train from deterministic evaluation behavior")
        advantages, returns = complete_episode_advantages(
            episodes,
            gamma=self.config["gamma"],
            gae_lambda=self.config["gae_lambda"],
        )
        if not torch.isfinite(advantages).all() or not torch.isfinite(returns).all():
            raise ValueError("nonfinite rewards or behavior values")
        before_hash = self.policy.model_sha256
        seen = set()
        # Validate the entire batch before optimizer state or parameters are touched.
        for transition in transitions:
            decision = transition.decision
            if decision.id in seen:
                raise ValueError("duplicate decision in PPO batch")
            seen.add(decision.id)
            if transition.candidate_ids != tuple(action.id for action in decision.candidates):
                raise ValueError("candidate mapping differs from behavior collection")
            if transition.behavior_version != self.policy.behavior_version or (
                transition.model_sha256 != before_hash
            ):
                raise ValueError("stale or mixed behavior policies in PPO batch")
            action = validate_action(decision, transition.action_id)
            index = decision.candidates.index(action)
            with torch.no_grad():
                logits, value = self.policy.model(decision)
                logprob = float(Categorical(logits=logits).log_prob(torch.tensor(index)))
            if not math.isclose(logprob, transition.old_logprob, rel_tol=0, abs_tol=1e-6):
                raise ValueError("behavior log probability does not match frozen policy")
            if not math.isclose(float(value), transition.old_value, rel_tol=0, abs_tol=1e-6):
                raise ValueError("behavior value does not match frozen policy")
            if not transition.terminated and transition.reward != 0:
                raise ValueError("this reward contract permits only terminal rewards")
        old_logprobs = torch.tensor([t.old_logprob for t in transitions])
        advantages = (advantages - advantages.mean()) / (advantages.std(unbiased=False) + 1e-8)
        metrics = []
        stop = False
        for _ in range(self.config["epochs"]):
            order = torch.randperm(len(transitions), generator=self.generator).tolist()
            for offset in range(0, len(order), self.config["minibatch_size"]):
                indices = order[offset : offset + self.config["minibatch_size"]]
                samples = [transitions[index] for index in indices]
                logits, values, _ = self.policy.model.batch([item.decision for item in samples])
                distribution = Categorical(logits=logits)
                actions = torch.tensor(
                    [item.candidate_ids.index(item.action_id) for item in samples]
                )
                logratio = distribution.log_prob(actions) - old_logprobs[indices]
                ratio = logratio.exp()
                approximate_kl = ((ratio - 1) - logratio).mean()
                if not torch.isfinite(approximate_kl):
                    raise ValueError("nonfinite PPO likelihood ratio")
                if float(approximate_kl.detach()) > self.config["target_kl"]:
                    stop = True
                    break
                clipped = ratio.clamp(1 - self.config["clip_coef"], 1 + self.config["clip_coef"])
                policy_loss = torch.maximum(
                    -advantages[indices] * ratio, -advantages[indices] * clipped
                ).mean()
                value_loss = 0.5 * (values - returns[indices]).square().mean()
                entropy = distribution.entropy().mean()
                loss = (
                    policy_loss
                    + self.config["value_coef"] * value_loss
                    - (self.config["entropy_coef"] * entropy)
                )
                if not torch.isfinite(loss):
                    raise ValueError("nonfinite PPO loss")
                self.optimizer.zero_grad(set_to_none=True)
                loss.backward()
                gradient_norm = nn.utils.clip_grad_norm_(
                    self.policy.model.parameters(),
                    self.config["max_grad_norm"],
                    error_if_nonfinite=True,
                )
                self.optimizer.step()
                detached_ratio = ratio.detach()
                clip_fraction = (
                    (detached_ratio < 1 - self.config["clip_coef"])
                    | (detached_ratio > 1 + self.config["clip_coef"])
                ).float().mean()
                metrics.append(
                    {
                        "loss": float(loss.detach()),
                        "policy_loss": float(policy_loss.detach()),
                        "value_loss": float(value_loss.detach()),
                        "entropy": float(entropy.detach()),
                        "approx_kl": float(approximate_kl.detach()),
                        "clip_fraction": float(clip_fraction),
                        "gradient_norm": float(gradient_norm),
                    }
                )
            if stop:
                break
        if not metrics:
            raise ValueError("PPO update performed no optimizer steps")
        self.update_count += 1
        self.policy.behavior_version = f"ppo-update-{self.update_count}"
        after_hash = self.policy.model_sha256
        return {
            **{name: sum(item[name] for item in metrics) / len(metrics) for name in metrics[0]},
            "optimizer_steps": len(metrics),
            "transitions": len(transitions),
            "episodes": len(episodes),
            "update": self.update_count,
            "early_stop_kl": stop,
            "before_sha256": before_hash,
            "after_sha256": after_hash,
            "parameters_changed": before_hash != after_hash,
        }

    def state_dict(self) -> dict:
        return copy.deepcopy(
            {
                "learner_version": LEARNER_VERSION,
                "reward_version": REWARD_VERSION,
                "policy": self.policy.state_dict(),
                "optimizer": self.optimizer.state_dict(),
                "generator": self.generator.get_state(),
                "torch_rng": torch.get_rng_state(),
                "config": self.config,
                "update_count": self.update_count,
            }
        )

    def load_state_dict(self, state: Mapping) -> None:
        if state["learner_version"] != LEARNER_VERSION or state["reward_version"] != REWARD_VERSION:
            raise ValueError("checkpoint learner or reward contract mismatch")
        if dict(state["config"]) != self.config:
            raise ValueError("checkpoint PPO configuration mismatch")
        self.policy.load_state_dict(state["policy"])
        self.optimizer.load_state_dict(state["optimizer"])
        self.generator.set_state(state["generator"])
        torch.set_rng_state(state["torch_rng"])
        self.update_count = int(state["update_count"])
