# Outcome-based language post-training (REINFORCE v1)

Declared before any sampled combat or outcome-based update. Supervised imitation
cannot exceed its teacher. This experiment asks whether on-policy policy-gradient
updates from original-engine combat outcomes can improve the adopted supervised
language adapter on the scenarios it trains on.

## Policy and data flow

- **Base:** the adapter adopted by the [relabel experiment](language-relabel-experiment.md)
  decision rule. The update starts from its exact saved tensors; the base Qwen
  snapshot, prompt format and LoRA shape are unchanged.
- **Behavior policy:** `language_sampling.CandidateSampler`. The model scores every
  canonical `{"a":N}` completion of the public prompt
  (`language_policy.candidate_log_probs`) and normalizes over the legal choices at
  temperature T. A seeded per-combat RNG draws one choice. Every draw, normalized
  log-probability vector and adapter hash is written to the audited trace, so
  `audit_run` can verify the draw without the model. Legality holds by construction:
  there are no parser failures, retries or fallbacks.
- **Rollout unit:** one complete combat in the original engine (fresh JVM, settled
  seeded start), on the three `starter-three-encounter-development-v1` scenarios.
  One iteration collects a group of 4 combats per scenario (12 combats) with the
  declared seed formula `seed·10⁶ + iteration·10³ + scenario·10² + member`.
- **Reward:** the existing PPO terminal reward, `1 + 0.25·HP/maxHP` for an
  engine-confirmed win and `−1` for a death. The **advantage** is the reward minus its
  scenario-group mean: identical outcomes give no gradient. A non-completed combat
  stops the job before any update; it is never treated as a loss.
- **Update:** recompute every collected decision's normalized log-probabilities from
  its public prompt, and require them to match the recorded behavior within 0.05.
  Then take one AdamW step (learning rate 1e-4, weight decay 0.01, gradient-norm clip
  1) on `−Σ A·log π(a|s) / decisions`. Only the scored completion tokens of the chosen
  legal choice carry the loss; the prompt text is never trained. Record the loss,
  gradient norm, changed elements and mean behavior-to-updated KL over the batch.
- **Budget:** 5 iterations (60 combats), at most 4,500 seconds for the whole job,
  under an outer process limit. There is no resume and no retry. Each completed
  iteration saves its adapter and declaration. The last completed iteration is the
  final artifact; no intermediate checkpoint is selected by score.

**Temperature rule.** T is fixed before collection, from the base adapter's own greedy
catalog trajectories. Choose the smallest T in {1, 1.5, 2, 3} for which the mean
probability of leaving the greedy choice, across those trajectory decisions, is at
least 0.05 (about one exploratory action per 20 decisions). Record the measurement.
If no T in the set reaches 0.05, use 3 and report the shortfall.

## Evaluation and decision

Evaluate the final adapter once with the unchanged frozen greedy language evaluator
on the same 12-slot catalog (1,800-second cap, no retry). Compare it with the base
adapter's catalog result. Report per-scenario wins over policy attempts, ending HP,
turns and failures, plus per-iteration sampled rewards, zero-signal groups, KL and
association deviation.

Call it an improvement only if macro ending HP rises above the base's with no fewer
wins and no policy or infrastructure failures. Report an unchanged result as no
improvement, and a lower result as a regression. Run `audit_language_rl` on the
stopped job; any broken adapter chain, reward or behavior identity invalidates the run.

The training objective normalizes only over legal completions; it does not watch
probability mass on illegal text. The greedy evaluator generates tokens freely, so
any rise in invalid completions shows up there as policy failures, which the
improvement rule forbids.

## Limitations

Training and evaluation use the same three deterministic seeded scenarios, so any
gain may be a memorized line rather than a better general policy. One seed, five
updates and a small group give a high-variance gradient. The headroom is small: the
best observed macro HP is 76.33, and the maximum after Burning Blood is 80. This
experiment tests whether a correct end-to-end outcome-based update works on the
original engine. It is not a generalization study or an Act 1 result.
