# Slay the Spire AI: Agent Operating Guide

**Audience:** Codex, Claude Code, and other coding agents working in this repository.  
**Research checked:** 11 October 2026.  
**Purpose:** Build a reproducible project that trains and evaluates policies for **Slay the Spire 1**, while making good use of autonomous coding and overnight experiments.

This is a bootstrap guide and reference. Read it once, execute the relevant stage, and keep the repository's short working instructions current. Do not load this entire guide into every small task. Commands and file layouts below are implementation targets, not claims that this empty repository already provides them.

## 0. Current status

See [docs/state.md](docs/state.md) for the current milestone, evidence, blockers, and next action.

## 1. Your assignment

Build the smallest reliable system that can run experiments, explain failures, and produce defensible results. Use existing game integrations where useful. The research contribution should come from the learning system, experimental design, engineering quality, and findings. Reimplementing an existing bridge does not automatically improve the project.

Start with these defaults unless the owner or existing repository instructions specify otherwise:

| Decision | Starting choice |
|---|---|
| Game | Slay the Spire 1; Ironclad; Ascension 0 |
| Initial scope | A clearly specified combat benchmark, followed by broader encounters and Act 1 |
| Policy input | Structured information available to a player; no hidden future state |
| First learner | A small, randomly initialized neural policy |
| Later comparison | A pretrained language model, before and after actual weight training |
| Resources | Inspect the machine; expected setup is Windows 11, optionally WSL2, with an RTX 3060 12 GB |
| Execution | One primary coding session and one GPU training job at a time |
| Spending | Existing authorized subscriptions and local hardware; no new paid services by default |

Keep three roles distinct:

- **Coding researcher:** reads sources, changes code, investigates failures, and chooses experiments.
- **Training process:** consumes data and updates model weights.
- **Gameplay policy:** receives its declared observation and chooses game actions.

Improving a hand-written policy through agent-generated code is a useful baseline. It is not neural RL from scratch. Updating a procedural skill library is not LLM weight training. A language model used only to write PPO code is not the policy being trained.

### Work autonomously within the assignment

Inspect the repository and machine, resolve ordinary dependencies, implement adapters, run checks, debug failures, and conduct local experiments within the active budget. Do not ask the owner to do routine shell work or stop after producing a plan. Preserve existing work and follow the repository's established contribution rules.

Ask for human involvement when an actual dependency requires it: unavailable game files, interactive account access, a purchase, an unapproved paid resource, or a material change in project direction. Explain the concrete blocker and continue independent work where possible. Do not repeatedly request authorization already present in the session.

The owner should review milestone results and understand the final scientific claims. That does not require manually supervising every implementation step.

## 2. Research informing this design

These sources inform the workflow; they are not dependencies to install. The project-specific instructions in later sections are our adaptation.

| Source | Useful finding or mechanism | Adoption here |
|---|---|---|
| **Apple/EPFL, September 2026** | Under matched models, hardware, and time, elaborate ML harnesses did not reliably outperform a strong coding agent with direct execution tools. [R1] | Start with the existing coding client, visible resources, and useful experiment commands. Add orchestration only to solve an observed problem. |
| **ENPIRE, September 2026 revision** | Constructs reset and verification interfaces, then uses feedback to improve policies and training code. [R2] | Establish a trustworthy game interface before autonomous optimization. Keep the experiment definition stable during comparisons. |
| **ASPIRE, June 2026** | Uses execution traces to locate failures, validate program repairs, and retain reusable skills. Its coding model remains frozen. [R4] | Make failed decisions inspectable. Preserve tested findings with their scope, rather than accumulating transcripts. |
| **Eureka, 2023 / ICLR 2024** | Proposes reward code, trains policies, and uses task performance plus reward statistics to improve proposals. [R5] | Later, investigate reward shaping as an explicit experiment while keeping gameplay evaluation fixed. |
| **ScientistOne, May 2026** | Its audit found gaps between reported methods, submitted code, and reported scores in autonomous research outputs. [R6] | Every reported result must point to the actual implementation, checkpoint, and evaluation output. |
| **AIRA₂, March–April 2026** | Separates search feedback from final selection and standardizes evaluation across candidates. [R7] | Reuse a canonical development evaluation; reserve final tests until after selection. |

The Apple/EPFL result is evidence for a starting design, not proof that all coordination is useless. Its tasks and hardware differ from this project. ENPIRE also reports that larger fleets trade more tokens for faster progress; that does not justify several training agents competing for one consumer GPU. [R1], [R2]

