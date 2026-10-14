# WH3 battle versions

## Benchmark harness b3 (draft, not installed in the running b2 queue)

The missing terrain field observed during b2 acceptance now fails benchmark setup
before a controller can act. Unexpected startup/source errors retain their cause and
are infrastructure failures; interruptions remain separate. Paired reports also show
valid trials per whole-job wall hour, counting setup, resets and failed jobs. If any
supplied job lacks final wall timing, throughput is unavailable rather than estimated
from episode durations.

The boundary review also found that enemy registration could announce unseen arrivals,
and an earlier sighting could reveal a later hidden death. `obs-v2+terrain` keeps the
initial lobby roster public but adds later units only on sight; a death flag requires
visibility at observation. This is a source/contract change before G1/G2, not installed
midway through the b2 screen. Scoring still uses private totals for all units.

The local engine API documentation identifies `CcoUnitStat.ValueBase` as excluding
modifiers/buffs/debuffs, and `Value` as current. Startup now retains both privately.
Subsequent b2 1.0/1.1 startup snapshots at 5.2 s show that the AI difficulty bonuses
already enter ValueBase: all 12 enemy entries change (roughly +10% melee attack/defence,
weapon damage and charge, +8 leadership); all 12 player entries stay identical. The
general API description must not be read as excluding that difficulty layer. Current
Value will distinguish additional active effects; its live b3 check remains pending.

Validation: 192 WH3 tests passed with the Lua runtime; Ruff and Lua 5.1 parsing passed. Regression
checks cover absent terrain, startup causes, and a throughput denominator containing a
setup failure, plus hidden summons/deaths and retained observed deaths. Live b2 traces/
reports remain separate by their recorded source; b3 live acceptance remains pending.

## Benchmark harness b2 (2026-10-14, draft awaiting live validation)

Read-only probes during b1 acceptance found the per-army AI modifier getter, stat
previews and terrain APIs. b2 sets/reads the declared lobby modifier and checks it again
on every army. It exposes coarse terrain and tested nearby destinations after an
unreachable move, without replacing an order. Both model renderers receive these
observations (`obs-v1+terrain`); the tactical policies otherwise remain unchanged.
It also records API wall latency, returned model and optional provider processing header
for WH3 only, retains setup failures in reports, and separates partial traces from
terminal failures. Herald development/held-out candidates are declared before tuning.

Worktree checks: 1019 passed, 14 skipped (local evidence absent in that worktree),
57 targeted tests passed after the follow-up changes, Ruff and Lua 5.1 parsing pass.
Frontend probe on `7c0abdb` set/read AI modifiers 1.0/1.1 and the short 1200 s
timer. The Herald calibration candidates now declare that timer. Battle validation and
calibration remain pending. Source edits were isolated while b1 ran.

The first Herald terrain job (`bench-b2-terrain-20261014`, `587d501`) was refused
before battle because the enemy roster exceeded Default Funds; zero scored episodes.
The funds probe read only Default/Custom options and verified custom 30000. Herald
candidates retain their units and now pin that budget. Setup failures retain current
menu dumps. Validation after this fix: 54 relevant tests passed; Ruff passed.

`bench-b2-broken-setup-20261014` (`acb97f5`) refused the nonexistent card before
scoring and saved its map dump. `bench-b2-acceptance-20261014` passed the corrected
Herald setup (1.0, 1200 s, custom 30000) and recorded both armies' starting stats, then
stopped at the terrain diagnostic: this game lacks `math.huge`, so the grid was absent.
The sampler now starts from its first corner; a Lua 5.1 regression reproducing the missing
constant passes. The failed trial is in the register, Luna was not played. Full suite
before the Lua fix: 1033 passed, 1 skipped; Ruff and post-fix Lua syntax passed.

## Benchmark harness b1 (2026-10-14, acceptance rotation complete)

Owner goal: complete paired benchmarks, difficulty/latency calibration and the scenario
interface fixes. Added recorded controller rotation and importable controllers; strict
benchmark setup checks; observation-age arms; private evaluation totals excluding
routing/shattered units; objective ownership integrated on game ticks; reinforcement
counts by type; trial failure/interruption accounting; and paired reports with explicit
denominators, uncertainty and missing pairs. Policies remain llm v15/commander v3.

