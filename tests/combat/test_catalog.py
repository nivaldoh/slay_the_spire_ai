"""Catalog contracts through the real runner/auditor, with no game process."""

import copy
import hashlib
import json

import pytest
import test_evidence
import test_rollout_lifecycle

from spire import provenance
from spire.combat import catalog, evaluation, rollout
from spire.combat.evidence import audit_run, normalized_observation_fingerprint
from spire.engine import doctor
from spire.engine.bridge import BridgeDisconnected
from spire.protocol import decision_from_message

runtime_harness = test_rollout_lifecycle.harness


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def raw(monster_id):
    message = test_evidence.combat_message()
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


def test_resolved_schedule_preserves_schema1_and_excludes_environment_metadata(
    tmp_path, declaration,
):
    before = copy.deepcopy(declaration)
    for index, entry in enumerate(declaration["schedule"]):
        child = catalog.resolve_child_suite(declaration, index)
        path = tmp_path / "suite.json"
        write(path, child)
        assert evaluation.load_suite(path) == child
        assert child["policy_seed"] == entry["policy_seed"] and child["episodes"] == 1
        assert not set(child) & {"monster_ids", "encounter_family", "discovery_trace_sha256"}
    assert declaration == before
    result = catalog.validate_catalog(declaration)
    result["scenarios"][0]["monster_ids"].clear()
    assert declaration == before


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("schema_version", 1), ("purpose", "held-out-seed"),
    ("id", "../outside"), ("scenarios", []), ("schedule", []),
    ("character", "SILENT"), ("ascension", True), ("observation_contract", "privileged"),
    ("policy_features", ["seed"]), ("reset", "snapshot"), ("description", 3),
])
def test_catalog_rejects_unknown_or_unsupported_declarations(declaration, field, value):
    declaration[field] = value
    with pytest.raises(ValueError):
        catalog.validate_catalog(declaration)


@pytest.mark.parametrize("field,value", [
    ("id", "todo"), ("game_seed", "TODO"), ("game_seed", "SEED☃"),
    ("game_seed", 42), ("expected_start_sha256", "0" * 64),
    ("discovery_trace_sha256", "a" * 64), ("discovery_trace_sha256", "not-captured"),
    ("monster_ids", ["JawWorm"]), ("monster_ids", "Cultist"),
    ("encounter_family", "small_slimes"), ("private_move", 2),
])
def test_scenario_rejects_placeholders_and_unsupported_compositions(declaration, field, value):
    declaration["scenarios"][0][field] = value
    with pytest.raises(ValueError):
        catalog.validate_catalog(declaration)


@pytest.mark.parametrize("mutation", ["id", "seed", "reference", "unused", "duplicate_draw",
                                     "bool_seed", "negative_seed", "large_seed", "extra"])
def test_schedule_is_explicit_complete_and_unambiguous(declaration, mutation):
    if mutation == "id":
        declaration["scenarios"][1]["id"] = "cultist-a"
    elif mutation == "seed":
        declaration["scenarios"][1]["game_seed"] = "ABC"
    elif mutation == "reference":
        declaration["schedule"][0]["scenario_id"] = "absent"
    elif mutation == "unused":
        declaration["schedule"].pop()
    elif mutation == "duplicate_draw":
        declaration["schedule"].append(declaration["schedule"][0])
    elif mutation == "extra":
        declaration["schedule"][0]["rng_state"] = 123
    else:
        declaration["schedule"][0]["policy_seed"] = {
            "bool_seed": True, "negative_seed": -1, "large_seed": 2**63,
        }[mutation]
    with pytest.raises(ValueError):
        catalog.validate_catalog(declaration)


@pytest.mark.parametrize("monster_ids", [
    ["FuzzyLouseNormal", "FuzzyLouseNormal"],
    ["FuzzyLouseDefensive", "FuzzyLouseNormal"],
    ["FuzzyLouseDefensive", "FuzzyLouseDefensive"],
])
def test_louse_compositions_preserve_order(declaration, monster_ids):
    declaration["scenarios"][0].update(encounter_family="two_louses", monster_ids=monster_ids)
    assert catalog.validate_catalog(declaration)["scenarios"][0]["monster_ids"] == monster_ids


@pytest.mark.parametrize("contents", ['{"schema_version":2,"schema_version":2}',
                                     '{"bad":NaN}', '[]'])
def test_json_loader_rejects_ambiguous_or_nonfinite_input(tmp_path, contents):
    path = tmp_path / "catalog.json"
    path.write_text(contents)
    with pytest.raises(ValueError):
        catalog.load_catalog(path)


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


