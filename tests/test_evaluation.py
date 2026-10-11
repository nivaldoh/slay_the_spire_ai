import json
from pathlib import Path

import pytest

from spire.evaluation import load_suite

SUITE = Path(__file__).parents[1] / "configs/suites/louse_diagnostic_development_v1.json"


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
    ],
)
def test_suite_rejects_unfrozen_or_unsupported_contract(tmp_path, changed):
    suite = json.loads(SUITE.read_text())
    suite.update(changed)
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite))
    with pytest.raises(ValueError):
        load_suite(path)
