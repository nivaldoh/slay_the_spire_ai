"""Outcome-based policy-gradient post-training of a local language LoRA on combats.

Each iteration samples a group of complete original-engine combats per catalog
scenario from the current adapter's distribution over legal choices
(``sampling``), centers the terminal combat rewards within each scenario
group, and takes one AdamW step on the REINFORCE objective. Before the step, every
sampled action's log-probability is recomputed from its public prompt and must match
the recorded behavior value. Evaluation stays separate and uses the frozen greedy
policy. There is no resume: an interrupted job keeps its last completed iteration.
"""

from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path

import torch

from gameai.provenance import write_json
from spire.combat.catalog import load_catalog
from spire.combat.evidence import audit_run
from spire.combat.rollout import rollout
from spire.language.demonstrations import render_prompt
from spire.language.policy import (
    MAX_PROMPT_TOKENS,
    _verify_adapter_tensors,
    candidate_completions,
    candidate_log_probs,
    create_declaration,
    file_sha256,
    gpu_lease,
    validate_declaration,
)
from spire.language.sampling import SCORING, CandidateSampler
from spire.language.training import _adapter, _dependencies, _finite, _source, tensor_hash
from spire.ppo.learning import terminal_reward
from spire.protocol import Action, Decision, UnsupportedStateError

