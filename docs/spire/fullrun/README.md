# Slay the Spire full runs with an API language model

Status: development since 2026-10-12; the current version, spend and next step are in
[state.md](../../state.md). v10 has no Luna pass on the development seeds (its job died to
a WSL restart on 2026-10-13); since then, three Qwen3.6 smoke runs (2026-10-17) and the
2026-10-18 runner change (jobs labelled v10.1). Every version, its evidence and per-seed
results are in [log.md](log.md). Code: `src/spire/fullrun/`, on top of `src/gameai/`.

## Question

How far does a cheap frontier API model get in complete Slay the Spire 1 runs (Ironclad,
Ascension 0) when it makes every decision through a public interface, and which
scaffolding measurably helps it? Scaffolding is found by watching the model's mistakes in
saved traces and changing one thing at a time. That makes this an autoresearch loop on
the prompt and memory, not weight training.

## Setup

- Model: `gpt-6-luna` through the OpenAI Responses API, reasoning effort `low`, structured
  JSON output. The owner chose Luna for cost; `gpt-6-astra`, `gpt-6-sol` and
  `gpt-6.1-sol` have declared prices in `gameai/providers.py` and can be selected with
  `--model`. `spire play --provider openrouter` plays the open-weight models declared there
  for OpenRouter (only Qwen3.6-35B-A3B has played, [posttraining.md](../../posttraining.md));
  a model or effort its provider does not declare is refused before the job directory
  exists.
