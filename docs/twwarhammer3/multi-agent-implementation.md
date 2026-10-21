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

- **Ownership.** On the first `decide` (the first Deployed observation), `_partition` binds
  `infantry` to the one Swordsmen unit and `cavalry` to the one Knights unit, by type, not
  ID order. Any other roster, a changed unit ID or a different battle raises
  `TeamHarnessError`, a `ProtocolError`, so the episode ends as `unsupported_or_invalid`,
  not as a loss. Dead units stay in the roster, but a new friendly unit (a reinforcement or
  summon) ends the episode. Behaviour through rout or rally is untested live.
- **Member input.** `project()` copies an allowlist: battle, sequence, phase, time,
  remaining time (`remaining_ms`; the end-of-battle `timer` record is dropped), speed, mode,
  terrain, the member's unit in `friendly`, the other in `allies` and the visible enemies;
  per unit only ID, type, position, bearing, men, state and a target if that enemy is
  visible. It drops `job`, the global `orders` acknowledgement (the teammate's results) and
  private fields, but also fields single-agent controllers get (`enemy_roster`, `armies`,
  `hp`, `class`, `men0`, abilities, behaviours).
- **Dispatch.** Each member has at most one decision running, on a two-thread pool. Each
  outer `decide` collects finished work without waiting, checks it, starts idle members on
  fresh copies and returns one member's whole batch, so engine feedback indices need no
  remapping. The earliest completed batch goes first; on a tie, not the member chosen last.
  With nothing ready it returns `[]` and no member is charged with a decision; a member's
  own `[]` is a decision and gets feedback.
- **Checks before dispatch.** A batch must be under 5 s old on the battle clock
  (`max_age_ms`, a probe constant), use only `move`, `attack` and `halt`, and pass
  `validate_orders` on the member's own view, which holds only its unit. A failing batch
  gets local feedback with no engine time and the peer's ready batch is still sent. The play
  loop's validation runs after this as before.
- **Feedback.** `acknowledge` routes results to the selected member with their original
  indices, tagged `engine`, `outer_validation` or `local`. Latency comes from the member's
  own times: `think_s` from the worker, `roundtrip_s` from input delivery, `delay_ms` as
  engine `applied_ms` minus the member's source time (for a queued order, `applied_ms` is
  queue submission), and `transport_overage` when that reaches the age limit.
- **Failure and cleanup.** A member exception becomes a `PolicyFailure` that keeps its
  cause, so `_drive` does not retry it. `close()` sets the stop event, waits for the
  workers, records every unsent or unacknowledged call as `discarded` and closes both
  members even if one fails. Each episode builds a fresh `TeamPolicy`.
- **Trace.** Member events (partition, input, completed, selected, feedback, discarded,
  failures) reach the episode trace through `drain_events()`, which `play.py` calls after
  each decide and acknowledgement and after cleanup. The `decision` record ties a member's
  decision ID to its mailbox request; its wire `based_on` is the observation the dispatcher
  checked against, not the member's source, so member ages come from the feedback events.
  The card says `asynchronous`; `digest` labels its header counts as dispatcher polls and
  prints member feedback with member ages.
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

Proposed order (plan [§9](multi-agent-plan.md#9-stages)): once the [starting-set
screen](tactic-cards.md#the-starting-set-proposal-2026-10-21) has picked the comparison card
and a held-out variant is reserved, build one set of focused commits that lets two model
members play it. Run the component checks after each commit and the live check once at the
end. Then, with the owner's go-ahead, play one paid smoke battle. There is no separate
milestone for one model plus one script, and messages wait for the first comparison.

1. **Partition.** Declared unit lists per member for the chosen card; for the rank-5 line,
   the Knights against the line and guns. The card needs no reinforcements or summons,
   unless the partition says who gets a new unit. Army-level orders (spells, purchases)
   belong to one named member or are left out.
2. **The single controller's information and orders.** Widen `project()` to the public
   fields the `llm` renderer reads, still dropping `job`, the global `orders`
   acknowledgement and hidden targets (the agreed input test). Allow every order type on the
   member's own units. Render the teammate's units as allies, plus one ownership sentence,
   as a logged `llm`/`llm_rules` prompt version that only team members get; the golden
   prompts of the existing controllers stay byte-identical.
3. **One staleness rule for both arms.** The single controller has no age limit. In six
   GLM-5.3 low battles from b43-b45 (`emp-line-grn-raid` three times, Knights/Swordsmen
   three times), 123 of 632 acknowledged requests were at least 5 s old; in the one rank-5
   line battle, 22 of 224 (`runs/twwarhammer3/review-team-20261021/doc-verify/ages.py`).
   Pass the rule to the model team explicitly: none, or one rule both arms share.
4. **Two calls at once within the cap.** `Ledger.reserve()` checks `spent + cost` but holds
   nothing, so two concurrent calls could both pass against the same remainder. Add a held
   total under a lock: `reserve` admits a call only if spent + held + cost fits and adds the
   cost to held; `Model.call` releases it in a `finally` after charging. About ten lines and
   a two-thread test, in its own commit, since `gameai` is in both games' play scope. A
   crash already loses an in-flight charge today, so no restart reconciliation. Build the
   team as a named model policy in `controllers.factories()`, so it shares the job's one
   `Ledger`: a `package.module:Class` import, like `DelayInfantry`, skips `--budget-usd`,
   the ledger-file check, model validation and the OpenRouter $50 cap, and its card reports
   a self-reported cost.
5. **Records.** `record_exchanges()` drains team events and `policy.api`, not member APIs:
   drain each member's exchanges under its name, record member prompts, sources and backends
   in the card, and keep member identity in `export`. The register's `delay_s` and the
   report's order age read the outer loop, which for a team measures dispatcher polls (0.3 s
   in every probe against member ages up to 3.9 s): take member ages and decision counts
   from the team feedback events before a team job writes register rows.
6. **Bounded shutdown.** `close()` waits for running workers, and a model call can take far
   longer than the probe's 3 s. Before a paid live job, decide how long cleanup waits and
   how an abandoned call is charged and recorded.

This change needs the live rerun anyway, so fold in the small cleanups the 2026-10-21 review
found: drop `play.py`'s unread `received_monotonic`; drop the `selected` event (the
`decision` record and `discarded` already carry it); share one refusal builder between
`team.py` and `play.py`; let `digest` recognize a team by its card's `members` rather than
the literal `script-team-v1`; test or drop `play.py`'s delay/interval guard.

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
