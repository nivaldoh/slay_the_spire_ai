# WH3 latency-aware battle benchmark

The benchmark as built, with the [implementation plan](#implementation-plan) for the
owner's 2026-10-15 revision: difficult scenarios, partial progress and one report for the
suite. Planned measures are distinguished from recorded ones. The owner's brief is
[WH3_latency_aware_benchmark_requirements.md](WH3_latency_aware_benchmark_requirements.md).
How to run it: [benchmark-run.md](benchmark-run.md). The report: [reports.md](reports.md).
What is running now: [docs/state.md](../state.md). Dated history: [log.md](log.md).
Evidence paths under `runs/` are local and not in Git.

## Purpose

Another developer connects a battle controller, runs declared tactical scenarios against
the game AI in the original game, and compares it with other controllers under the same
observation, action and timing rules. The brief's acceptance question:

> Can an independent user evaluate a different battle controller under the same declared
> scenario, information, action, and timing rules, and understand both its performance
> and the limitations of the comparison?

Settled by the owner on 2026-10-14: each controller's whole latency, network included, is
part of its result, as it would be in a real deployment. A controller that loses because
it is slow has lost. Delay arms (below) are diagnostics beside that primary result.

## The brief, as built

| Brief | As built | Reference |
|---|---|---|
| §1 Tactical control, any controller design | Classic custom battles against the game AI; scripted, model and hybrid built-ins, and any importable class | `battle/controllers.py` |
| §2 Observation contract | Named track, visibility-filtered, exact numbers, not player-equivalent; scoring data stripped | [Contract](#observation-and-action-contract) |
| §2 Actions, failures | Basic orders only; harness refusals and engine rejections both reach the controller | `protocol.py` |
| §3 Timing | Unpaused 1x always; information age on the battle clock per batch; added-age arms | [Timing](#timing-and-latency) |
| §4 Scenarios, lifecycle | Declared entries checked in the lobby and in battle; rematches restart the same instance; development and held-out variants | [Scenarios](#scenarios) |
| §5 Outcomes, failures | Engine result only; timer endings labelled; every started trial recorded with its failure class | [Outcomes](#outcomes-measures-and-comparison) |
| §6 Baselines | `hold`, walk-nearest, run-nearest, `skills`; `llm`, `llm_rules`, `commander` | [controllers.md](controllers.md) |
| §7 Records | Manifest (revision, file hashes, resolved scenario, deployment pins, prompts), trace, result, register | [benchmark-run.md](benchmark-run.md) |
| §8 Path to RL | Episode boundaries, basis observations, orders, battle times, `ended_by`, throughput | [Outcomes](#outcomes-measures-and-comparison) |
| §9 First milestone | Built and accepted in the game (b1-b9 in the log) | [log.md](log.md) |
| §9 Initial release | In preparation: scenario progress measures and a consolidated suite comparison remain to be implemented | [Implementation plan](#implementation-plan) |

## Terms

| Term | Meaning |
|---|---|
| scenario | An entry in `configs/twwarhammer3/scenarios.json`; a benchmark scenario has `expect` |
| variant | A scenario with one declared change (modifier, map, role) as its own entry; `split` is `development` or `held_out` |
| instance | The battle one launch builds; every rematch restarts it, so one job is one instance |
| trial | One controller playing an instance once (an episode) |
| track | A named observation contract, action contract and timing policy |
| controller | Code that turns observations into orders; its `card` records kind, source and disclosure |

## Observation and action contract

The track is `obs-v3+terrain/act-v2/live-1x` (`play.TRACK`); a trial with added age D
appends `+age-<D ms>ms`. A track versions the information and actions supplied by the
environment and its timing rules. Controller memory or prompt changes are controller
versions; scoring changes are evaluator versions. They need not create new tracks.
Results from different conditions can appear in the same report, labelled separately;
they are never pooled across tracks. History: `obs-v1/act-v1`
(b1), `obs-v1+terrain` (b2, terrain grid), `obs-v2+terrain` (b3, enemy roster boundary
fix), `obs-v3+terrain/act-v2` (b8, morale and flight). The code is the reference:
- `engine/mailbox.py` module docstring: the observation, the acknowledgement and every
  bridge file;
- `protocol.py`: the order types and `validate_orders`;
- `mod/script/battle/mod/twwarhammer3_battle.lua`: what is published, and the engine
  rejection codes;
- [integration.md](integration.md): engine facts behind them.

**Label: structured state; enemy units filtered by the engine's visibility tests;
numerically exact; not player-equivalent.** Enemy units appear only while
`is_visible_to_alliance` holds and `is_hidden` does not. The enemy roster the lobby showed
is public; later arrivals join it only on sight, and a death is reported only if the unit
is visible then. `evaluation`, `final` and `setup` hold hidden information, and the harness
strips them before a controller sees a snapshot.

Known limits:
- positions, men and health are exact, finer than a player reads them;
- enemy units' targets are not observed;
- a friendly unit's `target` can name an enemy that is out of sight, and an attack on an
  enemy that died out of sight is answered `target_dead`, not `target_not_visible`;
- `class` comes from the land-unit class and missile range, not the unit's role (flying
  non-lords read `flying`);
- `is_hidden` is unverified, and so is whether the filter matches what a player sees;
- the terrain grid samples 16 m squares every 32 m at deployment; it is not a path planner.

Actions: `move`, `attack`, `halt`, `behaviour`, `ability` and `flight` per unit; the unit
`"army"` casts army abilities and, paid with supplies, `build`s and `reinforce`s. The
game still decides pathfinding, formation, melee responses, fire at will and skirmish,
retargeting, morale and spell effects. The harness has no tactical helpers; the `skills`
executor belongs to the `skills` and `commander` controllers.

Failures are never repaired. A batch that fails `validate_orders` against its basis
observation is sent as no orders; the trace records it and `acknowledge` receives the
reason (`validation_error`). The engine rejects single orders with a code in the
acknowledgement. Both count as invalid; the report splits them. An acknowledgement means
issued or queued, not executed. Never actions: session settings, the `restart` control,
menu steps and bridge files.

## Timing and latency

`live-1x` is the only timing policy. The battle runs unpaused at 1x; `require_realtime`
refuses any other session and play refuses an observation that says otherwise.
- The mod ticks on a 250 ms model-time callback, which fires every 300 ms because the
  engine clock moves in 100 ms steps. It publishes every `observe_ms` (1000, so every
  1.2 s) and at the tick that applies each request, empty ones included.
- The harness reads `observation.json` every 100 ms of wall time; the mod reads
  `orders.json` every 200 ms and applies a request at its next tick. The floor is one
  tick: orders apply 0.3 s (sometimes 0.6 s) after the state a fast controller saw.
- One request is in flight; the next decision starts on the observation that carries its
  acknowledgement. Units keep their orders and the game's behaviour meanwhile, and a
  reply based on an old snapshot is applied as it is, with its basis recorded.

Recorded per decision: basis `seq` and `time_ms`, decision time, `applied_ms`, `delay_ms`
(information age at application, battle clock), `think_s` and `roundtrip_s` (wall,
system clock). Model calls add wall seconds, provider processing time
(`openai-processing-ms`) and the returned model name; the commander adds `plan_age_s`.
Each episode records its battle/wall clock ratio. Network conditions are measured, not
controlled; rotating controllers within a launch spreads their variance.

**Added-age arms.** `--delay-seconds 0,6,10` crosses every controller with each age. The
controller decides on the newest buffered public snapshot at least D battle seconds old,
which stays its basis, so `delay_ms` remains the true age. The first D seconds fill the
buffer without decisions. D is a minimum: a blocking call leaves gaps in the buffer, so
the text and JSON reports give the actual snapshot age at decision beside the order
age. D = 0 is the natural latency, not zero latency. Arms are never pooled with each
other.

## Scenarios

A scenario is an entry in `configs/twwarhammer3/scenarios.json`; the `setup.py` module
docstring lists every field and the code that reads it. Manifests record the resolved
entry (after `base` inheritance), and the job's source fingerprint versions the file.

An entry with `expect` is a benchmark. `validate_declaration` requires a pinned map,
pinned factions and explicit rosters, every `expect` key, a finite timer (1200, 2400 or
3600 s) and an episode cap at least 120 s above it, and refuses `--attach`. A declaration
error or a realism preference that differs from `expect.realism` stops play before the
job directory exists. Setup then checks, and any mismatch stops the job before a trial is
scored:
- the lobby: every menu step found its component, the selected map key, and read-backs of
  battle type, difficulty, funds (and amount), timer and AI stats modifier. The steps set
  all of these except difficulty, which the lobby keeps from its last use;
- the first battle observation: unit scale, realism, player role, every army's AI
  modifier, both rosters as multisets, both factions and the terrain grid.

The start fingerprint (positions, bearings, strength, ammunition, barriers, flight,
ability loadouts, magic, supplies, tickets) of every rematch is compared with the job's
first episode. It is flagged above 1 m or 10°, or on any strength, loadout or resource
change. Flags are reported, not enforced, because the snapshot depends on when the
wall-clock autostart fires.

Rules:
- **Always pin the map**: the lobby keeps the last started one.
- **Freeze random draws before use**: copy the rosters, pin each faction, record
  substitutions (`frozen_from`, `substitutions`).
- **Held-out means variants, not launches.** More launches of a tuned scenario are more
  development instances. Held-out entries (`-heldout-wastes`, another map) stay out of
  tuning.
- **Family measures use declared unit keys** (`protected`), never the observed `class`.

Declared families: ranged protection (`dwf-sla-taurox`, `dwf-sla-herald`), cavalry
against anti-large (`brt-cavalry-emp-pikes`, `-pegasus` and the attacking `-assault`) and
a caster-led force (`tze-caster-skv-screen` and the attacking `-assault`). All but
`dwf-sla-taurox` have a `-hard` variant at modifier 1.1 and a `-heldout-wastes` map. None
passed the former admission rule. Two Skaven swarm prototypes (`skv-swarm-dwf-line`,
`dwf-line-skv-swarm`) were screened on 2026-10-15; see [Scenario design](#scenario-design).

### Admission

The 30-70% reference win-rate gate and paired-margin admission test were retired by the
owner's 2026-10-15 direction. G1 and C1 remain development evidence. Difficulty is not
adjusted automatically to a reference model's win rate.

For the planned suite, check that setup repeats correctly, the controls needed for the
challenge work, the engine result is recorded, and declared progress measures are
available. A hard scenario can remain useful when every controller loses but reaches
different milestones. If neither outcomes nor progress distinguish play, review the
scenario or measurement; do not assume an easier opponent is the remedy. Repetitions
measure variability, not eligibility. A claim of latency sensitivity still needs an
added-age experiment. Existing configuration labels such as `prototype_not_admitted`
are legacy metadata, pending the implementation below.

## Scenario design

Owner direction, 2026-10-14: prioritize distinctive tactical challenges over balanced
general-purpose armies. Scenarios should give agents reasons to use specialist knowledge,
try unusual approaches and make difficult decisions. Battles should also be interesting
to watch. These properties guide scenario selection alongside measurable progress.

- **Start with a tactical problem**: a faction mechanic and one or a few anchor units,
  ours or the enemy's, whose use changes the battle. Supporting units create decisions
  around the anchor (buy it time, expose a target, protect a casting window). Famous units
  that can all just attack the nearest target are not enough. Size is a design choice:
  small forces give clearer decisions, with a budget fitted to the pinned roster.
- **Give a real disadvantage**, and identify the obvious approach that should be costly.
  Keep several plausible responses open; no secret trick. These are author hypotheses,
  never instructions in a prompt; every controller gets the same public rules.
- **Choose role and victory condition with the question.** Defender timeout wins invited
  evasion in the compact pilots, even against a faster flying enemy. When the challenge
  needs engagement, an attacker role or a contested objective supplies the pressure.
  Verify the AI's actual response; advertised speed does not prove it will force a fight.

Each candidate records its question, anchors, pressure, plausible tactics, exact setup,
what a viewer should recognize (a flank opening, a spell window, a breach, a reversal) and
development and held-out variants; its entry's `brief` holds the summary.

| Candidate | Anchor and faction character | Decisions it should encourage |
|---|---|---|
| Cavalry facing anti-large infantry | A few exceptional shock units against a spear or halberd line | Split the defense, choose angles, coordinate charges, disengage before a losing grind |
| A caster-led force | A strong caster built around its lore and magic economy (Tzeentch first) | Trade screens for casting time, choose spells, protect or risk the caster, spend a shared resource |
| A siege against severe odds | A small defense with an anchor that shifts between objectives | Allocate supplies, abandon or contest points, time a committed assault |
| Command a Skaven swarm | Many cheap bodies around a few unusual weapons or casters | Spend expendable units for space and time, preserve the scarce damage |
| Survive a Skaven swarm | A much smaller force with limited crowd-clearing anchors | Shape the approach, save ammunition and magic, avoid encirclement |

**Skaven swarm prototypes (screened 2026-10-15).** Both pin the Taurox
map, very hard AI, modifier 1.0, unit scale 0.75, custom funds 12000 and the 1200 s
timer, and use base Skaven (`wh2_main`) and Dwarf (`wh_main`) units whose keys exist in
the game's English localisation; both pass `validate_declaration` and build their lobby
steps offline.

| | `skv-swarm-dwf-line` (command a swarm) | `dwf-line-skv-swarm` (survive a swarm) |
|---|---|---|
| Player | 20 Skaven, attacking: Warlord, Warlock Engineer, 6 Skavenslaves, 4 Clanrats, 2 Skavenslave Slingers, 2 Warpfire Throwers, Poisoned Wind Globadiers, Warp Lightning Cannon, Doomwheel, Rat Ogres | 7 Dwarfs, defending: Lord, 2 Ironbreakers, Longbeards, Irondrakes, Thunderers, Organ Gun |
| Enemy | 9 Dwarfs: Lord, Hammerers, 2 Ironbreakers, Longbeards, 2 Thunderers, Irondrakes, Organ Gun | 20 Skaven: Warlord, Plague Priest, 5 Skavenslaves, 5 Clanrats, 2 Stormvermin, 2 Plague Monks, 2 Skavenslave Slingers, Warp Lightning Cannon, Rat Ogres |
| Protected | Warlock Engineer, Warp Lightning Cannon | Irondrakes, Organ Gun |
| Naive risk | one all-in charge into the guns, then a cascade of routs | spreading out and being encircled |
| A viewer should see | slaves screening and pinning, weapon teams arriving together, the caster kept alive | a refused flank, ammunition saved for clusters, the line holding or folding |

Screened on 2026-10-15 (`llm` v16, harness b10, Luna low), one launch each. The lobby took
both 20-unit armies at 12000 (decoded costs 8025 and 8200, 6300 and 8350); the AI held its
line in the first and attacked in the second; no battle ended in seconds or at the timer.
Every player army was routed:

| Scenario | Controller | Lost at | Enemy active at the end | Order delay (mean) | Engine rejections |
|---|---|---|---|---|---|
| `skv-swarm-dwf-line` | `llm_rules`, Luna | 457 s | 0.706 | 9.22 s | 56 (30 to fleeing units, 15 unreachable, 11 abilities) |
| `skv-swarm-dwf-line` | run-nearest | 288 s | 0.921 | 0.31 s | 3 |
| `dwf-line-skv-swarm` | `llm_rules`, Luna | 444 s | 0.640 | 8.18 s | 17 |
| `dwf-line-skv-swarm` | `hold` | 565 s | 0.529 | 0.30 s | 0 |

Both are hard for these controllers and neither is degenerate. In the second, standing
still outlasted the model and left the swarm weaker (0.561 against 0.640 over the original
Skaven force; `enemy_active` also counts a unit the Skaven summoned during `hold`'s
battle). The trace review: between 5 and 168 s the model ordered the Organ Gun 11 times to
attack the enemy cannon about 670 m away (its range is 300 m); an attack on a target out
of range moves the unit, so the gun, then the Thunderers and Irondrakes, left the line,
fought alone and fled first (the gun at 202 s), and at 128 s the reply called the cannon,
403 m away, "now-in-range". The rejections began after the line broke. Over three
quarters of every shooter's ammunition went unspent in both battles. The abilities refused in the first match the known causes
(readiness lag and magic spent by issuance; [integration.md](integration.md)), not
audited one by one. Next: include both scenarios in the matched model comparison after
v17 and the progress measures are ready, with no further win-rate admission block.

A siege attacker needs gate, wall and equipment orders before evaluation. Review traces
for whether meaningful specialist decisions occurred: a win by an unrelated exploit or a
grossly superior anchor does not establish the challenge. Keep that review qualitative
and separate from outcomes; there is no creativity or entertainment score.

## Outcomes, measures and comparison

Trial statuses (`battle/play.py`):
- `won`, `lost`, `draw`: the engine's result, the only gameplay outcomes. `ended_by` is
  `time_limit` when the countdown expired (inferred from the last ticked deadline; see
  [integration.md](integration.md)); the report shows `time_limit` and keeps the engine
  result, so a defender's timeout win is not hidden.
- `truncated` (episode wall cap), `policy_failure` (the controller raised, failed to
  construct or close, or exhausted its re-asks), `budget_exhausted` (the WH3 ledger cap),
  `infrastructure_failure`, `unsupported_or_invalid` (a protocol or battle setup check
  failure) and `interrupted` (operator stop).

Every started trial is written to `result.json`, the manifest and the register. Any other
ending than an engine result stops the job; unplayed controllers stay unpaired.

`battle/report.py` computes, per evidence group (same resolved scenario, source revision,
game build, track, recorder and imagery settings, observe/tick/interval, model and
effort; never pooled):
- outcomes per controller and added age, with valid trials (engine results) over started
  ones and the failures listed;
- the non-timer win rate (non-timer wins over all valid trials) with a 95% Wilson
  interval, withheld when a controller has repeats within one launch;
- the active-strength margin: own men neither routing nor shattered over own starting
  men, minus the same for the enemy, from hidden totals. Reinforcements and summons join
  the denominator; unit value is not weighted (the register's `own_left` and
  `enemy_left` count routing men as alive);
- paired differences: for each pair of controllers, the margin difference per launch
  (rematch repeats averaged within it), a Student-t 95% interval over launches, an
  approximate 80%-power detectable difference, the unpaired launches, and a sensitivity
  result without launches whose starts were flagged;
- per trial: order age at application (non-empty batches), snapshot age at decision, plan
  age, model call seconds and provider processing time, returned model names, decisions
  per battle second, rejections by validation or engine code, protected-unit survival,
  objective shares held (integrated on engine ticks), supplies left, accepted builds and
  reinforcements by type, tokens, USD, wall seconds and clock ratio;
- per controller, the median of its trials' median order ages (the HTML page's typical
  order delay);
- throughput: valid trials per job wall hour, counting setup, resets and failed jobs.

The text and JSON reports end with the limitations stated in `report.collect`. The HTML
page shows outcomes, the typical order delay and cost per battle, and leaves the margin,
paired differences and limitations to those files ([reports.md](reports.md)).

Reproducibility promises the same declared scenario checked in every job, the same start
for every controller within a launch (fingerprint reported), and records that recompute
every measure. It does not promise identical trajectories, identical instances across
launches or replay of a job.

## Evidence behind the design

Measured on 2026-10-13/14 from the register and runs; the full analysis is Part 1 of
this page before its rewrite (`git show d606d39:docs/twwarhammer3/benchmark.md`):
- **A rematch restarts the same instance** (30 of 32 jobs matched to 0.1 m and 1°; the
  two exceptions ended deployment 100 ms later). **A new launch does not** (up to 5 m and
  48° apart over 14 `kho5-dwf5` launches). Launches are the sampling unit.
- **The engine replays a battle when orders land on the same ticks.** Three of six
  `skills-v1.2-kho` episodes were identical to 530 s; one batch applied a tick later
  diverged the rest. Repeats of a controller on one instance are correlated.
- **`kho5-dwf5` changed maps**: it named none and the lobby kept a random draw's map.
- **WSL's monotonic clock ran 0-11% slow**, so wall durations use the system clock.
- **The raw margin contradicted the outcome** in 16 of 108 battles (routing men counted
  as alive), hence the active margin.
- **Throughput**: about 8 episodes an hour; a one-episode job took a median 409 s for a
  317 s battle.
- **Information age**: `llm` v14 median 6.0 s (90th percentile 9.2 s); scripted controllers
  one tick; commander plans 6.0 s old when adopted. Pausing during inference (`llm` v4,
  3 battles per arm) showed no effect, but could only have detected a large one.
- **The setup probe** (`runs/twwarhammer3/benchmark-probe-20261014`, source `f2c8463`,
  `dwf-sla-taurox`) recruited 24 cards by id and read the lobby and battle settings back.
  `hold` lost at 298 s; its 965 empty requests applied after 0.3 s (954) or 0.6 s (11).
  Its protected units met melee 8.4, 13.2, 24.0, 46.2 and 47.4 s after an enemy came
  within 100 m: one reaction window shorter than a slow model's age plus period.
- **The AI stats modifier** changed only the AI units' stats in the b2 and b8 startup
  snapshots. Lobby options, modifier getters and terrain sampling are in
  [integration.md](integration.md).

## Implementation plan

Prepared on 2026-10-15 at the owner's request. This is the next implementation, not
completed functionality or an instruction to launch jobs now. No controller, metric,
scenario configuration or report output changed during preparation.

### 1. Hard challenges and partial progress

Keep engine victory, defeat, draw, timer endings and failures. Add a small, versioned
mapping of scenario measures in `battle/report.py`, keyed by declared unit types, with
its definitions included in report JSON and explained in HTML. Start with the three
existing challenges below; no general scoring framework or composite leaderboard score.
A milestone is an accomplishment, not a requirement to use the designer's preferred
route or tactic. Declare measures before collecting the next comparison. Measures
applied retrospectively to C1 or the swarm screens are exploratory.

The audit of `strength()` in the battle Lua, `play.track_objectives`, `report.collect`
and recorded C1/swarm results found:

| Measure | Available evidence and next work |
|---|---|
| Casualties by unit type | Final hidden totals already contain `men0` and `men` per type. Derive `(men0 - men) / men0` where the denominator is positive; describe it as soldier/entity losses, not HP damage or unit value. |
| Active survivors by unit type | `active_men / men0` is recorded; excludes routing and shattered units. Show it separately from survivors including routed men. Existing `protected_left` is an active-men fraction, despite the broad name. |
| Point control and resources | Engine-tick point ownership integrals, final supplies and tickets already exist for applicable battle types. Show duration and ownership time/share together; leftover supplies are descriptive, not a reward for refusing to spend. |
| Destruction, routing and event times | Current final totals aggregate by type, not individual unit. Public replay events depend on visibility; zero active men does not prove destruction. Exact per-unit milestones and authoritative first-achievement times need additional evaluation-only recording. |
| Army value or HP damage | Final totals do not contain either. Defer weighting and HP scores until starting values, damage, summons, healing and reinforcement treatment are defined and recorded. Raw headcount is not a universal army score. |

Proposed first measures (engine outcome, natural order delay, cost and failures accompany
all rows):

| Scenario | Initial progress view |
|---|---|
| `brt-cavalry-emp-assault-hard` | Casualty and active fractions for enemy Great Cannons, Handgunners and Halberdiers; surviving and active player cavalry by type. Keep AI ×1.1. |
| `skv-swarm-dwf-line` | Enemy gun-line and elite-infantry casualties by type; own weapon-team survivors; caster survival. A one-model lord/caster's men count gives alive/dead, not health. |
| `dwf-line-skv-swarm` | Enemy losses by type, protected Irondrake/Organ Gun survivors and active strength, duration beside outcome. No points exist on this land map; duration alone must not reward hiding. |

Before implementing fractions, specify denominators and missing-data behavior. The
current `men0` includes units registered after the start, including summons; do not call
it the original army. Preserve that recorded denominator and label it for the first
view. Scoring only the original force, especially when summons share a type, needs
per-unit initial-membership recording. Missing fields mean unavailable, not zero.
Historical traces/results and `results.csv` stay unchanged; derived measures belong in
reports with their evaluator version. Scoring data remains outside policy inputs and
the public replay. Timing from sparse observations is an observed bound, not an exact
achievement time. These limits leave room for later milestones without delaying a
useful first progress comparison.

### 2. Integrate v17 and use the right version labels

`wh3-llm-v17` (`c1cc14b`) changes only `battle/llm.py` and its regression tests: shooter
range feedback and last-sighting memory. It consumes already-public observations;
`play.TRACK`, the Lua observation and the action/timing contracts are unchanged. Keep
`obs-v3+terrain/act-v2/live-1x`; earlier notes calling this `obs-v4` were incorrect.
The commander imports `remember` and `render_state`, so the integration must also be
logged as its next version (v4), alongside `llm`/`llm_rules` v17. This branch has not
been merged by the planning work.

Review the branch against current main, run the LLM/commander/prompt tests, change golden
prompts only where their expected rendering intentionally changes, then the WH3 suite
and lint. Check the two feedback cases in a real battle during the first evaluation
launch. Historical results retain their original revisions. Compare models on the same
controller version and conditions; show older controller versions in the same report
without attributing their differences solely to model quality. An actual future change
to environment information, actions or timing would change the track. New evaluator
measures need their own version, not a new observation track.

### 3. Evaluate the first suite, then expand

Use the three scenarios above as development challenges; the existing screens already
establish working setup. First proposed batch: one new launch per scenario, each rotating
Sol low and Luna low under `llm_rules`, plus run-nearest/walk-nearest on cavalry,
run-nearest on the swarm attack and `hold` on the Dwarf defence (10 battles total).
This is an exploratory comparison, not a stable model ranking. Keep rosters, controller
code, prompts, observation timing and recording settings fixed across the batch; retain
the rematch-start checks and held-out variants. Replace legacy admission status labels
in `configs/twwarhammer3/scenarios.json` as part of that implementation, without changing
rosters or silently rewriting old manifests.

Before launching, declare a small fixed repeat batch and cost allowance. Repetitions
use independent launches with matched controllers; do not stop when a preferred model
wins or a significance threshold is crossed. Additional batches may follow interesting
findings, labelled exploratory with their selection reason and all earlier trials shown.
The $25 cumulative ledger cap has $10.7821 left at preparation time; C1 Sol battles cost
$0.67-1.44 in its first two launches, and swarm Sol cost is unknown. Estimate the first
batch conservatively and retain room for repeats before adding models or scenarios.
No paid run is part of this preparation.

Generate a new queue plan only after implementation is committed. The old G1 plans,
completed C1 plans and unstarted `swarm-sol-screens-plan.json` are historical inputs;
do not resume or merely repin them as the new suite. A siege follows when gate, wall
and equipment controls work. Broader random draws, commander comparisons, other battle
types and army-size/context experiments remain later work, not initial-release gates.

### 4. Keep natural latency; defer added delay

Every comparison retains measured order age, outcome/progress, cost and reliability at
unpaused 1x. The existing `--delay-seconds 0,6,10` capability remains available, but no
G2 block is scheduled. Use it later on a scenario with interpretable progress measures
and a concrete latency question, without requiring a particular win rate. Compare the
same frozen controller across added ages and report actual information age; natural
latency differences between models alone do not establish a causal latency effect.

### 5. One benchmark report

Use `runs/twwarhammer3/reports/benchmark.html` as the planned canonical entry point for
the entire suite, with `.json` and `.txt` companions. Existing `report JOB [JOB ...]`
already accepts all scenarios and `report_html.display_data` provides navigation between
them. Extend that path; no separate site, server or new report framework is needed.

Add a compact suite overview (coverage, outcomes and scenario progress per model), then
in-page access to each challenge's comparison, run settings, notes and replays. Preserve
the current watch/understand/compare experience. Missing runs or measures stay explicit;
there is no aggregate ranking across unlike scenario measures. Historical runs and
interface/controller versions remain accessible with labelled conditions, not pooled
into current results. Existing grouping is conservative about source revisions; retain
it initially rather than inventing new compatibility inference.

Select an explicit list of input jobs, including failures and older evidence; the report
JSON already records this list. Do not glob all local runs into the benchmark or choose
only successes. Keep existing reports as historical artifacts until the canonical one
is validated. Start with the current embedded assets. Supporting files are allowed if
measured size or load time warrants them; any such packaging must still open locally
without a service and be tested as a copied bundle. A giant JSON `fetch` from `file://`
is not assumed to work. No consolidated report has been generated during preparation.

### Delivery order and checks

1. Integrate and log v17 plus the commander's shared rendering change. Keep other prompt
   or executor changes outside this batch.
2. Implement the first report-derived measures and overview using saved evidence; test
   casualty/active distinctions, zero or missing denominators, summons, historical data,
   and the scoring/policy boundary. Use existing report, replay and Lua test modules as
   appropriate; do not rewrite the register or saved jobs.
3. Build the single report from an explicit historical job list. Extend the browser
   check with several actual scenarios, navigation, missing metrics, mixed controller
   versions and replays; check desktop/mobile, offline opening, size and load time.
4. Freeze scoring definitions, code and the first run batch; run the matched launches,
   inspect real-game behavior, then rebuild the same canonical report. Do not promise
   new Lua mechanics or exact milestones on fixture evidence alone.

The next milestone is complete when the three challenges and model/baseline rows can
be inspected in that one report, with clear progress definitions, sample counts,
failures, conditions and replays. Further instrumentation is justified by gaps that
prevent useful comparison, not by a predetermined reference win rate.

## Calibration (stopped 2026-10-14)

Historical design, superseded by the implementation plan above. G1 proposed six launches
at each AI modifier (×1.0 and ×1.1), rotating Sol low `llm_rules`, walk-nearest and
run-nearest. Admission required Sol to win 2-4 of 6 before the timer and beat both
baselines on paired active margin with a 95% interval above zero. G2 would then rotate
0/6/10 s added ages on an admitted variant. The owner stopped G1 on 2026-10-14; it remains
partial, and G2 never ran. Outcomes and stop details are in the
[log](log.md#2026-10-14-partial-g1-and-owner-requested-stop).

Plans, state files, audits and runners under `runs/twwarhammer3/calibration/` remain
historical evidence; `scripts/wh3_queue.py` is the supported runner for future jobs.
The full former design and its estimates remain in git at `ae7ca31:docs/twwarhammer3/benchmark.md`.

## Calibration: options for the owner's discussion (2026-10-15)

Historical alternatives, adopted as C1 below and now superseded. They proposed engine
outcome as the primary measure, Sol as reference, adding Luna to the paired rotation,
and trying ×1.1 first. The options also proposed fixing fresh moves mislabelled as
stopped before running; that fix became v16. The original discussion remains at the
revision above; the [decision entry](log.md#2026-10-15-harness-b10-llm-v16-and-the-calibration-decisions)
records what was adopted.

## Calibration decided (2026-10-15)

Historical C1 design: six launches of `brt-cavalry-emp-assault-hard`, rotation seeds
2026101501-06, `llm` v16 on harness b10, added age 0, no stills. Every launch rotated
`llm_rules` on Sol low, `llm_rules@gpt-6-luna` low, run-nearest and walk-nearest.
The original rule admitted ×1.1 on Sol 2-4 wins with both baselines at zero, made it
harder on 5-6, and moved to ×1.0 on 0-1. It is no longer the next-run rule.

All six launches finished on 2026-10-15: Sol 1 of 6; Luna and both baselines 0 of 6,
all engine outcomes. The report is `runs/twwarhammer3/reports/c1-cavalry-ai11.html`.
[Launches 1-2](log.md#2026-10-15-calibration-c1-launches-1-and-2) include early trace
reviews; [launches 3-6](log.md#2026-10-15-calibration-c1-launches-3-to-6) complete the
register. The revised plan retains these trials as development evidence and does not
schedule an easier calibration block.

## Experiments the report should eventually present (definitions only)

From the report brief's section 10; none of these experiment series has run or is
scheduled. Added observation age is already supported by the harness.

- **Army size.** The cavalry assault at about ×0.5 (3 against 4 units), ×1 (6 against
  8) and ×2 (12 against 16), same composition ratios, map and timer, funds scaled. The
  axis is the number of units the controller commands, the lord counted as one. Each
  size is screened with the same reference and the two scripted baselines, because
  larger forces also change density, contact timing and the AI's behaviour on a fixed
  map. Observation tokens, reply time and order age are recorded beside the outcome, and
  a drop is reported as end-to-end degradation, not as a reasoning limit. Needs three new
  declarations and a lobby check of funds and unit caps. Motivating observation (uncontrolled,
  across harness versions and battles; Luna low, mean order delay per battle): about 5-7 s
  with 10 units on the field, 6.5-7.3 s with 24, 8.2 s with 27 and 9.2 s with 29, the last
  two from the 2026-10-15 swarm screens. Unit costs now come from `scripts/wh3_db.py`.
- **Context.** One change per comparison on one scenario and model, for example adding
  the report's one-line unit roles to the observation against raw unit names. Reported
  with tokens, reply time and cost beside outcomes; the viewer's role text never reaches
  a controller unless it is the treatment.
- **Delay.** Deferred added observation age (`--delay-seconds`), which is not the same
  intervention as a slower model; natural latency differences between models stay
  observations, not a dose-response curve.

## Later

Built only when a result or the owner calls for it:
- **A visual track and robotics models** (owner direction, 2026-10-14): a game image with
  each observation for vision models and VLAs, as its own track. Today's stills are
  presentation only ([reports.md](reports.md)); the track needs per-decision capture,
  camera and timing rules, an adapter from robot actions to orders, and hardware cards.
- **Model against model, possibly in teams** (owner idea, 2026-10-14): the battle script
  drives both armies with per-side views (try first), or local multiplayer with one
  client per side (desync risk). Results become relative ratings.
- An equal-tempo `age-D/P` track (fixed application age and decision period) to separate
  reasoning from speed; per-controller USD caps; an `exec:` adapter for controllers not
  written in Python; a reduced observation track if player equivalence becomes a goal; a
  value-weighted margin; a reaction-window screen with a pass mark.
- Records not kept yet: each hybrid executor order's basis, when the mod read a request,
  and when an order's effect first showed.
- In-game checks still open: `teleport_to_location` starting arrangements, restarting an
  undecided battle (play never does: such an ending stops the job), whether a launch
  reseeds the engine, whether the visibility filter matches the player's view, and
  whether the HUD's balance-of-power bar (kept out of observations) is player information.
