# MultiAgentBench reference for LLM team evaluation

[Reference index](../benchmark-references.md). **MultiAgentBench** is a useful complement
to [SMACv2](smacv2.md): it studies LLM team organisation and communication, while SMACv2
provides the closer tactical combat setting.

Kunlun Zhu et al., [MultiAgentBench: Evaluating the Collaboration and Competition of LLM
agents](https://aclanthology.org/2025.acl-long.421/), **ACL 2025, Main Conference, Long
Papers**, pp. 8580–8622; DOI `10.18653/v1/2025.acl-long.421`.
The publication links the public [MARBLE codebase](https://github.com/ulab-uiuc/MARBLE),
whose [licence](https://github.com/ulab-uiuc/MARBLE/blob/8d60fa17b5596b44458a52d4296061b9fc13d6f2/LICENSE)
is MIT.

## What it evaluates

The [paper](https://aclanthology.org/2025.acl-long.421.pdf), sections 3–4, covers research,
coding, database diagnosis, Minecraft, bargaining and Werewolf. It compares star, chain,
tree and graph coordination, with separate task scores and coordination measures.
Milestones track intermediate contributions; communication and planning are assessed by
an LLM judge. Final task scoring depends on the domain, including rule-based outcomes.
These distinct measures make it useful for asking whether agents accomplish the task,
how they divide the work, and whether their exchanges help.

## Connections to WH3

These are connections to our existing questions, not changes to the evaluation plan.

| Existing WH3 question | What this reference contributes |
|---|---|
| [One controller versus independent unit-group owners](../multi-agent-plan.md#1-questions-and-claims) | Explicit agent roles and relationships make division of control inspectable. Keep the same army, information and total resources when comparing architectures. |
| [Which team structure to use](../team-structures.md#3-the-structures) | Named communication topologies provide concrete comparison arms. A communication graph alone does not establish independent or concurrent action authority. |
| [Whether messages help](../multi-agent-plan.md#communication) | Logged exchanges can connect proposed coordination to subsequent actions. The existing message-removal comparison would test benefit; a judge rating fluent dialogue cannot establish it. |
| [Engine outcome and battle diagnostics](../benchmark.md#outcome-and-score) | Separate final success from intermediate coordination. For our cavalry advantage, a documented holding action followed by a cavalry attack could be a diagnostic; requiring that manoeuvre would change the benchmark. |
| [Later cooperation and competition](../multi-agent-plan.md#3-environments-and-agent-boundaries) | Bargaining and Werewolf connect to negotiation, alliances and private information in the campaign idea. They do not establish real-time battle competence. |

## Code to consult

Inspected 2026-11-02 at
[`8d60fa17b5596b44458a52d4296061b9fc13d6f2`](https://github.com/ulab-uiuc/MARBLE/commit/8d60fa17b5596b44458a52d4296061b9fc13d6f2)
(2025-08-03). This is the inspected revision, not an identified paper-reproduction release.

| Pinned file | Entry points and use |
|---|---|
| [marble/graph/agent_graph.py](https://github.com/ulab-uiuc/MARBLE/blob/8d60fa17b5596b44458a52d4296061b9fc13d6f2/marble/graph/agent_graph.py) | `AgentGraph`, `add_relationship`: agent identity and explicit relationship configuration. |
| [marble/engine/engine.py](https://github.com/ulab-uiuc/MARBLE/blob/8d60fa17b5596b44458a52d4296061b9fc13d6f2/marble/engine/engine.py) | `graph_coordinate`, `star_coordinate`, `chain_coordinate`, `tree_coordinate`: execution protocols; `_write_to_jsonl`: task assignments, results and communications saved by the engine. |
| [marble/evaluator/evaluator.py](https://github.com/ulab-uiuc/MARBLE/blob/8d60fa17b5596b44458a52d4296061b9fc13d6f2/marble/evaluator/evaluator.py) | `evaluate_communication`, `evaluate_planning`, `evaluate_kpi`: judge calls and contributing-agent records, separate from domain task evaluators. |

## Limits that affect reuse

The inspected `Engine.graph_coordinate` calls `agent.act` sequentially within iterations.
That schedule is not our [live-1x contract](../multi-agent-plan.md#4-the-battle-execution-contract),
where a ready teammate must act while another is still thinking. Borrowing its orchestration
would change what latency and parallelism mean in WH3.

There is also a paper/code gap: in `graph_coordinate`, communication, planning and KPI
evaluation calls are commented out; communication and planning lists receive `-1`
placeholders. `star_coordinate` calls those evaluators. A graph-mode run at this revision
therefore does not automatically reproduce the paper's coordination measurements.

`Engine._get_totoal_token_usage` sums agent and planner counters, excluding the evaluator's
own judge calls. It is not a complete API-spend ledger. Our team comparisons need to retain
their declared accounting boundary and distinguish controller cost from evaluation cost.

The paper's LLM-rated milestones and coordination scores are interpretations, not engine
witnesses or proof that communication caused success. Their scoring does not replace our
engine outcome, health/state scoring or agreed checks. No MARBLE execution or published
result was reproduced here; transfer to WH3 remains unverified.
