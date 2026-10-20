# Repository Guidelines

AI policies that play the original Windows games from WSL: Slay the Spire 1 (Ironclad,
Ascension 0) and Total War: WARHAMMER III (WH3; real-time custom battles through a Lua
mod). Start every session with [docs/state.md](docs/state.md): what is running, each
game's current track and next step. Then read the page of the track you are working on.
Codex loads this file; Claude Code imports it through `CLAUDE.md`. Keep shared guidance here.

## Verification (hard rule)

The owner's rule (2026-10-18): **if the owner has not explicitly discussed with the
assistant how to verify (repeatably test) whether a feature is correct, assume it might
have issues.** Be careful making claims about, or building on top of, unverified things.

How the assistant applies it:
- Passing tests, smoke runs and single battles are evidence, not verification. Say
  "unverified" when reporting or building on anything without an agreed method below.
- Every claim carries what it rests on: the number of battles or runs behind a rate, the
  check that decides it and its caveats. A summary never says more than its log entry.
- When a feature matters, propose a repeatable check; add a row below only after the
  owner agrees. A feature counts as verified only at revisions where its check passed.
- Test what matters, and add no slop tests (owner, 2026-10-18): balance verifying
  important behaviour against filling the codebase with low-value tests.

For each change:

1. State the observable behaviour and its independent reference (requirement, contract or
   trusted example); a recorded output alone is not proof of correctness.
2. Choose the cheapest relevant checks. For a bug, show the regression fails before the fix
   where feasible; for important verification, check it detects a plausible wrong implementation.
3. Run focused tests with `uv run --locked pytest -ra <tests>` and `uv run --locked ruff
   check .`; expand when a concrete risk requires it. Preserve useful failure output.
4. Report passed, failed, skipped and unavailable checks, and what each establishes.
   Component tests and recorded cases do not establish live-game effects or policy strength.

Agreed verification methods (feature, check and command, date agreed, last passing
revision):
- WH3 saved armies and experience: save a known army, change it, restart WH3 and reload;
  compare unit types, counts and ranks. Set several ranks using both increase and decrease,
  comparing lobby readback and battle-start ranks/stats: `uv run --locked python
  tests/twwarhammer3/check_wh3_army_setup.py --integration --output runs/twwarhammer3/army-check-<new-name>`.
  Extended 2026-10-19: disturb declared settings, check funds/permission refusals and a fixed
  reserve pool, then restore original settings. Passed with `e32b1b5` sources (four launches,
  ten-unit saved roster, three mounts, ranks 0/1/3/9, seven reserves; attack/defence exact,
  leadership XP bonuses relative to rank zero). Restart uses supervised shutdown; graceful
  exit, other modes, reinforcement XP and policy strength remain unverified.
- WH3 UI requests, failure reporting, scheduling, startup-query errors and session lifetime:
  real Python/Lua component checks, with simulated game APIs/play-loop observations:
  `uv run --locked pytest -ra tests/twwarhammer3`. Agreed 2026-10-19; passed at `e32b1b5`.
  These checks establish component contracts, not live order effects or policy strength.
- Play commands refuse a missing ledger file: `uv run pytest
  tests/fullrun/test_spire_cli.py::test_play_refuses_a_missing_ledger_before_any_job
  tests/twwarhammer3/test_wh3_controllers.py::test_each_model_controller_gets_its_own_prompt_and_the_shared_budget`;
  agreed 2026-10-18; passed at `6b054f3`.
- WH3 replacement mailbox requests reach Lua's pending state; duplicate delivery is rejected:
  `uv run --locked pytest -ra
  tests/twwarhammer3/test_wh3_mailbox.py::test_new_mailbox_requests_reach_lua_without_disabling_duplicate_rejection`;
  agreed 2026-10-19; passed at `f7b6c73`. No game execution claim.
- WH3 non-finite order fields are rejected before transmission, with invalid-batch feedback:
  `uv run --locked pytest -ra tests/twwarhammer3/test_wh3_protocol.py
  tests/twwarhammer3/test_wh3_play.py::test_illegal_scripted_orders_are_counted_and_not_sent`;
  agreed 2026-10-19; passed at `f7b6c73`. Play-loop observations are simulated.

## Working habits

The assistant's proposals for the owner's 2026-10-18 goal (less bookkeeping, garbage and
token use):
- `docs/state.md` stays status only, under about 120 lines, and holds the current next
  steps (other pages keep candidates and deferred items). New owner directions go in
  `docs/owner-direction.md`. A log entry stays within about 20 lines: what changed, its
  evidence with counts, and what is unverified.
