"""The self-improvement loop: a research agent runs one experiment at a time on the local model.

The rules follow ENPIRE's contract (NVlabs/ENPIRE, enpire/policy/autoresearch_instruction.md):
one falsifiable hypothesis per iteration, the smallest change, an approved number of trials,
and a change kept only past fixed gates; the agent never touches the environment, the seeds or
the scorer. The results log and "first run is the baseline" follow karpathy/autoresearch
(program.md). Here the agent edits only values inside ``SPACE``; it writes no code.

The agent is an Anthropic model, and the terms bar training on its outputs
(docs/posttraining.md, Provider terms), so nothing it writes reaches a prompt, a reward or a
training row: it only sets the numbers below. Rewards come from the game.

One process runs the whole loop: the game opens first and stays open, and a rejected cycle
restores the incumbent's weights in place.

python -m spire.localrl.research STATE_DIRECTORY --deadline UNIX_TIME --budget-usd 15 --ledger PATH
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import statistics
import time
from collections import Counter
from pathlib import Path

import torch

from gameai.ledger import BudgetExhausted, Ledger
from gameai.llm import APIError, InvalidReply, Model
from gameai.provenance import write_json
from spire.engine.runtime import GAME_DIR
from spire.localrl import policy, train
from spire.localrl.collect import Game

SPACE = {
    "method": ("ppo", "awr"), "temperature": (0.5, 2.0), "updates": (0, 4),
    "runs_per_update": (0, 10), "lr": (1e-6, 3e-4), "epochs": (1, 6), "minibatch": (4, 8),
    "clip": (0.05, 0.4), "entropy": (0.0, 0.05), "target_kl": (0.01, 0.2),
    "gamma": (0.97, 0.999), "lam": (0.8, 1.0), "beta": (0.3, 10.0),
    "weight_cap": (2.0, 20.0), "awr_rows": (500, 6000), "offline_share": (0.0, 1.0),
}
INTEGERS = {"updates", "runs_per_update", "epochs", "minibatch", "awr_rows"}
MAX_TRAINING_RUNS = 16
MAX_ROW_EPOCHS = 12000  # about 40 minutes of learning in one cycle
MAX_CYCLE_FAILURES = 3
# JUDGEMENT: Keep gate — Claude, 2026-11-06, owner away: a candidate replaces the incumbent when
# its greedy floors on the fixed evaluation seeds gain at least 0.5 on average, paired by seed,
# with no more seeds down than up. A stricter gate keeps less; the kept adapter rests on it.
MIN_GAIN = 0.5
MODEL = "claude-opus-5-5"
EFFORT = "high"
INSTRUCTIONS = """You run experiments on a small local language model (Qwen3-0.6B with a LoRA \
adapter) that plays Slay the Spire, Ironclad, Ascension 0, on the real game. It picks one symbol \
per decision from the public state. Each cycle you set training values, the loop plays sampled \
runs and updates the adapter, then the adapter plays fixed evaluation seeds greedily. The measure \
is floors reached on those seeds, paired by seed against the incumbent adapter.

Rules. Record one falsifiable hypothesis per cycle and change as little as tests it. You may set \
only the listed values, inside their ranges. You cannot change the evaluation seeds, the gate, \
the reward's floor term, the prompt or the code. Preserve failed trials: they stay in the log. \
Game time is the scarce resource, at about 2,400 decisions an hour, and a learning update \
takes about 0.2 s per row per epoch on top. Floors are noisy: one seed \
often moves several floors for no reason, so do not chase a single result, and a method needs \
a fair run before you drop it. Learning-only cycles (runs_per_update 0, method awr) cost \
no game time except evaluation.

