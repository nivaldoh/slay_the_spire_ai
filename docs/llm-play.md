# Full runs with an API language model

Status: development, started 2026-10-12. No benchmark score is claimed yet.

## Question

How far does a cheap frontier API model get in complete Slay the Spire 1 runs (Ironclad,
Ascension 0) when it makes every decision through a public interface, and which
scaffolding measurably helps it? Scaffolding is found by watching the model's mistakes in
saved traces and changing one thing at a time. That makes this an autoresearch loop on
the prompt and memory, not weight training.

## Setup

- Model: `gpt-6-luna` through the OpenAI Responses API, reasoning effort `low`, structured
  JSON output. The owner chose Luna for cost; `gpt-6-astra`, `gpt-6-sol` and
  `gpt-6.1-sol` have declared prices in `spire.llm` and can be selected with `--model`.
- Spend: every call is priced from its reported usage at the standard-tier list prices in
  `spire.llm.PRICES` (read 2026-10-12) and appended to a ledger. A call is refused before
  it is sent if the ledger's total plus that call's worst-case cost (prompt bytes as an
  upper bound on input tokens, plus 4,000 output tokens) would exceed `--budget-usd`. The
  owner's cap for the first overnight work is **$25** on `runs/llm-spend.jsonl`. An API
  request that times out on our side may still be billed without a ledger entry, so the
  OpenAI dashboard total is the final check.
- Key: read from `OPENAI_API_KEY` or from the file named by `SPIRE_OPENAI_KEY_FILE`.
  It is never logged; evidence records only response IDs and usage.
- Engine: the pinned original game, one fresh JVM per run, `START IRONCLAD 0 <seed>`. The
  run ends only on the engine's death or victory screen, or at a declared action or time
  limit.

```bash
export SPIRE_OPENAI_KEY_FILE=~/.config/robocasa/openai_api_key
uv run python -m spire play --model gpt-6-luna --effort low --seed LUNADEV1 \
  --budget-usd 25 --output runs/llm-luna-example
```

## Information boundary

`spire/fullgame.py` builds each decision from a stable CommunicationMod message.
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
offered. Identical cards in hand are offered once, since they are interchangeable. A state
with exactly one choice is answered without a model call. Initial `DEBUG` intents are
settled with a logged `wait 60`, as in first-combat rollouts.

## Scaffolding, version 1

- A static system prompt, `configs/llm/system_prompt.md`, describing the interface and
  output format. It contains no strategy advice and no card text.
- Model-written run notes of up to 2,000 characters. The model replaces them through the
  reply's `notes` field, and they are its only memory across a whole run.
- The last 12 decisions, each with its stated reason.
- A text rendering of the state, and the numbered choices. The map shows only the nodes
  still reachable.
- Invalid replies (bad JSON or an out-of-range choice) are re-asked twice, with the error
  appended. A third invalid reply ends the run as `policy_failure`. Transient HTTP and
  network errors are retried three times. Every attempt is billed and recorded.

What the model does not get: card, relic or power text; damage calculators; search; lookup
tools. Section 3 of [approaches.md](approaches.md) suggests these matter. They are
candidates to add when traces show the need, one at a time.

## Evidence

Each job directory holds `manifest.json` (source revision and fingerprints, config, prompt
hash), `system_prompt.md`, `environment.json`, and one `run-NNNN/` per seed. Each run holds
`trace.jsonl` with raw messages, public decisions, the full prompt, every API attempt with
usage, cost, latency, reason and notes, and the commands sent. `result.json` holds the
outcome, the final act, floor, HP, deck and relics, and LLM totals.

## Autoresearch rules

- Editable surface: `configs/llm/system_prompt.md`, and the rendering, memory and reply
  handling in `spire/llm.py`. The information boundary in `fullgame.py`, the runner, the
  pricing and the ledger are not tuning surfaces. Fix them only for real defects, and
  record each fix here.