VERSION = "language-candidate-reinforce-v1"
REWARD = "won_one_plus_quarter_hp_fraction_else_minus_one_v1"
ASSOCIATION_TOLERANCE = 0.05
UPDATE_RESERVE_SECONDS = 300
REQUIRED = {
    "initial_declaration",
    "catalog",
    "seed",
    "iterations",
    "group_size",
    "temperature",
    "learning_rate",
    "time_budget_seconds",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _read(path: Path):
    return json.loads(Path(path).read_text())


def validate_config(value: dict) -> dict:
    _require(
        isinstance(value, dict) and value.keys() == REQUIRED, "Unknown or missing RL configuration"
    )
    for key in ("seed", "iterations", "group_size"):
        _require(type(value[key]) is int and value[key] >= (0 if key == "seed" else 1), key)
    _require(
        2 <= value["group_size"] <= 100 and value["iterations"] <= 999,
        "Group size must be 2-100 and iterations at most 999 for distinct seeds",
    )
    for key in ("temperature", "learning_rate", "time_budget_seconds"):
        number = value[key]
        _require(type(number) in (int, float) and math.isfinite(number) and number > 0, key)
    return {
        **value,
        "initial_declaration": str(Path(value["initial_declaration"]).resolve()),
        "catalog": str(Path(value["catalog"]).resolve()),
    }


def policy_seed(config: dict, iteration: int, scenario: int, member: int) -> int:
    """Declared, collision-free sampling seed for one scheduled combat."""
    return config["seed"] * 1_000_000 + iteration * 1_000 + scenario * 100 + member


def episode_reward(episode: dict) -> float:
    """Terminal reward from audited engine evidence (the PPO reward, unchanged)."""
    _require(episode["status"] in ("won", "lost"), "Only complete combats have rewards")
    if episode["status"] == "lost":
        return -1.0
    after = episode["transitions"][-1]["next_observation"]
    return terminal_reward("won", after["current_hp"], after["max_hp"])


def group_advantages(rewards: list[float]) -> list[float]:
    """Mean-centered within one scenario group; identical outcomes give no signal."""
    mean = sum(rewards) / len(rewards)
    return [reward - mean for reward in rewards]


def sampled_decisions(run: Path) -> tuple[dict, list[tuple[Decision, Action, dict]]]:
    """Audited episode plus each public decision, chosen action and behavior record."""
    audited = audit_run(run)
    _require(audited["valid"], f"Collected combat failed audit: {audited['issues']}")
    _require(len(audited["episodes"]) == 1, "Each collection run holds one combat")
    episode = audited["episodes"][0]
    records = []
    trace = run / "episode-0000/trace.jsonl"
    behaviors = {
        event["decision"]["id"]: event["behavior"]
        for event in map(json.loads, trace.read_text().splitlines())
        if event["kind"] == "decision"
    }
    for transition in episode["transitions"]:
        decision = Decision(
            transition["action"]["decision_id"],
            transition["observation"],
            tuple(Action(**item) for item in transition["candidates"]),
        )
        chosen = next(item for item in decision.candidates if item.id == transition["action_id"])
        records.append((decision, chosen, behaviors[decision.id]))
    return episode, records


class Scorer:
    """Shared prompt encoding for behavior sampling and learner recomputation."""

    def __init__(self, model, tokenizer, temperature: float):
        self.model = model
        self.tokenizer = tokenizer
        self.temperature = temperature

    def encode(self, decision: Decision) -> tuple[list[int], list[list[int]]]:
        prompt = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": render_prompt(decision)}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        ids = self.tokenizer(prompt, add_special_tokens=False)["input_ids"]
        if len(ids) > MAX_PROMPT_TOKENS:
            raise UnsupportedStateError("Language prompt exceeds 2048 tokens")
        return ids, candidate_completions(self.tokenizer, len(decision.candidates))

    def log_policy(self, decision: Decision):
        """Normalized tempered log-probabilities over legal choices (gradients allowed)."""
        ids, completions = self.encode(decision)
        scores = candidate_log_probs(self.model, ids, completions)
        return torch.log_softmax(scores / self.temperature, dim=0)

    def __call__(self, decision: Decision) -> tuple[list[float], int]:
        """Behavior scores for ``CandidateSampler``; tempering happens in the sampler."""
        ids, completions = self.encode(decision)
        self.model.eval()
        with torch.inference_mode():
            scores = candidate_log_probs(self.model, ids, completions)
        return scores.float().tolist(), len(ids)


def reinforce_step(
    scorer, optimizer, batch, *, expected_adapter: str, tolerance=ASSOCIATION_TOLERANCE
) -> dict:
    """One step on -sum(A * log pi(a|s)) / decisions, after checking behavior association.

    ``batch`` holds (decision, chosen action, behavior record, advantage) tuples. The
    learner's adapter must be the collection adapter before anything is recomputed.
    """
    model = scorer.model
    trainable = [p for p in model.parameters() if p.requires_grad]
    before = _adapter(model)
    _require(tensor_hash(before) == expected_adapter, "Learner adapter differs from collection")
    deviation = 0.0
    model.eval()
    with torch.no_grad():
        for decision, _, behavior, _ in batch:
            current = scorer.log_policy(decision).float().tolist()
            recorded = behavior["candidate_log_probs"]
            _require(
                len(current) == len(recorded)
                and all(math.isfinite(value) for value in [*current, *recorded]),
                "Nonfinite or misaligned behavior log-probabilities",
            )
            deviation = max(deviation, *(abs(a - b) for a, b in zip(current, recorded)))
    _require(deviation <= tolerance, f"Recomputed behavior log-probabilities differ: {deviation}")
    signal = [item for item in batch if item[3] != 0]
    result = {
        "decisions": len(batch),
        "signal_decisions": len(signal),
        "max_behavior_deviation": deviation,
        "adapter_before_sha256": tensor_hash(before),
        "updated": False,
    }
    if not signal:
        result["adapter_after_sha256"] = result["adapter_before_sha256"]
        return result
    model.train()
    optimizer.zero_grad(set_to_none=True)
    objective = 0.0
    for decision, chosen, _, advantage in signal:
        log_prob = scorer.log_policy(decision)[decision.candidates.index(chosen)]
        loss = -advantage * log_prob / len(batch)
        _require(bool(torch.isfinite(loss)), "Nonfinite policy-gradient loss")
        objective += float(loss.detach())
        loss.backward()
    _require(
        all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in trainable),
        "Nonfinite adapter gradient",
    )
    norm = torch.nn.utils.clip_grad_norm_(trainable, 1.0)
    _require(bool(torch.isfinite(norm)) and float(norm) > 0, "No finite nonzero adapter gradient")
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    model.eval()
    after = _adapter(model)
    changed = sum(int((before[key] != value).sum()) for key, value in after.items())
    _require(changed > 0 and _finite(after), "Update did not change finite adapter tensors")
    kl = 0.0
    with torch.no_grad():
        for decision, _, behavior, _ in batch:
            new = scorer.log_policy(decision).float().tolist()
            old = behavior["candidate_log_probs"]
            kl += sum(math.exp(a) * (a - b) for a, b in zip(old, new))
    return {
        **result,
        "updated": True,
        "loss": objective,
        "gradient_norm": float(norm),
        "changed_elements": changed,
        "adapter_after_sha256": tensor_hash(after),
        "mean_behavior_to_updated_kl": kl / len(batch),
    }


