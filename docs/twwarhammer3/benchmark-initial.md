# Initial Empire mirror benchmark

Implementation of the [first-version follow-up](benchmark-implementation.md#first-version-follow-up-2026-11-02),
authorized by the owner's 2026-11-02 request to build it with a cheap Anthropic model.
Historical scenarios, chariot admission and results keep their earlier rules.

`emp-mirror-cavalry-v1` is the one development task. Its roster/settings rest on JUDGEMENT
`benchmark-implementation.md` Mirror profile. Its equal tactical-unit score and error
accounting rest on Simple condition score and No-retry scope and accounting there.
Neither the cavalry advantage nor controller strength has been established.

Owner, 2026-11-02: "Allow and record enemy AI toggles". Scenario version2 pins our initial
fire-at-will/skirmish/guard, records both armies' actual supported flags, and leaves enemy
control with the AI throughout startup. Enemy skirmish may be on. This supersedes the
original both-armies-off starter proposal after three failed setup attempts; those plans
and failures stay in their reports. Scoring remains mirror-v1, with no change to armies.
Each plan freezes its profile. Earlier plans without that field are checked against their
named Git revision, so later settings cannot silently change attribution of old attempts.

Owner, 2026-11-02, after pilot-r4's `hold` battle stood still (we attacked; the AI
defended and waited): scenario version3 gives the enemy a Great Cannon in place of its
fourth Swordsmen and makes the enemy the attacker; our army is unchanged. pilot-r4 was
stopped by its stop file after that battle. Whether a Great Cannon supports guard
(`defend`), which setup requires readable for every unit, is unknown until a pilot.

The owner's subsequent explicit confirmation in this implementation thread selects
version4: four enemy Swordsmen and a Great Cannon (replacing the enemy Crossbowmen),
with the AI attacking our unchanged army. This supersedes version3's different gun roster.
The Cannon's fire-at-will value may be either boolean; a missing readback is a setup error.
No Cannon skirmish flag is required. The current profile still needs its free pilot.

Owner follow-up, 2026-11-02: version5 adds two enemy Swordsmen, making six plus the
Great Cannon; role and our five units stay unchanged. This is an intended challenge
increase, not a measured balance claim. Version4's hold pilot is retained separately.

The engine's win/draw/loss comes first. At its first ending, the mod records each original
friendly unit's health bar (0.01 precision), headcount and wavering/routing/shattered/departed
flags. A departed unit must explicitly be no longer deployed or deploying; routing alone
does not mean departed. The evaluator averages five health fractions times their strongest
state penalty and multiplies by 100. It retains the raw values. Any missing/failed field
makes condition unavailable; it never cancels the engine ending. Late cleanup and model
errors remain visible. No terminal error is converted to a loss.

The supplied public task states the outcome/condition rule without prescribing tactics.
Controllers receive the current visibility-filtered interface, public roster, order
documentation and the existing `llm_rules` facts/memory. Evaluation, setup, final records,
screenshots and replays remain outside that input. No private enemy histories are needed.