def test_catalog_executes_real_evaluation_and_audit_with_equal_scenario_macro(run_setup):
    path, output, runtime = run_setup
    report = catalog.evaluate_catalog("random", path, output)
    assert report["valid"], report["issues"]
    assert report["metrics"]["wins"] == 3 and report["metrics"]["losses"] == 1
    assert report["metrics"]["win_rate"] == 0.75
    assert report["macro"]["win_rate"] == 0.5
    assert report["macro"]["mean_ending_hp"] == 37.5
    assert report["scenarios"]["cultist-a"]["reset_comparison"]["all_initial_states_equal"]
    assert report["scenarios"]["jaw-a"]["reset_comparison"]["eligible_episodes"] == 1
    assert len(runtime.games) == 4
    for index in range(4):
        assert audit_run(output / "runs" / f"attempt-{index:04d}")["valid"]
    assert catalog.audit_catalog(output) == report
    with pytest.raises(FileExistsError):
        catalog.evaluate_catalog("random", path, output)


def test_bridge_failure_remains_infrastructure_and_stops_schedule(run_setup):
    path, output, runtime = run_setup
    runtime.sessions[1] = [BridgeDisconnected("synthetic disconnect")]
    report = catalog.evaluate_catalog("random", path, output)
    assert not report["valid"] and report["status"] == "stopped"
    assert report["metrics"]["infrastructure_failures"] == 1
    assert report["metrics"]["losses"] == 0
    assert report["unattempted"] == 2 and len(runtime.games) == 2
    assert report["macro"]["win_rate"] is None


def test_ordered_public_monsters_checked_beyond_fingerprint(run_setup):
    path, output, runtime = run_setup
    data = json.loads(path.read_text())
    data["scenarios"][0].update(encounter_family="jaw_worm", monster_ids=["JawWorm"])
    write(path, data)
    report = catalog.evaluate_catalog("random", path, output)
    assert not report["valid"]
    assert any("composition" in item for item in report["issues"])
    assert len(runtime.games) == 1


@pytest.mark.parametrize("target", ["trace", "source", "suite", "policy", "catalog"])
def test_saved_catalog_audit_rejects_changed_evidence(run_setup, target):
    path, output, _ = run_setup
    assert catalog.evaluate_catalog("random", path, output)["valid"]
    child = output / "runs/attempt-0000"
    if target == "trace":
        target_path = child / "episode-0000/trace.jsonl"
        target_path.write_text(target_path.read_text() + "{}\n")
    elif target == "source":
        target_path = child / "manifest.json"
        data = json.loads(target_path.read_text())
        data["source_revision"] = "b" * 40
        write(target_path, data)
    elif target == "suite":
        target_path = output / "suites/attempt-0000.json"
        data = json.loads(target_path.read_text())
        data["policy_seed"] += 1
        write(target_path, data)
    elif target == "policy":
        (output / "frozen-policy/policies.py").write_text("changed")
    else:
        data = json.loads((output / "catalog.json").read_text())
        data["description"] = "Changed declaration"
        write(output / "catalog.json", data)
    assert not catalog.audit_catalog(output)["valid"]


def test_catalog_mutation_during_child_stops_before_another_launch(run_setup):
    path, output, runtime = run_setup
    terminal = runtime.sessions[0][-1]

    def mutate():
        write(path, {})
        return terminal

    runtime.sessions[0][-1] = mutate
    report = catalog.evaluate_catalog("random", path, output)
    assert not report["valid"] and report["orchestration_failures"] == 1
    assert len(runtime.games) == 1
    assert json.loads((output / "catalog.json").read_text())["schema_version"] == 2


