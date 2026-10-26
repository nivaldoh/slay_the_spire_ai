"""Checkpoint RL, model side (docs/twwarhammer3/checkpoint-rl-plan.md, stages 3 to 5).

One structure for every method: a task is one public context with its scored candidates and
a reward per candidate; a task set lists tasks with their splits; a method changes only the
update rule (``METHODS``); training, evaluation and comparison are shared. The first and only
method, ``exact_table@1``, maximises the exact expected reward over audited reward tables.
The model never runs beside the game. Torch is imported lazily: game phases that import this
module never initialise CUDA. Nothing here is verified beyond its tests.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import time
from pathlib import Path

from gameai.lm import candidate_log_probs, gpu_lease, tensor_hash, verify_adapter_tensors
from gameai.provenance import sha256, write_json
from twwarhammer3.battle import checkpoint, play
from twwarhammer3.battle.candidates import (
    CANDIDATES_VERSION,
    candidates,
    evaluation_orderings,
    mapping_hash,
    slot_to_candidate,
    training_orderings,
)
from twwarhammer3.battle.scripted import distance

RENDERING_VERSION = 1
EVALUATION_VERSION = 1
MODEL_ID, REVISION = "Qwen/Qwen3-0.6B", "c1899de289a04d12100db370d81485cdf75e47ca"
BASE_SNAPSHOT = Path.home() / f".cache/spire-models/models--Qwen--Qwen3-0.6B/snapshots/{REVISION}"
EOS_TOKEN_ID = 151645  # <|im_end|>, the tokenizer's eos_token
# The Spire language lock: one local model process at a time across both games.
GPU_LOCK_PATH = Path(f"/tmp/spire-language-gpu-{os.getuid()}.lock")
# JUDGEMENT: training_settings — Claude, 2026-10-26: K 4 fresh permutations per update,
# temperature 1.0, LoRA r 8/16/dropout 0, AdamW lr 1e-4, no weight decay, token cap 1,536,
# batch 16; versus other values or SGD. Stage 3 and 4 results rest on this.
SETTINGS = {"K": 4, "temperature": 1.0, "lr": 1e-4, "weight_decay": 0.0, "token_cap": 1536,
            "batch_size": 16}
LORA = {"r": 8, "lora_alpha": 16, "lora_dropout": 0.0, "bias": "none", "task_type": "CAUSAL_LM",
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj",
                           "down_proj"]}


def digest(value) -> str:
    return checkpoint.digest(value)


# --- Rendering ------------------------------------------------------------------------------

def _number(value, digits=1) -> str:
    return "?" if value is None else f"{round(value, digits):g}"


def render_context(context: dict, listed: list[dict], permutation: list[int]) -> str:
    """The compact public text a model reads: friendly units with their nearest visible enemy
    and its distance in whole metres, the visible enemies, then the candidates as numbered
    lines in the permutation's order."""
    enemies = context.get("enemy", [])
    lines = [f"Battle time {_number(context['time_ms'] / 1000)} s, "
             f"{_number((context.get('remaining_ms') or 0) / 1000, 0)} s left. "
             "Choose one order batch for your army.", "Your units:"]
    for unit in context.get("friendly", []):
        morale = (unit.get("morale") or {}).get("fraction")
        line = (f"{unit['id']} {unit.get('type')} {unit.get('class')}: men {unit.get('men')}/"
                f"{unit.get('men0')}, hp {_number(unit.get('hp'), 2)}, ammo {unit.get('ammo')}, "
                f"morale {_number(morale, 2)}, at x {_number(unit.get('x'))} "
                f"z {_number(unit.get('z'))}, state {','.join(unit.get('state', [])) or 'none'}")
        if enemies:
            nearest = min(enemies, key=lambda enemy: distance(unit, enemy))
            line += f"; nearest enemy {nearest['id']} at {round(distance(unit, nearest))} m"
        lines.append(line)
    lines.append("Enemies in sight:" if enemies else "Enemies in sight: none")
    for enemy in enemies:
        lines.append(f"{enemy['id']} {enemy.get('type')} {enemy.get('class')}: men "
                     f"{enemy.get('men')}/{enemy.get('men0')}, at x {_number(enemy.get('x'))} "
                     f"z {_number(enemy.get('z'))}, "
                     f"state {','.join(enemy.get('state', [])) or 'none'}")
    lines.append("Choices:")
    # Written out, not through slot_to_candidate: the closed-loop check compares this text
    # with the mapping, so a mapping bug shared by training and evaluation still shows.
    for slot, index in enumerate(permutation):
        lines.append(f"{slot}: {listed[index]['description']}")
    lines.append('Reply with {"a":N}, N the number of your choice.')
    return "\n".join(lines)


def choice_lines(rendered: str) -> dict[int, str]:
    """The numbered candidate lines of a rendered prompt, parsed from its text."""
    body = rendered.split("\nChoices:\n", 1)[1]
    return {int(m.group(1)): m.group(2) for m in re.finditer(r"^(\d+): (.*)$", body, re.M)}


# --- Scoring --------------------------------------------------------------------------------

