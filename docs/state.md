# Project state

Updated 2026-10-12. The full-run API language-model track is current; see
[llm-play.md](llm-play.md).

## Active work (last verified 2026-10-12 11:17 UTC)

Overnight autoresearch session in progress (owner: stop around 11:00 local, UTC-3).
Job `runs/llm-luna-v6-dev-20261012` (scaffolding v6, source `e26f649`) is playing
`RUNDEV1`–`RUNDEV3` with `gpt-6-luna` at low effort; check
`ps -eo pid,cmd | grep '[p]ython3 -m spire play'` before launching anything. While it
runs, `src/`, `scripts/` and `configs/` must stay unchanged: the runner compares their
fingerprints before every seed. Docs may change. Floors so far: v1.1 16/33/16, v2
16/24/33, v3 16/33/16, v4 16/33/41 (first Act 3), v5 29/23/16 (first RUNDEV1 Slime Boss
win); see the log in [llm-play.md](llm-play.md). API spend: $1.17 of the $25 cap in
`runs/llm-spend.jsonl`.

Owner direction (2026-10-12): run a frontier API model through complete runs, with
the scaffolding found by autoresearch from observed mistakes. Full runs, `gpt-6-luna`
at low reasoning effort, hard $25 API cap for the first overnight work. Keep the code
lean.

Earlier entries below describe the first-combat tracks, unchanged since 2026-10-11.

Owner direction (2026-10-11 afternoon): pause the pure-RL/PPO route and advance LLM
post-training. The declared PPO learning-rate launchers stay unrun; the seed-1 clock
gate has expired, so that pair would need a new declaration before any run.

The declared four-policy catalog comparison completed at source `01f2984` with all
48 slots, zero infrastructure failures and valid independent audits for every policy:

| Policy | Wins | Macro HP | Louses | Cultist | Jaw Worm |
| --- | ---: | ---: | --- | --- | --- |
| Heuristic | 12/12 | 76.00 | 4/4, HP77 | 4/4, HP71 | 4/4, HP80 |
| Random | 10/12 | 42.00 | 4/4, HP70.25 | 3/4, HP36.75 | 3/4, HP19 |
| Initial neural | 8/12 | 37.25 | 4/4, HP61.5 | 2/4, HP24.75 | 2/4, HP25.5 |
| Budget-64 neural | 9/12 | 35.67 | 4/4, HP60.25 | 2/4, HP21 | 3/4, HP25.75 |

The Louse-trained PPO policy shows no transfer improvement over its own initialization
and stays below random on HP. See [comparison](results/starter-three-encounter-development-v1.json).

The adopted [language catalog comparison](language-catalog-experiment.md) completed at
`7314779` (24/24 slots, valid audits, no infrastructure failures). Unchanged Qwen3-0.6B:
0/12, all invalid completions. Louse-only SFT LoRA: 12/12 wins, macro HP 76.33 (Louses
77, Cultist 74, Jaw Worm 78) against the heuristic's 76.00 (77/71/80). On the two
training-unseen families the adapter matches only 36 of 50 heuristic decisions along its
own trajectories, so outcomes transfer more than the decision rule. See
[result](results/language-catalog-development-v1.json) and research.md.

The [heuristic-relabel experiment](language-relabel-experiment.md) is complete: 234
audited updates on 1,868 relabeled Louse states. Held-out greedy agreement rose to 75.2%
of unique prompts (Louse-only adapter 72.1%, unchanged base 32.9%), but catalog macro HP
fell to 63.67 (Louses 77, Cultist 41, Jaw Worm 73; still 12/12 wins). The declared rule
adopted it on agreement and wins; HP was not part of the rule. See research.md and
[result](results/language-relabel-development-v1.json).

The first [outcome-based post-training](language-rl-experiment.md) job completed one
REINFORCE iteration (12 sampled combats, audited update), then stopped on a transient
Windows interop timeout before iteration 1. Its one-update adapter improved greedy
catalog macro HP from 63.67 to 66.67 (Cultist 41 → 50; it now finishes a 3-HP Cultist
instead of blocking), 12/12 wins: the contract's improvement rule is met on trained
development scenarios. See research.md and [result](results/language-rl-development-v1.json).

