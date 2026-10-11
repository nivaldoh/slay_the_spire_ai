# First real-data language imitation diagnostic

Declared before any unchanged-model engine evaluation or real-data fine-tuning.
The question is whether supervised imitation of a public heuristic improves a small
local pretrained model's legal responses and gameplay on the already-used fixed
Louse development scenario. This is a memorization and integration diagnostic,
with pretrained-model advantage disclosed. It is not an unseen-scenario study.

## Frozen comparison

Use Qwen/Qwen3-0.6B revision `c1899de289a04d12100db370d81485cdf75e47ca`, with base,
tokenizer, template and dependency hashes recorded by the language artifact declaration.
First evaluate the unchanged base model with no adapter. The synthetic smoke adapter
must never be used as the initial policy. Then train one fresh rank-8 attention LoRA
adapter (q/k/v/o projections, alpha 16, dropout zero), and evaluate its final committed
artifact. Do not select an intermediate checkpoint by gameplay score.

Both evaluations use `configs/suites/louse_diagnostic_development_v1.json`: the same
original engine, Ironclad A0, seeded settled start, eight scheduled policy seeds and
per-episode limits as the neural/random/heuristic comparisons, with a separate
1,600-second process deadline per evaluation batch. Greedy decoding is
deterministic; eight repeats of the same scenario do not give eight independent
situations or eight language-policy sampling draws. Report this duplication explicitly.

Freeze `public-card-table-choice-v1`, `single-json-choice-v1`, the non-thinking chat
template, greedy decoding, a 2,048-token prompt cap and 12 generated tokens. No prompt
truncation, fallback, parser repair or retry is allowed. A malformed response or context
overflow ends that attempt as a policy failure; the next independently scheduled
attempt may proceed. Count wins over all policy attempts alongside wins over completed
games, and report parser/context failures, invalid commands and infrastructure failures
separately. HP is defined only for completed games. Each decision retains exact prompt
hashes, token counts, completion IDs/text and its bound legal candidate.

## Data and training budget

Export `runs/heuristic-settled-20261011`, the two verified deterministic public-heuristic
replays, through the audited demonstration exporter. Expected data: 42 rows, 21 unique
public prompts. Preserve duplicates and their origins; do not claim they are independent
examples. Put the whole origin in the training split with no validation split. The
exporter must verify source identity, teacher actions, complete audited fights and split
provenance. This explicitly reuses development conditions. No final-test data, privileged
teacher, invented reasoning text, model self-labels or outcome-conditioned selection.

Training uses seed 0, BF16, completion-plus-EOS cross-entropy, prompt/padding labels
masked to -100, microbatch one and four examples per accumulated update. Use AdamW
learning rate 0.0002, sequence padding/cap 2,060 tokens, gradient checkpointing, and
at most **64 committed updates, 600,000 padded forward tokens, or 600 seconds**, whichever
limit comes first. Sixty-four complete updates would charge 527,360 padded tokens.
Charge reservations before work; interrupted reservations still spend tokens and time.
Resume the committed adapter, optimizer, data cursor and RNG under the original absolute
deadline. Never replenish budget by resume or silently discard a failed attempt.

The 1,024-token synthetic smoke does not prove the 2,060-token update fits. The first
real update remains a guarded feasibility check. Require available WSL RAM at least
700 MiB, total GPU use below 10 GiB, and one GPU owner. Stop and preserve evidence on a
resource failure; changing context, precision or budget would require a new declared
experiment. The main CPU environment remains separate from the CUDA environment.

## Evidence and decision

Require verified data lineage and masking, finite updates, changed adapter parameters,
exact saved-adapter reload and frozen original-engine evaluation before any gameplay
claim. Retain resource samples, charged/committed tokens, update/example counts, elapsed
time, source/dependency hashes, artifacts and every evaluation attempt.

Keep the candidate for this diagnostic only if valid results improve policy-attempt
completion/wins, or improve ending HP without reducing completion/wins. Reject an
unchanged or worse result as an improvement; mark a broken evidence contract invalid.
Small changes remain inconclusive about general ability. Any claim beyond this one
scenario requires new declared development comparisons and later held-out evaluation.

## Preserved infrastructure failure and bounded rerun

