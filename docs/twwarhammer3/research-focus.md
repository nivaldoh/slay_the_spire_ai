# WH3 research focus

Draft for owner review, 2026-11-06. This spec connects the project's research interests
and sets out proposed boundaries for future work. The owner wants AI evaluation,
multi-agent systems and LLMs in scope; the primary contribution remains open. RL,
LLM post-training and robot learning are interests whose role needs deciding.

The proposed central question is: **How well do AI controllers make tactical decisions
and coordinate in a changing, partly observed battle?** A useful result explains a
capability, failure or tradeoff under stated conditions. Building a stronger player can
serve that question, but a win alone does not explain what the controller can do.

This is a research focus proposal, not a new benchmark definition or experiment approval.
[Current status](../state.md), the [benchmark contract](benchmark.md) and
[agreed checks](../agreed-checks.md) govern existing work. The thesis question is still
open. Older leads in the [thesis directions](../thesis/directions.md) and
[robot-team research](robot-team-research.md) are candidates, not selected priorities.

## How the topics fit together

JUDGEMENT: Contribution priority — Codex, 2026-11-06: proposes evaluation as the first
research contribution, with controller methods serving its questions. A method-led study
is the alternative; the proposed priorities below rest on this choice.

| Topic | Proposed role | Concrete question |
|---|---|---|
| AI evaluation and benchmarking | Shared foundation and candidate primary contribution | Do our battles distinguish the capabilities we say they test? |
| Multi-agent systems | Central subject alongside individual control | When does splitting control, sharing information or assigning roles help? |
| LLM-based agents | Main model family to study, alongside scripts and other learned policies | Can a model use game knowledge, plan, revise a plan and issue useful orders? |
| RL and LLM post-training | Conditional method research | Can learning improve decisions or reduce inference cost within our data and compute budget? |
| Robot learning | Related domain and possible later validation | Does a coordination method also help on a specified robot task? |

These are overlapping topics. A team of LLMs need not learn; a learned controller need
not be an LLM; multi-agent RL means learning interacting policies. Changing prompts,
memory or generated programs without updating model weights is a separate form of
adaptation from LLM post-training.

Possible outputs include a capability study using existing tasks, a benchmark with
justified tasks and informative baselines, or a controller method with a controlled study
of when it helps. None requires solving all the topics in this table.

## Domain and boundaries

The current interface supports high-level control of custom battles through structured
observations and persistent orders. The engine handles pathfinding, formations and
individual fighting. Friendly state is available; enemy state is restricted by visibility,
plus the public roster. Hidden evaluation data stays outside policy inputs.
Automated battles run unpaused at 1x, so inference delay affects execution. Latency remains
a condition and measurement; the owner's stopped [support-timing study](support-timing.md)
is not resumed by this spec.

An evaluated agent owns decisions and authority over units. Several advisers feeding one
decision maker differ from independently acting teammates. Splitting one army and
commanding separate allied armies are distinct setups; neither implies private local
vision unless that information boundary is explicitly implemented and checked.

JUDGEMENT: Expansion rule — Codex, 2026-11-06: proposes using existing battle interfaces
until a named question needs another mode, native clients or visual input. Expanding
coverage first is the alternative; the proposed scope boundary rests on this choice.