- Read docs by section; do not reload full guidance already present in the session.
  Use multi-agent workflows only for independent verification, the WH3 loop's review step,
  or when the owner asks.
- Write in simple, concrete language (owner, 2026-10-20). Describe what a unit, controller
  or experiment actually does. Avoid inflated wording and unnecessary jargon; explain
  technical terms when they help.
- Put task-created scripts, logs, temporary artifacts and diagnostics inside this repository
  (normally ignored `runs/`), never in the environment/home root or unrelated directories.
  Keep test scratch directories there too; inventory earlier garbage for a later cleanup
  rather than scattering more files.
- Delete a branch and its worktree once merged; create worktrees outside `/tmp`, which a
  WSL restart wipes. While a WH3 queue runs, commit nothing: it stops before its next job
  when HEAD moves. Add no file, scenario or diagnostic that no planned experiment uses.
- When `doctor` or a job warns that a game build differs from its pin, tell the owner;
  re-pin only with their approval.

## Layout

```
src/gameai/        Game-neutral code both games import; it never imports a game package
  llm.py           Responses transport, Model (spend reservation, the
                   reply-retry loop)
  providers.py     OpenAI/OpenRouter endpoints, credentials, model settings and price ceilings
  ledger.py        Append-only spend ledger with a hard budget, for any paid model
  sft.py           Fine-tuning datasets from either game's export (docs/posttraining.md)
  provenance.py    Repository root, scoped source fingerprints, committed-source check,
                   atomic JSON writes
  windows.py       Windows games owned from WSL: runtime lock, supervised launch, probes
  windows_game.py  The Windows-side supervisor (job object, controller EOF and time limit)
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
src/twwarhammer3/  Total War: WARHAMMER III custom battles
  __main__.py      CLI: doctor, pack, launch, menu (runtime and UI probes); play, digest,
                   watch, card, stats, report, export, spend (jobs and offline evidence)
  protocol.py      Order types and validation, the error taxonomy; observations stay dicts
  engine/          runtime (pins, pack build, mod list, launch), startup (video skip), pack
                   (PFH5), mailbox (bridge files; its docstring is the observation
                   reference), doctor, windows_capture.py (passive stills, Windows Python)
  mod/             Lua scripts packed into the game: battle, frontend menus, and in _lib/
                   UI steps, JSON and twwarhammer3_imagery.lua (the stills camera)
  assets/          The blank startup clip and its MIT license
  battle/          play.py (job loop: launch, setup, episodes, rematch, register row),
                   setup.py (scenarios with `base` inheritance, lobby steps, benchmark
                   checks; its docstring is the scenario field reference), controllers.py
                   (policy names, model prompts, rotation, outside controllers), llm.py
                   (direct API-model controller: llm, llm_rules), commander.py
                   (asynchronous API model over skills), skills.py (per-unit skill
                   executor, probe_abilities), scripted.py (hold, attack_nearest,
                   rush_nearest), calibration.py (disclosed scenario diagnostics),
                   capture.py (1 Hz replay recorder and stills), export.py (offline model
                   decisions, exchanges and provenance), digest.py
                   (trace summaries), watch.py (follow a job), stats.py (results
                   register), report.py (paired statistics), report_html.py, replay.py
                   and report_assets/ (the offline HTML report and its replay)
configs/
  llm/             Spire: full-run system prompt and enemy rules notes (its tuning surface)
  suites/          Spire: first-combat suite and catalog declarations
  twwarhammer3/    WH3: system_prompt.md (llm), rules_prompt.md (llm_rules),
                   commander_prompt.md, scenarios.json, custom_battle.json (random draws),
                   report_notes.json (the report's scenario, unit and highlight text),
                   benchmark_jobs.json (the jobs the report and export read)
scripts/           Spire first-combat tools (inventory, audits, dataset export, training
                   drivers, plots); wh3_queue.py runs a frozen plan of WH3 play jobs;
                   wh3_db.py reads WH3 unit costs and attributes from the game database;
                   sft_smoke.py, a local LoRA smoke test of a built dataset
tests/             One directory per package; tests/fixtures holds Spire engine transitions;
                   test_doc_links.py checks every Markdown link and anchor
docs/
  state.md         The session page for both games: status only
  owner-direction.md  Every dated owner direction, newest first; superseded ones marked
  posttraining.md  Traces to fine-tuning datasets for both games: roles, contract, splits
  spire/           integration.md (engine and protocol facts), approaches.md (survey),
                   fullrun/, first-combat/, open-weight/ (one folder per track)
  twwarhammer3/    README.md (track page; its Pages table lists the others), log.md
                   (newest first, versions on main at the top), results.csv
runs/              Local evidence, ignored by Git; see runs/README.md
.claude/workflows/ wh3-version-review.js, the review step of the WH3 autoresearch loop
```

