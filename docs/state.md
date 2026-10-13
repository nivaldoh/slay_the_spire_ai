# Project state

Updated 2026-10-12. Read this first: what is running, what is current, what comes next.
History lives with each track ([full runs](fullrun/log.md),
[first combat](first-combat/README.md)), not here.

## Active work (last verified 2026-10-12 23:16 UTC)

No game, GPU or API job is running. Source and `HEAD` are free.

## Current track: full runs with an API model

[fullrun/README.md](fullrun/README.md) is the reference and loop;
[fullrun/log.md](fullrun/log.md) is the version history.

The first overnight autoresearch session (2026-10-12, 02:28–11:04 local, UTC-3) played
scaffolding v2–v7 on `RUNDEV1`–`RUNDEV3` (v7 on `RUNDEV2` only). Best floors per seed:
29, 50 and 42 (v1.1 baseline: 16, 33, 16). No run has won yet. API spend: $1.68 of the
$25 cap (`uv run python -m spire spend`).

A second session (2026-10-12, 15:40–20:16 local) replayed v7 on all three seeds (floors
16, 33 and 16, against 29, 50 and 42 for the same prompts' earlier runs: run-to-run
variance is that large), played v8, skipped-reward memory (50, 54 and 16; RUNDEV2 reached
Act 4, the furthest yet, and the reopen loop nearly stopped), and started v9, card keywords
(RUNDEV1 29; RUNDEV2 stopped on floor 38 when an accidental Escape press opened the game's
settings screen; RUNDEV3 not played). API spend: $2.49 of the $25 cap.

Next steps:

1. Replay v9 on all three seeds; it is untested on Ethereal cards so far.
2. v10, hand-select purpose, is commit `cb4c90d` on local branch `v10-hand-select`, rebased
   onto `main`: a line naming the card, potion or Gambling Chip behind each hand selection.
   Replaying the saved traces, it adds that line to all 385 hand-select prompts (226 Gambling
   Chip, 113 cards, 46 potions) and changes no other prompt.
3. Keys memory: CommunicationMod 1.2.1 never sends `keys`, so the model cannot see the
   keys it holds; v9 RUNDEV1 died on an elite path taken for a key it had
   ([integration.md](integration.md), [candidates](fullrun/README.md#candidate-changes)).
4. A results table across versions (owner request): the register is built.
   `spire play` appends each run to the committed `docs/fullrun/results.csv` (backfilled
   for v1–v9), and `spire stats` prints acts reached, wins and floors per version. Still
   to add: SpireBench's other measures, before more versions are compared
   ([fullrun/README.md](fullrun/README.md#ideas-from-related-work-2026-10-12)). SpireBench
   released no code; its metric definitions and fixed held-out seeds carry over.
5. Optional runner fix: close the settings screen (opened by an Escape press on the game
   window) with a logged key press instead of stopping the run.
6. An open StS1 full-run benchmark, built from this harness: owner interest, scoped in the
   [approaches.md addendum](approaches.md#addendum-2026-10-12-evening-an-open-sts1-benchmark).
   Its first step is the same results table as item 4.

Open owner decisions: [fullrun/README.md](fullrun/README.md#open-owner-decisions).

## Owner direction

- 2026-10-12: interest in turning this harness into an open-source StS1 benchmark, since
  SpireBench's code is not public (checked 2026-10-12); see the approaches.md addendum.
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

2026-10-12 (late): game-neutral code moved to `src/gameai/` (OpenAI calls and spend,
ledgers, scoped provenance) so other games can reuse it, and the full-run loop and engine
were simplified. Replaying all 30 saved full-run traces gave byte-identical prompts,
request bodies and ledger charges; a 40-action smoke run passed (API spend now $2.50).
`docs/agent-guide.md` was removed (in Git history).

The repository was reorganized on 2026-10-12 into per-track packages, test directories,
docs and run folders; [AGENTS.md](../AGENTS.md) has the map. Evidence from 2026-10-11 moved
to `runs/first-combat/`, and the records inside keep their old absolute paths
([how to re-audit](first-combat/README.md#evidence-and-tools)).

Pending owner cleanup: 49 local branches whose commits are all in `main`, and 47 stale
`git worktree` records for deleted `/tmp` checkouts. Keep
`integration/heldout-clip-continuation`, which holds unmerged first-combat work.

## Runtime and ownership

Host, engine, mod and process facts: [integration.md](integration.md#runtime-and-source-pins).

The owner authorizes the installed Steam game and personal profile slot 0, including
changes to stats, unlock progress, run history and achievements (Ironclad unlock level was
3 of 5 on 2026-10-11; runs record profile evidence). Also authorized: game windows, local
GPU work, commits and pushes to public `main`, and paid OpenAI API use within the declared
cap. One game runner and one GPU training job at a time.
