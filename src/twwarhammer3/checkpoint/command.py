"""Dispatch the checkpoint RL phases, keeping game and model execution separate."""

import json
import sys
from pathlib import Path


def run(args) -> int:
    """Game phases (checkpoint, audit, confirm's launch) hold the GPU lease, so no model
    process starts beside them; model phases refuse while the game runs."""
    import subprocess

    from gameai.lm import gpu_lease
    from twwarhammer3.checkpoint import audit, checkpoint, confirm, rl

    phase, paths = args.phase, [path.resolve() for path in args.paths]
    if args.output:
        args.output = args.output.resolve()
    if args.tasks:
        args.tasks = args.tasks.resolve()
    plan = json.loads(paths[0].read_text()) if phase in (
        "checkpoint", "audit", "tasks", "train", "confirm", "confirm-score") else None
    if phase == "checkpoint":
        with gpu_lease(rl.GPU_LOCK_PATH):
            result = checkpoint.checkpoint_root(plan, Path(plan["library"]))
        print(json.dumps({"status": result["attempt"]["status"],
                          "records": [r["tick"] for r in result["records"]]}))
    elif phase == "audit":
        with gpu_lease(rl.GPU_LOCK_PATH):
            result = audit.audit(plan, args.output)
        print(json.dumps({"pass": result["pass"]}))
    elif phase == "tasks":
        value = rl.build_tasks(plan)
        rl.write_task_set(args.output, value)
        print(f"{args.output}: {len(value['tasks'])} tasks, {value['hash'][:12]}")
    elif phase == "measure":
        print(json.dumps(rl.measure(paths[0], args.output), indent=1))
    elif phase == "train":
        print(json.dumps(rl.train(plan, args.output), indent=1))
    elif phase == "evaluate":
        value = rl.evaluate(paths[0], paths[1])
        print("\n".join(rl.report_lines(value)))
    elif phase == "compare":
        print(rl.compare(paths, args.split))
    elif phase == "confirm-score":
        result = confirm.score(plan, args.output)
        print(json.dumps({"pass": result["pass"], "checks": result["checks"]}))
        return 0 if result["pass"] else 1
    elif phase == "confirm":
        # The model scores in its own process, which exits before the game starts.
        scored = subprocess.run([sys.executable, "-m", "twwarhammer3", "rl", "confirm-score",
                                 str(paths[0]), "--output", str(args.output)])
        if scored.returncode:
            return scored.returncode
        result = confirm.launch(plan, args.output)
        print(json.dumps({"pass": result["pass"], "clauses": result["clauses"]}))
        return 0 if result["pass"] else 1
    elif phase == "recount":
        result = rl.recount(paths[0], args.tasks)
        print("\n".join(result["lines"]))
        print(json.dumps({"pass": result["pass"], "checks": result["checks"]}))
        return 0 if result["pass"] else 1
    return 0
