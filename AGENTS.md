# Repository Guidelines

AI policies that play the original Windows games from WSL: Slay the Spire 1 (Ironclad,
Ascension 0) and Total War: WARHAMMER III (WH3; real-time custom battles through a Lua
mod). Start every session with [docs/state.md](docs/state.md): what is running, each
game's current track and next step. Then read the page of the track you are working on.

## Layout

```
src/gameai/        Game-neutral code both games import; it never imports a game package
  llm.py           OpenAI Responses transport, prices, Model (spend reservation, the
                   reply-retry loop)
  ledger.py        Append-only spend ledger with a hard budget, for any paid model
  provenance.py    Repository root, scoped source fingerprints, committed-source check,
                   atomic JSON writes
  windows.py       Windows games owned from WSL: runtime lock, supervised launch, probes
  windows_game.py  The Windows-side supervisor (job object, controller EOF and time limit)
src/spire/         Slay the Spire 1
  __main__.py      CLI: doctor, play, digest, watch, spend, stats (full runs); rollout,
                   evaluate, train, report (first combat)
  protocol.py      Decision/Action types, the error taxonomy and the first-combat
                   observation contract (frozen)
  policies.py      Scripted first-combat policies: random, starter heuristic, end turn (frozen)
  decisions.py     Public full-game boundary: labeled choices on every in-game screen
  engine/          Real-game plumbing for every track: Windows runtime, relay bridge, doctor,
                   and the Windows-side windows_relay.py
  fullrun/         Full-run track: play.py (complete-run loop for any policy), llm.py
                   (prompt, memory and replies: the tuning surface), digest.py (trace
                   summaries and mistake flags), watch.py (job events), stats.py (the
                   results register)
  openweight/      Planned remote open-weight track (skeleton, mostly NotImplementedError):
                   tasks and seed splits, env backends, Tinker policy, rewards, rollout,
                   GRPO, dynamics
  combat/          First-combat benchmark: rollout, suites (evaluation), catalogs,
                   evidence audits
  ppo/             Actor-critic and the budgeted, resumable PPO runner
  language/        Local Qwen LoRA: demonstrations, SFT, frozen policy, evaluation,
                   sampling, REINFORCE
src/twwarhammer3/  Total War: WARHAMMER III custom battles
  __main__.py      CLI: doctor, pack, launch, menu (runtime and UI probes); play, digest,
                   watch, stats, spend (battle jobs)
  protocol.py      Order validation and the error taxonomy; observations stay dicts
  engine/          runtime (pins, pack build, mod list, launch), startup (video skip), pack
                   (PFH5), mailbox (the file protocol with the Lua scripts), doctor
  mod/             Lua scripts packed into the game: JSON, UI steps, frontend menus, battle
  assets/          The blank startup clip and its MIT license
  battle/          play.py (job loop: launch, scenario setup, episodes, rematch), llm.py
                   (direct API-model controller), skills.py (per-unit skill executor),
                   commander.py (asynchronous API model over skills), scripted.py (hold,
                   attack nearest, axis probe), digest.py, watch.py (live), stats.py
configs/
  llm/             Spire: full-run system prompt and enemy rules notes (its tuning surface)
  suites/          Spire: first-combat suite and catalog declarations
  twwarhammer3/    WH3: llm and commander prompts, named scenarios, random-draw catalogue
scripts/           Spire first-combat tools (inventory, audits, dataset export, training
                   drivers, plots)
tests/             One directory per package; tests/fixtures holds Spire engine transitions
docs/
  state.md         The session page for both games
  spire/           integration.md (engine and protocol facts), approaches.md (survey),
                   fullrun/, first-combat/, open-weight/ (one folder per track)
  twwarhammer3/    Track page, integration facts, controllers, log and results register
runs/              Local evidence, ignored by Git; see runs/README.md
.claude/workflows/ wh3-version-review.js, the review step of the WH3 autoresearch loop
```

