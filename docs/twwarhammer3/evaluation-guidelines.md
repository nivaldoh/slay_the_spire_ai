# Guidelines for evaluating WH3 battle controllers

Evaluate whether a declared controller can achieve a declared tactical objective while
Total War: WARHAMMER III keeps running at 1x. Report how often it succeeds, what it costs,
how reliably it runs and what the evidence says about its behavior. A useful evaluation
lets another developer make a concrete choice and inspect the reasons for that choice.

These guidelines accompany the [benchmark definition](benchmark.md),
[tactic cards](tactic-cards.md) and [run protocol](benchmark-run.md). The research basis is
the [twelve supplied readings and selected cited work](#sources-and-their-use), reviewed
2026-10-20. The WH3 procedures and examples below are our application of those ideas;
the cited studies do not establish that they work in this game.

**Status:** design guidance, with proposed code enforcement. This document changes no
code, frozen score or historical result. New verification methods still require owner
agreement under [AGENTS.md](../../AGENTS.md#verification-hard-rule), followed by passing
evidence at a named revision. Existing component checks do not verify live tactics.

Use this guide in order for a new study, or jump to the relevant decision:

- [Define the question and controller](#define-the-question-and-controller).
- [Build tasks that test the intended skill](#build-tasks-that-test-the-intended-skill).
- [Protect development and final evaluation](#protect-development-and-final-evaluation).
- [Plan trials and comparisons](#plan-trials-and-comparisons).
- [Make the game and scorer trustworthy](#make-the-game-and-scorer-trustworthy).
- [Account for every attempt](#account-for-every-attempt).
- [Measure success timing and cost](#measure-success-timing-and-cost).
- [Use statistics that match the experiment](#use-statistics-that-match-the-experiment).
- [Collect useful human judgments](#collect-useful-human-judgments).
- [Use LLM judges only after calibration](#use-llm-judges-only-after-calibration).
- [Design rubrics and training rewards separately](#design-rubrics-and-training-rewards-separately).
- [Interpret results and investigate failures](#interpret-results-and-investigate-failures).
- [Make results reproducible and publishable](#make-results-reproducible-and-publishable).
- [Enforce the guidelines through code](#enforce-the-guidelines-through-code).
- [Adapt common evaluation advice to WH3](#adapt-common-evaluation-advice-to-wh3).
- [Use a short study declaration](#use-a-short-study-declaration).

## Define the question and controller

**G1. Write the decision before choosing the score.** For example: does supplying
withdrawal advice improve this controller's contact-win rate on this frozen chariot
card? State the population the answer concerns: this card on this installation, the
released suite, reserved map variants, or a declared collection of tactical families.
These are different claims. An Empire-focused suite cannot establish general WH3 mastery,
campaign ability, human-level play or transfer to robots.

**G2. Treat the complete controller as the evaluated system.** Record the model,
provider/backend, prompt, memory, tools, executor, sampling settings, retries and resource
limits. A helper that chooses routes or targets supplies tactical ability. A model with
that helper is a different controller. This follows the distinction between the model
and the agent system in [Anthropic's evaluation guide](https://www.anthropic.com/research/demystifying-evals-for-ai-agents).

For WH3, freeze this contract before the comparison:

| Part | Declare precisely |
|---|---|
| Task | Card version, map, sides, rosters, experience, difficulty, AI modifier, timer, unit size, objective and supported content |
| Information | Public observation fields, precision, visibility, roster knowledge, history, terrain and any supplied tactical advice |
| Actions | Order vocabulary, queue/replacement rules, limits, legal targets and built-in behaviors such as fire-at-will |
| Controller | Model/served identity, prompt and executor hashes, memory/reset policy, sampling, token limits, dependencies and external access |
| Time and resources | Live 1x, observation/tick/decision intervals, actual serving latency, added-delay arm, retry policy, battle and spending limits |
| Evaluation | Success predicate, failure handling, sampling unit, comparison, scoring/rubric version and exclusions |

**G3. Separate kinds of claim.** An end-to-end model comparison measures the model and
its serving conditions together. A same-model prompt comparison estimates the effect of
that prompt change. An executor comparison changes the help given to the model. A latency
intervention tests the assigned delay. Do not attribute a gain to reasoning, coordination
or memory when several of these changed together.

Possible enforcement: require these fields in a study manifest; compute compatibility
keys from resolved content, not filenames; refuse silent pooling across incompatible
conditions. Require a plain-language claim and the contrast that could support it.

## Build tasks that test the intended skill

**G4. Design around a consequential choice.** For each card, describe the situation,
the choice the controller must make, the intended effect, the success rule and a plausible
wrong play. Include the simplest alternative that could win without making the choice.
For a rifle-protection task, test whether abandoning the rifles still wins. For a recovery
task, test whether a fixed early reserve order is enough. More units alone do not establish
a coordination or long-context task.

Provide the controller with the objective, deadlines and constraints that determine
success. Private test cases may stay hidden; additional behavioral requirements may not.
A witness's preferred tactic and a diagnostic signature need not be prescribed unless
performing that behavior is itself the stated task.

Use a **witness**, a disclosed reference controller showing that the whole task is
achievable, and **foils**, working controllers that test simpler explanations. They must
obey the same information and timing contract as the comparison unless explicitly marked
as privileged diagnostics. Check that a losing foil actually executes its intended play;
a broken controller is not evidence that a shortcut fails.

**G5. Test alternative explanations before making a skill claim.** Inspect automatic
skirmishing, fire-at-will, pathfinding, pursuit, morale, terrain and timer rules. A model
can win after making a poor decision; it can also use an effective tactic other than the
author's preferred one. Preserve legitimate wins. If such wins undermine the card's
interpretation, revise its description or create a new card version. Do not add a hidden
requirement after seeing the winning behavior.

**G6. Keep the task collection meaningful.** Use a small coverage table: tactical choice,
unit roles, information demands, timing window, terrain, opposing behavior and reset
requirements. Identify omissions explicitly. Retain easy controls for harness regressions,
diagnostic tasks for specific failures, and tasks that can distinguish the compared
controllers. An all-losing screen needs investigation of feasibility, interface and
timing; it does not establish that all models lack tactics.

The benchmark literature distinguishes construction, quality review and difficulty.
Changing difficulty does not repair a flawed question. This is a useful lesson from
[Wolfe's benchmark survey](https://cameronrwolfe.substack.com/p/llm-bench). For WH3, roster
strength and experience are difficulty knobs, but changing them may also change which
tactic is useful. Recheck the choice instead of assuming the card stayed equivalent.

**G7. Separate screening from confirmation.** Use cheap exploratory trials to find broken
setups and shortcuts. Freeze the retained card, witness, foils, signature and confirmation
rule before collecting new confirmation evidence. Keep rejected candidates and their
reasons in the design record; disclose which models helped select them. Do not repeatedly
retry an unchanged admission gate until it passes. Preserve the chariot's historical rule;
the [proposed future admission counts](benchmark.md#from-a-candidate-to-a-scored-card)
are not universal sample-size requirements.

Possible enforcement: card metadata with choice/witness/foil fields, candidate history,
explicit phase labels and a fixed confirmation cohort. A schema can require an explanation;
only inspected game evidence can establish that the task tests the stated choice.

## Protect development and final evaluation

**G8. Split by related situations, not trace rows.** Keep training/prompt development,
revision selection and final evaluation distinct. All views of a battle, rematches,
near-duplicate setups and examples derived from the same tactical template must stay
together when the claim requires unseen templates. A new launch of a tuned card measures
repeatability on that card; it is not an unseen task.

Reserve supported map, roster or placement variations before tuning. Declare what is
held out: a parameter change within a familiar tactic is a narrower test than a new
tactical family. Check that each variation is valid and achievable without exposing its
results to the people choosing controller revisions. If the same person must do both,
record the exposure and narrow the claim.

**G9. Track every route by which test evidence can influence a controller.** Examples
include prompts, rules notes, skills, code-generated policies, training exports, judge
examples and manual replay reviews. A public benchmark cannot promise absence from a
provider's pretraining. State what is known, when the tasks were published, and what
access the controller authors had. Private tests require controlled access and limited
feedback; they still do not guarantee absence of related training data.

Once final results guide a change, those cases become development evidence for the new
claim. Retain the original evaluation, freeze the revised controller, and use new reserved
cases for confirmation. A scorer bug can justify a documented correction across all
affected controllers; it does not justify quietly selecting a more favorable test subset.

Possible enforcement: stable family/variant/episode IDs, content hashes, an exposure log,
split checks in exports and a test-use register. Reject direct and derived test episodes
from training exports. Similarity checks flag likely duplicates for review; hashes alone
cannot detect all semantic overlap.

## Plan trials and comparisons

**G10. Use a launch as the minimum grouping unit for current WH3 evidence.** Record
card, variant, game launch, episode, controller and repeat IDs. Rematches share a launch
and may replay the same internal situation. Preserve them as repeated observations within
that launch. Decision ticks, units, screenshots and model calls are not extra independent
battles. A launch ID is necessary bookkeeping, not proof that launches are independent.

**G11. Match the comparison and randomize its order.** Where supported, run the compared
controllers in the same declared setup and launch, with preassigned, balanced/randomized
order. Repeat across fresh launches and time blocks. Check for rematch carryover, reset
differences and first-episode effects. If the pairing is invalid, use separately launched
controllers interleaved across time and analyze them as such. Do not manufacture pairs
after seeing outcomes or claim a seeded game reset that has not been established.

Reset controller memory and executor state between episodes, including shared/module
state, queued orders and pending calls. Persistent learning would require a separate
track with a revised contract; the current track prohibits cross-trial state.
Declare cache use, precomputed plans and warmup.
Preparatory work is part of the controller's cost and knowledge. Run one game controller
at a time, as the repository requires, and avoid competing jobs that change its timing.

**G12. Make budgets and stopping rules part of the design.** Before final trials,
declare the primary comparison, meaningful effect, launch count or precision target,
randomization, exclusions, replacements and time/API ceilings. Use pilot evidence to
estimate what the budget can resolve. A budget too small for the question calls for a
narrower claim or an exploratory result, not a guaranteed ranking.

Do not rerun bad model replies for free: retries consume real time and money. Separate
an allowed retry within a battle from a replacement battle. Handle demonstrable setup
failures by a rule fixed before outcomes, retain their records, and apply that rule equally.
Stop for a serious harness fault or resource cap; disclose that the planned study was
incomplete. A cap reached after expensive failures can select which outcomes are observed.

Possible enforcement: immutable trial schedule and attempt IDs, recorded randomization
seed, fresh policy instances, explicit replacement links, and a stop record. Check the
planned cohort against actual starts before computing a comparison.

## Make the game and scorer trustworthy

**G13. Check the full chain against independent evidence.** The chain is:

`declared setup → observed start → delivered observation → chosen order → acknowledgement → observed effect → ending → score`

Each arrow can fail. An acknowledgement establishes what the bridge/game accepted or
queued under its contract; it does not establish that a unit reached the destination,
escaped melee, hit the intended target or received a charge bonus. Compare actual movement,
contact and resources with the intended effect in live, unpaused checks. Use the
[proposed correctness checks](benchmark.md#correctness-checks-to-agree), including
plausible wrong cases, before claiming those links verified.

**G14. Keep controller information separate from evaluation information.** Current
policy inputs omit `evaluation`, `final` and `setup`; friendly units and visible enemies
have the documented public representation. Hidden totals may support offline scoring.
They must not reach prompts, helpers, memory, tools or training inputs intended to use
the public contract. Restrict outside controllers to the declared files/interfaces; the
current convention is not proof of isolation against a controller that reads arbitrary
local files. A broader untrusted-submission service would need an isolation design.

For a proposed boundary check, vary hidden fields while keeping public state fixed and
compare every delivered policy input. Also inspect in-game visibility: a serializer test
cannot establish whether Lua gathered the right units. Observation allowlists and
controller input snapshots make accidental leakage easier to detect.

**G15. Audit the scorer independently of the runner.** Hand-classify a small real evidence
set using the written rule, then compare code. Include engine wins/losses/draws, timer
endings, rejected orders, missing frames, terminal failures and failures after an ending.
Where feasible, show a check rejects a deliberately wrong implementation: counting every
`won` as a contact win, treating missing frames as no tactic, or counting an acknowledged
move as a completed withdrawal. Manufactured traces test readers; live checks test game
effects. Neither substitutes for the other.

Possible enforcement: separate raw facts from derived labels; preserve scorer version
and input hashes; use read-only rescoring and a small set of independently labeled cases.
Reuse agreed component checks instead of adding many tests of incidental implementation.

## Account for every attempt

**G16. Freeze the success rule and its denominator together.** A card score should answer
the declared task. For a contact-victory card, timer survival is not contact victory;
for a point-holding card, reaching the time limit may be the intended success. Keep the
engine result and the card result as separate fields. Draws are a separate engine outcome;
whether they earn credit must be specified rather than silently worth half a win.

The following applies the [proposed next-evaluator failure rule](benchmark.md#correctness-checks-to-agree).
It requires agreement and implementation before use; historical scores retain their rules.

| Event | Proposed treatment | What remains visible |
|---|---|---|
| Planned trial never attempted | Unstarted; outside the success denominator | Assignment and reason it was not run |
| Proven game/setup fault before a valid task | Invalid attempt; use the declared replacement rule | Original attempt, cause, evidence and replacement link |
| Proven game/harness failure during battle, before an ending | Apply the frozen invalidation/replacement rule; include missing-outcome sensitivity when it could affect the comparison | Evidence for attribution, original attempt and any replacement; do not infer a gameplay loss |
| Controller cannot construct on its assigned attempt | Unsuccessful controller attempt | Construction failure, separate from game setup failure |
| Engine ending observed | Apply the card predicate to the engine result | Won/lost/draw, ending cause and task facts |
| Controller fails terminally during a valid battle | Unsuccessful attempt or forfeit | Provider/controller error and retries; do not invent an engine loss |
| Invalid order or retried call, battle continues | Keep the eventual result | Lost time, refusals, retry count and cost |
| Acknowledgement or cleanup fails after observed ending | Preserve the ending and score | Additional reliability failure |
| Operator stop, global budget exhaustion or uncertain truncation | Incomplete, with the predeclared rule; no automatic complete-case ranking | Phase, cause and missing-outcome sensitivity |

Define controller-specific deadlines separately from an experiment-wide emergency stop.
If violating a declared controller resource limit is a forfeit, say so before the run.
Do not disguise a slow or unreliable controller as an infrastructure exclusion. Unknown
causes stay unknown until investigated without reference to which controller benefits.

**G17. Show all denominators.** Report planned assignments, attempted trials, valid
starts, scored attempts, engine completions, exclusions, forfeits and unstarted assignments
per arm. A wins/completed-battles rate describes survivors and can favor a controller
that crashes often. Present it only as a labeled diagnostic beside the primary score.
An outcome missing its partner is not automatically disposable; complete-pair analysis
can be biased when failures decide which pairs survive.

For illustration, among 20 assigned opportunities, 8 observed successes, 10 known
unsuccessful attempts and 2 unresolved outcomes imply a full-cohort success rate between
8/20 and 10/20, without guessing those two outcomes. These bounds do not fix a flawed
design, but show how much missing evidence could change the conclusion.

Possible enforcement: a phase-aware result record with immutable observed endings and
separate failure events; reconciliation of every assignment to one disposition; reports
that display the numerator, denominator and unresolved counts rather than a bare rate.

## Measure success timing and cost

**G18. Keep a small set of measures with distinct jobs.**

| Measure | Use | Avoid |
|---|---|---|
| Card success and failure rate | Primary task performance under the frozen rule | Replacing it with a judge's impression |
| Tactical signature | Evidence that a named behavior occurred | Assuming the signature caused victory or is the only winning tactic |
| State measures | Diagnose survival, objectives, damage or resource use | Treating routing as death, raw men as unit value, or shaped progress as victory |
| Timing | Diagnose whether useful orders arrived while the opportunity existed | Treating API response time as total action delay |
| Cost and throughput | Compare operational usefulness | Omitting retries, failed attempts, setup or controller preparation |

Specify formulas, units, aggregation and missing-data rules. A survival measure needs a
rule for routed units, summons and reinforcements. A time-to-event measure must retain
battles where the event never happened or was still unobserved when recording ended;
averaging only fast successful arrivals would mislead. Keep exact task outcomes primary
when a partial-credit measure could be increased without completing the task.

**G19. Measure time at the point it matters.** Record both monotonic wall time and game
time without subtracting one clock from the other. Follow the observation sequence/battle
ID through snapshot, decision start, model completion, dispatch and acknowledgement.
Separate snapshot age, model-call time, queue/transport time, age when the order is issued,
plan age in a hierarchical controller and observed effect time where measurable. The
[timing contract](benchmark.md#timing-and-latency) specifies current fields.

Show distributions and long gaps as well as typical latency. Report missing/dropped
measurements and counts. A controller issuing no orders must remain visible even though
it has no order-age median. Summarize within episodes and launches before across-trial
comparison; pooling all orders overweights long, chatty battles. If reporting tail
percentiles, show the sample size and avoid precision unsupported by a handful of calls.
Track game-time/wall-time ratio and recording settings; nominal 1x does not guarantee
identical wall-time progression under different machine load.

**G20. Preserve natural latency in the primary result.** Network delay, provider retries
and executor behavior are part of deployment performance. Added delay is a separately
assigned intervention: specify whether it ages observations, delays dispatch or changes
decision cadence. These are not interchangeable. Analyze assigned arms first and report
achieved delay. Filtering to fast responses or adjusting away actual latency changes the
question and may select easier battle states. Never pause or slow WH3 for reasoning.

Report total USD/tokens and wall time for all attempts, plus cost per scored attempt and
per success where defined. Separate development, execution and offline judging costs.
If there are no successes, cost per success is undefined, not zero. With similar task
performance, present the success/cost/latency tradeoff instead of forcing a single winner.

Possible enforcement: linked clock events, latency completeness checks, per-episode
aggregation, and ledger reconciliation. Add no new metric without naming the decision
or failure diagnosis it serves.

## Use statistics that match the experiment

[Miller's error-bar paper](https://arxiv.org/html/2411.00640v1) motivates paired comparisons,
grouping related observations and planning sample size around a useful effect.
[Wolfe's statistics guide](https://cameronrwolfe.substack.com/p/stats-llm-evals) also distinguishes
variation across tasks from repeated answers to one task. WH3 adds shared rematch state,
real-time serving variation and a deliberately selected small task collection. The
analysis must represent those sources of dependence and the actual scope of inference.

### Choose what the average describes

**G21. Define the quantity being estimated.** For one fixed card, estimate success over
new comparable launches under the declared conditions. For a fixed suite, first estimate
each card's result, then combine only if a suite summary serves a stated purpose. Freeze
card weights in advance. Equal weight per card answers a different question from weight
per battle or per tactical family. More chariot trials must not silently give chariots
more influence.

For broader generalization, specify a process for choosing new variants/families and
collect evidence from them. Repeating one card many times cannot reveal variation between
families. A hand-selected suite supports claims about its coverage, not a random sample
of all WH3 tactics. Report each card and reserved variation even if a summary is shown.
Missing suite cells mean incomplete coverage; do not silently renormalize weights.

### Respect the grouping and pairing

**G22. Calculate uncertainty using independent groups.** On a fixed card, the current
card reader counts the first recorded episode per controller and added-delay arm per
launch. A study that instead averages repeats within launches must predeclare that rule.
Never select the best repeat.
For a paired comparison define each launch's difference as A's score minus B's score;
analyze those differences while preserving the pairing.

For repeated-launch uncertainty on a fixed suite, keep its cards fixed and resample whole
launch groups within each card. Keep all controllers and repeats from a sampled launch
together. For an explicitly sampled-family claim, a hierarchical analysis can also
represent family/variant sampling. State each level and its count. If launches share
strong session/day effects, block the design and account for that higher grouping or
qualify the estimate. Bootstrap software cannot create independent information absent
from the study.

**G23. Match the interval to the outcome and sample size.** For independent binary
attempts on one card, use a stated binomial interval such as Wilson, rather than a normal
interval that collapses at zero or one. For paired binary outcomes, retain the joint
counts: both succeed, only A, only B, neither. An exact McNemar test can test equal success
probabilities using the pairs where only one controller succeeds; it is not an effect-size
interval. Choose a paired proportion-difference interval separately. For continuous
launch differences, a Student-t interval is an approximation whose plausibility depends on the distribution
and number of independent launches. Inspect the observations and disclose those limits.

Few groups, all equal outcomes and rare failures need special care. A plain bootstrap of
ten losses only resamples losses; a zero-width interval would be false certainty about
future battles. Use an appropriate finite-sample method or label the evidence descriptive.
If using a Bayesian interval, disclose the prior and its influence; it does not remove
dependence or sampling bias. Small-sample concerns are developed in
[Bowyer and colleagues](https://arxiv.org/abs/2503.01747), cited by Wolfe.

**G24. Show uncertainty in the difference.** Report A, B, A minus B, interval method,
confidence level, and independent counts. Overlap between separate A/B intervals is not
a test of their difference. A 95% confidence interval describes a method's coverage over
repeated studies under its assumptions; it does not assign 95% probability to this fixed
unknown value. Distinguish uncertainty in the mean from the variability of individual
battles. Neither interval accounts automatically for a wrong scorer, leaked information
or unrepresentative tasks.

Illustrative calculations, not benchmark evidence:

- Zero successes in 10 independent trials still gives a one-sided exact 95% upper
  bound of `1 - 0.05**(1/10)`, about 26%. It does not establish impossibility.
- Ten successes in 14 independent trials has a two-sided 95% Wilson interval of about
  45–88%. A point estimate of 71% is not precise evidence of dependable success.
- For 20 matched launches where only A succeeds in 6 and only B in 2, the observed
  difference is `(6 - 2) / 20 = 20` percentage points. Uncertainty depends on those
  paired outcomes, not on treating 40 episodes as unrelated samples.

### Plan precision and limit selection effects

**G25. Choose an effect worth detecting before the study.** State the smallest gain that
would change the engineering decision, desired precision or statistical power, and
plausible pilot rates/paired variation. Estimate the required launches with the intended
analysis, including failed attempts and grouping. Show sensitivity to uncertain pilot
values. At independent binary probability near 0.5, roughly 385 trials are needed for
a normal-approximation 95% half-width of five percentage points. This is an illustration
of precision cost, not a WH3 requirement or a sample-size calculation for paired gains.

Distinguish an exploratory screen, card admission and a model comparison. Their questions
and acceptable errors differ. No fixed number such as 5, 10 or 30 is enough for every
one. At a fixed budget, balance new situations against repeats according to the claim
and pilot variability; account for launch cost. Do not lower sampling temperature just
to obtain tidier error bars if that changes the controller users will run.

**G26. Prevent selection from masquerading as evidence.** Choose one primary contrast
and outcome. Label extra metrics, subgroup findings and unplanned comparisons exploratory.
For a planned family of confirmatory comparisons, specify a multiple-testing method
such as Holm adjustment or simultaneous intervals. Keep all tried prompt/controller
versions in the development record; choosing the best of many noisy estimates inflates
its apparent performance. Confirm the selected version on fresh reserved evidence.

Use a fixed stopping rule unless a valid sequential method was specified before peeking.
Repeatedly checking ordinary intervals and stopping when one favors A invalidates their
nominal interpretation. Operational monitoring for crashes or budget is still necessary;
an interrupted study must be reported as interrupted. A non-significant result does not
establish equivalence. To claim practically similar performance, predeclare an equivalence
margin and use an analysis that can support that claim.

Possible enforcement: explicit analysis unit, frozen contrast/weights/stopping metadata,
cluster-aware resampling, refusal of unsupported intervals, paired-count tables and
independent recalculation examples. Challenge the analysis with all-wins/all-losses,
unequal repeat counts, correlated rematches and missing partners. Label intervals by
method; never print one merely
because a plotting library accepts the rows.

## Collect useful human judgments

**G27. Give reviewers a bounded question and a usable evidence view.** Human review is
valuable for checking whether a card tests its claimed choice and whether a tactical
label matches observable behavior. Recruit people who understand the relevant WH3
mechanics; record their experience and relationship to the controller. The owner can
define the desired benchmark, while an independent reviewer tests whether someone else
can apply that definition.

Weng emphasizes task design, reviewer training and continuing quality checks;
Yan's annotation guide makes purpose, definitions, decisions, examples and task logistics
explicit. Use those principles to write short instructions for each review task, with
positive, negative and ambiguous examples. Include how to inspect evidence, when to stop,
and how to mark insufficient evidence. Give reviewers enough time and, if recruiting
paid reviewers, document compensation and handling of their contributions.
Sources: [Weng](https://lilianweng.github.io/posts/2024-02-05-human-data-quality/),
[Yan](https://eugeneyan.com/writing/labeling-guidelines/).

For WH3, provide two separate views:

| Review question | Evidence allowed |
|---|---|
| Was the decision defensible when made? | Delivered observation, its age, legal actions, preceding public history, current orders and available resources; conceal future outcome on the first pass |
| What happened after the order? | Time-aligned orders, acknowledgements, subsequent state and permitted evaluation evidence; reveal the outcome only for the retrospective question |

Hide controller/model identity where possible. Do not label “should have attacked the
hidden unit” as a decision error. Do not treat a later loss as proof that a reasonable
choice was wrong. Presentation replays can help inspect effects, but their sampling
rate or camera may not resolve a brief event. Missing evidence is a reason to abstain.

**G28. Keep disagreement informative.** Have reviewers label a shared subset independently
before discussion, then adjudicate against the written rule and evidence. Retain original
labels, revised labels and reasons. Distinguish mistakes, unclear instructions, missing
observations and legitimate disagreement over strategy. Recheck a small repeated subset
to detect inconsistent application. Report raw agreement, label frequencies, sample size
and a suitable chance-adjusted measure where useful; high agreement on a dominant label
alone is weak evidence.

This distinction is supported by
[Röttger and colleagues](https://arxiv.org/html/2112.07475v2) and the
[rater-disagreement taxonomy](https://arxiv.org/html/2311.04345v1). For WH3, use a common
rule for observable event labels, but preserve multiple defensible tactical opinions.
Majority vote should not turn a debate about the best route into a false fact about which
route was necessary. A lone expert can create a useful first reference set; that is not
independent agreement or a measured human-performance baseline.

**G29. Separate finding errors from measuring their prevalence.** Deliberately collect
rare failures, close calls, wins without the named tactic, losses despite it, scripts,
models and delayed controllers for rubric development. Also retain a representative
sample with known selection rules for measuring ordinary error rates. A collection chosen
because every replay looked suspicious cannot estimate how often normal play fails.
Keep related clips/decisions in one split and use untouched examples for final validation.

Possible enforcement: review packets with recorded information permissions, anonymized
controller IDs, independent annotation fields, evidence timestamps, rubric versions,
sampling reasons and an adjudication history. Keep reviews under `runs/` until selecting
a small, shareable reference set; do not scatter per-example documents through the repo.

## Use LLM judges only after calibration

**G30. Start with the cheapest adequate grader.** Use code for engine endings and explicit
state predicates, human inspection for ambiguous game behavior, and an LLM only where
its additional coverage is useful. A judge can flag likely mistakes or propose trace
segments for review. It must not invent missing observations, override a recorded ending,
or certify hidden tactical understanding.

[Wolfe's judge overview](https://cameronrwolfe.substack.com/p/llm-as-a-judge) distinguishes
single-response, pairwise and reference-guided judgments. Use a direct criterion for
“did withdrawal occur?” Pairwise preference answers “which looks better?”, which does
not show that either passed. A reference battle illustrates a possible successful tactic;
its wording or exact order sequence is not the only acceptable answer.

**G31. Calibrate on human-labeled WH3 evidence before using judge labels in claims.**
Follow the useful sequence in [Hamel's guide](https://hamel.dev/blog/posts/llm-judge/index.html):
inspect real examples, write concrete critiques, refine criteria, then evaluate automation
against expert labels. Keep separate discovery, judge-tuning and untouched judge-validation
sets. A few dozen examples may reveal failure categories; they do not automatically
establish a dependable error rate. If a judge cannot meet the intended use, keep the
human check or narrow its role to triage.

Define the positive label, then report the confusion matrix for each consequential
criterion: correct detections, misses, false alarms and correct negatives. Include
uncertainty, class frequencies, abstention and coverage. Report precision and recall for
failure detection; ranking correlation does not establish that individual judgments are
correct. This choice of validation measure follows
[Yan's evaluator review](https://eugeneyan.com/writing/llm-evaluators/). Choose acceptance
thresholds from what the label will be used for, not a borrowed agreement percentage.

For example, a judge that marks every decision acceptable can be 95% accurate in a set
with 5% errors while detecting none. A balanced challenge set tests both classes, but
its precision does not automatically transfer to the natural, rarer error frequency.
Validate important scenario and controller groups separately; pooled agreement can hide
systematic mistakes on a small family. Separate judge-label uncertainty from battle
sampling uncertainty in reports that use both.

**G32. Test judge biases and evidence handling.** The primary
[MT-Bench judge study](https://arxiv.org/html/2306.05685v4) investigates position, verbosity
and self-preference biases, and distinguishes consistency from accuracy. Apply that
lesson through WH3 challenge cases:

- Reverse A/B presentation order and rename controllers without changing battle evidence.
- Compare terse correct execution with confident tactical commentary unsupported by orders.
- Include a sensible decision followed by loss, and a poor decision followed by victory.
- Include no-order behavior, a blocked acknowledged move, a countermanded withdrawal and
  incomplete replay. Require the correct distinction or an explicit abstention.
- Put instructions to the judge inside quoted controller text; they are evidence to
  assess, not instructions to obey. Keep scoring instructions outside that text.

These checks should preserve genuinely relevant timing and state. Removing a crucial
acknowledgement may properly change a label to unknown; that is not undesirable sensitivity.
Use evidence references and short explanations so mistakes can be audited. Neither an
eloquent explanation nor the judge's self-reported confidence establishes correctness.
If pairwise judgments contribute to a reported score, predeclare the presentation-order
procedure and treatment of ties, order-dependent disagreement and abstention. Balanced
or swapped presentation is a candidate method to validate locally, not a guaranteed fix.

**G33. Version judges like any other measurement tool.** Pin the judge model/served
identity, prompt, rubric, examples, evidence representation, sampling, retries and
aggregation. Save raw replies and validate their schema. Keep `not_applicable`,
`insufficient_evidence` and `judge_error` separate; none is a silent pass. Grade offline
so judging does not consume the controller's live decision window. Revalidate after a
material change or a shift in task/controller distribution.

An ensemble or repeated judging is a candidate intervention, not automatic reliability.
Judges may share errors. Compare proposed improvements against held-out human labels and
their cost, criterion by criterion. [Autorubric v3](https://arxiv.org/html/2603.00077v3)
reports configuration-specific failures rather than a universally best combination of
calibration, shuffling and ensembling. Preserve unresolved disagreement and report
coverage; do not quietly remove difficult cases from the score.

Possible enforcement: separate judge artifacts from engine results, validation gates for
each intended use, schema-checked labels and evidence pointers, versioned caches, and a
regression set of judge challenge cases. A cache key must include the entire measurement
configuration and evidence; an old cached grade is not a fresh drift check.

## Design rubrics and training rewards separately

**G34. Make each rubric item observable and narrow.** Specify one condition, its purpose,
applicability, required evidence, time window, label meanings and missing-evidence rule.
Use binary conditions when a defensible threshold exists; use measured quantities or
anchored levels when they convey real distinctions. Avoid “good tactics: 4/5” and items
that combine several independent behaviors. Set numeric thresholds from mechanics and
development evidence before final evaluation, not to agree with a preferred result.

An illustrative withdrawal rubric, to develop and verify before adoption:

| Item | Evidence needed | What does not establish it |
|---|---|---|
| Withdrawal was attempted | A submitted move order whose destination/direction meets the declared withdrawal rule for the identified engagement; record rejection, queuing and actual issuance separately | Text saying the unit will withdraw, or a move toward the enemy |
| Separation occurred | Subsequent positions/contact evidence meeting the frozen separation rule | The order being accepted |
| Contact resumed | Later evidence of the identified unit re-entering contact within the declared window | An attack order alone |
| A charge bonus applied | An independently validated game signal for that mechanic | A melee flag, a replay impression or a judge's inference |

Distinguish “event absent with adequate evidence” from “event cannot be assessed.” This
example does not redefine the chariot's existing cycles v1. Include counterexamples where
withdrawing would be harmful; rewarding the same maneuver in every situation tests
habit rather than situational choice. Test for redundant criteria that count one event
several times.

**G35. Publish aggregation rules and keep critical conditions separate.** If a score
combines rubric items, publish weights, direction, thresholds and handling of inapplicable
items. Compute aggregation in code, retaining individual labels. Check whether reasonable
weight choices change the conclusion. A breached information boundary cannot be offset
by many minor tactical positives. Missing evidence cannot silently improve a controller's
average by removing difficult items. Show both performance among assessable cases and
the fraction assessable; neither replaces the battle outcome.

**G36. Keep training rewards distinct from evaluation criteria.**
[Wolfe's rubric-RL survey](https://cameronrwolfe.substack.com/p/rubric-rl) describes criteria
used as reward signals, including changing them during training.
[Rubrics as Rewards](https://arxiv.org/html/2507.17746v2) studies expert-grounded criteria
and reward construction in medicine and science. Those results motivate experiments;
they do not show that a rubric reward improves real-time control.

WH3 already has engine outcomes. If adding dense rewards later, test how a controller
could maximize them without winning: repeated harmless withdrawals, damage farming,
waiting indefinitely or verbose self-praise. Optimize on development data and preserve
frozen engine-based final evaluation. Report training-judge improvement separately from
held-out battle improvement. Use a separate validation judge or human audit where judge
scores matter, and test for shared errors; a different model name alone is not independence.
Keep test battles, final labels and derived critiques out of training, following
[post-training provenance](../posttraining.md).

Possible enforcement: criterion schemas, explicit gates and denominators, a frozen
evaluation-rubric hash separate from reward versions, reward-exploit checks and split
checks on every training export. No reward model or judge framework is required for the
first benchmark release.

## Interpret results and investigate failures

**G37. State exactly what was observed.** A useful result names the card/controller
versions, counts, success/failure rule, comparison interval, timing and scope. Write
“A had a higher observed success rate on these cards; the interval also allows a small
disadvantage” when that is what the data show. Avoid declaring a winner from decimal
rankings, claiming no difference from a wide interval, or calling a single success reliable.
Use the repository's word **unverified** for features without an agreed passing check.

**G38. Diagnose through evidence and interventions.** Trace the earliest supported
failure and its later consequences. Use a small taxonomy: setup/interface fault,
information unavailable, poor decision, delayed decision, rejected/overwritten order,
execution blocked, scorer/recording fault, and unexplained outcome. Permit multiple
contributing causes and unknowns. Count affected battles as well as decisions so one
long failure does not dominate the summary.

“The order arrived after the target moved” is an observation when the timestamps support
it. “Latency caused the loss” is a causal claim requiring a suitable intervention and
comparison. Likewise, better results with tactical advice show the effect of supplying
advice; they do not fully separate knowledge from execution. An offline answer test can
assess stated knowledge, but cannot replay how that answer would change a live battle.
The existing [latency program](latency.md) keeps these questions separate.

Inspect success cases too: they can expose automatic behavior, scoring loopholes and
unnecessary helpers. Choose showcased replays with a stated rule and retain access to
the full cohort. Label post-hoc explanations as hypotheses. A follow-up experiment should
name the competing explanations and the result that would favor each, including “no
change.” Negative or inconclusive results are useful when the task and checks are sound.

Possible enforcement: report templates requiring counts, scope and evidence links;
separate observation and hypothesis fields; a failure taxonomy with unknowns; and a
link from each claimed improvement to its frozen comparison. Code cannot establish
causation by requiring a field called `cause`.

## Make results reproducible and publishable

**G39. Make recounting possible before asking others to rerun battles.** Release or
otherwise provide accessible raw evidence sufficient to reconstruct every included
result, exclusion and sampled tactical label. Preserve manifests, resolved scenarios,
controller inputs, actions, acknowledgements, endings, API exchanges where permitted,
cost/timing records and scoring configuration. Hash artifacts and record missing files.
Keep raw records immutable; write rescored outputs separately with a change history.
Do not expose credentials or redistribute proprietary game files.

An independent developer should be able to recompute counts and example labels without
trusting a screenshot of the report. Then follow the supported installation/runbook and
complete the [independent rerun procedure](benchmark-run.md#independent-rerun-acceptance-proposal).
An exact recount checks analysis reproducibility. A fresh game run checks whether the
procedure works elsewhere. Matching trajectories or recovering the exact same win rate
is a stronger claim and is not a requirement established by two launches.

**G40. Publish the experiment, including its constraints.** Provide:

- A benchmark/task card describing intended uses, coverage, omissions, selection,
  witnesses/foils, exposure, success rules and supported controller contract.
- Versioned code/configs, dependencies, exact commands, game build/content, supported
  Windows/WSL setup, hardware, observation/recording settings, provider/backend, prompt,
  memory, sampling and executor details.
- The frozen plan, development search budget, independent counts, all attempt dispositions,
  per-card outcomes and differences, intervals, timing/cost distributions and limitations.
- Scoring/rubric definitions, human review instructions and agreement evidence, judge
  calibration results if used, and the independent recount/rerun record.
- An accessible artifact index, provenance, storage/backup location and retention policy;
  permissions for released code, traces, model outputs and reviewer contributions.

Purchased game content and a supported machine remain prerequisites. Hosted models and
game patches can change or disappear. Document those limits rather than promising
permanent byte-for-byte reproduction. State who designed tasks, tuned controllers,
reviewed outcomes and adjudicated disagreements; disclose relevant affiliations and
selection involvement. A paper needs a completed contribution and an honest comparison
with related work, not just a large leaderboard. Use the
[existing closest-work questions](benchmark.md#research-that-changes-the-design) and
refresh that review before submission.

**G41. Maintain frozen releases alongside development.** Add newly discovered failures
to development regression checks. Keep saturated cards useful for regression or publish
a new suite version; do not silently harden a release and compare new scores with old.
When a scorer or task is wrong, document the defect, affected cohorts and corrected
results for every affected controller. Preserve the original output and explain which
claims are withdrawn or narrowed.

Game-build warnings must be reported to the owner; re-pinning needs their approval.
Run declared reference checks after material game, harness or provider changes and keep
conditions separate until a comparability check supports pooling. A stable model alias
does not prove a stable backend. Monitor judge drift using saved calibration evidence,
without treating a changing judge as a changing controller. Assign a maintainer for
task disputes, scorer corrections and versioned releases.

Possible enforcement: an artifact index and independent recount command, compatibility
checks, versioned correction records, required release fields and a small reference
cohort for drift checks. Local `runs/` paths alone are not a public evidence package;
the current backup/access gap remains recorded in [state.md](../state.md#known-issues).

## Enforce the guidelines through code

**G42. Implement small checks at existing boundaries.** The table maps guidance to
likely homes in this repo. It describes inspected current behavior and proposals,
not a claim that every safeguard already exists or is verified. Apply the cheapest
relevant check, agree important methods with the owner, and test against independent
references and plausible wrong behavior before relying on it.

| Boundary and guidelines | Existing starting point | Proposed enforcement and evidence |
|---|---|---|
| Task and study definition, G1–G12 | `battle/setup.py`, scenarios, queue plan and source fingerprints | Validate resolved task/controller/scorer versions, splits, contrast, cohort and stopping rule; reject a deliberately mixed plan |
| Setup and isolation, G10–G15 | Lobby/start checks, rematch checks, per-episode controllers | Extend agreed live checks to rematch and cross-episode state; perturb hidden data and confirm public inputs stay unchanged; do not claim an external-controller sandbox |
| Outcomes and failures, G15–G17 | `battle/play.py`, `battle/cards.py`, raw result files | Phase-aware immutable endings, assignment reconciliation and agreed failure table; independently classify edge cases before testing |
| Timing and costs, G18–G20 | Trace/ack timing, `battle/report.py`, provider ledgers | Check event linkage, clock domains, silent/no-order cases and all-attempt costs; exercise a known delayed order and inspect the actual effect |
| Statistical reporting, G21–G26 | Card launch deduplication; report launch-level margin differences and Wilson intervals in limited cases | Name the quantity being estimated; add binary paired counts, approved grouping/interval choices and missing-data bounds; compare with independently calculated examples |
| Human labels and judges, G27–G35 | Trace exports, replay and manual review | Versioned evidence packets, preserved independent labels, judge-validation splits, confusion/coverage tables and challenge cases; no calibrated WH3 LLM judge is established here |
| Training separation, G8–G9 and G36 | `battle/export.py`, `gameai/sft.py`, post-training provenance | Check task-family and derived-label exposure; reject deliberately leaked final-test examples |
| Release and maintenance, G37–G41 | Reports, manifests, logs and the proposed outside rerun | Rebuild scores from accessible raw evidence, detect missing artifacts/mixed versions, archive corrections and record outside execution |

Prioritize outcome accounting and public-information checks, then trustworthy timing,
grouped analysis and recounting. Add judge automation only if manual review volume
justifies it. Do not build a framework merely to satisfy this table.

Known current differences matter: the card and generic report use different denominators;
the proposed constructor/post-ending failure handling is not yet implemented; generic
`stats` grouping is insufficient for these comparisons; and gameplay signature checks
and outside reruns remain pending. See the
[scoring contract](benchmark.md#outcomes-measures-and-comparison) and
[correctness proposals](benchmark.md#correctness-checks-to-agree). A new guide does not
retroactively verify those features.

## Adapt common evaluation advice to WH3

| Common advice | WH3 adaptation and reason |
|---|---|
| Use human preference as ground truth | Use trusted engine/state evidence for outcomes. Humans define and audit tactical labels; preference does not change a battle ending. |
| Match the reference answer or trajectory | Accept alternate legal tactics. A witness shows feasibility; exact imitation would penalize useful adaptation. |
| Make evaluation deterministic | Check/reset declared conditions and preserve variability. Game RNG seeding and deterministic replay are not established. Pausing would remove the real-time problem. |
| Count many examples cheaply | Calls, units and frames share a battle. Rematches share a launch. Count independent groups and task coverage, not rows. |
| Report the best of several attempts | Primary performance concerns one assigned live attempt. `pass@k` measures at least one success in k attempts; `pass^k` measures all k succeeding. Use only for an explicitly declared repeated-attempt question with all costs, a valid estimator and dependence assumptions; do not exponentiate a pooled heterogeneous win rate. See [τ-bench](https://arxiv.org/html/2406.12045v1). |
| Remove infrastructure/API problems | Proven setup failures may be invalid experiments. Provider outages and retries can be part of the controller's deployment reliability; follow the declared failure rule. |
| Use answer probabilities to reduce score noise | Probability of a reference order is not probability of winning. Multiple actions can be valid and outcomes depend on their timing and later control. |
| Lower temperature to stabilize scores | That changes the controller. Evaluate the declared deployment settings and report actual stochasticity. |
| Generate many synthetic examples | Use synthetic records for parser/scorer challenge cases. Validate generated scenarios in the game; imagined battles cannot establish feasibility or policy strength. |
| Filter difficult data as probable mislabels | Investigate against the engine and task rule. [Dataset Cartography](https://arxiv.org/html/2009.10795v2) studies model-dependent training dynamics, not a license to delete hard tactical losses. |
| Use adaptive subsets or predict a full-suite score | Such methods need validated historical structure. [tinyBenchmarks](https://arxiv.org/html/2402.14992v1) discusses distribution-shift limits. A small directly measured WH3 suite is more defensible today. |
| Normalize all graders into one leaderboard | Keep per-card success, reliability, timing, cost and tactical evidence distinct. Any aggregate needs frozen weights and sensitivity analysis. |
| Compare with a human playing normally | A GUI player and a structured-state controller have different information/actions. Disclose the mismatch or build a matched-interface study before claiming human parity. |
| Judge every step or require an LLM judge | A complete battle is the outcome unit. Selective trace review is diagnostic; reliable code can score much of the task without another model. |
| Evolve rubrics as the agent improves | Useful in development or training; freeze the evaluation rubric and version any later changes. |

## Use a short study declaration

Keep this with a planned experiment, not as a new hierarchy of bookkeeping files.
Fill every unresolved field before running a confirmatory comparison. Values below are
examples of the kind of statement needed, not authorization or a new frozen protocol.

| Field | Example for an advice comparison |
|---|---|
| Question and scope | Does adding a specific withdrawal explanation help one model on a frozen contact-victory card at natural latency? |
| Arms | A: rules-only prompt; B: same prompt plus the declared advice. Same model/backend, executor, sampling and information contract. Prompt length is part of this intervention. |
| Task/reference | Name card version, validated start settings, witness and functioning shortcut foils. Preserve historical c1 separately. |
| Primary outcome | Success under the named card and failure rules; engine ending retained separately. |
| Sampling | Predeclare fresh-launch count, within-launch order, repeats, time blocks and missing-partner treatment. |
| Precision | Choose a useful gain and interval/power target from the engineering decision; estimate required launches from pilot uncertainty. |
| Secondary evidence | Applied order age, actual withdrawal/contact evidence, refusals and total cost. Commentary alone supplies no execution label. |
| Controls and exposure | Both arms know the same public rules; record task exposure and reserve supported variations before tuning. |
| Stop and replace | Fixed cohort with explicit setup-failure replacement and operational caps; no favorable-result stopping. |
| Correctness | List agreed checks and passing revisions, plus unverified dependencies that limit the claim. |
| Interpretation | A gain supports the effect of supplying that advice in these conditions. It does not isolate pure knowledge, prove all wins used withdrawal, or establish a general model ranking. |

Before release, a reviewer should be able to answer five questions from the artifacts:
What exactly was compared? Did the declared game and information boundary hold? Where
did every assigned attempt go? Does the uncertainty match the sampling? Could someone
recount the result and follow the runbook? If any answer is missing, narrow the claim or
finish that work before presenting the result as a reusable benchmark.

## Sources and their use

All twelve requested sources were accessible on 2026-10-20. The table records the
methodological content used; the WH3 rules are domain-specific recommendations, not
findings from those articles. Linked research was followed selectively where it changes
a design decision, rather than treating every bibliography entry as a requirement.

| Requested reading | Main contribution to this guide |
|---|---|
| [Weng, Thinking about High-Quality Human Data](https://lilianweng.github.io/posts/2024-02-05-human-data-quality/) | Reviewer quality, training, disagreement and the limits of model-based label cleaning; G27–G29 and the adaptation table |
| [Yan, How to Write Data Labeling Guidelines](https://eugeneyan.com/writing/labeling-guidelines/) | Clear task definitions, examples, decision steps, tools and unsure labels; G27–G28 |
| [Wolfe, Using LLMs for Evaluation](https://cameronrwolfe.substack.com/p/llm-as-a-judge) | Scoring formats and judge biases; G30 and G32 |
| [Husain, Using LLM-as-a-Judge For Evaluation](https://hamel.dev/blog/posts/llm-judge/index.html) | Expert-led error analysis and judge calibration; G29–G31. Read the page updated September 2026. |
| [Yan, Evaluating the Effectiveness of LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/) | Choosing a judgment format and validating it with the appropriate metrics; G30–G33 |
| [Wolfe, Rubric-Based Rewards for RL](https://cameronrwolfe.substack.com/p/rubric-rl) | Criteria, reward construction and evolving training rubrics; G34–G36 |
| [Rao and Callison-Burch, Autorubric](https://arxiv.org/abs/2603.00077) | Criterion-level evaluation, abstention and configuration-specific reliability; G33–G35. Inspected v3, 2026-08-07. |
| [Wolfe, Applying Statistics to LLM Evaluations](https://cameronrwolfe.substack.com/p/stats-llm-evals) | Sources of variation, small samples, paired inference and study planning; G21–G26 |
| [Miller, Adding Error Bars to Evals](https://arxiv.org/abs/2411.00640) | Clustered observations, paired differences, variance and power; G21–G26. Its large-sample/task-sampling assumptions need the WH3 qualifications above. |
| [Wolfe, The Anatomy of an LLM Benchmark](https://cameronrwolfe.substack.com/p/llm-bench) | Task sourcing, quality audits, coverage and maintenance; G4–G9 and G41 |
| [Wolfe, Agent Evaluation](https://cameronrwolfe.substack.com/p/agent-evals) | Distinct tasks, trials, traces, outcomes, graders and controller scaffolding; G1–G3, G13–G20 and G39–G41 |
| [Anthropic, Demystifying evals for AI agents](https://anthropic.com/engineering/demystifying-evals-for-ai-agents) | Outcome checks, trial isolation, trace inspection and complementary review methods; G2, G13–G15 and G30. The supplied URL redirects to the research page. |

Selected primary work followed from these readings and their cited research:

| Source | What it adds and where its scope stops |
|---|---|
| [Röttger et al., Two Contrasting Data Annotation Paradigms](https://arxiv.org/html/2112.07475v2) | Distinguishes applying a common rule from collecting different opinions; its subjective NLP setting informs human review, not WH3 outcome scoring |
| [Zhang et al., A Taxonomy of Rater Disagreements](https://arxiv.org/html/2311.04345v1) | Investigate reasons for disagreement rather than collapsing every label to a majority; taxonomy comes from toxicity annotation |
| [Swayamdipta et al., Dataset Cartography](https://arxiv.org/html/2009.10795v2) | Hard/ambiguous training examples can be useful; model difficulty is not independent proof of a wrong benchmark label |
| [Zheng et al., Judging LLM-as-a-Judge](https://arxiv.org/html/2306.05685v4) | Direct evidence of judge biases and mitigation limits in dialogue; no measured WH3 judge accuracy |
| [Shankar et al., Who Validates the Validators](https://arxiv.org/html/2404.12272v1) | Criteria can change as people inspect examples; refine during development, then freeze and audit implementation |
| [Gunjal et al., Rubrics as Rewards](https://arxiv.org/html/2507.17746v2) | Expert-grounded reward criteria and aggregation choices; medical/scientific experiments do not establish battle-control gains |
| [Bowyer et al., Position: Don't Use the CLT in LLM Evals With Fewer Than a Few Hundred Datapoints](https://arxiv.org/html/2503.01747v2) | Small-sample uncertainty and limitations of familiar large-sample estimates; no cure for unrepresentative tasks or dependent trials |
| [Abadie et al., When Should You Adjust Standard Errors for Clustering](https://arxiv.org/html/1710.02926v4) | Clustering follows the sampling/assignment design and inference target; choose WH3 groups from the experiment |
| [Terminal-Bench](https://arxiv.org/html/2601.11868v1) | Concrete task packages, reference solutions and integrity review; containerized terminal tasks differ from a live proprietary game |
| [Agentic Benchmark Checklist](https://arxiv.org/html/2507.02825v1) | Separate task validity, outcome validity and reporting; checklist completion is not empirical verification |
| [τ-bench](https://arxiv.org/html/2406.12045v1) | State-based outcomes and repeated-attempt reliability measures; its independence assumptions cannot be copied onto rematches |
| [OSWorld](https://arxiv.org/html/2404.07972v1) | Initial-state setup, task-specific outcome checks and independent review; GUI/VM reset conditions differ from our interface |
| [MMLU-Redux](https://arxiv.org/html/2406.04127v3) | Auditing and correcting evaluation data can change conclusions; its error rates are not estimates for WH3 |
| [tinyBenchmarks](https://arxiv.org/html/2402.14992v1) | Efficient subset selection depends on historical performance structure; validate before using it to estimate an unplayed suite |

The sources differ in useful ways. Product-oriented judge guidance starts with one expert
and simple pass/fail labels; publication-quality claims also need independent review and
uncertainty. Rubric frameworks permit richer scales, but their reliability must be shown
per criterion. Statistical variance-reduction advice can change the evaluated policy or
assume task sampling we do not have. Agent benchmarks may omit failed API runs, whereas
our natural-latency track deliberately measures serving reliability. The governing choice
is the declared WH3 question and contract, not a technique's popularity.
