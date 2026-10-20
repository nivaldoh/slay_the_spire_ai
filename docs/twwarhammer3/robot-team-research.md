# Research for robot team control in WH3

Research reviewed through 2026-10-20. The useful connection to robotics is coordinating
units that can keep acting while a planner thinks, lose an ability, or stop supporting
another unit. The immediate priority is to establish a battle where recovering that
cooperation matters. New controller architectures and training methods come after that.

This guide connects research to possible WH3 experiments. Paper findings are described
within their tested settings; the WH3 applications are proposals. They are not agreed
verification methods or evidence of live-game improvements. The
[experiment plan](robot-team-plan.md) selects the current battle and checks; the
[controller notes](robotics.md) describe code boundaries and implementation options;
[post-training](../posttraining.md) specifies the existing data pipeline.

## Scope and possible contribution

Heterogeneous team allocation, failure recovery, hierarchical control and reasoning
under a live clock already have substantial prior work. An army is not a mechanically
connected robot body, and a centralized army controller is not decentralized merely
because it controls many units. The engine supplies movement, pathfinding and fighting.
Our research sits above those controllers.

A possible contribution is a set of small, inspectable battles where an opponent breaks
a cooperative arrangement during remote inference. The study could distinguish:
choosing the wrong replacement; failing to carry out a sensible assignment; and adopting
a late plan whose supporting conditions disappeared. To establish value, it must reveal
a consequential failure that strong simple controllers do not already resolve.

WH3 can test task dependencies that must remain true while another action runs:
"the infantry keeps the enemy occupied while the guns fire." It also makes recovery
costly: losses, spent ammunition and the opponent's progress cannot simply be undone.
These are useful hypotheses about what to study, not claims that other benchmarks lack
them. Transfer to a robot task would be needed for a physical-robot performance claim.
This reading guide is selective; it does not establish novelty through an exhaustive review.