The declared continuation `runs/language-rl-relabel-continued-20261011` (4 iterations,
seed 1, fresh AdamW) was stopped by owner request after its first iteration. That
iteration completed and saved: Louses 77×4 (no signal), Cultist 61/73/50/55, Jaw Worm
68/73/73/65 sampled HP; behavior recomputation within 1.3e-6; KL 0.048. The interrupt
landed during iteration 1's pre-game probe, so that slot is empty and no game launched.
`audit_language_rl` is valid. Its two-update adapter
(`iteration-000/policy.json`, SHA-256
`7870257b67607b5d7f5de319d4c6819d037dfd4cf56b20b8dd03ae65bf6ef84c`) has **not** been evaluated.
The best evaluated language artifact is still the Louse-only SFT adapter (macro 76.33); the
REINFORCE result is a +3.00 improvement over its own relabeled base, not over that adapter.

The frozen SFT v2 evaluation completed at source
`e829c1c`; tool session `71199` exited successfully and PIDs `337234`/`337233` are gone.
It won all eight canonical fights at HP77, with 168 audited transitions and no policy,
context, command or infrastructure failures. Every command and public transition
exactly matches the public heuristic. Independent CPU audit reconstructed all 168
prompts and completions and verified dataset, declarations, adapter/checkpoint files,
base-model files and historical source hashes. The recorded full-model tensor hash
was not independently recomputed by loading another model.

The controlled unchanged-model baseline had zero completed games and eight policy
failures; the final LoRA completed eight wins. Decision: keep for this same-scenario
imitation diagnostic. Training used 42 rows / 21 unique public prompts, directly
reusing this scenario; eight greedy repeats are correlated, and there is no held-out
or compute-matched PPO claim. See [controlled result](results/language-sft-development-v1.json)
and [experiment contract](language-experiment.md). Mean measured inference/total time
was 8.266/46.595 seconds per fight on the shared workstation.

The first trained batch remains separately preserved: two wins at HP77, one relay
startup failure with zero observations/actions, and five unattempted slots. Its
trace evidence is valid but its suite is incomplete. Across both trained batches,
11 attempts produced 10 wins and one infrastructure failure; those operational
totals do not replace the complete eight-attempt score. See
[incomplete result](results/language-sft-incomplete-development-v1.json).

Direct WSL guest-address transport passed 40 socket exchanges, five actual-relay
probes and two declared original-engine heuristic controls. Both controls won at
HP77 and exactly reproduced all 21 commands and transitions, satisfying the gate for
the separate SFT rerun. The intermittent localhost failure was not reproduced;
direct routing is a mitigation, not a proven diagnosis. Runtime queries the current
WSL address per launch; these controls used `172.18.34.183:19876`. See
[control audit](results/direct-relay-control-20261011.json) and
[transport evidence](relay-startup-mitigation.md).

Real-data SFT completed 64 updates, 527,360 charged/committed padded tokens and 256
example occurrences in 398.46 seconds, with no pending reservation or resume.
Peak allocated/reserved CUDA memory was 5,541.22/5,814 MiB, peak total GPU use
7,087 MiB, and minimum available WSL RAM 3,522.97 MiB. The independent training audit
passed all 12 checks, covering 129 immutable checkpoints, data lineage and budgets,
finite optimizer/parameter tensors, exact serialization and 2,293,759 changed adapter
elements. CUDA resume equivalence remains unproven. See
[training audit](results/language-sft-training-audit.json).
Final declaration SHA-256:
`70d19d51a5578ca3ce4e64e0f3f8646c9034ab6e14cf9f84baa2002268a248d6`.

The three-scenario catalog is admitted from original-engine inventory and repeat
traces. The declared next comparison is random, heuristic, initial neural and final
budget-64 neural: 12 attempts / 1,200 seconds per policy, 48 reserved attempts total.
Those catalog scores are complete (table above).

