"""Command line for the Total War: WARHAMMER III battle track."""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from gameai.provenance import REPO_ROOT

LEDGER_PATH = REPO_ROOT / "runs/twwarhammer3/llm-spend.jsonl"
RESULTS_PATH = REPO_ROOT / "docs/twwarhammer3/results.csv"


def add_session_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--speed", type=float, default=1.0, help="battle speed multiplier")
    parser.add_argument("--pause", action="store_true", help="pause the battle while deciding")
    parser.add_argument("--interval-ms", type=int, default=5000,
                        help="battle time between decisions")
    parser.add_argument("--observe-ms", type=int, default=1000,
                        help="battle time between observations")
    parser.add_argument("--tick-ms", type=int, default=250, help="in-game model tick for the mod")
    parser.add_argument("--no-autostart", action="store_true", help="leave deployment to a human")
    parser.add_argument("--no-menu", action="store_true", help="do not drive the frontend menus")


def skip_intro() -> None:
    """Dismiss the intro movies with Escape once the frontend scripts are running."""
    from gameai.windows import desktop

    time.sleep(2)
    for _ in range(3):
        desktop("key", "escape")
        time.sleep(1.5)


def session_from(args: argparse.Namespace) -> dict:
    return {
        "enabled": True, "speed": args.speed, "pause": args.pause,
        "interval_ms": args.interval_ms, "observe_ms": args.observe_ms, "tick_ms": args.tick_ms,
        "autostart": not args.no_autostart, "menu": not args.no_menu,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="twwarhammer3", description="WH3 battles for a policy")
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
            print(json.dumps(record, sort_keys=True))
            mailbox = Mailbox(BRIDGE_DIR, job=job)
            mailbox.reset()
            mailbox.write_session(session_from(args))
            try:
                with OwnedGame(output / "game.log", timeout=args.timeout) as game:
                    print(json.dumps(game.info), flush=True)
                    offsets = {"mod.log": 0, "menu.log": 0}
                    intro_skipped = False
                    while game.process.poll() is None:
                        for name in offsets:
                            text = mailbox.log_since(offsets[name], name)
                            if text:
                                offsets[name] += len(text.encode())
                                print(f"{name}: {text.rstrip()}", flush=True)
                        if offsets["menu.log"] and not intro_skipped:
                            skip_intro()
                            intro_skipped = True
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
        offset = mailbox.log_offset("menu.log")
        mailbox.write_menu(steps)
        deadline = time.monotonic() + args.wait
        while time.monotonic() < deadline:
            text = mailbox.log_since(offset, "menu.log")
            if text:
                offset += len(text.encode())
                print(text.rstrip(), flush=True)
                if text.rstrip().endswith("done"):
                    break
            time.sleep(0.5)
        return 0

    if args.command == "spend":
        from gameai.ledger import Ledger

        print(f"{Ledger(args.ledger, float('inf')).spent:.4f} USD")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
