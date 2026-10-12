# Full-run log

Append-only record of the [full-run track](README.md): every scaffolding version, the
mistake that motivated it, the runs before and after, and the decision. Job directories
are under `runs/fullrun/`; `python -m spire digest <job>` prints a job's per-seed table.

## 2026-10-12: harness smoke test

Before building, a 28-question knowledge probe of Luna (scratch evidence, not committed)
found that it knows most common cards, relics, potions and debuffs. It got several
details wrong: Searing Blow's damage (6, not 12); Gremlin Nob's Bellow (it said +3
Strength rather than Enrage, which punishes Skills); and Hexaghost's opening (it put
Divider on turn 1, not after Activate). Elite and boss mechanics are the likeliest
knowledge gap.

`runs/fullrun/llm-smoke-20261012-a`, seed `LUNASMOKE1`, scaffolding v1, source `3df5c0b`.
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

## 2026-10-12: first baseline attempt and harness fixes

`runs/fullrun/llm-luna-v1-dev-20261012`, seed `RUNDEV1`, source `3df5c0b`. This was the strongest
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

## 2026-10-12: v1.1 baseline on the development seeds

`runs/fullrun/llm-luna-v1.1-dev-20261012`, source `fea677a`, seeds `RUNDEV1`–`RUNDEV3`. Each run
was played once by a stochastic model, so these are single samples. Neow options are
fixed by the seed: `RUNDEV1` showed identical options in two runs after different
previous runs.

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV1 | lost | 1 / 16 | Slime Boss | 248 | 200 | $0.039 | 738 s |
| RUNDEV2 | lost | 2 / 33 | The Collector | 475 | 444 | $0.101 | 1,755 s |
| RUNDEV3 | lost | 1 / 16 | Slime Boss (split slimes) | 194 | 165 | $0.033 | 670 s |

- RUNDEV1 reached the Slime Boss at 72/80 HP with a Corruption and Feel No Pain deck. It
  then **ended turns 10 and 11 with 3 energy and attacks in hand**, "without crossing
  Slime Boss's 70-HP split threshold", and died to Slam. This is the same kind of rules
  error as waking Lagavulin in the smoke run.
- RUNDEV2 beat Gremlin Nob, Lagavulin, Hexaghost and Book of Stabbing, and reached The
  Collector at 104 HP. It lost an 11-turn fight with a 29-card deck that had never removed
  a card. After Mega Debuff (Weak, Vulnerable and Frail 3) it took 28–35 per turn.
- RUNDEV3 beat Lagavulin and reached the Slime Boss at 71 HP. It died to the split
  slimes at 15 HP after spending its last turn's energy exhausting Slimed instead of
  blocking 18 incoming damage.
- The notes said the potions were saved for the boss, but the model used them earlier.
  Its stated plans are not reliable evidence of its later play.

## Scaffolding v2: enemy rules notes

Evidence: Lagavulin woken early (smoke run), the Slime Boss split stall (RUNDEV1), and the
knowledge probe's errors on Gremlin Nob and Hexaghost. Change: `configs/llm/monsters.json`
holds a short, A0-accurate rules note for each Act 1 elite and boss: Gremlin Nob,
Lagavulin, Sentry, Slime Boss, The Guardian and Hexaghost. A note appears under "Enemy
rules" only while that enemy is in the fight. Amountless powers no longer render as
"Corruption -1". Add notes for later acts only when runs show they are needed, and check
every number against the game.

## 2026-10-12: v2 on the development seeds

`runs/fullrun/llm-luna-v2-dev-20261012`, source `e0b47aa`. These are single stochastic samples,
like v1.1. The opening of RUNDEV1 repeated v1.1 almost choice for choice (same Neow pick,
route, card and shop buys), so same-seed comparisons are less noisy early than feared.

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV1 | lost | 1 / 16 | Slime Boss (last Acid Slime (M), at 7 HP) | 267 | 217 | $0.050 | 1,020 s |
| RUNDEV2 | lost | 2 / 24 | Snecko | 435 | 387 | $0.085 | 1,888 s |
| RUNDEV3 | lost | 2 / 33 | The Champ | 546 | 497 | $0.113 | 2,389 s |

