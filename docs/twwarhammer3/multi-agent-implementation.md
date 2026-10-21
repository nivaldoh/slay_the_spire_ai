# Implementing the first WH3 agent team

Implementation path, 2026-10-21. Build a small split-army controller on top of
the existing custom-battle runner: two trusted scripted members, fixed unit ownership,
one mailbox writer, and independent decisions. The first live result should demonstrate
that one member can issue an effective order while the other is still thinking, with
correct ownership, feedback and timing records. It need not win the battle.

The first coding slice is an offline ownership and dispatch adapter. The next adds
independent workers and the trace needed to inspect them. Only then run a bounded live
probe. Model calls and communication follow in separate changes. Native team multiplayer
and campaign support remain later capability gates in the
[evaluation plan](multi-agent-plan.md); this implementation path does not replace them.

The owner authorized implementation and agreed the component checks and four $0 live
probes on 2026-10-21. Slices 1–2 are implemented in [team.py](../../src/twwarhammer3/battle/team.py);
the [component tests](../../tests/twwarhammer3/test_wh3_team.py) pass. Live capability is
still unverified, pending [the diagnostic check](../../tests/twwarhammer3/check_wh3_team.py).
Slices 4–6 and multiplayer/campaign support remain future work. Revision-specific
verification belongs in [AGENTS.md](../../AGENTS.md#verification-hard-rule).

## What the existing code lets us reuse

Source inspection at `c2a7ae7` supports a small adapter rather than a second game runner:

| Existing behavior | Implementation consequence |
|---|---|
| [Controller loading](../../src/twwarhammer3/battle/controllers.py) accepts a zero-argument class with `decide`, `acknowledge` and `metadata` | Expose fixed scripted probe variants through the existing `package.module:Class` syntax; no new command grammar is needed initially |
| [The play loop](../../src/twwarhammer3/battle/play.py) owns the mailbox and allows one request in flight | Keep that single writer; members return orders to the adapter and never access bridge files |
| Even an empty decision becomes a mailbox request | An idle adapter can return `[]`, but those polls must not be counted as completed member decisions |
| [Validation](../../src/twwarhammer3/protocol.py) permits orders for every unit in `friendly` | Give a member only its owned units in `friendly`, expose teammates separately, and enforce ownership independently |
| Feedback indices are one-based positions in a request | Initially send one member's complete batch per request; indices and queued move/attack sequences need no remapping |
| The outer timing starts at the adapter's latest input | Record the member's original input time; outer timing alone understates asynchronous decision age |
| Fresh controllers are constructed for each episode | Keep all member state, workers and ownership on that episode's instance |
| [The ledger](../../src/gameai/ledger.py) checks `spent + proposed_cost` but retains no outstanding reservation | Two concurrent model calls are a separate prerequisite; sharing one Ledger object does not make them budget-safe |

The existing multiplayer/campaign activation guards, Lua order format and single-agent
controllers need no change for the initial scripted prototype. The adapter is trusted
in-process code, like existing outside controllers; this does not provide isolation from
arbitrary submitted code.

## The first working configuration

Use the existing declared land battle `emp-knights-emp-swordsmen` from
[scenarios.json](../../configs/twwarhammer3/scenarios.json). Its player roster contains
one Swordsmen unit and one Empire Knights unit, giving two distinct unit types to bind.
This choice avoids inventing a new scenario just to test dispatch. Its value as a
coordination benchmark is a separate question.

Bind `infantry` to the single observed Swordsmen unit and `cavalry` to the single observed
Knights unit when the first complete deployed observation arrives. Check the expected
types and counts, save the resulting battle-scoped IDs, and refuse an ambiguous or
incomplete roster before issuing an order. Do not assume that `f1` means infantry in
every battle. Ownership stays fixed through rout/rally and ends with the episode.

The probe members issue a small, declared sequence of move/halt or attack commands.
Use distinct open waypoints chosen from the public terrain and initial positions; record
the exact points before judging movement. Reuse `Hold`/`AttackNearest` for component
cases where they fit, and add only the bounded movement/delay behavior the live check
needs. The two members have separate objects and histories.

Initial supported actions are `move`, `attack` and `halt`, including a queued move/attack
sequence. The probe has no shared spending, spells, summons, reinforcements or ownership
transfers. Reject unsupported actions and unexpected new friendly units explicitly;
never silently assign a new unit to whichever member happens to act next. Fix
`--interval-ms 0` and `--delay-seconds 0`; the existing global delay/interval are not
per-member settings. Battles and diagnostic probes remain unpaused at 1x.

## The adapter contract

Put the implementation in one new module, `src/twwarhammer3/battle/team.py`. A small
`TeamPolicy` can accept injected members and a partition rule for tests. Two thin
zero-argument probe classes fix the live variants: delayed infantry and delayed cavalry,
sharing every other setting. Keep configuration in those explicit classes until
another real experiment needs a configuration file. Record its members, supported actions,
timing, partition rule and resolved ownership in its disclosure and trace.

### Member inputs and action authority

Build a fresh nested copy for each member from a narrow, versioned allowlist. Include
battle/sequence/time/phase, relevant timer and terrain information, owned units in
`friendly`, other friendly units in `allies`, and visible enemies in `enemy`. Start with
the unit fields the scripted actions actually use: identity/type, position, men, state
and a target only if that enemy is currently visible. Expand the list deliberately when
the model stage needs more fields. This is a restricted prototype input contract, not a
claim of parity with every field in the existing benchmark.

Drop the global `orders` acknowledgement, operator job name and all private/evaluator
fields. Do not forward arbitrary nested fields or a hidden target's identity/death.
Both members get the same permitted battlefield information apart from which units they
may command. They do not receive each other's pending replies, private memory or refusal
feedback. Visible movement and public unit state can still reveal intentions.

Maintain authority in a separate ownership map keyed by battle and member. On receipt
and again before dispatch, require every ordered unit to belong to that member and to
remain legal in the current projected observation. Call the existing `validate_orders`
on that restricted view. Keep its aggregate check in `play.py` as a final guard. A member
must not gain authority by returning an order for a unit it can see under `allies`.

Reject a whole invalid member batch with explicit local feedback; do not salvage a
move/queued-attack sequence into a different maneuver. Leave the other member's valid
ready batch available. Local refusal is marked as local, with no invented engine
application time. Record it separately from a game acknowledgement and count it in
member diagnostics. An invalid ownership map or dispatcher invariant ends the probe;
it is a harness fault rather than a gameplay loss.

### One member batch per request

For each member retain only its input, one running decision or completed batch, and the
feedback state. The lifecycle is idle → running → ready → selected → idle after feedback.
For the first offline slice, deterministic completed workers can exercise these states;
independent workers are the next slice.

At each outer `decide(current_public_state)`:

1. Bind/check the battle and ownership; collect any finished member decisions without
   waiting for unfinished ones. Capture their orders and metadata together.
2. Reject expired, foreign-battle or currently illegal batches with member-local
   feedback. Keep their original input and rejection reason in the trace.
3. Start eligible idle members on separate copied current inputs. Never start a second
   decision before that member's preceding decision has received feedback.
4. Select one ready valid batch, using oldest-ready first and alternating equal-time
   ties. Save its selection/member/decision identity until feedback or terminal cleanup.
5. Return that batch unchanged. If no member is ready, return `[]` with no member assigned.

A member that deliberately returns `[]` has completed a decision and gets its own no-op
feedback; an idle dispatcher poll has not completed a member decision. Preserve that
distinction in the event record. A constantly ready member must not starve a peer whose
reply has finished. Do not merge batches initially: each engine acknowledgement belongs
to one member and its existing indices remain correct.

Selection is not transmission: the outer loop can observe an ending or reject the batch
before writing it. Record `selected` in the adapter and include its selection ID in
cached metadata; the outer `decision` event binds that ID to the actual mailbox request.
An unsent selection is discarded on cleanup. If outer validation substitutes an empty
batch and synthetic refusal, route that refusal to the selected member and mark it as
validation feedback, not a game execution failure. Process at most one completed result
per member per poll so repeated local refusals cannot trap the dispatcher.

`acknowledge(ack, latency)` routes only the selected member's results and then releases
that member for another decision. Recompute its latency from its own timestamps: worker
duration for `think_s`, input delivery to acknowledgement for `roundtrip_s`, and source
battle time to engine submission for `delay_ms`. Do not pass the outer adapter latency
unchanged. Local refusals carry no engine-application latency; the model stage must render
that distinction rather than invent a zero-age game acknowledgement.
`metadata()` returns a cached snapshot and never waits
for a worker. Member `decide`, `metadata` and `acknowledge` calls must be serialized for
that member; two different members can run concurrently. The first trusted scripted
callbacks must be short and bounded. Arbitrary slow acknowledgement callbacks need their
own scheduling before those controllers are supported.

The outer loop still waits for mailbox acknowledgement, including empty requests. That
is shared transport delay, not a teammate-inference barrier. Measure it. If it becomes a
demonstrated bottleneck, consider a later change to the runner; do not redesign the
transport before the probe shows why it is needed.

### Timing and trace records

An illustrative sequence, not a measured result: both members receive the state at
10 s; infantry finishes at 10.2 s and applies an order at 10.5 s; cavalry finishes at
13 s and applies at 13.4 s. Infantry must not wait for cavalry. Its order age is 0.5 s;
cavalry's is 3.4 s, even if the adapter saw a fresh state just before dispatching cavalry.

Retain member ID, decision ID, source sequence/battle time, the actual projected input,
worker start/completion on a monotonic clock, dispatch basis, outer request ID, engine
application time and final disposition. The current wire `based_on` still identifies the
adapter's dispatch validation basis; it does not become the child's original inference
basis. Compute member order age from engine `applied_ms - member_source_time_ms` and
worker duration from its monotonic timestamps. Report scheduler waiting separately.
The reply-age limit is checked against the latest available battle observation at Python
dispatch; the unchanged wire cannot enforce an expiry at actual game application. Report
any transport overage separately. For queued orders, `applied_ms` means submission to the
engine queue, not the later execution of that order. Observed movement is separate evidence.

Add a narrow optional `drain_events()` hook to the existing play-loop event writer before
the asynchronous live probe. Drain after decision/feedback handling, on exceptions and
after cleanup, including when a terminal observation skips the next decision. Workers
never write the trace themselves. Events cover member input, completion, local refusal,
dispatch, feedback and unfinished/cancelled work. The play loop supplies the actual outer
request ID when writing dispatch, so an order unacknowledged at termination is still
attributable. Keep all of this in the existing episode trace.

Extend `digest` only enough to show the two members' order origins, refusals and timings.
Ordinary decision counts and `think_s` remain adapter/transport measures; label them as
such for team controllers. The controller card must say asynchronous when workers are
introduced; today's imported-class card otherwise says blocking. Do not pool prototype
results or timings into single-controller benchmark conclusions.

### Failure and shutdown

For the first prototype, an unexpected member exception ends the diagnostic episode
through the existing policy-failure path, with member/decision identity attached. Preserve
its non-API exception as the cause: a directly raised `PolicyFailure` with no cause can
currently be treated as a failed decision and retried by `_drive`. Invalid
actions use the local-refusal path above. There is no automatic replacement of a failed
member. Continuing after a crashed member is a later resilience experiment with a
separately declared rule.

Give dispatcher invariant/setup faults a narrow `TeamHarnessError` derived from
`ProtocolError`, and pass that exact type through `policy_call` in slice 2. Otherwise
the current wrapper converts even protocol errors to policy failures. The episode then
records the existing `unsupported_or_invalid` disposition plus a team fault event;
it is not a gameplay loss. Preserve all other controllers' exception handling, mailbox
faults and budget-stop behavior. Test member failure and dispatcher failure separately.

On terminal result or stop, prevent new decisions, discard unsubmitted results and record
every pending decision's disposition. Do not wait for a game acknowledgement that can no
longer arrive. Close every member even if another close fails, preserve the recorded
engine ending and then construct entirely fresh state for the next episode.

Use only bounded, cooperative scripted workers in the first threaded version. A delay
probe should wait on a stop-aware event so cleanup can wake it. A running Python thread
cannot be assumed cancelled by cancelling its Future or using non-waiting shutdown. Do
not begin another episode while an old worker can still modify state. General external
controllers and network calls need an explicit bounded termination design before use;
the current commander waits for its worker and model transport can wait much longer
than the intended probe delay.

## Implementation sequence and stopping points

| Slice | Small change | Done when | Evidence limit |
|---|---|---|---|
| 1 Ownership and routing | `team.py` plus `tests/twwarhammer3/test_wh3_team.py`; injected members and deterministic worker completions | Partition/input checks, one-batch selection, local refusal and feedback identity pass against hand-specified cases | No claim of real concurrency or live control |
| 2 Independent scripted decisions | Bounded workers; narrow event/card/digest and fault-propagation changes; integration with the existing fake mailbox | Fast member dispatches before slow member completes; all lifecycles, timing and terminal traces are attributable | Simulated loop evidence; game effect still unverified |
| 3 Bounded live probe | Two fixed probe variants and a frozen run plan using the existing scenario | Repeated live motion/acknowledgement agrees with ownership and one member acts during the other's delay | Capability evidence only, no teamwork or win-rate claim |
| 4 First model member | One model plus one scripted teammate, guarded construction, team-aware prompt and exchange capture | Offline transport tests and bounded live use preserve inputs, feedback, costs and cleanup | One model call stream; no claim about parallel paid inference |
| 5 Bounded messages | One logged inbox per member, initially exercised by scripts and then one model plus a script | Recipient, expiry, delivery and consumption checks pass with the same action/ownership contract | A working channel does not establish communication benefit |
| 6 Parallel model calls | Actual outstanding budget reservations, worker cleanup and complete member exchange/export accounting | Simultaneous call/retry/failure tests respect the cap; a complete two-model comparison plan is costed | Enables a model-team study; policy strength remains to be measured |

Implement and review each slice before depending on it. Slice 1 is the recommended next
change. Source edits belong in an isolated worktree if a game queue is active; no live
job should run against changing source. No new scenario catalogue, generic workflow
engine, new game launcher or expanded Lua API is needed for slices 1–3.

### The checks that decide slices 1 and 2

Use existing fake observations and the play-loop fake mailbox, with a manually completed
future or explicit event barriers rather than timing-sensitive sleep assertions. These
are the checks agreed with the owner on 2026-10-21:

| Check | Independent reference and pass condition | Plausible error it detects |
|---|---|---|
| Partition and information | Hand-declared two-unit roster; each member owns exactly its unit. Missing/duplicate/extra units refuse initialization; changing hidden fields or sibling feedback does not change its input. Mutating one nested input cannot change another | Authority inferred from all visible units; shallow-copy leak; unexpected roster accepted |
| Local refusal | Member A orders B's unit or gives an illegal queued sequence; A gets a local rejection, no such order reaches the fake mailbox, and B's ready batch remains dispatchable | Entire team silently loses valid orders, or unauthorized order is sent |
| Feedback identity | Give a member a move followed by queued attack with distinct outcomes; only that member receives original one-based indices and order | Routing by unit ID loses per-order results; acknowledgement reaches wrong member |
| Independent progress and fairness | Hold A's worker behind a test event; B's request is written and acknowledged before A is released. Reverse roles, then keep B ready while A completes | Serial inference, hidden team barrier or starvation |
| Original timing and expiry | Member uses state at 10 s and submits to the engine at 13.4 s: trace and member feedback age are 3.4 s. At the declared dispatch age limit reject the batch. Separately test an order admitted before expiry but acknowledged after it | Reporting dispatch time as inference time; missing transport overage; treating queued submission as execution |
| Idle versus completed no-op | An idle poll and a member returning `[]` both traverse transport, but only the latter counts as a completed member decision | Inflated agent decision/action counts; accidental feedback to a running member |
| Ending and reset | End during a worker call, before an ack and with one close failure; record pending work and engine ending, close both members, then start a clean instance | Lost last events/results, wait for impossible ack, old result or inbox leaks into a new episode |
| Failure disposition | Inject an unexpected worker exception and a dispatcher invariant fault; the first stops as member-attributed policy failure, the second as a protocol/harness fault | Infinite retry of a causeless failure; scoring a dispatcher bug as controller weakness |

Use a deliberately broken ownership check, sequential worker implementation or timing
calculation to demonstrate that the corresponding important check fails. Avoid tests
that merely copy the adapter's own computed answer as the reference.

Once those test files exist, focused verification is:

```bash
uv run --locked pytest -ra tests/twwarhammer3/test_wh3_team.py \
  tests/twwarhammer3/test_wh3_play.py tests/twwarhammer3/test_wh3_controllers.py \
  tests/twwarhammer3/test_wh3_digest.py
uv run --locked ruff check .
```

Keep test scratch under an ignored `runs/twwarhammer3/` check directory. Add digest and
export tests only when their behavior changes; run the WH3 suite when the play-loop
integration is ready because terminal handling and ordinary controllers share that code.
No new Lua test is needed unless Lua actually changes.

### The agreed first live probe

Run four fresh launches of the named two-unit scenario: two delaying infantry and
two delaying cavalry, interleaved. Use a three-second cooperative delay on the selected
member's first decision and a five-second dispatch reply-age limit for the probe. Record these
constants; they are diagnostic choices, not recommended model deadlines. Keep the other
member ready to issue a simple visible move, then inspect its actual displacement as
well as its acknowledgement before the delayed member completes. If contact or terrain
makes the motion ambiguous, report unknown and revise the development probe.

The pass conditions are: correct unit authority on every request; fast-member dispatch
and observed movement during the other's delay in both role assignments; correct source
age and feedback; clean termination; and no evidence of a paused/slowed battle. An
acknowledgement alone does not establish movement. Preserve a failure or unknown instead
of extending the run until it passes. These four launches assess repeatable capability,
not a rate of successful teamwork.

Bound each diagnostic with an explicit setup/episode/process cap in the run plan. The
current episode timeout starts before waiting for the battle, so it is not a pure
active-combat duration: include measured startup allowance rather than promising exactly
90 seconds of battle from `--episode-timeout 90`. Stop at the named cap and retain any
truncated outcome as diagnostic evidence. Do not request a mid-battle rematch: that reset
route is unverified. Rematch/reset live checking can follow a naturally completed battle
in a separately bounded check; component reset tests are not a live rematch claim.

The owner agreed four launches at $0 within 30 minutes. Each process is capped at 360 s,
frontend setup at 240 s, and the diagnostic episode (including its initial battle wait)
at 90 s. This uses the usual menu/battle checks and process supervisor, with diagnostic
truncation outside the benchmark register. It does not relax scored `play` deadlines.
Require at least 0.25 m progress toward the declared point from the acknowledgement-time
position, with engine `moving`/`running` state, received while the delayed worker runs.
Both first moves must receive matching successful raw engine acknowledgements. Check
unit types independently against raw observations; require the 3 s worker delay and a
minimum 10 s clock sample within 15% of 1x. The clock check detects gross slowdown, not
every brief stall. `--recount OUTPUT` repeats the assessment without launching a game.
Check the installed build and active controller ownership; report any pin warning.
The run plan includes source revision, projected-input version, scenario, probe variant,
expected ownership, recording settings and output paths. All four jobs cost $0 in model
calls. Run the agreed check with a fresh output directory:

```bash
uv run --locked python tests/twwarhammer3/check_wh3_team.py \
  --output runs/twwarhammer3/team-live-<new-name>
```

## Adding models and messages after the probe

One model with one scripted teammate is the smallest next step. Use a dedicated team
factory that validates model settings, the existing ledger and cap before launch; an
importable class must not hide paid calls from these guards. Keep one paid call in flight
at this stage. Extend the model's rendered state to distinguish owned units from allies;
the current renderer does not consume the proposed `allies` field. Give it a versioned
team prompt and the same supported actions. Existing single-agent golden prompts should
stay unchanged unless their own version is intentionally revised.

The current `record_exchanges()` drains only `policy.api`. Add explicit aggregation for
member APIs, namespaced by episode/member/decision/exchange, and a team total taken after
workers settle. Record all member prompts, sources and backend identities; the adapter's
class hash alone does not describe a model team. Make the exporter retain member identity
before using these data for training. Pending and failed calls, including calls that
finish after the engine result, still need cost and exchange records. Agree a bounded
network-worker shutdown policy before the first paid live job.

For two simultaneous paid members, first implement and test a reservation held across
the entire reserve/send/settle interval. Admission must use charged spending **plus all
outstanding reservations**. Release unused reservation only after actual or conservative
uncertain-attempt charges are recorded. Retry and shutdown paths must settle exactly
once; restart must reconcile unresolved spending before admitting more calls. A lock
around the current `reserve()` check alone is insufficient. This changes `gameai`, so
check both games' model/ledger callers and keep the existing append-only ledgers intact.

For messages, begin with the existing two members and one bounded inbox each. Specify
size/count limits, expiry and delivery at the recipient's next decision; include messages
only in the recipient's copied input. Log send, delivery and first consumption separately.
Use simple scripts to prove recipient isolation and delayed/dropped message behavior
before asking a model to use the channel. A messages-disabled condition receives an empty
inbox with otherwise identical ownership and information. Add language-message generation
to the team reply format only at this stage, including its time and cost. Dynamic
ownership and shared resources remain separate extensions.

## When to expand beyond one army

After the adapter and evidence are usable, return to the evaluation plan's coordination
cards and budgeted comparisons. Add a configuration file only when a second concrete team
needs it; add shared resources or transfer authority only for a named task with its check.

Native allied armies and 2v2 need client/player/army identity, declared multiplayer setup,
replicated command effects, cross-client result agreement and revised session ownership.
They cannot be enabled by removing today's Lua guard. Reuse the member event/authority
contract, but inspect native control and visibility before designing the client transport.

Campaign work then adds a distinct faction observation/action contract, save/load and
turn transitions, synchronized actions and campaign-to-battle handoff. The existing
save/achievement decisions and loader issue remain gates. The evaluation plan supplies
the route through bounded cooperative tasks to full multiplayer campaigns; no campaign
adapter is part of the first implementation change.
