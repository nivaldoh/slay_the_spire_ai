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
episodes only, normally update after at least 64 transitions, with ceilings of 8 attempts,
2 updates, and 900 seconds from the original start (resuming does not replenish time).
The deliberate interruption during a later attempt counts against the attempt budget.
The already implemented collector flushes a smaller complete-episode tail batch when
the attempt ceiling is reached, provided time and update budget remain. It does not
flush after the wall-clock deadline or consume an incomplete episode. This clarification
describes the original implementation: the pilot's updates used 81 and 11 transitions.

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
training and recovery. Frozen initial evaluation completed at `70b08b0`; the repaired
full trained evaluation completed at `acb1bd3`, as recorded below. The former adds
stricter report-comparability and suite-declaration validation; the latter repairs
relay startup while preserving the suite and gameplay semantics. Do not infer gameplay
improvement from tensor changes or training wins.

## Next budget increase (declared before launch)

Conditional on valid frozen pilot evaluations, the next run is
`runs/ppo-budget64-seed0-20261011`: fresh seed-0 initialization, the same network,
PPO defaults, a 64-transition collection threshold with the existing attempt-limit
tail-batch flush described above, reward, fixed scenario and canonical evaluation.
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

## Budget-64 result

The declared budget-only trial at `7b4cc31` completed 64 attempts, all wins, 12 PPO
updates and 827 audited transitions in 2,298.47 seconds. The final 57-transition tail
batch follows the existing attempt-limit rule. All 30 applicable verifier checks pass,
including behavior probabilities, optimizer state, data lineage, unique ingestion,
source pins, and finite updates. The first update exactly reproduced the pilot from
the same initialization and first 81 transitions; this is not an independent replicate.

The final export `03ca30dc29154b968686a918efb0d4579d99c3142461ee2507a33138b18bbd22`
was evaluated without checkpoint selection. Result: 8/8 wins, ending HP
[80, 66, 76, 78, 71, 53, 80, 72], mean 72.0, compared with 72.75 for the exactly
matching initial tensor artifact, 72.75 for the pilot, 68 for random, and 77 for the
heuristic. There were no invalid actions or infrastructure failures. Six paired
command/public transition sequences were identical. Sampling seed 1004 first diverged
at turn 2, selecting a Strike at the second Louse instead of Defend from the same public
state; the subsequent trajectory ended six HP lower. Seed 1005 differed at a later
action but ended at the same 53 HP. Shared command prefixes had identical public
transitions. These observations locate behavioral differences, not a counterfactual
causal test of a single action, since subsequent actions and random-event streams may
diverge.

Decision: **reject** the increased budget as an improvement on this fixed diagnostic.
Keep its valid learning/evaluation evidence. A0 Louse wins are saturated and the health
term produces only a small optimization signal; this is a plausible limitation, not a
measured cause or a reason to alter reward within the completed experiment. The next
work broadens verified development conditions under the inventory below, while a
separate pretrained-model imitation diagnostic tests the language track. No unseen-
scenario performance or robust improvement is claimed.

See the generated [comparison](results/ppo-budget64-development-v1.json),
[paired evidence](results/ppo-budget64-paired-evaluation.json), and
[training audit](results/ppo-budget64-training-audit.json). Raw artifacts remain local.

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

## Bounded development inventory contract (declared before launch)

After the active long trial and its frozen evaluation finish, inventory additional
public first-combat starts under the existing engine/mod pins, observation contract,
fresh-JVM reset and settled-v2 prefix. This proposal does not change the active trial,
its final-artifact selection, or v1 results. Freeze an inventory manifest/source revision
before collection; no neural policy or performance-guided seed selection is involved.

Use this exact discovery order, without substitutions:
`SPIREINV01`, `SPIREINV02`, `SPIREINV03`, `SPIREINV04`, `SPIREINV05`, `SPIREINV06`,
`SPIREINV07`, `SPIREINV08`, `SPIREINV09`, `SPIREINV10`, `SPIREINV11`, `SPIREINV12`.
These are proposed inputs, not claims that any seed produces an eligible encounter.

Cap the entire inventory at **24 fresh-JVM attempts and 1,800 wall-clock seconds**,
whichever comes first. Each attempt retains the current 500-action, 180-second episode
and 45-second bridge limits, clipped to the remaining overall time. Reserve attempts
in this order:

