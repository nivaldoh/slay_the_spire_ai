# Project state

Updated 2026-10-15 13:57 UTC: what is running, where each game stands and what comes
next. Status only; history goes to the logs: [WH3](twwarhammer3/log.md),
[Spire full runs](spire/fullrun/log.md), [first combat](spire/first-combat/README.md).

## Active work

WH3, started 2026-10-15 about 11:05 UTC-3 (14:05 UTC): the queue
`runs/twwarhammer3/calibration/c1-plan-rest.json` runs C1 launches 3-6
(`bench-c1-cavalry-ai11-03-20261015` to `-06-`), about 2 hours, ending about 13:10 UTC-3.
Follow with `uv run python -m twwarhammer3 watch runs/twwarhammer3/battle/<job> --next`. To
stop it early, `pkill -INT -f wh3_queue.py`: the running battle records an interruption and
no further job starts. No commits while it runs (the queue refuses its next job if HEAD
moves). Stale `/tmp` worktrees and merged WH3 branches await the owner's removal (commands
in the [cleanup entry](twwarhammer3/log.md#2026-10-15-track-cleanup-for-agents-and-reviewers)).

When a job starts, note here its game, job directory, start time (`date -u`) and `watch`
command; clear it when the job stops.

## Total War: WARHAMMER III battles

[README](twwarhammer3/README.md) (track page and [Next](twwarhammer3/README.md#next)),
[log](twwarhammer3/log.md) (newest first, with the versions on `main` at the top),
[results.csv](twwarhammer3/results.csv).

- On `main`: `llm` v16 (`llm_rules` shares its input), `commander` v3 over the `skills`
  executor v1.2, the scripted `attack_nearest`, `rush_nearest` and `hold`, and benchmark
  harness b10: the 1 Hz replay recorder, optional stills, per-policy models (one launch
  pairs `llm_rules` on Sol with `llm_rules@gpt-6-luna`), a plan queue that stops on changed
  rematch starts, and the redesigned HTML report.
- Calibration block C1 (`brt-cavalry-emp-assault-hard`, AI ×1.1), decided under the owner's
  delegation on 2026-10-15 ([decisions](twwarhammer3/benchmark.md#calibration-decided-2026-10-15)):
  2 of 6 launches done, Sol 1 of 2, Luna and both baselines 0 of 2. No scenario is
  admitted yet; G1 (2026-10-14) stays a partial earlier attempt.
- Last finished (2026-10-15 morning): the two Skaven swarm screens (both prototypes work;
  every player army routed) and C1 launches 1-2 ([log](twwarhammer3/log.md)); reports
  `c1-cavalry-ai11`, `swarm-screens` and `cavalry-assault` in `runs/twwarhammer3/reports/`.
- API spend: $10.0391 of the $25 cap on 2026-10-15 (`uv run python -m twwarhammer3 spend`).

Next steps:
1. C1 launches 3-6: `runs/twwarhammer3/calibration/c1-plan-rest.json`, frozen to the HEAD
   of this update (regenerate `source_revision` if HEAD moves), about 2 hours and $4-6.
   After launch 2: Sol 1 of 2 at ×1.1, Luna and both baselines 0 of 2
   ([log](twwarhammer3/log.md#2026-10-15-calibration-c1-launches-1-and-2)).
2. Then: Sol screens of the two swarm prototypes
   (`runs/twwarhammer3/calibration/swarm-sol-screens-plan.json`, about 40 minutes and $3), and the next `llm` version with the
   out-of-range attack fix (and possibly last sightings that keep the unit's state, an
   `obs-v4` track change suggested by Sol's C1 loss) ([candidates](twwarhammer3/controllers.md#candidate-changes-for-the-next-version))
   only after C1, which freezes the controllers. The owner's later look at the delegated
   decisions ([log](twwarhammer3/log.md#2026-10-15-harness-b10-llm-v16-and-the-calibration-decisions)).
3. Then the [README's Next](twwarhammer3/README.md#next): specialist scenarios, the next
   `llm`/`commander` version, the random-draw comparison, battle-type variants and the
   deferred Lua cleanups.

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

- `wh3-llm-v17` (`c1cc14b`): both candidates below combined and tested (348 WH3 tests), ready
  to merge after C1 as `llm` v17 on track `obs-v4`.
- `wh3-obs-last-state` (`287cfba`): last sightings keep a fleeing enemy's state ("routing when
  last seen"), on `94eef9c`; an `obs-v4` track change, after C1.
- `wh3-llm-range` (`b58d327`): `llm`/`llm_rules` flag a shooter's target beyond its range
  ("it advances to shoot"), on `da6f3bb`; merge after C1, as the next `llm` version.
- `integration/heldout-clip-continuation` (`940d698`): first-combat work, on `01f2984`.
- `v11-keys` (`cd97667`): Spire v11 keys memory, on v10 (`54a5967`).
- `wh3-fire-report` (`832b233`): WH3 fire-report candidate, on v9 (`d928965`); untested.
- `wh3-v4-info` (`aa1ece5`): WH3 orientation and losses candidate, on v3 (`c34c246`).
- `wh3-visual-imagery` (`af8f76e`): patch-identical to `main`'s `ca397ab` (stills); remove
  with `git branch -D`.
