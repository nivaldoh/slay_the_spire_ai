# Project state

Updated 2026-10-16 00:42 UTC: what is running, where each game stands and what comes
next. Status only; history goes to the logs: [WH3](twwarhammer3/log.md),
[Spire full runs](spire/fullrun/log.md), [first combat](spire/first-combat/README.md).

## Active work

No game controller is running. Implementing b12: distinct scenario families, siege
defence, survival, conquest and a battery-evacuation pilot. Lobby inventory and explicit
survival pool recruitment are verified; offline checks and live screens are next.
Evidence: `runs/twwarhammer3/capability-probes/expansion-20261016/`.

When a job starts, note here its game, job directory, start time (`date -u`) and `watch`
command; clear it when the job stops.

## Total War: WARHAMMER III battles

[README](twwarhammer3/README.md) (track page and [Next](twwarhammer3/README.md#next)),
[log](twwarhammer3/log.md) (newest first, with the versions on `main` at the top),
[results.csv](twwarhammer3/results.csv).

- On `main`: `llm` v17 (`llm_rules` shares its input), `commander` v4 over the `skills`
  executor v1.2, the scripted `attack_nearest`, `rush_nearest` and `hold`, and benchmark
  harness b11 / evaluator v2: the 1 Hz replay recorder, optional stills, per-policy models (one launch
  pairs `llm_rules` on Sol with `llm_rules@gpt-6-luna`), a plan queue that stops on changed
  rematch starts, and the redesigned HTML report.
- C1 is complete: on `brt-cavalry-emp-assault-hard` (AI ×1.1), Sol won 1 of 6;
  Luna and both baselines 0 of 6 ([log](twwarhammer3/log.md#2026-10-15-calibration-c1-launches-3-to-6)).
  The owner has replaced win-rate admission with hard challenges and partial progress;
  C1 remains development evidence, with no automatic easier calibration block.
- Both swarm prototypes have working screens; every player army routed. Existing reports
  are `c1-cavalry-ai11`, `swarm-screens` and `cavalry-assault` in
  `runs/twwarhammer3/reports/`. The canonical `benchmark.html` (26 MB, 55 jobs) now
  shows one score per commander after the owner's review: the C1 controlled comparison,
  one mean-path map per model and scores in one section per game mode (empty modes as
  placeholders), on a paper page around the replay
  ([log](twwarhammer3/log.md#2026-10-15-report-sections-by-game-mode)); offline browser
  validation passed.
- API spend: $14.3146 of the $25 cap on 2026-10-15.

Next: expand varied armies, siege defence, survival and conquest, with 2-3 exploratory
battles total per new scenario. Each must offer credible plays that exploit strengths
and mitigate disadvantages; redesign or drop scenarios without meaningful choices.
The first three implementation steps are complete
([b11 log](twwarhammer3/log.md#2026-10-15-harness-b11-common-measures-and-one-report)).
Scenario-specific scoring, deeper comparisons and added delay remain later. Steam is
now pinned to 9.0.4; old evidence keeps its original build.

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
- 2026-10-16 (implementation): approved a compact core of 6-8 distinct decision problems;
  variants do not count as new coverage. Implement siege defence, survival and conquest
  plus one custom battery-evacuation pilot; narrow interface extensions and custom
  scripting are allowed. Audit existing families for redundancy. Later self-comparisons
  distinguish army/control workload from prompt length and useful history.
- 2026-10-15 (playmaking): retain difficult battles only when they give a controller
  meaningful options to exploit advantages and mitigate disadvantages. Exploratory runs
  should inspect those opportunities; redesign or drop scenarios with no credible plays,
  preserving their evidence. This applies to existing challenges too.
- 2026-10-15 (implementation): authorized the first three steps: controller integration,
  common measures and one report. Scenario expansion remains next.
- 2026-10-15 (refined): planning only at that stage. Prioritize scenarios that look and play very
  differently: varied armies, siege, survival, conquest and other modes. Start with
  general measures (kills, survivors, objective time, etc.); scenario-specific points
  are a possible future improvement. Play 2-3 exploratory battles total per new scenario,
  with deeper testing later. Keep difficult odds, no win-rate admission campaign, and
  one HTML report for the whole benchmark (supporting files allowed). Interface versions
  remain metadata; added-delay experiments wait. See the
  [plan](twwarhammer3/benchmark.md#implementation-plan).
- 2026-10-14 (benchmark steering): specialist anchor units and faction-specific mechanics
  should drive scenario design. Prioritize extreme tactical problems (cavalry against
  anti-large, caster-led forces, difficult sieges, commanding/fighting Skaven swarms),
  meaningful creative choices and battles worth watching; well-rounded armies can follow.
  Small armies on either or both sides are equally suitable; high funds and large
  rosters are not requirements. Start the first specialist prototypes compact.
- 2026-10-14 (night, sieges): benchmark who holds the victory points over time and the
  supplies left unspent; both are now measured per episode.
- 2026-10-13 (benchmark idea, the owner's words): "Eventually we could turn this game into
  some kind of serious LLM benchmark? For now I'm just registering this here. Could try to
  create certain challenge scenario battles where the opponent side is stronger, and see
  how well different models perform and whether they discover certain key insights
  required to win these battles. Eventually these challenge scenarios could even be
  AI-generated themselves."
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
