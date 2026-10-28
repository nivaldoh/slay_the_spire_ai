# The WH3 agent team: what is built and what comes next

Updated 2026-10-27. [team.py](../../src/twwarhammer3/battle/team.py) runs two members on
one army: the scripted probes, each owning one unit, and the model team (`team_llm_rules`).
Each member decides on its own copy of the public state and gets its orders sent while the
other is still thinking. The agreed component checks passed at `e8d1eda` (121 tests); the
live check passed 4/4 at `45fe7b0`, `b0ac9e3`, `31823f3` (the model-team branch before its
rebase onto `main`) and `3adbaa4` (rebased)
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
  not ID order; the probes declare one Swordsmen and one Knights unit. A new friendly unit
  (a reinforcement or summon) joins the member declaring its type or the one owning the
  rest. A unit left unowned (or a second unit for a one-unit member), a vanished unit ID or a
  different battle raises `TeamHarnessError`, a `ProtocolError`, so the episode ends as
  `unsupported_or_invalid`, not as a loss. Dead units stay in the roster. Reinforcements and
  behaviour through rout or rally are untested live.
- **Member input** (`team-v3`). `project()` copies an allowlist: battle, sequence, phase,
  time, remaining time, speed, the enemy roster, magic, `mode` (its purchase parts only for
  the army owner), terrain when present, the member's units in `friendly` with every field
  the `llm` renderer reads, the teammate's units in `allies` with the fields an enemy row
  has plus their condition (ammunition, fatigue, leadership % with its largest effect; the
  owner chose condition on 2026-10-27), but never their orders, queue or navigation; visible
  enemies; and on any unit a target only if that enemy is visible. The army owner also gets
  `army`. It drops `job`, the global `orders` acknowledgement (the teammate's results) and
  private fields. One difference from the single controller: a member does not see its own
  unit's current target while that enemy is out of sight, so its prompt says "no order" for
  that unit; the single controller sees it. Neither can order an attack on an unseen enemy.
  In the b43-b45 traces 11 of 24,248 friendly targets (7 of 10,293 observations, 45
  episodes) were hidden enemies.
- **Dispatch.** Each member has at most one decision running, on a two-thread pool. Each
  outer `decide` collects finished work without waiting, checks it, starts idle members on
  fresh copies and returns one member's whole batch, so engine feedback indices need no
  remapping. The earliest completed batch goes first; on a tie, not the member chosen last.
  With nothing ready it returns `[]` and no member is charged with a decision; a member's
  own `[]` is a decision and gets feedback. A member other than the army owner whose units
  are all destroyed is not asked until one of its units has men again.
- **Checks before dispatch.** A batch must pass `validate_orders` on the view the member
  decided on, as the single controller's batch is checked on its basis, so it may give any
  order to its own units, aim abilities at its teammate's (`allies`) and give army orders
  only as the army owner; the engine refuses each order the battle has made stale since. And,
  when `max_age_ms` is set (5 s for the probes, a probe constant), be younger than that on
  the battle clock. A failing batch gets local feedback with no engine time and the peer's
  ready batch is still sent. The play loop does not check a team's batch again.
- **Feedback.** `acknowledge` routes results to the selected member with their original
  indices, tagged `engine` or `local`. Latency comes from the member's
  own times: `think_s` from the worker, `roundtrip_s` from input delivery, `delay_ms` as
  engine `applied_ms` minus the member's source time (for a queued order, `applied_ms` is
  queue submission), and `transport_overage` when an age limit is set and reached.
- **Failure and cleanup.** Member calls go through `play.policy_call`, so a failure follows
  the single controller's rule: no valid reply or a provider error is a forfeit (a `team`
  `failed` event) and the member is asked again; a key, credit or budget stop ends the
  episode as `budget_exhausted`; any other exception ends it as a `PolicyFailure` that keeps
  its cause. `close()` sets the stop event, waits up to `CLOSE_WAIT_S` (30 s) for running
  calls, records every unsent or unacknowledged call as `discarded` (with `running` for one
  still in flight; a forfeit collected there is only discarded) and closes every member
  whose call has finished, even if one close fails. A stop from a call collected there still
  ends the episode as `budget_exhausted`. A member bug collected there is a policy failure
  naming its member even after the battle ended or ran out of time, where a single
  controller's call that straddles the end keeps the result (the agreed close-failure rule;
  changing it is the owner's call). A failure collected at cleanup never replaces an earlier
  failure. Only declared
  faults (`TeamHarnessError`) are harness faults: any other exception in `team.py`'s own
  code ends the episode as a policy failure, as a bug in a single controller does. Each
  episode builds a fresh team.