def _load_trainable(declaration: dict):
    from peft import PeftModel, get_peft_model_state_dict
    from safetensors.torch import load_file
    from transformers import AutoModelForCausalLM, AutoTokenizer

    _require(torch.cuda.is_available(), "Language RL requires CUDA and the llm extra")
    torch.cuda.set_per_process_memory_fraction(0.70)
    snapshot = declaration["base"]["directory"]
    tokenizer = AutoTokenizer.from_pretrained(
        snapshot, local_files_only=True, trust_remote_code=False
    )
    model = AutoModelForCausalLM.from_pretrained(
        snapshot,
        local_files_only=True,
        dtype=torch.bfloat16,
        device_map={"": "cuda:0"},
        attn_implementation="sdpa",
        trust_remote_code=False,
    )
    directory = declaration["adapter"]["directory"]
    model = PeftModel.from_pretrained(model, directory, is_trainable=True, local_files_only=True)
    _verify_adapter_tensors(
        get_peft_model_state_dict(model),
        load_file(str(Path(directory) / "adapter_model.safetensors"), device="cpu"),
    )
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    trainable = [name for name, p in model.named_parameters() if p.requires_grad]
    _require(
        trainable and all("lora_" in name for name in trainable), "Unexpected trainable tensor"
    )
    return model, tokenizer


def _save_adapter(model, directory: Path, base: Path, provenance: dict) -> dict:
    model.save_pretrained(directory)
    declaration = create_declaration(base, adapter_directory=directory, provenance=provenance)
    path = directory.parent / "policy.json"
    path.write_text(json.dumps(declaration, indent=2, sort_keys=True) + "\n")
    return {"declaration": str(path), "declaration_sha256": file_sha256(path)}