1. One deterministic heuristic sentinel on existing `SPIREAI1`, requiring the frozen
   v1 start and replay. Abort inventory if that known condition differs.
2. One deterministic heuristic discovery fight per listed seed, in order. Record every
   rejection and infrastructure attempt. A gameplay loss is a completed observation,
   not a reason to exclude a seed.
3. Select the first two preliminarily eligible seeds in discovery order per family
   (`cultist`, `jaw_worm`, `two_louses`), at most six. Repeat one full deterministic
   heuristic fight for each, retaining this selection even if a repeat fails. Do not
   backfill from later seeds based on outcomes.
4. One end-turn-only diagnostic per represented family, on its first admitted seed,
   at most three. These probes collect public enemy-power timing and DEATH evidence;
   their rewards never enter training or a policy performance comparison.
5. Repeat the existing v1 heuristic sentinel after the probes, checking that loss/reset
   activity has preserved its known start and public replay.

This uses at most 23 planned attempts. One additional attempt is reserved for the
first infrastructure failure only, immediately retrying the same assignment with the
same policy. Retain both records; a second infrastructure failure stops collection.
Unsupported gameplay, wrong conditions and unstable repeats receive no retry. A time
limit leaves explicit unattempted assignments and an incomplete inventory, rather than
silently shrinking a denominator. No additional seeds are searched to fill missing families.

Preliminary eligibility requires the normal original-engine first-floor MonsterRoom,
Ironclad A0, settled known intents, **80/80 HP**, 199 gold from the existing 100-gold
Neow choice, exactly five unupgraded Strike_R, four unupgraded Defend_R and one unupgraded
Bash, only Burning Blood, and empty potion slots. Keep the existing prefix's max-HP
preference: if it chooses max HP, record the variant as ineligible for this inventory;
do not change choices to manufacture eligibility. Allowed ordered monster IDs are
exactly `[Cultist]`, `[JawWorm]`, or two entries drawn from `FuzzyLouseNormal` and
`FuzzyLouseDefensive`. Preserve order and composition rather than pooling Louse variants.

Admission additionally requires an audited complete fight using only supported actions,
no private policy fields, and a repeated settled-start fingerprint with identical full
heuristic commands and public transitions. Record prefix commands, profile snapshots,
source revision, engine/mod hashes, discovery/repeat trace hashes and the public start
for each candidate. An unsupported card, choice or potion-dependent state, unexplained
state difference, mismatched composition, or invalid evidence prevents admission;
terminal health and win/loss do not determine eligibility.

Extract only actually observed minimal public mechanics: Cultist Ritual appearance,
Strength changes and subsequent displayed attack damage; Jaw Worm block, Strength and
mixed intents across turns; added Louse compositions' Curl Up, Weak/Strength and target
slot identity after a death. Also retain energy/card effects, block clearing, engine
terminal status and Burning Blood healing where observed. End-turn probes may not expose
every mechanic; report missing evidence instead of changing seeds or inventing coverage.

All admitted scenarios remain **development**. Freeze an explicit schema-2 catalog only
after checking discovery evidence, with no placeholder fingerprints. This inventory
does not create a held-out evaluation: a later contract must separate unseen seeds
within familiar families from entirely held-out encounter families before training or
tuning on the resulting catalog. See [scenario-expansion.md](scenario-expansion.md).

## Completed bounded inventory and next development comparison

The inventory ran at `cbe09ed` for 576.17 seconds and completed its fixed schedule
in 18 attempts: 10 wins, two deliberate end-turn losses, and six unsupported attempts.
These counts include discovery, exact repeats and sentinels; they are not policy win-rate
estimates. Of 12 discovery seeds, four completed with excluded 88-HP starts, six were
unsupported, and two met the declared 80-HP conditions. No infrastructure failure or
retry occurred. Both final admissions reproduced their entire heuristic public traces:
`SPIREINV07` (Cultist) and `SPIREINV09` (Jaw Worm). Both end-turn probes reached engine
DEATH, and the final v1 sentinel matched the initial/reference trace exactly.

