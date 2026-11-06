"""A rule-based Ironclad policy for complete runs, as a free teacher and a simple baseline.

Structure follows SimpleAgent in ForgottenArbiter/spirecomm (`spirecomm/ai/agent.py`): one
handler per screen, card priorities kept as data, a route chosen over the whole map, and
block weighed against incoming damage. The values and scoring are this project's own.

The policy reads only the public ``Decision`` and always returns one of its candidates, so
it stays inside the information boundary and cannot send an illegal command. It plans no
draws. Its strength is unmeasured until it plays real runs.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence

from spire.decisions import Choice
from spire.fullrun import rule_data as data
from spire.protocol import ATTACK_INTENTS, Decision

VERSION = "rules-v1"
BUTTONS = ("confirm", "proceed", "leave", "skip", "return", "cancel", "end")
# Seeing one state this often means the game is not moving; leave by any button.
LOOP_LIMIT = 6
UNKNOWN_CARD_VALUE = 2
SKIP_BELOW = 3
SKIP_BELOW_THICK_DECK = 5
THICK_DECK = 22


def _power(creature: Mapping, power_id: str) -> int:
    return next((p.get("amount", 0) for p in creature.get("powers", ())
                 if p.get("id") == power_id), 0)


def _index(choice: Choice) -> int | None:
    parts = choice.command.split()
    return int(parts[1]) if parts[0] == "choose" and len(parts) == 2 else None


def attacking(monster: Mapping) -> bool:
    return monster.get("intent") in ATTACK_INTENTS


def incoming(monster: Mapping, act: int) -> int:
    """Public damage this monster shows for its next move; unknown intents get a guess."""
    if attacking(monster) and monster.get("move_adjusted_damage", -1) >= 0:
        return monster["move_adjusted_damage"] * max(monster.get("move_hits", 1), 1)
    return 5 * act if monster.get("intent") == "UNKNOWN" else 0


def live_monsters(combat: Mapping) -> dict[int, Mapping]:
    return {index: monster for index, monster in enumerate(combat.get("monsters", ()))
            if not monster.get("is_gone") and not monster.get("half_dead")
            and monster.get("current_hp", 0) > 0}


def block_of(card: Mapping, player: Mapping) -> int:
    card_id = card.get("id")
    if card_id == "Entrench":
        return player.get("block", 0)
    table = data.UPGRADED_BLOCKS if card.get("upgrades") else {}
    base = table.get(card_id, data.BLOCKS.get(card_id, 0))
    if not base:
        return 0
    total = base + _power(player, "Dexterity")
    return int(total * 0.75) if _power(player, "Frail") else max(total, 0)


def base_damage(card: Mapping, player: Mapping, deck: Sequence,
                combat: Mapping) -> tuple[float, int]:
    """Damage per hit before the target's modifiers, and the number of hits."""
    card_id = card.get("id")
    upgrades = card.get("upgrades", 0)
    if card_id == "Mind Blast":
        return float(len(combat.get("draw_pile", ()))), 1
    table = data.UPGRADED_ATTACKS if upgrades else {}
    damage, hits = table.get(card_id, data.ATTACKS.get(card_id, (0, 0)))
    if card_id == "Body Slam":
        damage = player.get("block", 0)
    if not hits:
        return 0.0, 0
    strength = _power(player, "Strength")
    if card_id == "Perfected Strike":
        damage += (3 if upgrades else 2) * sum("Strike" in str(c.get("name", "")) for c in deck)
    elif card_id == "Heavy Blade":
        strength *= 5 if upgrades else 3
    elif card_id == "Searing Blow":
        damage += upgrades * (upgrades + 7) // 2
    elif card_id == "Whirlwind":
        hits = max(combat.get("player", {}).get("energy", 0), 0)
    elif card_id == "Fiend Fire":
        hits = max(len(combat.get("hand", ())) - 1, 0)
    total = float(damage + strength)
    return (total * 0.75 if _power(player, "Weakened") else total), hits


def damage_to(monster: Mapping, per_hit: float, hits: int) -> tuple[float, bool]:
    """Damage that gets past block, capped at remaining HP, and whether it kills."""
    if _power(monster, "Vulnerable"):
        per_hit *= 1.5
    total = max(int(per_hit), 0) * hits - monster.get("block", 0)
    health = monster.get("current_hp", 0)
    return max(min(total, health), 0.0), total >= health


