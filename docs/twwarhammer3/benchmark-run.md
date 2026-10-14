# Running a paired WH3 benchmark

Core live acceptance has passed: [benchmark-progress.md](benchmark-progress.md).
No scenario has passed calibration yet. Design: [benchmark.md](benchmark.md).
The owner stopped calibration after one paired launch and cleared the goal on
2026-10-14. The commands below document the interface and recorded configuration;
further experiments await a separate calibration discussion.

## Setup and commands

Use Windows/WSL2, Steam logged in, the pinned game and Windows Python at
`C:/Python313/python.exe`, with the paths/content in [integration.md](integration.md).
Run `uv sync --locked` and `uv run python -m twwarhammer3 doctor`. Source must be
committed; do not run another game controller. The game stays unpaused at 1x.

The frozen G1 candidate is `brt-cavalry-emp-assault` (AI modifier 1.0) and its
`-hard` variant (1.1): six Bretonnian cavalry units against eight Empire units on
the Taurox map, with the player attacking. Exact factions, cards, lord mount, anchor
hypotheses and content requirements are in `configs/twwarhammer3/scenarios.json`.
The 8000 funds cap leaves unused funds; army size is part of the tactical problem.
Settings are very-hard tactical AI, 1200 s timer, unit scale 0.75 and realism off.
The lobby explicitly sets funds, timer and AI modifier, then setup checks verify them
again in battle. Mismatches stop the job before scoring. Held-out variants stay out
of development tuning.

One paired launch with the frozen reference and both trivial baselines:

```bash
uv run python -m twwarhammer3 play --scenario brt-cavalry-emp-assault \
  --policy attack_nearest,rush_nearest,llm_rules --episodes 3 --rotation-seed 2026101401 \
  --model gpt-6-sol --effort low --budget-usd 25 --delay-seconds 0 \
  --start-timeout 900 --episode-timeout 1320 --run-timeout 5400 --show \
  --output runs/twwarhammer3/battle/my-cavalry-calibration-01
uv run python -m twwarhammer3 stats \
  --report runs/twwarhammer3/battle/my-cavalry-calibration-01 \
  --report-json runs/twwarhammer3/my-cavalry-calibration-report.json
```

Repeat independent launches using the declared schedule in
[calibration-plan.md](calibration-plan.md); a single launch cannot establish admission.
After a modifier is admitted, the same reference's G2 launch uses
`--policy llm_rules --episodes 3 --delay-seconds 0,6,10` and its declared G2 rotation
seed, with the same source, model, effort, timer and budget. G2 has not run yet.

Every new launch needs a new output directory. Pass multiple job directories to
`--report`. One launch is one instance; controllers rotate through rematches in a
recorded random order and start with fresh state. Repeated rematches are correlated.
Add `llm` or `commander` and `--budget-usd 25` to use the existing WH3 ledger; the cap
includes earlier jobs. Never reset or move the ledger.

`llm_rules` uses the same direct model, memory, actions, ledger and timing as `llm`, with
a separately saved rules-only prompt. It describes objectives and the interface without
the v15 instructions to stay in melee, advance together or wait behind infantry.
Use it when screening specialist scenarios; `llm` remains the tactical-prompt baseline.
For example, `--policy hold,attack_nearest,llm_rules --budget-usd 25`. Both names can
appear in a rotation; each prompt is saved and hashed separately. A prompt difference
is a controller difference, not evidence about model capability alone.

`rush_nearest` uses the same target selection and order persistence as `attack_nearest`,
but requests running. It adds no flanking, priorities or ability use. The cavalry
attacker's calibration compares both against the declared reference. Hold remains an
objective-failure control: staying idle can lose at the timer with both armies intact,
giving raw strength margin zero. See the pre-G1 amendment in
[calibration-plan.md](calibration-plan.md); outcomes and raw margins remain separate.

The default wall cap is 3900 s. Benchmarks require a finite game timer and a wall cap
at least 120 s longer. The process cap must cover setup, every trial and reset allowance.
Added age D supplies the newest buffered public snapshot at least D battle seconds old, retaining
its original sequence as the order basis. D=0 includes natural transport/engine delay.
The initial D seconds fill the buffer without decisions. Actual order feedback still
arrives. Delay arms remain separately labelled; total age is measured at issuance.
The buffer is populated between controller calls. A synchronous model call can leave
gaps, so actual age can exceed D. Reports give snapshot age at decision separately from
order age at issuance, preserving this distinction for the controlled-delay comparisons.

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

The lobby's initial enemy roster is public. Later enemy arrivals enter the known roster
only when visible; a previously seen enemy's death is reported only if the engine also
marks it visible then. Otherwise its last known state persists. Earlier b1/b2 sources
could expose hidden arrivals and later deaths; their acceptance/screening results must
not be pooled with this corrected observation contract.

## Records and interpretation

