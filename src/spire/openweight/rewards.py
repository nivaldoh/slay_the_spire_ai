"""Rewards from scored outcomes only.

Fights: winning first, remaining HP second. Full runs: victory alone; floors reached and
damage dealt are diagnostics, since rewarding them can favor strategies that lose. On easy
fights every policy wins (the heuristic won 12 of 12 floor-1 scenarios), so HP carries the
signal there. Infrastructure failures are not outcomes: their episodes leave the group.
"""

from __future__ import annotations

# Outcomes a policy is answerable for, as in spire.fullrun.play.
SCORED = frozenset({"won", "lost", "policy_failure", "truncated"})


def _scored(outcome: str) -> None:
    if outcome not in SCORED:
        raise ValueError(f"{outcome} is not a scored outcome")


def fight_reward(outcome: str, hp: int, max_hp: int) -> float:
    """1 plus the share of max HP kept for a win, else 0: any win beats any loss.

    The HP scale is a placeholder for the pilot to settle.
    """
    _scored(outcome)
    return 1.0 + hp / max_hp if outcome == "won" else 0.0


def run_reward(outcome: str) -> float:
    _scored(outcome)
    return 1.0 if outcome == "won" else 0.0
