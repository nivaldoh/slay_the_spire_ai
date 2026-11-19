# Earlier restructuring decisions

The [current plan](restructure-plan.md) contains the decisions for the proposed destination.
This record preserves open choices from earlier proposals. Phase numbers and words such as
“today” refer to the dated revision. The owner has not adopted or dismissed these markers.
To read each original proposal, use the Git command beside its group. The second proposal lived
on a local branch. Its Git objects and unfinished edits are backed up under
`runs/restructure-plan-20261115/final/review/` on the evidence machine.

## First proposal

`git show e453429:docs/restructure-plan.md`

**J3**

JUDGEMENT: Verification method — Claude, 2026-11-15, the K checks built for a phase are proposed as
the agreed check "restructure: offline equality". Without an agreed method every phase reports
unverified. Each "passed" statement about K checks in a phase report rests on it.

**J4**

JUDGEMENT: Batch approvals — Claude, 2026-11-15, the owner approves a phase's path-only edits as one
batch, on a table and a script's count of the edits that only rewrite a mapped path. Item-by-item
review is the alternative. About 286 plants, 102 references and 131 test files rest on it.

**J9**

JUDGEMENT?: Missing scope path stops a job — Claude, 2026-11-15, source_fingerprints and
committed_revision raise on a scope path that does not exist. Today such a path matches nothing and
passes. The scope tests and Spire's first-combat tools, which call the same functions, rest on it.

**J10**

JUDGEMENT?: Pinned hashes — Claude, 2026-11-16, no tracked file of pinned hashes is added; K8
compares the pack, agent, graph library and initiation checker hashes at each phase. A tracked file
would show each later change to the owner. What a stale saved value can pass unseen rests on it.

**J1**

JUDGEMENT: Controller identity — Claude, 2026-11-15, a controller is its declared name and version;
its file hash is recorded and not compared. Keeping the module path and hash renames every
class-path controller when its file moves. C7, C8 and the readers' labels and groups rest on it.

**J2**

JUDGEMENT: Old and new rows — Claude, 2026-11-15, the alias table only labels old class-path rows;
they never pool with declared-name rows, and nine old names keep a blank configuration. Pooling
would need a new summary key and merge groups kept apart today. Every rate after P5a rests on it.

**J8**

JUDGEMENT: Names — Claude, 2026-11-15, about 81 declared names of the form battle.role, one per
class a job may name. Another spelling changes the policy column of every later row, and a name is
never reused. The register's policy column and the alias table rest on it.

**J32**

JUDGEMENT: Version bump rule — Claude, 2026-11-16, a newly registered name starts at v1 and its
version changes only when some observation gives other orders. A bump on any byte change of the
controller's file is the alternative. Which rows pool after a controller edit rests on it.

**J12**

JUDGEMENT?: Presentation list — Claude, 2026-11-15, the list names the same files at their new
paths and keeps the nine old prefixes for old manifests; three items start counting. Listing all of
reports/ would stop export.py edits starting a new setup. Figure 1's groups rest on it.

**J34**

JUDGEMENT?: Game process names in gameai — Claude, 2026-11-16, gameai/games.py holds both games'
install folders and process names as data. Each game keeping its own list, with checkpoint.py's
import of spire listed as a known break, is the alternative. The two-games guard rests on it.

**J11**

JUDGEMENT: Provider rules stay in the protocol — Claude, 2026-11-16, policy_call, account_stop and
is_forfeit stay in protocol.py, where commit a69af01 put them on 2026-11-14. Moving them to
controller_call.py would let R3 say the protocol imports no model code. R3's root row rests on it.

**J36**

JUDGEMENT?: Controller files before identity — Claude, 2026-11-16, P2 and P3 change import lines in
most of the 20 controller files before J1 is answered, so their cards' file hashes change. Waiting
for J1 is the alternative. Three evade rows whose hash still matches today's file rest on it.

**J31**

