# Total War: WARHAMMER III battles

Custom battles played by scripted and model controllers against the game AI. The engine
decides the winner, including timer endings (owner, 2026-10-23), and battles run unpaused at
1x. Controller research, team recovery and training are related work with separate evidence
requirements. Start with the [benchmark definition](benchmark.md), the
[implementation plan](benchmark-implementation.md#phases) and the
[initial implementation](benchmark-initial.md). What is running and the versions on `main`:
[../state.md](../state.md); every version, job and finding: [log.md](log.md).

The owner's initial modding guide (8 October 2026) set the first shape. This page and
[integration.md](integration.md) supersede it, and git keeps it:
`git show 001d1ce:docs/twwarhammer3/guide.txt`.

## Pages

Find your topic and start at its first page. The status word says what kind of page it is.
**live** pages are still being updated, and a sentence on them can lag the code, so check it
against the code or log.md before building on it. **ref** pages describe something built or
researched; some say what remains unverified or tied to an older build, and silence on a page
does not make it verified. **open** pages are proposals or plans with decisions pending;
**parked** pages were stopped by a decision and kept; **done** pages are finished plans kept for
their reasoning; **record** pages are history, and their entries stay as written.

### Current research

| Page | Status | Read it for |
|---|---|---|
| [research-focus.md](research-focus.md) | open | proposed focus and four marked decisions |
| [scenario-guidelines.md](scenario-guidelines.md) | open | scenario coverage, winnability, release criteria, owner replies |
| [cannae-eval.md](cannae-eval.md) | live | Cannae A/B/C: candidates, results, deciding checks; all unverified |
| [cannae-comparison.md](cannae-comparison.md) | live | battles A and B: familiar tactic against adaptation |
| [cannae-communication.md](cannae-communication.md) | live | battle C: one army under limited communication |
| [haengju-eval.md](haengju-eval.md) | open | second evaluation battle: a siege defence against divisions released in turn; plan only (decision 15) |
| [communication-structure.md](communication-structure.md) | open | peer messages against a commander on battle C; stages 0-3 built and run 2026-11-08, the stage-2 gate failed (decision 14) |
| [tactic-judges.md](tactic-judges.md) | open | LLM and VLM tactic annotation; nothing adopted |
| [../thesis/](../thesis/proposal.md) | open | proposed master's thesis |

### Benchmark

| Page | Status | Read it for |
|---|---|---|
| [benchmark.md](benchmark.md) | live | definition: scope, outcome, measurements, orders, timing, the suite |
| [benchmark-implementation.md](benchmark-implementation.md) | live | phases, owner interview, checks, gaps, later work, earlier plans |
| [benchmark-initial.md](benchmark-initial.md) | ref | the built Empire mirror and its agreed check |
| [benchmark-run.md](benchmark-run.md) | live | running paired trials, the coordination suite and outside controllers |
| [evaluation-guidelines.md](evaluation-guidelines.md) | open | proposed evaluation rules: task design, failures, statistics, review |
| [benchmark-references.md](benchmark-references.md) | ref | outside benchmarks, with one profile each in `benchmark-references/` |

### Tactics

| Page | Status | Read it for |
|---|---|---|
| [tactics-reference.md](tactics-reference.md) | ref | tactics catalogue; [sources](tactics-sources.md) |
| [tactics-evaluation.md](tactics-evaluation.md) | open | proposed study designs for the catalogue |

### The harness

| Page | Status | Read it for |
|---|---|---|
| [integration.md](integration.md) | live | engine facts: packs, lobby, unit API, clocks, pins |
| [controllers.md](controllers.md) | live | policies, versions, comparing them, designs not built |
| [battle-types.md](battle-types.md) | ref | battle-type scenarios, the `mode` state, `build` and `reinforce` |
| [reports.md](reports.md) | live | the HTML report, replay and curated notes |
| [traces.md](traces.md) | ref | model-decision exports and provenance |
| [checkpoints.md](checkpoints.md) | ref | save and restore a battle: agreed check, limits |
| [../how-code-works.html](../how-code-works.html) | live | visual code map and stories; GitHub shows its source, so open it in a local browser by pasting `\\wsl.localhost\Ubuntu\home\niv\repos\slay_the_spire_ai\docs\how-code-works.html` |

### Teams on one client

| Page | Status | Read it for |
|---|---|---|
| [multi-agent-implementation.md](multi-agent-implementation.md) | live | the team as built, agreed checks, what comes next |
| [gap-plan.md](gap-plan.md) | live | graph controllers: built version, checks, deferred research |
| [multi-agent-plan.md](multi-agent-plan.md) | open | evaluating independent teammates, stages, campaign |
| [team-structures.md](team-structures.md) | parked | one model per class, unit or group; costs refer to the parked line |

### Multiplayer and cloud

The first two pages give the current status and the tools; the plans follow them.

| Page | Status | Read it for |
|---|---|---|
| [multiplayer-control-foundation.md](multiplayer-control-foundation.md) | live | current status and evidence, proposed stages |
| [multiplayer-tools.md](multiplayer-tools.md) | ref | worker operations, capture, compare-peers; `wh3-multiplayer` skill |
| [mp-next-steps.md](mp-next-steps.md) | open | three-step plan; offline parts built, paid session stopped |
| [vm-team-plan.md](vm-team-plan.md) | open | PC and VM team battle; decisions 1-4 |
| [native-multiplayer.md](native-multiplayer.md) | open | investigation, step plan, headless, costs, risks |
| [boris-scenarios.md](boris-scenarios.md) | open | battles for the VM account; [sources](boris-scenarios-sources.md) |
| [gcp-client-setup.md](gcp-client-setup.md) | ref | Windows game-host setup; pilot result |
| [Cloud usage](../cloud.md) | live | project, spending boundary, cleanup |

### Background and paused research

| Page | Status | Read it for |
|---|---|---|
| [robotics.md](robotics.md) | ref | robotics ideas and comparison designs |
| [robot-team-research.md](robot-team-research.md) | ref | capability allocation, recovery, delayed plans; what transfers |
| [robot-team-plan.md](robot-team-plan.md) | parked | staged Empire experiment plan |
| [latency.md](latency.md) | open | knowing a tactic against executing it in time; Kimi P5 left |
| [checkpoint-rl.md](checkpoint-rl.md) | parked | RL handoff and results, paused (decision 11) |
| [checkpoint-rl-plan.md](checkpoint-rl-plan.md) | done | its implementation plan, built 10-26; code cites it |
| [support-timing.md](support-timing.md) | parked | infantry support timing, stopped 11-05 |

### Records

| Page | Status | Read it for |
|---|---|---|
| [log.md](log.md) | record | dated history: versions, harness revisions, jobs, costs |
| [results.csv](results.csv) | record | results register, one row per episode, appended by `play` |
| [tactic-cards.md](tactic-cards.md) | record | chariot rule, card design, screens |
| [empire.md](empire.md) | record | Empire set of 2026-10-20: decisions, risks, results |
| [small-scenarios-2.md](small-scenarios-2.md) | record | scenarios S8-S13: rosters, database facts, hypotheses |
| [WH3_latency_aware_benchmark_requirements.md](WH3_latency_aware_benchmark_requirements.md) | record | the owner's benchmark brief |
| [WH3_report_redesign_guide_for_Codex.md](WH3_report_redesign_guide_for_Codex.md) | record | the owner's report redesign brief |

## Terms

- **Job, episode, trial**: one `play` run (`runs/twwarhammer3/battle/<job>/`); one battle
  in it (`episode-NNNN/`, later ones rematches); a trial is an episode of a rotation.
- **Job names**: `<policy>[-<model>]-v<version>-<scenario>-<date>`, such as
  `commander-luna-v2-rand-322117462-20261013`; benchmark jobs are
  `bench-<bN or g1>-<purpose>-<date>`, such as `bench-b9-timer-acceptance-20261014` or
  `bench-g1-cavalry-ai10-01-20261014`.
- **vN**: a version of the `llm` or `commander` prompt and harness; `v1.N` the `skills`
  executor. Each has a log.md entry. The register's `harness` column is the `-vN-` segment
  of the job name (`stats.harness_version`), blank when the name has none (most `bench-*`
  jobs).
- **bN**: benchmark harness revisions, each logged in log.md; current revision in state.md.
- **G1, G2, C1**: historical calibration designs in [benchmark-implementation.md](benchmark-implementation.md#history).
  G1 is incomplete, C1 finished and G2 never ran. The 2026-10-15 plan retires win-rate
  admission; added observation-age experiments (0, 6 and 10 s) remain deferred.
- **Track** `obs-v4+terrain/act-v2/live-1x`: the observation, action and timing contract
  a manifest records (`play.TRACK`). Controller memory/prompt versions and evaluator
  versions are separate. Different conditions can share a report without pooling trials.
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
  supervisor, holding `RuntimeLock` (`C:/wh3-agent/owner.lock`). The scripts stay inert
  without `C:/wh3-agent/bridge/session.json`, so the
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

  JUDGEMENT?: Enemy information — assistant, 2026-10-13/14 (flagged by Claude, 2026-10-28):
  the Lua `visible_to_player` and `enemy_observation` show enemies only while visible and not
  hidden, the starting roster public, in exact numbers. Interview questions 19 and 26 ask.
- **Setup.** `battle/setup.py` turns a `--scenario` entry of
  `configs/twwarhammer3/scenarios.json` into custom battle menu steps (no desktop input);
  its docstring is the scenario field reference. `random` entries draw a map and each
  side's race from `configs/twwarhammer3/custom_battle.json` with `--seed` and
  autogenerate the armies. An entry with `expect` is a declared benchmark scenario: the
  lobby sets and reads back its timer, AI stats modifier, funds, difficulty, unit size and
  realism; startup checks the battle's independent readbacks
  ([lobby settings](integration.md#lobby-settings-and-declared-scenarios)).
  Other entries leave funds, unit size, time limit and difficulty as the lobby has them.
- **Jobs.** `battle/play.py` launches the game once, plays the episodes and replays the
  same battle between them through the results popup's rematch. `battle/controllers.py`
  names the policies ([controllers.md](controllers.md)). The files of a job and an
  episode are listed in [runs/README.md](../../runs/README.md); each episode appends a
  row to [results.csv](results.csv).

## Code map

Moved from AGENTS.md on 2026-10-29 (light factory docs cleanup). One file per line since
2026-11-01: a line starting `` - `path`: `` says what that file does, and a path ending in `/`
covers the files below it. `scripts/diagram_files.py` reads these lines into the "How the
WH3 code works" page (`docs/how-code-works.html`), and `scripts/check.py` flags `src/` Python
files missing here, except Slay the Spire's, which the page leaves out. The Spire list is in [docs/spire/AGENTS.md](../spire/AGENTS.md#layout).

JUDGEMENT?: One file per line, full paths (Claude Code, 2026-11-01): chosen so a script reads
the list exactly; the old grouped prose gave 36 of 49 files a description. The page's file
lists and check.py's "missing from the Code map" flag rest on this format.

`src/twwarhammer3/`, Total War: WARHAMMER III custom battles:
- `src/twwarhammer3/__main__.py`: CLI: doctor, pack, launch, menu (runtime and UI probes);
  play, digest, watch, card, stats, report, export, spend (jobs and offline evidence);
  benchmark (mirror and suite plans, reports, authoring);
  graph-author, graph-view (graph controllers); rl (checkpoint RL); coordinator, worker,
  compare-peers (native multiplayer)
- `src/twwarhammer3/protocol.py`: order types and validation, the error taxonomy;
  observations stay dicts; it changes freely (Spire's protocol.py is byte-stable)

`src/twwarhammer3/engine/`, the game runtime:
- `src/twwarhammer3/engine/runtime.py`: pins, pack build, mod list, launch; it and
  `src/gameai/windows.py` pick WSL or native Windows paths at import
- `src/twwarhammer3/engine/startup.py`: the startup video skip
- `src/twwarhammer3/engine/pack.py`: PFH5 packs: build the mod pack, list and extract
  vanilla packs
- `src/twwarhammer3/engine/mailbox.py`: the bridge files; its docstring is the observation
  reference
- `src/twwarhammer3/engine/doctor.py`: the read-only launch check (`doctor`)
- `src/twwarhammer3/engine/windows_capture.py`: passive stills, run by Windows Python
- `src/twwarhammer3/engine/checkpoint_agent.js`: the checkpoint Frida agent
- `src/twwarhammer3/engine/checkpoint_frida.py`: runs the checkpoint Frida agent in the
  owned game (Windows side)
- `src/twwarhammer3/engine/link.py`: native multiplayer: the coordinator's link
- `src/twwarhammer3/engine/worker.py`: native multiplayer: per-client worker, typed lobby
  operations, readiness and leave; contracts in its docstring and multiplayer-tools.md
- `src/twwarhammer3/engine/multiplayer_probe.py`: bounded Windows reference capture;
  checks the actual process image and runs the passive multiplayer discovery agent
- `src/twwarhammer3/engine/multiplayer_probe.js`: passive deployment/command traces,
  completed-tick checksums, raw unit witnesses, phases and outcome
- `src/twwarhammer3/engine/multiplayer_adapter.py`: Windows Frida helper and stdin requests
  for direct deployment readiness, plus passive capture
- `src/twwarhammer3/engine/multiplayer_adapter.js`: fixed readiness sender on the game thread;
  phase/layout guards and submission evidence; unverified

`src/twwarhammer3/mod/`, Lua scripts packed into the game:
- `src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua`: the battle script:
  publishes observations, applies orders
- `src/twwarhammer3/mod/script/frontend/mod/twwarhammer3_frontend.lua`: frontend menus
- `src/twwarhammer3/mod/script/_lib/mod/twwarhammer3_ui.lua`: UI steps
- `src/twwarhammer3/mod/script/_lib/mod/twwarhammer3_json.lua`: JSON
- `src/twwarhammer3/mod/script/_lib/mod/twwarhammer3_imagery.lua`: the stills camera
- `src/twwarhammer3/assets/`: the blank startup clip and its MIT license

`src/twwarhammer3/battle/`, jobs and controllers:
- `src/twwarhammer3/battle/play.py`: job loop: launch, setup, episodes, rematch, register row
- `src/twwarhammer3/battle/benchmark.py`: initial mirror evaluator, limits, plans and reports
- `src/twwarhammer3/battle/suite.py`: the coordination suite: arms, plans, measures and comparison
- `src/twwarhammer3/battle/support_timing.py`: infantry/cavalry timing diagnostics and fresh-launch plan
- `src/twwarhammer3/battle/support_evidence.py`: offline event brackets and proposed numerical contrast
- `src/twwarhammer3/battle/manual_demo.py`: separate owner demonstration recorder and pause labels
- `src/twwarhammer3/engine/manual_capture.py`: passive Windows video and state journal for demonstrations
- `src/twwarhammer3/battle/reference.py`: `Concentrate`, the suite's scripted coordinated reference
- `src/twwarhammer3/battle/setup.py`: scenarios with `base` inheritance, lobby steps,
  benchmark checks; its docstring is the scenario field reference
- `src/twwarhammer3/battle/controllers.py`: policy names, model prompts, rotation, outside
  controllers
- `src/twwarhammer3/battle/llm.py`: direct API-model controller: llm, llm_rules
- `src/twwarhammer3/battle/commander.py`: asynchronous API model over skills
- `src/twwarhammer3/battle/skills.py`: per-unit skill executor, probe_abilities
- `src/twwarhammer3/battle/scripted.py`: hold, attack_nearest, rush_nearest
- `src/twwarhammer3/battle/evade.py`: `Evade`, a free control: every unit runs from visible enemies
- `src/twwarhammer3/battle/cannae.py`: `Envelop`, `WingSupport`, `CentreSupport`: scripted
  Cannae development witnesses on public state
- `src/twwarhammer3/battle/reserve.py`: battle B's private reserve draw, and the waves profile
  (version 3) that holds and releases enemy groups, kept apart from the public battle state
- `src/twwarhammer3/battle/wall_defence.py`: `WallWitness` and its controls for the walled siege
  defence (cth-emp-siege-a-v1), on public state
- `src/twwarhammer3/battle/wall_readings.py`: that siege's evaluator readings of finished
  battles: holders, tickets, sightings, ammunition, breach, reserve response, damage releases
- `src/twwarhammer3/battle/escalade.py`: `Escalade` and its controls for the siege attack
  (ksl-emp-siege-a-v1), on public state with the siege orders
- `src/twwarhammer3/battle/escalade_readings.py`: that siege's evaluator readings of finished
  battles: reallocation by melee flags, entry routes, Lancer losses, wall to victory point
- `src/twwarhammer3/battle/team.py`: independent members sharing one army and one mailbox
- `src/twwarhammer3/battle/local_command.py`: C's local sensing and signal/courier router; the
  version 2 text mode, which checks every sender and recipient pair against the arm's links, and
  its muted form, which accepts texts and delivers none
- `src/twwarhammer3/battle/local_team.py`: C's regiment groups, model interface and free probes;
  version 2's peer, relay and overview arms, the muted controls (peer or overview to their
  members, nothing delivered) and the unlinked one (no links, no messages), the commander and its
  stage-1 probes
- `src/twwarhammer3/battle/local_scripts.py`: scripted C v2 witnesses (peer, relay and overview)
  and foils (fixed schedule, central concentration, `ThinkingRush`) for the
  communication-structure stage 2; each sleeps a model-like think time per decision
- `src/twwarhammer3/battle/configured.py`: JSON controller composition; a version 2 star arm's
  `local_team` node takes the commander, whose model leaf gets its own prompt
- `src/twwarhammer3/battle/graph.py`: resumable graph nodes
- `src/twwarhammer3/battle/skill_contracts.py`: typed skills and public effect witnesses
- `src/twwarhammer3/battle/graph_goals.py`: background model target preferences over fixed
  graphs
- `src/twwarhammer3/battle/graph_author.py`: offline multi-LLM authoring and whole-battle
  revision
- `src/twwarhammer3/battle/graph_initiation.py`: temporary pre-contact attack-path check
  for caller-declared initiators
- `src/twwarhammer3/battle/graph_view.py`: recorded graph/battle inspection
- `src/twwarhammer3/battle/graph_view_assets/`: the graph view's page, script and style
- `src/twwarhammer3/battle/checkpoint.py`: battle checkpoints: save, fast checked rebuild,
  live handover; the checkpoint-RL step run, library records and attempt statuses
- `src/twwarhammer3/battle/candidates.py`: checkpoint RL: the public candidate set
- `src/twwarhammer3/battle/audit.py`: checkpoint RL: branch audits
- `src/twwarhammer3/battle/rl.py`: checkpoint RL: tasks, methods, evaluation (model side)
- `src/twwarhammer3/battle/confirm.py`: checkpoint RL: the closed loop
- `src/twwarhammer3/battle/calibration.py`: disclosed scenario diagnostics
- `src/twwarhammer3/battle/cards.py`: tactic cards: foils, witness, admission rule, board and
  verdict; backs `card`
- `src/twwarhammer3/battle/capture.py`: 1 Hz replay recorder and stills
- `src/twwarhammer3/battle/export.py`: offline model decisions, exchanges and provenance
- `src/twwarhammer3/battle/digest.py`: trace summaries
- `src/twwarhammer3/battle/watch.py`: follow a job
- `src/twwarhammer3/battle/stats.py`: results register
- `src/twwarhammer3/battle/report.py`: paired statistics
- `src/twwarhammer3/battle/report_html.py`: the offline HTML report
- `src/twwarhammer3/battle/replay.py`: the report's replay: public recorded frames and events
- `src/twwarhammer3/battle/report_assets/`: the report's page, script, style and replay
- `src/twwarhammer3/battle/peers.py`: native multiplayer: Lua-observation comparison and
  completed-tick/raw-witness comparison (`compare-peers --native`)

`configs/twwarhammer3/`:
- `configs/twwarhammer3/system_prompt.md`: the llm prompt
- `configs/twwarhammer3/rules_prompt.md`: the llm_rules prompt
- `configs/twwarhammer3/commander_prompt.md`: the commander prompt
- `configs/twwarhammer3/tips_prompt.md`: the suite's `tips` arm: the rules prompt plus "How to
  fight"
- `configs/twwarhammer3/local_command_prompt.md`: battle C's local commander prompt
- `configs/twwarhammer3/cannae_shared_plan.md`: battle C's shared prebattle plan
- `configs/twwarhammer3/cannae_shared_plan_v2.md`: the shared plan of C's version 2 arms,
  without the channel paragraphs
- `configs/twwarhammer3/local_captain_prompt.md`: the captain prompt of C's version 2 arms
- `configs/twwarhammer3/local_commander_prompt.md`: the commander prompt of C's relay and
  overview arms
- `configs/twwarhammer3/local_topology_rules.json`: the rules section each version 2 arm adds
  for captains and the commander (muted uses peer's, muted_overview overview's)
- `configs/twwarhammer3/graph_goal_prompt.md`: the graph target-preference prompt
- `configs/twwarhammer3/graphs/`: graph controller files
- `configs/twwarhammer3/controllers/`: battle C's `configured` controller files
- `configs/twwarhammer3/scenarios.json`: declared scenarios
- `configs/twwarhammer3/custom_battle.json`: random draws
- `configs/twwarhammer3/report_notes.json`: the report's scenario, unit and highlight text
- `configs/twwarhammer3/benchmark_jobs.json`: the jobs the report and export read
- `configs/twwarhammer3/gcp-regions.json`: the quoted region prices `scripts/wh3_gcp.py` reads

`src/gameai/`, game-neutral code both games import:
- `src/gameai/llm.py`: model API calls for any game: transport, spend and the reply-retry loop
- `src/gameai/providers.py`: declared model routes (OpenAI, OpenRouter, Anthropic)
- `src/gameai/ledger.py`: append-only spend ledgers with a hard budget
- `src/gameai/provenance.py`: source provenance for attributable evidence
- `src/gameai/sft.py`: supervised fine-tuning datasets from both games' decision exports
- `src/gameai/lm.py`: candidate scoring with local language models (WH3 checkpoint RL)
- `src/gameai/windows.py`: Windows game processes owned from WSL or native Windows Python:
  one controller lock, a supervised launch, probes
- `src/gameai/windows_game.py`: owns one Windows game process and stops it on controller EOF
  or a hard time limit

`scripts/`:
- `scripts/check.py`: the exit gate: Ruff, the whole offline suite and risky-edit warnings
- `scripts/githooks/pre-commit`: refuses a commit unless check.py passed on this tree
- `scripts/hooks/pre_bash.py`: Claude Code hook: refuses `ruff format` and HEAD moves while
  a WH3 queue runs
- `scripts/hooks/stop_check.py`: Stop hook: runs check.py when the tree changed since its
  last pass
- `scripts/wh3_queue.py`: runs a frozen plan of `twwarhammer3 play` jobs one at a time
- `scripts/wh3_gcp.py`: previews or creates one expiring GCP game host, trying priced regions
  on capacity errors
- `scripts/gcp/`: the GCP host's first-boot script and its deadline cleanup workflow
- `scripts/wh3_db.py`: reads rows of a WH3 database table from the game's db.pack
- `scripts/wh3_reserve_cells.py`: one row per reserve episode and a tally per cell, from saved jobs
- `scripts/refusal_sweep.py`: removes one refusal at a time and lists those no test catches
- `scripts/diagram_files.py`: the page's file lists, from these lists and the map's boxes
- `scripts/diagram_examples.py`: small excerpts of a recorded battle for the page's stories,
  and the whole GaP battle its graph replay plays
- `scripts/sft_smoke.py`: a minimal local LoRA fine-tuning smoke test (CUDA only)
- `scripts/inventory_scenarios.py`: Spire first combat: the development inventory
- `scripts/audit_language_training.py`: Spire first combat: audit of saved SFT evidence
- `scripts/audit_ppo_training.py`: Spire first combat: audit of saved PPO evidence
- `scripts/export_relabel_datasets.py`: Spire first combat: heuristic-relabel datasets
- `scripts/offline_agreement.py`: Spire first combat: a frozen language policy's agreement
  with heuristic labels
- `scripts/plot_results.py`: Spire first combat: plots of saved reports and PPO diagnostics
- `scripts/train_language.py`: Spire first combat: one local SFT job
- `scripts/train_language_rl.py`: Spire first combat: one outcome-based language
  post-training job

## Commands

```bash
# Play: a new --output, a clean source scope; model policies need --budget-usd, the
# ledger's cumulative cap ($52 OpenAI; OpenRouter $50 and Anthropic $200 across both games)
uv run python -m twwarhammer3 play --policy llm --budget-usd USD --scenario random --seed N \
    --output runs/twwarhammer3/battle/llm-luna-vN-rand-N-YYYYMMDD
uv run python -m twwarhammer3 play --policy commander --budget-usd USD --scenario kho5-dwf5 \
    --episodes 3 --output runs/twwarhammer3/battle/commander-luna-vN-kho-YYYYMMDD
uv run python -m twwarhammer3 play --scenario brt-cavalry-emp-assault \
    --policy llm_rules,attack_nearest,rush_nearest --model gpt-6-sol --budget-usd USD \
    --rotation-seed N --output runs/twwarhammer3/battle/bench-bN-<purpose>-YYYYMMDD
uv run python scripts/wh3_queue.py PLAN.json      # a frozen plan of play jobs, one at a time
# Benchmark plans: `plan` writes a queue plan and plays nothing; `report` reads its results
uv run --locked python -m twwarhammer3 benchmark plan PLAN.json [--stage pilot|model]  # benchmark-initial.md
uv run --locked python -m twwarhammer3 benchmark plan PLAN.json --stage suite \
    --scenarios A,B --arms rush,single  # benchmark-run.md
uv run --locked python -m twwarhammer3 benchmark report PLAN.json
uv run --locked python -m twwarhammer3 graph-author --task TEXT --budget-usd USD --output DIR  # paid; gap-plan.md
# Follow and review
uv run python -m twwarhammer3 watch [JOB]                 # live beside the game; --prompts
uv run python -m twwarhammer3 watch JOB --next            # wait for an episode, stall or end
uv run python -m twwarhammer3 digest JOB[/episode-NNNN]   # per-episode table, or one battle
uv run python -m twwarhammer3 digest JOB/episode-NNNN --at SECONDS  # one decision in full
uv run python -m twwarhammer3 digest JOB[/episode-NNNN] --units  # unit fates and refusals
uv run python -m twwarhammer3 graph-view JOB [JOB ...] --output runs/twwarhammer3/reports/graphs.html
uv run python -m twwarhammer3 stats                       # results.csv by scenario and controller
uv run python -m twwarhammer3 card chariot [JOB_OR_PLAN_DIR ...]  # board; add paths for a verdict
uv run python -m twwarhammer3 report JOB [JOB ...] --output runs/twwarhammer3/reports/NAME
uv run python -m twwarhammer3 export JOB [JOB ...] --output runs/twwarhammer3/exports/NAME
uv run python -m twwarhammer3 spend                       # OpenAI; --provider for the others
# Runtime and probes
uv run python -m twwarhammer3 doctor                      # read-only: pins, preferences, game
uv run python -m twwarhammer3 launch                      # build, install, run until Ctrl-C
uv run python -m twwarhammer3 menu --dump 4               # UI tree of the screen (ui_tree.txt)
uv run python -m twwarhammer3 menu [--battle] --steps steps.json  # tails menu.log or mod.log
uv run python -m twwarhammer3 pack --list PACK            # --extract PACK NAME; bare: build
uv run --locked pytest -ra tests/twwarhammer3              # Lua and image tests; show skip reasons
uv run --locked python tests/twwarhammer3/check_wh3_checkpoint.py --output runs/twwarhammer3/checkpoint-check-NAME  # 4 launches
# Native multiplayer: usage/limits in multiplayer-tools.md; live evidence remains unverified
uv run python -m twwarhammer3 coordinator --match M --attempt A1 --clients A,B  # stdin: {"client", "body"}
python -m twwarhammer3 worker --coordinator URL --token-file F --match M --attempt A1 --client A --mode observe
uv run python -m twwarhammer3 compare-peers runs/twwarhammer3/native-multiplayer/M/A1  # offline
uv run python -m twwarhammer3 compare-peers --native A=runs/CAPTURE_A/native.jsonl B=runs/CAPTURE_B/native.jsonl  # offline
uv run --locked --extra llm python -m twwarhammer3 rl PHASE PLAN --output ...  # checkpoint RL (checkpoint-rl-plan.md)
```

- `--model` (default `gpt-6-luna`) and `--effort` (default `low`) pick the API model of
  `llm`, `llm_rules` and `commander`. A model policy can name its own instead, so one job
  rotates several models: `llm_rules@gpt-6-luna` or `llm_rules@gpt-6-luna/medium`. The key
  comes from `OPENAI_API_KEY` or the file named by `SPIRE_OPENAI_KEY_FILE` (the shared
  `gameai.llm` keeps Spire's name).
- `--provider openrouter` selects GLM-5.3 by default and the separate OpenRouter ledger.
  Models/efforts and key-file setup: [OpenRouter](controllers.md#openrouter).
  `spend --provider openrouter` prints that ledger.
- `--provider anthropic` selects Claude Haiku 5.5 by default and
  `runs/twwarhammer3/anthropic-spend.jsonl`. Models, key file and the workspace variable:
  [Anthropic](controllers.md#anthropic). Five Haiku mirror battles completed;
  [results and limits](benchmark-initial.md#first-screen-2026-11-02).
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
  first job that fails (or the second in a row with `keep_going`) or whose rematch started
  with a changed roster, strength, loadout or resources; a `PLAN-stop` file or the plan's
  `start_before` time ends it between jobs.
- `launch` and `play` install a startup-video skip that persists for ordinary Steam
  launches: `data/zzz_twwarhammer3_skip_intro.pack` in the game folder and
  `fe_game_intro_video_enabled false` in the game's preferences. To reverse it, stop WH3,
  delete the pack and set the preference back to `true`; the next project launch
  reinstalls both ([details](integration.md#packs-and-loading)).

## The loop

Compare versions or controllers on paired battles: one job rotating the controllers on a
declared scenario (since 2026-10-16 mostly small focused scenarios; the earlier
`--scenario random --seed N` draws are superseded, see
[owner direction](../owner-direction.md)). A rematch replays the same battle, so a
deterministic controller's rematches are not independent samples. Review the battles,
make at most one change to the prompt, rendering, memory or executor, and log the version
in [log.md](log.md). The review is the `wh3-version-review` workflow
(`.claude/workflows/wh3-version-review.js`): a reviewer per episode reads the digest and
the prompts and replies at the turning points (`digest EPISODE --at SECONDS`), three
proposers each suggest one change (tactics prompt, state and memory, order interface)
with the version history and the baseline in view, and three judges score them against
"No change" (collect more evidence first), which wins when a few battles cannot separate
a flaw from noise. It returns the judges' pick as a proposal; a run where any step returned
nothing, or a judge picked a title no candidate has, is `incomplete`, not a result. While it
runs, play more seeds with the same version and draft the next change in a git worktree:
a job stops if its source scope changes. Note each job's start and stop in
[Active work](../state.md#active-work). The WH3 ledger (`runs/twwarhammer3/llm-spend.jsonl`)
is separate from Spire's, with its own cap: $25, raised to $52 on 2026-10-16.

## Next

Status and next steps are on [state.md](../state.md#total-war-warhammer-iii); the new
Land Battle work follows the [release route](benchmark-implementation.md#phases).
[Tactic-card](tactic-cards.md) and [Empire](empire.md) screens are development history.
This section keeps only what is deferred.

Deferred: the custom `emp-battery-skv-evacuation` pilot (its
[placement diagnosis](log.md#2026-10-16-evacuation-deferred-controller-version-labels-fixed)),
siege-attack controls, and separate workload, prompt-length, useful-history,
representation and observation-age experiments. More units do not isolate a context-length
effect. The older random-draw comparison still has seeds 264482191, 1355466036 and
238913231 left, then Sol and Astra as commander; it is not the current priority.
Other candidates remain in [controllers.md](controllers.md#candidate-changes-for-the-next-version)
and [battle-types.md](battle-types.md#next). The `wh3-fire-report` and `wh3-v4-info` drafts
are archived as tags `archive/wh3-fire-report` and `archive/wh3-v4-info`; both predate the
v13 interface and need review before reuse.

Deferred cleanups:
- Keep public realtime fields/guards and session activation switches: removing them is
  a compatibility change, not dead-code cleanup. Future Lua refactoring should follow a
  demonstrated problem and its repeatable check. API candidates and the focused discovery
  recipe are in [integration.md](integration.md#finding-another-capability).
- `LLMPolicy.acknowledge` keeps its fallback for acknowledgements without `index`
  (traces before `863d10b`); dropping it is the owner's call.
