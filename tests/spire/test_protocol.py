"""First-combat actions and public observations from synthetic game messages."""

import copy
import json
from collections import Counter
from dataclasses import FrozenInstanceError, replace

import pytest

from spire.policies import RandomPolicy, StarterHeuristicPolicy
from spire.protocol import (
    BridgeCommandError,
    IllegalActionError,
    NotReadyError,
    ProtocolError,
    StaleActionError,
    UnsupportedStateError,
    combat_outcome,
    decision_from_message,
    validate_action,
)


def card(card_id, uuid, *, playable=True, cost=1):
    return {
        "id": card_id, "uuid": uuid, "name": card_id, "cost": cost,
        "upgrades": 0, "has_target": card_id != "Defend_R", "is_playable": playable,
        "type": "SKILL" if card_id == "Defend_R" else "ATTACK", "rarity": "BASIC",
    }


def monster(name="Louse", *, hp=10, gone=False):
    return {
        "id": name, "name": name, "current_hp": hp, "max_hp": 10, "block": 0,
        "intent": "ATTACK", "move_id": 4, "last_move_id": 6, "second_last_move_id": 3,
        "move_base_damage": 99, "move_adjusted_damage": 6, "move_hits": 1,
        "is_gone": gone, "half_dead": False,
        "powers": [{"id": "Strength", "name": "Strength", "amount": 1, "misc": 77}],
    }


@pytest.fixture
def raw():
    return {
        "in_game": True,
        "ready_for_command": True,
        "available_commands": ["play", "end", "potion", "key", "click", "wait", "state"],
        "game_state": {
            "class": "IRONCLAD", "ascension_level": 0, "floor": 1, "act": 1,
            "current_hp": 80, "max_hp": 80, "gold": 99,
            "screen_type": "NONE", "screen_name": "NONE", "screen_state": {},
            "is_screen_up": False, "room_phase": "COMBAT", "room_type": "MonsterRoom",
            "seed": 123456, "current_action": "SecretAction", "private_future": "secret",
            "deck": [card("Strike_R", "deck-1"), card("Defend_R", "deck-2")],
            "relics": [{"id": "Burning Blood", "name": "Burning Blood", "counter": -1}],
            "potions": [{"id": "Fire Potion", "can_use": True, "requires_target": True}],
            "combat_state": {
                "turn": 1, "rng": 555, "future": ["secret"],
                "hand": [card("Strike_R", "strike-1"), card("Defend_R", "defend-1")],
                "draw_pile": [card("Bash", "draw-1", cost=2), card("Strike_R", "draw-2")],
                "discard_pile": [], "exhaust_pile": [], "limbo": ["secret"],
                "monsters": [monster(), monster()],
                "player": {
                    "current_hp": 80, "max_hp": 80, "block": 0, "energy": 3,
                    "powers": [], "private_rng": 1,
                },
            },
        },
    }


def decision(raw, sequence=0, session="session"):
    return decision_from_message(raw, session_id=session, sequence=sequence)


def test_preserve_original_target_and_card_positions(raw):
    combat = raw["game_state"]["combat_state"]
    combat["monsters"].insert(0, monster(hp=0, gone=True))
    combat["hand"].insert(0, card("Dazed", "dazed", playable=False, cost=-2))
    result = decision(raw)
    assert [action.command for action in result.candidates] == [
        "play 2 1", "play 2 2", "play 3", "end",
    ]
    # Identical enemies still have distinct positional identities.
    assert result.candidates[0].id != result.candidates[1].id
    assert result.candidates[0].target_index == 1
    assert result.candidates[1].target_index == 2
    assert result.candidates[0].hand_index == 1


def test_tenth_card_uses_unambiguous_one_based_index(raw):
    combat = raw["game_state"]["combat_state"]
    combat["hand"] = [card("Strike_R", str(i), playable=False) for i in range(9)]
    combat["hand"].append(card("Defend_R", "tenth"))
    assert [action.command for action in decision(raw).candidates] == ["play 10", "end"]


def test_targeted_actions_exclude_dead_escaped_and_half_dead(raw):
    monsters = raw["game_state"]["combat_state"]["monsters"]
    monsters[0]["is_gone"] = True
    monsters[1]["half_dead"] = True
    assert [action.command for action in decision(raw).candidates] == ["play 2", "end"]


def test_unplayable_cards_are_not_candidates_and_potions_are_excluded(raw):
    raw["game_state"]["combat_state"]["hand"][0]["is_playable"] = False
    result = decision(raw)
    assert [action.command for action in result.candidates] == ["play 2", "end"]
    assert "potions" in result.observation["excluded_actions"]


def test_allowlist_removes_private_fields_at_every_level(raw):
    serialized = json.dumps(decision(raw).to_dict())
    for forbidden in (
        "seed", "uuid", "move_id", "last_move_id", "second_last_move_id",
        "move_base_damage", "current_action", "private", "rng", "future", "secret", "77",
    ):
        assert forbidden not in serialized
    assert "move_adjusted_damage" in serialized
    assert "Burning Blood" in serialized


def test_draw_order_and_uuid_changes_are_policy_invisible(raw):
    first = decision(raw).to_dict()["observation"]
    draw = raw["game_state"]["combat_state"]["draw_pile"]
    draw.reverse()
    for item in draw:
        item["uuid"] = "replacement"
    assert decision(raw).to_dict()["observation"] == first


@pytest.mark.parametrize("intent", ["NONE", "UNKNOWN", "DEBUG", "BUFF", "DEBUFF"])
def test_internal_damage_does_not_reveal_hidden_or_nonattack_intents(raw, intent):
    raw["game_state"]["combat_state"]["monsters"][0]["intent"] = intent
    public = decision(raw).observation["combat_state"]["monsters"][0]
    assert "move_adjusted_damage" not in public
    assert "move_hits" not in public
    assert "last_move_id" not in public


