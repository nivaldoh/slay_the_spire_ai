"""API language-model player over full-run decisions: the prompt, memory and replies.

This file and ``configs/llm/`` are the autoresearch loop's editable surface; transport,
prices and spend live in ``gameai.llm``. Run memory is bounded: model-written notes
(rewritten through the reply's ``notes`` field) and the last few decisions. No transcript
accumulates.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, deque

from gameai.ledger import Ledger
from gameai.llm import InvalidReply, Model
from gameai.provenance import REPO_ROOT
from spire.decisions import Choice, card_text, live_targets
from spire.protocol import Decision, PolicyFailure

SYSTEM_PROMPT_PATH = REPO_ROOT / "configs/llm/system_prompt.md"
# Short rules notes for enemies the model was seen to misplay, keyed by monster ID.
MONSTER_NOTES_PATH = SYSTEM_PROMPT_PATH.with_name("monsters.json")
# Every full-run job shares this spend file, and so one budget; other games keep their own.
LEDGER_PATH = REPO_ROOT / "runs/llm-spend.jsonl"
MAX_OUTPUT_TOKENS = 4000
NOTES_LIMIT = 2000
HISTORY_LENGTH = 12
INVALID_RETRIES = 2
REWARD_SCREENS = ("COMBAT_REWARD", "CARD_REWARD")
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "choice": {"type": "integer"},
        "reason": {"type": "string"},
        "notes": {"type": ["string", "null"]},
    },
    "required": ["choice", "reason", "notes"],
    "additionalProperties": False,
}


def _clean(text: str) -> str:
    """Drop the game's color and wave markup and its NL line-break tokens."""
    text = re.sub(r"(?<!\S)[#][a-z]", "", text)
    text = re.sub(r"\s*\bNL\b\s*", "\n", text)
    return re.sub(r"[~@]", "", text).strip()


def _card(card: dict) -> str:
    """Name, cost and type, plus the keywords the engine reports (card text is not shown)."""
    keywords = "".join(f", {k}" for k in ("ethereal", "exhausts") if card.get(k))
    return card_text(card)[:-1] + keywords + ")"


def _cards(cards: list) -> str:
    counts = Counter(_card(card) for card in cards)
    return ", ".join(f"{n}x {text}" if n > 1 else text for text, n in counts.items()) or "none"


def _powers(creature: dict) -> str:
    # Amountless powers such as Corruption report -1.
    return ", ".join(
        p.get("name") + ("" if p.get("amount", -1) == -1 else f" {p['amount']}")
        for p in creature["powers"]
    ) or "none"


def _monster(index: int, monster: dict) -> str:
    name = f"[{index}] {monster.get('name')}"
    if monster.get("is_gone") or monster.get("current_hp", 0) <= 0:
        return f"{name}: dead"
    intent = monster.get("intent")
    if "move_adjusted_damage" in monster:
        hits = monster.get("move_hits", 1)
        intent += f" {monster['move_adjusted_damage']}" + (f"x{hits}" if hits > 1 else "")
    state = "half dead, " if monster.get("half_dead") else ""
    return (f"{name}: {state}HP {monster['current_hp']}/{monster['max_hp']}, block "
            f"{monster.get('block', 0)}, intent {intent}; powers: {_powers(monster)}")


ROOMS = {"MonsterRoom": "monster", "MonsterRoomElite": "elite", "MonsterRoomBoss": "boss"}
# The boss room ends each of the first three acts on a fixed floor.
BOSS_FLOORS = {1: 16, 2: 33, 3: 50}


def incoming_damage(monsters: list) -> int:
    # Visible attack intents only; hidden damage (Runic Dome) reports -1 and is left out.
    return sum(max(monsters[i].get("move_adjusted_damage", 0), 0) * monsters[i].get("move_hits", 1)
               for i in live_targets(monsters))


def _combat(combat: dict, room: str, monster_notes: dict) -> list[str]:
    player = combat["player"]
    monsters = combat.get("monsters", [])
    noted = {m["id"]: m.get("name") for m in monsters
             if m.get("id") in monster_notes and not m.get("is_gone")}
    lines = [
        f"Combat ({ROOMS.get(room, 'event')}), turn {combat.get('turn')}. "
        f"Energy {player.get('energy')}.",
        f"You: HP {player['current_hp']}/{player['max_hp']}, block {player.get('block', 0)}; "
        f"powers: {_powers(player)}",
        "Enemies:",
        *(f"  {_monster(i, m)}" for i, m in enumerate(monsters)),
        f"Incoming attack damage this turn: {incoming_damage(monsters)}, against your "
        f"{player.get('block', 0)} block and {player['current_hp']} HP.",
        *(["Enemy rules:"] if noted else []),
        *(f"  {name}: {monster_notes[key]}" for key, name in noted.items()),
        "Hand: " + (", ".join(_card(card) for card in combat.get("hand", [])) or "empty"),
    ]
    for pile in ("draw_pile", "discard_pile", "exhaust_pile"):
        cards = combat.get(pile, [])
        lines.append(f"{pile.replace('_', ' ').capitalize()} ({len(cards)}): {_cards(cards)}")
    return lines


