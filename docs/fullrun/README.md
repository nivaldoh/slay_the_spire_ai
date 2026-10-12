# Full runs with an API language model

Status: development, started 2026-10-12, current scaffolding **v7**. No run has won yet;
best floors per development seed are 29, 50 and 42 (v1.1: 16, 33, 16). Every version,
its evidence and its per-seed results are in [log.md](log.md). Code: `src/spire/fullrun/`.

## Question

How far does a cheap frontier API model get in complete Slay the Spire 1 runs (Ironclad,
Ascension 0) when it makes every decision through a public interface, and which
scaffolding measurably helps it? Scaffolding is found by watching the model's mistakes in
saved traces and changing one thing at a time. That makes this an autoresearch loop on
the prompt and memory, not weight training.

## Setup

- Model: `gpt-6-luna` through the OpenAI Responses API, reasoning effort `low`, structured
  JSON output. The owner chose Luna for cost; `gpt-6-astra`, `gpt-6-sol` and
  `gpt-6.1-sol` have declared prices in `spire.fullrun.api` and can be selected with `--model`.
- Spend: every call is priced from its reported usage at the standard-tier list prices in
  `spire.fullrun.api.PRICES` (read 2026-10-12) and appended to a ledger. A call is refused
  before it is sent if the ledger's total plus that call's worst-case cost (prompt bytes as
  an upper bound on input tokens, plus 4,000 output tokens) would exceed `--budget-usd`. The
  owner's cap for the first overnight work is **$25** on `runs/llm-spend.jsonl`, the default
  ledger. An API request that times out on our side may still be billed without a ledger
  entry, so the OpenAI dashboard total is the final check.
- Key: read from `OPENAI_API_KEY` or from the file named by `SPIRE_OPENAI_KEY_FILE`.
  It is never logged; evidence records only response IDs and usage.
- Engine: the pinned original game, one fresh JVM per run, `START IRONCLAD 0 <seed>`. The
  run ends only on the engine's death or victory screen, or at a declared action or time
  limit.

## Information boundary

`spire/decisions.py` builds each decision from a stable CommunicationMod message.
The policy sees allowlisted game fields: act, floor, HP, gold, deck, relics,
potions, keys, the map, the current screen, and combat state. Several fields are
hidden or changed:

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

## What the model sees (scaffolding v7)

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
- Invalid replies (bad JSON or an out-of-range choice) are re-asked twice, with the error
  appended. A third invalid reply ends the run as `policy_failure`. Transient HTTP and
  network errors are retried three times. Every attempt is billed and recorded.

What the model does not get: card, relic or power text; damage calculators; search; lookup
tools. Section 3 of [approaches.md](../approaches.md) suggests these matter. They are
candidates to add when traces show the need, one at a time.

## Evidence

Jobs go in `runs/fullrun/<job>/`, with the job's stdout and stderr beside it as
`<job>.log`. Each job directory holds `manifest.json` (source revision and fingerprints,
config, prompt hash), `system_prompt.md`, `environment.json`, and one `run-NNNN/` per seed.
Each run holds `trace.jsonl` with raw messages, public decisions, the full prompt, every API
attempt with usage, cost, latency, reason and notes, and the commands sent. `result.json`
holds the outcome, the final act, floor, HP, deck and relics, and LLM totals.

```bash
uv run python -m spire digest runs/fullrun/<job>                     # per-seed table for log.md
uv run python -m spire digest runs/fullrun/<job>/run-0000            # floors, choices, reasons
uv run python -m spire digest runs/fullrun/<job>/run-0000 --floor 16 # one fight, turn by turn
uv run python -m spire spend                                         # ledger total
```

## Autoresearch rules

- Editable surface: `configs/llm/` (system prompt and monster notes), and the rendering,
  memory and reply handling in `src/spire/fullrun/llm.py`. The information boundary
  (`spire/decisions.py`), the runner (`play.py`), the client and prices (`api.py`) and the
  ledger (`spire/ledger.py`) are not tuning surfaces. Fix them only for real defects, and
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

Preflight: no `spire play` process is running (`ps -eo pid,cmd | grep '[p]ython3 -m spire play'`;
a plain `pgrep -f` inside a shell or monitor script also matches that script), the game is
closed, `git status` is clean under `src/`, `scripts/` and `configs/`, and
`uv run python -m spire spend` is below the cap.

One iteration plays the three development seeds with the committed scaffolding version:

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

1. Watch for stalls: a trace that stays unmodified for more than 90 s while the process
   is alive. Stop a stalled job with SIGINT to its `python3 -m spire play` process, and
   diagnose the last observation before changing anything.
2. Review each run with `spire digest`, and `--floor N` for the fight that killed it.
3. Pick the most damaging mistake that recurs across runs. Make one change on the
   editable surface, add a test if code changed, commit, and run the next iteration on
   the same seeds.
4. Log the version, its evidence, the per-seed table and the decision in [log.md](log.md).
   Keep a change if the targeted mistake stops and outcomes do not get worse. With three
   stochastic runs per version, do not claim more than that.

## Candidate changes

