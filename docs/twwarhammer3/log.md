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
