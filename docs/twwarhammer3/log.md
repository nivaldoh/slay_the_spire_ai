# WH3 log

Dated history of the Total War: WARHAMMER III track, newest first: each controller
version, benchmark harness revision and notable job, with what changed, the jobs, their
outcomes and costs, and the decisions taken. Status is in [state.md](../state.md); the
reference pages are listed in the [README](README.md#pages), whose [Terms](README.md#terms)
define the labels: `vN` an `llm`/`commander` version, `v1.N` the `skills` executor, `bN` a
benchmark harness revision, G1 and G2 the calibration stages.

- Jobs are `runs/twwarhammer3/battle/<job>/`. Bare `reports/`, `calibration/`,
  `capability-probes/` and `visual-probes/` paths are under `runs/twwarhammer3/`
  ([runs/README.md](../../runs/README.md)); code paths such as `battle/llm.py` are under
  `src/twwarhammer3/`. Each episode is a row of [results.csv](results.csv);
  `uv run python -m twwarhammer3 digest <job>[/episode-NNNN]` reads a job's evidence.
- Until the 2026-10-14 benchmark work the scenario is `kho5-dwf5` unless an entry says
  otherwise: a custom battle on "An Ogre's Folly", Khorne (player: Herald of Khorne, Chaos
  Warriors, Bloodletters, Marauder Horsemen with throwing axes, Skullcannon) against
  Dwarfs under the game AI (Lord, Dwarf Warriors, Longbeards, Quarrellers, Grudge
  Thrower), unit size large, real time at speed 1. Before v13 a decision came 5 s of
  battle time after the previous orders applied; since v13 it starts as soon as they are
  acknowledged.
- The benchmark entries (b1-b9 and G1, 2026-10-14) are development screens: no scenario
  was admitted under the former rule, G1 is incomplete and G2 never ran. Win-rate admission
  was retired in the 2026-10-15 plan revision below. "Margin" is the active-strength margin
  and "clock ratio" battle time over wall time
  ([benchmark.md](benchmark.md#outcomes-measures-and-comparison)).
- A new entry goes at the top, and "On main" is updated with it.

## On main

| Piece | Version | Defined in | Latest results |
|---|---|---|---|
| `llm` | v17 (2026-10-15) | `configs/twwarhammer3/system_prompt.md`, `battle/llm.py` | Shared input validated through `llm_rules` in b11; tactical prompt's last mode campaign was v15 (Luna low: 6 wins in 10 jobs) |
| `llm_rules` | shares `llm` v17 input; added in b3 (`51c1796`) | `configs/twwarhammer3/rules_prompt.md`, `battle/llm.py` | b11 smoke, Luna low: lost `dwf-line-skv-swarm` at 460 s ($0.043) |
| `commander` | v4 (2026-10-15) | `configs/twwarhammer3/commander_prompt.md`, `battle/commander.py` | b11 smoke, Luna low: lost `dwf-line-skv-swarm` at 593 s ($0.054) |
| `skills` executor | v1.2 (`55ab6b3`, 2026-10-13) | `battle/skills.py` (also `probe_abilities`) | `bench-b2-screen-ai10-20261014` won at 382 s; `bench-b2-screen-ai11-20261014` lost at 265 s |
| scripted baselines | `attack_nearest`, `rush_nearest` (b9), `hold` | `battle/scripted.py` | `bench-g1-cavalry-ai10-01-20261014`: walk-nearest lost at 411 s, run-nearest at 248 s; `bench-b9-timer-acceptance-20261014`: hold lost on the timer at 1205 s |
| benchmark harness | b11 (2026-10-15), evaluator v2, track `obs-v3+terrain/act-v2/live-1x` | `battle/play.py` (`TRACK`), `setup.py`, `controllers.py`, `report.py` | Two b11 engine outcomes; whole-unit counters and unchanged rematch checked. C1 remains development evidence |
| replay recorder | v1, on by default (`--no-record-replay`) | `battle/capture.py` | `visual-sol-low-20261015` |
| stills | imagery v3, opt-in (`--stills`) | `battle/capture.py`, `mod/script/_lib/mod/twwarhammer3_imagery.lua` | `visual-probes/close-imagery-r2-20261015` |
| report | redesigned for outside readers (2026-10-15) | `battle/report_html.py`, `report_assets/`, `replay.py`, `configs/twwarhammer3/report_notes.json` | `reports/benchmark.html` (27 MB): 55 jobs, 85 battles shown in 19 scenarios (6 diagnostic probes held back), headline C1 |

## Index

- 2026-10-15: [Report redesign for outside readers](#2026-10-15-report-redesign-for-outside-readers) ·
  [Harness b11: common measures and one report](#2026-10-15-harness-b11-common-measures-and-one-report) ·
  [Integrate llm v17 and commander v4](#2026-10-15-integrate-llm-v17-and-commander-v4) ·
  [Prioritize scenario variety and shared measures](#2026-10-15-prioritize-scenario-variety-and-shared-measures) ·
  [Plan revision and preparation](#2026-10-15-plan-revision-and-preparation) ·
  [Calibration C1, launches 3 to 6](#2026-10-15-calibration-c1-launches-3-to-6) ·
  [Calibration C1, launches 1 and 2](#2026-10-15-calibration-c1-launches-1-and-2) ·
  [Skaven swarm screens](#2026-10-15-skaven-swarm-screens) ·
  [Harness b10, `llm` v16 and the calibration decisions](#2026-10-15-harness-b10-llm-v16-and-the-calibration-decisions) ·
  [Unit costs and attributes from the game database](#2026-10-15-unit-costs-and-attributes-from-the-game-database) ·
  [Skaven swarm drafts](#2026-10-15-skaven-swarm-drafts) ·
  [Several models in one job](#2026-10-15-several-models-in-one-job) ·
  [Queue stops on changed rematch starts](#2026-10-15-queue-stops-on-changed-rematch-starts) ·
  [Report redesign](#2026-10-15-report-redesign) ·
  [Track cleanup for agents and reviewers](#2026-10-15-track-cleanup-for-agents-and-reviewers) ·
  [Sol visual acceptance and closer action views](#2026-10-15-sol-visual-acceptance-and-closer-action-views) ·
  [Native imagery probe and passive capture](#2026-10-15-native-imagery-probe-and-passive-capture) ·
  [Recorder acceptance and imagery candidate](#2026-10-15-recorder-acceptance-and-imagery-candidate) ·
  [Visual replay v1 and recorder candidate](#2026-10-15-visual-replay-v1-and-recorder-candidate)
- 2026-10-14: [Offline benchmark field report v1](#2026-10-14-offline-benchmark-field-report-v1) ·
  [Partial G1 and owner-requested stop](#2026-10-14-partial-g1-and-owner-requested-stop) ·
  [Benchmark harness b9 (timer classification and running baseline)](#2026-10-14-benchmark-harness-b9-timer-classification-and-running-baseline) ·
  [Benchmark harness b8 (caster control)](#2026-10-14-benchmark-harness-b8-caster-control) ·
  [Benchmark harness b7 (snapshot age and cavalry attacker candidate)](#2026-10-14-benchmark-harness-b7-snapshot-age-and-cavalry-attacker-candidate) ·
  [Benchmark harness b6 (Pegasus pressure hypothesis)](#2026-10-14-benchmark-harness-b6-pegasus-pressure-hypothesis) ·
  [Benchmark harness b5 (draft while b4 screens ran)](#2026-10-14-benchmark-harness-b5-draft-while-b4-screens-ran) ·
  [Benchmark harness b4 (compact specialist prototypes)](#2026-10-14-benchmark-harness-b4-compact-specialist-prototypes) ·
  [Benchmark harness b3 (specialist interface and `llm_rules`)](#2026-10-14-benchmark-harness-b3-specialist-interface-and-llm_rules) ·
  [Benchmark harness b2 (terrain, lobby modifier, Herald screens)](#2026-10-14-benchmark-harness-b2-terrain-lobby-modifier-herald-screens) ·
  [Benchmark harness b1 (paired trials, acceptance rotation)](#2026-10-14-benchmark-harness-b1-paired-trials-acceptance-rotation) ·
  [Battle types, llm v15 and commander v3 (overnight)](#2026-10-14-battle-types-llm-v15-and-commander-v3-overnight)
- 2026-10-13: [Random-battle comparison, partial (into 2026-10-14)](#2026-10-13-random-battle-comparison-partial-into-2026-10-14) ·
  [Ability readiness and army abilities, llm v14 and commander v2 (`9bfee82`)](#2026-10-13-ability-readiness-and-army-abilities-llm-v14-and-commander-v2-9bfee82) ·
  [Controller comparison on `kho5-dwf5`, stopped for random battles (late)](#2026-10-13-controller-comparison-on-kho5-dwf5-stopped-for-random-battles-late) ·
  [Shooter re-send fix, executor v1.2 (`55ab6b3`)](#2026-10-13-shooter-re-send-fix-executor-v12-55ab6b3) ·
  [Random battles](#2026-10-13-random-battles) ·
  [Skills and commander v1](#2026-10-13-skills-and-commander-v1) ·
  [Unpaused 1x battles only](#2026-10-13-unpaused-1x-battles-only) ·
  [Automatic startup video skipping](#2026-10-13-automatic-startup-video-skipping) ·
  [v13, continuous decisions and expanded battle controls](#2026-10-13-v13-continuous-decisions-and-expanded-battle-controls) ·
  [Early findings (milestones, first night, mirror battles)](#2026-10-13-early-findings-milestones-first-night-mirror-battles) ·
  [v12, v6's melee rules with v10's fire rules](#2026-10-13-v12-v6s-melee-rules-with-v10s-fire-rules) ·
  [v11, the lords never fight alone](#2026-10-13-v11-the-lords-never-fight-alone) ·
  [v10, shooters hit infantry in the open](#2026-10-13-v10-shooters-hit-infantry-in-the-open) ·
  [v9, fight the enemy holding you](#2026-10-13-v9-fight-the-enemy-holding-you) ·
  [v8, answer the enemy's guns](#2026-10-13-v8-answer-the-enemys-guns) ·
  [Mirror battles (second session)](#2026-10-13-mirror-battles-second-session) ·
  [v7, the enemy lord only while he is losing the lords' race](#2026-10-13-v7-the-enemy-lord-only-while-he-is-losing-the-lords-race) ·
  [v6, show what each unit is really doing](#2026-10-13-v6-show-what-each-unit-is-really-doing) ·
  [v5, a hurt lord keeps fighting](#2026-10-13-v5-a-hurt-lord-keeps-fighting) ·
  [v4, one body, gang up on the enemy lord](#2026-10-13-v4-one-body-gang-up-on-the-enemy-lord) ·
  [v3, commit and focus (best so far)](#2026-10-13-v3-commit-and-focus-best-so-far) ·
  [v2, a battle doctrine (worse)](#2026-10-13-v2-a-battle-doctrine-worse) ·
  [Baseline after the lapse fix](#2026-10-13-baseline-after-the-lapse-fix) ·
  [v1, first LLM battles](#2026-10-13-v1-first-llm-battles) ·
  [First baseline](#2026-10-13-first-baseline)

## 2026-10-15: Report redesign for outside readers

The owner asked for a benchmark report that an AI researcher who knows nothing about the
game would stop to read: comparisons that read at a glance instead of "117 / 217 · 323 /
530", no run-set sections about code revisions, the real-time aspect easy to see and
compare, a less generic style, and lean code. [reports.md](reports.md#the-page) describes
the page. No game ran and no model was called; `reports/benchmark.html` is rebuilt from
the same 55 jobs.

What changed on the page:
- **Commanders, not run sets.** One row per commander (model, effort, prompt or scripted
  rule) per scenario. A row can span several harness versions; its name then carries a †
  and Run settings names each battle's. The collector's JSON and text keep the strict
  groups. A harness fingerprint hashes the job's source files except presentation, the
  scenario declaration without its prose, game build, track, timing and recorder/stills
  switches, so C1's two revisions (docs and report files only) count as one.
- **Enemy army broken**, one mark per battle on a shared 0–100% axis (filled won, hollow
  lost, a cross for did not finish), replaces the soldier-count tables: `1 −
  active/registered` of the enemy at the end, floored below 100%, "n/a" when the evaluator
  did not record it.
- **The headline** beside the title is the largest controlled comparison in the first
  notes group: the commanders shared by two or more launches of one harness. Today that is
  C1: 6 launches, gpt-6-sol 1/6, gpt-6-luna 0/6, both baselines 0/6, median order age
  5.7, 6.3, 0.3 and 0.3 s.
- **Same battle, different plans**: route maps of every battle, one column per commander
  over one framing. On the cavalry assault every gpt-6-sol battle loops around the halberd
  screen; every other commander's paths run straight at it.
- **Real time**: per commander, one minute of its first finished battle as a sawtooth of
  the age of its latest view (on the cavalry assault between about 3 and 14 s for gpt-6-sol
  and gpt-6-luna at low effort, up to 22 s for gpt-6-luna at medium effort, 0.3 to 1.8 s
  for the scripted baselines), the median and 90th-percentile order age, and the measured
  battle/wall clock ratio (0.98–1.00 there). The same view age is the replay timeline's
  lowest band and, behind "Model's view", outlines of the view behind the latest reply.
  "See what moved during one reply" pins the median-age reply, showing every unit that
  moved 5 m or more. The asynchronous commander is charted by its plans' age (only plan
  adoptions carry `plan_age_s`), not its executor's 0.3 s. A labelled placeholder names
  the deferred added-delay experiment.
- **Honesty**: the curated C1 battle (gpt-6-sol's one win in 6) states the commander's
  record and that it is not a typical result; Method says every scenario is in-sample
  development; pooled cells in All scenarios carry †; the 6 diagnostic-probe battles and 6
  setup-only launches are counted under "Not shown"; analyst notes are labelled as written
  with AI assistance; one note's causal wording ("broke the guns") became the observed
  sequence after checking the frames; battles that reached the 20:00 timer read "at the
  time limit" although b8 recorded them as `engine_result`; Method lists what a model
  actually receives, beside abridged verbatim lines of one message and its reply.
- **Style**: a dark stage and a light results page, one type scale, a neutral UI accent so
  blue and orange mean only the armies, the decision panel's repeated caveats said once,
  and on a phone the results keyed and the hero chart moved after the battle.
- **Size**: the embedded replays keep only the fields the page draws, coordinates to
  0.1 m: the suite page went from 35 MB to 27 MB.

Notes: `brt-cavalry-emp-assault-hard` is titled "Cavalry assault, stronger enemy (+10%
stats)"; both cavalry challenges explain why a frontal charge is risky (the halberd and
gun claims already checked in the game database); scenarios carry a `group`.

Reviews: three independent critiques (target reader, information design, rigor) and a
synthesis, then a second reader and rigor round on the rebuilt page, then an acceptance
review against each requirement of the request plus a maintainability review of the code.
Their findings were applied except a latency-against-outcome scatter, rejected because
speed is confounded with the model here; the added-delay experiment is the controlled test.
The acceptance round moved the battle onto the first desktop screen (the page opens on the
key maneuver's moment and plays it once in view), kept the decision panel's orders in view
with a two-line run card, capped route columns at three maps, put the view age on one
0–25 s scale everywhere, removed data the page never read and a duplicate model test, and
repaired a browser check that had stopped asserting routes.

Validation: full `uv run pytest -q` and lint; prettier (width 100); the offline browser
check passed on the canonical page, a copy, the synthetic demo and the two-model pair page
at 1440 and 390 px, with no external requests or browser errors.

## 2026-10-15: Harness b11: common measures and one report

The owner authorized the first three plan steps. Alongside v17/commander v4 above,
evaluator v2 adds whole-unit registered/destroyed/alive/active counts, with routed,
leaving, absent and unreadable counts. Zero living entities is death; invalid targets
alone are not. Counts include later registered arrivals and deduplicate returning ids;
resurrection changes the current counts rather than accumulating kills. Existing soldier
totals, policy observations and the environment track stay unchanged. The evaluator
version is recorded in the manifest and evaluation; controller cards now record versions.

The report collector and HTML expose both sides' net headcount losses, survivors and
whole units, per-point engine-tick ownership duration/share, supplies, tickets, accepted
builds and purchases, duration, order age, API cost and failures. Failed runs retain
partial progress; missing historical counts stay unavailable. Historical snapshot-voting
shares are not presented as objective time. Scoring stays outside policy inputs and public
replay exports; no aggregate ranking or scenario-specific score was added.

`reports/benchmark.html` (with JSON/text) is built from the explicit
`configs/twwarhammer3/benchmark_jobs.json` list using `report --jobs-file`: 55
jobs, 91 started trials (85 engine outcomes), 19 scenarios and 10 battle types: cavalry,
swarms, specialist screens and historical mode pilots, including failed attempts. Older
mode pilots lacked declaration names; the selector now uses their saved config names
instead of putting every unnamed mode together. Source revisions, evaluator versions and
game builds remain separate evidence groups. A collapsible overview shows armies and
coverage; each scenario keeps its comparisons, run settings, notes and replays. Existing
scenario reports are retained. The single-file HTML is about 33 MiB. Related scenarios
have distinct readable titles. Matching controller class/prompt hashes across source
revisions no longer claim identical controllers: shared dependencies can change too.

Runtime prerequisite: Steam updated after C1 to 9.0.4.0, build 25961564 (complete install,
no staged bytes). The executable reports The Creative Assembly Ltd; SHA256
`9bd58c63bd7fc5c9909b3d3d9b6b7a6ae4eac784369bf91a9e53c3e9f42be496`. Updated the pins
and retained the prior build/hash in integration.md. `doctor` is ready. Older 9.0.3
trials retain their provenance and are not pooled with new-build checks.

Live validation: `bench-b11-measures-20261015`, source `c251401`, ran 17:39-18:00 UTC.
Luna low controlled both episodes of `dwf-line-skv-swarm`, unpaused 1x, added age zero,
Steam build 25961564. The rematch preserved roster, strength, loadout, resources and
positions; both episodes ended on engine losses. Total cost $0.09664; ledger $14.3146
of the $25 cap.

| Controller | Loss at | Friendly units destroyed / alive | Enemy units destroyed / alive | Soldiers remaining, friendly / enemy | USD |
|---|---:|---:|---:|---:|---:|
| commander v4 | 592.7 s | 2 / 5 | 0 / 20 | 71 / 1416 | 0.05376 |
| llm_rules v17 | 460.0 s | 1 / 6 | 0 / 20 | 155 / 1702 | 0.04289 |

Both started with 7 friendly units / 331 soldiers and 20 enemy units / 1961 soldiers.
At both losses every surviving friendly unit was routed, none active; the commander
episode also retained one living leaving unit. Initial/final evaluator v2 counters
reconciled. All 753 decision observations and 1046 replay frames exclude evaluation,
final and setup data. Clock ratios were 1.000 and 0.988. Range feedback appeared in both
live controllers. Neither battle triggered the last-sighting annotation; that case was
checked by rendering actual historical routed-enemy observations through v17.
Audits: `validation/b11-engine-check.json` and `validation/b11-v17-historical-rendering.json`.
Arrivals, returns, resurrection and unreadable counts have Lua regressions; those new
counters still need mode-specific engine evidence as the scenarios expand. These smoke
trials validate integration, not controller improvement or a model ranking.

Validation: full `uv run pytest -q` passed (990 passed, 14 skipped); lint passed.
Tests cover routing versus death, absence/withdrawal, late/returning units, failed reads,
resurrection, historical missing measures, point identity/duration, information boundaries,
explicit input lists and unnamed pilot navigation. Offline Chromium checks passed on the
canonical HTML and a copy: all 19 scenarios, replay navigation/downloads, historical
missing measures, both new whole-unit results, objective point/time fields, controller
versions, desktop and phone layouts. No external requests or browser errors.
Screenshots/downloads are in `report-checks/benchmark/`; test and audit artifacts are in
`validation/`. No new scenario or calibration campaign is included.

During validation the owner clarified scenario selection: difficulty is useful only
when there are meaningful plays. The plan and report guidance now require exploitable
advantages, manageable choices about disadvantages and room for those decisions to
change progress. Use the exploratory runs to inspect recognition and execution; redesign
or drop scenarios with no credible options, retaining their evidence. This applies to
existing cavalry/swarm challenges too, without reinstating a win-rate admission rule.

## 2026-10-15: Integrate llm v17 and commander v4

Merged `wh3-llm-v17` (`c1cc14b`) into current main. Shooter target lines now say how far
beyond range a target is and that the unit advances to shoot. Last-sighting memory keeps
wavering, routing and shattered state, explicitly labelled as the state when last seen.
The commander shares both rendering and memory, so this is `llm`/`llm_rules` v17 and
commander v4. No system prompt, executor or environment contract changed; the track stays
`obs-v3+terrain/act-v2/live-1x`.

Validation: 44 LLM/commander/prompt tests and all 349 WH3 tests passed; `uv run ruff check .`
passed. Golden prompts did not change (their cases do not trigger the new feedback).
The [b11 smoke check](#2026-10-15-harness-b11-common-measures-and-one-report) validates
the shared renderer and both controller versions in the game. Existing results and
register rows retain their original revisions.

## 2026-10-15: Prioritize scenario variety and shared measures

The owner refined the plan again, with implementation still out of scope: general
milestones (kills, survivors, objective time and similar measures) come first;
scenario-specific points are a possible later improvement. The immediate goal is more
battles that look and play very differently, including varied land armies, siege,
survival and conquest. Start each new scenario with 2-3 exploratory battles total;
deeper testing can follow later.

Updated the [implementation plan](benchmark.md#implementation-plan), state, root/track
READMEs, battle-type next steps, runbook and report plan. The previous ten-battle proposal
across three scenarios is superseded; it was never launched. Keep the old calibration and
cavalry/swarm evidence, with no repeat campaign required before adding new modes.

The audit distinguishes content work from missing mechanics: siege defence, survival,
conquest and the other modes already ran end to end, mostly with the same small
Khorne/Dwarf armies. Distinctive rosters/maps/objectives are the next content work.
Siege attack's gate/wall/equipment gap does not block defence. Survival/domination hide
the lobby timer expected by the current strict benchmark declaration checks; adapt those
checks for the selected mode, without treating a controller wall limit as a game timer.

Common measures use existing headcounts and objective integrals first. Whole-unit
destruction/survival counts need minimal shared evaluation counters, not scenario-specific
scoring or a full per-unit event recorder. Historical missing counts stay unavailable.
Reporting expands incrementally at one canonical HTML entry point; scenario-specific
scores, complete model matrices and added-delay experiments remain later work.

No gameplay/source/configuration changes, branch merges, report builds, queues or paid
calls. Validation: `uv run pytest tests/test_doc_links.py -q` (43 passed),
`uv run ruff check .` and `git diff --check` passed.

## 2026-10-15: Plan revision and preparation

The owner requested planning, documentation updates and stale-file cleanup, with no
implementation of the five discussed changes. The
[plan](benchmark.md#implementation-plan) now starts with hard cavalry/swarm challenges,
partial progress beside engine outcomes, model comparisons under declared conditions,
natural latency, and one canonical HTML report for the suite. The 30-70% admission gate
and automatic switch to AI ×1.0 after C1 are retired. Added-delay experiments and broader
scenario/model work are deferred. C1 and the swarm screens remain development evidence;
this preparation does not claim new experimental findings.

The implementation audit refined the plan:
- `wh3-llm-v17` changes controller memory/rendering only, not the environment's public
  observations, actions or timing; the earlier `obs-v4` description was wrong. The
  commander shares those functions, so integration needs both controller versions and
  their tests. The branch remains unmerged.
- Final evaluation totals already support casualties and active survivors by unit type,
  and objective integrals exist for applicable battle types. Exact per-unit milestones,
  HP/value scores and original-roster-only denominators need more recording. Routing is
  not destruction; report missing measurements explicitly. New derived measures will
  version the evaluator, without rewriting old results.
- Multi-scenario HTML already works. The missing pieces are a canonical report build,
  suite overview and progress presentation. Supporting assets may remain embedded;
  splitting them is conditional on measured size/loading, not a new requirement.

Updated the state, root/track READMEs, benchmark, runbook, controller candidates, battle-type
next steps and report docs. C1's six-launch completion and the swarm's actual Warlord
roster/protected Engineer are now consistent across them. Compressed obsolete calibration
discussion to historical summaries with its existing link anchors; the full former text
remains at `ae7ca31:docs/twwarhammer3/benchmark.md`. The original owner briefs are retained.

Cleanup under this request: pruned eight worktree records whose `/tmp` directories no
longer exist; deleted the merged branches `wh3-benchmark-b2`, `-b3`, `-b4`, `-b5`, `-b7`,
`-b8`, `-b9` and `wh3-visual-final`; deleted `wh3-visual-imagery` (`af8f76e`) after
`git cherry main wh3-visual-imagery` verified its only commit was patch-equivalent to
main's `ca397ab`. No working files or unique work were removed. Kept v17 and its
component branches, the unique older candidates, all saved runs/reports, queue plans,
register rows and ledgers. Old queues are explicitly historical, not next-run commands.

No source/configuration code changed, no report was rebuilt, no game ran and no paid
model call was made. Validation: `uv run pytest tests/test_doc_links.py -q` (43 passed),
`uv run ruff check .` and `git diff --check` passed. Game/source tests are reserved for
implementation; this change is documentation and repository housekeeping only.

## 2026-10-15: Calibration C1, launches 3 to 6

Launches 3-6 of C1 ran from about 11:05 to 13:10 UTC-3 (`bench-c1-cavalry-ai11-03-20261015`
to `-06-`, queue `runs/twwarhammer3/calibration/c1-plan-rest.json`, completed); their 16
register rows are committed with this entry. Over all six launches: `llm_rules` on Sol won
1 of 6, `llm_rules@gpt-6-luna`, run-nearest and walk-nearest 0 of 6 each; every battle
ended on the engine's result. WH3 ledger: $14.2179 of $25. The report
`reports/c1-cavalry-ai11.html` covers all six launches. The results have not been analysed
or read against the C1 rule yet: that waits for the owner.

## 2026-10-15: Calibration C1, launches 1 and 2

The first two of C1's six launches on `brt-cavalry-emp-assault-hard` (AI ×1.1), harness b10
and `llm` v16 (source `8434cd3`), each rotating the four controllers
([decisions](benchmark.md#calibration-decided-2026-10-15)); the morning queue ran them after
the swarm screens, unattended, and completed. Every battle ended on the engine's result;
none reached the timer.

| Launch | Controller | Outcome | Battle s | Own active | Enemy active | Order delay s | USD |
|---|---|---|---|---|---|---|---|
| `bench-c1-cavalry-ai11-01-20261015` | `llm_rules`, Sol | lost | 1017 | 0 | 0.570 | 5.58 | 1.4358 |
| | `llm_rules@gpt-6-luna` | lost | 298 | 0 | 0.530 | 5.14 | 0.0254 |
| | run-nearest | lost | 214 | 0 | 0.802 | 0.30 | 0 |
| | walk-nearest | lost | 325 | 0 | 0.875 | 0.30 | 0 |
| `bench-c1-cavalry-ai11-02-20261015` | `llm_rules`, Sol | **won** | 487 | 0.203 | 0 | 5.77 | 0.6706 |
| | `llm_rules@gpt-6-luna` | lost | 803 | 0 | 0.260 | 8.03 | 0.0484 |
| | run-nearest | lost | 244 | 0 | 0.692 | 0.30 | 0 |
| | walk-nearest | lost | 350 | 0 | 0.849 | 0.30 | 0 |

So far Sol 1 of 2, Luna 0 of 2, both baselines 0 of 2: within the admission band, far from
decided. Sol's battles cost $0.67 and $1.44 (the lost one lasted 17 minutes), more than
the ×1.0 runs; at that rate launches 3-6 cost about $4-6. The per-policy rotation recorded
each trial's own model end to end (manifest, card, register). The register rows of the
screens and these launches are committed with this entry. WH3 ledger: $10.0391 of $25.

Sol's win against its loss, from the traces (a read-only review): both openings went
south of the obstruction for the guns ("Advance the cavalry around the south side of the
central obstruction to approach the enemy flank" in the win), and the guns broke at
similar times (186-236 s and 197-226 s). After that the win kept fighting the halberdiers
until the last broke at 487 s (they fell from 360 to 93 men). The loss withdrew, and from
376 to 1002 s 100 of its 114 reasons were about finding the routed guns, which the
prompt's last-sighting memory listed at the map edges without saying they were fleeing;
the halberdiers lost 58 men and the army routed at 1005 s. Supported: continuing against
the halberdiers separated the two. Plausible, not shown: the last-sighting entries led the
search. Unsupported: the route or losses on the way in decided it (124 and 120 knights at
about 257 s). The report `reports/c1-cavalry-ai11.html` features Sol's win as the selected
example with two analyst notes written from its recorded events (`report_notes.json`; a
second reader confirmed the first and corrected the second, which missed a rally; the owner
has not reviewed them).

Luna's two battles, by the same kind of review: both opened with a straight charge at the
line ("Exploit cavalry speed to disrupt the cannon and handgunners while the lord engages
the enemy general." in the first), with no flanking route, and met the halberds first. In
the 298 s loss the Lord won its duel with the General but the knights broke against the
halberds; in the 803 s loss the Lord lost the duel, units were withdrawn from 115 s, the
Lord stood idle in a corner from 365 to 689 s, and the knights later killed the fleeing
General and shattered one halberd unit before routing. Supported: the straight approach
in both, unlike Sol's; that the withdrawals explain the longer battle is plausible only.

## 2026-10-15: Skaven swarm screens

Both swarm drafts ran one screen each under the owner's authorization, on harness b10
with `llm` v16 (source `8434cd3`): `bench-b10-screen-skv-swarm-r2-20261015` and
`bench-b10-screen-dwf-line-20261015`. The first attempt (`bench-b10-screen-skv-swarm-20261015`)
stopped in the lobby before any battle: the declared `wh2_main_skv_cha_grey_seer_ruin_0` has
no card (a caster with several lores has one, `_plague_0`). Setup now dumps every army's
cards to `cards_slot<N>.txt`; the Warlord leads instead, the Warlock Engineer is the caster.

Results (table in [benchmark.md](benchmark.md#scenario-design)): every player army was
routed. Luna lost the swarm attack at 457 s (enemy 0.706 active) and the Dwarf hold at
444 s (0.640); run-nearest lost the attack at 288 s (0.921) and `hold` the hold at 565 s
(0.529; 0.561 over the original force, since a summoned Skaven unit joins the total),
outlasting the model: the model's repeated attacks on an enemy cannon out of range pulled
its Organ Gun and shooters out of the line ([benchmark.md](benchmark.md#scenario-design),
[controllers.md](controllers.md#candidate-changes-for-the-next-version)). Both prototypes
are now `prototype_not_admitted`. Cost
$0.064, both Luna battles.

Order delay grows with the units in view, observed across unrelated runs (Luna low,
mean per battle, from results.csv; versions and battles differ, so this is a motivation
for the army-size experiment, not a measurement): about 5-7 s with 10 units on the field,
6.5-7.3 s with 24, 8.2 s with 27 and 9.2 s with 29.

The independent check of the analyst notes, under the owner's delegation, dropped none
and corrected six (a melee start at 4:04 not 4:05, all five units attacking the
handgunners, the opening plan's other targets, "no men lost" limited to the Lord and
knights, "new moves" not "re-issued routes", "about" on a sparse-frame time). It also
found that "in melee with X" trusted the target field alone; a melee fact now needs the
target recorded within 50 m.

## 2026-10-15: Harness b10, `llm` v16 and the calibration decisions

The owner, away until 11:00 (UTC-3), delegated the open WH3 decisions to the agent's
judgement and authorized the swarm screens. Decided and recorded:
- **`llm` v16** (`llm_rules` shares it): the `wh3-llm-fresh-move` fix is merged (`005a050`).
  A move applied at the observed instant reads "your move to (x, z) issued this instant",
  not "stopped N m short". Golden prompts are unchanged; prompt text differs only in that
  state.
- **Benchmark harness b10**: per-policy models (`NAME@MODEL[/EFFORT]`), the queue's
  start-change stop rule, v16, and the redesigned report. Track unchanged
  (`obs-v3+terrain/act-v2/live-1x`).
- **Calibration**: the options in [benchmark.md](benchmark.md#calibration-decided-2026-10-15)
  are adopted as block C1 on `brt-cavalry-emp-assault-hard`: `llm_rules` on Sol low
  (reference) and on Luna low, run-nearest and walk-nearest, rotated in each launch.
  Primary measure: the engine outcome before the timer. Two of the six launches run
  this morning (the time until the owner returns); the other four are a frozen plan.
- **Analyst notes**: accepted under the delegation after one more independent check,
  which corrected six of eight ([swarm screens entry](#2026-10-15-skaven-swarm-screens));
  the owner can still revise them.

## 2026-10-15: Unit costs and attributes from the game database

`scripts/wh3_db.py` decodes a table of the game's `db.pack` with RPFM's schema, read-only
([integration.md](integration.md#packs-and-loading)); a synthetic table tests it. Two uses
so far, no game run:
- **The swarm drafts fit their funds**: decoded `multiplayer_cost` totals are 7850
  (Skaven) and 8200 (Dwarfs) for `skv-swarm-dwf-line`, 6300 and 8350 for
  `dwf-line-skv-swarm`, under 12000; no unit exceeds its multiplayer cap. As a check, the
  taurox rosters that played under large funds decode to 10675 and 11525.
- **The report's unit text now rests on game data**, not only recorded base stats:
  Halberdiers have a +16 bonus against large units with charge defence and charge
  reflection against large, so their role reads "Anti-cavalry infantry"; 38 of the
  Questing Knights' 52 damage is armour-piercing and they are immune to psychology; Grail
  Knights have magical attacks and never tire; Mounted Yeomen Archers fire on the move;
  Great Cannons cannot run; both generals encourage nearby units. Weapon damage plus
  armour-piercing damage matches each unit's recorded `weapon_damage`, which cross-checks
  the decoding. Nothing decoded is committed.

## 2026-10-15: Skaven swarm drafts

Two specialist scenarios from the owner's 2026-10-14 steering ("commanding/fighting
Skaven swarms") are declared as drafts, never run: `skv-swarm-dwf-line` (20 Skaven, led by
a Grey Seer with a few weapon teams, attack 9 Dwarfs on a gun line) and
`dwf-line-skv-swarm` (7 Dwarfs hold against 20 Skaven; the defender wins at the timer).
Status `draft_not_screened`; rosters, protected units and the screens they need are in
[benchmark.md](benchmark.md#scenario-design). Every unit key exists in the game's English
localisation, read from `local_en.pack` without extracting anything; both declarations
pass `validate_declaration` and build their lobby steps offline. Unit costs are not
recorded anywhere, so whether both rosters fit the 12000 custom funds is the first thing a
screen checks. The report notes carry each scenario's question for when it runs. The
`setup.py` field reference no longer says `status` puts a scenario in the HTML report.

## 2026-10-15: Several models in one job

A model policy can name its own model and effort, `NAME@MODEL` or `NAME@MODEL/EFFORT`
(`controllers.policy_parts`), so one launch can rotate, say, `llm_rules` on Sol and
`llm_rules@gpt-6-luna` on the same battle instance; launches are the benchmark's sampling
unit, so model comparisons can now be paired within them. Bare names keep `--model` and
`--effort`; a name resolving to another's model and effort is refused as a duplicate.
Cards, results and the report keep the full name; the register records the base policy
with the model and effort played; the job saves one prompt per base policy. Reports of
existing jobs are byte-identical. No game ran and no model was called: an adversarial
review with fake jobs found six issues (a card-less trial named with the job's model, the
review workflow's stale prompt-file guidance, readers checking old suffixes against
today's prices, no browser test of suffixed names), all fixed with tests; the synthetic
pair report in `make_wh3_report_demo.py` now exercises suffixed names in the browser check.
`uv run pytest -q`: 974 passed, 14 skipped.

## 2026-10-15: Queue stops on changed rematch starts

`scripts/wh3_queue.py` now applies the recorded G1 start rule itself: after each job it
reads every episode's `start_comparison` and stops the plan (status failed) when a
rematch started with a missing or changed unit, or changed strength, loadout or
resources. Position and bearing flags alone stay in the result. A resumed calibration
no longer needs a separate audit for this; admission is still audited separately. No
game ran. Tests: `tests/twwarhammer3/test_wh3_queue.py` covers both kinds of change and a
geometry-only flag.

## 2026-10-15: Report redesign

The owner's brief ([WH3_report_redesign_guide_for_Codex.md](WH3_report_redesign_guide_for_Codex.md))
asked for a report that lets a newcomer watch an AI command an army, understand its
consequential decisions and compare results, with the bookkeeping moved out of the
reading path. The HTML page was rebuilt around that order (watch, what happened,
compare); [reports.md](reports.md) describes it. No game ran and no model was called.

The brief asked for its items to be mapped to the repository first:
- **From existing records**: readable names and roles (the game's onscreen names,
  checked against the English localisation, and comparisons checked against each
  episode's recorded `unit_base_stats`), orders in plain words with queued steps and
  rejections, what the recorded frames show after each batch, the information age per
  decision on the battle clock beside the model's wall-clock reply time, stable map
  framing, issued routes apart from observed trails, the engine outcome with the timer
  rule, and run sets compared in plain words (the two Sol runs share controller code and
  prompts; the later one added the recorder and stills).
- **Small additions**: `configs/twwarhammer3/report_notes.json` (scenario question and
  challenge, unit roles, the selected run and its analyst notes); the collector's
  `order_age_median_s` and `battle_ms`; replay payload fields (unit identities, `steps`,
  `summary`, `next`, key events).
- **Needs new instrumentation, runs or an owner decision, so not built**: a real-game
  clip (no video capture exists), unit artwork (the owner ruled out pack art on
  2026-10-14), unit attributes that are not recorded (anti-large and armour-piercing live
  in the game's database tables), response-to-visible-effect timing, and the army-size,
  context and delay experiments, now defined in
  [benchmark.md](benchmark.md#experiments-the-report-should-eventually-present-definitions-only).

What changed:
- The page leads with the scenario's question, the selected run (outcome, duration,
  "Single recorded battle"), one sentence of input conditions and the replay. Removed
  from it: the masthead, throughput and wall time, the scenario declaration, the stills
  wall, failed-capture placeholders, the margin chart, the trial and tactical tables and
  the evidence section. They stay in the JSON and text reports, Run settings and the
  downloads. The 15 unrun catalogue placeholders are gone, which settles the deferred
  item.
- The moment panel follows the replay clock and never shows a reply before it applied;
  it gives the model's stated reason as a quotation (with a key for the unit ids it
  uses), the orders, what happened next and how old the information was. Before/after
  inspection is an explicit, pinned mode that includes the orders' targets.
- Five analyst notes on `visual-sol-low-20261015` (one is the featured maneuver) and three
  on the G1 Sol trial, each checked against the records by two independent reviewers. The
  brief asks for human review: the owner has not reviewed them yet.
- The active-strength margin no longer appears on the page (the brief: it counts routing
  men as lost and weighs units equally); the collector still computes it.

Findings:
- **The state taken as a batch applies predates it.** Units that were just ordered still
  show idle there. The replay's "what happened next" now ignores that frame. The `llm`
  prompt called such units "stopped N m short of your move": in the G1 Sol battle the
  model re-issued all six routes three times in 26 s. The fix is on branch
  `wh3-llm-fresh-move` (`5959587`), unmerged: it changes prompt text, so it is a new
  controller version and part of the calibration discussion.
- The cavalry assault already separates controllers at ×1.0 on outcomes alone (Sol low
  3 of 3, Luna 0 of 2, scripted 0 of 7, across revisions); options for the owner are in
  [benchmark.md](benchmark.md#calibration-options-for-the-owners-discussion-2026-10-15).

Validation: `uv run pytest -q` 949 passed, 14 skipped (the `train`/`llm` extras and the opt-in
Windows test); `uv run ruff check .` and prettier (width 100) clean; the offline browser
check (`tests/twwarhammer3/check_wh3_report_browser.cjs`) passes on the three jobs and
the demo at 1440 and 390 px. Reviewers read screenshots against the brief's six reader
tasks; a data review rebuilt all 200 recorded episodes without a crash. The rebuilt page
is `reports/cavalry-assault.html` (1.7 MB).

## 2026-10-15: Track cleanup for agents and reviewers

The owner asked for the WH3 code and repository to be easier for agents and outside
reviewers to read and navigate: less bloat, redundancy and stale or confusing docs. An
audit of eight areas fed six code lanes and three docs lanes. No game ran and no model was
called; the work was uncommitted when this entry was written.

What changed in the code:
- CLI. `twwarhammer3 report JOB [JOB ...] --output STEM` writes `STEM.html`, `STEM.json`
  and `STEM.txt` and replaces `stats --report/--report-json/--report-html`. `stats
  --rebuild` is gone: it rebuilt only from `battle/`, so it dropped six visual-probe rows,
  re-added two interrupted episodes and rewrote 288 cells; the register is append-only
  history. New: `digest EPISODE --at SECONDS` (one decision in full: the prompt its reply
  answers, the raw reply, the orders and the engine's verdicts) and `watch JOB --next
  [--stall-minutes M]` (waits for the next episode result, the job's end, a stall or a job
  that never started, prints it and exits). `play` lost `--ledger`, `--results`,
  `--no-autostart` and `--no-menu`; `launch` lost `--interval-ms`, `--no-autostart` and
  `--no-menu`, and `play --attach` uses its own `--interval-ms`. `--episode-timeout`
  defaults to a declared scenario's timer plus 120 s (else 3900 s) and `--run-timeout` to
  8 h, or longer when the episodes need it.
- Job loop and scenarios. Scenario loading, lobby steps and benchmark checks moved from
  `battle/play.py` to `battle/setup.py`, whose docstring is the scenario field reference.
  A `scenarios.json` entry can inherit another with `base` (the file went from 1623 to
  576 lines; the resolved scenarios that manifests record are identical). A refused
  declaration, realism preference or uncommitted source scope no longer leaves a job
  directory, so the same `--output` can be retried. Model jobs snapshot
  their prompt as `<policy>_prompt.md`. Objective shares come only from the mod's tick
  integrals. The setup saves its menu dumps on every exit. `session.json` no longer
  carries `interval_ms`. `scripts/wh3_queue.py` runs a frozen plan of `play` jobs one at
  a time; the untracked `calibration/run-*.py` runners are evidence only.
- Controllers. `probe_move` is gone. `battle/controllers.py` holds the one table of model
  policies and their prompts. `llm.py` shares `split_valid`, `strengths`, `render_clock`
  and `invalid_reply` with the commander and lost its unreachable paused-battle sentence;
  `scripted.distance` is public. `tests/twwarhammer3/test_wh3_prompts.py` compares the
  exact rendered prompts of `llm` (whose input `llm_rules` shares) and `commander` with
  golden files: no prompt byte changed.
- Reports and capture. `battle/capture.py` replaces `imagery.py` and `recording.py`;
  `visual_probe.py` and `report_html.py`'s `--demo` entry are deleted, and the synthetic
  demo comes from `tests/twwarhammer3/make_wh3_report_demo.py`. The replay payload lost
  its derived duplicates and names controllers as the controller table does; `replay.css`
  merged into `report.css`; a report with stills fails loudly without Pillow. The replay
  verdict's median information age is now the collector's order-age median over
  non-empty batches: 5.25 s instead of 5.1 s for the G1 Sol trial, 4.2 s instead of
  3.9 s for `visual-sol-low-20261015`. The saved artifacts in `reports/` predate this.
- Tools. The job digest has a policy column and no longer crashes on random survival and
  free-for-all draws; the episode digest folds runs of decisions without new orders into
  one line (`no new orders xN until T s`). `watch` no longer crashes at a classic
  battle's result and shares the commander's report header. New register rows round
  `own_active` and `enemy_active` to 3 decimals. The `engine/mailbox.py` docstring is the
  bridge and observation reference; a job start also clears the previous job's per-battle
  replay, imagery, still and capture files from the bridge.
- Tests. lupa and Pillow joined the dev group, so plain `uv run pytest` runs the Lua and
  image tests (21 Lua tests skipped before). The six `test_wh3_lua_*.py` files became
  `test_wh3_battle_lua.py`, which loads battle-script definitions by name
  (`tests/twwarhammer3/wh3_lua.py`); `test_wh3_mod_scripts.py` compiles every mod script
  under Lua 5.1, replacing the manual parse step. `tests/test_doc_links.py` checks every
  relative link and anchor in the repository's Markdown. `uv sync --locked` now removes the
  `llm` and `train` extras' packages; restore them with `uv sync --locked --extra llm` (or
  `--extra train`).

Docs: `benchmark.md` is the benchmark as built, `benchmark-run.md` the runbook and the new
`reports.md` the report page. `benchmark-progress.md`, `calibration-plan.md`,
`scenario-recipe.md`, `field-report.md` and `visual-report-plan.md` were folded into them;
their text stays at `d606d39`. The owner's modding guide `guide.txt` (dated 2026-10-08,
unchanged since `001d1ce`) left the tree: `git show 001d1ce:docs/twwarhammer3/guide.txt`
restores it, and its API links are in integration.md "References". The README,
integration.md, controllers.md and battle-types.md are reference pages now: the README's
milestones, first-night and mirror sections and battle-types.md's per-job tables moved
into this log; integration.md is grouped by subject, with the "Expanded controller
interface", "Specialist unit state" and "Timer result transition" sections folded into
"Battle" and the "Unverified" heading shortened; controllers.md lists every registered
policy, drops the flying-unit gap fixed in `dde4cfe` and records three prompt/code
contradictions for the next version. This log is newest first throughout, with "On main"
above; `docs/state.md` is a short status page; AGENTS.md, the root README and
`runs/README.md` match the code.

Evidence moved (untracked, local): the outside controllers of recorded trials
(ExternalHold and the flight probe) from `/tmp/wh3-benchmark-controllers/` to
`capability-probes/external-controllers/`, and the old replay-demo generator to
`reports/make-wh3-replay-demo.py`.

Validation (2026-10-15, before the commit): `uv run pytest -q` passes with 14 skips (13
need the `train`/`llm` extras' torch, one is the opt-in Windows process-ownership test);
`uv run pytest tests/twwarhammer3` passes with none skipped; `uv run ruff check .` passes;
the review workflow parses as JavaScript.

Deferred, with the reason:
- Lua cleanups, each needing one engine smoke battle, and no game could run: the
  pause-mode leftovers (constant `speed` and `awaiting_orders`, session `speed` and
  `pause`, `mailbox.require_realtime`), dead paths (the `start` control,
  `state.applied_ms`, restart's fallback before a decision, the duplicate imagery
  throttle and `shot.backend`), the always-true session switches `enabled`, `autostart`
  and `menu`, splitting `apply_order` and `mode_section`, sharing the observation code,
  and moving the file helpers into `_lib`.
- Three prompt/code contradictions for the next `llm`/`commander` version
  ([controllers.md](controllers.md#candidate-changes-for-the-next-version)): prompt bytes
  change only with a logged version and regenerated golden prompts.
- `LLMPolicy.acknowledge` keeps its fallback for acknowledgements without `index`: about
  2,900 of 25,300 acknowledgement results in `battle/` traces (30 jobs before `863d10b`)
  lack it. The owner decides.
- Single-job reports still list the 15 unrun catalogue scenarios as placeholders
  (unchanged from `d606d39`); removing them is the owner's decision.
- `play --attach` request ids restart at `r1`, so a second attach job on the same battle
  can stall until its episode timeout; a per-mailbox id prefix fixes it.
- The 49 unrounded `own_active`/`enemy_active` values already in results.csv: the register
  is append-only history, so rewriting old rows is the owner's call.
- Stale `/tmp` worktrees and merged WH3 branches: the agent had no permission to remove
  them; the owner will, with `git worktree remove /tmp/wh3-benchmark-bN` for b2, b3, b4,
  b5, b7, b8 and b9 and `git worktree remove /tmp/wh3-visual-imagery`, then
  `git branch -d wh3-benchmark-b2 wh3-benchmark-b3 wh3-benchmark-b4 wh3-benchmark-b5
  wh3-benchmark-b7 wh3-benchmark-b8 wh3-benchmark-b9 wh3-visual-final` and
  `git branch -D wh3-visual-imagery` (patch-identical to `main`'s `ca397ab` per
  `git cherry`). Whether to archive the unmerged `wh3-fire-report` and `wh3-v4-info`
  (pre-v13 candidates) is the owner's call.

## 2026-10-15: Sol visual acceptance and closer action views

The separately authorized `visual-sol-low-20261015` on `7136d6a` ran `llm_rules`
(`gpt-6-sol`, low) on `brt-cavalry-emp-assault`, unpaused at 1x with default recording and
`--stills`. It won at 382.4 s: 92 decisions, four engine refusals, 4.11 s mean information
delay, $0.6292834; ledger $7.7949 of $25. This is visual acceptance, not a resumed
calibration or an extra G1 trial. The replay has 473 frames and 168 submitted orders (167
acknowledged, one unacknowledged at the end), and embeds every prompt and reply, 14
readable names and two stills (first melee at 179.9 s, ending at 382.4 s). The opening
foreground check failed and the first rout at 208.1 s was throttled; both are kept as
such. Passive grabs took 62.6 / 32.5 ms in the separate capture process. Recorder terminal
and public-id checks passed (`visual-probes/sol-recorder-acceptance.json`). The report
keeps the new trial, the G1 triple and the interrupted launch in separate views.

Owner follow-up (2026-10-15): closer, low oblique action views, ideally before a charge,
melee or projectiles, chosen from observed public motion, within the four-still cap.
Imagery v3 takes an observed closing gap within 100 m before melee, with incoming fire or
first melee as fallbacks for the same action slot. The camera sits about 28 m above the
focus terrain with a side offset; the opening stays overhead; the 30 s throttle remains;
captions do not infer charge intent.

The scripted `visual-probes/close-imagery-20261015` on `981eb2d` ran to its planned 90 s
cutoff (truncated, no engine result): the opening at 5.9 s and the first rout at 56.6 s
were captured, requested and actual camera coordinates matched, and grabs took
74.8 / 37.2 ms. Incoming fire at 16.1 s was throttled and used up the action slot, so
`8aaabcd` keeps that trigger and defers the capture until spacing permits, aimed at the
units under fire instead of the army centroid (regression test). The recheck
`visual-probes/close-imagery-r2-20261015` on `8aaabcd` ran to its 90 s cutoff with 279
decisions, none invalid, and no model spend; its last 0.124 s deadline surfaced as a
mailbox timeout, so it stays `truncated`. The opening at 5.9 s and incoming fire at 36.8 s
were captured (39.5 / 49.0 ms; the metadata keeps the initial 16.1 s trigger) and the
first rout at 59.0 s was throttled. The low view shows the missile cavalry and the
opposing line before the first observed melee at 71.0 s; camera placement matched within
0.001 m (`visual-probes/close-camera-acceptance.json`).

Artifacts: `reports/visual-report.html` (about 1.64 MB), `reports/close-camera.html` and
`reports/close-camera.png`; older images were not reconstructed. Validation: 1119
repository tests passed, one skipped (before the timing fix); the WH3 suite 273 passed with
Lua 5.1 and the report extra; Ruff passed; offline Chromium checked both reports' images,
evidence, downloads and 390 px layout. The requested visual-report work was complete;
calibration stayed stopped.

## 2026-10-15: Native imagery probe and passive capture

`visual-probes/imagery-20261015` on `f395275` ran the scripted Khorne-Dwarf probe at
unpaused 1x to its planned 90 s wall cutoff (truncated, no engine result). The native
`common.take_screenshot` wrote a 1920×1080 TGA (8,294,418 bytes) at 6.1 battle seconds in
43.007 ms. `UnitRecordContext.Name` and `UnitDetailsContext.Name` both returned "Herald of
Khorne"; the other two candidate fields returned nil. The engine kept the camera about 100 m above
ground instead of the requested 500 m and clamped its pitch (actual position in
`visual-probe-metadata.json`); no world/pixel registration is established.

`visual-probes/passive-imagery-20261015` on `081f30f` completed its 90 s cutoff with no
invalid decisions, ten names and two stills; first contact was throttled because it came
less than 30 s after the first rout. Passive grabs took 54.34 and 42.82 ms in the capture
process (PNG writes 296.66 and 256.36 ms) while the order loop continued; `stills.json`
keeps timing and failures. A wider camera height range still clamped the view; an in-game
diagnostic at 36.2 s enabled the cinematic-camera flag and reached the requested overhead
position exactly at 36.7 s, and the passive capture at 67.1 s showed the armies (probe
code, coordinates and image beside the job). Decisions: production uses that camera flag
(no cutscene, no change to unit controls, battle unpaused at 1x) and passive Windows
Pillow capture in a background thread with job, battle and foreground-process checks;
capture errors are presentation metadata, and nothing waits between decision and order.
Only the diagnostic probe used the native call. Images stay beside the grid, not on it.
No API spend in either probe. Engine facts:
[integration.md](integration.md#visual-recording-and-presentation-probed-2026-10-15).

## 2026-10-15: Recorder acceptance and imagery candidate

Owner-requested visual acceptance, not calibration. Source `581119e` ran sequential
`rush_nearest` cavalry probes at unpaused 1x: recorder off
(`visual-probes/recorder-off-20261015-r3`) lost at 391.7 s with no refusals; recorder on
(`visual-probes/recorder-on-20261015`) lost at 263.7 s with one `unit_routing` refusal
(the lord routed before the order applied). Not a controller comparison; both rows are in
the register. The first off attempt was refused before launch by timeout validation. The
r2 attempt stalled before the frontend timer; bringing the game forward unblocked it, but
the 900 s startup deadline expired after Start Battle: an infrastructure failure with zero
episodes, not a loss.

The recorder saved 260 frames (1,564,778 bytes) including the terminal result, at
0.9-1.2 s intervals around the 1 Hz target. All 104 timestamps shared with the trace had
matching public unit ids and types; no evaluation, setup or hidden final state entered the
recorder. Sample CPU time: mean 2.851 ms, median 2.991, p90 3.998, maximum 7.019.
Battle/wall ratios over the deployed span: 0.998213 off, 0.997703 on. One pair cannot
establish a precise overhead, but the cost supports recording by default, with
`--no-record-replay` (`visual-probes/recorder-acceptance.json`,
`visual-probes/analyze_recording.py`).

The imagery candidate added `--stills`, public-position camera triggers, readable names,
capture failure metadata and WebP embedding within the report size budget; featured trials
are the earliest completed, whatever their outcome. No API spend.

## 2026-10-15: Visual replay v1 and recorder candidate

Implemented phase 1 of the visual report plan (now [reports.md](reports.md); the plan is
`visual-report-plan.md` at `d606d39`) and the opt-in 1 Hz public recorder. The report keeps
the collector summaries, embeds gzip/base64 replay evidence and adds an SVG map, timing
and resource strips, unit lanes, exact prompts, stated reasons and notes, factual events
and shared-scale trial tracks. The recorder has its own visibility memory and per-battle
files, copied after each episode including interruptions; its version and settings enter
comparison compatibility.

The original G1 Sol trace has 441 submitted orders, 436 acknowledged, 29 rejected and five
unacknowledged at battle end; it confirms the enemy general's rout, not his death. All
three G1 payloads are under 160 KB compressed; nine trials fit under 20 MiB.

Owner decisions (2026-10-14): no unit art from the game's packs; exact prompts included,
collapsed in the inspector, with the system prompt shown once per job (this replaced the
field report's rule of leaving prompts out); scripted camera moves accepted during
unattended jobs. Design figures from the first G1 Sol trial: order age median 5.1 s by the
replay's measure (5.25 s as the collector's non-empty-batch median), 90th percentile 7.2 s,
maximum 11.1 s; between consecutive decision states friendly units moved 22 m (median) and
49 m (90th percentile); 17 ability orders, notes rewritten in 29 decisions, nine decisions
without new orders; prompts and replies 855 KB raw, 44 KB compressed. Replay frames per G1
trial: 423/302/98.

Validation: 1102 repository tests passed, one skipped (with the report dependency and the
Lua 5.1 runtime); Ruff passed; offline Chromium checked replay selection, playback,
keyboard, exact counts, synthetic exports, 390 px layout and the statistics, download and
print behaviour. Artifacts: `reports/visual-report.html`, `visual-report-demo.html`,
`visual-browser/`. No new rows or spend. The owner then asked for scripted recorder off/on
and imagery probes and a later Sol low check (about $0.80), as visual-report acceptance
separate from the stopped calibration.

## 2026-10-14: Offline benchmark field report v1

Added `stats --report JOB... --report-html FILE` (since 2026-10-15 `twwarhammer3
report`), calling the collector once beside the text and JSON outputs. One HTML file
embeds the assets and compact evidence: scenario briefs, selectable and sortable
controller comparisons, SVG timing, cost and added-age charts, tactical metrics,
expandable uncertainty, failure and provenance records, image and JSON downloads, and
printing. Different model/effort groups display together only under matching scenario,
source, game, interface and timing; their summaries and pairs stay separate.

`reports/field-report.html` came from the G1 cavalry 1.0 launch and the interrupted 1.1
setup, labelled **Development pilot: one independent launch**, with the interruption kept
at zero trials. Prior JSON values were unchanged; job definitions and provenance were
added. Catalogue entries give labelled unrun placeholders, never historical briefs. The
separate `field-report-demo.html` and a committed synthetic fixture used invented Demo
controller A/B/C results, 0/6/10 s arms and missing, failure, timer and repeat cases
(replaced on 2026-10-15 by `tests/twwarhammer3/make_wh3_report_demo.py`); synthetic
evidence cannot mix with recorded evidence.

Validation: reporting regressions, the WH3 suite, Ruff, and offline Chromium checks of the
summaries, filters, sorting, keyboard controls, 390 px layout, SVG/PNG/JSON downloads,
timer and missing metrics, setup interruptions and evidence separation, with screenshots,
a chart PNG and a three-page PDF inspected (browser artifacts in
`/tmp/wh3-report-browser/`). No games, API calls, register rows or ledger entries. Page:
[reports.md](reports.md).

## 2026-10-14: Partial G1 and owner-requested stop

G1 started at 21:56:01 UTC on committed `6763d0e`, with the declared Sol low `llm_rules`
reference, the walk- and run-nearest baselines, the compact six-versus-eight cavalry
attacker (`brt-cavalry-emp-assault`) and the original rotation seeds. The first 1.0
launch, `bench-g1-cavalry-ai10-01-20261014`, completed:

| Controller | Engine result | Battle seconds | Active margin | Refusals | API USD |
|---|---|---|---|---|---|
| Walk-nearest | Lost | 411.2 | -0.79623 | 0 | 0 |
| Run-nearest | Lost | 247.7 | -0.62830 | 1 | 0 |
| Sol low | Won | 528.2 | +0.54378 | 29 | 0.793363 |

Both rematch starts matched; clock ratios 1.00091, 1.00076 and 0.99333. Sol made 96
decisions and calls, 393565 input and 30155 output tokens (164065 cached, 9917
reasoning). Its refusals were 23 unreachable moves, five targets no longer visible and one
routing unit; it carried on with the normal feedback. It circled west and north, broke the
ranged line, drew the infantry apart and disengaged before re-engaging: a useful
specialist battle and one paired win, not admission. Report `reports/g1-cavalry-ai10-01.json`;
whole job 1373.64 s, 7.86 valid battles/hour.

At the owner's request to wrap up and discuss calibration separately, SIGINT stopped the
next job, `bench-g1-cavalry-ai11-01-20261014` (modifier 1.1), during frontend setup:
`interrupted` / `KeyboardInterrupt`, zero episodes, 64.48 wall seconds. The runner stopped
at 22:19:59 UTC and the owner then cleared the goal; the other ten planned launches never
started. This is an owner interruption, not a gameplay loss or an unexplained failure, and
the queue is not to be resumed silently. Combined report `reports/g1-cavalry.json` /
`.txt`, admission audit `reports/g1-cavalry-admission.json`, queue state
`calibration/g1-cavalry-plan-state.json`, stop note `calibration/g1-owner-stop.json`:
three valid of three started battles in two launched jobs, 1438.13 wall seconds including
the interrupted setup, 7.51 valid battles/hour. No scenario admitted, G1 incomplete, G2
unstarted, held-out maps untouched. Spend $7.1656 of $25. Further difficulty and latency
experiments wait for the owner's discussion
([benchmark.md](benchmark.md#calibration-stopped-2026-10-14)).

## 2026-10-14: Benchmark harness b9 (timer classification and running baseline)

The b8 hold screen reached the timer with both armies intact. Its last finite countdown
sample was 945.679 ms remaining at 1204100 ms; the engine loss arrived at 1205200 ms,
154.321 ms past the implied deadline, with the remaining time reset to -1, so the
zero-only classifier recorded `ended_by=engine_result`. The engine loss is authoritative
and the timeout cause is inferred from its countdown; raw records are unchanged
(`reports/bench-b8-timer-classification-audit.json`).

Changes: `9f05777` samples the countdown on engine ticks, keeps its final deadline and
records its expiry apart from the engine outcome (regressions for unlimited timers,
disabled or extended countdowns and early results; replaying the recorded countdown
through the Lua helper identifies expiry). `33b7e2b` adds `rush_nearest`, AttackNearest
with the run flag. The calibration plan then took walk-nearest and run-nearest as the
cavalry attacker's tactical baselines and kept hold as its objective-failure control (an
untouched timer loss has raw margin zero); raw scoring, the 2-4/6 decisive-win criterion
and positive paired intervals against both active baselines were unchanged. After the b8
queue's evidence was committed as `4e4de1c`, b9 merged as `90a8796`. Validation: 223 WH3
tests with Lua and repository-wide Ruff.

Live on `a8fdf34`:
- `bench-b9-timer-acceptance-20261014`: hold lost at 1205.2 s with both armies intact, no
  refusals or API calls, clock ratio 0.999616. The raw countdown ends at -1, but the timer
  evidence gives deadline 1205045.875 ms and expired=true, so `ended_by=time_limit`. Whole
  job 1346.59 s, 2.67 valid trials/hour (`reports/bench-b9-timer-acceptance.json`).
- `bench-b9-assault-medium-ai10-20261014` (started 21:30:30 UTC): run-nearest's six
  initial run=true attacks were all accepted, and at 8.9 s each unit reported running,
  13.5-23.7 m from its 5.3 s start (`reports/bench-b9-rush-acceptance.json`). Run-nearest
  lost at 210.7 s (one refusal; the timer correctly unexpired, `ended_by=engine_result`).
  Luna `llm_rules` at medium effort lost at 214.4 s, margin -0.834 against the baseline's
  -0.791: matched start, 21 decisions, three routing refusals, $0.01520, clock 0.98169,
  mean issued order age 9.857 s; the halberds intercepted its direct attacks and its lord
  fought the general alone. Whole job 589.81 s, 12.21 valid trials/hour
  (`reports/bench-b9-assault-medium-ai10.json`).
- `bench-b9-assault-medium-ai11-20261014` (1.1): run-nearest lost at 256.7 s (margin
  -0.666, no refusals, clock 0.99837). Medium Luna lost at 341.7 s (-0.513): 35
  decisions, 13 refusals, matched start, clock 0.98596, 39 calls, $0.02566, mean order age
  9.339 s. It killed the general and routed the cannon and handgunners, then lost to the
  remaining halberds. Six ability refusals repeated accepted activations before readiness
  updated; three were dead targets and four routing units
  (`reports/bench-b9-luna-ability-refusals.json`, `reports/bench-b9-assault-medium-ai11.json`).
  Both screens: four valid of four started, 1354.34 wall seconds, 10.63 valid
  trials/hour, rematch starts matched. Spend $6.3723 of $25.

Decision before G1: freeze the compact cavalry attacker family and Sol low `llm_rules` as
the reference (b7's flanking win motivates it; the Luna low and medium screens did not
show competence), with walk- and run-nearest as baselines and source, prompt and rosters
fixed during calibration. Six launches per modifier on the original unused G1 seeds; if
both modifiers meet admission, G2 uses 1.1, else the passing one, else development
continues.

## 2026-10-14: Benchmark harness b8 (caster control)

Changes: `6b30737` adds the five-versus-ten caster attacker family (the defender's roster
and spellbook, only the role changes) with 1.0/1.1 settings and an untouched held-out map,
passing the declaration and setup-generation checks; the scenario recipe now also checks
objective incentives and the opponent's actual pressure. The b7 caster pilot had exposed
missing morale feedback and flight control: read-only UI queries at 793.3 and 836.2 s
reported that the flyers must attack by land, the corrected boolean query showed both
could toggle flight with no cooldown, and at 1070.9 s Kairos's largest effect was Army
losses and the fraction was -2.506; no query changed tactics or speed
(`capability-probes/benchmark-flight-toggle/`). `a0a7108` exposes friendly leadership
fraction and largest current effect plus flight availability and cooldown; both model
controllers accept `flight` orders, which the Lua checks against live state before the UI
command, and the requested state prevents reversing a completed change. The track became
`obs-v3+terrain/act-v2/live-1x` (b7 stays on its old contract). 215 WH3 tests with Lua,
Ruff and Lua 5.1 compilation passed; merged as `6a0fe53` after the b7 queue.

Live on `f179dbe`:
- `bench-b8-flight-probe-20261014` (`flight_probe:ProbeFlight`): both flyers grounded at
  7.9 s, still grounded after a repeated landing request at 8.2 s, airborne at 18.7 s once
  the cooldown expired; all six flight orders accepted. This checks completed transitions,
  not repeated requests mid-animation or every combat restriction
  (`reports/bench-b8-flight-acceptance.json`). The battle was lost at 372 s under
  AttackNearest, margin -0.486, two later refusals (dead target, routing unit), no spend,
  6.96 valid trials/hour (`reports/bench-b8-flight-probe.json`).
- `bench-b8-assault-screen-ai10-20261014` stopped at 19:56:04 UTC: attack-nearest received
  no new observation after sequence 1108 (340.7 s) for 60 s. Infrastructure failure: one
  refusal, 1108 decisions, no API calls, 545.74 wall seconds, no gameplay outcome; Luna,
  hold and the 1.1 screen unplayed. No Lua error in the mod log and no matching Windows
  application event; the cause is unresolved
  (`capability-probes/benchmark-b8-observation-stall/`,
  `reports/bench-b8-assault-screen-ai10-failure.json`).
- The retry `bench-b8-assault-screen-ai10-r2-20261014` (same implementation, scenario and
  rotation seed, no profile changes) recovered, which does not identify the stall's cause.
  Attack-nearest lost at 370 s (one refusal, margin -0.808, clock 0.9996). Luna
  `llm_rules` lost at 247 s (margin -0.589, clock 0.9976, matched start): it routed the
  cannon and both handgun units, but the lord and remaining cavalry lost to the general
  and halberdiers; 44 decisions, 12 refusals (six ability, six routing), 47 calls,
  $0.01922. All six ability refusals repeated an accepted activation on the immediate
  acknowledgement snapshot (`last_issued_ms` equal to its time while readiness still said
  true): readiness lag and repeated requests, not unsupported keys
  (`reports/bench-b8-luna-ability-refusals.json`). Hold lost at 1205 s with both armies
  intact (no refusals, matched start, clock 1.00004, raw margin 0), which exposed the timer
  label bug fixed in b9 and the limit of raw margin for idle attackers. With the failed
  first launch: 3 valid of 4 started, 2555.77 wall seconds, 4.23 valid trials/hour
  (`reports/bench-b8-assault-screen-ai10.json`, original timer label kept).
- `bench-b8-assault-screen-ai11-r2-20261014` (1.1): Luna lost at 271 s (45 decisions, 17
  refusals, margin -0.626, clock 0.9878, 49 calls, $0.02274), again routing the ranged
  units but losing to the general and halberdiers; hold lost at 1205 s with both armies
  intact (no refusals, matched start, clock 0.99992; raw label again `engine_result`, its
  countdown replicate appended to the timer audit); attack-nearest lost at 395 s (margin
  -0.868, no refusals, matched start). The queue completed at 21:05:37 UTC: 3 valid trials
  in 2055.85 wall seconds, 5.25 valid trials/hour. All cavalry screens with the failed
  attempt: 6 valid of 7 started, 4611.62 wall seconds, 4.68 valid trials/hour
  (`reports/bench-b8-assault-screen-ai11.json`, `reports/bench-b8-assault-development.json`,
  original timer labels kept beside the audit).
- The first 1.0 and 1.1 snapshots, both at 5.3 s, have all six player entries unchanged
  and all eight AI entries changed; the halberdiers' leadership 70→78, attack 26→29,
  defence 42→46, damage 28→31, charge 8→9 (`reports/bench-b8-cavalry-modifier-stats.json`):
  the applied settings, not a calibrated win rate.

No scenario admitted; ledger $6.3315.

## 2026-10-14: Benchmark harness b7 (snapshot age and cavalry attacker candidate)

Changes: `88de61a` and `2e643fe`, merged as `79d2f7d`, record the actual snapshot age
apart from the total order age, and keep start-comparison deltas plus a paired
sensitivity analysis without launches whose starts were flagged; primary results keep
every valid trial. Requested 0/6/10 s ages are minima (synchronous model calls can leave
gaps in the observation buffer); the runbook and CLI help say so. Recomputing the b4
traces keeps their primary samples and exposes the flagged cavalry launch in the secondary
comparison. `brt-cavalry-emp-assault` reverses the original foot-general candidate: the
same six cavalry units must defeat eight Empire units before the 1200 s timer, funds
capped at 8000, with 1.0/1.1 development settings and an untouched held-out map; a new
task, not pooled with the defender variants. 72 benchmark/play tests and Ruff passed after
the merge.

Sol low `llm_rules` pilots on `82f5626`:
- Caster `bench-b7-caster-sol-20261014` (`tze-caster-skv-screen`) lost at 1077 s: 281
  decisions, five refusals, margin -0.680, clock 0.9956, 282 calls, $1.78329; whole job
  1223.91 s, 2.94 valid trials/hour. It struck the artillery with spells, then withdrew and
  hid its escorts, planning a defender timeout win; after contact around 650 s the escorts
  were lost and the surviving flyers kept evading. An engine loss, not a timer ending
  (`reports/bench-b7-caster-sol.json`). Ground Pendulum was verified: accepted at 64.6 s,
  magic spent and cooldown visible at 70.9 s, while the immediate acknowledgement snapshot
  still showed pre-cast resources and readiness; exact damage attribution is not claimed.
  The b4 refused ground casts also lacked magic by acknowledgement after earlier casts
  took effect (11<16, 9<12), though their basis snapshots had enough
  (`reports/bench-b7-caster-ground-acceptance.json`,
  `reports/bench-b4-ground-refusal-resources.json`).
- Cavalry assault `bench-b7-assault-sol-20261014` (started 19:23:44 UTC) won at 432 s: 91
  decisions, one refusal, margin +0.433, mean action age 5.862 s, clock 0.9934, 92 calls,
  $0.62009; whole job 580.28 s, 6.20 valid trials/hour. Both handgun units and the cannon
  routed first; Sol then concentrated on the general while the remaining cavalry fought
  the halberdiers: a viable strategy, not admission (`reports/bench-b7-assault-sol.json`).

Both results are in the register; ledger $6.2895 of $25. Next was to screen Luna on the
same task before freezing a repeated reference, because 30 repetitions at Sol's cost would
leave almost no budget margin.

## 2026-10-14: Benchmark harness b6 (Pegasus pressure hypothesis)

`brt-cavalry-emp-pegasus` (1.0/1.1 development settings, untouched held-out map) keeps the
six-versus-eight roster and 8000 cap and replaces the enemy foot general with an Imperial
Pegasus mount. The frontend enemy-slot change and unit key passed; the Pegasus shows speed
105 and cost 1800 (a Griffon: 90 and 2050) against our cavalry's 84/92
(`capability-probes/benchmark-pressure-mounts/`). A faster flying enemy was meant to
pressure passive evasion; its AI behaviour was a hypothesis. Visible enemies now expose
walk/run speeds beside b5's flight fields, through the same queries as friendlies after
visibility filtering; the rules prompt states the facts without a strategy. 209 WH3 tests
with Lua, Ruff and Lua 5.1 compilation passed. The pilots were to try `gpt-6-sol` at low
effort as a stronger rules-only reference on the Pegasus and caster scenarios.

`bench-b6-pegasus-sol-20261014` on `1bd120b` hung after menu step 3 (opening custom
battle): Windows reported the game unresponsive while its CPU time grew, and the startup
deadline ended the job as `infrastructure_failure` after 903.87 s with zero episodes and
no model calls; the supervisor closed the game and the queue stopped
(`capability-probes/benchmark-startup-hang/`, `calibration/b6-startup-observations.jsonl`,
`reports/bench-b6-startup-failure.json`). The retry `bench-b6-pegasus-sol-r2-20261014`
(identical source and setup, no profile changes, started 18:51:24 UTC,
`calibration/b6-specialist-sol-r2-plan.json`) recovered. Its roster verified the
horse-mounted player lord and the airborne Pegasus general, with enemy speeds 10.5/10.5 m/s.
Sol moved for a flank, then chose to preserve a defender timeout win: at 385.6 s all six
friendly units were active with at least 93% health and the Pegasus was 367.7 m from the
nearest. Under the six-minute development review rule the pilot was interrupted for
inadequate pressure, not scored: 80 decisions, nine unreachable-move refusals, $0.46713,
clock 1.00004; the interrupted row is in the register (`calibration/b6-pegasus-review-rule.json`,
`calibration/b6-pegasus-retirement.json`, `reports/bench-b6-flight-speed-acceptance.json`,
`reports/bench-b6-pegasus-development.json`). The two launches used 1431.02 wall seconds
with no valid gameplay outcome; the runner stopped at 19:00:11 UTC, before the caster job.

## 2026-10-14: Benchmark harness b5 (draft while b4 screens ran)

The compact caster screen exposed missing flight information: the engine reports
Screamers as `inf_mel` despite `can_fly=true` and `is_currently_flying=true`, so the old
category rule rendered them as infantry. Flying non-commanders now take the flying
category (commanders keep their lord role), and units expose flight capability and
current airborne state, both in the initial-state comparison, without a prescribed tactic
(`dde4cfe`). A read-only query at 84.5 s verified Kairos and the Screamers airborne and
the three ground escorts not (`capability-probes/benchmark-specialist-flight/`). The b4
screen stayed on its frozen source. Timer-ended reports keep the engine's won/lost/draw
beside `time_limit`, with separate timeout-outcome counts and a "non-timer win rate"
label, so defender wins at the timer stay visible while the decisive-win criterion is
kept. Validation: 207 WH3 tests with Lua, Ruff and Lua 5.1 compilation; 25
report/setup/controller tests.

## 2026-10-14: Benchmark harness b4 (compact specialist prototypes)

Two development candidates, each with a 1.1 version and an untouched held-out map: six
Bretonnian cavalry units against eight Empire units (`brt-cavalry-emp-pikes`), and Kairos
with four escorts against ten Skaven units (`tze-caster-skv-screen`). The 8000 allowance
is a cap, not a target; both use explicit armies and default upgrades, and the cavalry
lord's Barded Warhorse is pinned. The frontend inventory verified the selectable cards and
excluded inactive DLC; the horse change returned `wh_main_brt_cha_lord_4` and Kairos
recruited with his default spellbook (`capability-probes/benchmark-specialist-rosters/`,
no battle). Scenario `mounts` maps recruitment indexes to mounted unit keys, with a lobby
read-back and a battle roster check; declared funds and settings now apply before
recruitment as well as being verified after. 69 benchmark/play tests and Ruff passed,
including refusal of a lord left on foot.

Screens on `e221324`:
- Caster `bench-b4-screen-caster-20261014`: Luna `llm_rules` lost at 963 s, hold at 613 s,
  attack-nearest at 301 s; margins -0.642/-0.771/-0.777; refusals 88/0/0; Luna $0.06841;
  whole job 2056.22 s, 5.25 valid trials/hour. Starts matched, including initial magic
  12/68; starting stats and nonzero barriers were captured. Unit-targeted spells used mana
  and entered cooldown; both unit-ground casts were refused, so that mechanic stayed
  unverified for Kairos (see b7). No reference won (`reports/bench-b4-screen-caster.json`,
  `reports/bench-b4-caster-interface-audit.json`).
- Cavalry `bench-b4-screen-cavalry-20261014`: hold lost at 415 s (margin -0.928, no
  refusals), attack-nearest at 262 s (-0.691, one refusal). That start was flagged: the
  missile cavalry displaced 4.826 m and the enemy lord turned 12 degrees in place, with
  resources, loadouts, roster and strength matching; the variation is kept for review, not
  dropped. Luna chose evasion for a timeout win; with the army untouched after several
  minutes the trial was interrupted at about 292 s to revise pressure and watchability: a
  legitimate defender strategy with **no gameplay outcome**, excluded from performance
  means, $0.01765 (`calibration/b4-cavalry-retirement.json`). Whole job 1148.78 s, two
  valid of three started, 6.27 valid trials/hour (`reports/bench-b4-screen-cavalry.json`).

A trace check measured Grail Knights at 2.01 m/s during the approach and 7.58 m/s just
before melee despite the walking setting: fast final movement, not a damage bonus
(`reports/bench-b4-cavalry-approach-check.json`). Next: a faster enemy anchor to pressure
evasive cavalry (b6).

## 2026-10-14: Benchmark harness b3 (specialist interface and `llm_rules`)

Draft commits `a9b066b` (missing-terrain gate, startup causes, whole-job throughput),
`7c71deb` (the `obs-v2+terrain` roster boundary), `6caacec` (ValueBase and Value kept
privately), `51c1796` (`llm_rules`), `2bdb0e5` (barrier and ability ranges) and `37f3ebf`
(starting resources):
- The missing terrain field seen in b2 acceptance fails setup before a controller acts.
  Unexpected startup or source errors keep their cause and are infrastructure failures;
  interruptions stay separate. Paired reports give valid trials per whole-job wall hour,
  counting setup, resets and failed jobs, or nothing when a job lacks final wall timing.
- Enemy registration could announce unseen arrivals, and an earlier sighting could reveal
  a later hidden death. `obs-v2+terrain` keeps the initial lobby roster public but adds
  later units only on sight; a death flag needs visibility. Scoring still uses private
  totals.
- The engine documentation says `CcoUnitStat.ValueBase` excludes modifiers and `Value` is
  current; startup keeps both privately. The b2 snapshots show that the AI difficulty
  bonuses already enter ValueBase (see b2).
- The owner's specialist-scenario direction exposed restrictive v15 tactical rules (stay
  in melee, cavalry wait behind infantry, all units advance together). `llm_rules` is the
  same direct controller, memory, ledger, observations, actions and timing with a separate
  rules-only prompt; `llm` stays. Rotation, prompt snapshots and hashes, model cards,
  digest and the register identify it.
- Specialist interface: current and maximum barrier HP, and owned abilities' cast range,
  effect radius and duration. A read-only probe during the 1.1 skills screen returned
  Dwarf barrier 0/0 and Rune cast ranges of 100 m with distinct durations and radii
  (`capability-probes/benchmark-specialist-interface`). Hidden enemies never enter
  unit_record.
- Starting fingerprints add friendly spell loadouts, initial strength, ammunition and
  barriers, and magic, supplies and tickets; a resource or loadout change flags a rematch
  even when positions match.

Recomputing the broken setup, the failed first b2 attempt and the retry gave 2 valid of 3
started trials in 0.38 job wall hours, 5.32 valid trials per hour
(`reports/bench-b3-report-preview.json`). An objective regression runs the Lua sampler
with ownership changes at unequal intervals: 25% held time where snapshot voting gives
40%. Validation: 1041 passed, 4 skipped in the main environment (the skipped Lua checks
passed separately); a fresh worktree passed 785 tests with 15 skips.

## 2026-10-14: Benchmark harness b2 (terrain, lobby modifier, Herald screens)

Read-only probes during b1 acceptance found the per-army AI modifier getter, stat previews
and terrain APIs. b2 sets and reads back the declared lobby modifier and checks it on
every army, and exposes coarse terrain and tested nearby destinations after an
unreachable move, without replacing the order; both model renderers receive them
(`obs-v1+terrain`), tactics otherwise unchanged. It records API wall latency, the returned
model and the optional provider processing header (WH3 only), keeps setup failures in
reports and separates partial traces from terminal failures. Herald development and
held-out candidates were declared before tuning. A frontend probe on `7c0abdb` set and
read AI modifiers 1.0/1.1 and the short 1200 s timer, which the Herald candidates declare.
Worktree checks: 1019 passed, 14 skipped; Ruff and Lua 5.1 parsing.

Setup failures, each with zero scored episodes:
- `bench-b2-terrain-20261014` (`587d501`): the enemy roster exceeded Default Funds. The
  operator copied its failed-setup dumps by hand. The funds probe
  (`capability-probes/benchmark-b2-funds`, 15:45:19 UTC) read only the Default/Custom
  options, verified custom 30000 and found that `funds_ultra` did not change the
  selection. The Herald candidates now pin custom 30000, and setup failures keep their menu
  dumps (54 relevant tests passed).
- `bench-b2-broken-setup-20261014` (`acb97f5`) refused the nonexistent card at recruitment
  step 37 and saved its map dump (hashes in
  `capability-probes/benchmark-b2-broken-setup/probe.json`).
- `bench-b2-acceptance-20261014` passed the corrected Herald setup (1.0, 1200 s, custom
  30000) and recorded both armies' starting stats, then stopped at the terrain diagnostic:
  the game lacks `math.huge`, so the grid was absent. The failed TerrainProbe trial is in
  the register; Luna was not played. The sampler now starts from its first corner (Lua 5.1
  regression). Full suite before the fix: 1033 passed, 1 skipped.

On `b476175` (the controller and queue exited at 17:15:50 UTC):
- Acceptance retry `bench-b2-acceptance-r2-20261014` (tool session 70797): at 5.5 s the
  engine refused f2's move to (-520, 130.6) and returned three tested nearby positions;
  TerrainProbe chose (-504, 130.6), which was accepted, and f2 moved 6.29 m in six seconds
  before the accepted halt (`capability-probes/benchmark-b2-controllers/navigation-proof.json`).
  It lost at 350 s (clock 1.0066). Luna (`llm` v15) lost at 442 s: its first call returned
  actual_model `gpt-6-luna` (an alias, not a pinned snapshot), provider processing
  7.280 s, call wall time 8.122 s, one transport attempt; 68 decisions, 14 refused orders,
  $0.03919. Its ability refusals were repeats during readiness lag (Whirlwind accepted at
  139.6 s, its retry refused at 145.3 s); the engine's "does not support this special
  ability" also appears in these temporary states (`reports/bench-b2-acceptance-r2.json`).
- Herald screens, one launch each. `bench-b2-screen-ai10-20261014` (started 16:17:05 UTC):
  hold lost at 448 s, skills won at 382 s, attack-nearest lost at 249 s; margins
  -0.412/+0.372/-0.710; invalid 0/0/5; whole job 1283.63 s, 8.41 valid trials/hour.
  `bench-b2-screen-ai11-20261014` (16:38:28): attack-nearest, hold and skills lost at
  242/266/265 s; margins -0.761/-0.658/-0.481; invalid 3/0/0; 967.02 s, 11.17 valid
  trials/hour. All rematch starts matched (`reports/bench-b2-screen-ai10.json`,
  `reports/bench-b2-screen-ai11.json`). Fresh snapshots at 5.2 s show the difficulty
  bonuses only in enemy stats, already in ValueBase: all 12 enemy entries change (about
  +10% melee attack and defence, weapon damage and charge, +8 leadership), all 12 player
  entries stay identical; at 1.1 the Marauders' attack went 28→31, defence 32→35, weapon
  damage 25→28, charge 6→7, leadership 60→68
  (`reports/bench-b2-starting-base-stat-comparison.json`). The first roster snapshots of
  the 1.0 screen and the acceptance retry, both at 5.2 s, had five unit positions more than
  1 m apart (up to 6.8 m): fresh launches vary.
- Objective probes (`probe_abilities`). `bench-b2-objectives-settlement-20261014`
  (16:54:35) lost at 244 s holding every point throughout, with nine accepted barricade
  builds and 204 supplies left; at its final snapshot eight built slots were destroyed and
  one still constructing, so build counts are accepted purchases, not surviving structures
  (`reports/bench-b2-settlement-objective-audit.json`).
  `bench-b2-objectives-domination-20261014` (17:00:42) lost at 776 s, tickets 0-1500, 514
  supplies left, 15 accepted purchases across nine types; the trace shows nine new
  friendly IDs and six old IDs restored from zero men, matching the purchases by type.
  Objective fields and register rows agree with the traces; the ownership-time
  reconstruction differs by at most the initial 300 ms sample gap
  (`reports/bench-b2-objective-audit.json`).

Ledger $3.3329. Owner steering then put specialist anchor-unit scenarios and faction
mechanics first ([benchmark.md](benchmark.md#scenario-design)): the unstarted Herald G1
plan was superseded, and cavalry/anti-large and caster-led candidates came before repeated
calibration.

## 2026-10-14: Benchmark harness b1 (paired trials, acceptance rotation)

Owner goal: complete paired benchmarks, difficulty and latency calibration and the
scenario interface fixes. b1 added recorded controller rotation and importable
controllers, strict benchmark setup checks, observation-age arms, private evaluation
totals excluding routing and shattered units, objective ownership integrated on game
ticks, reinforcement counts by type, trial failure and interruption accounting, and paired
reports with explicit denominators, uncertainty and missing pairs. Policies stayed `llm`
v15 and `commander` v3. Runbook: [benchmark-run.md](benchmark-run.md). Validation: 1030
tests passed, 1 skipped; Ruff; every mod script parses as Lua 5.1; the follow-up clock
and refusal edits passed 52 benchmark/play tests.

Acceptance `bench-b1-acceptance-20261014` on `5cad165` (started 14:54:39 UTC, frozen
development scenario `dwf-sla-taurox`): hold, Luna (`llm` v15), skills, attack_nearest and
the imported ExternalHold all ended on engine losses at 386, 824, 426, 262 and 386 s;
active margins -0.675, -0.002, -0.192, -0.594 and -0.675. All rematch start fingerprints
matched; clock ratios 0.9967 (hold) and 0.9985 (Luna). Luna cost $0.0594 (ledger
$3.2937); its 21 rejections were 9 unreachable moves, 7 routing units, 1 dead target and 4
spell refusals, and its later plan hid survivors for the defender's 60-minute timeout,
but Sigvald broke the remaining army first. The imported controller was
`/tmp/wh3-benchmark-controllers/external_controller.py` (sha256
`91410140291a601bab524e73a37755738d92d04b2e04339e965be00296957ea2`), now kept untracked at
`capability-probes/external-controllers/external_controller.py` beside the flight
diagnostic `flight_probe.py`. One instance verifies rotation and import, not ranking
confidence. Report: `reports/bench-b1-acceptance.json`.

Setup probe before b1: `runs/twwarhammer3/benchmark-probe-20261014` (`bench_probe.py`, run
from a clean worktree at `f2c8463`) built `dwf-sla-taurox` unattended. It selected and read
back the map ("Dread Crossing – Quest Battle"), pinned both factions, recruited all 24
cards by id and matched both rosters. Lobby read-backs: land_normal, 3600 s,
ai_level_very_hard, funds_large. Battle read-backs: IsDefender true, WillWinOnTimeout
true, UnitSize 0.75, BalanceOfPowerPercent 0.51 at 61 s. `hold` lost at 298 s (0.41 vs
0.65 men alive), and all five protected units were routing at the end. Its 965 empty
requests applied after 300 ms (954) or 600 ms (11). The protected units met melee 8.4,
13.2, 24.0, 46.2 and 47.4 s after an enemy came within 100 m. On the first rematch,
`attack_nearest` started from the same positions; the owner stopped it at 262 s.

## 2026-10-14: Battle types, llm v15 and commander v3 (overnight)

Owner goal (2026-10-14, away overnight): one minimal test scenario for each battle type
beyond the land battle (conquest, domination, free-for-all, ambush, chokepoint,
subterranean, minor settlement, siege, survival), as vertical slices toward the
benchmark. Reference: [battle-types.md](battle-types.md); engine facts in
[integration.md](integration.md#battle-types-probed-2026-10-14).

What changed (`0cf3646` to `aa5a62b` and after):
- Setup: `battle_type`, `attacker`, several or no enemy sides, reinforcing armies;
  lobby steps guarded by `when` expressions; the engine's type and the player's role
  checked at the first observation; a start click that starts nothing fails at once.
- State: the observation's `mode` (type, role, timeout winner, the game's objective
  text, capture points, tickets, gates, supplies, building slots, reinforcement pool and
  spawn zones); units of every enemy alliance and units that enter mid-battle.
- Orders: `build` (towers and barricades) and `reinforce` (pool units), both paid with
  supplies; `probe_abilities` uses both.
- Prompts (llm v15, commander v3): the Battle section, the two orders, and the
  objective rule, including the owner's siege notes (keep the victory points held,
  spend supplies).
- Three review workflows, each with reviewers per dimension and an adversarial verifier
  per finding. The first (30 findings, 24 confirmed, 10 distinct) found a validation
  crash, slot usability that always read false, shifting reinforcement ids and smaller
  defects (fixed in `c7287f4`). The second found a running mean that froze after about a
  thousand observations and a cost mismatch in the pool (`088a175`). The third found
  zone usability judged by one unit, double purchases of one pool entry and doc errors
  (`8f9d832`).
- Engine findings during the battles fixed the same night: purchased units never got
  ids, because the scan only ran with regular observations (`d62a751`); a reply invalid
  three times ended the battle (`9f08da8`); spawn zones refuse purchases (`89f3f8c`).
  A bridges field for the chokepoint (`2a0a1cd`) was removed again (`fcba267`): that
  map has no buildings, its crossings are terrain.
- Also: random draws per battle type (`9b0209f`), measures per episode (`ea646a3`,
  `7a40889`, `01e3abb`: victory points and the key building held, supplies left,
  tickets, builds and purchases) and three register columns (`ea66fef`).

Results, one battle each (per-job tables below):

| Scenario | `attack_nearest` | `probe_abilities` | Luna `llm` v15 | Luna `commander` v3 |
|---|---|---|---|---|
| conquest | won 510 s | | won 197 s | lost 403 s |
| domination | lost 742 s | lost 709 s | lost 1042 s (tickets 1156-1500) | lost 814 s |
| free-for-all | won 942 s | | policy failure; replay won 560 s | lost 909 s |
| ambush | won 173 s | | lost 699 s | truncated |
| chokepoint | won 369 s | | won 421 s | won 878 s |
| subterranean | lost 546 s | | won 391 s | won 503 s |
| minor settlement | lost 302 s | won 390 s | won 242 s | won 300 s |
| siege | won 510 s | won 430 s | won 368 s | won 450 s |
| survival | lost 198 s | lost 249 s | lost 292 s | lost 325 s |

One battle per cell separates nothing, but it shows each slice working. A siege with
the player attacking (`siege-attack-kho5-dwf5`) set up correctly but could not breach:
the gate stayed at 100% and the units idled outside the walls until the job was stopped
at 730 s; attacking needs gate and wall orders and siege equipment. LLM v15 cost
$0.32 for its ten battles; the commander $0.48.

"Strength left" is the men alive out of the initial men of every unit registered (at the
start, or when it entered), ours / the enemy's (every enemy army in the free-for-all).
Jobs before `e8eb0b6` and `d62a751` missed units that entered later. "Rejected" counts
the engine's rejections and orders refused by validation.

Smoke battles, `attack_nearest` (every unit at its nearest visible enemy, objectives ignored):

| Scenario | Job | Source | Result | Battle | Strength left | Rejected |
|---|---|---|---|---|---|---|
| conquest | `smoke-conquest-kho5-dwf5-attack_nearest-20261014-0245` | `aa5a62b` | won | 510 s | 29/197 / 78/235 | 0 |
| domination | `smoke-domination-kho5-dwf5-attack_nearest-20261014-0159` | `8b84632` | lost | 742 s | 0/197 / 207/235 | 0 |
| free-for-all | `smoke-ffa-kho5-dwf5-emp5-kho5-attack_nearest-20261014-0114` | `0cf3646` | won | 942 s | 103/197 / 36/669 | 3 |
| ambush | `smoke-ambush-kho5-dwf5-attack_nearest-20261014-0221` | `e8eb0b6` | won | 173 s | 162/197 / 117/235 | 0 |
| chokepoint | `smoke-chokepoint-kho5-dwf5-attack_nearest-20261014-0226` | `c7287f4` | won | 369 s | 72/197 / 55/235 | 5 |
| subterranean | `smoke-underground-kho5-dwf5-attack_nearest-20261014-0234` | `c7287f4` | lost | 546 s | 15/197 / 110/235 | 0 |
| minor settlement | `smoke-settlement-kho5-dwf5-attack_nearest-20261014-0214` | `e8eb0b6` | lost | 302 s | 43/197 / 121/235 | 1 |
| siege | `smoke-siege-kho5-dwf5-attack_nearest-20261014-0132` | `2dac47b` | won | 510 s | 117/197 / 82/235 | 0 |
| survival | `smoke-survival-kho5-attack_nearest-20261014-0154` | `1a5ec0c` | lost | 198 s | 38/197 / 434/448 | 1 |

- Before these, `probe-conquest-attack-20261014` (`12078dc`) played a conquest battle set
  up by hand with menu steps and was won at 331 s.
- The siege smoke had one tower built by hand mid-battle (the build-command probe), and
  the domination smoke one unit bought by hand (the purchase probe).
- The first survival job (`smoke-survival-kho5-attack_nearest-20261014-0143`) never
  started, because the lobby wants a reinforcing army; it was killed after 10 minutes.
- The free-for-all job predates the recorded `mode`; its trace shows `land_normal`.

`probe_abilities` (the `skills` executor plus abilities, builds and reinforcements) on the
four types with supplies:

| Scenario | Job | Source | Result | Battle | Strength left | Orders |
|---|---|---|---|---|---|---|
| siege | `smoke-siege-kho5-dwf5-probe_abilities-20261014-0255` | `aa5a62b` | won | 430 s | 133/197 / 109/235 | 8 towers built at 5.5 s (6000 supplies to 2000) |
| minor settlement | `smoke-settlement-kho5-dwf5-probe_abilities-20261014-0305` | `aa5a62b` | won | 390 s | 17/197 / 43/235 | 12 barricades and towers |
| domination | `smoke-domination-kho5-dwf5-probe_abilities-20261014-0313` | `aa5a62b` | lost | 709 s | 59/197 / 214/235 | 12 units bought, 7 refused at the zone; the bought units never got ids (fixed in `d62a751`) |
| survival | `smoke-survival-kho5-probe_abilities-20261014-0327` | `d62a751` | lost | 249 s | 227/611 / 1323/1405 | 6 units bought, each registered about 1 s later; 13 wave units registered as they came |

The probe won the minor settlement, which `attack_nearest` had lost, building as it went.

Luna `llm` v15 (`gpt-6-luna`, low; the source moved during the chain, each row names its revision):

| Scenario | Job | Source | Result | Battle | Strength left | Rejected | Objectives | Cost |
|---|---|---|---|---|---|---|---|---|
| conquest | `llm-luna-v15-conquest-kho5-dwf5-20261014-0453` | `89f3f8c` | won | 197 s | 162/197 / 102/235 | 4 | points held 12% | $0.014 |
| domination | `llm-luna-v15-domination-kho5-dwf5-20261014-0427` | `7a40889` | lost | 1042 s | 416/617 / 648/698 | 56 | points held 38%, supplies left 234, bought 21; tickets 1156 to the enemy's 1500 | $0.084 |
| free-for-all | `llm-luna-v15-ffa-kho5-dwf5-emp5-kho5-20261014-0335` | `ea646a3` | policy failure | | | 1 | | $0.014 |
| free-for-all | `llm-luna-v15-ffa-kho5-dwf5-emp5-kho5-20261014-0458` | `89f3f8c` | won | 560 s | 54/197 / 26/669 | 13 | | $0.039 |
| ambush | `llm-luna-v15-ambush-kho5-dwf5-20261014-0341` | `ea66fef` | lost | 699 s | 0/197 / 60/235 | 21 | | $0.042 |
| chokepoint | `llm-luna-v15-chokepoint-kho5-dwf5-20261014-0355` | `9f08da8` | won | 421 s | 75/197 / 24/235 | 28 | | $0.028 |
| subterranean | `llm-luna-v15-underground-kho5-dwf5-20261014-0404` | `088a175` | won | 391 s | 158/197 / 37/235 | 4 | | $0.026 |
| minor settlement | `llm-luna-v15-settlement-kho5-dwf5-20261014-0421` | `5cf042e` | won | 242 s | 118/197 / 94/235 | 5 | points held 100%, supplies left 796, built 5 | $0.020 |
| siege | `llm-luna-v15-siege-kho5-dwf5-20261014-0412` | `2a0a1cd` | won | 368 s | 120/197 / 69/235 | 8 | points held 100%, supplies left 2258, built 8 | $0.028 |
| survival | `llm-luna-v15-survival-kho5-20261014-0446` | `7a40889` | lost | 292 s | 450/737 / 1449/1555 | 10 | points held 20%, supplies left 2833, bought 7 | $0.024 |

- It read the Battle section and took and held capture points. In the siege it built 6
  towers in the first 30 s (6000 supplies to about 200), the last two at 74 s and 123 s;
  in the minor settlement 5 builds over the first 160 s. It called in reinforcements in
  domination (21) and survival (7) and commanded each new unit once it appeared.
- The owner's siege concern did not recur with the model: siege and minor settlement held
  every victory point throughout and were won. Survival ended with 2833 supplies unspent.
- The first free-for-all was a policy failure: the model ordered its lord's ability while
  it recharged, in three replies running, and the third invalid reply ended the battle.
  Since `9f08da8` a reply's valid orders are kept when the retries run out.
- Rejected orders: moves to unreachable points (17 each in ambush and chokepoint, across
  the river or off the forest path); purchases at zones that refuse them (34 in
  domination; zones marked since `89f3f8c` and `8f9d832`); orders to routing units; a few
  self abilities refused with "does not support this special ability".
- The first conquest job (`llm-luna-v15-conquest-kho5-dwf5-20261014-0333`) stopped before
  its battle: a merge during its lobby setup changed the source. The replay won by
  breaking the enemy, not on tickets.

Luna `commander` v3 (build and reinforce in its one-shot list):

| Scenario | Job | Source | Result | Battle | Strength left | Rejected | Objectives | Cost |
|---|---|---|---|---|---|---|---|---|
| conquest | `commander-luna-v3-conquest-kho5-dwf5-20261014-0611` | `01e3abb` | lost | 403 s | 51/197 / 100/235 | 0 | points held 38% | $0.022 |
| domination | `commander-luna-v3-domination-kho5-dwf5-20261014-0636` | `838044b` | lost | 814 s | 394/618 / 591/698 | 7 | points held 8%, supplies left 355, bought 15 | $0.058 |
| free-for-all | `commander-luna-v3-ffa-kho5-dwf5-emp5-kho5-20261014-0659` | `838044b` | lost | 909 s | 2/197 / 35/669 | 4 | | $0.052 |
| ambush | `commander-luna-v3-ambush-kho5-dwf5-20261014-0717` | `838044b` | truncated | | | 58 | | $0.183 |
| chokepoint | `commander-luna-v3-chokepoint-kho5-dwf5-20261014-0803` | `838044b` | won | 878 s | 1/197 / 73/235 | 53 | | $0.054 |
| subterranean | `commander-luna-v3-underground-kho5-dwf5-20261014-0820` | `fcba267` | won | 503 s | 34/197 / 102/235 | 17 | | $0.034 |
| minor settlement | `commander-luna-v3-settlement-kho5-dwf5-20261014-0629` | `838044b` | won | 300 s | 60/197 / 66/235 | 6 | points held 100%, key building 100%, supplies left 1060, built 5 | $0.022 |
| siege | `commander-luna-v3-siege-kho5-dwf5-20261014-0620` | `838044b` | won | 450 s | 171/197 / 19/235 | 4 | points held 100%, key building 100%, supplies left 3296, built 8 | $0.026 |
| survival | `commander-luna-v3-survival-kho5-20261014-0652` | `838044b` | lost | 325 s | 113/461 / 1515/1614 | 9 | points held 14%, supplies left 5980, bought 4 | $0.026 |

- It built 8 in the siege and 5 in the minor settlement, held the key building throughout
  both, and bought 15 units in domination and 4 in survival. Domination was lost with the
  points held 8% of the time.
- Almost every rejected order was a move to an unreachable point: 53 at the chokepoint,
  57 in the ambush, 17 underground.
- The ambush ended in a standoff, truncated by the job's 40-minute episode cap
  (`--episode-timeout 2400`): its last unit, the horsemen, stood hidden and idle against
  one enemy crossbow unit; as defender it would have won when the 60-minute battle limit
  ran out. It cost $0.18 for that reason. Types where time decides need an episode
  timeout above the battle's limit.

Siege attack: `siege-attack-kho5-dwf5` (added in `42b0c2f`), played by `probe_abilities`
in `smoke-siege-attack-kho5-dwf5-probe_abilities-20261014-0830` on `fcba267`, stopped by
hand at 730 s; the gate untouched at 100%, defenders on the walls holding every point and
all 1000 tickets, our units down to 63 of 197 men idle outside.

First four random battle-type draws, each played once by `skills` (which neither builds
nor buys; jobs `smoke-random-<type>-skills-20261014-*`), source `89f3f8c` for the siege,
`01e3abb` for the others:

| Draw | Seed | Map | Armies (units) | Result | Battle | Strength left | Objectives |
|---|---|---|---|---|---|---|---|
| `random-siege` | 632937498 | Gaean Vale (High Elves) | Chaos Dwarfs (15) defending against Dark Elves (20) | lost | 377 s | 207/734 / 400/858 | points held 100%, supplies left 9342 |
| `random-ffa` | 1161544204 | Moonlight Ridge | Daemons (10) against Lizardmen, Skaven and Slaanesh (42 in all) | lost | 1648 s | 275/403 / 46/2422 | |
| `random-survival` | 2113589463 | Endless Chaos Dwarfs | Ogre Kingdoms (14) against waves | lost | 514 s | 27/144 / 2340/3389 | points held 48%, supplies left 15449 |
| `random-domination` | 2063442117 | Toothgrass Hill | Wood Elves (6) against Lizardmen (11) | lost | 639 s | 6/327 / 1134/1262 | points held 0%, lost on tickets (0 to 1500), supplies left 10010 |

Each set up, played and ended on an engine result with no infrastructure failure. The
siege was lost with every victory point held (the army broke first). In the free-for-all
the last alliance standing was not ours although 275 of our men were alive (routing,
presumably). The spawn-zone `usable` field read true for all five domination zones.

Owner notes (2026-10-14): watching the siege smoke played by `attack_nearest`, the owner
saw the controller ignore the goal: every unit fought at the gate while enemy infantry
walked to the undefended key building, and the battle ended with more than 9,000
supplies unspent. The engine still scored it won (the enemy army broke). Both became
benchmark measures (victory points held over time, supplies left), both prompts now say
so, and the controllers can build and reinforce.

## 2026-10-13: Random-battle comparison, partial (into 2026-10-14)

Three seeds of the planned six, each played once by every controller (`9bfee82`, AI very
hard, autogenerated armies), then stopped at the owner's word to finish the engineering
first. All nine battles were lost:

| Seed: draw | `skills` | Luna `commander` v2 | Luna `llm` v14 |
|---|---|---|---|
| 2028855463: Dark Elves vs Nurgle | 434 s, 0.06 vs 0.34 | 299 s, 0.15 vs 0.56 | 618 s, 0.00 vs 0.31 |
| 1202868312: Daemons of Chaos vs Nurgle | 259 s, 0.00 vs 0.67 | 293 s, 0.00 vs 0.75 | 280 s, 0.00 vs 0.54 |
| 322117462: Dwarfs vs Slaanesh | 382 s, 0.31 vs 0.30 | 231 s, 0.43 vs 0.58 | 317 s, 0.46 vs 0.60 |

Cells show battle length and strength left (ours vs the enemy's). Costs: commander
$0.018-0.025 a battle, llm $0.025-0.040. The direct controller decided every 6-7 s
(49-89 decisions a battle).

Three paired draws separate nothing yet, and these draws at very hard (with the AI's
1.1 stats modifier) are hard for every controller. The remaining seeds are 264482191
(Ogre Kingdoms vs Slaanesh), 1355466036 (Daemons vs Greenskins) and 238913231 (Cathay
mirror). The chain script ran `play --scenario random --seed N --episodes 1` per
controller.

## 2026-10-13: Ability readiness and army abilities, llm v14 and commander v2 (`9bfee82`)

The script API has no ability cooldown getter, but the UI's context system has one
([integration.md](integration.md#ability-state-through-the-ui-context-system-probed-2026-10-13)).
Each friendly ability now carries:
- target type, magic cost and cooldown;
- `ready`, `active`, seconds of recharge left and uses left.

Army abilities, such as Khorne's three kill-unlocks, carry target, radius, unlock cost,
`unlocked` and `ready`. An `ability` order with unit `"army"` casts one. Validation
refuses an ability that is not ready, and both prompts describe the new state.

`watch` follows a job beside the game, and `play --show` puts each model reply in the
advisor window.

Engine check, `probe-abilities-random-s4` (`--policy probe_abilities`, seed 4: Khorne
(Arbaal) vs Dark Elves, autogenerated):
- The lord's and the hero's self abilities (Fight or Die, Potion of Toughness, Deadly
  Onslaught) were cast when ready and accepted. Afterwards the state showed them active
  and not ready, and the potion with 0 uses left.
- The army abilities showed locked, with costs 100/200/300.
- The battle was lost at 228 s with 31 points, so no army ability unlocked. The probe
  now runs on the `skills` executor (`46f94d0`), which earned 113 points on `kho5-dwf5`.

Second check, `probe-abilities-random-s245-20261014` (Khorne vs Skaven, seed 245):
- Horn of Khorne unlocked at 109 points and was cast at our largest unit's position at
  260 s. The engine accepted it, and its HUD timer counted 31 s active, then 90 s of
  recharge. The state now shows those phases (`739ce9c`).
- The lord's and hero's casts were accepted as before. The battle was lost at 337 s.

## 2026-10-13: Controller comparison on `kho5-dwf5`, stopped for random battles (late)

Six episodes each on the fixed Khorne vs Dwarfs battle, unpaused at 1x, AI very hard:

| Job | Source | Won | Mean battle s | Own left | Enemy left | Cost |
|---|---|---|---|---|---|---|
| `skills-v1.2-kho` | `cb12f6a` | 5/6 | 461 | 0.10 | 0.17 | $0 |
| `commander-luna-v1.2-kho` | `df390c1` | 5/6 | 329 | 0.27 | 0.33 | $0.12 |
| `llm-luna-v13-kho` (1 episode) | `df390c1` | 1/1 | 244 | 0.66 | 0.28 | $0.02 |

(Commander v1.2 is the v1 commander over executor v1.2; there was no v1.1 commander.)

- The scenario does not separate controllers: `skills`, the Luna commander and the v6
  direct controller all won 5 of 6 on it.
- Three `skills` episodes were identical (531 s, 0.10 vs 0.09 left). With a deterministic
  controller, a rematch replays the same battle, so its episodes are not independent
  samples.
- The commander's 34 engine rejections in 6 battles: 26 refused lord ability casts and 8
  unreachable moves.
- The owner asked why we were still playing small fixed battles, so the `llm` job was
  stopped after its first episode (won). The comparison moved to random draws: six
  seeds, each played once by every controller, so the draws are paired.

## 2026-10-13: Shooter re-send fix, executor v1.2 (`55ab6b3`)

Diagnosis from the Skaven trace: the four shooters spent most of their attack time moving,
with no target shown by the engine and no shots (779 such observations against 131
with shots). Many of those stretches were chases of fast chariots (Chaos Chariot,
Warwolves Chariot) kept in range for 15-42 s without a shot. The lapse rule read "no
target" as a dropped attack and re-sent it every 2 s. Two changes:
- an attack is not lapsed while the unit moves with no target and no move destination
  (closing in, finding a line of fire or evading as a skirmisher); it lapses when the
  unit is idle, shows another target, or stands without one. Replayed over the logged
  orders, this suppresses 118 of the 195 shooter re-sends;
- a shooter that fires no shot (ammunition unchanged) at a target in range for 15 s
  (30 s for artillery, whose reloads were up to about 20 s) skips that target for 30 s
  and picks another; its phase says so.

Validation, `skills-v1.2-random-a` (seed 255179936, same draw and the same
autogenerated armies): no shooter repeated an identical order more than 3 times in a row,
against stretches of up to 21 before. Orders per shooter fell from 69-102 in 415 s to
47-60 in 346 s; what remains is target switching as enemies enter and leave range.
Ammunition spent changed both ways (Night Runners 387 -> 162, Globadiers 96 -> 132,
Gutter Runners 1080 -> 880, Death Globes 146 -> 99), so one battle says nothing about
firing volume. Lost at 346 s with 0.40 of our men left against 0.70 (before: 0.35 vs
0.25 at 415 s). The draw is hard: fast Norscan cavalry and chariots against short-range
skirmishers.

## 2026-10-13: Random battles

Owner request: use the custom battle screen's Autogenerate army on random factions, and
randomize the map too. A UI probe (`runs/twwarhammer3/probe-random-army-20261013/`,
[integration.md](integration.md#frontend-automation)) found:
- the button `clear_autogen_parent/button_autogen`;
- the classic battle types' 380 maps;
- the faction list of each of 23 owned races (307 factions);
- the profile's fixed settings, including AI difficulty very hard.

`--scenario random [--seed N]` draws the map and both races from
`configs/twwarhammer3/custom_battle.json` and autogenerates both armies. The battle type
stays classic: sieges, capture points and survival need interface work first.

The first draw, `commander-luna-v1-random-s2-smoke`, was seed 2 on
`land_of_the_dead_01_04`. Dark Elves (Blessed Dread) had 13 units: a Dreadlord,
Corsairs, Executioners, Black Guard, Dark Riders, Cold One Knights, a Cold One chariot,
three Harpies, a Feral Manticore and a Reaper Bolt Thrower. Nurgle (Pallid Nurslings)
also had 13. The commander won at 407 s with 0.40 of its men left against 0.23, from 62
plans: mean plan age 6.5 s, think time 6.2 s, about 4,800 input tokens per call, $0.03.
All 9 rejections were refused lord ability casts. The trace was 5.5 MB.

A `skills` job on the same seed was stopped at the owner's word: a repeated draw shows
nothing new, and a job is one matchup. The draw also picked a faction for each side
(`5a2fc8d`), but the owner noted that a faction within a race only changes colours. The
next commit draws races only, a fresh seed per job. The mod reports the Harpies and the
Feral Manticore as infantry: its class mapping checks `can_fly` only for monsters.

Two fresh draws followed, each lost:

| Job | Draw | Outcome | Battle s | Own left | Enemy left | Notes |
|---|---|---|---|---|---|---|
| `skills-v1.1-random-a` (`900000a`) | Skaven (20 units) vs Norsca (13), `wh3_nur_wastes_01_04`, seed 255179936 | lost | 415 | 0.35 | 0.25 | 0 rejections |
| `commander-luna-v1-random-b` (`29c9325`) | Vampire Counts vs Lizardmen, `wh3_tze_wastes_02_01`, seed 369290826 | lost | 404 | 0.00 | 0.31 | 70 plans, plan age 5.6 s, $0.03 |

In the commander battle, 19 of 21 rejections were refused lord ability casts. A defect
to fix before the comparison: in the skills battle four Skaven missile units (Night
Runners, Gutter Runners, Globadiers, Death Globe Bombardiers) re-sent the same ranged
attack every 2 s for long stretches, 69-102 orders each. The engine never showed the
ordered target, probably for lack of line of sight, so the redirected-attack lapse rule
from `0f8eb39` fired on its 2-second repeat. A shooter should give up on a target the
engine keeps refusing and pick another.

## 2026-10-13: Skills and commander v1

Owner request: build the simplest design from a research summary (ChatGPT 6 Astra Pro,
2026-10-13), an asynchronous API-model commander over persistent scripted skills, and
document the other designs for later comparison
([controllers.md](controllers.md)). Code:
- `d2bf74a`: the skills executor (`--policy skills`), the commander
  (`--policy commander`), a `policy` column in the results register (rebuilt from
  `runs/`, identical except that column and blank model cells on scripted rows) and
  trace thinning for fast policies.
- `0f8eb39`: the fixes below.
- `5a2fc8d`: random battles.

The model's prompt is `configs/twwarhammer3/commander_prompt.md`; the direct controller
keeps `system_prompt.md`.

Smoke battles, one episode each on `kho5-dwf5`, unpaused at 1x, AI difficulty very hard
(found by the probe below; every earlier battle ran at it too):

| Job | Source | Outcome | Battle s | Own left | Enemy left | Plans | Mean plan age s | Cost |
|---|---|---|---|---|---|---|---|---|
| `skills-v1-kho-smoke` | `d2bf74a` | lost | 302 | 0.34 | 0.57 | | | $0 |
| `commander-luna-v1-kho-smoke` | `0f8eb39` | won | 355 | 0.53 | 0.28 | 53 | 6.5 | $0.02 |
| `commander-sol-v1-kho-smoke` (`gpt-6.1-sol`) | `0f8eb39` | won | 255 | 0.75 | 0.44 | 41 | 6.0 | $0.18 |
| `commander-astra-v1-kho-smoke` | `0f8eb39` | won | 309 | 0.64 | 0.26 | 59 | 5.1 | $1.17 |

All jobs ran at low effort. Mean order delay was 0.3 s (maximum 0.6 s) in every job,
against 4-11 s for the direct controller. The executor ran about 3 decisions a second,
and traces stayed at 1.6-2.5 MB per battle after thinning.

These battles show that the controller works, not that it is stronger: the direct
controller won 5 of 6 on this scenario at v6 and `attack_nearest` 3 of 3. The comparison
needs six or more episodes per controller
([controllers.md](controllers.md#comparing-controllers)).

- **skills v1** found a defect. The observation published with an acknowledgement still
  shows the previous target, and shoot preferred the observed target. After the enemy
  lord's melee flag flickered at 89 s, the Skullcannon alternated between two targets
  on every tick from 89 s until 185 s: 319 attack orders and no shots. `0f8eb39` makes every
  skill prefer the executor's own last target (regression test). A six-agent review
  (three reviewers, each with a verifier) confirmed eight more defects, all fixed in
  `0f8eb39`:
  - a charge whose named target is out of sight now acts as with no target;
  - without a post, charge halts the previous skill's order;
  - only an unreachable move drops its point;
  - an attack the game redirected counts as lapsed;
  - `describe_orders` no longer crashes on an ability with x but no z;
  - the prompt no longer annotates orders sent in the same tick;
  - the trace keeps the observation a failing decision saw.
- **Commander.** The first Luna plan arrived 7.2 s after its state. Meanwhile the
  default skills had the infantry engaging, the Skullcannon firing and the lord and
  horsemen waiting for melee. No assignment was ever dropped. Every engine rejection
  except two was an ability cast the engine refused ("does not support this special
  ability"): 7 for Luna, which repeated `deadly_onslaught`, and 2 each for Sol and
  Astra. Luna's other 2 were unreachable horsemen moves. The model still cannot tell ability cooldowns.
  The owner saw a Khorne army ability become available near the end of a battle and go
  unused. Army abilities are missing from the interface (state and orders) for every
  controller; this is a harness gap to fix, recorded in integration.md.
- **Latency and cost.** Sol and Astra at low effort spent only 25 and 10 reasoning
  tokens per call, against Luna's 341, so they were no slower: think time was 6.4 s
  for Luna, 5.8 s for Sol and 4.8 s for Astra. Astra's first call took 12.5 s. Total WH3
  spend after these jobs: $2.08 of the $25 ledger.

Every commander smoke call sent about 3,500 input tokens, about 2,100 of them cached.
Cost per call: about $0.0004 for Luna, $0.004 for Sol (`gpt-6.1-sol`) and $0.019 for
Astra, at the 2026-10-12 standard-tier prices per million input/cached/output tokens of
0.10/0.01/0.50, 2.00/0.10/10.00 and 10.00/1.00/50.00.

## 2026-10-13: Unpaused 1x battles only

The first diagnostic `play-smoke` used `--pause`; the owner rejected this and requires
all battles, including probes, to run unpaused at normal 1x. It remains labelled as a
paused diagnostic in local evidence and contributes no policy result. Code `1c56ec2`
removes automatic observation/order pauses from the Lua mod, sets the battle speed to
1x at deployment, and removes the CLI's pause/speed overrides. Python rejects paused
or altered-speed configurations, session writes, attached sessions and incompatible
live observations before a policy decision. The prompt and repository instructions
now explicitly require unpaused 1x. Historical results retain their recorded modes.

Validation: 95 WH3 tests and repository-wide Ruff pass, including rejection of stale
paused sessions and speed overrides. The replacement engine smoke is
`runs/twwarhammer3/skip-intro-20261013/play-smoke-realtime/`.
It reached a deployed five-versus-five battle, made 78 decisions and acknowledged
77 batches with zero invalid orders. Every decision observation reports speed 1 and
`awaiting_orders=false`; measured battle time advanced 23.4 s over 23.401 s of wall time.
The run ended at its 50-second diagnostic timeout, with no gameplay outcome measured
and no row added to the policy results register. Repeat installation preserved the
startup pack/preference bytes and mtimes. All probes are stopped, session files cleared,
and the final doctor reports ready with the startup skip installed.

## 2026-10-13: Automatic startup video skipping

Code `2793933`. `launch` and `play` install a separate auto-loaded PFH5 movie pack in
the game's `data/` directory and set `fe_game_intro_video_enabled false` in the existing
profile. The change persists for ordinary Steam launches. The pack replaces the five
startup movies and all 13 localized warning movies with twpatcher's 595-byte blank clip
(MIT attribution in `src/twwarhammer3/assets/LICENSE.twpatcher`). It leaves the main
cinematic intact for the viewer. Preparation refuses to change game files while WH3
is running, preserves all other preference bytes, and leaves matching startup files
untouched. Doctor reports the effective setting and actual/expected pack hashes;
deployment evidence includes them. No new CLI options or desktop input.

Before the skip, the frontend script loaded about 25 s after launch, but its real-time
callbacks did not run until the intro movies ended, about 2 minutes later.

Validation: 83 WH3 tests and repository-wide Ruff pass. Engine evidence is under
`runs/twwarhammer3/skip-intro-20261013/`. The baseline reached the visible Battle button
at 149.014 s; the patched launch at 17.735 s, saving 131.279 s in one comparison.
Without the project mod list, the menu is visible in the capture completed at 20.774 s,
and the game's Lua log shows no project scripts. These were direct executable launches
with Steam running; the Steam launcher UI was not exercised. The static loading splash
remains. All 18 overridden paths exist in the installed engine's `movies.pack`; the
installed 11,646-byte startup pack has SHA256
`87c3964bdbbb4d07feef70e7befcbb919753c948bff47182d78a42caa24c03f1`.
The live preference comparison changed only `true` to `false`, and attempting preparation
during the patched probe was refused before writing.

## 2026-10-13: v13, continuous decisions and expanded battle controls

Owner-requested controller change. Implementation starts at `863d10b`; final code
`6db8111`. Tactical rules remain based on v10, with command instructions updated.
The default post-application wait is 0 ms (was 5000); positive `--interval-ms` remains
an explicit pacing option. Terminal observations now record a matching acknowledgement
before ending the episode, and decision observations record `since_previous_applied_ms`.

The policy can select auto/melee/ranged attacks, queue moves and a final attack, choose
formation width, toggle supported fire-at-will/skirmish/guard/spacing/formed-attack
behaviors, and issue owned active abilities at self, friendly/visible enemy units or a
ground point. Python validation and Lua dispatch enforce the targets/capabilities.
Acknowledgements identify each order by index and distinguish queued from issued.
A rejected queued successor does not erase the preceding successful move from memory.
The prompt shows supported toggles, width, submitted queues, active ability keys,
permission and last issue times, plus the player's magic pool/reserve. Cooldowns and
uses remaining are explicitly unknown: `can_perform_special_ability` stays true after
casting. An ability/queue acknowledgement is not a completion report.

Validation: 71 WH3 tests pass; `ruff check src/twwarhammer3 tests/twwarhammer3` passes.
Real engine evidence is in `runs/twwarhammer3/capability-probes/` (ignored), with source
fingerprints, engine/pack pins, script copies, observations, requests, acknowledgements
and checks. `khorne-dwarfs-r3` verified toggles, a 20 m width, queued waypoints, ranged
fire followed by melee with 453 ammunition left, and rejection of successors to an
unreachable move. Foe Seeker raised the lord's walk/run speeds from 1.9/4.8 to 2.4/6.0.
Its 60-second Luna smoke made seven decisions, six acknowledged (zero invalid); every
next decision used the acknowledgement snapshot with 0 ms added gap. Mean think time
9.399 s, wall roundtrip 9.744 s; $0.003063. The final call ran across the episode timeout.

`wizard-r3` verified friendly Glittering Robe, enemy Plague of Rust and ground Searing
Doom orders with magic-pool decreases of 5, 4 and 6 respectively; a unit trying to use
another unit's ability was rejected. Earlier probes found the undocumented requirement
to pass a unit even for a self ability; the dispatcher now passes the caster. Spacing
and formed-attack toggles were unavailable on the tested armies and correctly omitted.
These are diagnostic battles with scripted prefixes, not comparable policy outcomes,
so they add no rows to the results register. See integration.md for the limits.

## 2026-10-13: Early findings (milestones, first night, mirror battles)

Moved from the track README on 2026-10-15. Milestones of the first day:

| Milestone | State | Evidence |
|---|---|---|
| 1 Mod loads | done | `runs/twwarhammer3/launch-m1/` |
| 1b Unattended custom battle | done | menu steps recruit both armies by double-click and start the battle; `runs/twwarhammer3/battle/*/menu.log` |
| 2 Roster readable | done | 5 v 5 units with positions, strength, fatigue, flags, targets in every observation |
| 3 Orders apply | done | attack, move (with facing) and halt through one unitcontroller per unit; acknowledgements carry the applied battle time |
| 4 Result | done | "lost" and "won" from the engine at VictoryCountdown, with both armies' true strength for evaluation |
| 5 Restart | done | rematch button and confirmation; 40 episodes in 14 jobs, none an infrastructure failure |
| 6 Scripted baselines | done | `attack_nearest`: 3 wins of 3 at about 345 s |
| 7 First LLM battles | done | v1: 1 win of 3 |
| 8 Autoresearch loop | stopped | v2 0/3, v3 3/5, v4 1/3 (1/3 paused), v5 4/6, v6 5/6, v7 2/6 (reverted); v8-v11 on mirror battles, no mirror win yet with guns |
| 9 Several scenarios | done | `configs/twwarhammer3/scenarios.json`: each side's race picked in the selector's popup; Khorne, Dwarf and Empire mirrors |

What the first night showed:
- The model can command a real-time battle through the mod: about one decision per 10 s
  of battle time, orders applied about 5 s after the state it saw, no invalid replies,
  about $0.01 per battle.
- The fixed script that sends every unit at its nearest enemy, walking, wins this battle
  every time. The model's early losses came from what it added: passivity (v1), retreats
  out of melee (v2), running everywhere and arriving tired, pairing its units off one to
  one, and above all leaving its lord to duel the enemy lord alone, or parking him while
  the enemy lord was nearly dead.
- Latency is not the gap: pausing the battle while the model thinks (orders applied 0.6 s
  after the state instead of 5.5 s) gave the same 1 of 3 for v4.
- The state must say what the game did with an order: the game retargets units on its
  own, and showing its choice as the model's order made the model believe plans were
  running that were not (v6 fixed this; 5 wins of 6).
- Still weak in every version: the Skullcannon and the missile horsemen. An attack order
  only makes a unit with ammunition shoot, and their fire killed almost nothing.

What the mirror battles showed (same army on both sides of the same map, player starting
north; 9 to 12 battles per mirror; wins and mean true strength left, ours/enemy, from
`python -m twwarhammer3 stats`):

| Version | Empire (guns, cannon, knights) | Dwarfs (crossbows, catapult) | Khorne (melee) |
|---|---|---|---|
| attack_nearest | 0/2, 26/82% | | |
| v6 | 0/3, 21/69% | 0/3, 25/53% | 2/3, 34/25%; replicate 0/3, 38/64% |
| v8 guns | 0/3, 31/70% | 0/2, 30/76% | |
| v9 melee | | 0/3, 35/65% | 1/3, 26/47% |
| v10 shooters | 0/3, 37/57% | 0/3, 42/68% | 0/3, 19/58% |
| v11 lords (reverted) | 0/3, 34/76% | | 0/3, 26/61% |
| v12 v6 + v10 fire (reverted) | | | 0/3, 16/55% |

- With guns, crossbows or artillery on both sides, Luna lost every battle (0 of 11 in the
  Empire mirror, 0 of 11 in the Dwarf mirror), and so did `attack_nearest` (Empire, 0 of
  2): the AI's missile units and artillery shot our units while they fought, and its
  missile infantry ended untouched (66-67 of 68 handgunners, 52-58 of 60 quarrellers).
- The profile's AI stats modifier was 1.1, so the AI's units are probably about 10%
  stronger and a mirror is not an even fight. The owner later authorized testing 1.0 and
  1.1 during benchmark calibration.
- Harness gaps found: enemy units' targets never reached the state (llm.py rendered a
  field the mod never sent), no record of what a fire order killed, an attack order
  replaces a move (a shooter walks straight at a target out of range), and units with
  ammunition could not be sent into melee. The decision delay grew from about 6 s to
  7-10 s as the prompt grew.

## 2026-10-13: v12, v6's melee rules with v10's fire rules

Change (prompt): v6's prompt with only v10's two fire bullets (shooters hit infantry in
the open until contact; artillery then fires at missile units, then artillery; missile
units never trade fire with enemy missile infantry; a shooter moves before it attacks).
v8's cavalry rules and v9's and v11's lord rules are left out. The mirrors split the
versions (v6 best in the Khorne mirror, v10 in the Empire mirror), and v10's fire rules
are the change with the clearest measured basis.

Job `llm-luna-v12-kho-20261013` (source `42a8af7`): lost at 225 s (11% against 59%), 271 s
(19% against 52%) and 265 s (19% against 54%).

The scenarios were less fixed than intended. Picking a race leaves the faction within it
to the game, and it varied between jobs on both sides: Khorne jobs played Khorne against
Arbaal's faction or Crimson Skull against Khorne (v12's enemy also deployed elsewhere),
Empire jobs Wissenland, Empire or Golden Order, Dwarf jobs Dwarfs, Karak Kadrin or the
Ancestral Throng. Every comparison between versions above carries that variation (the
first v6 Khorne job, 2 wins of 3, is the only one with wins and played Khorne against
Arbaal, as did v9-v11's). The next fix pins each side's faction in the scenario.

v12 was reverted (`main` runs v10) and the scenario steps now pin each side's faction
(`61c5f7f`). First battle with pinned factions, Khorne against Khorne, v10
(`llm-luna-v10-kho-pinned-20261013`, stopped after it at the owner's return): lost at
248 s (32% against 52%). The enemy deployed at about (-23, -295), as in v12's job, not at
(-148, -267) as with Arbaal's faction. Results before `61c5f7f` mix factions; versions
should be compared again with pinned factions.

## 2026-10-13: v11, the lords never fight alone

Change (prompt, net shorter), chosen by the review of v10's Empire losses and v9's fast
Khorne loss (all three judges): the lord bullet becomes one rule. Whenever the enemy
lord is within 20 m of ours or fights any of our units, at least the nearest melee unit
that is not cavalry must target him, even out of another melee, until he breaks; our
lord attacks only an enemy another unit is on, never arrives first, and stays in melee
once there. Gone: v9's 5-point condition (read literally, it forbade help in a losing
duel, since our own lord counts as a unit on him), the 35% hurt-lord clause and "he is
your best fighter", which is untrue against the AI's 1.1 stats modifier. The reviewers
measured our lord, alone against the enemy lord, losing health 3 to 8 times faster than
he did; he was the first unit to rout in the v10 Empire losses.

Job `llm-luna-v11-kho-20261013` (source `1eb75aa`): lost at 246 s (27% against 46%), 232 s
(28% against 63%) and 198 s (22% against 74%).

To check whether v8-v11 cost the Khorne mirror, v6 was replayed there from a worktree at
`6777a64` (same ledger and results file): `llm-luna-v6-kho-20261013b` lost at 214 s (44%
against 77%), 227 s (37% against 50%) and 185 s (34% against 65%). v6 in the Khorne
mirror: 2 wins of 6; v9 1 of 3, v11 0 of 3. The first v6 job's two wins look like luck
more than a better prompt; the newer prompts are not shown to be worse there.

Job `llm-luna-v11-emp-20261013`: lost at 160 s (39% against 79%), 249 s (20% against
77%) and 189 s (42% against 73%). v11 in all: 0 of 6, and the Empire margin went back to
-42 points from v10's -20, so v11 was reverted: `main` runs v10.

Job `llm-luna-v10-kho-20261013` (source `9c8f995`, the v10 prompt): lost at 298 s (25%
against 37%), 211 s (15% against 68%) and 194 s (18% against 70%).

Where the mirrors stand at the end of the session (mean strength left, ours minus the
enemy's, in points): v6 Empire -48, Dwarfs -28, Khorne -8 (2 wins of 6); v10 Empire -20,
Dwarfs -26, Khorne -39 (no win in 9). v8-v10 traded the melee mirror for the gun mirrors;
`main` keeps v10, and v6's prompt is at `6777a64` for comparison. Spend for the session
about $0.25 (ledger total $0.68).

## 2026-10-13: v10, shooters hit infantry in the open

Change (prompt), chosen by the review of two v9 Dwarf and two v8 Empire losses (all three
judges): the reviewers measured, over the gun mirrors, artillery killing about 2 men a
shot at infantry in the open, 1 in 2 shots at missile infantry and 1 in 3 at crews, and
missile units killing about 1 man per 100 shots at enemy missile infantry. So until the
enemy infantry reaches our line every shooter fires at it; after that artillery fires at
the enemy's missile units, then its artillery (replacing v8's counter-battery first); a
missile unit never trades fire with enemy missile infantry and shoots infantry not in
melee, or from 40-60 m to the side of a fight; a shooter moves to its spot before the
attack (an attack replaces a move and walks a shooter straight at a target out of
range: about 20 such orders cut a shooter's own move in 14 gun-mirror battles).

Job `llm-luna-v10-emp-20261013` (source `ffbc953`): lost at 237 s (37% against 71%), 296 s
(22% against 38%: the enemy's lowest yet in this mirror) and 254 s (51% against 63%).
Still no Empire win, but the margin has narrowed with each version: mean strength left,
ours against the enemy's, v6 21/69%, v8 31/70%, v10 37/57%.

Job `llm-luna-v10-dwf-20261013`: lost at 432 s (47% against 63%), 574 s (35% against 66%)
and 394 s (44% against 75%); mean 42/68%, against v9's 35/65% and v6's 25/53%.

## 2026-10-13: v9, fight the enemy holding you

Change (prompt), chosen by the review of the v6 Dwarf mirror losses and the Khorne
mirror loss (all three judges): after contact, a unit the game moved onto another enemy
stays on it; the enemy-lord rule sends units back to him only while he lost 5 or more
health since the last turn or none of ours is on him; no unit leaves a wavering enemy.
The reviewers counted 11-15 pulls onto the enemy lord per Dwarf battle while he stood
inside his own infantry, losing about 1.4 points a turn, and the enemy holding each
pulled unit hit its flank (f3 Longbeards 68→48 men against e3's 75→71 in one loss).

Job `llm-luna-v9-dwf-20261013` (source `d928965`): lost at 554 s (27% against 59%), 696 s
(33% against 49%) and 332 s (45% against 86%). Job `llm-luna-v9-kho-20261013`: lost at
205 s (25% against 70%), won at 218 s (35% against 36%), lost at 297 s (17% against 36%).
In the Khorne mirror v9 (with v8 under it) did worse than v6 (2 of 3, 34% against 25% on
average), and the mean delay rose from 7.2 s to 9.6 s as the prompt grew; which of v8 or
v9 cost the Khorne battles is not separated.

## 2026-10-13: v8, answer the enemy's guns

Change (prompt), chosen by the review of the Empire mirror (all three judges): artillery
fires first at enemy artillery in range ("never at small crews" had made the model take
the cannon off the enemy cannon, the game's own pick, at 5 s in all three battles);
missile infantry stands 40-60 m to the side of the melee line, never straight behind it
(the handgunners fired 167 rounds through our own melee for 2 kills); a shooter whose
target loses no men for two turns moves to a clear line or switches; cavalry shelled
while waiting ride wide onto the enemy artillery instead of shuffling about in its range;
cavalry are left out of the enemy-lord gang-up.

Job `llm-luna-v8-emp-20261013` (source `fbcdf99`): lost at 321 s (25% against 69%), 203 s
(30% against 83%) and 343 s (38% against 57%). The enemy cannon was hit hard each time
(7, 33 and 15 of 33 crew left, against 33 of 33 under v6) and our side kept more (25-38%
against v6's 8-37%), but the enemy handgunners still ended untouched (66-67 of 68).

Job `llm-luna-v8-dwf-20261013` (source `3879027`, stopped after two battles when v9 was
merged): lost at 487 s (33% against 77%) and 605 s (26% against 75%). The enemy Grudge
Thrower broke under counter-battery fire, but the enemy infantry kept more than under v6
(43-66%): shells that went at the enemy artillery no longer thinned its infantry, and the
melee was lost as before.

## 2026-10-13: Mirror battles (second session)

Scenarios are now named in `configs/twwarhammer3/scenarios.json` (each side's race,
faction and units; the menu steps pick the race in the selector's popup). Mirror battles
put the same army on both sides of the same map, the player starting north:
`kho5-kho5` (the Khorne army above), `dwf5-dwf5` (the Dwarf army above) and `emp5-emp5`
(Empire: General, Swordsmen, Handgunners, Empire Knights, Great Cannon).

Empire mirror, source `b1c9ce0`:
- `attack_nearest` (`attack-emp-mirror-20261013`): lost at 228 s and 232 s.
- v6 (`llm-luna-v6-emp-20261013`): lost at 270 s (8% against 71%), 242 s (19% against
  71%) and 246 s (37% against 65%). In every loss the enemy handgunners and cannon ended
  nearly untouched (64-66 of 68 men, 33 of 33) while ours were destroyed.

Khorne and Dwarf mirrors, v6, source `6777a64`:
- `llm-luna-v6-kho-20261013`: won at 265 s (39% against 17%), lost at 282 s (25% against
  33%), won at 247 s (37% against 25%).
- `llm-luna-v6-dwf-20261013`: lost at 499 s (31% against 66%), 576 s (24% against 50%) and
  629 s (20% against 43%).

v6 in the mirrors: 2 wins of 9, both in the melee-heavy Khorne mirror. The armies with
guns, crossbows and artillery beat the model every time.

## 2026-10-13: v7, the enemy lord only while he is losing the lords' race

Change (prompt): v4's always-on "every melee unit within 40 m attacks the enemy lord" is
gone. After contact the enemy lord stays the focus only while his health is below our
lord's or fell 5 points or more since the last turn; otherwise units leave melee targets
on the game's choice and switch to the nearby enemy closest to breaking.

Job `llm-luna-v7-20261013` (source `42d3054`): won at 451 s (10% against 27%), lost at
334 s (30% against 17%: our army broke with more men left than the enemy's), won at 376 s
(32% against 35%).

Replicate `llm-luna-v7-20261013b`: lost at 256 s (35% against 64%), lost at 278 s (32%
against 70%), lost at 434 s (22% against 29%). v7 in all: 2 wins of 6, against v6's 5 of
6, so v7 was reverted: `main` runs the v6 prompt. Without the standing order to pile onto
the enemy lord, the replicate's battles were lost fast; the race test seems to have taken
units off him too early. The next version starts again from v6.

## 2026-10-13: v6, show what each unit is really doing

Change (state rendering, `llm.py`, with the prompt's description of it): each friendly
target is marked as the ordered one ("target e1 3 m (your order, 95 s)") or the game's
choice with the order it replaced; a move the game dropped reads "stopped N m short of
your move"; a unit with no target or destination reads "no order" and shows its nearest
visible enemy; men and health show the change since the previous decision for both sides;
orders are forgotten once the game no longer carries them out. In the same merge, fixes
from a review of this session's code (not visible to the model in this scenario): flying
monsters labelled flying again, the restart fallback only before a decision, battle UI
probes through `menu.json`, `stats` grouping scripted rows by source revision.

Job `llm-luna-v6-20261013` (source `ac3c0bd`): won at 357 s (26% against 34%), won at
496 s (8% against 24%), lost at 428 s (12% against 38%).

Reviews: the new lines were used. The model put units back on the enemy lord after the
game had moved them ("game's choice") 6-8 times per episode, and the horsemen's attack
orders were no longer replaced over and over. But the always-on gang-up then misfired:
in the loss the Bloodletters and Chaos Warriors stood "on" the enemy lord for 80 s while
his health fell about 1 point a turn (he stood inside his own infantry), and the Dwarf
Warriors wavered untouched beside them; the Herald was sent back at him 24-26 points
behind. Support fire stayed useless (14 Skullcannon shots and 270 axes for about 2 kills
in the first win); the hurt-lord rule parked the Herald for most of two battles.

Replicate `llm-luna-v6-20261013b`: won at 462 s (16% against 34%), won at 381 s (51%
against 18%), won at 374 s (56% against 19%: the widest margins of any battle so far,
the baseline included). v6 in all: 5 wins of 6.

## 2026-10-13: v5, a hurt lord keeps fighting

Change (prompt): below 35% health the lord stays out of melee only while a healthier
enemy lord or hero is near, and goes back in as soon as that enemy has less health than
he has (v4 parked him for minutes while the enemy lord was nearly dead).

Job `llm-luna-v5-20261013` (source `33895de`): won at 333 s (64% of our men left, 29% of
the enemy's: a wider margin than any baseline battle), won at 343 s (36% against 36%),
lost at 417 s (10% against 48%).

Reviews: the wins came from the lord and both infantry units walking in together and
all three going onto the enemy lord in the same reply at contact (he routed at 162 s in
the first win, our lord at 58%); the hurt-lord rule mattered in the second win (the
Herald fought on at 42% once the lords' health was level). The loss turned on the lord
duel: the Herald's line move carried him past the engaged Chaos Warriors, he alone was
sent onto the enemy lord, and when the game retargeted him and the Bloodletters onto
other enemies the model read it as its own gang-up, leaving the enemy lord untouched at
80% for 90 s. The support units achieved little in all three: the Skullcannon's 12 shots
killed almost no one and the horsemen's attacks on the Quarrellers were replaced by the
game 7 times, each acknowledged as applied.

Replicate `llm-luna-v5-20261013b`: won at 333 s, won at 418 s, lost at 329 s (32% against
54%). v5 in all: 4 wins of 6.

## 2026-10-13: v4, one body, gang up on the enemy lord

Change (prompt): the lord and the melee units advance side by side at a walk; two or
three units on one enemy, the enemy lord first at contact; every melee unit within 40 m
attacks the enemy lord when he engages; our lord attacks only targets another unit is on
and parks 30-50 m behind the line below 35% health. From the v3 reviews: the Herald fought
the enemy lord with no other melee unit on him in all 28 such turns (the baseline had help
in 20 of 22), and the model paired its units off one to one.

Job `llm-luna-v4-20261013` (source `0547bfb`): lost at 603 s (9% of our men left, 32% of
the enemy's), lost at 488 s (7% against 40%), won at 355 s (44% against 39%, the closest
an LLM battle has come to the baseline's 45% against 33%). The model followed the
doctrine: it walked on 55 of 76 moves and attacks (v3: 34 of 140), met the enemy at 95 s
like the baseline (v3: 55-79 s) and helped its lord in 12 of 14 duel turns.

Reviews: in both losses the Herald was parked at 20-23% health for 18 and 23 straight
decisions while the enemy lord fell to 12-2% and the model itself called him "nearly
defeated" (v4's "bring him back only to finish a routing or nearly dead enemy" had no
threshold); in the win the enemy lord routed at about 160 s, earlier than in the
baseline. The support units still did little: the Skullcannon fired its 12 shots for at
most 3 kills, and the horsemen, ordered at the Quarrellers through the melee, stalled
behind it and routed, throwing 6-26 axes where the baseline's threw about 170 into the
Dwarf Warriors before contact. Moves to flank were acknowledged but the unit barely moved.

Pause-mode ablation, job `llm-luna-v4-pause-20261013` (same source, `--pause`: the battle
stops while the model thinks; orders apply 0.6 s of battle time after the state seen,
against 5.5 s in real time): lost at 232 s (37% against 71%), lost at 579 s (8% against
34%), won at 434 s (39% against 26%). One win of three, as in real time: the model's
latency is not what separates it from the baseline.

## 2026-10-13: v3, commit and focus (best so far)

Change (prompt): v2's withdrawal triggers replaced by a commit-and-focus doctrine: keep
units in melee and send help into the enemy's flank instead; focus the enemy closest to
breaking and the enemy lord; the lord leaves melee only below 35% health; spent missile
units fight in melee; cavalry wait until the lines lock; "back" means toward our start.

Job `llm-luna-v3-20261013` (source `2681d04`): lost at 303 s (38% of our men left, 49%
of the enemy's), won at 419 s (11% against 18%), won at 392 s (28% against 24%); mean
delay 4.5 s, think time back to v1's level.

Replicate `llm-luna-v3-20261013b`: lost at 257 s, won at 345 s. v3 in all: 3 wins of 5.

Reviews: the Herald fought the enemy lord with no other melee unit on him in all 28 such
turns (the baseline had help in 20 of 22 and its Herald survives); the model paired its
units off one to one at contact ("f1 e1, f2 e2, f3 e3", from "strongest against
strongest"); the game's automatic target is shown as if it were the order, so a unit
the game had retargeted looked busy; units with ammunition shoot when ordered to attack,
so the horsemen and the Skullcannon could not charge.

Across all episodes so far, the model orders `run` on about 90% of its moves and attacks
(v1: 62 of 67; v2: 296 of 324), while `attack_nearest` never runs; the baseline's units
always reach their first melee fresh, the model's often tired or exhausted.

## 2026-10-13: v2, a battle doctrine (worse)

Change (prompt): check every unit each turn and pull back units that waver, lose men
faster than their target, or are under fire with nothing to hit; pull the lord back
below 40% health; switch fire targets that lose no men; keep missile cavalry out of
enemy missile range; charge only once the lines are locked. State fixes in the same
version: "running" only while moving, a unit's class fixed at the start, enemy missile
range shown, dead units on one line, moves to unreachable points rejected.

Job `llm-luna-v2-20261013` (source `f807f64`): lost at 569 s (none of our men left,
77% of the enemy's), lost at 614 s (2% against 45%) and lost at 1226 s (10% against 20%,
66 rejected orders). The model turned "pull back"
into a slow general withdrawal: units left melee (which costs men and morale in Total
War) and the army drifted to the map corner, where about 25 moves per episode were
rejected as unreachable. Think time doubled to about 8 s with the longer prompt.
Reviews (two episodes): moves ordered to units in melee went from none in v1 to 14 and
10; after the withdrawals began the enemy lost almost no men; the lord flip-flopped
between committing and withdrawing over a 3-point health gap, and lost 42% health while
disengaging.

## 2026-10-13: Baseline after the lapse fix

`attack_nearest`, source `7b31ce9`, job `attack-b2-20261013`: won 3 of 3 at 346, 344 and
346 s, with 45% of our men left against 33% of the enemy's. A fixed policy gives nearly
the same battle every time; the model's variance comes from its own orders.

## 2026-10-13: v1, first LLM battles

Source `b615830`, job `llm-luna-v1-20261013`, `gpt-6-luna` low effort: won at 446 s,
lost at 503 s, lost at 366 s; 132 decisions, no invalid orders, mean delay 4.0 s between
the state seen and the orders applied (think time 3-6 s), $0.035 in all.

Reviews (one subagent per episode, `wh3-version-review` workflow): the Herald died in all
three episodes, each time sent into a fight at 21-38% health (twice at the enemy lord);
the Skullcannon spent all 36 of its shots across the episodes on the Grudge Thrower crew
and never killed one; the Marauder Horsemen were committed before the lines met and lost
missile duels to the Quarrellers; 83 of 132 replies gave no orders ("all units have
active orders", from the prompt's "leave out units that are carrying out your orders"),
including minutes when the lord bled out; "back toward the army" moves went to the
enemy side of the melee (no sense of the front). Misleading state: "running" on standing
units, the Skullcannon's class flipping with its ammunition, dead units listed with stale
flags, no enemy missile range, moves to unreachable points acknowledged as applied.

## 2026-10-13: First baseline

`attack_nearest` (every unit attacks its nearest visible enemy), source `60314c3`, job
`attack-m3-20261013`: lost at 344 s, won at 400 s. Before `c3c9177` the baseline did not
re-order units whose attack had lapsed, so units stood idle under fire for minutes; the
two episodes understate it.
