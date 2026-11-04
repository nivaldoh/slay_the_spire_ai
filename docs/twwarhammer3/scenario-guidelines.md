# Guidelines for WH3 evaluation scenarios

Owner request, 2026-11-04: diverse scenarios whose winnability and intended measurement
can be checked, including game mechanics, engine quirks and multi-agent control.
**Proposal for review.** The methods below do not add an agreed check, launch a game or
change existing scenarios, scores or historical results. The [benchmark definition](benchmark.md)
still governs: fixed armies and deployment, public structured observations, permitted
orders, engine wins including timer wins, and unpaused 1x play. Approval of these guidelines
would still need concrete per-scenario procedures and recorded passes under the
[verification rule](../../AGENTS.md#verification-hard-rule).

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

The proposed core rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Core eligibility.
This differs from current `suite-v1`, which retains unwitnessed candidates. Adoption would
create a new release; it would not delete failed attempts or retroactively admit old battles.

| Claim | Required evidence | Insufficient substitute |
|---|---|---|
| Constructed correctly | Declared setup compared with independent lobby/engine readings; required actions reach their effects | JSON accepted, a command acknowledged, or a green offline suite |
| Winnable under this interface | A valid complete win by a disclosed controller using the same public information, actions and timing contract | Equal army cost, an omniscient script, a paused demonstration or a win on another version |
| Reliably reproducible witness | Fresh confirmation attempts under a frozen plan, with counts and uncertainty for the declared conditions | Rerunning until a win or reusing the tuned success as confirmation |
| Exercises a named decision | The opportunity occurs and a controlled comparison supports that decision's relevance | The scenario name, a good-looking manoeuvre or correlation with winning |
| Generalizes | Frozen controller evaluated on declared reserved variants or families | More launches of a familiar battle |

A checked win establishes possibility for that execution, not success on every future
engine trajectory. No finite empirical check proves universal winnability of a random
scenario generator. Use a finite catalogue of concrete configurations with individual
witness records for a claim that **every released scenario is witnessed**. A generator
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

Maintain one coverage row per concrete scenario and a family summary. The matrix below
rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Coverage design. It is a design
space, not a demand to run its full Cartesian product. Select cells for distinct decisions
and important interactions; state omissions. Freeze selected cells and their relative
representation before compared-controller results can influence selection.

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
| Witness | Frozen controller/artifact, information access, timing, complete winning records and independent reproduction |
| Controls and predictions | Simplest shortcut, fixed plan, reactive alternative or executor-only comparison; what result would weaken the claim |
| Measurements | Outcome, setup validity, opportunity and action-effect events; data source, missingness, detector definition and negative cases |
| Variation and exposure | Allowed parameter ranges, constraints, realised instances, reserved split, authoring/tuning exposure and rejection history |
| Validation plan | Attempts, unit of repetition, stop/failure rules, pass criteria, uncertainty, budget and named agreed checks still needed |
| Release record | Source/configuration/pack/controller/scorer identities, evidence paths, current status and conditions requiring recheck |

For each decision write: **When cue C becomes available, choices A and B are feasible;
under condition X they should differ in consequence Y; under variant Z that prediction
may reverse or disappear.** This is a falsifiable design statement, not an instruction
requiring the evaluated controller to choose A.

## Winnability evidence

JUDGEMENT: Witness contract — Codex, 2026-11-04: proposes a public-interface witness for each
concrete core configuration, an independent fresh reproduction and a frozen reliability plan.
One unrestricted human win would be cheaper; eligibility and repeatability claims rest on this.

The procedure below rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Witness contract.

1. **Check feasibility first.** Confirm recruited content, usable routes, needed abilities,
   victory conditions and the time available. Cost ratios and soldier counts are hypotheses
   about balance, not proofs. Audit lordless leadership and army-loss behavior where relevant.
2. **Produce a complete legal winning witness.** A script, model or human acting through the
   same public interface can supply it. Save inputs, orders, effects and the engine ending,
   including the period after the supposed tactical success. Winning one engagement is not
   winning the battle. An ordinary human UI demonstration is a design lead if its information,
   controls or speed differ. Hidden data may validate the record, never guide the witness;
   do not embed private enemy coordinates or event schedules in its code or preparation.
3. **Freeze before confirmation.** Freeze the scenario, witness, helpers, observation/order
   contract and pass criteria. Give an independent checker the public task and procedure to
   reproduce the win from a fresh launch and check the trace. A separately authored witness
   is stronger evidence against shared strategy assumptions; disclose its absence.
4. **Specify repeatability quantitatively.** The plan names the minimum useful witness success
   probability, confidence level, number of fresh launches and stopping rule. Choose counts
   with the [small-sample methods](evaluation-guidelines.md#7-use-statistics-that-fit-small-live-studies),
   not a convenient universal count. An existence win and a repeatability pass have separate
   labels. Until these fields are agreed and confirmation passes, repeatability is unverified.
5. **Cover every released configuration.** Another map, rank, roster, mode, loadout or authored
   placement is a different configuration, even under one family name. Keep its witness and
   validity record. Report per-configuration failures; a good average cannot hide an unwitnessed
   item. Simultaneous claims across many items need a declared error budget, not isolated
   intervals presented as a guarantee for the whole set.

Report the witness's actual observation age, order age and decision gaps, plus its helpers
and any pre-battle preparation. A fast script establishes possibility under its own timing;
it does not establish feasibility at a slow model's cadence. For a latency claim, declare
and check that timing condition separately while the world continues at 1x. Never pause
or slow the battle to make a witness succeed.

Keep every confirmation attempt. Failure does not prove impossibility; diagnose setup,
execution, measurement, witness strategy and uncertainty separately. A repaired witness
or scenario gets new confirmation evidence. Do not replay an unchanged failed gate until
it happens to pass. Difficulty can be calibrated in development with reference players
and controls; do not select battles because they make a preferred model or architecture win.

## Establish that the intended decision matters

JUDGEMENT: Measurement eligibility — Codex, 2026-11-04: proposes checked opportunities,
effect evidence and controlled alternatives before giving a core scenario a capability label.
Outcome-only labels are an alternative; specific skill claims rest on this stronger evidence.

These checks rest on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Measurement eligibility.
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
| Identity and authored starts | Match types and identities through recruitment, placement and observation; engine IDs need not follow roster order. Check both armies privately, including hidden enemies. Check facing/usable formation when material; the current placement check tests x/z, not all geometry |
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

This separation rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Opponent control.
Prefer conditions native AI can produce and that the evidence supports. If exact wave or
threat behavior requires scripting, disclose the intervention, trigger, state access and
what enemy freedom remains. Privileged script knowledge must not leak to friendly policies.
A scripted diagnostic may establish a mechanism without establishing performance against
native AI. No such opponent or event system is authorized for implementation by this page.

## Multi-agent scenarios

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

Comparisons below rest on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Team comparisons.

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

The procedure rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Selection and reservation.
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

JUDGEMENT: Family reporting — Codex, 2026-11-04: proposes per-family and per-condition results
before any new suite aggregate. A weighted single ranking is an alternative; an aggregate
requires owner-selected population/weights so prolific variants do not dominate the claim.

Reporting below rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Family reporting.
Retain the current engine outcome and versioned condition measures. Present each scenario's
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

This lifecycle rests on JUDGEMENT `docs/twwarhammer3/scenario-guidelines.md` Validation lifecycle.
It is a proposed documentation procedure, not a new implemented `status` enum or automated gate.

| Stage | Evidence required to advance | If evidence is missing or contradicts the claim |
|---|---|---|
| Specify | Completed scenario specification, coverage rationale, feasible alternatives, source and interface audit | Remain a candidate; identify the actual missing mechanic or decision |
| Construct | Independent setup readbacks and live action-effect checks for required mechanics; detectors challenged with plausible wrong cases | Repair and version; preserve failure evidence |
| Witness | Legal full win for every released concrete configuration; independent reproduction and preregistered repeatability result | Label possibility/repeatability separately; no unqualified core admission |
| Validate meaning | Checked opportunity and effect evidence, working controls and declared comparison/perturbation result supporting each advertised capability | Narrow label, redesign, or retain only in the exploratory pool |
| Freeze | Owner-agreed procedures and selection, versions, reserved splits, witness/diagnostic records, limits and study plan | No claim of verification from proposal approval alone |
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

Each choice has one marker at its governing section. These links introduce no additional
settings. No battle count, probability target, detector tolerance, duration boundary,
coverage quota or aggregate weight is adopted by this proposal.

- [Core eligibility](#claims-and-eligibility): witnessed, validated core versus retaining all candidates together.
- [Coverage design](#coverage-across-dimensions): family/context matrix and anchors versus another suite composition.
- [Witness contract](#winnability-evidence): interface-faithful per-configuration wins, independent reproduction and a reliability plan.
- [Measurement eligibility](#establish-that-the-intended-decision-matters): evidence needed for each advertised skill.
- [Opponent control](#game-mechanics-and-engine-checks): native battles and separately labelled scripted diagnostics.
- [Team comparisons](#multi-agent-scenarios): whole-system results and separate matched tests of specific mechanisms.
- [Selection and reservation](#variation-and-protection-from-tuning): validity/coverage selection and the boundary around reserved cases.
- [Family reporting](#reporting-and-aggregation): per-family reporting before choosing new aggregate weights.
- [Validation lifecycle](#acceptance-and-maintenance): what must be rechecked as dependencies change.