The first model is `llm_rules@claude-haiku-5-5/low`, through Anthropic's Messages API;
model/effort/repeats rest on JUDGEMENT `battle/benchmark.py` Initial model screen. Its API
ID and inexpensive tier were rechecked in [Anthropic's model catalogue](https://platform.claude.com/docs/en/models/overview)
on 2026-11-02. Existing shared transport/other controllers keep their retry defaults.
For this profile: one transport attempt, no failed-response resend, parse repair or
partial salvage; subsequent decisions use new observations. At most 200 requests and
$2 per battle, layered over the existing cumulative ledger. No ledger is reset or replaced.
The initial screen's total ledger cap is $2, earlier WH3 Anthropic spend included; no
preparation calls. The shared key's $200 includes Spire too; check both ledgers first.
Limits rest on JUDGEMENT `benchmark-implementation.md` Starter limits and inputs.

The response cap is 16000 tokens. Each synchronous model request has a 60 s total
deadline as well as a socket/read timeout, enforced with WSL's main-thread alarm.
A timed-out request is charged conservatively as potentially billed, without a resend.
Record actual elapsed call times. Setup has a 900 s cap, each
battle 1320 wall seconds, and each job 2280 wall seconds. Engine timer: 1200 battle
seconds. Run one unpaused 1x battle per fresh launch, no added observation age or waits.

JUDGEMENT?: Startup handover — Codex, 2026-11-02: wait one existing engine tick before
enemy release and one before checking AI-owned readbacks. Immediate release failed two
pilots; this short setup interval changes when the first controller decision can begin.

Owner's subsequent "Allow and record enemy AI toggles" supersedes this attempted remedy.
It was tested only in pilot-r3 and did not produce the required enemy toggle state.
The active scenario (versions2 onward) never acquires enemy units, so uses no handover wait;
the helper's earlier modes remain for their recorded regression checks. Keep errors
from failed friendly application/readback. See the engine's
[unitcontroller documentation](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_unitcontroller.html):
issuing commands takes control, and release hands control back to the player or AI.
The third pilot still read enemy skirmish on after delayed release; its hypothesis is unproved.
Reference structure: [SWE-bench's planned-instance report](https://github.com/SWE-bench/SWE-bench/blob/02e7a74ffd0b/swebench/harness/reporting.py),
already in [references.md](../references.md): enumerate the plan, join evidence, keep missing attempts.

## Run and recount

Run from a supported Windows/WSL installation with Steam/WH3 and the repo's existing
runtime configured. `doctor --json` checks installation and build; tell the owner about
a build-pin warning and do not re-pin it automatically. Model jobs need the existing
Anthropic credential variables and `GAMEAI_ANTHROPIC_WORKSPACE_ID`. Never print credentials.
Commit source/configuration after `scripts/check.py` and review, before generating a plan.
The queue refuses a moving revision, a dirty source scope, an existing output or a reused plan.

```bash
uv run --locked python -m twwarhammer3 doctor --json
uv run --locked python -m twwarhammer3 spend --provider anthropic
uv run --locked python -m spire spend --provider anthropic
uv run --locked python -m twwarhammer3 benchmark plan runs/benchmark-initial-20261102/pilot.json
uv run --locked python scripts/wh3_queue.py runs/benchmark-initial-20261102/pilot.json
uv run --locked python -m twwarhammer3 benchmark report runs/benchmark-initial-20261102/pilot.json
```

The pilot plans hold, walk-nearest and run-nearest once each, three fresh launches, $0.
Stop and inspect any setup or measurement fault; a revised pilot gets a new plan/version
and retains the first evidence. After checking pilot measurements, create the model plan:

```bash
uv run --locked python -m twwarhammer3 benchmark plan runs/benchmark-initial-20261102/model.json --stage model --budget-usd 2
uv run --locked python scripts/wh3_queue.py runs/benchmark-initial-20261102/model.json
uv run --locked python -m twwarhammer3 benchmark report runs/benchmark-initial-20261102/model.json
```

Five fresh Haiku launches, no replacement attempts. Existing queue safety stops after two
consecutive job failures; remaining planned attempts appear as never started. The reports
(`PLAN.report.json`, `.txt`, `.html`) enumerate every attempt, engine outcomes, condition
inputs, errors and denominator. Error categories count recorded events and can describe
the same failure. Compare raw counts/condition values; no aggregate controller ranking or
reliable win-rate/generalisation claim from this exploratory screen. Generic report/stats
use this evaluator's engine outcomes for these jobs; the plan report is authoritative for
planned/never-started attempts. Source revision and controller prompts/cards stay in each job.
Started counts also use a matching first battle trace when result saving has not happened
or was interrupted. Truncated trace lines remain errors; foreign battle identities are refused.

Owner, 2026-11-02: the existing HTML visuals and benchmark scores are part of this benchmark.
`benchmark report` now uses that report's map/replay/decision viewer and adds every planned
attempt with its engine outcome and condition. The JSON/text plan report keeps its schema.
The earlier plain HTML bypassed the visual report; its legacy enemy-broken score was also
not this evaluator's condition. Both are corrected by the [visual integration](reports.md#initial-benchmark-visuals),
which gives the combined pilot/model command and offline checks. No new battles are needed
to build it; existing evidence supplies all eight replays. These presentation checks are
proposed, not a new agreement about model strength or winnability.

The canonical [main report](reports.md#main-report-and-retained-example) also retains the
earlier annotated Sol cavalry flank and its original comparison results, at the owner's
request, until a better replacement is agreed. Those keep their earlier scenario/score;
`initial-benchmark.html` remains the current mirror-only view.

## Measurement check

Owner originally agreed saved UI screenshots of rosters/settings, ending and health
within one percentage point. The later direction withdraws reliance on screenshots for
health: obtain it from the game. The mod already calls
[`unit:unary_hitpoints()`](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle_unit.html#function:unit:unary_hitpoints),
which returns regiment HP as a fraction of its initial HP. The saved per-unit `hp` is
rounded to two decimals; headcount and morale/departure flags are separate engine reads.
Check that binding and unit identity, missing reads and first-ending serialization;
hand-recompute condition and errors from the records. Offline checks retain routing,
recovery, accidental retries and private-input isolation. UI stills may check rosters,
settings and ending; no tooltip or numeric-health OCR is required. This checks recording
and arithmetic, not strength or the cavalry advantage. See [agreed checks](../agreed-checks.md).

Passed at `b1136e8`, scenario version5: 26 agreed component cases in the clean execution
checkout, the API getter/rounding/JSON/first-ending path independently challenged, and
three fresh scripted battles checked against rosters/settings, native unit records and
readable ending screens. The five Haiku attempts were also independently recounted;
645 response IDs each match one entry in the existing ledger. This verifies the reviewed
recording/arithmetic at that revision/profile, not task balance or controller strength.
Clock ratios are recorded evidence; their NTFS inputs were not independently recounted.

## First screen, 2026-11-02

All jobs used source `b1136e8`, profile version5, game build25961564, unpaused 1x.
Each controller started from a fresh launch. No retries or replacement battles.

| Controller | Planned / engine-completed | Wins / draws / losses | Condition values |
|---|---:|---:|---|
| Hold | 1 / 1 | 0 / 0 / 1 | 13.10 |
| Walk-nearest | 1 / 1 | 0 / 0 / 1 | 4.70 |
| Run-nearest | 1 / 1 | 0 / 0 / 1 | 4.40 |
| Haiku 5.5 low, `llm_rules` v22 | 5 / 5 | 0 / 0 / 5 | 28.40, 24.40, 5.50, 5.30, 24.30 |

Haiku: 646 attempted requests, 645 returned responses (one incomplete), 640 dispatched
decisions, zero invalid batches and zero terminal errors. Retain 28 individual engine
order refusals (26 routing, two unreachable), one malformed-reply forfeit and one timeout.
The timeout occurred during a call spanning the ending; its known engine loss remains.
The incomplete reply was not repaired or salvaged; later play used a new observation.
The report records two exchange-error events and one forfeit event; the latter describes
the same incomplete reply. Do not sum those as three independent failures.

Screen ledger debit: $0.5207731 = $0.5110642 known response usage + $0.0097089 conservative
estimate for the timed-out request. Actual provider billing of that request is unknown.
Cumulative WH3 ledger: $0.549347, Spire Anthropic ledger: $0, below the $2 screen cap and
the shared key allowance. The earlier $0.02 provider smoke is outside those ledgers.

Three scripted and 13 model presentation captures failed; those errors remain recorded.
Separate passive game-window captures supplied readable ending evidence for all eight
battles. None of these images supplies health to the evaluator or information to a policy.
The screen is exploratory: no reliable controller ranking, cavalry advantage, generalisation
or winnability claim. No scripted or human win is established on this version5 profile.

Plans, raw traces, reports and independent checks stay in ignored local evidence:
`runs/benchmark-initial-20261102/pilot-v5-r2*`, `model-v5*` and `review/`.
Earlier setup failures, the stopped version2 hold, the version4 hold win, and the CLI-only
rejection in `pilot-v5.json` remain separately attributed. The latter launched no game or
API request. Frozen execution and the path-only launchers prevented another session's
main-branch documentation commits from interrupting the queue; the original ledger was
used throughout. The normal main-checkout commands above remain the public run path.
