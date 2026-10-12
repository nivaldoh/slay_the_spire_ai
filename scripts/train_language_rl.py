"""Run one declared outcome-based language post-training job, or audit a finished one.

Launch from a clean committed checkout with the CUDA interpreter, under an outer
process limit; the job owns the GPU lease and launches every game itself:

    PYTHONPATH="$PWD/src" timeout --signal=INT --kill-after=30s 4200 \
        /path/to/cuda-env/bin/python scripts/train_language_rl.py \
        --config /absolute/rl-config.json --output /absolute/runs/language-rl

    PYTHONPATH="$PWD/src" /path/to/cuda-env/bin/python scripts/train_language_rl.py \
        --audit /absolute/runs/language-rl
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", type=Path)
    group.add_argument("--audit", type=Path, help="Read-only recheck of a stopped job")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    from spire.language.rl import audit_language_rl, train_language_rl

    if args.audit:
        report = audit_language_rl(args.audit)
        print(json.dumps(report, indent=2))
        return 0 if report["valid"] else 1
    if args.output is None:
        parser.error("--config requires --output")
    summary = train_language_rl(args.output, json.loads(args.config.read_text()))
    print(json.dumps({k: v for k, v in summary.items() if k != "iterations"}, indent=2))
    return 0 if summary["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
