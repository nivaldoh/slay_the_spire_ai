# Tests

Start here to find a check and understand its limits. [Testing guidelines](../docs/testing.md)
contain the review findings, reference projects and proposed cleanup. `spire/` holds the
Spire decision and protocol tests and their shared message builders. The remaining Spire
tests still use the older `combat/`, `engine/`, `fullrun/`, `language/`, `openweight/`, `ppo/`
and `fixtures/` directories. `gameai/` is shared; `twwarhammer3/` belongs to **WH3**;
`test_doc_links.py` covers the repo.

## Running tests

From the repository root:

```bash
# Ordinary suite, including Lua 5.1 and image checks; no game or paid model calls.
uv run --locked pytest -ra --basetemp=runs/test-scratch/default

# Select a feature, or inspect which tests the current environment discovers.
uv run --locked pytest -ra tests/twwarhammer3/team --basetemp=runs/test-scratch/team
uv run --locked pytest --collect-only -q -ra
uv run --locked ruff check .

# Optional dependency sets, run separately because train and llm conflict.
uv run --locked --extra train pytest -ra tests/ppo --basetemp=runs/test-scratch/ppo
uv run --locked --extra llm pytest -ra tests/language --basetemp=runs/test-scratch/language
```

`scripts/check.py` runs the ordinary suite and Ruff before a commit ([workflow](../docs/workflow.md#the-exit-gate-scriptscheckpy)).
The dev group includes lupa (Lua 5.1) and Pillow; the `train` (CPU torch) and `llm` (CUDA
torch, transformers, peft) extras conflict, so use only one per command; without them
those tests skip through `importorskip`.
Use a different scratch path for concurrent invocations: pytest clears its `--basetemp`.
Only disposable test data belongs there. `uv sync --locked` removes optional extras again.
Read `-ra` skip reasons: absent training packages or local evidence leave checks unrun.
Two tests replay agreed checks' saved passing evidence from `runs/` with planted wrong values
([siege](twwarhammer3/checkpoint_siege/test_wh3_siege_saved_evidence.py),
[checkpoint-RL step run](twwarhammer3/test_wh3_restored_episode_check.py)); they skip without it.
The opt-in Windows tests in [test_windows.py](gameai/test_windows.py) and
[test_wh3_runtime.py](twwarhammer3/test_wh3_runtime.py) additionally require WSL, Windows Python
and `GAMEAI_TEST_WINDOWS=1`; they start test processes, not a game. Two run this checkout's
source in native Windows Python (a cloud worker's side); one runs the read-only doctor there.

## What the checks establish

This is an entry-point map from the 2026-10-23 review, not an exhaustive assertion audit.
For agreed methods and last passing revisions, use
[agreed-checks.md](../docs/agreed-checks.md) (the rule: [AGENTS.md](../AGENTS.md#verification-hard-rule)).
An existing test is not automatically an
agreed verification method.

| Behavior | Where to start | Real dependency and limit |
|---|---|---|
| Model requests, retries and spending | [test_model.py](gameai/test_model.py), [test_providers.py](gameai/test_providers.py), [test_ledger.py](gameai/test_ledger.py) | Real request/accounting code and temporary ledgers, including caps after reopen; substituted API responses. No provider availability or real billing claim. |
| Source attribution | [test_provenance.py](gameai/test_provenance.py) | Real temporary Git repositories: scoped edits, staged/deleted/renamed/untracked files refuse attribution; outside-scope edits pass. Byte changes affect fingerprints even with matching size/timestamps. No launch or Windows claim. |
| Spire message framing and disconnects | [test_bridge.py](engine/test_bridge.py) | Real sockets and relay subprocess; no JVM or Windows game launch. |
| Spire legal choices, target identity and public inputs | [test_decisions.py](spire/test_decisions.py), [test_protocol.py](spire/test_protocol.py), [engine regressions](combat/test_engine_regressions.py) | Synthetic messages and recorded transitions. Original-trace comparisons need local evidence; no current-game validation. |
| Spire run lifecycle | [test_play.py](fullrun/test_play.py), [stopping](fullrun/test_play_stops.py) | Real loop; fake game and bridge. Includes disconnect, interruption and source-change cases. Action/time limits and actual Windows cleanup are not established by these tests. |
| WH3 order validation and mailbox delivery | [test_wh3_protocol.py](twwarhammer3/test_wh3_protocol.py), [test_wh3_mailbox.py](twwarhammer3/test_wh3_mailbox.py), [battle Lua](twwarhammer3/test_wh3_battle_lua.py) | Python, files and production Lua functions; simulated game methods. Includes foreign job/battle rejection and duplicate delivery. Acceptance does not establish live movement. |
| WH3 acknowledgement identity and endings | [test_wh3_play.py](twwarhammer3/test_wh3_play.py) | Real loop, queued observations and controlled time. Unrelated/repeated acknowledgements do not release pending work. Terminal-call time is excluded from the battle clock; actual game timing remains separate. |
| WH3 member ownership and independent progress | [team/test_wh3_team.py](twwarhammer3/team/test_wh3_team.py), [team/test_wh3_model_team.py](twwarhammer3/team/test_wh3_model_team.py), [test_wh3_play.py](twwarhammer3/test_wh3_play.py) | Controlled workers and some real threading; fake observations. The separate live check tests scripted members. |
| Exact model input | [test_wh3_prompts.py](twwarhammer3/test_wh3_prompts.py), [expected text](twwarhammer3/prompts/) | Rendered input compared with expected text, with `WH3_WRITE_PROMPTS` absent. Generation is not verification; matching text does not establish prompt quality. |
| Scoring and reporting | [test_wh3_cards.py](twwarhammer3/test_wh3_cards.py), [test_wh3_report.py](twwarhammer3/test_wh3_report.py), [HTML tests](twwarhammer3/test_wh3_report_html.py) | Constructed records and expected summaries. Benchmark choices may be undecided; HTML generation does not exercise browser behavior. |
| Refusals and checks of checks | [battle mod refusals](twwarhammer3/test_wh3_battle_lua.py), [setup declarations and readbacks](twwarhammer3/test_wh3_setup.py), [checkpoint guards](twwarhammer3/test_wh3_checkpoint_guards.py), [corrupt traces](twwarhammer3/test_wh3_export.py), [Spire loop guards](fullrun/test_play_stops.py), [pass rules on saved evidence](twwarhammer3/checkpoint_siege/test_wh3_siege_saved_evidence.py) | Each case fails when its refusal is removed (the 2026-10-29 sweeps, [WH3 log](../docs/twwarhammer3/log.md)). Component behaviour only: no live engine effect. |
| Learning and exports | [PPO](ppo/), [language](language/), [Spire export](fullrun/test_export.py), [WH3 export](twwarhammer3/test_wh3_export.py), [dataset building](gameai/test_sft.py) | Offline data and learning-code checks, some requiring extras. These do not establish policy strength or training gains in the game. |

## Checks outside pytest and supporting files

These filenames are not collected by the ordinary pytest command. Follow their own usage
instructions and existing game-window permissions before running a live check.

| File | Purpose and current use |
|---|---|
| [spire_messages.py](spire/spire_messages.py) | Builds synthetic card, combat and screen messages shared by Spire's decision and full-run tests. Expected results stay in the tests. |
| [combat_support.py](combat/combat_support.py) | First-combat messages and an opt-in `harness` fixture shared by combat and language tests. It substitutes rollout processes, bridge I/O, clock and source/environment readings; it never launches a game. |
| [fullrun_support.py](fullrun/fullrun_support.py), [conftest.py](fullrun/conftest.py) | Shared full-run messages and a simple policy; the `harness` fixture supplies queued game messages and records sent commands. It replaces game processes and bridge I/O only when a test requests it. |
| [check_wh3_army_setup.py](twwarhammer3/check_wh3_army_setup.py) | Launches WH3 to save, change, restart and reload armies; compares roster, ranks and settings. `--integration` adds refusal/reserve checks and restores settings. Changed lobby settings surviving shutdown is only observed. [Orchestration tests](twwarhammer3/test_wh3_army_check.py) exercise startup guards and restoration without launching a game. |
| [check_wh3_team.py](twwarhammer3/team/check_wh3_team.py) | Launches four scripted-team diagnostics, delaying each member in turn; checks movement, timing and cleanup. `--recount EXISTING_OUTPUT` reads only; `--recount-output NEW_CHECKS.json` saves a separate verdict with checker/input hashes and refuses overwrite. [Recount tests](twwarhammer3/team/test_wh3_team_recount.py) cover file preservation, not live movement. No model-team strength claim. |
| [check_wh3_checkpoint.py](twwarhammer3/check_wh3_checkpoint.py) | Launches WH3 four times: a source battle saved at tick 1200, two restores with the same later orders and one with a changed order; compares every tick's native checksum and Lua readings (the agreed check, [checkpoints.md](../docs/twwarhammer3/checkpoints.md)). `--recount EXISTING_OUTPUT` re-scores saved evidence. [Pass-rule tests](twwarhammer3/test_wh3_checkpoint.py) show it fails on one wrong tick, one wrong reading or a changed restore that does not diverge. Custom land battle, build 25961564 only. |
| [check_wh3_checkpoint_siege.py](twwarhammer3/check_wh3_checkpoint_siege.py) | Fifteen launches: three siege cases, four saved states, two identical restores and a changed-order control per state. Requires actual spell effect/expiry, living mixed units, ladder climbing, gate states, equipment counts, construction, supplies and ownership. Live numeric readings compare exactly; cached infocard stats remain separate diagnostics by the owner's agreement. [Fixtures and witness regressions](twwarhammer3/checkpoint_siege/) support the check. Scripted ownership changes do not establish normal capturing; speed getters do not establish fatigue-adjusted effective speed. |
| [check_wh3_report_browser.cjs](twwarhammer3/check_wh3_report_browser.cjs) | Uses Playwright/Chromium to exercise the offline benchmark report. Needs a separate browser installation and input reports or recorded jobs. It is an existing check, not part of the default suite. |
| [make_wh3_report_demo.py](twwarhammer3/make_wh3_report_demo.py) | Builds invented report inputs for HTML tests and the browser check. Demonstrates display behavior; its battles are not experiment evidence. |
| [prompts/](twwarhammer3/prompts/) | Expected controller-input text read by prompt tests. For an intended prompt version change, regenerate using the command in `test_wh3_prompts.py` and review the diff. |
| [wh3_fixtures.py](twwarhammer3/wh3_fixtures.py), [wh3_lua.py](twwarhammer3/wh3_lua.py) | Reusable inputs, API/mailbox substitutes and a Lua 5.1 loader. `FakeMailbox` feeds a sequence without real file polling or sequence filtering. The loader executes selected production definitions, not the whole game environment. |

Approval history stays in [docs/agreed-checks.md](../docs/agreed-checks.md) and logs. Commands and script descriptions explain
what a check does; neither a filename nor a passing local run makes a feature verified.
