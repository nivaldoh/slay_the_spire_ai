"""Adapter regressions grounded in captured original-engine transitions.

These tests replay observations, not game mechanics. Local trace checks verify
extraction provenance when the ignored run artifacts are available.
"""

import hashlib
import json
import os
from pathlib import Path

import pytest

from spire.protocol import (
    StaleActionError,
    combat_outcome,
    decision_from_message,
    validate_action,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures/engine_starter_transitions.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text())
CASES = {case["id"]: case for case in FIXTURE["transitions"]}


def decision(case, side):
    return decision_from_message(
        case[side], session_id=f"recorded:{case['id']}", sequence=case[f"{side}_sequence"]
    )


def combat(case_id, side):
    return decision(CASES[case_id], side).observation["combat_state"]


def power(creature, identifier):
    return next((item["amount"] for item in creature["powers"] if item["id"] == identifier), 0)


@pytest.mark.parametrize("case", FIXTURE["transitions"], ids=lambda case: case["id"])
def test_observed_commands_retain_card_and_target_identity(case):
    before = decision(case, "before")
    candidates = [action for action in before.candidates if action.command == case["command"]]
    assert len(candidates) == 1
    selected = validate_action(before, candidates[0])
    for field, expected in case["selected_action"].items():
        assert getattr(selected, field) == expected
    if selected.kind == "play":
        card = before.observation["combat_state"]["hand"][selected.hand_index]
        assert card["id"] == selected.card_id
        assert card["is_playable"] is True
        assert card["cost"] <= before.observation["combat_state"]["player"]["energy"]

    if case["after"]["game_state"]["room_phase"] == "COMBAT":
        after = decision(case, "after")
        with pytest.raises(StaleActionError):
            validate_action(after, selected)
        if selected.kind == "play":
            # Every captured nonterminal play is an ordinary-cost starter card.
            assert (
                before.observation["combat_state"]["player"]["energy"]
                - after.observation["combat_state"]["player"]["energy"]
                == card["cost"]
            )
        if after.observation["combat_state"]["player"]["energy"] == 0:
            assert all(action.kind == "end" for action in after.candidates)


def test_strike_damage_and_curl_up_are_preserved_in_public_observations():
    before = combat("strike_triggers_curl_up", "before")
    after = combat("strike_triggers_curl_up", "after")
    assert (before["player"]["energy"], after["player"]["energy"]) == (3, 2)
    assert (before["monsters"][0]["current_hp"], after["monsters"][0]["current_hp"]) == (14, 8)
    assert (before["monsters"][0]["block"], after["monsters"][0]["block"]) == (0, 7)
    assert power(before["monsters"][0], "Curl Up") == 7
    assert power(after["monsters"][0], "Curl Up") == 0
    assert before["monsters"][1]["current_hp"] == after["monsters"][1]["current_hp"] == 14


def test_bash_damage_vulnerable_and_second_louse_curl_up():
    before = combat("bash_adds_vulnerable", "before")
    after = combat("bash_adds_vulnerable", "after")
    assert (before["player"]["energy"], after["player"]["energy"]) == (3, 1)
    assert (before["monsters"][1]["current_hp"], after["monsters"][1]["current_hp"]) == (14, 6)
    assert (before["monsters"][1]["block"], after["monsters"][1]["block"]) == (0, 4)
    assert power(before["monsters"][1], "Curl Up") == 4
    assert power(after["monsters"][1], "Curl Up") == 0
    assert power(before["monsters"][1], "Vulnerable") == 0
    assert power(after["monsters"][1], "Vulnerable") == 2


def test_vulnerable_strike_observed_nine_damage_through_four_block():
    before = combat("vulnerable_strike_through_block", "before")
    after = combat("vulnerable_strike_through_block", "after")
    assert power(before["monsters"][1], "Vulnerable") == 2
    assert (before["monsters"][1]["block"], after["monsters"][1]["block"]) == (4, 0)
    assert (before["monsters"][1]["current_hp"], after["monsters"][1]["current_hp"]) == (6, 1)
    assert (before["player"]["energy"], after["player"]["energy"]) == (1, 0)


def test_defend_preserves_health_and_adds_five_block():
    before = combat("defend_adds_block", "before")
    after = combat("defend_adds_block", "after")
    assert (before["player"]["block"], after["player"]["block"]) == (0, 5)
    assert (before["player"]["energy"], after["player"]["energy"]) == (2, 1)
    assert before["player"]["current_hp"] == after["player"]["current_hp"] == 73
    assert before["monsters"] == after["monsters"]


def test_dead_first_monster_does_not_renumber_live_second_target():
    case = CASES["target_one_after_target_zero_died"]
    before = decision(case, "before")
    after = decision(case, "after")
    for observed in (before, after):
        monsters = observed.observation["combat_state"]["monsters"]
        assert [monster["id"] for monster in monsters] == [
            "FuzzyLouseNormal",
            "FuzzyLouseDefensive",
        ]
        assert monsters[0]["current_hp"] == 0 and monsters[0]["is_gone"] is True
        targeted = [action for action in observed.candidates if action.target_index is not None]
        assert targeted and {action.target_index for action in targeted} == {1}
    assert case["command"] == "play 3 1"
    assert after.observation["combat_state"]["monsters"][1]["current_hp"] == 8


