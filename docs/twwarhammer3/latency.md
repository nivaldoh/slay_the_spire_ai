# WH3 latency program

A plan, drafted 2026-10-18 (evening) while the owner was away, from the owner's WH3 notes of
that evening ([owner-direction.md](../owner-direction.md)): measure the gap between knowing a
tactic and executing it in a battle that never waits, read an army as the detachable pieces of
a robot body, and find the harnesses and the fine-tuning path that close the gap. Nothing here
is agreed, so every number is unverified ([hard rule](../../AGENTS.md#verification-hard-rule))
and carries its n. It rests on a read-only review of code, traces and literature ($0, no
game); its scripts and outputs are local evidence in
`runs/twwarhammer3/calibration/latency-review-20261018/` (not in Git). It builds on the
[tactic cards](tactic-cards.md) and keeps the reporting rules of the owner's
[latency brief](WH3_latency_aware_benchmark_requirements.md).

## The question

For a model, mode and harness on a card, did a loss come from not knowing the tactic, from
choosing wrongly, or from acting too late, and how much latency does the tactic tolerate?
Wins at natural latency stay the primary score: the battle runs at 1x and never waits for a
reply (owner, 2026-10-18: "Real-life situations can't slow down if a model fails to respond on
time, and neither can our models here"). Pausing is not an option (AGENTS.md), so knowledge
is measured offline and latency tolerance with scripted references.

## What the recorded battles show

Thirty model battles (chariot card at modifier 1.0, n = 12; S1, 12 episodes from 10 launches;
expendables, n = 6) and 47 scripted ones, battle clock only. One or two battles per
model-mode, unpinned backends, the 1.0 chariot card leaked (`rush_nearest` won 1 of 2), no
model has played 1.1, and one grader graded knowledge after seeing outcomes.

- **Wins came only with the tactic stated.** Battles whose replies stated the whole tactic
  before first contact won 5 of 10 (5 of 11 under the scoring proposed below); the others won 0
  of 17, though 7 of those 17 gave three replies or fewer before contact, so their knowledge is
  unmeasured. Counting reasoning text as well: 5 of 15 against 0 of 12. Confounded with model
  strength. One of the five wins (Kimi K3 high on the chariot card) never ordered a move from a
  state that showed melee.
- **Median speed does not separate.** GLM-5.3 low had the lowest median order age of the 12
  chariot battles (2.7 s) and the highest decision rate (0.33/s), stated cycle charging at 5.3
  s and lost; gpt-6.1-sol low won at 3.0 s. Contact-to-pull-out times of the six chariot
  battles that stated the tactic: winners 3.6, 12.0 and 26.4 s, losers 2.7, 8.1 and 12.6 s
  (melee gaps under 6 s merged; Kimi K3 high's 26.4 s was a move ordered 27 m out, not from
  melee).
- **Tails and missing calls stand out**, though no tail measure separates wins from losses
  (n = 12). With one request in flight a call is always running when
  contact begins (by construction); all 7 contacts a model never saw fell inside calls of 16 s
  or more. The register's `delay_s` and the card board's order age leave out calls that never
  applied: 4 of the 12 chariot battles ended inside an unapplied call of 126-152 s, and Step 5
  high's row reads 7.2 s although its chariot got no order through a 52 s contact.
- **Slow decisive calls were mostly retry loops.** Of the five chariot losses decided by a
  slow call, four held failed attempts (16,000-token unparseable replies or invalid orders,
  then retries: `battle/llm.py:33-36`); only Luna high's was a slow valid reply. On S1 Kimi K3
  high's pull-out applied 42.6 s old, on expendables its pin 135.0 s old (one Chutes call).
- **Decision, not only latency.** For decisions whose snapshot showed the chariot in melee
  (chariot 1.0, one count, not re-checked): gpt-6.1-sol ordered a move in 13 of 20 and never
  attacked; Luna high 11 of 15 (right, but at a 7.2 s median age); Qwen3.6 none 0 of 13 (13
  attacks): it chose to grind; Luna low 6 of 40 (33 attacks), but its decisive loss came from
  refused moves.
- **Latency awareness exists and was rarely used.** The prompt gives the last batch's order
  age, the wall-clock reply time and "Expect a similar delay now" (`battle/llm.py:445-451`).
  4 of 30 battles reasoned about their own delay, all lost. Kimi K3 low wrote "~14s to
  impact" and sent nothing; that call applied 16.5 s after its snapshot, 7.5 s after contact.
  One pre-committed pull-out (Kimi K3 low) was refused because a move may not follow an attack
  in a queue (`protocol.py:87-88`).
- **Scripted references.** Contact-to-pull-out on the 1.1 card at 5 s added age:
  `SnapHitAndRun` 4.8 s (won 2 of 2), at model pace 6.9 s (2 of 4); `HitAndRun` 7.2 s (3 of 3),
  at model pace 14.9 s (0 of 2); `CycleCharge` 11.1 s (1 of 3). At 1.0, `CycleCharge` with
  dwells of about 11 s won 4 of 4, so 1.0 model results do not compare with 1.1 witnesses. The
  gated witness really decides 3.2 times a second, about 87% of them empty (n = 2; traces log
  every order change and at most one quiet decision a second). The start configuration may
  explain more than tempo (post hoc, 14 launches;
  [benchmark review](log.md#2026-10-18-latency-program-plan-only)).

## Measures (proposed)

Defined on these battles, so they are frozen first and judged only on new battles.

| Measure | Definition |
|---|---|
| win at natural latency | engine wins over scored launches per model, mode, harness and card, 95% Wilson interval, under the rule below |
| order age, censored | ack `applied_ms` minus the basis `time_ms` per batch, empty batches included; a call that never applied runs to the battle's end; p50, p90, max |
| reaction R = B + D + A | per critical event (chariot: melee onset in the 1 Hz replay): B, until a call starts from a state showing it; D, calls that saw it and did not respond; A, the response's order age. A response is an applied move that ends farther from the enemy; contacts ending in an enemy rout or the battle's end are reported apart |
| tactic stated | a reply (reasoning text apart) based at least 10 s before first contact states every part of the card's rubric; a frozen keyword screen, then a blind grader; undefined with three replies or fewer before contact |
| decisive-loss class | at the event of the largest own loss: knowledge, decision (saw it, chose otherwise), latency (split: slow valid reply, retry loop, backend), execution (refused or stuck moves) |
| latency tolerance L50 | from witness sweeps: the latency at which the witness wins half its battles |

The 3 s merge in `cards.py` sits on the replay recorder's 0.9/0.9/1.2 s frame period (moving
it to 3.01 s changes 4 of 28 counts), so any engagement measure fixes its merge off that
period first.

## Scoring: the battle never waits

Proposed: everything inside the controller is time passing. Provider errors after the declared
retries, timeouts, cut-off or invalid replies and controller exceptions are the controller's
loss, shown in their own column. Excluded and rerun, at most 20% of a cell: game, mailbox and
setup failures and operator caps (ledger, credit). Today `cards.outcome` (`cards.py:39-48`)
excludes provider errors and harness exceptions, and the two Score texts in tactic-cards.md
disagree. Re-scored this way, the 32 small-scenario model battles (the 30 above plus S4's 2)
change one result (Kimi K3 low on S1: a failed response under code that predated the
failed-response resends of `e0d7404`).

Code it would need, after `c1`: a failed decision becomes an empty batch and the controller is
asked again from the newest state (today it ends the episode); the engine result is read even
while a call blocks (a failure after the battle ended can replace the result; not seen in the 8
failure episodes); the episode deadline on the battle clock instead of wall time
(`play.py:423-439`), with no per-decision deadline (that is rung 2). A pinned backend narrows
the "variable latency" the owner wants scored, so the scored route is part of the controller
and disclosed.

## Experiments that separate knowing from executing

- **Witness latency sweeps ($0, game time).** `SnapHitAndRun` on the 1.1 card with added age
  equal to the decision interval at 2, 3.5, 5 and 8 s, plus off-diagonal cells (0 s age with a
  5 s interval; 5 s age with none exists), 5 launches a cell. Existing `--delay-seconds` and
  `--interval-ms` suffice. Gives L50; report cells by start configuration (it cannot be set; the
  review's scripts recover it from first observations).
- **Trace-driven witness W(model).** The witness holds each decision for the call lengths a
  model actually took, in order: the tactic executed perfectly at that model's latency. Needs a
  battle-clock hold (in `play.py` or an [outside
  controller](benchmark-run.md#outside-controllers)); run it on the call sequences of the model
  round, not on 1.0 data.
- **Open-loop probes (no game).** Re-send recorded prompts from critical moments (battle start,
  within 6 s of contact, 80 m out after leaving) to each model and grade the orders against the
  tactic: knowledge K without latency, as robot learning separates offline from closed-loop
  evaluation. Replaying `LLMPolicy` with a fake transport reproduced 915 of 915 recorded model
  prompts byte for byte, so witness moments can be rendered by driving `LLMPolicy` with the
  witness's recorded orders and acknowledgements, notes and history blanked (they would leak
  plans). Moments: 210 engagements in 42 battles; a frozen draw of 70 (battle start, in melee
  within 6 s of contact, 80 m out after leaving), graded automatically: in melee, an unqueued
  move to at least 80 m is right, but a held attack with a stated dwell is its own class (most
  moments are within 1 s of contact, so plain grading would score the snap rule, not cycle
  charging); out, an attack is right. A paired variant states a 1 s or a 12 s last delay.
- **Reading a model-mode.** K low: knowledge-bound. K high, W(model) low: the tactic does not
  fit that latency. K and W(model) high, closed-loop wins E low: an execution gap beyond
  latency. At 10 launches a cell (5 for W(model)) these are screens, not rankings: at 10 a
  side a gap is found with 80% power only from 0 to 0.59 or from 0.2 to 0.88.

## Robotics framing

A unit is a module with its own fixed low-level controller (the engine's formation movement,
pathing and melee targeting); the model is the brain; casualties are actuator loss, a rout a
temporary loss of control, morale a shared body state, and `commander` over `skills` brain
over spinal cord. It breaks where units are mechanically uncoupled (closer to a supervised
fleet), where the engine overrides the brain (routing units refuse orders), and where the
brain unit is never replaced: the commander flag never moved in 469 traced episodes, 79 of
them with its unit at 0 men. Robot hierarchies keep the slow loop far faster than the reaction
window it serves; WH3 models plan at 3-7 s medians with tails past 30 s, which is what makes the
gap measurable here.

| Work | Mechanism | WH3 element |
|---|---|---|
| [Helix](https://www.figure.ai/news/helix) (Figure, 2025) | a 7B planner at 7-9 Hz runs asynchronously over an 80M policy at 200 Hz; training offsets their inputs by the deployed latency gap | planner over executor (rung 5); a student trained on observations offset by the measured order age |
| [Real-time chunking](https://arxiv.org/abs/2506.07339) (2025), [at training time](https://arxiv.org/abs/2512.05964) | plan the next chunk while one executes, freezing the actions already committed; synchronous inference degrades with delay | delay as the swept variable; a committed-prefix line in the prompt; delay-randomized fine-tuning |
| [Hierarchical Language Agent](https://arxiv.org/abs/2312.15224) (AAMAS 2024) | slow GPT-3.5, fast Llama2-13B and a scripted executor run concurrently; 1.07 s per macro action against 4.16 s slow-only | rung 5 with a small fast model |
| [DPT-Agent](https://arxiv.org/abs/2502.11882) (ACL 2025) | a state machine acts every 0.25 s; the slow model rewrites its logic | model-written standing rules at tick rate (rung 3) |
| [Sheridan 1984](https://ntrs.nasa.gov/citations/19850006202); Ferrell's move-and-wait via [Starr 1982](https://ntrs.nasa.gov/citations/19820026196) | predictor displays reduced completion times "by 50-150 percent" at 1-3 s delays; delayed operators move cautiously, then wait | a dead-reckoned "state at arrival" line (rung 1); Kimi K3 low's empty reply reads as move-and-wait (interpretation) |
| [Shared Modular Policies](https://arxiv.org/abs/2007.04976) (ICML 2020); [Cully et al.](https://arxiv.org/abs/1407.3501) (Nature 2015) | one shared policy per actuator, messages both ways, transfer across bodies; recovery from damage in under two minutes | cards that change the body: a lost limb, another army composition |

Closest language-model benchmarks: [Real-Time Reasoning Gym](https://arxiv.org/abs/2511.04898)
counts time in tokens; [The World Won't Wait](https://arxiv.org/abs/2610.20665) (2026) runs a
live clock: a frontier model beat a fast action model in 5 of 6 game types when paused, and
live it scored 1.51 against the fast model's 13.51 (18.97 s against 0.52 s response latency).
Neither admits tasks by tactic or has a latency-matched scripted reference. Body cards come
after the first card's admission: a lost limb (the unit controller's documented `kill` and
`morale_behavior_rout` are unprobed), morphology transfer and a scale ladder.

## Harness ladder

| Rung | Controller | Status | Isolates |
|---|---|---|---|
| 0 | `llm_rules`: one request in flight, the last-delay line | built (v20), played | baseline |
| 1 | latency-aware `llm_rules` (prompt and rendering only) | proposal | latency awareness |
| 2 | a deadline: drop a call after T s of battle time and ask again from the newest state | proposal | retry-loop losses |
| 3 | model-written standing rules run at tick rate ("in melee over N s: move to X") | proposal | knowledge with code timing; disclosed automation |
| 4 | `commander` over `skills` | built (v7), unplayed since v4 | two timescales, one model |
| 5 | a strong planner every 15-30 s or on events, a small fast model turning plans into skill assignments, skills at 3-4 Hz | not built | planner and executor models |
| 6 | k staggered calls in flight, same model | not built | decision interval at a fixed order age |

**Rung 1**, specified as a separate controller `llm_latency` v1 on the unchanged rules prompt
(full text in the readiness spec), replaces the timing line with: the last batch's order age
and call time on the battle clock (the wall-clock "you took" goes); the last 10 order ages
(median, 90th percentile, longest); the snapshot's age and when the reply should apply at the
median, 90th-percentile and longest call; a straight-line projection to contact for visible
units (a disclosed rendering aid: contact-time error a median 0.8 s over 25 recorded contacts,
mostly within 5 s ahead); public events since the last decision; and the cost of an empty
reply. At Kimi K3 low's 77 s decision it would have projected contact at 85.8 s (actual 86.0 s).
It needs about 130 lines in `battle/llm.py`, the decision clock passed to the policy, and a
reader thread in `play.py` (during a blocking call the harness reads no observations: 13
snapshots went unread in that call), which also makes added age exact for slow controllers
(today it compounds; no recorded job is affected). The fresh-state retry belongs to rung 2.
Rung 0's golden prompts stay byte-identical. At least 4 of about 530 chariot decisions
mention their own delay (all GLM-5.3, two battles).

**The planner-executor design (rung 5) the owner remembers.** It was proposed, never built. The
owner's modding guide (`001d1ce:docs/twwarhammer3/guide.txt:309`, deleted in `c916e6c`) already
allowed "a later commander mode" with built-in planners executing. On 2026-10-13 (19:03 UTC)
the owner pasted a "ChatGPT 6 Astra Pro" design (never committed;
[controllers.md](controllers.md#designs-not-built-yet) paraphrases it): "a slow, thoughtful
commander above fast, persistent controllers", "optional tactical specialists ... A genuinely
fast local model can run frequently; another five-second API model cannot serve as an emergency
reflex", advising one commander first; the first row of its table,
[SwarmBrain](https://arxiv.org/abs/2401.17749) (an LLM over a condition-response state
machine), is the only swarm-named hierarchical design in the WH3 sources. What was built is
[`commander`](controllers.md#commander-asynchronous-api-model-over-the-skills) (`d2bf74a`): one
model, one plan in flight, scripted skills underneath; 24 register rows (13 won, on scenarios
that do not pool). The specialists and a learned local policy stayed designs 4 and 7 in
controllers.md; no two-model controller exists on any branch or tag. The Spire survey's
"multi-agent swarms" ([section
7](../spire/approaches.md#7-multi-agent-systems-and-swarms-breadth-helps-depth-does-not))
covered several model calls per decision (voting, planner/executor splits, fast and strategic
tiers) and found that splitting a sequential decision hurt; which design the owner recalls is
unknown.

Before rungs 3-6 count: the commander prompt drops "a withdrawal only delays defeat"
(`commander_prompt.md:26`), skills gain a pull-out (`skills.py:195` has none, so a cycle costs
two plans), every order carries its origin (model, executor, rule) so the signature credits the
right layer, async order age is measured from the model's snapshot rather than the executor's
tick, agentic harnesses get a sandbox (the bridge on `/mnt/c` holds the hidden evaluation and a
writable `orders.json`), and the owner rules whether tactic-specific skills are allowed.

## Fine-tuning path

Compared on one card, one serving route and one held-out variant:

| Method | Labels | Caveat |
|---|---|---|
| SFT from the witness | about 11,650 witness decisions in winning chariot battles (3,700 logged; 3,565 on the leaked 1.0 card), about 87% empty | needs a prompt renderer for scripted decisions; imbalanced |
| SFT on delay-shifted labels ([DIDA](https://arxiv.org/abs/2205.05569)) | each order paired with the state L s earlier plus the orders sent since, L from measured ages; DIDA then relabels states the delayed learner visits | needs an undelayed (0 s) witness |
| distillation | 78 unexported exchanges from Kimi K3 chariot wins | 1.0 card only |
| DAgger | the witness labels states the student visits | needs the student playing |
| KTO or DPO | witness against foil at pull-out states | the witness's preference, not outcomes |
| rejection sampling | the student's own wins | needs wins first |
| online RL | engine wins | published agent RL used about 19,200 episodes a run: 240-480 nights here |

Data today: 658 usable OpenRouter rows in `trace-v2-20261017`, 459 unexported exchanges from
2026-10-18 (229 on the chariot card), none on 1.1, no log-probabilities
([gaps](../posttraining.md#beyond-supervised-fine-tuning)). Hosts: Tinker trains
Qwen3.6-35B-A3B LoRA and serves it through a beta OpenAI-compatible endpoint; CoreWeave/W&B
serves rank-16 LoRA on it at $0.25/$1.25 per million tokens; neither publishes latency, which
decides cards. The local RTX 3060 (12 GB) cannot hold the student and shares the GPU with WH3.
The transport speaks only the Responses API, so a chat-completions path, a provider entry and
a ledger are needed; base and fine-tune must share host and decoding. Stages: F0, the serving
latency of 50 recorded prompts per route (under $1, no game); F1, witness demonstrations at
the student's pace plus a held-out variant ($0, 6-7 game hours); F2, SFT; F3, base against
SFT, 20 launches each plus 10 held-out; F4, DAgger, rejection sampling and KTO. Estimate
$15-35 on host accounts (outside the OpenRouter credit) and 25-34 game hours.

## Staged plan

| Stage | Question | Decision it feeds | Needs | n | OpenRouter | Game h |
|---|---|---|---|---|---|---|
| P1 | what the frozen chariot rule gives on fresh launches | foil and witness rates and start configurations for card version 2 (not admission) | nothing (current HEAD) | 16 plans | $0 | 2.7 |
| P2 | what latency the tactic tolerates (L50) | whether the card discriminates at 3-8 s | nothing | 25 launches | $0 | about 4 |
| P3 | do backend pins hold through the Responses API | pins for P5 | `provider.only` and `order`, no fallbacks, per model in `providers.ROUTES` | 3 calls x 4 cells | about $0.03 | 0 |
| P4 | does each mode know the step, offline (K) | knowledge-bound modes, before P5 | probe script | 130 prompts x 4 modes (70 moments, 60 delay variants) | about $1.7 | 0 |
| P5 | closed-loop wins on 1.1 under "the battle never waits" (E) | the first model result | the scoring change; pins | 10 launches x Kimi K3 low, high, GLM-5.3 low, Qwen3.6 none | $12-20 | 6-8 |
| P6 | does rung 1 help | rung 1 as default or arm | `llm_latency` (harness b35) | 20 within-launch pairs, GLM-5.3 low | $4-10 | 4-5 |
| P7 | W(model) from P5's call sequences | latency-bound or execution-bound per model | a battle-clock hold | 5 x 4 | $0 | 3 |

Nothing runs while the owner is away: P1 and P2 are game runs and wait for a go-ahead.
OpenRouter $18-32 in all. Proposed (decision 4): paid stages stop at $20; P6 would be cut
first, which defers the latency-awareness note. P4's four modes are those P5 can afford; the
others are left out for cut-offs (GLM-5.3 high, Step 5), invalid orders (Qwen3.6 medium) and
cost (Step 5 about $8.6 at 70 prompts a mode). gpt-6.1-sol low and Luna wait on decision 4
(OpenAI $51.43 of $52); with the cap raised they join P5. Before each paid stage read
`/api/v1/credits` (the ledgers missed $2.69 of account use). A job's `--budget-usd` is the WH3
ledger total ($6.69 now; the shared $50 allowance less Spire's $0.25 leaves $43.06; the
account's $50.38 is a separate limit) plus one timer-length battle and one maximum reservation
(Kimi K3 about +$2.45), so that slow battles do not stop on the budget and drop out as
exclusions. Game hours P1-P7: about 20-23, two or three nights; fine-tuning adds 25-34.

## Owner decisions

1. **"The battle never waits"** as the scoring rule above. Recommended.
2. **`c1`**: finish it at the current HEAD as evidence (foil and witness rates on fresh
   launches, start configurations recovered from first observations) without reading its
   verdict as admission, then fix the card into a version 2 (launch counting, start
   configuration, commit-and-grind and charge-through foils, a signature counted from melee
   snapshots) with a new round. P5 then runs on an unadmitted card and its results stay
   provisional. Recommended; this revises the session review's advice not to resume `c1`.
3. **The scored route**: one pinned backend per model, named in the controller card, for
   comparisons; natural routing later as a deployment arm. Proposed pins: Kimi K3 (both
   modes, since `ROUTES` is keyed by model) on Sail Research, 0 failures in 100-108
   attempts; GLM-5.3 low on Decart with DeepInfra as fallback (weak evidence); Qwen3.6 none
   on Parasail, 8 of 121 failures, priced exactly at the ceiling. A pin in `providers.ROUTES`
   also pins Spire's runs of the same model. Recommended.
4. **Budget**: at most $20 of OpenRouter credit for P3-P6; about $5 more OpenAI cap only if
   gpt-6.1-sol (the only model to win both chariot 1.0 and S1, one battle each) stays the
   reference.
5. **Fine-tuning host and funding** (with the teacher question in [state.md](../state.md)).

## What is unverified

Everything: no check is agreed; 1-2 battles per model-mode; knowledge graded by one grader
after outcomes; thresholds read off the same battles; the 1.0 card leaked and no model has
played 1.1; unpinned backends make latency partly routing luck; wall-clock times before 18:01
UTC on 2026-10-18 are distorted. Unprobed: moves queued after attacks, damage injection, the
serving latency of any fine-tune. The robot analogy is an interpretation.
