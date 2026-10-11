"""Transparent baselines that receive only the public combat decision."""

from __future__ import annotations

import random

from spire.protocol import ATTACK_INTENTS, Action, Decision, IllegalActionError


class RandomPolicy:
    """Uniform over legal atomic candidates, including ending the turn."""

    name = "random"

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self._random = random.Random(seed)

    def choose(self, decision: Decision) -> Action:
        if not decision.candidates:
            raise IllegalActionError("Decision has no candidates")
        return self._random.choice(decision.candidates)


class EndTurnPolicy:
    """Diagnostic failure policy used to verify engine defeat and restart handling."""

    def choose(self, decision: Decision) -> Action:
        for candidate in decision.candidates:
            if candidate.kind == "end":
                return candidate
        raise IllegalActionError("End-turn diagnostic requires an available end action")


class StarterHeuristicPolicy:
    """Block visible incoming damage, then Bash/Strike the weakest enemy.

    This is a fixed, disclosed heuristic, not a learner or a search algorithm.
    It blocks until current block covers the visible attack total, ignores
    future enemy moves, and spends spare energy before ending the turn.
    """

    name = "starter_heuristic"

    def choose(self, decision: Decision) -> Action:
        if not decision.candidates:
            raise IllegalActionError("Decision has no candidates")
        combat = decision.observation["combat_state"]
        player = combat["player"]
        monsters = combat["monsters"]
        hand = combat["hand"]
        plays = [action for action in decision.candidates if action.kind == "play"]
        if not plays:
            return decision.candidates[0]
        incoming = sum(
            max(0, monster.get("move_adjusted_damage", 0)) * monster.get("move_hits", 1)
            for monster in monsters
            if monster.get("intent") in ATTACK_INTENTS
            and not monster.get("is_gone") and not monster.get("half_dead")
        )
        defends = [action for action in plays if action.card_id == "Defend_R"]
        if defends and player.get("block", 0) < incoming:
            return max(defends, key=lambda action: hand[action.hand_index].get("upgrades", 0))
        attacks = [action for action in plays if action.target_index is not None]
        if attacks:
            weakest = min(
                {action.target_index for action in attacks},
                key=lambda index: (monsters[index]["current_hp"], index),
            )
            target_attacks = [action for action in attacks if action.target_index == weakest]
            if player.get("energy", 0) >= 3:
                for action in target_attacks:
                    if action.card_id == "Bash":
                        return action
            for action in target_attacks:
                if action.card_id == "Strike_R":
                    return action
            return target_attacks[0]
        return plays[0]
