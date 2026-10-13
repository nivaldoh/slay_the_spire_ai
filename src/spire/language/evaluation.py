"""Frozen language-artifact evaluation on the existing schema-one engine suite."""

from __future__ import annotations

import copy
import hashlib
import json
from contextlib import nullcontext
from pathlib import Path

from gameai.provenance import write_json
from spire.combat.evaluation import load_suite
from spire.combat.evidence import summarize_run
from spire.combat.rollout import rollout
from spire.language.demonstrations import render_prompt
from spire.language.policy import (
    LanguagePolicy,
    decode_completion,
    dependency_versions,
    file_sha256,
    validate_declaration,
)
from spire.protocol import Action, Decision


def language_snapshot(
    declaration_path: Path, model_sha256: str | None, *, source_declaration: bytes | None = None,
) -> tuple[dict, dict]:
    """Capture exact declaration/adapter bytes and the loaded model identity."""
    data = declaration_path.read_bytes()
    declaration = json.loads(data)
    validate_declaration(declaration)
    files = {"declaration.json": data}
    if declaration["adapter"] is not None:
        directory = Path(declaration["adapter"]["directory"])
        for name, expected in declaration["adapter"]["files"].items():
            content = (directory / name).read_bytes()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError("Language adapter changed while preparing snapshot")
            files[f"adapter/{name}"] = content
    artifact = {
        "type": "language", "name": "language",
        "sha256": hashlib.sha256(data).hexdigest(),
        "path": str(declaration_path.resolve()),
        "snapshot_path": "frozen-language/declaration.json",
        "adapter_snapshot_path": "frozen-language/adapter" if declaration["adapter"] else None,
        "model_sha256": model_sha256, "declaration": declaration,
        "dependencies": dependency_versions(), "sampling": "greedy",
        "pretrained_base_only": declaration["adapter"] is None,
    }
    if source_declaration is not None:
        files["source-declaration.json"] = source_declaration
        artifact["source_declaration"] = {
            "sha256": hashlib.sha256(source_declaration).hexdigest(),
            "declaration": json.loads(source_declaration),
        }
    return artifact, files


def verify_language_snapshot(
    snapshot: Path, artifact: dict, *, verify_external_base: bool = True,
) -> None:
    """Check saved identity and byte inventories without constructing model weights."""
    data = (snapshot / "declaration.json").read_bytes()
    declaration = json.loads(data)
    if (hashlib.sha256(data).hexdigest() != artifact["sha256"]
            or declaration != artifact["declaration"]):
        raise ValueError("Frozen language declaration identity changed")
    if (artifact["type"] != "language" or artifact["name"] != "language"
            or artifact["sampling"] != "greedy"
            or artifact["pretrained_base_only"] is not (declaration["adapter"] is None)):
        raise ValueError("Frozen language artifact contract differs")
    identity = artifact["model_sha256"]
    if not isinstance(identity, str) or len(identity) != 64 or any(
        character not in "0123456789abcdef" for character in identity
    ):
        raise ValueError("Missing language model tensor identity")
    expected = {"declaration.json": artifact["sha256"]}
    if "source_declaration" in artifact:
        origin = artifact["source_declaration"]
        original = (snapshot / "source-declaration.json").read_bytes()
        if (hashlib.sha256(original).hexdigest() != origin["sha256"]
                or json.loads(original) != origin["declaration"]):
            raise ValueError("Original language declaration identity changed")
        rebased = copy.deepcopy(origin["declaration"])
        if rebased["adapter"] is not None:
            rebased["adapter"]["directory"] = declaration["adapter"]["directory"]
        if rebased != declaration:
            raise ValueError("Language execution declaration differs from original contract")
        expected["source-declaration.json"] = origin["sha256"]
    local = copy.deepcopy(declaration)
    if local["adapter"] is not None:
        expected.update({f"adapter/{name}": value
                         for name, value in local["adapter"]["files"].items()})
        local["adapter"]["directory"] = str((snapshot / "adapter").resolve())
    actual = {str(path.relative_to(snapshot)): file_sha256(path)
              for path in snapshot.rglob("*") if path.is_file()}
    if actual != expected:
        raise ValueError("Frozen language snapshot files changed")
    # Catalog children already match the fully validated parent artifact. Their
    # local copies still need exact hashes, without rereading the large base.
    if verify_external_base:
        validate_declaration(local)


