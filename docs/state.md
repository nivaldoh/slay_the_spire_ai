# Project state

Updated 2026-10-18: what runs, where each game stands, what comes next. Status only:
history goes to the logs ([WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md),
[first combat](spire/first-combat/README.md)), owner directions to
[owner-direction.md](owner-direction.md). Under the
[hard rule](../AGENTS.md#verification-hard-rule) only the missing-ledger refusal is
verified so far; everything below is unverified.

## Active work

WH3 overnight tactic-card checks (owner away until 13:00 UTC, delegated), one-job plans in
`runs/twwarhammer3/calibration/n2/` and later, chained until 12:45 UTC at the latest; follow
with `uv run python -m twwarhammer3 watch`. N1 (S5 card check, b27) started 04:11 UTC.

## Priorities (owner, 2026-10-18)

1. The WH3 benchmark.
2. Slay the Spire, after WH3.
3. Post-training is secondary, and not only SFT: RL and other methods will be tried, so
   traces must suit them ([what they keep](posttraining.md#beyond-supervised-fine-tuning)).

## Total War: WARHAMMER III

[README](twwarhammer3/README.md), [log](twwarhammer3/log.md) ("On main" at the top),
[board](twwarhammer3/benchmark.md#small-scenario-status-after-the-overnight-tranche-2026-10-17),
[results.csv](twwarhammer3/results.csv).

- On `main`: `llm`/`llm_rules` v20, `commander` v7, skills v1.2, harness b27 (16,000-token
  cap; a game update warns, never blocks), evaluator v2, track `obs-v4+terrain/act-v2/live-1x`.
- M1 (2026-10-16, three battles per model and scenario): pooled over the six planned core
  scenarios Sol won 9 of 18 and Luna 1 of 18 (8/17 against 1/17 without the M1a caster
  launch), Fisher p 0.007-0.017, optimistic as rematches correlate. No scenario separates
  the models alone (at three a side the smallest two-sided p is 0.10); no difference
  detected between gpt-6.1-sol and gpt-6-sol (10/12 against 8/11, 9/12 with M1a).
- Small scenarios: none admitted; no model win (6 lost, 5 policy failures: 3 at the old
  4,000-token cap, 1 API error, 1 degenerate backend output). Scripted diagnostics: S5 won
  at both ages with contact; S1 only with fresh (0.3 s) information; S4's escort won while
  the gun it guards fell every time; S7's two wins came on the timer without contact (the
  defenders hid in a corner). S2 and S10 are set aside. Ladder V1: GLM-5.3 / low lost both
  anchors, so its added-factor steps wait for stronger models.
- All modes of all models: 34 configurations (32 before Qwen3.6, not 26), 204 battles per
  repeat over six scenarios. Spend: OpenAI $50.90 of $52 (no Sol battle fits); OpenRouter
  $3.86 of $50 (one allowance for both games).

Next (owner direction 2026-10-18: [tactic cards](twwarhammer3/tactic-cards.md)):
1. Agree the card contract and admission checks (foils lose, a witness wins by contact at
   5 s age in 3 of 4 launches, signature, rules parity, held-out variant).
2. Necessity checks on the declared cards (foils first, then witnesses), then model screens
   only on cards that pass; pin backends before comparing models.
3. Draft the remaining cards of the list; harness benchmarks (multi-agent, MCP) later.

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
2. What "demonstrably winnable" requires: does a scripted win at 0.3 s count, or a timer
   win without contact, or must a model win? And the frozen round's size and battles per cell.
3. A training host and a route to play a fine-tune; the teacher: OpenAI outputs (whether
   they may train a model; 25,503 rows excluded), GLM-5.3, or rejection-sampled Qwen3.6.
4. Whether Step 5 preview has open weights, and whether to request token log-probabilities
   or a sampler seed before the next model screens
   ([gaps](posttraining.md#beyond-supervised-fine-tuning)).
5. `wh3-rules-v21-attack-path` (unmerged); whether to keep `commander` (unplayed since v4).
6. S2 and S10: drop them or keep them set aside. More OpenAI budget for Sol battles.

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
