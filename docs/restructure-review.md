# A smaller restructuring plan

**Start with the evaluator check and the policy-name parser.** Both changes pay for themselves in
the current tree. For a physical reorganization I would give checkpoint work and native multiplayer
a package each. Those tracks have their own entry points, artifacts and tests. The existing battle
package can then keep the paths that saved controllers import. Decide on each track when it next
needs work. A stop after the parser is a useful long-term layout in its own right.

This is a proposal based on `e453429`. The owner decides what to implement and how to verify it.
The original [decision record](restructure-plan.md#decisions-for-the-owner) remains available.
Claude's second design at `3a225ef` is the alternative to consult for a full move. Neither design
has been adopted. The cards below can be implemented from a clean clone. Local evidence gives a
future implementer additional comparisons on the machine that holds the saved jobs.

## Proposed tree

JUDGEMENT: Track packages — Codex, 2026-11-18, proposes moving checkpoint and multiplayer separately
when those tracks are worked on. Keeping today's locations or regrouping all WH3 modules by role
changes which compatibility work pays off. The target tree and the two move cards rest on this choice.

```text
src/
  gameai/                 provenance, ledgers, providers, model and Windows primitives used by games
  spire/                  engine, combat, fullrun, ppo, openweight, language and their entry points
  twwarhammer3/
    __main__.py           user commands and dispatch
    protocol.py           observation, orders and feedback contracts
    engine/               runtime, pack, startup, doctor, mailbox, Windows and manual capture
    battle/               play, scenario setup, policies, witnesses, readings and job reports
      policy_names.py     syntax shared by controllers and recorded-job readers
    checkpoint/           checkpoint.py, candidates.py, audit.py, confirm.py, rl.py,
                          checkpoint_frida.py and checkpoint_agent.js
    multiplayer/          worker.py, link.py, peers.py, multiplayer_probe.py and its .js,
                          multiplayer_adapter.py and its .js
    mod/  assets/         game-loaded resources
configs/                  scenario declarations, controller compositions, prompts and prices
scripts/                  queue, repository gate and other operator tools
tests/                    current game, protocol, reader and repository checks
docs/                     methods, status, register and game-specific guides
runs/                     local evidence and disposable comparisons
```

The tree shows the destinations. Existing battle files keep their names except for the six named
under the two new tracks that currently live in `battle/`. The rest of those tracks' files come
from `engine/`. Each new package needs only an ordinary `__init__.py`. Retaining the base names
lets an operator still search for the exact Windows script or checker named in a log.

**How a maintainer finds the code**

| Task | First file, then the boundary to follow |
|---|---|
| Add a battle observation or order | Start at `protocol.py` and the Lua producer/consumer. Follow the public projection through `battle/play.py` to the controller. Keep evaluation, final state, replay and stills on the evaluator side. A Python import rule cannot establish what data crossed that boundary. |
| Add a scenario, witness or reading | Start in `configs/twwarhammer3/scenarios/` and `battle/setup.py`. Put the witness beside its family. Share a fact via that family's existing `*_facts.py` when both sides use it. Put evaluator-only readings in `*_readings.py`. Families can have just the parts they use. |
| Read or group a result | Start at `battle/stats.py` for the CSV row and grouping, `benchmark.py` for the outcome, `report_html.py:harness` for the test setup, `digest.py` for the trace. The identity used by each reader is part of its contract. |
| Change a checkpoint restore or a worker session | Start with the matching command in `__main__.py`. Follow it into the corresponding track and its Windows component. Both can call game-specific battle or engine code. Keep transport and OS primitives where their existing callers use them. |

This leaves a sizeable battle directory. Its searchable family names are valuable to readers of
older work. A `reports/` directory would help someone browsing by output, but Claude's version puts
`suite.py`, which can author graphs via a paid call, in that directory. Likewise `stats.record`
appends a register row during play. Classifying either by its folder gives an agent the wrong answer
to “can I run this while a job is active?” The command and its side effects answer that question.

## What changed after checking Claude's work

| Option | Evidence and consequence |
|---|---|
| Keep file paths and cut an actual dependency | A cold import of `battle.stats` loads 14 modules with the `twwarhammer3.` prefix, including team and model controllers. In a temporary copy, extracting the parser and redirecting its four readers reduced this to 4. Five saved episodes passed through the parser in `stats.row` and yielded identical rows, including the rotated `llm_rules@gpt-6-luna` and an external policy. Reading the tracked CSV also produced the same summary, a separate control for grouping. This is a direct module import. The CLI still imports controller and watch code at startup. |
| Move only the two tracks | The two cards relocate 14 existing files. An AST walk finds the CLI is their only static Python importer elsewhere in game source. It touches 33 direct WH3 import statements in tests and scripts, against 221 for the full move. No register policy string names a relocated module directly. External imports, subprocess strings and path-based fingerprints still need checking. |
| Move everything by role | The second draft proposes moving 75 files. On the earlier full-move rehearsal at `6105354`, three recorded external policy names fail to load with their original files on the documented Python path. They load at `e453429`. Two rows use `terrain_probe:TerrainProbe`, one uses `flight_probe:ProbeFlight` and one uses `external_controller:ExternalHold`. Their modules import the old battle package. Reading those four rows and running the policies again are different operations. |

The second draft's moved-module table addresses names of defining modules. At base,
`twwarhammer3.battle.controllers:Skills` also resolves because that module imports `Skills`.
The rehearsal loses that spelling. Both `battle.calibration:Hold` and `battle.scripted:Hold`
(with the game prefix) still resolve to the same class and yield different supplied policy names.
A card stores both `name` and `class`. Grouping as if a class uniquely determined the policy
would change the meaning of existing results. Keep both fields and the current grouping.

Claude's later draft is worth keeping for its inventory of source paths and recorded identities, its alternative
packages and its replay of saved jobs. The handoff in the original run describes the first version on main. Git shows
the later planning commit `3a225ef` and uncommitted edits to both pages in that worktree.
The earlier full-move rehearsal and the later dry run exercised different designs. The latter ended
at `d936328`, after commit five of six in its first stage, with an untracked guidance page. Its
fifth pre-commit gate recorded 4,190 passes and 70 skips. Later stages of that draft have no such
result. For the earlier full move, the plant run had two baseline failures. Both were caught when
rerun separately. The full run itself exited 1.

Use the local `kit/` as worked examples. Its Stage 2 script `2a.py` introduces name lookup already,
and `2f.py` performs the graph-cycle cut the later plan deferred. Its wrapper can print that its
statement comparison exited 1 and still exit 0. Its snapshot classifier can report success when an
entire decisions directory disappears, an empty orders list disappears or a JSON boolean becomes a
number. These are reasons to retire the old command sequence. A fresh clone needs none of it to
carry out the following cards.

## First changes in the current packages

JUDGEMENT: First restructuring changes — Codex, 2026-11-18, proposes a targeted readings check
and one parser extraction. The alternative starts with the second draft's package-wide import
rules and exception lists. The first two implementation cards depend on this ordering.

**1. Make the readings check fail when it skips its inputs.** Work in
`tests/test_repo_rules.py`. The real-tree assertion accepts an empty list of violations even when
the walk visits zero files. With a misplaced `bad_readings.py` importing a witness, today's
`readings_loads` returned `[]` in a disposable tree.

- Discover the starting files once. Pass that inventory to the existing import walk. In the
  real-tree test, require the existing camp, lines, wall and escalade readings among the starts.
  Compare the visited starts with the actual `*_readings.py` paths under the WH3 source root.
  An unexpected location should identify its path. One missing family must fail even when three pass.
- Reuse the existing forbidden-import and package-initializer fixtures. Challenge the check with
  an empty discovery and with one readings file outside the walked directory. Keep a successful
  case with an independent facts module. Run
  `uv run --locked pytest -q tests/test_repo_rules.py -k readings`. The relevant observation is
  which files the check actually examined and which import it rejected. This checks static edges.
  The public observation boundary still has its own protocol and evaluator tests.

**2. Let a reader parse a policy without constructing the controller module graph.** Add
`src/twwarhammer3/battle/policy_names.py` with the existing `policy_parts` implementation and its
model-policy names. Keep the prompt mapping and controller construction in `battle/controllers.py`.
Import the two symbols there under their existing names for existing callers. In `stats.py`,
`digest.py`, `export.py` and `report_html.py`, import the needed symbols directly from
`policy_names.py`. A small equality assertion against the keys of `controllers.MODEL_PROMPTS`
catches adding a prompt without extending the parser. Keep the suite's prompt override where it is.

- Compare bare built-ins, configured and external names, a bare model, a vendor/model with an
  effort suffix, and invalid or empty suffixes. Readers parse recorded strings. The existing
  launch validation still rejects current unsupported combinations. Check both through their
  normal entry points. Preserve supplied names, card kinds/classes and versions.
- Run the five test files with the command below. In a fresh clone, the stats test for a
  rotated model exercises the parser through a row built from fixture data. In separate clean base and candidate processes,
  compare `stats.summary` on the same tracked CSV and `stats.row` on the same saved job and episode. Compare generated export records,
  counts, errors and labels by exporting the same saved episode into two fresh directories.
  Account for the actual `exporter_sha256` change against the bytes of the edited `export.py`.
- In a fresh interpreter import `twwarhammer3.battle.stats` and inspect `sys.modules`.
  `twwarhammer3.battle.controllers` should be absent. Reintroducing the old import should bring
  it back. The proposed test is about this dependency, so a total module count can vary.
  A new source file changes the WH3 provenance map and can start a new report setup for future
  jobs. Existing stored manifests, graph artifacts, checker pins and CSV rows retain their bytes.


```bash
uv run --locked pytest -q tests/twwarhammer3/test_wh3_{controllers,stats,digest,export,report_html}.py
```

The two cards can land independently. Revisit wording and geometry helpers only
when a caller pulls in a controller solely to format an order or compute a distance. Use the
existing `battle/unit_geometry.py` as a candidate home for geometry after checking what it imports.
The first slice leaves digest and HTML rendering with other controller dependencies. No claim
about overall CLI startup time follows from the import counts.

## Physical moves, one track at a time

**3. Checkpoint.** Move `battle/{checkpoint,candidates,audit,confirm,rl}.py` and
`engine/{checkpoint_frida.py,checkpoint_agent.js}` into `twwarhammer3/checkpoint/`. Preserve the public
`rl` command and its arguments. Move the pair of Windows files byte for byte. Make `AGENT` and `RUNNER` resolve the new siblings. Keep the Windows
work-directory filenames and config, native output and command-line formats. Update CLI dispatch,
Python consumers, tests, plants, current instructions and the Code map in the same change.
Review saved-command examples and dated references individually.

- Check `battle.candidates:RushNearest` with the full prefix. It resolves through a re-export
  today. Collect the old accepted spellings, direct Python imports and module commands in active
  use before moving. For a supported spelling, retain a small forwarding module at the old
  path with the needed exports, or keep that module in place. A breaking migration requires an
  owner decision that names the affected callers. Enumerate shipped destinations and any retained
  forwards on the card. A `module:Class` resolver alone cannot satisfy an ordinary Python import.
- Run the checkpoint, candidates, audit, confirm and RL tests and the applicable existing checks.
  Use a disposable copy for `rl recount`, which writes a new file. Compare checks, input hashes
  and derived values. A changed `checker_sha256` must match the candidate checker's actual bytes.
  Check that the base and candidate ship identical JS bytes. Compare restore acceptances and refusals
  on identical records. One retained checkpoint already pins a different agent from the base,
  so a matching candidate must still refuse it. Exercise the code that locates and copies both
  files. Keep pinned checker bytes and the original historical result available. An agreed checker that changes needs its own review.
- Checkpoint startup reads Spire's conflict settings, while the manifest hashes `play.SOURCES`.
  A package move alone cannot close this provenance gap. If checkpoint source attribution is the
  reason to do work, address that first on a separate card. Specify the dependency to include in
  both the dirty-tree refusal and the manifest. Plant an edit to it and show that an unrelated
  game edit still behaves according to the selected scope. A shared cross-game runner adds no
  value to this fix.

**4. Native multiplayer.** Move `battle/peers.py`, `engine/{worker,link}.py` and both
`engine/multiplayer_{probe,adapter}` Python/JS pairs into `twwarhammer3/multiplayer/`.
Preserve the public `coordinator`, `worker` and `compare-peers` commands and their arguments.
Inspect the string of Python code passed to the Windows helper in `multiplayer_adapter.py`, as well as static imports. Keep its source root
calculation valid and the two JS files beside their Python loaders.

- Resolve both JS siblings and compare their bytes at base and candidate. Inspect the actual
  helper argv and import it in a fresh appropriate interpreter with side effects stubbed at the
  process boundary. Exercise the documented old and new `python -m` operator paths, including
  argument parsing. Keep the old commands working through thin entry points unless the owner
  chooses a published migration. A collected pytest module alone never exercises a child command.
- Run the link, worker, probe, adapter and peers tests with a synthetic pair of manifests.
  Equal candidate source hashes must still be accepted. An old/new mixed pair must still fail
  the source comparison. Replay the same saved captures through the peers reader and compare
  outcomes, first mismatch and missing evidence. Keep the players' captures and agent digests
  intact. Update the worker guidance and deployment path examples with the move.

For each move run `git ls-files` on the source group and `git grep -n` for the old dotted names,
old path fragments and bare script/asset names before editing. Use `git diff --find-renames`
afterward and account for each old path as a new home, retained entry point or historical mention.
Check the built wheel includes each relocated resource using its ZIP member list. A missing
native environment or corpus is an unavailable check. Both track-only moves are proposals. The offline checks cannot
establish that a Windows worker launched or that a checkpoint restored exactly. Use the appropriate existing
[agreed check](agreed-checks.md) at the candidate revision when a live claim is needed.

## Landing and stopping

JUDGEMENT: Restructuring evidence — Codex, 2026-11-18, proposes the existing gate plus comparisons
of the exact inputs and consumers touched by each card. A whole-corpus replay is the alternative
for broader changes. The owner decides what evidence establishes correctness at a revision.

1. Before coding, confirm the selected card, current base and supported old interfaces. Write
   down each expected observable change, including new hashes and path keys. Record baseline
   outputs and inputs. Use an isolated worktree. Keep the game's live checkout and evidence at
   their recorded revision while comparing.
2. Run the focused checks and the repository's `uv run --locked python scripts/check.py` before
   each commit. Use the gate's actual approval list for changed markers, agreed tests and plants.
   Keep the existing gate rules. Compare structured outputs by filename, presence, type and
   value. Check each expected hash independently against its file. A removed section, a lost
   empty collection or a changed result must appear in the difference. Give a reviewer the
   diff and raw outcomes. Report skips and unavailable environments.
3. A queue depends on checkout HEAD, and an active play job depends on its source scope. Use a
   free merge window under the existing worktree rules, including Spire tools whose scope covers
   shared source. Recheck in main with the local evidence available there. If the candidate
   breaks a loader, moves a pinned checker without a disposition, changes how old results group,
   or requires broad forwarding machinery, keep the last accepted card. After landing, revert
   the offending card in a free window. Preserve every job and ledger produced at either revision.

**Decision now.** My recommendation is cards 1 and 2, with the checks above as proposed offline
evidence. Choosing just card 1 is reasonable if the owner wants to leave source identities alone.
The physical moves can be considered separately. Changes to witness hashing, pooling, trace joins,
evaluation rules or old benchmark status remain with their existing owner decisions. A passing
restructure check at a revision would say nothing about the strength of a policy in battle.

## Research and reproduction

MiniGrid registers a public environment ID and an implementation entry point separately. That makes
a good compatibility question for WH3. A WH3 policy can also be an arbitrary external Python class
whose source imports our modules. Renaming a registry entry cannot repair those imports.
DeepMind Control keeps related tasks together in a domain module and selects the requested task
from that module's suite. This supports keeping family code searchable in place. Its domain loader
imports every listed domain, a dependency cost our offline readers have no reason to pay.
[Source excerpts and versioned links](references.md#restructuring-review-2026-11-18)

On the evidence machine, `runs/restructure-plan-20261115/revision/` holds the parser probe and
reviewers' reproductions. Start at its `handoff.md`. The original `dryrun/` and `rehearsal/` hold
the separate raw gates. In a fresh clone use the two Git revisions if available and the focused
checks above. Local saved evidence is required to reproduce claims about external policies and
older episodes. Verification of the proposed structure and its effects in a game is open.
