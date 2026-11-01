# Owner direction

The owner's dated directions recorded so far, newest first within each heading;
superseded ones are marked. New directions are added here; older memory notes and pages
may repeat some. Status lives on [state.md](state.md).

Both games:
- 2026-11-01 (control methods on the page): "Find a good way to represent different army
  control methods that we will implement. For now we have the basic one, and then GaP. We need
  clean visuals for those too." Read as: the [page](multi-agent.html) draws each control method
  as it is built, now the basic one (the model picks the orders at each decision) and GaP
  (models write graphs that code plays); drawing GaP in the page itself rests on JUDGEMENT?
  docs/multi-agent.html GaP drawn in the page.
- 2026-11-01 (visual docs): "I like the general idea of helping me quickly understand how the
  code works in a visual, concrete, simple, intuitive way. That's by far the most important
  thing about that." Earlier (2026-10-31): make it "the main way I understand the structure of
  our codebase and execution of the code", keep it current as part of the factory, and avoid
  updating it "after every single commit". On the [plan](how-code-works-plan.md): "My answers:
  1a, 2a, 3a. About the three questions that need my 'yes', I agree with them." So:
  - `multi-agent.html` becomes a "How the code works" map of the whole repo, plus short
    stories built on real battles; today's tabs are frozen as an appendix;
  - refreshes run as away-window upkeep or on request, at most weekly and at most 100 API calls
    each;
  - small excerpts of recorded battles are committed in `docs/`, publicly: a standing exception
    to "run evidence stays out of Git";
  - three 2026-10-31 build answers change: a flagging script in `check.py` with 2-3 tests of the
    script; planned parts hidden by default; status colours behind a switch.

  The plan's other defaults were not answered one by one.
- 2026-10-31 (GaP): implement the existing plan autonomously; initial minimal implementation,
  interchangeable battle controllers, clean code and proper tests. Up to $5 in paid calls,
  using a cheap Anthropic model. Approved first library: existing move/hold/engage/shoot/charge
  tactics with public-state statuses, contact and target selection; no new formation or
  flanking tactics. Agreed offline typing/lifecycle/concurrency/boundary checks with planted
  wrong versions, canned author/revision replies, then live movement and contact/charge at
  1x without strength claims. PC available tonight. Benchmark and restore choices deferred.
  Follow-up (2026-11-01): "Include graph authoring and between-battle revision now."
  Also approved extending the contact check from 360 to 540 seconds and a fresh rerun,
  preserving the failed run and every effect criterion: "Yes, extend the contact limit and rerun."
  Follow-up (2026-11-01): "Continue to work on GaP, accrording to our plan. Run overnigjt
  using your best judgement. If you finish early, keep going with other tasks planned".
  Viewer check (2026-11-01): "Use this check" — raw graph/node/order/witness mappings,
  planted wrong mappings, then both saved battles exercised in a browser.
  Live target-preference check (2026-11-01): "I agree with the proposed live verification
  method" — delayed/stale replies, cancellation, ownership and independent progress
  offline, then a bounded fresh 1x probe of two eligible target preferences and their
  dispatched orders/public target readings. Existing cumulative $5 cap; no strength claim.
  Author-initiation check (2026-11-01): "Ok, we can proceed with this solution temporarily"
  after the concrete explanation: infantry's plan must let it start combat before anyone
  is already fighting; cavalry may wait. Catch circular waiting before launch and give
  the author its existing repair chance. Public starting-state check only; no live-effect
  or strength claim, and no permanent benchmark rule.
  Live follow-up (2026-11-01): "Yes, the PC is free now. Let's finish this" — one fresh
  battle, up to 30 minutes, checking infantry starts combat and cavalry joins after contact.
- 2026-10-31 (late, Anthropic provider's three "needs your yes" items): "I agree with all 3."
  They were: `test_wh3_cli.py`'s ledger test parametrized over OpenRouter and Anthropic (its
  asserts compare with the parameter); `test_spire_cli.py`'s play test gaining a spend check
  (`551b514`); the two transport plants in `tests/plants.toml` pointed at the moved header
  parsing (`563483a`). Approval is not verification.
- 2026-10-31 (factory efficiency): "consuming time from my system during an automated process
  is fine, and is very different from consuming time from myself as a reviewer, which is the
  part that matters the most." The owner asked to put this distinction in the factory's
  definition so it is remembered. Applied: [workflow.md](workflow.md) makes reducing the
  owner's attention and manual review work the main efficiency goal, separate from machine runtime.
- 2026-10-31 (evening, Anthropic provider): "Implement docs/anthropic-provider-plan.md." The
  owner's key is "scoped to 'Organization'" and needs an `anthropic-workspace-id` header; "It
  expires on April 1st 2027 and has a budget of $200 that we will use very carefully."
  Five of the plan's six recommendations were implemented as written; the key's budget stands
  in for recommendation 4's workspace spend limit ([plan](anthropic-provider-plan.md)).
- 2026-10-31 (02:10, long autonomous run, the owner's words): "We don't have an actual
  cutoff. We should have a lot of work ahead such that you can just keep running without a
  time limit, until every reasonable task involves a pending decision from me. I can review
  things as we go, but we should limit the situations where I'm a blocker. Things involving
  money can be a blocker, but most other things we can just try, see what happens, and if
  needed we can undo them later, branch out, etc. But for now we just need to plan ~10h of
  work since by then I'll be back to discuss more things". Plan: `runs/overnight-20261031/brief.md`.
- 2026-10-31 (factory assessment): "I won't have time to review it manually for now, but
  let's continue to assess it and look for potential improvements." "Remember that the
  factory's goal is to work more independently and reliably, with trustworthy automated
  verification to prevent errors." "The process needs to be aware that it can contain
  errors especially in places that I haven't reviewed manually (which is essentially the
  entire codebase at the moment)". Continue bounded offline assessment and repairs; existing code and checks
  remain fallible, and new checks remain proposed until explicitly agreed.