Language catalog evaluation is integrated at `2d3afb1`, with one frozen model owner
across scheduled children, independent saved-trace auditing and explicit partial
failure accounting. Combined-tree validation passed 703 CPU tests (20 optional or
local-evidence skips) and all 139 optional language checks on CPU in the CUDA
environment; Ruff and independent review passed. No live language catalog score
has been collected. The previously verified 73 original-engine mechanics checks
cover byte-unchanged mechanics/protocol fixtures.

The read-only PPO gradient diagnosis and declared tenfold-learning-rate experiment
are ready. Run that intervention only after the four-policy encounter comparison;
see [research contract](research.md) for the clock-gated seed-1 paired replication.
No higher-learning-rate game has been run.

The larger trial at source `7b4cc31` completed all 64 combats (64 wins), 12 updates,
and 827 consumed transitions in 2,298.47 seconds. No transitions remain pending.
All 30 applicable training-audit checks pass; all 3,201 actor elements changed.
Its final artifact is
`runs/ppo-budget64-seed0-20261011/artifacts/policy-0012-03ca30dc29154b968686a918efb0d4579d99c3142461ee2507a33138b18bbd22.json`.
Frozen evaluation completed 8/8 wins, HP [80,66,76,78,71,53,80,72], mean 72.0.
The exact same initial model scored 72.75, and the heuristic scored 77. The budget-only
change is rejected as an improvement on this diagnostic. Six paired action sequences
were identical; two differed, with one six-HP regression and one unchanged outcome.
These are eight sampling seeds on one game scenario, not independent encounters.
A read-only comparison on all 100 initial-evaluation public states found mean probability
mass displacement 0.02188, maximum individual probability change 0.03008, and mean final
entropy 0.99903 of the uniform maximum. The policy remains nearly uniform despite its
weight changes. The [distribution diagnostic](results/ppo-budget64-distribution-diagnostic.json)
is explanatory development evidence, not another independent gameplay evaluation.
See [comparison](results/ppo-budget64-development-v1.json),
[paired traces](results/ppo-budget64-paired-evaluation.json), and
[training audit](results/ppo-budget64-training-audit.json).

The three-scenario catalog now pins the existing Louses plus both inventory admissions.
Its declared comparison uses random, heuristic, initial neural and final budget-64
neural policies, with four sampling seeds per scenario. Actual catalog policy scores
have not been collected. Successful and failed language completions have explicit
provenance checks; real-data SFT has passed independent review.

Qwen3-0.6B at revision `c1899de289a04d12100db370d81485cdf75e47ca` passed a synthetic
LoRA smoke in 7.83 seconds at `699f641`. Peak reserved CUDA memory was 3,414 MiB; minimum
available RAM 3,457.5 MiB. Weights/logits changed and adapter serialization matched.
Its one-example loss 0.50518→0.02792 is computational evidence only. A later single
recorded public-state inference at `3fc7aaf` verified actual PEFT reload, 715 prompt tokens,
six generated tokens, strict JSON parsing and exact candidate identity in 0.699 seconds.
Both smoke workers exited; the unchanged-model evaluation and completed real-data
SFT are described above.
Prepared source-verified data: `runs/heuristic-language-training-data-20261011`, with
42 training rows, 21 unique examples and no validation/test rows. Manifest SHA-256:
`d4ce9b1c1d94109eb6acfaacf9217d79d6ebc85b2aa4ea3e326b45231ead5a71`.
The source predates formal suite labels; the experiment explicitly treats reuse of its
scenario as diagnostic development. Untuned declaration (adapter absent):
`runs/qwen3-0.6b-untuned-declaration-v2-20261011.json`, SHA-256
`b689e0d880f11b6ffee787a2c627b4d4da33ef2f7f190a9882df4302628af0b6`.
The loader now rejects partially restored PEFT adapters. Real-data SFT passed independent
review and is integrated. Its prepared config is
`runs/qwen3-0.6b-heuristic-sft-config-20261011.json` (64 updates, 600,000 padded tokens,
600 seconds, 4 examples/update, 2,060 sequence tokens, learning rate 0.0002).
The mechanics fixture is integrated: 16 exact public transitions, including both deaths,
with 73 new/existing engine regression checks passing. The superseded unexecuted
untuned declaration is retained; v2 pins the contract that explicitly adds a 1,600-second
evaluation batch deadline. No baseline result was observed before that clarification.
Evidence is preserved in `runs/language-smoke-20261011-0649` and
`runs/language-inference-20261011-0705`, with originals in `/tmp/spire-language-smoke`.
Base weights are cached under `/home/niv/.cache/spire-models`; about 2.2 GiB was downloaded
for model/packages, without paid services. Main `.venv` remains CPU; CUDA is isolated.

