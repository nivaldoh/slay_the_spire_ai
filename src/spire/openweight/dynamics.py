"""Stage D: what an action observably changed, as prediction targets (ECHO-style).

ECHO (arXiv 2605.24517) adds supervised learning on the environment's response tokens,
given a constant positive advantage alpha, to RL on the model's own tokens. Here the
response is a compact difference between the public observations before and after one
action. Random draws are uncertainty: drawn cards are a multiset, never an order. Targets
are training data only; no observation after an action reaches the policy's input before
it chooses that action.
"""

from __future__ import annotations

TARGETS = (
    "enemy_hp", "enemy_block", "enemy_powers",
    "player_hp", "player_block", "player_powers", "energy",
    "hand", "draw_pile", "discard_pile", "exhaust_pile",
)


def observable_delta(before: dict, after: dict) -> dict:
    """The TARGETS that differ between two public combat observations."""
    raise NotImplementedError


def render_delta(delta: dict) -> str:
    """The text the model learns to predict after its choice."""
    raise NotImplementedError
