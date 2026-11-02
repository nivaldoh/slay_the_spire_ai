# Evaluating tactics in WH3

Companion to the [tactics catalogue](tactics-reference.md). These are proposed study designs,
not implemented scenarios or agreed checks. They preserve the [benchmark definition](benchmark.md):
fixed armies and deployment, engine outcomes, public policy inputs and unpaused 1x play.
The owner's [2026-11-01 plan directions](benchmark-implementation.md#owner-directions-2026-11-01)
tentatively favour health as the main score, reduced by low morale and more strongly by
routing, with failed attempts counted separately as errors rather than partially scored.
Formulas, denominators and the relationship to victory remain open. Start the evaluation
method from a related benchmark and refine it later; no reference has yet been selected.
Battle-condition research and the owner's comparison choices are deferred. No implementation
is requested by this plan update.

## Three questions with different evidence

| Question | Evidence that could answer it | What it does not establish |
|---|---|---|
| Did the controller perform the manoeuvre? | Checked sequence of positions, contacts, casts or objective transitions | That the manoeuvre helped or was the only good solution |
| Did that decision help in this situation? | Comparison with a controlled alternative, repeated under declared conditions | That it helps on other maps, rosters or opponents |
| Is the controller effective in whole battles? | Outcomes and army condition across the declared suite, including failures | Which manoeuvre caused a win or whether the model understood its name |

A controller may win without any catalogue manoeuvre, or execute one correctly and lose.
Keep both findings. A written explanation of hammer and anvil tests knowledge in language;
a battle tests action selection and execution under delay. If both are studied, separate
their results and avoid supplying the tactic's answer in the battle prompt.

## Lessons from the benchmark references

The existing [reference index](benchmark-references.md) supplies the design foundation.
Its proposals remain proposals here; this page rests on JUDGEMENT
`docs/twwarhammer3/benchmark-references.md` Transfer proposals.

| Reference | Concrete use in a tactics study | Transfer limit |
|---|---|---|
| [BEHAVIOR](benchmark-references/behavior.md) | Describe goals independently of a preferred solution; separate a situation's specification from its realised initial state. “Preserve the guns and win” allows several tactics | Goal predicates need WH3-specific measurement; preservation is an additional diagnostic unless adopted as a task objective |
| [CARLA](benchmark-references/carla.md) | Specify a trigger, such as an attacker approaching the rear line, and record subsequent events. Examine incentives before combining diagnostics into a score | Routing, friendly losses and time cannot inherit driving penalties or CARLA's aggregation formula |
| [SMACv2](benchmark-references/smacv2.md) | Vary roster roles and starts within constrained families; compare feedback-driven play with fixed timed plans | WH3 uses persistent unit orders and real inference delay, not synchronised simulator steps |

For implementation after approval, consult the pinned files in those profiles:
BEHAVIOR task predicates and sampling, CARLA ScenarioRunner criteria and Leaderboard
statistics, and SMACv2 `distributions.py` and `wrapper.py`. Their published results and
sample counts do not set our WH3 design.

## What the harness can observe and command

