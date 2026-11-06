"""The rule policy on synthetic messages: legality, the information boundary and the
decisions that lose a run when wrong. Card numbers come from recorded engine results."""

import pytest
from spire_messages import card, combat_message, message

from spire import decisions
from spire.__main__ import main
from spire.fullrun.rule_data import BAD_CARDS, BOSS_RELICS, CARD_VALUE, UPGRADED_ATTACKS
from spire.fullrun.rules import (
    LOOP_LIMIT,
    RulePolicy,
    SimpleCombatPolicy,
    base_damage,
    block_of,
    can_finish,
    damage_to,
    event_score,
    live_monsters,
)


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


@pytest.mark.parametrize(("card_id", "upgrades", "expected"), [
    ("Defend_R", 0, 5), ("Defend_R", 1, 8), ("Flame Barrier", 1, 16), ("Power Through", 1, 20),
    ("Armaments", 1, 5), ("Shrug It Off", 1, 11),
])
def test_block_numbers_match_recorded_engine_results(card_id, upgrades, expected):
    played = {**card(card_id, kind="SKILL", target=False), "upgrades": upgrades}
    assert block_of(played, {"powers": []}) == expected


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


def test_rules_command_runs_the_job_with_a_fresh_policy_for_each_run(monkeypatch, tmp_path):
    seen = {}

    def fake_play(output, config, *, policy_factory):
        seen.update(output=output, config=config, first=policy_factory(), second=policy_factory())
        return {"status": "completed"}

    monkeypatch.setattr("spire.fullrun.play.play", fake_play)
    monkeypatch.setattr("sys.argv", ["spire", "rules", "--seed", "ABC", "--output",
                                     str(tmp_path / "job")])
    assert main() == 0
    assert seen["config"]["seeds"] == ["ABC"] and seen["config"]["model"] == "rules"
    assert isinstance(seen["config"]["results"], str)
    assert isinstance(seen["first"], RulePolicy) and seen["first"] is not seen["second"]


def test_a_curse_is_worse_than_leaving():
    cursed = event_score("[Desecrate] Become Cursed - Decay.", 70, 80)
    assert cursed < event_score("[Leave]", 70, 80)


def fight(monster_fields, hand, *, hp=70, energy=3, player_powers=(), **combat_fields):
    """One live monster and an exact hand, with no potions."""
    raw = combat(hp=hp, hand=hand, **combat_fields)
    state = raw["game_state"]["combat_state"]
    state["monsters"][1].update(monster_fields)
    state["player"].update(energy=energy, powers=list(player_powers))
    return raw


def test_attacks_chip_block_that_never_falls():
    guardian = {"name": "Spheric Guardian", "id": "SphericGuardian", "block": 40,
                "intent": "DEFEND", "powers": [{"id": "Barricade", "amount": -1}]}
    choice = RulePolicy().choose(decide(fight(guardian, [strike(), strike("b"), defend()])))
    assert "Strike" in choice.label


def test_attacks_together_break_a_block_none_breaks_alone():
    hand = [strike(), strike("b"), defend()]
    raw = fight({"block": 8, "current_hp": 30}, hand, energy=2, damage=0)
    assert "Strike" in RulePolicy().choose(decide(raw)).label


def test_knowing_skull_leaves_at_equal_cost():
    options = ["[A Pick Me Up?] Get a Potion. Lose 6 HP.", "[Riches?] Gain 90 Gold. Lose 6 HP.",
               "[Success?] Get a Colorless Card. Lose 6 HP.", "[How do I leave?] Lose 6 HP."]
    best = max(options, key=lambda text: event_score(text, 40, 80))
    assert "leave" in best


def test_runic_dome_hidden_intent_still_counts_as_a_threat():
    raw = fight({"intent": "NONE"}, [strike(), defend()], hp=8)
    state = raw["game_state"]["combat_state"]["monsters"][1]
    state.pop("move_adjusted_damage")
    state.pop("move_hits", None)
    assert "Defend" in RulePolicy().choose(decide(raw)).label


def test_an_unknown_intent_is_not_a_phantom_attack():
    raw = fight({"intent": "UNKNOWN"}, [strike(), defend()], hp=8)
    assert "Strike" in RulePolicy().choose(decide(raw)).label


def test_a_targetless_attack_gets_played():
    boomerang = card("Sword Boomerang", target=False)
    raw = fight({}, [boomerang, defend()], damage=0)
    assert "Sword Boomerang" in RulePolicy().choose(decide(raw)).label


def test_a_card_with_no_score_still_beats_wasting_the_turn():
    raw = fight({}, [card("Violence", kind="SKILL", target=False)], damage=0)
    assert RulePolicy().choose(decide(raw)).command == "play 1"


def test_flight_halves_a_hit():
    flying = {"powers": [{"id": "Flight", "amount": 3}], "current_hp": 100, "block": 0}
    assert damage_to(flying, 6.0, 1) == (3, False)


def test_a_debuff_bonus_is_not_spent_into_artifact():
    bash = card("Bash", cost=2)
    guarded = {"powers": [{"id": "Artifact", "amount": 2}], "current_hp": 60}
    raw = fight(guarded, [bash, strike()], energy=3, damage=0)
    assert "Strike" in RulePolicy().choose(decide(raw)).label


def test_flex_comes_before_the_attack_it_boosts():
    flex = card("Flex", cost=0, kind="SKILL", target=False)
    raw = fight({}, [strike(), flex], damage=0)
    assert "Flex" in RulePolicy().choose(decide(raw)).label


