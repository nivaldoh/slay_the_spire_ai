# Slay the Spire AI

An original-engine interface and reproducible learning experiments for Slay the Spire 1.
Two original-engine combat episodes and automatic seeded restarts are verified.
No learned-policy result is established yet.
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
The initial adapter will start seeded games from the main menu; arbitrary combat snapshots
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
