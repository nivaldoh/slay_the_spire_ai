# Testing guidelines

Tests should make it easy to see what behavior we require, why it is correct, and which
mistake would make the check fail. This guide covers the software around both games.
[Evaluation guidelines](twwarhammer3/evaluation-guidelines.md) cover a different question:
whether a controller or benchmark supports a research claim.

**Draft for owner review, 2026-10-23.** The review's findings and cleanup evidence are in the
[WH3 log](twwarhammer3/log.md#2026-10-23-testing-review-findings-moved-from-testingmd-on-2026-10-29).
The recommendations below do not add agreed
verification methods or change benchmark rules. The existing
[verification rule](../AGENTS.md#verification-hard-rule) still decides what may be called
verified. [The test directory guide](../tests/README.md) explains the current files and commands.

## References worth using

Use particular practices from these sources; a respected project is not a template to copy
wholesale. The applications to our game code below are proposals.

| Reference | What to take from it |
|---|---|
| [Software Engineering at Google, unit testing](https://abseil.io/resources/swe-book/html/ch12.html) | Behavior-focused tests, clear failure messages, and enough local detail to understand a test without chasing helpers. |
| [Software Engineering at Google, test doubles](https://abseil.io/resources/swe-book/html/ch13.html) | Prefer practical real dependencies; keep substitutes small and faithful to the interface they replace. |
| [pytest layout guidance](https://docs.pytest.org/en/stable/explanation/goodpractices.html) and [flaky tests](https://docs.pytest.org/en/stable/explanation/flaky.html) | Explicit discovery/import rules, isolated state, and diagnosing unreliable tests instead of hiding failures with retries. |
| [pytest's representation tests](https://github.com/pytest-dev/pytest/blob/966edc9d517cd092104028796b684fb1119a7c73/testing/io/test_saferepr.py) | Read `test_broken_getattribute` and the dictionary insertion-order cases: small inputs, a concrete failure, an observable result. |
| [urllib3's retry tests](https://github.com/urllib3/urllib3/blob/c284372e2e11639b4554d50bf6d1a5b1750c0df0/test/test_retry.py) | Read `test_retry_read_zero`, `test_parse_retry_after_invalid` and `test_respect_retry_after_header_sleep`: boundaries, explicit exceptions and controlled time. |
| [How SQLite is tested](https://www.sqlite.org/testing.html) | Failure injection, boundary cases, regressions and deliberately broken implementations. Its scale and coverage targets are not requirements for this project. |
| [Coverage.py branch measurement](https://coverage.readthedocs.io/en/latest/branch.html) | Find decisions whose alternatives never ran; distinguish executing code from checking its answer. |
| [Hypothesis introduction](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html) | Generate varied inputs for a stated property. Useful for parsers and information boundaries when handpicked cases leave a concrete gap. |
| [Anthropic, agent evaluations](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) | Check the resulting state, test the grader, and allow valid alternative solutions. Applied to software checks below; research scoring stays in the evaluation guide. |
| [Anthropic, infrastructure noise](https://www.anthropic.com/research/infrastructure-noise) | Resource limits can change which strategies succeed. Control component-test scheduling; do not silently relax live battle deadlines to make a check pass. |

## Write tests that explain the requirement

For a meaningful behavior, establish four things: the condition, the action, the expected
result, and its reference. A reference can be a documented protocol, an owner requirement,
a small hand calculation or an independently checked game observation. It need not be a
formal document attached to every assertion.

An output recorded from the implementation is a regression baseline, not independent
proof of correctness. A round trip can also pass when the writer and reader share the same
mistake. Use a separately justified example when compatibility matters. If the desired
result is undecided, mark the choice under the [judgement rule](judgement.md); do not make
it look settled by asserting it in a test.

Name tests after the condition and result. For example, the current
`test_partition_and_deep_public_inputs_use_types_not_positions` combines several checks.
Names such as `test_infantry_member_gets_infantry_when_roster_order_changes` and
`test_member_input_excludes_hidden_fields` explain separate requirements. Use meaningful
variable names such as `infantry_member` when `a` would make the reader look elsewhere.

Show setup, action and assertions in that order, separated by blank lines. Keep important
inputs and expected values in the test. One behavior may need several assertions; there
is no one-assertion rule or arbitrary line limit. Split unrelated behaviors, but keep a
sequence together when that sequence is the requirement.

For example, this is the shape of a small component test using the existing WH3 API:

```python
def test_move_rejects_an_infinite_coordinate():
    observation = {"friendly": [{"id": "f1"}]}
    order = {"unit": "f1", "type": "move", "x": float("inf"), "z": 0}

    with pytest.raises(protocol.IllegalActionError, match="finite"):
        protocol.validate_orders([order], observation)
```

The reference is the agreed finite-number rule in [agreed-checks.md](agreed-checks.md). This checks rejection by
Python; the separate play-loop check establishes that an invalid batch is not sent. It
does not show how a unit moves in the game. The example illustrates style, not a request
to duplicate existing coverage.

## Keep setup and assertions simple

- Use fixtures for resource lifetime or setup genuinely shared by several tests. A short
  ordinary helper is enough for constructing data. Avoid a large configurable builder
  that hides the fields the test depends on.
- Put shared helpers in a clearly named support module; avoid importing another test
  module. Use the nearest `conftest.py` for shared pytest fixtures. Keep scopes narrow and
  give each test fresh mutable data.
- Parameterize variants of the same behavior with descriptive case IDs. Separate cases
  that require different setup or assertions instead of adding branches to the test.
- Assert useful outputs and side effects directly. Prefer a specific exception type and
  a relevant message fragment over catching any exception. Avoid recreating the production
  algorithm to calculate its expected result.
- A little repeated setup is acceptable when it makes the test understandable. Do not
  build a test framework just to remove a few lines.

## Choose the smallest check that can catch the mistake

Test through the interface used by the caller. Real temporary files, sockets and Lua are
often cheap enough to use. Replace the game or paid model API when a repeatable local test
needs to control its replies. The substitute should reject unsupported operations rather
than silently succeed. Reused substitutes need evidence that their relevant behavior
matches the real boundary; they need not recreate the entire game.

Assertions about calls are appropriate when the call itself is the requirement: an invalid
order must never be transmitted, or a budget refusal must prevent an API request. Checking
the incidental order of internal helper calls usually makes a refactor unnecessarily hard.

Label the limitation where it matters. Our Lua tests execute production functions, but
their simulated game methods do not demonstrate a live order's effect. Source-text checks
such as banning `fetch(` in JavaScript do not demonstrate that a report works in a browser.

## Show that a test can detect a wrong result

For an observed bug, reproduce the failure before fixing it where feasible. Preserve the
failure and the fixed run. If reproducing the old failure is unavailable, say so.

For an important new check, try a plausible wrong implementation in an isolated copy:
allow a stale request, transmit an invalid order, leak a hidden field, or overwrite a win
after cleanup fails. The test should fail for the intended reason. This is a targeted
application of mutation testing, not a requirement to run a whole-repository mutation tool.

Test the decision boundary and the harmful side effect. Rejecting one bad input without
accepting a nearby valid input can pass when the code rejects everything. An error message
alone does not establish that no order was sent or that the owned process was stopped.

For a live check, use an observation capable of disagreeing with the implementation. The
mod currently reports constant `speed: 1`; asserting that field cannot detect slowdown.
The existing team check also compares game-clock progress with elapsed time. Any proposed
replacement check or tolerance still needs owner agreement.

## WH3 boundaries that need different checks

The Python controller, mailbox files, Lua mod and Windows game can fail independently.
Choose the boundary relevant to the claim; an acknowledgement is not evidence that a unit
reached its destination. The references are the [mailbox contract](../src/twwarhammer3/engine/mailbox.py),
[game integration notes](twwarhammer3/integration.md) and [agreed checks](agreed-checks.md).

| Boundary | Useful assertion and its limit |
|---|---|
| Job, battle and request identity | Inject an old or foreign request between valid ones. It must not replace pending orders, unlock a decision or deliver another request's feedback; the next valid request must still work. Include real files and Lua where serialization matters. |
| Time and concurrency | Control the order in which replies, acknowledgements and endings arrive. Advance clocks explicitly for arithmetic; use events for real workers. Assert a bounded wait completed, and register cleanup before the first assertion. Keep battle time and wall time separate. |
| Public policy input | Change hidden fields and require unchanged public input; also show a public-field change reaches it. Mutating one member's nested input must not change its peer or the recorded observation. Do not compute the expected view with the same projector being tested. |
| Orders and endings | Separate Python validation, Lua acceptance, engine dispatch and observed game effect. Preserve the engine ending and any later controller fault separately; retaining the ending does not imply changing the scored status. |
| Recording and reports | Execute Lua to check recording callbacks precede result publication; exercise the browser for JavaScript behavior. A source-text search establishes neither. Simulated callbacks still leave actual file flushing and game behavior untested. |

Selected Lua definitions run with globals supplied by the test. This does not check the
whole mod's startup wiring. Our `FakeMailbox` feeds a declared observation sequence; it
does not enforce the real mailbox's sequence filtering or rematch wait. State these limits
instead of growing either substitute into a second game implementation.

Treat a live checker or scorer as software too: give it a known qualifying example and a
near miss (wrong unit, movement before acknowledgement, missing evidence). A passing grader
test establishes its calculation against the chosen rule, not the correctness of that rule.
When regrading saved evidence, preserve the original verdict and identify the new checker
revision/hash separately. The team check's `--recount` is read-only; add
`--recount-output NEW_CHECKS.json` to save a separate verdict with checker and input hashes.
The destination must not exist. New grading criteria still require owner agreement.

## Use saved examples deliberately

Small recorded fixtures are useful when their origin and expected interpretation are
clear. Keep only the fields needed to reproduce the behavior, plus the provenance needed
to trace them. A fixture's source hash confirms its origin, not its interpretation.

Exact snapshots are appropriate when exact text matters. Our saved WH3 prompts protect
the model-input contract during refactors; they do not establish prompt quality. Review
the changed text and requirement before regenerating an expectation. Never refresh a
snapshot merely to turn a failure green.

Snapshot generation is authoring, even when pytest reports a pass after writing it.
`WH3_WRITE_PROMPTS=1` enables that mode; verification needs a separate run with the variable
absent, as shown in [the prompt tests](../tests/twwarhammer3/test_wh3_prompts.py).

Generated-input tests need a meaningful property. For example, changing only hidden fields
must leave the public policy input unchanged. This complements explicit examples; it does
not justify adding Hypothesis everywhere or replacing game checks with generated states.

## Reviewing changes written by agents

JUDGEMENT: Agent review workflow — Codex, 2026-10-23, proposes a requirement-first review
and targeted fault challenge; accepting an agent's green suite alone misses shared mistakes
in code and expectations. This is draft guidance, not a new agreed verification method.

Give an independent reviewer the requirement and the changed code/tests, and ask for a
specific wrong behavior that could still pass. Another agent's agreement is review evidence,
not an independent correctness reference; agents can share the same mistaken assumption.
Use reproducible counterexamples to resolve disagreements. The expectation should come
from the contract or independently checked example, not the author's explanation of the patch.

Review test changes as carefully as runtime changes: weaker assertions, new skips, longer
timeouts, rewritten snapshots and altered fakes can all conceal a regression. Check the
final diff and test selection after experiments. Run deliberate faults in an isolated copy
or process, and run the final checks on the restored implementation. An import error or
unrelated timeout is not evidence that a test detected the intended fault.

For agentic game policies, grade the observable outcome while allowing different valid
tactics. Exact command order belongs in a check only when order is part of the contract,
such as flushing a recording before publishing the ending. Keep tactical judging and
sample-size choices in the [evaluation guide](twwarhammer3/evaluation-guidelines.md).

## Make runs repeatable and failures visible

Keep test data under a fresh temporary directory within `runs/`; restore environment
variables and global state, and close sockets, processes and threads even after failure.
Use a controlled clock for deadline arithmetic and explicit events for thread coordination.
Real timeout tests still need bounded waits and cleanup; an arbitrary sleep is not proof
that a worker reached the intended point.

The ordinary suite should run without games, paid APIs, credentials or downloaded model
weights. Keep live checks explicit, with their prerequisites, side effects, commands and
stopping conditions documented. Preserve the one-controller and WH3 1x rules.

Report failures, errors, skips, expected failures and unavailable checks separately. A
module skipped at import time is not one skipped test case. A missing required dependency
must fail its dedicated test job, even if the lightweight local suite permits that skip.
Do not make repeated attempts until green the acceptance rule for a flaky test.

## Make coverage understandable

Keep a small map by behavior, linking the tests, what is real or substituted, and the gap
that remains. [The current map](../tests/README.md#what-the-checks-establish) is a starting
inventory, not a claim of complete coverage. Keep agreement and passing revisions in the
existing AGENTS.md register rather than creating another verification register.

JUDGEMENT: Coverage reporting — Codex, 2026-10-23, proposes scoped branch reports alongside
the behavior map; a percentage-only report would describe a different kind of coverage.
Tooling and adoption remain pending; no new acceptance threshold is defined here.

A useful code-coverage report names the command, revision, dependency set, skipped tests,
source scope and exclusions. Include untouched modules in that scope so importing only
well-tested modules cannot inflate the result. Look at missed branches in consequential
paths, especially failure handling. A Python report says nothing about execution coverage
inside Lua, JavaScript or the Windows game. Keep the existing no-threshold policy; do not
add tests merely to increase a number.

## Organize by game and feature

JUDGEMENT: Test layout — Codex, 2026-10-23, proposes game then feature, with explicit live
and browser checks; keeping the legacy layout avoids path changes but leaves game ownership
unclear. The migration is pending; existing agreed commands remain in force.

A possible destination, not the current tree:

```text
tests/
  README.md
  gameai/                         # shared transport, spending, process ownership
  spire/
    engine/  fullrun/  combat/     # then ppo/, language/, openweight/
    test_decisions.py
    test_protocol.py
    fixtures/
  twwarhammer3/
    engine/
    battle/
      team/                       # member ownership, scheduling and feedback
    report/                       # report data, replay and browser check
    prompts/                      # prompt tests and their expected text
    live/                         # explicitly invoked game checks, grouped by feature
  test_doc_links.py
```

Keep feature ownership primary; do not build parallel unit/integration trees for every
feature. State in each module which dependencies are real and which are replaced. A team
component suite should be selectable independently; its live command should also be easy
to find from that feature's guide.

Move in small, behavior-preserving steps. Extract shared helpers before moving their
callers; account for every old test ID and assertion, update imports, fixture paths and
documented commands, then run affected suites. The current un-packaged test modules need
globally unique filenames. Do not rename duplicates or switch pytest import modes blindly:
pytest's recommended `importlib` mode does not make cross-test imports work automatically.
Changes to agreed checks must preserve their requirements; a path cleanup is not permission
to weaken an assertion.

## Keep the suite lean

Test comments explain surprising inputs, the requirement or a past failure. Docstrings
explain behavior, dependencies and how to run an unusual check. Approval dates, work-session
history and claims of being verified belong in the existing register and logs, not in test
headers. This keeps the owner's verification rule without repeating its bookkeeping.

Before removing a confusing helper, find its callers. The report demo generator is used
by both report tests and the browser check; the saved prompts are read by prompt tests.
They need a clear home and purpose before a decision to keep, simplify or remove them.
Remove redundant tests when the retained test catches the same failure with less setup.
Avoid tests of unused scaffolding, incidental implementation details or speculative features.

JUDGEMENT: Cleanup sequence — Codex, 2026-10-23, proposes starting with Spire's misplaced
root tests and shared helpers, then WH3 team/report grouping; starting with coverage gaps
would prioritize different work. No migration or new check is adopted by this draft.

For review of a test change, ask: **What wrong behavior does it catch? Why is the expected
answer right? Can I understand the case here? What still needs a real dependency or game?**

## Initial cleanup

The owner's request to make initial progress is recorded in [owner direction](owner-direction.md).
This batch rests on JUDGEMENT `docs/testing.md` Test layout and Cleanup sequence; the larger
migration and coverage tooling remain for review.

- Moved the root decision and protocol tests to `tests/spire/`; extracted three unchanged
  message builders into `spire_messages.py` and updated four full-run callers.
- Replaced approval dates in the army and team check headers with their purpose. Their
  commands and check criteria are unchanged; approval history remains in agreed-checks.md.
- Before: 96 focused tests passed. After: the same 96 plus 64 documentation checks passed,
  with no failures or skips. Ruff passed. All 1,412 collected cases match after substituting
  the two paths; the same 11 modules skip without PyTorch. Comparing the 85 existing Python
  test/support modules found unchanged test bodies, helpers, parameters and assertions.
- Evidence: `runs/testing-cleanup-20261023/`. These are preservation checks, not a new
  correctness verification method. No game, browser or training check ran in this batch.

Second batch: full-run setup and stopping (2026-10-23).

- Moved the shared fixture to `tests/fullrun/conftest.py` and messages/policy to
  `fullrun_support.py`; removed the digest and watcher's imports from `test_play.py`.
- Added three component cases for a bridge disconnect, interruption and source change.
  Their interpretation rests on JUDGEMENT `tests/fullrun/test_play_stops.py` Stop-path checks;
  they remain proposed, not yet agreed verification. No runtime code changed.
- Full-run suite: 49 passed before, 52 after; no failures or skips. All 956 existing test
  definitions and the extracted helpers/constants are unchanged. Collection preserves
  1,412 existing cases and adds the three new cases; 11 modules still skip without PyTorch.
  All 64 documentation checks and Ruff passed.
- All three deliberate in-memory errors failed the intended assertion or missing-exception
  check: disconnect counted as loss, partial result not saved, source change ignored.
  Evidence: `runs/testing-cleanup-20261023-r2/`. No live process-cleanup claim.