def test_lethal_is_judged_per_target():
    raw = combat(hand=[strike()], damage=11, hp=8)
    state = raw["game_state"]["combat_state"]
    state["monsters"][0].update(current_hp=3, is_gone=False, intent="ATTACK", block=0,
                                move_adjusted_damage=1, move_hits=1)
    state["monsters"][1].update(current_hp=3)
    assert not can_finish(raw["game_state"], state, live_monsters(state))


def test_an_attack_that_kills_the_attacker_is_skipped():
    spiky = {"powers": [{"id": "Sharp Hide", "amount": 3}], "current_hp": 40}
    raw = fight(spiky, [strike()], hp=3, damage=0)
    assert RulePolicy().choose(decide(raw)).command == "end"


def test_end_of_turn_block_reduces_the_threat():
    raw = fight({}, [strike(), defend()], damage=4, hp=6,
                player_powers=[{"id": "Metallicize", "amount": 4}])
    assert "Strike" in RulePolicy().choose(decide(raw)).label


def test_free_block_with_a_cost_is_not_spent_on_nothing():
    through = card("Power Through", kind="SKILL", target=False)
    raw = fight({}, [through], damage=0, monster_hp=30)
    assert RulePolicy().choose(decide(raw)).command == "end"


def test_perfected_strike_counts_the_piles_in_play():
    perfected = card("Perfected Strike", cost=2)
    piles = {"hand": [perfected, strike()], "draw_pile": [strike("c")], "discard_pile": []}
    assert base_damage(perfected, {"powers": []}, [strike()] * 5, piles) == (12.0, 1)


def test_trip_deals_no_damage():
    player = {"powers": [{"id": "Strength", "amount": 3}]}
    assert base_damage(card("Trip", kind="SKILL"), player, [], {}) == (0.0, 0)


def test_a_two_card_grid_without_flags_removes_the_worst():
    cards = [card("Bash", cost=2), strike()]
    decision = decide(screen("GRID", ["choose"], ["Bash", "Strike"], {
        "cards": cards, "selected_cards": [], "num_cards": 2, "confirm_up": False},
        room_phase="EVENT"))
    assert RulePolicy().choose(decision).command == "choose 1"


def test_an_optional_hand_select_ignores_the_last_card_played():
    policy = RulePolicy()
    policy._last_played = "Armaments"
    decision = decide(screen("HAND_SELECT", ["choose", "confirm"], ["Strike"], {
        "hand": [strike()], "selected": [], "max_cards": 99, "can_pick_zero": True}))
    assert policy.choose(decision).command == "confirm"


def test_a_shop_potion_is_never_bought():
    state = {"cards": [], "relics": [], "potions": [
        {"name": "Fire Potion", "price": 40, "id": "Fire Potion"}], "purge_available": False}
    decision = decide(screen("SHOP_SCREEN", ["choose", "leave"], ["fire potion"], state,
                             gold=500, deck=[]))
    assert RulePolicy().choose(decision).command == "leave"


def test_match_and_keep_turns_a_fresh_card():
    decision = decide(screen("EVENT", ["choose"], ["a", "b"], {"event_id": "Match and Keep!",
        "options": [{"text": "Bash", "choice_index": 0}, {"text": "card1", "choice_index": 1}]}))
    assert RulePolicy().choose(decision).command == "choose 1"


def test_liquid_memories_waits_for_a_card_in_the_discard_pile():
    raw = fight({}, [strike()], hp=8, discard_pile=[])
    raw["game_state"]["potions"] = [{"id": "LiquidMemories", "name": "Liquid Memories",
                                     "can_use": True, "can_discard": True,
                                     "requires_target": False}]
    assert RulePolicy().choose(decide(raw)).command != "potion use 0"


@pytest.mark.parametrize("wire_id", ["SacredBark", "PanicButton"])
def test_tables_use_wire_ids(wire_id):
    assert wire_id in BOSS_RELICS or wire_id in CARD_VALUE


def test_rewards_further_on_do_not_pull_a_hurt_run_into_an_elite():
    nodes = [{"symbol": "E", "x": 0, "y": 5, "children": [{"x": 0, "y": 6}]},
             {"symbol": "M", "x": 1, "y": 5, "children": []},
             {"symbol": "R", "x": 0, "y": 6, "children": [{"x": 0, "y": 7}]},
             {"symbol": "T", "x": 0, "y": 7, "children": [{"x": 0, "y": 8}]},
             {"symbol": "R", "x": 0, "y": 8, "children": []}]
    state = {"next_nodes": nodes[:2], "current_node": {"x": 0, "y": 4}}
    decision = decide(screen("MAP", ["choose"], ["x=0", "x=1"], state, map=nodes, current_hp=40,
                             max_hp=80, floor=9))
    assert "monster" in RulePolicy().choose(decision).label


def test_simple_combat_blocks_only_when_attacked():
    hand = [strike(), defend(), card("Bash", cost=2)]
    assert "Defend" in SimpleCombatPolicy().choose(decide(fight({}, hand, damage=11))).label
    quiet = fight({"intent": "BUFF"}, hand)
    assert "Bash" in SimpleCombatPolicy().choose(decide(quiet)).label


def test_simple_combat_ends_the_turn_with_nothing_to_play():
    raw = fight({}, [card("Bash", cost=2, playable=False)], damage=11)
    assert SimpleCombatPolicy().choose(decide(raw)).command == "end"


def test_simple_combat_keeps_the_run_level_rules():
    assert SimpleCombatPolicy._map is RulePolicy._map
    assert SimpleCombatPolicy._event is RulePolicy._event
