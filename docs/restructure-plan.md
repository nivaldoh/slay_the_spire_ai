# Plan: restructuring the code

Written 2026-11-15 by Claude Code (the work ran past midnight into 2026-11-16), from the repository
as read at `d3c1f0f`. The owner's goal, verbatim: "You are the long-term owner of this codebase.
Without implementing anything yet, write a detailed, concrete plan to completely restructure the
code to make it better. We need to identify the architecture that will make it as readable,
maintainable, clean and organized as possible. Let's try to make it as easy as possible for you to
work with. Refer to best practices on code architecture. Use some of our collected "research
material" codebases as references on how to structure our code. Carefully explain what changes and
why." And the same day: "Let's be open to any type of structure for now, without restricting
ourselves to previous decisions. Use JUDGEMENT calls in the document so I can decide whether we will
move forward with relevant changes or not." Nothing on this page is implemented. Every choice below
is a proposal, and each one that is the owner's to make carries a marker as
[judgement.md](judgement.md) describes. The evidence is in `runs/restructure-plan-20261115/` in the
main checkout: eleven maps of the code, eight research reports, the clones they read, an import
graph, four independent designs, three judges' reports, six independent checks of this page's first
draft with the record of what each finding changed (`verify/revision.md`), and a second reading of
the revised page by three readers with the record of the corrections it led to
(`recheck/corrections.md`). That folder is local and is not in Git. Nothing here is verified under
the hard rule in [AGENTS.md](../AGENTS.md#verification-hard-rule): no method for checking a
restructure has been agreed with the owner, and section "Limits" says what was read and what was
run. The sections "Summary" and "Decisions for the owner" are written to be enough to decide; the
rest is the evidence and the detail for the agent that does the work.

Short forms: WH3 is Total War: WARHAMMER III. `battle/x.py` is `src/twwarhammer3/battle/x.py` and
`engine/x.py` is `src/twwarhammer3/engine/x.py`. A plant is one of the 493 planted wrong versions in
`tests/plants.toml`. The gate is `scripts/check.py`, and "needs your yes" is the list it prints for
edits that only the owner approves (`scripts/check.py:501-552`). The register is
`docs/twwarhammer3/results.csv`. A test setup is the 8-hex fingerprint the HTML report computes for
a battle (`battle/report_html.py:210-225`); Figure 1 of that report compares battles only inside one
test setup. A harness version is the `-vN-` part of a job's name, recorded in the register's
`harness` column. The Stop hook is Claude Code's check that runs when a session ends
(`scripts/hooks/stop_check.py`). A fake mailbox is the tests' stand-in for the game's file bridge,
and a stub transport their stand-in for a model API. The inventory is
`understand/path-identity-inventory.md` in the evidence folder. The four designs (clean-slate,
agent-first, harness-shaped, role-packages) and the three judges (evidence, simplicity, daily work)
are the files in the evidence folder's `design/`; the six checks (facts, file map, evidence safety,
rules and markers, overengineering, references) are in its `verify/`. K1 to K10 are the check
scripts of C0: K4 accounts for every moved statement, K6 replays controller decisions, K7 compares
what the readers print and K8 compares fixed hashes and values. R1 to R5 are the import rule tests
of "The import rules": R2 forbids one game from importing the other and R3 is the table of which
package may import which. C0 to C11 are the changes of "What changes and why".

## Summary

After the plan `src/twwarhammer3/battle/` (60 Python files at one level, 20,033 lines) is gone. The
WH3 package has five root modules that every part may import (`protocol.py`, `units.py`,
`wording.py`, `scope.py`, `registry.py`) and ten sub-packages named for one job each, with one
folder per evaluation battle; no folder holds more than eleven Python modules. Imports follow one
table that five rule tests check. A controller is named by a declared name and version, and one
module names the files of a job folder. `gameai` gains one file; Spire, the Lua mod, the registers,
`scripts/`, the test folders and the docs tree keep their paths.

Order of work: decisions and check scripts (P0); path lists that fail when they match nothing (P1);
the source scope and name parsing in root modules (P2); shared facts moved out of large modules,
four cuts that remove eleven wrong-way imports, and the import rule as a table of module names (P3);
a generated Code map and a guidance page (P4). P0 to P4 move no existing file (one, `benchmark.py`,
is cut into three in place) and the plan can stop there. Then, on a second yes: declared controller
names (P5a), one tool-made commit that moves 74 files (P5), docs (P8), live checks (P9). Test
imports (P7) are recommended and have their own question (J16): one `pythonpath` entry in
`pyproject.toml`, which is in both games' scopes, builder moves in 13 test files and a rule test; P7
may land any time after P1. Five further splits (P6) and moving the test files into package folders
are described and recommended against.

The three largest costs are listed below. Beside them, no measurement shows that sub-packages
improve an agent's results, and two daily routes get longer after the move (C7).

1. Owner approvals: at the move about 286 plant `file` values, 102 marker references (69 that the
   gate checks) and 219 import lines in 131 test files, proposed as one batch (J4); smaller batches
   at P2 and P3.
2. Breaks in the report's history: P1, P2, P3, P7, P5a and P5 each change a file the test setup
   hashes, so battles played between two of them share a setup only with each other (J7).
3. Live checks: 14 agreed entries need a game. Every commit that `docs/agreed-checks.md` names
   differs from `d3c1f0f` in at least 62 play-scope files (`git diff --name-only`), so no entry has
   a pass at today's HEAD either. The restructure adds to that distance, and a pass at a
   restructured revision needs a rerun at 1x (J24). Game hours and the size of the check scripts
   were not estimated.

## Decisions for the owner

Every marker on this page, with the recommended option first. Markers dated 2026-11-16 are choices
made or reversed in the revision after the six checks. The first three rows are asked before any
work starts; J4 is needed from P2's first plant batch. The next group is needed by one of P1 to P4
each. The third group is asked at the second yes; "How to answer" names the parts of J7, J13 and J24
that matter earlier. In the last group no phase from P0 to P5 waits for an answer. For J15, J17, J18
and J26 to J28 the recommended option changes nothing, so no answer is needed unless the owner wants
the other option. J16 is asked before P7: its recommended option moves no file and edits
`pyproject.toml` and test files (C9). J29 and J30 recommend a change and are asked on their own
later cards (C11); until the owner answers, nothing of theirs is built and the owner's earlier
answers stand. The full question, what happens today and the best case for each other option are
under each marker, in the section the last column names.

| Id | Name | The question | Options (recommended first) | Cost of the first option; earlier answer or marker it changes | What waits on it |
|---|---|---|---|---|---|
| J3 | Verification method | Which repeatable offline check may a phase report cite? | (a) the K checks built for each phase become one agreed entry, "restructure: offline equality"; (b) no agreed method, every report says "unverified" | New scripts under `runs/`, each first shown to fail on a planted wrong version; they say nothing about live play | every phase report; C0 |
| J5 | Stop point | Is the move decided now or after P4's report? | (a) P0 to P4 now, the rest on a second yes; (b) all phases now; (c) stop for good at P4 | For P0 to P4: 19 plant `file` values and 3 plant texts, about 60 assert lines, a new test setup at each of P1, P2 and P3, live passes stay at their old revisions | P5a, P5, P6, P8 and P9 (P7 waits for J16 only); C7 |
| J4 | Batch approvals | How are edits that only rewrite a path approved? | (a) one batch per phase on a table and the tool's count; (b) item by item | The largest batch is about 286 plants at P5; the largest approved so far was 23 | P2 to P8; C0 |
| J9 | Missing scope path stops a job | Should a scope path that does not exist stop a job? | (a) yes, raise; (b) keep passing | A new refusal in code both games run; 7 plants name the file | P1; C1 |
| J10 | Pinned hashes | Should a tracked file of content hashes exist? | (a) no file, K8 compares the values at each phase; (b) a file outside the agreed directory, shown in reports; (c) a file whose change needs a yes | None; a changed pack or library hash keeps showing only at the next restore or load | P1; C1 |
| J12 | Presentation list | Which files never start a new test setup? | (a) the same files, as live paths and recorded-only paths; (b) all of `reports/` after the move | Three items change status; the marker Test setup moves to `scope.py` | P2, P5; C3 |
| J34 | Game process names in gameai | Where does WH3's checkpoint code learn Spire's process names? | (a) a data file in `gameai`, compared with each runtime by a test; (b) keep the import of `spire` as R2's one listed break | New data beside the two-games guard; a new file in both games' scopes | P2; C3 |
| J35 | Root modules before the move | Are four new root modules created before the package set is decided? | (a) yes, in P2 and P3; (b) new modules stay in `battle/` until P5 | Every option of J13 then keeps these four modules | P2, P3; C4 |
| J11 | Provider rules stay in the protocol | Do `policy_call` and `account_stop` stay in `protocol.py`? | (a) yes, the rule allows its two `gameai` imports; (b) move them to `controller_call.py` | None; every importer of the protocol keeps loading the model API, 0.03 to 0.1 s as measured | P3; C4 |
| J36 | Controller files before identity | May P2 and P3 change import lines in controller files before J1 is answered? | (a) yes; (b) wait for J1 | Each card's file hash changes; 3 `evade` rows stop matching the hash of later jobs | P2, P3; C4 |
| J31 | Recorded hashes after extraction | May statements leave six files whose hash a card or manifest records? | (a) yes, the report names the values; (b) leave the statements; (c) record the new modules' hashes too | Card hashes and three other recorded values cover less; the one reader that compares a card hash does so inside one source commit | P3; C4 |
| J33 | Import rule checker | How are the import rules checked? | (a) syntax-tree tests in `tests/test_repo_rules.py`; (b) Import Linter as a development dependency | A table kept by hand in one test file | P2, P3; C4 |
| J19 | Code map generated | Are the three hand-kept file lists built from docstrings? | (a) built and tested for freshness; (b) kept by hand | The wording the owner reads becomes the docstrings'; replaces the format under `JUDGEMENT?` One file per line (Claude Code, 2026-11-01) | P4; C6 |
| J20 | Guidance page | Where does area guidance live? | (a) one page under `docs/` and one route line in `AGENTS.md`; (b) `AGENTS.md` files beside the code | One line in the owner's rule file | P4; C6 |
| J1 | Controller identity | What names a controller in a result? | (a) a declared name and version, hash recorded; (b) the module path and file hash, as today | Needed before a file moves; settles `JUDGEMENT?` Witness hash ("Decide later", 2026-11-15) | P5a, P5; C2 |
| J2 | Old and new rows | Do old class-path rows pool with declared-name rows? | (a) no, the alias table only labels; (b) pool approved pairs, keyed on the declared version; (c) pool all | None; (b) and (c) change `JUDGEMENT?` Summary identity (Claude, 2026-11-05), never asked | every rate after P5a; C2 |
| J8 | Names | How are declared names spelled? | (a) `battle.role`; (b) underscore names; (c) the owner's own list | About 81 names fixed for good in the register | P5a; C2 |
| J32 | Version bump rule | When does a declared version change? | (a) when some observation gives other orders; (b) on any byte change of the file; (c) on any change to orders, timing or a request body | A missed bump pools two behaviours, and K6 is the only check | P5a; C2 |
| J6 | Package move | Do existing files and battles move? | (a) all, in one tool-made commit; (b) only new battles get folders; (c) no move | The plan's largest cost; departs from the 2026-11-15 report's "Do not move existing battles" | P5 to P9; C7 |
| J7 | Test setup across the move | May battles before and after the move share a test setup? | (a) no, the path-keyed rule stays; (b) a declared harness version | One boundary per phase that is followed by a battle; (b) is the change-levels table ("Decide later", 2026-11-15) | the boundaries of P1 to P3 and P7, which land under (a); when P5 may land; C7 |
| J13 | Package set | Which sub-packages and which import table? | (a) ten sub-packages by role; (b) seven larger role groups; (c) battles at the top level, layered inside; (d) sixteen smaller ones | A wrong boundary costs the same approvals again; 106 of 150 multi-module commits cross (a)'s packages | R3's module table in P3; P5; C7 |
| J14 | Battle folder names | What is a battle's folder called? | (a) its scenario file's name, stems and pages kept; (b) rename stems and pages too | A battle keeps four names | P5; C7 |
| J21 | References by path tail | How does a "rests on" line name a file? | (a) shortest unique path tail; (b) path from the root | Changes the convention on the 58 gate-checked references that give a root path | P5; C7 |
| J22 | Module-path commands | Do the four `python -m <module>` commands keep that form? | (a) yes, at new module paths; (b) become subcommands | One long module path; the hook list and docs follow | P5; C7 |
| J23 | No-marker list | Do the six policy files still carry no marker? | (a) yes, same files at new paths; (b) drop the rule | None beyond paths, unless the marker's rule for a module cut from one of the six is meant for `units.py` and `wording.py` (Limits) | P5; C7 |
| J25 | Saved scripts at their revision | How is a saved script under `runs/` rerun after the move? | (a) at its recorded revision, and the pinned checker gets an approved copy at P9; (b) keep old module paths importable; (c) as (a) with no copy | One live agreed check cannot be rerun at HEAD until its copy is approved | P5; C7 |
| J24 | Live checks after the restructure | When does a live-checked feature count as verified again? | (a) when rerun, in a set the owner picks; (b) carried over on the offline checks | Game hours, not estimated | P9, or after P4 if the plan stops there; C10 |
| J15 | Further file splits | Are five more files split after the move? | (a) none; (b) `setup.py` only; (c) all five | None; five files keep several jobs each | P6; C8 |
| J16 | Test folders by package | Do the flat WH3 test files move into package folders? | (a) none, one `pythonpath` entry and a rule test; (b) 109 files move | One `pyproject.toml` line in both games' scopes; differs from `JUDGEMENT` Test layout (Codex, 2026-10-23) | P7; C9 |
| J17 | Spire | Does any Spire file change? | (a) no; (b) `scope.py` and seven test folders under `tests/spire/` | None | nothing in this plan; What stays as it is |
| J18 | Cloud prices stay in the play scope | Should `gcp-regions.json` stay in every job's fingerprint? | (a) yes, leave it; (b) move it to `scripts/gcp/` | None | nothing in this plan; What stays as it is |
| J26 | Graph library rule | Should authored graphs saved before 2026-11-14 load again? | (a) no change, the loader keeps comparing bytes; (b) an approved list of old digests; (c) declared versions | None | nothing in this plan; What stays as it is |
| J27 | Lua untouched | Is the battle Lua split? | (a) no, not in this plan; (b) split it alone, with every live check | None | nothing in this plan; What stays as it is |
| J28 | Scripts stay flat | Is `scripts/` grouped by what each script serves? | (a) no; (b) folders for the code page, WH3 tools and Spire drivers | None | nothing in this plan; What stays as it is |
| J29 | Shared trace reader | One decision join and one record description for all readers? | (a) yes, one reader per commit, any time after P3; (b) keep the seven loops | Departs from the strict reading of "Leave as is" (2026-11-14) | later card; C11 |
| J30 | Launch helper | One module for the launch sequence? | (a) yes, with one live launch first; (b) leave the copies | Changes launch code, whose only real check is a game | later card; C11 |

How to answer. P0 waits for J3 and J5; J4 is needed before P2's first plant batch and can be
answered with them, so one line is enough, for example "J3 a, J5 a, J4 a". J9 and J10 are asked on
P1's card. J12, J33, J34, J35 and J36 are asked before P2 and J11 and J31 before P3, at most three
on a card (`docs/workflow.md`, "Questions"). J19 and J20 are asked on P4's card and J16 before P7.
J1, J2, J8, J32, J6, J7, J13, J14, J21 to J23 and J25 are asked at the second yes, three at a time;
J24 is asked then, or with P4's report if the plan stops there. Two of these have a part that the
first yes already spends. Under J7 (a) each of P1, P2, P3 and P7 that is followed by a battle starts
a new test setup, and a later answer (b) does not undo it, so an owner who may want J7 (b) says so
before P1. R3 lands in P3 with the ten groups of J13 (a), so an owner who may want J13 (b), (c) or
(d) says so before P3. J15, J17, J18 and J26 to J28 need no answer for this plan; J29 and J30 are
asked on their own later cards.

The seven decisions that settle most of the plan, with the cost of the first option and the best
case for another:

- **J3.** Cost: new check scripts that must each fail on a planted wrong version before they count.
  Best case for (b): the agent that makes the moves also writes the checks, and agreeing before one
  run may give them more weight than they have earned.
- **J5.** Cost of (a): a wait between P4 and P5 in which battles land in a test setup of their own.
  Best case for (c): P0 to P4 remove the wrong-way imports and one cycle, put R3 in force, make the
  path lists fail when they match nothing and generate the Code map; policy names stay module paths
  and `battle/` stays flat, and no measurement shows that sub-packages improve an agent's results.
- **J4.** Cost: one approval covers about 286 plant edits at P5, on a count made by a new tool.
  Best case for (b): the largest batch approved so far held 23 edits.
- **J1.** Cost: a name is fixed for good, and a behaviour change with the version left alone is
  filed with the old behaviour. Best case for (b): a hash changes by itself when the file changes.
- **J2.** Cost of (a): none. Best case for (b): the 16 `CentreSupport` rows are the largest sample
  of a witness that still imports, and without pooling a later battle never joins them.
- **J6.** Cost: the approvals of cost 1, a new test setup, and live passes further behind. Best case
  for (c): the import rule works on the flat folder, the two daily routes get longer after a move,
  and the move's approvals give a narrower folder listing.
- **J7.** Cost of (a): no controlled comparison spans a phase boundary. Best case for (b): where K4
  and K6 pass, no statement and no replayed decision changed, and earlier battles stay usable as
  controls; K6 does not run for P1 to P4 (C0).

## What is wrong today

Each problem has its number and the place it was counted. Counts over the register and the plants
file were redone for this page with `python3 -I` snippets (`csv`, `tomllib`); the rest come from the
maps under `runs/restructure-plan-20261115/understand/`, from the six checks, or from the command
given.

### A file's location and bytes are identities

- **Policy names are module paths.** 39 of the 49 policy names in the register are `module:Class`
  paths, on 192 of 857 rows. 24 of those names (132 rows) no longer import. `controller_class`
  imports the string (`battle/controllers.py:135-145`), so moving a file renames its controllers.
- **A controller's card hashes one file.** `card` records the sha256 of the file that defines the
  class (`battle/controllers.py:149-159`), and `stats.configuration` writes 12 hex of it for a
  class-path policy (`battle/stats.py:41-47`). 19 register rows carry such a hash. 16 of them hold
  `6aac1c81f8dd` for `cannae.py`, which hashes to `e566e54edf8b` today (`sha256sum`).
- **Every controller file changes bytes when a package path changes.** All 20 files that define a
  class with `decide` have between 1 and 7 `from twwarhammer3...` import lines (inventory, 1.4), so
  a move rewrites their hashes even where the file stays put.
- **The report's test setup hashes paths.** `report_html.harness` hashes the manifest's `{path:
  sha256}` map less nine prefixes (`battle/report_html.py:41-45`, `:210-225`).
- **Approval registers name paths.** 277 of 493 plants name a file in `battle/` and 28 one in
  `engine/`; 552 plant test targets name 84 test files, 335 of them flat under
  `tests/twwarhammer3/`. 199 marker references are checked by the gate, 150 with a path from the
  root and 49 with a path tail (`check.RESTS_ON`, `scripts/check.py:124`). `docs/agreed-checks.md`
  names 33 files and the directory `tests/twwarhammer3`.
- **Path lists stop guarding without a message.** A scope path that does not exist matches nothing
  and passes (`src/gameai/provenance.py:38-53`). The readings rule returns an empty list when its
  glob finds no file (`tests/test_repo_rules.py:117`). One of the nine presentation prefixes,
  `configs/twwarhammer3/scenarios.json`, matches no tracked file since 2026-11-15. The Stop hook's
  command and checker names are literals (`scripts/hooks/stop_check.py:41-46`), and its test builds
  fake processes from the same literals (`tests/test_hooks.py:249-266`).

### No module describes a job's record

- **File names are literals.** `"manifest.json"` is on 36 lines in 17 files of `src/twwarhammer3`,
  `"trace.jsonl"` on 28 in 15 and `"result.json"` on 20 in 13: 79 lines in 21 files
  (`grep -rnE --include=*.py`).
- **The record is described nowhere.** Eight functions write 55 result keys and 12 trace kinds
  (`battle/play.py:317-826`; runtime map). `schema_version` is written at `battle/play.py:146` and
  compared by no reader (`grep -rn schema_version src/twwarhammer3`).
- **Each reader parses the trace itself.** Seven loops join a decision to its acknowledgement, and
  the member source-time fallback is written six times (readers map, 2.1).

### Small shared facts sit inside large modules

- **`distance` lives with the scripted policies.** 20 modules import `battle/scripted.py`; 15 take
  only helpers and 10 only `distance` (`grep -rnE "from twwarhammer3\.battle\.scripted import"
  src`).
- **The source scope lives in the job loop.** `SOURCES` is at `battle/play.py:87-88`, and seven
  files of `src` and `scripts` import the loop at eight sites to read it; four of them need nothing
  else from it. Three live checkers under `tests/twwarhammer3` read it through the loop as well
  (`check_wh3_army_setup.py:26`, `graph/check_wh3_graph.py:247`, `team/check_wh3_team.py:170`).
  `engine/worker.py` loads 31 project modules and `play.py` 27 (7,935 lines) (runtime map, section
  3).
- **Readers import controller modules for names and wording.** Nine imports run from reader modules
  to controller modules. Eight of them fetch `policy_parts`, `MODEL_POLICIES` or order text from
  `controllers.py`, `llm.py` and `commander.py` (`battle/digest.py:30-32`, `battle/watch.py:30-32`,
  `battle/export.py:21`, `battle/report_html.py:31`, `battle/replay.py:16`).
- **One late import in the protocol hides a cycle.** `protocol.py:301` imports `evidence_rules`
  inside a function, because `evidence_rules` imports `setup`, which imports the protocol.
  `protocol.py:17-18` also imports two exception classes from `gameai.ledger` and `gameai.llm`, so
  the 13 modules that take `friendly_units` from it load the model API, which takes most of the time
  of `import twwarhammer3.protocol`: 91 of 99 ms in the run made for the revision, and 23 to 84 ms
  of 30 to 93 ms in three runs made for the corrections (`python -X importtime`).
- **Cycles and one cross-game import.** `runs/restructure-plan-20261115/layers.txt:1-22` lists four
  import cycles, three in WH3. `battle/checkpoint.py:32` imports `spire.engine.runtime`.