def test_observation_is_deeply_immutable_and_detached(raw):
    result = decision(raw)
    raw["game_state"]["combat_state"]["player"]["energy"] = 999
    assert result.observation["combat_state"]["player"]["energy"] == 3
    with pytest.raises(TypeError):
        result.observation["combat_state"]["player"]["energy"] = 1
    with pytest.raises(FrozenInstanceError):
        result.id = "changed"
    serialized = result.to_dict()
    serialized["observation"]["combat_state"]["player"]["energy"] = 99
    assert result.observation["combat_state"]["player"]["energy"] == 3


@pytest.mark.parametrize("session,sequence", [("session", 1), ("new-session", 0)])
def test_stale_actions_rejected_even_when_commands_still_match(raw, session, sequence):
    original = decision(raw)
    current = decision(raw, sequence=sequence, session=session)
    assert original.candidates[0].command == current.candidates[0].command
    with pytest.raises(StaleActionError):
        validate_action(current, original.candidates[0])
    with pytest.raises(StaleActionError):
        validate_action(current, original.candidates[0].id)


def test_forged_actions_and_unknown_ids_are_rejected(raw):
    result = decision(raw)
    original = result.candidates[0]
    assert validate_action(result, original.id) is original
    assert validate_action(result, original) is original
    with pytest.raises(IllegalActionError):
        validate_action(result, replace(original, command="play 10 8"))
    with pytest.raises(IllegalActionError):
        validate_action(result, f"{result.id}:play:99")


def test_unready_available_commands_do_not_authorize_play(raw):
    raw["ready_for_command"] = False
    with pytest.raises(NotReadyError):
        decision(raw)


def test_command_error_is_not_observation_or_gameplay_loss():
    error = {"error": "Selected card cannot be played", "ready_for_command": True}
    with pytest.raises(BridgeCommandError):
        decision(error)
    with pytest.raises(BridgeCommandError):
        combat_outcome(error, combat_floor=1)


@pytest.mark.parametrize("screen", ["HAND_SELECT", "GRID", "EVENT", "COMBAT_REWARD"])
def test_noncombat_or_selection_screen_requires_explicit_support(raw, screen):
    raw["game_state"]["screen_type"] = screen
    with pytest.raises(UnsupportedStateError):
        decision(raw)


def test_unknown_playable_card_is_explicit_capability_failure(raw):
    raw["game_state"]["combat_state"]["hand"].append(card("Clash", "clash"))
    with pytest.raises(UnsupportedStateError, match="Clash"):
        decision(raw)


def test_malformed_nested_field_cannot_smuggle_private_input(raw):
    raw["game_state"]["combat_state"]["player"]["energy"] = {"seed": 123}
    with pytest.raises(ProtocolError):
        decision(raw)


def test_combat_outcome_requires_engine_transition_and_matching_floor(raw):
    for enemy in raw["game_state"]["combat_state"]["monsters"]:
        enemy["current_hp"] = 0
        enemy["is_gone"] = True
    assert combat_outcome(raw, combat_floor=1) is None
    raw["game_state"].update(room_phase="COMPLETE", screen_type="COMBAT_REWARD")
    assert combat_outcome(raw, combat_floor=1) == "won"
    assert combat_outcome(raw, combat_floor=2) is None
    raw["ready_for_command"] = False
    assert combat_outcome(raw, combat_floor=1) is None


def test_death_requires_engine_screen_not_zero_hp(raw):
    game = raw["game_state"]
    game["current_hp"] = 0
    assert combat_outcome(raw, combat_floor=1) is None
    game.update(screen_type="GAME_OVER", screen_name="DEATH", screen_state={"victory": False})
    assert combat_outcome(raw, combat_floor=1) == "lost"
    game["screen_name"] = "UNLOCK"
    assert combat_outcome(raw, combat_floor=1) is None
    game["screen_name"] = "NEOW_UNLOCK"
    assert combat_outcome(raw, combat_floor=1) is None


def test_menu_or_wrong_room_completion_is_not_combat_victory(raw):
    assert combat_outcome({"in_game": False, "ready_for_command": True}, combat_floor=1) is None
    raw["game_state"].update(room_phase="COMPLETE", room_type="EventRoom")
    assert combat_outcome(raw, combat_floor=1) is None


def test_random_policy_reproducible_and_chooses_all_atomic_actions(raw):
    result = decision(raw)
    first, second = RandomPolicy(42), RandomPolicy(42)
    choices = [first.choose(result).id for _ in range(1000)]
    assert choices == [second.choose(result).id for _ in range(1000)]
    counts = Counter(choices)
    assert set(counts) == {candidate.id for candidate in result.candidates}
    assert all(180 < count < 320 for count in counts.values())


def test_heuristic_blocks_visible_intent_then_attacks(raw):
    policy = StarterHeuristicPolicy()
    assert policy.choose(decision(raw)).card_id == "Defend_R"
    raw["game_state"]["combat_state"]["player"]["block"] = 12
    assert policy.choose(decision(raw)).card_id == "Strike_R"


def test_policy_cannot_see_raw_seed_or_leak_internals(raw):
    original = decision(raw)
    modified = copy.deepcopy(raw)
    modified["game_state"]["seed"] = 999999
    modified["game_state"]["combat_state"]["monsters"][0]["move_id"] = 99
    assert StarterHeuristicPolicy().choose(original) == StarterHeuristicPolicy().choose(
        decision(modified)
    )