Reply as JSON only, with keys hypothesis (one falsifiable sentence), reasoning (at most five \
sentences) and config_json (a JSON object string of the values you change)."""
SCHEMA = {
    "type": "object",
    "properties": {"hypothesis": {"type": "string"}, "reasoning": {"type": "string"},
                   "config_json": {"type": "string"}},
    "required": ["hypothesis", "reasoning", "config_json"], "additionalProperties": False,
}


def validate(changes) -> dict:
    """Refuse a key outside the space, a value outside its range, or a non-number."""
    if not isinstance(changes, dict):
        raise ValueError("config_json must be a JSON object")
    result = {}
    for key, value in changes.items():
        if key not in SPACE:
            raise ValueError(f"{key} is not an editable value")
        if key == "method":
            if value not in SPACE[key]:
                raise ValueError(f"method must be one of {SPACE[key]}")
            result[key] = value
            continue
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(f"{key} must be a number")
        if not math.isfinite(value):
            raise ValueError(f"{key} must be finite")
        if key in INTEGERS:
            if value != int(value):
                raise ValueError(f"{key} must be an integer")
            value = int(value)
        low, high = SPACE[key]
        if not low <= value <= high:
            raise ValueError(f"{key} must be within {low} and {high}")
        result[key] = value
    return result


def parse_reply(text: str, current: dict) -> dict:
    reply = json.loads(text)
    changes = validate(json.loads(reply["config_json"]))
    merged = {**current, **changes}
    if merged["updates"] * merged["runs_per_update"] > MAX_TRAINING_RUNS:
        raise ValueError(f"A cycle plays at most {MAX_TRAINING_RUNS} training runs")
    if merged["method"] == "ppo" and merged["runs_per_update"] == 0 and merged["updates"]:
        raise ValueError("PPO needs fresh runs")
    if merged["method"] == "awr":
        if merged["updates"] * merged["epochs"] * merged["awr_rows"] > MAX_ROW_EPOCHS:
            raise ValueError(f"updates x epochs x awr_rows must stay under {MAX_ROW_EPOCHS}")
    return {**reply, "changes": changes}


def compare(candidate: dict, incumbent: dict) -> dict:
    """The fixed gate: floors paired by seed."""
    shared = sorted(set(candidate) & set(incumbent))
    gains = [candidate[seed] - incumbent[seed] for seed in shared]
    up, down = sum(g > 0 for g in gains), sum(g < 0 for g in gains)
    mean = statistics.fmean(gains)
    return {"seeds": len(shared), "mean_gain": mean, "up": up, "down": down,
            "keep": mean >= MIN_GAIN and down <= up, "gains": gains}


def digest(run_directories: list[str], floors: list[int]) -> dict:
    """Where the runs died and what the policy did, from their steps."""
    deaths, actions, took, wasted, turns = Counter(), Counter(), Counter(), 0, 0
    for path in run_directories:
        lines = (Path(path) / "steps.jsonl").read_text().splitlines()
        steps = [json.loads(line) for line in lines]
        if steps:
            end = steps[-1]["observation"]
            deaths[f"floor {end['floor']} {end['room'] or end['screen']}"] += 1
        for step in steps:
            kind = step["label"].split(" ")[0]
            actions[kind] += 1
            if step["label"].startswith("take card "):
                took[step["label"].removeprefix("take card ")] += 1
            if step["label"] == "end turn":
                turns += 1
                wasted += step["observation"]["energy"] > 0 and step["observation"]["hand"] > 0
    return {"floors": floors, "last_rooms": deaths.most_common(8),
            "actions": actions.most_common(10), "cards_taken": took.most_common(10),
            "turns_ended_with_energy_and_cards": f"{wasted} of {turns}"}


def describe(state: dict) -> str:
    table = "\n".join(
        f"{c['cycle']}: {c['hypothesis']} | changes {json.dumps(c['changes'])} | train floors "
        f"{c['train_floors']} | evaluation {c['evaluation_mean']} | gate {c['gate']} | "
        f"{c['decision']}" for c in state["cycles"])
    return (
        f"Editable values and ranges: {json.dumps(SPACE)}\nA cycle plays at most "
        f"{MAX_TRAINING_RUNS} training runs.\nCurrent values: {json.dumps(state['config'])}\n"
        f"Controls on the evaluation seeds: {json.dumps(state['controls'])}\n"
        f"Incumbent evaluation by seed: {json.dumps(state['incumbent_evaluation'])}\n"
        f"Hours left: {(state['deadline'] - time.time()) / 3600:.1f}\n\nCycles so far:\n"
        f"{table or '(none)'}\n\nDigest of the last cycle: {json.dumps(state.get('digest'))}\n\n"
        "Propose the next experiment."
    )


def propose(model: Model, state: dict) -> dict:
    reply, attempts = model.ask(describe(state), SCHEMA,
                                lambda text: parse_reply(text, state["config"]), 2)
    reply["usd"] = sum(attempt.get("usd") or 0 for attempt in attempts)
    return reply


def run_cycle(root: Path, state: dict, changes: dict, game, scorer, offline) -> dict:
    index = next_cycle(root, state)
    config = {**state["config"], **changes}
    count = config["updates"] * config["runs_per_update"]
    start = state["next_train_seed"]
    config.update(
        output=str(root / f"cycle-{index:03d}"), adapter=state["incumbent"], seed=index + 1,
        earlier_runs=state["run_directories"], eval_seeds=state["eval_seeds"],
        train_seeds=[f"LRLTRAIN{i:04d}" for i in range(start, start + count)],
    )
    state["next_train_seed"] = start + count  # a crashed cycle's seeds are not reused
    return train.cycle(game, scorer, config, offline)


def next_cycle(root: Path, state: dict) -> int:
    """The first cycle number with no folder: a crash or a restart must not collide."""
    index = len(state["cycles"])
    while (root / f"cycle-{index:03d}").exists():
        index += 1
    return index


def snapshot_profile(root: Path, name: str) -> None:
    """A read-only copy of the owner's preferences, so a wipe is seen and costs little."""
    target = root / "profile-snapshots" / name
    shutil.copytree(GAME_DIR / "preferences", target)
    empty = sorted(path.name for path in target.iterdir() if path.stat().st_size == 0)
    print(json.dumps({"profile_snapshot": name, "empty_files": empty}), flush=True)


