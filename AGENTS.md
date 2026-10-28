# Repository Guidelines

AI policies for original Windows games from WSL. Current focus: Total War: WARHAMMER III
(WH3; real-time custom battles through a Lua mod). Start with [docs/state.md](docs/state.md):
read "Active work" and the relevant track, then that track's page.
Codex loads this file; Claude Code imports it through `CLAUDE.md`.

Keep shared and WH3 guidance here. Before Spire work, read
[docs/spire/AGENTS.md](docs/spire/AGENTS.md), including work on its source, legacy configs,
tests, scripts, or shared code affecting Spire. Skip that file for WH3-only work.

## Verification (hard rule)

The owner's rule (2026-10-18): **if the owner has not explicitly discussed with the
assistant how to verify (repeatably test) whether a feature is correct, assume it might
have issues.** Be careful making claims about, or building on top of, unverified things.

How the assistant applies it:
- Passing tests, smoke runs and single battles are evidence, not verification. Say
  "unverified" when reporting or building on anything without an agreed method.
- Every claim carries what it rests on: the number of battles or runs behind a rate, the
  check that decides it and its caveats. A summary never says more than its log entry.
- When a feature matters, propose a repeatable check; add it to
  [docs/agreed-checks.md](docs/agreed-checks.md) only after the owner agrees. A feature
  counts as verified only at revisions where its check passed there.
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

## Judgement calls

The owner's rule (2026-10-23): agents execute; the owner decides. A judgement call is a
choice no owner direction made that fixes what a benchmark measures, how something is
verified, what comes next, a design whose alternatives change results or their meaning, or
a parameter with benchmark or plan meaning. An agent that makes or finds one marks it in the
same change at the nearest convenient spot (a comment above the line; a note in the page
that documents a file that cannot carry one): `JUDGEMENT:`, or `JUDGEMENT?:` when unsure it
counts, then in one to three lines what was chosen, who and when, the alternative that would
change results and what rests on it. A marked spot may be wrong: say "rests on JUDGEMENT
<file> <name>" for anything built on it, copy its value nowhere without the marker, and park
what [docs/autonomy.md](docs/autonomy.md) parks; a marker is not permission to decide. Only
the owner removes or weakens a marker (an agent only when quoting the owner's words on that
spot in the commit); approval is not verification. Placement limits, the listing command and
the marking pass: [docs/judgement.md](docs/judgement.md).

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

## Working while the owner is away

Proposed 2026-10-21, in force once the owner says yes: when the owner says they cannot
review or are leaving, follow [docs/autonomy.md](docs/autonomy.md). Each task must finish
useful work or reduce a named uncertainty, with a reference and stopping point. Reuse
existing evidence; keep at most three independently reviewable changes waiting across
agents and sessions. Stop unapproved external effects and respect harness refusals. Park
adoption of changes to benchmark meaning; prepare only evidence that helps the choice.
Runtime/experiment code stays on local branches; new checks remain "proposed, not yet
agreed", and dependencies cannot outrun their evidence. Game time needs an away window and
the page's named-plan/check/probe rules. At capacity, finish or simplify pending work; if
no useful permitted step remains, record the resume condition and stop.

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
src/twwarhammer3/  Total War: WARHAMMER III custom battles
  __main__.py      CLI: doctor, pack, launch, menu (runtime and UI probes); play, digest,
                   watch, card, stats, report, export, spend (jobs and offline evidence)
  protocol.py      Order types and validation, the error taxonomy; observations stay dicts
  engine/          runtime (pins, pack build, mod list, launch), startup (video skip), pack
                   (PFH5), mailbox (bridge files; its docstring is the observation
                   reference), doctor, windows_capture.py (passive stills, Windows Python),
                   checkpoint_agent.js and checkpoint_frida.py (the checkpoint Frida agent)
  mod/             Lua scripts packed into the game: battle, frontend menus, and in _lib/
                   UI steps, JSON and twwarhammer3_imagery.lua (the stills camera)
  assets/          The blank startup clip and its MIT license
  battle/          play.py (job loop: launch, setup, episodes, rematch, register row),
                   setup.py (scenarios with `base` inheritance, lobby steps, benchmark
                   checks; its docstring is the scenario field reference), checkpoint.py
                   (battle checkpoints: save, fast checked rebuild, live handover),
                   controllers.py
                   (policy names, model prompts, rotation, outside controllers), llm.py
                   (direct API-model controller: llm, llm_rules), commander.py
                   (asynchronous API model over skills), skills.py (per-unit skill
                   executor, probe_abilities), scripted.py (hold, attack_nearest,
                   rush_nearest), team.py (two scripted members sharing one army),
                   calibration.py (disclosed scenario diagnostics),
                   cards.py (tactic cards: foils, witness, admission rule, board and
                   verdict; backs `card`), capture.py (1 Hz replay recorder and stills),
                   export.py (offline model decisions, exchanges and provenance),
                   digest.py (trace summaries), watch.py (follow a job), stats.py
                   (results register), report.py (paired statistics), report_html.py,
                   replay.py and report_assets/ (the offline HTML report and its replay)
