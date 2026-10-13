"""Public decisions for complete runs: every stable in-game screen and any card.

``protocol.py`` keeps the frozen first-combat contract. This module covers whole
runs (Neow, map, combat with any card or potion, rewards, events, shops, rest sites,
boss relics) for policies that pick among labeled engine commands. Raw input
(``key``/``click``), waiting and state polling are never offered as choices.
Wire indexes stay as CommunicationMod defines them: one-based hand cards for
``play``, zero-based monster targets, potion slots and ``choose`` indexes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from spire.protocol import (
    ATTACK_INTENTS,
    Decision,
    ProtocolError,
    UnsupportedStateError,
    _freeze,
)

OBSERVATION_CONTRACT = "full-run-public-v1"
# Engine identity, RNG and internal move bookkeeping that a player never sees.
HIDDEN_FIELDS = frozenset({
    "uuid", "seed", "action_phase", "current_action",
    "move_id", "last_move_id", "second_last_move_id", "move_base_damage",
})
GAME_FIELDS = (
    "class", "ascension_level", "act", "act_boss", "floor", "gold", "current_hp", "max_hp",
    "room_phase", "room_type", "screen_type", "screen_name", "is_screen_up", "keys",
    "relics", "potions", "deck", "map", "choice_list", "screen_state", "combat_state",
)
BUTTONS = ("confirm", "proceed", "skip", "cancel", "return", "leave")
MAP_SYMBOLS = {
    "M": "monster", "E": "elite", "R": "rest site", "$": "shop", "?": "unknown event",
    "T": "treasure",
}
REST_OPTIONS = {
    "rest": "rest: heal 30% of max HP",
    "smith": "smith: upgrade a card",
    "lift": "lift: gain 1 permanent Strength (Girya)",
    "dig": "dig: obtain a random relic (Shovel)",
    "toke": "toke: remove a card from your deck (Peace Pipe)",
    "recall": "recall: obtain the Ruby Key",
}


@dataclass(frozen=True)
class Choice:
    id: str
    decision_id: str
    command: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _public(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _public(v) for k, v in value.items() if k not in HIDDEN_FIELDS}
    if isinstance(value, list):
        return [_public(item) for item in value]
    return value


def _powers(creature: dict) -> list[dict]:
    # Upstream reflects extra private fields into powers; keep the tooltip data.
    return [{k: p[k] for k in ("id", "name", "amount") if k in p}
            for p in creature.get("powers", [])]


def _sorted_cards(cards: list[dict]) -> list[dict]:
    return sorted(cards, key=lambda card: json.dumps(card, sort_keys=True))


def public_observation(game: dict) -> dict:
    """Allowlisted game fields with hidden order and engine internals removed."""
    observation = _public({key: game[key] for key in GAME_FIELDS if key in game})
    observation["contract"] = OBSERVATION_CONTRACT
    combat = observation.get("combat_state")
    if combat:
        frozen_eye = any(relic.get("id") == "Frozen Eye" for relic in observation["relics"])
        if not frozen_eye:
            combat["draw_pile"] = _sorted_cards(combat.get("draw_pile", []))
        combat["player"]["powers"] = _powers(combat["player"])
        for monster in combat.get("monsters", []):
            monster["powers"] = _powers(monster)
            if monster.get("intent") not in ATTACK_INTENTS:
                monster.pop("move_adjusted_damage", None)
                monster.pop("move_hits", None)
    return observation


def card_text(card: dict) -> str:
    cost = {-1: "X", -2: "unplayable"}.get(card.get("cost"), card.get("cost"))
    return f"{card.get('name')} ({cost} {str(card.get('type', '')).lower()})"


def live_targets(monsters: list[dict]) -> list[int]:
    # Raw positions stay stable after deaths; never renumber targets.
    return [index for index, monster in enumerate(monsters)
            if not monster.get("is_gone") and not monster.get("half_dead")
            and monster.get("current_hp", 0) > 0]


def _target_name(monsters: list[dict], index: int | None) -> str:
    return "" if index is None else f" -> {monsters[index].get('name')} [{index}]"


def _choice_label(game: dict, index: int, name: str) -> str:
    screen = game.get("screen_type")
    state = game.get("screen_state") or {}

    def item(items: list):
        return items[index] if index < len(items) else None

    if screen == "MAP":
        if name == "boss":
            return f"go to the boss ({game.get('act_boss')})"
        node = next((n for n in state.get("next_nodes", []) if f"x={n['x']}" == name), None)
        if node:
            kind = MAP_SYMBOLS.get(node.get("symbol"), node.get("symbol"))
            return f"go to {kind} at x={node['x']}, y={node['y']}"
    elif screen == "CARD_REWARD":
        if name == "bowl":
            return "take Singing Bowl's +2 max HP instead of a card"
        card = item(state.get("cards", []))
        if card:
            return f"take card {card_text(card)}"
    elif screen == "COMBAT_REWARD":
        reward = item(state.get("rewards", []))
        if reward:
            kind = reward.get("reward_type")
            detail = {
                "GOLD": f"{reward.get('gold')} gold",
                "STOLEN_GOLD": f"{reward.get('gold')} stolen gold back",
                "POTION": f"potion {(reward.get('potion') or {}).get('name')}",
                "RELIC": f"relic {(reward.get('relic') or {}).get('name')}",
                "CARD": "a card reward (opens a card choice)",
                "EMERALD_KEY": "the Emerald Key",
                "SAPPHIRE_KEY": "the Sapphire Key (instead of the linked relic)",
            }.get(kind, str(kind).lower())
            return f"take {detail}"
    elif screen == "SHOP_SCREEN":
        if name == "purge":
            return f"pay {state.get('purge_cost')} gold to remove a card"
        for group in ("cards", "relics", "potions"):
            for thing in state.get(group, []):
                if str(thing.get("name", "")).lower() == name.lower():
                    text = card_text(thing) if group == "cards" else thing.get("name")
                    return f"buy {text} for {thing.get('price')} gold"
    elif screen == "EVENT":
        options = [o for o in state.get("options", []) if not o.get("disabled")]
        option = next((o for o in options if o.get("choice_index") == index), item(options))
        if option:
            return option.get("text") or option.get("label") or name
    elif screen == "REST":
        return REST_OPTIONS.get(name, name)
    elif screen == "BOSS_REWARD":
        relic = item(state.get("relics", []))
        if relic:
            return f"take boss relic {relic.get('name')}"
    elif screen in ("GRID", "HAND_SELECT"):
        cards = state.get("cards" if screen == "GRID" else "hand", [])
        card = item(cards)
        if card:
            # Choosing a grid card that is already selected deselects it.
            chosen = {c.get("uuid") for c in state.get("selected_cards", [])} - {None}
            return f"{'deselect' if card.get('uuid') in chosen else 'select'} {card_text(card)}"
    elif screen == "CHEST" and name == "open":
        return f"open the {str(state.get('chest_type', 'chest')).lower()}"
    elif screen == "SHOP_ROOM" and name == "shop":
        return "enter the shop"
    return name


def _button_label(game: dict, command: str) -> str:
    screen = game.get("screen_type")
    if screen == "CARD_REWARD" and command == "skip":
        return "skip this card reward"
    if screen == "COMBAT_REWARD" and command == "proceed":
        return "proceed, leaving any remaining rewards"
    if screen == "BOSS_REWARD" and command == "skip":
        return "skip the boss relic"
    if screen in ("SHOP_SCREEN", "SHOP_ROOM") and command in ("leave", "proceed", "return"):
        return f"{command} (leave the shop)"
    if screen == "MAP" and command == "return":
        return "return (close the map)"
    return command


def decision_from_message(message: dict, *, session_id: str, sequence: int) -> Decision:
    """Build an immutable labeled choice set from a ready, in-game message; the run loop
    handles errors, unready messages and the main menu before calling this."""
    game, commands = message["game_state"], message["available_commands"]
    decision_id = f"{session_id}:{sequence}"
    choices: list[tuple[str, str]] = []
    combat = game.get("combat_state") or {}
    monsters = combat.get("monsters", [])
    targets = live_targets(monsters)
    if "play" in commands:
        seen = set()
        for slot, card in enumerate(combat.get("hand", [])):
            # Cards identical in every public field are interchangeable; offer one.
            key = json.dumps(_public(card), sort_keys=True)
            if card.get("is_playable") is not True or key in seen:
                continue
            seen.add(key)
            for target in targets if card.get("has_target") else [None]:
                command = f"play {slot + 1}" + ("" if target is None else f" {target}")
                choices.append((command, f"play {card_text(card)}{_target_name(monsters, target)}"))
    if "potion" in commands:
        for slot, potion in enumerate(game.get("potions", [])):
            if potion.get("can_use"):
                for target in targets if potion.get("requires_target") else [None]:
                    command = f"potion use {slot}" + ("" if target is None else f" {target}")
                    label = f"use potion {potion.get('name')}{_target_name(monsters, target)}"
                    choices.append((command, label))
            if potion.get("can_discard"):
                choices.append((f"potion discard {slot}", f"discard potion {potion.get('name')}"))
    if "choose" in commands:
        for index, name in enumerate(game.get("choice_list", [])):
            choices.append((f"choose {index}", _choice_label(game, index, str(name))))
    # In a grid's confirm view, cancel only un-hovers the card; CommunicationMod sees no
    # state change and never replies, which hangs the run (observed 2026-10-12).
    confirm_view = game.get("screen_type") == "GRID" and (game.get("screen_state") or {}).get(
        "confirm_up")
    for button in BUTTONS:
        if button in commands and not (confirm_view and button == "cancel"):
            choices.append((button, _button_label(game, button)))
    if "end" in commands:
        choices.append(("end", "end turn"))
    if not choices:
        raise UnsupportedStateError(f"No supported choices for commands {commands}")
    candidates = tuple(
        Choice(f"{decision_id}:{index}", decision_id, command, label)
        for index, (command, label) in enumerate(choices)
    )
    return Decision(decision_id, _freeze(public_observation(game)), candidates)


def run_outcome(message: dict) -> str | None:
    """Engine-confirmed end of a run; unlock screens carry a placeholder flag."""
    game = message.get("game_state") or {}
    if (
        message.get("ready_for_command") is True
        and game.get("screen_type") == "GAME_OVER"
        and game.get("screen_name") in ("DEATH", "VICTORY")
    ):
        victory = (game.get("screen_state") or {}).get("victory")
        if type(victory) is not bool:
            raise ProtocolError("Game-over screen lacks a boolean victory flag")
        return "won" if victory else "lost"
    return None
