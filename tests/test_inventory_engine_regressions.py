"""Minimal inventory engine observations; these tests do not implement game rules."""

import hashlib
import json
import os
from pathlib import Path

import pytest

from spire.evidence import audit_run
from spire.protocol import StaleActionError, combat_outcome, decision_from_message, validate_action

FIXTURE_PATH = Path(__file__).parent / "fixtures/engine_inventory_transitions.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text())
CASES = {case["id"]: case for case in FIXTURE["transitions"]}


def decision(case, side):
    return decision_from_message(
        case[side], session_id=f"inventory:{case['id']}", sequence=case[f"{side}_sequence"]
    )


def combat(identifier, side):
    return decision(CASES[identifier], side).observation["combat_state"]


def power(creature, identifier):
    return next((item["amount"] for item in creature["powers"] if item["id"] == identifier), 0)


@pytest.mark.parametrize("case", FIXTURE["transitions"], ids=lambda case: case["id"])
def test_recorded_action_remains_legal_and_bound_to_its_original_slots(case):
    before = decision(case, "before")
    candidates = [action for action in before.candidates if action.command == case["command"]]
    assert len(candidates) == 1
    selected = validate_action(before, candidates[0])
    for name, expected in case["selected_action"].items():
        assert getattr(selected, name) == expected
    if combat_outcome(case["after"], combat_floor=1) is None:
        after = decision(case, "after")
        with pytest.raises(StaleActionError):
            validate_action(after, selected)
        if selected.kind == "end":
            assert after.observation["combat_state"]["turn"] == (
                before.observation["combat_state"]["turn"] + 1
            )
            assert after.observation["combat_state"]["player"]["energy"] == 3


def test_cultist_ritual_appears_before_its_first_strength_tick():
    before = combat("cultist_ritual_appears", "before")
    after = combat("cultist_ritual_appears", "after")
    old, new = before["monsters"][0], after["monsters"][0]
    assert old["id"] == new["id"] == "Cultist"
    assert old["intent"] == "BUFF" and "move_adjusted_damage" not in old
    assert (power(old, "Ritual"), power(new, "Ritual")) == (0, 3)
    assert power(old, "Strength") == power(new, "Strength") == 0
    assert new["intent"] == "ATTACK" and new["move_adjusted_damage"] == 6
    assert before["player"]["current_hp"] == after["player"]["current_hp"] == 80


@pytest.mark.parametrize(
    "case_id,strength_before,strength_after,damage_before,damage_after",
    [
        ("cultist_ritual_strength_after_attack", 0, 3, 6, 9),
        ("cultist_second_strength_tick", 3, 6, 9, 12),
    ],
)
def test_observed_cultist_strength_and_next_displayed_attack(
    case_id, strength_before, strength_after, damage_before, damage_after
):
    before, after = combat(case_id, "before"), combat(case_id, "after")
    old, new = before["monsters"][0], after["monsters"][0]
    assert power(old, "Ritual") == power(new, "Ritual") == 3
    assert (power(old, "Strength"), power(new, "Strength")) == (strength_before, strength_after)
    assert (old["move_adjusted_damage"], new["move_adjusted_damage"]) == (
        damage_before,
        damage_after,
    )
    assert (before["player"]["block"], after["player"]["block"]) == (10, 0)
    assert before["player"]["current_hp"] == after["player"]["current_hp"] == 80


def test_jaw_worm_attack_defend_preserves_displayed_damage_and_adds_five_block():
    before = combat("jaw_worm_attack_defend_adds_block", "before")
    after = combat("jaw_worm_attack_defend_adds_block", "after")
    old, new = before["monsters"][0], after["monsters"][0]
    assert old["id"] == new["id"] == "JawWorm"
    assert old["intent"] == "ATTACK_DEFEND" and old["move_adjusted_damage"] == 7
    assert (old["block"], new["block"]) == (0, 5)
    assert new["intent"] == "DEFEND_BUFF" and "move_adjusted_damage" not in new
    assert power(old, "Strength") == power(new, "Strength") == 0
    assert before["player"]["current_hp"] == after["player"]["current_hp"] == 79
    assert (before["player"]["block"], after["player"]["block"]) == (10, 0)