Karpathy's **autoresearch** remains a useful compact example of repeated, measured experiments. Borrow its clear objective, executable feedback, and retained experiment history. Its particular five-minute training workload and single editable file are not requirements for this game. [R8]

Read primary papers, official documentation, and upstream code when a decision needs them. Do not run a broad literature review before every edit. Record a source when it changes the implementation or motivates a hypothesis.

## 3. First session: establish a working feedback loop

### 3.1 Inspect before building

Read existing instructions and inspect Git state. Find the game, available Python and Java tooling, GPU access, disk space, and any installed mods. Check what works from the current runtime, including Windows/WSL boundaries. Record actual capabilities and versions; do not infer them from a package being present.

Use the currently available strong coding model in the existing client. As checked for this guide, relevant choices include **GPT-6.1 Sol** and **Claude Opus 5.5**. Verify the account's available models and charging behavior when starting substantial work. Use the normal reasoning setting initially; increase it for a difficult diagnosis or research decision. Do not copy the older model names in robotics reproduction scripts. [D1], [D2]

Keep the game on the host where it already works. Add a host boundary only if needed. A small local bridge is preferable to migrating the entire setup just to match an assumed Linux layout.

### 3.2 Investigate the existing integrations

| Integration | Candidate use | Constraint to verify |
|---|---|---|
| **CommunicationMod** | Receive structured state and send actions to the original game. | It is a game bridge, not a complete training environment. Its documented `START` command begins from the main menu; arbitrary combat reset is not promised. [G1] |
| **spirecomm** | Reuse Python protocol handling and inspect an existing simple agent. | Separate protocol code from policy logic so imported heuristics do not become an undisclosed part of the learner. [G2] |
| **sts_lightspeed** | Investigate a fast C++ simulator for repeated training. | Audit supported mechanics and measure local throughput. Its documented search uses exact RNG knowledge; treat that search as privileged. [G3] |
| **LudicrousSpeed / STSStateSaver** | Investigate faster original-engine execution or saved-state support if needed. | Verify the exact restore and compatibility behavior before depending on it. [G4], [G5] |

Inspect licenses and pin the upstream revisions actually used. Keep proprietary game files out of the public repository. If a missing mechanic becomes a blocker, inspect the relevant mod/source path first; targeted inspection or decompilation of the local game can be a later engineering task. Do not begin by reconstructing the whole game.

For CommunicationMod, respect its subprocess protocol: readiness handshake, newline-delimited messages, and stdout reserved for protocol traffic. Log diagnostics elsewhere. Confirm action indexing and state transitions against the implementation. Unsupported screens must produce an explicit capability limitation or a targeted fix. [G1]

### 3.3 Produce the first piece of evidence

Complete a combat through the original engine using a simple policy. Save the observations, selected actions, execution outcomes, and terminal result. Then demonstrate the route to another episode without human intervention.

Starting a full seeded game and navigating to a combat is acceptable initially. Do not pretend this is an arbitrary combat reset. If a selected-combat benchmark needs snapshots, implement and verify that capability separately. State exactly which starting conditions the current adapter supports.

A second fight in the same run demonstrates continuation, not reset. For a seeded restart, use a fixed noncombat prefix and preserve the resulting combat-start state. Record profile/unlock settings and initial choices that affect it. Before training, repeat the reset and a known action sequence; check normalized gameplay states in deterministic cases, and document any remaining variation.

Build only enough interface to make this exercise repeatable. A random legal-action policy is sufficient to test mechanics; it is not expected to play well.

Before long experiments, verify that:

- Actions execute against the state for which they were selected, rather than a stale observation.
- A terminal outcome comes from the engine, and another episode starts from its declared conditions.
- A failed bridge operation is distinguishable from an ordinary gameplay loss.
- The complete episode exists on disk, and any training-data ingestion consumes the intended transitions without accidental duplication.
- Restarting the runner preserves completed evidence and reports interrupted work accurately.

Test meaningful edge cases in the supported slice: card/target identity, energy costs, block and damage, status effects, and terminal transitions. Use regression cases discovered from actual failures. A test suite that merely restates the adapter's assumptions is insufficient.

### 3.4 Decide how training will run

Measure end-to-end episode and transition throughput, reset time, CPU use, GPU memory, and policy inference cost. Simulator README benchmarks are not measurements of this workload.

If a fast simulator is available, compare representative transitions and outcomes against the original engine. Test the mechanics used by the training slice and document exclusions. Matching a few traces does not establish whole-game equivalence.

