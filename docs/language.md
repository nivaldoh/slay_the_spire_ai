# Local language-policy feasibility and computational smoke

The first language-model experiment is local pretrained-policy imitation. It is
separate from the randomly initialized PPO policy. No gameplay capability follows
from loading a model or changing an adapter, and the synthetic smoke is not an
evaluation episode or an engine demonstration.

The primary candidate is
[`Qwen/Qwen3-0.6B`](https://huggingface.co/Qwen/Qwen3-0.6B), pinned to revision
`c1899de289a04d12100db370d81485cdf75e47ca`. Its Apache-2.0 repository is public
and ungated. The pinned BF16 weight file is 1,503,300,328 bytes, SHA-256
`f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`;
weights, tokenizer and configuration total about 1.52 GB. The model card documents
native Transformers support from 4.51.0 and the `enable_thinking=False` switch.
The smoke uses that switch and generates at most 12 tokens.

A larger alternative, not downloaded, is
[`Qwen/Qwen2.5-1.5B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct),
revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`. It is also public, ungated,
Apache-2.0, uses native Transformers, and has a 3,087,467,144-byte BF16 weight
file (about 3.10 GB including tokenizer/configuration). Neither parameter count
nor weight-file size establishes peak training memory; measure a full update.

## Locked environments

`train` retains PyTorch 2.13.0 CPU. The optional `llm` extra selects CUDA 13.0
PyTorch 2.13.0, Transformers 5.19.0, PEFT 0.21.2, Accelerate 1.15.0 and
Safetensors 0.8.0. The extras are mutually exclusive, following
[uv's documented optional-dependency index routing](https://docs.astral.sh/uv/guides/integration/pytorch/#configuring-accelerators-with-optional-dependencies).
This preserves one lockfile while preventing an ambiguous CPU/CUDA selection.

```sh
uv sync --locked --extra train  # CPU learner
uv sync --locked --extra llm    # Local GPU language experiment
```

Do not switch the environment while another process is using it. The first GPU
smoke uses an isolated worktree/environment; it does not change the active CPU
experiment or production runtime locks. Plain BF16 LoRA avoids a quantization
dependency for this small model. PEFT supports
[adapting selected attention projections and saving adapter weights](https://huggingface.co/docs/peft/en/quicktour).

## Bounded smoke

Download only the pinned public model's safetensors, tokenizer and configuration
into an external cache. Then run the script against that local snapshot:

```sh
uv run --locked --extra llm python scripts/language_smoke.py \
  --model-path /path/to/snapshots/c1899de289a04d12100db370d81485cdf75e47ca \
  --output runs/language-smoke-unique-name
```

The script verifies the base weight hash and disables network access in its sole
GPU worker. It records greedy, non-thinking generation from a synthetic public
legal-choice prompt, then performs exactly one rank-8 attention LoRA update.
The target is `{"a":0}` plus EOS; all prompt and padding labels are `-100`.
Training is batch one, padded to 1,024 tokens, with gradient checkpointing and
SDPA attention. It checks finite loss/gradients/Adam state, changed adapter tensor
values and logits, and exact adapter serialization. It saves the frozen adapter,
base/tokenizer file hashes, source/dependency/decoder identity and resource logs.

The supervisor has a 600-second limit, stops below 700 MiB WSL `MemAvailable`,
and conservatively stops if total GPU use reaches 10 GiB. The worker also limits
PyTorch's allocator to 70% of device memory. Free RAM alone is not the guard:
reclaimable file cache is included in `MemAvailable`. Every failure is retained.
No second worker, engine process, policy retry or fallback is launched.

## Proposed first untuned-versus-SFT contract

Use the demonstration exporter's versioned public rendering for the eventual
policy; `synthetic-legal-choice-v1` is only the smoke fixture. Preserve all
allowlisted public state while interning repeated card records. Keep duplicate
hand slots and target identities distinct. Model text contains numbered legal
choices, never game seeds, scenario/session IDs, raw commands or diagnostic fields.
Target at most 1,024 prompt tokens with a hard 2,048-token context cap; measure
the actual tokenizer count and reject overflow rather than silently dropping state.
Output is exactly `{"a":N}`. Freeze prompt, parser, decoding and retry behavior
before either gameplay evaluation; malformed output remains a recorded failure.

Evaluate the untouched pretrained model first. Then train one disclosed LoRA
adapter on audited, public-information teacher demonstrations, using completion-
only cross-entropy and no invented reasoning. Do not use canonical evaluation
episodes as training data. Split originating runs before tokenization/augmentation;
keep replay families together and remove cross-split duplicate public decisions.
Repeated deterministic heuristic trajectories on the present single scenario may
leave no independent validation data; report that limitation rather than treating
copies as new examples. A later dedicated teacher collection may use a declared
random-legal prefix followed by the fixed heuristic to visit more public states.

An initial bounded SFT comparison can use one fixed adapter configuration,
100-update or 10-minute ceiling, batch one/accumulation eight, and a predetermined
final checkpoint. Preserve adapter/optimizer/RNG and consumed-example state if
resuming. Compare untouched and trained artifacts on the same admitted suite,
reporting parser failures, wins, final HP, turns, inference cost and every attempt.
Current scope is the admitted two-Louse development scenario. Neither a validation
loss decrease nor better scores there establishes unseen-encounter performance.
