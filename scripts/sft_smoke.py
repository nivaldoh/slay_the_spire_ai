"""Minimal local LoRA fine-tuning smoke test of a gameai.sft dataset (llm extra, CUDA only).

    uv run --locked --extra llm python scripts/sft_smoke.py DATASET --output DIR

Trains a bf16 LoRA on the attention and MLP projections of the Qwen3-0.6B snapshot that
src/spire/language/policy.py pins (cached under ~/.cache/spire-models), batch 1, with the
loss on the assistant tokens only. Rows over --max-tokens, or whose reply the chat
template renders differently, are skipped and counted. The evaluation rows are the first
usable validation rows (train rows when there are none). Their mean loss per assistant
token is measured before training and again with the saved adapter, reloaded and verified
on a fresh base; then a few of them are greedily decoded and scored for JSON validity,
exact match after JSON normalisation, and action match (equal once the top-level
free-text keys "reason" and "notes" are dropped). It refuses to run while either game
runs. It checks the pipeline end to end; it is not a training recipe, and its numbers are
not results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from collections import Counter
from pathlib import Path
from statistics import mean

from gameai.provenance import git
from gameai.windows_game import conflicting_games
from spire.engine import runtime as spire_runtime
from spire.language.policy import MODEL_ID, REVISION, _load_adapter, dependency_versions, gpu_lease
from twwarhammer3.engine import runtime as wh3_runtime

BASE = (Path.home() / ".cache/spire-models" / f"models--{MODEL_ID.replace('/', '--')}"
        / "snapshots" / REVISION)
LORA = {"r": 8, "lora_alpha": 16, "lora_dropout": 0.0, "bias": "none", "task_type": "CAUSAL_LM",
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj",
                           "down_proj"]}
FREE_TEXT = ("reason", "notes")  # both games' top-level free-text reply keys


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def read_split(dataset: Path, split: str) -> list[tuple[dict, str]]:
    """(chat, row id) pairs of one split, from the chats and their aligned sidecar."""
    ids = [row["id"] for row in read_jsonl(dataset / f"{split}-rows.jsonl")]
    return list(zip(read_jsonl(dataset / f"{split}.jsonl"), ids, strict=True))


def games_running() -> str:
    """Process ids of a running Slay the Spire or WH3 game, which needs the GPU to itself."""
    return ", ".join(str(process["ProcessId"]) for runtime in (spire_runtime, wh3_runtime)
                     for process in conflicting_games(Path(runtime.WINDOWS_GAME_DIR),
                                                      runtime.CONFLICTS))


def encode(tokenizer, example: dict, max_tokens: int) -> tuple[list[int], list[int]] | str:
    """Prompt ids (system and user, opened for the reply) and target ids (reply, end of turn),
    or why the row is skipped."""
    messages = example["messages"]
    thinking = ({"enable_thinking": False} if "enable_thinking" in (tokenizer.chat_template or "")
                else {})
    prefix = tokenizer.apply_chat_template(messages[:2], tokenize=False,
                                           add_generation_prompt=True, **thinking)
    reply = messages[2]["content"] + tokenizer.eos_token
    # The trained text must be what the template renders for the whole chat (Qwen's strips
    # a reply's leading newlines, for one).
    if not tokenizer.apply_chat_template(messages, tokenize=False).startswith(prefix + reply):
        return "template"
    prompt = tokenizer(prefix, add_special_tokens=False)["input_ids"]
    target = tokenizer(reply, add_special_tokens=False)["input_ids"]
    return "max_tokens" if len(prompt) + len(target) > max_tokens else (prompt, target)


def usable(tokenizer, pairs: list, max_tokens: int, skipped: Counter) -> list[tuple]:
    """(example, row id, prompt ids, target ids) of the rows that encode; counts the rest."""
    kept = []
    for example, row_id in pairs:
        value = encode(tokenizer, example, max_tokens)
        if isinstance(value, str):
            skipped[value] += 1
        else:
            kept.append((example, row_id, *value))
    return kept


def canonical(text: str, drop=()) -> str | None:
    """Sorted compact JSON without the top-level keys in ``drop``; None when not JSON."""
    try:
        value = json.loads(text)
    except ValueError:
        return None
    if isinstance(value, dict):
        value = {key: item for key, item in value.items() if key not in drop}
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def score(text: str, reference: str) -> dict:
    value = canonical(text)
    return {"json_valid": value is not None,
            "exact_match": value is not None and value == canonical(reference),
            "action_match": value is not None
            and canonical(text, FREE_TEXT) == canonical(reference, FREE_TEXT)}


def token_loss(rows: list[tuple], loss) -> float | None:
    """Mean loss per target token of usable rows; ``loss(prompt, target)`` is one row's mean."""
    tokens = sum(len(target) for *_, target in rows)
    total = sum(loss(prompt, target) * len(target) for _, _, prompt, target in rows)
    return total / tokens if tokens else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dataset", type=Path, help="a gameai.sft output directory")
    parser.add_argument("--output", type=Path, required=True, help="new directory")
    parser.add_argument("--base", type=Path, default=BASE, help="local model snapshot")
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--loss-rows", type=int, default=64,
                        help="evaluation rows whose loss is measured before and after training")
    parser.add_argument("--eval-rows", type=int, default=8, help="evaluation rows to decode")
    parser.add_argument("--max-new-tokens", type=int, default=1024)
    args = parser.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise SystemExit("The smoke test needs CUDA and the llm extra; it never runs on CPU")
    if args.output.exists():
        raise SystemExit(f"Output already exists: {args.output}")
    if pids := games_running():
        raise SystemExit(f"A game is running (process {pids}); the GPU stays idle meanwhile")
    manifest = args.dataset / "manifest.json"
    if json.loads(manifest.read_text())["arguments"]["reasoning"]:
        raise SystemExit("Only non-thinking datasets are supported; rebuild without --reasoning")
    pairs = {split: read_split(args.dataset, split) for split in ("train", "validation")}
    split = "validation" if pairs["validation"] else "train"
    if not pairs["train"]:
        raise SystemExit("The dataset has no train rows")

    def load():
        return AutoModelForCausalLM.from_pretrained(
            args.base, local_files_only=True, dtype=torch.bfloat16, device_map={"": "cuda:0"},
            attn_implementation="sdpa", trust_remote_code=False)

    def loss(model, prompt, target):
        ids = torch.tensor([prompt + target], device="cuda:0")
        labels = torch.tensor([[-100] * len(prompt) + target], device="cuda:0")
        return model(input_ids=ids, labels=labels).loss

    def eval_loss(model):
        with torch.inference_mode():
            return token_loss(evals, lambda prompt, target: loss(model, prompt, target).item())

    with gpu_lease():
        torch.manual_seed(args.seed)
        tokenizer = AutoTokenizer.from_pretrained(args.base, local_files_only=True,
                                                  trust_remote_code=False)
        skipped = {"train": Counter(), "eval": Counter()}
        examples = usable(tokenizer, pairs["train"], args.max_tokens, skipped["train"])
        evals = usable(tokenizer, pairs[split], args.max_tokens, skipped["eval"])[:args.loss_rows]
        tests = evals[:args.eval_rows]
        if not examples:
            raise SystemExit(f"No train row fits: skipped {dict(skipped['train'])}")
        args.output.mkdir(parents=True)
        model = get_peft_model(load(), LoraConfig(**LORA))
        model.config.use_cache = False
        loss_before = eval_loss(model.eval())  # a new adapter leaves the base model unchanged
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                                      lr=args.lr)
        order = list(range(len(examples)))
        random.Random(args.seed).shuffle(order)
        model.train()
        losses, started = [], time.monotonic()
        for step in range(args.steps):
            _, _, prompt, target = examples[order[step % len(order)]]
            value = loss(model, prompt, target)
            value.backward()
            optimizer.step()
            optimizer.zero_grad()
            losses.append(value.item())
            print(f"step {step + 1}/{args.steps} loss {losses[-1]:.4f}", flush=True)
        train_seconds = time.monotonic() - started
        model.save_pretrained(args.output / "adapter")
        del model, optimizer
        torch.cuda.empty_cache()

        model = _load_adapter(load(), str(args.output / "adapter")).eval()  # verifies tensors
        predictions, started = [], time.monotonic()
        loss_after = eval_loss(model)
        with torch.inference_mode():
            for example, row_id, prompt, _ in tests:
                ids = torch.tensor([prompt], device="cuda:0")
                output = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                                        max_new_tokens=args.max_new_tokens, do_sample=False,
                                        pad_token_id=tokenizer.pad_token_id)
                text = tokenizer.decode(output[0, len(prompt):], skip_special_tokens=True)
                predictions.append({"id": row_id, "text": text,
                                    **score(text, example["messages"][2]["content"])})
        device = torch.cuda.get_device_name(0)

    first, last = mean(losses[:5]), mean(losses[-5:])
    count = len(predictions)
    metrics = {
        "base": str(args.base.resolve()), "dataset": str(args.dataset.resolve()),
        "dataset_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "revision": git("rev-parse", "HEAD").strip(), "dependencies": dependency_versions(),
        "device": device, "seed": args.seed, "steps": args.steps, "lr": args.lr, "lora": LORA,
        "train_rows": len(examples), "skipped": {k: dict(v) for k, v in skipped.items()},
        "losses": losses, "first5_mean": first,
        "last5_mean": last, "loss_fell": last < first,
        "seconds": {"train": train_seconds, "eval": time.monotonic() - started},
        "eval_loss": {"split": split, "rows": len(evals),
                      "tokens": sum(len(target) for *_, target in evals),
                      "before": loss_before, "after": loss_after},
        "eval": {"split": split, "rows": count,
                 **{f"{key}_rate": sum(p[key] for p in predictions) / count if count else None
                    for key in ("json_valid", "exact_match", "action_match")},
                 "predictions": predictions},
    }
    (args.output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps({k: metrics[k] for k in ("first5_mean", "last5_mean", "eval_loss")}
                     | {k: v for k, v in metrics["eval"].items() if k != "predictions"}))


if __name__ == "__main__":
    main()