Start from small, inspectable battles, following the owner's simpler-then-more-complex
[scenario direction](scenario-guidelines.md#current-plan-and-owner-decisions). General
local research can use any faction and lords; VM-account restrictions are separate.
Terrain, morale, ranged fire, flying units, magic and asymmetric capabilities are useful
sources of variation when they change the decision being studied. Adding content alone
does not establish a new capability test.

Siege, Survival, Ambush and Conquest remain in the intended benchmark scope. Native
multiplayer, unfamiliar partners, model opponents and human-AI teams remain relevant
extensions. Each needs a question that its added complexity helps answer. Campaigns,
army selection, deployment, screenshot-only control and low-level movement learning
would broaden the current task. They are not prerequisites for this proposal; their
existing plans and permission boundaries remain separate.

## Questions worth keeping in scope

This shortlist elaborates the topics above; it is not a schedule. The examples are
possible comparisons, not adopted checks, scores or selected scenarios.

| Area | Question and a useful contrast |
|---|---|
| Tactical knowledge and adaptation | Does a familiar plan survive a changed situation? Contrast a fixed plan with responses to new information; changing names alone cannot prove memorization. The [Cannae candidates](cannae-comparison.md) address this distinction but remain unverified. |
| Planning and hierarchical control | Can a model assign useful goals while scripts execute them? Compare the same executor with fixed versus model-selected goals; keep tactical advice visible as a possible confound. |
| Team organisation and communication | How should agents divide units and decisions? Compare central and split control; then vary messages within the same team. Account for information, parallel calls, helper code and total resources. |
| Partial observation, memory and uncertainty | Can agents act on incomplete reports and notice when old beliefs are wrong? Compare current observations with permitted history or scouting. Full-army shared vision does not test independent local sensing. |
| Recovery and teammate/opponent modelling | Can a controller reassign work after losses or adapt to an unfamiliar partner or opponent? Compare against simple recovery rules and reserve the changed partners or opponents from tuning. |
| Generalisation and robustness | Do results survive new compositions, maps and task combinations? Separate repeated starts, unseen instances and unseen problem families; state exactly what was withheld. |
| Measurement validity and incentives | Does a score reward the intended success? Check shortcuts and proxy exploitation; troop preservation, dialogue quality and apparent coordination can disagree with winning. An unusual legal win is still a win. |

Within-battle memory and lessons carried between battles are different comparisons;
cross-battle learning or skill reuse must respect reserved evaluation cases.
Observable orders and outcomes support these studies. Fluent explanations and message
transcripts alone do not show reasoning, cooperation or why a battle was won. LLM/VLM
judges can be studied as annotation tools under the existing [judge proposal](tactic-judges.md);
their labels need independent validation before supporting a capability claim.

## Learning under limited throughput

WH3 provides a live game rather than a fast batch simulator. Time spent resetting,
playing, checking failures and evaluating competes with data collection. A checkpoint
can shorten an episode, but does not make large-scale training cheap by itself. The
[checkpoint checks](checkpoints.md#limits) have scenario and build limits; the
[post-training pipeline](../posttraining.md) has no demonstrated learning gain.

JUDGEMENT: Learning scope — Codex, 2026-11-06: proposes small, data-efficient learning
studies before full-battle online RL or joint team training. A training-first programme
is the alternative; the candidate learning path below rests on this choice.

Candidates include imitation from useful demonstrations, distilling a strong controller
into a cheaper one, learning a skill selector or outcome predictor, and offline RL from
recorded transitions. Preference training needs credible comparisons between alternatives;
one winning trajectory does not supply them. Later online RL could use short restored
episodes or a curriculum that starts near a successful ending. Multi-agent training adds
the problem of assigning team credit and learning while teammates change.

Before selecting a learning study, establish usable data and targets, train/evaluation
separation, a training host and serving route, measured collection/reset throughput, and
a budget that includes evaluation. Compare with the unchanged model and a simple rule or
imitation baseline as appropriate. Better training loss is insufficient: the controller
must improve the declared behaviour in reserved live cases, with cost and uncertainty
reported. Exact comparisons and correctness checks require owner agreement.

Offline methods reduce new collection during training; they still depend on data coverage
and live evaluation. [IQL](https://arxiv.org/abs/2110.06169) is one reference, not a selected
algorithm. Large-scale end-to-end RL, training foundation models and learned world
simulators have no resource case here yet. The existing local checkpoint-RL experiment
[stays paused](checkpoint-rl.md#open-owner-choices-decision-11).

## Connection to robot learning

The closest connection is high-level coordination: assigning heterogeneous resources,
maintaining dependencies, reacting to missing information and recovering when a teammate
cannot do its job. [RoCoBench](benchmark-references/rocobench.md) provides concrete
robot task counterparts. A WH3 regiment is best compared to a resource controlled through
a skill interface; individual soldiers are not independently evaluated robot agents.

JUDGEMENT: Robotics role — Codex, 2026-11-06: proposes robotics as a source of questions,
with cross-domain testing optional. Requiring a robot-learning contribution would change
task selection and resources; the proposed connection below rests on this choice.

A later connection needs a named robot task, a statement of what transfers (for example,
the allocation rule), and a comparison on that task. WH3 supplies neither robot perception
nor contact physics, actuator control or physical safety evidence. Game wins do not
establish robot performance. A robot-learning claim would also need actual learning and
evaluation in that domain. Keeping robotics as motivation is a valid project choice.

## Keeping future work focused

The proposed filter rests on JUDGEMENT `research-focus.md` Contribution priority and
Expansion rule. Apply it through the existing [work card](../workflow.md#before-a-change-the-card):

- State the question, the capability it concerns and what result would change our view.
- Name the simplest useful comparison and why the current scenarios cannot already answer it.
- State the observable evidence, independent reference and proposed repeatable check.
- Name the data, game time, compute and owner decisions needed; park dependent work until resolved.

Evaluation should distinguish whole-controller performance from the effect of one component.
Fixing a model while changing prompts, tools and concurrency compares systems. Isolating a
component needs a matched comparison. Keep engine outcomes, cost, response delay and
reliability visible; report planned attempts and failures, repeated-run uncertainty and
development exposure. Reserve evaluation cases before tuning. Replays aid diagnosis;
one replay is not a causal test. Exact splits, counts, scores and acceptance thresholds
remain decisions under the [evaluation guidelines](evaluation-guidelines.md).

Recorded decision tasks can offer cheap probes, but do not replace live control tests.
Live replication needs the declared game build and mod, as well as the experiment files.
Useful deliverables are a clear task specification, reproducible setup and scoring records,
simple and competitive baselines, a bounded empirical finding and its limitations. A
negative result can qualify. New infrastructure serves these deliverables; a new interface,
scenario, report or controller is not by itself evidence of research progress.

Under the owner's [verification rule](../../AGENTS.md#verification-hard-rule), a proposed
check or passing test does not make a research claim verified. This spec adopts no check.
Novelty, general model rankings, training feasibility and robot transfer remain unestablished.

## Reading map and decisions

This spec draws from the [research collection](../thesis/papers.md),
[benchmark references](benchmark-references.md) and [evaluation references](../references.md).
The following primary sources were re-read for these narrow lessons; the WH3 applications
are our proposals. This was a focused synthesis, not an exhaustive novelty search.

| Source | Lesson for this focus |
|---|---|
| [CheckList](https://aclanthology.org/2020.acl-main.442/) | Organise tests around capabilities and test types; our tactical categories still need validation. |
| [SMACv2](https://arxiv.org/abs/2212.07489) | Timestep-only policies succeeded on some original SMAC tasks; test whether fresh observations matter here. |
| [Reasoning or Reciting?](https://arxiv.org/abs/2307.02477) | Alter default task assumptions to probe transfer; this cannot identify a model's WH3 training data. |
| [RoCo](https://arxiv.org/abs/2307.04738) | Study dialogue and action dependencies in robot teams; its results do not transfer to live WH3 automatically. |
| [IQL](https://arxiv.org/abs/2110.06169) | Learning from fixed data is a possible route; the paper does not establish that our traces suffice. |
| [Statistical Precipice](https://arxiv.org/abs/2108.13264) | Few-run point estimates can mislead; uncertainty matters. It does not select our sample size or interval method. |

For owner review, the marked calls are **Contribution priority**, **Expansion rule**,
**Learning scope** and **Robotics role**. They belong with existing review items
[1, 4, 8 and 10](../review-queue.md#decisions), without a new decision queue. Choosing
the main contribution comes first; the exact research question and experiment follow.
