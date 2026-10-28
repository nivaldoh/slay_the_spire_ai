# Project state

Updated 2026-10-28: what runs, where each game stands, what comes next. Status only:
History: [WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md), [first combat](spire/first-combat/README.md); directions: [owner-direction.md](owner-direction.md).
Under the [hard rule](../AGENTS.md#verification-hard-rule), only listed agreed checks are verified at their recorded revisions; gameplay findings below remain unverified.

## Active work

WH3 first; Spire waits behind it; post-training is secondary.
Standing work (owner, 2026-10-28): thesis frontier; decisions/`JUDGEMENT` and small interviews;
correctness/tests; code/repository upkeep; agent workflow efficiency. [Menu](autonomy.md#standing-work).
**Finished:** the [overnight plan](autonomy.md#next-overnight-research-and-checkpoint-timing)
and its backlog (2026-10-28 02:39 to 04:35; Claude Code, the only session; commits and
pushes). Your answers of 2026-10-28 are applied ([direction](owner-direction.md)). Night plan and evidence: `runs/overnight-20261028/`. $0. Game work
done (12 min). Report:
[log](twwarhammer3/log.md#2026-10-28-overnight-restore-pauses-were-wsl-clock-steps-land-check-passes-at-dcb8b5a)
(the "pauses" were WSL clock steps; Land check passed at `dcb8b5a`; 15 thesis notes,
[index](thesis/notes/README.md)). The thesis [proposal](thesis/proposal.md) is one candidate,
not a selected topic; [directions](thesis/directions.md), [papers](thesis/papers.md) remain open.
The [memory investigation](thesis/memory-investigation.md#conclusion-from-the-overnight-investigation-2026-10-27)
is retained as history; its policy benefit and the new proposal's novelty remain unproven.
Checkpoint review finished; all game controllers stopped. The declared siege cases and
manual-tower checks passed; other cases remain unverified ([scope](twwarhammer3/checkpoints.md#siege-check),
[log](twwarhammer3/log.md#2026-10-25-siege-checkpoint-checks-pass-for-declared-cases)).
Land Battle definition: the [owner interview](twwarhammer3/benchmark-implementation.md#owner-interview-one-land-battle)
focuses on one battle, model knowledge, API latency and scoring; the earlier profile/checks remain proposals.
Battle [checkpoints](twwarhammer3/checkpoints.md) restore exactly and are on main; the agreed
check passed at `6fdb271` ([log](twwarhammer3/log.md#2026-10-25-battle-checkpoints-restore-exactly-through-a-fast-rebuild));
the player tool is public (github.com/nivaldoh/wh3-battle-checkpoints, v0.1.0).
Latest testing: [eval review](testing.md#wh3-evaluations-and-tests-2026-10-23),
[live-check comparison](testing.md#wh3-live-check-comparison-2026-10-23); new methods await review.
The Spire collection night ended ([log](spire/fullrun/log.md#2026-10-23-collection-night-qwen36-reasoning-off-harness-v102)).
The WH3 starting-set screen admitted no new tactic card ([log](twwarhammer3/log.md#2026-10-22-the-starting-set-screen));
that reading remains historical and does not select the new Land Battle benchmark.
Judgement-call [marking](judgement.md) continues in reviewable batches. Four unmerged draft
branches remain ([list](#branches)), above the proposed three-branch cap; no new runtime branch in the next plan.
[Traces must support RL](posttraining.md#beyond-supervised-fine-tuning).

## Total War: WARHAMMER III

Current priority: define one small mixed-army Land Battle to compare model knowledge and
execution at API latency. Engine victory includes timer endings; how health, morale and
knowledge evidence contribute to the score is open in the interview.
[Definition](twwarhammer3/benchmark.md), [plan](twwarhammer3/benchmark-implementation.md#phases),
[README](twwarhammer3/README.md), [log](twwarhammer3/log.md), [results](twwarhammer3/results.csv).

- Runtime: `llm`/`llm_rules` v22, `commander` v8, `team_llm_rules` v22+t2, skills v1.2, harness b50,
  evaluator v2, track `obs-v4+terrain/act-v2/live-1x`. The new benchmark is not implemented or verified.
- [Chariot](twwarhammer3/tactic-cards.md) and Empire screens retain their historical rules/results;
  chariot confirmation, P5 and recovery studies are not the new benchmark's prerequisites.
- Scripted-team agreed checks passed at recorded revisions (live 4/4 at `3adbaa4`); the model
  team is on `main`, but its members have not played live and it has no agreed check.
- Spend: OpenAI $51.47 of $52; WH3 OpenRouter $21.33. A new paid cohort needs a bounded plan.
- Battle checkpoints: Land check at `6fdb271` and `dcb8b5a`, declared siege cases at `2e2acbe`; build
  25961564 ([limits](twwarhammer3/checkpoints.md#limits)).

Benchmark work waits: answer the [single-battle interview](twwarhammer3/benchmark-implementation.md#owner-interview-one-land-battle),
then revise the proposed profile, score, knowledge evidence and checks from those answers.
Readback work, implementation and a pilot follow the agreed definition; settings, counts,
checks and spending remain proposals. No new experiment is authorized by this interview.

## Slay the Spire

Paused behind WH3. No full run has won; the furthest reached Act 4, floor 54. The 2026-10-23
data night (Qwen3.6, harness v10.2) died in Act 1 in all 41 finished runs (median floor 8).
Next, highest Spire priority (owner, 2026-10-23): the [state-restore investigation](spire/state-restore.md),
restoring the game to a recorded state with the same RNG to try other choices. Its first live
step, a $0 replay check, needs a game window and your profile decision first.
Then: a meaningful comparison of the current controller, or a freeze.

[README](spire/fullrun/README.md), [log](spire/fullrun/log.md), [results.csv](spire/fullrun/results.csv). v10 on `main`; floor 54 was v8.
Version differences sit within run-to-run variation (about 11 floors on one seed; same-harness replays differed by 13–26), measured only on three tuning seeds. `HELDOUT01`–`HELDOUT10` unplayed.
Spend: OpenAI $2.52 of $25, OpenRouter $3.46. The comparison and `v11-keys` wait; [open questions](spire/fullrun/README.md#open-owner-decisions). Paused: [first combat](spire/first-combat/README.md); planned: [open-weight](spire/open-weight/README.md).

## Post-training

Secondary priority. Capture, export and dataset smoke checks passed; there is no learning
claim. A training host, a way to play fine-tuned models, and useful targets are still missing.
Spire capture for RL and other methods is in as harness v10.2 (2026-10-23): Qwen3.6 token
logprobs and per-floor save snapshots ([what each method can use](posttraining.md#beyond-supervised-fine-tuning));
restoring a snapshot is untested.

[Plan and data-use choices](posttraining.md). [Checkpoint RL handoff](twwarhammer3/checkpoint-rl.md) and
[implementation plan](twwarhammer3/checkpoint-rl-plan.md): implemented on branch `wh3-checkpoint-rl`
and run on the night of 2026-10-26 ([log](twwarhammer3/log.md#2026-10-26-checkpoint-rl-implemented-and-run-stage-3-fails-the-policy-collapses)):
exact-tick injection into restored battles works and is deterministic; the trained choice won
live on one rung; the synthetic check (also after its one allowed re-run) and the ladder's
second rung failed: the policy collapses (onto one action, or onto one displayed slot). A
state-loading check found no bug. The simplest fix (a log objective) stops the collapse but
reaches only 0.59 held out (bar 0.9; lr 1e-3: 0.10). A diagnostic showed the model fits contexts
but reads the wrong unit, and that the synthetic gate itself is confounded. On a de-confounded
v2 it learns the training split (0.96) but generalises to 0.76 held out. Stopped; decision 11.

## Known issues

- `runs/` has no backup (23 GB, 7.1 GB without `checkpoints/`); the owner said not now (2026-10-21).
- Check OpenRouter credits before paid jobs: on 2026-10-21 the account showed $24.26 used of
  $60, the ledgers $2.68 less. OpenAI caps and the shared OpenRouter allowance are kept by hand.
- Pinned OpenRouter backend outages count against the model; Step 5 preview is unpinned.
- No test yet shows whether a game patch changes results (owner: later). A build warning
  shows in `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- WH3 readers still differ on timer wins and failures; the new engine-outcome definition
  needs a versioned scorer. Register/`stats` also have blank benchmark versions and commit grouping.
- The mod sets 1x once, then reports constant `speed` 1 and `awaiting_orders` false: per-observation paused/slowed tests cannot fail; only the team check's clock ratio detects slowdown.
- WSL clocks run about 6-8% slow against Windows and `time.time()` is stepped 2-3 s every ~35 s (measured 2026-10-28, [clocks](twwarhammer3/integration.md#clocks-measured-2026-10-28)): WSL-timed think times, delays and short-window clock ratios are off; the battle itself runs at 1x.
- Spire runs often leave a profile preference file empty, likely when the game is killed at
  run end (25 of 43 data runs on 2026-10-23); the game recovers it from `.backUp` at the next
  start. `STSDataVagabond` is 0 bytes now and `STSUnlockProgress` has no `.backUp`
  ([details](spire/state-restore.md#risks-found-on-the-way)). Ironclad unlock level 4 is 43
  points away; decide the profile question before more Spire game time (owner's note: maybe
  unlock things normally first, then enable restore).
- The report browser check is separate from pytest; Spire's full-run action and time limits
  still lack loop tests. Spire's Workshop mod pins still block a run when a mod updates.

## Owner decisions waiting

1. **One Land Battle definition.** Answer the [interview](twwarhammer3/benchmark-implementation.md#owner-interview-one-land-battle) on model comparison, knowledge, latency, health/morale scoring and required game data. Engine timer outcomes and small mixed armies are agreed; the earlier profile, summary, role coverage and new checks remain proposals. Historical c1 is unchanged. Clock rule (owner, 2026-10-28): measured durations in battle time ([clocks](twwarhammer3/integration.md#clocks-measured-2026-10-28)).
2. **Next experiments and spending.** Choose a game window for the new profile's measurement checks/pilot, after its definitions are settled, then the controller comparison and budget. The [plan](twwarhammer3/benchmark-implementation.md#phases) starts with free scripts. Older P5, Kimi and team estimates are deferred; OpenAI's $52 cap still refuses Sol. No new paid plan is authorized by this definition update.
3. **Remaining autonomy rules.** The [standing menu and small interviews](autonomy.md#standing-work) were agreed on 2026-10-28; the next overnight plan is saved, not started. Other provisions of the older [away guidelines](autonomy.md) still await review; this was not blanket acceptance.
4. **Model-team choices to review later.** On 2026-10-28 you let me settle five open items for now; each keeps today's behaviour, stays marked and is listed in [multi-agent-implementation.md](twwarhammer3/multi-agent-implementation.md#choices-settled-for-now-2026-10-28). Before a paid team battle, agree a check for `team_llm_rules` ([next](twwarhammer3/multi-agent-implementation.md#next)); model members have not played live.
5. **Campaign permissions.** Separately allow or refuse harness saves and irreversible Steam achievements. These choices are required before any campaign launch. Deferring keeps campaign work to [offline drafts](autonomy.md#wh3-campaign-infrastructure).
6. **Controller direction.** Adopt or drop the attack-route prompt change; keep or defer the commander approach. The attack-route draft needs its own comparison under the new Land Battle definition and renumbering before adoption. `commander` is unplayed since v4; [controller plans](twwarhammer3/controllers.md) remain proposals.
7. **Backend and sampling policy.** Review the delegated backend pins and decide sampling capture and serving-fault treatment. b36's [backend pins](twwarhammer3/latency.md#owner-decisions) await review. Recommended: request log-probabilities, seed and explicit sampling where the pinned backend advertises them ([gaps](posttraining.md#beyond-supervised-fine-tuning); listings rechecked October 21, not a capture test). Choose how to report or rerun [garbled replies](twwarhammer3/empire.md#for-the-owner-to-decide); current backend failures count against the model.
8. **Training preparation.** Choose a host, serving route and teacher; decide when and how to build the Empire dataset. Secondary priority. [Data-use choices](posttraining.md#provider-terms): OpenAI outputs (25,503 rows excluded: Spire 11,099; WH3 14,404), GLM-5.3 or rejection-sampled Qwen3.6; Step 5 weights are public. An [Empire content screen and dataset timing](twwarhammer3/empire.md#for-the-owner-to-decide) are still needed. Smoke checks establish no learning gain.
9. **Spire's next step.** After WH3, run one meaningful comparison or freeze this track; the state-restore investigation comes first (owner, 2026-10-23). Also noted for later: the capture check (owner, 2026-10-23: "Not sure what this is"). Both, with the proposed comparison and the data-night choice: [Spire open decisions](spire/fullrun/README.md#open-owner-decisions).
10. **Thesis direction.** No topic is chosen. The 2026-10-28 notes ([index](thesis/notes/README.md)) favour the decision benchmark (2) with the support question (1) as its first task; direction 10 (human and AI together) stays a note (owner, 2026-10-28). Pick what to explore next; [summary](thesis/directions.md#what-the-2026-10-28-checks-changed).

11. **Checkpoint RL.** Stopped where the plan needs you (2026-10-26, "Stop here"): (a) how to continue after the policy collapse and the 0.76 held-out result, (b) review the choices made without you, (c) the stage 1 and 4 checks you agreed on 2026-10-26, (d) merging the branch. Details: [checkpoint-rl.md](twwarhammer3/checkpoint-rl.md#open-owner-choices-decision-11).
## Runtime and ownership

- Slay the Spire ([runtime facts](spire/integration.md#runtime-and-source-pins)): the installed game and personal profile slot 0 are authorized, including stats, unlock progress, history and achievements (Ironclad unlock 3 of 5; runs record profile evidence).
- WH3 ([engine facts](twwarhammer3/integration.md)): a launch's mod list and startup-video
  skip persist for ordinary Steam launches ([how to reverse](twwarhammer3/README.md#commands)).
  Steam auto-update stays on.
- Also authorized: game windows, local GPU work, commits and pushes to public `main`, and
  paid API use within each ledger's cap. One game controller at a time across both games
  (each game's lock and process check cover only that game); one GPU job at a time.

## Branches

- `wh3-checkpoint-rl` (worktrees `../slay_the_spire_ai-checkpoint-rl`, `-run` for game phases):
  checkpoint RL (mod export `twwarhammer3_inject`, step runs, candidates, audit, `exact_table@1`,
  `twwarhammer3 rl`); offline tests pass. Changes the mod pack; unmerged (decision 11).

- `v11-keys` (`cd97667`): Spire v11 keys memory, on v10 (`54a5967`).
- `wh3-rules-v21-attack-path` (`5baf28b`): WH3 `llm_rules` attack-route draft, labelled
  v21 before main's v21 (`18dabdd`); renumber before any merge.
- `wh3-human-opponent` (`de37005`, worktree `../slay_the_spire_ai-wh3-human-opponent`): the
  controllers command the AI's army so the owner can play against them. Parked by the owner
  (2026-10-22) to implement later, starting at step 1 of the [plan](twwarhammer3/multi-agent-plan.md#d-single-client-steps).
- Archived drafts are tags (`git tag --list 'archive/*'`).
