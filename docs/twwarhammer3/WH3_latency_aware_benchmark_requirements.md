# Project direction: a reproducible tactical battle environment for latency-aware agents

## Purpose and starting point

Evolve this project toward:

> **A reproducible tactical battle environment for evaluating latency-aware agents in Total War: Warhammer III.**

The intended contribution is not just a demonstration that an LLM can control a battle. It is a reusable environment in which another developer can connect a controller, run specified tactical scenarios, and compare its results with existing controllers under explicit observation, action, and timing rules.

The project owner reports that LLM battle control already works end to end, although performance is poor, and that mods expose structured/text-based game information and commands. A roughly five-second inference-to-command loop has been observed in one configuration. These are starting points to verify against the repository, not guarantees about interface completeness or typical latency.

This brief defines desired outcomes, not an implementation architecture. Inspect the existing project before deciding what needs to change. Preserve working components where possible. Do not assume that deterministic resets, seeded randomness, precise clock control, frame stepping, headless execution, parallel game instances, or authoritative command acknowledgments are available.

## 1. Scope: evaluate tactical control, not a prescribed agent architecture

Focus on battles between two opposing armies, not the campaign layer. A controller should be evaluated on how effectively it commands its allowed units with the information and actions available to it.

“Latency-aware” means that observation, reasoning, and command delivery take time, and the battlefield may change while the controller is deciding. We want to measure how well controllers operate under those conditions—not simply how quickly an API responds.

The environment should accommodate a direct LLM controller, a scripted controller, or a hybrid without requiring any particular design. Hierarchical control—such as a slower commander assigning objectives to faster unit controllers—is one possible experimental approach, not a benchmark requirement.

Prioritize a small, reliable, end-to-end evaluation path over broad game coverage. Training, multiple agent architectures, campaign support, and integration with external environment catalogs are not initial deliverables.

## 2. Explicit observation and action rules

Each evaluation configuration needs a clear contract describing what the controller can observe and do.

For observations, identify which information is available, its update timing, and whether it includes privileged enemy state. Start with the information the project actually exposes. A privileged-state benchmark is acceptable when labeled accurately; do not describe it as player-equivalent or visibility-filtered without verifying that claim. Information used only for scoring must not silently enter the controller’s observations.

For actions, define their meaning, permitted targets, persistence, and replacement or cancellation behavior where supported. Clarify what remains handled by the game’s normal unit behavior. Distinguish basic orders from tactical helpers that perform substantial decision-making themselves.

Controllers being compared should use the same declared interface and permissions. A controller with additional tactical automation can be evaluated, but that automation must be disclosed as part of the controller rather than mistaken for the model’s reasoning ability. Setup, debugging, and scoring powers must not be available as battle actions.

Invalid orders, unavailable targets, and action failures need visible, consistent treatment. Do not silently repair poor decisions in ways that give a controller unreported assistance.

## 3. Timing must be part of the task definition

Every evaluation must specify whether the battle continues during inference, the game-speed policy, whether pausing is allowed, and what happens while a controller is busy. Live real-time evaluation is the initial target unless the existing integration prevents it.

Results should distinguish wall-clock time from game time. Where observable, record when a state snapshot was captured, when a decision was requested and returned, and when resulting commands were delivered or applied. Do not equate “command sent” with “command took effect.” Where application timing cannot be observed, report the measurable boundary and the uncertainty.

The key quantity is the age of the information when a command can affect the battle, not just model response time. Also record actual decision frequency and the handling of outstanding or stale decisions. A response based on an old snapshot must not be presented as a decision based on the current state.

Support comparisons under clearly stated latency conditions. Initially, measured natural latency may be enough. Controlled additional delay is a useful subsequent capability, but distinguish added delay from total latency. A run with no added delay is not necessarily a zero-latency run.

Paused or controlled-advancement evaluation could later help separate tactical reasoning from speed limitations, but only if genuinely supported. Keep its results separate from live real-time results.

## 4. Reproducible scenarios and episode lifecycle

A scenario must identify the conditions needed to interpret and repeat an experiment: battlefield, opposing forces, starting arrangement, opponent behavior/settings, objective, allowed controls, observation rules, and episode limits, to the extent these can be specified or measured.

Begin with a small set of manageable scenarios that test distinguishable tactical capabilities. Candidate families include ranged-unit protection, coordinated attacks, and disengagement. These are suggestions, not requirements to create capabilities the integration lacks. At least some tasks should distinguish competent control from a trivial policy without making every available controller fail.

Separate development scenarios from held-out evaluation variations once tuning begins. Do not repeatedly optimize against the entire test suite and then describe its results as unseen generalization.

A supported episode needs a known start, controlled execution, an identifiable ending, recorded results, and a path back to a valid starting state. Routine starts and resets should be unattended within the declared supported setup. If some steps remain manual, expose that limitation rather than claiming a fully automated environment.

Reproducibility does not require promising identical trajectories. Record controllable settings, verify starting conditions where possible, and disclose uncontrolled variation. Use seeds only where they actually control something. Repeated trials should remain necessary when game or model behavior is nondeterministic.