- 2026-10-30 (away): "I'll be away for a few hours at least. Use your best judgement until then".
- 2026-10-30 (commit guard): "Enable it (Recommended)" to adopting `commit-guard-draft`
  (`6958d6f`) and configuring the git hook. The question stated that either session's edits
  invalidate the pass and require another `check.py` run. Approval is not verification.
- 2026-10-30 (light factory refinement): continue improving the factory so vague requests
  become specified, implemented changes and repository changes go through it. Continue while
  reasonable improvements remain, without bloat or overengineering; Claude Code is implementing
  native multiplayer in parallel.
- 2026-10-30 (01:55, planning the night run): "No spire. WH3 is our priority. We need to
  continue working on the light factory first though and make sure it's as good as possible
  so we can have more trust in these autonomous runs. About the quick items, yes to all."
  The quick items (`runs/overnight-20261030/brief.md`): kill the leftover test process
  159910; record the 2026-10-26 Land checkpoint pass at `d3ba6aa` in agreed-checks.md; retire
  the 5 markers in Spire log history (`docs/spire/fullrun/log.md`); make state.md's 120-line
  rule a `check.py` warning.
- 2026-10-30 (standing writing preference): keep all writing simple, concise, concrete and
  nicely written, including status summaries and decisions presented to the owner.
- 2026-10-29 (late evening, the four items left for the owner): "1. Now is fine. 2. We can
  leave a reminder for Codex to take care of its own hooks and Skills later. 3. I ran the
  command myself. 4. Seems fine." Applied: the b51 live battle ran in that window; state.md
  carries the reminder for Codex; `runs/test-scratch/` was emptied by the owner; the two process
  ideas (marker list without the thesis notes; planted versions replayed by
  `check.py --plants`) were built.
- 2026-10-29 (evening, light factory decisions in `runs/light-factory-20261029/handoff.md`):
  1 `check.py` records offline agreed-check passes: "(a)". 2 build the WH3 1x check by
  Windows file times, band 0.99-1.01 as suggested: "(a)". 3 keep the two hooks: "(a). Note: I
  keep alternating between Codex and Claude Code. In that case, we'll need to keep their
  hooks,skills,etc in sync". 4 CI with the link test skipping untracked targets: "(b)".
  5 `digest` warnings do not stop a WH3 queue: "(a)". 6 narrow Spire step 2's end-turn
  allowance to two or more different Ethereal cards: "(a). Note that the Warhammer part of the
  project is our priority". Smaller items (the checkpoint guard, the test-order fix, deleting
  `gameai.lm.sample_index` and `runs/test-scratch/`, retiring the `overnight_allocation` and
  `first_frontier_pass` markers): "these are fine".
- 2026-10-29 (light factory handoff): on keeping the night's work, "(a). Why would I even
  think about rejecting this work?" On the handoff itself: "hard to read ... Make it better:
  more concise, better structure, more concreteness, less slop." Applied: the handoff was
  rewritten around self-contained decisions; work the owner asked for is not put up for
  rejection.
- 2026-10-29 (light factory plan, implement): "Implement docs/light-factory-plan.md. You are
  free to restructure and reorganize the repo as needed. I won't be around to answer questions
  and will return in like 10h. If you finish early, continue making good use of this time by
  working on the next priority item." Answers on the page: decision 1 (one card covers later
  fixes in its area) "No"; decision 2 (reviewer on normal changes, rerun reviewer on every
  number for your pages, `check.py` alone for trivial edits) "Yes"; decision 3 (stage 1 first;
  `check.py` runs the whole offline suite before every commit) "Yes". Notes on the page: what
  "normal" means; `check.py` explained more concretely; agreed-checks.md and the hard rule
  not yet reviewed by the owner; how to keep the workflow from decaying and easy to change;
  whether WH3 needs its own check layer, such as battle timing.
- 2026-10-29 (sources): "By the way, we should keep track of all these sources for future
  reference." Applied: [references.md](references.md) lists every source from the light factory
  research, each with what it says and whether a second agent checked it; AGENTS.md points to it.
- 2026-10-29 (light factory plan, talk and style): "Actually, the talk I mentioned is "How
  Anthropic Merges 30,000 Code Changes a Day - Manish Kapur, Sonar & Addy Osmani, Anthropic". See
  if anything there changes our plan." Then: "deslopify our plan. Simplify the language. Make it
  more pleasant to read. Make it more concise. Change abstract, ambiguous elements into concrete
  things that are easier for me to process. Make the text structure flow better." Applied: the
  page cites that talk, adds a supply chain row and the Claude Code team's review practices, and
  was rewritten in plainer words.
- 2026-10-28 (light factory plan, refinement goal): "Refine docs/light-factory-plan.md" with
  "the latest industry best practices"; "Remember my context as just one person working on AI
  research, not an entire corporate team on mission-critical work"; "without overwhelming me
  with details to manually review". "It is critical to discuss specs and verification for
  probably anything that we implement here." "define the right loops for each run"; Sonar's
  verification, "zero-trust and multilayered, and in every loop", deterministic then agentic
  layers. "We are free to refactor and reorganize our repo as needed for this work." Answers:
  keep Codex's markers "verbatim"; "Leave uncommitted". Applied: the page was rewritten;
  nothing adopted.
- 2026-10-28 (light factory plan, current goal): "Write a detailed plan to turn our repo
  into a reliable light factory." "Remember that for now we won't implement anything:
  we are just writing the plan." The goal asks for current Codex, Claude Code and other
  trustworthy guidance, specs and verification discussed before features, and layered
  deterministic and agentic verification suited to one AI researcher. Draft:
  light-factory-plan.md (since 2026-10-29 [workflow.md](workflow.md)). No new method or autonomy rule adopted.
- 2026-10-28 (ProgramLab reference): "This one seems relevant to, and if so, we should add
  it to our list as well: https://programlab.blog/" Added [ProgramLab](thesis/papers.md#programlab-train-single-and-multi-agents-to-rebuild-programs)
  for LLM-team training and reward-test design, with its blog status and unreleased training
  infrastructure noted. No verification method adopted.