class CandidateScorer:
    """Scores a task's candidates under one displayed ordering. The distribution is over
    displayed slots; ``by_candidate`` maps it to canonical candidates."""

    def __init__(self, model, tokenizer, *, temperature: float, token_cap: int):
        self.model, self.tokenizer = model, tokenizer
        self.temperature, self.token_cap = temperature, token_cap

    def encode(self, task: dict, permutation: list[int]):
        rendered = render_context(task["context"], task["candidates"], permutation)
        prompt = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": rendered}], tokenize=False,
            add_generation_prompt=True, enable_thinking=False)
        ids = self.tokenizer(prompt, add_special_tokens=False)["input_ids"]
        if len(ids) > self.token_cap:
            raise ValueError(f"{len(ids)} prompt tokens exceed the cap of {self.token_cap}")
        completions = [self.tokenizer(json.dumps({"a": k}, separators=(",", ":")),
                                      add_special_tokens=False)["input_ids"] + [EOS_TOKEN_ID]
                       for k in range(len(permutation))]
        return ids, completions, rendered

    def adapter_state(self) -> dict:
        return adapter_state(self.model)

    def slot_log_probs(self, task: dict, permutation: list[int]):
        """Normalised, tempered log-probabilities over displayed slots (gradients allowed)."""
        import torch

        ids, completions, _ = self.encode(task, permutation)
        scores = candidate_log_probs(self.model, ids, completions)
        return torch.log_softmax(scores / self.temperature, dim=0)


def by_candidate(slot_values, permutation: list[int]):
    """Reorder per-slot values to canonical candidate order via slot_to_candidate."""
    import torch

    order = [0] * len(permutation)
    for slot in range(len(permutation)):
        order[slot_to_candidate(permutation, slot)] = slot
    return slot_values[torch.tensor(order, device=slot_values.device)]


# --- Tasks and task sets --------------------------------------------------------------------

def task_hash(task: dict) -> str:
    return digest({key: task[key] for key in ("context", "candidates", "mapping", "rewards",
                                              "split", "provenance")})


def make_task(context: dict, listed: list[dict], rewards: list[int], split: str,
              provenance: dict, cost: int) -> dict:
    task = {"context": context, "candidates": listed, "mapping": mapping_hash(listed),
            "rewards": rewards, "split": split, "provenance": provenance, "cost": cost}
    task["hash"] = task_hash(task)
    task["eval_orderings"] = evaluation_orderings(len(listed), task["hash"])
    return task


def tasks_from_table(table_path: Path, splits: dict) -> list[dict]:
    """One task per audited rung with a winner and a loser; ``splits`` maps each root (all
    its checkpoints) to a split."""
    table = json.loads(table_path.read_text())
    out = []
    for rung in table["rungs"]:
        if not (1 in rung["rewards"] and 0 in rung["rewards"]):
            continue
        out.append(make_task(rung["context"], rung["candidates"], rung["rewards"],
                             splits[rung["root"]], {"audit": sha256(table_path),
                                                    "root": rung["root"], "tick": rung["tick"]},
                             rung["launches"]))
    return out


def transform(tasks: list[dict], kind: str | None, seed: int = 0) -> list[dict]:
    """A label transform on the training split only, recorded in each changed task's
    provenance: shuffle_classes reassigns training rewards among tasks; derange_first_loser
    rewards the first losing candidate in canonical order instead."""
    if kind is None:
        return tasks
    out = [copy.deepcopy(task) for task in tasks]
    training = [task for task in out if task["split"] == "train"]
    if kind == "shuffle_classes":
        labels = [task["provenance"]["class"] for task in training]
        random.Random(f"shuffle:{seed}").shuffle(labels)
        for task, label in zip(training, labels):
            task["rewards"] = synthetic_rewards(task["candidates"], label)
    elif kind == "derange_first_loser":
        for task in training:
            first = task["rewards"].index(0)
            task["rewards"] = [int(i == first) for i in range(len(task["rewards"]))]
    else:
        raise ValueError(f"unknown label transform {kind}")
    for task in training:
        task["provenance"] = {**task["provenance"], "transform": {"kind": kind, "seed": seed}}
        task["hash"] = task_hash(task)
        task["eval_orderings"] = evaluation_orderings(len(task["candidates"]), task["hash"])
    return out


def validate_splits(tasks: list[dict]) -> None:
    """No root (real tasks) or template job (synthetic tasks) in two splits."""
    seen = {}
    for task in tasks:
        source = task["provenance"]
        key = ("job", source["template_job"]) if "template_job" in source else (
            "root", source["root"])
        if seen.setdefault(key, task["split"]) != task["split"]:
            raise ValueError(f"{key[0]} {key[1]} appears in two splits")


def task_set(name: str, tasks: list[dict]) -> dict:
    validate_splits(tasks)
    if len({task["hash"] for task in tasks}) != len(tasks):
        raise ValueError("a task appears twice")
    listing = sorted([task["hash"], task["split"]] for task in tasks)
    return {"name": name, "hash": digest(listing), "tasks": tasks}


