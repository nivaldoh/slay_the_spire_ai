"""Compact comparisons generated from audited evidence."""

import json
import re
from pathlib import Path

from spire.evidence import summarize_run


def _comparison_contract(run: dict) -> tuple[dict, list[str]]:
    """Compare declared experiments, not a coincidentally equal sample of starts.

    Policy identity and implementation revision may change between candidates.
    Unknown config/suite fields remain in the contract so a future distribution
    or observation option cannot silently disappear from comparisons.
    """
    provenance = run["provenance"]
    config = provenance.get("config") or {}
    if not isinstance(config, dict):
        return {}, ["manifest config is not an object"]
    contract = {
        key: provenance.get(key)
        for key in ("engine", "scope", "observation_version", "prefix_version", "reset")
    }
    issues = [f"missing {key}" for key, value in contract.items() if not value]
    contract["config"] = {
        key: value for key, value in config.items() if key not in {"policy", "policy_artifact"}
    }
    artifact = config.get("policy_artifact") or {}
    if not isinstance(artifact, dict):
        artifact = {}
        issues.append("policy artifact metadata is not an object")
    contract["policy_observation_contract"] = artifact.get(
        "observation_contract", provenance.get("observation_version")
    )
    for key in (
        "game_seed", "expected_start_sha256", "policy_seed", "episodes",
        "max_actions", "episode_timeout", "bridge_timeout",
    ):
        if config.get(key) is None:
            issues.append(f"missing config.{key}")
    expected = config.get("expected_start_sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
        issues.append("starting distribution is not pinned by a valid expected_start_sha256")
    elif run["reset_comparison"]["initial_state_hashes"] != [expected]:
        issues.append("observed combat starts do not match the declared starting state")

    # The public files have already been matched to the raw engine trace by the audit.
    starts = set()
    directory = Path(run["directory"])
    try:
        for episode in run["episodes"]:
            if episode["valid"] and episode.get("combat_start_sha256"):
                public = json.loads(
                    (directory / f"episode-{episode['episode']:04d}" / "combat_start.json")
                    .read_text()
                )
                starts.add((public["class"], public["ascension_level"], public["contract"]))
        contract["observed_start_contracts"] = sorted(starts)
        if not starts:
            issues.append("no audited starting character, ascension, or observation contract")
        for _, _, observation in starts:
            if observation != provenance.get("observation_version"):
                issues.append("public observation contract differs from manifest")
        environment = json.loads((directory / "environment.json").read_text())
        contract["engine_sha256"] = environment["game"]["sha256"]
        contract["mod_sha256"] = {
            name: mod["sha256"] for name, mod in environment["mods"].items()
        }
        hashes = [contract["engine_sha256"], *contract["mod_sha256"].values()]
        if not contract["mod_sha256"] or not all(
            isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) for value in hashes
        ):
            issues.append("missing game/mod content hashes")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        issues.append(f"incomplete starting-state or engine evidence: {exc}")

    evaluation_path = directory / "evaluation.json"
    contract["evaluation_suite"] = None
    if evaluation_path.exists():
        try:
            evaluation = json.loads(evaluation_path.read_text())
            suite = evaluation["suite"]
            if not isinstance(suite, dict):
                raise ValueError("suite is not an object")
            contract["evaluation_suite"] = suite
            contract["suite_sha256"] = evaluation["suite_sha256"]
            if evaluation.get("schema_version") != 1 or evaluation.get("valid") is not True:
                issues.append("evaluation record is not valid schema 1")
            if not re.fullmatch(r"[a-f0-9]{64}", evaluation["suite_sha256"]):
                issues.append("missing suite content hash")
            for key in ("game_seed", "expected_start_sha256", "policy_seed", "episodes"):
                if suite[key] != config.get(key):
                    issues.append(f"evaluation suite {key} differs from manifest")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            issues.append(f"incomplete evaluation record: {exc}")
    for declarations in (config, contract["evaluation_suite"] or {}):
        for key, index in (
            ("character", 0), ("class", 0), ("ascension", 1), ("ascension_level", 1),
            ("observation_version", 2), ("observation_contract", 2),
        ):
            if key in declarations and any(declarations[key] != start[index] for start in starts):
                issues.append(f"declared {key} differs from observed public starting state")
    if contract["policy_observation_contract"] != provenance.get("observation_version"):
        issues.append("policy observation contract differs from manifest")
    return contract, issues


def compare_runs(directories: list[Path]) -> dict:
    runs = [summarize_run(directory) for directory in directories]
    contracts, issues = [], []
    for run in runs:
        contract, run_issues = _comparison_contract(run)
        contracts.append(contract)
        issues.extend(f"{Path(run['directory']).name}: {issue}" for issue in run_issues)
        if not run["valid"]:
            issues.append(f"{Path(run['directory']).name}: run failed evidence audit")
    differences = sorted(
        key
        for key in {key for contract in contracts for key in contract}
        if any(contract.get(key) != contracts[0].get(key) for contract in contracts[1:])
    )
    return {
        "schema_version": 1,
        "valid": all(run["valid"] for run in runs),
        "same_protocol": bool(runs) and not differences and not issues,
        "protocol_differences": differences,
        "comparison_issues": issues,
        "comparison_contracts": contracts,
        "scope": "Recorded original-engine combat attempts; no generalization claim",
        "runs": runs,
    }


def render_report(report: dict) -> str:
    lines = [
        "# Combat evidence report",
        "",
        report["scope"],
        "",
        "| Run | Policy | Wins / valid games | Wins / policy attempts | Policy failures | "
        "Attempts | Mean final HP | Evidence valid |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for run in report["runs"]:
        metrics = run["metrics"]
        policy = run["provenance"]["config"]["policy"]
        hp = metrics["mean_ending_hp"]
        hp_text = f"{hp:.2f}" if hp is not None else "—"
        # Saved reports from before language policies have only completed-game counts.
        failures = metrics.get("policy_failures", 0 if policy != "language" else "—")
        attempts = metrics.get(
            "policy_attempts", metrics["valid_gameplay_episodes"] if policy != "language" else "—"
        )
        lines.append(
            f"| [{Path(run['directory']).name}]({run['evidence'].get('manifest.json', '')}) "
            f"| {policy} | {metrics['wins']} / {metrics['valid_gameplay_episodes']} "
            f"| {metrics['wins']} / {attempts} | {failures} "
            f"| {metrics['attempts']} | {hp_text} | {run['valid']} |"
        )
        if run["issues"]:
            lines.extend(["", f"Audit issues: {'; '.join(run['issues'])}"])
    lines.extend(
        [
            "",
            "HP includes engine postcombat healing. Infrastructure failures, unsupported states,",
            "limits, and interruptions remain attempts but do not become gameplay losses.",
            "Policy-attempt denominators include recorded model failures; final HP and gameplay "
            "win rates include only verified game endings.",
        ]
    )
    if not report["same_protocol"]:
        lines.extend(
            [
                "",
                "A shared protocol is not established; "
                "these scores are not a controlled comparison.",
            ]
        )
        if report.get("protocol_differences"):
            lines.append("Different contract fields: " + ", ".join(report["protocol_differences"]))
        lines.extend(report.get("comparison_issues", []))
    return "\n".join(lines) + "\n"