- **Measured against the target table.** With every file placed whole in its target package, 26
  imports run a forbidden way: `runs/restructure-plan-20261115/scripts/final_plan/edges.py` prints
  27, one of which, `graph_view.py` loading `graph.py`, the table allows by name.

### Flat folders and files with several jobs

- **Two flat folders.** `battle/` holds 60 Python files; `tests/twwarhammer3/` holds 135 files at
  one level, 118 of them test files (`git ls-files`). One battle's parts sit in five places under
  four names: the walled siege defence is `wall_*.py`, `haengju-eval.md`, `siege_defence.json` and
  `cth-emp-siege-a-v1` (evaluation map, 1.3).
- **Files with several jobs.** `play.py` (826 lines) holds nine, `setup.py` (1,119) four,
  `checkpoint.py` (1,017) a launcher and offline analysis, `benchmark.py` (240) six, `suite.py`
  (582) eight, `controllers.py` (249) five (the maps' counts).
- **Copies.** The launch sequence is written five times in `src/twwarhammer3` and three times in
  live checkers (`grep -rnE 'prepare_runtime\(\)|RuntimeLock\(\)' src`; engine map).
- **Tests reach helpers three ways.** Bare names, a `pythonpath` line (`pyproject.toml:53`) and
  `sys.path.insert` in 15 files, each of which inserts `tests/twwarhammer3`; 13 test modules are
  imported by 13 others; the tests hold 713 `monkeypatch.setattr` calls, 48 of them on
  `battle/play.py` (tests map; file-map check).

### Hand-kept descriptions

- **Each code file is described in four places.** The Code map in
  [twwarhammer3/README.md](twwarhammer3/README.md) holds 131 entries, 100 of them for Python
  modules whose docstring they repeat; only presence is checked. The unchecked lists have drifted:
  `docs/spire/AGENTS.md` misses three files, `tests/README.md` misses seven helper rows, and
  `docs/development.md:38` names a `card` command that no longer exists (docs map, 4.1 and 4.2).
- **The reading route is long.** A normal WH3 source change is routed through 955 lines in six
  files before a source file is opened: `docs/workflow.md` 338, the Code map 223, `tests/README.md`
  136 and three shorter parts (agent-friendly research note, 2.3).
- **The list of commands that start a game exists in six places** with different contents (scripts
  map, problem 1).

## Target structure

### The tree

The tree shows the recommended options. Files that an option would add are named in C8 and C9.

```text
AGENTS.md                        one new route line to docs/twwarhammer3/code.md (J20)
CLAUDE.md README.md              unchanged
pyproject.toml uv.lock           unchanged except one pytest pythonpath entry (J16)
.agents/ .claude/ .codex/        tool settings and skills: paths unchanged, path text follows
.github/                         CI, unchanged
src/gameai/                      code both games import; imports no game
  ledger.py providers.py llm.py  paid model calls
  provenance.py                  repository root, hashes, source fingerprints
  windows.py windows_game.py     Windows process ownership
  games.py                       new: each game's install folder and process names, as data (J34)
  lm.py sft.py                   local model helpers; the dataset command
src/spire/                       Slay the Spire; no file changes (J17)
src/twwarhammer3/
  __main__.py                    the command line, one file
  protocol.py                    what a controller sees and may order; the failure classes
  units.py                       new: helpers on public unit records (distance, nearest, able)
  wording.py                     new: one-line text for orders, plans and unit types
  scope.py                       new: what a job's code identity covers; the presentation list
  registry.py                    new: policy name parsing; after P5a the declared controller
                                 names, versions and old names
  engine/                        install, launch pieces, file mailbox, capture scripts
  mod/ assets/                   the Lua mod and the startup clip; bytes and inner paths unchanged
  scenarios/                     what a battle is: catalogue, declaration rules, lobby steps and
                                 start checks (setup.py), benchmark profiles, the reserve
  records/                       what a job folder contains: file names (layout.py), the outcome
                                 label, the register writer
  controllers/                   controllers not tied to one battle; how one is built and carded
    team/                        controllers with several members: dispatcher and local team
    graph/                       graph controllers: contracts, runtime, goals, authoring, artifacts
  battles/                       rules the evaluation battles share; the replay schedule
    camp/ lines/ siege_defence/ siege_attack/ cannae/ support_timing/
                                 one folder per battle: witness, controls, shared values, readings
  run/                           the play job: loop, capture, owner demonstration
  reports/                       readers of finished jobs: digest, watch, report, page, replay,
                                 export, graph view, statistics, and the two asset folders
  benchmark/                     plans of many jobs and the coordination suite
  checkpoint/                    battle checkpoints, attempt analysis, checkpoint RL, Frida agent
  multiplayer/                   native multiplayer: link, worker, probes, adapter, peers
configs/                         unchanged (J18)
scripts/                         gate, hooks, code-page tools, WH3 tools, Spire drivers; no moves
tests/                           unchanged folders (J16, J17); repository tests and plants.toml at
                                 the top, gameai/, spire/ and Spire's seven folders, twwarhammer3/
                                 with team/ graph/ checkpoint_siege/ prompts/
docs/                            unchanged tree; gains this page and twwarhammer3/code.md
runs/                            local evidence, ignored by Git; unchanged
```

After the plan `src/twwarhammer3` holds 82 Python modules besides the `__init__.py` files: 6 at the
root, 7 in `engine`, 3 in `scenarios`, 3 in `records`, 11 in `controllers` with 3 in `team/` and 6
in `graph/`, 2 in `battles` with 16 in the six battle folders, 3 in `run`, 9 in `reports`, 2 in
`benchmark`, 6 in `checkpoint` and 5 in `multiplayer` (counted from the file map). Today it holds
73, and 3 `__init__.py` files against 19 after. 23 of the 82 repeat their folder's name
(`battles/camp/camp.py`, `controllers/graph/graph_author.py`, `reports/report_html.py`), because a
file that moves keeps the prefix that groups it today.

### The import rules

A package may import the packages on its row, the root modules and `gameai`. "Root" means
`protocol.py`, `units.py`, `wording.py`, `scope.py` and `registry.py`. `controllers/`,
`controllers/team/` and `controllers/graph/` are one unit for R3 and import each other.

| Package | May import inside `twwarhammer3` | Must not import | The check |
|---|---|---|---|
| `gameai` | nothing | any game package | R1, exists (`tests/test_repo_rules.py:156-170`) |
| `spire`, `twwarhammer3` | their own modules | each other | R2, new; 1 break today (`battle/checkpoint.py:32`) |
| root modules | each other | any sub-package | R3 |
| `engine` | root | every other sub-package | R3 |
| `scenarios` | root | every other sub-package | R3 |
| `records` | root, `scenarios` | `engine`, `controllers` and everything above it | R3 |
| `controllers` | root, `scenarios`, `records` | `battles`, `run`, `reports`, `benchmark`, `checkpoint`, `multiplayer`, `engine` | R3 |
| `battles` | root, `scenarios`, `records`, `controllers` | `run`, `reports`, `benchmark`, `checkpoint`, `multiplayer`, `engine` | R3 |
| `run` | root, `engine`, `scenarios`, `records`, `controllers` | `battles` (reached by registry names), `reports`, `benchmark`, `checkpoint`, `multiplayer` | R3 |
| `reports` | root, `records`, `scenarios`; `graph_view.py` alone also `controllers/graph/` | `run`, `engine`, `battles`, `benchmark`, `checkpoint`, `multiplayer`, other controllers | R3 |
| `benchmark` | root, `records`, `scenarios`, `reports`, `controllers` | `run`, `engine`, `battles`, `checkpoint`, `multiplayer` | R3 |
| `checkpoint` | root, `engine`, `scenarios`, `records`, `controllers`, `run` | `battles`, `reports`, `benchmark`, `multiplayer` | R3 |
| `multiplayer` | root, `engine`, `scenarios`, `records`, `run` | `battles`, `reports`, `benchmark`, `checkpoint`, `controllers` | R3 |
| `__main__.py` | anything, imported inside the command that needs it | nothing | none |
| a `*_readings.py` module | may import: `protocol.py`, `units.py`, `battles/evidence_rules.py`, `controllers/unit_geometry.py`, its battle's `*_facts.py`; may load besides, through those: `scenarios/setup.py`, `controllers/skills.py` | any other module of the package, directly or through what it loads | R4, exists (`tests/test_repo_rules.py:173`); its two lists are edited at P3 and given new paths at P5 |
| every module | | an import cycle, function-level imports counted | R5, new; three groups listed by name |

R1 to R5 are plain tests in `tests/test_repo_rules.py` that walk the syntax tree, as the two
existing rules do, each with a planted violation and a failure message that says what to do (J33
asks whether Import Linter should check them instead). R3 lands in P3, while `battle/` is still
flat, as a table from module name to package; a module missing from the table fails the test. P5
replaces the module names by folder names. With the cuts of P3 the table has one allowance by name
(`graph_view.py`) and no other exception: the file-map check applied it to every use of a name after
P3 and after P5 and found no break (`verify/file-map/check_map.py`, sections "rules" and "cycles").
An unmatched exception fails in Import Linter by default too
(`refs/import-linter/docs/contract_types/index.md:66-70`, `b2d4938`). R5 lists three groups:
`controllers.py` with `configured.py` (a composition builds its leaves through the normal factory,
and the factory builds a composition), `rl.py` with `confirm.py` (each imports the other inside a
function), and Spire's frozen `combat.evidence` with two `language` modules. No rule can see a class
loaded from a string; `registry.py` is the one place that does it, and its own test imports every
row. Tests and scripts are outside R3.

Naming rules: a file that moves whole keeps its base name; base names are unique inside
`src/twwarhammer3` (a test); a part cut from a module carries the subject in its name
(`graph_artifact.py`, `outcome.py`), never `utils.py` or `helpers.py`; a battle's folder is named
after its scenario file; the suffixes `_facts.py` and `_readings.py` keep their meaning. No outside
reference was read for these naming rules.

Where a new thing goes:

| New thing | Goes | The check that names a missing part |
|---|---|---|
| Controller for any battle | a module in `controllers/`; one row in `registry.CONTROLLERS` per class a job may name | the registry test; one contract test run over every row |
| Evaluation battle | `battles/<name>/` with its witness module, `<stem>_facts.py`, `<stem>_readings.py`; a registry row per class; the scenario file; the page | the battles test, which lists the folders under `battles/` and checks each for these files (`cannae/` and `support_timing/` are exempt by name: they have no facts or readings module) |
| Scenario | an entry in `configs/twwarhammer3/scenarios/<family>.json` | `test_wh3_scenario_status.py`, as today |
| Reader of finished jobs | a module in `reports/` | R3 |
| File in a job folder | a function in `records/layout.py` | the literal test |
| Command | `run_<command>` in `__main__.py`, marked if it starts a game | the command-list test against the Stop hook |
| Test | `tests/twwarhammer3/test_wh3_<module>.py`; shared builders only in a `wh3_*.py` helper module | a test file that imports a test file fails |

## What changes and why

The changes are in the order of work, except that the second step of C2 lands as P5a, just before
C7. Reference paths that start with `refs/` are under `runs/restructure-plan-20261115/refs/`; the
commit of each clone is in section "References".

### C0. Check scripts, built before the change they check (P0, and again before P5a and P5)

**Today.** No repeatable check for "this change moved code and changed no behaviour" is agreed. The
gate lists every changed plant by id and every changed agreed file by name, and shortens only the
marker, assert and skip lists to three items and "+N more" (`scripts/check.py:496-498`, `:514-537`).
Saved evidence is under `runs/` in the main checkout only: in a worktree the tests that read it
skip, and the gate does not compute the code-page flags (`docs/workflow.md:80-81`;
`scripts/check.py:768`). The gate at `d3c1f0f` in the main checkout shows 4210 passed and 44
skipped; the worktree gate one commit earlier shows 4154 passed and 70 skipped
(`runs/checks/20261115-225955-d3c1f0f-3729892.log`,
`runs/checks/20261115-225654-a03a804-3722350.log`).

**Change.** Under `runs/restructure-<date>/`, ignored by Git, in three builds. Before P1: K1, K2,
K4, K5, K7, K8, K10 and the fingerprint part of K9, with a baseline taken at the commit P1 starts
from, in the worktree and in the main checkout. Before P5a: K6. After the second yes: the move tool,
K3 and the table part of K9. No decision replay therefore runs in P2 and P3, which change controller
files (C4, Cost). Each script is first shown to fail on a planted wrong version, and the comparison
scripts are first run base against base to show that their output is stable.

The move tool applies a table of old and new paths (`runs/restructure-plan-20261115/file-map.tsv` is
its draft) with `git mv`. It rewrites import lines and dotted module strings in `.py` and `.cjs`
files, repository paths in the tracked files under `.claude/`, `.codex/` and `.agents/`, path
constants, the `file` values of plants, the plant texts it lists in full, marker references,
Markdown links and path tokens in `docs/agreed-checks.md`. It never touches
`docs/twwarhammer3/results.csv`, a `log.md`, a file under `configs/`, the keys of
`registry.ALIASES`, or a class-path string in `docs/agreed-checks.md` (`:19`, `:38`): those are
recorded names.

| Check | What it compares | Fails on |
|---|---|---|
| K1 gate | `uv run --locked python scripts/check.py`, four runs per phase: plain in the worktree; with `--extra train` and `--extra llm` for P1, P2 and P7, which touch `src/gameai` or `pyproject.toml` (the plain gate skips every torch test, 40 skips); plain in the main checkout after the fast-forward; with `GAMEAI_TEST_WINDOWS=1` for P5 | any failure; passed, failed and skipped counts are reported. A phase is finished when the run in the main checkout passes |
| K2 plants | `scripts/check.py --plants`; the run in the main checkout is the one the agreed entry "Test suite rejects its kept wrong versions" asks for (`docs/agreed-checks.md:77-78`) | fewer plants caught than at the base (493 today) |
| K3 reproduced move | the move tool run on the parent commit with the table | any difference from the move commit; the commit message holds the sha256 of tool and table |
| K4 statement accounting | every top-level statement of a changed module, base against head. It lists each edit this page names in words, each moved statement that reads `__file__` or `__name__`, and each statement that crosses the presentation list | a statement missing, doubled or changed outside import lines, docstrings and the listed edits |
| K5 same tests | collected test ids, pass count, skip count and each skip reason, in the worktree and again in the main checkout against a baseline taken there | a test lost, or a test that became a skip (a wrong `parents[n]` depth does this) |
| K6 decision replay | each controller class built at base and at head, one process per worktree, fed the same observations and acknowledgements (test fixtures and the `observation` rows of saved traces); orders and metadata byte for byte, less a listed set of fields that hold a module path; request bodies for model controllers with a stub transport. After P5a a declared name is mapped to its base class path through the alias table | any difference; a missing base; a controller with zero observations |
| K7 reader equality | `stats.row`, the outcome label, `report.collect`, `digest`, the replay payload, export rows and `report_html.display_data` over every result under the main checkout's `runs/` that a WH3 reader accepts, by absolute path, with every plan row found; each live checker's `--recount` over the evidence folder its agreed entry names; from P5a, for each key of `report_html.SCRIPTED` and `LOCAL_CONTROLS` and for one composed team, a fake-mailbox job at head whose reader labels equal those of a saved job of the same controller | any difference; fewer results read per root than the stated count (1,594 WH3 results on this machine: 647 in 482 job folders under `runs/twwarhammer3/battle/`, 947 in older roots) |
| K8 fixed values | `pack_sha256()`, the agent hash, the graph library digest and the initiation checker's hash; the 19 controller-file digests computed with the scenario config their jobs use; the five prompt snapshots and each prompt file's sha256; the 118 resolved scenario entries; `--help` of every command; `git diff --stat` for `mod/` and the five pinned Spire files; the folder and rules each caller passes to `conflicting_games`; the register's bytes at head start with its bytes at base; 0 deleted lines in every `log.md`; `stats.summary` equal; the key set of `ALIASES` equal across P5 | any difference, except a value the phase's card lists beforehand as changing, which the report quotes old and new |
| K9 test setup | `harness()` for every saved manifest; after the second yes also the set of files the presentation list matches, base against head through the table | a changed fingerprint; a file that gained or lost presentation status unlisted |
| K10 stale patches | each `monkeypatch.setattr(module, name)` whose module no longer uses the name | a count above the base |

**Why.** K3 and K4 let the owner approve a move from a table and a rerun instead of reading each
edit; the time that takes was not measured. `scripts/check.py` already treats a line moved verbatim
as unchanged (`scripts/check.py:160-174`); K3 and K4 extend that to a move that renames a path. No
outside reference was found for a table-driven move tool or for statement accounting, so both follow
that function only. The pattern of loading old and new code and comparing what they do is
`runs/gap-plan-20261031/open-robot-skills/tests/test_promotion_is_behaviour_preserving.py:36-119`
(`752dfbd`). That test loads one self-contained script with `git show` and skips when the old
revision is missing; K6 has to build about 81 classes that import the whole package, in one process
per worktree, and must fail where that test skips. Two precedents here: the 2026-10-23 test move
compared 1,412 collected cases ([testing.md](testing.md), "Initial cleanup"), and
`runs/terminal-bench-review-20261115/impl/recount_C.py` recounted 1,881 saved results with 0
differences.

**Cost.** The scripts change no tracked file. The agreed entry of J3 option (a) is an edit to
`docs/agreed-checks.md`, and this page does not say which merge carries it (Limits). The tool and
scripts are new code that needs its own planted wrong versions; their size was not estimated. A
plants run took 17 minutes for 408 plants on 2026-11-06 with other jobs running
(`docs/workflow.md:396-399`), and each phase needs at least one; a file filter for that replay would
be its own card, because 45 plants name `scripts/check.py`. K6 has thin evidence for the four
2026-11-08 battles, whose register rows are all `hold`, so their witnesses are replayed on test
fixtures only. K6 may be unstable for team controllers, which use threads and a clock
(`battle/team.py:150-155`); a controller whose base-against-base run differs is reported as not
covered. K6 is untracked, so after the restructure nothing replays a controller edit unless the
replay is later kept as a test. K7 covers this machine's evidence only.

**Check.** Each script fails on its planted wrong version: an extra edit inside a moved function
(K4), a test that turns into a skip (K5), a changed order in one witness (K6), a changed label in
one reader and a registry that maps an alias but no current entry string (K7), a rewritten register
row (K8), a dropped old presentation prefix (K9), a test that patches a name its module no longer
uses (K10, the case C4 names). No planted wrong version is named on this page for K3 or for the move
tool.

JUDGEMENT: Verification method — Claude, 2026-11-15, the K checks built for a phase are proposed as
the agreed check "restructure: offline equality". Without an agreed method every phase reports
unverified. Each "passed" statement about K checks in a phase report rests on it.

- Question (J3): which repeatable offline check, if any, may a phase report cite?
- Options: (a) the K checks enter [agreed-checks.md](agreed-checks.md) as one entry, with the sha256
  of each script, once each has failed on its planted wrong version; K6, K3 and the table part of K9
  are built later than the rest (C0), so a report names the checks that ran for its phase, the
  controllers K6 did not cover and the tests that skipped as not checked (recommended); (b) no
  agreed method.
- Today: no method exists, so by the hard rule every restructure claim is unverified.
- (a) lets a phase report "passed the K checks built so far at revision X", which says nothing about
  live play and, for P1 to P4, nothing about replayed decisions. (b) changes no work; every report
  carries the word "unverified" and the owner judges from counts.
- Best case for (b): the checks are written by the same agent that makes the moves, they live under
  ignored `runs/` while the agreed-checks page is permanent, and agreeing to them before seeing one
  run may give them more weight than they have earned.

JUDGEMENT: Batch approvals — Claude, 2026-11-15, the owner approves a phase's path-only edits as one
batch, on a table and a script's count of the edits that only rewrite a mapped path. Item-by-item
review is the alternative. About 286 plants, 102 references and 131 test files rest on it.

- Question (J4): how does the owner approve several hundred edits that only rewrite a path?
- Options: (a) one batch per phase: a script writes the full list to a file, counts the edits that
  equal a removed line after the table is applied, and lists every other edit in full (recommended);
  (b) item by item from the gate's output.
- Today: the gate lists every changed plant and agreed file and the first three marker and assert
  lines. Batches of 5, 11 and 23 path-only edits were approved on 2026-11-14 and 2026-11-15
  ([owner-direction.md](owner-direction.md)). What the gate lists for an agreed file is itself a
  marked rule: this option rests on JUDGEMENT? `scripts/check.py` Agreed-check edits.
- (a) needs no change to `scripts/check.py`. The first batches are small: 19 plant `file` values and
  3 plant texts in P2 and P3. (b) makes P5 several hundred separate approvals.
- Best case for (b): a batch of 286 is twelve times the largest batch approved so far, and the
  count comes from a new tool.

### C1. Path lists that raise when they match nothing (P1)

**Today.** Section "What is wrong today", last item of the first group. Also: `check.NO_MARKER` and
`check.SNAPSHOTS` are path patterns that match nothing after a move, with no message
(`scripts/check.py:110-115`); `.claude/workflows/wh3-version-review.js` names 15 repository paths
that no test reads; two browser check programs hold Python import lines that no test runs
(`tests/twwarhammer3/graph/check_wh3_graph_view.cjs:46`, `check_wh3_graph_goal_view.cjs:24`), the
first of them the command of an agreed check (`docs/agreed-checks.md:161-163`); the order vocabulary
is written by hand in Python and in Lua (`protocol.py:124`, `twwarhammer3_battle.lua:27`) with no
check between the copies; a reference line names a file and a marker, and the gate checks only that
the file holds some marker (`scripts/check.py:585-587`).

**Change.** Tests, about ten lines in `src/gameai/provenance.py`, and a mark on each game-starting
command in `src/twwarhammer3/__main__.py`:

- `source_fingerprints` and `committed_revision` raise when a scope path does not exist.
- Every glob, prefix and path constant used as a guard matches at least one tracked file:
  `check.SNAPSHOTS`, `check.NO_MARKER`, the scope tuples, the Stop hook's checker names, the hook
  script paths in both tools' settings, and each constant that names a file run or copied (`AGENT`,
  `RUNNER`, the two `multiplayer_*.js` agents, `manual_capture.py`, the three `windows_*.py`,
  `MOD_SOURCE`, the asset folders). The readings glob must find at least four modules. The
  presentation list gets this test in P2, when it is split in two (C3).
- Every sub-package directory and every config path constant lies inside the source scope.
- The commands `__main__.py` marks as starting a game equal the Stop hook's `GAME_COMMANDS`, in the
  way `tests/test_hooks.py:597` already compares the live-checker list. Each dotted key of
  `GAME_COMMANDS` (`twwarhammer3.battle.manual_demo` today) resolves with
  `importlib.util.find_spec` and its module accepts each listed word.