An independent post-run check verified every child file hash and original trace audit,
both admission replays and both sentinel comparisons. The compact
[inventory record](results/starter-inventory-20261011.json) retains all rejections,
limits, provenance and admitted start/trace hashes. No additional seed replaced a
rejection. The 88-HP fights can support separately labelled mechanics observations,
but are excluded from this inventory's 80-HP development catalog.

The new `starter-three-encounter-development-v1` catalog combines the existing
`SPIREAI1` mixed Louses with these two admissions. Every scenario has four explicitly
scheduled policy sampling seeds, 2000–2003, in seed-major round-robin order (12 attempts
per policy). All start at 80/80 HP with the unupgraded starter deck, Burning Blood and
empty potion slots. Preserve exact monster order and public start hashes. These are
three game scenarios, not twelve independent environment samples.

Next comparison, declared before running catalog policies: uniform random, the public
heuristic, the seed-0 initial neural artifact `1d60fa62…`, and the final budget-64 neural
artifact `03ca30dc…`. The question is whether the fixed Louse-trained policy's behavior
transfers to the two newly verified encounters. No new training or intermediate
checkpoint selection precedes this comparison. Report each scenario and equal-scenario
macro metrics, all attempts/failures, ending HP, turns and inference/runtime cost. The
same 500-action/180-second episode limits apply, with a separate 1,200-second maximum
per policy batch; incomplete batches remain incomplete and cannot yield a full macro
score. Reserve all four policies, up to 48 attempts, with no outcome-conditioned reruns.

The Cultist and Jaw Worm were absent from this policy's training, but this is still a
small development comparison with one training initialization. It does not establish
robust held-out performance. Broader training, repeated initialization seeds and a
separately declared held-out split remain later work. The language imitation diagnostic
keeps its original fixed-Louse suite and cannot be scored as this catalog experiment.

## Optimization-scale diagnosis and next comparison

Read-only reconstruction of the saved budget-64 batches found 136 Adam steps across
12 updates. Logged mean approximate KL never exceeded 9.48e-6 against the 0.02 stop
threshold; full-batch before/after KL peaked at 3.91e-5. Weighted entropy gradients
were 0.00055% of policy gradients at the first update and 0.54% at the last. Entropy
dominance is therefore not supported by these measured batches. Critic value loss
fell from 0.2653 to 0.001079, while the final actor remained nearly uniform on the
fixed 100-state diagnostic. See the source/checkpoint/trace-linked
[gradient diagnostic](results/ppo-budget64-gradient-diagnostic.json).

Early raw advantages strongly correlated with actions remaining until termination
(-0.990 in the first batch). All 64 training games won, and terminal rewards ranged
from 1.10 to 1.25. Critic fitting and delayed health credit are plausible limitations.
Gradient magnitudes alone do not prove a cause: advantages are normalized and Adam
rescales updates. Do not change reward, GAE or initialization alongside the next test.

After completing the already declared four-policy catalog comparison, test only
Adam learning rate **0.0003 → 0.003**. Run a fresh seed-0 initialization under the same
64-attempt, 16-update and 3,000-second ceilings, 64-transition batch threshold,
existing tail flush, fixed Louse training suite, reward, feature encoder, PPO epochs,
clipping, entropy, value weight, gradient cap and KL stop. No deliberate interruption
or checkpoint selection. Evaluate the final budget-limited artifact on the unchanged
eight policy seeds 1000–1007, with a 1,200-second evaluation process limit.

The initial tensor hash must equal `1d60fa62ccd3ba50a70c174b9c1d9933d7a26c97f013f6d7d2a592cac883d4f0`.
Default-LR seed-0 evidence is the preserved 64-attempt run and final artifact
`03ca30dc29154b968686a918efb0d4579d99c3142461ee2507a33138b18bbd22`. The question is whether
larger steps produce useful behavior, not merely larger tensor differences. Reuse
the same frozen 100 public states for an explanatory probability comparison. Declare
mean total-variation distance of at least 0.05 as a noticeable distribution response
(old result 0.02188); it is not a gameplay-success threshold.

Directional gameplay support requires no loss of the eight wins or command legality,
and ending HP above both the same initial policy's 72.75 and default-LR final policy's
72.0. Greater probability movement without better HP rejects the simple step-size
quality hypothesis for this diagnostic. An isolated positive result remains exploratory;
record all attempts, failures, clipping/KL stops and outcomes, not just the favorable metric.

