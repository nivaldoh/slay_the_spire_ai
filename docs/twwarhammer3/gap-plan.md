# GaP graph controllers for WH3

Planning only, 2026-10-31. The owner requested a GaP research reference and a concrete plan
for one army with several LLM controllers, then several allied armies. No implementation,
game run or paid experiment is authorized by this page. New checks below are proposed,
not agreed. Local source audit: `35dbeab`; external pins are in [references](#references).

**This is worth a bounded experiment.** A graph can keep a useful battle plan running while
models think, make recovery explicit, and let us inspect which decision led to an order.
The interesting question is whether those properties help when units move, targets vanish
and teammates become unavailable. A graph can also make a bad plan very reliable: strength
must be compared with simpler controllers using the same skills and information.

Start with two controllers owning disjoint groups in one army. Reuse the existing controller
contract and team dispatcher; build a small WH3 skill catalog around existing code. First
prove a hand-written graph works, then let multiple LLM authors build the same kind of graph,
then improve it between battles. Repeated attempts from a checkpoint are a later, narrower
training tool. Native allied armies depend on their own multiplayer checks.

## What transfers from GaP

[Chen et al., GaP](https://arxiv.org/html/2607.05369v1), July 2026, describes agents that
compose typed skill graphs and improve them through simulation rehearsal. Its authoring
agents are distinct from the deployed graph; a multi-agent authoring process does not by
itself imply decentralized live control. MORSL supplies reusable robot capabilities.
Sections 3–4 define VA and the method; Appendix E gives the rehearsal loop.

The paper calls its tasks **quasi-static** and leaves moving targets to future work.
WH3 adds partial visibility and reacting opponents. Testing this extension would not by
itself establish novelty or an advantage.
[Paper, section 6](https://arxiv.org/html/2607.05369v1#S6).

Keep three experiments distinguishable:

| Experiment | What the LLMs do | What runs during battle | Claim it can test |
|---|---|---|---|
| GaP-style authoring | A coordinator and specialist authors build subgraphs before battle | Frozen graphs, one per army group | Whether structured authoring produces better reusable policies |
| Live graph controllers | Each group has its own LLM choosing bounded graph goals or parameters | Fast graph execution continues while each LLM thinks | Whether graphs help several live controllers handle change |
| Graph improvement | Authors revise graphs using completed training attempts | The next attempt uses a new frozen version | Whether experience improves held-out performance |

Only the second is necessarily several **live LLM controllers**. The first still has
separate runtime controllers, but their authors may no longer run. Do not label these arms
interchangeably or attribute an improvement to multi-agent execution just because multiple
agents wrote the artifact.

JUDGEMENT: G1 Research claim — Codex, 2026-10-31: separate authoring, live control and revision.
A combined system is the alternative; attribution of any improvement rests on this split.

## What already exists

The source and an independent read agree on these boundaries. Historical agreed checks
remain evidence only at the revisions and for the cases [agreed-checks.md](../agreed-checks.md)
records; this inspection is not a new live verification.

| Existing piece | Useful contract | Missing for this plan |
|---|---|---|
| [controllers.py](../../src/twwarhammer3/battle/controllers.py), `controller_class`, `factories` | `decide(observation)`, `acknowledge(ack, latency)`, `metadata()`; fresh controller per episode; external `module:Class` loading | A written/type-checked contract would help; no need for a replacement framework. Paid calls and prompts are integrated for named built-ins, not automatically for external classes |
| [team.py](../../src/twwarhammer3/battle/team.py), `TeamPolicy`, `project` | Exactly two members; copied views, ownership checks, independent completion, routed feedback | No teammate message protocol. `ModelTeam` fixes both members to the same model/effort and Knights/rest split; general configuration is not implemented |
| [skills.py](../../src/twwarhammer3/battle/skills.py), `RULES`, `Skills` | Persistent assignments for `engage`, `shoot`, `hold`, `charge`, `move` | These return orders and phase descriptions, not a typed start/running/succeeded/failed/cancelled lifecycle |
| [commander.py](../../src/twwarhammer3/battle/commander.py), `CommanderPolicy` | A fast skills executor continues while a model plans asynchronously | Useful scheduling reference and baseline; its whole-army assumptions need an adapter before use on a member view |
| [play.py](../../src/twwarhammer3/battle/play.py), `_drive` | One transport writer, validation, acknowledgements, traces and ending handling | `decide` is synchronous at this boundary. A graph must yield promptly instead of waiting inside it for movement or a model |
| [checkpoint.py](../../src/twwarhammer3/battle/checkpoint.py) | Replay reconstruction and scripted tick-specific input; `restore_episode` supports a step with at most one injected batch | No generic continuously running restored graph/team loop; no automatic Python memory restoration |
| [worker.py](../../src/twwarhammer3/engine/worker.py) and native battle mode | Offline multiplayer plumbing | Worker control currently accepts only unqueued moves, rejecting even an explicit `queue: false`; current skills cannot be plugged in unchanged. No live native multiplayer battle established |

The existing team partition, target filtering, age policy and cleanup choices remain marked
in [multi-agent-implementation.md](multi-agent-implementation.md#choices-settled-for-now-2026-10-28).
Any comparison using that team rests on those JUDGEMENT calls; this plan does not settle them.

## Controller design to propose

JUDGEMENT: G2 Integration — Codex, 2026-10-31: use the existing policy contract and two-member
dispatcher with a WH3 graph adapter; direct GaP runtime integration is the alternative.
The implementation steps below rest on this choice.

Keep the outer controller interface independent of graphs. Document its current required
methods, optional cleanup/event methods, exception behavior and feedback identity. A small
Python `Protocol` may express that contract; it must not force scripts or direct LLM
controllers to pretend to be graphs. A factory should separately select controller type,
model, skill catalog and graph artifact, and supply the existing shared ledger/transport.
It must still construct fresh episode state. Preserve existing controller names and behavior.

Use `TeamPolicy` to own partitioning and sending orders. Each graph member receives only its
projected view, returns ordinary orders and gets only its own feedback. A member may be a
script, a direct LLM, a fixed graph, or an LLM planner over a graph. This permits mixed pairs
for diagnosis without changing the transport. More than two members is a later change.

Suggested responsibilities, created only when a step actually needs them:

| Location | Responsibility |
|---|---|
| `battle/controllers.py` | Select factories and record complete controller identity; preserve budget/provider checks |
| Proposed `battle/graph.py` | Load a declared graph, validate it, track node instances, advance ready work and yield orders |
| `battle/skills.py` plus a small adapter | Implement approved WH3 capabilities and their observable status; keep tactics shared across baselines |
| Existing `battle/team.py` | Unit authority, independent dispatch and feedback; graph-only dispatch guard and later explicit member factories |
| Proposed `configs/twwarhammer3/graphs/` | Reviewed immutable graphs and skill descriptions, only for planned experiments |
| A later offline authoring/revision entry point | Produce candidate artifacts from training evidence; never edit the running policy or scorer |

Keep this code within WH3 until another game actually needs it. GaP remains an optional
controller family, not a dependency of `hold`, `llm_rules` or ordinary team play.

### Graph execution in a moving battle

JUDGEMENT: G3 Execution semantics — Codex, 2026-10-31: resumable nodes, explicit data producers
and fresh guards before dispatch; blocking super-steps are the alternative.
Responsiveness and stale-order claims rest on the proposed semantics and their checks.

Each node has a kind, typed inputs/outputs and named exits. Start with approved skills,
public-state conditions, branches and bounded loops. Each running skill returns its current
status on later observations; waiting for contact must not stop the other member. Keep
control edges (what runs next) separate from data edges (where an input came from).
Give each value its producer, battle/episode, graph revision, node invocation and source
observation sequence/time. Reject missing producers and ambiguous bindings.

At each call, consume feedback, refresh public conditions, advance a bounded amount of ready
work, then yield. A model request is asynchronous; a late response must match the still-live
invocation before it can alter a goal. An acknowledgement means an order arrived or was
accepted; node success requires the skill's independent state witness. Track queued orders
through their effects instead of treating queue submission as completion.

Recheck target visibility, unit authority and skill preconditions against the latest view
before emitting an order. This cannot eliminate changes during transport: the engine remains
the last legality check. Preserve the original observation time so freshness is measurable.
Use battle time for deadlines and order age; use the existing clock caveats when measuring
model latency. All battles remain unpaused at 1x.

This needs a specific addition: today's `TeamPolicy._validate` checks the member's saved
decision view, not the current dispatch view. A check inside the graph's `decide` is therefore
insufficient. Under G3, add an optional graph dispatch guard that receives the latest
`project()` view when the dispatcher selects a ready graph batch. On a failed precondition,
send no orders and return local refusal feedback so the graph can reconsider. Keep the
original source time and batch identity; do not relabel an old decision as fresh. Existing
direct-controller validation keeps its current behavior, and that difference must be
declared in comparisons. Test a target hiding after worker completion but before selection.

JUDGEMENT: G4 Interruption policy — Codex, 2026-10-31: fresh guards can cancel/reselect a skill;
age limits, loop limits, retry counts and fallback orders await the owner. Keeping old goals
is the alternative; tactical behavior and any comparison rest on these parameters.

Cancellation must distinguish stopping a Python task from stopping a unit's already-issued
order. Record whether an engine cancellation/replacement was sent and acknowledged; never
claim a cancelled graph node has stopped the unit without a witness. On battle end, record
unsent work and ignore replies from that episode. No thread may send after a new episode
takes ownership. A new graph version starts only between attempts in the initial design.

### The WH3 skill catalog

MORSL's robot functions do not transfer. Its documented capability contracts do: a short
description for the coordinator, detailed inputs, exits and examples for a specialist.
Start by wrapping capabilities we already have, not by building a general tactics library.

JUDGEMENT: G5 Skill scope — Codex, 2026-10-31: begin with observation predicates, move and
engage; add charge/hold/shoot only when a planned case needs them. A broad library first
would change effort and baseline strength; the minimal delivery order rests on this scope.

For every skill record: allowed unit owners; public inputs and types; entry conditions;
orders it can emit; running/success/failure/cancel exits; timeout and retry policy; behavior
when a target hides, dies or routs; and a separate engine witness. Keep data lookup and
evaluation out of the skill's policy input. Version implementation and description together.

| Candidate | Initial contract to resolve | Evidence needed beyond acknowledgement |
|---|---|---|
| `observe_contact` | Read visible enemies and friendly contact state; no orders | Known contact and non-contact cases, including a hidden target; no oracle field in routing |
| `move_to` | Command owned units toward a public point and keep observing | Position approaches/reaches a declared region; no-order control excludes idle drift; arrival radius and deadline need agreement |
| `engage_visible` | Engage a currently visible enemy; yield if visibility/authority changes | Correct target and contact/effect where observable; target disappearance is not proof it died |
| `hold_area` | Stay near a point with an explicit engagement allowance | Position and movement compared with the allowance; existing `hold` may attack nearby enemies |
| `charge_when_engaged` | Charge a visible enemy already in melee | Movement/contact and chosen target; existing `charge` is not a general flank planner or proof of a charge bonus |
| `shoot_visible` | Use an owned ranged unit on a visible target | Firing/ammunition/target evidence, with a control for unrelated shots; no claim that the order guarantees damage |

Use structured references such as owned-unit IDs, visible-enemy IDs and world points, rather
than arbitrary strings. Type checks cannot prove reachability, good tactics, visibility at
future execution, or absence of friendly obstruction. Those remain runtime/game concerns.

## A concrete first battle graph

Use the existing two-group setting to check machinery, not to declare a benchmark. The line
member engages a visible opponent; the cavalry member waits for observable contact, then
attacks an eligible visible target. While it waits, the line keeps acting. If the target
disappears, cavalry returns to selection; if none is visible, it yields without inventing
a target. This is intentionally close to the existing charge rule so we can isolate the
graph from new tactical code.

```text
Line member:     select visible target -> engage -> observe -> select again
Cavalry member:  observe contact -> eligible target? -> charge -> observe again
                       ^                 |
                       +---- no target --+
```

Each arrow advances on a new observation or completed local work; it is not a blocking
Python loop. Initially both members use the current allowed ally view, without messages.
For the live LLM arm, each member's LLM chooses a target preference or goal from a bounded
menu while the graph keeps evaluating current conditions. The army-wide authority remains
with the declared owner; graph generation cannot reassign units or spend shared magic.

JUDGEMENT: G6 Coordination — Codex, 2026-10-31: use existing public ally observations first;
explicit messages or a central blackboard are alternatives. The first coordination claim
rests on observation alone; communication requires a separate comparison and contract.

This example tests conditional progress. It does not test sophisticated flanking, optimal
timing or teamwork strength. If contact never occurs or cavalry cannot reach the target,
the case is unsuitable for that claim; fix the experiment specification before collecting
comparison data, rather than silently adjusting the success condition afterwards.

## Learning between battles and checkpoint attempts

JUDGEMENT: G7 Improvement unit — Codex, 2026-10-31: revise frozen artifacts between completed
battles first, then between checkpoint attempts. Editing during one live battle is the
alternative; the initial learning claim rests on the between-attempt boundary.

The proposed loop is concrete:

1. Freeze a task family, skill catalog, authoring prompt, generation budget and independent
   evaluator. Reserve development, selection and held-out families before generating graphs.
2. A coordinator declares roles and graph connections. Specialist LLM authors receive only
   their capability descriptions and required interfaces. Compose their outputs and run
   structural checks. Keep failed generations and repair costs in the record.
3. Run the candidate on the declared training battles, sequentially on this machine. Save
   every node transition, public source observation, order, engine acknowledgement, effect
   witness and final outcome. A graph reaching its success node cannot award itself a win.
4. A diagnostic reader identifies candidate failures, such as an attack selected after a
   target hid or a branch that kept cavalry idle. Distinguish missing skill, executor bug,
   bad plan, provider failure and ordinary defeat. A causal story needs a targeted replay
   or intervention; an LLM explanation alone is a hypothesis.
5. Authors propose a versioned graph/parameter change. Keep the skills, evaluator and test
   split frozen for this arm. Re-run component checks, then compare incumbent and candidate
   on the selection set under the declared budget. Retain the incumbent if the promotion
   rule is not met. Archive both artifacts and all failed candidates.
6. Stop at the predeclared iteration/game-time/cost bound or plateau rule. Freeze the selected
   graph before the held-out test. Report authoring, revisions and battle execution costs
   separately; never keep tuning on held-out feedback.

JUDGEMENT: G8 Revision authority — Codex, 2026-10-31: authors change graph wiring/parameters,
not skills, tests or scores in the first study; generated skill code is the alternative.
Attributing gains to graph improvement rests on keeping the catalog fixed.

JUDGEMENT: G9 Feedback access — Codex, 2026-10-31: authors initially receive public traces
and approved outcome diagnostics; privileged training diagnostics are a separate option.
Information fairness and transfer claims rest on the chosen feedback boundary.

An evaluator may inspect hidden state for an agreed check, but hidden fields, replay stills
and evaluation/setup/final blocks must not become live node inputs, messages or model context.
Privileged checks that change a live branch can leak information even when the raw field is
hidden. Keep such checks in the evaluator; live guards use the legal public observation.

### What checkpoint restoration makes feasible

WH3 checkpoints reconstruct the engine from replay inputs, then hand control back. They are
different from GaP's “checkpoints,” which are postcondition checks, not saved simulations.
The [WH3 limits](checkpoints.md#limits) include unreproduced real-time script timers and a
fresh bridge after restore. Declared Land/siege checks do not establish arbitrary cases.

| Loop | Feasibility and missing work |
|---|---|
| New whole battles, revise between them | Simplest initial route. Still needs the graph runner, revision driver and agreed evaluation |
| Restore one saved battle situation, try A, restore again, try B | Plausible later. Needs a restored continuous controller loop and a check for that specific situation, graph state and handover |
| Rehearse alternatives while the original battle continues | Not supported by the current single-controller machine. Would need separate synchronized game instances, compute and a valid transfer back to an advancing state |
| Reflect and change goals during a live battle | Possible controller extension without restoration, but consumes real battle time and is a different online adaptation experiment |

The existing `restore_episode` is a step-run helper, not a drop-in `play` for an arbitrary
team; `checkpoint_root` currently accepts only a `hold` source. Producing tactical roots
from an actively controlled battle needs an explicit source-run extension too. A future
adapter must join the restored public observation stream to the normal
policy lifecycle, suppress input before handover and preserve source time/identity. Rebuild
may run faster before handover under the existing exception; execution after it stays 1x.

JUDGEMENT: G10 Restored policy state — Codex, 2026-10-31: start a fresh graph from the public
handover view first; serialized member memory is the alternative. Checkpoint results would
measure fresh decisions from a situation, not continuation of the original controller.

If we later restore memory, save graph version, node invocations, skill state, model history,
random state, pending-order identity and message state separately. Never resume an HTTP
request as if it were part of the engine replay. Explicitly discard/reconcile pending work
and test that a late reply from the old attempt cannot reach the new one.

Repeated branches from one source battle are correlated. Put the entire source battle and
all its checkpoints in one data split; test transfer on different source battles. Replaying
the same situation can help diagnose a graph, but does not by itself establish learning
across battles. A graph that memorizes the checkpoint's timestamp is a concrete wrong result
the held-out design must expose.

## WH3 as a VA challenge

A WH3 analogue of VA fixes the map/mode, observation and action rules,
available unit types and opponent family; instances vary deployment geometry, composition
within bounds or starting battle situations. This is our proposed adaptation of VA, not
one of the paper's robotic benchmarks.

JUDGEMENT: G11 Task family — Codex, 2026-10-31: begin with one declared Land family and bounded
deployment variation; composition/opponent/map variation are later alternatives.
Generalization claims rest on the exact family, distribution and held-out split.

Candidate families, in increasing scope: coordinate line contact with a cavalry attack;
protect a ranged group while enemies change approach; keep cooperation working when a unit
routs and later rallies. Start only with a case whose required state and actions are exposed
and checked. Do not manufacture unrecorded hidden-state changes to make the task harder.
Deployment variation needs a repeatable setup procedure; the current menu scenario alone
does not establish that we can sample the desired distribution.

Separate familiar variations from withheld combinations, then from shifts such as an unseen
opponent policy. Keep seeds/setup recipes, opponent identity and side explicit. Unknown-map
generalization is a different claim from tolerance to different positions on one map.
Winning quickly is not automatically the right counterpart of robotic throughput: WH3
health/morale measures and outcome rules remain in the owner's
[benchmark interview](benchmark-implementation.md#owner-interview-one-land-battle).

## Comparisons and evidence of improvement

JUDGEMENT: G12 Comparison design — Codex, 2026-10-31: match skills/information and report
total development plus execution cost; matching only online calls is the alternative.
Claims about graph structure versus extra computation rest on the selected controls.

Use a staged comparison so an expensive full matrix is not required at the start:

| Comparison | Hold constant | What it isolates |
|---|---|---|
| Hand-written graph vs ordinary skills/commander | Same skill code, state and tactical goals | Runtime correctness and cost before testing LLM authorship |
| Direct two-member LLM team vs two live graph members | Ownership, views, models, allowed actions, helpers and total call/spend policy | The effect of a graph execution layer; report any unavoidable helper difference |
| One author vs coordinator plus specialist authors | Skill catalog, task and aggregate generation budget | Authoring decomposition; distinct from runtime member count |
| Initial generated graph vs revised graph | Skill catalog, runtime, selection/test splits | Benefit of between-attempt revision |
| Fixed public-state graph vs graph with live LLM goal updates | Same authored graph and scenario distribution | Value and latency cost of live adaptation |
| One runtime controller vs two group controllers | Whole army, aggregate resources, legal information and skills | Division of runtime control; defer until the graph layer itself works |

Report battle outcomes with their denominators, infrastructure/policy failures separately,
and the agreed health/morale measures when available. Diagnostics include time from a public
trigger to the corresponding engine effect, source-observation age at application, wrong or
stale orders, idle intervals, cancellation failures, model calls and dollars. These explain
behavior but do not replace the predeclared primary measure.

JUDGEMENT: G13 Statistical plan — Codex, 2026-10-31: primary measure, sample count, meaningful
effect, confidence method, promotion/stopping rules and failure handling remain undecided.
A small exploratory screen is an alternative to a powered study; strength claims await this.

Use independent source battles as the unit for uncertainty, with paired cases where reset
checks justify pairing. Do not count frames, nodes or repeated branches as independent
battles. Randomize declared run order to limit time/build effects; do not quietly replace
losses or failed generations. Choose counts from the effect worth detecting and observed
variation, then register them before the scored run. The bounded budget must cover authoring
and failed candidates as well as final graph execution and both games' existing ledger use.

## Proposed checks and delivery sequence

Every row needs its own behavior card and owner discussion before it becomes an agreed
verification method. The independent reference is the stated contract or engine witness,
not a saved output from the implementation being tested. A deliberate wrong implementation
must fail the important checks. No new entry is added to agreed-checks.md by this plan.

| Step and deliverable | Repeatable check and independent reference | Wrong version it must catch; limit |
|---|---|---|
| 0. Agree the smallest graph/controller/skill contract | Walk the two-member example through explicit public observations and expected transitions; pin the GaP donor files below | A graph calling an undeclared skill or treating `hold` as strict immobility; this is specification review only |
| 1. Document the existing controller interface and add a graph skeleton | Offline adapter checks: scripts, fixed graphs and mixed members use the same lifecycle, ending and feedback rules; fake ledger tests share a single cap | A new graph type bypasses spend accounting, shares episode memory or loses a member's feedback; no tactics claim |
| 2. Implement only approved node types and required skill adapters | Tiny hand-computed graphs for routing, typed data, no target, movement status, bounded loops and cancellation; use fresh sequence/time fixtures | Ack sets `succeeded` without movement; old output feeds a new invocation; a skill name loads arbitrary Python |
| 3. Exercise two graphs through TeamPolicy offline | Hold one member/model future behind an event while the other emits and receives feedback; reverse roles; hide a target and change battle identity | Global graph barrier, cross-owner order, hidden-field leak, late reply in a new battle; offline concurrency is not live movement |
| 4. Run a zero-model live graph check after agreement and a game window | Fresh launches at 1x: controlled moves with no-order controls, correct identities and engine effects; then the contact/charge example with explicit witnesses | False arrival from idle drift, target mismatch, charge branch firing before contact, fast member blocked by slow member; does not establish policy strength |
| 5. Add multi-LLM graph authoring and live LLM members separately | Canned author replies test assembly/rejection; immutable artifact hash and budget accounting; then a bounded live smoke using the agreed checks | Author silently changes evaluator, missing capability accepted, model reply overrides wrong member; smoke is not learning evidence |
| 6. Add between-battle revision and a small declared comparison | Replay saved training evidence into candidate selection; poison held-out inputs and scorer-write attempts; recount every attempt/cost independently | Test leakage, dropped failed generations, promotion on training-only gains; scored claim waits for G13 |
| 7. Add checkpoint attempts only if whole-battle cost warrants them | Rerun the relevant agreed restore check; identical-action restores plus changed-order control, public handover readings and clean graph state | Matching checksums but wrong public fields, stale memory/reply, pre-handover orders; limited to checked cases |
| 8. Extend to native allied armies after multiplayer prerequisites | Per-peer identity/authority, visible information, independent progress, order replication and common ending checks, with raw peer evidence | A locally accepted order absent at another peer, private ally data leak, cross-army control; single-client evidence cannot pass this |

For steps 2–3, explicitly perturb `evaluation`, hidden enemy rows, teammate private state and
final/setup fields while holding the legal view constant. The graph's outputs must remain
unchanged. Check that missing witnesses produce unknown/failure, never an invented success.
For stateful nodes, test rout/rally, dead targets, a newly appearing unit and a battle ending
while a model request is still running, against the declared ownership/reset contract.

Preserve raw failures. Run focused offline checks while developing and `scripts/check.py`
before each commit. Once component checks pass, the next evidence is the agreed live
procedure, not more fixtures repeating the implementation. Do not change an agreed checker
or its thresholds to get a pass.

## Extending from one army to allied armies

Keep the graph contract independent of whether a member owns a group or an army. Extend the
authority context explicitly with match, peer, alliance, army and member identities; unit
IDs alone are not safe across clients. One local runtime remains responsible for each
client's order submission. Observing an allied unit never grants permission to order it.

JUDGEMENT: G14 Team architecture — Codex, 2026-10-31: independent graphs per army with bounded
messages are the later candidate; a central joint graph is the alternative.
Decentralization, communication cost and resilience claims rest on this choice.

A later message can say “my line is engaging enemy E,” with sender, match, source battle
time, expiry and an allowed public target reference. It conveys a teammate report, not an
engine fact. Messages must not wait at a global barrier or carry private orders/evaluation
data accidentally. Deciding whether allied vision is shared, who owns army resources,
what may be communicated and what happens on disconnection belongs to the multiplayer
information/authority contract, not to a convenient shared Python dictionary.

Follow [native-multiplayer.md](native-multiplayer.md#step-by-step-delivery): prove native
matches and passive observations, order replication, authority and lifecycle before an LLM
study. Current move-only support cannot establish attack/charge graph behavior. Expand and
check each needed action before enabling it. Native allied armies come before four-client
2v2; results must reconcile peer outcomes and report desynchronization as infrastructure
failure. A single-client allied-AI experiment, if used, gets its own label and cannot stand
in for several independently controlled armies.

Native checkpoint restoration remains separate research: the current tool does not restore
peer sessions, membership or synchronized handover. Start team experiments from fresh
matches, consistent with the owner's existing preference to avoid multiplayer checkpoints.

## Risks and reasons to stop or narrow the work

| Risk | Concrete response |
|---|---|
| Most gains come from better hand-coded tactics | Share skill code across baselines and compare with a hand-written graph and existing commander |
| Graph waits become another source of delay | Require the independent-progress test and measure engine effect age, not merely graph throughput |
| Success predicates reward the wrong thing | Separate public runtime guards from evaluator witnesses; challenge with wrong-target and no-effect controls |
| Generated code bypasses authority or leaks data | Initial graphs select approved operations only. GaP imports Python scripts even during validation; type checking is not a sandbox |
| A rigid graph cannot handle moving opponents | Test target loss, rout/rally and delayed replies; compare fixed graphs with bounded live goal updates |
| Improvement overfits one checkpoint/opponent | Split by source battle and opponent family; freeze before held-out evaluation |
| Rehearsal consumes excessive game time or money | Sequential bounded attempts, account for failed generation and revision; no assumed parallel simulator fleet |
| GaP software differs from the paper | Pin inspected code/docs; distinguish structural repair from demonstrated rehearsal optimization |
| The proposed contribution duplicates prior work | Before a thesis claim, compare with behavior trees, reactive plans, options and dynamic multi-agent graph control; current reading is not an exhaustive novelty search |

If ordinary shared skills match the graph under the declared budget, a negative result is
useful; it is not a reason to add complexity without a new hypothesis. If the live skill
witnesses fail, fix or narrow those contracts before asking models to optimize over them.
If native replication is not established, keep the result scoped to split-army control.

## References

Primary sources inspected 2026-10-31; external tests and robotics results were not reproduced.
The research collection entry is in [papers.md](../thesis/papers.md#gap-graph-as-policy-for-variational-automation).
Source checkouts and the review/check report live under `runs/gap-plan-20261031/` (ignored).

- [Paper v1](https://arxiv.org/html/2607.05369v1), [project](https://graph-robots.github.io/gap/),
  [docs](https://graph-robots.github.io/graph-as-policy/).
- GaP code pin: `71549e1584839337eb355c280e7b1e50c805b8c7`.
  Use [gap/agent/multi_agent.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/agent/multi_agent.py)
  for coordinator/subgraph assembly, validation repair and separate postcondition authoring;
  [tests/agent/test_pipeline.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/tests/agent/test_pipeline.py)
  for canned-response pipeline tests. Adapt the separation; do not let authors control scores.
- [workflow.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/runtime/workflow.py),
  [validate.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/runtime/validate.py),
  [schema docs](https://graph-robots.github.io/graph-as-policy/reference/workflow-schema.html):
  follow explicit graph structure and typed bindings. Unknown-tool warnings and script
  imports in GaP are reasons to define a stricter WH3 approved-operation subset.
- [executor.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/runtime/executor.py),
  [executor docs](https://graph-robots.github.io/graph-as-policy/reference/executor.html),
  [test_executor.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/tests/runtime/test_executor.py):
  reference routing, scope and failure tests. Regular nodes complete a super-step before
  its successors advance; cross-subgraph inputs resolve by latest producer name. WH3's
  resumable independent members and explicit producer identities deliberately differ.
- [GaP checkpoint docs](https://graph-robots.github.io/graph-as-policy/running/checkpoints.html):
  postconditions checked against simulator truth. Missing sidecars may be skipped and
  enforcement has off/warn/raise modes. WH3 verification must require the named witnesses;
  these checks are not an engine save/restore facility.
- [gap/benchmark/__init__.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/benchmark/__init__.py)
  explicitly describes one-shot generation without rehearsal/refinement in that harness.
  The inspected generation repair loop is structural repair. Do not promise a ready-made
  implementation of the paper's full self-learning loop; map further code before reuse.
- Open Robot Skills pin: `752dfbd96968d4d08379f8111765efbf6457800b`.
  [transporting-objects/SKILL.md](https://github.com/graph-robots/open-robot-skills/blob/752dfbd96968d4d08379f8111765efbf6457800b/skills/transporting-objects/SKILL.md)
  and [authoring docs](https://graph-robots.github.io/graph-as-policy/skills/authoring-bundles.html)
  show capability descriptions, typed inputs, named exits, allowed tools and canonical scripts.
  Mirror the documentation pattern; robot motion/perception implementations do not apply.
  The repositories declare Apache-2.0 licensing; preserve attribution/license notices for
  any later copied code and inspect individual bundles and third-party terms then.

The first implementation decision is G2 with the small contract in step 0. G3–G6 determine
that slice; G7–G13 determine later research claims. G14 waits for native multiplayer.
