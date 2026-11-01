# Agreed checks

The owner's agreed verification methods under the
[hard rule](../AGENTS.md#verification-hard-rule): a feature counts as verified only at
revisions where its check passed. Each entry gives the feature, the check and command, the
date agreed and the last passing revision. Only the owner agrees a new entry. Moved here from
AGENTS.md on 2026-10-28 to keep that file lean (owner).

Offline passes after 2026-10-29 are recorded by the exit gate, `check.py` (owner, 2026-10-29:
"(a)"): each run appends a line to `runs/checks/agreed-passes.jsonl` with the revision and, for
every entry below that has a pytest command, whether its tests passed in that run. A line
counts for its revision only when its `at_revision` is true: the files were HEAD's before and
after the run (rests on JUDGEMENT? `check.py` Pass at a revision). An entry that also has a
live command is recorded as "(pytest part only)" and says nothing about the live check. It is
read from the whole suite, not the command run alone; `runs/` has no backup. The "passed at"
revisions written below are the earlier passes.

- WH3 GaP temporary author-initiation check (agreed 2026-11-01, owner: "Ok, we can proceed
  with this solution temporarily"): a caller-declared initiator must have an attack route
  before contact; waiting members remain allowed. Reject a stalled specialist reply via
  the existing limited repair, retaining rejected attempts and charges. Check the first
  permitted member starting view; private/outcome changes must not change model inputs.
  Command: `uv run --locked pytest -ra
  tests/twwarhammer3/graph/test_wh3_graph_initiation.py`.
  Check stalled/fixed graphs, contact branches, move-before-attack, invalid identities,
  projection, repair/exhaustion, revision and saved proof identity; plant an always-pass
  check, wrong contact branch and accidental checking of waiting members.
  This is an optimistic control-flow check: possible skill exits do not prove movement,
  contact, completion, universal progress or strength. Semantics rest on JUDGEMENT
  `battle/graph_initiation.py` Temporary initiation semantics. Passed at `4f0c3fc`: 52 cases
  on a clean tracked tree, independently replayed; three semantic plants caught on the
  same source bytes. Evidence: `runs/gap-initiation-20261101/agreed-at-revision.json` and
  `review/author-followup/report.txt` there.
- WH3 GaP live target preferences (agreed 2026-11-01, owner: "I agree with the proposed
  live verification method"): delayed/stale replies, cancellation, ownership, independent
  graph/team progress, fresh instances, public inputs and shared budgets; canned replies
  and planted wrong implementations. Component command: `uv run --locked pytest -ra
  tests/gameai/test_goal_transport_timeout.py
  tests/twwarhammer3/graph/test_wh3_graph_goals.py
  tests/twwarhammer3/graph/test_wh3_graph_goal_factory.py
  tests/twwarhammer3/graph/test_wh3_graph_goal_configuration_guards.py
  tests/twwarhammer3/graph/test_wh3_graph_goal_view.py`.
  Live: one fresh 1x diagnostic, two Haiku members and two goal requests each; each
  eligible preference must reach selection, an owned accepted attack and a later public
  target reading, with a change from first target to second. Raw records must match
  controller/graph/battle/source identities, model requests, ledger charges and cleanup;
  check engine speed and the agreed Windows-clock band. No strength/completion claim.
  Frozen local command: `uv run --locked python
  runs/gap-continuation-20261101/goal-probe-draft.py --output OUTPUT`;
  `--recount OUTPUT` never launches. Checker SHA256:
  `4c992d383a9c0484b1a975e9a87c3484aa77c180486fd6300624a06cca43ac26`.
  Bounds rest on JUDGEMENT Goal probe bounds in that script/card. The conservative
  transient-target rejection can fail a valid run; failure alone is not a runtime bug.
  Passed at `87518f9`: 54 component cases in a clean checkout and one live probe, with
  four target dispatch/readback witnesses, zero invalid orders and clean shutdown.
  Probe: `runs/twwarhammer3/graph-goals-live-20261101-01/`; independent recount in
  `runs/gap-continuation-20261101/review/live01/`. Diagnostic truncation is not a gameplay
  outcome; this establishes no strength, learning or live skill-completion claim.
- WH3 GaP execution viewer (agreed 2026-11-01, owner: "Use this check"): compare graph
  identity, node transitions, ordinary orders, acknowledgements and completion witnesses
  against raw configuration/trace rows; plant wrong mappings, then exercise both saved
  battles in a browser. Reader command: `uv run --locked pytest -ra
  tests/twwarhammer3/graph/test_wh3_graph_view.py`. Browser command:
  `NODE_PATH=~/.cache/wh3-playwright/node_modules node
  tests/twwarhammer3/graph/check_wh3_graph_view.cjs OUTPUT_DIR PAGE.html EPISODE [EPISODE ...]`.
  Browser cases must use raw trace/result records, not the collector's JSON as their reference.
  The view must distinguish source and collection times, ready and started nodes, and
  acceptance and completion. No interpolation or inferred missing effects. Evidence:
  `runs/gap-continuation-20261101/`; passed at `b8f8cb7` in a clean checkout (31 reader
  cases, both recorded battles in a browser, plus wrong-member and ack-as-completion
  plants). Exact source/HTML hashes: `viewer-check-at-revision.json` there.
- WH3 initial GaP (agreed 2026-10-31): offline graph typing, branches/loops,
  effect-based completion, independent team progress, stale targets, public information
  boundaries, fresh episodes and canned multi-LLM author/revision replies, with planted
  wrong implementations. Initial component command: `uv run --locked pytest -ra
  tests/twwarhammer3/test_wh3_graph.py tests/twwarhammer3/test_wh3_graph_configured.py
  tests/twwarhammer3/team/test_wh3_graph_team.py
  tests/twwarhammer3/graph/test_wh3_graph_live_check.py
  tests/twwarhammer3/graph/test_wh3_graph_author.py`. Runtime part passed 35 cases at
  `ff5e4ea`; all 91 component cases passed at `d6dfe92`
  (`runs/gap-implementation-20261031/components-d6dfe92.txt`). Author/revision component
  cases do not establish learning or live effects.
  Live method: fresh 1x attempts, movement with no-order controls, then contact/charge
  with public target and melee witnesses. PC available tonight. No strength/learning claim.
  Command: `uv run --locked python tests/twwarhammer3/graph/check_wh3_graph.py --output
  runs/twwarhammer3/graph-live-NEW`; `--recount OUTPUT` reads saved evidence without launching.
  Live passed 3/3 at `d12be58` (`runs/twwarhammer3/graph-live-20261101-extended/`) after
  the owner approved 540 s contact; first 360 s run remains failed. Holds/firing unchecked.
  One authored-plan follow-up at `5c02d08` passed the unchanged contact assessor and
  pre-contact infantry attack/matching-melee audit; movement/no-order controls were not
  rerun. Engine lost at 666.8 s; no strength claim. Raw checks/citations:
  `runs/gap-initiation-20261101/review/live-followup/` (one battle).
- WH3 scripted two-member team: ownership, public inputs, independent progress, feedback,
  timing and cleanup: `uv run --locked pytest -ra tests/twwarhammer3/team/test_wh3_team.py
  tests/twwarhammer3/test_wh3_play.py tests/twwarhammer3/test_wh3_controllers.py
  tests/twwarhammer3/test_wh3_digest.py`; agreed 2026-10-21; passed at `e8d1eda` (121 tests)
  and at the merged model team (123 tests).
  Live: `uv run --locked python tests/twwarhammer3/team/check_wh3_team.py --output
  runs/twwarhammer3/team-live-<new-name>`: four fresh launches alternating the delayed
  member; the correct unit moves after its acknowledgement while its peer thinks; 1x, $0,
  30-minute cap. Passed 4/4 at `45fe7b0` (`runs/twwarhammer3/team-live-20261021/`),
  `b0ac9e3`, `31823f3` and `3adbaa4` (`runs/twwarhammer3/team-live-20261027-rebased/`; the
  merged revision's play-scope files are identical). Its age rule changed after agreement
  (JUDGEMENT in the checker), kept for now (owner, 2026-10-28). No model-team, strength or
  multiplayer claim.
- WH3 saved armies and experience: save a known army, change it, restart WH3 and reload;
  compare unit types, counts and ranks. Set several ranks using both increase and decrease,
  comparing lobby readback and battle-start ranks/stats: `uv run --locked python
  tests/twwarhammer3/check_wh3_army_setup.py --integration --output runs/twwarhammer3/army-check-<new-name>`.
  Extended 2026-10-19: disturb declared settings, check funds/permission refusals and a fixed
  reserve pool, then restore original settings. Passed with `e32b1b5` sources (four launches,
  ten-unit saved roster, three mounts, ranks 0/1/3/9, seven reserves; attack/defence exact,
  leadership XP bonuses relative to rank zero; that relative reading came after agreement,
  JUDGEMENT? in the checker). Restart uses supervised shutdown; graceful
  exit, other modes, reinforcement XP and policy strength remain unverified.
- WH3 UI requests, failure reporting, scheduling, startup-query errors and session lifetime:
  real Python/Lua component checks, with simulated game APIs/play-loop observations:
  `uv run --locked pytest -ra tests/twwarhammer3`. Agreed 2026-10-19; passed at `6291377`.
  These checks establish component contracts, not live order effects or policy strength.
- Play commands refuse a missing ledger file: `uv run pytest
  tests/fullrun/test_spire_cli.py::test_play_refuses_a_missing_ledger_before_any_job
  tests/twwarhammer3/test_wh3_controllers.py::test_each_model_controller_gets_its_own_prompt_and_the_shared_budget`;
  agreed 2026-10-18; passed at `6291377`.
- WH3 replacement mailbox requests reach Lua's pending state; duplicate delivery is rejected:
  `uv run --locked pytest -ra
  tests/twwarhammer3/test_wh3_mailbox.py::test_new_mailbox_requests_reach_lua_without_disabling_duplicate_rejection`;
  agreed 2026-10-19; passed at `6291377`. No game execution claim.
- WH3 non-finite order fields are rejected before transmission, with invalid-batch feedback:
  `uv run --locked pytest -ra tests/twwarhammer3/test_wh3_protocol.py
  tests/twwarhammer3/test_wh3_play.py::test_illegal_scripted_orders_are_counted_and_not_sent`;
  agreed 2026-10-19; passed at `6291377`. Play-loop observations are simulated.
- WH3 battle checkpoints restore exactly: a source battle (tick-1 battle script, orders
  before and after a checkpoint at tick 1200), two restores with the same later orders and
  one with a changed order; per-tick native checksums and Lua readings:
  `uv run --locked python tests/twwarhammer3/check_wh3_checkpoint.py --output
  runs/twwarhammer3/checkpoint-check-<new-name>` (pass rule offline:
  `uv run --locked pytest -ra tests/twwarhammer3/test_wh3_checkpoint.py`); agreed
  2026-10-25; passed at `7b1e2ed` (`checkpoint-check-20261025b/`) and at `6fdb271` on main
  (`runs/twwarhammer3/checkpoint-check-20261025c/`, 4 launches: 0 mismatches over 2,001
  ticks and 9/9 readings per restore, the changed one diverged at 1303; a bystander replay
  was set aside and returned unchanged), and at `dcb8b5a` on main with the script as of
  `6cd5fbe`, which adds completeness checks (`runs/twwarhammer3/checkpoint-check-20261028/`,
  same counts; changed diverged at 1303; recorded 2026-10-28 under the owner's "use common
  sense for now, I'll review later"), and at `d3ba6aa` on the checkpoint-RL branch, merged
  into main on 2026-10-28, with the same script bytes as main on 2026-10-30
  (`runs/twwarhammer3/checkpoint-check-20261026-rl/`, 4 launches: 0 mismatches and 9/9
  readings per restore, changed diverged at 1303; recorded 2026-10-30 at the owner's yes,
  "About the quick items, yes to all"). Custom land battle, build 25961564; no claim for
  real-time script timers, our bridge mod's state, the loading screen, other battle types
  or builds.
- WH3 engine ending kept after a late controller failure (acknowledge or `close()`):
  `uv run --locked pytest -ra
  tests/twwarhammer3/test_wh3_play.py::test_a_controller_failure_after_the_ending_keeps_the_engine_result`
  (fails on the parent of `b536ae6`); agreed 2026-10-21; passed at `080be70`. No game
  execution claim; which result counts is unchanged.
- WH3 siege checkpoints: a source, two restores with identical later orders and one with a
  changed order; require every planned native checksum and live reading, witnessed tested
  unit states and a spell taking effect and expiring. Agreed 2026-10-25; owner then chose
  "Use live engine values (Recommended)": numeric morale/speed readings, armour and spell
  witnesses, with cached infocard-stat differences reported separately. Command:
  `uv run --locked python tests/twwarhammer3/check_wh3_checkpoint_siege.py --output
  runs/twwarhammer3/siege-<new-name>` (15 launches, three declared cases/four saved states).
  Passed at `2e2acbe` (`runs/twwarhammer3/siege-final-20261025b/`): 15 completed logs
  (11 new, four reused with identical runtime/agent/input bytes), eight identical restores
  with zero mismatches over 2,400 planned ticks each and 194 live readings total; all four
  changed controls diverged after their orders. Three declared cases, two maps, build
  25961564 only. Source-only manual-tower supplement passed at `fbdba3b`: seven launches,
  construction/completed checkpoints, four exact restores (3,300 ticks each/66 readings).
  [Scope and limits](twwarhammer3/checkpoints.md#siege-check); other cases unverified.
- WH3 checkpoint-RL step run (restore to the engine ending, exact-tick injection, attribution,
  identical attempts): `uv run --locked python tests/twwarhammer3/check_wh3_restored_episode.py
  --output runs/twwarhammer3/rl/stage1-<new-name>` (7 launches; `--recount`); agreed 2026-10-26.
  Ran at `9c11bc6`, passed on recount at `d3ba6aa` after the result-collapse gap rule was
  added on seeing the run (`runs/twwarhammer3/rl/stage1-20261026/`). Land scenario only.
  Recorded on the branch; moved here with its merge to main (2026-10-28).
- WH3 checkpoint-RL closed loop (overfit check, then the trained choice executed and compared
  with its audit attempt, with a deranged control): `twwarhammer3 rl confirm PLAN`; agreed
  2026-10-26. Passed at `b07ad3b` on one rung (`runs/twwarhammer3/rl/confirms/hard-late*`);
  the first-order pre-launch gate came later (`c1f7894`), and the control would have failed it.
