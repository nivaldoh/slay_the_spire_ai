# Robotics ideas for WH3 control and evaluation

Research notes, updated 2026-10-20. A useful starting point is a local controller that keeps
reacting while a slower planner chooses its assignments. Compare their contributions
separately. Try fixed control rules and model-selected parameters before generating new
rules or learning movement.

The [research guide](robot-team-research.md) connects capability allocation, recovery,
delayed plans, evaluation and learning to published work and recent preprints. The
[robot team plan](robot-team-plan.md) turns those ideas into a staged Empire experiment:
first establish whether replacing a broken line unit helps. This page keeps the
controller designs and code boundaries.

These are proposals, not implementation or agreed verification methods. WH3 performance
claims remain unverified under [the repository rule](../../AGENTS.md#verification-hard-rule).
This extends the [latency program](latency.md) and
[controller candidates](controllers.md#designs-not-built-yet), without changing their priorities.

## What the robot analogy explains

The army resembles a team of mobile modules with their own controllers. The engine already
handles pathfinding, formation movement and individual combat. Movement and attack orders
persist; abilities are one-shot, and some commands address the army. Control is above the
level of motor torques or individual soldiers' movements. Position, orientation,
melee state and order history matter; so do other units, morale and an adversary that reacts.

| Robotics concept | Useful WH3 interpretation | Limit of the analogy |
|---|---|---|
| Hierarchical control | Planner assigns roles and targets; executor manages engagement and disengagement | A good executor can supply the entire tactic being tested |
| Delayed feedback | The battle changes between observing, deciding and issuing an order | Issuing an order does not establish when its effect starts |
| Changing team capabilities | Units die, rout, rally or join; capabilities and available roles change | Units have no fixed mechanical connections, and routing can reverse |
| Partial observability | Public state plus memory of previously visible enemies | No access to hidden enemy state or evaluator data |
| Hybrid actions | Select attack/move/ability and a target, with continuous positions and bearings | Continuous trajectory methods cannot simply interpolate command types or target IDs |

These correspondences follow the [observation contract](../../src/twwarhammer3/engine/mailbox.py)
and [engine facts](integration.md#battle). A useful robotics benchmark need not add cameras:
the current structured-state interface already isolates several control problems. Screenshot
input would create a separate perception and information-boundary experiment.

The latest [b40 round](log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40) gives a reason
to investigate execution. The revised scripted chariot controller won 4/5 battles at
5 s added observation age / 5 s decision interval, and 4/5 at 8 s / 8 s. GLM-5.3 low with
the corrected prompt won 0/10 at younger information ages. These small, unverified samples
weaken a latency-only explanation. Withdrawal geometry and repeated changes of orders are
hypotheses suggested by the traces; their causal effects have not been isolated.

## 1 Compare parameter selection with generated feedback rules

[Code as Policies](https://code-as-policies.github.io/) generates programs that connect
perception outputs to existing control primitives, including geometry and feedback loops.
The transferable idea is to express a reusable decision rule once, then evaluate it on
fresh state without another model call for every action. The paper does not establish that
generated programs are reliable outside their tested tasks and APIs.

For WH3, a model could specify a small state machine for an assigned unit: approach,
engage, disengage, regroup. Transitions would depend on observable state rather than a
fixed list of commands. The model would choose the conditions and parameters; a local
runner would evaluate them. This is more expressive than choosing an existing `charge`
skill, and less costly to explore than training a new motor policy.

The [concrete boundary](#concrete-controller-boundary) limits rules to public observations,
bounded memory and ordinary validated orders, with explicit replacement and failure behavior.

An essential baseline is the same state machine with **fixed transition logic and
model-selected parameters**: target choice, retreat distance or a re-engagement threshold.
This exposes less freedom and makes failures easier to locate. Robotics already studies
optimizing parameters inside an existing controller; for example,
[automatic LQR tuning](https://arxiv.org/abs/1605.01950) uses Bayesian optimization over
controller parameters. WH3 does not have that linear dynamics model. The transferable idea
is a small search space, including a non-language-model baseline such as bounded parameter
search on development battles. Count those battles as tuning cost.

Freeze a candidate before evaluation. Preparation uses only the declared scenario brief
and development evidence; generation using the first live observation belongs on the live
clock. Online revision is another condition. If the study rules out a benefit large enough
to justify generated logic, prefer the smaller interface for this task. An inconclusive
pilot is only a reason to defer complexity, not evidence of equivalence. In either case,
parameter selection does not establish that the model discovered the authored tactic.

**What would make this useful:** a generated policy beats direct model orders with the same
information and primitive actions, or approaches the disclosed witness on unseen starts.
The [behavior checks](#what-to-establish-before-a-live-comparison) can reject broken rules
cheaply; later game outcomes decide whether they help.

**Main risk:** a helper named `cycle_charge` can conceal the entire solution. A model that
calls it has selected a tactic, not implemented its timing. Keep authored tactical helpers
separate from neutral geometry and command helpers when describing the controller.

## 2 Make the planner and executor independently replaceable

Figure's [Helix description](https://www.figure.ai/news/helix) reports a slower semantic
module above a fast motor policy, with a training offset matching their deployment latency
gap. [GR00T N1](https://arxiv.org/abs/2503.14734) also separates vision-language processing
and action generation, but its modules are jointly trained. These support a division of
labor; they do not show that attaching an arbitrary small model to a large one produces
competent control.

WH3 already has this scheduling structure in
[`CommanderPolicy`](../../src/twwarhammer3/battle/commander.py): a model request runs while
[`Skills`](../../src/twwarhammer3/battle/skills.py) reacts to observations. The research
question is the division of responsibility and quality of each component.

The planner handles allocation across the army; the executor handles reactions within an
assignment and reports failed progress. The boundary below makes that division explicit.

The current commander needs care as an experimental baseline. Its `charge` skill waits
for an enemy already in melee and does not cycle out; a lone chariot can wait without an
initiating engagement. Its [prompt](../../configs/twwarhammer3/commander_prompt.md) also
discourages withdrawal. Testing it unchanged would mix the hierarchy question with those
specific tactical choices.

[CaP-X](https://proceedings.mlr.press/v306/fu26u.html), an ICML 2026 robotics benchmark,
explicitly studies this attribution problem: across 12 models, human-designed abstractions
affect success. The [comparisons below](#comparisons-that-answer-different-questions)
separate supplied behavior from model choices.

Record who chose the tactic, target and reaction timing. A chariot card can measure
execution, but if the executor already knows cycle charging, a win says little about
planning. Add a later task where targets compete or the tactic must change. A fixed-plan
baseline should fail for a stated reason before calling that task a planning test.
Also compare the fields each component actually receives: a sanitized observation and a
rendered model prompt need not expose the same information. The
[design rules](tactic-cards.md#design-rules-from-s1-s11) already
flags the commander field available to scripted controllers but absent from model inputs.

## 3 Treat stale plans and action commitment as control problems

[Real-Time Chunking](https://www.pi.website/research/real_time_chunking) predicts the next
robot action sequence while the previous one executes, conditioning on actions committed
during inference. Its diffusion/flow inpainting algorithm is specific to continuous action
chunks. The useful WH3 principle is **account for what happened while thinking**.

A returned plan can be legal and already obsolete: its target still exists, but the ally
that was supposed to pin it has routed. The current commander rechecks units, targets and
abilities when adopting a plan; it has no general tactical preconditions or plan expiry.
Candidate improvements are completion and abandonment conditions, an age limit appropriate
to the assignment, and a check against current state before replacement. Avoid a universal
rule that old plans are bad: a long flank can remain useful while a newer plan is mistaken.

Keep short sequences for stable movement segments, and use feedback at engagement
boundaries. The current [queue contract](../../src/twwarhammer3/protocol.py) supports moves
followed by moves and a final attack. It cannot express a timed attack followed by a
conditional withdrawal. An acknowledgement means submission, and `command_queue` records
the requested sequence, not its progress. Measure subsequent movement and contact before
calling an action executed. Averaging two attack targets or two routes around opposite
sides of an obstacle has no justified meaning here.

Event-triggered replanning also fits: request a new plan when an assignment fails, a role
loses its unit, or an objective changes, with a periodic fallback. Compare against periodic
planning using the same executor. The risk is oscillation: noisy state changes repeatedly
trigger new plans or cancel useful motion. Measure abandoned plans and repeated order
changes as well as calls saved and wins.

The benchmark should distinguish observation age, decision interval and response latency.
First vary one at a time; then test variable delays and occasional long stalls. For a
hierarchy, planner delay and executor delay are different interventions. Today's
`--delay-seconds` delays the snapshot given to the whole policy, including its executor;
it cannot isolate a slow planner with fresh local feedback. Report achieved timings,
including failed calls, rather than assuming a requested update rate was maintained.

## 4 Learn micro control only where the action problem warrants it

VLA, diffusion and hierarchy name different choices: inputs and outputs, an action
distribution, and an execution architecture. They can be combined, but none requires the
others. For the current benchmark, the natural student is a small **structured-state
policy** conditioned on an assignment and recent history.

Two relevant precedents are [ACT](https://tonyzhaozh.github.io/aloha/), which predicts
action sequences using a transformer and conditional latent variable, and
[Diffusion Policy](https://diffusion-policy.cs.columbia.edu/), which learns multimodal
action distributions and uses receding-horizon execution. Diffusion Policy includes
state-based experiments; images are not a requirement of diffusion itself. Neither
paper's manipulation results establish a suitable WH3 data volume or inference speed.

| Candidate | Reason to try it | Reason to stop or defer |
|---|---|---|
| Small classifier or candidate ranker | Learn when to engage, retreat, retarget or preserve an order | Candidate construction can supply the tactics; it must be disclosed |
| Recurrent policy or short sequence predictor | Use contact history and coordinate several related decisions | A long predicted sequence can become stale before execution |
| Diffusion or flow action head | Represent several viable continuous retreat paths or formation placements | Discrete command/target selection still needs a suitable representation; sampling adds computation |

Begin with the classifier/ranker and a scripted reference on the same inputs. If the
remaining failure is choosing among distinct continuous routes, compare a generative action
head with a simple alternative using the same demonstrations and deployment hardware.
For example, averaging two valid retreat directions may point back into the enemy; a
multimodal distribution could help, but selecting among explicit route candidates may be
enough. No assumption that diffusion is faster, more data-efficient, or necessary is justified.

A narrower learned alternative is **correcting a reference controller**.
[Residual Reinforcement Learning](https://arxiv.org/abs/1812.03201) adds a learned control
signal to a conventional robot controller. WH3 commands cannot generally be added together;
instead, a small policy could adjust an allowed retreat parameter or choose among declared
recovery actions when the reference stops making progress. Compare it with the unchanged
reference and a simple hand-written correction. This may narrow the data problem, but it
inherits the reference's tactic and can still make it worse. A zero correction must reproduce
the reference. Start with supervised corrections if suitable labels exist; the robotics
paper does not establish that live WH3 reinforcement learning would be affordable.

Successful witness trajectories are a starting point, not complete training data. A student
will encounter states the witness avoided. [DAgger](https://proceedings.mlr.press/v15/ross11a.html)
addresses this distribution shift by iteratively obtaining expert actions on states visited
by the learner. A bounded WH3 analogue would collect a small set of student failures and
obtain recovery actions from a demonstrator that can handle those states. A stateful witness
needs the relevant history; querying it on an isolated snapshot may give a meaningless label.

[Training-time RTC](https://arxiv.org/html/2512.05964v2) samples inference delays and
conditions on committed action prefixes. For WH3, preserve observation times, intervening
orders, plan age and observed effects when constructing examples. Simply shifting action
labels against older snapshots can mislabel a state after another action has changed it.
The training delay range must suit deployment; success at short delays does not establish
recovery from long stalls outside that range.
Training and evaluation must also separate whole launches and reserved scenario variants;
random adjacent-frame splits leak nearly identical situations.

The current [export](traces.md) records model decisions, not a ready-made dense witness
dataset. A learned executor needs a data and serving route before this becomes an experiment.
Offline imitation accuracy can reject a bad candidate cheaply, but it cannot establish
closed-loop wins. Do not optimize the number of cycles as if it were the objective: repeated
ineffective disengagements could increase that count while losing the battle.
The current [`cycles` metric](../../src/twwarhammer3/battle/cards.py) associates accepted
move acknowledgements with melee spans; it does not check the achieved separation. It is
therefore not an independent oracle for successful withdrawal.

## 5 Test adaptation to a changing army

[Shared Modular Policies](https://arxiv.org/abs/2007.04976) shares a policy across actuators
and passes messages along physical connections, demonstrating transfer across planar robot
morphologies. The analogous WH3 hypothesis is a shared unit policy conditioned on capabilities,
role, nearby allies and visible threats, operating on a variable-size set or interaction graph.
It is not evidence that army attrition can be handled by importing a robot skeleton.

This offers a concrete benchmark direction: **can a controller preserve the plan's purpose
when the unit allocation stops working?** A screening unit routes, the intended flanker is
unavailable, or a new unit becomes available. Compare a controller that reallocates roles
with one that keeps its original assignments, and inspect recovery time and the engine result.
First establish that the changed situation remains winnable by a disclosed reference.

Natural casualties are affected by earlier decisions, so post hoc comparisons of battles
with and without a lost unit do not isolate adaptation. Begin with declared roster variants
where setup supports them. A controlled mid-battle loss or reinforcement would require a
separate, validated scenario mechanism; it is not an existing experimental control. Test
recoverable routing separately from permanent destruction.

Before training a graph network, compare a simple shared policy with access to nearby
allies and a central role allocator. Independent unit policies can all chase the same enemy,
block each other's retreat or spend the same resource. Mechanical modularity is a useful
representation idea, not a reason to launch one language model per unit.
Nor should adaptation mean preserving every unit: sacrificing an expendable screen may
serve the objective. Score recovery against the task, not a generic survival reward.

## 6 Ground plans in observable progress and test genuine generalization

[SayCan](https://say-can.github.io/) combines a language model's assessment of useful skills
with learned estimates of whether those skills can succeed. Its lesson for WH3 is to
separate **legal**, **currently feasible**, and **tactically worthwhile**. An accepted move
can fail to clear melee; an accepted cast does not establish damage; being within range
does not establish an effective firing lane.

Start with explicit progress feedback rather than invented success probabilities. A local
executor could report an attempted withdrawal that has not gained separation, a target
that disappeared, or a shooter that has not fired. Completion conditions need to be tested
against independent examples, including accepted orders that did not achieve their purpose.
Such feedback could improve either a planner or a learned controller without exposing
hidden state. The coarse terrain grid cannot certify a collision-free route, and unit speed
capabilities are not measured velocities.

[LIBERO-Plus](https://sylvestf.github.io/LIBERO-plus/) evaluates controlled changes in robot
tasks and includes blank-instruction and changed-goal tests. Borrow the experimental logic:
a controller should respond when the goal changes and remain stable when irrelevant encoding
details change.

Useful additions to the existing [tactic cards](tactic-cards.md):

| Test | Specific question | Caveat |
|---|---|---|
| Consistently rename unit IDs and reorder lists | Does behavior depend on arbitrary serialization? | Undo renaming before comparison; allow equivalent tied choices and sampling variation. This checks consistency, not wins |
| Change the assigned target or role while holding state fixed | Does a learned executor actually use the planner's assignment? | Use cases where the alternatives are feasible and should require different actions |
| Reserve another map or supported start arrangement | Does the tactic survive changed geometry? | Validate reachability and reference wins; a new map may change the task itself |
| Reserve a roster composition or capability change | Can roles transfer across units and team sizes? | Recalibrate difficulty; an impossible matchup measures little |
| Introduce a long planner delay during an engagement | Can local execution continue and reject an obsolete return? | Preserve the same public-state boundary; separate it from delayed sensing |

Keep one variant that would break the suspected shortcut, and add another only after
learning something from it. Wins at natural latency remain primary; acting quickly or
producing many orders while losing is not progress.

## Concrete controller boundary

Use the existing controller shape: `decide(public_observation) -> orders`,
`acknowledge(ack, latency)` and `metadata()`, with a fresh object for each episode.
Keep execution logic in `twwarhammer3/battle/`; neither a second game-neutral framework nor
a new Lua command is needed to express rules over today's observations and orders.

A proposed cycle-charge assignment could mean the following. These fields describe a
design, **not the current commander schema**; adoption and lifetime conditions vary by task:

| Part | Concrete meaning |
|---|---|
| Identity | Unit `f1`, target `e1`, assignment revision, source observation sequence and battle time |
| Behavior | A fixed cycle-charge executor, a frozen generated program, or a learned executor, identified by version/hash |
| Parameters | Retreat geometry and re-engagement thresholds within declared ranges; ranges are part of the authored controller |
| Adoption conditions | The unit is present and not routing; the target is currently visible and not routing; any required supporting role still exists |
| Lifetime | Observable completion/abandonment conditions and an expiry time on the battle clock |
| Replacement | Explicit patch or replacement; whether to retain the active phase and timers |

For example, the executor has observed contact and issued a withdrawal while a new planner
request is pending. An unrelated assignment update must not reset that unit's disengagement
timer. If the late reply orders another attack but its required supporting unit has routed,
reject that assignment and record why. Retain the still-valid withdrawal assignment. This
distinguishes plan validation from order legality, and can be checked on a short event sequence.
Whether continuing the withdrawal wins requires a live comparison.

Choose replacement semantics before adding concurrency: adopt changes between executor
steps, with one owner for each unit's movement and a central owner for shared resources.
A rejected replacement should leave the previous valid assignment intact. If that assignment
also becomes invalid or expires, use a declared fallback. `[]` means **no new orders**;
existing movement or combat continues. Stopping needs an explicit `halt`, which itself may
be tactically wrong. Startup defaults and failure fallback are part of each tested controller.

For generated rules, first use finite states, allowlisted predicates and bounded arithmetic
over public fields, plus a bounded amount of episode memory. Evaluate at most a declared
number of transitions per observation. The existing outside-controller loader runs Python
in process; it is not a sandbox for generated code. Unrestricted Python synthesis would need
a different execution boundary and is not the cheap first experiment.

## Fit to the current codebase

| Existing location | Smallest relevant change, if an experiment is chosen |
|---|---|
| [controllers.py](../../src/twwarhammer3/battle/controllers.py) | Construct a candidate and record its configuration. Outside classes already work, but take no constructor arguments; artifact/config selection needs an explicit route rather than hidden mutable globals |
| [skills.py](../../src/twwarhammer3/battle/skills.py) | A fixed state machine or bounded rule runner can own assignments and phase memory here or in one focused sibling module. Keep existing tactical rules distinct from shared command bookkeeping |
| [commander.py](../../src/twwarhammer3/battle/commander.py) | Reuse the one-request-in-flight pattern; add only the assignment fields and adoption semantics the chosen comparison needs. Keep prompt/schema changes versioned |
| [play.py](../../src/twwarhammer3/battle/play.py) and [protocol.py](../../src/twwarhammer3/protocol.py) | Preserve public-state filtering, validation, acknowledgement and game ownership. Controllers return orders through this path; they do not read bridge files or send commands themselves |
| [export.py](../../src/twwarhammer3/battle/export.py) | A micro-training dataset needs new row semantics. Today's exporter includes built-in model requests, excludes external/scripted policies, and does not export every executor step |

The scheduler places a real bound on reactivity: `decide` runs after the outstanding batch
is acknowledged and the configured interval has elapsed. A fast Python function does not
create an independent high-frequency control loop. Likewise, the existing commander raises
a completed worker's error before running skills on that callback. Previous engine orders
continue, but that local reaction is missed. Preserving local execution through planner
failure would be an explicit scheduling change to test, not a property to assume.

Keep a learned executor within the same boundary: one batched inference over available
units, their assignments and permitted history, followed by assembly of one valid order
batch. Begin with a small input representation shared across units. Separate workers per
unit, new message buses and a general graph framework add complexity before showing benefit.
Measure loading, warmup and inference time; loading in the per-episode constructor is not
automatically free preparation. Do not block `decide` for a slow planner.

**Artifact identity needs more than a class name.** Current external-controller cards hash
the defining source file; they do not pin loaded programs, weights or imported helpers.
Two checkpoints using the same class can therefore receive the same report label. Small
frozen rule/config artifacts fit the existing committed `configs/twwarhammer3/` scope.
Weights stay out of Git, with their exact hash, preprocessing, action decoder and configuration
recorded. Online-generated programs belong in run evidence with their inputs, attempts,
adoption decisions and hashes; editing source during a job would stop subsequent episodes.
Loaded identities must distinguish evaluation conditions, not merely appear in free text.

The built-in model path supplies the shared spend ledger and exchange capture. An external
class does not automatically gain that budget enforcement; its cost totals are self-reported,
and its card currently labels timing as blocking even if it uses a worker. Prefer explicit
factory wiring for a paid prototype over quietly making model calls inside an external class.

Use existing decision metadata for active assignment/program identity, phase transitions,
plan adoption/rejection and order origin. The harness should set origin, not trust a model's
claim. Log changes rather than a new timestamp-only metadata value every tick, which defeats
the quiet-trace throttling. A training input must use the permitted observation projection:
full traces contain evaluator information. A dense data export should be added only for a
specified learner, with explicit state, history, action and timing meanings.

Controller changes get controller versions; changed trace/export semantics need their own
schema or harness revision. Changing public information, primitive actions or timing changes
the benchmark condition and potentially its track. Do not relabel an altered information
boundary as only a better prompt.

## Comparisons that answer different questions

Keep the historical withheld-tactic chariot condition intact. For an execution study,
**disclose the tactic to every model arm** and label that cohort separately. Otherwise
the authored executor knows something the direct model may not. Common primitive actions
and fields matter; identical tactical APIs would remove the very expressiveness difference
that a synthesis experiment is intended to test.

| Question | Small comparison | Hold fixed | Reason to stop expanding |
|---|---|---|---|
| Is parameter adaptation enough? | Fixed reference versus model-selected parameters for that reference | Transition logic, inputs, local cadence and command suppression | No useful gain on a reserved variant; keep fixed parameters |
| Does generating logic add value? | Parameterized machine versus generated rules, with direct model orders as context | Disclosed knowledge, primitive orders, preparation information/budget and local rule cadence | Generated logic adds failures/cost without a meaningful benefit over parameters |
| Does planning help? | Fixed assignments versus model assignments above one executor | Executor, defaults, fallback and available fields | No task requires a consequential allocation decision yet |
| Does learning improve reactions? | Scripted reference versus a small learned executor or bounded correction | Assignment contract and information; same data across learned alternatives | Benefit vanishes against a hand-written correction, or serving misses the reaction window |
| Does the scheduling change help? | One controller with and without the proposed stale-plan or event trigger rule | Decision logic, scenario distribution and delay intervention | Only call count improves while outcomes or recovery degrade |

For the first chariot execution comparison, use the same disclosed target-selection rule
and retreat-geometry helper in both local arms. The parameter arm chooses bounded numeric
values; the generated arm can also change transition logic. This tests control-logic
synthesis within supplied geometry, not unrestricted tactic discovery. Target reassignment
and new movement geometry can be separate comparisons if the first one warrants them.

These are sequential choices, not a factorial suite to run at once. A natural-latency
comparison answers which deployed system performs better. A controlled component comparison
tests the changed component's contribution; equal median order age or token budgets do not
make systems equivalent.
Injected delays should be declared independently of observed difficulty. Do not infer a
causal latency effect from slower calls happening in harder battles. Planner-only delay
needs its own schedule inside the hybrid controller; do not sleep the whole executor.

**A generated artifact and its generator have different sampling units.** Many launches
of one frozen program estimate that program's performance. To compare policy-generating
models, retain multiple independent generation attempts, including invalid programs, repairs,
discarded candidates and all preparation/tuning cost. Group launches by generated artifact;
do not treat them as independent generation successes. State whether selection is first
valid candidate or a development-budgeted search. Never select on held-out wins. The same
distinction applies to training runs and learned checkpoints.

For each condition, retain wins/scored launches, exclusions and terminal forfeits, plus
preparation cost, runtime cost and failures. Measure planner request-to-adoption separately
from executor observation-to-order submission. Where contact-to-withdrawal matters, use
observed behavior with the recording resolution disclosed; 1 Hz replay cannot resolve
subsecond effects. Include failed and unfinished calls rather than reporting timing only
for accepted orders. Terminal episode scoring and recoverable failed decisions are distinct
in [the current loop](latency.md#scoring-the-battle-never-waits).

Randomize controller assignment across fresh launches and report start classes without
discarding unfavorable ones after seeing results. A launch is a sampling unit, not a promise
of an identical start; rematches and frames are not extra independent trials. Freeze the
launch count and stopping rule around the minimum improvement worth paying for. If the
available budget cannot distinguish that improvement, call the result a feasibility study.

## What to establish before a live comparison

For a chariot execution study, use the latest b40 model and reference traces, preserving
event timing and observed effects. The changed withdrawal recipe and corrected prompt mean
earlier explanations need rechecking. A replay can suggest a failure or test a rule's
decisions, but cannot show what the battle would have done after a different order.
Disagreeing with the reference controller is not itself an error. The
[robot team plan](robot-team-plan.md) proposes a separate study of changing assignments.

Agree the chosen repeatable check with the owner before treating a feature as verified:

| Observable requirement | Independent reference and cheapest useful check | What still needs the game |
|---|---|---|
| Expired or tactically invalid plans do not replace valid assignments | The agreed adoption contract; a short event sequence with a late reply and a lost supporting unit. Deliberately accepting every plan should fail it | Whether rejection improves recovery or wins |
| Parameter selection changes only permitted values; zero learned correction preserves the reference | Fixed state-machine semantics and the reference controller on the same histories | Whether any nonzero correction improves outcomes |
| A generated transition follows its declared guard and survives irrelevant ID changes | Hand-specified cases with distinct tactical choices and a deliberately inverted guard | Whether the guard captures the real tactical requirement |
| An accepted withdrawal actually clears engagement | Declared public-state/recording criteria, reviewed examples including accepted-but-stuck moves | Repeatable successful withdrawal and battle results |

Build only the check attached to the selected experiment. If the execution study does not
locate a convincing defect, keep the cause open: a small direct-versus-fixed-executor pilot
can still test whether persistent automation helps, but cannot explain why. Expand only
when a benefit survives the simpler baseline and a reserved variant.

Defer end-to-end visual fine-tuning, a learned battle simulator and large online RL runs.
They add perception, dynamics-model error or data costs before the current execution gap is
understood. All eventual battles remain unpaused at 1x.
