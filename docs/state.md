# Project state

Updated 2026-10-14 17:31 UTC: what is running, where each game
stands and what comes next. History: [WH3 log](twwarhammer3/log.md),
[Spire full-run log](spire/fullrun/log.md), [first combat](spire/first-combat/README.md).

## Active work

WH3 benchmark work is active (owner goal, 2026-10-14): complete the paired benchmark,
difficulty/latency calibration, and the interface fixes its scenarios require.
Owner steering: prioritize specialist challenge scenarios with anchor units and faction
mechanics, including cavalry/anti-large, caster-led forces, difficult sieges and Skaven
swarms. [Scenario recipe](twwarhammer3/scenario-recipe.md) is now part of selection.
The current queue finishes as diagnostics; choose a specialist candidate before G1/G2.
The unstarted Herald G1 draft is superseded; freeze the new candidate/reference before G1.
The b2 acceptance rotations and serial screening/objective queue have completed.
The queue and final child exited successfully at 2026-10-14 17:15:50 UTC; no game
controller from that queue remains active. b2 source was `b476175`. Herald 1.0: hold lost 448 s, skills won
382 s, attack-nearest lost 249 s; 1.1: all three lost (242/266/265 s). Both launches
had matched rematches; these are screening instances, not calibration admission.
Settlement/domination objective fields and register rows passed trace audits, including
nine builds and 15 reinforcement purchases. Proofs and limits are in the progress page.

b2 evidence is committed. Tested draft `9b73105` from `/tmp/wh3-benchmark-b3` is
merged into main (`4d3caad`). The frontend-only specialist roster inventory completed;
the owned launch exited normally. No game controller is active. Evidence is in
`runs/twwarhammer3/capability-probes/benchmark-specialist-rosters/`.
b4 (`7727ee6`) adds compact six-versus-eight cavalry and five-versus-ten caster
prototypes, explicit horse selection and an 8000 budget cap. Next: screen both
development variants with `hold`, `attack_nearest` and Luna `llm_rules`.
The draft adds the missing-terrain setup gate, detailed startup failures, whole-job
throughput, corrected visibility (`obs-v2+terrain`), `llm_rules`, barrier/spell-range
observations and starting-resource/loadout comparisons. It passed 197 WH3 tests with
Lua, a further Lua ownership test, 1041 broader tests with four explained skips, Ruff
and Lua parsing. Specialist game acceptance remains pending. No G1/G2 trials have run.
Implementation and evidence: [benchmark-progress.md](twwarhammer3/benchmark-progress.md).

When a job starts, note here its game, job directory, start time (`date -u`) and `watch`
command; clear it when the job stops.

## Total War: WARHAMMER III battles

[README](twwarhammer3/README.md) (track page, full [Next](twwarhammer3/README.md#next)),
[battle types](twwarhammer3/battle-types.md), [controllers](twwarhammer3/controllers.md),
[integration](twwarhammer3/integration.md), [log](twwarhammer3/log.md). `main` runs
`llm` v15 and `commander` v3 (every battle type's objectives, `build` and `reinforce`
orders) and the `skills` executor v1.2. API spend: $3.3329 of the $25 cap
(ledger after b2 acceptance; the queued jobs are scripted).
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

- `integration/heldout-clip-continuation` (`940d698`): first-combat work, on `01f2984`.
- `v11-keys` (`cd97667`): Spire v11 keys memory, on v10 (`54a5967`).
- `wh3-fire-report` (`832b233`): WH3 fire-report candidate, on v9 (`d928965`); untested.
- `wh3-v4-info` (`aa1ece5`): WH3 orientation and losses candidate, on v3 (`c34c246`).
