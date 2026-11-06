"""Rewards, a linear baseline, PPO on sampled runs, and an advantage-weighted warm start.

The PPO update follows CleanRL's ``ppo.py`` (clipped ratio, entropy bonus, approximate-KL
early stop; advantages normalised over the whole update) and GAE follows Schulman et al.
2016. The warm start is advantage-weighted regression (Peng et al. 2019). The value baseline
is ridge regression on public numbers, with no gradient through the language model.
"""

from __future__ import annotations

import math
import random

import numpy as np
import torch

from spire.localrl.policy import Scorer, log_probs
from spire.localrl.rewards import fight_rewards, fight_spans  # noqa: F401

SCREENS = ("NONE", "MAP", "COMBAT_REWARD", "CARD_REWARD", "EVENT", "SHOP_SCREEN", "SHOP_ROOM",
           "REST", "GRID", "HAND_SELECT", "CHEST", "BOSS_REWARD")
ROOMS = ("MonsterRoom", "MonsterRoomElite", "MonsterRoomBoss")


def features(o: dict) -> list[float]:
    """Public numbers for the baseline."""
    hp, top = o["hp"] or 0, max(o["max_hp"] or 1, 1)
    floor = (o["floor"] or 0) / 16
    fraction = hp / top
    margin = (hp + o["block"] - o["incoming"]) / top
    return [
        1.0, floor, floor * floor, fraction, fraction * floor, fraction * fraction, top / 80,
        (o["gold"] or 0) / 200, o["deck"] / 20, o["relics"] / 5, o["potions"] / 3,
        o["turn"] / 5, o["energy"] / 3, o["block"] / 20, o["hand"] / 5,
        o["enemy_hp"] / 60, o["enemies"] / 3, o["incoming"] / 20, margin,
        (o["enemy_hp"] / 60) * fraction,
        *(float(o["screen"] == name) for name in SCREENS),
        *(float(o["room"] == name) for name in ROOMS),
    ]


def rewards(steps: list[dict], status: str, final_floor: int, config: dict) -> list[float]:
    """One reward per step: floors climbed, plus potential-based shaping on the HP fraction.

    JUDGEMENT: Reward — Claude, 2026-11-06, owner away: +1 a floor, ``win_bonus`` for a win, and
    F = w(gamma*P(next) - P(now)) with P the HP fraction and w ``hp_weight`` (Ng, Harada and
    Russell 1999), so the shaping leaves the best policy unchanged. Every end of a run has
    potential 0; a truncated run has no end, and its value comes from the bootstrap. Floors
    reached is the evaluation measure.

    With HP among the baseline's features the shaping cancels out of the advantages: on the
    5,114 offline rows, those at w=3 and w=10 correlate 0.9999 and 0.9990 with w=0 (peer review,
    2026-11-06). So w is not a tuning value; HP reaches the credit through the baseline, as the
    floors it predicts.
    """
    gamma, weight = config["gamma"], config["hp_weight"]

    def hp(observation: dict) -> float:
        return (observation["hp"] or 0) / max(observation["max_hp"] or 1, 1)

    values = []
    for step, following in zip(steps, steps[1:]):
        a, b = step["observation"], following["observation"]
        gain = (b["floor"] or 0) - (a["floor"] or 0)
        values.append(gain + weight * (gamma * hp(b) - hp(a)))
    last = steps[-1]["observation"]
    gain = max(final_floor - (last["floor"] or 0), 0)
    if status == "lost":
        values.append(gain - weight * hp(last))
    elif status == "won":
        values.append(gain + config["win_bonus"] - weight * hp(last))
    else:
        values.append(float(gain))
    return values


def discounted(values: list[float], gamma: float) -> list[float]:
    total, result = 0.0, []
    for value in reversed(values):
        total = value + gamma * total
        result.append(total)
    return result[::-1]


class Baseline:
    """Ridge regression from public numbers to the discounted return."""

    def __init__(self, penalty: float = 1.0):
        self.penalty, self.weights = penalty, None

    def fit(self, rows: list[list[float]], targets: list[float]) -> float:
        x, y = np.array(rows), np.array(targets)
        a = x.T @ x + self.penalty * np.eye(x.shape[1])
        self.weights = np.linalg.solve(a, x.T @ y)
        residual = y - x @ self.weights
        return float(1 - residual.var() / max(y.var(), 1e-9))

    def __call__(self, rows: list[list[float]]) -> np.ndarray:
        return np.array(rows) @ self.weights


def advantages(values: list[float], estimates, config: dict, *, terminal: bool) -> list[float]:
    """GAE; a truncated run bootstraps from its last estimate."""
    gamma, lam = config["gamma"], config["lam"]
    result, running = [], 0.0
    for t in reversed(range(len(values))):
        following = estimates[t + 1] if t + 1 < len(values) else (
            0.0 if terminal else estimates[t])
        delta = values[t] + gamma * following - estimates[t]
        running = delta + gamma * lam * running
        result.append(running)
    return result[::-1]


