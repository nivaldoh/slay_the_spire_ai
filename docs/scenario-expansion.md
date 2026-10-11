# Starter encounter expansion

The original read-only review covered revision
`741d96aafd176da201105f06f4527ce9126392e7` on 2026-10-11 without launching games
or training policies. Subsequent [inventory evidence](results/starter-inventory-20261011.json)
admitted Cultist `SPIREINV07` and Jaw Worm `SPIREINV09` after exact public-trace
replays. The [three-scenario catalog](../configs/suites/starter_three_encounter_development_v1.json)
combines them with the existing mixed Louses under the same fresh-JVM reset and
public-information boundary. It remains development-only; catalog policy scores
have not yet been collected. The single-scenario v1 suite and its results are preserved.

## Coverage and concrete limits

The [adapter](../src/spire/protocol.py) restricts cards and screens, not monster
species. For ordinary Ironclad A0 combat it uses engine-reported playability and
retains original target indices. Strike, Defend, Bash and END need no new command
for the proposed encounters. The [learner](../src/spire/learning.py) already
encodes visible attack damage/hits, block, Strength, `Weakened`, Vulnerable,
Curl Up and Ritual, including mixed attack/buff/defend intents.

| Candidate encounter | Relevant public features | Current evidence |
| --- | --- | --- |
| Cultist | Ritual and subsequent Strength; visible attack intent/damage | `SPIREINV07` has an exact heuristic replay and captured Ritual appearance, Strength ticks, displayed attack damage and engine death. |
| Jaw Worm | Block, Strength, attack and mixed defensive/buff intents | `SPIREINV09` has an exact heuristic replay and captured block/Strength transitions, displayed attack damage and engine death. |
| Other Louse compositions | Curl Up, Strength, Weak, per-target health/block/intent; stable target slots | Captured same-species normal and defensive Louses supplement the original mixed-Louse evidence. Both new captured variants started at 88 HP and remain excluded from the 80-HP catalog. |

Public monster names and the Ritual/Curl Up/Weak/Strength tooltip meanings were
checked against the installed engine's English localization resources, under the
engine hash in [integration.md](integration.md). No enemy move probabilities,
private move history, RNG state or future draw order were used. The
[inventory fixture](../tests/fixtures/engine_inventory_transitions.json) and its
[regressions](../tests/test_inventory_engine_regressions.py) preserve 16 exact public
transitions. These observations do not establish general mechanics formulas or
admit unseen seeds. Four 88-HP discoveries and six unsupported attempts remain
excluded, with no replacement seeds sampled.

Actual limitations found:

- **Monster identity is dropped by the model.** The public observation retains
  `id`, but `_monster()` ignores it. Changing only
  `FuzzyLouseNormal` to `FuzzyLouseDefensive` produced exactly equal features,
  logits and value in a synthetic check. Different visible variants can therefore
  be indistinguishable when their numeric state and intent match. This does not
  invalidate action legality. Keep v1 as a declared restricted representation;
  adding public archetype identity requires a new encoder version and artifacts.
- Unknown power identities share amount/count channels. None of the named powers
  above needs that fallback, but accepting arbitrary monsters is not full feature
  coverage. Relic identity is also omitted; retain Burning Blood and starter-deck
  constraints for this expansion. The model has no public action-history memory.
- Playable nonstarter cards are unsupported: a synthetic playable `Slimed` raises
  `UnsupportedStateError`. Potions and choice screens remain excluded. Do not
  include additional encounter families or Neow card/relic changes merely because
  their first observation passes; check an entire fight for new actions.
- The [prefix](../src/spire/rollout.py) supports max-HP or 100-gold Neow choices and
  the leftmost map option. It rejects a seeded menu with neither supported reward.
  Thus an arbitrary seed is not automatically an eligible scenario. Initial HP,
  deck, relics, actual Neow choice and settled intent must be recorded and pinned.

At the original review, **52 protocol/learning tests passed**. Read-only synthetic
checks demonstrated the identity aliases, accepted the Cultist/Jaw Worm examples,
and confirmed Slimed rejection. These checks do not replace live transitions.

