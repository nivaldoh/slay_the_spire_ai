# Project state

Updated 2026-10-14 21:05 UTC: what is running, where each game
stands and what comes next. History: [WH3 log](twwarhammer3/log.md),
[Spire full-run log](spire/fullrun/log.md), [first combat](spire/first-combat/README.md).

## Active work

WH3 benchmark work is active (owner goal, 2026-10-14): finish the paired benchmark,
difficulty/latency calibration and required interface fixes. Prioritize specialist
anchor units, faction mechanics and compact armies; see the
[scenario recipe](twwarhammer3/scenario-recipe.md). No scenario is admitted and no G1/G2
trials have run. The generic Herald G1 draft remains superseded; held-out maps are untouched.

The b8 cavalry retry queue on `f179dbe` completed at 21:05:37 UTC. Runner/controller
and the read-only stall monitor exited; doctor reports ready. No game controller is
active. Queue state: `runs/twwarhammer3/calibration/b8-assault-screen-r2-plan-state.json`.

At 1.0: attack-nearest lost at 370 s (margin -0.808), Luna low at 247 s (-0.589),
hold at the timer at 1205 s (0). At 1.1: Luna low lost at 271 s (-0.626), hold at
1205 s (0), attack-nearest at 395 s (-0.868). All rematch starts matched. Hold's two
armies stayed intact; Luna routed the guns/cannon but lost against the remaining
halberdiers/general. The initial 1.0 attempt's unexplained observation stall at 340.7 s
remains an infrastructure failure, not a loss. The retry had no recurrence.
Combined: 6 valid / 7 started trials in 4611.62 wall seconds, 4.68 valid trials/hour.
Report: `runs/twwarhammer3/reports/bench-b8-assault-development.json`. WH3 spend:
$6.3315 of $25. Keep the cumulative ledger; do not reset it.

The earlier b7 Sol low cavalry pilot won at 432 s (margin +0.433, $0.62009), proving
one viable strategy but not admission. The caster pilot lost at 1077 s; it verified
ground Pendulum resource/cooldown changes and exposed missing morale/flight controls.
b8 added those controls. Its separate live probe verified both flyers grounded at
7.9 s, still grounded after a repeated land request at 8.2 s, and airborne at 18.7 s.
All six flight orders were accepted. Evidence: `reports/bench-b8-flight-acceptance.json`.

The timer endings exposed a label bug: the engine resets `remaining_ms` to -1 at
VictoryCountdown, so b8 records `ended_by=engine_result`. The engine losses remain
valid. Both countdown deadlines expired about 154 ms before the result; separate
correction audit: `reports/bench-b8-timer-classification-audit.json`. Raw records stay
unchanged. Isolated b9 `33b7e2b` in `/tmp/wh3-benchmark-b9` retains a countdown sampled
on engine ticks and labels expiry as a countdown inference. It also adds `rush_nearest`,
changing only AttackNearest's run flag. The clean combined worktree passes 223 WH3
tests with Lua, repository-wide Ruff, Lua 5.1 parsing and recorded-countdown replay.
Neither change has live acceptance yet; b9 is unmerged.

Pre-G1 baseline amendment: for the cavalry attacker, compare walk-nearest/run-nearest
against the reference. Hold stays an objective-failure control because an idle timer
loss can have raw margin zero. Raw scoring, six launches per modifier, the 2–4/6
non-timer-win threshold and positive paired intervals against both active baselines
are unchanged. Geometry flags stay in primary comparisons, with a secondary result
excluding flagged launches; changed resources/loadouts stop later jobs for review.
Requested 0/6/10 s snapshot ages are minima; actual ages are reported.

Next: merge b9 after committing the b8 evidence, then pin and launch
`runs/twwarhammer3/calibration/b9-timer-and-reference-plan.json`. Its separate
`run-experiment-b9.py` driver requires a valid timer result with retained expiry
evidence before the paid screens. Then medium-effort Luna and run-nearest screen
1.0/1.1 on the unchanged compact armies. The draft is not executable until its source
revision/status are set. Freeze a competent reference and viable candidate before
G1/G2. Earlier retired pilots and all failures remain in the [log](twwarhammer3/log.md).

When a job starts, note here its game, job directory, start time (`date -u`) and `watch`
command; clear it when the job stops.

## Total War: WARHAMMER III battles

[README](twwarhammer3/README.md) (track page, full [Next](twwarhammer3/README.md#next)),
[battle types](twwarhammer3/battle-types.md), [controllers](twwarhammer3/controllers.md),
[integration](twwarhammer3/integration.md), [log](twwarhammer3/log.md). `main` runs
`llm` v15 and `commander` v3 (every battle type's objectives, `build` and `reinforce`
orders) and the `skills` executor v1.2. API spend: $6.3315 of the $25 cap
(after both b8 Luna cavalry screens).
The owner has authorized benchmark calibration, including AI modifiers 1.0 and 1.1.
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

Current owner goal: complete the first three benchmark steps recommended in the
2026-10-14 status discussion (paired benchmarks, calibration/latency experiments, required
interface fixes). Remaining longer-term directions:
1. Battle types toward benchmarks ([battle-types.md](twwarhammer3/battle-types.md#next)):
   variants per type (the `random-<type>` draws, both roles), calibration of the
   scripted controllers per type, and the interface gaps found (no deployment phase, no
   terrain, survival wave timing).
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

- `wh3-benchmark-b9` (`33b7e2b`): terminal countdown classification and running baseline,
  tested, awaiting the b8 queue's exit before merge and live acceptance.
- `integration/heldout-clip-continuation` (`940d698`): first-combat work, on `01f2984`.
- `v11-keys` (`cd97667`): Spire v11 keys memory, on v10 (`54a5967`).
- `wh3-fire-report` (`832b233`): WH3 fire-report candidate, on v9 (`d928965`); untested.
- `wh3-v4-info` (`aa1ece5`): WH3 orientation and losses candidate, on v3 (`c34c246`).