The frozen `dwf-sla-taurox` development scenario starts the acceptance work. Independent
run instructions: [benchmark-run.md](benchmark-run.md). No calibration claim yet.
Validation: 1030 tests passed, 1 skipped; Ruff passed; every mod script parses as Lua 5.1.
Follow-up clock/refusal edits passed the 52 relevant benchmark/play tests. Live results
and remaining acceptance work go in [benchmark-progress.md](benchmark-progress.md).

Acceptance job `bench-b1-acceptance-20261014`, source `5cad165`: hold, Luna, skills,
attack_nearest and imported ExternalHold all ended on engine losses (386, 824, 426,
262 and 386 s). All rematch start fingerprints matched. Luna cost $0.0594; ledger
$3.2937. Active margins -0.675, -0.002, -0.192, -0.594 and -0.675 respectively.
One instance verifies the rotation/import path, not ranking confidence or calibration.
The five rows are committed in the register; report and probes are linked in progress.

One entry per harness version: what changed, the job, and the results. The scenario is
fixed unless an entry says otherwise: `kho5-dwf5`, a custom battle on "An Ogre's Folly",
Khorne (player: Herald of Khorne, Chaos Warriors, Bloodletters, Marauder Horsemen with
throwing axes, Skullcannon) against Dwarfs under the game AI (Lord, Dwarf Warriors,
Longbeards, Quarrellers, Grudge Thrower), unit size large, real time at speed 1. Before
v13 a decision came 5 s of battle time after the previous orders applied; since v13 it
starts as soon as they are acknowledged. Later entries play random draws and say so.
Rows are in [results.csv](results.csv);
`python -m twwarhammer3 digest <job>[/episode-NNNN]` reads the evidence.

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

Job `llm-luna-v12-kho-20261013` (source `42a8af7`): lost at 225 s (11% against 59%), 271 s
(19% against 52%) and 265 s (19% against 54%).