- The targeted mistakes stopped. On RUNDEV1 and RUNDEV3 the model pushed the Slime Boss
  through its split on purpose ("crosses the split threshold, starting both slimes at lower
  HP"), and RUNDEV3 beat it for the first time. Both Lagavulin fights used the sleeping
  turns for setup without waking it early. The note's "attacks for 18 twice" was read as a
  single 36-damage turn, so v3 rewords it.
- RUNDEV1 died at 1 HP on boss turn 17, one block short, with the last slime at 7 HP. It
  had taken an Explosive Potion "for the Slime Boss split", repeated that plan on the next
  two floors, then used it on floor 10 against two small slimes. v1.1 did the same with
  the same potion on the same seed.
- RUNDEV2 died at 7 HP to a Snecko on 15 HP with Vulnerable. Perfected Strike would have
  killed it and Defend would have survived. It played Disarm "to reduce Snecko's
  multi-hit damage enough to survive", which left a single exactly lethal 7-damage hit.
  Earlier, after a floor-22 hallway fight, it wrote "Proceed from the Collector rewards"
  and took an elite at 27 HP. In one shop it bought Ancient Potion, discarded it at once
  to buy Skill Potion, then discarded that on the map screen (123 gold lost), and bought
  no card removal with 474 gold.
- RUNDEV3 ended its last Champ turn into 24x2 with Fairy in a Bottle, "the Fairy can
  revive me after his lethal attack", spending 2 energy on Inflame and Twin Strike
  rather than Defends. The first hit used the Fairy (24 HP) and the second killed it.
- Decision: keep v2. Floors went from 16/33/16 to 16/24/33; RUNDEV2's regression came in
  Act 2 hallways the notes do not touch.

## Scaffolding v3: incoming damage against block and HP

Evidence: every v2 death ended in survival arithmetic (one block short, a single hit
read as multi-hit, a multi-hit read as one lethal hit), and the costly-turn scans of
v1.1 and v2 show attacks played while Defends stay in hand and 10–35 damage comes in.
Change: combat states add one line, "Incoming attack damage this turn: N, against your
B block and H HP.", summing the visible attack intents of live enemies. Hidden intent
damage (Runic Dome) is left out. The Lagavulin note now says "Attack (one hit of 18) on
two turns in a row".

## 2026-10-12: v3 on the development seeds

`runs/fullrun/llm-luna-v3-dev-20261012`, source `7171bd8`.

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV1 | lost | 1 / 16 | Slime Boss (Acid Slime (L)) | 254 | 208 | $0.047 | 1,047 s |
| RUNDEV2 | lost | 2 / 33 | The Collector | 490 | 425 | $0.094 | 2,042 s |
| RUNDEV3 | lost | 1 / 16 | Slime Boss (split slimes) | 199 | 172 | $0.035 | 804 s |

- The model reads the new line: "against the 32 incoming damage", "the 24 incoming
  damage". RUNDEV1 lost 7 HP to Lagavulin (v2: 23) and entered the boss at 71 HP (v2: 56),
  but then ran out of damage. After the split it never attacked the Acid Slime (L)
  (65 → 61 HP in 12 turns) and spent energy cycling Slimed for Feel No Pain block.
- RUNDEV2 reached The Collector again and beat Hexaghost for 2 HP. On floor 20 it took
  Council of Ghosts (5 Apparitions for 40 max HP), then spent a rest site on the Ruby Key
  at 33/40 HP before the boss.
- RUNDEV3 made the same Neow pick as v1.1 and v2 (lose all gold, remove 2 cards), then
  removed two more Strikes at events and skipped most fights, reaching the boss with 11
  cards. It handled the split well, using Explosive Potion after crossing 70 HP so both
  Large slimes started at 54, but died one block short on turn 11.
- Two deaths were again exact or near-exact lethal (RUNDEV1 at 10 HP with 6 block against
  16; RUNDEV3 at 23 HP with 12 block against 36), so the targeted arithmetic mistake did
  not stop. Costly turns (at least 8 unblocked damage) were 9, 14 and 7 against v2's 9,
  15 and 11.
- Decision: keep v3, as cheap context the model uses; with these samples it shows no
  measurable effect on outcomes (floors 16/33/16 against v2's 16/24/33).

## 2026-10-12: grid deselect fix

On RUNDEV3's Neow removal grid, every v1.1–v3 run chose the first of five identical
"select Strike" choices again after selecting it, which only deselects it: 1, 7 and 4
wasted calls. A grid card that is already selected is now labeled "deselect …". This is a
`fullgame.py` (now `fullrun/decisions.py`) defect fix, so later runs carry it.

## Scaffolding v4: the act boss's floor

Evidence: the "Which fight is the boss" candidate of the time; v3 RUNDEV1 again played the floor-13
Spike Slime (L) as "the slime boss" and drank Heart of Iron against a Slaver "while
helping in the upcoming boss fight". Change: the header reads "Act 1, floor 13. Act boss:
Slime Boss, on floor 16." (floors 16, 33 and 50 for Acts 1–3) instead of naming the boss
alone.

## 2026-10-12: v4 on the development seeds

`runs/fullrun/llm-luna-v4-dev-20261012`, source `5136609` (v4 and the grid fix).

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV1 | lost | 1 / 16 | Slime Boss (split slimes) | 263 | 239 | $0.054 | 1,252 s |
| RUNDEV2 | lost | 2 / 33 | The Collector | 452 | 377 | $0.087 | 1,856 s |
| RUNDEV3 | lost | 3 / 41 | Giant Head (elite) | 835 | 808 | $0.172 | 3,739 s |

- The targeted mistake stopped. Hallway combat reasons that treat the fight as the act
  boss went from 2, 4, 1 and 2 in RUNDEV1's runs (v1–v3, all in the floor 12–13 slime
  fight) to 0, on the same floor-13 Spike Slime (L) fight. RUNDEV2 stayed at 0.
- The header change also flipped RUNDEV1's Neow pick (random rare card in v1.1–v3, now
  +16 max HP), so a prompt edit can perturb choices it was not aimed at; seeds stay
  comparable only up to their first divergent decision.