Every started trial is recorded, including interruptions. Only engine won/lost/draw
are gameplay outcomes; a timer ending is labelled `time_limit` in the report while
retaining its engine outcome explicitly, including a defender's win. The report labels
its existing win-rate measure "non-timer win rate" and also counts timer outcomes by
engine winner. A timeout win remains a legitimate result under the battle's rules;
the initial calibration separately requires decisive wins. Undecided failures stop
the launch; unplayed controllers
remain missing pairs. Different scenarios/builds/source revisions are not pooled.

The engine can reset remaining time to -1 at its result transition. b9 retains a
countdown sample on each engine tick and records the last sample/deadline in terminal
`timer` evidence. Timer classification uses expiry of that deadline; the actual
won/lost/draw is always the engine's result. This is an inference about the ending
cause, including uncertainty if combat and expiry coincide, not an authoritative
end-cause getter. The original b8 hold records have the old incorrect `engine_result`
label; their separate timer audit documents the correction without rewriting evidence.

Reports include failures and denominators, Wilson win intervals (omitted for correlated
repeats), and Student-t paired margin intervals across launch means. Active-strength
margin excludes routing/shattered men and does not weight unit value. Small samples
are exploratory; a null latency result only bounds effects the experiment could detect.
Each side's denominator includes every registered unit's initial men, including summons
and reinforcements that entered during battle. It is not strictly the starting roster's
survival fraction; the by-type totals preserve these additions for inspection.

Whole-job throughput includes setup, resets and failed jobs in its wall-time denominator.
It is unavailable for incomplete jobs or older records without total job timing. A
missing terrain grid rejects benchmark setup before decisions.

JSON retains all trials, objectives integrated on engine ticks, supplies, purchases by
type, protected-unit survival, order/plan age, decision rate, rejection reasons and costs.
Start displacements above 1 m or bearing changes above 10 degrees are flagged rather
than discarded. Starts also record friendly ability loadouts, initial strength/ammunition/
barriers and magic/supplies/tickets; differences are flagged even when positions match.
The JSON retains each comparison's deltas. Paired reports keep all valid trials in the
primary estimate and also give a sensitivity comparison excluding launches with any
flagged start. This secondary comparison is not a replacement for investigating a
changed roster or resources.
Inspect setup checks, start flags, missing pairs and the limitations. A matched formation
alone does not establish a matched caster's resources or spell loadout.

## Terrain, specialist interface and calibration candidates

The observation track is `obs-v3+terrain/act-v2/live-1x`. A deployment snapshot gives
32 m spaced samples of 16 m squares clear of pathfinding restrictions. This is a coarse
map, not a path planner: narrow crossings can be missed and buildings can later change.
After an unreachable move, the unit reports nearby destinations tested with its own
reachability query. The engine sends no replacement order; the controller must choose.

For specialist units, current/maximum barrier HP is separate from ordinary health.
Friendly leadership includes its UI fraction and largest current morale effect. This
can expose warnings such as losing battlefield control while all survivors are flying.
Flyers report flight-change availability/cooldown; a `flight` order requests take-off
(`flying: true`) or landing (`false`). Availability is checked again in the engine,
and later airborne state confirms the transition. Earlier tracks lack these fields
and this action; do not pool their trials with this contract.
Owned abilities include their cast range, effect radius and duration where the engine
provides them. These describe capabilities, not a suggested tactic. Rune ranges/durations
and nonzero Tzeentch barriers are live-verified, as are unit-targeted spells and their
mana/cooldown changes. Kairos's ground-targeted Pendulum spent magic and entered
cooldown after issuance in b7; the immediate acknowledgement snapshot still showed
the earlier resources. Visible units also expose walk/run speeds and airborne/grounded
state. b8 verified landing, a repeated landing request after the completed transition,
and take-off for both Kairos and Screamers, with cooldowns in their public observations.
Evidence and the limits of these checks are in [integration.md](integration.md).

The live b1 probes read the modifier as 1.1. Its stat previews say +10% attack, defence
and weapon damage and +8 leadership; a setting read-back alone does not measure each
unit's applied bonuses. Calibration explicitly tests 1.0 as well as 1.1.

Three additional candidates were frozen before their calibration: `dwf-sla-herald`
(1.0), `dwf-sla-herald-hard` (1.1), and `dwf-sla-herald-heldout-wastes` (1.0, Nurgle
wastes map). They replace Sigvald with the selectable Shadow Herald, preserving every
other unit. The first two are development variants; the third must stay out of tuning.
They remain candidates, not admitted benchmark scenarios. The frontend probe verified
the short timer as 1200 s; these three candidates explicitly set that timer. Use an
episode wall cap of at least 1320 s (for example `--episode-timeout 1500`).

Herald candidates use custom funds 30000 because the game refused their exact roster
under Default Funds. This only admits the declared units; no army is autogenerated.
