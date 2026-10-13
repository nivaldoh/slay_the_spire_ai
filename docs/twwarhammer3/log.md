# WH3 battle versions

One entry per harness version: what changed, the job, and the results. The scenario is
fixed unless an entry says otherwise: `kho5-dwf5`, a custom battle on "An Ogre's Folly",
Khorne (player: Herald of Khorne, Chaos Warriors, Bloodletters, Marauder Horsemen with
throwing axes, Skullcannon) against Dwarfs under the game AI (Lord, Dwarf Warriors,
Longbeards, Quarrellers, Grudge Thrower), unit size large, real time at speed 1, a
decision 5 s of battle time after the previous orders applied. Rows are in
[results.csv](results.csv); `python -m twwarhammer3 digest <job>[/episode-NNNN]` reads
the evidence.

## Baselines

`attack_nearest` (every unit attacks its nearest visible enemy), source `60314c3`, job
`attack-m3-20261013`: lost at 344 s, won at 400 s. Before `c3c9177` the baseline did not
re-order units whose attack had lapsed, so units stood idle under fire for minutes; the
two episodes understate it.

## v1: first LLM battles

Source `b615830`, job `llm-luna-v1-20261013`, `gpt-6-luna` low effort: won at 446 s,
lost at 503 s, lost at 366 s; 132 decisions, no invalid orders, mean delay 4.0 s between
the state seen and the orders applied (think time 3-6 s), $0.035 in all.

