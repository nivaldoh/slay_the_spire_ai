"""One training cycle: sampled runs, updates, then greedy evaluation on fixed seeds."""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import numpy as np
import torch

from gameai.provenance import write_json
from spire.localrl import learn
from spire.localrl.collect import SCORED, Game, play_seeds
from spire.localrl.policy import Scorer

DEFAULTS = {
    "method": "ppo", "temperature": 1.0, "updates": 2, "runs_per_update": 6, "lr": 3e-5,
    "epochs": 3, "minibatch": 4, "clip": 0.2, "entropy": 0.005, "target_kl": 0.03,
    "max_grad_norm": 1.0, "gamma": 0.995, "lam": 0.95, "hp_weight": 3.0, "win_bonus": 10.0,
    "beta": 3.0, "weight_cap": 8.0, "awr_rows": 2000, "offline_share": 0.5,
    "fight_hp": 30.0, "fight_death": 2.0, "fight_potion": 0.1, "fight_lam": 0.9,
}


def read_run(directory: Path) -> dict | None:
    """Steps and the outcome of one finished run, or None when it was not played."""
    path = directory / "steps.jsonl"
    result = json.loads((directory / "result.json").read_text())
    if not path.exists() or result["status"] not in SCORED:
        return None
    steps = [json.loads(line) for line in path.read_text().splitlines()]
    if not steps:
        return None
    return {"steps": steps, "status": result["status"], "floor": result.get("floor") or 0}


def read_offline(path: Path) -> list[dict]:
    """Recorded runs in the same shape, grouped by seed."""
    runs: dict[str, dict] = {}
    for line in path.read_text().splitlines():
        row = json.loads(line)
        # A run that ended in an infrastructure failure did not die: bootstrap, as a truncation.
        status = row["status"] if row["status"] in SCORED else "truncated"
        run = runs.setdefault(row["group"], {"steps": [], "status": status,
                                             "floor": row["final_floor"], "offline": True})
        row["allowed"] = list(range(row["count"]))
        run["steps"].append(row)
    return list(runs.values())


def score_runs(runs: list[dict], config: dict) -> dict:
    """Returns and advantages under this config, baseline fitted on every run given."""
    baseline, rows, targets = learn.Baseline(), [], []
    for run in runs:
        run["rewards"] = learn.rewards(run["steps"], run["status"], run["floor"], config)
        run["features"] = [learn.features(s["observation"]) for s in run["steps"]]
        rows += run["features"]
        targets += learn.discounted(run["rewards"], config["gamma"])
    r2 = baseline.fit(rows, targets)
    spread = []
    for run in runs:
        estimates = baseline(run["features"])
        terminal = run["status"] != "truncated"
        for step, value in zip(run["steps"], learn.advantages(run["rewards"], estimates, config,
                                                              terminal=terminal)):
            step["advantage"] = value
            spread.append(value)
    return {"baseline_r2": r2, "advantage_sd": float(np.std(spread)), "rows": len(rows)}


def score_fights(runs: list[dict], config: dict) -> dict:
    """Give fight steps an advantage from ``learn.fight_rewards`` and normalise each kind apart.

    Runs on after ``score_runs``. Fight steps and the rest then enter one update on one scale.
    """
    baseline, rows, targets, spans = learn.Baseline(), [], [], []
    for run in runs:
        for start, end in learn.fight_spans(run["steps"]):
            values = learn.fight_rewards(run["steps"], start, end, run["status"], config)
            features = [learn.features(s["observation"]) for s in run["steps"][start:end]]
            rows += features
            targets += learn.discounted(values, 1.0)
            spans.append((run, start, end, values, features))
    r2 = baseline.fit(rows, targets)
    fight, other = [], []
    for run, start, end, values, features in spans:
        steps = run["steps"][start:end]
        ended = end < len(run["steps"]) or run["status"] != "truncated"
        found = learn.advantages(values, baseline(features),
                                 {"gamma": 1.0, "lam": config["fight_lam"]}, terminal=ended)
        for step, value in zip(steps, found):
            step["advantage"] = value
            step["in_fight"] = True
        fight += steps
    other = [s for run in runs for s in run["steps"] if not s.get("in_fight")]
    for group in (fight, other):
        if group:
            spread = np.array([s["advantage"] for s in group])
            center, scale = spread.mean(), spread.std() + 1e-6
            for step in group:
                step["advantage"] = float((step["advantage"] - center) / scale)
    return {"fight_baseline_r2": r2, "fight_steps": len(fight), "other_steps": len(other)}


