"""Command-line entry point."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Slay the Spire experiment tools")
    parser.add_argument("--version", action="version", version="spire-agent 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Inspect local runtime prerequisites")
    doctor.add_argument("--json", action="store_true", help="Emit structured diagnostics")
    rollout = commands.add_parser("rollout", help="Record original-engine first-combat episodes")
    rollout.add_argument("--policy", choices=["random", "heuristic", "end_turn"], default="random")
    rollout.add_argument("--game-seed", default="SPIREAI1")
    rollout.add_argument("--policy-seed", type=int, default=0)
    rollout.add_argument("--episodes", type=int, default=2)
    rollout.add_argument("--max-actions", type=int, default=500)
    rollout.add_argument("--episode-timeout", type=float, default=600)
    rollout.add_argument("--bridge-timeout", type=float, default=90)
    rollout.add_argument("--output", type=Path)
    report = commands.add_parser("report", help="Audit and compare saved combat evidence")
    report.add_argument("runs", type=Path, nargs="+")
    report.add_argument("--output", type=Path, help="Write a .json or Markdown report")
    evaluate = commands.add_parser("evaluate", help="Evaluate a fixed baseline on a frozen suite")
    evaluate.add_argument("--policy", choices=["random", "heuristic"], required=True)
    evaluate.add_argument("--suite", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "doctor":
        from spire.doctor import collect_diagnostics, exit_code, render_diagnostics

        report = collect_diagnostics()
        print(json.dumps(report, indent=2) if args.json else render_diagnostics(report))
        return exit_code(report)
    if args.command == "rollout":
        from spire.rollout import rollout as run_rollout

        config = vars(args).copy()
        output = config.pop("output") or Path("runs") / datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S.%fZ"
        )
        config.pop("command")
        manifest = run_rollout(output, config)
        print(f"Evidence: {output.resolve()}")
        return 0 if manifest["status"] == "completed" else 1
    if args.command == "report":
        from spire.report import compare_runs, render_report

        report = compare_runs(args.runs)
        rendered = render_report(report)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, indent=2) + "\n" if args.output.suffix == ".json" else rendered
            )
        print(rendered)
        return 0 if report["valid"] else 1
    if args.command == "evaluate":
        from spire.evaluation import evaluate

        result = evaluate(args.policy, args.suite, args.output)
        print(json.dumps(result["audit"]["metrics"], indent=2))
        print(f"Evaluation: {args.output.resolve() / 'evaluation.json'}")
        return 0 if result["valid"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