The scenarios were less fixed than intended. Picking a race leaves the faction within it
to the game, and it varied between jobs on both sides: Khorne jobs played Khorne against
Arbaal's faction or Crimson Skull against Khorne (v12's enemy also deployed elsewhere),
Empire jobs Wissenland, Empire or Golden Order, Dwarf jobs Dwarfs, Karak Kadrin or the
Ancestral Throng. Every comparison between versions above carries that variation (the
first v6 Khorne job, 2 wins of 3, is the only one with wins and played Khorne against
Arbaal, as did v9-v11's). The next fix pins each side's faction in the scenario.

v12 was reverted (`main` runs v10) and the scenario steps now pin each side's faction
(`61c5f7f`). First battle with pinned factions, Khorne against Khorne, v10
(`llm-luna-v10-kho-pinned-20261013`, stopped after it at the owner's return): lost at
248 s (32% against 52%). The enemy deployed at about (-23, -295), as in v12's job, not at
(-148, -267) as with Arbaal's faction. Results before `61c5f7f` mix factions; versions
should be compared again with pinned factions.


## v13: continuous decisions and expanded battle controls

Owner-requested controller change. Implementation starts at `863d10b`; final code
`6db8111`. Tactical rules remain based on v10, with command instructions updated.
The default post-application wait is 0 ms (was 5000); positive `--interval-ms` remains
an explicit pacing option. Terminal observations now record a matching acknowledgement
before ending the episode, and decision observations record `since_previous_applied_ms`.

The policy can select auto/melee/ranged attacks, queue moves and a final attack, choose
formation width, toggle supported fire-at-will/skirmish/guard/spacing/formed-attack
behaviors, and issue owned active abilities at self, friendly/visible enemy units or a
ground point. Python validation and Lua dispatch enforce the targets/capabilities.
Acknowledgements identify each order by index and distinguish queued from issued.
A rejected queued successor does not erase the preceding successful move from memory.
The prompt shows supported toggles, width, submitted queues, active ability keys,
permission and last issue times, plus the player's magic pool/reserve. Cooldowns and
uses remaining are explicitly unknown: `can_perform_special_ability` stays true after
casting. An ability/queue acknowledgement is not a completion report.

Validation: 71 WH3 tests pass; `ruff check src/twwarhammer3 tests/twwarhammer3` passes.
Real engine evidence is in `runs/twwarhammer3/capability-probes/` (ignored), with source
fingerprints, engine/pack pins, script copies, observations, requests, acknowledgements
and checks. `khorne-dwarfs-r3` verified toggles, a 20 m width, queued waypoints, ranged
fire followed by melee with 453 ammunition left, and rejection of successors to an
unreachable move. Foe Seeker raised the lord's walk/run speeds from 1.9/4.8 to 2.4/6.0.
Its 60-second Luna smoke made seven decisions, six acknowledged (zero invalid); every
next decision used the acknowledgement snapshot with 0 ms added gap. Mean think time
9.399 s, wall roundtrip 9.744 s; $0.003063. The final call ran across the episode timeout.

`wizard-r3` verified friendly Glittering Robe, enemy Plague of Rust and ground Searing
Doom orders with magic-pool decreases of 5, 4 and 6 respectively; a unit trying to use
another unit's ability was rejected. Earlier probes found the undocumented requirement
to pass a unit even for a self ability; the dispatcher now passes the caster. Spacing
and formed-attack toggles were unavailable on the tested armies and correctly omitted.
These are diagnostic battles with scripted prefixes, not comparable policy outcomes,
so they add no rows to the results register. See integration.md for the limits.

## Automatic startup video skipping (2026-10-13)

Code `2793933`. `launch` and `play` install a separate auto-loaded PFH5 movie pack in
the game's `data/` directory and set `fe_game_intro_video_enabled false` in the existing
profile. The change persists for ordinary Steam launches. The pack replaces the five
startup movies and all 13 localized warning movies with twpatcher's 595-byte blank clip
(MIT attribution in `src/twwarhammer3/assets/LICENSE.twpatcher`). It leaves the main
cinematic intact for the viewer. Preparation refuses to change game files while WH3
is running, preserves all other preference bytes, and leaves matching startup files
untouched. Doctor reports the effective setting and actual/expected pack hashes;
deployment evidence includes them. No new CLI options or desktop input.

Validation: 83 WH3 tests and repository-wide Ruff pass. Engine evidence is under
`runs/twwarhammer3/skip-intro-20261013/`. The baseline reached the visible Battle button
at 149.014 s; the patched launch at 17.735 s, saving 131.279 s in one comparison.
Without the project mod list, the menu is visible in the capture completed at 20.774 s,
and the game's Lua log shows no project scripts. These were direct executable launches
with Steam running; the Steam launcher UI was not exercised. The static loading splash
remains. All 18 overridden paths exist in the installed engine's `movies.pack`; the
installed 11,646-byte startup pack has SHA256
`87c3964bdbbb4d07feef70e7befcbb919753c948bff47182d78a42caa24c03f1`.
The live preference comparison changed only `true` to `false`, and attempting preparation
during the patched probe was refused before writing.

### Unpaused 1x battles only

The first diagnostic `play-smoke` used `--pause`; the owner rejected this and requires
all battles, including probes, to run unpaused at normal 1x. It remains labelled as a
paused diagnostic in local evidence and contributes no policy result. Code `1c56ec2`
removes automatic observation/order pauses from the Lua mod, sets the battle speed to
1x at deployment, and removes the CLI's pause/speed overrides. Python rejects paused
or altered-speed configurations, session writes, attached sessions and incompatible
live observations before a policy decision. The prompt and repository instructions
now explicitly require unpaused 1x. Historical results retain their recorded modes.

Validation: 95 WH3 tests and repository-wide Ruff pass, including rejection of stale
paused sessions and speed overrides. The replacement engine smoke is
`runs/twwarhammer3/skip-intro-20261013/play-smoke-realtime/`.
It reached a deployed five-versus-five battle, made 78 decisions and acknowledged
77 batches with zero invalid orders. Every decision observation reports speed 1 and
`awaiting_orders=false`; measured battle time advanced 23.4 s over 23.401 s of wall time.
The run ended at its 50-second diagnostic timeout, with no gameplay outcome measured
and no row added to the policy results register. Repeat installation preserved the
startup pack/preference bytes and mtimes. All probes are stopped, session files cleared,
and the final doctor reports ready with the startup skip installed.

## Skills and commander v1 (2026-10-13)

Owner request: build the simplest design from a research summary (ChatGPT 6 Astra Pro,
2026-10-13), an asynchronous API-model commander over persistent scripted skills, and
document the other designs for later comparison
([controllers.md](controllers.md)). Code:
- `d2bf74a`: the skills executor (`--policy skills`), the commander
  (`--policy commander`), a `policy` column in the results register (rebuilt from
  `runs/`, identical except that column and blank model cells on scripted rows) and
  trace thinning for fast policies.
- `0f8eb39`: the fixes below.
- `5a2fc8d`: random battles.

The model's prompt is `configs/twwarhammer3/commander_prompt.md`; the direct controller
keeps `system_prompt.md`.

Smoke battles, one episode each on `kho5-dwf5`, unpaused at 1x, AI difficulty very hard
(found by the probe below; every earlier battle ran at it too):

| Job | Source | Outcome | Battle s | Own left | Enemy left | Plans | Mean plan age s | Cost |
|---|---|---|---|---|---|---|---|---|
| `skills-v1-kho-smoke` | `d2bf74a` | lost | 302 | 0.34 | 0.57 | | | $0 |
| `commander-luna-v1-kho-smoke` | `0f8eb39` | won | 355 | 0.53 | 0.28 | 53 | 6.5 | $0.02 |
| `commander-sol-v1-kho-smoke` (`gpt-6.1-sol`) | `0f8eb39` | won | 255 | 0.75 | 0.44 | 41 | 6.0 | $0.18 |
| `commander-astra-v1-kho-smoke` | `0f8eb39` | won | 309 | 0.64 | 0.26 | 59 | 5.1 | $1.17 |

All jobs ran at low effort. Mean order delay was 0.3 s (maximum 0.6 s) in every job,
against 4-11 s for the direct controller. The executor ran about 3 decisions a second,
and traces stayed at 1.6-2.5 MB per battle after thinning.

These battles show that the controller works, not that it is stronger: the direct
controller won 5 of 6 on this scenario at v6 and `attack_nearest` 3 of 3. The comparison
needs six or more episodes per controller
([controllers.md](controllers.md#comparing-controllers)).

- **skills v1** found a defect. The observation published with an acknowledgement still
  shows the previous target, and shoot preferred the observed target. After the enemy
  lord's melee flag flickered at 89 s, the Skullcannon alternated between two targets
  on every tick from 89 s until 185 s: 319 attack orders and no shots. `0f8eb39` makes every
  skill prefer the executor's own last target (regression test). A six-agent review
  (three reviewers, each with a verifier) confirmed eight more defects, all fixed in
  `0f8eb39`:
  - a charge whose named target is out of sight now acts as with no target;
  - without a post, charge halts the previous skill's order;
  - only an unreachable move drops its point;
  - an attack the game redirected counts as lapsed;
  - `describe_orders` no longer crashes on an ability with x but no z;
  - the prompt no longer annotates orders sent in the same tick;
  - the trace keeps the observation a failing decision saw.
- **Commander.** The first Luna plan arrived 7.2 s after its state. Meanwhile the
  default skills had the infantry engaging, the Skullcannon firing and the lord and
  horsemen waiting for melee. No assignment was ever dropped. Every engine rejection
  except two was an ability cast the engine refused ("does not support this special
  ability"): 7 for Luna, which repeated `deadly_onslaught`, and 2 each for Sol and
  Astra. Luna's other 2 were unreachable horsemen moves. The model still cannot tell ability cooldowns.
  The owner saw a Khorne army ability become available near the end of a battle and go
  unused. Army abilities are missing from the interface (state and orders) for every
  controller; this is a harness gap to fix, recorded in integration.md.
- **Latency and cost.** Sol and Astra at low effort spent only 25 and 10 reasoning
  tokens per call, against Luna's 341, so they were no slower: think time was 6.4 s
  for Luna, 5.8 s for Sol and 4.8 s for Astra. Astra's first call took 12.5 s. Total WH3
  spend after these jobs: $2.08 of the $25 ledger.

### Random battles

Owner request: use the custom battle screen's Autogenerate army on random factions, and
randomize the map too. A UI probe (`runs/twwarhammer3/probe-random-army-20261013/`,
[integration.md](integration.md#frontend-automation)) found:
- the button `clear_autogen_parent/button_autogen`;
- the classic battle types' 380 maps;
- the faction list of each of 23 owned races (307 factions);
- the profile's fixed settings, including AI difficulty very hard.

`--scenario random [--seed N]` draws the map and both races from
`configs/twwarhammer3/custom_battle.json` and autogenerates both armies. The battle type
stays classic: sieges, capture points and survival need interface work first.

The first draw, `commander-luna-v1-random-s2-smoke`, was seed 2 on
`land_of_the_dead_01_04`. Dark Elves (Blessed Dread) had 13 units: a Dreadlord,
Corsairs, Executioners, Black Guard, Dark Riders, Cold One Knights, a Cold One chariot,
three Harpies, a Feral Manticore and a Reaper Bolt Thrower. Nurgle (Pallid Nurslings)
also had 13. The commander won at 407 s with 0.40 of its men left against 0.23, from 62
plans: mean plan age 6.5 s, think time 6.2 s, about 4,800 input tokens per call, $0.03.
All 9 rejections were refused lord ability casts. The trace was 5.5 MB.

A `skills` job on the same seed was stopped at the owner's word: a repeated draw shows
nothing new, and a job is one matchup. The draw also picked a faction for each side
(`5a2fc8d`), but the owner noted that a faction within a race only changes colours. The
next commit draws races only, a fresh seed per job. The mod reports the Harpies and the
Feral Manticore as infantry: its class mapping checks `can_fly` only for monsters.

Two fresh draws followed, each lost:

| Job | Draw | Outcome | Battle s | Own left | Enemy left | Notes |
|---|---|---|---|---|---|---|
| `skills-v1.1-random-a` (`900000a`) | Skaven (20 units) vs Norsca (13), `wh3_nur_wastes_01_04`, seed 255179936 | lost | 415 | 0.35 | 0.25 | 0 rejections |
| `commander-luna-v1-random-b` (`29c9325`) | Vampire Counts vs Lizardmen, `wh3_tze_wastes_02_01`, seed 369290826 | lost | 404 | 0.00 | 0.31 | 70 plans, plan age 5.6 s, $0.03 |

In the commander battle, 19 of 21 rejections were refused lord ability casts. A defect
to fix before the comparison: in the skills battle four Skaven missile units (Night
Runners, Gutter Runners, Globadiers, Death Globe Bombardiers) re-sent the same ranged
attack every 2 s for long stretches, 69-102 orders each. The engine never showed the
ordered target, probably for lack of line of sight, so the redirected-attack lapse rule
from `0f8eb39` fired on its 2-second repeat. A shooter should give up on a target the
engine keeps refusing and pick another.

### Shooter re-send fix: executor v1.2 (`55ab6b3`)

Diagnosis from the Skaven trace: the four shooters spent most of their attack time moving,
with no target shown by the engine and no shots (779 such observations against 131
with shots). Many of those stretches were chases of fast chariots (Chaos Chariot,
Warwolves Chariot) kept in range for 15-42 s without a shot. The lapse rule read "no
target" as a dropped attack and re-sent it every 2 s. Two changes:
- an attack is not lapsed while the unit moves with no target and no move destination
  (closing in, finding a line of fire or evading as a skirmisher); it lapses when the
  unit is idle, shows another target, or stands without one. Replayed over the logged
  orders, this suppresses 118 of the 195 shooter re-sends;
- a shooter that fires no shot (ammunition unchanged) at a target in range for 15 s
  (30 s for artillery, whose reloads were up to about 20 s) skips that target for 30 s
  and picks another; its phase says so.

Validation, `skills-v1.2-random-a` (seed 255179936, same draw and the same
autogenerated armies): no shooter repeated an identical order more than 3 times in a row,
against stretches of up to 21 before. Orders per shooter fell from 69-102 in 415 s to
47-60 in 346 s; what remains is target switching as enemies enter and leave range.
Ammunition spent changed both ways (Night Runners 387 -> 162, Globadiers 96 -> 132,
Gutter Runners 1080 -> 880, Death Globes 146 -> 99), so one battle says nothing about
firing volume. Lost at 346 s with 0.40 of our men left against 0.70 (before: 0.35 vs
0.25 at 415 s). The draw is hard: fast Norscan cavalry and chariots against short-range
skirmishers.


## Controller comparison on `kho5-dwf5`, stopped for random battles (2026-10-13, late)

Six episodes each on the fixed Khorne vs Dwarfs battle, unpaused at 1x, AI very hard:

| Job | Source | Won | Mean battle s | Own left | Enemy left | Cost |
|---|---|---|---|---|---|---|
| `skills-v1.2-kho` | `cb12f6a` | 5/6 | 461 | 0.10 | 0.17 | $0 |
| `commander-luna-v1.2-kho` | `df390c1` | 5/6 | 329 | 0.27 | 0.33 | $0.12 |
| `llm-luna-v13-kho` (1 episode) | `df390c1` | 1/1 | 244 | 0.66 | 0.28 | $0.02 |

(Commander v1.2 is the v1 commander over executor v1.2; there was no v1.1 commander.)

- The scenario does not separate controllers: `skills`, the Luna commander and the v6
  direct controller all won 5 of 6 on it.
- Three `skills` episodes were identical (531 s, 0.10 vs 0.09 left). With a deterministic
  controller, a rematch replays the same battle, so its episodes are not independent
  samples.
- The commander's 34 engine rejections in 6 battles: 26 refused lord ability casts and 8
  unreachable moves.
- The owner asked why we were still playing small fixed battles, so the `llm` job was
  stopped after its first episode (won). The comparison moved to random draws: six
  seeds, each played once by every controller, so the draws are paired.

## Ability readiness and army abilities: llm v14, commander v2 (`9bfee82`)

The script API has no ability cooldown getter, but the UI's context system has one
([integration.md](integration.md#ability-state-through-the-ui-context-system-probed-2026-10-13)).
Each friendly ability now carries:
- target type, magic cost and cooldown;
- `ready`, `active`, seconds of recharge left and uses left.

Army abilities, such as Khorne's three kill-unlocks, carry target, radius, unlock cost,
`unlocked` and `ready`. An `ability` order with unit `"army"` casts one. Validation
refuses an ability that is not ready, and both prompts describe the new state.

`watch` follows a job beside the game, and `play --show` puts each model reply in the
advisor window.

Engine check, `probe-abilities-random-s4` (`--policy probe_abilities`, seed 4: Khorne
(Arbaal) vs Dark Elves, autogenerated):
- The lord's and the hero's self abilities (Fight or Die, Potion of Toughness, Deadly
  Onslaught) were cast when ready and accepted. Afterwards the state showed them active
  and not ready, and the potion with 0 uses left.
- The army abilities showed locked, with costs 100/200/300.
- The battle was lost at 228 s with 31 points, so no army ability unlocked. The probe
  now runs on the `skills` executor (`46f94d0`), which earned 113 points on `kho5-dwf5`.

Second check, `probe-abilities-random-s245-20261014` (Khorne vs Skaven, seed 245):
- Horn of Khorne unlocked at 109 points and was cast at our largest unit's position at
  260 s. The engine accepted it, and its HUD timer counted 31 s active, then 90 s of
  recharge. The state now shows those phases (`739ce9c`).
- The lord's and hero's casts were accepted as before. The battle was lost at 337 s.

## Random-battle comparison, partial (2026-10-13/14)

Three seeds of the planned six, each played once by every controller (`9bfee82`, AI very
hard, autogenerated armies), then stopped at the owner's word to finish the engineering
first. All nine battles were lost:

| Seed: draw | `skills` | Luna `commander` v2 | Luna `llm` v14 |
|---|---|---|---|
| 2028855463: Dark Elves vs Nurgle | 434 s, 0.06 vs 0.34 | 299 s, 0.15 vs 0.56 | 618 s, 0.00 vs 0.31 |
| 1202868312: Daemons of Chaos vs Nurgle | 259 s, 0.00 vs 0.67 | 293 s, 0.00 vs 0.75 | 280 s, 0.00 vs 0.54 |
| 322117462: Dwarfs vs Slaanesh | 382 s, 0.31 vs 0.30 | 231 s, 0.43 vs 0.58 | 317 s, 0.46 vs 0.60 |

Cells show battle length and strength left (ours vs the enemy's). Costs: commander
$0.018-0.025 a battle, llm $0.025-0.040. The direct controller decided every 6-7 s
(49-89 decisions a battle).

Three paired draws separate nothing yet, and these draws at very hard (with the AI's
1.1 stats modifier) are hard for every controller. The remaining seeds are 264482191
(Ogre Kingdoms vs Slaanesh), 1355466036 (Daemons vs Greenskins) and 238913231 (Cathay
mirror). The chain script ran `play --scenario random --seed N --episodes 1` per
controller.

## Battle types: llm v15, commander v3 (2026-10-14, overnight)

Owner goal (2026-10-14, away overnight): one minimal test scenario for each battle type
beyond the land battle (conquest, domination, free-for-all, ambush, chokepoint,
subterranean, minor settlement, siege, survival), as vertical slices toward the
benchmark. Everything is in [battle-types.md](battle-types.md); engine facts in
[integration.md](integration.md#battle-types-probed-2026-10-14).

What changed (`0cf3646` to `aa5a62b` and after):
- Setup: `battle_type`, `attacker`, several or no enemy sides, reinforcing armies;
  lobby steps guarded by `when` expressions; the engine's type and the player's role
  checked at the first observation; a start click that starts nothing fails at once.
- State: the observation's `mode` (type, role, timeout winner, the game's objective
  text, capture points, tickets, gates, supplies, building slots, reinforcement pool and
  spawn zones); units of every enemy alliance and units that enter mid-battle.
- Orders: `build` (towers and barricades) and `reinforce` (pool units), both paid with
  supplies; `probe_abilities` uses both.
- Prompts (llm v15, commander v3): the Battle section, the two orders, and the
  objective rule, including the owner's siege notes (keep the victory points held,
  spend supplies).
- Three review workflows, each with reviewers per dimension and an adversarial verifier
  per finding. The first (30 findings, 24 confirmed, 10 distinct) found a validation
  crash, slot usability that always read false, shifting reinforcement ids and smaller
  defects (fixed in `c7287f4`). The second found a running mean that froze after about a
  thousand observations and a cost mismatch in the pool (`088a175`). The third found
  zone usability judged by one unit, double purchases of one pool entry and doc errors
  (`8f9d832`).
- Engine findings during the battles fixed the same night: purchased units never got
  ids, because the scan only ran with regular observations (`d62a751`); a reply invalid
  three times ended the battle (`9f08da8`); spawn zones refuse purchases (`89f3f8c`).
  A bridges field for the chokepoint (`2a0a1cd`) was removed again (`fcba267`): that
  map has no buildings, its crossings are terrain.
- Also: random draws per battle type (`9b0209f`), measures per episode (`ea646a3`,
  `7a40889`, `01e3abb`: victory points and the key building held, supplies left,
  tickets, builds and purchases) and three register columns (`ea66fef`).

Results, one battle each ([battle-types.md](battle-types.md#results) has the tables):

| Scenario | `attack_nearest` | `probe_abilities` | Luna `llm` v15 | Luna `commander` v3 |
|---|---|---|---|---|
| conquest | won 510 s | | won 197 s | lost 403 s |
| domination | lost 742 s | lost 709 s | lost 1042 s (tickets 1156-1500) | lost 814 s |
| free-for-all | won 942 s | | policy failure; replay won 560 s | lost 909 s |
| ambush | won 173 s | | lost 699 s | truncated |
| chokepoint | won 369 s | | won 421 s | won 878 s |
| subterranean | lost 546 s | | won 391 s | won 503 s |
| minor settlement | lost 302 s | won 390 s | won 242 s | won 300 s |
| siege | won 510 s | won 430 s | won 368 s | won 450 s |
| survival | lost 198 s | lost 249 s | lost 292 s | lost 325 s |

One battle per cell separates nothing, but it shows each slice working. A siege with
the player attacking (`siege-attack-kho5-dwf5`) set up correctly but could not breach:
the gate stayed at 100% and the units idled outside the walls until the job was stopped
at 730 s; attacking needs gate and wall orders and siege equipment. LLM v15 cost
$0.32 for its ten battles; the commander $0.48.