def can_finish(game: Mapping, combat: Mapping, monsters: dict) -> bool:
    """Whether the attacks in hand, best per energy first, can kill every enemy this turn."""
    player = combat["player"]
    remaining = sum(m.get("current_hp", 0) + m.get("block", 0) for m in monsters.values())
    if not monsters:
        return False
    vulnerable = all(_power(m, "Vulnerable") for m in monsters.values())
    options = []
    for card in combat.get("hand", ()):
        if not card.get("is_playable") or card.get("type") != "ATTACK":
            continue
        per_hit, hits = base_damage(card, player, game.get("deck", ()), combat)
        damage = per_hit * hits * (1.5 if vulnerable else 1)
        cost = max(card.get("cost", 0), 0)
        options.append((damage / max(cost, 0.5), damage, cost))
    energy = player.get("energy", 0)
    for _, damage, cost in sorted(options, reverse=True):
        if cost <= energy:
            energy -= cost
            remaining -= damage
    return remaining <= 0


def card_value(card: Mapping, deck: Sequence, floor: int) -> float:
    """Worth of adding this card to the deck; 0 means leave it."""
    card_id = card.get("id")
    if card_id in data.BAD_CARDS:
        return 0.0
    copies = sum(c.get("id") == card_id for c in deck)
    if copies >= data.MAX_COPIES.get(card_id, 2):
        return 0.0
    value = float(data.CARD_VALUE.get(card_id, UNKNOWN_CARD_VALUE)) + 0.5 * card.get("upgrades", 0)
    damage = data.ATTACKS.get(card_id, (0, 0))
    if floor <= 8 and card_id not in data.AREA and damage[0] * damage[1] >= 9:
        value += 1  # Act 1 elites punish a deck short of damage.
    if card_id in data.AREA and not any(c.get("id") in data.AREA for c in deck):
        value += 1.5
    if card.get("rarity") == "CURSE":
        return 0.0
    return value


def worst_first(cards: Sequence) -> list[int]:
    """Indexes of cards ordered from the most to the least worth losing."""
    def key(index: int) -> tuple:
        card = cards[index]
        card_id = card.get("id")
        rank = 0 if card_id in data.BAD_CARDS else 1 if card_id in ("Strike_R", "Defend_R") else 2
        return rank, data.CARD_VALUE.get(card_id, UNKNOWN_CARD_VALUE) + card.get("upgrades", 0)
    return sorted(range(len(cards)), key=key)


def upgrade_score(card: Mapping) -> float:
    if card.get("id") in data.BAD_CARDS or card.get("type") in ("CURSE", "STATUS"):
        return -1.0
    return data.UPGRADE_VALUE.get(card.get("id"), data.CARD_VALUE.get(card.get("id"), 2) / 2)


def event_score(label: str, hp: int, max_hp: int) -> float:
    """Read the gains and costs an option states; 0 is about the same as leaving."""
    text = label.lower()
    score = 0.0
    for word, worth in (("remove a card", 6), ("upgrade", 5), ("relic", 6), ("max hp +", 5),
                        ("transform", 3), ("apparition", 9), ("potion", 3), ("gain", 2),
                        ("rare card", 6), ("next three combats", 5), ("choose a card", 3),
                        ("colorless card", 3), ("become cursed", -8), ("cursed -", -8),
                        ("lose all", -2),
                        ("fight a boss", -9),
                        ("lose your starting relic", -6), ("no longer heal", -5), ("fight", -3),
                        ("[leave", 0.5), ("[continue", 1), ("[talk", 1), ("[proceed", 1)):
        if word in text:
            score += worth
    if re.search(r"lose \d+ gold", text):
        score -= 1
    healing = re.search(r"heal (\d+)", text)
    if healing:
        score += 8 * min(int(healing.group(1)), max_hp - hp) / max(max_hp, 1) * 3
    if "max hp" in text and "lose" in text:
        score -= 5
    for pattern in (r"lose (\d+) hp", r"take (\d+) (?:damage|damage\.)"):
        match = re.search(pattern, text)
        if match:
            cost = int(match.group(1))
            score -= 100 if cost >= hp else 12 * cost / max(hp, 1)
    return score