- RUNDEV1 entered the boss at 96/96 HP and still lost. After the split it held back
  damage on purpose: "Both slimes are above their split thresholds, so avoid dealing
  damage and end the turn" (11 such reasons over turns 7–10). The v2 boss note is shown
  only while the Slime Boss lives, and the Large slimes had none, so the v1.1
  misconception came back. It also spent four potions in the floor 13–14 hallways.
- RUNDEV2 died to The Collector on exactly lethal damage, reasoning that Defend would let
  it "survive this turn, even if only at 0 HP". Across the 11 deaths since v1.1, four
  ended with unblocked damage exactly equal to the remaining HP.
- RUNDEV3 is the first run to reach Act 3. It beat the Slime Boss and The Champ, lost
  almost no HP in the Act 2 hallways, and died to Giant Head on floor 41 while refusing
  to drink Ancient Potion, "reserved for Time Eater", on every turn. It opened and
  skipped the same card reward 17 times after a floor-22 fight and 19 times after a
  floor-35 fight, because a skipped card reward stays on the rewards screen (39 skips and
  36 reopenings in the run, about a tenth of its calls).
- Decision: keep v4.

## Scaffolding v5: Large slime split notes

Evidence: v4 RUNDEV1's split-slime stall above, and the same stall on the Slime Boss
itself in v1.1. Change: rules notes for `AcidSlime_L` and `SpikeSlime_L`. Each says that
at half its max HP its next move is Split into two Medium slimes with its HP at that
moment, that holding back damage never avoids the split, and that damage before its turn
still lowers both Mediums (killing it first prevents the split). The notes also show in
hallway fights with Large slimes.

## 2026-10-12: v5 on the development seeds

`runs/fullrun/llm-luna-v5-dev-20261012`, source `b564305`.

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV1 | lost | 2 / 29 | Colosseum Slavers (event fight) | 501 | 422 | $0.097 | 2,183 s |
| RUNDEV2 | lost | 2 / 23 | Book of Stabbing (elite, left at 4 HP) | 340 | 301 | $0.066 | 1,402 s |
| RUNDEV3 | lost | 1 / 16 | Slime Boss (split slimes) | 253 | 214 | $0.048 | 1,167 s |

- The targeted mistake stopped: no reason in any v5 run holds back damage to stay above
  a split threshold. Instead: "push the Acid Slime well below its split threshold", "Deal
  damage before the Spike Slime splits, reducing the HP of both resulting slimes", and
  "Iron Wave … triggers its split".
