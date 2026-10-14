# Planned Slay the Spire track: a remotely trained open-weight model

*Owner direction, 2026-10-12. The Spire full-run track with `gpt-6-luna` continues. At some
point the Spire work will also test an open-weight model that is served and trained remotely.
This page records the proposed plan. Only a code skeleton exists
([Code skeleton](#code-skeleton)). Facts were checked on 2026-10-12.*

**Question.** Does learning what actions do help an LLM become a better player, with less training
and better generalization? The plan uses game-reward RL as the foundation and adds one experiment
that also trains the model to predict the game's response to each action.

**Models and stack.**

| Role | Model | Architecture on Tinker | Tinker $ per million tokens (prefill / sample / train) |
|---|---|---|---|
| Main experimentation model | Qwen3.6-35B-A3B | MoE, 35B total, 3B active, 64K context | 0.45 / 1.335 / 1.177 |
| Frontier model | GLM-5.3 | MoE, 753B total, 40B active, listed only with 256K context | 3.78 / 12.15 / 14.58 |

- **Tinker:** it trains LoRA adapters remotely, while this computer keeps the game, any simulator
  and the orchestration.
  - Its cookbook has a `verifiers_rl` recipe that trains Prime Intellect Verifiers environments
    installed into the local project.
  - The recipe page names no algorithm and does not say whether multi-turn environments work. The
    pilot must check both.
  - Pin the `verifiers` version, because its main branch has removed the v0 API.
- **Prime Intellect** stays relevant for its environment and training frameworks. Its Hosted
  Training needs beta access and bills per GPU-hour, so the plan starts on Tinker.
- **Evidence on the chosen models.** On SpireBench (StS1, A20, maximum or extra-high reasoning
  effort, 10 runs each; see the [approaches.md addendum](../approaches.md#addendum-2026-10-12-self-improving-harnesses-an-sts1-benchmark-and-training-services)):
  - Qwen3.6-35B-A3B had the lowest mean floor of the open models listed (10.2, no act cleared).
  - GLM-5.3 matched the human telemetry mean floor (22.1).
  - If the untouched Qwen cannot use the interface, two models sit in between:

    | Model | SpireBench mean floor | Tinker $ per million tokens (prefill / sample / train) |
    |---|---|---|
    | GLM-5.3-Flash | 15.6 | 0.84 / 2.11 / 5.58 |
    | Qwen3.8-27B | 14.9 | 0.6975 / 5.595 / 4.103 |
- **Retirement:** Tinker shows no retirement date for either chosen model. Its sibling
  Qwen3.6-27B retires on October 23.

**Terms.** RLVR names the reward source: results a program can check, such as winning a fight.
GRPO is the update rule: it compares several attempts at the same scenario and reinforces the
better ones. A win can be verified, but whether each move was optimal usually cannot. Randomness and
delayed consequences still matter.

**Plan.**

A. **A trustworthy training environment.**
   - Ironclad, Ascension 0. Start with varied combat scenarios and move toward full runs.
   - Compact structured observations and legal actions, limited to what a player can know (the
     existing `Decision` boundary).
   - CommunicationMod stays the real game, and sts_lightspeed is the candidate for fast training.
     Its README describes its tree search as "knowing the state of the game's rng", lists RNG-free
     search only as a planned feature, and loads saves only into combat. Fair search and reliable
     resets therefore need an audited adapter; [approaches.md section 1](../approaches.md#1-pure-rl-and-search-the-strongest-bots-built-on-a-simulator-this-project-lacks) covers the parity work.

B. **Measure the starting point.**
   - Run the untouched Qwen and GLM and the scripted heuristic on the same development scenarios.
   - Measure win rate, invalid actions, tokens and cost.
   - If a model struggles with the interface or rarely wins, give it a small supervised warm start
     on verified successful trajectories. Otherwise go straight to RL, so a large demonstration
     dataset is not a prerequisite.

C. **Train on game outcomes.** Use RLVR with GRPO, on a curriculum: single fights, then varied
   Act 1 encounters, then complete Act 1, then full runs.
   - **Combat rewards:** winning comes first and remaining HP second.
   - **Full-run rewards:** optimize victory. Damage dealt and floors reached are diagnostics that
     can reward strategies that lose.
   - **Seeds:** training, validation and final-test seeds stay separate from the start, including
     combat snapshots taken from those seeds.

D. **One research experiment: ECHO-style dynamics learning.** Alongside the action reward, train
   the model to predict what an action changes: damage, block, energy and statuses.
   - **ECHO** (Prime Intellect, 2026-06-10; arXiv 2605.24517) adds supervised learning on the
     environment's response tokens to RL on the model's own tokens. It does this by giving those
     tokens a constant positive advantage α.
   - **Its evidence is mixed.** On Qwen3-4B-Instruct and GLM-4.5-Air it helped some held-out tasks
     (Wordle consistently) and hurt others (`general-agent`). GLM collapsed after about 50 steps at
     α = 0.05, and one Qwen run overfit after about one epoch. The authors suggest using it only
     for the first few hundred steps.
   - **Targets here:** compact, observable state changes. Random draws are treated as uncertainty:
     predict the multiset of cards, not their order. No future observation enters the policy's
     input when it chooses an action.

   | Arm | What it tests |
   |---|---|
   | Untouched model | Existing ability |
   | Game-reward RL | Benefit of learning through play |
   | RL plus dynamics prediction | Whether modelling consequences improves learning and generalization |

E. **Scale the winning recipe.**
   - Repeat it on GLM-5.3.
   - Evaluate on untouched seeds and unfamiliar deck and relic combinations, then confirm on the
     real game.
   - Report win rate with uncertainty, training cost and inference cost, so the result can be
     judged even if the smaller model stays the better value.

**Later, and left out.**
- **Bounded search followed by distillation (later):** explore continuations at hard decisions,
  then train the model to reproduce the better choices with fewer searches. This waits until a
  simulator can branch without revealing hidden futures. The distillation forms in [approaches.md section 5](../approaches.md#5-distillation-from-frontier-models-cheap-labels-capped-by-the-teacher) apply.
- **RLCD (left out):** the training method behind TypeSafe AI's Jev model (announced 2026-10-12)
  targets calibrated probabilities for structured decisions. The announcement gives no algorithm,
  paper or code, and no evidence on long decision sequences.

**Priority.** Build a reliable environment, then show a measured RL improvement, then run the
dynamics experiment, then train the frontier model, then add search and distillation. Before
scaling, a short cloud pilot measures the actual cost of rollouts and updates, since long game
histories can make tokens the deciding cost.

**What the Spire tracks' evidence adds.**
- **Engine time (estimate):**
  - On the real engine there is one controller, at about 38 s per combat.
  - A GRPO step of 64 combats takes about 40 minutes plus remote sampling latency, which has not
    been measured. That is roughly 30 steps a day.
  - Full-run groups would take hours per step, so stages past Act 1 likely need the simulator.
- **Token cost per step (estimate):**
  - Assumptions: 28 decisions per combat, 1.5k prompt and 200 sampled tokens per decision, each
    decision trained as its own sequence, and no thinking tokens.
  - A 64-combat step then costs about $5 on Qwen3.6-35B-A3B and about $59 on GLM-5.3. Thirty
    steps cost about $160 and $1,770.
  - Thinking tokens or turn histories raise both figures. The pilot replaces them with
    measurements.
- **Saturated rewards:** on the current floor-1 catalog the heuristic wins 12 of 12. The one
  real-engine REINFORCE update raised macro HP from 63.67 to 66.67, with 12 of 12 wins before and
  after. Win-based rewards need harder scenarios where policies lose ([approaches.md section 10](../approaches.md#10-recommended-sequence-for-this-project), first step). On
  easy fights, HP is the signal.
- **Warm-start data:** successful trajectories from the heuristic or the open model itself avoid
  the terms question that Luna-derived data would raise ([approaches.md section 5](../approaches.md#5-distillation-from-frontier-models-cheap-labels-capped-by-the-teacher)).

## Code skeleton

`src/spire/openweight/` (2026-10-12) sets the module layout; it trains and plays nothing yet.
Unbuilt functions raise `NotImplementedError`, and `tests/openweight/` covers the parts that
work.

| Stage | Module | State |
|---|---|---|
| A | `tasks`: curriculum `Stage`, `Split`, `Task`, `check_splits` (a seed in one split only) | Splits checked; declarations not designed |
| A | `env`: a step interface (`reset`, `step`) with `RealGame` and `Simulator` backends | Interface only |
| B, C | `policy`: `SampledPolicy` with the `fullrun` policy interface, so `spire.fullrun.play` can run it | Placeholder prompt and reply |
| B, E | `evaluate`: every arm on the same tasks, with a Wilson interval on the win rate | Interval only |
| C | `rewards`: fights score win then HP, full runs score victory alone | Working; HP scale is a placeholder |
| C | `rollout`: episodes and groups recording sampled tokens and the next observation | Working on a fake environment |
| C, D | `grpo`: `GRPOConfig` with the ECHO `echo_alpha`/`echo_steps` arm, `group_advantages` | Advantages only |
| D | `dynamics`: observable changes per action as ECHO targets | Target list only |
| infrastructure | `remote`: Tinker session, prices, a separate `runs/tinker-spend.jsonl` ledger | Prices only; no SDK dependency |

Gaps the skeleton makes visible:

- `RealGame` has to invert `spire.fullrun.play.play_run`'s loop, which calls the policy, into
  `reset`/`step` without changing the trace.
- No scripted heuristic plays full-run decisions; `spire.policies` covers only the starter
  first combat.
- Fight and Act 1 tasks need a way to start mid-run: a recorded prefix on the real game, or
  a snapshot on the simulator.
- The Tinker SDK needs its own extra in `pyproject.toml`, pinned, before the first call.

## Starting points in this repository

- **Full runs:** `spire.fullrun.play.play` takes a `policy_factory`. A policy needs
  `choose(decision) -> Choice`, `choice_metadata(decision_id) -> dict` (saved in the trace)
  and optionally a `totals` mapping. `spire.decisions` is the public full-run boundary,
  `gameai.ledger` the spend cap, and `spire.fullrun.llm.render_prompt` the current text
  rendering.
- **Combat scenarios:** `spire.combat` runs seeded first-combat suites and catalogs, but
  its observation contract (`spire/protocol.py`) covers only the starter cards. Varied
  scenarios need the full-run boundary or a new admitted contract;
  [first-combat/README.md](../first-combat/README.md) records what was verified.
- **Local RL references:** `spire.language.sampling` scores legal choices as a normalized
  candidate distribution, and `spire.language.rl` is an audited REINFORCE loop on it.
  Both assume a local model, not a remote sampler.

## Sources

- [Tinker model catalog (models.json)](https://tinker-docs.thinkingmachines.ai/tinker/models.json)
- [Tinker cookbook, Verifiers RL recipe](https://tinker-docs.thinkingmachines.ai/cookbook/recipes/verifiers-rl/)
- [Prime Intellect, ECHO: true agents model the world (2026-06-10)](https://www.primeintellect.ai/blog/true-agents-model-the-world)
- [ECHO, arXiv 2605.24517 (linked from the post)](https://arxiv.org/abs/2605.24517)
- [TypeSafe AI, Introducing System One models and Jev (2026-10-12)](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
