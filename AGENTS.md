# Repository Guidelines

## Project Structure & Module Organization

Read `docs/state.md` for current evidence and next steps. `SLAY_THE_SPIRE_AGENT_GUIDE.md` is the project reference; consult relevant sections before implementing a milestone.

Create the planned layout as needed:

- `src/spire/`: game adapter, policies, training, evaluation, and reporting.
- `tests/`: protocol contracts and regression cases.
- `configs/`: experiment configurations.
- `docs/state.md`: current baseline, blockers, and next action.
- `docs/research.md`: experiment contracts and research decisions.
- `runs/`: run manifests, metrics, and evidence; exclude bulky artifacts from Git.

## Build, Test, and Development Commands

Use `uv sync --locked`, `uv run pytest`, and `uv run ruff check .`. `uv run python -m spire doctor` and `rollout` are implemented; see `README.md` for reproduction commands. Commit implementation changes before attributable live rollouts. Never run two game controllers concurrently.

Planned CLI commands, to implement incrementally:

- `python -m spire doctor`: report capabilities, versions, and blockers.
- `python -m spire rollout ...`: collect episodes from a named policy.
- `python -m spire train ...`: run budgeted, resumable training.
- `python -m spire evaluate ...`: score a frozen artifact on a named suite.
- `python -m spire report ...`: compare results and link evidence.

## Coding Style & Naming Conventions

For new Python code, use four-space indentation, `snake_case` functions/modules, `PascalCase` classes, and `UPPER_SNAKE_CASE` constants. Separate protocol handling from policy logic. Reserve bridge stdout for protocol traffic; send diagnostics elsewhere. Ruff checks imports and basic errors; use `uv run ruff format` for formatting.

## General Guidelines
Aim for simplicity and readability. Avoid slop and overengineering.

## Testing Guidelines

Use pytest with `tests/test_*.py`; run `uv run pytest`. No arbitrary coverage threshold is required.

Prioritize action/target identity, stale observations, terminal transitions, reproducible resets, and bridge failures. Add regressions for observed failures. Validate supported mechanics against the original engine; fixtures alone do not demonstrate working game integration.

## Commit & Pull Request Guidelines

Use concise, imperative commit subjects, such as `Add bridge readiness handshake`. Keep changes focused. The owner authorizes commits and pushes to `main`.

PRs should explain the problem, behavior changes, validation commands/results, and limitations. Link relevant issues and experiment artifacts when applicable.

## Experiment & Artifact Rules

Start with Ironclad, Ascension 0, and a combat benchmark. Exclude hidden game state from policy inputs. Record source revision, configuration, engine/mod versions, and evaluation output for each experiment; distinguish infrastructure failures from gameplay losses.

Never commit proprietary game files, mod jars, saves, bulky trajectories/checkpoints, or `*:Zone.Identifier` files.