def card_pool() -> dict:
    """The profile's unlocked cards: floors are comparable only inside one pool, since a new
    unlock changes what a seed offers."""
    return json.loads((GAME_DIR / "preferences" / "STSUnlocks").read_text())


def restore(model, adapter: str) -> None:
    """Back to the incumbent's exact weights after a rejected cycle."""
    from peft import set_peft_model_state_dict
    from safetensors.torch import load_file

    weights = load_file(str(Path(adapter) / "adapter_model.safetensors"), device="cuda:0")
    outcome = set_peft_model_state_dict(model, weights)
    if outcome.unexpected_keys:
        raise ValueError(f"Adapter keys do not match: {outcome.unexpected_keys[:3]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--deadline", type=float, required=True)
    parser.add_argument("--budget-usd", type=float, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--cycle-hours", type=float, default=1.5,
                        help="start no cycle later than this before the deadline")
    arguments = parser.parse_args()
    root, state_path = arguments.root, arguments.root / "state.json"
    state = json.loads(state_path.read_text())
    state["deadline"] = arguments.deadline
    ledger = Ledger(arguments.ledger, arguments.budget_usd, must_exist=True)
    agent = Model(MODEL, EFFORT, ledger, provider="anthropic", instructions=INSTRUCTIONS,
                  max_output_tokens=6000)
    game = Game(root / "game")
    snapshot_profile(root, f"start-{int(time.time())}")
    game.open()
    model, tokenizer = policy.load(Path(state["incumbent"]), trainable=True)
    scorer = policy.Scorer(model, tokenizer)
    policy.enable_training(model)
    offline = train.read_offline(Path(state["offline"]))
    if not state["incumbent_evaluation"]:
        result = train.evaluate(game, scorer, root / "start-evaluation", state["eval_seeds"])
        state["incumbent_evaluation"] = result["evaluation"]
    state["card_pool"] = card_pool()
    write_json(state_path, state)
    failures = 0
    while time.time() < arguments.deadline - arguments.cycle_hours * 3600:
        try:
            proposal = propose(agent, state)
        except (APIError, InvalidReply, BudgetExhausted, ValueError) as error:
            # Training goes on without the agent: repeat the current values.
            proposal = {"hypothesis": f"(no agent: {type(error).__name__}) repeat", "reasoning": "",
                        "changes": {}, "usd": 0}
        index = next_cycle(root, state)
        print(json.dumps({"cycle": index, **proposal}), flush=True)
        try:
            summary = run_cycle(root, state, proposal["changes"], game, scorer, offline)
        except Exception as error:  # kept in the log, like any failed trial
            note = f"{type(error).__name__}: {error}"[:300]
            print(json.dumps({"cycle": index, "crashed": note}), flush=True)
            failures += 1
            state["cycles"].append({
                "cycle": index, "hypothesis": proposal["hypothesis"], "reasoning": note,
                "changes": proposal["changes"], "train_floors": [], "evaluation": {},
                "evaluation_mean": None, "gate": None, "decision": "crashed",
                "adapter": None, "usd": proposal["usd"], "learn": [], "score": [],
            })
            torch.cuda.empty_cache()
            restore(model, state["incumbent"])
            write_json(state_path, state)
            if failures >= MAX_CYCLE_FAILURES:
                break
            game.restart()
            continue
        failures = 0
        gate = compare(summary["evaluation"], state["incumbent_evaluation"])
        pool_changed = card_pool() != state["card_pool"]
        keep = gate["keep"] and not pool_changed
        decision = "keep" if keep else "reject (card pool changed)" if pool_changed else "reject"
        floors = [f for update in summary["updates"] for f in update["floors"]]
        record = {
            "cycle": index, "hypothesis": proposal["hypothesis"],
            "reasoning": proposal["reasoning"], "changes": proposal["changes"],
            "train_floors": floors, "evaluation": summary["evaluation"],
            "evaluation_mean": round(statistics.fmean(summary["evaluation"].values()), 2),
            "gate": {k: gate[k] for k in ("seeds", "mean_gain", "up", "down")},
            "decision": decision, "adapter": summary["adapter"], "usd": proposal["usd"],
            "learn": [update.get("learn") for update in summary["updates"]],
            "score": [update.get("score") for update in summary["updates"]],
        }
        state["cycles"].append(record)
        state["run_directories"] += summary["run_directories"]
        evaluation_runs = [str(path.parent) for path in sorted(
            (root / f"cycle-{index:03d}" / "evaluation").glob("run-*/steps.jsonl"))]
        state["digest"] = digest([*summary["run_directories"], *evaluation_runs], floors)
        state["config"].update(proposal["changes"])
        if keep:
            state["incumbent"] = summary["adapter"]
            state["incumbent_evaluation"] = summary["evaluation"]
        else:
            restore(model, state["incumbent"])
        if pool_changed:  # the incumbent's floors are from the old pool: measure it again
            directory = root / f"cycle-{index:03d}" / "incumbent-evaluation"
            again = train.evaluate(game, scorer, directory, state["eval_seeds"])
            state["incumbent_evaluation"] = again["evaluation"]
            state["card_pool"] = card_pool()
        write_json(state_path, state)
        snapshot_profile(root, f"after-cycle-{index:03d}")
        with (root / "results.tsv").open("a") as file:
            file.write("\t".join(map(str, (
                index, decision, record["evaluation_mean"],
                f"{gate['mean_gain']:+.2f}", f"{gate['up']}/{gate['down']}",
                proposal["hypothesis"]))) + "\n")
    game.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
