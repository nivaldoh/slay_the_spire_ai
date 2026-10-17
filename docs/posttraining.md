# Post-training pipeline

*2026-10-17. Shared by both games. What exists: trace capture, per-game exports, the
dataset builder [`gameai.sft`](../src/gameai/sft.py) and a local LoRA smoke test
([`scripts/sft_smoke.py`](../scripts/sft_smoke.py)). What is missing is listed at the
end.*

## Roles

- **OpenRouter serves inference only.** Both games play open-weight models through it
  (`--provider openrouter`): baseline play and the traces that become training data. It
  has no fine-tuning API, and a fine-tuned model cannot be served there except through
  Enterprise private endpoints.
- **Training happens elsewhere.** Tinker is planned (remote LoRA for Qwen3.6-35B-A3B; prices
  and the RL plan are on the [open-weight track page](spire/open-weight/README.md)); no
  credential exists yet. Until then a local RTX 3060 (12 GB) runs only a small smoke test
  on Qwen3-0.6B with the `llm` extra, never while a game runs (the script refuses to start
  then).

## Student model

`qwen/qwen3.6-35b-a3b` on OpenRouter, `Qwen/Qwen3.6-35B-A3B` on Hugging Face (MoE, 35B total,
3B active). [`gameai/providers.py`](../src/gameai/providers.py) declares it:

- Reasoning is on/off: effort `none` (no reasoning) or `medium` (reasoning on). Checked
  live on 2026-10-17, `low` to `max` were all accepted and all reasoned 1.3k-4k tokens.
- Routing: fp8 or bf16 endpoints only (its cheapest endpoint is fp4),
  `require_parameters`, and price ceilings of $0.15 input and $1.00 output per million tokens.
- Sampling made explicit: temperature 1.0, top_p 0.95.
- Thinking-on replies often exhaust both harnesses' 4,000-token output cap, so the first
  datasets come from effort `none`.

## Data flow

1. **Play** with a model (`spire play`, `twwarhammer3 play`). Each finished model request
   is written to the trace as a `model_exchange` event: the prompt, every attempt with its
   request body, raw output items, reply text, status, usage and backend, and the error
   of a request that failed.
2. **Export** each game's stopped evidence to `decisions.jsonl` and `sources.json`
   (WH3: `twwarhammer3 export`, [trace exports](twwarhammer3/traces.md); Spire full runs
   have their own exporter emitting the same contract). Exports never render new prompts.
