# Owner direction

The owner's dated directions recorded so far, newest first within each heading;
superseded ones are marked. New directions are added here; older memory notes and pages
may repeat some. Status lives on [state.md](state.md).

Both games:
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
