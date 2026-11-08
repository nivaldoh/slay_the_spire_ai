# Haengju inspired siege evaluation plan

Draft, 2026-11-08 (Claude, under the owner's goal of that day). **Planning only: nothing here is
built, launched or measured, and no run is scheduled.** The owner asked for a second evaluation
battle: a real siege in which one side had a clear disadvantage and still won through better
tactics. This page proposes the defence of Haengju fortress in Korea on 14 March 1593, adapted
as a WH3 siege battle. The controller defends a walled fort with a small garrison while a much
larger attacker comes at it in successive divisions. The owner's choices are collected in
[decisions for owner review](#decisions-for-owner-review).

The plan follows the [scenario guidelines](scenario-guidelines.md), the
[evaluation guidelines](evaluation-guidelines.md) and the [benchmark contract](benchmark.md):
fixed armies, public structured observations, permitted orders, engine wins including timer
wins, and unpaused 1x play. It reuses what the [Cannae plan](cannae-eval.md) and its two
windows taught: resolve every placement before evaluating anything, check that orders reach
their effects, keep shortcut wins as wins, and expect one battle per case to settle nothing.
Under the [hard rule](../../AGENTS.md#verification-hard-rule), everything below is unverified.

## The historical battle

In early 1593 the Joseon general Gwon Yul (Kwŏn Yul) occupied Haengju-sanseong, a hill fort
above the Han River west of Hanseong (Seoul), which the Japanese army then held. His staff
officer Jo Gyeong built two lines of wooden palisades, an outer and an inner one, and raised
earth banks to shield the garrison from musket fire. The garrison had bows, swords and spears,
Byeon I-jung's hwacha (carts that fired volleys of rocket arrows), cannon and stone-throwing
machines built on Gwon Yul's orders ([Encyclopedia of Korean Culture](https://encykorea.aks.ac.kr/Article/E0062859)).

Forces. Hawley puts the garrison at about 2,300 men against about 30,000 attackers, with
Konishi Yukinaga leading the attack ([Hawley 2005, p. 318, via Wikipedia](https://en.wikipedia.org/wiki/Battle_of_Haengju)).
The Korean encyclopedia gives the Korean total as "fewer than 10,000", counting detachments
posted outside the fort and 1,000 monk soldiers under the monk general Cheoyeong, and the
attackers as "3만여 명", about 30,000. On both counts the defenders were outnumbered, by
between about three and thirteen to one.

The battle. The attack began at about 6 a.m. and lasted until dusk. Because the space in front
of the stockade was limited, the Japanese divisions attacked in turn rather than together
(Hawley, via Wikipedia). The encyclopedia lists seven divisions in this order: Konishi
Yukinaga, whose division was routed; Ishida Mitsunari, wounded; Kuroda Nagamasa, whose towers
for musket fire Jo Gyeong's cannon broke; Ukita Hideie, the commander-in-chief, wounded by hwacha
fire; Kikkawa Hiroie, who tried to burn the palisade and was badly wounded; a sixth attack on
the second palisade, which the monks drove back; and finally Kobayakawa Takakage, whose men
broke through the monks holding the northwest inner works. Gwon Yul drew his sword and led a
counterattack hand to hand, and the line was restored. The entry's order for the fourth to
sixth divisions is not fully clear. Hawley has Ukita breaching the outer defences and reaching
the inner wall, and Kobayakawa burning a hole through the log pilings that the defenders held
until it was repaired.

The end. The defenders ran short of arrows and threw stones. Two boats under the Gyeonggi naval
commander Yi Bin came up the river carrying tens of thousands of arrows (Hawley: 10,000), and the
encyclopedia describes their arrival as a threat to the Japanese rear. The Japanese withdrew at
dusk and burned their dead. Casualty figures disagree: the encyclopedia counts over 200 bodies
left behind besides those burned; Wikipedia cites Turnbull (2002, p. 150) for 10,000 dead and
wounded. The battle is counted among the three great Korean victories of the war. The Japanese
abandoned Hanseong on 17 May 1593, after a raid burned their grain stores and after negotiations,
so Haengju was one cause of that withdrawal among several.

What the garrison did, as the sources tell it: it chose a position with a narrow approach,
built a second line behind the first, protected itself against the attackers' muskets, massed
its fire weapons, and sent a reserve, led by the commander himself, to the breach in time. Two
things outside its control also mattered: the attackers came in one division at a time, and the
boats arrived at the end. The adaptation makes the first a fixed condition of the battle (the
controller faces divisions in turn and must make the most of it) and drops the boats.

## Why this battle

| Candidate | What fits the request | Why it is not the proposal |
|---|---|---|
| **Haengju, 1593** | One day; outnumbered three to thirteen times; outer and inner lines, fire weapons, a breach and a counterattack | Proposed. It may fit one WH3 siege defence with the current orders if stage 2 shows defenders can fight on the wall; an [earlier attack test](battle-types.md#the-player-attacking-a-siege) found that no attack order reached units on a wall |
| Alesia, 52 BCE | Caesar's smaller army held its siege lines against the garrison and a larger relief army (no source checked here) | The outnumbered side was the besieger, attacked from inside and outside its own lines. WH3 siege maps put every attacker outside the walls, and the battle is famous enough to raise the recognition question that Cannae A already covers |
| Izmail, 1790 | A besieger with fewer men than the garrison stormed a strong fortress: 31,000 against 35,000 in the [article's text](https://en.wikipedia.org/wiki/Siege_of_Izmail) | Attacking a siege needs gate attacks, wall positions and equipment orders the interface lacks ([battle types](battle-types.md#the-player-attacking-a-siege)) |
| Eger, 1552 | 2,100-2,300 defenders against 35,000-40,000 ([Wikipedia](https://en.wikipedia.org/wiki/Siege_of_Eger_(1552))) | 39 days and five major assaults; the withdrawal is credited partly to Ottoman infighting, powder shortages and weather, so no single assault decided it |
| Jinju, 1592 | 3,800 soldiers against a division listed at 30,000 ([Wikipedia](https://en.wikipedia.org/wiki/Siege_of_Jinju_(1592))) | Six days; irregulars outside the walls helped decide it, and its commander fell |
| Malta, 1565 | A small garrison held a much larger Ottoman force (no source checked here) | Months long and ended by a relief army |
| Belgrade, 1456 | The defenders trapped the Janissaries who broke into the town | By some accounts the decisive sortie the next day was unordered ([Wikipedia](https://en.wikipedia.org/wiki/Siege_of_Belgrade_(1456))), and force ratios are uncertain once the crusader levies are counted |

Haengju should also lower the recognition risk the [Cannae comparison](cannae-comparison.md)
worries about; this is an argument, and nothing here measures it. The garrison's solution is a set
of ordinary defensive choices made at the right moments. A model that recognised the battle would
learn little it could not infer from the situation, and the neutral briefing below does not name
it. That does not show the model never saw the battle.

## What it adds to the benchmark

Cannae A to C are Land battles about joining manoeuvres in time. The existing siege family,
`chd-reserve-grn-siege` on the same map, sends every attacker at once; gpt-6-sol won it 3 of 3 in
the M1a screen ([log](log.md#2026-10-16-matched-round-m1-on-the-retained-core-plan)), where
gpt-6-luna lost 3 of 3, and `hold`, `attack_nearest` and `CentralDefence` each lost their one
recorded battle there ([register](results.csv)). Its suite copy `coord-siege` was not played in
the first comparison. This battle asks a different question: **can the controller spend a fixed
stock of firepower and one reserve across threats that arrive one after another, and give ground
in order when the outer line fails?**

| Dimension ([coverage](scenario-guidelines.md#coverage-across-dimensions)) | This battle | Cannae A |
|---|---|---|
| Mode and role | Siege, defender, against native AI | Land, defender, against native AI |
| Decision complexity | Sequential threats sharing one ammunition stock, one reserve and one supply pool | Concurrent dependent manoeuvres |
| Duration and horizon | Four divisions reaching the wall over about the first 10 minutes of a 20-minute timer | One main engagement |
| Resources | Finite ammunition, supplies for towers, no resupply | No missiles, supplies or spells |
| Information demand | Later divisions may be visible while they wait (stage 1 checks); when they attack is not told, and shooting a waiting division brings it on | No enemy arrives later |
| Disturbance and recovery | Breaches by ladder, tower or gate; loss of the outer line; fallback to an inner line | A wing routs |
| Objective | Hold the victory points (tickets) until the timer, or rout every division | Rout the enemy, or hold until the timer |

## Proposed battle specification

JUDGEMENT: Situation and fidelity — Claude, 2026-11-08: Haengju as a siege defence against
divisions released in turn. A literal hill fort, an all-at-once assault or another battle
changes the decisions; this plan rests on it.

The adaptation keeps the structure of the battle: one approach to a fortified line, a second line
behind it, attackers fed in by division, fire weapons with a fixed stock of ammunition, a breach,
and a commander who can lead a reserve. It drops the river, the boats and the twelve hours. The
historical force ratio is out of reach at the start: calibration begins near two to one and
raises the attacker's strength while the witness still wins. It needs no new game assets, no
historical reskin and no native multiplayer client.

JUDGEMENT: Faction pairing — Claude, 2026-11-08: a Grand Cathay garrison against Empire
divisions. An Empire mirror, as in Cannae, or another pairing changes matchups and mechanics;
the rosters and costs below rest on it.

Grand Cathay is a WH3 faction, and its Fire Rain Rocket Battery is the closest unit to a hwacha.
On 2026-11-05 the owner wrote that "we should take advantage of WH3's unique setting whenever
possible" and that "we can consider any faction as well as lords" ([owner
direction](../owner-direction.md)); choosing Cathay for that reason is this plan's proposal.
Cathay units also carry the Yin/Yang Harmony mechanic. Its exact effect on this roster must be
read from the game before anyone interprets a result, and it may be a reason to prefer the mirror.
The Empire attacker reuses known siege equipment keys and a siege setup that the [checkpoint siege
check](checkpoints.md#siege-check) already exercised on this map. Its Handgunners stand in for the
Japanese musketeers.

JUDGEMENT: Construction profile — Claude, 2026-11-08: the rosters, map and settings below as a
development start. Other force sizes, map or timer change difficulty; every balance reading
rests on it.

| Field | Proposed setting or required resolution |
|---|---|
| Mode and role | `siege`, engine type `settlement_standard`; friendly defender, native AI attacker |
| Map | `battle_preset_wh2_dlc13_minor_settlement_empire_fort` (Helmgart in [battle types](battle-types.md#the-scenarios)), described below |
| Factions | Defender subculture `wh3_main_sc_cth_cathay`, faction chosen from the nine the lobby listed in the 2026-10-13 probe (for example `wh3_main_cth_the_western_provinces`); attacker `wh_main_sc_emp_empire` / `wh_main_emp_empire`. No recorded battle has Cathay units |
| Difficulty and scale | AI very hard, AI stats modifier 1.0, large units (0.75), realism off, rank 0 |
| Timer and funds | 1,200 battle seconds; 20,000 funds, with a readback that both rosters fit |
| Siege equipment | Attacker 1 `emp_battering_ram` and 1 `emp_siege_tower_15m`, cleared and read back as in `tests/twwarhammer3/checkpoint_siege/lobby.py`; which units use them is the AI's choice |
| Toggles | Engine defaults (`behaviour_defaults: true`); friendly fire at will on at the start; the controller may change it |
| Public task | Win the battle; every engine win counts, including holding until the timer |
| Input and control | Current public observation and orders, including `build`; automated play unpaused at 1x |
| Exposure and status | Development candidate; no reserved set, no witness, no agreed readiness check |

| Defender (Grand Cathay) | Count | `multiplayer_cost` | Job |
|---|---|---|---|
| Lord Magistrate `wh3_main_cth_cha_lord_magistrate_0` | 1 | 400 | Commander; leads the reserve, as Gwon Yul did |
| Jade Warriors (sword and shield) `wh3_main_cth_inf_jade_warriors_0` | 2 | 525 each | Hold the wall or the breach; shields face the attackers' guns |
| Peasant Spearmen `wh3_main_cth_inf_peasant_spearmen_1` | 2 | 350 each | Cheap holders for the inner line, as the monks held the inner works |
| Peasant Archers `wh3_main_cth_inf_peasant_archers_0` | 2 | 400 each | Volume of fire with limited arrows |
| Jade Warrior Crossbowmen `wh3_main_cth_inf_jade_warrior_crossbowmen_0` | 1 | 600 | Armoured shooters |
| Fire Rain Rocket Battery `wh3_main_cth_art_fire_rain_rocket_battery_0` | 1 | 1,100 | The hwacha: area fire with few shots |
| Grand Cannon `wh3_main_cth_art_grand_cannon_0` | 1 | 900 | Jo Gyeong's cannon; can break the siege tower or reach a general |

| Attacker (Empire) division | Historical counterpart | Units | Cost | Release |
|---|---|---|---|---|
| D1, vanguard | Konishi | 3 Spearmen `wh_main_emp_inf_spearmen_0`, 1 Swordsmen | 1,275 | 0 s, native from the start |
| D2, guns | Ishida and Kuroda | 2 Handgunners, 2 Swordsmen | 1,950 | 150 s |
| D3, commander-in-chief | Ukita | General of the Empire `wh_main_emp_cha_general_0`, 2 Halberdiers, 2 Greatswords | 3,400 | 240 s |
| D4, final assault | Kobayakawa | 2 Greatswords, 2 Swordsmen, 1 Crossbowmen | 2,925 | 450 s |

That is 10 defending and 18 attacking units, 5,550 against 9,550 by `multiplayer_cost` (1.72
times) and about 735 against 1,464 men at large scale (2.0 times). The costs and per-unit men
were read from the installed game's `main_units_tables` with `scripts/wh3_db.py` on 2026-11-08,
with men multiplied by 0.75; the lobby charge and the recruited sizes must still be read back.
Equal cost would not mean equal strength in a siege, and this ratio is far below Haengju's. The
witness and its difficulty ladder decide how far it can rise (see
[stage 3](#development-stages)), following the owner's aim of the hardest battle that is still
demonstrably winnable.

### The map

From the first observation of `bench-b12-siege-reserve-r2-20261016/episode-0001` (x across, z from
the attacker's side to the defender's). The battlefield spans x from -384 to 384 and z from -640
to 384. The wall runs across the full width, so every attacker must come over it or through its
one gate. Its centre section with the gate lies near z = -16 and its side sections near z = -80,
and the engine's own defender start puts a unit "On high ground" near (-257, -109) on the west, so
stage 1 fixes the wall line as a polygon from the terrain grid and that start. The Gatehouse
capture point sits at (-2, -22.5) and the gate at (-32, -16). Four Fort Tower points sit on the
wall at (-62, -31), (58, -31), (-192, -81) and (188, -81); their key, `capture_point_tower_only`,
suggests each controls the towers near it, which stage 1 checks. The victory points are the Key
Building at (0, 310) and Minor Supply Locations at (-1, 155), (-320, 320) and (320, 320). Eight
empty tower slots lie behind the wall, at about (±130, 97), (±56, 192), (-299, 191), (289, 187)
and (±111, 353), with piercing towers from 500 supplies and magic towers up to 2,000. The siege
started with 6,000 supplies and gained about 9 per second, and a tower took 75 s to build
([integration](integration.md#battle-types-probed-2026-10-14)). South of the wall is open ground;
in that battle the attackers started around z = -230 to -320.

```text
 z  320    supply(-320,320)          KEY BUILDING (0,310)          supply(320,320)
 z  190         slot(-299,191)  slot(-56,192)   slot(56,192)  slot(289,187)     inner line
 z  155                            SUPPLY POINT (-1,155)
 z   97                  slot(-130,97)                    slot(130,97)
 z  -50  ====tower(-192,-81)==tower(-62,-31)==GATE(-32,-16)==tower(58,-31)==tower(188,-81)====
 z -300                               D1 (0,-300)
 z -380           D2 (-200,-380)                            D4 (200,-380)
 z -460                               D3 (0,-460)
```

The picture is a schematic built from those coordinates; it is not a deployment file. The 32 m
terrain grid does not show wall walkways, steps or height, so Helmgart's slope is unknown and
it may be flatter than Haengju's hill. The wall is the outer palisade; the inner line has no
wall and is made of the supply point, the buildings around it and whatever towers the
controller builds there.

JUDGEMENT: Placement — Claude, 2026-11-08: freeze the engine's own defender start after stage 1
and author the enemy staging above. Authored defender posts change who holds the wall at 0 s;
the opening rests on it.

The engine places siege defenders itself, and the existing siege family kept that placement.
Teleporting a unit onto a wall walkway is untested, so stage 1 reads the engine's start, and a
later version authors it only if a teleport to those points reproduces the same wall occupancy.
The staging points are proposals within open cells of the recorded grid and need route checks.

### Divisions released in turn

JUDGEMENT: Division schedule — Claude, 2026-11-08: D2-D4 held at staging, released at 150, 240
and 450 s, or early once the garrison damages one. A trigger on the previous division or an
all-at-once assault changes the sequence; the predictions below rest on it.

The mod holds D2, D3 and D4 under script control at their staging points and hands each to the
native AI at its release time. D1 is native from the first tick. This is the pattern of Cannae
B's reserve: `battle/reserve.py` materializes the resolved configuration before launch (after
the SMACv2 wrapper's reset, which it names) and the mod holds and releases the regiments. Here
the schedule is fixed and has no random draw. The garrison's guns can probably reach every
staging point (an Empire Great Cannon read a range of 450 m in `bench-b7-assault-sol-20261014`;
the Cathay ranges are unread), so a held division that the garrison damages is released at once,
and troops that may not react are never bombarded. The sequence is then the same in every launch
only while the controller leaves the waiting divisions alone. Shooting one brings it on early;
that is a legal choice, and the evaluator records it. The times aim to bring the divisions to the
wall about 150 s apart. In the cited siege trace 13 attackers covered 135-150 m in 50-62 s
(2.2-2.9 m/s), so at about 2.5 m/s D1 needs about 115 s from (0, -300), D2 and D4 about 120 s
to the side towers and D3 about 180 s to the gate, for arrivals near 115, 270, 420 and 570 s.
Stage 1 measures the real times and may move the releases before the first version is frozen.

The owner's reply 5 of 2026-11-04 allowed some scripting "if easy" and made it no priority for
the initial scenarios ([owner replies](scenario-guidelines.md#current-plan-and-owner-decisions)),
and the guidelines prefer conditions native AI can produce. This plan needs a script because in
the existing siege family's battles native AI starts its whole army together, and the sequence
is the point of this battle. Cannae B's scripted reserve is the precedent and the code to start
from; decision 2(c) is the option without a script.

Native AI may behave differently with part of its army held. It may wait, attack piecemeal or
use the siege equipment late. Stage 1 records what it does, and the plan changes if the released
divisions do not attack.

### Public briefing

JUDGEMENT: Public presentation — Claude, 2026-11-08: neutral names and factual rules, plus one
sentence that divisions may attack at different times. Saying nothing or giving the times
changes the information demand; comparisons rest on it.

The scenario and job names stay neutral (for example `cth-emp-siege-a-v1`), because the job name
is part of the observation. The briefing gives the engine's objective text (already in `mode`),
the timer and that holding until it counts as a win, the tickets, the public enemy roster, and one
sentence: "The attacking army is drawn up in several divisions, which may attack at different
times." It gives no times, no history and no recommended tactic. It does not say that shooting a
waiting division brings it on; the division's movement shows that. Release times live only in
evaluator records, and a test of the rendered prompt checks they never appear there.

## Decisions the battle could test

These are design predictions to test in development. A controller may win by any legal play, and
a prediction that fails narrows this page's interpretation without touching the win.

| Public cue | Feasible choices | Expected consequence, and what would reverse it |
|---|---|---|
| D1 comes into range while D2-D4 stand at staging | Shoot D1 with everything; shoot only what threatens the gate; let the melee line hold it | If ammunition is sized in stages 2-3 to last about two or three divisions at full fire, firing at will on every division should leave the rockets and archers empty when D3 and D4 arrive. If D1 alone can take the wall when left unshot, holding fire loses sooner |
| Attackers come over the wall by ladder or tower, or the gate falls | Send the reserve to the breach now; keep it central | Attacking while only part of a division is up should destroy it piecemeal. Ladders can put attackers on several wall sections at once, and then committing the only reserve to the first breach may lose the second |
| Several enemy regiments are inside the wall and the Fort Tower points fall | Fall back to the inner line; keep fighting on the wall | Falling back keeps units and uses the inner towers. If no inner towers were built in time, the inner line has no fire support and holding may be better |
| 6,000 supplies at 0 s and about 9 more per second | Which slots get towers, which option, and when | Eight piercing towers cost 4,000, so the cheapest option needs no choice, and about 10,800 more supplies arrive over 1,200 s. The choice is where the dearer options (900 to 2,000) go and when. The nearest slots are about 110 m behind the gate, so every tower supports a fight inside the wall or at the inner line. A tower takes 75 s, so a late purchase may finish after its fight |
| D3's General comes into range | Aim the cannon and rockets at him; keep shooting the troops | Killing the army's general should weaken every remaining division's morale. If he stays behind his men, chasing him spends shots for nothing |

In the [specification form](scenario-guidelines.md#the-scenario-specification):

- **D1 ammunition.** When D1 is in range and later divisions are visible at staging, firing at
  will and selective fire are both feasible. With missile ammunition sized for about two or three
  divisions, they should differ in how much of D3 and D4 is shot before contact. If D1 can take
  the wall unshot, or ammunition is plentiful, the difference disappears.
- **D2 breach.** When attackers come over the wall or the gate falls, sending the reserve and
  keeping it are both feasible. Sending it early should cost fewer regiments at the breach. If
  two breaches open together, which ladders make likely, the prediction can reverse.
- **D3 fallback.** When the outer line is lost, withdrawing and holding are both feasible.
  Withdrawal should keep more units able to fight and keep the victory points longer when inner
  towers stand. Without inner towers it may lose that advantage.

## How it would be built

Nothing below is approved for implementation. Each row would get its own card when it is.

| Component | What can be reused | New work |
|---|---|---|
| [`scenarios.json`](../../configs/twwarhammer3/scenarios.json), [`battle/setup.py`](../../src/twwarhammer3/battle/setup.py) | Rosters, settings, `expect`; siege mode setup and engine type check; `deployment`, never used in a siege yet | A `siege_equipment` field, moving the checkpoint lobby helper's clear-and-read-back steps into setup; one development declaration |
| [`battle/reserve.py`](../../src/twwarhammer3/battle/reserve.py) and the mod's reserve hold | Materialize before launch; hold regiments; release to native AI; evaluator-only records | A `waves` profile with several groups and release times, the release on damage, and their records. A Lua change moves the pack hash and so each card cell's setup identity |
| [`battle/play.py`](../../src/twwarhammer3/battle/play.py) | Briefing view, reserve evidence, manifests, ledgers, register rows | Pass the waves profile and its briefing; record releases privately |
| [`battle/manual_demo.py`](../../src/twwarhammer3/battle/manual_demo.py) | Owner recording with pauses | It refuses `reserve` because the hold does not run under the observer session; the waves must run there before the owner can demonstrate this battle |
| [`battle/scripted.py`](../../src/twwarhammer3/battle/scripted.py), [`battle/evade.py`](../../src/twwarhammer3/battle/evade.py), `calibration.py:CentralDefence` | `Hold`, `AttackNearest`, `RushNearest`, `Evade`, the earlier siege fallback | A witness and two fixed-plan controls (below) in a new module |
| Trace, replay, `digest`, `stats`, report | Outcome, unit condition, `victory_held`, `key_held`, supplies, builds | Per-division readings (below), descriptive only |

Offline tests worth adding with that work, each with a plausible wrong version it must catch:
the schedule refuses a malformed profile and saves the resolved one (must fail on a division
bound to the wrong unit type); the rendered prompt from a recorded first observation holds no
release time (must fail on a time planted in the brief or job name); the Lua hold keeps held
units still and releases them by name (must fail on a planted early release); and the setup
steps read back the equipment counts (must fail on a leftover ram from the last lobby).

## Development stages

Each stage reports counts and failures; none verifies anything until a check is agreed. Game time
starts only when the owner names the stage.

| Stage | What runs | Cost and time | What it can establish |
|---|---|---|---|
| 0 | Owner answers; implementation of the rows above under their cards; `check.py` | $0, offline | That the code does what its tests say |
| 1 | Two or three setup launches with `hold` | $0, about 20-40 min of game time | Readbacks (Cathay recruitment, equipment, settings), whether `deployment` places the staged divisions in a siege, the engine's defender start, the wall polygon, visibility of staged divisions, ranges, travel times, what native AI does with held divisions, and whether held units count for the battle's end. A hold battle also gives the first floor result |
| 2 | One or two probe launches | $0, about 20 min | That a move order puts a unit on the wall, `fire_at_will` off stops ammunition falling, a build at an inner slot finishes in about 75 s, and attack orders reach attackers on the wall, ladders and tower (an earlier attack test found none reached units on a wall) |
| 3 | Shortcut controls, then the witness, then a difficulty ladder | $0, about 10-14 launches, 3-4 h | Whether a simple rule wins; whether the witness wins at a model-like timing; the hardest step it still wins, one factor per step (a fifth division, stronger D4, fewer arrows, rank) |
| 4 | The owner's manual demonstration, once the recorder supports the waves | Owner's time | Human-demonstrated winnability of the frozen version |
| 5 | A first model pilot, if the owner wants one | Paid, owner's budget and arms | Exploratory model results on a development battle; no ranking |

## Proposed deciding checks

JUDGEMENT: Deciding checks draft — Claude, 2026-11-08: the rows below, one launch per attempt,
with the counts and plants shown. Other rules change what each stage may claim; every label
rests on it.

These are proposals for the owner to accept or change; none is in
[agreed checks](../agreed-checks.md).

| # | Claim | Cases and evidence | Count and rule | Must fail on |
|---|---|---|---|---|
| 1 | Constructed | Every stage 1-3 battle; lobby readback and the private first reading | Map, mode, role, difficulty, modifier, scale, timer, funds, rosters and equipment counts match; every staged unit within 25 m of its point, bearing within 5 degrees (Cannae row 1 found a constant 2.8-degree offset) | A swapped roster unit; a leftover ram; a division staged 100 m off |
| 2 | Divisions held and released | The 1 Hz replay in the same battles, which never reaches a policy; stage 1 first checks that it records held units out of sight | Each held unit stays within 15 m until its release; each released division moves within 10 s; none moves early unless a held unit was damaged first | A planted release 60 s early; a division never released |
| 3 | Information boundary | Rendered prompt and observation JSON from a recorded first observation | No release time, staging label or historical name in any model input | A release time planted in the brief or job name |
| 4 | Orders reach effects | Stage 2 probes, with trace and video | Each of the four effects in stage 2 seen once from order to engine effect | An accepted move whose unit never reaches the wall |
| 5 | Human win | `uv run --locked python -m twwarhammer3.battle.manual_demo record --scenario S --output DIR --ffmpeg FFMPEG --timeout SECONDS`, after the recorder change | One engine win; every attempt kept; pauses labelled from video | A recorder that starts the battle when the waves cannot run there; it must refuse |
| 6 | Shortcuts | `hold`, `rush_nearest`, the keep-only and wall-only controls, `Evade`, one launch each | Reported only; a win is kept and narrows the label | Nothing; it is reported only |
| 7 | Interface witness | The witness at its named order age and decision interval, fresh launches | Reported with the timing ([guideline 2.3](evaluation-guidelines.md#23-show-the-card-can-be-won-at-a-named-timing)); counts chosen with the owner | A witness win credited at a timing it did not play |

## Controls

- `hold` (no orders; the engine shoots and fights on its own) and `rush_nearest`: the floor and
  the naive plan. A hold win would mean the walls and towers win this battle without a commander.
- **Keep only**: every unit walks to the Key Building at 0 s and stays. A win by the timer would
  show the outer line is not needed, and the claim about giving ground in order would narrow.
- **Wall only**: every unit holds the wall with fire at will on, never falls back and builds
  nothing. It separates holding the wall from scheduling ammunition and the fallback.
- **Witness**: a public-state script for the garrison's plan. It builds piercing towers at the
  inner slots at 0 s, keeps missile units on the wall with fire at will off until a division is
  within a set range of the wall, sends the Lord and both Jade Warriors to any enemy regiment
  inside the wall polygon, and moves everyone to the inner line once a set number of enemy
  regiments are inside. Its thresholds are construction parameters to be marked when it is
  written.
- **Witness with fire at will always on**: the same script with one rule removed, to test whether
  ammunition scheduling matters here (the D1 prediction).
- **Fixed schedule**: the witness's orders from a winning battle replayed by battle time on fresh
  launches, to test whether reacting to the divisions matters.

A model loss counts against the battle's interpretation only when a control or the witness shows
a winning continuation existed at a similar timing. A shortcut win stays a win.

## Measurements and interpretation

The engine outcome stays primary. Existing readings carry over: unit health, men and morale
state, `victory_held`, `key_held`, supplies left, builds, order age, refusals and cost. The owner's
interest in health and morale and a later overall ranking applies; this page adds no formula.

| Reading | Source and limit |
|---|---|
| Release and first sighting of each division | Evaluator record and the first public observation that shows any of its units; never moves the policy's knowledge earlier |
| Early releases | Which division, at what time, and the friendly unit whose shot caused it, from the evaluator record |
| Ammunition left at each release and at each division's first wall contact | Friendly `ammo` and `ammo0`; spent shots are not hits |
| Breach time | Gate `hp` and `destroyed`, and the first enemy regiment centre inside the wall polygon; a centre near the wall does not prove a unit is on it, and a unit climbing a ladder may not show inside yet |
| Reserve response | Time from breach to the reserve's attack order and to its melee; an order alone is not an effect |
| Outer line lost and fallback | Fort Tower holders and friendly positions over time |
| Towers | Build order, completion and the zone's holder; a standing tower is not proof that it fired |
| General | Time of the General's death or rout, if any, and the morale of other divisions after it |

All readings are descriptive until a check ties them to the decision. Missing values stay unknown.

## Variation and the eventual run plan

The first version is one fixed battle for development. Later variants could swap which division
carries the elite troops, move the General to the last division, shift a release by 60 s, or
change which side D4 stages on. Each changes one thing and predicts what should change; until the
owner chooses a reservation policy, every inspected variant is development evidence. An
announced-schedule arm, where the briefing gives the release times, is the foreknowledge control
in the style of Cannae B. A team version could split the garrison into wall, reserve and
artillery commands for the [communication structure](communication-structure.md) work, after the
single-controller version is understood. Before any scored run, a frozen experiment card
gives the arms, launches, stop rule, budget and analysis, as the
[Cannae run plan](cannae-eval.md#variation-and-the-eventual-run-plan) lists.

## Risks that would change the design

| Risk | What stage shows it | Response |
|---|---|---|
| Native AI idles or acts oddly with divisions held | 1 | Stage the divisions at different distances and release all at once, or trigger each release on the previous division's rout, as a new version |
| The siege tower or ram is used by a division nobody intended, or not at all | 1 | Record it; choose the equipment count again |
| Towers and supplies decide the battle alone | 3 (`hold`, wall only) | No lobby setting for starting supplies is known; a version without tower slots, or another map |
| Ammunition never runs short | 3 | Fewer missile units or stronger divisions, one step at a time |
| Keep only wins by the timer | 3 | Keep the win; narrow the claim, or ask the owner about a different timer or objective |
| Cathay cards do not recruit, or Harmony dominates | 1 | Fall back to the Empire mirror |
| The recorder cannot run the waves | 0 | No human demonstration until it can; the witness gives interface evidence meanwhile |
| A held unit is not counted as present, so the battle ends early | 1 | Release all divisions and use staging distance instead |
| Attack orders cannot reach attackers on the wall or ladders | 2 | The reserve meets them where they come down into the fort, by move orders, and the breach prediction then concerns those moves |

## Decisions for owner review

Three questions, with the recommendation first:

1. **Battle and pairing.** (a) Haengju with a Grand Cathay garrison against Empire divisions
   (recommended): uses WH3's own faction and a rocket battery like the hwacha, at the cost of
   checking Cathay recruitment and Harmony first. (b) Haengju as an Empire mirror: fewer new
   mechanics, matches Cannae, loses the WH3-specific part. (c) Another battle from
   [the candidates](#why-this-battle).
2. **How divisions attack.** (a) Fixed release times, and a division the garrison shoots comes on
   at once (recommended): the same sequence in every launch unless the controller shoots a waiting
   division, which is recorded. It is a scripted opponent, which the owner's reply 5 made no
   priority; Cannae B is the precedent. (b) Each division released when the previous one routs:
   closer to the history, but the sequence then depends on the controller's play throughout.
   (c) No script; native AI attacks at once from staggered distances: no new script, and the
   sequence may collapse into one assault.
3. **What the briefing says.** (a) Rules plus "divisions may attack at different times"
   (recommended). (b) Rules only. (c) Rules and the release times, as a foreknowledge arm.

Other open choices: the construction profile, placement and deciding checks (marked above);
whether the garrison has a lord (the roster has one because Gwon Yul led the counterattack, and
Cannae started lordless); which stages may start; whether the recorder change for the owner's
demonstration comes first; and any budget for stage 5.

## Sources

Read for this plan on 2026-11-08; listed in [references](../references.md#haengju-siege-evaluation-plan-2026-11-08).
The historical account guides the design and is no evidence about the engine.

- [Encyclopedia of Korean Culture, 행주대첩](https://encykorea.aks.ac.kr/Article/E0062859): preparations,
  forces, the seven divisions, the northwest breach, arrows and boats. Read through a translation.
- [Wikipedia, Battle of Haengju](https://en.wikipedia.org/wiki/Battle_of_Haengju), citing Hawley,
  *The Imjin War* (2005), pp. 318-323, Swope (2009) and Turnbull (2002): forces, turns, breaches,
  arrows, casualties and aftermath. Secondary.
- M. G. Haynes, [Military Heritage article](https://warfarehistorynetwork.com/?p=100625): narrow
  approach, hwacha, breach. Popular, cites no sources.
- Wikipedia, [Siege of Eger (1552)](https://en.wikipedia.org/wiki/Siege_of_Eger_(1552)),
  [Siege of Jinju (1592)](https://en.wikipedia.org/wiki/Siege_of_Jinju_(1592)),
  [Siege of Belgrade (1456)](https://en.wikipedia.org/wiki/Siege_of_Belgrade_(1456)) and
  [Siege of Izmail](https://en.wikipedia.org/wiki/Siege_of_Izmail): the rejected candidates'
  figures. Secondary. Alesia and Malta are described from general knowledge, with no source checked.