JUDGEMENT?: Recorded hashes after extraction — Claude, 2026-11-16, statements leave scripted.py,
llm.py, commander.py, local_team.py, graph_author.py and report.py, whose hash a card or manifest
records. Leaving them, or hashing the new modules too, is the alternative. Card hashes rest on it.

**J35**

JUDGEMENT?: Root modules before the move — Claude, 2026-11-16, registry.py, scope.py, units.py and
wording.py are created at the package root in P2 and P3, before J13 is asked. Keeping new modules
in battle/ until the move is the alternative. The stop at P4 and the tree it leaves rest on it.

**J33**

JUDGEMENT?: Import rule checker — Claude, 2026-11-16, R2, R3 and R5 are syntax-tree tests in
tests/test_repo_rules.py, as R1 and R4 are today. Import Linter contracts as a development
dependency are the alternative. Whether a plant can target a rule rests on it.

**J19**

JUDGEMENT?: Code map generated — Claude, 2026-11-15, the 100 hand-kept entries for Python modules
are replaced by a list built from module docstrings and checked for freshness. Keeping the list by
hand costs 69 entry edits at the move. The owner's reading page and 22 plants rest on it.

**J20**

JUDGEMENT: Guidance page — Claude, 2026-11-15, one page docs/twwarhammer3/code.md holds the checks,
rules and recipes. Nested AGENTS.md files beside the code would sit inside the play scope, hashed
into every job. The reading route for a WH3 change rests on it.

**J5**

JUDGEMENT: Stop point — Claude, 2026-11-15, P0 to P4 stand alone and leave battle/ flat (no file
moves; benchmark.py is cut in place); the move is a second yes after their report. Approving all
phases now, or stopping for good at P4, are the alternatives. What work comes next rests on it.

**J6**

JUDGEMENT: Package move — Claude, 2026-11-15, all of battle/ and eight engine files move in one
tool-made commit, the six existing battles into folders. Moving only new battles, or no file, keeps
today's flat layout and its approvals. C8 to C10 and the folder form of R3 rest on it.

**J7**

JUDGEMENT: Test setup across the move — Claude, 2026-11-15, the path-keyed fingerprint stays, so
battles before and after the move are two test setups. A declared harness version would let them
share one. Figure 1's controlled comparison and the change-levels table rest on it.

**J13**

JUDGEMENT: Package set — Claude, 2026-11-15, ten sub-packages and five root modules with one
allowed-import table, roles first and battles inside one role. Fewer or more packages, or battles
at the top level, change which edits the gate refuses. The move table and the rule tests rest on it.

**J14**

JUDGEMENT: Battle folder names — Claude, 2026-11-15, a battle's folder takes its scenario file's
name; module stems and page names stay. Renaming stems and pages too gives one name per battle and
breaks each reference that uses a renamed bare name. The battles test and the file map rest on it.

**J21**

JUDGEMENT?: References by path tail — Claude, 2026-11-15, the path edits of the move rewrite each
"rests on" reference as the shortest unique path tail. Keeping root-relative paths costs the same
edits at the next move. How a marker is named in use rests on it.

**J22**

JUDGEMENT?: Module-path commands — Claude, 2026-11-15, the four commands run as python -m <module>
keep that form at their new module paths. Turning them into subcommands changes the command line.
The Stop hook's command list and the commands the docs name rest on it.

**J23**

JUDGEMENT?: No-marker list — Claude, 2026-11-15, check.NO_MARKER and docs/judgement.md keep naming
the same six policy files at their new paths. With J1 the stated reason (the card hash) no longer
applies, so dropping the rule is the alternative. Which files may carry markers rests on it.

**J25**

JUDGEMENT: Saved scripts at their revision — Claude, 2026-11-15, a saved script under runs/ is
rerun in a worktree at the revision its evidence records. Re-exporting modules under battle/ would
keep it running at HEAD. A live agreed check's pinned checker and eight other scripts rest on it.

