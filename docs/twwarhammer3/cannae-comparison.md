# Comparing familiar tactics and adaptation in Cannae evaluations

Owner direction, 2026-11-05: distinguish a recognizable, potentially memorized tactic
from a situation requiring decisions on the spot, using separate eval battles. This
extends the [Cannae plan](cannae-eval.md). The owner subsequently selected a third design,
[C: one-army coordination with limited communication](cannae-communication.md).
**Development implementation is in progress; the scientific labels remain unverified.**
This page details A/B; C has its own specification. Any faction and lords remain available.
The owner requested construction and testing during the current away window; no paid
model comparison is scheduled.

The comparison should make prior tactical knowledge useful in one case and insufficient
to select the concrete response in the other. A controller can still use learned concepts
in both. We can test whether it uses fresh information and changes its actions usefully;
we cannot inspect an unknown training corpus or prove that it invented a tactic internally.
Here, **improvisation means composing or revising a plan from newly observed conditions**.
Evidence for that is stronger than unfamiliar scenery, and narrower than reasoning from
no prior knowledge. The outcome report must preserve that distinction.

## The three battles

| Design | What stays familiar | What the controller must resolve | Evidence needed for its label |
|---|---|---|---|
| A: Cannae pattern | Projected centre, stronger flank reserves, cavalry advantage and opportunity to turn inward | Execute a recognizable double-envelopment plan with normal battle feedback | A checked winning witness and evidence that the historical manoeuvre is useful, without requiring it for victory |
| B: Changing reserve commitments | The same tactical vocabulary and a comparable opening | After the battle begins, read a fresh combination of enemy commitments and friendly condition, then choose where to concentrate, reinforce or abandon the enclosure | Unrevealed future assignments, public cues with feasible responses, conflicting useful choices across cases, and a demonstrated benefit from fresh information over specified controls |
| [C: Limited communication](cannae-communication.md) | A shared Cannae-style plan and agreed signals | Separate command groups coordinate dependent manoeuvres with local views, delayed reports and local initiative | Useful temporal dependencies, audited local inputs/channel delivery and comparisons holding views/plan fixed while changing communication |

