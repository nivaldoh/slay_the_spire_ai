"""Slay the Spire command line."""

import argparse
import json
from pathlib import Path

from gameai.providers import PROVIDERS, validate
from spire.fullrun.llm import LEDGERS
from spire.fullrun.stats import RESULTS_PATH


def _seed(text: str) -> str:
    # The seed goes into CommunicationMod's START command.
    if not text.isalnum():
        raise argparse.ArgumentTypeError("seeds are alphanumeric")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="spire", description="Slay the Spire 1: full runs and the first-combat benchmark"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Inspect the game, mods and runtime (read-only)")
    doctor.add_argument("--json", action="store_true", help="Emit structured diagnostics")
    rollout = commands.add_parser("rollout", help="First combat: record seeded episodes")
    rollout.add_argument("--policy", choices=["random", "heuristic", "end_turn"], default="random")
    rollout.add_argument("--game-seed", default="SPIREAI1")
    rollout.add_argument("--policy-seed", type=int, default=0)
    rollout.add_argument("--episodes", type=int, default=2)
    rollout.add_argument("--max-actions", type=int, default=500)
    rollout.add_argument("--episode-timeout", type=float, default=600)
    rollout.add_argument("--bridge-timeout", type=float, default=90)
    rollout.add_argument("--output", type=Path, required=True)
    report = commands.add_parser("report", help="First combat: audit and compare saved evidence")
    report.add_argument("runs", type=Path, nargs="+")
    report.add_argument("--output", type=Path, help="Write a .json or Markdown report")
    evaluate = commands.add_parser(
        "evaluate", help="First combat: evaluate a frozen policy on a suite or catalog"
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
    train = commands.add_parser("train", help="First combat: budgeted, resumable PPO training")
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
    play = commands.add_parser("play", help="Full runs: play complete runs with an API model")
    play.add_argument("--provider", default="openai", choices=PROVIDERS)
    play.add_argument("--model", required=True,
                      choices=sorted({m for p in PROVIDERS.values() for m in p.prices}))
    play.add_argument("--effort", default="low",
                      choices=sorted({e for p in PROVIDERS.values() for v in p.efforts.values()
                                      for e in v}))
    play.add_argument("--seed", type=_seed, action="append", dest="seeds", required=True,
                      help="Alphanumeric game seed; repeat for several runs")
    play.add_argument("--budget-usd", type=float, required=True,
                      help="Hard cap on the ledger's total spend, including earlier jobs")
    play.add_argument("--ledger", type=Path, help="override the provider's ledger")
    play.add_argument("--results", type=Path, default=RESULTS_PATH,
                      help="Results register that gets one row per run")
    play.add_argument("--max-actions", type=int, default=4000)
    play.add_argument("--run-timeout", type=float, default=5 * 3600)
    play.add_argument("--bridge-timeout", type=float, default=300)
    play.add_argument("--output", type=Path, required=True)
    digest = commands.add_parser("digest", help="Full runs: summarize a saved job or run")
    digest.add_argument("path", type=Path, help="A job directory, or one of its run-NNNN")
    digest.add_argument("--floor", type=int, help="Show one floor of a run turn by turn")
    digest.add_argument("--picks", action="store_true",
                        help="List a run's noncombat choices and reasons under each floor")
    watch = commands.add_parser("watch", help="Full runs: wait for a job's next run, stall or end")
    watch.add_argument("job", type=Path, help="A job directory under runs/fullrun")
    spend = commands.add_parser("spend", help="Full runs: total the API spend ledger")
    spend.add_argument("--provider", default="openai", choices=PROVIDERS)
    spend.add_argument("--ledger", type=Path, help="override the provider's ledger")
    export = commands.add_parser("export", help="Full runs: export saved model requests")
    export.add_argument("paths", nargs="+", type=Path, metavar="JOB_OR_RUN")
    export.add_argument("--output", type=Path, required=True,
                        help="new directory outside the jobs, e.g. runs/fullrun-exports/<name>")
    export.add_argument("--model", action="append", default=[], help="keep this model; repeatable")
    export.add_argument("--provider", action="append", default=[],
                        help="keep this provider; repeatable")
    export.add_argument("--prompt-sha256", action="append", default=[],
                        help="keep this exact system prompt hash; repeatable")
    stats = commands.add_parser("stats", help="Full runs: milestones from the results register")
    stats.add_argument("--rebuild", action="store_true",
                       help="Rewrite the register from every job under runs/fullrun")
    stats.add_argument("--results", type=Path, default=RESULTS_PATH)
    args = parser.parse_args()
    if args.command == "doctor":
        from spire.engine.doctor import collect_diagnostics, render_diagnostics

        report = collect_diagnostics()
        print(json.dumps(report, indent=2) if args.json else render_diagnostics(report))
        return 1 if report["blockers"] else 0
    if args.command == "rollout":
        from spire.combat.rollout import rollout as run_rollout

        config = vars(args).copy()
        output = config.pop("output")
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
        from functools import partial

        from gameai.ledger import Ledger
        from gameai.llm import api_key, post
        from spire.fullrun.llm import LLMPolicy
        from spire.fullrun.play import play as run_play

        try:
            validate(args.provider, args.model, args.effort)
        except ValueError as error:
            parser.error(str(error))
        config = vars(args).copy()
        output = config.pop("output")
        config.pop("command")
        config["ledger"] = str(args.ledger or LEDGERS[args.provider])
        config["results"] = str(config["results"])
        try:
            ledger = Ledger(Path(config["ledger"]), args.budget_usd, must_exist=True)
        except FileNotFoundError as error:
            parser.error(str(error))
        # A missing key fails here, before any launch.
        send = partial(post, api_key(args.provider), provider=args.provider,
                       record_transport=True)
        manifest = run_play(output, config, policy_factory=lambda: LLMPolicy(
            args.model, args.effort, ledger, send=send, provider=args.provider))
        print(f"Evidence: {output.resolve()}")
        return 0 if manifest["status"] == "completed" else 1
    if args.command == "digest":
        from spire.fullrun.digest import main as run_digest

        run_digest(args.path, args.floor, args.picks)
        return 0
    if args.command == "watch":
        from spire.fullrun.watch import next_event

        print(next_event(args.job))
        return 0
    if args.command == "spend":
        from gameai.ledger import Ledger

        path = args.ledger or LEDGERS[args.provider]
        print(f"${Ledger(path, budget_usd=0).spent:.4f} spent ({path})")
        return 0
    if args.command == "export":
        from spire.fullrun.export import export_runs

        try:
            summary = export_runs(args.paths, args.output, models=tuple(args.model),
                                  providers=tuple(args.provider),
                                  prompt_hashes=tuple(args.prompt_sha256))
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(json.dumps({"output": str(args.output), "counts": summary["counts"],
                          "issues": summary["issues"]}, sort_keys=True))
        return 0
    if args.command == "stats":
        from spire.fullrun.stats import JOBS_ROOT, rebuild, summary

        if args.rebuild:
            rebuild(JOBS_ROOT, args.results)
        print(summary(args.results))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
