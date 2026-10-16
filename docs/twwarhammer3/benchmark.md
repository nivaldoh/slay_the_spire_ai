# WH3 latency-aware battle benchmark

The benchmark as built, with the [implementation plan](#implementation-plan) revised on
2026-10-16: keep the scenario collection provisional and calibrate its challenges before
another expensive model comparison. Planned measures are distinguished from recorded ones. The owner's brief is
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
| §9 Initial release | Shared measures, the consolidated report and six candidate families have live evidence; calibration and final selection remain open | [Implementation plan](#implementation-plan) |

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

The track is `obs-v4+terrain/act-v2/live-1x` (`play.TRACK`); a trial with added age D
appends `+age-<D ms>ms`. A track versions the information and actions supplied by the
environment and its timing rules. Controller memory or prompt changes are controller
versions; scoring changes are evaluator versions. They need not create new tracks.
Results from different conditions can appear in the same report, labelled separately;
they are never pooled across tracks. History: `obs-v1/act-v1`
(b1), `obs-v1+terrain` (b2, terrain grid), `obs-v2+terrain` (b3, enemy roster boundary
fix), `obs-v3+terrain/act-v2` (b8, morale and flight), `obs-v4+terrain/act-v2`
(b12, optional public custom objectives). The code is the reference:
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
pinned factions and explicit rosters and every required `expect` key. Timed modes need a
finite timer (1200, 2400 or 3600 s) and an episode cap at least 120 s above it; native
timerless survival/domination require `time_limit_s: null` and `timer_enabled: false`.
Declared reinforcement pools must be explicit. All declarations refuse `--attach`. A declaration
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
available. Use common measures first; scenario-specific scoring can wait. A hard
scenario can remain useful when every controller loses but makes different progress. If neither outcomes nor progress distinguish play, review the
scenario or measurement; do not assume an easier opponent is the remedy. Repetitions
measure variability, not eligibility. A claim of latency sensitivity still needs an
added-age experiment. Existing configuration labels such as `prototype_not_admitted`
are legacy metadata, not a current eligibility gate.

## Scenario design

Owner direction, 2026-10-16: aim for a compact core of **6–8 distinct decision
problems**. A different faction, map, army size, role or difficulty is a variant unless
it introduces a different consequential choice. Keep historical evidence, but do not
count variants or native-mode smoke tests as extra benchmark coverage.

Follow-up owner note, 2026-10-16: **less is more**. This benchmark is slow to execute,
so prioritize a smaller set of high-quality scenarios. Quality means benchmark usefulness:
does this scenario help us learn something new about the models? The 6–8 range is a
planning guide, not a quota. Redundant scenarios do not justify their execution time;
each retained scenario should answer a distinct question. This is planning guidance;
no scenario selection changes are made by recording it.

**Owner direction after M1, 2026-10-16:** keep the collection provisional until the
strongest models have been tested. The audit's retain/demote recommendations below are
development priorities, not a settled core. First improve challenge quality and the
expected information from expensive runs; the [revised plan](#implementation-plan) is
planning only, with no implementation or new runs authorized by this revision.

Before adding a core candidate, record its question, scarce resource or commitment,
at least two credible plays, nearest existing family, reason it adds coverage, public
information/actions needed and observable evidence. These are analyst hypotheses, never
tactical advice inserted into a policy prompt. Mechanics and objective rules are public.
A candidate stays exploratory until the game shows that its choices are feasible.

| Family / candidate | Benchmark question and hard choice | Credible alternatives to inspect | Nearest family; why distinct | Evidence |
|---|---|---|---|---|
| Cavalry against anti-large | Can the controller create a safe charge window, then disengage? | Split the line and strike a flank; concentrate charges against an isolated target | Conquest; here contact and disengagement determine success, rather than distributed ticket income | Charge/withdrawal orders, contacts, unit survival and enemy strength |
| Caster-led force | Which spell opportunity justifies spending shared mana and risking the caster? | Spend early on a useful cluster; screen and wait for a better casting window | Swarm assault; the binding resource is shared mana and spell timing | Mana, accepted casts, target geometry, screen/caster survival |
| Command a Skaven swarm | How much cheap infantry should be spent to deliver scarce weapons safely? | Pin broadly while weapons concentrate; send successive screens down one approach | Caster; several independent damage units need synchronized access, not one casting budget | Screen contacts/routs, weapon firing and survival; prior attacks exposed this coordination problem |
| Survive a Skaven swarm | How should a compact gunline preserve firing space under encirclement? | Refuse one flank and concentrate fire; fall back with an intact screen | Swarm assault; the player allocates finite fire lanes/ammunition, rather than expendable screens | Gun movement, ammunition, encirclement and time alive. Standing still beat the model in the existing screen; keep the distinction provisional |
| `chd-reserve-grn-siege` — territorial defence | When should a point be conceded, and where should the only mobile reserve commit? | Contest outer points with construction support; fall back and concentrate around the decisive point | Defensive swarm; geographically separate victory points and construction supplies make territory itself a resource | Point ownership time, supplies/builds, reserve movement, surviving garrison |
| `ksl-reserves-survival` — reinforcement budgeting | Buy relief now or preserve supplies for a more expensive reinforcement? | Buy cheap fresh screens; save for a specialist while conserving the starting force | Defensive swarm; purchases change the available army over an unknown future sequence | Supplies, purchases by type/time, fresh units, ammunition, duration and native objectives |
| `emp-battery-skv-evacuation` — asset evacuation (deferred, low priority) | How much scouting and route-clearing effort can the escort afford before its deadline? | Guard the batteries on a direct route; scout and detour around revealed threats | Ranged protection; moving a designated asset to a public destination under incomplete information is the objective | Batteries in zone, survivors, deadline, sightings, escort separation and engine-confirmed ending |

**Evacuation deferred, 2026-10-16.** Its first live attempt failed the authored-placement check before any model call ([log](log.md#2026-10-16-evacuation-deferred-controller-version-labels-fixed)), and the owner moved the custom scenario to the end of the plan as a low-priority item. It stays specified and offline-tested, outside the active core: six candidate families with live evidence remain.

**Conquest was demoted during the live check.** `sla-detachments-dwf-conquest` has one
central point, not the separated objectives its original brief assumed. It therefore
fails its stated novelty criterion and remains reference evidence, outside this seven-family
candidate core. [Creative Assembly's Conquest description](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/23-total-war-warhammer-iii-patch-5-1-0)
confirms a central point. The installed build reports a 600-ticket target, despite its
older help text saying 500; use the numeric engine state. Distributed control belongs in
a future Domination candidate (the existing Arnheim pilot exposes three separated points),
with its reinforcement mechanic explicitly separated from the survival question. Do not
count it as new coverage before it is designed and screened.

Cavalry pikes/Pegasus/assault, their difficulty revisions and held-out maps are **one
family**. The caster variants likewise form one family. Older Dwarf/Slaanesh ranged
protection and the Khorne/Dwarf mode pilots remain historical/reference evidence.
Both swarm roles provisionally occupy separate slots because they reverse the scarce
resource: expendable screens versus limited firing space. If new trace evidence shows
that either collapses to an already-covered decision, demote it to a variant. Do not
add a ninth family to preserve a theme. Cathay cohesion under bombardment is a reserve
replacement: proximity support versus dispersal, requiring an actual mechanic check.

The roster inventory is local evidence in
`runs/twwarhammer3/capability-probes/expansion-20261016/`. Selectable faction menus and
unit cards are evidence of lobby availability, not a complete ownership audit. Steam
entitlement presence was checked without retaining authentication-ticket contents.
The implementation uses playable Chaos Dwarfs and Champions of Chaos units. Wood Elf
cards appeared in the inventory but were inactive and recruited no units in the live lobby;
the evacuation pilot therefore uses available base Skaven opposition. Gutter Runners
have `stalk` in the installed database, preserving the scouting question. This is
availability evidence, not a claim about the complete DLC purchase history. Mechanics
research: the [Chaos Dwarfs roster](https://store.steampowered.com/app/2059190/Total_War_WARHAMMER_III__Forge_of_the_Chaos_Dwarfs/),
[Wood Elves](https://store.steampowered.com/app/534331/?l=english), and
[Creative Assembly's Cathay update](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/98).
Local documentation from the installed build governs the script API.

**New native screens, 2026-10-16.** Siege defence produced a Sol loss at 508 s and a
Luna win at 688 s from matching starts. Construction, reserve commitment, firing and
fallback were executable. Survival produced losses at 322/406 s (Luna/Sol): four late
purchases versus all seven initial reserves purchased earlier, followed by lost spawn
access with supplies unspent. Keep both as exploratory families. Initial survival pools
are fixed; later native pool changes are observed, not artificially frozen. These pairs
establish usable choices, not rankings. See the [b12 log](log.md#2026-10-16-harness-b12-and-distinct-scenario-families).

**Retained caster evidence, reviewed 2026-10-16.** The existing base caster scenario has
three b4 outcomes (Luna 963 s, hold 613 s, walk-nearest 301 s, all losses) and a b7 Sol
loss at 1077 s. Both model runs began with 12 available mana and 68 in reserve. Their
accepted ability orders differed materially: Luna requested 16 ordinary and 3 upgraded
Blue Fires; Sol requested 3 upgraded and 1 ordinary Firestorm, alongside other spells and
abilities. Their final available mana was 6 and 35 respectively, with reserve nearly
exhausted. Accepted orders do not prove spell impact, and the harness versions differ,
so this is evidence of an available mana-allocation problem, not a model ranking.
No extra caster screen is needed for this expansion tranche; keep it as a provisional
core family and audit actual spell value in later controlled work.

**Family audit under "less is more" (2026-10-16, recommendation for the owner).** An
independent read of the saved battles asked of each live family: which plays were
executed, whether results moved with the controller's decisions, and whether its decision
collapses into another family's. [H] marks conclusions that rest on hidden evaluation data.
The selection itself is the owner's call; nothing has been demoted.

| Family | Evidence | Recommendation |
|---|---|---|
| Cavalry against anti-large | Sol won by flanking to the guns (382 s, 487 s); Luna charged into the halberds. At ×1.1 Sol 1/6, Luna 0/8, scripted 0 | Retain |
| Siege defence | Identical starts, opposite outcomes: Sol's lord went alone and its cannon never fired; Luna held the gate, fired the cannon and retook a point. Ownership time (92% both) and the opening build did not discriminate | Retain |
| Command a Skaven swarm | Luna 457 s against run-nearest 288 s (enemy active 0.71 against 0.92 [H]); the only large-army latency test (20 units, mean order age 9.2 s) | Retain; it needs Sol battles |
| Caster-led force | All model evidence predates flight orders and the current prompts; as a timer-winning defender, Sol spent its second half evading | Screen the attacker variant `tze-caster-skv-assault` (declared in b8, never run) first |
| Survive a Skaven swarm | Four losses, 444-593 s; `hold` matched or beat both `llm_rules` battles (0.53 against 0.64/0.84 [H]) | Demote to evidence; siege defence covers the gunline problem with more workable options |
| Kislev reinforcement budgeting | Income was about 30 supplies/s (trace-checked); Sol bought the whole pool and kept 5165. The binding constraint was holding the spawn point, the siege's question | Demote unless supplies can be made scarce |

That leaves a core of three distinct questions (manoeuvre against counters, territory and
reserve, mass coordination under latency), with the caster as a conditional fourth. The
overnight matched round (M1, [log](log.md#2026-10-16-matched-round-m1-on-the-retained-core-plan))
runs the retained three first and the two demotion candidates last, so the decision can
rest on matched evidence.

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
audited one by one. Keep both scenarios and their existing evidence in the shared
report; broader scenario coverage now precedes further matched repeats.

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
- per controller, the median of its trials' median order ages in the collector; the HTML
  pools order batches (adopted plans for commander) to show its typical delay;
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

### Current proposal: calibrate before a broad model comparison

Implementation resumed on 2026-10-16 after the cleanup review. OpenRouter support and
its small schema checks are complete ([log](log.md#2026-10-16-harness-b13-shared-openrouter-transport));
the saved-evidence calibration cards below are the next checkpoint. The planning-only
wording in the original revision describes its authorization at that time.

Revised after M1 on 2026-10-16 at the owner's request. **Planning only:** no code,
scenario declarations, report selection or scoring changes, game launches or API calls
are part of this revision. The sequence below supersedes the earlier implementation
sequence and the proposal to settle the core from M1.

M1 is development evidence about the tested model/controller configurations. Three
wins can flag a possible ceiling; three losses do not prove a scenario is impossible
or uninformative. Neither establishes how the strongest models will perform. Preserve
all six candidate families for review, the earlier audit and all outcomes. Conquest's
one-point novelty failure still stands, and custom evacuation remains deferred. The
report's current core labels are a presentation selection, not a final benchmark.

**1. Extract more information from saved battles before buying more.** For each family,
write a short calibration card: the capability under test; the actual scarce resource;
two feasible competing plays; observed turning points and failure causes; a suspected
easy strategy or exploit; and the smallest unanswered question worth a new battle.
Separate interface defects, tactical mistakes, natural latency, overwhelming forces
and inconclusive evidence. Check whether winning models solved the intended problem or
bypassed it. Reuse traces, replays, start checks, recorded resources and existing unit
data; no model calls are needed for this pass. Keep analyst tactics out of model prompts.

**2. Make the challenge fair and its result interpretable.** Before new model
calibration, address the observed stale ability-readiness feedback and missing rule
that routing units ignore orders in a logged controller/interface revision, with
targeted engine checks. Verify any mechanic essential to a proposed challenge through
the actual public interface. No general rewrite or unrelated cleanup is required.
Retain engine outcomes and common measures; identify the recorded evidence that would
distinguish good choices within wins or losses. Examples are reserve survival and
commitment, weapon firing behind a screen, and spell timing alongside mana and target
state. Accepted orders and mana expenditure alone do not establish effective execution
or spell value. Avoid a new composite score or speculative creativity score.

**3. Draft a small difficulty ladder for promising families.** Preserve each current
scenario as an anchor; propose at most two variants initially, each changing one
justified factor. Prefer pressure on an actual decision (reserve allocation, exposure,
mana or ammunition scarcity, competing threats) to generic stat inflation. A numerical
odds adjustment can still be useful when it preserves feasible counterplay. Larger
armies also change workload, prompt size and latency, so do not call that a pure
difficulty or reasoning intervention. There is no target win-rate admission rule.

The following are hypotheses to investigate, not selected settings or promised engine
capabilities. Check feasibility before implementing a variant:

| Family | First calibration question | Candidate adjustment or diagnostic |
|---|---|---|
| Siege defence | Do reserve placement and territory trades remain necessary once the obvious mistakes disappear? | Test whether a simple central defence solves it; vary pressure on a second approach or reserve availability while retaining workable fallback choices. |
| Caster assault | Does winning require choosing spell windows and preserving the caster, or does one repeatable cast/retreat pattern suffice? | Contrast simple casting approaches; vary one of starting magic, escort strength or enemy anti-air pressure, after checking supported controls. |
| Swarm command | How much does synchronizing the screen and damage units matter beyond a simple coordinated advance? | Contrast staggered and coordinated commitments; vary screen depth or one enemy threat without merely inflating unit count. |
| Cavalry assault | Are the charge/disengagement opportunities reproducible and visible through the interface? | Establish that the successful flank is repeatable before making it harder; examine one coverage or terrain variant only where it preserves a credible route. |
| Defensive swarm | Is there an executable defence that improves on holding position? | Check one focused-fire or fallback hypothesis; redesign only if it creates a distinct, controllable firing-space problem. Equal loss records alone do not settle its value. |
| Kislev survival | Can reinforcement spending become a consequential tradeoff? | Supplies were abundant in the audit; check whether initial resources, income or available purchases can be controlled. If not, describe it as spawn defence or defer it rather than claim budgeting. |

**4. Use cheap tests to eliminate bad designs.** After implementation is authorized,
start with the existing scripted baselines and a narrowly scoped public-state controller
for a particular tactical hypothesis where needed. Such a diagnostic may encode a
strategy; disclose that knowledge and keep it separate from general model results.
Do not build an expert bot or sweep a large parameter grid. Choose at most two families
for the first calibration tranche, with roughly 2-3 purposeful battles total per
candidate variant, reusing existing anchor evidence when conditions are comparable.
Each battle must resolve a named uncertainty; add a repeat only when variability
prevents the next decision. A cheap model is useful for interface/usability checks,
but its losses cannot certify difficulty for a stronger model. Scripted controllers'
faster reactions likewise do not establish feasibility at model latency.

**5. Buy a small frontier screen once cheaper work stops answering the question.**
Offline analysis and scripted probes cannot establish the ceiling of the strongest
models. Select two or three well-supported candidate scenarios, freeze the conditions,
and initially run one battle each with one strong model/configuration, chosen when
the screen is planned. Do not automatically cross every scenario, model and effort.
Specify each run's question, expected cost range, hard spend ceiling and next action
before starting; review its trace before allocating another paid battle. A repeat is
for an ambiguous result, a suspected failure or variability that changes a decision.
One win is not a ceiling estimate and one loss is not evidence of benchmark quality.
Clear easy wins motivate testing a harder variant, useful varied decisions justify
later comparison, and interface failures send the candidate back to repair. These
runs remain development data if they influence scenario or controller design.

**6. Freeze an evaluation collection only after that screen.** Select for distinct
capabilities, executable alternatives, interpretable progress, difficulty headroom
and reasonable runtime/cost. Keep an easier anchor when it provides a useful control;
not every scenario needs to defeat the strongest model. Freeze scenarios, controller
rules, settings, metrics and stopping rules for a comparison round; later revisions
are new versions. Reserve unseen variants before tuning and never use them to select
the design. If held-out evidence prompts redesign, retire it as development evidence
and reserve fresh variants. Allocate matched repeats only to questions that survived
calibration, accounting for variation across launches and correlated rematches.

**Spend and stopping discipline.** No broad unattended paid matrix is the default.
Choose small tranches by how likely a run is to change a design decision, relative to
its expected API cost and wall time. Keep infrastructure failures separate, retain
negative evidence and stop a tranche when its question is answered or its cap reached.
Do not shorten losing battles and report them as engine losses; an interrupted battle
remains incomplete. Use observed duration, calls, token use and retries for estimates;
long losing battles need allowance too. The ledger remains $45.96 of $52 as recorded
after M1, with $6.04 unallocated; this proposal neither spends it nor raises the cap.

**Immediate planning deliverable:** six short calibration cards, followed by a proposed
first tranche for at most two families: the exact hypothesis, one-factor variants,
controller/probe, observable evidence, battle count, runtime/cost allowance and decision
rule. That makes implementation reviewable before any new experiments. OpenRouter now
has a separate [cleanup and integration proposal](controllers.md#openrouter);
added-age studies, broader controller comparisons, report polish and custom evacuation
remain later work unless a specific calibration question needs them.

### Calibration cards, 2026-10-16

These cards use the 54 battles in the saved M1a–d plans, not a new experiment. The
read-only extraction is `runs/twwarhammer3/calibration/calibration-audit-20261016.py`
with its JSON alongside it; each row retains its episode path and source revision.
The [M1 trace review](log.md#2026-10-16-matched-round-m1-on-the-retained-core-plan)
provides the earlier turning-point analysis. Observed associations are hypotheses
about causes; no single tactic is established as necessary or sufficient.

| Candidate | Question and scarce resource | Competing plays | Evidence and remaining uncertainty | Next useful test |
|---|---|---|---|---|
| Siege defence | Can a controller allocate its one mobile reserve while keeping firing positions useful? Time and exposure of the reserve/lord matter more clearly than construction currency. | Defend several approaches with local support; concentrate around a central point and trade outer territory. | Sol and gpt-6.1-sol each won 3/3, Luna 0/3; hold and walk-nearest lost. Earlier review links reserve/lord isolation and weak blunderbuss fire to losses. The newer model won even with only 54 observed blunderbuss rounds in one battle, so that weapon's use is not a demonstrated necessity. | One disclosed, simple central-defence diagnostic on the existing anchor. If it wins comfortably, test whether a specific second threat creates an actual allocation problem before a frontier comparison. |
| Swarm command | Can the screen and expensive damage units arrive together? The scarce resource is protected time for the weapons and mobile units, not raw body count. | Commit screen and damage units together; pin the line while a mobile group flanks. | Sol 2/3, gpt-6.1-sol 3/3, Luna 0/3. Sol's loss reversed its successful commitment order. M1c won once despite its Doomwheel routing at 208 s, so preserving every specialist is not required. A simple synchronized advance may suffice. | One coordinated-advance diagnostic using public positions and speeds, preserving the current roster. If timing materially improves execution, compare one screen-depth variant; do not enlarge both armies. |
| Caster assault | Choose spell windows and preserve the caster/escorts under a deadline. Mana, barrier recovery and escort lifetime are the candidate constraints. | Spend early to break a dense group; preserve magic and withdraw the caster between windows. | Sol and gpt-6.1-sol each 3/3, Luna 1/3; two nearest-enemy scripts lost. Accepted ability orders vary substantially and include non-spells; order counts alone do not measure spell impact. Stale post-cast readiness confounds failed orders. | Correct/read back readiness first. Then test a narrowly specified cast-and-retreat diagnostic before reducing magic or escorts. Starting magic is not a current scenario field, so a mana ladder requires an engine feasibility check. |
| Cavalry assault | Reach vulnerable guns without becoming trapped by halberds. The scarce resource is safe approach/disengagement space and time. | Commit to a flank; bait part of the screen and exploit the opening. | Both stronger tested models won 1/3, Luna 0/3. Earlier wins reached the guns; losses often entered the screen. This is already difficult, with unresolved route repeatability and model-latency sensitivity. | Keep the current difficulty. Review the successful route against the other starting geometries before buying a repeat or changing the roster; do not make an inconsistent manoeuvre test harder yet. |
| Defensive swarm | Can limited firing space be preserved against encirclement? Ammunition and formation exposure are possible constraints. | Hold a compact line with focused targets; trade ground with a controlled fallback. | Both M1 models lost 3/3; earlier hold evidence matched or beat some model runs. No evidence yet that a general controller can execute a materially better defence at its natural latency. | Test one focused-fire or fallback hypothesis only after the first two families. Retain negative evidence; redesign rather than add enemy strength if executable alternatives remain absent. |
| Kislev survival | Keep reinforcement access useful while the initial force is pressured. Budget scarcity is not established. | Purchase relief early; preserve a route and bring a specialist later. | Sol bought all seven initial reserves in each M1 run, surviving 366–413 s with 4,004–5,654 supplies left. Its public spawn-zone list first emptied at 229–240 s, with 1,065–1,602 supplies. Luna's list emptied at 210–232 s. This supports a deployment/access problem, not yet a budgeting benchmark. | Reframe the report as reinforcement defence. Check whether starting supplies/income can be controlled before proposing a resource ladder; those are not current scenario fields. Keep it provisional because it may duplicate siege territory control. |

The audit distinguishes an empty spawn-zone list (no zone available to the alliance)
from `usable: false` (no affordable unit can currently be purchased there) and a missing
`usable` value (not judged because nothing is affordable). Treating all three as lost
territory would invent a failure cause. Ammo differences are observed expenditure,
not hits or damage; evaluation-only final counts never enter diagnostic policies.

**First calibration tranche:** siege and swarm command, one purposeful scripted battle
on each unchanged anchor, $0 API spend, up to 20 battle minutes each plus setup. Build
only the small public-state diagnostic needed for the named question, disclose its
scenario knowledge in its controller card, and record execution alongside the outcome.
Review each trace before a second battle; repeat only for a specific ambiguous mechanism
or changed start. A second run per family is a ceiling, not a quota (at most 80 battle
minutes plus setup for the tranche). A scripted win may identify an easy strategy;
a scripted loss does not establish difficulty for a strong model. No roster variants
or frontier runs are queued before this review. Correct the two observed controller
feedback issues in a separate logged version before the next paid comparison.

## Earlier implementation sequence (2026-10-15)

The completed work and earlier decisions are recorded in the log:
[v17 / commander v4](log.md#2026-10-15-integrate-llm-v17-and-commander-v4),
[b11 shared measures and report](log.md#2026-10-15-harness-b11-common-measures-and-one-report),
[b12 scenario expansion](log.md#2026-10-16-harness-b12-and-distinct-scenario-families),
and [M1](log.md#2026-10-16-matched-round-m1-on-the-retained-core-plan).
The superseded implementation instructions remain in Git history; the active sequence
is the [calibration proposal](#implementation-plan). Measurement definitions are above;
report behavior is in [reports.md](reports.md).

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

These are definitions only; this tranche does not execute self-comparison series or
build a new experiment framework. Compare one model to itself with its exact model id,
effort, controller/prompt version, build, map, settings and non-treatment conditions fixed.
Use matched instances, rotate condition order, reset controller memory each episode and
retain all attempts, including infrastructure/policy failures. Record input/output/cached
tokens, response latency, observation age, cost, actions and objective progress.

| Axis | Change | Interpretation and controls |
|---|---|---|
| Army/control workload | Number of independently commanded units, with declared composition ratios | Also changes action volume, density, pathing, contact timing, combat balance and tokens. This is end-to-end scaling, not a pure context-length effect |
| Prompt-only neutral context | Additional non-tactical text, same battle/state/action space | Vary token count while holding facts and history fixed; record where text is inserted. Check that the text does not introduce advice or alter the task |
| Useful history | Relevant prior observations/actions at prescribed lengths | Tests memory value and interference; it changes information as well as length. Keep the history-selection rule fixed |
| Factual representation | Equivalent facts rendered compactly or verbosely | Test representation separately from adding new information; audit factual equivalence |
| Added observation age | Buffered observations at declared minimum ages | Already supported; distinct from slower generation or a longer prompt. Natural model latency remains measured, not an experimentally assigned dose |

Larger armies and longer prompts may be crossed later to separate their effects. First
screen feasibility and freeze the treatments; use objective measures appropriate to the
family, and do not infer reasoning limits solely from slower real-time play.

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
