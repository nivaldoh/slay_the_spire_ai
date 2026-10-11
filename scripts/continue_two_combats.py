"""Bounded canonical two-combat continuation and read-only saved-run audit."""

import argparse
import json
from pathlib import Path

from spire.continuation import audit_continuation, run_continuation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--second-policy", choices=("heuristic", "end_turn"), default="heuristic")
    run.add_argument("--time-budget", type=float, default=240)
    run.add_argument("--max-actions", type=int, default=500)
    run.add_argument("--bridge-timeout", type=float, default=45)
    audit = commands.add_parser("audit")
    audit.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.command == "audit":
        report = audit_continuation(args.directory)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["valid"] else 1
    report = run_continuation(
        args.output,
        second_policy=args.second_policy,
        time_budget=args.time_budget,
        max_actions=args.max_actions,
        bridge_timeout=args.bridge_timeout,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return (
        0
        if report["audit"]["valid"]
        and not report["result"].get("cleanup_error")
        and report["result"]["status"]
        in {
            "completed_segment",
            "lost",
        }
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
