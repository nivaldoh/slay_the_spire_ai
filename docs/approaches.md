# Approaches to an AI that plays Slay the Spire

*Research snapshot dated 2026-10-11, synthesized from six research notes compiled that day (the
notes stay outside Git, under `runs/research_notes/`). "Estimate" marks a number a researcher
computed from stated assumptions rather than one a source reported. "Self-reported" marks a
result its authors published and nobody has reproduced. Prices are list prices read on
2026-10-11. Project facts come from [state.md](state.md) and [research.md](research.md).*

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
deciding constraint is **engine time, not GPU or money**: the original engine yields roughly
1,400–2,900 combats a day on its single controller (estimate), while the RL successes worth
copying used from about 15,000 simulated runs to hundreds of millions of games. That argues for four moves in order: tighten the evaluation
(held-out and harder scenarios, HP-based paired comparisons); improve the local language policy
with the changes that have direct evidence (MLP-inclusive LoRA, turn-level credit, a 2–4B
Qwen3.5 base); add a frontier model as a measured baseline and offline teacher; and, if the goal
becomes the full game, validate a fast simulator against the project's audited traces before
training on it. Paid services buy bigger models, not more samples. The project's distinctive
asset is its honest-information, audited, real-engine evaluator: the notes found no
peer-reviewed Slay the Spire paper with real-engine RL results and no published RL-trained LLM
for the game.

## Comparison of paths