- Every repository path named in `.claude/`, `.codex/` and `.agents/` text exists, and every
  `twwarhammer3.x.y` or `spire.x.y` module named in a tracked `.py`, `.cjs`, `.js` or settings file
  under `tests/`, `scripts/` and those folders resolves, recorded names aside.
- Every `tests/`, `src/` or `scripts/` path named in a scenario entry exists.
- Each "rests on" reference names a marker that exists, by name, in the file it names.
- `protocol.BEHAVIOURS` equals the Lua table of the same name, and the order types the Lua
  dispatches cover `ORDER_TYPES`.

**Why.** Harbor's hand-kept tree lists three folders that do not exist
(`refs/harbor/AGENTS.md:43-139`, `ec6aeab`), and 65 lines in 22 other files spell the four file
names its paths class defines, some of them job-folder files for which Harbor has no such class
(harbor research note). Transformers runs its repository rules from one list
(`refs/transformers/Makefile:13-38`, `cf13eb9`) and tests eight of the 22 with temporary
repositories (`tests/repo_utils/test_check_repo.py` and seven more).

**Cost.** About twelve short tests, each with a plant. 7 plants name `provenance.py`, and the file
is in both games' scopes; 4 plants name `__main__.py`. P1 therefore lands while no job of either
game runs, and it starts a new test setup for every later WH3 battle (J7).
`tests/gameai/test_provenance.py:20` passes a missing path today and expects it skipped; under J9
(a) that call changes and a raises test is added, and its assert line stays.

**Check.** Each test fails on its planted violation: a scope path that does not exist, a glob that
matches nothing, a command the hook does not list, a hook key left at an old module path, a
one-byte Lua edit, a reference to a marker name its file does not hold. K1, K2.

JUDGEMENT?: Missing scope path stops a job — Claude, 2026-11-15, source_fingerprints and
committed_revision raise on a scope path that does not exist. Today such a path matches nothing and
passes. The scope tests and Spire's first-combat tools, which call the same functions, rest on it.

- Question (J9): should a job refuse to start when a path in its source scope does not exist?
- Options: (a) raise (recommended); (b) keep passing.
- Today: `git status --porcelain -- <missing path>` exits 0 with no output, so a moved folder leaves
  the dirty check and every fingerprint with no error.
- (a) is a new refusal in code both games use; a mistyped scope stops a job at start. (b) leaves the
  move relying on the scope test alone.
- Best case for (b): `provenance.py` has not changed since 2026-10-13, and two byte-pinned Spire
  files import it; their bytes do not change with this edit, but any edit there deserves a reason.

JUDGEMENT?: Pinned hashes — Claude, 2026-11-16, no tracked file of pinned hashes is added; K8
compares the pack, agent, graph library and initiation checker hashes at each phase. A tracked file
would show each later change to the owner. What a stale saved value can pass unseen rests on it.

- Question (J10): should a tracked file hold the content hashes that saved evidence is compared
  with, so that a change to one is shown?
- Options: (a) no file; K8 compares the four values during the restructure and each phase report
  quotes old and new (recommended); (b) a file outside the agreed directory, whose change is one
  line in a report and no approval; (c) a file under `tests/twwarhammer3`, whose change is an edit
  to an agreed check's files and so needs a yes.
- Today: a changed pack or library hash shows only when a restore or a load is next run. No saved
  value on this machine equals today's pack hash or library digest (J26, J27).
- (a) adds nothing that outlives the restructure. (c) asks for a yes on every Lua edit and every
  edit to a graph library file: 30 commits since 2026-11-01 touch the files those four hashes cover,
  20 of them under `mod/`; the gate would show the file's name inside its list of changed agreed
  files, without the old and new values (`scripts/check.py:513-518`).
- Best case for (c): it is the only option in which a later commit that changes a pinned value
  cannot land unseen. Best case for (b): the same signal at no approval cost.

### C2. Controller names: one resolver, then declared names (P2 and P5a)

**Today.** The first two problems of "What is wrong today". `BUILTINS` holds five built-in names,
`MODEL_PROMPTS` four model names and `VERSIONS` five versions (`battle/controllers.py:26-30`,
`:40-41`); every other controller is named by its module path. A card's kind is `external` for such
a class (`battle/controllers.py:152-153`), and `stats.configuration` returns a value only for kinds
`composed` and `external` (`battle/stats.py:41-47`). 583 register rows belong to the nine names
that exist and all 583 have a blank `configuration`. 13 of the 19 files under
`configs/twwarhammer3/controllers/` hold 70 class-path strings, 11 distinct; the composition digest
is taken over the resolved file with those strings in it (`battle/configured.py:55-56`, `:228-229`).
The page's display names are keyed by 16 class paths (`battle/report_html.py:67-105`), and
`report_html.commander` compares the `class` of member cards with class-path keys
(`battle/report_html.py:256-259`). The summary keeps rows apart by scenario and case, policy and
configuration, model, effort, harness version or else source commit, mode and timing
(`battle/stats.py:152-176`). 191 of the 192 class-path rows have no harness version, so each commit
already starts a new summary line for them: the 16 `CentreSupport` rows are 14 lines today. What
the hash should cover is the open marker Witness hash, which the owner answered "Decide later" on
2026-11-15 ([owner-direction.md](owner-direction.md)); which rows pool is the open marker Summary
identity (Claude, 2026-11-05), which the owner has not been asked.

**Change.** A new root module `registry.py`, in two steps.

Step 1 (P2, needs no identity decision). `policy_parts` moves verbatim from
`battle/controllers.py:72-85`. `MODEL_POLICIES` (`:30`) becomes a literal set of the four model
names there, and a test asserts that it equals `set(MODEL_PROMPTS)`, because the prompt table holds
paths from `llm.py` and `commander.py` and cannot sit in a root module. The readers and
`local_team.py`, `configured.py` and `__main__.py` import the two names from `registry.py`. No
recorded name or key changes. The file hash on a card does change for the classes in
`local_team.py`, and for those in `support_timing.py` if its import of `SOURCES` follows to
`scope.py` (C3, J36).

Step 2 (P5a, after P4 and before the move; needs J1, J2, J8 and J32):

- `CONTROLLERS`: one row per class a job may name, with a declared name, an entry string
  (`module:Class`, imported only when a job builds it), a version and a kind. 84 classes pass
  `controller_class`'s test today (`decide`, `acknowledge` and `metadata`, own, inherited or
  assigned), 81 without the `Controller` protocol class and two private helpers; 40 of the 84 define
  `decide` themselves and 44 inherit it, `cannae:CentreSupport` among those. The list is drafted for
  the owner before the change (J8). The five entries of `VERSIONS` (`:40-41`) become the versions of
  their rows.
- `ALIASES`: each of the 26 old class-path strings that still import (15 in the register, on 60
  rows, and 11 in controller files) mapped to its declared name. The 24 register names without code
  get no table: the register test accepts a class path that no longer imports on a row dated before
  the registry lands.
- `controller_class` (`:135-145`) moves to `registry.py` and resolves a declared name, then an
  alias, then a `module:Class` outside `twwarhammer3`. A typed string that names a registered
  class, by alias or by entry, is recorded under the declared name. A class inside the package with
  no row is refused with a message that names the registry, so a trial controller needs a name and
  a version before its first job. `BUILTINS` stays in `controllers.py`, and `card` reads a
  controller's kind from its row.
- New jobs record the declared name as `policy`. The card keeps `class`, `source_file` and
  `source_sha256` and records the declared version. `configuration` stays blank for the nine names
  that exist and holds the declared version for names registered by this change.
- `stats`, `report`, `report_html`, `validate_config`, `suite.ARMS` and
  `benchmark_plans.controller_matches` read names through one function `registry.canonical`. The
  lookups at `report_html.py:256-259` use it too, so a card written after the move still gets its
  "Local rush" or "Central concentration" label. Display labels stay in `report_html.py`.
- The 13 controller files keep their strings as typed and resolve through `ALIASES`, so no
  composition digest should change; K8 compares the 19. `battle/support_timing.py` keeps building
  names from `__name__` (`:171`, `:177`); those strings are entries and are recorded under the
  declared name.

**Why.** Each module hides one design decision (Parnas 1972, `refs/principles/parnas-1972-cacm.txt`,
"The Criteria"); here the decision is where a controller's code lives. One literal table from a
declared name to an import string is Harbor's `refs/harbor/src/harbor/agents/factory.py:62-164`;
Harbor keeps the names a second time in an enum that disagrees with the table (49 against 47), so
ours stay in one table. Gymnasium also stores the module path as a value of the table
(`refs/gymnasium/gymnasium/envs/registration.py:72-115`, `:254`, `:533-546`); its registration by
`register()` calls is not copied. SWE-bench keeps several stored names for one implementation
(`refs/swe-bench/swebench/harness/log_parsers/python.py:275-289`). An alias from an old name to
current code has no precedent in the references read: Gymnasium registers 17 old ids whose entry
point only raises (`gymnasium/envs/__init__.py:195-376`), and PettingZoo refuses a removed name
with a message (`refs/pettingzoo/pettingzoo/utils/deprecated_module.py:20-48`). The 2026-11-15
Terminal-Bench comparison proposed the declared-name step
(`runs/terminal-bench-review-20261115/report.md:611-615`).

**Cost.** Step 1: import lines in eight modules; no plant sits on the moved lines. Step 2: one table
of about 81 rows that every new controller class adds to (a new battle of `camp.py`'s size adds 4
rows, one of `escalade.py`'s size 17), and edits in modules that carry plants: `outcome.py` 15 and
`budget.py` 1 (the 16 of `benchmark.py`, none of them in `profiles.py`), `report.py` 12, `stats.py`
6, `controllers.py` 3, `report_html.py` 2, `suite.py` 2, and the users of the moved names in
`play.py` (24 plants), `local_team.py` (17), `digest.py` (8), `configured.py` (4), `export.py` (4)
and `__main__.py` (4). Three tests in the agreed directory assert today's rule and change:
`tests/twwarhammer3/test_wh3_register_identity.py:43-46` (a class-path row carries its file hash)
and `:125-134` (two hashes of one class stay two controllers), and
`tests/twwarhammer3/test_wh3_controllers.py:29-37` (a `module:Class` string for a class in the
package gives kind `external` and a 64-hex hash). They are rewritten for a class outside the
package, where the hash rule stays, and new tests assert name and version for a registered class.
The agreed-check script `scripts/wh3_reserve_cells.py:43` builds its label from the text after the
colon of `policy`, and `tests/twwarhammer3/test_wh3_reserve_cells.py:88-98` asserts
`WingSupport <hash>`; both change. Those are changed assert lines and so "needs your yes" items.
`scripts/diagram_files.py:100-109` reads `VERSIONS` and `MODEL_PROMPTS` from `controllers.py` by
path and must follow, and one plant holds its `VERSIONS` line. Ten more test lines in seven files
reach `controller_class` or `VERSIONS` through `controllers.py`, five of them assert lines; they
keep working only while `controllers.py` still imports those names. A name can never be reused for
other behaviour. This change rests on JUDGEMENT? `src/twwarhammer3/battle/controllers.py` Witness
hash and rests on JUDGEMENT? `src/twwarhammer3/battle/stats.py` Summary identity; only the owner
removes or rewords those two markers.

**Check.** Step 1: the equality test for `MODEL_POLICIES`; K4, K5, K7, K10. Step 2, a registry
test: every entry imports and has `decide`, `acknowledge` and `metadata`; the class reached through
an alias is the same object as the class reached through its row; every `module:Class` string in
`configs/`, `tests/` and `docs/agreed-checks.md` is an alias, an entry or a class outside the
package; a class in the package with no row is refused. For all 857 register rows, the label each
reader shows is equal before and after. One job through the real loop with a fake mailbox, typed as
`twwarhammer3.battle.cannae:WingSupport`, records the declared name, version `v1` and a card built
by the loop; the same for `hold`, with a blank `configuration`. K6, K7 with its new-format jobs, K8
(the 19 digests). The plausible wrong versions: an alias that points at another existing class, a
version written into `configuration` for `hold`, and a `canonical` that knows aliases and declared
names but no current entry string.

JUDGEMENT: Controller identity — Claude, 2026-11-15, a controller is its declared name and version;
its file hash is recorded and not compared. Keeping the module path and hash renames every
class-path controller when its file moves. C7, C8 and the readers' labels and groups rest on it.

- Question (J1): what names a controller in a result, and so which results are the same
  controller's?
- Options: (a) the declared name and version (recommended); (b) the module path and the hash of the
  class's file, as today.
- Today: (b) for class-path policies, and the name alone for the nine built-in and model names. In
  the summary the source commit keeps rows apart as well for jobs with no harness version, which is
  191 of the 192 class-path rows, so a hash decides a summary line only for jobs named with `-vN-`.
- (a) lets a controller file move, gain a comment or lose a helper without a new name or a new
  `configuration`; it answers the two open markers named above. A class in the package then needs a
  registry row before a job can name it. (b) keeps a machine-made value; a move then renames every
  class-path controller, because the name is the module path, so P5 should not be made under (b).
- Best case for (b): a hash changes by itself when the file changes, and a version changes only when
  someone edits it. Under (a) a behaviour change with the version left alone is filed with the old
  behaviour unless K6 or a reviewer notices.

JUDGEMENT: Old and new rows — Claude, 2026-11-15, the alias table only labels old class-path rows;
they never pool with declared-name rows, and nine old names keep a blank configuration. Pooling
would need a new summary key and merge groups kept apart today. Every rate after P5a rests on it.

- Question (J2): should an old row named `twwarhammer3.battle.cannae:CentreSupport` and a new row
  named by its declared name be one line in `stats` and the report?
- Options: (a) no: same display label, separate lines (recommended); (b) pool only the pairs the
  owner approves one by one, from a list that shows every joined row, with declared-name rows keyed
  on the declared version in place of the source commit; (c) pool all, with the same new key.
- Today: the 16 `CentreSupport` rows are 14 summary lines, split by case and by source commit
  (`702ba10`, `d3ddc7b`, `932c0a4`); a battle played after any commit starts a new line whatever its
  file hash.
- (a) changes no existing group. (b) and (c) pool nothing unless `stats.conditions` changes too,
  which is a change to `JUDGEMENT?` Summary identity; (c) also rests on the 2026-11-14 cleanup's own
  statement that it changed no behaviour.
- Best case for (b): the 16 `CentreSupport` rows are the largest sample of a witness that still
  imports, and under (a) no later battle ever joins them. Best case for (c): one rule and no list
  to approve. Neither reference registry pools: both refuse an old name.

JUDGEMENT: Names — Claude, 2026-11-15, about 81 declared names of the form battle.role, one per
class a job may name. Another spelling changes the policy column of every later row, and a name is
never reused. The register's policy column and the alias table rest on it.

- Question (J8): how are the declared names spelled?
- Options: (a) `cannae.centre_support`, `evade` (recommended); (b) underscore names such as
  `cannae_centre_support`; (c) the owner's own list.
- Today: nine names exist; `policy_parts` splits a name only at `@`
  (`battle/controllers.py:72-85`), so a dot is allowed.
- Any option fixes the strings in every later register row.
- Best case for (b): a dotted name looks like a module path, which is the identity this change
  removes. Best case for (c): the owner reads these names in every table.

JUDGEMENT: Version bump rule — Claude, 2026-11-16, a newly registered name starts at v1 and its
version changes only when some observation gives other orders. A bump on any byte change of the
controller's file is the alternative. Which rows pool after a controller edit rests on it.

- Question (J32): when does a declared version change?
- Options: (a) when K6 shows other orders on some observation; the agent that changes a controller
  proposes the bump on its card (recommended); (b) on any byte change of the file that defines the
  class; (c) on any change to orders, timing or a model request body.
- Today: the five versions in `VERSIONS` are bumped by hand, with no written rule.
- (a) keeps a version stable across a move or a comment. (b) changes the version whenever the file's
  bytes change, as the hash does today. (c) is (a) with timing and request bodies added.
- Best case for (b): it needs no judgement and cannot be missed. Best case for (c): a prompt or
  timing change can change results while every order on a saved observation stays equal. Under (a)
  a missed bump has no check once K6's scripts are gone.

### C3. The source scope and the presentation list in one module (P2)

**Today.** `SOURCES`, `TRACK` and `EVALUATOR_VERSION` are in the job loop (`battle/play.py:87-90`);
seven files import the loop to read the tuple (`engine/worker.py:69`, `battle/checkpoint.py:33`,
`battle/rl.py:25`, `battle/manual_demo.py:21`, `battle/support_timing.py:16`, `__main__.py:328` and
`:513`, `scripts/wh3_queue.py:45`); three of them take other names from the loop too. Three live
checkers under `tests/twwarhammer3` read the tuple through `play` as well, and so does the pinned
saved checker of J25. The presentation list is in the page renderer (`battle/report_html.py:36-45`),
and one of its nine prefixes matches no tracked file. `battle/checkpoint.py:32` imports
`spire.engine.runtime` to pass Spire's folder and process names to `conflicting_games` (`:167`).

**Change.** `src/twwarhammer3/scope.py` takes `SOURCES`, `TRACK`, `EVALUATOR_VERSION` and the
presentation list with its marker, moved verbatim. The list becomes two tuples: live prefixes, each
of which must match a tracked file, and recorded-only prefixes, each of which must match none
(`configs/twwarhammer3/scenarios.json` today; after P5 the old `battle/` paths join it). A module
cut from a presentation file stays presentation; a module with any other parent counts toward the
test setup. `src/gameai/games.py` holds each game's Windows folder and conflict rules as data;
`battle/checkpoint.py` reads Spire's entry from it. Neither game's `engine/runtime.py` is edited: a
test asserts that each runtime's `WINDOWS_GAME_DIR` and `CONFLICTS` equal the entry.

**Why.** A decision that is likely to change gets one module (Parnas, Conclusion); here the
decision is which files count as the code that ran. The repository already keeps an old and a new
path side by side twice (`src/spire/fullrun/export.py:23-24`; the two scenario prefixes at
`battle/report_html.py:44-45`). No outside repository was read for a scope module.

**Cost.** One plant sits on the moved lines (`report_html.py:45`); 24 plants name `play.py`. 48 test
patches name `battle/play.py`, among them `source_fingerprints` and `committed_revision`. The marker
`JUDGEMENT?` Test setup moves with its lines; one reference names it at the old path, the last
sentence of this paragraph, and follows. Three items change status. The list itself leaves
`report_html.py`, a presentation file, here; `strength` leaves `digest.py` for `wording.py` and
`plan_report` leaves `report.py` for `benchmark_plans.py` in C4. An edit to any of the three then
starts a new test setup. `games.py` is a new file in both games' scopes. The three live checkers and
the pinned saved checker that read `play.SOURCES` keep running unedited only while `play.py` still
imports that name from `scope.py`; if it does not, the checkers' lines are edits to agreed checks'
files and the pinned checker stops at P2 (J25). The three new modules each need a Code map entry by
hand until P4 (C4, Docs). The list's membership rests on JUDGEMENT?
`src/twwarhammer3/battle/report_html.py` Test setup.

**Check.** K9; the fingerprint map of an unchanged tree is equal before and after, apart from the
new files; a fake-mailbox job's manifest has the same `source_files` keys plus those; K8 for the
folder and rules each caller passes to `conflicting_games`; K4, K10, K1, K2. R2 with its planted
cross-game import. The plausible wrong version: a folder string in `games.py` that differs from
Spire's, with which the guard sees no running game.

JUDGEMENT?: Presentation list — Claude, 2026-11-15, the list names the same files at their new
paths and keeps the nine old prefixes for old manifests; three items start counting. Listing all of
reports/ would stop export.py edits starting a new setup. Figure 1's groups rest on it.

- Question (J12): which files may change without starting a new test setup?
- Options: (a) the files the list covers today, at their paths of the day (recommended); (b) after
  the move, all of `reports/`.
- Today: nine prefixes; the marker at `battle/report_html.py:36-40` says `export.py` and
  `gameai/sft.py` still count.
- (a) keeps membership except the three status changes named under Cost. (b) removes `export.py`,
  `graph_view.py`, `exact_stats.py` and `statistics.py` from the test setup.
- Best case for (b): a folder prefix covers a new reader module with no edit, and a file list needs
  one for each new file.

JUDGEMENT?: Game process names in gameai — Claude, 2026-11-16, gameai/games.py holds both games'
install folders and process names as data. Each game keeping its own list, with checkpoint.py's
import of spire listed as a known break, is the alternative. The two-games guard rests on it.

- Question (J34): where does WH3's checkpoint code learn Spire's folder and process names?
- Options: (a) a data file in `gameai`, read by `battle/checkpoint.py` and compared with both
  runtimes by a test (recommended); (b) `battle/checkpoint.py:32` keeps its import of
  `spire.engine.runtime`, and R2 lists it as its one known break.
- Today: each game's runtime holds its own values (`src/spire/engine/runtime.py:16-24`,
  `engine/runtime.py:28`, `:40`), and `checkpoint.py` imports Spire's.
- (a) puts game-specific data into a package that `docs/development.md:11` describes as
  game-neutral, and adds a file to both source scopes. (b) changes nothing and leaves R2 with one
  exception for good.
- Best case for (b): the guard behind the hard rule "never run two game controllers at once" is
  not touched at all.

### C4. Shared facts leave the large modules and four cuts remove wrong-way imports, in place (P3)

**Today.** The third group of "What is wrong today". Also `battle/skills.py:20` imports `ARRIVED_M`
from `llm.py`, so the scripted skills executor loads the model policy file; seven witness modules
import `able` from the Cannae messaging module (controllers map, wrong-way edges 1 and 2). Eleven of
the 26 wrong-way imports come from four places: `benchmark.py` holds names that lower packages need
(`evaluate`, read by `stats`, `digest`, `export`, `report` and `play`, and the profile names and
limits, read by `controllers.py`, `configured.py` and `llm.py`: 8 imports); `exact_stats.py` takes
its statistics from `suite.py`; `report.py:18` imports `benchmark_plans`; `manual_demo.py:33`
imports `support_timing` for one constant. Four hashes cover whole files that such cuts touch. The
graph library hashes `skills.py` as its tactics and the loader refuses an artifact whose library
digest differs (`battle/graph_author.py:95-97`, `:139-141`). `recount` records the hash of `rl.py`
as `checker_sha256` (`battle/rl.py:1007`). A model team records the hash of `llm.py` as
`member_source_sha256` (`battle/team.py:494`). The graph author records the hash of
`graph_author.py` in its manifest (`:285`).