def _map(observation: dict) -> list[str]:
    """Only nodes still reachable from the next-row choices."""
    nodes = {(n["x"], n["y"]): n for n in observation.get("map", [])}
    state = observation["screen_state"]
    frontier = [(n["x"], n["y"]) for n in state.get("next_nodes", [])]
    reachable = set()
    while frontier:
        point = frontier.pop()
        if point in nodes and point not in reachable:
            reachable.add(point)
            frontier.extend((c["x"], c["y"]) for c in nodes[point].get("children", []))
    rows: dict[int, list[str]] = {}
    for x, y in sorted(reachable):
        children = ",".join(str(c["x"]) for c in nodes[(x, y)].get("children", []))
        rows.setdefault(y, []).append(f"{x}{nodes[(x, y)]['symbol']}>{children or 'boss'}")
    current = state.get("current_node") or {}
    return [
        f"Map ahead, from x={current.get('x')}, y={current.get('y')}. Each node is "
        "x+symbol>children's x in the next row. M monster, E elite, R rest, $ shop, "
        "? event, T treasure.",
        *(f"  y={y}: " + "  ".join(row) for y, row in sorted(rows.items())),
        f"  then the boss: {observation.get('act_boss')}",
    ]


def _screen(observation: dict) -> list[str]:
    screen = observation.get("screen_type")
    state = observation.get("screen_state") or {}
    if screen == "MAP":
        return _map(observation)
    if screen == "EVENT":
        options = [
            f"  {option.get('text')}" + (" (disabled)" if option.get("disabled") else "")
            for option in state.get("options", [])
        ]
        return [f"Event: {state.get('event_name')}", _clean(state.get("body_text", "")),
                "Options:", *options]
    if screen == "SHOP_SCREEN":
        items = [_card(card) + f" {card.get('price')}g" for card in state.get("cards", [])]
        items += [f"{thing.get('name')} {thing.get('price')}g"
                  for group in ("relics", "potions") for thing in state.get(group, [])]
        purge = f"; card removal {state.get('purge_cost')}g" if state.get("purge_available") else ""
        return [f"Shop (you have {observation.get('gold')} gold): " + ", ".join(items) + purge]
    if screen == "GRID":
        purpose = next((p for p in ("upgrade", "transform", "purge") if state.get(f"for_{p}")),
                       "select")
        count = "any number of" if state.get("any_number") else state.get("num_cards")
        # A single chosen card waits in a hover slot, not in selected_cards.
        selected = state.get("selected_cards", [])
        return [f"Choose {count} card(s) to {purpose}."
                + (f" Selected: {_cards(selected)}" if selected else "")]
    if screen == "HAND_SELECT":
        return [f"Choose up to {state.get('max_cards')} card(s) from your hand. Selected: "
                + _cards(state.get("selected", []))]
    return [f"Screen: {screen}" + (f" ({state['chest_type']})" if "chest_type" in state else "")]


def render_state(observation: dict, monster_notes: dict | None = None) -> str:
    relics = [r.get("name") + (f" ({r['counter']})" if r.get("counter", -1) >= 0 else "")
              for r in observation.get("relics", [])]
    potions = [f"[{slot}] " + ("empty" if p.get("id") == "Potion Slot" else p.get("name"))
               for slot, p in enumerate(observation.get("potions", []))]
    deck = observation.get("deck", [])
    act, boss = observation.get("act"), observation.get("act_boss")
    boss = f"{boss}, on floor {BOSS_FLOORS[act]}" if act in BOSS_FLOORS else boss
    lines = [
        f"Act {act}, floor {observation.get('floor')}. Act boss: {boss}. "
        f"HP {observation.get('current_hp')}/{observation.get('max_hp')}, "
        f"gold {observation.get('gold')}.",
        "Relics: " + (", ".join(relics) or "none"),
        "Potions: " + (", ".join(potions) or "none"),
        f"Deck ({len(deck)}): {_cards(deck)}",
    ]
    keys = [name for name, held in (observation.get("keys") or {}).items() if held]
    if keys:
        lines.append("Keys: " + ", ".join(keys))
    if observation.get("combat_state"):
        lines += _combat(
            observation["combat_state"], observation.get("room_type"), monster_notes or {}
        )
    if observation.get("screen_type") not in (None, "NONE"):
        lines += _screen(observation)
    return "\n".join(lines)


