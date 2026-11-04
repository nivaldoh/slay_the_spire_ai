# Reference benchmarks for WH3

Use these benchmarks to design WH3 scenarios and check what their results mean.
Read this index, then the relevant profile for construction details, evaluation rules and
pinned GitHub entry points.

For the current battle and its evaluation, see the
[benchmark definition](benchmark.md) and [implementation plan](benchmark-implementation.md).

| Benchmark | How tasks are made | What it measures | Read it for |
|---|---|---|---|
| [BEHAVIOR](benchmark-references/behavior.md) | Human-specified goals; sampled physical instances | Goal completion and partial credit | Multiple valid solutions, starting states and goal checks |
| [CARLA Leaderboard](benchmark-references/carla.md) | Programmed traffic situations; configured routes | Route progress with infraction penalties | Triggers, event records and unintended scoring incentives |
| [SMACv2](benchmark-references/smacv2.md) | Designed maps and distributions; generated armies and starts | Team combat win rate | Tactical variation and whether a policy actually needs feedback |
| [RoCoBench](benchmark-references/rocobench.md) | Tabletop tasks with different capabilities, observations and action dependencies | Task success, steps and replanning | Robot coordination parallels to both WH3 team setups |
| [MultiAgentBench](benchmark-references/multiagentbench.md) | Domain tasks with agent roles and communication structures | Task scores, milestones and judged coordination | LLM team organisation, communication and outcome/process separation |

