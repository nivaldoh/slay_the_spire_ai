# Battle controllers

One page for every WH3 battle controller: what is built, how to run and compare it, and
the researched designs not built yet. Started 2026-10-13 from a research summary the
owner obtained from ChatGPT 6 Astra Pro; its citations were checked where noted under
[Sources](#sources-and-caveats).

## The problem

The direct controller (`--policy llm`) asks the model for raw orders and blocks on each
call. Luna at low effort takes 4-11 s, during which the observations that arrive are
dropped, so every order rests on a state several seconds old. Most documented losses are
execution failures:
- units idle after their target dies;
- shooters walk at targets out of range;
- the lord arrives alone;
- units run everywhere.

See the README's [first-night](README.md#what-the-first-night-showed-2026-10-13) and
[mirror](README.md#what-the-mirror-battles-showed-2026-10-13-second-session) sections. Pausing during inference is
excluded by the owner (battles always run unpaused at 1x).

Two points from the research summary shape the designs below:
- **Freshness and throughput are different.** Staggering several model calls gives more
  decisions per minute, but each still rests on a state several seconds old. What
  improves *observation age at execution* is a fast layer acting on the newest state
  while the model thinks. That age is the battle time an order is applied minus the
  battle time of the state it came from.
- **A slow planner is fine when its output outlives its latency.** "Keep the shooters
  behind the infantry and fire at the largest block" stays useful for tens of seconds.
  "Move f3 to (120, -40) now" does not.

## Implemented

| Policy | Who decides | Order latency | Notes |
|---|---|---|---|
| `attack_nearest` | script | one mod tick (~0.25 s) | every unit attacks its nearest visible enemy; the floor to beat |
| `llm` (v1-v14) | API model, every decision, blocking | 4-11 s with Luna low | raw orders; prompt `configs/twwarhammer3/system_prompt.md`; history in [log.md](log.md) |
| `skills` (executor v1.2) | scripted executor, class defaults | one mod tick | no model; `battle/skills.py` |
| `commander` (v2) | API model sets standing assignments asynchronously; the executor acts on every observation | executor one mod tick; plans several seconds | `battle/commander.py`, prompt `configs/twwarhammer3/commander_prompt.md` |

### `skills`: persistent unit skills

Each unit holds an assignment `{skill, target, x, z}` until it is replaced. On every
observation, its skill turns the fresh state into the order the unit should have. An
order goes out only when it differs from the last one sent, or when the last one
lapsed and was sent at least 2 battle seconds ago. An order lapses when the engine
dropped it or never started it; an attack also lapses when the game switched the
target, left the unit idle, or the unit stands without a target. A unit moving with no
target and no move destination is still carrying the attack out.

The skills:
- **engage**: melee. Its target choice, in order:
  1. the enemy lord fighting within 40 m;
  2. the assigned target;
  3. the target it was last sent at, or is fighting;
  4. the nearest live enemy.

  It walks, and runs only for the last 30 m.
- **shoot**: fires at enemies in range that are not in melee, unless the commander named
  the target. Its target order:
  1. the assigned target;
  2. the target it was last sent at, or is shooting;
  3. infantry, cavalry and monster blocks before missile units and artillery, largest first.

  It walks to a firing spot first if one is given. With nothing in range it closes on a
  target, unless it has a firing spot or is artillery. It sends a single halt rather
  than shoot into melee. Out of ammunition, artillery stays idle and other shooters
  charge. A target in range that draws no shot (ammunition unchanged) for 15 s, or 30 s
  for artillery, is skipped for 30 s (`55ab6b3`, after Skaven skirmishers chased
  chariots without firing).
- **hold**: keeps a post and fights enemies within 40 m of it.
- **charge**: waits, at a post if one is given, until its target or any enemy is in
  melee with our units, then charges. Mounted units run all the way. This is the lord
  and cavalry rule from the direct controller's prompt.
- **move**: goes to a point, also out of melee. A move the engine rejects as unreachable
  turns into holding where the unit stands.

Targets stick to the executor's own last order, not the observed target: the
observation published with an acknowledgement still shows the previous target, and
following it made the first smoke's Skullcannon switch targets every tick without
firing. An attack the game switched to another enemy is sent again after 2 s, except in
melee.

Defaults by class:
- missile infantry, artillery and missile chariots (the Skullcannon) shoot;
- the lord, heroes and all cavalry, including the axe horsemen, charge;
- everything else engages.

The executor never queues orders and leaves behaviour toggles alone.

### `commander`: asynchronous API model over the skills

One plan request is in flight at a time, on a worker thread, so `decide` never waits.
Planning runs back to back, each request built from the latest state. On each
observation the commander:
1. adopts a finished plan against the current state;
2. runs the executor;
3. starts the next request if none is in flight.

Checks on adoption:
- assignments for dead or unknown units are dropped;
- a dead or unknown target is cleared;
- a `move` without a point is dropped;
- `shoot` for a unit without missiles is dropped;
- a target that is out of sight is kept (the skill falls back until it reappears);
- abilities are revalidated and sent once.

Drops and engine rejections are reported in the next prompt. Units the plan omits keep
their assignment, and until the first plan arrives units follow their class defaults.

What is recorded:
- `result.json` `llm` holds the API totals plus `plans` and `plan_age_ms`; mean plan age
  is `plan_age_ms / plans`.
- Each adoption's trace decision carries `plan`, `plan_age_s`, `dropped`, `reason` and
  `notes`, and each request carries its `prompt`.

Both new policies decide at the mod's tick rate (about 3-4 decisions per second), so the
trace keeps every decision with orders, an error or new metadata, and quiet ones once
per `--observe-ms`. `digest` prints only decisions with orders or a model's reason, and
shows each adopted plan with its age. Commands: [README](README.md#commands).

## Comparing controllers

The results register has a `policy` column. `model` and `effort` are filled only for the
model-driven policies (`llm`, `commander`), and the harness version still comes from the
job name (`-vN-`), counted separately per policy. A comparison should use:
- the same random seeds for every controller (paired draws, one job per seed); a
  deterministic controller plays each seed once, since a rematch replays the same battle;
- at least six seeds per controller (three separated nothing, on a fixed scenario or on
  paired draws);
- the same information boundary: enemies only while visible, no privileged state;
- the AI's stats modifier (1.1) noted, since it favours the enemy in mirrors.

| Variant | What it isolates |
|---|---|
| `llm` (current version), live | the baseline |
| `attack_nearest` | the scripted floor |
| `skills` | whether the executor is useful by itself |
| `commander` + Luna | whether high-level model decisions add value over the same executor |
| `commander` + Sol / Astra | whether better planning is worth its latency and cost once execution no longer waits |
| later designs below | one change at a time against the best of the above |

### Metrics

| Metric | Status |
|---|---|
| outcome, battle length, strength left on both sides, decisions, invalid orders, order delay, cost | recorded (`results.csv`) |
| plan count and mean plan age (state seen → plan adopted) | recorded (commander `result.json`) |
| order churn: orders per unit per minute | derivable from the trace; to add to `digest` |
| threat-to-response time: an enemy comes within 40 m of a free unit → that unit's next order | to add |
| idle units while a useful action exists: no target, no destination, enemy visible | to add |
| dropped or rejected assignments per plan | in the trace; to add to `digest` |
| losses weighted by unit value instead of men | to add (needs unit costs) |

### Model tiers for the commander

Prices are standard-tier USD per million tokens from `gameai.llm.PRICES` (read
2026-10-12). Measured latency and cost come from the smoke battles below. A call that
exceeds 60 s times out in `gameai.llm.post`.

Measured in one smoke battle each, on `kho5-dwf5` at low effort, 2026-10-13. Every call
sent about 3,500 input tokens, of which about 2,100 were cached.

| Model | Input / cached / output | Mean think s | Mean plan age s | Reasoning tokens per call | Plans (battle s) | Cost per call | Cost per battle |
|---|---|---|---|---|---|---|---|
| `gpt-6-luna` | 0.10 / 0.01 / 0.50 | 6.4 | 6.5 | 341 | 53 (355) | $0.0004 | $0.02 |
| `gpt-6.1-sol` | 2.00 / 0.10 / 10.00 | 5.8 | 6.0 | 25 | 41 (255) | $0.004 | $0.18 |
| `gpt-6-astra` | 10.00 / 1.00 / 50.00 | 4.8 | 5.1 | 10 | 59 (309) | $0.019 | $1.17 |

At low effort the stronger models were not slower: Sol and Astra reasoned very little.
Astra's first call took 12.5 s (its plan was 12.9 s old on adoption), and the later
ones were faster. Higher efforts will
reason more and take longer; measure them before relying on them. One battle per model
measures latency and cost, not strength.

## Watching a battle (owner request, 2026-10-13)

The owner wants to follow what the models receive and decide during a battle,
summarized, together with other useful context. Built in `9bfee82`:
- **`watch`** (`battle/watch.py`), a terminal view beside the game that tails the job's
  `trace.jsonl` and touches nothing in the game. It prints each model request with the
  battle time and both sides' strength of its state, and what it reports as dropped or
  rejected (`--prompts` prints it whole); each reply, a plan with its age, think time,
  cost and reason or the direct controller's orders and reason, and the notes when they
  change; engine rejections, a strength line every 30 s and each result.
- **`play --show`**, each model reply in the game's advisor window through
  `common.advice(text)`, sent as `say` with the orders in `orders.json`
  ([integration.md](integration.md#advisor-text-verified-2026-10-13)). The debug
  `bm:queue_advisor` call was not needed.

**Already stored per episode in `trace.jsonl`:**
- Commander: every request's full prompt (`prompt`, `prompt_sha256`), which includes the
  Assignments section with each unit's skill and current phase. Every adopted plan
  carries the assignments, abilities, the model's one-sentence `reason`, its running
  `notes`, dropped items, `plan_age_s` and `attempts` (raw reply text, token usage,
  seconds).
- Direct controller: the prompt, reason, notes and attempts for every decision.
- The API returns reasoning only as a token count, which is stored in the usage
  figures; the reasoning text itself is not returned.
- `digest` prints the plans with their age and reason after the fact. The commander has
  no model subagents yet; specialists are a later design below.

**Not built, to probe before choosing:**
1. **A text component of our own.** `uic:SetStateText(text)` on a component created or
   borrowed by the battle script; it needs a layout to attach to.
2. **Map markers.** `bm:add_ping_icon(x, y, z, type, waypoint, rotation)` and
   `remove_ping_icon` could mark plan points: charge posts, move and firing spots.

Both would pass their text or points through the mailbox like `--show`. Battles stay
unpaused at 1x.

**Other information worth showing, not shown yet:**
- each unit's phase and last order;
- a strength curve of both sides (`watch` prints only a line every 30 s);
- the enemy army composition as seen;
- kill counts per fire order (candidate branch `wh3-fire-report`).

## Designs not built yet

They are ordered by how much each is expected to teach for its cost. Each should be
tested against the best implemented controller, one change at a time.

1. **Event-triggered replanning.** Today the commander plans back to back, which is
   cheap with Luna and costly with Astra. Instead, plan on a timer (every 15-30 s) plus
   events, each with a cooldown:
   - a friendly unit routs or wavers;
   - the enemy lord enters melee;
   - a unit loses a set share of its men since the last plan;
   - an assignment completes (a move arrived) or its target dies.

   An event-triggered call is still a slow call, and the executor's own rules stay the
   immediate response. Source: React When You Need To (arXiv 2609.22587), which adapts
   the inference schedule of robot action policies to scene changes. First experiment:
   an Astra commander with timer and events against Astra planning back to back, on
   cost and outcome.
2. **Delay injection.** Hold each adopted plan back by a fixed battle-time delay (0.5,
   2, 5 and 10 s) to measure how sensitive outcomes are to plan age, independent of
   which model is used. This replaces the paused-inference diagnostic, which the owner's
   no-pause rule excludes.
3. **Richer skills from observed failures:**
   - a rear charge through a queued waypoint (the protocol supports a move followed by
     a queued attack);
   - shooters kiting with the `skirmish` toggle;
   - a lord escort or bodyguard skill (guard a friendly unit);
   - screening (stay between a friendly shooter and the nearest enemy).

   Add executor-level coordination too: a shared count of units on each enemy, so that
   defaults gang up rather than spread. Build each skill with a unit test and a live
   probe; check `unitcontroller` semantics first. For example, `withdraw()` leaves the
   battlefield (our protocol has no withdraw order, and `move` must stay a plain goto).
4. **Candidate-action selection.** Code builds a few feasible options per decision, such
   as three targets for each free unit with distance, enemy strength, who else is on it
   and estimated time to contact. The model picks by id and sets bounded parameters.
   This removes coordinate errors and is the path to a learned ranker (item 8).
5. **Specialists with bounded authority.** HIMA (arXiv 2508.06042, COLM 2025) coordinates
   imitation-trained specialists through a planner. Per the summary, the learned part is
   production and technology, while combat is rule-based. STRATA (arXiv 2609.38881, Red
   Alert) separates strategic, logistics and tactical agents and adds a post-match review
   agent. Two forms fit here:
   - before contact, two or three parallel advisers propose deployment plans, and the
     commander resolves them into one allocation;
   - in battle, a specialist owns a fixed set of units (the mounted units, or ability
     use), and never shares a unit with another model.

   Do this only after items 1-3 show which decisions the executor and commander still
   get wrong.
6. **A between-battle coach and code-as-policies skill development.** Code as Policies
   (arXiv 2209.07753) has a language model write programs with feedback loops that
   compose control primitives; STRATA distils matches into experience cards. Here, the
   autoresearch loop (`wh3-version-review` workflow) becomes the coach. Its reviews
   propose changes to skills (as tested code) and to the commander prompt, and live
   battles only select among tested skills, never generated code.
7. **Stronger models on the same executor.** Once the Luna commander is understood, run
   the paired-draw comparison for Sol and Astra (table above), at low and medium effort.
8. **A learned local policy.** A small shared network or action ranker, not a language
   model, scores candidates (item 4) from structured state and the unit's assignment. It
   is trained from logged battles, or from stronger-model labels checked by outcome, with
   delayed, variable and sometimes missing plans during training. Training-time action
   conditioning for real-time chunking (arXiv 2512.05964) is the precedent for training
   under inference delay. Later comes cooperative reinforcement learning (MAPPO) on
   bounded scenarios, which needs cheap resets. Today a rematch takes about 15 s and
   battles run at 1x, so experience accrues at roughly ten battles an hour.
9. **Precedents the commander already follows:**
   - AgileThinker (ICLR 2026): a planner and a reactive process run concurrently, and
     the reactive one uses the latest observation.
   - Real-time chunking (arXiv 2506.07339, NeurIPS 2025): keep executing while the next
     plan is computed, and hand over consistently with what is under way.
   - JEV-Star (arXiv 2609.27331): a fast action selector under persistent GPT-6 planning
     in StarCraft II. Its micro-combat wins rose only from 3 to 7 of 105 episodes, so the
     architecture alone does not produce skilled micro.

Interface gap that affects every controller: the mod reports flying units that are not
monsters, such as Harpies and the Feral Manticore, as infantry (`unit_class` in
`twwarhammer3_battle.lua` checks `can_fly` only for monsters and unknown classes), and
random draws bring many of them. Army abilities and ability readiness, missing until
`9bfee82`, are in the state now
([integration.md](integration.md#ability-state-through-the-ui-context-system-probed-2026-10-13)).

Not planned: per-unit language models, dynamic agent spawning, debates per unit, and
vision input. The structured state is already cleaner than screenshots.

## Sources and caveats

Abstract pages were checked on 2026-10-13 unless marked otherwise.

- SwarmBrain: an LLM sets strategy and a condition-response state machine handles local
  StarCraft II reactions. Shao et al., [arXiv 2401.17749](https://arxiv.org/abs/2401.17749).
- AgileThinker, ICLR 2026
  ([proceedings PDF](https://proceedings.iclr.cc/paper_files/paper/2026/file/ccbe16043125599293b01dd467c260f3-Paper-Conference.pdf)).
  Not opened.
- HIMA: Ahn, Kim and Choi, [arXiv 2508.06042](https://arxiv.org/abs/2508.06042). The
  abstract does not say whether the planner is learned. The summary's caveat (the learned
  actions concern production and technology; attacks and scouting are rule-based) was
  not checked.
- Code as Policies: Liang et al., [arXiv 2209.07753](https://arxiv.org/abs/2209.07753).
  Not opened.
- Real-time chunking: Black, Galliker and Levine,
  [arXiv 2506.07339](https://arxiv.org/abs/2506.07339). The summary cites "A2C2 / Leave
  No Observation Behind" with this same link; no separate A2C2 reference was given.
- Training-time action conditioning for real-time chunking: Black et al.,
  [arXiv 2512.05964](https://arxiv.org/abs/2512.05964).
- STRATA: Tian et al., [arXiv 2609.38881](https://arxiv.org/abs/2609.38881). In a fixed
  Red Alert scenario its experience cards raised the win rate from 30% to 100%. The
  abstract does not give the agents' observation scopes or update schedules.
- React When You Need To: Wu et al., [arXiv 2609.22587](https://arxiv.org/abs/2609.22587).
  It concerns real robots, not games.
- JEV-Star: Ma et al., [arXiv 2609.27331](https://arxiv.org/abs/2609.27331). The 0.422 s
  median for action selection and the 3-to-7 of 105 micro wins are on the abstract page.
  The summary's 27.6 s planning median, and how the micro tests advanced the simulation,
  are not.
- AlphaStar: Vinyals et al., Nature 2019. Its skill came from imitation and multi-agent
  reinforcement learning, not from a hierarchy of conversational models.
- MAPPO: Yu et al., NeurIPS 2022 Datasets and Benchmarks.
- [OpenAI latency guide](https://developers.openai.com/api/docs/guides/latency-optimization):
  fewer output tokens and round trips, and a stable prompt prefix for caching.
- WH3 scripting documentation for
  [battle_unit](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_unit.html)
  and [battle_unitcontroller](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_unitcontroller.html).