def write_task_set(path: Path, value: dict) -> None:
    if path.exists():
        raise FileExistsError(path)
    write_json(path, value)


def read_task_set(path: Path) -> dict:
    value = json.loads(path.read_text())
    for task in value["tasks"]:
        if task_hash(task) != task["hash"]:
            raise ValueError(f"task {task['hash'][:12]} differs from its hash")
    if digest(sorted([t["hash"], t["split"]] for t in value["tasks"])) != value["hash"]:
        raise ValueError(f"{path} differs from its hash")
    return value


# --- The synthetic state-dependence task ------------------------------------------------------

# JUDGEMENT: synthetic_check — Claude, 2026-10-26: 100 m rule, balanced classes, 200/100 tasks
# split by job, 300 updates, pass 0.9 at every eval permutation, control at majority + 0.1;
# versus another rule or thresholds. Whether stage 4 starts rests on this.
SYNTHETIC = {"boundary_m": 100, "near_m": [20, 90], "far_m": [110, 300], "unit": "f2",
             "enemy": "e1", "near": "fall_back_f2", "far": "attack_nearest",
             "counts": {"train": 200, "held_out": 100}}


def synthetic_rewards(listed: list[dict], label: str) -> list[int]:
    winner = SYNTHETIC["near"] if label == "near" else SYNTHETIC["far"]
    if winner not in [c["id"] for c in listed]:
        raise ValueError(f"no {winner} candidate")
    return [int(c["id"] == winner) for c in listed]


def template_observations(job: Path) -> list[dict]:
    """A job's recorded public observations, in trace order."""
    out = []
    for trace in sorted(job.glob("episode-*/trace.jsonl")):
        for line in trace.read_text().splitlines():
            event = json.loads(line)
            if event.get("kind") == "observation":
                out.append(event["observation"])
    return out


def synthetic_context(reference: dict, template: dict, d: float, bearing: float) -> dict | None:
    """The reference observation with the template's friendly positions and the enemy placed
    ``d`` metres from the handgunners at ``bearing`` degrees; None outside the bounds."""
    context = copy.deepcopy(reference)
    for unit in context["friendly"]:
        source = next(u for u in template["friendly"] if u["id"] == unit["id"])
        unit["x"], unit["z"] = source["x"], source["z"]
    guns = next(u for u in context["friendly"] if u["id"] == SYNTHETIC["unit"])
    x = round(guns["x"] + d * math.cos(math.radians(bearing)), 1)
    z = round(guns["z"] + d * math.sin(math.radians(bearing)), 1)
    bounds = context["terrain"]["bounds"]
    if not (bounds["min_x"] <= x <= bounds["max_x"] and bounds["min_z"] <= z <= bounds["max_z"]):
        return None
    enemy = next(u for u in context["enemy"] if u["id"] == SYNTHETIC["enemy"])
    enemy["x"], enemy["z"] = x, z
    return context


def synthetic_tasks(templates: dict[str, list[tuple[str, dict]]], reference: dict,
                    seed: int, counts: dict | None = None) -> list[dict]:
    """Balanced near/far tasks; every draw from a stream keyed by (split, task index).
    ``templates`` maps a split to (job, observation) pairs; held-out draws that repeat a
    training draw's rounded distance and bearing on a nearby template are redrawn."""
    reference = play.context_projection(play.public(reference, {}))
    counts = counts or SYNTHETIC["counts"]
    near, far = SYNTHETIC["near_m"], SYNTHETIC["far_m"]
    out, train_keys = [], []
    for split in ("train", "held_out"):
        for index in range(counts[split]):
            rng = random.Random(f"synthetic:{seed}:{split}:{index}")
            while True:
                job, template = rng.choice(templates[split])
                label = "near" if rng.random() < 0.5 else "far"
                d = rng.uniform(*(near if label == "near" else far))
                bearing = rng.uniform(0, 360)
                context = synthetic_context(reference, play.context_projection(
                    play.public(template, {})), d, bearing)
                if context is None:
                    continue
                key = (round(d), round(bearing))
                if split == "held_out" and any(
                        k == key and _displacement(t, context) < 5 for k, t in train_keys):
                    continue
                break
            listed = candidates(context)["candidates"]
            out.append(make_task(context, listed, synthetic_rewards(listed, label), split,
                                 {"synthetic": digest(SYNTHETIC), "seed": seed, "index": index,
                                  "template_job": job, "class": label, "d": d,
                                  "bearing": bearing}, 0))
            if split == "train":
                train_keys.append((key, context))
    return out


def build_tasks(plan: dict) -> dict:
    """``rl tasks``: a task set from audit tables ({table, splits}) and/or the synthetic
    generator ({train: [jobs], held_out: [jobs], reference: {job, index}, seed, counts}),
    with an optional training-split label transform ({kind, seed})."""
    tasks = []
    for item in plan.get("tables", []):
        tasks += tasks_from_table(Path(item["table"]), item["splits"])
    if "synthetic" in plan:
        spec = plan["synthetic"]
        templates = {split: [(Path(job).name, o) for job in spec[split]
                             for o in template_observations(Path(job))]
                     for split in ("train", "held_out")}
        reference = template_observations(Path(spec["reference"]["job"]))[
            spec["reference"]["index"]]
        tasks += synthetic_tasks(templates, reference, spec["seed"], spec.get("counts"))
    change = plan.get("transform") or {}
    return task_set(plan["name"], transform(tasks, change.get("kind"), change.get("seed", 0)))