The accepted pilot used 8 attempts (7 completed and 1 intentional interruption),
2 PPO updates, and 92 audited transitions. All 3,201 actor parameters changed, and
all 32 reusable verifier checks pass. Its fixed-port frozen evaluation now completed
8/8 wins with mean HP72.75, exactly equal to the initial policy. Every one of 100
paired commands and public transitions matched. This verifies the learning loop;
it provides no gameplay improvement. The heuristic remains best at mean HP77.
See [comparison](results/ppo-pilot-development-v1.json),
[paired traces](results/ppo-pilot-paired-evaluation.json), and
[training audit](results/ppo-pilot-training-audit.json).

The first trained evaluation remains invalid after 5 games plus 1 startup failure.
Its random port 53899 was inside Windows' excluded range 53849–53948. Fixed
loopback 19876 passed 50 socket round trips and now 8 full game episodes. Each episode
records its deployed address and appended relay stderr. No reconnection or hidden
gameplay retry was added. All earlier artifacts are preserved; see
[failure audit](results/relay-startup-failure-audit.json).

## Current evidence

Milestone A is verified: recorded wins and losses, automatic seeded restarts,
matching fixed-action replays, independent trace audits, and process-tree cleanup.
Milestone B is verified for the narrow fixed-encounter diagnostic: declared start
state, engine mechanics fixtures, repeated resets, measured throughput, and matched
baselines. Milestone C is verified as a computational learning loop on this fixed diagnostic,
including frozen development evaluation; neural PPO improvement is unproven.
Milestone E is verified narrowly: identified public data, actual LoRA updates, an
unchanged-model baseline and a controlled same-scenario imitation result. D and F
remain incomplete; no held-out generalization or Act 1 performance is claimed.

`runs/first-random-v2-20261011/manifest.json` records source `deba4b7`, the configuration,
environment, and two random-policy episodes on `SPIREAI1`, Ironclad, Ascension 0.
Both fought two Louses at floor 1, won, and issued no rejected actions. Starting HP was
80; ending HP was 70 and 76 (includes Burning Blood healing). Both normalized combat
start hashes are `976a1cde16a54125d6b8466f0d562a8150e4f5811f8cf2e6146ae9cf157ed48b`.
Reset/startup took 13.24 and 13.20 seconds; combat plus process cleanup took 17.48 and
11.18 seconds. These are infrastructure smoke results, not a policy benchmark.

Reproduction (a new output directory is required):

```bash
uv sync --locked
uv run python -m spire doctor
uv run python -m spire rollout --policy random --episodes 2 --output runs/random-reproduction
uv run pytest
uv run ruff check .
```

Each episode owns a fresh Windows JVM, issues seeded `START`, chooses max HP at Neow
if offered or the exact 100-gold option otherwise, and chooses the leftmost first-floor
map node. It stops at an engine-confirmed combat outcome. There is no arbitrary combat
snapshot reset. Profile history affects Neow options, so actual prefix and initial
combat state are evidence, not assumptions.

Settled observation contract: initial engine `DEBUG` intents are resolved with a logged
`WAIT 60` before policy inference. The frozen suite pins normalized start SHA-256
`177b2fcdc80ed0e9efb7d2a01191a40df6e40d4123867d09e091fa122edc12c4`.
Two heuristic replays under this contract won at HP77 in 6 turns, with every observed
public transition matching. An end-turn-only diagnostic then lost twice at HP0 in
8 turns; the same seeded start still reproduced after defeat. Unlock progress was
observed unchanged at 817 in this probe (do not assume all future runs preserve it).

