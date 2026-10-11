# Proposed frozen language-policy catalog comparison

Prepared before either language policy is evaluated on this catalog. This proposal
does not launch or authorize an automatic queue. Adopt it in the research record
before execution, after the active four-policy CPU comparison has terminated and
released the game. Serialize it with other experiments; run the unchanged model
first, then the existing final LoRA. Preserve this order regardless of outcomes.

## Question and scope

Does the already-trained public-heuristic LoRA improve legal-response completion
and combat outcomes relative to its unchanged pretrained base on the three declared
development scenarios? Separate the familiar Louse scenario from Cultist and Jaw
Worm, which are absent from this adapter's 42 training rows. Those rows contain only
21 unique public prompts, all from the same Louse start. Do not add demonstrations,
train again, repair responses, change prompts, or choose another checkpoint.

This is a transfer diagnostic with one training initialization. The two additional
encounter families are held out from this adapter's training data; the catalog is
already used for development and is not an untouched test. The pretrained model's
prior game knowledge is uncontrolled. Four greedy repeats per scenario remain
correlated repetitions, not four independent situations or sampling draws.

## Frozen inputs

Use `configs/suites/starter_three_encounter_development_v1.json`, SHA-256
`837572e877102407b0731523b361217a4bccc5f662c59993ee4ac99727f6ef5b`.
Its three scenarios are SPIREAI1 (ordered Normal/Defensive Louses), SPIREINV07
(Cultist), and SPIREINV09 (Jaw Worm), with their existing exact public-start and
discovery hashes. For each policy, execute the following exact 12-attempt order:
for policy-seed label 2000, then 2001, 2002, 2003, run SPIREAI1, SPIREINV07,
SPIREINV09 in that order. There are 24 reserved slots across the two policies.
The seed labels do not randomize greedy language decoding.

Use these original declarations without editing their provenance:

- Unchanged base: `runs/qwen3-0.6b-untuned-declaration-v2-20261011.json`, SHA-256
  `b689e0d880f11b6ffee787a2c627b4d4da33ef2f7f190a9882df4302628af0b6`.
  Adapter must be null. Previously recorded full-model tensor SHA-256:
  `bda00e3e09e7e35c6c6950cfb2673117052c3e8718dfc47ed35f7db9c5405c94`.
- Final LoRA: `runs/qwen3-0.6b-heuristic-sft-20261011/artifacts/update-000064-b2281346a63a7944bb9f4f2c64b3f1f3839d15bbcc97e1da6e83335d72dcd1bc/policy.json`,
  SHA-256 `70d19d51a5578ca3ce4e64e0f3f8646c9034ab6e14cf9f84baa2002268a248d6`.
  Adapter config/file SHA-256 values are respectively
  `d5b8b5caefef3288fbb86ee2b1bbbcfd6e3474588ae4a2999d356855c9bcede2` and
  `cb769776c3fd9c220747b81275779c209995a2dc5eabdd8ea0f208ff052d585e`.
  Previously recorded loaded-model tensor SHA-256:
  `b620fa2e3f44a0bd7e7f38646f28a51cf1d33a9fa7ec8062d18b2d02c1be496c`.

Both use Qwen/Qwen3-0.6B revision
`c1899de289a04d12100db370d81485cdf75e47ca`, with all nine existing base/tokenizer
file pins. Require the recorded dependency versions: torch 2.13.0+cu130,
transformers 5.19.0, peft 0.21.2, accelerate 1.15.0, safetensors 0.8.0.
Record interpreter/CUDA versions and frozen source revision/files at launch.
The final adapter remains linked to update64, its actual checkpoint digest,
training job, dataset manifest and independent saved-training audit.

Keep `ironclad-starter-combat-v1`, `public-card-table-choice-v1`, and
`single-json-choice-v1`; the same public information and state-bound legal actions
apply to both policies. Use the existing stateless nonthinking chat template,
greedy decoding, one beam, 2,048 prompt tokens and at most 12 generated tokens.
Preserve raw text/token IDs and the one-terminal-EOS removal rule. No truncation,
grammar change, parser repair, fallback, retries, or cross-episode memory.

## Budget and stop rules

Use the original engine, Ironclad A0, 80/80-HP pinned starts, existing reset/prefix,
500 actions and 180 seconds per episode, and 45-second bridge timeout. Reserve
**1,800 seconds per policy batch**, including initial model load and evaluation,
with at most 10 seconds of process cleanup grace; the two-batch evaluation budget
is 3,600 seconds plus that explicitly separate cleanup allowance. The measured
trained Louse rerun averaged 46.595 seconds per fight (8.266 seconds inference),
or roughly 559 seconds for twelve such fights. The larger cap allows longer new
encounters and setup; it is a ceiling, not a runtime forecast or replenishable budget.

One frozen model/GPU owner spans each policy's catalog schedule. Confirm source,
catalog, research contract, declaration, adapter and external base pins before and
after collection. Freeze original declaration bytes plus the separately recorded
execution declaration that rebases only the adapter directory to its snapshot.
Release model, GPU lease and owned game on every exit.

A parser/context failure ends that policy attempt and advances to the next already
scheduled slot. A real death is a gameplay loss and also advances. Infrastructure,
unsupported-state, truncation, evidence failure or timeout stops the queue, preserving
all completed/failed children and unattempted slots, including the second policy if
not yet started. No retry, resume, substitute seed, fallback or automatic rerun.
Any later recovery requires a separate declared protocol and retains this batch.

## Reporting and claim boundary

Independently re-audit every child and the complete catalog, including tokenizer
reconstruction, observed start/monster identity and artifact/source linkage. Report
each scenario first, then an equal-scenario macro only when the entire declared
schedule is valid. The primary comparison is wins divided by policy attempts,
where policy attempts are wins + gameplay losses + parser/context policy failures.
Report the absolute trained-minus-untuned difference without treating repeats as
independent evidence. Separately give wins/completed games; terminal HP and turns
are conditional on completed gameplay and undefined when none complete. Do not
average away a scenario with no completed games.

Retain all 24 planned slots, started attempts, unattempted slots, infrastructure,
unsupported, truncated, interrupted and invalid-evidence counts. Include total and
per-decision inference time, setup/combat/wall time, generated tokens and resource
measurements where recorded. An incomplete batch has no complete macro score.
Show familiar-Louse and two-family transfer outcomes separately, with failure
examples. Do not invent confidence intervals from the four identical-start greedy
repeats, pool these with historical eight-game scores, or call this compute-matched
against PPO from scratch.

Guide milestone E's minimum evidence exists for the narrow Louse diagnostic:
untuned baseline, identified public training data, actual changed and reloaded
adapter, and controlled original-engine evaluation. This comparison can extend that
evidence to two training-unseen families. It cannot complete milestone D's broader
generalization study: that requires selected held-out comparisons, repeated training
initializations, appropriate uncertainty and failure analysis. It establishes neither
Act 1 competence nor full-run success (milestone F).
