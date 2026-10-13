"""Strict development catalogs layered over unchanged single-scenario evaluation.

Catalogs and seeds belong to the environment, never to policy observations.
Validation establishes declarations; original-engine discovery is still required.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from contextlib import ExitStack
from pathlib import Path
from statistics import mean

from gameai.provenance import committed_revision, source_fingerprints, write_json
from spire import policies
from spire.combat import evaluation
from spire.combat.evidence import _metrics, audit_run, compare_resets
from spire.protocol import OBSERVATION_CONTRACT

DECLARATIONS = {
    "character": "IRONCLAD",
    "ascension": 0,
    "observation_contract": OBSERVATION_CONTRACT,
    "reset": "owned_jvm_restart_then_seeded_start",
    "prefix_version": "neow-maxhp-or-gold-leftmost-settled-v2",
}
SCENARIO_FIELDS = {
    "id", "game_seed", "expected_start_sha256", "encounter_family", "monster_ids",
    "discovery_trace_sha256",
}
PLACEHOLDERS = {"todo", "tbd", "placeholder", "changeme", "unknown", "seed", "yourseed"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _fields(value, required: set, optional: set, name: str) -> None:
    _require(type(value) is dict, f"{name} must be an object")
    _require(required <= value.keys(), f"Missing {name} fields: {sorted(required - value.keys())}")
    _require(not value.keys() - required - optional, f"Unknown {name} fields")


def _identifier(value, name: str) -> None:
    _require(
        type(value) is str and re.fullmatch(r"[a-z][a-z0-9_-]{0,79}", value) is not None
        and value not in PLACEHOLDERS,
        f"Invalid or placeholder {name}",
    )


def _hash(value, name: str) -> None:
    _require(
        type(value) is str and re.fullmatch(r"[a-f0-9]{64}", value) is not None
        and len(set(value)) > 1,
        f"{name} requires a non-placeholder SHA-256",
    )


def validate_catalog(value: dict) -> dict:
    """Return a detached, validated schema-2 catalog; reject unknown semantics."""
    _fields(value, {"schema_version", "purpose", "id", "scenarios", "schedule"},
            {"description", *DECLARATIONS}, "catalog")
    _require(type(value["schema_version"]) is int and value["schema_version"] == 2,
             "Only schema-2 catalogs are supported")
    _require(value["purpose"] == "development", "Only development catalogs are supported")
    _identifier(value["id"], "catalog id")
    if "description" in value:
        _require(type(value["description"]) is str and bool(value["description"].strip()),
                 "description must be nonempty text")
    for name, expected in DECLARATIONS.items():
        if name in value:
            _require(type(value[name]) is type(expected) and value[name] == expected,
                     f"Unsupported {name}")
    scenarios, schedule = value["scenarios"], value["schedule"]
    _require(type(scenarios) is list and bool(scenarios), "scenarios must be a nonempty list")
    _require(type(schedule) is list and bool(schedule), "schedule must be a nonempty list")
    identities, seeds = set(), set()
    for scenario in scenarios:
        _fields(scenario, SCENARIO_FIELDS, set(), "scenario")
        _identifier(scenario["id"], "scenario id")
        _require(scenario["id"] not in identities, "Duplicate scenario id")
        identities.add(scenario["id"])
        seed = scenario["game_seed"]
        _require(type(seed) is str and re.fullmatch(r"[A-Z0-9]+", seed) is not None
                 and seed.lower() not in PLACEHOLDERS, "Invalid or placeholder game_seed")
        _require(seed not in seeds, "Duplicate game seed aliases a scenario")
        seeds.add(seed)
        for field in ("expected_start_sha256", "discovery_trace_sha256"):
            _hash(scenario[field], field)
        family, monsters = scenario["encounter_family"], scenario["monster_ids"]
        _require(type(monsters) is list and all(type(item) is str for item in monsters),
                 "monster_ids must be an ordered list of public IDs")
        _require(
            (family == "cultist" and monsters == ["Cultist"])
            or (family == "jaw_worm" and monsters == ["JawWorm"])
            or (family == "two_louses" and len(monsters) == 2
                and all(item in {"FuzzyLouseNormal", "FuzzyLouseDefensive"} for item in monsters)),
            "Unsupported encounter family or monster composition",
        )
    scheduled, draws = set(), set()
    for entry in schedule:
        _fields(entry, {"scenario_id", "policy_seed"}, set(), "schedule entry")
        _require(type(entry["scenario_id"]) is str and entry["scenario_id"] in identities,
                 "Schedule references an absent scenario")
        seed = entry["policy_seed"]
        _require(type(seed) is int and 0 <= seed < 2**63,
                 "policy_seed must be an integer in [0, 2**63)")
        pair = (entry["scenario_id"], seed)
        _require(pair not in draws, "Duplicate scenario/policy-seed schedule entry")
        draws.add(pair)
        scheduled.add(entry["scenario_id"])
    _require(scheduled == identities, "Every declared scenario must be scheduled")
    return copy.deepcopy(value)


def _json(data: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"Nonfinite JSON value: {value}")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def load_catalog(path: Path) -> dict:
    return validate_catalog(_json(Path(path).read_bytes()))


def resolve_child_suite(catalog: dict, schedule_index: int) -> dict:
    """Resolve one frozen assignment into an ordinary schema-1, one-episode suite."""
    catalog = validate_catalog(catalog)
    _require(type(schedule_index) is int and 0 <= schedule_index < len(catalog["schedule"]),
             "Invalid schedule index")
    entry = catalog["schedule"][schedule_index]
    scenario = next(s for s in catalog["scenarios"] if s["id"] == entry["scenario_id"])
    return {
        "schema_version": 1, "purpose": "development",
        "id": f"{catalog['id']}-{scenario['id']}-{schedule_index:04d}",
        "game_seed": scenario["game_seed"],
        "expected_start_sha256": scenario["expected_start_sha256"],
        "policy_seed": entry["policy_seed"], "episodes": 1,
        "character": "IRONCLAD", "ascension": 0,
        "observation_contract": OBSERVATION_CONTRACT,
    }


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _files(directory: Path) -> dict:
    return {str(p.relative_to(directory)): _digest(p.read_bytes())
            for p in sorted(directory.rglob("*")) if p.is_file()}


def _source() -> dict:
    return {
        "source_revision": committed_revision("catalog evaluation"),
        "source_files": source_fingerprints(),
    }


def _path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    _require(path.is_relative_to(root.resolve()), "Evidence path leaves catalog run")
    return path


def _engine(directory: Path) -> dict:
    environment = _json((directory / "environment.json").read_bytes())
    result = {"game": environment["game"]["sha256"],
              "mods": {name: item["sha256"] for name, item in environment["mods"].items()}}
    _require(bool(result["mods"]), "Missing engine/mod pins")
    for value in [result["game"], *result["mods"].values()]:
        _hash(value, "engine/mod hash")
    return result


def _artifact_identity(artifact: dict) -> dict:
    return {key: value for key, value in artifact.items()
            if key not in {"path", "record_path", "snapshot_path", "adapter_snapshot_path"}}


def _verify_policy(output: Path, manifest: dict) -> None:
    directory = output / "frozen-policy"
    policy = manifest["policy"]
    _require(policy in {"random", "heuristic", "end_turn", "neural", "language"}, "Unknown policy")
    if policy == "language":
        from spire.language.evaluation import verify_language_snapshot

        artifact = manifest["policy_artifact"]
        _require("source_declaration" in artifact, "Missing original language declaration")
        adapter = artifact["declaration"]["adapter"]
        _require(adapter is None or Path(adapter["directory"]) == (directory / "adapter").resolve(),
                 "Language execution adapter is not the frozen parent snapshot")
        verify_language_snapshot(directory, artifact)
        return
    if policy == "neural":
        paths = list(directory.glob("*.pt"))
        _require(len(paths) == 1, "Expected one frozen neural artifact")
        _, artifact, *_ = evaluation._neural_artifact(paths[0])
    else:
        artifact = {"type": "builtin", "name": policy, "weights": None,
                    "policy_source_sha256": _digest((directory / "policies.py").read_bytes()),
                    "source_revision": manifest["source_revision"]}
    _require(_artifact_identity(artifact) == _artifact_identity(manifest["policy_artifact"]),
             "Frozen policy identity differs from manifest")


def audit_catalog(output: Path, *, _tokenizer=None) -> dict:
    """Re-audit saved child traces and frozen evidence; never launch or modify a run."""
    output = Path(output)
    manifest = _json((output / "catalog-manifest.json").read_bytes())
    if manifest["policy"] == "language":
        from spire.language import evaluation as language_evaluation
    _require(manifest["schema_version"] == 1, "Unsupported catalog run schema")
    _require(manifest["status"] in {"running", "completed", "stopped", "interrupted"},
             "Unknown catalog run status")
    data = (output / "catalog.json").read_bytes()
    catalog = validate_catalog(_json(data))
    issues = []
    if _digest(data) != manifest["catalog_sha256"]:
        issues.append("Catalog snapshot hash changed")
    if _files(output / "frozen-policy") != manifest["policy_files"]:
        issues.append("Frozen policy snapshot changed")
    language_verified = False
    try:
        _verify_policy(output, manifest)
        if manifest["policy"] == "language":
            language_verified = True
            _require(language_evaluation.dependency_versions()
                     == manifest["policy_artifact"]["dependencies"],
                     "Language tokenizer verification requires recorded dependencies")
            if _tokenizer is None:
                _tokenizer = language_evaluation.load_tokenizer(
                    manifest["policy_artifact"]["declaration"]
                )
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        issues.append(f"Frozen policy: {exc}")
    grouped = {s["id"]: [] for s in catalog["scenarios"]}
    children, sessions = [], set()
    records = manifest["children"]
    _require(len(records) <= len(catalog["schedule"]), "More children than scheduled")
    for index, child in enumerate(records):
        child_issues = []
        expected = resolve_child_suite(catalog, index)
        scenario = next(s for s in catalog["scenarios"]
                        if s["id"] == catalog["schedule"][index]["scenario_id"])
        directory = _path(output, child["directory"])
        audited = audit_run(directory)
        try:
            _require(child["index"] == index and child["scenario_id"] == scenario["id"],
                     "Child assignment differs from schedule")
            _require(child["directory"] == f"runs/attempt-{index:04d}", "Child path mismatch")
            suite_path = output / "suites" / f"attempt-{index:04d}.json"
            _require(_json(suite_path.read_bytes()) == expected, "Child suite changed")
            _require(_files(directory) == child["files"], "Child evidence files changed")
            _require(not child.get("error"), child.get("error", ""))
            result = _json((directory / "evaluation.json").read_bytes())
            _require(result["valid"] is True and audited["valid"], "Child failed evidence audit")
            _require(result["suite"] == expected and result["suite_sha256"]
                     == _digest(suite_path.read_bytes()), "Child evaluation suite mismatch")
            for key in ("source_revision", "source_files"):
                _require(audited["manifest"][key] == manifest[key], f"Child {key} mismatch")
            _require(result["evaluation_source_revision"] == manifest["source_revision"],
                     "Child evaluation revision mismatch")
            _require(_artifact_identity(result["policy_artifact"])
                     == _artifact_identity(manifest["policy_artifact"]),
                     "Child policy identity mismatch")
            config = audited["manifest"]["config"]
            if manifest["policy"] == "language":
                _require(_artifact_identity(config["policy_artifact"])
                         == _artifact_identity(manifest["policy_artifact"]),
                         "Child manifest language policy identity mismatch")
                language_evaluation.verify_language_snapshot(
                    directory / "frozen-language", result["policy_artifact"],
                    verify_external_base=not language_verified,
                )
                _require(result["snapshot_files"] == {
                    f"frozen-language/{name}": value
                    for name, value in _files(directory / "frozen-language").items()
                }, "Child language snapshot inventory mismatch")
                _require(not result["consistency_errors"],
                         "Child language consistency check failed")
                _require(_tokenizer is not None, "Language tokenizer could not be verified")
                language_evaluation.check_recorded_tokens(directory, _tokenizer)
            for key, value in {
                "engine": "original", "scope": "first_combat",
                "observation_version": OBSERVATION_CONTRACT,
                "reset": DECLARATIONS["reset"], "prefix_version": DECLARATIONS["prefix_version"],
            }.items():
                _require(audited["manifest"].get(key) == value, f"Child {key} mismatch")
            _require(_engine(directory) == manifest["engine_pins"], "Engine/mod pins changed")
            _require(config["policy"] == manifest["policy"], "Child policy mismatch")
            for key in ("game_seed", "policy_seed", "episodes", "expected_start_sha256"):
                _require(config[key] == expected[key], f"Child config {key} mismatch")
            _require(len(audited["episodes"]) == 1, "Child must contain exactly one attempt")
            episode = audited["episodes"][0]
            statuses = {"won", "lost"}
            if manifest["policy"] == "language":
                statuses.add("policy_failure")
            _require(episode["status"] in statuses, "Child did not complete a policy attempt")
            _require(episode["combat_start_sha256"] == scenario["expected_start_sha256"],
                     "Audited combat start differs from scenario fingerprint")
            _require(episode["session_id"] not in sessions, "Session reused across children")
            sessions.add(episode["session_id"])
            public = _json((directory / "episode-0000/combat_start.json").read_bytes())
            _require([m["id"] for m in public["combat_state"]["monsters"]]
                     == scenario["monster_ids"], "Observed monster composition differs")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            child_issues.append(str(exc))
        child_episodes = []
        for episode in audited["episodes"]:
            episode = copy.deepcopy(episode)
            episode["episode"] = index  # Unique parent identity for reset comparisons.
            if child_issues and episode["status"] in {"won", "lost", "policy_failure"}:
                episode.update(valid=False, status="invalid_evidence")
            grouped[scenario["id"]].append(episode)
            child_episodes.append(episode)
        issues.extend(f"Child {index}: {issue}" for issue in child_issues)
        children.append({"index": index, "scenario_id": scenario["id"],
                         "directory": child["directory"], "valid": not child_issues,
                         "issues": child_issues, "metrics": _metrics(child_episodes)})
    complete = len(records) == len(catalog["schedule"]) and manifest["status"] == "completed"
    scenarios = {
        name: {"metrics": _metrics(episodes), "reset_comparison": compare_resets(episodes)}
        for name, episodes in grouped.items()
    }
    valid = complete and not issues
    fields = ("win_rate", "policy_attempt_win_rate", "mean_ending_hp",
              "mean_net_hp_lost", "mean_turns")
    macro = {field: mean(s["metrics"][field] for s in scenarios.values())
             if valid and all(s["metrics"][field] is not None for s in scenarios.values())
             else None for field in fields}
    return {
        "schema_version": 1, "valid": valid, "status": manifest["status"], "issues": issues,
        "catalog_sha256": manifest["catalog_sha256"],
        "source_revision": manifest["source_revision"],
        "policy_artifact": manifest["policy_artifact"],
        "children": children, "scenarios": scenarios,
        "metrics": _metrics([episode for episodes in grouped.values() for episode in episodes]),
        "macro": {"weighting": "equal_scenario", "complete": valid, **macro},
        "scheduled_attempts": len(catalog["schedule"]), "attempts_started": len(records),
        "unattempted": len(catalog["schedule"]) - len(records),
        "orchestration_failures": sum(bool(c.get("error")) for c in records),
        "scope": "Declared development scenarios; no held-out generalization claim",
    }


def evaluate_catalog(policy: str, catalog_path: Path, output: Path,
                     *, checkpoint: Path | None = None,
                     language_artifact: Path | None = None, loader=None) -> dict:
    """Own one frozen language model across the schedule, releasing it on every exit."""
    with ExitStack() as stack:
        return _evaluate_catalog(policy, catalog_path, output, checkpoint=checkpoint,
                                 language_artifact=language_artifact, loader=loader, stack=stack)


def _evaluate_catalog(
    policy, catalog_path, output, *, checkpoint, language_artifact, loader, stack,
):
    """Evaluate the frozen schedule once, stopping on failure; no retries or resume."""
    catalog_path, output = Path(catalog_path).resolve(), Path(output).resolve()
    data = catalog_path.read_bytes()
    catalog = validate_catalog(_json(data))
    _require(policy in {"random", "heuristic", "end_turn", "neural", "language"}, "Unknown policy")
    _require((policy == "neural") == (checkpoint is not None), "Policy/checkpoint mismatch")
    _require((policy == "language") == (language_artifact is not None),
             "Policy/language artifact mismatch")
    _require(loader is None or policy == "language", "Model loader requires language policy")
    source = _source()
    watched = {catalog_path: data}
    policy_files = {}
    source_declaration = shared_policy = None
    if language_artifact is not None:
        from spire.language import evaluation as language_evaluation
        from spire.language.policy import LanguagePolicy

        original = Path(language_artifact).resolve()
        _, policy_files = language_evaluation.language_snapshot(original, None)
        source_declaration = policy_files.pop("declaration.json")
        policy_files["source-declaration.json"] = source_declaration
        declaration = _json(source_declaration)
        watched[original] = source_declaration
        if declaration["adapter"] is not None:
            original_adapter = Path(declaration["adapter"]["directory"])
            watched.update({original_adapter / name: policy_files[f"adapter/{name}"]
                            for name in declaration["adapter"]["files"]})
            declaration["adapter"]["directory"] = str(output / "frozen-policy/adapter")
        policy_files["declaration.json"] = (json.dumps(declaration, sort_keys=True, indent=2)
                                             + "\n").encode()
    elif checkpoint is not None:
        _, artifact, binary, original, record, record_bytes = (
            evaluation._neural_artifact(checkpoint)
        )
        watched[original] = binary
        policy_files[original.name] = binary
        if record is not None:
            watched[record] = record_bytes
            policy_files[record.name] = record_bytes
    else:
        original = Path(policies.__file__)
        binary = original.read_bytes()
        watched[original] = binary
        policy_files[original.name] = binary
        artifact = {"type": "builtin", "name": policy, "weights": None,
                    "policy_source_sha256": _digest(binary), **{
                        "source_revision": source["source_revision"]}}
    output.mkdir(parents=True, exist_ok=False)
    for name in ("suites", "runs", "frozen-policy"):
        (output / name).mkdir()
    (output / "catalog.json").write_bytes(data)
    watched[output / "catalog.json"] = data
    for name, content in policy_files.items():
        path = output / "frozen-policy" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        watched[path] = content
    frozen = output / "frozen-policy" / original.name if checkpoint is not None else None
    if language_artifact is not None:
        frozen = output / "frozen-policy/declaration.json"
        shared_policy = stack.enter_context(LanguagePolicy(declaration, loader=loader))
        artifact, _ = language_evaluation.language_snapshot(
            frozen, shared_policy.model_sha256, source_declaration=source_declaration
        )
        artifact["snapshot_path"] = "frozen-policy/declaration.json"
        artifact["adapter_snapshot_path"] = (
            "frozen-policy/adapter" if declaration["adapter"] is not None else None
        )
        for path in (output / "frozen-policy").rglob("*"):
            if path.is_file():
                path.chmod(0o444)
    manifest = {"schema_version": 1, "catalog_sha256": _digest(data), **source,
                "policy": policy, "policy_artifact": artifact,
                "policy_files": _files(output / "frozen-policy"),
                "status": "running", "engine_pins": None, "children": []}
    write_json(output / "catalog-manifest.json", manifest)

    def unchanged():
        _require(_source() == source, "Evaluation source changed")
        _require(all(path.is_file() and path.read_bytes() == content
                     for path, content in watched.items()), "Frozen catalog or policy changed")
        if shared_policy is not None:
            shared_policy.verify_frozen()

    def audit():
        return audit_catalog(output, _tokenizer=shared_policy.tokenizer if shared_policy else None)

    try:
        for index, entry in enumerate(catalog["schedule"]):
            unchanged()
            if manifest["children"]:
                _require(not audit()["issues"], "Earlier child evidence changed")
            suite_path = output / "suites" / f"attempt-{index:04d}.json"
            write_json(suite_path, resolve_child_suite(catalog, index))
            child = {"index": index, "scenario_id": entry["scenario_id"],
                     "directory": f"runs/attempt-{index:04d}", "files": {}}
            manifest["children"].append(child)
            write_json(output / "catalog-manifest.json", manifest)
            directory = output / child["directory"]
            try:
                if shared_policy is not None:
                    language_evaluation.evaluate_language(
                        frozen, suite_path, directory, _policy=shared_policy,
                        _source_declaration=source_declaration,
                    )
                else:
                    evaluation.evaluate(policy, suite_path, directory, checkpoint=frozen)
                if manifest["engine_pins"] is None:
                    manifest["engine_pins"] = _engine(directory)
                unchanged()
            except Exception as exc:
                child["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                child["files"] = _files(directory)
                write_json(output / "catalog-manifest.json", manifest)
            report = audit()
            if report["issues"]:
                manifest["status"] = "stopped"
                break
        else:
            manifest["status"] = "completed"
    except BaseException:
        manifest["status"] = "interrupted"
        raise
    finally:
        write_json(output / "catalog-manifest.json", manifest)
    result = audit()
    write_json(output / "catalog-evaluation.json", result)
    return result
