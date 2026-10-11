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
