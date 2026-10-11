# Research contract

## Current question

Can a small randomly initialized masked PPO policy improve terminal health over uniform
random play on the verified fixed two-Louse combat? The immediate pilot tests correct
weight updates, original-engine collection, interruption/resume, and frozen evaluation.
It does not test unseen encounters or independent game seeds.

## Initial scope

- Original Steam engine, fixed Workshop jars, personal profile slot 0 as authorized.
- Seeded `START` and a fixed noncombat prefix. No arbitrary combat reset is claimed.
- A random legal policy followed by an explicit heuristic baseline.
- Raw engine state is diagnostic evidence; policies receive a separate allowlisted view.
- Exclude seeds, RNG state, unrevealed draw order, and private monster state from policies.
- Record terminal gameplay outcomes separately from limits and bridge failures.
- Preserve every attempt and attribute observations/actions to a unique decision state.

The fixed development suite supports the initial training diagnostic. No held-out final
evaluation suite is established yet. Milestone B evidence for this narrow case now
includes the declared start, mechanic coverage, repeat resets, throughput, and baselines.

## Bootstrap findings, 2026-10-11

The original engine is available through CommunicationMod. A seeded JVM restart plus
Neow `Talk → Obtain 100 Gold → Leave` and leftmost first-floor node produces two Louses,
80 HP, the starter deck and Burning Blood on `SPIREAI1` with the inspected profile.
Two random fights completed with health outcomes 70/76; two deterministic heuristic
replays produced the same 13 public decisions and 18 commands, ending at 80 HP.
These observations establish a reproducible diagnostic case, not generalization.

A real timing defect was found before freezing the benchmark: CommunicationMod reports
`ready_for_command=true` with initial enemy intents still `DEBUG`. A recorded `WAIT 60`
(60 frames) resolves them to BUFF/ATTACK; a second wait leaves public state unchanged.
The runner now settles this initial state, with a three-wait cap, before requesting a
policy action. Waits are environment actions and must never become PPO samples.
Pre-fix results remain infrastructure evidence; rerun baselines under the settled prefix.

The next learning question is intentionally small: can a randomly initialized, public-
information candidate-action scorer improve terminal health over random play on this
fixed encounter? A successful pilot proves data flow and weight training, not unseen-seed
or unseen-encounter ability. The deterministic heuristic provides a disclosed reference
comparison for this case. Development repetitions share the same game seed and therefore
are not independent game scenarios; report their scope and stochastic-policy variability.

Initial reward proposal: zero during combat; on a win, `1 + 0.25 * terminal_hp / max_hp`;
on defeat, `-1`. Terminal HP includes Burning Blood healing and is bounded by max HP.
Report wins, terminal HP, turns, invalid actions, and infrastructure attempts separately
from return. Only complete, audited episodes from one frozen behavior version may enter
an initial PPO update. Interrupted or unsupported episodes remain recorded but excluded.

Use optional pinned PyTorch 2.13.0 CPU for the small first learner. Original-engine
collection takes roughly 30 seconds per combat and dominates a <50,000-parameter network;
GPU use is unnecessary for this pilot. The RTX 3060 remains available for later measured
workloads. No Gymnasium/CleanRL runtime dependency or extra simulator is introduced.

An end-turn-only loss probe verified DEATH→seeded-restart twice with the same settled
combat-start hash. The engine's seeded Neow path chooses four options from seed-driven
reward categories rather than profile eligibility. Profile unlock progress was 817
before, between, and after these two losses; continue recording it rather than treating
that observation as an invariant for all runs.

## First original-engine learning pilot contract

Planned run: `runs/ppo-pilot-seed0-20261011`. Source is frozen at the integrated training
revision before launch. Initialization seed 0; CPU set encoder/candidate scorer, 12,498
parameters; PPO defaults documented in [learning.md](learning.md). Collect complete
episodes only, update after at least 64 transitions, with ceilings of 8 attempts,
2 updates, and 900 seconds from the original start (resuming does not replenish time).
The deliberate interruption during a later attempt counts against the attempt budget.

Baseline evidence is the completed eight-attempt suite for random and heuristic under
`louse-diagnostic-development-v1`: both 8/8 wins, random mean final HP68 (range50–80),
heuristic HP77 in every episode. No rejected actions or infrastructure failures. The
random suite yielded 115 validated transitions in 270.58 episode-seconds; heuristic 168
in306.35 seconds. These repetitions share one game scenario; the random outcome range
is policy sampling variation, and repeated heuristic outputs do not add independent
scenario coverage. Canonical evaluation uses eight fixed policy seeds starting at 1000.