- **Trace and records.** Member events (partition, input, completed, failed, feedback,
  discarded, close_failed, fault) reach the episode trace through `drain_events()`, and member model
  exchanges, tagged with the member, through `drain_exchanges()`; `play.py` drains both
  after each decide and acknowledgement and after cleanup. The `decision` record carries the
  member's own behaviour (its prompt for a model) plus its name and decision ID; its wire
  `based_on` is the observation at dispatch, not the member's source, so
  member ages come from the feedback events. The result's decisions, delays, think times,
  invalid count, spend and calls count member batches (with per-member rows under
  `members`), and `polls` keeps the dispatcher's own. The card says `asynchronous`; `digest`
  and `watch` label member lines and show a member's prompt at its source time; `digest`
  measures a member's delay from that source and labels evidence recorded before `team-v2`
  (no `polls`) as dispatcher polls. `report`
  refuses team episodes and `export` excludes them until they read member records.
- **Clock.** Team times use the wall clock, as `play.py`'s think times do: WSL's monotonic
  clock ran 0-11% slow ([benchmark](benchmark.md)), the wall clock is stepped about 1 s every
  32 s, and this Python's thread timeouts follow the wall clock: 15 timed 3 s waits
  took 3.0-4.1 s by the wall clock and 2.2-3.0 s by the monotonic one
  (`runs/twwarhammer3/review-multiagent-20261021/lead-check/probe_wait.txt`). Measured
  against a Windows clock on 2026-10-28, both WSL clocks run about 6% slow
  ([clocks](integration.md#clocks-measured-2026-10-28)).
- **The model team.** `--policy team_llm_rules@MODEL/EFFORT` builds `ModelTeam` through
  `controllers.factories()`, so it gets `--budget-usd`, the ledger-file check, model
  validation and the OpenRouter cap like `llm_rules`. Both members (`TeamLLM`, the
  `llm_rules` controller on its member view) share the job's one `Ledger` and send function;
  `PARTITION` gives `cavalry` the Knights and `line` every other unit and the army orders.
  Each member's prompt is the `llm_rules` input plus a last section listing the teammate's
  units ([golden](../../tests/twwarhammer3/prompts/team_member.txt)). There is no age limit,
  like the single controller (a limit would also need `TeamLLM` to drop a local refusal's
  latency, which has no `delay_ms` for `llm.render_timing`). `Ledger` holds each call's
  reservation until it returns, so two calls at once cannot overspend the cap; near the cap
  a team therefore stops one reservation earlier than `llm_rules`. After cleanup starts no
  new call or reply retry is sent, but a request already in flight may still retry its
  transport; if it outlasts the 30 s wait, its cost reaches only the ledger and its hold
  lasts into the next episode.
- `play.py` refuses a team with `delay_ms` or `interval_ms` other than 0.

Members are trusted in-process code; separate Python dictionaries are not a sandbox.

Choices in `team.py` the owner has not decided (`team.py` is hashed into `source_sha256`, so
its markers live here):

JUDGEMENT: `team.py` PARTITION, ARMY_OWNER — assistant, 2026-10-21: the Knights against every
other unit, army orders with `line`. Another split is another team arm; team results rest on it.

JUDGEMENT: `team.py` project() target filter — assistant, 2026-10-21: a member sees its unit's
target only while that enemy is visible, the single controller always. Member prompts rest on it.

JUDGEMENT: `team.py` ModelTeam max_age_ms=None — assistant, 2026-10-21: no age limit, like the
single controller. A limit refuses old batches locally; what both arms compare rests on it.

JUDGEMENT: `team.py` CLOSE_WAIT_S — assistant, 2026-10-21: cleanup waits 30 s; a stop or bug in
it replaces an engine ending, a later call is abandoned and its cost reaches only the ledger.
Results and recorded spend rest on it.

JUDGEMENT?: `team.py` dead-member skip — assistant, 2026-10-22: a member other than the army
owner is not asked while all its units are destroyed. Asking it adds calls and cost.

JUDGEMENT?: `team.py` condition() largest effect — assistant, 2026-10-27: ally rows add the
morale effect the single controller shows; the owner named leadership %, fatigue and ammo.

## Checks

The component checks agreed with the owner on 2026-10-21 are in
[test_wh3_team.py](../../tests/twwarhammer3/team/test_wh3_team.py), with the play-loop,
controller and digest files [agreed-checks.md](../agreed-checks.md) names:

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
files). A second review that day found three more edits that passed every test: an ally row
showing a hidden target, feedback sent to the first member holding a batch, and a third unit
type accepted. The agreed file now fails each
(`runs/twwarhammer3/review-multiagent-20261021/lead-check/mutants.txt`).

The live check, [check_wh3_team.py](../../tests/twwarhammer3/team/check_wh3_team.py), makes four
fresh launches alternating `DelayInfantry` and `DelayCavalry`, at $0 and within 30 minutes
(360 s per process, 240 s for setup, 90 s per episode including the wait for the battle). A
launch passes when:
- every dispatched order names its member's unit (checked against raw unit types);
- both first moves get matching successful raw engine acknowledgements, every member
  feedback comes from the engine (no local refusal), and each member's
  age equals the raw engine `applied_ms` minus the time of the raw observation with the
  sequence number the adapter recorded, so a source time that disagrees with it fails (this
  rule and the wall-clock samples changed after the owner agreed the check; marked in the
  checker);
- after its acknowledgement, while the delayed worker still runs, the fast unit is moving or
  running and at least 0.25 m closer to its point;
- the delayed worker took 3-4.5 s (wall clock, like the observation samples; a wall step
  over 1.5 s in a wait's last moments could still exceed 4.5 s, rarely);
- a clock sample of at least 10 s runs within 15% of 1x. This catches gross slowdown, not a
  brief stall; the per-sample speed check cannot fail, because the mod writes `speed` 1 and
  `awaiting_orders` false as constants;
- the episode ended `truncated` or with an engine result, the manifest is closed and no game
  process is left.

A failure or unknown stands; do not keep rerunning until it passes. `--recount OUTPUT`
reassesses saved evidence without a game and without rewriting its `checks.json`, and
`plan.json` records the run settings. The saved evidence recounts 4/4 with the stricter age
check.
Mid-battle rematch is not used and remains unverified.

Results: 4/4 at `3adbaa4` (2026-10-28, `runs/twwarhammer3/team-live-20261027-rebased/`;
fast members 0.6 s, delayed 3.6-3.9 s, clock ratio 0.991-1.010), at `b0ac9e3` on `main`
(2026-10-23) and at `31823f3` on the branch (`runs/twwarhammer3/team-live-20261022-tip/`); after the rebase onto `main` the saved runs
of `45fe7b0` and `31823f3` recount 4/4 with the merged checker. `31823f3`, these recounts
and later runs rest on JUDGEMENT `tests/twwarhammer3/team/check_wh3_team.py` member age
witness; every live pass rests on its Movement witness. At `45fe7b0`: 4/4 launches
passed in about 12 minutes. The check's first qualifying samples were 0.42-1.76 m closer,
1.74-1.84 s before the peer completed; at the last sample before it completed, the fast
units were 4.6-10.8 m closer, moving and running (review recount of `observations.jsonl`).
Member order age was 0.6 s for the fast member and 3.3-3.9 s for the delayed one; clock
ratio 0.9998-1.0006. Evidence: `runs/twwarhammer3/team-live-20261021/`.

Proposed, not agreed (owner's call): the 0.25 m threshold is below the Knights' idle jitter
(one 5.16 m jump between the two idle samples before any order, probe 3). So when the
Knights are the fast unit, the pass rests on the moving flag, and a unit already moving
before its order would pass. Require the fast unit to be idle in every sample before its
acknowledgement and report that as a failed probe, not an assertion error. Every unit was
idle before its order in all four probes, so the strict recount of the saved evidence still
passes 4/4 (`runs/twwarhammer3/review-team-20261021/correctness/recount/checks.json`); no
game time is needed.

## Next

Team work is a later controller arm on the Land Battle benchmark ([owner,
2026-10-27](../owner-direction.md)); the structure screen in
[team-structures.md](team-structures.md) waits for that battle's first team-vs-single
result. The live check passed at the rebased `3adbaa4`, so `wh3-model-team` merges (owner,
2026-10-27). Before the first team battle:
1. `report` and `export` read member records: order ages from each member's source time,
   calls and forfeits from team events, exchanges keyed by member (both members number theirs
   `m1`, `m2`, ...). The card board uses `member_source_sha256` or skips team rows (today it
   takes them, and counting both members' decisions roughly halves the decision-gap part of
   their information age), and `result.json` counts calls abandoned at cleanup.
2. An agreed check for `team_llm_rules`: proposed, `team/test_wh3_model_team.py` plus a
   written pass list for the first paid battle.
3. A check that the pinned backend serves two calls at once (it has only served one).

Then, with the owner's go-ahead and budget, one paid `team_llm_rules` battle on the Land
Battle, as its own job. Messages and
teams beyond one army stay deferred: [plan §4](multi-agent-plan.md#communication) and
[§9-§10](multi-agent-plan.md#9-stages).