## 5. Outcomes and failures must be trustworthy

Use the game’s authoritative battle outcome where accessible. Preserve meaningful distinctions between victory, defeat, draw, an imposed time limit, controller failure, and infrastructure failure. When the game’s result cannot be observed reliably, disclose the substitute criterion rather than silently inferring success.

Define treatment of time limits and failed trials before comparing controllers. A crashed bridge must not become a tactical defeat by accident, but unstable runs must not simply disappear from the report either. Report both performance on valid trials and operational reliability, with clear denominators.

Secondary measures may include battle duration, surviving forces, losses, invalid commands, decision latency, token use, and inference cost where available. Include only quantities that can be measured and interpreted consistently. Clearly label estimates and unavailable values.

Do not begin by inventing one elaborate composite score. Preserve the underlying outcomes so users can distinguish tactical success, responsiveness, cost, and reliability.

## 6. Baselines and comparisons should establish usefulness

Retain the current LLM controller as a baseline if it can be run reproducibly. Add a simple non-LLM reference controller if the available actions make that practical. Its purpose is to reveal whether a more expensive controller adds value—not to require development of an expert scripted opponent.

Evaluate controllers on matched scenario definitions and repeated runs. Keep model configuration, observations, action permissions, and relevant resource budgets controlled when making causal claims about one design change. When those differ, disclose them and compare tradeoffs instead of attributing every gain to the architecture.

A useful report should answer:

- How often does each controller achieve the objective, and how variable are its results?
- How does performance change with the measured or imposed latency conditions?
- What inference resources and operational reliability accompany those results?

Small-sample findings should be labeled exploratory. One impressive victory is a demonstration, not sufficient benchmark evidence.

## 7. Records must support inspection and independent reruns

Each run should retain enough information to explain what happened: scenario and trial identifiers, relevant game/mod/project versions, controller configuration, observation/action contract, timing policy, observations, commands, timestamps, outcomes, and errors. Record model/provider identity and generation settings when relevant, plus hardware/runtime information that materially affects timing.

The records should make it possible to inspect what the controller knew before a consequential decision and whether that information was already stale. They should also support rerunning an experiment from its declared configuration and recomputing summary metrics without manually watching every battle.

Do not promise deterministic replay unless demonstrated. Inspecting a saved decision trace is different from recreating the same game trajectory. Similarly, record actual external model identifiers and acknowledge when a provider does not offer an immutable model version.

Software tests are useful, but distinguish mocked tests from verified in-game behavior. Claims about reset reliability, command effects, and unattended execution need evidence from actual game runs.

## 8. Leave a path to RL without building training infrastructure now

Keep task definitions, controller interaction, and evaluation independent of a particular LLM provider or prompting scheme. A future learned policy should be able to control the same supported tasks without redefining their meaning.

Preserve episode boundaries, observations, issued actions, their timing, outcome information, and the distinction between natural termination and externally imposed stopping. In an asynchronous real-time environment, these are not automatically ordinary fixed-duration RL transitions. The records must preserve enough ordering and elapsed-time information for a future training adapter to define valid transitions rather than inventing them afterward.

An explicit terminal outcome can later support a simple reward. Dense reward shaping, demonstrations, preference datasets, and post-training algorithms are separate decisions; do not add them speculatively.

Measure rollout throughput, including battle execution, resets, and failures. Future RL feasibility depends on actual experience-generation cost and reliability, not just an interface that resembles an RL environment.

Do not require a Gym-style wrapper, Prime Intellect integration, remote hosting, or parallel execution for the first release. Keep integration possible through clear contracts, but do not assume external platforms can run the commercial game. Distribution should center on project code and scenario configuration, with game-installation requirements explicit; do not assume game assets or binaries can be bundled.

## 9. Completion criteria and scope control

The first milestone is one complete, repeatable evaluation path using the existing game integration: a specified scenario, the current controller, visible timing behavior, reliable outcome/failure classification, and inspectable records. Identify any remaining manual steps honestly.

An initial benchmark release should then provide a small documented suite, reference results, routine episode execution/reset within the supported setup, and a clear way to substitute another controller. Another developer should be able to follow the documentation, run an evaluation, and obtain interpretable results—not necessarily identical trajectories or win rates.

Additional scenario families, controlled-delay experiments, alternative observation tracks, and RL adapters should follow demonstrated need. Do not let hypothetical future flexibility block a usable release.

## Requested first response from Codex

Inspect the repository and map these requirements to what already exists. Distinguish confirmed capabilities, missing pieces, and uncertainties that need an in-game check. Propose the smallest next milestone that closes a meaningful gap, and state what evidence would demonstrate completion.

Do not propose a rewrite or a broad framework before establishing why existing components are insufficient. The central acceptance question is:

> **Can an independent user evaluate a different battle controller under the same declared scenario, information, action, and timing rules, and understand both its performance and the limitations of the comparison?**