def load_tokenizer(declaration: dict):
    """Load only the pinned local tokenizer for saved-evidence verification."""
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(
        declaration["base"]["directory"], local_files_only=True, trust_remote_code=False
    )


def check_recorded_tokens(output: Path, tokenizer) -> None:
    """Recompute token evidence using the frozen tokenizer, with no generation."""
    for path in output.glob("episode-*/trace.jsonl"):
        for line in path.read_text().splitlines():
            event = json.loads(line)
            if event["kind"] not in {"policy_failure", "decision"}:
                continue
            item = event["decision"]
            metadata = event["failure" if event["kind"] == "policy_failure" else "behavior"]
            decision = Decision(item["id"], item["observation"],
                                tuple(Action(**a) for a in item["candidates"]))
            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": render_prompt(decision)}],
                tokenize=False, add_generation_prompt=True, enable_thinking=False,
            )
            encoded = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
            if encoded["input_ids"].shape[1] != metadata["prompt_tokens"]:
                raise ValueError("Language prompt token count differs from tokenizer")
            ids = metadata["completion_token_ids"]
            if len(ids) != metadata["completion_tokens"]:
                raise ValueError("Language completion token count mismatch")
            if event["kind"] == "decision" and metadata["chat_prompt_sha256"] != (
                hashlib.sha256(prompt.encode()).hexdigest()):
                raise ValueError("Language chat template hash mismatch")
            if metadata.get("kind") == "context_limit":
                if ids or metadata["raw_completion"] is not None:
                    raise ValueError("Context failure must not generate completion tokens")
            else:
                try:
                    decoded = decode_completion(tokenizer, ids)
                except (OverflowError, IndexError) as error:
                    raise ValueError("Language completion token ID is out of range") from error
                if decoded != (metadata["completion"], metadata["raw_completion"]):
                    raise ValueError("Language token IDs differ from recorded completion")


def evaluate_language(
    declaration_path: Path,
    suite_path: Path,
    output: Path,
    *,
    loader=None,
    _policy=None,
    _source_declaration: bytes | None = None,
) -> dict:
    """Snapshot one declaration and adapter before the first owned game launch."""
    suite = load_suite(suite_path)
    suite_bytes = suite_path.read_bytes()
    if json.loads(suite_bytes) != suite:
        raise ValueError("Suite changed while preparing language evaluation")
    declaration_bytes = declaration_path.read_bytes()
    declaration = json.loads(declaration_bytes)
    snapshot = output / "frozen-language"
    if _policy is not None and loader is not None:
        raise ValueError("Supply a shared policy or a loader, not both")
    context = (nullcontext(_policy) if _policy is not None
               else LanguagePolicy(declaration, loader=loader))
    with context as policy:
        if policy.declaration != declaration:
            raise ValueError("Shared language policy differs from declaration")
        artifact, snapshot_bytes = language_snapshot(
            declaration_path, policy.model_sha256, source_declaration=_source_declaration
        )
        snapshot_files = {
            name: hashlib.sha256(data).hexdigest() for name, data in snapshot_bytes.items()
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

        def policy_factory(seed):
            # Greedy decoding does not sample. The scheduled seed is still preserved
            # by rollout, and no failed seed is retried.
            check_inputs()
            if not snapshot.exists():
                snapshot.mkdir()
                for name, data in snapshot_bytes.items():
                    path = snapshot / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
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
        for check in (check_inputs, check_snapshot,
                      lambda: check_recorded_tokens(output, policy.tokenizer)):
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
