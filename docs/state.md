# Project state

Updated 2026-10-11, during the authorized unattended bootstrap session.

## Active work (last verified 07:56 UTC)

No game or GPU job is active. The two direct-address original-engine controls
completed at source `f0736a7`; session `42973` exited successfully. Both won at HP77
in 39.17/38.91 seconds, with all commands and public transitions matching the existing
heuristic reference exactly. Output: `runs/direct-relay-control-20261011`; see
[control audit](results/direct-relay-control-20261011.json). Both deployed
`172.18.34.183:19876`. This satisfies the declared gate for the separate frozen
SFT evaluation rerun; it does not establish the original failure's exact cause.

The previous trained evaluation session `4043` exited with code 1: two wins at
HP77, then a relay-startup infrastructure failure with zero observations/actions,
leaving five attempts unrun. The two wins exactly match the teacher's commands and
public transitions; all three traces audit correctly, but the suite is incomplete.
Preserved output: `runs/qwen3-0.6b-sft-eval-20261011`, source `a828645`; see
[incomplete result](results/language-sft-incomplete-development-v1.json). The failed
Linux accept timed out; Windows relay stderr reports WinError10054. Do not count
this as a gameplay loss or a completed eight-attempt comparison.

Direct WSL guest-address transport is integrated after 40 bounded
socket probes succeeded (loopback/direct NAT, disposable/fixed 19876 ports). The exact
intermittent localhost failure was not reproduced; direct routing is a mitigation,
not a proven causal diagnosis. Five additional exchanges using the real relay script
passed, as did 106 focused integrated tests (one optional Windows test skipped),
Ruff and independent review. Before any model evaluation rerun, the
[declared recovery sequence](language-experiment.md) requires two exact heuristic
control fights under a 300-second batch ceiling. Only if they pass, evaluate the same
final adapter in `runs/qwen3-0.6b-sft-eval-v2-20261011`, eight attempts/1,600 seconds,
preserving the first batch and all operational costs. No prompt/parser/weights change.

Real-data SFT finished all 64 updates, 527,360 charged/committed padded tokens and
256 example occurrences in 398.46 seconds, with no pending reservation or resume.
Session `52953`, worker `320214` and watchdog `320211` exited successfully before
the original 07:42:31 UTC deadline. Peak allocated/reserved CUDA memory was
5,541.22/5,814 MiB; peak total GPU use was 7,087 MiB and minimum available WSL RAM
3,522.97 MiB. Root's CPU preflight independently verified canonical checkpoint
accounting/finite tensors, source pins, dataset re-export, exact adapter tensor/config
serialization, declaration and supervisor bounds. Evidence:
`runs/qwen3-0.6b-heuristic-sft-20261011-preflight-audit.json`. Adapter tensor SHA-256:
`bf708e4a541167f2808c40989fc595d2c9a6114e441c5de66752097b063f32ac`;
declaration SHA-256 `70d19d51a5578ca3ce4e64e0f3f8646c9034ab6e14cf9f84baa2002268a248d6`.
The independent full ancestry audit passed all 12 checks, including 129 immutable
checkpoints and 2,293,759 changed adapter elements. Its auditor and catalog evidence
docs are integrated at `4a7e4f4`; 27 focused integrated audit tests passed and Ruff is
clean. See [compact training audit](results/language-sft-training-audit.json).
No gameplay result or CUDA resume-equivalence claim follows from training alone.

The unchanged-model baseline exited successfully and passed independent trace/metric
audit: all eight scheduled attempts ended on the same malformed string-valued index
`{"a": "1"}` after three legal actions. There were zero wins/completed games, eight
policy failures, and zero infrastructure failures or invalid commands. HP and win rate
over completed games are undefined; wins per policy attempt is 0/8. Greedy repeats of
this fixed scenario are correlated. All 24 acknowledged prefix transitions remain
evidence but are excluded from whole-episode training data. See
[baseline result](results/language-untuned-development-v1.json) and raw evidence in
`runs/qwen3-0.6b-untuned-eval-20261011`. No repair or retry was used.

Inventory PID 313645/session 86612 exited successfully: 18 attempts in 576.17 seconds,
with Cultist `SPIREINV07` and Jaw Worm `SPIREINV09` admitted after exact replays.
Both end-turn probes lost; both control fights matched the reference. Every child
hash and original trace audit was independently rechecked. No infrastructure failure
or retry occurred. Four discovery fights had excluded 88-HP starts and six were
unsupported. All evidence remains in `runs/starter-inventory-20261011`.

Integrated CPU checks: 620 passed, 7 skipped (six optional language-library cases plus
Windows cleanup). All 89 combined optional language checks passed on CPU using the
CUDA environment. The added/existing original-engine mechanics checks also passed
73/73. Actual-tokenizer preflight verified all 42 SFT rows: 644–723 prompt tokens,
5 JSON tokens plus 1 EOS per target, masks exact, sequences within 2060. Evidence:
`runs/qwen3-0.6b-sft-tokenization-20261011.json`, SHA-256
`48144de4ec81a611a26073d94646e768b847fe67cd4ff4f28991e0c1535c74d1`.
Further source work uses an isolated worktree for language catalog evaluation.
A read-only PPO gradient diagnosis supports the newly declared tenfold-learning-rate
test, to run only after the existing four-policy encounter comparison. See
[research contract](research.md) for the optional clock-gated seed-1 paired replication.

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
including frozen development evaluation; policy improvement is unproven. D–F remain
incomplete. The computational neural pilot is complete; GPU smoke checks are also complete, without a language-gameplay claim.

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
- Loopback Windows-to-WSL TCP forwarding works. CommunicationMod config is at
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
No new paid services or APIs. One game runner and one GPU training job at a time.
The user requested autonomous work until 10:00 tomorrow; session start was 2026-10-11
02:12 America/Sao_Paulo. Experiments use explicit shorter bounds rather than relying on
that natural-language deadline.

## Next useful actions

1. Controls passed. Start the exact final adapter in the separate declared v2 batch,
   with eight canonical attempts and the 1,600-second process ceiling.
2. Monitor its process/session to terminal;
   audit and report both batches before making a controlled-comparison claim.
3. Run random/heuristic/initial-neural/final-neural catalog comparisons under the
   [declared development contract](research.md), with 12 attempts and 1,200 seconds per
   policy. Catalog: `configs/suites/starter_three_encounter_development_v1.json`.
4. Use measured behavior to choose a single controlled PPO intervention, then repeat
   training initializations and separately define later held-out evaluation.

Current limitations: starter cards only, no potion actions or noncombat policy,
Neow prefixes outside max HP/100 gold unsupported, no arbitrary snapshots, no live
combat resume, and no demonstrated gameplay improvement yet. Integrated checks: 620 CPU tests passed, with six optional language-library cases and
the Windows process probe skipped. The combined optional language cases passed separately
on CPU with the CUDA environment; the Windows probe passed earlier. Ruff is clean. Use `uv run --extra train pytest` for
learner coverage. Optional PyTorch 2.13.0 CPU is locked and installed; tiny-network
training is deliberately CPU because original-engine collection dominates runtime.
