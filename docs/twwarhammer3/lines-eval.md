# Alesia inspired two-front defence plan

Development candidate, 2026-11-08 (Claude). **Built offline at `e918091`; nothing has been
launched, and everything on this page is unverified.** On 2026-11-08 the owner asked to build the
good battle ideas now and to play them only when the owner says so ("Build now, game when I say",
[owner direction](../owner-direction.md)). This page documents the last day of the siege of
Alesia (52 BCE), adapted as a WH3 Land battle in which the player defends two lines back to back:
`ksl-nor-lines-a-v1` and `ksl-nor-lines-b-v1` in
[scenarios.json](../../configs/twwarhammer3/scenarios.json), the witness and its arms in
[battle/lines.py](../../src/twwarhammer3/battle/lines.py), and their offline tests in
[test_wh3_lines.py](../../tests/twwarhammer3/test_wh3_lines.py) and
[test_wh3_land_eval_declarations.py](../../tests/twwarhammer3/test_wh3_land_eval_declarations.py).
No stage is scheduled; every live stage below waits for a window the owner names. The design, its
reviews and the build records are in `runs/siege-evals-20261108/` (`final-alesia.md`,
`portfolio.md`, `build-offline.json`), which Git does not keep.

The plan follows the [scenario guidelines](scenario-guidelines.md), the
[evaluation guidelines](evaluation-guidelines.md) and the [benchmark contract](benchmark.md), and
its deciding checks use the rules the set's review (`portfolio.md`) shares across the new battles,
listed under [proposed deciding checks](#proposed-deciding-checks). Under the
[hard rule](../../AGENTS.md#verification-hard-rule) every reading below is unverified, and every
count from earlier battles comes from single recorded battles. The history guides the design and
is no evidence about the engine.

## The historical battle

In 52 BCE Caesar's army besieged the Gallic leader Vercingetorix in the hill town of Alesia. By
Caesar's account the Romans built an inner ring of works facing the town, eleven Roman miles long
with 23 forts (*Gallic War* VII.69), with trenches, a 12-foot rampart and palisade and turrets every
80 feet (VII.72), and an outer ring of fourteen miles facing outward, and stored 30 days of corn and
forage (VII.74). When a Gallic relief army arrived, the Romans were holding two lines back to back.

Forces. Caesar has Vercingetorix speak of 80,000 chosen men in the town (VII.71) and counts the
relief army at 8,000 horse and about 250,000 foot (VII.76, Loeb translation). English Wikipedia
gives the relief as 248,000-300,000 and the Gallic total in ancient sources as 328,000-470,000
(Plutarch 470,000, Strabo 400,000), and calls Caesar's figure "probably an exaggeration to enhance
his victory". It gives Delbrück's modern estimate as 20,000-80,000 besieged and 50,000-100,000 in
the relief. For the Romans it gives 10-11 legions (30,000-50,000 legionaries) and 10,000
auxiliaries, about 60,000-75,000 in all, citing Dodge and Keppie; Livius gives twelve legions,
"about 50,000 legionaries, with allies".

The last day. Vercassivellaunus led 60,000 picked men against the Roman camp on the hill north of
the town. Two legions under Reginus and Rebilus held it. The hill was too large to bring inside the
works, so the camp stood "on ground generally sloping, which put them almost at a disadvantage"
(VII.83). At the same time Vercingetorix came out of the town (VII.84), and his men tried to climb
the steep parts of the inner works and pull down the rampart with hooks (VII.86). Caesar sent
Labienus with six cohorts (VII.86), then young Brutus and Gaius Fabius with more. He then came
himself with four cohorts withdrawn from the nearest fort and ordered part of the cavalry "to go
round the outer entrenchments and attack the enemy in rear"; Labienus gathered forty cohorts
(VII.87). When the cavalry appeared behind them the attackers fled and were cut down. Sedulius was
killed, Vercassivellaunus was captured and 74 standards were taken; the men from the town withdrew
from the works (VII.88), and the next day Vercingetorix was surrendered (VII.89).

Where the sources disagree:
- Labienus' cohorts: forty in Caesar (VII.87), 39 in Livius.
- The lines: eleven and fourteen Roman miles in Caesar, "about 15 km" in Livius. Wikipedia says
  archaeology suggests the lines "were not continuous as Caesar claims".
- The relief army: about 250,000 foot and 8,000 horse in the Loeb translation, 248,000 in
  Wikipedia's lower relief figure. This page did not read the Latin.
- The weak point: in Caesar it is a hill too large to enclose; Livius calls it "a small gap in the
  northwest".
- The account itself: Livius calls Caesar's narrative "very artful", says that by Caesar's account
  "it was only the arrival of the general himself" that decided the battle, and calls the story of
  the Gallic leaders handing over Vercingetorix "probably not what really happened".

The disadvantage, stated plainly. Wikipedia gives Caesar's Gallic total as 328,000; the Loeb
numbers above add up to 338,000 (80,000 in the town, 8,000 horse and about 250,000 foot in the
relief). Against the modern estimate of 60,000-75,000 Romans, Wikipedia's figure is about 4.4 to
5.5 times their number and the Loeb sum about 4.5 to 5.6 times; on Delbrück's estimate
(70,000-180,000 Gauls in all) they faced between about 0.9 and 3 times their number. On every
account they stood between two enemies who attacked on the same day from both sides. Their
advantages were the prepared works and short distances between forts (Caesar drew four cohorts
from the nearest one). What decided the
last day, as Caesar tells it, was that the Romans read where the main attack was, fed reserves
there in steps, brought the commander in person and sent cavalry outside the works into the
attackers' rear. That is Caesar's own version, which Livius treats with suspicion.

## Choosing the WH3 game mode

WH3's siege mode gives the defender one wall that faces outward; every attacker starts outside it,
and tickets and victory points decide the battle (the Helmgart first observation in
`bench-b12-siege-reserve-r2-20261016`, as the design read it). That fits Haengju. Alesia's
defining feature is that the defenders were attacked from inside and outside their own lines on the
same day (VII.84), which no siege layout in WH3 allows without engine behaviours nobody has tried.

| Battle type and role | What its rules give | Verdict |
|---|---|---|
| Siege, player defends, attacker garrison teleported inside the walls | One outward wall, tickets and victory points; all attackers start outside | Rejected. It needs about six untested engine behaviours (placement in a siege, a teleport inside the walls, native AI for attackers already inside, a multi-slot hold with a release, attacks on units on walls, a gate sally), and tickets turn the inner front into a defence of the Key Building |
| Siege on a major settlement, native attack on several faces | Gates on several faces. Native AI split its army once, in one random battle with an autogenerated army, apparently by unit class | Not built under this name. It has no garrison front, so it would be a separate multi-face siege candidate after Haengju's stages 1-2 |
| **Classic Land battle, player defends** | The defender wins at the timer if it still has units present and not routing; native attacker groups attack from authored positions | **Chosen.** It keeps the decision and drops the works |
| Survival, chokepoint, ambush, minor settlement, siege attack | One attack direction, native waves, field works built during the battle, or gate and wall orders the interface lacks | Rejected |

JUDGEMENT: Separate multi-face siege — Claude, 2026-11-08 (two-front design): the native siege
on several faces is not built as this battle, at most later as its own candidate. Built as this
battle it drops the inner front; the set's siege coverage and what comes next rest on it.

What the chosen mode rests on. The objective text of the `coord-two-fronts` first observation
reads role defender and `timeout_winner` "us" (the design's reading). In the
[register](results.csv), 16 battles ended by `time_limit`, all classic Land battles, and the player
won 3 of them (`CornerHold` twice, `attack_nearest` once). Authored placement read back within 25 m
for every unit in all 13 Cannae window 1 battles, with a largest error of 8.8 m (recounted for this
page from their `result.json` files). The design's "12 of 13" counts the battles inside every
tolerance, width included: the air battle had 5 units outside on width. Rear charges, flank
morale, the lord's aura and army-loss morale are native mechanics that nothing here has measured.

What the adaptation drops:
- The works. WH3 has no Land mode with prepared field lines and a garrison inside them, so the
  player's regiments are not tied to their lines and may leave them. The `Concentrate` and `Evade`
  controls and deciding check 4 measure what that changes.
- The force ratio. The player is the stronger side by lobby cost and outnumbered only 1.25 times by
  table men ([rosters](#rosters)). The difficulty comes from three groups attacking from two
  directions at once under very hard AI, and the ladder in stage 3 can raise the enemy's rank.
- The weak camp. Both friendly lines are mirror-symmetric, with no weak sector, so the two cases
  differ only in which side the heavy relief group attacks.
- The anchored ends. No terrain on Taurox anchors both lines; check 4 fails the layout if the
  attackers come round the ends.
- The town, the hill, the starving garrison, the day-long fight and the surrender. The town-side
  group starts in the open 120 m north of the inner line, and the timer is 1,200 s.

This page labels the battle "a two-front defence after Alesia's last day". WH3 does not treat it as
a siege battle, and if the owner wants only battles that play in WH3's siege mode this battle
should be dropped ([owner question 1](#decisions-for-owner-review)).

## Battle specification

In the fields of [the scenario specification](scenario-guidelines.md#the-scenario-specification):

| Field | This battle |
|---|---|
| Question and coverage | Which of two relief attacks arriving together gets the reserve and the cavalry: reserve allocation between fronts, the family of `coord-two-fronts`. Land defence against native AI. Claims excluded: siege mechanics, recognition of the battle, model ability, rear-charge collapse, cavalry timing |
| Public task | Win the battle; every engine win counts, the timer win included. The existing observation and orders, unpaused at 1x, with no added briefing ([public briefing](#public-briefing)) |
| Concrete setup | [Settings](#settings), [rosters](#rosters), [map and placements](#map-and-placements); b inherits everything from a except its name, provenance text and `deployment.enemy` |
| Decision opportunity | [P1](#decisions): the cue, the choices, about 101 m for the reserve to either sector post and 190 m between posts |
| Mechanic reference | The timer rule and placement readback above; native morale and charge mechanics unmeasured |
| Winnability evidence | None yet. The owner's demonstration per case (check 12) and the frozen witness gate (check 10) |
| Controls and predictions | [Witness, arms and controls](#witness-arms-and-controls-as-built) |
| Measurements | [Measurements](#measurements) |
| Variation and exposure | Two mirror cases, a and b, both development; no held-out variant. The terrain under the two slots differs, so the mirror is not assumed equivalent |
| Validation plan | [Proposed deciding checks](#proposed-deciding-checks) and [live stages](#live-stages) |
| Release record | Source `e918091`, which did not change the Lua or the pack hash; `prototype_not_admitted`, split `development`; nothing launched. The `private_record` opt-in and the `withheld` list were added after `f3fec92`. The Lua changed at `f3fec92` (the evaluator-only record, divisions in turn and the siege-attack interface), so every launch from `f3fec92` on, this battle's included, carries the new pack hash and a separate card setup identity |

### Settings

JUDGEMENT: Lines mode — Claude, 2026-11-08 (two-front design): scenarios.json
ksl-nor-lines-a-v1 battle_type classic and attacker enemy, with no script. A siege with an inner
garrison or a native multi-face siege changes the decision; both cases rest on it.

JUDGEMENT: Lines settings — Claude, 2026-11-08 (two-front design, unmarked there):
scenarios.json ksl-nor-lines-a-v1 map and expect (very hard, modifier 1.0, large units, 1,200 s,
funds 14,000). Another difficulty, timer or funds changes how hard the battle is.

| Field | `ksl-nor-lines-a-v1` (b inherits all of it) |
|---|---|
| Mode and role | `battle_type` `classic`, `attacker` `enemy`; `expect` pins engine type `land_normal` and `player_defends` true, so the first observation must read role defender |
| Map | `battle_preset_qb_wh2_dlc17_taurox_rune_tortured_axes`, bounds ±512 m |
| Difficulty and scale | `ai_level_very_hard`, AI stats modifier 1.0, unit scale 0.75 (large), realism off |
| Ranks | Experience 0 on all 12 units of each side |
| Timer and funds | 1,200 s; `funds_custom` 14,000 against the player's table cost of 9,000; the lobby charge is unread |
| Toggles | `behaviour_defaults: true` |
| Deployment | Authored for both sides, the whole roster placed by type, read back within 25 m (`setup.DEPLOYMENT_TOLERANCE_M`) |
| Content | `wh_main`, `wh_dlc08`, `wh3_main` |
| Scripted elements | None: no `reserve`, `custom`, `scoring` or `benchmark` key |
| Evaluator-only record | `private_record: true` in both cases: once per engine second the mod writes every unit of both sides, hidden enemies included, to a file no controller reads ([measurements](#measurements)) |
| Status | `prototype_not_admitted`, split `development`; no reserved set and no agreed check |

### Rosters

JUDGEMENT: Lines forces — Claude, 2026-11-08 (two-front design): scenarios.json
ksl-nor-lines-a-v1 player and enemy units, Kislev against Norsca. Empire against Greenskins
changes the matchups; the rosters and costs rest on it.

JUDGEMENT: Lines enemy lord — Claude, 2026-11-08 (two-front design): scenarios.json
ksl-nor-lines-a-v1 enemy lord false. A chieftain with either group adds a decapitation target
or a cue for the main effort; which decision the battle tests rests on it.

JUDGEMENT: Norsca banner — Claude, 2026-11-08: scenarios.json ksl-nor-lines-a-v1 enemy faction
wh_dlc08_nor_norsca, an autogenerated Norsca army's banner, where the design leaves the faction
to the stage 1 lobby list. Another banner may offer other cards in the lobby.

Costs are `multiplayer_cost` and men are `num_men` from `main_units_tables`, read for this page on
2026-11-08 with `scripts/wh3_db.py` (read-only; the rows stay in
`runs/siege-evals-20261108/scratch/lines-eval/`). They match the declaration's provenance text.
Men at large scale are table men times 0.75, an assumption: no lobby or battle has read these
units' sizes.

Player, Kislev (`wh3_main_sc_ksl_kislev` / `wh3_main_ksl_kislev`, lord true):

| Unit | Key | Count | Cost each | Table men each |
|---|---|---|---|---|
| Boyar (on foot) | `wh3_main_ksl_cha_boyar_0` | 1 | 700 | 1 |
| Kossars | `wh3_main_ksl_inf_kossars_1` | 3 | 500 | 90 |
| Armoured Kossars | `wh3_main_ksl_inf_armoured_kossars_0` | 3 | 700 | 100 |
| Streltsi | `wh3_main_ksl_inf_streltsi_0` | 2 | 850 | 90 |
| Tzar Guard | `wh3_main_ksl_inf_tzar_guard_0` | 1 | 1,000 | 80 |
| Winged Lancers | `wh3_main_ksl_cav_winged_lancers_0` | 2 | 1,000 | 60 |

That is 12 units, 9,000 cost and 951 table men (about 713 at large scale).

Enemy, Norsca (`wh_dlc08_sc_nor_norsca` / `wh_dlc08_nor_norsca`, lord false), in three groups:

| Group | Units (cost each, table men each) | Cost | Table men |
|---|---|---|---|
| G, the town side | 2 Chaos Marauders `wh_main_nor_inf_chaos_marauders_0` (400, 120), 2 Marauder Spearmen `wh_dlc08_nor_inf_marauder_spearman_0` (425, 120) | 1,650 | 480 |
| L, the light relief group | 2 Marauder Spearmen, Marauder Hunters `wh_dlc08_nor_inf_marauder_hunters_0` (550, 90), Marauder Horsemen `wh_main_nor_cav_marauder_horsemen_0` (600, 60) | 2,000 | 390 |
| H, the heavy relief group | 2 Marauder Champions `wh_dlc08_nor_inf_marauder_champions_0` (1,000, 100), Marauder Berserkers `wh_dlc08_nor_inf_marauder_berserkers_0` (750, 100), Fimir `wh_dlc08_nor_mon_fimir_0` (1,150, 16) | 3,900 | 316 |

That is 12 units, 7,550 cost (0.84 times the player's) and 1,186 table men (about 890 at large
scale, 1.25 times the player's). H is the main effort: it costs nearly twice as much as L and has
fewer men (316 against 390 table men), so a rule that counts heads picks the wrong group. The Fimir
key is the Norsca unit; the row `wh3_dlc25_nur_chieftain_mon_fimir_0` (1,300) is a different unit.

Card evidence, all short of a readback in a classic lobby:
- The Boyar, Kossars, Armoured Kossars and Streltsi were recruited in `ksl-reserves-survival`, a
  survival battle with 10 register rows. The Tzar Guard, Winged Lancers and Boyar cards appear
  in the lobby card list `runs/twwarhammer3/battle/bench-b12-kislev-reserves-20261016/cards_slot0.txt`;
  no played scenario has recruited the Tzar Guard or the Winged Lancers.
- No Norsca card has been recruited by key. An autogenerated Norsca army fought under the banner
  `wh_dlc08_nor_norsca` in `skills-v1.1-random-a-20261013`; its trace shows `chaos_marauders_0`,
  `marauder_spearman_0`, `marauder_berserkers_0` and `marauder_horsemen_0`, and the `_1` variants
  of the Champions and Hunters (searched for this page). The Champions `_0`, Hunters `_0` and
  Fimir `_0` have never been read in a battle.

### Map and placements

JUDGEMENT: Lines layout — Claude, 2026-11-08 (two-front design): scenarios.json
ksl-nor-lines-a-v1 and -b-v1 deployment, b mirroring every enemy point about x = 130. Another
layout or a second map changes timing and the cue; every reading rests on it.

JUDGEMENT: Reserve facing — Claude, 2026-11-08: scenarios.json ksl-nor-lines-a-v1 bearing 180
for the Boyar, Tzar Guard and Lancers; the design gives none. Facing 0 changes the turn the
reserve makes before it moves to the inner line.

Axes: x east, z north, bearing 0 north. The positions are the declaration's (x in brackets):

```text
 z  -45  G:          Spearmen(62)  Marauders(107)  Marauders(153)  Spearmen(198)       facing 180
 z -165  inner line: Kossars(70)   Armoured Kossars(130)   Kossars(190)                facing 0
 z -215                            Boyar(130)                                          facing 180
 z -230                            Tzar Guard(130)                                     facing 180
 z -245              Lancers(85)                   Lancers(175)                        facing 180
 z -295  outer line: AK(10) Streltsi(60) Kossars(130) Streltsi(200) AK(250)            facing 180
 z -445  west slot front: (5) (55)                  east slot front: (205) (255)       facing 0
 z -480  west slot back:  (5) (55)                  east slot back:  (205) (255)       facing 0
```

- Case a: H in the west slot (Champions at (5,-445) and (55,-445), Berserkers (5,-480), Fimir
  (55,-480)); L in the east slot (Spearmen at (205,-445) and (255,-445), Hunters (205,-480),
  Horsemen (255,-480)).
- Case b: every enemy placement of a mirrored, x to 260 - x and bearing to (360 - bearing) % 360.
  H is in the east slot and L in the west. G and the whole friendly army are their own mirror
  images, so the cases differ only in the side of H and in the terrain under it.
- Widths are 40 m, except 30 m for the Fimir and the Horsemen and 20 m for the Boyar. The Boyar's
  20 m rests on JUDGEMENT docs/twwarhammer3/camp-eval.md Authored widths; the other widths are the
  design's, under Lines layout.
- Distances: G's front to the inner line 120 m; the relief front rank to the outer line 150 m (the
  back rank 185 m); between the lines 130 m, a strip from z -295 to -165 that this page calls the
  band; the Tzar Guard and the Boyar to either sector post 101 m; between the two posts 190 m; the
  west Lancers to the west waypoint 194 m and the east Lancers to it 281 m.
- Terrain: all 48 placements of both cases, the four reserve posts and the two Lancer waypoints lie
  on open cells of the recorded 32 m grid (`runs/cannae-window-1/a-evade-01`, same map), checked
  for this page with the scripts' own cell test (`calibration._clear`). That tests cell centres
  only; routes are unchecked.
- Timing, as the design read it: Kislev run speeds of 3.0-3.4 m/s in
  `bench-b12-kislev-reserves-r2-20261016` (Armoured Kossars, Kossars, Streltsi, Boyar; the Tzar
  Guard is unread) give about 30-34 s to a post and 56-63 s between posts. In the `skills` replays
  of the suite, each enemy group's first melee came at 62.2 and 64.0 s on `coord-two-fronts`
  (groups 250 m away) and at 40.0, 40.0 and 42.1 s on `coord-breakout` (210 m). Contact here is
  unmeasured.
- Visibility: in the first observations of `coord-two-fronts` and `coord-breakout` (their `skills`
  launches) and Cannae A's `a-hold-01`, every enemy was listed at 5.2 s, when each stood 255-258 m,
  168-182 m and 168-228 m from the nearest friendly unit (recomputed for this page; the design gave
  210-250 m). Here the enemy starts 120-185 m from the lines. Check 5 tests it.

### Public briefing

JUDGEMENT: Lines briefing — Claude, 2026-11-08 (two-front design): ksl-nor-lines-a-v1 has no
scoring, benchmark or reserve key, so no added sentence or lobby cost reaches a controller.
Adding one changes the information demand; model comparisons rest on it.

A controller sees only the existing observation: the engine's objective text in `mode`, which
states the timer rule, `remaining_ms`, the enemy roster as ids and type keys, the terrain grid and
the units it can see. The scenario's `brief` is for people and never reaches a controller.
`test_no_declaration_text_names_the_history_or_reaches_a_controller` checks that `play.public`
gives the same view with and without the scenario (so no `mode.benchmark` tag) and that the battle
session holds only the behaviour defaults, the private deployment and the private-record switch.
The job name does reach
controllers ([guideline 4.5](evaluation-guidelines.md#45-give-controllers-only-listed-public-fields-and-test-by-changing-hidden-data)),
so jobs get neutral numbered names such as `lines-r1-017`, with the case and arm kept only in
private plan records. `play` and the owner's recorder refuse a job that holds one of the
declaration's withheld words at a word start (`setup.check_job`), so `alesia-a-r1` is refused.
Nothing keeps the case or the arm out of a job name: the plan builder (portfolio S6) is not built.

Both cases list the words under `withheld` (`ksl-nor-lines-b-v1` inherits case a's list), which
`emp-chd-camp-v1` shares. For this battle the list holds alesia, caesar, vercingetorix,
vercassivellaunus, labienus, reginus, rebilus, sedulius, gallic, gaul, roman, vallation,
circumvallation and contravallation; the rest are the camp attack's names. The same test folds
every key and string of the three new declarations, the list itself excepted, to lower-case ASCII
and checks it against these words, and
`test_a_job_that_names_the_history_is_refused_and_a_neutral_one_accepted` checks the job refusal.

JUDGEMENT?: Withheld names — Claude, 2026-11-08: the designs' prompt-test lists plus other
names in their sources, folded to lower-case ASCII. A shorter list would pass more names; the
neutral-naming check rests on it.

Information asymmetry. The witness weighs the relief groups by lobby cost from a fixed table
(`COST` in lines.py), which no controller is told; a model sees only type keys. The witness
therefore knows more than any model, and W against M measures whether a cost-informed side choice
matters for this script. It does not measure whether a controller can read the main effort from
public fields. This rests on JUDGEMENT src/twwarhammer3/battle/lines.py Lines side weights.

## Decisions

In the [specification form](scenario-guidelines.md#the-scenario-specification). A controller may
win by any legal play; a prediction that fails narrows this page's reading and leaves the win
standing.

**P1, the main effort (this battle's one claim).** When both relief groups are visible south of the
outer line (expected at the first observation; check 5), sending the reserve (Tzar Guard and Boyar)
and the Lancers to H's side and sending them to L's side are both feasible: the reserve needs about
101 m to either sector post and the Lancers 194-281 m to the outside waypoint. With the friendly
line even and all three groups reaching the lines within the window (check 2), H should break the
sector it faces unless the reserve joins it, while L's sector should hold either way, so the
witness W should win more often than M, which sends them to L. If L alone can break its sector, if
native AI moves H across x = 130 to L's side (check 3 reads this), or if the contacts are staggered
beyond the window, the difference should shrink or reverse.

Overlap rule (portfolio, "overlaps"). Reserve allocation between fronts or at a breach appears five
times across the new designs and the suite: Haengju D2, Malta D2, this battle's P1,
`coord-two-fronts` ("Two separate fights at once, one reserve to send") and `coord-siege` /
`chd-reserve-grn-siege` ("committing one mobile reserve"). It is counted once, here, because this
battle's design was the only one that already planned its contrast at 16 launches per arm; every
built battle page now recommends 16 per arm for its round, so the assignment no longer follows
from power and rests on JUDGEMENT docs/twwarhammer3/historical-evals.md Claim assignment. Haengju
D2 and Malta D2 stay exploratory. Everything else in this battle stays exploratory and has no test:

- **E1, inner economy.** When G reaches the inner line while the relief is engaged, holding with
  the three inner regiments and pulling outer regiments inward are both feasible. Holding should
  keep the outer line whole; if G breaks the inner line first, the inner front becomes the main
  effort.
- **E2, counterstroke.** When two or more H regiments are in melee at the outer line, the Lancers
  can ride round the line's end into H's rear or stay in the band. The rear charge should rout H
  sooner; if H turns to face them, or no rear contact lands, nothing can be tested. The
  [Cannae plan](cannae-eval.md) reports that no A v2 battle shows Knights hitting the rear of an
  unbroken regiment that then collapses; no rear-contact reader exists to say more. Rear charges
  are counted once, in Cannae A, and no N arm (W without the Lancers) is built.
- **E3, commander.** When an outer regiment wavers, bringing the Boyar within aura range and keeping
  him back are both feasible. The aura should delay the rout; his death costs army-wide morale.
  Commander exposure stays exploratory in every new battle.
- **E4, reading before contact.** Choosing the side from strength before contact (W) and sending
  the reserve to the first sector in melee are both feasible. L's Horsemen probably arrive first,
  so the reactive rule should go to the wrong side; if H arrives first the two agree. No F arm is
  built. The Lancers' wait for two engaged units is a timing choice, which the set counts once in
  Cannae A and keeps descriptive here (owner, 2026-11-05: "I actually don't think the problem of
  studying timing is that interesting for now").

| Existing battle | Shared with this one | Different here |
|---|---|---|
| `coord-breakout` (Taurox; player at x 104-196, z -300 to -215; three groups about 210 m away to the west, east and south) | Same map, with its player on the ground of this battle's outer line and band; groups converge | Two lines back to back with a reserve between them; unequal relief groups whose stronger one has fewer men; one group attacks from the town side |
| `coord-two-fronts` (Taurox; two groups 410 m apart, one Knights reserve) | One reserve between two fights | Back-to-back lines, unequal groups, an inner front |
| Cannae A | Rear charge | Here the counterstroke is exploratory |
| [Haengju](haengju-eval.md) | A defender against a stronger attacker | Land battle; the threats arrive together |

Register facts ([results.csv](results.csv), recounted for this page): on `coord-breakout` `skills`
won 1 of 1, `commander` 1 of 1 and `Concentrate` lost 2 of 2, and the 6 other battles were lost; on
`coord-two-fronts` `commander` won 1 of 1 and the 10 other battles were lost. If `Concentrate` or
`skills` wins here about as often as the witness, the battle narrows to a converging-groups battle
like `coord-breakout`, and the owner decides whether to keep it.

## Witness, arms and controls as built

[battle/lines.py](../../src/twwarhammer3/battle/lines.py) holds three classes. No built-in name is
registered; a job names them as `twwarhammer3.battle.lines:LinesWitness`, `:LinesByMen` and
`:LinesCentral`. Each reads public state only (its own units, the visible enemies, the terrain
grid and the battle time) and gives these orders:

1. **Roles** bind once, at the first observation, from type and start position. The Kossars,
   Armoured Kossars and Streltsi split at the midpoint of their start z into the inner line (three,
   north) and the outer line (five, south). The outer line's two westmost regiments are the west
   sector, its two eastmost the east sector, and the middle one belongs to neither. The Tzar Guard
   and the Boyar are the reserve, the two Winged Lancers the Lancers. Any other army, or a unit not
   seen at binding, raises `PolicyFailure`.
2. **Leash.** Every unit keeps its start as its post. It attacks a visible enemy only when that
   enemy is within 40 m of its post and goes back, facing out from its line, when it is more than
   15 m from the post. The eight line regiments set guard and fire at will on and skirmish off.
3. **Relief units** are the enemies first seen more than 60 m ahead of the outer line's start
   centre, kept by id (rests on JUDGEMENT? src/twwarhammer3/battle/lines.py Relief membership).
4. **Side.** The first time 6 enemies stand more than 60 m ahead of the outer line, the relief units
   are split at the outer line's centre x (130) and each side is scored; the higher side is chosen
   and a tie chooses nothing yet. The side switches only when the other side scores more than 1.3
   times as much. Routing units are not scored.
5. **Reserve.** Once a side is chosen the Tzar Guard posts 30 m behind that sector's centre, at
   (35,-265) or (225,-265), and the Boyar 15 m behind it, at (35,-250) or (225,-250), each on the
   same leash. Until then both keep their starts.
6. **Lancers.** They wait on their leash until 2 relief units on the chosen side are in melee (the
   engine flag, `evidence_rules.in_melee`), take the engaged unit nearest the sector centre, ride
   to a waypoint 110 m past the line's end regiment and 10 m ahead of the line, at (-100,-305) or
   (360,-305), then to 70 m behind the target along the outer line's front, and charge. After 8 s
   of melee, or when the target is lost, they pull out to 120 m from the nearest enemy and ride
   again after 20 s, or after 10 s once no enemy is within 80 m. These are
   `calibration.HammerAnvil`'s values (rests on JUDGEMENT? src/twwarhammer3/battle/lines.py
   Lancers' rear point).
7. Nothing else: no inner-line replacement and no pursuit. Moves are run orders, and a goal on a
   blocked cell steps to the nearest open cell within two cells, or the unit holds.

The values rest on JUDGEMENT src/twwarhammer3/battle/lines.py Lines witness rules.

| Arm | Class | Rule it changes | Built |
|---|---|---|---|
| W, the witness | `LinesWitness` | Side scored by lobby cost (`COST`, 7 Norsca types) | Yes |
| M, the primary foil | `LinesByMen` | Side scored by the visible enemies' current men; on this roster it picks L in both cases | Yes |
| C, central | `LinesCentral` | No side: the reserve and the Lancers keep their start posts on the leash, and the Lancers never ride | Yes |
| F, first contact | none | Side = the first outer sector with a friendly unit in melee | No |
| N, no counterstroke | none | W without rule 6 | No |

Offline evidence at `e918091`: the 9 tests in `test_wh3_lines.py` run the arms on made-up fights
built from both declarations. W chooses H's side and M L's side in both cases, and C chooses none;
case b's orders are case a's mirrored about x = 130; M and C differ from W only in the Boyar's,
Tzar Guard's and Lancers' orders, and W and M give identical orders where both rules pick the same
side (`wh3_ablation.assert_ablation`); renaming the job, adding hidden keys or renaming and
reordering unit ids changes no order. The build's fixer swept 42 planted wrong versions and the
tests caught 39; the three missed are M weighing men at the start, an enemy exactly on x = 130,
and no Lancer reset on a side switch (`build-offline.json`, P7). These tests show what the scripts
order; what the engine does with those orders is untested.

| Control | Source | What a win means |
|---|---|---|
| `hold` | `scripted.py` | Engine automation holds both fronts unaided |
| `attack_nearest`, `rush_nearest` | `scripted.py` | Naive play suffices |
| `skills` (won `coord-breakout` 1 of 1) | `skills.py` | A class script suffices |
| `twwarhammer3.battle.evade:Evade` | `evade.py` | The timer alone can decide the battle |
| `twwarhammer3.battle.reference:Concentrate` (lost `coord-breakout` 2 of 2) | `reference.py` | Beating the groups one at a time beats holding lines; the battle narrows to a `coord-breakout`-like label |
| C | `lines.py` | Committing the reserve and the Lancers at all is not needed |
| M | `lines.py` | Which side they go to does not matter for this script |

Every win is kept; a shortcut win narrows the label and never adds a requirement. For model studies
later: a fixed-schedule foil (`replay_schedule.ReplaySchedule`, built at `e918091`) that replays a
winning W launch's orders by battle time; an announced arm whose briefing names H's side; and a
named-briefing arm only if recognition becomes a claim.

## Measurements

| Reading | Source and limit | Built |
|---|---|---|
| Engine outcome, `ended_by`, `battle_s`, `own_left`, `enemy_left`, `own_active`, `enemy_active`, `added_age_s` | Register row and trace | Yes |
| The side the witness chose, when, its scores, any switch, the Lancers' phase and charges | `LinesWitness.metadata()`, which the trace records when it changes | Yes |
| Each group's contact time (the first time 2 of its 4 units are in melee) and the spread between groups | 1 Hz replay, never a policy input; contact is the engine melee flag on a unit with men left, and groups come from the private first reading matched to the placements, never from current position | No |
| Where each unit's first melee lay, relative to the lines and the split | Same | No |
| The reserve's arrival within 25 m of its post | Same | No |
| The first friendly rout per sector, and when | Same | No |
| Lancer arrival at the waypoint and melee behind a target | Same; a rear-contact detector stays later work, validated against owner-labelled clips chosen before its thresholds | No |
| The Boyar's position, waver and death times | Same | No |

The contact and grouping readings rest on JUDGEMENT src/twwarhammer3/battle/evidence_rules.py
Contact rule and on JUDGEMENT? src/twwarhammer3/battle/evidence_rules.py Group membership. The
replay keeps enemies only while they are visible. The evaluator-only all-unit record (portfolio
S3), built at `f3fec92` (fields in `capture.copy_private_record`), holds every enemy unit, hidden
ones included, and both cases opt into it with `"private_record": true`, so if check 5 or stage 1
shows enemies leaving sight the readings can read it instead; no reader of it is built for this
battle, and no game has written it. All readings are descriptive, and missing values stay unknown.

## Proposed deciding checks

JUDGEMENT: Lines deciding checks — Claude, 2026-11-08: the rows, counts and plants below, with W
against M as the one claim and a 4-of-5 gate at 5 s/5 s in alternating cases. Other contrasts,
counts or gates change what each stage may claim; every label rests on it.

These are proposals for the owner; none is in [agreed checks](../agreed-checks.md). They follow
the set's shared rules: one primary contrast per battle at two-sided Fisher p < 0.05
([exact_stats.py](../../src/twwarhammer3/battle/exact_stats.py)), a frozen 4-of-5 witness gate at
5 s added order age and a 5 s decision interval before any round, exact power printed, and contact
from the engine melee flag ([evidence_rules.py](../../src/twwarhammer3/battle/evidence_rules.py)).
No gate exists in this battle, so the hp <= 0 breach rule does not apply. Checks 2-4 are premise
checks that need all six stage 1 `hold` launches, 3 of 3 in each case. A premise that holds in 80%
of launches passes one case 0.512 of the time and the whole check, both cases, 0.262 of the time
(0.8 to the sixth power).

| # | Claim | Evidence | Rule | Must fail on |
|---|---|---|---|---|
| 0 | Cards recruit | Lobby-only readback with no battle (portfolio S9): the scenario's lobby steps without the Start click, then `setup.army_checks` | All 13 keys and the banner read back in a classic lobby, with counts | A scenario copy with one key swapped |
| 1 | Constructed | Lobby readback and the private first reading, every launch | Map, mode, role, settings, funds and charge, rosters by multiplicity, rank 0; every unit within 25 m; bearing within 5 degrees after the constant offset stage 1 measures (Cannae found 2.8 degrees); widths recorded, the Boyar's excluded | A Champions placed in the east slot in case a; a group staged 100 m off; case b's file launched under case a's label |
| 2 | Two fronts at once | 1 Hz replay of the stage 1 `hold` launches, 3 of 3 per case | The spread between G's, L's and H's contact times is at most the window: provisional 56 s (190 m at 3.4 m/s), recomputed from the Tzar Guard's run in stage 2 and then re-read on the same replays | A synthetic replay with G's contact 200 s late; a reader that times a group from one lone Horsemen charge; groups rebuilt from current x |
| 3 | Main effort on its side | Same | H's first melee lies on its slot's side of x = 130, 3 of 3 per case | The same replay read under the swapped case label |
| 4 | Lines met at their front | Same | Per launch, at most 2 of 8 relief units' first melee lies north of z -280 or outside x -50 to 310, and at most 1 of 4 G units' first melee lies south of z -180 or outside x 10 to 250 | A synthetic replay in which relief units first meet in melee inside the band |
| 5 | Visible at the start | First observation against the private reading, stage 1 | 12 of 12 enemies visible by the first decision | A reading that drops a hidden unit and still counts 12 |
| 6 | Information boundary | Built: the declaration test above, the arms' hidden-key and job tests, and `test_wh3_eval_boundary.py`, which renders the `llm` prompt and `play.public` view from fixture first observations of both cases and checks that the two views differ only in enemy positions, bearings and states. To build: the same from recorded first observations of both cases (portfolio S2) | No case, slot, group label, "main effort" or withheld name in any input, the job name included; the two cases' views differ only in enemy positions, bearings and states | The case letter planted in the job name |
| 7 | Orders reach effects | Stage 2 probe, trace and video | The Tzar Guard runs between the posts (its time sets check 2's window); the Lancers reach the waypoint and the rear point, and an attack gives melee within 15 s; guard, fire at will and skirmish read back on the Kislev units. An effect seen once shows it can happen and says nothing about how often | An accepted move whose unit never arrives, reported as a non-arrival |
| 8 | Arms wired | Offline, built (`test_wh3_lines.py`); to repeat on recorded first-observation sequences after stage 1 | W picks H's side and M L's side in both cases; arms differ only in the reserve and Lancer orders; the job changes no order | M's flag unwired; W weighing by men; W reading the case from anything but positions |
| 9 | Shortcuts | Stage 3a, one launch per control, cases alternated, rerun at each ladder step | Reported only; a win is kept and narrows the label | Nothing; reported only |
| 10 | Witness at a named timing | Frozen gate: W at 5 s / 5 s, fresh launches in a pre-drawn alternating case order | At least 4 of 5 won, stopping at the 4th win or the 2nd loss. Exact error rates (`exact_stats.gate_pass`): it passes a 50% witness 0.1875 of the time and fails an 80% one 0.263 | A witness win credited at a cell it did not play |
| 11 | The side choice matters for this witness (primary) | Confirmation round, fresh launches, only after check 10 passes and the owner names this contrast | W against M, 16 per arm (8 per case); pooled two-sided Fisher p < 0.05; Newcombe interval (`exact_stats.newcombe`) reported; per-case counts descriptive | Offline, built (`test_wh3_exact_stats.py`): Fisher's tea table (3 of 4 against 1 of 4) gives 0.486 two-sided, and a one-sided version (0.243) fails |
| 12 | Human win | `manual_demo record --scenario ksl-nor-lines-a-v1`, then b; neither has `reserve` or `custom`, so the observer session accepts them | One engine win per case; every attempt kept; pauses labelled from video. The recorder's handover is itself unverified | A recorder run whose setup readback fails must stop |

Primary round plan (check 11):
- 32 fresh launches, W and M by two cases by 8, in a pre-drawn order of blocks of four (one of each
  arm and case per block), with neutral job names and the arm and case kept only in the private
  plan record. The plan builder (portfolio S6) is not built.
- A launch with no engine outcome is not an attempt and gets one new launch in a new plan. That is
  Cannae row 3's agreed rule, applied here by extension, which the owner has not agreed for this
  battle. There is no early stop.
- Exact power (`exact_stats.plan_power`, 16 per arm): 0.740 if the arms truly win 20% and 70%,
  0.786 for 10% and 60%, 0.962 for 0% and 50%. At 10 per arm the same gaps give 0.426, 0.474 and
  0.623. To pass, W must win at least 5 of 16 if M wins 0, 9 if M wins 2, 11 if M wins 4 and 15 if
  M wins 8.
- C is exploratory unless the owner names a procedure fixed in advance.
- A pass shows that, for this witness at 5 s / 5 s in this version, sending the reserve and the
  Lancers to the costlier relief group won more often than sending them to the group with more men.
  M picks the lighter group by construction, so a pass says nothing about models and nothing about
  whether a controller can read the main effort from public fields.

## Live stages

All $0. Game time starts only when the owner names a stage; the stages run one battle at a time,
and a launch takes about 20 minutes (the 1,200 s timer plus loading; the design's estimate).

| Stage | What runs | Launches and game time | What it can establish |
|---|---|---|---|
| 0 | Offline. Done at `e918091`: declarations, W, M and C, the ablation helper, statistics and evidence helpers, their tests. Built since: the evaluator-only record (`f3fec92`) and the fixture boundary test (`test_wh3_eval_boundary.py`). Still to build: the replay readers for checks 2-4 with their synthetic plants, the boundary test on recorded first observations, the plan builder, and F and N if the owner wants them | None | That the code does what its tests say |
| 1a | Lobby-only readback (check 0), shared with the other new battles: `scripts/wh3_lobby_readback.py` writes the step files (it launches nothing) and `twwarhammer3 menu --steps` sends them; no live lobby has run them | One game session, minutes, no battle | Whether the Kislev and Norsca cards and the banner recruit; a Norsca failure starts the Greenskin version and a Kislev failure goes to the owner (see risks) |
| 1b | One `hold` launch of case a | 1, about 20 min | Checks 1 and 5, the bearing offset, the funds charge |
| 1c | Five more `hold` launches, 3 per case in all | 5, about 1.7 h, plus about 2 per restage | Checks 2-4 at the provisional window, Norsca travel times, the hold floor. G or the relief is restaged in 15 m steps as development versions until checks 2 and 4 pass |
| 2 | Probe, with one spare | 1-2, about 30 min | Check 7 and the window; then checks 2-4 are re-read on the stage 1 replays |
| 3a | Shortcut screen: `attack_nearest`, `rush_nearest`, `skills`, `Evade`, `Concentrate`, C and M, cases alternated (`hold` comes from stage 1) | 7, about 2.3 h | Check 9 |
| 3b | Frozen gate (check 10), plus W at 10 s / 10 s once per case as development evidence | At most 5 plus 2, about 2.3 h | Check 10 |
| 3c | Ladder, only after a gate passes: harder is enemy rank +2 on all 12 units, easier is player rank +2; one factor a step, at most three steps. Each step reruns W twice per case and every shortcut once, and re-reads checks 2-4. The hardest step where W won at least 3 of 4 and no shortcut won is frozen and gets its own gate | About 11 per step (3.7 h), then at most 5 for the frozen step's gate | Check 9 and 10 at each step |
| 4 | The owner's demonstration, one engine win per case | Owner's time | Check 12 |
| 5 | Confirmation round, only if the owner names it | 32, about 8-11 h | Check 11 |
| 6 | Model pilot, if wanted | Paid, the owner's budget | Exploratory model results only |

JUDGEMENT: Lines ladder — Claude, 2026-11-08 (two-front design): stage 3c's knob (enemy rank +2
on all 12 units, player rank +2 for easier), at most three steps, frozen at the hardest step where
W won at least 3 of 4 and no shortcut won. Adding units changes the cue; the difficulty rests on it.

Through stage 3b that is about 21-22 launches and 7 hours of game time before any restage or
ladder step.

## Risks

| Risk | Stage | Response |
|---|---|---|
| Norsca cards or the banner do not recruit | 1a | A Greenskin enemy (Orc Boyz, Goblin Spearmen, Arrer Boyz, Big 'Uns, Black Orcs, Trolls) as a new version, starting stage 1 again |
| Kislev cards do not recruit (most likely the Tzar Guard or the Winged Lancers, which no played scenario has recruited) | 1a | The player roster changes, which is the owner's choice (for example question 3 (b)); the new version starts stage 1 again |
| The posted reserve rarely fights: an enemy 3 m in front of a sector regiment's centre is about 41 m from the Tzar Guard's post, just past the 40 m leash, so W's posted reserve may fight no more than C's until a regiment gives way (the build's implementer found this). W still differs from C in the Lancers' ride round the line's end, and from M in the side they ride to | 3 | Record it; a different leash is a new witness version and needs the owner, since the values are marked |
| The groups merge, arrive staggered or go round the line ends | 1c (checks 2-4) | Restage in 15 m steps; a scripted hold (shared with Haengju's waves work) only if staging cannot fix it |
| G arrives well before the relief | 1c | Move G 15 m at a time |
| `Concentrate`, `skills` or `Evade` wins | 3a | Keep the win; narrow the label; the owner decides whether to keep the battle |
| W never wins, or fails the gate | 3b | Easier ladder steps; with no win the battle stays unwitnessed and no round runs |
| M wins as often as W | 5 | The side choice does not matter for this script here; the battle is not labelled with the decision |
| The terrain under the two slots favours one side | 1c, 5 | Per-case counts are reported beside the pooled test |
| A ladder step removes the premise (contacts stop coinciding) | 3c | Checks 2-4 are re-read at every step |
| No rear contact ever lands | 2-3 | E2 stays untested |
| Kislev hybrid infantry skirmish or shoot instead of holding | 2-3 | Record it; the witness sets skirmish off, and check 7 reads the settings back |
| One launch per case settles nothing (the Cannae windows) | All | Only check 11 makes a claim |

## Decisions for owner review

Three questions, with the recommendation first; the build at `e918091` used the recommended answer
to each.

1. **Keep this battle under a siege-set name?** (a) Keep it as a Land battle labelled "a two-front
   defence after Alesia's last day" (recommended): no WH3 siege mode puts a garrison inside the
   besieger's lines without about six untested engine behaviours, and this is the set's one
   powered test of reserve allocation. (b) Drop it from the siege set, because it does not play in
   WH3's siege mode.
2. **The primary contrast.** (a) W against M at 16 per arm (recommended): 32 launches, about 8-11 h
   of $0 game time, exact power 0.740 for 20% against 70%. (b) 10 per arm, power 0.426-0.623.
   (c) W against C, which asks whether committing the reserve matters at all. (d) Paired
   checkpoint branches compared with exact McNemar (portfolio S11), which first needs a declared
   checkpoint check case for this map and army.
3. **Factions.** (a) Kislev against lordless Norsca (recommended): Norsca has fought in the game
   only as an autogenerated army, and a Greenskin enemy is the fallback version if its cards fail.
   (b) Empire against Greenskins: every card recruited before, but the same factions as two suite
   battles on the same map.

Other open choices are marked above: the separate multi-face siege, the settings, forces, enemy
lord, banner, layout, reserve facing, briefing, withheld names, deciding checks and ladder on this
page, and the witness rules, side weights, relief membership and rear point in `lines.py`.

## Sources

Read on 2026-11-08 for the design; Caesar VII.75-90, Wikipedia and Livius were read again for this
page, VII.63-74 only for the design. They are listed in
[references](../references.md#two-front-defence-after-alesia-2026-11-08).
The history guides the design and is no evidence about the engine.

- Caesar, *Gallic War* VII.63-74 and VII.75-90, Loeb 1917 translation on
  [LacusCurtius](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Caesar/Gallic_War/7G*.html)
  (VII.63-74 is the page ending `7F*.html`). Primary source in translation: the works (69, 72,
  74), 80,000 in the town (71), the relief army (76), the north camp and its ground (83), the sally
  (84, 86), the reserves and the cavalry (86-87), the outcome (88) and the surrender (89).
- [Wikipedia, Battle of Alesia](https://en.wikipedia.org/wiki/Battle_of_Alesia), first 100,000 of
  129,350 characters. Secondary: Roman and Gallic strengths with Dodge, Keppie, Plutarch, Strabo
  and Delbrück; "probably an exaggeration"; the lines "not continuous".
- [Livius.org, Alesia (52 BCE)](https://www.livius.org/articles/battle/alesia-52-bce/).
  Secondary: twelve legions, 39 cohorts, about 15 km of lines, the northwest gap, the "very
  artful" narrative and the doubted surrender.
- Repo: `runs/siege-evals-20261108/final-alesia.md` (the design, with its judges' corrections) and
  `portfolio.md` (overlaps, shared rules and the corrections applied here: the claim counted once,
  the witness's cost asymmetry, check 2 run in stage 1 and recomputed after stage 2, the cards in
  the lobby-only readback, and the 4-of-5 gate in place of the design's 3 of 4).
- Recorded evidence: `runs/cannae-window-1/a-evade-01/episode-0000/trace.jsonl` (the Taurox grid);
  `runs/twwarhammer3/battle/skills-v1.1-random-a-20261013` (the Norsca army);
  `runs/twwarhammer3/battle/bench-b12-kislev-reserves-20261016/cards_slot0.txt` (Kislev cards); the
  register rows for `coord-breakout`, `coord-two-fronts` and `ksl-reserves-survival`.
- Game data, read-only: `main_units_tables` through `scripts/wh3_db.py` with RPFM's WH3 schema
  (`runs/cannae-build/research/schema_wh3.ron`); nothing was written.
