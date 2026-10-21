# Running a WH3 benchmark

The runbook: declare a scenario, play paired launches, plug in your own controller, run a
plan of jobs, stop cleanly and make the report. What the numbers mean is in
[benchmark.md](benchmark.md); the report in [reports.md](reports.md). Check
[docs/state.md](../state.md) first: never run two game controllers at once, of either
game. Battles always run unpaused at 1x.

## Before a run

Use the [evaluation guidelines](evaluation-guidelines.md) to define the question,
sampling, scoring and failure rules; its [study plan checklist](evaluation-guidelines.md#before-you-start)
is a short planning template. New checks and score changes there remain proposals.

The supported setup:
- Windows with WSL2, Steam running and logged in, and WH3 at the build pinned in
  `src/twwarhammer3/engine/runtime.py` (another build warns and is recorded), in the
  default Steam library on `C:`;
- Windows Python 3.13 at `C:/Python313/python.exe` (with Pillow, only for `--stills`);
- the content the scenario uses (its `content` lists the DLC);
- a desktop the game can hold fullscreen, and no other game controller.

Installation, paths and what a launch changes in the game folder are in
[README.md](README.md) and [integration.md](integration.md). Then:

```bash
uv sync --locked          # removes the Spire llm/train extras; restore with --extra llm
uv run python -m twwarhammer3 doctor
```

`play` refuses uncommitted changes in its source scope (`src/gameai`, `src/twwarhammer3`,
`configs/twwarhammer3`, `pyproject.toml`, `uv.lock`, `.python-version`) and stops before
its next episode if one changes, so commit first and draft in a git worktree while a job
runs. The game's realism preference must match `expect.realism` before play creates the
job. Since b42 setup also applies declared difficulty, unit scale and realism, then the
explicit AI modifier, and reads them back; difficulty is no longer a manual setup step.

## Declaring a scenario

Add an entry to `configs/twwarhammer3/scenarios.json`. The `setup.py` module docstring
lists every field and what reads it; `expect` makes the entry a benchmark, which must pin
the map, both factions and explicit rosters (lord first). Keep `name` equal to the key.
A variant copies its base and overrides what differs; dicts merge, other values replace:

```json
"my-cavalry-hard": {"base": "brt-cavalry-emp-assault", "name": "my-cavalry-hard",
                    "expect": {"ai_stats_modifier": "1.1"}}
```

Check a declaration without the game, then run the setup tests:

```bash
uv run python -c "
from twwarhammer3.battle import setup
c = {'scenario': 'my-cavalry-hard', 'episode_timeout': None, 'run_timeout': None,
     'start_timeout': 900, 'episodes': 3}
s = setup.load_scenario(c); setup.fill_timeouts(s, c); setup.validate_declaration(s, c)
print(len(setup.scenario_steps(s)), 'lobby steps')"
uv run pytest tests/twwarhammer3/test_wh3_setup.py
```

Commit the entry before playing it. Declare held-out variants (`split: held_out`) before
any tuning, and never use them to choose rosters, settings or controllers. The scenario
rules and readiness checks are in [benchmark.md](benchmark.md#scenarios). Current
[card gates](benchmark.md#from-a-candidate-to-a-scored-card) are proposals; a frozen
card's historical rule remains attached to its own evidence. Earlier integration,
expansion and M1 runs are recorded in the log.

## One launch

One `play` job is one launch, which is one instance. Scripted baselines cost nothing:

```bash
uv run python -m twwarhammer3 play --scenario brt-cavalry-emp-assault \
  --policy hold,attack_nearest,rush_nearest \
  --output runs/twwarhammer3/battle/my-cavalry-01-20261015
```

With a model controller, add its model, effort and the ledger cap:

```bash
uv run python -m twwarhammer3 play --scenario brt-cavalry-emp-assault \
  --policy attack_nearest,rush_nearest,llm_rules --model gpt-6-sol --effort low \
  --budget-usd 25 --show --output runs/twwarhammer3/battle/my-cavalry-sol-01-20261015
```

- **Rotation.** Each listed controller plays once (the first battle, then rematches) in
  an order shuffled from `--rotation-seed` (drawn and recorded when omitted). `--episodes
  N` repeats the list in shuffled blocks; repeats on one instance are correlated.
  `--delay-seconds 0,6,10` crosses every controller with each added age. Duplicate
  entries are refused, and `--episodes` must cover every controller/delay combination.
- **Several models in one job.** A model policy may carry its own model and effort,
  `NAME@MODEL` or `NAME@MODEL/EFFORT`; bare names use `--model` and `--effort`. For
  example `--policy llm_rules,llm_rules@gpt-6-luna,rush_nearest --model gpt-6-sol` pairs
  Sol and Luna within each launch. A name that resolves to another's model and effort
  (`llm_rules@gpt-6-sol` beside `llm_rules` on `--model gpt-6-sol`) is a duplicate. The
  report keeps the full names as controllers; the register records the base policy with
  the model and effort it played with. Launches pool in one report group only when their
  `--model` and `--effort` also match, even when every model policy carries a suffix.
- **More instances** are more launches, each with a new `--output` directory.
- **Timeouts** follow the declared timer: `--episode-timeout` defaults to the timer plus
  120 s, and `--run-timeout` to 8 hours or setup plus every episode if that is longer.
  `--start-timeout` (900 s) bounds the launch, the lobby setup and each battle load.
- **Models**: `llm`, `llm_rules` and `commander` need `--budget-usd`, which caps the
  cumulative WH3 ledger (`runs/twwarhammer3/llm-spend.jsonl`), earlier jobs included.
  Never reset or move it; on a fresh clone create it first (`touch` the file), since
  `play` refuses a missing ledger. `uv run python -m twwarhammer3 spend` prints its total. A
  job in a plan may carry a lower `--budget-usd` than the night's cap to leave room for the
  paid jobs after it; it then stops as `budget_exhausted` and a `keep_going` queue moves on.
  To stop a job from outside, signal only its Python process, never also the `uv` wrapper
  (`pkill -f` on the command line matches both and sends two SIGINTs). Each job saves the
  prompt of every model policy it rotates as `<base policy>_prompt.md` with its hash
  (`llm_rules@gpt-6-luna` uses `llm_rules_prompt.md`); a prompt difference is a controller
  difference.
- **Session settings**: keep `--observe-ms`, `--tick-ms` and `--interval-ms` at their
  defaults; different values make a separate comparison group. `--record-replay` is on
  by default and `--stills` adds presentation images ([reports.md](reports.md)).
  `--attach` is refused for benchmark scenarios, which need their own launch and checks.

Follow a job with `uv run python -m twwarhammer3 watch` (the live job's model inputs and
outputs) or `watch runs/twwarhammer3/battle/JOB --next`, which waits for the next episode
result, stall (`--stall-minutes`, default 2) or job end, prints it and exits. Afterwards,
`digest JOB` gives a table per episode and `digest JOB/episode-0000 --at 120` the full
decision nearest 120 s of battle time. Note a running job in [state.md](../state.md).

## Outside controllers

Name a class as `package.module:Class` anywhere in `--policy`. The committed
`twwarhammer3.battle.scripted:Hold` exercises the path:

```bash
uv run python -m twwarhammer3 play --scenario brt-cavalry-emp-assault \
  --policy hold,attack_nearest,twwarhammer3.battle.scripted:Hold \
  --output runs/twwarhammer3/battle/my-import-check-20261015
```

Keep a local experimental class under `runs/twwarhammer3/external-controllers/` and put
that directory on the path, for example
`PYTHONPATH=runs/twwarhammer3/external-controllers uv run python -m twwarhammer3 play ...
--policy my_controller:MyController`. Each trial's `card` records the class, its source
file and sha256, and the file's git revision if it lives in a repository; reports label
the controller with its hash prefix. Freeze its source, configuration and any imported
helpers for a comparison; the entry file's hash alone does not identify those dependencies.
Earlier examples are kept, untracked, in
`runs/twwarhammer3/capability-probes/external-controllers/`: `ExternalHold` (the b1
acceptance controller, with a `card`) and `ProbeFlight` (a flight diagnostic).

The interface (`battle/controllers.py` checks before launch that `decide`, `acknowledge`
and `metadata` exist):
- the constructor takes no arguments; every trial gets a new object;
- `decide(observation) -> list[dict]`: orders as `protocol.py` defines them. The
  observation is the public snapshot `engine/mailbox.py` describes, without
  `evaluation`, `final` and `setup`; with an added age it is the buffered basis;
- `acknowledge(ack, latency)`: `ack` is the observation's `orders` block (`request`,
  `based_on`, `applied_ms`, `results` with `index`, `unit`, `ok` and `queued` or
  `error`). After a refused batch it also carries `validation_error`, with every order
  marked not ok. `latency` has `think_s`, `roundtrip_s` and `delay_ms`;
- `metadata() -> dict`, recorded with each logged decision. The report reads
  `plan_age_s` (an asynchronous controller reports each plan's age when it adopts it)
  and `attempts` (model calls with `seconds`, `provider_processing_ms`, `actual_model`
  and `response_id`); `--show` displays `reason`;
- optional: `close()` at the end of the trial; `totals`, a dict with `usd`,
  `input_tokens` and `output_tokens`; `card`, a dict disclosing automation, memory and
  deployment (provider and endpoint, or machine and GPU).

Any exception from these ends the trial as `policy_failure` and stops the job. Rules:
carry no state between trials (module globals included); never read bridge files or
hidden game state; the battle keeps running while `decide` blocks, and observations
published meanwhile are skipped. This is a reviewed in-process interface, not a
sandbox. An outside controller's costs are self-reported through `totals`; only the
built-in model controllers draw on the WH3 ledger.

## Running a plan

`scripts/wh3_queue.py` runs a frozen list of `play` jobs one at a time; its docstring
has the format. Write the plan, commit everything, then:

```json
{"source_revision": "<git rev-parse HEAD>",
 "purpose": "two scripted launches of the cavalry assault",
 "jobs": [
   {"output": "runs/twwarhammer3/battle/my-cavalry-01-20261015",
    "args": ["--scenario", "brt-cavalry-emp-assault",
             "--policy", "hold,attack_nearest,rush_nearest", "--rotation-seed", "1"]},
   {"output": "runs/twwarhammer3/battle/my-cavalry-02-20261015",
    "args": ["--scenario", "brt-cavalry-emp-assault",
             "--policy", "hold,attack_nearest,rush_nearest", "--rotation-seed", "2"]}]}
```

```bash
uv run python scripts/wh3_queue.py runs/twwarhammer3/calibration/my-plan.json
```

It refuses to start unless HEAD is the plan's full revision with no uncommitted change
in play's source scope or the runner, no output exists and the plan has no state file.
It checks the source again before each job, stops at the first job that exits nonzero
(play does for any manifest status but `completed`) or whose rematch started with a
missing or changed unit or changed strength, loadout or resources (position
and bearing flags alone stay in the result), and never retries: continue with a new plan.
A night of single launches is one plan with `"keep_going": true` (a failed job is
recorded and the next starts; two in a row stop it) and `"start_before"` (no job starts
after that time). `my-plan-state.json` beside the plan holds the runner's pid, status
(running, completed, stopped, failed, interrupted), the current job and each exit code.
Exit codes: 0 completed or stopped, 1 failed or refused, 130 interrupted. Follow each job
with `watch JOB --next`.

The old G1 plans, completed C1/M1 plans and unstarted `swarm-sol-screens-plan.json` are
historical. The [release route](benchmark.md#route-to-the-first-release) and
[card gates](benchmark.md#from-a-candidate-to-a-scored-card) schedule no new runs.
For later authorized experiments, each small calibration plan should identify
the question, scenario/variant, controller, observable evidence, battle count, runtime
and spend allowance, decision rule and final committed revision. Start with targeted
cheap probes; a small frontier screen precedes any broad matched matrix. Shared measures
do not require a new scoring rule per scenario.

## Stopping

- **A job**: press Ctrl+C in its terminal, or send one SIGINT to its `uv run` or play
  process (`uv run` forwards it). Play records the running episode and the manifest as
  `interrupted`, appends the register row, and the supervisor closes the game. An
  interrupted trial is a failure in the report, never a loss.
- **A queue after its current battle**: create `my-plan-stop` beside the plan; the running
  job ends normally and the plan ends `stopped`.
- **A queue now**: send SIGINT or SIGTERM to the pid in the state file, or press Ctrl+C in
  its terminal. The running job gets one SIGINT, later jobs never start and the plan ends
  `interrupted`.

A job started with `&` from a non-interactive shell inherits an ignored SIGINT and cannot
be interrupted cleanly; run background jobs through `scripts/wh3_queue.py`, which handles
the signal itself. Never stop a job with SIGTERM or `kill -9`: Python exits without
cleanup, its manifest stays `running`, and the plain `watch` waits on it forever.

## The report

```bash
uv run python -m twwarhammer3 report runs/twwarhammer3/battle/my-cavalry-01-20261015 \
  runs/twwarhammer3/battle/my-cavalry-02-20261015 --output runs/twwarhammer3/reports/my-cavalry
```

It prints the text report and writes `my-cavalry.txt`, `.json` and the offline
`.html`. Before drawing conclusions, read the setup checks, start flags, missing pairs
and limitations: a matched formation alone does not show a matched caster's resources or
spell loadout. Everything else is in [reports.md](reports.md).

For the planned suite, pass the explicit input jobs for all scenarios to this same
command and use the canonical output stem `runs/twwarhammer3/reports/benchmark`.
Different scenarios and controller versions can share one HTML file while their
comparison conditions remain distinct. The overview and shared measures are planned;
no consolidated report was generated during preparation.

## Independent rerun acceptance (proposal)

This is the first reusable-path check, not a new admission rule or a run performed in
this review. Use one frozen card before attempting a suite. The proposer hands another
developer:

- the repository revision, card and scorer rule, required game build/content, settings,
  exact commands and one disclosed outside controller with its dependencies;
- a named reference cohort with the manifests, results and trace/recording evidence
  needed to recount outcomes, exclusions and selected signature examples;
- the expected counts, known manual setup steps and failure/stop instructions.

Local `runs/` paths alone are not that handoff. Provide the agreed evidence separately
from Git, without game assets or credentials; until it is accessible, independent
recounting remains unavailable. Existing logs are summaries, not replacements for it.

The recipient first rebuilds the reference counts and labels the selected signature
cases without reading the scorer's verdict. Disagreement is resolved against engine
endings and the written rule, not by editing expected numbers. Then, on their supported
installation, they run two fresh launches with one foil and the frozen outside reference
per launch, exercising a rematch in each. They inspect setup/start checks, observation
bases, acknowledgements, continuing battle time and recorded endings, and generate the
report without undocumented intervention. Every started or skipped trial is accounted for.

Passing requires a correct recount and a usable, documented execution/reset path.
Two launches do not re-estimate the reference win rate or prove general reset reliability;
unexpected behavior goes back to the relevant correctness check. Different trajectories
are allowed. Build differences require separate labels and a new comparability check.
After this path works, repeat it for the retained distinct cards; architectures, training
and a large model grid are not prerequisites.