| Path | What it is | Frontier example (date) | Slay the Spire prior work | What this project would need | Rough cost / time (estimates unless noted) | Main risk |
|---|---|---|---|---|---|---|
| 1. Pure RL and search | Policy/value nets trained on environment reward; MCTS or Gumbel search over a simulator; world models | Ataraxos, superhuman Stratego for under $8k on 16 H100s for a week (2025–26); Generals.io, #1 on a human ladder after 4×H200 × 4 days (Jun 2026) | heart1 82.5% A0 wins in simulator; sts-ironclad-agent 50.1% A20 Heart (self-reported); six failed attempts to distill MCTS combat into a network | Python binding to an sts_lightspeed fork, parity check against audited traces, HP or run-value reward, entity-based masked policy | ~$0 on the local GPU; real-engine RL beyond one fight is infeasible (a 50k-step single-fight budget is ~15–40 h of engine time) | Simulator fidelity unquantified; RNG-aware teachers leak hidden information |
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
([scenario-expansion.md](scenario-expansion.md)). Policies see only public, allowlisted fields,
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
([language-rl-experiment.md](language-rl-experiment.md)).

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
cards, claims "1M random playouts in 5s with 16 threads", and describes itself as "Designed to
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
(computed here from the measured figures; one research note calls even this budget out of reach).
Full-game RL is not reachable. The learned non-combat layer that gained 11 floors needed 15k
simulated games ([Jialeiv model card](https://huggingface.co/Jialeiv/sts-rl-agent)); at about 27
combats per run (estimate) that is roughly 400k combats, or about 140–290 days of engine time.

The path therefore runs through a simulator, in a fixed order. The first job is a Python binding
to a maintained sts_lightspeed fork; pybind11 bindings exist upstream but are undocumented, and
Jialeiv's patches add legal-action listing and pause hooks. The second is **parity before
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
[language-rl-experiment.md](language-rl-experiment.md) itself warns that a gain "may be a
memorized line", so a held-out set is required. Turn-level credit is cheap to add, with per-turn
HP lost as reward and GiGPO-style anchor-state grouping, because the catalog restarts fixed seeds
and early states repeat exactly across a group. Adapters should be selected by outcome, not
agreement: the heuristic-relabel adapter raised held-out agreement to 75.2% but cut macro HP from
76.33 to 63.67 ([language-relabel-experiment.md](language-relabel-experiment.md)). And with 7.7
GiB of WSL RAM, plain HF generation is safer than colocating vLLM (untested). Engine time is the
budget: one 12-combat iteration costs about 6–12 minutes, 1,000 combats take 8.3–16.7 hours
(estimate), and GiGPO-scale episode counts would take weeks.

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
public, honest-information frontier win rate exists for full StS1 runs.

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
| Prime Intellect Lab | Does not fit (environment runs on their side) | Shared LoRA training stopped accepting new runs on 2026-10-08; dedicated runs are in closed beta ([Prime Intellect docs](https://docs.primeintellect.ai/hosted-training/what-is-lab)) |
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
game controller remains the bottleneck. Moving to Tinker also means changing the base model,
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
form of OPD ([language-relabel-experiment.md](language-relabel-experiment.md)). The teacher must
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
combats, or about 12.6 hours, while AlphaEvolve-scale searches with thousands of candidates are
infeasible without a simulator (all estimates). The project's infrastructure already supplies the
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
published for a run of this size. With a fast simulator the calculation flips, and one agent per
simulator instance, population-based training and exploiter-style scenario search become real
parallel speedups.

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

The ordering follows from the constraints above: engine time is scarce, the language track is
current, and money is now available but mainly buys model size.

**First, make the evaluator worth optimizing against** (no cash, little engine time). Add
encounters where random play loses and the heuristic does not saturate, declare a held-out
scenario set that no training or selection loop sees, and score on paired seeds with HP-based
metrics and confidence intervals. Everything later depends on this; the 2026 autoresearch
literature attributes most false progress to evaluation noise, and the relabel result already
showed agreement and outcome diverging.

**Second, spend the next language-track runs on the changes with direct evidence** (local, $0):
MLP-inclusive LoRA, a Qwen3.5-2B or 4B base with thinking disabled, turn-level HP rewards with
anchor-state grouping, and training only on scenarios that carry gradient. Report each change
against the frozen 76.33 SFT adapter; the unevaluated two-update REINFORCE adapter is the natural
first evaluation ([state.md](state.md)).

**Third, measure a frontier model on the same catalog** (tens of dollars). Run one cheap and one
flagship model as policies under the existing `Decision` boundary, logging dollars and seconds per
fight and invalid outputs. If either beats the heuristic, relabel saved states through a batch API
(about $175 per 10,000 decisions on Sonnet 5.5, estimate) and distill; if neither does, the
heuristic remains the better teacher, which is itself a reportable result.

**Fourth, run an autoresearch loop on the heuristic, gated by the held-out catalog** (overnight).
Edits are confined to the policy module, every candidate is committed before it runs, kept or
reset, and re-audited offline. About 100 candidates fit in a night, and no comparable experiment
is published for the game.

**Fifth, decide on the full game, and if the answer is yes, start with simulator parity, not
training.** Bind an sts_lightspeed fork, replay audited traces, publish a divergence rate, and only
then follow the section 1 recipe (behavior cloning from the heuristic, masked PPO, determinized
search) with the real engine as final judge. Non-combat decisions could start with a frontier LLM,
at the hybrid costs in section 3, and later move to a card-pick model trained on human or
simulator runs.

**Sixth, use paid remote training only when model size is the hypothesis**, for example on-policy
distillation from Qwen3.5-9B on Tinker at an estimated $29–80 per 1,000 combats, with the loop
written against the Tinker-style API so it can move between local, rented and hosted GPUs.

**Seventh, treat a multi-agent builder setup as an experiment, not a default**, and if it is
tried, run and report the single-agent-versus-team ablation on a fixed engine budget.

On the evidence above, this guide would not pursue world models, equilibrium solvers, gameplay
debate or mixed-model ensembles, RNG-reading teachers, or distillation from a frontier teacher
that has not first been measured as a policy. OpenAI fine-tuning is not an option for a new
account in any case.

## Conclusion

The research shifts the question from which algorithm to which resource. Algorithms have
converged: generic policy gradient, low-rank LoRA, group baselines and determinized search all
work. What separates the 2026 successes is cheap, trustworthy evaluation, whether a fast simulator
for RL, an automatic verifier for program search or a near-perfect oracle for an agent swarm. This
project has the opposite profile, with evaluation that is slow, serialized and expensive but
unusually trustworthy: original engine, public information only, audited traces. That makes
sample efficiency and evaluation design the project's real research problems, and they are the
parts of the field the notes found least covered for Slay the Spire.

The second lesson is that who sees what decides which results count. Several headline numbers come
from searches that read RNG or future draws, and a student trained on such a teacher learns labels
it cannot reproduce. An honest-information pipeline, running from a public-state policy through a
determinized search teacher to a real-engine audit, would be a credible contribution even at
first-floor scale, and it is what would make any later full-game result comparable to the human
reference points of 9% across all StS1 runs in 2020 and 16% at StS2 A0.

## Sources

All links below are cited in this guide and appear in the research notes. They are grouped by the
section where each is first cited.

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
