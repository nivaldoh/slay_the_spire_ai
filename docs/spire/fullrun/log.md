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

## 2026-10-12: v7 on the three development seeds

`runs/fullrun/llm-luna-v7-dev-20261012-b`, source `5020fef`, all three seeds; the first
replay of one version on the same seeds.

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV1 | lost | 1 / 16 | 2x Spike Slime (M), Acid Slime (M) (boss) | 234 | 189 | $0.040 | 831 s |
| RUNDEV2 | lost | 2 / 33 | The Collector (boss) | 460 | 394 | $0.090 | 1,664 s |
| RUNDEV3 | lost | 1 / 16 | 2x Spike Slime (M), Acid Slime (M) (boss) | 224 | 194 | $0.043 | 850 s |

- RUNDEV1 lost to the Slime Boss on floor 16, turn 12 (80 → 10 HP over the fight; v6 on
  this seed reached floor 29 and entered the boss at 75 HP, left it at 50). On the F2 shop
  it removed a Strike (75g) where v6 bought Feel No Pain, while holding Corruption. In the
  boss fight it played Corruption+ on turn 5 "to make skills free" and then spent its
  last Defends on turns 6 and 8 against no incoming damage; Corruption exhausts them, so
  from turn 9 it drew no block and took 16, 8, 8 and a lethal 16. Potions went in the
  F8 elite (Fear, Heart of Iron) and an F11 hallway (Explosive). Flags: three turns ended
  with energy and a playable card (F3, F8, F16 turn 6), no card rewards skipped. Nothing
  shown says what Corruption does; the card-keywords candidate covers only Ethereal.
  v7 differs from v6 only by The Collector note, which this run never showed, so the gap
  between floors 29 and 16 on RUNDEV1 is the model's own variance. Both took the same
  Neow rare (Corruption) and route; the first non-combat divergence is the F1 card reward
  (Thunderclap here, Armaments in v6), then the F2 shop.
- RUNDEV2 lost to The Collector on floor 33, in the enemy turn after turn 15, with The
  Collector at 38/282 (the earlier v7 run won this fight and died on floor 50). It entered
  at 53/53 HP with no potions (earlier: 61/61 and a Power Potion), having drunk its Energy
  Potion, held "for the Collector", against a Snecko on F31. The rules note was in all 42
  F33 prompts and the model focused The Collector (244 HP lost against 156 for the Torch
  Heads, mostly area damage). Two costly turns: on turn 4 it played Metallicize, Feel No
  Pain and Disarm against the heads' 20 damage, "no damage to block" on the debuff turn
  (41 → 27); on turn 11 it held both Apparitions "for a dangerous turn", they exhausted
  as Ethereal, and turn 12's 39 damage took it from 29 to 8. Ethereal is invisible in the
  hand, the same failure as the earlier run's Awakened One. Flags: five turns ended with
  energy and a playable card, the F31 card reward reopened and skipped six times.
- RUNDEV3 lost to the Slime Boss's split slimes on floor 16, turn 11 (v6 on this seed
  beat the boss and reached floor 42). Its first prompt hashes match v6's; the first
  divergence is the F0 map pick (x=1 toward a shop here, x=2 toward events in v6), so this
  too is the model's variance. It reached the boss at 80/80 with no upgrades and one
  potion (v6: three upgrades, Inflame, three potions), having drunk an Energy Potion at
  80/80 on F10 with 2 energy left unspent and an Explosive Potion on a lone slime on F11,
  against its own notes. On turn 1 it chose Twin Strike and Clothesline on Gambling Chip's
  screen "to play them", which discards them (the hand-select purpose candidate), and
  played Reaper on the single boss for 4, exhausting it before the split. Slam hit for 33
  on turn 3 with no Defend in hand.

Same scaffolding, same seeds: floors 16, 33 and 16 here against 29, 50 and 42 for the
same prompts' earlier runs (v6 on RUNDEV1 and RUNDEV3, v7 on RUNDEV2). On RUNDEV1 and
RUNDEV3 the runs part at an early non-combat choice (F1 and F0), so one run per seed cannot
rank versions by floor. Judge the next versions first by their targeted flags, and treat
floors as a noisy outcome.
Evidence added to the candidates: Ethereal invisible again (RUNDEV2), Corruption's exhaust
rule unknown (RUNDEV1), Reaper's exhaust unknown and Gambling Chip's discard misread
(RUNDEV3).