The first trained evaluation, `runs/qwen3-0.6b-sft-eval-20261011`, stopped after two
wins at HP77 and one relay-startup failure, leaving five scheduled attempts unrun.
The two completed fights exactly reproduced the teacher's commands and public
transitions. The third attempt had zero observations/actions and failed while Linux
waited for the Windows relay connection; relay stderr reported WinError10054.
Its trace evidence is valid, but the eight-attempt evaluation is incomplete and
cannot establish the declared full-suite improvement. Preserve its separate
[result](results/language-sft-incomplete-development-v1.json), runtime and costs.

Before any new game, declare this recovery sequence: implement and check a narrow
transport mitigation that connects Windows directly to the current WSL guest IPv4
address instead of its localhost forwarder. Keep port19876, timeouts and fail-closed
session semantics. This bypasses a suspected intermediary; bounded socket probes
did not reproduce the intermittent failure and do not prove its exact cause.

First run `runs/direct-relay-control-20261011`: two canonical SPIREAI1 public-heuristic
fights, 500 actions/180 seconds per episode, 45-second bridge timeout and a 300-second
process limit. Require both original-engine outcomes, exact settled starts and full
command/public-transition agreement with the existing heuristic reference. Stop on
failure; these are infrastructure controls, not new training demonstrations.

If those controls pass, run the same final update64 adapter (declaration SHA-256
`70d19d51a5578ca3ce4e64e0f3f8646c9034ab6e14cf9f84baa2002268a248d6`) on the unchanged
eight-attempt suite as `runs/qwen3-0.6b-sft-eval-v2-20261011`, with the existing
1,600-second batch limit. No new training, checkpoint selection, prompt/parser change,
response repair or automatic retry. This is one explicitly declared infrastructure
rerun after preserving the first batch, not a continuation that overwrites it. Report
both batches and their combined attempted-game/infrastructure cost, while scoring the
new complete suite separately. The untuned baseline and its archived original
contract remain unchanged. If the rerun fails, retain it and diagnose again rather
than silently relaunching.

## Controlled diagnostic result

Real-data training completed all 64 updates in 398.46 seconds, charging 527,360
padded tokens and consuming 256 example occurrences from 42 rows (21 unique public
prompts). The independent saved-training audit passed all 12 checks: 129 immutable
checkpoints, finite parameters and optimizer state, exact exported tensors and data
lineage, unchanged budgets, and no pending or abandoned reservations. Peak total GPU
use was 7,087 MiB; minimum available WSL RAM was 3,522.97 MiB. CUDA resume equivalence
has not been demonstrated. See [training audit](results/language-sft-training-audit.json).

The two declared direct-address control fights passed, each exactly reproducing the
reference's 21 commands and public transitions. The frozen v2 evaluation then
completed all eight scheduled attempts at source `e829c1c`:

| Policy | Wins / policy attempts | Policy failures | Completed games | Mean final HP |
| --- | ---: | ---: | ---: | ---: |
| Unchanged Qwen3-0.6B | 0 / 8 | 8 | 0 | undefined |
| Final public-heuristic LoRA | 8 / 8 | 0 | 8 | 77 |

Every trained fight matched the teacher's full command sequence and public
transitions, ending on turn 6. There were no invalid commands, context failures or
infrastructure failures in the complete rerun. Mean measured inference time was
8.266 seconds per fight; mean total episode time was 46.595 seconds, including
14.530 seconds of reset/startup. These are observed workstation timings, with
occasional concurrent CPU audit/test work, not an isolated throughput benchmark.

Decision: **keep for this imitation diagnostic**. Actual parameter training changed
the unchanged model's malformed string-valued responses into the teacher's legal
trajectory on the reused scenario. The model tensor hash loaded for evaluation was
`b620fa2e3f44a0bd7e7f38646f28a51cf1d33a9fa7ec8062d18b2d02c1be496c`, linked to the exact
declared final adapter. This is a successful memorization/integration result with
pretraining advantage, one training initialization and eight correlated greedy
repeats. It is not evidence of unseen-scenario competence or a compute-matched
improvement over PPO from scratch.

The initial incomplete batch remains separate: two wins, one infrastructure failure
and five unattempted slots. Across both trained batches, 11 game attempts produced
10 wins and one startup failure; these totals do not replace the canonical eight-game
score. See [comparison and paired traces](results/language-sft-development-v1.json).
Regenerate that compact result with `uv run python runs/summarize_language_diagnostic.py`
when the retained local raw runs are available. Multi-encounter language evaluation
is now implemented, but no such gameplay score has been collected yet.