@pytest.mark.parametrize(
    "case_id,strength_before,strength_after,intent,damage",
    [
        ("jaw_worm_defend_buff_adds_strength", 0, 3, "ATTACK_DEFEND", 10),
        ("jaw_worm_second_buff_changes_damage", 3, 6, "ATTACK", 17),
    ],
)
def test_jaw_worm_defend_buff_observed_block_strength_and_next_intent(
    case_id, strength_before, strength_after, intent, damage
):
    before, after = combat(case_id, "before"), combat(case_id, "after")
    old, new = before["monsters"][0], after["monsters"][0]
    assert old["intent"] == "DEFEND_BUFF" and "move_adjusted_damage" not in old
    assert (old["block"], new["block"]) == (0, 6)
    assert (power(old, "Strength"), power(new, "Strength")) == (strength_before, strength_after)
    assert new["intent"] == intent and new["move_adjusted_damage"] == damage
    assert (power(old, "Vulnerable"), power(new, "Vulnerable")) == (2, 1)
    assert before["player"]["current_hp"] == after["player"]["current_hp"] == 79


def test_jaw_worm_attack_spends_player_block_and_old_monster_block_expires():
    before = combat("jaw_worm_attack_consumes_player_block", "before")
    after = combat("jaw_worm_attack_consumes_player_block", "after")
    assert before["monsters"][0]["move_adjusted_damage"] == 17
    assert (before["monsters"][0]["block"], after["monsters"][0]["block"]) == (6, 0)
    assert (before["player"]["block"], after["player"]["block"]) == (15, 0)
    assert (before["player"]["current_hp"], after["player"]["current_hp"]) == (79, 77)


def test_same_species_louses_keep_distinct_curl_up_amounts_and_target_slots():
    before = combat("same_species_louse_curl_up", "before")
    after = combat("same_species_louse_curl_up", "after")
    assert [monster["id"] for monster in before["monsters"]] == ["FuzzyLouseNormal"] * 2
    assert [power(monster, "Curl Up") for monster in before["monsters"]] == [4, 7]
    assert (before["monsters"][0]["current_hp"], after["monsters"][0]["current_hp"]) == (10, 4)
    assert (before["monsters"][0]["block"], after["monsters"][0]["block"]) == (0, 4)
    assert power(after["monsters"][0], "Curl Up") == 0
    assert before["monsters"][1] == after["monsters"][1]


def test_dead_first_same_species_louse_does_not_renumber_surviving_target():
    case = CASES["same_species_target_one_after_kill"]
    assert case["command"] == "play 2 1"
    for side in ("before", "after"):
        observed = decision(case, side)
        monsters = observed.observation["combat_state"]["monsters"]
        assert [monster["id"] for monster in monsters] == ["FuzzyLouseNormal"] * 2
        assert monsters[0]["current_hp"] == 0 and monsters[0]["is_gone"] is True
        targeted = [action for action in observed.candidates if action.target_index is not None]
        assert {action.target_index for action in targeted} <= {1}
    before, after = combat(case["id"], "before"), combat(case["id"], "after")
    assert (before["monsters"][1]["current_hp"], after["monsters"][1]["current_hp"]) == (11, 5)
    assert (before["monsters"][1]["block"], after["monsters"][1]["block"]) == (0, 7)
    assert power(before["monsters"][1], "Curl Up") == 7
    assert power(after["monsters"][1], "Curl Up") == 0


