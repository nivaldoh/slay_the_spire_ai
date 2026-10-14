# Running a paired WH3 benchmark

Live acceptance is in progress: [benchmark-progress.md](benchmark-progress.md).
No scenario has passed calibration yet. Design: [benchmark.md](benchmark.md).

## Setup and commands

Use Windows/WSL2, Steam logged in, the pinned game and Windows Python at
`C:/Python313/python.exe`, with the paths/content in [integration.md](integration.md).
Run `uv sync --locked` and `uv run python -m twwarhammer3 doctor`. Source must be
committed; do not run another game controller. The game stays unpaused at 1x.

`dwf-sla-taurox` freezes a 12-v-12 development draw, including its map, factions,
armies, DLC requirements and Runelord substitution. It expects very hard, large funds,
3600 s, unit scale 0.75, realism off, the player defending and AI stats preference 1.1.
These settings are checked, not automatically changed. The AI slider's relationship
to the preference is still being probed. Setup mismatches stop the job before scoring.

```bash
uv run python -m twwarhammer3 play --scenario dwf-sla-taurox \
  --policy hold,attack_nearest,skills --rotation-seed 101 \
  --output runs/twwarhammer3/battle/bench-calibration-01
uv run python -m twwarhammer3 play --scenario dwf-sla-taurox \
  --policy skills --delay-seconds 0,6,10 --rotation-seed 102 \
  --output runs/twwarhammer3/battle/bench-delay-01
uv run python -m twwarhammer3 stats \
  --report runs/twwarhammer3/battle/bench-calibration-01 \
  --report-json runs/twwarhammer3/bench-calibration-report.json
```

Every new launch needs a new output directory. Pass multiple job directories to
`--report`. One launch is one instance; controllers rotate through rematches in a
recorded random order and start with fresh state. Repeated rematches are correlated.
Add `llm` or `commander` and `--budget-usd 25` to use the existing WH3 ledger; the cap
includes earlier jobs. Never reset or move the ledger.

The default wall cap is 3900 s. Benchmarks require a finite game timer and a wall cap
at least 120 s longer. The process cap must cover setup, every trial and reset allowance.
Added age D supplies the newest public snapshot at least D battle seconds old, retaining
its original sequence as the order basis. D=0 includes natural transport/engine delay.
The initial D seconds fill the buffer without decisions. Actual order feedback still
arrives. Delay arms remain separately labelled; total age is measured at issuance.

## Outside controllers

Use `--policy package.module:Controller` for a class importable in the environment.
Its no-argument constructor initializes fresh episode state. It implements
`decide(observation) -> orders`, `acknowledge(ack, latency)` and `metadata() -> dict`;
optional `close()` releases resources and `totals` reports calls/tokens/USD. A `card`
dict should disclose automation, within-trial memory and deployment. Async controllers
report adopted plan ages in metadata. The harness records class/source hash/revision.

No state may carry between episodes. Do not read bridge files or hidden game state.
This is a reviewed in-process interface, not an adversarial security sandbox. Inputs
contain full friendlies, visible enemies and public roster/objectives; player equivalence
is unverified. `evaluation`, `final` and `setup` are stripped before controller calls.
Order refusals reach `acknowledge`. Engine acceptance means issued/queued, not effect.

## Records and interpretation

Every started trial is recorded, including interruptions. Only engine won/lost/draw
are gameplay outcomes; a timer ending is labelled `time_limit` in the report while
retaining its engine outcome. Undecided failures stop the launch; unplayed controllers
remain missing pairs. Different scenarios/builds/source revisions are not pooled.

Reports include failures and denominators, Wilson win intervals (omitted for correlated
repeats), and Student-t paired margin intervals across launch means. Active-strength
margin excludes routing/shattered men and does not weight unit value. Small samples
are exploratory; a null latency result only bounds effects the experiment could detect.

JSON retains all trials, objectives integrated on engine ticks, supplies, purchases by
type, protected-unit survival, order/plan age, decision rate, rejection reasons and costs.
Start displacements above 1 m or bearing changes above 10 degrees are flagged rather
than discarded. Inspect setup checks, start flags, missing pairs and the limitations.