A is the existing [construction proposal](cannae-eval.md#proposed-battle-specification),
initially against native AI. It is **familiarity-compatible**, not a pure memory test:
recognition is possible, but a win could come from another tactic or ordinary feedback.
B is a separate scenario family, with each concrete configuration and attempt retained.
One permanently published surprise becomes another familiar scenario after exposure, so
B needs fresh combinations and controlled exposure as well as separate battle IDs.

The original Cannae account is an intentional source of prior knowledge in A. Renaming
units, rotating the picture or omitting the historical name does not remove the structure.
Conversely, a different faction or a random army does not establish a need to improvise.
The distinction rests on changed consequences of choices, not the scenario labels.

C separates communication and distributed execution from this A/B question. It may
supply the same plan to all agents and use native AI throughout, so recognizing the
historical tactic or discovering B's hidden reserve commitment is not its defining demand.
Compare communication regimes within C; a raw A/B/C outcome gap mixes several changes.

## Battle B construction

JUDGEMENT: Reserve mechanism — Codex, 2026-11-05: proposes late enemy reserve commitments
with competing friendly responses. Native-AI-only surprises or an unrelated new battle
would differ; the adaptation claim rests on the implemented mechanism and its checks.

Start from A's roster and map, then designate part of the existing enemy army as a reserve
behind the main line. Do not add hidden troops, change unit statistics mid-battle or
teleport an obstacle into an already committed route. The full roster is declared normally;
enemy movement and condition reach the model only through the permitted visibility rules.
The reserve's starting location, identities and force split are frozen during construction,
and match across B's alternative continuations. The remaining enemy army uses native AI.

The proposed event controller holds only the declared reserve until a predeclared window
in battle time, then assigns it a route and target region. It chooses the commitment from
private episode randomness after the friendly controller and its preparation are frozen.
Draw before launch, independently of the engine/setup RNG, model identity and reply timing,
and seal the assignment from all controller access until its physical effects are visible.
This also permits a matched foreknowledge control with exactly the same selection procedure.
The controller may know that reserves can move and the family of possibilities; it does
not receive the selected future assignment or a symbolic instruction naming the response.

The actual manoeuvre is the cue: successive public positions, bearings, visible types and
engagements reveal what the enemy is doing. The intervention cannot wait for an LLM reply,
require a pause or use private friendly morale to manufacture a last-moment failure.
Trigger time, command authority, destination rules and any subsequent targeting use must
be specified before trials. Full action/effect records remain private to the evaluator.

| Possible commitment | Intended conflict for the friendly controller | Condition that can reverse the useful response |
|---|---|---|
| Reserve joins the pressured central fight | Continue the enclosure or divert flank/cavalry support to keep the centre viable | If the centre is already secure, abandoning an available flank attack may waste the opportunity |
| Reserve approaches outside one friendly wing | Continue turning inward or retain/redirect units to prevent the outer threat | If that threat is weak or cannot arrive while the main fight is decided, committing a reserve to it may be costly |

These are hypotheses for construction, not a solution lookup table. The first engineering
check can use two continuations to test information isolation and differing consequences.
Those two cases alone would support a small contingent-response task. To justify the
stronger improvisation study, vary a **combination** of commitment, approach side and the
portion of the declared reserve committed, with the rest following a declared hold/support
rule. Also evaluate different public friendly conditions produced by ordinary play.
The same visible advance should sometimes warrant interception and sometimes continued
pressure, depending on relative strength, distance and the condition of the centre.

JUDGEMENT: Composition and exposure — Codex, 2026-11-05: proposes reserved combinations
of otherwise familiar commitments and configurations, drawn after controller freeze.
Repeating known combinations is cheaper; broader adaptation claims depend on this split.

Use a finite, curator-validated catalogue first. Each configuration fixes the map, forces,
starting geometry and legal continuation menu. Materialize the selected commitment before
launch, execute it at the event and preserve the draw. Never discard a draw because it
produced a difficult result. Keep full reserve totals constant within comparisons. Different opening geometry
or roster is another configuration, not a hidden change during a battle.

Develop mechanics and controllers on disclosed combinations. Freeze prompts, skills,
graphs, tools and memory policy before drawing confirmation cases. Reserve combinations
that require integrating known factors rather than only reversing left and right. Record
all author/agent exposure and keep confirmation records out of subsequent tuning. In a
public repository this protects against declared development exposure; it does not certify
absence from pretraining. Fresh event randomness protects the exact future assignment
even if the model knows every rule of the generator.

## What would justify confidence in online adaptation

JUDGEMENT: Adaptation evidence — Codex, 2026-11-05: proposes the checks below before the
improvisation label. Outcome-only comparison is an alternative; the claimed need for fresh
decisions depends on information isolation, feasible alternatives and measured controls.

1. **No advance knowledge of the realized branch.** For the same friendly action history,
   changing a future assignment must not change any earlier public input, prompt, tool
   result or harness behavior. Inspect model-visible job/scenario names, random seeds,
   timestamps, ordering, caches and files accessible to tool-using controllers. Inspect
   nested fields too: current `play.public()` removes top-level private keys and the team
   projection forwards most `mode` fields, so a new nested branch field could leak. Private
   evaluator manifests are outside their access. Plant a branch label in metadata to
   show that the audit catches it. Existing Python policy adapters are not a sandbox;
   any broader filesystem/tool access needs explicit isolation before this claim holds.
2. **A legal opportunity to distinguish the cases.** Independently identify the first
   usable public cue and the latest feasible response, using observed order effects and
   routes. There must be enough battle time for the declared interface to act at 1x.
   A hidden choice requiring commitment before it can be known is a gamble, not a test
   of improvisation. Choosing a robust reserve beforehand is valid tactical play.
3. **Consequences that depend on the case.** Cross candidate response plans against every
   declared continuation. A fixed rear attack, centre reinforcement and outer interception
   should have different consequences across cases, with a valid winning route in each.
   Demonstrate effects and engine outcomes; do not declare the intended action correct
   from its name. Agree the required separation, counts and uncertainty before confirmation.
4. **Challenge plans that bypass the choice.** Try concentration, an opening rush,
   destroying the reserve early, waiting, timer defence, splitting forces to cover all
   branches and always reinforcing the centre. Test a competent fixed Cannae plan and a
   simple public-state rule library. A universal solution stays a win and weakens the
   improvisation claim. Do not add a hidden requirement to wait for or obey the event.
5. **Show that new information helps the model's decisions.** Compare live replanning with
   an opening-only plan executed by the same legal executor, then with a prewritten
   contingent policy using that executor. Log which component reads new evidence and
   selects each response. If a shared helper handles the branch, improvement belongs to
   that helper or whole system unless a matched test isolates the LLM's contribution.

A useful construction artifact is a response-by-continuation table: each cell contains
wins/attempts, condition, errors and independently checked action effects. Show the best
tested fixed plan across the whole mixture beside the plans that respond to the event.
Freeze selection of that best fixed plan on development data. A crossed table can rule
out those concrete alternatives; finite testing cannot prove that **every** legal winning
policy must adapt. Do not present a hypothetical 50% guessing ceiling without proving the
action restrictions and absence of a common winning response under the actual task.

Fresh launches do not produce identical engine trajectories. The no-leakage requirement
is conditional on the same prior action history; controllers can legitimately create
different openings. Offline input tests establish the branch code's noninterference,
not live-state equivalence. Checkpoint continuations are optional only after checks of
this battle's complete relevant state; a successful restore elsewhere is insufficient.
Otherwise report randomized launch comparisons and residual state variation honestly.

If friendly actions prevent or neutralize the event, keep the attempt and the win. Record
that disposition without filtering the main comparison to battles where the script's
desired story occurred. A broken intervention and a successfully prevented threat are
different outcomes. Opportunity-conditioned exploratory analyses must retain their full
denominator and cannot replace the outcome over all planned attempts.

## Separating recognition from task difficulty

JUDGEMENT: Comparison controls — Codex, 2026-11-05: proposes briefing and information
controls within each battle, plus separate predictable/live versions of B. Other matching
choices change attribution; raw A-versus-B score differences cannot identify memorization.

Both battles get the same engine objective, information/action track, model/harness
version and resource policy, except the explicitly declared foreknowledge treatment.
Start each trial with a fresh conversation and cleared episodic/team memory; frozen
tactical instructions remain available. Carryover learning would be a separate arm.
Report their outcomes separately. B can change opponent
behavior, force availability and difficulty, so a lower win rate there does not measure
how much A was memorized. Use the following comparisons for narrower claims:

| Comparison | Keep fixed | What a difference means |
|---|---|---|
| A neutral briefing versus A explicitly identified as Cannae-inspired | Physical setup, rules, controller and resources; change only the factual historical cue | Benefit or harm from a recognition cue; not proof that the unprompted model retrieved a training example |
| The same A conditions with a concise supplied tactic | Advice text identical across compared harnesses | Ability to use supplied tactical knowledge; this is a separate advice treatment, not a recognition-only contrast |
| B with its reserve commitment announced before play versus B with it learned from the live cue | Event distribution, scripted authority, setup and controller | Value of knowing the future commitment early; announce only what the intervention controls, not the engine trajectory |
| B live model replanning versus opening-only plan and frozen conditional rules | Same legal executor, game information available to that executor and declared accounting | Added value of online model decisions beyond the stated automation; a strong conditional rule can explain success without extended reasoning |
| Single controller versus model team within A and within B | Same condition, factual/tactical advice and explicitly chosen resource policy | Whether the team advantage changes across these tasks; cost, concurrency and projection differences remain visible |

Retain the original plan's JUDGEMENT `docs/twwarhammer3/cannae-eval.md` Public presentation
for the neutral base briefing. Its named and advised alternatives become explicit controls
here, rather than being mixed into one arm. All arms know the game's rules and the possibility
of enemy reserves. Optional naming/advice calls must not leak the realized B commitment.

For the opening-only plan, the shared executor handles legal IDs, basic targeting/pathing
and the frozen action vocabulary. Document any feedback it uses. For the conditional-rule
control, publish the frozen predicates and decisions; it is deliberately allowed to use
fresh state. If that control works as well as live models, report that online contingency
selection was sufficient. Do not call it evidence for difficult improvisation. If a model
writes a new contingent controller before every battle, its preparation is part of the
system; test that preparation method and include its cost and exposure.

Do not blind the executor by deleting visible enemies: that changes valid target IDs and
therefore the legal action set. The planning component can stop receiving new tactical
information while the common validator/executor keeps the normal public state. Persistent
attack orders already track targets through engine behavior; credit that feedback to the
executor/engine. Include a case where another commitment is needed to test model replanning.

Record public observation basis, chosen actions, application/effect and changed assignments.
Use model explanations and optional recognition questions only as ancillary data. Asking
about Cannae before play can itself prime recognition, and an explanation after the win
does not reveal faithful internal reasoning. No chain-of-thought judge is the oracle.

## Implementation boundary and checks

### Development adapter, 2026-11-05

`emp-envelopment-b-v1` retains A's rosters, settings and friendly deployment, moving only
two enemy Swordsmen to the rear before launch. Their one-based authored placement slots
are bound to actual engine identities by the same type-occurrence procedure used for
teleporting. The Lua adapter takes those two controllers before placement; all other
enemies return to native AI. No extra troops, stat changes or mid-battle teleport occur.

The concrete development catalogue and timings rest on JUDGEMENT
`src/twwarhammer3/battle/reserve.py` Reserve development catalogue. It crosses centre versus
outside approach, north versus south and one versus both reserve regiments committed.
The routes are fixed ground regions; the script never reads friendly units to select a
target. It holds the reserve, issues running waypoint orders at the fixed trigger, then
releases both regiments to native AI at the fixed release time. Uncommitted regiments stay
held until release. These choices need live calibration and do not establish that fresh
reasoning is necessary or that every case has a winning response.

Each planned episode gets a separate independently seeded prelaunch draw, saved in the
ordinary job manifest's `reserve_draws`; the appropriate activation is written before
the first launch or subsequent rematch. The public scenario/job names contain no draw.
Private `evaluation.reserve` records identity, chosen configuration, submission status,
initial positions and the latest actual position reading. The public boundary drops all
evaluation/setup/final data. A configuration, identity or submission failure stops the
job as infrastructure evidence while retaining any engine ending already observed.
Adapters remain trusted Python code, without an arbitrary filesystem/tool sandbox.

Focused component tests cover draws, immutable openings, private-input differences,
controller ownership, holding, one-shot trigger/release and terminal suppression. Fake
controllers can accept a move without moving; their tests explicitly retain separate
position readings. Live routes, event cues and the crossed tactical comparisons remain.
No new procedure is entered in agreed checks. Card and raw evidence: `runs/cannae-build/`.

`emp-envelopment-b-v2` keeps v1's rosters, opening, catalogue and trigger. It changes release
using only the reserve's own condition and position, resting on JUDGEMENT
`src/twwarhammer3/battle/reserve.py` Reserve route completion: a committed regiment
returns to native AI within 25 m of the final route point, when unavailable, or at the
360 s bound. Uncommitted regiments stay controlled through routing/rally until that bound.
Each release records its own time, position, reason and submission status; the aggregate
`released_ms` means all reserve entries have a release disposition. A bound without arrival
is retained as an incomplete route, not silently counted as a completed intervention.
V1 retains its original fixed release; do not pool versions for readiness or strength.

Reserve briefing v1 supplies the same factual catalogue/trigger/release rules to both
information arms. `emp-envelopment-b-announced-v2` inherits v2's entire physical setup
and intervention, adding the realized region, side, count and fixed ground route to the
briefing before play. The ordinary arm has no realized commitment field. The announcement
comes from the very draw activated for that episode; it does not predict native AI after
release or reveal a seed, runtime identities, private health or actual hidden positions.
This disclosure rests on JUDGEMENT `battle/reserve.py` Foreknowledge disclosure.
The single-model renderer and ordinary team projection carry it to actual requests;
captured fake requests check matching announcements and ordinary-arm noninterference.
Old jobs predate this briefing; no model/live foreknowledge effect has been measured.

`play --reserve-seed N` supplies an optional private construction/matched-sequence seed.
Each episode still gets a separate drawn seed and configuration; setup/rotation RNGs are
not reused. Repeating N reproduces selection only, not engine trajectories. The root seed
and every draw stay in the evaluator manifest/configuration, not policy observations.
Default runs still use independent OS-entropy seeds. Construction will cover every declared
case before the response comparisons; this does not create a held-out set or verify adaptation.

### Harder development screen, 2026-11-05

The owner selected a separate `emp-envelopment-b-v3` candidate after passive hold won
all eight B v2 construction cases. Only the four front enemy Swordsmen become Greatswords,
in both the roster and deployment types. All other units, slots, placements, settings and
B v2 reserve mechanics stay fixed; slots 7/8 remain Swordsmen. Scenario version 3 does
not change the reserve adapter's version 2. This candidate is outside existing suites.

First live setup at `3a3f195` shows an additional engine consequence of replacing types:
the ordinary enemy commander is still Swordsman e1, now bound to rear placement slot 5
at (291.6, -175), rather than B v2's front slot 1 at (246.6, -175). The 45 m change
comes from type-based identity binding. Reserve slots 7/8 correctly bind e3/e4. Preserve
this consequence; the live contrast does not isolate troop quality or centre pressure,
and these positions alone do not establish a commander/morale effect.

JUDGEMENT: Harder B construction screen — Codex, 2026-11-05: selects two disclosed
development cases and one attempt per control, rather than the full catalogue/repeats.
Six attempts can expose shortcuts or a broken witness; they cannot establish adaptation.

JUDGEMENT: Harder B launch window — Codex, 2026-11-05: sets the initial queue bound
at 10:20 UTC, leaving 15 minutes after three full 3400 s watchdogs for game cleanup.
Halving case coverage is an alternative; live attempt counts rest on this scheduling choice.

Run Hold, RushNearest and the existing Envelop witness for two episodes each, using
root 106's first two reserve draws: outside/south/two, then centre/north/two. These cases
were disclosed by earlier B construction, not held out. Matching draws do not pair engine
randomness. Envelop has incomplete cavalry routes and is not a winning oracle for this
new force. Retain every engine result, including passive wins and failed witness paths;
do not silently retune the roster to make weak controls lose.

The card checks the resolved declaration, recruitment/settings/placements, reserve
identity and actual route/release dispositions, then each control's actions and ending.
Each two-episode job is $0, unpaused 1x, with start/episode/job limits of 600/1320/3400 s.
Start the three-job queue by 10:20 UTC, stop on infrastructure failure, and start no job
after 12:05 UTC; retain time for cleanup before the 13:25 UTC game cutoff. If preparation
runs late, narrow the declared count before launching. Raw card/checks/review/evidence:
`runs/cannae-build/`. No agreed check, adoption or difficulty claim follows from this screen.

### Additional public witness, 2026-11-05

The first harder screen lost all six attempts, including both original Envelop cases.
Its infantry routes reached deadlines and cavalry redeployment never started. This does
not establish a cause or impossibility. `battle.cannae:WingSupport` is a separate candidate
whole tactic, resting on JUDGEMENT `src/twwarhammer3/battle/cannae.py` B support witness.
Envelop's definitions remain unchanged. Stable own binding, first-seen horse labels and
target persistence inherit the parent's marked development rules.

The northern Greatswords support the currently eligible visible north horse. The other
Greatswords attack infantry directly; the centre keeps its existing engagement rule.
The two northern Knights prioritize north horse, then south horse, then infantry; the
containing Knight prioritizes south horse, then infantry. Routing/dead/departed targets
are excluded, and disappearing contacts are not treated as known dead. No waypoint route
or movement completion is claimed. The controller reads no private reserve draw/evaluation.

JUDGEMENT: Additional B witness screen — Codex, 2026-11-05: repeats the two disclosed
cases with one alternate public tactic rather than changing forces or expanding cases.
This can supply a winning witness, not an isolated remedy or evidence of adaptation.

Prospective card: one attempt per root 106 case, outside/south/two then centre/north/two,
with B3's force, geometry, AI and intervention unchanged. Keep the six prior losses;
trajectories are not paired or held out. Run $0, unpaused 1x, with 600/1320/3400 s
start/episode/job bounds, starting by 11:30 UTC (adding 3400 s gives a planning time of
12:26:40). Stop on an
infrastructure failure or the time bound. Optional air pilots follow only if their
declared window still fits. No adopted suite/check or model comparison.

### Final cavalry-priority construction probe

WingSupport won the outside case at 534.5 s and lost the centre case at 353.2 s, with
zero invalid orders in both. This supplies one legal winning trajectory, not a winning
reference for every B3 case. Preserve the previous six losses and both new results.

`battle.cannae:CentreSupport` is one further separate control, resting on JUDGEMENT
`src/twwarhammer3/battle/cannae.py` B cavalry follow-up. Only the two northern Knights'
candidate priority changes: currently eligible visible north horse, then infantry, then
south horse. WingSupport keeps north/south/infantry. Other roles, binding, current target
sets, cache handling and attack primitives stay the same. Absence is not known death;
the same horse can reappear or rally. Source replay checks the prior WingSupport batches
after extracting its unchanged priority order into a class attribute.

JUDGEMENT: Final B construction probe — Codex, 2026-11-05: tries this one alternative
second commitment on both disclosed cases, without another roster or case search.
Any difference includes fresh engine trajectories; it is not an isolated causal result.

Run the same root 106 cases once each, $0, unpaused 1x, with 600/1320/3400 s bounds,
only after the air queue's actual exit and full gates. Start by 12:15 UTC; adding 3400 s
gives a planning time of 13:11:40 before the 13:25 UTC game cutoff. Supervisor preparation
adds time; this is not an observed watchdog deadline. If late, record not started. This is
the final planned B construction probe in this window; no model comparison, score,
agreed check or suite adoption. Raw card/checks: `runs/cannae-build/`.

At `932c0a4`, the dispatch passed the queue bound at 12:14:59.387832 UTC; the child
manifest was created at 12:15:00.875797. Both cases ended in engine wins at 472.9/466.0 s,
with nine/zero invalid orders and $0. All nine refusals were `target_not_visible`; source
candidate checks still matched. The exact-source audit covered 815 recorded batches and
159 attacks, including all refused orders; it does not cover every quiet poll. This gives
a legal winning trajectory for each selected case, not for the other six B3 combinations
or a demonstration of necessary adaptation. No further B probe is scheduled this window.

### What the B evidence supports now, 2026-11-05

`scripts/wh3_reserve_cells.py JOB...` rebuilds the rows and cell tally from raw manifests and results.
There are 29 B battles (v1 2, v2 8, v3 19), one attempt per cell except two repeated v3 cases, all
engine-ended. All of this is unverified.

Each construction job was one game launch. Inside a job, rematches matched in all 41 shared samples
up to the 45 s trigger in 28 of 28 v2 pairs. On v3, RushNearest's orders landed on different ticks at
15.4 and 15.7 s, so its positions differed from 16.0 s; on v1 they differed from 27.1 s. Hold's 8 of
8 and each construction v3 controller's two attempts therefore rest on one launch and are not
independent; count launches beside attempts. Window 1 used one launch per battle.

| v3 controller | Outside/south/2 | Centre/north/2 |
|---|---|---|
| Hold (one launch) | Lost, 377.4 s | Lost, 330.5 s |
| RushNearest (one launch) | Lost, 334.3 s | Lost, 498.7 s |
| Envelop (one launch) | Lost, 390.3 s | Lost, 456.2 s |
| WingSupport (one launch) | Won, 534.5 s | Lost, 353.2 s |
| CentreSupport (one launch) | Won, 472.9 s | Won, 466.0 s |
| CentreSupport, window 1 (a launch each) | Won, 519.9 s | Won, 527.7 s |
| Evade, window 1 | Lost, 477.9 s | Not played |

| Case in window 1, CentreSupport, one launch each | Result |
|---|---|
| Centre/north/1 | Won, 450.4 s |
| Centre/south/1 | Lost, 474.8 s |
| Centre/south/2 | Won, 540.7 s |
| Outside/north/1 | Lost, 874.7 s |
| Outside/north/2 | Lost, 357.2 s |
| Outside/south/1 | Won, 537.2 s |

On v1 and v2 one fixed public-state controller won every case it tried: Hold 8 of 8 on v2, RushNearest
2 of 2 on v1. On v3 no tested controller has: CentreSupport won 5 of 8, and only 3 of the 6 cases that
did not select it. Nothing shows a fresh contingent response is needed or unneeded, because no other
fixed rule has played the three lost cases on v3. CentreSupport reads public state, so it is the
conditional-rule type of control, and a rule that reads visible reserves would be the same type.

Whether the case matters remains open; the [window results](cannae-eval.md#window-1-results-2026-11-05)
explain why the outside/north and outside/south split is not a finding. There is no baseline
without the reserve, so the reserve's own effect is unmeasured. The two selected cases won in both of
their launches, which cannot be read onto the other six. In the first ten v3 battles a regiment routed
before the reserve first fought in 6 of 7 losses and in 2 of 3 wins, and CentreSupport gave no order at
a reserve regiment before 425.5 s and 462.7 s.

Of the 46 regiments committed on v2 and v3, 45 arrived. In the centre/south/2 win, e3 came within
26 m of its route end at about 134 s, one metre outside the 25 m arrival rule, stood 41-45 m away
from about 180 s and was released at the 360 s bound, so that battle was not a full two-regiment
test, and what stopped it is unknown. Centre
north and south release about 45 m apart at the same time; whether they are physically distinct cases
is unknown. The announced control is declared on v2 only and has no battles, and no controller that
reads the briefing has played B, so its value is unknown.

A initially reuses the native-AI route in the [base implementation plan](cannae-eval.md#implementation-using-the-current-repository).
B needs **new, bounded enemy-reserve control**. Current authored deployment releases the
enemy back to native AI; it cannot schedule these commitments. Planning B does not claim
that API, checkpoint equivalence or controlled opponent already exists. This is a proposed
exception to the initial preference for native AI, resting on Reserve mechanism above;
the owner selects it before implementation. If selected, use this sequence:

1. Add separate A/B declarations and provenance for opponent type, reserve membership,
   trigger distribution and continuation catalogue. Bind actual unit identities and keep
   the reserve ownership stable. Pin troop/loadout changes and validate both rosters.
2. Add a Lua opponent adapter confined to declared enemy units. Check controller acquisition,
   holding, actual route/attack effects, AI interference and cleanup. Never let it order
   the friendly army or write the policy mailbox. Define exactly which controls it retains
   after the event and which state it can read; do not grant accidental omniscience.
3. Add private event-draw and action/effect records with source/configuration hashes and
   reproducible audit data. Check every policy input and authorized tool path for leaks.
   A separate RNG seed reproduces selection, not the entire engine battle.
4. Check true/false/ambiguous cues, wrong identities, rejected and accepted-but-ineffective
   orders, missing public visibility, events after the ending, prevented threats and
   mismatched announcement versus actual assignment. A fast or slow model must not change
   the event distribution just by changing its reply timing.
5. Complete setup, owner-manual demonstrations and the selected adaptation evidence before
   model comparison. Freeze concrete counts, thresholds, uncertainty, failure dispositions,
   budget and stop rules through the existing agreement process. No check is agreed here.

For scenario materialization, use the [SMACv2 code reference](benchmark-references/smacv2.md#code-to-consult),
especially `wrapper.py` and `distributions.py` at the recorded pin. The WH3 adaptation must
retain every draw and failure and keep continuous 1x execution; SMACv2's reset retries and
stepped execution do not transfer. Use existing queue/manifests/reports and extend only
the event data needed for this experiment.

## Reporting and decisions still open

Report A and B as separate battles, with B's cases also visible individually. Engine wins
remain wins, including alternative tactics and timer endings. Show first-ending condition,
latency, cost and errors beside them; no new aggregate score or hidden adaptation bonus is
introduced. For any claim about changed decisions, show the public cue and action effects
alongside the relevant control and uncertainty. Repeated frames, decisions or branches
from one restored state are not independent battles.

The result can support three progressively stronger statements: the future assignment
was unavailable in advance; this controller responded to its public consequences; those
responses helped beyond the tested fixed and conditional controls on reserved cases.
Even all three would leave open whether its useful reasoning was learned, retrieved or
newly composed. They would provide concrete evidence that replaying the opening Cannae
plan was insufficient under the tested conditions.

The owner has selected the familiar-versus-improvised comparison. Remaining choices are
the reserve mechanism and concrete armies/geometry, what counts as sufficient adaptation
evidence, and the arm/resource/exposure plan. Name-only, cosmetic and difficulty-only
substitutes do not meet this direction. Start with the canonical battle and validate the
event mechanics before expanding B's combinations; this schedules neither battle.

Research basis: [SMACv2](https://arxiv.org/abs/2212.07489v2) motivates challenging a fixed
schedule; [CheckList](https://aclanthology.org/2020.acl-main.442/) motivates behavioral cases
whose consequences should change; [Procgen](https://arxiv.org/abs/1912.01588) motivates
explicit development/evaluation exposure for generated instances. These are design
adaptations, not evidence that WH3 or a particular model satisfies this plan.
