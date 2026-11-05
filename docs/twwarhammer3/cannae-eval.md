# Cannae inspired evaluation plan

Draft, 2026-11-05. **Candidates under construction; A has one scripted live attempt.** This proposes
three separate evaluations following the owner's directions:
**A, a recognizable Cannae pattern**, and **B, changing reserve commitments intended to
require fresh contingent decisions**, plus **C, coordinated execution by agents sharing
one army under limited communication**. The [comparison design](cannae-comparison.md)
specifies A/B's controls; [battle C](cannae-communication.md) separates prebattle agreement,
local initiative, signals and couriers. All three need construction and deciding checks. The canonical
construction below puts the controller on the enveloping side of Hannibal's battle at Cannae in
[216 BCE](https://sourcebooks.web.fordham.edu/ancient/polybius-cannae.asp). The difficult decision is how to turn success on one wing into victory in the
main fight while the centre remains under pressure. The controller must decide which
local fight to finish, which to leave, where to keep reserves and when to abandon its plan.

The attraction for frontier-model evaluation is the combination of spatial planning,
changing priorities and dependencies between groups whose orders take time to act.
Knowing the famous solution supplies a starting idea; executing and revising it against
an independent opponent could still be difficult. Whether this particular WH3 adaptation
actually requires those capabilities must be established in development.

This follows the [scenario guidelines](scenario-guidelines.md) and
[benchmark contract](benchmark.md). The owner stopped the earlier
[support-timing investigation](support-timing.md#stopped-comparison-and-next-steps);
this is a separate proposal, not a scheduled replacement or a continuation of that test.
The simpler-then-complex direction remains, with no battle scheduled. The owner has
selected the familiar-versus-improvised comparison and a separate limited-communication
team battle; the exact construction and deciding checks remain open. Anticipation can
still be studied separately without treating any design as the final thesis question.

## Historical situation and what WH3 would preserve

Polybius describes an advanced, curved centre with stronger infantry on its flanks.
As the centre gave ground and Roman infantry pressed forward, those flanking troops
turned inward. Cavalry success on one wing enabled help on the other and then attacks
on the infantry's rear. That sequence supplies the design's linked tasks.
[Polybius, Histories 3.113–116](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Polybius/3%2A.html#113).

The historical account is a design reference, not an engine specification. In particular,
we should not assume that a WH3 formation can execute a controlled retreat while engaged,
that native AI will follow it into a pocket, or that an encirclement guarantees surrender.
Use ordinary units and their actual morale, collision and pathfinding. No historical
reskin, ancient army sizes, river reconstruction or casualty target is needed.

JUDGEMENT: Situation and fidelity — Codex, 2026-11-05: proposes the enveloping side of
Cannae at regiment scale, preserving dependent manoeuvres. A breakout from the other side
or a literal reconstruction would change the decisions; the candidate rests on this choice.

The intended sequence is: contain the infantry advance; gain freedom on a cavalry wing;
redirect that force instead of pursuing indefinitely; bring both flanks into the same
engagement; recover if one part fails. This is more demanding than a single flank attack
because one group's apparent success can make the army worse off if it arrives too late,
leaves another wing exposed or consumes reserves the centre needs. It also allows a
competent controller to reject double envelopment when the opponent does not cooperate.

The historical name creates a memorization risk. We can ask whether familiar tactical
knowledge transfers into contingent control, but cannot call the task novel reasoning
merely because its coordinates are new. A fixed plan and simple feedback rules are
essential comparisons. The [two-battle design](cannae-comparison.md#what-would-justify-confidence-in-online-adaptation)
adds a test of fresh information and contingent response beyond recognition: appearance
alone does not identify either memorization or improvisation.
[SMACv2](https://arxiv.org/abs/2212.07489v2) showed that timestep-only
policies could do well on several original SMAC scenarios; that motivates this challenge
to our interpretation, without establishing what will happen in WH3.

## Proposed battle specification

Owner clarification, 2026-11-05: **any faction and lords may be considered for this eval**.
The restricted content and no-lord fixtures belonged to multiplayer work on the VM.
They do not constrain this local scenario or a model team sharing its single game client.

JUDGEMENT: Construction profile — Codex, 2026-11-05: proposes the roster and settings below
as one development starting point. Different troop quality, scale, geometry or timer could
remove or reverse dependencies; balance and difficulty claims rest on this profile.

The starting Empire mirror is a design choice: familiar unit types make the infantry and
cavalry interactions easier to inspect. These are functional stand-ins;
the two armies are not historically equivalent forces. Recruitment on the actual host
must still be checked. The starting hypothesis is an enemy infantry advantage and a
friendly cavalry advantage, not equality of cost or proof of balance.

The roster review can consider a Bretonnian enveloping army against Empire, or another
faction pairing, using the [faction catalogue](tactics-reference.md#factions-and-army-compositions)
as a source of candidates. Such a choice changes matchup, morale and mobility as well as
the manoeuvre; its suitability needs the same witness and mechanism checks. A lord-led
version can add a decision about where command support is most useful, while mounts,
passives, abilities and the consequences of losing the lord become explicit setup and
measurement requirements. Neither faction identity nor adding a lord establishes difficulty.

| Group | Proposed regiments | Initial job and tradeoff |
|---|---|---|
| Friendly centre | 4 Swordsmen | Make contact and remain useful while other groups act; holding, shortening the line and giving ground are alternatives |
| Friendly flank reserves | 2 Greatswords, one on each side behind the centre | Turn inward when useful, reinforce the centre, or intercept a threat; committing both removes the reserve |
| Friendly decisive cavalry wing | 2 Empire Knights | Overcome the opposing horse, then choose pursuit, cross-field support or the enemy infantry's rear |
| Friendly containing cavalry wing | 1 Empire Knights | Keep the other enemy horse occupied or disengage; it cannot be assumed to win alone |
| Enemy infantry | 8 Swordsmen | Native AI has a larger infantry group, free to advance, widen or split it |
| Enemy cavalry | 2 Empire Knights, one on each wing | Threaten friendly flanks; their actual assignments remain the AI's choice |

This is nine friendly and ten enemy regiments. The unit keys already used in the repo are
`wh_main_emp_inf_swordsmen`, `wh_main_emp_inf_greatswords` and
`wh_main_emp_cav_empire_knights`. Use rank zero, full starting strength, no added characters,
items, spells, reinforcements, missiles or artillery. Lordless armies still have engine
command and morale behaviour: record the command unit and check whether its loss dominates
the proposed manoeuvre. Lordless play is a proposed control of complexity, not an account
restriction. The owner may instead select lords when freezing the first roster; adding
them after that freeze changes the scenario version and interpretation.

| Field | Proposed setting or required resolution |
|---|---|
| Mode and role | `classic` / `land_normal`; friendly defender, native AI attacker |
| Factions and recruitment | Both `wh_main_emp_empire`, subculture `wh_main_sc_emp_empire`, explicit `lord: false`; check the allow-no-lord profile and actual recruited armies |
| Engine | Existing pin at implementation time; currently 9.0.5, build 26403568; read `doctor`, report a mismatch and request owner re-pin |
| Map candidate | Existing `battle_preset_qb_wh2_dlc17_taurox_rune_tortured_axes`; choose a usable open area only after terrain and formation checks |
| Difficulty and scale | Normal, AI modifier 1.0, large units (`0.75`), realism off |
| Timer and funds | 1,200 battle seconds; 20,000 lobby funds, with readback that both fixed rosters fit |
| Toggles | `behaviour_defaults: true`; supported friendly fire-at-will on, skirmish and defend off; read back both armies, with enemy settings left engine-controlled |
| Public task | Win the battle and preserve the army where possible; every permitted engine win, including a timer win, counts |
| Input and control | Current structured public observation/action track; fixed armies and deployment; automated play unpaused at 1x |
| Exposure and status | Development candidate; no reserved set, winning witness, agreed readiness check or measured difficulty |

Absolute placement is intentionally unresolved: the earlier support scenario's nominal
origin placed a formation at a cliff. A map key and clear coarse terrain cells are
insufficient. The construction step must save an explicit, fully resolved placement for
every regiment, including width and bearing, before anyone evaluates a controller.

Use the following relative layout to guide that step. The centre projects forward in a
shallow convex line; the Greatswords are set back at its ends; the two cavalry wings have
clear routes outside the infantry. The enemy infantry starts opposite the centre, in
several ranks with enough room to form, and its cavalry starts outside that block.
Leave usable space behind the friendly centre and around both enemy flanks. The widths,
gaps and distances are construction parameters under the marker above, to be fixed from
formation and travel measurements rather than presented as historical constants.

```text
                       Enemy rear and usable approach space
        Enemy horse       Enemy infantry block        Enemy horse
                             facing down

                          Forward friendly centre
                               C        C
                        C                      C
                  Left reserve                 Right reserve
      Two friendly horse                             One friendly horse
                      Space to shorten or withdraw the line
```

This picture is schematic, not a deployment file or proof that the routes work. If this
map has no suitable area, select another recruitable Land map with the owner and record
the change before balancing. Do not shrink formations into unusable gaps to preserve it.

JUDGEMENT: Public presentation — Codex, 2026-11-05: proposes a neutral scenario/job label
and factual task briefing, without the historical solution. Giving all arms a Cannae hint
is an alternative; transfer and advice comparisons depend on the presentation.

The model gets the legal roster, visible state and rules, with no required tactic or
private future positions. Keep the implementation name out of model-visible metadata
if testing the neutral briefing: inspect the actual payload, including job/scenario text,
not only the prompt. A separate advice condition can name the tactic equally for all arms.
Neither neutral names nor a public repository guarantee absence from model training data.

## Decisions the battle could test

The following are falsifiable design predictions, not requirements for a successful play.
Each depends on the proposed construction profile and on the opportunity actually occurring.

| Public cue | Feasible choices to compare | Expected consequence and condition that changes it |
|---|---|---|
| Enemy infantry advances while friendly cavalry is still engaged | Hold the projected centre; shorten or withdraw it before loss of control; commit a reserve | Preserving an effective centre may keep flank attacks useful. If withdrawal exposes units or the enemy spreads, holding or reinforcing may be better |
| One enemy cavalry unit routes while the main infantry fight continues | Pursue it; redirect toward the main fight; support the other wing | A local win becomes useful support only if the cavalry reaches a consequential fight. If the routed enemy rallies or the far wing collapses, immediate rear attack may be the wrong choice |
| The enemy's forward infantry passes the flanking reserves | Turn both reserves inward; commit only one; keep them guarding the sides | Inward attacks may punish overextension. If enemy infantry has split toward the reserves, following the original pincer plan may expose the centre |
| A friendly group routes or loses its route | Reassign remaining forces; recover/rally; continue the original plan | Useful recovery requires a viable alternative. If the battle is already irrecoverable, a loss does not establish a failure to adapt |

The complexity comes from dependencies and competing uses for the same units, rather
than unit count alone. The centre supplies continuing support to the manoeuvre; cavalry
success enables a later job; the reserves must choose between completing that job and
preventing collapse elsewhere. A four-part plan can fail even when each local order is legal.

For anticipation, a possible question is whether the controller acts on where an enemy
or friendly group will be when an order takes effect. Inference time, path length, turning,
engagement and morale all affect that future. A model need not issue an explicit prediction
to behave prospectively, and a good written prediction need not produce a good action.
Do not assume this is the selected research question or revive the stopped delay study.

## Implementation using the current repository

The initial construction needs no new game assets or native multiplayer client. Existing
placement and movement code provides a plausible route, with important checks still needed.

| Existing component | What can be reused | Work or limitation specific to this proposal |
|---|---|---|
| [`configs/twwarhammer3/scenarios.json`](../../configs/twwarhammer3/scenarios.json), [`battle/setup.py`](../../src/twwarhammer3/battle/setup.py) | Fixed rosters/settings and `deployment` entries by type, position, bearing and width | Add one development declaration only when selected; resolve all inheritance and map duplicate types to observed identities |
| [`twwarhammer3_battle.lua`](../../src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua) | Temporarily place both armies, then release enemy units to native AI | Check the actual shape after release. Existing x/z acceptance has a 25 m tolerance and does not establish achieved facing/width |
| [`protocol.py`](../../src/twwarhammer3/protocol.py) and the Lua order handler | Move, attack, halt, formation facing/width and queued movement/attack | Withdrawal is ordinary movement, not an atomic feigned-retreat action; routing/shattered units cannot be ordered. Check disengagement and routes with these regiments |
| [`battle/play.py`](../../src/twwarhammer3/battle/play.py), [`scripts/wh3_queue.py`](../../scripts/wh3_queue.py) | Job manifests, public input boundary, fresh launches, ledger caps, traces and raw outcomes | Freeze the chosen study before comparison; no executable plan or launch is created by this document |
| [`battle/manual_demo.py`](../../src/twwarhammer3/battle/manual_demo.py) | Owner recording/handover workflow | Its present interface is specific to support timing; generalize scenario selection and verify this setup's handover before using it |
| [`battle/team.py`](../../src/twwarhammer3/battle/team.py), [`battle/controllers.py`](../../src/twwarhammer3/battle/controllers.py) | Asynchronous members, ownership validation, one mailbox writer; current Knights/rest or suite class split | Selecting a general class team needs an explicit adapter/profile; separate centre/wing owners of identical types need a new checked partition |
| Existing trace, replay and [`reports.md`](reports.md) workflow | Outcomes, unit condition, visible paths, member identities, decisions and order evidence | Add only the selected event annotations/readers. The regular recorder does not provide an omniscient enemy timeline |

Battle A initially retains native AI, with no enemy choreographer. Native AI
is free to attack a flank, spread out or stay out of the intended pocket. In that case,
retain the attempts and reconsider the Cannae interpretation. Battle B's
[bounded reserve controller](cannae-comparison.md#implementation-boundary-and-checks) is a
new proposed implementation, with its control scope and verification still for owner
review. It must disclose information, triggers and remaining enemy freedom, and be reported
separately. Scripted-opponent evidence does not establish performance against native AI.

For any later variant generator, follow the explicit configuration pattern in the
well-known [SMACv2 repository, `StarCraftCapabilityEnvWrapper.reset`](https://github.com/oxwhirl/smacv2/blob/577ab5a2cff2391f8df582da5731ea9cd6adf3c6/smacv2/env/starcraft2/wrapper.py):
materialize the construction parameters and save the resolved instance. Do not copy its
invalid-reset retries or stepped execution; our failures remain visible and WH3 keeps
running during inference. Keep generation, execution and measurement separate, using
the existing scenario/queue/report structure rather than a parallel benchmark framework.

## Development and repeatable validation

### Construction in progress, 2026-11-05

The owner requested implementation of A, B and C during an approximately ten-hour away
window. A's first development declaration is `emp-envelopment-a-v1` in
[`scenarios.json`](../../configs/twwarhammer3/scenarios.json). It uses the proposed nine
friendly and ten enemy regiments, native AI and ordinary engine outcomes. B's reserve
adapter and C's local views/channels are subsequent implementation work. None has an
agreed readiness check; these remain unverified candidates outside existing suites.

JUDGEMENT: Initial resolved geometry — Codex, 2026-11-05: selects the open negative-z strip
on the proposed map, with friendly facing east and enemy west; the centre projects 20 m.
Other spacing/orientation can change useful routes and difficulty; live construction rests on this.

The friendly centre occupies x=60–80, z=-175 to -325, with Greatswords at x=0,
z=-125/-375. Two cavalry start at z=-85 and one at z=-425. Enemy infantry uses two
four-regiment ranks at x=245/290, cavalry outside them. Infantry widths are 40 m;
cavalry widths are 30 m. This rotates the schematic above to avoid the origin's cliff.
The prior support battle's saved 32 m terrain grid suggests the strip is clear; it does
not establish complete formation footprints or routes. The first live attempt checks
recruitment, setup, native AI behaviour and movement before tactical strength claims.
Task brief/card and raw evidence: `runs/cannae-build/`.

At `d7003f3`, one native-AI battle with `rush_nearest` recruited and placed all nineteen
regiments and ended with an engine win at 468 battle seconds, zero invalid orders and
$0 model spend (`runs/cannae-build/a-rush-01/`). This demonstrates a working construction
attempt, not readiness or difficulty. A nearest-enemy controller succeeded without an
explicit envelopment plan; retain it as a challenge to that interpretation. The manoeuvre
witness, route checks and repeatable readiness procedure remain outstanding.

JUDGEMENT: Readiness procedure — Codex, 2026-11-05: proposes the staged checks below,
starting with setup and owner demonstration before capability claims. Outcome-only readiness
is an alternative; all scientific labels depend on the eventual agreed check and its pass.

These are proposed procedures. No Cannae check is entered in `agreed-checks.md` until the
owner agrees its concrete cases, commands, counts, tolerances, failure rules and outputs.
The earlier timing check and existing checkpoint passes do not verify this scenario.

1. **Construct and inspect the opportunity.** Verify recruitment, role, mode, settings,
   unit identities, initial strength, command unit, supported toggles, actual formations
   and all required routes against lobby and independent engine/video readings. Measure
   the native enemy's behaviour after placement under a declared simple controller. Stop
   on a setup or recording defect; a working setup that fails to create the hypothesized
   problem is evidence against the design, not an infrastructure error to discard.
2. **Check orders reach their effects.** On the actual setup, demonstrate movement around
   either flank, redirection after combat and any withdrawal the witness uses. Trace
   observation → submission → acknowledgement → movement → engagement. Inspect turning,
   entanglement, rallying and persistent queues. A route acknowledgment establishes only
   acceptance; a unit centre inside a polygon establishes only geometry.
3. **Record the owner's winning demonstration.** Use the exact frozen configuration and
   record manual controls, information, pause intervals and engine ending. Only the owner
   may pause. Retain failed attempts. A win establishes human-demonstrated possibility;
   if it depends on a view/action the structured interface lacks, resolve that difference
   before interpreting model losses. Public-interface wins at 1x can add evidence later;
   they are not silently imposed as a new gate on the owner's tentative manual route.
4. **Challenge the intended mechanism.** Compare the reference play with the controls
   below, with action-effect checks for each. Look for coupled fights and consequential
   reassignments. If the cavalry can win alone, the centre wins unsupported, or the AI
   splits into unrelated duels, revise the claim or propose a new version. Any legal
   shortcut win stays a win. Do not rebalance until every weak baseline loses.
5. **Agree readiness and freeze a study.** Select the research question, an independent
   deciding check and enough fresh attempts for the claim. Freeze the full resolved
   setup, controller/advice versions, detector definitions and analysis before comparison.
   Add a complexity or variation only after the current construction is understood.

Required negative checks follow the failure mechanism. Swap two same-type unit IDs to
challenge setup and ownership readers. Supply an accepted order whose unit never moves.
Show reserves surrounding empty space, cavalry merely pursuing a routed unit and two
separate duels. Include obscured enemies, a rally after rout, missing frames and events
whose sampling brackets overlap. A detector must distinguish these from useful engagement
or report unknown; it must not turn a pleasing shape into a successful envelopment.

## Controls and optional research directions

JUDGEMENT: Study arms — Codex, 2026-11-05: proposes the controls and alternative research
tracks below. Choosing a different executor, advice or resource allowance changes attribution;
no arm set or primary contrast is selected until the owner chooses the question.

The first controls need to expose easy solutions and test the interpretation:

- A working nearest-enemy attack and a competent concentration rule test whether ordinary
  pressure already solves the battle. Confirm they receive and attack real visible targets.
- A frozen manoeuvre schedule, developed separately from evaluation, tests whether a
  memorized sequence suffices. Its schedule uses no current feedback beyond legality.
- A simple feedback controller redirects cavalry when its target routes and commits
  reserves from observable conditions. This tests whether a small rule set already
  explains what looks like sophisticated planning.
- A reference with cavalry left pursuing, or one reserve withheld, probes a specific
  dependency with the remaining executor unchanged. These are interventions to interpret
  the battle, not obligatory losing baselines or hidden conditions on model victory.

The owner has selected the familiar-versus-improvised comparison. Its
[within-battle controls](cannae-comparison.md#separating-recognition-from-task-difficulty)
prevent raw differences between A and B being read as a measure of memorization. The
following remain additional research options:

| Direction | Comparison | Claim it could support and remaining confound |
|---|---|---|
| Decisions under changing conditions | One frozen model/controller versus fixed schedule and feedback rules on declared variants | Whether feedback/adaptation helps these tasks; winning alone does not reveal internal reasoning |
| Anticipation | Prospectively recorded predictions and actions, with a matched uninstrumented controller | Observable forecasting accuracy and whether the measurement changes play; added output consumes time/tokens |
| Independent model members | Single direct controller versus existing asynchronous class ownership, with equal factual/tactical advice | Whole-system effect of partitioning work; differences include information projection, calls, concurrency and cost |
| Hierarchical control | Model planner plus a shared executor versus that executor alone | Added value of the planner under its contract; direct orders versus skills also changes execution |
| Communication or reassignment | A future role-based team with/without one named communication or transfer mechanism | Contribution of that mechanism after a matched protocol is built and checked; current teams have no teammate messages |

Current members see allied condition and visible targets, but not teammates' queues,
orders or notes. Their alliance vision is shared; it is not independent local sensing.
A geographic design could assign centre, both infantry flanks, and cavalry to separate
owners, but splitting identical Swordsmen/Knights by location is not the current type/class
partition. Bind roles once to verified public unit IDs, preserve ownership as they move,
and add explicit transfer/version handling if reassignment is selected. Never determine
ownership afresh from which side of the map a unit currently occupies.

A future communication study must specify what a message means, when it was observed and
delivered, and which recipient can act on it. Check stale messages, stale replies, duplicate
ownership and one slow member without an accidental global barrier. Existing no-message
teams already allow useful coordination through observed allied state, so a benefit from
multiple agents is not automatically evidence for communication or a commander hierarchy.

For whole-system comparisons show natural latency, calls, tokens, dollars and preparation
cost beside battle results. For an architectural claim, choose a separate matched ablation
with the same information/advice, executor and declared resource limit. Equal total tokens,
equal dollars and equal wall time answer different questions; no setting makes them
interchangeable. Keep provider/model/effort and scheduling identities in the manifest.

## Measurements and interpretation

Engine outcome remains primary and all legal wins count. Record per-regiment tactical HP,
entity count, morale where available, routing/rally/shattered/departed status, and the first
engine ending; keep missing values unknown. The owner's interest in health/morale and an
overall ranking carries over, but this proposal adds no formula, weight or success bonus.
The existing suite score is not automatically this candidate's scorer. Read errors, caps
and gameplay outcomes separately, retaining a known engine ending alongside a later error.

JUDGEMENT: Diagnostic events — Codex, 2026-11-05: proposes the evidence definitions below
as descriptive candidates. Different contact, control-loss or spatial rules change labels;
event thresholds and their deciding checks must be agreed before interpretation.

| Event or quantity | Evidence and limit |
|---|---|
| Decision opportunity | First public observation containing the relevant cue; private setup/recording cannot move the policy's knowledge earlier |
| Centre remains useful | Identity-specific condition, controllability and engagement over time; HP or a routing flag alone is not all useful support |
| Cavalry reassignment | Target/order change followed by movement and engagement in the other fight; an issued command or route alone is insufficient |
| Flank/rear engagement | Relative facing/formation and actual contact against the relevant enemy, corroborated with native/video evidence; nearest centres do not establish it |
| Coupled action | A documented dependency plus the selected controlled comparison; contact overlap or message count is descriptive |
| Delay and order age | Observation, submission, application and effect on engine time; Windows evidence for wall speed and latency, retaining the known WSL clock limits |

Use independently sampled recordings rather than only states taken when a model answers.
Choose sampling frequency and tolerances to resolve the proposed events, measure recording
overhead, then freeze them across arms. Represent event times as sampling intervals;
overlapping intervals do not establish order. Hidden enemies stay absent from public
records. Additional private engine measurements for validation must remain inaccessible
to policies and must declare their visibility/coverage limits.

An LLM/VLM judge is an optional annotation assistant under the
[judge proposal](tactic-judges.md), not the authority for outcome or causation. Compare its
labels with independently annotated true, false and ambiguous sequences, conceal controller
identity, and test persuasive but false action narratives. No judge model is selected.

JUDGEMENT: Forecast protocol — Codex, 2026-11-05: proposes an optional structured,
prospective event forecast on public inputs. Retrospective text coding is an alternative;
forecast claims depend on the horizon, event definition, continuation and sampling rules.

If anticipation is selected, define a few events before the run, such as a named enemy
crossing a declared line or a named friendly group losing controllability within a
battle-time horizon. Record the probability, observation sequence, issuance time, horizon
and event identity before the outcome. A forecast delivered after its target time is late,
not a successful prospective prediction. Freeze opportunity sampling independently of the
model's answer frequency and report omitted, late and unresolvable forecasts.

Score resolvable binary probabilities with a declared proper score such as mean
`(probability - observed_event)^2`, alongside calibration and a constant/base-rate or
simple motion reference fitted on development data. The horizon, sample count and scorer
are still owner choices. Summarize within battles before comparison; dozens of predictions
from one trajectory are not dozens of independent battles. A forecast under the policy's
actual future actions describes that joint process: it cannot score what would have
happened under another action. Movement and a change of plan may prevent its own predicted
danger. Record the continuation assumption and avoid calling that a model error without it.

Retrospective rationales and visible plan text can explain what to inspect; they do not
expose faithful internal reasoning. To ask whether a decision helped, use the controlled
comparisons above. Optional checkpoint branches require separate restore equivalence
checks for these armies, queues, morale and hidden state; current checkpoint successes do
not supply identical counterfactual futures here. All continuations run at 1x after handover.

## Variation and the eventual run plan

JUDGEMENT: Variant design — Codex, 2026-11-05: proposes constrained, materialized variants
after the base case works. A single familiar layout is an alternative; adaptation and
generalization claims rest on the declared exposure boundary and validity of each instance.

For A, possible interventions include swapping which wing has the cavalry advantage, changing
available space for the centre, or changing one enemy wing's strength. Predict in advance
which choice should change and why. Changing several properties at once is transfer to
another battle, not isolation of a single mechanism. Physical reflection is not presumed
equivalent on real terrain; consistent ID/list renaming is a separate presentation test.
No generator is required for the first canonical case. These changes alone do not establish
improvisation; B's [reserved combinations and fresh assignments](cannae-comparison.md#battle-b-construction)
must change which response is useful and pass the adaptation evidence checks.

Until the owner chooses a reservation policy, all inspected/tuned instances are development
and carry no held-out claim. Later freeze exact instances, validation history, rejection
reasons and who saw them before controller tuning. Every reserved battle needs its own
feasibility evidence; procedural sampling does not prove winnability.

JUDGEMENT: Trial design — Codex, 2026-11-05: proposes fresh-launch episodes and interleaved
arms, with counts/budget chosen for one primary claim. Rematches or adaptive stopping change
uncertainty and exposure; the eventual comparison rests on its frozen plan.

Before scheduling, write a concrete experiment card and queue plan specifying:

- The selected question, primary contrast, model/harness versions, neutral or advised
  briefing, exact scenarios and development/confirmation stage.
- Fresh-launch count per cell, ordering across time blocks, ending/cap rules, failures,
  unstarted attempts, replacements if any, and the minimum effect worth resolving.
- One deciding metric/check, uncertainty method and multiplicity rule. Use the existing
  [small-study guidance](evaluation-guidelines.md#7-use-statistics-that-fit-small-live-studies):
  per-cell win counts with Wilson intervals, exact bounds at zero wins, and methods for
  separate launches rather than pretending matching setup implies paired trajectories.
- Battle and setup time allowance, current provider availability, named existing ledger,
  total and per-job spending caps, and a stop that fits capture and cleanup. Keep both games'
  shared allowances intact. This page authorizes no new spending or game time.
- Artifact identities and output locations: source/configuration/pack, host/build,
  controller/advice/executor, scorer/detector, manifest, queue disposition, trace/replay,
  independent readings/video, first ending and ledger-linked costs under `runs/`.

There is no scientifically justified repeat count before selecting the claim and observing
development variability. Choose it before confirmation using power or desired interval
precision, and show what an affordable plan can resolve. A pilot cannot rank frontier
models, and no number of repeats of one battle establishes general tactical intelligence.

The report should reconstruct every planned attempt and show the engine result beside
condition, cost, latency and the selected decision evidence. Keep setup failures visible;
do not restrict the ranking to battles that happened to show an attractive encirclement.
Independently recount derived numbers from raw records. Recheck affected assumptions after
engine, map, pack, interface, executor or detector changes; retain old versioned evidence.

## Decisions for owner review

The owner has selected separate familiar-tactic, adaptation and limited-communication
battles. Implementation details rest on the named JUDGEMENT choices in this file and the
linked A/B and C designs. The next decisions concern construction and evidence for each demand;
neither a historical narrative nor a green repository check settles those.

| Decision | Options and consequence |
|---|---|
| Construction order and scale | Settle the canonical battle, then validate B's event mechanism before expanding its combinations; decide how much of the proposed force/geometry to retain |
| Comparison method | Settle recognition and adaptation controls; for C settle command groups, local sensing, signals/couriers and channel controls; optional anticipation remains separate |
| Construction and evidence | Review the proposed roster/settings, then settle exact terrain/geometry and the first setup/demo check; decide what additional evidence makes the scenario ready |

After those choices, settle arms/resources, optional forecasts, variation,
ranking formula and trial budget in their respective stages. The proposed contribution
is an inspectable comparison of executing a familiar tactical pattern and adapting to
fresh conditions, with a third battle isolating distributed execution under limited
communication. Demonstrating each battle's advertised demand remains future work.
