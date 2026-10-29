# Light factory plan

**Draft for discussion, 2026-10-29.**

## The short version

A light factory is a repo where agents do most of the work and you keep the judgement: what to
build, what "correct" means, what a result means. You read short specs and short reports, not code.

What would change for you:
- Before a feature: a **spec card** of about ten lines. You answer agree, change or not now.
- After a change: a **report** of six lines. It says what changed, which checks ran with their
  counts, what was not checked and how to undo it.
- Questions: at most three at a time, multiple choice, with a recommendation and the best case
  against it.

What would change for agents:
- One command, `scripts/check.py`, runs Ruff and the offline tests (20 seconds) before each commit.
- A second agent reviews each normal [what does "normal" mean here?] change against its card, and reruns every number before it
  reaches your pages.
- No agent may weaken a test to make its own change pass.

First step, if you agree: build `check.py` and a few repo-rule tests, then try the process on one
real task. [this seems too loosely defined. I don't get what "check.py" should be. Try to explain it more concretely]

## What "light factory" means

Addy Osmani: "You can run the loop with humans in it (light factory)". In a dark factory nobody
reads the code ([Software Factories, Light and Dark](https://addyosmani.com/blog/software-factories/)).
A loop can run without a person only if its check "is cheap, runs at high frequency, and relies on
something that can't be easily faked out". So the test suite can run without you; research directions, meaning
and benchmark design cannot. Anthropic's source-control team still reviews every change to its
system, but they "examine the intent of the change as opposed to reading every line of code"
([Redesigning source control](https://www.anthropic.com/research/redesigning-source-control)).

This works if you spend fewer minutes per accepted change, fewer bugs turn up after "done", and
every number on your pages comes with its command and revision.

## Where we are today

Working:
- The [hard rule](../AGENTS.md#verification-hard-rule) and the [agreed checks](agreed-checks.md). [I haven't review these two files manually so I don't know if they're good or not]
- [JUDGEMENT markers](judgement.md) for choices you haven't made.
- Guards in the CLI: `play` refuses uncommitted changes to its code, ledgers cap spending,
  `RuntimeLock` keeps a second controller off a game, queues stop on failures.
- 1,634 offline tests pass and 41 skip in 18.8 s, Lua included (`uv run --locked pytest -ra` at
  `e0d3919`).
- Rules committed before runs: the tactic cards (now historical) required naive plays to lose and a
  scripted winning play to win.
- A **rerun reviewer**: an agent that reruns counts before they reach you. On 2026-10-28 four review
  passes found 5 wrong and 13 weak JUDGEMENT markers
  ([judgement](judgement.md#status-and-how-to-continue)), and after a rerun two claims (a short
  rout, healing) were withdrawn from interview evidence.

Missing:
- A check script, hooks, CI or skills. Checks run only when an agent remembers. On 2026-10-28 a
  `stats` fix (`b24df11`) passed its own tests and broke `test_wh3_play.py` on `main` until
  `04e5adb`; the full suite would have caught it.
- Tests for some written rules: `gameai` never imports a game; the JUDGEMENT marker format; no
  commits while a queue runs.
- Tests that hidden game state never reaches exports (one weak check) or stills (none).
- Planted-bug runs: most tests have never run against a copy of the code with a deliberate bug. On
  2026-10-23 some still passed with the behaviour they test removed
  ([fixed then](testing.md#wh3-follow-up-2026-10-23)).
- A [review workflow](../.claude/workflows/wh3-version-review.js) that reports failure. Today it
  names the first proposal the winner when every judge fails.
- Short instructions. AGENTS.md is 305 lines, loads every session, and repeats rules that
  autonomy.md and testing.md also state.
- Questions you can answer at a glance. Two agent questions on 10-28 got "Not sure what you mean"
  and "Not sure what you need".
[we should also think about how to prevent our workflow from gradually decaying over time, and how to make it easier to adapt/evolve it as needed]

## 1. The spec card

Slice contract — Codex, 2026-10-28, proposes the brief below before feature work.

Before a feature, the agent writes a card and you answer it. Osmani's advice: "write down what
you're building, what it must not break and how you'll know it worked. It doesn't need to be long"
([The Code Nobody Reads](https://addyo.substack.com/p/the-code-nobody-reads)). Without an agreed
card, a feature counts as unverified.

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

- **Behaviour**: one `WHEN … SHALL` line per case ([EARS](https://kiro.dev/docs/specs/feature-specs/)
  style). Each line becomes a test.
- **Reference**: where the right answer comes from, such as your words, the protocol, the game or
  a named research repo. Never the code itself.
- **Check**: the command, plus a plausible wrong version it must catch. For WH3 work, it names the
  step it tests on engine → Lua → mailbox → policy → order → Lua → engine. An acknowledgement shows
  that an order arrived; only the engine shows that the unit acted.

What you see depends on the kind of change, whoever wrote it. The Claude Code team works the same
way: "The change sets the tier, not the author"
([How the Claude Code team does code review](https://claude.dev/blog/solving-code-review-at-anthropic/),
"claude.dev" below).

| Size | Examples | What you see |
|---|---|---|
| Trivial | Typo, broken link, a refactor that existing tests cover | Nothing; the commit names the check |
| Normal | Feature, bug fix, new or changed check, anything touching a scorer or a results reader (`stats`, `report`, `digest`) | A card before, a report after |
| Experiment | Benchmark run, RL run, paid model screen | An experiment card, committed before the first run |
| Live check | An [agreed](agreed-checks.md) game check | Its procedure, then a report |

An **experiment card** gives:
- the question and the comparison;
- the main measure and the number of runs;
- the stop rule and how failures count;
- the budget (a named ledger cap if paid) and the analysis command.

Committing it first is [pre-registration](https://neurips.cc/virtual/2020/workshop/16158), as the
tactic cards did. The report then says "planned at `<rev>`" or "exploratory".

If you say yes to [decision 1](#decisions), one agreed card also covers later fixes in its area,
such as "an old or foreign request never replaces pending orders". Task cards go in the commit
message or `runs/<task>/`; the few lasting ones go in the docstring or page they govern.

When an agent asks you something, it asks at most three questions, as multiple choice with the
recommendation first. Each says what happens now, what each answer changes, and the best case for
the other option. In one Anthropic study, analysts took the option their agent leaned toward 86%
of the time ([judgement calls](https://www.anthropic.com/research/agents-judgment-calls)). A
question that argues only one side mostly gets that side back.

Your yes to a run doesn't make its result correct. A passing check never permits a launch,
spending or a change to what a benchmark measures.

## 2. Checks in layers

You named the talk by Manish Kapur (Sonar) and Addy Osmani (Anthropic),
[How Anthropic Merges 30,000 Code Changes a Day](https://www.youtube.com/watch?v=AnsXWH2_EBU) (AI
Engineer New York, October 2026). Its listing promises "why every loop in the factory needs
independent, multi-layered verification". A news recap paraphrases Kapur: "zero trust,
multi-layered verification in every loop", with deterministic, agentic and supply chain layers
([StartupHub.ai](https://www.startuphub.ai/ai-news/technology/2026/anthropic-now-merges-30-000-changes-a-day)).
I couldn't read the transcript.

The layer names you listed match, word for word, a slide by Sonar's CEO in another talk
([Shaukat](https://ai.engineer/talks/in-the-land-of-ai-agents-the-verifiers-are-king)). The tables
below follow that slide.

**Zero trust**: nothing counts as correct because of who made it. That includes code, tests,
agent summaries, a reviewer's "looks good", a `/goal` "met" and a green run of a check you never
agreed. Sonar: "The critical failure mode across all layers is using the same method that wrote
the code to verify it"
([zero-trust verification](https://www.sonarsource.com/resources/library/zero-trust-verification-in-software-delivery/)).
Agents really do rig checks: METR saw frontier models edit tests and scoring code
([2025](https://metr.org/blog/2025-06-05-recent-reward-hacking/),
[2026](https://metr.org/blog/2026-05-19-frontier-risk-report/)).

**Multi-layered**: checks that fail in different ways. Two agents sharing one wrong assumption
count as one check.

- **Script checks** (deterministic) give the same answer every time and decide pass or fail.
- **Agent checks** (agentic) are a second agent reading and reasoning. They can only point at a
  problem, which then becomes a test, a fix or a question for you.

JUDGEMENT: Verification depth — Codex, 2026-10-28, proposes checks selected by affected behavior.

JUDGEMENT: Exit gate — Claude, 2026-10-28, proposes the full offline suite at every exit gate.

The exit gate is the last check before a commit or report. There the offline suite always runs in
full, since it takes 20 seconds. Live, browser, optional-extra and paid checks run only when a
change touches what they cover.

### Script checks

B1-B9 are the build items in [section 6](#6-what-to-build). The last three rows are ours. The
slide calls the supply chain row "known dependency analysis"; "supply chain" is Kapur's word in
the recap.

| Layer | Today | Add |
|---|---|---|
| Syntax and style | Ruff (E, F, I) | Nothing until a kind of bug repeats |
| Supply chain | `uv.lock`, used with `--locked` | A warning when `uv.lock` adds or upgrades a package (B4) |
| Secrets | Keys live outside the repo; `.gitignore` blocks `runs/` and game files, not key files | A test that no key, `runs/` or game file is tracked (B2) |
| Data flow | Tests plant a fake secret in hidden fields and check it never shows up (controller input, checkpoint-RL projection, candidates, replays); a Lua test hides fogged enemies (visibility stubbed) | The same for exports and stills (B3) |
| Control flow and state | Mailbox, protocol, Lua and lifecycle tests | A [Hypothesis](https://hypothesis.readthedocs.io/en/latest/stateful.html) test that sends random sequences of valid, old and foreign requests, next time the mailbox changes |
| Structure | Rules written in AGENTS.md | Tests: `gameai` imports no game; marker format; AGENTS.md size (B2) |
| Regression | 1,634 offline tests | All of them before every commit (B1) |
| Environment | `doctor`, build pin, source-scope refusal, `RuntimeLock`, ledger caps | Nothing; reports include their output |
| Checks of checks | Bugs planted by hand ([testing](testing.md#show-that-a-test-can-detect-a-wrong-result)) | [mutmut](https://mutmut.readthedocs.io/en/latest/), which plants small bugs and reports those no test catches, on 2-3 files when an agreed check is made or changed |
[we should think about whether we need any layer specific to WH3, like timing in battles]

A check counts only after it has failed on a planted wrong version (in a scratch copy) and passed
on the real code. That is [mutation testing](https://sqlite.org/testing.html#mutation_testing) on
a small scale.

Agents must not rig checks ([Anthropic](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices), METR):
- Never special-case test inputs, scenario names or seeds.
- If a test seems wrong, report it; don't change it in the change that makes it pass.
- Don't edit an existing test, check, scorer or expected output in the same change as the code it
  judges. New tests for new behaviour go in with that behaviour.
- List every test, snapshot, skip or scorer edit in the report.

### Agent checks

"Research logic" replaces the slide's "business logic".

| Layer | The question here | Who and when |
|---|---|---|
| Intent | Does the change do what the card says, and nothing else? | Reviewer, normal changes |
| Research logic | Does each number mean what its sentence says: right denominator, failures counted, no peeking at test scenarios, same conditions? | Rerun reviewer, before any number reaches your pages |
| Deep semantics | Does it break a meaning used elsewhere: an acknowledgement matched to the wrong request, which outcomes count, battle time vs WSL time, two scripts that read the same files? | Reviewer, when shared code, scorers, result readers or the protocol change |
| Emergent anomalies | Is a run surprising: a win faster than the scripted reference, zero invalid orders where they're usual, a score above the reference? | A script flags runs; an agent reads only those |
| Performance | Only a named question: think time at 1x, restore speed, suite time | On demand, same inputs before and after |
| State and environment | Is the world as the plan assumes: game build, running jobs and locks, branch, ledgers, clock source? | Session start and before any launch |

The reviewer's rules (rests on JUDGEMENT `docs/testing.md` Agent review workflow):
- It gets the card, the diff, the raw output and the code that reads the changed data, never the
  author's explanation.
- Each finding gives a file, a line and a concrete failure case, or it is only noted. "A reviewer
  that's asked to find problems will always find something"
  ([Claude Code](https://code.claude.com/docs/en/best-practices)), and "Noise costs more when the
  author is an agent" (claude.dev).
- After three rounds, the author rethinks or parks the change. One Claude Code PR "went through
  more than fifty rounds of review and fixes overnight" (claude.dev).
- No answer, or garbage, means the review is incomplete, not approved.
- An agent's reason for a lost fight is a guess until a trace or replay shows it.
- The reviewer gets tested too. Run it on saved past bugs and on a clean diff, and count misses and
  false alarms. The past bugs include `b24df11`'s break and the tests that passed on 10-23 with
  their behaviour removed. Anthropic: "Any incidents are now an eval" (claude.dev).

## 3. Loops: what runs when

JUDGEMENT: Work loops — Codex, 2026-10-28, proposes the transitions and stop conditions below.

Checks run at four moments:
1. while editing;
2. at the exit gate;
3. once per run or session;
4. in occasional cleanups.

Sonar's loops in the agent, at the pull request and in background maintenance are the first,
second and fourth ([Verify](https://www.sonarsource.com/agent-centric-development/verify/),
[overview](https://www.sonarsource.com/agent-centric-development/)).

The talk's "every loop" means, here, that each kind of run below has a script check and an agent
check sized to it (none for trivial edits). When a mistake gets past a review, the fix adds a test
or a rule, so the same mistake is caught earlier next time (claude.dev does the same). If a check
still fails after the attempts its card or run brief allows, park the change with what blocks it.
Never loosen the check.

| Run | Script check | Agent check | You | Stops when |
|---|---|---|---|---|
| Docs edit | Link test, then `check.py` | Rerun reviewer, only if the text states numbers | Nothing for factual fixes | `check.py` passes |
| Code change | Ruff and nearby tests, then `check.py` | Reviewer against the card | Agree the card; read the report | `check.py` passes; findings fixed or parked |
| Bug fix | A test that fails first, then `check.py` | Reviewer: does it fail for the right reason? | Nothing if an agreed card covers it | Fails before the fix, passes after |
| Test or check change | `check.py` with risky-edit warnings | Reviewer: real code passes, planted bug fails | Yes if an agreed check changes | `check.py` passes, plus your yes if needed |
| Live game check | Preflight, then the agreed pass rule; recount from saved files | Agent reads the digest for anomalies | Game window and the named check | Pass rule, cutoff, unexpected closure, two failed launches |
| Experiment | Experiment card; per-episode warnings stop a queue; summaries recomputed from raw files | Rerun reviewer on every number you'll see; reads flagged runs | Card and budget before; log entry after | Planned runs, budget or stop rule |
| RL or environment | Environment checks, then `check.py` | Reviewer compares with the named reference repo | Card | Checks pass on a fake game, then once on the real one |
| Research | Each claim has a URL and an exact quote | A second agent re-fetches each quote | Nothing until a thesis decision | Question answered, or search limits written down |
| JUDGEMENT work | Marker-format test | A second agent checks each marker against `git log -S` | At most three questions | Marker matches its site |
| Long run | `check.py` first, on the tree the last session left; the loops above inside | A second agent checks every claim in the handoff | Run brief before; one report after | Cutoff, budget, capacity, or nothing useful left |
| Cleanup | Link test and repo rules | Agent compares `state.md` and track pages with code and logs | One small fix branch | Nothing scheduled until it has worked by hand |
| Process change | `check.py` | Does each step still catch something? | A rule change comes only after the same failure twice, and needs your yes | Kept, simplified or dropped |

Slay the Spire uses the same rows with its own commands ([Spire guide](spire/AGENTS.md)).

Notes:
- **Live game check.** Preflight is `doctor`, committed code, no other controller, and a cutoff
  that fits the whole procedure including cleanup. Durations use battle time
  ([clocks](twwarhammer3/integration.md#clocks-measured-2026-10-28)). WH3 stays unpaused at 1x.
- **Experiment.**
  - The per-episode warnings are new work. Today `digest` shows invalid batches and build warnings,
    but no queue stops on them yet.
  - A 0/N score means a weak model only if a scripted or human player has won that scenario.
    [Anthropic](https://www.anthropic.com/research/demystifying-evals-for-ai-agents): with frontier
    models, "a 0% pass rate across many trials ... is most often a signal of a broken task".
  - Each log entry ends with four things
    ([NeurIPS checklist](https://neurips.cc/public/guides/PaperChecklist)):
    - what the evidence covers;
    - its limits (few runs, one build);
    - the interval, with its unit and method;
    - the spend, failed jobs included.
- **RL or environment.**
  - Copy [Gymnasium](https://gymnasium.farama.org/_modules/gymnasium/utils/env_checker/)'s checker:
    two resets with the same seed must give the same observation, and each observation must be a
    fresh object. For us, two restores of one checkpoint must give the same first observation.
  - Copy [PettingZoo](https://pettingzoo.farama.org/content/environment_tests/)'s tests: seeded
    runs agree, and an episode ends at its declared limit. Add: each agent sees only its own share.
  - Test a [CleanRL](https://jmlr.org/papers/v23/21-1342.html) learner on a standard environment
    before WH3.
  - When a policy games its reward, fix the environment or scorer. Punishing the hacks a monitor
    spots teaches subtler hacks (METR).

## 4. Long runs while you're away

Before a run goes unattended, its `runs/` note answers five questions from
[Claude Code's guidance](https://code.claude.com/docs/en/best-practices):

1. **Done**: the outcome and its card.
2. **Check**: the commands or agreed check that show it.
3. **May touch**: worktree and branch, files, game window yes or no, spend cap.
4. **Stops**: cutoff in Windows or engine time, budget, attempts, the stop rules in
   [autonomy](autonomy.md#limits).
5. **Result**: where the report goes; you decide.

A `/goal` condition names the check command and asks for its output. It forbids edits to existing
tests and agreed checks that the brief doesn't list, and it states the cutoff. "Met" only means
stop:
- in Claude Code, a small model judges "met" from the transcript
  ([/goal](https://code.claude.com/docs/en/goal));
- in Codex, the working model marks its own goal done
  ([Using Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex)).

Codex and Claude share this tree, so each session claims its task in
[Active work](state.md#active-work) first.

The handoff note has five headings, adapted from OpenAI's
[ExecPlans](https://developers.openai.com/cookbook/articles/codex_exec_plans):
1. Progress;
2. Surprises;
3. Decisions (and who made them);
4. Not checked;
5. Next.

The next session checks the note against `git`, running processes and files on disk. Permissions
stay in [autonomy.md](autonomy.md): its standing menu and small interviews are agreed; the rest is
still the 2026-10-21 proposal.

## 5. What a report looks like

```text
Change:      add tests/test_repo_rules.py (card agreed <date>)
Checks:      scripts/check.py at <rev>, clean: <n> passed, <n> skipped (no torch); log <path>
Review:      1 finding, fixed; none open
Not checked: imports made through strings
Undo:        git revert <rev>
Status:      passed at <rev>; the check is proposed, not agreed
```

The status is one of:
- proposed;
- agreed but not run here;
- passed at `<rev>`;
- failed;
- skipped;
- unavailable.

A check "passed" only if it ran and someone saw the result
([OpenAI cookbook](https://developers.openai.com/cookbook/examples/codex/iterating-development-workflows-with-codex)).
When you read a report: "If you can't say what the checks would miss, ask for a real review rather
than a quick approval" (claude.dev).

## 6. What to build

Smallest first. Each item gets its own card. Nothing launches a game, spends money or commits as a
side effect.

| Item | What it does |
|---|---|
| B1 `scripts/check.py` | Runs Ruff, the full offline suite (scratch in `runs/test-scratch/<pid>`) and B2. Prints five lines: revision, clean or dirty, counts, skip reasons, log path. Exits non-zero on failure. Both agents call it. |
| B2 `tests/test_repo_rules.py` | `gameai` imports no game; no tracked key, `runs/` or game files; AGENTS.md at most 305 lines now, 200 after the cleanup. Marker problems are listed for you rather than failed on, since only you change markers. |
| B3 More leak tests | A planted fake secret never reaches exports, stills or a new RL observation. |
| B4 Risky-edit warnings | `check.py` prints "needs your yes" when an agreed check's files change, a JUDGEMENT line is removed or edited, assertions are deleted or tests skipped, prompt snapshots are regenerated, or `uv.lock` adds or upgrades a package. |
| B5 Hooks | Only if stage 2 shows checks being skipped (stage 4). At the end of each turn, Claude Code and Codex call `check.py`, skipping the run if nothing changed. Before tool calls, a hook blocks `ruff format` and commits during a queue. |
| B6 One reviewer | `.claude/agents/reviewer.md`: read-only tools and the rules in section 2. Codex runs `/review` with the same prompt. A cross-model review through [codex-plugin-cc](https://github.com/openai/codex-plugin-cc) is optional. |
| B7 Skills | Only for workflows already repeated by hand. One copy in `.agents/skills/` (Codex), symlinked into `.claude/skills/` (Claude Code). |
| B8 Review workflow fix | `wh3-version-review.js` returns "incomplete" when judges fail and calls its winner a proposal. Or retire it if the WH3 loop stays unused. |
| B9 CI, optional | A GitHub Actions job runs `check.py` on each push. The repo is public and the suite needs no game. |

B5's card must handle the hook quirks ([Claude Code](https://code.claude.com/docs/en/hooks),
[Codex](https://learn.chatgpt.com/docs/hooks)):
- Exit code 1 doesn't block, so a small wrapper turns a `check.py` failure into exit code 2.
- Claude Code overrides an end-of-turn (`Stop`) hook after eight blocks in a row with no tool call
  between them.
- A Codex `Stop` hook that exits 0 must print JSON, and Codex loads project hooks only from a
  trusted `.codex/`.

Hooks are "a useful guardrail, not a complete enforcement boundary" (OpenAI). Games, spending and
ledgers stay guarded by refusals in our CLI: `play`, ledger caps and `RuntimeLock`.

Not building:
- Sonar's products, dashboards or coverage targets.
- Repo-wide mutation testing.
- Spec frameworks such as Kiro, which in one trial turned a small bug into 16 acceptance criteria
  ([Böckeler](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)).
- An Inspect port, a type-checker migration or an orchestration framework.
- Anthropic's scale machinery: risk classifiers, voting bug-hunt agents, merge queues, staged
  releases. Anthropic says its ability to spend tokens "far exceeds what any other business would
  realistically want to spend"
  ([Redesigning source control](https://www.anthropic.com/research/redesigning-source-control)).
  Osmani: "you can get surprisingly far with your stock coding harness"
  ([Human judgment doesn't leave the software](https://addyosmani.com/blog/human-judgment-doesnt-leave-the-software/)).

A new tool needs a gap we have seen, a named use and a check that it helps.

## 7. Clean up the docs

Long instruction files are followed less well. Claude Code's docs aim for "under 200 lines per
CLAUDE.md file" ([memory](https://code.claude.com/docs/en/memory)), and Codex stops adding
instruction files at a combined 32 KiB by default
([AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)). Each change below only
moves text, and the link test catches broken links.

- **AGENTS.md** becomes a map under 200 lines. It keeps:
  - the hard rules (verification, judgement, games, spending, ledgers, 1x);
  - the commands, with `check.py` first;
  - pointers to the rest.

  Layout and architecture move to the [WH3 README](twwarhammer3/README.md#how-it-works) and
  `runs/README.md`. `docs/spire/AGENTS.md` gets the same treatment.
- **autonomy.md** keeps current rules only. Its finished
  [overnight plan](autonomy.md#next-overnight-research-and-checkpoint-timing) (130 lines) moves to
  the log, and each remaining rule is marked agreed or proposed.
- **testing.md** keeps the how-to. Its 2026-10-23 review history (113 lines) moves to the log.
- **This page**: each part you agree moves into its home, then this page goes.

## 8. Rollout

JUDGEMENT: Rollout order — Codex, 2026-10-28, proposes agreement, one pilot, then selective tooling.

Each stage is one change you can accept or drop. We "start strict and loosen with evidence"
(claude.dev): the reviewer sees every normal change until the counts below show its findings are
mostly noise.

| Stage | What | Done when |
|---|---|---|
| 1 | B1, B2, B4 with their cards | Each rule fails on a planted violation and passes on `main`; `check.py` matches plain pytest's counts; warnings fire on planted diffs and stay quiet on an unrelated one |
| 2 | One real task through the code loop with the reviewer (B6), such as B3 or B8 | The result and a planted wrong case shown; your minutes, bugs caught (and by which layer) and reviewer noise recorded |
| 3 | The docs cleanup | Links pass; a reviewer finds no rule lost or changed; B2's cap drops to 200 |
| 4 | Hooks, skills, CI (B5, B7, B9) | Only if stage 2 showed checks being skipped or a workflow repeating |
| 5 | The experiment loop, on the next planned free experiment | Card committed first; warnings and rerun review used; report in the agreed shape |

The proposed capacity limit in autonomy.md (not yet agreed) keeps at most three changes waiting for
your review ([limits](autonomy.md#limits)).

### Checking the process itself

JUDGEMENT: Pilot assessment — Codex, 2026-10-28, proposes the cases and observations below.

Try these on saved examples or throwaway changes; never trigger a forbidden effect for real.

| Situation | Expected response |
|---|---|
| Agreed card, passing checks | Finish without asking again |
| Behaviour or acceptance rule unspecified | Draft the card; stop dependent work |
| A planted bug passes the tests | Add the missing check before claiming correctness |
| A check skipped, missing or crashed; the review returned nothing | Report incomplete, not success |
| Code or a check changed after its pass | Rerun at the final state; keep the old result as old |
| Scoring, test data or a permission boundary involved | Name that exact choice and park it |
| A session ends with work running, then resumes | Check what is really running; repeat no launch, spend or finished step |

Report each case separately; there is no overall score. Without a dashboard, count:
- per change: reviewer findings (real or noise), questions asked, and your minutes if you share
  them;
- in the log: bugs found after "done". The Claude Code team on reverts and incidents: "if they
  rise, we haven't saved human time, we've only moved it" (claude.dev).

After about five changes you keep, simplify or drop each part. After a model upgrade, drop steps
that no longer catch anything
([Anthropic](https://www.anthropic.com/research/harness-design-long-running-apps)).

## Decisions

1. **Can one agreed card cover later fixes in the same area?**
   - No
2. **Where is a reviewer worth it?** Proposed: the reviewer on normal changes, the rerun reviewer
   on every number for your pages, and `check.py` alone for trivial edits.
   - Yes
3. **Build stage 1 first?** Recommended: `check.py`, the repo-rule tests and the risky-edit
   warnings. `check.py` runs the whole offline suite before every commit (the Exit gate marker),
   where Codex proposed a focused selection (the Verification depth marker).
   - Yes

Hooks, CI, skills, the docs cleanup and cross-model review wait behind these three.

## Sources

Links are inline; [references.md](references.md) lists every source with its status. "claude.dev"
(Osmani and colleagues, 2026-10-15) describes the Claude Code repo, not Anthropic's whole monorepo.

- All sources were read on 2026-10-28 or 2026-10-29, and a second agent re-checked each quote.
- Anthropic's figures are its own reports.
- Sonar's pages are vendor marketing: we borrow layer names, not product claims.

Whether this process saves your time here will only show in the [rollout](#8-rollout).
