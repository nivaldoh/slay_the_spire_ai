# Project state

Updated 2026-10-11, during the authorized unattended bootstrap session.

## Active jobs (last verified 06:21 UTC)

Repaired trained evaluation session `61555` finished exit0. No game currently runs.
Next command, already preregistered in [research.md](research.md):

```bash
uv run --extra train python -m spire train --suite configs/suites/louse_diagnostic_development_v1.json --output runs/ppo-budget64-seed0-20261011 --episodes 64 --batch-steps 64 --updates 16 --time-budget 3000 --seed 0
```

The trial starts from the same seed-0 initialization with a new explicit budget;
it does not extend the completed pilot. Expected collection is roughly 34 minutes
at the measured 31.99 seconds/episode; hard limit 50 minutes. Evaluate the final
export on the same eight-attempt suite afterward. Do not edit tracked source,
configuration or dependencies while a live training/evaluation batch owns them.
An independent agent is implementing scenario catalogs in an isolated worktree;
no broader encounters are admitted until original-engine inventory/replays exist.

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
incomplete. The computational neural pilot is complete; no GPU job has run.

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
- RTX 3060 12 GB is available; WSL memory is 7.7 GiB. No GPU allocation yet.
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

1. Launch and monitor the predeclared larger trial; inspect actual process
   ownership and metrics before resuming or starting anything else.
2. Audit its stopped checkpoint with `scripts/audit_training.py`, then evaluate
   the exact final export on the unchanged suite. Report negative results honestly.
3. Choose a larger training budget from results, or fix any observed data-flow issue.
4. Investigate faster engine resets independently; adopting them requires a new
   versioned protocol and demonstrated replay equivalence. Do not alter this pilot.

Current limitations: starter cards only, no potion actions or noncombat policy,
Neow prefixes outside max HP/100 gold unsupported, no arbitrary snapshots, no live
combat resume, and no demonstrated gameplay improvement yet. Root checks at `637ae98`: 305 tests
passed, one optional Windows process probe skipped by default; that probe was
independently run and passed. Ruff is clean. Use `uv run --extra train pytest` for
learner coverage. Optional PyTorch 2.13.0 CPU is locked and installed; tiny-network
training is deliberately CPU because original-engine collection dominates runtime.