If the simulator is inaccurate, fix or narrow the declared slice. If original-engine execution is too slow, profile the bottleneck and investigate acceleration. Do not spend a week training against known incorrect rules or building a new simulator without first measuring the alternatives.

**First milestone:** another coding session can reproduce a real combat, inspect a failure, and start a valid second episode using documented commands. If game access is blocked, mark this milestone incomplete; fixtures and simulator work can continue, but they do not prove original-game operation.

## 4. Keep the repository small and useful

Create files as working code needs them. A reasonable starting arrangement is:

| Location | Responsibility |
|---|---|
| `AGENTS.md` | Short operating rules, actual commands, and pointers to current state |
| `CLAUDE.md`, if needed | A thin reference to the same instructions, rather than a conflicting copy |
| `README.md` | What currently works and how to reproduce it |
| `docs/research.md` | Current question, observation/evaluation contract, decisions, and useful sources |
| `docs/state.md` | Current baseline, active work, blockers, and next useful action |
| `src/spire/` | Adapter, policy, training, evaluation, and reporting code as they become necessary |
| `tests/` | Contract checks and meaningful regressions |
| `configs/` | Resolved experiment choices; avoid a configuration framework initially |
| `runs/` | Per-run metadata, metrics, and evidence; keep bulky artifacts out of Git |

Use one locked dependency environment. Keep large trajectories and checkpoints in an explicit artifact location with stable identifiers. A few JSON/JSONL files and ordinary plots are enough initially; no experiment database is required.

Codex and Claude have their own instruction-loading rules. Verify that the active client actually loads the canonical instructions. A thin `CLAUDE.md` containing `@AGENTS.md` is a supported compatibility option; avoid duplicating rules. [D3], [D4]

### Expose operations, not a new platform

Implement a small command surface. The following names are suggestions; adapt to an existing working interface:

| Operation | Required result |
|---|---|
| `python -m spire doctor` | Capabilities, versions, resources, and precise blockers |
| `python -m spire rollout ...` | Attributable episodes from a named policy and scenario distribution |
| `python -m spire train ...` | A budgeted training job, live metrics, and resumable checkpoints |
| `python -m spire evaluate ...` | Canonical scores for a frozen artifact on a named suite |
| `python -m spire report ...` | A comparison plus links to representative evidence |

Initially implement only the operations needed for the current milestone. Ordinary functions and CLI commands are sufficient. Add a custom MCP server, dashboard, or retrieval service only when an observed limitation makes it worthwhile.

Give the agent direct access to source, targeted documentation search, commands, and logs. Return concise summaries with artifact paths; do not paste an entire trajectory into every response.

## 5. Define the experiment contract

Write this contract before comparing learned policies. Keep it small enough to inspect.

### Observation and action rules

Specify the exact public observation, including current hand, public deck information, health, energy, relics, visible enemy intent, and relevant history. Specify what is excluded.

Never expose the game seed, unrevealed draw order, private RNG state, unrevealed outcomes, or internal enemy information beyond what a player can know. Audit raw bridge fields; a field's presence does not make it legitimate policy input. A draw-pile array needs an ordering audit rather than an assumption that it is safe or that it necessarily reveals the real order. Preserve information that game mechanics legitimately reveal. [G1]

Use a policy-facing observation separate from diagnostic engine state. The evaluator calls the policy with that interface; it does not give the policy unrestricted researcher tools, reset access, or raw logs.

Represent legal atomic actions explicitly, including card and target selection and ending a turn. Tie action identifiers to the current decision state. For a neural policy, masking must agree with both sampling and probability calculations. For an LLM, validate the returned action against the same legal set.

A legality helper may filter impossible actions. A helper that chooses an optimal play sequence is already part of the strategy. Record that distinction when defining a baseline.

### What may change during research

The researcher may change policy architecture, training code, hyperparameters, data processing, and the stated experimental variable. Training reward shaping and curriculum are legitimate variables when explicitly recorded.

Within a comparison, keep game mechanics, observation/action semantics, the evaluation reset distribution, canonical scoring, and evaluation suites fixed. Record their versions or hashes. A curriculum experiment may change the training distribution as its declared variable. Do not improve a result by changing what success means.

This boundary adapts ENPIRE's released research contract, which separates policy changes from the trusted environment and requires attributable experiment records. It does not require adopting ENPIRE's services. [R3]

If a genuine environment or evaluator bug appears, preserve a reproduction, fix it, version the contract, and rerun the baseline. Work may continue autonomously, but old and new scores belong to different protocols until recomputed.

Distinguish true termination from a time or step limit. Training must handle truncation consistently with the chosen algorithm; reports must not silently turn interrupted or unsupported episodes into clean gameplay outcomes. [M1]

