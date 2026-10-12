"""Command-line entry point."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from spire.fullrun.api import EFFORTS, LEDGER_PATH, PRICES


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
    evaluate = commands.add_parser(
        "evaluate", help="Evaluate a frozen policy on a suite or catalog"
    )
    artifact = evaluate.add_mutually_exclusive_group(required=True)
    artifact.add_argument("--policy", choices=["random", "heuristic"])
    artifact.add_argument("--checkpoint", type=Path, help="Frozen neural policy artifact")
    artifact.add_argument(
        "--language-artifact", type=Path, help="Frozen local language-policy declaration"
    )
    evaluate.add_argument(
        "--suite", type=Path, required=True, help="Schema-1 suite or schema-2 catalog"
    )
    evaluate.add_argument("--output", type=Path, required=True)
    train = commands.add_parser("train", help="Run budgeted, resumable original-engine PPO")
    train.add_argument("--output", type=Path, required=True)
    train.add_argument("--resume", action="store_true", help="Resume with the original budget")
    train.add_argument("--suite", type=Path)
    train.add_argument("--episodes", type=int)
    train.add_argument("--batch-steps", type=int)
    train.add_argument("--updates", type=int)
    train.add_argument("--time-budget", type=float, help="Total wall budget in seconds")
    train.add_argument("--seed", type=int)
    train.add_argument(
        "--learning-rate", type=float, help="PPO Adam learning rate (default: 0.0003)"
    )
    play = commands.add_parser("play", help="Play complete original-engine runs with an API model")
    play.add_argument("--model", required=True, choices=sorted(PRICES))
    play.add_argument("--effort", default="low", choices=EFFORTS)
    play.add_argument("--seed", action="append", dest="seeds", required=True,
                      help="Alphanumeric game seed; repeat for several runs")
    play.add_argument("--budget-usd", type=float, required=True,
                      help="Hard cap on the ledger's total spend, including earlier jobs")
    play.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    play.add_argument("--max-actions", type=int, default=4000)
    play.add_argument("--run-timeout", type=float, default=5 * 3600)
    play.add_argument("--bridge-timeout", type=float, default=300)
    play.add_argument("--output", type=Path, required=True)
    digest = commands.add_parser("digest", help="Summarize a saved full-run job or run")
    digest.add_argument("path", type=Path, help="A job directory, or one of its run-NNNN")
    digest.add_argument("--floor", type=int, help="Show one floor of a run turn by turn")
    spend = commands.add_parser("spend", help="Total the API spend ledger")
    spend.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    args = parser.parse_args()
    if args.command == "doctor":
        from spire.engine.doctor import collect_diagnostics, exit_code, render_diagnostics

        report = collect_diagnostics()
        print(json.dumps(report, indent=2) if args.json else render_diagnostics(report))
        return exit_code(report)
    if args.command == "rollout":
        from spire.combat.rollout import rollout as run_rollout

        config = vars(args).copy()
        output = config.pop("output") or Path("runs") / datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%S.%fZ"
        )
        config.pop("command")
        manifest = run_rollout(output, config)
        print(f"Evidence: {output.resolve()}")
        return 0 if manifest["status"] == "completed" else 1
    if args.command == "report":
        catalog_runs = [
            any((run / name).exists() for name in (
                "catalog.json", "catalog-manifest.json", "catalog-evaluation.json"
            ))
            for run in args.runs
        ]
        if any(catalog_runs):
            if not all(catalog_runs):
                parser.error("Report catalogs and single-scenario runs separately")
            from spire.combat.catalog_report import compare_catalogs, render_catalog_report

            report = compare_catalogs(args.runs)
            rendered = render_catalog_report(report)
        else:
            from spire.combat.report import compare_runs, render_report

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
        try:
            declaration = json.loads(args.suite.read_text())
        except (OSError, ValueError) as error:
            parser.error(f"Cannot read suite: {error}")
        schema = declaration.get("schema_version") if isinstance(declaration, dict) else None
        if type(schema) is not int or schema not in {1, 2}:
            parser.error("Evaluation requires a schema-1 suite or schema-2 catalog")
        if args.language_artifact and schema == 1:
            from spire.language.evaluation import evaluate_language

            result = evaluate_language(args.language_artifact, args.suite, args.output)
            metrics = result["audit"]["metrics"]
            filename = "evaluation.json"
        elif schema == 2:
            from spire.combat.catalog import evaluate_catalog

            result = evaluate_catalog(
                args.policy or ("language" if args.language_artifact else "neural"),
                args.suite, args.output, checkpoint=args.checkpoint,
                **({"language_artifact": args.language_artifact} if args.language_artifact else {}),
            )
            metrics = {"metrics": result["metrics"], "macro": result["macro"]}
            filename = "catalog-evaluation.json"
        else:
            from spire.combat.evaluation import evaluate

            result = evaluate(
                args.policy or "neural", args.suite, args.output, checkpoint=args.checkpoint
            )
            metrics = result["audit"]["metrics"]
            filename = "evaluation.json"
        print(json.dumps(metrics, indent=2))
        print(f"Evaluation: {args.output.resolve() / filename}")
        return 0 if result["valid"] else 1
    if args.command == "train":
        choices = [
            args.suite,
            args.episodes,
            args.batch_steps,
            args.updates,
            args.time_budget,
            args.seed,
            args.learning_rate,
        ]
        if args.resume and any(value is not None for value in choices):
            parser.error("--resume reuses the recorded configuration; omit training overrides")
        if not args.resume and any(value is None for value in choices[:5]):
            parser.error(
                "new training requires --suite, --episodes, --batch-steps, --updates, --time-budget"
            )
        from spire.ppo.training import train

        config = (
            None
            if args.resume
            else {
                "suite_path": str(args.suite),
                "total_episodes": args.episodes,
                "batch_steps": args.batch_steps,
                "max_updates": args.updates,
                "time_budget_seconds": args.time_budget,
                "seed": args.seed or 0,
                "learning_rate": args.learning_rate if args.learning_rate is not None else 3e-4,
            }
        )
        result = train(args.output, config, resume=args.resume)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] in {"completed", "budget_exhausted"} else 1
    if args.command == "play":
        from spire.fullrun.api import Ledger, ResponsesClient, api_key
        from spire.fullrun.llm import LLMPolicy
        from spire.fullrun.play import play as run_play

        config = vars(args).copy()
        output = config.pop("output")
        config.pop("command")
        config["ledger"] = str(config["ledger"])
        ledger = Ledger(args.ledger, args.budget_usd)
        client = ResponsesClient(api_key())
        manifest = run_play(output, config, policy_factory=lambda: LLMPolicy(
            args.model, args.effort, ledger, client=client))
        print(f"Evidence: {output.resolve()}")
        return 0 if manifest["status"] == "completed" else 1
    if args.command == "digest":
        from spire.fullrun.digest import main as run_digest

        run_digest(args.path, args.floor)
        return 0
    if args.command == "spend":
        from spire.fullrun.api import Ledger

        print(f"${Ledger(args.ledger, budget_usd=0).spent:.4f} spent ({args.ledger})")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
