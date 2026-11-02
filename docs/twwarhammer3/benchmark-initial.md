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
The active scenario version2 never acquires enemy units, so uses no handover wait;
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

## Measurement check

Owner agreed 2026-11-02 in the implementation thread: saved UI screenshots for rosters,
settings, engine ending and displayed unit health within 1 percentage point; offline
routing/recovery, missing-read and accidental-retry cases. Hand-recompute scores and
failure counts from saved records; change private fields and require identical inputs.
This establishes recording/arithmetic, not strength or the cavalry advantage. A green
component suite alone is insufficient. See [agreed checks](../agreed-checks.md).

Current status: implemented at `b5ecab8`, with readback/handover fixes at `ae9a09b` and
`52eab85`; latest full gate 2587 passed, 43 skipped, independent review found no findings.
Three starter pilots each stopped on setup: first stale own readback, then two enemy
skirmish readbacks. All three plans/results are retained (no model calls or engine ending).
Owner-selected friendly-only toggles are built, with new component regressions; version2
pilot and live measurements remain pending.
No live correctness or strength claim yet. Evidence/card:
`runs/benchmark-initial-20261102/`.
