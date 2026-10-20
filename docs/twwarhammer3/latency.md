# WH3 latency program

The plan for the owner's WH3 notes of 2026-10-18 (evening, [owner-direction.md](../owner-direction.md)):
measure the gap between knowing a tactic and executing it in a battle that never waits, borrow
from robotics, and find harnesses and a fine-tuning path that close the gap. Research checks
remain proposals and gameplay findings unverified ([hard rule](../../AGENTS.md#verification-hard-rule)).
History and counts are in the [log](log.md#2026-10-18-latency-program-plan-only); local evidence
in `runs/twwarhammer3/calibration/latency-review-20261018/`.

## The question

When a model loses a [tactic card](tactic-cards.md), did it not know the tactic, choose wrongly
or act too late, and how much latency does the tactic tolerate? Wins at natural latency stay the
primary score. Battles never pause (AGENTS.md), so knowledge is measured offline and latency
tolerance with scripted references. Offline knowledge answers remain diagnostics;
they do not independently identify the cause of a live loss. The
[current benchmark definition](benchmark.md#the-decisions-the-benchmark-should-support)
separates those claims.

## What the evidence shows so far

From 30 recorded model battles (1-2 per model-mode, mostly the leaked 1.0 chariot card) and 70
offline probes per model-mode; all post hoc:
- Every model win came from a battle whose replies stated the tactic before contact (5 of 10;
  the others 0 of 17), but stating it did not predict winning: in the probes GLM-5.3 low planned
  cycle charging best (9 of 10) and pulled out most, and lost its one battle.
- Younger order ages went with winning (AUC 0.83, 3 + 9 battles), yet the fastest model lost;
  how often a chariot cycled ordered the battles best (AUC 0.96), how far it pulled out did not.
- Slow decisive calls were mostly retry loops (4 of 5 chariot cases: cut-off or invalid
  replies), and the register's order age omits calls that never applied.
- The prompt already states the last delay; telling a model 12 s instead of 1 s changed nothing
  detectable offline (10 paired tests).
- 2026-10-19 round ([log](log.md#2026-10-19-overnight-round-at-b36-c1-finished-p2-cells-p5a)):
  the witness won 4 of 4 at 2 s added age / 2 s decision interval, and 0 of 5 at 5 s / 5 s.
  GLM-5.3 low stated the tactic in 10 of 10 battles and won 1, with median order age 2.1 s.
  GLM ordered a pull-out in 37 of 43 engagements and re-attacked 12-14 of them before leaving
  melee, by whether a queued later-batch attack counts (the witness never): the 2026-10-19
  [second pass](log.md#2026-10-19-benchmark-verifiability-second-pass-harness-b39) read 12 of
  those re-attacks as decided at 2-29 m centre distance while the melee flag still read on
  (it clears at a median of about 30 m), an interface gap rather than a commitment failure,
  and read the witness's own slow-cell losses as a withdrawal stall ending near the map edge,
  so the tolerance curve reads as the recipe's. Unverified (10 battles, one night, one
  backend).
- 2026-10-19 evening ([b40 log](log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40)):
  witness v2 (one fixed 150 m withdrawal with the charge queued behind it) won 4 of 5 at
  5 s / 5 s and 4 of 5 at 8 s / 8 s, where v1 had won 2 of 8 and 0 of 4. This shows a
  more robust recipe at those configured settings, not a 13 s reaction deadline or a
  causal explanation of model losses. GLM-5.3 low on the amended prompt won 0 of 10 with
  fewer in-melee re-attacks and more damage dealt; withdrawal depth and re-planning are
  candidate explanations. Latency sensitivity of the card remains unestablished.

## Scoring: the battle never waits

Since b35, controller failures and truncations that end an in-battle episode count as losses
(forfeits) in `cards.outcome`; game/setup failures, interrupts and operator stops are excluded.
Recoverable provider or invalid-reply failures in `_drive` instead log a `forfeit` event,
send no new orders and request again. That event alone does not force a terminal loss:
`cards.outcome` scores the final episode status. Invalid order batches are recorded and sent
as no orders. Earlier engine actions continue while no replacement is issued. Since b35
only the game or the harness can truncate; none has in 80 chariot episodes, so the
[second pass](tactic-cards.md#second-pass-2026-10-19-evening-findings-and-the-version-2-decisions)
dropped the proposal to exclude truncations until one is seen.

If the battle ends during a blocking call, the loop checks for its result after the call
returns and does not send the late orders. It does not continuously read results inside
that call. These are current code semantics, not agreed live verification; the failed-call
paths remain unverified in the game. Compare failed decisions and terminal forfeits separately.

## Measurements

- **Witness timing sweeps** ($0 API, game time still costs): completed v1/v2 results are
  in the [card](tactic-cards.md#the-chariot-card-the-first-benchmark-card). Changing both
  age and interval compares operating conditions; it does not isolate either variable.
  More sweeps wait for a distinct question. A witness that loses with delay bounds that
  recipe, not every possible execution of the tactic.
- **Open-loop probes** (no game): recorded critical moments rendered by `LLMPolicy` and sent to
  each model; graded against the tactic. One round done (log, 2026-10-18). Retired as an
  instrument: its first-contact grade matched the live first-decision reading in count (18 of
  30 against 18 of 33; not checked per battle), and the live reading needs no probe (the
  ladder built on it was dropped by the
  [second pass](tactic-cards.md#second-pass-2026-10-19-evening-findings-and-the-version-2-decisions)).
- **Closed-loop round**: 10 launches per model-mode on the 1.1 card under the rule above, with
  pinned backends; at that n only gaps of about 0.6 in win rate are detectable (two-sided; about 0.5 one-sided).
- Report order issue age as p50/p90, achieved decision gaps and pending/failed calls.
  `cards.py`'s `info age` is median issue age plus half the mean decision gap: a proxy,
  not a measured time average, effective reaction delay or execution age. Unequal gaps
  matter, empty batches need not change standing orders, and a queued attack executes
  after issuance. Do not collapse these into one deadline or compare controllers only
  by this proxy. Calls still in flight at the ending have no issue age; list them separately.
- `--delay-seconds` supplies older state; `--interval-ms` waits after acknowledgement.
  Vary one at a time to study that intervention. Neither flag alone reproduces slower
  computation on fresh input or isolates a slow planner above a fresh-state executor.
  Filling the age buffer also postpones the first order. Isolating reactions after contact
  would need a shared opening and declared activation point; these are not implemented.
  Extra delay can show sensitivity, but cannot establish that faster serving would rescue
  a natural-latency loss. Battles always stay at 1x.

## Robotics framing

The [robotics research notes](robotics.md) develop these ideas into candidate comparisons,
with primary sources, limits of transfer and the current commander's constraints.

A unit is a module with its own low-level controller (the engine's movement, pathing and melee
targeting); routing can temporarily remove a module and death removes it permanently. Local
execution must react within the task's window. A higher-level planner can be slower if its
assignments remain useful and the executor handles the intervening changes. The measured
chariot timing cells motivate testing that separation; they do not set a universal safe rate.

| Work | Mechanism | WH3 use |
|---|---|---|
| [Helix](https://www.figure.ai/news/helix) (2025) | a 7-9 Hz planner over a 200 Hz policy, trained with the deployed latency gap | planner over executor; train on observations offset by order age |
| [Real-time chunking](https://arxiv.org/abs/2506.07339) (2025) | plan the next chunk while one runs, keep committed actions | latency as the swept variable |
| [DPT-Agent](https://arxiv.org/abs/2502.11882) (2025) | a 0.25 s state machine whose logic the slow model rewrites | model-written standing rules |
| [Shared Modular Policies](https://arxiv.org/abs/2007.04976) (2020) | one shared policy per actuator, transfer across bodies | cards that change the body (a lost unit, another army) |

Related live-clock benchmarks and concrete design lessons are in the
[current source comparison](benchmark.md#research-that-changes-the-design).
WH3 does not establish novelty merely by running during inference.

## Harnesses

| Rung | Controller | Status |
|---|---|---|
| 0 | `llm_rules`: one request in flight, the last-delay line | built, played |
| 1 | latency-aware rendering | proposal (minimal: recent order ages on the battle clock instead of one delay and wall time) |
| 2 | a per-decision deadline | proposal |
| 3 | model-written standing rules run at tick rate | proposal; disclosed automation |
| 4 | `commander` over `skills` | built, unplayed since v4 |
| 5 | a strong planner over a small fast executor model (candidate: Jev, owner 2026-10-19) | not built |

Rung 5 is the design the owner remembers: a "ChatGPT 6 Astra Pro" answer pasted on 2026-10-13
("a slow, thoughtful commander above fast, persistent controllers"), never committed; only
`commander` was built ([designs not built](controllers.md#designs-not-built-yet)). Before rungs
3-5 compare models, the commander prompt must drop "a withdrawal only delays defeat" and orders
need an origin tag so the signature credits the model, not the executor.

## Fine-tuning

Candidates on one card with a reserved variant: witness imitation, training with explicit
delay and intervening-action context, distillation, rejection sampling and preference methods.
Simply shifting labels against older observations can mislabel the state. The
[robotics notes](robotics.md#4-learn-micro-control-only-where-the-action-problem-warrants-it)
also consider small structured-state learners and bounded corrections to a reference.
Large online RL runs are costly at 1x; this does not rule out a bounded later experiment.
A student still needs a measured serving route and suitable data
([post-training](../posttraining.md#beyond-supervised-fine-tuning)). A serving probe on recorded
inputs can measure latency without a game, but cannot establish policy performance.

## Staged plan

| Stage | Question | n | Cost | Game h |
|---|---|---|---|---|
| P1 | foil and witness rates on fresh launches (`c1` plans 05-20, as evidence) | done 2026-10-19 | $0 | 3 |
| P2 | the tactic's latency tolerance (sweeps) | done: 5 cells, 19 launches; the curve was `SnapHitAndRun`'s: witness v2 (b40, 13 launches) won 4 of 5 at both 5/5 and 8/8 ([log](log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40)) | $0 | 5.5 |
| P3, P4 | pins hold; offline knowledge per mode | done | $2.19 | 0 |
| P5 | closed-loop wins under the rule, Kimi K3 low and high, GLM-5.3 low, Qwen3.6 none | P5a done (GLM, Qwen: 15); Kimi left | $1.78 so far | 2 |

A job's `--budget-usd` leaves room for one
timer-length battle and one maximum reservation (Kimi K3 about $2.45), so slow battles do not
drop out as budget stops.

## Owner decisions

1. "The battle never waits": merged as b35 (owner, 2026-10-19).
2. `c1` finished as evidence, then the
   [second-pass decisions](tactic-cards.md#second-pass-2026-10-19-evening-findings-and-the-version-2-decisions).
   Recommended.
3. One pinned backend per model for comparisons (checked: Kimi K3 on Sail Research, GLM-5.3 on
   Decart, Qwen3.6 on Parasail): merged as b36 under delegation (2026-10-19), for review.
4. At most $20 of OpenRouter credit for P5; more OpenAI cap only if gpt-6.1-sol stays the
   reference.
5. A fine-tuning host and its funding.
