# Owner direction

The owner's dated directions recorded so far, newest first within each heading;
superseded ones are marked. New directions are added here; older memory notes and pages
may repeat some. Status lives on [state.md](state.md).

Both games:
- 2026-10-21 (autonomy strategy), verbatim: "Read docs/autonomy.md. We've been trying to
  come up with a strategy that we can use to keep you making at least some progress
  autonomously while I haven't had the time to review progress and make decisions, in order
  to minimize the situations where I would be a bottleneck. I will have to review things,
  don't get me wrong, but we should be able to find a way to make the most of your time until
  I'm able to review something new. We need to be careful to not simply add errors or
  bloat/garbage/slop, which is very easy to do. Let's refine our strategy for that as much as
  we can." Refinement is not approval of the proposed standing rules or a new game window.
- 2026-10-20 (late, working while away), verbatim: "Let's take note of that, but more than
  that, let's actually try to come up with guidelines for you to follow when trying to make
  progress while I'm not around without keeping me as a bottleneck unless critical. You can
  also do additional things towards features on our roadmap if it's safer than other
  options, such as starting to test the infrastructure for WH3's campaign mode. Note that
  I'm not telling you to design the benchmark for the campaign, as that would be an example
  of situation where I have to be the bottleneck (although you can try different options,
  test some things ahead of time, give me pre-tested suggestions, etc), but instead to first
  build and test the features that can be counted as objective, easier to verify."
  Proposed as [autonomy.md](autonomy.md), pending the owner's yes.
- 2026-10-20 (late, review bottleneck), verbatim: "For sure my review time has been a
  bottleneck, it's true. But there has to be more than you can do to help us continue to
  make reliable progress. Let's think more deeply about that and try to come up with ideas
  to keep making legitimate progress while I'm still not able to proceeed with reviews and
  decisions". Ideas and their review: `runs/autonomy-20261020/`.
- 2026-10-20 (writing): use simpler, more concrete and intuitive language from now on;
  avoid inflated wording and unnecessary jargon. Record the preference in shared guidance.
- 2026-10-19 (artifact locations): put task-created files only inside the repository;
  stop polluting the environment root. Remember this in shared guidance and leave earlier
  garbage for a later cleanup pass.
- 2026-10-19: one bounded WH3 maintenance pass, up to three demonstrated issues, no product
  features or large paid evaluations. Agreed component verification for mailbox identity
  and finite order fields (real Python/Lua components plus a simulated play-loop regression);
  actual game effects remain unverified. Preserve shared Codex/Claude guidance and use an
  independent diff review. Stop after the selected improvements and evidence report.
- 2026-10-18 (evening): the OpenRouter account now has $50.38 of credit, shared by both
  games; "let's spend it carefully though".
- 2026-10-18 (closing the goal): unit tests suffice to verify the missing-ledger refusal;
  "we will need to strike a good balance in order to verify/test important things while
  also not polluting the codebase with a bunch of slop tests". The game smoke check of the
  16k cap and relay change waits; the goal is done.
