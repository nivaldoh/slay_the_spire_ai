# Slay the Spire AI

An original-engine interface and reproducible learning experiments for Slay the Spire 1.
Original-engine wins, losses, seeded restarts, and frozen random/heuristic baselines
are verified. Budgeted PPO verified weight updates and interruption recovery, without
improving this fixed combat. A trained Qwen3-0.6B LoRA reproduced the teacher on the
reused scenario; broader encounter and held-out results remain unproven.
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
| Neural policy after twelve PPO updates | 8/8 | 72.00 |

The two-update pilot selected the same actions as its initial model. The larger
64-combat trial changed two paired trajectories and reduced mean HP by 0.75. These
results verify the learning loop but do not establish improved play. All attempts
use one game scenario and one neural initialization. See the
[audited comparison](docs/results/ppo-budget64-development-v1.json) and
[paired traces](docs/results/ppo-budget64-paired-evaluation.json). Earlier incomplete
evaluations remain separately recorded as infrastructure failures.

The language-model diagnostic used 42 public-heuristic rows (21 unique prompts),
64 actual LoRA updates and 527,360 padded training tokens. The unchanged model had
eight policy failures and no completed games; its final trained adapter won 8/8 at
HP77, exactly matching the teacher. This is imitation on reused data conditions,
not held-out generalization or a compute-matched comparison to PPO. See the
[language experiment, results and reproduction details](docs/language-experiment.md).

## Full runs with an API language model

`spire play` drives complete original-engine runs (Neow to death or victory) with an
OpenAI model choosing every action from a public, labeled choice list. Spend is priced
from reported usage and capped by a ledger before each call. See
[llm-play.md](docs/llm-play.md) for the information boundary, scaffolding and log.

```bash
export SPIRE_OPENAI_KEY_FILE=~/.config/robocasa/openai_api_key   # or OPENAI_API_KEY
uv run python -m spire play --model gpt-6-luna --effort low --seed RUNDEV1 \
  --budget-usd 25 --output runs/llm-example
uv run python scripts/play_digest.py runs/llm-example/run-0000
```

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

## Reproduce saved-result figures

[HP samples and paired differences](docs/figures/fixed-louse-hp.svg) and
[PPO probability/gradient diagnostics](docs/figures/ppo-movement.svg) are generated
from the explicit saved JSON inputs below. [Plot data](docs/figures/plot-data.json)
records all plotted points, input/script SHA-256 hashes, source/model identities,
and rendering versions. These are eight policy samples on one fixed development
scenario, with no error bars or generalization claim. Incomplete evaluations are
rejected; this script consumes saved audited summaries rather than re-auditing traces.

The verified renderer is the existing external `/home/niv/miniconda3/bin/python`
(Python 3.13.5, Matplotlib 3.11.0, NumPy 2.3.3, Pillow 12.3.0); the locked game/training
environment and dependencies are unchanged. Run from the repository root in that
environment, or an external environment with those versions:

```bash
python scripts/plot_results.py \
  --comparison docs/results/ppo-budget64-development-v1.json \
  --distribution docs/results/ppo-budget64-distribution-diagnostic.json \
  --gradients docs/results/ppo-budget64-gradient-diagnostic.json \
  --output docs/figures --png-directory runs/diagnostic-figures
```

SVGs have fixed metadata and element IDs for reproducible output. PNGs stay in
ignored `runs/`; rendering loads no game, model, GPU, or original bulky trajectory.