## 6. Build the learners in a useful order

### 6.1 Establish baselines before adding complexity

Keep a random legal policy and a simple understandable heuristic. Run both through the same interface. If importing an existing agent, identify the imported strategy and its information access.

A search-based policy may be informative, but distinguish ordinary planning from access to exact future randomness. The search documented in `sts_lightspeed` is an oracle comparison unless that privileged access is removed and verified. [G3]

These baselines diagnose the environment and show what the learned system adds. They do not need to be the eventual research contribution.

### 6.2 Train a neural policy from scratch

Start with a small PyTorch policy and a conventional algorithm such as masked PPO. Use a readable, maintained implementation as a reference; CleanRL is one such reference, rather than a modular library that must be wrapped into the project. Randomly initializing the policy and training it on game interaction counts as learning from scratch even when the optimizer and algorithm implementation are reused. [M2]

Choose an observation encoder that handles collections of cards and enemies without depending on accidental array order. A modest candidate-action scorer may be enough initially. Add recurrence or a more complex encoder only when a demonstrated information or capacity problem motivates it.

Start with a simple, documented reward aligned with the combat objective. Report gameplay outcomes separately from training return. Check that parameters actually update, data comes from the intended policy, losses remain valid, and evaluation loads the checkpoint that was just trained.

For policy-gradient updates, retain the behavior-policy version, sampled actions and log probabilities, and the action masks/candidate mapping used during collection. Respect the algorithm's assumptions about policy age and data reuse. Arbitrary old replay or data from a different observation version is not automatically valid PPO training data.

A tiny case that the policy can learn is a useful diagnostic. It is not evidence of general gameplay competence. Expand across starting health, encounters, legal deck variations, and random seeds as the environment supports them.

Investigate the observed bottleneck. Invalid actions suggest an interface problem. Slow collection suggests a systems problem. Noisy advantages or collapsed action distributions suggest a training problem. Repeated failure on an unseen encounter suggests a generalization problem. Do not respond to all four by changing the model size.

### 6.3 Add the language-model track after the loop works

Select a current, openly available pretrained model based on local memory tests, useful capability, and its model card. Roughly 0.5–3B parameters is a sensible range to investigate on 12 GB, not a fit guarantee. Test the intended context length and a full update before committing to it.

First evaluate the unchanged model using a fixed prompt, the public observation, and a compact action format. Then perform actual supervised fine-tuning on declared demonstrations, using LoRA or quantized adapters where appropriate. Those techniques reduce some memory costs; activations, long sequences, optimizer state, and rollout generation still matter. [M3]

Identify every data source: heuristic, search teacher, human play, existing dataset, or previous policy. A teacher with privileged state creates a privileged-teacher experiment even if the student later sees public observations. Do not merge that result into an unqualified comparison against a public-information teacher.

Use action targets and verifiable outcomes. Do not invent reasoning traces and call them ground-truth explanations. Freeze prompt, parser, gameplay memory, and retry rules for each evaluation.

Only then consider outcome-based post-training if it addresses a real limitation. Current TRL development documentation includes tool-using and environment-based GRPO workflows, but development documentation is not a guarantee about an installed release. Pin a compatible version and demonstrate one correct end-to-end update. Keep rollout generation small enough for the measured memory budget. [M4]

Define the rollout unit and reward assignment, for example one complete combat. Verify the association between actions, log probabilities, and outcomes. Apply the policy loss to generated policy tokens, excluding environment/tool-response text. Changing weights alone does not prove that this update is correct.

Coding subscriptions fund the research assistant; they are not an assumed unlimited API for gameplay rollouts. Local policies should continue collecting data without a Claude or Codex call per game action. API teachers or hosted gameplay models need their own explicit cost budget.

### 6.4 Borrow robotics ideas when a question calls for them

**Reward design:** after ordinary RL works, test whether a specific shaping signal improves learning. Record each reward component, train under comparable budgets, and judge the resulting policy with unchanged gameplay metrics. This is the useful Eureka mechanism. A rising shaped return with falling win rate is evidence against the candidate. [R5]

**Curriculum:** probe weak regions among valid encounters, decks, and relic combinations, then test a recorded change in training distribution. DrEureka motivates using measured weaknesses to inform randomization, but its physical sim-to-real setting is different. Randomizing rules is not a remedy for a wrong game simulator. [R9]

**Reusable gameplay skills:** later, investigate a frozen library of tactical routines with clear preconditions, or a hierarchical policy. Compare it with a policy without the library under declared action and compute budgets. Keep this track distinct from both neural training and the coding agent's own debugging guidance.

