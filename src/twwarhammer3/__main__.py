"""Command line for the Total War: WARHAMMER III battle track."""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from gameai.provenance import write_json
from gameai.providers import PROVIDERS, get_provider
from twwarhammer3.battle.controllers import BUILTINS, MODEL_POLICIES
from twwarhammer3.battle.llm import LEDGER_PATH, OPENROUTER_LEDGER_PATH
from twwarhammer3.battle.stats import JOBS_ROOT, RESULTS_PATH
from twwarhammer3.battle.watch import STALL_S


def add_session_arguments(parser: argparse.ArgumentParser) -> None:
    """Settings the mod reads from session.json; battles always run unpaused at 1x."""
    parser.set_defaults(speed=1.0, pause=False)
    parser.add_argument("--observe-ms", type=int, default=1000,
                        help="battle time between observations")
    parser.add_argument("--tick-ms", type=int, default=250, help="in-game model tick for the mod")
    parser.add_argument("--record-replay", action=argparse.BooleanOptionalAction, default=True,
                        help="record public replay frames at 1 Hz (default: on)")
    parser.add_argument("--stills", action="store_true",
                        help="capture up to four presentation stills and readable unit names")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="twwarhammer3",
        description="Total War: WARHAMMER III custom battles for scripted and API-model policies",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    doctor = commands.add_parser("doctor", help="Inspect the game and runtime (read-only)")
    doctor.add_argument("--json", action="store_true")

    pack = commands.add_parser("pack", help="Build the mod pack, or list/extract a pack")
    pack.add_argument("--output", type=Path, default=Path("runs/twwarhammer3/twwarhammer3.pack"))
    pack.add_argument("--list", type=Path, metavar="PACK", help="list a pack's entries")
    pack.add_argument("--extract", nargs=2, metavar=("PACK", "NAME"), help="print one entry")

    launch = commands.add_parser("launch", help="Prepare the runtime and run the game until Ctrl-C")
    launch.add_argument("--timeout", type=float, default=4 * 3600,
                        help="seconds before the game is killed")
    launch.add_argument("--output", type=Path, default=None, help="log directory")
    add_session_arguments(launch)

    menu = commands.add_parser("menu", help="Send frontend steps to the game; tail menu.log")
    menu.add_argument("--steps", type=Path, help="JSON file with a list of steps")
    menu.add_argument("--dump", metavar="DEPTH", type=int, help="dump the UI tree to ui_tree.txt")
    menu.add_argument("--find", nargs="+", help="component path for --dump or --click")
    menu.add_argument("--click", action="store_true", help="click the --find component")
    menu.add_argument("--wait", type=float, default=20, help="seconds to tail menu.log")
    menu.add_argument("--battle", action="store_true",
                      help="send the steps to the running battle script (tails mod.log)")

    play = commands.add_parser("play", help="Play custom battles with a policy; one job directory")
    play.add_argument("--policy", default="llm",
                      help=f"{', '.join(sorted(BUILTINS.keys() | MODEL_POLICIES))} or"
                      " package.module:Class; comma-separated names rotate; a model policy"
                      " takes its own model and effort as NAME@MODEL or NAME@MODEL/EFFORT")
    play.add_argument("--provider", default="openai", choices=PROVIDERS,
                      help="API gateway for every model controller in this job")
    play.add_argument("--model", default=None,
                      help="model for policies without @MODEL; default: gpt-6-luna (OpenAI),"
                      " z-ai/glm-5.3 (OpenRouter)")
    play.add_argument("--effort", default="low",
                      help="the reasoning effort of a model policy named without /EFFORT")
    play.add_argument("--budget-usd", type=float, default=None,
                      help=f"required with a model policy: {', '.join(sorted(MODEL_POLICIES))}")
    play.add_argument("--episodes", type=int, default=None,
                      help="default: one trial per controller/delay combination")
    play.add_argument("--rotation-seed", type=int, default=None, help="recorded trial order seed")
    play.add_argument("--delay-seconds", default="0",
                      help="minimum buffered snapshot ages in seconds, e.g. 0,6,10")
    play.add_argument("--scenario", required=True,
                      help="a battle in configs/twwarhammer3/scenarios.json; random entries"
                      " draw a map and every race, and autogenerate the armies")
    play.add_argument("--seed", type=int, default=None, help="the draw of a random scenario")
    add_session_arguments(play)
    play.add_argument("--interval-ms", type=int, default=0,
                      help="optional battle-time wait after orders apply (default: none)")
    play.add_argument("--start-timeout", type=float, default=900)
    play.add_argument("--observation-timeout", type=float, default=60)
    play.add_argument("--episode-timeout", type=float, default=None,
                      help="wall limit per episode (default: a benchmark's game timer + 120 s,"
                      " else 3900)")
    play.add_argument("--run-timeout", type=float, default=None,
                      help="game process limit (default: 8 h, or setup plus every episode"
                      " timeout + 60 s if longer)")
    play.add_argument("--attach", action="store_true", help="use the game a launch started")
    play.add_argument("--show", action="store_true",
                      help="show each model reply in the game's advisor window")
    play.add_argument("--output", type=Path, required=True)

    digest = commands.add_parser("digest", help="Summarise a job or one episode's trace")
    digest.add_argument("path", type=Path, help="job directory or job/episode-NNNN")
    digest.add_argument("--at", type=float, metavar="SECONDS",
                        help="with an episode: the decision nearest this battle time in full")
    digest.add_argument("--units", action="store_true",
                        help="per episode: each unit's men, ammunition, first melee and rout, "
                             "and the engine's refusals")

    watch = commands.add_parser("watch", help="Follow a job live: model inputs and outputs")
    watch.add_argument("path", type=Path, nargs="?",
                       help="job or episode directory (default: the job in session.json); "
                            "--next needs the job directory")
    watch.add_argument("--prompts", action="store_true", help="print every prompt in full")
    watch.add_argument("--next", action="store_true",
                       help="wait for the next episode result, stall or job end; print it and exit")
    watch.add_argument("--stall-minutes", type=float, default=STALL_S / 60,
                       help="with --next: report a stall after this long without new evidence")

    card = commands.add_parser(
        "card", help="A tactic card's board; with jobs or plan directories, its verdict")
    card.add_argument("name", help="card name, e.g. chariot")
    card.add_argument("paths", nargs="*", type=Path, metavar="JOB_OR_PLAN_DIR")

    stats = commands.add_parser("stats", help="Summarise the results register")
    stats.add_argument("--results", type=Path, default=RESULTS_PATH)

    report = commands.add_parser(
        "report", help="Paired benchmark report of jobs: print it, save text, JSON and HTML")
    report.add_argument("jobs", nargs="*", type=Path, metavar="JOB", help="job directory")
    report.add_argument("--jobs-file", type=Path,
                        help="JSON list of job paths, relative to the working directory")
    report.add_argument("--output", type=Path, required=True, metavar="STEM",
                        help="writes STEM.txt, STEM.json and the offline field report STEM.html")

    export = commands.add_parser("export", help="Export saved model decisions for post-training")
    export.add_argument("paths", nargs="*", type=Path, metavar="JOB_OR_EPISODE")
    export.add_argument("--jobs-file", type=Path, help="JSON list of job or episode paths")
    export.add_argument("--output", type=Path, required=True, help="new directory outside the jobs")
    export.add_argument("--prompt-version", action="append", default=[],
                        help="keep this version (e.g. v20 or unknown); repeatable")
    export.add_argument("--model", action="append", default=[], help="keep this model; repeatable")
    export.add_argument("--prompt-sha256", action="append", default=[],
                        help="keep this exact system prompt hash; repeatable")

    spend = commands.add_parser("spend", help="Print the API ledger total")
    spend.add_argument("--provider", default="openai", choices=PROVIDERS)
    spend.add_argument("--ledger", type=Path, default=None, help="override the provider's ledger")

    args = parser.parse_args()

    if args.command == "export":
        from twwarhammer3.battle.export import export_traces

        try:
            paths = list(args.paths)
            if args.jobs_file:
                names = json.loads(args.jobs_file.read_text())
                if not isinstance(names, list) or any(not isinstance(p, str) for p in names):
                    raise ValueError("--jobs-file must contain a JSON list of paths")
                paths += [Path(name) for name in names]
            summary = export_traces(paths, args.output,
                                    prompt_versions=tuple(args.prompt_version),
                                    models=tuple(args.model),
                                    prompt_hashes=tuple(args.prompt_sha256))
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(json.dumps({"output": str(args.output), "counts": summary["counts"],
                          "issues": summary["issues"]}, sort_keys=True))
        return 0

    if args.command == "doctor":
        from twwarhammer3.engine.doctor import collect_diagnostics, render_diagnostics

        report = collect_diagnostics()
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(render_diagnostics(report))
        return 0 if report["status"] == "ready" else 1

    if args.command == "pack":
        from twwarhammer3.engine import pack as packs
        from twwarhammer3.engine.runtime import mod_files

        if args.list:
            for name, _, size, compressed in packs.read_index(args.list):
                print(f"{size:>10} {'z' if compressed else ' '} {name}")
            return 0
        if args.extract:
            sys.stdout.buffer.write(packs.extract(Path(args.extract[0]), args.extract[1]))
            return 0
        files = mod_files()
        packs.write_pack(args.output, files)
        print(f"{args.output}: {len(files)} files")
        return 0

    if args.command == "launch":
        from twwarhammer3.battle.capture import PassiveCapture
        from twwarhammer3.battle.play import session
        from twwarhammer3.engine.mailbox import Mailbox
        from twwarhammer3.engine.runtime import BRIDGE_DIR, OwnedGame, RuntimeLock, prepare_runtime

        job = f"launch-{datetime.now():%Y%m%d-%H%M%S}"
        output = args.output or Path("runs/twwarhammer3") / job
        output.mkdir(parents=True, exist_ok=True)
        with RuntimeLock():
            record = prepare_runtime()
            write_json(output / "deployment.json", record)
            print(json.dumps(record, sort_keys=True))
            mailbox = Mailbox(BRIDGE_DIR, job=job)
            mailbox.reset()
            try:
                with (mailbox.owned_session(session(vars(args))),
                      OwnedGame(output / "game.log", timeout=args.timeout) as game,
                      PassiveCapture(BRIDGE_DIR, job=job, pid=game.info.get("pid", 0),
                                     enabled=args.stills)):
                    print(json.dumps(game.info), flush=True)
                    offsets = {"mod.log": 0, "menu.log": 0}
                    while game.process.poll() is None:
                        for name in offsets:
                            text = mailbox.log_since(offsets[name], name)
                            if text:
                                offsets[name] += len(text.encode())
                                print(f"{name}: {text.rstrip()}", flush=True)
                        time.sleep(1)
                    print("game exited", flush=True)
            except KeyboardInterrupt:
                print("stopping", flush=True)
        return 0

    if args.command == "menu":
        from twwarhammer3.engine.mailbox import Mailbox
        from twwarhammer3.engine.runtime import BRIDGE_DIR

        if not (BRIDGE_DIR / "session.json").exists():
            parser.error("menu needs an active launch session")
        live = json.loads((BRIDGE_DIR / "session.json").read_text())
        mailbox = Mailbox(BRIDGE_DIR, job=live["job"])
        if args.steps:
            steps = json.loads(args.steps.read_text())
        elif args.dump is not None:
            steps = [{"dump": "ui_tree.txt", "depth": args.dump}]
            if args.find:
                steps[0]["find"] = args.find
        elif args.find:
            steps = [{"find": args.find, "click": args.click}]
        else:
            parser.error("menu needs --steps, --dump or --find")
        # The battle script runs menu.json steps too (the frontend is unloaded in battle).
        log = "mod.log" if args.battle else "menu.log"
        offset = mailbox.log_offset(log)
        request = mailbox.write_menu(steps)
        deadline = time.monotonic() + args.wait
        while time.monotonic() < deadline:
            text = mailbox.log_since(offset, log)
            if text:
                offset += len(text.encode())
                print(text.rstrip(), flush=True)
                lines = text.splitlines()
                if any(line.endswith(f"menu {request}: failed") for line in lines):
                    return 1
                if any(line.endswith(f"menu {request}: done") for line in lines):
                    return 0
            time.sleep(0.5)
        print("menu request timed out before completion", file=sys.stderr)
        return 1

    if args.command == "play":
        from twwarhammer3.battle.controllers import factories, rotation
        from twwarhammer3.battle.play import play as run_play

        config = {key: value for key, value in vars(args).items()
                  if key not in ("command", "output")}
        config["model"] = args.model or next(iter(get_provider(args.provider).prices))
        ledger = OPENROUTER_LEDGER_PATH if args.provider == "openrouter" else LEDGER_PATH
        config.update(ledger=str(ledger), results=str(RESULTS_PATH))
        try:
            rotation(config)
            makers = factories(config)
        except (ValueError, ImportError, AttributeError, FileNotFoundError) as exc:
            parser.error(str(exc))
        manifest = run_play(args.output, config, makers=makers)
        return 0 if manifest["status"] == "completed" else 1

    if args.command == "digest":
        from twwarhammer3.battle.digest import decision_at, digest, units_digest

        if args.units:
            print(units_digest(args.path))
        elif args.at is None:
            print(digest(args.path))
        elif (args.path / "trace.jsonl").exists():
            print(decision_at(args.path, args.at))
        else:
            parser.error("--at needs an episode directory")
        return 0

    if args.command == "watch":
        from twwarhammer3.battle.watch import follow, next_event
        from twwarhammer3.engine.runtime import BRIDGE_DIR

        if args.next:  # the job directory may not exist yet beside a starting play
            if args.path is None or args.path.name.startswith("episode-"):
                parser.error("--next needs the job directory")
            print(next_event(args.path, args.stall_minutes * 60))
            return 0
        path = args.path or JOBS_ROOT / json.loads(
            (BRIDGE_DIR / "session.json").read_text())["job"]
        if not path.is_dir():
            parser.error(f"no job or episode directory at {path}")
        print(f"following {path}", flush=True)
        try:
            follow(path, args.prompts)
        except KeyboardInterrupt:
            pass
        return 0

    if args.command == "card":
        from twwarhammer3.battle.cards import CARDS, board

        if args.name not in CARDS:
            parser.error(f"unknown card {args.name!r}; cards: {', '.join(sorted(CARDS))}")
        print(board(args.name, args.paths or None))
        return 0

    if args.command == "stats":
        from twwarhammer3.battle.stats import summary

        print(summary(args.results))
        return 0

    if args.command == "report":
        from twwarhammer3.battle.report import collect, render
        from twwarhammer3.battle.report_html import write

        jobs = list(args.jobs)
        if args.jobs_file:
            try:
                listed = json.loads(args.jobs_file.read_text())
            except (OSError, ValueError) as exc:
                parser.error(f"cannot read --jobs-file: {exc}")
            if not isinstance(listed, list) or any(not isinstance(p, str) or not p for p in listed):
                parser.error("--jobs-file must contain a JSON list of job paths")
            jobs.extend(Path(path) for path in listed)
        if not jobs:
            parser.error("report needs JOB directories or --jobs-file")
        data = collect(jobs)
        text = render(data)
        stem = args.output
        stem.parent.mkdir(parents=True, exist_ok=True)
        write(stem.with_name(stem.name + ".html"), data)  # first: it may need Pillow
        write_json(stem.with_name(stem.name + ".json"), data)
        stem.with_name(stem.name + ".txt").write_text(text + "\n")
        print(text)
        return 0

    if args.command == "spend":
        from gameai.ledger import Ledger

        path = args.ledger or (OPENROUTER_LEDGER_PATH if args.provider == "openrouter"
                               else LEDGER_PATH)
        print(f"${Ledger(path, budget_usd=0).spent:.4f} spent ({path})")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
