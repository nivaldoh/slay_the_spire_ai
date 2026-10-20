# Robot team research plan

Updated 2026-10-20. **Can a controller keep an army working when one unit can no longer
perform the job that other units depend on?** The first candidate is the Empire line
battle. The next decision is whether it actually requires recovery, before adding a new
controller or training a model.

The [research guide](robot-team-research.md) explains the relevant work, what it establishes
and which comparisons it suggests. The [controller notes](robotics.md) hold implementation
options and constraints. The [Empire set](empire.md) holds the battle records.
The comparisons and checks here are proposals, not agreed verification methods;
gameplay findings remain unverified under the [repository rule](../../AGENTS.md#verification-hard-rule).

## What might make this interesting

The engine already handles each unit's movement, pathfinding and individual fighting.
Our controller chooses how units support one another: an infantry unit holds an enemy
while guns fire or cavalry moves elsewhere. When that infantry routes, a healthy
teammate's assignment can stop making sense.

This is a problem of team allocation and execution above local controllers. Units have
no mechanical connections, and a single central planner is not a decentralized robot
system. The possible research contribution is an inspectable set of situations where
cooperation breaks while a remote controller is thinking and existing orders continue.
Neither team recovery nor slow planning over fast execution is new; see the
[research comparisons](robot-team-research.md#scope-and-possible-contribution).

Three questions should be answered separately:

1. **Allocation:** who should take over, and when is abandoning the original plan better?
2. **Execution:** can the chosen unit actually reach and perform the replacement job?
3. **Plan adoption:** does a reply based on the old arrangement undo a useful recovery?

A win alone cannot distinguish these. A stronger robotics claim would also require the
same useful mechanism to work in a robot-team task, such as delivery with one carrier
unavailable. WH3 alone establishes results about this game and interface.

## The current Empire candidate

The current candidate is `emp-line-grn-raid-xp5`, the rank-5 variation of
`emp-line-grn-raid`, on Taurox; adopting rank 5 remains an owner decision.
Both are already declared in [scenarios.json](../../configs/twwarhammer3/scenarios.json).
Both sides are lordless; the player defends and the battle runs unpaused at 1x.
Keep declared settings fixed within a comparison.

| Side | Roster | Possible cooperation |
|---|---|---|
| Empire | Halberdiers, two Swordsmen, reserve Spearmen, two Handgunners, Empire Knights | Infantry holds the line, guns fire, the reserve repairs a gap and knights respond to a threat |
| Greenskins | Two Orc Boyz, Big 'Uns, Goblin Spearmen, Arrer Boyz, Wolf Riders, Boar Boyz | The game AI chooses its own attacks |

The scene to look for: a line unit protects a gun while the reserve is available.
The line unit routes during a planner request. Before the reply returns, the enemy
approaches the gun. Can the controller fill the gap, move the gun, or give up that
position? Does a late reply send the reserve away or cancel the withdrawal?
This is a candidate sequence, not an established recurring event.

### What the existing launches establish

The [Empire results](empire.md#results) contain feasibility evidence:

- At rank 0, `LineTeam` and `LineTeamReserve` each lost two launches.
- At rank 5, the fixed `LineTeam` won its one launch; **its reserve never entered melee**.
  `LineTeamReserve` lost its one launch after six enemy units had routed.
- At rank 5, GLM won its one launch and Kimi lost its one; the two simple floors each
  lost one. These are individual outcomes, not reliable differences between controllers.
- The b46 changes to target retention and knight behavior are unplayed. Earlier results
  do not establish the behavior of those revised controllers.

The fixed-plan win is a reason to test whether recovery matters. A battle can be a useful
coordination card even if it is a poor recovery card. Do not harden it until every model
loses or count a reserve order as a successful handover.

## What to compare

First establish that a useful allocation choice exists. Use one shared local executor,
the same public fields, update schedule, opening arrangement and supplied tactical
knowledge. These are proposed experimental arms; today's two `LineTeam` classes are
starting points, not a completed common-executor comparison.

| Arm | Assignment decision | What it tests |
|---|---|---|
| Fixed jobs | Retain opening roles, with ordinary local checks for unavailable targets | Whether replanning is needed at all |
| Commit the reserve early | Put the reserve into a declared useful job before a break | Whether waiting for a handover is an unnecessary restriction |
| Simple replacement | On a line unit's rout, send an available reserve toward the gap | Whether one authored rule is sufficient |
| Capability and distance rule | Select among legal replacements using declared capability constraints and distance, with a penalty for abandoning another job | Whether a small allocator handles the meaningful choices |
| Model assignments | Choose replacement, redirection or abandonment above the same executor | Whether model decisions add value beyond those rules |

Add the capability rule only if there is more than one consequential choice. Distance
is a rough travel proxy, not a promise of reachability or an accurate arrival time.
Disclose every tactical rule supplied to the executor and allocator.
`hold` and nearest-attack remain context, but are too weak to establish a planning benefit.

If a hierarchy is useful, run a separate adoption comparison with the **same planner**:
ordinary legality checks; legality plus a fixed age limit; legality plus explicit
conditions for the assignment to remain useful. For example, "continue this flank while
the supporting infantry is still holding" is different from "the target is alive."
Keep unchanged assignments and their progress when patching a plan.

The conditions themselves are supplied behavior. Start with authored conditions and say
so; having the model select them is a later experiment. Excessive rejection can be worse
than accepting an imperfect plan. Count rejected plans whose declared conditions still
held, and independently review applicability with an unknown category. Their unobserved
battle outcome remains unknown. Also measure delayed recovery and obsolete orders adopted.
Define the response to false or unknown support before comparison: retain a still-valid
assignment, use a declared local fallback, or request replanning. Unknown must not
silently count as false.

## What we would observe

Keep the engine outcome and ending type. For this card, a **contact win** means the
enemy is routed or destroyed before the timer; report defender timer wins separately.
For each relevant disruption, record the sequence below on the battle clock.

| Event | Evidence and limit |
|---|---|
| Support becomes unavailable | Public routing, destruction or loss of progress, with the rule stated in advance; these events are not interchangeable |
| Controller observes it | Snapshot sequence/time and which component received it |
| Planner requests or returns a change | Source snapshot, request/return/adoption times, assignment identity and rejection reason |
| Replacement order is submitted | Acknowledgement and order origin; this establishes submission, not the effect |
| Protection is restored or abandoned | Reviewed movement/contact and the protected unit's behavior; define the observable criterion before scoring |
| Whole battle ends | Contact win, timer win, loss, draw or classified failure, under the frozen outcome rule |

Before automating handover scoring, agree examples of success, failure and ambiguity:
an order that arrives too late, a replacement that never reaches the fight, an unnecessary
handover, and a purposeful retreat. Public melee flags alone do not identify the opponent
being fought. The 1 Hz replay cannot resolve subsecond timing; retain an unknown category
when the evidence cannot decide.

Measure planner request time, observation age at adoption, local update intervals and
observed effect separately, including failed and unfinished calls. The current
`--delay-seconds` ages the entire policy's snapshot; a planner-only delay with fresh local
feedback requires a separate implementation. No paused or slowed WH3 condition is allowed.

Score every assigned launch, including battles with no rout. Natural routing depends on
earlier decisions, so selecting only episodes where a unit routed does not isolate
recovery. Replays can identify failure sequences; they cannot reveal the outcome of an
untried alternative. Controlled mid-battle removal or a restored battle checkpoint is
not an established experimental capability.

## A small sequence of experiments

These are gates, not a large suite to run at once. Choose counts, budgets, a stopping rule
and a minimum useful improvement with the owner before any live comparison.

### 1 Establish a recoverable coordination problem

Review the recorded line battles for occasions where a replacement could plausibly matter.
Then propose a small script-only screen using the revised fixed, early-commitment and
replacement arms. Three fresh launches per arm would be a feasibility screen, not a
reliable rate comparison. Record starting geometry and the commander flag.

Proceed only if there are recoverable disruptions and more than a cosmetic change of
target. If fixed jobs or early commitment consistently solve the development cases
without recovery, retain the battle as a coordination example and choose another recovery
candidate. If every break causes an unavoidable morale collapse, revise the setup or stop.

### 2 Test one allocation change

Freeze the shared executor and the best relevant simple rules, then compare model
assignments. Explain the tactic to all model arms: this study concerns allocation and
recovery, not recalling an undisclosed game tactic.

Reserve a legal roster or geometry variation before tuning. A stronger reserve's extra
wins alone do not show adaptation; compare controllers within each variation. Randomize
controller order across fresh launches, report all starts, and keep rematches grouped
with their launch. Reserve development, selection and final evaluation groups.

### 3 Test one timing or adoption mechanism

Only after a useful assignment comparison exists, change one of:
planner delay; plan adoption checks; or event-triggered versus periodic replanning.
Keep the executor's observation interface and update cadence fixed, using each arm's
current battle state. The planner's model and configuration stay fixed; its replies can
differ as battles diverge. Begin with natural latency and a declared fixed added delay;
add variable delay or stalls only when the question needs them. Delays must be assigned
independently of observed battle difficulty.

Check the implementation on a short known event sequence first. A deliberately wrong
"accept every legal plan" implementation should fail a contract requiring rejection after
the support unit routes. This establishes the adoption contract, not a benefit in battle.
Then measure whether the changed mechanism improves outcomes or recovery without simply
rejecting everything.

### 4 Learn only the remaining decision

If failures cluster around a bounded choice, such as retain assignment, replace support
or withdraw, first try a small classifier/ranker or bounded correction to a reference.
The [learning section](robot-team-research.md#learning-from-recovery-and-feedback)
compares demonstrations, recovery labels, offline guidance and reward-conditioned learning.

Compare with the unchanged script, a simple written correction and imitation on the same
data. Count demonstrator effort and all development battles. Whole held-out launches and
variants decide whether learning helps; action agreement and lower loss are screening
checks. Do not begin large online RL before a serving route, useful reward and affordable
interaction budget exist.

## The earlier Skaven candidate

`skv-ogres-slaves-emp-halberds-1` has one Rat Ogres unit and two Skavenslaves against
Halberdiers and Handgunners. Its proposed handover is simple: one slave unit holds the
halberds while the ogres reach the guns, then the reserve replaces the routing screen.
It remains deferred in favor of Empire data.

The [earlier pilot](log.md#2026-10-18-tactic-cards-harness-b28-to-b30-and-the-overnight-checks)
recorded `SlaveTarpit` winning 3/4, and hold and nearest-attack each losing one.
`SlaveTarpit` sends both slave units together; those wins do not demonstrate a useful
reserve. The ogres might also bypass the halberds without any screen. If this candidate
returns, compare those simpler choices before developing a handover controller.

## Main risks and reasons to change course

- **The game can win without the proposed skill.** Test the shortcut before claiming a
  recovery benchmark; the rank-5 fixed-plan win already warns about this.
- **Morale or movement can dominate.** Lordless armies still receive a commander flag.
  A rout cascade or blocked path can overwhelm an otherwise sensible assignment.
  Scripts and rendered model prompts currently expose different commander information;
  match their inputs before comparing.
- **A monitor can supply the solution.** A rule that chooses the replacement, its route
  and its timing already performs much of the task. Attribute decisions to the component
  that actually made them.
- **More units do not establish more coordination.** Compare interdependent jobs with
  similarly sized independent fights before interpreting team-size effects. Defer
  per-unit language agents until communication itself is a question.
- **The baseline may solve the task.** Keep that result. Do not add complications solely
  to make a model necessary.
- **A narrow game result may be all we obtain.** Broader claims need another task family
  and eventually a robot-team setting where the same mechanism can be tested.

The immediate next step is the Empire feasibility review in gate 1. The
[Empire owner decisions](empire.md#for-the-owner-to-decide) remain pending; this research
update does not admit a card, authorize a new run plan or change benchmark priorities.