Compact committed audits: [bootstrap](results/bootstrap-audit.json) and
[loss/restart](results/loss-restart-audit.json). Mechanics fixtures cover 11 observed
starter-card/Louse transitions, with trace hashes and [coverage limits](mechanics.md).

## Canonical baseline results

Both frozen evaluations completed without invalid actions or infrastructure failures.
Random: 8/8 wins, terminal HP [75, 66, 50, 69, 71, 60, 73, 80], mean68, 115 audited
transitions, 270.58 total episode-seconds (33.82 seconds/episode). Heuristic: 8/8 wins,
HP77 throughout, 168 transitions, 306.35 seconds (38.29 seconds/episode). Mean JVM
reset/start time was 14.56 seconds for random and 14.34 for heuristic. Timing includes
process cleanup. These repeat one scenario; stochastic sampling varies but no unseen
encounter or game-seed performance is claimed. See [comparison](results/baselines-development-v1.json).

## Completed attempts

- `runs/bootstrap-probe/`: Windows launch, relay handshake, main-menu observation,
  seeded start, and Neow screen verified. No combat attempted.
- `runs/first-random-20261011/`: preserved unsupported attempt. Neow offered four
  choices without max HP. The runner stopped before combat. Added an exact 100-gold
  fallback and a regression; did not count this attempt as a gameplay loss.
- `runs/first-random-v2-20261011/`: two completed combat attempts described above.
- `runs/heuristic-replay-20261011/`: two deterministic replays; all 13 public decisions
  and 18 commands identical, HP80. Initial intents still DEBUG; not a settled baseline.
- `runs/intent-probe/`: diagnosed initial DEBUG intent; WAIT60 resolves it, second wait
  leaves state unchanged. Probe source and observations preserved locally.
- `runs/heuristic-settled-20261011/`: two matching corrected replays, HP77, 6 turns.
- `runs/loss-restart-probe-20261011/`: two verified deaths and identical subsequent start.
- `runs/baseline-random-settled-20261011/`: eight canonical random attempts, audit valid.
- `runs/baseline-heuristic-settled-20261011/`: eight canonical heuristic attempts, audit valid.

Raw trajectories and game logs are local ignored artifacts. Selected compact audit
results will be published in `docs/`; proprietary jars, saves, and assets stay out of Git.

## Runtime and ownership

- WSL2 Ubuntu 24.04; uv 0.12.5, locked Python 3.13 environment.
- Windows Python 3.13.1 and game-bundled Java 1.8.0_144 run from WSL.
- Steam game build 10180494 / game version 12-18-2022.
- Pinned ModTheSpire 3.30.3, BaseMod 5.56.0, CommunicationMod 1.2.1 at
  `C:/spire-agent/mods`; local game mods are verified copies. Hashes are in code and
  each deployment record. Workshop copies are rechecked on every launch.
- Game transport connects Windows to the current WSL guest IPv4 address. CommunicationMod config is at
  `%LOCALAPPDATA%/ModTheSpire/CommunicationMod/config.properties`.
- RTX 3060 12 GB is available; WSL memory is 7.7 GiB. Measured GPU smoke jobs have exited.
- Steam is running, but the directly launched JVM reports Steam API initialization
  failure. Gameplay works; Steam integration is not claimed.
- Runtime `isModded=true` and local engine inspection confirm metrics/crash-upload
  suppression. The owner's Upload Data setting remains unchanged. See
  [integration audit](integration.md).
- Windows AC sleep timeout is zero (disabled), verified with `powercfg`.

All rollout processes have episode and action limits. A Windows Job Object stops the owned
JVM and relay descendants on controller EOF, deadline, or supervisor death. A WSL lock
and Windows mutex prevent overlap, and pre-existing game processes cause a refusal.
Forced child/grandchild cleanup was tested with disposable Windows processes. No game process from a
completed attempt is intentionally left running.