configs/
  twwarhammer3/    WH3: system_prompt.md (llm), rules_prompt.md (llm_rules),
                   commander_prompt.md, scenarios.json, custom_battle.json (random draws),
                   report_notes.json (the report's scenario, unit and highlight text),
                   benchmark_jobs.json (the jobs the report and export read)
scripts/           wh3_queue.py runs a frozen plan of WH3 play jobs; wh3_db.py reads
                   WH3 unit costs and attributes from the game database; sft_smoke.py
                   runs a local LoRA smoke test of a built dataset
tests/             Tests per package; test_doc_links.py checks Markdown links and anchors
docs/
  state.md         The session page for both games: status only
  owner-direction.md  Every dated owner direction, newest first; superseded ones marked
  autonomy.md      What agents may do alone while the owner is away
  judgement.md     Judgement calls: the marker, placement limits and the marking pass
  agreed-checks.md The owner's agreed checks and the revisions where each passed
  posttraining.md  Traces to fine-tuning datasets for both games: roles, contract, splits
  thesis/          The proposed master's thesis: proposal, directions, related work;
                   notes/README.md indexes the research notes (untracked: git grep misses it)
  twwarhammer3/    README.md (track page; its Pages table lists the others), log.md
                   (newest first, versions on main at the top), results.csv
runs/              Local evidence, ignored by Git; see runs/README.md
.claude/workflows/ wh3-version-review.js, the review step of the WH3 autoresearch loop
```

A new game gets `src/<game>/`, `configs/<game>/`, `docs/<game>/`, `runs/<game>/` and
`tests/<game>/`. Move code into `gameai` when a second game would otherwise copy it,
not before. The job modules (play, digest, watch, stats) stay per game: launch semantics,
trace formats, result fields and exceptions differ. WH3 launches once per job and restarts
by rematch; its `protocol.py` changes freely. Test files share one namespace (there is no
`tests/__init__.py`), so every test file name must be unique across `tests/`.

## Commands

```bash
uv sync --locked
uv run --locked pytest -ra          # everything; or append tests/twwarhammer3 for WH3
uv run ruff check .
uv run python -m twwarhammer3 doctor   # read-only: pins, preferences, running game
uv run python -m twwarhammer3 digest runs/twwarhammer3/battle/<job>   # add /episode-0000 [--at S]; --units
uv run python -m twwarhammer3 watch    # follow the running job beside the game; --prompts
uv run python -m twwarhammer3 watch runs/twwarhammer3/battle/<job> --next   # next episode, stall or end
uv run python -m twwarhammer3 stats    # results by scenario, policy, model, harness and mode
uv run python -m twwarhammer3 card chariot [JOB_OR_PLAN_DIR ...]  # tactic-card evidence
uv run python -m twwarhammer3 report <job> [<job> ...] --output runs/twwarhammer3/reports/<name>
uv run python -m twwarhammer3 export <job> [<job> ...] --output runs/twwarhammer3/exports/<name>
uv run python -m twwarhammer3 spend    # WH3 OpenAI ledger total; --provider openrouter for OpenRouter
uv run --locked python tests/twwarhammer3/check_wh3_checkpoint.py --output runs/twwarhammer3/checkpoint-check-<name>   # battle checkpoints, 4 launches
uv run python -m gameai.sft <export> [<export> ...] --output runs/sft/<name>   # see docs/posttraining.md
git grep -n JUDGEMENT -- ':!AGENTS.md' ':!docs/judgement.md'   # marked judgement calls awaiting the owner
```

- The dev group includes lupa (Lua 5.1) and Pillow, so `uv run pytest` runs the WH3 Lua and
  image tests. The `train` (CPU torch) and `llm` (CUDA torch, transformers, peft) extras
  conflict; use only one per command. Without them, those tests skip through `importorskip`;
  `uv sync --locked` removes their packages again.
- `twwarhammer3 play`, `twwarhammer3 launch` and `scripts/wh3_queue.py` run a real game
  (`menu` and `play --attach` use the game `launch` started). `play` needs a new output
  directory and refuses uncommitted changes in its source scope: `src/gameai/`,
  `src/twwarhammer3/`, `configs/twwarhammer3/`, `pyproject.toml`, `uv.lock` and
  `.python-version` (`battle/play.py` `SOURCES`). `launch` checks no scope.
  A play job stops before its next episode if a file in its scope changes. Shared source
  and dependency changes can stop either game. Check any running job's source scope before
  editing, even another game's files; draft in a git worktree while one runs.
- Check "Active work" in `docs/state.md` first. Never run two game controllers at once,
  even for different games: each `RuntimeLock` only protects its own game.
- WH3 battles always run unpaused at 1x speed, including diagnostic probes and smoke
  tests. Never pause or slow the battle to give a policy more thinking time. One exception
  (owner, 2026-10-25): a checkpoint restore may rebuild the battle faster than 1x before
  its handover; from the handover on, 1x.

## Architecture

Both games run on Windows from their Steam installs under `/mnt/c`; the controller runs in
WSL and owns the game process through `gameai.windows`.

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
them. A battle can also be saved at a tick and restored exactly (`battle/checkpoint.py`,
a Frida agent in `engine/`; [checkpoints.md](docs/twwarhammer3/checkpoints.md)).

Information boundary: friendly units in full; enemy units only while
`is_visible_to_alliance`, plus the enemy roster the custom battle screen shows; the
observation's `evaluation`, `final` and `setup` never reach a policy, nor do replay
frames or stills. Failure
taxonomy (`protocol.py`): `ProtocolError`, `IllegalActionError`, `PolicyFailure`,
`MailboxTimeout` and `BattleRestarted` are infrastructure, protocol or policy failures; a
batch that fails validation is recorded as invalid and sent as no orders. Only an
engine-reported won, lost or draw is a gameplay outcome.

## Evidence

Run evidence stays out of Git (layout in `runs/README.md`). WH3 jobs live in
`runs/twwarhammer3/battle/<job>/`. Its OpenAI ledger is `runs/twwarhammer3/llm-spend.jsonl`;
OpenRouter uses `runs/twwarhammer3/openrouter-spend.jsonl` (`play --provider openrouter`;
key from `OPENROUTER_API_KEY` or the file named by `OPENROUTER_API_KEY_FILE`).

A job's `--budget-usd` caps its selected ledger's total, earlier jobs included. The owner's
$50 OpenRouter allowance covers both games: leave room for the total in
`runs/spire-openrouter-spend.jsonl` too (`uv run python -m spire spend --provider openrouter`).
Never move or reset a ledger. A play command refuses a ledger file that does not exist
(a mistyped path or a job started from a worktree would count from $0): create it
deliberately for a new ledger.

Each WH3 `play` appends one row per episode to `docs/twwarhammer3/results.csv`. Log every
version in `docs/twwarhammer3/log.md` and commit the register with that entry. Update
`docs/state.md` when work starts, stops or changes direction, and keep it short: what runs,
what is stopped and why, what is next, with links. Results, validation counts and history
go in the logs.

## Coding Style

Four-space indentation, `snake_case` functions and modules, `PascalCase` classes,
`UPPER_SNAKE_CASE` constants. Keep protocol handling separate from policy logic. Reserve
bridge stdout for protocol traffic; send diagnostics elsewhere. Match the surrounding code.
`uv run ruff check .` must pass; do not run `ruff format` on hand-formatted files (most
modules are). The WH3 report JavaScript uses `prettier --print-width 100`.

Aim for simplicity and readability. Avoid overengineering and bloat. This is not
"enterprise production-grade" slop, so avoid excessive abstractions, overly safe code, etc.
Keep the codebase clean and lean. Your writing should be simple, intuitive, well-structured, easy to read. Favor concrete, concise wording over annoying abstract jargon-heavy language.

## Testing

Start with [tests/README.md](tests/README.md) for the current suites and their limits.
[docs/testing.md](docs/testing.md) contains proposed guidelines and reference projects;
it does not add agreed verification methods.

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
