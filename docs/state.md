# Project state

Updated 2026-10-22: what runs, where each game stands, what comes next. Status only:
History: [WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md), [first combat](spire/first-combat/README.md); directions: [owner-direction.md](owner-direction.md).
Under the [hard rule](../AGENTS.md#verification-hard-rule), only listed agreed checks are verified at their recorded revisions; gameplay findings below remain unverified.

## Active work

WH3 first; Spire waits behind it; post-training is secondary. Three changes await review.

No game, benchmark or paid job is running. The 2026-10-22 night ($0, game 02:37-07:28) ran
the starting-set screen and a shortcut screen ([log](twwarhammer3/log.md#2026-10-22-the-starting-set-screen)):
neither new card (line, expendables) nor either probe goes to confirmation.

Scripted split-army [team](twwarhammer3/multi-agent-implementation.md) (b49): agreed checks passed
(component at `e8d1eda`, live at `45fe7b0`). The model team is on `wh3-model-team` ([review fixes](twwarhammer3/log.md#2026-10-21-night-team-code-review-and-fixes-on-the-branch)); the agreed live check passed 4/4 at its tip on 2026-10-22; model members have not played live.
[Scope](twwarhammer3/benchmark.md#scope-and-first-release), [evaluation guidelines](twwarhammer3/evaluation-guidelines.md#13-owner-decisions-these-rules-need), suite, remaining checks and gates are proposals; [Empire items](twwarhammer3/empire.md) pending.
The October 21 offline window's evidence is in the [log](twwarhammer3/log.md#2026-10-21-a-proposed-starting-set-the-failure-rule-recount-and-a-blind-c1-recount) and `runs/twwarhammer3/away-20261021/`. Waiting changes: 3 of 3 ([branches](#branches)).

The local codebase and state overview is built at `runs/project-overview/index.html`
([build instructions](../README.md#project-overview)): game loops, module guide, evidence,
current work and pending decisions. [Traces must support RL](posttraining.md#beyond-supervised-fine-tuning).

## Total War: WARHAMMER III

Current priority: establish a small, repeatable battle benchmark. Scripted-team checks passed
at the recorded revisions; the model team has offline evidence and a passing live check at its tip. The chariot is still the only card: no battle in the starting-set screen goes to confirmation.

[README](twwarhammer3/README.md), [log](twwarhammer3/log.md) ("On main" at the top), [benchmark](twwarhammer3/benchmark.md), [tactic cards](twwarhammer3/tactic-cards.md), [latency plan](twwarhammer3/latency.md), [results](twwarhammer3/results.csv).

- On `main`: `llm`/`llm_rules` v22, `commander` v8, skills v1.2, harness b49, evaluator v2,
  track `obs-v4+terrain/act-v2/live-1x` ([definitions](twwarhammer3/log.md#on-main)).
- Benchmark: [the chariot card](twwarhammer3/tactic-cards.md#the-chariot-card-the-first-benchmark-card);
  results in the [b40 round](twwarhammer3/log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40).
  No model has won above its foils' bound (an unverified gameplay finding).
- Spend: OpenAI $51.47 of $52; WH3 OpenRouter ledger $21.33 ($8.84 the Empire night).

Next (proposals for the owner; [release route](twwarhammer3/benchmark.md#route-to-the-first-release)):
0. Read the Empire [results](twwarhammer3/empire.md#results) and [owner items](twwarhammer3/empire.md#for-the-owner-to-decide); screen/readout and line marker agreed October 21.
1. Agree remaining [correctness checks](twwarhammer3/benchmark.md#correctness-checks-to-agree) and chariot choices; failure rule, witness v2 at 2 s/2 s and c1 preservation already agreed. The c1 [rerun handoff](twwarhammer3/benchmark-run.md#independent-rerun-acceptance-proposal) stays local in `runs/twwarhammer3/away-20261021/handoff-c1/`.
2. Breadth: the [starting set](twwarhammer3/tactic-cards.md#the-starting-set-proposal-2026-10-21) ran 2026-10-22: floors won the line and the rifle lane, and the expendables' named shortcut won 3 of 3. New cards need your choice of battles or redesigns (the expendables would need a battle where waiting for the pin matters; two threats would get one step). Prompt v22 says only contact wins count on these cards (unplayed).
3. Choose P5's question before more chariot cells; its Kimi plans are unplayed. A stronger model at modifier 1.1 remains untested (OpenAI cap).
4. [Robot team plan](twwarhammer3/robot-team-plan.md), [research guide](twwarhammer3/robot-team-research.md): useful recovery? Only 1 of 17 recorded line battles had a replacement opportunity ([review](twwarhammer3/robot-team-plan.md#1-establish-a-recoverable-coordination-problem)); b46–b48 unplayed.

## Slay the Spire

Paused behind WH3. No full run has won; the furthest reached Act 4, floor 54.
Next choice: a meaningful comparison of the current controller, or a freeze.

[README](spire/fullrun/README.md), [log](spire/fullrun/log.md), [results.csv](spire/fullrun/results.csv). v10 on `main`; floor 54 was v8.
Version differences sit within run-to-run variation (about 11 floors on one seed; same-harness replays differed by 13–26), measured only on three tuning seeds. `HELDOUT01`–`HELDOUT10` unplayed.
Spend: OpenAI $2.52 of $25, OpenRouter $0.25. The comparison and `v11-keys` wait; [open questions](spire/fullrun/README.md#open-owner-decisions). Paused: [first combat](spire/first-combat/README.md); planned: [open-weight](spire/open-weight/README.md).

## Post-training

Secondary priority. Capture, export and dataset smoke checks passed; there is no learning
claim. A training host, a way to play fine-tuned models, and useful targets are still missing.

[Plan and data-use choices](posttraining.md).

## Known issues

- `runs/` has no backup (23 GB, 7.1 GB without `checkpoints/`); the owner said not now (2026-10-21).
- Check OpenRouter credits before paid jobs: on 2026-10-21 the account showed $24.26 used of
  $60, the ledgers $2.68 less. OpenAI caps and the shared OpenRouter allowance are kept by hand.
- Pinned OpenRouter backend outages count against the model; Step 5 preview is unpinned.
- No test yet shows whether a game patch changes results (owner: later). A build warning
  shows in `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- WH3 register and `stats`: blank version on benchmark rows, grouping by commit, API failures
  as `policy_failure` (`card` classifies failures, keys by setup); a defender's timer stalemate
  counts as won (3 rows; `stats` ignores `ended_by`; the card and the Empire review do not).
- The mod sets 1x once, then reports constant `speed` 1 and `awaiting_orders` false: per-observation paused/slowed tests cannot fail; only the team check's clock ratio detects slowdown.
- No automated checks for report JavaScript or several Spire play-loop stop paths. Spire's
  Workshop mod pins still block a run when a mod updates.

## Owner decisions waiting

1. **Benchmark rules and checks.** Agree the remaining checks and the criteria for a first benchmark release.

   Still proposed: [scope, suite and gates](twwarhammer3/benchmark.md#scope-and-first-release), [correctness checks](twwarhammer3/benchmark.md#correctness-checks-to-agree), [evaluation choices](twwarhammer3/evaluation-guidelines.md#13-owner-decisions-these-rules-need) and chariot [decisions 3–5](twwarhammer3/tactic-cards.md#second-pass-2026-10-19-evening-findings-and-the-version-2-decisions) on gate sizes, reporting and drops. The failure rule, c1 preservation and witness v2 at 2 s/2 s are already agreed. Until the rest is settled, there is no verified benchmark release.
2. **Next experiments and spending.** Choose the next free game night and how to divide the remaining allowance.

   The $0 [starting-set screen](twwarhammer3/log.md#2026-10-22-the-starting-set-screen) ran 2026-10-22 and admitted no card to confirmation; choose which battles to screen next (the chariot remains the only card). Model and team screens together fit only their central cost estimates. Choose P5's question and [$20 cap](twwarhammer3/latency.md#owner-decisions), [Kimi's role](twwarhammer3/empire.md#for-the-owner-to-decide), and whether to raise OpenAI's $52 cap (Sol is refused; gpt-6.1-sol low cost a median $0.84 over 22 battles). No new paid plan is authorized by these estimates.
3. **Standing autonomy rules.** Accept or revise the proposed rules for work while you cannot review.

   [Away guidelines](autonomy.md): the October 21 window used the proposal, not its agreed trial. Reviews caught 114 errors in drafts and commits, 113 fixed. Existing offline delegation continues; it does not settle the standing rules.
4. **Model-team behavior and readiness.** Decide the remaining behavior and check changes before adopting the model team.

   The $0 live rerun passed 4/4 at the tip `31823f3` (2026-10-22); merging needs your yes on the rest. Pending: the stricter movement witness; members cannot target out-of-sight enemies while the single controller can (11 of 24,248); member cleanup bugs replace an engine ending with policy failure while a single controller keeps it. The agreed ledger test now includes `team_llm_rules`; outer-validation assertions were dropped from the agreed team test ([review](twwarhammer3/log.md#2026-10-22-second-review-two-team-fixes-and-the-screen-reader)); keep these changes? Cut-off member calls reach the ledger but not register costs. Already chosen under delegation, reversible: a round-robin structure screen first (single, two, per class, per unit, planner groups; 3 each; about $10, up to $17), instead of two-member 6 + 6; Stage D's selection rule still needs care ([defaults](twwarhammer3/team-structures.md#8-choices-made-for-the-owners-review)). Model members have not played live.
5. **Campaign permissions.** Separately allow or refuse harness saves and irreversible Steam achievements.

   These choices are required before any campaign launch. Deferring keeps campaign work to [offline drafts](autonomy.md#wh3-campaign-infrastructure).
6. **Controller direction.** Adopt or drop the attack-route prompt change; keep or defer the commander approach.

   Recommended: adopt `wh3-rules-v21-attack-path` as its own renumbered `llm_rules` version after the contact-scoring change. `commander` is unplayed since v4; [controller plans](twwarhammer3/controllers.md) remain proposals.
7. **Backend and sampling policy.** Review the delegated backend pins and decide sampling capture and serving-fault treatment.

   b36's [backend pins](twwarhammer3/latency.md#owner-decisions) await review. Recommended: request log-probabilities, seed and explicit sampling where the pinned backend advertises them ([gaps](posttraining.md#beyond-supervised-fine-tuning); listings rechecked October 21, not a capture test). Choose how to report or rerun [garbled replies](twwarhammer3/empire.md#for-the-owner-to-decide); current backend failures count against the model.
8. **Training preparation.** Choose a host, serving route and teacher; decide when and how to build the Empire dataset.

   Secondary priority. [Data-use choices](posttraining.md#provider-terms): OpenAI outputs (25,503 rows excluded: Spire 11,099; WH3 14,404), GLM-5.3 or rejection-sampled Qwen3.6; Step 5 weights are public. An [Empire content screen and dataset timing](twwarhammer3/empire.md#for-the-owner-to-decide) are still needed. Smoke checks establish no learning gain.
9. **Spire's next step.** After WH3, run one meaningful comparison or freeze this track.

   Proposed comparison: current controller against ablated scaffolding, 20–30 fresh seeds per arm, about $5 and three nights. `v11-keys` waits on that choice; [other Spire questions](spire/fullrun/README.md#open-owner-decisions) stay secondary. No held-out seeds have been played.

## Runtime and ownership

- Slay the Spire ([runtime facts](spire/integration.md#runtime-and-source-pins)): the installed game and personal profile slot 0 are authorized, including stats, unlock progress, history and achievements (Ironclad unlock 3 of 5; runs record profile evidence).
- WH3 ([engine facts](twwarhammer3/integration.md)): a launch's mod list and startup-video
  skip persist for ordinary Steam launches ([how to reverse](twwarhammer3/README.md#commands)).
  Steam auto-update stays on.
- Also authorized: game windows, local GPU work, commits and pushes to public `main`, and
  paid API use within each ledger's cap. One game controller at a time across both games
  (each game's lock and process check cover only that game); one GPU job at a time.

## Branches

- `v11-keys` (`cd97667`): Spire v11 keys memory, on v10 (`54a5967`).
- `wh3-rules-v21-attack-path` (`5baf28b`): WH3 `llm_rules` attack-route draft, labelled
  v21 before main's v21 (`18dabdd`); renumber before any merge.
- `wh3-model-team` (`31823f3`, worktree `../slay_the_spire_ai-wh3-model-team`, from `9e43143`):
  two model members on one army (`team_llm_rules`), reviewed at `73e2ccd`, its 2026-10-22 fixes by
  one skeptic; offline checks pass; the agreed live check passed 4/4 at the tip (2026-10-22).
- Archived drafts are tags (`git tag --list 'archive/*'`).
