# WH3 benchmark definition

## Purpose

Compare the performance of two different controllers on a Total War Warhammer 3 battle, under different circumstances. Controllers can be a single model, a multi-agent team of models, a complex harness that orchestrates different models as components, etc. A controller may win by any permitted play, as acknowledged by the game engine.

## Scope

Current scenario direction, 2026-11-04: develop a simpler scenario, then a more complex one
once the first is reliable and validated. Their concrete setups are still open. The
[updated plan](scenario-guidelines.md#current-plan-and-owner-decisions) records tentative
owner-manual winnability evidence and the wish to try an overall ranking. The mirror and
suite below retain their recorded definitions/results; no replacement scenario or score is
selected here. [Tactic-judge research](tactic-judges.md) is a proposal, not an adopted measure.

The first draft covers a Land Battle (`classic` / `land_normal`) against the game's built-in AI, with small mixed armies (owner, 2026-10-23). The intended benchmark also includes Siege, Survival, Ambush and Conquest, with other battle types for the owner to confirm (2026-10-28). Existing [battle-type scenarios](battle-types.md) and siege checkpoint work are starting points; they do not establish a benchmark for those modes. Their profiles, order of implementation, measurements and checks remain open.

- **Task.** The controller commands a fixed army. It doesn't choose the army or deploy it.
- **Winner.** The game engine decides who won, lost or drew. A win when the timer runs out is a win (owner, 2026-10-23).
- **Inputs and orders.** The controller reads the structured battle state our Lua mod publishes and sends its orders back through the mod. The game still does the pathfinding, formations and unit-level fighting.
- **Time.** The battle runs unpaused at normal speed (1x). The controller's whole delay, network and retries included, is part of its result: a controller that loses because it is slow has lost (owner, 2026-10-14).
- **Manual demonstration.** Only the owner may pause when manually demonstrating winnability (owner, 2026-11-04). Such evidence is separate from automated results and does not establish their interface/timing feasibility. The recording/check procedure remains open.
- **Same conditions.** Every controller plays the same battle, with the same information and the same permitted orders. Results from different roles, maps, game builds, controller versions or scoring versions are kept apart.
- **Claims.** A result says how a controller did in the declared battles, nothing about general WH3 skill or a model's intelligence.

Training (fine-tuning, RL) can use the benchmark's records, but it isn't part of the benchmark (yet?).

A `JUDGEMENT:` line marks an agent's proposal that the owner hasn't decided yet; the [owner interview](benchmark-implementation.md#owner-interview-one-land-battle) collects the open questions. How we will build and check the benchmark: [benchmark-implementation.md](benchmark-implementation.md).

## The first battle

This section records the earlier mirror choice. The next two scenarios follow the current
plan above; the mirror is not automatically selected as its simpler scenario.

Owner follow-up, 2026-11-02: start with a single Empire-versus-Empire battle. Both sides
have three melee units and one ranged unit; our fifth unit is cavalry, theirs a weaker
non-cavalry unit. The aim is to see whether the controller can exploit that advantage.
The owner delegated reasonable starting settings; the concrete
[mirror profile](benchmark-implementation.md#first-version-follow-up-2026-11-02) remains
marked and unverified. Other battle research comes later.

The following Empire-versus-Greenskins roster and two-role design are earlier proposals,
retained with their markers; they are not the current first battle.

JUDGEMENT: Starter armies — Codex, 2026-10-23: propose eight units per side with lords and casters.
Reusing the lordless line or changing factions would change the decisions and measurement scope;
the first matchup proposal rests on this choice, not on the old line's win rates.

Empire against Greenskins, eight units a side, each army with a lord and a caster. The unit types come from the existing [Empire line and pitched battles](empire.md#the-set), but this is a new scenario.

| Empire, played by the controller | Greenskins, played by the game AI |
|---|---|
| General of the Empire, Bright Wizard | Orc Warboss, Orc Shaman |
| Halberdiers, Swordsmen, Spearmen with shields | Orc Boyz, Big 'Uns, Goblin Spearmen |
| Two Handgunners | Arrer Boyz |
| Empire Knights | Goblin Wolf Riders, Orc Boar Boyz |

These armies give the controller real choices: what to shoot, where to put the guns and how to screen them, when to commit the cavalry, when to cast spells, and how to keep units from breaking. None of these is required to win. We won't try to credit damage or the win to individual spells. Nobody has played these armies yet, and eight units a side doesn't mean equal cost or equal strength. Results from the older seven-unit Empire line don't carry over.

JUDGEMENT: Starter settings — Codex, 2026-10-23: propose the existing Taurox map, rank zero,
very hard AI at modifier 1.0, large units (0.75), realism off and a 1200 s engine timer.
Other settings change difficulty and timeout opportunities; the first profile rests on these.

The map is Taurox (`battle_preset_qb_wh2_dlc17_taurox_rune_tortured_axes`). Before the first run, fix both rosters, the characters' mounts, equipment and spells, ranks, unit behaviour toggles, how deployment happens, and the funds, and check each one against the lobby and the first battle observation. Characters cost more in the lobby than in the game database, so check that the funds cover them. Never inherit settings left over in the lobby.

JUDGEMENT: Role coverage — Codex, 2026-10-23: propose separate Empire-attacks and Empire-defends
conditions for the same roster and map. A defender-only version is cheaper but narrower;
the proposed first release's coverage and game-time estimate rest on both roles.

The Empire plays the same armies on the same map twice: once attacking, once defending. The two roles are different battles (deployment and the AI's behaviour change), so their results are reported separately, and the gap between them doesn't test any one tactic. A timer win is a win in either role; the result notes how the battle ended.

These battles are for development: we will study them and tune controllers on them. To see how a controller does on a battle it wasn't tuned on, set aside another map before any new tuning (noting any earlier battles played there), freeze the controller, then play that map and report it separately. More launches on Taurox repeat the same task; they aren't new tasks. Without a reserved map, results describe only the development battles. Which map, and how many launches, is still open.

## The coordination suite (suite-v1)

Owner's goal, 2026-11-04: compare control methods (one model, a team of models, GaP and others)
across different dimensions on a decent number of challenging battles. The suite plays each
frozen method on each battle and reports them side by side. It is a proposal in use: every
choice below is marked in the code that holds it, and the owner decides what stays.
Code: [`suite.py`](../../src/twwarhammer3/battle/suite.py). Commands: [runbook](benchmark-run.md#the-coordination-suite).

**Battles.** Each scenario in `scenarios.json` with `"benchmark": "suite-v1"` poses one problem,
named in its `tests` field. Six use authored starting positions, which the setup check reads back
in the first observation: these are the battles one general cannot fight from one place.
Six keep native starts, from battles where earlier evidence showed room between weak and strong
play (the owner's first mirror battle and five others from the register); these six have not
been played as suite battles yet.

| Scenario | The problem |
|---|---|
| `coord-two-fronts` | Two separate fights at once, one reserve to send |
| `coord-relief` | A garrison holds while a column 460 m away marches to the same fight |
| `coord-pincer` | Two groups attack one block together, or each loses alone |
| `coord-breakout` | Three groups converge; concentrate on one first |
| `coord-detail` | Beat the near wave before the far wave arrives |
| `coord-rear-raid` | Guns behind a line, cavalry behind the guns |
| `coord-mirror` | One cavalry unit's advantage against a larger army with a gun |
| `coord-line-raid` | A line, guns, reserve and knights with changing jobs |
| `coord-swarm` | Twenty cheap units against a small strong line |
| `coord-caster` | One caster's spells and scarce escorts in an assault |
| `coord-siege` | Walls, one reserve and limited supplies against many |
| `coord-cavalry` | Cavalry only, against spears and guns |

As in [BEHAVIOR](benchmark-references/behavior.md), a scenario names a goal, not a solution: any
engine win counts and the prompt names no tactic. As in [SMACv2](benchmark-references/smacv2.md),
simple scripts play too, so a battle a fixed rule can win shows up as one.
A scenario is *witnessed* once any arm wins it at this build. Nothing here is admitted or
excluded by a win rate: an unwitnessed scenario stays and is shown as unwitnessed.

JUDGEMENT: Authored calibration — Claude, 2026-11-04, overnight goal: rank-5 player units and
enemy men 1.09-1.20 times the player's, after 22 straight losses on harder versions; very hard AI
kept. An easier or harder setting changes which battles are witnessed and what each arm can show.

**Control methods.** `suite.ARMS` freezes them; all use Haiku 5.5 low where a model plays.

| Arm | Who decides | What it asks |
|---|---|---|
| `hold`, `rush` | Nobody; every unit runs at its nearest enemy | The floor and the naive plan |
| `skills` | Scripted class skills: shooters shoot, cavalry waits for contact then charges | What a fixed script does for $0 |
| `concentrate` | A script that gathers the army, picks one enemy and hits it together, fast units last | Whether the coordination a battle asks for can win it, and whether the readings notice |
| `single` | One model orders every unit (`llm_rules`) | The reference for every model arm |
| `tips` | One model orders every unit, on `single`'s prompt plus "How to fight" (`llm` on a suite battle) | Do tips alone explain `commander`'s wins? |
| `team` | One model per unit class, at the same time | Does dividing the army help? |
| `commander` | One model gives standing skills; scripts carry them out between its replies. Its prompt also holds a page of tactics advice | Does a slower planner over fast scripts help? |
| `gap` | Before each scenario a coordinator and one specialist per class write frozen [graphs](gap-plan.md) from its public task; in battle a model only suggests targets every 30 s. What Haiku wrote are rules per unit class, with no map plan | Can rules a model writes once beat thinking throughout? Writing is billed separately |

These compare whole systems, as the [evaluation plan](multi-agent-plan.md#6-controllers-and-comparisons)
says to do first: each at its natural concurrency, with what it spent shown beside what it won.
They do not isolate the cause of a difference, and equal-resource arms come later.

**Dimensions.** One row per planned battle, played or not. No dimension is folded into another.

| Dimension | Measures | Read from |
|---|---|---|
| Effectiveness | engine outcome; `own` (the [mirror formula](benchmark-implementation.md#first-version-follow-up-2026-11-02) at any army size); `taken`, percent of the enemy dead, routed or gone at the end; `killed`, percent of its men dead. A timer win can leave active enemies, so neither percentage is necessarily 100 | Engine ending and totals |
| Cost | dollars, calls, tokens; for `gap`, what writing the graphs cost, shown apart | Ledger-backed result |
| Speed | median and 90th-percentile order age, observation to engine application | Engine acknowledgements |
| Reliability | orders the engine refused; bad replies, which void a decision; failed calls, provider faults or calls closed unsent; every failed or unplayed battle | Trace and plan |
| Coordination (descriptive) | `spread_s`, how long after first contact the median unit joined; `local_share`, friendly men over all men near each fight; `idle_share`, able melee units standing idle after contact | 1 Hz recorder, the same for every arm |

Bad-reply and failed-call totals include every matching attempt with recorded evidence, including
terminal failures without an engine outcome. Failed calls include transport failures and provider-reported
failed responses, including events retained only in a trace when the result is missing.
Total play cost and dollars per win include all recorded result-ledger costs; an attempt
without a result keeps its cost unavailable. Per-battle means still describe engine-completed
battles. Explicit provider and configured-controller paths must match the plan. Older plans pin paths without artifact hashes, so editing a graph
in place remains undetectable by this join.

The owner chose on 2026-11-12 to keep known outcomes and show a comparison as unavailable
when its tie-break is missing. If either arm has any completed repeat missing `own` or
`taken`, equal win rates yield no better/worse/tied verdict; reports count these unavailable
tie-breaks separately. Different known win rates still compare. An arm without a completed
battle continues to have no paired comparison. This is a reporting choice, not verification.

`taken` exists because `own` alone rewards fleeing: the mirror's best Haiku condition, 28.4, was an
army that routed having removed 2% of the enemy.

Coordination readings describe what happened and are never added to a score
([MultiAgentBench](benchmark-references/multiagentbench.md) keeps outcome and process apart for the
same reason). What they are worth so far (`runs/coord-suite-20261104/local_share_check.py`): on 491
recorded battles (144 wins), of which 389 lie in the 25 scenarios holding both a win and a loss,
the within-scenario AUC of whole-battle `local_share` is 0.82, of its first 60 s after contact 0.50,
and of `spread_s` 0.49. So `local_share` mostly restates who won, and `spread_s` does not go with
winning. On 29 battles of the Empire line `spread_s` does tell running from walking (37 s against
9 s), because running units arrive one at a time. `idle_share` counts units held back, including a
sound reserve. None is checked against a human's judgement, and no reading here measures
coordination in a way we have shown to matter.

**Arms that share parts.** `commander` is `skills` with a model choosing the skills, so `skills` is
its control: a `commander` win means little until `skills` has played the same battle. The same
holds for any method built on another.

**Arms that differ in advice.** `single` and `team` get the rules-only prompt. `commander`'s prompt
has a "How to fight" section (arrive together, gang up, come from behind), so comparing them
mixes the control method with the advice. The `tips` arm is `single` plus only that advice, in
`system_prompt.md`'s direct-order words (owner's yes, 2026-11-04; rests on JUDGEMENT suite.py Tips
arm). A test holds that the tips section is its only difference from `single`'s prompt. First result, one
battle per scenario: 0 of 6, as `single` ([log](log.md#2026-11-04-one-model-with-tips-won-none-of-six)).

**What the battles turned out to be.** The authored battles were designed around one problem each,
and in play several were not that problem (one battle per pair): in `coord-pincer` the enemy block
split and fought both groups, in `coord-detail` the two waves reached the army within about 10 s of
each other, and in
`coord-breakout` neither win kept its line on one enemy group. Read a battle by what its report
page shows, not by its name in the table above.

**Comparison.** The scenario is the unit. Within a scenario arms compare by wins, then `own + taken`
(rests on JUDGEMENT `battle/suite.py` Scenario tie-break);
across scenarios, each arm against `single` by how many scenarios it did better or worse on, with
an exact sign test, and a paired t interval of `taken`. Win rates carry Wilson intervals, or the
exact one-sided bound at zero wins. These are the [guidelines'](evaluation-guidelines.md#72-use-the-named-method-for-each-situation)
small-sample methods, which rule out a bootstrap at these sizes. Battles run in one shuffled order
per repeat. A battle that fails keeps its row; nothing is replaced. With one or two battles per
pair these results are exploratory: they rank nothing and show where a confirmation would be worth
paying for. Results: [log](log.md#2026-11-04-first-comparison-of-control-methods), report
`runs/twwarhammer3/reports/suite.html` ([build](reports.md#coordination-suite)).

**Proposed check, not agreed.** For any finished plan, a script that shares no code with `suite.py`
would check, from raw records: every planned pair has one row; every authored unit stood within
25 m of its place in the private first reading; `taken` equals the engine's enemy totals; `own`
equals a hand recomputation from the first-ending unit records; each battle's cost matches the
ledger's response ids; and the plan's revision, versions and graph artifacts match each job. It
would fail on a planted swapped unit, a dropped battle and an altered total. This establishes
that the suite recorded the battles it says it did, not which method is stronger.

## Outcome and score

The engine decides win, loss or draw. Keep the raw engine result next to any benchmark score.

Owner follow-up, 2026-11-02: **engine wins rank above losses**. Health means the game's
tactical-unit health bar, not individual soldiers' HP. Start with simple calculations
and revise later. The proposed outcome-first, health/state tie-break and no-retry error
accounting are in the [starter plan](benchmark-implementation.md#first-version-follow-up-2026-11-02).
The earlier text below records the preceding discussion; the relationship between wins
and losses is now decided, while the proposed numeric defaults remain marked.

Owner direction, 2026-11-01, refining 2026-10-28: tentatively score mostly on unit health;
a healthier army should score better. Lower morale should reduce the score, with routed
units penalised more strongly. The formula, unit weighting, observation time, treatment
of recovery and relation to the engine result remain undecided. The win-rate summary below
is an earlier proposal, not the selected primary score. See the
[plan update](benchmark-implementation.md#owner-directions-2026-11-01).

The owner also tentatively prefers failures counted separately as errors rather than
partially scored battles. This does not yet resolve comparison denominators, replacement
rules or the earlier forfeit convention below. A known engine ending is still retained
alongside later errors; a transient error need not erase the eventual battle result.
This update changes the plan only; the evaluator and historical scores are unchanged.

JUDGEMENT: Primary summary — Codex, 2026-10-23: propose wins divided by scored attempts,
with draws as non-wins, not half-points. A points table or preservation tie-break changes
rankings; the proposed summary and comparison rest on this choice.

Under the proposed Primary summary, the score is the number of wins divided by the number of scored attempts. A draw is not a win.

| What happened | How it counts | Status |
|---|---|---|
| Engine win, timer win included | A win | Agreed 2026-10-23 |
| Engine loss or draw | Not a win; losses and draws are shown separately | Draws: proposed |
| The controller fails for good during a valid battle | Not a win, labelled forfeit; never recorded as an engine loss | Agreed 2026-10-21 |
| The controller can't be built for its assigned battle | Not a win; shown apart from game or setup failures | Agreed 2026-10-21 |
| An error after the engine reported the ending | The engine result counts; the error is reported as a reliability failure | Agreed 2026-10-21 |
| A decision fails and play continues | The final engine result counts; the lost time, invalid orders and cost stay on record | Agreed 2026-10-21 |
| A proven setup or game failure, or an operator stop | Shown separately; whether it is excluded or replaced follows the plan fixed before the run | Proposed |
| Unknown cause, unsettled cap, or no ending | Shown as unresolved; settle the rule before counting it as a loss or excluding it | Proposed |
| A planned battle that never started | Shown with its reason; no outcome | Agreed 2026-10-21 |

Still to settle before a run: provider, key and credit failures; budget stops; and what to do when the wall-clock cap hits with no engine result. That cap is not the engine's timer. What the code does today is in the [failure audit](evaluation-guidelines.md#52-freeze-how-every-trial-is-scored). Never drop failed battles to improve the rate.

Report how many battles were planned, started, ended by the engine, forfeited, excluded, unresolved and never started, and define each word (one battle can fall under several). Show the win rate with its denominator and uncertainty. If some outcomes are unresolved, show the range of rates they could produce instead of treating the finished battles as the answer. Under the proposed Primary summary, own losses, battle length, flanking and API cost don't change the score; the broader scoring choice remains open.

## Measurements

Three levels: the outcome, the condition of each army, and what happened (orders and events). The evaluator records both armies in full; the controller gets only its public inputs. A unit that leaves the controller's sight hasn't died.

JUDGEMENT: First diagnostics — Codex, 2026-10-23: propose game-clock unit histories and
separate timing/cost summaries, without a weighted army-advantage score. Cost-weighted damage
or tactical points change interpretation; the first report and capture scope rest on this.

| Measure | What it is |
|---|---|
| Health | Each unit's remaining health fraction and living entities against its starting values, for both armies, over game time. Fractions are never added up across units as if they were army value |
| Leadership | Each unit's leadership as the game's UI shows it, with the effects listed beside it. No invented "morale damage" total |
| Unit state | Wavering, routing, rallied, shattered, leaving the field and dead, with each change and recovery |
| Losses and recovery | Remaining health, its change, deaths and recovery, kept apart |
| Orders and events | Orders, acknowledgements, refusals, contacts and state changes on one timeline. An accepted order isn't proof that it happened |
| Time and cost | Battle length, gaps between decisions, how old the observation was when orders went out, wall time, failures, tokens and API spend |

Unit states are recorded at fixed game-clock intervals, whatever the controller is doing; the interval is chosen after a pilot shows how precise and costly the readback is. Each record keeps its real timestamp, the unit's identity and the value's source, and gaps stay visible. The evaluated timeline stops at the engine ending; calls and cleanup after it still count toward reliability and cost. Evaluation data never reaches the controller's prompts, memory or feedback. A missing measurement never cancels a known engine result.

What the code records today, and what is missing: [measurement gaps](benchmark-implementation.md#measurement-gaps).

### The report

For each battle, the report shows the result and how it ended, each unit's condition over time, and the orders around the moments that decided it. A table lists every battle, wins and failures alike, and links to each one, so nothing depends on a hand-picked replay. Health and leadership get separate curves. Any army-wide total says what it divides by and what it leaves out. Nothing is labelled "probability of winning" unless that estimate has been validated.

## Comparison

JUDGEMENT: First comparison — Codex, 2026-10-23: propose one frozen direct `llm_rules`
controller against `rush_nearest` as the primary contrast, with `hold` and `attack_nearest`
reference rows. A different controller or primary baseline changes what the first study answers.

The first question: in each role, does the model controller `llm_rules` win more often than `rush_nearest` (every unit runs at its nearest visible enemy), and at what delay, cost and failure rate? `hold` (no orders) and `attack_nearest` (the same attack at a walk) add two reference rows. This compares whole controllers: the model, prompt, helpers and speed together. It doesn't separate the model's reasoning from its speed or its helpers.

Before any paid run, fix the model and provider, prompt, reasoning effort, memory, limits and source versions. Scripts keep the game's normal automatic unit behaviour; each controller's disclosure says what help it gets. The battle description gives the objective and the facts, never the tactic we hope to see.

JUDGEMENT: Launch sampling — Codex, 2026-10-23: propose one episode per fresh launch,
interleaved by controller within each condition. Rematch pairing costs less but needs reset
evidence and grouped analysis; the first comparison's sampling and overhead rest on this.

Each fresh game launch plays one scored battle, and controllers take turns across launches within each role. A rematch restarts the same battle from the same start, so rematches aren't independent samples ([measured facts](benchmark-implementation.md#measured-facts-behind-the-design)); fresh launches cost more time but avoid the problem. Pairing controllers through rematches later would need a reset check and an analysis that keeps each launch's battles together.

Before collecting results, fix the win-rate difference worth detecting, the number of battles, the statistical method, the replacement and stopping rules, the reserved map, and the money and game-time cap. None of these is set yet. A few pilot battles show that everything works; they don't measure win rates. If an affordable number of battles can't answer the question, call the comparison exploratory. Report each role separately with its counts and intervals, and never pool roles, settings or versions into one number.

## What makes the battle useful

- The engine gives a clear outcome, and the measurements are reliable.
- Choices matter: different play leads to different results.
- It is hard, but someone has shown it can be won (owner's difficulty target). No particular script, tactic, architecture or model has to win; if a simple script wins, it becomes a reference, not a reason to drop the battle.
- If every controller plays alike, keep that evidence and rethink the battle before paying for a broad comparison.
- Don't adjust the difficulty to make a favourite model win, or until every model loses.
- Health, leadership and event measures explain the result and never overturn the engine's winner. Battles where they would rank controllers differently from the engine are worth reading to see why.
- A measurement shows what happened, not that a spell or a flank caused the win.
- Results cover the declared battle and the variations actually tested.

## Observations and orders

The track is `obs-v4+terrain/act-v2/live-1x` (`play.TRACK`). A track names what the controller sees, which orders it can send and the timing rules; a battle with added observation age appends `+age-<D>ms` (D in milliseconds). A changed prompt or memory makes a new controller version and changed scoring a new evaluator version; neither makes a new track. Results from different tracks can share a report but are never pooled. Earlier tracks: `obs-v1/act-v1` (b1), `obs-v1+terrain` (b2, terrain grid), `obs-v2+terrain` (b3, enemy roster fix), `obs-v3+terrain/act-v2` (b8, morale and flight), `obs-v4+terrain/act-v2` (b12, optional public objectives).

The code is the reference:
- the `engine/mailbox.py` docstring: the observation, the acknowledgement and every bridge file;
- `protocol.py`: the order types and `validate_orders`;
- `mod/script/battle/mod/twwarhammer3_battle.lua`: what is published, and the engine's refusal codes;
- [integration.md](integration.md): the engine facts behind them.

**The controller sees structured state, not the player's screen.** Enemy units appear only while `is_visible_to_alliance` holds and `is_hidden` doesn't. The enemy roster shown in the lobby is public; enemy units that arrive later join it when seen, and an enemy death is reported only if the unit is visible when it dies. The `evaluation`, `final` and `setup` fields hold hidden information, and the harness strips them before the controller sees a snapshot.

Known limits:
- positions are rounded to 0.1 m and health fractions to 0.01; entity counts are integers;
- enemy units' targets aren't observed;
- a friendly unit's `target` can name an enemy out of sight, and attacking an enemy that died out of sight returns `target_dead`, not `target_not_visible`;
- `class` comes from the land-unit class and missile range, not the unit's battlefield role (flying non-lords read `flying`);
- nobody has checked that `is_hidden` works, or that the filter matches what a player sees;
- the terrain grid samples 16 m squares every 32 m at deployment; it isn't a path planner.

Orders: `move`, `attack`, `halt`, `behaviour`, `ability` and `flight` for each unit; the unit `"army"` casts army abilities and, paying with supplies, `build`s and `reinforce`s. The game still decides pathfinding, formation, melee responses, fire at will and skirmish, retargeting, morale and spell effects. The harness adds no tactical helpers; the `skills` executor belongs to the `skills` and `commander` controllers.

Bad orders are never repaired. A batch that fails `validate_orders` against the observation it was based on is sent as no orders; the trace records it, and the acknowledgement gives the reason (`validation_error`). The engine can also refuse single orders, with a code in the acknowledgement. Both count as invalid, and the report counts them separately. An acknowledgement means issued or queued, not carried out. A controller can never change session settings, use the `restart` control, take menu steps or touch bridge files.

## Timing

`live-1x` is the only timing policy: the battle runs unpaused at 1x. `require_realtime` refuses any other session, and play refuses an observation that reports another speed. The mod's speed fields never change, though, so this can't catch a real slowdown ([runtime speed limits](integration.md#loading-phases-and-control)); a clock check is proposed. A setting is not evidence of the speed actually achieved.

- The mod runs on a 250 ms game-time callback, which fires every 300 ms because the engine clock moves in 100 ms steps. It publishes an observation every `observe_ms` (1000, so every 1.2 s) and at the tick that applies each request, empty ones included.
- The harness reads `observation.json` every 100 ms of wall time; the mod reads `orders.json` every 200 ms and applies a request at its next tick. So even an instant controller's orders apply 0.3 s (sometimes 0.6 s) after the state it saw.
- One request is in flight at a time; the next decision starts from the observation that carries its acknowledgement. Meanwhile units keep their orders and the game's automatic behaviour. A reply based on an old snapshot is applied as it is, and its basis is recorded.

Recorded for each decision: basis `seq` and `time_ms`, decision time, `applied_ms`, `delay_ms` (how old the information was when the orders were issued or queued, on the battle clock), `think_s` and `roundtrip_s` (wall time, system clock). Model calls add wall seconds, the provider's processing time (`openai-processing-ms`) and the returned model name; the commander adds `plan_age_s`. Each battle records its battle-clock to wall-clock ratio. Network conditions are measured, not controlled; interleaving controllers over time spreads their variation.

**Added observation age (a diagnostic).** `--delay-seconds 0,6,10` runs every controller at each age. At age D the controller decides on the newest public snapshot that is at least D battle seconds old; that snapshot is its basis, so `delay_ms` stays the true age. The first D seconds only fill the buffer, so the first order is late too. D is a minimum: a slow call leaves gaps in the buffer, so the text and JSON reports show the actual snapshot age at decision beside the order age. D = 0 is the controller's natural delay, not zero delay. Results at different ages are never pooled, and they sit beside the main result at natural delay (owner, 2026-10-14).

Added age changes how old the observations are, not how long the model thinks. `--interval-ms` sets the wait after an acknowledgement; it isn't an exact decision period. Change one of them at a time, and report the ages and gaps actually achieved, retries and unfinished calls included. Delaying a fresh reply, or delaying only a planner that sits above an executor with fresh state, would need a different mechanism. Testing only the reactions after contact would need a shared opening and a declared start point, which aren't built. Don't select battles by their latency to claim the latency caused the losses: hard situations, retries and long replies can cause both.

## Scenarios

A scenario is an entry in `configs/twwarhammer3/scenarios.json`; the `setup.py` docstring lists every field and the code that reads it. A job's manifest records the resolved entry (after `base` inheritance), and the job's source fingerprint versions the file.

An entry with `expect` is a declared benchmark scenario; that alone doesn't mean it was admitted or verified. `validate_declaration` requires a pinned map, pinned factions, explicit rosters and every required `expect` key. Timed modes need a timer of 1200, 2400 or 3600 s and an episode cap at least 120 s above it; survival and domination without a timer need `time_limit_s: null` and `timer_enabled: false`. Reinforcement pools must be explicit. Declared scenarios refuse `--attach`. A declaration error stops play before the job directory exists.

Setup then checks the battle against the declaration, and any mismatch stops the job before a battle is scored:
- the lobby: every menu step found its component; the map key; readbacks of battle type, difficulty, unit scale, realism, funds (and amount), timer and AI stats modifier. Since b42 the steps apply these settings, difficulty before the AI modifier;
- the first battle observation: unit scale, realism, player role, each army's AI modifier, both rosters and experience ranks (as multisets), both factions and the terrain grid.

Each rematch's starting state (positions, bearings, strength, ammunition, barriers, flight, abilities, magic, supplies, tickets) is compared with the job's first battle. A unit more than 1 m or 10° off, or any change in strength, abilities or resources, is flagged. Flags are reported, not enforced, because the snapshot depends on when the wall-clock autostart fires.

Rules:
- **Always pin the map**: the lobby keeps the last one used.
- **Freeze random draws before use**: copy the rosters, pin each faction and record substitutions (`frozen_from`, `substitutions`).
- **Held out means a different variant, not more launches.** More launches of a tuned scenario are more development battles. Held-out entries (`-heldout-wastes`, another map) stay out of tuning.
- **Measures about a group of units use declared unit keys** (`protected`), never the observed `class`.
- **Check content on the installation that will run it**: a unit card visible in the lobby doesn't prove the unit can be recruited.

Older declared families and the retired admission rule: [history](benchmark-implementation.md#history).

## Scenario design

The [scenario guidelines](scenario-guidelines.md) propose coverage across dimensions,
per-scenario winnability evidence, checks of the intended decision and release criteria.
Their marked choices await review; they do not change `suite-v1` eligibility or scoring.

Choose variations for coverage, not to steer how a controller should win. Pin every changed condition and compare controllers within it. A larger army changes combat balance, pathing and the number of orders, not only prompt length, and a map or roster change doesn't isolate one cause. A diagnostic for one tactic can be its own experiment.

Other battle types remain later questions: giving up ground and committing reserves in siege defence, spending reinforcements in survival, holding several points in Domination. Each needs its own success rule. Earlier pilots in those modes are in the [history](benchmark-implementation.md#history).

## Reproducibility

Here it means the declared conditions are checked and differences are reported. Starting fingerprints are compared, which doesn't prove identical internal state. The records must let someone else recount the results; a rerun by someone else is a separate check. Identical replays, identical battles across launches, seeded engine randomness and restoring a battle midway aren't available.

## Terms

| Term | Meaning |
|---|---|
| scenario | An entry in `configs/twwarhammer3/scenarios.json`. `expect` declares its benchmark setup; it doesn't mean the scenario was admitted or verified |
| variant | A scenario with one declared change (AI modifier, map, role), as its own entry; `split` is `development` or `held_out` |
| instance | The battle one launch builds; rematches restart it, and their starts are compared |
| trial | One controller playing an instance once (an episode) |
| track | A named set of observations, orders and timing rules |
| controller | Everything that turns observations into orders: code, model and provider, prompt, memory, helpers and limits. Its `card` records kind, source and disclosure |
| tactic card | Earlier work: a tactical question with a scenario, a witness (an example winning play), wrong plays and an evidence rule. A *scored* card passed its frozen admission rule ([tactic-cards.md](tactic-cards.md)) |

## Related pages

[Implementation, checks and open questions](benchmark-implementation.md) · [running it](benchmark-run.md) · [reports](reports.md) · [evaluation guidelines](evaluation-guidelines.md) · [the owner's original brief](WH3_latency_aware_benchmark_requirements.md) · [status](../state.md) · [log](log.md)