- RUNDEV1 beat the Slime Boss for the first time in five versions (80 → 9 HP), on the
  same Corruption opening as v1.1–v3. It died on floor 29, where a "?" room was the
  Colosseum and its forced Slaver fight started at 26 HP after Byrd and Chosen.
- RUNDEV2 and RUNDEV3 diverged from v4 by floors 2–7, before any Large slime appeared, so
  their lower floors are the model's own variance. RUNDEV2 has now reached floors 33,
  24, 33, 33 and 23 across versions.
- Decision: keep v5.

## Scaffolding v6: death at 0 HP and skipped card rewards

Evidence: the "0 HP is death" and "Skipped card rewards" candidates of the time. Change: two
lines in the system prompt's state description: "You die when your HP reaches 0, so to
survive a turn the damage that gets past your block must be less than your HP", and "A
skipped card reward stays on the rewards list; choose proceed to leave it." The second
is an interface fact the screen does not show.

## 2026-10-12: v6 on the development seeds

`runs/fullrun/llm-luna-v6-dev-20261012`, source `e26f649`.

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV1 | lost | 2 / 29 | Colosseum Gremlin Nob and Taskmaster (event) | 476 | 377 | $0.084 | 1,603 s |
| RUNDEV2 | lost | 2 / 33 | The Collector | 524 | 480 | $0.109 | 2,204 s |
| RUNDEV3 | lost | 3 / 42 | Transient | 675 | 644 | $0.142 | 2,678 s |

- No v6 death was exactly lethal; the final unblocked damage exceeded the remaining HP
  by 23, 11 and 29, against four exact-lethal deaths in eleven before. Three runs cannot show
  more than that.
