# Game agents: Slay the Spire and Total War: WARHAMMER III

AI players for Slay the Spire 1 (Ironclad, Ascension 0) and Total War: WARHAMMER III (WH3)
custom battles. They act through the original games on Windows, driven from WSL, see only
what a player could see, and leave an audited record of every decision.

## Status

| Game | Track | Status | Page |
| --- | --- | --- | --- |
| WH3 | Battles with an API model | **Idle after C1 finished on 2026-10-15.** The [next plan](docs/twwarhammer3/benchmark.md#implementation-plan) prioritizes varied armies and battle types, shared progress measures, 2-3 exploratory battles per new scenario and one suite report; implementation has not started. Current controllers: direct `llm` (v16), its rules-only variant `llm_rules`, asynchronous `commander` (v3) over `skills` (v1.2), and scripted baselines. Real-time battles through a Lua mod, paired trials and offline HTML replays. Results: [log](docs/twwarhammer3/log.md). | [docs/twwarhammer3](docs/twwarhammer3/README.md) |
| Slay the Spire | Full runs with an API model | **Idle since 2026-10-13.** `gpt-6-luna` plays complete runs from a labeled list of public choices; its scaffolding changes one observed mistake at a time. v10 is untested: its only job stopped on floor 10 when WSL restarted. Results per version: [log](docs/spire/fullrun/log.md). | [docs/spire/fullrun](docs/spire/fullrun/README.md) |
| Slay the Spire | First-combat benchmark | **Paused.** Verified original-engine loop on fixed floor-1 combats. PPO updated weights without playing better; a Qwen3-0.6B LoRA imitated the scripted heuristic (catalog HP 76.33 against 76.00). | [docs/spire/first-combat](docs/spire/first-combat/README.md) |
| Slay the Spire | Remotely trained open-weight model | **Planned.** Game-reward RL on Tinker, with a dynamics-prediction experiment. | [docs/spire/open-weight](docs/spire/open-weight/README.md) |

What is running and what comes next: [docs/state.md](docs/state.md). Repository layout
and working rules: [AGENTS.md](AGENTS.md). Shared pieces (OpenAI calls with a spend cap,
ledgers, provenance, Windows process ownership) live in `src/gameai/`; both games use them.

## Setup

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run python -m spire doctor          # read-only check of the game, mods and runtime
uv run python -m twwarhammer3 doctor   # read-only check of WH3, its pins and preferences
```

Both games run on Windows from their Steam installs; the harness's Windows-side scripts
need Windows Python 3.13 at `C:/Python313/python.exe` (`gameai.windows.WINDOWS_PYTHON`).

Slay the Spire is driven through CommunicationMod, with ModTheSpire and BaseMod from the
Steam Workshop. The game and mod jars stay outside Git;
[docs/spire/integration.md](docs/spire/integration.md) records their pins and the
protocol's quirks.

WH3 is driven through a Lua mod pack that the harness builds and installs under
`C:/wh3-agent`. A launch also installs a startup-video skip that persists for ordinary
Steam launches. [docs/twwarhammer3/integration.md](docs/twwarhammer3/integration.md)
records the skip, the pinned Steam build and the engine facts;
[docs/twwarhammer3/README.md](docs/twwarhammer3/README.md#commands) says how to reverse the
skip.

## Play a full run

```bash
export SPIRE_OPENAI_KEY_FILE=~/.config/robocasa/openai_api_key   # or OPENAI_API_KEY
uv run python -m spire play --model gpt-6-luna --effort low --seed RUNDEV1 \
  --budget-usd 25 --output runs/fullrun/example
uv run python -m spire digest runs/fullrun/example            # per-seed table
uv run python -m spire digest runs/fullrun/example/run-0000   # floors, choices, reasons
```

## Play a battle

```bash
uv run python -m twwarhammer3 play --policy commander --budget-usd 25 --scenario random \
  --seed 2 --output runs/twwarhammer3/battle/example
uv run python -m twwarhammer3 digest runs/twwarhammer3/battle/example               # episodes
uv run python -m twwarhammer3 digest runs/twwarhammer3/battle/example/episode-0000  # orders
uv run python -m twwarhammer3 report runs/twwarhammer3/battle/example \
  --output runs/twwarhammer3/reports/example     # example.html, .json and .txt
```

`--scenario random` draws a map and both races from `--seed` and lets the game
autogenerate both armies. `--policy skills` needs no model or budget; comma-separated
policies (`--policy llm_rules,attack_nearest`) take turns on rematches of one battle.
[docs/twwarhammer3/README.md](docs/twwarhammer3/README.md#commands) lists every command.

Every API call is priced from its reported usage and refused in advance if its game's
ledger could exceed `--budget-usd`: `runs/llm-spend.jsonl` for Slay the Spire,
`runs/twwarhammer3/llm-spend.jsonl` for WH3. Both games read the key from `OPENAI_API_KEY`
or the file named by `SPIRE_OPENAI_KEY_FILE`, which keeps its first game's name.

## Ground rules

- Policies receive public state only: in Slay the Spire no seed, RNG, draw order or hidden
  enemy state; in WH3 enemy units only while the player's army can see them. Only an
  engine-reported result (Slay the Spire's victory or death screen, a WH3 battle won, lost
  or drawn) is a gameplay outcome; infrastructure failures and interruptions are recorded
  separately.
- A recorded job (`spire play`, `twwarhammer3 play`, the first-combat tools) refuses
  uncommitted source changes in its scope and needs a new output directory. It records the
  source revision, configuration and game and mod hashes with its evidence.
- WH3 battles always run unpaused at 1x speed.
- Game files, mod jars, game packs, saves, bulky trajectories, checkpoints and keys never
  enter Git.
