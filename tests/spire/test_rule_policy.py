"""The rule policy on synthetic messages: legality, the information boundary and the
decisions that lose a run when wrong. Card numbers come from recorded engine results."""

import pytest
from spire_messages import card, combat_message, message

from spire import decisions
from spire.fullrun.rule_data import BAD_CARDS, UPGRADED_ATTACKS
from spire.fullrun.rules import LOOP_LIMIT, RulePolicy, base_damage, event_score


def decide(raw):
    return decisions.decision_from_message(raw, session_id="s", sequence=1)


def combat(hp=70, monster_hp=30, damage=11, **fields):
    raw = combat_message(**fields)
    state = raw["game_state"]["combat_state"]
    state["player"]["current_hp"] = hp
    state["monsters"][1].update(current_hp=monster_hp, move_adjusted_damage=damage)
    raw["game_state"]["potions"] = []
    return raw


def defend():
    return card("Defend_R", "Defend", kind="SKILL", target=False, uuid="d")


def strike(uuid="a"):
    return card("Strike_R", "Strike", uuid=uuid)


def screen(kind, commands, choices, state, **game):
    return message(commands, screen_type=kind, choice_list=choices, screen_state=state, **game)


def test_draw_order_cannot_change_a_choice():
    pile = [card("Bash", cost=2, uuid="z"), card("Anger", cost=0, uuid="y")]
    first = RulePolicy().choose(decide(combat(draw_pile=pile)))
    second = RulePolicy().choose(decide(combat(draw_pile=pile[::-1])))
    assert first.command == second.command


def test_every_choice_is_a_candidate_on_an_unknown_screen():
    decision = decide(screen("SOMETHING_NEW", ["choose", "proceed"], ["a", "b"], {}))
    assert RulePolicy().choose(decision) in decision.candidates


def test_blocks_a_lethal_hit_when_it_cannot_kill():
    choice = RulePolicy().choose(decide(combat(hp=8, damage=11, hand=[strike(), defend()])))
    assert "Defend" in choice.label


def test_attacks_instead_of_blocking_when_the_hand_finishes_the_fight():
    choice = RulePolicy().choose(decide(combat(hp=8, monster_hp=6, damage=11,
                                               hand=[strike(), defend()])))
    assert "Strike" in choice.label


def test_ends_the_turn_when_nothing_helps():
    raw = combat(hand=[card("Bash", cost=2, playable=False)])
    assert RulePolicy().choose(decide(raw)).command == "end"


def test_skills_wait_against_gremlin_nob():
    raw = combat(hand=[strike(), defend()], damage=2)
    raw["game_state"]["combat_state"]["monsters"][1]["powers"] = [
        {"id": "Anger", "name": "Enrage", "amount": 2}]
    assert "Strike" in RulePolicy().choose(decide(raw)).label


@pytest.mark.parametrize(("card_id", "upgrades", "expected"), [
    ("Twin Strike", 1, (7.0, 2)), ("Pummel", 1, (2.0, 5)), ("Bash", 1, (10.0, 1)),
    ("Searing Blow", 2, (21.0, 1)), ("Strike_R", 0, (6.0, 1)),
])
def test_card_numbers_match_recorded_engine_results(card_id, upgrades, expected):
    played = {**card(card_id), "upgrades": upgrades}
    assert base_damage(played, {"powers": []}, [], {}) == expected


def test_body_slam_adds_strength_to_block():
    player = {"block": 9, "powers": [{"id": "Strength", "amount": 3}]}
    assert base_damage(card("Body Slam"), player, [], {}) == (12.0, 1)


def test_upgrade_table_covers_only_known_attacks():
    assert all(hits for _, hits in UPGRADED_ATTACKS.values())


def test_a_stuck_state_leaves_by_a_button():
    decision = decide(screen("GRID", ["choose", "confirm"], ["Strike"], {
        "cards": [strike()], "selected_cards": [], "num_cards": 1, "confirm_up": False}))
    policy = RulePolicy()
    chosen = [policy.choose(decision).command for _ in range(LOOP_LIMIT + 1)]
    assert chosen[-1] == "confirm"


def test_a_skipped_card_reward_is_not_reopened():
    policy = RulePolicy()
    weak = [{**card("Strike_R", "Strike"), "rarity": "BASIC"}]
    reward = decide(screen("CARD_REWARD", ["choose", "skip"], ["strike"],
                           {"cards": weak, "skip_available": True}))
    assert policy.choose(reward).command == "skip"
    back = decide(screen("COMBAT_REWARD", ["choose", "proceed"], ["card"],
                         {"rewards": [{"reward_type": "CARD"}]}))
    assert policy.choose(back).command == "proceed"


def test_purge_removes_a_curse_before_a_strike():
    cards = [strike(), card("Writhe", kind="CURSE", target=False, uuid="w")]
    assert "Writhe" in BAD_CARDS
    decision = decide(screen("GRID", ["choose"], ["Strike", "Writhe"], {
        "cards": cards, "selected_cards": [], "num_cards": 1, "confirm_up": False,
        "for_purge": True}))
    assert RulePolicy().choose(decision).command == "choose 1"


def test_a_selected_grid_card_is_confirmed_and_never_deselected():
    chosen = strike()
    decision = decide(screen("GRID", ["choose", "confirm"], ["Strike"], {
        "cards": [chosen], "selected_cards": [chosen], "num_cards": 1, "confirm_up": False}))
    assert RulePolicy().choose(decision).command == "confirm"


def test_route_avoids_an_elite_at_low_health():
    nodes = [{"symbol": "E", "x": 0, "y": 5, "children": []},
             {"symbol": "M", "x": 1, "y": 5, "children": []}]
    state = {"next_nodes": nodes, "current_node": {"x": 0, "y": 4}}
    decision = decide(screen("MAP", ["choose"], ["x=0", "x=1"], state, map=nodes, current_hp=20,
                             max_hp=80, floor=9))
    assert "monster" in RulePolicy().choose(decision).label


@pytest.mark.parametrize(("text", "hp", "safe"), [
    ("[Reach Inside] Lose 5 HP. 25%: Find a Relic.", 4, False),
    ("[Pray] Remove a card from your deck. Lose 7 HP.", 60, True),
])
def test_an_event_never_pays_with_the_whole_health_bar(text, hp, safe):
    assert (event_score(text, hp, 80) > 0) is safe


def test_a_curse_is_worse_than_leaving():
    cursed = event_score("[Desecrate] Become Cursed - Decay.", 70, 80)
    assert cursed < event_score("[Leave]", 70, 80)