Source inspection, 2026-11-01: [mailbox contract](../../src/twwarhammer3/engine/mailbox.py),
[order validation](../../src/twwarhammer3/protocol.py),
[Lua recorder and executor](../../src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua),
and [measurement gaps](benchmark-implementation.md#measurement-gaps).
Interface support is not live verification of a tactic or measurement.

| Available interface | Candidate use | Missing evidence or restriction |
|---|---|---|
| Unit positions, bearing, HP fraction, entities and state flags; friendly ordered width | Approach, engagement, retreat and target survival | Unit centres are not contact edges; ordered width is not achieved shape. Actual per-entity attack direction, collision and charge bonus are not recorded |
| Friendly ammunition, fatigue, abilities, targets and destinations | Resource use and action sequence | Enemy ammunition/fatigue and target orders are not equivalent public fields; net changes do not assign damage |
| Friendly UI leadership fraction and largest effect | Friendly recovery and pressure | Not full modifiers or enemy leadership; fraction can exceed normal bounds and is not a cross-unit morale scale |
| Visible enemy records and public lobby roster | Responding to threats and retaining last-seen knowledge | Disappearance is not death; hiding-filter equivalence to the player's view is unverified |
| Coarse clear/blocked terrain grid | Avoiding obviously blocked movement | No height, trees, water labels, full path graph or projectile line of sight; a clear cell does not guarantee a shot |
| `move` with facing/width/run, queued movement/attack, `halt` | Formation, route, reserve and withdrawal attempts | No policy deployment; engine routes and entity movement remain automatic |
| `attack` with auto/melee/ranged modes; behaviour toggles | Target selection, skirmish, fire-at-will and formation spacing | No explicit gate/wall target, per-entity control or checked bracing flag; an issued order may never produce contact |
| Unit/army `ability` and `flight` | Spell timing, summons, air attacks | Loadout and readiness dependent; no generic overcast control. Do not assume a specific spell variant is exposed |
| Public mode points, tickets, gates, supplies, slots, pools and zones | Objective decisions, `build` and `reinforce` | Fields are mode dependent; no generic capture/unsummon/repair/ammunition-purchase/upgrade order |
| Private evaluation totals, final state, orders and acknowledgements | Outcome and summary diagnostics | Not complete private per-unit HP/leadership histories. Acknowledgements show issue/queue acceptance, not effects |

`evaluation`, `final`, `setup` and `native` are excluded from policy observations by
`protocol.HIDDEN_KEYS`. Replays, stills and evaluator-only measurements may support offline
review but cannot enter prompts, memories or action selection. A new measurement exposed
to the policy changes the information contract and needs a declared track.

Treat missing or failed getters as unknown. The current recorder can fall back to HP zero
or a false state flag, so neither alone proves death or absence of an effect. It also
publishes `unstable`, `crumbling` and `rampaging` flags; interpreting them as cause, severity
or remaining control requires engine checks, not just their presence in a schema.

For terrain-dependent tasks, distinguish three studies: familiar fixed-map play using
permitted prior knowledge; a future track with public terrain semantics; and adaptation
from observed movement/shooting failures with the current grid. They measure different
things. A reserved-map test cannot quietly give the policy a manually annotated height
map while claiming the current observation track. Record any map guide supplied to it.

## Candidate experiment cards

JUDGEMENT: Tactical comparisons — Codex, 2026-11-01: proposes the cards below as design examples.
Different contrasts test different decisions; causal interpretations rest on the chosen foil.
No card, roster, detector threshold or run count is adopted.

These cards rest on JUDGEMENT `docs/twwarhammer3/tactics-reference.md` Tactic catalogue.
They are a menu, not an experiment queue. Each requires fixed unit keys/loadouts, actual
placements, mode settings and a measurement check before it becomes executable.

| Card and hypothesis | Setup and comparison | Evidence and negative case |
|---|---|---|
| **E1 Coordinated flank** — H1 | Infantry hold a target with cavalry on a legal open wing. Compare a contact-triggered flank, a timed flank, a frontal cavalry attack and no cavalry order | Check approach and overlapping engagement, then infantry/cavalry condition and engine outcome. Add a counter-flank reserve; coordination should respond to it |
| **E2 Guns under pressure** — T1/T2/H5 | Empire direct-fire units, infantry and a reserve face separated melee/mobile threats. Compare a reactive screen and lane adjustment with a static line and nearest-enemy pursuit | Protected guns must both survive and contribute. Add a second arrival direction; a reserve must choose. Visibility and shot evidence are measurement prerequisites |
| **E3 Mobile fire** — T6/T8 | Faster missile units against slower melee on an open map with declared timer role. Compare manual kite/crossfire with no orders under identical skirmish/fire settings and a fixed movement loop | Ammo and contact histories, map-edge collisions, outcome. Add faster pursuers or a capture objective. Do not relabel a permitted timer win as a loss |
| **E4 Reserve allocation** — H5/H6 | A line with a reserve faces a threat on one of several legal approaches. Compare reactive commitment, fixed timing/direction and immediate commitment | Arrival before/after breach, protected-unit loss and final condition. The adversary may decline the attack. Vary threat location in setup without revealing hidden positions |
| **E5 Magic combination** — W1/W2 | Same caster/loadout, holding unit and damage source. Compare contact-triggered cast, early cast and cast withheld while other orders remain controlled | Resource and ability transitions plus downstream unit condition. Add dispersed targets or a target that escapes. Do not claim spell damage from a coincident HP drop |
| **E6 Rotation and recovery** — W3 | Two suitable barrier/healing-supported units and an enemy capable of sustained pressure. Compare alternating coverage with continuous engagement | HP, barrier, entities, time absent and objective costs. Add pursuit or anti-healing pressure where supported. A no-damage recovery probe first checks the readout |
| **E7 Objective rotation** — O4 | Declared Conquest or Domination map and roster/pool. Compare enemy-seeking, fixed point allocation and reactive capture defence | Holder/ticket history, arrival, supplies and engine outcome. Add a distraction or alternate entry. Run each mode separately; the purchase mechanism is not common to both |
| **E8 Restricted-map coordination** — O1/O2/O3/O5/O6 | Choose one mode: crossing, siege, survival or ambush. Compare staged movement/defence with immediate commitment under its actual objective | Check reachable routes and objective transitions. Remove an assumed alternative route or change threat timing. Siege entry commands and survival services may require bridge work first |

For a controlled script comparison, change one decision rule and keep observation access,
order cadence, automation settings and other behaviour fixed. The resulting difference
estimates the value of that rule in those conditions, including the opponent's reaction.
Removing cavalry or replacing a lord changes the army as well as the tactic: useful for
robustness, not an isolated intervention on the decision rule.

Comparing whole model controllers cannot hold their other choices fixed. Report their
complete battle performance and observed behaviours; do not assign the outcome difference
to one named tactic. A saved replay's different-looking manoeuvres are not a counterfactual.

## Candidate diagnostics and how to check them

JUDGEMENT: Tactic diagnostics — Codex, 2026-11-01: proposes event diagnostics below, separate
from ranking. Outcome-only reporting is an alternative; any execution claim rests on a checked
detector and its declared thresholds, which remain undecided.

| Diagnostic | Operational proposal | Independent check and a plausible wrong positive |
|---|---|---|
| Flank contact | Target-relative approach followed by overlapping engagement of holder and flanker | Compare live engine/UI/replay evidence with annotated contacts. A unit behind the target but not fighting must not pass; target turning during approach must be handled |
| Cycle charge | Contact, genuine separation, then renewed approach/contact against a recorded target | Inspect trapped entities and a failed withdrawal. Repeated attack acknowledgements without separation must not count as repeated charges |
| Screening | Threat engages the screen while the protected unit remains able to act | Compare with a bypass and a protected gun that survives but never fires. Mere proximity must not pass |
| Ranged contribution | Ammo use and visible firing evidence during declared target windows | Empty ammo, obstruction and firing at the wrong target are negative cases. Ammo depletion alone proves neither hits nor useful damage |
| Spell use | Accepted cast followed by applicable resource/ability and effect evidence | A cast refused, queued too late, interrupted or aimed at an empty area must not receive effect credit |
| Recovery | HP/barrier/entities change during a known interval, each recorded separately | Compare a controlled no-damage recovery with UI values. Barrier restoration must not count as healed HP; net HP hides simultaneous damage/healing |
| Rout and return | Routing state followed by recovery and renewed participation | Check against shattered, leaving, dead and invisible cases. Loss of visibility must not imply death or rally |
| Capture and purchase | Engine holder/ticket changes; a purchase's unit or structure actually appears | A contested point, a flyer overhead, a locked point, an accepted but uncompleted build and a refused purchase must not pass |

Version the definition and save timestamps, unit identities, data provenance and missing
values for every event. Detector windows, geometric tolerances and minimum durations need
calibration against engine evidence; do not choose thresholds because a favourite policy
passes. Check annotated positives and plausible negatives, then measure agreement on
different cases. An LLM reviewer can flag ambiguous episodes but is not the sole oracle.

Do not invent a scalar “tactical intelligence” score from these diagnostics. A composite
could reward repeated cheap contacts, sacrificial summons, needless casting or avoiding
combat. Keep engine outcomes and per-unit health, entities, leadership and objective
histories available while score choices remain open. Different initial health and unit
costs need explicit denominators; summing HP fractions treats a lord like a disposable unit.

## Variation and repeated battles

JUDGEMENT: Tactic study structure — Codex, 2026-11-01: proposes the variation and baseline
procedure below. A single fixed encounter is cheaper but narrower; generalisation and causal
claims depend on the selected families and sampling unit. The owner sets the actual plan.

1. **Specify one question and its population.** Name roles, maps, rosters, AI settings,
   time limit, unit size, rank, magic/equipment, behaviour toggles and allowed knowledge.
   Check funds and DLC content. Keep a realised start record as well as a random seed.
2. **Establish that the decision is reachable and measurable.** Check movement, targeting,
   ability/resource and objective effects against the game. Include an expected failure
   case. A script/human demonstration establishes possibility in that case, not a rate.
3. **Compare useful alternatives.** Include no orders with default engine behaviour,
   existing nearest-enemy baselines, a fixed timed plan, and a disclosed reactive script
   where relevant. Label each controller's helpers and information. A strong baseline is
   evidence, not a reason to discard a scenario.
4. **Vary conditions that can invalidate the tactic.** Range, initial separation, frontage,
   threat side, route length, terrain, leadership vulnerability, available ammunition,
   support availability and objective urgency are candidates. Avoid impossible starts or
   variants that accidentally change multiple mechanisms when isolating one decision.
5. **Reserve generalisation cases before tuning.** Repetition on the same map measures
   consistency. New placements on that map, a new map, a different faction and a different
   mode are distinct claims. Disclose prior exposure and keep test variants out of prompts,
   graph authoring, between-battle revision and skill tuning.
6. **Predeclare attempts and analysis.** Choose effect size, repeat count, stopping/replacement
   rules, uncertainty method and budget before scored play. Interleave controllers to
   reduce order/time effects. Report every failure and unplayed attempt with its reason;
   avoid analysing only completed pairs. No sample number is selected here.
7. **Audit the result against what happened.** Separate execution failures from strategic
   choices and setup/measurement failures. Retain negative results and shortcuts. Report
   uncertainty at the scenario/launch level appropriate to sampling, not over thousands
   of correlated observations as if each were an independent battle.

Identical seeds or starting screenshots do not establish identical engine randomness.
Rematches share a launch; do not treat them as independent fresh battles. Restored starts
can help compare nearby decisions only within the [checkpoint check's coverage](checkpoints.md#limits).
Exact equality beyond that coverage needs its own repeatable check; new modes, spells,
summons and resources must not inherit a Land restore claim automatically.

## Timing and team coordination

All tests run unpaused at 1x, including diagnostics. A fixed timed plan still acts in the
live game; it does not pause the engine between steps. Natural controller delay is part
of performance. Added observation age, order cadence, executor skill and model reasoning
effort are separate factors; changing several cannot isolate “reasoning speed”.

Use engine battle time for tactical durations and retain observation basis, application
time and effect time where measurable. An acknowledgement time is not a contact time.
Record Windows-clock speed evidence and the known [WSL clock limits](integration.md#clocks-measured-2026-10-28).
Different controllers' observation traces may have different temporal coverage; a detector
must report gaps, and independently sampled evaluation histories require recorder work.

Team variants can divide holder/flanker, screen/shooter, or sector/reserve roles, then
test reassignment when a unit is lost or a route is blocked. Compare with a single
controller under the same army, information, abilities and disclosed execution helpers.
Report communication and scheduling delay as well as decisions. Single-client split
control and native multiplayer are different implementations; current native multiplayer
does not provide the full combat action set, so it is not ready for these tactical tests.

## From research to an approved experiment

The existing [owner interview](benchmark-implementation.md#owner-interview-one-land-battle)
remains the decision location. This reference helps select a family, its goal, allowed
information, comparison and evidence; it does not bypass decisions about scoring, checks,
sample count, runtime or spending. After selection, turn one candidate into a concrete
experiment card and agree its repeatable correctness check before calling it verified.
