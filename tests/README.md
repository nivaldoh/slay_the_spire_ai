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
uv run --locked pytest -ra tests/twwarhammer3/test_wh3_team.py --basetemp=runs/test-scratch/team
uv run --locked pytest --collect-only -q -ra
uv run --locked ruff check .

# Optional dependency sets, run separately because train and llm conflict.
uv run --locked --extra train pytest -ra tests/ppo --basetemp=runs/test-scratch/ppo
uv run --locked --extra llm pytest -ra tests/language --basetemp=runs/test-scratch/language
```

Use a different scratch path for concurrent invocations: pytest clears its `--basetemp`.
Only disposable test data belongs there. `uv sync --locked` removes optional extras again.
Read `-ra` skip reasons: absent training packages or local evidence leave checks unrun.
The opt-in Windows process test in [test_windows.py](gameai/test_windows.py) additionally
requires WSL, Windows Python and `GAMEAI_TEST_WINDOWS=1`; it starts test processes, not a game.

## What the checks establish

This is an entry-point map from the 2026-10-23 review, not an exhaustive assertion audit.
For agreed methods and last passing revisions, use
[AGENTS.md](../AGENTS.md#verification-hard-rule). An existing test is not automatically an
agreed verification method.

| Behavior | Where to start | Real dependency and limit |
|---|---|---|
| Model requests, retries and spending | [test_model.py](gameai/test_model.py), [test_providers.py](gameai/test_providers.py) | Real request/accounting code and temporary ledgers; substituted API responses. No provider availability or real billing claim. |
| Spire message framing and disconnects | [test_bridge.py](engine/test_bridge.py) | Real sockets and relay subprocess; no JVM or Windows game launch. |
| Spire legal choices, target identity and public inputs | [test_decisions.py](spire/test_decisions.py), [test_protocol.py](spire/test_protocol.py), [engine regressions](combat/test_engine_regressions.py) | Synthetic messages and recorded transitions. Original-trace comparisons need local evidence; no current-game validation. |
| Spire run lifecycle | [test_play.py](fullrun/test_play.py), [stopping](fullrun/test_play_stops.py) | Real loop; fake game and bridge. Includes disconnect, interruption and source-change cases. Action/time limits and actual Windows cleanup are not established by these tests. |
| WH3 order validation and mailbox delivery | [test_wh3_protocol.py](twwarhammer3/test_wh3_protocol.py), [test_wh3_mailbox.py](twwarhammer3/test_wh3_mailbox.py), [battle Lua](twwarhammer3/test_wh3_battle_lua.py) | Python, files and production Lua functions; simulated game methods. Delivery and acceptance do not establish live movement. |
| WH3 member ownership and independent progress | [test_wh3_team.py](twwarhammer3/test_wh3_team.py), [test_wh3_play.py](twwarhammer3/test_wh3_play.py) | Controlled workers and some real threading; fake observations. The separate live check tests scripted members. |
| Exact model input | [test_wh3_prompts.py](twwarhammer3/test_wh3_prompts.py), [expected text](twwarhammer3/prompts/) | Rendered input compared with the expected text. Detects prompt changes, not whether a prompt plays well. |
| Scoring and reporting | [test_wh3_cards.py](twwarhammer3/test_wh3_cards.py), [test_wh3_report.py](twwarhammer3/test_wh3_report.py), [HTML tests](twwarhammer3/test_wh3_report_html.py) | Constructed records and expected summaries. Benchmark choices may be undecided; HTML generation does not exercise browser behavior. |
| Learning and exports | [PPO](ppo/), [language](language/), [Spire export](fullrun/test_export.py), [WH3 export](twwarhammer3/test_wh3_export.py), [dataset building](gameai/test_sft.py) | Offline data and learning-code checks, some requiring extras. These do not establish policy strength or training gains in the game. |

## Checks outside pytest and supporting files

These filenames are not collected by the ordinary pytest command. Follow their own usage
instructions and existing game-window permissions before running a live check.

| File | Purpose and current use |
|---|---|
| [spire_messages.py](spire/spire_messages.py) | Builds synthetic card, combat and screen messages shared by Spire's decision and full-run tests. Expected results stay in the tests. |
| [fullrun_support.py](fullrun/fullrun_support.py), [conftest.py](fullrun/conftest.py) | Shared full-run messages and a simple policy; the `harness` fixture supplies queued game messages and records sent commands. It replaces game processes and bridge I/O only when a test requests it. |
| [check_wh3_army_setup.py](twwarhammer3/check_wh3_army_setup.py) | Launches WH3 to save, change, restart and reload armies; compares roster, ranks and settings. `--integration` extends the check. Its Python helpers also have component tests. |
| [check_wh3_team.py](twwarhammer3/check_wh3_team.py) | Launches four scripted-team diagnostics, delaying each member in turn; checks movement, timing and cleanup. `--recount` only reads saved evidence. No model-team strength claim. |
| [check_wh3_report_browser.cjs](twwarhammer3/check_wh3_report_browser.cjs) | Uses Playwright/Chromium to exercise the offline benchmark report. Needs a separate browser installation and input reports or recorded jobs. It is an existing check, not part of the default suite. |
| [make_wh3_report_demo.py](twwarhammer3/make_wh3_report_demo.py) | Builds invented report inputs for HTML tests and the browser check. Demonstrates display behavior; its battles are not experiment evidence. |
| [prompts/](twwarhammer3/prompts/) | Expected controller-input text read by prompt tests. For an intended prompt version change, regenerate using the command in `test_wh3_prompts.py` and review the diff. |
| [wh3_fixtures.py](twwarhammer3/wh3_fixtures.py), [wh3_lua.py](twwarhammer3/wh3_lua.py) | Reusable test inputs, fake transports and a Lua 5.1 loader. The loader executes selected production definitions, not the whole game environment. |

Approval history stays in AGENTS.md and logs. Commands and script descriptions explain
what a check does; neither a filename nor a passing local run makes a feature verified.