def _displacement(a: dict, b: dict) -> float:
    units = {u["id"]: u for u in a["friendly"]}
    return sum(distance(u, units[u["id"]]) for u in b["friendly"])


# --- Model loading and artifacts --------------------------------------------------------------

def file_hashes(directory: Path) -> dict:
    return {path.name: sha256(path) for path in sorted(directory.iterdir()) if path.is_file()}


def load_base(snapshot: Path = BASE_SNAPSHOT):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError("checkpoint RL needs the llm extra's CUDA torch")
    torch.cuda.set_per_process_memory_fraction(0.70)
    tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True,
                                              trust_remote_code=False)
    if tokenizer.eos_token_id != EOS_TOKEN_ID:
        raise ValueError(f"tokenizer EOS {tokenizer.eos_token_id} is not {EOS_TOKEN_ID}")
    model = AutoModelForCausalLM.from_pretrained(
        snapshot, local_files_only=True, dtype=torch.bfloat16, device_map={"": "cuda:0"},
        attn_implementation="sdpa", trust_remote_code=False)
    if getattr(model.config, "attention_dropout", 0) != 0:
        raise ValueError("the declared policy has no dropout")
    return model, tokenizer


def fresh_adapter(model, seed: int):
    """The declared LoRA shape with PEFT's default initialisation: it scores as the base."""
    import torch
    from peft import LoraConfig, get_peft_model

    torch.manual_seed(seed)
    model = get_peft_model(model, LoraConfig(**LORA))
    trainable = [name for name, p in model.named_parameters() if p.requires_grad]
    if not trainable or not all("lora_" in name for name in trainable):
        raise ValueError("only LoRA tensors may train")
    return model


def adapter_state(model) -> dict:
    from peft import get_peft_model_state_dict

    return {k: v.detach().cpu().clone() for k, v in get_peft_model_state_dict(model).items()}


def save_adapter(model, tokenizer, directory: Path, extra: dict) -> dict:
    """Save the adapter and its declaration (directory.json beside it)."""
    model.save_pretrained(directory)
    declaration = {
        "base": {"id": MODEL_ID, "revision": REVISION, "directory": str(BASE_SNAPSHOT),
                 "files": {name: sha256(BASE_SNAPSHOT / name) for name in
                           ("config.json", "model.safetensors", "tokenizer.json")}},
        "adapter": {"directory": str(directory.resolve()), "files": file_hashes(directory),
                    "tensors": tensor_hash(adapter_state(model))},
        "tokenizer_sha256": sha256(BASE_SNAPSHOT / "tokenizer.json"),
        "template_sha256": hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
        "rendering_version": RENDERING_VERSION, "candidates_version": CANDIDATES_VERSION,
        "eos_token_id": EOS_TOKEN_ID, "lora": LORA, **extra}
    write_json(directory.with_suffix(".json"), declaration)
    return declaration


def load_adapter(declaration: dict, *, trainable: bool):
    """Base plus a declared adapter, its files and tensors checked against the declaration."""
    from peft import PeftModel, get_peft_model_state_dict
    from safetensors.torch import load_file

    directory = Path(declaration["adapter"]["directory"])
    if file_hashes(directory) != declaration["adapter"]["files"]:
        raise ValueError(f"{directory} differs from its declaration")
    model, tokenizer = load_base()
    model = PeftModel.from_pretrained(model, directory, is_trainable=trainable,
                                      local_files_only=True)
    saved = load_file(str(directory / "adapter_model.safetensors"), device="cpu")
    verify_adapter_tensors(get_peft_model_state_dict(model), saved)
    if tensor_hash(adapter_state(model)) != declaration["adapter"]["tensors"]:
        raise ValueError("loaded adapter tensors differ from the declaration")
    return model, tokenizer


# --- The first method -----------------------------------------------------------------------

def expected_reward(scorer, task: dict, permutation: list[int]):
    """Σ_c π_p(c|x) r(c) under one displayed ordering (gradients allowed)."""
    import torch

    probabilities = by_candidate(scorer.slot_log_probs(task, permutation), permutation).exp()
    rewards = torch.tensor(task["rewards"], dtype=probabilities.dtype,
                           device=probabilities.device)
    return (probabilities * rewards).sum()


def objective(scorer, tasks: list[dict], permutations: dict) -> float:
    import torch

    with torch.no_grad():
        values = [sum(float(expected_reward(scorer, t, p)) for p in permutations[t["hash"]])
                  / len(permutations[t["hash"]]) for t in tasks]
    return sum(values) / len(values) if values else 0.0