Pilot acceptance requires: audited engine transitions matched to logged behavior
probabilities and candidate identities; nonzero actor-weight changes and finite
optimization; completed evidence preserved across intentional interruption; no repeated
transition ingestion; original absolute deadline preserved; and evaluation loading the
exact frozen exported artifact. Save/evaluate the initial artifact as well as the trained
one. An unchanged or worse gameplay score remains a valid computational pilot, but no
policy improvement will be claimed from it. A metadata, resume, or optimizer failure
invalidates the affected experiment and must be repaired before extending training.

The initial result will decide whether to increase the budget or fix a measured data-flow
or learning problem. It will not select on a held-out final test. Broader mechanics and
encounter generalization remain separate later experiments.

## Pilot computational result

The seed-0 pilot at source `741d96a` completed in 310.94 seconds, with 8 attempts
(7 verified wins and one deliberate interruption), 92 unique audited transitions,
and 2 updates. All 3,201 actor parameters changed; values, parameters, and optimizer
state are finite. Resume preserved the original 900-second deadline and completed
trace, reproduced the interrupted prefix, and excluded its samples. The exported
final tensor hash is `0aef9e7e0bebaab135f2621d42d743606cb9c6d129c37c1aed9c0e2fb540d52b`.

The [computational audit](results/ppo-pilot-training-audit.json) supports real weight
training and recovery. Frozen initial/final evaluations are now running at source
`70b08b0` with unchanged suite and rollout semantics. That source adds stricter
report-comparability and suite-declaration validation. Do not infer gameplay
improvement from tensor changes or training wins.

## Next budget increase (declared before launch)

Conditional on valid frozen pilot evaluations, the next run is
`runs/ppo-budget64-seed0-20261011`: fresh seed-0 initialization, the same network,
PPO defaults, 64-transition batches, reward, fixed scenario and canonical evaluation.
Only the training budget increases, to at most 64 attempts, 16 updates and 3,000
wall-clock seconds, whichever limit arrives first. No deliberate interruption is
planned. The initial model hash must match the pilot's initial artifact; this repeats
its initial sampling stream and is not an independent training replicate.

Hypothesis: more complete-episode updates will produce a useful action-distribution
change and higher ending health on the fixed development suite. Pilot initial control:
8/8 wins, mean HP72.75, range53–80. Evaluate the final budget-limited export, without
selecting among checkpoints by evaluation score, on the same eight sampling seeds.
Check wins and infrastructure counts as well as HP; unchanged/worse scores or lower
win rate count against improvement. This comparison remains development on one game
scenario. It cannot establish unseen-seed ability or robustness across initialization
seeds. No reward, encoder, environment or scoring change is bundled into this trial.

The initial neural evaluation averaged 31.99 seconds per episode, so 64 attempts
would take about 34 minutes at that rate. The 50-minute hard budget permits ordinary
variation; a separate eight-attempt frozen evaluation is reserved afterward. Disk
headroom is 396 GiB; the first pilot occupied 7.6 MiB including checkpoints and traces.
CPU inference/update cost is small relative to game collection. New training uses
an independent run directory and deadline; it does not extend the completed pilot.

## Evaluation infrastructure interruption

Initial evaluation finished 8/8 wins, mean HP72.75. The first trained evaluation
matched its first five outcomes, then failed at relay startup before policy action
on sampling seed1005. Random WSL port53899 was Windows-reserved. This is an
infrastructure failure, not a loss; the partial evaluation remains invalid.

The fixed-port repair changes transport setup and diagnostics, preserving game,
mods, observations, policy artifact, prefix, scoring and suite. A new full trained
evaluation uses all eight original sampling seeds after 50 socket round trips and
305 passing tests. Preserve the original six attempts (five games plus startup
failure) alongside the rerun; do not pool repeated games as independent samples.
The larger training trial remains gated on completing this frozen comparison.

## Accepted pilot outcome

The repaired full trained evaluation at `acb1bd3` completed all eight attempts,
with no infrastructure failure or invalid action. Initial and trained artifacts
both won 8/8 and ended at HP [80,66,76,78,77,53,80,72], mean72.75. All 100 paired
actions and their public transitions matched exactly (`compare_resets` over the
independently audited corresponding episodes); ending-health differences were zero.
The fixed transport port preserved the normalized game behavior in these traces.

Random baseline mean HP68 and heuristic HP77 use the same declared protocol and
suite. The initialized network's higher point estimate than uniform random is not
evidence of training, and the two-update policy shows no improvement over its own
initial control. Every frozen snapshot hash matches the expected exported artifact.
[Comparison](results/ppo-pilot-development-v1.json) and
[paired evidence](results/ppo-pilot-paired-evaluation.json) are generated from traces.

The computational pilot is accepted: actual actor/probability changes, finite PPO,
audited behavior data, interruption/resume, and frozen evaluation all work. The
next declared budget increase can now run. The heuristic remains the strongest
measured policy on this fixed diagnostic; no generalization result exists.