def test_neural_children_share_frozen_artifact_but_use_scheduled_rng(run_setup, tmp_path):
    torch = pytest.importorskip("torch")
    from spire.ppo.learning import LEARNER_VERSION, CandidateActorCritic, NeuralPolicy

    path, output, _ = run_setup
    policy = NeuralPolicy(CandidateActorCritic(3))
    checkpoint = tmp_path / "policy.pt"
    torch.save({"schema_version": 1, "learner_version": LEARNER_VERSION,
                "policy": policy.state_dict(), "model_sha256": policy.model_sha256,
                "training_checkpoint_sha256": digest("synthetic-ancestor")}, checkpoint)
    report = catalog.evaluate_catalog("neural", path, output, checkpoint=checkpoint)
    assert report["valid"], report["issues"]
    assert report["policy_artifact"]["sha256"] == digest_bytes(checkpoint.read_bytes())
    for index, entry in enumerate(json.loads(path.read_text())["schedule"]):
        result_path = output / f"runs/attempt-{index:04d}/episode-0000/result.json"
        result = json.loads(result_path.read_text())
        assert result["policy_seed"] == entry["policy_seed"]
        assert result["policy_rng"] == "per_episode_seed"


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def test_engine_change_between_children_stops_and_invalidates_changed_child(run_setup, monkeypatch):
    path, output, runtime = run_setup
    calls = 0

    def environment():
        nonlocal calls
        calls += 1
        return {"game": {"sha256": digest("game" if calls == 1 else "changed-game")},
                "mods": {"mod": {"sha256": digest("mod")}}}

    monkeypatch.setattr(doctor, "collect_diagnostics", environment)
    report = catalog.evaluate_catalog("random", path, output)
    assert not report["valid"] and report["status"] == "stopped"
    assert report["metrics"]["valid_gameplay_episodes"] == 1
    assert report["metrics"]["invalid_evidence"] == 1
    assert any("Engine/mod pins changed" in issue for issue in report["issues"])
    assert len(runtime.games) == 2


def test_failure_before_child_files_keeps_reservation_and_empty_metrics(run_setup, monkeypatch):
    path, output, runtime = run_setup

    def fail(*args, **kwargs):
        raise OSError("synthetic preparation failure")

    monkeypatch.setattr(evaluation, "evaluate", fail)
    report = catalog.evaluate_catalog("random", path, output)
    assert not report["valid"] and report["status"] == "stopped"
    assert report["attempts_started"] == report["orchestration_failures"] == 1
    assert report["metrics"]["attempts"] == report["children"][0]["metrics"]["attempts"] == 0
    assert report["unattempted"] == 3 and not runtime.games


def test_interrupted_child_keeps_readable_parent_and_excludes_macro(run_setup):
    path, output, runtime = run_setup
    runtime.sessions[0][-1] = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        catalog.evaluate_catalog("random", path, output)
    report = catalog.audit_catalog(output)
    assert not report["valid"] and report["status"] == "interrupted"
    assert report["attempts_started"] == 1 and report["unattempted"] == 3
    assert report["metrics"]["interrupted"] == 1
    assert report["macro"]["mean_ending_hp"] is None


def test_coherent_expected_metadata_cannot_replace_actual_start_fingerprint(run_setup):
    path, output, _ = run_setup
    assert catalog.evaluate_catalog("random", path, output)["valid"]
    catalog_path = output / "catalog.json"
    declaration = json.loads(catalog_path.read_text())
    declaration["scenarios"][0]["expected_start_sha256"] = digest("wrong-public-start")
    write(catalog_path, declaration)
    manifest_path = output / "catalog-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["catalog_sha256"] = digest_bytes(catalog_path.read_bytes())
    for index in range(3):
        child = output / f"runs/attempt-{index:04d}"
        suite_path = output / f"suites/attempt-{index:04d}.json"
        suite = catalog.resolve_child_suite(declaration, index)
        write(suite_path, suite)
        child_manifest = json.loads((child / "manifest.json").read_text())
        child_manifest["config"]["expected_start_sha256"] = suite["expected_start_sha256"]
        write(child / "manifest.json", child_manifest)
        result = json.loads((child / "evaluation.json").read_text())
        result.update(suite=suite, suite_sha256=digest_bytes(suite_path.read_bytes()))
        write(child / "evaluation.json", result)
        manifest["children"][index]["files"] = catalog._files(child)
        assert audit_run(child)["valid"]  # Trace coherence alone cannot establish assignment.
    write(manifest_path, manifest)
    report = catalog.audit_catalog(output)
    assert not report["valid"]
    assert any("scenario fingerprint" in issue for issue in report["issues"])


def test_refreshed_snapshot_inventory_cannot_replace_policy_identity(run_setup):
    path, output, _ = run_setup
    assert catalog.evaluate_catalog("random", path, output)["valid"]
    (output / "frozen-policy/policies.py").write_text("changed policy source")
    manifest_path = output / "catalog-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["policy_files"] = catalog._files(output / "frozen-policy")
    write(manifest_path, manifest)
    report = catalog.audit_catalog(output)
    assert not report["valid"]
    assert any("Frozen policy identity" in issue for issue in report["issues"])
