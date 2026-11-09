# Siege attack evaluation after Izmail, 1790

Development candidate, 2026-11-08 (Claude); this page was written on 2026-11-09. **Built offline
at `f3fec92`; nothing has been launched or measured, and everything on this page is
unverified.** The owner's direction of 2026-11-08 was "Build now, game when I say"
([owner direction](../owner-direction.md)), and no game window has been named. The battle adapts
the Russian assault on the Ottoman fortress of Izmail in December 1790 as a WH3 siege in which the
controller attacks a walled fort held by a native AI garrison. It is built from the declaration
`ksl-emp-siege-a-v1` in [scenarios.json](../../configs/twwarhammer3/scenarios.json), the
siege-attack interface behind that declaration's `siege_assault` opt-in, the witness `Escalade`
and its controls in [battle/escalade.py](../../src/twwarhammer3/battle/escalade.py), the readings
in [battle/escalade_readings.py](../../src/twwarhammer3/battle/escalade_readings.py) and the
private all-unit record. The owner's choices are collected in
[decisions for owner review](#decisions-for-owner-review). A witness version 2, the options of
[question 6](#decisions-for-owner-review), is built beside version 1 in the same module
([version 2 options](#witness-version-2-options)); version 1 stays the default and no plan uses
version 2.

**The `llm` and `llm_rules` models can use the siege orders; the `commander` and team controllers
cannot.** The owner approved "models using siege orders" on 2026-11-09
([question 4](#decisions-for-owner-review)), and the `llm.py` change from branch
`izmail-llm-orders` landed as `llm`/`llm_rules` v23
([log](log.md#2026-11-09-prompt-v23-siege-orders-for-the-llm-controller)). Every controller that
shares `llm.render_state` now reads the fortification list, its siege vehicles and enemy-built
structures as facts. Only `llm` and `llm_rules` also read the paragraph on the two orders and send
a reply schema that carries `besiege` and `attack_building`. The `commander`'s plan schema has no
siege order. A team member, whether a `team_llm_rules` member or an `llm` or `llm_rules` leaf of a
configured `team`, keeps the land-battle schema, and a siege order in its reply is refused as
unknown (marker Team siege orders below). A `local_team` member's view carries no fortification
list, and its schema copies the land-battle one. The edit moved `llm.py`'s `source_sha256`, so
every `llm` and `llm_rules` card splits from the recorded `llm` battles. No battle has run on v23,
and no game has shown what the orders do.

The page follows the [scenario guidelines](scenario-guidelines.md), the
[evaluation guidelines](evaluation-guidelines.md) and the [benchmark contract](benchmark.md):
fixed armies, public structured observations, permitted orders, every engine win counts, and
automated play runs unpaused at 1x. It applies the rules that Claude's 2026-11-08 review of the
five siege designs proposed for the whole set, none of them agreed with the owner: one primary
contrast per battle, a frozen witness gate before any round, exact power printed in advance,
contact read from the engine melee flag, and a gate counted as breached at hp 0 or less. The
design, that review and the build records are `runs/siege-evals-20261108/final-izmail.md`,
`portfolio.md` and `lua-batch.json` (package L3), which Git ignores. Under the
[hard rule](../../AGENTS.md#verification-hard-rule) everything below is unverified, every count
from earlier battles comes from single recorded battles with other armies, and the history guides
the design and is no evidence about the engine.

The recorded runs this page cites ran on builds older than the pin, patch 9.0.5, Steam build
26403568 ([pins](integration.md#pins)), whose patch includes battle balance changes. By each job's
`environment.json`, the runs of 2026-10-13 and 2026-10-14 (the siege-attack, siege and settlement
smokes, `smoke-random-siege-skills-20261014-0511` and `attack-emp-mirror-20261013`) ran on 9.0.3,
Steam build 25823491, and the `bench-b12-*`, `bench-b13-*`, `bench-b18-*` and
`bench-b23-l1-setup-20261017` jobs on 9.0.4, Steam build 25961564. Only the 2026-11-03 checkpoint
battles (`siege-905-20261103`) ran on the pin. A stage 1 reading on 9.0.5 replaces the older one
it repeats.

## The historical battle

The account rests on four sources fetched for the design on 2026-11-08: the English Wikipedia
article (characters 0-100,000 of 118,235), the Russian Wikipedia article read through a
translation, the article in Sytin's pre-revolutionary Military Encyclopedia on Wikisource, and
Osipovsky (2026), a peer-reviewed article whose full text the design read. Duffy, Orlov (1890),
Gladky (1993), Grant, Bodart and Arsenyev appear only as those sources cite them and were not
fetched. This page did not fetch the sources again.

Izmail stood on the Kilia arm of the Danube. Sytin describes a bastioned wall about 6 versts long,
a main rampart 4 sazhens high (about 8.5 m) and a ditch up to 5 sazhens deep (about 10.7 m) and 6
wide, water-filled in places; the Russian article gives the ditch as 3-5 sazhens. There were four
gates: the Brosskie (Tsargrad) and Khotin gates on the west, the Bender gate on the north-east and
the Kilia gate on the east. Sytin counts 260 guns, 85 cannon and 15 mortars of them on the river
side. The Russian article quotes Suvorov's verdict after reconnaissance, "Крепость без слабых
мест", a fortress without weak points.

By the English article, the troops trained on a ditch and earth ramparts built like Izmail's, with
escalade and bayonet drill, and prepared ladders and fascines; a 24-hour ultimatum was refused, and
the bombardment began the day before the assault. The Russian guns disagree across sources: the
English text says "only 40 field guns, but no siege guns at all", its infobox gives 500-600
including the flotilla, and Sytin says about 600 guns bombarded the fortress on 10 December (Old
Style). The English sentence that the walls "could not be breached" is tagged [citation needed].

A first signal came at 3 a.m. (a "flare" in the English article, a "rocket" in Sytin and the
Russian article), and the advance began at 5:30. Nine columns attacked in three detachments (Sytin;
English article): de Ribas from the river with 9,000, Potemkin on the west front with 7,500 and
Samoilov on the east with 12,000, with Westphalen's 2,500 cavalry in reserve (English article).
Lassi's column was first onto the rampart (Sytin; English article). The Russian article says
Meknob's ladders, 5.5 sazhens (about 11.7 m), were too short and had to be tied together in pairs
under fire. Sytin has a sortie from the Bender gate against Orlov's column beaten off by Suvorov's
reinforcements of one infantry battalion, seven squadrons and one Cossack regiment; the translated
summary of the Russian article has no such sortie. Kutuzov's column took the Kilia gate after a
stubborn fight (Sytin), and the Russian article adds that he asked to withdraw and that Suvorov
refused and sent him a grenadier battalion. By 8 a.m. the ramparts were held and the Bros, Khotin
and Bender gates were open (English article). Sytin says the cavalry reserves entered after those
gates were opened; the English article says Suvorov kept the cavalry out until the infantry had
cleared the way and brought 20 light guns inside to fire along the streets. Qaplan Giray's
counterattack of 3,000-4,000 was stopped by regular infantry, and the fighting died down by about
4 p.m. (English article; Sytin). The sources also disagree about the Tabia redoubt, and only the
Russian article says that deserters had revealed the plan.

The numbers are contested. The attacker had about 31,000, of them 16,000 regulars and 15,000
irregular and poorly armed (English and Russian articles); Sytin has 25,000-30,000 by late
November. The garrison was 35,000 (Sytin; the English text, citing Arsenyev, Grant and Orlov) or
40,000 (Duffy, through the English article), and the English infobox gives 40,000-42,000.
Osipovsky quotes Suvorov's report of 35,000 armed men although rations were drawn for 42,000, and
concludes that the armed defenders "could not exceed 20 thousand" and were most likely
12,000-15,000; he cites Gladky (1993) that Suvorov "knew his troops were double the enemy's".
Losses disagree as well. Russian losses were 1,879 killed and 2,703 wounded (Orlov 1890, through
the Russian article), 2,037 killed and 2,933 wounded including the bombardment day (Sytin), or up
to 10,000 (Grant, Bodart and Arsenyev, through the English article). Ottoman losses were 26,000
killed and 9,000 captured (Sytin; Orlov through the Russian article), or no more than 15,000 dead
by Osipovsky.

The owner asked for a siege in which one side had a clear disadvantage and still won through
tactical superiority ([owner direction](../owner-direction.md)). Izmail meets that only in part.
On the official count the attacker had about 0.89 of the garrison (31,000 against 35,000); on
Osipovsky's count it had about twice as many armed men. The disadvantage that holds on every count
is the fortress: the rampart, the ditch, the guns and a garrison that refused to surrender and
fought in place. What the sources credit to the attacker is an assault on many sectors at once on
one signal, columns of infantry carrying ladders, reserves sent to columns in trouble (the Bender
sortie, Kutuzov's column), cavalry held outside until the gates were opened from inside, and light
guns in the streets. This page never claims that the attacker was outnumbered.

In the WH3 version the attacker costs 1.56 times as much by database cost (9,800 against 6,275)
and has 0.97 times as many men in the table (1,013 against 1,049). The defender holds the wall,
the gate and the four Fort Tower points and wins if the timer runs out. Whether that adds up to a
disadvantage in play is unmeasured.

## Why this WH3 game mode

The owner's answer on 2026-11-08 was "We can try to build those sieges but let's make sure we're
adapting them well to WH3's game modes". Izmail adapts to WH3's siege mode played as the attacker
and to no other lobby mode. The design weighed three proposals and one map variant.

| Proposal | WH3 mode | Verdict |
|---|---|---|
| P1, the escalade | Siege, the controller attacks a native AI garrison on Helmgart | Built as `ksl-emp-siege-a-v1` |
| P2, wing captains | The same siege with one model per sector | Deferred until P1 is understood: it stacks on P1's unverified interface, its view split is a radius rule that WH3 does not supply, it lacks a pre-agreed-clock foil, and the scripted team witness failed Cannae C's 4-of-5 gate |
| P3, a minor settlement | Settlement battle without walls | Rejected: in three recorded Osterwald launches the engine placed the defending army about 650-750 m from the Key Building (the design's reading, which reread `smoke-settlement-kho5-dwf5-attack_nearest-20261014-0214`), the objective is rout-all only, and its decision repeats `coord-pincer`, `coord-breakout` and Cannae A |
| Altdorf, `battle_preset_major_a_emp` | Siege on a capital map | A later variant: six gates and five victory points, some barricades and towers already built at 5 s, and its one player-side wall besieger routed before it reached the wall (the design's reading of the 2026-11-03 checkpoint battle) |

A siege the player attacks fits Izmail for these reasons, each with what it rests on:

- The engine sets the problem, and no enemy script is needed. The first observation (5.3 s) of
  `smoke-siege-attack-kho5-dwf5-probe_abilities-20261014-0830`, the only siege the player attacked
  in a play job, reread for this page, has type `settlement_standard`, role attacker, timeout
  winner enemy, and an enemy ticket row of 1,000 with `per_s` 5. In the 4 recorded Helmgart
  ticket drains that field read 5 at rest from the start and 0 in every reading during the drain.
  In the episodes' 1 Hz replay frames it turned 0 between 81 and 135 s before each drain began.
  So it is neither the drain rate nor a sign of a drain (recounted for this page;
  [check 3(f)](#proposed-deciding-checks)). Its objectives text says "The attacker must destroy or
  rout all enemy units before the timer expires, or reduce the enemy victory tickets to 0" and
  "Losing capture points to the attacker will cause the defender to lose victory tickets". The
  owner's 2026-11-04 reply put easy scripting "not an initial priority", and this battle needs
  none.
- Every victory point lies behind one wall with one gate. On Helmgart the gate stands at
  (-32,-16), the four Fort Tower points along the wall, and the Key Building and three Minor Supply
  Locations at z 155 to 320 (the same first observation).
- The engine's siege rules give the problem the history describes. In the source launch of the
  2026-11-03 Helmgart checkpoint case (`siege-905-20261103/helmgart-defender`), as the design read
  it, AI-side infantry climbed the wall on ladders, a ram was pushed to the gate, and the cavalry
  got in only through the broken gate. That was the AI attacking a garrison that never moved, so it
  shows nothing about a climb by the player's units.
- The orders that existed before `f3fec92` cannot attack a wall. In the attack smoke our units
  received 650 attack orders and no move orders over 776 decisions, and in 776 observations no
  unit carried a melee flag although 6 friendly-enemy pairs stood within 40 m, 364 pair readings
  across the observations, the closest 10.1 m apart (f3 and e5 at 714.5 s); all recounted for this
  page from the trace. The job ran the `probe_abilities` script, and our units lost men: f2, f3
  and f4 fell from 75, 75 and 45 to 13, 29 and 19. The trace ends at 730.7 s with the gate
  untouched and no recorded ending: no result row, no register row, and a manifest that reads
  `interrupted` with no episode. [Battle types](battle-types.md#the-player-attacking-a-siege) says
  the run was stopped by hand, which the record does not show. The defence smoke of the same day
  has 1,625 melee flags (the design's count), so the flag works.
- It covers a gap. [O2](tactics-reference.md#o2-siege-assault-and-diversion) in the tactics
  reference asks for an assault that threatens more than one approach and lists gate attacks and
  wall targeting as missing orders. The 22 siege rows in the [register](results.csv) all come from
  scenarios in which the enemy attacks (counted for this page), and the existing siege family
  (`chd-reserve-grn-siege`, `coord-siege`) and [Haengju](haengju-eval.md) all have the player
  defend Helmgart.

The adaptation drops the river landing, the night approach, the replica training, the bombardment
day, the nine columns (three assault groups here), most of the 260 guns (the garrison has one Great
Cannon and one Mortar, beside the fort's own towers), the deserters and the street
fighting as a phase of its own. The Little Grom stands in for the light guns.

JUDGEMENT: Escalade adaptation — Claude, 2026-11-08: Izmail's escalade as a WH3 siege the player
attacks on Helmgart, with no enemy script. Altdorf's six gates, or dropping Izmail for its contested
disadvantage, changes the battle; every reading on this page rests on it.

## Battle specification

The declaration is `ksl-emp-siege-a-v1` in
[`scenarios.json`](../../configs/twwarhammer3/scenarios.json), `scenario_version` 1, family
`siege attack`, split `development`, status `prototype_not_admitted`. Its values rest on JUDGEMENT
tests/twwarhammer3/test_wh3_siege_assault.py Siege attack construction profile (map, rosters,
`expect`, rank 0 and the engine's starts) and Siege attack equipment (one ksl ram, no tower). The
JSON file cannot carry a comment, so those markers sit in that test, which also checks the
declaration. The faction pairing, the lord and the timer belong to the construction profile.

In the fields of [the scenario specification](scenario-guidelines.md#the-scenario-specification):

| Field | This battle |
|---|---|
| Question and coverage | Whether an assault on three wall sectors at once beats one on the gate recess against a native garrison ([D1](#the-decision), the one claim); the Lancers' wait, the start timing, the reserve and suppression are descriptive or exploratory. Siege attack against native AI. Claims excluded: that the attacker was outnumbered, recognition of the battle, model ability |
| Public task | Win the battle; every engine win counts, and the timer ending is a loss for the attacker. The public observation with the siege fields and the orders listed below, `besiege` and `attack_building` included, unpaused at 1x, with no added briefing; `llm` also reads its prompt's How to fight section ([public briefing](#public-briefing)) |
| Concrete setup | The settings below, [rosters](#rosters) and [map and starts](#map-and-starts). No build has read this battle (the pin is 9.0.5, Steam build 26403568); Kislev and Empire unit keys and a ksl ram, which the lobby readback (check 0) checks |
| Decision opportunity | [D1](#the-decision): from the start, with the fortification list and the wall's defenders in view; three sectors or the gate recess. The groups stage 150 m south of their targets and climb at phase 2, by 150 s at the latest |
| Mechanic reference | [Why this WH3 game mode](#why-this-wh3-game-mode) and [the interface](#the-siege-attack-interface-as-built): CA's documentation, the recorded runs on 9.0.3 and 9.0.4, the 2026-11-03 checkpoint battles on 9.0.5, and database values read on 2026-11-09. Unread: the mod's siege orders, `is_on_top_of_wall`, a player climb against an active garrison, a siege timer win |
| Winnability evidence | None yet: the owner's demonstration (check 8) and the frozen witness gate (check 6) |
| Controls and predictions | [Witness and controls](#witness-and-controls-as-built); condition X and variant Z in [the decision](#the-decision) |
| Measurements | [Measurements](#measurements) |
| Variation and exposure | One development version, split `development`, no reserved variant ([variation](#variation)); this page and the code are public |
| Validation plan | [Proposed deciding checks](#proposed-deciding-checks) and [live stages](#live-stages) |
| Release record | Built at `f3fec92`; the siege orders reached `llm` and `llm_rules` as v23 at `da05498`; the readers and this page revised on 2026-11-09; `prototype_not_admitted`; nothing launched |

The settings:

| Field | Setting |
|---|---|
| Mode and role | `battle_type` `siege` (engine `settlement_standard`); `attacker` `player`, `expect.player_defends` false; native AI garrison, which wins at the timer |
| Map | Helmgart, `battle_preset_wh2_dlc13_minor_settlement_empire_fort`; x -384 to 384, z -640 to 384 ([Haengju](haengju-eval.md#the-map)) |
| Factions | Player `wh3_main_sc_ksl_kislev` / `wh3_main_ksl_kislev`; enemy `wh_main_sc_emp_empire` / `wh_main_emp_empire`; both with a lord |
| Difficulty and scale | AI `ai_level_very_hard`, stats modifier 1.0, large units (0.75), realism off, rank 0 for every unit |
| Timer and funds | 1,200 s (the lobby offers 1,200, 2,400 or 3,600); `funds_custom` 20,000, which both rosters fit by database cost; the lobby charge, the ram's included, is unread |
| Siege equipment | `siege_equipment` `{ksl_battering_ram: 1, ksl_siege_tower_15m: 0}`: the lobby steps remove every piece the player's slot holds, add one ram and read back the count per key, and `check_battle` compares the battle's `assault_equipment` with the declaration (rests on JUDGEMENT src/twwarhammer3/battle/setup.py Battle-side equipment check) |
| Placement | No `deployment`: the engine's own starts for both sides; teleporting units in a siege is untested |
| Toggles | `behaviour_defaults: true` (fire at will on at the start; the controller may change it) |
| Opt-ins | `siege_assault: true` (the fields and orders [below](#the-siege-attack-interface-as-built)); `private_record: true`, which `siege_equipment` requires |
| Withheld words | 29 lower-case words: the 1790 sources' people, places and sides, and "escalade"; a job or recording name that holds one is refused (rests on JUDGEMENT? tests/twwarhammer3/test_wh3_siege_assault.py Siege attack withheld names) |
| Script | None: the garrison is native AI from the first tick, with no hold, release, reserve or custom objective |
| Public task | Win the battle; any engine win counts, and the timer ending is a loss for the attacker |
| Input and control | The current public observation with the siege fields, and the orders `move`, `attack`, `halt`, `behaviour`, `ability`, `besiege` and `attack_building`; automated play unpaused at 1x |
| Exposure and status | Development candidate; no reserved variant, no lobby readback, no agreed check |

### Rosters

Costs are `main_units_tables` `multiplayer_cost` and men its `num_men`, and weapons, ammunition,
armour and morale come from `land_units_tables` and `projectiles_tables`, all read from the
installed game with `scripts/wh3_db.py` on 2026-11-09 for this page. The costs, men and
ammunition match the design's 2026-11-08 reading; the ranges are new here. The engine's own
`range` field read the same values in recorded battles with other armies: 90, 140, 145 and 420 m
for the four Kislev missile units in the first observations of `bench-b12-m1-kislev-20261016`,
`bench-b12-kislev-baselines-20261016` and `bench-b12-kislev-reserves-r2-20261016`, 145 m for the
Handgunners in `attack-emp-mirror-20261013`, and 145 and 160 m for the Handgunners and Crossbowmen
in `bench-b23-l1-setup-20261017` (read by this page's review and reread for this page). No lobby
has read these rosters back, so the charge and the recruited sizes are unverified.

| Attacker, Kislev | Count | Cost | Men (table) | Weapons and ammunition | Group in `escalade.py` |
|---|---|---|---|---|---|
| Boyar `wh3_main_ksl_cha_boyar_0` | 1 | 700 | 1 | Axe; no missile weapon | Reserve |
| Armoured Kossars `wh3_main_ksl_inf_armoured_kossars_0` | 5 | 700 each | 100 each | Axe; pistol 90 m, 6 shots; plate 80, morale 65 | Two West, two East, the rest Reserve |
| Kossars (Spears) `wh3_main_ksl_inf_kossars_1` | 3 | 500 each | 90 each | Spear; bow 140 m, 20 arrows; leather 15, morale 60 | One each in West, Centre and East |
| Streltsi `wh3_main_ksl_inf_streltsi_0` | 2 | 850 each | 90 each | Halberd; rifle 145 m, 20 rounds; plate 70 | The western one Centre, the other Reserve |
| Winged Lancers `wh3_main_ksl_cav_winged_lancers_0` | 1 | 1,000 | 60 | Lance; plate 80 | Horse |
| Little Grom `wh3_main_ksl_veh_little_grom_0` | 1 | 1,400 | 2 | Cannon 420 m (minimum 10 m), 22 rounds, can damage buildings; `can_siege` true | Centre |

| Garrison, Empire | Count | Cost | Men (table) | Missile |
|---|---|---|---|---|
| General of the Empire `wh_main_emp_cha_general_0` | 1 | 600 | 1 | None |
| Halberdiers `wh_main_emp_inf_halberdiers` | 2 | 550 each | 120 each | None |
| Handgunners `wh_main_emp_inf_handgunners` | 3 | 600 each | 90 each | Rifle 145 m, 22 rounds |
| Spearmen `wh_main_emp_inf_spearmen_0` | 3 | 300 each | 120 each | None |
| Crossbowmen `wh_main_emp_inf_crossbowmen` | 1 | 475 | 90 | Crossbow 160 m, 22 bolts |
| Great Cannon `wh_main_emp_art_great_cannon` | 1 | 800 | 44 | 22 rounds; `can_siege` true |
| Mortar `wh_main_emp_art_mortar` | 1 | 600 | 44 | 22 rounds; `can_siege` true |

The attacker has 13 units, 9,800 in cost and 1,013 men in the table, about 760 at large scale; the
garrison has 12 units, 6,275 and 1,049 men, about 787. The army's missile stock is 3 × 20 arrows,
2 × 20 rifle rounds, 5 × 6 pistol shots and 22 Grom rounds. Equal cost would not mean equal
strength in a siege, because the wall, the towers, the gate and the timer belong to the defender.
The ram's crew is one of the 13 units, and which one the engine picks is unread: in the 2026-11-03
checkpoint battles a ram read an occupant type at 5 s before any order (the design's reading). The
crews there were the earliest infantry in army order, and all of them were Swordsmen, so "the
first infantry in army order" (here the first Armoured Kossars) is a weak prediction for Kislev.
In `helmgart-defender` the siege tower at (262,-236) read no occupant and never moved while the
AI's infantry climbed ladders, so a tower may stay uncrewed (the second look's reading, rechecked
for this page). If the crew is an Armoured Kossars, the Reserve holds no Armoured Kossars.

Recruitment: the Boyar, Armoured Kossars, Kossars (Spears), Streltsi and Little Grom appear in the
first observation of `bench-b12-m1-kislev-20261016` (the design's reading). The Winged Lancers are
declared in `ksl-ffa-grn-dwf-12`, which has no register rows, and in the unlaunched two-front
battles, so their recruitment is unread, and so is a ksl ram in the player's slot. No recorded
lobby has run the equipment removal step: the 2026-11-03 lobbies held no equipment
(`setup.siege_equipment_steps`).

### Map and starts

Axes: x runs across the map and z from the attacker's side towards the defender's. These points
come from the attack smoke's first observation and match the [Haengju map](haengju-eval.md#the-map):

- The gate (`mode.gates`, "Gatehouse") at (-32,-16) and the Gatehouse capture point c2 at
  (-2,-22.5).
- Fort Tower points c3 (188,-81), c4 (58,-31), c5 (-62,-31) and c6 (-192,-81).
- Victory points: the Key Building c1 at (0,310) and Minor Supply Locations c7 (-1,155),
  c8 (-320,320) and c9 (320,320). At 5.3 s the smoke read the enemy holding c1, c2, c6 and c7-c9,
  and nobody holding c3-c5. `Escalade` binds to these ids and keys and refuses any other map.
- The wall line is unread as pieces. In the 2026-11-03 Helmgart checkpoint launch, as the design
  read it, defenders standing on the wall read y 345 against ground near 330: Swordsmen at
  (212,-73) and (164,-73), Handgunners at (-49,-21). That puts the wall near z -20 in the centre
  recess and near z -75 to -100 for x between about 160 and 260 on either side. Stage 1 reads the
  pieces from `mode.fortifications`, and the offline fixture's 11 wall pieces are a sketch along
  this line.
- Starts recorded so far, with other armies: the smoke's five Khorne attackers at x -193 to -244,
  z -191 to -257, and its five Dwarf defenders at 5.3 s at (-286,-88), (-2,-23), (-246,-75),
  (-217,-71) and (-4,89) (reread for this page); in the checkpoint launch an Empire AI attacker
  near (0,-247) and (22,-229) with its ram at (0,-231) and a siege tower at (262,-236) (the
  design's reading). Stage 1 reads the 13- and 12-unit starts of this battle.
- Timings recorded so far, as the design read the checkpoint launch: an AI-side ram crew under the
  checkpoint's script pushed the ram from (0,-231) to (-2,-30) in about 105 s (about 1.9 m/s), and
  the gate's raw hit points fell from 4,380 to 0 between 105 and 120 s against defenders who never
  moved; an AI-side besieger the script ordered at 10 s read `is_climbing_ladder` from 100 s at
  y 330 and reached y 345 at about 130 s. Those were AI units against an idle garrison, so they
  give only an order of magnitude. Public gate hp is a percentage, so the raw values are never used
  as public thresholds.
- The ram stopped at (-2,-30), 33 m from the gate's position (-32,-16), and in
  `bench-b12-siege-baselines-20261016` episode-0001 the Trolls that broke the door stood at about
  (-2,-23), 31 m from it (both rechecked for this page). A gate rule keyed on g1's centre must
  allow for that offset ([check 3](#proposed-deciding-checks)).
- In the player-side Altdorf launch (`capital-attacker`) the crew ordered at 10 s pushed its ram
  about 300 m by 240 s under fire, about 1.3 m/s (1.2 m/s over its first 180 s), and fell from 90
  to 58 men; it was still about 260 m from the gate at 240 s (recounted for this page from
  `native.jsonl`). The UI's `VehicleList` `IsDestroyed` read true while a ram
  still moved: there from 140 s with `health_percent` 0.99, and in `helmgart-defender` from 70 s
  with 0.999, before that ram broke the door. A ram's state is read from `health_percent`. No code
  here reads `IsDestroyed` for a vehicle, and the mod's vehicle reading (`crew_reading`) records
  neither field.

```text
 z  320  c8(-320,320)               c1 KEY (0,310)                c9(320,320)
 z  155                              c7 (-1,155)
 z  -20               c5(-62,-31) GATE(-32,-16) c2(-2,-22) c4(58,-31)
 z  -80  ==c6(-192,-81)=======  centre recess, about 120 m  =======c3(188,-81)==
 z -230  attacker starts seen near x -245 to 262, z -190 to -257 (stage 1 reads ours)
```

The picture is a schematic built from those points.

### Public briefing

The declaration has no `scoring`, `benchmark` or `reserve` key, so `play.public` adds nothing to
the observation, and its `brief` text reaches no controller. A controller sees the native Battle
section (mode, role, timeout winner, objective text, tickets, capture points and gates), its own
units, the visible enemies, the public enemy roster and, under the opt-in, the siege fields below.
Under the opt-in the mod leaves `mode.slots` out: in a siege the player attacks, that list held the
defender's eight tower slots and their build timers (the 2026-10-14 attack smoke).
The observation carries `job`, so job names stay neutral (for example `siege-r1-003`, the name the
declaration test accepts); a name holding a withheld word is refused by `setup.check_job`, which
`play` and the recorder both call.

What an `llm` or `llm_rules` model reads since v23: the fortification list with each piece's health
and each tower's holder, one paragraph describing the two siege orders and their refusals
(`SIEGE_ORDERS`), its own siege vehicles and their crews, enemy-built structures, and on its units
"on the wall", "can climb walls" or "cannot climb walls" and "can attack buildings". Also in v23,
revised on 2026-11-09 before any battle: a unit whose last accepted order was `besiege` or
`attack_building` reads "last siege order: besiege w3 at 120 s (the state cannot confirm it is still
carried out)" in place of "no order". The line stays until a later move, attack or halt is accepted,
or `llm.holds_siege` drops it: the unit has no men or routs, a besieger reads on the wall, a gun has
no ammunition, or the target reads 0% or leaves the list. The ticket line adds each count's change
since the previous decision. Both are tested offline only, and every exit but a unit with no men
left has a test (`test_wh3_siege_assault.py`). It reads no history, no battle name, no staging
point, no hint that defenders move along the wall and no sentence about ladders. An `llm_rules`
model reads no recommended tactic: its system prompt, `configs/twwarhammer3/rules_prompt.md`, has
none. An `llm` model reads no battle-specific tactic beyond the How to fight section of
`configs/twwarhammer3/system_prompt.md`, which bears on this battle in two places. Line 34 says "A
missile unit never trades fire with enemy missile infantry", and the defenders on this wall include
Handgunners. Line 30's "One body: from the first turn, advance the lord and the melee units side by
side" is a weak link to D1's concentrated arm only, since it is about arriving together in the
field. The design's one sentence on climbing waits until stage 2 shows that these units climb. The
`commander` reads the same without the paragraph, the siege-order line and the ticket changes; a
team member reads the lists without the paragraph and without the climb, wall and building words,
because `team.project` leaves `on_wall`, `can_climb` and `can_siege` out of every unit row.

JUDGEMENT: Escalade briefing — Claude, 2026-11-08: a model gets the parked llm.py text on branch
izmail-llm-orders (fort list, SIEGE_ORDERS, climb and building abilities) and no history, tactic
or climbing sentence. More or less text changes what models know; model arms rest on it.

JUDGEMENT: Team siege orders — Claude, 2026-11-09: llm.py LLMPolicy.decide gives a team member's
view neither SIEGE_ORDERS nor the siege schema and refuses its siege orders. Members with them (and
project() keeping the climb fields) could besiege; any team arm in this battle rests on it.

## The siege-attack interface as built

The interface exists only in a scenario with `"siege_assault": true`, which validation accepts only
in a two-sided siege the player attacks, so every other battle's observation and prompt stay as
they were (rests on JUDGEMENT src/twwarhammer3/battle/setup.py Siege assault boundary). The build
review compared 741 recorded request bodies from 147 traces with `e918091` and found all of them
identical, and validated 12,503 recorded order batches with the same result as before; the
declaration test freezes the request for a land battle the player attacks and for a siege attack
without the opt-in.

Observation fields, written by the battle Lua (`setup_fortifications`, `fortification_reading`,
`mode_section`, `siege_unit`, `siege_vehicles`, `enemy_structures`) and described in
[engine/mailbox.py](../../src/twwarhammer3/engine/mailbox.py). What is public rests on JUDGEMENT
src/twwarhammer3/engine/mailbox.py Siege attack fields, which takes the design's owner question 3,
option (a):

- `mode.fortifications`: gates g1.., wall pieces w1.. and towers t1.., each with `kind`, x and z
  from `central_position()` (CA's documentation calls `position()` a pivot point), `hp` as a whole
  percent of `health()`, and for towers an `owner` of us, enemy or none. Wall pieces are the wall
  list minus gate buildings, because `lib_battle_manager.lua` puts every gate in the wall list too.
  Ids are given once at setup, ordered by centre x then z, and each id keeps its building object for
  orders.
- On our units, `on_wall` (`is_on_top_of_wall`), `can_climb` (`can_climb_walls`, read once) and
  `can_siege` (`has_attribute("can_siege")`, read once); on visible enemies, `on_wall`.
  `is_climbing_ladder` never reaches a policy: in the 2026-11-03 checkpoint battles it read true at
  ground height on the approach and for defenders (the design's reading).
- `mode.vehicles`: only vehicles one of our units crews, with that unit's id, as `v` plus the UI's
  vehicle list index (rests on JUDGEMENT? src/twwarhammer3/engine/mailbox.py Siege vehicle list).
- `mode.enemy_structures`: the other armies' finished builds only.
- A list or field that fails to read is absent, never empty or false.

Orders, validated in [protocol.py](../../src/twwarhammer3/protocol.py): `besiege` and
`attack_building`, each `{unit, target, run}`, accepted only while the observation lists
`mode.fortifications`. Each replaces a unit's move, attack or halt and cannot be queued.
Validation refuses a target that is not listed, a target at 0% or less (the breach rule of
`evidence_rules.gate_breached`, applied to every piece), a routing or shattered unit, a wall
`besiege` by a unit whose `can_climb` is not known to be true, and an `attack_building` without
`can_siege` true and ammunition left. The Lua mod (`apply_siege`) refuses an unknown or destroyed
target, a wall `besiege` by a unit that cannot climb and an `attack_building` without `can_siege`
or ammunition, and calls the unit controller's `besiege_building(building, 1, run)` or
`attack_building(building, 1, run)` on the kept building object (signatures from CA's
`battle_unitcontroller.html`); its acknowledgement confirms that the order was issued, and
nothing more.

Setup and evidence: `check_battle` raises `ProtocolError` unless `setup.siege_assault` reads ok with
a gate and at least one wall piece listed. The private record (`capture.copy_private_record`)
writes one frame per engine second beside the replay with every unit of both sides, hidden enemies
included: position, men, routing, shattered, melee, `on_wall`, climbing, visibility and
ammunition, plus equipment, vehicles and crews, raw gate hit points, capture holders and tickets.
It never enters the observation (rests on JUDGEMENT? src/twwarhammer3/battle/capture.py Private
record in scored battles and Private record fields).

The CA calls behind the two orders, `besiege_building` and `attack_building`, have live readings
from the 2026-11-03 checkpoint battles, sent through
`tests/twwarhammer3/checkpoint_siege/assault.lua`: on AI-side units on Helmgart
(`helmgart-defender`) and on the player's own units on Altdorf (`capital-attacker`)
([map and starts](#map-and-starts)). Still unread: the mod's wrappers
(`apply_siege` and the readings behind the fields above, `is_on_top_of_wall` among them) and a
climb by the player's units against an active garrison; the full list is in
[integration](integration.md#unverified). The Lua tests run the mod's real definitions under Lua 5.1
against a fake engine that answers with CA's documented values, so they show what the mod does with
those answers and nothing about what the engine returns.

## The decision

The 2026-11-08 review found no existing equivalent of D1 in the register or the set, and counted
the Lancers' wait among the cavalry-timing decisions that the set counts once, in
[Cannae A](cannae-eval.md). This battle therefore claims D1 alone.

**D1, spread or concentrate.** At the start the army stands south of the wall with the public
fortification list and the defenders on the wall in view (all five Dwarf defenders were visible at
5.3 s in the smoke; this garrison's visibility is unread). Two choices are feasible: assault three
sectors at once, with West on the wall piece nearest c6, Centre's Kossars on the piece nearest c5
beside the gate and East on the piece nearest c3 (A, `Escalade`), or put West and East on the two
pieces nearest c5 and c4 on either side of the gate as well (B, `Concentrate`). Under condition X,
in which the native garrison moves units along the wall toward the sector being assaulted, A should
meet fewer defender units in melee per assaulted sector in the 120 s after our first `on_wall`
reading, and should win more launches than B. Under variant Z the prediction may disappear or
reverse: the defenders hold their posts, or the concentrated assault gets over the wall before
moved defenders arrive. If one sector's ladders cannot take every climber at once, A may win for a
reason other than the defenders' movement; the exercised reading in check 7 counts the moved
defenders, which separates the two.

The two arms as built also stage differently, because each group stages 150 m south of its own
target (`Escalade._bind` and `Concentrate.target_points` in `escalade.py`). On the fixture's
sketch pieces (`runs/siege-evals-20261108/scratch2/exploit-hunter/staging.py`, rerun for this
page), four of Concentrate's six West and East spots (all three West, one East) stand 15.7-25.9 m
from a Centre spot, in six pairs, where Escalade has no pair under 32 m; the other two East spots
have no Centre spot within 32 m. The six stand 117-151 m from the nearest listed piece, four of
them 117-132 m, against 144-155 m in Escalade; the Handgunners reach 145 m and the Crossbowmen
160 m.
The flank rows stand 12-14 m behind Centre's in z on the fixture; on the real map that gap
depends on the recess pieces' z, which stage 1 reads. A Concentrate loss can therefore also come
from a crowded staging closer to the wall, and its phase 2 may start later, which check 7's
disposition table shows. Changing the staging is part of [question 6](#decisions-for-owner-review),
and version 2 builds one such change as an option ([version 2 options](#witness-version-2-options)).

Condition X has one recorded hint. In the smoke the gatehouse Dwarf Warriors (e2) moved from
(-2,-23) at 5.3 s to (-47,-18) at 61 s, (-172,-70) at 120 s and (-183,-73) at 186 s, and the
Longbeards (e3) stood at the gate at 726 s (reread for this page). Those moves came before any
climb and went toward our start near x -200, so they may be positioning against the army's
approach, with no assault to respond to. That is one battle with five Dwarf units.

JUDGEMENT: Escalade claim — Claude, 2026-11-08: D1 (spread or concentrate) is the only claim; the
Lancers' wait (D2), the start timing, the reserve and suppression stay descriptive. Claiming D2 as
well changes what a pass means and its threshold; the one primary contrast rests on it.

What stays exploratory or descriptive:

- **D2, the Lancers' wait.** The witness holds the Lancers 300 m south of g1 until the gate reads hp
  0 or less or c2 is ours; `CavalryEarly` sends them to the gate at once. On 2026-11-05 the owner
  said "I actually don't think the problem of studying timing is that interesting for now"
  ([owner direction](../owner-direction.md)), so D2 is recorded (Lancer men lost before the
  breach, the time from the breach to the first victory point held) and never tested. The design
  had claimed it as a secondary decision with a fixed-order threshold; the review demoted it.
- **S1, a synchronised start** against groups that climb on arrival (`Piecemeal`).
- **S2, the reserve:** sent to the group losing men fastest or to the group with most units on the
  wall.
- **S3, suppressing fire before the ladders** (`ShootOnly`). In the smoke a Skullcannon spent all
  12 rounds by 139 s while the Quarrellers on the wall lost 3 men (the design's count), so fire at
  the parapet may do little.
- A pass would show that the spread rule mattered for this witness, at the 5 s / 5 s cell, on the
  version its ladder picked. It would not show that a model reads the wall or the defenders.

## Witness and controls as built

[battle/escalade.py](../../src/twwarhammer3/battle/escalade.py) holds the witness and seven
controls. Their names are not built-in policy names; a job loads them by module path, for example
`twwarhammer3.battle.escalade:Escalade`. Each reads only what `play.public` passes: its own units
(with `on_wall`, `can_climb` and `can_siege`), the visible enemies and `mode` (capture points,
gates, fortifications and vehicles). None reads `evaluation`, `setup`, `native`, `final` or the
job. The witness plays these rules:

1. **Binding.** At the first observation the army must be the 13 declared types with positions,
   the capture points must be Helmgart's ids and keys, and `mode.fortifications` must list g1 and a
   wall piece; otherwise the witness raises `PolicyFailure` with a cause, which ends the episode as
   a policy failure (a bare one would count as a forfeit, with the army standing for the whole
   battle). Groups come from type and start x, never from ids: Centre is the ram's crew (from
   `mode.vehicles`), the middle Kossars (Spears), the western Streltsi and the Little Grom; West and
   East are the two westmost and two eastmost remaining Armoured Kossars with the westmost and
   eastmost Kossars (Spears); the Reserve is the other Armoured Kossars and Streltsi and the Boyar;
   the Horse is the Lancers. The crew leaves its type's list first.
2. **Targets.** West takes the wall piece nearest c6, East the one nearest c3, Centre's Kossars the
   one nearest c5, and the crew and the Grom the gate g1; ties go to the smaller id.
3. **Phase 1.** Each group walks to spots 150 m south of its target (Centre: of g1), 40 m apart
   along x, facing it; the Horse waits 300 m south of g1.
4. **Phase 2,** when every able unit of West, Centre and East stands within 20 m of its spot, or at
   150 s. In one decision every climber with `can_climb` true besieges its target (one without it
   stands at its spot), the crew besieges g1, the Grom attacks g1 while it has `can_siege` true and
   ammunition, and the Centre's Streltsi attack the visible enemy nearest them among those within
   their range of g1.
5. **Phase 3.** A unit with `on_wall` true, or inside the front line, runs to the first victory
   point we do not hold, in the order c7, the nearer of c8 and c9, then c1. The front line is the
   southernmost fortification centre in each 40 m column of x, and inside means 10 m or more north
   of it (rests on JUDGEMENT? src/twwarhammer3/battle/escalade.py Front line). The order matters
   only in phase 3 and in phase 4 with no visible enemy, since phase 4 sends every unit at the
   nearest visible enemy. On the recorded ticket rule (check 3(f)) holding c7, c8 or c9 drained
   nothing until c1 fell; c7 lies on the way from the gate to c1, and c8 and c9 are a detour
   (rests on JUDGEMENT? src/twwarhammer3/battle/escalade.py Victory order;
   [question 6](#decisions-for-owner-review)).
6. **After a target falls.** A siege order goes only to a piece that this observation lists above
   0%. A climber or the crew whose target reads 0% walks in as in phase 3, and the Grom stops
   (rests on JUDGEMENT? src/twwarhammer3/battle/escalade.py After a target falls).
7. **Horse.** Once the public gate nearest g1 reads hp 0 or less, whatever `destroyed` says, or c2
   is ours, the Lancers ride to c7 and then c1 (`evidence_rules.gate_breached`, resting on
   JUDGEMENT src/twwarhammer3/battle/evidence_rules.py Breach rule). Two recorded gates read hp 0
   with `destroyed` false: `smoke-random-siege-skills-20261014-0511` from 179.5 s and
   `bench-b12-siege-baselines-20261016` episode-0001 from 258.4 s (the review's reading).
8. **Reserve.** 60 s after the first phase 2 it joins the group that lost the largest share of its
   men since phase 2, if that share is over 30%, and otherwise the group with most units on the
   wall (ties in West, Centre, East order), and besieges that group's climbing target. Until then
   the Reserve stays at its start.
9. **Phase 4.** Once 6 of our able units are inside the front line, every unit attacks the visible
   able enemy nearest it and keeps that target while it stays able and visible.
10. **Repeats.** An unchanged order is sent again only if, 10 s or more after it was last sent, a
    moving unit reads idle more than 15 m from its point, or an attacking or besieging unit reads
    idle or an attacker has no target; a refused order is sent again at the next decision.

The values rest on JUDGEMENT src/twwarhammer3/battle/escalade.py Escalade thresholds.

| Class (`arm` in metadata) | Role | Rule it changes |
|---|---|---|
| `Escalade` (`escalade`) | Witness, D1 arm A | None |
| `Concentrate` (`concentrate`) | C6, D1 arm B | West's and East's targets are the wall pieces nearest c5 and c4, beside the gate, staged as the witness stages |
| `CavalryEarly` (`cavalry_early`) | C7, D2 arm, descriptive | Until the gate is breached the Lancers ride from the start to 20 m south of g1 and attack the visible enemy nearest them within 50 m |
| `Piecemeal` (`piecemeal`) | C8, S1, exploratory | Each group starts phase 2 when it is staged, or at 150 s; the reserve's clock starts with the first group |
| `ShootOnly` (`shoot_only`) | C4, shortcut | A unit with ammunition stands 120 m south of its target (Centre and the Reserve: of g1) and shoots, ranged, the visible enemy nearest it within its range; out of ammunition it plays as the witness |
| `GateOnly` (`gate_only`) | C5, shortcut | No ladders: the infantry, its Streltsi holding their fire, and the Reserve wait 150 m south of g1; the crew besieges and the Grom attacks g1 in phase 2; once the gate is breached or c2 is ours, every unit but the Grom goes to the victory points |
| `BesiegeNearest` (`besiege_nearest`) | C3, shortcut | Its own plan: from the first decision every climber besieges the wall piece nearest its start, the crew besieges g1 and the Grom attacks it, and the Lancers, the Boyar and any non-climber attack the visible enemy nearest them; a unit on the wall, inside the front line, or whose target fell attacks the visible enemy nearest it |
| `EscaladeReplay` | C9, exploratory | `replay_schedule.ReplaySchedule` over a witness win; siege orders keep their fortification ids and are dropped when the target is not listed or reads 0% |
| `hold`, `rush_nearest`, `attack_nearest` (`battle/scripted.py`) | C1 and C2, shortcuts | `hold` gives no orders; the other two run or attack at the nearest visible enemy. None has played a siege the player attacks |

The controls' values rest on JUDGEMENT src/twwarhammer3/battle/escalade.py Control parameters; the
replay rests on JUDGEMENT src/twwarhammer3/battle/replay_schedule.py Replay carried out, Replay
time and Replay remap. The metadata of the witness and its subclasses records the groups, jobs,
targets, the phase 2 times and reason, the reserve's group and time, the gate's opening time and
the phase 4 time; `BesiegeNearest` records its plan. The trace logs the metadata whenever it
changes. Under `ShootOnly` the Armoured Kossars carry 90 m pistols, by the database and by the
engine's own readings given [above](#rosters), so from 120 m south of a wall piece they reach no
defender on that wall, keep their 6 shots and never climb. If the engine picks an Armoured Kossars
as the ram's crew, the ram is never pushed either. That follows the design's C4 text literally.
The build review raised this with the fixture's made-up 35 m pistol; the 90 m figure comes from
the database and the engine.

Offline evidence at `f3fec92`. The fixture
[wh3_siege_attack.py](../../tests/twwarhammer3/wh3_siege_attack.py) copies the attack smoke's
capture points, gate, tickets, role and timeout winner unchanged. Its fortification pieces (a gate,
11 wall pieces and 4 towers), the vehicle and its crew, the Kislev starts, ranges and ammunition,
and three defenders are made up, so every target id in the tests is a fixture id.
[test_wh3_escalade.py](../../tests/twwarhammer3/test_wh3_escalade.py) (18 tests) shows that groups
follow type and start x under shuffled ids, that the witness stages, assaults in one decision,
sends its reserve to a group that lost over 30% since phase 2 and releases the Horse at gate hp 0
with `destroyed` false, and that a unit whose target reads 0% walks in.
`Concentrate` differs from the witness only in West's and East's orders and `CavalryEarly` only in
the Lancers' (`wh3_ablation.assert_ablation`, which also renames the job and requires identical
orders); every arm's orders pass `validate_orders` on two fixture sequences; each control plays
its own rule; the replay keeps and drops siege orders as stated.
[test_wh3_escalade_readings.py](../../tests/twwarhammer3/test_wh3_escalade_readings.py) (4, and 7
since the second look's readers) and
[test_wh3_siege_assault.py](../../tests/twwarhammer3/test_wh3_siege_assault.py) (28, the interface,
the declaration and each controller's siege prompt and schema) cover the readings and the
interface. The 50 tests in these three files passed with v23 on 2026-11-09 (branch
`siege-review`), before the second look's tests were added. The readings tests build their
inputs in the producers' formats, the private record's frames and play's trace rows, and the
acted-on test copies the recorded course of the Altdorf ram crew.

The build planted 38 wrong versions, and the tests caught all of them, two only after a test was
added. Three of the 38 edit `llm.py`: R7c and L1 plant faults in the parked change, and R7d adds
a `SIEGE_ORDERS` line that on this branch fails only because the name does not exist here. The
independent review then found one blocking fault: once g1 read 0%, every arm kept ordering it,
validation refused the whole batch, and every later decision was refused, the Horse's release
included. It also found five minor faults, and its
own 9 planted versions caught 5 and missed 4 (an unknown `can_climb` accepted in Python and in Lua,
reserve losses counted from the battle's start, and the siege schema sent for any battle the player
attacks). After the fix round, the fixer's rerun on a scratch copy that still held the parked
`llm.py` change caught all 53 planted versions (the implementer's 38 less L1, the reviewer's 9 and
7 new ones), and four of them (R7c, M9, M10 and N7) plant faults in that parked code
(`runs/siege-evals-20261108/lua-batch.json`, L3). This page's review reran the 53 on a copy of
this branch on 2026-11-09: 49 applied and all 49 were caught, and those four found no text to
change (`runs/siege-evals-20261108/scratch/review-D2-escalade-page/plants.txt`). When v23 landed,
four more planted versions (a team member offered the orders, the paragraph in every controller's
state, the `llm` prompt without it, the old list header) each failed a test in
`test_wh3_siege_assault.py`; they are not in `tests/plants.toml`. None of this shows what the
orders do in a game.

### Witness version 2 options

Built offline on 2026-11-09 for [question 6](#decisions-for-owner-review), which the owner has not
answered. Version 1 (the classes above) stays the default: no plan, stage or card uses version 2,
and a part the owner declines can be dropped before the version is frozen, since each sits in its
own method or constant. `EscaladeV2`, `ConcentrateV2`, `CavalryEarlyV2`, `PiecemealV2`,
`ShootOnlyV2` and `GateOnlyV2` are their version 1 classes with the mixin `Version2`, and
`BesiegeNearestV2` takes the door rule only. Each keeps its version 1 `arm` name and writes
`"version": 2` in its metadata; a job loads one by module path, for example
`twwarhammer3.battle.escalade:EscaladeV2`. `OrderProbe` and `EscaladeReplay` have no version 2.

| Rule | Version 1 (default) | Version 2 option | Marker in `escalade.py` |
|---|---|---|---|
| Phase 3's order of victory points (question 6(a)) | c7, the nearer of c8 and c9, then c1 | c7, then c1 | JUDGEMENT Witness v2 victory order |
| When the crew and the Grom treat g1 as fallen (6(b)) | g1's own entry in `mode.fortifications` (the gatehouse building) reads 0%; the crew walks in and the Grom gets no new order | Also once the public gate nearest g1, its door, reads hp 0 or less (`door_view`). A unit whose last order besieges or attacks g1 and that gets no new one, the Grom among them, then gets one halt (`door_halts`); `BesiegeNearestV2`'s crew and Grom attack the visible enemy nearest them, or with none in view get the halt. Validation is unchanged, so a model may still order the building | JUDGEMENT Witness v2 door rule |
| Staging of West and East (6(c)); in `GateOnly` also the Reserve | 150 m south of the target (`GateOnly`: of g1), 40 m apart along x | The same rows, moved south in whole metres until every spot stands 150 m or more from every listed piece and 40 m or more from the Horse's, Centre's and earlier rows' spots; Centre and the Horse are unchanged | JUDGEMENT Witness v2 staging |

On the fixture's sketch pieces (`runs/siege-evals-20261108/scratch3/izmail-witness-v2/geometry.py`)
the staging change gives these numbers. Standoff is a spot's distance to its nearest listed piece;
approach is its distance to its own target.

| Arm | Flank standoff | Flank approach | Closest spots |
|---|---|---|---|
| `Escalade` | 144.4-155.2 m | 150-155 m | 40 m |
| `EscaladeV2` | 150.3-161.0 m (rows at z -244) | 156-161 m | 40 m |
| `Concentrate` | 117.2-150.8 m | 150-155 m | 15.7 m (an East and a Centre spot) |
| `ConcentrateV2` | 150.1-184.4 m (rows at z -218, 52 m behind Centre's) | 188-194 m | 40 m |
| `GateOnly` | 120.9-144.0 m; West and East share their spots, and the Reserve two of Centre's | 150-155 m to g1 | 0 m |
| `GateOnlyV2` | 153.7-215.9 m; rows at z -201 (West), -241 (East) and -276 (Reserve) behind Centre's at -166 | 185-229 m to g1 (West and East) | 40 m |

The three aims of the change cannot all hold on the fixture. The 40 m spacing holds, and so does the
150 m floor: each flank group's spot nearest a piece stands 150.3 m from it in `EscaladeV2` and
150.1 m in `ConcentrateV2`. Standoff is equal only for those nearest spots. Spot by spot,
`EscaladeV2`'s six flank spots stand 150.3, 156.0 and 161.0 m from their nearest piece on each side,
and `ConcentrateV2`'s stand 150.1, 169.1 and 183.8 m (West) and 184.4, 167.3 and 150.1 m (East), so
four of its six stand 11-23 m farther than the witness's spot at the same place in the row.
`ConcentrateV2`'s flanks also walk 188-194 m to their pieces against `EscaladeV2`'s 156-161 m,
because the wall's wings (w3 and w9 at z -88, w4 and w8 at z -55 to -60) stand south of the gate
recess, and its westmost and eastmost spots stay 150 m from w3 and w9 only at z -218. Keeping a
150 m approach for both arms (the standoff from the target alone, version 1) leaves four of
Concentrate's six flank spots 117-132 m from other pieces. A second rank 30 m behind Centre, at
z -196, walks 166-173 m, but its end spots stand 131.5 m from w3 and w9 against the witness's 150 m.
Stage 1 reads the real pieces; these numbers come from the sketch.

`ShootOnlyV2`'s firing spots are version 1's: on the fixture the ram's crew (Armoured Kossars,
6 shots) and the Reserve's Streltsi share (-12,-136) while both have ammunition. Version 2 does not
change that. `EscaladeReplay` still drops a g1 order only when g1's own entry reads 0%.

Version 2 sends the halt because the engine keeps an order on the building in force after the door
falls. In `runs/twwarhammer3/siege-905-20261103/helmgart-defender/source/native/native.jsonl` (48
readings) the attacking army's Great Cannon, under script control, got one `attack_building` on the
gate at 10 s (`tests/twwarhammer3/checkpoint_siege/assault.lua`) and no later order. Its ammunition
went from 55 to 52 between the reading at 120 s, the first with the door at 0, and the one at 150 s,
the first with the building at 0 and `destroyed` true, and stayed at 52 until 240 s. In version 1
the gun job sends nothing once g1 reads 0%, which matches that stop; in version 2, without the halt,
a Grom whose door has fallen would keep firing at the building. Whether a halt ends an
`attack_building` is unread: the mod sends it as `controller:halt()`, and no recording shows that
call on a unit firing at a building.

Offline evidence for version 2 in
[test_wh3_escalade.py](../../tests/twwarhammer3/test_wh3_escalade.py): a unit inside the front line
with c7 ours runs to c1 in version 2 and to c8 in version 1; with the door at hp 0 and g1 at 10%
(the 2026-11-03 Helmgart checkpoint read the door at 0 from 120 s while the building held 3,061 to
423 hit points until 150 s), `EscaladeV2`'s crew walks to c7 and its Grom gets a halt,
`BesiegeNearestV2`'s two attack the nearest enemy or, with none in view, get a halt, and version 1's
orders on g1 still pass validation; the phase 1 spots of `EscaladeV2`, `ConcentrateV2`,
`CavalryEarlyV2`, `PiecemealV2` and `GateOnlyV2` stand 40 m or more apart; in both arms each flank
group's spot nearest a piece stands 150 m or more from it (150.3 m and 150.1 m), which is the only
standoff the test compares; `ConcentrateV2` differs from `EscaladeV2` only in West's and East's
orders (`assert_ablation`); and the seven version 2 classes order only what validation accepts on
the three fixture sequences. Fourteen planted wrong versions were each caught on a scratch copy
(`runs/siege-evals-20261108/scratch3/izmail-witness-v2/plants.tsv`): version 1's tiers in version 2
and version 2's in version 1; the door rule removed, read from `destroyed`, or left out of
`BesiegeNearestV2`; no halt for the Grom, no halt in `BesiegeNearestV2`, and a halt for every unit
whatever its last order; version 1's staging; no standoff from the pieces; no spacing from earlier
spots; Centre left out of the spacing; the mixin placed after the version 1 class; and version 1 in
the metadata. None of this shows what version 2 does in a game.

## Measurements

The engine outcome is primary. Every reading below is descriptive until a check ties it to the
decision, and a missing value stays unknown. Contact is the engine's melee flag on a unit with men
left (rests on JUDGEMENT src/twwarhammer3/battle/evidence_rules.py Contact rule), and a gate is
breached at public hp 0 or less.

| Reading | Source and limit | Built |
|---|---|---|
| Outcome, `ended_by`, `battle_s`, `own_left`, `enemy_left`, `victory_held`, `key_held`, tickets | Register row and trace | Yes |
| Groups, jobs, targets, phase 2 time and reason, the reserve's group and time, the gate's opening time, phase 4 time, and the version (1, or 2 for the [options](#witness-version-2-options)) | Controller metadata in the trace | Yes |
| First `on_wall` reading, first victory point held, and the time between | `escalade_readings.wall_to_point`, public observations | Yes |
| Each unit's way in: ladder once it reads `on_wall`, gate when it first comes inside the front line within 20 m of g1 without having read `on_wall` | `entry_routes`; inside starts 10 m north of the line, so a unit that crosses the 10 m band in one reading gets no route (the review's note), and a unit first read already inside gets none | Yes |
| The first `on_wall` per group | `first_on_wall` over the private record's own units, never the garrison's; groups from the witness's metadata, or one group for a controller without them | Yes |
| How many wall sections our units hold on the wall within 120 s of the first `on_wall` reading: D1's branch for any controller, a model included (the second look's B1) | `wall_sections` over the private record; a section is a 120 m bin of x of the listed piece nearest the unit (rests on JUDGEMENT? src/twwarhammer3/battle/escalade_readings.py Wall sections). On the fixture's pieces the witness's three targets read 3 and Concentrate's 2 | Yes |
| Whether each accepted `besiege` or `attack_building` was acted on: its unit 50 m nearer the target within 60 s, or reading climbing within 120 s, with the times | `siege_order_acted_on`, the trace's decisions and acks with the private record; no outcome and no pass rule. A gun that fires from where it stands reads not acted on (rests on JUDGEMENT? src/twwarhammer3/battle/escalade_readings.py Acted on) | Yes |
| Defender units in melee in each assaulted sector within 120 s of a start time, and those of them that began more than 150 m along x outside it | `reallocation` over the private record's enemy units; a sector is its target piece's x ± 60 m (rests on JUDGEMENT? src/twwarhammer3/battle/escalade_readings.py Escalade readings) | Yes |
| Lancer men lost before the gate reads breached (D2, descriptive) | `lancer_losses`, public observations; nothing after the breach counts | Yes |
| Gate hp over time, ram position and crew | `mode.gates`, `mode.vehicles`; raw hit points in the private record | Fields only |
| Ammunition spent per unit | `ammo` and `ammo0`; spent shots are not hits | Fields only |
| Enemy structures built, and when | `mode.enemy_structures`, finished builds only; the private record holds no slots | Field only |
| Which holdings drain the defender's tickets (check 3(f)) | `wall_readings.ticket_onset` (the first public defender count below the first reading) beside the capture holders in `mode.capture_points`; `per_s` is no drain signal | Yes |
| Routs and rallies, both sides | Unit state in the private record | Fields only |
| Whether each shortcut carried out its play (check 5) | None | No |

The reallocation reading takes its start time and its frames from the caller. The design measures
from the first `on_wall` reading; the review asked for the end of staging as well, because in the
smoke the defenders moved before any climb. Check 7 below fixes which frames it passes.

## Proposed deciding checks

JUDGEMENT: Escalade deciding checks — Claude, 2026-11-08: the rows below, their counts (2 holds,
the climb go/no-go, 4 of 5 at 5 s/5 s, 2 units in 6 of 10, n per arm) and plants. Other counts
change what each stage may claim; every label rests on it.

These are proposals; none is in [agreed checks](../agreed-checks.md). They follow the set's shared
rules: one primary contrast per battle at two-sided Fisher p < 0.05 with a Newcombe interval
([exact_stats.py](../../src/twwarhammer3/battle/exact_stats.py)), a frozen 4-of-5 witness gate at
5 s added order age and a 5 s decision interval before any round, exact error rates and power
printed in advance, contact from the engine melee flag, a breach at hp 0 or less, tickets read
from the defender's row with a holder of none never counted as enemy, and units identified by type
key. An effect seen once shows that it can happen; showing that it is reliable takes more
launches.

| # | Claim | Evidence | Count and rule | Must fail on |
|---|---|---|---|---|
| 0 | Recruits | The set's lobby-only readback: the scenario's lobby steps without the Start click, then `setup.army_checks` | All 13 attacker and 12 garrison cards recruit, the Winged Lancers included; the player's slot holds exactly one `ksl_battering_ram` and nothing else | A copy with one key swapped; a lobby that still holds an `emp_battering_ram` from a Haengju launch (the removal step must clear every piece) |
| 1 | Constructed | Lobby readback and the private first reading, every launch; `check_battle` | Map, type `settlement_standard`, role attacker, timeout winner enemy, difficulty, modifier, scale, timer, funds, rank 0 and rosters by multiplicity; `assault_equipment` keys equal one ksl ram and `setup.siege_assault` reads ok with a gate and a wall piece (both built: `check_battle` raises otherwise) | One Armoured Kossars swapped for Kossars (Spears); an emp ram passing for the declared ksl ram and a failed siege setup ignored (both planted offline and caught); a setup that reads ok with no gate or no wall piece listed (a test added after `f3fec92`, when the set's integration review's plant of it survived) |
| 2 | Fort registry | Stage 1 first and last observations against the engine's three fort lists, read in the same launch | The gate listed once; wall pieces equal the wall list minus gates; centres within 0.5 m of `central_position`; ids unchanged after a piece falls; g1 within 1 m of (-32,-16); a tower within 30 m of each of c3-c6; no building with both a w and a t id; tower owners agree with the Fort Tower capture holders | Offline, built and caught: ids reassigned in list order, the gate counted as a wall piece, towers dropped, `position()` used for the centre, a zero-based owner reading. Live: a building listed twice must be reported |
| 3 | Orders reach effects, with the climb go/no-go | Stage 2 probe, trace, private record and video | (a) An Armoured Kossars and a Kossars (Spears) besieging a wall piece read `on_wall` within 150 s, with y within 3 m of the wall-top height the private record shows there. (b) The crew besieging g1 brings the ram within 15 m of the gate within 180 s. The recorded Helmgart ram stopped at (-2,-30), 33 m from g1's expected centre (-32,-16), and the Trolls that broke the door in `bench-b12-siege-baselines-20261016` episode-0001 stood at about (-2,-23), so (b) as written can fail a ram that works (marker Gate anchor below). (c) The Grom's `attack_building` on g1 lowers its hp within 60 s while its ammunition falls; whether g1's `health()` reaches 0 when the door breaks is recorded. (d) Streltsi fire at a visible wall defender lowers its men within 60 s (descriptive). (e) A unit on the wall reads melee within 60 s of an attack on an adjacent wall defender. (f) Which holdings drain the defender's tickets, read with `wall_readings.ticket_onset` beside the capture holders: first c7 alone as the control, then c1. The recorded rule, recounted for this page from 23 Helmgart siege traces with the player defending (9.0.3 and 9.0.4; 4 drains, all on 9.0.4; a trace counts when its job's manifest names the Helmgart map, `battle_preset_wh2_dlc13_minor_settlement_empire_fort`): no reading showed the tickets below 1,000 while only c7, c8 or c9 was attacker-held (c7, by its position, was in 13 of the 23); 19 of the 23 kept 1 Hz replay frames, and none of those frames showed it either. In all 4 drains' replay frames the first drop came 0 to 1.2 s after c1's first enemy reading. In the fourth (`bench-b13-v1c-siege-flankers-kimi-20261016`) the trace jumps from 643.9 to 659.0 s; its replay frames read c1 enemy-held at 649.0 s and the tickets first at 990 at 650.2 s. The records cannot tell c1 alone from c1 plus supply points, since c1 fell after at least two of them each time, and the attack side is unread. Go/no-go: no player unit reads `on_wall` in two attempts by both unit types stops the battle; a unit at wall-top height whose `on_wall` stays false is a getter fault and goes back to the interface | `besiege` sent as a move to the piece centre (no `on_wall`, as in the smoke) and `attack_building` sent to the same index of another list (gate hp unchanged): both planted offline and caught. Built since: `siege_order_acted_on` reads the recorded Altdorf crew, whose ram stood 327 m short of the gate at 190 s, the test's last frame, and 263 m short when the record ends at 240 s, as acted on, and a reader keyed on the ram within 15 m of the gate within 180 s fails that test |
| 4 | Information boundary | Built: the declaration test (no withheld word outside the list; `bench-izmail-r1` and `escalade-r1` refused), the Lua tests (climbing never shown, a hidden enemy's `on_wall` absent, unbuilt enemy slots absent) and the job-rename check in `assert_ablation`; the review's one-off script found the LLM request and all 7 arms' orders unchanged when `evaluation`, `setup`, `native` and `final` changed. To build: the rendered prompt and `play.public` view from this battle's recorded stage 1 first observation (question 4 answered 2026-11-09). Until the 2026-11-09 fix for the second look's seat-1 and seat-2, the boundary broke in two ways: `mode.slots`, which the mod reads in every battle, listed the defender's eight tower slots with their build timers (the attack smoke's slot list), and an accepted `besiege` or `attack_building` rendered in the `llm` prompt as "no order", which the system prompt defines as standing until ordered. The mod now leaves `mode.slots` out of a siege the player attacks, and the v23 prompt shows the unit's last siege order; both offline only | No `evaluation`, `setup`, `native`, `final`, climbing or private-record field in any controller input; enemy `on_wall` only on visible enemies; enemy structures only once finished; no withheld word, group label or staging point | A hidden enemy's `on_wall` and an unbuilt slot listed (both planted offline and caught); "izmail" in the job name (built test) |
| 5 | Shortcuts | C1 `hold`, C2 `rush_nearest` and `attack_nearest`, C3 `BesiegeNearest`, C4 `ShootOnly`, C5 `GateOnly`: one fresh launch each on the frozen version | Reported only; a win is kept and narrows the label. A control counts only if it carried out its play (C3: at least one `on_wall`; C4: at least half its ammunition spent; C5: the ram within 15 m of the gate, which a working ram may never meet: the recorded one stopped 33 m from the gate's centre, marker Gate anchor below). A C1 or C3 win sends the battle to a harder step before any gate | A control that never carried out its play must read "not carried out" in place of a loss (the reading is not built) |
| 6 | Witness gate | `Escalade` at 5 s added age and a 5 s interval, frozen code, fresh launches; development launches never count | At least 4 of 5, stopping at the 4th win or the 2nd loss. It passes a 50% witness 0.1875 of the time and fails an 80% one 0.263 (`exact_stats.gate_pass`). Then 5 launches at 10 s / 10 s, reported only | A win credited to a timing the witness did not play |
| 7 | D1 exercised and relevant, the one primary contrast | `Escalade` against `Concentrate`, n separate fresh launches per arm fixed in advance (10 in the design), 5 s / 5 s, order drawn in blocks | Exercised: in at least 6 of 10 `Concentrate` launches (10 of 16 at 16 per arm, marker Exercised at 16 below), at least 2 enemy units that stood more than 150 m along x outside an assaulted sector at the end of staging are flagged in melee inside it within 120 s of our first `on_wall` (`reallocation` over private frames from the end of staging; the reading over frames from the battle's start is reported beside it). The 6-of-10 rule passes a 50% rate 0.377 of the time and a 40% one 0.166, and fails an 80% one 0.033. Relevant: two-sided Fisher p < 0.05 (`fisher`), Newcombe interval (`newcombe`), a disposition table for every planned launch that gives each arm's per-group `phase2_ms` and its `phase2_reason` (staged or time) from the metadata, every launch counted. An unexercised D1 never carries the label; a relevant but unexercised D1 reads "mechanism not shown" | A proximity detector (planted offline and caught on two observations copied from the smoke, at 5.3 s and 714.5 s, the second holding 2 of its 6 friendly-enemy pairs within 40 m, none flagged); analysis code that drops a launch, counts a rematch, or reports a one-sided or Wald result |
| 8 | Human win | `uv run --locked python -m twwarhammer3.battle.manual_demo record --scenario ksl-emp-siege-a-v1 --output DIR --ffmpeg FFMPEG --timeout SECONDS --start-reference HOLD1 --start-reference HOLD2`, with one `--start-reference` for each of stage 1's two `hold` episode folders; the recorder runs the same lobby steps, copies the private record and refuses a withheld word in the output name; its handover is unverified. The engine places both armies and the owner plays through deployment, so the owner starts the battle without moving any unit, and `manifest.start_check` compares both armies' first private-record positions with every hold's | One engine win; every attempt kept; pauses labelled from video; an attempt counts only if `manifest.start_check.label` reads `same start`, and one that reads `own deployment` or `start not comparable` is kept and does not count (marker Demo start label below) | A recording whose equipment readback failed must be refused. Built and caught offline (`test_wh3_manual_demo.py`): one enemy unit 40 m off read as the same start; one hold, or holds 30 m apart, read as comparable |

JUDGEMENT?: Demo start label — Claude, 2026-11-09 (second look ER6): only `same start` counts
toward check 8. Counting `start not comparable`, with a video label that no unit moved during
deployment, would admit attempts when holds are missing or vary; check 8's count rests on it.

The start check's 25 m and its comparison with every hold rest on JUDGEMENT?
src/twwarhammer3/battle/manual_demo.py Demo start limit and Every hold a reference. It has not run
live. Whether both armies' engine starts repeat within 25 m is unknown until stage 1, and whether
the enemy AI deploys the same way after the owner's deployment phase is unread; if it does not, an
attempt reads `own deployment` although the owner moved nothing.

JUDGEMENT?: Gate anchor — Claude, 2026-11-09 (proposed, owner question 6; second look ER5): 3(b)
and C5 read door hp falling or the ram within 15 m of the recorded stop near (-2,-30). The current
15 m of g1's centre fails the recorded ram; check 3(b) and C5's carried-out reading rest on it.

JUDGEMENT?: Check 3 split — Claude, 2026-11-09 (proposed, owner question 6; second look ER5):
check 3 splits into acted on (the go/no-go; it misses a gun firing in place, below) and outcomes
with no window. Outcomes in windows, as now, can stop working orders; stage 2's verdict rests on it.

Acted on is `siege_order_acted_on`, and a gun that fires from where it stands never comes 50 m
nearer and never climbs, so it reads not acted on. In `helmgart-defender` the AI side's Great
Cannon, ordered `attack_building` on the gate at 10 s, stood about 339 m from the gate throughout,
its ammunition fell from 66 to 60 and the gate building's hit points from 18,000 to 12,720 by 80 s,
and the reader returns not acted on for it (rerun for this page). Under the split as written, a
Grom firing on g1 as 3(c) expects would fail the go/no-go. The go/no-go could cover `besiege`
only, or acted on could also count an `attack_building` whose unit's ammunition falls within 60 s
(the private record carries `ammo`); the choice is the owner's, in question 6(d).

Check 3 under the split, an option for question 6(d) that is not in force (it rests on JUDGEMENT?
Check 3 split and Gate anchor above), would read as follows. The go/no-go is acted on: each
accepted `besiege` is read by `siege_order_acted_on` (its unit 50 m nearer the target within 60 s,
or reading climbing within 120 s), and no wall `besiege` acted on in two attempts by both unit
types stops the battle. The Grom's `attack_building` counts as the owner picks in 6(d): left out of
the go/no-go, or acted on once its unit's ammunition falls within 60 s, which the reader does not
read yet. The outcomes are reported, each with its time and no pass window: (a) each climber's
first `on_wall`, with y against the wall-top height; (b) the door, read as the first value below
100 and the first at 0 of the public gate nearest g1, with the ram's closest approach to the
recorded stop near (-2,-30); (c) g1's building hp and the Grom's ammunition over time, and whether
the building reaches 0 when the door does; (d) Streltsi fire and the target's men; (e) the first
melee on the wall; (f) the ticket reading as now. A unit at wall-top height whose `on_wall` stays
false still goes back to the interface. It must fail on a reader keyed on the ram within 15 m of
the gate within 180 s (built: that reader fails the Altdorf crew test) and on check 3's two plants.

Two more 20 m values sit on g1's centre: `escalade_readings.GATE_M`, within which a unit coming
inside counts as a gate entry, and `CavalryEarly`'s ride to 20 m south of g1 (`GATE_FRONT_M`).
Both are re-checked against the recorded 33 m offset once stage 1 reads g1's `central_position`
(check 2).

If the witness fails check 6, no round runs. The version then steps down one factor (see the
ladder below) or is revised, and the new version gets a gate on fresh launches; an unchanged gate is
never rerun until it passes
([guideline 2.7](evaluation-guidelines.md#27-admit-a-card-only-from-a-frozen-confirmation-round)).
If stage 2's go/no-go stops the battle, the page reports that the escalade does not adapt with the
current engine access, and a version with a `ksl_siege_tower_15m` becomes a new design with its own
decisions.

Exact power of check 7's relevance test, from `plan_power`
([guideline 7.4](evaluation-guidelines.md#74-decide-before-you-look)), computed for this page:

| Launches per arm | 0% → 50% | 10% → 60% | 20% → 70% | 10% → 80% | Wins needed for p < 0.05 against 0, 1, 2, 3, 4 |
|---|---|---|---|---|---|
| 10 | 0.623 | 0.474 | 0.426 | 0.841 | 5, 7, 8, 9, 10 |
| 16 | 0.962 | 0.786 | 0.740 | 0.986 | 5, 7, 9, 10, 11 |

With 10 per arm a moderate effect will probably stay unresolved. The contrast holds only for the
version the witness's ladder picks, and the page says so with any result. The
[overview's grid](historical-evals.md#method-rules-the-set-shares) gives the power at witness
rates of 0.7-0.9, nearer what a gated witness wins: at 16 per arm a 30-point drop is found
0.269-0.359 of the time.

Check 7's exercised rule at 16 per arm is 10 of 16 `Concentrate` launches, the share of 6 of 10.
It passes a 50% rate 0.227 of the time and a 40% one 0.058, and fails a 70% rate 0.175 and an 80%
one 0.027 of the time (binomial tails, computed for this page). With the relevance test's 0.740 at
20% → 70%, a label needs both.

JUDGEMENT?: Exercised at 16 — Claude, 2026-11-09 (second look S1, C1): 10 of 16 Concentrate
launches, the 6-of-10 share. 9 of 16 passes a 50% rate 0.402 of the time and 11 of 16 fails an 80%
one 0.082; D1's exercised label at 16 per arm rests on it.

JUDGEMENT: Escalade ladder — Claude, 2026-11-08 (design): garrison rank 2, one more Handgunners,
one fewer Armoured Kossars, modifier 1.1, in that order; easing removes the Mortar, then one
Handgunners. Another order may freeze another version; the frozen difficulty rests on it.

The difficulty ladder follows
[guideline 2.6](evaluation-guidelines.md#26-set-difficulty-with-the-witness-and-foils-never-with-the-compared-models):
one factor per step, each a new version with its reason written before launch, never tuned on
model results. Each step runs 5 witness launches at the 4-of-5 rule plus one launch each of C1, C3
and `Concentrate`, and re-reads the reallocation readings, because a rank or roster step can
change how fast defenders move. The first step the witness fails stops the ladder, and the step
before it is frozen.

## Live stages

Stages 0 to 5 cost $0 in API calls; stage 6 is paid. Every live stage waits for a window the owner
names and runs one battle at a time. Every automated stage keeps the battle unpaused at 1x; in
stage 4 only the owner may pause, as the owner's 2026-11-04 rule allows while demonstrating that
a scenario can be won. Times use the design's estimate of 20-25 minutes for a launch that runs to
the 1,200 s timer (the timer plus loading and setup), and each range is that estimate times the
launch count. No siege has reached its timer, so no recorded launch gives the Helmgart figure, and
battles that end earlier take less.

| Stage | What runs | Launches and time | What it can show |
|---|---|---|---|
| 0 (done offline) | Declaration, interface, private record, `escalade.py`, `escalade_readings.py`, tests; `check.py` passed at `f3fec92` (3585 passed, 70 skipped, by its commit message) | Done | The code does what its tests say |
| 0b (offline) | Still to build: the stage 2 probe script, the carried-out readings for C3-C5, the check 2 comparison with the engine's fort lists, the rendered-prompt boundary test on a recorded first observation (`test_wh3_eval_boundary.py` runs it on the attack fixture's), the plan builder | No game | Inputs for checks 2, 3, 4, 5 and 7 |
| L | The set's lobby-only readback (check 0), one game session with no battle | Minutes | Whether the Winged Lancers and a ksl ram in the player's slot recruit, before any launch |
| 1 | 2 `hold` launches | 40-50 min | Checks 1 and 2; both engine starts and whether they repeat within 25 m per unit; `can_climb` and `can_siege` per unit; which unit crews the ram; enemy builds; visibility at 5 s; `sample_cpu_ms`; the hold result (C1) |
| 2 | The order-effect probe | 2-3 launches, 40-75 min | Check 3, with which holdings drain the defender's tickets (c7 alone as the control, then c1), and the climb go/no-go |
| 3a | Shortcuts C2-C5, with C2's two scripts one launch each as check 5 gives them (C1 reuses stage 1 if the code is unchanged; the design's stage 3a counted `rush_nearest` only) | 5-6 launches, 1.7-2.5 h | Check 5 |
| 3b | Up to 6 witness development launches (never counted), the frozen gate, then 5 launches at 10 s / 10 s | Up to 16 launches, 5.3-6.7 h | Check 6 |
| 3c | The ladder, only after a gate passes: per step 5 witness launches plus C1, C3 and `Concentrate` once each, at most 4 steps | 8 launches per step, 2.7-3.3 h per step | The hardest step the witness still wins, with the reallocation readings re-measured |
| 4 | The owner's manual demonstration (check 8) | The owner's time | Human-demonstrated winnability |
| 5 | The D1 round (check 7), only if the owner names it | 10 per arm: 20 launches, 6.7-8.3 h; 16 per arm: 32 launches, 10.7-13.3 h | The primary contrast |
| 6 | A model pilot, if wanted: `llm_rules`, or `llm` reported as a tips arm, as [set rule 7](historical-evals.md#method-rules-the-set-shares) proposes (the marker below). The owner's approval of "models using siege orders" (question 4, 2026-11-09) lets both read the orders and chooses no arms | Paid; the owner's budget and arms | Exploratory model results; no ranking |

JUDGEMENT?: Izmail pilot arms — Claude, 2026-11-09 (second look seat-3): a stage 6 pilot runs
llm_rules, or reports an llm result as a tips arm, as set rule 7 (Pilot prompt) does. Reading llm
as a plain model arm credits How to fight's lines 30 and 34 to it; stage 6's readings rest on it.

Through stage 3b that is about 25-27 launches and 8.3-11.3 hours of game time before any ladder
step or round. The design's stage 4 had 30 launches with `CavalryEarly` as a third arm; with D2
descriptive the round has two arms.

## Risks

| Risk | Stage that shows it | Response |
|---|---|---|
| The player's units cannot climb, or rout on the approach (the one player-side wall besieger in the 2026-11-03 Altdorf checkpoint battle lost 29 of 90 men and routed at about 125 s before it reached the wall, by the design's reading) | 2 | The go/no-go stops the battle, or a siege-tower version as a new design; never tuned silently |
| `is_on_top_of_wall` or `can_climb_walls` reads wrong or not at all | 1-2 | Compare with the private record's y; a getter fault goes back to the interface |
| A gate building's `health()` does not follow its door: `mode.gates` reads 0 while g1 stays above 0% | 2 | The Horse is still released on `mode.gates`; the crew and the Grom keep ordering g1, which validation accepts; record it and decide the rule. Version 2 keys the crew and the Grom on the door (question 6(b)) |
| Tower owners read swapped (`alliance_owner_id` against a one-based `local_alliance`) | 1 | Check 2 compares them with the Fort Tower capture holders |
| Vehicle ids change as vehicles fall, or an uncrewed ram leaves the view | 1-2 | Record it; the crew binding happens once, at the first observation |
| A building is both a wall piece and a tower and gets two ids | 1 | Check 2 reports it; dedupe as a new version |
| The front line, the ±60 m sectors, the recess pieces or the 40 m staging spacing do not fit the real pieces | 1 | A new version with the rules re-marked; the fixture's pieces are a sketch |
| Dozens of wall pieces bloat the observation | 1 | Group the pieces between Fort Tower points into sections, as a new version |
| The engine's attacker start varies between launches | 1 | Author the start with `deployment` and read it back, once [Haengju](haengju-eval.md)'s stage 1 shows whether teleport works in a siege |
| Winged Lancers or the ksl ram do not recruit | L | Horse Raiders (`wh3_main_ksl_cav_horse_raiders_0`, recruited in `ksl-raiders-emp-halberds`) for the Lancers, as a new version; a ram that does not recruit goes to the owner |
| The Grom or the ram makes the gate trivial (C5 wins) | 3a | Remove one, as a new version with a stated reason |
| Missile attrition wins (C4) | 3a | Fewer bows, one step at a time; keep the win |
| The garrison never shifts, so D1 is not exercised; or it shifts only toward the army's approach | 3b-5 | Report it; never tune toward reallocation |
| Ticket drain decides the battle, or holding Fort Tower points alone wins | 2, 3a | Keep the win and narrow the label |
| A siege timer win has never been observed: none of the 22 siege rows in the register ended at its timer, so a timeout loss assumes `ended_by` reads `time_limit` in a siege | 1 | Record the first one; 1,200 s may also be too short for any winning plan, which goes to the owner as a 2,400 s question |
| The defender builds towers that dominate | 1, 3a | `mode.enemy_structures` shows them; report |
| The private record costs too much CPU per second for 25 units | 1 | Read `sample_cpu_ms`, already recorded |
| Lua and observation changes split evidence; new fields change prompt snapshots | 0 | One logged version; snapshots regenerated only for an intended change |
| Recognition: Kislev attacking an Empire fort hints at Russia | None | Neutral names and withheld words; nothing measures it |

## Variation

The first version is one fixed battle for development. Later candidates, each a new version or a
new design: Altdorf's six gates; a siege-tower version if stage 2 stops the battle; wall sections
if the observation is too large; authored starts if the engine's vary; and the P2 wing-captain team
version, only with the owner's yes and only after the single-controller battle is frozen. Helmgart
already hosts the `chd-reserve-grn-siege` family, `coord-siege` and Haengju, and the owner has not
chosen a reservation policy, so every inspected variant is development evidence. Before stage 5, a
frozen experiment card gives the arms, launches, stop rule, budget and analysis, as the
[Cannae run plan](cannae-eval.md#variation-and-the-eventual-run-plan) does.

## Decisions for owner review

Six questions, with the recommendation first. The build at `f3fec92` took the recommended answer
to questions 1-3; the owner answered question 4 on 2026-11-09; nothing in any plan depends on
questions 5 and 6, and question 6's options are built beside version 1 without replacing it.

1. **Whether Izmail counts.** Its disadvantage is the fortress, and its numbers are contested:
   31,000 against 35,000 on the official count, and about two to one for the attacker on
   Osipovsky's and Gladky's. (a) Build it with that caveat on the page (recommended; built): it is
   the only candidate in which the controller attacks a fortress, and WH3's siege rules set its
   problem with no enemy script. (b) Drop it as not meeting "one side had a clear disadvantage".
2. **Pairing and roster.** (a) Kislev attacking an Empire garrison, with a Boyar and the re-planned
   roster with fewer bows (recommended; built): five Armoured Kossars, three Kossars (Spears), two
   Streltsi, the Winged Lancers and the Little Grom. (b) An Empire attacker with melee climbers and
   the Empire siege equipment the 2026-11-03 checkpoint battles used. (c) The design's first Kislev
   roster with four Kossars (Spears) and two Kossars (6 × 20 arrows), which makes missile attrition
   a stronger shortcut.
3. **What the policy sees of the siege.** (a) The wall pieces and towers with their health, its own
   units' `on_wall`, the `on_wall` of visible enemies, its ram's crew, and enemy towers and
   barricades once built (recommended; built, marked as Siege attack fields in `mailbox.py`): a
   player sees all of these on screen. (b) The same without wall and tower health and without
   enemy-built structures, which may hide what the owner's demonstration shows. The fields exist
   only behind the opt-in, so Haengju's observation does not change either way.
4. **When a model may use the siege orders.** (a) Keep the `llm.py` change parked on
   `izmail-llm-orders` until stage 2's climb go/no-go passes, then merge it as its own logged
   version (recommended): no model arm is planned before stage 6, and a battle that cannot adapt
   would never cost the card split. (b) Merge it now, with the Lua batch that already moves every
   card cell's setup identity, so the source split lands at the same time. Either way, the
   `commander`, `team` and `local_team` schemas lack the siege orders, while the parked change's
   shared prompt rendering would show them the fort; a team arm needs that work too.
   **Answered 2026-11-09:** "I approve models using siege orders"
   ([directions](../owner-direction.md)). The change landed as v23, before stage 2, with the order
   paragraph kept out of the `commander`'s and team members' prompts (marker Team siege orders).
5. **How check 7 runs, once the gate passes.** (a) 16 separate fresh launches per arm at 5 s / 5 s
   (recommended): 32 launches, 10.7-13.3 h, power 0.74 for a 20% → 70% gain; the exercised count
   becomes 10 of 16 `Concentrate` launches (marker Exercised at 16). (b) 10 per arm, the design's
   count: 20 launches, 6.7-8.3 h, power 0.43 for the same gain. (c) Branches restored from one
   checkpoint, compared with exact McNemar (`exact_stats.mcnemar`). A shared checkpoint at the end
   of staging cannot exist here, because the arms stage in different places (each group 150 m
   south of its own target: `Escalade._bind`, `Concentrate.target_points`). A branch at the start
   shares only the engine's randomness, and the register's rematches show no sign of a gain from
   that (the second look's S5, which pooled rematches across unrelated scenarios). It would also
   need a declared checkpoint case for a player attack on Helmgart, and whether the fort ids and
   the controllers' bound groups survive a restore is unknown.
6. **Witness version 2, before any gate** (the second look's owner question 2, 2026-11-09). One new
   witness version, from the parts the owner approves. All four parts are built as options beside
   version 1, which stays the default ([version 2 options](#witness-version-2-options); check 3's
   split as text after the markers). (a) Phase 3 goes from c7 straight to c1 and drops the c8/c9
   tier, on check 3(f)'s recorded rule, whose attack side is unread. (b) g1 counts as fallen once
   the door nearest it reads hp 0, as the Horse's release already does: in `helmgart-defender` the
   door's hit points read 0 from 120 s while the gatehouse building's read 3,061 to 423 until 150 s,
   and the crew and the Grom key on the building. As built, a unit still on a g1 order then gets one
   halt, since a standing `attack_building` kept firing until the building read 0 in that recording;
   whether a halt ends one is unread ([version 2 options](#witness-version-2-options)).
   (c) Concentrate's flank groups stage at Escalade's standoff, at least 150 m from every listed
   piece and at least 40 m from Centre's spots, each arm keeping a 150 m approach
   ([the decision](#the-decision)). As built on the fixture, each flank group's nearest spot stands
   150 m from a piece in both arms, but four of `ConcentrateV2`'s six flank spots stand 11-23 m
   farther than Escalade's, and its flanks walk 188-194 m against `EscaladeV2`'s 156-161 m. (d)
   Check 3 splits into acted on, the go/no-go, and outcomes reported with no time window, with 3(b)
   anchored on the door (markers Gate anchor and Check 3 split). As built, acted on reads a gun that
   fires from where it stands as not acted on, so the Grom in 3(c) would fail that go/no-go. Either
   the go/no-go covers `besiege` only, or acted on also counts an `attack_building` whose unit's
   ammunition falls within 60 s; the paragraph after the markers gives the recorded cannon. The
   second look recommends yes to all four. Each changes the witness, a control or a check, so
   evidence from the current version would not carry over.

Other open choices: the markers on this page, in `escalade.py`, `escalade_readings.py`,
`mailbox.py`, `setup.py`, `capture.py` and `test_wh3_siege_assault.py`; the 1,200 s timer against
2,400 s; whether the battle keeps its two lords; which stages may start; and any budget for stage 6.

## Sources

The historical account guides the design and is no evidence about the engine.

- Wikipedia, [Siege of Izmail](https://en.wikipedia.org/wiki/Siege_of_Izmail), fetched for the
  design on 2026-11-08 (characters 0-100,000 of 118,235). Secondary. Strengths and their
  attributions, the infobox figures, "only 40 field guns, but no siege guns at all", the [citation
  needed] tag on the walls, the replica training, the signals, the three wings and Westphalen's
  cavalry, Lassi first, the Tabia, the gates open by 8 a.m., the cavalry kept out, the 20 light
  guns, Qaplan Giray's counterattack and the losses with their attributions.
- Wikipedia (Russian), [Штурм Измаила](https://ru.wikipedia.org/wiki/Штурм_Измаила), fetched for
  the design on 2026-11-08 through a translation. Secondary. The 31,000 (16,000 regular, 15,000
  irregular), the garrison of 35,000, the guns taken, the ditch of 3-5 sazhens, Suvorov's verdict,
  the signal rocket, Meknob's ladders, Kutuzov's request and the grenadier battalion, the deserters,
  Markov's column at the Tabia, and Orlov's 1890 losses.
- [Измаил](https://ru.wikisource.org/wiki/ВЭ/ВТ/Измаил), Sytin's Military Encyclopedia, volume
  10, on Wikisource, fetched for the design on 2026-11-08. Pre-revolutionary encyclopedia. The wall,
  rampart and ditch, the four gates, the 260 guns, the garrison of about 35,000, the 25,000-30,000
  Russians, the bombardment, the three detachments of three columns, the rockets, the Bender-gate
  sortie, the cavalry entering after the gates opened, the end at about 4 p.m. and the losses.
- S. N. Osipovsky, "Штурм Измаила в 1790 году А. В. Суворовым: противоречия в оценках численности
  гарнизона и потерь турок", Манускрипт 19(2), 2026, doi:10.30853/mns20260095; abstract from
  [gramota.net](https://www.gramota.net/en/article/mns20260095/fulltext) and full text from
  [manuscript-journal.ru](https://manuscript-journal.ru/article/mns20260095/pdf), read for the
  design on 2026-11-08. Peer-reviewed. Suvorov's 35,000 armed and rations for 42,000, Gladky's
  10,000-15,000, the conclusion of at most 20,000 armed defenders, and at most 15,000 Ottoman dead.
- Not fetched, so nothing here rests on them directly: Duffy, Orlov (1890), Gladky (1993), Grant,
  Bodart and Arsenyev.
- Creative Assembly's battle-script documentation under `runs/twwarhammer3/vanilla/` (ignored by
  Git): `battle_unitcontroller.html` (`besiege_building`, `attack_building`), `battle_unit.html`
  (`can_climb_walls`, `is_on_top_of_wall`, `is_climbing_ladder`, `is_in_melee`, the `can_siege`
  attribute), `battle_building.html` (`central_position`, `position`, `health`,
  `alliance_owner_id`), `ai_planner.html` (AI planners are not recommended in sieges, so no AI
  planner reference arm), and `lib_battle_manager.lua`, which adds gates to the wall list.
- Game database, read-only with `scripts/wh3_db.py` and RPFM's `schema_wh3.ron` on 2026-11-09 for
  this page: `main_units_tables` (costs, men, `can_siege`), `land_units_tables` (weapons,
  ammunition, armour, morale), `missile_weapons_tables` and `projectiles_tables` (ranges, whether a
  projectile can damage buildings). The design read the same tables and
  `battlefield_siege_vehicles_custom_battles_tables` (equipment caps) on 2026-11-08.
- Recorded evidence, ignored by Git. Under `runs/twwarhammer3/battle/`:
  `smoke-siege-attack-kho5-dwf5-probe_abilities-20261014-0830` (first observation, defender
  positions and objective text reread for this page),
  `smoke-siege-kho5-dwf5-attack_nearest-20261014-0132`,
  `smoke-settlement-kho5-dwf5-attack_nearest-20261014-0214`,
  `smoke-random-siege-skills-20261014-0511`, `bench-b12-siege-baselines-20261016` and
  `bench-b12-m1-kislev-20261016`. Under `runs/twwarhammer3/`: `siege-905-20261103` (the Helmgart
  and Altdorf checkpoint cases). All as the design and the review read them unless this page says
  it reread them; the register [results.csv](results.csv).
- Design and build records, ignored by Git: `runs/siege-evals-20261108/final-izmail.md`,
  `portfolio.md` (overlaps, shared rules and the Izmail corrections applied here: D1 the only
  claim, D2 descriptive, hp 0 or less everywhere, the shared private record in place of the
  design's `evaluation` field) and `lua-batch.json` (L3: card, plants, review and fixes), and
  `runs/siege-evals-20261108/parked/` with the parked `llm.py` patch.
