# Total War: WARHAMMER III battles

The benchmark draft starts with small mixed-army **Land Battles** against the game AI.
The intended scope also includes Siege, Survival, Ambush and Conquest; other types await
confirmation (owner, 2026-10-28). Health and morale are the tentative primary measures;
scoring and checks remain open. The engine decides the winner, including timer endings
(owner, 2026-10-23). Scripts, models and hybrids use structured state while the benchmark
battle runs unpaused at 1x; actual delay, cost and failures accompany outcomes.
Start with the [definition and first profile](benchmark.md#the-first-battle)
and [implementation plan](benchmark-implementation.md#phases). The profile and new
checks remain proposals; the existing readers do not yet implement this definition.
The [tactic cards](tactic-cards.md) retain their historical rules and evidence.
Controller research, team recovery and training are related work with separate evidence
requirements. What is running and the versions on `main`: [../state.md](../state.md);
every version, job and finding: [log.md](log.md).

The owner's initial modding guide (8 October 2026) set the first shape. This page and
[integration.md](integration.md) supersede it, and git keeps it:
`git show 001d1ce:docs/twwarhammer3/guide.txt`.

## Pages

| Page | Read it for |
|---|---|
| [integration.md](integration.md) | engine facts: packs, menus, lobby settings, unit API, context system, battle types, capture |
| [controllers.md](controllers.md) | the policies and their versions, comparing them, candidate changes, designs not built |
| [battle-types.md](battle-types.md) | the battle-type scenarios, the `mode` state, the `build` and `reinforce` orders |
| [benchmark.md](benchmark.md) | the Land Battle benchmark definition: scope, the proposed first battle, outcome and score, measurements, comparison, observations, orders, timing, scenarios and terms |
| [benchmark-implementation.md](benchmark-implementation.md) | building it: phases, the owner interview, proposed checks, measurement gaps, what the current report code does, research, later work and earlier plans |
| [evaluation-guidelines.md](evaluation-guidelines.md) | research-based evaluation guidelines: task design, failure accounting, statistics, human/LLM review, proposed code checks and publication |
| [tactic-cards.md](tactic-cards.md) | historical chariot rule, tactic-card design, candidate screens and their evidence |
| [latency.md](latency.md) | the latency program (2026-10-18 plan): knowing a tactic against executing it in time, measures, robotics framing, harness ladder, fine-tuning path |
| [robotics.md](robotics.md) | robotics ideas and concrete comparison designs: parameterized/generated policies, learned micro, controller boundaries and codebase fit |
| [../thesis/](../thesis/proposal.md) | the proposed master's thesis (moved 2026-10-27): proposal, candidate directions, related work and the earlier memory proposal |
| [robot-team-research.md](robot-team-research.md) | research guide: capability allocation, recovery, delayed plans, evaluation and learning; what each source suggests for WH3 and where it does not transfer |
| [robot-team-plan.md](robot-team-plan.md) | staged Empire experiment plan: establish useful recovery, compare allocation, then test delayed plans or learning; evidence, measures and stop conditions |
| [multi-agent-plan.md](multi-agent-plan.md) | proposed evaluation of independent teammates: split army, single-client steps, native team battles and multiplayer campaigns; contracts, comparisons, checks and stages |
| [native-multiplayer.md](native-multiplayer.md) | initial native team-battle assessment: unattended versus headless clients, synchronization probes, cloud costs and risks |
| [team-structures.md](team-structures.md) | who commands which units: one model per class, per unit or per planner-made group, the call schedule, costs, code, stages and the views of team behaviour |
| [multi-agent-implementation.md](multi-agent-implementation.md) | the scripted split-army team (`team.py`) as built, its agreed checks, and the next code for a model team |
| [gap-plan.md](gap-plan.md) | initial graph controllers: frozen skills, interchangeable members, authoring/revision commands, checks, evidence and deferred research |
| [../multi-agent.html](../multi-agent.html) | an animated diagram of the play loop, the team, native multiplayer and the factory: boxes, wires and step-by-step flows, each claim with its source. GitHub shows its source; open it in a local browser by pasting `\\wsl.localhost\Ubuntu\home\niv\repos\slay_the_spire_ai\docs\multi-agent.html` |
| [empire.md](empire.md) | the Empire set (2026-10-20): why one faction, the Empire scenarios from one unit to 20 v 20, the line battle for the robot-team question, the night's decisions and risks |
| [small-scenarios-2.md](small-scenarios-2.md) | second batch of small scenario candidates (S8-S13): rosters, database facts, hypotheses |
| [benchmark-run.md](benchmark-run.md) | running paired benchmark trials, outside controllers |
| [reports.md](reports.md) | the offline HTML report and replay, its curated notes |
| [traces.md](traces.md) | offline model-decision exports, reasoning capture and data provenance |
| [checkpoints.md](checkpoints.md) | battle checkpoints: save a battle, restore it exactly, the agreed check and limits |
| [checkpoint-rl.md](checkpoint-rl.md) | short-episode RL research handoff: a proposed local candidate chooser, integration risks, numerical tests and live checks |
| [checkpoint-rl-plan.md](checkpoint-rl-plan.md) | the implementation plan for RL from restored checkpoints with a reverse curriculum: design decisions, code changes, staged checks, detectors and owner decisions |
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

Moved from AGENTS.md on 2026-10-29 (light factory docs cleanup).

```
src/twwarhammer3/  Total War: WARHAMMER III custom battles
  __main__.py      CLI: doctor, pack, launch, menu (runtime and UI probes); play, digest,
                   watch, card, stats, report, export, spend (jobs and offline evidence);
                   coordinator, worker, compare-peers (native multiplayer)
  protocol.py      Order types and validation, the error taxonomy; observations stay dicts;
                   it changes freely (Spire's protocol.py is byte-stable)
  engine/          runtime (pins, pack build, mod list, launch), startup (video skip), pack
                   (PFH5), mailbox (bridge files; its docstring is the observation
                   reference), doctor, windows_capture.py (passive stills, Windows Python),
                   checkpoint_agent.js and checkpoint_frida.py (the checkpoint Frida agent)
                   link.py and worker.py (native multiplayer: the coordinator's link and
                   the per-client worker); runtime.py and gameai/windows.py pick WSL or
                   native Windows paths at import
  mod/             Lua scripts packed into the game: battle, frontend menus, and in _lib/
                   UI steps, JSON and twwarhammer3_imagery.lua (the stills camera)
  assets/          The blank startup clip and its MIT license
  battle/          play.py (job loop: launch, setup, episodes, rematch, register row),
                   setup.py (scenarios with `base` inheritance, lobby steps, benchmark
                   checks; its docstring is the scenario field reference), checkpoint.py
                   (battle checkpoints: save, fast checked rebuild, live handover; the
                   checkpoint-RL step run, library records and attempt statuses),
                   candidates.py, audit.py, rl.py, confirm.py (checkpoint RL: the public
                   candidate set, branch audits, tasks/methods/evaluation, closed loop),
                   controllers.py
                   (policy names, model prompts, rotation, outside controllers), llm.py
                   (direct API-model controller: llm, llm_rules), commander.py
                   (asynchronous API model over skills), skills.py (per-unit skill
                   executor, probe_abilities), scripted.py (hold, attack_nearest,
                   rush_nearest), team.py (two scripted members sharing one army),
                   configured.py (JSON controller composition), graph.py (resumable graph
                   nodes), skill_contracts.py (typed skills and public effect witnesses),
                   graph_author.py (offline multi-LLM authoring and whole-battle revision),
                   calibration.py (disclosed scenario diagnostics),
                   cards.py (tactic cards: foils, witness, admission rule, board and
                   verdict; backs `card`), capture.py (1 Hz replay recorder and stills),
                   export.py (offline model decisions, exchanges and provenance),
                   digest.py (trace summaries), watch.py (follow a job), stats.py
                   (results register), report.py (paired statistics), report_html.py,
                   replay.py and report_assets/ (the offline HTML report and its replay),
                   peers.py (native multiplayer: what two clients observed, compared)
configs/twwarhammer3/
                   system_prompt.md (llm), rules_prompt.md (llm_rules),
                   commander_prompt.md, scenarios.json, custom_battle.json (random draws),
                   report_notes.json (the report's scenario, unit and highlight text),
                   benchmark_jobs.json (the jobs the report and export read)
```

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
# Follow and review
uv run python -m twwarhammer3 watch [JOB]                 # live beside the game; --prompts
uv run python -m twwarhammer3 watch JOB --next            # wait for an episode, stall or end
uv run python -m twwarhammer3 digest JOB[/episode-NNNN]   # per-episode table, or one battle
uv run python -m twwarhammer3 digest JOB/episode-NNNN --at SECONDS  # one decision in full
uv run python -m twwarhammer3 digest JOB[/episode-NNNN] --units  # unit fates and refusals
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
# Native multiplayer (native-multiplayer.md#implementation-status): unverified, no live use yet
uv run python -m twwarhammer3 coordinator --match M --attempt A1 --clients A,B  # stdin: {"client", "body"}
python -m twwarhammer3 worker --coordinator URL --token-file F --match M --attempt A1 --client A --mode observe
uv run python -m twwarhammer3 compare-peers runs/twwarhammer3/native-multiplayer/M/A1  # offline
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
  [Anthropic](controllers.md#anthropic). Unplayed in battle.
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