With evidence so far, in priority order (v3–v7 took the earlier ones):

- **Skipped-reward memory**: v6's interface line did not stop the reopen loop (43 skips in
  v6 RUNDEV3). Candidate in `llm.py`: after the model skips a card reward, the rewards
  screen on that floor says which cards it already declined.
- **Hand-select purpose**: Gambling Chip's start-of-combat screen reads only "Choose up to
  99 card(s) from your hand", and v6 RUNDEV3 discarded Impervious+ believing it would
  block. Candidate: name the source of the selection when the state shows it (relic at
  combat start, or the card just played).
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
  turns, and Giant Head (v4 RUNDEV3's death).
- **Notes**: separate run notes from combat scratch, or tighten the instruction.
  Evidence: notes clobbered in the smoke run, copied unchanged on about half of calls.
- **Deck building**: RUNDEV2 decks of 28–31 cards with no removal bought at 474 gold
  (v2), and RUNDEV3's 11-card deck with little damage (v3).

## Ideas from related work (2026-10-12)

A literature check on self-improving harnesses is summarized in the
[approaches.md addendum](../approaches.md#addendum-2026-10-12-self-improving-harnesses-an-sts1-benchmark-and-training-services).
This loop already has the shape that works best there: a strong proposer changes the
harness between runs while a cheap, low-effort model plays. DemoEvolve, the closest
published setup, has GPT-5.4 at low effort play Slay the Spire 2, with Opus 4.7 proposing
changes, and selects them on three development seeds. The ideas below are not built yet.

Changes to the loop, in priority order:

1. **Replay saved decisions before a live run.** Each model decision in `trace.jsonl`
   keeps the observation, the full prompt and the notes. A replay script would re-render
   chosen decision points with the changed harness, keep the recorded notes and history,
   and ask the model about five times each. At about $0.0002 a call, a test costs cents
   and launches no game. It shows whether a change moves the targeted choice. It cannot
   show what follows that choice, so live runs still judge outcomes.
2. **Failure flags in `spire digest`.** Count per run what the log now counts by hand:
   turns ended with unspent energy while unblocked damage came in, deaths with potions
   unused, reopened card rewards, damage to minions against damage to the boss,
   exact-lethal deaths, and hallway fights with a large HP loss. These counts vary less
   than the floor reached. The flags should point into the traces rather than replace
   them: in Meta-Harness, a proposer that read raw traces scored a median of 50.0, against
   34.9 with summaries.
3. **Held-out seeds.** `RUNDEV1`–`RUNDEV3` have chosen seven versions. Add two or three
   seeds that never choose a change, and play them every few versions. DemoEvolve reports
   two held-out seeds. In Growing Harness, without a no-regression gate, success on the
   gate set rose to 30% and then fell to 16%.
4. **Demonstrations for the proposer only**, if a human run on a development seed can be
   recorded. In DemoEvolve, nine human runs shown only to the proposer took the StS2
   held-out mean floor from 18.17 to 28.83, against 23.17 with self-play traces alone.
   Demonstration summaries placed in the player's prompt did not help.

Harness changes this evidence favors:

- **Code over prose for recurring decisions.** Growing Harness moves recurring control
  logic into harness code. Continual Harness credits most of its gain to code skills.
  SpireBench (StS1, A20) finds that stronger models are "stronger mainly in the fights, not
  in the route". The skipped-reward memory and hand-select purpose candidates are of this
  kind. An end-of-turn preview with a lethal check would be another.
- **Notes shown only when they apply.** Extend the `monsters.json` pattern to events, relic
  screens and shops. AgenticSTS's triggered skills went from 3/10 to 6/10 StS2 wins
  (p≈0.37). Keep these to checked rules: SpireBench found 78% of model-written rules
  false (against 9% of facts) and caution advised seven times as often as risk.

Not worth adopting now:

- **The player refining its own harness**, as in Continual Harness. The benefit depends on
  the model: on Pokémon Emerald, every self-refining Flash-Lite variant scored below the
  minimal harness's 20% of milestones.
- **Model-written lessons carried across runs.** On StS1 A20, SpireBench measured +0.00
  acts from consolidated memory and +0.06 from verbatim notes over 80 matched pairs per
  arm. AgenticSTS's episodic memory added nothing.
- **Whole-text note rewrites**, if the notes change. ACE recorded a context that collapsed
  from 18,282 to 122 tokens in one rewrite; itemized additions and removals avoid that.
- **Paid post-training.** `gpt-6-luna` cannot be fine-tuned. Open models of its class
  scored within noise of GPT-5.6 Luna on SpireBench. Prime Intellect's hosted training runs
  rollouts on its own machines. Training an open model would buy a free local player near
  Luna's level, not a stronger one.

## Open owner decisions

- **Reasoning effort.** One v7 pass over the three seeds at `medium` would separate the
  model's limits from the harness's. The owner fixed `low`.
- **A whole turn per call.** In SpireBench, one action per call needed 3.0 more calls per
  floor, cost 23% more and cleared 0.07 fewer acts than batched turns. Model calls are
  most of the wall time here, so batching would buy iterations per night.