## Original catalog proposal

Schema 2 now implements development catalogs, round-robin training reservations
and grouped evaluation; [catalogs.md](catalogs.md) defines the current API. The
proposal below records the design rationale. Held-out purposes remain unimplemented.

Introduce a new catalog schema while keeping each scenario a single-seed run
under the existing adapter/reset/prefix contracts. Evaluation can initially invoke
the existing single-scenario collector separately for each catalog entry and then
aggregate audited child runs. Do not broaden `load_suite()` by silently reinterpreting
v1 fields; it currently requires one seed/fingerprint and purpose `development`.

| Catalog field | Required meaning |
| --- | --- |
| `schema_version`, `id`, `purpose` | New schema/id; explicitly development, held-out-seed, or held-out-encounter purpose. Current loader needs an explicit extension for these purposes. |
| `scenarios[]` | Unique scenario ID, exact game seed, expected public start SHA-256, encounter family and ordered public monster IDs. No invented seed/fingerprint placeholders in executable configs. |
| Per-scenario evidence | Discovery run/trace hash, actual prefix choices, starting HP/max HP, deck/relic constraints, profile snapshot and engine/mod/contract pins. |
| `schedule[]` | Explicit scenario ID and independent policy sampling seed for each evaluation attempt, frozen before comparing policies. Declare equal scenario weights initially. |
| Provenance | Catalog bytes/hash, implementation revision, policy artifact, per-attempt scenario ID and child evidence path. Seed and catalog remain environment-only. |

For training, a deterministic round-robin schedule is sufficient initially.
Checkpoint its cursor and the selected scenario in the existing pending-attempt
reservation **before** writing files or launching a game. Resume must retain that
assignment and existing failure accounting. Collect complete episodes from one
behavior version into each PPO batch; changing scenarios does not justify mixing
old-policy data or treating failed attempts as losses.

Existing evidence assumes one scenario: `compare_resets()` currently compares all
episode pairs and expects one initial hash. Group reset comparisons by scenario.
Report per-scenario and per-family metrics, declared macro averages, and all failure
counts; an episode-weighted average alone can change when encounter counts change.
Do not require different scenarios to have equal starting states.

## Admission and generalization claims

First inventory a bounded, predetermined list of candidate seeds using only the
runner and public states. Record every discovery attempt and why a seed is rejected
(unsupported prefix/action, wrong composition, unstable start, or infrastructure).
Select eligibility before examining learned-policy performance. Initially prefer
the existing 80-HP, starter-deck, Burning Blood conditions; any max-HP-reward variant
must be separately declared rather than silently mixed with them. This evaluates
the declared eligible seed distribution, not all possible first-floor encounters.

For each admitted seed, repeat a fresh-JVM start and a fixed legal action sequence,
compare all public transitions, and audit a complete combat. Capture new minimal
regressions for Ritual growth, Jaw Worm block/Strength, and the added Louse
compositions. Keep unknown initial intents behind the existing settling gate.
Admission requires no unsupported actions, unexplained state mismatch or hidden
information in policy inputs. A discovery run is infrastructure evidence only.

Freeze splits by **game seed**, not by episode or policy RNG seed:

- **Held-out seeds:** new seeds for encounter families/compositions already present
  in training. Repeating one seed with different policy samples is variability on
  one scenario, not another independent environment sample.
- **Held-out encounter types:** reserve an entire declared family from training
  and policy tuning. A new Louse color composition should be reported separately
  from holding out Cultist or Jaw Worm as a whole. Freeze this taxonomy in advance.

Infrastructure checks of held-out scenarios may verify legality/repeatability, but
must not feed gameplay trajectories into the learner or guide policy tuning. Freeze
the policy before held-out evaluation and report scenario counts as well as episode
counts; do not claim broad generalization from a handful of seeds. Preserve all v1
results and generate new random/heuristic/frozen-policy baselines for the new catalog.
Any public-feature extension is a separate, versioned experiment.