class RulePolicy:
    """Plays one run; keep one instance per run, because it remembers a little of each."""

    def __init__(self) -> None:
        self._seen: Counter = Counter()
        self._last_played = ""
        self._skipped_floor = -1
        self._shopped_floor = -1

    def choice_metadata(self, decision_id: str) -> dict:
        return {"type": "rules", "version": VERSION}

    def choose(self, decision: Decision) -> Choice:
        game = decision.observation
        state = game.get("screen_state") or {}
        screen = game.get("screen_type")
        key = (game.get("floor"), screen, game.get("current_hp"),
               tuple(c.command for c in decision.candidates),
               (game.get("combat_state") or {}).get("turn"))
        self._seen[key] += 1
        if self._seen[key] > LOOP_LIMIT:
            return self._leave(decision, nudge=self._seen[key])
        handler = getattr(self, f"_{str(screen).lower()}", None)
        choice = handler(decision, game, state) if handler else None
        if choice is None and game.get("combat_state") and screen == "NONE":
            choice = self._combat(decision, game)
        return choice or self._leave(decision)

    # Screens outside combat.

    def _leave(self, decision: Decision, nudge: int = 0) -> Choice:
        for button in BUTTONS:
            for choice in decision.candidates:
                if choice.command == button:
                    return choice
        usable = [c for c in decision.candidates if not c.command.startswith("potion")]
        options = usable or decision.candidates
        return options[nudge % len(options)]

    def _pick(self, decision: Decision, index: int) -> Choice | None:
        return next((c for c in decision.candidates if _index(c) == index), None)

    def _with_label(self, decision: Decision, *starts: str) -> Choice | None:
        for start in starts:
            for choice in decision.candidates:
                if choice.label.startswith(start):
                    return choice
        return None

    def _map(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        boss = self._with_label(decision, "go to the boss")
        if boss:
            return boss
        best, best_value = None, float("-inf")
        nodes = {(n["x"], n["y"]): n for n in game.get("map", ())}
        memo: dict = {}
        for choice in decision.candidates:
            match = re.search(r"x=(-?\d+), y=(\d+)", choice.label)
            if match:
                value = self._path_value((int(match[1]), int(match[2])), nodes, game, memo)
                if value > best_value:
                    best, best_value = choice, value
        return best

    def _path_value(self, position: tuple, nodes: dict, game: Mapping, memo: dict) -> float:
        if position in memo:
            return memo[position]
        node = nodes.get(position)
        if node is None:
            return 0.0
        symbol = node.get("symbol")
        health = game.get("current_hp", 0) / max(game.get("max_hp", 1), 1)
        gold = game.get("gold", 0)
        value = {"M": 1.0, "?": 2.0, "T": 3.0, "$": 3.0 if gold >= 150 else 0.0,
                 "R": 6.0 if health < 0.6 else 3.0,
                 "E": 4.0 if health >= 0.7 and game.get("floor", 0) >= 5 else -6.0,
                 }.get(symbol, 0.0)
        following = [self._path_value((c["x"], c["y"]), nodes, game, memo)
                     for c in node.get("children", ())]
        memo[position] = value + 0.9 * max(following, default=0.0)
        return memo[position]

    def _combat_reward(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        free_slot = any(p.get("id") == "Potion Slot" for p in game.get("potions", ()))
        rewards = state.get("rewards", ())
        for kind in ("RELIC", "GOLD", "STOLEN_GOLD", "EMERALD_KEY", "POTION", "CARD"):
            for index, reward in enumerate(rewards):
                if reward.get("reward_type") != kind:
                    continue
                if kind == "POTION" and not free_slot:
                    continue
                if kind == "CARD" and self._skipped_floor == game.get("floor"):
                    continue
                choice = self._pick(decision, index)
                if choice:
                    return choice
        return None

    def _card_reward(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        deck = game.get("deck", ())
        floor = game.get("floor", 0)
        scored = [(card_value(card, deck, floor), index)
                  for index, card in enumerate(state.get("cards", ()))]
        value, index = max(scored, default=(0.0, -1))
        least = SKIP_BELOW_THICK_DECK if len(deck) >= THICK_DECK else SKIP_BELOW
        if value >= least or "skip" not in [c.command for c in decision.candidates]:
            choice = self._pick(decision, index)
            if choice:
                return choice
        self._skipped_floor = floor
        return self._with_label(decision, "take Singing Bowl") or self._leave(decision)

    def _rest(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        if state.get("has_rested"):
            return None
        health = game.get("current_hp", 0) / max(game.get("max_hp", 1), 1)
        before_boss = game.get("floor", 0) % 17 >= 15
        if health < 0.5 or (before_boss and health < 0.85):
            return self._with_label(decision, "rest") or self._leave(decision)
        return (self._with_label(decision, "smith", "lift", "dig", "toke", "rest")
                or self._leave(decision))

    def _shop_room(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        if self._shopped_floor != game.get("floor"):
            self._shopped_floor = game.get("floor")
            return self._with_label(decision, "enter the shop") or self._leave(decision)
        return None

    def _shop_screen(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        names = game.get("choice_list", ())
        deck = game.get("deck", ())
        floor = game.get("floor", 0)
        gold = game.get("gold", 0)
        free_slot = any(p.get("id") == "Potion Slot" for p in game.get("potions", ()))
        best, best_value = None, 0.0
        for choice in decision.candidates:
            index = _index(choice)
            if index is None or index >= len(names):
                continue
            name = str(names[index]).lower()
            value = 0.0
            if name == "purge":
                worst = worst_first(deck)[0] if deck else None
                bad = worst is not None and deck[worst].get("id") in data.BAD_CARDS
                value = 9.0 if bad else 6.5 if worst is not None else 0.0
            for group in ("cards", "relics", "potions"):
                for item in state.get(group, ()):
                    if str(item.get("name", "")).lower() != name or item.get("price", 0) > gold:
                        continue
                    if group == "cards":
                        value = card_value(item, deck, floor) - 1
                    elif group == "relics":
                        value = 7.0
                    elif free_slot:
                        value = 2.5
            if value > best_value and value >= SKIP_BELOW:
                best, best_value = choice, value
        return best

    def _boss_reward(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        relics = state.get("relics", ())
        order = {name: rank for rank, name in enumerate(data.BOSS_RELICS)}
        if not relics:
            return None
        index = min(range(len(relics)),
                    key=lambda i: order.get(relics[i].get("id"), len(order)))
        return self._pick(decision, index)

    def _chest(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        return None if state.get("chest_open") else self._with_label(decision, "open the")

    def _event(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        hp, max_hp = game.get("current_hp", 1), game.get("max_hp", 1)
        options = [c for c in decision.candidates if not c.command.startswith("potion")]
        return max(options, key=lambda c: event_score(c.label, hp, max_hp), default=None)

    def _grid(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        cards = state.get("cards", ())
        selected = state.get("selected_cards", ())
        if state.get("confirm_up") or len(selected) >= state.get("num_cards", 1):
            return self._button(decision, "confirm")
        offered = [i for i in range(len(cards)) if self._selectable(decision, i)]
        if not offered:
            return None
        if state.get("for_purge") or state.get("for_transform"):
            order = [i for i in worst_first(cards) if i in offered]
            return self._pick(decision, order[0]) if order else None
        return self._pick(decision, max(offered, key=lambda i: upgrade_score(cards[i])))

    def _hand_select(self, decision: Decision, game: Mapping, state: Mapping) -> Choice | None:
        hand = state.get("hand", ())
        selected = state.get("selected", ())
        most = min(state.get("max_cards", 1), 3)
        if len(selected) >= most:
            return self._button(decision, "confirm")
        offered = [i for i in range(len(hand)) if self._selectable(decision, i)]
        if not offered:
            return self._button(decision, "confirm")
        if self._last_played in ("Armaments", "Dual Wield"):
            return self._pick(decision, max(offered, key=lambda i: upgrade_score(hand[i])))
        order = [i for i in worst_first(hand) if i in offered]
        if state.get("can_pick_zero") and hand[order[0]].get("id") not in data.BAD_CARDS:
            return self._button(decision, "confirm")
        return self._pick(decision, order[0])

    def _button(self, decision: Decision, button: str) -> Choice | None:
        return next((c for c in decision.candidates if c.command == button), None)

    def _selectable(self, decision: Decision, index: int) -> bool:
        choice = self._pick(decision, index)
        return choice is not None and not choice.label.startswith("deselect")

    # Combat.

    def _combat(self, decision: Decision, game: Mapping) -> Choice | None:
        combat = game["combat_state"]
        player = combat["player"]
        monsters = live_monsters(combat)
        act = game.get("act", 1)
        threat = sum(incoming(m, act) for m in monsters.values())
        hp, max_hp = player.get("current_hp", 0), max(player.get("max_hp", 1), 1)
        need = max(threat - player.get("block", 0), 0)
        if can_finish(game, combat, monsters):
            need = 0
        best, best_score = None, 0.0
        for choice in decision.candidates:
            if choice.command.startswith("play"):
                score = self._play_score(choice, game, combat, monsters, need)
            elif choice.command.startswith("potion use"):
                score = self._potion_score(choice, game, need, hp, max_hp)
            else:
                continue
            if score > best_score:
                best, best_score = choice, score
        if best is None:
            return self._button(decision, "end")
        if best.command.startswith("play"):
            slot = int(best.command.split()[1]) - 1
            hand = combat.get("hand", ())
            self._last_played = hand[slot].get("id", "") if slot < len(hand) else ""
        return best

    def _play_score(self, choice: Choice, game: Mapping, combat: Mapping,
                    monsters: dict, need: int) -> float:
        parts = choice.command.split()
        hand = combat.get("hand", ())
        slot = int(parts[1]) - 1
        if slot >= len(hand):
            return 0.0
        card = hand[slot]
        card_id = card.get("id")
        player = combat["player"]
        energy = player.get("energy", 0)
        cost = energy if card.get("cost", 0) < 0 else card.get("cost", 0)
        weight = max(cost, 0.5)
        target = monsters.get(int(parts[2])) if len(parts) > 2 else None
        hp, max_hp = player.get("current_hp", 0), max(player.get("max_hp", 1), 1)
        left = hp - need
        urgency = 4.0 if left <= 0 else 2.5 if left < 0.3 * max_hp else 1.3
        dangerous_room = game.get("room_type") in ("MonsterRoomElite", "MonsterRoomBoss")

        if card.get("type") == "CURSE" or card_id in data.BAD_CARDS:
            return 0.2 if card_id == "Slimed" and energy > cost else 0.0
        if card_id in data.SITUATIONAL:
            return 0.1

        punishes_skills = any(_power(m, "Anger") for m in monsters.values())
        if card.get("type") == "POWER":
            if any(_power(m, "Curiosity") for m in monsters.values()):
                return 1.0
            if card_id in data.POWERS_FIRST or data.CARD_VALUE.get(card_id, 0) >= 5:
                return 20.0 if left >= 0.4 * max_hp or dangerous_room else 6.0
            return 4.0

        score = 0.0
        per_hit, hits = base_damage(card, player, game.get("deck", ()), combat)
        if hits:
            if card_id in data.AREA:
                dealt = [damage_to(m, per_hit, hits) for m in monsters.values()]
                total = sum(d[0] for d in dealt)
                kills = sum(d[1] for d in dealt)
                score += total / weight + 6 * kills
            elif target is not None:
                dealt_to, kills_it = damage_to(target, per_hit, hits)
                summoned = _power(target, "Minion") and not kills_it
                score += (0.7 if summoned else 1.0) * dealt_to / weight
                if kills_it:
                    score += 6 + 1.5 * incoming(target, game.get("act", 1)) / weight
                    if card_id == "Feed":
                        score += 8
                if not _power(target, "Vulnerable") and card_id in data.VULNERABLE:
                    score += 6 if energy > cost else 2
            if card_id in data.WEAK and target is not None and attacking(target):
                score += 3
        guard = block_of(card, player)
        if guard:
            useful = min(guard, need)
            score += urgency * useful / weight + 0.1 * (guard - useful)
        if card_id in data.DRAW:
            score += 2
        score += {
            "Battle Trance": 12, "Offering": 14 if hp > 0.35 * max_hp else 0,
            "Bloodletting": 5 if hp > 0.4 * max_hp else 0, "Seeing Red": 5,
            "Shockwave": 16, "Disarm": 15 if target is not None and attacking(target) else 8,
            "Intimidate": 6, "Spot Weakness": 12 if target is not None and attacking(target) else 0,
            "Limit Break": 3 * _power(player, "Strength"), "Rage": 3, "Flex": 3, "Warcry": 1,
            "Burning Pact": 7 if any(c.get("id") in data.BAD_CARDS for c in hand) else 1,
            "Double Tap": 4, "Infernal Blade": 3, "Apotheosis": 25, "Panacea": 2,
            "Trip": 8, "Blind": 6, "Dark Shackles": 5,
        }.get(card_id, 0)
        if punishes_skills and card.get("type") == "SKILL" and left > 0.3 * max_hp:
            score -= 8
        if card_id == "Hemokinesis" and hp < 0.3 * max_hp:
            score = 0.1
        if card_id == "Ghostly":
            score += 18 if left < 0.5 * max_hp else 2
        return score

    def _potion_score(self, choice: Choice, game: Mapping, need: int, hp: int,
                      max_hp: int) -> float:
        parts = choice.command.split()
        potions = game.get("potions", ())
        slot = int(parts[2])
        potion = potions[slot] if slot < len(potions) else {}
        potion_id = potion.get("id")
        if potion_id in data.BAD_POTION_NOW:
            return 0.0
        danger = hp - need < 0.3 * max_hp
        hard = game.get("room_type") in ("MonsterRoomElite", "MonsterRoomBoss")
        first_turn = (game.get("combat_state") or {}).get("turn", 1) == 1
        if danger and potion_id in data.DEFENCE_POTIONS:
            return 30.0
        if danger or (hard and first_turn and game.get("room_type") == "MonsterRoomBoss"):
            return 25.0 if potion_id in data.ATTACK_POTIONS else 0.0
        if hard and need >= 0.5 * hp and potion_id in data.ATTACK_POTIONS:
            return 22.0
        return 0.0
