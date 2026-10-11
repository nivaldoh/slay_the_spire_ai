"""Comparability needs the declared distribution as well as the observation version."""

import copy
import json

import pytest

from spire import report


def write(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def runs(tmp_path, monkeypatch):
    summaries = {}
    paths = []
    for index in range(2):
        directory = tmp_path / f"run-{index}"
        directory.mkdir()
        episode = directory / "episode-0000"
        episode.mkdir()
        write(episode / "combat_start.json", {
            "class": "IRONCLAD", "ascension_level": 0, "contract": "starter-v1",
        })
        write(directory / "environment.json", {
            "game": {"sha256": "a" * 64},
            "mods": {"mod.jar": {"sha256": "b" * 64}},
        })
        suite = {
            "schema_version": 1, "purpose": "development", "id": "same-scenario",
            "game_seed": "ABC", "policy_seed": 1000, "episodes": 1,
            "expected_start_sha256": "c" * 64,
        }
        write(directory / "evaluation.json", {
            "schema_version": 1, "valid": True, "suite": suite, "suite_sha256": "d" * 64,
        })
        summaries[directory] = {
            "directory": str(directory), "valid": True, "issues": [],
            "evidence": {"manifest.json": str(directory / "manifest.json")},
            "metrics": {
                "mean_ending_hp": 75, "wins": 1, "valid_gameplay_episodes": 1, "attempts": 1,
            },
            "provenance": {
                "source_revision": str(index) * 40,
                "engine": "original", "scope": "first_combat",
                "observation_version": "starter-v1", "prefix_version": "prefix-v1",
                "reset": "restart",
                "config": {
                    **{key: suite[key] for key in (
                        "game_seed", "policy_seed", "episodes", "expected_start_sha256",
                    )},
                    "policy": ("random", "neural")[index],
                    "policy_artifact": {"model_sha256": str(index) * 64},
                    "max_actions": 500, "episode_timeout": 180, "bridge_timeout": 45,
                },
            },
            "reset_comparison": {"initial_state_hashes": ["c" * 64]},
            "episodes": [{"episode": 0, "valid": True, "combat_start_sha256": "c" * 64}],
        }
        paths.append(directory)
    monkeypatch.setattr(report, "summarize_run", lambda path: copy.deepcopy(summaries[path]))
    return paths, summaries


def change_json(path, **changes):
    data = json.loads(path.read_text())
    data.update(changes)
    write(path, data)


def test_identical_suite_allows_different_policies_weights_and_source_revisions(runs):
    paths, _ = runs
    result = report.compare_runs(paths)
    assert result["valid"] and result["same_protocol"]
    assert result["comparison_issues"] == result["protocol_differences"] == []
    assert "not a controlled comparison" not in report.render_report(result)


@pytest.mark.parametrize("field,value", [
    ("game_seed", "XYZ"), ("expected_start_sha256", "e" * 64), ("policy_seed", 2000),
    ("episodes", 2), ("max_actions", 10), ("episode_timeout", 30), ("bridge_timeout", 5),
    ("character", "SILENT"), ("ascension_level", 20),
    ("observation_contract", "privileged-v2"),
    ("starting_distribution", {"encounters": ["jaw-worm"]}),
])
def test_resolved_contract_changes_are_not_comparable(runs, field, value):
    paths, summaries = runs
    summaries[paths[1]]["provenance"]["config"][field] = value
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert "config" in result["protocol_differences"]


@pytest.mark.parametrize("field,value", [
    ("observation_version", "privileged-v2"), ("prefix_version", "unsettled-v1"),
    ("scope", "full-run"), ("engine", "simulator"), ("reset", "snapshot"),
])
def test_environment_and_observation_contracts_are_compared(runs, field, value):
    paths, summaries = runs
    summaries[paths[1]]["provenance"][field] = value
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert field in result["protocol_differences"]


@pytest.mark.parametrize("field,value", [
    ("expected_start_sha256", "e" * 64), ("game_seed", "XYZ"),
    ("starting_distribution", {"seeds": ["ABC", "XYZ"]}),
    ("character", "SILENT"), ("ascension", 20),
    ("observation_contract", "privileged-v2"),
])
def test_suite_content_is_compared_even_if_record_reuses_suite_id_and_hash(runs, field, value):
    paths, _ = runs
    path = paths[1] / "evaluation.json"
    data = json.loads(path.read_text())
    data["suite"][field] = value
    write(path, data)
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert "evaluation_suite" in result["protocol_differences"]


def test_suite_and_manifest_must_agree_even_if_both_runs_repeat_the_same_error(runs):
    paths, summaries = runs
    for path in paths:
        summaries[path]["provenance"]["config"]["game_seed"] = "OTHER"
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert result["protocol_differences"] == []
    assert all("suite game_seed differs" in issue for issue in result["comparison_issues"])


@pytest.mark.parametrize("field,value", [("class", "SILENT"), ("ascension_level", 20)])
def test_observed_start_character_and_ascension_are_compared(runs, field, value):
    paths, _ = runs
    change_json(paths[1] / "episode-0000/combat_start.json", **{field: value})
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert "observed_start_contracts" in result["protocol_differences"]


def test_shared_false_character_declaration_does_not_override_audited_public_state(runs):
    paths, _ = runs
    for path in paths:
        record = json.loads((path / "evaluation.json").read_text())
        record["suite"]["character"] = "SILENT"
        write(path / "evaluation.json", record)
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert "declared character differs" in result["comparison_issues"][0]


def test_policy_artifact_cannot_claim_another_observation_contract(runs):
    paths, summaries = runs
    summaries[paths[1]]["provenance"]["config"]["policy_artifact"]["observation_contract"] = (
        "privileged-v2"
    )
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert "policy_observation_contract" in result["protocol_differences"]


def test_equal_observed_starts_do_not_establish_an_undeclared_distribution(runs):
    paths, summaries = runs
    for path in paths:
        (path / "evaluation.json").unlink()
        del summaries[path]["provenance"]["config"]["expected_start_sha256"]
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert result["protocol_differences"] == []
    assert "starting distribution is not pinned" in report.render_report(result)


def test_observed_start_must_match_declared_start(runs):
    paths, summaries = runs
    summaries[paths[1]]["reset_comparison"]["initial_state_hashes"] = ["e" * 64]
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert "observed combat starts" in result["comparison_issues"][0]


def test_recorded_game_or_mod_hash_change_breaks_comparability(runs):
    paths, _ = runs
    change_json(paths[1] / "environment.json", game={"sha256": "e" * 64})
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert "engine_sha256" in result["protocol_differences"]


@pytest.mark.parametrize("missing", ["observation_version", "prefix_version", "reset"])
def test_missing_contract_metadata_fails_closed(runs, missing):
    paths, summaries = runs
    for path in paths:
        del summaries[path]["provenance"][missing]
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert f"missing {missing}" in result["comparison_issues"][0]


def test_invalid_evaluation_record_cannot_claim_a_controlled_comparison(runs):
    paths, _ = runs
    change_json(paths[1] / "evaluation.json", valid=False)
    result = report.compare_runs(paths)
    assert not result["same_protocol"]
    assert "evaluation record is not valid" in report.render_report(result)


def test_no_runs_do_not_establish_a_protocol():
    assert not report.compare_runs([])["same_protocol"]