- 2026-10-28 (research references): "Find 3 good papers (ideally from 2026) about
  multi-agent RL along with their github repos. We will use them for reference to check
  best practices, correctness, etc" Collected [BenchMARL, MARL-BattleGrounds and MEAL](thesis/papers.md#marl-implementation-references-2026-10-28),
  with publication status, inspected code paths and limits. No verification method adopted.
- 2026-10-28 (an idea to keep), verbatim: "Also, let's write the following as some kind of
  general idea that I think could be interesting in some way somehow, maybe at least as
  something that we can use for inspiration or reference for some part of our project:
  PostTrainBench-style tasks: - Give an agent n H100-hours + Kaggle access - Ask it to
  post-train Qwen 2b for (chess, SWE-bench, etc) - Eval the submitted model" Applied: noted
  with the paper's actual setup in
  [posttraining.md](posttraining.md#idea-posttrainbench-style-tasks) and listed in the
  thesis related work.
- 2026-10-28 (two things to write down), verbatim: "1. We can rename these runs more broadly to
  'long autonomous runs', as they will run during the day as well. 2. Just like we will keep
  track of research references for the thesis, we should also remember to use existing
  research repos as inspiration and direct reference for our code, especially for more
  complicated, ambiguous parts. We should eventually look at code for existing well-known
  projects and see how they implement benchmarks, evaluations, infrastructure, tests,
  workflows, etc and incorporate useful parts into our own repo whenever relevant"
  Applied: the term is defined in [autonomy.md](autonomy.md#when-it-applies); the habit is in
  AGENTS.md's working habits and the standing work menu's upkeep row.
- 2026-10-28 (RL environment, answers), verbatim: "1. We can run episodes faster if they stay
  deterministic. Note that this adds complexity and risk, so we should be careful with it.
  Avoid overengineering and bloat. Test carefully. Keep the code clean. 2. We need to discuss
  the RL env idea first. 3. Is our checkpoint branch not merged? If so, could we merge it now?
  4. No limit. We'll see as we go." Applied: `wh3-checkpoint-rl` merged into main (`6b942a3`);
  the RL environment stays a discussion until the owner settles its scope.
- 2026-10-28 (on return from the afternoon window), verbatim: "1. No time to check that
  commit. Use common sense for now. 2. Not sure what you mean 3.Not sure what you need 4.
  Don't worry about licensing yet." Then: "Let's think about what it would take to turn WH3
  into an RL env. Write a plan here." Applied: `04e5adb`'s test expectation stays; the
  army-setup row in agreed-checks.md now names its marker and the autonomy page no longer
  calls the overnight plan unstarted (plain factual fixes); licensing is deferred.
- 2026-10-28 (answers to the overnight report's three questions): "1. We'll keep the
  human-AI direction just as a note for now. We'll prioritize other directions. 2. Not sure
  about the differences. We should use whatever clock that helps us stay correct and is
  also reproducible ideally in other environments without WSL. 3. I'm not sure what those
  checks are. Use common sense for now, I'll review later." Applied: direction 10 stays a
  note; the [clock rule](twwarhammer3/integration.md#clocks-measured-2026-10-28) is battle
  time for measured durations; the Land check's `dcb8b5a` pass is recorded in
  [agreed-checks.md](agreed-checks.md); the team check's band stays as it is, marked.
- 2026-10-28 (overnight setup, answering the plan's questions): "My return time is in like
  10+h. Don't worry too much about it. I'll set you on "/goal" and if you finish early, there
  seems to be no shortage of work to do afterwards and you can just keep going. Only one
  session for you will run overnight, so you do the commits and pushes." "we will prioritize
  setting up infrastructure, explore different potential directions to get an idea of what
  would be the best topic for the thesis, map the frontier for our selected topics, etc. The
  research we collect should be summarized here and/or indexed or whatever you think is best
  in order to make it easier for you to retrieve relevant pieces in the future." Then: "Let's
  wrap up the plan before I start the run (don't start yet)."
  Night plan: `runs/overnight-20261028/plan.md` (ignored by Git).
- 2026-10-28 (thesis idea): "researching cooperation between human and AI in a WH3 battle
  could potentially be one interesting direction that we should consider. We should add that
  to the list of topics that we want to explore before committing to a thesis topic."
  Added as direction 10 in [directions.md](thesis/directions.md); not for this overnight run.
- 2026-10-28 (recurring work and next overnight plan): keep making gradual progress on
  thesis research, important decisions and `JUDGEMENT` markers, correctness/tests, and
  code/repository cleanliness. "Let's keep track of these requests as I don't want to keep
  repeating all this manually every day"; overnight runs may last about ten hours, without
  accumulating slop. The thesis topic, RL/MARL, post-training and benchmarking remain open.
  Added: "we should remember to look for potential improvements to your own workflow from
  time to time", including token efficiency and reducing confusion/error.
  Selected: "Standing menu (Recommended)", "Small interviews (Recommended)",
  "Mixed research and review", "Free live checks too", "Checkpoint timing (Recommended)"
  and "Conditional diagnostic (Recommended)". The diagnostic first reuses saved evidence;
  if needed, one unchanged four-launch Land checkpoint check with passive 10 Hz wall and
  monotonic clock sampling, at most 45 minutes including cleanup, ending at least one hour
  before return. No new timing pass threshold or deliberate game pauses. Other provisions
  of the older autonomy proposal are not collectively accepted by these choices.
  Scope now: "Right now we will just write the plan. You won't actually do the overnight
  run yet." Then: "Let's write the plan." [Standing work](autonomy.md#standing-work)
  and [saved overnight plan](twwarhammer3/log.md#2026-10-28-overnight-the-saved-plan-moved-from-autonomymd-on-2026-10-29);
  starting it still needs an explicit instruction and game window.
- 2026-10-28 (agent context, continued): the owner had removed the agreed-checks list from
  AGENTS.md to keep it lean; "If you really think that was important, at least let's move
  it to a different file that won't automatically pollute your context window." Moved to
  [agreed-checks.md](agreed-checks.md) with a one-line pointer. "docs/thesis can stay
  untracked."
- 2026-10-27 (agent context): move Spire-specific instructions out of the root AGENTS.md
  into a Spire directory, keeping context focused on WH3. Read the
  [Spire guidance](spire/AGENTS.md) only for Spire work; shared rules stay in the root.
- 2026-10-27 (thesis revision): improve the proposal "to increase our odds of having a strong
  thesis proposal", using a supplied ChatGPT answer as a reference; learn more about the
  possible directions and what is unique about WH3 for robotics and robot learning; novelty
  comes later. "Be careful with hidden assumptions, overconfident claims"; simple, concrete
  language. In-doc notes: a separate folder for thesis ideas, novelty checks and papers;
  whether training is required or API models could be benchmarked (WH3 as a benchmark and/or
  RL environment); what "unfamiliar" means; whether checkpoints help.
  [Proposal](thesis/proposal.md), [directions](thesis/directions.md), [papers](thesis/papers.md).
- 2026-10-27 (thesis rewrite): "this time focusing on the multi-agent aspect" of the supplied
  discussion. Keep the proposal simple, intuitive, concrete and readable; constrain possible
  collaborators to Prof. Yuke Zhu's RPL lab, with Prof. Peter Stone as the alternative.
  [Revised proposal](thesis/proposal.md). Supersedes the memory-only thesis focus
  below; the request is for a proposal, not adoption of its experiment or verification choices.
- 2026-10-27 (memory overnight; thesis focus superseded above): "Ignore the multi-agent part
  and focus on the memory topic." Analyze existing runs and launch more as needed;
  "let's avoid spending money for
  now. At most, if really needed, we will have a budget of $3 for tonight"; "I'll leave you
  running for at least ~10 hours." Prepare an overnight plan, investigate deeply, validate
  claims and append viability, early findings, risks, promising directions and next steps
  to the proposal. Supersedes the earlier two-topic scope below for this session.
- 2026-10-27 (thesis exploration, overnight): "Let's append both points for this overnight run
  in the thesis proposal doc. I'll try to explore both": the memory analysis of recorded battles
  and the $0 model-team catch-up ([proposal](thesis/memory-investigation.md#overnight-2026-10-27)).
- 2026-10-26 (thesis exploration): investigate an empirical, robotics-connected master's
  topic combining WH3 with Rutav Shah's work and potential Yuke Zhu supervision; avoid
  math-heavy work and distinguish viability, research overlap and willingness to supervise.
  Then: “Let's write this as a document in the repo.” [Earlier proposal](thesis/memory-investigation.md).
  This saves the proposal; the research direction, experiments and checks remain open.
- 2026-10-26 evening (checkpoint RL, after synthetic v2: training 0.96, held out 0.76): "Stop
  here" (options offered: more varied layouts from 18 recorded jobs, not gating stages 4/5 on
  the check, a larger budget). Earlier the same day: "Let's try the simplest fix. I'll leave it
  to your judgement"; "Keep working on this ... use your best judgement and take note of any
  important decisions for me to review later" (decisions: runs/twwarhammer3/rl/plans/expansion-declaration.md).
- 2026-10-26 (checkpoint RL, after the night's run), answering two questions: "Stop here for
  review" (no remedy or second method yet); agreed the stage 1 step-run check and the stage 4
  closed loop as verification methods (recorded on branch `wh3-checkpoint-rl`'s AGENTS.md).
- 2026-10-26 (checkpoint RL plan), verbatim: "Let's add your suggested checks, as well as plan
  a structure that will make it easier to test and compare these different RL post-training
  methods. We will start by implementing the simpler one, moving up gradually, but don't
  worry about planning the other methods now. Let's focus on getting the first one right."
  Earlier the same session: plan RL with a reverse curriculum from checkpoints, no
  implementation, strong tests, checkpoint errors exposed. [Plan](twwarhammer3/checkpoint-rl-plan.md).
- 2026-10-25 (checkpoint RL handoff): write a document from the research to help another
  agent research and implement short-episode RL; highlight risks and suggest a minimal
  implementation with unit tests that catch likely issues. [Handoff](twwarhammer3/checkpoint-rl.md).
  Documentation requested; implementation and the proposed experiment/check choices remain open.
- 2026-10-25 (manual towers): built two field towers during a restore and asked to restore
  that state; then asked whether to build them manually or have the assistant do it.
  Assistant recreates the recorded choices for the check; the original timed run had
  ended without a checkpoint after those clicks.
- 2026-10-25 (siege readings): chose "Use live engine values (Recommended)" after the
  field restore matched native checksums but four cached infocard-stat readings differed.
  Compare numeric live morale/speed readings and retain armour/spell-effect witnesses;
  report cached infocard differences separately. The speed getters describe movement
  capability; this choice does not establish fatigue-adjusted effective speed.
- 2026-10-25 (siege coverage): also restore different counts of battering rams and siege
  towers selected in battle setup; both player roles; different field towers/resources and
  siege-supply amounts; Key Buildings and Minor Supply Locations held by different players;
  ladder and gate states. These are required parts of the ongoing checkpoint review.
- 2026-10-25 (checkpoint review): review restoration for errors and gaps, focusing on varied
  units and situations (including after a spell effect) in Siege maps. "No slop, no
  overengineering, no bloat." Agreed the expanded check: a source, two identical restores
  and one changed-order restore, requiring witnessed unit states and a spell taking effect
  and expiring, alongside per-tick checksums and Lua readings.
- 2026-10-25 (WH3 checkpoint decisions), answering three questions: release the standalone tool
  as a public GitHub repo with an MIT license (done: github.com/nivaldoh/wh3-battle-checkpoints,
  v0.1.0); the rebuild may run faster than 1x before the handover (AGENTS.md 1x rule amended);
  agree the checkpoint check (source, two restores with the same later orders, one changed
  restore) "but move it into the repo" first.
- 2026-10-25 (WH3 checkpoint goal), verbatim: "Let's continue working on finding a way to enable
  battle checkpoint restoration for WH3 to empower the modding community. Keep going until you
  achieve this." During the session: check notable state first (positions, timer, health and
  the like), finer details (velocity, charge state, auras) later; the restored battle's clock
  should count down; the loading screen showing current health was asked for, then parked as
  "an optional point for later … focus on restoring the battle itself correctly".
  [Result](twwarhammer3/log.md#2026-10-25-battle-checkpoints-restore-exactly-through-a-fast-rebuild).
- 2026-10-24 (WH3 checkpoint stop): "Let's wrap it up for now." Stop live probes, save
  findings and a resume point; no complete-restoration result or impossibility claim.
- 2026-10-24 (WH3 restore witnesses): first investigate restoring a unit's position after
  it has moved well away from its start, timer and unit health, as simple checks of battle
  restoration. Full checkpoint restoration remains the goal; no new route or tolerance
  is adopted by this request.
- 2026-10-24 (WH3 checkpoint continuation), verbatim: "Proceed with the investigation.
  Ignore the previous deadline and continue until you find a result or prove that it's
  impossible." Supersedes the eight-hour deadline below; the complete-state requirement
  and local evidence/binary-preservation constraints remain. A bounded negative search
  alone does not establish impossibility.
- 2026-10-24 (WH3 native checkpoints): investigate a reusable native serializer/deserializer
  for the complete running battle, using `~/wh3-checkpoint-lab/SETUP.md`, Universal Modder
  and the existing Lua integration/harness. Required state includes soldiers, orders,
  spells/projectiles, cooldowns/timers, AI/pathfinding, RNG and relevant script state.
  Validate capture/advance/restore with identical subsequent inputs and repeated restores;
  replay support, aggregate positions/health and untested memory dumps are insufficient.
  Work autonomously for up to eight hours, stopping earlier on verified success or no
  productive permitted route; preserve the deadline, journal findings and write a final
  report in the lab. Preserve unrelated work/original binaries and keep decompilation local.
- 2026-10-23 (WH3 checkpoint environment): install/configure Universal Modder without fal,
  PyGhidra MCP and a Windows native-inspection helper; reuse the battle harness and existing
  tools. Exercise decompilation, battle control and module enumeration separately. Keep
  binaries, decompiles and setup evidence in `~/wh3-checkpoint-lab/`; preserve unrelated
  work and global permission policies. This request prepares the overnight investigation.
  In this session the owner explicitly authorized `--approve-for-me` in the lab's restart
  launcher, for session-only automatic approval review; global policies stay unchanged.
- 2026-10-23 (WH3 live checks), verbatim: "focusing on anything that requires a live
  battle to actually be executed (ideally without cost first. We can talk about cases
  that might cost money later)"; "You are free to run the game right now as needed".
- 2026-10-23 (WH3 eval/test comparison), verbatim: "Consider them relative to each other,
  and whether there are any inconsistencies, gaps and opportunities for improvement in
  general. Get rid of any slop you find." Also: "Highlight anything that could still require
  or at least benefit from my personal review and judgement by taking notes and marking
  these spots in the codebase."
- 2026-10-23 (WH3 testing review): review and improve tests, focusing on WH3 methodology,
  guidelines, coverage, correctness and style; larger structural changes are allowed.
  Remove slop, gather external testing and agentic-verification practices, and document
  missing or unclear guidance. This does not adopt new verification methods or benchmark rules.
- 2026-10-23 (testing continued), verbatim: "Continue to make progress on improving our tests".
- 2026-10-23 (initial testing cleanup), verbatim: "Let's write our testing guidelines down
  and make some initial progress. I'll review a bit later. Remember, no slop!"
  First batch: Spire's root tests and shared message builders, plus clearer WH3 check headers.
- 2026-10-23 (tests): review test organization, readability, coverage and correctness;
  gather testing guidelines and examples from established projects, as for evaluations.
  [Draft](testing.md), [current test guide](../tests/README.md). This request does not
  adopt new verification methods or benchmark rules.
- 2026-10-23 (Spire profile and restore), verbatim: "Let's take note that we might want to
  unlock things normally first in the game before enabling this then". A tentative note on
  the profile decision in [state-restore.md](spire/state-restore.md#owner-decisions), not
  a decision.
- 2026-10-23 (after the Spire collection night), answering four questions (push; a teacher
  or reasoning-on night next; agree the capture check; try restoring a snapshot), verbatim:
  "1. Yes, let's push. 2. Let's take note of that to decide later. 3. Not sure what this
  is. Let's write it down for now. 4. Yes, being able to restore the game back to a
  specific state (ideally with fixed RNG) to try different choices from there would be
  great for model training and benchmarking. We should write about an investigation for
  this potential feature as the highest priority within the Slay The Spire work". Pushed
  `da62f74`; the restore investigation is Spire's first item in [state.md](state.md).
- 2026-10-23 (01:53 -03, goal, away 10 hours), verbatim: "Improve trace data collection for
  Slay The Spire to feed a broader range of frontier post-training methods like RL. After
  that, proceed to collect game data until I return 10 hours from now. Keep track of the
  results." Supersedes "no money yet" below for this night; the owner named no cap.
  Capture: harness v10.2 ([posttraining.md](posttraining.md#beyond-supervised-fine-tuning));
  the night: [Spire log](spire/fullrun/log.md).
- 2026-10-23 (post-training data): no money on data-collection runs yet. Before any
  overnight run that collects post-training data, set up improved capture of what RL and
  the other methods used at the frontier need from traces; training itself starts with a
  plain SFT scope. The Spire collection night assessed that day was not launched; the
  reminder is in [posttraining.md](posttraining.md#beyond-supervised-fine-tuning).
- 2026-10-23 (judgement calls): coding agents have made judgement-based calls (benchmark
  goals, how to verify, next steps, design decisions) without the owner's awareness or
  approval; from now on agents execute and the owner decides. Mark every such call for
  review at the nearest convenient location (a code comment, a note in a doc), with a
  separate mark when unsure it counts; register the goal in [judgement.md](judgement.md)
  and the rule in AGENTS.md. The format of the two examples was accepted; no decision was
  made on any marked call.
- 2026-10-22 (overview removal): remove the project overview to keep the project lean;
  the owner found it useless. Supersedes both overview requests below.
- 2026-10-22 (visual project overview; superseded by removal): implement the overview as an intuitive guide to
  all major parts of the codebase, with concise explanations and details available when
  needed. Keep it simple and lean. On checks: "We don't need to worry too much about
  that. FOcus on getting the most important points right instead".
- 2026-10-22 (02:35, overnight), verbatim: "Let's continue to implement what we can during
  this overnight run. I'll be back tomorrow. I'll delegate decisions to you until I'm able
  to review them." Read as a free night (the agreed starting-set screen ran) with decisions
  delegated; choices that change benchmark meaning stay parked ([log](twwarhammer3/log.md)).
- 2026-10-22 (owner overview; superseded by removal), verbatim: "I just need an easy way to know what's the current state of the project and what decisions are pending on my end." Start implementing the simple local overview; diffs and PR review are outside this first version.
- 2026-10-21 (night, after the multi-agent review), verbatim: "I have no time to review
  this. I'll trust your judgement. Fix any issues you find. Test things carefully. Try to
  keep the code simple and lean as much as possible. Avoid overengineering/bloat/garbage/slop."
  Applied as offline fixes on `wh3-model-team`; choices that change benchmark meaning stay
  parked for the owner ([autonomy](autonomy.md#the-test), rule 3).
- 2026-10-21 (evening), verbatim: "We won't have a second machine for now. We'll have to
  leave that part for the future. You are free to proceed with other work. I won't have time
  to review decisions carefully now, so continue to follow your best judgement and highlight
  any meaningful decisions for me to review later". No return time or free PC was named, so
  this is offline work under the [away proposal](autonomy.md)'s busy rule.
- 2026-10-21 (evaluation resource): read [Wolfe's subjective-evaluation guide](https://cameronrwolfe.substack.com/p/subjective-evals),
  incorporate useful ideas into the repo's evaluation guidelines, and add it to the
  [reference list](twwarhammer3/evaluation-guidelines.md#sources).
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
- 2026-10-31 (GaP answers G1–G14, plan only): first see whether it works in WH3; defer
  research comparisons and benchmark scoring/statistical decisions, while keeping interest
  in better live control and learning across battles. Use GaP as a reference and our existing
  controllers/team dispatcher. Start with independent progress, observation-only coordination,
  graph revisions between whole battles, a narrow Land family, and separate graphs for later
  allied armies. Waiting rounds, messages, live graph edits, other battle types and a central
  graph remain possible later experiments. Delegate common-sense initial limits/retries and
  fallbacks to the implementer, to record and tune. "We should build a broader library first"
  and tackle its scope separately, with MORSL as a reference and care over unbounded complexity;
  start with a "frozen, pre-built skill library". "stick with permitted information only"
  for authors as well as live controllers. Count development/revision costs as well as battle
  costs. Battle restoration and its policy-state choice wait. "Update the plan based on these
  points, but don't start the implementation yet." [Revised plan](twwarhammer3/gap-plan.md).
- 2026-10-31 (GaP, plan only): add the paper to the research collection and plan graph
  controllers for one army with multiple LLMs, then multiple allied armies. Inspect GaP's
  GitHub code/docs, existing controller interfaces, WH3 skill needs, between-battle learning
  and checkpoint-based alternatives. Cover risks and repeatable verification; mark open
  choices as JUDGEMENT calls. "Right now we are only focused on the plan, so don't start
  the actual implementation yet." [Plan](twwarhammer3/gap-plan.md).
- 2026-10-30 15:01 (native multiplayer, implement): "Implement
  docs/twwarhammer3/native-multiplayer.md. Note that I haven't set up accounts, billing, etc,
  so do as much as we reasonably can before that part becomes a blocker." Inline notes on the
  plan's markers before that: Client layout "[seems ok]"; Session contract, Worker link, Probe
  scope, Verification contract and the architecture paragraph "[seems fine]"; Capability
  fixture "[fine]"; Worker platform: "not sure why we need a WSL coordinator. Can't we just do
  some simple if/else to see what the env is running? I use WSL2 locally for dev, and the
  hosted machines will likely use windows directly and we won't need to force WSL there just
  because of that". Applied and merged at `5d10e2a` ([status](twwarhammer3/native-multiplayer.md#implementation-status)).
- 2026-10-30 (native multiplayer plan refinement): "Further investigate and refine
  docs/twwarhammer3/native-multiplayer.md (without implementing it yet) until each step is
  concrete and highly detailed." Identify the ideal approach, risks, cost reductions,
  strong verification, approval decisions and a similar GitHub project. Overnight research
  is authorized; implementation and spending are not. Inline notes in the original draft:
  "we will not use money just yet. Let's set up everything we can before that, and get as
  much certainty as possible"; "we need to start testing minimally as this will be complex
  enough as it is, then increment from there". Investigate Google Cloud and airgpu setup,
  headless viability more deeply, and keep the implementation simple. Benchmarking comes
  first, with a later RL path: "maybe with a service like Tinker or Prime Intellect".
  More licenses still need purchasing; multiplayer checkpoints may be considered if needed
  but should probably be avoided because of their complexity. [Plan](twwarhammer3/native-multiplayer.md).
- 2026-10-30 (native multiplayer exploration): assess actual team-versus-team LLM battles
  on multiple machines, keeping the cloud setup vague. Investigate Lua-only/unattended
  control and whether reverse engineering could fill missing features; draft a plan,
  rough costs, main risks and reasons it might fail. Initial assessment requested;
  [draft](twwarhammer3/native-multiplayer.md). No hosting purchase or new paid cohort chosen.
- 2026-10-28 (RL environment, thesis and benchmark, status follow-up): the thesis will
  likely concern multi-agent systems; multi-agent RL could connect it to the WH3 RL
  environment, which may also stay separate. "The research question is something we're
  still figuring out." Tentative environment outline: each agent observes the battle
  information available to it, perhaps with information about other active agents, and
  controls its part of the army. Rewards might be sparse win/loss outcomes, using restores
  to study relevant situations near a battle's end. Reset could return to a battle start
  or a saved checkpoint; the owner asked what reset means. Explanation: restart the game
  episode at that state while retaining learned model weights. Observation sharing,
  control allocation, rewards, reset details and correctness checks remain open; discuss
  the checks more deeply later. [Candidate connection](thesis/directions.md#6-wh3-as-an-rl-environment-for-high-level-decisions).
- 2026-10-28 (benchmark scope and measures): "The Land Battle benchmark should probably
  measure unit health and morale, since other metrics seems secondary to these two."
  Tentative priority, not a scoring formula. Include several battle types: Siege (existing
  work), Survival, Ambush and Conquest; the owner will confirm others. Many benchmark
  definitions remain for later. This broadens the 2026-10-23 Land-only planning scope;
  mode order, profiles, scoring and checks are not settled. [Definition](twwarhammer3/benchmark.md).
- 2026-10-28 (local LLM learning experiment): "If it's the simple RL post-training for a
  local LLM, we can leave it paused for now." It is the checkpoint-based Qwen3-0.6B LoRA
  candidate chooser; leave that experiment paused. This does not pause discussion of the
  broader RL environment. [Experiment](twwarhammer3/checkpoint-rl.md#open-owner-choices-decision-11).
- 2026-10-28 (side quest, verbatim): "one thing that might be outside of thesis scope but that
  I want to do at least as a sidequest is to see if we can turn WH3 into an RL env, maybe even
  using the checkpoint restoration feature for reverse curriculum or so." Recorded only; no
  work is scheduled. Related: thesis [direction 6](thesis/directions.md#6-wh3-as-an-rl-environment-for-high-level-decisions),
  the [restart-curricula note](thesis/notes/restart-curricula.md) and [checkpoint RL](twwarhammer3/checkpoint-rl.md).
- 2026-10-28 (model-team open items): "I don't know what my pending decisions mean so I'll
  let you decide something reasonable for now just to unblock us. Just keep track of that so
  I can remember to review it at some point later." Each item keeps today's behaviour and
  its marker; listed in [state.md](state.md) item 4 for a later review.
- 2026-10-27 (multi-agent review; chosen from options offered): team work becomes "a later
  controller on the new Land Battle benchmark", and the team-structures stages wait for that
  battle's first team-vs-single result; `wh3-model-team`: "Rebase, clean, merge" after one
  $0 rerun of the agreed live check; members "see their teammate's condition (leadership %,
  fatigue, ammo), still not its orders, queue or destination".
  [Implementation page](twwarhammer3/multi-agent-implementation.md#next).
- 2026-10-23 (benchmark pages): [benchmark.md](twwarhammer3/benchmark.md) holds only the
  benchmark's definition; [benchmark-implementation.md](twwarhammer3/benchmark-implementation.md)
  holds how it will be built, each phase and other transient details. The owner judged the
  page's prose slop and rewrote its Purpose paragraph as the reference for plain writing.
- 2026-10-23 (Land Battle interview), verbatim: "We will start by focusing on the definition
  for one Land Battle, ignoring other game modes for now" and "interview me (writing all
  questions at once in that document)". Compare models on battle performance, testing the
  knowledge needed to win and execution given API latency; consider objective health and
  wavering/routing measures and missing game information. The [interview](twwarhammer3/benchmark-implementation.md#owner-interview-one-land-battle)
  leaves scoring formulas, knowledge evidence, profile and checks open for the owner's
  answers; earlier proposals are not adopted by this request. Land-only planning scope
  broadened on 2026-10-28 to include the battle types listed above.
- 2026-10-23 (Land Battle benchmark), verbatim: "Timer outcomes can be whoever the engine
  decides is the winner. Let's work on the updated, improved benchmark definition and
  plan, focusing on what our first Land Battle benchmark should look like." On army size:
  "Small mixed armies first (recommended)". Develop the definition and plan around engine
  outcomes, with health, leadership and tactical events explaining performance. This
  supersedes contact-only scoring for the new Land Battle benchmark, not historical card
  verdicts. Exact rosters, settings, summary, comparisons and new verification methods
  remain proposals in [benchmark.md](twwarhammer3/benchmark.md); no runtime implementation
  or new game/API run is requested by this planning direction.
- 2026-10-23 (native checkpoint feasibility): reopen research into whether native reverse
  engineering could provide exact battle-state/RNG restoration, possibly through Lua,
  and which tools the assistant would need. This requests a viability assessment;
  the earlier failed implementation remains closed. [Findings](twwarhammer3/log.md#2026-10-23-native-checkpoint-feasibility).
- 2026-10-23 (rewind closed): wrap up the unsuccessful direct battle-state/RNG restore
  investigation and clean up its leftovers. Decompilers are a topic for another session;
  no further native reverse engineering or VM investigation now. Repeating the opening
  did not satisfy the requested direct jump. [Outcome](twwarhammer3/log.md#2026-10-23-battle-rewind-investigation-closed).
- 2026-10-22 (human opponent): wrap up the mode where the owner plays against the
  controllers and remember to implement it later. Resume at step 1 of the
  [plan](twwarhammer3/multi-agent-plan.md#d-single-client-steps); keep branch
  `wh3-human-opponent` (`de37005`) and its worktree until then.
- 2026-10-22 (checkpoints and RNG; closed 2026-10-23): use reproducible battle situations for benchmarking
  and training; first research the available reset/RNG mechanisms and plan a clean,
  small implementation with repeatable checks. Direct restoration and fixed engine RNG
  were not achieved; the plan and abandoned draft were removed at the owner's request.
- 2026-10-21 (evening goal, team structures), verbatim: "Using two LLMs for one army is
  arbitrary decision, but we can use it to compare with other options later. But we have
  more interesting options, like one model per unit, one model per type of unit, one model
  per custom group (with custom groups being decided ahead of time by another LLM), and
  more. Lots of interesting options to explore. There should be interesting things that we
  can visualize from the LLM team behavior as well. Let's think further about this carefully
  plan how we might do it". A planning request: no game sessions or spend.
- 2026-10-21 (goal), verbatim: "Review the WH3 multi-agent plan and implementation. Look for
  opportunities to make it better. See if you can simplify it and reduce slop." Done:
  [log](twwarhammer3/log.md#2026-10-21-team-plan-and-implementation-review).
- 2026-10-21 (multi-agent implementation and verification): "Proceed with the implementation
  for the multi-agent battles. Keep it simple at the start, make it verifiable, no slop."
  Agreed component checks for ownership, hidden-state filtering, independent progress,
  feedback identity, timing and cleanup; also four script-only live probes on the existing
  Knights/Swordsmen battle, alternating the delayed member, unpaused at 1x, $0 model
  spend, capped at 30 minutes total. Live success requires the correct unit to move while
  its teammate is still thinking. This authorizes the first scripted split-army adapter;
  paid model teams, native multiplayer and campaigns remain later work.
- 2026-10-21 (multi-agent implementation plan): "Plan the implementation (starting small)
  for the multi-agent implementation". [Implementation plan](twwarhammer3/multi-agent-implementation.md):
  begin with a split-army adapter for two scripted members and propose concrete checks;
  this requests the plan, not implementation or new game sessions.
- 2026-10-21 (multi-agent evaluation plan), verbatim: "Let's write a detailed, careful
  plan on how we might evaluate Total War Warhammer 3 as a multi-agent problem (initially
  just team battles, but eventually the multi-player campaign too)". Plan:
  [multi-agent-plan.md](twwarhammer3/multi-agent-plan.md). This requests campaign evaluation
  design as well as team-battle design; it does not adopt scoring/checks or authorize new
  game sessions, multiplayer clients, campaign saves or achievements.
- 2026-10-21 (12:45, four more answers): the starting-set screen runs "Tonight"; add the
  engine-ending regression as an agreed check in AGENTS.md ("Yes, add it"); back up `runs/`
  "Not now"; the chariot card uses witness v2 (HitAndRunV2) for its next confirmation at
  decision 3's 2 s/2 s cell, c1 staying v1's admitted record ("Yes, v2 at 2 s/2 s").
- 2026-10-21 (on return, 12:20, answering the three inbox questions): (1) the starting
  set's screen: "Yes, run it", which also agrees its reading rule and the two markers as
  [tactic-cards.md](twwarhammer3/tactic-cards.md#the-starting-set-proposal-2026-10-21)
  words them; run on the next free night; (2) the defender prompt: "Tell models", a
  contact-scoring scenario field and one logged prompt version for `llm`, `llm_rules` and
  `commander`; (3) the failure rule: "Agree and merge" `wh3-keep-engine-ending` as harness
  b47.
  The contact-only objective is superseded for the new Land Battle benchmark by the
  2026-10-23 engine-outcome direction above; the historical screen and prompt remain recorded.
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
  ([decisions](twwarhammer3/benchmark-implementation.md#history)).
- 2026-10-16 (evening, latest): benchmark every reasoning mode of every model in each
  scenario; verify each model's real modes first (some open-weight models are only
  on/off) ([model coverage](twwarhammer3/benchmark-implementation.md#owner-goals)).
- 2026-10-16 (evening, later): mostly many small battles that each test one or two
  specific things (e.g. two cheap cavalry units against one braced pikeman unit, if
  winnable: feint and flank), plus a few larger battles for context length and
  scale-only problems; diversity, quality and room for unexpected behaviour
  ([scenario mix](twwarhammer3/benchmark-implementation.md#owner-goals)).
- 2026-10-16 (evening): make each scenario maximally difficult while still demonstrably
  winnable; fewer high-quality scenarios beat redundant ones that waste compute. Armies,
  map settings etc. may be modified to calibrate
  ([difficulty target](twwarhammer3/benchmark-implementation.md#owner-goals)).
- 2026-10-16 (resume): implement OpenRouter and the three chosen models, then continue
  improving benchmark calibration and the report within the existing budgets.
- 2026-10-16 (OpenRouter): the owner stored an OpenRouter key and set a separate $50
  budget. Requested support and three leading open-weight model API checks, then
  clarified: stop after cleanup and design this turn; no implementation or paid calls.
- 2026-10-16 (after M1): planning only. Keep the core provisional until the strongest
  models have been tested; current scenarios may be too easy for them. Calibrate
  challenges and extract more useful evidence before spending on another large model
  comparison ([proposal](twwarhammer3/benchmark-implementation.md#history)).
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
  [plan](twwarhammer3/benchmark-implementation.md#history).
- 2026-10-14 (benchmark steering): specialist anchor units and faction-specific mechanics
  should drive scenario design. Prioritize extreme tactical problems (cavalry against
  anti-large, caster-led forces, difficult sieges, commanding/fighting Skaven swarms),
  meaningful creative choices and battles worth watching; well-rounded armies can follow.
  Small armies on either or both sides are equally suitable; high funds and large
  rosters are not requirements. Start the first specialist prototypes compact.
- 2026-10-14 (night, sieges): benchmark who holds the victory points over time and the
  supplies left unspent; both are now measured per episode.
- 2026-10-14 (benchmark spec; added 2026-10-28 from a paragraph dated 2026-10-14 in a session
  memory note): a controller's whole latency, network included, is part of what is measured
  ("it will also matter in certain real-life settings"). The note's conclusion, not quoted
  words: live 1x with natural latency is the primary result and added-delay tracks are
  diagnostics. Cited in [benchmark.md](twwarhammer3/benchmark.md).
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
