# Battle C: coordinating one army with limited communication

Owner direction, 2026-11-05: add a third, separate Cannae-inspired battle studying how
multiple agents execute a complex plan through synchronized manoeuvres despite limited
communication. This is the single-army setting, with one client and disjoint command
groups. **Development implementation: local views, channels and asynchronous/model
integration have component evidence and one scripted live case; readiness is unverified.** Any faction
and lords may be considered. The owner requested construction/testing in the away window;
no paid model comparison is scheduled.

[A studies a familiar tactic and B studies adaptation to fresh information](cannae-comparison.md).
C asks how much coordinated execution can come from a shared plan, local initiative,
visible movement and restricted messages. It gets its own scenario identity, construction
checks and results. A common Cannae geometry can connect the designs without making their
raw win-rate differences a measurement of memory, improvisation or communication.

## Historical basis and fidelity

Polybius places different commanders at the centre and wings (3.114), describes infantry
reacting to their developing flank opportunity (3.115), and credits Hasdrubal's decision
to leave pursuit to the Numidians and support the infantry (3.116). This motivates both
advance organization and subordinate initiative. It does not establish that every move
followed a fresh order from Hannibal or that all groups moved at the same instant.
[Histories 3.114–116](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Polybius/3%2A.html#114).

Those passages do not supply a reconstructable message log, signal codebook, delivery
times or ranges. Polybius elsewhere describes successive signals coordinating a Roman
camp departure, which supports the general idea of prearranged signals, not a particular
Carthaginian signalling system at Cannae.
[Histories 6.40](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Polybius/6%2A.html#40).

JUDGEMENT: Historical communication proxy — Codex, 2026-11-05: proposes prebattle agreement,
local observation, short signals and delayed couriers as experimental abstractions.
A literal reconstruction differs; findings describe these rules, not Hannibal's actual channel.

Use that distinction throughout: reproducing the constraints on distributed execution is
the objective; exact ancient communications remain unknown from these sources. A short
signal represents an agreed instruction; a courier carries a richer but older report.
Neither channel grants a commander a live map of the whole army. Failed delivery and
misinterpretation can be studied after the basic channel works; do not invent historical
failure probabilities. No new audiovisual assets or native multiplayer clients are needed.

## Battle and command groups

JUDGEMENT: Command groups and local knowledge — Codex, 2026-11-05: proposes five fixed
groups with local command views and a common prebattle brief. Three broad sectors or
global alliance vision differ; coordination claims depend on the partition and view rule.

Use the [canonical Cannae construction](cannae-eval.md#proposed-battle-specification) as
a candidate starting geometry. C is separately calibrated against native AI; B's random
reserve intervention is not required. Keep the forces, deployment and opponent fixed
across C's channel comparisons. If this geometry supplies no consequential dependencies,
revise it explicitly rather than assuming the name guarantees coordination.

| Proposed agent | Exclusive command | Dependency to investigate |
|---|---|---|
| Centre | Central infantry; a lord may belong here | Keep the main fight viable while deciding whether support is needed or the enclosure must be abandoned |
| Left infantry | Left flank infantry/reserve | Commit inward when useful while preserving support for the centre or cavalry |
| Right infantry | Right flank infantry/reserve | Coordinate its commitment with developing pressure and the other flank, without a live report from it |
| Decisive cavalry | Strong cavalry wing | Finish or leave its local fight, help the other wing when needed, then choose support or a rear attack |
| Containing cavalry | Other cavalry wing | Keep opposing horse occupied or report inability to contain it; pursuit and support are competing jobs |

Ownership is by declared regiment identity/slot, not just unit type: the same unit type
can belong to different wings. Freeze the partition before play and log it. No agent can
directly order another's units; requests require messages and local execution. A centre
agent may have overall command responsibility but has no privileged observations or
remote action authority. An extra strategic commander, reassignment or a three-agent
grouping is a separately declared architecture, not a silent change to the comparison.

Map the useful dependencies before trials: centre resistance creates time; flank
engagement changes the value of cavalry support; containing enemy horse enables safe
redeployment. Check actual contact, route and morale effects. Synchronization means
actions occur in useful temporal relation, including continued overlap and ordered
handoffs. It does not mean minimizing the spread of all order timestamps. Simultaneous
attacks can be wrong when one wing needs to wait or the centre needs relief first.

## What commanders can know

Before launch, provide every agent the same permitted roster, map/deployment brief,
ownership map, objective, channel rules and a shared plan/codebook. For an execution
study, supply and freeze the same plan in every arm, including contingent triggers,
fallbacks and local discretion. A separate preparation study lets the team write it
within a recorded budget before launch. Do not mix plan quality with channel quality.
Record preparation calls/cost, freeze the artifact and clear unrelated episodic memory.

During play, own units retain full condition and order telemetry, with target references
sanitized so they do not refresh unseen enemy positions or condition. Other friendly units are reported only
when locally observable; unseen teammates do not supply live health, morale, target,
intent, location or death updates. Locally observed movement is legitimate implicit
communication. Remembered observations retain their age and source. The declared enemy
roster remains known, but unseen enemy losses do not become a global status feed.

Proposed first sensing rule: use a named owned command regiment as each group's moving
anchor. Local contacts must be within a declared radius of that anchor; enemies must
also satisfy the existing alliance-visibility boundary. This additional radius is an
experimental locality proxy, not verified engine line-of-sight or human perception.
Start on inspected open terrain; a terrain/occlusion model requires additional checks.
Own-unit telemetry remains an abstraction of communication within the command group;
scattering owned scouts does not silently give a commander their union of enemy views.

Anchors need a frozen replacement rule for death/rout and distinct behavior while no
anchor is usable. No automatic transfer of the lost commander's intelligence to peers.
If a lord anchors a group, its combat/leadership effects are part of the fixed scenario,
not an excuse for a global command channel. All these choices rest on JUDGEMENT
`docs/twwarhammer3/cannae-communication.md` Command groups and local knowledge.

Inspect the entire input path: unit targets and target positions, aggregate strength,
observed-death counters, global objectives, mode metadata, logs/tools, caches, memory,
orders, validation errors and helper decisions. Derived fields can reveal a distant
fight even when its unit rows are hidden. The server may retain full legal public state
for validation, but cannot return unauthorized details through errors or target lists.
Messages about enemies do not grant attack-by-ID authority beyond the declared legal
target rule; reported locations may support movement. Freeze that rule across channel arms.

Retain a common battle clock for instrumentation. An exact clock shown to every model
is a modern coordination aid: disclose it, challenge timed scripts, and treat coarse
or relative model time as a separate sensitivity condition. Do not silently attribute
clock-driven coordination to ancient signals. Messages may encode information in their
timing or absence; those uses are part of the measured channel capacity.

## Communication contract

JUDGEMENT: Channel mechanics — Codex, 2026-11-05: proposes a range-limited signal codebook
and finite-capacity delayed courier channel, with no instant acknowledgement. Text-only
rate limits or simulated physical couriers differ; conclusions rest on these mechanics.

| Method | Proposed semantics | Constraint to declare before implementation |
|---|---|---|
| Prebattle agreement | Shared intent, contingencies, roles and codebook fixed before launch | Preparation budget and artifact size; no live rewriting of shared files |
| Signal | One code broadcast from the sender's anchor to eligible nearby anchors | Alphabet, range, cooldown and propagation delay; no appended free text, coordinates or arbitrary metadata |
| Courier | Addressed, bounded text carrying the sender's report/instruction as composed | Payload size, finite in-flight slots, travel rule, lifetime and destination rule |
| Visible action | Agents can infer intentions from legitimately observed motion/fighting | Same sensing and action rules in every channel arm; inference is not an explicit message |

A candidate signal vocabulary is READY, HOLD, COMMIT, HELP and ABORT, with meanings
agreed beforehand. It is a proposed codebook, not a historical claim or an adopted value.
The router delivers the chosen symbol; it does not decide whether a unit is really ready,
choose a tactical recipient or turn a message into an order. Relaying consumes a new send
and its delay/capacity. Recipient identity, send time and any sequence/age fields are
explicit protocol content, not an unlimited metadata channel.

For a signal, determine recipients from anchor range at emission; after the declared
delay, deliver only to recipients with a usable anchor. The sender receives no recipient
list. Signal reception identifies its sender/code but does not disclose exact coordinates
or the sender's unseen condition. This is a range proxy, not simulated sound or flag visibility.

For the first courier prototype, use a virtual travel model: at accepted send time `t`,
freeze the sender anchor position and a rendezvous drawn from the sender's permitted
knowledge: a prearranged point, last local sighting or delivered report. Never use a
secretly refreshed recipient position to choose the destination. Availability
is no earlier than `t + dispatch_delay + distance / courier_speed`, measured in battle
seconds. Distance is initially straight-line distance on the inspected open map. At arrival
the recipient must be within the declared rendezvous radius, otherwise that delivery fails;
the slot remains occupied until arrival or expiry. This models delay and missed rendezvous,
not a pathfinding messenger, combat interception or terrain traversal. Physical messengers
and rerouting would be separate mechanisms requiring engine evidence. The router's private
endpoint coordinates and future arrival time are never exposed as an advance tracking feed.

Payloads are immutable snapshots, not live shared memory. Delivered claims can be wrong
or stale; forwarding does not refresh their source time. A sender learns only that a
local send was accepted, not remote receipt or comprehension. An acknowledgement is a
new message using the same channel. Failures do not reveal the recipient's unseen death
or coordinates. Expiry, ordering, capacity overflow, ties and reset behavior are declared
and logged. Start with deterministic range/delivery rules; a stochastic loss arm must
state its independently drawn mechanism and preserve every failed delivery.

All numerical settings remain open: view/signal/rendezvous radii, signal delay/cooldown,
payload/alphabet limits, courier speed/dispatch delay, slots and lifetime. First measure
useful response windows and route lengths, then propose values and a small sensitivity
range for owner agreement. Values must allow usable but constrained communication at 1x;
do not tune them to make one model win. No historical seconds-per-message claim follows.

The battle never pauses for a conversation or waits for all agents to finish. Separate
send acceptance, channel arrival, recipient's next input, inference completion, order
application and observed effect. A message arriving during inference enters the next
request under the declared scheduler; it does not rewrite an in-flight prompt. Model/API
latency adds to the channel delay and is reported separately. Existing legal orders
continue, and a silent/slow agent gets no undisclosed intelligent substitute.

## Comparisons and evidence

JUDGEMENT: Communication comparisons — Codex, 2026-11-05: proposes within-C channel
comparisons with fixed views, plans and executors, plus separate information controls.
Raw A/B/C rankings differ; causal communication claims depend on what each contrast holds fixed.

| Condition | What it answers |
|---|---|
| Local views, shared plan, no live explicit channel | How far preplanning, local rules, clock and visible movement suffice |
| Same views/plan, bounded signals and couriers | What the proposed limited channels add, including their costs and delays |
| Same views/plan, fast addressed text with declared high limits | How restrictive the bounded channel is; inference and scheduling still take real time |
| Global permitted alliance view, same no-message team | How much shared telemetry substitutes for messages; an information/action-access contrast if visibility changes target legality, not a channel-only contrast |

Signals-only, couriers-only, greater delay, loss and prepared-plan versus team-authored-plan
conditions are follow-ups, not an automatic full grid. Freeze the chosen roster, command
groups, model versions, prompts, tactical advice, executor, cadence, context policy and
resource ceilings. Count all preparation, message writing/reading, retries and helper calls.
Show actual tokens, dollars, action rates and inference delays; equal ceilings do not make
cost equal. An unlimited-resource team is a separate whole-system comparison. Removal of
a channel from a frozen controller tests dependence; allowing separate retraining/tuning
tests what each communication regime can achieve. Label them separately.

Use fresh battles with predeclared repeats and balanced arm order, retaining attempts,
failures and the full result register. Matched initial configurations do not ensure identical
later trajectories against native AI. One team outcome is one battle, not five samples.
Numbers, uncertainty method, budgets and stopping rules require an experiment card.

Before saying communication or synchronization matters:

1. Establish a feasible winning witness through the proposed local interface at 1x.
   The owner's manually paused demonstration can support winnability but cannot establish
   that this restricted automated interface has enough time or information.
2. Identify a local fact whose useful consequence depends on another group's action:
   for example, the containing cavalry's worsening fight changes whether the decisive
   cavalry should assist it or attack the rear. Record who could know it, the latest useful
   response, and the actual action effects. Test the proposed timing dependency in engine;
   do not define success as following the preferred script.
3. Challenge a fixed common schedule, independent local rules, pursuit/rush strategies,
   central concentration and timer defense. Vary declared starting distances or opponent
   pressure across construction cases to test brittleness without adding B's hidden event.
   If a simple plan wins reliably without messages, that is evidence for preplanned/local
   coordination; it does not establish online communication necessity.
4. For message usefulness, compare normal delivery with its declared removal/delay while
   preserving views and usable action rules. Trace sender observation → message → recipient
   input → changed choice → effect. A matched decision replay can test a local choice;
   only live continuations support outcome claims. No single intervention establishes
   that every winning policy must communicate, and helpful explanations are not causal proof.
5. Measure task-specific support overlap, arrival relative to the supported engagement,
   exposure while waiting, failed handoffs, and recovery after an obsolete instruction.
   Calibrate event definitions against actual units/actions. Many messages, close positions
   or simultaneous orders do not themselves demonstrate effective coordination.

Report engine outcomes, health/morale, cost and latency beside the above evidence. Keep
every legal engine win, including an uncoordinated shortcut or timer win. Do not reject
successful local initiative for disobeying a plan, reward verbosity, or introduce a new
aggregate coordination score before its meaning and deciding check are agreed.

## Implementation boundary and proposed checks

The base team controller retains its alliance-wide projection and type partitions.
`battle/local_command.py` adds C's authored regiment binding, anchor sensing and router;
`battle/local_team.py` uses the same asynchronous `TeamPolicy` through its member-view
hook. Both the input and fresh dispatch guard use that hook. Existing model-team tests
do not verify these additions. See [current team implementation](multi-agent-implementation.md).

### Development interface, 2026-11-05

`emp-envelopment-c-v1`, `emp-envelopment-c-silent-v1`, `emp-envelopment-c-fast-v1` and
`emp-envelopment-c-global-v1` share A's physical declaration and native AI. They select
local bounded channels, local no-message control, local fast text and global contacts
without messages, respectively. The global control changes target availability as well
as information, so its difference is not a channel-only effect. No existing suite adopts C.

The concrete numerical profile rests on JUDGEMENT `src/twwarhammer3/battle/local_command.py`
Local command development profile and Fast text control. Couriers initially use the
published starting-anchor rendezvous, not a refreshed peer location. Router events keep
acceptance, source observation, arrival and delivery disposition. Original content/time
survives explicit courier relays, which require a message already delivered to the sender.
Delivery is processed at the first dispatcher observation at/after its due time; actual
receipt time is recorded. Ordering/expiry ties rest on Local channel ordering in that file.

The fixed command groups and fallback order are the authored slots in `GROUP_SLOTS`.
Own telemetry remains available when no anchor is usable, but there are no local contacts
or channel transmissions/receptions then. Memory of enemy roster types/identities comes
from the initial public roster; remote observed-death updates do not enter C. Navigation,
queue and destination readbacks are removed rather than refreshing unseen targets.
New orders must pass the source and latest local views, resting on JUDGEMENT
`src/twwarhammer3/battle/local_team.py` Local target authority; persistent engine orders
continue normally. A remote target cannot be queried through fresh orders or error text.

Run via the existing configured controller interface:
`play --scenario emp-envelopment-c-v1 --policy configured --controller-config
configs/twwarhammer3/controllers/cannae-local-probe.json --output NEW_JOB` for the free
interface probe. `cannae-local-model.json` selects five `llm_rules` model leaves sharing
the ordinary job ledger; add the normal model/provider/budget arguments only within a
named budget. A C declaration refuses ordinary global-view controllers before launching.

Every member gets the same frozen `configs/twwarhammer3/cannae_shared_plan.md`, ownership
map, channel rules and prearranged rendezvous. Model replies add up to two messages to
the ordinary orders/reason/notes envelope, resting on Member message batch in
`local_team.py`. Their orders and memories use only that member's view. Invalid model
envelopes forfeit the decision with no partial salvage or invalid-reply retries; normal
provider transport accounting still applies. Supplied preparation is free and fixed;
there are no unrecorded model planning calls. All preparation/inference in later studies
must still count against their declared resource policy.

The dispatcher transports messages independently of stale-order dispatch: a factual
report retains the composing observation time even when its associated orders become
stale. Newly delivered messages/acceptance reports enter only a later immutable member
input, then leave its unread inbox. Explicit relays can reference earlier received mail.
The probe sends initial READY/couriers. Left infantry waits for a centre courier, then
issues one eastward move before using local nearest attacks; the other groups use local
nearest attacks immediately after their initial sends. This diagnostic rests on Message
effect probe in `local_team.py`. It can check delivery-to-order effects, not tactical
usefulness or communication improving outcomes. The silent arm deliberately never
releases that diagnostic move; its outcome is not a competent no-message baseline.
Card, component checks, review and live evidence belong in `runs/cannae-build/`.

At `8f6dc0b`, `runs/cannae-build/c-bounded-probe-01/` ended with one engine win at
520.6 battle seconds. Independent recount checked all 1,692 recorded member inputs
against their source observations, fixed ownership and the 160 m anchor boundary.
Five refusals were three local target-visibility checks and two engine routing refusals.
The centre courier's composing input was at 5.2 s, send at 5.5 s, arrival at 11.5 s and
the next left-infantry input at 12.4 s. Its move was applied at 13.9 s. Replay readings
approached the requested point before a replacement order, supporting one delivery-to-
movement chain. This is not an exact displacement claim, useful tactical synchronization,
model/provider behavior or communication improving the outcome. Recount: `review/c-live/`.

Follow the separation of per-agent observations from shared state in the research code
[SMAC, `smac/env/starcraft2/starcraft2.py`, `get_obs_agent`](https://github.com/oxwhirl/smac/blob/master/smac/env/starcraft2/starcraft2.py),
while preserving WH3's asynchronous 1x execution and legal-action contract. This is a design
reference, not reused correctness evidence. [TarMAC](https://proceedings.mlr.press/v97/das19a.html)
motivates separately studying message content and recipients; its rounds of communication
before environment actions are not a license to stop this battle.

| Proposed check | Plausible wrong implementation it must detect |
|---|---|
| Change only distant, unobserved friendly/enemy state; compare complete member inputs and helper outputs until an allowed cue/delivery | Hidden health/target counters, shared summaries or a fast executor reveal the distant fight |
| Change a peer's private plan, inbox, files or pending request | Another worker reads it without permitted communication; dictionary copies mistaken for isolation |
| Exercise duplicate unit types in separate wings, routing/death, stale replies and new episodes | A type partition merges groups; orders or messages cross ownership/episode boundaries |
| Replay numbered sends at range/capacity/expiry boundaries using battle time | Instant ACK, early arrival, free relays, payload updated in flight, expired or wrong-recipient delivery |
| Move the courier recipient after send and compare private router and permitted recipient records | Instant tracking or delivery at a missed rendezvous; hidden destination leaked in status |
| Slow one member and let a message arrive during inference | Team-wide barrier, prompt silently changed, arrival confused with first usable input |
| Inspect live sender/recipient inputs, order application and effects at 1x | Component pass assumed to prove a usable response window, sensing fidelity or synchronization benefit |

The executor must use the same member view for tactical choices; validation may use
broader server state only to enforce legality. Audit LLM rules, persistent target pursuit,
skills, GaP artifacts and summaries before admitting them. An executor that already
coordinates from full state changes whose capability is measured. Trusted adapters are
not an isolation boundary for arbitrary tool-using agents; file/process access needs a
separate isolation design before an adversarial submission claim.

Next settle the partition/local view and abstract communication profile, then the specific
battle dependencies and deciding procedures. Implement and check transport/projection
offline before any live construction check; demonstrate feasible action windows before a
model comparison. No check is added to [agreed checks](../agreed-checks.md) until agreed.
This third design preserves the [scenario guidelines](scenario-guidelines.md) and the
owner's simpler-then-complex progression; it does not restart stopped support-timing work.