- Commit before every run; the runner refuses uncommitted source and prompt changes.
- Judge a change by outcomes (floor reached, wins), not by how good the reasons sound.
  With a handful of runs a night, report each run individually and do not call small
  differences improvements. Compare variants on the same seeds where possible, knowing
  the model itself is stochastic.
- Log every change below with the mistake that motivated it and the runs before and after.

## Log

### 2026-10-12: harness smoke test

Before building, a 28-question knowledge probe of Luna (scratch evidence, not committed)
found that it knows most common cards, relics, potions and debuffs. It got several
details wrong: Searing Blow's damage (6, not 12); Gremlin Nob's Bellow (it said +3
Strength rather than Enrage, which punishes Skills); and Hexaghost's opening (it put
Divider on turn 1, not after Activate). Elite and boss mechanics are the likeliest
knowledge gap.

`runs/llm-smoke-20261012-a`, seed `LUNASMOKE1`, scaffolding v1, source `3df5c0b`.
The run lost on act 1 floor 6 to Lagavulin, with score 36: 76 decisions, 61 model calls,
$0.0137 and 276 s in total. Calls took 1.2–7 s each, and prompts were about 760 input
tokens. Neow, map, events, combat with potions, combat and card rewards, the elite fight
and the death screen all ran without a protocol gap. No shop, rest site, boss, chest or
card-selection grid was reached.

Mistakes seen, with candidate scaffolding for each:

1. **Under-blocking.** Against Lagavulin's 18-damage attacks the model spent energy on
   attacks in three turns (HP 58→40→27→9). Candidate: show the visible incoming total
   against current block in the state.
2. **Unused scaling.** Demon Form sat in hand on turn 3 and on the no-damage debuff turn
   7, and the model never played it. Candidate: general guidance on setting up powers in
   long fights. This is strategy advice; prefer the state fix first.
3. **Woke a sleeping elite** with two Strikes on turn 1. It is a knowledge gap;
   candidate: elite and boss notes.
4. **Risky route.** It traded Burning Blood for a random boss relic (Black Star), took a
   curse for gold, never reached a shop with 332 gold, and took the floor-6 elite at
   58/74 HP with an almost-starter deck.
5. **Notes clobbered.** The model rewrote its notes on 31 of 61 calls, mostly copying
   them unchanged. In the elite fight it replaced the run strategy with turn-level combat
   chatter. Candidate: separate a per-combat scratchpad from the run notes, or tighten
   the notes instruction.

### 2026-10-12: first baseline attempt and harness fixes

`runs/llm-luna-v1-dev-20261012`, seed `RUNDEV1`, source `3df5c0b`. This was the strongest
play so far: the model took a random rare card (Corruption) at Neow, then shopped, rested,
collected the Ruby and Sapphire keys, beat Lagavulin and reached act 1 floor 14 at 77/80
HP ($0.030, 149 calls, 770 s). The run then hung, and was interrupted by hand after 190 s
without a reply. It is not a scored attempt.

- **Hang.** In Bonfire Spirits' purge grid the model chose a card and was shown the
  confirm view. CommunicationMod keeps a single chosen card in a hover slot and reports
  `selected_cards: []`, so the prompt read "Selected: none", and the model chose
  `cancel`. In that view, cancel only un-hovers the card; CommunicationMod sees no state
  change and never sends a reply ([ChoiceScreenUtils](https://github.com/ForgottenArbiter/CommunicationMod/blob/5e417eb189530986b9047a3c9426889fb261d146/src/main/java/communicationmod/ChoiceScreenUtils.java)).
  Fix: `cancel` is no longer offered in a grid's confirm view (so `confirm` is forced), and
  the empty "Selected" list is no longer rendered. Any other silent command still ends the
  run when the bridge times out. That timeout now defaults to 300 s, and each API attempt
  is limited to 60 s.
- **Missing room type.** After a floor-13 Spike Slime (L) fight the model wrote "Act 1
  Slime Boss defeated" in its notes; the boss was still ahead. The combat state now says
  whether the fight is a monster, elite, boss or event combat, as the game shows.

Both fixes change what the model sees, so later runs are scaffolding v1.1.
