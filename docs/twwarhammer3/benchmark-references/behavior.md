# BEHAVIOR task construction reference

[Reference index](../benchmark-references.md). Read this profile for task definitions,
valid instances and scoring progress without prescribing one action sequence.

BEHAVIOR is a household-robotics benchmark. This profile uses BEHAVIOR-1K for the origin of
its task catalogue and the 2026 challenge for a concrete evaluation protocol. The challenge
evaluates a subset of the catalogue; a catalogue size is not an evaluation sample count.
The challenge rules require tag `v3.9.3`; the implementation inspected below is a pinned
`main` snapshot, not an established match to that tag. Its commit and tag-ref API lookups
did not resolve on the inspection date. Code findings below describe that snapshot.

## How tasks are created

The [BEHAVIOR-1K paper, sections 2 and 4 and Appendix B](https://arxiv.org/html/2403.09227v1)
describes a human-led pipeline. Candidate activities came from time-use surveys and
WikiHow, were filtered for feasibility, and were prioritised through a survey about work
people wanted robots to do. Annotators specified objects, initial conditions and goal
conditions in BDDL, a predicate-logic language. An annotation interface enforced logical
constraints. Object-property annotation combined crowdworkers, students and GPT-3; that
assistance should not be described as automatic authorship of all task goals.

An activity definition can admit many physical starting states and solutions. The
[task documentation](https://behavior.stanford.edu/behavior_components/behavior_tasks.html)
describes sampling concrete objects and poses while satisfying the initial conditions,
then saving accepted instances for reuse. Human task specification and automatic instance
generation are distinct stages. Logical validity alone does not establish that a robot can
physically complete every sampled instance.

For example, [assembling gift baskets](https://github.com/StanfordVL/BEHAVIOR-1K/blob/14bc29c66821eca9e2f7948a749397d9e7fddd13/bddl3/bddl/activity_definitions/assembling_gift_baskets/problem0.bddl)
specifies the objects and the required contents of the baskets. The goal does not require
the robot to fill the baskets in one particular order. WH3 could likewise define a battle
situation and its objective while accepting different valid tactics.

## What evaluation measures

The [2026 challenge rules](https://behavior.stanford.edu/challenge/evaluation.html#metrics-and-results)
rank submissions by task success score, including partial completion, averaged across
100 tasks. They also report simulated time and distances travelled by the robot's base
and hands, normalised against demonstrations; efficiency breaks score ties.

For self-evaluation, the rules specify one rollout on each of the first 10 public test
instances per task. Other public instances can be used for development, with additional
instances held out for final evaluation. Instances vary initial object states and robot
poses. The rules explicitly prohibit selecting the best rollout for each instance.
This tests variations of known tasks, not arbitrary unseen household competence.

The pinned [TaskMetric implementation](https://github.com/StanfordVL/BEHAVIOR-1K/blob/14bc29c66821eca9e2f7948a749397d9e7fddd13/OmniGibson/omnigibson/metrics/task_metric.py)
is more specific than the website's short formula. Full success gives Q = 1. Otherwise,
for each allowed goal option it counts predicates false initially and true finally,
divides by that option's total predicate count, and takes the maximum over options. The
denominator includes predicates already satisfied initially. The website describes a
plain final satisfied fraction. This is a website-versus-snapshot difference, not proof
of how the required challenge tag scores; do not treat the descriptions as interchangeable.

The [evaluator](https://github.com/StanfordVL/BEHAVIOR-1K/blob/14bc29c66821eca9e2f7948a749397d9e7fddd13/OmniGibson/omnigibson/eval/evaluator.py)
keeps full success separately. Policy connection, query-timeout and policy-error failures
receive success false and final Q zero. JSON records retain task, instance, rollout and
failure details. This separation between completion, progress and failure is more useful
to borrow than treating a goal-predicate fraction as a WH3 health or morale formula.

## Timing and information limits

The evaluator queries the policy and then advances the simulator. The world waits during
inference. In the documented websocket mode, policy queries and a share of simulation
work consume an accounted wall-time budget, with separate first-query allowances. Thus
latency can reduce the available budget without creating WH3's continuously ageing battle
state. [Protocol details](https://behavior.stanford.edu/challenge/evaluation.html)
belong to that serving mode, not to every BEHAVIOR experiment.

The challenge exposes RGB, depth and proprioception through the policy wrapper; goal
checks use simulator state. WH3's public structured observation and hidden evaluator
state need their own boundary, rather than inheriting the robot's sensor contract.

## Code to consult

Inspected 2026-11-01 at [`14bc29c`](https://github.com/StanfordVL/BEHAVIOR-1K/commit/14bc29c66821eca9e2f7948a749397d9e7fddd13)
(commit dated 2026-10-30). Code inspection only; no robot experiments reproduced. Current
BDDL code is inside this repository under `bddl3/`; the old `StanfordVL/bddl` URL redirects
to the archived BEHAVIOR-100 implementation.

| File at the inspected revision | Entry point and use |
|---|---|
| [problem0.bddl](https://github.com/StanfordVL/BEHAVIOR-1K/blob/14bc29c66821eca9e2f7948a749397d9e7fddd13/bddl3/bddl/activity_definitions/assembling_gift_baskets/problem0.bddl) | Concrete object list, starting conditions and goal expression |
| [behavior_task.py](https://github.com/StanfordVL/BEHAVIOR-1K/blob/14bc29c66821eca9e2f7948a749397d9e7fddd13/OmniGibson/omnigibson/tasks/behavior_task.py) | `BehaviorTask`, `get_goal_option_satisfaction`: connecting a task to a physical instance and goal readings |
| [bddl_utils.py](https://github.com/StanfordVL/BEHAVIOR-1K/blob/14bc29c66821eca9e2f7948a749397d9e7fddd13/OmniGibson/omnigibson/utils/bddl_utils.py) | `BDDLSampler`: concrete initial states satisfying semantic constraints |
| [predicate_goal.py](https://github.com/StanfordVL/BEHAVIOR-1K/blob/14bc29c66821eca9e2f7948a749397d9e7fddd13/OmniGibson/omnigibson/termination_conditions/predicate_goal.py) | `PredicateGoal._step`: task completion checked against the simulator |
| [task_metric.py](https://github.com/StanfordVL/BEHAVIOR-1K/blob/14bc29c66821eca9e2f7948a749397d9e7fddd13/OmniGibson/omnigibson/metrics/task_metric.py) | `compute_q_score`, `TaskMetric`: exact partial-credit denominator and efficiency records |
| [evaluator.py](https://github.com/StanfordVL/BEHAVIOR-1K/blob/14bc29c66821eca9e2f7948a749397d9e7fddd13/OmniGibson/omnigibson/eval/evaluator.py) | `evaluate_instances_batched`, `BatchedEvaluator.run`, `_step_fn`: rollout lifecycle, failures and timing |

## What WH3 can borrow

Within the [index's transfer proposals](../benchmark-references.md#design-lessons-to-discuss):
keep a problem definition separate from its concrete starting state, allow multiple valid
solutions, and keep independently checked goal readings separate from policy inputs.
Keep the raw measurements beside any partial-credit score; their usefulness depends on
which parts of the task the chosen predicates actually capture.

The real-world parallel is a supervisor arranging a sequence of actions while underlying
controllers carry out physical work. WH3 supplies much of that low-level control through
the game engine. This is a useful setting for planning and recovery questions, while
manipulation physics, perception and household task coverage remain different problems.