## Scaffolding v8: skipped card rewards named on the reward screens

Evidence: the reopen loop survived v6's system prompt line (43 skips in v6 RUNDEV3, 20 of
them on F24, where the history showed only "skip this card reward"; six on F31 in this
v7 RUNDEV2 run). Change, in `llm.py`: after the model skips a card reward, that floor's
reward and card screens add "Card rewards you skipped on this floor (reopening one shows
the same cards): …" with the cards offered. Target: card-reward reopens near zero in the
flags; floors are not expected to move.

## 2026-10-12: v8 on the development seeds

`runs/fullrun/llm-luna-v8-dev-20261012`, source `f36176b`.

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV1 | lost | 3 / 50 | Deca, Donu (boss) | 782 | 700 | $0.169 | 3,113 s |
| RUNDEV2 | lost | 4 / 54 | Spire Shield, Spire Spear (elite) | 955 | 869 | $0.208 | 3,641 s |
| RUNDEV3 | lost | 1 / 16 | Acid Slime (L) (boss) | 238 | 211 | $0.047 | 892 s |

- RUNDEV1 lost to Donu and Deca on floor 50, turn 2 (score 524), this seed's furthest run
  (v6: 29, v7: 16). It escaped the F29 Colosseum at 44 HP where v6 fought on and died. On
  F37 it took Mind Bloom's "I am Awake" (upgrade all cards, no more healing) at 80 HP,
  "enough to forgo future healing", with 13 floors left; the F41 elite (77 → 33) and F42
  Spire Growth (33 → 12) losses then stood, the F47 and F49 rest sites healed nothing, and
  it entered the boss at 12/76. It drank Liquid Memories, kept "for the boss", on F48, and
  twice played Corruption+ before Second Wind+ (F42 turn 4, F50 turn 1), halving Second
  Wind's block. Skip line: one reopen, on F22, where the model reopened the skipped reward
  "to inspect the cards", skipped the same three again and left; on F39, F42 and F48 the
  line appeared and it left without reopening. Flags: six card rewards skipped, five turns
  ended with energy and a playable card.
- RUNDEV2 reached Act 4, the first run to do so, and died on floor 54 to Spire Shield and
  Spire Spear on turn 6 (10 HP, 14 block, against Smash for 54). It beat Awakened One on
  F50 (47 → 18 HP, 12 turns): the first form died on turn 8 with the player at full HP,
  after Reaper+ healed and two Apparitions gave Intangible, and Twin Strike finished the
  second form. Keys: Emerald from a burning Gremlin Nob (F13), Sapphire from a chest (F26),
  Ruby by Recall at F49. It took five Apparitions from Council of Ghosts on F29 (max HP
  94 → 47); they carried both bosses, but Act 4 began at 50 max HP against Smash turns of
  57 (turn 3, 50 → 12 HP) and 54. In that fight it paired Apparitions "to extend
  Intangible", covering turns 1–2 and 4–5 but neither Smash turn, and it had smithed two
  Apparitions believing the upgrade grants two turns of Intangible (it removes Ethereal,
  which the hand does not show). Skip line: one skip, on F45, and no reopen. Flags: 15
  turns ended with energy and a playable card; Sozu from F34 meant no potions.
- RUNDEV3 lost to the Slime Boss on floor 16, turn 12, killed by an untouched Acid Slime
  (L) at 4 HP. It took Recall (Ruby Key) on F15 instead of resting and entered at 61/80
  with one upgrade and two potions, having drunk three potions it had said it was keeping
  for the boss in F10 and F12 hallways. On Gambling Chip's screen it discarded cards it
  meant to play in six fights (F7, F10–F13, and boss turn 1, where Offering and Bash+
  went unplayed); v6 played Offering on turn 1 and split the boss before any Slam. Slam
  hit for 27 on turn 3. On turn 4 it played Spot Weakness against a debuff intent and
  stopped the boss at 74, "just above its split threshold". The rules notes appeared as
  intended. No card reward was skipped.

Skip line: one reopen in three runs (RUNDEV1 F22), against 43 skips on four floors in v6
RUNDEV3 and six reopens on F31 in v7 RUNDEV2; the line appeared on five floors and the
model left four of them without reopening. Keep v8. Floors were 50, 54 and 16 against v7's
16, 33 and 16 on the same seeds; v8 is not expected to change floors, and the RUNDEV1 and
RUNDEV2 gains are within the variance the v7 replay showed. Hand-select purpose now has
the clearest recurring evidence: RUNDEV3 has misread Gambling Chip's screen in v6, v7 and
v8.

