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
scale; 1200 s timer unless marked). Results per controller: `twwarhammer3 stats`, whose
Won column counts the line floor's timer stalemate as a win (`review.py` in the plan
folder and the cards' outcome separate contact wins from timer wins).

| Size | Scenario | Question | Known before tonight (launches) |
|---|---|---|---|
| 1 unit | `emp-knights-grn-arrers-spears` (attacks), new | which target a cavalry unit charges past a spear screen | none |
| 2 units | `emp-handgunners-grn-savage-orcs`, `-hard` (1.1) | keep a firing lane past the spearmen (the riflemen card) | at 1.0 attack-nearest won (1); at 1.1 attack-nearest lost (1), FlankLane 1 of 2 |
| 2 units | `emp-handgunners-grn-wolves-boyz`, new | which unit meets which of a fast and a slow threat | none |
| 2 units | `emp-helblaster-brt-raiders` | protect a Helblaster from riders | hold lost (1); Bodyguard 5 of 8; GLM 0 of 1 and one policy failure |
| 2 units | `emp-knights-emp-swordsmen-2` (attacks) | hammer and anvil against two Swordsmen | attack-nearest won (1): too easy at two, too hard at three |
| 2 units | `emp-wizard-emp-swordsmen` (attacks), `-hard` (attacks, 1.1) | spell timing with scarce magic | attack-nearest lost (2); SpellWindow 5 of 6; FireballSpam won (2) |
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
is scored yet; a scoring rule comes after the floors and screens say the battle is worth it.