## 7. Run experiments that answer a question

Choose one current question, such as:

> Does a card-set encoder improve performance on unseen Act 1 encounters at the same training budget?

Or:

> Does reward shaping improve early learning while preserving final combat success and health outcomes?

For each candidate:

1. State the hypothesis, changed variables, baseline, comparison budget, and what would count against the hypothesis.
2. Run the smallest meaningful correctness check and a short training pilot.
3. Inspect the pilot for broken data flow, invalid actions, unstable learning, and memory/throughput problems.
4. If valid, run the larger experiment within the remaining budget.
5. Evaluate the saved artifact with the canonical development suite and inspect representative regressions.
6. Mark the result **keep**, **reject**, **inconclusive**, or **invalid**, with evidence and a next step.

An invalid run says little about the algorithm. A small noisy improvement may be inconclusive. Preserve both outcomes instead of forcing every attempt into success or failure.

Do not require one-line edits or a ritual sequence of research agents. A coherent implementation change may span several files. Keep the experimental difference explainable; use an ablation when interacting changes prevent attribution.

### Minimum run record

Store a machine-readable manifest beside the results. It should resolve:

| Question | Recorded evidence |
|---|---|
| What ran? | Source commit and any dirty diff; exact command; resolved configuration |
| What was changed? | Hypothesis, baseline identifier, changed variables |
| What world was used? | Engine/mod/simulator versions; observation and evaluator versions; suite identifier |
| What learned? | Initialization, checkpoint ancestry, training-data sources, algorithm |
| What resources were spent? | Intended and actual runtime, steps/episodes, peak memory, relevant model/token use |
| What happened? | Exit status, metrics, raw evaluation output, checkpoint identifier, selected traces |
| What follows? | Retention decision, uncertainty, next useful experiment |

Save checkpoints atomically and give each a stable identifier or hash. Never use an unqualified `latest` path as the only evidence for a public result. Reports should derive numbers from saved evaluation output, not from an agent's remembered narrative. This addresses the method/code/result disconnect identified by ScientistOne. [R6]

A resumable checkpoint must include the training state the algorithm needs: optimizer/scheduler state, random generators, normalization, counters, and any required replay state. If a live game cannot be restored, mark that episode interrupted and restart it under the declared rules.

### Retain useful knowledge

After a validated repair, add a short record containing **symptom, evidence, cause, repair, applicability, and regression check**. For example: a stale card index was used after a draw changed the hand; the repair binds action candidates to the observed state and is checked by a replay.

This adapts ASPIRE's trace-based repair mechanism. Keep records searchable in ordinary files. Consolidate repeated findings into a small workflow or skill only when repetition makes that worthwhile. A large skill catalog at project creation adds maintenance without evidence of benefit. [R4]

Keep coding knowledge separate from policy inputs. Research notes can include diagnostic engine information; a gameplay memory library must obey the policy's information contract and be frozen for final evaluation.

## 8. Make evaluation resistant to self-deception

Use three distinct purposes:

- **Training:** data collection and parameter updates.
- **Development:** repeated comparisons, debugging, and candidate selection.
- **Final test:** evaluation of the selected, frozen candidate after development decisions are complete.

A second set used to choose a winner is still validation, even if its filename contains `test`. Reusing a final test result to choose the next experiment makes that set part of development. Keep the canonical scorer and split definitions stable. These choices apply AIRA₂'s separation of search and selection to the game. [R7]

Specify what is held out: random seeds, starting snapshots, encounter types, decks, or combinations. New seeds for familiar enemies do not establish performance on unseen encounters. Split demonstrations by originating run or snapshot family before generating examples; keep duplicates and derived turns with their origin. Exclude held-out evaluation trajectories from fine-tuning and other training data.

Do not promise an adversarially secure benchmark simply because an agent was told not to open a file. Initially, use clear separation, recorded suite identities, and reproducible evaluation. Stronger isolation is a later requirement if the project specifically studies evaluator exploitation.

### What to measure

For a combat benchmark, report wins and denominator, health outcomes, turns, invalid actions, infrastructure failures, and inference/runtime cost. State starting-condition distributions and mechanic coverage. For larger scopes, report their own completion metrics. Combat wins do not imply full-run wins.

If training mainly uses a simulator, validate the selected learned policy in the original engine on a declared suite before claiming original-game performance. Label simulator and original-engine results separately; a working bridge demonstrated with a heuristic does not establish transfer of the learned policy.