`spire/protocol.py` and `spire/policies.py` stay byte-stable: demonstration export compares
their syntax tree with the recorded teacher sources (WH3's `protocol.py` changes freely).
New full-run behavior belongs in `fullrun/`.

A new game gets `src/<game>/`, `configs/<game>/`, `docs/<game>/`, `runs/<game>/` and
`tests/<game>/`. Slay the Spire predates this and keeps `configs/llm/`, `configs/suites/`,
`tests/{combat,engine,fullrun,language,ppo,openweight}/`, `tests/test_decisions.py`,
`tests/test_protocol.py`, `tests/fixtures/`, `runs/fullrun/`, `runs/first-combat/`,
`runs/research-notes/` and `runs/llm-spend.jsonl`. Move code into `gameai` when a second
game would otherwise copy it, not before. The job modules (play, digest, watch, stats) stay
per game: Spire starts a fresh JVM per run and its trace bytes must stay identical, WH3
launches once per job and restarts by rematch, and each has its own result fields and
exceptions. Test files share one namespace (there is no `tests/__init__.py`), so every
test file name must be unique across `tests/`.

## Commands

```bash
uv sync --locked
uv run pytest                      # everything; or one track: uv run pytest tests/fullrun
uv run pytest tests/test_protocol.py -k <pattern>
uv run ruff check .
uv run python -m spire doctor      # read-only runtime check
uv run python -m spire digest runs/fullrun/<job>   # per-seed table; add /run-0000 [--picks | --floor N]
uv run python -m spire watch runs/fullrun/<job>    # wait for the next finished run, stall or job end
uv run python -m spire spend       # Spire API ledger total
uv run python -m spire stats       # milestones per model, effort and harness; --rebuild from runs/
uv run python -m twwarhammer3 doctor   # read-only: pins, preferences, running game
uv run python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>   # add /episode-0000
uv run python -m twwarhammer3 watch    # follow the running job beside the game; --prompts
uv run python -m twwarhammer3 stats    # results by policy, harness and mode; --rebuild
uv run python -m twwarhammer3 spend    # WH3 API ledger total
```

- The `train` (CPU torch) and `llm` (CUDA torch, transformers, peft) extras conflict; use
  one per command: `uv run --extra train ...` for PPO, `uv run --locked --extra llm ...` for
  local language models. Without them, those tests skip through `importorskip`.
- The original-engine regressions in `tests/combat/` read `runs/first-combat/` (override with
  `SPIRE_EVIDENCE_ROOT`) and skip when it is absent.
- `spire play`, `rollout`, `evaluate`, `train`, `scripts/inventory_scenarios.py`,
  `twwarhammer3 play` and `twwarhammer3 launch` run a real game (`menu` and `play --attach`
  use the game `launch` started). Both `play`s, `rollout`, `evaluate` and `train` need a new
  output directory and refuse uncommitted changes in their source scope: `src/gameai/`,
  `src/spire/` and `configs/llm/` for `spire play` (`fullrun/play.py` `SOURCES`);
  `src/gameai/`, `src/twwarhammer3/` and `configs/twwarhammer3/` for `twwarhammer3 play`
  (`battle/play.py` `SOURCES`); both add `pyproject.toml`, `uv.lock` and `.python-version`.
  The first-combat tools use the default `gameai.provenance.SOURCE_PATHS`: all of `src/`
  (WH3 included), `scripts/`, `configs/` and the same three files. `twwarhammer3 launch`
  checks no scope. A `play` job stops before its next seed or episode if a file in its
  scope changes, so an edit to `src/gameai/`, `pyproject.toml` or `uv.lock` stops either
  game's job; draft in a git worktree while one runs.
- Check "Active work" in `docs/state.md` first. Never run two game controllers at once, even
  for different games: each `RuntimeLock` (`C:/spire-agent/owner.lock`,
  `C:/wh3-agent/owner.lock`) only blocks a second controller of its own game.
- `scripts/audit_ppo_training.py` and `scripts/audit_language_training.py` are read-only.
  Run them only on stopped runs, and write their reports outside the run directory.
- WH3 battles always run unpaused at 1x speed, including diagnostic probes and smoke
  tests. Never pause or slow the battle to give a policy more thinking time.

## Architecture

Both games run on Windows from their Steam installs under `/mnt/c`; the controller runs in
WSL and owns the game process through `gameai.windows`.

### Slay the Spire

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
[docs/spire/integration.md](docs/spire/integration.md) records the other protocol quirks.

Failure taxonomy: `BridgeError` subclasses and protocol errors (`StaleActionError`,
`IllegalActionError`, `UnsupportedStateError`, `PolicyFailure`, …) are infrastructure or
policy failures. Only an engine-confirmed victory or death is a gameplay outcome.

### Total War: WARHAMMER III

There is no external game API; a Lua mod is the API
([how it works](docs/twwarhammer3/README.md#how-it-works)). The Steam build and executable
hash are pinned in `twwarhammer3/engine/runtime.py`. Under `RuntimeLock`
(`C:/wh3-agent/owner.lock`), `runtime.prepare_runtime` packs and installs the mod, and
`runtime.OwnedGame` starts `Warhammer3.exe` once per job under the same `windows_game.py`
supervisor. The controller and the Lua scripts exchange JSON files in
`C:/wh3-agent/bridge/` (`engine/mailbox.py` documents them). `battle/play.py` turns
`--scenario` into custom battle menu steps (no desktop input). Each episode repeats
observation → policy → validated orders → acknowledgement with the battle time they were
issued at; the battle keeps running meanwhile, and the measured delay goes into the next
prompt. Later episodes replay the battle through the results popup's rematch button.

Information boundary: friendly units in full; enemy units only while
`is_visible_to_alliance`, plus the enemy roster the custom battle screen shows. Failure
taxonomy (`protocol.py`): `ProtocolError`, `IllegalActionError`, `PolicyFailure`,
`MailboxTimeout` and `BattleRestarted` are infrastructure, protocol or policy failures; a
batch that fails validation is recorded as invalid and sent as no orders. Only an
engine-reported won, lost or draw is a gameplay outcome.

## Evidence

Run evidence stays out of Git (layout in `runs/README.md`): Spire jobs in
`runs/<track>/<job>/`, WH3 jobs in `runs/twwarhammer3/battle/<job>/`. Each game has its own
API spend ledger, `runs/llm-spend.jsonl` for Spire and `runs/twwarhammer3/llm-spend.jsonl`
for WH3, and a job's `--budget-usd` caps its ledger's total, earlier jobs included. Never
move or reset a ledger. Compact first-combat results are committed in
`docs/spire/first-combat/results/`. Each `play` appends one row per run or episode to its
game's results register (`docs/spire/fullrun/results.csv`,
`docs/twwarhammer3/results.csv`). Log every version in `docs/spire/fullrun/log.md` or
`docs/twwarhammer3/log.md` and commit the register with that entry. Update `docs/state.md`
when work starts, stops or changes direction.

## Coding Style

Four-space indentation, `snake_case` functions and modules, `PascalCase` classes,
`UPPER_SNAKE_CASE` constants. Keep protocol handling separate from policy logic. Reserve
bridge stdout for protocol traffic; send diagnostics elsewhere. Match the surrounding code.

Aim for simplicity and readability. Avoid overengineering and bloat. This is not
"enterprise production-grade" slop, so avoid excessive abstractions, overly safe code, etc.
Keep the codebase clean and lean.

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
jars, game packs or files extracted from them (`runs/twwarhammer3/vanilla/`), saves, bulky
trajectories or checkpoints, API keys, or `*:Zone.Identifier` files.
