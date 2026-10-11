"""Frozen, narrowly scoped original-engine development suites."""

import hashlib
import json
import re
from pathlib import Path

from spire.evidence import summarize_run
from spire.rollout import rollout, write_json


def load_suite(path: Path) -> dict:
    suite = json.loads(path.read_text())
    if suite.get("schema_version") != 1 or suite.get("purpose") != "development":
        raise ValueError("Only declared schema-1 development suites are implemented")
    if not isinstance(suite.get("id"), str) or not suite["id"]:
        raise ValueError("Suite requires a stable identifier")
    if not re.fullmatch(r"[A-Z0-9]+", suite.get("game_seed", "")):
        raise ValueError("Suite seed must use uppercase ASCII letters and numbers")
    if not re.fullmatch(r"[a-f0-9]{64}", suite.get("expected_start_sha256", "")):
        raise ValueError("Suite must pin the normalized combat start")
    if type(suite.get("episodes")) is not int or suite["episodes"] <= 0:
        raise ValueError("Suite episodes must be positive")
    if type(suite.get("policy_seed")) is not int:
        raise ValueError("Suite must fix the first policy RNG seed")
    return suite


def evaluate(policy: str, suite_path: Path, output: Path) -> dict:
    suite = load_suite(suite_path)
    resolved = {
        "policy": policy,
        **{
            key: suite[key]
            for key in (
                "game_seed",
                "policy_seed",
                "episodes",
                "expected_start_sha256",
            )
        },
        "max_actions": 500,
        "episode_timeout": 180,
        "bridge_timeout": 45,
    }
    manifest = rollout(output, resolved)
    report = summarize_run(output)
    policy_path = Path(__file__).with_name("policies.py")
    result = {
        "schema_version": 1,
        "suite": suite,
        "suite_sha256": hashlib.sha256(suite_path.read_bytes()).hexdigest(),
        "policy_artifact": {
            "type": "builtin",
            "name": policy,
            "source_revision": manifest["source_revision"],
            "policy_source_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
            "weights": None,
        },
        "valid": report["valid"] and manifest["status"] == "completed",
        "audit": report,
    }
    write_json(output / "evaluation.json", result)
    return result