For selected results, repeat independent training seeds as affordable and evaluate on more than the debugging scenarios. Separate variability from training initialization from variability across game scenarios. Compare candidates on matched scenario suites; shared game seeds do not guarantee identical random event streams when policies take different actions.

Report uncertainty rather than only the highest observed score. At 100 independent games, a win rate around 50% has roughly a ±10 percentage-point 95% sampling interval; correlated scenarios can provide less information. Small differences on small suites should trigger confirmation, not a breakthrough claim.

When comparing RL and LLM policies, state input information, training data, inference/search budget, and any pretraining advantage. There is no single automatically fair compute comparison; choose and explain the comparison relevant to the question.

**Count attempts honestly.** Normal evaluation does not rewind an episode after an unfavorable action. Parser repair, environment recovery, and strategy retries must have explicit rules and separate counts. ENPIRE's showcased pass@8 permits failure-conditioned retries; it is not a one-attempt game win rate. [R2]

Infrastructure errors must remain visible. For operational success, include their cost; for policy-quality estimates, separately report valid episodes and explain exclusions. Preserve both the original attempt and any justified rerun. Never discard hard gameplay losses as infrastructure problems.

Freeze policy weights and any cross-episode memory during ordinary final evaluation. Reset per-run state as specified. If online adaptation is the research topic, define it as a separate track with its own data and reset rules.

## 9. Use overnight time without building a second coding agent

An overnight run needs an objective, a resource boundary, and a resumable result. It does not need a custom swarm.

### Choose a budget from measurements

When asked to work overnight and no duration is supplied, use **eight hours as a declared local default**, subject to existing authorization and machine availability. This is a project default, not a claim about provider quotas. Use no new paid API or cloud budget unless authorized.

Run a short pilot, estimate candidate cost, and reserve time for evaluating or confirming the best candidate. Then choose how many experiments fit. Do not copy autoresearch's trial count, impose an arbitrary three-run ceiling, or spend the whole window generating unconfirmed candidates.

Put the deadline and step/episode limits in the process runner. Checkpoint before stopping and ensure owned child processes respect the limit. A natural-language goal is not a hard runtime or spending control.

### Use existing client capabilities

Use the coding client's native long-running goal, background-job, and resume facilities when available. Codex and Claude both document goal workflows; verify the active version rather than creating an outer loop immediately. [D5], [D6]

For subscription-based Claude sessions, current interactive mode documents waiting for eligible usage-limit resets and resuming. Headless/background sessions do not have the same behavior. Do not assume all launch modes consume the same quota or automatically recover. [D7]

Keep training jobs, logs, and checkpoints independent of the chat session. A quota limit should pause further research decisions without destroying valid training already running. Use the client's job controls or the host's ordinary process/session tools. Persist what is needed to reconnect; prevent a resumed session from launching a duplicate job.

### Spend scarce resources deliberately

Use one training job on the GPU initially. While it runs, the coding researcher may inspect earlier failures, review an upstream implementation, prepare a CPU check, or plan the next candidate. A temporary subagent can investigate an independent question or review a risky change. Parallel work must have distinct ownership and a concrete deliverable.

If two coding agents edit concurrently, use separate branches or worktrees and avoid overlapping file ownership. Merge deliberately. A second model agreeing with a claim is not a replacement for rerunning its evidence.

Measure useful throughput before increasing workers. More agents may consume subscriptions faster without producing more completed experiments. Reassess parallelism when profiling shows idle resources or truly independent work.

### Monitor and finish cleanly

Monitor episode counts, learner updates, data ingestion, resource use, and process exit status. A quiet log alone does not establish failure; a running process alone does not establish progress. Use observed progress signals to detect stalls.

Stop launching new trials when the remaining window cannot cover training and evaluation. On repeated identical infrastructure failure, change the diagnosis instead of retrying indefinitely. Stop the affected experiment if its observation/evaluation contract is invalid, disk is insufficient, or the declared budget is exhausted. Continue a useful independent task where feasible.

Before handing off, update `docs/state.md` with:

- The best verified artifact and exact reproduction command.
- Completed experiments, including invalid and inconclusive attempts.
- Active jobs and how to inspect or stop them.
- Consumed resources and any remaining budget.
- The next useful action and unresolved uncertainty.

“No improvement found” is a valid night's result. An unsupported improvement claim is not.

## 10. Expand through evidence-based milestones