**J15**

JUDGEMENT?: Further file splits — Claude, 2026-11-16, after the move no further file is split;
setup.py, checkpoint.py, play.py, team.py and controllers.py stay whole. Splitting setup.py alone,
or all five, is the alternative. 23 second plant edits and 581 test lines rest on it.

**J16**

JUDGEMENT: Test folders by package — Claude, 2026-11-16, no test file moves; one pythonpath entry
and a rule test replace the 15 sys.path lines. Moving 109 flat WH3 test files into package folders
is the alternative, as is the tree in docs/testing.md. 323 plant targets rest on it.

**J24**

JUDGEMENT: Live checks after the restructure — Claude, 2026-11-15, each live-checked feature is
unverified at the new revision until its check is rerun in a set the owner picks. Carrying passes
over on the offline checks is the alternative. Which features count as verified rests on it.

**J29**

JUDGEMENT: Shared trace reader — Claude, 2026-11-15, after P3 one module joins decisions to
acknowledgements for all readers; each reader keeps its own rule for a bad line. The owner answered
"Leave as is" on 2026-11-14; keeping the seven loops is that answer. 41 reader plants rest on it.

**J30**

JUDGEMENT: Launch helper — Claude, 2026-11-15, after the plan, one context manager holds the launch
sequence, landed only with one live launch. Leaving the five copies in src and three in checkers
is the alternative. 48 test patches on play.py and every live check rest on it.

**J17**

JUDGEMENT: Spire — Claude, 2026-11-16, no file under src/spire or in Spire's test folders changes
in this plan. A scope.py cut from fullrun/play.py and seven test folders moved under tests/spire/
are the alternative. One agreed-check path and five plant targets rest on it.

**J18**

JUDGEMENT: Cloud prices stay in the play scope — Claude, 2026-11-16, gcp-regions.json stays in
configs/twwarhammer3/ and so in every job's fingerprint, although only scripts/wh3_gcp.py reads it.
Moving it to scripts/gcp/ is the alternative. What a job's source identity covers rests on it.

**J26**

JUDGEMENT?: Graph library rule — Claude, 2026-11-15, the loader keeps refusing an artifact whose
library digest differs. A declared-version rule or an owner-approved list of old digests would let
old artifacts load. Reuse of authored graphs for the suite's gap arm rests on it.

**J27**

JUDGEMENT: Lua untouched — Claude, 2026-11-15, no byte under mod/ changes in this plan and the
battle script stays one file. Splitting it into library files changes the pack hash and can only
be shown in a live game. 16 plants and the Lua tests' loader rest on it.

**J28**

JUDGEMENT?: Scripts stay flat — Claude, 2026-11-15, no file under scripts/ moves. Folders by what
each script serves (code page, WH3 tools, Spire drivers) would group 18 flat files and retarget
their plants. An agreed-check path and the Spire audits' path keys rest on it.

## Second proposal

`git show 3a225ef:docs/restructure-plan.md`

**D1**

JUDGEMENT: Verification method — Claude, 2026-11-16, a commit that only moves code cites the agreed
entry "Test suite rejects its kept wrong versions" and reports the kit's outputs as evidence. A new
agreed entry for the kit, or none, are the alternatives. Each stage report's "passed" rests on it.

**D2**

JUDGEMENT: Package set — Claude, 2026-11-16, the import rules use this page's seven groups and eight
shared root modules. The first version's ten packages are the alternative. Stage 1's import table,
the move table and each way to move the files that is asked with stage 2's report rest on it.

**D3**

JUDGEMENT: Controller identity — Claude, 2026-11-16, under the full move a recorded policy string
stays the name and names.MOVED says where a moved module lives. A registry of declared names is the
alternative and changes the policy column of later rows. Commit 3a and report labels rest on it.

**D4**

