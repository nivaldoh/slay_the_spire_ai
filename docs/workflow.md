# How work is done here

Agents do most of the work; the owner keeps the judgement: what to build, what "correct"
means, what a result means. The owner reads short cards and short reports, not code.
This page is the light factory plan (2026-10-28/29; the full plan with the owner's notes is
`git show a3abee9:docs/light-factory-plan.md`) as implemented on 2026-10-29 at the owner's word
"Implement docs/light-factory-plan.md". The process is in use; every check it
added is still "proposed, not agreed" under the [hard rule](../AGENTS.md#verification-hard-rule).
Sources are linked inline and listed in [references.md](references.md).

## Sizes of change

What the owner sees depends on the kind of change, not on who made it ("The change sets the
tier, not the author",
[claude.dev](https://claude.dev/blog/solving-code-review-at-anthropic/)).

JUDGEMENT?: Sizes — Claude, 2026-10-29, answering the owner's "what does normal mean": the
plan's rows plus prompt, protocol and `export` as normal, and "when unsure, normal".

| Size | What counts | What the owner sees |
|---|---|---|
| Trivial | A typo, a broken link, a comment (not a JUDGEMENT line), a refactor that existing tests cover | Nothing; the commit quotes `check.py` |
| Normal | Anything else that changes behaviour: a feature, a bug fix, a new or changed test or check, a prompt, the protocol, anything a scorer or results reader (`stats`, `report`, `digest`, `export`) uses | A card before, a report after |
| Experiment | A benchmark run, an RL run, a paid model screen | An experiment card, committed before the first run |
| Live check | An [agreed](agreed-checks.md) game check | Its procedure, then a report |

When unsure, a change is normal.

## Before a change: the card

JUDGEMENT: Slice contract — Codex, 2026-10-28, proposes the brief below before feature work.

The agent writes a card of about ten lines; the owner answers agree, change or not now.
Without an agreed card a feature counts as unverified.

JUDGEMENT: Away cards — Claude, 2026-10-29, under the owner's "Implement": when the owner is
away, the agent writes the card, builds, and the report says the card was not agreed; waiting
for agreement first would stop away work.

```text
Change:         test that src/gameai never imports a game package
Behaviour:      WHEN a module under src/gameai imports spire or twwarhammer3 (`import x`,
                `from x import y`, at any depth) THE TEST SHALL fail and name the file,
                the line and the rule.
                WHEN a docstring or comment only mentions them THE TEST SHALL pass.
Must not break: the rest of the suite; no new dependency.
Reference:      AGENTS.md Layout: "it never imports a game package"
Check:          uv run --locked pytest -ra tests/test_repo_rules.py
                Must fail on: `from twwarhammer3 import protocol` planted in a scratch copy.
Not checked:    imports made through strings (importlib).
You:            agree / change / not now
```

- **Behaviour**: one `WHEN ... SHALL` line per case ([EARS](https://kiro.dev/docs/specs/feature-specs/)
  style). Each line becomes a test.
- **Reference**: where the right answer comes from: the owner's words, the protocol, the game
  or a named research repo. Never the code itself.
- **Check**: the command, plus a plausible wrong version it must catch. For WH3 work it names
  the step it tests on engine → Lua → mailbox → policy → order → Lua → engine. An
  acknowledgement shows that an order arrived; only the engine shows that the unit acted.
- A card covers its own change only (owner, decision 1: "No"); a later fix in the same area
  gets its own card, which can be three lines.
- Task cards go in the commit message or `runs/<task>/`; the few lasting ones go in the
  docstring or page they govern.

An **experiment card** gives the question and the comparison; the main measure and the number
of runs; the stop rule and how failures count; the budget (a named ledger cap if paid) and
the analysis command. Committing it first is [pre-registration](https://neurips.cc/virtual/2020/workshop/16158);
the report then says "planned at `<rev>`" or "exploratory".

**Questions** to the owner: at most three, multiple choice, the recommendation first. Each
says what happens now, what each answer changes and the best case for the other option. In
one Anthropic study, analysts took the option their agent leaned toward 86% of the time
([judgement calls](https://www.anthropic.com/research/agents-judgment-calls)).

A yes to a run does not make its result correct. A passing check never permits a launch,
spending or a change to what a benchmark measures.

## The exit gate: `scripts/check.py`

Before every commit, both agents run one command and quote its first five lines:

```text
$ uv run --locked python scripts/check.py
revision  297a061 on main
tree      dirty: 3 changed, 4 untracked
result    PASSED: Ruff clean; 1655 passed, 41 skipped in 17.92s
skipped   40 could not import 'torch'; 1 set GAMEAI_TEST_WINDOWS=1 on WSL to test actual Windows ...
log       runs/checks/20261029-024523-297a061-545683.log
needs your yes (changes since HEAD):
  - 1 skip or xfail added: tests/twwarhammer3/test_wh3_version_review.py: pytest.skip("needs Node.js")
markers   3 problems listed in the log, for the owner
```

- It runs `ruff check .` and the whole offline suite (about 27 s; 18 s before 2026-10-29's
  evidence-replay tests), Lua and image tests
  included, the repo rules ([test_repo_rules.py](../tests/test_repo_rules.py)) and the link
  test among them. It exits 1 if anything fails. It never launches a game, spends money or
  commits, and it removes `WH3_WRITE_PROMPTS` so it cannot rewrite prompt snapshots.
- "needs your yes" lists edits only the owner approves, in everything not yet on
  `origin/main` (or since `--base REV`): lines removed or changed in a file an agreed check
  names or in [agreed-checks.md](agreed-checks.md); an edited or removed JUDGEMENT line; an
  assert removed or changed under `tests/`; a skip or xfail added; a changed prompt snapshot;
  a package added or a version changed in `uv.lock`. A line moved verbatim is not flagged.
  Warnings never fail the run: they go in the report for the owner.
- "markers" counts format problems in JUDGEMENT markers (misspelt, in a file that cannot
  carry one, no date, a "rests on" pointing nowhere), listed in the log. Only the owner
  changes markers, so they never fail the run.
- Optional extras (`--extra train`, `--extra llm`), the browser check and live game checks
  run only when a change touches what they cover. The full offline suite always runs, since
  it takes well under a minute (owner, decision 3: "Yes", when it took 20 s).

## Checks in layers

Nothing counts as correct because of who made it: code, tests, agent summaries, a reviewer's
"looks good", a `/goal` "met" or a green run of a check the owner never agreed. "The critical
failure mode across all layers is using the same method that wrote the code to verify it"
([Sonar](https://www.sonarsource.com/resources/library/zero-trust-verification-in-software-delivery/)).
Agents do rig checks: METR saw frontier models edit tests and scoring code
([2025](https://metr.org/blog/2025-06-05-recent-reward-hacking/),
[2026](https://metr.org/blog/2026-05-19-frontier-risk-report/)). Layers must fail in
different ways: two agents sharing one wrong assumption are one check. Script checks decide
pass or fail; agent checks only point at a problem, which then becomes a test, a fix or a
question. Layer names follow Sonar's
([Shaukat](https://ai.engineer/talks/in-the-land-of-ai-agents-the-verifiers-are-king)).

| Script layer | Here |
|---|---|
| Syntax and style | Ruff (E, F, I) |
| Supply chain | `uv.lock` with `--locked`; `check.py` flags added or changed packages |
| Secrets | Keys live outside the repo; a repo rule fails on a tracked or untracked key, `runs/` or game file |
| Data flow | Planted hidden values never reach controller input, the checkpoint-RL projection, candidates, replays or exports; the stills director gets visible units only (Lua test) |
| Control flow and state | Mailbox, protocol, Lua and lifecycle tests. Next time the mailbox changes: a [Hypothesis](https://hypothesis.readthedocs.io/en/latest/stateful.html) test of random valid, old and foreign requests |
| Structure | Repo rules: `gameai` imports no game; AGENTS.md at most 200 lines; links resolve |
| Regression | The whole offline suite before every commit |
| Environment | `doctor`, the build pin, the source-scope refusal, `RuntimeLock`, ledger caps |
| Checks of checks | Planted wrong versions in a scratch copy, by hand or with the refusal sweep that removes each `raise`/`error()` in turn (`scripts/refusal_sweep.py`, the `refusal-sweep` skill; 2026-10-29 results in the WH3 log); proposed: [mutmut](https://mutmut.readthedocs.io/en/latest/) (not installed) on 2-3 files when an agreed check is made or changed |

A check counts only after it has failed on a planted wrong version (in a scratch copy) and
passed on the real code: [mutation testing](https://sqlite.org/testing.html#mutation_testing)
on a small scale.

**WH3 needs its own rows** (owner's question, 2026-10-29). Three of its meanings are not
covered by any generic layer:

| WH3 layer | Today | Gap |
|---|---|---|
| Battle time | Delays, ages and the clock rule use engine battle time ([clocks](twwarhammer3/integration.md#clocks-measured-2026-10-28)). The 1x rate by the Windows clock was measured once, offline, from the checkpoint agent's stamps | No check measures 1x against the Windows clock: the team and checkpoint checks' clock ratios use WSL time, and the mod reports a constant `speed` 1. Proposed: record each observation file's NTFS write time (WSL reads it to 100 ns), and `digest` flags battle time per Windows second outside a band the owner sets |
| Order effect | Acknowledgements and engine refusals are recorded; tests cover identity | An accepted order is not an effect. The [proposed correctness checks](twwarhammer3/benchmark-implementation.md#correctness-checks-to-agree) wait on the benchmark definition |
| Outcome source | Only an engine won, lost or draw is a gameplay outcome; a late failure keeps the engine ending (agreed) | Readers still differ on timer wins and failures (state.md Known issues) |

Spire's equivalents (game state restored with the same RNG; the shared profile's unlocks)
are in its [state-restore plan](spire/state-restore.md).

Rules against rigged checks ([Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices), METR):
- Never special-case test inputs, scenario names or seeds.
- If a test seems wrong, report it; don't change it in the change that makes it pass.
- Don't edit an existing test, check, scorer or expected output in the same change as the
  code it judges. New tests for new behaviour go in with that behaviour.
- List every test, snapshot, skip or scorer edit in the report (`check.py` lists most).

### Agent checks and the reviewer

| Layer | The question | Who and when |
|---|---|---|
| Intent | Does the change do what the card says, and nothing else? | Reviewer, normal changes |
| Research logic | Does each number mean what its sentence says: right denominator, failures counted, no peeking at test scenarios, same conditions? | Rerun reviewer, before any number reaches the owner's pages |
| Deep semantics | Does it break a meaning used elsewhere: an acknowledgement matched to the wrong request, which outcomes count, battle time vs WSL time, two scripts reading the same files? | Reviewer, when shared code, scorers, result readers or the protocol change |
| Emergent anomalies | Is a run surprising: a win faster than the scripted reference, zero invalid orders where they are usual? | A script flags runs; an agent reads only those |
| Performance | Only a named question: think time at 1x, restore speed, suite time | On demand, same inputs before and after |
| State and environment | Game build, running jobs and locks, branch, ledgers, clock source | Session start and before any launch |

The reviewer is [.claude/agents/reviewer.md](../.claude/agents/reviewer.md); Codex runs
`/review` with that file as custom instructions. Where it is used (owner, decision 2: "Yes"):
on every normal change, as the rerun reviewer on every number for the owner's pages, and not
on trivial edits. Its rules (rest on JUDGEMENT `docs/testing.md` Agent review workflow):
- It gets the card, the diff, the raw output and the code that reads the changed data, never
  the author's explanation.
- Each finding gives a file, a line and a concrete failure case, or it is only a note
  ("Noise costs more when the author is an agent", claude.dev).
- After three rounds, the author rethinks or parks the change.
- No answer, or garbage, means the review is incomplete, not approved.
- An agent's reason for a lost fight is a guess until a trace or replay shows it.
- The reviewer is tested too: on saved past bugs and a clean diff, counting misses and
  false alarms ([first run](twwarhammer3/log.md#2026-10-29-light-factory-stages-1-3)).

## Loops: what runs when

JUDGEMENT: Work loops — Codex, 2026-10-28, proposes the transitions and stop conditions below.

Each kind of run has a script check and an agent check sized to it. When a mistake gets past
a review, the fix adds a test or a rule, so the same mistake is caught earlier next time. If
a check still fails after the attempts its card allows, park the change with what blocks it.
Never loosen the check.

| Run | Script check | Agent check | Owner | Stops when |
|---|---|---|---|---|
| Docs edit | `check.py` | Rerun reviewer, only if the text states numbers | Nothing for factual fixes | `check.py` passes |
| Code change | Nearby tests, then `check.py` | Reviewer against the card | Card; report | `check.py` passes; findings fixed or parked |
| Bug fix | A test that fails first, then `check.py` | Reviewer: does it fail for the right reason? | Card (three lines will do); report | Fails before the fix, passes after |
| Test or check change | `check.py` and its warnings | Reviewer: real code passes, planted bug fails | Yes if an agreed check changes | `check.py` passes, plus the yes if needed |
| Live game check | Preflight, then the agreed pass rule; recount from saved files | Agent reads the digest for anomalies | Game window and the named check | Pass rule, cutoff, unexpected closure, two failed launches |
| Experiment | Experiment card; summaries recomputed from raw files | Rerun reviewer on every number; reads flagged runs | Card and budget before; log entry after | Planned runs, budget or stop rule |
| RL or environment | Environment checks, then `check.py` | Reviewer compares with the named reference repo | Card | Checks pass on a fake game, then once on the real one |
| Research | Each claim has a URL and an exact quote | A second agent re-fetches each quote | Nothing until a thesis decision | Question answered, or search limits written down |
| JUDGEMENT work | `check.py`'s marker list | A second agent checks each marker against `git log -S` | At most three questions | Marker matches its site |
| Long run | `check.py` first, on the tree the last session left | A second agent checks every claim in the handoff | Run brief before; one report after | Cutoff, budget, capacity, or nothing useful left |
| Cleanup | `check.py` | Agent compares `state.md` and track pages with code and logs | One small fix branch | Done by hand first; nothing scheduled |
| Process change | `check.py` | Does each step still catch something? | A rule change only after the same failure twice, and the owner's yes | Kept, simplified or dropped |

Spire uses the same rows with its own commands ([Spire guide](spire/AGENTS.md)).

- **Live game check.** Preflight is `doctor`, committed code, no other controller, and a
  cutoff that fits the whole procedure including cleanup. Durations use battle time. WH3
  stays unpaused at 1x.
- **Experiment.** A 0/N score means a weak model only if a scripted or human player has won
  that scenario: with frontier models, "a 0% pass rate across many trials ... is most often a
  signal of a broken task" ([Anthropic](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)).
  Each log entry ends with what the evidence covers, its limits, the interval (unit and
  method) and the spend, failed jobs included
  ([NeurIPS checklist](https://neurips.cc/public/guides/PaperChecklist)). Per-episode
  warnings that stop a queue are not built yet.
- **RL or environment.** Copy [Gymnasium](https://gymnasium.farama.org/_modules/gymnasium/utils/env_checker/)'s
  checker (two resets with one seed give the same observation; each observation is a fresh
  object; here, two restores of one checkpoint give the same first observation) and
  [PettingZoo](https://pettingzoo.farama.org/content/environment_tests/)'s tests (seeded runs
  agree; an episode ends at its limit; each agent sees only its share). Test a
  [CleanRL](https://jmlr.org/papers/v23/21-1342.html) learner on a standard environment first.
  When a policy games its reward, fix the environment or scorer (METR).

## Long runs while the owner is away

Before a run goes unattended, its `runs/<task>/brief.md` answers five questions
([Claude Code](https://code.claude.com/docs/en/best-practices)): **Done** (the outcome and its
card); **Check** (commands or agreed check); **May touch** (worktree, branch, files, game
window, spend cap); **Stops** (cutoff in Windows or engine time, budget, attempts,
[autonomy limits](autonomy.md#limits)); **Result** (where the report goes; the owner decides).

A `/goal` condition names the check command, forbids edits to existing tests and agreed
checks the brief does not list, and states the cutoff. "Met" only means stop: in Claude Code
a small model judges it from the transcript ([/goal](https://code.claude.com/docs/en/goal));
in Codex the working model marks its own goal done
([Codex goals](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)).
Codex and Claude share this tree: each session claims its task in
[Active work](state.md#active-work) first.

The handoff note (`runs/<task>/handoff.md`) has five headings, after OpenAI's
[ExecPlans](https://developers.openai.com/cookbook/articles/codex_exec_plans): Progress,
Surprises, Decisions (and who made them), Not checked, Next. The next session checks it
against `git`, running processes and files on disk.

## Reports

```text
Change:      add tests/test_repo_rules.py (card agreed <date>, or "not agreed: owner away")
Checks:      scripts/check.py at <rev>, clean: <n> passed, <n> skipped (no torch); log <path>
Review:      1 finding, fixed; none open
Not checked: imports made through strings
Undo:        git revert <rev>
Status:      passed at <rev>; the check is proposed, not agreed
```

A check's status is proposed, agreed but not run here, passed at `<rev>`, failed, skipped or
unavailable. It "passed" only if it ran and someone saw the result. "If you can't say what
the checks would miss, ask for a real review rather than a quick approval" (claude.dev).

## Keeping the process working

The owner asked (2026-10-29) how to stop this workflow decaying and keep it easy to change.

- **Rules a test can decide are tests.** Imports, committed files, AGENTS.md's length and
  links fail `check.py`; marker problems are listed in every run. A written rule nothing
  checks drifts first, so a repeated slip gets a test before more text.
- **One home per rule.** AGENTS.md holds the hard rules and pointers; each process rule lives
  here once, test how-to in [testing.md](testing.md), away rules in [autonomy.md](autonomy.md).
  The 200-line cap on AGENTS.md stops it regrowing.
- **Every slip becomes a check, slowly.** A fix adds a test or a rule; a new process rule
  waits for the same failure twice and the owner's yes.
- **Count what each step catches.** Per change: reviewer findings (real or noise), questions
  asked, the owner's minutes if shared. In the log: bugs found after "done" ("if they rise,
  we haven't saved human time, we've only moved it", claude.dev). After about five changes,
  keep, simplify or drop each step; after a model upgrade, drop steps that catch nothing
  ([Anthropic](https://www.anthropic.com/research/harness-design-long-running-apps)).
- **Changing the process** is a normal change with a card: edit this page, `check.py` or the
  reviewer file, and the report names what the change should catch.

JUDGEMENT: Pilot assessment — Codex, 2026-10-28, proposes the cases and observations below.

Process cases, tried on saved examples or throwaway changes, never on a forbidden effect:
an agreed card with passing checks finishes without asking again; an unspecified rule gets a
card and dependent work stops; a planted bug that passes gets its missing check; a skipped,
crashed or empty check or review is reported incomplete; a check changed after its pass is
rerun at the final state; scoring, test data or a permission boundary is named and parked; a
resumed session repeats no launch, spend or finished step. Each case is reported on its own.

## What exists and what waits

JUDGEMENT: Rollout order — Codex, 2026-10-28, proposes agreement, one pilot, then selective tooling.

Start strict and loosen with evidence (claude.dev): the reviewer sees every normal change
until its counts show its findings are mostly noise.

| Item | Status (2026-10-29) |
|---|---|
| `scripts/check.py`, repo rules, risky-edit warnings (stage 1) | Built and planted-tested |
| Reviewer and its first eval (stage 2), export leak test, review workflow fix | Built |
| Docs cleanup (stage 3) | Done and reviewed (one reviewer found 6 issues, fixed): AGENTS.md is a map of at most 200 lines; docs/spire/AGENTS.md only gained the `check.py` line (135 lines, loaded only for Spire work) |
| Hooks, skills, CI (stage 4) | Trigger seen 2026-10-29: a commit made before its `check.py` run (96e6265), and one workflow repeated about twenty times (plant, sweep, recount). Built for Claude Code: `scripts/hooks/stop_check.py` (Stop: runs `check.py` when HEAD, the index, the diff or an untracked file changed since its last pass; exit 2 keeps the turn going once; skipped while a game job runs) and `scripts/hooks/pre_bash.py` (Bash: refuses `ruff format` except `--check`/`--diff`, and git commands that move HEAD while `scripts/wh3_queue.py` runs), tested in `tests/test_hooks.py`, registered in the local `.claude/settings.json` (excluded from git, as before); both seen live on 2026-10-29 (the Bash hook refusing a probe, the Stop hook running `check.py` at a turn's end: `runs/checks/20261029-111240-a2c63b0-988366.log`). Skill: `refusal-sweep` (`.agents/skills/`, symlinked into `.claude/skills/`) for the repeated sweep, with `scripts/refusal_sweep.py` tested in `tests/test_refusal_sweep.py`. Not built: the Codex hooks (a trusted `.codex/` cannot be checked from here), CI (committed pages still link into the untracked `docs/thesis/`) |
| Experiment loop (stage 5) | Waits for the next planned free experiment (it is done on one). Its new code, per-episode warnings that stop a queue, is not built: of the two warnings `digest` shows, a build mismatch "warns and is recorded but never blocks" (owner, 2026-10-18), and stopping on invalid batches would change what an experiment measures (autonomy.md parks such changes); which warnings stop a queue is the owner's choice |

JUDGEMENT?: Hook details — Claude, 2026-10-29: the HEAD-moving git subcommands (commit, merge,
rebase, reset, checkout, switch, pull, cherry-pick, revert, am), `ruff format` refused everywhere,
one block per failing check, no check beside a game job, and a stop let through when `check.py`
cannot run or timed out; a narrower list, more blocks or failing closed would block differently.
How hard the exit gate is enforced rests on these.

Hooks must handle: exit code 1 does not block (a wrapper turns a `check.py`
failure into 2); Claude Code overrides a `Stop` hook after eight blocks in a row with no tool call between them
(so `stop_check.py` lets an unchanged failing tree through after one block); a Codex
`Stop` hook that exits 0 must print JSON, and Codex loads project hooks only from a trusted
`.codex/` ([Claude Code](https://code.claude.com/docs/en/hooks), [Codex](https://learn.chatgpt.com/docs/hooks)).
Hooks are "a useful guardrail, not a complete enforcement boundary" (OpenAI); games,
spending and ledgers stay guarded by refusals in the CLI.

Not building: Sonar's products, dashboards or coverage targets; repo-wide mutation testing;
spec frameworks such as Kiro; an Inspect port, a type-checker migration or an orchestration
framework; Anthropic's scale machinery. A new tool needs a gap we have seen, a named use and
a check that it helps.
