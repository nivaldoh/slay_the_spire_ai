# Project state

Updated 2026-10-15 01:40 UTC: what is running, where each game
stands and what comes next. History: [WH3 log](twwarhammer3/log.md),
[Spire full-run log](spire/fullrun/log.md), [first combat](spire/first-combat/README.md).

## Active work

WH3 [visual report redesign plan](twwarhammer3/visual-report-plan.md) implementation
is active. The offline replay and opt-in recorder are implemented; 1102 repository
tests pass (one skip), including Lua 5.1, and the offline browser checks pass.
The owner requested the scripted recorder off/on and imagery probes, followed
by the Sol low check (about $0.80). Both short imagery probes have stopped at their
planned 90 s cutoffs. Passive capture passed: two stills, one explicit throttle,
ten readable names, no invalid decisions. The cinematic-camera diagnostic reached
the requested overhead position exactly. The camera fix is ready for Sol acceptance.
No game is currently running. Latest WH3 tests: 266 passed; Ruff passed.
The recorder off/on probes are complete. Off lost at 391.7 s with no refusals; on lost at 263.7 s with one
`unit_routing` refusal. The recorder audit passed: 260 public frames including the
terminal result, 2.851 ms mean CPU/sample, clock ratios 0.998213 off / 0.997703 on.
Evidence: `runs/twwarhammer3/visual-probes/recorder-acceptance.json`.
The earlier r2 startup failure is retained with zero episodes and no API spend.
The imagery candidate is merged. Next: inspect the native camera/name/capture probe,
then run the authorized Sol low check. Calibration stays stopped.
Calibration remains stopped. Artifacts: `runs/twwarhammer3/reports/visual-report.html` and the synthetic
`visual-report-demo.html`.
Owner decisions: no unit art, exact prompts included but collapsed, and camera moves
during jobs accepted.

WH3 [offline field report](twwarhammer3/field-report.md) implementation is complete.
Generated `runs/twwarhammer3/reports/field-report.html` from the saved cavalry jobs;
`field-report-demo.html` is a separate, explicitly synthetic demonstration. The exporter
preserves statistical groups and adds local charts, data/image downloads and printing.
No new battles or model calls; calibration remains stopped.

WH3 benchmark work stopped at the owner's request on 2026-10-14 at 22:19:59 UTC.
The owner cleared the goal and wants to discuss difficulty calibration separately.
**Do not resume calibration automatically.** Its controller and runner exited. Only the
separately requested visual-report acceptance probes above may run.

The engineering and live acceptance work is preserved on `main`: paired rotations,
external controllers, setup checks, uncertainty/failure reports, terrain, specialist
controls, objective metrics, timer classification and the run-nearest baseline.
b9 passed 223 WH3 tests with Lua, Ruff and Lua 5.1 parsing. The specialist recipe
prioritizes anchor units, faction mechanics and compact forces; the current cavalry
candidate is six versus eight, and the caster candidate five versus ten. All held-out
maps remain untouched. No scenario is admitted; G1 is incomplete and G2 has not run.

The first G1 paired launch on frozen source `6763d0e` completed at AI modifier 1.0:

- Walk-nearest lost at 411.2 s, active margin -0.796, no refusals.
- Run-nearest lost at 247.7 s, margin -0.628, one refusal.
- Sol low `llm_rules` won at 528.2 s, margin +0.544, $0.79336. It circled the defense,
  routed the ranged line, separated infantry and disengaged/repositioned the cavalry.
  Both rematch starts matched. One paired launch cannot establish admission or uncertainty.

The following 1.1 launch was interrupted during frontend setup at the owner's request:
zero episodes started, no gameplay outcome, 64.48 job-wall seconds. Preserve this as
an owner interruption, not a tactical loss or unexplained infrastructure failure.
The remaining ten planned launches were never started. Queue state:
`runs/twwarhammer3/calibration/g1-cavalry-plan-state.json`; stop note:
`runs/twwarhammer3/calibration/g1-owner-stop.json`. Partial reports:
`runs/twwarhammer3/reports/g1-cavalry.json`, `g1-cavalry.txt` and
`g1-cavalry-admission.json`. Three valid / three started battles across two launched
jobs, 1438.13 wall seconds including interrupted setup, 7.51 valid battles/hour.

