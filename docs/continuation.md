# Two-combat continuation contract

This is a separate development scope, `ironclad-two-combat-continuation-v1`.
It is not an Act 1 completion benchmark, a reset between fights, or a new training
dataset. Existing first-combat rollout, evaluation, observations and artifacts
retain their original semantics. No original-engine continuation has been
validated yet; the second encounter must fail closed if unsupported.

The only game seed is `SPIREAI1`, Ironclad Ascension 0, with the existing settled
80-HP first-combat fingerprint
`177b2fcdc80ed0e9efb7d2a01191a40df6e40d4123867d09e091fa122edc12c4`.
The usual Neow 100-gold/leftmost prefix reaches map node `(0,0)`. The saved public
map in `runs/baseline-heuristic-settled-20261011/episode-0000/trace.jsonl`
shows its normal-combat successor `(1,1)`; the second encounter's identity and
behavior have not been observed. The route is fixed before that observation.

After the first engine-confirmed combat completion, a disclosed transit controller
claims visible GOLD rewards one at a time, then uses PROCEED to leave all other
rewards unclaimed. It chooses `(1,1)` from the next stable MAP observation, requiring
that the visible symbol is `M` and the current node is `(0,0)`. A choice's wire
index is its ordinal in the current reward/next-node list, not its coordinate or
an index cached before the previous action. No card reward is opened; no potion,
relic, shop, event, chest, rest, upgrade, boss or arbitrary map route is supported.
Unexpected screens or state changes stop the attempt without a fallback.

The deck stays five unupgraded Strikes, four unupgraded Defends and one unupgraded
Bash; Burning Blood is the sole relic and no potions may be acquired or used.
Both combats use the existing starter action interface. The second combat admits
only one Cultist, one Jaw Worm, or two normal/defensive Louses, with ordinary
MonsterRoom combat and no newly playable unsupported card. Family membership is
checked on every combat decision; these boundaries are not proof of second-fight
mechanic coverage. The initial implementation uses the disclosed starter
heuristic, or a diagnostic end-turn policy for combat two, without model loading.

One owned JVM and runtime lock span the complete segment. Each combat completion
is recorded once; repeated COMPLETE/reward observations cannot increment the
combat count. HP after engine healing, max HP, gold, deck and relic/potion identity
must carry across reward/map transitions into combat two. Gold may change only by
a claimed reward's displayed amount during transit. The second combat's complete
start fingerprint is recorded, but is not required to equal another policy's
start: health and RNG consumption depend on the first fight. Exact replay equality
applies only to identical complete action histories.

The endpoint is the second engine-confirmed combat completion, before its rewards
are claimed: `completed_segment`, never an Act 1 win. Real engine DEATH ends the
segment as `lost`. Unsupported or invalid state, infrastructure failure, interruption and action/time
truncation remain separate outcomes. Saved evidence
retains both combat summaries and all noncombat decisions, including partial
progress from failed segments; partial progress never becomes a complete score.
The new auditor reconstructs decisions, continuity and the endpoint from the trace.
The existing first-combat auditor and trainers must reject this new scope.

Before implementation is admitted for gameplay comparisons, run a bounded original-
engine gate of at most five fresh JVMs and 1,200 seconds total, with at most 240
seconds and 500 actions per attempt, no automatic retry or replacement seed:

1. Discover the full segment with the fixed heuristic. Verify GOLD claim/reindex,
   PROCEED leaving the deck/relics/potions unchanged, exact map destination, settled
   second combat, persistent state and the second actual combat completion.
2. Restart and replay the same controller. Compare commands and normalized public
   transitions throughout both combats and transit. Preserve any mismatch.
3. Use the heuristic in combat one and END only in combat two. Require actual DEATH
   evidence to claim the new death path; a cap or unexpected win is a coverage gap.
4. Deliberately interrupt after reward collection and before entering combat two;
   preserve the first completed combat and incomplete segment.
5. Start a new JVM after interruption and repeat the fixed segment; there is no
   implicit live-game resume. Confirm the initial fingerprint and public replay.

Stop the gate on an unexpected unsupported state, evidence failure or infrastructure
failure; retain unattempted assignments. Record source/contract/controller hashes,
profile snapshots and engine/mod pins before collection. The gate is engineering
evidence on one development seed, not milestone D generalization or milestone F
Act 1 competence. Execution waits until the current fixed game jobs release
ownership and the integrated source is committed and reviewed. If the canonical
second encounter is unsupported, preserve that gate failure and use the observed
mechanic as the next implementation target; do not substitute a more favorable seed.

## Commands and saved evidence

After the ownership/source gate above, from the committed repository root:

```bash
uv run python scripts/continue_two_combats.py run --output runs/two-combat-discovery
uv run python scripts/continue_two_combats.py audit runs/two-combat-discovery
# The separately scheduled defeat probe changes only combat two's controller:
uv run python scripts/continue_two_combats.py run --second-policy end_turn --output runs/two-combat-death
```

Each invocation creates a fresh directory and one JVM; there is no resume or retry.
`--time-budget`, `--max-actions` and `--bridge-timeout` can reduce the declared caps.
The absolute deadline starts before setup; game ownership is released on exceptions
and interruption, and cleanup overrun is reported separately. A cleanup error preserves
a verified gameplay endpoint but makes the command fail so the validation gate stops. The manifest pins the
Git revision, source fingerprints, contract/document hashes, engine/mod evidence and all
saved files. Raw bridge messages stay diagnostic; only sanitized combat/transit
decisions are controller inputs. The auditor requires the recorded source checkout:
use the manifest's source revision when auditing after subsequent implementation edits.
It checks evidence consistency, not cryptographic proof of which executable produced it.

Focused tests use synthetic state sequences and mocked runtime ownership. The optional
saved-engine regression replays the already recorded first combat up to its unclaimed
GOLD boundary; it provides no second-combat validation:

```bash
SPIRE_EVIDENCE_ROOT=/path/to/original/repository uv run pytest tests/test_continuation.py
```