- Spend: every call is priced from its reported usage at the standard-tier list prices in
  `gameai.llm.PRICES` (read 2026-10-12) and appended to a ledger. A call is refused
  before it is sent if the ledger's total plus that call's worst-case cost (prompt bytes as
  an upper bound on input tokens, plus the 16,000-token output cap) would exceed `--budget-usd`. The
  default ledger is `runs/llm-spend.jsonl`; the owner's cap is in [state.md](../../state.md).
  A request whose billing is uncertain (a timeout, HTTP 408 or 5xx) is charged at its
  reservation with a ledger entry, so the ledger overestimates those attempts; the provider
  dashboard is the final check. OpenRouter calls are charged their
  reported `usage.cost` to `runs/spire-openrouter-spend.jsonl`, which shares the owner's
  $50 OpenRouter allowance with WH3's file
  ([controllers.md](../../twwarhammer3/controllers.md#openrouter)), so `--budget-usd` must
  leave room for that file's total; `spire spend --provider openrouter` totals it.
- Key: `gameai.llm` reads it, for both games, from `OPENAI_API_KEY` or the file named by
  `SPIRE_OPENAI_KEY_FILE`; for OpenRouter, from `OPENROUTER_API_KEY` or the file named by
  `OPENROUTER_API_KEY_FILE`. It is never logged; evidence records only response IDs and
  usage.
- Engine: the pinned original game, one fresh JVM per run, `START IRONCLAD 0 <seed>`. The
  run ends only on the engine's death or victory screen, or at a declared action or time
  limit.

## Information boundary

JUDGEMENT?: Public interface — assistant, 2026-10-12 (flagged by Claude, 2026-10-28): the
allowlist in `decisions.py` hides card UUIDs, the seed, monster move IDs and base damage, and
sorts the draw pile (unless Frozen Eye). Showing more or less changes what a model can infer.

`spire/decisions.py` builds each decision from a stable CommunicationMod message.
The policy sees allowlisted game fields: act, floor, HP, gold, deck, relics,
potions, keys (allowlisted, but CommunicationMod 1.2.1 never sends them), the map, the
current screen, and combat state. Several fields are hidden or changed:

- UUIDs, the seed, the action phase, enemy move IDs, move history and base damage are
  removed.
- The draw pile is sorted into an unordered multiset unless the player holds Frozen Eye,
  which shows the real order in game.
- Enemy damage and hit counts are kept only for attack intents.

Choices are every legal `play`, `potion use`/`discard`, `choose` and screen button
(`confirm`, `proceed`, `skip`, `cancel`, `return`, `leave`), plus `end`. Each choice has a
label built from the screen. Raw input (`key`, `click`), `wait` and `state` are never
offered. Identical cards in hand are offered once, since they are interchangeable. A grid
card that is already selected is labeled "deselect", and `cancel` is not offered in a grid's
confirm view, where CommunicationMod would never reply. A state with exactly one choice is
answered without a model call. Initial `DEBUG` intents are settled with a logged `wait 60`,
as in first-combat rollouts.

## What the model sees (scaffolding v10)

The version that introduced each piece is in brackets; [log.md](log.md) has the evidence.

- A static system prompt, `configs/llm/system_prompt.md`: the interface and output format,
  and two state facts, that 0 HP is death and that a skipped card reward stays listed (v6).
  It has no strategy advice and no card text.
- Model-written run notes of up to 2,000 characters, replaced through the reply's `notes`
  field: its only memory across a run. Also the last 12 decisions with their reasons.
- A text rendering of the state and the numbered choices. The header names the act boss
  and its floor (v4). The map shows only the nodes still reachable. Combat states give the
  room type (v1.1) and the visible incoming attack damage against block and HP (v3).
- Enemy rules notes from `configs/llm/monsters.json`, shown only while that enemy is in the
  fight: the Act 1 elites and bosses (v2), the Large slimes (v5) and The Collector (v7).
  Every number is checked against the game.

  JUDGEMENT?: Enemy notes — assistant, v2-v7 (flagged by Claude, 2026-10-28): they mix rules with
  advice ("Kill an outer Sentry first."), written for enemies the model misplayed; rules-only
  notes change what a floor measures, like WH3's `llm` tactics.
- On the reward screens, the card rewards already skipped on that floor and their cards
  (v8).
- Cards show the engine's `ethereal` and `exhausts` keywords, with one system prompt line
  on what they do (v9).
- A hand selection names its source when the trace shows it: the card or potion just
  played, or Gambling Chip on turn 1 (v10).
- Invalid replies (bad JSON, a missing or wrong-typed field such as `choice` true or 1.0,
  or an out-of-range choice) are re-asked twice, with the error appended. A third invalid
  reply ends the run as `policy_failure`. Transient HTTP and network errors are retried
  three times; an HTTP 429 that outlasts them is asked again after pauses of 15 s up to
  480 s (since 2026-10-23). Every attempt is billed and recorded.

What the model does not get: card, relic or power text; damage calculators; search; lookup
tools. Section 3 of [approaches.md](../approaches.md) suggests these matter. They are
candidates to add when traces show the need, one at a time. SpireBench's system prompt
carries a compendium of the rules, keywords and every card, relic and potion with its
effect; this harness's checked notes (enemy rules, v9's keywords) are a narrow version of
that, and v7–v9 deaths from unknown card and power rules (Ethereal, Corruption, Apparition+)
argue for a broader one. Game text itself must not be committed.

JUDGEMENT: Knowledge boundary — assistant, 2026-10-12 (flagged by Claude, 2026-10-28): starting
from no card, relic or power text and no tools; notes from observed mistakes follow the owner's
2026-10-12 direction. A broader start (a rules summary; no game text) changes what a floor measures.

## Evidence

Jobs go in `runs/fullrun/<job>/`, with the job's stdout and stderr beside it as
`<job>.log`. Each job directory holds `manifest.json` (source revision and fingerprints,
config, prompt hash, status and finished runs), `system_prompt.md`, `environment.json`, and
one `run-NNNN/` per seed. Each run holds `trace.jsonl` with raw messages, public decisions,
the full prompt, every API attempt with usage, cost, latency, reason and notes, and the
commands sent. `result.json` holds the outcome, the final act, floor, HP, deck and relics,
and LLM totals. A trace record of kind `decision` holds `decision.observation`,
`decision.candidates` (each with `id`, `command` and `label`), the `choice_id` taken, and
`behavior`, whose `type` is `llm` (with `reason` and `notes`) or `forced`;
`digest._decisions` reads them. Since harness v10.2 (2026-10-23, `model_exchange_version`
2) a decision's attempts omit the request and output items, which its `model_exchange`
event keeps once, with Qwen3.6's token logprobs; and `run-NNNN/saves/` holds a copy of each
new version of the game's autosave, each with a `save_snapshot` event
([posttraining.md](../../posttraining.md#beyond-supervised-fine-tuning)).

```bash
uv run python -m spire digest runs/fullrun/<job>                      # per-seed table for log.md
uv run python -m spire digest runs/fullrun/<job>/run-0000             # floors, flags, final notes
uv run python -m spire digest runs/fullrun/<job>/run-0000 --picks     # also each choice and reason
uv run python -m spire digest runs/fullrun/<job>/run-0000 --floor 16  # one floor, turn by turn
uv run python -m spire watch runs/fullrun/<job>  # waits for the next finished run, stall or end
uv run python -m spire spend                   # OpenAI ledger total; --provider openrouter
uv run python -m spire stats                  # milestones per model, effort and harness version
uv run python -m spire stats --rebuild        # rewrite results.csv from every saved job
```

`spire play` appends one row per run to the committed [results.csv](results.csv): date, job,
run, seed, character, ascension, model, effort, harness version (from the job name), source,
outcome, act, floor, score and cost. Rows come only from saved evidence, so `--rebuild`
reproduces them; pass `play --results <path>` to keep a smoke test out of the register.
`spire stats` counts, per group, the runs that reached Acts 2, 3 and 4 (however they
ended), wins, and the best floor, plus the mean floor over finished runs (engine-confirmed
wins and deaths).

A run's flags count what the log once counted by hand: turns ended with energy and a
playable card (and those with attacks exceeding block), card rewards skipped (and floors
where one was reopened), potions used and held at the end, and the last turn's incoming
damage against block and HP. They point into the traces and do not replace reading them.

## Export

`spire export` turns saved jobs or runs into a dataset for post-training and analysis.
It is offline: no API call, no game, and the evidence is never changed. Code:
`src/spire/fullrun/export.py`.

```bash
uv run python -m spire export runs/fullrun/<job> [runs/fullrun/<job>/run-NNNN ...] \
    --output runs/fullrun-exports/<name>
```

It writes `decisions.jsonl` (one row per model request, with every attempt), `logprobs.jsonl`
(token logprobs, about 1 kB per output token, keyed by row id and attempt), `sources.json`
(manifests, environments, each run's result, profile and deployment, input and exporter
hashes, filters, counts and issues) and `datacard.md`. The output must be a new directory
outside the jobs; it is built beside it and renamed after every input hash is rechecked.
Jobs still marked running and runs without `result.json` are refused. `--model`,
`--provider` and `--prompt-sha256` (the system prompt's) are repeatable: values of one
filter are alternatives, and every filter given must match.

Rows follow the export-row contract shared with the [WH3 exporter](../../twwarhammer3/traces.md):
`group` is the seed, `split` is `held_out` for the reserved seeds below and `development`
otherwise, and `harness` and `prompt_version` are the job-name label. Spire rows add the public
`decision` the policy saw, the `choice`, the reply's reason and notes, and `labels` taken
from decision observations only, including each combat decision's `fight`: won when a
later decision is out of combat or the run is won during it, lost when the run is lost
during it, otherwise unknown, with HP at its start and at the next out-of-combat decision.
A request that never got an accepted reply (invalid replies, an API failure, a budget
stop) is a row with an `error` and no decision, and so is an accepted reply whose decision
was never logged (`DecisionNotRecorded`) and a request stopped by an interrupt before any
reply was accepted (`Interrupted`). Traces from before exchange capture (no `model_exchange_version` in the
manifest: every job up to v10) kept the first prompt but no retry prompt or reasoning;
those gaps are labelled as issues, never reconstructed. Their 11,167 requests all come
from OpenAI's `gpt-6-luna`, whose rows must not enter a training set by default (the
owner has not decided the terms question), and every readable profile is at Ironclad
unlock level 3; the data card explains both.

Held-out seeds: `HELDOUT01` to `HELDOUT10` (`HELD_OUT_SEEDS` in `export.py`, chosen on
2026-10-17 under the owner's delegation) are reserved for evaluating models and
fine-tunes. The tuning loop must never play them, and no harness change may be chosen on
their results; their exported rows are `held_out`, so the dataset builder never trains on
them. The game reads a seed in any case, the letter O as 0 and leading zeros as nothing
(`HELD0UT01` is `HELDOUT01`); the exporter holds out every such spelling, but a seed's
`group` is the seed as typed.

## Autoresearch rules

- Editable surface: `configs/llm/` (system prompt and monster notes), and the rendering,
  memory and reply handling in `src/spire/fullrun/llm.py`. The information boundary
  (`spire/decisions.py`), the runner (`play.py`), the client, prices and retry loop
  (`gameai/llm.py`) and the ledger (`gameai/ledger.py`) are not tuning surfaces. Fix them only for real defects, and
  record each fix in the log.
- Commit before every run; the runner refuses uncommitted source and prompt changes.
- Judge a change by outcomes (floor reached, wins), not by how good the reasons sound.
  With a handful of runs a night, report each run individually and do not call small
  differences improvements. Compare variants on the same seeds where possible, knowing
  the model itself is stochastic. A prompt edit can perturb choices it was not aimed at,
  so same-seed runs stay comparable only up to their first divergent decision.
- Log every change in [log.md](log.md) with the mistake that motivated it and the runs
  before and after.

## The loop

One iteration plays the three development seeds with the committed scaffolding version.
There is no separate preflight: `spire play` refuses uncommitted source, an existing output
directory, a second Spire controller and a running Slay the Spire, and the ledger refuses
calls over the cap. It cannot see a WH3 job, so check Active work in
[state.md](../../state.md) first.

```bash
export SPIRE_OPENAI_KEY_FILE=~/.config/robocasa/openai_api_key
JOB=runs/fullrun/llm-luna-v<VERSION>-dev-<DATE>
nohup uv run python -m spire play --model gpt-6-luna --effort low \
  --seed RUNDEV1 --seed RUNDEV2 --seed RUNDEV3 --budget-usd 25 \
  --output $JOB > $JOB.log 2>&1 &
```

Measured cost: Luna runs from v1.1 to v7 cost $0.03–0.17 each and took 11–62 minutes,
depending on how far the model got. Model calls took 70–80% of that wall time in the v6
and v7 runs (median about 3 s per call, with a median of 100–130 reasoning tokens at
`low` effort); the engine took the rest. The $25 cap is therefore not the binding limit;
time is, at roughly two to four iterations a night. Then:

1. Run `spire watch $JOB` in the background (in Claude Code, Bash with `run_in_background`)
   and start it again after each event. It returns one line per event: a finished run (its
   log table row), a stall (the newest trace unchanged for 90 s), the job's end, or a job
   that wrote no manifest (the log's last lines say why). Stop a stalled job with SIGINT to
   its `python3 -m spire play` process, and diagnose the last observation before changing
   anything.
2. Review each finished run in a fresh subagent with the prompt below (in Claude Code, a
   general-purpose agent, not a fork), so digests stay out of the main context. Add its
   findings to a draft entry in [log.md](log.md) at once; `docs/` is not fingerprinted, so
   this is safe while the job runs.
3. While the job runs, draft one change on the editable surface in a git worktree: a job
   stops if a file in `play.py`'s `SOURCES` changes between its seeds (`src/gameai/`,
   `src/spire/`, `configs/llm/`, `pyproject.toml`, `uv.lock`, `.python-version`), so WH3
   work that edits `src/gameai/`, `pyproject.toml` or `uv.lock` stops it too. Target the
   most damaging mistake that recurs across runs. Before editing, read the decisions the
   reviews point to (`--floor N`) and the source by function (`grep -n`, then that range).
   Add a test if code changed.
4. When the job ends, finish its log entry (the table is `spire digest $JOB`), merge the
   change, commit it with the new `results.csv` rows and push once, and run the next iteration on the same seeds. Keep a
   change if the targeted mistake stops and outcomes do not get worse. With three
   stochastic runs per version, do not claim more than that.

   JUDGEMENT: Keep rule and seeds — assistant, 2026-10-12 (flagged by Claude, 2026-10-28): one run
   on each of RUNDEV1-RUNDEV3 decides whether the mistake stopped and outcomes held. More seeds or
   runs (SpireBench uses ten seeds) change which versions are kept; the v1-v8 keeps rest on it.

Update "Active work" in [state.md](../../state.md) when the loop starts and when it stops, with
the time from `date -u`, rather than at every launch. To save context, a session reads
[state.md](../../state.md), this page and only the newest entry of [log.md](log.md), and never
reads `docs/spire/approaches.md` whole.

Review prompt, one subagent per finished run:

> Review the Slay the Spire full run at `runs/fullrun/<job>/run-NNNN` in
> /home/niv/repos/slay_the_spire_ai, read-only. Run `uv run python -m spire digest <run>`,
> then `--floor N` for the fight that ended the run and for floors the flags or HP losses
> point to, and `--picks` (filtered to the floors in question) for route and reward choices.
> The same seed's previous run is `<previous run>`; compare only where it explains a
> different outcome. Reply in at most 300 words: the outcome and cause of death, with floor
> and turn; the flags; up to three costliest mistakes, each with floor and turn, the
> model's stated reason and why it was wrong; and which of them match the candidate
> changes in docs/spire/fullrun/README.md. Report what the trace shows, not guesses.

## Candidate changes

With evidence so far, in priority order (v3–v10 took the earlier ones):

- **Keys memory** (harness gap): CommunicationMod 1.2.1 never sends `keys`, so the "Keys:"
  line never appears and the model tracks keys only in its notes. v9 RUNDEV1 took an
  elite path for an Emerald Key it already held and died on that path. Candidate in
  `llm.py`: remember keys from the choices that take them (the Emerald and Sapphire Key
  rewards, Recall at a rest site) and show them in the header. Drafted as v11 on branch
  `v11-keys` (`cd97667`), unmerged.
- **Power rules**: v7 and v8 RUNDEV1 played Corruption+ without knowing it exhausts every
  skill (spending the last Defends; halving Second Wind+). Candidate: short checked notes
  for the player's powers, shown while active, like `monsters.json`.
- **Potion effects end with the combat**: Heart of Iron was drunk in hallway fights twice
  "to help through the Slime Boss fight". Draft line: "Potions are single-use. A potion's
  effect, like every power, buff and debuff, ends with the combat it is used in." Potion
  use swings both ways: early runs drank boss potions in hallways, v4 RUNDEV3 died to an
  elite holding a potion "reserved for Time Eater".
- **Optional fights and big trades**: the Colosseum's second fight at 58 HP (v6 RUNDEV1),
  an Orb Walker event fight at 84 HP that left 25 (v6 RUNDEV3), and Council of Ghosts'
  half max HP before The Collector (v3 and v6 RUNDEV2). This is strategy advice; prefer
  state or rules fixes first.
- **Act 3 notes** as runs reach them: Transient (v6 RUNDEV3's death) fades after a few
  turns, Giant Head (v4 RUNDEV3's death), and Awakened One, which revives at full HP in a
  second form: v7 RUNDEV2 killed the first at 21 HP with no block left and died to it.
- **Notes**: separate run notes from combat scratch, or tighten the instruction.
  Evidence: notes clobbered in the smoke run, copied unchanged on about half of calls.
- **Deck building**: RUNDEV2 decks of 28–31 cards with no removal bought at 474 gold
  (v2), and RUNDEV3's 11-card deck with little damage (v3).

## Ideas from related work (2026-10-12)

A literature check on self-improving harnesses, with its evidence, is in the
[approaches.md addendum](../approaches.md#addendum-2026-10-12-self-improving-harnesses-an-sts1-benchmark-and-training-services).
This loop already has the shape that works best there: a strong proposer changes the
harness between runs while a cheap, low-effort model plays (DemoEvolve, the closest
published setup, does this on Slay the Spire 2). Loop changes not built yet, in priority
order:

1. **A results table across versions** (owner request, 2026-10-12). The first part is
   built: [results.csv](results.csv) holds one row per run and `spire stats` prints acts
   reached, wins and floors per model, effort and harness version. Still to add from
   SpireBench's measures where they fit: bosses beaten, HP lost per Act 1 hallway fight (the measure
   that best separated models there), card-reward skip and reopen counts, calls and cost
   per floor. The v7 replay (floors 16, 33, 16 against 29, 50, 42 for the same prompts)
   shows why: versions need several runs per seed, summarized, before any comparison.
   SpireBench itself is not reusable code: as of 2026-10-12 neither its harness nor its
   CommunicationModPlus fork is public (the paper links neither), so only its metric
   definitions and protocol (ten fixed held-out seeds, the same for every model) carry over.
2. **Replay saved decisions before a live run.** Re-render recorded decision points with the
   changed harness, keep the recorded notes and history, and ask the model about five times
   each: cents and no game. It shows whether a change moves the targeted choice, not what
   follows it, so live runs still judge outcomes.
3. **Held-out seeds.** Two or three seeds that never choose a change, played every few
   versions, against selecting for `RUNDEV1`–`RUNDEV3` alone. SpireBench uses ten.
4. **Demonstrations for the proposer only**, if a human run on a development seed can be
   recorded.

Failure flags in `spire digest`, formerly second, are built (2026-10-12).

Harness changes the evidence favors: code over prose for recurring decisions (the
skipped-reward memory and hand-select purpose candidates are of this kind; an end-of-turn
preview with a lethal check would be another), and notes shown only when they apply, kept
to checked rules: extend the `monsters.json` pattern to events, relic screens and shops
(AgenticSTS's triggered skills went from 3/10 to 6/10 StS2 wins, p≈0.37). Not worth
adopting now: the player refining its own harness, model-written lessons carried across
runs, whole-text note rewrites, and paid post-training.

## Open owner decisions

- **Reasoning effort.** One v7 pass over the three seeds at `medium` would separate the
  model's limits from the harness's. The owner fixed `low`.
- **A whole turn per call.** In SpireBench, one action per call needed 3.0 more calls per
  floor, cost 23% more and cleared 0.07 fewer acts than batched turns. Model calls are
  most of the wall time here, so batching would buy iterations per night.

- **Moved from the state page inbox (2026-10-28), verbatim.** Item 9: **Spire's next step.** After WH3, run one meaningful comparison or freeze this track. Proposed comparison: current controller against ablated scaffolding, 20–30 fresh seeds per arm, about $5 and three nights. `v11-keys` waits on that choice; [other Spire questions](#open-owner-decisions) stay secondary. No held-out seeds have been played. The state-restore investigation comes first (owner, 2026-10-23). To decide later: whether the next data night uses a teacher (GLM-5.3) or Qwen3.6 with reasoning on.
- Item 10: **Spire capture check.** Noted for later (owner, 2026-10-23: "Not sure what this is"). It is a script that reads one finished run and checks the new capture against facts recorded separately: the logprob tokens spell the reply and match the provider's token count, the choice probabilities sum to 1, and each save snapshot decodes with the run's own seed. It passed on 40 of 43 night runs ([log](log.md#2026-10-23-collection-night-qwen36-reasoning-off-harness-v102)). Agreeing it would make it the capture's repeatable test under the verification rule; until then the capture counts as unverified. It lives only in `runs/fullrun/collect-20261023/check_capture.py`, which has no backup.
