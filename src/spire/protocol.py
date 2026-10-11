"""Audited, deliberately narrow CommunicationMod combat interface.

The raw bridge message is diagnostic data, not policy input. This first contract
supports starter Ironclad cards and excludes potions and all noncombat choices.
Upstream wire indexes are one-based for cards and zero-based for monsters.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

OBSERVATION_CONTRACT = "ironclad-starter-combat-v1"
SUPPORTED_CARDS = frozenset({"Strike_R", "Defend_R", "Bash"})
ATTACK_INTENTS = frozenset({"ATTACK", "ATTACK_BUFF", "ATTACK_DEBUFF", "ATTACK_DEFEND"})


class ProtocolError(ValueError):
    """Malformed or unsupported bridge data; never a gameplay loss."""


class NotReadyError(ProtocolError):
    """A message is not a stable decision state."""


class BridgeCommandError(ProtocolError):
    """The engine rejected an earlier command."""


class UnsupportedStateError(ProtocolError):
    """The state falls outside the declared combat contract."""


class StaleActionError(ProtocolError):
    """An action belongs to a different session or observation."""


class IllegalActionError(ProtocolError):
    """An action is not an exact member of the current candidate set."""


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True)
class Action:
    id: str
    decision_id: str
    command: str
    kind: Literal["play", "end"]
    # These are indexes into the original arrays, both zero-based in Python.
    hand_index: int | None = None
    target_index: int | None = None
    card_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "command": self.command,
            "kind": self.kind,
            "hand_index": self.hand_index,
            "target_index": self.target_index,
            "card_id": self.card_id,
        }


@dataclass(frozen=True)
class Decision:
    id: str
    observation: Mapping[str, Any]
    candidates: tuple[Action, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "observation": _thaw(self.observation),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def _object(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProtocolError(f"{field} must be an object")
    return value


def _objects(value: Any, field: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, (list, tuple)):
        raise ProtocolError(f"{field} must be an array")
    return [_object(item, field) for item in value]


def _integer(value: Any, field: str) -> int:
    if type(value) is not int:
        raise ProtocolError(f"{field} must be an integer")
    return value


def _scalars(source: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    result = {}
    for field in fields:
        if field in source:
            value = source[field]
            if value is not None and type(value) not in (str, int, bool, float):
                raise ProtocolError(f"{field} must be a scalar")
            result[field] = value
    return result


def _cards(value: Any, *, unordered: bool = False) -> list[dict[str, Any]]:
    # UUIDs serve engine identity, but are neither needed by policies nor stable
    # across resets. Sorting after stripping them hides the actual draw order.
    cards = [
        _scalars(card, (
            "id", "name", "type", "rarity", "cost", "upgrades", "has_target",
            "exhausts", "ethereal", "misc", "is_playable",
        ))
        for card in _objects(value, "cards")
    ]
    if unordered:
        cards.sort(key=lambda card: json.dumps(card, sort_keys=True, separators=(",", ":")))
    return cards


def _powers(value: Any) -> list[dict[str, Any]]:
    # Upstream reflectively adds several private fields. Keep only tooltip data.
    return [_scalars(power, ("id", "name", "amount")) for power in _objects(value, "powers")]


def _creature(creature: Mapping[str, Any], *, monster: bool) -> dict[str, Any]:
    fields = ("current_hp", "max_hp", "block")
    fields += ("id", "name", "intent", "half_dead", "is_gone") if monster else ("energy",)
    result = _scalars(creature, fields)
    result["powers"] = _powers(creature.get("powers", []))
    if monster and creature.get("intent") in ATTACK_INTENTS:
        result.update(_scalars(creature, ("move_adjusted_damage", "move_hits")))
    return result


def _game(message: Mapping[str, Any]) -> Mapping[str, Any]:
    if "error" in message:
        raise BridgeCommandError(str(message["error"]))
    if message.get("ready_for_command") is not True:
        raise NotReadyError("Wait for a stable ready_for_command=true message")
    if message.get("in_game") is not True:
        raise UnsupportedStateError("Main-menu START belongs to the episode runner")
    return _object(message.get("game_state"), "game_state")


def decision_from_message(
    message: Mapping[str, Any], *, session_id: str, sequence: int
) -> Decision:
    """Build a safe immutable decision from a fresh, stable combat message.

    The runner owns session/sequence allocation and must increment sequence for
    every received message. It must invalidate an earlier decision before send.
    """
    if not isinstance(session_id, str) or not session_id:
        raise ProtocolError("A nonempty session_id is required")
    if type(sequence) is not int or sequence < 0:
        raise ProtocolError("sequence must be a nonnegative integer")
    game = _game(_object(message, "message"))
    if game.get("class") != "IRONCLAD" or game.get("ascension_level") != 0:
        raise UnsupportedStateError("This contract supports Ironclad at Ascension 0")
    if game.get("room_phase") != "COMBAT" or game.get("screen_type") != "NONE":
        raise UnsupportedStateError("Only ordinary combat decisions are supported")
    if game.get("is_screen_up", False):
        raise UnsupportedStateError("An open screen requires explicit runner support")
    combat = _object(game.get("combat_state"), "combat_state")
    hand = _objects(combat.get("hand"), "hand")
    monsters = _objects(combat.get("monsters"), "monsters")
    player = _object(combat.get("player"), "player")
    commands = message.get("available_commands")
    if not isinstance(commands, (list, tuple)) or any(type(c) is not str for c in commands):
        raise ProtocolError("available_commands must be an array of strings")

    observation = _scalars(game, (
        "class", "ascension_level", "floor", "act", "gold", "current_hp", "max_hp",
    ))
    observation["contract"] = OBSERVATION_CONTRACT
    observation["excluded_actions"] = ["potions", "noncombat_choices"]
    observation["deck"] = _cards(game.get("deck", []), unordered=True)
    observation["relics"] = [
        _scalars(relic, ("id", "name", "counter"))
        for relic in _objects(game.get("relics", []), "relics")
    ]
    observation["potions"] = [
        _scalars(potion, ("id", "name", "can_use", "can_discard", "requires_target"))
        for potion in _objects(game.get("potions", []), "potions")
    ]
    public_combat = _scalars(combat, ("turn", "cards_discarded_this_turn", "times_damaged"))
    public_combat["player"] = _creature(player, monster=False)
    public_combat["monsters"] = [_creature(monster, monster=True) for monster in monsters]
    for pile in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        public_combat[pile] = _cards(combat.get(pile, []), unordered=pile != "hand")
    observation["combat_state"] = public_combat

    decision_id = f"{session_id}:{sequence}"
    candidates = []
    live_targets = [
        index for index, monster in enumerate(monsters)
        if monster.get("is_gone") is False and monster.get("half_dead") is False
        and _integer(monster.get("current_hp"), "monster.current_hp") > 0
    ]
    if "play" in commands:
        for hand_index, card in enumerate(hand):
            if card.get("is_playable") is not True:
                continue
            card_id = card.get("id")
            if card_id not in SUPPORTED_CARDS:
                raise UnsupportedStateError(f"Playable card outside starter contract: {card_id}")
            targeted = card_id != "Defend_R"
            if card.get("has_target") is not targeted:
                raise ProtocolError(f"Unexpected target mode for starter card {card_id}")
            for target_index in live_targets if targeted else (None,):
                suffix = f":{target_index}" if target_index is not None else ""
                command = f"play {hand_index + 1}"
                if target_index is not None:
                    command += f" {target_index}"
                candidates.append(Action(
                    id=f"{decision_id}:play:{hand_index}{suffix}",
                    decision_id=decision_id,
                    command=command,
                    kind="play",
                    hand_index=hand_index,
                    target_index=target_index,
                    card_id=card_id,
                ))
    if "end" in commands:
        candidates.append(Action(f"{decision_id}:end", decision_id, "end", "end"))
    if not candidates:
        raise UnsupportedStateError("No supported legal combat actions in this message")
    return Decision(decision_id, _freeze(observation), tuple(candidates))


def validate_action(decision: Decision, action: Action | str) -> Action:
    """Resolve an ID or reject a stale/forged action before writing to the bridge."""
    action_id = action.id if isinstance(action, Action) else action
    if not isinstance(action_id, str):
        raise IllegalActionError("Policy must return an Action or action ID")
    if isinstance(action, Action) and action.decision_id != decision.id:
        raise StaleActionError(f"Action belongs to {action.decision_id}, current is {decision.id}")
    for candidate in decision.candidates:
        if action_id == candidate.id:
            if isinstance(action, Action) and action != candidate:
                raise IllegalActionError("Action fields differ from the recorded legal candidate")
            return candidate
    if not action_id.startswith(f"{decision.id}:"):
        raise StaleActionError("Action ID does not belong to the current decision")
    raise IllegalActionError("Action is absent from the current legal candidate set")


def combat_outcome(
    message: Mapping[str, Any], *, combat_floor: int
) -> Literal["won", "lost"] | None:
    """Read an engine outcome after the runner has observed combat on this floor.

    A lack of living enemies is not terminal evidence. Unlock screens also map
    to GAME_OVER upstream but contain a placeholder victory flag; ignore them.
    """
    if "error" in message:
        raise BridgeCommandError(str(message["error"]))
    if message.get("ready_for_command") is not True or message.get("in_game") is not True:
        return None
    game = _object(message.get("game_state"), "game_state")
    if game.get("floor") != combat_floor:
        return None
    if game.get("screen_type") == "GAME_OVER":
        if game.get("screen_name") not in ("DEATH", "VICTORY"):
            return None
        screen = _object(game.get("screen_state"), "screen_state")
        if type(screen.get("victory")) is not bool:
            raise ProtocolError("Game-over screen lacks a boolean victory flag")
        return "won" if screen["victory"] else "lost"
    if game.get("room_phase") == "COMPLETE" and game.get("room_type") in (
        "MonsterRoom", "MonsterRoomElite", "MonsterRoomBoss",
    ):
        return "won"
    return None