def batches(items: list, size: int, generator: random.Random):
    order = sorted(items, key=lambda item: generator.random())
    for start in range(0, len(order), size):
        yield order[start:start + size]


def ppo_update(scorer: Scorer, optimizer, steps: list[dict], config: dict, seed: int) -> dict:
    """Minibatch epochs over one update's steps. Each step needs ``advantage`` and ``log_prob``."""
    model, generator = scorer.model, random.Random(seed)
    for step in steps:
        step.setdefault("ids", scorer.encode(step["prompt"]))
    trainable = [p for p in model.parameters() if p.requires_grad]
    # CleanRL normalises per minibatch, with hundreds of rows; four rows would lose the signal.
    spread = np.array([s["advantage"] for s in steps])
    center, scale = spread.mean(), spread.std() + 1e-6
    model.train()
    totals = {"clipped": 0.0, "entropy": 0.0, "grad_norm": 0.0}
    count, stopped, kls, first_deviation = 0, False, [], None
    for epoch in range(config["epochs"]):
        epoch_kl, epoch_count = 0.0, 0
        for group in batches(steps, config["minibatch"], generator):
            logits = scorer.logits([s["ids"] for s in group], [s["count"] for s in group])
            loss = 0.0
            kl = clipped = entropy = deviation = 0.0
            for s, row in zip(group, logits):
                current = log_probs(row, s["allowed"], config["temperature"])
                new = current[s["allowed"].index(s["index"])]
                ratio = torch.exp(new - s["log_prob"])
                advantage = (s["advantage"] - center) / scale
                limited = torch.clamp(ratio, 1 - config["clip"], 1 + config["clip"])
                loss = loss - torch.min(ratio * advantage, limited * advantage)
                spread_entropy = -(current.exp() * current).sum()
                loss = loss - config["entropy"] * spread_entropy
                deviation += abs(float(new.detach()) - s["log_prob"])
                kl += float((ratio.detach() - 1) - (new.detach() - s["log_prob"]))
                clipped += float(abs(ratio.detach() - 1) > config["clip"])
                entropy += float(spread_entropy.detach())
            if first_deviation is None:  # weights untouched: recomputed against recorded
                first_deviation = deviation / len(group)
            loss = loss / len(group)
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite policy loss")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(trainable, config["max_grad_norm"])
            optimizer.step()
            count += 1
            epoch_count += 1
            epoch_kl += kl / len(group)
            totals["clipped"] += clipped / len(group)
            totals["entropy"] += entropy / len(group)
            totals["grad_norm"] += float(norm)
        kls.append(epoch_kl / epoch_count)
        if kls[-1] > config["target_kl"]:  # this epoch's own mean, as CleanRL checks it
            stopped = True
            break
    model.eval()
    return {**{key: value / max(count, 1) for key, value in totals.items()}, "epoch_kl": kls,
            "first_deviation": first_deviation, "minibatches": count, "stopped_early": stopped,
            "steps": len(steps)}


def warm_start(scorer: Scorer, optimizer, rows: list[dict], config: dict, seed: int) -> list[dict]:
    """Advantage-weighted regression on recorded decisions; each row has ``weight``."""
    model, generator = scorer.model, random.Random(seed)
    for row in rows:
        row.setdefault("ids", scorer.encode(row["prompt"]))
    trainable = [p for p in model.parameters() if p.requires_grad]
    history = []
    model.train()
    for epoch in range(config["epochs"]):
        total, right, seen = 0.0, 0, 0
        for group in batches(rows, config["minibatch"], generator):
            logits = scorer.logits([r["ids"] for r in group], [r["count"] for r in group])
            loss = 0.0
            for r, row_logits in zip(group, logits):
                allowed = r.get("allowed") or list(range(r["count"]))
                current = log_probs(row_logits, allowed, 1.0)
                loss = loss - r["weight"] * current[allowed.index(r["index"])]
                right += allowed[int(row_logits[allowed].argmax())] == r["index"]
            loss = loss / len(group)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, config["max_grad_norm"])
            optimizer.step()
            total, seen = total + float(loss.detach()) * len(group), seen + len(group)
        history.append({"epoch": epoch, "weighted_loss": total / seen, "accuracy": right / seen})
        print(history[-1], flush=True)
    model.eval()
    return history


def agreement(scorer: Scorer, rows: list[dict]) -> dict:
    """Held-out accuracy and uniform-relative log-likelihood on recorded decisions."""
    right, gain = 0, 0.0
    with torch.inference_mode():
        for row in rows:
            logits = scorer.logits([scorer.encode(row["prompt"])], [row["count"]])[0]
            right += int(logits.argmax()) == row["index"]
            gain += float(torch.log_softmax(logits, 0)[row["index"]]) + math.log(row["count"])
    return {"rows": len(rows), "accuracy": right / len(rows), "gain_over_uniform": gain / len(rows)}
