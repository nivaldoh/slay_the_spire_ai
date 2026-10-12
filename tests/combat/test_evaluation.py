import json

import pytest

from spire.combat.evaluation import load_suite
from spire.provenance import REPO_ROOT

SUITE = REPO_ROOT / "configs/suites/louse_diagnostic_development_v1.json"


def test_development_suite_freezes_a_single_start_and_policy_seeds():
    suite = load_suite(SUITE)
    assert suite["purpose"] == "development"
    assert len(suite["expected_start_sha256"]) == 64
    assert suite["game_seed"] == "SPIREAI1"


@pytest.mark.parametrize(
    "changed",
    [
        {"purpose": "final"},
        {"expected_start_sha256": ""},
        {"game_seed": "SEED☃"},
        {"episodes": 0},
        {"episodes": True},
        {"policy_seed": "random"},
        {"character": "SILENT"},
        {"class": "DEFECT"},
        {"ascension": 20},
        {"ascension_level": True},
        {"observation_version": "privileged-v2"},
        {"observation_contract": "unrestricted"},
        {"starting_distribution": {"seeds": ["ABC", "XYZ"]}},
    ],
)
def test_suite_rejects_unfrozen_or_unsupported_contract(tmp_path, changed):
    suite = json.loads(SUITE.read_text())
    suite.update(changed)
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite))
    with pytest.raises(ValueError):
        load_suite(path)


def test_suite_accepts_explicit_supported_character_and_observation_contract(tmp_path):
    suite = json.loads(SUITE.read_text())
    suite.update(
        character="IRONCLAD", ascension=0, observation_contract="ironclad-starter-combat-v1"
    )
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite))
    assert load_suite(path) == suite
