# Repository Guidelines

AI policies for original Windows games from WSL. Current focus: Total War: WARHAMMER III
(WH3; real-time custom battles through a Lua mod). Start with [docs/state.md](docs/state.md):
read "Active work" and the relevant track, then that track's page.
Codex loads this file; Claude Code imports it through `CLAUDE.md`. It holds hard rules and
pointers in at most 200 lines (a repo rule): detail goes in the page it governs. How a change
is made (cards, `scripts/check.py`, the reviewer, reports): [docs/workflow.md](docs/workflow.md).

Before Spire work (its source, legacy configs, tests, scripts, or shared code affecting it),
read [docs/spire/AGENTS.md](docs/spire/AGENTS.md); skip it for WH3-only work.

## Verification (hard rule)

The owner's rule (2026-10-18): **if the owner has not explicitly discussed with the
assistant how to verify (repeatably test) whether a feature is correct, assume it might
have issues.** Be careful making claims about, or building on top of, unverified things.

How the assistant applies it:
- Passing tests, smoke runs and single battles are evidence, not verification. Say
  "unverified" when reporting or building on anything without an agreed method.
- Every claim carries what it rests on: the number of battles or runs behind a rate, the
  check that decides it and its caveats. A summary never says more than its log entry.
- When a feature matters, propose a repeatable check; add it to
  [docs/agreed-checks.md](docs/agreed-checks.md) only after the owner agrees. A feature
  counts as verified only at revisions where its check passed there.
- Test what matters, and add no slop tests (owner, 2026-10-18): balance verifying
  important behaviour against filling the codebase with low-value tests.

For each change:

1. State the observable behaviour and its independent reference (requirement, contract or
   trusted example); a recorded output alone is not proof of correctness. A normal change
   states them in its card ([workflow](docs/workflow.md#before-a-change-the-card)).
2. Choose the cheapest relevant checks. For a bug, show the regression fails before the fix
   where feasible; for important verification, check it detects a plausible wrong implementation.
3. Iterate with focused tests and expand when a concrete risk requires it (extras, live
   checks); before each commit run `scripts/check.py`. Preserve useful failure output.
4. Report passed, failed, skipped and unavailable checks, and what each establishes.
   Component tests and recorded cases do not establish live-game effects or policy strength.

## Judgement calls

The owner's rule (2026-10-23): agents execute; the owner decides. A judgement call is a
choice no owner direction made that fixes what a benchmark measures, how something is
verified, what comes next, a design whose alternatives change results or their meaning, or
a parameter with benchmark or plan meaning. An agent that makes or finds one marks it in the
same change at the nearest convenient spot (a comment above the line; a note in the page
that documents a file that cannot carry one): `JUDGEMENT:`, or `JUDGEMENT?:` when unsure it
counts, then in one to three lines what was chosen, who and when, the alternative that would
change results and what rests on it. A marked spot may be wrong: say "rests on JUDGEMENT
<file> <name>" for anything built on it, copy its value nowhere without the marker, and park
what [docs/autonomy.md](docs/autonomy.md) parks; a marker is not permission to decide. Only
the owner removes or weakens a marker (an agent only when quoting the owner's words on that
spot in the commit); approval is not verification. Placement limits, the listing command and
the marking pass: [docs/judgement.md](docs/judgement.md).

## Working habits

The assistant's proposals for the owner's 2026-10-18 goal (less bookkeeping, garbage and
token use):
- `docs/state.md` stays status only, under about 120 lines, with the current next steps
  (other pages keep candidates and deferred items). New owner directions go in
  `docs/owner-direction.md`. A log entry stays within about 20 lines: what changed, its
  evidence with counts, and what is unverified.
- Read docs by section; do not reload full guidance already present in the session.
  Use multi-agent workflows only for independent verification, the WH3 loop's review step,
  or when the owner asks.
- For complicated or ambiguous code (benchmarks, evaluation, environments, infrastructure,
  tests, workflows), follow a well-known research repo and name the repo and file in a comment
  or the commit (owner, 2026-10-28); outside sources go in [references.md](docs/references.md).
- Put task-created scripts, logs, temporary artifacts, diagnostics and test scratch in the
  ignored `runs/`, never in the home root or unrelated directories; inventory old garbage.
- Delete a branch and its worktree once merged; create worktrees outside `/tmp`, which a
  WSL restart wipes. While a WH3 queue runs, commit nothing: it stops before its next job
  when HEAD moves. Add no file, scenario or diagnostic that no planned experiment uses.
- When `doctor` or a job warns that a game build differs from its pin, tell the owner;
  re-pin only with their approval.

## Working while the owner is away

When the owner says they cannot review or are leaving, see [docs/autonomy.md](docs/autonomy.md):
its standing menu and small interviews were agreed on 2026-10-28; its other rules (at most
three changes waiting, park changes to benchmark meaning, game time only in an away window)
are the 2026-10-21 proposal, in force once the owner says yes. A long run gets a brief and a
handoff note ([workflow](docs/workflow.md#long-runs-while-the-owner-is-away)).

## Layout

```
src/gameai/        Game-neutral code both games import; it never imports a game package:
                   llm (transport, Model), providers, ledger (hard budget), sft, provenance,
                   lm (local models, GPU lease), windows and windows_game (owned Windows games)
src/twwarhammer3/  WH3 custom battles; module map in docs/twwarhammer3/README.md (Code map)
src/spire/         Slay the Spire; its map is in docs/spire/AGENTS.md
configs/           Per game: twwarhammer3/ (prompts, scenarios, report notes, benchmark jobs)
scripts/           check.py (the exit gate); wh3_queue.py (a frozen plan of WH3 play jobs);
                   wh3_db.py (unit data from the game database); sft_smoke.py; Spire tools
tests/             Per package (tests/README.md); test_repo_rules.py, test_doc_links.py: the repo
docs/              state.md, owner-direction.md, workflow.md, autonomy.md, judgement.md,
                   agreed-checks.md, testing.md, posttraining.md, references.md, thesis/
                   (untracked: git grep misses it), twwarhammer3/ (README, log, results), spire/
runs/              Local evidence, ignored by Git; see runs/README.md
.claude/ .codex/   the same hooks and reviewer for each tool, skills in .agents/ (workflow.md)
```

A new game gets `src/<game>/`, `configs/<game>/`, `docs/<game>/`, `runs/<game>/` and
`tests/<game>/`. Move code into `gameai` when a second game would otherwise copy it, not
before; the job modules (play, digest, watch, stats) stay per game. Test files share one
namespace (no `tests/__init__.py`): every test file name is unique across `tests/`.

## Commands

```bash
uv sync --locked
uv run --locked python scripts/check.py   # before each commit: Ruff, whole offline suite, warnings
uv run python -m twwarhammer3 doctor   # read-only: pins, preferences, running game
uv run python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>   # add /episode-0000 [--at S]; --units
uv run python -m twwarhammer3 stats    # results by scenario, policy, model, harness, mode, timing
git grep -n JUDGEMENT -- ':!AGENTS.md' ':!docs/judgement.md'   # marked judgement calls awaiting the owner
```

More: the WH3 [README](docs/twwarhammer3/README.md#commands) (watch, report, export, spend,
card, checkpoints, RL); [posttraining](docs/posttraining.md); [tests](tests/README.md) (extras).
- `twwarhammer3 play`, `twwarhammer3 launch` and `scripts/wh3_queue.py` run a real game
  (`menu` and `play --attach` use the game `launch` started). `play` needs a new output
  directory and refuses uncommitted changes in its source scope: `src/gameai/`,
  `src/twwarhammer3/`, `configs/twwarhammer3/`, `pyproject.toml`, `uv.lock` and
  `.python-version` (`battle/play.py` `SOURCES`). `launch` checks no scope.
  A play job stops before its next episode if a file in its scope changes. Shared source
  and dependency changes can stop either game. Check any running job's source scope before
  editing, even another game's files; draft in a git worktree while one runs.
- Check "Active work" in `docs/state.md` first. Never run two game controllers at once,
  even for different games: each `RuntimeLock` only protects its own game.
- WH3 battles always run unpaused at 1x speed, including diagnostic probes and smoke
  tests. Never pause or slow the battle to give a policy more thinking time. One exception
  (owner, 2026-10-25): a checkpoint restore may rebuild the battle faster than 1x before
  its handover; from the handover on, 1x.

## Architecture

Both games run on Windows from their Steam installs under `/mnt/c`; the controller runs in
WSL and owns the game process through `gameai.windows`. WH3's Lua mod is its API ([how it
works](docs/twwarhammer3/README.md#how-it-works)); its build is pinned in `engine/runtime.py`,
and a different build warns and is recorded but never blocks (owner, 2026-10-18).

Information boundary: friendly units in full; enemy units only while
`is_visible_to_alliance`, plus the enemy roster the custom battle screen shows; the
observation's `evaluation`, `final` and `setup` never reach a policy, nor do replay
frames or stills. Failure taxonomy (`protocol.py`): `ProtocolError`, `IllegalActionError`,
`PolicyFailure`, `MailboxTimeout` and `BattleRestarted` are infrastructure, protocol or
policy failures; a batch that fails validation is recorded as invalid and sent as no
orders. Only an engine-reported won, lost or draw is a gameplay outcome.

## Evidence

Run evidence stays out of Git ([runs/README.md](runs/README.md): layout and ledger paths).
A job's `--budget-usd` caps its selected ledger's total, earlier jobs included. The owner's $50
OpenRouter allowance covers both games: leave room for the total in
`runs/spire-openrouter-spend.jsonl` too (`uv run python -m spire spend --provider openrouter`).
Never move or reset a ledger. A play command refuses a ledger file that does not exist (a
mistyped path or a job started from a worktree would count from $0): create it deliberately for
a new ledger.

Each WH3 `play` appends one row per episode to `docs/twwarhammer3/results.csv`. Log every
version in `docs/twwarhammer3/log.md` and commit the register with that entry. Update
`docs/state.md` when work starts, stops or changes direction, and keep it short: what runs,
what is stopped and why, what is next, with links. Results, validation counts and history
go in the logs.

## Coding style and tests

Four-space indentation, `snake_case` functions and modules, `PascalCase` classes,
`UPPER_SNAKE_CASE` constants. Keep protocol handling separate from policy logic. Reserve
bridge stdout for protocol traffic; send diagnostics elsewhere. Match the surrounding code.
Do not run `ruff format` on hand-formatted files (most are); the WH3 report JavaScript uses
`prettier --print-width 100`. No overengineering, excessive abstractions or overly safe code.
Write in simple, concrete language (owner, 2026-10-20): say what a unit, controller or
experiment actually does; no inflated wording; explain technical terms when they help.

Tests: [tests/README.md](tests/README.md); [docs/testing.md](docs/testing.md) holds proposed
guidelines; no coverage threshold. Prioritize action and target identity, stale observations,
terminal transitions, reproducible resets and bridge failures; add a regression for every
observed failure; validate mechanics against the original engine, not fixtures alone.
Regenerate the prompt snapshots in `tests/twwarhammer3/prompts/` (`WH3_WRITE_PROMPTS=1`) only
for an intended prompt change, a logged version. Each top-level definition in
`twwarhammer3_battle.lua` ends with an unindented `end` or `}` (Lua tests load them by name).

## Commits and artifacts

Concise, imperative subjects, such as `Add bridge readiness handshake`. Keep changes
focused. The owner authorizes commits and pushes to `main`. PRs explain the problem,
behavior changes, validation commands and results, and limitations.

Exclude hidden game state from policy inputs. Record source revision, configuration, engine
and mod versions, and evaluation output for each experiment; distinguish infrastructure
failures from gameplay losses. Never commit proprietary game files, mod jars, game packs or
files extracted from them (`runs/twwarhammer3/vanilla/`), saves, bulky trajectories or
checkpoints, API keys, or `*:Zone.Identifier` files (`tests/test_repo_rules.py` checks the
patterns it can).
