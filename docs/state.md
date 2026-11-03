# Project state

Updated 2026-11-03: what runs, where each game stands, what comes next. Status only:
History: [WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md), [first combat](spire/first-combat/README.md); directions: [owner-direction.md](owner-direction.md).
Under the [hard rule](../AGENTS.md#verification-hard-rule), only listed agreed checks are verified at their recorded revisions; gameplay findings below remain unverified.

## Active work

GCP: no VM (retry stopped after Windows setup: no Steam login or game; handoff `runs/twwarhammer3/gcp/session-20261103c/handoff.md`).
Leftover disk `wh3-compat-20261103c` (no game) auto-deletes 2026-11-04 04:20 UTC; `gcp-retry` (`f038dc5`) unmerged.
Draft [VM team plan](twwarhammer3/vm-team-plan.md) (2026-11-03): owner decisions first; nothing agreed or run.

Initial one-army team test/comparison complete at `c1ad84d`; games closed. [Results/next steps](twwarhammer3/multi-agent-implementation.md#next).

Visual reports: `runs/twwarhammer3/reports/benchmark.html` ([open/build](twwarhammer3/reports.md#main-report-and-retained-example)) and `initial-benchmark.html` ([open/build](twwarhammer3/reports.md#initial-benchmark-visuals)); checks in `runs/benchmark-visual-20261102/`.

Factory: one worktree per writing session ([rule](workflow.md#several-sessions-at-once)); handoff `runs/factory-multiagent-20261102/handoff.md`.

Completed work and review handoffs: [review queue](review-queue.md#completed-work-and-handoffs); [test review](testing.md#mailbox-transition-review-2026-11-03).
Follow-up: shared Codex/Claude WH3 knowledge skill ([direction](owner-direction.md)).
Later planning: [session context](workflow.md#session-context-improvements) and the remaining [concurrent work](workflow.md#concurrent-work-improvements) proposals.

WH3 first; Spire waits behind it; post-training is secondary.
Boris-only [battle proposals](twwarhammer3/boris-scenarios.md): unverified candidates for owner selection; no games scheduled.
Standing work (owner, 2026-10-28): thesis frontier; decisions/`JUDGEMENT` and small interviews; correctness/tests; code/repository upkeep; agent workflow efficiency. [Menu](autonomy.md#standing-work).
Thesis (decision 10): the research question is open; the [proposal](thesis/proposal.md) is one candidate ([directions](thesis/directions.md), [papers](thesis/papers.md)). Added [cross-domain design reference](thesis/papers.md#cross-domain-test-design-from-video-game-to-real-robot); WH3 transfer remains open.

## Total War: WARHAMMER III
Benchmark [initial implementation](twwarhammer3/benchmark-initial.md) completed, version5 (decision 1): [definition](twwarhammer3/benchmark.md), [phases](twwarhammer3/benchmark-implementation.md#phases),
[README](twwarhammer3/README.md), [log](twwarhammer3/log.md), [results](twwarhammer3/results.csv).
The [visual report](twwarhammer3/reports.md#initial-benchmark-visuals) includes current outcome/condition
scores, every planned attempt and the recorded replays; controller ranking remains unverified.

- Runtime: `llm`/`llm_rules` v22, `commander` v8, `team_llm_rules` v22+t2, skills v1.2, harness b52; game [9.0.5/build 26403568](twwarhammer3/integration.md#pins).
  evaluator v2 plus mirror-v1, track `obs-v4+terrain/act-v2/live-1x`. Recording/arithmetic passed at `b1136e8`; strength and winnability remain unverified.
- [Chariot](twwarhammer3/tactic-cards.md) and Empire screens retain their historical rules/results;
  chariot confirmation, P5 and recovery studies are not the new benchmark's prerequisites.
- Scripted-team agreed checks passed at recorded revisions (live 4/4 at `3adbaa4`); direct model-team mechanics passed one live case at `c1ad84d`; its initial comparison is complete.
- Spend: OpenAI $51.47 of $52; WH3 OpenRouter $21.33; Anthropic game ledgers $0.8216764 (includes one timeout estimate); the key also spent $0.02 on provider smoke calls, under its shared $200. GaP has a $5 cap.
- Battle checkpoints: Land check at `6fdb271` and `dcb8b5a`, declared siege cases at `2e2acbe`;
  build 25961564 only, blocked on 9.0.5 pending a native-hook port ([limits](twwarhammer3/checkpoints.md#limits)); public player tool v0.1.0.
- Native team multiplayer: offline parts built (platform detection, `observe`/`control` battle
  modes, link, worker, `compare-peers`; [status](twwarhammer3/native-multiplayer.md#implementation-status)),
  all unverified; zero live MP battles. GCP launched WH3, but the agreed host check is
  incomplete and VM/disk deleted. The second account has DLC-granted access with a limited
  roster; use its confirmed recruitable units. [GCP result](twwarhammer3/gcp-client-setup.md#pilot-result-2026-11-03).

## Slay the Spire

Paused behind WH3. No full run has won; the furthest reached Act 4, floor 54 (v8; `main` has v10).
Next, highest Spire priority (owner, 2026-10-23): the [state-restore investigation](spire/state-restore.md), restoring
the game to a recorded state with the same RNG to try other choices. Step 1 ran offline on 2026-10-29
([results](spire/state-restore.md#step-1-results-2026-10-29-offline)). Its first live step, a $0 replay check
(driver on branch `spire-restore-replay`, never run), needs a game window and your profile decision first.
[README](spire/fullrun/README.md), [log](spire/fullrun/log.md), [results.csv](spire/fullrun/results.csv).
Version differences sit within run-to-run variation (about 11 floors on one seed; same-harness replays differed by 13–26), measured only on three tuning seeds. `HELDOUT01`–`HELDOUT10` unplayed.
Spend: OpenAI $2.52 of $25, OpenRouter $3.46. The controller comparison (decision 9) and `v11-keys` wait; [open questions](spire/fullrun/README.md#open-owner-decisions). Paused: [first combat](spire/first-combat/README.md); planned: [open-weight](spire/open-weight/README.md).

## Post-training

Secondary priority. Capture, export and dataset smoke checks passed; there is no learning claim.
A training host, a way to play fine-tuned models, and useful targets are still missing
([plan and data-use choices](posttraining.md)). The local Qwen3-0.6B checkpoint-RL experiment
stays paused (owner, 2026-10-28; decision 11); its failed synthetic gate establishes no
general learning gain ([log](twwarhammer3/log.md#2026-10-26-checkpoint-rl-implemented-and-run-stage-3-fails-the-policy-collapses)).

## Known issues

- `runs/` has no backup (30 GB on 2026-10-31, inventory in `runs/overnight-20261031/b7/`); the owner said not now (2026-10-21).
- Check OpenRouter credits before paid jobs; OpenAI caps and the shared allowances are kept by hand. Keep both Anthropic ledgers under the key's $200: what the key returns at its limit is untested. Pinned OpenRouter backend outages count against the model; Step 5 preview is unpinned.
- No test yet shows whether a game patch changes results (owner: later). A build warning shows in
  `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- WH3 readers differ on 3 timer wins, 8 controller failures and 5 wall caps of 642 rows; `cards.benchmark_outcome` v1 maps the outcome table, no reader uses it yet. Register/`stats` also have blank benchmark versions and commit grouping.
- Since `1cc4582` each observation's `speed` is the engine's `current_battle_speed()` (one probe: 440/440 read 1); a slowed battle was never tried. `awaiting_orders` stays false (the mod never waits). Pauses run no script: the Windows-clock line (b51) covers them.
- WSL clocks run about 6-8% slow against Windows and `time.time()` is stepped 2-3 s every ~35 s (measured 2026-10-28, [clocks](twwarhammer3/integration.md#clocks-measured-2026-10-28)): WSL-timed think times, delays and short-window clock ratios are off; the battle itself runs at 1x.
- Spire runs often leave a profile preference file empty (25 of 43 data runs on 2026-10-23; [details](spire/state-restore.md#risks-found-on-the-way)). Decide the profile question before more Spire game time (owner's note: maybe unlock things normally first, then enable restore).
- Under parallel load `test_wh3_capture.py`'s passive-capture test (2 s wait; PR #1 changed it) and once `test_wh3_checkpoint_rl.py`'s source-run test flaked: rerun before calling a regression. Six `test_hooks.py` tests fail whenever a game job runs (the hook they start sees it), so `check.py` cannot pass during game time.
- Spire's Workshop mod pins still block a run when a mod updates.

## Owner decisions waiting

Details and source links live in the [review queue](review-queue.md#decisions).
Numbers are unchanged; open the relevant item before acting.

1. **Initial benchmark:** implemented and checked; three scripts and five Haiku attempts lost. Further comparisons and balance remain open.
2. **Experiments/spending:** game window, comparison and budget; older screens deferred.
3. **Autonomy:** standing menu agreed; remaining away rules await review.
4. **Model team:** initial test/comparison complete; broader design/budget and earlier marked choices remain for later review ([next](twwarhammer3/multi-agent-implementation.md#next)).
5. **Campaign:** saves and achievements each need permission before any campaign launch.
6. **Controllers:** attack-route comparison/renumbering and commander direction wait.
7. **Backend/sampling:** pins, capture and treatment of serving failures await review.
8. **Training:** host, serving route, teacher and dataset choices; secondary priority.
9. **Spire:** restore/profile decision first, after WH3; other comparisons wait.
10. **Thesis/RL:** research question and environment details remain open.
11. **Local checkpoint RL:** stays paused; no recovery decision needed now.
12. **Factory:** test edits and approval for edits to `check.py` remain open.

## Runtime and ownership

- Slay the Spire ([runtime facts](spire/integration.md#runtime-and-source-pins)): the installed game and personal profile slot 0 are authorized, including stats, unlock progress, history and achievements (Ironclad unlock 3 of 5; runs record profile evidence).
- WH3 ([engine facts](twwarhammer3/integration.md)): a launch's mod list and startup-video skip
  persist for ordinary Steam launches ([how to reverse](twwarhammer3/README.md#commands)). Steam auto-update stays on.
- Also authorized: game windows, local GPU work, commits and pushes to public `main`, and paid API
  use within each ledger's cap. One game controller at a time across both games (each game's lock and process check cover only
  that game); one GPU job at a time.

## Branches

- `v11-keys` (`cd97667`): Spire v11 keys memory, on v10 (`54a5967`).
- `wh3-rules-v21-attack-path` (`5baf28b`): WH3 `llm_rules` attack-route draft, labelled
  v21 before main's v21 (`18dabdd`); renumber before any merge.
- `wh3-human-opponent` (`de37005`, worktree `../slay_the_spire_ai-wh3-human-opponent`): the
  controllers command the AI's army so the owner can play against them. Parked by the owner
  (2026-10-22) to implement later, starting at step 1 of the [plan](twwarhammer3/multi-agent-plan.md#d-single-client-steps).
- `spire-restore-replay` (`765ab2f`, worktree `../slay_the_spire_ai-spire-replay`): the Spire
  state-restore step 2 replay driver (`spire replay`), tested with a fake game only, never run.
- `team-check-battle-time` (`58a52ef`), `land-check-stats-apart` (`f3bcd97`): agreed-check drafts;
  `gate-xdist` (`668940e`): check.py on xdist workers.
- Archived drafts are tags (`git tag --list 'archive/*'`).
