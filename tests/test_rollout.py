"""Regressions for the declared noncombat prefix and evidence files."""

import json

import pytest

from spire.protocol import ProtocolError
from spire.rollout import prefix_command, write_json


def neow(options):
    return {
        "available_commands": ["choose"],
        "game_state": {
            "screen_type": "EVENT",
            "screen_state": {"event_id": "Neow Event", "options": options},
        },
    }


def test_prefix_uses_enabled_choice_index_and_max_hp():
    message = neow(
        [
            {"text": "Max HP", "choice_index": 0, "disabled": True},
            {"text": "Enemies in your next 3 combats have 1 HP", "choice_index": 1},
            {"text": "[Max HP +10%]", "choice_index": 4},
        ]
    )
    assert prefix_command(message) == "CHOOSE 4"


def test_prefix_refuses_a_changed_start_distribution():
    message = neow(
        [
            {"text": "Choose a card", "choice_index": 0},
            {"text": "Obtain a random relic", "choice_index": 1},
        ]
    )
    with pytest.raises(ProtocolError, match="without max HP"):
        prefix_command(message)


def test_neow_four_option_profile_can_preserve_starter_deck():
    # Observed original-engine failure: profile offers four choices, no max HP.
    message = neow(
        [
            {"label": "Choose a Card to obtain", "choice_index": 0},
            {"label": "Obtain 100 Gold", "choice_index": 1},
            {"label": "Take 24 damage Gain 250 Gold", "choice_index": 2},
        ]
    )
    assert prefix_command(message) == "CHOOSE 1"


def test_prefix_uses_only_neow_event():
    message = neow([{"text": "Leave", "choice_index": 0}])
    message["game_state"]["screen_state"]["event_id"] = "Other Event"
    with pytest.raises(ProtocolError, match="Unsupported prefix event"):
        prefix_command(message)


def test_atomic_evidence_replacement(tmp_path):
    path = tmp_path / "result.json"
    write_json(path, {"status": "interrupted"})
    write_json(path, {"status": "won"})
    assert json.loads(path.read_text()) == {"status": "won"}
    assert not list(tmp_path.glob("*.tmp"))
