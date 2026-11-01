# Slay the Spire guidance

Read this before Spire work anywhere in the repository, including its legacy configs,
tests and scripts, or shared code changes affecting Spire. It supplements the shared rules
in [the root AGENTS.md](../../AGENTS.md). Paths and commands below are relative to the
repository root.

The game is Slay the Spire 1, Ironclad, Ascension 0, running from its Windows Steam install
through WSL. Start with the [Spire state](../state.md#slay-the-spire), then the relevant
track: [full runs](fullrun/README.md), [first combat](first-combat/README.md) or
[open-weight](open-weight/README.md). Engine facts live in [integration.md](integration.md);
[approaches.md](approaches.md) surveys methods.

## Layout

```
src/spire/         Slay the Spire 1
  __main__.py      CLI: doctor, play, digest, watch, spend, stats, export (full runs);
                   rollout, evaluate, train, report (first combat)
  protocol.py      Decision/Action types, the error taxonomy and the first-combat
                   observation contract (frozen)
  policies.py      Scripted first-combat policies: random, starter heuristic, end turn (frozen)
  decisions.py     Public full-game boundary: labeled choices on every in-game screen
  engine/          Real-game plumbing for every track: Windows runtime, relay bridge, doctor,
                   and the Windows-side windows_relay.py
  fullrun/         Full-run track: play.py (complete-run loop for any policy), llm.py
                   (prompt, memory and replies: the tuning surface), digest.py (trace
                   summaries and mistake flags), watch.py (job events), stats.py (the
                   results register), export.py (offline model-request datasets)
  openweight/      Planned remote open-weight track (skeleton, mostly NotImplementedError):
                   tasks and seed splits, env backends, Tinker policy, rewards, rollout,
                   GRPO, dynamics
  combat/          First-combat benchmark: rollout, suites (evaluation), catalogs,
                   evidence audits
  ppo/             Actor-critic and the budgeted, resumable PPO runner
  language/        Local Qwen LoRA: demonstrations, SFT, frozen policy, evaluation,
                   sampling, REINFORCE
configs/llm/      Full-run system prompt and enemy rules notes (the tuning surface)
configs/suites/   First-combat suite and catalog declarations
scripts/          First-combat inventory, audits, dataset export, training drivers and plots
tests/spire/      Decision and protocol tests
tests/            Legacy Spire suites: combat/, engine/, fullrun/, language/, ppo/,
                  openweight/; fixtures/ holds engine transitions
docs/spire/       integration.md, approaches.md and one folder per track:
                  fullrun/, first-combat/, open-weight/
runs/             Spire evidence: fullrun/, fullrun-exports/, first-combat/, research-notes/
```

Spire predates the per-game directory convention; keep these legacy paths.
`src/spire/protocol.py` and `src/spire/policies.py` stay byte-stable: demonstration export
compares their syntax tree with the recorded teacher sources. New full-run behavior belongs
in `src/spire/fullrun/`.

Keep job modules (play, digest, watch, stats) separate from WH3's: Spire starts a fresh JVM
per run and its trace bytes must stay identical, while WH3 launches once per job and
restarts by rematch. Each game has its own result fields and exceptions.

## Commands

```bash
uv run --locked python scripts/check.py   # before each commit, as for WH3 (docs/workflow.md)
uv run pytest tests/spire/test_protocol.py -k <pattern>
uv run python -m spire doctor      # read-only runtime check
uv run python -m spire digest runs/fullrun/<job>   # per-seed table; add /run-0000 [--picks | --floor N]
uv run python -m spire watch runs/fullrun/<job>    # wait for the next finished run, stall or job end
uv run python -m spire spend       # Spire OpenAI ledger total; --provider openrouter|anthropic
uv run python -m spire stats       # milestones per model, effort and harness; --rebuild from runs/
uv run python -m spire export runs/fullrun/<job> ... --output runs/fullrun-exports/<name>
```

`spire play`, `rollout`, `evaluate`, `train` and `scripts/inventory_scenarios.py` run a real
game. `play`, `rollout`, `evaluate` and `train` need a new output directory and refuse
uncommitted changes in their source scope:

- `spire play`: `src/gameai/`, `src/spire/`, `configs/llm/`, `pyproject.toml`, `uv.lock`
  and `.python-version` (`fullrun/play.py` `SOURCES`).
- First-combat tools: the default `gameai.provenance.SOURCE_PATHS` includes all of `src/`
  (WH3 included), `scripts/`, `configs/` and the same three project files.

A play job stops before its next seed if a file in its scope changes. Draft in a git
worktree while a job runs. The root rule allows only one game controller at a time across
both games; Spire's own lock does not prevent a WH3 controller from starting.

## Architecture

Paths and Workshop jar hashes are pinned in `spire/engine/runtime.py`. One episode:

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
`decisions.py` builds it for full runs, `protocol.py` for the starter-card first
combat. On the wire, cards are one-based; monster targets, potion slots and `choose`
indexes are zero-based. Keep raw target positions after monsters die.
[integration.md](integration.md) records the other protocol quirks.

Failure taxonomy: `BridgeError` subclasses and protocol errors (`StaleActionError`,
`IllegalActionError`, `UnsupportedStateError`, `PolicyFailure`, …) are infrastructure or
policy failures. Only an engine-confirmed victory or death is a gameplay outcome.

## Tests and training

The `train` (CPU torch) and `llm` (CUDA torch, transformers, peft) extras conflict; use one
per command: `uv run --extra train ...` for PPO, `uv run --locked --extra llm ...` for local
language models. Without them, those tests skip through `importorskip`;
`uv sync --locked` removes their packages again.

- The original-engine regressions in `tests/combat/` read `runs/first-combat/` (override with
  `SPIRE_EVIDENCE_ROOT`) and skip when it is absent.
- `scripts/audit_ppo_training.py` and `scripts/audit_language_training.py` are read-only.
  Run them only on stopped runs, and write their reports outside the run directory.

## Evidence

Spire jobs live in `runs/<track>/<job>/`. Compact first-combat results are committed in
`docs/spire/first-combat/results/`. Each full-run `play` appends a row per run to
`docs/spire/fullrun/results.csv`. Log every version in `docs/spire/fullrun/log.md` and
commit the register with that entry.

The OpenAI ledger is `runs/llm-spend.jsonl`; OpenRouter uses
`runs/spire-openrouter-spend.jsonl` (`spire play --provider openrouter`) and Anthropic
`runs/spire-anthropic-spend.jsonl`. The shared OpenRouter and Anthropic allowances, credential settings, budget accounting and missing-ledger rules in
[the root guidance](../../AGENTS.md#evidence) apply. Never move or reset a ledger.
