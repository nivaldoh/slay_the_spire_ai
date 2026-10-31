"""Synthetic catalog inputs and the opt-in fake rollout boundary.

Shared-setup pattern: Hugging Face datasets tests/utils.py; tests/combat/combat_support.py.
Expected assertions stay in the tests; no original-engine evidence is created here.
"""

import copy
import hashlib
import json

import combat_evidence as evidence_fixtures
import pytest
from combat_support import harness

from gameai import provenance
from spire.combat import catalog, rollout
from spire.combat.evidence import normalized_observation_fingerprint
from spire.engine import doctor
from spire.protocol import decision_from_message

runtime_harness = harness


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()



def raw(monster_id):
    message = evidence_fixtures.combat_message()
    message["game_state"]["combat_state"]["monsters"][0]["id"] = monster_id
    return message



def public(monster_id):
    return decision_from_message(raw(monster_id), session_id="fixture", sequence=1).to_dict()[
        "observation"
    ]



@pytest.fixture
def declaration():
    return {
        "schema_version": 2, "purpose": "development", "id": "synthetic-catalog",
        "scenarios": [
            {"id": "cultist-a", "game_seed": "ABC", "encounter_family": "cultist",
             "monster_ids": ["Cultist"], "discovery_trace_sha256": digest("synthetic-a"),
             "expected_start_sha256": normalized_observation_fingerprint(public("Cultist"))},
            {"id": "jaw-a", "game_seed": "DEF", "encounter_family": "jaw_worm",
             "monster_ids": ["JawWorm"], "discovery_trace_sha256": digest("synthetic-b"),
             "expected_start_sha256": normalized_observation_fingerprint(public("JawWorm"))},
        ],
        "schedule": [
            {"scenario_id": "cultist-a", "policy_seed": 10},
            {"scenario_id": "cultist-a", "policy_seed": 11},
            {"scenario_id": "cultist-a", "policy_seed": 12},
            {"scenario_id": "jaw-a", "policy_seed": 10},
        ],
    }



def write(path, data):
    path.write_text(json.dumps(data))



@pytest.fixture
def run_setup(tmp_path, declaration, runtime_harness, monkeypatch):
    revision = "a" * 40
    fingerprints = {"src/example.py": digest("source")}
    monkeypatch.setattr(catalog, "source_fingerprints", lambda: fingerprints)
    monkeypatch.setattr(rollout, "source_fingerprints", lambda: fingerprints)
    monkeypatch.setattr(provenance.subprocess, "check_output", lambda command, **kwargs:
                        revision if command[:3] == ["git", "rev-parse", "HEAD"] else "")
    monkeypatch.setattr(doctor, "collect_diagnostics", lambda: {
        "game": {"sha256": digest("game")}, "mods": {"mod": {"sha256": digest("mod")}},
    })
    menu = {"in_game": False, "ready_for_command": True, "available_commands": ["start"]}
    for entry in declaration["schedule"]:
        monster_id = "Cultist" if entry["scenario_id"] == "cultist-a" else "JawWorm"
        initial = raw(monster_id)
        terminal = copy.deepcopy(initial)
        game = terminal["game_state"]
        game.pop("combat_state")
        game.update(room_phase="COMPLETE", screen_type="COMBAT_REWARD", current_hp=75)
        if monster_id == "JawWorm":
            game.update(current_hp=0, screen_type="GAME_OVER", screen_name="DEATH",
                        screen_state={"victory": False})
        runtime_harness.sessions.append([menu, initial, terminal])
    path = tmp_path / "input.json"
    write(path, declaration)
    return path, tmp_path / "evaluation", runtime_harness