**Change.** Statements move verbatim into new modules. No existing file changes its path;
`benchmark.py` ends, because all of it is cut.

| Module after P3 | What lands there |
|---|---|
| `units.py` (new, root) | `battle/scripted.py:70-93` (`distance`, `nearest`, `find`, `forget_refused`); `battle/local_command.py:33-38` (`able` and its five-state set `OUT`, names unchanged); `battle/llm.py:47` (`ARRIVED_M`) |
| `wording.py` (new, root) | `battle/llm.py:131-133`, `:665-669`, `:694-730` (`short_type`, `describe_dropped`, `describe_orders`); `battle/commander.py:46`, `:79-89` (`REPORT_HEADER`, `describe_assignment`, `describe_plan`); `battle/digest.py:38-44` (`strength`) |
| `protocol.py` (stays) | gains `gate_breached` with its Breach rule marker from `battle/evidence_rules.py:53-62` |
| `battle/graph_artifact.py` (new) | `battle/graph_author.py:20-22`, `:30-40`, `:72-97`, `:115-124`, `:127-169` (the artifact versions, `DESCRIPTIONS`, `frozen_library`, `authority`, `read_bytes`, `load_artifact`, `previous_artifact`) |
| `battle/controllers.py` (stays) | gains `validate_config` from `battle/local_team.py:104-122` |
| `battle/profiles.py`, `battle/budget.py`, `battle/outcome.py` (new) | `battle/benchmark.py:14-32`, `:35-39`, `:221-240` (profile names, limits, `validate_config`); `:42-100` (`send_once`, `BattleBudget`, `suite_budget`); `:33-34`, `:103-218` (the outcome label, `evaluate`) |
| `battle/statistics.py` (new) | `battle/suite.py:368-448` (eight generic statistics functions) |
| `battle/benchmark_plans.py` (stays) | gains `plan_report` from `battle/report.py:526-547` |

Five edits are not verbatim moves, and K4 lists each: the late import at `protocol.py:301` becomes a
plain use; `report.collect` takes its plan rows from its caller in place of calling the plan reader
(`battle/report.py:295`); `manual_demo.py` holds its default scenario id itself, with a test that it
equals `support_timing.SCENARIO`; `configured.py` imports `graph_artifact` at the top, which ends
its late import at `:23`; `validate_config` loses its late import of `controllers`, while its import
of `configured.load` stays inside the function, because `configured.py` imports `controllers` at the
top (the pair R5 lists). Besides these, 30 source lines in nine files name a thing that P2 or P3
moves as `module.name` through the module it leaves, and at least 18 of them must change (12 are
`benchmark.<name>`). Inside the moved `validate_config` the names `declaration`, `LocalTeam` and
`controllers.controller_class` read differently in `controllers.py`. Each of these is an edit that
K4 lists too.

Three cuts of this page's first draft are dropped, because a compared or recorded hash would cover
less with no decision behind it. `SHOOTERS`, `CHARGERS`, `MOUNTED` and the two-state `OUT` stay in
`skills.py`, where the library digest covers them; they decide a unit's default skill and its
targets (`battle/skills.py:36-48`). `unit_geometry.py` therefore stays a module, because it needs
that `OUT`. `recount` stays in `rl.py`.

R3 lands here as a table from module name to package (section "The import rules"). The readings
rule's two lists change in the same commit: a readings module may then import `protocol`, `units`,
`battle.evidence_rules` and `battle.unit_geometry` and may load `battle.setup` and `battle.skills`
besides; `battle.scripted`, `battle.llm` and `battle.benchmark` leave the lists, and the planted
cases of `tests/test_repo_rules.py:190-229` follow.

