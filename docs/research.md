# Research contract

## Current question

Can we repeatedly start the same Ironclad Ascension 0 game, enter its first combat,
execute state-bound legal actions, record the engine outcome, and restart automatically?
This is infrastructure validation, not a policy-performance claim.

## Initial scope

- Original Steam engine, fixed Workshop jars, personal profile slot 0 as authorized.
- Seeded `START` and a fixed noncombat prefix. No arbitrary combat reset is claimed.
- A random legal policy followed by an explicit heuristic baseline.
- Raw engine state is diagnostic evidence; policies receive a separate allowlisted view.
- Exclude seeds, RNG state, unrevealed draw order, and private monster state from policies.
- Record terminal gameplay outcomes separately from limits and bridge failures.
- Preserve every attempt and attribute observations/actions to a unique decision state.

No training or final evaluation suite is established yet. Do not interpret debugging seeds
as a held-out benchmark. Milestone B requires a declared start distribution, mechanic
coverage, repeat-reset evidence, measured throughput, and baseline results.

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
or unseen-encounter ability. The deterministic heuristic provides a disclosed ceiling
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