| Question | Read first | First useful comparison |
|---|---|---|
| Which unit can take over? | [Capabilities and allocation](#capabilities-and-allocation) | Capability/distance rule versus model allocation |
| When does a failed job need another unit? | [Failure and recovery](#failure-and-recovery) | Local retry versus immediate reassignment |
| What should happen during a slow call? | [Execution and delayed plans](#execution-and-delayed-plans) | One executor with different adoption or request rules |
| Does the battle require the claimed skill? | [Evaluation that tests the intended behavior](#evaluation-that-tests-the-intended-behavior) | Fixed/scheduled behavior versus feedback |
| Which examples should a student learn from? | [Learning from recovery and feedback](#learning-from-recovery-and-feedback) | Same learner with different data collection |
| Is a larger agent team warranted? | [Scaling and communication](#scaling-and-communication) | Central allocator before independent model teammates |

## Capabilities and allocation

### EMOS and explicit capability information

[EMOS / Habitat-MAS](https://arxiv.org/html/2410.22662v2) (2024 preprint, revised 2025)
derives robot capability descriptions from structural descriptions and kinematic tools.
Its ablations support the value of numerical capability information for allocation in
that benchmark. The setup supplies navigation/manipulation skills, assumes ideal scene
reconstruction and disables physical contact simulation. This is evidence about
high-level capability reasoning, not autonomous control of the whole robot stack.

**WH3 idea:** distinguish what a unit can do, whether it is currently available, and what
job it has been assigned. A surviving unit with no ammunition is not an equivalent
replacement shooter. Test a held-out replacement roster using identical public fields.
Compare model allocation against a capability filter followed by a distance rule.
If that rule handles the relevant choices, a discussion among model agents is unnecessary.
Unit speed fields describe capabilities, not measured movement or guaranteed arrival times.

### DART-LLM and dependencies between jobs

[DART-LLM](https://arxiv.org/html/2411.09022v2) (2024 preprint, revised 2025)
constructs task dependencies and schedules independent work in parallel. Its construction
benchmark includes sequential and interdependent multi-robot tasks and ablates dependency
modeling.

**WH3 idea:** record why two assignments depend on each other, rather than keeping only
a list of unit roles. A cavalry flank may require infantry to keep an enemy occupied.
First compare assignments with and without manually declared support conditions; learning
those conditions is another comparison.

A completed prerequisite differs from continuing support. "The infantry engaged once"
cannot permanently satisfy "the flank is protected." A task graph alone does not establish
that a relationship still holds. Public melee flags also do not identify every engagement
partner, so any support predicate needs an observable definition and an unknown state.

## Failure and recovery

### Reactive allocation and the choice to retry

[Reactive Task Allocation and Planning for Quadrupedal and Wheeled Robot Teaming](https://arxiv.org/html/2110.08436v4)
(2021, revised 2022) is a useful foundational comparison. It separates local recovery,
local replanning and team reassignment through a behavior-tree execution layer.
Its formal completion claims depend on the specified task and transition model.
The authors also note that local recovery may save computation while being slower than
using a different robot.

**WH3 idea:** distinguish an ongoing movement, a blocked approach, a routing screen and
a permanently unavailable unit. Compare a bounded local retry with immediate reassignment
to a suitable available unit. Count the job abandoned by that replacement too.
The decision should depend on observed progress and the remaining opportunity, not a
universal preference for retrying. Formal guarantees from the paper do not carry over
to a battle whose opponent and movement outcomes are uncertain.

### CoMuRoS and relevant events

[CoMuRoS](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2026.1843313/full)
(published August 2026) combines a central task manager, local execution and event reports.
Its physical object-recovery experiment succeeded in 9/10 trials. The failure occurred
when the quadruped resumed before its cargo was secured: selecting a recovery action did
not establish that its prerequisite had finished. Skills and application rules are supplied;
textual allocation scores are separate from physical trials.

**WH3 idea:** distinguish "screen routed," "reserve assigned," "reserve reached the fight"
and "gun protected again." Request replanning for a consequential disruption, with a
periodic fallback, rather than every minor state change. Compare against a small
event-to-action rule table and periodic requests above the same executor.
Measure missed events, unnecessary calls and repeated reversals as well as outcomes.
An event filter that itself chooses the entire recovery must be credited with that decision.

## Execution and delayed plans

### DPT-Agent and standing behavior

[DPT-Agent](https://arxiv.org/html/2502.11882) (2025) combines a finite-state controller,
generated policy code and asynchronous reasoning in real-time Overcooked collaboration.
An authored executor converts its macro actions into movement, including pathfinding.
The results support this combination in that setting; they do not show that any slow
model paired with any fast controller will work.

**WH3 idea:** keep local behavior running while the model revises assignments or bounded
transition rules. Compare fixed rules, model-selected parameters and generated rules
separately, with the same movement helpers. Preserve a unit's progress when an unrelated
assignment changes. The existing commander is a scheduling starting point, but its skills,
prompt and error handling need the [checks already recorded](robotics.md#fit-to-the-current-codebase).
Do not add unrestricted generated Python merely to reproduce this architecture.

### Real-Time Chunking and actions already in progress

[Real-Time Chunking](https://arxiv.org/abs/2506.07339) (NeurIPS 2025) generates the next
continuous action sequence while the current one runs, conditioning on the prefix that
will execute before the new sequence arrives. It evaluates dynamic simulation tasks and
physical manipulation under inference delay.

**WH3 idea:** a planner should know which orders will remain in force while it thinks.
Compare adoption that preserves valid ongoing execution with adoption that resets it,
holding the planner and local rules fixed. A withdrawal already underway should not be
restarted merely because another unit receives a new assignment.

The paper's diffusion/flow inpainting is not a ready-made algorithm for discrete attack
targets, ability calls and conditional withdrawal. Averaging two target identities or
opposite routes is meaningless. Use its execution principle before considering its
continuous action model.

### Planfence and assumptions that have changed

[Planfence](https://arxiv.org/html/2609.03340v2) (September 2026 preprint)
distinguishes current information from the inputs a stored plan was derived from.
Its software-agent evaluation checks plans against recorded dependencies after requirements
change. The dependencies are application-supplied; the method does not discover omitted
assumptions or guarantee that conditions remain true after checking.

**WH3 idea:** check a returned assignment's declared supporting conditions at adoption.
Compare ordinary unit/target legality checks, a fixed age limit and explicit support
checks. An old plan can remain useful; a young plan can already be invalid.
For a flank, the relevant condition may concern another unit still holding the enemy.
Start with authored conditions and audit rejections even when those conditions still hold.
That establishes applicability, not the unobserved outcome of the rejected plan.
A distributed memory system is unnecessary for this first test.

### Timing variables to keep separate

| Variable | WH3 meaning | Comparison it supports |
|---|---|---|
| Observation age | How old the supplied snapshot is | Delayed sensing |
| Planner response time | Time spent awaiting a plan | Remote reasoning delay while local behavior continues |
| Adoption delay | Time between reply availability and accepting/rejecting it | Scheduler or plan-check overhead |
| Executor cadence | Time between local reactions on fresh state | Ability to respond between plans |
| Order and effect delay | Submission time, then observed movement/contact | Whether a timely decision achieves its purpose |
| Committed behavior | What continues before a replacement takes effect | Useful persistence versus obsolete execution |

These definitions guide proposed measurements; not every event is currently exported.
Today's `--delay-seconds` changes the snapshot for the whole policy. It cannot by itself
measure planner delay with fresh executor feedback. The
[live comparison plan](robot-team-plan.md#3-test-one-timing-or-adoption-mechanism)
keeps WH3 at unpaused 1x and changes one timing mechanism at a time.

## Evaluation that tests the intended behavior

### SMACv2 and simple solutions to complex-looking tasks

[SMACv2](https://arxiv.org/abs/2212.07489) (NeurIPS 2023) found that policies using
identity and timestep could achieve substantial performance on many original SMAC
scenarios. It introduces randomized teams/starts and stronger partial observability to
require feedback and generalization.

**WH3 idea:** retain fixed jobs, early reserve commitment and, if needed, a frozen
scheduled-assignment sequence from development as shortcut checks. Evaluate on reserved
supported roster or geometry variations. Establishing that feedback matters still does
not establish that cooperation matters: compare interdependent jobs with similarly sized
independent engagements.

SMACv2's [environment source](https://github.com/oxwhirl/smacv2/blob/main/smacv2/env/starcraft2/starcraft2.py)
sets `realtime=False` and explicitly advances simulation steps. Our remote inference runs
while the battle advances. This is a difference from that standard implementation, not
a claim that live-clock agent evaluation is new.

### LIBERO-Plus and whether instructions change behavior

[LIBERO-Plus](https://arxiv.org/html/2510.13626v2) (October 2025)
tests manipulation policies under controlled changes, including removed instructions and
changed target goals. Some tested policies continue pursuing familiar goals despite
different instructions. Its results concern the models and tasks evaluated.

**WH3 idea:** distinguish two tests. Consistent unit-ID renaming and list reordering should
preserve equivalent decisions. Changing to another feasible assignment should change
behavior when the task requires it. For a learned executor, compare normal assignments
with masked assignments on cases where different assignments require different actions.
Unchanged behavior could mean the executor ignores its planner or infers the task from
the usual scene.

A changed goal must remain feasible. A controller that ignores meaningful changes should
not receive credit for robustness merely because it resists irrelevant ones.

### CaP-X and who supplies the competence

[CaP-X](https://proceedings.mlr.press/v306/fu26u.html) (ICML 2026)
studies coding agents across control abstractions, interaction and perception conditions.
Across 12 models, human-designed abstractions improve success; removing them exposes
dependence on supplied behavior.

**WH3 idea:** report which component selects the role, target, movement, withdrawal timing
and plan rejection. Compare assignment methods above one executor before comparing
different executors. A model calling a complete authored repair routine has selected that
routine; it has not demonstrated all the decisions inside it.

Use a direct-orders model as deployment context, while labeling its different interface.
Giving it fewer tactical helpers and then attributing the whole outcome gap to planning
would be misleading. The [controller comparison table](robotics.md#comparisons-that-answer-different-questions)
keeps these questions separate.

### Uncertainty and the unit of evidence

[Deep RL at the Edge of the Statistical Precipice](https://arxiv.org/abs/2108.13264)
(NeurIPS 2021) shows how few runs and aggregate point estimates can give unreliable
algorithm comparisons, and develops uncertainty-aware reporting.

For WH3, show wins/scored launches, failures and exclusions for each condition before
an aggregate. A launch, a rematch, a frame, a generated program and a trained checkpoint
are different sampling units. Repeated battles with one generated controller estimate
that controller's behavior, not how reliably its generator produces good controllers.
Group correlated observations and report the number of independent artifacts.

Choose the minimum useful improvement and sampling plan before evaluation. Uncertainty
intervals do not correct selection on favorable battles, repeated tuning on test variants,
or treating natural routs as randomized interventions. A small pilot may justify a better
experiment without establishing a rate or equivalence.

## Learning from recovery and feedback

### DAgger and states reached by a failing student

[DAgger](https://proceedings.mlr.press/v15/ross11a.html) (AISTATS 2011)
collects trajectories from the learner, obtains expert actions on visited states, and
aggregates those examples for training. It addresses the difference between fitting
demonstrations and controlling the states the learner actually reaches.

**WH3 idea:** for a small recovery-action ranker, compare spending the same additional
annotation budget on ordinary demonstrations or student-visited failure states. Keep
the learner and initial data fixed, and count student launches and demonstrator effort.

The demonstrator must be competent in those states. A stateful witness that works from
its own opening cannot automatically label an arbitrary snapshot; it may need history and
phase state. Offline action agreement is a screening measure. Live outcomes decide whether
the new examples teach useful recovery.

### RaC and restoring a useful arrangement

[RaC: Robot Learning for Long-Horizon Tasks by Scaling Recovery and Correction](https://arxiv.org/html/2509.07953v1)
(September 2025 preprint) changes data collection while retaining imitation learning:
interventions first return the robot to a familiar state and then demonstrate the desired
subtask. It compares recovery/correction data with other demonstrations on physical
bimanual tasks and simulated assembly.

**WH3 idea:** compare direct correction with first restoring a defensible arrangement.
An exposed gun might withdraw behind surviving infantry before resuming its job.
Compare the same learner with demonstrations only, direct corrections and
re-form-then-correct examples under matched collection budgets.

The opponent keeps moving, and casualties, ammunition and morale cannot be rewound.
Restoring the old arrangement may be impossible or waste the remaining opportunity.
Include abandoning or reallocating the job as valid alternatives. Reward the objective,
not the number of retries or apparent recoveries.

### RECAP and learning from outcomes

[RECAP / pi-star-0.6](https://arxiv.org/html/2511.14759v1)
(November 2025 preprint) combines demonstrations, autonomous rollouts and expert
interventions. It trains a value model and conditions policy learning on estimated
advantage: whether an action appears better than the usual continuation. Its manipulation
results use substantial task data; its value estimation is described as on-policy/Monte
Carlo even though policy extraction uses mixed old/new data.

**WH3 idea:** once suitable data exist, compare ordinary imitation, episode-success
filtering and outcome-conditioned or value-weighted action selection on the same data.
A winning battle can contain a poor replacement; a losing battle can contain a successful
handover. A learned value estimate does not automatically identify which action caused
the outcome.

Do not infer sufficient data from the existing 29 Empire model episodes. Sparse outcomes,
hidden enemies and changing elapsed time complicate learning. Faster completion is also
not always desirable: holding an enemy in place can be the assignment's purpose.

### TORSI and learning between battles

[The World Won't Wait / TORSI](https://arxiv.org/html/2610.20665)
(October 2026 preprint) evaluates agents under a live clock and separates slow teaching
from fast acting. A teacher revises reusable guidance between attempts; frozen candidates
are selected on validation tasks and evaluated on held-out tasks. The student makes no
teacher calls during gameplay. This is instruction improvement, not weight fine-tuning.

**WH3 idea:** refine the existing review loop with explicit feedback, selection and final
evaluation groups. Compare frozen revised guidance against the previous guidance under
the same development budget. Count rejected revisions and their cost.

The paper's teacher practices alternatives from saved states with paused or slowed games.
Our WH3 rule forbids that, and a trace is not a branchable simulator. Borrow the separation
of learning and deployment; test proposed alternatives through permitted fresh live runs.

### Delay-aware examples and the current export

[Training-Time Action Conditioning](https://arxiv.org/html/2512.05964v2)
(2025 preprint) trains continuous-action policies with a committed action prefix and
sampled inference delay, evaluating simulation and physical manipulation.
For WH3, the transferable data idea is to preserve what happened while a plan was pending.
Simply shifting an action label onto an older snapshot can omit intervening orders.
Training on one delay range also does not establish behavior under longer stalls.

Before building a recovery dataset, specify the following meanings in its contract:

- Permitted observation/history, active assignments and the component choosing the action.
- Proposed action, order actually submitted, acknowledgement, and later observed effect.
- Elapsed battle time, pending plan identity and intervening actions.
- Terminal outcome, failure type, and the definition and source of any intermediate reward.
- Whether a label came from a teacher, a human correction, a script or an autonomous student.
- Whole-launch/family split, including retries, related variants and generated artifacts.

This is a proposed dataset, not the existing model-request export. In particular,
acknowledgements are not achieved effects, a next snapshot may contain several units'
actions, and losing sight of an enemy is not evidence of damage or death.
Missing behavior token probabilities rule out corrections requiring those probabilities;
they do not rule out every offline learning method. For example,
[Implicit Q-Learning](https://arxiv.org/html/2110.06169v1) (2021) fits values from recorded
transitions and extracts a policy through advantage-weighted imitation, without requiring
the behavior policy's saved action probabilities. This does not establish that our
partially observed, variable-duration order traces meet its assumptions. The
[post-training contract and gaps](../posttraining.md#beyond-supervised-fine-tuning)
remain the implementation reference. A dense exporter needs a specified learner first.

## Scaling and communication

[DynaHMRC](https://arxiv.org/html/2606.14882v1) (June 2026 preprint)
studies heterogeneous agents under changed objectives, inaccessible regions, added
teammates and removed teammates, alongside domain fine-tuning. Its step-based measures
and physical execution windows do not establish an advantage under our live inference
clock.

Borrow its separation of disturbances: temporary routing, permanent destruction, rallying,
and movement failure should be different cases. Compare a central planner with concise
structured state before adding per-unit model agents. Hold information, local skills and
total model resources fixed where the comparison requires it. Longer history can preserve
obsolete assignments as well as useful context.

[Decentralized MRTA Under Degraded Communication](https://arxiv.org/html/2609.13711v1)
(September 2026 preprint) compares classical allocators under message loss and measures
allocation stability, duplicate effort and computation. Its measured computation does
**not** advance simulation time or alter event ordering. It therefore cannot substitute
for a live-latency study.

If decentralized communication later becomes the question, distinguish missing teammate
messages from slow central planning. Measure duplicate assignments, abandoned jobs,
messages and end-to-end effects. Our current centralized public-state interface does not
establish those communication conditions. One language model per unit adds calls without
creating a useful experiment by itself.

## Which ideas to use first

| Priority | Concrete use | Reason to defer the next layer |
|---|---|---|
| First | Establish a recoverable Empire situation; compare fixed jobs, early commitment and replacement | The rank-5 fixed plan already won one battle without its reserve fighting |
| Then | Separate allocation from local execution; add a capability/distance baseline | A simple rule may explain the whole benefit |
| If delayed replies cause harm | Compare legality, age and support-condition checks with one planner | An old reply is not necessarily a bad reply |
| If a repeatable decision remains difficult | Collect student failures and compare small learners on matched data | Existing model-request rows are not a recovery training set |
| Later | Try communication, larger teams or a second robotics domain | More agents or units alone do not establish generality |

Keep each experiment small enough to explain what changed and why its baseline is a
serious alternative. A failed transfer or a simple rule that wins is useful evidence.
Neither justifies relabeling a game-specific result as general robot intelligence.
