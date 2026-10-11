# Slay the Spire AI

An original-engine interface and reproducible learning experiments for Slay the Spire 1.
Original-engine wins, losses, seeded restarts, and eight-attempt random/heuristic
baselines are verified. A real PPO pilot verified weight updates and interruption recovery. Initial and
trained policies tied in frozen evaluation; no gameplay improvement is established.
Start with [current state](docs/state.md) and the [operating guide](SLAY_THE_SPIRE_AGENT_GUIDE.md).

## Development

Use the locked Python environment:

```bash
uv sync --locked
uv run python -m spire --version
uv run pytest
uv run ruff check .
```

Runtime code initially uses the standard library. Pytest and Ruff are development tools.
The Windows game and Workshop mod jars stay outside Git. Local run evidence goes in
`runs/`, which is ignored; selected compact results can be published under `docs/`.

## Scope

Ironclad, Ascension 0, combat first. Policy inputs must contain only player-visible
information. Infrastructure failures and interrupted episodes are separate from game losses.
The adapter starts seeded games from the main menu; arbitrary combat snapshots
are not yet supported.

## Verified original-engine loop

On this WSL/Windows installation:

```bash
uv run python -m spire doctor --json
uv run python -m spire rollout --policy random --episodes 2 --output runs/random-example
uv run python -m spire rollout --policy heuristic --episodes 2 --output runs/heuristic-example
```

Rollouts require committed implementation files and a new output directory. They verify
pinned Workshop jars, deploy the stdlib relay to `C:/spire-agent`, configure CommunicationMod,
launch a bounded owned JVM, and record every engine message and selected action. Each episode
restarts from the main menu with the same seed, enters the first combat through a documented
Neow/map prefix, and stops on engine-confirmed victory or defeat. Logs distinguish unsupported
screens, rejected actions, bridge failures, time limits, and interruption from gameplay losses.

The default slice includes Ironclad's starter cards; potion use is excluded. Policies see
allowlisted public state with draw-pile order removed. Actions are bound to the observation
that generated them. This is an initial combat experiment interface, not a complete-run agent.
See [integration notes](docs/integration.md) for dependencies, information boundaries, and
known limitations. The initial two-episode random smoke run verified automatic original-engine
interaction; it does not establish learned performance.

## Auditing and development evaluation

```bash
uv run python -m spire report runs/random-example runs/heuristic-example
uv run python -m spire evaluate --policy random --suite configs/suites/louse_diagnostic_development_v1.json --output runs/random-development
```

The suite fixes one two-Louse combat and its normalized starting state, then repeats
eight policy attempts. It is a learning diagnostic, not a held-out generalization test.
A changed starting state stops the evaluation. The report reconstructs decisions and
terminal outcomes from saved evidence rather than trusting reported scores.

The same `evaluate --suite` interface also accepts [schema-2 development
catalogs](docs/catalogs.md): an explicit list of scenarios and policy seeds, with
per-scenario results and an equally weighted scenario average. `report` audits saved
catalog directories and compares matching catalogs. Report single-scenario runs
separately. New scenarios require original-engine discovery and repeatability
evidence before admission; the catalog schema alone does not establish coverage.

The frozen diagnostic results are:

| Policy | Wins | Mean final HP |
| --- | ---: | ---: |
| Uniform random | 8/8 | 68.00 |
| Starter heuristic | 8/8 | 77.00 |
| Initial neural policy | 8/8 | 72.75 |
| Neural policy after two PPO updates | 8/8 | 72.75 |

Initial and trained neural policies selected identical actions across these eight
sampling seeds despite changed probabilities. This pilot validates the learning
loop, not policy improvement. All attempts use one game scenario. See the
[audited comparison](docs/results/ppo-pilot-development-v1.json) and
[paired traces](docs/results/ppo-pilot-paired-evaluation.json). An earlier partial
trained evaluation failed at relay startup and remains separately recorded.

## Budgeted learning

The optional learner is a 12,498-parameter CPU actor-critic with masked PPO.
Install it with `uv sync --locked --extra train`; test with
`uv run --extra train pytest`.

```bash
uv run --extra train python -m spire train --suite configs/suites/louse_diagnostic_development_v1.json --output runs/ppo-example --episodes 8 --batch-steps 64 --updates 2 --time-budget 900 --seed 0
uv run --extra train python -m spire train --resume --output runs/ppo-example
uv run --extra train python -m spire evaluate --checkpoint <exported-policy.json> --suite configs/suites/louse_diagnostic_development_v1.json --output runs/ppo-evaluation
```

Resume preserves the original absolute deadline, optimizer, RNGs, and consumed
episode identities. Interrupted combat is recorded and excluded from training;
the next attempt starts a fresh game. `training.json` identifies immutable initial
and current policy artifacts for frozen evaluation. See [learning details](docs/learning.md)
and the [pilot contract](docs/research.md). The first original-engine pilot completed two updates from 92 audited transitions,
with seven completed combats and one deliberately interrupted attempt. All actor
weights changed; interrupted data was excluded and the original deadline survived
resume. See the [training audit](docs/results/ppo-pilot-training-audit.json).
Weight updates alone do not establish improved gameplay.