Of the four cycles in `layers.txt`, one goes (`protocol` with `evidence_rules` and `setup`), one
shrinks from four modules to the pair R5 lists, and two stay listed (`rl` with `confirm`; Spire's).

**Why.** Break a cycle by moving the shared piece out (Martin 2000,
`refs/principles/martin-design-principles-2000.pdf`, pages 20 to 21). Classes that are not reused
together should not be grouped together (the same paper's Common Reuse Principle, page 17); Martin
notes that this pulls against grouping what changes together, which C7's co-change count is about.
Length alone is no reason to split (Ousterhout, `refs/principles/ouster-cs190-modularDesign.html`).
An interface file that imports almost nothing is `refs/smac/smac/env/multiagentenv.py` (`d6aab33`):
68 lines with no project import. That file is the case for option (b) of J11.

**Cost.**

- Bytes and hashes. Most controller files' import lines change here. `controllers.py` and
  `local_team.py` already changed in P2, and so did `support_timing.py` if its import of `SOURCES`
  followed to `scope.py` (J36). The graph library digest changes, because `skills.py` and the other
  library files change import lines. `member_source_sha256` and the graph author's `source_sha256`
  cover less (J31). `export.py:408-409` records the sha256 of `export.py` and of the whole file
  `report.py`; the second value changes for new exports when `plan_report` leaves, and no reader
  compares either.
- Plants. 18 sit on moved statements and get a new `file` value: `benchmark.py` 16,
  `graph_author.py` 1, `scripted.py` 1. One more holds the late import of `protocol.py:301` as its
  `old` text and needs new text. None sits on the lines moved from `digest.py`, `local_team.py`,
  `llm.py`, `commander.py` or `suite.py`. The plant `diagram-graph-ops-fact-unread` needs new text
  as well: its `old` text is `scripts/diagram_files.py:104`, which reads `DESCRIPTIONS` from
  `battle/graph_author.py` by path. That line, the plant and `tests/test_check_script.py:1002` and
  `:1048` follow at P3, or the graph view is flagged; the line builds its path from a `battle/`
  prefix (`:98`), so it changes again at P5.
- Markers. Five move with their statements: Breach rule to `protocol.py`; Suite limits and Initial
  model screen to `profiles.py`; Benchmark-outcome rows to `outcome.py`; Scenario tie-break to
  `statistics.py`. Five references that the gate checks name them at the old files and get the new
  path: `haengju-eval.md:198` (Breach rule), `benchmark-initial.md:50` and `benchmark.md:248`
  (`benchmark.py`), `benchmark.md:188` and `benchmark-implementation.md:544` (`battle/suite.py`);
  the last four change again at P5. Four more name the Breach rule in wording the gate's pattern
  does not match (`escalade-eval.md:562`, `haengju-eval.md:893`, `historical-evals.md:295`,
  `battle/llm.py:184`). The other four checked references to `evidence_rules.py` name Contact rule
  or Group membership and keep their path.
- Tests. 145 test lines in 27 files reach a name that P2 or P3 moves through its old module, 60 of
  them assert or raises lines, 28 of those in files `docs/agreed-checks.md` names. 95 of the 145 (34
  assert lines) must change whatever the old module still imports, because `benchmark.py` ends and
  `validate_config` and `plan_report` leave their modules; the other 50 keep working where the old
  module still imports the name. The cut of `benchmark.py` accounts for 85, 33 and 23 of them
  (`test_wh3_benchmark_outcome.py`, `test_wh3_mirror_benchmark.py`, `test_wh3_mirror_enemy_ai.py`).
  `from module import name` lines are not counted, so the 95 is a lower bound
  (`verify/file-map/check_test_lines.py`; the recount is in `recheck/numbers.md`).
- Docs. The Code map entry and one Markdown link for `benchmark.py`, and the code-page files that
  name it. P2 and P3 add eleven modules (`registry.py`, `scope.py` and `gameai/games.py`;
  `units.py`, `wording.py`, `layout.py`, `graph_artifact.py`, `profiles.py`, `budget.py`,
  `outcome.py` and `statistics.py`). Each needs a hand-written Code map entry, and a map box where
  no box covers its path, or the map view is flagged in the main checkout
  (`scripts/diagram_files.py:208-226`); P4 then replaces the hand-written entries.
- Status. `strength` and `plan_report` leave presentation files and start counting toward the test
  setup (C3).
- Checks. No decision replay covers P2 and P3, because K6 is built before P5a (C0). What stands
  between a changed controller and the merge is K4, the unit tests and the five prompt snapshots. K4
  does not look at import lines, and after P3 two different sets are named `OUT` (five states in
  `units.py`, two in `skills.py`), so a module that imports the other one passes K4 (Limits).

**Check.** K4 with the listed edits; K5; K7 for the cuts of `benchmark.py` and `report.py`; K8 (the
five prompt snapshots pass without `WH3_WRITE_PROMPTS`; the library digest and the recorded hashes
are quoted old and new); K10; K1; K2. R3 fails on a planted wrong-way import and on a module missing
from its table; R5 shows one cycle gone. A new test: every module that the five library files take a
constant from is a library source or is listed by name in that test. The wrong version K10 must
catch: a test that patches `play.strength` after the loop stopped using that name.

JUDGEMENT: Provider rules stay in the protocol — Claude, 2026-11-16, policy_call, account_stop and
is_forfeit stay in protocol.py, where commit a69af01 put them on 2026-11-14. Moving them to
controller_call.py would let R3 say the protocol imports no model code. R3's root row rests on it.

- Question (J11): do the account-limit rules and `policy_call` stay in `protocol.py`?
- Options: (a) yes; `protocol.py` keeps its imports of two exception classes from `gameai.ledger`
  and `gameai.llm`, which R3 allows for every package (recommended); (b) move
  `protocol.py:53-113` to a new `controller_call.py`.
- Today: `protocol.py` holds four concepts. Loading it took 30 to 99 ms in the runs made for this
  page, most of it the model API module.
- (a) changes nothing. (b) partly reverses a placement the owner approved on 2026-11-14 ("Approve
  all", "Merge and push all"); three markers leave `protocol.py` with those lines (Account-limit
  markers, Operator errors, Forfeit split), four reference lines that name `protocol.py` for them
  change at P3 and again at P5 (`battle/benchmark.py:149-150`, `battle/cannae.py:47`,
  `battle/lines.py:129`, `protocol.py:55`), and two plants get a new `file` value.
- Best case for (b): an interface file that imports no model code can be read and loaded alone, and
  "the protocol imports nothing but the standard library" is a rule a test can state in one line.
  This page's first draft recommended (b); the overengineering check's case against it is the
  measured load time of 0.1 s or less and the owner's approval of 2026-11-14.

JUDGEMENT?: Controller files before identity — Claude, 2026-11-16, P2 and P3 change import lines in
most of the 20 controller files before J1 is answered, so their cards' file hashes change. Waiting
for J1 is the alternative. Three evade rows whose hash still matches today's file rest on it.

- Question (J36): may P2 and P3 change import lines in controller files while what a controller's
  hash means is still open?
- Options: (a) yes (recommended); (b) P3 waits for J1.
- Today: 19 register rows carry a file hash. 16 hold a hash `cannae.py` no longer has; 3 hold
  `6dce31c5540e`, which `evade.py` still has. Jobs with no harness version are kept apart by source
  commit as well, so a later job starts a new summary line with or without a hash change. P2 already
  changes `controllers.py` and `local_team.py` (C2, step 1), and P3 most of the other 18 files. On
  2026-11-14 the owner first answered "Team files only" for a cleanup, with the other controller
  files left to wait for a version bump, and then "Everything now" for that round's findings
  ([owner-direction.md](owner-direction.md)). P2 and P3 hold no version bump.
- (a) lets P1 to P4 proceed while J1, J2 and J8 stay open, as the owner left them on 2026-11-15.
  After P3 no register row's hash matches a current file. (b) keeps `evade.py`'s bytes and blocks
  the cuts of `units.py` and `wording.py`, which most controller files import from.
- Best case for (b): the witness-hash question was deferred one day before this page, and (a)
  changes the bytes that question is about before it is answered.

JUDGEMENT?: Recorded hashes after extraction — Claude, 2026-11-16, statements leave scripted.py,
llm.py, commander.py, local_team.py, graph_author.py and report.py, whose hash a card or manifest
records. Leaving them, or hashing the new modules too, is the alternative. Card hashes rest on it.

- Question (J31): may statements leave a file whose own hash a card or a manifest records?
- Options: (a) yes; each phase report names the recorded hashes that cover less (recommended);
  (b) leave those statements where they are and list the five reader imports of `llm.py` and
  `commander.py` in R3 by name; (c) cut them and record the hashes of `units.py`, `wording.py` and
  `graph_artifact.py` in the card or manifest as well.
- Today: `card` records the hash of the file that defines the class, for every controller
  (`battle/controllers.py:149-159`); a model team also records `llm.py`'s hash and the graph author
  its own file's. 15 of the 20 importers of `scripted.py` take only helpers from it, so their cards
  do not cover `distance` today. One reader compares the card hash: the HTML report refuses a group
  whose trials of one controller differ in it (`battle/report_html.py:379-386`). A group's signature
  holds the source revision (`battle/report.py:316`), so trials played before and after P3 are in
  different groups. `stats.configuration` reads the card hash for class-path policies
  (`battle/stats.py:46`).
- Under (a) the cards of the three classes in `scripted.py` no longer cover `distance`, `nearest`,
  `find` and `forget_refused`, an edit to `describe_orders` no longer changes
  `member_source_sha256`, the cards of the seven classes in `local_team.py` no longer cover
  `validate_config`, and `measures_sha256` no longer covers `plan_report`; the five prompt snapshots
  still change when wording reaches a prompt. (b) keeps five wrong-way imports and the late import
  in `configured.py`. (c) changes what a new card records and is one answer to the open marker
  Witness hash, which the owner deferred on 2026-11-15.
- Best case for (b): no recorded value changes meaning before the owner has said what a card hash
  should cover. Best case for (c): each card keeps covering the code it covers today.
- The hash a loader does compare, the graph library digest, keeps its cover: the four constants it
  would have lost stay in `skills.py`. This question rests on JUDGEMENT?
  `src/twwarhammer3/battle/controllers.py` Witness hash.

JUDGEMENT?: Root modules before the move — Claude, 2026-11-16, registry.py, scope.py, units.py and
wording.py are created at the package root in P2 and P3, before J13 is asked. Keeping new modules
in battle/ until the move is the alternative. The stop at P4 and the tree it leaves rest on it.

- Question (J35): are the four new root modules created before the package set is decided?
- Options: (a) yes, beside `protocol.py`, which is at the root today (recommended); (b) every new
  module is created in `battle/` and P5 moves it.
- Today: one root module, `protocol.py`.
- (a) fixes one part of J13 early: every option of J13 keeps these four. The other new modules of
  P3 (`layout.py`, `graph_artifact.py`, `profiles.py`, `budget.py`, `outcome.py`, `statistics.py`)
  are created in `battle/`, so no sub-package exists before J13. At the stop after P4 the tree is
  five root modules, `engine/` and a flat `battle/` of 65 Python files. (b) costs a second `file`
  edit for the plants on those statements.
- Best case for (b): the owner decides the whole layout in one answer.

JUDGEMENT?: Import rule checker — Claude, 2026-11-16, R2, R3 and R5 are syntax-tree tests in
tests/test_repo_rules.py, as R1 and R4 are today. Import Linter contracts as a development
dependency are the alternative. Whether a plant can target a rule rests on it.

- Question (J33): how are the import rules checked?
- Options: (a) plain tests that walk the syntax tree (recommended); (b) Import Linter, with the
  table as contracts in a config file.
- Today: R1 and R4 are such tests. The research note on architecture principles left this choice
  to the owner.
- (a) keeps one mechanism and lets a plant target each rule. (b) adds a development dependency and
  a second config; whether Import Linter counts function-level imports was not established, and
  three of the four cycles here exist only through those.
- Best case for (b): a maintained tool with layer and cycle contracts, in place of a table and
  graph walk that this repository must keep correct itself.

### C5. One module names the files of a job folder (P3)

**Today.** The first item of the group "No module describes a job's record".
`runs/README.md:76-93` describes the job folder in prose.

**Change.** A new module `battle/layout.py`, which P5 moves to `records/layout.py`, gives every file
name of a job folder and an episode folder as a function; the literal lines become calls: 77 lines
in 19 files at P3, and `battle/graph_initiation.py:68` at P5, because that file compares its own
hash (`:167`) and is byte-identical to the revision its agreed check passed at.
`engine/manual_capture.py:72` keeps its literal: the file stays in `engine`, which may import root
modules only (R3), and Windows Python runs it from the source tree with `gameai.windows` as its only
project import. The module also takes `RECORDER_VERSION` (`battle/capture.py:18`), which `replay.py`
imports from the capture module today. No saved file is renamed and no key changes. Readers keep
their own loading code. A description of the result keys and trace kinds is left to the reader that
would load through it (J29).

**Why.** One module names a record folder's files: Harbor
`refs/harbor/src/harbor/models/trial/paths.py`. Functions and a test that forbids the literal,
because constants alone leak: 65 lines elsewhere in Harbor spell its file names, and SWE-bench
builds the same path by hand beside its constants
(`refs/swe-bench/swebench/harness/run_evaluation.py:254`, `:588-594`, `02e7a74`). In both record
references a description holds because one loader goes through it and refuses a version it does not
know (`refs/inspect_ai/src/inspect_ai/log/_file.py:530-647`, `59c1340`;
`refs/harbor/src/harbor/models/README.md`); a typed description that no reader loads through would
be one more hand-kept list, in a repository with no type checker (`pyproject.toml:59-60`).

**Cost.** Mechanical edits on 77 lines; one plant holds such a literal in its `old` text
(`export-excludes-teams-again`) and needs new text. `schema_version` stays unread. One of the 19
files defines a controller class (`replay_schedule.py`), and two have their own bytes recorded
(`graph_author.py:285`, `export.py:408`); their recorded hashes change, as in C4. This change
carries no marker of its own: it changes no recorded key, and the one file whose bytes a loader
compares is left until P5.

**Check.** A test that the three literals occur only in `layout.py`, with
`engine/manual_capture.py:72` listed for good and `graph_initiation.py:68` listed until P5. K7; K5;
K1; K2. The 77 lines are edits inside function bodies, so K4 lists them as edits and does not
account for them; the literal test and K7 cover them. K7 reads saved jobs and runs no writer at P3,
so a writer outside the play loop that calls the function for another file
(`battle/checkpoint.py:237`, `engine/multiplayer_probe.py:63`) is left to its own unit tests. The
plausible wrong version: a function that returns `"results.json"`, which K7 catches as a job no
reader finds.

### C6. A generated Code map and one guidance page (P4)

**Today.** The last group of "What is wrong today". The Code map's format is Claude Code's
undecided call of 2026-11-01 (`JUDGEMENT?` One file per line,
`docs/twwarhammer3/README.md:205-207`); `scripts/diagram_files.py` reads the map and writes the
tracked `docs/how-code-works-files.js`, and nothing compares that file with a fresh run. All 132
modules under `src/` have a docstring; for 29 the first line runs on to the next (17 in `battle/`).

**Change.** `scripts/diagram_files.py` builds the entries of the 100 Python modules from the first
sentence of each module docstring, joined across lines, and a test compares the tracked output with
a fresh run. P4 edits no file under `src/`. The other 31 entries (Lua files, agents, asset folders,
config files, the commit hook) stay by hand. The file list in `docs/spire/AGENTS.md:14-95` and the
helper table in `tests/README.md:103-130` are built the same way. A new page
`docs/twwarhammer3/code.md`, at most 120 lines, holds the package table in the words the rule tests
print, the recipes of "Where a new thing goes", the files whose bytes are evidence, the rule that a
module's tests are in `test_wh3_<module>.py` with the ten modules that have no such file, one
command that lists the battle Lua's functions with line numbers, and this table of checks:

| You changed | Run | Time in saved logs |
|---|---|---|
| one module | `uv run --locked pytest -q` with that module's test file | about 1 s |
| a root module, `setup.py`, `play.py` or `gameai` | `uv run --locked pytest -q tests/twwarhammer3` | 44 to 47 s |
| anything, before a commit | `uv run --locked python scripts/check.py` | 116 to 153 s |

The root `AGENTS.md` gets one route line to the page. On the reading route `code.md` takes the
place of the Code map (223 lines) and `tests/README.md` (136), which stay as reference: 955 lines
become about 720. This lands before the move, so the generated entries need no hand edit at P5; at
P5 each new package `__init__.py` gets a docstring that states the package's purpose.

**Why.** A tracked generated file is compared with its generator: the graph-as-policy clone's
`tests/agent_skill/test_cli_reference_fresh.py` (`71549e1`) does it in a test, and
`refs/transformers/utils/check_dummies.py:195-256` in a script that has no test of its own and
passes one kind of mismatch (`:244-246`), so ours carries a planted stale line. A focused check is
named where the agent works (`refs/inspect_ai/AGENTS.md`, "Gated tests"). Two papers bear on the
page (agent-friendly research note, 3.1, 3.2 and 3.4). Gloaguen et al. found that agents use the
commands a guidance file names and that a file overview in it did not help agents find files
(section 4.3; read through a summarising tool, no saved copy). McMillan found no gain in
rule-following from nested instruction files (section 4.1; saved text). The package table is kept
on the page because it states the import rule; a test compares it with the rule's own table.

**Cost.** 22 plants name `diagram_files.py`. The Code map is the owner's page for reading the code,
and its wording becomes the docstrings'. One line in the root `AGENTS.md`, the owner's rule file.
This change rests on JUDGEMENT? `docs/twwarhammer3/README.md` One file per line.

**Check.** The freshness test with a planted stale line; every module under `src/` has a docstring
whose first sentence is not empty; a test compares `code.md`'s package table with the module table
of R3; `tests/test_doc_links.py`.

JUDGEMENT?: Code map generated — Claude, 2026-11-15, the 100 hand-kept entries for Python modules
are replaced by a list built from module docstrings and checked for freshness. Keeping the list by
hand costs 69 entry edits at the move. The owner's reading page and 22 plants rest on it.

- Question (J19): should the Code map, the Spire file list in `docs/spire/AGENTS.md` and the helper
  table in `tests/README.md` be written by hand or built from the module docstrings?
- Options: (a) built and tested for freshness (recommended); (b) kept by hand.
- Today: by hand, one file per line; only a missing entry is flagged.
- (a) makes each docstring's first sentence the one description of a Python file. (b) keeps today's
  format and costs 69 entry edits at P5 (66 files and 2 folders that move, 1 file that ends at P3).
- Best case for (b): the hand-written entries are often longer and clearer than a docstring's first
  sentence, and the code-page plan the owner answered on 2026-11-01 keeps the README list as the
  one home for "which file does what" (`docs/how-code-works-plan.md:156-157`).

JUDGEMENT: Guidance page — Claude, 2026-11-15, one page docs/twwarhammer3/code.md holds the checks,
rules and recipes. Nested AGENTS.md files beside the code would sit inside the play scope, hashed
into every job. The reading route for a WH3 change rests on it.

- Question (J20): where does the guidance for working in the WH3 code live?
- Options: (a) one page under `docs/`, routed from the root `AGENTS.md` (recommended); (b)
  `AGENTS.md` files with one-line `CLAUDE.md` imports under `src/twwarhammer3/`, `src/spire/` and
  `tests/`.
- Today: `docs/development.md`, the Code map and `tests/README.md`.
- (a) keeps guidance out of every source scope. (b) loads by itself in Claude Code when a file in
  the folder is read; every guidance edit is then a source change that stops a running job, unless
  provenance skips those files, and that skip makes Spire's language-training audit disagree with
  its Git listing (`scripts/audit_language_training.py:59-71`, `:343`).
- Best case for (b): guidance beside the code is read at the moment it applies, and (a) depends on
  the agent following a route.

### C7. The mechanical move (P5a and P5)

**Today.** `battle/` holds 60 Python files and two asset folders; `engine/` also holds the
multiplayer runner (58% of its lines) and the checkpoint agent (engine map). 387 import lines in 182
files name `twwarhammer3.battle` (`grep -rnE`). After P3 no import breaks the table, so the move
itself removes no wrong-way import.

**Change.** Two merges in one window. P5a is the second step of C2: it changes what a new register
row records and is a commit of its own. P5 is one commit made by the move tool from the reviewed
table. In it 74 files tracked today (66 from `battle/`, 8 from `engine/`) and the six modules that
P3 created in `battle/` change path (the file map lists each), and `battle/__init__.py` is deleted.
The tool rewrites what C0 lists, and with it R3's table (module names become folder names), R4's two
lists, `check.NO_MARKER`, the Stop hook's module key, the new presentation tuple and the import
lines inside the two `.cjs` programs. Each new package gets an `__init__.py` whose docstring states
its purpose. A battles test lists the folders under `battles/` and names a missing part. Two lines
are edited by hand and listed for K4: the path arithmetic that crosses packages becomes a sibling
lookup (`battle/checkpoint.py:40-42`), and the last job-file literal becomes a `layout` call
(`battle/graph_initiation.py:68`). No file is split and no other function body under `src/` changes.
One more hand edit is in the tests: R4's walk globs `battle/` for readings modules and seeds the
package files `""` and `"battle"` (`tests/test_repo_rules.py:117-120`), so its logic and the trees
of its planted cases (`:190-229`) change when a readings module sits in `battles/<battle>/`. These
hand edits, the new `__init__.py` docstrings, the battles test and the rewritten plant texts are in
the commit that K3 must reproduce from the table alone; whether they become a second commit or
inputs of the tool is not decided (Limits). After the merge, on the owner's yes, in the main
checkout: `python -m twwarhammer3 doctor`, one `launch` and one `hold` battle at 1x on a scenario
named on P5's card, outside the benchmark job list. The battle appends a register row
(`battle/play.py:193`), which is committed there with its log entry before anything else lands. The
two graph-view browser programs are run on their saved battles; they need no game.

**Why.** The sources that were read put the feature or domain at the top level and the layers
inside it (Fowler, `refs/principles/fowler-pdd-layering.html:335-344`). This plan does the reverse,
roles first with the battle folders inside one role, because the history does not show a battle as
the unit of change. Counted per battle folder, 11 of 46 commits touch no other `battle/` module
(camp 0 of 6, lines 3 of 10, siege defence 0 of 7, siege attack 1 of 8, Cannae 4 of 10, support
timing 3 of 5), and 25 of the 344 commits touch any battle folder's module, against 181 that touch
`play`, `llm`, `report_html` or `setup` (`verify/overengineering/cochange_plan.py`). The same
history does not show the ten packages as units of change either: 194 of the 344 commits touch one
module, and of the 150 that touch two or more, 44 stay inside one package and 106 cross. The
packages therefore give names and an import rule a folder can state; they are not shown to keep
changes local. One folder per evaluation: Inspect Evals has four fixed entries per folder
(`refs/inspect_evals/src/inspect_evals/gpqa/`, `3034895`), of which we take the code; PettingZoo is
a folder whose contents vary (`refs/pettingzoo/pettingzoo/classic/tictactoe/`, `e767786`). No
central table of battles: Inspect Evals replaced its central listing by a file in each folder
(`refs/inspect_evals/adr/0001-eval-metadata-location.md`) and SWE-bench 5.0.0 did the same for task
metadata (`refs/swe-bench/CHANGELOG.md:34`), so the battles test reads the folders. One function
reports a unit's missing part: `refs/swe-bench/swebench/task/checks.py:72-158` (`02e7a74`). One
mapped commit: nobody outside imports our modules, so no moved name needs a shim and every caller
changes in the same commit; Inspect keeps about 100 shims for its outside importers (inspect-ai
research note).

Two daily routes, counted by the overengineering check before and after the move, as the
observable for the second yes:

| Route | Today | After P5 |
|---|---|---|
| Add an evaluation battle with a witness, shared values and readings | 7 new files; 2 edited (three Code map lines by hand, the code-page list by its generator); 4 folders; no row in a source table | 8 new files (one more `__init__.py`); 3 edited (`registry.py`, the two generated lists by one run); 5 folders counting the package root; one registry row per class a job may name (4 for a battle of `camp.py`'s size, 17 for `escalade.py`'s) |
| Change one result key (`engine_ending`) | 9 source files in 1 folder; 21 test files | the same 9 source files in 7 folders; the same 21 test files |

**Cost.** This step costs more than any other in the plan.

- Plants: about 286 `file` values (275 under `battle/` after P3, 11 on the eight files that leave
  `engine/`). Six more hold a moving module path inside their `old` or `new` text and are text
  edits, which the tool prints in full: `stop-hook-misses-manual-demo-record`,
  `camp-readings-import-the-witness-again`, `camp-readings-import-the-witness-relatively`,
  `lines-facts-import-a-witness-module`, `protocol-imports-a-witness-in-a-function` and
  `battle-package-file-imports-a-witness`. The last is planted in `battle/__init__.py`, which is
  deleted, and is rewritten for `battles/__init__.py`.
- Marker references: 102 name a path the move changes. The gate's pattern matches 69 of them, 58
  with a path from the root and 11 tail references of the form `battle/x.py` (one of them in
  `docs/agreed-checks.md:127-128`). It does not match the other 33: 14 are written "Rests on" with a
  capital, 5 "resting on", and 14 are joined by "and", sit in a table or bracket, or are wrapped
  onto an indented line. A tool or test that finds references with the gate's pattern leaves those
  33 at a path that no longer exists, and no check fails. 82 lines outside the logs hold the word
  JUDGEMENT and a moving path, and the gate lists each of them that is edited
  (`scripts/check.py:523-526`). This page holds four more references to moving files, which follow
  too.
- Agreed files: 219 import lines in 131 files of the agreed directory (129 Python files and the two
  `.cjs` programs) and one in `scripts/wh3_reserve_cells.py:18`, shown as one item. At least 55 more
  lines there, in 38 files, hold a moving module path or file path outside an import line (a regex
  count).
- Docs: 67 Markdown links into moved code; 215 code-page citations refreshed (P8); every code-page
  example shows "code changed since" until a battle is played at the new revision
  (`scripts/diagram_examples.py:309-321`).
- Hashes: every card hash, the graph library digest, `exporter_sha256` and `measures_sha256` change
  again, and the initiation checker's own hash changes for the first time (three saved proof
  records hold today's `827d50a466f0`; none loads today, J26).
- Every later job is a new test setup (J7). No live agreed check has a pass at the new revision
  (J24).
- Two parked branches, `tower-owner-20261114` and `wh3-human-opponent`, touch files that move. This
  plan does not touch them; applying the table to a branch is asked when the owner resumes it.
- The four commands run by module path get new paths (J22). 23 modules repeat their folder's name,
  and the package holds 19 `__init__.py` files where it holds 3 today.

**Check.** K3; K4 for the hand edits; K1 in its four runs; K2 with only `file` values differing,
except the six listed plants; K5; K6; K7; K8; K9; the battles test and R4 with their planted cases;
R3 fails on a planted new break. Then the live launch, the `hold` battle and the two browser
programs, which are evidence and no agreed check.

JUDGEMENT: Stop point — Claude, 2026-11-15, P0 to P4 stand alone and leave battle/ flat (no file
moves; benchmark.py is cut in place); the move is a second yes after their report. Approving all
phases now, or stopping for good at P4, are the alternatives. What work comes next rests on it.

- Question (J5): is the move decided now, or after the owner has read P4's report?
- Options: (a) approve P0 to P4 now and decide P5a to P9 after their report (recommended); (b)
  approve all phases now; (c) P0 to P4 only.
- Today: nothing is scheduled; `docs/state.md` lists no running or planned game job.
- After P4 the path lists raise when they match nothing, the scope and the name parsing are in root
  modules, one cycle is gone and one is a listed pair, no import runs a forbidden way and R3 keeps
  it so, job file names are in one module, and the Code map is generated. Reaching that state costs
  19 plant `file` values and 3 plant texts, 145 test lines of which 60 are assert or raises lines, 5
  marker reference lines that the gate checks and 4 that it does not, and a new test setup at each
  of P1, P2 and P3, and at P7 if it lands before P4 with a battle between. P1 already changes
  play-scope bytes, so if the plan stops at P4 the owner picks which live checks are rerun at the P4
  revision (J24). (a) lets the owner see the checks run once before the costly part, and the two
  routes of the table above are recounted in P4's report. (b) saves one round of questions. (c)
  leaves `battle/` flat with 65 Python files.
- Best case for (b): one decision in place of two, and no wait between P4 and P5 in which battles
  land in a test setup of their own.
- Best case for (c): P0 to P4 remove the wrong-way imports and one cycle, put R3 in force, make the
  path lists fail when they match nothing and generate the Code map; policy names stay module paths
  and `battle/` stays flat, and no measurement shows that sub-packages improve an agent's results.

JUDGEMENT: Package move — Claude, 2026-11-15, all of battle/ and eight engine files move in one
tool-made commit, the six existing battles into folders. Moving only new battles, or no file, keeps
today's flat layout and its approvals. C8 to C10 and the folder form of R3 rest on it.

- Question (J6): do existing files and existing battles move?
- Options: (a) all, in one commit a tool reproduces, followed on the owner's yes by `doctor`, one
  `launch` and one `hold` battle at 1x in the main checkout, whose register row and log entry are
  committed there (recommended); (b) only the next new battle gets a folder; (c) no move.
- Today: the 2026-11-15 Terminal-Bench comparison proposed "Do not move existing battles" and to
  build the next new battle as one folder first
  (`runs/terminal-bench-review-20261115/report.md:611-615`); on 2026-11-14 the owner first limited a
  cleanup to "Team files only" and later said "Everything now".
- (a) departs from that proposal. (b) leaves some battles in folders and some flat, which the same
  report calls worse than either. (c) keeps R3 as the table of about 65 module names that P3 lands,
  in which a new module needs a row before the rule covers it, and costs no plant, marker or link
  edit.
- What (a) gives that (c) does not: no folder with more than eleven modules, a rule keyed by
  folders, and one folder per battle. It does not shorten the two routes in the table above.
- Best case for (b): it tests on one battle whether a folder reads better, for a handful of
  approvals.
- Best case for (c): P0 to P4 already remove the wrong-way imports and put R3 in force; the move
  costs about 286 plant approvals and a new test setup, and no measurement shows that sub-packages
  improve an agent's results.

JUDGEMENT: Test setup across the move — Claude, 2026-11-15, the path-keyed fingerprint stays, so
battles before and after the move are two test setups. A declared harness version would let them
share one. Figure 1's controlled comparison and the change-levels table rest on it.

- Question (J7): may a battle played before a phase and one played after it share a test setup?
- Options: (a) no; the report shows one boundary for each phase that is followed by a benchmark
  battle, and one in all only if no benchmark battle is played from P1's merge until P5's
  (recommended); (b) a declared harness version replaces the code map in the fingerprint for new
  manifests.
- Today: any source change outside the presentation list starts a new setup
  (`battle/report_html.py:215-216`). P1 edits `src/gameai/provenance.py` and `__main__.py`, P2 adds
  three modules and edits `play.py`, P3 edits most controller files, P5a edits `controllers.py` and
  `registry.py`, P5 moves 80 paths, and the `pyproject.toml` line of P7 is in the scope too; none of
  these is on the list. P4 edits no file in the scope.
- (a) changes no rule. (b) is the change-levels decision the owner answered "Decide later" on
  2026-11-15; it changes which battles the page compares.
- Best case for (b): where K4 and K6 pass, no statement and no replayed decision changed, and (a)
  makes every earlier battle unusable as a control for a later one. K6 does not run for P1 to P4
  (C0).

JUDGEMENT: Package set — Claude, 2026-11-15, ten sub-packages and five root modules with one
allowed-import table, roles first and battles inside one role. Fewer or more packages, or battles
at the top level, change which edits the gate refuses. The move table and the rule tests rest on it.

- Question (J13): which packages, and which may import which?
- Options: (a) the tree and table of "Target structure" (recommended); (b) seven larger groups,
  with `benchmark` inside `reports` and `multiplayer` and `checkpoint` left in `engine`; (c) one
  folder per battle or domain at the top level, with the layers inside each; (d) sixteen packages
  with `policies`, `team` and `graph` at the first level.
- Today: two packages, `engine` and `battle`, and from P3 a rule keyed by module names. The four new
  root modules exist from P2 and P3 under every option (J35). R3 lands in P3 with the ten groups of
  option (a), as groups of module names, before this question is asked at the second yes. Two of
  P3's four cuts (`suite.py:368-448` to `statistics.py`, `report.py:526-547` to
  `benchmark_plans.py`) remove imports that are wrong-way only where `benchmark` and `reports` are
  separate packages, as they are under (a) and are not under (b).
- A wrong boundary found after the move costs a second round of the same approvals. Under (a)
  `benchmark` holds two modules and `records`, `run`, `scenarios` and `controllers/team` three
  each; 23 modules repeat their folder's name; 106 of the 150 commits that touched two or more
  `battle/` modules cross a package boundary.
- Best case for (b): `llm` changed together with `play` 23 times and `play` with `setup` 17 times
  (`research/cochange.txt`), so fewer, larger packages would keep more changes inside one folder.
- Best case for (c): it is the order the saved sources recommend for a system whose layers have
  grown. Against it here: 25 of 344 commits touch a battle's own modules.
- Best case for (d): each rule cell is smaller, so the table refuses more.

JUDGEMENT: Battle folder names — Claude, 2026-11-15, a battle's folder takes its scenario file's
name; module stems and page names stay. Renaming stems and pages too gives one name per battle and
breaks each reference that uses a renamed bare name. The battles test and the file map rest on it.

- Question (J14): what is a battle's folder called, and are its modules renamed to match?
- Options: (a) `siege_defence/` holding `wall_defence.py`, `wall_facts.py`, `wall_readings.py`, with
  the page still `haengju-eval.md` (recommended); (b) rename stems and pages to the folder's name.
- Today: four names per battle and no folder.
- (a) leaves four names per battle and keeps true the 38 marker references and 543 prose mentions
  that use a bare file name. (b) gives one name and breaks those of them that name a renamed stem or
  page: at least 10 of the 38 (`escalade.py` 8, `escalade_facts.py` 2); the rest were not counted.
- Best case for (b): under (a) a reader of `siege_defence/` finds files named `wall_*` and a page
  named `haengju-eval.md`.

JUDGEMENT?: References by path tail — Claude, 2026-11-15, the path edits of the move rewrite each
"rests on" reference as the shortest unique path tail. Keeping root-relative paths costs the same
edits at the next move. How a marker is named in use rests on it.

- Question (J21): when the move must edit a reference line anyway, which form does it write?
- Options: (a) the shortest unique tail, such as `escalade.py Door breach` (recommended); (b) the
  new path from the root.
- Today: 150 references give a root path and 49 a tail; `scripts/check.py:579-588` resolves both.
  The move edits 69 of them under either option, and 33 more references that the gate's pattern does
  not match (C7, Cost).
- Both are path-only edits to marker lines and "needs your yes" items. (a) changes the convention.
- Best case for (b): a full path is unambiguous; 17 base names repeat across `src` besides
  `__init__.py`.

JUDGEMENT?: Module-path commands — Claude, 2026-11-15, the four commands run as python -m <module>
keep that form at their new module paths. Turning them into subcommands changes the command line.
The Stop hook's command list and the commands the docs name rest on it.

- Question (J22): what happens to `python -m twwarhammer3.battle.manual_demo record` and the three
  like it (`support_timing`, `support_evidence`, `engine.multiplayer_probe`)?
- Options: (a) same form, new module path, with the hook list and docs edited in the move commit
  (recommended); (b) subcommands of `python -m twwarhammer3`.
- Today: the Stop hook recognises `twwarhammer3.battle.manual_demo` by that string, and one plant
  holds the line.
- (a) is a consequence of the move and gives one long path
  (`twwarhammer3.battles.support_timing.support_timing`). (b) adds commands, which is new behaviour.
- Best case for (b): every game-starting command would then be found by one module name.

JUDGEMENT?: No-marker list — Claude, 2026-11-15, check.NO_MARKER and docs/judgement.md keep naming
the same six policy files at their new paths. With J1 the stated reason (the card hash) no longer
applies, so dropping the rule is the alternative. Which files may carry markers rests on it.

- Question (J23): may `scripted.py`, `calibration.py`, `llm.py`, `commander.py`, `team.py` and
  `skills.py` carry markers after J1?
- Options: (a) no, keep the list at the new paths; a module cut from one of the six is on the list
  too (recommended); (b) drop the six from the list.
- Today: the list exists because a comment changes the card hash.
- (a) changes nothing but paths. (b) lets judgement calls in those files be marked where they are.
- Best case for (b): the 14 other controller files already carry 53 markers, and the list's reason
  falls away with J1.

JUDGEMENT: Saved scripts at their revision — Claude, 2026-11-15, a saved script under runs/ is
rerun in a worktree at the revision its evidence records. Re-exporting modules under battle/ would
keep it running at HEAD. A live agreed check's pinned checker and eight other scripts rest on it.

- Question (J25): how is a saved script that imports `twwarhammer3.battle...` rerun after the move?
- Options: (a) saved scripts run unedited in a worktree at their recorded revision; for the pinned
  checker the owner is asked at P9 to approve a copy with six lines rewritten (four imports and two
  path keys in assert lines) and its new sha256, and until then that entry is "cannot be rerun at
  this revision" (recommended); (b) keep `twwarhammer3/battle/` as modules that re-export the moved
  names; (c) as (a) without the new copy: the entry stays at its last passing revision for good.
- Today: 11 saved scripts that tracked files name import a repository package, 9 of them
  `twwarhammer3.battle`. One of the nine, `runs/gap-continuation-20261101/goal-probe-draft.py`, is
  the frozen command of a live agreed check and is pinned by sha256
  (`docs/agreed-checks.md:141-149`). Its lines 18, 19, 72 and 314 import `twwarhammer3.battle` and
  its lines 96 and 99 look up `src/twwarhammer3/battle/` paths in the fingerprint map, so after P5
  neither its live probe nor its recount runs at HEAD. Five of its lines read `play.SOURCES`, which
  P2 moves (C3, Cost).
- (a) leaves the pinned bytes alone until the owner approves a new hash. (b) keeps a second set of
  module paths, and a test that patches a name through a re-export changes nothing. (c) retires
  that agreed check.
- Best case for (b): the pinned checker keeps running at HEAD with no new approval. Best case for
  (c): no checker is edited at all.

### C8. Five further splits, described and not recommended (P6)

**Today.** The files with several jobs listed under "What is wrong today". None of the five splits
below removes a wrong-way import: the four cuts that do are in C4.

**Change.** Under option (c) of J15 each split is its own commit after P5; statements move
verbatim.

| File after P5 | Would become | What it gives | Cost in tests (lines that reach a moved name; assert or raises lines among them) and plants on the file |
|---|---|---|---|
| `scenarios/setup.py` (1,119 lines) | `catalogue.py` (1-91, 104-111, 118-128, 154-244, 585-617), `declaration.py` (665-794), `lobby.py` (112-117, 129-151, 247-474, 477-582, 620-662, 797-861), `readback.py` (864-1119) | 5 of 11 importers want only `scenarios()` and would stop loading the lobby steps; a module name per job | 373; 61; 5 plants; 3 markers and 4 reference lines |
| `checkpoint/checkpoint.py` (1,017) | the launcher stays; the analysis of saved attempts (259-289, 294-349, 352-409, 412-610, 767-823, 959-1017) to `checkpoint_analysis.py` | a module name for the analysis; every importer still loads the launcher (`audit.py:41`, `rl.py:764`) | 97; 43; 27 plants; 6 markers and 2 reference lines |
| `run/play.py` (826) | `session.py` (102, 105-122, 262-303), `view.py` (574-588, 591-599, 624-648); `_drive` stays whole | `rl.py`, `checkpoint.py` and `manual_demo.py` take helpers without the loop | 78; 15; 24 plants; 1 marker |
| `controllers/team/team.py` (543) | `model_team.py` (435-500), `team_diagnostics.py` (503-543) | the dispatcher stops importing `llm.py` | 9; 1; 6 plants |
| `controllers/controllers.py` (249) | `build.py`, `card.py` (148-182); `rotation` (107-132) to `run/play.py` | no module named like its package | 24; 6; 3 plants; the marker Witness hash |

The ranges for `setup.py` are those the file-map check found to give no cycle; this page's first
draft put `ENGINE_TYPES` in `lobby.py`, which made `catalogue.py` and `lobby.py` import each other.
With them a readings module would load `catalogue.py` and `readback.py`. The split of
`controllers.py` needs `card` to read a controller's kind from the registry row (C2), or R5 must
list `build.py`, `card.py` and `configured.py` as a group. `__main__.py` is not on the list: two of
the three ranges the first draft gave lie inside functions and are edits, and `run` may import
`controllers` for the ledger paths. `llm.py`, `rl.py` and `escalade.py` are not split under any
option.

**Why.** Classes that are not reused together should not be grouped together (Martin, page 17);
that is the case for `setup.py`. The saved Ousterhout page counts against most of the others: it
calls classes of 200 to 2,000 lines fine, warns against small classes and says to decompose only
where it can be done cleanly (`refs/principles/ouster-cs190-modularDesign.html:98-104`, `:250`). By
the ranges above `card.py` would hold 35 lines, `team_diagnostics.py` 41, `view.py` about 50,
`session.py` and `model_team.py` about 65 each.

**Cost.** Under (c): 581 test lines, 126 of them assert or raises lines (lower bounds, as in C4), 23
plants on moved statements that get a second `file` edit, 11 markers that leave their file, up to 6
reference lines that change again, and one commit and one plants run per split.

**Check.** Per commit: K4, K5, K10, K1, K2; K6 for `team.py` and `controllers.py`; R3 and R5
unchanged. The wrong version K4 must catch: a split that edits a moved function body.

JUDGEMENT?: Further file splits — Claude, 2026-11-16, after the move no further file is split;
setup.py, checkpoint.py, play.py, team.py and controllers.py stay whole. Splitting setup.py alone,
or all five, is the alternative. 23 second plant edits and 581 test lines rest on it.

- Question (J15): which of the five splits in the table above are wanted?
- Options: (a) none (recommended); (b) `setup.py` only; (c) all five.
- Today: none of these files is split. `benchmark.py` was split once already on 2026-11-14 ("Do
  both now"), and C4 cuts the rest of it.
- (a) leaves five files with several jobs each and a module named `controllers/controllers.py`. (b)
  costs 373 test lines, 61 of them assert or raises lines. (c) costs what the table sums to.
- Best case for (b): `setup.py` is the largest file, four jobs are easy to tell apart in it, and
  five importers would load a fifth of it.
- Best case for (c): the owner asked for the most readable layout, and a module name per job is
  what a reader searches by. This page's first draft recommended (c); the checks found that the
  `checkpoint.py` split spares no importer, that the `__main__.py` row was no verbatim move, and
  that the cost in assert lines had been counted for `setup.py` only.

### C9. Test imports (P7)

**Today.** The test items of "What is wrong today". `tests/twwarhammer3/wh3_fixtures.py` has five
jobs and is imported by 43 files. 49 of 59 `battle/` modules have a test file named
`test_wh3_<module>.py`. Spire's tests sit in eight top-level folders, one named `tests/engine`.
[testing.md](testing.md) holds a pending marker on the test layout with another tree.

**Change.** No test file changes path.

- `pyproject.toml` gets one more `pythonpath` entry, `tests/twwarhammer3`. The 15
  `sys.path.insert` lines, which all insert that folder, go; with the entry every bare-name import
  under `tests/` resolves when one folder is collected alone (`verify/file-map/check_tests.py`).
- The builders that 13 test modules lend to 13 others move into the `wh3_*.py` helper modules. A
  rule test fails when a `test_*.py` file imports a `test_*.py` file; a live checker and a helper
  module may be imported.
- The rule "a module's tests are in `test_wh3_<module>.py`" and the ten modules without such a file
  go into `code.md` (C6).

**Why.** Of the references, Gymnasium mirrors its packages in `tests/` and imports helpers through
the `tests` package (`refs/gymnasium/tests/testing_env.py`, `68c3f95`), which this repository does
not have. The two references that set out to mirror lost it: Harbor has 124 test files at the top of
`tests/unit`, and open-robot-skills stops its one-directory-per-bundle rule at 24 flat test files.
SWE-bench (29 files and one folder at the top of `tests`) and Inspect (53 at the top) do not mirror.
The research note rated reorganising offline tests by subject "low" (harbor research note).

**Cost.** One line in `pyproject.toml`, which is in both games' scopes: it lands while no job of
either game runs and starts a new test setup. Landed alone it adds one test-setup boundary; landed
in the quiet time of P1 or P2 with no battle between the two merges it adds none. Builder moves in
13 test files, some of them named by agreed checks; a verbatim move is netted out by the gate. No
plant target and no agreed-check path changes.

**Check.** K5 (ids equal, pass and skip counts equal, each skip reason equal); each folder under
`tests/` collects on its own; the rule test with a planted test-to-test import; K1 with both
extras; K2.

JUDGEMENT: Test folders by package — Claude, 2026-11-16, no test file moves; one pythonpath entry
and a rule test replace the 15 sys.path lines. Moving 109 flat WH3 test files into package folders
is the alternative, as is the tree in docs/testing.md. 323 plant targets rest on it.

- Question (J16): do the existing flat test files move into folders named after the packages?
- Options: (a) none; the import cleanup above (recommended); (b) 109 of the 118 flat test files
  move in one mapped commit after the source move, the six helper modules and the demo generator
  go to `tests/twwarhammer3/support/`, and a rule test fails on a test file at the top level beyond
  the nine that stay (the file map lists each destination).
- Today: 118 test files in one folder. The pending marker in `docs/testing.md` (Codex, 2026-10-23)
  proposes game then feature, with `live/` and `browser/` folders; only the owner removes or
  rewords it.
- (a) costs no plant target and no agreed-check path, and leaves a flat test folder beside ten
  source packages. (b) costs 323 plant test targets, nine files named in `docs/agreed-checks.md`
  with four named test ids, 7 marker reference lines and a second rewrite of the 131 files P5
  already edited; 14 of its placements are marked to confirm. Pass records are keyed by an entry's
  title, so their history would continue; that rests on JUDGEMENT? `scripts/check.py` Pass at a
  revision. Under either option `test_wh3_siege_assault.py` and `test_wh3_waves.py` stay where they
  are: scenario declarations name their paths (`configs/twwarhammer3/scenarios/siege_attack.json`,
  `siege_defence.json`), and the declaration digest covers that text
  (`battle/replay_schedule.py:40-44`).
- Best case for (b): a test is found in the folder of the code it tests, and the whole WH3 folder no
  longer lists 135 files. Against it: finding a test is a name lookup for 49 of 59 modules today,
  and the whole folder runs in 44 to 47 s.

### C10. Docs, the code page and the live checks (P8, P9)

**Today.** 249 Markdown links point into `src`, `tests`, `scripts` or `configs`, 67 of them at a
path this plan changes; the code page cites 215 `path:line` references at five commits and pins 42
file hashes (inventory, F1, G2). `.claude/workflows/wh3-version-review.js:14` holds the checkout's
absolute path. 14 agreed entries need a game: 8 have a launch command and 6 describe a live
procedure in prose (`docs/agreed-checks.md:18`, `:36`, `:46`, `:62`, `:93`, `:191`); 2 of the 14 say
they have no passing revision (`:46`, `:62`), and 2 more record only a run made before they were
agreed (`:18`, `:36`). The passes that are recorded are at revisions before the 2026-11-14 cleanup
(`210e356`, `c1ad84d`, `3adbaa4` and others).

**Change.** The links move with their files in P5, because the link test is part of the gate. P8 is
what remains: prose paths; [development.md](development.md) Layout names the packages and routes to
`code.md`; the code page's views are refreshed once by the procedure in
`docs/how-code-works-plan.md`; the workflow file derives its root at run time; the log entry and
`docs/state.md` record the result. P9: the live agreed checks the owner picks are rerun in the main
checkout at 1x and their passes recorded.

**Why.** The three unchecked lists named under "Hand-kept descriptions" drifted; the link test
already fails on a broken link, and the path test of C1 covers the agent files. No outside
reference was read for this change.

**Cost.** One code-page refresh, which the owner capped at 100 API calls and at most one a week
(`docs/how-code-works-plan.md:14`); game time at 1x for P9, not estimated.

**Check.** `tests/test_doc_links.py`, which a link left at an old path fails; the gate, run in the
main checkout, reports 0 flagged code-page views and no marker problem (a worktree does not compute
the flags); each rerun live check is recorded with its revision in `docs/agreed-checks.md`.

JUDGEMENT: Live checks after the restructure — Claude, 2026-11-15, each live-checked feature is
unverified at the new revision until its check is rerun in a set the owner picks. Carrying passes
over on the offline checks is the alternative. Which features count as verified rests on it.

- Question (J24): when does a feature with a live agreed check count as verified again?
- Options: (a) when its check has been rerun at the final revision; the owner picks the set and the
  order; the entry whose checker J25 covers waits for its approved copy (recommended); (b) the old
  passes carry over on K3 to K8 and one live `hold` battle.
- Today: a feature counts as verified only at revisions where its check passed
  (`docs/agreed-checks.md:3-5`), and earlier carry-overs argued from identical play-scope bytes
  (`:217-218`, `:261`).
- Under (a) each such feature stays verified only at its last passing revision, as today. P1 to P3
  already change play-scope files and the live checkers' own import lines, so no pass carries to a
  restructured revision by identical bytes. If the plan stops at P4, the reruns are asked for then;
  the pinned checker of J25 runs unedited at the P4 revision only if `play.py` still imports
  `SOURCES` by name (C3, Cost). (b) saves the game hours. No entry has a pass at the restructure's
  base, so under (b) the owner would also accept every change between an entry's last passing
  revision and that base.
- Best case for (b): the offline checks compare every moved statement and the decisions saved on
  this machine; what a live rerun adds beyond them was not measured.

### C11. Later changes, each on its own card

Two changes follow the same direction and are kept out of the phases because each changes code that
a move check cannot cover.

JUDGEMENT: Shared trace reader — Claude, 2026-11-15, after P3 one module joins decisions to
acknowledgements for all readers; each reader keeps its own rule for a bad line. The owner answered
"Leave as is" on 2026-11-14; keeping the seven loops is that answer. 41 reader plants rest on it.

- Question (J29): should a module `trace.py` beside `layout.py` (in `battle/` before P5, in
  `records/` after) hold the one join and the source-time fallback, with loaders that fill today's
  defaults and refuse an unknown format version, and with one description of the result keys and
  trace kinds that those loaders read through?
- Options: (a) yes, one reader per commit, each checked by K7 over every saved result, truncated
  traces included; a reader whose output differs keeps its loop (recommended); (b) leave the loops.
- Today: seven joins and six copies of the fallback; the owner's 2026-11-14 answer was about one
  rule for truncated or invalid lines. Nothing in it waits for the move: `layout.py` exists from
  P3.
- (a) departs from the strict reading of that answer and is the change that shortens the
  record-field route of C7's table. Whether the description is a `TypedDict`, a dataclass or a
  model class is asked on that card. (b) keeps a record-field change at seven edits.
- Best case for (b): the loops differ in small ways on purpose, and K7 covers only this machine's
  evidence.
- The pattern for (a) is one reader that every tool calls and that refuses a version it does not
  know: `refs/inspect_ai/src/inspect_ai/log/_file.py:530-647`, with the description at
  `log/_log.py:1325-1386`.

JUDGEMENT: Launch helper — Claude, 2026-11-15, after the plan, one context manager holds the launch
sequence, landed only with one live launch. Leaving the five copies in src and three in checkers
is the alternative. 48 test patches on play.py and every live check rest on it.

- Question (J30): after P9, should `engine/launch.py` hold lock, install, mailbox, reset, session
  file and game process, taking the session dict and yielding the mailbox and the game?
- Options: (a) yes, one caller per commit, each with a recorded step order before and after and one
  live launch before it lands (recommended); (b) leave the copies.
- Today: the callers differ in what they do between the steps (`battle/play.py:229-230`,
  `battle/checkpoint.py:195-198`, `engine/worker.py:375-378`).
- (a) changes launch code, whose only real check is a game. (b) keeps eight places to edit.
- Best case for (b): a wrong step order shows only live, the copies have worked since 2026-10, and
  the research note on environment interfaces warns that a helper with many optional hooks is worse
  than five copies.
- The pattern for (a): a launch and close pair on one object
  (`refs/smac/smac/env/starcraft2/starcraft2.py:316-394`, `:1478-1484`) and the `with` form
  (`refs/gymnasium/gymnasium/core.py:268-276`).

## Order of work

Rules for every phase. Work is done in the agent's own worktree and branch; one phase is one
reviewed merge, and the owner is asked before each merge and push to `main`. Nothing lands in the
main checkout while a WH3 queue runs, because any HEAD move stops it (`scripts/wh3_queue.py:51-56`).
Both rules rest on JUDGEMENT? `docs/workflow.md` Worktree details. A phase that touches a play scope
(`src/gameai`, `src/twwarhammer3`, `configs/twwarhammer3`, `pyproject.toml`, `uv.lock`,
`.python-version`) lands only while no play job of that game runs, and it starts a new test setup
for the battles after it. P3, P5 and P6 contain no intended behaviour change. P1 adds one refusal
(J9), P2 adds the data file of J34, and P5a changes what a new register row records (J1, J8); each
is a commit of its own. No phase holds a version bump, a prompt edit, a Lua edit, a dependency
change or a new game-build pin. A commit either moves statements or edits them. Each phase ends
with the gate passing in the main checkout, all plants caught there, its checks, and a log entry of
about 20 lines that says what is unverified.

| Phase | Contains | Stop point | Must not run at the same time | Waits for |
|---|---|---|---|---|
| P0 Decisions and checks | the owner's first answers; C0's first build and its two baselines | no tracked file changed | anything tracked | J3, J5; J4 before P2's first plant batch |
| P1 Path lists | C1 | the tests, the `provenance.py` edit and the command marks merged; nothing moved | a job of either game; a benchmark series whose rows should share a setup | J9, J10 |
| P2 Scope and names | C3; C2 step 1 | one scope module; readers take names from `registry.py`; R2 on | a job of either game; such a series | J4, J12, J33, J34, J35, J36 |
| P3 Cuts in place | C4, C5 | no wrong-way import and R3 on with its one allowance by name; one cycle gone; job file names in one module; `battle/` still flat | a WH3 job; such a series; any edit inside a moved statement | J11, J31 |
| P4 Map and guidance | C6 | Code map generated, `code.md` on the route; the plan can stop here | a running queue (P4 edits no file in a play scope) | J19, J20 |
| P5a Declared names | K6; C2 step 2 | new jobs record declared names; old names resolve | a WH3 job; a benchmark series | the second yes (J5); J1, J2, J8, J32 |
| P5 The move | the move tool, K3 and K9's table part; C7 | `battle/` gone; R3 keyed by folders; one live launch and `hold` battle done and their register row committed | any other change in the commit; a WH3 job; a benchmark battle between P5a and P5 | J6, J7, J13, J14, J21, J22, J23, J25 |
| P6 Further splits | C8, only under J15 option (b) or (c) | the chosen files are split | a WH3 job; another phase in the same commit | J15 |
| P7 Test imports | C9 | no test file imports a test file; none of the 15 `sys.path.insert` lines that add `tests/twwarhammer3` is left | a job of either game; such a series | J16 |
| P8 Docs and code page | C10, first part | prose paths follow; 0 flagged views in the main checkout | a marker text change (P8's are path-only edits) | none |
| P9 Live checks | C10, second part | each rerun check names the new revision in `docs/agreed-checks.md` | any commit in the main checkout while a checker runs | J24, J25 |

P0 to P4 can be done between game jobs; each of P1 to P3 starts a new test setup for the jobs after
it. P7 touches no moved path under the recommended option, so it may land any time after P1, also
before the stop at P4; it starts a new test setup too (C9). P5a and P5 need one quiet window with no
benchmark battle between them. P8 lands in the same window as P5. P4 may also run after P5; before
is cheaper by the Code map edits.

## What stays as it is

- **`src/gameai`'s nine files and their paths.** `provenance.py` is imported by 50 source modules,
  two of them byte-pinned Spire files (`src/spire/language/training.py:26`, `demonstrations.py:20`);
  `battle/export.py:44` reads `src/gameai/llm.py` at old revisions; `windows_game.py` is copied
  alone to Windows; 33 plants name these files. `llm.py` holds five concerns in 555 lines and no
  importer is hurt by it.
- **The job modules stay per game.** `docs/development.md:24-25` says so. The measured overlap of
  the two play loops is 13 identical lines of 135 (gameai map, 4.4), Spire is paused, and a shared
  skeleton would put both games' record formats behind one edit.
- **The registers and logs.** `docs/twwarhammer3/results.csv` is named in the root `AGENTS.md`, in
  `battle/stats.py:18` and in 12 Markdown links; rows are history and are never rewritten, which K8
  checks byte for byte.
- **The docs tree, `configs/twwarhammer3`'s layout, the package names.** 2,029 relative links, ten
  path constants and prompt hashes, and 103 mentions of `python -m twwarhammer3` would move for a
  tidier listing.
- **`scripts/check.py` as one file, the hooks and their paths, `tests/plants.toml` as one file.**
  `core.hooksPath`, both tools' settings and the 104 plants that name a file under `scripts/` rest
  on those paths.
- **The test folders.** C9 changes how tests import helpers and moves no file.
- **`play._drive` as one 176-line function, `rl.py` and `escalade.py` whole, `llm.py` whole apart
  from the statements of C4.** Each has one job or steps that share state; length alone is no
  reason to split.
- **Three statements that a hash covers.** The four unit-class constants stay in `skills.py`,
  `unit_geometry.py` stays a module and `recount` stays in `rl.py` (C4).
- **The owner's earlier answers that nothing here needs changed:** the witnesses' five differing
  `_send` rules ("Leave as is"), no controller base class ("Skip it"), the three copy blocks in
  `play_episode`. The 14 sites that probe optional controller members stay; a wrapper around the
  controller would be what `card` receives, and `card` reads `type(policy)` for `class`,
  `source_file` and `source_sha256` (`battle/controllers.py:149-159`).
- **Outside a restructure, each its own later question:** a `readings` command for the four readings
  modules that have no tracked caller; new result keys and a failure table; one tally for every
  reader; the outcome label for scenarios without a profile; the page's scores computed in Python
  instead of `report.js`. Each changes what is recorded or printed.

JUDGEMENT: Spire — Claude, 2026-11-16, no file under src/spire or in Spire's test folders changes
in this plan. A scope.py cut from fullrun/play.py and seven test folders moved under tests/spire/
are the alternative. One agreed-check path and five plant targets rest on it.

- Question (J17): how much of Spire changes while its tracks are paused?
- Options: (a) nothing (recommended); (b) `src/spire/scope.py` takes `SOURCES` from
  `src/spire/fullrun/play.py:45-46`, its two importers follow, and Spire's seven test folders move
  under `tests/spire/`.
- Today: 63% of Spire's source is paused first-combat code, byte-identical to 2026-10-12 (spire
  map). Two source files import the tuple: `src/spire/fullrun/replay.py:32`, which takes three
  other names from the same module, and `src/spire/openweight/env.py:97`.
- Under (a) no Spire file is edited, launch code included; J34 compares Spire's runtime values in a
  test and does not edit them. Spire's source fingerprint still changes, because its scope covers
  `src/gameai` and `pyproject.toml`, which P1, P2 and P7 edit. The five pinned files keep path and
  bytes, checked by an empty `git diff --stat d64da18 HEAD` over them. The file list in
  `docs/spire/AGENTS.md` becomes generated under J19. (b) costs 5 plant targets, one agreed-check
  path with one test id (`tests/fullrun/test_spire_cli.py`) and 1 marker reference line.
- Best case for (b): the top of `tests/` then holds one folder per game, and `tests/engine` no
  longer reads as WH3's engine.

JUDGEMENT: Cloud prices stay in the play scope — Claude, 2026-11-16, gcp-regions.json stays in
configs/twwarhammer3/ and so in every job's fingerprint, although only scripts/wh3_gcp.py reads it.
Moving it to scripts/gcp/ is the alternative. What a job's source identity covers rests on it.

- Question (J18): should a cloud price edit change a battle's source fingerprint?
- Options: (a) leave the file where it is (recommended); (b) move it to `scripts/gcp/`.
- Today: a price edit would change every later job's source hashes and stop a running job. The file
  has one commit, its creation (`6202878`, 2026-11-03), and `docs/state.md` lists no VM.
- (a) changes nothing. (b) takes one file out of the scope rule "everything under
  `configs/twwarhammer3`", which has no exception today.
- Best case for (b): no battle reads the file, and the next price edit starts a test setup for no
  reason a battle could show.

JUDGEMENT?: Graph library rule — Claude, 2026-11-15, the loader keeps refusing an artifact whose
library digest differs. A declared-version rule or an owner-approved list of old digests would let
old artifacts load. Reuse of authored graphs for the suite's gap arm rests on it.

- Question (J26): should authored graphs saved before 2026-11-14 load again?
- Options: (a) no change (recommended); (b) an owner-approved list of older digests declared equal;
  (c) a rule keyed on declared library versions, hashes recorded.
- Today: none loads. 347 `manifest.json` files under `runs/` hold a `library_sha256`, and none
  equals the digest this checkout computes (`f70f0b174dbe`), because `team.py` and `graph_goals.py`
  changed on 2026-11-14 (`cd59c92`, `a69af01`). The restructure therefore refuses no artifact that
  loads today. The digest changes again at P3 and at P5, when the library files' import lines
  change; what it covers does not change (C4). The initiation checker compares its own file's hash
  (`battle/graph_initiation.py:167`); that file is byte-identical to the revision its agreed check
  passed at and changes for the first time at P5.
- (b) and (c) change what "the same library" means; a judge found that for 308 of 333 artifacts the
  library's content differs outside the file hashes too. From P5 an artifact that carries an
  initiation proof is refused by the checker's own hash as well
  (`battle/graph_initiation.py:165-168`), under (a), (b) and (c) alike, so an owner who wants such
  artifacts to load again must also decide that comparison.
- Best case for (b): a short list the owner reads once. Best case for (c): after the move every
  import rewrite in the library files changes the digest again, and a version rule would stop that
  for artifacts authored from now on.

JUDGEMENT: Lua untouched — Claude, 2026-11-15, no byte under mod/ changes in this plan and the
battle script stays one file. Splitting it into library files changes the pack hash and can only
be shown in a live game. 16 plants and the Lua tests' loader rest on it.

- Question (J27): is the 2,384-line battle script split?
- Options: (a) no (recommended); (b) split it into library files alone, as its own change, with
  every live check rerun.
- Today: one chunk of 82 local functions. 25 JSON files under `runs/` hold a pack hash value and
  none equals the pack this checkout builds (`f5c7de5589cd`), so no saved checkpoint library
  restores today either way.
- (a) keeps the largest single reading cost; `code.md` gets a command that lists the script's
  functions with line numbers. (b) cannot be checked offline: the Lua tests load definitions by
  name from the one file (`tests/twwarhammer3/wh3_lua.py:19-30`).
- Best case for (b): no saved library depends on the current pack, so the usual cost of a Lua change
  is already paid.

JUDGEMENT?: Scripts stay flat — Claude, 2026-11-15, no file under scripts/ moves. Folders by what
each script serves (code page, WH3 tools, Spire drivers) would group 18 flat files and retarget
their plants. An agreed-check path and the Spire audits' path keys rest on it.

- Question (J28): should `scripts/` get folders by what each script serves?
- Options: (a) no (recommended); (b) `codepage/`, `wh3/` and `spire/` folders, with the gate and
  hooks left at their paths.
- Today: 18 scripts at one level and three folders.
- (b) moves `diagram_files.py` (22 plants), `wh3_reserve_cells.py` (named by an agreed check) and
  scripts whose `ROOT` is computed from folder depth.
- Best case for (b): the folder then says what a script belongs to, which the flat listing does
  not.

## What we would not copy from the references

| Practice | Where | Why not here |
|---|---|---|
| A decorator registry with registration on import, or by `register()` calls | `refs/inspect_ai/src/inspect_ai/_util/registry.py` (880 lines); Gymnasium's 63 `register(` calls in `gymnasium/envs/__init__.py` | Both serve outside packages. One literal table of about 81 rows can be read without running anything |
| Shims that keep moved names importable | Inspect's about 100 relocated attributes (`_util/deprecation.py`) | Every caller here changes in one commit, only recorded names need an alias, and a shim makes a test patch succeed and change nothing |
| A central table of evaluations | Inspect Evals' `listing.yaml`, removed by `adr/0001-eval-metadata-location.md`; SWE-bench's per-repository spec map, gone at 5.0.0 (`CHANGELOG.md:34`) | Both projects moved the entry into each evaluation's folder; the battles test here reads the folders, and nothing would run from a table |
| Typed record models before a reader loads through them | `refs/inspect_ai/src/inspect_ai/log/_log.py`; Harbor `models/` | They hold where one loader validates through them; here the description waits for that loader (J29) |
| A base class and factory per kind | `refs/harbor/src/harbor/agents/base.py`; CARLA's defaults for optional hooks in `leaderboard/autoagents/autonomous_agent.py:32-132` | The owner declined a base class; the three-method contract stays |
| A shared job skeleton across games | `refs/harbor/src/harbor/trial/` | See "What stays as it is" |
| A second metadata file per evaluation | `refs/inspect_evals/src/inspect_evals/gpqa/eval.yaml` | Scenario entries already hold name, version, status and split |
| Classes found by globbing a folder | `refs/carla-leaderboard/leaderboard/scenarios/route_scenario.py:271-292` | A bare class name becomes an identity again, and two classes of one name collide silently |
| One adapter that supplies optional members | the CARLA research note's proposal, with `leaderboard/autoagents/agent_wrapper.py:121-139` as the place the loop calls | See "What stays as it is" |
| A total layer order and port classes | `refs/import-linter/.importlinter` | A table with one row per package is enough for the imports found here; the tool itself is J33's other option |
| Tests that mirror the packages | `refs/gymnasium/tests/` | It works there through a `tests` package; the two references that tried it without one lost the mirror (C9) |
| Side-by-side versioned files | Gymnasium `envs/mujoco/` `_v4`, `_v5` | Manifests record the revision, and superseded code goes to a tag |
| `reset` and `step`, wrappers, retries | `refs/gymnasium/gymnasium/core.py`, SMAC, `refs/harbor/src/harbor/trial/queue.py` | WH3 runs unpaused at 1x and never waits for a controller; any ending but a result stops the job |
| Many nested instruction files, a line cap on files, test selection from the import graph | agent-friendly research note, section 4 | No measurement there supports them, and the WH3 folder runs in under a minute |

## File map

The full list is `runs/restructure-plan-20261115/file-map.tsv` in the main checkout: one line for
each of the 483 tracked files under `src/`, `scripts/`, `tests/` and `configs/`, with the old path,
the action, the new path or paths, the phase and a note. Under the recommended options 407 files
stay, 60 move, 15 are split and one is deleted; the commit of P5 moves 74 files tracked today and
the six modules that P3 creates in `battle/`. The tables below are built from that file by
`runs/restructure-plan-20261115/scripts/final_plan/make_section.py`. They are a draft of the move
table; the owner reviews the table itself before P5 (J4). Beside it, `file-map-j15c.tsv` is the same
map with the five optional splits of C8, and `file-map-before-revision.tsv` is the map of this
page's first draft.

### `src/twwarhammer3/`

Paths in this table are relative to `src/twwarhammer3/`. A file that stays is listed with the other
files of its folder. For a split, the target that keeps most of the file is named first where there
is one, and the phases are those in which statements leave the file or its path changes; the line
ranges are in the note column of the TSV file. Five modules that P2 and P3 create have no row,
because they are not tracked today: `registry.py`, `scope.py`, `units.py` and `wording.py` at the
package root, and `battle/layout.py`, which P5 moves to `records/layout.py`. The parts cut in place
in P3 (`battle/profiles.py`, `battle/budget.py`, `battle/outcome.py`, `battle/statistics.py`,
`battle/graph_artifact.py`) appear as the split targets of the files they come from.

| Today | After | Phase |
|---|---|---|
| (package root): `__init__.py`, `__main__.py`, `protocol.py` | stays | - |
| `assets/`: `LICENSE.twpatcher`, `blank.ca_vp8` | stays | - |
| `battle/__init__.py` | deleted | P5 |
| `battle/audit.py` | `checkpoint/audit.py` | P5 |
| `battle/benchmark.py` | split: `scenarios/profiles.py`, `controllers/budget.py`, `records/outcome.py` | P3,P5 |
| `battle/benchmark_plans.py` | `benchmark/benchmark_plans.py` | P5 |
| `battle/calibration.py` | `controllers/calibration.py` | P5 |
| `battle/camp.py` | `battles/camp/camp.py` | P5 |
| `battle/camp_facts.py` | `battles/camp/camp_facts.py` | P5 |
| `battle/camp_readings.py` | `battles/camp/camp_readings.py` | P5 |
| `battle/candidates.py` | `checkpoint/candidates.py` | P5 |
| `battle/cannae.py` | `battles/cannae/cannae.py` | P5 |
| `battle/capture.py` | split: `run/capture.py`, `records/layout.py` | P3,P5 |
| `battle/checkpoint.py` | `checkpoint/checkpoint.py` | P5 |
| `battle/commander.py` | split: `controllers/commander.py`, `wording.py` | P3,P5 |
| `battle/configured.py` | `controllers/configured.py` | P5 |
| `battle/confirm.py` | `checkpoint/confirm.py` | P5 |
| `battle/controllers.py` | split: `controllers/controllers.py`, `registry.py` | P2,P5a,P5 |
| `battle/digest.py` | split: `reports/digest.py`, `wording.py` | P3,P5 |
| `battle/escalade.py` | `battles/siege_attack/escalade.py` | P5 |
| `battle/escalade_facts.py` | `battles/siege_attack/escalade_facts.py` | P5 |
| `battle/escalade_readings.py` | `battles/siege_attack/escalade_readings.py` | P5 |
| `battle/evade.py` | `controllers/evade.py` | P5 |
| `battle/evidence_rules.py` | split: `battles/evidence_rules.py`, `protocol.py` | P3,P5 |
| `battle/exact_stats.py` | `reports/exact_stats.py` | P5 |
| `battle/export.py` | `reports/export.py` | P5 |
| `battle/graph.py` | `controllers/graph/graph.py` | P5 |
| `battle/graph_author.py` | split: `controllers/graph/graph_author.py`, `controllers/graph/graph_artifact.py` | P3,P5 |
| `battle/graph_goals.py` | `controllers/graph/graph_goals.py` | P5 |
| `battle/graph_initiation.py` | `controllers/graph/graph_initiation.py` | P5 |
| `battle/graph_view.py` | `reports/graph_view.py` | P5 |
| `battle/graph_view_assets/index.html` | `reports/graph_view_assets/index.html` | P5 |
| `battle/graph_view_assets/view.css` | `reports/graph_view_assets/view.css` | P5 |
| `battle/graph_view_assets/view.js` | `reports/graph_view_assets/view.js` | P5 |
| `battle/lines.py` | `battles/lines/lines.py` | P5 |
| `battle/lines_facts.py` | `battles/lines/lines_facts.py` | P5 |
| `battle/lines_readings.py` | `battles/lines/lines_readings.py` | P5 |
| `battle/llm.py` | split: `controllers/llm.py`, `wording.py`, `units.py` | P3,P5 |
| `battle/local_command.py` | split: `controllers/team/local_command.py`, `units.py` | P3,P5 |
| `battle/local_scripts.py` | `battles/cannae/local_scripts.py` | P5 |
| `battle/local_team.py` | split: `controllers/team/local_team.py`, `controllers/controllers.py` | P3,P5 |
| `battle/manual_demo.py` | `run/manual_demo.py` | P5 |
| `battle/peers.py` | `multiplayer/peers.py` | P5 |
| `battle/play.py` | split: `run/play.py`, `scope.py` | P2,P5 |
| `battle/reference.py` | `controllers/reference.py` | P5 |
| `battle/replay.py` | `reports/replay.py` | P5 |
| `battle/replay_schedule.py` | `battles/replay_schedule.py` | P5 |
| `battle/report.py` | split: `reports/report.py`, `benchmark/benchmark_plans.py` | P3,P5 |
| `battle/report_assets/replay.js` | `reports/report_assets/replay.js` | P5 |
| `battle/report_assets/report.css` | `reports/report_assets/report.css` | P5 |
| `battle/report_assets/report.html` | `reports/report_assets/report.html` | P5 |
| `battle/report_assets/report.js` | `reports/report_assets/report.js` | P5 |
| `battle/report_assets/suite.js` | `reports/report_assets/suite.js` | P5 |
| `battle/report_html.py` | split: `reports/report_html.py`, `scope.py` | P2,P5 |
| `battle/reserve.py` | `scenarios/reserve.py` | P5 |
| `battle/rl.py` | `checkpoint/rl.py` | P5 |
| `battle/scripted.py` | split: `controllers/scripted.py`, `units.py` | P3,P5 |
| `battle/setup.py` | `scenarios/setup.py` | P5 |
| `battle/skill_contracts.py` | `controllers/graph/skill_contracts.py` | P5 |
| `battle/skills.py` | `controllers/skills.py` | P5 |
| `battle/stats.py` | `records/stats.py` | P5 |
| `battle/suite.py` | split: `benchmark/suite.py`, `reports/statistics.py` | P3,P5 |
| `battle/support_evidence.py` | `battles/support_timing/support_evidence.py` | P5 |
| `battle/support_timing.py` | `battles/support_timing/support_timing.py` | P5 |
| `battle/team.py` | `controllers/team/team.py` | P5 |
| `battle/unit_geometry.py` | `controllers/unit_geometry.py` | P5 |
| `battle/wall_defence.py` | `battles/siege_defence/wall_defence.py` | P5 |
| `battle/wall_facts.py` | `battles/siege_defence/wall_facts.py` | P5 |
| `battle/wall_readings.py` | `battles/siege_defence/wall_readings.py` | P5 |
| `battle/watch.py` | `reports/watch.py` | P5 |
| `engine/`: `__init__.py`, `doctor.py`, `mailbox.py`, `manual_capture.py`, `pack.py`, `runtime.py`, `startup.py`, `windows_capture.py` | stays | - |
| `engine/checkpoint_agent.js` | `checkpoint/checkpoint_agent.js` | P5 |
| `engine/checkpoint_frida.py` | `checkpoint/checkpoint_frida.py` | P5 |
| `engine/link.py` | `multiplayer/link.py` | P5 |
| `engine/multiplayer_adapter.js` | `multiplayer/multiplayer_adapter.js` | P5 |
| `engine/multiplayer_adapter.py` | `multiplayer/multiplayer_adapter.py` | P5 |
| `engine/multiplayer_probe.js` | `multiplayer/multiplayer_probe.js` | P5 |
| `engine/multiplayer_probe.py` | `multiplayer/multiplayer_probe.py` | P5 |
| `engine/worker.py` | `multiplayer/worker.py` | P5 |
| `mod/script/_lib/mod/`: `twwarhammer3_imagery.lua`, `twwarhammer3_json.lua`, `twwarhammer3_ui.lua` | stays | - |
| `mod/script/battle/mod/`: `twwarhammer3_battle.lua` | stays | - |
| `mod/script/frontend/mod/`: `twwarhammer3_frontend.lua` | stays | - |

### `src/gameai/` and `src/spire/`

Paths are relative to `src/`. `gameai/` gains `games.py` (decision J34), a new file with no row. No
Spire file changes (decision J17).

| Today | After | Phase |
|---|---|---|
| `gameai/`: `__init__.py`, `ledger.py`, `llm.py`, `lm.py`, `provenance.py`, `providers.py`, `sft.py`, `windows.py`, `windows_game.py` | stays | - |
| `spire/`: `__init__.py`, `__main__.py`, `decisions.py`, `policies.py`, `protocol.py` | stays | - |
| `spire/combat/`: `__init__.py`, `catalog.py`, `catalog_report.py`, `evaluation.py`, `evidence.py`, `report.py`, `rollout.py` | stays | - |
| `spire/engine/`: `__init__.py`, `bridge.py`, `doctor.py`, `runtime.py`, `windows_relay.py` | stays | - |
| `spire/fullrun/`: `__init__.py`, `digest.py`, `export.py`, `llm.py`, `play.py`, `replay.py`, `rule_data.py`, `rules.py`, `stats.py`, `watch.py` | stays | - |
| `spire/language/`: `__init__.py`, `demonstrations.py`, `evaluation.py`, `policy.py`, `rl.py`, `sampling.py`, `training.py` | stays | - |
| `spire/openweight/`: `__init__.py`, `dynamics.py`, `env.py`, `evaluate.py`, `grpo.py`, `policy.py`, `remote.py`, `rewards.py`, `rollout.py`, `tasks.py` | stays | - |
| `spire/ppo/`: `__init__.py`, `learning.py`, `training.py` | stays | - |

### `scripts/`

No file under `scripts/` moves (decision J28). The edits each script needs are in the note column of
the TSV file.

| Today | After | Phase |
|---|---|---|
| `scripts/`: `audit_language_training.py`, `audit_ppo_training.py`, `check.py`, `diagram_examples.py`, `diagram_files.py`, `export_relabel_datasets.py`, `inventory_scenarios.py`, `offline_agreement.py`, `plot_results.py`, `refusal_sweep.py`, `sft_smoke.py`, `train_language.py`, `train_language_rl.py`, `wh3_db.py`, `wh3_gcp.py`, `wh3_lobby_readback.py`, `wh3_queue.py`, `wh3_reserve_cells.py` | stays | - |
| `scripts/gcp/`: `cleanup.yaml`, `windows-bootstrap.ps1` | stays | - |
| `scripts/githooks/`: `pre-commit` | stays | - |
| `scripts/hooks/`: `pre_bash.py`, `stop_check.py` | stays | - |

### `tests/`

Under the recommended options no file under `tests/` changes path (decisions J16 and J17), so each
destination below is the folder the files are in today. The table after the list gives the
destinations of the other options.

- **`tests/` top level** (rule: repository tests and the plants file stay; 10 files): `README.md`,
  `plants.toml`, `test_agent_sync.py`, `test_check_isolation.py`, `test_check_script.py`,
  `test_diagram_examples.py`, `test_doc_links.py`, `test_hooks.py`, `test_refusal_sweep.py`,
  `test_repo_rules.py`.
- **`tests/gameai/`** (rule: stays; 7 files): `test_goal_transport_timeout.py`, `test_ledger.py`,
  `test_model.py`, `test_provenance.py`, `test_providers.py`, `test_sft.py`, `test_windows.py`.
- **`tests/spire/`** (rule: stays; 4 files): `spire_messages.py`, `test_decisions.py`,
  `test_protocol.py`, `test_rule_policy.py`.
- **`tests/combat/`** (rule: Spire's folder, stays; 14 files): `catalog_support.py`,
  `combat_evidence.py`, `combat_support.py`, `test_catalog.py`, `test_catalog_cli.py`,
  `test_catalog_report.py`, `test_engine_regressions.py`, `test_evaluation.py`, `test_evidence.py`,
  `test_inventory.py`, `test_inventory_engine_regressions.py`, `test_report.py`, `test_rollout.py`,
  `test_rollout_lifecycle.py`.
- **`tests/engine/`** (rule: Spire's folder, stays; 3 files): `test_bridge.py`, `test_doctor.py`,
  `test_runtime.py`.
- **`tests/fixtures/`** (rule: Spire's folder, stays; 2 files): `engine_inventory_transitions.json`,
  `engine_starter_transitions.json`.
- **`tests/fullrun/`** (rule: Spire's folder, stays; 11 files): `conftest.py`, `fullrun_support.py`,
  `test_digest.py`, `test_export.py`, `test_llm.py`, `test_play.py`, `test_play_stops.py`,
  `test_replay_run.py`, `test_spire_cli.py`, `test_stats.py`, `test_watch.py`.
- **`tests/language/`** (rule: Spire's folder, stays; 14 files): `demonstration_support.py`,
  `language_policy_support.py`, `language_training_support.py`, `test_catalog_language.py`,
  `test_demonstrations.py`, `test_language_audit_source.py`, `test_language_cli.py`,
  `test_language_evaluation.py`, `test_language_policy.py`, `test_language_rl.py`,
  `test_language_sampling.py`, `test_language_training.py`, `test_language_training_audit.py`,
  `test_sft_smoke.py`.
- **`tests/openweight/`** (rule: Spire's folder, stays; 1 files): `test_openweight.py`.
- **`tests/ppo/`** (rule: Spire's folder, stays; 6 files): `ppo_training_support.py`,
  `test_learning.py`, `test_neural_evaluation.py`, `test_training.py`, `test_training_audit.py`,
  `test_training_cli.py`.
- **`tests/twwarhammer3/team/`** (rule: stays; 11 files): `check_wh3_team.py`,
  `test_wh3_graph_team.py`, `test_wh3_local_script_recovery.py`, `test_wh3_local_scripts.py`,
  `test_wh3_local_team.py`, `test_wh3_local_topology.py`, `test_wh3_model_team.py`,
  `test_wh3_team.py`, `test_wh3_team_ownership.py`, `test_wh3_team_recount.py`,
  `wh3_team_fixtures.py`.
- **`tests/twwarhammer3/graph/`** (rule: stays; 14 files): `check_wh3_graph.py`,
  `check_wh3_graph_goal_view.cjs`, `check_wh3_graph_view.cjs`, `test_wh3_graph_author.py`,
  `test_wh3_graph_goal_configuration_guards.py`, `test_wh3_graph_goal_factory.py`,
  `test_wh3_graph_goal_view.py`, `test_wh3_graph_goals.py`, `test_wh3_graph_initiation.py`,
  `test_wh3_graph_live_check.py`, `test_wh3_graph_skill_contracts.py`, `test_wh3_graph_view.py`,
  `wh3_graph_author_support.py`, `wh3_graph_goal_support.py`.
- **`tests/twwarhammer3/checkpoint_siege/`** (rule: stays; 18 files): `assault.lua`, `build.lua`,
  `cast.lua`, `field.lua`, `gate_exit.lua`, `gate_observer.js`, `ground_fire.lua`, `live_units.lua`,
  `lobby.py`, `reading.lua`, `test_wh3_siege_capture_reading.py`,
  `test_wh3_siege_checkpoint_states.py`, `test_wh3_siege_comparison.py`,
  `test_wh3_siege_ground_fire.py`, `test_wh3_siege_saved_evidence.py`,
  `test_wh3_siege_saved_spell_witness.py`, `test_wh3_siege_source_builds.py`,
  `test_wh3_siege_spell_witness.py`.
- **`tests/twwarhammer3/prompts/`** (rule: stays; 5 files): `commander.txt`, `evacuation_mode.txt`,
  `llm.txt`, `llm_opening.txt`, `team_member.txt`.
- **`tests/twwarhammer3/` top level, other files** (rule: live checkers, browser programs, the demo
  generator and the helper modules stay; 17 files): `check_wh3_army_setup.py`,
  `check_wh3_benchmark_report_browser.cjs`, `check_wh3_checkpoint.py`,
  `check_wh3_checkpoint_siege.py`, `check_wh3_owner_tags_browser.cjs`,
  `check_wh3_report_browser.cjs`, `check_wh3_restored_episode.py`,
  `check_wh3_scripted_screen_browser.cjs`, `check_wh3_suite_browser.cjs`,
  `check_wh3_suite_comparison_browser.cjs`, `make_wh3_report_demo.py`, `wh3_ablation.py`,
  `wh3_fixtures.py`, `wh3_graph_fixtures.py`, `wh3_helmgart.py`, `wh3_lua.py`,
  `wh3_siege_attack.py`.
- **`tests/twwarhammer3/` top level, test files** (rule: stays; 118 files; the prefix `test_wh3_`
  and the suffix `.py` are left out): `army_check`, `audit`, `battle_budget`, `battle_lua`,
  `benchmark_guards`, `benchmark_outcome`, `benchmark_visual`, `calibration`, `camp`,
  `camp_readings`, `candidates`, `cannae`, `cannae_support`, `capture`, `checkpoint`,
  `checkpoint_agent`, `checkpoint_boundaries`, `checkpoint_guards`, `checkpoint_records`,
  `checkpoint_rl`, `cli`, `comm_intermediate`, `commander`, `configured_guards`, `confirm`,
  `controllers`, `db`, `digest`, `doctor`, `escalade`, `escalade_feedback`, `escalade_readings`,
  `evacuation`, `evade`, `eval_boundary`, `evidence_rules`, `exact_stats`, `export`,
  `foreknowledge`, `gcp`, `graph`, `graph_configured`, `harder_force`, `imagery_lua`, `json`,
  `land_eval_declarations`, `land_live_values`, `lines`, `lines_contacts`, `lines_readings`, `link`,
  `llm`, `lobby_readback`, `local_command`, `local_intervention_guard`, `local_schema`, `mailbox`,
  `mailbox_transitions`, `manual_demo`, `mirror_benchmark`, `mirror_cannon_profile`,
  `mirror_enemy_ai`, `mirror_started_attempt`, `mirror_toggle_readback`, `mod_scripts`,
  `multiplayer_adapter`, `multiplayer_click_probe`, `multiplayer_deployment_probe`,
  `multiplayer_probe`, `native_lua`, `native_peers`, `pack`, `peers`, `play`, `play_capture`,
  `play_wall_cap`, `private_record`, `prompts`, `protocol`, `queue`, `reference`,
  `register_identity`, `replay`, `replay_schedule`, `report`, `report_comm_arms`, `report_html`,
  `report_local_controls`, `reserve`, `reserve_cells`, `reserve_v2`, `restored_episode_check`, `rl`,
  `runtime`, `scenario_status`, `scripted`, `setup`, `siege_assault`, `skills`, `startup`, `stats`,
  `suite`, `suite_accounting`, `suite_page`, `suite_timer_measures`, `support_measurements`,
  `support_public_copies`, `support_timing`, `support_translation`, `ui_requests`, `version_review`,
  `wall_defence`, `wall_readings`, `watch`, `waves`, `windows_capture`, `wing_horse`, `worker`.

Under J16 option (b) 109 of the 118 flat WH3 test files and 7 helper files would move as follows;
the other 9 test files stay at the top level: seven test a root module, `__main__.py` or a live
checker beside them or find `prompts/` beside themselves, and a scenario declaration names
`test_wh3_siege_assault.py` and `test_wh3_waves.py` by path. Under J17 option (b) the seven Spire
folders would move to `tests/spire/<folder>/`. `*` marks a file that `docs/agreed-checks.md` names
and `?` a placement to confirm from the file's imports.

| Destination under `tests/twwarhammer3/` (J16 option b) | Files |
|---|---|
| `support/` (7) | `make_wh3_report_demo.py`, `wh3_ablation.py`, `wh3_fixtures.py`, `wh3_graph_fixtures.py`, `wh3_helmgart.py`, `wh3_lua.py`, `wh3_siege_attack.py` |
| `engine/` (7) | `doctor`, `mailbox`*, `mailbox_transitions`, `pack`, `runtime`, `startup`, `windows_capture` |
| `mod/` (6) | `battle_lua`, `imagery_lua`, `json`, `mod_scripts`, `native_lua`?, `ui_requests`? |
| `multiplayer/` (8) | `link`, `multiplayer_adapter`, `multiplayer_click_probe`, `multiplayer_deployment_probe`, `multiplayer_probe`, `native_peers`, `peers`, `worker` |
| `checkpoint/` (9) | `audit`, `candidates`, `checkpoint_agent`, `checkpoint_boundaries`, `checkpoint_guards`, `checkpoint_records`, `checkpoint_rl`, `confirm`, `rl` |
| `scenarios/` (9) | `evacuation`?, `foreknowledge`?, `land_eval_declarations`?, `mirror_cannon_profile`, `mirror_toggle_readback`?, `reserve`, `reserve_v2`, `scenario_status`, `setup` |
| `records/` (3) | `benchmark_outcome`*, `register_identity`, `stats` |
| `controllers/` (10) | `battle_budget`, `calibration`, `commander`, `configured_guards`, `controllers`*, `evade`, `llm`, `reference`, `scripted`, `skills` |
| `team/` (6) | `comm_intermediate`?, `harder_force`?, `local_command`, `local_intervention_guard`, `local_schema`, `wing_horse` |
| `graph/` (2) | `graph`*, `graph_configured`*? |
| `battles/` (3) | `eval_boundary`?, `evidence_rules`, `replay_schedule` |
| `battles/camp/` (2) | `camp`, `camp_readings` |
| `battles/lines/` (3) | `lines`, `lines_contacts`, `lines_readings` |
| `battles/siege_defence/` (2) | `wall_defence`, `wall_readings` |
| `battles/siege_attack/` (3) | `escalade`, `escalade_feedback`, `escalade_readings` |
| `battles/cannae/` (2) | `cannae`, `cannae_support` |
| `battles/support_timing/` (4) | `support_measurements`, `support_public_copies`, `support_timing`, `support_translation` |
| `run/` (6) | `capture`, `manual_demo`, `play`*, `play_capture`, `play_wall_cap`, `private_record`? |
| `reports/` (11) | `benchmark_visual`, `digest`*, `exact_stats`, `export`, `replay`, `report`, `report_comm_arms`, `report_html`, `report_local_controls`, `suite_page`, `watch` |
| `benchmark/` (7) | `benchmark_guards`?, `mirror_benchmark`*?, `mirror_enemy_ai`*?, `mirror_started_attempt`, `suite`, `suite_accounting`, `suite_timer_measures` |
| `scripts/` (6) | `db`, `gcp`, `lobby_readback`, `queue`, `reserve_cells`, `version_review` |

### `configs/`

- **`configs/llm/`** (rule: stays; 2 files): `monsters.json`, `system_prompt.md`.
- **`configs/suites/`** (rule: stays; 2 files): `louse_diagnostic_development_v1.json`,
  `starter_three_encounter_development_v1.json`.
- **`configs/twwarhammer3/`** (rule: stays; 15 files): `benchmark_jobs.json`,
  `cannae_shared_plan.md`, `cannae_shared_plan_v2.md`, `commander_prompt.md`, `custom_battle.json`,
  `gcp-regions.json`, `graph_goal_prompt.md`, `local_captain_prompt.md`, `local_command_prompt.md`,
  `local_commander_prompt.md`, `local_topology_rules.json`, `report_notes.json`, `rules_prompt.md`,
  `system_prompt.md`, `tips_prompt.md`.
- **`configs/twwarhammer3/controllers/`** (rule: stays; 19 files): `cannae-local-concentrate.json`,
  `cannae-local-model.json`, `cannae-local-probe.json`, `cannae-local-rush-think.json`,
  `cannae-local-rush.json`, `cannae-local-schedule.json`, `cannae-local-slow-probe.json`,
  `cannae-muted-overview-witness.json`, `cannae-muted-witness.json`, `cannae-overview-model.json`,
  `cannae-overview-probe.json`, `cannae-overview-witness.json`, `cannae-peer-model.json`,
  `cannae-peer-probe.json`, `cannae-peer-witness.json`, `cannae-relay-model.json`,
  `cannae-relay-probe.json`, `cannae-relay-witness.json`, `cannae-unlinked-model.json`.
- **`configs/twwarhammer3/graphs/`** (rule: stays; 6 files): `contact-cavalry.json`,
  `contact-goals-team.json`, `contact-line.json`, `contact-ranged.json`, `contact-team.json`,
  `suite-gap.json`.
- **`configs/twwarhammer3/scenarios/`** (rule: stays; 11 files): `air_relief.json`, `camp.json`,
  `cannae.json`, `harness.json`, `lines.json`, `mirror.json`, `retired.json`, `siege_attack.json`,
  `siege_defence.json`, `suite.json`, `support_timing.json`.

## Limits

**Read and not run.** Nothing on this page was implemented or tried on a branch. No game was
started, no paid model call was made, and `scripts/check.py` was not run in the main checkout. For
the first draft I read the four designs and the three judges' reports in full, the path-identity
inventory in full, the summaries and problem lists of the other ten maps, `layers.txt`, and the code
lines cited where a claim decides a choice. For the revision of 2026-11-16 I read the six check
reports in full and rechecked each finding against the code or the source before it changed the
page; `runs/restructure-plan-20261115/verify/revision.md` lists every finding, whether it held and
what changed. I did not reread the other ten maps in full. For the first draft I did not open the
reference clones; in the revision I opened the lines behind the reference check's major findings and
the lines marked "opened" in section "References". The other reference paths and reading depths are
the research reports'. No outside reference backs the naming rules, the move tool and statement
accounting (K3, K4), an alias from an old name to current code, the scope module or C10. Whether
Import Linter counts function-level imports was not established (J33).

**What I ran.** For the first draft: counts over the register and `tests/plants.toml` with
`python3 -I`; `grep` counts of the importers of `scripted.py` and of the three file-name literals;
`sha256sum` of `cannae.py` and `evade.py`; a comparison of today's graph library digest and pack
hash with every saved value under `runs/` (it imported `graph_author` and `engine.runtime` with
`.venv/bin/python -B` and wrote nothing). For the revision: the file-map check's four scripts on the
revised map, with the revised map typed as data in `verify/file-map/plan.py` and the checker's own
versions kept beside them; the same scripts on the map with the five optional splits; `edges.py`
with the revised placement; `python3 -I` recounts of plants, marker references, Code map entries,
Markdown links and controller classes; `python -X importtime` on `twwarhammer3.protocol`; and, in
this page's worktree, `uv run --locked pytest -q tests/test_doc_links.py tests/test_repo_rules.py`
(130 passed, none failed or skipped). For the corrections after the second reading: the recounts
that `recheck/corrections.md` records, and the same two test files on the corrected page.

**Unverified.** Nothing on this page is verified. In particular it is not shown that the K checks
can be built as described and are stable (K6 for team controllers above all), that each cut is
verbatim, or that the game launches after the move. The import table was applied to the revised map
at the level of single uses of a name, function-level imports counted, after P3, after P5 and with
the five optional splits; it found no break and the cycle groups this page lists. Classes loaded
from strings, tests and scripts are outside that check, an import line left behind with no use is
not counted, and the check did not model the `layout` imports that C5 adds. Three second readers
then read the revised page (consistency, numbers, evidence and markers; their reports are in
`recheck/`), and one agent applied their confirmed findings as corrections without a design change
(`recheck/corrections.md`). Nobody has read the corrected page, and the new phase order, the six new
markers and the cuts are still one agent's reading of the six reports.

**Open points from the second reading.** Each needs a design decision, which the correction pass did
not make.

- J3 option (a) does not say which merge carries the entry into `docs/agreed-checks.md`, since P0
  changes no tracked file, nor whether K6, K3 and the table part of K9 join it by an owner-approved
  edit or as a second entry.
- P2 and P3 change controller files, and no decision replay runs before K6 is built for P5a. The
  page does not fix K6's base; only a base at the commit P1 starts from would replay the edits of P2
  and P3.
- K4 does not look at import lines. After P3 two different sets are named `OUT` (five states in
  `units.py`, two in `skills.py`), and a module that imports the wrong one (`unit_geometry.py`,
  `reference.py`, `skill_contracts.py`) passes the named checks; whether a unit test catches it was
  not established.
- C7 puts hand edits, new `__init__.py` docstrings, a battles test, rewritten plant texts and the
  changed walk of R4 into the commit that K3 must reproduce from the table alone. Whether these
  become a second commit or inputs of the tool is not decided.
- The page does not say by which pattern the move tool and P1's reference test find a marker
  reference. With the gate's pattern they miss 33 of the 102 references that the move changes.
- P3 puts the import table of J13 option (a) in force before J13 is asked, and makes two cuts that
  only (a) needs. The page gives no reduced form of P3 for an owner who wants another option.
- J23 option (a) puts a module cut from one of the six files on the no-marker list. It does not say
  whether that covers `units.py` and `wording.py`, which P3 cuts from three of the six and which
  hold no controller class.
- K7 fails on any difference, and a live checker's recount holds the checker's own file hash, which
  changes whenever its import lines do (`tests/twwarhammer3/graph/check_wh3_graph.py:243`); K7 names
  no exception for it. K7 also names no rule that its script writes nothing into evidence, which has
  no backup.
- C3 does not say how `play.py` reaches `SOURCES` after P2. Three live checkers and the pinned saved
  checker keep running unedited only if it imports the name from `scope.py`.
- The pinned saved checker asserts that a `graph_llm` member's card `version` equals
  `graph_goals.VERSION` (its line 100). C2 does not say whether that field keeps its meaning after
  P5a.
- J36 option (b) says that P3 waits for J1. It does not say whether P2's edits to `controllers.py`
  and `local_team.py` wait as well.
- C5 leaves the literal at `engine/manual_capture.py:72`, because R3 lets `engine` import root
  modules only and `layout.py` belongs to `records`. Making `layout.py` a root module in its place
  was not weighed.

**Counts that are lower bounds or local.** 1,594 results, 482 job folders, 347 artifact manifests
and 25 files with a pack hash are this machine's `runs/`; evidence kept elsewhere is not covered.
Import-line and class-path counts are regex matches. Test-line counts leave out
`from module import name` lines. "About 286 plants" is 275 under `battle/` after P3 and 11 on the
engine files that move. The class counts apply `controller_class`'s own test to every module-level
class of the imported package (`recheck/numbers-scripts/classes_live.py`). The load time of
`twwarhammer3.protocol` differed between runs (30 to 99 ms); only the share of the model API module
is used here. The co-change counts follow file history by path inside `battle/` only; the two checks
that recounted them differ by one commit (344 and 343). The game hours of the live reruns and the
size and run time of the check scripts were not estimated. No study measured that sub-packages,
mirrored tests or a shorter reading route improve an agent's results (agent-friendly research note,
sections 3 and 4). What can be shown afterwards is narrower: no forbidden import, the number of
modules each reader loads, counted before and after (no count was made for the target tree), and the
two routes of C7's table, which get longer. Scenario entries are not edited; the two test paths they
name stay under every option (C9).

**Where the designs and judges disagreed, and what this page does.**

| Point | Positions | Here |
|---|---|---|
| Base design | clean-slate ranked first by two judges, agent-first by one | clean-slate's root modules and package set; agent-first's identity defaults and move method |
| Old and new register rows | clean-slate and harness-shaped pool by default; the evidence judge showed that this merges groups kept apart today | label only (J2) |
| Class paths in the 13 controller files | clean-slate rewrites them; the other three keep them | kept, resolved through aliases |
| Graph library load rule | the evidence judge wanted it decided before the first byte change; the simplicity judge found that no saved artifact loads today | rule unchanged (J26) |
| Listing "needs your yes" items | the evidence judge wanted the gate to print every item; the simplicity judge wanted no gate change | a script writes the full list; the gate is unchanged (J4) |
| Pins | clean-slate asks a yes for every controller file's hash; the simplicity judge called that too much | no pins file; K8 compares the values during the restructure (J10) |
| Existing tests | simplicity judge: move none; daily-work judge: all or none; clean-slate: old flat, new in folders | none, with the import cleanup of C9 (J16) |
| Guidance beside the code | daily-work judge for it, with a fingerprint skip; the other two against, because of the Spire audit | one docs page (J20) |
| Spire | simplicity judge: nothing; daily-work judge: a small set | nothing (J17) |
| Trace reader, loaders, `readings` command, launch helper | daily-work judge: take them; the other two: outside a restructure | trace reader and launch helper as later cards (J29, J30); `readings` not planned |
| Display names in a registry row | daily-work judge and harness-shaped for it | labels stay in `report_html.py`, a presentation file, so a label edit starts no new test setup |
| Number of packages | the simplicity judge noted two-module packages; the daily-work judge preferred this set | ten (J13) |

**What the six checks changed.** Cut from the first draft: `registry.BATTLES` and `RETIRED`;
`records/schema.py`; the pins file; `spire/scope.py` and every other Spire edit;
`controller_call.py`; `rl_recount.py`; `run/config.py`; the merge of `unit_geometry.py` into
`units.py`; the move of `gcp-regions.json`. Made optional and recommended against: five splits (J15)
and the test move (J16). Moved earlier: the four cuts that remove a wrong-way import, and R3 itself,
from after the move into P3. Moved later: declared controller names, from P2 to just before the
move, so that P0 to P4 wait for no identity decision. Corrected: the count of test-setup boundaries,
the date from which live passes fall behind, the summary key in J1 and J2, the registry's size, the
direction of Fowler's advice, the co-change counts, and the smaller numbers and citations that
`verify/revision.md` lists. Where a checker's finding did not hold or its fix was not taken, that
file says why.

**What the second reading changed.** Corrected numbers: the controller classes (84 and 81), the
marker references and import lines at the move (102, and 219 in 131 files), the test lines of P2 and
P3 (145 and 60), the reference lines of P3's markers, the job-file literals (77 lines in 19 files),
and the smaller ones that `recheck/corrections.md` lists. Corrected statements: P7 is recommended
and has its own question; J16, J29 and J30 need an answer before their change is made; J33 and J36
are asked before P2, which lands R2 and already changes two controller files; one reader does
compare a card hash; no live entry has a pass at today's HEAD. The texts of nine markers were
corrected (J3, J4, J8, J14, J15, J25, J31, J32, J36). One cell of the file map changed
(`battle/controllers.py`, phase `P2,P5a,P5`). No change, phase or recommended option was added,
removed or reversed; the points that would need one are under "Open points from the second reading".

**Where this page departs from the planning workflow's starting view**, each on the judged
evidence: `gameai` is not split by job (all four designs and all judges keep its files, because
pinned Spire files import them); `scripts/` is not grouped (J28); registers and generated files
stay under `docs/`; `__main__.py` and `report_html.py` are not split by job; live checkers and
browser programs stay in the test folders; the launch sequence gets one module only after the plan
(J30); under the recommended J7 a fingerprint does not survive a phase; the Lua is not split,
because only a live game can check a split; of the four import cycles one is removed, one shrinks
to a listed pair and two stay listed.

**Questions this page leaves open.** What observable, beyond the two routes of C7, would show the
move was worth its cost. Who notices a missed version bump once K6's scripts are gone. What happens
to register rows appended on the two parked branches. How long the check scripts take to build and
to run.

## References

The outside sources this page cites. Clones are under `runs/restructure-plan-20261115/refs/` unless
another place is given; nothing in them was executed. Paths and reading depths are the research
reports' (`runs/restructure-plan-20261115/research/*.md`); the author of this page did not open the
clones for the first draft. "Opened" marks lines that were read in the clone during the revision.
The same sources are listed in [references.md](references.md#restructuring-plan-2026-11-15).

| Source | Repository and commit | Files cited on this page | Depth |
|---|---|---|---|
| Harbor | `harbor-framework/harbor`, `ec6aeab` (2026-11-13) | `src/harbor/agents/factory.py:62-164`; `src/harbor/models/trial/paths.py`; `src/harbor/models/README.md`; `AGENTS.md:43-139`; `src/harbor/agents/base.py`; `src/harbor/trial/`; `tests/unit` | `factory.py`, `paths.py` and `AGENTS.md` fully; `base.py` lines 1-200 and 620-745; `tests/` listed and counted |
| Inspect AI | `UKGovernmentBEIS/inspect_ai`, `59c1340` (2026-11-15) | `src/inspect_ai/log/_file.py:530-647`; `log/_log.py:1325-1386`; `_util/registry.py`; `_util/deprecation.py`; `AGENTS.md` | `registry.py` and `AGENTS.md` fully; `_file.py` lines 530-650; `deprecation.py` lines 1-120; `_log.py` in part, line 1325 opened |
| Inspect Evals | `UKGovernmentBEIS/inspect_evals`, `3034895` (2026-11-16) | `src/inspect_evals/gpqa/`; `adr/0001-eval-metadata-location.md` | `__init__.py`, `eval.yaml` and `gpqa.py` fully; the ADR's first lines opened |
| SWE-bench | `SWE-bench/SWE-bench`, `02e7a74` (2026-09-02) | `swebench/harness/log_parsers/python.py:275-289`; `harness/run_evaluation.py:254`, `:588-594`; `task/checks.py:72-158`; `CHANGELOG.md:34` | `run_evaluation.py` and `checks.py` fully; `log_parsers/python.py` skimmed (three ranges); the changelog line opened |
| Gymnasium | `Farama-Foundation/Gymnasium`, `68c3f95` (2026-11-12) | `gymnasium/envs/registration.py:72-115`, `:254`, `:533-546`; `gymnasium/envs/__init__.py:195-376`; `gymnasium/core.py:268-276`; `tests/testing_env.py`; `envs/mujoco/` | `registration.py` in part (lines 1-140, 254-320, 371-470, 488-660, 676-843); `testing_env.py` lines 1-80; `mujoco_env.py` first 60 lines and the rest of the folder listed; the cited `registration.py` and `core.py` lines opened |
| PettingZoo | `Farama-Foundation/PettingZoo`, `e767786` (2026-11-10) | `pettingzoo/classic/tictactoe/`; `pettingzoo/utils/deprecated_module.py:20-48` | `tictactoe.py` lines 60-112; the folder listed; `deprecated_module.py` lines 20-26 opened |
| SMAC | `oxwhirl/smac`, `d6aab33` (2024-02-18) | `smac/env/multiagentenv.py`; `smac/env/starcraft2/starcraft2.py:316-394`, `:1478-1484` | `multiagentenv.py` fully; `starcraft2.py` lines 1-130, 180-560, 1478-1510, 1634-1707 |
| CARLA Leaderboard | `carla-simulator/leaderboard`, `cfecdc8` (2025-03-06), branch `leaderboard-2.1` | `leaderboard/scenarios/route_scenario.py:271-292`; `leaderboard/autoagents/agent_wrapper.py:121-139`; `leaderboard/autoagents/autonomous_agent.py:32-132` | the first two fully; the class header of the third opened |
| Transformers | `huggingface/transformers`, `cf13eb9` (2026-11-16), sparse clone | `Makefile:13-38`; `tests/repo_utils/test_check_repo.py`; `utils/check_dummies.py:195-256` | `check_dummies.py` docstring, config and `check_dummies`; the script and test counts and lines 244-246 opened |
| Import Linter | `seddonym/import-linter`, `b2d4938` (2026-11-13) | `.importlinter`; `docs/contract_types/index.md:66-70` | contracts read; the docs lines opened |
| graph-as-policy | `graph-robots/graph-as-policy`, `71549e1` (2026-10-19), clone in `runs/gap-plan-20261031/` | `tests/agent_skill/test_cli_reference_fresh.py` | lines 1-30 |
| open-robot-skills | `graph-robots/open-robot-skills`, `752dfbd` (2026-09-12), clone in `runs/gap-plan-20261031/` | `tests/test_promotion_is_behaviour_preserving.py:36-119` | fully |
| Parnas, "On the Criteria To Be Used in Decomposing Systems into Modules" | CACM 15(12), 1972; saved as `refs/principles/parnas-1972-cacm.txt` | "The Criteria"; Conclusion | fully |
| Martin, "Design Principles and Design Patterns" | 2000; saved as `refs/principles/martin-design-principles-2000.pdf` and `.txt` | pages 17 to 24 | those pages; the rest not read; two lines of the text opened |
| Ousterhout, CS 190 lecture notes | Winter 2018; saved as `refs/principles/ouster-cs190-modularDesign.html` | lines 98-104, 250 | that page fully; the book mostly not read; the lines opened |
| Fowler, "PresentationDomainDataLayering" | 2015-08-26; saved as `refs/principles/fowler-pdd-layering.html` | lines 335-344 | fully; the lines opened |
| Gloaguen et al., "Evaluating AGENTS.md" | arXiv 2602.11988 v3 (2026-09-29) | section 4.3 | read through a summarising fetch tool; no saved copy |
| McMillan, "Instruction Adherence in Coding Agent Configuration Files" | arXiv 2605.10039 (2026-05-11); text saved under `research/agent-friendly-scripts/` | section 4.1 | abstract, 3.2, 4.1, 5.7-5.8, 6 and the conclusion |

Our own earlier work cited: `runs/terminal-bench-review-20261115/report.md` (the structure
comparison of 2026-11-15, F5 at lines 590-615), `runs/code-quality-20261114/handoff.md`,
`runs/terminal-bench-review-20261115/impl/recount_C.py`, the co-change count
`runs/restructure-plan-20261115/research/cochange.txt` with its script, and the two recounts of it
under `runs/restructure-plan-20261115/verify/`.
