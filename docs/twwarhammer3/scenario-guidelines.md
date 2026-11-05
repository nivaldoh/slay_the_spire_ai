# Guidelines for WH3 evaluation scenarios

Owner request, 2026-11-04: diverse scenarios whose winnability and intended measurement
can be checked, including game mechanics, engine quirks and multi-agent control.
**Owner stopped the timing investigation on 2026-11-05; no further scenario run is scheduled.**
The [wrap-up](support-timing.md#stopped-comparison-and-next-steps) retains the implementation,
seven completed comparison battles, one owner interruption and ten unstarted attempts.
The earlier timing question remains stopped.
The owner selected a [Cannae comparison](cannae-comparison.md): separate familiar-tactic,
adaptation and [limited-communication team battles](cannae-communication.md). Their construction,
deciding checks and place in the development sequence remain proposed; no battle is scheduled.
The [benchmark definition](benchmark.md) still governs automated controllers: fixed armies
and deployment, public structured observations, permitted orders, engine wins including
timer wins, and unpaused 1x play. The owner alone may pause a manual winnability demonstration.
That demonstration is separate evidence, not a paused model benchmark. No agreed check,
scorer or historical result changes here; [verification](../../AGENTS.md#verification-hard-rule)
still needs a concrete agreed procedure and a recorded pass.

## Current plan and owner decisions

Owner, 2026-11-04, replying to the nine choices. These directions govern the initial work;
earlier marked proposals below remain only where not superseded. Tentative answers are
not blanket approval of the earlier procedures.

| Choice | Current direction | What remains open |
|---|---|---|
| 1 Entry and growth | Add scenarios one by one; add the next when the previous seems complete, reliable, trustworthy and validated | Concrete readiness checks and total eventual set |
| 2 Initial scope | Start with two scenarios, one simpler and one more complex, developed sequentially | Actual maps, armies, tactics and what creates the added complexity |
| 3 Winnability | Tentatively use the owner's manual win; only the owner may pause to make that play easier | Recording method, repeatability and what additional evidence is needed for the automated interface |
| 4 Intended measurement | Work out the method together; research an LLM/VLM judge for tactic detection | Which tactic/event, rubric, evidence, judge model and acceptance criteria; no judge adopted |
| 5 Opponent | Some scripting is possible if easy; not a priority for the initial scenarios | Need, feasibility and scope of any later scripting |
| 6 Comparison | Unit health and morale, with cost, latency and other relevant metrics; refine as work progresses | Formulas, weights, resources, timing and method comparisons; no equal-budget or whole-system design newly approved |
| 7 Reserved scenarios | Undecided | Selection, development/evaluation boundary and reserved variants |
| 8 Ranking | Try one overall ranking | Formula, scenario weights, failures, uncertainty and whether cost/latency affect rank or appear beside it |
| 9 Rechecks | Expect to recheck after changes such as game updates | Trigger scope and concrete rerun procedure |

## First two scenarios

The first candidate, [infantry support and cavalry timing](support-timing.md), was implemented
and partly tested. The owner stopped it because timing is not interesting for now. It has
no passing readiness revision. Revisit the intended coordination capability before another
candidate; the sequential-development guidance below does not schedule a replacement.

1. Plan the simpler scenario first: a small, inspectable decision problem with a clear
   engine objective and few interacting mechanics. Select its concrete setup with the owner;
   no existing mirror or suite entry is selected automatically by this update.
2. For that one scenario, settle setup checks, the owner's demonstration record, the first
   measurement question and its validation procedure. Resolve observed setup/measurement
   problems before treating the scenario as ready. Keep a short evidence summary and open
   issues; “complete” needs an agreed meaning for this scenario, not a universal gate count.
3. Once the first is judged ready under those checks, add the more complex scenario. Choose
   the added difficulty deliberately, such as dependent jobs or concurrent threats, rather
   than assuming extra units alone prove greater reasoning demand. Its actual design is open.
4. The owner subsequently requested a third Cannae design for limited-communication teams
   (2026-11-05). Its construction order remains open; keep the sequential-development
   principle. The coverage matrix does not commit to building further scenarios.

These are planning steps. They schedule no human session, game launch, paid judge call or
policy run. The manual recording path is implemented but its handover remains unverified; do not
disable `require_realtime` or change a live controller to obtain the owner's demonstration.

A useful scenario has a consequential decision, a legal winning witness and evidence
that supports its stated interpretation. Difficulty, visual variety and a plausible story
alone establish none of these. A scenario can run correctly and yield a real victory while
failing to exercise its advertised skill. In the [first suite review](log.md#2026-11-04-suite-page-rebuilt-around-who-coordinates-with-whom),
the pincer enemy split, the intended waves arrived together, and a relief victory did not
require the column to reach the garrison's fight.

Read [coverage](#coverage-across-dimensions) to choose situations, the
[scenario specification](#the-scenario-specification) to make one concrete, and
[acceptance](#acceptance-and-maintenance) before proposing evaluation. The
[review choices](#choices-for-owner-review) collect decisions without duplicating their values.

## Claims and eligibility

JUDGEMENT: Core eligibility — Codex, 2026-11-04: proposes a validated core and an exploratory
candidate pool. Keeping unwitnessed battles in the core is an alternative; release eligibility
below depends on per-scenario winning evidence and support for the advertised measurement.

The earlier core/pool proposal rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md`
Core eligibility. For now the owner selected gradual completion of individual scenarios,
not a batch admission exercise. The exact readiness procedure remains open. Current
`suite-v1` and all its failed or unwitnessed attempts retain their historical status.

| Claim | Required evidence | Insufficient substitute |
|---|---|---|
| Constructed correctly | Declared setup compared with independent lobby/engine readings; required actions reach their effects | JSON accepted, a command acknowledged, or a green offline suite |
| Human-demonstrated winnability | Owner wins the exact battle manually; record setup, controls, pause use and engine ending | A claim that this also proves the automated observation/action interface or its response timing is sufficient |
| Winnable under this interface | A valid complete win by a disclosed controller using the same public information, actions and timing contract | Equal army cost, an omniscient script, a paused demonstration or a win on another version |
| Reliably reproducible witness | Fresh confirmation attempts under a frozen plan, with counts and uncertainty for the declared conditions | Rerunning until a win or reusing the tuned success as confirmation |
| Exercises a named decision | The opportunity occurs and a controlled comparison supports that decision's relevance | The scenario name, a good-looking manoeuvre or correlation with winning |
| Generalizes | Frozen controller evaluated on declared reserved variants or families | More launches of a familiar battle |

A checked win establishes possibility under that player's conditions, not success on every
future engine trajectory. Keep each initial scenario's demonstration attached to its exact
configuration. No finite empirical check proves universal winnability of a random generator. A generator
needs its own validity evidence and sampling-failure report; sampled wins do not certify
all possible outputs. Neither label means a compared LLM will win.

Keep the goal separate from the scientific hypothesis. The goal remains an engine win;
"support timing matters here" is a hypothesis. Any legal winning tactic counts. If a
controller bypasses the intended problem, retain its win and revise the interpretation,
or publish a new scenario version. Do not introduce a hidden survival, contact, tactic or
speed requirement after seeing results. A different task objective needs owner agreement,
a public instruction and a checked scorer.

## Coverage across dimensions

JUDGEMENT: Coverage design — Codex, 2026-11-04: proposes a matrix of decision families and
independent context dimensions, mostly focused cases with some combined battles and easier
anchors. A hardest-only or faction-balanced suite differs; coverage claims rest on this design.

For the first two scenarios, record their selected dimensions and differences. A larger
coverage row/family summary is a later option. The matrix below
rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Coverage design. It is a design
space, not a demand to run its full Cartesian product. Select cases for distinct decisions
and important interactions; state omissions. The detailed selection/reservation policy is
still undecided under the owner's reply 7; do not treat this matrix as its adoption.

| Dimension | Useful variation | What must be distinguished |
|---|---|---|
| Decision complexity | One consequential choice; several dependent choices; concurrent fronts; a combined battle | Unit count, number of useful choices, dependency depth and simultaneous demands are separate |
| Army scale and heterogeneity | Few regiments through larger armies; homogeneous and mixed roles; asymmetric strengths | More units also change balance, pathing and order volume; this does not isolate context length |
| Duration and horizon | Brief encounter; sustained engagement; several phases; long resource pressure | Time to contact, decision window, action travel time, observed ending time and engine timer |
| Map geometry | Open ground, obstacles, narrow passages, separated approaches, constrained settlement routes | A new map name adds coverage only if its usable geometry changes the decision |
| Terrain and visibility | Firing obstruction, elevation, concealment, restricted sight, uncertain enemy locations | What the engine simulates versus what this observation track actually reveals |
| Mode and role | Land attack/defence; siege attack/defence; ambush, survival and conquest | Victory rules, timer incentives, points, waves and purchase actions differ by mode |
| Tactical opportunity | Target priority, screen and fire, flank, concentration, reserve, withdrawal, recovery, objective rotation | A likely tactic is a hypothesis; several solutions can be valid |
| Resources and capabilities | Ammo, magic, cooldowns, supplies, fatigue, mobility, range, barriers, healing | Scarcity must create a feasible tradeoff; nominal unit class does not prove a capability |
| Information demand | Fully visible choice; discoverable threat; last-seen state; uncertain intent | Relevant hidden information needs a legal way to learn or hedge against it |
| Disturbance and recovery | Threat changes, route failure, rout/rally, permanent loss, reinforcement arrival | Temporary inability, destruction, missing data and a scripted intervention are different |
| Team dependency | Independent jobs, sequential enabling, continuing support, shared resource, reassignment | Multiple agents or simultaneous fights alone do not establish useful interdependence |
| Difficulty and timing pressure | Easier reference case through challenging witnessed variants; broad and tight response windows | Combat disadvantage, planning demand and control bandwidth can fail for different reasons |

For duration, initially record continuous battle seconds and the actual decision windows;
choose any short/medium/long boundaries before selection and mark them as judgement calls.
A long timer is not a long planning task. Setup time affects study cost but is not battle
horizon. If a claimed reaction window closes before permitted information and commands
can reach it, that reaction is infeasible under the contract; anticipation may still win.

Pair some opportunities with situations where habitual use is costly: an exposed gun
versus a protected gun, committing a reserve early versus keeping it available, concentrated
versus dispersed spell targets. These are hypotheses to validate, not universal tactical
laws. The [tactics catalogue](tactics-reference.md) and
[candidate comparisons](tactics-evaluation.md#candidate-experiment-cards) supply ideas.
Faction, roster or role swaps can change several mechanisms; label them transfer cases
unless a controlled comparison justifies a narrower interpretation.

Prioritize the intended modes in [benchmark scope](benchmark.md#scope). Other modes remain
candidates for owner selection. Mark unsupported information, actions, content and
measurements as prerequisites, not losses. Diversity cannot justify a broken scenario.

## The scenario specification

Owner clarification, 2026-11-05: general local evals may consider any faction and lords.
The Boris-only content restrictions and no-lord fixtures concern multiplayer battles on
the VM, not all WH3 benchmarks or single-client model teams. Choose factions and characters
for the intended decision, then check the exact setup on the executing installation.

Keep one short specification beside the scenario's documentation, with links to its
resolved JSON and evidence. Reuse the manifest and existing reports; no new runtime schema
or parallel reporting framework is required by this proposal. Split `development` versus
`held_out`, validation status and experiment stage are separate facts.

| Field | What an author must supply |
|---|---|
| Question and coverage | Primary decision family, context dimensions, intended use and claims explicitly excluded |
| Public task | Mode, role, engine goal, timer rules, permitted observations/orders, prior knowledge and supplied advice |
| Concrete setup | Map/build/content, explicit rosters, rank, loadouts, mounts, resources, AI settings, toggles and deployment; resolve inheritance |
| Decision opportunity | Observable cue, useful alternatives, dependencies, travel/effect time, opportunity window and expected consequence |
| Mechanic reference | Relevant engine contract or checked mechanic, research/design source and limits; historical tactics alone are not WH3 evidence |
| Winnability evidence | Initially the owner's proposed manual demonstration: setup, controls/information, pauses and engine ending; distinguish human evidence from automated-interface feasibility and repeatability |
| Controls and predictions | Simplest shortcut, fixed plan, reactive alternative or executor-only comparison; what result would weaken the claim |
| Measurements | Outcome, setup validity, opportunity and action-effect events; data source, missingness, detector definition and negative cases |
| Variation and exposure | Exact instances and authoring/tuning exposure; ranges, constraints, reserved split and rejection history when those are chosen, without assuming a reservation policy |
| Validation plan | Attempts, unit of repetition, stop/failure rules, pass criteria, uncertainty, budget and named agreed checks still needed |
| Release record | Source/configuration/pack/controller/scorer identities, evidence paths, current status and conditions requiring recheck |

For each decision write: **When cue C becomes available, choices A and B are feasible;
under condition X they should differ in consequence Y; under variant Z that prediction
may reverse or disappear.** This is a falsifiable design statement, not an instruction
requiring the evaluated controller to choose A.

## Winnability evidence

Owner, 2026-11-04: “Probably a human win by me, manually, with me (and only me) being able
to pause a battle to make it easier for me.” This is the tentative starting route for the
initial scenarios. Only the owner may use that pause exception; automated policies and
agent-operated probes stay unpaused at 1x. A manual human session is not scheduled here.

For the proposed demonstration record, retain the exact setup/version, identity of the
player, normal manual controls/information used, whether pauses occurred, and the engine
ending. Where available, save pause intervals and action/effect evidence; the recording
procedure is still to be designed and agreed. Keep failed attempts and setup problems.
A complete human win establishes human-demonstrated winnability of that configuration.
It does not measure a model's latency, establish that the structured interface exposes
every needed action, or demonstrate repeatability from one success.

Record the human and automated conditions separately. If the demonstration relies on a
view or action the policy lacks, resolve that interface issue before interpreting model
failure as tactical weakness. Do not pool paused-human performance into a live-controller
ranking. A model or script win at 1x could later provide additional interface/timing evidence;
it is not imposed as a prerequisite for beginning the initial human-demonstration route.
The repeat count and sufficient readiness evidence remain to be agreed for each scenario.

### Earlier stronger witness proposal

JUDGEMENT: Witness contract — Codex, 2026-11-04: proposes a public-interface witness for each
concrete core configuration, an independent fresh reproduction and a frozen reliability plan.
One unrestricted human win would be cheaper; eligibility and repeatability claims rest on this.

This earlier proposal remains parked under the owner's tentative human-win route. It is
not the mandatory admission gate for the first two scenarios. If selected later, it rests
on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Witness contract: the witness uses
only public inputs and permitted orders at 1x; a separate checker reproduces it; a frozen
plan declares attempts, success threshold, uncertainty and stopping/failure rules. Private
coordinates or event schedules must not enter its code or preparation. More repeated wins
would support reliability under the stated conditions, not a universal guarantee.

## Establish that the intended decision matters

JUDGEMENT: Measurement eligibility — Codex, 2026-11-04: proposes checked opportunities,
effect evidence and controlled alternatives before giving a core scenario a capability label.
Outcome-only labels are an alternative; specific skill claims rest on this stronger evidence.

Owner reply 4 leaves the method open and requests research on LLM judges. The
[tactic-judge research and proposal](tactic-judges.md) considers structured evidence and
visual sequences; no judge or detector is selected. The checks below remain candidate
methods, resting on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Measurement eligibility.
Separate three questions: did a decision opportunity exist, did the controller do something,
and did that choice help? None implies the next. A whole-system win supports an outcome
claim; it does not identify the model's internal reasoning or prove a tactic was necessary.

- **Observe the opportunity.** Define when its cue is publicly available, what options
  remain possible and what changes if it is ignored. Use independently sampled engine
  evidence where needed, not only snapshots taken when a model happens to answer.
- **Challenge the claimed mechanism.** Compare a competent reference with a working control
  lacking the proposed response. Hold other rules, information and executor timing fixed
  where possible. State the minimum meaningful difference and uncertainty rule before runs.
  A baseline that never attacks because no target is visible has not tested a bad attack.
- **Vary relevant conditions.** Change threat side, approach time, available support or target
  arrangement within a checked feasible range. Predict what should change. This tests the
  claim beyond one convenient layout. Several simultaneous changes support a broader claim.
- **Vary irrelevant presentation separately.** Consistent unit-ID renaming and list ordering
  should preserve equivalent decisions, allowing stochastic variation. Remap every reference.
  Physical mirroring is not automatically equivalent: terrain, light, deployments and AI
  reactions may be asymmetric. Such transformations need their own equivalence check.
- **Validate the detector independently.** Compare events with native/engine witnesses and
  carefully labelled recordings. Include true, false and ambiguous cases on different records
  from those used to choose thresholds. Plant swapped identities, missing observations or
  accepted-but-unexecuted commands. Preserve unknowns rather than converting them to failure
  or success. Human/LLM interpretations cannot be the sole oracle for an objective event.

A tactical event may depend on what the controller does. An advance that prevents an enemy
wave from forming is valid play, not an excuse to exclude that winning trial. Freeze which
failures mean a malformed setup, which observations challenge the scientific interpretation,
and which are controller consequences. Keep the latter in the comparison. Do not filter
results afterwards to battles where the desired story happened.

| Candidate | Expected opportunity and comparison | Evidence that would weaken its label |
|---|---|---|
| Relief | Garrison has a real threat; column has a usable route and time to help. Compare timely support, a fixed departure and withheld support | Garrison wins unaided, column cannot arrive, or the winning plan never needs that engagement |
| Pincer | Both groups can affect a common fight; compare joint and staggered commitment at matched execution settings | Native AI divides into independent battles; convergence never matters |
| Sequential threats | A meaningful interval permits dealing with the first threat before the second. Compare priority and commitment rules | Waves arrive together, or the first can be ignored without consequence |
| Rear protection | Threat can reach useful guns; compare reserve response with an otherwise identical fixed plan | Guns survive but never contribute; nearest-enemy pursuit already supplies equivalent protection |
| Recovery | A visible loss of support leaves a feasible alternative assignment. Compare reactive reassignment with the frozen original plan | Intervention removes all winning continuations, or recovery is inferred from mere proximity |

These are examples of specifications to validate, not claims that the current named suite
scenarios satisfy them. A simple successful alternative should narrow a claim, not trigger
an automatic increase in enemy strength. Keep easier anchors that reveal interface or
execution failures. The historical rule that every naive baseline must lose is not restored.

## Game mechanics and engine checks

Use the [integration notes](integration.md), [mode contract](battle-types.md) and
[current observation limits](tactics-evaluation.md#what-the-harness-can-observe-and-command)
to identify checks. The rows below are requirements for relevant scenarios, not declarations
that those checks are implemented or already passed.

| Mechanic or quirk | Scenario requirement |
|---|---|
| Lobby persistence and content | Set and read back map, role, mode, difficulty, stats modifier, scale, timer and funds. Confirm recruitable unit keys, mounts, rank and loadout on the executing installation; a visible DLC card is insufficient |
| Identity and authored starts | Match types and identities through recruitment, placement and observation; engine IDs need not follow roster order. Check both armies privately, including hidden enemies. Check facing/usable formation when material; the current placement check tests x/z and only records bearing and ordered width, not all geometry |
| Native AI after placement | Confirm attack/defence incentives and actual behavior. Teleporting a block does not make it hold together; distance does not schedule a wave. Preserve engine timer wins even when they bypass a tactic |
| Movement and terrain | Check required paths with the relevant units, widths and speeds. Coarse clear cells do not prove reachability or projectile line of sight; narrow passages, map edges and obstacles can invalidate assumed routes |
| Positions and engagement | A reported unit centre can jump between separated squads. Nearby centres do not prove contact, flanking, blocking, bracing or support; ordered width does not prove achieved formation |
| Engine automation | Record fire-at-will, skirmish, guard, attack mode and persistent queues. No new orders can still mean useful fighting or movement. Test what automation supplies before crediting a planner |
| Orders and effects | Trace public cue → decision → acknowledgement → movement/contact/cast effect. An accepted or queued command can fail to achieve its purpose; queue submission time is not each action's start time |
| Visibility and stale targets | Exclude private setup/evaluation and recorder data from policy inputs. Disappearance is not death. Target loss can end an attack; check retargeting opportunities and make information demand feasible |
| Morale and survival | Distinguish wavering, routing, rallying, shattered, departed, dead, crumbling and loss of control where exposed. Lordless command assignment and army-loss cascades can dominate a supposedly geometric task |
| Damage and resources | Separate HP, entities, barriers, regeneration, ammo and fatigue. Ammo spent does not prove hits; net HP does not attribute damage. Different unit costs/counts do not establish equal combat strength |
| Magic and abilities | Pin spells/equipment and check readiness, resources, targets, interruption and actual effect. Permission to cast is not readiness; resource changes can lag acknowledgement and shared pools can race |
| Flyers and unusual units | Check supported flight transitions, ground-force requirements and actual capabilities. Class labels alone are insufficient for targets, ownership partitions or tactic assumptions |
| Mode objectives | Read holders, tickets, supplies, slots and reinforcement pools as appropriate. Check capture/build/spawn effects, identity after return and shared spending. Siege wall/gate and survival service requirements must fit the actual order API |
| Ending and missing reads | Use the engine ending and declared observation point. Keep timeout cause ambiguous when appropriate; wall caps and provider failures are not invented engine losses. Missing getters or default values must not silently establish a tactical fact |
| Clocks and resets | Use engine time for tactical windows and Windows evidence for wall speed; retain WSL clock limits. Fresh launches, rematches and checkpoint continuations are different sampling units; a seed or checksum alone does not prove equivalent state |

Do not build a terrain-reasoning claim on information the policy cannot obtain. A known-map
track with declared prior knowledge, a richer terrain-observation track, and learning from
failed orders are different tasks. Likewise, a restore used for an intervention must pass
checks for its actual state, resources and mode; [checkpoint coverage](checkpoints.md#limits)
does not automatically extend to new armies, equipment or spells. From handover onward,
all continuations run at 1x. "No new orders" preserves standing orders and is not an idle
counterfactual.

JUDGEMENT: Opponent control — Codex, 2026-11-04: proposes native-AI battles as the main
comparison and separately labelled scripted-event diagnostics when exact opportunities need
control. Combining them is an alternative; opponent realism and causal claims depend on this.

Owner reply 5 permits considering easy scripting later and defers it for the initial
scenarios. The separation proposed here remains unadopted and rests on JUDGEMENT
`docs/twwarhammer3/scenario-guidelines.md` Opponent control. Prefer conditions native AI can
produce and that the evidence supports. If exact wave or
threat behavior requires scripting, disclose the intervention, trigger, state access and
what enemy freedom remains. Privileged script knowledge must not leak to friendly policies.
A scripted diagnostic may establish a mechanism without establishing performance against
native AI. No such opponent or event system is authorized for implementation by this page.

## Multi-agent scenarios

The owner's [third Cannae battle](cannae-communication.md) studies a single army whose
command groups coordinate through prebattle plans, local views, signals and couriers.
Those channels and views are proposed additions, not capabilities of the current team.

Define an agent by action authority: which regiments or armies it controls, its observations,
memory, communication, resources and executor. Geographic groups need not match owners;
a class-based owner can have units on both fronts. Single-client army partitions and native
multiplayer clients differ in resource ownership, vision, clock and synchronization and
must be reported as separate conditions. Consult [team structures](team-structures.md) and
[native multiplayer status](multiplayer-control-foundation.md#implementation-status).

Draw the dependency before writing the scenario: who needs whose action or continuing
support, what each can know, when help is useful, and what happens if support fails.
Include independent parallel jobs as a control for mere workload distribution. Sequential
enabling, simultaneous commitment, continuing cover, shared-resource allocation and recovery
from teammate failure are distinct candidate demands. A shared victory or concurrent calls
is not proof that the decisions depended usefully on each other.

JUDGEMENT: Team comparisons — Codex, 2026-11-04: proposes whole-system comparisons at natural
concurrency, with separate matched ablations for specific coordination claims. A single
resource-equalized ranking differs; architectural interpretations rest on which comparison is used.

Owner reply 6 prioritizes health/morale and relevant cost/latency measures while leaving
comparison design for later. The alternatives below remain proposals, not a selected arm
or resource plan; they rest on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Team comparisons.

- For whole systems, freeze and disclose model, effort, prompts/advice, partition, skills,
  scheduler, memory, preparation, retries and limits. Show all calls, tokens, dollars and
  actual delays beside outcomes. Different totals remain part of the system comparison.
- To isolate a component, hold army, public information, supplied tactics, executor and
  the relevant resource/timing allowance fixed; state residual differences. Compare a
  planner with its executor alone, adaptation with fixed assignments, and reactive support
  with a frozen schedule. Do not call a direct-orders versus skills comparison pure planning.
- Test communication only if it exists. Current suite members share observed allied state
  but exchange no teammate messages; API calls are not messages. Future message ablations
  must leave the rest of the protocol usable and distinguish delayed, absent and stale data.
  Shared alliance vision is not independent local sensing.
- Check ownership and reassignment, simultaneous army-resource spending, conflict handling,
  stale replies, cancellation, departed agents and new/recovered units where relevant.
  One slow member must be assessed under the declared scheduler, not an accidental global
  barrier. Native clients additionally need peer identity/state and effect checks.
- Measure each member's observation basis, delivery/application and effect on a common
  battle clock; distinguish planner age from fresh executor cycles. Existing suite order-age
  summaries do not make those quantities interchangeable. Trace gaps remain visible.
- Separate authoring a controller from executing it. Repeats of one frozen GaP artifact
  test that artifact; claims about the authoring method need independent artifacts with
  their failures and preparation costs included. No one artifact is a sample of many teams.

Treat message count, arrival spread, proximity and idle share as descriptions until checked
against the proposed mechanism. Holding a reserve can be correct; tight formation can be
harmful. [MultiAgentBench](benchmark-references/multiagentbench.md) motivates outcome/process
separation, not an automatic WH3 communication score. [RoCoBench](benchmark-references/rocobench.md)
motivates genuine action dependencies; its planning/execution timing is not our live clock.

## Variation and protection from tuning

JUDGEMENT: Selection and reservation — Codex, 2026-11-04: proposes selecting by coverage and
reference validity, then reserving instances before compared-controller tuning. Selecting by
model separation is an alternative; generalization claims rest on the declared exposure boundary.

Owner reply 7: “Not sure yet.” The following is a retained option, not an adopted split
or a gate on choosing the initial scenarios. Until a boundary is chosen, label evidence
used to change a scenario or controller as development and make no held-out claim.
This procedure rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Selection and reservation.
Author a family and constrained parameter range, then materialize and save concrete
configurations. Record generator version/seed, resolved values and rejection reasons. Freeze
selection and rejection rules before comparison; never redraw a difficult instance silently.
Do not mistake seed reproducibility in our generator for control over all engine randomness.

Curators may check reserved instances with declared witnesses and mechanical validity tools
without exposing them to compared-controller development. Record who saw what, including
an LLM used to author scenarios, inspect traces, write prompts, choose graphs or tune skills.
In this public repository, held out means protected from declared tuning, not secret from
pretraining or impossible for an author to see. If inspection informs a controller change,
move those cases to development and obtain fresh confirmation cases.

Report separately: repetitions of familiar configurations, unseen instances within a
family, new maps/rosters, and new families or modes. Reserve combinations as well as individual
factors where compositional transfer is the question. Do not assume those transfers have
equal difficulty or pool them under one generalization claim. Preserve all rejected versions
and prior results as development history; selection rules must not favor a preferred arm.

## Reporting and aggregation

Owner, 2026-11-04: compare health and morale, with cost, latency and other relevant metrics;
“We can try to have one overall ranking.” Work toward an overall ranking while retaining
individual scenario results. No ranking formula or metric weights are selected by this reply.
With the initial two scenarios, any aggregate describes those two cases, not general WH3 skill.

The current [condition calculation](../../src/twwarhammer3/battle/benchmark.py) combines
unit health with categorical state penalties such as wavering and routing. It is not a
continuous numeric leadership score. The mirror and suite also use different comparison
rules ([current definitions](benchmark.md#outcome-and-score)); “like we already do” does
not select either unchanged as the new overall ranking. Existing scoring remains intact.

Before ranking, settle scenario weighting, engine outcomes versus condition, missing/failed
attempts, and whether cost/latency change rank or are reported alongside it. Keep engine
outcomes visible and retain the standing engine-win priority until explicitly changed.
LLM tactic labels are not added to the score by this planning request.

JUDGEMENT: Family reporting — Codex, 2026-11-04: proposes per-family and per-condition results
before any new suite aggregate. A weighted single ranking is an alternative; an aggregate
requires owner-selected population/weights so prolific variants do not dominate the claim.

The earlier preference above no longer postpones work toward an overall ranking. Its
per-family disclosure remains a useful option, resting on JUDGEMENT
`docs/twwarhammer3/scenario-guidelines.md` Family reporting. Retain the current engine
outcome and versioned condition measures. Present each scenario's
validity/witness status, attempts, outcomes, errors, uncertainty and pertinent diagnostics.
Show unsupported, unwitnessed and unplayed cases rather than silently dropping them. Report
family coverage and missing cells. Separate duration, cost and reliability from victory;
do not invent a scalar coordination score or let tactic detectors override legal wins.

Choose the analysis unit from the design: scenario instances for coverage claims, launches
for repeatability, and independent authored artifacts for generation claims. Rematches and
samples within a battle are correlated. Pair matching declared conditions without promising
identical random trajectories. Predeclare ordering/interleaving, stopping, replacement and
failure accounting; do not report only finished matched pairs. Existing
[evaluation guidelines](evaluation-guidelines.md#4-plan-and-run-trials) give the study details.
No number of repeats makes a narrowly selected suite representative of all WH3.

## Acceptance and maintenance

JUDGEMENT: Validation lifecycle — Codex, 2026-11-04: proposes the gates below and renewed
checks for changed dependencies before carrying a scenario's validity into another release.
Permanent admission is an alternative; released claims depend on the recorded versions and scope.

Owner reply 9 tentatively expects rechecks after game updates. The exact triggers and
procedure remain open. This proposed lifecycle rests on JUDGEMENT
`docs/twwarhammer3/scenario-guidelines.md` Validation lifecycle; it is not an implemented
`status` enum or automated gate. For the first two scenarios, use the human-demonstration
route and settle readiness with the owner before advancing, rather than silently applying
the earlier mandatory public-interface witness proposal.

| Stage | Evidence required to advance | If evidence is missing or contradicts the claim |
|---|---|---|
| Specify | Completed scenario specification, coverage rationale, feasible alternatives, source and interface audit | Remain a candidate; identify the actual missing mechanic or decision |
| Construct | Independent setup readbacks and live action-effect checks for required mechanics; detectors challenged with plausible wrong cases | Repair and version; preserve failure evidence |
| Demonstrate winnability | Tentatively the owner’s manual win, with setup, pause/controls and engine ending recorded; agree further reliability evidence | Record human-demonstrated status only; automated-interface feasibility and repeatability remain separate |
| Validate meaning | Agree a check for the actual decision; consider observed events, controlled comparisons and a calibrated judge where useful | Keep unsupported labels tentative, narrow them or redesign; a judge’s opinion alone is not verification |
| Judge ready and advance | Owner-agreed readiness checks and passes, versions, demonstration/measurement records and unresolved limits; selection/split only when decided | Finish the current scenario before adding the next; proposal approval alone is not verification |
| Maintain | Rechecks of dependencies affected by engine, pack, interface, scenario, helper or detector changes | Mark affected scope pending recheck; retain the prior release's evidence |

Before a verification run, the owner-agreed procedure must identify exact cases, commands,
counts, thresholds, expected failures and output artifacts. Record its pass at the tested
revision in [agreed checks](../agreed-checks.md) only through the existing agreement process.
The mirror's recording/arithmetic pass and checkpoint passes cover their stated scopes;
they do not certify all scenarios or their tactical meaning. An independent reviewer
checks the specification and raw evidence, not the author's summary alone.

A release packet can reuse the resolved scenario manifest, frozen plan, trace/replay,
engine ending, setup readings, ledger and existing report. Add only the missing witness,
validity and exposure references. Every advertised capability should lead to its deciding
check and limits. Publish explicit known gaps; keep evidence location and retention visible.

A changed game build warns under existing policy; it is not silently re-pinned. Notify the
owner and scope the needed rechecks. A new controller does not automatically invalidate the
scenario, but an unexpected legal shortcut can invalidate its capability interpretation.
A new scorer or detector needs its own validation; keep raw records and old-version results.

## Research basis

These are WH3 adaptations of the [collected research](benchmark-references.md), not claims
that another benchmark verifies ours. The existing profiles name pinned code entry points;
recheck upstream before reusing code. The collection's [robot-team review](robot-team-research.md#evaluation-that-tests-the-intended-behavior)
and [evaluation guide](evaluation-guidelines.md#sources) supply further controls, measurement
and uncertainty references.

| Reference | Design used here | Transfer limit |
|---|---|---|
| [BEHAVIOR](benchmark-references/behavior.md), [task definitions](https://behavior.stanford.edu/behavior_components/behavior_tasks.html) | Specify initial conditions and goals separately; sample and preserve concrete valid instances | Logical predicates and valid placements alone do not prove a WH3 battle can be won |
| [CARLA](benchmark-references/carla.md), [ScenarioRunner](https://github.com/carla-simulator/scenario_runner) | Explicit situations, triggers and event criteria; retain outcome-relevant events | Scripted traffic and stepped execution differ from native enemy AI and persistent live orders |
| [SMACv2](https://arxiv.org/abs/2212.07489), [code profile](benchmark-references/smacv2.md) | Challenge feedback claims with fixed schedules; constrain variation in rosters and starts | Its results concern StarCraft policies, not WH3; unseen samples from one distribution are not new-distribution transfer |
| [CheckList](https://aclanthology.org/2020.acl-main.442/) | Capability matrix, simple functional cases, invariance and directional-change checks | An NLP method; WH3 directional predictions and physical equivalences require independent evidence |
| [Procgen](https://arxiv.org/abs/1912.01588) | Separate familiar-instance performance from evaluation on unseen generated instances | Procedural diversity alone guarantees neither feasibility nor tactical relevance |
| [RoCoBench](benchmark-references/rocobench.md), [paper](https://arxiv.org/abs/2307.04738) | Different capabilities, action dependencies and continuing support | Robot tasks/planning do not reproduce WH3 combat, hidden opponents or inference during live execution |
| [MultiAgentBench](benchmark-references/multiagentbench.md), [paper](https://aclanthology.org/2025.acl-long.421/) | Explicit roles and separate outcome/process evidence | Judged coordination is not causal evidence; its inspected graph loop is sequential |

## Choices for owner review

The [owner response table](#current-plan-and-owner-decisions) is the current decision record.
Earlier markers are retained with their limits; they are not nine unanswered questions.

- Selected direction: progress one scenario at a time; initially one simpler and then one
  more complex; try an overall ranking. No specific battles or ranking formula selected.
- Tentative: the owner's manual winning demonstration with owner-only pause; health/morale
  with cost/latency; rechecks after updates. Exact checks and sufficient evidence remain open.
- Deferred: scripting for the initial pair; reservation policy; controller resources and
  comparison design. None is silently settled by the earlier options.
- Active research: [tactic judges](tactic-judges.md), including what to label, evidence to use
  and how to test a judge against owner-labelled examples before trusting its output.

No battle count, probability target, detector tolerance, duration boundary, coverage quota,
score weight or judge model is selected. No implementation or evaluation is scheduled.