JUDGEMENT?: Plant follows its text — Claude, 2026-11-16, the gate stops listing a plant whose only
changed field is file when its old text left that file and arrived in the new one. Listing every
such plant is today's rule. What the owner is asked at stages 2 and 3 rests on it.

**D5**

JUDGEMENT?: Code map upkeep — Claude, 2026-11-16, the Code map's entries for WH3 Python modules
stay written by hand, and two tests keep the list and the code page's file list in step. Building
the entries from module docstrings is the alternative. The owner's reading page rests on it.

**D6**

JUDGEMENT: Guidance page — Claude, 2026-11-15, one page docs/twwarhammer3/code.md holds the checks,
rules and recipes, with one route line in AGENTS.md. AGENTS.md files beside the code are the
alternative and would sit inside the play scope. The reading route for a WH3 change rests on it.

**D7**

JUDGEMENT: Shared trace reader — Claude, 2026-11-16, after stage 2 one module would join a decision
to its acknowledgement and hold the member source-time fallback. The alternative keeps the seven
loops; the owner's "Leave as is" (2026-11-14) was to a narrower question. Reader output rests on it.

**D8**

JUDGEMENT: Live checks after the restructure — Claude, 2026-11-15, each live-checked feature stays
unverified at the new revision until its check is rerun, in a set the owner picks after stage 3.
Carrying passes over on the offline checks is the alternative. Which features count rests on it.

## Interim review

`git show 3378ce4:docs/restructure-review.md`

JUDGEMENT: Track packages — Codex, 2026-11-18, proposes moving checkpoint and multiplayer separately
when those tracks are worked on. Keeping today's locations or regrouping all WH3 modules by role
changes which compatibility work pays off. The target tree and the two move cards rest on this choice.

JUDGEMENT: First restructuring changes — Codex, 2026-11-18, proposes a targeted readings check
and one parser extraction. The alternative starts with the second draft's package-wide import
rules and exception lists. The first two implementation cards depend on this ordering.

JUDGEMENT: Restructuring evidence — Codex, 2026-11-18, proposes the existing gate plus comparisons
of the exact inputs and consumers touched by each card. A whole-corpus replay is the alternative
for broader changes. The owner decides what evidence establishes correctness at a revision.

<details>
<summary>Original references to other owner decisions</summary>

These excerpts preserve the first proposal’s links between decisions. Each number is a
line in `e453429:docs/restructure-plan.md`. Phase names and counts belong to that revision.

