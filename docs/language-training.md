# Bounded public-demonstration SFT

`scripts/train_language.py` trains the pinned local Qwen3-0.6B through attention
LoRA. This implementation has CPU transaction, loss-mask and serialization tests;
it does not establish gameplay improvement or GPU resume equivalence. A real job
requires a separately recorded untouched-model engine baseline and a frozen
experiment contract. The first experiment is specified separately in
[language-experiment.md](language-experiment.md).

The base snapshot is `Qwen/Qwen3-0.6B` at revision
`c1899de289a04d12100db370d81485cdf75e47ca`, with the exact nine file hashes required
by `language_policy.py`. Loading is local-only, with remote code disabled. The
base uses BF16, SDPA and nonreentrant gradient checkpointing. Only attention
`q_proj`, `k_proj`, `v_proj`, `o_proj` LoRA parameters train: rank 8, alpha 16,
dropout 0, no bias. PEFT's normal FP32 adapter promotion is retained and actual
trainable dtypes/counts are recorded. AdamW uses the declared learning rate,
weight decay 0.01, default betas/epsilon, and global gradient clipping at 1.

## Data and loss

`verify_dataset(path)` reconstructs the demonstration export from its original
engine evidence using the current exporter. The manifest and every exported file
must match. Only source-verified public heuristic origins are accepted; smoke,
random, privileged, test-split and held-out-origin declarations are rejected.
Only `train.jsonl` supplies examples. Validation rows, if present, are unused.
All original source paths must remain available, including catalog parent suite
evidence. A source's prior purpose and development reuse flag remain recorded;
all results here retain the dataset's diagnostic development scope.

Each example is the exact public prompt and canonical `{"a":N}` completion from
an origin-labelled engine action. Metadata, outcomes, seed identities and any
reasoning text stay outside model input. The chat template is shared with
inference: one user message, generation prompt enabled, thinking disabled, and
no additional special tokens during tokenization. Labels mask the entire prompt
and all padding. Only the completion and one tokenizer EOS contribute causal
cross entropy. The trainer rejects overlength examples; it never truncates them.

One microbatch contains one padded sequence. `batch_size` is the number of
microbatches accumulated before an optimizer update. Losses are weighted by the
number of supervised tokens, giving a completion-plus-EOS token mean across the
whole update, including variable-length completions. Exact duplicate public
examples retain their separate real origins. A seeded shuffled sampler cycles
through epochs; occurrence identity includes original example ID, epoch and
position. There is no success filtering, synthetic augmentation or reasoning
generation.

## Configuration and invocation

`train_language(output: Path, config: dict | None = None, *, resume=False)` is the
Python entry point. Use the script for real jobs because it adds an independent
process watchdog around the worker. `prepare_run` and `load_checkpoint` expose
the frozen manifest and authoritative CPU checkpoint for inspection.

| Required JSON field | Meaning |
| --- | --- |
| `base_snapshot` | Absolute local directory containing the pinned snapshot |
| `dataset` | Audited demonstration export directory |
| `seed` | Explicit nonnegative Torch/Python/sampler seed |
| `max_updates` | Maximum committed optimizer updates |
| `time_budget_seconds` | Wall budget from supervisor launch, including initialization |
| `max_tokens` | Maximum reserved padded input tokens |
| `batch_size` | Accumulated examples per update; microbatch is fixed at one |
| `max_sequence_tokens` | Exact padded sequence length, at most 2060 |
| `learning_rate` | Positive finite AdamW learning rate |

Optional guards are `min_available_mib` (default 700) and `max_gpu_gib` (default
10). Unknown keys and invalid budgets fail before model loading. Prompt and
completion limits also remain fixed at 2048 and 12 tokens respectively.

With an already prepared CUDA environment, invoke its interpreter from the
frozen source checkout. Keep the ordinary CPU environment separate:

```bash
PYTHONPATH="$PWD/src" /path/to/cuda-env/bin/python scripts/train_language.py \
  --config /absolute/experiment.json --output /absolute/runs/language-sft

PYTHONPATH="$PWD/src" /path/to/cuda-env/bin/python scripts/train_language.py \
  --output /absolute/runs/language-sft --resume
```