def distributions(scorer, tasks: list[dict], permutations: dict) -> dict:
    import torch

    with torch.no_grad():
        return {t["hash"]: [by_candidate(scorer.slot_log_probs(t, p), p).float().tolist()
                            for p in permutations[t["hash"]]] for t in tasks}


def exact_table_step(scorer, optimizer, tasks: list[dict], permutations: dict,
                     config: dict) -> dict:
    """exact_table@1: one step on −(1/K) Σ_p Σ_c π_p(c|x) r(c), averaged over the batch's
    tasks whose rewards differ. A batch with none left takes no optimizer step.

    JUDGEMENT: objective — Claude, 2026-10-26: exact expected reward on audited one-decision
    tables as the first method, versus a sampled policy-gradient method first (competes with
    checkpoint-rl.md `candidate_reinforce`). Launches per update rest on this.
    """
    import torch

    model = scorer.model
    trainable = [p for p in model.parameters() if p.requires_grad]
    signal = [t for t in tasks if len(set(t["rewards"])) > 1]
    before = scorer.adapter_state()
    record = {"tasks": [t["hash"] for t in tasks], "signal_tasks": [t["hash"] for t in signal],
              "permutations": {t["hash"]: permutations[t["hash"]] for t in tasks},
              "adapter_before": tensor_hash(before), "updated": False}
    if not signal:
        record["adapter_after"] = record["adapter_before"]
        return record
    record["distributions_before"] = distributions(scorer, signal, permutations)
    optimizer.zero_grad(set_to_none=True)
    loss_value = 0.0
    for task in signal:
        perms = permutations[task["hash"]]
        for p in perms:
            loss = -expected_reward(scorer, task, p) / (len(perms) * len(signal))
            if not torch.isfinite(loss):
                raise ValueError("non-finite loss")
            loss.backward()
            loss_value += float(loss.detach())
    grads = [p.grad.detach().clone() if p.grad is not None else torch.zeros_like(p)
             for p in trainable]
    if not all(bool(torch.isfinite(g).all()) for g in grads):
        raise ValueError("non-finite gradient")
    norm = float(torch.sqrt(sum((g.float() ** 2).sum() for g in grads)))
    params_before = [p.detach().clone() for p in trainable]
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    # The predicted change of the expected reward: −∇loss · Δθ.
    predicted = -float(sum((g.float() * (p.detach() - q).float()).sum()
                           for g, p, q in zip(grads, trainable, params_before)))
    after_value = -objective(scorer, signal, permutations)
    record.update(updated=True, loss=loss_value, loss_after=after_value, gradient_norm=norm,
                  predicted_change=predicted, measured_change=loss_value - after_value,
                  distributions_after=distributions(scorer, signal, permutations),
                  adapter_after=tensor_hash(scorer.adapter_state()))
    record["kl"] = sum(
        sum(math.exp(a) * (a - b) for a, b in zip(old, new))
        for h in record["distributions_before"]
        for old, new in zip(record["distributions_before"][h], record["distributions_after"][h])
    ) / sum(len(v) for v in record["distributions_before"].values())
    return record


METHODS = {"exact_table@1": exact_table_step}


def make_optimizer(model, settings: dict):
    import torch

    trainable = [p for p in model.parameters() if p.requires_grad]
    return torch.optim.AdamW(trainable, lr=settings["lr"], weight_decay=settings["weight_decay"])


# --- Runs -----------------------------------------------------------------------------------

def refuse_beside_game() -> None:
    from twwarhammer3.engine import runtime

    if runtime.running_pids():
        raise RuntimeError("WH3 is running: model phases never run beside the game")


def batches(tasks: list[dict], batch_size: int, order_seed: int):
    """Passes over the tasks, each shuffled with the order seed and cut into batches (a
    short last batch kept)."""
    epoch = 0
    while True:
        order = list(tasks)
        random.Random(f"order:{order_seed}:{epoch}").shuffle(order)
        for start in range(0, len(order), batch_size):
            yield order[start:start + batch_size]
        epoch += 1


def run_updates(scorer, optimizer, tasks: list[dict], plan: dict, output: Path,
                set_hash: str) -> list[dict]:
    """``max_updates`` updates of the plan's method; one record per update."""
    step = METHODS[plan["method"]]
    records, source = [], batches(tasks, plan["batch_size"], plan["order_seed"])
    for ordinal in range(plan["max_updates"]):
        batch = next(source)
        permutations = {t["hash"]: training_orderings(len(t["candidates"]), t["hash"], ordinal,
                                                      plan["K"], t["eval_orderings"])
                        for t in batch}
        started = time.time()
        record = step(scorer, optimizer, batch, permutations, plan)
        record.update(ordinal=ordinal, task_set=set_hash, method=plan["method"],
                      wall_s=round(time.time() - started, 3))
        if records and record["adapter_before"] != records[-1]["adapter_after"]:
            raise ValueError("the adapter changed between updates")
        write_json(output / f"update-{ordinal:04d}.json", record)
        records.append(record)
    return records


