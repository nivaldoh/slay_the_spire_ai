# Approaches to an AI that plays Slay the Spire

*Research snapshot dated 2026-10-11, synthesized from eleven research notes compiled that day (the
notes stay outside Git, under `runs/research-notes/`). "Estimate" marks a number a researcher
computed from stated assumptions rather than one a source reported. "Self-reported" marks a
result its authors published and nobody has reproduced. Prices are list prices read on
2026-10-11. Project facts come from [state.md](state.md) and [research.md](first-combat/research.md). An
addendum dated 2026-10-12 comes before the sources; the owner's plan for a remotely trained
open-weight model, also dated 2026-10-12, is in [open-weight/README.md](open-weight/README.md).*

## Summary

As of October 2026 no single technique plays the full game of Slay the Spire well. The strongest
public players are hybrids in which tree search over a fast simulator plays combat and a
heuristic, a small learned network or an LLM makes the other decisions. On the sts_lightspeed
simulator such bots report **82.5% wins at Ascension 0 with Ironclad** (the "heart1" bot,
measured in the simulator; [typed-decision-slay-the-spire](https://github.com/MindrLabs/typed-decision-slay-the-spire))
and **50.1% Heart wins at Ascension 20** (self-reported, over 501 original-game runs;
[sts-ironclad-agent](https://github.com/destire-mio/sts-ironclad-agent)), but several of these
searches read hidden RNG, so every comparison needs an information-access column. LLMs alone are
far behind: frontier models won **0 of 25** zero-shot Slay the Spire 2 runs at A0 in May 2026
([ClaudePlaysTheSpire](https://github.com/hiKareeem/ClaudePlaysTheSpire/blob/main/docs/benchmark/trial-v0-summary.md)), the best scaffolded
agent won 6 of 10, not significantly better than its 3 of 10 baseline
([AgenticSTS](https://arxiv.org/abs/2607.02255)), and a Qwen3.5-9B fine-tuned on about 40k
search-bot decisions reached a mean floor of 19.5 without a win. For this project the
deciding constraint is **engine wall-clock, not GPU or money**, and that wall-clock is mostly not
game logic: in the project's traces, about 61% of a heuristic fight is animation timers the engine
plays out in real time and 26% is starting a fresh JVM. Today the engine yields roughly
1,400–2,900 combats a day on one controller (estimate). JVM reuse, a fixed-step no-render mod and
3–4 parallel instances could raise that 10–40×, and a parity-checked C++ engine such as
sts_lightspeed by 10^2.5× or more (estimates); a JAX port is not worth its cost for a rule-heavy
game. The RL successes worth copying used from about 15,000 simulated runs to hundreds of
millions of games. That argues for five moves in order: tighten the evaluation (held-out and
harder scenarios, HP-based paired comparisons); speed up the real engine behind a parity gate;
improve the local language policy with the changes that have direct evidence (MLP-inclusive LoRA,
turn-level credit, a 2–4B Qwen3.5 base); add a frontier model as a measured baseline and offline
teacher; and, if the goal becomes the full game, validate a fast simulator against the project's
audited traces before training on it. Paid services buy bigger models, not more samples. The project's distinctive
asset is its honest-information, audited, real-engine evaluator: the notes found no
peer-reviewed Slay the Spire paper with real-engine RL results and no published RL-trained LLM
for the game. Section 11 sketches two later directions that keep that focus: interpretability of
every policy, with behavioral tests for closed API models and mechanistic tools for the local Qwen
(ready-made transcoders exist for its exact base model); and robot-learning methods that fit the
project's slow, verified engine (ENPIRE's agent contract, RECAP-style advantage-conditioned
post-training, AutoEval-style evaluation and SIMPLER-style sim-to-real metrics).

## Comparison of paths

| Path | What it is | Frontier example (date) | Slay the Spire prior work | What this project would need | Rough cost / time (estimates unless noted) | Main risk |
|---|---|---|---|---|---|---|
| 1. Pure RL and search | Policy/value nets trained on environment reward; MCTS or Gumbel search over a simulator; world models | Ataraxos, superhuman Stratego for under $8k on 16 H100s for a week (2025–26); Generals.io, #1 on a human ladder after 4×H200 × 4 days (Jun 2026) | heart1 82.5% A0 wins in simulator; sts-ironclad-agent 50.1% A20 Heart (self-reported); six failed attempts to distill MCTS combat into a network | Python binding to an sts_lightspeed fork, parity check against audited traces, HP or run-value reward, entity-based masked policy | ~$0 on the local GPU; a 50k-step single-fight budget is ~15–40 h on today's engine, ~0.4–4 h if the 10–40× real-engine speedups hold; full-game RL needs a simulator | Simulator fidelity unquantified; RNG-aware teachers leak hidden information |
| 2. Local small-LLM fine-tuning | LoRA SFT, then on-policy RL (GRPO family, turn-level credit) on a ≤4B model | GiGPO: Qwen2.5-1.5B 86–87% on ALFWorld vs 48% for prompted GPT-4o (NeurIPS 2025) | Orak: Llama-3.2-3B 0 → 10.7 after SFT; 9B LoRA reached floor 19.5, 0 wins; this project 12/12 at macro HP 76.33 | MLP-inclusive LoRA, Qwen3.5-2B/4B, turn-level advantages, harder and held-out scenarios | $0 cash; ~6–12 min engine time per 12-combat iteration; 1,000 combats = 8.3–16.7 h | Sample starvation; memorizing fixed seeded lines |
| 3. Frontier inference with scaffolding | A closed model picks each action from a bounded prompt with notes, game knowledge and tools | BalatroBench: Gemini 3 Pro 9/15 wins at $11.16/run (Feb 2026); AgenticSTS 6/10 at StS2 A0 (Jul 2026) | Orak StS1 best normalized score 51.9 (Gemini-2.5-pro); SpireBench StS2 0/25 | Full-run controller (map, events, shops, potions), candidate-index prompt, caching, cost logging | $0.50–5 per full run (cheap tier) to $18–90 (Claude Opus 5.5); 1–10 h per run | Low, uncertain win rate with wide confidence intervals; cost of enough runs |
| 4. Remote fine-tuning/RL services | Rent the trainer (Tinker, Fireworks Training API, rented GPUs) while the game loop stays local | Tinker client-side training loop; Fireworks Training API GA 2026-08-31 | None found | A client-side-loop API (the Windows game cannot be hosted) and a ≥4B base model | ~$29–80 per 1,000 combats on Tinker; rented RTX 4090 $6–15 per 17 h | Buys model size, not throughput; heavy vendor churn in 2026 |
| 5. Distillation from frontier models | A teacher labels states offline (for SFT) or scores student tokens (on-policy distillation) | On-policy distillation 74.4% AIME'24 in 1,800 GPU-h vs RL 67.6% in 17,920 (Qwen3 report via TML, 2025) | Orak: ~11k GPT-4o/o3-mini samples lifted Llama-3.2-3B to 10.7 (GPT-4o itself: 23.6) | Batch relabeling of saved public `Decision`s; an open-weight teacher for on-policy distillation | ~$175 per 10,000 relabeled decisions (Claude Sonnet 5.5, Batch API) | Student capped by the teacher; "competing model" terms of service |
| 6. Autoresearch and program search | A coding agent edits policy code against a fixed evaluator; LLM-guided program evolution; code-as-policy | Karpathy autoresearch cut nanochat time-to-GPT-2 from 2.02 h to 1.65 h (Mar 2026); AlphaEvolve (2025) | None published for StS1; DemoEvolve raised StS2 mean floor 18.17 → 28.83 | Read-only evaluator, hidden held-out catalog, keep/reset log; a simulator for evolution at scale | ~12 candidates/h, ~100 overnight on the real engine; a 150-generation run ≈ 12.6 h | Evaluation noise; reward hacking (30.5% unprompted in a Sep 2026 study) |
| 7. Multi-agent systems and swarms | In the player: voting, routing, escalation. As builders: planner/worker/judge coding agents | Carlini's C compiler, 16 agents, ~$20k (Feb 2026); a single minimal agent beat elaborate harnesses, 62.5% vs 47.1% medal rate (Sep 2026) | spire-agent routes decisions to Map/Build/Combat sub-agents; no true multi-agent StS player | One serialized evaluation queue, a triage judge, workers in worktrees | Agent teams use ~7× the tokens of one session | Sequential tasks lose 39–70% under multi-agent designs; the engine is the critical path |
| 8. Imitation from human run data | Learn card-pick, path or value models from recorded runs | DraftFM: 1.6M-parameter MTG draft model on 149M human picks (Aug 2026) | ~75–77M-run dump (2018–2020, ~380 GB), no per-turn combat actions | Download and parse the dump; human HP-loss baseline per floor-1 encounter | ~380 GB of JSON; provenance and licence unverified | No combat actions to imitate; licence unstated |
| 9. Hybrids | Search for combat plus learned or LLM strategy; an LLM as prior or coach for RL | PokéChamp, LLM inside minimax, 76% vs the best prior LLM bot (ICML 2025) | Every strong StS bot above is a hybrid | A validated simulator and an information-honest search | Sum of the parts | Integration complexity; hidden-information leaks |

## Where this project starts

The project drives the original Slay the Spire 1 engine (game version 12-18-2022, Steam build
10180494) through
CommunicationMod 1.2.1 with ModTheSpire and BaseMod, with the controller in WSL and the game on
Windows. Every fight gets a fresh JVM, a first-floor combat takes 30–60 s including about 14 s of
game start, and only one game controller may run at a time. There is no simulator: LudicrousSpeed
and STSStateSaver were inspected and rejected because neither has a licence file, both target
older versions, and STSStateSaver removes six potion types at startup
([integration.md](integration.md)); sts_lightspeed has not been evaluated. The scope is Ironclad,
Ascension 0, first-floor combat only, starter cards only, with no potions or non-combat
decisions, over three development fights (two Louses, a Cultist, a Jaw Worm) and no held-out set
([scenario-expansion.md](first-combat/scenario-expansion.md)). Policies see only public, allowlisted fields,
with the draw pile as an unordered multiset, and their actions are validated against a legal
candidate list. Measured decision counts are about 21 per fight for the heuristic (168 over 8
Louse fights) and about 28 for the language policy (336 over 12 catalog fights). The hardware is
one RTX 3060 12 GB, with WSL limited to 7.7 GiB of RAM, and the owner is now open to paid APIs
and paid remote training. A coding agent (Claude Code) builds the project under declared
experiment contracts, with commit-before-run, independent trace audits and hard budgets.

| Policy (development catalog, 12 attempts each) | Wins | Macro HP |
|---|---:|---:|
| Public heuristic | 12/12 | 76.00 |
| Random | 10/12 | 42.00 |
| PPO, 12.5k-parameter set encoder, 64 training fights on Louses (policy still near-uniform) | 9/12 | 35.67 |
| Unchanged Qwen3-0.6B (invalid outputs) | 0/12 | — |
| Qwen3-0.6B LoRA SFT, rank 8, attention-only, 21 heuristic prompts (best) | 12/12 | 76.33 |
| Heuristic-relabel SFT | 12/12 | 63.67 |
| Relabel SFT plus one REINFORCE update (group-mean baseline, T=1, 12 combats/iteration) | 12/12 | 66.67 |

The owner has paused PPO, and the language track is the current focus
([language-rl-experiment.md](first-combat/language-rl-experiment.md)).

## Engine speed: where the time goes, and how much can be recovered

Almost none of the 30–60 s per fight is game logic. The saved traces split it between animation
timers the engine plays out in real time and restarting the JVM for every fight. Both can be cut
on the real engine, by roughly 10–40× together (estimate), and a parity-checked reimplementation
removes them entirely. A JAX port is the one rebuild option the evidence does not support.

**Where the time goes.** The table below is computed here from the project's saved traces
(`trace.jsonl` timestamps; every action is paired with the next engine message). The runner adds
no sleeps of its own: it waits for CommunicationMod's next stable state.

| Phase (mean per fight) | Heuristic, 8 Louse fights | Qwen LoRA, 12 catalog fights |
|---|---:|---:|
| JVM start, ModTheSpire patching, asset load, to main menu | 9.9 s (26%) | 9.9 s (21%) |
| Seeded `START`, Neow, map choice, one settling `WAIT 60` | 4.4 s (12%) | 4.9 s (10%) |
| Card plays | 8.3 s (16.0 plays × 0.52 s) | 8.3 s (18.3 × 0.45 s) |
| End turns, including the enemy turn | 15.1 s (5.0 × 3.03 s) | 14.8 s (5.3 × 2.78 s) |
| Policy inference | 0.02 s | 8.7 s (19%) |
| After the engine outcome | 0.5 s | 0.5 s |
| **Total** | **38.3 s** | **46.5 s** |

The mechanism explains these numbers. CommunicationMod reports a combat state only when the
action queue is empty and it is the player's turn; it waits for actions, not for visual effects
([GameStateListener.java](https://github.com/ForgottenArbiter/CommunicationMod/blob/master/src/main/java/communicationmod/GameStateListener.java)).
The engine advances one update per rendered frame (60 FPS with vsync in the owner's
configuration), runs at most one action per frame, and each action counts down its timer in real
elapsed time. The game's Fast Mode, already on, shortens those timers but does not remove them:
waits are capped at 0.1 s, the intent flash takes 0.5 s per monster, each card draw 0.1 s, and the
monster start-of-turn and gain-block actions 0.25 s each. Those timers add up to about 2.75 s for a
two-Louse enemy turn, against 3.03 s measured. (These engine facts come from a local decompile of
the pinned game jar for research; nothing decompiled is committed.) Inside combat, then, the time
is animation and timers. Per fight, though, about 37% is restart and
prefix, which removing animations does not touch: with a fresh JVM per fight, even a zero-time
combat caps the gain at about 2.6× (derived). The rules themselves are cheap: sts_lightspeed's
original benchmark ran about 12,500 random Act 1 attempts per second per thread (2021).

**Speeding up the real engine.** Every lever below runs the original Java game code, though some
patch it. Speedups
are per instance, relative to today's ~94 fights an hour, and are estimates unless noted.

| Lever | What changes | Speedup (estimate) | Risks and costs |
|---|---|---|---|
| JVM reuse | Start new seeded runs from the main menu, restarting the JVM every N fights; spirecomm already loops `START` in one JVM | ~1.2–1.3× alone, but required for everything below | State carried across runs; keep the combat-start hash gate. Abandoned runs add deaths to profile stats |
| Display settings | Uncapped frame rate, vsync off | ~1.1× | Low |
| [SuperFastMode](https://github.com/Skrelpoid/SuperFastMode) | MIT, declares the 12-18-2022 build, last commit 2023-01-14, 188k Workshop subscribers; multiplies each frame's time step, up to 10× | ~4–5× with JVM reuse | Still one frame per action; fades stay real-time. Users report gameplay bugs (Dual Wield copies, effects not applying at high speed, a missing hand in the Hexaghost fight; [issue #38](https://github.com/Skrelpoid/SuperFastMode/issues/38)) |
| A small project-owned fixed-step mod | Feed the game a constant 1/60 s per update, skip drawing, uncap the loop; keep the original action loop and CommunicationMod's stability rules | ≥10× with JVM reuse; the upper bound depends on the unmeasured cost of an update without drawing | New mod code, but the most faithful fast option |
| Parallel instances | Steam is not required and the game code has no single-instance lock. Each instance needs its own copy of the game directory, its own `LOCALAPPDATA`, its own relay port and windowed mode; destire-mio ran 4, then 8 instances with a 384 MB heap ([runbook](https://github.com/destire-mio/sts-ironclad-agent/blob/main/live_original/README.md)) | ~3–4× aggregate on this 6-core, 16 GB host | Requires the owner to relax the one-controller rule; per-instance ownership locks |
| Savestate stack ([LudicrousSpeed](https://github.com/boardengineer/LudicrousSpeed), [STSStateSaver](https://github.com/boardengineer/STSStateSaver), BattleAiMod) | Replaces the action loop with about 130 patches; resets to saved mid-combat states | Little beyond the levers above for first-floor fights | No licence; built for the 11-30-2020 game; Save State Mod changes the potion pool (a user reported different potion drops for the same seed, 2025-11-11). Keep out of scored evaluation |
| Headless game classes | Run the game's own classes under OpenJDK with graphics mocked, with no window and no CommunicationMod. [rusted-spire](https://github.com/lhy-loveworld/rusted-spire) does this as a combat oracle for this exact build | Unpublished; potentially the fastest real-logic option | A new harness. Use only the locally installed, licensed jar; never redistribute game classes |

Combined, JVM reuse, a fixed-step mod and 3–4 instances would take today's ~94 fights an hour to
roughly 1,000–3,800, or about 22,000–90,000 fights a day (estimate). The per-lever factors do not
simply multiply, because instances compete for the same 6 CPU cores and 16 GB of RAM. Each change needs a
differential replay gate: the same seed and commands on the stock and modded engines must produce
identical public observations, with mod hashes and display settings recorded as part of the
engine's identity. The reference is the project's pinned modded stack, not the vanilla game,
since BaseMod already changes how one end-of-turn shuffle is seeded
([sts-ironclad-agent](https://github.com/destire-mio/sts-ironclad-agent)). Once combat time
collapses, the policy becomes the bottleneck on the language track: the Qwen LoRA spends 8.7 s per
fight (about 0.3 s per decision), so batching decisions across parallel games becomes the next
lever.

**Rebuilding the game.** Several fast StS1 engines already exist. None has a published parity rate
against the real game.

| Engine | Language, licence | Coverage | Reported speed | Parity evidence |
|---|---|---|---|---|
| [sts_lightspeed](https://github.com/gamerpuppy/sts_lightspeed) | C++, MIT; ~34k lines; upstream last commit 2024-08-10 | All Ironclad and colorless cards (121 card cases), all enemies and relics; bit-exact port of the game's xorshift128+ RNG | 1M random Act 1 playouts in 5 s on 16 threads (2021; the benchmark code has since been deleted) | None published; 40 fix PRs filed in September 2026. Python bindings are run-level, and forks add combat bindings |
| daniel-ziegler fork ("Silver Automaton") | C++ | 692 commits ahead of upstream, with a live real-game bridge and divergence catalogues | ~83% Heart kills at A0 in its simulator (self-reported) | Merges combat RNG into one stream, so seeded replay against the real game is impossible |
| [SpeedTheSpire](https://github.com/degraffa/SpeedTheSpire) (degraffa, 2026) | C++20, no licence | Full-game rewrite in progress | 60,323 random one-monster combats per second per core on a 5800X3D under WSL ([report](https://github.com/degraffa/SpeedTheSpire/blob/HEAD/docs/verification/s245-throughput.md)) | Has a CommunicationMod differential harness; no published rate |
| [mini-spire](https://github.com/rob-pitkin/mini-spire) | C++ | All Ironclad cards, Act 1 enemies | 438k engine steps/s; ~4.3k inside SB3 PPO | Built from the wiki, not checked against the game |
| [rusted-spire](https://github.com/lhy-loveworld/rusted-spire) | Rust + PyO3, no licence | Ironclad combat subset (29 card IDs, 21 enemies) | Unpublished | Matches 530 decision-boundary snapshots from this project's exact build ([COMBAT_TRACES.md](https://github.com/lhy-loveworld/rusted-spire/blob/HEAD/docs/COMBAT_TRACES.md)) |

A JAX port is the wrong tool for this game. JAX pays off when the whole loop (environment, small
policy and search) stays on the GPU: Craftax runs 267k–406k steps per second during PPO on an RTX
4090 ([Matthews et al.](https://arxiv.org/abs/2402.16801v1)), and the Generals.io result in section 1
rests on a JAX simulator. Slay the Spire is a rule-heavy event system, and that is where JAX
struggles. Under `vmap`, every branch of a `lax.cond` or `lax.switch` runs for every game
([JAX docs](https://docs.jax.dev/en/latest/_autosummary/jax.lax.cond.html)), so a per-card switch
costs the sum of all card effects on every step. Compile time grows super-linearly with the number
of switch options ([JAX issue #4453](https://github.com/jax-ml/jax/issues/4453)), Pgx dropped full mahjong over compile cost
([Pgx](https://arxiv.org/abs/2303.17503)), and a full-fidelity JAX NetHack found that "a single
GPU roughly matches *one* CPU core" ([NetHax benchmark](https://github.com/rsiegemit/NetHax/blob/main/docs/benchmark.md)).
The game's RNG needs 64-bit integers, which JAX disables by default, and JAX GPU support on WSL2
is listed as experimental ([JAX installation](https://docs.jax.dev/en/latest/installation.html)).
No Slay the Spire or deckbuilder exists in JAX; the closest, an unfinished Balatro engine, runs at
about 191k steps per second on CPU only ([balatro-rl](https://github.com/Michael-OvO/balatro-rl)).

| Route | Effort for this project's slice (estimate) | Effort for all of Act 1, Ironclad (estimate) | Speed over the real engine (estimate) |
|---|---|---|---|
| Faster real engine (levers above) | Days to weeks | Already covers everything | ~10–40× |
| Wrap sts_lightspeed with a PyTorch policy in the loop | 3–7 days, including a parity replay on existing traces | Already implemented; the cost is fixing divergences | ~10^2.5–10^4.5× end to end; >10^5× engine only |
| Batched C/C++ slice environment (PufferLib or EnvPool style) with GPU PPO | 1–2 weeks to bit-exact RNG | 3–6 months | ~10^5.5–10^6.5× |
| JAX slice environment with PureJaxRL PPO on the RTX 3060 | 2–4 weeks | 4–9 months, with branch-cost risk | ~10^5.5–10^6×, only 1–5× better than a good C++ batch environment |
| Full JAX port | — | Not recommended | — |

The first floor makes parity cheap to check: sts_lightspeed reseeds the combat RNG streams from
`seed + floor`, so a floor-1 fight should depend only on the seed, the encounter, the deck and the
actions (an inference from its code, still to be verified). The project's traces already record
the seed, ordered piles, monster move IDs, intents, powers and HP, enough to replay each fight and
diff the state after every action. For the language track, a simulator's main value is not raw
speed but many parallel, resettable games, because LLM inference stays at about 0.3 s per
decision unless batched across games.

## 1. Pure RL and search: the strongest bots, built on a simulator this project lacks

**How it works.** A neural policy, usually paired with a value function, learns from
environment reward, with or without search at decision time. Model-free methods such as PPO
learn directly from returns. AlphaZero-style methods run Monte Carlo tree search (MCTS) guided by
the network and train the network toward the search's improved policy; MuZero learns its own
dynamics model and searches inside it; Stochastic MuZero adds afterstates and chance codes for
random transitions ([Antonoglou et al., ICLR 2022](https://iclr.cc/virtual/2022/poster/6832));
and Gumbel search makes policy improvement work with tens of simulations rather than 800
([Danihelka et al., ICLR 2022](https://iclr.cc/virtual/2022/spotlight/6419);
[DeepMind mctx](https://github.com/google-deepmind/mctx)). Hidden information is handled by
determinization (sample the unknown state, search, average) or by information-set MCTS, which
avoids "strategy fusion" ([Cowling, Powley & Whitehouse 2012](https://eprints.whiterose.ac.uk/75048)).
Slay the Spire is a single-player stochastic game against "nature": the draw order, enemy move
rolls and reward RNG are chance, not an opponent's private information, so two-player
equilibrium machinery such as ReBeL adds cost without benefit
([Brown et al. 2020](https://arxiv.org/abs/2007.13544)).

**Frontier, 2025–2026.** The headline trend is that **superhuman play in hard
imperfect-information games no longer needs industrial compute**. AlphaZero used 5,000 TPUs for
self-play and 44 million chess games in 2017 ([Silver et al.](https://arxiv.org/abs/1712.01815)).
Ataraxos reached superhuman Stratego (v1 November 2025, v2 October 2026) with 16 H100s for a week
plus 4 H100s for four days, "less than $8,000 at 2025 prices", 163M games, and a 15–1–4 record
against the most decorated human player ([Sokota et al.](https://arxiv.org/html/2511.07312v2)).
Generals.io (June 2026) trained on 4×H200 for four days with a JAX simulator about 10,000× faster
than its predecessor and reached #1 on a ladder of more than 5,000 humans
([arXiv 2606.23348](https://arxiv.org/abs/2606.23348)). Across more than 7,000 runs, generic
policy gradient matched specialized imperfect-information methods (2025;
[arXiv 2502.08938](https://arxiv.org/abs/2502.08938)), so the algorithm is not the bottleneck.
Search on top of learned nets still adds a lot: in Legends of Code and Magic, belief-sampled
search beat the champion ByteRL 51.35% of the time over 10,000 games, against 26.8% without
search (September 2026; [arXiv 2609.06816](https://arxiv.org/abs/2609.06816)). Simulator speed is
the strongest lever of all: PufferLib 3.0 reaches up to 4M steps per second on one RTX 5090
([PufferLib 3.0](https://puffer.ai/blog/3.0/)), and Craftax runs PPO for 1B interactions in under
an hour on one GPU ([Matthews et al.](https://arxiv.org/abs/2402.16801v1)).

Two cautions apply. In NetHack, the closest roguelike, hand-coded symbolic bots still beat
neural agents on median score, by about 3× in the 2021 challenge report
([NetHack Challenge report](https://nethackchallenge.com/report.html)) or more than 4× in a 2023
paper ([NetHack is Hard to Hack](https://arxiv.org/pdf/2305.19240)); the notes could not
reconcile the two figures. And world models are expensive: Dreamer 4 obtained Minecraft
diamonds purely from offline data, but in 0.7% of episodes and with a 2B-parameter model trained
on 256–1,024 TPU-v5p (September 2025; [Dreamer 4](https://arxiv.org/abs/2509.24527)). Slay the
Spire's rules are exact and seed-deterministic, and an RNG-accurate reimplementation exists, so
a learned model would introduce error exactly where it matters (damage, block and lethal
checks). A learned model earns its place only as a fast value function inside search.

**Slay the Spire prior work.** The serious work lives in GitHub READMEs, not papers, and almost
none of it has been reproduced independently. The information-access column matters as much as
the score.

| Bot (activity) | Method | Reported result | Information access |
|---|---|---|---|
| heart1, as reported by typed-decision-slay-the-spire (Oct 2026) | Policy net out of combat; simulator battle search in combat | 165/200 wins (82.5%), A0 Ironclad, in the simulator | Samples undrawn cards and other random outcomes |
| sts-ironclad-agent (Sep–Oct 2026) | Distilled net out of combat; simulator search | 50.1% A20 Heart over 501 original-game runs (95% CI 45.7–54.5), self-reported; 34 were bridge-faulted reruns and the parity checker is "INCOMPLETE" | Not stated |
| Jialeiv/sts-rl-agent (Jul–Sep 2026) | ~100k-parameter REINFORCE MLP out of combat; MCTS combat | Mean floor 42.5 and 14% wins at MCTS@50,000, vs 31.2 and 6% for stock heuristics, over 50 A0 seeds | MCTS teacher uses the true future draw order |
| conquer-the-spire fork (Sep 2026) | PPO "climber" plus turn search in its own C++ engine | 74.5% to the Act 3 cap with search; 25.5% for the policy alone | Search copies the run's RNG ("sees upcoming cards") |
| spire-agent (Sep 2026) | LLM routes and card rewards; MCTS combat | "Multiple" A20 Heart wins without a denominator; a 12-run sample averaged floor 38.6 | Disputed (see below) |
| bottled_ai (stats Oct 2024) | Rules plus combat graph search, no ML | Ironclad 20% over 50 runs (95% CI ~8.9–31.1%); ascension not stated | "No access to secret information" |
| STS2FableBot (StS2, from Jun 2026) | Depth-first search of the current turn on the visible board | 20.7% at A0 over 343 runs (95% CI 16–25%) | No peeking at undrawn cards or RNG |
| zhiyue/sts2-rl-agent (StS2, May 2026) | MaskablePPO in a Python simulator at ~1,200 combats/s | ~92% Act 1 Ironclad combat wins | Its own simulator |

Sources: [typed-decision-slay-the-spire](https://github.com/MindrLabs/typed-decision-slay-the-spire),
[sts-ironclad-agent](https://github.com/destire-mio/sts-ironclad-agent),
[Jialeiv/sts-rl-agent](https://github.com/Jialeiv/sts-rl-agent),
[conquer-the-spire fork](https://github.com/yuchinchenTW/conquer-the-spire),
[spire-agent](https://github.com/AttemorySystem/spire-agent),
[bottled_ai win rates](https://github.com/xaved88/bottled_ai/blob/main/docs/winrates.md),
[STS2FableBot](https://github.com/cicero225/STS2FableBot),
[zhiyue/sts2-rl-agent](https://github.com/zhiyue/sts2-rl-agent).

The notes disagree about spire-agent: one reads its README as giving MCTS the "complete combat
state" with `threads` controlling "RNG-world coverage", which suggests sampled worlds, while the
other found it undocumented whether the search sees the true draw order. Its wins should not be
treated as an honest-information baseline until that is settled. The most instructive StS
result is negative: Jialeiv made **six attempts to distill MCTS combat into a feed-forward
network, and all failed**, with students reaching floors of about 8–14 against the teacher's 23
and imitation accuracy capped near 0.44. The author attributes the cap to a teacher that
"effectively sees the future" draw order and concludes that combat seems "to need a full
AlphaZero-style self-play loop, which nobody has published for this game yet"
([Jialeiv/sts-rl-agent](https://github.com/Jialeiv/sts-rl-agent)).

Most of this work runs on [sts_lightspeed](https://github.com/gamerpuppy/sts_lightspeed), an
MIT-licensed C++ engine that implements all enemies and relics but only Ironclad and colorless
cards, claims "1M random playouts in 5s with 16 threads" (a playout being one random Act 1
attempt; see the engine-speed section), and describes itself as "Designed to
be 100% RNG accurate*" with the asterisk never explained. Upstream has been dormant since
2024-08-10, forks are active in 2026 (daniel-ziegler, Attemory, Jialeiv's patches), and no
published parity rate against the real engine exists. At single-fight scale there is a clean
reference point: mini-spire, a C++ Ironclad-versus-Jaw-Worm fight in which random play wins about
52%, trained a 15k-parameter maskable PPO to about 90% wins within about 50k steps and ran 1M
steps in about four minutes ([mini-spire, June 2026](https://rhp.bearblog.dev/mini-spire/)).

**What it would take here.** On the real engine, pure RL is limited to single fights. The
budget-64 PPO run consumed 827 transitions ([state.md](state.md)), about 60× fewer than
mini-spire's ~50k steps, on a fight (the Louses) that gives no win/loss signal because random
play wins it. Mini-spire's budget is reachable for one fight: at the measured 21–28 decisions per
fight, 50k steps is about 1,800–2,400 combats, or roughly 15–40 hours of continuous engine time
(computed here from the measured figures; one research note calls even this budget out of reach),
and roughly 0.4–4 hours if the real-engine speedups in the engine-speed section hold (estimate).
Full-game RL is a different matter. The learned non-combat layer that gained 11 floors needed 15k
simulated games ([Jialeiv model card](https://huggingface.co/Jialeiv/sts-rl-agent)); at about 27
combats per run (estimate) that is roughly 400k combats: about 140–290 days on today's engine and
still about 4–18 days at 22,000–90,000 accelerated fights a day (estimates), for one training run.

Full-game RL therefore runs through a simulator, in a fixed order. The first job is a Python
binding to sts_lightspeed. For parity work, pin upstream (commit `7476a81`) plus its RNG-relevant
fix PRs rather than the daniel-ziegler fork, whose merged combat RNG stream rules out seeded
replay; upstream's pybind11 bindings are run-level and undocumented, and forks (Jialeiv's patches
among them) add combat-level stepping and legal-action listing. The second is **parity before
training**: replay the project's audited CommunicationMod traces (same seed, same actions)
through the simulator, diff the public states, and publish a divergence rate, since the fork's
target version relative to the 12-18-2022 build is undocumented. The third is the information
boundary: the simulator state holds RNG and the ordered draw pile, so the policy must receive the
same `Decision` projection it gets today, and any search must determinize over the unordered
draw-pile multiset. The fourth is reward: HP retained, or a learned value of the post-combat
state in the style of Suphx's global reward prediction
([Li et al. 2020](https://arxiv.org/abs/2003.13590)), trained on encounters where random play
loses (the Cultist and Jaw Worm fights show variance; the Louses do not). Training would then
start with behavior cloning from the audited heuristic, continue with masked PPO over set or
attention encoders for cards and monsters with a pointer head for targets, and optionally add
Gumbel search over determinized draws at test time, with the real engine kept as final judge
through the existing catalogs and offline re-audit. Scaling from the cited data points, the notes
estimate targets of 10^4+ combat steps per second, 10^6–10^8 decisions for combat PPO and
10^4–10^5 runs for run-level policies. The RTX 3060 and 7.7 GiB of RAM are enough for a
sub-1M-parameter policy and a CPU-threaded C++ simulator, so cash cost is about zero; elapsed
time is dominated by binding and parity engineering, which no note estimates.

**Risks.** Fidelity comes first: the asterisk is unexplained, destire-mio's parity checker is
incomplete, and Jialeiv's real-game bridge has one-seed evidence. Clairvoyant teachers come
second, because an RNG-reading search produces labels a public-information student cannot learn.
Reward saturation on easy fights already stalled this project's PPO. A JAX port of the game would
give the largest speedup but is judged out of scope for a portfolio project, while a C++ batch
wrapper is not.

**What it would teach and show.** Simulator engineering and parity testing, masked set-based
policies, search under hidden information and reward design: the Ataraxos and Generals.io recipe
at hobby scale. A published sts_lightspeed-versus-real-engine divergence rate would itself be
new, since the notes found none, and they found no peer-reviewed RL or MCTS paper with
real-engine results for the game.

## 2. Local small-LLM fine-tuning: the current track, limited by engine samples rather than GPU

**How it works.** A small open model reads a text rendering of the public state and names one
legal candidate. LoRA SFT on demonstrations makes its outputs valid and sensible; on-policy RL
then adjusts it from outcomes. The GRPO family replaces a learned critic with a group baseline
(sample several rollouts from the same start, subtract the group's mean reward), and its
successors change loss normalization or clipping: DAPO, Dr. GRPO, GSPO, CISPO, SAPO, and 2026's
VESPO, LUSPO and GDPO ([TRL paper index](https://huggingface.co/docs/trl/paper_index)).
Multi-turn variants assign credit per turn or step: MT-GRPO uses per-turn rewards
([MT-GRPO](https://arxiv.org/html/2505.11821v3)), and GiGPO finds identical "anchor states"
across a group's rollouts and compares the actions taken from them
([GiGPO](https://arxiv.org/pdf/2505.10978)). The project's REINFORCE, with a scenario-group mean
baseline and one update per batch, is already GRPO with a single inner step; clipping never
activates in that regime, so a renamed objective changes little. The levers that matter are
variance, credit assignment across a combat's 20–30 decisions, and where the LoRA sits.

**Frontier, 2025–2026.** Thinking Machines' "LoRA Without Regret" (2025-09-29) reports that LoRA
matches full fine-tuning under RL "even with ranks as low as 1", that **attention-only LoRA
"significantly underperforms" MLP-only LoRA** even at matched parameter count, and that the
optimal LoRA learning rate is about 10× the full fine-tuning rate
([Thinking Machines](https://thinkingmachines.ai/blog/lora/)); a community wiki notes these are
the lab's own claims, not independently reproduced, though TRL ships a reproduction guide
([HF discussion](https://huggingface.co/datasets/rl-llm-wiki/knowledge-base/discussions/747)).
GiGPO (NeurIPS 2025) supplies the clearest small-model evidence: on ALFWorld, Qwen2.5-1.5B scored
72.8 with GRPO and 86.1–86.7 with GiGPO, against 48.0 for prompted GPT-4o and 60.3 for
Gemini-2.5-Pro, after 150 iterations on 2×H100 with millisecond-speed environments
([GiGPO HTML](https://arxiv.org/html/2505.10978v2)). Multi-turn RL can collapse, as RAGEN's "Echo
Trap" shows ([RAGEN](https://arxiv.org/html/2504.20073v2)), but it also works in games:
lmgame-Bench's Qwen2.5-7B rose from 9.0 to 49.5 on Tetris
([lmgame-Bench](https://arxiv.org/html/2505.15146v2)). ScaleRL, a study of more than 400,000
GPU-hours, found that most recipe choices change compute efficiency rather than the asymptote
([ScaleRL](https://arxiv.org/pdf/2510.13786)), and heavy reasoning can hurt agents, with more
"overthinking" going with lower SWE-bench scores ([arXiv 2502.08235](https://arxiv.org/pdf/2502.08235)).
Since the project's action output is a 12-token `{"a":N}`, a non-thinking model is the default.
On tooling, TRL v1.15's `GRPOTrainer` has experimental `environment_factory` and `rollout_func`
hooks for multi-turn environments ([TRL GRPO docs](https://huggingface.co/docs/trl/main/en/grpo_trainer)),
and Unsloth lists bf16 LoRA minimums for Qwen3.5 of **3 GB (0.8B), 5 GB (2B), 10 GB (4B) and
22 GB (9B)**, advises against QLoRA for Qwen3.5 ([Unsloth Qwen3.5 guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune)),
and cannot use its vLLM fast path for that family
([Unsloth RL guide](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide)). The
candidate small bases are Qwen3.5 0.8B/2B/4B/9B (Apache-2.0, 2026-03-02;
[Artificial Analysis](https://artificialanalysis.ai/articles/qwen3-5-small-models)), Gemma 4
E2B/E4B (Apache-2.0 since 2026-04-02;
[The Decoder](https://the-decoder.com/googles-gemma-4-is-now-available-with-apache-2-0-licensing-for-the-first-time/))
and Ministral 3 3B/8B (2025-12-02; [Mistral](https://mistral.ai/news/mistral-3)).

**Slay the Spire prior work.** The notes found **no published RL-trained LLM** for Slay the Spire
1 or 2; only SFT results exist. Orak (KRAFTON, June 2025) fine-tuned Llama-3.2-3B on about 11k
GPT-4o and o3-mini samples and raised its normalized score from 0.0 to 10.7 ± 1.2, measured on
unseen scenarios and so not directly comparable to GPT-4o's 23.6 on the main table
([Orak v3](https://arxiv.org/html/2506.03610v3)). typed-decision-slay-the-spire (October 2026)
fine-tuned for one epoch on 39,884 heart1 decisions: a Qwen3.5-9B LoRA went from mean floor 14.1
zero-shot to 19.5 and a 421M ModernBERT model from 10.4 to 17.1, but "No text model won a run";
an exploratory DAgger round reached floors 28.7 and 26.6 on 50 check seeds, and in the real game
the 9B model beat the Act 3 boss once in 8 matches
([typed-decision-slay-the-spire](https://github.com/MindrLabs/typed-decision-slay-the-spire)). The
project's own results are in the table above, and the notes found no published counterpart to
its real-engine LoRA SFT and REINFORCE runs.

**What it would take here.** The local path costs nothing in cash, and six changes have direct
evidence behind them. LoRA should cover the MLP projections as well as the current rank-8
`q/k/v/o_proj` adapter. The base can move to Qwen3.5-2B or 4B, which fit the 12 GB card (4B is
tight once 1.5–2K-token prompts and rollout groups are added) and need main-branch Transformers;
slower HF generation costs little here, since measured inference was 8.3 s of a 46.6 s fight
([state.md](state.md)). Training should use scenarios that carry signal: in the stopped
continuation all four Louse combats ended at 77 HP and contributed no gradient, and
[language-rl-experiment.md](first-combat/language-rl-experiment.md) itself warns that a gain "may be a
memorized line", so a held-out set is required. Turn-level credit is cheap to add, with per-turn
HP lost as reward and GiGPO-style anchor-state grouping, because the catalog restarts fixed seeds
and early states repeat exactly across a group. Adapters should be selected by outcome, not
agreement: the heuristic-relabel adapter raised held-out agreement to 75.2% but cut macro HP from
76.33 to 63.67 ([language-relabel-experiment.md](first-combat/language-relabel-experiment.md)). And with 7.7
GiB of WSL RAM, plain HF generation is safer than colocating vLLM (untested). Engine time is the
budget today: one 12-combat iteration costs about 6–12 minutes, 1,000 combats take 8.3–16.7 hours
(estimate), and GiGPO-scale episode counts would take weeks. The engine-speed levers above would
shrink the engine share, after which the model's own 8.7 s per fight dominates unless decisions
are batched across parallel games.

**Risks.** Three deterministic scenarios invite memorization. Headroom is small: macro HP can
reach at most 80 after Burning Blood, and the best result is 76.33. Small groups risk the Echo
Trap, Qwen3.5-0.8B is prone to thinking loops ([Modal](https://modal.com/library/qwen/qwen3-5-0-8b)),
and any change of base model breaks comparability unless SFT is rerun.

**What it would teach and show.** A modern post-training stack (LoRA placement, the GRPO family,
turn-level credit, relabeling) run under hard compute limits. The notes found no published
wall-clock or sample-count results for LLM RL against an engine that takes tens of seconds per
episode, so carefully audited results here, positive or negative, fill a gap.

## 3. Frontier models with scaffolding: competent players, unproven winners, $0.50–90 per run

**How it works.** A closed frontier model chooses each action through an API. The prompt has a
cacheable static prefix (rules, a card, relic and monster glossary, the output schema) and a
dynamic part (the public state, short run notes and the legal candidates). The scaffold adds
tools such as a damage calculator or a simulator with determinized draws, retrieval of game
knowledge, and lessons or skills distilled from earlier runs.

**Frontier, 2025–2026.** Frontier models have now finished long games, every time with a
substantial harness. Claude Opus 4.7 beat Pokémon Red (reported 2026-05-16) after its developer
had removed supports over time, including a critic agent and visual hints
([LessWrong](https://www.lesswrong.com/posts/sehJYg5Yny9fvpbpt/a-year-late-claude-finally-beats-pokemon)).
Gemini 3 Pro finished Pokémon Crystal at turn 24,178 using 1.88B tokens
([jcz.dev](https://blog.jcz.dev/gemini-3-pro-vs-25-pro-in-pokemon-crystal)). A GPT-6 Astra agent
ascended in NetHack on 2026-09-21, winning one of three runs with a self-built harness and
unrestricted wiki and source access, for a $200/month Codex plan plus about $300 in credits
([kenforthewin](https://kenforthewin.github.io/blog/posts/llm-nethack-ascension/)). The best
card-game comparison is BalatroBench (data generated 2026-02-03): **Gemini 3 Pro won 9 of 15 at
$11.16 per run** and 34.3 s per call, GPT-5.2 won 3 of 16 at $4.36, Claude Opus 4.5 won 2 of 15
at $14.86, and every open model scored zero
([BalatroBench data](https://balatrobench-prod.b-cdn.net/benchmarks/models/v1.0.8/default/leaderboard.json)).
Harnesses matter: in lmgame-Bench, 40% of unharnessed runs failed to beat random, while 86.7%
beat it with perception, memory and reflection modules
([lmgame-Bench](https://arxiv.org/html/2505.15146v2)).

The scaffolding lessons are consistent across these efforts. Text state works as well as
pixels; Gemini played Pokémon "roughly as well" from RAM-extracted text
([dbreunig.com](https://www.dbreunig.com/2025/06/17/an-agentic-case-study-playing-pokémon-with-gemini.html)).
Bounded per-call context beats an accumulating transcript: Gemini degraded once context grew well
past 100k tokens and suffered "context poisoning" from a hallucinated goal, while AgenticSTS kept
each strategic call near 5k tokens as competing harnesses grew from about 9k to 500k, using
66–90× fewer tokens per score point, though without a matched ablation
([AgenticSTS](https://arxiv.org/html/2607.02255v1)). Human-taught lessons beat self-reflection in
one StS1 playbook study, mean floor 27.33 against 18.73
([AlasamAkkit/spirecomm](https://github.com/AlasamAkkit/spirecomm)). And letting the LLM propose
while search evaluates gives the strongest tactical play: PokéChamp with GPT-4o won 76% against
the best prior LLM bot ([PokéChamp](https://arxiv.org/abs/2503.04094)).

**Slay the Spire prior work.** Orak (KRAFTON, June 2025; ICLR 2026) is the main StS1 benchmark,
and its setup is close to this project's: a modified CommunicationMod, Ironclad, no ascension, an
LLM choosing card plays, end turn and card rewards while rules handle the map, events and
potions, and a 200-step cap ([Orak](https://arxiv.org/html/2506.03610v1);
[leaderboard](https://krafton-ai.github.io/orak-leaderboard/)). Its normalized score (floors
cleared plus 50/3 per boss) put **Gemini-2.5-pro at 51.9 ± 31.9**, beating the second boss in two
of three runs, against a novice human's 52.9 ± 23.2; GPT-5 scored 26.2, GPT-4o 23.6,
Claude-3.7-sonnet 15.0, Qwen-2.5-7B 5.0, and Llama-3.2 1B/3B, Qwen-2.5-3B and Minitron 4B/8B 0.0.
The notes disagree on Orak's GPT-4o agent ablation: two notes citing the HTML versions report
zero-shot 24.7, reflection 41.3, planning 35.3 and both 36.0, while a third citing the PDF's
Table 39 reports 12.3 ± 4.6, 26.2 ± 19.4 and 23.2; both readings agree that reflection helps
most. Xiao and Yang (2024) found GPT-3.5 and GPT-4 won under 5% of boss fights with an
average deck through the real CommunicationMod ([arXiv 2410.02829](https://arxiv.org/abs/2410.02829)),
and a playbook study won 0 of 15 runs per condition at A0. On Slay the Spire 2, SpireBench
recorded **0 wins in 25 A0 runs** across gpt-5.5, claude-opus-4.7, deepseek-v4-pro,
gemini-3.1-pro-preview and glm-5.1 between 2026-04-27 and 2026-05-05; the best run died on floor
50, and gpt-5.5 averaged about 134M tokens per run
([ClaudePlaysTheSpire](https://github.com/hiKareeem/ClaudePlaysTheSpire/blob/main/docs/benchmark/trial-v0-summary.md)). AgenticSTS
(2026-07-02) won 3 of 10 with Gemini 3.1 Pro and 6 of 10 with a triggered-skill layer (Fisher
p≈0.37, which the authors call directional), while Qwen 3.6 27B and DeepSeek V4 Pro each went
0 of 5; a run took a median of about 80 minutes with 67 strategic calls plus about 500 fast-tier
or mechanical decisions ([AgenticSTS](https://arxiv.org/abs/2607.02255)). Humans win 16% of StS2
A0 runs (Mega Crit, May 2026, via
[GameGeeker](https://gamegeeker.com/fr/news/slay-the-spire-2-may-neows-news-update?market=FR)). No
public, honest-information frontier win rate exists for full StS1 runs. An StS1 benchmark at
Ascension 20, published after this snapshot, is summarized in the addendum.

**What it would take here.** Two scales need separating. On the current combat catalog, a
frontier policy needs only an adapter that returns a candidate index under the existing
`Decision` boundary. The notes estimate about $0.047 per call for Claude Opus 5.5 at 10k input
tokens (6k cached) and 1.5k output tokens, so a 12-fight catalog of about 336 decisions would
cost roughly **$16 on Opus 5.5, $8 on Sonnet 5.5 and under $1 on Haiku 5.5** (computed here from
the notes' per-call figures; probably high, because the floor-1 prompt is far smaller than 10k
tokens and the local Qwen prompt was 715). Latency matters more: at BalatroBench's measured 17–48 s
per call for reasoning models, 28 calls add roughly 8–22 minutes to each fight, so the language
evaluator's 1,800-second cap for 12 slots would need a newly declared budget. That pilot would
show whether a frontier model beats the heuristic's macro HP of 76.00 and whether it can serve as
a teacher (section 5).

Full runs need a controller for the map, events, shops, rewards and potions, all out of scope
today. The notes estimate **about 750 decisions per Act 1–3 run** (range 550–1,400; never
measured on full StS1 runs). Selected per-run cost estimates, uncached → cached:

| Model (list $/MTok in/out) | 300 output tokens per call | 1.5k output tokens per call | Hybrid: ~300 strategic calls, 12k in, 1.5k out |
|---|---|---|---|
| Claude Opus 5.5 ($4/$20) | $34.50 → $18.26 | $52.50 → $36.26 | $23.40 → $17.42 |
| GPT-6 Astra ($10/$50) | $86.25 → $47.37 | $131.25 → $92.37 | $58.50 → $43.92 |
| Gemini 3.1 Pro Preview ($2/$12) | $17.70 → $9.92 | $28.50 → $20.72 | $12.60 → $9.68 |
| Claude Sonnet 5.5 ($2/$10) | $17.25 → $9.13 | $26.25 → $18.13 | $11.70 → $8.71 |
| DeepSeek V4 Pro, peak ($1.32/$3.96) | $10.79 → $5.28 | $14.36 → $8.84 | $6.53 → $4.47 |
| Claude Haiku 5.5 ($0.10/$0.50) | $0.86 → $0.48 | $1.31 → $0.93 | $0.58 → $0.44 |

The prices come from the [Claude](https://platform.claude.com/docs/en/about-claude/pricing),
[OpenAI](https://developers.openai.com/api/docs/pricing),
[Gemini](https://ai.google.dev/gemini-api/docs/pricing) and
[DeepSeek](https://api-docs.deepseek.com/quick_start/pricing) pricing pages. Claude 4.7 and later
models use a tokenizer that produces about 30% more tokens for the same text, Gemini prices rise
on 2027-01-01, and batch discounts cannot apply to live sequential play. As a cross-check,
BalatroBench's measured per-call costs scaled to 750 calls give about $10–110 per run for
2025-era models. A 100-run evaluation (1.5k-output scenario, cached) is estimated at about $93 on
Haiku 5.5, $1,800 on Sonnet 5.5, $3,600 on Opus 5.5 and $9,200 on GPT-6 Astra. Wall-clock time
is the harder limit, at an estimated 3.5–10 hours per run for reasoning models, or 2–6 runs a day
on one controller. Statistics are unforgiving at these sample sizes: 3 wins in 10 has a 95%
confidence interval of 10.8–60.3%, and an honest comparison needs dozens of runs per arm, about
$0.5k–4k per arm (estimate).

**Risks.** The win rate is genuinely unknown; extrapolating from StS2 and Balatro gives anywhere
from 0% to about 50%, which the notes call too uncertain to quote without a pilot. Harness and
model effects are confounded in every public comparison. Invalid outputs ranged from under 1% to
about 13% of calls on BalatroBench. Any combat tool must sample the draw pile from the public
multiset rather than read the true order, and the models themselves change every few months.

**What it would teach and show.** Agent-harness design, context management and cost accounting.
The novel contribution would be the first honest-information StS1 frontier baseline, reported
with dollars per run, seconds per run, invalid-output rate and confidence intervals.

## 4. Remote fine-tuning and RL services: buy model size, not throughput

**How it works.** Hosted training comes in three shapes. Dataset-in services run SFT or DPO on an
uploaded file. Client-side-loop training APIs keep your code in charge of the environment and
call remote GPUs for sampling and gradient steps; Tinker, for example, exposes `forward_backward`,
`optim_step` and `sample` ([Tinker docs](https://tinker-docs.thinkingmachines.ai/)). Raw GPU
rental runs your own trainer (TRL, Unsloth, ART, SkyRL-tx). This project's environment is a
Windows game behind a WSL bridge and cannot move into a vendor's container, so only the second
and third shapes fit. Unsloth is an open-source library for local or rented GPUs, not a hosted
service.

**Landscape on 2026-10-11.** The hosted options narrowed sharply during 2026.

| Service | Fit here | Status and prices (USD) |
|---|---|---|
| Thinking Machines Tinker | Fits (client-side loop) | LoRA only; smallest model Qwen3.5-4B. Per 1M tokens (prefill / sample / train): Qwen3.5-4B 0.33 / 1.005 / 0.737; Qwen3-8B 0.195 / 0.60 / 0.44; Qwen3.5-9B 0.30 / 0.807 / 1.463. Launch lineup retired 2026-06-12; prices rose 2026-07-17. A $150 new-user credit is reported only by a third party and is unconfirmed ([Tinker models](https://tinker-docs.thinkingmachines.ai/tinker/models/); [Beam](https://www.beam.cloud/blog/tinker-model-pricing)) |
| Fireworks Training API | Fits | GA 2026-08-31, serverless LoRA billed per token ([Fireworks blog](https://fireworks.ai/blog/train-past-the-frontier-training-api-now-generally-available)); per-model rates came only from an aggregator and are unverified. The docs call managed RFT deprecated while the GA blog still lists it ([Fireworks docs](https://docs.fireworks.ai/fine-tuning/connect-environments)). Managed LoRA SFT up to 16B: $0.50/M tokens ([Fireworks pricing](https://fireworks.ai/pricing)) |
| W&B / CoreWeave Serverless RL (ART backend) | Fits, but no personal accounts | W&B docs say training is "free during preview"; CoreWeave's page lists RL at $2.70/GPU-hour; the two conflict ([W&B](https://docs.wandb.ai/serverless-rl/usage-limits); [CoreWeave](https://coreweave.com/forge-pricing/post-training)) |
| Together AI | Offline SFT/DPO only | Qwen3.5 up to 9B: SFT $0.34/M tokens, with a second, unlabeled table showing $0.38; an RL API is mentioned only by a third party ([Together pricing](https://www.together.ai/pricing)) |
| OpenAI | Closed to new users | Fine-tuning is being wound down (notice dated 2026-05-08), with job creation ending by January 2027; RFT on o4-mini cost $100/hour ([OpenAI pricing](https://developers.openai.com/api/docs/pricing); [Tessl](https://tessl.io/blog/openai-shutting-fine-tuning-signals-for-enterprise-ai)) |
| Prime Intellect Lab | Does not fit (environment runs on their side) | Shared LoRA training was retired (the CLI warning gives 2026-10-05); on-demand Hosted Training, billed per GPU-hour, replaced it in beta; see the addendum ([Prime Intellect docs](https://docs.primeintellect.ai/hosted-training/what-is-lab)) |
| Anthropic | Not available | No current Claude fine-tuning found; Claude 3 Haiku on Bedrock reached end of life on 2026-09-10 ([AWS](https://aws.amazon.com/jp/blogs/machine-learning/fine-tune-anthropics-claude-3-haiku-in-amazon-bedrock-to-boost-model-accuracy-and-quality/)) |
| Rented GPUs | Fits (the project's trainer runs remotely) | RunPod RTX 4090 $0.34 community / $0.74 secure per hour, A100 80GB $1.19 / $1.59, H100 SXM $2.69 / $3.49, though the rendered page showed higher figures such as $0.89 for the 4090 ([RunPod](https://www.runpod.io/pricing)); Modal H100 ≈ $3.95/h ([Modal](https://modal.com/pricing)); Lambda H100 SXM $4.29/h ([Lambda](https://lambda.ai/pricing)); HF Jobs A100 80GB $2.50/h ([HF Jobs](https://huggingface.co/docs/huggingface_hub/guides/jobs)) |

**Slay the Spire prior work.** The notes found no StS project that reports using a hosted
training service.

**What it would take here.** The notes estimate Tinker costs per 1,000 combats at about **$49 for
Qwen3.5-4B, $29 for Qwen3-8B and $80 for Qwen3.5-9B**, assuming 30 decisions per combat, about
1,500 prompt tokens per decision and every decision trained as its own sequence (the measured
21–28 decisions per fight put this at the upper end). Those 1,000 combats still take 8.3–16.7
hours of engine time, while renting an RTX 4090 for 17 hours costs about $6–15 and an A100 80GB
about $20–42 (estimates). **Compute is cheap next to engine wall-clock**: paying buys model size,
meaning 4B–30B models that do not fit in 12 GB, and does not buy throughput, because the single
game controller remains the bottleneck; throughput comes from the engine-speed levers instead. Moving to Tinker also means changing the base model,
since Qwen3-0.6B is not offered, and rerunning SFT on Qwen3.5-4B. The WSL controller would stay
the client and call the remote sampler for every decision, a round trip the notes did not
measure. Under the project's contracts, remote spend should be declared as a budget alongside
engine time.

**Risks.** Vendor churn dominates. Within 2026 alone, OpenAI closed fine-tuning to new users,
Prime Intellect closed shared LoRA training, Fireworks deprecated managed RFT, and Tinker retired
its launch lineup and raised prices; several prices in the table also conflict between pages.
The mitigation is to write the loop against the Tinker-style API, which open stacks implement too:
SkyRL-tx and VeRL-Tinker can run the same scripts on local GPUs
([SkyRL](https://github.com/NovaSky-AI/SkyRL); [verl](https://github.com/volcengine/verl)).

**What it would teach and show.** Cost-aware infrastructure decisions, and the honest finding that
for a slow real environment money mostly buys model capacity.

## 5. Distillation from frontier models: cheap labels, capped by the teacher

**How it works.** Off-policy SFT trains the student on teacher trajectories. DAgger-style
relabeling has the teacher label states the student itself visits. On-policy distillation (OPD)
scores every token the student samples with the teacher's log-probabilities, using the negative
reverse KL as a per-token advantage and needing no reward model
([TML on-policy distillation](https://thinkingmachines.ai/blog/on-policy-distillation/)). Because
OPD needs teacher log-probabilities on the student's tokens, closed APIs cannot be OPD teachers;
they can only supply labels and traces.

**Frontier, 2025–2026.** Thinking Machines' OPD post (2025-10-27, updated June 2026) reports that
Qwen3-8B-Base reached 70% on AIME'24 in about 150 steps at 9–30× lower cost than extrapolated
SFT, and, citing the Qwen3 report, compares RL reaching 67.6% in 17,920 GPU-hours with OPD
reaching 74.4% in 1,800 ([TML on-policy distillation](https://thinkingmachines.ai/blog/on-policy-distillation/)).
TRL implements OPD (`DistillationTrainer`, `GKDTrainer`) and cross-tokenizer distillation
(`GOLDTrainer`) ([TRL paper index](https://huggingface.co/docs/trl/paper_index)). In an adjacent
game domain, LoRA SFT lifted a small model to 66.2% accuracy on Magic: The Gathering draft picks,
against GPT-4o's 43% zero-shot ([UrzaGPT](https://arxiv.org/abs/2508.08382)).

**Slay the Spire prior work.** Orak's SFT on GPT-4o and o3-mini traces took Llama-3.2-1B from 0
to 8.0 and Llama-3.2-3B from 0 to 10.7, less than half of GPT-4o's own 23.6
([Orak v3](https://arxiv.org/html/2506.03610v3)). typed-decision distilled a search teacher into
language models and reached mean floors of 17.1–19.5 with no wins. sts-ironclad-agent distilled only its
out-of-combat network, and the student matched the teacher at 50.2% against 50.1% in the
simulator (self-reported; [sts-ironclad-agent](https://github.com/destire-mio/sts-ironclad-agent)).
Jialeiv's failures mark the boundary condition: a teacher that sees hidden state produces labels
the student cannot learn.

**What it would take here.** The pipeline already exists (public-state prompts, strict JSON,
candidate identity), and the heuristic-relabel experiment is already the hard-label, DAgger-style
form of OPD ([language-relabel-experiment.md](first-combat/language-relabel-experiment.md)). The teacher must
be measured as a policy first (section 3), because distilling a teacher that scores below the
heuristic's 76.00 on these fights would be a regression by construction. Relabeling saved
`Decision`s through a batch API costs an estimated **$175 per 10,000 decisions with Claude Sonnet
5.5** at 10k input and 1.5k output tokens per call, less with caching, and because the teacher
sees only the public `Decision`, the student stays inside the information boundary. True OPD
needs an open-weight teacher: Thinking Machines' current recipe pairs a Qwen3.5-9B-Base student
with a Qwen3.5-9B teacher on Tinker, and training a 9B LoRA locally needs 22 GB, beyond the 12 GB
card.

Terms of service need attention. Anthropic's Commercial Terms forbid using the services to
"build a competing product or service, including to train competing AI models"
([Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms)), and OpenAI's and
Google's terms contain similar clauses ([OpenAI Terms](https://openai.com/en-GB/policies/row-terms-of-use/);
[Gemini API Terms](https://ai.google.dev/gemini-api/terms)). None explicitly addresses a narrow
game-playing policy, and whether one counts as "competing" is a legal question the notes do not
settle. Open-weight teachers such as MIT-licensed DeepSeek R1 sidestep it
([Simon Willison](https://simonwillison.net/2025/Jan/20/deepseek-r1)), but open models played
worse in the evidence above.

**Risks.** The student inherits the teacher's ceiling and its information access. Agreement with
a teacher is not the same as outcome, as the relabel run showed by raising agreement while
cutting HP. The terms-of-service question is unresolved.

**What it would teach and show.** Data-centric ML: evaluating a teacher, DAgger, and on-policy
distillation, one of the more cost-efficient post-training techniques of 2025–2026.

## 6. Autoresearch and LLM-driven program search: the evaluator is the product

**How it works.** In an autoresearch loop, a coding agent edits a narrow, version-controlled
surface against a fixed evaluator it cannot modify, keeps a change if the score improves, resets
it otherwise, and logs every attempt. Evolutionary program search (FunSearch, AlphaEvolve,
OpenEvolve, ShinkaEvolve) has an LLM mutate a population of programs that an automatic scorer
selects among. Code-as-policy has an LLM write the bot itself, as heuristic, search or value code,
and repair it from execution traces. LLM-written rewards and curricula (Eureka and its successors)
are a fourth variant.

**Frontier, 2025–2026.** Karpathy's autoresearch (March 2026) is the canonical small loop: one
editable file, read-only data and evaluation, a fixed five-minute run (about 12 experiments an
hour), keep the commit if `val_bpb` improves or `git reset` if not, log every run including
crashes to `results.tsv`, and "LOOP FOREVER"
([autoresearch](https://github.com/karpathy/autoresearch);
[program.md](https://raw.githubusercontent.com/karpathy/autoresearch/master/program.md)). It cut
nanochat's time-to-GPT-2 from 2.02 h to 1.80 h and then 1.65 h over two rounds in March 2026
([nanochat README](https://cdn.jsdelivr.net/gh/karpathy/nanochat@master/README.md)); secondary
accounts of the experiment counts conflict (about 700 experiments and 20 improvements, 276 and 29,
or 126 in one night; [philschmid.de](https://www.philschmid.de/autoresearch);
[VentureBeat](https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai)).
The harness study "How Much of a Harness Does a Strong Agent Need for Autonomous ML Engineering?"
(submitted 2026-09-30) found that a minimal single-session coding agent reached a **62.5% medal
rate on an MLE-bench subset against 47.1% for the best of four open-source research harnesses**
at the same backbone and budget, that
adding delegation and parallelism cut its rate on one subset from 55.7% to 33.3%, that search
strategy had no significant effect, that its modelled LLM cost was about $12 per 24-hour run, and
that four MLE-bench tasks leaked test ground truth or were impossible
([arXiv 2609.40303](https://arxiv.org/html/2609.40303)). The notes disagree on that study's
provenance: one is based on the full arXiv HTML, while another found only secondary coverage
([CryptoBriefing](https://cryptobriefing.com/apple-study-minimal-agent-beats-multi-agent/)),
could not locate the arXiv entry, and observes that the coverage names only Apple, so the
study's usual "Apple/EPFL" label rests on an inferred EPFL affiliation. AIRA₂ (FAIR, v2 April 2026) reports 81.5% mean percentile rank on
MLE-bench-30 at 24 hours (v1: 71.8%) and concludes that earlier "overfitting" "was driven by
evaluation noise rather than true data memorization" ([AIRA₂](https://arxiv.org/abs/2603.26499)).

On program evolution, AlphaEvolve (May 2025) recovered about 0.7% of Google's worldwide compute
with a scheduling heuristic and requires automatically verifiable, objective scores
([DeepMind](https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/)).
Its nearest game application evolved CFR and PSRO variants for poker-like games, where the
discovered mechanisms overfit their training games and distilled, simpler versions generalized
better ([arXiv 2602.16928](https://arxiv.org/abs/2602.16928)). ShinkaEvolve reached
state-of-the-art circle packing in 150 samples ([Sakana ShinkaEvolve](https://sakana.ai/shinka-evolve/)),
OpenEvolve estimates $0.01–0.60 per iteration depending on the model
([OpenEvolve](https://github.com/algorithmicsuperintelligence/openevolve)), and Sakana's ALE-Agent
won AtCoder Heuristic Contest 058 for about $1,300 in total ([Sakana AHC058](https://sakana.ai/ahc058/)).
On code-as-policy, Code World Models (ICLR 2026) has an LLM write a game model and value functions
and plans with MCTS or IS-MCTS, matching or beating Gemini 2.5 Pro in 9 of 10 games
([Code World Models](https://arxiv.org/abs/2510.04542)); PromptPO found LLM-written policies
competitive with RL at far fewer interactions when the LLM knows the domain, and weaker on MuJoCo
([PromptPO](https://arxiv.org/abs/2605.30719)); and in the NeurIPS 2025 PokéAgent battling track,
"specialist RL and search methods dominated LLM approaches"
([PokéAgent Challenge](https://arxiv.org/pdf/2603.15563)). Reward hacking is measured, not
hypothetical: across 17 LLMs, unprompted hacking occurred in **30.5% of open-ended
research-pipeline tasks**, and an LLM review panel missed 6.5% of confirmed hacks; the mitigation
is to keep metrics outside the agent's control and recompute them independently (September 2026;
[arXiv 2609.28614](https://arxiv.org/abs/2609.28614)). Agent endurance is no longer the limit:
METR put its best model's 50% time horizon at "likely at least 16 hours" in May 2026
(secondary; [Wikipedia: METR](https://en.wikipedia.org/wiki/METR)).

**Slay the Spire prior work.** The notes found no published account of a coding agent
iteratively improving an StS bot and no LLM-evolved StS evaluation function. The nearest examples
are on Slay the Spire 2: DemoEvolve (May 2026) used demonstration-guided harness evolution to
raise mean floor from 18.17 to 28.83 on held-out seeds ([DemoEvolve](https://arxiv.org/abs/2605.24539)),
and STS2FableBot, an information-honest search bot whose README says its code is mostly written by
Claude, wins 20.7% of A0 runs ([STS2FableBot](https://github.com/cicero225/STS2FableBot)). This
project's heuristic is itself a code policy built by Claude Code, and it is still the best policy.

**What it would take here.** At about 38 s per combat the real engine gives about 95 combats an
hour, so a budget of 8 combats per candidate allows **about 12 candidates an hour and about 100
overnight**. A 150-generation ShinkaEvolve run at 8 combats per generation needs about 1,200
combats, or about 12.6 hours on today's engine and roughly 20–75 minutes if the 10–40×
real-engine speedups hold, while AlphaEvolve-scale searches with thousands of candidates still
need a simulator (all estimates). The project's infrastructure already supplies the
loop's discipline: commit-before-run, live commands that refuse uncommitted `src/` changes,
read-only catalogs, and scores recomputed offline from traces by `evidence.py` and `report.py`.
Three pieces are missing. The loop needs a hidden held-out catalog whose scores the agent never
sees, in the manner of AIRA₂'s hidden consistent evaluation. It needs a low-noise metric, because
win/loss over eight easy fights cannot separate candidates when the heuristic already wins 12 of
12; HP, paired fixed seeds and harder scenarios where the heuristic loses would do. And its
writable surface must be narrow: the heuristic policy module, never `protocol.py`, the evaluator,
the catalogs or the scoring. Population evolution would then move to a simulator with cascade
evaluation, cheap simulator screens followed by a small real-engine confirmation for survivors,
gated on the parity work in section 1.

**Risks.** Evaluation noise mistaken for progress is the main one; best-of-N selection showed the
largest gap between self-selected and oracle scores in the harness study. Reward hacking threatens
anything the agent can write, three scenarios invite overfitting, and long sessions grow costly as
context accumulates, which fresh sessions resuming from the log and git history avoid.

**What it would teach and show.** The 2026 literature rewards a demonstrably sound evaluator and
an honest keep/reject log more than a complex harness. An autoresearch loop on a real game engine
that documents its reward-hacking guards and runs held-out re-audits would be a distinctive
portfolio artifact.

## 7. Multi-agent systems and swarms: breadth helps, depth does not

**How it works.** The idea applies at two levels. Inside the player, several model calls are
combined per decision through majority voting, debate, a mixture of models, a planner/executor
split, a critic, or routing to specialists. As builders, an orchestrator splits development work
across parallel coding agents that coordinate through git and a task board.

**Frontier, 2025–2026.** Inside the player, the evidence points one way: cheap aggregation
captures most of the gains attributed to debate and model mixing, and splitting a sequential
decision process across agents hurts. Majority voting accounts for most of the gains credited to
multi-agent debate (NeurIPS 2025; [Debate or Vote](https://arxiv.org/pdf/2508.17536)), and
sampling the single best model beat mixing different models by 6.6% on AlpacaEval 2.0
([Self-MoA](https://arxiv.org/pdf/2502.00674)). Self-organizing teams underperformed their best
member by up to 41.1% even when told who the expert was
([Multi-Agent Teams Hold Experts Back](https://arxiv.org/html/2602.01011v1)), and across 180
configurations every multi-agent variant degraded a sequential planning benchmark by 39–70%, while
centralized coordination improved a parallelizable one by 80.9%
([Google Research](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)).
The sub-agents that did help were narrow tools a main agent chose to call, such as Gemini's
Pokémon pathfinder and boulder-puzzle solver
([The Decoder](https://the-decoder.com/googles-reasoning-llm-gemini-2-5-pro-beats-pokemon-blue-with-a-little-help/)).

As builders, multi-agent systems win on breadth. Anthropic's orchestrator–worker research system
beat a single agent by 90.2% on an internal eval at about 15× the tokens of chat (June 2025;
[Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). Carlini's C
compiler (February 2026) used 16 parallel Claude Opus 4.6 agents with no orchestrator,
coordinating only through git and lock files, over about 2,000 sessions, 2B input tokens and just
under $20,000, and produced a 100k-line compiler that builds Linux; when all 16 agents got stuck
on the same kernel bug, the fix was a known-good oracle that split the work, and the stated lesson
is that "the verifier must be nearly perfect" ([Anthropic](https://www.anthropic.com/engineering/building-c-compiler)).
Cursor settled on planners, workers and a judge with fresh restarts after flat peer designs
stalled (January 2026; [Cursor](https://cursor.com/blog/scaling-agents)). Claude Code agent teams
are experimental, use about 7× the tokens of a standard session in plan mode, and are not
recommended for sequential work ([Claude Code costs](https://code.claude.com/docs/en/costs);
[agent teams](https://code.claude.com/docs/en/agent-teams)). MAST annotated 1,642 multi-agent
traces, found failure rates of 41–86.7%, and found that adding a verification step was the best
single intervention at +15.6% ([MAST](https://arxiv.org/html/2503.13657v3)). ENPIRE gave each of
eight robot stations its own coding agent; time to mastery fell, but token cost grew with fleet
size and utilization of the physical robots fell ([ENPIRE](https://research.nvidia.com/labs/gear/enpire/)).

**Slay the Spire prior work.** No published StS agent uses a true multi-agent gameplay
architecture. spire-agent's `GameAgent` routes each decision to a Map, Build or Combat sub-agent
that returns one legal decision, which is routing by decision type rather than agents conversing
([spire-agent](https://github.com/AttemorySystem/spire-agent)). AgenticSTS routes across fast,
strategic, analysis and evolution model tiers, yet one note found no multi-agent design described
in the paper ([AgenticSTS](https://arxiv.org/html/2607.02255v1)); the two readings are
compatible, since tiered routing is not a team.

**What it would take here.** Inside the player, a combat is a tightly coupled sequential chain,
exactly where multi-agent designs lose. The supported options, cheapest first, are k-sample
voting over the enumerated candidate actions of one strong model (the action set is small and
discrete, so exact-match votes are feasible), routing by decision type to specialist prompts,
and "smart-friend" escalation to an expensive model only for card rewards, elites, bosses and
shops ([Cognition](https://cognition.com/blog/multi-agents-working)). Debate and heterogeneous
model mixes are not supported by the evidence.

As builders, the engine is the critical path. At 60–120 combats an hour, detecting a 10-point
win-rate difference near 50% needs about 390 combats per arm and a 5-point difference about 1,570
(estimate, standard two-proportion test), so the live engine can judge only a handful of variants
a day, and a swarm generating dozens of variants an hour would be bottlenecked 10–100× by
evaluation. The pattern that fits keeps a single evaluation owner, consistent with the project's
single controller and `RuntimeLock`: a planner keeps a hypothesis board; workers in separate git
worktrees implement variants and run engine-free checks (unit tests, offline replay on saved
traces); a clean-context judge prunes variants before they spend engine time; and one runner
drains a serialized queue, screening catalogs first, which amounts to successive halving under a
fixed engine budget. A 3–5 teammate team costs about 7× a single session, and no dollar figure is
published for a run of this size. Parallel game instances on the real engine (engine-speed
section) would loosen this bottleneck 3–4×, and a fast simulator flips the calculation: one agent
per instance, population-based training and exploiter-style scenario search become real parallel
speedups.

**Risks.** Tokens multiply while engine-hours stay fixed. Sequential tasks degrade, parallel
writers make conflicting choices, and agents optimize whatever the verifier rewards, so a
low-fidelity simulator becomes the target.

**What it would teach and show.** The defensible contribution is an honest ablation: the same
model as a single Claude Code session against a team, on the same engine-hour budget, reporting
tokens, dollars, engine-hours and win-rate deltas with confidence intervals. The harness study
calls that control missing from most harness papers.

## 8. Imitation from human run data: 77 million runs, zero combat actions

**How it works.** Behavior cloning or offline RL learns from recorded human play. For Slay the
Spire the public human data is run-level, not turn-level, so it supports models of card picks,
paths and run value, and human baselines, but not combat imitation.

**Frontier, 2025–2026.** The closest analogue is DraftFM (August 2026), a 1.6M-parameter model
that scores only the cards in the current pack from frozen text-derived card features; trained on
149M human Magic: The Gathering picks, it reached 50.8–60.4% top-1 agreement on fully held-out
sets against about 7% chance ([DraftFM](https://arxiv.org/abs/2608.19568)). In NetHack, imitation
scales smoothly with compute ([Tuyls et al.](https://arxiv.org/abs/2307.09423)), yet billions of
transitions from a symbolic bot did not close the gap to that bot
([NetHack is Hard to Hack](https://arxiv.org/pdf/2305.19240)). Offline RL beats behavior cloning
mainly when rewards are sparse or data is noisy ([Kumar et al. 2022](https://arxiv.org/abs/2204.05618)).

**Slay the Spire data.** The largest source is a metrics dump of **about 75–77 million StS1 runs**
from October 2018 to November 2020, about **380 GB of JSON**, attributed to Mega Crit. The
game-datasets index lists it as
"77 million Slay the Spire Runs from 2018-2020" in a PR merged 2026-09-05 that cites the
r/slaythespire post "77 million runs, an STS metrics dump"
([game-datasets PR #39](https://github.com/leomaurodesenv/game-datasets/pull/39)), and Fox Row's
analysis (2020-12-14) describes it as released by the developers
([Fox Row](https://foxrow.com/slay-the-spire-statistical-analysis)). Its 2020 slice alone held 18M
runs (about 90 GB raw, 77 GB in SQLite), with a 9% overall win rate and the Heart causing 51.12% of
Ironclad deaths. Provenance is not settled: the Reddit announcement could not be fetched, so its
date, terms and the Google Drive folder's current availability are unverified; slaythespire.dev
lists "No stable official link; license not stated" ([slaythespire.dev datasets](https://slaythespire.dev/datasets/));
and a second note found no primary source at all. The record schema was inferred from one
2022-era local `.run` file ([sample run file](https://raw.githubusercontent.com/MaT1g3R/Slay-the-Spire-data/master/runs/200-rotating-sample/DEFECT/1663714310.run)),
not from documentation of the dump: card choices with skipped options, path, relics, events,
campfires, shop and purge actions, HP and gold per floor, final deck and victory, and for each
fight only damage taken and turns, with **no per-turn actions**. Other human data is thin
(Spirelogs is offline; curated sets hold hundreds of runs). Known uses include a 20,000-run
path-entropy study ([Bazzaz and Cooper](https://arxiv.org/abs/2504.03918)), a fight predictor
trained on more than 325,000 fights ([slaythespire.dev projects](https://slaythespire.dev/projects/)),
and spire-agent's card picker built on Baalorlord's run archive
([spire-agent](https://github.com/AttemorySystem/spire-agent)). StS2 telemetry (about 240M runs by
May 2026) is not public ([GameGeeker](https://gamegeeker.com/fr/news/slay-the-spire-2-may-neows-news-update?market=FR)).

**What it would take here.** The current combat scope has nothing to imitate, but the dump offers
two things now and one later. Its `damage_taken` rows for floor-1 fights at A0 Ironclad give a
**human HP-loss baseline per encounter** (Jaw Worm, Cultist, Louses) that the project's policies
could be compared against directly, which no current bot comparison offers. Its encounter
frequencies give a prior for weighting scenarios. Once the scope reaches full runs, it could train
a DraftFM-style card-reward and path model. The cost is about 380 GB of download and storage, with
streaming parsing to stay inside 7.7 GiB of WSL RAM; the data predates the project's 12-18-2022
build, so version differences would need checking.

**Risks.** Unverified provenance and an unstated licence (do not redistribute), no combat actions,
and a schema inferred rather than documented.

**What it would teach and show.** Large-scale data engineering, and an evaluation contribution, a
human reference point, that stays meaningful whichever policy wins.

## 9. Hybrid paths: every strong Slay the Spire bot already is one

The pure paths are most useful as components. The first and best-supported hybrid puts **search
in combat and a learned or LLM layer above it**. Jialeiv's learned non-combat layer on fixed MCTS
combat was worth about 11 floors (31.2 → 42.5) and raised wins from 6% to 14%
([Jialeiv model card](https://huggingface.co/Jialeiv/sts-rl-agent)), and spire-agent delegates to
an LLM "only judgments that still require open-ended tradeoffs"
([spire-agent](https://github.com/AttemorySystem/spire-agent)). Both follow the options framework,
a combat policy invoked by a run-level controller
([Sutton, Precup & Singh 1999](https://www.sciencedirect.com/science/article/pii/S0004370299000521)).
A second hybrid has **the LLM propose and search evaluate**: PokéChamp's LLM-inside-minimax design
won 76% against the best prior LLM bot and 84% against the strongest rule bot
([PokéChamp](https://arxiv.org/abs/2503.04094)), and Code World Models has the LLM write the model
and value function before planning with IS-MCTS. A third has **an LLM coach a non-LLM engine**: a
developer's non-LLM engine beat Pokémon Red in under a week with Claude Opus 5 adjusting its
options from the game log ([Tom's Hardware, 2026-09-27](https://www.tomshardware.com/tech-industry/artificial-intelligence/developer-says-jev-decision-model-beat-pokemon-red-in-under-a-week-non-llm-engine-succeeds-where-traditional-chatbots-stalled-for-months-but-claude-opus-5-coached-the-model-through-its-dead-ends)),
and in a Slay the Spire 2 write-up a local greedy policy made all 35 in-combat actions while the
LLM tuned it from rejection feedback (one combat, explicitly "not an audited benchmark";
[dev.to](https://dev.to/brmarcosbr/i-made-an-agent-play-slay-the-spire-2-on-its-own-and-what-unlocked-it-was-the-game-saying-no-2hc2)).

A fourth uses **an LLM as prior or teacher for fast RL**: LLM action suggestions fed as extra
observations sped BabyAI learning up to 9× ([arXiv 2510.08779](https://arxiv.org/html/2510.08779v1)),
and here the LoRA-tuned Qwen could serve as a behavior-cloning teacher for a simulator-trained
policy rather than being deployed itself. A fifth is **behavior cloning followed by RL**, which
matched or slightly beat the champion in Legends of Code and Magic
([arXiv 2404.16689](https://arxiv.org/abs/2404.16689v1)). The sixth is **privileged training with
honest deployment**: Suphx's Mahjong agents first saw hidden tiles and then had that access
annealed away, and predicted the final game outcome to get dense rewards
([Suphx](https://arxiv.org/abs/2003.13590)). Both ideas map onto Slay the Spire, as annealing away
the true draw order and valuing combat HP by what it is worth later in the run.

A strategic alternative is to change games. Slay the Spire 2 is C#/Godot, and **sts2-cli runs the
real StS2 engine headless**, which removes the simulator-fidelity problem that dominates StS1 work
([sts2-cli](https://github.com/wuhao21/sts2-cli)). Against that, StS2 has been in Early Access
since 2026-03-05, with patches from v0.103 to v0.111 in about six months that break mods and shift
baselines, and it is crowded with LLM-agent projects. StS1 is frozen, which suits reproducible
research, and learned-policy work on its real engine is comparatively empty.

## 10. Recommended sequence for this project

The ordering follows from the constraints above: engine time is scarce but mostly recoverable,
the language track is current, and money is now available but mainly buys model size.

**First, make the evaluator worth optimizing against** (no cash, little engine time). Add
encounters where random play loses and the heuristic does not saturate, declare a held-out
scenario set that no training or selection loop sees, and score on paired seeds with HP-based
metrics and confidence intervals. Everything later depends on this; the 2026 autoresearch
literature attributes most false progress to evaluation noise, and the relabel result already
showed agreement and outcome diverging.

**Second, speed up the real engine behind a parity gate** (days to weeks, $0). Reuse one JVM
across fights, then add a small fixed-step, no-render mod (or evaluate SuperFastMode), and accept
each change only if the same seeds and commands reproduce identical public observations on the
stock and modded engines. Parallel instances add another 3–4× but need the owner to relax the
one-controller rule. This multiplies every later step, and its measured speedup and divergence
report would be a useful result in its own right.

**Third, spend the next language-track runs on the changes with direct evidence** (local, $0):
MLP-inclusive LoRA, a Qwen3.5-2B or 4B base with thinking disabled, turn-level HP rewards with
anchor-state grouping, and training only on scenarios that carry gradient. Report each change
against the frozen 76.33 SFT adapter; the unevaluated two-update REINFORCE adapter is the natural
first evaluation ([state.md](state.md)).

**Fourth, measure a frontier model on the same catalog** (tens of dollars). Run one cheap and one
flagship model as policies under the existing `Decision` boundary, logging dollars and seconds per
fight and invalid outputs. If either beats the heuristic, relabel saved states through a batch API
(about $175 per 10,000 decisions on Sonnet 5.5, estimate) and distill; if neither does, the
heuristic remains the better teacher, which is itself a reportable result.

**Fifth, run an autoresearch loop on the heuristic, gated by the held-out catalog** (overnight).
Edits are confined to the policy module, every candidate is committed before it runs, kept or
reset, and re-audited offline. About 100 candidates fit in a night on today's engine, and an
order of magnitude more on an accelerated one (estimate); no comparable experiment is published
for the game.

**Sixth, decide on the full game, and if the answer is yes, start with simulator parity, not
training.** Bind upstream sts_lightspeed, replay audited traces, publish a divergence rate, and only
then follow the section 1 recipe (behavior cloning from the heuristic, masked PPO, determinized
search) with the real engine as final judge. Non-combat decisions could start with a frontier LLM,
at the hybrid costs in section 3, and later move to a card-pick model trained on human or
simulator runs.

**Seventh, use paid remote training only when model size is the hypothesis**, for example on-policy
distillation from Qwen3.5-9B on Tinker at an estimated $29–80 per 1,000 combats, with the loop
written against the Tinker-style API so it can move between local, rented and hosted GPUs. The
owner's planned version, dated 2026-10-12, is the
[remote open-weight track](open-weight/README.md).

**Eighth, treat a multi-agent builder setup as an experiment, not a default**, and if it is
tried, run and report the single-agent-versus-team ablation on a fixed engine budget.

On the evidence above, this guide would not pursue a full JAX port, world models, equilibrium
solvers, gameplay debate or mixed-model ensembles, RNG-reading teachers, or distillation from a frontier teacher
that has not first been measured as a policy. OpenAI fine-tuning is not an option for a new
account in any case.

## 11. Later directions: interpretability and robotics

These two directions are for after the sequence in section 10, not instead of any of it. Both keep
the project what it is, an AI that plays Slay the Spire, and add a way of studying or improving it.
Three further research notes compiled on 2026-10-11 back this section.

Both build mainly on assets the project already has. Its 288 saved traces hold about 5,000 combat
decision states (counted here; many repeat the same seeded states), each with its public
`Decision`; a decision has a median of 5 legal candidates and at most 11. The Qwen policy
gives an exact probability for every candidate (`candidate_log_probs` in `language_policy.py`), the
PPO network a softmax, and the heuristic a deterministic pick. The state is structured, so single
fields can be edited to make counterfactuals. One base model has a lineage of adapters with measured
behavior (unchanged, Louse SFT, heuristic relabel, one and two REINFORCE updates). And the real
engine can turn a claim about a model's internals into a prediction about wins and HP that it then
confirms or refutes.

### Interpretability: showing how each policy decides

**What the terms mean.** Interpretability asks why a model produces the outputs it does, and it has
two broad branches. *Behavioral* (black-box) interpretability treats the model as a function: edit
the input, watch the output, and fit simple explanations to what changes. It needs only queries, so
it is the only branch that reaches closed API models. *Mechanistic* interpretability opens the model
and reads or edits its internal activations to find which components cause an output. Its main tools
are linear probes (does a layer encode "incoming damage"?), activation patching (copy one internal
value from a counterfactual input and see whether the decision follows), steering vectors (add a
direction to the activations to shift behavior) and sparse dictionaries (SAEs and transcoders, which
split activations into more readable features). It needs the weights, so here it applies to Qwen and
the PPO network, not to Claude, GPT or Gemini.

**Why this project is a good testbed.** Most LLM interpretability work explains free-text answers,
where "the decision" is fuzzy. Here every decision is a choice among a handful of legal candidates,
Qwen gives each an exact probability, and the inputs are game fields with ground-truth values such
as intent damage, block, HP and energy. A metric like "log-probability of the chosen card minus the
runner-up" is therefore precise, probe labels come free from the audited states, and edited states
can be checked for legality. Games have long been interpretability's favorite testbed for the same
reasons. Othello-GPT's board is linearly decodable and editable ([Li et al., ICLR
2023](https://arxiv.org/abs/2210.13382); [Nanda et al. 2023](https://arxiv.org/abs/2309.00941));
adding a "skill vector" to a chess-playing GPT raised its win rate by up to 2.6× ([Karvonen
2024](https://arxiv.org/abs/2403.15498)); a probe on Leela Chess Zero predicts the best move two
turns ahead 92% of the time in single-line positions ([Jenner et al., NeurIPS
2024](https://arxiv.org/abs/2406.00877)); AlphaZero's chess concepts were probed and then taught to
grandmasters ([McGrath et al. 2022](https://arxiv.org/abs/2111.09259); [Schut et al., PNAS
2025](https://arxiv.org/abs/2310.16410)); a model-free Sokoban agent turned out to plan, in
something like bidirectional search ([Bush et al., ICLR 2025](https://arxiv.org/abs/2504.01871));
and subtracting a "cheese vector" made a maze agent mostly ignore its goal ([Turner et al.
2023](https://www.alignmentforum.org/posts/cAC4AXiNC5ig6jQnc/understanding-and-controlling-a-maze-solving-policy-network)).
A 2026 study of Llama, Qwen3 and gpt-oss in strategic games found their internal representations of
the game state "substantially more accurate than their own verbal reports" ([Sobotka et
al.](https://arxiv.org/abs/2605.00226)). The notes found **no interpretability work on Slay the
Spire, on any deck-builder, or on a fine-tuned LLM card-game policy**.

**Where the field stands, late 2026.** The open toolchain is mature, and opinion has turned
pragmatic. Anthropic's attribution graphs, which trace a single output back through readable
features, were open-sourced as `circuit-tracer` with a Neuronpedia front end in May 2025
([Anthropic](https://www.anthropic.com/research/open-source-circuit-tracing)); since v0.4.0
(February 2026) a graph can target the difference between two logits, which is exactly "why
candidate 2 over candidate 3"
([releases](https://github.com/safety-research/circuit-tracer/releases)). Ready-made per-layer
transcoders exist for **Qwen3-0.6B, the project's exact base model** (163,840 features per layer,
about 18.8 GB for all 28 layers;
[mwhanna/qwen3-0.6b-transcoders-lowl0](https://huggingface.co/mwhanna/qwen3-0.6b-transcoders-lowl0)).
The Qwen team's official Qwen-Scope SAEs cover all 24 layers of **Qwen3.5-2B-Base**, the planned
upgrade, and the model card calls applying base-model SAEs to post-trained checkpoints "reasonable"
for most situations ([Qwen-Scope](https://arxiv.org/abs/2605.11887); [model
card](https://huggingface.co/Qwen/SAE-Res-Qwen3.5-2B-Base-W32K-L0_50)); nothing comparable exists
for Qwen3.5-4B. TransformerLens v4 (2026-09-21) supports Qwen3.5
([releases](https://github.com/TransformerLensOrg/TransformerLens/releases)), and the Jacobian lens
(Gurnee et al., July 2026), a principled refinement of the logit lens that shows what each layer
"would predict", ships with Qwen examples ([arXiv 2607.15495](https://arxiv.org/abs/2607.15495);
[jacobian-lens](https://github.com/anthropics/jacobian-lens)). Against that, Google DeepMind
deprioritized fundamental SAE research in March 2025 after dense linear probes beat SAE-based probes
out of distribution ([Alignment Forum](https://www.alignmentforum.org/posts/4uXCAJNuPKtKBsi28/)),
AxBench found that for steering "prompting outperforms all existing methods" ([AxBench, ICML
2025](https://arxiv.org/abs/2501.17148)), and Anthropic reports that attribution graphs give
"satisfying insight" on about a quarter of the prompts it tried ([Biology of a
LLM](https://transformer-circuits.pub/2025/attribution-graphs/biology.html)). The working consensus
is to treat SAE and transcoder features as hypothesis generators and to rest claims on probes with
controls, patching, and steering compared against a prompting baseline.

**What closed APIs allow.** As of October 2026 none of Anthropic, OpenAI or Google returns raw chain
of thought. Each returns at most a summary, and Anthropic's summaries are written "by a different
model from the one you target" ([Claude thinking
docs](https://platform.claude.com/docs/en/build-with-claude/thinking)). Token log-probabilities are
nearly gone: Anthropic's OpenAI-compatibility layer ignores them ([compatibility
docs](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk)), a reply on
Google's developer forum (2026-08-05) says they "are no longer returned for 3.X models"
([forum](https://discuss.ai.google.dev/t/missing-logprobs-support-in-the-newest-gemini-models-3-1-pro-3-6-flash-on-vertex-ai-and-ai-studio/176557)),
and OpenAI returns them only at reasoning effort `none`, which GPT-6 Sol and Luna accept and GPT-6
Astra does not ([Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model)). Claude
4.7 and later also reject temperatures below 1. A closed model's probability over the candidates
must therefore be estimated by sampling; with 10 samples per state, a 50/50 choice carries a 95%
interval of about ±0.26 (estimate). Two traps follow. Anthropic's `reasoning_extraction` classifier
can refuse prompts that ask for "a `reasoning`, `thinking`, or `trace` field in JSON output", and as
of September 2026 such refusals are billed, so prompts should ask for a short explanation instead
([refusals docs](https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback)). And
stated reasons are weak evidence: explanations "systematically fail to mention" planted biases
([Turpin et al. 2023](https://arxiv.org/abs/2305.04388)), Claude 3.7 Sonnet mentioned a hint it had
used 25% of the time ([Anthropic
2025](https://www.anthropic.com/research/reasoning-models-dont-say-think)), and monitors' detection
of incidental nudges fell as low as 5% under realistic system prompts ([arXiv
2608.04735](https://arxiv.org/abs/2608.04735)). Reasoning that is genuinely needed almost always
shows up ([METR](https://www.alignmentforum.org/posts/WAxkA6gDgrschZovx)), but easy first-floor
decisions are the regime where explanations are least constrained. Finally, re-running identical
inputs changed agent models' actions in 8.7% of replicate pairs ([arXiv
2609.03221](https://arxiv.org/abs/2609.03221)), and LLMs favor some option positions over others
([Zheng et al., ICLR 2024](https://arxiv.org/abs/2309.03882)), so every flip rate needs a measured
noise floor beside it. An outsider's closest look inside a closed model is a behavioral twin: run an
open model on the same counterfactual sets, and where its decision boundaries match the closed
model's, treat its internals as a hypothesis about the closed one, never as evidence.

**Prior art for visuals.** Saliency maps alone are "an exploratory tool rather than an explanatory
tool" ([Atrey et al., ICLR 2020](https://arxiv.org/abs/1912.05743)). In a 124-participant study only
saliency combined with reward bars improved non-experts' understanding significantly ([Anderson et
al., IJCAI 2019](https://ijcai.org/proceedings/2019/184)), and minimal counterfactual game frames
helped non-experts spot a flawed agent ([Olson et al. 2021](https://arxiv.org/abs/2101.12446)). Game
AI's lasting visual forms are a value-over-time curve (OpenAI Five's announced win probability), a
distribution over moves (chess-engine GUIs, poker-solver frequency grids), and the model's text
beside the game (Claude Plays Pokémon). BalatroBench shows leaderboard columns, and Orak and
AgenticSTS release trajectories without a viewer. The notes found **no public LLM game benchmark
that shows per-decision probability distributions across models**, which is the visual niche here.

**What it would take here.** Everything below runs offline on saved states; the engine is needed
only to validate a steering claim or to branch-replay a few showcase states. The behavioral
experiments cover every policy. Costs assume a frozen bank of about 300 states, about 2,000 input
and 1,000 output tokens per query with the fixed prefix cached, and list prices before the 50% batch
discount (estimates):

| Behavioral experiment | What the visual shows | Queries | Haiku 5.5 | Opus 5.5 |
|---|---|---:|---:|---:|
| Noise floor and invariance: re-query identical states, shuffle candidate order, reorder the hand, reformat the prompt | Each model's stochastic floor and position bias; gates every flip rate below | ~6k | ≈$3 | ≈$134 |
| Per-decision probability bars on a replayed real-engine combat, with disagreement markers and an HP strip | How confident each policy is and where they part ways | ~3k | ≈$2 | ≈$67 |
| "What flips the decision": sweep incoming damage, block, HP and monster HP; plot P(Defend) against incoming damage with the heuristic's threshold overlaid | Each policy's decision boundaries, and whether they are sensible and monotone | ~18k | ≈$10 | ≈$401 |
| Faithfulness of stated reasons: a "said vs did" matrix, hint insertion ("coach's note: play Bash"), and whether a reader can predict edited-state choices from the explanation | Whether explanations are faithful or merely plausible | ~5k | ≈$3 | ≈$112 |
| Agreement matrices, a 2-D "style map", depth-4 surrogate decision trees with fidelity, and a disagreement gallery ranked by stakes, with 10–20 states branch-replayed in the engine | Which policies decide alike, the rules each appears to follow, and the decisive disagreements | Reuses the above | — | — |

Edits that leave the legal candidates unchanged (intent damage, HP, block, monster HP, powers) come
first; edits to the hand, energy or draw pile need a recomputed candidate list so the `Decision`
contract still holds. Full sweeps suit the cheap models, with flagship spot checks on a few states.

The mechanistic experiments apply to Qwen and the PPO network, need only the GPU and saved traces,
and are listed by value for effort (owner-days with a coding agent, estimates):

| Mechanistic experiment | What it would show | Effort |
|---|---|---|
| Decision X-ray: a logit or Jacobian lens over layers × legal candidates, for the base, SFT, relabel and REINFORCE adapters, beside the heuristic's pick | At which layer the choice forms, and how each fine-tune moves it | 2–4 days |
| Probes for derived tactical concepts (net incoming damage, lethal available, "should block"), with control tasks, a random-weights baseline and held-out encounters | Whether SFT or RL makes these concepts more linearly readable | 4–7 days |
| Activation patching on the Cultist "finish versus block" decision | Which state tokens and layers carry the change the one-update REINFORCE adapter made ("it now finishes a 3-HP Cultist instead of blocking") | 4–7 days |
| Steering along an attack-versus-block direction, with predictions written down first and a prompt-instruction baseline | A dial from defensive to aggressive play, with engine-confirmed wins and HP at each setting | 3–5 days plus ~1 engine-hour (5 settings × 12 fights) |
| Adapter diffing: singular spectra and cosines of the rank-8 updates, and activation differences | Whether the RL change is small and late-layer, as math-RL studies report | 4–8 days |
| One attribution graph for a headline decision, from the Qwen3-0.6B transcoders | Prompt tokens → features → the logit difference between two cards | 5–10 days; untested within 7.7 GiB of RAM |
| Full analysis of the 12.5k-parameter set encoder: weights, integrated gradients, ablations | A contrast panel showing what a tiny, barely trained network attends to | 1–3 days |

A static, evidence-linked trace viewer would hold the results together: the combat drawn the way the
game draws it, per-candidate bars for every policy, explanation text and clearly labeled thinking
summaries, a precomputed counterfactual slider, and links to the audited traces. The behavioral
sampling harness is the one section 10's fourth step needs for the frontier baseline, so the two can
share a 20-state, 10-sample pilot per closed model that measures real token counts, checks whether
GPT-6 Luna's log-probabilities work, and catches refusals before any larger spend. The first five
mechanistic experiments would make a portfolio-grade write-up in about 3–5 weeks part-time
(estimate). Two facts affect the tooling. The current LoRA touches only attention, so the MLPs the
transcoders describe are unchanged under every adapter (an inference, not a published result), and
the planned MLP-inclusive LoRA would remove that convenience. And Qwen3.5 uses full attention in
only one layer in four (the others are Gated DeltaNet), so attention views cover a quarter of its
layers and no tool found draws attribution graphs through the rest.

**Risks.** Interpretability results are easy to over-read. Probes can learn the prompt template
instead of the concept, so they need control tasks ([Hewitt & Liang
2019](https://arxiv.org/abs/1909.03368)) and held-out encounters, not just held-out states. Subspace
patching can produce illusions ([Makelov et al. 2023](https://arxiv.org/abs/2311.17030)), attention
weights are not explanations ([Jain & Wallace 2019](https://arxiv.org/abs/1902.10186)), and narrow
fine-tunes leave easily read "this is a game prompt" traces that are not discoveries ([Minder et
al., ICLR 2026](https://arxiv.org/abs/2510.13900)). Edited states may be ones the engine could never
produce, so findings should be confirmed on reachable states. Base-model dictionaries may fit
adapter-shifted activations poorly, which has to be measured. The evidence that RL updates are
sparse and late-layer ([Mukherjee et al., NeurIPS 2025](https://arxiv.org/abs/2505.11711); [arXiv
2609.15064](https://arxiv.org/abs/2609.15064)) comes from math and reasoning RL with many updates,
not one or two. Closed models change every few months, and their thinking summaries come from a
separate model whose fidelity nobody has measured.

**What it would teach and show.** Causal experimental design (controls, baselines, predictions
written down first) and the current interpretability toolchain, on a model small enough to study
completely. The portfolio question has a measurable answer: what changed inside a 0.6B policy when
one REINFORCE update taught it to finish a 3-HP Cultist instead of blocking? Neel Nanda's guide
calls public write-ups the main credential in the field and recommends short, well-baselined
projects over training new dictionaries ([Nanda,
2025-09-02](https://www.alignmentforum.org/posts/jP9KDyMkchuv6tHwm/how-to-become-a-mechanistic-interpretability-researcher)).
Anthropic Fellows lists mechanistic interpretability as an area and reports that over 35% of fellows
joined Anthropic (self-reported;
[Anthropic](https://alignment.anthropic.com/2025/anthropic-fellows-program-2026/)); whether such
programs sponsor visas was not verified. The behavioral experiments alone would be the first
counterfactual, faithfulness and noise-floor analysis the notes know of for frontier models choosing
actions in a real game.

### Robotics: the project already has the shape of a robot-learning setup

**The link.** The connection is in method, not domain. The original engine behaves like a physical
robot: one slow instance (about 94 fights an hour), an expensive reset (26% of a heuristic fight's
wall time is JVM start), an exact verifier, a safety layer, and, once a simulator exists, a
sim-to-real gap. Several of the project's mechanisms are standard robotics patterns under other
names. The candidate list plus `validate_action` is a preemptive shield, which hands the agent only
safe actions ([Alshiekh et al. 2017](https://arxiv.org/abs/1708.08611)); the Windows job object that
kills the JVM on controller EOF is a watchdog; the combat-start hash gate is a verified reset; and
the split between bridge, protocol and gameplay failures is the fault taxonomy that robot-evaluation
systems keep. Robot-learning labs in 2025–2026 worked on the questions this project faces: how to
improve a policy when real trials are scarce, how to evaluate it credibly, and when to trust a
simulator. The notes found no paper that uses a turn-based card game as a robotics proxy, and the
project should not claim to be one. Slay the Spire isolates decision-making under partial
observability with an exact verifier, with no perception or control.

**ENPIRE, read closely.** ENPIRE (NVIDIA GEAR with CMU and Berkeley; arXiv v1 2026-06-18, v2
2026-09-20; CoRL 2026; Apache-2.0 code) runs in two stages ([arXiv
2606.19980](https://arxiv.org/abs/2606.19980); [code](https://github.com/NVlabs/ENPIRE)). Coding
agents first build safety limits, a binary verifier and an auto-reset, which humans assess and which
then freeze as fixed interfaces; the agents then loop reset → execute → verify → refine. Its written
contract for the agents reads almost like this repository's rules. Agents may edit only policy and
training code, while the environment, reset, verifier, safety limits, evaluation seeds and scorer
are protected. Each iteration records one falsifiable hypothesis, runs offline tests first, spends
only an approved number of real trials, and keeps a change only if it passes success and regression
gates. "Never redefine success inside the policy", failed trials are preserved, and a run is invalid
if human actions are counted as the policy's
([contract](https://raw.githubusercontent.com/NVlabs/ENPIRE/main/enpire/policy/autoresearch_instruction.md)).
The agents (Claude Code, Codex and Kimi Code) wrote heuristic controllers, behavior cloning, offline
and online RL, and tool code around a VLA. The headline 99% is pass@8, up to eight attempts that see
earlier failures, not independent samples. Going from one agent and robot to eight cut Push-T from
about five hours to two, but token cost grew super-linearly and robots sat idle while agents read
logs. All three agents solved Push-T in simulation, and two of the three failed on the real robot
(all self-reported); no dollar cost is reported. The project already has ENPIRE's environment and
rollout pieces in stricter form (an exact verifier, a hash-gated reset, independent re-audits,
contracts declared before runs). It lacks the agent driver, ENPIRE's hypothesis tree (one git branch
per idea, compared and pruned), and headroom: on today's catalog, where the heuristic wins 12 of 12,
an agent would climb noise. A follow-up from overlapping authors, SimEX (2026-09-30), has the agent
replay real rollouts in simulation and patch the simulator until they match. It reports 26 of 30
real trials against 3 of 30 for its own reimplementation of ENPIRE (self-reported; [arXiv
2609.38982](https://arxiv.org/abs/2609.38982)), which supports this guide's parity-before-training
order.

**Code-as-policy.** Robotics moved from LLM programs over fixed primitive APIs ([Code as Policies,
2022](https://arxiv.org/abs/2209.07753)) to coding agents that search over whole policy repositories
at training time ([RHO](https://arxiv.org/abs/2606.16458) and
[ASPIRE](https://arxiv.org/abs/2607.00272), 2026). The finding that transfers best is CaP-X's:
performance drops as human-designed abstractions are removed ([CaP-X, ICML
2026](https://arxiv.org/abs/2603.22435)). For this project that makes the policy's interface an
experimental variable. The same coding agent could get raw `Decision` fields, then raw fields plus
derived predicates (incoming damage, lethal this turn), then those plus a library of earlier fixes,
with each level scored on a held-out catalog. LLM-written invariants checked over saved traces, such
as "ended the turn with unspent energy and a playable card", are the game counterpart of
Code-as-Monitor ([CVPR 2025](https://arxiv.org/abs/2412.04455)) and give dense failure signals at no
engine cost. Code-as-policy in robotics is held back by contact and perception, which Slay the Spire
lacks; Gemini Robotics-ER's zero-shot code control averaged 25% on a real ALOHA 2 robot ([Gemini
Robotics, 2025](https://arxiv.org/abs/2503.20020)).

**Robot post-training mirrors this project's post-training.** Physical Intelligence's RECAP (π*0.6,
2025-11-18) is the closest robotics analogue to the Qwen track ([arXiv
2511.14759](https://arxiv.org/abs/2511.14759)). It trains a value function on all collected data,
computes each step's advantage, marks it positive when it exceeds the task's 30th percentile, and
gives the policy that mark as the text "Advantage: positive" or "Advantage: negative" during
ordinary supervised fine-tuning, with human corrections always positive; the policy is then run
conditioned on the positive label. The authors report that PPO and AWR "fall far short" and that on
some of the hardest tasks RECAP "more than doubles task throughput and roughly halves the task
failure rate". Because the mark is a prompt string, the method fits an LLM policy almost literally:
a value model trained on every audited trace (heuristic, random, PPO, SFT, relabel and REINFORCE)
would label turns by HP lost, the existing SFT code would do the training, and the engine would only
collect data and confirm results. SimpleVLA-RL, GRPO for robot policies, drops groups in which every
rollout had the same outcome ([arXiv 2509.09674](https://arxiv.org/abs/2509.09674)); that is the
"Louses 77×4, no signal" case in the stopped REINFORCE continuation. Real-world robot RL became
practical through off-policy learning from a few demonstrations rather than on-policy PPO. HIL-SERL
reached near-100% success in 1–2.5 hours of real training from 20–30 demonstrations, sampling half
of each batch from demonstrations and half from its own experience, with human interventions that
tapered off (self-reported; [arXiv 2410.21845](https://arxiv.org/abs/2410.21845)). If the
set-encoder track returns, that is the robotics-consistent design, with heuristic traces as the
demonstration buffer and the heuristic as the intervening teacher.

**Evaluation and sim-to-real.** AutoEval (Berkeley, CoRL 2025) runs real-robot evaluation around the
clock from a job queue: about 500 episodes a day with about 3 human interventions, an alert to a
person after three failed resets, Pearson 0.942 against human-run evaluation, and drift noticed
after about 8 hours (self-reported; [arXiv 2503.24278](https://arxiv.org/abs/2503.24278)). Its
retry-then-escalate handling would have let the stopped REINFORCE job survive its transient Windows
interop timeout. Robotics papers also push better statistics: explicit trial counts, initial
conditions and success criteria ([Kress-Gazit et al. 2024](https://arxiv.org/abs/2409.09491)), and
sequential tests that stop early without p-hacking ([STEP, RSS
2025](https://arxiv.org/abs/2503.10966)). For simulators, robotics asks above all whether the
simulator **ranks policies the way reality does**. SIMPLER reports Pearson r and MMRV, a
rank-violation measure, between simulated and real success; its best setup reached r = 0.924 and
MMRV = 0.056, against 0.308 and 0.375 for a validation-loss baseline ([SIMPLER, CoRL
2024](https://arxiv.org/abs/2405.05941)). SureSim combines many simulated runs with a few paired
real ones into confidence intervals on real performance ([arXiv
2510.04354](https://arxiv.org/abs/2510.04354)). Slay the Spire can also report something robotics
cannot, exact transition parity, because both engines are deterministic given the seed and the
actions. A parity study that reports both levels over the project's seven existing policies
(heuristic, random, two PPO checkpoints, SFT, relabel, REINFORCE) would show whether imperfect
parity still ranks policies correctly.

**What it would take here.** Ranked by value for effort; efforts are estimates.

| Extension | Borrows from | Effort (estimate) | Precondition |
|---|---|---|---|
| 1. Evaluation service: a queue, retry-then-escalate on transient faults, interventions per 24 h, infrastructure failures per 100 combats, drift plots, paired bootstrap intervals and sequential stopping | AutoEval, Kress-Gazit et al., STEP | 2–4 days | None |
| 2. Self-improvement loop on the real engine under ENPIRE's contract, with protected paths enforced by a check on every candidate diff, a hypothesis tree, action-source labels, and tokens per kept improvement | ENPIRE | 4–7 days for the harness, then ~12 candidates an hour overnight | Section 10's harder and hidden held-out catalogs |
| 3. Advantage-conditioned training of the Qwen policy, compared with REINFORCE at an equal engine budget | π*0.6 (RECAP), SimpleVLA-RL | 1–2 weeks | None |
| 4. Sim-to-real study: transition parity plus r, MMRV and corrected intervals over seven policies | SIMPLER, SureSim | 3–5 days after the parity replay | An sts_lightspeed binding (section 1) |
| 5. Agentic simulator correction, judged by the exact divergence rate on held-out traces | SimEX, ASPIRE | 1–3 weeks | Item 4 |
| 6. Code-as-policy evolution with simulator screening and real-engine confirmation, plus the interface ablation | CaP-X, RHO, ASPIRE | 2–4 weeks | Items 4–5 for scale; the ablation alone runs on the real engine |

Item 2 is section 10's fifth step (the autoresearch loop) carried out in ENPIRE's terms, and items
4–6 extend its sixth step, so much of this direction sharpens work already planned rather than
adding to it. A direct robotics touchpoint needs no hardware: running ENPIRE's own Push-T prompt on
the open `gym-pusht` simulator through item 2's harness (2–3 days on CPU, estimate) would show that
the harness is domain-agnostic and independently check ENPIRE's simulation result. It reuses loop
code, not game code, and belongs in the portfolio as a labeled side experiment.

**Risks.** Overclaiming is the main one. The project cannot show hardware, control or perception,
and nothing shows that card-game skill transfers to robots. ENPIRE's results are self-reported, with
costs and per-agent numbers only in figures; SimEX's ENPIRE baseline is a competitor's
reimplementation; and RECAP has been shown only on Physical Intelligence's own stack. An agent loop
on a saturated catalog would optimize noise, as section 6 warns.

**What it would teach and show.** Robot-learning postings in 2026 repeatedly ask for evaluation
frameworks, task definitions and success criteria, reproducible policy evaluation and diagnosis of
real-world failures, alongside multimodal LLM training and simulators such as MuJoCo or Isaac Sim
(for example [NVIDIA
GEAR](https://jobs.anitab.org/companies/nvidia/jobs/68139470-senior-research-engineer-generalist-embodied-agent-research),
[Amazon Fauna](https://scoutify.com/companies/amazon/jobs/1352280/) and
[Runway](https://jobs.madrona.com/companies/runway-3/jobs/81324241-member-of-technical-staff-robotics-engineer),
read through job aggregators; visa sponsorship not verified). Evaluation infrastructure is the
project's strongest area, and the defensible pitch is a slow, single-instance real system with an
exact verifier, on which the owner built the evaluation and self-improvement infrastructure that
robot-learning labs build for robots. Using the robotics names in the docs (shield, watchdog,
verified reset, sim-to-real ranking fidelity) costs nothing and makes those skills recognizable. The
direction also serves the goal of learning to build with coding agents: ENPIRE's agents are Claude
Code, Codex and Kimi Code working under a written contract, which is how this project is already
built.

### Order

Most of these experiments need decisions on which policies disagree and outcomes vary, so they gain
from section 10's first step, a harder and held-out catalog. After that, the cheapest wins overlap
with planned work. The behavioral pilot shares its sampling harness with the frontier baseline (step
4), the evaluation service strengthens every later comparison, and ENPIRE's contract is a way to run
step 5. Mechanistic work on Qwen needs only the GPU and saved traces, so it can run while the engine
is busy, but it is worth more once the language track has chosen the adapter worth explaining; the
Decision X-ray and the probability-bar viewer are the quickest routes to visuals.
Advantage-conditioned training competes with section 10's language-track changes for the same engine
time and is best treated as one more of them. The sim-to-real work waits on simulator parity (step
6).

## Conclusion

The research shifts the question from which algorithm to which resource. Algorithms have
converged: generic policy gradient, low-rank LoRA, group baselines and determinized search all
work. What separates the 2026 successes is cheap, trustworthy evaluation, whether a fast simulator
for RL, an automatic verifier for program search or a near-perfect oracle for an agent swarm. This
project has the opposite profile, with evaluation that is slow, serialized and expensive but
unusually trustworthy: original engine, public information only, audited traces. Much of that
slowness is animation and process restarts rather than game logic, so a parity-gated fast mode
and parallel instances can recover an order of magnitude without giving up the real engine. That makes
sample efficiency and evaluation design the project's real research problems, and they are the
parts of the field the notes found least covered for Slay the Spire.

The second lesson is that who sees what decides which results count. Several headline numbers come
from searches that read RNG or future draws, and a student trained on such a teacher learns labels
it cannot reproduce. An honest-information pipeline, running from a public-state policy through a
determinized search teacher to a real-engine audit, would be a credible contribution even at
first-floor scale, and it is what would make any later full-game result comparable to the human
reference points of 9% across all StS1 runs in 2020 and 16% at StS2 A0.

## Addendum, 2026-10-12: self-improving harnesses, an StS1 benchmark and training services

*Added after the full-run API model track started ([fullrun/README.md](fullrun/README.md)); sources were read
on 2026-10-12. That page lists the ideas taken from this research for its loop.*

**Self-improving harnesses.**
- **Continual Harness** (arXiv 2605.09998, May 2026) automates the human refinement loop of
  Gemini Plays Pokémon within one episode, without resets.
  - **How it works:** a Refiner, run by the same model as the player, reads the last 50 steps
    with automatic failure flags such as "possible loop". It then edits four stores: the
    strategy prompt, sub-agents, code skills and memory. The released code refines after 25
    steps, every 25 steps up to step 200, and every 100 after that.
  - **Results:** on Pokémon Emerald, Gemini 3 Pro reached 100% of milestones at a median of
    $130, against 98% at $215 for a minimal harness. Flash was mixed. Every Flash-Lite variant
    scored below the minimal harness's 20%.
  - **Gaps:** the paper has no component ablation and no check or rollback of edits. It credits
    most of the gain to code skills, and most authored skills were never used.
  - **The released harness:** the evolved Pokémon Red harness holds 13 overlapping navigation
    skills and a prompt that drifted into run-specific goals.
  - **Co-learning loop:** Gemini relabels a Gemma-4 student's low-reward steps for SFT. It
    reports no absolute gains, and its training code is not released.
- **Growing Harness** (arXiv 2609.26760) has an offline optimizer edit harness code, only in
  functions that appear in failing traces. It accepts a change only if a gate set does not
  regress. Without the gate, success on the gate set rose to 30% and then fell to 16%. Moving
  control logic into code cut inference cost by 74–99% against a tool-calling agent.
- **Meta-Harness** (arXiv 2603.28052) has a coding agent read every earlier harness with its
  scores and raw traces. Proposers given raw traces scored a median of 50.0, against 34.6 with
  scores only and 34.9 with summaries.
- **DemoEvolve** (section 6) is the closest setup to this project's full-run track:
  - GPT-5.4 at low effort plays and Opus 4.7 proposes changes;
  - changes are selected on three development seeds, about 60 development rollouts in all;
  - results are reported on two held-out seeds;
  - human demonstrations go to the proposer only.
- **ACE** (arXiv 2510.04618) edits a playbook through itemized additions with helpful and harmful
  counters. It records how a whole-context rewrite collapsed from 18,282 to 122 tokens and
  dropped accuracy below the baseline.
- **"Harness Updating Is Not Harness Benefit"** (arXiv 2605.30621) finds that weak models fail to
  use or follow the harness changes made for them.

**An StS1 benchmark.**
- **SpireBench** (Lowe and Keemink, arXiv 2610.12596, 2026-10-08) is unrelated to the StS2 trial
  of the same name in section 3. It plays the original game's Ironclad at Ascension 20 through
  CommunicationModPlus, with 10 runs per model. Whether its interface hides the same information
  as this project's was not checked.
- **Results** (mean floor, acts cleared, cost per run):

  | Model | Mean floor | Acts cleared | Cost per run |
  |---|---|---|---|
  | GPT-6 Astra (max) | 37.0 | 1.50 | $33.09 |
  | Claude Fable 5.1 (max) | 36.2 | 1.60 | $61.91 |
  | Claude Opus 5 | 32.5 | 1.30 | $60.62 |
  | GLM-5.3 (max) | 22.1 | 0.60 | $3.92 |
  | DeepSeek V4.1 Flash | 16.9 | 0.30 | at most $0.35 |
  | GLM-5.3 Flash | 15.6 | 0.40 | $0.40 |
  | Qwen3.8 27B | 14.9 | 0.20 | — |
  | GPT-5.6 Luna (max) | 14.2 | 0.10 | $0.24 |
  | Human telemetry (206,082 runs) | 22.1 | 0.73 | — |
  | BottledAI | 11.3 | — | — |
  | Random choice | 7.5 | — | — |

  Only GPT-5.6 Sol killed the final boss, once. `gpt-6-luna` was not tested.
- **Fights, not route:** stronger models are "stronger mainly in the fights, not in the route".
  HP change over hallway fights separates models (ρ = +0.62). Elites taken, shops, resting and
  skipped rewards do not.
- **Memory across runs:** over 80 matched pairs per arm, consolidated memory added +0.00 acts
  and verbatim notes +0.06.
  - 17% of memories were false: 78% of written rules, against 9% of statements of fact.
  - 119 memories advised caution and 17 advised risk.
  - One model's system prompt grew to 227,089 characters.
- **Other findings:**
  - Models rest at 57–75% of rest sites, against 23% of players.
  - They bring 19.3 cards to the Act 1 boss, against 16.8 for humans.
  - One action per response needed 3.0 more calls per floor, cost 23% more and cleared 0.07
    fewer acts.
  - Renamed cards and enemies cost 0.14 acts, so prior knowledge is part of the score.

**Corrections and updates to section 4.**
- **Prime Intellect:**
  - It retired shared LoRA training; the CLI warning gives 2026-10-05.
  - On-demand Hosted Training replaced it. It is in beta, billed per GPU-hour, with rates shown
    only in the CLI.
  - Hosted Training runs rollouts in Prime's own pods and sandboxes, so a local game would need
    a tunnel while paid GPUs wait.
  - prime-rl's full RL stack needs two GPUs.
  - The `verifiers` main branch has removed its v0 API while the docs still call it
    deprecated.
  - Its Environments Hub has no Slay the Spire or game environment.
- **OpenAI** blocked new fine-tuning in three steps:
  - from 2026-05-07, organizations that had never fine-tuned;
  - from 2026-07-02, organizations without fine-tuned inference in the previous 60 days;
  - from 2027-01-06, everyone.

  `gpt-6-luna` cannot be fine-tuned.
- **Tinker:**
  - It added Qwen3.8-27B ($0.6975 / $5.595 / $4.103 per million tokens of prefill, sampling and
    training), DeepSeek-V4.1-Flash, GLM-5.3, GLM-5.3-Flash and Kimi-K2.6.
  - Qwen3.6-27B, DeepSeek-V3.1 and Nemotron-3-Nano retire on 2026-10-23.
  - Its API is now the portable choice: Fireworks' serverless training, Baseten Loops (early
    access) and SkyRL v0.4.0 on local GPUs all implement it.
- **Fireworks** managed RFT takes no new jobs.
- **CoreWeave Serverless RL** (formerly W&B) is in public preview with free training. Whether
  personal accounts are allowed was not verified.
- **What this means for the full-run track:** training an open model would buy a free local
  player near Luna's level, not a stronger one. Luna-class open models scored within noise of
  GPT-5.6 Luna on SpireBench, and Luna runs here cost $0.03–0.17.

**Wall time on the full-run track.** In the v6 and v7 runs, model calls took 70–80% of wall time,
at a median of about 3 s per call. The Summary's claim that engine wall-clock decides holds for the
RL and local-model tracks. On the API model track, API latency decides.

## Addendum, 2026-10-12 (evening): an open StS1 benchmark

*Prompted by the owner after the second full-run session, when SpireBench's code turned out
not to be public. Sources were read on 2026-10-12.*

**What is public.**
- **SpireBench** (above) is the most complete StS1 full-run benchmark: Ironclad at A20, every
  decision made by the model, 20 models, ten fixed held-out seeds. No code is public as of
  2026-10-12.
  - The arXiv page has no comment or code link.
  - The paper links only upstream projects (CommunicationMod, Bottled AI) and human run data.
  - Its CommunicationModPlus fork appears in no public repository.
  - The first author's public GitHub has no related repository.
  - The preprint is four days old, so a release may follow. Check again before building.
- **Orak** (KRAFTON, MIT license, last pushed 2025-06-17) is open and includes StS1 through a
  modified CommunicationMod with file-based input and output. It is not a full-run benchmark:
  - Its default config plays one seed (0) at Ascension 0 with a 200-step cap.
  - Rules make the map, event and potion decisions.
- **Slay the Spire 2:** ClaudePlaysTheSpire (MIT; its "SpireBench" trial is unrelated to the
  paper) and AgenticSTS publish harness code.
- **Hobby harnesses** on CommunicationMod (spirecomm forks, small LLM bots) report a few runs
  each, with no fixed seeds or results table.

**The gap.** No open benchmark has a model make every decision of complete StS1 runs with:
- fixed public and held-out seeds;
- a declared information boundary;
- per-decision traces;
- cost accounting.

**What this project already has.**
- The pinned engine and mods, checked by hash (`spire/engine/runtime.py`).
- Seeded complete runs, one JVM per run.
- A public decision boundary that labels every legal choice and removes hidden state
  (`spire/decisions.py`).
- A failure taxonomy that keeps infrastructure stops out of gameplay results. v9's run
  stopped by an accidental Escape is an example.
- Provenance per job: source fingerprints and the prompt hash.
- A spend ledger with a hard cap.
- Full traces with failure flags (`spire digest`).
- A runner that takes any policy. The open-weight skeleton already plugs into it.

**What a benchmark would still need.**
1. **Seed sets:** development seeds plus held-out seeds, the same for every model (SpireBench
   uses ten).
2. **A results table:** acts cleared, floor reached, bosses beaten, wins, and cost and calls
   per floor, with spread over runs. This is the `spire stats` plan in
   [fullrun/README.md](fullrun/README.md#ideas-from-related-work-2026-10-12); the v7 replay
   showed that one run per seed cannot rank anything.
3. **Harness levels:** a bare interface and the tuned scaffolding as named, frozen versions,
   to separate the model from the scaffolding. Possibly also a reference compendium, which
   SpireBench's prompt includes for the rules and every card, relic and potion. Game text
   cannot be redistributed, so a compendium would be hand-written or generated from the
   user's own install.
4. **Baselines:**
   - random choice;
   - a scripted policy;
   - Bottled AI (rules plus search);
   - human runs from Mega Crit's released telemetry ([section 8](#8-imitation-from-human-run-data-77-million-runs-zero-combat-actions)).
5. **Setup others can reproduce.** Today it is a Windows game with a WSL controller and
   Workshop jars pinned by hash, and every user must own the game.
6. **Throughput.** Runs take 15–60 minutes and one game runs per machine, so ten seeds per
   model is an evening per model.

**Risks.**
- If SpireBench publishes its harness, the value of an open one narrows to the A0 and
  cheap-model tier, the harness levels and the public traces. Contributing to theirs is also
  an option.
- The game is proprietary: no game files, saves or game text can ship.
- A benchmark needs upkeep: engine pins, model APIs and prices.
- The autoresearch loop changes the harness, but a benchmark needs it frozen. Benchmark
  entries must name a frozen scaffolding version.

**First step.** Build `spire stats` and fix the seed sets. Both serve the loop now and are
the core of any benchmark. Then decide the scope and a public name, for example Ironclad A0
complete runs with every decision by the model, after rechecking whether SpireBench has
released code.

## Sources

All links below are cited in this guide and appear in the research notes. They are grouped by the
section where each is first cited.

### Engine speed and reimplementations

- [ForgottenArbiter/CommunicationMod, GameStateListener.java (stability rules)](https://github.com/ForgottenArbiter/CommunicationMod/blob/master/src/main/java/communicationmod/GameStateListener.java)
- [Skrelpoid/SuperFastMode (MIT, 12-18-2022 build)](https://github.com/Skrelpoid/SuperFastMode)
- [SuperFastMode issue #38](https://github.com/Skrelpoid/SuperFastMode/issues/38)
- [boardengineer/LudicrousSpeed](https://github.com/boardengineer/LudicrousSpeed)
- [boardengineer/STSStateSaver](https://github.com/boardengineer/STSStateSaver)
- [destire-mio/sts-ironclad-agent, live-original runbook (parallel instances)](https://github.com/destire-mio/sts-ironclad-agent/blob/main/live_original/README.md)
- [lhy-loveworld/rusted-spire (Rust + PyO3, headless oracle)](https://github.com/lhy-loveworld/rusted-spire)
- [rusted-spire COMBAT_TRACES.md (530 snapshots from the 12-18-2022 jar)](https://github.com/lhy-loveworld/rusted-spire/blob/HEAD/docs/COMBAT_TRACES.md)
- [degraffa/SpeedTheSpire (C++20 reimplementation)](https://github.com/degraffa/SpeedTheSpire)
- [SpeedTheSpire throughput report](https://github.com/degraffa/SpeedTheSpire/blob/HEAD/docs/verification/s245-throughput.md)
- [rob-pitkin/mini-spire](https://github.com/rob-pitkin/mini-spire)
- [JAX `lax.cond` documentation (both branches traced under vmap)](https://docs.jax.dev/en/latest/_autosummary/jax.lax.cond.html)
- [JAX issue #4453, lax.switch compile time super-linear in switch options (2020)](https://github.com/jax-ml/jax/issues/4453)
- [JAX installation (WSL2 GPU support experimental)](https://docs.jax.dev/en/latest/installation.html)
- [Koyamada et al., Pgx, arXiv 2303.17503 (NeurIPS 2023)](https://arxiv.org/abs/2303.17503)
- [NetHax benchmark](https://github.com/rsiegemit/NetHax/blob/main/docs/benchmark.md)
- [Michael-OvO/balatro-rl (JAX Balatro engine)](https://github.com/Michael-OvO/balatro-rl)

### Pure RL, search and Slay the Spire bots

- [Antonoglou et al., Stochastic MuZero, ICLR 2022](https://iclr.cc/virtual/2022/poster/6832)
- [Danihelka et al., Gumbel AlphaZero/MuZero, ICLR 2022](https://iclr.cc/virtual/2022/spotlight/6419)
- [google-deepmind/mctx, JAX MCTS library](https://github.com/google-deepmind/mctx)
- [Cowling, Powley & Whitehouse, Information Set MCTS, IEEE TCIAIG 2012](https://eprints.whiterose.ac.uk/75048)
- [Brown et al., ReBeL, arXiv 2007.13544 (NeurIPS 2020)](https://arxiv.org/abs/2007.13544)
- [Silver et al., AlphaZero, arXiv 1712.01815 (2017)](https://arxiv.org/abs/1712.01815)
- [Sokota et al., Ataraxos (superhuman Stratego), arXiv 2511.07312v2 (Nov 2025, v2 Oct 2026)](https://arxiv.org/html/2511.07312v2)
- [Superhuman Generals.io by self-play, arXiv 2606.23348 (Jun 2026)](https://arxiv.org/abs/2606.23348)
- [Generic policy gradient vs specialized imperfect-information RL, arXiv 2502.08938 (2025)](https://arxiv.org/abs/2502.08938)
- [Search with learned nets in Legends of Code and Magic, arXiv 2609.06816 (Sep 2026)](https://arxiv.org/abs/2609.06816)
- [PufferLib 3.0 release blog (2025)](https://puffer.ai/blog/3.0/)
- [Matthews et al., Craftax, arXiv 2402.16801 (ICML 2024)](https://arxiv.org/abs/2402.16801v1)
- [NeurIPS 2021 NetHack Challenge report](https://nethackchallenge.com/report.html)
- [NetHack is Hard to Hack, arXiv 2305.19240 (NeurIPS 2023)](https://arxiv.org/pdf/2305.19240)
- [Dreamer 4, arXiv 2509.24527 (Sep 2025)](https://arxiv.org/abs/2509.24527)
- [MindrLabs/typed-decision-slay-the-spire, README (Oct 2026)](https://github.com/MindrLabs/typed-decision-slay-the-spire)
- [destire-mio/sts-ironclad-agent, README (Sep–Oct 2026)](https://github.com/destire-mio/sts-ironclad-agent)
- [Jialeiv/sts-rl-agent, README (Jul–Sep 2026)](https://github.com/Jialeiv/sts-rl-agent)
- [yuchinchenTW/conquer-the-spire fork (Sep 2026)](https://github.com/yuchinchenTW/conquer-the-spire)
- [AttemorySystem/spire-agent, README (Sep 2026)](https://github.com/AttemorySystem/spire-agent)
- [xaved88/bottled_ai, win rates (stats Oct 2024)](https://github.com/xaved88/bottled_ai/blob/main/docs/winrates.md)
- [cicero225/STS2FableBot, README (2026)](https://github.com/cicero225/STS2FableBot)
- [zhiyue/sts2-rl-agent, README (May 2026)](https://github.com/zhiyue/sts2-rl-agent)
- [gamerpuppy/sts_lightspeed, README](https://github.com/gamerpuppy/sts_lightspeed)
- [Mini-spire, single-fight C++ PPO write-up (Jun 2026)](https://rhp.bearblog.dev/mini-spire/)
- [Jialeiv/sts-rl-agent, Hugging Face model card](https://huggingface.co/Jialeiv/sts-rl-agent)
- [Li et al., Suphx (Mahjong), arXiv 2003.13590 (2020)](https://arxiv.org/abs/2003.13590)

### Small-LLM post-training

- [Hugging Face TRL paper index](https://huggingface.co/docs/trl/paper_index)
- [MT-GRPO, arXiv 2505.11821](https://arxiv.org/html/2505.11821v3)
- [GiGPO, arXiv 2505.10978 (NeurIPS 2025)](https://arxiv.org/pdf/2505.10978)
- [Thinking Machines, LoRA Without Regret (2025-09-29)](https://thinkingmachines.ai/blog/lora/)
- [rl-llm-wiki discussion of LoRA Without Regret's replication status](https://huggingface.co/datasets/rl-llm-wiki/knowledge-base/discussions/747)
- [GiGPO, arXiv 2505.10978v2 (HTML, results tables)](https://arxiv.org/html/2505.10978v2)
- [RAGEN / StarPO, arXiv 2504.20073](https://arxiv.org/html/2504.20073v2)
- [lmgame-Bench, arXiv 2505.15146 (ICLR 2026)](https://arxiv.org/html/2505.15146v2)
- [ScaleRL, The Art of Scaling RL Compute for LLMs, arXiv 2510.13786 (ICLR 2026)](https://arxiv.org/pdf/2510.13786)
- [The Danger of Overthinking, arXiv 2502.08235](https://arxiv.org/pdf/2502.08235)
- [TRL GRPOTrainer documentation (v1.15)](https://huggingface.co/docs/trl/main/en/grpo_trainer)
- [Unsloth, Qwen3.5 fine-tuning guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
- [Unsloth, reinforcement learning guide](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide)
- [Artificial Analysis, Qwen3.5 small models (Mar 2026)](https://artificialanalysis.ai/articles/qwen3-5-small-models)
- [The Decoder, Gemma 4 under Apache-2.0 (Apr 2026)](https://the-decoder.com/googles-gemma-4-is-now-available-with-apache-2-0-licensing-for-the-first-time/)
- [Mistral, Mistral 3 announcement (2025-12-02)](https://mistral.ai/news/mistral-3)
- [Orak, arXiv 2506.03610v3 (HTML)](https://arxiv.org/html/2506.03610v3)
- [Modal model library, Qwen3.5-0.8B](https://modal.com/library/qwen/qwen3-5-0-8b)

### Frontier models with scaffolding, and API pricing

- [LessWrong, A Year Late, Claude Finally Beats Pokémon (2026-05-16)](https://www.lesswrong.com/posts/sehJYg5Yny9fvpbpt/a-year-late-claude-finally-beats-pokemon)
- [jcz.dev, Gemini 3 Pro vs 2.5 Pro in Pokémon Crystal](https://blog.jcz.dev/gemini-3-pro-vs-25-pro-in-pokemon-crystal)
- [kenforthewin, An LLM Beat NetHack (Sep 2026)](https://kenforthewin.github.io/blog/posts/llm-nethack-ascension/)
- [BalatroBench leaderboard data v1.0.8 (generated 2026-02-03)](https://balatrobench-prod.b-cdn.net/benchmarks/models/v1.0.8/default/leaderboard.json)
- [dbreunig.com, An agentic case study: playing Pokémon with Gemini (2025-06-17)](https://www.dbreunig.com/2025/06/17/an-agentic-case-study-playing-pokémon-with-gemini.html)
- [AgenticSTS, arXiv 2607.02255v1 (HTML)](https://arxiv.org/html/2607.02255v1)
- [AlasamAkkit/spirecomm, LLM self-reflection study](https://github.com/AlasamAkkit/spirecomm)
- [PokéChamp, arXiv 2503.04094 (ICML 2025)](https://arxiv.org/abs/2503.04094)
- [Orak, arXiv 2506.03610v1 (HTML; KRAFTON, Jun 2025)](https://arxiv.org/html/2506.03610v1)
- [Orak leaderboard (last updated 2025-06-09)](https://krafton-ai.github.io/orak-leaderboard/)
- [Xiao & Yang, LLMs May Not Be Human-Level Players, But They Can Be Testers, arXiv 2410.02829 (2024)](https://arxiv.org/abs/2410.02829)
- [hiKareeem/ClaudePlaysTheSpire, SpireBench trial-v0.1 (Apr–May 2026)](https://github.com/hiKareeem/ClaudePlaysTheSpire/blob/main/docs/benchmark/trial-v0-summary.md)
- [AgenticSTS, arXiv 2607.02255 (2026-07-02)](https://arxiv.org/abs/2607.02255)
- [GameGeeker, Slay the Spire 2 May 2026 Neow's Dispatch (secondary)](https://gamegeeker.com/fr/news/slay-the-spire-2-may-neows-news-update?market=FR)
- [Claude API pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing)

### Training services and GPU rental

- [Tinker documentation](https://tinker-docs.thinkingmachines.ai/)
- [Tinker models and pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/)
- [Beam blog, Tinker model pricing (Jul 2026)](https://www.beam.cloud/blog/tinker-model-pricing)
- [Fireworks, Training API generally available (2026-08-31)](https://fireworks.ai/blog/train-past-the-frontier-training-api-now-generally-available)
- [Fireworks docs, connecting environments (RFT deprecation notice)](https://docs.fireworks.ai/fine-tuning/connect-environments)
- [Fireworks pricing](https://fireworks.ai/pricing)
- [W&B Serverless RL usage limits](https://docs.wandb.ai/serverless-rl/usage-limits)
- [CoreWeave Forge post-training pricing](https://coreweave.com/forge-pricing/post-training)
- [Together AI pricing](https://www.together.ai/pricing)
- [Tessl, OpenAI shutting fine-tuning (2026-05-20)](https://tessl.io/blog/openai-shutting-fine-tuning-signals-for-enterprise-ai)
- [Prime Intellect Lab documentation](https://docs.primeintellect.ai/hosted-training/what-is-lab)
- [AWS blog, fine-tuning Claude 3 Haiku on Bedrock (end-of-life notice)](https://aws.amazon.com/jp/blogs/machine-learning/fine-tune-anthropics-claude-3-haiku-in-amazon-bedrock-to-boost-model-accuracy-and-quality/)
- [RunPod pricing](https://www.runpod.io/pricing)
- [Modal pricing](https://modal.com/pricing)
- [Lambda pricing](https://lambda.ai/pricing)
- [Hugging Face Jobs guide](https://huggingface.co/docs/huggingface_hub/guides/jobs)
- [NovaSky-AI/SkyRL](https://github.com/NovaSky-AI/SkyRL)
- [volcengine/verl](https://github.com/volcengine/verl)

### Distillation and terms of service

- [Thinking Machines, On-Policy Distillation (2025-10-27, updated Jun 2026)](https://thinkingmachines.ai/blog/on-policy-distillation/)
- [UrzaGPT, arXiv 2508.08382 (2025)](https://arxiv.org/abs/2508.08382)
- [Anthropic Commercial Terms](https://www.anthropic.com/legal/commercial-terms)
- [OpenAI Terms of Use (rest of world)](https://openai.com/en-GB/policies/row-terms-of-use/)
- [Gemini API Additional Terms](https://ai.google.dev/gemini-api/terms)
- [Simon Willison, DeepSeek R1 (2025-01-20)](https://simonwillison.net/2025/Jan/20/deepseek-r1)

### Autoresearch and program search

- [karpathy/autoresearch, README (Mar 2026)](https://github.com/karpathy/autoresearch)
- [karpathy/autoresearch, program.md](https://raw.githubusercontent.com/karpathy/autoresearch/master/program.md)
- [karpathy/nanochat, README (time-to-GPT-2 leaderboard)](https://cdn.jsdelivr.net/gh/karpathy/nanochat@master/README.md)
- [philschmid.de on autoresearch (secondary)](https://www.philschmid.de/autoresearch)
- [VentureBeat on autoresearch (secondary)](https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai)
- [How Much of a Harness Does a Strong Agent Need for Autonomous ML Engineering?, arXiv 2609.40303 (2026-09-30)](https://arxiv.org/html/2609.40303)
- [CryptoBriefing on the Apple harness study (2026-10-07; secondary)](https://cryptobriefing.com/apple-study-minimal-agent-beats-multi-agent/)
- [AIRA₂, arXiv 2603.26499 (v1 Mar 2026, v2 Apr 2026)](https://arxiv.org/abs/2603.26499)
- [Google DeepMind, AlphaEvolve (2025-05-14)](https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/)
- [Discovering Multiagent Learning Algorithms with Large Language Models, arXiv 2602.16928 (Feb 2026)](https://arxiv.org/abs/2602.16928)
- [Sakana AI, ShinkaEvolve (Sep 2025)](https://sakana.ai/shinka-evolve/)
- [OpenEvolve, README](https://github.com/algorithmicsuperintelligence/openevolve)
- [Sakana AI, ALE-Agent wins AtCoder Heuristic Contest 058 (Dec 2025)](https://sakana.ai/ahc058/)
- [Code World Models for General Game Playing, arXiv 2510.04542 (ICLR 2026)](https://arxiv.org/abs/2510.04542)
- [PromptPO, When are LLMs Sufficient Policy Optimizers for Sequential RL Tasks?, arXiv 2605.30719](https://arxiv.org/abs/2605.30719)
- [PokéAgent Challenge, arXiv 2603.15563 (NeurIPS 2025 competition)](https://arxiv.org/pdf/2603.15563)
- [Reward Hacking Challenges Oversight of Autonomous Research Agents, arXiv 2609.28614 (Sep 2026)](https://arxiv.org/abs/2609.28614)
- [Wikipedia, METR (secondary)](https://en.wikipedia.org/wiki/METR)
- [DemoEvolve, arXiv 2605.24539 (May 2026)](https://arxiv.org/abs/2605.24539)

### Multi-agent systems

- [Debate or Vote, arXiv 2508.17536 (NeurIPS 2025)](https://arxiv.org/pdf/2508.17536)
- [Rethinking Mixture-of-Agents (Self-MoA), arXiv 2502.00674](https://arxiv.org/pdf/2502.00674)
- [Multi-Agent Teams Hold Experts Back, arXiv 2602.01011 (ICML 2026)](https://arxiv.org/html/2602.01011v1)
- [Google Research, Towards a Science of Scaling Agent Systems (2026-01-28)](https://research.google/blog/towards-a-science-of-scaling-agent-systems-when-and-why-agent-systems-work/)
- [The Decoder, Gemini 2.5 Pro beats Pokémon Blue (2025)](https://the-decoder.com/googles-reasoning-llm-gemini-2-5-pro-beats-pokemon-blue-with-a-little-help/)
- [Anthropic Engineering, multi-agent research system (2025-06-13)](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Anthropic Engineering, building a C compiler with parallel Claude agents (2026-02-05)](https://www.anthropic.com/engineering/building-c-compiler)
- [Cursor, scaling long-running autonomous coding (2026-01-14)](https://cursor.com/blog/scaling-agents)
- [Claude Code documentation, costs](https://code.claude.com/docs/en/costs)
- [Claude Code documentation, agent teams](https://code.claude.com/docs/en/agent-teams)
- [MAST, Why Do Multi-Agent LLM Systems Fail?, arXiv 2503.13657 (NeurIPS 2025)](https://arxiv.org/html/2503.13657v3)
- [NVIDIA GEAR, ENPIRE project page (CoRL 2026)](https://research.nvidia.com/labs/gear/enpire/)
- [Cognition, multi-agent patterns that work (2026-04-22)](https://cognition.com/blog/multi-agents-working)

### Human run data and imitation

- [DraftFM, arXiv 2608.19568 (Aug 2026)](https://arxiv.org/abs/2608.19568)
- [Tuyls et al., scaling laws for imitation learning in NetHack, arXiv 2307.09423 (2023)](https://arxiv.org/abs/2307.09423)
- [Kumar, Hong, Singh & Levine, when offline RL beats BC, arXiv 2204.05618 (ICLR 2022)](https://arxiv.org/abs/2204.05618)
- [leomaurodesenv/game-datasets PR #39 (merged 2026-09-05)](https://github.com/leomaurodesenv/game-datasets/pull/39)
- [Fox Row, Slay the Spire statistical analysis (2020-12-14)](https://foxrow.com/slay-the-spire-statistical-analysis)
- [slaythespire.dev, datasets index](https://slaythespire.dev/datasets/)
- [MaT1g3R/Slay-the-Spire-data, sample .run file](https://raw.githubusercontent.com/MaT1g3R/Slay-the-Spire-data/master/runs/200-rotating-sample/DEFECT/1663714310.run)
- [Bazzaz & Cooper, Analysis of Uncertainty in Procedural Maps in Slay the Spire, arXiv 2504.03918 (2025)](https://arxiv.org/abs/2504.03918)
- [slaythespire.dev, projects index](https://slaythespire.dev/projects/)

### Hybrids

- [Sutton, Precup & Singh, the options framework (1999)](https://www.sciencedirect.com/science/article/pii/S0004370299000521)
- [Tom's Hardware, Jev decision engine beats Pokémon Red (2026-09-27)](https://www.tomshardware.com/tech-industry/artificial-intelligence/developer-says-jev-decision-model-beat-pokemon-red-in-under-a-week-non-llm-engine-succeeds-where-traditional-chatbots-stalled-for-months-but-claude-opus-5-coached-the-model-through-its-dead-ends)
- [Bruno Marcos, DEV post on a Slay the Spire 2 agent (2026-09-09)](https://dev.to/brmarcosbr/i-made-an-agent-play-slay-the-spire-2-on-its-own-and-what-unlocked-it-was-the-game-saying-no-2hc2)
- [LLM action recommendations as observations for RL, arXiv 2510.08779 (Oct 2025)](https://arxiv.org/html/2510.08779v1)
- [Behavior cloning then RL in Legends of Code and Magic, arXiv 2404.16689 (2024)](https://arxiv.org/abs/2404.16689v1)
- [wuhao21/sts2-cli, headless real StS2 engine](https://github.com/wuhao21/sts2-cli)

### Interpretability

- [Li et al., Othello-GPT world model, arXiv 2210.13382 (ICLR 2023)](https://arxiv.org/abs/2210.13382)
- [Nanda, Lee & Wattenberg, linear world model in Othello-GPT, arXiv 2309.00941 (2023)](https://arxiv.org/abs/2309.00941)
- [Karvonen, chess-GPT probes and skill vector, arXiv 2403.15498 (2024)](https://arxiv.org/abs/2403.15498)
- [Jenner et al., look-ahead in Leela Chess Zero, arXiv 2406.00877 (NeurIPS 2024)](https://arxiv.org/abs/2406.00877)
- [McGrath et al., concepts in AlphaZero, arXiv 2111.09259 (PNAS 2022)](https://arxiv.org/abs/2111.09259)
- [Schut et al., teaching AlphaZero's concepts to grandmasters, arXiv 2310.16410 (PNAS 2025)](https://arxiv.org/abs/2310.16410)
- [Bush et al., planning in a model-free Sokoban agent, arXiv 2504.01871 (ICLR 2025)](https://arxiv.org/abs/2504.01871)
- [Turner et al., understanding and controlling a maze-solving policy network (2023)](https://www.alignmentforum.org/posts/cAC4AXiNC5ig6jQnc/understanding-and-controlling-a-maze-solving-policy-network)
- [Sobotka et al., LLM game-state representations versus verbal reports, arXiv 2605.00226 (2026)](https://arxiv.org/abs/2605.00226)
- [Anthropic, open-sourcing circuit tracing (2025-05-29)](https://www.anthropic.com/research/open-source-circuit-tracing)
- [safety-research/circuit-tracer releases (logit-difference targets from v0.4.0, Feb 2026)](https://github.com/safety-research/circuit-tracer/releases)
- [mwhanna/qwen3-0.6b-transcoders-lowl0 (per-layer transcoders for Qwen3-0.6B)](https://huggingface.co/mwhanna/qwen3-0.6b-transcoders-lowl0)
- [Qwen-Scope, arXiv 2605.11887 (May 2026)](https://arxiv.org/abs/2605.11887)
- [Qwen-Scope SAE model card, Qwen3.5-2B-Base](https://huggingface.co/Qwen/SAE-Res-Qwen3.5-2B-Base-W32K-L0_50)
- [TransformerLens releases (v4.0, 2026-09-21)](https://github.com/TransformerLensOrg/TransformerLens/releases)
- [Gurnee et al., the Jacobian lens, arXiv 2607.15495 (Jul 2026)](https://arxiv.org/abs/2607.15495)
- [anthropics/jacobian-lens](https://github.com/anthropics/jacobian-lens)
- [Google DeepMind interpretability team, deprioritising SAE research (2025-03-26)](https://www.alignmentforum.org/posts/4uXCAJNuPKtKBsi28/)
- [AxBench, arXiv 2501.17148 (ICML 2025)](https://arxiv.org/abs/2501.17148)
- [Anthropic, On the Biology of a Large Language Model (2025-03-27)](https://transformer-circuits.pub/2025/attribution-graphs/biology.html)
- [Claude documentation, extended thinking](https://platform.claude.com/docs/en/build-with-claude/thinking)
- [Claude documentation, OpenAI SDK compatibility](https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk)
- [Google AI developer forum, Gemini 3.x logprobs (2026-08-05)](https://discuss.ai.google.dev/t/missing-logprobs-support-in-the-newest-gemini-models-3-1-pro-3-6-flash-on-vertex-ai-and-ai-studio/176557)
- [OpenAI documentation, Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model)
- [Claude documentation, refusals and fallback (`reasoning_extraction`)](https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback)
- [Turpin et al., unfaithful explanations in chain of thought, arXiv 2305.04388 (NeurIPS 2023)](https://arxiv.org/abs/2305.04388)
- [Anthropic, Reasoning models don't always say what they think (2025-04-03)](https://www.anthropic.com/research/reasoning-models-dont-say-think)
- [Duzan & Cooper Stickland, incidental nudges and CoT monitoring, arXiv 2608.04735 (Aug 2026)](https://arxiv.org/abs/2608.04735)
- [METR, CoT faithfulness when reasoning is required (Aug 2025)](https://www.alignmentforum.org/posts/WAxkA6gDgrschZovx)
- [Instability floors for LLM agent decisions, arXiv 2609.03221 (Sep 2026)](https://arxiv.org/abs/2609.03221)
- [Zheng et al., selection bias in multiple-choice answers, arXiv 2309.03882 (ICLR 2024)](https://arxiv.org/abs/2309.03882)
- [Atrey, Clary & Jensen, saliency maps in deep RL, arXiv 1912.05743 (ICLR 2020)](https://arxiv.org/abs/1912.05743)
- [Anderson et al., saliency and reward bars for non-experts (IJCAI 2019)](https://ijcai.org/proceedings/2019/184)
- [Olson et al., counterfactual states for explaining agents, arXiv 2101.12446 (2021)](https://arxiv.org/abs/2101.12446)
- [Hewitt & Liang, control tasks for probes, arXiv 1909.03368 (EMNLP 2019)](https://arxiv.org/abs/1909.03368)
- [Makelov et al., subspace activation-patching illusions, arXiv 2311.17030 (2023)](https://arxiv.org/abs/2311.17030)
- [Jain & Wallace, Attention is not Explanation, arXiv 1902.10186 (NAACL 2019)](https://arxiv.org/abs/1902.10186)
- [Minder et al., activation differences reveal narrow fine-tunes, arXiv 2510.13900 (ICLR 2026)](https://arxiv.org/abs/2510.13900)
- [Mukherjee et al., RL fine-tunes small subnetworks, arXiv 2505.11711 (NeurIPS 2025)](https://arxiv.org/abs/2505.11711)
- [Tracking RL drift with a fixed SAE, arXiv 2609.15064 (Sep 2026)](https://arxiv.org/abs/2609.15064)
- [Nanda, How to become a mechanistic interpretability researcher (2025-09-02)](https://www.alignmentforum.org/posts/jP9KDyMkchuv6tHwm/how-to-become-a-mechanistic-interpretability-researcher)
- [Anthropic Fellows Program 2026](https://alignment.anthropic.com/2025/anthropic-fellows-program-2026/)

### Robotics

- [Alshiekh et al., safe RL via shielding, arXiv 1708.08611 (AAAI 2018)](https://arxiv.org/abs/1708.08611)
- [ENPIRE, agentic robot policy self-improvement, arXiv 2606.19980 (CoRL 2026)](https://arxiv.org/abs/2606.19980)
- [NVlabs/ENPIRE (Apache-2.0)](https://github.com/NVlabs/ENPIRE)
- [ENPIRE auto-research contract for agents](https://raw.githubusercontent.com/NVlabs/ENPIRE/main/enpire/policy/autoresearch_instruction.md)
- [SimEX, simulation-integrated robotics autoresearch, arXiv 2609.38982 (2026-09-30)](https://arxiv.org/abs/2609.38982)
- [Liang et al., Code as Policies, arXiv 2209.07753 (2022)](https://arxiv.org/abs/2209.07753)
- [RHO, repositories as policies, arXiv 2606.16458 (Jun 2026)](https://arxiv.org/abs/2606.16458)
- [ASPIRE, agentic skill discovery for robotics, arXiv 2607.00272 (2026)](https://arxiv.org/abs/2607.00272)
- [CaP-X, arXiv 2603.22435 (ICML 2026)](https://arxiv.org/abs/2603.22435)
- [Code-as-Monitor, arXiv 2412.04455 (CVPR 2025)](https://arxiv.org/abs/2412.04455)
- [Gemini Robotics, arXiv 2503.20020 (Mar 2025)](https://arxiv.org/abs/2503.20020)
- [Physical Intelligence, π*0.6 and RECAP, arXiv 2511.14759 (Nov 2025)](https://arxiv.org/abs/2511.14759)
- [SimpleVLA-RL, arXiv 2509.09674 (ICLR 2026)](https://arxiv.org/abs/2509.09674)
- [Luo et al., HIL-SERL, arXiv 2410.21845 (2024)](https://arxiv.org/abs/2410.21845)
- [Zhou et al., AutoEval, arXiv 2503.24278 (CoRL 2025)](https://arxiv.org/abs/2503.24278)
- [Kress-Gazit et al., robot evaluation practice, arXiv 2409.09491 (2024)](https://arxiv.org/abs/2409.09491)
- [STEP, sequential policy comparison, arXiv 2503.10966 (RSS 2025)](https://arxiv.org/abs/2503.10966)
- [Li et al., SIMPLER, arXiv 2405.05941 (CoRL 2024)](https://arxiv.org/abs/2405.05941)
- [SureSim, arXiv 2510.04354 (Oct 2025)](https://arxiv.org/abs/2510.04354)
- [NVIDIA, Senior Research Engineer, Generalist Embodied Agent Research (posting via aggregator; closed)](https://jobs.anitab.org/companies/nvidia/jobs/68139470-senior-research-engineer-generalist-embodied-agent-research)
- [Amazon, Applied Scientist, Fauna (posting via aggregator, 2026-06-10)](https://scoutify.com/companies/amazon/jobs/1352280/)
- [Runway, Member of Technical Staff, Robotics Engineer (posting via aggregator, 2026-06-02)](https://jobs.madrona.com/companies/runway-3/jobs/81324241-member-of-technical-staff-robotics-engineer)

### Addendum, 2026-10-12

- [Continual Harness, arXiv 2605.09998v1 (HTML; May 2026)](https://arxiv.org/html/2605.09998v1)
- [sethkarten/continual-harness at commit bbab97a](https://github.com/sethkarten/continual-harness/tree/bbab97a)
- [Growing Harness, arXiv 2609.26760](https://arxiv.org/abs/2609.26760)
- [Meta-Harness, arXiv 2603.28052](https://arxiv.org/abs/2603.28052)
- [DemoEvolve, arXiv 2605.24539 (HTML)](https://arxiv.org/html/2605.24539)
- [ACE, Agentic Context Engineering, arXiv 2510.04618v2 (HTML)](https://arxiv.org/html/2510.04618v2)
- [Harness Updating Is Not Harness Benefit, arXiv 2605.30621](https://arxiv.org/abs/2605.30621)
- [SpireBench, arXiv 2610.12596 (HTML; 2026-10-08)](https://arxiv.org/html/2610.12596)
- [Prime Intellect docs, shared LoRA retired](https://docs.primeintellect.ai/hosted-training/shared-lora-retired)
- [PrimeIntellect-ai/prime, PR #984 (retirement warning)](https://github.com/PrimeIntellect-ai/prime/pull/984)
- [Prime Intellect docs, Hosted Training billing](https://docs.primeintellect.ai/hosted-training/billing)
- [PrimeIntellect-ai/prime-rl](https://github.com/PrimeIntellect-ai/prime-rl)
- [PrimeIntellect-ai/verifiers, overview](https://github.com/PrimeIntellect-ai/verifiers/blob/main/docs/overview.md)
- [OpenAI API deprecations (fine-tuning)](https://developers.openai.com/api/docs/deprecations)
- [Fireworks docs, reinforcement fine-tuning](https://fireworks.ai/docs/fine-tuning/reinforcement-fine-tuning-models)
- [Fireworks docs, Training API](https://docs.fireworks.ai/fine-tuning/training-api/introduction)
- [Baseten Loops, Tinker compatibility](https://docs.baseten.co/loops/tinker-compatibility)
- [CoreWeave Serverless RL usage limits](https://docs.coreweave.com/serverless-rl/usage-limits)
- [SpireBench, arXiv abstract page 2610.12596 (no code link, read 2026-10-12)](https://arxiv.org/abs/2610.12596)
- [krafton-ai/Orak (MIT)](https://github.com/krafton-ai/Orak)
- [Orak Slay the Spire config](https://github.com/krafton-ai/Orak/blob/main/src/mcp_agent_client/configs/slay_the_spire/config.yaml)
- [hiKareeem/ClaudePlaysTheSpire (MIT)](https://github.com/hiKareeem/ClaudePlaysTheSpire)
- [AlayaLab/AgenticSTS](https://github.com/AlayaLab/AgenticSTS)
- [xaved88/bottled_ai](https://github.com/xaved88/bottled_ai)