Reviews (one subagent per episode, `wh3-version-review` workflow): the Herald died in all
three episodes, each time sent into a fight at 21-38% health (twice at the enemy lord);
the Skullcannon spent all 36 of its shots across the episodes on the Grudge Thrower crew
and never killed one; the Marauder Horsemen were committed before the lines met and lost
missile duels to the Quarrellers; 83 of 132 replies gave no orders ("all units have
active orders", from the prompt's "leave out units that are carrying out your orders"),
including minutes when the lord bled out; "back toward the army" moves went to the
enemy side of the melee (no sense of the front). Misleading state: "running" on standing
units, the Skullcannon's class flipping with its ammunition, dead units listed with stale
flags, no enemy missile range, moves to unreachable points acknowledged as applied.

## Baseline after the lapse fix

`attack_nearest`, source `7b31ce9`, job `attack-b2-20261013`: won 3 of 3 at 346, 344 and
346 s, with 45% of our men left against 33% of the enemy's. A fixed policy gives nearly
the same battle every time; the model's variance comes from its own orders.

## v2: a battle doctrine (worse)

Change (prompt): check every unit each turn and pull back units that waver, lose men
faster than their target, or are under fire with nothing to hit; pull the lord back
below 40% health; switch fire targets that lose no men; keep missile cavalry out of
enemy missile range; charge only once the lines are locked. State fixes in the same
version: "running" only while moving, a unit's class fixed at the start, enemy missile
range shown, dead units on one line, moves to unreachable points rejected.

Job `llm-luna-v2-20261013` (source `f807f64`): lost at 569 s (none of our men left,
77% of the enemy's), lost at 614 s (2% against 45%) and lost at 1226 s (10% against 20%,
66 rejected orders). The model turned "pull back"
into a slow general withdrawal: units left melee (which costs men and morale in Total
War) and the army drifted to the map corner, where about 25 moves per episode were
rejected as unreachable. Think time doubled to about 8 s with the longer prompt.
Reviews (two episodes): moves ordered to units in melee went from none in v1 to 14 and
10; after the withdrawals began the enemy lost almost no men; the lord flip-flopped
between committing and withdrawing over a 3-point health gap, and lost 42% health while
disengaging.

## v3: commit and focus (best so far)

Change (prompt): v2's withdrawal triggers replaced by a commit-and-focus doctrine: keep
units in melee and send help into the enemy's flank instead; focus the enemy closest to
breaking and the enemy lord; the lord leaves melee only below 35% health; spent missile
units fight in melee; cavalry wait until the lines lock; "back" means toward our start.

Job `llm-luna-v3-20261013` (source `2681d04`): lost at 303 s (38% of our men left, 49%
of the enemy's), won at 419 s (11% against 18%), won at 392 s (28% against 24%); mean
delay 4.5 s, think time back to v1's level.

Replicate `llm-luna-v3-20261013b`: lost at 257 s, won at 345 s. v3 in all: 3 wins of 5.

Reviews: the Herald fought the enemy lord with no other melee unit on him in all 28 such
turns (the baseline had help in 20 of 22 and its Herald survives); the model paired its
units off one to one at contact ("f1 e1, f2 e2, f3 e3", from "strongest against
strongest"); the game's automatic target is shown as if it were the order, so a unit
the game had retargeted looked busy; units with ammunition shoot when ordered to attack,
so the horsemen and the Skullcannon could not charge.

Across all episodes so far, the model orders `run` on about 90% of its moves and attacks
(v1: 62 of 67; v2: 296 of 324), while `attack_nearest` never runs; the baseline's units
always reach their first melee fresh, the model's often tired or exhausted.

## v4: one body, gang up on the enemy lord

Change (prompt): the lord and the melee units advance side by side at a walk; two or
three units on one enemy, the enemy lord first at contact; every melee unit within 40 m
attacks the enemy lord when he engages; our lord attacks only targets another unit is on
and parks 30-50 m behind the line below 35% health. From the v3 reviews: the Herald fought
the enemy lord with no other melee unit on him in all 28 such turns (the baseline had help
in 20 of 22), and the model paired its units off one to one.

Job `llm-luna-v4-20261013` (source `0547bfb`): lost at 603 s (9% of our men left, 32% of
the enemy's), lost at 488 s (7% against 40%), won at 355 s (44% against 39%, the closest
an LLM battle has come to the baseline's 45% against 33%). The model followed the
doctrine: it walked on 55 of 76 moves and attacks (v3: 34 of 140), met the enemy at 95 s
like the baseline (v3: 55-79 s) and helped its lord in 12 of 14 duel turns.

Reviews: in both losses the Herald was parked at 20-23% health for 18 and 23 straight
decisions while the enemy lord fell to 12-2% and the model itself called him "nearly
defeated" (v4's "bring him back only to finish a routing or nearly dead enemy" had no
threshold); in the win the enemy lord routed at about 160 s, earlier than in the
baseline. The support units still did little: the Skullcannon fired its 12 shots for at
most 3 kills, and the horsemen, ordered at the Quarrellers through the melee, stalled
behind it and routed, throwing 6-26 axes where the baseline's threw about 170 into the
Dwarf Warriors before contact. Moves to flank were acknowledged but the unit barely moved.

Pause-mode ablation, job `llm-luna-v4-pause-20261013` (same source, `--pause`: the battle
stops while the model thinks; orders apply 0.6 s of battle time after the state seen,
against 5.5 s in real time): lost at 232 s (37% against 71%), lost at 579 s (8% against
34%), won at 434 s (39% against 26%). One win of three, as in real time: the model's
latency is not what separates it from the baseline.

## v5: a hurt lord keeps fighting

Change (prompt): below 35% health the lord stays out of melee only while a healthier
enemy lord or hero is near, and goes back in as soon as that enemy has less health than
he has (v4 parked him for minutes while the enemy lord was nearly dead).

Job `llm-luna-v5-20261013` (source `33895de`): won at 333 s (64% of our men left, 29% of
the enemy's: a wider margin than any baseline battle), won at 343 s (36% against 36%),
lost at 417 s (10% against 48%).

Reviews: the wins came from the lord and both infantry units walking in together and
all three going onto the enemy lord in the same reply at contact (he routed at 162 s in
the first win, our lord at 58%); the hurt-lord rule mattered in the second win (the
Herald fought on at 42% once the lords' health was level). The loss turned on the lord
duel: the Herald's line move carried him past the engaged Chaos Warriors, he alone was
sent onto the enemy lord, and when the game retargeted him and the Bloodletters onto
other enemies the model read it as its own gang-up, leaving the enemy lord untouched at
80% for 90 s. The support units achieved little in all three: the Skullcannon's 12 shots
killed almost no one and the horsemen's attacks on the Quarrellers were replaced by the
game 7 times, each acknowledged as applied.

Replicate `llm-luna-v5-20261013b`: won at 333 s, won at 418 s, lost at 329 s (32% against
54%). v5 in all: 4 wins of 6.

## v6: show what each unit is really doing

Change (state rendering, `llm.py`, with the prompt's description of it): each friendly
target is marked as the ordered one ("target e1 3 m (your order, 95 s)") or the game's
choice with the order it replaced; a move the game dropped reads "stopped N m short of
your move"; a unit with no target or destination reads "no order" and shows its nearest
visible enemy; men and health show the change since the previous decision for both sides;
orders are forgotten once the game no longer carries them out. In the same merge, fixes
from a review of this session's code (not visible to the model in this scenario): flying
monsters labelled flying again, the restart fallback only before a decision, battle UI
probes through `menu.json`, `stats` grouping scripted rows by source revision.

Job `llm-luna-v6-20261013` (source `ac3c0bd`): won at 357 s (26% against 34%), won at
496 s (8% against 24%), lost at 428 s (12% against 38%).

Reviews: the new lines were used. The model put units back on the enemy lord after the
game had moved them ("game's choice") 6-8 times per episode, and the horsemen's attack
orders were no longer replaced over and over. But the always-on gang-up then misfired:
in the loss the Bloodletters and Chaos Warriors stood "on" the enemy lord for 80 s while
his health fell about 1 point a turn (he stood inside his own infantry), and the Dwarf
Warriors wavered untouched beside them; the Herald was sent back at him 24-26 points
behind. Support fire stayed useless (14 Skullcannon shots and 270 axes for about 2 kills
in the first win); the hurt-lord rule parked the Herald for most of two battles.

Replicate `llm-luna-v6-20261013b`: won at 462 s (16% against 34%), won at 381 s (51%
against 18%), won at 374 s (56% against 19%: the widest margins of any battle so far,
the baseline included). v6 in all: 5 wins of 6.

## v7: the enemy lord only while he is losing the lords' race

Change (prompt): v4's always-on "every melee unit within 40 m attacks the enemy lord" is
gone. After contact the enemy lord stays the focus only while his health is below our
lord's or fell 5 points or more since the last turn; otherwise units leave melee targets
on the game's choice and switch to the nearby enemy closest to breaking.

Job `llm-luna-v7-20261013` (source `42d3054`): won at 451 s (10% against 27%), lost at
334 s (30% against 17%: our army broke with more men left than the enemy's), won at 376 s
(32% against 35%).

Replicate `llm-luna-v7-20261013b`: lost at 256 s (35% against 64%), lost at 278 s (32%
against 70%), lost at 434 s (22% against 29%). v7 in all: 2 wins of 6, against v6's 5 of
6, so v7 was reverted: `main` runs the v6 prompt. Without the standing order to pile onto
the enemy lord, the replicate's battles were lost fast; the race test seems to have taken
units off him too early. The next version starts again from v6.

## Mirror battles (2026-10-13, second session)

Scenarios are now named in `configs/twwarhammer3/scenarios.json` (each side's race,
faction and units; the menu steps pick the race in the selector's popup). Mirror battles
put the same army on both sides of the same map, the player starting north:
`kho5-kho5` (the Khorne army above), `dwf5-dwf5` (the Dwarf army above) and `emp5-emp5`
(Empire: General, Swordsmen, Handgunners, Empire Knights, Great Cannon).

Empire mirror, source `b1c9ce0`:
- `attack_nearest` (`attack-emp-mirror-20261013`): lost at 228 s and 232 s.
- v6 (`llm-luna-v6-emp-20261013`): lost at 270 s (8% against 71%), 242 s (19% against
  71%) and 246 s (37% against 65%). In every loss the enemy handgunners and cannon ended
  nearly untouched (64-66 of 68 men, 33 of 33) while ours were destroyed.

Khorne and Dwarf mirrors, v6, source `6777a64`:
- `llm-luna-v6-kho-20261013`: won at 265 s (39% against 17%), lost at 282 s (25% against
  33%), won at 247 s (37% against 25%).
- `llm-luna-v6-dwf-20261013`: lost at 499 s (31% against 66%), 576 s (24% against 50%) and
  629 s (20% against 43%).

v6 in the mirrors: 2 wins of 9, both in the melee-heavy Khorne mirror. The armies with
guns, crossbows and artillery beat the model every time.

## v8: answer the enemy's guns

Change (prompt), chosen by the review of the Empire mirror (all three judges): artillery
fires first at enemy artillery in range ("never at small crews" had made the model take
the cannon off the enemy cannon, the game's own pick, at 5 s in all three battles);
missile infantry stands 40-60 m to the side of the melee line, never straight behind it
(the handgunners fired 167 rounds through our own melee for 2 kills); a shooter whose
target loses no men for two turns moves to a clear line or switches; cavalry shelled
while waiting ride wide onto the enemy artillery instead of shuffling about in its range;
cavalry are left out of the enemy-lord gang-up.

Job `llm-luna-v8-emp-20261013` (source `fbcdf99`): lost at 321 s (25% against 69%), 203 s
(30% against 83%) and 343 s (38% against 57%). The enemy cannon was hit hard each time
(7, 33 and 15 of 33 crew left, against 33 of 33 under v6) and our side kept more (25-38%
against v6's 8-37%), but the enemy handgunners still ended untouched (66-67 of 68).

Job `llm-luna-v8-dwf-20261013` (source `3879027`, stopped after two battles when v9 was
merged): lost at 487 s (33% against 77%) and 605 s (26% against 75%). The enemy Grudge
Thrower broke under counter-battery fire, but the enemy infantry kept more than under v6
(43-66%): shells that went at the enemy artillery no longer thinned its infantry, and the
melee was lost as before.

## v9: fight the enemy holding you

Change (prompt), chosen by the review of the v6 Dwarf mirror losses and the Khorne
mirror loss (all three judges): after contact, a unit the game moved onto another enemy
stays on it; the enemy-lord rule sends units back to him only while he lost 5 or more
health since the last turn or none of ours is on him; no unit leaves a wavering enemy.
The reviewers counted 11-15 pulls onto the enemy lord per Dwarf battle while he stood
inside his own infantry, losing about 1.4 points a turn, and the enemy holding each
pulled unit hit its flank (f3 Longbeards 68→48 men against e3's 75→71 in one loss).

Job `llm-luna-v9-dwf-20261013` (source `d928965`): lost at 554 s (27% against 59%), 696 s
(33% against 49%) and 332 s (45% against 86%). Job `llm-luna-v9-kho-20261013`: lost at
205 s (25% against 70%), won at 218 s (35% against 36%), lost at 297 s (17% against 36%).
In the Khorne mirror v9 (with v8 under it) did worse than v6 (2 of 3, 34% against 25% on
average), and the mean delay rose from 7.2 s to 9.6 s as the prompt grew; which of v8 or
v9 cost the Khorne battles is not separated.

## v10: shooters hit infantry in the open

Change (prompt), chosen by the review of two v9 Dwarf and two v8 Empire losses (all three
judges): the reviewers measured, over the gun mirrors, artillery killing about 2 men a
shot at infantry in the open, 1 in 2 shots at missile infantry and 1 in 3 at crews, and
missile units killing about 1 man per 100 shots at enemy missile infantry. So until the
enemy infantry reaches our line every shooter fires at it; after that artillery fires at
the enemy's missile units, then its artillery (replacing v8's counter-battery first); a
missile unit never trades fire with enemy missile infantry and shoots infantry not in
melee, or from 40-60 m to the side of a fight; a shooter moves to its spot before the
attack (an attack replaces a move and walks a shooter straight at a target out of
range: about 20 such orders cut a shooter's own move in 14 gun-mirror battles).

Job `llm-luna-v10-emp-20261013` (source `ffbc953`): lost at 237 s (37% against 71%), 296 s
(22% against 38%: the enemy's lowest yet in this mirror) and 254 s (51% against 63%).
Still no Empire win, but the margin has narrowed with each version: mean strength left,
ours against the enemy's, v6 21/69%, v8 31/70%, v10 37/57%.

Job `llm-luna-v10-dwf-20261013`: lost at 432 s (47% against 63%), 574 s (35% against 66%)
and 394 s (44% against 75%); mean 42/68%, against v9's 35/65% and v6's 25/53%.

## v11: the lords never fight alone

Change (prompt, net shorter), chosen by the review of v10's Empire losses and v9's fast
Khorne loss (all three judges): the lord bullet becomes one rule. Whenever the enemy
lord is within 20 m of ours or fights any of our units, at least the nearest melee unit
that is not cavalry must target him, even out of another melee, until he breaks; our
lord attacks only an enemy another unit is on, never arrives first, and stays in melee
once there. Gone: v9's 5-point condition (read literally, it forbade help in a losing
duel, since our own lord counts as a unit on him), the 35% hurt-lord clause and "he is
your best fighter", which is untrue against the AI's 1.1 stats modifier. The reviewers
measured our lord, alone against the enemy lord, losing health 3 to 8 times faster than
he did; he was the first unit to rout in the v10 Empire losses.

Job `llm-luna-v11-kho-20261013` (source `1eb75aa`): lost at 246 s (27% against 46%), 232 s
(28% against 63%) and 198 s (22% against 74%).

To check whether v8-v11 cost the Khorne mirror, v6 was replayed there from a worktree at
`6777a64` (same ledger and results file): `llm-luna-v6-kho-20261013b` lost at 214 s (44%
against 77%), 227 s (37% against 50%) and 185 s (34% against 65%). v6 in the Khorne
mirror: 2 wins of 6; v9 1 of 3, v11 0 of 3. The first v6 job's two wins look like luck
more than a better prompt; the newer prompts are not shown to be worse there.

Job `llm-luna-v11-emp-20261013`: lost at 160 s (39% against 79%), 249 s (20% against
77%) and 189 s (42% against 73%). v11 in all: 0 of 6, and the Empire margin went back to
-42 points from v10's -20, so v11 was reverted: `main` runs v10.

Job `llm-luna-v10-kho-20261013` (source `9c8f995`, the v10 prompt): lost at 298 s (25%
against 37%), 211 s (15% against 68%) and 194 s (18% against 70%).

Where the mirrors stand at the end of the session (mean strength left, ours minus the
enemy's, in points): v6 Empire -48, Dwarfs -28, Khorne -8 (2 wins of 6); v10 Empire -20,
Dwarfs -26, Khorne -39 (no win in 9). v8-v10 traded the melee mirror for the gun mirrors;
`main` keeps v10, and v6's prompt is at `6777a64` for comparison. Spend for the session
about $0.25 (ledger total $0.68).

## v12: v6's melee rules with v10's fire rules

Change (prompt): v6's prompt with only v10's two fire bullets (shooters hit infantry in
the open until contact; artillery then fires at missile units, then artillery; missile
units never trade fire with enemy missile infantry; a shooter moves before it attacks).
v8's cavalry rules and v9's and v11's lord rules are left out. The mirrors split the
versions (v6 best in the Khorne mirror, v10 in the Empire mirror), and v10's fire rules
are the change with the clearest measured basis.
