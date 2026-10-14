# Audited public-action demonstrations

`spire.language.demonstrations` prepares model-independent action targets for guide §6.3.
It performs no model download, training, generation, game launch or evaluation.
The current teachers are the known public `heuristic` and seeded `random` policies.
Search, human, neural and privileged teachers require their own provenance contract
before they can be admitted.

```python
from pathlib import Path
from spire.language.demonstrations import DemonstrationSource, export_demonstrations

manifest = export_demonstrations(
    Path("/tmp/heuristic-demonstrations"),
    [DemonstrationSource(
        run=Path("runs/first-combat/heuristic-settled-20261011"),
        split="train",
        source_role="heuristic",
        teacher_information="public",
    )],
    purpose="smoke",
)
```

The output must be new and outside every source run. `purpose` is explicitly
`smoke` (only a train split), `supervised_finetuning`, or `offline_evaluation` (only
a test split); source split assignments are explicit `train`, `validation` or `test`. Validation finishes before output
creation. A final `manifest.json` marks a completed export; a partial filesystem
write without this manifest is not a completed dataset.

## Shared prompt and action contract

`FORMAT_VERSION = "public-card-table-choice-v1"` freezes these APIs:

- `public_input(decision: Decision) -> dict` returns a detached public object.
- `render_prompt(decision: Decision) -> str` returns the fixed instruction and
  compact JSON, with no dialogue or gameplay memory.
- `parse_completion(decision: Decision, text: str) -> Action` accepts a single
  JSON object with exactly one integer local choice index, for example `{"a":0}`.

The parser permits JSON whitespace. It rejects booleans, floats, strings,
extra/duplicate keys, out-of-range indexes, prose and fenced JSON. There is no
repair, retry or fallback. It returns the exact candidate object from the supplied
Decision; the runner must still validate its session/sequence binding against the
current Decision before sending a command.

The rendering losslessly interns complete public card records in a `cards` table.
Deck and pile entries refer to table indexes; hand and target slots keep their
original positions, including duplicate cards and dead monster slots. The draw
pile retains the observation contract's canonical unordered representation.
Every currently allowlisted public field is retained, including public powers,
intent damage, card flags and resources. Candidate rows are
`[kind, hand_slot, target_slot]`, where `kind` is `play` or `end`, slots are zero-based,
and `null` means unused. Their list positions are the completion indexes.

Model text contains no session or decision IDs, action commands, game or policy
seeds, scenario declarations, source hashes, diagnostic raw state, future states,
terminal labels, teacher explanations or invented reasoning. Outcomes and source
identity stay in separate metadata. Token counts depend on the eventual tokenizer
and chat template: this exporter makes no context-length claim and never truncates
fields. A model adapter must measure and reject oversized prompts explicitly.

## Evidence and teacher verification

Each entire originating run must independently pass `audit_run`, finish with status
`completed`, and contain only complete engine-confirmed wins or losses. Interrupted,
truncated, unsupported, rejected, model-failure or corrupt runs cannot contribute a convenient
completed subset. Every exported action must be one of the audited legal candidates.

The recorded teacher must match the caller's role, have clean preserved source,
and have manifest source hashes equal the historical Git blobs for `policies.py`
and `protocol.py`. Those blobs must match the known public implementations' ASTs;
the exact known later `EndTurnPolicy` and independent `PolicyFailure` exception
additions are allowed for older collections. Their implementations must match
exactly, with no duplicate class or other source change.
The exporter never executes historical code. It independently replays every
heuristic choice or seeded random choice and rejects disagreement. The verified
source bytes are copied into the dataset. A caller's `teacher_information="public"`
is therefore a required declaration, not sufficient evidence.

A saved evaluation also requires its suite fields to agree with the originating
run's seed, policy seed, episode count and start pin, and every audited actual
start to match that pin. The suite's saved hash must resolve to matching captured
bytes (`suite.json`, the catalog parent's child suite, or historical tracked
`configs/*.json` bytes). The copied declaration and builtin artifact identity are
verified. Missing or conflicting evaluation provenance fails closed.

Development evaluation reuse is allowed and records both `original_purpose` and
`development_reuse`; the dataset is labeled `diagnostic_development`. Such reuse
cannot be described as an independent held-out comparison. Test, final-test and
held-out evaluation origins cannot supply train or validation examples. Their
purpose is not inferred from a filename. Input hashes are checked again before
writing to catch evidence changes during export.

## Heuristic relabeling

Source role `heuristic_relabel` labels every audited public state in a complete run
with the current `StarterHeuristicPolicy`, whatever policy chose the recorded
actions: random, neural, heuristic or end-turn. The heuristic reads only the public
Decision, so the label is exact and needs no game access. The run's recorded
`protocol.py` must match its Git blob and the current known public implementation.
Its recorded status may change only documentation or run files, never `src/`,
`scripts/`, `configs/` or dependency locks. The current `policies.py` and historical
`protocol.py` bytes are copied into `teacher_sources/`. Origins add
`behavior_policy` and `behavior_action`; neither enters model text. The training
loader accepts these sources with `teacher_information="public_builtin_relabel"`.
See [the relabel experiment](language-relabel-experiment.md).

## Split boundaries and duplicates

There is no random turn split. The following groups must remain wholly in one
split across all declared sources:

- originating run and session;
- environment game seed, independent of policy RNG seed;
- identical normalized public combat start;
- identical rendered public prompt, even if its chosen action differs.

Sharing an encounter type alone is allowed across distinct environment seeds and
starts. Encounter-family holdout needs a separate stronger declared contract.
The exporter does not establish hidden-state independence or prevent undeclared
reuse in another dataset; all intended splits must be declared together.

Exact duplicate examples remain as separate rows, each with its full origin.
`unique_prompts`, `unique_examples` and `duplicate_rows` expose this duplication;
repeating a deterministic replay does not create new scenario coverage. The same
originating run cannot be supplied twice. No wins-only or reward-based filtering
occurs: complete losses contribute their observed actions too.

## Output and verified smoke scope

`train.jsonl`, `validation.jsonl` and `test.jsonl` exist only for populated splits.
Each row has exactly `prompt` and `completion`. `origins.jsonl` links each split/row
to its run, session, transition, scenario, public start, trace and selected Action;
it contains outcome metadata for auditing and must not become model input.
`manifest.json` records format/version, dataset purpose, source roles and purposes,
file hashes, split rules and duplicate counts. `teacher_sources/` and, when used,
`source_suites/` retain verified provenance bytes. Bulky exports remain outside Git.

Read-only validation on the existing original-engine
`runs/first-combat/heuristic-settled-20261011` reproduced all **42 actions** in two complete
heuristic episodes. They yield **21 unique examples and 21 duplicate rows**, one
environment seed and one public-start family. This is a training/smoke dataset;
it provides no independent validation/test scenario or generalization result.
The unit tests additionally exercise hidden-field rejection, duplicate slot
identity, stale actions, malformed completions, provenance tampering, incomplete
origins and split leakage without accessing the game or production locks.
