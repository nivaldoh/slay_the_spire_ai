"""One bounded, synthetic CUDA LoRA update; never launches a game or downloads weights."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

MODEL_ID = "Qwen/Qwen3-0.6B"
REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
WEIGHTS_SHA256 = "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b"
DEPENDENCIES = ("torch", "transformers", "peft", "accelerate", "safetensors")


def write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def available_mib() -> float:
    fields = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    return int(fields["MemAvailable"].split()[0]) / 1024


def gpu_used_mib() -> float:
    output = subprocess.check_output(
        ["/usr/lib/wsl/lib/nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        text=True, timeout=3,
    )
    return float(output.splitlines()[0])


def synthetic_messages() -> list[dict]:
    # Explicitly synthetic, not a recorded engine observation or demonstration.
    state = {
        "player": {"hp": 40, "max_hp": 80, "block": 0, "energy": 1, "powers": []},
        "turn": 2,
        "relics": ["Burning Blood"],
        "card_table": [
            {"name": "Strike", "cost": 1, "damage": 6, "upgraded": False},
            {"name": "Defend", "cost": 1, "block": 5, "upgraded": False},
        ],
        "hand": [0, 1], "draw": [0, 0, 1], "discard": [0, 1], "exhaust": [],
        "enemies": [{"name": "Cultist", "hp": 6, "block": 0, "intent": "ATTACK",
                     "damage": 6, "hits": 1, "powers": []}],
        "choices": [["play", 0, 0], ["play", 1, None], ["end", None, None]],
    }
    return [
        {"role": "system", "content": "Choose one listed legal Slay the Spire action. "
         "Prefer winning, then remaining health. Piles contain card_table indexes; hand and "
         "enemy indexes are zero-based. Choices are [kind,hand_index,target_index]. "
         'Reply only with {"a":N}, where N is the zero-based choice index. No explanation.'},
        {"role": "user", "content": json.dumps(state, separators=(",", ":"))},
    ]


def worker(args) -> None:
    import torch
    from peft import LoraConfig, get_peft_model, get_peft_model_state_dict
    from safetensors.torch import load_file
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(1)
    torch.manual_seed(0)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; this smoke requires the llm extra")
    torch.cuda.set_per_process_memory_fraction(0.70)
    torch.cuda.reset_peak_memory_stats()
    metrics = {"scope": "synthetic computational smoke; no gameplay evaluation",
               "pid": os.getpid(), "steps": [], "synthetic": True}

    def record(stage, **fields):
        torch.cuda.synchronize()
        memory = available_mib()
        peak = torch.cuda.max_memory_reserved() / 2**20
        metrics.update(fields)
        metrics["steps"].append({"stage": stage, "available_mib": memory,
                                 "cuda_allocated_mib": torch.cuda.memory_allocated() / 2**20,
                                 "cuda_reserved_mib": torch.cuda.memory_reserved() / 2**20})
        metrics["cuda_peak_reserved_mib"] = peak
        metrics["cuda_peak_allocated_mib"] = torch.cuda.max_memory_allocated() / 2**20
        write(args.output / "metrics.json", metrics)
        print(json.dumps({"stage": stage, **metrics["steps"][-1]}), flush=True)
        if memory < args.min_available_mib or peak >= args.max_gpu_gib * 1024:
            raise RuntimeError("Resource bound reached")

    record("before_load")
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, local_files_only=True)
    messages = synthetic_messages()
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False,
    )
    prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    target = '{"a":0}'
    target_ids = tokenizer(target, add_special_tokens=False)["input_ids"] + [tokenizer.eos_token_id]
    if len(prompt_ids) + len(target_ids) > 1024 or len(target_ids) > 12:
        raise RuntimeError("Synthetic prompt or completion exceeds the fixed token budget")
    write(args.output / "synthetic-example.json", {"messages": messages, "prompt": prompt,
          "target": target, "prompt_tokens": len(prompt_ids), "target_tokens": len(target_ids)})
    start = time.monotonic()
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path, local_files_only=True, dtype=torch.bfloat16,
        device_map={"": "cuda:0"}, attn_implementation="sdpa", trust_remote_code=False,
    )
    model.eval()
    record("loaded", load_seconds=time.monotonic() - start,
           prompt_tokens=len(prompt_ids), target_tokens=len(target_ids),
           model_parameters=sum(p.numel() for p in model.parameters()))
    inputs = torch.tensor([prompt_ids], device="cuda")
    start = time.monotonic()
    with torch.inference_mode():
        generated = model.generate(
            inputs, attention_mask=torch.ones_like(inputs), max_new_tokens=12,
            do_sample=False, pad_token_id=tokenizer.eos_token_id,
        )
    response = tokenizer.decode(generated[0, len(prompt_ids):], skip_special_tokens=True)
    record("generated", generation_seconds=time.monotonic() - start, response=response,
           generated_tokens=generated.shape[1] - len(prompt_ids),
           canonical_legal_response=response.strip() in {'{"a":0}', '{"a":1}', '{"a":2}'})
    del generated, inputs

    model = get_peft_model(model, LoraConfig(
        task_type="CAUSAL_LM", r=8, lora_alpha=16, lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], bias="none",
    ))
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    trainable = [p for p in model.parameters() if p.requires_grad]
    if not trainable or any("lora_" not in name for name, p in model.named_parameters()
                            if p.requires_grad):
        raise RuntimeError("Unexpected trainable base parameters")
    before = {name: tensor.detach().cpu().clone()
              for name, tensor in get_peft_model_state_dict(model).items()}
    ids = prompt_ids + target_ids
    padding = 1024 - len(ids)
    input_ids = torch.tensor([ids + [tokenizer.eos_token_id] * padding], device="cuda")
    attention = torch.tensor([[1] * len(ids) + [0] * padding], device="cuda")
    labels = torch.full_like(input_ids, -100)
    labels[0, len(prompt_ids):len(ids)] = torch.tensor(target_ids, device="cuda")
    if (labels[attention == 0] != -100).any() or (labels[0, :len(prompt_ids)] != -100).any():
        raise RuntimeError("Prompt or padding tokens entered the loss")
    optimizer = torch.optim.AdamW(trainable, lr=0.001, weight_decay=0.01)
    model.eval()
    with torch.no_grad():
        output = model(input_ids=input_ids, attention_mask=attention, labels=labels)
        logits_before = output.logits[0, len(prompt_ids) - 1:len(ids) - 1].float().cpu()
        loss_before = output.loss.item()
    del output
    record("before_update", training_sequence_tokens=1024, padding_tokens=padding,
           supervised_tokens=int((labels != -100).sum()),
           trainable_parameters=sum(p.numel() for p in trainable), loss_before=loss_before)
    model.train()
    start = time.monotonic()
    output = model(input_ids=input_ids, attention_mask=attention, labels=labels)
    loss = output.loss
    if not torch.isfinite(loss):
        raise RuntimeError("Nonfinite loss")
    loss.backward()
    if not all(p.grad is None or torch.isfinite(p.grad).all() for p in trainable):
        raise RuntimeError("Nonfinite adapter gradient")
    norm = torch.nn.utils.clip_grad_norm_(trainable, 1.0)
    if not torch.isfinite(norm) or norm.item() <= 0:
        raise RuntimeError("Missing finite nonzero gradient")
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    del output, loss
    if not all(torch.isfinite(value).all() for state in optimizer.state.values()
               for value in state.values() if isinstance(value, torch.Tensor)):
        raise RuntimeError("Nonfinite optimizer state")
    after = {name: tensor.detach().cpu().clone()
             for name, tensor in get_peft_model_state_dict(model).items()}
    changed = sum(int((before[name] != value).sum()) for name, value in after.items())
    if not changed or not all(torch.isfinite(value).all() for value in after.values()):
        raise RuntimeError("Adapter did not make a finite parameter update")
    model.eval()
    model.requires_grad_(False)
    with torch.inference_mode():
        output = model(input_ids=input_ids, attention_mask=attention, labels=labels)
        logits_after = output.logits[0, len(prompt_ids) - 1:len(ids) - 1].float().cpu()
        loss_after = output.loss.item()
    delta = (logits_after - logits_before).abs().max().item()
    if not math.isfinite(delta) or delta <= 0 or not math.isfinite(loss_after):
        raise RuntimeError("No finite post-update logits change")
    del output
    adapter = args.output / "frozen-adapter"
    model.save_pretrained(adapter, safe_serialization=True)
    saved = load_file(adapter / "adapter_model.safetensors")
    if saved.keys() != after.keys() or not all(torch.equal(saved[k], after[k]) for k in saved):
        raise RuntimeError("Saved adapter differs from the updated tensors")
    record("complete", update_seconds=time.monotonic() - start, updates=1,
           adapter_changed_elements=changed, grad_norm=norm.item(), loss_after=loss_after,
           max_logit_change=delta, finite_optimizer=True, adapter_roundtrip_exact=True,
           frozen=True, artifacts={str(p.relative_to(args.output)): digest(p)
                                   for p in adapter.iterdir() if p.is_file()})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--min-available-mib", type=float, default=700)
    parser.add_argument("--max-gpu-gib", type=float, default=10)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    for value in (args.timeout, args.min_available_mib, args.max_gpu_gib):
        if not math.isfinite(value) or value <= 0:
            parser.error("resource bounds must be positive and finite")
    if args.worker:
        worker(args)
        return 0
    if digest(args.model_path / "model.safetensors") != WEIGHTS_SHA256:
        raise ValueError("Pinned base-model content hash mismatch")
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    source_files = {name: digest(root / name)
                    for name in ("scripts/language_smoke.py", "pyproject.toml", "uv.lock")}
    manifest = {
        "schema_version": 1, "status": "running", "synthetic": True,
        "scope": "one computational LoRA update; no gameplay or performance claim",
        "base_model": MODEL_ID, "base_revision": REVISION, "base_weights_sha256": WEIGHTS_SHA256,
        "base_snapshot": str(args.model_path.resolve()),
        "base_files": {p.name: WEIGHTS_SHA256 if p.name == "model.safetensors" else digest(p)
                       for p in args.model_path.iterdir() if p.is_file()},
        "prompt_format": "synthetic-legal-choice-v1",
        "decoder": {"enable_thinking": False, "max_new_tokens": 12, "do_sample": False},
        "training": {"method": "LoRA", "rank": 8, "alpha": 16, "dropout": 0,
                     "targets": ["q_proj", "k_proj", "v_proj", "o_proj"],
                     "learning_rate": 0.001, "optimizer": "AdamW", "updates": 1,
                     "weight_decay": 0.01, "gradient_clip_norm": 1.0, "seed": 0,
                     "loss": "completion_and_eos_only", "batch_size": 1,
                     "padded_sequence_tokens": 1024},
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "source_status": subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root, text=True),
        "source_files": source_files, "command": [sys.executable, *sys.argv],
        "dependencies": {name: importlib.metadata.version(name) for name in DEPENDENCIES},
        "limits": {"timeout_seconds": args.timeout, "min_available_mib": args.min_available_mib,
                   "max_gpu_gib": args.max_gpu_gib},
    }
    write(args.output / "manifest.json", manifest)
    environment = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                   "HF_HUB_DISABLE_TELEMETRY": "1", "TOKENIZERS_PARALLELISM": "false"}
    started = time.monotonic()
    failure = None
    with (args.output / "worker.log").open("w") as log, (
        args.output / "resources.jsonl"
    ).open("w", buffering=1) as samples:
        process = subprocess.Popen([sys.executable, *sys.argv, "--worker"],
                                   stdout=log, stderr=subprocess.STDOUT, env=environment)
        manifest["worker_pid"] = process.pid
        write(args.output / "manifest.json", manifest)
        print(json.dumps({"worker_pid": process.pid, "output": str(args.output)}), flush=True)
        try:
            while process.poll() is None:
                memory, gpu = available_mib(), gpu_used_mib()
                sample = {"elapsed_seconds": time.monotonic() - started,
                          "available_mib": memory, "gpu_total_used_mib": gpu}
                samples.write(json.dumps(sample) + "\n")
                if memory < args.min_available_mib:
                    raise RuntimeError("WSL available RAM fell below minimum")
                if gpu >= args.max_gpu_gib * 1024:
                    raise RuntimeError("Total GPU usage reached the conservative bound")
                if sample["elapsed_seconds"] >= args.timeout:
                    raise TimeoutError("GPU smoke deadline reached")
                time.sleep(0.5)
        except BaseException as exc:
            failure = f"{type(exc).__name__}: {exc}"
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
    manifest.update(status="completed" if process.returncode == 0 and not failure else "failed",
                    exit_code=process.returncode, error=failure,
                    elapsed_seconds=time.monotonic() - started)
    if any(digest(root / name) != value for name, value in source_files.items()):
        manifest.update(status="failed", error="Smoke source changed during execution")
    final_base_files = {p.name: digest(p) for p in args.model_path.iterdir() if p.is_file()}
    if final_base_files != manifest["base_files"]:
        manifest.update(status="failed", error="Base-model snapshot changed during execution")
    else:
        manifest["base_snapshot_unchanged"] = True
    metrics = args.output / "metrics.json"
    if metrics.exists():
        manifest["metrics_sha256"] = digest(metrics)
        computed = json.loads(metrics.read_text())
        if (computed.get("steps", [{}])[-1].get("stage") != "complete"
                or computed.get("updates") != 1):
            manifest.update(status="failed", error="Worker did not record one complete update")
        if "artifacts" in computed:
            manifest["adapter_directory"] = str((args.output / "frozen-adapter").resolve())
            manifest["adapter_files"] = computed["artifacts"]
            if any(digest(args.output / name) != value
                   for name, value in computed["artifacts"].items()):
                manifest.update(status="failed", error="Frozen adapter changed after worker exit")
    else:
        manifest.update(status="failed", error="Worker metrics are missing")
    write(args.output / "manifest.json", manifest)
    print(json.dumps(manifest), flush=True)
    return 0 if manifest["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
