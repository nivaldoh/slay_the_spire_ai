# Camp attack evaluation after Belgrade, 1456

Development candidate, 2026-11-08 (Claude). **Nothing here has been launched or measured, and
everything is unverified.** The owner's direction of 2026-11-08 was "Build now, game when I say"
([owner direction](../owner-direction.md)), so the scenario `emp-chd-camp-v1`, its witness and its
controls were built offline at `e918091`, and no game window has been named. The battle adapts the
sortie on the Ottoman gun camp outside Belgrade on 22 July 1456 as a WH3 Land battle in which the
controller attacks. Its levies start fighting on the camp's flank at once, and its mounted group
then chooses between the war machines and the cavalry that left them to fight the levies. The
owner's choices are collected in [decisions for owner review](#decisions-for-owner-review).

The page follows the [scenario guidelines](scenario-guidelines.md), the
[evaluation guidelines](evaluation-guidelines.md) and the [benchmark contract](benchmark.md):
fixed armies, public structured observations, permitted orders, every engine win counts, and
automated play runs unpaused at 1x. It applies the rules that Claude's 2026-11-08 review of the
five siege designs proposed for the whole set, none of them agreed with the owner: one primary
contrast per battle, a frozen witness gate before any round, exact power printed in advance, and
engine melee flags for contact. The design and that
review are `runs/siege-evals-20261108/final-belgrade.md` and `portfolio.md`, which Git ignores.
Under the [hard rule](../../AGENTS.md#verification-hard-rule), everything below is unverified.

## The historical battle

The account below rests on two secondary sources fetched for the design on 2026-11-08: the English
Wikipedia article (its first 100,000 characters) and the Hungarian one, read through a
translation. The English account of both nights carries no citation marker. Kovach (HistoryNet),
Mixson (2022) and Britannica were not fetched; nothing here rests on them, except a sentence the
English article cites to Mixson. This page did not fetch the articles again.

In July 1456 Mehmed II's army was besieging Belgrade, and a river battle was fought on 14 July. On
21 July Mehmed launched "an all-out assault that began at sundown and continued all night" (English
article, uncited). The two articles disagree on how the defenders won that night. The English one
says burning tar "separated the Janissaries fighting in the city from their fellow soldiers". The
Hungarian one says the defenders "were forced to give up the town" and that Hunyadi's cavalry struck
the Janissaries in the castle's inner courtyard "when the reinforcement appeared in the Turks'
rear".

On 22 July, by the English article's uncited account, "some of the units crept out from
demolished ramparts"; its reference 30 (Mixson) says instead that "The sultan ordered a feigned
retreat". Capistrano was soon "surrounded by about 2,000 peasant levymen", and "Ottoman Sipahis
tried without success to disperse the harassing force". The Hungarian article has five crusader
archers (íjász) shooting at the Anatolian corps and a sipahi unit sent to remove
them, which drew more crusaders out. It then says the Rumelian cavalry was thrown against the
crusaders and "by pulling his cavalry away, he left the Ottoman artillery unprotected"; Hunyadi
"with a sweeping attack ... seized the Ottoman gun positions". The Ottomans left on the night of
22-23 July (English article, reference 28). Mehmed was wounded; the Hungarian article says by an
arrow in the thigh.

Forces disagree across and within the two pages. The garrison was 5,000-7,000 (both). Hunyadi
brought 12,000 (English, reference 17), or about 10,000 plus 2,000 at Szeged (Hungarian). The
crusaders were about 25,000, including about 18,000 inexperienced peasants (reference 17),
30,000-35,000 (Hungarian text) or 30,000-60,000 (English infobox). The Ottoman army was
60,000-70,000 "according to newer research" (reference 24), about 40,000 regulars and 30,000
irregulars (Hungarian), or 30,000, 60,000 or 100,000 (English infobox), with 300 cannons.

The size of the disadvantage depends on the phase. The garrison alone was outnumbered several
times over by every modern Ottoman estimate. After the relief, the Christian count reaches the
lower Ottoman figures:
the English article says Hunyadi built "a force of 25–30,000", and the Hungarian one puts the
defenders "above 20 000" against about 40,000 regulars and 30,000 irregulars. The disadvantage that
lasted was in guns and troop quality: 300 Ottoman cannons, and crusaders "some of them carrying
only clubs and slings" (English, reference 17). What decided 22 July, in the Hungarian account, was
that the Ottoman cavalry left the guns to fight the levies and Hunyadi's attack took the guns. In
the English account the levies' fight began without orders, so the credit for tactics belongs to
how Hunyadi followed it. The battle therefore fits the owner's request for a disadvantaged side
that won by tactics only in part.

In the WH3 version the enemy costs 1.37 times as much (9,200 against 6,700 by database cost), holds
every gun, outranges every player unit and wins if the timer runs out; the player has 1.26 times as
many men at large scale (587 against 466). Whether that adds up to a disadvantage in play is
unmeasured.

## Why this WH3 game mode

The owner's answer on 2026-11-08 was "We can try to build those sieges but let's make sure we're
adapting them well to WH3's game modes". Belgrade has three decisive actions, and only one of them
adapts well.

| Action | WH3 mode | Verdict |
|---|---|---|
| 14 July river battle | None; WH3 has no naval battle | Does not adapt |
| 21-22 July, the break-in | Siege, the controller defends | Does not adapt well (four reasons below) |
| 22 July, the sortie on the guns | Land, the controller attacks a native AI defender | Built as `emp-chd-camp-v1` |

The siege defence was rejected for four reasons, all from the design's review:

1. Its premise is that native AI attackers enter a few at a time, and the recorded no-defence
   baselines contradict it. The design recounted `bench-b12-siege-baselines-20261016` on Helmgart,
   counting visible enemy regiment centres north of z = -10. Under `hold` (episode-0001) 1 regiment
   was inside at 208.0 s, 5 at 227.2 s and 6 of 16 at 242.8 s; under `attack_nearest`
   (episode-0000) the same counts came at 181.9, 208.6 and 221.5 s. Regiment centres can jump
   between squads, so the 19-27 s from the first to the fifth is approximate. That is one battle
   per policy, and it does not change the verdict.
2. It would repeat [Haengju](haengju-eval.md)'s breach decision and the brief of
   `chd-reserve-grn-siege` ("committing one mobile reserve and limited construction supplies") in
   the same mode and role.
3. WH3 has nothing like the burning tar, which only the uncited English account gives, and
   captured guns cannot be turned on their owners.
4. A siege defender wins at the timer, so a sortie on the guns would be optional. When the design
   was reviewed, enemy ammunition was also recorded nowhere: the battle Lua's `unit_record` sets
   `ammo` only for the player's units, and the replay keeps enemies only while they are visible.
   The evaluator-only record built at `f3fec92` now holds it for a scenario that opts in, so only
   the first half of this reason stands.

The 22 July action fits a Land attack for these reasons, each with what it rests on:

- The defender wins at the timer, so the camp has to be broken. A `hold` attacker lost at the
  timer at 1,205 s in pilot-r4, where no unit of either army moved
  ([log](log.md#2026-11-02-mirror-version3-the-enemy-gets-a-great-cannon-and-attacks)), and in two
  `brt-cavalry-emp-assault` register rows (one recorded `ended_by` time_limit).
- The defender's war machines outrange everything the player fields. The database gives the
  Magma Cannon 380 m and the Deathshrieker 420 m effective range; the player's only missile unit,
  the Free Company, carries pistols with 90 m range (`projectiles_tables`) and 18 shots
  (`land_units_tables` `primary_ammo`), both read 2026-11-08.
- Native AI defenders react to attackers who come close, so the cover leaving the guns would be the
  engine's own behaviour. The design's recount of one battle supports this:
  `bench-b9-assault-medium-ai10-20261014` episode-0000 (`rush_nearest` against an Empire defender
  with a Great Cannon), where no enemy unit moved more than 2 m until our cavalry was 63-128 m away
  at 66.8 s, and the cannon never moved in 206 s. `coord-pincer` counts against it: its native
  Greenskin block charged groups that started 132-279 m away (the design's reading of two traces),
  and the block split in all five battles
  ([log](log.md#2026-11-04-suite-page-rebuilt-around-who-coordinates-with-whom)). Check 2
  decides whether the guns stay and fire. Check 3 and the stage 1 readings of how the cover reacts
  decide whether the cover leaves them to fight the levies.
- Authored placement reads back in Land battles: in `round-1a`, six launches with one battle each,
  every authored unit stood within 8.4 m of its place
  ([log](log.md#2026-11-04-authored-starts-work-live-two-battles-recalibrated)); that is no agreed
  check.

The adaptation drops the fortress, the river, the night, the relief's arrival, captured guns turned
on their owners, and the fact that nobody ordered the levies' attack. Here the controller commands
the levies. To bring the history closer, the Priest and Flagellants start 77-183 m from the
Cutthroats on the camp's west flank, so their fight begins at once and the controller's real
decision is how the mounted group follows it, as Hunyadi's did. A more faithful later version would
make the levies a native AI ally the controller cannot order; it needs a lobby slot on the player's
team, a public `allies` observation and an `allied` deployment, and its results would never pool
with these.

JUDGEMENT: Camp adaptation — Claude, 2026-11-08: Belgrade's 22 July sortie as a Land battle the
player attacks, with no script. The 21 July break-in as a siege defence tests a breach decision
instead; which decision this battle measures rests on it.

## Battle specification

JUDGEMENT: Camp construction profile — Claude, 2026-11-08 (camp design): scenarios.json
emp-chd-camp-v1 player, enemy, map, deployment points and bearings, and expect. Other forces,
timer or rank change the difficulty; every reading of the battle rests on it.

The declaration is `emp-chd-camp-v1` in
[`scenarios.json`](../../configs/twwarhammer3/scenarios.json), `scenario_version` 1, split
`development`, status `prototype_not_admitted`.

| Field | Setting |
|---|---|
| Mode and role | `battle_type` `classic` (engine `land_normal`); `attacker` `player`, `expect.player_defends` false; native AI defender, which wins at the timer |
| Map | Taurox, `battle_preset_qb_wh2_dlc17_taurox_rune_tortured_axes`; bounds ±512 m |
| Factions | Player `wh_main_sc_emp_empire` / `wh_main_emp_empire`; enemy `wh3_dlc23_sc_chd_chaos_dwarfs` / `wh3_dlc23_chd_astragoth` with `recruitment_faction` `wh3_dlc23_chd_legion_of_azgorh`; both with a lord |
| Difficulty and scale | AI `ai_level_very_hard`, stats modifier 1.0, large units (0.75), realism off, rank 0 for every unit |
| Timer and funds | 1,200 s; `funds_custom` 10,000, which both rosters fit by database cost; the lobby charge is unread |
| Loadouts | Default recruitment upgrades; the General's mount `wh_main_emp_cha_general_1`; war-machine upgrades at the lobby defaults, unread |
| Toggles | `behaviour_defaults: true` (fire at will on at the start; the controller may change it) |
| Script | None: no hold, reserve or custom objective |
| Evaluator-only record | `private_record: true`: once per engine second the mod writes every unit of both sides, hidden enemies and enemy ammunition included, to a file no controller reads ([measurements](#measurements)) |
| Public task | Win the battle; any engine win counts, and the timer ending is a loss for the attacker |
| Input and control | The current public observation and orders; automated play unpaused at 1x |
| Exposure and status | Development candidate; no reserved variant, no lobby readback, no agreed check |

JUDGEMENT: Camp loadouts — Claude, 2026-11-08: war-machine upgrades at the lobby defaults, to be
read back. Clearing them weakens the guns and needs a new lobby step; the guns' strength rests
on it.

### Rosters

Costs are `main_units_tables` `multiplayer_cost` and men are its `num_men` times 0.75, both read
from the installed game with `scripts/wh3_db.py` on 2026-11-08; single entities count as 1. No
lobby has read these rosters back, so the charge and the recruited sizes are unverified.

| Player, Empire | Count | Cost | Men | Group in `camp.py` |
|---|---|---|---|---|
| General `wh_main_emp_cha_general_0` with mount `wh_main_emp_cha_general_1` (barded warhorse; the foot card costs 600) | 1 | 850 | 1 | Mounted |
| Empire Knights `wh_main_emp_cav_empire_knights` | 2 | 850 each | 45 each | Mounted |
| Reiksguard `wh_main_emp_cav_reiksguard` | 1 | 1,100 | 45 | Mounted |
| Warrior Priest `wh_main_emp_cha_warrior_priest_0` | 1 | 350 | 1 | Levies |
| Flagellants `wh_dlc04_emp_inf_flagellants_0` (unbreakable) | 3 | 600 each | 90 each | Levies |
| Free Company Militia `wh_dlc04_emp_inf_free_company_militia_0` (pistols, 90 m) | 2 | 450 each | 90 each | Levies |

| Enemy, Chaos Dwarfs | Count | Cost | Men | Role |
|---|---|---|---|---|
| Overseer `wh3_dlc23_chd_cha_overseer` | 1 | 700 | 1 | Lord, in the camp |
| Magma Cannon `wh3_dlc23_chd_veh_magma_cannon` (380 m, minimum 10 m, reload 10 s, 25 shots) | 2 | 1,000 each | 1 each | Guns |
| Deathshrieker `wh3_dlc23_chd_veh_deathshrieker_rocket_launcher` (420 m, minimum 60 m, reload 12 s, 25 shots) | 1 | 1,300 | 1 | Guns |
| Infernal Guard `wh3_dlc23_chd_inf_infernal_guard` | 2 | 950 each | 75 each | Guard in front of the guns |
| Hobgoblin Wolf Raiders `wh3_dlc23_chd_cav_hobgoblin_wolf_raiders_spears` | 2 | 500 each | 45 each | Cover |
| Bull Centaurs `wh3_dlc23_chd_cav_bull_centaurs_axe` | 1 | 1,500 | 12 | Cover |
| Hobgoblin Cutthroats `wh3_dlc23_chd_inf_hobgoblin_cutthroats` | 2 | 400 each | 105 each | West flank, nearest the levies |

The player has 10 units, 6,700 in cost and 587 men; the enemy has 11 units, 9,200 (1.37 times)
and 466 men. Both guns can damage allies (`can_damage_allies`), and the war machines carry 500
bonus hit points and heavy metal armour. 25 shots at the base reload gives each Magma Cannon about
250 s of fire and the Deathshrieker about 300 s. Recorded in earlier traces: the Magma Cannon reads
engine class `missile_chariot`, range 380, speed 1/1.5 m/s and ammo 25; the Bull Centaurs read
class `infantry`; the Wolf Raiders read `cavalry` at 1.9/9.2 m/s; Empire Knights ran at 7.8 m/s
in `gap-initial-02-20261101`. Never recorded in a battle: Flagellants, Free Company, Reiksguard,
Warrior Priest, the General's mount and the Deathshrieker. No scenario has recruited Chaos Dwarf
cards in the AI slot; `emp-battery-skv-evacuation` passes a `recruitment_faction` to an AI slot,
but one equal to its own faction, so it is weak evidence for a different card namespace.

JUDGEMENT: Camp pairing — Claude, 2026-11-08: Empire levies and knights against Chaos Dwarf war
machines. An Empire mirror with Great Cannons, or Kislev against Chaos Dwarfs, changes morale,
gun ranges and ammunition; the rosters and costs above rest on it.

### Map and placements

Axes: x east, z north; bearing 0 faces +z. "Checked" means a point another Taurox scenario declares,
where a unit stood within 8.4 m at the first recorded reading (5.2 s) of a `coord-suite-20261104`
launch. For the `coord-pincer`, `coord-relief` and `coord-rear-raid` points that reading is in
`round-1a`, one launch each, at 1.6-5.2 m. Only version 3 of `coord-two-fronts` declares the two
Cutthroat points, so they were read back in `round-4` to `round-6`, at 2.4-5.3 m in all 6 launches;
in `round-1a` to `round-3` its versions 1 and 2 stood 22.6-23.5 m away. The design dates every
check to `round-1a`, which is wrong for these two. No recorded unit has stood at the other ten of
the 21 points (the design counted eight, a miscount). The terrain grid from `coord-rear-raid` in
`round-1a` (32 m cells) is restricted at x ≤ -224 for z up to about -160, and in a block at about
x -80..240, z -16..208. The design's text puts every placement in a clear cell, and its table marks
six of the unchecked points (the Infernal Guard and the mounted group) as clear cells.

JUDGEMENT: Authored widths — Claude, 2026-11-08: scenarios.json deployment widths of
emp-chd-camp-v1 (40 m regiments, 20 m characters and guns, 30 m Bull Centaurs) and the Boyar's
20 m in ksl-nor-lines-a-v1; the designs give none. Other frontages change contact timing.

| Unit | Point (x, z) | Bearing | Width | Checked |
|---|---|---|---|---|
| General (`wh_main_emp_cha_general_1`), Knights, Knights, Reiksguard | (380,-40), (426,-40), (380,-86), (426,-86) | 210 | 20, 40, 40, 40 | No |
| Warrior Priest | (-150,-369) | 150 | 20 | Yes (`coord-pincer`) |
| Flagellants ×3 | (-150,-231), (-150,-277), (-150,-323) | 150 | 40 | Yes (`coord-pincer`) |
| Free Company ×2 | (-132,-150), (-154,-190) | 150 | 40 | Yes (`coord-relief`) |
| Magma Cannon, Deathshrieker, Magma Cannon | (81,-470), (127,-470), (173,-470) | 0 | 20 | Yes (`coord-rear-raid`) |
| Infernal Guard ×2 | (104,-420), (150,-420) | 0 | 40 | No |
| Overseer | (127,-445) | 0 | 20 | No |
| Wolf Raiders ×2 | (-11,-470), (35,-470) | 0 | 40 | No |
| Bull Centaurs | (12,-430) | 0 | 30 | No |
| Cutthroats ×2 | (-80,-400), (-34,-400) | 0 | 40 | Yes (`coord-two-fronts`) |

```text
z  -40                                                    G(380,-40) K(426,-40)
z  -86                                                    K(380,-86) R(426,-86)
z -150  FC(-132,-150)
z -190  FC(-154,-190)
z -231  FL(-150,-231)
z -277  FL(-150,-277)
z -323  FL(-150,-323)
z -369  WP(-150,-369)
z -400        CT(-80,-400) CT(-34,-400)
z -420                                IG(104,-420) IG(150,-420)
z -430                BC(12,-430)
z -445                                     OV(127,-445)
z -470         WR(-11,-470) WR(35,-470) MC(81,-470) DS(127,-470) MC(173,-470)
```

The picture is a schematic built from the declared points. Centre-to-centre distances computed from
them for this page:

- Mounted group to the nearest Magma Cannon 436-499 m, at least 56 m outside its range; to the
  Deathshrieker 460-524 m, at least 40 m outside its range. At 7.8 m/s the nearest guns are 56-64 s
  away; only the Knights' speed was ever recorded.
- Levies to the nearest Cutthroats: Warrior Priest 77 m, Flagellants 104, 142 and 183 m (south to
  north), Free Company 223 and 255 m. The cover starts 172-211 m from the nearest levy.
- At the start the Warrior Priest and the south and middle Flagellants are within range of all
  three guns (252-376 m), the north Flagellants and the south Free Company of two, and the north
  Free Company only of the Deathshrieker (412 m).
- The Infernal Guard stand 55-85 m from the guns.

### Public briefing

JUDGEMENT: Camp presentation — Claude, 2026-11-08: neutral names (emp-chd-camp-v1, jobs camp-*),
no briefing key, no history or tactic. A historical name or a sentence about the camp changes the
information demand; model comparisons rest on it.

The declaration has no `scoring`, `benchmark` or `reserve` key, so `play.public` adds nothing to
the observation, and its `brief` text reaches no controller; a declaration test checks both. A
model sees the native Battle section (mode, role, timeout winner, objective text), the rules
prompt and the public enemy roster. The observation carries `job`, so job names stay neutral; no
camp job has been named yet. The declaration lists 28 `withheld` words, 14 for Belgrade and 14 for
the lines battle (the same list as `ksl-nor-lines-a-v1`), and `play` and the owner's recorder
refuse a job that holds one at a word start (`setup.check_job`), so `belgrade-camp-r1` is
refused; this rests on JUDGEMENT? docs/twwarhammer3/lines-eval.md Withheld names.

## The decision

The 2026-11-08 review found that the choice a mounted strike force makes between guns and troops
already engaged was designed twice, in Malta's D1 and here, with the same factions and unit keys,
and counted it once, in this battle. This is therefore the only battle in the set that claims that
decision, and it claims nothing else. The same choice is close to existing battles:
`coord-rear-raid` (protect guns from cavalry behind them; 8 register rows, all lost) and
`brt-cavalry-emp-assault` (cavalry against spears and guns; `llm_rules` won 3 of 5 rows, all three
by gpt-6-sol). `coord-cavalry` has no register row.

**D1, guns or cover.** When a visible cover unit (Wolf Raiders or Bull Centaurs, by type key) has
been flagged in melee with its centre within 30 m of a levy unit with men left, in observations
spanning 10 s, attacking the war machines first (A) and attacking the cover units fighting the
levies first (B) are both feasible for the mounted group. Under condition X, A should win more
launches than B, because the guns stop firing into the levies' fight and the knights are not
shelled there. Two variants may reverse or remove the prediction. Z1, a late cue: the guns have
spent most of their shots, A removes guns that can hardly fire, and B should do as well or better.
Z2, the unbuilt variant `emp-chd-camp-z-v1`: one Infernal Guard moves to the checked point
(219,-470) beside the east Magma Cannon on the knights' approach, the knights meet braced heavy
infantry there, and B should do better.

Condition X, read from the evaluator-only record (built at `f3fec92`; the reader for X is not
built): the cover stays in melee with the levies for at least 60 s after the cue, no Infernal Guard
stands within 50 m of a war machine on the knights' side, and the guns still hold at least 13 of
their 25 shots at the cue. X decides only the exploratory view; every launch counts in the primary
contrast.

JUDGEMENT: Camp condition X — Claude, 2026-11-08: cover in melee 60 s after the cue, no Infernal
Guard within 50 m of a gun, 13 of 25 shots left. Other thresholds change which launches count as X
in the exploratory view; that view rests on it.

JUDGEMENT: Camp claim — Claude, 2026-11-08: the battle claims only D1; start timing and the
Overseer's death stay descriptive. Claiming timing as well changes what a pass means; the one
primary contrast rests on it.

What stays exploratory or descriptive:

- When the mounted group starts (`CampStrikeNow`, `CampStrikeFixed`). On 2026-11-05 the owner said
  "I actually don't think the problem of studying timing is that interesting for now"
  ([owner direction](../owner-direction.md)), and the review counts cavalry commitment timing once,
  in [Cannae A](cannae-eval.md).
- The Overseer's or the General's death, and anything else a controller does, such as hunting the
  Overseer or pulling the levies back. These are legal and recorded, and none is part of the claim.
- A pass would show that the rule mattered for this witness, at its timing cell, on the version its
  ladder picked. It would not show that a model reads the cue.

## Witness, ablations and controls as built

[`battle/camp.py`](../../src/twwarhammer3/battle/camp.py) holds four public-state controllers, each
loaded by module path (for example `twwarhammer3.battle.camp:CampStrike`); their names are not
built-in policy names. All four share these rules:

- **Binding.** At the first observation the friendly army must be the ten declared types with
  positions (the General under his mounted key), or the controller raises `PolicyFailure`, which
  ends the episode as a policy failure (a test checks that it is not counted as a forfeit, in which
  the army would stand for the whole battle). Groups come from type keys; ids and list order change
  nothing.
- **Levies.** From the first decision the Warrior Priest and Flagellants attack the nearest visible
  able enemy in `melee` mode at a run, and the Free Company in `auto` mode at a walk. Each keeps its
  target until it is dead, routing, shattered or out of sight.
- **Cue.** One cover unit's engine melee flag while it has men left (`evidence_rules.in_melee`,
  resting on `JUDGEMENT` Contact rule there), plus the camp's own 30 m test against a levy with men
  left, for 10 s; each cover unit keeps its own streak, which ends at the first observation without
  that state, out of sight included. A routing cover unit still counts (`JUDGEMENT?` Routing cover
  in `camp.py`). Without a cue the mounted group starts at 180 s.
- **Mounted group, after its start.** Attacks in `auto` mode and moves at a run. When its first
  list is empty, each unit attacks its kept target or the nearest enemy, preferring enemies in
  melee beside the levies.
- **Repeats.** An unchanged order is sent again only if, 10 s or more after it was last sent, the
  unit reads idle or an attacking unit has no target, or after the engine refused it.

| Class (`arm` in metadata) | Role | Rule it changes |
|---|---|---|
| `CampStrike` (`camp_strike`) | Witness, arm A | First list: visible able war machines by key, nearest first, kept while able and seen; if none is visible, a run to the last spot of a gun still chased (one seen dead, seen unable, or unseen with one of our able units within 15 m of its spot is dropped) |
| `CampSupport` (`camp_support`) | Arm B | First list: visible able cover units engaged beside the levies; it never rides to an unseen cover unit's last spot (`JUDGEMENT?` Support last spot) |
| `CampStrikeFixed` (`camp_strike_fixed`) | Timing control, descriptive | Starts at a fixed time `T_fixed` instead of the cue. `FIXED_CUE_MS` is unset, so the class raises; a job started now would end every episode as a policy failure |
| `CampStrikeNow` (`camp_strike_now`) | Timing control, descriptive | Starts at the first decision |
| `hold` and `rush_nearest` (`battle/scripted.py`) | Shortcuts | `hold` gives no orders; under `rush_nearest` every unit runs at its nearest visible enemy |

Each controller's metadata records `roles`, `cue_ms`, `start_ms`, `start_reason` (cue, fallback,
fixed or now) and `targets`, and the trace logs it whenever it changes. The values are marked in
`camp.py` (`JUDGEMENT` Camp groups, Camp thresholds and Camp target rules). The shared
fixed-schedule replay (`battle/replay_schedule.py`) is not planned here; `CampStrikeFixed` takes
its place.

[`test_wh3_camp.py`](../../tests/twwarhammer3/test_wh3_camp.py) builds every unit record with the
battle Lua's own `unit_record`, starting from the declared placements, and its 9 tests show which
orders the scripts give: the cue fires on the Bull Centaurs alone (a class-based detector misses
them) and not for idle cover, cover fighting the knights, cover 40 m away, a streak of 8 s or of 6 s
for each of two units, a streak broken by one unseen observation, or cover beside a dead levy; the
strike takes guns by key and keeps a gun while a nearer one passes; `CampSupport` and the timing
controls differ from the witness only in their named rule (`wh3_ablation.assert_ablation`); no arm
reads a hidden section; binding ignores ids and list order. The build planted 34 wrong versions,
15 from the independent review and 19 from the implementer and the fixer. Before the fix round the
review's 15 caught 7. After it, the fixer's own rerun caught 33 of the 34, and no second review
checked that rerun. The survivor is the routing-cover reading, which is marked and left untested
(`runs/siege-evals-20261108/build-offline.json`). None of this shows what the orders do in a game.

## Measurements

The engine outcome is primary. The existing readings carry over: `own_left`, `enemy_left`, men,
order age p50/p90, refusals and cost. Every reading below is descriptive until a check ties it to
the decision, and a missing value stays unknown.

| Reading | Source |
|---|---|
| Cue time, fallback, start time and reason | Controller metadata in the trace |
| Levies' men at the cue and 120 s after | Public friendly rows |
| How long engaged cover stays in melee beside the levies after the cue | Public rows while the cover is visible; the evaluator-only record's `melee` while it is hidden |
| Each gun's ammunition at the cue, and the first time each could no longer fire (men 0, routing or shattered, or ammo 0), with every rout and rally | The evaluator-only record's enemy `ammo` and `ammo0` (the engine's `ammo_left` and `starting_ammo`), `men`, `routing` and `shattered`; no reader is built |
| Whether X held | The evaluator-only record; no reader is built |
| The Overseer's and the General's death or rout | Public rows, and `enemy_roster`'s `dead` flag, which is set only for a unit seen dead; a hidden death or rout reads from the evaluator-only record |

The evaluator-only record, shared work for the whole set (review item S3), was built at `f3fec92`
(`record_private` in the battle Lua; `play` copies it to the episode's `private.jsonl`, fields in
`capture.copy_private_record`). Once per engine second it holds every unit of both sides, hidden
enemies included, with position, men, routing, shattered, melee, hidden, visibility and
ammunition, and it never enters the mailbox observation or the replay. `emp-chd-camp-v1` opts in
with `"private_record": true`, as does every other new declaration of the set. No game has written
the record, so enemy `starting_ammo` and the record's CPU cost per second (`sample_cpu_ms`) are
unread. The Lua changed at `f3fec92`, so every launch from then on, older battles included,
carries a new pack hash and a separate card setup identity. The camp's readers of the record are
not built. They must read a unit whose rows stop as unknown; a reader that counts such a unit as
silenced is the wrong version their tests must catch.

## Proposed deciding checks

JUDGEMENT: Camp deciding checks — Claude, 2026-11-08: the rows below, their counts, and the 5 s/5 s
cell for gate and round. Other counts or cells change what each stage may claim; every label
rests on it.

These are proposals; none is in [agreed checks](../agreed-checks.md). A count of one shows that an
effect is possible; showing that it is reliable takes more launches. Exact chances below come from
[`battle/exact_stats.py`](../../src/twwarhammer3/battle/exact_stats.py).

| # | Claim | Evidence | Count and rule | Must fail on |
|---|---|---|---|---|
| 0 | Recruits | The set's lobby-only readback: setup steps without the Start click, then `army_checks` | Every card recruits, Chaos Dwarf cards in the AI slot under the declared `recruitment_faction` included; war-machine loadouts dumped | A copy with one key swapped |
| 1 | Constructed | Lobby dump and private first reading, every launch | Map, mode, role, settings, rosters as multisets, the General's mount and loadouts as recorded; every unit within 25 m, bearing within 5° after the constant 2.8° offset Cannae's row 1 found | A war machine planted 100 m off; the Wolf Raiders swapped for `wh3_dlc23_chd_cav_hobgoblin_wolf_raiders_bows` |
| 2 | Camp premise | Evaluator-only record in 3 `hold` launches | Each war machine stays within 30 m of its start until a friendly unit is within 100 m of it, and loses ammunition before 120 s; 3 of 3. Passes a premise that holds half the time 12.5%; fails one that holds 80% of the time 48.8% | A fixture whose gun ammunition never falls; a gun moved 40 m; a gun missing from the record must read unknown and fail |
| 3 | Cue occurs | The 4 A and 4 B development launches | A cue before 180 s in at least 6 of 8; the fallback does not count. Passes a 50% cue 14.5%; fails an 80% one 20.3% | Cover idle 40 m away; cover fighting only the knights; a one-observation melee; it must fire when only the Bull Centaurs fight |
| 4 | Orders reach effects | Stage 2 probes, trace and video | Seen once each: a knight attack on a Magma Cannon and on the Deathshrieker reaches the engine melee flag within 90 s and lowers hp; the next decision's attack on another gun; an attack on a cover unit fighting the levies | An accepted attack with no melee flag within 90 s; contact read from distance |
| 5 | Information boundary | Rendered prompt and controller view from this battle's recorded first observation; the declaration-level part already runs offline in `test_wh3_land_eval_declarations.py`, and `test_wh3_eval_boundary.py` runs the prompt and view on a fixture first observation | No historical name, group label, cue rule, evaluator-only key or `mode.benchmark` text in any controller input | Job `belgrade-camp-r1`; a planted evaluator-only key; a benchmark tag |
| 6 | Human win | `uv run --locked python -m twwarhammer3.battle.manual_demo record --scenario emp-chd-camp-v1 --output DIR --ffmpeg FFMPEG --timeout SECONDS`; the recorder refuses only a `custom` scenario or a `reserve` other than a waves profile, so this one records and copies its private record, though its handover is unverified | One engine win; every attempt kept; pauses labelled from video | A recording whose setup readback failed must be refused |
| 7 | Shortcuts | One launch each of `hold` and `rush_nearest` | Reported only; a win is kept and narrows the label | Nothing; reported only |
| 8 | Witness gate | `CampStrike`, fresh launches at 5 s added age and a 5 s interval, frozen version | 4 of 5, stopping at the 4th win or the 2nd loss. Passes a 50% witness 18.75%; fails an 80% one 26.3% | A win credited to a timing the witness did not play |
| 9 | D1 matters, the one primary contrast | `CampStrike` against `CampSupport`, n fresh separate launches per arm fixed in advance, 5 s / 5 s, order drawn in blocks | Two-sided Fisher exact p < 0.05 (`fisher`), Newcombe interval (`newcombe`), a disposition table for every planned launch; every launch counts, fallback-cue launches included; the cue-conditional view and the timing controls are exploratory | Analysis code that drops a fallback-cue launch, counts a rematch as a launch, or reports a one-sided or Wald result |

If the witness fails check 8, no round runs. The version then steps down one difficulty factor or is
revised, and the new version gets a gate on fresh launches; an unchanged gate is never rerun until
it passes
([guideline 2.7](evaluation-guidelines.md#27-admit-a-card-only-from-a-frozen-confirmation-round)).
Natural-timing launches may be reported beside the 5 s / 5 s cell, as
[guideline 2.3](evaluation-guidelines.md#23-show-the-card-can-be-won-at-a-named-timing) asks, but
neither the gate nor the contrast runs there.

Exact power of check 9, from `plan_power`
([guideline 7.4](evaluation-guidelines.md#74-decide-before-you-look)):

| Launches per arm | 0% → 50% | 10% → 60% | 20% → 70% | Wins needed for p < 0.05 against 0, 1, 2, 3 |
|---|---|---|---|---|
| 10 | 0.623 | 0.474 | 0.426 | 5, 7, 8, 9 |
| 16 | 0.962 | 0.786 | 0.740 | 5, 7, 9, 10 |

## Live stages

Stages 0 to 5 cost $0 in API calls, and stage 6 is paid. Every live stage waits for a window the
owner names. Times use the design's estimate of 20-25 minutes for a launch whose battle runs to the
1,200 s timer, and each range below is that estimate times the launch count.

| Stage | What runs | Time | What it can show |
|---|---|---|---|
| 0 (done offline) | Declaration, `camp.py`, tests; `check.py` passed at `e918091` (3461 passed, 70 skipped, by its commit message) | Done | The code does what its tests say |
| 0b (offline) | Still to build: the camp's readers of the evaluator-only record (check 2's ammunition, condition X) and the plan builder. Built since `e918091`: the record itself (`f3fec92`) and a boundary test on fixture first observations (`test_wh3_eval_boundary.py`) | No game | Inputs for checks 2, 5 and 9 |
| L | The set's lobby-only readback (check 0; step files from `scripts/wh3_lobby_readback.py`, which no live lobby has run), one game session with no battle | Minutes | Whether every card recruits, before stage 1 |
| 1 | 3 `hold` launches | About 1-1.25 h | Checks 1 and 2; fields of the never-recorded units; whether the guns are visible at 5 s from the knights' start (enemies were seen at 537-603 m in `bench-b9` and 554 m at 5.3 s in pilot-r4); how the cover and Cutthroats react; whether the guns fire into melee |
| 2 | 1-2 probe launches | About 20-50 min | Check 4; time for the knights to silence a gun |
| 3a | One launch each of `rush_nearest` and `CampStrikeNow` | About 45 min | Check 7 and a timing reading |
| 3b | 4 `CampStrike` and 4 `CampSupport` launches at 5 s / 5 s, then 1 `CampStrikeFixed` once `T_fixed` is set | About 3-3.75 h | Check 3, `T_fixed` (the median cue time of these 8), a first witness win |
| 3c | A ladder from a witness win, one factor per step (stats modifier 1.1, an extra Infernal Guard, rank), 1-2 launches per step with the shortcuts rerun and the cue and condition X re-measured | 4-6 launches, about 1.3-2.5 h | The hardest step the witness still wins |
| 3d | The frozen witness gate (check 8) | Up to 5 launches, up to about 2 h | Whether the frozen version is winnable at the model-like cell |
| 4 | The owner's manual demonstration (check 6) | The owner's time | Human-demonstrated winnability |
| 5 | The round for check 9, only if the owner names it | 16 per arm: 32 launches, about 11-13.5 h; 10 per arm: 20 launches, about 7-8.5 h | The primary contrast |
| 6 | A model pilot, if the owner wants one | Paid; the owner's budget and arms | Exploratory model results; no ranking |

Under owner question 3(c), stage 5 first needs a declared checkpoint check case for this map and
these armies (about 4 launches), then n source launches with two restores each. The Land checkpoint
check passed only for its declared case at `210e356` ([checkpoints](checkpoints.md#the-check)).

## Risks

| Risk | Stage that shows it | Response |
|---|---|---|
| Chaos Dwarf cards do not recruit in the AI slot | L | Another banner from the lobby list, or the Empire mirror |
| The cover charges the knights or never leaves the guns | 3 (check 3) | The prediction disappears; restate the decision, or a version with the knights further away |
| The whole camp leaves to fight the levies | 1 | Record it; the cue still comes, and the guns move slowly |
| The guns destroy the Flagellants before contact | 1 | One fewer gun or the levies closer, one step at a time |
| Knights take too long to kill war machines with 500 bonus hit points | 2 | Change the gun count or the mounted group; record time to silence |
| The guns run out of ammunition before any cue matters | 1-3 | Z1 applies; report the cue time against ammunition from the evaluator-only record |
| The Overseer's or the General's death decides the battle | 3 | Record it; consider a lordless version |
| `hold` or `rush_nearest` wins | 3 | Keep the win; narrow the label |
| The witness never passes the gate | 3d | No round; step down or revise as above |
| Launch variation swamps the contrast, as in Cannae's window 2 | 5 | Question 3(c), checkpoint branches |
| Unchecked placements are unreachable or on slopes | 1 | Move them to checked points |
| The evaluator-only record costs too much CPU per second for about 21 units | 1 | Read `sample_cpu_ms`, already recorded |

## Variation

The first version is one fixed battle for development. The later candidates are the Z2 variant
`emp-chd-camp-z-v1`, the levies starting 400 m out beside the knights (owner question 2(b)), and the
allied-AI levies above. The review proposes reserving a held-out map,
`battle_preset_wh3_nur_wastes_01_04`, before any tuning, because this is the fourth evaluation
battle on Taurox; nobody has inspected that map for this battle, and until the owner chooses a
reservation policy every inspected variant is development evidence. Before stage 5, a frozen
experiment card gives the arms, launches, stop rule, budget and analysis, as the
[Cannae run plan](cannae-eval.md#variation-and-the-eventual-run-plan) does.

## Decisions for owner review

Three questions, with the recommendation first:

1. **Which part of Belgrade, in which mode.** (a) The 22 July sortie on the camp as a Land battle
   the player attacks (recommended; the build at `e918091` used it): native AI only and existing
   orders, at the cost of leaving the fortress and WH3's siege mode out. (b) The 21 July break-in
   as a siege defence: it repeats Haengju's breach decision, and the recorded Helmgart baselines
   put 5 of 16 regiments inside within about 19-27 s of the first. (c) The levies as a native AI
   ally the controller cannot order, after (a): the most faithful, but it needs a player-team lobby
   slot, a public `allies` list and an `allied` deployment.
2. **Where the levies start.** (a) The Priest and Flagellants 77-183 m from the Cutthroats on the
   camp's west flank, so the fight begins at once and the controller decides only how its cavalry
   follows (recommended; the build used it). (b) 400 m out beside the knights, which adds a decision
   about who goes first under fire and changes what is measured.
3. **How check 9 runs, once the gate passes.** (a) 16 separate fresh launches per arm at 5 s / 5 s
   (recommended): 32 launches, about 11-13.5 h, power 0.74 for a 20% → 70% gain. (b) 10 per arm,
   the design's first proposal: 20 launches, about 7-8.5 h, power 0.43 for the same gain.
   (c) Branches restored from a checkpoint saved just before the cue in each source launch,
   compared with exact McNemar (`exact_stats.mcnemar`), which removes launch variation before the
   cue but first needs this battle as a new checkpoint check case. Nothing built depends on this answer.

Other open choices: the markers on this page and in `camp.py`; whether to reserve the held-out map
now; whether the battle keeps its two lords; which stages may start; and any budget for stage 6.

## Sources

The historical account guides the design and is no evidence about the engine.

- Wikipedia, [Siege of Belgrade (1456)](https://en.wikipedia.org/wiki/Siege_of_Belgrade_(1456)),
  fetched for the design on 2026-11-08 (first 100,000 characters). Secondary. Forces, the 21 July
  assault and burning tar (uncited), the 22 July sortie (uncited) and the feigned retreat
  (reference 30), the capture of the guns (references 28 and 30), the withdrawal (reference 28) and
  the infobox figures.
- Wikipedia (Hungarian),
  [Nándorfehérvári diadal](https://hu.wikipedia.org/wiki/N%C3%A1ndorfeh%C3%A9rv%C3%A1ri_diadal),
  fetched for the design on 2026-11-08 through a translation. Secondary. The defenders giving up
  the town, the cavalry counterattack in the inner courtyard, the five archers, the cavalry pulled
  away from the guns, the seizure of the gun positions, Mehmed's wound and its force estimates.
- Not fetched, so nothing here rests on them: Kovach (HistoryNet), Mixson 2022 and Britannica.
- Game database, read-only with `scripts/wh3_db.py` and RPFM's `schema_wh3.ron` on 2026-11-08:
  `main_units_tables` (costs, men), `land_units_tables` (ammunition, armour, bonus hit points,
  spotting range), `missile_weapons_tables` and `projectiles_tables` (ranges, reloads,
  `can_damage_allies`).
- Recorded evidence, ignored by Git. Under `runs/twwarhammer3/battle/`:
  `bench-b12-siege-baselines-20261016`, `bench-b9-assault-medium-ai10-20261014`,
  `bench-b12-siege-reserve-r2-20261016`, `smoke-random-siege-skills-20261014-0511` and
  `gap-initial-02-20261101`. Under `runs/`: `benchmark-initial-20261102/pilot-r4-01` and
  `coord-suite-20261104/round-1a`, `round-2` and `round-4` to `round-6`. All as the design and the
  review read them; the register [results.csv](results.csv).