3. **Build** a dataset from one or more exports with `gameai.sft`.
4. **Train**: Tinker (planned); `scripts/sft_smoke.py` checks the pipeline locally now.
5. **Evaluate** the fine-tune by playing it in both harnesses (not yet possible, see
   [Missing](#missing)).

## Export-row contract

Both exporters emit these fields; the builder reads nothing else.

| Field | Meaning |
|---|---|
| `schema_version`, `id` | Integer row schema; stable id independent of paths |
| `game` | `spire` or `twwarhammer3` |
| `group` | The leak-free split unit (see [Splits](#splits)) |
| `split` | `development` or `held_out` |
| `policy`, `provider`, `model`, `effort`, `prompt_version` | The controller; the version may be null |
| `system_prompt`, `user_prompt` and their `_sha256` | Exact saved prompts; `user_prompt` is the first attempt's |
| `attempts` | In request order, below |
| `error` | Null, or `{"type", "message"}` for a request that ended without an accepted reply |
| `outcome` | `status`, `gameplay_outcome` (`won`, `lost`, `draw` or null) and game-specific measures |
| `labels` | Game-specific dict, possibly empty |
| `provenance` | Source ids, revisions, hashes, trace lines |

Each attempt has `user_prompt` (the exact text sent, retry feedback included; null when
unknown), `text` (raw reply), `status` (provider status: `completed`, `incomplete`,
`failed`), `error` (absent or null when the reply was accepted, else the parser's or
transport's message), `reasoning` (parts from `gameai.llm.reasoning_parts` with
`type`, `text`, `field`, `item_index`; null when not recorded), `usage`, and when
recorded `request`, `output` and backend fields.

The SFT target of a row is its **last attempt**, used only when that attempt has no error,
status `completed` and non-blank text, the row's `error` is null and its split is
`development`. The user message is that attempt's own prompt, so a retried target keeps
the feedback the model was answering. Outcomes do not select targets: replies from lost
battles and runs are kept, and `outcome` and `labels` travel beside the chats for
filtering or weighting, never into a prompt.

## Splits

- The group is the unit that must not leak: Spire uses the game seed; WH3 uses the
  scenario's declared `family`, else its name, and for `random` scenarios `NAME/seed-N`
  (the job directory only when no seed is recorded). Repeated starts of one seed or
  scenario, in any job, share a group.
- `held_out` rows never enter a dataset. WH3 rows are held out when their scenario
  declares `split: held_out`, so a WH3 family can hold both kinds; its held-out rows are
  dropped. Spire declares no held-out seed yet, so every Spire row is `development`.
- Validation is exactly the groups named with `--validation-group GAME:GROUP`; everything
  else kept is train. A group is never in both. A named group without kept rows is refused.

## Provider terms

By default the builder keeps only `openrouter` rows (open-weight models). Rows produced
by OpenAI models are dropped and counted: whether their outputs may train a model is the
owner's open decision. `--provider openai` includes them explicitly; do not do so before
that decision. Every dataset's `datacard.md` repeats this.

OpenRouter also serves closed models, so `openrouter` means open-weight only while
[`providers.py`](../src/gameai/providers.py) declares nothing else for it (today GLM-5.3,
Kimi K3, Step 5 preview and Qwen3.6). The builder does not check licenses: each data card
lists its kept models, and each one's terms must be checked before training. Whether
`stepfun/step-5-preview` has open weights is not verified here.

## Reasoning

Exports keep the visible reasoning of each attempt. OpenAI returns summaries
(`summary_text`); open-weight models through OpenRouter return the reasoning itself
(`reasoning_text`). With `--reasoning`, the assistant message gets `reasoning_content`, the
concatenated `reasoning_text` parts of the target attempt; summaries are never used.
Without it, a reply made with reasoning on is trained as a direct answer, so build
non-thinking datasets from effort `none` play: `--effort none` drops the other rows and
counts them. The smoke test refuses reasoning datasets.

## Token limits

`--tokenizer NAME_OR_PATH` (the `llm` extra) counts each row's chat-template rendering;
with `--max-tokens N`, longer rows are dropped and counted, never truncated. The manifest
reports count, p50, p99 and max per split. The smoke test skips rows over its own
`--max-tokens` (default 4,096) and rows whose reply the chat template renders differently
(Qwen's strips leading newlines), and counts both in its `metrics.json`.

## Commands

```bash
# Build: train and validation chats, aligned row sidecars, manifest.json, datacard.md
uv run python -m gameai.sft runs/twwarhammer3/exports/NAME [EXPORT ...] \
    --output runs/sft/NAME --validation-group twwarhammer3:FAMILY --effort none
# Options: --provider P and --effort E (repeatable), --first-attempt-only, --reasoning
# Token counts and limits need the llm extra (transformers):
uv run --locked --extra llm python -m gameai.sft runs/twwarhammer3/exports/NAME \
    --output runs/sft/NAME --tokenizer Qwen/Qwen3.6-35B-A3B --max-tokens 8192
# Local smoke test (CUDA; refuses while a game runs): ~30 LoRA steps on Qwen3-0.6B, then
# reload and verify the adapter and decode validation rows (JSON-valid, exact-match rates)
uv run --locked --extra llm python scripts/sft_smoke.py runs/sft/NAME \
    --output runs/sft/NAME-smoke
uv sync --locked   # removes the llm extra again
```

The builder refuses an existing output directory, an export whose `decisions.jsonl` no
longer matches its `sources.json` hash, rows without `id`, `game`, `group` or `split`, an
unknown game or split, and duplicate ids. Output is deterministic for unchanged inputs; the manifest records input
hashes, arguments, counts kept and dropped by reason and by game, model and effort, the
groups per split, token statistics and the builder's hash.

## Missing

- Tinker training and sampling: no credential, no training client, no recipe.
- Serving a fine-tune back into both harnesses: OpenRouter cannot serve it, so the games
  need a provider route to Tinker sampling or another endpoint before a fine-tune can be
  played and compared with its base.
- Held-out Spire seeds, and held-out WH3 scenarios beyond those already declared.
- Thinking datasets: they need effort `medium` play that fits the output cap.
