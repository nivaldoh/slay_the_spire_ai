"""Shared synthetic fixtures; pattern: huggingface/datasets tests/utils.py."""

import hashlib
import json
import shutil
import subprocess

import combat_evidence as evidence_fixtures
import pytest

from gameai.provenance import REPO_ROOT
from spire.combat.evidence import audit_run, normalized_observation_fingerprint
from spire.language import demonstrations as demos
from spire.protocol import decision_from_message

evidence_run = evidence_fixtures.run


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value) + "\n")


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture
def run(evidence_run):
    root = REPO_ROOT
    manifest = read(evidence_run / "manifest.json")
    manifest.update(
        source_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        source_status="",
        source_files={
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("src/spire/policies.py", "src/spire/protocol.py")
        },
    )
    manifest["config"]["policy"] = "heuristic"
    write(evidence_run / "manifest.json", manifest)
    evidence_fixtures.set_result(evidence_run, policy="heuristic")
    assert audit_run(evidence_run)["valid"]
    return evidence_run


def source(run, split="train", role="heuristic", information="public"):
    return demos.DemonstrationSource(run, split, role, information)


def renamed_copy(run, destination, *, seed="ABC", hp=80):
    shutil.copytree(run, destination)
    for path in destination.rglob("*.json*"):
        path.write_text(path.read_text().replace("session-0", f"session-{destination.name}"))
    manifest = read(destination / "manifest.json")
    manifest["config"]["game_seed"] = seed
    write(destination / "manifest.json", manifest)
    evidence_fixtures.set_result(destination, seed=seed, starting_hp=hp)
    episode = destination / "episode-0000"
    events = evidence_fixtures.events(episode)
    events[2]["command"] = f"START IRONCLAD 0 {seed}"
    raw = events[3]["raw"]
    raw["game_state"]["current_hp"] = hp
    raw["game_state"]["combat_state"]["player"]["current_hp"] = hp
    result = read(episode / "result.json")
    decision = decision_from_message(raw, session_id=result["session_id"], sequence=2).to_dict()
    events[5]["decision"] = decision
    result["combat_start_sha256"] = normalized_observation_fingerprint(decision["observation"])
    events[-1]["result"] = result
    evidence_fixtures.write_events(episode, events)
    write(episode / "result.json", result)
    write(episode / "combat_start.json", decision["observation"])
    manifest = read(destination / "manifest.json")
    manifest["episodes"] = [result]
    write(destination / "manifest.json", manifest)
    assert audit_run(destination)["valid"]
    return destination


def evaluation_source(run, purpose="development"):
    manifest = read(run / "manifest.json")
    manifest["config"]["expected_start_sha256"] = manifest["episodes"][0]["combat_start_sha256"]
    write(run / "manifest.json", manifest)
    suite = {
        "schema_version": 1,
        "id": "fixture",
        "purpose": purpose,
        **{
            key: manifest["config"][key]
            for key in ("game_seed", "policy_seed", "episodes", "expected_start_sha256")
        },
    }
    write(run / "suite.json", suite)
    record = {
        "schema_version": 1,
        "valid": True,
        "suite": suite,
        "suite_sha256": hashlib.sha256((run / "suite.json").read_bytes()).hexdigest(),
        "policy_artifact": {
            "type": "builtin",
            "name": "heuristic",
            "source_revision": manifest["source_revision"],
            "policy_source_sha256": manifest["source_files"]["src/spire/policies.py"],
        },
    }
    write(run / "evaluation.json", record)
    return record


def policy_failure_after_action(run):
    """Keep one acknowledged public action before an invalid model completion."""
    evidence_fixtures.make_policy_failure(run, after_action=True)


def non_heuristic_behavior(run):
    """Record a legal random-policy choice that differs from the heuristic's choice."""
    manifest = read(run / "manifest.json")
    manifest["config"].update(policy="random", policy_seed=7)
    write(run / "manifest.json", manifest)
    evidence_fixtures.set_result(run, policy="random", policy_seed=7)
    events = evidence_fixtures.events(run / "episode-0000")
    selected = events[5]["decision"]["candidates"][-1]
    events[5]["selected_action_id"] = selected["id"]
    events[6].update(action_id=selected["id"], command=selected["command"])
    events[7]["previous_action_id"] = selected["id"]
    events[8]["action_id"] = selected["id"]
    evidence_fixtures.write_events(run / "episode-0000", events)
    assert audit_run(run)["valid"]
    return selected
