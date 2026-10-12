# Repository Guidelines

AI policies for Slay the Spire 1 (Ironclad, Ascension 0), played through the original game
from WSL. Start every session with [docs/state.md](docs/state.md): what is running, the
current track and the next step. Then read that track's page. The owner's original brief
is [docs/agent-guide.md](docs/agent-guide.md); read it once, not for every task.

## Layout

```
src/spire/
  __main__.py      CLI: doctor, play, digest, spend (full runs); rollout, evaluate, train, report (first combat)
  protocol.py      Decision/Action types, the error taxonomy and the first-combat observation contract (frozen)
  policies.py      Scripted first-combat policies: random, starter heuristic, end turn (frozen)
  provenance.py    Repository root, source fingerprints, committed-source check, atomic JSON writes
  engine/          Real-game plumbing for every track: Windows runtime, relay bridge, doctor,
                   and the Windows-side windows_game.py / windows_relay.py
  fullrun/         Current track: decisions.py (public full-run boundary), play.py (run loop),
                   llm.py (prompt, memory and replies: the tuning surface), api.py (OpenAI
                   transport, prices, spend ledger), digest.py (trace summaries)
  openweight/      Planned remote open-weight track (skeleton, mostly NotImplementedError): tasks
                   and seed splits, env backends, Tinker policy, rewards, rollout, GRPO, dynamics
  combat/          First-combat benchmark: rollout, suites (evaluation), catalogs, evidence audits
  ppo/             Actor-critic and the budgeted, resumable PPO runner
  language/        Local Qwen LoRA: demonstrations, SFT, frozen policy, evaluation, sampling, REINFORCE
configs/llm/       Full-run system prompt and enemy rules notes (the autoresearch surface)
configs/suites/    First-combat suite and catalog declarations
scripts/           Standalone first-combat tools (inventory, audits, dataset export, training drivers, plots)
tests/             One directory per package; tests/fixtures holds original-engine transitions
docs/              state.md, integration.md (engine and protocol facts), approaches.md (survey),
                   fullrun/, first-combat/, open-weight/ (one folder per track)
runs/              Local evidence, ignored by Git; see runs/README.md
```

`protocol.py` and `policies.py` stay byte-stable: demonstration export compares their syntax
tree with the recorded teacher sources. New full-run behavior belongs in `fullrun/`.

## Commands

```bash
uv sync --locked
uv run pytest                      # everything; or one track: uv run pytest tests/fullrun
uv run pytest tests/test_protocol.py -k <pattern>
uv run ruff check .                # format with: uv run ruff format
uv run python -m spire doctor      # read-only runtime check
uv run python -m spire digest runs/fullrun/<job>   # per-seed table; add /run-0000 [--floor N]
uv run python -m spire spend       # API ledger total
```

- The `train` (CPU torch) and `llm` (CUDA torch, transformers, peft) extras conflict; use
  one per command: `uv run --extra train ...` for PPO, `uv run --locked --extra llm ...` for
  local language models. Without them, those tests skip through `importorskip`.
- The original-engine regressions in `tests/combat/` read `runs/first-combat/` (override with
  `SPIRE_EVIDENCE_ROOT`) and skip when it is absent.
- `play`, `rollout`, `evaluate`, `train` and `scripts/inventory_scenarios.py` launch the real
  game. They refuse uncommitted changes under `src/`, `scripts/`, `configs/`,
  `pyproject.toml`, `uv.lock` and `.python-version`, and need a new output directory. Check
  "Active work" in `docs/state.md` first: a live job may need source and `HEAD` frozen.
  Never run two game controllers at once.
- `scripts/audit_ppo_training.py` and `scripts/audit_language_training.py` are read-only.
  Run them only on stopped runs, and write their reports outside the run directory.

## Architecture

The controller runs in WSL; the game runs on Windows from the Steam install under `/mnt/c`
(paths and Workshop jar hashes are pinned in `spire/engine/runtime.py`). One episode:

1. `runtime.prepare_runtime` checks the pinned ModTheSpire, BaseMod and CommunicationMod
   jars, copies them and the two Windows scripts to `C:/spire-agent`, and writes
   CommunicationMod's config so the mod launches the relay against the current WSL address.
2. `runtime.OwnedGame` runs `windows_game.py` with Windows Python, which holds the JVM in a
   Windows job object and kills it on controller EOF or a hard time limit. `RuntimeLock`, an
   flock on `C:/spire-agent/owner.lock`, allows one controller at a time.
3. CommunicationMod starts `windows_relay.py`, which connects to `bridge.BridgeServer` (a
   one-session TCP server in WSL), sends `ready` and passes JSON lines and commands through
   unchanged. Any bridge error ends the session; there is deliberately no reconnect.
4. The run loop sends `START IRONCLAD 0 <seed>`, settles initial `DEBUG` intents with a logged
   `wait 60`, then repeats: message → public `Decision` → policy → validated command. Every
   message and action is saved with a source fingerprint. `fullrun.play` hands every
   decision from Neow onward to the policy; `combat.rollout` walks a fixed Neow/map prefix
   to the first combat.

Information boundary: policies get a `Decision` (allowlisted public state, the draw pile as
an unordered multiset, candidates tied to that decision's id) and never the raw message.
`fullrun/decisions.py` builds it for full runs, `protocol.py` for the starter-card first
combat. On the wire, cards are one-based; monster targets, potion slots and `choose`
indexes are zero-based. Keep raw target positions after monsters die.
[docs/integration.md](docs/integration.md) records the other protocol quirks.

Failure taxonomy: `BridgeError` subclasses and protocol errors (`StaleActionError`,
`IllegalActionError`, `UnsupportedStateError`, `PolicyFailure`, …) are infrastructure or
policy failures. Only an engine-confirmed victory or death is a gameplay outcome.

## Evidence

Run evidence goes in `runs/<track>/<job>/` and stays out of Git (layout in
`runs/README.md`). The full-run API ledger is `runs/llm-spend.jsonl`; never move or reset it.
Compact first-combat results are committed in `docs/first-combat/results/`. Log every
full-run version in `docs/fullrun/log.md`, and update `docs/state.md` when work starts,
stops or changes direction.

## Coding Style

Four-space indentation, `snake_case` functions and modules, `PascalCase` classes,
`UPPER_SNAKE_CASE` constants. Keep protocol handling separate from policy logic. Reserve
bridge stdout for protocol traffic; send diagnostics elsewhere. Aim for simplicity and
readability; avoid slop and overengineering. Match the surrounding code.

## Testing

Pytest, `tests/<package>/test_*.py`; no coverage threshold. Prioritize action and target
identity, stale observations, terminal transitions, reproducible resets and bridge
failures. Add a regression for every observed failure. Fixtures alone do not demonstrate
working game integration; validate mechanics against the original engine.

## Commits

Concise, imperative subjects, such as `Add bridge readiness handshake`. Keep changes
focused. The owner authorizes commits and pushes to `main`. PRs explain the problem,
behavior changes, validation commands and results, and limitations.

## Experiment and Artifact Rules

Exclude hidden game state from policy inputs. Record source revision, configuration,
engine and mod versions, and evaluation output for each experiment; distinguish
infrastructure failures from gameplay losses. Never commit proprietary game files, mod
jars, saves, bulky trajectories or checkpoints, API keys, or `*:Zone.Identifier` files.
