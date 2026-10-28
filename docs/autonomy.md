# Working while the owner is away

What Claude Code and Codex may do alone when the owner cannot review or decide. The
[standing work menu](#standing-work) and small interviews were agreed on 2026-10-28.
The other general rules below remain the 2026-10-21 proposal unless separately agreed.
The [overnight plan](#next-overnight-research-and-checkpoint-timing) ran on 2026-10-28
(02:39-04:35; [report](twwarhammer3/log.md#2026-10-28-overnight-restore-pauses-were-wsl-clock-steps-land-check-passes-at-dcb8b5a)).
[AGENTS.md](../AGENTS.md) still applies. The [owner's direction](owner-direction.md) is to
reduce their bottleneck through objective, testable work, without accumulating errors or
unused features. Success is a useful finished change or evidence that makes an existing
decision easier. Time occupied, tests added and branches produced are not success measures.

## When it applies

- The standing menu applies to future requests for autonomous progress. Once the remaining
  general rules are accepted, tasks within them need no further yes. Until then, use existing
  authorization for offline work; saving a plan does not activate a run or the whole proposal.
- **Long autonomous runs** (owner, 2026-10-28; formerly "overnight runs"): a long window of
  autonomous work while the owner is away, by day or by night. Game time still follows
  [game time](#game-time) and needs a free PC.
- **Busy**, or no clear game window: offline work only; the owner may be using the PC.
- **Away**: the owner gives a return time and frees the PC, subject to [game time](#game-time).
  At the cutoff or an owner message, stop game work through the existing stop procedure
  unless they explicitly keep the window open. A status question does not cancel authorized
  offline work. New directions supersede conflicting work.
- The [limits](#limits) are shared across agents and sessions. A new day, message or session
  does not clear pending review. Check [Active work](state.md#active-work) and live process
  handles before claiming a task or the game; an old status line alone proves neither idle
  nor running. Record the task, responsible agent and artifact there; one writer per task.

## The test

Classify by the action's effects, including the code it calls, not its filename.

1. **Stop that action** if it exceeds authorization: spending or game time, new external
   writes, profile changes, achievements, deleting evidence, re-pinning, changing/resetting
   ledgers or credit, or making anything public (including pushes). An allowed game plan
   includes the existing documented pack/mod-list/startup writes and normal ledger appends
   within its cap; it does not authorize new side effects. Campaign access has a separate gate.
2. **Respect harness refusals** and pending permission requests. Use the required approval
   route; never rephrase, switch tools or edit instructions to evade a refusal. Record it
   once and continue independent work. These guidelines do not change sandbox permissions
   ([Codex permission controls](https://learn.chatgpt.com/docs/agent-approvals-security)).
3. **Park adoption** if it changes benchmark meaning: scenarios, suites, scores, gates,
   verdicts, failure rules, held-out sets, model prompts/observations, agreed check criteria,
   benchmark definitions, historical register rows, or training/data/teacher use. The same
   applies to a bug fix with those effects. Prepare the smallest comparison that could
   settle the choice, with affected-row counts where relevant; preserve the original data.
   Do not implement every alternative. Attach it to the existing inbox item, or add one.
4. **Otherwise decide locally**, within the limits below: use the smallest implementation
   and relevant check. Ordinary engineering choices need no ratification. Record a meaningful
   default with its reason and undo step; put routine details in the commit message.

## Choosing work

First finish or stop running work safely ([stopping](twwarhammer3/benchmark-run.md#stopping)).
Then prioritize work the owner named, evidence for the decision blocking the next milestone,
and objective roadmap features useful across the unresolved choices. Inspect existing
artifacts first. Prefer finishing or simplifying a draft over opening another line of work.

Before starting, write a few lines in the existing task note or `runs/` folder:
**what this unblocks; what already exists; the next observable result and its reference;
what will be retained; the time/attempt bound and stop condition.** Reuse a command or test
before adding one. A new script or abstraction needs a named consumer in the current plan.
If work is useful only after an owner choice, limit it to the cheapest discriminating probe.

At the bound, keep the result, narrow the task, or park it with the reason. Repeat a scan,
experiment or review only for changed inputs or a specific unanswered question. A negative
result can finish a task. If no permitted next step will change a decision or finish useful
work, leave one resume condition and stop; do not fill time with more audits, research,
documentation, speculative features or a workflow framework. No new doc pages or public CI.

## Standing work

Owner, 2026-10-28: consider all five areas when asked to make autonomous progress; select
a bounded task for the window rather than trying to cover everything every night.

| Area | Useful outcome and existing home |
|---|---|
| Thesis research | A source-backed research comparison or resolved feasibility uncertainty in the existing [directions](thesis/directions.md) and [papers](thesis/papers.md). Robotics and multi-agent work matter; the exact topic, RL/MARL, post-training and benchmark contribution remain open. |
| Decisions | Accurate [JUDGEMENT markers](judgement.md) and small owner interviews about consequential choices, before implementation where possible. |
| Correctness and tests | Evidence about important behavior, a meaningful regression or a stated verification gap; reuse [testing guidance](testing.md) and [agreed checks](agreed-checks.md). |
| Code and repository upkeep | Simpler, readable code and organization; corrected stale references; justified cleanup proposals with preserved evidence. Compare how well-known research repos build benchmarks, evaluations, infrastructure, tests and workflows, and adopt the parts that fit (owner, 2026-10-28). |
| Agent workflow | Less repeated context reading, duplicated notes, confusing handoffs and unnecessary tool work; keep only improvements whose benefit can be assessed. |

When the owner is available, ask at most three consequential questions at a time. Explain
current behavior, evidence, alternatives, the recommendation and what each answer changes.
Keep unanswered choices in the relevant page, with only the next decisions surfaced in
[state](state.md#owner-decisions-waiting). Deferral does not settle a choice.

Check old marker candidates against the code before copying them. Follow placement exceptions
and preserve unresolved markers. Include relevant branches and untracked thesis drafts in a
review: `git grep` alone misses the latter. The owner chose to keep thesis pages untracked.

Use the existing pages, not another dashboard or decision registry. At handoff, assess useful
work retained, corrections needed and review burden. Look for workflow improvements from
observed friction; make small changes, and do not claim token savings without measurements.

## Checks

Write the expected behavior and independent reference before implementing it; a check-first
approach does not require a new test for every edit. Reuse focused checks. For a bug, retain
the failing-before evidence where feasible; for important new checks, show they reject a
plausible wrong implementation. Snapshots and agreement between readers of the same source
do not independently establish correctness. Run the relevant AGENTS.md commands.

Record command, source revision (and diff if uncommitted), inputs, passed/failed/skipped or
unavailable checks, and the narrow conclusion. New checks stay **proposed, not yet agreed**;
only explicit owner agreement changes that status. An agreed method is verified only where
it passed, and only for its stated scope. Do not feed official scores from proposed checks.

A passing component check permits further draft work only within the same bounded change
and the behavior actually exercised. Rerun relevant dependency checks at the resulting tip.
Stop at the first missing live readback, failed dependency or owner design choice; do not
stack another feature on an assumed result. Do not weaken agreed assertions or criteria.
New branch-local regressions are allowed even in a suite used by an agreed method; they
remain proposed. Any changed expectation is a separate, visible review decision.

## Code and main

- Runtime and experiment code stays on local, unpushed branches in worktrees outside
  `/tmp`, with its tests. Check the actual command's source scope in AGENTS.md: first-combat
  tools include `scripts/`. A diagnostic filename does not exempt experiment behavior.
- `main` may receive small factual docs and independent offline checks outside the park
  list, with whole diffs that are yours and relevant checks passing. No commits while a
  queue runs or owns a frozen revision for an imminent start. WH3 `report` groups by full
  source revision, so even docs commits can split later groups; prepare named batches
  against one fixed revision. Do not rewrite historical revisions to combine them.
- Before a launch, commit the Active work line with responsible agent, purpose and cutoff,
  then freeze the plan at that revision. Other agents do not commit to that checkout until
  its owner confirms the process ended. Draft elsewhere while it runs.
- These guidelines, their AGENTS.md summary, agreed-check rows and queue stop logic are
  not self-editable during an absence. `owner-direction.md` records owner words verbatim.

## Game time

Only while **away**, for plans the owner named for that window; agreed-check reruns; and
`twwarhammer3 launch` + `menu` infrastructure probes with their check written first. Earlier
stopped plans or unplayed arms need a new go-ahead. A proposal is not a named plan. Paid
model screens and new battle questions need explicit scope and budget. Probes never use
`play`/queues or produce benchmark register rows, scores or training inputs. Authorized play
plans retain their normal evidence/register writes; historical corrections stay parked.

Set the cutoff at least 60 minutes before return. `launch --timeout` and each play job's
explicit `--run-timeout` must fit before it, allowing for preparation and shutdown. Queue
`start_before` only prevents the next job: set it early enough that the longest remaining
job plus preparation/shutdown fits. Do not launch if that bound is unknown or cannot fit;
use the existing stop procedure if running work threatens the cutoff. Write to absolute
paths in the main checkout's `runs/`; branch probes record their commit and pack sha256.
For a multi-launch agreed check, budget the whole procedure including restoration. Its
safe stop ends test phases and completes already-authorized restoration (which may launch
again); an explicit immediate-shutdown request takes precedence, with unfinished restoration
reported. Defer a check whose cleanup cannot fit the window or be safely interrupted.

## WH3 campaign infrastructure

The first two independent drafts are a save guard tested on synthetic files, then checks
that mod scripts stay inert in a campaign unless the session asks. The guard compares a
sha256 manifest of `save_games` and `preferences.script.txt` before/after: earlier files
must be byte-identical. A newly appearing file is not proof of harness ownership. Cleanup
requires an exact recorded harness-created path and authorization; unexpected files stay
untouched. Do not automatically restore an owner file that changed.

Before loading any campaign map (including the built-in campaign benchmark), the owner
decides separately on harness saves and irreversible Steam achievements. Until then, stop
at those offline drafts. Once authorized, proceed one live capability at a time: start,
heartbeat/state readback, end turn, move, recruit, save/reload/compare, autoresolve, battle
handoff. Each needs its own observed readback before the next depends on it.

Use a faction with no owner saves, check cloud saves are off, never use "continue", change
no campaign setting and skip no AI turn. Readbacks do not reach a policy. Campaign choice,
policy information, turn-time rules and scoring stay owner decisions. Put measured options
in the existing inbox and facts with evidence limits in [integration.md](twwarhammer3/integration.md).

## Limits

Defaults until review: **3 waiting changes**, each with one outcome the owner can accept or
discard separately; at most 3 branches, 10 reported choices and 10 inbox items. One large
campaign branch does not count as one change. Count carried-over drafts too; do not hide
overflow in `runs/`, another agent or a catch-all question. At capacity, finish, correct or
simplify existing work; do not start another change. Preserve rejected evidence and record
why a draft was dropped. Branch capacity reopens when a change is accepted or discarded,
not when its code is copied elsewhere. Do not exceed the remaining choice/inbox limits.

Spending defaults to $0 per window unless the owner names a cap, within existing ledger
caps and the shared allowance; count ledger/account use conservatively. No training, large
copies or heavy CPU/GPU work while WH3 runs or the owner may be using the PC. Stop game work
on unexpected closure, spend at a $0 cap, changed owner files, two consecutive failed
launches, or WSL restart (no automatic resume). Report a new game build; it does not itself
stop play and is never re-pinned alone (owner, 2026-10-18).

## Applying the rules

| Current work | Useful stopping point |
|---|---|
| Failure-rule decision | Reuse the existing recount; compare only unresolved options against raw cases. Keep official scores unchanged. |
| Preserve the engine ending | A local regression and minimal fix retaining the raw ending; changing which result counts is a separate decision. |
| Chariot scorer check | Inspect the existing mutation results; an unchanged verdict alone is insufficient. Add only a demonstrated missing check. |
| Campaign infrastructure | Synthetic save-guard check and inert-script check; no speculative campaign controller beyond the live-access gate. |
| Prompt/held-out/training choice | One measured recommendation and relevant alternative; do not build a family of versions or consume held-out evidence. |
| All useful next steps blocked | Record what would unblock them and stop. More artifacts are not a substitute for that decision. |

## On return

- **One report**, at most 20 lines in the game's log, linking evidence instead of copying
  it: completed outcomes, ready drafts, rejected approaches, checks with revision and n,
  spend/game time if used, meaningful defaults with undo steps, and refusals. Separate
  completed delegated work from proposals needing a decision; no blanket ratification.
- **One inbox**, [Owner decisions waiting](state.md#owner-decisions-waiting), at most 10
  items of at most 3 lines. Each gives the recommendation, relevant alternative, evidence
  link, consequence of deferring, and exact scope of approval. Surface at most three that
  unblock the most work. Keep the rest linked. Consolidate duplicates without losing the
  owner's wording or unresolved choices; only their answer settles a decision.
- For a ready code change, show its final diff, check evidence and remaining uncertainty
  before asking to merge. For a check, agreement on its method is distinct from accepting
  code or a benchmark conclusion. Silence approves nothing; partial answers release only
  the relevant work.
- Try this first on one offline batch within these limits. At review, assess useful work
  retained, corrections/discards, remaining decisions and the owner's actual review effort.
  Broaden delegation only by explicit agreement after that evidence; a tabletop review of
  these rules cannot establish that the workflow reduces errors or review time in practice.

## Next overnight: research and checkpoint timing

Saved 2026-10-28 at the owner's request; **ran that night** (02:39-04:35, at the owner's
explicit start). A rerun needs the owner's explicit start; record the start, return time and
game cutoff then. No clear game
window means offline work only. This is the selected mixed research/review plan, with $0
model spending and the conditional free timing diagnostic the owner selected. It does not
resume the stopped checkpoint-RL training or choose a thesis topic.

### Allocation and limits

JUDGEMENT: overnight_allocation — Codex, 2026-10-28, proposes the time split below within
the owner's roughly ten-hour window. Another split changes research depth versus review;
these are planning ceilings, not required work counts or verification thresholds.

| Allowance | Work and stopping point |
|---|---|
| 30 minutes | Recheck revision, processes, permissions, pending drafts and existing evidence. Record the task, responsible agent, absolute cutoff and one evidence directory under the main checkout's `runs/`. |
| 4 hours | Extend and challenge the thesis frontier map; retain a concise comparison and source-backed corrections. |
| 3 hours | Finish the bounded checkpoint timing investigation; at most 45 minutes of conditional live work, including cleanup. |
| 1 hour | Independent review of consequential research/timing claims, then targeted documentation, readability and workflow cleanup. |
| 1.5 hours | Consolidate results, run relevant checks, prepare up to three owner questions and leave the next concrete step. |

Ten hours is a maximum, not a target to fill. If timing work finishes early, use the remaining
research allowance for a named unresolved comparison. Stop when no permitted next step can
change a decision or finish useful work. Do not repeat unchanged audits to occupy the window.

Four unmerged draft branches were present at planning, above the older proposal's three-branch
cap. Preserve them; open no new runtime implementation branch in this plan. Attach findings
to the existing thesis/checkpoint work. No new dashboard, generic test framework, speculative
infrastructure or exhaustive repository sweep. New scripts need a named use in this plan.

### Thesis frontier

JUDGEMENT: first_frontier_pass — Codex, 2026-10-28, proposes the three areas below for this
first mixed night. A different emphasis could surface other thesis candidates; this search
does not rank or select the thesis, and leaves the other documented directions open.

Start with the existing thesis notes and their research evidence; extend these comparisons:

- Checkpoint-based curricula and sample-efficient learning, including MARL and non-LLM
  policies. Distinguish demonstration-based starts such as
  [Backplay](https://arxiv.org/abs/1807.06919) from
  [reverse curriculum generation](https://proceedings.mlr.press/v78/florensa17a/florensa17a.pdf)
  and critical-state restarts such as [RICE](https://proceedings.mlr.press/v235/cheng24j.html).
  Restoration alone does not establish that a method's assumptions fit WH3.
- Heterogeneous teams, changing capabilities, coordination and unfamiliar teammates.
- Repeatable decision evaluation, counterfactual continuations and coordination under
  real execution delay. Keep decision-table evaluation distinct from closed-loop battles.

For each promising direction, record the closest primary sources and what they already
establish; the possible remaining contribution; WH3's useful properties and alternatives;
the robotics connection and its limits; required capabilities and missing evidence;
estimated game/data/compute cost; and the cheapest next step that could change the choice.
Check current literature and relevant methods/results, recording source versions, dates,
what was actually read and search limits. Abstract-only or inaccessible claims stay qualified.

Keep benchmark-only, learning-only and combined theses open. Distinguish centralized control
of several units from decentralized multi-agent learning. Treat the current support-prediction
proposal as one candidate. One failed training method cannot rule out RL, and an unsuccessful
literature search cannot establish novelty. Do not build an algorithm or collect a new dataset.
Update existing thesis pages; detailed evidence stays in the named `runs/` directory.

### Checkpoint timing investigation

Question: do the reported periodic pauses reflect simulation stalls, timestamp artifacts,
or evidence that cannot distinguish them? The planning review found a discrepancy between
WSL observation timestamps and simultaneous Windows native-tick timestamps in saved Stage 1
runs. This is a lead to reproduce, not a verified cause or proof of continuous 1x execution.

1. Recount the six completed attempts in `runs/twwarhammer3/rl/stage1-20261026/`, comparing
   observation battle times/`read_wall` with native ticks/Windows `wall_time`. Use the saved
   Land check `runs/twwarhammer3/checkpoint-check-20261025c/` as additional existing evidence.
   Preserve originals; retain a small reproducible recount and report counts, durations,
   largest gaps, offset changes, missing samples and concrete examples.
2. Trace timestamp producers and relevant consumers. Both existing wall timestamps use
   `time.time()`; native log timestamps come from the Windows Frida receiver, not directly
   from the simulation. Establish which written claims or timing measures depend on them;
   do not expand into a general timing rewrite or silently rescore old results.
3. Challenge the analysis with synthetic records: a wall-clock jump with continuous ticks
   and monotonic time; an elapsed-time gap without tick progress; missing/batched messages.
   It must distinguish supported cases or say "undetermined". Do not induce pauses in WH3.
4. If a named uncertainty remains, use the conditional live diagnostic below once. If the
   existing evidence resolves the question, skip live work.
5. Correct unsupported current statements and append a dated correction to historical
   claims, preserving the original evidence. Separate observed discrepancies, inferred
   causes and unresolved possibilities. Mark consequential choices at their proper sites.

The owner selected this diagnostic method on 2026-10-28:

- Run the unchanged [Land checkpoint check](../tests/twwarhammer3/check_wh3_checkpoint.py)
  on main: source battle, two identical restores and one changed-order control. Its existing
  restoration verdict stays separate from the timing diagnostic; no RL branch is needed.
- Alongside it, a passive sidecar in the evidence directory samples Windows
  `time.time_ns()`/`time.perf_counter_ns()` at 10 Hz with sequence numbers. WSL records each
  received pair with `time.time_ns()`/`time.monotonic_ns()`. Keep native logs unchanged.
  Bound and clean up the sampler with the check; it sends no game controls.
- Compare within-clock elapsed intervals and offset changes with native tick progression
  and Lua battle time. Windows elapsed time is an independent clock reference; message
  arrival includes transport/scheduling delays. Sampling and receiver timestamps cannot
  establish absence of every simulation stall. Add no timing pass threshold.
- Allow one four-launch check, at most 45 minutes including cleanup, finished at least one
  hour before return. Do not start unless the whole bound fits. No automatic repeat.
  Respect harness refusals, unexpected closure and the existing safe-stop procedure. An
  unsupported checkpoint build blocks this diagnostic; report it without re-pinning.

If live work is unavailable or inconclusive, retain the offline result and exact remaining
uncertainty. Do not add a timing entry to agreed verification merely because the diagnostic
was permitted or passed its synthetic cases. The existing restoration method is unchanged.

### Checks and handoff

Use the behavior and independent references above; add no coverage-percentage target or
tests that merely mirror the implementation. Run focused checkpoint tests if their analysis
or checks change, documentation-link tests for documentation changes, and
`uv run --locked ruff check .`. Keep pytest scratch directories inside `runs/`. Report
commands, source revision/diff, input counts and passed/failed/skipped/unavailable checks.
Component tests do not establish live effects; new methods remain proposed unless agreed.

An independent reviewer challenges consequential research claims and timing conclusions.
Do not change benchmark meaning, scoring, observations, training gates, historical results
or agreed criteria without an owner decision. Cleanup stays within the touched material.
Assess workflow friction at handoff; retain only small, justified improvements and state
their observed benefit or uncertainty. Do not edit autonomy rules during the absence.

The morning handoff gives the research comparison and timing result, checks and limitations,
any small cleanup/workflow improvement, and up to three questions that unblock further work.
Keep the log summary within about 20 lines, link evidence, and update status with the next
step. Success is reduced uncertainty and manageable review effort, not hours occupied,
paper counts, test counts or newly created branches.
