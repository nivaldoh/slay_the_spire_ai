"""Frozen language-artifact evaluation on the existing schema-one engine suite."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from spire.evaluation import load_suite
from spire.evidence import summarize_run
from spire.language_policy import (
    LanguagePolicy,
    decode_completion,
    dependency_versions,
    file_sha256,
)
from spire.protocol import Action, Decision
from spire.rollout import rollout, write_json


def evaluate_language(
    declaration_path: Path,
    suite_path: Path,
    output: Path,
    *,
    loader=None,
) -> dict:
    """Snapshot one declaration and adapter before the first owned game launch."""
    suite = load_suite(suite_path)
    suite_bytes = suite_path.read_bytes()
    if json.loads(suite_bytes) != suite:
        raise ValueError("Suite changed while preparing language evaluation")
    declaration_bytes = declaration_path.read_bytes()
    declaration = json.loads(declaration_bytes)
    artifact_hash = hashlib.sha256(declaration_bytes).hexdigest()
    snapshot = output / "frozen-language"
    with LanguagePolicy(declaration, loader=loader) as policy:
        adapter_bytes = {}
        if declaration["adapter"] is not None:
            directory = Path(declaration["adapter"]["directory"])
            adapter_bytes = {
                name: (directory / name).read_bytes() for name in declaration["adapter"]["files"]
            }
            if {name: hashlib.sha256(data).hexdigest() for name, data in adapter_bytes.items()} != (
                declaration["adapter"]["files"]
            ):
                raise ValueError("Language adapter changed while preparing snapshot")
        snapshot_files = {
            "declaration.json": artifact_hash,
            **{
                f"adapter/{name}": hashlib.sha256(data).hexdigest()
                for name, data in adapter_bytes.items()
            },
        }
        artifact = {
            "type": "language",
            "name": "language",
            "sha256": artifact_hash,
            "path": str(declaration_path.resolve()),
            "snapshot_path": "frozen-language/declaration.json",
            "adapter_snapshot_path": "frozen-language/adapter" if adapter_bytes else None,
            "model_sha256": policy.model_sha256,
            "declaration": declaration,
            "dependencies": dependency_versions(),
            "sampling": "greedy",
            "pretrained_base_only": declaration["adapter"] is None,
        }

        def check_inputs():
            if declaration_path.read_bytes() != declaration_bytes:
                raise ValueError("Language declaration changed during evaluation")
            if suite_path.read_bytes() != suite_bytes:
                raise ValueError("Language suite changed during evaluation")
            policy.verify_frozen()

        def check_snapshot():
            current = {
                str(path.relative_to(snapshot)): file_sha256(path)
                for path in snapshot.rglob("*")
                if path.is_file()
            }
            if current != snapshot_files:
                raise ValueError("Frozen language evidence snapshot changed")

        def check_recorded_tokens():
            for path in output.glob("episode-*/trace.jsonl"):
                for line in path.read_text().splitlines():
                    event = json.loads(line)
                    if event["kind"] not in {"policy_failure", "decision"}:
                        continue
                    item = event["decision"]
                    metadata = event["failure" if event["kind"] == "policy_failure" else "behavior"]
                    decision = Decision(
                        item["id"],
                        item["observation"],
                        tuple(Action(**a) for a in item["candidates"]),
                    )
                    _, prompt, encoded = policy.encode_decision(decision)
                    if encoded["input_ids"].shape[1] != metadata["prompt_tokens"]:
                        raise ValueError("Language prompt token count differs from tokenizer")
                    ids = metadata["completion_token_ids"]
                    if len(ids) != metadata["completion_tokens"]:
                        raise ValueError("Language completion token count mismatch")
                    if event["kind"] == "decision" and metadata["chat_prompt_sha256"] != (
                        hashlib.sha256(prompt.encode()).hexdigest()
                    ):
                        raise ValueError("Language chat template hash mismatch")
                    if metadata.get("kind") == "context_limit":
                        if ids or metadata["raw_completion"] is not None:
                            raise ValueError("Context failure must not generate completion tokens")
                    elif decode_completion(policy.tokenizer, ids) != (
                        metadata["completion"],
                        metadata["raw_completion"],
                    ):
                        raise ValueError("Language token IDs differ from recorded completion")

        def policy_factory(seed):
            # Greedy decoding does not sample. The scheduled seed is still preserved
            # by rollout, and no failed seed is retried.
            check_inputs()
            if not snapshot.exists():
                snapshot.mkdir()
                (snapshot / "declaration.json").write_bytes(declaration_bytes)
                if adapter_bytes:
                    (snapshot / "adapter").mkdir()
                    for name, data in adapter_bytes.items():
                        (snapshot / "adapter" / name).write_bytes(data)
                for path in snapshot.rglob("*"):
                    if path.is_file():
                        path.chmod(0o444)
            check_snapshot()
            return policy

        config = {
            "policy": "language",
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
            "policy_artifact": artifact,
        }
        manifest = rollout(output, config, policy_factory=policy_factory)
        audit = summarize_run(output)
        consistency_errors = []
        for check in (check_inputs, check_snapshot, check_recorded_tokens):
            try:
                check()
            except (OSError, ValueError, KeyError, TypeError) as error:
                consistency_errors.append(str(error))
        results = manifest["episodes"]
        won = sum(result["status"] == "won" for result in results)
        lost = sum(result["status"] == "lost" for result in results)
        failures = sum(result["status"] == "policy_failure" for result in results)
        gameplay = won + lost
        attempts = gameplay + failures
        # These counts are accepted only with an authoritative valid trace audit.
        metrics = {
            "attempted_episodes": len(results),
            "completed_gameplay": gameplay,
            "wins": won,
            "losses": lost,
            "policy_failures": failures,
            "invalid_completions": sum(
                result.get("policy_failure", {}).get("kind") == "invalid_completion"
                for result in results
            ),
            "context_failures": sum(
                result.get("policy_failure", {}).get("kind") == "context_limit"
                for result in results
            ),
            "infrastructure_failures": sum(
                result["status"] == "infrastructure_failure" for result in results
            ),
            "unattempted_episodes": suite["episodes"] - len(results),
            "win_rate": won / gameplay if gameplay else None,
            "policy_attempts": attempts,
            "policy_attempt_win_rate": won / attempts if attempts else None,
        }
        result = {
            "schema_version": 1,
            "suite": suite,
            "suite_sha256": hashlib.sha256(suite_bytes).hexdigest(),
            "policy_artifact": artifact,
            "evaluation_source_revision": manifest["source_revision"],
            "valid": audit["valid"]
            and manifest["status"] == "completed"
            and not consistency_errors,
            "consistency_errors": consistency_errors,
            "audit": audit,
            "metrics": metrics,
            "snapshot_files": {
                str(path.relative_to(output)): file_sha256(path)
                for path in snapshot.rglob("*")
                if path.is_file()
            },
        }
        write_json(output / "evaluation.json", result)
        return result