def train(plan: dict, output: Path) -> dict:
    """``rl train``: a method, its config, a training task set (its train split only), a start
    adapter (``fresh`` or a declaration path), seeds, batch size and a budget of updates."""
    import torch

    refuse_beside_game()
    settings = {**SETTINGS, **plan.get("settings", {})}
    plan = {**plan, **{k: plan.get(k, settings[k]) for k in ("K", "batch_size")},
            "settings": settings}
    tasks = read_task_set(Path(plan["task_set"]))
    training = [t for t in tasks["tasks"] if t["split"] == "train"]
    output.mkdir(parents=True)
    write_json(output / "plan.json", plan)
    with gpu_lease(GPU_LOCK_PATH):
        started = time.time()
        torch.cuda.reset_peak_memory_stats()
        extra = {"temperature": settings["temperature"], "token_cap": settings["token_cap"],
                 "adapter_seed": plan["adapter_seed"]}
        if plan["start"] == "fresh":
            model, tokenizer = load_base()
            model = fresh_adapter(model, plan["adapter_seed"])
            start = save_adapter(model, tokenizer, output / "adapter-0000", extra)
            start_path = output / "adapter-0000.json"
        else:
            start_path = Path(plan["start"])
            start = json.loads(start_path.read_text())
            model, tokenizer = load_adapter(start, trainable=True)
        model.eval()
        scorer = CandidateScorer(model, tokenizer, temperature=settings["temperature"],
                                 token_cap=settings["token_cap"])
        optimizer = make_optimizer(model, settings)
        records = run_updates(scorer, optimizer, training, plan, output, tasks["hash"])
        final = save_adapter(model, tokenizer, output / "adapter-final",
                             {**extra, "start": str(start_path), "updates": len(records),
                              "task_set": tasks["hash"], "method": plan["method"]})
        summary = {"start": str(start_path), "final": str(output / "adapter-final.json"),
                   "updates": len(records), "updated": sum(r["updated"] for r in records),
                   "wall_s": round(time.time() - started, 1),
                   "cuda_peak_allocated": torch.cuda.max_memory_allocated(),
                   "cuda_peak_reserved": torch.cuda.max_memory_reserved(),
                   "adapter_final": final["adapter"]["tensors"],
                   "adapter_start": start["adapter"]["tensors"]}
    write_json(output / "summary.json", summary)
    return summary


# --- Evaluation and comparison ----------------------------------------------------------------

def score_orderings(scorer, task: dict) -> list[dict]:
    """Per evaluation ordering: slot log-probabilities, the argmax slot, the candidate it maps
    to and the text of the numbered line at that slot, parsed from the rendered prompt."""
    import torch

    rows = []
    for permutation in task["eval_orderings"]:
        with torch.no_grad():
            slots = scorer.slot_log_probs(task, permutation).float().tolist()
        _, _, rendered = scorer.encode(task, permutation)
        top = max(range(len(slots)), key=slots.__getitem__)
        rows.append({"permutation": permutation, "slot_log_probs": slots, "argmax_slot": top,
                     "argmax_candidate": slot_to_candidate(permutation, top),
                     "argmax_line": choice_lines(rendered)[top]})
    return rows


def metrics(tasks: list[dict], scored: dict[str, list[dict]]) -> dict:
    """Every evaluation metric from scored orderings and the tasks' rewards alone."""
    per_task, splits = {}, {}
    for task in tasks:
        rows, rewards = scored[task["hash"]], task["rewards"]
        n = len(rewards)
        masses, hits, averaged = [], [], [0.0] * n
        for row in rows:
            probs = [0.0] * n
            for slot, value in enumerate(row["slot_log_probs"]):
                probs[slot_to_candidate(row["permutation"], slot)] = math.exp(value)
            masses.append(sum(p * r for p, r in zip(probs, rewards)))
            hits.append(rewards[row["argmax_candidate"]])
            averaged = [a + p / len(rows) for a, p in zip(averaged, probs)]
        per_task[task["hash"]] = {
            "split": task["split"], "mass": sum(masses) / len(masses),
            "mass_by_ordering": masses, "argmax_accuracy": sum(hits) / len(hits),
            "hits": hits, "choice": max(range(n), key=averaged.__getitem__),
            "uniform": sum(rewards) / n,
            "index0": sum(rewards[row["permutation"][0]] for row in rows) / len(rows)}
    for split in sorted({t["split"] for t in tasks}):
        mine = [t for t in tasks if t["split"] == split]
        depth = min(len(scored[t["hash"]]) for t in mine)
        by_index = [sum(per_task[t["hash"]]["hits"][i] for t in mine) / len(mine)
                    for i in range(depth)]
        winners = [tuple(c["id"] for c, r in zip(t["candidates"], t["rewards"]) if r)
                   for t in mine]
        counts = {w: winners.count(w) for w in set(winners)}
        splits[split] = {
            "tasks": len(mine), "argmax_accuracy_by_index": by_index,
            "argmax_accuracy_min": min(by_index), "argmax_accuracy_max": max(by_index),
            "mass": sum(per_task[t["hash"]]["mass"] for t in mine) / len(mine),
            "uniform": sum(per_task[t["hash"]]["uniform"] for t in mine) / len(mine),
            "index0": sum(per_task[t["hash"]]["index0"] for t in mine) / len(mine),
            "majority_class": max(counts.values()) / len(mine)}
    return {"tasks": per_task, "splits": splits}


