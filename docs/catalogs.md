# Development scenario catalogs

Schema 2 adds explicit development scenarios without changing schema 1 suites or
their saved results. It is a declaration and evidence format, not certification
that a seed works. The committed [three-scenario development catalog](../configs/suites/starter_three_encounter_development_v1.json)
contains the existing mixed Louses, Cultist `SPIREINV07` and Jaw Worm `SPIREINV09`.
The latter two passed the [bounded original-engine inventory](results/starter-inventory-20261011.json)
and exact public-trace replays. New seeds still require admission under
[scenario-expansion.md](scenario-expansion.md). The single-scenario v1 benchmark
remains unchanged; catalog policy scores have not yet been collected.

The catalog is a JSON object with these required fields:

| Field | Contract |
| --- | --- |
| `schema_version` | Integer `2`. |
| `purpose` | `development`; held-out purposes are not implemented. |
| `id` | Stable lowercase identifier containing letters, digits, `_` or `-`; starts with a letter, at most 80 characters. |
| `scenarios` | Nonempty ordered list of the scenario objects below. |
| `schedule` | Nonempty ordered list of exact `{scenario_id, policy_seed}` assignments. |

Each scenario requires `id`, `game_seed`, `expected_start_sha256`,
`encounter_family`, ordered `monster_ids`, and `discovery_trace_sha256`. Scenario
IDs and game seed strings must be unique. Seeds use uppercase ASCII letters and
digits; hashes are lowercase SHA-256. Obvious placeholders, duplicate JSON keys,
nonfinite values, unknown fields, missing references and unsupported declarations
are rejected. Every scenario must be scheduled at least once; each scenario and
policy-seed pair is unique. Policy seeds are integers in `[0, 2**63)`.

| Family | Required ordered public monster IDs |
| --- | --- |
| `cultist` | `["Cultist"]` |
| `jaw_worm` | `["JawWorm"]` |
| `two_louses` | Two entries, each `FuzzyLouseNormal` or `FuzzyLouseDefensive`. |

Optional top-level fields are nonempty `description` and exact supported
declarations: `character="IRONCLAD"`, `ascension=0`,
`observation_contract="ironclad-starter-combat-v1"`,
`reset="owned_jvm_restart_then_seeded_start"`, and
`prefix_version="neow-maxhp-or-gold-leftmost-settled-v2"`. Defaults are fixed to
these contracts. Catalog IDs, seeds, fingerprints, family labels and discovery
hashes are environment metadata; they are never added to policy observations.

The discovery hash is a required reference to separately retained evidence. The
loader checks its format, not the existence or contents of that external trace.
Admission must verify that evidence, repeated settled starts, prefix choices,
profile, starter deck/Burning Blood conditions and complete supported combat.
The [inventory fixture](../tests/fixtures/engine_inventory_transitions.json) adds
16 exact public transitions for Cultist Ritual/Strength, Jaw Worm block/Strength,
Louse variants and both admitted encounters' engine-reported deaths. These captures
support only the observed transitions, not general mechanics coverage. The captured
88-HP Louse variants remain excluded from the 80-HP development catalog; accepting
a family declaration alone does not admit another seed.
The v1 learner still omits monster identity, as documented in the expansion review.

## Python API

- `validate_catalog(value)` returns a detached validated schema-2 dictionary.
- `load_catalog(path)` loads strict JSON and validates it. Call the existing
  `evaluation.load_suite(path)` for schema 1; schema dispatch is the caller's job.
- `resolve_child_suite(catalog, schedule_index)` returns an ordinary schema-1
  development suite with exactly one episode and the selected game seed, expected
  public start and policy RNG seed. It leaves its input unchanged.
- `evaluate_catalog(policy, catalog_path, output, *, checkpoint=None)` invokes the
  existing evaluator once per frozen assignment. Supported policies are `random`,
  `heuristic`, `end_turn`, and `neural`; only `neural` requires a frozen checkpoint.
- `audit_catalog(output)` re-derives the saved report without launching a game or
  writing files. Malformed or missing parent declarations raise an exception;
  child evidence failures produce an invalid report with issues.

Training accepts schema 2 through its existing suite path. The
`round_robin_scenarios_v1` schedule cycles unique scenarios in declaration order,
resolving each through its first evaluation schedule entry. Evaluation repetition
counts therefore do not change training weights. Before attempt files or a game
exist, the checkpoint reserves the cursor, scenario ID and schedule index. Every
reserved attempt advances the cursor, including an interrupted or failed attempt;
resume preserves that assignment and the original absolute deadline. A completed
recovered episode restores its sampling state from audited public decisions; an
incomplete attempt remains recorded and excluded from training.

The training sampler keeps its external checkpointed RNG and never uses the
evaluation schedule's policy seed. Scenario context belongs to checkpoint,
manifest and environment metadata, outside policy observations. Before ingestion
and batch reuse, training verifies the assigned scenario, public start fingerprint
and ordered monster IDs. The saved-training auditor independently checks scenario
reservations throughout checkpoint history and child evidence. Schema-1 training
retains its existing format and behavior.

## Evaluation evidence and scoring

Evaluation requires a clean implementation checkout and a new output directory.
It freezes exact catalog bytes, source revision/fingerprints, and policy source or
neural artifact/export record. Each child retains ordinary schema-1 evidence:

```text
catalog.json                 frozen input bytes
catalog-manifest.json        source/artifact pins, ordered child reservations
catalog-evaluation.json      final independently re-auditable report
frozen-policy/               policy source or weights and optional export record
suites/attempt-NNNN.json     resolved one-episode schema-1 suite
runs/attempt-NNNN/           existing evaluator's full child evidence
```

The auditor reruns the existing trace audit, checks exact child file hashes and
source/artifact/configuration linkage, and compares game/mod hashes across all
children. It also checks each audited public combat start's **ordered monster
IDs** against its scenario, beyond matching the pinned start fingerprint. Session
IDs cannot be reused. Reset comparisons group only the same scenario's children.

Both evaluation and read-only audit return the same report shape: top-level
`metrics` holds episode-weighted counts and means; `scenarios[id]` contains
`metrics` and `reset_comparison`; `macro` uses equal weight per scenario for win
rate, ending HP, net HP lost and turns. Macro values are populated only when the
entire schedule completes validly. Scores include engine postcombat healing.

The schedule stops at the first collection, provenance or evidence failure.
Infrastructure failures remain distinct from gameplay losses. `attempts_started`
counts reserved children, while `metrics.attempts` counts saved audited episodes;
a failure before episode creation can make these differ. `orchestration_failures`
counts caught child exceptions, `unattempted` retains the rest of the schedule,
and the metrics preserve interrupted/unsupported/truncated/invalid evidence
counts. Interruption writes the parent manifest before propagating the exception;
`audit_catalog` can inspect it even without a final report. There is no retry or
resume API. New evaluation uses a new output directory.

The implementation does not alter features, train a policy, or establish held-out
generalization. Freeze and compare the same catalog and schedule across policies;
different policy RNG seeds alone do not create new environment scenarios.

Validation: catalog tests use the actual schema-1 evaluator and trace auditor with
mocked game communication, including provenance tampering, engine changes,
interruption and unequal schedule weights. They perform no game launches and do
not establish original-engine compatibility for uninventoried seeds.
