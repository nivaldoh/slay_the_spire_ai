"""Audited public-action demonstrations, with origin-level split boundaries.

Only known builtin public teachers are supported. A ``heuristic_relabel`` source
labels public states visited by any recorded behavior policy with the current public
heuristic. This exporter neither trains nor evaluates a language model, and never
generates reasoning targets.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from spire.combat.evidence import EvidenceError, audit_run
from spire.policies import RandomPolicy, StarterHeuristicPolicy
from spire.protocol import (
    OBSERVATION_CONTRACT,
    Action,
    Decision,
    IllegalActionError,
    validate_action,
)
from spire.provenance import REPO_ROOT

# Teacher and observation sources are pinned at their recorded paths in this directory.
PACKAGE_DIR = REPO_ROOT / "src/spire"

FORMAT_VERSION = "public-card-table-choice-v1"
PROMPT = (
    "Choose one legal action to win this combat and preserve HP. "
    "Card indexes refer to the cards table. Choices are [kind,hand_slot,target_slot]; "
    "slots are zero-based and null means unused. "
    'Reply only with {"a":N}, where N is the zero-based choice index.\n'
)
SPLITS = ("train", "validation", "test")
TEACHERS = {"heuristic": StarterHeuristicPolicy, "random": RandomPolicy}
RELABEL = "heuristic_relabel"
IMPLEMENTATION_PATHS = (
    "src/",
    "scripts/",
    "configs/",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
)
CARD_FIELDS = {
    "id",
    "name",
    "type",
    "rarity",
    "cost",
    "upgrades",
    "has_target",
    "exhausts",
    "ethereal",
    "misc",
    "is_playable",
}


@dataclass(frozen=True)
class DemonstrationSource:
    run: Path
    split: str
    source_role: str
    teacher_information: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read(path: Path) -> dict:
    return json.loads(path.read_text())


def _fields(value: dict, allowed: set[str], name: str) -> None:
    _require(
        isinstance(value, dict) and not value.keys() - allowed, f"Unrecognized public {name} fields"
    )


def public_input(decision: Decision) -> dict:
    """Losslessly compact the current allowlisted observation; retain all slots."""
    observation = decision.to_dict()["observation"]
    _require(
        observation.get("contract") == OBSERVATION_CONTRACT, "Unsupported observation contract"
    )
    _fields(
        observation,
        {
            "class",
            "ascension_level",
            "floor",
            "act",
            "gold",
            "current_hp",
            "max_hp",
            "contract",
            "excluded_actions",
            "deck",
            "relics",
            "potions",
            "combat_state",
        },
        "observation",
    )
    combat = observation["combat_state"]
    _fields(
        combat,
        {
            "turn",
            "cards_discarded_this_turn",
            "times_damaged",
            "player",
            "monsters",
            "hand",
            "draw_pile",
            "discard_pile",
            "exhaust_pile",
        },
        "combat",
    )
    for creature, monster in [
        (combat["player"], False),
        *((item, True) for item in combat["monsters"]),
    ]:
        allowed = {"current_hp", "max_hp", "block", "powers"}
        allowed |= (
            {"id", "name", "intent", "half_dead", "is_gone", "move_adjusted_damage", "move_hits"}
            if monster
            else {"energy"}
        )
        _fields(creature, allowed, "creature")
        for power in creature["powers"]:
            _fields(power, {"id", "name", "amount"}, "power")
    for relic in observation["relics"]:
        _fields(relic, {"id", "name", "counter"}, "relic")
    for potion in observation["potions"]:
        _fields(potion, {"id", "name", "can_use", "can_discard", "requires_target"}, "potion")
    table, indexes = [], {}
    for owner, pile in [
        (observation, "deck"),
        *((combat, name) for name in ("hand", "draw_pile", "discard_pile", "exhaust_pile")),
    ]:
        slots = []
        for card in owner[pile]:
            _fields(card, CARD_FIELDS, "card")
            key = _json(card)
            if key not in indexes:
                indexes[key] = len(table)
                table.append(card)
            slots.append(indexes[key])
        owner[pile] = slots
    choices = []
    for action in decision.candidates:
        validate_action(decision, action)
        _require(action.kind in ("play", "end"), "Unsupported demonstration action")
        choices.append([action.kind, action.hand_index, action.target_index])
    _require(bool(choices), "No legal demonstration choices")
    result = {"observation": observation, "cards": table, "choices": choices}
    _json(result)  # Reject nonfinite values before rendering model text.
    return result


def render_prompt(decision: Decision) -> str:
    return PROMPT + _json(public_input(decision))


def parse_completion(decision: Decision, text: str) -> Action:
    """Accept exactly one local candidate index, without repair or fallback.

    The caller must still validate against its current Decision before sending;
    returned actions retain the supplied Decision's session/sequence binding.
    """

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(text, object_pairs_hook=unique_keys)
    except (ValueError, TypeError) as error:
        raise IllegalActionError("Completion must be a single JSON action object") from error
    if (
        type(value) is not dict
        or set(value) != {"a"}
        or type(value["a"]) is not int
        or not 0 <= value["a"] < len(decision.candidates)
    ):
        raise IllegalActionError("Completion requires exactly one in-range integer action index")
    return validate_action(decision, decision.candidates[value["a"]])


def _source_bytes(revision: str, filename: str) -> bytes:
    _require(re.fullmatch(r"[a-f0-9]{40}", revision) is not None, "Invalid teacher source revision")
    try:
        return subprocess.check_output(
            ["git", "show", f"{revision}:{filename}"],
            cwd=REPO_ROOT,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise EvidenceError(
            f"Preserved teacher source unavailable: {revision}:{filename}"
        ) from error


def _known_ast(source: bytes, *, policies: bool) -> str:
    tree = ast.parse(source)
    # These exact independent classes were added after the first teacher runs.
    # Normalize only their absence/presence; every public projection and teacher
    # statement, import and other declaration still has to match the known source.
    optional_name = "EndTurnPolicy" if policies else "PolicyFailure"
    if policies:
        reference = ast.parse((PACKAGE_DIR / "policies.py").read_bytes())
        optional = next(
            item
            for item in reference.body
            if isinstance(item, ast.ClassDef) and item.name == optional_name
        )
    else:
        optional = ast.parse('''class PolicyFailure(ProtocolError):
    """A policy output/context failure before any command was selected."""

    def __init__(self, message: str, *, failure: dict):
        super().__init__(message)
        self.failure = failure
''').body[0]
    retained, found = [], False
    for item in tree.body:
        if isinstance(item, ast.ClassDef) and item.name == optional_name:
            _require(
                not found and ast.dump(item) == ast.dump(optional),
                f"Unknown optional {optional_name} declaration",
            )
            found = True
        else:
            retained.append(item)
    tree.body = retained
    return ast.dump(tree, include_attributes=False)


def _verify_teacher(manifest: dict, run: Path, role: str) -> dict[str, bytes]:
    _require(role in TEACHERS, "Unsupported or privileged teacher source role")
    _require(manifest["config"]["policy"] == role, "Source role differs from recorded policy")
    _require(
        manifest.get("source_status") == "" and (run / "source.patch").read_bytes() == b"",
        "Teacher requires preserved clean source provenance",
    )
    _require(
        manifest.get("teacher_information", "public") == "public"
        and manifest.get("privileged_teacher", False) is False,
        "Privileged teacher evidence is outside the public-teacher contract",
    )
    snapshots = {}
    for filename in ("policies.py", "protocol.py"):
        relative = f"src/spire/{filename}"
        saved = _source_bytes(manifest["source_revision"], relative)
        _require(
            manifest.get("source_files", {}).get(relative) == _sha(saved),
            f"Teacher source hash differs from manifest: {relative}",
        )
        current = (PACKAGE_DIR / filename).read_bytes()
        _require(
            _known_ast(saved, policies=filename == "policies.py")
            == _known_ast(current, policies=filename == "policies.py"),
            f"Unknown public teacher implementation: {relative}",
        )
        snapshots[relative] = saved
    return snapshots


def _verify_observer(manifest: dict, run: Path) -> dict[str, bytes]:
    """Relabel sources need committed observation code, not a particular behavior policy."""
    status = manifest.get("source_status")
    _require(isinstance(status, str), "Relabel source requires recorded source status")
    paths = [
        path.strip().strip('"') for line in status.splitlines() for path in line[3:].split(" -> ")
    ]
    _require(
        not any(path.startswith(IMPLEMENTATION_PATHS) for path in paths),
        "Relabel source requires committed implementation files",
    )
    _require(
        manifest.get("teacher_information", "public") == "public"
        and manifest.get("privileged_teacher", False) is False,
        "Privileged behavior evidence is outside the public relabel contract",
    )
    relative = "src/spire/protocol.py"
    saved = _source_bytes(manifest["source_revision"], relative)
    _require(
        manifest.get("source_files", {}).get(relative) == _sha(saved),
        f"Observation source hash differs from manifest: {relative}",
    )
    _require(
        _known_ast(saved, policies=False)
        == _known_ast((PACKAGE_DIR / "protocol.py").read_bytes(), policies=False),
        "Unknown public observation implementation",
    )
    return {
        relative: saved,
        "src/spire/policies.py": (PACKAGE_DIR / "policies.py").read_bytes(),
    }


def _suite_snapshot(run: Path, manifest: dict, record: dict) -> bytes:
    """Recover frozen suite bytes from evidence or the recorded Git revision."""
    expected = record.get("suite_sha256")
    _require(
        isinstance(expected, str) and re.fullmatch(r"[a-f0-9]{64}", expected) is not None,
        "Evaluation requires a preserved suite hash",
    )
    candidates = [run / "suite.json", run.parent.parent / "suites" / f"{run.name}.json"]
    for path in candidates:
        if path.is_file() and _sha(data := path.read_bytes()) == expected:
            _require(json.loads(data) == record["suite"], "Captured evaluation suite differs")
            return data
    revision = manifest["source_revision"]
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", revision, "--", "configs"],
        cwd=REPO_ROOT,
        text=True,
        stderr=subprocess.PIPE,
    ).splitlines()
    for name in paths:
        if name.endswith(".json") and _sha(data := _source_bytes(revision, name)) == expected:
            _require(json.loads(data) == record["suite"], "Historical evaluation suite differs")
            return data
    raise EvidenceError("Preserved evaluation suite bytes unavailable or hash differs")


def _original_purpose(
    run: Path, manifest: dict, episodes: list[dict], *, builtin_teacher: bool = True
) -> tuple[str, bytes | None]:
    evaluation = run / "evaluation.json"
    suite_bytes = None
    declared_evaluation = (
        "evaluate" in manifest.get("command", []) or "policy_artifact" in manifest["config"]
    )
    _require(
        not declared_evaluation or evaluation.is_file(), "Originating evaluation record is missing"
    )
    if evaluation.exists():
        record = _read(evaluation)
        _require(record.get("valid") is True, "Evaluation source is not valid")
        suite = record.get("suite", {})
        _require(
            type(record.get("schema_version")) is int and record["schema_version"] == 1,
            "Unsupported evaluation record schema",
        )
        _require(
            type(suite.get("schema_version")) is int and suite["schema_version"] == 1,
            "Unsupported evaluation suite schema",
        )
        purpose = suite.get("purpose")
        fixed = {
            "character": "IRONCLAD",
            "class": "IRONCLAD",
            "ascension": 0,
            "ascension_level": 0,
            "observation_version": OBSERVATION_CONTRACT,
            "observation_contract": OBSERVATION_CONTRACT,
        }
        _fields(
            suite,
            {
                "schema_version",
                "id",
                "purpose",
                "description",
                "game_seed",
                "policy_seed",
                "episodes",
                "expected_start_sha256",
                *fixed,
            },
            "suite",
        )
        _require(
            isinstance(suite.get("id"), str) and bool(suite["id"]),
            "Evaluation suite requires an identifier",
        )
        for name, expected in fixed.items():
            _require(
                name not in suite
                or (type(suite[name]) is type(expected) and suite[name] == expected),
                "Unsupported evaluation suite declaration",
            )
        for name in ("game_seed", "policy_seed", "episodes", "expected_start_sha256"):
            _require(
                name in suite
                and type(suite[name]) is type(manifest["config"].get(name))
                and suite[name] == manifest["config"].get(name),
                f"Evaluation suite {name} differs from originating run",
            )
        _require(
            all(
                episode["combat_start_sha256"] == suite["expected_start_sha256"]
                for episode in episodes
            ),
            "Evaluation actual start differs from suite",
        )
        _require(not record.get("consistency_errors"), "Evaluation has consistency errors")
        _require(
            record.get("evaluation_source_revision", manifest["source_revision"])
            == manifest["source_revision"],
            "Evaluation source revision differs",
        )
        suite_bytes = _suite_snapshot(run, manifest, record)
        _require(
            manifest.get("purpose", purpose) == purpose, "Source purpose declarations conflict"
        )
        artifact = record.get("policy_artifact", {})
        _require(
            not builtin_teacher
            or (
                artifact.get("type") == "builtin"
                and artifact.get("name") == manifest["config"]["policy"]
                and artifact.get("source_revision") == manifest["source_revision"]
                and artifact.get("policy_source_sha256")
                == manifest["source_files"]["src/spire/policies.py"]
            ),
            "Evaluation teacher provenance differs from originating run",
        )
    else:
        purpose = manifest.get("purpose", "rollout")
    _require(
        purpose
        in {
            "rollout",
            "training",
            "development",
            "validation",
            "test",
            "final_test",
            "held_out",
            "held_out_evaluation",
        },
        "Unknown original source purpose",
    )
    return purpose, suite_bytes


def _inventory(run: Path) -> dict[str, str]:
    paths = [run / name for name in ("manifest.json", "environment.json", "source.patch")]
    for path in (
        run / "evaluation.json",
        run / "suite.json",
        run.parent.parent / "suites" / f"{run.name}.json",
    ):
        if path.exists():
            paths.append(path)
    for episode in sorted(run.glob("episode-*")):
        paths.extend(
            episode / name
            for name in ("trace.jsonl", "result.json", "combat_start.json", "deployment.json")
        )
    return {
        str(path.relative_to(run))
        if path.is_relative_to(run)
        else f"catalog-suite/{path.name}": _sha(path.read_bytes())
        for path in paths
    }


def export_demonstrations(
    output: Path,
    sources: list[DemonstrationSource],
    *,
    purpose: str,
) -> dict:
    """Export complete audited origins with explicit, nonrandom split assignments.

    Purpose is ``smoke`` (train split only), ``supervised_finetuning`` or
    ``offline_evaluation`` (test split only). Exact duplicates remain separate rows.
    Source role is ``heuristic`` or ``random``, each source-verified and replayed
    independently, or ``heuristic_relabel``, which labels every audited public state
    with the current public heuristic regardless of the recorded behavior policy.
    """
    output = Path(output).resolve()
    _require(not output.exists(), "Dataset output already exists")
    _require(
        purpose in {"smoke", "supervised_finetuning", "offline_evaluation"},
        "Explicit supported dataset purpose required",
    )
    _require(bool(sources), "Dataset requires at least one source")
    rows = {split: [] for split in SPLITS}
    origins, source_records, snapshots, groups = [], [], {}, {}
    suite_snapshots = {}
    input_inventories, run_identities, prompt_counts, example_counts = (
        [],
        set(),
        Counter(),
        Counter(),
    )

    def group(kind: str, identity: str, split: str) -> None:
        key = (kind, identity)
        _require(key not in groups or groups[key] == split, f"Cross-split {kind} leakage")
        groups[key] = split

    for source in sources:
        _require(
            isinstance(source, DemonstrationSource),
            "Source must declare role, split and information",
        )
        _require(source.split in SPLITS, "Unknown dataset split")
        _require(
            purpose != "smoke" or source.split == "train", "Smoke datasets have one train split"
        )
        _require(
            purpose != "offline_evaluation" or source.split == "test",
            "Offline evaluation datasets have one test split",
        )
        relabel = source.source_role == RELABEL
        _require(source.teacher_information == "public", "Privileged teacher sources are rejected")
        run = Path(source.run).resolve()
        _require(not output.is_relative_to(run), "Dataset output must be outside source runs")
        inventory = _inventory(run)
        audited = audit_run(run)
        _require(audited["valid"], f"Source failed independent audit: {audited['issues']}")
        manifest = audited["manifest"]
        _require(
            manifest["status"] == "completed"
            and bool(audited["episodes"])
            and all(item["status"] in ("won", "lost") for item in audited["episodes"]),
            "Only complete originating runs may supply demonstrations",
        )
        verified = (
            _verify_observer(manifest, run)
            if relabel
            else _verify_teacher(manifest, run, source.source_role)
        )
        original_purpose, suite_bytes = _original_purpose(
            run, manifest, audited["episodes"], builtin_teacher=not relabel
        )
        if suite_bytes is not None:
            suite_snapshots[_sha(suite_bytes)] = suite_bytes
        _require(
            source.split == "test"
            or original_purpose not in {"test", "final_test", "held_out", "held_out_evaluation"},
            "Held-out evaluation origins cannot supply training or validation",
        )
        run_id = _sha(_json(inventory).encode())
        _require(run_id not in run_identities, "Duplicate originating run supplied")
        run_identities.add(run_id)
        group("origin_run", run_id, source.split)
        game_seed = manifest["config"]["game_seed"]
        scenario_family = _sha(
            _json({"game_seed": game_seed, "engine": "original", "scope": "first_combat"}).encode()
        )
        group("scenario_seed_family", scenario_family, source.split)
        source_records.append(
            {
                "run": str(run),
                "run_sha256": run_id,
                "split": source.split,
                "source_role": source.source_role,
                "teacher_information": (
                    "public_builtin_relabel" if relabel else "verified_public_builtin"
                ),
                **({"behavior_policy": manifest["config"]["policy"]} if relabel else {}),
                "original_purpose": original_purpose,
                "evaluation_suite_sha256": _sha(suite_bytes) if suite_bytes is not None else None,
                "development_reuse": original_purpose == "development",
                "source_revision": manifest["source_revision"],
                "files": inventory,
                "teacher_sources": {name: _sha(data) for name, data in verified.items()},
            }
        )
        snapshots.update({_sha(data): data for data in verified.values()})
        input_inventories.append((run, inventory))
        for episode in audited["episodes"]:
            session = episode["session_id"]
            group("origin_session", session, source.split)
            start_hash = episode["combat_start_sha256"]
            group("public_start_family", start_hash, source.split)
            transitions = episode["transitions"]
            _require(
                bool(transitions)
                and all(item["ingestible"] for item in transitions)
                and transitions[-1]["terminal"],
                "Incomplete demonstrated action sequence",
            )
            teacher = (
                TEACHERS[source.source_role](episode["result"]["policy_seed"])
                if source.source_role == "random"
                else StarterHeuristicPolicy()
            )
            trace_name = f"episode-{episode['episode']:04d}/trace.jsonl"
            for transition in transitions:
                decision = Decision(
                    transition["action"]["decision_id"],
                    transition["observation"],
                    tuple(Action(**item) for item in transition["candidates"]),
                )
                behavior = validate_action(decision, transition["action_id"])
                selected = teacher.choose(decision)
                _require(
                    relabel or selected == behavior,
                    "Recorded action differs from replayed public teacher",
                )
                selected_index = decision.candidates.index(selected)
                prompt = render_prompt(decision)
                completion = _json({"a": selected_index})
                prompt_hash = _sha(prompt.encode())
                example_hash = _sha(_json([prompt, completion]).encode())
                group("identical_public_prompt", prompt_hash, source.split)
                prompt_counts[prompt_hash] += 1
                example_counts[example_hash] += 1
                row_index = len(rows[source.split])
                rows[source.split].append({"prompt": prompt, "completion": completion})
                origins.append(
                    {
                        "split": source.split,
                        "row": row_index,
                        "prompt_sha256": prompt_hash,
                        "example_sha256": example_hash,
                        "origin_run_sha256": run_id,
                        "session_id": session,
                        "episode": episode["episode"],
                        "transition_id": transition["transition_id"],
                        "sequence": transition["sequence"],
                        "scenario_id": manifest.get("scenario", {}).get("scenario_id"),
                        "scenario_seed_family_sha256": scenario_family,
                        "public_start_sha256": start_hash,
                        "trace_sha256": inventory[trace_name],
                        "source_role": source.source_role,
                        "outcome": episode["status"],
                        "ending_hp": episode["ending_hp"],
                        "selected_action": selected.to_dict(),
                        **(
                            {
                                "behavior_policy": manifest["config"]["policy"],
                                "behavior_action": behavior.to_dict(),
                            }
                            if relabel
                            else {}
                        ),
                    }
                )
    _require(any(rows.values()), "No demonstrated public actions")
    for run, inventory in input_inventories:
        _require(_inventory(run) == inventory, "Source evidence changed during export")
    manifest = {
        "schema_version": 1,
        "status": "completed",
        "purpose": purpose,
        "format_version": FORMAT_VERSION,
        "observation_contract": OBSERVATION_CONTRACT,
        "exporter_sha256": _sha(Path(__file__).read_bytes()),
        "split_rule": "whole_origin_and_game_seed_and_public_start_and_prompt_v1",
        "duplicates": "preserved_with_all_origins",
        "sources": source_records,
        "rows": {split: len(values) for split, values in rows.items()},
        "unique_prompts": len(prompt_counts),
        "unique_examples": len(example_counts),
        "duplicate_rows": sum(count - 1 for count in example_counts.values()),
        "scenario_seed_families": len({item["scenario_seed_family_sha256"] for item in origins}),
        "public_start_families": len({item["public_start_sha256"] for item in origins}),
        "development_reuse": any(item["development_reuse"] for item in source_records),
        "research_scope": "diagnostic_development",
        "scope": "Declared public-teacher imitation data; no held-out gameplay claim",
    }
    # Validation finishes before files are created. A final manifest marks a
    # completed export; no source file or originating run is modified.
    output.mkdir(parents=True)
    files = {}
    for name, values in {
        **{f"{split}.jsonl": values for split, values in rows.items() if values},
        "origins.jsonl": origins,
    }.items():
        data = "".join(_json(value) + "\n" for value in values).encode()
        (output / name).write_bytes(data)
        files[name] = _sha(data)
    (output / "teacher_sources").mkdir()
    for identity, data in snapshots.items():
        name = f"teacher_sources/{identity}.py"
        (output / name).write_bytes(data)
        files[name] = identity
    if suite_snapshots:
        (output / "source_suites").mkdir()
        for identity, data in suite_snapshots.items():
            name = f"source_suites/{identity}.json"
            (output / name).write_bytes(data)
            files[name] = identity
    manifest["files"] = files
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest
