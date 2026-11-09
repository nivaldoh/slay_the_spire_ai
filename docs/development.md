# Development details

Read only the sections needed for the task, as routed by [AGENTS.md](../AGENTS.md).
These are the implementation and command details moved from that file on 2026-11-09;
the rules still apply. For Spire or shared code affecting it, also read
[Spire guidance](spire/AGENTS.md). For cloud work, read [cloud.md](cloud.md).

## Layout

```
src/gameai/        Game-neutral code both games import; it never imports a game package:
                   transport, budgets, datasets, provenance, local models, Windows ownership
src/twwarhammer3/  WH3 custom battles; module map in docs/twwarhammer3/README.md (Code map)
src/spire/         Slay the Spire; its map is in docs/spire/AGENTS.md
configs/           Per-game prompts, scenarios and experiment declarations
scripts/           Exit gate and tools; listed in the WH3 Code map
tests/             Per package; tests/README.md routes checks
docs/              Shared guidance and game tracks; thesis/ is untracked (git grep misses it)
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
git grep -n JUDGEMENT -- ':!AGENTS.md' ':!docs/judgement.md'   # marked judgement calls awaiting the owner
```

More: the WH3 [README](twwarhammer3/README.md#commands) (digest, stats, watch, report, export, spend,
card, checkpoints, RL); [posttraining](posttraining.md); [tests](../tests/README.md) (extras).
- `twwarhammer3 play`, `launch`, `worker` without `--attach`, the `rl` phases `checkpoint`,
  `audit` and `confirm`, `python -m twwarhammer3.battle.manual_demo record`,
  `scripts/wh3_queue.py` and the six `check_wh3_*.py` checkers (except `--recount`) run a real
  game (`menu` and `play --attach` use the game `launch` started). `play` needs a new output
  directory and refuses uncommitted changes in its source scope: `src/gameai/`,
  `src/twwarhammer3/`, `configs/twwarhammer3/`, `pyproject.toml`, `uv.lock` and `.python-version`
  (`battle/play.py` `SOURCES`). `launch` checks no scope.
  A play job stops before its next episode if a file in its scope changes: while one runs,
  merge nothing into its checkout that touches its scope (shared code counts for both games).
- Never run two game controllers at once,
  even for different games: each `RuntimeLock` only protects its own game.
- WH3 battles always run unpaused at 1x speed, including diagnostic probes and smoke
  tests. Never pause or slow the battle to give a policy more thinking time. Restore exception
  (owner, 2026-10-25): a checkpoint restore may rebuild the battle faster than 1x before
  its handover; from the handover on, 1x.
  Owner, 2026-11-04: only the owner may pause while manually demonstrating scenario winnability
  ([plan](twwarhammer3/scenario-guidelines.md#winnability-evidence)); never an agent or policy.

## Architecture

Both games run on Windows from their Steam installs under `/mnt/c`; the controller runs in
WSL and owns the game process through `gameai.windows`. WH3's Lua mod is its API ([how it
works](twwarhammer3/README.md#how-it-works)); its build is pinned in `engine/runtime.py`,
and a different build warns and is recorded but never blocks (owner, 2026-10-18).

Information boundary: friendly units in full; enemy units only while
`is_visible_to_alliance`, plus the enemy roster the custom battle screen shows; the
observation's `evaluation`, `final` and `setup` never reach a policy, nor do replay
frames or stills. Failure taxonomy (`protocol.py`): `ProtocolError`, `IllegalActionError`,
`PolicyFailure`, `MailboxTimeout` and `BattleRestarted` are infrastructure, protocol or
policy failures; a batch that fails validation is recorded as invalid and sent as no
orders. Only an engine-reported won, lost or draw is a gameplay outcome.

## Coding style and tests

Four-space indentation, `snake_case` functions and modules, `PascalCase` classes,
`UPPER_SNAKE_CASE` constants. Keep protocol handling separate from policy logic. Reserve
bridge stdout for protocol traffic; send diagnostics elsewhere. Match the surrounding code.
Do not run `ruff format` on hand-formatted files (most are); the WH3 report JavaScript uses
`prettier --print-width 100`. No overengineering, excessive abstractions or overly safe code.
Write in simple, concrete language (owner, 2026-10-20): say what a unit, controller or
experiment actually does; no inflated wording; explain technical terms when they help.
No punchlines in public or owner-voiced text (owner, 2026-11-04): whole connected sentences, no
tagline headings, closers for effect or "X, not Y"; rules in `runs/portfolio/AGENTS.md`, Writing.

Tests: [tests/README.md](../tests/README.md); [docs/testing.md](testing.md) holds proposed
guidelines; no coverage threshold. Prioritize action and target identity, stale observations,
terminal transitions, reproducible resets and bridge failures; add a regression for every
observed failure; validate mechanics against the original engine, not fixtures alone.
Regenerate the prompt snapshots in `tests/twwarhammer3/prompts/` (`WH3_WRITE_PROMPTS=1`) only
for an intended prompt change, a logged version. Each top-level definition in
`twwarhammer3_battle.lua` ends with an unindented `end` or `}` (Lua tests load them by name).