These commands neither install dependencies nor download models. The worker
must have the locked `llm` dependencies. The supervisor sets offline and telemetry
environment flags and never imports Torch. Source revision, implementation file
hashes, dependency versions, local base hashes, dataset/origin hashes and every
budget are frozen before GPU work. Implementation changes must be committed.
Resume requires the same configuration, source and evidence; it cannot extend
the original absolute deadline. An optional internal `started_unix` argument
passes the supervisor's launch time to the worker, and cannot be in the future
or replace a resumed job's original time.

## Commit and resource boundaries

Before an update, an atomic checkpoint reserves
`batch_size * max_sequence_tokens` padded input tokens and records the planned
occurrences. This counts padding and prompt tokens, irrespective of the number
of supervised labels; it is not a FLOP or backward-recomputation counter. After
the update, a second atomic checkpoint commits adapter tensors, optimizer,
Python/Torch/CUDA RNG, sampler cursor, consumed occurrences and finite metrics.
Checkpoint files and directories are fsynced before replacing the authoritative
`checkpoint.json` pointer. Unpointed checkpoint files remain as crash evidence.

An interrupted uncommitted reservation stays charged. On explicit resume it is
marked abandoned, and the last committed weights, optimizer, RNG and cursor are
restored. Recomputing those unconsumed examples requires a new charged
reservation. A committed update is never silently repeated. Checkpoint loading
replays every reservation from the frozen seed/example list to verify the
sampler and occurrence schedule. There is no automatic resume or budget increase.
For example, 64 updates of four sequences padded to 2060 require 527,360 tokens
before any abandoned reservation overhead.

The worker holds the same nonblocking GPU lease as language inference, plus a
separate per-output lease. A conflicting owner fails immediately. Model,
optimizer and exception-frame tensor references are released before GPU lease
exit. The CUDA allocator limit is 70%; available host RAM and reserved GPU memory
are checked inside updates. The supervisor polls host availability and whole-GPU
usage, also checking the original deadline. On a guard failure it interrupts its
one worker, permits up to five seconds of cleanup, then kills it if needed. It
records the reason and cleanup overrun; no new update begins after deadline.
An OOM or guard failure preserves the last checkpoint and failure evidence;
there is no automatic batch/sequence/dtype reduction.

After the original deadline, `--resume` automatically uses a bounded CPU-only
finalization path so an interrupted export can be recovered. `--resume --finalize`
requests the same path explicitly before deadline. It permits 30 seconds for
checkpoint verification/export plus bounded process cleanup, never loads a model,
never takes the GPU lease, and retains the original training deadline. The
watchdog records this separate supervision deadline and cleanup overrun. This
does not grant additional optimizer work.

## Saved evidence and limitations

`job.json` freezes the contract. `checkpoints/` retains immutable CPU payloads
and `checkpoint.json` selects the committed state. `training.json` records the
committed update count, charged/committed tokens, consumed occurrences,
reservations, finite loss/gradient/optimizer checks, changed adapter elements,
tensor hashes and resource measurements. `watchdog-*.json` preserves each
supervisor invocation, including interrupted ones.

An update/time/token stop exports the last committed adapter under
`artifacts/update-<count>-<checkpoint SHA>/adapter/`. The adjacent `policy.json`
uses the shared frozen language declaration; it is outside the adapter directory
to avoid a recursive file hash. `export.json` records export file hashes. The
safetensors are checked against the checkpoint before publication. Reusing an
existing export revalidates tensors, configuration and declaration provenance;
self-reported refreshed file hashes are insufficient. Error/interruption exits
retain their checkpoint without claiming a completed final export.

CPU tests establish completion masking, token-mean accumulation, finite adapter
changes, exact resumed toy weights/optimizer/RNG/cursor, crash recovery,
provenance rejection, and serialization. CUDA kernels may introduce numeric
nondeterminism: bit-exact GPU resume has not been established. The 1024-token
synthetic smoke does not prove a real 2060-token update fits; the first real
update remains a guarded feasibility check. Lower training loss and changed
weights are computational findings; gameplay claims require the separately
frozen original-engine evaluation.

```bash
uv run --extra train pytest -q tests/test_language_training.py
```

The torch-only test environment skips three safetensors integration cases and
one tiny CPU Qwen/PEFT continuation case when those optional packages are absent.
They can also run with the locked CUDA
interpreter while using CPU toy models exclusively; no test launches a game,
loads Qwen weights or acquires the production GPU lease.