`spire/protocol.py` and `spire/policies.py` stay byte-stable: demonstration export compares
their syntax tree with the recorded teacher sources (WH3's `protocol.py` changes freely).
New full-run behavior belongs in `fullrun/`.

A new game gets `src/<game>/`, `configs/<game>/`, `docs/<game>/`, `runs/<game>/` and
`tests/<game>/`. Slay the Spire predates this and keeps `configs/llm/`, `configs/suites/`,
`tests/{combat,engine,fullrun,language,ppo,openweight}/`, `tests/test_decisions.py`,
`tests/test_protocol.py`, `tests/fixtures/`, `runs/fullrun/`, `runs/fullrun-exports/`,
`runs/first-combat/`, `runs/research-notes/`, `runs/llm-spend.jsonl` and
`runs/spire-openrouter-spend.jsonl`. Move code into `gameai` when a second game would
otherwise copy it, not before. The job modules (play, digest, watch, stats) stay per game:
Spire starts a fresh JVM per run and its trace bytes must stay identical, WH3 launches once
per job and restarts by rematch, and each has its own result fields and exceptions. Test
files share one namespace (there is no `tests/__init__.py`), so every test file name must
be unique across `tests/`.

## Commands

```bash
uv sync --locked
uv run --locked pytest -ra          # everything; or append tests/twwarhammer3 for WH3
uv run pytest tests/test_protocol.py -k <pattern>
uv run ruff check .
uv run python -m spire doctor      # read-only runtime check
uv run python -m spire digest runs/fullrun/<job>   # per-seed table; add /run-0000 [--picks | --floor N]
uv run python -m spire watch runs/fullrun/<job>    # wait for the next finished run, stall or job end
uv run python -m spire spend       # Spire OpenAI ledger total; --provider openrouter for OpenRouter
uv run python -m spire stats       # milestones per model, effort and harness; --rebuild from runs/
uv run python -m spire export runs/fullrun/<job> ... --output runs/fullrun-exports/<name>
uv run python -m twwarhammer3 doctor   # read-only: pins, preferences, running game
uv run python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>   # add /episode-0000 [--at S]; --units
uv run python -m twwarhammer3 watch    # follow the running job beside the game; --prompts
uv run python -m twwarhammer3 watch runs/twwarhammer3/battle/<job> --next   # next episode, stall or end
uv run python -m twwarhammer3 stats    # results by scenario, policy, model, harness and mode
uv run python -m twwarhammer3 card chariot [JOB_OR_PLAN_DIR ...]  # tactic-card evidence
uv run python -m twwarhammer3 report <job> [<job> ...] --output runs/twwarhammer3/reports/<name>
uv run python -m twwarhammer3 export <job> [<job> ...] --output runs/twwarhammer3/exports/<name>
uv run python -m twwarhammer3 spend    # WH3 OpenAI ledger total; --provider openrouter for OpenRouter
uv run python -m gameai.sft <export> [<export> ...] --output runs/sft/<name>   # see docs/posttraining.md
```

- The dev group includes lupa (Lua 5.1) and Pillow, so `uv run pytest` runs the WH3 Lua and
  image tests. The `train` (CPU torch) and `llm` (CUDA torch, transformers, peft) extras
  conflict; use one per command: `uv run --extra train ...` for PPO, `uv run --locked
  --extra llm ...` for local language models. Without them, those tests skip through
  `importorskip`; `uv sync --locked` removes their packages again.
- The original-engine regressions in `tests/combat/` read `runs/first-combat/` (override with
  `SPIRE_EVIDENCE_ROOT`) and skip when it is absent.
- `spire play`, `rollout`, `evaluate`, `train`, `scripts/inventory_scenarios.py`,
  `twwarhammer3 play`, `twwarhammer3 launch` and `scripts/wh3_queue.py` (a queue of WH3
  `play` jobs) run a real game (`menu` and `play --attach` use the game `launch` started).
  Both `play`s, `rollout`, `evaluate` and `train` need a new output directory and refuse
  uncommitted changes in their source scope: `src/gameai/`, `src/spire/` and
  `configs/llm/` for `spire play` (`fullrun/play.py` `SOURCES`);
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
hash are pinned in `twwarhammer3/engine/runtime.py`; Steam may update the game, and a
different build warns and is recorded but never blocks (owner, 2026-10-18). Under `RuntimeLock`
(`C:/wh3-agent/owner.lock`), `runtime.prepare_runtime` packs and installs the mod, and
`runtime.OwnedGame` starts `Warhammer3.exe` once per job under the same `windows_game.py`
supervisor. The controller and the Lua scripts exchange JSON files in
`C:/wh3-agent/bridge/` (`engine/mailbox.py` documents them). `battle/setup.py` turns
`--scenario` into custom battle menu steps (no desktop input). Each episode repeats
observation → policy → validated orders → acknowledgement with the battle time they were
issued at; the battle keeps running meanwhile, and the measured delay goes into the next
prompt. Later episodes replay the battle through the results popup's rematch button; one
job can rotate several controllers over them (`--policy a,b`), and `report` compares
them.

Information boundary: friendly units in full; enemy units only while
`is_visible_to_alliance`, plus the enemy roster the custom battle screen shows; the
observation's `evaluation`, `final` and `setup` never reach a policy, nor do replay
frames or stills. Failure
taxonomy (`protocol.py`): `ProtocolError`, `IllegalActionError`, `PolicyFailure`,
`MailboxTimeout` and `BattleRestarted` are infrastructure, protocol or policy failures; a
batch that fails validation is recorded as invalid and sent as no orders. Only an
engine-reported won, lost or draw is a gameplay outcome.

## Evidence

Run evidence stays out of Git (layout in `runs/README.md`): Spire jobs in
`runs/<track>/<job>/`, WH3 jobs in `runs/twwarhammer3/battle/<job>/`. Each game has its own
API spend ledgers: OpenAI uses `runs/llm-spend.jsonl` (Spire) and
`runs/twwarhammer3/llm-spend.jsonl` (WH3); OpenRouter (`spire play --provider openrouter`,
`twwarhammer3 play --provider openrouter`; key from `OPENROUTER_API_KEY` or the file named
by `OPENROUTER_API_KEY_FILE`) uses `runs/spire-openrouter-spend.jsonl` and
`runs/twwarhammer3/openrouter-spend.jsonl`. A job's `--budget-usd` caps its selected
ledger's total, earlier jobs included. The owner's $50 OpenRouter allowance covers both
OpenRouter files, so a job's `--budget-usd` must leave room for the other file's total
(`spend --provider openrouter` in each game). Never move or reset a ledger. Compact
first-combat results are committed in `docs/spire/first-combat/results/`. Each `play`
appends one row per run or episode to its game's results register
(`docs/spire/fullrun/results.csv`, `docs/twwarhammer3/results.csv`). Log every version in
`docs/spire/fullrun/log.md` or `docs/twwarhammer3/log.md` and commit the register with
that entry. Update `docs/state.md` when work starts, stops or changes direction, and keep
it short: what runs, what is stopped and why, what is next, with links. Results,
validation counts and history go in the logs. A play command refuses a ledger file that
does not exist (a mistyped path or a job started from a worktree would count from $0):
create it deliberately for a new ledger.

## Coding Style

Four-space indentation, `snake_case` functions and modules, `PascalCase` classes,
`UPPER_SNAKE_CASE` constants. Keep protocol handling separate from policy logic. Reserve
bridge stdout for protocol traffic; send diagnostics elsewhere. Match the surrounding code.
`uv run ruff check .` must pass; do not run `ruff format` on hand-formatted files (most
modules are). The WH3 report JavaScript uses `prettier --print-width 100`.

Aim for simplicity and readability. Avoid overengineering and bloat. This is not
"enterprise production-grade" slop, so avoid excessive abstractions, overly safe code, etc.
Keep the codebase clean and lean.

## Testing

Pytest, `tests/<package>/test_*.py`; no coverage threshold. Prioritize action and target
identity, stale observations, terminal transitions, reproducible resets and bridge
failures. Add a regression for every observed failure. Fixtures alone do not demonstrate
working game integration; validate mechanics against the original engine.

WH3 specifics: `tests/twwarhammer3/test_wh3_prompts.py` compares the exact rendered model
prompts with `tests/twwarhammer3/prompts/`; regenerate them (`WH3_WRITE_PROMPTS=1`) only
for an intended prompt change, which is a logged version. The Lua tests run the mod under
Lua 5.1 and load battle-script definitions by name (`tests/twwarhammer3/wh3_lua.py`), so
every top-level definition in `twwarhammer3_battle.lua` ends with an unindented `end` or `}`.

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
