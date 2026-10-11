# Project state

Updated 2026-10-11, during the authorized unattended bootstrap session.

## Active jobs (last verified 05:37 UTC)

One sequential baseline job is live in tool session `58891`, WSL shell PID `283480`.
The random evaluator Python PID was `283524`; inspect current ownership with
`pgrep -af 'python3 -m spire evaluate'` before sending signals. It runs random 8 episodes
then heuristic 8 episodes, on the frozen development suite. Each episode has a 180-second
hard Windows watchdog and a 500-action cap. Stop the current Python controller with
`kill -INT <verified PID>`; it records interruption and closes its owned Windows job.
The second evaluator is queued in the same shell, so stopping the first with a nonzero
exit prevents the second from launching.

Evidence directories: `runs/baseline-random-settled-20261011` and
`runs/baseline-heuristic-settled-20261011`. Last inspection: two random wins (HP75/66),
third attempt live. Re-poll the actual tool session/process; do not restart based on
an old manifest alone. **Do not change source/configuration/dependency files or merge
code while this batch is live**: source fingerprints intentionally stop a changed run.
Documentation edits are safe.

Parallel implementation lives in isolated worktrees. Learner commit `976cc23` on
`feature/learning` is ready to cherry-pick after baseline completion; it provides a
12,498-parameter CPU network and PPO with 22 passing correctness tests. Training
orchestration is still being implemented on `feature/training` in `/tmp/spire-training`.
These are unmerged and no weight training against the engine is claimed.

## Current evidence

Milestone A is verified: recorded wins and losses, automatic seeded restarts,
matching fixed-action replays, independent trace audits, and process-tree cleanup.
Milestone B baseline evaluation is running. Milestones B–F remain incomplete; no
neural training or GPU job has run.

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

1. Poll the live baseline session `58891` and audit both completed evaluations. This
   establishes matched baseline numbers for Milestone B's fixed-encounter diagnostic.
2. Cherry-pick learner `976cc23` only after collection completes; integrate and test
   training orchestration when its agent returns. Keep complete episode batches tied
   to one frozen behavior policy. Add frozen-artifact evaluation support.
3. Run a bounded first neural pilot, verify actual actor updates, save optimizer/RNG/
   budget state, test resume, and evaluate the exact saved artifact against baselines.
4. Expand beyond one encounter only after this learning loop is verified. Current
   development repetitions are one fixed scenario, not held-out seed generalization.

Current limitations: starter cards only, no potion actions or noncombat policy,
Neow prefixes outside max HP/100 gold unsupported, no arbitrary snapshots, no live
combat resume, and no engine-trained policy yet. Root tests: 173 pass, one optional
Windows process probe skipped by default; that probe was independently run and passed.
Use `uv run --extra train pytest` when testing learner code. The same locked environment
has optional PyTorch 2.13.0 CPU installed; baseline collection needs only the core stdlib.
