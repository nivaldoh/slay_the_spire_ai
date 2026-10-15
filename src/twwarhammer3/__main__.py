"""Command line for the Total War: WARHAMMER III battle track."""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from gameai.llm import EFFORTS, PRICES
from gameai.provenance import write_json
from twwarhammer3.battle.llm import LEDGER_PATH
from twwarhammer3.battle.stats import JOBS_ROOT, RESULTS_PATH


def add_session_arguments(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(speed=1.0, pause=False)
    parser.add_argument("--interval-ms", type=int, default=0,
                        help="optional battle-time wait after orders apply (default: none)")
    parser.add_argument("--observe-ms", type=int, default=1000,
                        help="battle time between observations")
    parser.add_argument("--tick-ms", type=int, default=250, help="in-game model tick for the mod")
    parser.add_argument("--no-autostart", action="store_true", help="leave deployment to a human")
    parser.add_argument("--no-menu", action="store_true", help="do not drive the frontend menus")
    parser.add_argument("--record-replay", action="store_true",
                        help="record public replay frames at 1 Hz (cost probe pending)")


def session_from(args: argparse.Namespace) -> dict:
    return {
        "enabled": True, "speed": args.speed, "pause": args.pause,
        "interval_ms": args.interval_ms, "observe_ms": args.observe_ms, "tick_ms": args.tick_ms,
        "autostart": not args.no_autostart, "menu": not args.no_menu,
        "record_replay": args.record_replay,
    }


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
                      help="built-in name or package.module:Class; comma-separated names rotate")
    play.add_argument("--model", default="gpt-6-luna", choices=sorted(PRICES))
    play.add_argument("--effort", default="low", choices=EFFORTS)
    play.add_argument("--budget-usd", type=float, default=None,
                      help="required with a model policy: llm, llm_rules or commander")
    play.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    play.add_argument("--results", type=Path, default=RESULTS_PATH)
    play.add_argument("--episodes", type=int, default=None,
                      help="default: one trial per controller/delay combination")
    play.add_argument("--rotation-seed", type=int, default=None, help="recorded trial order seed")
    play.add_argument("--delay-seconds", default="0",
                      help="minimum buffered snapshot ages in seconds, e.g. 0,6,10")
    play.add_argument("--scenario", required=True,
                      help="a battle in configs/twwarhammer3/scenarios.json; random draws a map"
                      " and both races, and autogenerates both armies")
    play.add_argument("--seed", type=int, default=None, help="the draw of --scenario random")
    add_session_arguments(play)
    play.add_argument("--start-timeout", type=float, default=900)
    play.add_argument("--observation-timeout", type=float, default=60)
    play.add_argument("--episode-timeout", type=float, default=3900,
                      help="wall limit; benchmark runs require at least game timer + 120 s")
    play.add_argument("--run-timeout", type=float, default=8 * 3600, help="game process limit")
    play.add_argument("--attach", action="store_true", help="use the game a launch started")
    play.add_argument("--show", action="store_true",
                      help="show each model reply in the game's advisor window")
    play.add_argument("--output", type=Path, required=True)

    digest = commands.add_parser("digest", help="Summarise a job or one episode's trace")
    digest.add_argument("path", type=Path, help="job directory or job/episode-NNNN")

    watch = commands.add_parser("watch", help="Follow a job live: model inputs and outputs")
    watch.add_argument("path", type=Path, nargs="?",
                       help="job or episode directory (default: the job in session.json)")
    watch.add_argument("--prompts", action="store_true", help="print every prompt in full")

    stats = commands.add_parser("stats", help="Summarise the results register")
    stats.add_argument("--results", type=Path, default=RESULTS_PATH)
    stats.add_argument("--rebuild", action="store_true", help="rewrite it from runs/")
    stats.add_argument("--report", nargs="+", type=Path, metavar="JOB",
                       help="paired benchmark report from these job directories")
    stats.add_argument("--report-json", type=Path,
                       help="save full benchmark metrics and trial list")
    stats.add_argument("--report-html", type=Path,
                       help="save a self-contained offline benchmark field report")

    spend = commands.add_parser("spend", help="Print the API ledger total")
    spend.add_argument("--ledger", type=Path, default=LEDGER_PATH)

    args = parser.parse_args()

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
            mailbox.write_session(session_from(args))
            try:
                with OwnedGame(output / "game.log", timeout=args.timeout) as game:
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

        session = json.loads((BRIDGE_DIR / "session.json").read_text())
        mailbox = Mailbox(BRIDGE_DIR, job=session["job"])
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
        mailbox.write_menu(steps)
        deadline = time.monotonic() + args.wait
        while time.monotonic() < deadline:
            text = mailbox.log_since(offset, log)
            if text:
                offset += len(text.encode())
                print(text.rstrip(), flush=True)
                if text.rstrip().endswith("done") or f"ui {len(steps)}:" in text:
                    break
            time.sleep(0.5)
        return 0

    if args.command == "play":
        from twwarhammer3.battle.play import play as run_play

        skipped = ("command", "output")
        config = {key: value for key, value in vars(args).items() if key not in skipped}
        config.update(session_from(args))
        for key, value in config.items():
            if isinstance(value, Path):
                config[key] = str(value)
        from twwarhammer3.battle.controllers import factories, rotation

        try:
            rotation(config)
            makers = factories(config)
        except (ValueError, ImportError, AttributeError) as exc:
            parser.error(str(exc))
        manifest = run_play(args.output, config, policy_factory=makers)
        return 0 if manifest["status"] == "completed" else 1

    if args.command == "digest":
        from twwarhammer3.battle.digest import digest as render

        print(render(args.path))
        return 0

    if args.command == "watch":
        from twwarhammer3.battle.watch import follow
        from twwarhammer3.engine.runtime import BRIDGE_DIR

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

    if args.command == "stats":
        from twwarhammer3.battle.stats import rebuild, summary

        if args.report:
            from twwarhammer3.battle.report import collect, render

            report = collect(args.report)
            if args.report_json:
                write_json(args.report_json, report)
            if args.report_html:
                from twwarhammer3.battle.report_html import write

                write(args.report_html, report)
            print(render(report))
            return 0
        if args.report_json:
            parser.error("--report-json requires --report JOB...")
        if args.report_html:
            parser.error("--report-html requires --report JOB...")
        if args.rebuild:
            print(f"{rebuild(JOBS_ROOT, args.results)} rows")
        print(summary(args.results))
        return 0

    if args.command == "spend":
        from gameai.ledger import Ledger

        print(f"${Ledger(args.ledger, budget_usd=0).spent:.4f} spent ({args.ledger})")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
