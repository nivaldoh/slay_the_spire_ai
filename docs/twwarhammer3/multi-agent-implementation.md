# The WH3 agent team: what is built and what comes next

Updated 2026-10-21. [team.py](../../src/twwarhammer3/battle/team.py) runs two trusted
scripted members on one army. Each owns one unit, decides on its own copy of the public
state and gets its orders sent while the other is still thinking. The agreed component
checks passed at `e8d1eda` (121 tests) and the live check at `45fe7b0`
([AGENTS.md](../../AGENTS.md#verification-hard-rule)). They cover ownership, independent
progress, feedback and cleanup for two scripts; model teams, messages and teamwork quality
are unverified. The [evaluation plan](multi-agent-plan.md) says what a team is for; this
page covers the code.

## What team.py does

The probe battle is `emp-knights-emp-swordsmen` (one Swordsmen, one Empire Knights unit).
`DelayInfantry` and `DelayCavalry` are zero-argument controllers, so they load through the
usual `package.module:Class` syntax. Each member (`_MoveOnce`) sends one running move 20 m
ahead along its unit's bearing on its first decision and `[]` after that; the delayed member
first waits 3 s on a stop event that cleanup can wake.

- **Ownership.** A member is declared by one unit type (exactly one unit of it), a tuple of
  types (one or more units) or `None` (every unit nobody else declares). On the first
  `decide` (the first Deployed observation), `_partition` binds each member's units by type,
  not ID order; the probes declare one Swordsmen and one Knights unit. A unit left unowned,
  a changed unit ID, a new friendly unit (a reinforcement or summon) or a different battle
  raises `TeamHarnessError`, a `ProtocolError`, so the episode ends as
  `unsupported_or_invalid`, not as a loss. Dead units stay in the roster. Behaviour through
  rout or rally is untested live.
- **Member input** (`team-v2`). `project()` copies an allowlist: battle, sequence, phase,
  time, remaining time, speed, the enemy roster, magic, `mode` (its purchase parts only for
  the army owner), terrain when present, the member's units in `friendly` with every field
  the `llm` renderer reads, the teammate's units in `allies` with only the fields an enemy
  row has (never their orders, queue or navigation), visible enemies, and a target only if
  that enemy is visible. The army owner also gets `army`. It drops `job`, the global
  `orders` acknowledgement (the teammate's results) and private fields.
- **Dispatch.** Each member has at most one decision running, on a two-thread pool. Each
  outer `decide` collects finished work without waiting, checks it, starts idle members on
  fresh copies and returns one member's whole batch, so engine feedback indices need no
  remapping. The earliest completed batch goes first; on a tie, not the member chosen last.
  With nothing ready it returns `[]` and no member is charged with a decision; a member's
  own `[]` is a decision and gets feedback.
- **Checks before dispatch.** A batch must pass `validate_orders` on the member's own view,
  so it may give any order to its own units and army orders only as the army owner, and,
  when `max_age_ms` is set (5 s for the probes, a probe constant), be younger than that on
  the battle clock. A failing batch gets local feedback with no engine time and the peer's
  ready batch is still sent. The play loop's validation runs after this as before.
- **Feedback.** `acknowledge` routes results to the selected member with their original
  indices, tagged `engine`, `outer_validation` or `local`. Latency comes from the member's
  own times: `think_s` from the worker, `roundtrip_s` from input delivery, `delay_ms` as
  engine `applied_ms` minus the member's source time (for a queued order, `applied_ms` is
  queue submission), and `transport_overage` when an age limit is set and reached.
- **Failure and cleanup.** Member calls go through `play.policy_call`, so a failure follows
  the single controller's rule: no valid reply or a provider error is a forfeit (a `team`
  `failed` event) and the member is asked again; a key, credit or budget stop ends the
  episode as `budget_exhausted`; any other exception ends it as a `PolicyFailure` that keeps
  its cause. `close()` sets the stop event, waits up to `CLOSE_WAIT_S` (30 s) for running
  calls, records every unsent or unacknowledged call as `discarded` (with `running` for one
  still in flight) and closes every member whose call has finished, even if one close fails.
  Each episode builds a fresh team.
- **Trace and records.** Member events (partition, input, completed, failed, selected,
  feedback, discarded) reach the episode trace through `drain_events()`, and member model
  exchanges, tagged with the member, through `drain_exchanges()`; `play.py` drains both
  after each decide and acknowledgement and after cleanup. The `decision` record carries the
  member's own behaviour (its prompt for a model) plus its name and decision ID; its wire
  `based_on` is the observation the dispatcher checked against, not the member's source, so
  member ages come from the feedback events. The result's decisions, delays, think times,
  invalid count, spend and calls count member batches (with per-member rows under
  `members`), and `polls` keeps the dispatcher's own. The card says `asynchronous`; `digest`
  and `watch` label member lines, and `digest` labels evidence recorded before `team-v2` (no
  `polls`) as dispatcher polls.
- **The model team.** `--policy team_llm_rules@MODEL/EFFORT` builds `ModelTeam` through
  `controllers.factories()`, so it gets `--budget-usd`, the ledger-file check, model
  validation and the OpenRouter cap like `llm_rules`. Both members (`TeamLLM`, the
  `llm_rules` controller on its member view) share the job's one `Ledger` and send function;
  `PARTITION` gives `cavalry` the Knights and `line` every other unit and the army orders.
  Each member's prompt is the `llm_rules` input plus a last section listing the teammate's
  units ([golden](../../tests/twwarhammer3/prompts/team_member.txt)). There is no age limit,
  like the single controller. `Ledger` holds each call's reservation until it returns, so
  two calls at once cannot overspend the cap. After cleanup starts no new call or reply
  retry is sent, but a request already in flight may still retry its transport, and its cost
  then reaches only the ledger.
- `play.py` refuses a team with `delay_ms` or `interval_ms` other than 0.

Members are trusted in-process code; separate Python dictionaries are not a sandbox.

## Checks

The component checks agreed with the owner on 2026-10-21 are in
[test_wh3_team.py](../../tests/twwarhammer3/test_wh3_team.py), with the play-loop,
controller and digest files AGENTS.md names:

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

Deliberately broken ownership, concurrency and source-age code each failed the matching test
(log, b49). The review on 2026-10-21 found that no test checked oldest-first selection: a
selector that ignores or reverses completion order passed all 120 tests at `45fe7b0`.
`test_the_oldest_completed_batch_goes_first` now fails on both
(`runs/twwarhammer3/review-team-20261021/selector_mutation.txt`;
`runs/twwarhammer3/review-team-20261021/doc-verify/selector_all_files.txt` for all four
files).

The live check, [check_wh3_team.py](../../tests/twwarhammer3/check_wh3_team.py), makes four
fresh launches alternating `DelayInfantry` and `DelayCavalry`, at $0 and within 30 minutes
(360 s per process, 240 s for setup, 90 s per episode including the wait for the battle). A
launch passes when:
- every dispatched order names its member's unit (checked against raw unit types);
- both first moves get matching successful raw engine acknowledgements, every member
  feedback comes from the engine (no local or outer-validation refusal), and each member's
  age equals engine `applied_ms` minus its source time;
- after its acknowledgement, while the delayed worker still runs, the fast unit is moving or
  running and at least 0.25 m closer to its point;
- the delayed worker took 3-4.5 s;
- a clock sample of at least 10 s runs within 15% of 1x. This catches gross slowdown, not a
  brief stall; the per-sample speed check cannot fail, because the mod writes `speed` 1 and
  `awaiting_orders` false as constants;
- the episode ended `truncated` or with an engine result, the manifest is closed and no game
  process is left.

A failure or unknown stands; do not keep rerunning until it passes. `--recount OUTPUT`
reassesses saved evidence without a game, and `plan.json` records the run settings.
Mid-battle rematch is not used and remains unverified.

Result at `45fe7b0`: 4/4 launches passed in about 12 minutes. The check's first qualifying
samples were 0.42-1.76 m closer, 1.74-1.84 s before the peer completed; at the last sample
before it completed, the fast units were 4.6-10.8 m closer, moving and running (review
recount of `observations.jsonl`). Member order age was 0.6 s for the fast member and 3.3-3.9
s for the delayed one; clock ratio 0.9998-1.0006. Evidence:
`runs/twwarhammer3/team-live-20261021/`.

Proposed, not agreed (owner's call): the 0.25 m threshold is below the Knights' idle jitter
(one 5.16 m jump between the two idle samples before any order, probe 3). So when the
Knights are the fast unit, the pass rests on the moving flag, and a unit already moving
before its order would pass. Require the fast unit to be idle in every sample before its
acknowledgement and report that as a failed probe, not an assertion error. Every unit was
idle before its order in all four probes, so the strict recount of the saved evidence still
passes 4/4 (`runs/twwarhammer3/review-team-20261021/correctness/recount/checks.json`); no
game time is needed.

## Next: a model team

On the `wh3-model-team` branch (offline checks only; 2026-10-21): the six items listed here
before are built: a declared partition, the single controller's information and order set,
no age limit, the ledger hold, member records and exchanges, and a 30 s bounded cleanup.
Still to do before a comparison:
1. Rerun the agreed live check at the branch's tip: the scripted team's trace shape and
   input version changed.
2. `report.py` (order ages and forfeits from team events), `export.py` (member exchange IDs
   collide: export of a team job fails with "ambiguous model exchange") and the card board's
   identity (`member_source_sha256` is recorded but not grouped on).
3. The card: once the [starting-set
   screen](tactic-cards.md#the-starting-set-proposal-2026-10-21) keeps it, check that
   `PARTITION` fits it; then one paid smoke battle with the owner's go-ahead.

The small cleanups the 2026-10-21 review found still wait: drop `play.py`'s unread
`received_monotonic` and the `selected` event, share one refusal builder between `team.py`
and `play.py`, and test or drop `play.py`'s delay/interval guard.

### Messages, later

Only if the first comparison shows the split team at least even with the single controller,
or losing through visible coordination failures (plan §9 C). Then: one bounded inbox per
member (size and count limits, expiry), delivered in the recipient's next input; send,
delivery and first use logged separately; scripts show recipient isolation and delayed or
dropped messages before a model uses the channel; the no-message arm gets an empty inbox
with everything else identical; writing messages counts in the team's time and cost.

### Beyond one army

Deferred (no second machine for now; owner, 2026-10-21). Native allied armies and 2v2 need
client, player and army identity, a declared multiplayer setup, replicated command effects,
cross-client result agreement and a revised session ownership. Removing the Lua guard does
not enable them. Campaigns need their own faction observation and action contract,
save/load, turn transitions and campaign-to-battle handoff, behind the owner's save and
achievement decisions. The plan's §9 and §10 give the stages.
