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
per-episode limits as the neural/random/heuristic comparisons. Greedy decoding is
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
