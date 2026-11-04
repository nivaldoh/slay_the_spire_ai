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
