# Total War: WARHAMMER III battles

Can an API model command an army in a real-time custom battle against the game AI, with
the delay between the state it saw and its orders measured and told to it, and can the
autoresearch loop improve its scaffolding? A Lua mod is the only interface, and the battle
keeps running unpaused at 1x while the model thinks. Campaign mode and model training come
later. What is running and the versions on `main`: [../state.md](../state.md); every
version, job and finding: [log.md](log.md).

The owner's initial modding guide (8 October 2026) set the first shape. This page and
[integration.md](integration.md) supersede it, and git keeps it:
`git show 001d1ce:docs/twwarhammer3/guide.txt`.

## Pages

| Page | Read it for |
|---|---|
| [integration.md](integration.md) | engine facts: packs, menus, lobby settings, unit API, context system, battle types, capture |
| [controllers.md](controllers.md) | the policies and their versions, comparing them, candidate changes, designs not built |
| [battle-types.md](battle-types.md) | the battle-type scenarios, the `mode` state, the `build` and `reinforce` orders |
| [benchmark.md](benchmark.md) | the latency-aware benchmark: definition, scenarios, the stopped calibration |
| [benchmark-run.md](benchmark-run.md) | running paired benchmark trials, outside controllers |
| [reports.md](reports.md) | the offline HTML report and replay, its curated notes |
| [WH3_latency_aware_benchmark_requirements.md](WH3_latency_aware_benchmark_requirements.md) | the owner's benchmark brief |
| [WH3_report_redesign_guide_for_Codex.md](WH3_report_redesign_guide_for_Codex.md) | the owner's report redesign brief |
| [log.md](log.md) | dated history: versions, harness revisions, jobs, costs |
| [results.csv](results.csv) | the results register, one row per episode, appended by `play` |

## Terms

- **Job, episode, trial**: one `play` run (`runs/twwarhammer3/battle/<job>/`); one battle
  in it (`episode-NNNN/`, later ones rematches); a trial is an episode of a rotation.
- **Job names**: `<policy>[-<model>]-v<version>-<scenario>-<date>`, such as
  `commander-luna-v2-rand-322117462-20261013`; benchmark jobs are
  `bench-<bN or g1>-<purpose>-<date>`, such as `bench-b9-timer-acceptance-20261014` or
  `bench-g1-cavalry-ai10-01-20261014`.
- **vN**: a version of the `llm` or `commander` prompt and harness; `v1.N` the `skills`
  executor. Each has a log.md entry. The register's `harness` column is the `-vN-` segment
  of the job name (`stats.harness_version`), blank for `bench-*` jobs.
- **b1-b9**: benchmark harness revisions, each a "Benchmark harness bN" entry in log.md.
- **G1, G2**: the calibration stages in [benchmark.md](benchmark.md): G1 repeats paired
  controllers on one candidate scenario at AI stats modifiers 1.0 and 1.1; G2 adds
  observation-age arms (0, 6 and 10 s). G1 is incomplete and G2 never ran.
- **Track** `obs-v3+terrain/act-v2/live-1x`: the observation, action and timing contract
  a manifest records (`play.TRACK`); trials on different tracks are not pooled.
- **Luna, Sol, Astra**: `gpt-6-luna`, `gpt-6-sol`, `gpt-6-astra` (the 2026-10-13
  commander smoke used `gpt-6.1-sol`). "Low" is `--effort low`; "Sol low" in the
  benchmark work is `gpt-6-sol` at low effort.
- **walk-nearest, run-nearest**: the scripted policies `attack_nearest` and `rush_nearest`.
- **`llm`, `llm_rules`, `commander`**: the direct model controller with the tactical prompt
  (`system_prompt.md`), the same controller with a rules-only prompt (`rules_prompt.md`),
  and the asynchronous model that sets skills for the `skills` executor.
- **Scenario names** such as `kho5-dwf5`: the player's army, then the enemy's, by race
  and unit count. `-hard` variants set AI stats modifier 1.1; `-heldout-*` variants are
  kept out of tuning.

## How it works

There is no external game API; the mod is the API. Everything the game knows leaves
through it, and every order enters through it.

