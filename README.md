# Slay the Spire AI

AI players for Slay the Spire 1 (Ironclad, Ascension 0) that act through the original
game, see only what a player could see, and leave an audited record of every decision.

## Status

| Track | Status | Page |
| --- | --- | --- |
| Full runs with an API model | **Current.** `gpt-6-luna` plays complete runs from a labeled list of public choices; its scaffolding changes one observed mistake at a time. Results per version: [log](docs/spire/fullrun/log.md). | [docs/spire/fullrun](docs/spire/fullrun/README.md) |
| First-combat benchmark | **Paused.** Verified original-engine loop on fixed floor-1 combats. PPO updated weights without playing better; a Qwen3-0.6B LoRA imitated the scripted heuristic (catalog HP 76.33 against 76.00). | [docs/spire/first-combat](docs/spire/first-combat/README.md) |
| Remotely trained open-weight model | **Planned.** Game-reward RL on Tinker, with a dynamics-prediction experiment. | [docs/spire/open-weight](docs/spire/open-weight/README.md) |

What is running and what comes next: [docs/state.md](docs/state.md). Repository layout
and working rules: [AGENTS.md](AGENTS.md). Game-neutral pieces (OpenAI calls with a spend
cap, ledgers, provenance) live in `src/gameai/`, so other games can reuse them.

## Setup

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run python -m spire doctor     # read-only check of the game, mods and runtime
```

The game runs on Windows from its Steam install and is driven from WSL through
CommunicationMod, with ModTheSpire and BaseMod from the Steam Workshop. The game and mod
jars stay outside Git; [docs/spire/integration.md](docs/spire/integration.md) records their pins and
the protocol's quirks.

## Play a full run

```bash
export SPIRE_OPENAI_KEY_FILE=~/.config/robocasa/openai_api_key   # or OPENAI_API_KEY
uv run python -m spire play --model gpt-6-luna --effort low --seed RUNDEV1 \
  --budget-usd 25 --output runs/fullrun/example
uv run python -m spire digest runs/fullrun/example            # per-seed table
uv run python -m spire digest runs/fullrun/example/run-0000   # floors, choices, reasons
```

Every API call is priced from its reported usage and refused in advance if the shared
ledger (`runs/llm-spend.jsonl`) could exceed `--budget-usd`.

## Ground rules

- Policies receive allowlisted public state only: no seed, RNG, draw order or hidden enemy
  state. Only the engine's own win or death screen counts as a gameplay outcome;
  infrastructure failures and interruptions are recorded separately.
- A game launch refuses uncommitted source changes and needs a new output directory. It
  records the source revision, configuration and engine and mod hashes with every message
  and action.
- Game files, mod jars, saves, bulky trajectories, checkpoints and keys never enter Git.