def render_prompt(decision: Decision, notes: str, history: list[str],
                  monster_notes: dict | None = None, reminders: list[str] = ()) -> str:
    choices = "\n".join(f"{i}: {c.label}" for i, c in enumerate(decision.candidates))
    state = render_state(decision.to_dict()["observation"], monster_notes)
    return "\n\n".join([
        "Run notes:\n" + (notes or "(empty)"),
        "Recent decisions, oldest first:\n" + ("\n".join(history) or "(none)"),
        "State:\n" + "\n".join([state, *reminders]),
        "Choices:\n" + choices,
    ])


def _parse(text: str, count: int) -> dict:
    # The strict reply schema fixes the keys and types; only the range is left to check.
    reply = json.loads(text)
    if not 0 <= reply["choice"] < count:
        raise ValueError(f"choice must be an integer from 0 to {count - 1}")
    return reply


class LLMPolicy:
    """One instance per run: its notes and history are that run's only memory."""

    def __init__(self, model: str, effort: str, ledger: Ledger, *, send=None,
                 system_prompt: str | None = None):
        self.api = Model(model, effort, ledger, send=send,
                         instructions=system_prompt or SYSTEM_PROMPT_PATH.read_text(),
                         max_output_tokens=MAX_OUTPUT_TOKENS)
        self.totals = self.api.totals
        self.monster_notes = json.loads(MONSTER_NOTES_PATH.read_text())
        self.notes = ""
        self.history: deque[str] = deque(maxlen=HISTORY_LENGTH)
        # Skipped card rewards stay listed; remember them per floor (v6 reopened one 20 times).
        self.declined: dict[int, list[str]] = {}
        # A hand selection does not say what it is for; the action before it, on the same
        # floor and combat turn, does. Keyed (floor, turn, label).
        self.last_action: tuple = (None, None, "")
        self._metadata = None

    def _reminders(self, observation: dict) -> list[str]:
        """Facts from earlier decisions that the current screen does not show."""
        screen = observation.get("screen_type")
        declined = self.declined.get(observation.get("floor"))
        if declined and screen in REWARD_SCREENS:
            return ["Card rewards you skipped on this floor (reopening one shows the same "
                    "cards): " + "; ".join(declined)]
        if screen != "HAND_SELECT":
            return []
        turn = (observation.get("combat_state") or {}).get("turn")
        floor, action_turn, action = self.last_action
        if (floor, action_turn) == (observation.get("floor"), turn):
            if action.startswith("play "):
                return [f"This selection is for {action.removeprefix('play ')}, which you just "
                        "played."]
            if action.startswith("use potion "):
                return [f"This selection is for the potion {action.removeprefix('use potion ')}"
                        ", which you just used."]
        relics = {relic.get("name") for relic in observation.get("relics", [])}
        if "Gambling Chip" in relics and turn == 1:
            return ["This selection is Gambling Chip's: the chosen cards are discarded, then "
                    "you draw that many."]
        return []

    def choose(self, decision: Decision) -> Choice:
        observation = decision.observation
        floor = observation.get("floor")
        prompt = render_prompt(decision, self.notes, list(self.history), self.monster_notes,
                               self._reminders(observation))
        self._metadata = metadata = {
            "type": "llm", "model": self.api.name, "effort": self.api.effort,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "prompt": prompt,
        }
        try:
            reply, metadata["attempts"] = self.api.ask(
                prompt, REPLY_SCHEMA, lambda text: _parse(text, len(decision.candidates)),
                INVALID_RETRIES)
        except InvalidReply as error:
            raise PolicyFailure(str(error), failure={
                "kind": "invalid_reply", "attempts": error.attempts,
            }) from None
        choice = decision.candidates[reply["choice"]]
        if reply["notes"] is not None:
            self.notes = reply["notes"][:NOTES_LIMIT]
            metadata["notes"] = self.notes
        if observation.get("screen_type") == "CARD_REWARD" and choice.command == "skip":
            offer = _cards((observation.get("screen_state") or {}).get("cards", []))
            if offer not in self.declined.setdefault(floor, []):
                self.declined[floor].append(offer)
        if observation.get("screen_type") != "HAND_SELECT":
            turn = (observation.get("combat_state") or {}).get("turn")
            self.last_action = (floor, turn, choice.label)
        self.history.append(f"floor {floor}: {choice.label} ({reply['reason']})")
        metadata.update(selected_index=reply["choice"], reason=reply["reason"])
        return choice

    def choice_metadata(self, decision_id: str) -> dict:
        return self._metadata