- 2026-10-18 (goal: improve the codebase before anything else): (1) clean up accumulated
  files and branches; (2) find low-hanging fixes for excessive bookkeeping, unfounded
  claims, token use and garbage, starting simple and minimal, and look for infrastructure
  and verification improvements; (3) let the game auto-update and only warn the owner;
  later, find a way to test whether a patch changes benchmark results before approving
  it; (4) note that OpenRouter backends are unpinned, to address later; (5) priority: the
  WH3 benchmark first, then Slay the Spire; post-training is secondary; (6) post-training
  will try RL and other methods, not only SFT, and trace data must suit them in advance;
  (7) raise the output cap to 16k tokens; (8) hard rule: a feature whose repeatable test
  the owner has not explicitly discussed may have issues; be careful making claims or
  building on unverified things ([AGENTS.md](../AGENTS.md#verification-hard-rule)).
- 2026-10-17 (19:10 UTC, away): "Review the repo in terms of its preparation for
  post-training experiments. Review whether we're collecting data properly, check and
  improve the quality of related code, prepare the structure required to fine-tune an open
  model with OpenRouter (and do an initial minimal test run for this, with both games)."
  Shortly after: "run more of the planned TW3 games in the background". At 23:24 UTC:
  "wrap it up after the current battle ends". Done: [first end-to-end test](posttraining.md#first-end-to-end-test-2026-10-17).

WH3:
- 2026-10-21 (on return, 12:20, answering the three inbox questions): (1) the starting
  set's screen: "Yes, run it", which also agrees its reading rule and the two markers as
  [tactic-cards.md](twwarhammer3/tactic-cards.md#the-starting-set-proposal-2026-10-21)
  words them; run on the next free night; (2) the defender prompt: "Tell models", a
  contact-scoring scenario field and one logged prompt version for `llm`, `llm_rules` and
  `commander`; (3) the failure rule: "Agree and merge" `wh3-keep-engine-ending` as harness
  b47.
- 2026-10-21 (away window from 02:20, about 10 hours), verbatim: "Continue to make progress
  on the WH3 benchmark until I return in like 10 hours. Check our relevant documentations
  before starting like autonomy.md. Remember that progress could count as many different
  things such as improving our definitions, documentations, tests, infrastructure,
  research, data collection, etc. Let's make the most of this time. For instance, have we
  decided on a set with a least a few battles that we should start with for our
  benchmarking? Do we have a strategy on how to decide that? Do we know what we're trying
  to achieve from each battle and how we're going to test them? There's no shortage of
  useful things that we can do until I return, so I'll leave you to it. Don't add slop,
  don't accumulate garbage. Keep our code and docs clean." Proposed answer: the
  [starting set](twwarhammer3/tactic-cards.md#the-starting-set-proposal-2026-10-21).
- 2026-10-20 (guideline review): review evaluation-guidelines.md against the twelve
  readings and their cited work; improve it, say how each rule could be enforced in code,
  use simple language, and note common eval practices that do not apply or must differ for
  WH3. Guidelines only, no code changes; summarise every change at the end.
- 2026-10-20 (evaluation guidelines): read the twelve supplied evaluation resources and
  relevant cited work; write comprehensive, concrete benchmark guidelines covering
  definition, methods, reliability, interpretation, possible code enforcement and WH3
  exceptions. Documentation only; keep all writing and research artifacts in this repo.
- 2026-10-20 (scope review): assess whether the benchmark has a clear scope and a credible
  path to being strong, useful, reliable, interesting and distinctive; improve definition
  and documentation where needed, with no implementation. The release boundary and
  unresolved evidence belong in the [benchmark definition](twwarhammer3/benchmark.md).
- 2026-10-20 (benchmark definition): refine the objective and plan, reduce uncertainty,
  make correctness checks and abstract ideas concrete, and use relevant frontier research.
  Keep it concise and simple; research and documentation only, no implementation.
  [Current definition](twwarhammer3/benchmark.md).
- 2026-10-20 (research follow-up): expand and organize the robot-team research notes and
  plans using relevant robotics, LLM, agent, benchmark, evaluation and post-training
  research. Keep concrete uses, comparisons and limitations so the ideas remain useful
  for later experiments. Recorded in the [research guide](twwarhammer3/robot-team-research.md)
  and [Empire plan](twwarhammer3/robot-team-plan.md); documentation only.
- 2026-10-20 (night, goal, away until 11:00): keep making progress toward the WH3
  benchmark, but spend less time perfecting one battle and explore a larger range of
  options; small battles to understand units, early tests of larger battles for the
  framing of an army as a robot team that must stay coordinated as its environment
  changes; specialize mostly in Empire units so the collected data can post-train an
  Empire specialist (other factions for specific challenges such as the Orc chariot);
  use best judgement, record design decisions and risks for review. Taken as the
  [Empire set](twwarhammer3/empire.md) and its night queue.
- 2026-10-20 (research plan): keep the robot-team framing and write a rough plan in the
  repository, with a concrete battle example, what to observe, uncertainties and risks.
  [Draft](twwarhammer3/robot-team-plan.md); this request is for research planning.
- 2026-10-19 (integration review): implement the agreed UI/modding cleanup plan, including
  structural simplification where useful. Apply declared lobby settings automatically;
  compare context setup with the click route, disturb settings, exercise unavailable units,
  insufficient funds and reserves, then clear/restart/load and compare lobby with battle
  startup. Real Python/Lua component checks suffice for request isolation, failure reporting,
  scheduling, startup-query errors and session cleanup. Free live checks only, unpaused at
  1x; keep benchmark/paid jobs stopped. Document new battle API candidates without exposing
  new policy signals. Restore pre-review settings after diagnostics.
- 2026-10-19 (army setup goal): find and use the lobby's saved-army save/load controls
  and per-unit Increase/Decrease experience controls; keep the code simple and clean.
  Agreed verification: save a known army, change it, restart and load; compare types/counts/
  ranks, exercise increases/decreases and compare lobby with battle-start ranks/stats.
  Done: [b41](twwarhammer3/log.md#2026-10-19-saved-armies-and-experience-harness-b41),
  check passed at `c768460`.
- 2026-10-19 (evening, during the b40 round): a battle can also be calibrated by giving
  units different experience ranks, since units gain stats as they gain ranks; in the lobby,
  clicking a unit on the army selection page shows two small buttons under its card,
  "Increase experience" and "Decrease experience". Registered as a card knob in
  [tactic-cards.md](twwarhammer3/tactic-cards.md#design-rules-from-s1-s11); implemented in
  b41 and used in the Empire rank-5 candidate. The
  owner also asked why the chariot battle is repeated so often (answered in the session: the
  repetitions are the sampling behind each cell's rate, and the card is the template for the
  next ones; breadth comes next) and then: "Let's wrap up the runs for now after the current
  battle ends" (the plan-stop file ended the round after that job). For later: the lobby
  rebuilds both armies unit by unit on every launch, which wastes time; the game has a button
  to save an army setup and another to load it, to be found and used
  ([integration.md](twwarhammer3/integration.md#unverified)). Done: both found and used in
  b41 (above).
- 2026-10-19 (evening): "Continue to make progress on the benchmark. You're allowed to run
  battles and spend some API budget as needed. Make sure you understand the benchmark and the
  results well before drawing strong conclusions." Taken as the go-ahead for second-pass
  decisions 1 and 2 (witness v2, the prompt sentence and GLM's rerun) and P5's Kimi
  remainder, under delegation; decisions 3-5 still wait
  ([log](twwarhammer3/log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40)).
- 2026-10-19 (afternoon): "think more deeply about verifiability and reproducibility for our
  WH3 benchmark" and improve it, keeping the code clean and lean: are knowing a tactic and
  executing it checked properly; a battle must be guaranteed winnable and let the model
  exercise exactly the skill measured; battles are real time and API response times vary;
  refer to similar research projects for ideas. Done as a review with proposals
  ([log](twwarhammer3/log.md#2026-10-19-benchmark-verifiability-review)), then as a second
  pass that recounted them, fixed the card reader (b39) and left five decisions
  ([log](twwarhammer3/log.md#2026-10-19-benchmark-verifiability-second-pass-harness-b39)).
- 2026-10-19 (research follow-up): refine the robotics documentation with concrete
  comparisons, clean integration into this codebase, benefits, risks and viability checks;
  continue looking for high-value ideas. Documentation only.
- 2026-10-19: research the army as a robot body: code as policy, fast learned unit control
  (including VLAs and diffusion), and a slower planner. Write useful ideas for benchmark
  design and model performance, grounded in research and the current harness; consider
  risks and unsupported assumptions. No implementation.
- 2026-10-19 (night, later): "recent JEV models seem to work well for situations that
  require low-latency, like our battles? We should remember to experiment with them at some
  point". Possibly Jev (TypeSafe: structured state to typed decisions, vendor-reported
  70-500 ms; one web search, unchecked): a candidate fast executor (latency.md rung 5).
- 2026-10-19 (night, during the overnight round): "I'm still very interested in seeing if we
  can approach the problem of interpreting an army as detachable robot parts, and control it
  using ideas inspired by recent robotics research with LLMs"; keep tracking it (the
  2026-10-18 evening items 2-3; [robotics framing](twwarhammer3/latency.md#robotics-framing)).
- 2026-10-18 (evening, goal, away), after the benchmark review: (1) the gap between knowing
  a battle tactic or concept and executing it in real time under variable latency looks
  relatively unexplored and fairly unique to this game: take advantage of it and start
  measuring and investigating it specifically; (2) think of a WH3 army as "detachable
  pieces" of a robot body and draw on robotics research to make the project more
  interesting and relevant; (3) the owner recalls an explored agent-swarm structure (a
  stronger model making the larger plan while smaller sub-agents at different timings
  handle execution, similar to robotics control) and wants it considered for testing
  later; (4) at least one harness should make the model aware of its own latency; (5) keep
  working on a path to fine-tuning a specialist army, comparing several fine-tuning
  methods; (6) "Wins have to account for variable latency. Real-life situations can't
  slow down if a model fails to respond on time, and neither can our models here";
  (7) keep track of these notes and keep refining the plan, researching options and
  making progress toward the benchmark while away.
- 2026-10-18 (afternoon, goal, away): "at least a single good, reliable benchmark"; built
  as the chariot card ([log](twwarhammer3/log.md#2026-10-18-the-chariot-card-harness-b32-to-b34)).
- 2026-10-18 (night, later): multi-agent command delegation was discussed before, but only
  one model plays at a time; eventually also benchmark harnesses (multi-agent, MCP and other
  features), not only models. Delegation was never built: [controllers.md](twwarhammer3/controllers.md#designs-not-built-yet)
  item 4.
- 2026-10-18 (night, goal, away until 13:00 UTC): "Continue writing the definition for the
  benchmarks. Run them overnight until I return at 10 AM ... Make the most of this time.
  Analyze the benchmarks and ensure their utility. Try to identify benchmark opportunities
  that are unique to Total War Warhammer battles."
- 2026-10-18 (night): define minimal battles that each test whether a model can apply one
  tactic, won only if it applies that tactic correctly; an evolving list of battle tactics,
  single-unit mastery, concept knowledge, key decisions and situation types, with large
  armies for context length later ([tactic cards](twwarhammer3/tactic-cards.md)). Earlier
  the same night: overnight runs had been "mostly pointless battles without really knowing
  what we want to achieve with them".
- 2026-10-17 UTC: cleared the active goal and asked to wrap up. Stop further game/API
  jobs, save the completed calibration evidence and leave the remaining plan pending.
- 2026-10-16 (trace-export goal): implement the offline exporter for future post-training.
  Complete as [b14](twwarhammer3/traces.md); no new game/API jobs or training.
- 2026-10-16 (night): small scenarios approved to try; ladder continues with a cheaper
  reference model for now (expensive models later); write a trace exporter and store
  reasoning text. Exporter/capture are complete as b14; the small scripted tranche is
  recorded in b15-b17, while its model checks and the cheaper ladder remain unplayed
  ([decisions](twwarhammer3/benchmark.md#owner-decisions-and-next-tranche-2026-10-16-night)).
- 2026-10-16 (evening, latest): benchmark every reasoning mode of every model in each
  scenario; verify each model's real modes first (some open-weight models are only
  on/off) ([model coverage](twwarhammer3/benchmark.md#current-proposal-calibrate-before-a-broad-model-comparison)).
- 2026-10-16 (evening, later): mostly many small battles that each test one or two
  specific things (e.g. two cheap cavalry units against one braced pikeman unit, if
  winnable: feint and flank), plus a few larger battles for context length and
  scale-only problems; diversity, quality and room for unexpected behaviour
  ([scenario mix](twwarhammer3/benchmark.md#current-proposal-calibrate-before-a-broad-model-comparison)).
- 2026-10-16 (evening): make each scenario maximally difficult while still demonstrably
  winnable; fewer high-quality scenarios beat redundant ones that waste compute. Armies,
  map settings etc. may be modified to calibrate
  ([difficulty target](twwarhammer3/benchmark.md#current-proposal-calibrate-before-a-broad-model-comparison)).
- 2026-10-16 (resume): implement OpenRouter and the three chosen models, then continue
  improving benchmark calibration and the report within the existing budgets.
- 2026-10-16 (OpenRouter): the owner stored an OpenRouter key and set a separate $50
  budget. Requested support and three leading open-weight model API checks, then
  clarified: stop after cleanup and design this turn; no implementation or paid calls.
- 2026-10-16 (after M1): planning only. Keep the core provisional until the strongest
  models have been tested; current scenarios may be too easy for them. Calibrate
  challenges and extract more useful evidence before spending on another large model
  comparison ([proposal](twwarhammer3/benchmark.md#implementation-plan)).
- 2026-10-16 (03:28 UTC): the WH3 API cap rises to $52 (Spire keeps its own $25). Overnight,
  prioritize work that needs the game running, since a fullscreen battle makes the
  computer awkward to use during the day.
- 2026-10-16 (03:20 UTC): delay the custom battles (the evacuation pilot) for much later in
  the plan as a low-priority item, and proceed with other things.
- 2026-10-16 (planning note): less is more; a smaller set of high-quality scenarios, each
  answering a distinct question ([scenario design](twwarhammer3/benchmark.md#scenario-design)).
  Report feedback is recorded in [reports.md](twwarhammer3/reports.md#pending-report-notes).
- 2026-10-16 (implementation): approved a compact core of 6-8 distinct decision problems;
  variants do not count as new coverage. Implement siege defence, survival and conquest
  plus one custom battery-evacuation pilot; narrow interface extensions and custom
  scripting are allowed. Audit existing families for redundancy. Later self-comparisons
  distinguish army/control workload from prompt length and useful history.
- 2026-10-15 (playmaking): retain difficult battles only when they give a controller
  meaningful options to exploit advantages and mitigate disadvantages. Exploratory runs
  should inspect those opportunities; redesign or drop scenarios with no credible plays,
  preserving their evidence. This applies to existing challenges too.
- 2026-10-15 (implementation): authorized the first three steps: controller integration,
  common measures and one report. Scenario expansion remains next.
- 2026-10-15 (refined): planning only at that stage. Prioritize scenarios that look and play very
  differently: varied armies, siege, survival, conquest and other modes. Start with
  general measures (kills, survivors, objective time, etc.); scenario-specific points
  are a possible future improvement. Play 2-3 exploratory battles total per new scenario,
  with deeper testing later. Keep difficult odds, no win-rate admission campaign, and
  one HTML report for the whole benchmark (supporting files allowed). Interface versions
  remain metadata; added-delay experiments wait. See the
  [plan](twwarhammer3/benchmark.md#implementation-plan).
- 2026-10-14 (benchmark steering): specialist anchor units and faction-specific mechanics
  should drive scenario design. Prioritize extreme tactical problems (cavalry against
  anti-large, caster-led forces, difficult sieges, commanding/fighting Skaven swarms),
  meaningful creative choices and battles worth watching; well-rounded armies can follow.
  Small armies on either or both sides are equally suitable; high funds and large
  rosters are not requirements. Start the first specialist prototypes compact.
- 2026-10-14 (night, sieges): benchmark who holds the victory points over time and the
  supplies left unspent; both are now measured per episode.
- 2026-10-13 (benchmark idea, the owner's words): "Eventually we could turn this game into
  some kind of serious LLM benchmark? For now I'm just registering this here. Could try to
  create certain challenge scenario battles where the opponent side is stronger, and see
  how well different models perform and whether they discover certain key insights
  required to win these battles. Eventually these challenge scenarios could even be
  AI-generated themselves."
- 2026-10-13: an API model plays real-time battles, with the order delay measured; control
  through an in-game mod, never screenshots or desktop input; a hard $25 cap (now $52) on its own
  ledger, `runs/twwarhammer3/llm-spend.jsonl`. Battles always run unpaused at 1x.
- 2026-10-13 (evening): an asynchronous `commander` over scripted `skills`, beside the
  direct `llm`; the other designs wait in [controllers.md](twwarhammer3/controllers.md).
- 2026-10-13 (late), *the random-draw part superseded on 2026-10-16 by mostly small focused
  scenarios (above); very hard AI difficulty and other battle types still stand*: evaluate
  on paired random draws (`--scenario random`, the same seeds
  for every controller, races drawn, armies autogenerated) at AI difficulty very hard;
  fixed scenarios only for quick diagnostics. Other battle types next.

Slay the Spire:
- 2026-10-12: complete runs by a frontier API model (`gpt-6-luna`, low effort), scaffolding
  found by autoresearch from observed mistakes; a hard $25 cap on `runs/llm-spend.jsonl`.
- 2026-10-12: interest in an open StS1 benchmark, since SpireBench's code is not public.
  Later, a remotely trained open-weight model (Qwen3.6-35B-A3B, then GLM-5.3, RL on Tinker).
- 2026-10-11: PPO paused for language-model post-training, itself paused for full runs.
