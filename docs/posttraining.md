# Post-training pipeline

*2026-10-17. Shared by both games. What exists: trace capture, per-game exports, the
dataset builder [`gameai.sft`](../src/gameai/sft.py) and a local LoRA smoke test
([`scripts/sft_smoke.py`](../scripts/sft_smoke.py)). What is missing is listed at the
end.*

For checkpoint-based WH3 training, see the [minimal RL research handoff](twwarhammer3/checkpoint-rl.md):
local hardware, reusable code, a proposed one-decision loop, risks and tests. It does not
change the student, benchmark or agreed verification methods on this page.

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
- Routing: fp8 or bf16 (the routing constraint; the served quantization is not recorded),
  which excludes its cheapest endpoint (fp4); `require_parameters`; price ceilings of $0.15
  input and $1.00 output per million tokens.
- Sampling made explicit: temperature 1.0, top_p 0.95.
- Thinking-on replies often exhausted both harnesses' 4,000-token output cap, so the first
  datasets come from effort `none`. The cap is 16,000 tokens since 2026-10-18; at it the
  student has played one thinking-on battle (`bench-b30-chariot-qwen-medium-20261018`: 2
  decisions, lost) and no Spire run.

## Data flow

1. **Play** with a model (`spire play`, `twwarhammer3 play`). Each finished model request
   is written to the trace as a `model_exchange` event: the prompt, every attempt with its
   request body, raw output items, reply text, status, usage and backend, and the error
   of a request that failed.
2. **Export** each game's stopped evidence to `decisions.jsonl`, `sources.json` and a data
   card: `twwarhammer3 export` ([trace exports](twwarhammer3/traces.md)) into
   `runs/twwarhammer3/exports/`, `spire export` ([full-run README](spire/fullrun/README.md))
   into `runs/fullrun-exports/`. Exports never render new prompts.