## Owner decisions and boundaries

The guide authorizes the installed Steam game and personal profile slot 0, including
changes to stats, unlock progress, run history, and achievements. Initial Ironclad unlock
level is 3 of 5. The starter combat slice is insensitive to reward-pool unlock changes;
new runs record profile evidence and each new episode snapshots unlocks.

The owner authorizes game windows, local GPU work, commits, and pushes to public `main`.
Paid API use is authorized for the OpenAI key the owner set up (2026-10-12), within
the declared spend cap. One game runner and one GPU training job at a time.
The user requested autonomous work until 10:00 tomorrow; session start was 2026-10-11
02:12 America/Sao_Paulo. Experiments use explicit shorter bounds rather than relying on
that natural-language deadline.

## Next useful actions

0. Full-run LLM track (current): run the overnight autoresearch loop in
   [llm-play.md](llm-play.md), starting with scaffolding v2 on `RUNDEV1`–`RUNDEV3`. Review
   traces with `scripts/play_digest.py`, fix the most damaging recurring mistake with one
   scaffolding change, commit, and rerun the same seeds.
1. Evaluate the stopped continuation's two-update adapter once on the catalog with the
   frozen greedy evaluator; compare with the base (63.67) and the one-update adapter (66.67).
2. Decide the language track's next question (owner review pending): more outcome-based
   iterations, RL from the stronger Louse-only adapter, or new held-out scenarios so
   post-training gains are not measured on the seeds used for training.
3. PPO learning-rate work is paused by owner direction; re-declare before resuming.
4. Declare held-out evaluation and the smallest supported noncombat expansion before
   collecting their results.

Current limitations: starter cards only, no potion actions or noncombat policy,
Neow prefixes outside max HP/100 gold unsupported, no arbitrary snapshots, no live
combat resume, and no demonstrated neural PPO improvement. Use
`uv run --extra train pytest` for learner coverage. Optional PyTorch 2.13.0 CPU is
locked and installed; tiny-network training uses CPU because original-engine
collection dominates runtime. CUDA dependencies remain isolated in their locked
mutually exclusive extra.

The language comparison report identifies its original and rerun contracts by
historical Git revision and content hash (committed after the catalog queue ended).

Isolated completed source work, awaiting a safe integration window:
- `1625e722e80e3ca62de195c66a7fe35ea331b5b2`: PPO clipping-frequency diagnostic.
  89 focused tests passed. An 81-transition saved original-engine replay exactly
  preserved model/Adam/RNG and every historical metric; only the new diagnostic
  was added. Proof: `runs/ppo-clip-diagnostic-equivalence-20261011/proof.json`.
- `f6a3c3e`: held-out evaluation purpose propagation and training/resume/export/
  saved-training-audit rejection. 234 focused checks passed, Ruff clean, independent
  review passed. The completed random development catalog re-audits identically.
  This adds an operational boundary; no held-out suite or score is established.
- Two-combat continuation passed independent review at `d446e85`; existing
  first-combat files are unchanged. No second-combat game has been run. A separate
  bounded five-attempt engineering gate is being prepared, including a deliberate
  interruption after claiming gold and before entering the second fight.
The three source changes are combined in `/tmp/spire-combined-integration` at
`940d69844fdbffb67326aac9dacead8b4a23fc47`, based on current main. All 764 CPU
tests passed (eight optional skips), including actual saved mechanics evidence;
Ruff is clean. Fast-forward only after the current game queue releases ownership.
Prepared, reviewed, unexecuted launchers: `runs/run_ppo_high_lr_seed0.py` (whole-job
4,350-second cap) and `runs/run_ppo_seed1_pair.py` (clock gate and whole-block
10,500-second cap). Do not run either until the current catalog queue completes
and its evidence is valid. Seed-1 clock gate is before 10:05 UTC, independent of
seed-0 scores, to reserve 175 minutes before the conservative 13:00 UTC boundary.
