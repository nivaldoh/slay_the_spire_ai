# Project state

Updated 2026-10-13. Read this first: what is running, what is current, what comes next.
History lives with each track ([full runs](fullrun/log.md),
[first combat](first-combat/README.md)), not here.

## Active work (last verified 2026-10-13 20:45 UTC)

WH3 controllers (owner request, 2026-10-13). From a ChatGPT 6 Astra Pro research
summary, the simplest design is now built:
- `--policy skills`: persistent per-unit skills run by a scripted executor on every
  observation.
- `--policy commander`: an API model setting those skills asynchronously, so units keep
  acting while it thinks.

The other designs are catalogued for later in
[twwarhammer3/controllers.md](twwarhammer3/controllers.md). Code: `d2bf74a`, `0f8eb39`
(fixes from the first smoke and a six-agent review) and `5a2fc8d`.

Smoke battles on `kho5-dwf5`, one each: the commander won with Luna ($0.02), Sol
(`gpt-6.1-sol`, $0.18) and Astra ($1.17). The pre-fix skills executor lost. Order delay
is 0.3 s, against 4-11 s for the direct controller. Think time at low effort: Luna
6.4 s, Sol 5.8 s, Astra 4.8 s.

`--scenario random` (owner request) draws a map and both races, leaves the faction to
the game, and autogenerates both armies (about 13 units a side). The seed is drawn per
job unless `--seed` is given. The first draw (Dark Elves vs Nurgle) was won by the Luna
commander. Every battle so far ran at AI difficulty very hard. Army
abilities (Khorne's kill unlocks) are missing from the interface: a gap to fix.

Next:
1. The six-episode comparison of `llm`, `skills` and `commander`.
2. Army abilities and ability readiness.

WH3 interface work completed: no extra wait by default; explicit attack modes, queued
moves/attacks, formation width, supported behavior toggles and self/unit/ground abilities.
The model also sees the added controls' state and its Winds of Magic. Code `6db8111`,
71 WH3 tests and Ruff pass. Original-engine probes plus a short Luna run are in
`runs/twwarhammer3/capability-probes/`; every following LLM decision had 0 ms extra
battle-time gap. Spell cooldowns remain unknown and are labelled that way. All probes
are stopped; no game/controller is running. See the WH3 track log's v13 entry.

WH3 mirror battles (owner away 11:25-16:25 UTC): `gpt-6-luna` against the game AI with
the same army on both sides (Khorne, Dwarf, Empire), and prompt versions v8-v11 chosen
by the review workflow. Last job: `runs/twwarhammer3/battle/llm-luna-v10-kho-pinned-20261013` (stopped at the
owner's return). That experiment and the subsequent capability probes are stopped.
The Spire v10 job (`runs/fullrun/llm-luna-v10-dev-20261013`) died on floor 10 when WSL
restarted at 04:36 UTC; Spire autoresearch is idle (v10 untested).

## Second game: Total War: WARHAMMER III (started 2026-10-13)

[twwarhammer3/README.md](twwarhammer3/README.md) is the track page, status, findings and
next steps; [twwarhammer3/integration.md](twwarhammer3/integration.md) the verified engine
facts; [twwarhammer3/log.md](twwarhammer3/log.md) the versions. A job launches the game,
sets up the `--scenario` battle from `configs/twwarhammer3/scenarios.json` (race picked in
the selector's popup, units recruited by double-click), plays episodes in real time and
restarts through the rematch button, with no desktop input. On Khorne vs Dwarfs
`attack_nearest` wins 3 of 3 and v6 won 5 of 6. In mirror battles Luna has not won with
guns on both sides (Empire 0 of 11+, Dwarfs 0 of 11) and won 3 of 18 Khorne mirrors (2 of 6 for v6, none for v10); the
AI's stats modifier preference is 1.1. `main` now runs the v13 controller with v10
tactical rules (v11 and v12 tactics reverted). Until `61c5f7f` the
game picked each side's faction within the race, so earlier mirror results mix factions. API spend about $0.7 of its own $25 ledger.

Next: evaluate the v13 interface with pinned factions (earlier runs had a 5 s extra wait),
then the fire-report candidate (branch `wh3-fire-report`) and
an owner decision on the AI stats modifier for mirrors. Branch `wh3-v4-info` holds an
older unmerged state candidate.

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
   Chip, 112 cards, 47 potions) and changes no other prompt.
3. Keys memory (drafted as v11 on branch `v11-keys`, unmerged): CommunicationMod 1.2.1 never sends `keys`, so the model cannot see the
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

- 2026-10-13: WH3 battles always run unpaused at 1x, including diagnostic probes; no
  pausing or slowing the simulation while the policy thinks.
- 2026-10-13: a WH3 battle track driven by the same API model; real-time with the order
  delay measured; control through an in-game mod, not screenshots or desktop input;
  paused after the first probes for a review of how to proceed.
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

Pending owner cleanup: 49 local branches whose commits are all in `main`. Keep
`integration/heldout-clip-continuation`, which holds unmerged first-combat work, and
`v11-keys` (`cd97667`, "Remember the keys taken and show them in the state header"), the
Spire session's unmerged v11 draft. The stale `git worktree` records for deleted `/tmp`
checkouts were pruned on 2026-10-13 (`git worktree prune`; no branch was touched).

## Runtime and ownership

Host, engine, mod and process facts: [integration.md](integration.md#runtime-and-source-pins).

The owner authorizes the installed Steam game and personal profile slot 0, including
changes to stats, unlock progress, run history and achievements (Ironclad unlock level was
3 of 5 on 2026-10-11; runs record profile evidence). Also authorized: game windows, local
GPU work, commits and pushes to public `main`, and paid OpenAI API use within the declared
cap. One game runner and one GPU training job at a time.
