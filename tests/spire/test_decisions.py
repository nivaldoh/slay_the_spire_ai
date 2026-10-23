"""Full-run choices and public observations from synthetic game messages."""

import pytest
from spire_messages import card, combat_message, message

from spire import decisions
from spire.protocol import UnsupportedStateError


def commands(decision):
    return {choice.command: choice.label for choice in decision.candidates}


def test_combat_choices_keep_raw_targets_and_offer_identical_cards_once():
    decision = decisions.decision_from_message(combat_message(), session_id="s", sequence=4)
    assert commands(decision) == {
        "play 1 1": "play Strike (1 attack) -> Jaw Worm [1]",
        "play 3": "play Defend (1 skill)",
        "potion use 0 1": "use potion Fire Potion -> Jaw Worm [1]",
        "potion discard 0": "discard potion Fire Potion",
        "end": "end turn",
    }
    assert all(choice.decision_id == "s:4" for choice in decision.candidates)


def test_observation_hides_order_rng_and_engine_internals():
    observation = decisions.decision_from_message(
        combat_message(), session_id="s", sequence=1
    ).to_dict()["observation"]
    assert "seed" not in observation
    combat = observation["combat_state"]
    assert [c["id"] for c in combat["draw_pile"]] == ["Anger", "Bash"]
    assert all("uuid" not in c for c in combat["hand"] + combat["draw_pile"])
    worm = combat["monsters"][1]
    assert "move_id" not in worm and "move_base_damage" not in worm
    assert worm["move_adjusted_damage"] == 11
    assert worm["powers"] == [{"id": "Strength", "name": "Strength", "amount": 3}]


def test_frozen_eye_keeps_the_visible_draw_order():
    raw = combat_message()
    raw["game_state"]["relics"] = [{"id": "Frozen Eye", "name": "Frozen Eye", "counter": -1}]
    observation = decisions.decision_from_message(raw, session_id="s", sequence=1).observation
    assert [c["id"] for c in observation["combat_state"]["draw_pile"]] == ["Bash", "Anger"]


@pytest.mark.parametrize(("screen", "state", "choices", "expected"), [
    ("MAP", {"next_nodes": [{"x": 2, "y": 4, "symbol": "E"}]}, ["x=2"],
     "go to elite at x=2, y=4"),
    ("MAP", {"next_nodes": []}, ["boss"], "go to the boss (Hexaghost)"),
    ("CARD_REWARD", {"cards": [card("Anger", cost=0)]}, ["anger"], "take card Anger (0 attack)"),
    ("CARD_REWARD", {"cards": []}, ["bowl"], "take Singing Bowl's +2 max HP instead of a card"),
    ("COMBAT_REWARD", {"rewards": [{"reward_type": "POTION", "potion": {"name": "Fire Potion"}}]},
     ["potion"], "take potion Fire Potion"),
    ("SHOP_SCREEN", {"purge_cost": 75, "cards": [], "relics": [], "potions": []}, ["purge"],
     "pay 75 gold to remove a card"),
    ("SHOP_SCREEN", {"cards": [{**card("Inflame", kind="POWER"), "price": 160}]}, ["inflame"],
     "buy Inflame (1 power) for 160 gold"),
    ("EVENT", {"options": [{"text": "[Locked]", "disabled": True},
                           {"text": "[Pray] Gain 5 Max HP.", "choice_index": 0}]},
     ["pray"], "[Pray] Gain 5 Max HP."),
    ("REST", {"rest_options": ["smith"]}, ["smith"], "smith: upgrade a card"),
])
def test_noncombat_choices_carry_their_screen_details(screen, state, choices, expected):
    raw = message(["choose"], screen_type=screen, screen_state=state, choice_list=choices,
                  act_boss="Hexaghost")
    decision = decisions.decision_from_message(raw, session_id="s", sequence=1)
    assert decision.candidates[0].command == "choose 0"
    assert decision.candidates[0].label == expected


def test_buttons_are_choices_but_raw_input_and_polling_never_are():
    raw = message(["skip", "key", "click", "wait", "state"], screen_type="CARD_REWARD",
                  screen_state={"cards": []})
    decision = decisions.decision_from_message(raw, session_id="s", sequence=1)
    assert commands(decision) == {"skip": "skip this card reward"}
    with pytest.raises(UnsupportedStateError):
        decisions.decision_from_message(message(["key", "click", "wait", "state"]),
                                       session_id="s", sequence=2)


@pytest.mark.parametrize(("name", "victory", "expected"), [
    ("DEATH", False, "lost"), ("VICTORY", True, "won"), ("UNLOCK", False, None),
])
def test_only_death_and_victory_screens_end_a_run(name, victory, expected):
    raw = message(["proceed"], screen_type="GAME_OVER", screen_name=name,
                  screen_state={"victory": victory, "score": 100})
    assert decisions.run_outcome(raw) == expected
    assert decisions.run_outcome({**raw, "ready_for_command": False}) is None


def test_grid_confirm_view_never_offers_the_cancel_that_hangs_communicationmod():
    # Observed 2026-10-12 (Bonfire Spirits purge): cancel here produced no reply.
    raw = message(["confirm", "cancel", "key", "click", "wait", "state"], screen_type="GRID",
                  screen_state={"confirm_up": True, "for_purge": True, "num_cards": 1,
                                "selected_cards": [], "cards": [card("Strike_R", "Strike")]})
    decision = decisions.decision_from_message(raw, session_id="s", sequence=1)
    assert commands(decision) == {"confirm": "confirm"}


def test_grid_labels_an_already_selected_copy_as_deselect():
    # Observed 2026-10-12 (Neow remove 2): choosing the first of five identical Strikes
    # again only toggled it off, seven times in one run.
    strikes = [card("Strike_R", "Strike", uuid=f"s{i}") for i in range(2)]
    raw = message(["choose", "key", "click", "wait", "state"], screen_type="GRID",
                  choice_list=["strike", "strike"],
                  screen_state={"for_purge": True, "num_cards": 2, "cards": strikes,
                                "selected_cards": [strikes[0]]})
    decision = decisions.decision_from_message(raw, session_id="s", sequence=1)
    assert commands(decision) == {"choose 0": "deselect Strike (1 attack)",
                                  "choose 1": "select Strike (1 attack)"}
