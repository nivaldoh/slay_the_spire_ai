"""What the prompt says a move does, against numbers worked out by hand from the card text."""

from spire.localrl import facts


def strike(upgrades=0):
    return {"id": "Strike_R", "name": "Strike", "upgrades": upgrades}


def fight(hand, *, block=0, powers=(), monster_powers=(), energy=3, intent="ATTACK", damage=11):
    return {
        "hand": hand,
        "player": {"block": block, "energy": energy, "powers": list(powers)},
        "monsters": [{"name": "Jaw Worm", "current_hp": 40, "block": 3, "intent": intent,
                      "move_adjusted_damage": damage, "move_hits": 2,
                      "powers": list(monster_powers)}],
        "draw_pile": [], "discard_pile": [],
    }


def play(combat, command="play 1 0", label="play X"):
    observation = {"combat_state": combat, "current_hp": 15}
    return facts.annotate(observation, [{"label": label, "command": command}])[0]


def test_upgraded_card_text_reads_the_second_value():
    assert facts.card_text("Bash", False) == "deal 8, 2 Vulnerable"
    assert facts.card_text("Bash", True) == "deal 10, 3 Vulnerable"
    assert facts.named_card("Shrug It Off+") == "11 block, draw 1"


def test_attack_counts_strength_weak_vulnerable_and_target_block():
    # (6 + 2) x 0.75 = 6, x 1.5 = 9, floored; 3 block leaves 6 through.
    powers = [{"id": "Strength", "amount": 2}, {"id": "Weakened", "amount": 1}]
    label = play(fight([strike()], powers=powers,
                       monster_powers=[{"id": "Vulnerable", "amount": 1}]))
    assert "6 through, it would have 34 HP" in label


def test_multi_hit_and_kill():
    combat = fight([{"id": "Twin Strike", "upgrades": 1}])
    combat["monsters"][0]["current_hp"] = 5
    assert "11 through, KILLS it" in play(combat)


def test_block_card_shows_what_stays_unblocked():
    label = play(fight([{"id": "Defend_R", "upgrades": 0}], block=2,
                       powers=[{"id": "Frail", "amount": 1}]), command="play 1")
    # Two hits of 11, 2 block up: 20 unblocked; Frail makes Defend 3.
    assert "unblocked 20 > 17" in label


def test_end_turn_warns_of_a_lethal_turn():
    assert play(fight([]), command="end", label="end turn") == (
        "end turn: 3 energy unused, take 22, YOU DIE")


def test_paths_count_fewest_and_most_of_each_room():
    nodes = [
        {"x": 0, "y": 0, "symbol": "M", "children": [{"x": 0, "y": 1}, {"x": 1, "y": 1}]},
        {"x": 0, "y": 1, "symbol": "E", "children": []},
        {"x": 1, "y": 1, "symbol": "R", "children": []},
    ]
    observation = {"map": nodes}
    choice = {"label": "go to monster at x=0, y=0", "command": "choose 0"}
    label = facts.annotate(observation, [choice])[0]
    assert label.endswith("paths on to the boss: elite 0-1, rest 0-1, monster 1")


def test_every_card_text_with_damage_or_block_parses_on_both_sides():
    player = {"block": 0, "energy": 3, "powers": []}
    target = {"powers": []}
    for card_id, text in facts.CARDS.items():
        for upgrades in (0, 1):
            card = {"id": card_id, "upgrades": upgrades}
            if text.startswith("deal") and "draw pile size" not in text:
                assert facts.attack_damage(card, player, target, {}) is not None, card_id
            assert "|" not in facts.card_text(card_id, bool(upgrades)), card_id
            facts.card_block(card, player)