## Scaffolding v9: card keywords

Evidence: Ethereal Apparitions exhausted unplayed in both v7 RUNDEV2 runs, and v8 RUNDEV2
upgraded Apparitions believing the upgrade adds Intangible (it removes Ethereal). Change:
cards in the hand, piles, deck and shop show the engine's `ethereal` and `exhausts` flags,
as in "Apparition (1 skill, ethereal, exhausts)", and the system prompt gains one line on
what the two keywords do. Power rules (Corruption) are not covered.

## 2026-10-12: v9 on the development seeds (incomplete)

`runs/fullrun/llm-luna-v9-dev-20261012`, source `005083f`. The job stopped after an
infrastructure failure on RUNDEV2; RUNDEV3 was not played.

| Seed | Outcome | Act / floor | Killed by | Decisions | Calls | Cost | Wall time |
|---|---|---|---|---:|---:|---:|---:|
| RUNDEV1 | lost | 2 / 29 | 2x Slaver, Taskmaster (elite) | 493 | 427 | $0.099 | 2,024 s |
| RUNDEV2 | unsupported_or_invalid | 3 / 38 | (settings screen opened; see below) | 582 | 511 | $0.120 | 2,326 s |

- RUNDEV1 lost to the Slavers elite on floor 29, turn 5 (4 HP, Entangled, 22 incoming;
  earlier runs on this seed: 29, 16 and 50). On the F26 map it chose an elite path "to
  pursue the Emerald Key", which it had taken on F23, and opened the F26 chest "for the
  Sapphire Key", taken on F7; the path forced the Gremlin Leader (F27, 80 → 62 HP and
  three potions) and the fatal Slavers. **Harness gap:** CommunicationMod 1.2.1 never
  sends `keys` (no raw message in the v8 and v9 traces has it), so the allowlisted field
  and its "Keys:" line never appear, and the model knows its keys only from its notes,
  which dropped the Emerald Key on F25. Two other false beliefs cost HP: it bottled Dark
  Embrace in Bottled Tornado "without duplicating the already-bottled Demon Form+" (no
  power was bottled), and on F29 turn 2 it took 25 trusting a Fossilized Helix Buffer
  spent on turn 1 (the powers line showed only Dark Embrace). No Ethereal card appeared;
  every reason that named exhaust was sound (Slimed, True Grit on Wounds, Dark Embrace
  draws). Flags: four turns ended with energy and a playable card, one card reward
  skipped, no reopen.
- RUNDEV2 stopped on floor 38 (Act 3, turn 4 against a Writhing Mass, 91/104 HP) as
  `unsupported_or_invalid`, not a gameplay outcome. After `play 3 0` the game reported
  `screen_name` `SETTINGS` with `is_screen_up` true, so CommunicationMod offered only
  `key`, `click`, `wait` and `state`. The owner confirmed an accidental Escape press on the
  game window; the runner then stopped the run and closed the game, as designed. It is not
  a loss. A runner fix could close the settings screen with a logged key press and
  continue. The run had beaten The Collector
  and had no Apparitions, so v9's keywords were not tested on Ethereal cards in either run.

v9 is not judged: one finished run, no Ethereal card in play. Replay it on all three seeds.

## 2026-10-12: shared gameai package and a leaner harness (no scaffolding change)

To let other games reuse the model code, the OpenAI transport, prices, spend reservation and
reply-retry loop moved to `gameai/llm.py` (`Model.ask`), and the ledger and provenance to
`gameai/`. Full-run jobs fingerprint only `src/gameai`, `src/spire`, `configs/llm` and the
lock files, so edits elsewhere no longer stop a job. The runner loop, decision builder and
engine package were simplified (engine 1,153 → 739 lines). Checks:

- Replaying all 30 saved traces through `LLMPolicy` with their recorded replies gave
  byte-identical prompts, request bodies, ledger reservations and charges, choices and
  totals, also with injected invalid replies; `digest`, `watch`, `stats` and the rebuilt
  `results.csv` were unchanged.
