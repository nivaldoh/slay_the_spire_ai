"""Public facts for the local model's prompt: what cards and potions do, what a move would do now.

CommunicationMod reports a card's name, cost and type, never its text, so a 0.6B model reading
"Bash (2 attack)" has to know the game already. Everything here comes from public card text
or from numbers the player sees on screen (intents, HP, powers); nothing reads hidden state,
and an estimate that turns out wrong costs quality of play, never legality.

JUDGEMENT: Prompt facts — Claude, 2026-11-06: card and potion text written from memory of the
public card text at Ascension 0, checked against the recorded engine numbers only for damage and
block of common cards. Floors of a ``render_v2`` adapter rest on these strings and on the
choice of what a label shows.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

# "a|b" reads a before an upgrade and b after it.
CARDS = {
    "Strike_R": "deal 6|9", "Defend_R": "5|8 block", "Bash": "deal 8|10, 2|3 Vulnerable",
    "Anger": "deal 6|8, copy into discard", "Armaments": "5 block, upgrade 1|all hand card(s)",
    "Body Slam": "deal your block", "Clash": "deal 14|18, only if hand is all attacks",
    "Cleave": "deal 8|11 to all", "Clothesline": "deal 12|14, 2|3 Weak",
    "Flex": "+2|4 Strength this turn", "Havoc": "play top of draw pile, exhaust it",
    "Headbutt": "deal 9|12, put a discard on top of draw", "Heavy Blade": "deal 14, Strength x3|5",
    "Iron Wave": "5|7 block, deal 5|7", "Perfected Strike": "deal 6, +2|3 per Strike card",
    "Pommel Strike": "deal 9|10, draw 1|2", "Shrug It Off": "8|11 block, draw 1",
    "Sword Boomerang": "deal 3 at random 3|4 times", "Thunderclap": "deal 4|7 to all, 1 Vulnerable",
    "True Grit": "7|9 block, exhaust a card", "Twin Strike": "deal 5|7 twice",
    "Warcry": "draw 1|2, put a card on draw", "Wild Strike": "deal 12|17, Wound into draw",
    "Battle Trance": "draw 3|4, no more draws this turn",
    "Blood for Blood": "deal 18|22, cheaper per HP loss", "Bloodletting": "lose 3 HP, +2|3 energy",
    "Burning Pact": "exhaust a card, draw 2|3", "Carnage": "deal 20|28, ethereal",
    "Combust": "each turn lose 1 HP, deal 5|7 to all", "Dark Embrace": "draw 1 per exhaust",
    "Disarm": "enemy -2|3 Strength", "Dropkick": "deal 5|8, on Vulnerable +1 energy and draw 1",
    "Dual Wield": "copy an attack or power in hand", "Entrench": "double your block",
    "Evolve": "draw 1|2 per status drawn", "Feel No Pain": "+3|4 block per exhaust",
    "Fire Breathing": "deal 6|10 to all per status drawn",
    "Flame Barrier": "12|16 block, attackers take 4|6", "Ghostly Armor": "10|13 block, ethereal",
    "Hemokinesis": "lose 2 HP, deal 15|20", "Infernal Blade": "random attack at 0 cost",
    "Inflame": "+2|3 Strength", "Intimidate": "1|2 Weak to all",
    "Metallicize": "+3|4 block each turn", "Power Through": "15|20 block, 2 Wounds in hand",
    "Pummel": "deal 2 x 4|5", "Rage": "+3|5 block per attack this turn",
    "Rampage": "deal 8, +5|8 each play", "Reckless Charge": "deal 7|10, Dazed into draw",
    "Rupture": "+1|2 Strength per card HP loss", "Searing Blow": "deal 12|16",
    "Second Wind": "exhaust non-attacks, 5|7 block each", "Seeing Red": "+2 energy",
    "Sentinel": "5|8 block, energy if exhausted",
    "Sever Soul": "exhaust non-attacks in hand, deal 16|22",
    "Shockwave": "3|5 Weak and Vulnerable to all",
    "Spot Weakness": "+3|4 Strength if enemy attacks",
    "Uppercut": "deal 13, 1|2 Weak and Vulnerable", "Whirlwind": "deal 5|8 to all per energy",
    "Barricade": "block stays between turns", "Berserk": "2|1 Vulnerable on you, +1 energy a turn",
    "Bludgeon": "deal 32|42", "Brutality": "each turn lose 1 HP, draw 1",
    "Corruption": "skills cost 0 and exhaust", "Demon Form": "+2|3 Strength every turn",
    "Double Tap": "next 1|2 attack(s) play twice", "Exhume": "take a card back from exhaust",
    "Feed": "deal 10|12, a kill gives +3|4 max HP",
    "Fiend Fire": "exhaust hand, deal 7|10 per card",
    "Immolate": "deal 21|28 to all, Burn into discard", "Impervious": "30|40 block",
    "Juggernaut": "deal 5|7 per block gain", "Limit Break": "double your Strength",
    "Offering": "lose 6 HP, +2 energy, draw 3|5", "Reaper": "deal 4|5 to all, heal that much",
    # Colorless
    "Bandage Up": "heal 4|6", "Blind": "2 Weak", "Dark Shackles": "enemy -9|15 Strength this turn",
    "Deep Breath": "reshuffle discard, draw 1|2", "Discovery": "pick 1 of 3 cards at 0 cost",
    "Dramatic Entrance": "deal 8|12 to all, innate", "Enlightenment": "hand costs 1 this turn",
    "Finesse": "2|4 block, draw 1", "Flash of Steel": "deal 3|6, draw 1",
    "Forethought": "put a card under draw, it costs 0", "Good Instincts": "6|9 block",
    "Impatience": "draw 2|3 if no attack in hand", "Jack Of All Trades": "1|2 random colorless",
    "Madness": "random hand card costs 0", "Mind Blast": "deal draw pile size, innate",
    "Panacea": "+1|2 Artifact", "PanicButton": "30|40 block, no block for 2 turns",
    "Purity": "exhaust up to 3|5 hand cards", "Swift Strike": "deal 7|10", "Trip": "2 Vulnerable",
    "Apotheosis": "upgrade all cards this fight", "Chrysalis": "3|5 random skills into draw at 0",
    "HandOfGreed": "deal 20|25, a kill gives gold", "Magnetism": "a random colorless each turn",
    "Master of Strategy": "draw 3|4", "Mayhem": "play top of draw each turn",
    "Metamorphosis": "3|5 random attacks into draw at 0",
    "Panache": "every 5 cards deal 10|14 to all",
    "Sadistic Nature": "deal 5|7 per debuff", "Secret Technique": "fetch a skill from draw",
    "Secret Weapon": "fetch an attack from draw", "The Bomb": "in 3 turns deal 40|50 to all",
    "Thinking Ahead": "draw 2, put a card on draw", "Transmutation": "X random colorless cards",
    "Violence": "fetch 3|4 attacks from draw",
    # Status cards and curses
    "Wound": "unplayable", "Dazed": "unplayable, ethereal", "Slimed": "exhaust it for 1 energy",
    "Burn": "unplayable, 2 damage at end of turn", "Void": "unplayable, -1 energy when drawn",
    "AscendersBane": "unplayable curse", "Clumsy": "unplayable curse", "Decay": "curse, 2 damage",
    "CurseOfTheBell": "unplayable curse", "Doubt": "curse, 1 Weak each turn",
    "Injury": "unplayable curse", "Necronomicurse": "unplayable curse",
    "Normality": "curse, 3 cards a turn at most", "Pain": "curse, 1 HP per card played",
    "Parasite": "curse, -3 max HP if removed",
    "Pride": "curse", "Regret": "curse, 1 HP per hand card",
    "Shame": "curse, 1 Frail each turn", "Writhe": "unplayable curse",
}
POTIONS = {
    "Fire Potion": "deal 20", "Explosive Potion": "deal 10 to all", "Block Potion": "12 block",
    "BloodPotion": "heal 20% of max HP", "Dexterity Potion": "+2 Dexterity",
    "Energy Potion": "+2 energy", "Strength Potion": "+2 Strength", "Swift Potion": "draw 3",
    "FearPotion": "3 Vulnerable", "Weak Potion": "3 Weak", "Regen Potion": "heal 5 then less",
    "AncientPotion": "+1 Artifact", "FairyPotion": "revives you at 30% HP when you die",
    "SmokeBomb": "escape a normal fight", "LiquidBronze": "attackers take 3",
    "SteroidPotion": "+5 Strength this turn", "SpeedPotion": "+5 Dexterity this turn",
    "ElixirPotion": "exhaust any hand cards", "GamblersBrew": "swap any hand cards",
    "EssenceOfSteel": "+4 Plated Armor", "HeartOfIron": "+6 Metallicize",
    "PowerPotion": "pick a power at 0 cost", "SkillPotion": "pick a skill at 0 cost",
    "AttackPotion": "pick an attack at 0 cost",
    "ColorlessPotion": "pick a colorless card at 0 cost",
    "SneckoOil": "draw 5, costs random", "CunningPotion": "3 Shivs",
    "EntropicBrew": "fill slots with potions", "Fruit Juice": "+5 max HP",
    "LiquidMemories": "take a discard back at 0 cost", "DuplicationPotion": "next card plays twice",
    "DistilledChaos": "play top 3 of draw", "BlessingOfTheForge": "upgrade your hand this fight",
    "GhostInAJar": "1 Intangible", "CultistPotion": "+1 Strength each turn",
}
NAME_TO_ID = {"Strike": "Strike_R", "Defend": "Defend_R",
              "Jack of All Trades": "Jack Of All Trades", "Panic Button": "PanicButton",
              "Hand of Greed": "HandOfGreed",
              "Ascender's Bane": "AscendersBane", "Curse of the Bell": "CurseOfTheBell"}
ATTACK_INTENTS = ("ATTACK", "ATTACK_BUFF", "ATTACK_DEBUFF", "ATTACK_DEFEND")
# Damage per hit and hits, read back from the same text so one table says it once.
_DEAL = re.compile(r"deal (\d+(?:\|\d+)?)(?: x (\d+(?:\|\d+)?)| at random (\d+(?:\|\d+)?) times)?")
_BLOCK = re.compile(r"(?:^|, )(\d+(?:\|\d+)?) block")


def _side(token: str, upgraded: bool) -> str:
    return token.split("|")[-1 if upgraded else 0]


def card_text(card_id: str | None, upgraded: bool) -> str:
    text = CARDS.get(card_id or "", "")
    return re.sub(r"(\S+?)\|([^\s,]+)", lambda m: m[2] if upgraded else m[1], text)


def _power(creature: Mapping, power_id: str) -> int:
    return next((p.get("amount", 0) for p in creature.get("powers", ())
                 if p.get("id") == power_id), 0)


def _strip_upgrade(name: str) -> tuple[str, bool]:
    upgraded = name.endswith("+") or re.search(r"\+\d+$", name) is not None
    return re.sub(r"\+\d*$", "", name), upgraded


def named_card(label_name: str) -> str:
    """Text of a card known only by its printed name, as on reward and shop labels."""
    name, upgraded = _strip_upgrade(label_name.strip())
    return card_text(NAME_TO_ID.get(name, name), upgraded)


def attack_damage(card: Mapping, player: Mapping, target: Mapping, combat: Mapping) -> int | None:
    """Total this card would deal to ``target`` before block, from public numbers."""
    card_id, upgraded = card.get("id"), bool(card.get("upgrades"))
    text = CARDS.get(card_id or "", "")
    found = _DEAL.search(text)
    if card_id == "Body Slam":
        per_hit, hits = player.get("block", 0), 1
    elif found:
        per_hit = int(_side(found[1], upgraded))
        hits = int(_side(found[2] or found[3] or "1", upgraded))
        if "twice" in text:
            hits = 2
    else:
        return None
    strength = _power(player, "Strength")
    if card_id == "Heavy Blade":
        strength *= 5 if upgraded else 3
    if card_id == "Perfected Strike":
        piles = (*combat.get("hand", ()), *combat.get("draw_pile", ()),
                 *combat.get("discard_pile", ()))
        per_hit += (3 if upgraded else 2) * sum("Strike" in str(c.get("name", "")) for c in piles)
    if card_id == "Whirlwind":
        hits = max(player.get("energy", 0), 0)
    if card_id == "Fiend Fire":
        hits = max(len(combat.get("hand", ())) - 1, 0)
    total = float(per_hit + strength)
    if _power(player, "Weakened"):
        total *= 0.75
    if _power(target, "Vulnerable"):
        total *= 1.5
    return max(int(total), 0) * hits


def card_block(card: Mapping, player: Mapping) -> int:
    upgraded = bool(card.get("upgrades"))
    found = _BLOCK.search(CARDS.get(card.get("id") or "", ""))
    if card.get("id") == "Entrench":
        return player.get("block", 0)
    if not found:
        return 0
    total = float(int(_side(found[1], upgraded)) + _power(player, "Dexterity"))
    if _power(player, "Frail"):
        total *= 0.75
    return max(int(total), 0)


def incoming(combat: Mapping) -> int:
    total = 0
    for monster in combat.get("monsters", ()):
        if monster.get("is_gone") or monster.get("current_hp", 0) <= 0:
            continue
        if monster.get("intent") in ATTACK_INTENTS and monster.get("move_adjusted_damage", -1) >= 0:
            total += monster["move_adjusted_damage"] * max(monster.get("move_hits", 1), 1)
    return total


def _play(command: str, label: str, combat: Mapping) -> str:
    """What playing this card does now: its text, and damage or block against this turn."""
    parts = command.split()
    hand, player = combat.get("hand", ()), combat.get("player", {})
    number = int(parts[1]) - 1
    if not 0 <= number < len(hand):
        return label
    card = hand[number]
    text = card_text(card.get("id"), bool(card.get("upgrades")))
    notes = [text] if text else []
    if len(parts) > 2 and int(parts[2]) < len(combat.get("monsters", ())):
        target = combat["monsters"][int(parts[2])]
        damage = attack_damage(card, player, target, combat)
        if damage is not None:
            through = max(damage - target.get("block", 0), 0)
            left = max(target.get("current_hp", 0) - through, 0)
            notes.append(f"{through} through, it would have {left} HP" if left else
                         f"{through} through, KILLS it")
    block = card_block(card, player)
    if block:
        coming = incoming(combat)
        before = max(coming - player.get("block", 0), 0)
        notes.append(f"unblocked {before} > {max(before - block, 0)}")
    return f"{label}: " + "; ".join(notes) if notes else label


def _end_turn(label: str, combat: Mapping, hp: int) -> str:
    player = combat.get("player", {})
    unblocked = max(incoming(combat) - player.get("block", 0), 0)
    energy = player.get("energy", 0)
    parts = [f"{energy} energy unused"] if energy else []
    if unblocked >= hp:
        parts.append(f"take {unblocked}, YOU DIE")
    elif unblocked:
        parts.append(f"take {unblocked}, HP {hp} > {hp - unblocked}")
    else:
        parts.append("no damage gets through")
    return f"{label}: " + ", ".join(parts)


def _path_summary(nodes: Sequence[Mapping], x: int, y: int) -> str:
    """Fewest and most of each room type on the paths from this node to the boss."""
    by_place = {(n["x"], n["y"]): n for n in nodes}
    memo: dict[tuple[int, int], dict[str, tuple[int, int]]] = {}
    kinds = {"E": "elite", "R": "rest", "$": "shop", "?": "event", "M": "monster"}

    def walk(place: tuple[int, int]) -> dict[str, tuple[int, int]]:
        if place in memo:
            return memo[place]
        node = by_place.get(place)
        if node is None:
            return {}
        below = [walk((c["x"], c["y"])) for c in node.get("children", ())
                 if (c["x"], c["y"]) in by_place]
        spans = {}
        for name in kinds.values():
            lows = [b.get(name, (0, 0))[0] for b in below] or [0]
            highs = [b.get(name, (0, 0))[1] for b in below] or [0]
            own = int(kinds.get(node.get("symbol")) == name)
            spans[name] = (min(lows) + own, max(highs) + own)
        memo[place] = spans
        return spans

    spans = walk((x, y))
    return ", ".join(f"{name} {low}-{high}" if low != high else f"{name} {low}"
                     for name, (low, high) in spans.items() if high)


def annotate(observation: Mapping, candidates: Sequence[Mapping]) -> list[str]:
    """Each choice's label with what it does, in the same order."""
    combat = observation.get("combat_state") or {}
    hp = observation.get("current_hp") or 0
    potions = observation.get("potions", ())
    names = {p.get("name"): POTIONS.get(p.get("id"), "") for p in potions}
    for potion in (observation.get("screen_state") or {}).get("potions", ()):
        if isinstance(potion, Mapping):
            names.setdefault(potion.get("name"), POTIONS.get(potion.get("id"), ""))
    result = []
    for candidate in candidates:
        label, command = candidate["label"], candidate.get("command", "")
        if command.startswith("play ") and combat:
            label = _play(command, label, combat)
        elif command == "end" and combat:
            label = _end_turn(label, combat, hp)
        elif command.startswith("potion use "):
            text = names.get(label.removeprefix("use potion ").split(" -> ")[0], "")
            label = f"{label}: {text}" if text else label
        elif label.startswith(("take card ", "buy ")) and " (" in label:
            name = label.removeprefix("take card ").removeprefix("buy ").split(" (")[0]
            text = named_card(name)
            label = f"{label}: {text}" if text else label
        elif label.startswith("buy ") or label.startswith("take potion "):
            name = label.removeprefix("buy ").removeprefix("take potion ").split(" for ")[0]
            text = names.get(name, "")
            label = f"{label}: {text}" if text else label
        elif label.startswith("go to ") and observation.get("map"):
            found = re.search(r"x=(\d+), y=(\d+)", label)
            if found:
                summary = _path_summary(observation["map"], int(found[1]), int(found[2]))
                label = f"{label}; paths on to the boss: {summary}" if summary else label
        result.append(label)
    return result
