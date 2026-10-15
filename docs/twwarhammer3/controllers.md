# Battle controllers

What each WH3 battle controller is, its current version, how to compare controllers, the
changes queued for the next version, and the researched designs not built yet. The
designs come from a research summary the owner obtained from ChatGPT 6 Astra Pro
(2026-10-13); its citations were checked where noted under
[Sources](#sources-and-caveats).

## The problem

The direct controller (`--policy llm`) asks the model for raw orders and blocks on each
call. Luna at low effort takes 4-11 s, during which the observations that arrive are
dropped, so every order rests on a state several seconds old. Most losses recorded in
[log.md](log.md) (v1-v12 and the mirror battles) are execution failures: units idle
after their target dies, shooters walk at targets out of range, the lord arrives alone,
units run everywhere. Pausing during inference is excluded: battles always run unpaused
at 1x.

Two points from the research summary shape the designs:
- **Freshness and throughput are different.** Staggering several model calls gives more
  decisions per minute, but each still rests on a state several seconds old. What
  improves *observation age at execution* (the battle time an order is applied minus the
  battle time of the state it came from) is a fast layer acting on the newest state
  while the model thinks.
- **A slow planner is fine when its output outlives its latency.** "Keep the shooters
  behind the infantry and fire at the largest block" stays useful for tens of seconds.
  "Move f3 to (120, -40) now" does not.

## Implemented

`battle/controllers.py` names them (`BUILTINS`, `MODEL_POLICIES`, `MODEL_PROMPTS`) and
records a card per trial (kind, class, source file and hash, model, effort, timing).

| Policy | Kind | Who decides | Version on `main` | Code, prompt |
|---|---|---|---|---|
| `hold` | scripted | nobody: never orders | | `scripted.py` |
| `attack_nearest` (walk-nearest) | scripted | every able unit attacks its nearest visible enemy, again when the engine drops the attack | | `scripted.py` |
| `rush_nearest` (run-nearest) | scripted | `attack_nearest`, running | | `scripted.py` |
| `skills` | scripted | the executor, every unit on its class default | executor v1.2 (`55ab6b3`) | `skills.py` |
| `probe_abilities` | scripted diagnostic | `skills`, plus every ability as soon as it is ready, the cheapest build on each usable slot and the cheapest affordable unit every 10 s | | `skills.py` |
| `llm` | model, blocking | the model, raw orders every decision | v15 | `llm.py`, `configs/twwarhammer3/system_prompt.md` |
| `llm_rules` | model, blocking | as `llm`, with a prompt that states objectives and interface without tactics (`51c1796`, b3) | | `llm.py`, `configs/twwarhammer3/rules_prompt.md` |
| `commander` | hybrid, asynchronous | the model sets standing skills; the executor acts on every observation | v3 | `commander.py` over `skills.py`, `configs/twwarhammer3/commander_prompt.md` |
| `package.module:Class` | outside | any class with `decide`, `acknowledge` and `metadata` | | [benchmark-run.md](benchmark-run.md) |

`llm` v15 and `commander` v3 are the log's
[Battle types, llm v15 and commander v3](log.md#2026-10-14-battle-types-llm-v15-and-commander-v3-overnight)
entry. The benchmark harness revisions then extended the rendered state and prompts
under their own labels (terrain in b2, morale and flight in b8), so benchmark jobs carry
`bN`, not `vN`. Comma-separated `--policy` names rotate within one job; `--delay-seconds` gives each
trial the newest observation at least that old (an added-age arm; the track label gains
`+age-<ms>`).

`tests/twwarhammer3/test_wh3_prompts.py` holds the exact rendered input of `llm` (whose
input `llm_rules` shares; only the system prompt differs) and `commander` for one compact
battle (`tests/twwarhammer3/prompts/*.txt`), the quickest way to see what each model
receives. A refactor must leave those bytes
unchanged; after an intended prompt or rendering change, regenerate them with
`WH3_WRITE_PROMPTS=1 uv run pytest tests/twwarhammer3/test_wh3_prompts.py` and log the
version.

### `skills`: persistent unit skills

Each unit holds an assignment `{skill, target, x, z}` until it is replaced; on every
observation its skill turns the fresh state into the order the unit should have. The
exact rules of the five skills (engage, shoot, hold, charge, move) and the class defaults
(`default_skill`) are in the `skills.py` docstring and constants, and the commander
receives them in `commander_prompt.md` ("Skills. These are the exact rules"). Behaviour
not written there:
- An order goes out only when it differs from the last one sent, or that one lapsed and
  was sent at least 2 battle seconds ago (`REPEAT_S`). An order lapses when the engine
  dropped or never started it; an attack also lapses when the game switched the target or
  left the unit idle or standing without a target. A unit moving with no target and no
  destination is still carrying the attack out.
- Targets stick to the executor's own last order, not the observed target: the
  observation published with an acknowledgement still shows the previous target, and
  following it made the first smoke's Skullcannon switch targets every tick without
  firing (fixed in `0f8eb39`).
- A shooter skips a target in range that draws no shot for 15 s (30 s for artillery)
  for 30 s (`55ab6b3`, after Skaven skirmishers chased chariots without firing).
- The executor never queues orders and leaves behaviour toggles alone.

### `commander`: asynchronous API model over the skills

One plan request is in flight at a time, on a worker thread, so `decide` never waits
(`commander.py` docstring). On adoption, assignments for dead or unknown units, a `move`
without a point and `shoot` for a unit without missiles are dropped; a dead or unknown
target is cleared; a target out of sight is kept (the skill acts as with no target until
it reappears); abilities are revalidated and sent once. Drops and engine rejections go
into the next prompt. Units the plan omits keep their assignment; until the first plan
arrives, units follow their class defaults. A reply that is not JSON is retried once
(`INVALID_RETRIES`); the direct controller retries an invalid reply twice, then keeps
the last reply's valid orders.

Both `skills` and `commander` decide at the mod's tick rate (about 3-4 decisions a
second). The trace keeps every decision with orders, an error or new metadata, and quiet
ones once per `--observe-ms`. `result.json` `llm` holds the API totals plus `plans` and
`plan_age_ms` (mean plan age is `plan_age_ms / plans`).

## Following a battle

- `watch` tails a running job beside the game, touching nothing in it: each model
  request with its state's battle time and strength and what it reports as dropped or
  rejected (`--prompts` prints it whole), each reply, engine rejections, a strength line
  every 30 s and each result. `watch JOB --next` waits for one event and exits (for agents).
- `play --show` puts each model reply in the game's advisor window
  ([advisor text](integration.md#advisor-text-verified-2026-10-13)).
- `digest` summarises a job or episode afterwards; `digest EPISODE --at SECONDS` prints
  one decision in full: the prompt, raw reply, plan or orders and the engine's verdict.
- The trace stores, per commander request, the full `prompt` and `prompt_sha256` (with
  the Assignments section: each unit's skill and current phase) and, per adopted plan,
  the assignments, abilities, `reason`, `notes`, `dropped`, `plan_age_s` and `attempts`
  (raw reply text, token usage, seconds); per direct decision, the prompt, reason, notes
  and attempts. The API returns reasoning only as a token count.

Commands: [README](README.md#commands).

## Comparing controllers

The results register has `policy`, `model`, `effort` and `harness` columns; the harness
version comes from `-vN-` in the job name and is counted separately per policy. A
comparison should use:
- paired battles: the same random seeds for every controller (one job per seed; a
  deterministic controller plays each seed once, since a rematch replays the same
  battle), or an in-job rotation on a declared scenario (`--policy a,b,c
  --rotation-seed N`, [benchmark-run.md](benchmark-run.md));
- at least six battles per controller (three separated nothing, on a fixed scenario or
  on paired draws);
- the same information boundary: enemies only while visible, no privileged state;
- the AI's stats modifier as declared per scenario (`expect.ai_stats_modifier`); at 1.1
  it favours the enemy in mirrors.

| Variant | What it isolates |
|---|---|
| `llm` (current version) | the baseline |
| `attack_nearest`, `rush_nearest` | the scripted floor |
| `skills` | whether the executor is useful by itself |
| `commander` + Luna | whether high-level model decisions add value over the same executor |
| `commander` + Sol / Astra | whether better planning is worth its latency and cost once execution no longer waits |
| `--delay-seconds 0,6,10` | how much outcomes depend on observation age, independent of the model |
| later designs below | one change at a time against the best of the above |

| Metric | Where |
|---|---|
| outcome, battle length, strength left on both sides, decisions, invalid orders, order delay, cost | `results.csv` |
| plan count and mean plan age (state seen to plan adopted) | commander `result.json` |
| active margin, order and snapshot ages, plan-age distribution, rejections per trial | `report` ([reports.md](reports.md)) |
| order churn: orders per unit per minute | derivable from the trace; not computed |
| threat-to-response time: an enemy comes within 40 m of a free unit, to that unit's next order | not computed |
| idle units while a useful action exists | not computed |
| losses weighted by unit value instead of men | not computed (needs unit costs) |

Model tiers: prices per million tokens are in `gameai.llm.PRICES`; a call over 60 s
times out in `gameai.llm.post`. One commander smoke battle per model on `kho5-dwf5` at
low effort (log.md, "Skills and commander v1") measured mean think time 6.4 s for
`gpt-6-luna`, 5.8 s for `gpt-6.1-sol` and 4.8 s for `gpt-6-astra` (Sol and Astra reasoned
very little at low effort), and $0.02, $0.18 and $1.17 per battle. One battle per model
measures latency and cost, not strength.

## Candidate changes for the next version

Verified contradictions between the prompts and the code. Each changes prompt bytes or
executor behaviour, so it belongs in a logged `llm`/`commander` version with regenerated
golden prompts:
1. **The Battle line is not at the top of the state.** Line 1 of `system_prompt.md` and
   `commander_prompt.md` says "The Battle line at the top of the state", but
   `llm.render_state` puts the terrain grid first, then Battle, army abilities and Winds
   of Magic. The terrain paragraph also carries tuning text in code ("Do not repeat an
   unreachable move: select a reported reachable alternative or another goal."). Render
   Battle first or say "near the top", and move that sentence into the prompt files.
2. **A morale and flight paragraph splits the order list.** In `system_prompt.md` the
   paragraph "Friendly units also show the UI's leadership fraction ..." (from `a0a7108`)
   sits between "Orders are processed in list order" and the `- move:` bullet;
   `rules_prompt.md` has a proper `- flight:` bullet instead. `commander_prompt.md` has
   the same paragraph between the Skills rules and the Abilities paragraph. Move the
   morale sentence into the state description, make flight a bullet in
   `system_prompt.md` and fold it into the commander's Abilities paragraph.
3. **The commander's default-skill sentence is wrong.** `commander_prompt.md` says
   "missile infantry, artillery and the Skullcannon shoot; the lord, heroes and all
   cavalry charge; everyone else engages". In `skills.py` every missile chariot shoots,
   non-missile chariots charge, and flying heroes and cavalry (class `flying` since the
   mod classes every non-lord flyer so) engage. Either change the defaults (executor
   v1.3) or reword the sentence to the code. Also, `llm.render_unit` labels a unit
   without target or destination "no order"; `system_prompt.md` explains the label, but
   under the commander it is the normal state of a unit waiting under charge or hold and
   `commander_prompt.md` never mentions it.
4. **Just-applied moves read as stopped.** The observation taken as a batch applies
   predates its moves, so `llm.render_target` called every freshly ordered unit "stopped
   N m short of your move"; in `bench-g1-cavalry-ai10-01-20261014` episode 2 Sol
   re-issued all six routes three times in 26 s. Fixed in `llm` v16 (merged `005a050`,
   2026-10-15): such a move reads "your move to (x, z) issued this instant". It changes
   prompt text only in that state, so the golden prompts are unchanged.
5. **An attack on a target out of range is a move.** In `bench-b10-screen-dwf-line-20261015`
   episode 0 Luna ordered the Organ Gun (range 300 m) to attack the enemy cannon about
   670 m away eleven times, called it "now-in-range" at 403 m, and the advancing gun and
   shooters left the defensive line and fled first. The state gives each unit's `range`
   but neither prompt says that attacking beyond it walks the unit forward; the unit line
   could print the target's distance against the range, or the rules could say it.
   Drafted on branch `wh3-llm-range`, included in `wh3-llm-v17`. C1 is complete;
   integration is planned, not performed yet.
6. **Last sightings do not say a unit was fleeing.** In `bench-c1-cavalry-ai11-01-20261015`
   episode 3 Sol spent 600 s of a lost battle looking for guns that had routed off the
   map, listed in the last-sighting memory at the map edges with no state. Carrying the
   last observed state (routing, shattered) with each sighting changes controller memory
   and rendered text, using already-public information. Drafted on `wh3-obs-last-state`,
   included in `wh3-llm-v17`; no change to the environment observation track is needed.

Integration note (2026-10-15): the v17 branch changes only `llm.py` and its tests. The
commander imports the same `remember` and `render_state`, so both fixes also affect it.
Log `llm`/`llm_rules` v17 and commander v4 together when integrating, and validate both;
keep unrelated prompt/executor changes out of that comparison. The branch's earlier
348-test result is historical, not validation against current main. See the
[implementation plan](benchmark.md#implementation-plan).

## Designs not built yet

Ordered by how much each is expected to teach for its cost; test each against the best
implemented controller, one change at a time.

1. **Event-triggered replanning.** The commander plans back to back, which is cheap with
   Luna and costly with Astra. Instead, plan on a timer (every 15-30 s) plus events, each
   with a cooldown: a friendly unit routs or wavers; the enemy lord enters melee; a unit
   loses a set share of its men since the last plan; an assignment completes or its
   target dies. The executor's own rules stay the immediate response. Source: React When
   You Need To (arXiv 2609.22587). First experiment: an Astra commander with timer and
   events against Astra planning back to back, on cost and outcome.
2. **Richer skills from observed failures:** a rear charge through a queued waypoint (a
   move followed by a queued attack); shooters kiting with the `skirmish` toggle; a lord
   escort or bodyguard skill; screening (stay between a friendly shooter and the nearest
   enemy). Add executor-level coordination too: a shared count of units on each enemy,
   so that defaults gang up rather than spread. Build each skill with a unit test and a
   live probe, and check `unitcontroller` semantics first (`withdraw()` leaves the
   battlefield; `move` must stay a plain goto).
3. **Candidate-action selection.** Code builds a few feasible options per decision, such
   as three targets for each free unit with distance, enemy strength, who else is on it
   and time to contact; the model picks by id and sets bounded parameters. This removes
   coordinate errors and leads to a learned ranker (item 7).
4. **Specialists with bounded authority.** HIMA (arXiv 2508.06042, COLM 2025) coordinates
   imitation-trained specialists through a planner; STRATA (arXiv 2609.38881, Red Alert)
   separates strategic, logistics and tactical agents and adds a post-match review agent.
   Two forms fit here: before contact, two or three parallel advisers propose deployment
   plans that the commander resolves into one allocation; in battle, a specialist owns a
   fixed set of units (the mounted units, or ability use) and never shares one. Only
   after items 1-2 show what the executor and commander still get wrong.
5. **A between-battle coach and code-as-policies skill development.** Code as Policies
   (arXiv 2209.07753) has a language model write programs that compose control
   primitives; STRATA distils matches into experience cards. Here the autoresearch loop
   (`wh3-version-review`) becomes the coach: its reviews propose tested skills and
   commander prompt changes, and live battles only select among tested skills.
6. **Stronger models on the same executor**: the paired comparison for Sol and Astra as
   commander, at low and medium effort.
7. **A learned local policy.** A small shared network or action ranker scores candidates
   (item 3) from structured state and the unit's assignment, trained from logged battles
   or outcome-checked stronger-model labels, with delayed, variable and missing plans in
   training (training-time action conditioning for real-time chunking, arXiv
   2512.05964). Later, cooperative reinforcement learning (MAPPO) on bounded scenarios;
   a rematch takes about 15 s and battles run at 1x, so about ten battles an hour.
8. **Display aids**, passed through the mailbox like `--show`: a text component of our
   own (`uic:SetStateText(text)` on a component the battle script creates or borrows),
   map markers for plan points (`bm:add_ping_icon(x, y, z, type, waypoint, rotation)`,
   `remove_ping_icon`), each unit's phase and last order, the enemy composition as seen,
   and kills per fire order (unmerged branch `wh3-fire-report`).

Precedents the commander already follows: AgileThinker (ICLR 2026) runs a planner and a
reactive process concurrently, the reactive one on the latest observation; real-time
chunking (arXiv 2506.07339, NeurIPS 2025) keeps executing while the next plan is computed;
JEV-Star (arXiv 2609.27331) puts a fast action selector under persistent GPT-6 planning in
StarCraft II, and its micro-combat wins rose only from 3 to 7 of 105 episodes, so the
architecture alone does not produce skilled micro.

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
- WH3 scripting documentation: [integration.md](integration.md#references).
