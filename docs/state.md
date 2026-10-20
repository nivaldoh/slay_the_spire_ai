# Project state

Updated 2026-10-20: what runs, where each game stands, what comes next. Status only:
history goes to the logs ([WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md),
[first combat](spire/first-combat/README.md)), owner directions to
[owner-direction.md](owner-direction.md). Under the
[hard rule](../AGENTS.md#verification-hard-rule), only the listed agreed checks are
verified at their recorded revisions; the gameplay findings below remain unverified.

## Active work

Nothing is running. The WH3 [Empire set](twwarhammer3/empire.md) night of 2026-10-20
finished at 09:00: four queues, 45 launches, $8.84
([log](twwarhammer3/log.md#2026-10-20-the-empire-set-harness-b43)); its decisions and
risks wait for the owner ([list](twwarhammer3/empire.md#for-the-owner-to-decide)). A
review of the night corrected its pages and the LineTeam arms' target rules
([b46](twwarhammer3/log.md#2026-10-20-lineteam-kept-targets-and-a-reason-cap-harness-b46));
the revised arms are unplayed. The chariot b40 round stays stopped.

Priorities (owner, 2026-10-18): WH3 benchmark first, then Spire; post-training secondary.
[Traces must support RL](posttraining.md#beyond-supervised-fine-tuning).

## Total War: WARHAMMER III

[README](twwarhammer3/README.md), [log](twwarhammer3/log.md) ("On main" at the top),
[tactic cards](twwarhammer3/tactic-cards.md) (the benchmark definition and its board),
[latency program](twwarhammer3/latency.md) (plan), [results.csv](twwarhammer3/results.csv).

- On `main`: `llm`/`llm_rules` v21, `commander` v7, skills v1.2, harness b46,
  evaluator v2, track `obs-v4+terrain/act-v2/live-1x`. Definitions and earlier changes:
  [log](twwarhammer3/log.md#on-main).
- Benchmark: [the chariot card](twwarhammer3/tactic-cards.md#the-chariot-card-the-first-benchmark-card);
  results in the [b40 round](twwarhammer3/log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40).
  No model has won above its foils' bound (an unverified gameplay finding).
- Spend: OpenAI $51.47 of $52; WH3 OpenRouter ledger $21.33 ($8.84 the Empire night).

Next (proposals for the owner; stages in [latency.md](twwarhammer3/latency.md#staged-plan)):
0. Read the night's [results](twwarhammer3/empire.md#results) and its six
   [owner items](twwarhammer3/empire.md#for-the-owner-to-decide), from the rank-5 line
   battle as the first team card to the first Empire export (29 model episodes).
1. Freeze the chariot card once owner decision 2 below is taken.
2. Breadth over repetition (owner's question, 2026-10-19): the expendables card, then
   pin-then-rear, with the lean protocol only (foils at 10 launches each, one witness gate,
   one 10-launch model cell, no exploration cells); definitions first.
3. The rest of P5 when a night is free: Kimi K3 low on v21 (10 plans written, about $5),
   then high; a stronger model at modifier 1.1 is still untested (the OpenAI cap).
4. [Robot team research draft](twwarhammer3/robot-team-plan.md) (owner, 2026-10-20):
   can another unit take over when a teammate breaks? Next is reviewing whether the
   expendables battle can test this; experiments have not started. Controller ideas remain
   in the [robotics notes](twwarhammer3/robotics.md).

## Slay the Spire

[README](spire/fullrun/README.md), [log](spire/fullrun/log.md),
[results.csv](spire/fullrun/results.csv). v10 on `main`. No run has won; the furthest
reached Act 4 (v8, floor 54). Version differences sit within run-to-run variation (about
11 floors per run on one seed; replays of one harness differed by 13-26 floors), measured
only on the three tuning seeds, so harness progress is not shown. `HELDOUT01`-`HELDOUT10`
are reserved and unplayed. Spend: OpenAI $2.52 of $25, OpenRouter $0.25.

Next, after WH3: one decisive comparison (current scaffolding against an ablated one, 20-30
fresh seeds per arm, about $5 and three nights) or a freeze; `v11-keys` waits on it. Open
decisions: [fullrun README](spire/fullrun/README.md#open-owner-decisions); paused:
[first combat](spire/first-combat/README.md); planned: [open-weight](spire/open-weight/README.md).

## Post-training

[posttraining.md](posttraining.md): capture/export/dataset smoke passes, with no learning
claim. Missing: training host, fine-tune serving for both games and useful targets.

## Known issues

- Check OpenRouter credits before paid jobs: ledgers missed $2.69 by 2026-10-18.
- Pinned OpenRouter backend outages count against the model; Step 5 preview is unpinned.
- No test yet shows whether a game patch changes results (owner: later). A build warning
  shows in `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- OpenAI caps and the OpenRouter allowance shared by both games are kept by hand.
- WH3 register and `stats`: blank version on benchmark rows, grouping by commit, API
  failures as `policy_failure` (`twwarhammer3 card` classifies failures and keys by setup);
  a defender's timer stalemate counts as won (`stats` ignores `ended_by`; the card outcome
  and the Empire review script separate contact wins).
- No automated checks for report JavaScript or several Spire play-loop stop paths.
- Spire's Workshop mod pins still block a run when a mod updates.
- `runs/` has no off-machine copy: 23 GB, 6.9 GB without the `checkpoints/` directories
  (16 GB of them in the two SFT jobs; `du -sh --exclude=checkpoints runs/`, 2026-10-20).

## Owner decisions waiting

1. Where to back up `runs/`.
2. The chariot card: second-pass decisions 3-5 (1-2 ran in b40;
   [list](twwarhammer3/tactic-cards.md#second-pass-2026-10-19-evening-findings-and-the-version-2-decisions))
   and whether witness v2 replaces v1 in the rule (the v1 rule stays as the admitted
   pre-registered verdict; the proposals they replace are in git at `5c01b93`); the
   [latency program's](twwarhammer3/latency.md#owner-decisions) three left: `c1` as
   evidence, the scored route, the $20 stop.
3. A training host and a route to play a fine-tune; the teacher: OpenAI outputs (whether
   they may train a model; 25,503 rows excluded), GLM-5.3, or rejection-sampled Qwen3.6.
4. Whether Step 5 preview has open weights, and whether to request token log-probabilities,
   a sampler seed or explicit GLM/Kimi sampling before the next model screens
   ([gaps](posttraining.md#beyond-supervised-fine-tuning)).
5. `wh3-rules-v21-attack-path` (unmerged); whether to keep `commander` (unplayed since v4);
   more OpenAI budget (the $52 cap refuses Sol calls now).

## Runtime and ownership

- Slay the Spire ([runtime facts](spire/integration.md#runtime-and-source-pins)): the owner
  authorizes the installed Steam game and personal profile slot 0, including changes to
  stats, unlock progress, run history and achievements (Ironclad unlock level 3 of 5; runs
  record profile evidence).
- WH3 ([engine facts](twwarhammer3/integration.md)): a launch's mod list and startup-video
  skip persist for ordinary Steam launches ([how to reverse](twwarhammer3/README.md#commands)).
  Steam auto-update stays on.
- Also authorized: game windows, local GPU work, commits and pushes to public `main`, and
  paid API use within each ledger's cap. One game controller at a time across both games
  (each game's lock and process check cover only that game); one GPU job at a time.

## Branches

- `v11-keys` (`cd97667`): Spire v11 keys memory, on v10 (`54a5967`).
- `wh3-rules-v21-attack-path` (`5baf28b`): WH3 `llm_rules` attack-route draft, labelled
  v21 before main's v21 (`18dabdd`); renumber before any merge.
- Archived drafts are tags (`git tag --list 'archive/*'`).
