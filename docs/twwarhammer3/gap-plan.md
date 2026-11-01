# GaP graph controllers for WH3

Implementation authorized 2026-10-31: bounded existing-tactic library, interchangeable
controllers and initial offline/live checks; up to $5 using cheap Anthropic calls.
The owner approved the scope and check method; benchmark comparisons stay deferred.
The owner asked for a GaP research
reference and a concrete plan for one army with several LLM controllers, then several allied
armies. Code read at `35dbeab`; outside sources are pinned under [References](#references).

Initial release implemented at `d6dfe92`: the bounded library, interchangeable controller
composition, independent graph members, multi-LLM authoring and between-battle revision.
The agreed component/live checks and two authored whole-battle smoke runs are recorded in
the [log](log.md#2026-11-01-complete-the-initial-gap-author-battle-revision-smoke).
Live holding/firing, tactical strength and learning remain unverified.

## In short

GaP ([Chen et al., July 2026](https://arxiv.org/html/2607.05369v1)) has LLMs write a robot's
policy as a graph of skills, a flowchart such as "find the can → grasp it → place it in the
basket", which an executor runs. The LLMs improve the graph by rehearsing it in simulation.

It is worth a bounded experiment in WH3: a graph keeps a plan running while models think,
makes recovery steps explicit and shows which decision led to each order. The open question
is whether that helps when units move, targets vanish and teammates become unavailable. The
risk is a graph that carries out a bad plan very reliably. First establish whether it works
here; comparisons with other methods and formal learning claims come later, through the
repo's benchmark. The owner also wants to observe how graphs improve across battles.

The plan, in order:

1. Plan and build a broader WH3 skill library as a separate, bounded piece of work, using
   MORSL as a design reference. Settle its first release's scope and checks before building it.
2. Two controllers on one army, each owning its own units, using the existing controller
   interface and team dispatcher. Start with independent progress and observation alone.
3. A hand-written graph, then graphs written by several LLMs, then graphs revised between
   whole battles. Authors use a frozen, pre-built library and permitted information only.
4. Allied armies once native multiplayer passes its own checks, starting with separate graphs.
   Battle restoration is deferred and is not a prerequisite for this step.

The owner chose the initial approach for G2, G3, G6–G9, G12 and G14; alternatives remain
possible later experiments. G4 delegates common-sense starting parameters to the implementer,
to record and tune. G5 chooses the broader library first but leaves its boundary to separate
planning. G11 chooses a narrow start; the exact battle family is still open. G1's research
comparisons, G10's restoration choices and G13's benchmark design are deferred. These were
planning answers; subsequent implementation authorization, G5 scope and check agreement are
recorded under [First release](#first-release-approved-scope-2026-10-31).

## What GaP is and what carries over

A coordinator LLM splits the task and specialist LLMs write subgraphs from a skill library
(MORSL, the Modular Open Robot Skill Library). The composed graph is type-checked and run;
before deployment, rehearsal in simulation finds failing nodes and revises the graph. The
task class is Variational Automation (VA): one job done reliably across many varied instances,
such as objects of different shapes in different poses. Paper sections 3–4 define VA and the
method; Appendix E gives the rehearsal loop.

The paper calls its tasks quasi-static and leaves moving targets to future work
([section 6](https://arxiv.org/html/2607.05369v1#S6)). WH3 adds opponents that move and react,
and partial visibility. Testing that extension would not by itself show novelty or an
advantage.

### Three activities and later research questions

"Multi-agent GaP" can mean three different things. These labels describe what runs; they
do not require three separate studies before the first working system:

| Activity | What the LLMs do | What runs during the battle | Possible later question |
|---|---|---|---|
| Authoring | Before battle, a coordinator and specialist LLMs write graphs for the army groups | Frozen graphs, one per group | Whether structured authoring writes better reusable policies |
| Live control | During battle, each group's LLM picks goals or parameters from a bounded menu | The graphs keep running while each LLM thinks | Whether graphs help several live controllers cope with change |
| Revision | Between battles, LLMs revise the graph from finished training attempts | The next attempt's new frozen graph | Whether experience improves results on held-out battles |

Only live control is sure to have several LLMs controlling the battle. Authoring also gives
each group its own controller, but that controller is a frozen graph whose authors may have
stopped. So never label one experiment as another, and never credit an improvement to live
multi-agent control just because several LLMs wrote the graph.

Owner, 2026-10-31 (G1): "For now I guess I just want to see if it works here." Comparing
methods for live control and observing learning across battles are later interests; more
specific research choices wait.

JUDGEMENT: G1 Research claim — deferred by the owner, 2026-10-31: separate or combined studies
of authoring, live control and revision remain undecided. Later attribution claims rest on
that design; the initial work establishes feasibility only.

## What already exists

Read from source at `35dbeab` and confirmed by a second, independent read; this is not a new
live check. Agreed checks on these pieces count only at the revisions and for the cases
[agreed-checks.md](../agreed-checks.md) records.

| Piece | What it gives us | What this plan still needs |
|---|---|---|
| [controllers.py](../../src/twwarhammer3/battle/controllers.py) `controller_class`, `factories` | `decide(observation)`, `acknowledge(ack, latency)`, `metadata()`; a fresh controller per episode; loading an external `module:Class` | A written, type-checked contract, not a new framework. Paid calls and prompts are wired up for named built-ins only, not automatically for external classes |
| [team.py](../../src/twwarhammer3/battle/team.py) `TeamPolicy`, `project` | Exactly two members, each with a copied view, ownership checks, independent completion and its own feedback | No teammate messages. `ModelTeam` fixes both members to one model and effort and to the Knights/rest split; nothing more general is built |
| [skills.py](../../src/twwarhammer3/battle/skills.py) `RULES`, `Skills` | Persistent `engage`, `shoot`, `hold`, `charge` and `move` assignments | They return orders and a phase description, not a typed start/running/succeeded/failed/cancelled status |
| [commander.py](../../src/twwarhammer3/battle/commander.py) `CommanderPolicy` | A fast skill executor keeps acting while a model plans in the background | A scheduling reference and baseline; it assumes the whole army, so a member's view needs an adapter |
| [play.py](../../src/twwarhammer3/battle/play.py) `_drive` | One transport writer, validation, acknowledgements, traces, battle endings | `decide` is synchronous here: a graph must return promptly, not wait inside it for movement or a model |
| [checkpoint.py](../../src/twwarhammer3/battle/checkpoint.py) | Rebuilding a battle from replay inputs, scripted input at chosen ticks; `restore_episode` runs a step with at most one injected batch | No graph or team running continuously after a restore; Python memory is not restored |
| [worker.py](../../src/twwarhammer3/engine/worker.py), native battle mode | Offline multiplayer plumbing | Worker control accepts only unqueued moves (it rejects even an explicit `queue: false`), so current skills do not plug in. No live native multiplayer battle yet |

The current team's unit split, target filter, age rule and cleanup carry their own JUDGEMENT
markers in [multi-agent-implementation.md](multi-agent-implementation.md#choices-settled-for-now-2026-10-28).
Any comparison using that team rests on them; this plan does not settle them.

## Controller design

Owner, 2026-10-31 (G2): "use our existing controllers and team dispatcher". Inspect the GaP
repository for reference and ideas; implement a WH3 graph adapter through our existing
interfaces. The pinned donor files are under [References](#references).

A graph controller is one more kind of controller:

- **Interface.** Document the contract controllers already follow (required and optional
  methods, exception behaviour, how feedback finds its decision), perhaps as a small Python
  `Protocol`. Scripts and direct LLM controllers must not have to pretend to be graphs.
- **Factory.** Choose controller type, model, skill catalog and graph file separately; pass in
  the shared ledger and transport; build fresh state each episode; keep existing names and
  behaviour.
- **Team.** `TeamPolicy` still splits units and sends orders; each member sees only its
  projected view, returns ordinary orders and gets only its own feedback. A member can be a
  script, a direct LLM, a fixed graph or an LLM steering a graph, so mixed pairs help diagnose
  problems without touching the transport. More than two members comes later.

Where the code would go, each piece created only when a step needs it:

| Location | Job |
|---|---|
| `battle/controllers.py` | Pick factories, record the full controller identity, keep budget and provider checks |
| New `battle/graph.py` | Load and validate a graph, track node runs, advance ready work, return orders |
| `battle/skills.py` plus a small adapter | Approved WH3 skills and their observable status; tactics shared with the baselines |
| `battle/team.py` | Unit ownership, independent dispatch and feedback; a graph-only dispatch guard, later explicit member factories |
| New `configs/twwarhammer3/graphs/` | Reviewed, immutable graphs and skill descriptions, only for planned experiments |
| A later offline authoring/revision command | Write candidate graphs from training evidence; never edit the running policy or the scorer |

The code stays in WH3 until another game needs it. GaP stays an optional controller family:
`hold`, `llm_rules` and ordinary team play do not depend on it.

### Running a graph in a moving battle

Owner, 2026-10-31 (G3): "for the initial implementation we can stick with the independent
progress approach." Comparing independent progress with rounds that wait for every node
can come later. The mechanics and checks below remain proposed contracts.

GaP advances its regular nodes in lockstep rounds ("super-steps"): the next round starts only
when every node in the current one has finished, so a node waiting for contact holds up its
whole round. Instead:

- **Nodes resume.** A node has a kind, typed inputs and outputs, and named exits; start with
  approved skills, public-state conditions, branches and bounded loops. A running skill
  reports its status on each new observation, so one member's wait never stops the other.
- **Every value has a known source.** Control edges say what runs next; data edges say where
  an input came from. Each value records its producer, battle and episode, graph revision,
  node run, and its source observation's sequence and time. Missing producers and ambiguous
  bindings are rejected.
- **`decide` returns quickly.** Each call reads feedback, refreshes public conditions,
  advances a bounded amount of ready work and returns orders. Model requests run in the
  background; a late reply changes a goal only if the node run that asked is still live.
- **Acknowledged is not done.** An acknowledgement means the order arrived or was accepted. A
  node succeeds only on its skill's witness, separate evidence from the game such as the unit
  nearing its point. A queued order counts once it takes effect, not when queued.
- **Recheck before sending.** On the latest view, recheck target visibility, unit ownership
  and the skill's preconditions. Things can still change in transit, so the engine stays the
  final legality check. Each order keeps its source observation time, so its age can be
  measured. Deadlines and order age use battle time; model latency measurements must allow
  for the known WSL clock drift. Battles stay unpaused at 1x.

This needs one addition to `team.py`. `TeamPolicy._validate` checks orders against the view
the member decided on, not the current one, so a graph checking inside its own `decide` is
not enough. Under G3, add an optional dispatch guard for graph members:

- when the dispatcher picks a ready graph batch, the guard rechecks it on the latest
  `project()` view;
- if a precondition fails, nothing is sent and the graph gets local refusal feedback so it
  can choose again;
- the batch keeps its original source time and identity: an old decision is never relabelled
  as fresh.

Direct controllers keep today's validation, and comparisons must state that difference. Test
case: a target hides after the member's worker finished but before the dispatcher picks the
batch.

Owner, 2026-10-31 (G4): "You can set some common-sense values initially." Choose and record
starting order-age limits, loop limits, retries and fallback behaviour with the skill and
controller contracts when implementation is authorized. Treat them as an experimental
baseline to tune, not established best values or agreed verification thresholds; this does
not require another owner decision for each initial value.

JUDGEMENT: G4 Baseline parameters — delegated by the owner, 2026-10-31: initial limits and
fallbacks remain to be set and marked at their sites. Longer waits or different retries
and fallback orders change tactics; comparisons rest on the recorded settings.

Stopping a Python task does not stop an order a unit already has: record whether a cancel or
replacement order was sent and acknowledged, and claim a unit stopped only with a witness.
When a battle ends, record unsent work and ignore late replies; nothing sends once a new
episode owns the transport. In the first design, a new graph version starts only between
attempts.

### The skill catalog

Owner, 2026-10-31 (G5): "We should build a broader library first", using MORSL as a
reference, and "This is a step that will need to be tackled separately" because its
complexity can grow without a useful stopping point. This replaces the minimal-catalog-first
proposal. G8 then freezes the resulting pre-built library for graph authoring and revision.

MORSL's robot code does not transfer; its organization and documentation are references:
a short description for the coordinator, and detailed inputs, exits and examples for the
specialist. Inspect the pinned skill bundle and authoring docs under [References](#references)
when planning the WH3 library. Reuse existing WH3 capabilities where suitable.

The separate scope plan should identify a finite first release: which capabilities the
initial Land cases need, what existing code can supply, what needs new work, and what waits.
It should give each included skill a contract and independent evidence of its effect, plus
an effort bound and completion rule for the release. These details remain to be settled;
the six entries below are a starting inventory, not the chosen boundary of the broader
library. A small diagnostic graph can exercise part of that library without defining its
whole scope. Do not grow the catalog merely because another tactic is imaginable.

JUDGEMENT: G5 Library boundary — open after the owner's broader-first choice, 2026-10-31:
the first release's skills, tactical depth and effort bound await separate planning.
A larger catalog changes build effort and baseline strength; experiments rest on its scope.

Each skill records:

- which units may use it, and its public inputs and their types;
- its entry conditions and the orders it may send;
- its exits (running, succeeded, failed, cancelled) and its timeout and retry rules;
- what it does when its target hides, dies or routs;
- a separate engine witness for success.

Data lookups and evaluation stay out of a skill's policy input; its code and description are
versioned together.

| Skill | First contract to settle | Evidence beyond an acknowledgement |
|---|---|---|
| `observe_contact` | Read visible enemies and friendly contact state; no orders | Known contact and no-contact cases, including a hidden target; no evaluator-only field decides a branch |
| `move_to` | Move owned units toward a public point and keep watching | Position nears or reaches a declared region; a no-order control rules out idle drift; arrival radius and deadline need agreement |
| `engage_visible` | Attack a visible enemy; yield if visibility or ownership changes | Right target, and contact or effect where observable; a vanished target did not necessarily die |
| `hold_area` | Stay near a point with an explicit allowance to engage | Position and movement against the allowance; today's `hold` may attack nearby enemies |
| `charge_when_engaged` | Charge a visible enemy already in melee | Movement, contact and chosen target; today's `charge` is not a general flank planner and does not prove a charge bonus |
| `shoot_visible` | Fire an owned ranged unit at a visible target | Firing, ammunition and target evidence, with a control for unrelated shots; an order does not guarantee damage |

Inputs are structured references (owned-unit IDs, visible-enemy IDs, world points), not free
strings. Type checks still cannot prove reachability, good tactics, visibility when the order
runs, or a path clear of friendly units; those stay runtime concerns.

### First release: approved scope, 2026-10-31

The owner answered "Use this bounded scope": the five existing tactics plus contact and
target selection, with public-state statuses. This settles G5 for the initial release;
the earlier open marker records the planning state before that answer. No new flanking,
formation, spell, purchase, multiplayer or restore skills belong to this release.
Bound: one adapter over existing tactics, one graph runner and the checks below; extend
only to fix a demonstrated contract failure. Freeze library source and descriptions before
model authoring. Delivery ends after authoring/revision and a bounded feasibility check,
without selecting a benchmark score, promotion rule or claiming learning.

| Operation | Inputs and exits | Public witness / limit |
|---|---|---|
| `owned` | none; succeeded/empty; outputs owned active unit IDs | Full own-unit list minus destroyed, routing or shattered units |
| `select_target` | owned IDs; succeeded/empty; outputs one visible target ID | Nearest eligible visible enemy; `engaged` mode requires enemy melee state |
| `contact` | none; yes/no | Any visible friendly, ally or enemy in melee; hidden enemies cannot trigger it |
| `move` | owned IDs, point; succeeded/failed/cancelled | All selected units inside the existing tactic's arrival radius |
| `hold` | owned IDs, point; same exits | At post after the retry interval; may engage nearby enemies, never means immobility |
| `engage` | owned IDs, visible target; same exits | All selected units observed in melee with that target |
| `charge` | same | Target already in melee before dispatch, then own melee with it; no charge-bonus claim |
| `shoot` | same, with ammunition | Ammo decreases between consecutive readings of the selected target; no damage attribution |

The adapter pins attack target identity rather than substituting another target. An absent,
dead, routing or shattered target fails; rout of an owned unit also fails, then a later
`owned` node can include it after rally. New owned units join at the next selection.
Acceptance never completes a skill. A local cancellation sends no halt and claims no stop.
Missing effects fail at the battle-time deadline. Parameters rest on JUDGEMENT
`battle/skill_contracts.py` G4 Skill limits and `battle/graph.py` G4 Graph limits.
These are component contracts until the live check passes at a recorded revision.

Controller composition uses `play --policy configured --controller-config FILE`.
The file contains `{ "type": "graph", "graph": GRAPH_OR_RELATIVE_PATH }`, a leaf such as
`{ "type": "hold" }` or `{ "type": "llm_rules@claude-haiku-5-5/low" }`, or a `team` with
exactly two named `members`. Each member supplies `unit_types` (list, or null for the rest)
and `controller`; optional `army_owner` names one member. The provider and ledger are the
job's. Resolved graphs, prompts, member identities and source hashes are recorded; instances
are fresh per episode. Configured controllers remain optional; existing policy names work.
Ownership, visibility filtering and feedback rest on JUDGEMENT in
[multi-agent-implementation.md](multi-agent-implementation.md#choices-settled-for-now-2026-10-28).

Graphs have `version: wh3-graph-v1`, `entry` and named `nodes`. Each node declares `op`,
`inputs` and a `next` map covering every exit; `end` has no successors. Inputs are typed
literals or `{ "ref": "producer.field" }`. Every input path must execute its producer
successfully. Repeating a consumer requires a new producer run; stale values fail explicitly.
There is one active node per member and one transition per new observation. Branches and
bounded loops therefore yield to the dispatcher. Every transition logs battle identity
(the episode identity), graph hash, node run, public observation and input provenance.
Orders keep their original source sequence/time; the optional dispatch guard rechecks the
latest projected view. Direct controllers keep their existing validation behavior.
The hand-written example is `configs/twwarhammer3/graphs/contact-team.json`; it composes
`contact-line.json` and `contact-cavalry.json` with the existing Knights/rest split.
To replace a member's graph with a script or direct model, change only its `controller`.

The initial live check is `tests/twwarhammer3/graph/check_wh3_graph.py`: three fresh
launches on the existing `emp-knights-emp-swordsmen` diagnostic. First the cavalry gets
no orders, then a graph moves it forward to a waypoint, then the two hand-written graphs
engage and charge. Raw positions must establish arrival after an accepted move and no
arrival in the control. A cavalry attack must name an enemy already in melee in its
source view; later raw melee must name that same target. Graph completions must match
those raw witnesses. The control must cover the move's actual time to arrival.
Recount also checks fresh battle identities, ownership, acknowledgements, cleanup and
1x through the engine speed flag plus the owner's whole-interval Windows-clock band.
Its launch geometry and wall caps rest on JUDGEMENT `check_wh3_graph.py` Probe bounds.
This does not check live holding/firing, a charge bonus, tactical strength or learning.

### Live target preferences

The optional `graph_llm` controller asks a model for one visible target ID or `none` while
its fixed graph keeps running. A preference only affects a later `select_target` node,
within that node's current eligible set. Otherwise the graph uses its existing nearest
target. An active skill keeps its target until its own witness, deadline or refusal.
The model cannot edit graphs or skills, send orders, reassign units or read hidden state.

Each request has a separate goal-run identity, controller UUID, graph hash, battle,
owned-unit context and public source observation. The caller adopts replies; model workers
only ask and parse. Close, source expiry, ownership changes and stale targets discard
replies. New episodes construct fresh controllers. Mixed graph/model teams and root policy
rotations share the job's Ledger. Exchanges and charges remain recorded during cleanup.
Scheduling, expiry and network limits rest on JUDGEMENT `graph_goals.py` G4 Goal limits;
the opt-in network timeout applies to each read, not the whole request's wall duration.

`configs/twwarhammer3/graphs/contact-goals-team.json` uses the existing two contact graphs.
JUDGEMENT: Goal example — Codex, 2026-11-01, G4 delegated starting values: Haiku 5.5,
low effort and at most two goal requests per member per episode. Other models or caps
change cost and opportunities to steer; this is a bounded example, not a comparison.
Use it with `play --policy configured --controller-config PATH --provider anthropic
--budget-usd 5`, adding normal scenario/output arguments. A missing ledger is refused;
the cap includes prior jobs. This example has not run live.

The proposed check covers delayed/stale replies, cancellation, eligibility, independent
team progress, shared budgets and trace provenance with canned models and planted errors,
then a bounded fresh 1x two-target dispatch probe. The owner's answer on that new method
is pending; the feature is unverified and no dependent live probe has run.

### Authoring and revision command

`graph-author` runs one coordinator and one specialist per member, using the existing
provider transport and one shared ledger. The first release authors two-graph teams;
ordinary runtime composition still accepts graphs, scripts and direct model members.
The coordinator receives the public task, fixed ownership and skill summaries. Each
specialist receives the detailed frozen library and its own prior graph and permitted
feedback. Model replies contain graph JSON; they cannot change Python skills or ownership.
Author v3 also accepts `graph_llm` templates and preserves their model/task/request limits;
authors can only replace their graphs. Older artifacts remain immutable and require their
original library/revision; they are not silently accepted under the changed source pin.

```bash
uv run --locked python -m twwarhammer3 graph-author \
  --task 'The line engages visible enemies; cavalry waits for contact then charges.' \
  --provider anthropic --model claude-haiku-5-5 --budget-usd 5 \
  --output runs/twwarhammer3/gap/initial
uv run --locked python -m twwarhammer3 play --policy configured \
  --controller-config runs/twwarhammer3/gap/initial --episodes 1 \
  --scenario emp-knights-emp-swordsmen --output runs/twwarhammer3/battle/gap-initial
uv run --locked python -m twwarhammer3 graph-author \
  --task 'The line engages visible enemies; cavalry waits for contact then charges.' \
  --provider anthropic --model claude-haiku-5-5 --budget-usd 5 \
  --previous runs/twwarhammer3/gap/initial \
  --evidence runs/twwarhammer3/battle/gap-initial/episode-0000 \
  --output runs/twwarhammer3/gap/revised
```

The budget is the selected provider ledger's cumulative cap, not a fresh allowance per
command. The default is the existing WH3 ledger; a missing ledger is refused. Paid CLI
authoring requires committed runtime sources. Initial generation and revision each write a
new directory: `controller.json`, a manifest, prompt/schema snapshots and model exchanges
containing every attempt, rejected reply and cost. A failed generation stays failed;
neither its existence nor a successful graph compilation means a battle was won.

Use the artifact directory as `--controller-config`. Both directory and generated-file
loading check readiness, controller bytes, authority and the frozen library before building
fresh episode state. Revision also checks that the completed whole battle ran the parent
candidate and its library. Changed or partial artifacts are refused. No running graph is
edited, no candidate is promoted automatically, and no scorer or held-out set is selected.

Revision context uses only projected member input views, own ordinary orders and own
acknowledgements. The coordinator gets no battle evidence. Hidden result/evaluator/setup
fields, teammate orders/queues and teammate feedback stay out of specialist context.
An engine ending gates whether the evidence is complete; its outcome and private diagnostics
never reach the authors. Source file hashes and retained/truncated counts stay in the audit
manifest. The context and repair limits rest on JUDGEMENT `battle/graph_author.py` Author limits.
New artifacts may be unchanged; a revision is not evidence of learning or improvement.

## A first test graph

Inspect recorded executions with the offline viewer (no game or model call):

```bash
uv run --locked python -m twwarhammer3 graph-view \
  runs/twwarhammer3/battle/gap-initial-02-20261101 \
  runs/twwarhammer3/battle/gap-revised-01-20261101 \
  --output runs/twwarhammer3/reports/gap-20261101.html
```

Open the HTML file in a browser. Select a member, seek by battle time or step through
events. The graph is the recorded configuration; unit positions come from public trace
observations without interpolation. Orders, engine acknowledgements and node results have
their own events and source rows. A ready successor has not started yet. The view preserves
source observation time and the later collection/dispatch/application bounds; it does not
reconstruct exact Python execution times, infer missing witnesses or score graphs.

This graph tests the machinery, not strength. It uses the current team split: `cavalry` owns
the Knights, `line` every other unit.

```text
line:     pick visible target -> engage -> observe -> pick again
cavalry:  observe contact -> eligible target? -> charge -> observe again
               ^                  |
               +---- no target ---+
```

The line engages a visible enemy. The cavalry waits for observed contact, then charges an
eligible visible target, while the line keeps acting. If the target disappears, the cavalry
chooses again; if none is visible, it sends nothing rather than inventing one. This is close
to the existing charge rule, so a problem points at the graph, not at new tactics.

Arrows advance on a new observation or finished local work, never in a blocking Python loop.
At first both members see the current allowed ally view and send no messages. In the live LLM
version, each member's LLM picks a target preference or goal from a bounded menu while the
graph keeps checking conditions. Army-wide authority stays with its declared owner; graph
generation cannot reassign units or spend the shared magic.

Owner, 2026-10-31 (G6): "we can start with observation alone." Messages or shared notes
remain possible later experiments, with their own information contract and comparison.

This tests conditional progress, not flanking, timing or teamwork strength. If contact never
happens or the cavalry cannot reach a target, the case cannot answer the question: fix the
experiment's definition before collecting comparison data, never quietly change the success
condition afterwards.

## Learning between battles

Owner, 2026-10-31 (G7): "We can start with the simpler approach" and consider live graph
edits later. Start with graph revisions between completed whole battles. Checkpoint attempts
are deferred under G10, rather than an automatic next stage. Changing a goal within a fixed
graph is distinct from editing the graph itself.

The loop below describes the eventual revision study. Initial work should show that the
system can run and revise graphs, retaining evidence across attempts. Selection, held-out
testing and claims of learning wait for the benchmark choices in G1 and G13; these steps
do not settle those choices or authorize a battle cohort.

1. **Freeze the setup:** task family, skill catalog, authoring prompt, generation budget and
   independent evaluator. Set aside development, selection and held-out families before
   generating any graph.
2. **Author.** A coordinator declares roles and connections; each specialist LLM sees only its
   skills' descriptions and required interfaces. Compose the parts and run structural checks,
   keeping failed generations and repair costs on record.
3. **Run training battles** one at a time on this machine, saving every node transition,
   public source observation, order, acknowledgement, effect witness and outcome for audit.
   Author inputs use only permitted fields and explicitly permitted outcome summaries;
   evaluator-only evidence stays separate. A graph's success node does not count as a win.
4. **Diagnose from permitted evidence.** A reader lists likely failures (an attack chosen
   after its target hid, a branch that left the cavalry idle) and sorts them: missing skill, executor bug, bad plan,
   provider failure or plain defeat. An LLM's explanation is a hypothesis; a causal claim
   needs a targeted replay or intervention.
5. **Revise and select.** Authors propose a new graph or parameter version; skills, evaluator
   and splits stay frozen. Re-run component checks, then compare incumbent and candidate on
   the selection set within budget. The incumbent stays unless the promotion rule is met.
   Archive both and every failed candidate.
6. **Stop and test** at the declared limit on iterations, game time or cost, or at the plateau
   rule. Freeze the chosen graph before the held-out test, never tune on held-out results,
   and report authoring, revision and battle costs separately.

Owner, 2026-10-31 (G8): "We can start with a frozen, pre-built skill library." Graph authors
can revise wiring and parameters within its contracts. Skill code, tests and scoring stay
outside their authority; generated skill code is a possible later research question.

Owner, 2026-10-31 (G9): "stick with permitted information only." This applies to authors,
revision feedback and live controllers. The initial design gives authors no privileged
training diagnostics; any outcome summary supplied to them needs an explicit permitted
definition, not a copy of evaluator-only fields.

An evaluator may read hidden state for an agreed check, but hidden fields, replay stills and
the `evaluation`, `setup` and `final` blocks never reach live nodes, messages, graph authors
or revision model context. Even a privileged check that only picks a live branch or tells
an author which branch failed can leak information. Such checks stay in the evaluator;
live guards and author feedback use only permitted information.

### What checkpoints make possible

Owner, 2026-10-31 (G10): "Restoring a battle is a feature that can wait. We'll think about
it later." This section preserves later options and known limitations; no restore adapter,
policy-state strategy or checkpoint study is part of the initial delivery sequence.

WH3 checkpoints rebuild a battle from its replay inputs and hand control back; GaP's
"checkpoints" are postcondition checks, not saved simulations. WH3's
[limits](checkpoints.md#limits) include unreproduced real-time script timers and a fresh
bridge after restore, and the agreed restore checks cover only their declared Land and siege
cases.

| Loop | Status and missing work |
|---|---|
| Play whole new battles, revise between them | Simplest, so first. Still needs the graph runner, a revision driver and an agreed evaluation |
| Restore one situation, try A, restore again, try B | Deferred by the owner (G10). Would need a continuous controller loop after restore, and a check for that situation, the graph state and the handover |
| Rehearse alternatives while the original battle goes on | Not supported by today's single-controller setup: needs extra synchronized game instances, compute and a valid way back into a battle that kept moving |
| Reflect and change goals during the live battle | A controller extension needing no restore, but it costs real battle time and is a different experiment (online adaptation) |

`restore_episode` is a step-run helper, not a `play` for any team, and `checkpoint_root`
accepts only a `hold` source; tactical starting points from an actively controlled battle need
a source-run extension. A future adapter must feed restored public observations into the
normal policy lifecycle, block input before the handover and keep source time and identity.
The rebuild may run faster than 1x before the handover under the existing exception; after
it, 1x.

JUDGEMENT: G10 Restored policy state — deferred by the owner, 2026-10-31: fresh graph state
versus restored member memory remains undecided. Future checkpoint claims would measure
fresh decisions or controller continuation according to that choice.

If chosen later, restoring member memory means saving each part separately: graph version,
node runs, skill state, model history, random state, pending-order identities and message state. An HTTP
request is never resumed as if it were part of the engine replay; pending work is discarded
or reconciled explicitly, with a test that a late reply from the old attempt cannot reach the
new one.

Branches from one source battle are correlated: keep a source battle and all its checkpoints
in one data split, and test transfer on other source battles. Replaying one situation helps
diagnose a graph but does not show learning across battles. A wrong result the held-out
design must expose: a graph that memorized the checkpoint's timestamp.

## WH3 as a VA task family

A WH3 version of VA fixes the map and mode, the observation and action rules, the available
unit types and the opponent family; instances vary deployment positions, composition within
bounds, or the starting situation. This is our adaptation, not one of the paper's benchmarks.

Owner, 2026-10-31 (G11): "We can start narrowly and consider different battle types later."
Start with a narrow Land family; varying deployment positions is still a candidate for its
instances, not a settled sampling procedure.

JUDGEMENT: G11 Task family — open within the owner's narrow start, 2026-10-31: the exact Land
case, variations, distribution and held-out split await definition. Different deployments,
armies or opponents change difficulty; generalization claims rest on those choices.

Candidate families, smallest first:

1. Line contact coordinated with a cavalry attack.
2. Protecting a ranged group while enemies change their approach.
3. Cooperation that keeps working when a unit routs and later rallies.

Start only with a case whose needed state and actions are exposed and checked, and do not
invent unrecorded hidden-state changes to make it harder. Varying deployment needs a
repeatable setup procedure; the current menu scenario alone does not show we can sample the
positions we want.

Hold out in stages: familiar variations, then withheld combinations, then shifts such as an
unseen opponent policy. Record seeds or setup recipes, opponent identity and side. New
positions on one map is a different claim from unseen maps. Winning fast is not automatically
the counterpart of robot throughput: WH3's health and morale measures and outcome rules
belong to the owner's [benchmark interview](benchmark-implementation.md#owner-interview-one-land-battle).

## Comparisons

Owner, 2026-10-31 (G12): "look at these other things too, instead of comparing only
battle-time costs." Record authoring, revisions and failed candidates as well as battle
calls, time and money. The eventual comparison also needs matched skills and information;
its exact controls remain part of the later study design under G1 and G13.

These are candidate later comparisons, not prerequisites for seeing whether GaP works here.
Choose relevant ones in stages rather than committing to a full matrix now:

| Comparison | Held equal | What it isolates |
|---|---|---|
| Hand-written graph vs. today's skills or commander | Skill code, state, tactical goals | Whether the runtime works, and its cost, before any LLM writes graphs |
| Direct two-member LLM team vs. two live graph members | Ownership, views, models, allowed actions, helpers, total call and spend policy | What the graph layer adds; report any unavoidable helper difference |
| One author vs. coordinator plus specialists | Skill catalog, task, total generation budget | Splitting the authoring, separate from how many controllers run in battle |
| First generated graph vs. revised graph | Skill catalog, runtime, selection and test splits | What revision between attempts adds |
| Fixed graph vs. graph with live LLM goal updates | Same authored graph and scenario distribution | Value and latency cost of live adaptation |
| One runtime controller vs. two group controllers | Whole army, total resources, legal information, skills | Splitting runtime control; only once the graph layer works |
| Independent progress vs. waiting rounds | Graphs, skills, information and model resources | Execution scheduling, if revisited under G3 |
| Observation alone vs. explicit communication | Ownership, permitted information rules, skills and total resources | Messages or shared notes, if revisited under G6 |
| Separate army graphs vs. one central graph | Armies, legal information, skills and total resources | Team architecture, after native multiplayer and if revisited under G14 |

Report battle outcomes with their denominators, infrastructure and policy failures
separately, and the agreed health and morale measures once they exist. Diagnostics: time from
a public trigger to its engine effect, source-observation age when an order applies, wrong or
stale orders, idle time, failed cancellations, model calls and dollars. These explain
behaviour; they do not replace the declared primary measure.

Owner, 2026-10-31 (G13): "part of what we will measure in the repo's benchmark" and "we
will think about that later." Settle the GaP study's measurement through that benchmark
work, not by choosing a separate GaP score now.

JUDGEMENT: G13 Statistical plan — deferred to benchmark work by the owner, 2026-10-31:
score, sample count, meaningful effect, uncertainty, promotion/stopping and failure rules
remain open. An exploratory screen or a powered study supports different strength claims.

The unit of uncertainty is an independent source battle, paired only where reset checks
justify it; frames, nodes and repeated branches are not independent battles. Randomize the
declared run order to limit time and build effects, and never quietly replace losses or
failed generations. Choose counts from the effect worth detecting and the observed variation,
registered before the scored run. The budget must cover authoring, failed candidates, the
battles themselves and both games' existing ledger use.

## Delivery steps and proposed checks

Each step needs its own behaviour card and an owner discussion before its check is agreed;
this plan adds nothing to agreed-checks.md. A check's reference is the stated contract or an
engine witness, never a saved output of the code under test, and a deliberately wrong
implementation must fail the important checks.

| Step | Repeatable check | Wrong version it must catch; limit |
|---|---|---|
| 0. Separately scope the broader skill library and controller contract | Inspect the pinned MORSL reference; list first-release capabilities, exclusions, effort bound, contracts and proposed witnesses; walk the two-member example through explicit public observations | An open-ended tactics wish list, an undeclared skill, or treating `hold` as "never move". Planning only; exact scope remains G5 |
| 1. Build, check and freeze that pre-built library, only after separate authorization | Offline skill contracts plus agreed live effect checks in a game window: identities, movement/contact/firing as relevant, with no-order and wrong-target controls; record delegated G4 starting values | An ack sets `succeeded` without an effect, idle drift counts as arrival, or skill scope grows without a release boundary. No strength claim |
| 2. Document the controller interface and add the graph runner using that library | Offline lifecycle, feedback, shared budget and fresh episode state; tiny hand-computed graphs for branching, typed data, no target, bounded loops and cancelling | A graph skips spend accounting, shares episode memory, loses member feedback, uses an old node's output or loads arbitrary Python. No live-effect claim |
| 3. Two graphs through `TeamPolicy`, offline | Hold one member's model reply behind an event while the other sends orders and gets feedback; swap roles; hide a target; change battle identity | A global graph barrier, an order for the other member's unit, a hidden-field leak, a late reply in a new battle. Offline concurrency is not live movement |
| 4. A live graph check with no model, after agreement and in a game window | Fresh launches at 1x: controlled moves with no-order controls, right identities and engine effects; then the contact/charge example with explicit witnesses | False arrival from idle drift, wrong target, charge before contact, fast member blocked by slow one. Says nothing about policy strength |
| 5. Multi-LLM authoring and live LLM members, added separately for diagnosis | Canned author replies test assembly and rejection; immutable library/artifact hashes and budget accounting; then a bounded live smoke using the agreed checks | An author changes a skill or evaluator; hidden diagnostics enter author context; a missing skill is accepted; a reply steers the wrong member. No separate study or learning claim required |
| 6. Between-whole-battle revision; formal comparisons deferred to the benchmark | Replay permitted training evidence into graph revision; preserve the frozen library and count every attempt and cost. Later, once G13 is settled, test candidate selection against held-out leakage and scorer-write attempts | Hidden feedback, skill changes or dropped failed generations; later, promotion on training-only gains. Observing revisions alone establishes no learning gain |
| 7. Native allied armies, after the multiplayer prerequisites; no restore dependency | Per-peer identity and authority, visible information, independent progress, order replication, a common ending, with raw evidence from each peer | An order accepted locally but missing at another peer; a private ally-data leak; one army controlling another. Single-client evidence cannot pass |

Checkpoint work has no delivery step for now (G10). If reopened, its proposed check would
rerun the relevant agreed restore procedure, compare identical-action restores with a
changed-order control, and check public handover readings and the chosen policy-state
strategy. It must catch wrong public fields, stale memory or replies, and pre-handover orders.

For steps 2–3, also change `evaluation`, hidden enemy rows, the teammate's private state and
the `final` and `setup` fields while keeping the legal view fixed: the graph's output must not
change. In steps 5–6, apply that information-boundary check to author and revision inputs too:
changing evaluator-only evidence must not change what the authors receive. A missing witness
gives unknown or failure, never an invented success. For nodes with
state, test rout and rally, a dead target, a newly appearing unit and a battle ending while a
model request is still running, against the declared ownership and reset contract.

Once component checks pass, the next evidence is the agreed live procedure, not more fixtures
repeating the implementation. Never change an agreed checker or its thresholds to get a pass.

## From one army to allied armies

The graph contract stays the same whether a member owns a group or a whole army. Extend the
ownership context explicitly with match, peer, alliance, army and member identities; unit IDs
alone are not safe across clients. Each client's own local runtime submits its orders, and
seeing an allied unit never grants the right to order it.

Owner, 2026-10-31 (G14): "Start with separate graphs", with a central graph as a possible
future comparison. Communication is still a later extension under G6: separate graphs do
not by themselves authorize messages or a shared information store.

A later message might say "my line is engaging enemy E", with sender, match, source battle
time, expiry and a public target reference: a teammate's report, not an engine fact. Messages
never wait at a global barrier or carry private orders or evaluation data by accident.
Whether allies share vision, who owns army-wide resources, what may be said and what happens
on a disconnect belong in the multiplayer information and authority contract, not in a
convenient shared Python dictionary.

Follow [native-multiplayer.md](native-multiplayer.md#step-by-step-delivery): prove native
matches and passive observation, order replication, authority and lifecycle before any LLM
study. Today's move-only worker cannot show attack or charge behaviour, so add and check each
needed action before enabling it. Native allied armies come before four-client 2v2. Results must reconcile
what each peer reports, with desyncs counted as infrastructure failures. A single-client
experiment with an allied AI, if used, gets its own label and cannot stand in for several
independently controlled armies.

Native checkpoint restore is separate research: the current tool does not restore peer
sessions, membership or a synchronized handover. Team experiments start from fresh matches,
in line with the owner's existing preference to avoid multiplayer checkpoints.

## Risks and when to stop

| Risk | Response |
|---|---|
| The broader skill library grows without a stopping point | Scope its finite first release separately (G5), with explicit exclusions, effect checks and an effort bound; freeze it before graph revision |
| Gains come from better hand-coded tactics | Share skill code across baselines; compare with a hand-written graph and the current commander |
| Graph waits add delay | Require the independent-progress test; measure the age of engine effects, not graph throughput |
| Success checks reward the wrong thing | Keep public runtime guards apart from evaluator witnesses; test with wrong-target and no-effect controls |
| Generated code bypasses ownership or leaks data | First graphs only pick approved operations. GaP imports Python scripts even while validating; type checks are not a sandbox |
| A rigid graph cannot handle moving opponents | Test target loss, rout and rally, and late replies; compare fixed graphs with bounded live goal updates |
| Improvement overfits one checkpoint or opponent | Split by source battle and opponent family; freeze before the held-out test |
| Rehearsal costs too much game time or money | Bounded sequential attempts; count failed generations and revisions; no assumed fleet of parallel simulators |
| GaP's code differs from its paper | Pin what was inspected; tell structural repair apart from demonstrated rehearsal optimization |
| The idea duplicates prior work | Before a thesis claim, compare with behaviour trees, reactive plans, options and dynamic multi-agent graph control; the reading so far is not a full novelty search |

Stop or narrow the work when:

- plain shared skills match the graph within the declared budget: a useful negative result,
  and no reason to add complexity without a new hypothesis;
- the live skill witnesses fail: fix or narrow those contracts before asking models to
  optimize over them;
- native order replication is not established: keep results scoped to split-army control.

## References

Primary sources read 2026-10-31; no external tests or robot results were reproduced. Research
entry: [papers.md](../thesis/papers.md#gap-graph-as-policy-for-variational-automation). Source
checkouts, the review and the check report are in `runs/gap-plan-20261031/` (ignored).

- [Paper v1](https://arxiv.org/html/2607.05369v1), [project](https://graph-robots.github.io/gap/),
  [docs](https://graph-robots.github.io/graph-as-policy/).
- GaP code at `71549e1584839337eb355c280e7b1e50c805b8c7`:
  - [gap/agent/multi_agent.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/agent/multi_agent.py):
    coordinator and subgraph assembly, validation repair, postconditions written separately;
    [tests/agent/test_pipeline.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/tests/agent/test_pipeline.py):
    pipeline tests with canned replies. Adapt the separation; never let authors control scores.
  - [workflow.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/runtime/workflow.py),
    [validate.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/runtime/validate.py),
    [schema docs](https://graph-robots.github.io/graph-as-policy/reference/workflow-schema.html):
    explicit graph structure and typed bindings to follow. GaP only warns on unknown tools and
    imports scripts, so WH3 needs a stricter list of approved operations.
  - [executor.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/runtime/executor.py),
    [executor docs](https://graph-robots.github.io/graph-as-policy/reference/executor.html),
    [test_executor.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/tests/runtime/test_executor.py):
    reference tests for routing, scope and failures. Regular nodes finish a super-step before
    their successors advance, and cross-subgraph inputs resolve by the latest producer's name;
    WH3's resumable members and explicit producers differ on purpose (G3).
  - [Checkpoint docs](https://graph-robots.github.io/graph-as-policy/running/checkpoints.html):
    postconditions checked against simulator truth; a missing sidecar may be skipped, and
    enforcement can be off, warn or raise. WH3 checks must require their named witnesses.
    These are not an engine save/restore.
  - [gap/benchmark/__init__.py](https://github.com/graph-robots/graph-as-policy/blob/71549e1584839337eb355c280e7b1e50c805b8c7/gap/benchmark/__init__.py)
    says its harness does one-shot generation without rehearsal or refinement, and the
    code's repair loop is structural repair. Do not promise a ready-made version of the
    paper's full self-learning loop; map more code before reusing any.
- Open Robot Skills at `752dfbd96968d4d08379f8111765efbf6457800b`:
  [transporting-objects/SKILL.md](https://github.com/graph-robots/open-robot-skills/blob/752dfbd96968d4d08379f8111765efbf6457800b/skills/transporting-objects/SKILL.md)
  and the [authoring docs](https://graph-robots.github.io/graph-as-policy/skills/authoring-bundles.html)
  show capability descriptions, typed inputs, named exits, allowed tools and canonical
  scripts. Mirror the documentation pattern; the robot motion and perception code does not
  apply. Both repositories declare Apache-2.0: keep attribution and licence notices on any
  code copied later, and check individual bundles and third-party terms then.