3. **Build** a dataset from one or more exports with `gameai.sft`.
4. **Train**: Tinker (planned); `scripts/sft_smoke.py` checks the pipeline locally now.
5. **Evaluate** the fine-tune by playing it in both harnesses (not yet possible, see
   [Missing](#missing)).

## Beyond supervised fine-tuning

*Owner, 2026-10-18: post-training will also try RL and other methods, so traces must serve
them, not only SFT.* Exports are rebuilt from a stopped job's traces at any time; what the
traces keep:

- Every model request: the exact prompts, raw outputs with visible reasoning, usage,
  backend, wall time and the sampling fields sent. `providers.py` declares sampling only
  for Qwen3.6; GLM-5.3 and Kimi K3 requests carry no temperature or top_p, so they ran at
  the backend's unrecorded default (3,092 of the Empire night's 3,116 rows).
- Every decision: its index in the episode and trace lines; Spire's public observation,
  candidates, the choice and labels (HP, gold, floor, the fight); WH3's decision time,
  orders, the engine's verdict on each and the observation age.
- Every episode: the engine-confirmed outcome and measures, and the raw trace. Spire keeps
  every CommunicationMod message and command. WH3 keeps the public observation behind each
  decision, the hidden enemy totals only at the start and the end (the trace's `roster` and
  `result` records; for scoring, never prompts)
  and, by default, a 1 Hz replay of public state (120 of the 200 model jobs have one,
  counted from the job directories on 2026-10-20).

So episode rewards, and decision rewards from public state (HP lost per fight, visible
strength exchanged between two decisions), can be computed later without replaying a
game. Not captured:

- WH3 hidden state between the start and the end of a battle, so decision rewards cannot
  use the enemy's true losses.

- Token log-probabilities of the model that played, except Qwen3.6 in Spire since harness
  v10.2 (below). WH3 does not request them. GLM's pinned Decart endpoint does not list
  them, and Kimi's pin covers an endpoint without them (untried). Without them, the
  behavior probabilities that importance-weighted updates need cannot be reconstructed;
  that does not rule out all offline RL. For example,
  [IQL](https://arxiv.org/html/2110.06169v1) uses recorded transitions and
  advantage-weighted imitation without saved behavior probabilities.
  Suitability still depends on state/action coverage,
  transitions, rewards and the chosen method; it has not been established for these rows.
- More than one reply per state, which preference methods such as DPO pair up. Saved
  prompts allow resampling offline later; the outcome of another action needs the game.
- A reproducible sampler: Parasail accepted a seed on 2026-10-23, but one seed gave two
  different Qwen3.6 replies (2 calls), so none is sent.
- Play by a model outside OpenAI and OpenRouter, which online RL needs ([Missing](#missing)).

No RL or preference run has used these data yet, so their fitness is unverified
([AGENTS.md](../AGENTS.md#verification-hard-rule)).

**Spire capture since harness v10.2 (2026-10-23).** The owner asked that day to improve
capture for RL and other methods before any collection run; WH3 capture is unchanged.

- Token logprobs: Spire asks Qwen3.6 for each output token's logprob and its top 10
  alternatives (`LOGPROBS` in [`providers.py`](../src/gameai/providers.py)). The
  `model_exchange` event keeps them in the output items, and `spire export` writes them to
  `logprobs.jsonl`. They are the backend's distribution after the strict schema's mask
  (masked alternatives read -9999), the same constrained policy that acted. The reply
  starts with `choice`, so the alternatives at its digit give the probability of every
  candidate below 10 (99.5% of the 187 model decisions of the 2026-10-17 Qwen3.6 run had at
  most 10 candidates). In 3 of the 5,157 attempts of the 2026-10-23 night the backend left out
  a "<" token after a digit; the export flags those rows `logprobs_incomplete`.
- Save snapshots: each new version of the game's autosave, copied into `run-NNNN/saves/`
  with a `save_snapshot` trace event (floor, act, room, seed). The game saves at room
  transitions, so these are the floor-level states from which branch rollouts or a
  simulator could restart a run. They hold hidden state and never reach a policy.
  Restoring one is untested, and so is replaying a run's commands to reach one.

What each method family would read from these traces. "Present" means recorded, not shown
suitable; no method has been tried on them.

| Method | Needs | In Spire traces since v10.2 |
|---|---|---|
| SFT, rejection-sampling fine-tuning | Prompts, replies, outcomes to filter on | Present |
| Offline RL, value and reward models | States, actions, next states, rewards | Present; rewards computed from the trace |
| Importance-weighted off-policy RL, KL to the behavior policy | Behavior logprobs | Qwen3.6 only |
| Unpaired preferences (KTO-style) | Replies labelled good or bad | Present; labels from outcomes |
| Paired preferences (DPO-style) | Two replies to one state | Resample saved prompts; no outcome for the other reply |
| Group rollouts from one state (GRPO-style) | Resettable states | Per-floor snapshots; restore untested ([investigation](spire/state-restore.md)) |
| On-policy RL and distillation | Sampling from the model in training | Needs a training host ([Missing](#missing)) |

The [robot-team learning notes](twwarhammer3/robot-team-research.md#learning-from-recovery-and-feedback)
compare ways to collect recovery examples, learn from outcomes and improve guidance
between battles. They also list additional timing and action-origin fields to audit
before using WH3 traces for those studies.

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
recorded `request`, `output` and backend fields. A Spire attempt with token logprobs has
`logprob_tokens`; its logprobs are in the export's `logprobs.jsonl`, keyed by row `id` and
attempt index. A transport failure's attempt has null
`text`, `status` and `usage`.

The SFT target of a row is its **last attempt**, used only when that attempt has no error,
status `completed` and non-blank text, the row's `error` is null and its split is
`development`. The user message is that attempt's own prompt, so a retried target keeps
the feedback the model was answering. By default outcomes do not select targets: replies
from lost battles and runs are kept, and `outcome` and `labels` travel beside the chats
for filtering or weighting, never into a prompt.

`--require PATH=VALUE` (repeatable; every one must match) keeps only rows whose value at
a dotted path into the row equals VALUE, for example `labels.fight.won=true`,
`outcome.gameplay_outcome=won` or `provenance.unlock_level=3`. VALUE is read as JSON when
it parses (`true`, `3`, `null`, `"3"`), else as text, and must match in type as well; a
row without the path is dropped. Dropped rows count as `require`, and the manifest and
data card list the requirements. Outcomes and labels still never enter the messages.
`--first-attempt-only` drops targets whose prompt differs from the first attempt's, that
is, targets answering retry feedback (`retried`); a failed response resent unchanged is
not a retry.

## Splits

- The group is the unit that must not leak: Spire uses the game seed; WH3 uses the
  scenario's declared `family`, else its name, and for `random` scenarios `NAME/seed-N`
  (the job directory only when no seed is recorded). Repeated starts of one seed or
  scenario, in any job, share a group.
- A WH3 group comes from the scenario snapshot in each job's manifest, so renaming a
  family splits that scenario's earlier and later jobs into different groups. Treat
  declared families as fixed ids.
- `held_out` rows never enter a dataset. WH3 rows are held out when their scenario
  declares `split: held_out`, so a WH3 family can hold both kinds; its held-out rows are
  dropped. Spire reserves ten evaluation seeds, `HELDOUT01` to `HELDOUT10`
  (`HELD_OUT_SEEDS` in [`spire/fullrun/export.py`](../src/spire/fullrun/export.py)); their
  rows are `held_out` and every other Spire row is `development`. The tuning loop never
  plays them.
- Validation is exactly the groups named with `--validation-group GAME:GROUP`; everything
  else kept is train. A group is never in both. A named group without kept rows is refused.
  WH3 families contain spaces, commas and apostrophes, so quote the argument:
  `--validation-group "twwarhammer3:cavalry against anti-large, two-unit form"`.

## Provider terms

By default the builder keeps only `openrouter` rows (open-weight models). Rows produced
by OpenAI models are dropped and counted: whether their outputs may train a model is the
owner's open decision. A lone `--provider` replaces the default, so `--provider openai`
alone keeps only OpenAI rows; `--provider openai --provider openrouter` adds them to the
open-weight rows. Do not include them before that decision. Every dataset's
`datacard.md` repeats this. The question is narrower than a ban: OpenAI's terms of use bar
using output "to develop models that compete with OpenAI" (the 2024-12-11 revision, read
through search results on 2026-10-21; the policy pages refused automated fetches, and the
API's services agreement, which governs API use, was not read). Whether a WH3 battle
specialist competes is the owner's judgment.

OpenRouter also serves closed models, so `openrouter` means open-weight only while
[`providers.py`](../src/gameai/providers.py) declares nothing else for it (today GLM-5.3,
Kimi K3, Step 5 preview and Qwen3.6). The builder does not check licenses: each data card
lists its kept models, and each one's terms must be checked before training. Step 5
preview's weights are public (checked 2026-10-21: `huggingface.co/stepfun-ai/Step-5-Preview`,
604B parameters, BF16 and FP8, "StepFun Model License 1.0"), and it counts a model
trained to a material extent on its outputs as a derivative work, allowed with its notice
and attribution terms; a separate license is needed only for device features or a model
service over US$20M a year. The teacher candidates, same day: `zai-org/GLM-5.3` (753B) uses
the "glm-5.3" license, MIT-style, with a Z.ai security review only for model services over
US$10B a year and nothing on training from outputs; `Qwen/Qwen3.6-35B-A3B` is Apache-2.0;
`moonshotai/Kimi-K3` (2.8T) uses the "Kimi K3 License", MIT-style with conditions above
US$20M of revenue and nothing on training from outputs. Readings of the license pages, not
legal advice.

## Reasoning

Exports keep the visible reasoning of each attempt. OpenAI returns summaries
(`summary_text`); open-weight models through OpenRouter return the reasoning itself
(`reasoning_text`). With `--reasoning`, the assistant message gets `reasoning_content`, the
concatenated `reasoning_text` parts of the target attempt; summaries are never used. It
drops rows played at an effort other than `none` whose target has no `reasoning_text`
(`no_reasoning`): the chat template would render them with an empty think block, as
non-thinking replies. Without it, a reply made with reasoning on is trained as a direct
answer, so build non-thinking datasets from effort `none` play: `--effort none` drops the
other rows and counts them. The smoke test refuses reasoning datasets.

## Token limits

`--tokenizer NAME_OR_PATH` (the `llm` extra) counts each row's chat-template rendering;
with `--max-tokens N`, longer rows are dropped and counted, never truncated. The manifest
reports count, p50, p99 and max per split. The smoke test skips rows over its own
`--max-tokens` (default 4,096) and rows whose reply the chat template renders differently
(Qwen's strips leading newlines), and counts both in its `metrics.json`.

## Smoke-test measures

The training loss of single shuffled rows is noise, so the smoke test measures the mean
loss per assistant token on fixed evaluation rows (the first `--loss-rows`, default 64,
usable validation rows; train rows when there is no validation) before training and again
with the saved adapter, reloaded and verified (`eval_loss` in `metrics.json`). It then
decodes the first `--eval-rows` (default 8) of them and reports the JSON-valid, exact-match
and action-match rates. Exact match compares the whole normalised JSON, including the
free-text `reason` and `notes`, so it stays near zero; action match compares the replies
after dropping the top-level `reason` and `notes` keys (Spire's `choice`, WH3's `orders`).
A lower loss after training on validation rows is the learning signal; on train rows it
shows only fitting.

## Commands

```bash
# Build: train and validation chats, aligned row sidecars, manifest.json, datacard.md
uv run python -m gameai.sft runs/twwarhammer3/exports/NAME [EXPORT ...] \
    --output runs/sft/NAME --validation-group "twwarhammer3:FAMILY NAME" --effort none
# Options: --provider P, --effort E and --require PATH=VALUE (repeatable),
# --first-attempt-only, --reasoning
# Token counts and limits need the llm extra (transformers):
# runs/sft/tokenizers/Qwen3.6-35B-A3B holds the student's tokenizer and chat template at
# Hugging Face revision 995ad96 (REVISION file; Apache-2.0 LICENSE beside it).
uv run --locked --extra llm python -m gameai.sft runs/twwarhammer3/exports/NAME \
    --output runs/sft/NAME --tokenizer runs/sft/tokenizers/Qwen3.6-35B-A3B --max-tokens 8192
# Local smoke test (CUDA; refuses while a game runs): validation loss, ~30 LoRA steps on
# Qwen3-0.6B, then reload and verify the adapter, validation loss again, and decode
# validation rows (JSON-valid, exact-match and action-match rates)
uv run --locked --extra llm python scripts/sft_smoke.py runs/sft/NAME \
    --output runs/sft/NAME-smoke
uv sync --locked   # removes the llm extra again
```

The builder refuses an existing output directory, an export whose `decisions.jsonl` no
longer matches its `sources.json` hash, rows without `id`, `game`, `group` or `split`, an
unknown game or split, and duplicate ids. Output is deterministic for unchanged inputs.
The manifest records input hashes, arguments, counts kept and dropped by reason and by
game, model and effort, the groups per split, token statistics and the builder's hash.

## First end-to-end test (2026-10-17)

Qwen3.6-35B-A3B played both games through OpenRouter on 2026-10-17. Run details are in the
[Spire log](spire/fullrun/log.md#2026-10-17-qwen36-smoke-runs-and-the-first-end-to-end-post-training-test)
and the [WH3 log](twwarhammer3/log.md#2026-10-17-queue-e2-qwen36-on-s1-step-floors-and-harness-b25).

| Step | Output | Result |
|---|---|---|
| Spire play: one full run and two short runs (reasoning off; one short run with it on) | `runs/fullrun/llm-qwen36*-smoke*-20261017` | $0.24; lost on floor 16 (boss) and floor 6 |
| WH3 play: S1 twice with reasoning off, once with it on | `runs/twwarhammer3/battle/bench-b24-s1-qwen-*` | $0.05; both lost; reasoning on ended at the cap |
| Export | `runs/fullrun-exports/qwen36-smoke-20261017`, `runs/twwarhammer3/exports/qwen36-smoke-20261017` | 273 Spire rows, no issues; 84 WH3 rows, 2 missing acknowledgements |
| Build, `--effort none`, validation `spire:QWENSMOKE2` | `runs/sft/qwen36-smoke-20261017` | 268 train (Spire QWENSMOKE1 and WH3 S1), 55 validation; p50 2.5k, max 5.9k tokens |
| Build, `--effort medium --reasoning` | `runs/sft/qwen36-reasoning-smoke-20261017` | 33 chats with `reasoning_content` (about 5.8k characters on the first) |
| Smoke fine-tune, 60 steps on Qwen3-0.6B | `runs/sft/qwen36-smoke-20261017-smoke` | Loss 1.22 to 1.02 (first and last five steps); adapter reloaded and verified; 8 of 8 validation replies valid JSON, none exact (the 0.6B model always chose 0) |

The b26 smoke test (same dataset and settings, `runs/sft/qwen36-smoke-20261017-smoke-b26`)
adds measures on fixed rows: validation loss on the 55 rows of the unseen Spire seed fell
from 1.685 to 1.328, and 5 of 16 decoded replies matched the reference action. All 16
replies chose index 0, and 5 of those 16 references are 0, so the match equals the
always-choose-0 baseline. About 94% of the validation target characters are the free-text
`notes` and `reason`; how the loss drop splits by field is unmeasured.

The pipeline works from play to an adapter. None of these numbers is a result: one run per
configuration, a 0.6B stand-in for the student, and 60 steps.

## Missing

- Tinker training and sampling: no credential, no training client, no recipe.
- Serving a fine-tune back into both harnesses: OpenRouter cannot serve it, so the games
  need a provider route to Tinker sampling or another endpoint before a fine-tune can be
  played and compared with its base.
- Held-out WH3 scenarios beyond those already declared. Spire's held-out seeds are
  declared but not yet played.
- WH3 scenarios without a declared `family` each form their own group, so variants that
  share armies (the `kho5-dwf5` battle types) can land in different splits. Declare
  families before validating on them.
- Spire's content changes with the Ironclad unlock level: every run so far is level 3, and
  the profile was 81 points short of level 4 on 2026-10-17. Exports record the level per
  run; compare like with like.
- Thinking datasets from the student need effort `medium` play at the 16,000-token cap (so
  far one WH3 battle, `bench-b30-chariot-qwen-medium-20261018`, 2 decisions; no Spire run).
  Teacher reasoning rows exist: with `--reasoning`, the Empire night gives
  2,519 GLM-5.3 and 507 Kimi K3 rows with `reasoning_content` (63 rows have none: 62
  GLM, 1 Kimi).
- Target selection: which replies to learn from (a teacher's, rejection-sampled wins, or
  RL from the start). Winning targets: 965 WH3 rows from the Empire night's 7 GLM wins
  (`--require outcome.gameplay_outcome=won`; add `outcome.ended_by=engine_result` to leave
  out timer wins), no Spire win. Export has no content screen: a reply that parses but is
  garbage (no orders, a gibberish reason) enters a dataset unless screened; the 2026-10-20
  review counted 7 such accepted replies in the Empire night, 3 of them in won episodes.
