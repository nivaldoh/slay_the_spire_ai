"""Episodes for training and evaluation: one task, one policy, one environment.

Each step keeps the public decision, the choice, the policy's metadata (prompt, sampled
tokens, log-probabilities) and the next observation, which is stage D's dynamics target.
GRPO plays groups: several attempts at the same task.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from spire.openweight.env import Environment
from spire.openweight.tasks import Task
from spire.protocol import PolicyFailure


@dataclass(frozen=True)
class Episode:
    task: Task
    steps: list[dict]
    outcome: str
    summary: dict


def run_episode(env: Environment, task: Task, policy, *, max_actions: int) -> Episode:
    decision = env.reset(task)
    steps: list[dict] = []
    summary: dict = {}
    while len(steps) < max_actions:
        try:
            choice = policy.choose(decision)
        except PolicyFailure:
            return Episode(task, steps, "policy_failure", summary)
        step = env.step(choice)
        summary = step.summary
        steps.append({
            "decision": decision.to_dict(),
            "choice": choice.to_dict(),
            "policy": policy.choice_metadata(decision.id),
            "next_observation": step.decision and step.decision.to_dict()["observation"],
        })
        if step.decision is None:
            return Episode(task, steps, step.outcome, summary)
        decision = step.decision
    return Episode(task, steps, "truncated", summary)


def run_group(make_env: Callable[[], Environment], task: Task, make_policy: Callable,
              size: int, *, max_actions: int) -> list[Episode]:
    """Attempts one after another: the real game allows a single controller."""
    episodes = []
    for _ in range(size):
        env = make_env()
        try:
            episodes.append(run_episode(env, task, make_policy(), max_actions=max_actions))
        finally:
            env.close()
    return episodes
