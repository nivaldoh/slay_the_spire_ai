# WH3 checkpoint RL research and minimal implementation

2026-10-25. Handoff for an agent researching and implementing short-episode language
model reinforcement learning in WH3. Code inspected at `34f485b`; no WH3 RL trainer or
learning result exists yet. Read [state](../state.md), [checkpoints](checkpoints.md),
[post-training](../posttraining.md) and the [verification rule](../../AGENTS.md#verification-hard-rule)
before starting. This request authorizes documentation; the implementation, experiment
choices and new verification method below remain proposals. The implementation plan that
builds on this page and corrects it against the code is
[checkpoint-rl-plan.md](checkpoint-rl-plan.md).

The smallest useful prototype is a language model choosing one action from a few legal
candidates at a restored battle state. A fixed script then continues to the engine's
ending. Train a small LoRA adapter from those outcomes. This is a **contextual bandit**:
one learned decision per episode. It can test the reset, action, reward and update path
without first building multi-step real-time model control.

## Existing evidence and reusable code

The checkpoint is a replay prefix plus Lua seed, rebuilt before live handover. It is not
an instantaneous RAM snapshot. The agreed Land check passed at `6fdb271`; declared siege
cases passed at `2e2acbe`: eight identical restores matched every planned native tick and
194 live readings across four saved states under the agreed comparison. Cached infocard
stats remain separate diagnostics; 12 of those 194 raw stat rows differed. Scope and
counterexamples are in [checkpoints](checkpoints.md#siege-check). A successful restore does not establish that
the learner sees the right context, its command executes or its reward is attributed
correctly. Keep these as separate checks.

| Existing piece | Reuse and important limit |
|---|---|
| [`battle/checkpoint.py`](../../src/twwarhammer3/battle/checkpoint.py), [`checkpoint_agent.js`](../../src/twwarhammer3/engine/checkpoint_agent.js) | Launch/rebuild, tick hooks, checked native state and `restored` event. The runner currently stops at a diagnostic `stop_tick`; it does not run the ordinary policy loop or collect an RL trajectory. |
| [`battle/play.py`](../../src/twwarhammer3/battle/play.py), [`mailbox.py`](../../src/twwarhammer3/engine/mailbox.py) | Public observations, command identity, acknowledgements, engine endings and supervised cleanup. `_drive` has no checkpoint handover gate. `Mailbox.reset()` requires a stopped game. |
| [`protocol.py`](../../src/twwarhammer3/protocol.py) | `validate_orders` validates a batch. It does not enumerate legal candidates; the prototype needs a public candidate builder. |
| [`spire/language/policy.py`](../../src/spire/language/policy.py), [`sampling.py`](../../src/spire/language/sampling.py) | Pinned Qwen base, candidate sequence scores, seeded categorical sampling, artifact checks. Spire prompts and action objects are game-specific. |
| [`spire/language/rl.py`](../../src/spire/language/rl.py) | `Scorer`, `reinforce_step`, behavior-probability checks and adapter diagnostics provide numerical patterns. Its HP-shaped reward, catalog, initial supervised adapter requirement and game orchestration do not transfer directly. It has no resume. |
| [`scripts/sft_smoke.py`](../../scripts/sft_smoke.py), [`language tests`](../../tests/language/) | A small local LoRA workload and CPU toy-model test examples. The historical smoke lowered loss, but all 16 decoded actions chose index 0; 5/16 matched, equal to always choosing 0. See [evidence](../posttraining.md#first-end-to-end-test-2026-10-17). |

If a second game actually shares numerical code, move the small common functions into
`gameai`; WH3 should not import Spire decisions, rewards or training orchestration. Keep
the new game adapter small rather than building a general RL framework.

## Local hardware and resource plan

Read-only probes on 2026-10-25 found an RTX 3060 with 12,288 MiB VRAM, a Ryzen 5 5600X
(6 cores, 12 threads), about 16 GiB Windows RAM and 7.7 GiB visible to WSL. WSL had
about 2.3 GiB available and a 2 GiB swap file; these free-memory values are transient.
Qwen3-0.6B is already cached and pinned in `spire/language/policy.py`. No memory or
latency measurement has been made for the proposed WH3 RL workload.

JUDGEMENT: local_model — Codex, 2026-10-25, proposes cached Qwen3-0.6B with bf16 LoRA.
A larger or quantized model changes memory, speed and capability; feasibility rests on this choice.

Start from the existing small-model pattern: frozen base weights, small LoRA adapter,
zero dropout, one context at a time and gradient checkpointing if needed. Use the locked
`llm` extra; it conflicts with `train`. Preserve the pinned model revision, tokenizer,
chat template and dependencies in every artifact. The official [Qwen model card](https://huggingface.co/Qwen/Qwen3-0.6B)
documents the 0.6B model and disabling thinking. This choice is a plumbing test, not a
prediction that a 0.6B model can learn strong battle tactics.

Measure peak CUDA allocated/reserved memory, process RAM, scoring time and update time
with the actual prompt and candidate sizes before game collection. Measure through the
first optimizer step: optimizer state may be allocated lazily. LoRA reduces trainable
gradients and optimizer state, but sequence activations still consume memory; see
[PEFT memory guidance](https://huggingface.co/docs/peft/main/en/developer_guides/memory_efficient_training).

Use separate processes for model scoring, game execution and training. End the model
process before launching WH3, and confirm the game supervisor has closed before the next
model process. `torch.cuda.empty_cache()` does not free live tensors. The existing
`gpu_lease()` only locks cooperating language processes; WH3 does not acquire that lock.
It cannot enforce this exclusion alone. The Spire RL trainer keeps its model resident
while collecting combats, so do not copy its lifecycle unchanged.

## Proposed task and execution contract

JUDGEMENT: minimal_task — Codex, 2026-10-25, proposes one precomputed candidate decision
with fresh controller memory and fixed continuation. Live repeated decisions or resumed memory
define different tasks; the first implementation and its claims rest on this choice.

Use a small, already-supported Land Battle first. Select a checkpoint where an explicit
choice can still affect the outcome. A nearly finished battle may already be decided;
shorter episodes help only when the remaining decision matters. Audit candidate branches
before training. Do not assume that attack versus hold changes the winner.

JUDGEMENT: candidate_task — Codex, 2026-10-25, proposes a small public candidate set and
a frozen continuation script. Free-form orders or a different continuation change attainable
outcomes; the tactical-selection result rests on their declared versions.

Each candidate is a canonical ID bound to an exact validated order batch, with a public
description. Generate it from friendly state and visible enemies only. Freeze the
ordered list for that decision; never silently regenerate or reorder it at execution.
Avoid duplicate order batches under different labels. Record the continuation's version
and when it starts so it cannot immediately overwrite the chosen command. A deliberate
no-op means issuing no new order; native orders and effects continue. Bind it to an explicit
empty-batch request, matching acknowledgement and the declared boundary. It needs that
execution evidence, rather than a visible new action effect.

The serial loop is:

1. **Prepare context.** Restore a checkpoint with no model loaded. Establish a declared
   decision tick after handover, capture the normal public observation and candidate
   mapping there, then close the game. Store private restore diagnostics separately.
2. **Sample offline.** With the game stopped, score the saved context and sample choices
   from one frozen adapter. Save the full distribution and sampling evidence, then exit
   the model process. Multiple independent draws may share this context.
3. **Execute a choice.** Restore again. Wait for the matching `restored` event and the
   declared decision boundary. Compare the public state and candidate mapping with the
   saved context before issuing exactly the sampled batch. Record actual issue time and
   matching acknowledgements, then run the fixed continuation to an engine ending.
4. **Update.** Close the game. Audit the complete collection group, reload the unchanged
   collection adapter, recompute its probabilities, take one update and save an adapter.
5. **Evaluate separately.** Use the same execution contract and candidate scorer for the
   frozen starting adapter, updated adapter and random baseline.

**The decision boundary needs new integration.** A generic first mailbox observation
after handover can arrive at different simulation ticks. Equality at the checkpoint does
not prove equality at command issue. A possible implementation uses the existing tick
hooks to capture the public context and guard/dispatch the preselected command at the
declared tick, through the shared public-observation builder and normal order validation.
Prove this boundary before collecting learning data. If Python polling cannot meet it,
do not relax the state comparison until it passes; explicitly redesign the task and its
timing contract. Keep volatile transport fields separate from the compared public game
state, and document every exclusion. Do not use private Lua diagnostic readings as model
input or replace the normal validator with raw unit-controller calls.

From handover onward the battle remains unpaused at 1x. Only the rebuild may run faster.
Offline scoring removes model thinking time from the battle: report this as precomputed
tactical selection, not evidence about live API latency or real-time LLM play. Restoring
still incurs launch/menu/rebuild overhead; a short suffix is not necessarily a cheap
rollout. Measure wall time through closure and the number of executed decisions.

## Reward and a minimal update

JUDGEMENT: terminal_reward — Codex, 2026-10-25, proposes reward 1 for an engine win and
0 for an engine loss or draw, including engine timer endings. Draw credit, health shaping
or truncation penalties change the objective; the first learning result rests on this mapping.

Keep outcome and infrastructure status separate. No terminal reward comes from reaching
`stop_tick`, a supervisor timeout, a crash, restore mismatch, invalid/refused command or a
reply that was never executed. Preserve any engine ending observed before a subsequent
acknowledgement or cleanup failure, and record the failure alongside it. An engine ending
alone does not make a sampled action eligible: execution attribution must also pass.
For the first prototype, stop an incomplete collection group rather than training only
its successful members; dropping failures selectively can bias rewards by action.

JUDGEMENT: candidate_reinforce — Codex, 2026-10-25, proposes one on-policy REINFORCE step
per group with a leave-one-out baseline, without a critic or reward model. PPO, repeated
updates or a different baseline change learning; the update tests rest on this objective.

For public context `x`, let `s_j` be the summed conditional token log-probability of
candidate completion `j`, including its terminal EOS. Define the actual action policy as
`log pi(j|x) = log_softmax(s / T)[j]`, with positive recorded temperature `T`. The learner
must differentiate this normalized distribution, not just the raw chosen sequence score.
Only completion tokens contribute; prompt and padding tokens do not. Compact canonical
IDs avoid training long explanations. Tokenization, EOS and summed versus averaged token
scores are part of the policy contract.

For `B >= 2` independent draws from that same context and frozen policy, use
`b_i = sum(r_k for k != i) / (B - 1)`, detached advantage `A_i = r_i - b_i`, and minimize
`L = -mean(A_i * log pi(a_i|x))`. Keep groups separate by context, candidate mapping,
continuation and collection adapter. Compared with centering on the full group mean,
leave-one-out avoids including a sample's own reward in its baseline. All-equal rewards
give zero signal; explicitly skip the optimizer step, including weight decay/momentum.

Before an update, verify exact identities for the base, adapter tensors, tokenizer,
rendered prompt/token IDs, ordered candidate-to-order mapping and temperature. Recompute
the entire behavior distribution; a matching selected probability alone can miss a
permuted candidate mapping. Reject non-finite values and changes before mutating weights.
Record numerical deviations. Set any CUDA comparison tolerance from measured repeatability
and a known wrong-policy negative control, rather than inheriting Spire's `0.05` value.

Use deterministic scoring for both collection and differentiation: evaluation mode still
allows gradients. Spire's current update switches from `eval()` to `train()` and relies
on zero dropout. Nonzero dropout can silently change the distribution being optimized.
Likewise, `LanguagePolicy.choose` uses greedy text generation, whereas its RL sampler
scores candidates. Free greedy generation and candidate argmax are different policies;
WH3 evaluation must preserve the declared candidate-selection semantics.

The branch audit may force every candidate to establish which choices matter. Those
forced runs are not on-policy draws. Do not relabel them as such or reuse the same batch
for repeated vanilla on-policy updates after the adapter changes. Full enumeration with
an exact expected-reward objective is another possible design and requires its own
declared objective and tests. Choose learning rate, group size, token cap, update count
and any regularizer explicitly; no battle-training values were established by this research.

## Collection records and failure boundaries

Keep raw evidence and one small audited transition record per attempt. At minimum retain:

- Root/source battle identity; parent checkpoint and replay/sidecar hashes; checkpoint,
  decision, issue and ending ticks; build, executable/mod/agent/source/config hashes.
- Public observation, rendered messages and token IDs; ordered candidate IDs, descriptions
  and exact order batches; context/mapping hashes; fixed continuation identity.
- Base revision, tokenizer/template, adapter tensor hash, precision, temperature, complete
  behavior probabilities, sampling seed/draw and selected candidate ID.
- Actual command batch, job/battle/request identity, per-order acknowledgements and
  execution status; independent engine ending, infrastructure status and reward version.
- Update input IDs, before/after adapter hashes, recomputation deviations, advantage,
  loss, gradient norm and saved-artifact identity. A collection record is consumed at most
  once by this update design.

The trainer should consume an explicit audited transition format. Existing exports are
valuable evidence, but are not automatically suitable RL inputs:

- [`play._drive`](../../src/twwarhammer3/battle/play.py) retains a model exchange even
  when the battle ends during the call and its reply is never sent.
  [`export._decisions`](../../src/twwarhammer3/battle/export.py) preserves such exchanges;
  [`gameai.sft.target`](../../src/gameai/sft.py) accepts completed replies without requiring
  execution. Winner-filtered text is therefore not proof of an action that caused a win.
- `play` retains `engine_ending` across late failures, but the current exporter derives
  `gameplay_outcome` from top-level `status`. Reconcile these deliberately for reward
  extraction; do not silently discard a real ending or reward a failed action.
- Native restoration does not serialize Python policy notes, last-seen maps, pending
  model threads, skills, delayed observations or bridge sequence/request state. Start
  fresh controller state for this task. Native queued orders and in-flight effects still
  continue; fresh controller memory does not clear them.
- `Mailbox.reset()` must not run live at handover. Reject stale/foreign observations and
  acknowledgements without deleting the active bridge. Replays displaced by the restore
  runner must be returned unchanged after exceptions and interrupts.

Group train/validation/test splits by **root source battle and all descendants**, not by
individual checkpoint or rollout. Also account for scenario families that share armies
and setup. Checkpoint filenames, root IDs, private enemy totals, branch rewards and future
events belong in metadata, never the prompt. Looking at held-out branch outcomes while
designing candidates or tuning updates contaminates the held-out set.

## Proposed unit and component tests

JUDGEMENT: verification_plan — Codex, 2026-10-25, proposes the independent numerical,
boundary and live checks below. Weaker smoke checks or different controls establish different
claims; owner agreement is required before recording this as an agreed verification method.

Use small CPU tensors and real production functions for the numerical core. Fake the
engine, clocks and file events at the external boundary; do not fake the learner or the
function whose correctness is being asserted. The oracle should be a hand calculation,
an independent slow implementation or the stated contract. Share fixtures where helpful,
not the production calculation that determines the expected answer.

| Check | Independent reference and likely bug it catches |
|---|---|
| Candidate scores and gradients | Compare batching with a slow, token-by-token causal likelihood calculation on a tiny model. Include unequal completion lengths, EOS, padding and the first completion token. Compare gradients too. Detects masking, causal shift, accidental prompt loss and detached scores. |
| Token and parameter limits | Reject oversized contexts without silent truncation. Verify optimizer parameters are exactly the allowed LoRA tensors and base tensors stay unchanged. Non-finite logits, loss, gradients or adapter values must not produce a completed update. Detects missing context, accidental full fine-tuning and corrupt updates. |
| Categorical policy | Hand-calculate a two-candidate distribution at different temperatures; check normalization and invariance to a shared score offset. For one term with logits `z = s/T`, check every derivative against `dL/dz_j = -A * (indicator(j=a) - p_j)` or finite differences. Use a fixed draw to reproduce the chosen action. Detects missing/double temperature and training on unnormalized sequence likelihoods, even when update direction looks right. |
| Update direction | With a scalar two-action logit and a sufficiently small SGD step, positive advantage increases the chosen probability and negative decreases it. Reverse rewards from the same initial state and require reversed direction. Detects a flipped sign or reward/index misassociation. |
| Zero signal | Equal rewards yield zero advantages and no optimizer step. Run this after a nonzero step has populated momentum; adapter and optimizer state must remain unchanged. Detects weight decay or momentum moving weights during a claimed no-op. |
| Baseline and grouping | Hand-compute leave-one-out advantages, reject single-member groups and non-finite rewards, and prevent mixing context/adapter/continuation identities. Detects self-inclusion or averaging incompatible tasks. |
| Behavior association | Tamper with weights, prompt tokens, tokenizer, candidate order-to-batch mapping and temperature separately. Include equal-probability candidates, so hashes rather than distribution differences must catch the mapping change. Every rejection precedes any optimizer mutation. |
| Same policy throughout | Collection and gradient-enabled scoring produce the same distribution under the declared deterministic mode. Reject unsupported stochastic dropout. Verify evaluation uses the candidate scorer; a deliberately different free decoder must not affect its action. |
| Public inputs | Insert unique sentinels into hidden evaluation/final/setup fields, unseen enemies' hidden current state, rewards and checkpoint metadata. Perturb these while public state is fixed; prompt/candidates must remain unchanged. Preserve public lobby rosters and legitimately recorded last-seen information. Detects answer leakage and visibility violations. |
| Restore and decision gate | Feed pre-handover, wrong-checkpoint, stale and late observations before the matching event/state/tick. Assert no command is sent early and a changed public state aborts. Detects playing during rebuild or training on the wrong state. |
| Command attribution | Observe one exact selected batch and matching request/per-order acknowledgements. Wrong job/battle/request, duplicate delivery, refused/partial execution and ending-before-send cannot become valid rewarded actions. Test explicit no-op separately. Assert continuation does not overwrite the action at the boundary. |
| Outcome extraction | Test engine win/loss/draw and timer endings, timeout without ending, restore failure, and engine win followed by cleanup failure. Expect separate outcome and infrastructure fields under the proposed reward contract. Detects false losses, false wins and lost ending evidence. |
| Artifact integrity | Reload a saved adapter onto a fresh base and require exact tensors plus matching candidate probabilities within a measured precision tolerance. Corrupt/missing keys and wrong base/tokenizer must fail. Detects silently partial PEFT loads or evaluating the wrong weights. |
| Lifecycle and interruption | Mock process/lease transitions and inject exceptions in scoring, restore, execution, update and save. Assert no game/model overlap, closure, restored bystander replays and no partial artifact marked complete. Reject duplicate transition consumption. Either explicitly refuse resume or test optimizer/RNG/cursor equivalence to an uninterrupted run. |
| Split leakage | Fork several checkpoints from one source battle and put a sibling in another split: validation must fail. Also test declared related scenario families. Detects memorized battle outcomes masquerading as generalization. |

Reuse relevant examples in [`test_language_policy.py`](../../tests/language/test_language_policy.py),
[`test_language_sampling.py`](../../tests/language/test_language_sampling.py),
[`test_language_rl.py`](../../tests/language/test_language_rl.py),
[`test_wh3_play.py`](../../tests/twwarhammer3/test_wh3_play.py) and
[`test_wh3_checkpoint.py`](../../tests/twwarhammer3/test_wh3_checkpoint.py).
The current RL tests cover positive/zero advantage and behavior mismatch; they do not
already provide the negative-advantage, reward-reversal or WH3 execution checks above.
Preserve the frozen Spire protocol/policies and unique test filenames. Keep scratch data
under `runs/test-scratch/`. Run focused pytest with `-ra` and Ruff; report optional
dependency skips as unavailable evidence rather than passes.

For each important check, show that a plausible broken variant fails: omit the causal
shift, flip the reward sign, swap equal-probability candidate mappings, remove the handover
gate or accept an unexecuted reply. A small explicit negative control is enough; no broad
mutation-testing framework is needed. Add the smallest regression for each observed bug.

## Live checks and the first implementation sequence

Unit tests establish the mathematical and record-processing contracts. A repeatable live
check must independently establish restoration, command effect and actual reward:

1. **Measure the model workload with the game stopped.** Score the intended contexts,
   run one toy-reward update, reload it and compare probabilities. Record memory/latency
   and distinguish a successful optimizer call from useful tactical learning.
2. **Prove the decision boundary and branch effects without learning.** Force each
   candidate from the same checkpoint, with the frozen continuation. Repeat identical
   branches; require checked start state, actual issue/ack evidence, a visible action
   witness (explicit boundary/empty-batch evidence for no-op) and engine ending. If branch
   outcomes do not distinguish the choices, choose another development checkpoint before
   spending time on RL.
3. **Perform one audited local update.** Draw a complete group from the frozen candidate
   policy, execute those choices, recompute behavior probabilities and update once. A
   draw group with no reward variation is valid but provides no signal; do not silently
   resample until a favorable group appears. Save/reload and inspect the resulting
   candidate probability change alongside the numerical controls.
4. **Test learning separately.** Compare updated, frozen-start and random policies with
   the same candidates, timing and continuation. Permute displayed candidate IDs/order
   while preserving action meanings to expose index preference. Expect possible label
   sensitivity; measure it rather than requiring a language model to be exactly invariant.
5. **Test transfer only when ready.** Use untouched root battles, earlier checkpoints and
   relevant tactical variants. Report each stratum separately before pooling. Choose
   counts, seeds, stopping rules and the improvement criterion before viewing those results.

For an initial development checkpoint whose branches are deterministic and exhaustively
audited, the policy's probability mass on winning candidates is an interpretable measure.
It is still a result on that checkpoint. Repeated deterministic restores test consistency,
not independent new battles; report unique sources, checkpoints, action draws and launches
separately. If execution timing makes outcomes vary, collect and report that variation.

Build only the public context/candidate adapter, checked one-decision runner, audited
records, small numerical update and a recount command needed for these stages. Initially
refusing training resume is acceptable if an interruption preserves the last complete
adapter and incomplete batches cannot be reused accidentally. Full resume needs adapter,
optimizer, RNG, rollout cursor and consumption state; loading weights alone is not resume.

The proposed implementation rests on JUDGEMENT `docs/twwarhammer3/checkpoint-rl.md`
`local_model`, `minimal_task`, `candidate_task`, `terminal_reward`, `candidate_reinforce`
and `verification_plan`. Before game-training experiments, settle the concrete task,
continuation, timing, reward, resource window and repeatable pass criteria with the owner.
Agreement adopts a method; passing it at a recorded revision establishes its stated scope.

## Main risks and later research

- **No learnable signal.** The prefix or continuation can determine every outcome. Audit
  branches first; zero-variance rewards cannot teach the proposed chooser.
- **Training the wrong policy.** Candidate indexing, token masks, EOS, temperature,
  dropout and a different evaluation decoder can each produce apparently successful
  updates to a different distribution. Preserve one scoring contract end to end.
- **Rewarding an action that never happened.** A completed model exchange, successful
  file write or aggregate acknowledgement is insufficient. Bind exact commands to
  execution and independent engine endings; preserve failed attempts for audit.
- **Incomplete reset.** Bridge/controller state and wall-clock script timers are outside
  the native checkpoint contract. Source scripts must replay consistently, and native
  checksums alone miss some siege resources. Keep the independent readings required by
  [checkpoint limits](checkpoints.md#limits); do not extend scope from one battle type.
- **Memorization and selection bias.** One checkpoint can demonstrate plumbing or fitting.
  It cannot show general tactics, full-battle gains or better sample efficiency. Keep
  descendant splits together and preserve failed/unfavorable rollouts.
- **Resource and throughput limits.** Host RAM may constrain the workload before VRAM.
  Serial phases avoid coexistence but add model loads and game rebuilds. Measure useful
  decisions per hour; an OOM must leave no artifact or rollout marked complete.
- **Policy collapse and unstable updates.** A wrong reward or large step can concentrate
  all probability on one candidate. Log distributions and KL change, compare with frozen
  and index baselines, and decide regularization from observed needs. Falling loss and
  changing adapter tensors alone do not demonstrate correct learning.

Starting near a goal and moving starts earlier has precedent in
[Reverse Curriculum Generation](https://arxiv.org/abs/1707.05300) (Florensa et al., 2017),
which studies simulated navigation and manipulation. It motivates checkpoint curricula;
it does not establish data savings for WH3 or LLMs. A later curriculum should expand to
harder starts only under a declared success rule, rather than quietly selecting easy wins.

[Back to Basics](https://arxiv.org/abs/2402.14740) (Ahmadian et al., 2024) studies simpler
REINFORCE-style alternatives to PPO for language-model alignment. It supports investigating
a critic-free first prototype; its RLHF results are not WH3 evidence. Multi-step online
play, open-ended order generation, SFT from audited winners, KL/entropy regularization,
remote training and full-battle evaluation are later designs with separate tests.

## Open owner choices (decision 11)

Moved verbatim from the [state page](../state.md#owner-decisions-waiting) inbox on 2026-10-28
to keep the inbox short. The branch's own pages hold the evidence.

**Checkpoint RL.** The [night's run](log.md#2026-10-26-checkpoint-rl-implemented-and-run-stage-3-fails-the-policy-collapses)
stopped where the plan needs you. (a) The first method collapses whenever the right
choice depends on the state (synthetic check and its re-run: one action; the two-rung
ladder: one displayed slot); no state-loading bug was found. The log objective you approved
avoids the collapse but fails the gate, and the gate is confounded (a spearmen-distance
shortcut would pass it): de-confound the generator (e.g. f1/f2 classes disagreeing in a
fixed share of tasks, or F2READ as a pass condition) and/or render f2's distance on the
fall-back line, then rerun the log method (about 2 h of GPU with its control). Done for
the generator (v2, my choice under your delegation): training 0.96, held out 0.76, a
generalisation finding. Choose: more varied training layouts (18 recorded jobs fit), a larger
budget, a rendering that states f2's distance next to its choice, or not gating stages 4/5 on
this check (you said "Stop here" for now, 2026-10-26). (b) Review
the choices made without you (`runs/twwarhammer3/rl/plans/expansion-declaration.md`):
the second root, K 1 for the synthetic check, stage 4 before stage 3, the result-collapse
gap rule, the 1e-6 first-order floor, the 1e-4 reload tolerance, the flat-rung skip rule,
the re-run's form (continued from the first run's adapter), stopping each moot control,
the 16-task diagnostic with its reading thresholds, and synthetic v2 (share 0.5, class drawn
once per task). (c) Agreed 2026-10-26: the
stage 1 and stage 4 checks (you chose to stop here for review). (d) Merge the branch: it changes the
mod pack, so the siege and team checks would read "runtime changed since" (re-run them?).