@pytest.mark.parametrize(
    "case_id,hp_before,hp_after,block_before",
    [("partial_block_end_turn", 73, 71, 5), ("full_block_end_turn", 78, 78, 10)],
)
def test_end_turn_damage_block_clearing_and_energy_refresh(
    case_id, hp_before, hp_after, block_before
):
    before = combat(case_id, "before")
    after = combat(case_id, "after")
    assert before["player"]["current_hp"] == hp_before
    assert after["player"]["current_hp"] == hp_after
    assert before["player"]["block"] == block_before
    assert after["player"]["block"] == 0
    assert (before["player"]["energy"], after["player"]["energy"]) == (0, 3)
    assert after["turn"] == before["turn"] + 1
    assert before["monsters"][0]["is_gone"] is True
    assert before["monsters"][1]["move_adjusted_damage"] == 7


def test_louse_buff_strength_and_vulnerable_duration_survive_projection():
    before = combat("strength_and_vulnerable_tick", "before")
    after = combat("strength_and_vulnerable_tick", "after")
    assert before["monsters"][0]["intent"] == "BUFF"
    assert "move_adjusted_damage" not in before["monsters"][0]
    assert power(before["monsters"][0], "Strength") == 0
    assert power(after["monsters"][0], "Strength") == 3
    assert power(before["monsters"][0], "Vulnerable") == 2
    assert power(after["monsters"][0], "Vulnerable") == 1
    assert after["monsters"][0]["intent"] == "ATTACK"
    assert after["monsters"][0]["move_adjusted_damage"] == 8
    assert (before["monsters"][0]["block"], after["monsters"][0]["block"]) == (7, 0)


def test_weak_strike_observed_four_damage():
    before = combat("weak_strike", "before")
    after = combat("weak_strike", "after")
    assert power(before["player"], "Weakened") == 2
    assert (before["monsters"][1]["current_hp"], after["monsters"][1]["current_hp"]) == (8, 4)
    assert before["monsters"][1]["block"] == after["monsters"][1]["block"] == 0


@pytest.mark.parametrize(
    "case_id,hp_before,hp_after",
    [
        ("victory_heals_six", 64, 70),
        ("victory_heal_capped", 78, 80),
    ],
)
def test_engine_terminal_and_burning_blood_healing(case_id, hp_before, hp_after):
    case = CASES[case_id]
    before = decision(case, "before").observation
    assert before["current_hp"] == hp_before
    assert before["max_hp"] == 80
    assert any(relic["id"] == "Burning Blood" for relic in before["relics"])
    assert combat_outcome(case["before"], combat_floor=1) is None
    assert combat_outcome(case["after"], combat_floor=1) == "won"
    assert case["after"]["game_state"]["current_hp"] == hp_after
    assert "combat_state" not in case["after"]["game_state"]


def test_initial_debug_intent_is_retained_without_hidden_damage():
    monsters = combat("strike_triggers_curl_up", "before")["monsters"]
    assert all(monster["intent"] == "DEBUG" for monster in monsters)
    assert all("move_adjusted_damage" not in monster for monster in monsters)


def test_committed_fixture_excludes_private_fields_and_stays_small():
    forbidden = {
        "seed",
        "uuid",
        "draw_pile",
        "move_id",
        "move_base_damage",
        "last_move_id",
        "second_last_move_id",
        "current_action",
        "just_applied",
    }

    def check(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(FIXTURE)
    assert FIXTURE_PATH.stat().st_size < 50_000


def assert_recorded_subset(captured, original):
    if isinstance(captured, dict):
        for key, value in captured.items():
            assert key in original
            assert_recorded_subset(value, original[key])
    elif isinstance(captured, list):
        assert len(captured) == len(original)
        for value, source_value in zip(captured, original, strict=True):
            assert_recorded_subset(value, source_value)
    else:
        assert captured == original


@pytest.mark.parametrize("source_id", FIXTURE["sources"])
def test_fixture_matches_original_local_trace_when_available(source_id):
    root = Path(os.environ.get("SPIRE_EVIDENCE_ROOT", Path(__file__).resolve().parents[1]))
    source = FIXTURE["sources"][source_id]
    trace_path = root / source["trace_path"]
    if not trace_path.is_file():
        pytest.skip("Original traces are local artifacts; set SPIRE_EVIDENCE_ROOT to verify them")
    trace_bytes = trace_path.read_bytes()
    assert hashlib.sha256(trace_bytes).hexdigest() == source["trace_sha256"]
    records = [json.loads(line) for line in trace_bytes.splitlines()]
    manifest = json.loads((trace_path.parent.parent / "manifest.json").read_text())
    assert manifest["source_revision"] == source["source_revision"]
    assert manifest["source_status"] == ""
    assert records[-1]["kind"] == "result"
    assert records[-1]["result"]["status"] == source["episode_status"]
    for case in FIXTURE["transitions"]:
        if case["source"] != source_id:
            continue
        action = records[case["action_line"] - 1]
        before = records[case["before_line"] - 1]
        after = records[case["after_line"] - 1]
        assert action["kind"] == "action" and action["command"] == case["command"]
        assert action["sequence"] == before["sequence"] == case["before_sequence"]
        assert after["sequence"] == case["after_sequence"]
        assert after["previous_action_id"] == action["action_id"]
        assert_recorded_subset(case["before"], before["raw"])
        assert_recorded_subset(case["after"], after["raw"])