Source inspection: 2026-11-01; MultiAgentBench added 2026-11-02; RoCoBench added 2026-11-04. This is research, not a reproduction of their results or a
verification of WH3. The [definition](benchmark.md) and [owner interview](benchmark-implementation.md#owner-interview-one-land-battle)
still govern the choices awaiting the owner. No scenario, score or check is adopted here.

Each profile names the source revision and relevant functions. Recheck upstream before
adapting code. Versions matter: CARLA changed its score after early-stopping strategies
benefited from the old formula; BEHAVIOR's current partial-credit code is more specific
than its website summary. Their stepped simulators also differ from WH3's live-1x clock.

## How WH3 relates to real settings

These are parallels in the decision problem, not evidence that a WH3 controller transfers
to a physical robot or vehicle.

| WH3 feature | Comparable real setting | Possible research question |
|---|---|---|
| Orders persist while the engine handles movement | Fleet dispatch above vehicle controllers | Can a planner coordinate actions that take time to finish? |
| Different units depend on one another and can stop contributing | Warehouse or emergency-response robot teams | Can the team assign roles and recover from lost capabilities? |
| Reports become old while several places need attention | Supervising vehicles through delayed telemetry | Can the controller prioritise, react and recover in time? |

Our interface supplies structured state and high-level orders, making supervision and
coordination the closest connection. The game's pathfinding, combat, morale and opponent
bound the analogy; game success establishes no real-world competence. The current
[observation and order contract](benchmark.md#observations-and-orders) defines what is actually available.

## Design lessons to discuss

The [scenario guidelines](scenario-guidelines.md) turn these lessons into proposed coverage,
witness and validity procedures, with marked decisions for review. They also draw on
[CheckList](https://aclanthology.org/2020.acl-main.442/) and
[Procgen](https://arxiv.org/abs/1912.01588) for behavioral tests and reserved instances.

JUDGEMENT?: Transfer proposals — Codex, 2026-11-01: the ideas below organise possible WH3
scenario work; a single full-battle study is an alternative. These are research proposals;
the benchmark's pending definition, scores and verification methods remain with the owner.

1. **Separate families, scenarios and attempts.** A family might be a ranged force facing
   mobile attackers; a scenario fixes its armies and settings. Repeats measure consistency;
   unseen variants test the declared kind of generalisation.
2. **Allow different solutions.** A setup can encourage protecting vulnerable units without
   requiring a screening manoeuvre. Showing that screening caused success needs another comparison.
3. **Combine human design with constrained variation.** Choose useful situations, vary
   declared dimensions and reject invalid setups. Save realised starts and generator versions.
4. **Keep outcomes and diagnostics visible.** Before combining victory, health, morale or
   duration, test the formula against retreat, sacrifice, waiting and stopping.
5. **Try fixed plans as well as reactive scripts.** A simple win is useful evidence;
   whether the scenario remains informative depends on the question it should answer.
6. **Include focused situations and whole battles if both serve the question.** Local
   success alone does not establish full-battle strength.

## Decisions this research helps frame

The [existing interview](benchmark-implementation.md#owner-interview-one-land-battle) holds
the decisions these references help frame:

- Which situations should the suite cover?
- How should the engine result relate to health and morale in the ranking?
- Which variations will be reserved from tuning?
- Are we comparing complete controllers or models inside one fixed controller?

After those choices, use the existing [implementation phases](benchmark-implementation.md#phases).
This research does not select a new paid experiment or a sample count.

## Make cooperation inspectable before scoring it

Owner, 2026-11-04: use the collected papers **and code** to improve measurement and
visualisation, starting with simple fundamentals. The [animated research figure](reports.md#cooperation-evidence-proposal)
uses one saved team battle to make the following proposals concrete. It changes no benchmark rule.

JUDGEMENT: Cooperation evidence proposal — Codex, 2026-11-04: proposes owner-specific
timelines and continuing-support inspection before another coordination score. An aggregate
score is an alternative; the display and comparison proposals below remain unadopted.

**First identify the agent.** In the current split-army team, an agent owns regiments;
it is neither a soldier nor the game's movement controller. In native multiplayer it can
own an army, with separate client and army resources. Geographic groups are another grouping:
a class-based agent can own units on both wings. The [current suite page](reports.md#coordination-suite)
now colours actual owners from each battle's partition record, replacing its earlier geographic groups.

Use **cooperation** for the shared task; investigate **coordination** through how choices
depend on teammates' capabilities, state and timing. These are working distinctions, not
new scores. A shared victory, concurrent calls and useful interdependence are different claims.

| Question for the reader | Small display or measurement | Research idea and WH3 limit |
|---|---|---|
| Who knew what when they acted? | A lane per owner: member source observation → engine receipt, linked to its units and older positions. Keep empty, refused and unsent batches visible. | [MultiAgentBench](benchmark-references/multiagentbench.md) makes identities explicit. Its inspected graph loop is sequential; WH3 members can act independently. A model API exchange is not a teammate message. |
| Did one group remain able to support another? | Put sampled melee/routing states beside orders and the map. Inspect an interval, with unknowns; do not infer protection from nearby units. | [RoCo](benchmark-references/rocobench.md)'s cabinet requires continuing support. Its `task_cabinet.py` distinguishes holding from opening; `prompting/display_utils.py` pairs attributed dialogue with execution video. WH3 support can fail through morale, casualties, hidden enemies or hostile action during inference. |
| Did adaptation improve the shared result? | Keep engine outcomes and attempt counts beside the existing simple-controller comparisons. A replay illustrates a possible mechanism; it does not isolate its benefit. | [SMACv2](benchmark-references/smacv2.md) tests whether feedback is needed. Its `step(actions)` advances joint steps, whereas WH3 charges real inference delay and preserves standing orders. |

The remaining report improvement is member-specific information age: select an actual owner,
then inspect its own source view and calls on the same clock as the units. The current
`replay.read_trace` still uses dispatcher observations for team decisions; ownership colours
do not fix that clock. Reuse the current map and owner colours; a second reporting framework
is unnecessary. The figure is a design
example, not a replacement report. Its selected battle and fidelity check remain unverified
under the owner's rule; selection rests on JUDGEMENT `runs/cooperation-evidence/build.py`
Figure example. Source audit: `runs/cooperation-evidence/source-audit.md`.

Keep labels literal: **not in melee** does not establish readiness to help. The earlier
group display's **ready** label is gone with that display. A scenario's intended tactic is
a hypothesis, not an observed action.
The existing [coordination diagnostics](benchmark.md#the-coordination-suite-suite-v1)
already document their limits; low idle time, tight arrival timing or local numerical
advantage should not become a quality ranking without a check that establishes their meaning.

**For a later causal comparison**, the simplest question is whether reacting to a teammate
helps over a declared fixed plan with the same army, information access and executor.
The exact disabled feedback, timing, budget and repeats need agreement: existing single/team
arms also differ in information and concurrency. Removing messages becomes meaningful only
after a message channel exists. Preserve every failure and attempt; several calls in one
battle are not independent trials. Checkpoint interventions additionally need a declared
continuation and baseline: “no new orders” leaves standing orders active. A saved state alone
does not validate causal credit. No such comparison is scheduled by this proposal.

The closest robotics connection is supervision of heterogeneous resources through delayed
telemetry, not low-level physical control. [Real-Time Chunking](https://arxiv.org/abs/2506.07339)
offers the principle of conditioning on actions that will execute during inference;
its continuous-action inpainting is not an adapter for WH3's discrete targets. The collected
[game-to-robot study](../thesis/papers.md#cross-domain-test-design-from-video-game-to-real-robot)
instead motivates naming what transfers and testing it across interfaces. WH3's game rules,
pathfinding, opponent and shared army vision do not establish robot perception, motion safety
or independent local sensing. There is no cross-domain transfer result here.