```text
L10–12
why." And the same day: "Let's be open to any type of structure for now, without restricting
ourselves to previous decisions. Use JUDGEMENT calls in the document so I can decide whether we will
move forward with relevant changes or not." Nothing on this page is implemented. Every choice below

L107–107
| J19 | Code map generated | Are the three hand-kept file lists built from docstrings? | (a) built and tested for freshness; (b) kept by hand | The wording the owner reads becomes the docstrings'; replaces the format under `JUDGEMENT?` One file per line (Claude Code, 2026-11-01) | P4; C6 |

L109–109
| J1 | Controller identity | What names a controller in a result? | (a) a declared name and version, hash recorded; (b) the module path and file hash, as today | Needed before a file moves; settles `JUDGEMENT?` Witness hash ("Decide later", 2026-11-15) | P5a, P5; C2 |

L110–110
| J2 | Old and new rows | Do old class-path rows pool with declared-name rows? | (a) no, the alias table only labels; (b) pool approved pairs, keyed on the declared version; (c) pool all | None; (b) and (c) change `JUDGEMENT?` Summary identity (Claude, 2026-11-05), never asked | every rate after P5a; C2 |

L123–123
| J16 | Test folders by package | Do the flat WH3 test files move into package folders? | (a) none, one `pythonpath` entry and a rule test; (b) 109 files move | One `pyproject.toml` line in both games' scopes; differs from `JUDGEMENT` Test layout (Codex, 2026-10-23) | P7; C9 |

L492–495
- Today: the gate lists every changed plant and agreed file and the first three marker and assert
  lines. Batches of 5, 11 and 23 path-only edits were approved on 2026-11-14 and 2026-11-15
  ([owner-direction.md](owner-direction.md)). What the gate lists for an agreed file is itself a
  marked rule: this option rests on JUDGEMENT? `scripts/check.py` Agreed-check edits.

L679–682
keep working only while `controllers.py` still imports those names. A name can never be reused for
other behaviour. This change rests on JUDGEMENT? `src/twwarhammer3/battle/controllers.py` Witness
hash and rests on JUDGEMENT? `src/twwarhammer3/battle/stats.py` Summary identity; only the owner
removes or rewords those two markers.

L727–729
- (a) changes no existing group. (b) and (c) pool nothing unless `stats.conditions` changes too,
  which is a change to `JUDGEMENT?` Summary identity; (c) also rests on the 2026-11-14 cleanup's own
  statement that it changed no behaviour.

L787–790
**Cost.** One plant sits on the moved lines (`report_html.py:45`); 24 plants name `play.py`. 48 test
patches name `battle/play.py`, among them `source_fingerprints` and `committed_revision`. The marker
`JUDGEMENT?` Test setup moves with its lines; one reference names it at the old path, the last
sentence of this paragraph, and follows. Three items change status. The list itself leaves

L796–798
files and the pinned checker stops at P2 (J25). The three new modules each need a Code map entry by
hand until P4 (C4, Docs). The list's membership rests on JUDGEMENT?
`src/twwarhammer3/battle/report_html.py` Test setup.

L1021–1023
- The hash a loader does compare, the graph library digest, keeps its cover: the four constants it
  would have lost stay in `skills.py`. This question rests on JUDGEMENT?
  `src/twwarhammer3/battle/controllers.py` Witness hash.

L1099–1103
**Today.** The last group of "What is wrong today". The Code map's format is Claude Code's
undecided call of 2026-11-01 (`JUDGEMENT?` One file per line,
`docs/twwarhammer3/README.md:205-207`); `scripts/diagram_files.py` reads the map and writes the
tracked `docs/how-code-works-files.js`, and nothing compares that file with a fresh run. All 132
modules under `src/` have a docstring; for 29 the first line runs on to the next (17 in `battle/`).

L1137–1139
**Cost.** 22 plants name `diagram_files.py`. The Code map is the owner's page for reading the code,
and its wording becomes the docstrings'. One line in the root `AGENTS.md`, the owner's rule file.
This change rests on JUDGEMENT? `docs/twwarhammer3/README.md` One file per line.

L1247–1250
  33 at a path that no longer exists, and no check fails. 82 lines outside the logs hold the word
  JUDGEMENT and a moving path, and the gate lists each of them that is edited
  (`scripts/check.py:523-526`). This page holds four more references to moving files, which follow
  too.

L1550–1552
  already edited; 14 of its placements are marked to confirm. Pass records are keyed by an entry's
  title, so their history would continue; that rests on JUDGEMENT? `scripts/check.py` Pass at a
  revision. Under either option `test_wh3_siege_assault.py` and `test_wh3_waves.py` stay where they

L1657–1663
Rules for every phase. Work is done in the agent's own worktree and branch; one phase is one
reviewed merge, and the owner is asked before each merge and push to `main`. Nothing lands in the
main checkout while a WH3 queue runs, because any HEAD move stops it (`scripts/wh3_queue.py:51-56`).
Both rules rest on JUDGEMENT? `docs/workflow.md` Worktree details. A phase that touches a play scope
(`src/gameai`, `src/twwarhammer3`, `configs/twwarhammer3`, `pyproject.toml`, `uv.lock`,
`.python-version`) lands only while no play job of that game runs, and it starts a new test setup
for the battles after it. P3, P5 and P6 contain no intended behaviour change. P1 adds one refusal

```

</details>
