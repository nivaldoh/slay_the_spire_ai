# Project state

Updated 2026-11-23. Status only. History: [WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md), [first combat](spire/first-combat/README.md); directions: [owner-direction.md](owner-direction.md). Under the [hard rule](../AGENTS.md#verification-hard-rule), only listed agreed checks are verified at their recorded revisions; gameplay findings below remain unverified.

## Active work
The [seven-step restructure](restructure-plan.md#implementation-notes) is complete, and the [code walkthrough](code-structure.html#command-arguments) includes a command reference. The [WH3 log](twwarhammer3/log.md#2026-11-19-wh3-package-restructure) records the checks and limits. The changed checker imports and plant definitions await owner review ([item 17](review-queue.md#decisions)).

Terminal-Bench plan, 2026-11-15 (Claude): the superseded October designs are deleted except three classes current pages name (tag `wh3-legacy-20261115`), benchmark readers count through one outcome label and each declared scenario writes its own status; offline, $0, no live run ([log](twwarhammer3/log.md#2026-11-15-october-designs-deleted-one-outcome-label-a-status-on-each-scenario)). The rest of that plan followed the same day: readings off the witness modules, the scenario file split by family, a proposed change-levels table and evaluation page headers ([log](twwarhammer3/log.md#2026-11-15-readings-off-the-witness-modules-scenario-files-by-family-change-levels-page-headers)). Seven questions wait in the [review queue](review-queue.md#completed-work-and-handoffs).

Historical-battle construction: the [2026-11-14 holds](twwarhammer3/log.md#2026-11-14-first-haengju-and-izmail-construction-holds) stopped at Haengju's broken gate and Izmail's timer. Haengju's version decision remains parked. The [Izmail wall-height repeat](twwarhammer3/escalade-eval.md#wall-height-reference-and-repeat-2026-11-23) recorded both infantry within 3 m of a defender height from a separate stock hold. The [eligibility draft](twwarhammer3/escalade-eval.md#climb-eligibility-draft-2026-11-23) is parked locally and passed the offline opening rehearsal. The [Grom gate trial](twwarhammer3/escalade-eval.md#little-grom-gate-diagnostic-2026-11-23) read the stock siege attribute as false at dispatch. Under a diagnostic rule, the gate building and door both fell to 62% in 60 s. The [gate eligibility draft](twwarhammer3/escalade-eval.md#grom-gate-eligibility-draft-2026-11-23) composes that grant with the climb fallback and is parked for review. In the [stock ram trial](twwarhammer3/escalade-eval.md#stock-ram-gate-diagnostic-2026-11-23), the public ram reading moved from 312.2 m to 37.6 m from g1 over 180 s. The gate and door both read 100%. The arrival measure remains open. Both [authored-start probes](twwarhammer3/escalade-eval.md#authored-start-native-readbacks-2026-11-23) failed setup. The ram centres matched and its listed crew centres were 440.0 m apart between launches. A [passive follow-up](twwarhammer3/escalade-eval.md#passive-authored-start-follow-up-2026-11-23) found the crew still 129.0 m from the vehicle at 59.3 s and first read an eligible public wall defender at 18.5 s. The [authored slot check](twwarhammer3/escalade-eval.md#authored-slot-readback-draft-2026-11-23) is parked locally. It points to the ram crew's actual slot on all three saved openings. Codex owns one passive assembly readback with a 20:30 BRT cutoff. Stage 2 still needs agreement on the height check and eligibility rules, plus decisions on the tower fix and fixed starts. The [integrated draft](twwarhammer3/escalade-eval.md#integrated-stage-2-draft-2026-11-23) exercised the manifest and ticket launch guard offline.

Refusal sweeps, 2026-11-13 (Claude, overnight then from 10:28): tests now catch 55 of 59 refusal removals that the tests of nineteen WH3 files missed; tests, twelve plants and one sweep-tool fix; offline, $0. The Cannae and Alesia witnesses' 11 refusals now end the battle instead of counting as forfeits (owner's answer, 2026-11-13). Evidence: `runs/overnight-20261113/`, `runs/sweeps-20261113b/`.

Battle review, 2026-11-12 (Codex): b55 fixes deployment handover failures and siege replay omissions; evidence readers share accepted-order decoding. Reports retain planned attribution, failure costs and unavailable tie-breaks. Escalade V2 retains refused gate-attack replacements; V2 is still unadopted. The local-team audit found a target-retention test gap, now covered; no new policy defect reproduced. Live handover, halt effects and battle suitability remain unverified. Evidence: `runs/battle-review/`. No game or paid run scheduled.

Feedback and Alesia construction, 2026-11-12 (Codex): saved-input feedback probe and one case-a hold completed; independent recounts done, report selection updated. The feedback candidate remains unadopted. The hold missed the proposed first-rout-in-heavy-sector clause; actual army charge is unread. Both games closed. Evidence: `runs/comm-feedback-20261112/`. Next: decisions 14 and 15; no new game planned.

Benchmark progress, 2026-11-11 (Codex): exploratory P/R/O pilot, independent recounts and report update finished. All six battles lost; no ranking. Belgrade's Flagellants and Free Company report unowned in the lobby; no battle or roster change. Both games closed; recorded spend $6.45 of $30. Evidence: `runs/benchmark-progress-20261111/`. Next: endpoint/check agreement and Belgrade access.

Unmerged-work cleanup, 2026-11-11: selected tests, Spire rule policy/environment/replay and experimental Alesia contacts are merged. Fourteen original local branches and three remote branches were removed. The owner kept `wh3-human-opponent` and its worktree; experimental training is archived at `archive/spire-local-rl-20261111`, with results retained and three reproduced defects documented. No cleanup choice remains pending. No games or training started. Evidence: `runs/unmerged-cleanup-20261110/`.

WH3 single-army follow-up, 2026-11-10 (Codex): the owner chose all three communication structures, delegated a provisional messaging baseline and deferred runs. Communication necessity is one experiment type, not a universal prerequisite. Selected test-cleanup fixtures and targeted regressions landed during the 2026-11-11 cleanup; both old drafts were removed. Ownership repair and its 4/4 agreed scripted-team check remain recorded at `7b8b9bf`; overlap/reinforcement regressions remain unverified offline evidence. Both games are closed; API spend for the window remains $0 of $20. Evidence: `runs/cleanup-review-20261110/` and `runs/single-army-20261110/`.
Agent context loading, 2026-11-09 (Codex): [shared startup routes and personal-memory cleanup](context-loading.md); handoff `runs/context-loading-20261109/handoff.md`. No game work. Session speed and adherence remain unverified.

Spire local-model training, 2026-11-07, owner's repeated goal; nothing runs and the game is closed. Code archived as `archive/spire-local-rl-20261111`, handoff `runs/spire-rl-20261107/handoff.md`, decisions first. A second pick (learned fights with a human-taught run adapter) beat the 2026-11-06 best adapter (+2.80, interval +0.92 to +4.67) and the warm start on 60 fresh test seeds, one revision ([log](spire/fullrun/log.md#2026-11-07-evening-learned-fights-with-a-human-taught-run-adapter-beat-yesterdays-best-on-fresh-test-seeds)). **Owner: `STSUnlockProgress` is still the wiped copy; `runs/local-rl-20261106/handoff.md` has the restore commands.**

WH3 historical evaluations beyond Cannae, harness b54: one Alesia case-a hold, one Haengju stage 1a hold and two Izmail stage 1 holds played; all unverified ([overview](twwarhammer3/historical-evals.md)). Alesia, Haengju and Izmail retain their 2026-11-10 lobby readbacks. On 11-11 Belgrade's Flagellants and Free Company both reported unowned and unrecruitable despite sufficient funds; no complete army readback. Haengju, Belgrade, Alesia and Izmail have declarations, witnesses, controls and pages; Malta remains unbuilt. The owner approved models using siege orders: `llm`/`llm_rules` v23 offers them in Izmail; the commander and team members read the fort as facts without the orders, and `local_team` members do not see it. No siege battle has run on v23. Next: Belgrade access or an owner roster choice, and decision 15's Alesia premise before further construction trials.

WH3 [research focus](twwarhammer3/research-focus.md) saved for review (2026-11-06); contribution priority and scope remain open, no experiment scheduled.

[Cannae A/B/C](twwarhammer3/cannae-eval.md#window-2-results-2026-11-05) and the separate [air-relief candidate](twwarhammer3/tactics-reference.md#air-relief-audit-2026-11-05) remain unverified development candidates; all games are closed and none is scheduled. Next: decision 13.

[Infantry support timing](twwarhammer3/support-timing.md#stopped-comparison-and-next-steps) stopped at the owner's request on 2026-11-05; no further timing work or second scenario is scheduled. Next choose the coordination question worth studying before another scenario or live run.

Overnight suite run ended 2026-11-04; owner on its page: ok for now, reviews later; no more battles for now. [Scenario guidelines](twwarhammer3/scenario-guidelines.md): plan only, no evaluations scheduled.

GCP: no VM and no disk. Game disk deleted 2026-11-05 ([owner](owner-direction.md)), no snapshot, so a new VM session needs a fresh install and Steam login. Cloud spend of the $10: about $2.06 compute plus storage (unreconciled). [Native multiplayer](twwarhammer3/native-multiplayer.md#implementation-status): two live PC+VM battles at `01647bd` on 11-03, unverified (one battle each, no agreed check). [Three-step work](twwarhammer3/mp-next-steps.md): offline parts built, PC test bed run ($0), paid VM session stopped. [Foundation](twwarhammer3/multiplayer-control-foundation.md#implementation-status): one client so far; two clients and full acceptance remain. [VM team plan](twwarhammer3/vm-team-plan.md) decisions 1-4 still open.

[Visual reports](twwarhammer3/reports.md): the [cooperation proposal](twwarhammer3/reports.md#cooperation-evidence-proposal) adopts no new score; reader feedback on the [suite report](twwarhammer3/reports.md#coordination-suite) remains open.

Factory, repo upkeep of 2026-11-06: the owner ran both of its cleanup scripts (nine stale worktrees and 841 `runs/` paths removed); handoff `runs/repo-improve-20261106/handoff.md`. Repo upkeep and bug audit of 2026-11-08 (Claude; nothing runs): its fixes landed, the last 14 moving the report fingerprint ([log](twwarhammer3/log.md#2026-11-08-repository-upkeep-and-bug-audit)); handoff `runs/repo-improve-20261108/handoff.md`. The owner ran its cleanup scripts (159 `runs/` paths and 1,449 duplicate C: game logs, 4.2 GB).

Completed work and handoffs: [review queue](review-queue.md#completed-work-and-handoffs); [test repairs](twwarhammer3/log.md#2026-11-09-test-faults-timing-and-duplicate-setup). Later planning: [workflow](workflow.md#session-context-improvements).

WH3 first; Spire waits behind it; post-training is secondary.
Standing work (owner, 2026-10-28): thesis frontier; decisions/`JUDGEMENT` and small interviews; correctness/tests; code/repository upkeep; agent workflow efficiency. [Menu](autonomy.md#standing-work).
Thesis (decision 10): the research question is open; the [proposal](thesis/proposal.md) is one candidate ([directions](thesis/directions.md), [papers](thesis/papers.md)). Saved [references](references.md) have unverified WH3 applications and no experiment scheduled.

## Total War: WARHAMMER III
Benchmark [initial implementation](twwarhammer3/benchmark-initial.md) completed, version5 (decision 1): [definition](twwarhammer3/benchmark.md), [README](twwarhammer3/README.md), [results](twwarhammer3/results.csv). Controller ranking remains unverified.
[Coordination suite](twwarhammer3/benchmark.md#the-coordination-suite-suite-v1) (`suite-v1`): 12 scenarios, 6 played, first comparison 26 of 28 battles, one per pair; exploratory, no ranking.

- Runtime: `llm`/`llm_rules` v23, `commander` v8, `team_llm_rules` v23+t2, skills v1.2, harness b55 (handover fix checked offline); game [9.0.5/build 26403568](twwarhammer3/integration.md#pins).
  evaluator v2 plus mirror-v1, track `obs-v4+terrain/act-v2/live-1x`. Recording/arithmetic passed at `b1136e8`; strength and winnability remain unverified.
- [Chariot](twwarhammer3/tactic-cards.md) and Empire screens retain their historical rules/results; chariot confirmation, P5 and recovery studies are not the new benchmark's prerequisites.
- Scripted-team agreed checks passed at recorded revisions (latest live 4/4 at `7b8b9bf`); direct model-team mechanics passed one live case at `c1ad84d`.
- [Communication follow-up](twwarhammer3/communication-structure.md#exploratory-model-pilot-2026-11-11), 2026-11-11: two fresh model launches per chosen structure, six losses at `54c3c79`; raw recounts completed. The earlier scripted screen still failed its proposed gate. No ranking, benefit or verification claim. Next: decision 14; handoff `runs/benchmark-progress-20261111/handoff.md`.
- Spend: OpenAI $51.47 of $52; WH3 OpenRouter $21.33; Anthropic game ledgers $20.46 on 2026-11-12 (WH3 $20.2456, Spire $0.2124; includes estimates for failed calls); the key also spent $0.0211 on provider smoke calls, under its shared $200. GaP has a $5 cap.
- Battle checkpoints: Land live-value rule and all four declared siege states passed at `210e356`, build 26403568 ([limits](twwarhammer3/checkpoints.md#limits)); public player tool v0.1.0 still targets build 25961564.

## Slay the Spire

Paused behind WH3. No full run has won; the furthest reached Act 4, floor 54 (v8; `main` has v10).
Local Qwen3-0.6B (2026-11-07, unverified): a learned fight adapter with a run-level adapter taught by public human run files reached 17.82 floors on `LRTEST061`-`120` against 15.02 for the 2026-11-06 fight adapter (+2.80, +0.92 to +4.67) and 11.45 for the warm start; an earlier pick, 15.88 on `LRTEST001`-`060`, beat only the warm start, whose arm there spanned two revisions. Rests on the archived code's marked choices, including the human-run rows and the outcome tables ([log](spire/fullrun/log.md#2026-11-07-evening-learned-fights-with-a-human-taught-run-adapter-beat-yesterdays-best-on-fresh-test-seeds)).
The hand-written rule policy (now merged, no model) reached 26.0 floors on 37 seeds, unpaired with the models; whether the model may train on its choices is the owner's terms decision. A speed mod in that archived code played a run in about 30 s. Every floor above was played with it, and floors at speed do not pair with 1x.
Next, highest Spire priority (owner, 2026-10-23): the [state-restore investigation](spire/state-restore.md). Its first live step, a $0 replay check (driver now merged, never run live), needs a game window and your profile decision first.
Version differences sit within run-to-run variation (about 11 floors on one seed; same-harness replays differed by 13–26), measured only on three tuning seeds. `HELDOUT01`–`HELDOUT10` unplayed.
Spend: OpenAI $2.52 of $25, OpenRouter $3.46. The controller comparison (decision 9) waits; the owner deleted the old `v11-keys` draft; [open questions](spire/fullrun/README.md#open-owner-decisions). Paused: [first combat](spire/first-combat/README.md); planned: [open-weight](spire/open-weight/README.md).

## Post-training

Secondary priority. Capture, export and dataset smoke checks passed; the learning claims are the unverified [local Spire](posttraining.md#local-rl-on-complete-runs) warm start (2026-11-06) and the 2026-11-07 second pick, learned fights with a human-taught run adapter ([log](spire/fullrun/log.md#2026-11-07-evening-learned-fights-with-a-human-taught-run-adapter-beat-yesterdays-best-on-fresh-test-seeds)); the learned fights' own share was not separated. A training host, a way to play fine-tuned models, and useful targets are still missing ([plan](posttraining.md)). Local checkpoint RL stays paused (owner, 2026-10-28; decision 11); its failed synthetic gate establishes no general learning gain.

## Known issues

- A Ctrl-C during a job's final copying writes the record as `interrupted`, which `benchmarks.profile.evaluate` excludes from benchmark win rates (owner's answer, 2026-11-13; offline tests only). An interrupt in other cleanup steps, or a second one, can still lose the record.
- `runs/` has no backup (30 GB on 2026-10-31, inventory in `runs/overnight-20261031/b7/`); the owner said not now (2026-10-21).
- Check OpenRouter credits before paid jobs; OpenAI caps and the shared allowances are kept by hand. Keep both Anthropic ledgers under the key's $200: its limit error is untested.
- No test yet shows whether a game patch changes results (owner: later). A build warning shows in `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- WH3 readers differed on 3 timer wins, 8 controller failures and 5 wall caps of the 642 rows on 2026-10-31. Benchmark plan reports now show recorded and counted endings, exclusions, and possible win-rate ranges for matched unresolved attempts ([definition](twwarhammer3/benchmark.md), offline evidence in `runs/benchmark-accounting-20261123/`). For other scenarios the text `report` lists the engine outcomes for completed timer endings and still uses the historical non-timer win rate. `stats` tallies raw statuses. Register/`stats` also have blank benchmark versions and commit grouping.
- Since `1cc4582` each observation's `speed` is the engine's (one probe: 440/440 read 1); a slowed battle was never tried. A pause stops the `repeat_callback` tick, so no observation is written ([integration](twwarhammer3/integration.md#loading-phases-and-control)); the Windows-clock line (b51) covers pauses.
- WSL clocks ran about 6-8% slow against Windows (measured 2026-10-28, [clocks](twwarhammer3/integration.md#clocks-measured-2026-10-28)): WSL-timed think times, delays and short-window clock ratios are off; the battle itself runs at 1x.
- Spire runs often leave a profile preference file empty (25 of 43 data runs on 2026-10-23; [details](spire/state-restore.md#risks-found-on-the-way)). Decide the profile question before more Spire game time.
- Passive capture failed once under parallel load (11-01, before its wait became 30 s at `6079201`). The checkpoint source-run test now uses controlled time (`e10e85d`); no general flake-rate claim.
- Spire's Workshop mod pins still block a run when a mod updates.

## Owner decisions waiting

Details and source links live in the [review queue](review-queue.md#decisions). Numbers are unchanged; open the relevant item before acting.

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
12. **Factory:** unrelated test/process approvals, tally suggestions and formal-map candidates remain open (review queue). The old cleanup, xdist and battle-time drafts were removed during the owner-directed cleanup.
13. **Cannae:** does a script win clear harder A; three WingSupport repeats; rows 1, 2 and 5 of the checks.
14. **Communication structure:** all three structures chosen. The existing forced-message rule is provisional. After the [exploratory pilot](twwarhammer3/communication-structure.md#exploratory-model-pilot-2026-11-11), choose whether to redesign around wins or make raw `taken` primary, then agree the exact checks and scored run plan.
15. **Historical siege evaluations:** the per-battle questions and set rules ([overview](twwarhammer3/historical-evals.md)), the Alesia first-rout premise, and from 2026-11-14 Haengju v1's park or version 2 and Izmail's tower-owner fix, unit-level climb check and authored starts.
16. **Reference ideas:** two unadopted proposals, a difficulty threshold as the score and questions on judgement calls without a recommended option, await a yes, change or no.
17. **Restructuring plan.** [Owner decisions](restructure-plan.md#decisions-for-the-owner) cover the layout, migration and evidence. Review of the checker and plant changes remains open.

## Runtime and ownership

- Slay the Spire ([runtime facts](spire/integration.md#runtime-and-source-pins)): the installed game and personal profile slot 0 are authorized, including stats, unlock progress, history and achievements (Ironclad at unlock level 5 of 5 since the 2026-11-06 runs; runs record profile evidence).
- WH3 ([engine facts](twwarhammer3/integration.md)): a launch's mod list and startup-video skip
  persist for ordinary Steam launches ([how to reverse](twwarhammer3/README.md#commands)). Steam auto-update stays on.
- Also authorized: game windows, local GPU work, commits and pushes to public `main`, and paid API use within each ledger's cap. One game controller at a time across both games (each game's lock and process check cover only that game); one GPU job at a time.

## Branches
- `tower-owner-20261114` (`d6b4d76`, worktree `../slay_the_spire_ai-tower-owner-20261114`): siege tower owners read with the capture points' 0-based side; parked for the owner (review queue item 15).
- `wh3-human-opponent` (`de37005`, worktree `../slay_the_spire_ai-wh3-human-opponent`): owner explicitly kept both on 2026-11-11. Still parked; resume at step 1 of the [plan](twwarhammer3/multi-agent-plan.md#d-single-client-steps) when requested.
- Archived training: pushed tag `archive/spire-local-rl-20261111` (`5a227e5`); results stay recorded. Generic collector/trainer defects: `runs/unmerged-cleanup-20261110/review/rl/report.md`.
- Other archived drafts are tags (`git tag --list 'archive/*'`); deleted drafts from this cleanup are recoverable from its local `unmerged-before.bundle`.
