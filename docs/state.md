# Project state

Updated 2026-10-12. Read this first: what is running, what is current, what comes next.
History lives with each track ([full runs](fullrun/log.md),
[first combat](first-combat/README.md)), not here.

## Active work (last verified 2026-10-12 16:13 UTC)

No game, GPU or API job is running. Source and `HEAD` are free.

## Current track: full runs with an API model

[fullrun/README.md](fullrun/README.md) is the reference and loop;
[fullrun/log.md](fullrun/log.md) is the version history.

The first overnight autoresearch session (2026-10-12, 02:28–11:04 local, UTC-3) played
scaffolding v2–v7 on `RUNDEV1`–`RUNDEV3` (v7 on `RUNDEV2` only). Best floors per seed:
29, 50 and 42 (v1.1 baseline: 16, 33, 16). No run has won yet. API spend: $1.68 of the
$25 cap (`uv run python -m spire spend`).

Next steps:

1. Replay all three seeds on v7. The 2026-10-12 reorganization moved code but did not
   change what the model sees, so any later commit plays v7.
2. Take the top candidate in [fullrun/README.md](fullrun/README.md#candidate-changes),
   skipped-reward memory.
3. Loop improvements from related work, on the same page: replay saved decisions offline,
   failure flags in `spire digest`, held-out seeds.

Open owner decisions: reasoning effort above `low`, and a whole turn per call.

## Owner direction

- 2026-10-12: run a frontier API model through complete runs, with scaffolding found by
  autoresearch from observed mistakes. `gpt-6-luna` at low reasoning effort, a hard $25 API
  cap for the first overnight work, and lean code.
- 2026-10-12: later, test a remotely trained open-weight model (Qwen3.6-35B-A3B, then
  GLM-5.3, with RL on Tinker). The plan is in [open-weight/README.md](open-weight/README.md);
  only a code skeleton exists, in `src/spire/openweight/`.
- 2026-10-11: PPO paused in favor of language-model post-training, which in turn paused
  with the move to full runs. Results and open threads:
  [first-combat/README.md](first-combat/README.md).

## Housekeeping

The repository was reorganized on 2026-10-12 into per-track packages, test directories,
docs and run folders; [AGENTS.md](../AGENTS.md) has the map. Evidence from 2026-10-11 moved
to `runs/first-combat/`, and the records inside keep their old absolute paths
([how to re-audit](first-combat/README.md#evidence-and-tools)).

Pending owner cleanup: 49 local branches whose commits are all in `main`, and 47 stale
`git worktree` records for deleted `/tmp` checkouts. Keep
`integration/heldout-clip-continuation`, which holds unmerged first-combat work.

## Runtime and ownership

- WSL2 Ubuntu 24.04 with uv 0.12.5 and a locked Python 3.13 environment. Windows Python
  3.13.1 and the game-bundled Java 1.8.0_144 run from WSL.
- Steam game build 10180494 (game version 12-18-2022). Pinned ModTheSpire 3.30.3, BaseMod
  5.56.0 and CommunicationMod 1.2.1, copied to `C:/spire-agent/mods`; hashes are in
  `spire/engine/runtime.py` and [integration.md](integration.md), and the Workshop copies
  are rechecked on every launch.
- The relay connects from Windows to the current WSL guest IPv4 on fixed port 19876.
  CommunicationMod's config is `%LOCALAPPDATA%/ModTheSpire/CommunicationMod/config.properties`.
- Every launch owns one JVM in a Windows job object, which stops it and the relay on
  controller EOF, deadline or supervisor death. A WSL lock and a Windows mutex prevent
  overlap, and pre-existing game processes cause a refusal.
- The directly launched JVM reports a Steam API initialization failure; gameplay works.
  `isModded=true` gates the engine's metric and crash uploads (see [integration.md](integration.md)).
- RTX 3060 12 GB; WSL memory 7.7 GiB. Windows AC sleep is disabled.

The owner authorizes the installed Steam game and personal profile slot 0, including
changes to stats, unlock progress, run history and achievements (Ironclad unlock level was
3 of 5 on 2026-10-11; runs record profile evidence). Also authorized: game windows, local
GPU work, commits and pushes to public `main`, and paid OpenAI API use within the declared
cap. One game runner and one GPU training job at a time.