def kl_from(start: dict, scored: dict) -> float:
    """Mean KL(start ‖ this) over every task and evaluation ordering."""
    total, count = 0.0, 0
    for key, rows in scored.items():
        for a, b in zip(start[key], rows):
            total += sum(math.exp(x) * (x - y) for x, y in zip(a["slot_log_probs"],
                                                               b["slot_log_probs"]))
            count += 1
    return total / count


def evaluate(declaration_path: Path, task_set_path: Path) -> dict:
    """``rl evaluate``: score an adapter on a task set under each task's evaluation orderings;
    write eval-<adapter>-<task set sha12>.json beside the adapter, once."""
    refuse_beside_game()
    declaration = json.loads(declaration_path.read_text())
    tasks = read_task_set(task_set_path)
    run = declaration_path.parent
    name = declaration_path.stem
    output = run / f"eval-{name}-{tasks['hash'][:12]}.json"
    if output.exists():
        raise FileExistsError(output)
    start_path = Path(declaration.get("start", declaration_path))
    start_eval = start_path.parent / f"eval-{start_path.stem}-{tasks['hash'][:12]}.json"
    if start_path != declaration_path and not start_eval.exists():
        raise FileNotFoundError(f"evaluate the start adapter first: {start_eval}")
    with gpu_lease(GPU_LOCK_PATH):
        model, tokenizer = load_adapter(declaration, trainable=False)
        model.eval()
        scorer = CandidateScorer(model, tokenizer, temperature=declaration["temperature"],
                                 token_cap=declaration["token_cap"])
        started = time.time()
        scored = {t["hash"]: score_orderings(scorer, t) for t in tasks["tasks"]}
        wall = time.time() - started
    result = evaluation_record(declaration_path, declaration, tasks, scored, start_path,
                               start_eval)
    result["wall_s"] = round(wall, 1)
    write_json(output, result)
    return result


def evaluation_record(declaration_path, declaration, tasks, scored, start_path, start_eval):
    plan_path = declaration_path.parent / "plan.json"
    plan = json.loads(plan_path.read_text()) if plan_path.exists() else {}
    updates = sorted(declaration_path.parent.glob("update-*.json")) \
        if declaration_path.stem != "adapter-0000" else []
    start = json.loads(start_eval.read_text()) if start_path != declaration_path else None
    training = None
    if updates:
        training = json.loads(Path(plan["task_set"]).read_text())
        training = {"hash": training["hash"], "launches": sum(
            t["cost"] for t in training["tasks"] if t["split"] == "train"),
            "tasks": sum(1 for t in training["tasks"] if t["split"] == "train")}
    return {
        "evaluation_version": EVALUATION_VERSION, "adapter": str(declaration_path),
        "adapter_tensors": declaration["adapter"]["tensors"], "task_set": tasks["hash"],
        "rendering_version": declaration["rendering_version"],
        "candidates_version": declaration["candidates_version"],
        "temperature": declaration["temperature"], "token_cap": declaration["token_cap"],
        "permutation_rule": "candidates.evaluation_orderings v1",
        "k_eval": {t["hash"]: len(t["eval_orderings"]) for t in tasks["tasks"]},
        "start_adapter": str(start_path), "method": declaration.get("method"),
        "config_hash": digest(plan.get("settings")) if plan else None,
        "training": training, "updates": len(updates),
        "train_wall_s": sum(json.loads(p.read_text())["wall_s"] for p in updates),
        "scored": scored, "metrics": metrics(tasks["tasks"], scored),
        "start_metrics": start["metrics"]["splits"] if start else None,
        "kl_from_start": kl_from(start["scored"], scored) if start else 0.0}


COMPARE_FIELDS = ("task_set", "start_adapter", "rendering_version", "candidates_version",
                  "temperature", "k_eval", "permutation_rule", "token_cap", "evaluation_version")


def compare(paths: list[Path], split: str) -> str:
    """``rl compare``: evaluations side by side, refused unless every COMPARE_FIELDS matches."""
    evals = [json.loads(path.read_text()) for path in paths]
    for field in COMPARE_FIELDS:
        if field == "start_adapter":
            starts = {e["start_adapter"] for e in evals if e["updates"]}
            if len(starts) > 1:
                raise ValueError(f"evaluations differ in {field}")
            continue
        if len({json.dumps(e[field], sort_keys=True) for e in evals}) > 1:
            raise ValueError(f"evaluations differ in {field}")
    lines = [f"split {split}: adapter | method | updates | launches | argmax min/max | mass "
             f"| uniform | index0 | majority | KL"]
    for path, e in zip(paths, evals):
        m = e["metrics"]["splits"][split]
        launches = (e["training"] or {}).get("launches", 0)
        lines.append(f"{path.parent.name}/{e['adapter'].split('/')[-1]} | {e['method']} | "
                     f"{e['updates']} | {launches} | {m['argmax_accuracy_min']:.3f}/"
                     f"{m['argmax_accuracy_max']:.3f} | {m['mass']:.3f} | {m['uniform']:.3f} | "
                     f"{m['index0']:.3f} | {m['majority_class']:.3f} | "
                     f"{e['kl_from_start']:.4f}")
    return "\n".join(lines)