- The skipped-reward line did not stop the loop. RUNDEV3 reopened the same Cleave /
  Clothesline / Searing Blow+1 reward 20 times on floor 24 ("assess whether any option
  meaningfully improves the deck") and 16 times on floor 39 (43 skips in the run). The
  model knows the reward stays; it does not remember that it already looked.
- RUNDEV1 beat the Slime Boss again (75 → 50 HP). In the floor-29 Colosseum it took the
  optional second fight at 58 HP ("[VICTORY] A powerful fight with many rewards" over
  "[COWARDICE] Escape") and died to Gremlin Nob and Taskmaster.
- RUNDEV2 reached The Collector at 48 HP after again trading 50 max HP for five
  Apparitions (Council of Ghosts, as in v3). In all four Collector fights so far the model
  dealt more damage to the Torch Heads, which are minions it revives, than to the boss:
  117 vs 108 (v1.1), 156 vs 116 (v3), 138 vs 89 (v4) and 206 vs 82 (v6).
- RUNDEV3 is the furthest run yet. It beat The Champ in 5 turns for 10 HP, then took an
  Orb Walker event fight at 84 HP (left at 25) and died to a Transient on floor 42. At
  that fight's start, Gambling Chip's "Choose up to 99 card(s) from your hand" screen has
  no stated purpose, and the model selected Impervious+ "to block the Transient's full 30
  damage", which discarded it.
- Decision: keep v6 (floors 29/33/42, the best so far, with the usual caveats).

## Scaffolding v7: The Collector rules note

Evidence: the damage split above. Change: a note for `TheCollector`, with every number
checked against the saved fights: 282 HP; two Torch Heads (about 40 HP, Tackle 7) on turn
1; Mega Debuff (3 Weak, 3 Vulnerable, 3 Frail) on turn 4; otherwise Fireball 18, a buff
(15 block, and 3 Strength to it and each Torch Head) or Revive. Torch Heads are minions,
so killing The Collector ends the fight. Only RUNDEV2 reaches it, so v7 was played on
RUNDEV2 alone to finish before the session's end.

## 2026-10-12: v7 on RUNDEV2

`runs/fullrun/llm-luna-v7-dev-20261012`, source `df231dc`, RUNDEV2 only.

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV2 | lost | 3 / 50 | Awakened One (Act 3 boss) | 862 | 719 | $0.172 | 3,420 s |

- The targeted mistake reversed. The model aimed its attacks at The Collector, "the only
  enemy whose defeat ends the fight", and dealt it 236 damage against 89 to the Torch
  Heads (earlier fights: 82–116 against 117–206). It won in 13 turns at 61 → 23 HP, the
  first Collector win in five attempts on this seed.
- It then cleared Act 3's hallways and died to Awakened One on floor 50 after 14 turns,
  the furthest any run has gone (score 506).
- This is one sample on one seed. Keep v7; the next session should replay all three
  seeds with it.

## Overnight summary, 2026-10-12

Seven scaffolding versions ran between 02:28 and 11:04 local time for $1.45 of API spend
(ledger total $1.67 of the $25 cap). Best floors per seed went from 16/33/16 (v1.1) to
29 (v5, v6), 50 (v7) and 42 (v6). Changes that removed a recurring, run-ending mistake:
the Slime Boss note (v2), the boss's floor in the header (v4), the Large slime notes (v5)
and The Collector note (v7). The incoming-damage line (v3) is used but showed no
measurable effect, and v6's 0-HP line coincided with the end of exact-lethal deaths in
three runs. Two harness defects were found and one fixed: the grid deselect labels, and
the skipped card reward that stays listed (still open).


## 2026-10-12: harness check after the repository reorganization

`runs/fullrun/smoke-reorg-20261012`, seed `RUNDEV1`, source `d0ad9f4`, scaffolding v7 with
`--max-actions 40`. The code moved into packages (the Windows scripts now deploy from
`src/spire/engine/`) without changing what the model sees. The run deployed and launched
the game, played Neow, the map and two hallway fights, and stopped as `truncated` on floor 3
at 75/80 HP: 37 decisions, 27 calls, $0.0047, 125 s. It is a harness check, not a scored
attempt; its Neow pick (a random rare card) matches v1.1–v3 on this seed.

## 2026-10-12: shared modules for the open-weight track

`fullrun/decisions.py` moved to `spire/decisions.py`, and the spend ledger (`Ledger`,
`BudgetExhausted`) moved from `fullrun/api.py` to `spire/ledger.py`, so the open-weight
skeleton uses them without depending on this track's OpenAI client. The code is unchanged
and so is what the model sees: later commits still play scaffolding v7, and the ledger
file is still `runs/llm-spend.jsonl`.

## 2026-10-12: a leaner review loop

The owner asked for a loop that uses less of Claude Code's context. The overnight session's
transcript showed where its context went: 413k tokens by the end, about 59% of the growth
from tool output and notifications. Digest output was half of all tool output (full-run
views of 10–30 KB). 39 one-off trace scans written as inline scripts added both their code
and their output. Polling took about 50 calls: Monitor expires after 30 minutes, so it was
re-armed 13 times, and background wait loops repeated its events.

Changes, none of them to what the model sees (later commits still play v7):

- `spire digest <run>` prints floors, flags and final notes: 2.4 KB for v7 RUNDEV2's
  50-floor run, against 30 KB before. `--picks` restores the per-floor choices and reasons.
  `--floor N` prints the state once per turn and at its end, not on every card: v7's
  Awakened One fight went from 15.0 to 10.1 KB, most of it the model's reasons.
- The flags reproduce the log's hand counts: v6 RUNDEV3's 43 card reward skips (20 on F24,
  16 on F39), v2 RUNDEV2's exactly lethal Snecko hit (7 against 0 block and 7 HP), v6's
  final-turn margins of 23, 11 and 29, and v1.1 RUNDEV1's six Slime Boss turns ended with
  energy and a playable card.
- `spire watch <job>` returns once per finished run, stall, job end or refused start. It
  replaces Monitor, the wait loops and the progress checks.
- The loop in [README.md](README.md) reviews each finished run in a fresh subagent and
  keeps only its review, writes findings straight into this log, updates `state.md` once
  per loop, and drops the manual preflight, which `spire play` and the engine already
  enforce.

A check of the review subagent on the saved v7 RUNDEV2 run (91k subagent tokens, 14 tool
calls, 3 minutes; about 600 tokens returned) matched this log's v7 entry and found two
things the hand review missed. The model did not know the Awakened One revives: it spent
its last resources killing the first form at 21 HP. And the hand never shows Ethereal:
`decisions.card_text` renders name, cost and type, while the trace marks the cards
`ethereal`. Both are now candidate changes.