- Smoke run `runs/fullrun/smoke-gameai-20261012` (source `1a24d2f`, RUNDEV1, 40-action
  cap): truncated on floor 3 as intended after 28 calls ($0.005); manifest and result keys
  match the previous smoke run, and no game process remained.
- The `--version` flag is gone. The trace no longer writes the `terminal` and `result`
  events, which repeated `result.json`.

## Scaffolding v10: hand-select purpose, and a runner fix for the settings screen

Evidence: a hand selection reads only "Choose up to N card(s) from your hand", whatever
asked for it. Gambling Chip's start-of-combat discard was misread as a play or a block: v6
RUNDEV3 discarded Impervious+ "to block", v7 RUNDEV3 discarded Twin Strike and
Clothesline "to play them", and v8 RUNDEV3 did the same in six fights, discarding Offering
and Bash+ on the Slime Boss's turn 1. Change (`llm.py`): on a hand selection, one line
names its source when the trace shows it: the card or potion played just before on the
same floor and turn, else Gambling Chip on turn 1. Replaying the saved traces with their
recorded replies adds the line to all 385 hand-select prompts (226 Gambling Chip, 112
cards, 47 potions) and changes no other prompt.

Runner fix (`play.py`, not scaffolding): an Escape press on the game window opens the
settings screen, where CommunicationMod offers only `key`, `click`, `wait` and `state`
(v9 RUNDEV2 stopped there). The runner now sends `key cancel`, up to three times, and
continues. Not yet seen against the engine; if the game does not close the screen, the
run stops as before.

## 2026-10-13: v10 on the development seeds (stopped by a WSL restart)

`runs/fullrun/llm-luna-v10-dev-20261013` (source `54a5967`): RUNDEV1 reached floor 10 with
60 HP, then the bridge connection reset (`[Errno 104] Connection reset by peer`) when the
WSL virtual machine restarted at 04:36 UTC; the run is an infrastructure failure and the
autoresearch session that ran it ended with the VM. RUNDEV2 and RUNDEV3 were not played.
v10 remains untested.

## 2026-10-17: open models through OpenRouter, exchange capture and `spire export` (no scaffolding change)

Owner goal (away): review the preparation for post-training, check data collection,
prepare fine-tuning an open model with OpenRouter and run a minimal test in both games.
The cross-game pipeline is on [posttraining.md](../../posttraining.md); the WH3 side is
harness b24 ([WH3 log](../../twwarhammer3/log.md#2026-10-17-queue-e1-harness-b24-and-post-training-data-capture)).
Prompts and scaffolding are unchanged (v10), but the trace format and the request change,
on `main` at `87b370b`:
- `spire play --provider openrouter` plays OpenRouter models against their own ledger,
  `runs/spire-openrouter-spend.jsonl`. The model and effort are checked before the job
  directory exists. Qwen3.6-35B-A3B, the open-weight model to fine-tune, is declared with
  efforts `none` and `medium` (on/off).
- Exchange capture, as WH3 b14: each model request writes a `model_exchange` event with its
  prompt, every attempt's request body and output items (reasoning text from open models;
  OpenAI requests now ask for reasoning summaries), and a failed request's error. The
  manifest gains `model_exchange_version`, the behavior metadata `provider`, and attempts
  the served model, backend and wall time. Before, a policy failure kept no prompt and an
  API error lost its billed attempts. `digest`, `watch` and `stats` ignore the new events.
- Shared transport: a failed upstream response is resent unchanged; a reply cut at the
  output limit gets a cut-off notice; a body truncated during the read is retried.
- The reply parser retries off-schema replies (a string, bool or float choice, missing
  keys, a non-object). Before, they ended as infrastructure failures or, for `true`,
  silently chose candidate 1. OpenAI's strict mode prevented them; OpenRouter backends do
  not guarantee it.
- `spire export` (`fullrun/export.py`): every model request with exact prompts, attempts,
  reasoning, the choice, public per-fight labels (won, HP at start and end) and the run
  outcome. The 33 existing runs export to 11,167 rows (gpt-6-luna/low, one attempt each,
  no reasoning recorded, no hash mismatch). Those rows are OpenAI outputs, which the
  dataset builder leaves out by default until the owner decides the terms question.

Comparability: every run so far is Ironclad unlock level 3, and the profile is 81 points
from level 4, whose new cards and relics change the pools. The next scored run will
likely cross it; exports record the level per run.
