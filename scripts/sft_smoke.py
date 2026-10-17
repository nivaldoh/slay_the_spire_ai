"""Minimal local LoRA fine-tuning smoke test of a gameai.sft dataset (llm extra, CUDA only).

    uv run --locked --extra llm python scripts/sft_smoke.py DATASET --output DIR

Trains a bf16 LoRA on the attention and MLP projections of the Qwen3-0.6B snapshot that
src/spire/language/policy.py pins (cached under ~/.cache/spire-models), batch 1, with the
loss on the assistant tokens only. Saves the adapter, reloads it onto a fresh base, then
greedily decodes a few validation rows (train rows when there are none) and scores JSON
validity and exact match after JSON normalisation. It checks the pipeline end to end; it
is not a training recipe, and its numbers are not results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from pathlib import Path
from statistics import mean

from spire.language.policy import MODEL_ID, REVISION, gpu_lease

BASE = (Path.home() / ".cache/spire-models" / f"models--{MODEL_ID.replace('/', '--')}"
        / "snapshots" / REVISION)
LORA = {"r": 8, "lora_alpha": 16, "lora_dropout": 0.0, "bias": "none", "task_type": "CAUSAL_LM",
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj",
                           "down_proj"]}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def encode(tokenizer, example: dict, max_tokens: int) -> tuple[list[int], list[int]]:
    """Prompt ids (system and user, opened for the reply) and target ids (reply, end of turn)."""
    messages = example["messages"]
    thinking = ({"enable_thinking": False} if "enable_thinking" in (tokenizer.chat_template or "")
                else {})
    prefix = tokenizer.apply_chat_template(messages[:2], tokenize=False,
                                           add_generation_prompt=True, **thinking)
    reply = messages[2]["content"] + tokenizer.eos_token
    # The trained text must be what the template renders for the whole chat.
    if not tokenizer.apply_chat_template(messages, tokenize=False).startswith(prefix + reply):
        raise SystemExit("The chat template does not render prompt + reply + end of turn")
    prompt = tokenizer(prefix, add_special_tokens=False)["input_ids"]
    target = tokenizer(reply, add_special_tokens=False)["input_ids"]
    if len(prompt) + len(target) > max_tokens:
        raise SystemExit(f"A row has {len(prompt) + len(target)} tokens, over --max-tokens "
                         f"{max_tokens}; rebuild the dataset with gameai.sft --max-tokens")
    return prompt, target


def canonical(text: str) -> str | None:
    try:
        return json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"))
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dataset", type=Path, help="a gameai.sft output directory")
    parser.add_argument("--output", type=Path, required=True, help="new directory")
    parser.add_argument("--base", type=Path, default=BASE, help="local model snapshot")
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--eval-rows", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=1024)
    args = parser.parse_args()

    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise SystemExit("The smoke test needs CUDA and the llm extra; it never runs on CPU")
    manifest = args.dataset / "manifest.json"
    if json.loads(manifest.read_text())["arguments"]["reasoning"]:
        raise SystemExit("Only non-thinking datasets are supported; rebuild without --reasoning")
    train = read_jsonl(args.dataset / "train.jsonl")
    split = "validation" if read_jsonl(args.dataset / "validation.jsonl") else "train"
    held = read_jsonl(args.dataset / f"{split}.jsonl")[:args.eval_rows]
    held_ids = [row["id"] for row in read_jsonl(args.dataset / f"{split}-rows.jsonl")]
    if not train:
        raise SystemExit("The dataset has no train rows")
    args.output.mkdir(parents=True)  # refuses an existing directory

    def load():
        return AutoModelForCausalLM.from_pretrained(
            args.base, local_files_only=True, dtype=torch.bfloat16, device_map={"": "cuda:0"},
            attn_implementation="sdpa", trust_remote_code=False)

    with gpu_lease():
        torch.manual_seed(args.seed)
        tokenizer = AutoTokenizer.from_pretrained(args.base, local_files_only=True,
                                                  trust_remote_code=False)
        examples = [encode(tokenizer, example, args.max_tokens) for example in train]
        tests = [encode(tokenizer, example, args.max_tokens) for example in held]
        model = get_peft_model(load(), LoraConfig(**LORA))
        model.config.use_cache = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                                      lr=args.lr)
        order = list(range(len(examples)))
        random.Random(args.seed).shuffle(order)
        model.train()
        losses, started = [], time.monotonic()
        for step in range(args.steps):
            prompt, target = examples[order[step % len(order)]]
            ids = torch.tensor([prompt + target], device="cuda:0")
            labels = torch.tensor([[-100] * len(prompt) + target], device="cuda:0")
            loss = model(input_ids=ids, labels=labels).loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            losses.append(loss.item())
            print(f"step {step + 1}/{args.steps} loss {losses[-1]:.4f}", flush=True)
        train_seconds = time.monotonic() - started
        model.save_pretrained(args.output / "adapter")
        del model, optimizer
        torch.cuda.empty_cache()

        model = PeftModel.from_pretrained(load(), args.output / "adapter").eval()
        predictions, started = [], time.monotonic()
        with torch.inference_mode():
            for (prompt, _), example, row_id in zip(tests, held, held_ids):
                ids = torch.tensor([prompt], device="cuda:0")
                output = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                                        max_new_tokens=args.max_new_tokens, do_sample=False,
                                        pad_token_id=tokenizer.pad_token_id)
                text = tokenizer.decode(output[0, len(prompt):], skip_special_tokens=True)
                value = canonical(text)
                predictions.append({"id": row_id, "text": text, "json_valid": value is not None,
                                    "exact_match": value is not None and value == canonical(
                                        example["messages"][2]["content"])})
        device = torch.cuda.get_device_name(0)

    first, last = mean(losses[:5]), mean(losses[-5:])
    count = len(predictions)
    metrics = {
        "base": str(args.base.resolve()), "dataset": str(args.dataset.resolve()),
        "dataset_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "device": device, "seed": args.seed, "steps": args.steps, "lr": args.lr, "lora": LORA,
        "train_rows": len(examples), "losses": losses, "first5_mean": first,
        "last5_mean": last, "loss_fell": last < first,
        "seconds": {"train": train_seconds, "eval": time.monotonic() - started},
        "eval": {"split": split, "rows": count,
                 "json_valid_rate": sum(p["json_valid"] for p in predictions) / count
                 if count else None,
                 "exact_match_rate": sum(p["exact_match"] for p in predictions) / count
                 if count else None,
                 "predictions": predictions},
    }
    (args.output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps({k: metrics[k] for k in ("first5_mean", "last5_mean", "loss_fell")}
                     | {k: v for k, v in metrics["eval"].items() if k != "predictions"}))


if __name__ == "__main__":
    main()
