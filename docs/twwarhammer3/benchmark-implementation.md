# WH3 benchmark implementation

How we get from the [definition](benchmark.md) to a working benchmark: the phases, the open questions, the checks, what the code does today, and the earlier plans. This page changes as the work moves; the definition should not. Status on 2026-10-23: planning only. The owner asked for the definition and plan, not for code changes, game runs or spending.

## Milestones

The first milestone is a working evaluation of one matchup in both roles, with a checked report and commands anyone can rerun. A reusable release also freezes the reference controllers, makes the evidence accessible, lists its limits, and records a recount and a rerun by someone other than the author. A pilot alone gives neither a reliable win rate nor results on other armies or maps. Two roles rest on JUDGEMENT `benchmark.md` Role coverage.

## Phases

Each phase ends with something the owner can review. A new correctness check needs the owner's agreement.

| Phase | Work | Done when |
|---|---|---|
| 1. Settle the battle | The owner answers the [interview](#owner-interview-one-land-battle); review the marked roster, settings, roles, score and comparison; settle the outcome edge cases and the measurement and check definitions | One resolved battle profile and outcome table, with no inherited settings or unnamed exclusions |
| 2. Check what can be measured | Read representative existing battles; draft an example report with the missing fields marked; probe only the missing engine readbacks, with free scripts | Comparing the game UI with the engine readings shows which health, leadership and state histories can actually be recorded |
| 3. Build the minimum | Version the evaluator; record the agreed histories; use one outcome calculation in every benchmark reader; align the scenario text and prompt with the definition | Focused regressions and the agreed live checks pass at recorded sources; c1 and the raw results are unchanged |
| 4. Free pilot | Run the battle in both roles with the simple scripts; check setup, endings, the clock, recordings and cleanup | Complete evidence and a recounted report; no win-rate claim |
| 5. Compare frozen controllers | Fix the contrast, sample plan and budget; collect and report every planned battle; play the reserved map only after freezing | Counts, uncertainty, timing, cost and replay examples answer the question, or show that it can't be answered yet |
| 6. Make it reusable | Commands, configuration, versions and accessible non-proprietary evidence; someone else recounts and follows the runbook | A recorded recount and rerun on the supported installation; other machines remain untested |

JUDGEMENT: Pilot size — Codex, 2026-10-23: propose one fresh launch for each of the three
simple scripts in each role, six battles total. More repeats add rate evidence and cost;
this bounded pilot establishes feasibility only and stops on a setup/measurement fault.

The pilot rests on JUDGEMENT `benchmark.md` Starter settings and Role coverage, and on Pilot size above. Its exact commands and time cap come after those choices and after the checks are agreed. Phases 2 and 4 need no model calls. A paid study needs its own ledger budget; the old chariot and Empire estimates don't authorize one.

Build on what exists: the mod and mailbox, the play loop, the reports and the outside-controller boundary. Before new jobs, remove the contact-only objective from the new scenario and its prompt, and make every benchmark view use the new evaluator. Today's `scoring: contact`, `cards.outcome` and report denominators don't implement the definition ([current code](#what-the-current-code-reports)). Don't rewrite old scenario evidence or rescore old cards. No general reward framework, new controller architecture or exhaustive event detector is needed.

## Owner interview: one Land Battle

The owner asked for these questions on 2026-10-23, all at once, to settle the definition of one Land Battle; other battle types come later. Answer by number, here or in conversation; a short answer or "undecided" is enough. The options are not defaults, and the JUDGEMENT proposals in the definition stay open until answered.

Already decided: small mixed armies first; the engine picks the winner, timer wins included; battles run unpaused at 1x. The aim (owner, 2026-10-23): compare models on the knowledge needed to win **and** on acting well despite API latency. Reading health or a routing flag is objective; how much it is worth in a score is a separate choice. A win alone doesn't show which knowledge the model used.

### A. What the comparison should tell us

1. **What decision should the result help you make?** Which model plays this battle best as served today, which has better tactical knowledge, or which best balances winning against time and API cost? Rank them if several matter. Should diagnosing failures, or tracking improvement after training, shape this first definition, or wait?

2. **What are we ranking?** Models swapped into one shared prompt, memory, action interface and budget; each model with its own best-tuned controller; or both, reported separately? The first measures model differences within one interface; the second measures whole systems, helpers and tuning included. Neither isolates a model's intrinsic skill.

3. **What does "one Land Battle" mean?** One fixed matchup, map, role and starting deployment repeated across models, or a scoring contract meant for later matchups, starting with one example? Should the second role and the reserved map wait until the single battle works?

4. **What should the score be?** The engine result plus separate health, morale, knowledge and timing measures; a ranking where victory always comes first and other measures break ties; or one number with explicit weights? Must every win outrank every loss? For example, does a costly win beat a loss that leaves the enemy nearly destroyed? One battle gives one score; comparing models reliably still needs repeated battles.

### B. The battle and the decisions it should require

5. **Which knowledge should this battle let a model show?** Pick the essentials: unit matchups and target priority; protecting ranged units and their lines of fire; positioning and flanking; charging and disengaging; leadership and rallying; fatigue and ammunition; spells and abilities; terrain; coordinating several units. Give an example of good and bad play for each essential. Which can wait?

6. **Which armies and opponent create those chances?** Keep, simplify or replace the [proposed armies](benchmark.md#the-first-battle)? Do lords, casters, cavalry and ranged units all belong in the first battle? Keep the built-in AI as the opponent? Should the armies cost the same, mirror each other, or be deliberately unequal? Equal cost equalizes resources, not strength.

7. **Which starting conditions are part of the task?** Pick the role, map, difficulty and AI stats modifier, timer and unit size; set ranks, mounts, equipment and spells, funds and the starting behaviour toggles. Should the model deploy its army, or get a fixed deployment? May it plan before the battle clock starts, and with what information and time? Today the mod ends deployment automatically and sends the first observation afterwards; model deployment would need new work.

8. **What would show that the battle really tests knowledge?** If holding, or attacking the nearest enemy, wins as often as a model does, is the battle still useful? Would one competent winning example plus contrasting bad decisions be enough to keep it for development? Can several different winning plans count equally? This decides what makes the battle informative; the engine outcome is already agreed.

### C. Evidence of knowledge and its execution

9. **What counts as showing knowledge?** Observed choices and their effects only; a short declared plan linked to the orders that follow; separate questions about recorded public situations; or a mix? Explanations cost tokens and time, and offline answers don't show live execution. A stated tactic that isn't carried out supports a different claim than one carried out successfully.

10. **What is the independent reference for a good decision?** Your annotated examples, the game's rules and unit stats, a competent reference controller, or the measured outcomes of alternative plays? Who settles ambiguous cases and acceptable alternatives? Should knowledge labels be correct/incorrect/unknown, or graded? An LLM judge's impression, or the model's own explanation, doesn't establish correctness.

11. **How do we separate knowing, choosing and executing?** Do you want a record of the opportunity the model could see → the order it chose → the engine accepting it → the observed effect? For example, telling apart "never ordered a withdrawal", "ordered it too late" and "ordered it, but the unit stayed stuck". May an explanation stay "cause unknown" when the trace can't tell a bad plan from stale state or game behaviour?

12. **How far should the first version go in attributing causes?** Is an observed effective action enough, or must we show it improved health, morale or the chance of winning compared with another action? That needs its own comparison; damage that follows an order isn't enough. The harness can't restore an exact mid-battle state or the game's randomness. Should credit for specific actions, spell damage included, wait?

### D. Health, wavering/routing and battle scoring

13. **When should army condition be scored?** At the engine ending, at fixed battle times, over the whole battle, or several of these separately? The final state describes the finish; time spent ahead also rewards when it happened, and can reward dragging a battle out. If a battle ends early, what does a later checkpoint mean? Do you also want the state just before the decisive collapse? Does "ending" mean the first engine result or the later results screen? The two can give different readings.

14. **How should health be valued across units?** Keep each unit separate; sum absolute HP, if we can read it; average each unit's remaining fraction equally; or weight each fraction by a fixed declared value such as recruitment cost? These rank a damaged lord and damaged infantry very differently. Should the summary reward enemy losses, your own preservation, the difference, or show both? Should the denominator be the starting army, or include later summons too? A headcount or a sum of fractions doesn't measure combat strength.

15. **What should healing and temporary resources mean?** Net remaining health; total damage and healing separately, if observable; or both? How should barriers, resurrection and summoned units count if the roster has them, and should summons stay separate from the original army? Repeated damage and healing could inflate a cumulative score without improving the result. These cases can stay out of the first roster instead of needing general support now.

16. **What is each leadership state worth?** Do wavering, routing, rallied, shattered, leaving the battlefield and destroyed need distinct outcomes? The options are the final state, the time spent in each state, or how often units change state: which matches what you want to reward? Does a rout that recovers keep credit? Repeated routs and time spent routing answer different questions. Numeric leadership is another measure, not automatically a common scale across unit types.

17. **How should health and morale combine?** Keep them separate, combine them with explicit weights, or use one only to break ties? How do we avoid counting a damaged unit's later rout as a second, independent loss? Does a healthy routed unit count as temporarily out, lost, or partly valuable? How are units that don't rout normally treated? End-state flags alone can't show which order caused a collapse, and the flags can overlap.

   Evidence for 16-17 (2026-10-28, not an answer; friendly units in 441 recorded battles, older
   scenarios): 42% of 1,867 routs recovered but only 144 stayed in action; half began with more
   than half the men; 37% of living units routing at the end were above half strength
   (`runs/interview-evidence-20261028/`).

18. **How should non-wins and failures count?** A draw as zero, a half point, or its own category? The controller-failure rule is agreed ([outcome table](benchmark.md#outcome-and-score)); decide the rest: provider outage, exhausted credits, wall-time or budget cap, unknown failure and voluntary surrender. Which count against the model as served, which get a replacement battle, and which stay unresolved? Can a failed battle keep partial health or morale credit? The engine timer and the controller's wall-time limit are different endings.

### E. Model inputs, permitted help and real-time execution

19. **What knowledge do we give the model, and what must it bring?** Only the current structured state and the order rules; also unit stats and ability descriptions; or tactical guidance and worked examples too? Which facts visible in the game's UI should our interface expose? Today it gives unit type, class, range and visible state, but not every unit-card stat or a full terrain and line-of-fire map. Missing facts can make a battle test memorized game data or interface gaps instead of the intended skill, and added tactical advice changes what prior knowledge is tested.

20. **Which helpers are allowed?** Direct orders only, the game's queued orders, scripted tactical skills, or several cooperating model calls? The game already does pathfinding and ordinary combat, and behaviour toggles change what units do automatically. Should every model get the same memory, history, observation detail and helpers? Which choices belong in separate controller comparisons?

21. **How much can a model act while a decision is pending?** One request at a time while existing orders keep running, or asynchronous planning with faster helpers? What happens to a stale reply: issue it, discard it, or check it against newer public state? What can cancel or replace queued orders? These rules decide whether a slow model can commit to actions that keep working through its next API call.

22. **Which latency claim comes first?** Performance at each model's natural serving latency, sensitivity to added delay for a fixed controller, or both, reported separately? Natural latency answers the practical question but doesn't isolate reasoning quality. Older observations, longer waits between calls and slower inference are different interventions. No option pauses or slows the battle, and a delay sweep can't prove that faster serving would have saved a particular loss.

23. **Which time measurements should explain performance?** API request and response time, the age of the observed state when an order is issued, gaps between decisions, and time to the observed effect answer different questions. Do you want typical and slowest behaviour, including retries, failed calls and calls still pending at the ending? Is issue time enough at first, with execution time marked unknown for queued orders, or is per-order effect timing needed before this battle can be a benchmark?

24. **What resources are equal, and does efficiency change the rank?** The same money cap, token cap, call limit or effort setting; each model's declared best setting; or several operating points reported separately? What happens at a cap? Should latency and cost lower the score, or be reported beside it? Delay already hurts live play, so an extra latency penalty would count speed twice. Which provider, model version, sampling settings and retry rules must be fixed or disclosed?

### F. Information gaps and the minimum implementation

What the code records today and what is missing: [measurement gaps](#measurement-gaps).

25. **Which missing measurements does the first usable version need?** Choose among private per-unit HP and state histories, explicit unknown/read-error values, finer or absolute HP, enemy numeric leadership, unit-card facts, richer terrain and line of fire, and order-effect evidence. Which can be marked unavailable without blocking a useful result? We will find out what the game API allows; you don't need to pick a method.

26. **Which new fields reach the model, and which are for scoring only?** Hidden enemy health, for example, could help the evaluator but would leak forbidden information to a controller. Should new visible unit facts go to every controller equally? Scoring data stays out of prompts, memory, helpers and feedback unless the public information rules change.

27. **What accuracy and missing-data policy is enough?** What is the shortest wavering or routing episode, or the smallest HP change, you care about? That sets the recording interval and precision, independently of how often a model calls. Should a recording gap make only that measure unknown, require bounded estimates, or void the attempt for that comparison? A known engine result can stand even when a diagnostic can't be computed.

### G. Repetition, checks and when the definition is done

28. **Which references make the scores meaningful?** Hold, walking or running at the nearest enemy, a stronger script, your own play, or a particular model? What difference would you care about: more wins, fewer own losses for the same outcomes, better use of a tactical opportunity, or lower cost? A human reference would need its different information and controls disclosed.

29. **What repeatability and uncertainty are acceptable?** Fresh launches, rematches after an agreed reset check, or both during development? Which starting conditions must match, and what uncontrolled variation is acceptable? Should the first comparison be exploratory, or large enough to detect a stated gap? Set the game-time and money bound and the stopping and replacement rule before choosing a sample count. A seed or a matching start doesn't make the battle's randomness identical. May prompts and controllers be tuned on this battle, or must they be frozen before seeing it? The answer limits what we can claim beyond this matchup.

30. **What should the report let you inspect?** Candidates: a result table, both armies' per-unit health and state timelines, knowledge judgements linked to decisions, latency, cost and failure summaries, and representative events. Which are essential for comparing models? Should different strengths stay visible instead of forcing one winner when the evidence or the tradeoffs don't support one?

31. **Which repeatable checks would convince you the implementation is correct?** Candidates: lobby and start settings checked against the actual battle; unit HP and flags checked against timestamped UI or independent engine evidence through damage, rout and recovery; hand-classified endings and failures; changes to hidden data that must not alter public inputs; and clock and order-effect checks. Which cases, tolerances and independent references? Include plausible wrong implementations (a rout treated as a death, a failed read treated as zero, a queued order counted as executed). The [proposed checks](#correctness-checks-to-agree) are material to refine, not agreed methods.

32. **When is the definition complete enough to build?** One fixed battle with an agreed objective, score and diagnostics, inputs and orders, timing, failure rules and correctness checks? Which open items may be deferred explicitly? Once you have answered, we replace the affected proposals with your decisions and list only the work they need. This interview picks no roster, formula, threshold, sample count or new experiment.

## Correctness checks to agree

JUDGEMENT: Land Battle checks — Codex, 2026-10-23: propose the case set below, using live
UI/engine observations and independently classified outcomes. Offline readers alone would
support narrower claims; release readiness rests on agreement and execution of these checks.

| Claim | Independent reference and repeatable check | Wrong behaviour it must catch |
|---|---|---|
| The battle starts as declared | Reuse the agreed army and settings check; compare this battle's rosters, ranks, equipment, role, funds and map before scoring | Leftover lobby settings, wrong character equipment, the wrong map or role |
| Results and denominators are right | Hand-classify engine win, loss and draw, timer win and loss, construction failure, retry, terminal failure, late cleanup error, setup failure and operator stop; compare every benchmark reader with that | A timer win dropped, a failed controller missing, a late error replacing a win |
| Unit measurements mean what they say | Compare timestamped unit records with the game UI and engine through damage, recovery, rout and rally, shattering, leaving the field, and hidden or unavailable units | A fraction treated as absolute HP, a rout counted as a death, overlapping states counted twice, missing data filled with zero |
| Hidden information stays hidden | Change only evaluation data and check that the controller's inputs stay identical; separately check visible and hidden units in game | Hidden enemy health or leadership reaching prompts, memory or feedback |
| The clock runs and orders take effect | Compare battle-clock progress with independently measured elapsed time; follow an order through to movement or contact, including orders accepted without effect | Trusting the constant speed field, calling a queued order executed, a controller's call rate changing how much a measurement weighs |
| The report matches the evidence | Recompute a saved set of battles from raw evidence; compare text, JSON and HTML, and look at the page in a browser; keep input hashes | Lost failures, pooled conditions, a misleading curve where data is missing, a changed historical verdict |

Agree the exact cases, tolerances and stopping conditions before these become release checks. Reuse existing evidence where it answers the same question; add focused tests for observed failures, and try important checks against a plausible wrong implementation. Run focused `uv run --locked pytest -ra <tests>` with scratch files under `runs/`, and `uv run --locked ruff check .`. Passing component tests don't show live effects or playing strength. The agreed checks in [agreed-checks.md](../agreed-checks.md) keep their scope; this page adds none.

## The failure rule in code

The owner agreed the controller-failure rule on 2026-10-21 (the agreed rows of the [outcome table](benchmark.md#outcome-and-score)). Since harness b47 (`b536ae6`), a late acknowledgement or `close()` failure keeps the engine's ending (`engine_ending`), but the episode still scores as a policy failure. A controller is built before a battle id is recorded, so the card reader leaves construction failures out. Scoring both cases by the rule is a later evaluator change; c1's historical scoring stays as it is.

How often it matters (recount 2026-10-21, `runs/twwarhammer3/away-20261021/failures.txt`; rerun with `uv run --locked python runs/twwarhammer3/away-20261021/failures.py`): of 595 recorded episodes, none failed at construction, at the acknowledgement of an ending or at `close()`, so the rule changes no recorded result. All 9 policy failures happened during battle, and the rule scores them as today's reader does: 8 forfeits, plus an HTTP 402 credit stop at b30 excluded as an operator stop. The register still lists that stop and a harness-probe `KeyError` at b2 as policy failures; fixing those rows is a separate decision. 18 jobs ended before any episode (10 of them setup failures), none in the c1 cohort.

The agreed check ([agreed-checks.md](../agreed-checks.md), 2026-10-21): `uv run --locked pytest -ra tests/twwarhammer3/test_wh3_play.py::test_a_controller_failure_after_the_ending_keeps_the_engine_result`, which fails on the parent of `b536ae6`. It makes no claim about the game itself.

## Measurement gaps

What the code records today, from the [mailbox contract](../../src/twwarhammer3/engine/mailbox.py), the [Lua recorder](../../src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua), the [integration notes](integration.md#battle), the [timing limits](latency.md#measurements) and the [trace capture limits](../posttraining.md#beyond-supervised-fine-tuning). This reads the code and past records; none of it is a new live measurement.

| Quantity | Recorded now | Missing |
|---|---|---|
| Health and entities | Each unit's `hp` fraction (rounded to 0.01) and living entity count, for friendly and visible enemy units; barrier HP separately where available | Hidden enemies' health over time; absolute and maximum HP; gross damage and healing, which net changes can't recover |
| Wavering and routing | Public flags for wavering, routing and shattered; private totals for routed, leaving, absent and alive | Per-unit private histories, recoveries and durations. The private `routed` total merges routing and shattered, and the categories overlap |
| Numeric leadership | Friendly units' UI fraction and the text of the largest effect | Enemy leadership; the full modifiers, the precision, and whether values compare across units. The fraction can be below 0 or above 1 |
| Coverage | The private evaluation holds both armies' headcounts and unit totals; public enemy records follow visibility | Hidden totals are kept only at the start and end, not as unit histories. The replay is visibility-filtered and observations follow the controller's timing, so neither gives a complete private unit timeline, and old traces can't rebuild hidden health or enemy leadership |
| Missing values | A failed unit record becomes `{id, error}`; the evaluator has an unknown living-count category | A single failed Lua getter can fall back to HP 0 or a false flag; that must never be read as a death or as "not routing" |
| Contacts and spells | Observed contacts and accepted casts | Flank contacts and spell effects need their own checks |
| Time and order effects | Basis timestamps, issue acknowledgements and later observations | A queued acknowledgement means submitted, not executed, and execution can come later; `speed: 1` is a constant, not a measurement; the engine ending is authoritative, but a timer cause is inferred |

The results screen's `DamageDealt`, `DamageDealtCost` and friendly-kill counters are documented candidates ([capability notes](integration.md#finding-another-capability)). Nobody has checked them, and they aren't scoring inputs; comparing them with the results screen would show whether they can fill a damage gap.

Full enemy leadership would help. Until we can read it, it stays missing: never invent values, and don't hold back a correctly labelled outcome benchmark waiting for it.

## What the current code reports

This is what `battle/play.py` and `battle/report.py` do today, not the new score. The report and the card code disagree on timer wins and failed trials; the [audit](../testing.md#wh3-evaluations-and-tests-2026-10-23) lists the differences. Use the definition's [outcome table](benchmark.md#outcome-and-score) only after its evaluator is built and checked.

Trial statuses (`battle/play.py`):
- `won`, `lost`, `draw`: the engine's result, the only gameplay outcomes. `ended_by` is `time_limit` when the countdown ran out (inferred from the last ticked deadline; see [integration.md](integration.md)). The report shows `time_limit` and keeps the engine result, so a defender's timer win isn't hidden.
- `truncated` (episode wall cap), `policy_failure` (the controller failed for good, or failed to build or close), `budget_exhausted` (the job's ledger cap or its safety stop, or the account's key or credit: HTTP 401/402), `infrastructure_failure`, `unsupported_or_invalid` (a protocol or setup check failed) and `interrupted` (operator stop).

Every started trial goes into `result.json`, the manifest and the register. Any ending other than an engine result stops the job, leaving unplayed controllers unpaired. Show planned, started and scored counts per controller, with the reason each missing partner is missing, and don't discard a failure to balance pairs. Comparing only complete pairs keeps the battles both controllers finished, which can favour easier ones. If that blocks the planned comparison, stop it or freeze a new set with one controller per launch, interleaved over time; don't keep replacing only the incomplete pairs.

`battle/report.py` groups evidence by resolved scenario, source revision, game build, track, recorder and imagery settings, observe/tick/interval, model and effort, and never pools groups. For each group it computes:
- outcomes per controller and added age: valid trials (engine results) over started ones, with the failures listed;
- the non-timer win rate (non-timer wins over all valid trials) with a 95% Wilson interval, withheld when a controller has repeats within one launch;
- the active-strength margin: own men neither routing nor shattered over own starting men, minus the same for the enemy, from hidden totals. Reinforcements and summons join the denominator, and unit value isn't weighted (the register's `own_left` and `enemy_left` count routing men as alive);
- paired differences: for each pair of controllers, the margin difference per launch (rematch repeats averaged within it), a Student-t 95% interval over launches, an approximate 80%-power detectable difference, the unpaired launches, and the result without launches whose starts were flagged;
- per trial: order age at application (non-empty batches), snapshot age at decision, plan age, model call seconds and provider processing time, returned model names, decisions per battle second, refusals by validation or engine code, protected-unit survival, objective shares held (integrated on engine ticks), supplies left, accepted builds and reinforcements by type, tokens, USD, wall seconds and clock ratio;
- per controller, the median of its trials' median order ages; the HTML pools order batches (adopted plans, for `commander`) to show its typical delay;
- throughput: valid trials per job wall hour, counting setup, resets and failed jobs.

The text and JSON reports end with the limitations from `report.collect`. The HTML page shows outcomes, the typical order delay and the cost per battle, and leaves the margin, paired differences and limitations to those files ([reports.md](reports.md)). The report's engine-completed rate and the old tactic-card rate use different denominators; neither is the new score. Other battle types need their own declared objectives; a point-capture objective shouldn't require destroying the enemy.

## Measured facts behind the design

Measured on 2026-10-13/14 from the register and runs; the full analysis is Part 1 of `git show d606d39:docs/twwarhammer3/benchmark.md`.
- **A rematch restarts the same battle**: 30 of 32 jobs matched to 0.1 m and 1°, and the two exceptions ended deployment 100 ms later. **A new launch doesn't**: starts were up to 5 m and 48° apart over 14 `kho5-dwf5` launches. So launches are the sampling unit.
- **The engine replays a battle exactly when orders land on the same ticks.** Three of six `skills-v1.2-kho` episodes were identical to 530 s; one batch applied a tick later made the rest diverge. Repeats of a controller on one battle are correlated.
- **`kho5-dwf5` changed maps**: it named none, and the lobby kept a random draw's map.
- **WSL's monotonic clock ran 0-11% slow**, so wall durations use the system clock.
- **The raw margin contradicted the outcome** in 16 of 108 battles (routing men counted as alive), hence the active margin.
- **Throughput**: about 8 episodes an hour; a one-episode job took a median 409 s for a 317 s battle.
- **Information age**: `llm` v14 median 6.0 s (90th percentile 9.2 s); scripts one tick; commander plans 6.0 s old when adopted. Pausing during inference (`llm` v4, 3 battles per arm) showed no effect, but could only have detected a large one.
- **The setup probe** (`runs/twwarhammer3/benchmark-probe-20261014`, source `f2c8463`, `dwf-sla-taurox`) recruited 24 cards by id and read the lobby and battle settings back. `hold` lost at 298 s; its 965 empty requests applied after 0.3 s (954) or 0.6 s (11). Its protected units met melee 8.4, 13.2, 24.0, 46.2 and 47.4 s after an enemy came within 100 m; the shortest of these is less than a slow model's information age plus its decision period.
- **The AI stats modifier** changed only the AI units' stats in the b2 and b8 startup snapshots. Lobby options, modifier getters and terrain sampling are in [integration.md](integration.md).

## Related research

A selective review of primary sources on 2026-10-20. It shaped the earlier tactic-card work; the WH3 uses below are our proposals.

| Source | Lesson for WH3 | Limit |
|---|---|---|
| [Realtime-Bench](https://arxiv.org/html/2610.22155v2), October 2026 | Keep the natural timing of a deployment apart from assigned timing conditions, and consistency apart from one lucky run | Its paused and token clocks aren't WH3 conditions; WH3 stays live at 1x |
| [The World Won't Wait / TORSI](https://arxiv.org/html/2610.20665), October 2026 | Keep feedback, choosing between revisions, and final evaluation apart; account for actions that keep running during inference | A different paper from Realtime-Bench; its pausing and saved states aren't available here |
| [GameWorld](https://arxiv.org/html/2604.07429), April 2026 | Check state-based outcome rules, and freeze the whole interface and budget before rerunning | Its live variant already studies inference during play; saved state alone doesn't validate a WH3 tactic signature |
| [SMACv2](https://arxiv.org/abs/2212.07489) | Try a fixed schedule before claiming that feedback or recovery is needed | Random StarCraft teams don't give useful or reproducible WH3 variants |
| [LatencySensitiveBench](https://arxiv.org/html/2505.19481v1) | Faster calls stop helping once carrying out the actions is the bottleneck | Its Street Fighter timing threshold isn't a WH3 threshold |
| [Gaia2, §B.2.4](https://arxiv.org/html/2602.11964v1), February 2026 | Check the scorer both with perturbations of known validity and with labelled real agent runs | Its 450-run verifier study doesn't validate WH3 signatures; uncertain labels and independent review here are our proposals |
| [Statistical Precipice](https://arxiv.org/html/2108.13264v4), NeurIPS 2021 | Match the uncertainty to the comparison: repeated runs on fixed tasks differ from sampling more tasks | Neither the bootstrap nor an aggregate score makes a small, chosen WH3 suite representative |

What WH3 adds is the combination: tactics you can inspect, morale, orders that persist, and units whose support can fall apart while the model is thinking. Live clocks and hierarchical control already have prior work. [Robot-team research](robot-team-research.md) develops the recovery comparisons and transfer limits; any benefit to physical robots is untested.

**A possible research contribution, a hypothesis for the team branch:** a reproducible set of tactical cases where a controller must keep or restore support between units while its observations age, with evidence that separates the plan, the orders and their effects. "The reserve was ordered forward" is different from "it arrived before the gun was caught". That would diagnose something a win rate misses. It isn't an established novelty claim, and single-unit cards such as the chariot don't need it.

Before a research release, compare the retained tasks with the closest work on five points: what keeps happening during inference; which decisions the game's own unit AI makes; whether support can fail and be restored; what action and effect evidence exists; and what an outside user can reproduce. Include Realtime-Bench and GameWorld for live timing, SMACv2 for coordination and shortcut tests, and [DPT-Agent](https://arxiv.org/abs/2502.11882) for asynchronous hierarchical game control. Record overlaps and open questions as well as differences, and search again at release. A different game, or a mix of familiar mechanics, doesn't prove novelty. If fixed jobs or a timed reserve solve the line battle, narrow its recovery claim; other tactic cards can still be useful.

## Owner goals

Earlier owner directions that still guide which battles and models come next ([owner-direction.md](../owner-direction.md)):
- **Difficulty:** hard but shown to be winnable, with meaningful choices. One win shows a battle is possible, not that it is reliably winnable.
- **Scenario mix:** mostly small battles testing one or two distinct decisions, plus a few larger coordination or scale problems. A different faction or difficulty step doesn't automatically add coverage.
- **Model coverage:** eventually compare every supported reasoning mode of each selected model. Recheck the provider's real modes before freezing a round; a provider accepting the setting doesn't mean the effort levels behave differently.
- **Budget:** choose the number of repeats per question, and don't start with a broad paid matrix. Declare API and game-time caps, allow long losing battles and keep failures. Old cost estimates and ledger balances are history, not current allowances.

## Experiments for later

Definitions only; nothing here is scheduled. To compare a model with itself, fix its exact model id, effort, controller and prompt version, game build, map, settings and everything other than the treatment. Use matched battles, rotate the order of conditions, reset controller memory every battle and keep every attempt, failures included. Record input, output and cached tokens, response latency, observation age, cost, actions and objective progress.

| Axis | Change | What it means and what to control |
|---|---|---|
| Army size and control workload | The number of independently commanded units, with declared composition ratios | Also changes the number of orders, unit density, pathing, contact timing, combat balance and tokens: end-to-end scaling, not a pure context-length effect |
| Neutral prompt text | Extra non-tactical text, with the same battle, state and orders | Vary the token count while holding facts and history fixed, and record where the text goes. Check that it adds no advice and doesn't change the task |
| Useful history | Relevant earlier observations and orders at set lengths | Tests whether memory helps or interferes; it changes information as well as length. Keep the rule for choosing history fixed |
| Fact formatting | The same facts written compactly or verbosely | Tests representation apart from new information; check that the facts are really equivalent |
| Added observation age | Buffered observations at declared minimum ages | Already supported; different from slower generation or a longer prompt. Natural model latency stays measured, not assigned |

Larger armies and longer prompts can be crossed later to separate their effects. First check feasibility and freeze the treatments; use objective measures that fit the battle, and don't infer reasoning limits from slower real-time play alone.

## Later

Built only when a result or the owner calls for it:
- **A visual track and robotics models** (owner, 2026-10-14): a game image with each observation, for vision models and VLAs, as its own track. Today's stills are only for presentation ([reports.md](reports.md)); the track needs per-decision capture, camera and timing rules, an adapter from robot actions to orders, and hardware cards.
- **Model against model, possibly in teams** (owner idea, 2026-10-14): the battle script drives both armies with a view per side (try this first), or local multiplayer with one client per side (risk of desync). Results become relative ratings.
- **RL rewards.** The benchmark defines tasks, conditions, outcomes and evidence; an RL reward defines what training optimizes. They can share the engine outcome and the measurements without sharing every scoring rule. Start training from the final outcome; health or leadership shaping is a later, separately versioned experiment. Don't reward every morale drop, rout or flank as its own achievement: temporary effects reverse, damage and routing can describe the same fight, and useful sacrifices win battles. A shaped reward is better only if it improves results on frozen, unseen evaluation battles.
- An equal-tempo `age-D/P` track (fixed application age and decision period) to separate reasoning from speed; per-controller USD caps; an `exec:` adapter for controllers not written in Python; a reduced observation track if matching what a player sees becomes a goal; a value-weighted margin; a reaction-window screen with a pass mark.
- Records not kept yet: the basis of each hybrid executor order, when the mod read a request, and when an order's effect first showed.
- In-game checks still open: `teleport_to_location` starting arrangements; restarting an undecided battle (play never does: such an ending stops the job); whether a launch reseeds the engine; whether the visibility filter matches the player's view; whether the HUD's balance-of-power bar (kept out of observations) counts as player information.

## History

Earlier benchmark plans, all superseded by the Land Battle definition. Their full text is in `git show b0ac9e3:docs/twwarhammer3/benchmark.md`, and older revisions are named below; results and findings are in [log.md](log.md).

- **Tactic cards (2026-10-18 to 10-22).** A card was a tactical question with a scenario, a witness (an example winning play), wrong plays and an evidence rule: [definition and gates](tactic-cards.md#a-card), [chariot rule](tactic-cards.md#the-chariot-card-the-first-benchmark-card), [starting-set screen](tactic-cards.md#the-starting-set-proposal-2026-10-21). Their verdicts stay attached to their own evidence and don't admit or reject Land Battle scenarios. Labels such as `prototype_not_admitted` are legacy metadata.
- **Small scenarios S1-S11 (2026-10-16/17).** Battles testing one or two skills each: feint and flank, kiting, lines of fire, protecting a gun, spell timing, hammer and anvil, terrain defence, focus fire, monster targeting, receiving a charge and counter-battery. Each was tried with a naive script that should lose and a scripted play of the intended tactic at 0 and 5 s added age. None was admitted, and no model won one. Still relevant: on Taurox, posts and waypoints often fell inside the central rock and the engine refused the moves (since b23 scripted moves step to open ground); characters cost more in the lobby than in the database; in S7 a defender won on the timer by hiding in a corner without any contact. Records: [first checkpoint](log.md#2026-10-17-harness-b17-small-scenario-checkpoint-work-stopped), [overnight tranche](log.md#2026-10-17-overnight-tranche-harness-b18-b23), [second batch](small-scenarios-2.md). Superseded on 2026-10-18 by the tactic cards.
- **Owner decisions, 2026-10-16 night.** Try small scenarios; use GLM-5.3 low through OpenRouter as the cheap reference model; write a trace exporter that stores reasoning text (built as harness b14, [traces.md](traces.md)).
- **Calibration cards (2026-10-16).** A review of 54 M1 battles proposed six families as hypotheses: siege defence, swarm command, caster assault, cavalry assault, defensive swarm and Kislev survival ([M1 review](log.md#2026-10-16-matched-round-m1-on-the-retained-core-plan)). A free scripted tranche lost all three tries ([log](log.md#2026-10-16-free-siegeswarm-calibration-checks)).
- **Declared families (b12).** Ranged protection (`dwf-sla-taurox`, `dwf-sla-herald`), cavalry against anti-large (`brt-cavalry-emp-pikes`, `-pegasus`, `-assault`) and a caster-led force (`tze-caster-skv-screen`, `-assault`). All but `dwf-sla-taurox` have a `-hard` variant (AI modifier 1.1) and a `-heldout-wastes` map. Two Skaven swarm prototypes (`skv-swarm-dwf-line`, `dwf-line-skv-swarm`) were screened on 2026-10-15. None passed the admission rule then in force. Audits and rosters: `git show e75cba5:docs/twwarhammer3/benchmark.md` and the [b12 log](log.md#2026-10-16-harness-b12-and-distinct-scenario-families).
- **Other battle types.** The old Conquest pilot had one central point, so it didn't test holding several; the survival screen never made supplies scarce; custom evacuation is deferred after a placement failure ([log](log.md#2026-10-16-evacuation-deferred-controller-version-labels-fixed)).
- **Admission rule retired (2026-10-15).** The owner retired the 30-70% reference win-rate gate and the paired-margin admission test. Difficulty isn't adjusted automatically to a reference model's win rate.
- **C1 (2026-10-15).** Six launches of `brt-cavalry-emp-assault-hard` (`llm` v16, harness b10, no added age, rotation seeds 2026101501-06), each rotating `llm_rules` on Sol low and on Luna low with the run-nearest and walk-nearest scripts. Sol won 1 of 6; Luna and both scripts won 0 of 6, all engine outcomes. Report: `runs/twwarhammer3/reports/c1-cavalry-ai11.html`. Records: [decisions](log.md#2026-10-15-harness-b10-llm-v16-and-the-calibration-decisions), [launches 1-2](log.md#2026-10-15-calibration-c1-launches-1-and-2), [launches 3-6](log.md#2026-10-15-calibration-c1-launches-3-to-6).
- **G1 (stopped 2026-10-14).** Six launches at each AI modifier (1.0 and 1.1), rotating Sol low `llm_rules` with walk-nearest and run-nearest. The owner stopped it partway, and G2 (added ages 0, 6 and 10 s) never ran ([log](log.md#2026-10-14-partial-g1-and-owner-requested-stop)). Design: `git show ae7ca31:docs/twwarhammer3/benchmark.md`.

Plans, state files, audits and runners under `runs/twwarhammer3/calibration/` stay as evidence; `scripts/wh3_queue.py` runs future jobs.
