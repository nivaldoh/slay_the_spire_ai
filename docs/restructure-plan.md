# Long-term structure of the game AI repository

**Keep one package per game and one small shared package. Give WH3 controllers, scenario families,
benchmark design and result readers distinct homes.** Keep the original games, their protocols,
and their definitions of a result visible in the code. A maintainer should be able to follow a
command from its arguments to the game or saved files it touches, and to the check that would
catch a mistake there.

This is the proposed destination for the whole repository. The first two implementation steps are
useful on their own. The later steps describe how to finish the reorganization. None of these
moves is approved or verified. The source baseline is `e453429`. The owner’s choices appear
under [Decisions for the owner](#decisions-for-the-owner).

### What came from Claude Code

Claude mapped the files and imports, drew a second layout and tried the moves in a separate
checkout. Its later trial stopped five commits into the first six-commit stage. We kept the map,
the checkpoint and multiplayer groupings, and the trial as an example we could run against old
controllers. We changed where live battles and benchmarks belong, and how to move a working
feature safely. The first two steps fix concrete problems before moving files. Steps 3–7
complete the proposed layout. The [earlier decisions](restructure-decisions.md) distinguish
Claude’s recommendations from the choices still up to the owner.

## Where the code belongs

```text
src/
  gameai/         shared Windows, provenance, ledger, model and dataset code
  spire/          the Spire game, with its engine, play, evaluation and learning tracks
  twwarhammer3/
    __main__.py   command names, argument parsing, dispatch
    protocol.py   public observation and orders, acknowledgements and failures
    policy_names.py   parse names used in jobs and records
    scope.py          source paths and recording versions used by a WH3 job
    units.py          calculations on public unit records
    order_text.py     text shared by policies, the live loop and its readers
    engine/       Windows process, game pack, startup and mailbox
    battle/       set up and play a battle, collect its files
    controllers/  reusable policies, their construction and graph tooling
    scenarios/    witnesses, controls, facts and evaluator readings for named battles
    benchmarks/   select trials, set the budget, score and compare them
    results/      write the register, read jobs, render reports and export examples
    checkpoint/   capture, restore, candidate selection and checkpoint RL
    multiplayer/  coordinator, workers, native captures and peer comparison
    mod/  assets/ files loaded by the game
configs/          prompts, scenarios, suites and controller declarations
scripts/          operator commands, repository checks, hooks and deployment tools
tests/            contract and regression tests, explicit live checks and fixtures
docs/             game guides, evidence rules, owner decisions and research history
runs/             ignored local jobs, ledgers, saved evidence and scratch
```

**The WH3 move list.** Each row names the existing files, without the `.py` suffix. Most of the
inputs are in today's `battle/`. A name after an arrow is the target basename. Package
initializers are inert. A retained old entry point has a specific caller as described below.

| Destination | Existing modules and resources |
|---|---|
| Package root | Keep `__main__`, `protocol`. `battle/unit_geometry → units`. The other three proposed root modules are extractions described below. |
| `engine/` | Keep `runtime, pack, startup, doctor, mailbox, manual_capture, windows_capture` in place. |
| `battle/` | Keep `setup, play, capture, reserve, manual_demo`. Setup owns declaration resolution, lobby steps and preflight. Reserve draws and private frames belong on the runner side of the policy boundary. |
| `controllers/` | `controllers → factory`, `configured, scripted, skills, llm, commander, team, local_team, local_command, calibration, evade, reference, replay_schedule, graph, graph_author, graph_goals, graph_initiation, skill_contracts`. The Cannae team and local command adapter belong beside their dispatcher here. Graph authoring has an explicit model-calling command. Loading an existing artifact must work offline. |
| `scenarios/` | The `camp`, `lines` and `escalade` witnesses with their corresponding `*_facts` and `*_readings`; `wall_defence, wall_facts, wall_readings`; `cannae, local_scripts, support_timing, support_evidence, evidence_rules`. Keep the family stems searchable. Add only the files a family actually uses. |
| `benchmarks/` | `benchmark → profile`, `benchmark_plans → plans`, `suite, exact_stats`. A suite can schedule or pay for work. Its plan builder and scoring rules have a different owner from the HTML renderer. |
| `results/` | `stats → register`, `digest, watch, report, report_html, replay, export, graph_view`, with `report_assets/` and `graph_view_assets/` beside their loaders. The register also appends during play. Watch follows growing files. Export writes a new dataset. |
| `checkpoint/` | `battle/{checkpoint,candidates,audit,confirm,rl}` and `engine/{checkpoint_frida.py,checkpoint_agent.js}`. Keep the JS and the standalone Windows runner together. |
| `multiplayer/` | `battle/peers` and `engine/{worker,link,multiplayer_probe,multiplayer_adapter}`, including both sibling JS agents. |
| Game resources | Keep `mod/` and `assets/` at their engine-visible paths, including the startup clip and its license. Leave the Lua packaging and tick behavior alone. |

The earlier full rehearsal put `suite` under reports and moved live play out of `battle/`. The
interim review kept most of `battle/` together. This design keeps the established live-job name
and groups a scenario's public witness with the facts and independent readings used to study it.
That makes a family easier to find, at the cost of moving names that some saved policies import.
Separate per-family packages would give shorter filenames but require more directories and new
import spellings. There is no study here showing that one layout improves agent performance.

### Dependencies that matter in WH3

- A policy receives public friendly units, visible enemies and the custom-battle roster. The job
  owns the mailbox, private evaluation, final state, replay and imagery. A named family may share
  public constants and geometry between witness and evaluator. Its readings never load its witness.
  A static import check and a test of the data a controller actually receives cover different mistakes.
- Keep `policy_parts` and the model-policy names in `policy_names.py`. Keep prompt selection,
  current-provider validation, fresh instance construction and cards in the factory. Compare the
  parser's model names with the prompt map keys. Historical records must parse without consulting
  today's prices. Keep `SOURCES`, track and recorder/evaluator versions in `scope.py` so a worker
  can fingerprint the game without importing `play`. The HTML presentation exclusions belong with
  `report_html.harness`, which interprets old and new manifests.
- Move `distance`, `nearest` and the public geometry used by multiple callers into `units.py`.
  Follow the imports of `unit_geometry._active` through `skills.OUT` before cutting. Preserve the
  actual eligibility set at each caller. Move the public gate-HP rule used by the protocol and
  witnesses into `protocol.py`. Put public unit rules (`in_melee`, `ids_by_type`) in `units.py`
  and the public capture-point `holds` rule beside the gate rule. Keep `group_ids` (private
  deployment matching) and `accepted_orders` (trace interpretation) in
  scenario evidence code. For support timing, extract the shared `TYPES` and `identities` to
  `scenarios/support_facts.py` before treating its evidence reader as independent of its witness.
- Move shared order descriptions from `llm` and `commander`, and the `strength` text used by
  `play` and `digest`, to `order_text.py`. Keep format outputs byte-for-byte, especially text
  inserted into model prompts. Leave a helper at its definition when only one consumer needs it.
- Allow real dependencies by name and purpose. The suite reads trial measures and can render a
  report. The graph view consumes graph definitions and recorded replay. Today `exact_stats.mcnemar` loads `suite.sign_test`, and
  `exact_stats.newcombe` uses `report.wilson`. Put those calculations under benchmarks and
  update the suite and report to call them. Compare the counts, rounding and empty-input
  results before removing the old definitions. A matrix of allowed imports for every file would cost more to
  maintain than these contracts. Keep the existing `gameai` and readings checks.

### Spire and the shared package

| Owner | Long-term home and contract |
|---|---|
| Spire engine and actions | Keep `spire/engine/{runtime,bridge,doctor,windows_relay}`. The Windows relay has to run in its deployed environment. `spire/decisions.py` projects full-game screens and maps a choice to a legal action. `spire/protocol.py` and `spire/policies.py` are first-combat provenance anchors. Retain their paths and bytes. A forwarding import changes both the file and its syntax tree. |
| Spire full runs | Keep the fresh-JVM loop, rule and model policies, save/replay, digest, watch, register and exporter together in `spire/fullrun/`. `openweight.env.RealGame` calls `fullrun.play.play_run` and hands out decisions. Use this one loop for that adapter. A mid-run reset and the simulator each have separate prerequisites. |
| Spire combat and learning | `spire/combat/` owns first-combat catalogs, rollouts, comparisons and evidence. `spire/ppo/` owns its learner, optimizer and resume state. `spire/language/` owns demonstrations, local policy, sampling, evaluation and training. Keep CPU and CUDA extras distinct. An archived experiment or an unimplemented remote trainer stays a proposal until it has a real use. Keep the working tasks, rewards and environment adapter in `openweight/`. |
| Shared services | Keep `gameai/{windows,windows_game}` for OS/process primitives, `provenance` for revision/bytes/atomic writes, `ledger` for durable charges, `providers,llm` for provider routing, wire data, attempts and billing, `lm` for local model operations and `sft` for building datasets. `windows_game.py` is deployed standalone. Keep its standalone imports and entry point. Each game's loop decides how an error ends or delays its own job. |
| A future game | Start its game package, config, tests, guide and run folder with one working observation → action → engine outcome. Use the shared ledger, Windows tools or provider client when applicable. Promote a primitive to `gameai` when a second game needs the same semantics. Keep replay, score, job layout and recoverability with the game that can interpret them. |

`gameai` never imports either game. Adding a full-run Spire policy starts at `spire.decisions` and `fullrun.play`.
It does not require an interface shared with a WH3 policy, which can issue orders asynchronously
and receive an acknowledgement later. For a shared provider change, trace one request through
`gameai.llm.Model`, its reservation and its recorded attempts, then through each game's error
handling. Preserve cumulative charges on reopen, retry and an uncertain billed attempt. A model's
failure to act is distinct from infrastructure failure and from an engine-reported loss.

### Configs, commands, tests and guides

- A WH3 scenario declaration has one home under `configs/twwarhammer3/scenarios/`; compositions,
  prompts and report notes stay data files. Use the existing Spire `configs/llm/` and
  `configs/suites/` paths as its guide requires. New games use per-game directories. Moving price
  data, changing the fingerprint scope, editing a prompt or renaming an explicit CLI input can
  change the experiment and deserves its own decision.
- Keep `python -m spire`, `python -m twwarhammer3`, the queue, `scripts/check.py`, and deployed
  Windows commands as entry points. Keep a small argparse dispatcher in each game. Put business
  logic under the feature that uses it. The queue owns scheduling, a game owns play, an audit
  owns its independent reading of evidence. Organize new multi-file operator tools like the
  existing `scripts/gcp/`; a one-file operator command needs no directory. The Claude and Codex hooks use
  `scripts/hooks/` for tool and stop checks. Git’s separate `scripts/githooks/pre-commit`
  compares the tree with the last pass from `scripts/check.py` for commits from any client.
- Tests stay with the game or feature they exercise. Keep unique file names, the Spire legacy
  test roots and `tests/twwarhammer3/` command paths. Existing graph and team subdirectories are
  useful. Put a shared builder in a small helper beside its users when a second test needs it.
  Importing another test for the fixture, moving each test to mirror every source rename, or adding
  a test for an empty package makes later refactors harder. Preserve the scope and assertions of
  existing agreed tests; a smaller count alone is no evidence that a deletion is safe.
- Root `AGENTS.md` routes to `docs/development.md`, the game guide and the applicable track.
  The WH3 Code map and Spire guide own the current paths. `docs/state.md` gives current status,
  the game log holds counted evidence, `docs/agreed-checks.md` records owner-agreed methods, and
  the review queue holds open decisions. Update the guide that a changed command makes wrong.
  For example, the Spire open-weight page's old description of `RealGame` needs to follow the
  actual adapter before someone plans a second implementation. A new folder needs at most a
  purpose line in the existing map. Keep run evidence, ledgers and migration scratch out of Git.

## What past sessions taught us

| What happened | Consequence for this plan |
|---|---|
| WH3 once grouped different observation delays and intervals into the same results (`b24df11`). Later readers disagreed about when a team member saw the state (`749b3f2`). | The register owns its comparison key. A reader names its time origin. A directory rename cannot justify a new grouping or delay calculation. |
| On request `r532` in the saved `graph-live-20261101/move` trace, the closed graph retained a source of 33.2 s, the no-order poll was at 165.5 s and its acknowledgement at 165.8 s. The digest prints 132.6 s; the replay reports 0.3 s. | Both readings follow their current code. A proposed common reader can expose the poll, member/node source and application times separately. Keep both outputs until the owner decides what each label should mean. The owner's “Leave as is” for malformed or truncated rows still applies. |
| The WH3 readings rule could return zero violations after examining zero inputs. The full-move snapshot comparator also accepted deletion of a whole output section, loss of an empty order list and replacement of a JSON boolean with a number. | Compare the inventory before the values. Challenge the checker with a missing family or a known bad value. A green command on an empty comparison cannot support a preservation claim. |
| In a replay of Spire’s old export rule, the supplied held-out spellings `HELD0UT01` and `00HELDOUT01` both classified as development. Commit `9c43785` fixed both cases. The shared training builder trusts the game export's split. | Spire's exporter owns seed equivalence. Exercise the exporter and dataset reader together on the historical aliases. Sharing a generic seed normalizer with WH3 would hide the owning rule. |
| A WH3 provider 503 body ending in “and stopped” exposed a difference between message matching and typed status handling (`d2e2711`). Spire's rate-limit wait has its own handling. | Keep wire decoding and billing in the client. Test the same transport response against the relevant game rules before extracting common error behavior. |
| An archived Spire learner compared scores from different unlocked-card pools. Commit `774e177` added a pool check, but restarting could still attach a new pool to old scores. Commit `d9a7c35` fixed that path. Four retained training manifests also name an earlier validator path than today's audit lookup. | The evaluator owns cohort identity. The auditor must read the recorded revision/keys. Preserve a pre-existing refusal separately from a regression introduced by a move. |

These are selected incidents from Git, session records and saved inputs. They establish specific
failure modes. They do not establish that a flat folder caused them, or that a new folder prevents
them. The source of the navigation recommendation is the set of tasks in the move list.

## Identity, old records and external code

A **saved name**, the **Python class** found through it, and the **source bytes** of that class are
three different facts. Preserve the supplied policy string in the result. Preserve historical
register rows, manifests and recordings verbatim. Record the actual source file and digest for a
new run. Never label an edited controller with the old digest to make a comparison pass.

1. Before moving a policy, exercise the old factory on names from the register, configs and
   published examples. Capture successful loads, expected refusals, supplied names and defining
   classes separately. At the baseline only 15 of 36 distinct WH3-prefixed class-path strings
   in the CSV still load. Twenty names refer to missing attributes and one to a missing module.
   The old rows remain readable. Reconstructing retired policies is a different task.
2. Keep the old string accepted by the resolver for each supported moved policy. Maintain a
   small explicit old-to-new **module** mapping at the factory and preserve the attribute lookup,
   including re-exports that callers use. Capture the old defining spelling on cards for existing
   classes when that spelling is part of the reader contract. Use actual new paths for genuinely
   new classes. Check `battle.controllers:Skills` and the two spellings of `Hold` through
   `calibration` and `scripted`. They illustrate why the input and the defining class cannot be
   deduced from each other. Under the proposed compatibility choice, support the old inputs
   first. If a new spelling is also accepted, record it as supplied and map a known old class
   identity explicitly wherever comparisons depend on it. Test both spellings with the same
   source. A single module substitution cannot reconstruct every historical class identity.
3. An ordinary Python import inside an external file bypasses the factory. In the earlier
   full-move rehearsal, three saved external policies failed at import. A disposable
   `battle/scripted.py` forwarding `AttackNearest` and `Hold` to their actual definitions
   restored all three imports. On the first saved view for each of four register rows it reproduced
   three recorded decisions and the fourth row's original missing-terrain error. This establishes
   a remedy for those files only. Keep an explicit forward at known import/command entry points
   or leave the definition in place until its caller migrates. Check ordinary Python imports,
   config-only strings and `python -m` subprocesses separately. Avoid global import hooks.
4. Keep the reader's comparison keys. `stats.configuration` uses a shortened external source or
   composition digest. The HTML harness uses paths and hashes with selected presentation paths
   excluded. Match old and new presentation prefixes individually, including retired config
   paths; excluding all of `results/` would incorrectly exempt the exporter. Recompute an old
   report with its old manifest and a new job with its new manifest. Keep new setup groups apart
   unless the owner agrees otherwise. Preserve the owner's status exclusion in replay identity.
5. Graph artifacts compare a frozen library with the current one; a change to the hashed policy
   modules can legitimately refuse an old artifact. The checkpoint reader checks its JS pin.
   One retained checkpoint already differs from the base JS. Spire exports read both
   `src/spire/llm.py` and `src/spire/fullrun/llm.py` renderer keys from historical manifests.
   Preserve old reads and refusals, keep original bytes and Git revisions available, and name
   any new refusal or split. Keep resume at the original revision where its job requires it.

## Implementation order

JUDGEMENT: Migration units — Codex, 2026-11-18, proposes moving one working feature with its callers
at a time. A single mechanical move would create fewer intermediate source setups. Revision
boundaries, review cost and which new jobs can be compared depend on this choice.

Each step is a change or series of small changes that can be reviewed independently. Use separate commits
for a semantic fix and a move. Refresh the actual caller list at the phase base; old migration
scripts apply to different trees. Use `git ls-files` and `git grep` for dotted names, paths,
CLI strings, asset basenames, source maps, plants and marker references. Account for every hit
as an updated consumer, an intentional old entry point or a historical record.

### 1. Repair the evaluator check

In `tests/test_repo_rules.py`, compare the files the readings check visited with every WH3
`*_readings.py`. Include the four known families (camp, lines, wall and escalade). Move a
forbidden witness import outside the old search folder, remove a known family, then try a
legitimate facts-only import. The first two cases should fail and the third should pass.
Run `uv run --locked pytest -q tests/test_repo_rules.py -k readings`.

### 2. Cut dependencies before moving files

Extract `policy_names`, keep its old imports working through `battle.controllers`, and switch
stats, digest, export and HTML over. A temporary version reduced the WH3 modules imported by
stats from 14 to 4. The original and changed readers produced identical rows when each recomputed
stats for five saved episodes. Those outputs differ from the older CSV entries.

Compare `stats.row` and parser refusals in fresh processes, including vendor/model suffixes.
Then move scope, public geometry, shared rules and text for the callers named above. Keep
`battle.play.SOURCES` importable for pinned checkers. Record any hash that changes and why.

### 3. Move checkpoint and multiplayer separately

Move each track with its Python and JavaScript helpers. Open the built wheel, compare the
deployed files' bytes, and inspect the actual command built for Windows. Keep the public
`rl`, `worker`, `coordinator` and `compare-peers` commands and old probe/adapter entry points.

A moved file changes the worker’s path-based source hash. Exercise a matching manifest and the
mixed-version HTTP 409 refusal. Recount copies of saved checkpoint evidence and compare every
field except the specific hashes the card predicted. Keep the saved checkpoint’s original pin.

### 4. Separate results from benchmark design

Move the register and readers with their assets and the code that writes to them during play.
Preserve the exporter's lookup of sibling `report.py` and its two recorded source hashes. Move
the benchmark profile, plans, suite and numerical routines to their assigned homes.

Run stats, digest, export, report and suite collection on the same episodes and frozen plans
before and after. Include an interrupted attempt and an incomplete comparison between policies.
Run the relevant existing browser checks whenever a graph or HTML output changes.

### 5. Move controllers with their callers

First record which class each supported old name loads. Move the factory and generic policies,
then the team and graph code in working groups. Take their loaders, public import paths and
other callers with them. Test a saved external Python controller as well as the built-in ones.

Load an artifact, construct the controller and give it the same public observation and
acknowledgement. Compare orders, the controller’s recorded details and any refusal. Report
graph-library or prompt hash changes individually.

### 6. Move one scenario family at a time

Move a family’s witness, facts and independent readings together. Update its tests, file map,
guide, named commands and any configuration that refers to a source path. Keep scenario IDs,
armies, captured inputs and pass criteria stable. Run the independent readings on the same
saved inputs, including a case that should fail. Repeat for the other families. Check support
timing’s evidence annotations independently of its six policy classes.

### 7. Check the installed commands and update their guides

Use the final paths in the game guides, Code map, queue and hook command checks. Run the CLI
in a fresh process from the installed wheel. Check help, a saved external import, browser asset
loading and the Windows helper command line. Wherever shared code or source scopes changed,
also exercise Spire’s recorded teacher and renderer lookups, dataset split and training resume.
Retire temporary migration commands once the final paths work through these entry points.

The checkpoint source scope deserves a separate fix if the owner wants one. Today the launch
reads Spire's process-conflict settings and fingerprints WH3's `play.SOURCES`. Moving packages
cannot add that dependency to provenance. Decide whether to fingerprint the actual Spire dependency
for checkpoints or give the two consumers a shared process descriptor under `gameai`. Either
choice needs a dirty-dependency refusal and a manifest assertion. Avoid generalizing the two game
launch loops to solve this one problem.

## How to keep the structure useful

Use the public command, its input and its output to place a change. A new WH3 family starts at
the scenario declaration and its public witness. Add a reading when there is a question to answer.
A new report starts with the recorded fields it needs and a reader under `results/`. A change to a
provider starts at the wire response, amount charged and game-specific action on failure. If two
functions have the same shape, first identify whether they mean the same thing. A member's source
time, a graph node's start time and a poll time are a useful counterexample.

Use the existing card, gate and reviewer. Add a lasting test for a concrete way the software
could silently change a result, omit an input, leak private state, double-charge or resume the
wrong job. Run the same check against a plausible wrong version. Temporary move inventories,
import counts, whole-tree snapshots and package counts can be discarded after the comparison.
A new permanent package rule, generated document, registry or scheduler requires a continuing
job that existing code cannot do simply.

For each card, record the base revision, exact input files, expected output differences and a
failing case *before* reading the candidate output. Compare inventories, JSON types, keys and
values; explain each changed hash from the file that produced it. Preserve the original engine
and policy bytes outside the approved edits. Run focused tests, then
`uv run --locked python scripts/check.py` before each commit. Report lost tests, changed skips,
unavailable dependencies and any newly listed approvals. A move that changes an agreed command,
plant or pinned checker uses the existing approval route. Check on main with retained evidence
before making a claim about it. Check for an active queue before landing any commit in its checkout. Check each live job’s
source scope before landing a change there. Some Spire tools fingerprint both games.

If a candidate loses a supported caller, changes a comparison unexpectedly, or needs broad
forwarding machinery, keep the previous coherent phase and split the change or revisit the
destination. After landing, revert the code commit in a free window if necessary. Keep every
result, ledger and manifest from both revisions. Only an owner-agreed check run at a particular
revision can support the corresponding verification claim. A passing offline rehearsal cannot
establish Windows cleanup, real-time play, a restore or a policy's strength.

## Decisions for the owner

The full move list rests on JUDGEMENT `docs/restructure-plan.md` Destination. The sequence
rests on JUDGEMENT `docs/restructure-plan.md` Migration units. The recommendation is to accept
the destination in principle and start with steps 1 and 2.
The other choices can wait for the card they affect. The existing decisions on witness hashing,
trace error handling, battle moves and pooling remain in force unless changed explicitly.

JUDGEMENT: Destination — Codex, 2026-11-18, proposes the package and module homes in this plan.
Keeping the large battle package or grouping all code by scenario would change navigation,
dependency cuts and compatibility work. The move list rests on this choice.

JUDGEMENT: Supported old interfaces — Codex, 2026-11-18, proposes preserving documented and observed
working entry points, including ordinary imports, with bounded forwards. Preserving every private
path or requiring a versioned migration instead changes which old clients can run.

JUDGEMENT: Evidence across revisions — Codex, 2026-11-18, proposes preserving old grouping and
recording actual new source identities. Pooling, extending witness hashes or repinning artifacts
would change what a result can be compared with and needs a separate decision.

JUDGEMENT: Reader semantics — Codex, 2026-11-18, proposes preserving each reader's interpretation
during the move. A shared request/ack join or new age label could change output on saved traces.
Any later reader consolidation depends on deciding the cases that differ.

JUDGEMENT: Restructure checks — Codex, 2026-11-18, proposes focused before/after evidence and
existing agreed checks at their own revisions. A new agreed method or extra live checks would
change the cost and scope of a verification claim. The owner selects those checks.

JUDGEMENT: Checkpoint provenance — Codex, 2026-11-18, proposes a checkpoint-specific scope fix
on its own card. A shared descriptor or leaving scope as it is changes which source edits stop
checkpoint jobs and which dependencies their manifests identify.

Earlier agents' open choices are preserved verbatim in the [decision record](restructure-decisions.md).
The record names the Git revision for each earlier proposal.

## Implementation references

- SMAC exposes both `get_obs_agent` and `get_state`. Use the same explicit distinction when
  following public WH3 input from the mailbox to a policy. Keep evaluator data on its own path.
  [SMAC interface](https://github.com/oxwhirl/smac/blob/d6aab33f76abc3849c50463a8592a84f59a5ef84/smac/env/multiagentenv.py)
- DeepMind Control keeps related cartpole tasks in one domain module. Use that locality for WH3
  families and keep independent readings in sibling files. MiniGrid's registration separates
  an ID from the implementation path. The external-import probe above shows the additional
  contract a Python plugin brings. [Cartpole](https://github.com/google-deepmind/dm_control/blob/1.0.34/dm_control/suite/cartpole.py) · [MiniGrid registration](https://github.com/Farama-Foundation/Minigrid/blob/v2.3.1/minigrid/__init__.py#L94-L106)
- Inspect AI's `read_eval_log` gives callers a named place to read a log. Borrow that approach
  for a shared WH3 parsing rule only once the record semantics are agreed. The current functions
  and ordinary dictionaries suffice. [Log reader](https://github.com/UKGovernmentBEIS/inspect_ai/blob/59c1340741ba863fb0d79287f66420e5dd782480/src/inspect_ai/log/_file.py#L530-L571)
- CleanRL keeps environment construction, agent, optimizer and rollout storage in the PPO execution
  path. Keep Spire's algorithm similarly legible and put original-game lifecycle and evidence
  in their own existing modules. [PPO implementation](https://github.com/vwxyzjn/cleanrl/blob/fe8d8a03c41a7ef5b523e2e354bd01c363e786bb/cleanrl/ppo.py#L129-L187)
- Sacred records source paths, digests and repository revisions separately. For WH3 the source
  inventory must also include the JS, Lua and other resources actually deployed. [Source tracking](https://github.com/IDSIA/sacred/blob/86865b03d05e83da35ca582392ca31777db88d11/sacred/dependencies.py#L445-L470)

The session probes, file inventory and earlier planning evidence are indexed in
`runs/restructure-plan-20261115/handoff.md`. They document the baseline and selected rehearsals.
The proposed combined destination has not been implemented or exercised in either game.
