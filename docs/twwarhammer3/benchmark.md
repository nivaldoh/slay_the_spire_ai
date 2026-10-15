# WH3 latency-aware battle benchmark

The benchmark as built: what it measures, the contract a controller plays under, how
scenarios are declared and admitted, and how results are computed. The owner's brief is
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
| §9 Initial release | Not reached: no scenario is admitted and no reference results exist | [Calibration](#calibration-stopped-2026-10-14) |

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
appends `+age-<D ms>ms`. Results are never pooled across tracks. History: `obs-v1/act-v1`
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
is admitted. Two Skaven swarm prototypes (`skv-swarm-dwf-line`, `dwf-line-skv-swarm`) were
screened on 2026-10-15; see [Scenario design](#scenario-design).

### Admission

A scenario joins a suite when, over repeated independent launches:
1. a declared competent reference wins before the timer roughly 30-70% of the time
   (neither floor nor ceiling; timer endings count as valid trials, not as wins here);
2. that reference beats the better trivial baseline on the paired active margin, with a
   95% interval above zero.

The reference is frozen before the repeated trials: `skills` if it can express the needed
tactics, else a declared model, hybrid or specialist script with its prompts and tuning
history recorded. Setup must be repeatable and the required controls must work. A
scenario is latency-sensitive only if an added-age experiment shows degradation.

## Scenario design

Owner direction, 2026-10-14: prioritize distinctive tactical challenges over balanced
general-purpose armies. Scenarios should give agents reasons to use specialist knowledge,
try unusual approaches and make difficult decisions. Battles should also be interesting
to watch. This is part of benchmark selection, not an optional showcase after calibration.

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

**Skaven swarm drafts (2026-10-15, definitions only, never run).** Both pin the Taurox
map, very hard AI, modifier 1.0, unit scale 0.75, custom funds 12000 and the 1200 s
timer, and use base Skaven (`wh2_main`) and Dwarf (`wh_main`) units whose keys exist in
the game's English localisation; both pass `validate_declaration` and build their lobby
steps offline.

| | `skv-swarm-dwf-line` (command a swarm) | `dwf-line-skv-swarm` (survive a swarm) |
|---|---|---|
| Player | 20 Skaven, attacking: Grey Seer (Ruin), Warlock Engineer, 6 Skavenslaves, 4 Clanrats, 2 Skavenslave Slingers, 2 Warpfire Throwers, Poisoned Wind Globadiers, Warp Lightning Cannon, Doomwheel, Rat Ogres | 7 Dwarfs, defending: Lord, 2 Ironbreakers, Longbeards, Irondrakes, Thunderers, Organ Gun |
| Enemy | 9 Dwarfs: Lord, Hammerers, 2 Ironbreakers, Longbeards, 2 Thunderers, Irondrakes, Organ Gun | 20 Skaven: Warlord, Plague Priest, 5 Skavenslaves, 5 Clanrats, 2 Stormvermin, 2 Plague Monks, 2 Skavenslave Slingers, Warp Lightning Cannon, Rat Ogres |
| Protected | Grey Seer, Warp Lightning Cannon | Irondrakes, Organ Gun |
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
audited one by one. Next: the same screens with Sol before any calibration.

A siege attacker needs gate, wall and equipment orders before admission. Review traces
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

## Calibration (stopped 2026-10-14)

The owner stopped calibration on 2026-10-14 (the runner exited at 22:19:59 UTC) and wants
to discuss its objective, reference, thresholds, trial count and cost before any further
run. Do not resume the recorded queue. What follows is the recorded plan, unchanged.

**Objective.** G1 finds a modifier at which the scenario passes [admission](#admission);
G2 then measures whether added information age costs the reference anything.

**G1 design** (frozen on source `6763d0e`):
- scenario `brt-cavalry-emp-assault` (modifier 1.0) and `-hard` (1.1): six Bretonnian
  cavalry units, Grail Knights as anchor, must defeat eight Empire units (four halberds,
  two handguns, a cannon, a foot general) on the Taurox map before the 1200 s timer;
  very hard AI, custom funds 8000, unit scale 0.75, realism off;
- reference: `llm_rules` on `gpt-6-sol`, effort low, rules prompt sha256 `f20379b6...`,
  chosen for its b7 flanking win, which is a viability demonstration, not admission;
- baselines: walk-nearest (`attack_nearest`) and run-nearest (`rush_nearest`); `hold`
  is an objective-failure control only (an idle attacker loses at the timer with both
  armies intact, margin 0);
- 12 launches alternating modifiers, each `--episodes 3` rotating the three controllers,
  rotation seeds 2026101401-06 (1.0) and 2026101411-16 (1.1), added age 0, start/
  episode/run timeouts 900/1320/5400 s, `--budget-usd 25 --show`;
- admission per modifier: the reference wins 2-4 of 6 before the timer, and its paired
  margin over each baseline has a 95% interval above zero. If both modifiers pass, G2
  uses 1.1; if one, that one; if neither, no G2 and scenario development continues;
- start flags: geometry flags stay in the primary result, with the secondary comparison
  without them; a changed roster, strength, loadout or resource stops later jobs for
  investigation. No tuning of prompt, rosters or controllers during G1 or G2.

**G2 design**: on the admitted setting, six launches rotate the reference at added ages
0, 6 and 10 s, seeds 2026101421-26. Primary contrast: 10 s minus 0 s active margin; a 95%
paired interval below zero shows sensitivity. The 6 s contrast is secondary. A null
result bounds only the detectable effect.

**What ran.** `bench-g1-cavalry-ai10-01-20261014` (1.0): walk-nearest lost at 411.2 s
(margin -0.796), run-nearest lost at 247.7 s (-0.628), Sol won at 528.2 s (+0.544,
$0.793363); 1373.64 s for the whole job. `bench-g1-cavalry-ai11-01-20261014` (1.1) was
interrupted during frontend setup, with no episode. The other ten launches never started.

**Size and cost of the recorded plan.** 54 battles: G1 36 (12 of them Sol), G2 18 (all
Sol). At about 23 minutes a launch, the 17 unplayed launches take about 6.5 hours of
machine time. Sol cost $0.62-0.79 a battle on this scenario (b7, G1 and the visual
acceptance), so the 29 unplayed Sol trials would cost about $18-23. Every model call draws
on the cumulative $25 WH3 ledger, which held $7.7949 on 2026-10-15 (`uv run python -m
twwarhammer3 spend`): the plan does not fit the cap at Sol prices. Sizing estimates from
the register (made with the old raw margin, 2026-10-14): six launches resolve a paired
gap of about 0.2 margin, three about 0.4; a 20-point win-rate difference is about
0.12-0.14 margin and needs 17-28 paired launches per contrast (36 with a Holm correction
over three); wins alone need about 97 battles per controller.

**Where it is.** Plan and queue state: `runs/twwarhammer3/calibration/g1-cavalry-plan.json`
and `g1-cavalry-plan-state.json`; stop note `g1-owner-stop.json`. Partial reports:
`runs/twwarhammer3/reports/g1-cavalry.json` and `.txt`, admission audit
`g1-cavalry-admission.json`, HTML `field-report.html`. G1 ran through the untracked
driver `calibration/run-g1.py`, with `audit-g1.py` checking admission. A resumed plan
would run through `scripts/wh3_queue.py` ([benchmark-run.md](benchmark-run.md#running-a-plan)),
which applies the start-change stop rule since 2026-10-15; admission is still audited
separately.

## Calibration: options for the owner's discussion (2026-10-15)

A proposal, not a plan: nothing below runs until the owner decides. It answers the five
questions the owner asked before any further calibration (objective, reference,
thresholds, trial count, cost) from the evidence already recorded. No game ran and no
model was called to write it.

**What the register already shows** on the cavalry assault (development screens and G1,
three source revisions, so descriptive only and never pooled into a result):

| Controller | `brt-cavalry-emp-assault` (AI ×1.0) | `-hard` (AI ×1.1) |
|---|---|---|
| `llm_rules`, Sol low | won 3 of 3: 432, 528 and 382 s; $0.62-0.79 a battle | not played |
| `llm_rules`, Luna low | lost 1 of 1 (247 s); $0.02 | lost 1 of 1 (271 s) |
| `llm_rules`, Luna medium | lost 1 of 1 (214 s) | lost 1 of 1 (342 s) |
| run-nearest | lost 4 of 4 | lost 1 of 1 |
| walk-nearest | lost 2 of 2 (one more ended in an infrastructure failure) | lost 1 of 1 |
| `hold` | lost 2 of 2 at the timer | lost 1 of 1 at the timer |

At ×1.0 the scenario already separates Sol from Luna and from the scripted baselines on
the outcome alone. Sol's 3 of 3 is compatible with any win rate from 44% to 100% (95%
Wilson), so ×1.0 may sit at Sol's ceiling, which the admission rule's 30-70% band was
meant to avoid; ×1.1 has never been played by Sol.

**1. Objective.** Proposed: decide whether one variant *discriminates*: the reference
wins sometimes but not always, while the cheaper model and the scripted baselines
rarely win. The recorded G1/G2 plan remains the alternative.

**2. Primary measure and thresholds.** The report redesign retired the active-strength
margin as a headline: it counts routing men as lost and weighs a cannon crew like a
lord. Proposed: the engine outcome before the timer is primary (wins out of battles,
with the time-limit rule stated), battle length and protected-unit survival are
descriptive, and the margin stays in the JSON. Admission rule 2 (paired margin interval
above zero) would become: every scripted baseline wins none of its battles and the
reference's wins exceed the best baseline's. Rule 1 (reference between 30 and 70%)
stays.

**3. Reference and rows.** `llm_rules` on `gpt-6-sol`, low effort, unchanged prompt;
`gpt-6-luna` low on the same prompt as a cheap second model row; run-nearest and
walk-nearest as baselines. `hold` is dropped: it can only lose at the timer, which is
already shown. Per-policy models are built, so the Luna row is paired within Sol's
launches: `--policy llm_rules,llm_rules@gpt-6-luna,rush_nearest,attack_nearest` with
`--model gpt-6-sol --effort low` rotates all four (`NAME@MODEL/EFFORT` also sets the
effort). Separate Luna launches would be unpaired.

**4. Variant and trial count.** Proposed: ×1.1 first, six launches, each rotating the
four controllers (24 battles: 6 per row). Reading it: Sol 2-4 of 6 with the baselines at
0 admits ×1.1; Sol 5-6 of 6 means both settings are likely too easy for Sol, and the
next step is a harder declaration (for example the Pegasus general variant) rather than
more trials; Sol 0-1 of 6 means ×1.0 is the setting to repeat. Six battles a row detect
only large gaps (2 of 6 against 0 of 6 is not significant on its own), so a second
block of six would follow before any claim beyond "admitted for development".

**5. Cost and time.** Sol: 6 × about $0.70 = about $4.20 (the 1077 s caster battle cost
$1.78, so a long battle can double it); Luna: 6 × about $0.02. The WH3 ledger held
$7.7949 of $25 on 2026-10-15, so the block fits with about $12.8 to spare. Machine time:
a G1 launch of three battles took 23 minutes; four battles about 30 minutes, so about 3
hours for six launches, unattended.

**6. A controller fix to decide first.** In the G1 Sol battle the first observation
after the opening orders (taken the instant they applied, before any unit moved) told
the model all six units had "stopped 300-350 m short", and it re-issued every route at
0:12, 0:20 and 0:30. The fix is on branch `wh3-llm-fresh-move`, unmerged: it changes
prompt text, so `llm` and `llm_rules` would get a new version and Sol results before
it would not pool with results after it. Proposed: merge it before the block above,
because a resumed calibration starts a new run set anyway.

**7. Delay (G2) afterwards.** With a win/loss outcome, three arms of six launches can
detect only a collapse. Proposed: run G2 only on an admitted variant, read it on wins
and battle length, and size it after the block above shows the reference's win rate.

## Calibration decided (2026-10-15)

The owner delegated the decisions above to the agent on 2026-10-15. Adopted as proposed,
as block C1:
- objective: whether `brt-cavalry-emp-assault-hard` (AI ×1.1) discriminates; primary
  measure the engine outcome before the timer, margin kept in the JSON only;
- rows, rotated in every launch: `llm_rules` on `gpt-6-sol` low (reference, `llm` v16),
  `llm_rules@gpt-6-luna` (low), run-nearest, walk-nearest; added age 0; no stills;
- six launches, rotation seeds 2026101501-06; launches 1-2 ran on the morning of
  2026-10-15, launches 3-6 wait in `runs/twwarhammer3/calibration/c1-plan-rest.json`;
- reading: Sol 2-4 of 6 with both baselines at 0 admits ×1.1 for development; 5-6 of 6
  moves the next block to a harder declaration; 0-1 of 6 moves it to ×1.0. No prompt,
  roster or controller change during C1.
- status after launches 1-2 (2026-10-15): Sol 1 of 2 (lost at 1017 s, won at 487 s), Luna
  and both baselines 0 of 2; Sol cost $0.67-1.44 a battle here
  ([log](log.md#2026-10-15-calibration-c1-launches-1-and-2)).

## Experiments the report should eventually present (definitions only)

From the report brief's section 10; none is built or scheduled.

- **Army size.** The cavalry assault at about ×0.5 (3 against 4 units), ×1 (6 against
  8) and ×2 (12 against 16), same composition ratios, map and timer, funds scaled. The
  axis is the number of units the controller commands, the lord counted as one. Each
  size is screened with the same reference and the two scripted baselines, because
  larger forces also change density, contact timing and the AI's behaviour on a fixed
  map. Observation tokens, reply time and order age are recorded beside the outcome, and
  a drop is reported as end-to-end degradation, not as a reasoning limit. Needs three new
  declarations and a lobby check of funds and unit caps.
- **Context.** One change per comparison on one scenario and model, for example adding
  the report's one-line unit roles to the observation against raw unit names. Reported
  with tokens, reply time and cost beside outcomes; the viewer's role text never reaches
  a controller unless it is the treatment.
- **Delay.** G2 above: added observation age (`--delay-seconds`), which is not the same
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