def awr_rows(runs: list[dict], config: dict, generator) -> list[dict]:
    """A sample of every run so far, ``offline_share`` of it recorded, weighted by advantage."""
    offline = [s for run in runs if run.get("offline") for s in run["steps"]]
    online = [s for run in runs if not run.get("offline") for s in run["steps"]]
    wanted = config["awr_rows"]
    take = min(len(offline), int(wanted * config["offline_share"])) if online else min(
        len(offline), wanted)
    chosen = generator.sample(offline, take)
    left = wanted - take
    chosen += generator.sample(online, min(len(online), left))
    weights = np.minimum(np.exp(np.array([s["advantage"] for s in chosen]) / config["beta"]),
                         config["weight_cap"])
    for step, weight in zip(chosen, weights / weights.mean()):
        step["weight"] = float(weight)
    return chosen


def cycle(game: Game, scorer: Scorer, config: dict, offline: list[dict]) -> dict:
    """Sampled runs and updates from the model's current weights, then greedy evaluation."""
    output = Path(config["output"])
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "config.json", config)
    model = scorer.model
    parameters = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=config["lr"], weight_decay=0.0)
    generator = random.Random(config["seed"])
    earlier = [run for path in config["earlier_runs"] if (run := read_run(Path(path)))]
    seeds = list(config["train_seeds"])
    summary: dict = {"updates": [], "started": time.time()}
    for update in range(config["updates"]):
        chunk, seeds = seeds[:config["runs_per_update"]], seeds[config["runs_per_update"]:]
        directory = output / f"update-{update:02d}"
        results = play_seeds(game, directory, chunk, scorer, temperature=config["temperature"],
                             label=f"train-{update}",
                             seed_offset=config["seed"] * 1000 + update * 100) if chunk else []
        fresh = [run for item in results if (run := read_run(Path(item["directory"])))]
        record: dict = {"update": update, "floors": [r["floor"] for r in results],
                        "statuses": [r["status"] for r in results],
                        "decisions": sum(r["decisions"] or 0 for r in results)}
        pool = [*offline, *earlier, *fresh]
        record["score"] = score_runs(pool, config)
        started = time.time()
        if config["method"] == "ppo":
            steps = [step for run in fresh for step in run["steps"]]
            record["learn"] = learn.ppo_update(scorer, optimizer, steps, config,
                                               seed=config["seed"] + update)
        else:
            rows = awr_rows(pool, config, generator)
            record["learn"] = {"history": learn.warm_start(scorer, optimizer, rows, config,
                                                           seed=config["seed"] + update)}
        record["learn_seconds"] = time.time() - started
        earlier += fresh
        model.save_pretrained(directory / "adapter")
        record["adapter"] = str(directory / "adapter")
        summary["updates"].append(record)
        write_json(output / "summary.json", summary)
        print(json.dumps({k: record[k] for k in ("update", "floors", "learn_seconds")}), flush=True)
    summary.update(evaluate(game, scorer, output / "evaluation", config["eval_seeds"]))
    updates = summary["updates"]
    summary["adapter"] = updates[-1]["adapter"] if updates else config["adapter"]
    summary["finished"] = time.time()
    summary["run_directories"] = [
        str(path.parent) for path in sorted(output.glob("update-*/run-*/steps.jsonl"))]
    write_json(output / "summary.json", summary)
    return summary


def evaluate(game: Game, scorer: Scorer | None, output: Path, seeds: list[str]) -> dict:
    results = play_seeds(game, output, seeds, scorer, temperature=0, label="evaluation")
    return {"evaluation": {r["seed"]: r["floor"] for r in results},
            "evaluation_status": {r["seed"]: r["status"] for r in results}}
