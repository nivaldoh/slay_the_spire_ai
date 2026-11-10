# Haengju inspired siege evaluation plan

Development candidate (Claude). Written on 2026-11-08 as a plan, brought in line with the offline
build on 2026-11-09 and revised after that day's second look at the set. **Built offline at
`f3fec92`; no battle has been played, and everything on this page is unverified.** The 2026-11-10
lobby-only readback passed the all-at-once declaration's 10/18 rosters, ranks and empty attacker
equipment list; the divisions declaration generates identical lobby steps and was not sent
separately ([readings](historical-evals.md#first-lobby-readbacks-2026-11-10)). On
2026-11-08 the owner asked for a second evaluation
battle: a real siege in which one side had a clear disadvantage and still won through better
tactics. Later that day the owner asked to build the good battle ideas now and to play them only
when the owner says so ("Build now, game when I say", [owner direction](../owner-direction.md)).
This page adapts the defence of Haengju fortress in Korea on 14 March 1593 as a WH3 siege battle:
the controller defends a walled fort with a small Grand Cathay garrison while a larger Empire army
comes at it in divisions released in turn. The declarations are `cth-emp-siege-a-v1` (divisions in
turn) and `cth-emp-siege-a-all-v1` (the same armies all at once) in
[scenarios.json](../../configs/twwarhammer3/scenarios.json). The hold and release are reserve
profile version 3 in [battle/reserve.py](../../src/twwarhammer3/battle/reserve.py) and the battle
Lua, the witness and its controls are in
[battle/wall_defence.py](../../src/twwarhammer3/battle/wall_defence.py), the readings are in
[battle/wall_readings.py](../../src/twwarhammer3/battle/wall_readings.py), and the offline tests are
[test_wh3_waves.py](../../tests/twwarhammer3/test_wh3_waves.py),
[test_wh3_wall_defence.py](../../tests/twwarhammer3/test_wh3_wall_defence.py),
[test_wh3_wall_readings.py](../../tests/twwarhammer3/test_wh3_wall_readings.py) and the waves tests
in [test_wh3_manual_demo.py](../../tests/twwarhammer3/test_wh3_manual_demo.py). No stage is
scheduled; every live stage below waits for a window the owner names. The design, the review of
the set of five siege designs and the build records are in `runs/siege-evals-20261108/`
(`final-haengju.md`, `portfolio.md`, `lua-batch.json`), which Git does not keep. The owner's
choices are collected in [decisions for owner review](#decisions-for-owner-review).

The plan follows the [scenario guidelines](scenario-guidelines.md), the
[evaluation guidelines](evaluation-guidelines.md) and the [benchmark contract](benchmark.md):
fixed armies, public structured observations, permitted orders, every engine win counts (timer
wins included), and automated play runs unpaused at 1x. It reuses what the
[Cannae plan](cannae-eval.md) and its two windows taught: resolve every placement before
evaluating anything, check that orders reach their effects, keep shortcut wins as wins, and expect
one battle per case to settle nothing. Its deciding checks use the rules that Claude's 2026-11-08
review of the set (`portfolio.md`) proposed for every new battle, none of them agreed with the
owner: one primary contrast per battle at two-sided Fisher p < 0.05
([battle/exact_stats.py](../../src/twwarhammer3/battle/exact_stats.py)) with its exact power
printed in advance; a frozen 4-of-5 witness gate at 5 s added order age and a 5 s decision
interval before any round; premise checks that print their own error rates; contact from the
engine melee flag and a gate breached at public hp 0 or below
([battle/evidence_rules.py](../../src/twwarhammer3/battle/evidence_rules.py)). The
[overview of the set](historical-evals.md) lists these rules; using one set for every new battle
rests on JUDGEMENT docs/twwarhammer3/historical-evals.md Shared method rules, and this battle's
counts and cells rest on the Deciding checks draft marker below. Under the
[hard rule](../../AGENTS.md#verification-hard-rule) everything below is unverified, and the counts
from earlier battles come from recorded battles with other armies, mostly one battle each. The
history guides the design and is no evidence about the engine.

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
| **Haengju, 1593** | One day; outnumbered three to thirteen times; outer and inner lines, fire weapons, a breach and a counterattack | Chosen, and built offline at `f3fec92`. It fits one WH3 siege defence with the current orders if stage 2 shows defenders can fight at the wall; an [earlier attack test](battle-types.md#the-player-attacking-a-siege) found that no attack order reached units on a wall |
| Alesia, 52 BCE | Caesar's smaller army held its siege lines against the garrison and a larger relief army (no source checked here) | The outnumbered side was the besieger, attacked from inside and outside its own lines. WH3 siege maps put every attacker outside the walls, and the battle is famous enough to raise the recognition question that Cannae A already covers |
| Izmail, 1790 | A besieger with fewer men than the garrison stormed a strong fortress: 31,000 against 35,000 in the [article's text](https://en.wikipedia.org/wiki/Siege_of_Izmail) | Attacking a siege needed gate attacks, wall positions and equipment orders that the interface lacked when this plan was written ([battle types](battle-types.md#the-player-attacking-a-siege)); `f3fec92` built them offline for its own declaration, `ksl-emp-siege-a-v1` |
| Eger, 1552 | 2,100-2,300 defenders against 35,000-40,000 ([Wikipedia](https://en.wikipedia.org/wiki/Siege_of_Eger_(1552))) | 39 days and five major assaults; the withdrawal is credited partly to Ottoman infighting, powder shortages and weather, so no single assault decided it |
| Jinju, 1592 | 3,800 soldiers against a division listed at 30,000 ([Wikipedia](https://en.wikipedia.org/wiki/Siege_of_Jinju_(1592))) | Six days; irregulars outside the walls helped decide it, and its commander fell |
| Malta, 1565 | A small garrison held a much larger Ottoman force (no source checked here) | Months long and ended by a relief army |
| Belgrade, 1456 | The defenders trapped the Janissaries who broke into the town | By some accounts the decisive sortie the next day was unordered ([Wikipedia](https://en.wikipedia.org/wiki/Siege_of_Belgrade_(1456))), and force ratios are uncertain once the crusader levies are counted |

After this choice the owner asked to build the other good ideas as well. Belgrade's sortie became
the Land battle in [camp-eval.md](camp-eval.md), Alesia's last day the Land battle in
[lines-eval.md](lines-eval.md), and Izmail the siege attack `ksl-emp-siege-a-v1`; Malta was not
built.

Recognition is a risk here, as in the [Cannae comparison](cannae-comparison.md). The lesson the
sources record at the end of the battle, that the defenders ran short of arrows, is this battle's
claim: a model that recognised the battle could reach the witness's fire rule from its memory of
the history, without reading the situation. The neutral names and briefing below do not name the
battle, but this page and the witness's code are in a public repository, and nothing here measures
recognition. Until a recognition probe exists, or a variant in which the historical choice should
not help (the all-at-once arm is the nearest), a model's win here cannot separate recognition from
a decision made on the spot. The [overview](historical-evals.md) lists these options for the owner.

## What it adds to the benchmark

Cannae A to C are Land battles about joining manoeuvres in time. The existing siege family,
`chd-reserve-grn-siege` on the same map, sends every attacker at once; gpt-6-sol won it 3 of 3 in
the M1a screen ([log](log.md#2026-10-16-matched-round-m1-on-the-retained-core-plan)), where
gpt-6-luna lost 3 of 3, and `hold`, `attack_nearest` and `CentralDefence` each lost their one
recorded battle there ([register](results.csv)). Its suite copy `coord-siege` was not played in
the first comparison. This battle asks a different question: **can the controller spend a fixed
stock of firepower across threats that arrive one after another?**

| Dimension ([coverage](scenario-guidelines.md#coverage-across-dimensions)) | This battle | Cannae A |
|---|---|---|
| Mode and role | Siege, defender, against native AI | Land, defender, against native AI |
| Decision complexity | Sequential threats sharing one ammunition stock, one reserve and one supply pool | Concurrent dependent manoeuvres |
| Duration and horizon | Four divisions reaching the wall at an estimated 100, 270, 445 and 570 s of a 1,200 s timer | One main engagement |
| Resources | Finite ammunition (172 shots and rockets across the five missile units by database values), 6,000 supplies for towers and about 9 more per second, no resupply | No missiles, supplies or spells |
| Information demand | Held divisions stand 449-559 m from the public wall line, and whether they are visible there is unread (stage 1); the release times are not told, and damaging a waiting division brings it on | No enemy arrives later |
| Disturbance and recovery | Breaches by ladder only: version 1 has no ram, no siege tower and no attacker that can damage the gate (every Empire unit key in it reads `can_siege` false), so the gate can pass to the attackers only with the Gatehouse point `c2` (unverified live); loss of the outer line; fallback to the Key Building | A wing routs |
| Objective | Hold until the timer, a defender's win no recorded siege has reached, or rout every division; tickets fall once the Key Building is lost | Rout the enemy, or hold until the timer |

The overlap with `chd-reserve-grn-siege` is large, and the design states it. That family has the
same map, mode and role, and its brief is "Trade outer territory for time while committing one
mobile reserve and limited construction supplies"; its whole army attacks at once. This battle
adds four things: divisions released in turn, missile ammunition that runs out across them, a
Grand Cathay garrison (rockets, Harmony and Cathay towers), and siege equipment set and read back
(none in version 1). The reserve and fallback decisions repeat that family's, and the review of the
set counts reserve allocation once, in [lines-eval.md](lines-eval.md), so this battle claims only
the fire decision and keeps the other two exploratory (rests on JUDGEMENT
docs/twwarhammer3/historical-evals.md Claim assignment). The all-at-once arm
`cth-emp-siege-a-all-v1` is that family's condition with a Cathay garrison. It checks that the
script changes the battle (check 7) and claims no decision.

## How the siege mode fits

The owner's 2026-11-08 instruction was to adapt each battle well to WH3's game modes. The siege's
own rules carry most of Haengju's structure. The rules below come from the installed game's help
text, read locally for the design and not copied here, and from recorded traces.

| Haengju | WH3 siege rule | Fit |
|---|---|---|
| Outer palisade attacked by storm | A wall with one gate; infantry scale it with native ladders | Good |
| Losing the outer line costs fire support | Whoever holds a capture point holds the gate or tower linked to it; losing a supply point destroys its linked defences | Good, unverified live |
| Inner works must hold; flight impossible | Defender tickets fall only after the Key Building (`c1`) is enemy-held, and a defender holding it gets a boost for its units inside the walls | Good; recorded on one map |
| Hold until dusk | The defender wins at the time limit (objective text) | Never observed in a siege |
| Divisions in turn | Native AI attacks with the whole army | Script required |
| Self-built double palisade | Helmgart has 8 tower slots, no barricade slots, and 6,000 supplies | Weak; construction is not claimed |
| Kuroda's musket towers | A siege tower exists, but which division mans it is the AI's choice | Deferred to a variant |
| Repair of the pilings, the boats | No equivalent; walls cannot be repaired | Dropped |

Recorded facts behind the table, each from the design's recount on 2026-11-08 unless named. In the
19 recorded `chd-reserve-grn-siege` family battles on Helmgart, tickets fell in 4, each starting
within 1.2 s of the Key Building turning enemy, at about 5 per second. 8 were won and 11 lost, none
reached the 1,200 s timer (the longest ended at 962.6 s), and every loss ended with 145 to 1,000
defender tickets left, so the garrison broke before its tickets ran out. The review of the set
found that all 16 `time_limit` rows in the register are classic Land battles, so a siege timer win
has never been observed. In the
`hold` battle of that family (`bench-b12-siege-baselines-20261016/episode-0001`, a Chaos Dwarf
garrison) the Gatehouse was enemy-held at 336.7 s, `c7` at 467.8 s and `c1` at 699.1 s, the
defender's tickets first read below 1,000 at 700.3 s, and the battle was lost at 708.7 s; the
build and its review counted the holder and ticket times again by hand. In the same battle the
gate at (-32, -16) read hp 0 with `destroyed` false from 258.4 s to the end, as a gate did in
`smoke-random-siege-skills-20261014-0511` from 179.5 s, so every gate cue here reads hp 0 or
below (rests on JUDGEMENT src/twwarhammer3/battle/evidence_rules.py Breach rule). At 5.2 s three
of the four Fort Tower points were neutral and their holders flickered afterwards, so no cue reads
Fort Tower holders.

Every recorded fact above comes from a build older than the pinned one, patch 9.0.5, Steam build
26403568 ([pins](integration.md#pins)), whose patch includes battle balance changes. By each job's
`environment.json`, the 19 family battles, `bench-b12-siege-baselines-20261016` and
`bench-b12-siege-reserve-r2-20261016` ran on 9.0.4 (Steam build 25961564), and
`smoke-random-siege-skills-20261014-0511` on 9.0.3 (25823491), as did every 2026-10-14 run that
recorded its build, the day of the battle-type probes cited for supplies and tower build time. The
checkpoint siege check's runs of 2026-11-03 (`siege-905-20261103`) read the pinned build. The
database values on this page were read on 2026-11-08 and 2026-11-09, after Steam's 2026-11-03
update; the reads did not record the build. Two older-build facts carry weight here. Check 5
re-reads the first, the ticket onset, in every stage 1-5 battle on the pinned build, stages 1a-1c
first. The second, the gate at hp 0 with `destroyed` false, cannot be re-read in version 1, which
has no attacker that can damage the gate; only the optional stage 1e, with its ram, could read it
here, and until then the Breach rule rests on the 9.0.3 and 9.0.4 readings.

The other modes fit worse. The unfortified settlement has no tickets, and its objective text, as
the design read it in the Osterwald traces, counts any surviving unit at the timer as a win, so
running away would be a structural shortcut there. Its scarce barricade supplies match Jo Gyeong's
palisades, which were built before the assault, so they would be a fixed starting condition and no
decision in battle. A conquest battle drops the fortification. What does not fit the siege is
stated above: native AI does not send its divisions in turn, construction is no real choice on
Helmgart, and the walls cannot be repaired.

## Battle specification

In the fields of [the scenario specification](scenario-guidelines.md#the-scenario-specification):

| Field | This battle |
|---|---|
| Question and coverage | Whether the controller can spend a fixed stock of firepower across divisions that arrive one after another ([D1](#decisions-the-battle-could-test), the one claim); the reserve and the fallback are exploratory. Siege defence against native AI. Claims excluded: construction, reserve allocation (counted in [lines-eval.md](lines-eval.md)), recognition of the battle, model ability |
| Public task | Win the battle; every engine win counts, the defender's timer win at 1,200 s included. The public observation and orders, `build` included, unpaused at 1x, with one briefing sentence; `llm` also reads its prompt's How to fight advice ([public briefing](#public-briefing)) |
| Concrete setup | [Settings](#settings), [rosters](#rosters), [the map](#the-map) and [divisions released in turn](#divisions-released-in-turn). Patch 9.0.5, Steam build 26403568 (the pin); Grand Cathay (`wh3_main_cth_`) and Empire (`wh_main_emp_`) unit keys, whose owning packs are unverified. `cth-emp-siege-a-v1` is `cth-emp-siege-a-all-v1` plus `reserve`, `name` and `brief` |
| Decision opportunity | [D1](#decisions-the-battle-could-test): the fire cue, two fire settings, and D3's first approach at an estimated 445 s |
| Mechanic reference | [How the siege mode fits](#how-the-siege-mode-fits), from the game's help text and 9.0.3-9.0.4 traces; ammunition, ranges and costs by database values; no version 1 attacker can damage the gate; whether a gate at hp 0 lets units through is unread |
| Winnability evidence | None yet: the owner's demonstration (check 10) and the frozen witness gate (check 9) |
| Controls and predictions | [Witness, ablations and controls](#witness-ablations-and-controls-as-built) and the predictions in [decisions](#decisions-the-battle-could-test) |
| Measurements | [Measurements](#measurements) |
| Variation and exposure | The waves arm, the all-at-once arm and the Eagle Gate screen `cth-emp-siege-a-all-gates-v1`, all split `development`; no held-out or reserved variant; this page and the code are public |
| Validation plan | [Proposed deciding checks](#proposed-deciding-checks) and [development stages](#development-stages) |
| Release record | Lua and pack hash from `f3fec92`; the Eagle Gate screen declared at `050020e`; the readings and tests revised on 2026-11-09; `prototype_not_admitted`; no battle played |

JUDGEMENT: Situation and fidelity — Claude, 2026-11-08: Haengju as a siege defence against
divisions released in turn. A literal hill fort, an all-at-once assault or another battle
changes the decisions; this plan rests on it.

The adaptation keeps the structure of the battle: one approach to a fortified line, a second line
behind it, attackers fed in by division, fire weapons with a fixed stock of ammunition, a breach,
and a commander who can lead a reserve. It drops the river, the boats and the twelve hours. The
historical force ratio is out of reach at the start: the build starts at 1.72 times by cost, and
the ladder raises the attacker's strength while the witness still wins. It needs no new game
assets, no historical reskin and no native multiplayer client.

JUDGEMENT: Faction pairing — Claude, 2026-11-08: a Grand Cathay garrison against Empire
divisions. An Empire mirror, as in Cannae, or another pairing changes matchups and mechanics;
the rosters and costs below rest on it.

Grand Cathay is a WH3 faction, and its Fire Rain Rocket Battery is the closest unit to a hwacha.
On 2026-11-05 the owner wrote that "we should take advantage of WH3's unique setting whenever
possible" and that "we can consider any faction as well as lords" ([owner
direction](../owner-direction.md)); choosing Cathay for that reason is this plan's proposal.
Cathay units also carry the Yin/Yang Harmony mechanic. Its exact effect on this roster must be
read from the game before anyone interprets a result, and it may be a reason to prefer the mirror.
The Empire attacker reuses a siege setup that the [checkpoint siege
check](checkpoints.md#siege-check) already exercised on this map. Its Handgunners stand in for the
Japanese musketeers.

JUDGEMENT: Construction profile — Claude, 2026-11-08: scenarios.json cth-emp-siege-a-all-v1
rosters, map, expect and siege_equipment {} (no ram or tower) as a development start. Other
forces, map, timer or equipment change difficulty and breaches; every balance reading rests on it.

### Settings

| Field | Setting at `f3fec92` |
|---|---|
| Declarations | `cth-emp-siege-a-all-v1` is the base; `cth-emp-siege-a-v1` is the base plus `reserve`, a new `name` and `brief`, and a declaration test checks that they differ in nothing else. Both: `scenario_version` 1, family `siege defence`, split `development`, status `prototype_not_admitted` |
| Mode and role | `battle_type` `siege`, `expect.battle_type` `settlement_standard`; `attacker` `enemy`, `expect.player_defends` true; native AI attacker; the defender wins at the timer |
| Map | Helmgart, `battle_preset_wh2_dlc13_minor_settlement_empire_fort` ([battle types](battle-types.md#the-scenarios)), described below |
| Factions | Defender `wh3_main_sc_cth_cathay` / `wh3_main_cth_cathay_mp`; attacker `wh_main_sc_emp_empire` / `wh_main_emp_empire`; both with a lord. `units_custom_battle_permissions_tables` lists the seven Cathay cards only under `wh3_main_cth_cathay_mp` (read for the build on 2026-11-08), so this plan's earlier example `wh3_main_cth_the_western_provinces` would need it as `recruitment_faction`; this rests on JUDGEMENT tests/twwarhammer3/test_wh3_waves.py Cathay lobby faction. No recorded battle has Cathay units |
| Difficulty and scale | `ai_level_very_hard`, `ai_stats_modifier` 1.0 (the `chd-reserve-grn-siege` family used 1.1), `unit_scale` 0.75, realism off, rank 0 for every unit |
| Timer and funds | 1,200 s, the shortest lobby option (`setup.TIMERS`: 1,200, 2,400 or 3,600); `funds_custom` 20,000, with readback |
| Siege equipment | `siege_equipment: {}`: the lobby steps clear every piece from the attacker's slot and read back size 0 before Start, and `check_battle` requires the battle's first reading of assault equipment to hold none (rests on JUDGEMENT src/twwarhammer3/battle/setup.py Battle-side equipment check). The game's custom-battle vehicle table gives Empire rams and towers generation probabilities, and whether the engine adds equipment to an empty list is unread |
| Toggles | No `behaviour_defaults`, so the engine's own toggles stay (defend and fire at will were on in the recorded siege); the controller may change them. This rests on JUDGEMENT tests/twwarhammer3/test_wh3_waves.py Siege toggles |
| Script | `cth-emp-siege-a-v1`: reserve profile version 3 (`waves`), [below](#divisions-released-in-turn); `cth-emp-siege-a-all-v1`: none |
| Records | `private_record: true`: the mod writes the evaluator-only all-unit record once per engine second, which `play` and the recorder copy to `private.jsonl` and no controller input carries |
| Withheld words | 19 historical names (`haengju`, `gwon`, `gyeong`, `konishi`, `hwacha` and others), which no controller input may hold (rests on JUDGEMENT? tests/twwarhammer3/test_wh3_waves.py Withheld words) |
| Public task | Win the battle; every engine win counts, including holding until the timer |
| Input and control | The current public observation and orders, including `build`; automated play unpaused at 1x |
| Exposure and status | Development candidate; no reserved variant, no lobby readback, no agreed check |

### Rosters

Costs are `main_units_tables` `multiplayer_cost`, and men are its `num_men` times 0.75 with single
entities as 1, both read from the installed game with `scripts/wh3_db.py` on 2026-11-08 and
recomputed for this page from the build's saved rows. Missile values are base database values
(`land_units_tables`, `missile_weapons_tables`, `projectiles_tables`); a live `range` reading can
differ (the Magma Cannon read 380 m live). No lobby has read these rosters back, so the charge and
the recruited sizes are unverified.

| Defender, Grand Cathay | Count | Cost | Men | Missile values | Role in the witness |
|---|---|---|---|---|---|
| Lord Magistrate `wh3_main_cth_cha_lord_magistrate_0` | 1 | 400 | 1 | | Reserve; leads it, as Gwon Yul did |
| Jade Warriors `wh3_main_cth_inf_jade_warriors_0` | 2 | 525 each | 90 each | | Reserve |
| Peasant Spearmen `wh3_main_cth_inf_peasant_spearmen_1` | 2 | 350 each | 120 each | | No rule before the fallback; they stay where the engine puts them |
| Peasant Archers `wh3_main_cth_inf_peasant_archers_0` | 2 | 400 each | 90 each | 22 shots, 140 m, reload 11 s | Fire rule |
| Jade Warrior Crossbowmen `wh3_main_cth_inf_jade_warrior_crossbowmen_0` | 1 | 600 | 67.5 | 22 shots, 160 m, reload 13 s | Fire rule |
| Fire Rain Rocket Battery `wh3_main_cth_art_fire_rain_rocket_battery_0` | 1 | 1,100 | 33 | 84 ammunition, 400 m (minimum 40 m), reload 20 s, 7 a volley | Fire rule; the hwacha |
| Grand Cannon `wh3_main_cth_art_grand_cannon_0` | 1 | 900 | 33 | 22 shots, 450 m, reload 22 s | Fire rule; Jo Gyeong's cannon |

| Attacker division | Deployment slots | Units | Cost | Men | In `cth-emp-siege-a-v1` | Historical counterpart |
|---|---|---|---|---|---|---|
| D1, vanguard | 1-4 | 3 Spearmen `wh_main_emp_inf_spearmen_0`, 1 Swordsmen `wh_main_emp_inf_swordsmen` | 1,275 | 360 | Native from 0 s | Konishi |
| D2, guns | 5-8 | 2 Handgunners `wh_main_emp_inf_handgunners` (145 m), 2 Swordsmen | 1,950 | 315 | Released at 150 s | Ishida and Kuroda |
| D3, commander-in-chief | 9-13 | 2 Halberdiers `wh_main_emp_inf_halberdiers`, 2 Greatswords `wh_main_emp_inf_greatswords`, General of the Empire `wh_main_emp_cha_general_0` | 3,400 | 361 | Released at 300 s | Ukita |
| D4, final assault | 14-18 | 2 Greatswords, 2 Swordsmen, 1 Crossbowmen `wh_main_emp_inf_crossbowmen` (160 m) | 2,925 | 427.5 | Released at 450 s | Kobayakawa |

That is 10 defending and 18 attacking units, 5,550 against 9,550 by cost (1.72 times) and 734.5
against 1,463.5 men at large scale (1.99 times). Equal cost would not mean equal strength in a
siege, and this ratio is far below Haengju's. Each division is also smaller than the garrison: the
largest, D3, costs 3,400 against the garrison's 5,550 before any of its eight possible towers. The
review of the set therefore reads the 1.72 ratio as overstating the local disadvantage and expects
`HoldBuild` to be a likely shortcut (see [risks](#risks-that-would-change-the-design)). The
witness and its difficulty ladder decide how far the attacker can grow
([development stages](#development-stages)), following the owner's aim of the hardest battle that
is still demonstrably winnable.

From base reloads, an archer unit firing without pause empties in about 240 s, the crossbowmen in
about 290 s, the rockets in about 240 s (12 volleys of 7 at 20 s) and the cannon in about 480 s.
That suggests that under `hold`, with fire at will on, most missile units are empty before D3
arrives. It is a hypothesis, and stage 1 measures it (check 6).

### The map

The Helmgart terrain grid (32 m cells, first row at z -624) and the points below come from the
first observation of `bench-b12-siege-reserve-r2-20261016/episode-0001` and
`bench-b12-siege-baselines-20261016/episode-0001` (x across, z from the attacker's side to the
defender's). The battlefield spans x from -384 to 384 and z from -640 to 384. The side walls run
at z of about -80 for |x| ≥ 112, and a centre wall at z of about -16 for |x| ≤ 112 holds the gate
at (-32, -16) in a recess open to the south, so every attacker must come over the wall or through
its one gate. Inside are the Gatehouse capture point `c2` at (-2, -22.5); four Fort Tower points
`c3` to `c6` at (188, -81), (58, -31), (-62, -31) and (-192, -81), whose key
`capture_point_tower_only` suggests each controls the towers near it (stage 1 reads
`linked_buildings`); the Minor Supply Locations `c7` (-1, 155), `c8` (-320, 320) and `c9`
(320, 320); and the Key Building `c1` (0, 310). Eight empty tower slots lie behind the wall at
about (±56, 192), (-131, 97), (128, 97), (-299, 191), (289, 187), (-111, 353) and (110, 353),
with piercing towers from 500 supplies and magic towers up to 2,000 in the recorded Chaos Dwarf
battle; the Cathay options are unread. The siege started with 6,000 supplies and gained about 9
per second, and a tower took 75 s to build
([integration](integration.md#battle-types-probed-2026-10-14)). The open approach runs from x -240
to 240 for z -464 to -112. South of it a pocket is open over x of about -112 to 208 at the map's
southern edge, and wider further north; every staging point falls on a clear cell of the recorded
grid, as the build checked and this page checked again.

```text
 z  320  c8 supply (-320,320)        c1 KEY BUILDING (0,310)        c9 supply (320,320)
 z  190      slot (-299,191)   slot (-56,192)   slot (56,192)   slot (289,187)
 z  155                           c7 SUPPLY POINT (-1,155)
 z   97                slot (-131,97)                    slot (128,97)
 z  -20           c5 (-62,-31)  GATE (-32,-16)  c2 (-2,-23)  c4 (58,-31)       centre wall
 z  -80  ==c6 (-192,-81)===========                          ===========c3 (188,-81)==  side walls
 z -470                     D1: four units from x -44 to 76
 z -530       D2: x -120 to 0                    D4: x 68 to 212
 z -595                     D3: x -20 to 100; the General at (40,-620)
```

The picture is a schematic built from those coordinates and the declaration. The terrain grid
does not show wall walkways, steps or height, so Helmgart's slope is unknown and it may be flatter
than Haengju's hill. The wall is the outer palisade; the inner line has no wall and is made of the
Key Building, the supply points and whatever towers the controller builds.

JUDGEMENT: Placement — Claude, 2026-11-08: the engine places the garrison, frozen after stage 1;
the attackers start at authored pocket points, held units 50 m beyond friendly reach. Garrison
posts or closer staging change the opening and early releases; the opening rests on it.

The engine places siege defenders itself, and the existing siege family kept that placement. The
declarations carry an enemy-only `deployment` of 18 placements by type, bearing 0, with 32 m
regiments and a 20 m General (rests on JUDGEMENT tests/twwarhammer3/test_wh3_waves.py Siege
staging); `validate_deployment` accepts a declaration that leaves out a side, and it refuses one
that leaves out a unit of a side it places. The mod teleports every placement at the start, D1's
included: it borrows D1's units for the teleport and hands them straight back to native AI. The
review of the set reads earlier logs as using teleport only in Land battles, so stage 1 is also the
set's first test of teleporting units in a siege. Teleporting a garrison unit onto a wall walkway
is untested and not used. The test fixture `tests/twwarhammer3/wh3_helmgart.py` puts the Cathay
garrison on the recorded Chaos Dwarf starts until stage 1 reads and freezes the Cathay start, after
which the fixture is refreshed.

The design's staging rule: every held unit stands at least 50 m beyond the longest live `range` of
every friendly unit, measured from that unit's frozen engine start; at least 400 m (350 m, the
database range of a Cathay settlement tower, plus 50 m) from each Fort Tower point; and at least
250 m (200 m for a Cathay placement tower, plus 50 m) from each tower slot. Which tower set Helmgart
uses is unread. D1 is native from 0 s and exempt. Computed from the declared points for this page,
every held unit stands at least 449 m from every Fort Tower point and at least 627 m from every
tower slot, so those two parts hold. The friendly part waits for the engine's Cathay start. Against
the recorded Chaos Dwarf starts on this map, D2's westmost Handgunners stand 436 m from one of them
at (-277, -123), inside the Grand Cannon's 450 m database range and short of the 450 m (400 m plus
50 m) that the rule asks of the rockets, so the rule may fail once stage 1 reads where the Cathay
artillery starts. Under the rule, a held division can only be shot by a unit the controller has
moved forward, and the release on damage then follows the controller's choice.

### Divisions released in turn

JUDGEMENT: Division schedule — Claude, 2026-11-08: D2-D4 held, released at 150, 300 and 450 s, or a
group at once when one of its units loses men or reads under missile attack. A trigger on the
previous division or an all-at-once assault changes the sequence; the predictions rest on it.

`cth-emp-siege-a-v1` adds the reserve profile `{"version": 3, "kind": "waves", "groups": [...],
"release_on_damage": true}`: three groups of one-based enemy deployment slots, each slot with the
type it must place, and a release time per group, slots 5-8 (D2) at 150,000 ms, 9-13 (D3) at
300,000 ms and 14-18 (D4) at 450,000 ms. D1 is native from the first tick. The pattern is Cannae
B's reserve (`setup_reserve` in the battle Lua, after the SMACv2 wrapper's reset, which
`reserve.py` names), with no random draw. What the code does, as its offline tests show:

- `reserve.waves` refuses a group without slots, a slot in two groups, a slot past
  `deployment.enemy`, a slot whose placement is not its declared type, release times that are
  negative, fractional or out of order, and a waves profile beside a `custom` objective.
  `reserve.materialize` returns the profile unchanged and refuses a seed, and the manifest saves it
  for every episode.
- At the start the Lua `setup_waves` binds every held slot by deployment order and type, as the
  teleport binds placements, checks every slot, and only then takes control of each held unit and
  halts it (CA's `battle_unitcontroller` `take_control` and `halt`), so a refused profile leaves no
  unit held.
- Each tick `tick_waves` hands a group to native AI (`release_control`) at its `release_ms` of
  engine time, or at once when one of its units has fewer men than at setup or reads
  `is_under_missile_attack` true. Damage releases only that group, and a unit with no men left is
  not released. A getter that fails or answers another type releases the group with `ok` false,
  and `reserve.check` then stops the battle as an infrastructure failure. The release decision
  never reads friendly units; a test makes every friendly field raise on access.
- The evidence, `evaluation.reserve`, which no controller reads, holds the profile, each held
  unit's group, slot, type and enemy id, and each release's group, reason, time, unit positions and
  men, and the damaged units. `play` checks it at every observation (`reserve.check_waves`): a
  release before its time that damage did not cause, a group released twice, a unit bound to
  another type, a damage release that names no damaged unit, or, in an observation without a
  result, a group still held at or after its `release_ms` stops the battle as an infrastructure
  failure. The last rests on JUDGEMENT? src/twwarhammer3/battle/reserve.py Overdue release.
- The release records no friendly state, so `wall_readings.damage_releases` finds the friendly
  units within range at a damage release afterwards, from the public observations, and
  `wall_readings.release_distances` gives each damaged unit's distance to the nearest D1 unit, from
  the private record, and whether it lost men or was only flagged under fire.

CA's `battle_unit` reference documents `number_of_men_alive` and `is_under_missile_attack`. The
mod already reads `is_under_missile_attack` into the `under_fire` state of every unit record, and
that state appears in 544 trace lines of the Helmgart `hold` baseline by the review's count; it
has not been read for a unit under script control, or against video. The flag needs no men lost:
the second look counted, and this revision recounted, 690 enemy readings flagged `under_fire` in
that baseline, 538 of them with no men lost since the unit's previous reading.

Fire that no one aims at a held division may still release it. D1 is native from 0 s and stands
60-68 m in front of D2 and D4 (60.1, 60.1, 68.0 and 60.5 m from each D1 placement to the nearest
held one), and from 5 of the 10 recorded garrison starts a D1 placement lies within the Grand
Cannon's 450 m database range (417.6-447.1 m). Shots at D1, or at routed attackers fleeing south
through the staging area, can therefore land about 60 m from held units. Whether a held unit that
nobody targets is ever flagged or loses men is unread; check 4's probe reads it, and stage 1
reports the distance and the loss for every damage release.

The times aim to bring the divisions to the wall about 150 s apart. In
`bench-b12-siege-reserve-r2-20261016/episode-0001`, the trace this plan first read the map from, 13
attackers covered 135-150 m in 50-62 s (2.2-2.9 m/s), so at about 2.5 m/s the estimated first
arrivals within 150 m of the wall line are D1 at about 100 s, D2 at about 270 s, D3 at about 445 s
and D4 at about 570 s. Stage 1 measures them and may move the release times once before the
version is frozen. The build used the design's 300 s for D3 in place of this plan's first draft of
240 s.

The owner's reply 5 of 2026-11-04 allowed some scripting "if easy" and made it no priority for
the initial scenarios ([owner replies](scenario-guidelines.md#current-plan-and-owner-decisions)),
and the guidelines prefer conditions native AI can produce. This battle needs a script because
native AI started its whole army together in the existing siege family's battles, and on Helmgart
staging by distance alone separates the arrivals by at most about 50 s: the map is only about
560 m deep from the side walls to its southern edge. Cannae B's scripted reserve is the precedent;
decision 2(c) is the option without a script. Native AI may behave differently with part of its
army held: D1 may wait, attack alone or use its ladders late. Stage 1 records what it does.

The owner's recorder ([battle/manual_demo.py](../../src/twwarhammer3/battle/manual_demo.py)) used
to refuse every `reserve` scenario, because the mod's hold did not run under its observer session.
A waves profile now runs there: the recorder passes the profile in the session, and the Lua accepts
the observer session (`multiplayer` `observe`) for version 3 in a single-player battle, while Cannae
B's versions 1-2 and `custom` objectives stay refused. The recorder refuses an output folder whose
name holds a withheld word, checks the hold at the first observation (a hold the mod skipped or
bound wrongly ends the attempt), copies the private record, and checks the evidence again at the
last observation into `manifest.reserve_final`. A refusal there is kept beside the attempt and does
not change its status or the command's exit code, so check 10 must read it. The recorder change
rests on JUDGEMENT src/twwarhammer3/battle/manual_demo.py Observer holds waves.

### Public briefing

JUDGEMENT: Public presentation — Claude, 2026-11-08: neutral names, the engine's rules and one
sentence that divisions may attack at different times, after the prompt's "Reserve briefing:"
label. Silence, the times or another label change the information demand; comparisons rest on it.

The scenario names are neutral, and the job names must be as well, because the observation's
`job` field reaches every controller (`HIDDEN_KEYS` drops only `evaluation`, `final`, `setup` and
`native`). `play` and the recorder refuse a job whose name holds a withheld word at a word start
(`setup.check_job`; by the review's test `run2haengju` would pass). Neither declaration has a
`benchmark` or `scoring` key, so `play.public` adds nothing to the mode, and the declaration's
`brief` reaches no controller. In `cth-emp-siege-a-v1`, `play.public` adds `reserve_briefing`,
which is exactly "The attacking army is drawn up in several divisions, which may attack at
different times." A model's prompt shows it as `Reserve briefing: "The attacking army ..."`,
because `llm.py` keeps its existing label so that every existing prompt stays byte-identical. A
model may read "Reserve" as a hint that some enemies are held back; changing the label is a prompt
change and a logged version. The all-at-once arm shows no sentence (rests on JUDGEMENT?
tests/twwarhammer3/test_wh3_waves.py All-at-once briefing). The briefing gives no times, no
history and no recommended tactic, and it does not say that damaging a waiting division brings it
on; the division's movement shows that.

The model arms read different system prompts (`controllers.MODEL_PROMPTS`). `llm_rules` reads
[rules_prompt.md](../../configs/twwarhammer3/rules_prompt.md), which gives the rules and no tactic.
`llm` reads [system_prompt.md](../../configs/twwarhammer3/system_prompt.md), whose How to fight
section prescribes one arm of two of this battle's decisions. Its line 34, "until the enemy
infantry reaches your line, every shooter fires at it", is D1's `WFire` arm. Its line 29, "a
withdrawal only delays defeat", argues against D3's fallback and is wrong for a defender who wins
at the timer. So "no recommended tactic" holds for `llm_rules` only, and an `llm` result here
mixes the model with that advice, which [benchmark.md](benchmark.md) runs as its own `tips` arm.

JUDGEMENT?: Pilot arms — Claude, 2026-11-09 (second look, seat-3): a stage 6 pilot runs llm_rules,
or reports an llm result as a tips arm. Reading llm as a plain model arm credits its How to fight
advice to the model; stage 6's reading rests on it.

Cannae B's reserve briefing publishes its catalogue, trigger and release bounds, and this battle
publishes one sentence. [Guideline 2.2](evaluation-guidelines.md#22-tell-the-controller-everything-the-scorer-checks)
asks that a controller be told everything the scorer checks. The script is not scored, but the
choice changes the information demand, and the review of the set asks the owner for one disclosure
rule for every scripted opponent (decision 3).

## Decisions the battle could test

These are design predictions to test in development. A controller may win by any legal play, and
a prediction that fails narrows this page's interpretation without touching the win. The cues
below are recorded by every arm (`cues` in its metadata; see the controls).

**D1, fire across divisions (the battle's one claim).** When a visible enemy unit comes within
150 m of the public wall line or inside it while at least 10 units of the public enemy roster have
never been seen within 300 m of it, two choices are feasible for the five missile units: the
engine default, fire at will on (`WFire`), or holding fire until an enemy is within 60 m of the wall
line or inside it (`WallWitness`). Under condition X, the witness should keep more ammunition at
D3's approach, shoot more D3 and D4 men before they reach the wall, and win more often than
`WFire`. Condition X is the S-ammo premise (check 6): under `hold`, the five missile units' summed
ammunition is at most 25% of its start when D3's first unit comes within 150 m of the wall line.
The prediction disappears if S-ammo fails, or if D1 takes `c2` before 150 s when it is left
unshot. The rule is partly about timing (when to start shooting), and on 2026-11-05 the owner said
studying timing "is not that interesting for now" ([owner direction](../owner-direction.md));
whether this should be the claim is decision 4. A pass would show that holding fire mattered for
this witness, at 5 s / 5 s, on the version its ladder picked; it would not show that a model reads
the cue. The rule holds every shot, the long ones included (rockets to 400 m, the cannon to
450 m), until an able enemy is within 60 m of the line or inside it; from then on the engine picks
targets at any range. So a pass of `WallWitness` over `WFire` cannot by itself separate saving
ammunition for later divisions from shooting at closer range; the Cathay projectiles' calibration
distances are unread. `wall_readings.division_missile_losses` reads, per division, the men lost
before any of its units reads melee or `on_wall` in the private record; it does not tell missile
losses from other causes, and no battle has run it.

Proposed narrowing, for the owner to decide (it rests on JUDGEMENT
src/twwarhammer3/battle/wall_defence.py Wall witness thresholds): in version 1 the fallback cue is
`c2` enemy-held, which the hold baseline reached at 336.7 s, before D3's estimated first approach
at 445 s. If the fallback cue comes before D3's approach in most launches (`gate_timeline` read
beside `approach_ammunition`), the D1 prediction becomes "more ammunition carried into the later
divisions' fight" in place of "more D3 and D4 men shot before they reach the wall". From the
Key Building ring the rockets and the cannon still reach the gate area, about 290-370 m away.

**D2, reserve at a breach (exploratory).** When exactly one visible enemy that is not routing has
been inside the wall line for two decisions in a row, sending the Lord and both Jade Warriors to
attack it and keeping them at `c7` are both feasible. Sending should rout the breaching unit sooner
and keep `c2` defender-held longer. Two breaches at once on different wall sections, which ladders
make likely, can reverse it; the cue then does not occur.

**D3, fallback (exploratory).** When `c2` is enemy-held, withdrawing every unit to the Key
Building and fighting on at the wall are both feasible. The rule also falls back at a gate reading
hp 0 or below, which version 1 cannot produce: no attacker in it can damage the gate.
Withdrawal should keep more units not routing when D4 first approaches, and keep `c1` defender-held
so that no ticket falls. If `KeepOnly` wins as often from the first decision, the outer line is
unnecessary and the reading narrows to keeping units alive. If `c2` stays defender-held until D4
arrives, the cue never occurs.

Construction is no claimed decision: 6,000 supplies buy every piercing tower at once, so builds,
tower losses and options are only recorded.

## Witness, ablations and controls as built

[`battle/wall_defence.py`](../../src/twwarhammer3/battle/wall_defence.py) holds the witness and
five controls, each loaded by module path (for example
`twwarhammer3.battle.wall_defence:WallWitness`); their names are not built-in policy names. The
module has never driven a game. Every arm shares these rules:

- **Binding.** At the first observation the friendly army must be the ten declared types with
  positions, and the capture points `c1` to `c7` must carry Helmgart's keys. Otherwise the arm
  raises `PolicyFailure` with a cause, which ends the episode as a policy failure; a bare one would
  be a forfeit, and the army would stand for the whole battle. Roles come from type keys: the
  missile units (archers, crossbowmen, rockets, cannon) and the reserve (the Lord and both Jade
  Warriors). Each unit's fallback spot lies on a 40 m ring around `c1`, assigned in order of type
  and start position; ids and list order change nothing.
- **Wall line.** The polyline through (-384, -81), `c6`, `c5`, `c2`, `c4`, `c3` and (384, -81),
  from the public capture point positions; an enemy 10 m or more north of it is inside.
- **Repeats.** Moves and attacks go at a run. An unchanged move or attack is sent again only if,
  10 s after it was last sent, the unit reads idle more than 15 m from its point or an attacking
  unit has no target, or after the engine refused it.

The witness `WallWitness` (`wall_witness`) plays four rules:

1. **Build.** At each decision, the cheapest option at every usable empty slot that the supplies
   cover, until the engine accepts one per slot.
2. **Fire.** The four missile types keep fire at will off, and turn it on only while a visible enemy
   that is not routing stands within 60 m of the wall line or inside it.
3. **Reserve.** The Lord and both Jade Warriors go to `c7` and attack the nearest enemy that has
   been inside the line for two decisions in a row, keeping their target while it stays there. They
   hold their place while an enemy is inside but not yet confirmed, and go back to `c7` once no
   visible enemy is inside. The rule stops at the fallback.
4. **Fallback.** Once `c2` is enemy-held or a gate reads hp 0 or below
   (`evidence_rules.gate_breached`, whatever `destroyed` says), every unit goes to its spot near
   `c1` and attacks visible enemies within 100 m of it, to the end of the battle. In version 1
   only the Gatehouse can start it: every Empire unit key in the roster reads `can_siege` false
   (`main_units_tables`, read on 2026-11-09) and `siege_equipment` is `{}`.

The values rest on JUDGEMENT src/twwarhammer3/battle/wall_defence.py Wall witness thresholds. The
witness is single-author until someone without its code reproduces a win.

| Class (`arm`) | Role | What it changes | Counted in the screen only if |
|---|---|---|---|
| `HoldBuild` (`hold_build`) | The engine's automation with towers | Builds as the witness, then gives no orders | All 8 builds were accepted (`builds_accepted` in its metadata) |
| `KeepOnly` (`keep_only`) | A partial plan with no outer line | Builds, and the fallback from the first decision | At least 9 of 10 units within 80 m of `c1` by 180 s; no reader of this is built |
| `WFire` (`w_fire`) | Ablation; the other arm of the primary contrast | No fire rule: fire at will stays as the engine has it | Decision 1's cue occurred (`cues.fire_ms`) |
| `WReserve` (`w_reserve`) | Ablation, exploratory | No reserve rule: the Lord and the Jade Warriors stay where the engine put them until the fallback | Decision 2's cue occurred (`cues.reserve_ms`) |
| `WNoFallback` (`w_nofallback`) | Ablation, exploratory | No fallback rule | Decision 3's cue occurred (`cues.fallback_ms`) |
| `hold`, `attack_nearest`, `rush_nearest` ([`battle/scripted.py`](../../src/twwarhammer3/battle/scripted.py)) | Floors | No orders, or attacks on the nearest visible enemy | `hold` always; the others after at least one accepted attack and one melee engagement |
| `Evade` ([`battle/evade.py`](../../src/twwarhammer3/battle/evade.py)) | Shortcut | Every unit runs from visible enemies; a timer win would mean that holding is unnecessary | As `evade.py` records |
| `ReplaySchedule` ([`battle/replay_schedule.py`](../../src/twwarhammer3/battle/replay_schedule.py)) | Fixed-schedule foil, after the first witness win | Replays the win's accepted orders by battle time on fresh launches; each attack goes to the visible enemy of the same type nearest the original target's last public position, and is dropped when none is visible (rests on JUDGEMENT src/twwarhammer3/battle/replay_schedule.py Replay remap; this plan's draft fell back to any type) | The engine accepted at least 90% of the orders due (rests on JUDGEMENT src/twwarhammer3/battle/replay_schedule.py Replay carried out) |

Every arm records two sets of first times. `cues` are the decisions' cues above, which decide
whether an ablation launch counts in the screen: the fire cue counts a roster unit never seen as
not yet within 300 m, the reserve cue needs exactly one confirmed enemy inside, and `KeepOnly`'s
start is not its fallback cue (rests on JUDGEMENT? src/twwarhammer3/battle/wall_defence.py Ablation
cues). `triggers` are when each rule's own trigger first fired; they describe the play and count
nothing. Each arm's metadata also records its roles, the fallback reason and the builds accepted.

`test_wh3_wall_defence.py` (21 tests) drives the arms through Helmgart frames built from the
fixture. It shows the witness building, rationing fire, answering a breach and falling back; a gate
at hp 0 that reads not destroyed starting the fallback; each ablation differing from the witness
only in its named rule (`wh3_ablation.assert_ablation`); `KeepOnly` holding the Key Building from
the first decision; ablations counting on the cues and not the triggers, with the fire cue counting
at exactly 10 roster units never seen and not at 9; the reserve holding its place while an
unconfirmed enemy is inside; fire at will turning on at 59 m from the wall line and not at 61 m;
builds kept within the supplies across slots (two at 1,000); a refused build ordered again; the
fallback kept after `c2` is retaken, with the reserve rule still stopped; a kept target not replaced
by a nearer enemy, before and after the fallback; the 10 m margin; no arm reading a hidden section
or the briefing; and roles binding by type and start. The build's implementer, an independent
reviewer and a fixer planted wrong versions of the waves code, the arms and the readings in scratch
copies (`runs/siege-evals-20261108/lua-batch.json`). The implementer's 37 plants caught 36. The
review reran the tests, planted 10 more and reported 7 problems, two of them to fix (the cues were
the rules' triggers, and the reserve-response reading was missing). After the fix round, 60 of 64
plants were caught; no second review checked that rerun. The four survivors are a first-sighting
plant that changes the function's signature, a truncated unit list that the Lua refuses first, an
unreadable `is_multiplayer` accepted, and whole-token job matching. The second look on 2026-11-09
found more survivors in the witness and the readings: the fallback recomputed every decision (WD4),
the supplies not counted down across slots (WD7), a build that costs exactly the supplies left
skipped (WD16), a refused build marked accepted (WD10), kept targets dropped (Q9, Q10), the approach
reading overwritten by later approaches (W4), and `APPROACH_M`, `FIRE_M` and `CUE_FAR_UNITS` moved
(K7, K1, K6). The tests listed above and in the readings file kill each of these in a scratch copy
(`runs/siege-evals-20261108/scratch3/haengju-readers-docs/`), as they kill the planted wrong
versions of the three readers added that day. None of this shows what the orders do in a game.

## Measurements

The engine outcome is primary. The existing readings carry over: unit condition, `victory_held`,
`key_held`, supplies left, builds, order age, refusals and cost. The owner's interest in health and
morale and a later overall ranking applies; this page adds no formula. Every reading below is
descriptive until a check ties it to a decision, and a missing value stays unknown.

| Reading | Source (`f3fec92`, and the three readers added on 2026-11-09) |
|---|---|
| Each release: group, time, reason, positions; damage releases with the friendly units then within their public `range` of a released unit | The mod's evidence and `wall_readings.damage_releases` (the friendly view rests on JUDGEMENT? src/twwarhammer3/battle/wall_readings.py Release friendly view) |
| For each damaged unit of a damage release: its distance to the nearest D1 unit, and whether it lost men or was only flagged under fire | `wall_readings.release_distances`: positions from the last private-record frame at or before the release, D1's ids from `evidence_rules.group_ids` (slots 1-4), the loss from the release's own `men` and `men0` (rests on JUDGEMENT? src/twwarhammer3/battle/wall_readings.py Release distance) |
| The gate, Gatehouse and fallback times | `wall_readings.gate_timeline`: the first observation with a public gate at hp 0 or below, the first with `c2` enemy-held, and the arm's fallback time and reason from its metadata in the trace's last decision row; read beside each division's first sighting and first approach |
| Each division's men lost before contact | `wall_readings.division_missile_losses`: in the private record, the men each division lost before any of its units reads melee with men left or `on_wall` (rests on JUDGEMENT? src/twwarhammer3/battle/wall_readings.py Missile losses and JUDGEMENT src/twwarhammer3/battle/evidence_rules.py Contact rule); it does not tell missile losses from other causes |
| First sighting of each division | `wall_readings.first_sightings`: the first observation whose public `enemy` list holds one of its units, never the private record, which also lists units nobody can see |
| Missile ammunition at each division's first approach | `wall_readings.approach_ammunition`: at the first observation in which a visible unit of the division is 150 m or nearer the wall line or inside it, the summed `ammo` and `ammo0` of the friendly units that carry ammunition (rests on JUDGEMENT? src/twwarhammer3/battle/wall_readings.py Approach distance). The sum weights each unit by its own count, so the rockets' 84 make up about half of the 172 total by database values; spent shots do not prove hits. D1's reading also counts the shots fired before D1 first comes within 150 m (its `ammo0` minus its `ammo`), so no other reader is built for them |
| Breach time | `wall_readings.breach`: the first private-record frame in which an enemy reads `on_wall` true, or, once stage 1 has frozen the private wall polygon from the terrain grid and `on_wall` readings, whose centre is inside it in two frames in a row (rests on JUDGEMENT? src/twwarhammer3/battle/wall_readings.py Breach reading). `is_on_top_of_wall` has never been read live, and a centre alone can jump between squads |
| Reserve response | `wall_readings.reserve_response`: ms from the breach until the engine applied the first accepted attack by the Lord or a Jade Warriors unit, and until the first frame with one of them flagged in melee with men left (rests on JUDGEMENT? src/twwarhammer3/battle/wall_readings.py Reserve response and JUDGEMENT src/twwarhammer3/battle/evidence_rules.py Contact rule). Checked only on a hand-built trace |
| Holder times of `c1`, `c2` and `c7`; ticket onset | `wall_readings.enemy_held` and `ticket_onset`, with holders and tickets as `evidence_rules` reads them: a holder of None is neither side's, and tickets are the defender's row. Tested against the `hold` baseline times above |
| Divisions as unit ids | `evidence_rules.group_ids`: fixed by the placement each enemy unit matched at the first observation (rests on JUDGEMENT? src/twwarhammer3/battle/evidence_rules.py Group membership) |
| Cues, triggers, fallback reason, builds accepted | Each arm's metadata in the trace |
| Tower builds and losses, the General's death or rout, Harmony effects at the start | Public `mode.slots` and unit rows; no reader is built |

The private record (`capture.copy_private_record`) holds every unit of both sides once per engine
second, hidden enemies included, with men, routing, melee, `on_wall`, `climbing`, visibility and
ammunition where the engine gives them; raw gate hit points, holders and tickets. A field the
engine did not give is absent, never false or zero. No game has written it, and its CPU cost per
second for 28 units is unmeasured (`sample_cpu_ms` keeps it). Its use in every opted-in battle
rests on JUDGEMENT? src/twwarhammer3/battle/capture.py Private record in scored battles, and its
fields on the Private record fields marker there. Publishing `on_wall` and `climbing` to the
controllers would change policy input and the prompt snapshots. At `f3fec92` `on_wall` (with
`can_climb` and `can_siege` for the player's own units) reaches controllers only in a siege the
player attacks, and `climbing` reaches none: the mod reads `is_climbing_ladder` only for the
private record, because it read true at ground height and for defenders on 2026-11-03 (rests on
JUDGEMENT src/twwarhammer3/battle/setup.py Siege assault boundary).

## Proposed deciding checks

JUDGEMENT: Deciding checks draft — Claude, 2026-11-08: the rows below with their counts, plants and
S-ammo's 25% bar; WallWitness against WFire as the one primary contrast; a 4-of-5 gate at 5 s/5 s.
Other rules change what each stage may claim; every label rests on it.

These are proposals for the owner to accept or change; none is in
[agreed checks](../agreed-checks.md). They follow the set's shared rules listed at the top. Exact
chances come from [`battle/exact_stats.py`](../../src/twwarhammer3/battle/exact_stats.py). A count
of one shows that an effect is possible; showing that it is reliable takes more launches.

| # | Claim | Evidence | Count and rule | Must fail on |
|---|---|---|---|---|
| 0 | Cards recruit | The set's lobby-only readback: the scenario's lobby steps without the Start click, then `setup.army_checks` (the step file that stops before Start is not written) | All 14 unit keys recruit with their counts under `wh3_main_cth_cathay_mp` and `wh_main_emp_empire`; the attacker's equipment list reads size 0 | A scenario copy with one key swapped |
| 1 | Constructed | Lobby readback and the private first reading, every launch | Map, mode, engine type, role, difficulty, modifier, scale, timer, funds, both rosters by multiplicity, equipment size 0 in the lobby and none in the battle's first reading (pieces added later go unseen); every staged unit within 25 m of its point and bearing within 5 degrees after the constant offset stage 1 measures (Cannae's row 1 found 2.8 degrees); the garrison within 25 m of the frozen engine start; the public gate reads hp 100 at every observation, since no version 1 attacker can damage it (a fall stops the stage, marker below the table) | A swapped unit; a leftover ram in the lobby (built: `test_wh3_setup.py` runs the steps against a lobby that already holds one); a division staged 100 m off; a changed garrison start; a gate that falls |
| 2 | Held and released | The mod's evidence at every observation (built: `reserve.check_waves`) and the private record | Every waves launch: the evidence check passes; each held unit stays within 15 m of its placement until its release; each group is released within one tick (250 ms) of its time unless the reason is damage; each released division moves at least 20 m within 15 s, and one of its units comes within 150 m of the wall line within 300 s; no damage release in any `hold` or `HoldBuild` launch, and each damage release reported with `release_distances`. The position parts need a private-record reader, not built. Exact error rate (`exact_stats.gate_pass(3, 3, 0.7)`): three `hold` launches pass a 30%-per-launch damage release rate 0.34 of the time | Built and caught: a release one tick early, one group's damage releasing every group, an unreadable getter read as no damage, a destroyed unit released, slots bound by roster index. Built and caught offline (`test_wh3_waves.py`): a group never released, read as a group still held at or after its `release_ms`; a damage release that names no damaged unit. To build: plants on recorded replays, a release 60 s early, a damage release inserted into a `hold` battle |
| 3 | Information boundary | Built: the rendered prompt and `play.public` view from the Helmgart fixture's first observation, and the job check in `play` and the recorder. To repeat on the scenario's own first observation after stage 1 | No withheld word, profile key, release time in seconds or milliseconds, group or staging label in any controller input; `reserve_briefing` is the agreed sentence; inputs unchanged when only `evaluation`, `setup`, `native` or `final` change | Built and caught: `briefing()` returning the profile; a job named after the history; a witness that reads `evaluation` |
| 4 | Orders reach effects | Stage 2 probes, with trace and video | 3 of 3 each within the probe launches: fire at will off stops ammunition falling for 30 s with a target in range; an attack on an enemy inside the wall gives the melee flag within 20 s; a build reads `built`, with supplies down by its cost within 2 s, and finishes at the stage 1 time within 5 s; a move from the wall ends within 25 m of `c1`; one held division shot on purpose is released within 2 s while the others stay held, and the probe reads whether a held unit about 60 m behind a unit under artillery fire is flagged under fire or loses men. Repeats in one battle are not independent, so this shows an effect can happen and says little about how often | An accepted order whose unit never changes state; an `on_wall` reader returning a constant |
| 5 | Ticket and ending rules | Every stage 1-5 battle | Tickets stay at 1,000 while `c1` is defender-held and fall from within 2 s of it turning enemy (the recorded basis is below the table); any battle that reaches 1,200 s ends `won` with `ended_by` `time_limit`. Until one does, the timer win stays unverified | Built and caught: tickets read from the attacker's row; a holder of None read as enemy. To build: a scorer that counts losing `c1` as defeat |
| 6 | S-ammo, the premise of D1 | `wall_readings.approach_ammunition` in the three stage 1 `hold` launches of the waves arm; read again, descriptively, in every `WFire` launch (stage 3a and the round), where the premise should hold, and reported per arm in every gate and round launch | 3 of 3: the five missile units' summed `ammo` is at most 25% of their summed `ammo0` when D3 first approaches. Exact error rates (`exact_stats.gate_pass`): a premise that holds in half of all launches passes 0.125 of the time, and one that holds in 80% of launches fails 0.488 of the time. A 3-of-3 pass puts an exact one-sided 95% lower bound of only 0.368 on the premise's rate | Built and caught: the approach read at 200 m. To build: a fixture whose ammunition never falls; a division that never approaches must read unknown and fail |
| 7 | The sequence changes the battle (construction) | The three waves `hold` launches and one `hold` launch of `cth-emp-siege-a-all-v1` | In every waves launch the four divisions first approach in order, each at least 60 s after the one before (about half the smallest estimated gap of 125 s); the all-at-once spread is reported. It claims no decision | A waves launch whose hold silently failed (check 2 must pass in every launch counted) |
| 8 | Shortcuts | Stage 3a, one launch per control, rerun after each ladder step | Reported only; a win is kept and narrows the label; a control's launch counts only if it carried out its play (controls table) | Nothing; reported only |
| 9 | Witness gate | `WallWitness`, fresh launches at 5 s added order age and a 5 s decision interval, frozen version | At least 4 of 5, stopping at the 4th win or the 2nd loss. Exact error rates: it passes a 50% witness 0.1875 of the time and fails an 80% one 0.263 | A win credited at a timing the witness did not play |
| 10 | Human win | `uv run --locked python -m twwarhammer3.battle.manual_demo record --scenario cth-emp-siege-a-v1 --output DIR --ffmpeg FFMPEG --timeout SECONDS --start-reference HOLD1 --start-reference HOLD2 --start-reference HOLD3`, with a neutral folder name and one `--start-reference` for each of stage 1a's and 1b's three `hold` episode folders. The engine places the garrison and the owner plays through deployment, so the owner starts the battle without moving any unit, and `manifest.start_check` compares the garrison's first private-record positions with every hold's | One engine win; every attempt kept; pauses labelled from video; check 2 passes on the recording, with `manifest.reserve` and `manifest.reserve_final` both clean; an attempt counts only if `manifest.start_check.label` reads `same start`, and one that reads `own deployment` or `start not comparable` is kept and does not count (marker Demo start label below) | Built and caught: Lua setup that skips the hold under the observer; a recorder that skips its first or final waves check. Built and caught offline (`test_wh3_manual_demo.py`): one garrison unit 40 m off read as the same start; one hold, or holds 30 m apart, read as comparable |
| 11 | D1 matters for this witness, the one primary contrast | `WallWitness` against `WFire`, n fresh separate launches per arm fixed in advance, at 5 s / 5 s, in an order drawn in blocks; only after check 9 passes and the owner names this contrast | Two-sided Fisher exact p < 0.05 (`exact_stats.fisher`), the Newcombe interval (`exact_stats.newcombe`) and a disposition table for every planned launch that also lists each launch's release times and reasons. Every launch counts, including one in which the cue never came; the cue-conditional view is exploratory. A pass with `WFire` ahead reads "the decision matters and the witness's rule is the worse choice here"; whether it earns a label is the owner's call. `approach_ammunition` and `division_missile_losses` are reported per arm | Analysis code that drops a launch without the cue, counts a rematch as a launch, or reports a one-sided or Wald result (built: `test_wh3_exact_stats.py` fails a one-sided Fisher, 0.243 on the tea table) |

JUDGEMENT?: Gate stop — Claude, 2026-11-09 (second look, ER3): the public gate must read hp 100
throughout every version 1 launch, and a fall stops the stage. Recording the fall and going on
keeps launches with an unplanned engine source; every stage 1-5 count rests on it.

JUDGEMENT?: Demo start label — Claude, 2026-11-09 (second look ER6): only `same start` counts
toward check 10. Counting `start not comparable`, with a video label that no unit moved during
deployment, would admit attempts when holds are missing or vary; check 10's count rests on it.

The start check's 25 m and its comparison with every hold rest on JUDGEMENT?
src/twwarhammer3/battle/manual_demo.py Demo start limit and Every hold a reference. It has not run
live: whether the garrison's engine start repeats within 25 m is unknown until stage 1.

No version 1 attacker can damage the gate, so a fall would mean an engine source the design did
not plan for. The same rule catches a lobby that failed to remove the attacker's siege equipment,
which the 2026-11-10 all-at-once lobby readback completed; no battle has read the equipment yet.

Check 5's recorded basis, recounted on 2026-11-09 from the two episodes of
`bench-b12-siege-baselines-20261016` (episode 0 `attack_nearest`, episode 1 `hold`; 9.0.4, Chaos
Dwarfs defending against Greenskins on this map): losing supply points cost no tickets, and the
count fell only once `c1` was enemy-held. In episode 0, `c7` was enemy-held from 406.0 s and `c8`
from 583.6 s with the defender at 1,000; `c1` fell at 791.5 s, the count read 995 at 792.4 s and
fell about 5 per second, to 835 by 825.1 s and 145 at the end, 962.6 s. In episode 1, `c9` fell at
453.4 s, `c7` at 467.8 s and `c8` at 660.4 s, all at 1,000; `c1` fell at 699.1 s and the count read
990 at 700.3 s. That is n = 2 with the player defending. Neither episode can tell `c1` alone from
`c1` plus supply points, since `c1` fell after at least two of them each time, and `per_s` is not
the drain: it fell from 5 to 0 at 699.7 s and 566.8 s, 92.7 and 133.5 s before each drain began,
while the count stayed at 1,000.

If the witness fails check 9, no round runs. The version then steps down one difficulty factor or
the witness is revised, and the new version gets a gate on fresh launches; an unchanged gate is
never rerun until it passes
([guideline 2.7](evaluation-guidelines.md#27-admit-a-card-only-from-a-frozen-confirmation-round)).
If no version's witness ever wins, the battle stays unwitnessed and is not used for any claim.
Natural-timing and 10 s / 10 s launches may be reported beside the 5 s / 5 s cell, as
[guideline 2.3](evaluation-guidelines.md#23-show-the-card-can-be-won-at-a-named-timing) asks, but
neither the gate nor the contrast runs there. `WReserve` and `WNoFallback` get their screening
launch only; more is the owner's call.

Exact power of check 11, from `plan_power`
([guideline 7.4](evaluation-guidelines.md#74-decide-before-you-look)):

| Launches per arm | 0% → 50% | 10% → 60% | 20% → 70% | Wins needed for p < 0.05 against 0, 1, 2, 3 |
|---|---|---|---|---|
| 10 | 0.623 | 0.474 | 0.426 | 5, 7, 8, 9 |
| 16 | 0.962 | 0.786 | 0.740 | 5, 7, 9, 10 |

For other witness rates and launch counts, see the power grid under the
[overview's method rules](historical-evals.md#method-rules-the-set-shares).

The paired checkpoint branches that the review offers other battles for low power do not apply
here: the bridge mod starts fresh after a restore ([checkpoints](checkpoints.md#limits)), so the
held divisions would be lost.

## Development stages

Stages 0 to 5 cost $0 in API calls, and stage 6 is paid. Every live stage waits for a window the
owner names, and the live stages run one battle at a time across the set. A launch that runs to
the timer takes about 20-25 minutes: the 1,200 s timer is 20 minutes, and loading and setup come on
top. This is the design's estimate, the one the whole set uses; no recorded launch on these maps
ran to the timer, and a battle that ends earlier takes less. Each time below is that estimate
times the launch count.

| Stage | What runs | Launches and game time | What it can establish |
|---|---|---|---|
| 0 | Offline. Done at `f3fec92`: the declarations, the waves profile and Lua hold, the recorder support, the job check, the witness and controls, the readings and their tests; `check.py` passed there (3585 passed, 70 skipped, by its commit message). The Eagle Gate screen declaration `cth-emp-siege-a-all-gates-v1` was added at `050020e`, and the gate, release-distance and missile-loss readers on 2026-11-09. Still to build: the private-record reader for check 2's positions, `KeepOnly`'s carried-out reading, check 6's fixtures and the plan builder that names a round's jobs | None | That the code does what its tests say |
| L | The set's lobby-only readback (check 0), one game session shared with the other new battles | Minutes, no battle | Whether the Cathay cards recruit under `wh3_main_cth_cathay_mp`; the equipment readback in the AI slot |
| 1a | One `hold` launch of `cth-emp-siege-a-v1` | 1, about 20-25 min | Checks 1, 2 and 5, which re-read the 9.0.4 ticket onset on the pinned build; each damage release's distance to D1 and loss (`release_distances`); the gate, `c2` and fallback times beside each division's first approach (`gate_timeline`); a go or no-go on teleporting the divisions in a siege and on the hold; the engine's Cathay start and live ranges, frozen, then the staging rule applied; whether held divisions are visible; what D1 does alone; whether the battle ends while divisions are held; travel times; `linked_buildings` per supply point; the Cathay tower options; Harmony fields; `sample_cpu_ms` |
| 1b | Two more `hold` launches of the waves arm | 2, about 40-50 min | Check 6 at 3 of 3 with 1a; the waves part of check 7; the same release, gate and `c2` readings as 1a |
| 1c | One `hold` launch of `cth-emp-siege-a-all-v1` | 1, about 20-25 min | How far apart the divisions arrive with no hold (check 7); checks 1 and 5 |
| 1d | One `hold` launch of the Eagle Gate screen `cth-emp-siege-a-all-gates-v1`, declared at `050020e` (marker below) | 1, about 20-25 min | Whether the rule frozen beforehand picks Eagle Gate over Helmgart |
| 1e | Optional: `hold` with 1 `emp_battering_ram` and 1 `emp_siege_tower_15m` | 1, about 20-25 min | Which division mans each piece and when, and, if the ram breaks the gate, whether a gate at hp 0 still reads `destroyed` false on the pinned build; information for a later variant only. Rule: each vehicle stands within 30 m of its crew in the first private frame after the teleport, otherwise 1e reads "crew separated by teleport". In the 2026-11-03 checkpoint sieges the engine bound crews at deployment and left one siege tower uncrewed, and nobody has teleported a crew. The owner may instead run 1e with `deployment` null, so that the engine places every unit |
| 2 | Probe launches | 2, about 40-50 min | Check 4, including whether a held unit about 60 m behind a unit under artillery fire is flagged or loses men; `on_wall` and `climbing` in the private record against video at 10 moments; whether an attack on an enemy reading `on_wall` reaches melee, which version 1 does not depend on. The probe of a gate at hp 0 is parked until a variant with a ram or a `can_siege` unit exists |
| 3a | Shortcut screen in guideline 2.4's order: `HoldBuild`, `attack_nearest`, `rush_nearest`, `KeepOnly`, `Evade`, `WFire`, `WReserve`, `WNoFallback` (`hold` comes from stage 1) | 8, about 2.7-3.3 h | Check 8 |
| 3b | Witness development at 5 s / 5 s, once at 10 s / 10 s, and `ReplaySchedule` after the first witness win. If a shortcut won in 3a, the next version first strengthens the divisions one ladder step at a time, rerunning the floors and check 6 | About 4-8, about 1.3-3.3 h | A witness win at a named timing |
| 3c | The frozen witness gate (check 9) | Up to 5, up to about 2.1 h | Whether the frozen version is winnable at the model-like cell |
| 3d | The ladder, only after a gate passes (marker below): one factor per step; each step reruns `hold` three times for check 6, `HoldBuild` and `KeepOnly` once, and `WallWitness` twice. The hardest step the witness still wins is frozen and gets its own gate | About 7 per step (about 2.3-2.9 h), then up to 5 | The hardest step the witness still wins |
| 4 | The owner's manual demonstration (check 10) | The owner's time | Human-demonstrated winnability |
| 5 | The round for check 11, only if the owner names it | 16 per arm: 32 launches, about 11-13 h; 10 per arm: 20 launches, about 7-8 h | The primary contrast |
| 6 | A model pilot, if the owner wants one | Paid; the owner's budget and arms (`llm` and `llm_rules` read different prompts; marker Pilot arms under the public briefing) | Exploratory model results on a development battle; no ranking |

Through stage 3c that is about 24-29 launches and 8-12 hours of game time before any ladder step.

JUDGEMENT: Eagle Gate screen — Claude, 2026-11-08 (siege defence design): one hold launch on
battle_preset_wh2_main_minor_settlement_fortress_gates, kept only under the rule below, frozen
first. A looser rule may pick a map whose shape staggers the divisions; the map choice rests on it.

The rule, fixed before the launch: one wall face toward the attacker; an approach between blocked
cells at most 300 m wide; `c1` and at least one supply point inside; the staging rule satisfiable
inside the bounds; and the garrison starting inside the walls. Otherwise Helmgart stays.

JUDGEMENT: Wall defence ladder — Claude, 2026-11-08 (design; reruns 2026-11-09): one factor a step
(D4 one more Greatswords, D2-D4 30 s apart, one fewer archer unit, attacker rank); each step reruns
hold x3, HoldBuild, KeepOnly, WallWitness x2. Other knobs or reruns change the frozen version.

A ladder step can remove the premise: one more Greatswords or releases 30 s apart change S-ammo
and the arrival spacing, so check 6 and check 7's waves part are re-read at every step, beside
the floors.

## Risks that would change the design

| Risk | Stage | Response |
|---|---|---|
| Cathay cards do not recruit, or Harmony dominates | L, 1a | The Empire mirror (decision 1(b)) |
| Teleport is refused or misplaces units in a siege | 1a | No staged version; report it. The all-at-once arm uses the same placements, so it fails too |
| The staging rule fails once the Cathay start is read (D2 stands 436 m from a recorded start) | 1a | Move the held divisions deeper into the pocket as a new version before freezing; the pocket ends at z -624 |
| Held divisions, 449-559 m from the wall line, are not visible from the garrison | 1a | Record it; the fire cue already counts unseen roster units as far |
| D1 idles while the rest of its army is held | 1a | A version that gives each released division a disclosed route toward the wall before handing it to native AI (Cannae B v2 precedent) |
| Held units do not count as present, so the battle ends early | 1a | Release all divisions; the battle becomes the all-at-once arm only |
| The engine adds siege equipment to the empty list | L, 1a | `check_battle` refuses a battle whose first reading lists any piece (pieces added later go unseen by it; the private record's `equipment` field would list them, and no reader for it is built); equipment becomes a declared variant |
| `hold` or `HoldBuild` wins, since each division is weaker than the garrison plus eight towers | 1, 3a | Keep the win; the next version strengthens the divisions one ladder step at a time, with S-ammo re-measured |
| S-ammo fails | 1b | Decision 1 is dropped, or one fewer archer unit as a new version |
| `KeepOnly` wins | 3a | The fallback reading narrows to keeping units alive |
| Ladders put several divisions on the walls at once | 1-3 | Decision 2's reversal case; reported |
| A gate at hp 0 still keeps units out, or another flag says more | Parked | Version 1 cannot produce it, since no attacker can damage the gate; the probe waits for a variant with a ram or a `can_siege` unit, and the fallback cue rests on hp 0 or below until then (JUDGEMENT src/twwarhammer3/battle/evidence_rules.py Breach rule) |
| The public gate falls in a version 1 launch | 1-5 | The stage stops (marker Gate stop): an engine source the design did not plan for, or siege equipment the lobby failed to remove |
| Fire at D1, or at routed attackers fleeing through the staging area, flags or kills men in a held division nobody aimed at, so it comes on early | 1-3 | Read each damage release's distance to D1 and its loss (stage 1), and the probe in check 4. If such collateral releases appear, propose moving D1 about 100 m north as a new version, which keeps shots at D1 farther from held units whether they flag or kill; propose dropping the under-fire flag from the release only if the probe shows flags without losses on held units nobody targeted. Both are the owner's (JUDGEMENT Division schedule, JUDGEMENT Placement) |
| Attack orders cannot reach attackers on the wall or ladders | 2 | The reserve meets them where they come down into the fort, by move orders, and the breach reading then concerns those moves |
| No battle reaches the timer | 3-5 | The timer win stays unverified; check 5 is reported as unobserved |
| The witness never passes the gate | 3c | No round; a step down or a revised witness gets a new gate |
| The private record costs too much CPU per second for 28 units | 1a | Read `sample_cpu_ms` |
| The recorder's final check refuses the hold after the owner's win | 4 | The refusal is kept in `reserve_final`; the attempt does not count for check 10 |

## Variation and the eventual run plan

The first version is one fixed battle for development. Later variants could swap which division
carries the elite troops, move the General to the last division, shift a release by 60 s, change
which side D4 stages on, or add one ram and one siege tower once stage 1e shows who mans them.
Each changes one thing and predicts what should change; until the owner chooses a reservation
policy, every inspected variant is development evidence. An announced-schedule arm, where the
briefing gives the release times, is the foreknowledge control in the style of Cannae B. A team
version could split the garrison into wall, reserve and artillery commands for the
[communication structure](communication-structure.md) work, after the single-controller version is
understood. Before any scored run, a frozen experiment card gives the arms, launches, stop rule,
budget and analysis, as the [Cannae run plan](cannae-eval.md#variation-and-the-eventual-run-plan)
lists.

## Decisions for owner review

Four questions, with the recommendation first; the build at `f3fec92` used the recommended answer
to the first three:

1. **Battle and pairing.** (a) Haengju with a Grand Cathay garrison against Empire divisions
   (recommended; built): it uses WH3's own faction and a rocket battery like the hwacha, at the cost
   of checking Cathay recruitment and Harmony first. (b) Haengju as an Empire mirror: fewer new
   mechanics, matches Cannae, loses the WH3-specific part. (c) Another battle from
   [the candidates](#why-this-battle).
2. **How divisions attack.** (a) Fixed release times of 150, 300 and 450 s, and a group the garrison
   damages comes on at once (recommended; built): the same sequence in every launch unless the
   controller damages a waiting division, which is recorded. It is a scripted opponent, which the
   owner's reply 5 made no priority; Cannae B is the precedent. (b) Each division released when the
   previous one routs: closer to the history, but the sequence then depends on the controller's
   play throughout. (c) No script: on Helmgart the divisions would arrive within about 50 s of each
   other, and the battle would be the existing siege family with a Cathay garrison, which the
   all-at-once arm already is.
3. **What the briefing says.** (a) One sentence that the divisions may attack at different times
   (recommended; built). (b) Rules only. (c) Rules and the release times, as a foreknowledge arm.
   The review of the set also asks for one disclosure rule for every scripted opponent, since
   Cannae B publishes its trigger and release bounds.
4. **The primary claim, once the gate passes.** (a) The fire decision: `WallWitness` against
   `WFire`, 16 launches per arm at 5 s / 5 s (recommended): 32 launches, about 11-13 h, power 0.74
   for a 20% → 70% gain; at 10 per arm it is 20 launches, about 7-8 h, power 0.43 (other rates in
   the [overview's grid](historical-evals.md#method-rules-the-set-shares)). The rule is partly a
   timing rule, and it also holds every long shot until an able enemy is within 60 m of the line or
   inside it. (b) The sequence: `WallWitness` on the waves arm against the all-at-once arm at the
   same counts, which asks whether the script changes the outcome for this witness and claims no
   tactic. (c) Winnability only for now: the gate and the owner's win, with no decision claim. Two
   additions to (a) are offered as options. First, a mechanism requirement in Izmail's shape: the D1
   label also requires that witness launches keep more summed ammunition at D3's approach than
   `WFire` launches, by a rule fixed before the round, and an effect without it reads "mechanism not
   shown". Second, an all-at-once screen: `WallWitness` and `WFire` on `cth-emp-siege-a-all-v1`, two
   to four launches read descriptively with no pass rule; it could not show that the effect is
   close-range fire. The narrowing proposed under D1, for a fallback that comes before D3's
   approach, is also the owner's to decide.

Other open choices: the markers on this page and in the code and tests it names; which prompt a
model pilot reads (marker Pilot arms); whether stage 1e runs with the teleport and its crew rule or
with `deployment` null; whether the garrison keeps its lord (it has one because Gwon Yul led the
counterattack, and Cannae started lordless); whether the prompt's "Reserve briefing:" label
should change; which stages may start; and any budget for stage 6.

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
- Game database, read-only with `scripts/wh3_db.py` and RPFM's `schema_wh3.ron` on 2026-11-08
  (`can_siege` in `main_units_tables` on 2026-11-09), after Steam's 2026-11-03 update, build not
  recorded:
  `main_units_tables` (costs, men), `units_custom_battle_permissions_tables` (which faction lists
  the Cathay cards), `land_units_tables` (ammunition), `missile_weapons_tables`,
  `projectiles_tables` and `battlefield_engines_tables` (ranges, reloads, tower ranges) and the
  custom-battle siege vehicle table (generation probabilities). The installed game's help text for
  sieges was read locally and is not copied.
- Creative Assembly's battle script reference, read locally: `battle_unitcontroller`
  (`take_control`, `halt`, `release_control`), `battle_unit` (`number_of_men_alive`,
  `is_under_missile_attack`, `is_on_top_of_wall`, `is_climbing_ladder`), `battle_capture_location`
  (`linked_buildings`) and `battle_assault_equipment`.
- Recorded evidence, ignored by Git, under `runs/twwarhammer3/battle/`:
  `bench-b12-siege-baselines-20261016`, `bench-b12-siege-reserve-r2-20261016`,
  `smoke-random-siege-skills-20261014-0511` and the other `chd-reserve-grn-siege` family jobs the
  design recounted; the register [results.csv](results.csv).
  All as the design, the build and the review read them.
