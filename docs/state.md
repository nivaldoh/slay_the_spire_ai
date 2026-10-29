# Project state

Updated 2026-10-28: what runs, where each game stands, what comes next. Status only:
History: [WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md), [first combat](spire/first-combat/README.md); directions: [owner-direction.md](owner-direction.md).
Under the [hard rule](../AGENTS.md#verification-hard-rule), only listed agreed checks are verified at their recorded revisions; gameplay findings below remain unverified.

## Active work

WH3 first; Spire waits behind it; post-training is secondary.
Standing work (owner, 2026-10-28): thesis frontier; decisions/`JUDGEMENT` and small interviews;
correctness/tests; code/repository upkeep; agent workflow efficiency. [Menu](autonomy.md#standing-work).
**Running (Claude Code, 2026-10-29 02:17-12:10 -03, owner away):** the light factory plan,
now [workflow.md](workflow.md): stages 1-3 built ([log](twwarhammer3/log.md#2026-10-29-light-factory-stages-1-3));
no game, no spend. Before each commit: `uv run --locked python scripts/check.py`.
**Nothing runs**: all game controllers are stopped. The 2026-10-28 long autonomous runs
and checkpoint-RL merge are finished ([log](twwarhammer3/log.md)); the owner's latest
[direction](owner-direction.md) is recorded. Local LLM post-training stays paused.
Thesis: likely multi-agent systems, possibly multi-agent RL linked to the WH3 environment;
the research question is open. The [proposal](thesis/proposal.md) is one candidate
([directions](thesis/directions.md), [papers](thesis/papers.md)). Testing reviews await you:
[eval review](twwarhammer3/log.md#wh3-evaluations-and-tests-2026-10-23),
[live-check comparison](twwarhammer3/log.md#wh3-live-check-comparison-2026-10-23).
Three unmerged draft branches remain ([list](#branches)); checkpoint RL was merged on 2026-10-28.
MARL references: [three papers plus ProgramLab](thesis/papers.md#marl-implementation-references-2026-10-28), inspected 2026-10-28; ProgramLab's training code is pending. No external tests or learning results reproduced.
[Traces must support RL](posttraining.md#beyond-supervised-fine-tuning).

## Total War: WARHAMMER III

Benchmark definition remains open. The Land Battle draft uses small mixed armies; health
and morale are the owner's tentative primary measures (2026-10-28). Planned scope also
includes Siege, Survival, Ambush and Conquest, with other types to confirm. Engine victory
includes timer endings; scoring, mode order and checks remain undecided.
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
  25961564 ([limits](twwarhammer3/checkpoints.md#limits)); public player tool v0.1.0.

Open discussions: the [RL environment and its possible thesis connection](thesis/directions.md#6-wh3-as-an-rl-environment-for-high-level-decisions)
and remaining [benchmark definitions](twwarhammer3/benchmark-implementation.md#owner-interview-one-land-battle)
when the owner is ready. Implementation, checks and new runs await those definitions.

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

[Plan and data-use choices](posttraining.md). The local Qwen3-0.6B checkpoint-RL experiment
is merged, but stays paused (owner, 2026-10-28; decision 11). The revised learner reached
0.76 on held-out synthetic tasks against a 0.90 gate; no general learning gain established
([log](twwarhammer3/log.md#2026-10-26-checkpoint-rl-implemented-and-run-stage-3-fails-the-policy-collapses)).
The broader RL environment remains a separate discussion, possibly connected to the thesis.

## Known issues

- `runs/` has no backup (31 GB on 2026-10-28, 16 GB of it in `checkpoints/` folders); the owner said not now (2026-10-21).
- Check OpenRouter credits before paid jobs: on 2026-10-21 the account showed $24.26 used of
  $60, the ledgers $2.68 less. OpenAI caps and the shared OpenRouter allowance are kept by hand.
- Pinned OpenRouter backend outages count against the model; Step 5 preview is unpinned.
- No test yet shows whether a game patch changes results (owner: later). A build warning
  shows in `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- WH3 readers still differ on timer wins and failures; the new engine-outcome definition
  needs a versioned scorer. Register/`stats` also have blank benchmark versions and commit
  grouping.
- The mod sets 1x once, then reports constant `speed` 1 and `awaiting_orders` false: per-observation paused/slowed tests cannot fail; only the team check's clock ratio detects slowdown.
- WSL clocks run about 6-8% slow against Windows and `time.time()` is stepped 2-3 s every ~35 s (measured 2026-10-28, [clocks](twwarhammer3/integration.md#clocks-measured-2026-10-28)): WSL-timed think times, delays and short-window clock ratios are off; the battle itself runs at 1x.
- Spire runs often leave a profile preference file empty, likely when the game is killed at
  run end (25 of 43 data runs on 2026-10-23); the game recovers it from `.backUp` at the next
  start. `STSDataVagabond` is 0 bytes now and `STSUnlockProgress` has no `.backUp`
  ([details](spire/state-restore.md#risks-found-on-the-way)). Ironclad unlock level 4 is 43
  points away; decide the profile question before more Spire game time (owner's note: maybe
  unlock things normally first, then enable restore).
- The report browser check is separate from pytest. Spire's Workshop mod pins still block a
  run when a mod updates.

## Owner decisions waiting

1. **Benchmark definition, later.** Health and morale are the tentative primary measures; Siege, Survival, Ambush and Conquest join Land in the intended scope (owner, 2026-10-28). Scoring formulas, profiles, mode order, knowledge/latency evidence and checks remain open in the [Land interview](twwarhammer3/benchmark-implementation.md#owner-interview-one-land-battle). Engine timer outcomes and small mixed armies remain agreed; historical c1 is unchanged. Durations use battle time ([clocks](twwarhammer3/integration.md#clocks-measured-2026-10-28)).
2. **Next experiments and spending.** Choose a game window for the new profile's measurement checks/pilot, after its definitions are settled, then the controller comparison and budget. The [plan](twwarhammer3/benchmark-implementation.md#phases) starts with free scripts. Older P5, Kimi and team estimates are deferred; OpenAI's $52 cap still refuses Sol. No new paid plan is authorized by this definition update.
3. **Remaining autonomy rules.** The [standing menu and small interviews](autonomy.md#standing-work) were agreed on 2026-10-28; the saved overnight plan ran that night (02:39-04:35; [report](twwarhammer3/log.md#2026-10-28-overnight-restore-pauses-were-wsl-clock-steps-land-check-passes-at-dcb8b5a)). Other provisions of the older [away guidelines](autonomy.md) still await review; this was not blanket acceptance.
4. **Model-team choices to review later.** On 2026-10-28 you let me settle five open items for now; each keeps today's behaviour, stays marked and is listed in [multi-agent-implementation.md](twwarhammer3/multi-agent-implementation.md#choices-settled-for-now-2026-10-28). Before a paid team battle, agree a check for `team_llm_rules` ([next](twwarhammer3/multi-agent-implementation.md#next)); model members have not played live.
5. **Campaign permissions.** Separately allow or refuse harness saves and irreversible Steam achievements. These choices are required before any campaign launch. Deferring keeps campaign work to [offline drafts](autonomy.md#wh3-campaign-infrastructure).
6. **Controller direction.** Adopt or drop the attack-route prompt change; keep or defer the commander approach. The attack-route draft needs its own comparison under the new Land Battle definition and renumbering before adoption. `commander` is unplayed since v4; [controller plans](twwarhammer3/controllers.md) remain proposals.
7. **Backend and sampling policy.** Review the delegated backend pins and decide sampling capture and serving-fault treatment. b36's [backend pins](twwarhammer3/latency.md#owner-decisions) await review. Recommended: request log-probabilities, seed and explicit sampling where the pinned backend advertises them ([gaps](posttraining.md#beyond-supervised-fine-tuning); listings rechecked October 21, not a capture test). Choose how to report or rerun [garbled replies](twwarhammer3/empire.md#for-the-owner-to-decide); current backend failures count against the model.
8. **Training preparation.** Choose a host, serving route and teacher; decide when and how to build the Empire dataset. Secondary priority. [Data-use choices](posttraining.md#provider-terms): OpenAI outputs (25,503 rows excluded: Spire 11,099; WH3 14,404), GLM-5.3 or rejection-sampled Qwen3.6; Step 5 weights are public. An [Empire content screen and dataset timing](twwarhammer3/empire.md#for-the-owner-to-decide) are still needed. Smoke checks establish no learning gain.
9. **Spire's next step.** After WH3, run one meaningful comparison or freeze this track; the state-restore investigation comes first (owner, 2026-10-23). Also noted for later: the capture check (owner, 2026-10-23: "Not sure what this is"). Both, with the proposed comparison and the data-night choice: [Spire open decisions](spire/fullrun/README.md#open-owner-decisions).
10. **Thesis and RL environment.** Likely multi-agent systems, possibly multi-agent RL; no research question selected (owner, 2026-10-28). Tentative environment: each agent sees its available battle state, perhaps teammate information, controls its army share and learns from sparse win/loss near restored endings. Reset may use a battle start or checkpoint; details and correctness checks are for later. [Direction 6](thesis/directions.md#6-wh3-as-an-rl-environment-for-high-level-decisions); [research shortlist](thesis/directions.md#what-the-2026-10-28-checks-changed). Human-AI work stays a note; licensing is deferred.

11. **Local LLM checkpoint RL — deferred.** Leave this post-training experiment paused (owner, 2026-10-28). No recovery choice is needed now; the existing results and choices remain for a future review. Merged on 2026-10-28. [Details](twwarhammer3/checkpoint-rl.md#open-owner-choices-decision-11).
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
- `wh3-human-opponent` (`de37005`, worktree `../slay_the_spire_ai-wh3-human-opponent`): the
  controllers command the AI's army so the owner can play against them. Parked by the owner
  (2026-10-22) to implement later, starting at step 1 of the [plan](twwarhammer3/multi-agent-plan.md#d-single-client-steps).
- Archived drafts are tags (`git tag --list 'archive/*'`).