def train_language_rl(output: Path, config: dict) -> dict:
    """Run the declared iterations; one process owns the GPU lease and each game."""
    output = Path(output).resolve()
    _require(not output.exists(), "RL output already exists")
    config = validate_config(config)
    started = time.time()
    initial = Path(config["initial_declaration"])
    declaration = _read(initial)
    validate_declaration(declaration)
    _require(declaration["adapter"] is not None, "RL starts from a supervised adapter")
    catalog = load_catalog(Path(config["catalog"]))
    _require(len(catalog["scenarios"]) <= 10, "At most ten scenarios keep seeds distinct")
    job = {
        "schema_version": 1,
        "version": VERSION,
        "reward": REWARD,
        "scoring": SCORING,
        "config": config,
        "deadline_unix": started + config["time_budget_seconds"],
        "source": _source(),
        "dependencies": _dependencies(),
        "initial_declaration_sha256": file_sha256(initial),
        "catalog_sha256": file_sha256(Path(config["catalog"])),
        "scenarios": [
            {key: item[key] for key in ("id", "game_seed", "expected_start_sha256")}
            for item in catalog["scenarios"]
        ],
    }
    output.mkdir(parents=True)
    write_json(output / "job.json", job)
    summary = {
        "status": "running",
        "iterations": [],
        "job_sha256": file_sha256(output / "job.json"),
    }
    base = Path(declaration["base"]["directory"])
    with gpu_lease():
        model, tokenizer = _load_trainable(declaration)
        scorer = Scorer(model, tokenizer, config["temperature"])
        trainable = [p for p in model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(trainable, lr=config["learning_rate"], weight_decay=0.01)
        adapter_sha = tensor_hash(_adapter(model))
        summary["initial_adapter_sha256"] = adapter_sha
        try:
            for iteration in range(config["iterations"]):
                record = _iteration(output, job, scorer, optimizer, iteration, adapter_sha)
                summary["iterations"].append(record)
                write_json(output / "training.json", summary)
                if record["status"] != "completed":
                    summary["status"] = record["status"]
                    break
                adapter_sha = record["update"]["adapter_after_sha256"]
                target = output / f"iteration-{iteration:03d}" / "adapter"
                record["export"] = _save_adapter(
                    model,
                    target,
                    base,
                    {
                        "trainer_version": VERSION,
                        "job_sha256": summary["job_sha256"],
                        "source_revision": job["source"]["revision"],
                        "initial_declaration_sha256": job["initial_declaration_sha256"],
                        "iterations_completed": iteration + 1,
                        "adapter_sha256": adapter_sha,
                        "scope": "Outcome-based development post-training; no gameplay claim",
                    },
                )
                write_json(output / "training.json", summary)
            else:
                summary["status"] = "completed"
        except BaseException as error:
            summary.update(status="stopped", error=f"{type(error).__name__}: {error}")
            raise
        finally:
            summary["elapsed_seconds"] = time.time() - started
            write_json(output / "training.json", summary)
            del optimizer, scorer, model
            torch.cuda.empty_cache()
    return summary


def _iteration(output, job, scorer, optimizer, iteration, adapter_sha) -> dict:
    config = job["config"]
    directory = output / f"iteration-{iteration:03d}"
    directory.mkdir()
    record = {"iteration": iteration, "adapter_before_sha256": adapter_sha, "groups": []}
    for index, scenario in enumerate(job["scenarios"]):
        group = []
        for member in range(config["group_size"]):
            remaining = job["deadline_unix"] - time.time()
            if remaining < 180 + UPDATE_RESERVE_SECONDS:
                record["status"] = "budget_exhausted"
                return record
            run = directory / f"{scenario['id']}-{member:02d}"
            seed = policy_seed(config, iteration, index, member)
            manifest = rollout(
                run,
                {
                    "policy": "language_sample",
                    "game_seed": scenario["game_seed"],
                    "policy_seed": seed,
                    "episodes": 1,
                    "expected_start_sha256": scenario["expected_start_sha256"],
                    "max_actions": 500,
                    "episode_timeout": 180,
                    "bridge_timeout": 45,
                    "policy_artifact": {
                        "type": "language_sample",
                        "trainer_version": VERSION,
                        "job_sha256": file_sha256(output / "job.json"),
                        "iteration": iteration,
                        "adapter_sha256": adapter_sha,
                        "temperature": config["temperature"],
                    },
                },
                policy_factory=lambda value: CandidateSampler(
                    scorer,
                    seed=value,
                    temperature=config["temperature"],
                    model_sha256=adapter_sha,
                ),
            )
            entry = {"run": str(run), "policy_seed": seed, "status": manifest["status"]}
            group.append(entry)
            if manifest["status"] != "completed":
                record["groups"].append({"scenario_id": scenario["id"], "members": group})
                record["status"] = "collection_failure"
                return record
        record["groups"].append({"scenario_id": scenario["id"], "members": group})
    batch = []
    for group in record["groups"]:
        episodes = [sampled_decisions(Path(item["run"])) for item in group["members"]]
        rewards = [episode_reward(episode) for episode, _ in episodes]
        advantages = group_advantages(rewards)
        for item, (episode, decisions), reward, advantage in zip(
            group["members"], episodes, rewards, advantages, strict=True
        ):
            _require(
                all(behavior["model_sha256"] == adapter_sha for _, _, behavior in decisions),
                "Collected behavior came from a different adapter",
            )
            item.update(
                outcome=episode["status"],
                ending_hp=episode["ending_hp"],
                reward=reward,
                advantage=advantage,
                decisions=len(decisions),
            )
            batch.extend((d, chosen, behavior, advantage) for d, chosen, behavior in decisions)
    record["update"] = reinforce_step(scorer, optimizer, batch, expected_adapter=adapter_sha)
    record["status"] = "completed"
    write_json(directory / "iteration.json", record)
    return record


def _audit_iteration(output: Path, job: dict, record: dict, adapter: str) -> None:
    config = job["config"]
    iteration = record["iteration"]
    directory = output / f"iteration-{iteration:03d}"
    _require(
        [group["scenario_id"] for group in record["groups"]]
        == [scenario["id"] for scenario in job["scenarios"]],
        "Iteration does not cover every declared scenario in order",
    )
    decisions_total = 0
    for index, (scenario, group) in enumerate(zip(job["scenarios"], record["groups"], strict=True)):
        members = group["members"]
        _require(len(members) == config["group_size"], "Scenario group has missing members")
        episodes = []
        for member, item in enumerate(members):
            seed = policy_seed(config, iteration, index, member)
            run = directory / f"{scenario['id']}-{member:02d}"
            _require(
                item["policy_seed"] == seed and Path(item["run"]) == run,
                "Member seed or run path differs from the declared schedule",
            )
            run_config = _read(run / "manifest.json")["config"]
            _require(
                run_config["game_seed"] == scenario["game_seed"]
                and run_config["expected_start_sha256"] == scenario["expected_start_sha256"]
                and run_config["policy_seed"] == seed
                and run_config["policy_artifact"]
                == {
                    "type": "language_sample",
                    "trainer_version": VERSION,
                    "job_sha256": file_sha256(output / "job.json"),
                    "iteration": iteration,
                    "adapter_sha256": adapter,
                    "temperature": config["temperature"],
                },
                "Collected run configuration differs from the iteration",
            )
            episode, decisions = sampled_decisions(run)
            rng = random.Random(seed)
            _require(
                all(
                    behavior["draw"] == rng.random()
                    and behavior["model_sha256"] == adapter
                    and behavior["temperature"] == config["temperature"]
                    for _, _, behavior in decisions
                ),
                "Behavior draws, adapter or temperature differ from the seeded schedule",
            )
            episodes.append((item, episode, decisions))
        rewards = [episode_reward(episode) for _, episode, _ in episodes]
        for (item, _, decisions), reward, advantage in zip(
            episodes, rewards, group_advantages(rewards), strict=True
        ):
            _require(
                item["reward"] == reward
                and item["advantage"] == advantage
                and item["decisions"] == len(decisions),
                "Recorded reward, advantage or decision count differs from audited evidence",
            )
            decisions_total += len(decisions)
    update = record["update"]
    _require(update["decisions"] == decisions_total, "Update did not use the whole batch")
    _require(
        update["adapter_before_sha256"] == adapter
        and update["updated"] == (update["adapter_after_sha256"] != adapter),
        "Update identity disagrees with the adapter chain",
    )
    export = record["export"]
    _require(
        file_sha256(Path(export["declaration"])) == export["declaration_sha256"],
        "Exported declaration changed",
    )
    from safetensors.torch import load_file

    saved = load_file(str(directory / "adapter/adapter_model.safetensors"))
    _require(
        tensor_hash(saved) == update["adapter_after_sha256"],
        "Saved adapter differs from the committed update",
    )


def audit_language_rl(output: Path) -> dict:
    """Read-only recheck of saved evidence; loads no model and takes no GPU lease."""
    from safetensors.torch import load_file

    output = Path(output).resolve()
    errors = []
    job = _read(output / "job.json")
    summary = _read(output / "training.json")
    adapter = summary["initial_adapter_sha256"]
    try:
        _require(summary["job_sha256"] == file_sha256(output / "job.json"), "Job file changed")
        initial = Path(job["config"]["initial_declaration"])
        _require(
            file_sha256(initial) == job["initial_declaration_sha256"],
            "Initial declaration changed",
        )
        directory = Path(_read(initial)["adapter"]["directory"])
        _require(
            tensor_hash(load_file(str(directory / "adapter_model.safetensors"))) == adapter,
            "Initial adapter tensors differ from the trained starting point",
        )
        _require(
            [record["iteration"] for record in summary["iterations"]]
            == list(range(len(summary["iterations"]))),
            "Iterations are missing or out of order",
        )
    except (OSError, ValueError, KeyError) as error:
        errors.append(f"job: {error}")
    for record in summary["iterations"]:
        try:
            _require(record["adapter_before_sha256"] == adapter, "Adapter chain is broken")
            if record["status"] != "completed":
                continue
            _audit_iteration(output, job, record, adapter)
            adapter = record["update"]["adapter_after_sha256"]
        except (OSError, ValueError, KeyError) as error:
            errors.append(f"iteration {record['iteration']}: {error}")
    return {"valid": not errors, "errors": errors, "final_adapter_sha256": adapter}
