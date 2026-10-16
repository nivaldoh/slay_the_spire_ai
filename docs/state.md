# Project state

Updated 2026-10-16 19:22 UTC: what is running, where each game stands and what comes
next. Status only; history goes to the logs: [WH3](twwarhammer3/log.md),
[Spire full runs](spire/fullrun/log.md), [first combat](spire/first-combat/README.md).

## Active work

Running since 20:11 UTC: WH3 queue `runs/twwarhammer3/calibration/v1b2-plan-20261016.json`:
a $0 `CasterSkirmish` check on the new caster variant, then one gpt-6.1-sol / low battle
on each of the siege and swarm variants (OpenAI cumulative cap $50.00). V1a's two free
checks passed ([ladder V1](twwarhammer3/log.md#2026-10-16-difficulty-ladder-first-step-v1));
follow with `uv run python -m twwarhammer3 watch`.

The [v20 live check](twwarhammer3/log.md#2026-10-16-live-check-of-the-v20-shared-magic-warning)
won the caster anchor with GLM-5.3 / low at 575 s ($0.41); spell refusals after a pending
spell fell from 7 to 3, short of the pre-set bar, and v20 stays. The caster anchor now
also needs a harder step. Earlier today: OpenRouter support and three schema checks passed;
the first GLM-5.3 / low battle completed, losing the caster anchor at 566 s for $0.4248.
The [review](twwarhammer3/log.md#2026-10-16-first-openrouter-battle-and-shared-magic-feedback)
records model reply errors, routing and a stale shared-magic reading after casts.
Four free tactical diagnostics are also complete. Feedback v20 / commander v7 now
labels pending spell costs; it is checked on recorded states but untested with a model.
The canonical report now includes the fourth script and GLM replay, backend snapshots
and reply-validation counts; offline browser checks pass. All six candidates remain provisional.

API ledgers: OpenAI $45.96 of $52; OpenRouter $0.83868719 of $50. V1b is the only paid
run planned.

When a job starts, note here its game, job directory, start time (`date -u`) and `watch`
command; clear it when the job stops.

## Total War: WARHAMMER III battles

[README](twwarhammer3/README.md) (track page and [Next](twwarhammer3/README.md#next)),
[log](twwarhammer3/log.md) (newest first, with the versions on `main` at the top),
[results.csv](twwarhammer3/results.csv).

- On `main`: `llm`/`llm_rules` v20, `commander` v7, skills v1.2, benchmark b13,
  evaluator v2 and track `obs-v4+terrain/act-v2/live-1x`. The interface supports native
  objectives/reinforcements and the optional public battery-evacuation objective.
- Six candidate decision families with live evidence remain after the live novelty audit
  in the [design audit](twwarhammer3/benchmark.md#scenario-design); the custom evacuation
  pilot is deferred (owner, 2026-10-16). Cavalry/caster variants
  count once each; the two swarm roles remain provisionally distinct. Conquest was
  demoted because it has one point, not the planned separated objectives. Win-rate admission
  is retired; difficult battles need meaningful, executable choices.
- M1 (2026-10-16 night): three battles per model on six core scenarios (gpt-6.1-sol on
  the four that separate models). Siege, swarm command and caster assault separate the
  models; survive-a-swarm and Kislev did not. The report page shows core scenarios and
  completed battles only; its JSON keeps setup failures and variants. Results, costs and
  reviews: [M1 entry](twwarhammer3/log.md#2026-10-16-matched-round-m1-on-the-retained-core-plan).
- OpenAI spend: $45.96 of $52; OpenRouter $0.8387 of $50.

Next: use the [cards](twwarhammer3/benchmark.md#calibration-cards-2026-10-16) to select
a specific remaining play to test (siege withdrawal/firing positions, swarm flank or
weapon support, or caster withdrawal), then a small strongest-model screen. The shared-magic
feedback fix needs live model validation before broader paid comparisons. OpenRouter's three
models passed the real WH3 reply schema and parser, and GLM completed one battle
([support](twwarhammer3/controllers.md#openrouter)); Kimi/Step battles and all high-effort
settings remain untested. The OpenAI remainder ($6.04) is unallocated; custom evacuation and separate
workload, prompt, history, representation and added-age experiments remain deferred.
Steam is pinned to 9.0.4; old evidence keeps its original build.

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
- 2026-10-16 (evening): make each scenario maximally difficult while still demonstrably
  winnable; fewer high-quality scenarios beat redundant ones that waste compute. Armies,
  map settings etc. may be modified to calibrate
  ([difficulty target](twwarhammer3/benchmark.md#current-proposal-calibrate-before-a-broad-model-comparison)).
- 2026-10-16 (resume): implement OpenRouter and the three chosen models, then continue
  improving benchmark calibration and the report within the existing budgets.
- 2026-10-16 (OpenRouter): the owner stored an OpenRouter key and set a separate $50
  budget. Requested support and three leading open-weight model API checks, then
  clarified: stop after cleanup and design this turn; no implementation or paid calls.
- 2026-10-16 (after M1): planning only. Keep the core provisional until the strongest
  models have been tested; current scenarios may be too easy for them. Calibrate
  challenges and extract more useful evidence before spending on another large model
  comparison ([proposal](twwarhammer3/benchmark.md#implementation-plan)).
- 2026-10-16 (03:28 UTC): the WH3 API cap rises to $52 (Spire keeps its own $25). Overnight,
  prioritize work that needs the game running, since a fullscreen battle makes the
  computer awkward to use during the day.
- 2026-10-16 (03:20 UTC): delay the custom battles (the evacuation pilot) for much later in
  the plan as a low-priority item, and proceed with other things.
- 2026-10-16 (planning note): less is more; a smaller set of high-quality scenarios, each
  answering a distinct question ([scenario design](twwarhammer3/benchmark.md#scenario-design)).
  Report feedback is recorded in [reports.md](twwarhammer3/reports.md#pending-report-notes).
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
  through an in-game mod, never screenshots or desktop input; a hard $25 cap (now $52) on its own
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
