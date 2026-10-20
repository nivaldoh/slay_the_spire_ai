# The Empire set

Started on the night of 2026-10-20 under the owner's delegation (away until 11:00):
explore a larger range of battles instead of perfecting one, use small battles to
understand units and larger ones to test an army as a robot team, and specialize in
**Empire** units so the collected traces can later train an Empire specialist. Other
factions stay for specific challenges (the [chariot card](tactic-cards.md#the-chariot-card-the-first-benchmark-card)).
Everything here is unverified under the [hard rule](../../AGENTS.md#verification-hard-rule):
no check is agreed, and every rate rests on the launch count beside it.

## Why one faction

- One faction keeps the training data coherent: the same unit types, abilities and
  counters recur across scenarios, so a fine-tuned model sees many situations for few
  unit types instead of few situations for many.
- Empire has every role in the base game: line infantry (Swordsmen, Spearmen,
  Halberdiers, Greatswords), guns (Handgunners, Crossbowmen), artillery (Great Cannon,
  Mortar, Helblaster), cavalry (Knights, Pistoliers, Outriders) and casters. Its
  guns and artillery make lines of fire and protection real problems, which the owner's
  robot-team question needs.
- The enemy varies (Greenskins, Dwarfs, Bretonnia, mirror Empire), so the player's side
  is fixed and the opponents give the variety.

## The set

Scenarios with Empire on the player's side, from `configs/twwarhammer3/scenarios.json`
(player defends unless marked attacks; very hard AI, modifier 1.0 unless marked; 0.75
scale; 1200 s timer unless marked). Results per controller: `twwarhammer3 stats`.

| Size | Scenario | Question | Known before tonight (launches) |
|---|---|---|---|
| 1 unit | `emp-knights-grn-arrers-spears` (attacks), new | which target a cavalry unit charges past a spear screen | none |
| 2 units | `emp-handgunners-grn-savage-orcs`, `-hard` (1.1) | keep a firing lane past the spearmen (the riflemen card) | at 1.0 attack-nearest won (1); at 1.1 attack-nearest lost (1), FlankLane 1 of 2 |
| 2 units | `emp-handgunners-grn-wolves-boyz`, new | which unit meets which of a fast and a slow threat | none |
| 2 units | `emp-helblaster-brt-raiders` | protect a Helblaster from riders | hold lost (1); Bodyguard 5 of 8; GLM 0 of 1 and one policy failure |
| 2 units | `emp-knights-emp-swordsmen-2` | hammer and anvil against two Swordsmen | attack-nearest won (1): too easy at two, too hard at three |
| 2 units | `emp-wizard-emp-swordsmen`, `-hard` | spell timing with scarce magic | attack-nearest lost (2); SpellWindow 5 of 6; FireballSpam won (2) |
| 3 units | `emp-handgunners-dwf-warriors-3` (attacks) | two gun units and a spear unit against shielded Dwarfs | attack-nearest lost (1); Crossfire 0 of 6 |
| 7 v 7 | `emp-line-grn-raid`, new | the robot-team question: who guards what, who fills a gap, when the knights commit | none |
| 20 v 20 | `emp-pitched-grn-20` (attacks, 2400 s) | do the small skills survive forty units and a long history | attack-nearest lost at 523 s (1) |

`emp-battery-skv-evacuation` (escort two cannons to a zone) stays deferred.

### The line battle, `emp-line-grn-raid`

Seven Empire units receive seven Greenskin units on Taurox, both sides without lords:
Halberdiers, two Swordsmen, a Spearmen reserve, two Handgunners and Empire Knights
against two Orc Boyz, Big 'Uns, Goblin Spearmen, Arrer Boyz, Goblin Wolf Riders and
Boar Boyz. It is the first concrete test of the
[robot-team plan](robot-team-plan.md): the AI's riders and boars go for the guns, its
infantry hits the line, and infantry units break and leave gaps. The decisions a
controller must keep making are which unit guards what, when the reserve fills a gap,
and when the knights spend their charge. Compared with the Skaven expendables battle
the plan proposed, this one has several places where a teammate's loss changes another
unit's job, and the data is Empire.

What to look at in a battle (replay and `digest --units`): when each infantry unit first
routed, whether the reserve moved toward that gap before the enemy came through, whether
the guns kept firing after the riders arrived, and what the knights charged. None of this
is scored yet; a signature comes after the floors and screens say the battle is worth it.

Two disclosed scripted controllers were written during the night (branch `wh3-line-team`,
merged after the queue) as the first two arms of the
[robot-team comparison](robot-team-plan.md#what-to-compare): `LineTeam` keeps fixed
jobs (the line in guard mode where it deployed, the guns 30 m behind it with skirmish
off shooting cavalry first, the reserve waiting behind the centre, the knights waiting
until an enemy cavalry unit comes within 120 m, then charging it, then the archers, then
the weakest engaged enemy); `LineTeamReserve` adds one rule: when a line unit is seen
routing, the reserve attacks the enemy infantry nearest to where that unit stood. Their
rules are in their cards (`battle/calibration.py`); one offline test each. Unplayed until
the second queue.

## Tonight's plan (2026-10-20, 02:37 to about 09:30 local)

Queue `runs/twwarhammer3/calibration/empire-20261020/plan.json`, frozen at `4fefd1c`,
17 single-episode launches in this order: floors on the three new scenarios (`hold` and
`attack_nearest` on the line and wolves battles, `attack_nearest` and `rush_nearest` on
the knights battle); GLM-5.3 low on `llm_rules` v21 on eight Empire scenarios (the line
battle twice); Kimi K3 low on the line battle; Qwen3.6 (no reasoning) on the 20 v 20.
Paid jobs stop the WH3 OpenRouter ledger at $22.50 (it held $12.49 at the start; the
account had $44.57 of credit). No prompt, code or executor change: `llm_rules` v21 and
harness b42 as on `main`, so every model row pools with the b40 cohort's conditions.

Reading rules fixed before the results: a floor win marks a new scenario "too easy" and
its next step is a stronger enemy (modifier 1.1 or one unit up); a model win is reviewed
in the replay before it is called anything; no rate from these single launches is a
comparison between models.

## Decisions taken for the owner's review

1. **Empire on the player's side for all new scenarios**, enemies varied. The existing
   non-Empire cards keep their results and are not rerun tonight.
2. **Lordless armies in the line battle**, as in the small cards, to avoid a lord's
   morale aura and death confounding the first look. A general-led variant is a later
   step and a real part of the game (the leader as a team member whose loss changes
   everything).
3. **The Skaven expendables feasibility step of the robot-team plan is deferred**; the
   Empire line battle takes its place as the first handover test, since it holds several
   handover situations and produces Empire data.
4. **Model screens before calibration.** The owner asked for breadth, so the new
   scenarios get one GLM launch each tonight even before their floors are read; a floor
   win still marks the scenario too easy and the model row is then only data.
5. **`llm_rules` (objectives and interface, no tactics) for every model battle**, as in
   the chariot cohorts, so prompt knowledge is held constant across scenarios. The
   tactical `llm` prompt may give better demonstrations; that is a separate comparison.
6. **Spend cap $10 tonight** on the shared OpenRouter allowance (owner, 2026-10-18:
   spend carefully); Qwen3.6, the cheapest model, takes the 20 v 20.
7. **A defender's timer win is not a contact win.** The engine awards the line battle to
   the player when its units are still standing at 1200 s, so a floor can "win" by
   surviving a stalemate (attack_nearest did). For the team question the outcome of
   record is the contact win (every enemy unit routed or destroyed before the timer), as
   the chariot card already reads it (`cards.outcome`); timer wins are reported beside it.

## Risks

- A seven-unit lordless army may rout in a cascade once its first unit breaks (the
  commander flag sits on a card the lobby chooses); the floors show whether the battle
  lasts long enough for any handover to matter.
- The AI may not split its army (riders to the guns, infantry to the line); if it comes
  as one block, the battle is a plain line fight and the team question needs another
  enemy mix.
- `hold` may win the line battle on contact with the default deployment: then the
  enemy steps up and tonight's model rows are easy-battle data.
- Costs of four Greenskin cards are unread (no database schema on this machine); funds
  carry headroom, so recruitment should pass, and the lobby refuses otherwise before
  any battle is scored.
- Missile units start with skirmish mode on, so against fast cavalry a passive gun unit
  runs instead of shooting (the wolves `hold` floor). A floor's result therefore depends
  on the default toggles; the prompt shows the toggles, and the model can change them.
- Single launches say almost nothing about rates; they say whether a setup works and
  what a battle looks like.

## Results

Filled in as the queue runs (one launch each unless stated; `review.py --units` in the
plan folder prints the table and the per-unit times); the log entry
[b43](log.md#2026-10-20-the-empire-set-harness-b43) keeps the counts.

- **Line battle, `hold`: lost at 327 s** (54% of its men left, enemy 79%). The AI split
  its army as hoped: Wolf Riders and Boar Boyz charged the line at 151-153 s, the four
  infantry units arrived at 186-194 s. The line beat the riders (routed at 186 s) and cut
  the boars to 15 of 45, then the infantry wave broke every line unit between 240 and
  245 s; both gun units were caught in melee at 200-215 s after 73-75 rounds each and
  routed at 210-227 s; the idle knights fought from 238 s and routed last. So the guns
  barely fired and the knights were never used: the battle does pose the team question.
- **Line battle, `attack_nearest`: engine "won" on the timer at 1205 s**, with 13% of its
  men left against 17%: not a contact win. Every unit walked at its nearest enemy; the
  knights hit the Wolf Riders at 99 s and both enemy cavalry units were routed by 125 s
  (3 and 1 riders left); the guns fired 950 and 1,090 rounds; both Orc Boyz units ended
  with 1 and 5 men. But the Spearmen, one Swordsmen unit, the knights and both gun units
  were destroyed, and from about 850 s the last Swordsmen unit chased shattered goblins
  while the Big 'Uns (42 men, never engaged after 850 s) wandered: a stalemate the timer
  rule hands to the defender. The two floors together say the battle is neither trivial
  nor hopeless: meeting the cavalry early and using the knights mattered, and the
  remaining question is whether a controller can finish it by contact.
- **Wolves battle, `hold`: lost at 245 s, and the Handgunners fired no round** (ammo
  1,496 at the end). The trace shows why: the guns start with skirmish mode on, so when
  the Wolf Riders came inside about 150 m at 149 s the unit turned and ran (bearing 138
  to 317, "moving, running" at 161 s) instead of shooting, the riders caught it at 173 s
  and it routed at 189 s; the Spearmen stood idle 20 m away until the Boyz hit them at
  190 s. In the line battle the same guns fired 73-75 rounds because the cavalry charged
  the line first. So in this battle the default toggles decide the floor: a controller
  must turn skirmish off or put the spears between the guns and the riders before it
  gets any shots, which is the two-threat decision the scenario was written for.
- **Wolves battle, `attack_nearest`: lost at 456 s.** Attack orders override the
  skirmish retreat: the guns fired 280 rounds before the riders reached them at 195 s and
  576 in all, and the riders were routed at 146 s with 3 of 60 left. Then the Orc Boyz
  beat the Spearmen (routed at 302 s, 13 of 90 left) and the guns (routed at 456 s, 39
  left) while losing 57 of 90 men. Both floors lost, by different routes (no shots; shots
  but no screen), so the battle is open for a controller that keeps the spears between
  the Boyz and the guns while the guns shoot.
- **Knights battle, `attack_nearest`: won by contact at 371 s**, so this step is too easy:
  the knights charged the Goblin Spearmen head-on at 250 s and routed them by 294 s (1 of
  120 left) with 29 of 45 knights, then rode down the archers (routed at 371 s). The spear
  screen does not hold 0.75-scale goblins against knights. Next step, after the queue:
  Orc Boyz in place of the goblins (`emp-knights-grn-arrers-boyz`), floors first again.
- **Knights battle, `rush_nearest`: lost at 122 s.** Running, the knights hit the same
  goblins at 79 s under arrow fire, lost the rider carrying the commander flag at about
  110 s ("Lord recently died" took the morale fraction from 0.68 to 0.30) and routed at
  122 s with 29 of 45 alive while the goblins had 107 of 120. One floor wins, the other
  loses within two minutes: the roster sits on the floors' edge, and the commander flag
  on the only unit is a built-in morale shock (design rule 8 of the tactic cards).
- **Line battle, GLM-5.3 low (`llm_rules` v21), launch 1: lost at 455 s** ($0.23, 76
  decisions, order age p50 5.0 s, 4 refused orders, all on routing units). Its plan read
  well at first: guard mode on the four line units and the knights pulled behind the line
  at 5 s; guns on the Wolf Riders and Boar Boyz at 129 s; the knights counter-charged the
  riders at 134 s (routed at 159 s, 1 of 60 left). Then it sent the 45 knights into the 75
  Big 'Uns at 159 s (the knights routed at 213 s with 11 left), kept both gun units on the
  Boar Boyz long after they were down to 8 riders, and gave the line units one attack
  order each at 178-197 s. The Spearmen reserve was spent at 178 s like any line unit, and
  the first order after the first friendly rout (213 s) came at 282-395 s: retreat moves
  for the guns and then the line. So: the early team decisions were the right kind, the
  knights' second target and the guns' target choice were the losses, and no handover
  happened. Guns fired 118 and 242 rounds before their first melee (the hold floor: 73-75).
- **Riflemen card at 1.1, GLM-5.3 low, launch 1: lost at 520 s** ($0.28, 159 decisions,
  age p50 3.0 s, 4 refusals, all "unreachable" moves). It sent the Spearmen at the Savage
  Orcs at 132 s and turned the guns' skirmish mode off at 150 s, which is the right
  setting for shooting; the Spearmen routed at 264 s. From then on it kited the guns by
  hand: 60 move orders about every 3 s along the west edge and then east across the map,
  and a unit that is always moving does not fire. The guns fired 218 rounds in all, were
  caught at 442 s and routed at 506 s with the orcs at 47 of 90. The same lesson as S2:
  hand-kiting with 3 s order age loses to the engine's own skirmish, and the model did
  not alternate halts with moves.
- **Wolves battle, GLM-5.3 low, launch 1: lost at 367 s** ($0.19, 101 decisions, age p50
  3.3 s). This time the two-threat plan was executed: Spearmen in guard mode, the guns
  placed behind them at 5 s and ordered onto the riders at 161 s (239 rounds before any
  melee), the riders broke on the spears at 196 s (23 of 60 left), the guns switched to
  the Boyz at 174 s. The Orc Boyz still beat the Spearmen (41 of 90 left at the end) and
  reached the guns at 249 s (routed at 290 s), ending with 32 of 90 men. Both floors and
  this plan left the Boyz at about a third: one Orc Boyz unit may simply be too strong
  for a Spearmen unit plus one gun unit at this scale, so the battle may need a step down
  (a weaker slow threat) rather than a better plan. No witness exists yet to say.
- **Knights battle, GLM-5.3 low, launch 1: lost at 450 s** ($0.21, 115 decisions, age
  p50 3.6 s). The model played the card's intended tactic: it charged the archers first
  (contact at 84 s), pulled out at 96 s, charged them again at 124 s, then cycled against
  the goblin spears five more times between 155 and 389 s with long rides between, and
  lost with 15 of 45 knights while the goblins kept 120 of 120 and the archers 60 of 68.
  The walking floor had won the same battle by grinding. So on this roster the "correct"
  cavalry play loses to the naive one: the 0.75-scale goblins do not break to charges,
  and each pull-out costs riders. The harder step (Orc Boyz for the goblins) tests
  whether grinding stops working before cycling starts to.
- **Helblaster battle, GLM-5.3 low, launch 1: lost at 212 s** ($0.10, 48 decisions, age
  p50 3.9 s). The escort was moved and put in guard mode at 5-10 s and the gun told to
  shoot one Yeomen unit; the other Yeomen unit reached the gun at 69 s after 31 rounds,
  and the gun routed at 117 s. The halberds routed one Yeomen unit (142 s) and then lost
  to the Men-at-arms (212 s). As in every S4 battle so far, the gun fell: the escort cannot
  be in front of two rider units at once, and the gun gets about a minute of fire.
- **Hammer and anvil (two Swordsmen), GLM-5.3 low, launch 1: won by contact at 382 s**
  ($0.19, 101 decisions, age p50 3.3 s, no refusals). The first model contact win on a
  small Empire scenario: the Swordsmen pinned one enemy unit from 85 s, the knights
  charged the other at 82 s, pulled out at 103 s and 176 s and charged again (routed at
  276 s), then hit the pinned unit, which routed at 382 s; 21 of 45 knights and 55 of 90
  swordsmen left. The walking floor had also won this step (2026-10-17), so it is still
  "too easy" as a card; as data it is a clean hammer-and-anvil demonstration.
- **Wizard battle, GLM-5.3 low, launch 1: lost at 314 s** ($0.16, 59 decisions, age p50
  4.2 s, 4 refusals: two on routing units, one unreachable point, one item ability the
  unit does not support). It cast from 91 s (four Fireballs, Piercing Bolts, Flaming
  Sword on the Spearmen, The Burning Head, four bound blasts, two fire cloaks) but let
  the second Swordsmen unit reach the wizard at 191 s and then ordered the lone hero
  to melee it; wizard and Spearmen routed together at 314 s with the enemy at 61 and 74
  of 90. The scripted SpellWindow (5 of 6 wins) keeps the wizard out of contact; the model
  did not.
- **Lines of fire (three Dwarf Warriors), GLM-5.3 low, launch 1: lost at 319 s** ($0.13,
  51 decisions, age p50 5.4 s). Skirmish off at 81 s and both gun units on targets; they
  fired 209 and 319 rounds, and the three Dwarf units lost 1, 0 and 2 of 75 men: frontal
  fire into shields and heavy armour does nothing, which is the card's point. The Dwarfs
  reached the guns at 146 s; the model then marched every unit away across the map until
  all three routed (184-278 s). Nine launches of three controllers have now lost this
  step; no play has yet put a shot into a Dwarf flank.
- **Line battle, Kimi K3 low (`llm_rules` v21), launch 1: lost at 349 s** ($0.55, 108
  decisions, age p50 2.7 s, no refusals). Guard mode on every unit and skirmish off at
  5 s; the knights counter-charged the Wolf Riders at 142 s (routed at 170 s); then it
  sent the line units out of the line at the Boar Boyz (155-210 s) and later at whatever
  was nearest, moved the reserve twice and finally away from the fight (325 s), and the
  line broke between 259 and 349 s with 55% of its men left against 66%. The guns fired
  142 and 375 rounds before melee. Like GLM: the opening was right, the knights' first
  charge was right, and there was no plan for the infantry wave or the reserve.
- **20 v 20, Qwen3.6-35B without reasoning, launch 1: lost at 523 s** ($0.05, 20
  decisions, order age p50 18.4 s, 60 refused orders, 54 of them on routing units). The
  40-unit prompt works, and the battle shows what scale does to a single blocking model:
  each reply lists an order for every unit (about 20 orders), so a reply takes about
  22 s of model time against 2-4 s on the small battles, and the order age is set by the
  reply length, not by thinking. The model marched the whole army forward from 39 s and
  into the Orc line at 328 s, where five infantry units routed on contact (first melee
  and first routing in the same second) and the rest within two minutes; the guns fired
  16-203 rounds, the artillery 2-9. Enemy 88% left. An early argument for a planner that
  assigns jobs and an executor that writes the unit orders, and the same 523 s that the
  walking floor lasted on this battle (2026-10-17).
- **Line battle, GLM-5.3 low, launch 2: lost at 432 s** ($0.23, 77 decisions, age p50
  5.1 s). The same shape as launch 1: the line tidied and put in guard mode by 12 s, the
  knights on the Wolf Riders at 105 s (routed at 181 s) and then on the Boar Boyz, where
  they died (0 of 45 by 216 s); skirmish off on the guns only at 216-237 s; the line units
  then given attack orders one by one; 51% of its men left against 65%. Both GLM line
  launches lost the knights to the second cavalry unit and never used the reserve.

**First queue done at 05:01**: 17 launches, $2.30 (GLM-5.3 $1.70 on 9 battles, Kimi
$0.55, Qwen $0.05); WH3 OpenRouter ledger $14.79. Model contact wins: 1 of 12 (GLM on
the two-Swordsmen hammer and anvil, a step the walking floor also wins).
