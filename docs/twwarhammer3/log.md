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
