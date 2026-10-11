# Slay the Spire AI

An original-engine interface and reproducible learning experiments for Slay the Spire 1.
Bootstrap work is in progress; no gameplay or learned-policy result is established yet.
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
