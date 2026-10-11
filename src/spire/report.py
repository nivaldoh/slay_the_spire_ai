"""Compact comparisons generated from audited evidence."""

from pathlib import Path

from spire.evidence import summarize_run


def compare_runs(directories: list[Path]) -> dict:
    runs = [summarize_run(directory) for directory in directories]
    contracts = {
        (run["provenance"]["observation_version"], run["provenance"]["prefix_version"])
        for run in runs
    }
    return {
        "schema_version": 1,
        "valid": all(run["valid"] for run in runs),
        "same_protocol": len(contracts) == 1,
        "scope": "Recorded original-engine combat attempts; no generalization claim",
        "runs": runs,
    }


def render_report(report: dict) -> str:
    lines = [
        "# Combat evidence report",
        "",
        report["scope"],
        "",
        "| Run | Policy | Wins / valid games | Attempts | Mean final HP | Evidence valid |",
        "|---|---|---:|---:|---:|---|",
    ]
    for run in report["runs"]:
        metrics = run["metrics"]
        policy = run["provenance"]["config"]["policy"]
        hp = metrics["mean_ending_hp"]
        hp_text = f"{hp:.2f}" if hp is not None else "—"
        lines.append(
            f"| [{Path(run['directory']).name}]({run['evidence'].get('manifest.json', '')}) "
            f"| {policy} | {metrics['wins']} / {metrics['valid_gameplay_episodes']} "
            f"| {metrics['attempts']} | {hp_text} | {run['valid']} |"
        )
        if run["issues"]:
            lines.extend(["", f"Audit issues: {'; '.join(run['issues'])}"])
    lines.extend(
        [
            "",
            "HP includes engine postcombat healing. Infrastructure failures, unsupported states,",
            "limits, and interruptions remain attempts but do not become gameplay losses.",
        ]
    )
    if not report["same_protocol"]:
        lines.extend(
            [
                "",
                "These runs use different protocols; their scores are not a controlled comparison.",
            ]
        )
    return "\n".join(lines) + "\n"
