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

## Proposed bounded development inventory (not launched)

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
