# Project state

Updated 2026-10-21: what runs, where each game stands, what comes next. Status only:
history goes to the logs ([WH3](twwarhammer3/log.md), [Spire full runs](spire/fullrun/log.md),
[first combat](spire/first-combat/README.md)), owner directions to
[owner-direction.md](owner-direction.md). Under the
[hard rule](../AGENTS.md#verification-hard-rule), only the listed agreed checks are
verified at their recorded revisions; the gameplay findings below remain unverified.

## Active work

No benchmark or paid job is running. The [evaluation guidelines](twwarhammer3/evaluation-guidelines.md#13-owner-decisions-these-rules-need),
[scope](twwarhammer3/benchmark.md#scope-and-first-release), suite, checks and gates remain proposals;
[Empire items](twwarhammer3/empire.md) pending. Away window 2026-10-21 02:20 to about 12:00 (Claude
Code; offline, $0, no game): [log](twwarhammer3/log.md#2026-10-21-a-proposed-starting-set-the-failure-rule-recount-and-a-blind-c1-recount),
`runs/twwarhammer3/away-20261021/`. Waiting changes: 3 of 3 ([branches](#branches)).

Priorities (2026-10-18): WH3 first, then Spire; post-training secondary. [Traces must support RL](posttraining.md#beyond-supervised-fine-tuning).

## Total War: WARHAMMER III

[README](twwarhammer3/README.md), [log](twwarhammer3/log.md) ("On main" at the top),
[benchmark definition](twwarhammer3/benchmark.md), [tactic cards](twwarhammer3/tactic-cards.md),
[latency program](twwarhammer3/latency.md) (plan), [results.csv](twwarhammer3/results.csv).

- On `main`: `llm`/`llm_rules` v21, `commander` v7, skills v1.2, harness b46, evaluator v2,
  track `obs-v4+terrain/act-v2/live-1x` ([definitions](twwarhammer3/log.md#on-main)).
- Benchmark: [the chariot card](twwarhammer3/tactic-cards.md#the-chariot-card-the-first-benchmark-card);
  results in the [b40 round](twwarhammer3/log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40).
  No model has won above its foils' bound (an unverified gameplay finding).
- Spend: OpenAI $51.47 of $52; WH3 OpenRouter ledger $21.33 ($8.84 the Empire night).

Next (proposals for the owner; [release route](twwarhammer3/benchmark.md#route-to-the-first-release)):
0. Read the night's [results](twwarhammer3/empire.md#results) and its six
   [owner items](twwarhammer3/empire.md#for-the-owner-to-decide) (from the rank-5 line card to the export).
1. Agree the [correctness checks and failure rule](twwarhammer3/benchmark.md#correctness-checks-to-agree)
   and chariot version decisions; preserve c1's rule. The c1 [recount/rerun](twwarhammer3/benchmark-run.md#independent-rerun-acceptance-proposal)
   handoff is in `runs/twwarhammer3/away-20261021/handoff-c1/` (not shared off this machine).
2. Breadth: the [starting set](twwarhammer3/tactic-cards.md#the-starting-set-proposal-2026-10-21) (chariot,
   rank-5 line, expendables) and its $0 screen with two probes; the chariot waits on step 1.
3. P5's Kimi plans remain unplayed; choose their question before scheduling more chariot
   cells. A stronger model at modifier 1.1 remains untested (the OpenAI cap).
4. [Robot team plan](twwarhammer3/robot-team-plan.md) ([research guide](twwarhammer3/robot-team-research.md)):
   does the Empire line battle offer useful recovery? 1 of 17 recorded battles had a replacement
   opportunity ([review](twwarhammer3/robot-team-plan.md#1-establish-a-recoverable-coordination-problem)); b46 is unplayed.

## Slay the Spire

[README](spire/fullrun/README.md), [log](spire/fullrun/log.md),
[results.csv](spire/fullrun/results.csv). v10 on `main`. No run has won; the furthest
reached Act 4 (v8, floor 54). Version differences sit within run-to-run variation (about 11
floors per run on one seed; replays of one harness differed by 13-26 floors), measured only
on the three tuning seeds. `HELDOUT01`-`HELDOUT10` are unplayed. Spend: OpenAI $2.52 of
$25, OpenRouter $0.25. Next, after WH3: one decisive comparison (current against ablated
scaffolding, 20-30 fresh seeds per arm, about $5 and three nights) or a freeze; `v11-keys`
waits on it. [Open decisions](spire/fullrun/README.md#open-owner-decisions); paused:
[first combat](spire/first-combat/README.md); planned: [open-weight](spire/open-weight/README.md).

## Post-training

[posttraining.md](posttraining.md): capture/export/dataset smoke passes, with no learning
claim. Missing: training host, fine-tune serving for both games and useful targets.

## Known issues

- Check OpenRouter credits before paid jobs: on 2026-10-21 the account showed $24.26 used of
  $60, the ledgers $2.68 less. OpenAI caps and the shared OpenRouter allowance are kept by hand.
- Pinned OpenRouter backend outages count against the model; Step 5 preview is unpinned.
- No test yet shows whether a game patch changes results (owner: later). A build warning
  shows in `doctor`, the job's stderr, `watch` and `digest`; `stats` would pool builds.
- WH3 register and `stats`: blank version on benchmark rows, grouping by commit, API failures
  as `policy_failure` (`card` classifies failures, keys by setup); a defender's timer stalemate
  counts as won (3 rows; `stats` ignores `ended_by`; the card and the Empire review do not).
- No automated checks for report JavaScript or several Spire play-loop stop paths. Spire's
  Workshop mod pins still block a run when a mod updates.

## Owner decisions waiting

1. **The [starting set's screen](twwarhammer3/tactic-cards.md#the-starting-set-proposal-2026-10-21)**: recommended, a yes runs its $0 scripted plan
   (39 launches, about 5.1 h) on a free night (no item 9 needed) and agrees its reading rule and the two markers as the card table words them,
   each read at its first melee frame. Alternative: change the set or the rule first; deferring keeps breadth at the chariot alone.
2. **The defender prompt** of every model controller says "if time runs out, you win"; the cards count only contact wins
   ([Empire decision 7](twwarhammer3/empire.md#decisions-taken-for-the-owners-review), for your review; 16 of 17 `llm_rules` episodes on five
   defending battles restate it). Recommended: a contact-scoring scenario field that says so instead (a prompt version once fewer than 3 changes wait); or count timer wins.
3. **The [failure rule](twwarhammer3/benchmark.md#correctness-checks-to-agree)**: recommended, agree it (rescores none of 595 episodes) and merge
   `wh3-keep-engine-ending` (`git show 98b3013`, harness b47), which keeps the ending only, scores unchanged; scoring that ending and construction failures is a later change.
   Alternative: keep today's code, where a late acknowledge or `close()` failure loses the ending (none of 595 did).
4. Where to back up `runs/` (no copy; 23 GB, 7.1 GB without `checkpoints/`, 2026-10-21). Recommended: copy it without `checkpoints/`
   to a `C:` folder you name and check a sha256 manifest after (same machine, so not off-site; no script exists yet); or an external
   or cloud copy. Deferring leaves the evidence in one place.
5. The chariot card: [second-pass decisions](twwarhammer3/tactic-cards.md#second-pass-2026-10-19-evening-findings-and-the-version-2-decisions) 3-5; recommended, witness v2 for the next confirmation at
   decision 3's 2 s/2 s cell (v2 3/3 there, 4/5 at 5 s/5 s and at 8 s/8 s; v1 2/8 and 0/4), c1 staying v1's admitted record. [Latency
   program](twwarhammer3/latency.md#owner-decisions), your call: `c1` as evidence (recommended there), the $20 P5 cap; b36's backend pins await review.
6. A training host and a route to play a fine-tune; the teacher: OpenAI outputs (may they train a model? 25,503 rows
   excluded: 11,099 in the Spire export `luna-v1-v10-20261017`, 14,404 in WH3's `trace-v2-20261017`), GLM-5.3 or
   rejection-sampled Qwen3.6 ([licenses](posttraining.md#provider-terms)); your call, secondary.
7. Token log-probabilities, a sampler seed or explicit GLM/Kimi sampling before the next model screens
   ([gaps](posttraining.md#beyond-supervised-fine-tuning))? Recommended: ask where the pinned backend lists them (log-probabilities: Qwen's,
   one of Kimi's two endpoints, not GLM's Decart; all list a seed and sampling; listing rechecked 2026-10-21). Step 5's weights are [public](posttraining.md#provider-terms).
8. `wh3-rules-v21-attack-path` (one rules sentence: attacks take the engine's route; move first
   and queue the attack): recommended, its own `llm_rules` version after item 2's, or drop it.
   Your call: keep `commander` (unplayed since v4)? More OpenAI budget (the $52 cap refuses Sol)?
9. Your call: yes/no on the [away guidelines](autonomy.md) (tonight ran under the proposal, not as its agreed trial; reviews caught 110
   errors in my drafts and commits, 109 fixed); before any campaign launch, yes/no on harness saves in the WH3 profile and on Steam
   achievements (which cannot be undone; a no keeps campaign work to offline drafts).

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
- `wh3-keep-engine-ending` (`98b3013`, worktree `../slay_the_spire_ai-wh3-ending`): inbox item 3; merges
  cleanly onto `main` (rechecked 2026-10-21; merged WH3 suite and ruff pass at `66d2d20`).
- Archived drafts are tags (`git tag --list 'archive/*'`).