Two disclosed scripted controllers were written during the night (branch `wh3-line-team`,
merged after the queue) as the first two arms of the
[robot-team comparison](robot-team-plan.md#what-to-compare): `LineTeam` keeps fixed
jobs (the line in guard mode where it deployed, the guns 30 m behind it with skirmish
off shooting cavalry first, the reserve waiting behind the centre, the knights waiting
until an enemy cavalry unit comes within 120 m, then charging it, then the archers, then
the weakest engaged enemy); `LineTeamReserve` adds one rule: when a line unit is seen
routing, the reserve attacks the enemy infantry nearest to where that unit stood. Their
rules are in their cards (`battle/calibration.py`). After the night, b46 made the guns,
reserve and knights keep their targets, stopped the knights' recall mid-melee and
reworded the reserve card to what the code does; the revised arms are unplayed.

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
   Found afterwards (2026-10-20, recounted from the traces): the model prompt still tells a
   defender "if time runs out, you win" (`battle/llm.py:300`). 16 of the night's 29 model
   launches had that line, all seven line-battle launches among them, and models acted on
   it (Kimi, line launch 2: "Defender, timeout wins. Hold defensive line."). Those rows
   were told one goal and scored on another. The owner ruled on 2026-10-21 ([directions](../owner-direction.md)):
   tell the models, and paid screens on defender cards wait for that version. The smallest
   version of the change (approved, not made yet): a scenario field naming
   contact scoring, and for it `render_mode` writes "if time runs out, the game gives you
   the battle, but this benchmark counts only routing or destroying every enemy unit
   before the timer" in place of "if time runs out, you win"; prompt fixtures regenerate, a
   logged prompt version. `render_mode` builds the state line of `llm`, `llm_rules` and
   `commander` alike, so one logged change covers all three and bumps both the `llm` and
   the `commander` label in `controllers.VERSIONS`, as `llm` v20 / `commander` v7 did. The
   alternative, counting timer
   wins, changes `cards.outcome`, which now scores a timer win as lost, and would count the
   3 timer wins already in the register. Recount the same day
   (`runs/twwarhammer3/away-20261021/timer_mentions.txt`):
   on five defending battles (the line at ranks 0 and 5, expendables, rifle lane, two
   threats) 16 of 17 model episodes restate the timer win in
   their replies (7 of 8 on the two defending starting cards), in 11-97% of their decisions
   (GLM's rank-5 line win in 82%). Stated
   reasons are leads, not evidence of an effect on the outcome (evaluation guideline 8.3).

## For the owner to decide

1. **The rank-5 line battle as the first team card.** Its floors lost and the fixed plan
   won by contact once; the replacement-rule arm nearly won. Proposed next (2026-10-21):
   the [starting set](tactic-cards.md#the-starting-set-proposal-2026-10-21)'s $0 screen
   (every floor including `rush_nearest`, and LineTeam b46 at 0 s, 3 launches each), then
   its named shortcut and confirmation before any model screen; and
   whether to keep the rank-5 step or to drop the Boar Boyz instead.
2. **What the line battle measures.** A contact win is the outcome of record (decision
   7); the handover reading (first order after the first friendly rout, rounds before a
   gun's first melee, who the knights charged) is printed by the review script but not
   scored. Agree a signature before any admission claim.
3. **Kimi's cost.** Per line battle Kimi cost $0.55, $1.47 and $0.63 (rank 5) against
   GLM's $0.23, $0.23, $0.44 and $0.58 (rank 5); per decision $0.0041-0.0060 against
   GLM's $0.0026-0.0030, 1.4 to 2.3 times. The $1.47 launch was the longest model battle
   of the night (925 s, 245 decisions), not a dearer model. Keep Kimi for a few launches on
   cards GLM cannot win, or drop it.
4. **Backend anomalies.** The second wizard launch lost on garbled replies from the
   pinned Decart backend (its Results entry) and is scored as GLM's loss; decide whether
   a screen reports and reruns such launches, and at what threshold. The numbers that
   separate it: 622.6 s of model time over 7 calls (`llm.seconds` over `llm.calls` in
   `result.json`), 88.9 s a call, against 1.6-5.8 s in the other 27 GLM and Kimi
   launches (Qwen on the 20 v 20: 18.7 s, from its 20-order replies); its longest reply
   took 178.5 s, the longest anywhere else 52.6 s. The digest's delay mean (56.8 s)
   misses the call still in flight at the end; the Results entry has the cut-off retry.
   Over every recorded model episode (296, 6,819 completed replies; 2026-10-21,
   `runs/twwarhammer3/away-20261021/garbled_all.txt`), a reason over 300 characters marks 9
   replies in 5 episodes: 8 garbled Decart replies in 4 GLM launches of this night, two of
   them wins (the second hammer-and-anvil and wolves launches), and one coherent
   314-character Qwen reason.
   Rerunning flagged launches would discard those two wins. An independent hunt by other
   signals (script mix, junk words, word salad, symbols, whitespace runs;
   `runs/twwarhammer3/away-20261021/garbled-hunt/`) found 15 garbled attempts in 6 jobs. The
   300-character rule catches 8 and misses 7: three completed replies in
   `bench-b19-s4-glm-20261017` (Decart and Baidu, with short, unreadable or missing reasons)
   and four incomplete attempts (two of them in that battle's episode 1 "no valid reply"
   forfeit, one in the wizard battle, one a Step 5 whitespace flood). It also lists 26 GLM
   repetition loops: 16 completed replies repeating one order 5-151 times and 10 incomplete
   attempts whose text repeats. Since GLM-5.3 was pinned to Decart (b36, 2026-10-19), 4 of
   its 45 episodes had a garbled reply, all in the Empire night's 25 (0 of the 20 chariot
   battles before it); the first GLM screen inherits that backend unless it is re-pinned.
5. **The 20 v 20.** One launch each of Qwen and GLM worked technically; order age (Qwen
   18 s) and per-decision cost (GLM) both argue for a planner-executor harness before more
   large battles; the owner's harness-comparison direction (2026-10-18) fits here.
6. **Export.** All model battles of the night are exportable (`twwarhammer3 export`), 29
   model episodes, every one Empire on the player's side; whether to build the first
   Empire dataset now or after the cards settle. The export has no content screen, so
   the seven accepted garbled Decart replies (three in the second wizard launch, one in
   the second hammer-and-anvil launch, two in the second wolves launch, one in the GLM
   20 v 20) would enter a dataset as targets. A trial build in
   `runs/twwarhammer3/review-20261020/` kept all seven among 3,110 rows, and three (from
   the two won launches) among the 965 rows of a won-only build. A content screen on the
   reply, not a reply-time cutoff (four of the seven came back in 11-53 s), must be
   agreed before any dataset is built. Measured 2026-10-21
   (`runs/twwarhammer3/away-20261021/reply_screen.py`): "the reply's reason is over 300
   characters", the harness's own reason cap, flags exactly the seven among the export's
   3,113 replies; 40 spaces in a row flags six of them. The same rule could flag serving
   faults in a report (item 4). It is not general: on other nights it misses garbage with
   short reasons (item 4's hunt).

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
- A pinned OpenRouter backend can degrade mid-battle: GLM-5.3 on Decart returned
  garbled replies (gibberish reasoning and reason text, the JSON spread over whitespace)
  in four launches: four at 120-178 s in the second wizard launch, which lost without
  orders, and four accepted at 11-53 s in three launches that played on (two of them
  won). The harness scores the wizard launch as the model's loss; a screen of several
  launches must say how many were played on sound replies.

## Results

One launch each unless stated. The rows are in `docs/twwarhammer3/results.csv`;
`review.py --units` in the plan folder (`runs/twwarhammer3/calibration/empire-20261020/`)
prints the table and the per-unit times; the log entry
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
  caught at 442 s and routed at 506 s with the orcs at 47 of 90. The same lesson as the
  hand-kite card against Slayers: hand-kiting with 3 s order age loses to the engine's
  own skirmish, and the model did not alternate halts with moves.
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
  to the Men-at-arms (212 s). As in every Helblaster battle so far, the gun fell: the
  escort cannot be in front of two rider units at once, and the gun gets about a minute
  of fire.
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
  all three routed (184-278 s). Eight launches of three controllers have now lost this
  step (the walking floor, `Crossfire` 0 of 6, GLM); no play has yet put a shot into a
  Dwarf flank.
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
$0.55, Qwen $0.05); WH3 OpenRouter ledger $14.79. Model contact wins: 1 of 11 (GLM on
the two-Swordsmen hammer and anvil, a step the walking floor also wins).

Second queue (b44, from 05:02):
- **Line battle, `LineTeam` (fixed jobs), launch 1: lost at 592 s**, 22% of its men left
  against 36% (the longest contact battle on this scenario; hold 327 s, the models
  349-455 s). The opening held: guns 216 and 263 rounds before melee (hold: 73-75), the
  knights counter-charged the Boar Boyz at 150 s and both enemy cavalry units were routed
  by 237 s (3 and 1 riders left), but the knights died doing it (0 of 45 by 228 s, the
  infantry wave arriving at 177-192 s on top of them). The line in guard mode fought from
  155 s and broke between 299 and 381 s, taking the Big 'Uns to 17 (routed at 405 s) and
  the goblins to 44 (routed at 523 s); the reserve engaged at 338 s under its 25 m rule
  and lasted to 490 s. Defect seen: the guns' "nearest in range" rule flipped targets
  (41 and 43 orders, 5-7 targets each); b46 gave them a kept-target rule like
  `Bodyguard`'s, unplayed since. Fixed jobs are not enough: the knights need a rule that keeps
  them off a fresh cavalry unit while the infantry wave is arriving, or a second charge
  target that is not the boars.
- **Line battle, `LineTeamReserve` (replacement rule), launch 1: lost at 392 s**, 40%
  left against 52%. The rule fired as written: the first line unit was seen routing at
  344.8 s and the reserve's attack on the Boyz nearest its position went out in the same
  decision; but the other two line units broke within 30 s (356 and 375 s), so the
  reserve (80 of 90 men at the end) replaced one unit of a line that no longer existed.
  The knights again went wolves, boars, archers and were down to 6 by 240 s. Seven
  launches on this battle and no contact win: before more model launches the battle
  needs a step that a sound fixed plan can win. Proposed step: the same rosters with the
  player's units at experience rank 5 (`emp-line-grn-raid-xp5`), the smaller step the
  owner named on 2026-10-19 and the b41 check verified at battle start; floors first.
- **Knights battle, harder step (Orc Boyz for the goblins), floors: both lost.** Walking
  (`attack_nearest`) lost at 453 s: the knights ground the Boyz down to 1 of 90 (routed at
  291 s) and then lost the melee with the archers from 304 s, ending with 11 of 45 against
  35 of 68 archers. Running (`rush_nearest`) lost at 130 s, routing with 25 of 45 after
  53 s of melee against the fresh Boyz (66 of 90 left). So on this step neither naive play
  wins, and the archers-first, cycle-against-the-Boyz play is what remains to test.
- **Knights battle, harder step, GLM-5.3 low, launch 1: lost at 124 s** ($0.07, 46
  decisions, age p50 2.4 s). It charged the Boyz first (contact at 78 s), switched to the
  archers at 88 s with a pull-out move, and the unit routed at 124 s with 35 of 45 riders
  alive: the same morale collapse as the running floor (the commander flag sits on the
  only unit, so one rider's death is a "lord died" shock). On the easier step the model
  had played archers-first; here it did not.
- **Line battle, GLM-5.3 low, launch 3: lost at 569 s** ($0.44, 164 decisions, age p50
  3.1 s), the closest model battle on this scenario: it tidied the line and set guard
  mode by 16 s, kept the guns out of melee for the whole battle (476 and 571 rounds), had
  the knights charge the Boar Boyz at 132 s and the line units pick targets as the wave
  arrived, and routed four of the seven enemy units (riders 183 s, boars 278 s, both Boyz
  345-352 s, goblins 363 s). The Big 'Uns (33 of 75 left) and the archers then broke what
  was left of the line at 449-453 s, and from 477 s the model rode the surviving knights
  (19) around the map edge instead of charging the Big 'Uns' rear. Enemy 42% left.
- **Line battle, Kimi K3 low, launch 2: lost at 925 s** ($1.47, 245 decisions, age p50
  3.0 s, 58 refusals, 53 of them unreachable points). Guard mode and skirmish off at 5 s,
  the knights on the Boar Boyz at 144 s, the Spearmen reserve sent at the Wolf Riders at
  161 s; the enemy cavalry was routed by 261 s and the archers at 333 s, the guns fired
  646 and 457 rounds. Then the line broke at 351-376 s and from 380 s the model ran the
  guns and knights to the western map edge with move orders every 3-4 s (114 accepted
  moves at x -470 to -511, inside the -512 edge; of the 58 refusals, 31 were unreachable
  points inside the map, 16 out-of-bounds runs east to x 520-620 at 657-813 s, 6 into
  the blocked south-west corner and 5 to routing units), until the guns were caught at
  387 s and 536 s. Enemy 43% left. $1.47 for 925 s and 245 decisions (owner item 3 compares
  the cost per decision); the ledger read $16.78 after this one.
- **20 v 20, GLM-5.3 low, launch 1: lost at 732 s** ($0.88, 167 decisions, order age
  p50 3.6 s, 10 refusals). GLM replies in about 2 s with a few orders per reply (unlike
  Qwen's 20), so it decided every 3-4 s on a 40-unit prompt; the first 84 s cost $0.13 and
  projected to $4-6, so a watcher was set to interrupt the job at a $19.50 ledger, but
  decisions slowed as the battle went on and it finished on its own at $0.88. The battle:
  the whole infantry line met the Orc line at 265-280 s and every line unit routed between
  352 and 373 s (the general at 418 s), while the guns fired 274-566 rounds each, the
  Pistoliers shot 990 of 1,080 rounds and the enemy cavalry, trolls and Rock Lobber were
  routed; enemy 47% left against Qwen's 88% and the walking floor's 61%. Per-decision
  cost at scale is a second reason, after order age, for a planner-executor split.
- **Line battle, `LineTeam` (fixed jobs), launch 2: lost at 381 s**, 43% left against
  58%: the same course as launch 1 but faster (both enemy cavalry units routed by 216 s,
  the knights down to 5 by 336 s, the line broken 321-354 s, the guns 213 and 158 rounds
  before melee). Two launches, 592 and 381 s: the fixed plan does not win this battle.
- **Line battle, `LineTeamReserve`, launch 2: lost at 499 s**, 29% left against 38%.
  Three enemy units routed (goblins 306 s, both Boyz 390-399 s) and the reserve went in
  at 377 s, nine seconds after the first line rout; the Big 'Uns (38) and the untouched
  archers (68) finished the rest. The knights again died by 234 s. Two launches each for
  both scripted arms, four losses: on this roster the fixed plan and the one-rule plan
  both fall to the second cavalry unit plus the Big 'Uns, which is why the rank-5 step
  comes next.
- **Wolves battle, GLM-5.3 low, launch 2: won by contact at 295 s** ($0.21, 115
  decisions, age p50 2.1 s, no refusals): the first model contact win tonight on a
  scenario whose floors both lost. Spearmen in guard mode and the guns placed behind
  them at 5 s, skirmish off at 11 s; the guns shot the riders from 141 s and the riders
  broke on the spears at 169 s (35 of 60 left); the guns switched to the Boyz (256 rounds
  in all, never in melee, 68 of 68 men), and the Boyz routed at 295 s with 46 of 90 while
  the Spearmen kept 47 of 90. The same plan GLM played in launch 1 (lost at 367 s), so
  the scenario sits near this plan's edge: GLM 1 of 2, floors 0 of 2 (all unverified).
- **Riflemen card at 1.1, GLM-5.3 low, launch 2: lost at 237 s** ($0.19, 118 decisions,
  age p50 1.8 s). This time it left skirmish on (it even re-enabled it at 5 s) and only
  moved the Spearmen; the guns fired 119 rounds before the orcs reached them, the
  Spearmen routed at 204 s, the guns at 237 s with the orcs at 76 of 90. GLM 0 of 2 on
  this card by two different routes (hand-kiting, then no plan at all).
- **Wizard battle, GLM-5.3 low, launch 2: lost at 526 s with 5 decisions** ($0.16): a
  backend failure, not a tactic. The first three replies took 1.6 s; from the fourth the
  Decart backend returned corrupted output: gibberish reasoning, reason and notes text,
  the JSON spread over whitespace (13-49% of the text), no orders, each reply taking
  120-178 s, and one cut at the 16,000-token output cap after 162 s and retried: the
  retry re-sent the same prompt, took 178.5 s and $0.04 and landed about 104 s after the
  battle ended, discarded. The army walked at the enemy under its 5 s orders and
  was never commanded again. The replies are in the trace (`m4`-`m6`; `m6` holds both
  attempts). Counted as a loss by the harness rule (the battle never waits), flagged
  here as a served-backend anomaly for the owner's "pinned backend outages count
  against the model" issue; the same backend garbled seven accepted replies in four
  launches of the night (owner item 6).
- **Hammer and anvil (two Swordsmen), GLM-5.3 low, launch 2: won by contact at 333 s**
  ($0.23, 126 decisions, age p50 2.1 s): the Swordsmen pinned one enemy unit, the knights
  charged the other and pulled out three times (82, 118, 151 s) before it routed at 246 s,
  then the pinned unit at 333 s; 19 of 45 knights, 56 of 90 swordsmen left. GLM 2 of 2
  on this step (the walking floor also wins it).
- **Helblaster battle, GLM-5.3 low, launch 2: won by contact at 172 s** ($0.13, 71
  decisions, age p50 2.1 s, no refusals), and the gun survived (27 of 33 crew): the first
  battle on this scenario in which the protected unit lived. The escort was placed beside
  the gun in guard mode at 5 s; the gun shot one Yeomen unit from 60 s and the other from
  63 s, both reached the gun at 74 s and both routed (84 and 114 s) with 17 and 19 of 45
  left; the gun then shot the Men-at-arms, which routed at 168 s with 47 of 90 without
  ever reaching melee. GLM 1 of 2 tonight (1 of 4 episodes with the 2026-10-17 launch); the
  `Bodyguard` script won 5 of 8 but
  always lost the gun.
- **Lines of fire (three Dwarf Warriors), GLM-5.3 low, launch 2: lost at 399 s** ($0.27,
  107 decisions, 7 refusals). Skirmish off and halts at 71 s, both guns on targets from
  88 s (402 and 293 rounds), then a retreat at 151 s while the Dwarfs closed; the Dwarfs
  lost 2, 0 and 21 of 75 men. GLM 0 of 2; this step has now beaten nine launches.

**Second queue done at 07:20**: 16 launches, $4.06 (GLM $2.59 on 9 battles, Kimi
$1.47, scripted $0); WH3 OpenRouter ledger $18.85 (both queues $6.36). Model contact
wins in the queue: 3 of 10 (GLM on the wolves battle, the hammer and anvil and the
Helblaster battle). Scripted
team arms: 0 of 4 on the line battle.

Third queue (b45, from 07:20; the line battle with every player unit at rank 5, which the
startup check confirmed: friendly ranks 5, enemy 0):
- **`hold`: lost at 327 s**, 47% left against 77%: the same length as the rank-0 hold
  floor (327 s) and almost the same losses (54% against 79%). The cavalry hit the line at
  153 s, the infantry wave at 188-203 s, the line broke at 259-268 s. Rank 5 alone did
  not change what a passive line does.
- **`attack_nearest`: lost at 449 s**, 37% left against 51% (at rank 0 it had reached the
  timer with 13% against 17%). Both enemy cavalry units were routed by 156 s, the Big 'Uns
  at 320 s, but the line units walked into the Boyz and goblins and broke 189-354 s. Both
  rank-5 floors lost, so the step is still open for the team arms and the models.
- **`LineTeam` (fixed jobs): won by contact at 461 s**, 49% left against 34%: the first
  contact win on the line battle (11 launches at rank 0, this the third at rank 5).
  Every enemy unit routed: the riders at
  179 s and the boars at 218 s (the knights' counter-charge, which again cost the whole
  knights unit by 274 s), the goblins and Big 'Uns at 393 s, both Boyz at 407-410 s and
  finally the archers at 449 s. The guns were never caught (560 and 276 rounds) and the
  reserve never fought (74 of 90, no melee): the rank-5 line in guard mode held the
  infantry wave by itself, losing one Swordsmen unit and the Halberdiers (26, 42 and 12
  left). So at rank 5 the fixed plan wins where both floors lose, a candidate card in the
  tactic-card sense (one launch each, unverified; the replacement-rule arm, GLM and Kimi
  follow).
- **`LineTeamReserve`: lost at 491 s**, 41% left against 38%, a near thing: six of the
  seven enemy units routed (riders 159 s, boars 198 s, goblins 317 s, Big 'Uns 360 s, both
  Boyz 383-395 s) and only the archers (65 of 68) were still fighting when the guns
  (457 and 471 s) and then the whole line (487-491 s) routed together, a morale collapse
  rather than a melee loss. The reserve got no order until 343 s: the rallied Boar Boyz
  remnant ran into it at 266 s and guard mode fought them off (266-273 s, no men lost;
  the 25 m rule covers enemy infantry only). The replacement rule fired at 343 s, in the
  decision the Halberdiers were first seen routing, and sent the reserve at the Big 'Uns
  about 50 m away, then at each Boyz unit. One win and one near-loss for the two arms at
  rank 5 are consistent with one plan on a battle at its edge, not with a difference
  between the arms.
- **GLM-5.3 low: won by contact at 687 s** ($0.58, 224 decisions, age p50 2.7 s, one
  refusal): the first model contact win on the line battle. The knights charged the boars
  at 143 s and then a Boyz unit, and were kept alive to the end (13 of 45, never routed);
  the Spearmen reserve was sent at the riders at 167 s and the goblins at 181 s; both gun
  units were ordered onto the Big 'Uns from 193 s, one was caught at 228 s after 60 rounds
  and routed at 290 s, the other fired 736 rounds; the enemy routed in order riders 181 s,
  goblins and boars 365 s, Boyz 475 and 561 s, archers 500 s, Big 'Uns 594 s, while both
  Swordsmen units held to the end (18 and 37 men). At rank 5 the floors are 0 of 2, the
  fixed plan 1 of 1, the replacement arm 0 of 1 (near), GLM 1 of 1, all single launches.
- **Kimi K3 low: lost at 532 s** ($0.63, 152 decisions, age p50 3.3 s, 6 refusals). Halts
  and guard mode on everything at 5 s, the knights on the boars at 143 s and then on a
  Boyz unit, the reserve on the riders at 156 s; both enemy cavalry units and the Big 'Uns
  routed (177, 337 and 398 s), but from 223 s the knights were walked to the western edge
  in a dozen moves and the line broke 272-378 s with the archers untouched; 23% left
  against 44%.

**Third queue done at 08:18**: 6 launches, $1.21 (GLM $0.58, Kimi $0.63); the night's 39
launches cost $7.56 and the WH3 OpenRouter ledger reads $20.05. On the rank-5 line
battle: floors 0 of 2, `LineTeam` 1 of 1, `LineTeamReserve` 0 of 1, GLM 1 of 1, Kimi 0 of 1,
every one a single launch.

Fourth queue (from 08:19; one GLM-5.3 low launch on each Empire scenario not yet played
tonight):
- **Riflemen card at 1.0: won by contact at 307 s** ($0.23, 152 decisions, age p50 1.8 s).
  Two orders in the whole battle: guard mode on both units at 5 s. The guns fired 163
  rounds at will and were never touched, the braced Spearmen held the Savage Orcs from
  152 s and the orcs routed at 307 s with 36 of 90. The walking floor also wins this step
  (2026-10-18), so it is data, not a card result.
- **Riflemen card against Big 'Uns: lost at 183 s** ($0.12, 68 decisions, age p50 2.4 s).
  Guard mode and a forward move at 5 s, halts at 52 s, then the Spearmen sent at the orcs
  at 118 s while the guns were walked back; the Spearmen routed at 169 s after 42 s of
  melee, the guns at 183 s after 170 rounds, the orcs at 62 of 75. Both floors had lost
  this step the same way (2026-10-18); nothing a two-unit plan has tried holds Big 'Uns.
- **Lines of fire against two Dwarf Warriors: won by contact at 458 s** ($0.34, 171
  decisions, age p50 2.4 s, no refusals). Guard mode at 5 s, a short advance, the guns on
  one Dwarf unit from 60 s and the Spearmen sent in at 84 s; from 116 s both guns were
  switched to the unit the Spearmen were fighting and kept there (507 and 696 rounds,
  never in melee), which fell to 9 of 75 and routed at 384 s; the other followed at 458 s.
  The walking floor also wins the two-Dwarf step, so this is data; the three-Dwarf step
  remains unbeaten.
- **Hammer and anvil against three Swordsmen: lost at 335 s** ($0.20, 88 decisions, age
  p50 3.3 s). The knights rode a wide loop and charged from 80 s, cycling three times
  against the same unit (routed none; 66 of 90 left), while the Swordsmen pinned another
  from 174 s; the knights routed at 319 s with 16 of 45 and the Swordsmen at 335 s.
  Consistent with the step's history (walking floor and `HammerAnvil` 0 of 5): three
  Swordsmen are too many for this pair.
- **Helblaster step 2 (two Men-at-arms): lost at 226 s** ($0.13, 60 decisions, age p50
  3.3 s). The gun was moved at 5 s and 34 s and so had fired nothing when the riders
  reached it at 75 s (ammunition 594 of 594 at its death at 110 s); the escort routed one
  Yeomen unit (135 s) and fell to the two Men-at-arms at 226 s. Moving an artillery piece
  in the opening minute costs its whole firing window: a lesson that reads straight from
  the trace.
- **Wizard at 1.1: lost at 427 s** ($0.26, 91 decisions, age p50 3.9 s, 2 refusals). A
  long spell sequence from 118 s (Fireballs, upgraded Fireballs, bound blasts, The Burning
  Head, Flaming Sword and the cloak on the Spearmen) and a kiting wizard; the Spearmen
  were sent in at 214 s and fought from 260 s; the wizard was caught at 381 s and both
  routed at 427 s with the enemy at 86 and 61 of 90. GLM 0 of 3 on the wizard battles.

**Fourth queue done at 09:00**: 6 launches, $1.28; GLM won the riflemen card at 1.0 and the
two-Dwarf crossfire (both steps the walking floor also wins) and lost the Big 'Uns, the
three-Swordsmen, the Helblaster step 2 and the wizard at 1.1. **The night**: four queues,
45 launches, $8.84 on OpenRouter (ledger $12.49 to $21.33); model contact wins 7 of 29
model launches, all GLM-5.3 low (GLM 7 of 25, Kimi 0 of 3, Qwen 0 of 1), three of them
(wolves, Helblaster, rank-5 line) on steps where a floor loses. All unverified, single
launches except where counted; the log entry keeps the per-scenario counts.