For a second independent initialization, reserve a matched seed-1 pair: default LR then
high LR, each with the same training ceilings; evaluate seed 1's initial artifact once
and both finals on the unchanged suite. Require the two seed-1 initial hashes to match.
Start this whole pair only if at least 175 minutes remain before 10:00 local time,
based on the clock before either arm starts, independently of seed 0's score. Otherwise
leave it unrun and report the seed-0 result as a single-initialization experiment. Do not
start only a potentially favorable arm. The 175-minute reservation covers 100 minutes
of training caps, 60 minutes for three evaluation caps and 15 minutes for cleanup.
For repeatability, require positive high-minus-default HP differences in both seed 0
and seed 1 without reduced wins; report the two paired effects individually. Eight
policy samples per initialization do not become eight independent training replicates.
The original pilot and default seed-0 run share initialization and are not replicates.
All of this remains development; broader held-out evaluation and Act 1 are unfinished.

## Language catalog transfer comparison (adopted before launch)

With the PPO route paused by owner direction, the next language-track measurement is
the reviewed [language catalog contract](language-catalog-experiment.md), adopted
unchanged (SHA-256 `406f2a6c6c281025504b4d446bb4ecebaf6b6828c6c3f704ed905539c3fb56a7`).
It evaluates the unchanged Qwen3-0.6B and then the existing final Louse-only SFT LoRA
on `starter-three-encounter-development-v1`, 12 slots each, with no new training,
checkpoint choice, prompt change or retry. Cultist and Jaw Worm are absent from the
adapter's training data; all three scenarios remain development evidence.

### Result

Completed at source `7314779` in 1,307 seconds: all 24 slots, valid independent
audits, no infrastructure, unsupported, truncated or invalid-evidence attempts.

| Policy | Wins / policy attempts | Louses | Cultist | Jaw Worm | Macro HP |
| --- | ---: | --- | --- | --- | ---: |
| Unchanged Qwen3-0.6B | 0 / 12 (12 invalid completions) | 0/4 | 0/4 | 0/4 | undefined |
| Louse-only SFT LoRA | 12 / 12 | 4/4, HP77 | 4/4, HP74 | 4/4, HP78 | 76.33 |
| Heuristic reference (four-policy batch) | 12 / 12 | 4/4, HP77 | 4/4, HP71 | 4/4, HP80 | 76.00 |

The trained-minus-untuned difference is +12 wins over 12 policy attempts, measured on
four correlated greedy repeats of each of three scenarios. Paired with the heuristic's
traces, the adapter reproduces all 21 Louse decisions but agrees with the heuristic's
choice on only 18 of 23 Cultist and 18 of 27 Jaw Worm decisions along its own
trajectories. On Cultist it opens with Strike rather than Bash and ends three HP higher;
on Jaw Worm it attacks on turn 2 where the heuristic blocks, and ends two HP lower.
Outcomes transfer to these easy unseen families; the teacher's decision rule only
partly does. See [contract](language-catalog-experiment.md) and [compact result](results/language-catalog-development-v1.json).

## Heuristic-relabel SFT result (adopted by declared rule)

Training completed all 234 updates (3,744 example occurrences, 2,935,296 padded tokens)
in 1,719.6 seconds; the independent training audit passed all 12 checks. Offline greedy
agreement with the heuristic on 513 unique states from six public starts absent from
training (no prompt, start or seed overlap):

| Adapter | Test prompts / rows | Label probability | Entropy | Train prompts / rows |
| --- | --- | ---: | ---: | --- |
| Relabeled (811 Louse states) | 75.2% / 77.1% | 0.700 | 0.414 | 81.9% / 90.6% |
| Louse-only (21 prompts) | 72.1% / 72.9% | 0.715 | 0.070 | 67.0% / 80.7% |
| Unchanged base | 32.9% / 33.1% (54 invalid) | 0.374 | 0.484 | not run |

Always answering choice 0 agrees with 59.2% of test rows. Catalog gameplay (12 slots,
valid audit, no failures): the relabeled adapter won 12/12 with macro HP
63.67 (Louses 77, Cultist 41, Jaw Worm 73), against
76.33 (77/74/78) for the Louse-only adapter and 76.00 (77/71/80) for the heuristic.

