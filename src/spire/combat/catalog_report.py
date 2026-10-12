"""Comparisons of complete catalog evaluations, rebuilt from authoritative audits."""

from __future__ import annotations

import json
from pathlib import Path

from spire.combat.catalog import audit_catalog


def _read(path: Path) -> dict:
    return json.loads(path.read_text())


def _run(directory: Path) -> dict:
    directory = directory.resolve()
    result = {"directory": str(directory), "comparison_issues": []}
    try:
        # The saved catalog-evaluation.json is a convenience output, not authority.
        result.update(audit_catalog(directory))
        manifest = _read(directory / "catalog-manifest.json")
        catalog = _read(directory / "catalog.json")
        result["catalog"] = catalog
        result["policy"] = manifest["policy"]
        if manifest["policy"] == "language":
            artifact = manifest["policy_artifact"]
            declaration = artifact["declaration"]
            result["language_policy_contract"] = {
                "base": {key: declaration["base"][key] for key in ("id", "revision", "files")},
                **{key: declaration[key] for key in (
                    "prompt_format", "parser_version", "decoder", "max_prompt_tokens",
                )},
                "dependencies": artifact["dependencies"],
            }
        contract = {
            "catalog_sha256": result["catalog_sha256"], "catalog": catalog,
            "engine_pins": manifest["engine_pins"],
        }
        protocols = []
        for child in manifest["children"]:
            # audit_catalog has checked child paths, file hashes, and engine evidence.
            child_manifest = _read(directory / child["directory"] / "manifest.json")
            protocol = {
                key: child_manifest[key]
                for key in ("engine", "scope", "observation_version", "prefix_version", "reset")
            }
            protocol["rollout_config"] = {
                key: value for key, value in child_manifest["config"].items()
                if key not in {"policy", "policy_artifact", "game_seed", "policy_seed",
                               "expected_start_sha256"}
            }
            for key in ("max_actions", "episode_timeout", "bridge_timeout"):
                if protocol["rollout_config"].get(key) is None:
                    result["comparison_issues"].append(f"Child {child['index']} lacks {key}")
            protocols.append(protocol)
        if not protocols:
            result["comparison_issues"].append("No child protocol evidence")
        else:
            contract.update(protocols[0])
            if any(protocol != protocols[0] for protocol in protocols[1:]):
                result["comparison_issues"].append("Child rollout protocols differ within catalog")
        if result["status"] != "completed" or result["unattempted"]:
            result["comparison_issues"].append(
                f"Incomplete catalog: {result['attempts_started']}/{result['scheduled_attempts']} "
                f"attempts started, status={result['status']}"
            )
        if not result["valid"]:
            result["comparison_issues"].append("Catalog failed authoritative evidence audit")
            result["comparison_issues"].extend(result["issues"])
        result["comparison_contract"] = contract
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result.update(valid=False, status="unavailable", issues=[str(exc)])
        result["comparison_issues"].append(f"Cannot audit catalog: {exc}")
        result["comparison_contract"] = None
    return result


def compare_catalogs(directories: list[Path]) -> dict:
    """Compare fixed schedules, allowing different policies, weights, and source revisions."""
    runs = [_run(Path(directory)) for directory in directories]
    contracts = [run["comparison_contract"] or {} for run in runs]
    differences = sorted(
        key for key in {key for contract in contracts for key in contract}
        if any(contract.get(key) != contracts[0].get(key) for contract in contracts[1:])
    )
    language_contracts = [run["language_policy_contract"] for run in runs
                          if "language_policy_contract" in run]
    if language_contracts and any(value != language_contracts[0]
                                  for value in language_contracts[1:]):
        differences.append("language_policy_contract")
    issues = [f"{Path(run['directory']).name}: {issue}"
              for run in runs for issue in run["comparison_issues"]]
    return {
        "schema_version": 1, "kind": "catalog_comparison",
        "valid": bool(runs) and all(run["valid"] for run in runs),
        "same_protocol": bool(runs) and not differences and not issues,
        "protocol_differences": differences, "comparison_issues": issues,
        "scope": "Declared development scenarios; no held-out generalization claim",
        "runs": runs,
    }


def _number(value) -> str:
    return "—" if value is None else f"{value:.3f}"


def render_catalog_report(report: dict) -> str:
    lines = [
        "# Catalog evidence report", "", report["scope"], "",
        "Macro scores weight each scenario equally and require a complete audited schedule.", "",
        "| Run | Policy | Macro win rate | Macro policy-attempt win rate | Macro final HP | "
        "Wins / valid games | Wins / policy attempts | Policy failures | "
        "Started / scheduled | Infra failures | Orchestration failures | Unattempted | Valid |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for run in report["runs"]:
        directory = Path(run["directory"])
        metrics = run.get("metrics", {})
        macro = run.get("macro", {}) if run["valid"] else {}
        lines.append(
            f"| [{directory.name}]({directory / 'catalog-manifest.json'}) "
            f"| {run.get('policy', '—')} | {_number(macro.get('win_rate'))} "
            f"| {_number(macro.get('policy_attempt_win_rate'))} "
            f"| {_number(macro.get('mean_ending_hp'))} "
            f"| {metrics.get('wins', '—')} / {metrics.get('valid_gameplay_episodes', '—')} "
            f"| {metrics.get('wins', '—')} / {metrics.get('policy_attempts', '—')} "
            f"| {metrics.get('policy_failures', '—')} "
            f"| {run.get('attempts_started', '—')} / {run.get('scheduled_attempts', '—')} "
            f"| {metrics.get('infrastructure_failures', '—')} "
            f"| {run.get('orchestration_failures', '—')} | {run.get('unattempted', '—')} "
            f"| {run['valid']} |"
        )
    lines.extend([
        "", "| Run | Scenario | Family | Wins / valid games | Wins / policy attempts | "
        "Policy failures | Mean final HP | Attempts | Infra failures |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for run in report["runs"]:
        definitions = {s["id"]: s for s in run.get("catalog", {}).get("scenarios", [])}
        for name, scenario in run.get("scenarios", {}).items():
            metrics = scenario["metrics"]
            lines.append(
                f"| {Path(run['directory']).name} | {name} "
                f"| {definitions.get(name, {}).get('encounter_family', '—')} "
                f"| {metrics['wins']} / {metrics['valid_gameplay_episodes']} "
                f"| {metrics['wins']} / {metrics['policy_attempts']} "
                f"| {metrics['policy_failures']} "
                f"| {_number(metrics['mean_ending_hp'])} | {metrics['attempts']} "
                f"| {metrics['infrastructure_failures']} |"
            )
    lines.extend([
        "", "HP includes engine postcombat healing. Infrastructure and orchestration failures "
        "remain attempts; they are not gameplay losses.",
        "Policy-attempt win rates include language parser/context failures. Gameplay and HP "
        "macro scores require completed gameplay in every scenario; failures are never retried.",
    ])
    if not report["same_protocol"]:
        lines.extend(["", "A shared complete protocol is not established; "
                      "these scores are not a controlled comparison."])
        if report["protocol_differences"]:
            lines.append("Different contract fields: " + ", ".join(report["protocol_differences"]))
        lines.extend(report["comparison_issues"])
    return "\n".join(lines) + "\n"