def test_same_species_louse_buff_preserves_strength_after_curl_up_block_expires():
    before = combat("same_species_louse_strength_and_block_expire", "before")
    after = combat("same_species_louse_strength_and_block_expire", "after")
    old, new = before["monsters"][1], after["monsters"][1]
    assert old["intent"] == "BUFF" and "move_adjusted_damage" not in old
    assert (old["block"], new["block"]) == (7, 0)
    assert (power(old, "Strength"), power(new, "Strength")) == (3, 6)
    assert new["intent"] == "ATTACK" and new["move_adjusted_damage"] == 13


@pytest.mark.parametrize("source_id", ["attempt_0005", "attempt_0011"])
def test_max_hp_variant_is_labeled_outside_catalog(source_id):
    excluded = FIXTURE["sources"][source_id]
    assert (excluded["starting_hp"], excluded["max_hp"], excluded["starting_gold"]) == (88, 88, 99)
    assert excluded["catalog_eligible"] is False
    assert excluded["catalog_scenario_id"] is None
    assert "Prefix chose a max-HP variant" in excluded["catalog_exclusion_reasons"]


def test_private_fields_are_absent_and_fixture_stays_small():
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

    def inspect(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    inspect(FIXTURE)
    assert FIXTURE_PATH.stat().st_size < 100_000


def assert_subset(captured, original):
    if isinstance(captured, dict):
        for name, value in captured.items():
            assert name in original
            assert_subset(value, original[name])
    elif isinstance(captured, list):
        assert len(captured) == len(original)
        for value, source in zip(captured, original, strict=True):
            assert_subset(value, source)
    else:
        assert captured == original


@pytest.mark.parametrize("source_id", FIXTURE["sources"])
def test_inventory_fixture_links_audited_original_trace_when_available(source_id):
    root = Path(os.environ.get("SPIRE_EVIDENCE_ROOT", Path(__file__).resolve().parents[1]))
    source = FIXTURE["sources"][source_id]
    path = root / source["trace_path"]
    if not path.is_file():
        pytest.skip("Set SPIRE_EVIDENCE_ROOT to verify original local inventory evidence")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source["trace_sha256"]
    run = path.parent.parent
    for name, key in (
        ("manifest.json", "manifest_sha256"),
        ("source.patch", "source_patch_sha256"),
    ):
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == source[key]
    audited = audit_run(run)
    assert audited["valid"], audited["issues"]
    assert audited["manifest"]["status"] == "completed"
    assert audited["manifest"]["source_revision"] == source["source_revision"]
    assert audited["manifest"]["source_status"] == source["source_status"]
    assert (
        audited["manifest"]["source_files"]["src/spire/protocol.py"]
        == (source["protocol_source_sha256"])
    )
    assert audited["episodes"][0]["status"] == source["episode_status"]
    assert audited["episodes"][0]["combat_start_sha256"] == source["combat_start_sha256"]
    records = [json.loads(line) for line in path.read_text().splitlines()]
    for case in FIXTURE["transitions"]:
        if case["source"] != source_id:
            continue
        before, selected, action, after, execution = (
            records[case[f"{name}_line"] - 1]
            for name in ("before", "decision", "action", "after", "execution")
        )
        assert action["kind"] == "action" and action["command"] == case["command"]
        assert before["sequence"] == action["sequence"] == case["before_sequence"]
        assert after["sequence"] == execution["sequence"] == case["after_sequence"]
        assert selected["selected_action_id"] == action["action_id"]
        assert execution["action_id"] == after["previous_action_id"] == action["action_id"]
        assert execution["status"] == "next_stable_state"
        candidate = next(
            item for item in selected["decision"]["candidates"] if item["id"] == action["action_id"]
        )
        assert all(candidate[key] == value for key, value in case["selected_action"].items())
        assert_subset(case["before"], before["raw"])
        assert_subset(case["after"], after["raw"])


def test_two_defensive_louses_keep_independent_intents_and_apply_weak():
    before = combat("defensive_louses_apply_weak", "before")
    after = combat("defensive_louses_apply_weak", "after")
    assert [monster["id"] for monster in before["monsters"]] == ["FuzzyLouseDefensive"] * 2
    assert [monster["intent"] for monster in before["monsters"]] == ["ATTACK", "DEBUFF"]
    assert before["monsters"][0]["move_adjusted_damage"] == 6
    assert "move_adjusted_damage" not in before["monsters"][1]
    assert (power(before["player"], "Weakened"), power(after["player"], "Weakened")) == (0, 2)
    assert (before["player"]["block"], after["player"]["block"]) == (10, 0)
    assert before["player"]["current_hp"] == after["player"]["current_hp"] == 88


def test_weak_strike_hits_original_second_defensive_slot_and_triggers_its_curl_up():
    case = CASES["weak_strike_targets_second_defensive_louse"]
    before, after = combat(case["id"], "before"), combat(case["id"], "after")
    assert case["command"] == "play 1 1"
    assert power(before["player"], "Weakened") == 1
    assert before["monsters"][0]["is_gone"] is True
    targets = {
        action.target_index
        for action in decision(case, "before").candidates
        if action.target_index is not None
    }
    assert targets == {1}
    assert (before["monsters"][1]["current_hp"], after["monsters"][1]["current_hp"]) == (15, 11)
    assert (before["monsters"][1]["block"], after["monsters"][1]["block"]) == (0, 3)
    assert (power(before["monsters"][1], "Curl Up"), power(after["monsters"][1], "Curl Up")) == (
        3,
        0,
    )


def test_cultist_probe_loses_six_hp_before_next_displayed_attack_rises_to_nine():
    before = combat("cultist_probe_unblocked_attack", "before")
    after = combat("cultist_probe_unblocked_attack", "after")
    assert before["player"]["block"] == 0
    assert (before["player"]["current_hp"], after["player"]["current_hp"]) == (80, 74)
    assert (
        before["monsters"][0]["move_adjusted_damage"],
        after["monsters"][0]["move_adjusted_damage"],
    ) == (6, 9)
    assert (power(before["monsters"][0], "Strength"), power(after["monsters"][0], "Strength")) == (
        0,
        3,
    )


def test_cultist_probe_reaches_actual_engine_death_after_displayed_twenty_one_attack():
    case = CASES["cultist_probe_engine_death"]
    before = decision(case, "before").observation["combat_state"]
    assert before["player"]["current_hp"] == 20 and before["player"]["block"] == 0
    assert power(before["monsters"][0], "Ritual") == 3
    assert power(before["monsters"][0], "Strength") == 15
    assert before["monsters"][0]["move_adjusted_damage"] == 21
    after = case["after"]["game_state"]
    assert after["current_hp"] == 0
    assert after["screen_type"] == "GAME_OVER" and after["screen_name"] == "DEATH"
    assert after["screen_state"]["victory"] is False
    assert combat_outcome(case["after"], combat_floor=1) == "lost"


def test_jaw_worm_probe_unblocked_attack_defend_loses_seven_hp_and_adds_five_block():
    before = combat("jaw_worm_probe_unblocked_attack_defend", "before")
    after = combat("jaw_worm_probe_unblocked_attack_defend", "after")
    old, new = before["monsters"][0], after["monsters"][0]
    assert old["id"] == new["id"] == "JawWorm"
    assert old["intent"] == "ATTACK_DEFEND" and old["move_adjusted_damage"] == 7
    assert (before["player"]["current_hp"], after["player"]["current_hp"]) == (69, 62)
    assert before["player"]["block"] == after["player"]["block"] == 0
    assert (old["block"], new["block"]) == (0, 5)
    assert new["intent"] == "DEFEND_BUFF" and "move_adjusted_damage" not in new


def test_jaw_worm_probe_reaches_actual_engine_death_after_displayed_sixteen_attack():
    case = CASES["jaw_worm_probe_engine_death"]
    before = decision(case, "before").observation["combat_state"]
    assert before["player"]["current_hp"] == 5 and before["player"]["block"] == 0
    assert power(before["monsters"][0], "Strength") == 9
    assert before["monsters"][0]["intent"] == "ATTACK_DEFEND"
    assert before["monsters"][0]["move_adjusted_damage"] == 16
    after = case["after"]["game_state"]
    assert after["current_hp"] == 0
    assert after["screen_type"] == "GAME_OVER" and after["screen_name"] == "DEATH"
    assert after["screen_state"]["victory"] is False
    assert combat_outcome(case["after"], combat_floor=1) == "lost"


def test_fixture_links_completed_inventory_and_catalog_admissions_when_available():
    assert FIXTURE["inventory_status_at_extraction"] == "completed"
    assert len(FIXTURE["inventory_sha256"]) == 64
    root = Path(os.environ.get("SPIRE_EVIDENCE_ROOT", Path(__file__).resolve().parents[1]))
    path = root / FIXTURE["inventory_path"]
    if not path.is_file():
        pytest.skip("Set SPIRE_EVIDENCE_ROOT to verify original inventory admission evidence")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == FIXTURE["inventory_sha256"]
    parent = json.loads(path.read_text())
    assert parent["status"] == "completed" and parent["admissions_valid"] is True
    assert parent["contract_sha256"] == FIXTURE["contract_sha256"]
    assert parent["engine_pins"] == FIXTURE["engine_pins"]
    admitted = {item["expected_start_sha256"]: item["id"] for item in parent["admissions"]}
    for source in FIXTURE["sources"].values():
        attempt = parent["attempts"][source["attempt_index"]]
        assert attempt["assignment_id"] == source["assignment_id"]
        assert attempt["status"] == source["episode_status"]
        assert attempt["files"]["episode-0000/trace.jsonl"] == source["trace_sha256"]
        eligibility = attempt["audit"]["eligibility"]
        assert eligibility["eligible"] == source["catalog_eligible"]
        assert eligibility["reasons"] == source["catalog_exclusion_reasons"]
        assert eligibility["monster_ids"] == source["monster_ids"]
        assert admitted.get(source["combat_start_sha256"]) == source["catalog_scenario_id"]


@pytest.mark.parametrize("repeat", FIXTURE["repeats"], ids=lambda item: item["scenario_id"])
def test_admitted_scenario_repeat_matches_full_public_trajectory_when_available(repeat):
    root = Path(os.environ.get("SPIRE_EVIDENCE_ROOT", Path(__file__).resolve().parents[1]))
    source = FIXTURE["sources"][repeat["discovery_source"]]
    original, replay = root / source["trace_path"], root / repeat["repeat_trace_path"]
    if not original.is_file() or not replay.is_file():
        pytest.skip("Set SPIRE_EVIDENCE_ROOT to verify original inventory repeat evidence")
    assert hashlib.sha256(original.read_bytes()).hexdigest() == source["trace_sha256"]
    assert hashlib.sha256(replay.read_bytes()).hexdigest() == repeat["repeat_trace_sha256"]
    assert (
        hashlib.sha256((replay.parent.parent / "manifest.json").read_bytes()).hexdigest()
        == repeat["repeat_manifest_sha256"]
    )
    left, right = audit_run(original.parent.parent), audit_run(replay.parent.parent)
    assert left["valid"] and right["valid"]
    before, after = left["episodes"][0], right["episodes"][0]
    assert before["status"] == after["status"] == "won"
    assert before["combat_start_sha256"] == after["combat_start_sha256"]
    assert before["prefix"] == after["prefix"]
    assert (
        len(before["transitions"]) == len(after["transitions"]) == repeat["matching_combat_actions"]
    )
    for old, new in zip(before["transitions"], after["transitions"], strict=True):
        for key in ("command", "observation", "next_observation"):
            assert old[key] == new[key]
