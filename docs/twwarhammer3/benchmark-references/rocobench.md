# RoCoBench reference for robot coordination

[Reference index](../benchmark-references.md). **RoCoBench** is a useful reference for
our LLM teams: its tasks make agents divide work, respect different capabilities and
coordinate actions that depend on one another.

Zhao Mandi, Shreeya Jain and Shuran Song, **RoCo: Dialectic Multi-Robot Collaboration
with Large Language Models**, [ICRA 2024](https://doi.org/10.1109/ICRA57147.2024.10610855).
[Paper, 2023 preprint](https://arxiv.org/abs/2307.04738v1) ·
[Project](https://project-roco.github.io/) ·
[Code](https://github.com/MandiZhao/robot-collab).

[VMAS](https://arxiv.org/abs/2207.03530) offers broader robot learning scenarios;
[COHERENT](https://arxiv.org/abs/2409.15146) focuses on a central task assigner and
heterogeneous robot executors. RoCoBench is the closer reading choice for our question
about communicating LLM teammates with separate roles.

## What it tests

Six simulated tabletop tasks vary action ordering, shared versus agent-specific
observations, and workspace overlap. Examples: **Sort Cubes** requires robots with
limited reach to pass objects toward another robot's goal; **Arrange Cabinet** needs
robots to hold doors open while a teammate retrieves cups; **Move Rope** needs joint
movement of the same object. See [paper §4 and Appendix 10](https://arxiv.org/pdf/2307.04738v1).

RoCo is the controller evaluated on that benchmark. Each robot has an LLM role; agents
discuss a joint plan, receive constraint feedback and revise it. The last speaker proposes
every robot's action; a central motion planner then produces their trajectories ([paper §§2–3](https://arxiv.org/pdf/2307.04738v1)).

## Similarities to WH3

These are our analogies, using the existing [agent boundaries](../multi-agent-plan.md#3-environments-and-agent-boundaries).

| Coordination problem | Single-army team | Multi-army team |
|---|---|---|
| Different capabilities and limited reach | Infantry and cavalry owners must assign jobs their unit groups can perform. | Allied army owners must account for each army's roster and position when dividing objectives. |
| One agent enables another's action, as in Arrange Cabinet | A holding group can keep enemies occupied while a mobile group flanks. | One army can pin an enemy while its ally approaches; the attack depends on the ally's readiness. |
| Actions share space, as in Move Rope or Pack Grocery | Groups must coordinate approach routes and timing around the same fight. | Armies must coordinate convergence and support across fronts. |

The common problem is coordinating separately controlled resources toward a shared result.
The mapping is robot agent → unit-group owner or army owner, rather than robot → individual
soldier. WH3 army ownership also brings army-level resources; native multiplayer adds
client boundaries that RoCoBench does not model.

## Evaluation and limits

The paper's Table 2 uses **20 runs per task** and reports success, steps **among successful
runs**, and replanning attempts **across all runs**. Its central baseline has fuller
information, so that comparison does not isolate the benefit of communication.
These measures distinguish task completion from planning effort; they do not measure
WH3 battle-time responsiveness ([paper §5.1](https://arxiv.org/pdf/2307.04738v1)).

The simulator plans before advancing execution. WH3 runs [unpaused at 1x](../multi-agent-plan.md#4-the-battle-execution-contract):
orders persist, observations age, and one agent must act while another thinks. RoCo's
simulation uses accurate state descriptions and cooperative tasks; WH3 adds hidden
enemies, opponents, casualties and morale. The paper's physical demonstration pairs a
human with one robot, rather than reproducing the simulated robot teams (§§5.4, 7).
WH3-to-robot transfer remains unverified.

## Code to consult

Inspected 2026-11-04 at `9943870298e650de7ff1f9231ed279b35f196ddc`:

- [rocobench/envs/task_sort.py](https://github.com/MandiZhao/robot-collab/blob/9943870298e650de7ff1f9231ed279b35f196ddc/rocobench/envs/task_sort.py):
  `SortOneBlockTask`, `get_agent_prompt`, `get_reward_done`; reach constraints, agent
  descriptions and a task completion check.
- [run_dialog.py](https://github.com/MandiZhao/robot-collab/blob/9943870298e650de7ff1f9231ed279b35f196ddc/run_dialog.py):
  `LLMRunner.one_run`; dialogue → planning → execution. It can also restore the previous
  state after a plan fails to execute, unlike a live WH3 battle.

Use this as a task-design reference. No scenario, score or check is adopted, and no
published result was reproduced. Source review: `runs/robot-coordination-reference/`.
