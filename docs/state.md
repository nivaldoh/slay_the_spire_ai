# Project state

Updated 2026-10-19: what runs, where each game stands, what comes next. Status only:
history goes to the logs ([WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md),
[first combat](spire/first-combat/README.md)), owner directions to
[owner-direction.md](owner-direction.md). Under the
[hard rule](../AGENTS.md#verification-hard-rule), only the listed component checks are
verified at their recorded revisions; the gameplay findings below remain unverified.

## Active work

Nothing is running. The bounded maintenance pass is complete
([log](twwarhammer3/log.md#2026-10-19-harness-b37-mailbox-and-order-boundaries)); no game/API jobs.

## Priorities (owner, 2026-10-18)

1. The WH3 benchmark.
2. Slay the Spire, after WH3.
3. Post-training is secondary, and not only SFT: RL and other methods will be tried, so
   traces must suit them ([what they keep](posttraining.md#beyond-supervised-fine-tuning)).

## Total War: WARHAMMER III

[README](twwarhammer3/README.md), [log](twwarhammer3/log.md) ("On main" at the top),
[tactic cards](twwarhammer3/tactic-cards.md) (the benchmark definition and its board),
[latency program](twwarhammer3/latency.md) (plan), [results.csv](twwarhammer3/results.csv).

- On `main`: `llm`/`llm_rules` v20, `commander` v7, skills v1.2, harness b37 (mailbox
  identity and finite order fields; b36 pinned OpenRouter backends; b35 controller forfeits),
  evaluator v2, track `obs-v4+terrain/act-v2/live-1x`.
- Benchmark: [the chariot card](twwarhammer3/tactic-cards.md#the-chariot-card-the-first-benchmark-card)
  (one chariot against two Swordsmen units at AI modifier 1.1; tactic: cycle charging;
  witness `SnapHitAndRun`; signature: cycles; rule pre-registered at `5396182`). Round
  `c1`: foils lost 10 of 10 each, the witness won 4 of 5 at 5 s: admitted under
  that rule (no check agreed). The witness tolerates 2-3 s at model pace, not 5 s; GLM-5.3 low
  won 1 of 10 while stating the tactic in all 10, Qwen3.6 none 0 of 5. All unverified.
- Spend: OpenAI $51.47 of $52. OpenRouter: the account had $50.38 of credit (owner,
  2026-10-18 evening; spend carefully), shared with Spire; the WH3 ledger holds $10.66
  after P5a ($1.78, 2026-10-19).

Next (proposals for the owner; stages in [latency.md](twwarhammer3/latency.md#staged-plan)):
1. An execution study (no game): what GLM-5.3 low's 9 losses do differently from the witness
   at the same pace (pull-out depth, refusals and contact length do not separate them); it
   decides what a harness or a specialist trained on the witness should change.
2. The rest of P5: Kimi K3 low and high, 10 launches each ($6-12).
3. [Card version 2](twwarhammer3/tactic-cards.md#card-version-2-draft-2026-10-18-evening-not-agreed)
   (drafted: start classes, three more foils, cycles v2, launch counting) with its admission
   rule proposed as an AGENTS.md check; then the expendables card the same way.
4. The army as detachable robot parts (owner, kept open): the
   [robotics framing](twwarhammer3/latency.md#robotics-framing) and harness rungs 3-5, sized
   by P2's reaction window.

## Slay the Spire

[README](spire/fullrun/README.md), [log](spire/fullrun/log.md),
[results.csv](spire/fullrun/results.csv). v10 on `main`; the relay now waits as long as a
model thinks. No run has won; the furthest reached Act 4 (v8, floor 54). Version
differences sit within run-to-run variation (about 11 floors per run on one seed; replays
of one harness differed by 13-26 floors), measured only on the three tuning seeds, so
harness progress is not shown. `HELDOUT01`-`HELDOUT10` are reserved and unplayed. Spend:
OpenAI $2.52 of $25, OpenRouter $0.25.

Next, after WH3: one decisive comparison (current scaffolding against an ablated one, 20-30
fresh seeds per arm, about $5 and three nights) or a freeze; `v11-keys` waits on it. Jobs
after the 2026-10-18 runner change are labelled v10.1 (16,000-token cap), so they do not
pool with v10. Open decisions: [fullrun README](spire/fullrun/README.md#open-owner-decisions);
paused: [first combat](spire/first-combat/README.md); planned:
[open-weight](spire/open-weight/README.md).

## Post-training

[posttraining.md](posttraining.md): capture, exports, dataset builder and a local smoke
test work end to end. The smoke numbers are not learning: the 0.6B stand-in's "5 of 16
action matches" equals always choosing 0. Missing: a training host, a route to play a
fine-tune in both games, and a way to choose targets (winning targets are scarce).

## Known issues

- OpenRouter: the ledgers missed $2.69 of account use by 2026-10-18 and the key's $50 limit
  is only a cap, so check `/api/v1/credits` before paid jobs.
- OpenRouter backends are pinned with no fallback since b36 (Step 5 preview is not), so a
  pinned backend's outage fails every call of that model, which b35 scores against it.
- No test yet shows whether a game patch changes results (owner: later). A build warning
  shows in `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- Only WH3's $50 OpenRouter ceiling per ledger is in code; the OpenAI caps and the
  OpenRouter allowance shared by both games' ledgers are kept by hand.
- WH3 register and `stats`: blank version on benchmark rows, grouping by commit, API
  failures as `policy_failure` (`twwarhammer3 card` classifies failures and keys by setup).
- Not in the automated tests: the battle Lua's order application; the report JavaScript
  (a manual browser check only); several Spire play-loop
  stop paths (source change, interruption).
- Spire's Workshop mod pins still block a run when a mod updates.
- `runs/` (22 GB) has no off-machine copy; its core evidence (traces, manifests, results,
  ledgers, replays) was about 2.6 GB, 90 MB with zstd, on 2026-10-17.

## Owner decisions waiting

1. Where to back up `runs/`.
2. The chariot card's rule (foils lose 10 of 10, witness wins 4 of 5 at 5 s with a cycle,
   the model-pace witness reported, not a gate; decided under delegation, against E2's own
   rule; moot if card version 2 is chosen), and the
   [latency program's](twwarhammer3/latency.md#owner-decisions) three left: `c1` as evidence,
   the scored route, the $20 stop (the scoring rule merged as b35).
3. A training host and a route to play a fine-tune; the teacher: OpenAI outputs (whether
   they may train a model; 25,503 rows excluded), GLM-5.3, or rejection-sampled Qwen3.6.
4. Whether Step 5 preview has open weights, and whether to request token log-probabilities
   or a sampler seed before the next model screens
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
- `wh3-rules-v21-attack-path` (`5baf28b`): WH3 `llm_rules` v21 draft.
- Archived drafts are tags: `archive/wh3-fire-report`, `archive/wh3-v4-info`,
  `archive/wh3-openrouter-pin` and `archive/heldout-clip-continuation`.