Earlier b9 screens: Luna medium lost both modifiers; run-nearest also lost both.
At 1.1 Luna killed the general and routed the ranged line but lost to the halberds.
The idle-attacker timer check correctly recorded an engine loss at 1205.2 s as
`time_limit`, with retained countdown expiry evidence. Running movement was verified
after accepted attacks. Full evidence and earlier failed/retired candidates remain in
[the log](twwarhammer3/log.md); sources are not pooled. WH3 API spend is **$7.1656
of the cumulative $25 cap**. Never reset the ledger.

Before further experiments, discuss the calibration objective, reference, thresholds,
trial count and cost with the owner. The recorded plan used Sol low against walking
and running baselines, six launches per modifier, then six launches rotating added
snapshot ages 0/6/10 s. That work is unfinished, not automatically queued for resumption.
The code, compact scenario candidates and historical design remain available for review.

When a job starts, note here its game, job directory, start time (`date -u`) and `watch`
command; clear it when the job stops.

## Total War: WARHAMMER III battles

[README](twwarhammer3/README.md) (track page, full [Next](twwarhammer3/README.md#next)),
[battle types](twwarhammer3/battle-types.md), [controllers](twwarhammer3/controllers.md),
[integration](twwarhammer3/integration.md), [log](twwarhammer3/log.md). `main` runs
`llm` v15 and `commander` v3 (every battle type's objectives, `build` and `reinforce`
orders) and the `skills` executor v1.2. API spend: $7.1656 of the $25 cap
(after the first G1 Sol trial).
The stopped calibration was authorized to test AI modifiers 1.0 and 1.1.
Both lobby and battle read-backs passed. Fresh 5.2 s startup snapshots show all 12 AI
unit entries changing at 1.1 (roughly +10% attack/defence/damage/charge, +8 leadership),
with the 12 player entries unchanged. These differences appear even in UI ValueBase;
b3 also captures current Value to distinguish other active effects. See the progress page.

2026-10-14 overnight (owner goal: one minimal test scenario per battle type, vertical
slices toward the benchmark): done for all nine types (conquest, domination,
free-for-all, ambush, chokepoint, subterranean, minor settlement, siege, survival).
Each sets up unattended, reports its objectives in the state (`mode`), has the orders
it needs and ended on an engine result with `attack_nearest`, Luna `llm` v15 and Luna
`commander` v3; `probe_abilities` verified building and buying in the engine. Results
and gaps: [battle-types.md](twwarhammer3/battle-types.md); engine facts:
[integration.md](twwarhammer3/integration.md#battle-types-probed-2026-10-14).

The owner cleared the benchmark goal on 2026-10-14 at 22:20 UTC. Its engineering
work is preserved; difficulty and latency calibration remain incomplete and await a
separate discussion. Remaining longer-term directions:
1. Battle types toward benchmarks ([battle-types.md](twwarhammer3/battle-types.md#next)):
   variants per type (the `random-<type>` draws, both roles), calibration of the
   scripted controllers per type, and remaining interface gaps (deployment control, finer terrain detail and
   survival wave timing).
2. Resume the random-draw model comparison later (three seeds left, in the
   [log](twwarhammer3/log.md)), then Sol and Astra as commander on the same draws.
3. Eventually we could turn this game into some kind of serious LLM benchmark? For now I'm just registering this here. Could try to create certain challenge scenario battles where the opponent side is stronger, and see how well different models perform and whether they discover certain key insights required to win these battles. Eventually these challenge scenarios could even be AI-generated themselves.
   2026-10-14: the owner's brief and a draft definition to discuss (analysis of the
   harness, spec, one concrete instance): [twwarhammer3/benchmark.md](twwarhammer3/benchmark.md).
   Owner notes on sieges (2026-10-14 night): benchmark who holds the victory points
   over time and the supplies left unspent; both are now measured per episode.

## Slay the Spire

Full runs with an API model ([README](spire/fullrun/README.md): reference and loop;
[log](spire/fullrun/log.md): versions), idle since 2026-10-13; v10 is on `main`, untested.
No run has won; the furthest reached Act 4 (v8, floor 54); `uv run python -m spire stats`
gives acts, wins and floors per version. API spend: $2.52 of the $25 cap
(`uv run python -m spire spend`, 2026-10-13). Open owner decisions:
[fullrun/README.md](spire/fullrun/README.md#open-owner-decisions). Paused: the first-combat
track ([README](spire/first-combat/README.md)). Planned: a remotely trained open-weight
model ([README](spire/open-weight/README.md); only a skeleton in `src/spire/openweight/`).

Next steps:
1. Replay v10 (`54a5967`, hand-select purpose) on `RUNDEV1`–`RUNDEV3`: its only job died
   on floor 10 at a WSL restart, so it and its settings-screen `key cancel` are untested.
2. Keys memory (drafted as v11 on branch `v11-keys`, unmerged): CommunicationMod 1.2.1
   never sends `keys`, so the model cannot see the keys it holds; v9 RUNDEV1 died on an
   elite path taken for a key it had ([integration.md](spire/integration.md),
   [candidates](spire/fullrun/README.md#candidate-changes)).
3. The rest of the results register ([results.csv](spire/fullrun/results.csv)): SpireBench's
   other measures, before more versions are compared. SpireBench released no code; its
   metric definitions and fixed held-out seeds carry over
   ([ideas](spire/fullrun/README.md#ideas-from-related-work-2026-10-12)).
4. An open StS1 full-run benchmark built from this harness: owner interest, scoped in the
   [approaches.md addendum](spire/approaches.md#addendum-2026-10-12-evening-an-open-sts1-benchmark).

## Owner direction

WH3:
- 2026-10-14 (benchmark steering): specialist anchor units and faction-specific mechanics
  should drive scenario design. Prioritize extreme tactical problems (cavalry against
  anti-large, caster-led forces, difficult sieges, commanding/fighting Skaven swarms),
  meaningful creative choices and battles worth watching; well-rounded armies can follow.
  Small armies on either or both sides are equally suitable; high funds and large
  rosters are not requirements. Start the first specialist prototypes compact.
- 2026-10-13: an API model plays real-time battles, with the order delay measured; control
  through an in-game mod, never screenshots or desktop input; a hard $25 cap on its own
  ledger, `runs/twwarhammer3/llm-spend.jsonl`. Battles always run unpaused at 1x.
- 2026-10-13 (evening): an asynchronous `commander` over scripted `skills`, beside the
  direct `llm`; the other designs wait in [controllers.md](twwarhammer3/controllers.md).
- 2026-10-13 (late): evaluate on paired random draws (`--scenario random`, the same seeds
  for every controller, races drawn, armies autogenerated) at AI difficulty very hard;
  fixed scenarios only for quick diagnostics. Other battle types next.

Slay the Spire:
- 2026-10-12: complete runs by a frontier API model (`gpt-6-luna`, low effort), scaffolding
  found by autoresearch from observed mistakes; a hard $25 cap on `runs/llm-spend.jsonl`.
- 2026-10-12: interest in an open StS1 benchmark, since SpireBench's code is not public.
  Later, a remotely trained open-weight model (Qwen3.6-35B-A3B, then GLM-5.3, RL on Tinker).
- 2026-10-11: PPO paused for language-model post-training, itself paused for full runs.

## Runtime and ownership

- Slay the Spire ([runtime facts](spire/integration.md#runtime-and-source-pins)): the owner
  authorizes the installed Steam game and personal profile slot 0, including changes to
  stats, unlock progress, run history and achievements (Ironclad unlock level was 3 of 5
  on 2026-10-11; runs record profile evidence).
- WH3: [engine facts](twwarhammer3/integration.md). A launch builds the mod into
  `C:/wh3-agent/mods`, writes `twwarhammer3_mods.txt` into the game folder, installs the
  startup-video skip pack `data/zzz_twwarhammer3_skip_intro.pack` and sets
  `fe_game_intro_video_enabled false`; both persist for ordinary Steam launches
  ([how to reverse](twwarhammer3/README.md#commands)).
- Also authorized: game windows, local GPU work, commits and pushes to public `main`, and
  paid OpenAI API use within each ledger's cap. One game controller at a time across both
  games (each game's lock and process check cover only that game); one GPU job at a time.

## Unmerged branches

- `integration/heldout-clip-continuation` (`940d698`): first-combat work, on `01f2984`.
- `v11-keys` (`cd97667`): Spire v11 keys memory, on v10 (`54a5967`).
- `wh3-fire-report` (`832b233`): WH3 fire-report candidate, on v9 (`d928965`); untested.
- `wh3-v4-info` (`aa1ece5`): WH3 orientation and losses candidate, on v3 (`c34c246`).
