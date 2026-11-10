# Project state

Updated 2026-11-09. Status only. History: [WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md), [first combat](spire/first-combat/README.md); directions: [owner-direction.md](owner-direction.md). Under the [hard rule](../AGENTS.md#verification-hard-rule), only listed agreed checks are verified at their recorded revisions; gameplay findings below remain unverified.

## Active work
Agent context loading, 2026-11-09 (Codex): [shared startup routes and personal-memory cleanup](context-loading.md); handoff `runs/context-loading-20261109/handoff.md`. No game work. Session speed and adherence remain unverified.

WH3 [communication structure](twwarhammer3/communication-structure.md), 2026-11-10 (Codex): owner authorized the next construction/testing steps, live games and up to $20 new spending. Branch `comm-next-20261110`, worktree `runs/comm-next-20261110/worktree`; brief `runs/comm-next-20261110/brief.md`. First batch: three scripted mechanics probes, each bounded to 750 seconds, then evidence review before further launches. The previous construction gate failed; no scored comparison is established. [Previous results](twwarhammer3/communication-structure.md#results-so-far-night-of-2026-11-08), handoff `runs/comm-build-20261108/handoff.md`. Checks remain proposed; decision 14 retains the unresolved design choices.

Spire local-model training, 2026-11-07, owner's repeated goal; nothing runs and the game is closed. Branch `spire-local-rl`, handoff `runs/spire-rl-20261107/handoff.md`, decisions first. A second pick (learned fights with a human-taught run adapter) beat the 2026-11-06 best adapter (+2.80, interval +0.92 to +4.67) and the warm start on 60 fresh test seeds, one revision ([log](spire/fullrun/log.md#2026-11-07-evening-learned-fights-with-a-human-taught-run-adapter-beat-yesterdays-best-on-fresh-test-seeds)). **Owner: `STSUnlockProgress` is still the wiped copy; `runs/local-rl-20261106/handoff.md` has the restore commands.**

WH3 historical siege evaluations, 2026-11-08/09 (Claude, owner's goal): built offline at harness b54, nothing launched, all unverified ([overview](twwarhammer3/historical-evals.md)). Haengju (siege defence, divisions in turn), Belgrade's camp attack and Alesia's two fronts (Land), and Izmail (siege attack) have declarations, witnesses, controls and pages; Malta was designed and not built. The owner approved models using the siege orders (2026-11-09): `llm`/`llm_rules` v23 offers them in Izmail; the commander and team members read the fort as facts without the orders, and `local_team` members do not see it. No battle has run on v23. Next: the rest of decision 15, then a game window the owner names, starting with the lobby-only roster readback.

WH3 [research focus](twwarhammer3/research-focus.md) saved for review (2026-11-06); contribution priority and scope remain open, no experiment scheduled.

[Cannae A/B/C](twwarhammer3/cannae-eval.md#window-2-results-2026-11-05) and the separate [air-relief candidate](twwarhammer3/tactics-reference.md#air-relief-audit-2026-11-05) remain unverified development candidates; all games are closed and none is scheduled. Next: decision 13.

[Infantry support timing](twwarhammer3/support-timing.md#stopped-comparison-and-next-steps) stopped at the owner's request on 2026-11-05; no further timing work or second scenario is scheduled. Next choose the coordination question worth studying before another scenario or live run.

Overnight suite run ended 2026-11-04; owner on its page: ok for now, reviews later; no more battles for now. [Scenario guidelines](twwarhammer3/scenario-guidelines.md): plan only, no evaluations scheduled.

GCP: no VM and no disk. Game disk deleted 2026-11-05 ([owner](owner-direction.md)), no snapshot, so a new VM session needs a fresh install and Steam login. Cloud spend of the $10: about $2.06 compute plus storage (unreconciled).
[Native multiplayer](twwarhammer3/native-multiplayer.md#implementation-status): two live PC+VM battles at `01647bd` on 11-03, unverified (one battle each, no agreed check). [Three-step work](twwarhammer3/mp-next-steps.md): offline parts built, PC test bed run ($0), paid VM session stopped. [Foundation](twwarhammer3/multiplayer-control-foundation.md#implementation-status): one client so far; two clients and full acceptance remain. [VM team plan](twwarhammer3/vm-team-plan.md) decisions 1-4 still open.

[Visual reports](twwarhammer3/reports.md): the [cooperation proposal](twwarhammer3/reports.md#cooperation-evidence-proposal) adopts no new score; reader feedback on the [suite report](twwarhammer3/reports.md#coordination-suite) remains open.

Factory, repo upkeep of 2026-11-06: the owner ran both of its cleanup scripts (nine stale worktrees and 841 `runs/` paths removed); handoff `runs/repo-improve-20261106/handoff.md`.
Repo upkeep and bug audit of 2026-11-08 (Claude; nothing runs): its fixes landed, the last 14 moving the report fingerprint ([log](twwarhammer3/log.md#2026-11-08-repository-upkeep-and-bug-audit)); handoff `runs/repo-improve-20261108/handoff.md`. The owner ran its cleanup scripts (159 `runs/` paths and 1,449 duplicate C: game logs, 4.2 GB).

Completed work and handoffs: [review queue](review-queue.md#completed-work-and-handoffs); [test repairs](twwarhammer3/log.md#2026-11-09-test-faults-timing-and-duplicate-setup). Later planning: [workflow](workflow.md#session-context-improvements).

WH3 first; Spire waits behind it; post-training is secondary.
Standing work (owner, 2026-10-28): thesis frontier; decisions/`JUDGEMENT` and small interviews; correctness/tests; code/repository upkeep; agent workflow efficiency. [Menu](autonomy.md#standing-work).
Thesis (decision 10): the research question is open; the [proposal](thesis/proposal.md) is one candidate ([directions](thesis/directions.md), [papers](thesis/papers.md)). Saved [references](references.md) have unverified WH3 applications and no experiment scheduled.

## Total War: WARHAMMER III
Benchmark [initial implementation](twwarhammer3/benchmark-initial.md) completed, version5 (decision 1): [definition](twwarhammer3/benchmark.md), [README](twwarhammer3/README.md), [results](twwarhammer3/results.csv). Controller ranking remains unverified.
[Coordination suite](twwarhammer3/benchmark.md#the-coordination-suite-suite-v1) (`suite-v1`): 12 scenarios, 6 played, first comparison 26 of 28 battles, one per pair; exploratory, no ranking.

- Runtime: `llm`/`llm_rules` v23, `commander` v8, `team_llm_rules` v23+t2, skills v1.2, harness b54; game [9.0.5/build 26403568](twwarhammer3/integration.md#pins).
  evaluator v2 plus mirror-v1, track `obs-v4+terrain/act-v2/live-1x`. Recording/arithmetic passed at `b1136e8`; strength and winnability remain unverified.
- [Chariot](twwarhammer3/tactic-cards.md) and Empire screens retain their historical rules/results; chariot confirmation, P5 and recovery studies are not the new benchmark's prerequisites.
- Scripted-team agreed checks passed at recorded revisions (live 4/4 at `3adbaa4`); direct model-team mechanics passed one live case at `c1ad84d`.
- Spend: OpenAI $51.47 of $52; WH3 OpenRouter $21.33; Anthropic game ledgers $13.89 on 2026-11-08 (WH3 $13.6806, Spire $0.2124; includes estimates for failed calls); the key also spent $0.0211 on provider smoke calls, under its shared $200. GaP has a $5 cap.
- Battle checkpoints: Land live-value rule and all four declared siege states passed at `210e356`, build 26403568 ([limits](twwarhammer3/checkpoints.md#limits)); public player tool v0.1.0 still targets build 25961564.

## Slay the Spire

Paused behind WH3. No full run has won; the furthest reached Act 4, floor 54 (v8; `main` has v10).
Local Qwen3-0.6B (2026-11-07, unverified): a learned fight adapter with a run-level adapter taught by public human run files reached 17.82 floors on `LRTEST061`-`120` against 15.02 for the 2026-11-06 fight adapter (+2.80, +0.92 to +4.67) and 11.45 for the warm start; an earlier pick, 15.88 on `LRTEST001`-`060`, beat only the warm start, whose arm there spanned two revisions. Rests on the branch's marked choices, including the human-run rows and the outcome tables ([log](spire/fullrun/log.md#2026-11-07-evening-learned-fights-with-a-human-taught-run-adapter-beat-yesterdays-best-on-fresh-test-seeds)).
The hand-written rule policy (`spire-teacher`, no model) reached 26.0 floors on 37 seeds, unpaired with the models; whether the model may train on its choices is the owner's terms decision. A speed mod on `spire-local-rl` plays a run in about 30 s. Every floor above was played with it, and floors at speed do not pair with 1x.
Next, highest Spire priority (owner, 2026-10-23): the [state-restore investigation](spire/state-restore.md). Its first live step, a $0 replay check (driver on branch `spire-restore-replay`, never run), needs a game window and your profile decision first.
Version differences sit within run-to-run variation (about 11 floors on one seed; same-harness replays differed by 13–26), measured only on three tuning seeds. `HELDOUT01`–`HELDOUT10` unplayed.
Spend: OpenAI $2.52 of $25, OpenRouter $3.46. The controller comparison (decision 9) and `v11-keys` wait; [open questions](spire/fullrun/README.md#open-owner-decisions). Paused: [first combat](spire/first-combat/README.md); planned: [open-weight](spire/open-weight/README.md).

## Post-training

Secondary priority. Capture, export and dataset smoke checks passed; the learning claims are the unverified [local Spire](posttraining.md#local-rl-on-complete-runs) warm start (2026-11-06) and the 2026-11-07 second pick, learned fights with a human-taught run adapter ([log](spire/fullrun/log.md#2026-11-07-evening-learned-fights-with-a-human-taught-run-adapter-beat-yesterdays-best-on-fresh-test-seeds)); the learned fights' own share was not separated. A training host, a way to play fine-tuned models, and useful targets are still missing ([plan](posttraining.md)). Local checkpoint RL stays paused (owner, 2026-10-28; decision 11); its failed synthetic gate establishes no general learning gain.

## Known issues

- Ctrl-C during a job's final copying leaves a won battle with no `result.json` and no register row, the ending staying in the trace: reproduced offline at `bd46129` with a real SIGINT (one probe, no live game, 0 of 650 saved episodes show it; `runs/repo-improve-20261106/preflight/unlanded-bugs/probe_play_signal.py`). First found in `runs/tests-cleanup/handoff.md`. No wrong outcome is counted today, though a benchmark row then has no outcome and the suite's cost leaves out that battle's spend. A draft fix was withdrawn after two reviews, because in a simulated case it lets a partial replay into benchmark measures: what a stopped job should count is an owner choice (handoff `runs/repo-improve-20261106/handoff.md`).
- `runs/` has no backup (30 GB on 2026-10-31, inventory in `runs/overnight-20261031/b7/`); the owner said not now (2026-10-21).
- Check OpenRouter credits before paid jobs; OpenAI caps and the shared allowances are kept by hand. Keep both Anthropic ledgers under the key's $200: its limit error is untested.
- No test yet shows whether a game patch changes results (owner: later). A build warning shows in `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- WH3 readers differ on 3 timer wins, 8 controller failures and 5 wall caps of the 642 rows on 2026-10-31; no reader uses `cards.benchmark_outcome` v1 yet. Register/`stats` also have blank benchmark versions and commit grouping.
- Since `1cc4582` each observation's `speed` is the engine's (one probe: 440/440 read 1); a slowed battle was never tried. A pause stops the `repeat_callback` tick, so no observation is written ([integration](twwarhammer3/integration.md#loading-phases-and-control)); the Windows-clock line (b51) covers pauses.
- WSL clocks ran about 6-8% slow against Windows (measured 2026-10-28, [clocks](twwarhammer3/integration.md#clocks-measured-2026-10-28)): WSL-timed think times, delays and short-window clock ratios are off; the battle itself runs at 1x.
- Spire runs often leave a profile preference file empty (25 of 43 data runs on 2026-10-23; [details](spire/state-restore.md#risks-found-on-the-way)). Decide the profile question before more Spire game time.
- Passive capture failed once under parallel load (11-01, before its wait became 30 s at `6079201`). The checkpoint source-run test now uses controlled time (`e10e85d`); no general flake-rate claim.
- Spire's Workshop mod pins still block a run when a mod updates.

## Owner decisions waiting

Details and source links live in the [review queue](review-queue.md#decisions).
Numbers are unchanged; open the relevant item before acting.

1. **Benchmark:** mirror checked; suite `JUDGEMENT` choices (battles, calibration, arms, tie-break, check) await review.
2. **Experiments/spending:** whether to confirm the first comparison, with which arms and budget; older screens deferred.
3. **Autonomy:** standing menu agreed; remaining away rules await review.
4. **Model team:** initial test/comparison complete; broader design/budget and earlier marked choices remain for later review ([next](twwarhammer3/multi-agent-implementation.md#next)).
5. **Campaign:** saves and achievements each need permission before any campaign launch.
6. **Controllers:** attack-route comparison/renumbering and commander direction wait.
7. **Backend/sampling:** pins, capture and treatment of serving failures await review.
8. **Training:** host, serving route, teacher and dataset choices; secondary priority.
9. **Spire:** restore/profile decision first, after WH3; other comparisons wait.
10. **Thesis/RL:** research question and environment details remain open.
11. **Local checkpoint RL:** stays paused; no recovery decision needed now.
12. **Factory:** test edits and approval for edits to `check.py` remain open; so do the older test-cleanup branches, `gate-xdist` and `team-check-battle-time` (handoff `runs/repo-improve-20261106/handoff.md`), and the tally suggestions and formal-map candidates (`runs/factory-multiagent-20261102/handoff.md`).
13. **Cannae:** does a script win clear harder A; three WingSupport repeats; rows 1, 2 and 5 of the checks.
14. **Communication structure:** what "forced" means, which arms, and what may start ([spec](twwarhammer3/communication-structure.md#questions-for-the-owner)).
15. **Historical siege evaluations:** the per-battle questions and set rules ([overview](twwarhammer3/historical-evals.md)), one test-plant re-anchor needing your yes, and when the first game window runs.

## Runtime and ownership

- Slay the Spire ([runtime facts](spire/integration.md#runtime-and-source-pins)): the installed game and personal profile slot 0 are authorized, including stats, unlock progress, history and achievements (Ironclad at unlock level 5 of 5 since the 2026-11-06 runs; runs record profile evidence).
- WH3 ([engine facts](twwarhammer3/integration.md)): a launch's mod list and startup-video skip
  persist for ordinary Steam launches ([how to reverse](twwarhammer3/README.md#commands)). Steam auto-update stays on.
- Also authorized: game windows, local GPU work, commits and pushes to public `main`, and paid API
  use within each ledger's cap. One game controller at a time across both games (each game's lock and process check cover only
  that game); one GPU job at a time.

## Branches
- `v11-keys` (`cd97667`): Spire v11 keys memory, on v10 (`54a5967`).
- `wh3-rules-v21-attack-path` (`5baf28b`): attack-route draft, labelled v21 before main's v21 (`18dabdd`); renumber before any merge.
- `wh3-human-opponent` (`de37005`, worktree `../slay_the_spire_ai-wh3-human-opponent`): parked by the owner (2026-10-22); resume at step 1 of the [plan](twwarhammer3/multi-agent-plan.md#d-single-client-steps).
- `spire-restore-replay` (`765ab2f`, worktree `../slay_the_spire_ai-spire-replay`): state-restore step 2 replay driver (`spire replay`), tested with a fake game only, never run.
- `team-check-battle-time` (`58a52ef`): agreed-check draft; `gate-xdist` (`668940e`): `check.py` on xdist workers. Each moves the report fingerprint.
- `gcp-retry` (`f038dc5`): US VM retry record, unmerged; three owner directions live only there.
- `tests-cleanup` (`ef90ec6`), `simplify-tests` (`2a36b13`): test-suite cleanups of 11-03, unmerged (decision 12).
- `spire-teacher` (`72b9233`), `spire-env` (`0b879d4`, contains `spire-teacher`) and `spire-docfix` (`95797bb`, docs only), each in worktree `../slay_the_spire_ai-<name>`: the rule policy, a `RealGame` environment and Spire doc corrections of 2026-11-06; landing waits on decision 4 of `runs/spire-offline-20261106/handoff.md`.
- `repo-improve-proposals` (worktree `../slay_the_spire_ai-repo-proposals`): 2026-11-06 changes that need the owner, one commit per choice; one-line choices in `runs/repo-improve-20261106/handoff.md`.
- Archived drafts are tags (`git tag --list 'archive/*'`).