| Milestone | Evidence required before moving on |
|---|---|
| **A. Real interaction** | A reproducible combat trace, correct outcome, and automatic route to another episode |
| **B. Trustworthy training slice** | Declared mechanics and start distribution; simulator/engine checks where applicable; measured throughput; baseline results |
| **C. Learned policy** | Verified weight updates, resumable training, and development results against the baselines |
| **D. Generalization study** | Selected comparisons across held-out scenarios and repeated training runs, with uncertainty and failure analysis |
| **E. LLM post-training** | Untuned-model baseline, identified training data, actual trained adapters/weights, and a controlled evaluation |
| **F. Broader gameplay** | Supported noncombat decisions, longer-horizon evaluation, and results specific to Act 1 or full runs |

Do not assign optimistic calendar dates before measuring throughput. A strong narrow study is a useful deliverable while broader gameplay develops.

Choose a focused contribution once the baseline exposes a worthwhile question: structured representations, sparse versus shaped rewards, teacher information, tactical skill reuse, sample efficiency, or simulator fidelity. The project need not invent a new algorithm to be credible. It does need a clear account of what was reused, what changed, and what the evidence supports.

The final project should include reproducible commands, a bounded benchmark definition, plots and tables generated from saved results, a playable demonstration, useful failures, and an explanation the owner can defend. Do not claim stronger gameplay or greater autonomy than the implementation demonstrates.

## 11. Entry prompts

These prompts assume this file is in the repository root. Adapt paths if it is moved.

### Bootstrap

```text
Read SLAY_THE_SPIRE_AGENT_GUIDE.md and the repository instructions.
Execute the first applicable milestone. Inspect what already works,
then build and verify the smallest missing piece. Handle routine local
setup yourself. Use existing integrations where justified. Preserve
evidence and leave actual reproduction commands. Do not stop at a plan.
If an external-access blocker prevents progress, explain it precisely
and continue independent work that advances the milestone.
```

### Overnight research

```text
Read the repository instructions and docs/state.md. Continue the current
research question within the overnight budget defined in the guide and
any more specific budget already authorized in this session. Confirm
the baseline, evaluator, and active jobs before launching more work.
Choose experiments from measured bottlenecks; reserve time to evaluate
the selected candidate. Preserve failed and inconclusive attempts.
Finish with the best verified artifact, evidence, resource use, and a
resumable next step. Do not add paid services or expand scope silently.
```

### Independent review

```text
Audit the selected result against its source commit, configuration,
checkpoint, and raw evaluation output. Check information leakage,
evaluation consistency, actual weight training, data provenance, and
the attribution of the reported gain. Run targeted checks needed to
resolve concrete concerns. Report what the evidence supports, what
remains uncertain, and any correction required before promotion.
```

## 12. Primary sources

Dates identify the material examined, not a promise that a repository will remain unchanged. Verify live documentation when adopting a dependency. None of the robotics systems below needs to be installed for this project.

### Research

