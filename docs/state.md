# Project state

Updated 2026-10-18: what runs, where each game stands, what comes next. Status only:
history goes to the logs ([WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md),
[first combat](spire/first-combat/README.md)), owner directions to
[owner-direction.md](owner-direction.md). Under the
[hard rule](../AGENTS.md#verification-hard-rule) only the missing-ledger refusal is
verified so far; everything below is unverified.

## Active work

Nothing is running. The WH3 overnight tactic-card checks (2026-10-18, owner away until
13:00 UTC, delegated) ended at 12:49 UTC; plans are in `runs/twwarhammer3/calibration/n1`
to `n8`.

## Priorities (owner, 2026-10-18)

1. The WH3 benchmark.
2. Slay the Spire, after WH3.
3. Post-training is secondary, and not only SFT: RL and other methods will be tried, so
   traces must suit them ([what they keep](posttraining.md#beyond-supervised-fine-tuning)).

## Total War: WARHAMMER III

[README](twwarhammer3/README.md), [log](twwarhammer3/log.md) ("On main" at the top),
[tactic cards](twwarhammer3/tactic-cards.md) (the benchmark definition and its board),
[results.csv](twwarhammer3/results.csv).

- On `main`: `llm`/`llm_rules` v20, `commander` v7, skills v1.2, harness b31 (tactic-card
  scenarios and diagnostics), evaluator v2, track `obs-v4+terrain/act-v2/live-1x`.
- Benchmark definition (owner, 2026-10-18): minimal battles each won only by applying one
  tactic (cards), with foils that must lose, a witness that must win at 5 s age, a
  signature, rules parity and a held-out variant; draft, no check agreed.
- Night of 2026-10-18 (68 launches, n = 1-4 per cell, unpinned backends, rules v20;
  [board](twwarhammer3/tactic-cards.md#the-first-checks-night-of-2026-10-18)): the
  expendables card is a candidate (foils 0 of 2, witness 3 of 4, Kimi K3 low won); the
  chariot card leaks (rush-nearest won 1 of 2) although its witness won 4 of 4 and models
  won 3 of 12; gpt-6.1-sol won S1, the first model win on it; S5 dropped; flyers, giant and
  riflemen have no reliable witness. These are the first model wins on small scenarios.
- Spend: OpenAI $51.43 of $52; OpenRouter $6.69 (WH3) + $0.25 (Spire) of $50.

Next (proposals for the owner):
1. Agree or amend the card contract and the admission checks, then turn the agreed ones
   into AGENTS.md rows.
2. Settle the chariot card's 1.1 step (foils lost 3 of 3, witness 1 of 2); finish the expendables card
   (foil repeats, held-out variant, a fixed signature rule); check OpenRouter credits and
   pin backends; then several launches per model, since one launch is a screen.
3. Redesign flyers and giant (witnesses that keep their target); draft the next cards.

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

- OpenRouter returned HTTP 402 "in_flight_budget_exhausted" on 2026-10-18 with $6.93 of
  the $50 allowance on the ledgers: check the account's credits before paid jobs.
- No OpenRouter model pins its serving backend (Qwen3.6 only a quantization); across four
  GLM jobs, parse or validation failures ran from about 5% to 42% by backend. Pin before
  comparing models. Tag `archive/wh3-openrouter-pin` is an older draft: not the baseline pin.
- No test yet shows whether a game patch changes results (owner: later). A build warning
  shows in `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- Only WH3's $50 OpenRouter ceiling per ledger is in code; the OpenAI caps and the
  OpenRouter allowance shared by both games' ledgers are kept by hand.
- WH3 register: the version column is blank on benchmark rows (each manifest's card has
  it), and `stats` groups by commit, so results fragment; an API failure is recorded as a
  `policy_failure`.
- Not in the automated tests: the battle Lua's order application and the mailbox JSON
  codec; the report JavaScript (a manual browser check only); several Spire play-loop
  stop paths (source change, interruption).
- Spire's Workshop mod pins still block a run when a mod updates.
- `runs/` (22 GB) has no off-machine copy; its core evidence (traces, manifests, results,
  ledgers, replays) was about 2.6 GB, 90 MB with zstd, on 2026-10-17.

## Owner decisions waiting

1. Where to back up `runs/`.
2. The tactic-card checks ([proposal](twwarhammer3/tactic-cards.md#proposed-admission-checks);
   "winnable": a witness wins 3 of 4 at 5 s, or a model wins) and launches per cell.
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
