# Agreed checks

The owner's agreed verification methods under the
[hard rule](../AGENTS.md#verification-hard-rule): a feature counts as verified only at
revisions where its check passed. Each entry gives the feature, the check and command, the
date agreed and the last passing revision. Only the owner agrees a new entry. Moved here from
AGENTS.md on 2026-10-28 to keep that file lean (owner).

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
  leadership XP bonuses relative to rank zero). Restart uses supervised shutdown; graceful
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
  sense for now, I'll review later"). Custom land battle, build 25961564; no claim for
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