- **[R1]** Brilliantov, Hernández-Cano, and Abbe, Apple/EPFL. [How Much of a Harness Does a Strong Agent Need for Autonomous ML Engineering?](https://arxiv.org/html/2609.40303v1), 30 September 2026. Matched harness experiments; useful evidence for starting with a strong coding session.
- **[R2]** Xiao et al., NVIDIA/CMU/UC Berkeley. [ENPIRE, v2](https://arxiv.org/html/2606.19980v2), 20 September 2026; originally 18 June. [Project](https://research.nvidia.com/labs/gear/enpire/) and [code](https://github.com/NVlabs/ENPIRE). Reset/verification and policy-improvement separation; inspect the retry metric carefully.
- **[R3]** NVlabs. [ENPIRE Auto-Research Contract](https://github.com/NVlabs/ENPIRE/blob/main/enpire/policy/autoresearch_instruction.md). Concrete boundaries and experiment provenance. The [release workflow notes](https://github.com/NVlabs/ENPIRE/blob/main/enpire/env/docs/REAL_WORLD_WORKFLOWS.md) identify components not included in the public release.
- **[R4]** Lu et al. [ASPIRE: Agentic /Skills Discovery for Robotics](https://arxiv.org/html/2607.00272v1), submitted 30 June 2026. [Project](https://research.nvidia.com/labs/gear/aspire/) and [code](https://github.com/NVlabs/ASPIRE). Trace-based repair and program/skill refinement; its reproduction stack is not the proposed local architecture.
- **[R5]** Ma et al. [Eureka: Human-Level Reward Design via Coding Large Language Models](https://eureka-research.github.io/), 2023 / ICLR 2024. [Code](https://github.com/eureka-research/Eureka). Established reward-design mechanism, not a new 2026 release.
- **[R6]** Google Cloud AI Research and collaborators. [ScientistOne: Towards Human-Level Autonomous Research via Chain-of-Evidence](https://arxiv.org/html/2605.26340v1), 25 May 2026. Evidence connecting claims, code, and results.
- **[R7]** FAIR and collaborators. [AIRA₂: Overcoming Bottlenecks in AI Research Agents](https://arxiv.org/html/2603.26499v2), 13 April 2026 revision; originally 27 March. Consistent evaluation and separation of search from selection.
- **[R8]** Andrej Karpathy. [autoresearch](https://github.com/karpathy/autoresearch) and [research instructions](https://github.com/karpathy/autoresearch/blob/master/program.md), March 2026. A compact example of autonomous measured iteration.
- **[R9]** Ma et al. [DrEureka: Language Model Guided Sim-To-Real Transfer](https://eureka-research.github.io/dr-eureka/), RSS 2024. Conditional inspiration for distribution experiments; not a game-simulator correctness method.

### Game integrations

- **[G1]** [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod): original-engine protocol, commands, exposed state, and documented limitations.
- **[G2]** [spirecomm](https://github.com/ForgottenArbiter/spirecomm): Python communication and example agent.
- **[G3]** [sts_lightspeed](https://github.com/gamerpuppy/sts_lightspeed): C++ simulator, coverage claims, and search assumptions.
- **[G4]** [LudicrousSpeed](https://github.com/boardengineer/LudicrousSpeed): candidate original-engine acceleration.
- **[G5]** [STSStateSaver](https://github.com/boardengineer/STSStateSaver): candidate saved-state support.

### Coding-agent documentation

- **[D1]** [OpenAI model guidance](https://learn.chatgpt.com/docs/models).
- **[D2]** [Claude Code model configuration](https://code.claude.com/docs/en/model-config).
- **[D3]** [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
- **[D4]** [Claude Code memory and instructions](https://code.claude.com/docs/en/memory).
- **[D5]** [Codex long-running work](https://learn.chatgpt.com/docs/long-running-work).
- **[D6]** [Claude Code goals](https://code.claude.com/docs/en/goal).
- **[D7]** [Claude Code interactive usage-limit recovery](https://code.claude.com/docs/en/interactive-mode#wait-for-a-usage-limit-to-reset).

### Training references

- **[M1]** [Gymnasium environment API](https://gymnasium.farama.org/api/env/): termination and truncation semantics.
- **[M2]** [CleanRL documentation](https://docs.cleanrl.dev/): readable reference algorithm implementations.
- **[M3]** [PEFT quantization guide](https://huggingface.co/docs/peft/v0.21.0/en/developer_guides/quantization): quantized adapter training.
- **[M4]** [TRL GRPO development documentation](https://huggingface.co/docs/trl/main/en/grpo_trainer) and [memory guidance](https://huggingface.co/docs/trl/main/en/reducing_memory_usage): verify compatibility with the selected release.

[R1]: https://arxiv.org/html/2609.40303v1
[R2]: https://arxiv.org/html/2606.19980v2
[R3]: https://github.com/NVlabs/ENPIRE/blob/main/enpire/policy/autoresearch_instruction.md
[R4]: https://arxiv.org/html/2607.00272v1
[R5]: https://eureka-research.github.io/
[R6]: https://arxiv.org/html/2605.26340v1
[R7]: https://arxiv.org/html/2603.26499v2
[R8]: https://github.com/karpathy/autoresearch
[R9]: https://eureka-research.github.io/dr-eureka/
[G1]: https://github.com/ForgottenArbiter/CommunicationMod
[G2]: https://github.com/ForgottenArbiter/spirecomm
[G3]: https://github.com/gamerpuppy/sts_lightspeed
[G4]: https://github.com/boardengineer/LudicrousSpeed
[G5]: https://github.com/boardengineer/STSStateSaver
[D1]: https://learn.chatgpt.com/docs/models
[D2]: https://code.claude.com/docs/en/model-config
[D3]: https://learn.chatgpt.com/docs/agent-configuration/agents-md
[D4]: https://code.claude.com/docs/en/memory
[D5]: https://learn.chatgpt.com/docs/long-running-work
[D6]: https://code.claude.com/docs/en/goal
[D7]: https://code.claude.com/docs/en/interactive-mode#wait-for-a-usage-limit-to-reset
[M1]: https://gymnasium.farama.org/api/env/
[M2]: https://docs.cleanrl.dev/
[M3]: https://huggingface.co/docs/peft/v0.21.0/en/developer_guides/quantization
[M4]: https://huggingface.co/docs/trl/main/en/grpo_trainer