The declared rule adopts the relabeled adapter: higher held-out agreement than the
first adapter and the choice-0 baseline, equal unseen-family wins (8/8), no failures.
The rule did not include HP, and gameplay HP regressed on both unseen families.
Traces show why: against the Cultist's non-attacking first turn the adapter plays Defend
instead of Bash, then over-blocks, letting Ritual Strength accumulate. Defend is 62% of
the relabeled training labels, and the model under-fits its own training states (82% of
unique prompts). Better average label agreement did not mean better play in the states
that decide these fights. See [result](results/language-relabel-development-v1.json).

## Outcome-based post-training launch record

Base: the adopted relabeled adapter (declaration SHA-256
`3cfbd9c9534b4a9dbc768cddae96f6eab8b1623733495daf4a094196b1174d0a`). Temperature rule
measured on its 336 greedy catalog decisions: mean probability of leaving the greedy
choice 0.118 at T=1 (Louses 0.034, Cultist 0.152, Jaw Worm 0.139), so **T = 1**. Before any
collection, the whole-job budget in the [RL contract](language-rl-experiment.md) was raised
from 4,500 to 5,400 seconds: this adapter's measured fights take 46–59 seconds, and five
12-combat iterations plus updates would not fit the original cap.

### First REINFORCE job: one completed iteration, then infrastructure stop

`runs/language-rl-relabel-20261011` (source `e8d0b86`) completed iteration 0: 12 sampled
combats, all won (Louses HP 79/79/77/79, Cultist 69/66/61/69, Jaw Worm 75/52/78/58),
all three groups with nonzero advantages. The update recomputed all 331 behavior
log-probability vectors within 8.9e-7 of the recorded values, changed all 2,293,759
adapter elements, and moved the policy by a mean behavior-to-updated KL of 0.031 per
decision. Before iteration 1's first game, the per-game Windows interop query for
`LOCALAPPDATA` timed out after 10 seconds, so that slot is an infrastructure failure
with zero actions. Per the contract the job stopped without retry. A read-only
`audit_language_rl` passed. The final artifact is iteration 0's adapter
(`af13a8a2…`, declaration SHA-256 `f184598519a6b8a2aac4545e263f7e959f68844fbc7709b56871e27b41724f9c`).
The same query took 0.05 seconds when repeated; WSL swap was nearly full at the time.
That is a plausible contributor, not a measured cause.

Frozen greedy evaluation of that one-update adapter (12 slots, valid audit, no failures):
12/12 wins, Louses HP77, Cultist HP50, Jaw Worm HP73, macro **66.67** against the base's
63.67 (+3.00), so the contract's improvement rule is met. Paired with the base's traces,
the Louse and Jaw Worm action sequences are identical. The Cultist line matches until
turn 8, when the Cultist has 3 HP: the base, like the heuristic teacher, blocks three
times and takes a hit, while the updated adapter plays Strike and ends the fight 9 HP
higher. One outcome-based update corrected a mistake inherited from the teacher in a
trained scenario. It is one decision on a deterministic seed that training also used,
not evidence of a general rule. See [result](results/language-rl-development-v1.json).

### Declared continuation (before any further collection)

Infrastructure mitigation `e9ab10c`: the fixed per-user config path is resolved once
per process (30-second cap) instead of before every game. Game, observation, policy,
reward and retry semantics are unchanged.

Continuation job `runs/language-rl-relabel-continued-20261011`: the same contract
(T = 1, group 4, learning rate 1e-4, three catalog scenarios, one REINFORCE step per
iteration), starting from iteration 0's exact adapter, for **4 iterations** with
`seed = 1` so no sampling seed repeats, and a 4,500-second cap. AdamW state is not
carried over: the optimizer restarts, so this chain is not identical to one
uninterrupted 5-iteration job. Evaluate its final iteration once with the frozen
greedy evaluator, and compare it with the base (63.67) and the one-update result under
the contract's improvement rule. No checkpoint is selected by score. A failure stops
this job too, and its last completed iteration is the final artifact.

### Continuation stopped by owner request

The continuation completed one iteration (the second update overall), with a valid audit,
then was interrupted on request before iteration 1's first game. Its adapter has not been
evaluated; no claim is made about it. See docs/state.md for the artifact path and hash.