- **Mod and launch.** `src/twwarhammer3/mod/` holds five Lua scripts: battle, frontend,
  shared UI steps, presentation capture and a vendored JSON library. `engine/pack.py`
  packs them into `C:/wh3-agent/mods/twwarhammer3.pack`; `engine/runtime.py` writes the
  mod list and starts `Warhammer3.exe` once per job under the `gameai.windows`
  supervisor. The scripts stay inert without `C:/wh3-agent/bridge/session.json`, so the
  installed pack changes nothing in ordinary play
  ([packs and loading](integration.md#packs-and-loading)).
- **Bridge.** The controller in WSL and the scripts exchange whole JSON files in
  `C:/wh3-agent/bridge/`. The `engine/mailbox.py` docstring is the reference for every
  file and observation field. `protocol.py` holds the orders: `ORDER_TYPES` (move,
  attack, halt, behaviour, ability, flight), the army's own orders (unit `"army"`:
  ability, build, reinforce) and `validate_orders`.
- **Real time.** The battle keeps running while a policy decides. Each request names the
  observation it was based on; its acknowledgement gives the battle time each order was
  issued or queued, and that delay goes into the next prompt. The next decision starts
  when the previous batch is acknowledged. `--observe-ms` sets how often the state is
  published, `--interval-ms` adds a wait after orders apply, and `--delay-seconds`
  buffers observations to a minimum age. There is no pause or speed option.
- **Information boundary.** A policy gets the observation without its `evaluation`,
  `final` and `setup` sections: friendly units in full, enemy units only while the player
  can see them, and the enemy roster the custom battle screen shows.
- **Setup.** `battle/setup.py` turns a `--scenario` entry of
  `configs/twwarhammer3/scenarios.json` into custom battle menu steps (no desktop input);
  its docstring is the scenario field reference. `random` entries draw a map and each
  side's race from `configs/twwarhammer3/custom_battle.json` with `--seed` and
  autogenerate the armies. An entry with `expect` is a declared benchmark scenario: the
  lobby sets and reads back its timer, AI stats modifier and funds, and the battle checks
  the rest ([lobby settings](integration.md#lobby-settings-and-declared-scenarios)).
  Other entries leave funds, unit size, time limit and difficulty as the lobby has them.
- **Jobs.** `battle/play.py` launches the game once, plays the episodes and replays the
  same battle between them through the results popup's rematch. `battle/controllers.py`
  names the policies ([controllers.md](controllers.md)). The files of a job and an
  episode are listed in [runs/README.md](../../runs/README.md); each episode appends a
  row to [results.csv](results.csv).

## Commands

```bash
# Play: a new --output, a clean source scope; model policies need --budget-usd
uv run python -m twwarhammer3 play --policy llm --budget-usd 25 --scenario random --seed N \
    --output runs/twwarhammer3/battle/llm-luna-vN-rand-N-YYYYMMDD
uv run python -m twwarhammer3 play --policy commander --budget-usd 25 --scenario kho5-dwf5 \
    --episodes 3 --output runs/twwarhammer3/battle/commander-luna-vN-kho-YYYYMMDD
uv run python -m twwarhammer3 play --scenario brt-cavalry-emp-assault \
    --policy llm_rules,attack_nearest,rush_nearest --model gpt-6-sol --budget-usd 25 \
    --rotation-seed N --output runs/twwarhammer3/battle/bench-bN-<purpose>-YYYYMMDD
uv run python scripts/wh3_queue.py PLAN.json      # a frozen plan of play jobs, one at a time
# Follow and review
uv run python -m twwarhammer3 watch [JOB]                 # live beside the game; --prompts
uv run python -m twwarhammer3 watch JOB --next            # wait for an episode, stall or end
uv run python -m twwarhammer3 digest JOB[/episode-NNNN]   # per-episode table, or one battle
uv run python -m twwarhammer3 digest JOB/episode-NNNN --at SECONDS  # one decision in full
uv run python -m twwarhammer3 stats                       # results.csv by scenario and controller
uv run python -m twwarhammer3 report JOB [JOB ...] --output runs/twwarhammer3/reports/NAME
uv run python -m twwarhammer3 spend                       # runs/twwarhammer3/llm-spend.jsonl
# Runtime and probes
uv run python -m twwarhammer3 doctor                      # read-only: pins, preferences, game
uv run python -m twwarhammer3 launch                      # build, install, run until Ctrl-C
uv run python -m twwarhammer3 menu --dump 4               # UI tree of the screen (ui_tree.txt)
uv run python -m twwarhammer3 menu [--battle] --steps steps.json  # tails menu.log or mod.log
uv run python -m twwarhammer3 pack --list PACK            # --extract PACK NAME; bare: build
uv run pytest tests/twwarhammer3                          # Lua (lupa) and image tests included
```

- `--model` (default `gpt-6-luna`) and `--effort` (default `low`) pick the API model of
  `llm`, `llm_rules` and `commander`. The key comes from `OPENAI_API_KEY` or the file
  named by `SPIRE_OPENAI_KEY_FILE` (the shared `gameai.llm` keeps Spire's name).
- Comma-separated `--policy` names rotate in an order drawn from `--rotation-seed`;
  `--delay-seconds 0,6,10` crosses them with observation-age arms; `--episodes` defaults
  to one per combination. `--policy package.module:Class` loads an outside controller
  ([benchmark-run.md](benchmark-run.md)).
- `--episode-timeout` defaults to a declared scenario's timer plus 120 s (else 3900 s)
  and `--run-timeout` to 8 h, or longer if every episode needs it. A declared scenario
  refuses `--attach` (which plays in the game `launch` started).
- `--show` puts each model reply in the game's advisor window; `--stills` captures up to
  four presentation stills; `--no-record-replay` turns off the 1 Hz replay recorder.
- `report` writes `NAME.html`, `NAME.json` and `NAME.txt` offline ([reports.md](reports.md)).
- `scripts/wh3_queue.py`: the plan format is in its docstring. It refuses to start unless
  HEAD is the plan's `source_revision` with a clean source scope, and it stops at the
  first job that fails or whose rematch started with a changed roster, strength, loadout
  or resources.
- `launch` and `play` install a startup-video skip that persists for ordinary Steam
  launches: `data/zzz_twwarhammer3_skip_intro.pack` in the game folder and
  `fe_game_intro_video_enabled false` in the game's preferences. To reverse it, stop WH3,
  delete the pack and set the preference back to `true`; the next project launch
  reinstalls both ([details](integration.md#packs-and-loading)).

## The loop

Compare versions or controllers on paired battles: the same `--scenario random --seed N`
draws for each (one job per seed; a rematch replays the same draw, so a deterministic
controller plays each seed once), or one job rotating the controllers on a declared
scenario. Fixed scenarios such as `kho5-dwf5` are quick diagnostics. Review the battles,
make one change to the prompt, rendering, memory or executor, and log the version in
[log.md](log.md). The review is the `wh3-version-review` workflow
(`.claude/workflows/wh3-version-review.js`): a reviewer per episode reads the digest and
the prompts and replies at the turning points (`digest EPISODE --at SECONDS`), three
proposers each suggest one change (tactics prompt, state and memory, order interface)
with the version history and the baseline in view, and three judges score them. While it
runs, play more seeds with the same version and draft the next change in a git worktree:
a job stops if its source scope changes. Note each job's start and stop in
[Active work](../state.md#active-work). The WH3 ledger (`runs/twwarhammer3/llm-spend.jsonl`)
is separate from Spire's, with its own $25 cap.

## Next

Status and the owner's current direction are in [../state.md](../state.md). Candidate
work:
1. Specialist scenarios ([benchmark.md](benchmark.md)): anchor units, faction mechanics,
   hard tactical choices and watchable battles, starting compact. Screen the cavalry
   against anti-large and caster-led prototypes before repeated calibration at AI
   modifiers 1.0 and 1.1; keep held-out variants out of tuning.
2. Freeze a viable candidate and a competent reference, review starting-formation
   variation, then run repeated paired calibration (G1).
3. Paired added-observation-age arms (`--delay-seconds 0,6,10`), unpaused at 1x, reported
   with uncertainty (G2).
4. The random-draw comparison on its three remaining seeds (264482191, 1355466036,
   238913231), then Sol and Astra as commander on the same draws.
5. Battle types: variants, both roles and the interface gaps in
   [battle-types.md](battle-types.md#next).
6. The next `llm`/`commander` version:
   [candidate changes](controllers.md#candidate-changes-for-the-next-version). The older
   branches `wh3-fire-report` and `wh3-v4-info` predate the v13 interface and would need
   rebasing.

Deferred cleanups:
- Lua changes that each need one engine smoke battle: drop the pause-mode leftovers
  (the observation's constant `speed` and `awaiting_orders`, session `speed` and `pause`,
  `mailbox.require_realtime` and its guards); remove dead paths (the `start` control,
  `state.applied_ms`, restart's fallback before a decision with its
  [Unverified](integration.md#unverified) entry, the duplicate imagery throttle and
  `shot.backend` in `twwarhammer3_imagery.lua`); stop reading the always-true session
  switches `enabled`, `autostart` and `menu`, then drop them from `play.session`; split
  `apply_order`, share the observation-building code, split `mode_section`, and move the
  file helpers into the shared `_lib` script.
- `play --attach`: request ids restart at `r1` for every `Mailbox`, and the battle drops a
  request repeating its last id, so a second attach job on the same battle can stall
  until its episode timeout. A per-mailbox id prefix fixes it.
- `LLMPolicy.acknowledge` keeps its fallback for acknowledgements without `index`
  (traces before `863d10b`); dropping it is the owner's call.