def recount(path: Path, tasks_path: Path | None = None) -> dict:
    """``rl recount``: re-derive a record's numbers from records alone (no model, no game);
    writes recount.json beside it with the checker's and the inputs' hashes."""
    from twwarhammer3.battle import audit

    checks, inputs = {}, {}
    if path.is_file() and path.name.startswith("eval-"):
        value = json.loads(path.read_text())
        tasks = read_task_set(tasks_path)
        inputs = {str(path): sha256(path), str(tasks_path): sha256(tasks_path)}
        checks["task_set"] = tasks["hash"] == value["task_set"]
        again = metrics(tasks["tasks"], value["scored"])
        checks["metrics"] = json.dumps(again, sort_keys=True) == json.dumps(
            value["metrics"], sort_keys=True)
        start_path = Path(value["start_adapter"])
        start = start_path.parent / f"eval-{start_path.stem}-{tasks['hash'][:12]}.json"
        if value["updates"] and start.exists():
            checks["kl"] = math.isclose(kl_from(json.loads(start.read_text())["scored"],
                                                value["scored"]), value["kl_from_start"])
        lines = report_lines(value)
    elif path.is_file():
        tasks = read_task_set(path)
        inputs = {str(path): sha256(path)}
        validate_splits(tasks["tasks"])
        checks["hashes"] = True
        lines = [f"task set {tasks['hash'][:12]}: {len(tasks['tasks'])} tasks"]
    elif (path / "table.json").exists():
        inputs = {str(p): sha256(p) for p in sorted(path.glob("attempt-*/attempt.json"))}
        again = audit.table(path)
        checks["table"] = json.loads(json.dumps(again)) == json.loads(
            (path / "table.json").read_text())
        lines = [f"audit {again['name']}: rung {r['root']}@{r['tick']} n={len(r['candidates'])}"
                 f" winners={sum(r['rewards'])} refused={r['refused']} launches={r['launches']}"
                 f" statuses={r['statuses']} pass={r['verdict']['pass']}" for r in again["rungs"]]
    elif (path / "plan.json").exists() and list(path.glob("update-*.json")):
        records = [json.loads(p.read_text()) for p in sorted(path.glob("update-*.json"))]
        inputs = {str(p): sha256(p) for p in sorted(path.glob("update-*.json"))}
        plan = json.loads((path / "plan.json").read_text())
        tasks = read_task_set(Path(plan["task_set"]))
        held_out = {t["hash"] for t in tasks["tasks"] if t["split"] != "train"}
        checks["chain"] = all(a["adapter_after"] == b["adapter_before"]
                              for a, b in zip(records, records[1:]))
        checks["no_held_out"] = not any(set(r["tasks"]) & held_out for r in records)
        checks["ordinals"] = [r["ordinal"] for r in records] == list(range(len(records)))
        start = json.loads((path / "adapter-0000.json").read_text()) if (
            path / "adapter-0000.json").exists() else None
        checks["start"] = start is None or records[0]["adapter_before"] == start["adapter"][
            "tensors"]
        final = json.loads((path / "adapter-final.json").read_text())
        checks["final"] = records[-1]["adapter_after"] == final["adapter"]["tensors"]
        lines = [f"run {path.name}: {len(records)} updates, "
                 f"{sum(r['updated'] for r in records)} with a step"]
    elif (path / "confirm.json").exists():
        from twwarhammer3.battle import confirm as confirm_module

        value = json.loads((path / "confirm.json").read_text())
        again = confirm_module.clauses(path)
        inputs = {str(path / "confirm.json"): sha256(path / "confirm.json")}
        checks["clauses"] = again == value["clauses"]
        lines = [f"confirm {path.name}: " + ", ".join(f"{k} {v}" for k, v in again.items())]
    else:
        raise ValueError(f"nothing to recount in {path}")
    result = {"checks": checks, "pass": all(checks.values()), "lines": lines,
              "checker_sha256": sha256(Path(__file__)), "inputs": inputs}
    target = (path.parent if path.is_file() else path) / (
        f"recount-{path.stem}.json" if path.is_file() else "recount.json")
    write_json(target, result)
    return result


def report_lines(value: dict) -> list[str]:
    lines = []
    for split, m in value["metrics"]["splits"].items():
        lines.append(f"{split}: argmax accuracy min {m['argmax_accuracy_min']:.3f} max "
                     f"{m['argmax_accuracy_max']:.3f}, mass {m['mass']:.3f}; baselines uniform "
                     f"{m['uniform']:.3f}, index 0 {m['index0']:.3f}, majority "
                     f"{m['majority_class']:.3f}; KL from start {value['kl_from_start']:.4f}")
    return lines
