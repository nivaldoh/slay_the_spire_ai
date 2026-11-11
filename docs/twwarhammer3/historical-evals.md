# Evaluation battles adapted from history

Overview, written 2026-11-09 (Claude). **None of the four new battles has been launched, and
everything on this page is unverified** under the
[hard rule](../../AGENTS.md#verification-hard-rule). On 2026-11-08 the owner asked that good battle
ideas be implemented with an evaluation method that is "good (in a concrete, legitimate way)". The
owner's answers that day said to try building the five sieges the question listed (Haengju, Malta
1565, Belgrade 1456, Alesia and Izmail) while making sure they are adapted well to WH3's game
modes, and to play them only when the owner says so ("Build now, game when I say",
[owner direction](../owner-direction.md)). Four new battles were built offline, at `e918091` and
`f3fec92`; the three Cannae battles came earlier. For each battle this page gives the history it
adapts, the WH3 mode it uses and why, and the one decision it claims. It then explains why Malta was
not built, lists the method rules the set shares, gives the order of the live stages, and ends with
the owner's open choices. The battle pages hold the details. The designs, Claude's review of the set
(`portfolio.md`) and the build records are in `runs/siege-evals-20261108/`, which Git ignores. Each
history guides its design and is no evidence about the engine; the sources are in
[references](../references.md#historical-siege-evaluations-2026-11-08).

## The battles

| Battle | Page | WH3 mode and role | Scenarios | The one claim | State |
|---|---|---|---|---|---|
| Cannae, 216 BCE | [cannae-eval.md](cannae-eval.md) | Land; the player defends | `emp-envelopment-*` | None by a powered contrast | Built and played since 2026-11-05 (windows 1 and 2: 22 launches) |
| Haengju, 1593 | [haengju-eval.md](haengju-eval.md) | Siege; the player defends against divisions released in turn | `cth-emp-siege-a-v1`, `cth-emp-siege-a-all-v1`, the map screen `cth-emp-siege-a-all-gates-v1` | Fire across divisions | Built offline at `f3fec92` |
| Belgrade, 1456 | [camp-eval.md](camp-eval.md) | Land; the player attacks a camp | `emp-chd-camp-v1` | Guns or cover | Built offline at `e918091` |
| Alesia, 52 BCE | [lines-eval.md](lines-eval.md) | Land; the player defends two lines back to back | `ksl-nor-lines-a-v1`, `-b-v1` | The main effort | Built offline at `e918091` |
| Izmail, 1790 | [escalade-eval.md](escalade-eval.md) | Siege; the player attacks | `ksl-emp-siege-a-v1` | Spread or concentrate | Built offline at `f3fec92` |

Several decision families appear in more than one design and in older battles. The review counted
each family once and gave its claim to one battle. Reserve allocation between fronts or at a breach
appears five times and is claimed only in Alesia, because its design was the only one that already
planned 16 launches per arm (portfolio overlaps); every battle page now recommends 16 per arm for
its round. Alesia's P1 moves the reserve and the Lancers together: each arm sends both to the side
it chooses, so a P1 result does not separate the reserve from where the Lancers' rear charge lands.
The strike force's choice between guns and troops already engaged is claimed only in
Belgrade. Falling back to inner works is claimed by none of the new battles, because the existing
siege family carries it in its brief ("Trade outer territory for time", `chd-reserve-grn-siege` and
its suite copy `coord-siege`). When a mounted force commits stays descriptive in every battle: on
2026-11-05 the owner said "I actually don't think the problem of studying timing is that interesting
for now". The review counts both timing and rear charges once, under Cannae A, where no contrast
tests them. Rear charges are exploratory only as a claim of their own, since Alesia's P1 arms
include one, and commander exposure stays exploratory in the new battles.

JUDGEMENT: Claim assignment — Claude, 2026-11-08 (portfolio overlaps): reserve allocation claimed
only in Alesia, strike target only in Belgrade, falling back and commit timing nowhere. Other
assignments change which label each round can grant; each battle's one claim rests on it.

### Cannae A, B and C

Polybius describes Hannibal's army at Cannae in 216 BCE holding an advanced, curved centre while its
flanking infantry turned inward and its cavalry, after winning on one wing, came round onto the
Roman infantry's rear (*Histories* 3.113-116). Cannae was fought in the open, so its page uses a
Land battle in which the controller holds the enveloping side and defends against native AI, Empire
against Empire on Taurox; it compares no other mode. A is the recognizable pattern, B adds a
scripted reserve whose commitment changes between launches, and C splits one army among agents under
limited communication. No Cannae battle claims a decision by a powered contrast. Two of its checks
are agreed ([agreed checks](../agreed-checks.md)): a fixed rule's sufficiency on the harder B, where
`CentreSupport` won 5 of 8, so sufficiency is not shown; and one launch of each shortcut, all five
lost. No A v2 battle shows Knights hitting the rear of an unbroken regiment that then collapses
([window 2](cannae-eval.md#window-2-results-2026-11-05)).

### Haengju, 1593: a siege defence

On 14 March 1593 Gwon Yul's garrison, about 2,300 men by Hawley's count, held the hill fort of
Haengju behind two palisade lines against about 30,000 Japanese attackers, who came on in successive
divisions from dawn until dusk. The battle is a siege that the player defends against native AI on
Helmgart, with a Grand Cathay garrison against Empire divisions. WH3's siege rules, as the game's
help text gives them, carry most of the structure: a wall with one gate, towers that serve whoever
holds their capture point, defender tickets that fall once the Key Building is lost (in 4 of the 19
recorded `chd-reserve-grn-siege` family battles on Helmgart, as the design counted them), and a
defender who wins at the timer, which no siege in the register has reached. The minor settlement has
no tickets, and its objective text counts any surviving unit at the timer as a win, so running away
could pass; a conquest battle drops the walls. Native AI attacks with its whole army, and on
Helmgart staggering the divisions by distance alone separates their arrivals by at most about 50 s
(the design's estimate). A script therefore holds three of the four divisions and releases them at
150, 300 and 450 s, or a division at once when one of its units loses men or reads under missile
attack (reserve profile version 3, which rests on JUDGEMENT docs/twwarhammer3/haengju-eval.md
Division schedule). The briefing says only "The attacking army is drawn up in several divisions,
which may attack at different times." The witness `WallWitness` and five controls are in
`battle/wall_defence.py`, the readings in `battle/wall_readings.py`.

Its one claim is fire across divisions: `WallWitness` turns fire at will on for the archers,
crossbowmen, rockets and cannon only while a visible enemy that is not routing stands within 60 m of
the wall line or inside it, and off again otherwise, which is the design's way of rationing shots
between divisions. `WFire` is the witness with that rule removed. The claim holds only if ammunition
runs short across the divisions, which stage 1 measures under `hold`. The reserve at a breach
(`WReserve`) and falling back to the Key Building (`WNoFallback`) stay exploratory. Divisions in
turn against all at once (`cth-emp-siege-a-all-v1`) checks that the script changes the battle and
claims no decision. Stage 1 is also the set's first test of units teleported into position in a
siege, since the held divisions are placed that way.

### Belgrade, 1456: the camp attack

On 22 July 1456, the day after the Ottoman assault on Belgrade failed, crusader levies began
fighting outside the walls, the Ottoman cavalry left the gun positions to fight them, and Hunyadi's
attack took the guns, by the Hungarian Wikipedia account; the English article says the levies' fight
began without orders. The battle is a Land battle in which the player attacks a native AI defender
that wins at the timer: Empire levies and knights against Chaos Dwarf war machines and their cover
on Taurox. The 21 July break-in as a siege defence would repeat Haengju's breach decision, and the
recorded Helmgart baselines contradict its premise that attackers enter a few at a time; WH3 has no
naval battle for the 14 July river fight ([camp-eval.md](camp-eval.md#why-this-wh3-game-mode)).

Its one claim is D1, guns or cover. Once a cover unit has been flagged in melee within 30 m of a
levy for 10 s, `CampStrike` sends the mounted group at the war machines first and `CampSupport` at
the cover units fighting the levies (`battle/camp.py`). When the mounted group starts
(`CampStrikeNow`, `CampStrikeFixed`) and the death of either lord stay descriptive.

### Alesia, 52 BCE: two fronts

In 52 BCE Caesar's army besieging Alesia was attacked on the same day by the garrison from inside
its works and by a Gallic relief army from outside, and by Caesar's account the Romans held by
reading where the main attack fell and sending reserves and cavalry there (*Gallic War* VII.83-88).
The battle is a Land battle in which the player defends two lines back to back against three native
AI groups, Kislev against lordless Norsca on Taurox, in two mirror cases. No WH3 siege layout puts a
garrison inside the besieger's lines without about six engine behaviours nobody has tried, and a
native siege on several faces has no garrison front, so the Land defence keeps the decision and
drops the works ([lines-eval.md](lines-eval.md#choosing-the-wh3-game-mode)). WH3 does not treat it
as a siege, and that page asks the owner whether it belongs in the set.

Its one claim is P1, the main effort. `LinesWitness` sends the reserve and the Lancers to the side
whose relief units cost more, and `LinesByMen` to the side with more men (`battle/lines.py`). The
witness weighs units by a cost table no model sees, so a pass would say nothing about whether a
controller can read the main effort from public fields. The inner front, the counterstroke, the
commander and reading the attack before contact (E1-E4) stay exploratory.

### Izmail, 1790: the escalade

In December 1790 Suvorov's army of about 31,000 stormed the Ottoman fortress of Izmail on the Danube
with ladders, in nine columns that attacked on one signal, against a garrison the official count put
at 35,000; Osipovsky (2026) concludes the armed defenders were most likely 12,000-15,000, so the
clear disadvantage was the rampart and the ditch, and the numbers are contested. The battle is a
siege in which the player attacks a native AI garrison on Helmgart: Kislev with one ram against an
Empire garrison. The engine produces the problem without a script: a continuous wall with one gate,
ladders for infantry, cavalry that cannot climb, and an objective text that makes the defender the
winner at the timer, which no siege has been seen to reach. The minor settlement has no walls, and
in three recorded launches the engine placed its defenders 650-750 m from the Key Building; a team
of wing captains waits until the single-controller battle is understood. In the one earlier siege
the player attacked, a smoke run stopped by hand at 730 s, our units stayed idle outside the wall
([battle types](battle-types.md#the-player-attacking-a-siege)). The siege-attack interface built at
`f3fec92` for scenarios that opt in with `siege_assault` (the fortification list, `on_wall`, and the
`besiege` and `attack_building` orders) has never run in a game.

Its one claim is D1, spread or concentrate. `Escalade` sends three groups over three wall sectors at
once, and `Concentrate` moves the two outer groups onto the wall pieces nearest `c5` and `c4` in the
gate recess, beside the centre group (`battle/escalade.py`). It is the set's only decision in a
siege the player attacks. Holding the Lancers until the gate falls (`CavalryEarly` against the
witness, the design's D2) is a timing choice and stays descriptive, as do the synchronised start,
the reserve and suppressing fire.

## Malta 1565, designed and not built

On 7 August 1565, during the Great Siege of Malta, the Ottoman assault on Fort St Michael and Birgu
broke off when about a hundred horsemen riding out of Mdina under Vincenzo Anastagi struck the
poorly guarded camp, and the attackers took the raid for the relief army (Wikipedia and an
unattributed garrison diary). The design made it a siege defence on Gaean Vale in which two Empire
Knights units start outside the walls and choose between the Chaos Dwarf battery and the rear of the
assault (`final-malta.md`).

The owner's 2026-11-08 answer listed Malta among the sieges to try building, on the condition that
each is adapted well to WH3's game modes. Claude's review left it unbuilt for two reasons. Its main
decision is Belgrade's, with the same factions and the same unit keys
(`wh_main_emp_cav_empire_knights`, `wh3_dlc23_chd_veh_magma_cannon`,
`wh3_dlc23_chd_cav_hobgoblin_wolf_raiders_spears`, `wh3_dlc23_chd_cha_overseer`). Its adaptation to
the siege mode also rested on three engine behaviours nobody has observed: a unit teleported outside
the walls in a siege, Chaos Dwarfs in the AI slot, and a siege won at the timer. Belgrade needs only
the second, which the lobby-only readback settles in minutes. Malta's two-front premise came from
one random battle, in which the engine had split the attackers by unit class. It could come back as
a siege variant with another faction pairing once Haengju's stage 1 shows that teleporting works in
a siege, a siege has been seen to end at the timer, and Belgrade's round shows that the
strike-target decision matters.

JUDGEMENT: Malta not built — Claude, 2026-11-08 (portfolio): Malta 1565 stays a design and
Belgrade carries the strike-target decision. Building Malta instead puts that decision in a
siege on three unobserved engine behaviours; the set's coverage rests on it.

## Method rules the set shares

Claude's review of the five designs proposed these rules for the whole set. The owner has agreed
none of them, and none is in [agreed checks](../agreed-checks.md). Each battle page fixes its own
contrast, gate cell and check counts under its deciding-checks marker, so the values in rules 1-3
rest on JUDGEMENT docs/twwarhammer3/camp-eval.md Camp deciding checks,
docs/twwarhammer3/lines-eval.md Lines deciding checks, docs/twwarhammer3/haengju-eval.md Deciding
checks draft and docs/twwarhammer3/escalade-eval.md Escalade deciding checks. The marker below
covers only the choice to use one set of rules for every new battle.

JUDGEMENT: Shared method rules — Claude, 2026-11-08 (portfolio): rules 1-3 apply alike to every new
battle in place of each design's own; the values sit under each page's marker. Rules chosen
battle by battle let a label mean different things per battle; comparing labels rests on it.

1. **One primary contrast per battle.** A battle compares its witness with one ablation that changes
   a single rule, on fresh separate launches whose number is fixed in advance, and decides by a
   two-sided Fisher exact test at p < 0.05 with a Newcombe interval
   ([`battle/exact_stats.py`](../../src/twwarhammer3/battle/exact_stats.py)). Anything else is
   exploratory unless the owner names a procedure fixed in advance. The designs had used Holm over
   two contrasts, a fixed-order rule they called Holm, or a single primary. A pass shows that the
   rule mattered for that witness at that timing on that version, and it says nothing about models.

   Each round's exact power is printed before it runs (`plan_power`). A round runs only after the
   witness has passed its gate, on a version the pages' ladders make as hard as the witness still
   wins, so its true rate is more likely 0.7-0.9 than the low rates the battle pages' power tables
   assume. The grid gives the power for a witness winning 0.7, 0.8 or 0.9 of launches against an
   ablation 30, 40 or 50 points lower (recomputed for this page; `test_wh3_exact_stats.py` checks
   it against `plan_power`):

   | Launches per arm | Witness rate | 30-point drop | 40-point drop | 50-point drop |
   |---|---|---|---|---|
   | 16 | 0.7 | 0.269 | 0.496 | 0.740 |
   | 16 | 0.8 | 0.281 | 0.505 | 0.740 |
   | 16 | 0.9 | 0.359 | 0.581 | 0.786 |
   | 24 | 0.7 | 0.471 | 0.750 | 0.931 |
   | 24 | 0.8 | 0.493 | 0.760 | 0.931 |
   | 24 | 0.9 | 0.602 | 0.834 | 0.955 |
   | 32 | 0.7 | 0.619 | 0.879 | 0.983 |
   | 32 | 0.8 | 0.644 | 0.887 | 0.983 |
   | 32 | 0.9 | 0.748 | 0.935 | 0.991 |

   The fewest launches per arm that reach 80% power are 44 for 0.8 against 0.5, 27 for 0.8 against
   0.4, 48 for 0.7 against 0.4 and 23 for 0.9 against 0.5. At the pages' 16 per arm, a 30-point
   drop is found 0.269-0.359 of the time.

   The gate's pass chance is a separate line and is not multiplied into these powers: the 4-of-5
   gate of rule 2 passes a witness that wins 0.7, 0.8 or 0.9 of launches 0.528, 0.737 or 0.919 of
   the time (`gate_pass`).

   How to read a round. A result that does not pass reads "not shown at this power", never "does
   not matter". A pass with the witness ahead reads that the decision matters in the direction the
   battle page predicts. A pass with the ablation ahead reads "the decision matters and the
   witness's rule is the worse choice here"; whether it earns a label is the owner's call. Labels
   are per battle and are never pooled across the set. A set-level false-pass figure uses the
   test's exact sizes: at 16 per arm, a battle whose rule changes nothing passes at most 0.0202 of
   the time (0.0101 with the witness ahead), so with the four battles' launches independent and no
   rule mattering, the chance that at least one battle passes is at most 0.079, and 0.040 in the
   witness's favour.

   How a round runs. The plan builder (portfolio S6, not built) draws the order in blocks. A block
   is one launch of each arm (in Alesia, each arm and case), which is a time block in the sense of
   [guideline 4.2](evaluation-guidelines.md#42-balance-who-plays-first-and-when) ("a night, or one
   pass of the plan through every arm"), and each block runs whole within one night. Each job
   records its Steam build in `environment.json` (`game.steam_build_id`). When a block's build
   differs from that of the round's first block, the round pauses at the end of that block and the
   owner is told. The comparison is with the round's own build, not the pin: if the owner keeps the
   pin while Steam moves on, every block repeats the same pin warning, which `doctor` and each job
   still report to the owner. A build difference never blocks a launch
   ([AGENTS.md](../../AGENTS.md)), and
   [guideline 4.4](evaluation-guidelines.md#44-compare-only-matching-cells-and-recheck-references-after-a-change)
   never pools launches across builds, so what follows is the owner's call. An admission holds
   only for its build
   ([guideline 2.7](evaluation-guidelines.md#27-admit-a-card-only-from-a-frozen-confirmation-round)),
   so before the round the game build `doctor` reports is compared with the gate's recorded build,
   and a change means the gate is rerun on the new build.

   JUDGEMENT?: Round blocks — Claude, 2026-11-09 (second look S9): a block is one launch per arm,
   run whole in one night, pausing at its end if its recorded build differs from the first block's.
   Blocks split across nights compare arms on different nights; every round plan rests on it.

   Replacements follow
   [guideline 5.2](evaluation-guidelines.md#52-freeze-how-every-trial-is-scored)'s table, in place
   of portfolio S6's "a launch with no engine outcome gets one new launch". A controller
   exception is a loss. Only a failed setup check or lobby readback, a game silent before the wall
   cap, an operator stop and an infrastructure stop of the waves check (`reserve.check_waves`) are
   replaced by a new launch. The builder prints the replacements per arm, and when the arms'
   counts differ by 2 or more the round reports
   [guideline 5.3](evaluation-guidelines.md#53-give-every-planned-trial-one-visible-disposition)'s
   range from all-lost to all-won for the replaced launches.

2. **A frozen witness gate before any round.** The witness's code is frozen, and it plays fresh
   launches at 5 s added order age and a 5 s decision interval. It passes at 4 of 5, stopping at the
   4th win or the 2nd loss, which passes a 50% witness 0.1875 of the time and fails an 80% one 0.263
   (`gate_pass`). A failed gate is never rerun unchanged; the version is revised or made easier and
   gets a new gate
   ([guideline 2.7](evaluation-guidelines.md#27-admit-a-card-only-from-a-frozen-confirmation-round)).

3. **Premise and opportunity checks print their error rates.** Before a round, each battle checks
   that its premise holds, such as the camp's guns staying and firing or the three groups reaching
   the lines together, and that its decision's cue occurs; stage 2 probes check that orders reach
   their effects. A check of 3 of 3 launches passes a premise that holds half the time 0.125 of the
   time and fails one that holds 80% of the time 0.488. Belgrade's cue check of 6 of 8 passes a 50%
   cue 0.145 of the time and fails an 80% one 0.203. An effect a probe sees once shows only that it
   can happen. The pages screen shortcuts and ladder steps with one launch per control, and one
   launch catches a shortcut that wins 30% of the time with chance 0.30 and one that wins half the
   time with chance 0.50; three launches catch them 0.657 and 0.875 of the time, and 0 wins in 3
   bounds the shortcut's rate only below 0.63 (exact one-sided 95% bound). A freeze that rests on
   single losses carries this error.

4. **Contact and breach.** Contact is the engine's melee flag on a unit with men left, never the
   distance between centres: in the 2026-10-14 attack smoke 6 friendly-enemy pairs stood within 40 m
   in 364 readings, and none carried the flag. A gate is breached when its public hp reads 0 or
   less, whatever `destroyed` says, because two recorded gates read hp 0 with `destroyed` false to
   the end of their battles. Whether hp 0 lets units through is unverified. Both rules are in
   [`battle/evidence_rules.py`](../../src/twwarhammer3/battle/evidence_rules.py) and rest on
   JUDGEMENT src/twwarhammer3/battle/evidence_rules.py Contact rule and Breach rule. Units are
   chosen by type key, because the Magma Cannon reads class `missile_chariot` and the Bull Centaurs
   read `infantry`.
5. **The evaluator-only private record.** A scenario with `"private_record": true` makes the mod
   write every unit of both sides, hidden enemies included, once per engine second; `play` copies it
   to the episode's `private.jsonl`, and no policy input carries it. Every new declaration opts in:
   the three siege declarations at `f3fec92` (and the Eagle Gate screen, which inherits it), and
   `emp-chd-camp-v1`, `ksl-nor-lines-a-v1` and `ksl-nor-lines-b-v1` after it. Belgrade's camp
   premise needs enemy ammunition, which only this record holds, and Alesia's group readings need
   it if enemies leave sight; neither battle's readers of it are built. The fields and its use in
   scored battles rest on JUDGEMENT? src/twwarhammer3/battle/capture.py Private record fields and
   Private record in scored battles. No game has written it, and its CPU cost per second is
   unmeasured.
6. **Neutral names.** Scenario names carry factions and a version, and job names are neutral and
   numbered, such as `lines-r1-017`, because the observation carries `job`. No new declaration has a
   `benchmark` key, which `play.public` would copy into the mode a controller sees. Every new
   declaration lists `withheld` words (the land ones, added after `f3fec92`, share one list of the
   Belgrade and Alesia names), and `play` and the recorder refuse a job name that holds one at a
   word start (`setup.check_job`), so `run2haengju` still passes.
   `test_wh3_land_eval_declarations.py` checks the land declarations' own text against their list
   and the refusal of jobs such as `belgrade-camp-r1`. Each battle marks its own choice, so
   this rests on JUDGEMENT docs/twwarhammer3/camp-eval.md Camp presentation,
   docs/twwarhammer3/lines-eval.md Lines briefing, docs/twwarhammer3/haengju-eval.md Public
   presentation, and the withheld lists' JUDGEMENT? markers (Withheld names in lines-eval.md,
   Withheld words in test_wh3_waves.py, Siege attack withheld names in test_wh3_siege_assault.py).
   The plan builder that would name a round's jobs (portfolio S6) is not built.
7. **The siege orders for models.** The owner approved "models using siege orders" on 2026-11-09,
   and the `llm.py` change from branch `izmail-llm-orders` landed as `llm`/`llm_rules` v23
   ([log](log.md#2026-11-09-prompt-v23-siege-orders-for-the-llm-controller)). In a siege attack
   with `siege_assault`, `llm` and `llm_rules` read the fortification list, a paragraph on
   `besiege` and `attack_building` and a reply schema that carries both. Also in v23, revised on
   2026-11-09 before any battle ran on it: a unit's last accepted siege order in place of "no
   order", and each ticket count's change since the previous decision; the mod leaves the building
   slots out of such a battle. The `commander` and the team controllers cannot use the orders.
   The `commander` and every team member (`team_llm_rules`
   members and the `llm` or `llm_rules` leaves of a configured `team`) read the fortification list
   and the siege vehicles as facts, and a `local_team` member's view has no fortification list.
   None of their reply schemas has the orders, and a team member's siege order is refused.
   The edit moved `llm.py`'s source hash, on which every `llm` controller's cards pool
   ([controllers](controllers.md)); every battle without `siege_assault` sends the same request
   as v22. No battle has run on v23.

   The two model controllers read different system prompts. `llm` reads
   `configs/twwarhammer3/system_prompt.md`, whose How to fight section prescribes one arm of
   several contrasts here. Its line 34 ("until the enemy infantry reaches your line, every shooter
   fires at it") is Haengju D1's `WFire` arm. Its line 29 ("a unit that is not fighting is wasted
   and a withdrawal only delays defeat") is false in the defences the player wins at the timer,
   Haengju and Alesia. Its line 35 sends cavalry at "the rear of an enemy fighting your infantry,
   or an enemy missile unit or artillery crew with no melee unit near it", which states both
   options of Belgrade D1 and a rule for choosing between them. `llm_rules` reads
   `rules_prompt.md`, which has no tactics. The review recommends that model pilots on these
   battles use `llm_rules`, or that an `llm` result be reported as a tips arm, as
   [benchmark.md](benchmark.md) treats that advice ("Arms that differ in advice").

   JUDGEMENT?: Pilot prompt — Claude, 2026-11-09 (second look seat-3): model pilots use llm_rules,
   or an llm result is reported as a tips arm. Reporting an llm pilot as the model alone
   credits How to fight's arms to it; every model pilot's reading rests on it.

8. **Game time.** No game runs until the owner names a window. Every live stage is $0 in API calls
   until a model pilot, which needs the owner's budget and arms.

## What a run needs

| Item | What the set uses |
|---|---|
| Game | Total War: WARHAMMER III on Steam on Windows, driven from WSL ([AGENTS.md](../../AGENTS.md#architecture)) |
| Patch and build | 9.0.5, Steam build 26403568, pinned in `engine/runtime.py`; another build warns and is recorded but never blocks |
| Mod pack | The pack the checkout builds from `src/twwarhammer3/mod/`; its hash is `engine/worker.pack_sha256()`, and each job's `manifest.json` records it under `deployment.pack`. Its Lua changed at `f3fec92` |
| Haengju content | `wh_main` (the Empire divisions), `wh3_main` (the Grand Cathay garrison) |
| Belgrade content | `wh_main` (Empire knights, Reiksguard, General, Warrior Priest), `wh_dlc04` (Flagellants, Free Company), `wh3_dlc23` (every Chaos Dwarf unit) |
| Alesia content | `wh_main` (the Norsca Marauders and Marauder Horsemen), `wh_dlc08` (the other Norsca units; the faction is `wh_dlc08_nor_norsca`), `wh3_main` (the Kislev army) |
| Izmail content | `wh_main` (the Empire garrison), `wh3_main` (the Kislev army) |

The content rows are each declaration's `content` field, the set of its roster key prefixes;
`test_wh3_land_eval_declarations.py` checks the field against the rosters, which shows the two
agree and nothing about what an account owns. Which pack each prefix needs is unverified: `wh_main`
should be the first game's races, `wh_dlc04` The Grim and the Grave, `wh_dlc08` Norsca, `wh3_main`
the third game and `wh3_dlc23` Forge of the Chaos Dwarfs. A missing pack should fail at readiness
through `setup.army_checks`: a card that cannot be recruited is skipped silently, as the Wood Elf
probe found ([log](log.md#2026-10-16-harness-b12-and-distinct-scenario-families)), so the lobby's
unit count comes up short and the required check stops the job before the battle. No run has
shown this with a missing pack.

## Live order

JUDGEMENT: Live order — Claude, 2026-11-08 (portfolio build order): one lobby-only readback, then
stage 1 one battle at a time: camp, two fronts, Haengju, Izmail. Another order changes what each
window can show first; the live schedule rests on it.

The first step is a lobby-only readback of every new roster, run in one game session with no battle:
each scenario's lobby steps without the Start click, then `setup.army_checks`.
`scripts/wh3_lobby_readback.py` writes those step files for the four battles' six declarations and
launches nothing; the owner starts the game with `twwarhammer3 launch` and sends each file with
`twwarhammer3 menu --steps`. The first live readbacks are recorded below. The readback settles the roster
questions before any battle. After it, stage 1 runs one battle at a time, smallest first, which
here means the battle that needs the fewest untried engine behaviours: the two Land battles use only
existing orders, Haengju adds the scripted hold and teleporting in a siege, and Izmail adds the new
siege orders. Each stage 1 reports only construction, premise and opportunity readings, and Izmail's
step adds its order probes. Shortcut screens, gates, the owner's demonstrations and any round come
later, battle by battle, each in a window the owner names. The mod's Lua changed at `f3fec92`, so
every launch from then on, older battles included, carries a new pack hash and a separate card setup
identity.

### First lobby readbacks, 2026-11-10

In the owner's two-hour window, two lobby sessions at `2105a9c`, build 26403568 and pack
`bfe8fb3de86aba5a17b1df5e272fa25d85e29053f93bacadd44f086e71e6a571`, started no battle.
Belgrade's file stopped at step 48: the engine refused `wh_dlc04_emp_inf_flagellants_0`
after five successful recruit commands. This does not identify the refusal's cause or
establish a complete army, mount, enemy or equipment readback. The original failure stays.
A separate session checked the independent remaining rosters without retrying Belgrade:

| File | Completed steps | Final player/enemy unit counts | Equipment readback |
|---|---:|---:|---|
| Alesia case a | 127 | 12 / 12 | No siege equipment required |
| Haengju all-at-once | 156 | 10 / 18 | Attacker slot 1 empty |
| Izmail | 157 | 13 / 12 | Player slot 0: one `ksl_battering_ram`, no tower |

Each completed file read exact roster keys and rank multiplicities, plus its required lobby
settings. Alesia case b and Haengju's divisions declaration generate identical lobby steps
to their listed partners, and were not sent separately. No Eagle Gate file was tried.
These are lobby readings, with no map/deployment, battle timer, wave, movement or strength
evidence. The procedure remains unverified without an agreed check. All games closed;
$0 API spend. Raw logs, generated steps and independent recount:
`runs/benchmark-window-20261110/`, `review/report-new-test/audit_lobby.json`.

The 2026-11-11 Belgrade lobby diagnostic at `25fc787`, the same build and pack,
reproduced the first five recruitments and read 4450 main-army funds remaining.
The native unit records then reported:

| Card | Cost | Can recruit | IsOwned |
|---|---:|---|---|
| Flagellants | 600 | false | false |
| Free Company Militia | 450 | false | false |
| Swordsmen | 375 | true | true |
| Greatswords | 850 | true | true |

The refusal is not explained by insufficient remaining funds. Both unavailable
cards report unowned in the same native field that the game's UI uses for ownership
locks. This identifies a content-access blocker; exact package/license causes remain
unestablished. No purchase, substitution, further recruitment or battle followed.
Belgrade still has no complete army readback and needs content access or an explicit
owner roster decision. The owned launch ended; no game/controller remained.
Cards, exact scalar logs, cached-binding references and independent recount:
`runs/benchmark-progress-20261111/`. The procedure remains unverified without an agreed check.

### Estimated battle windows

The times below use one estimate, 20-25 min, for a launch that runs to its 1,200 s timer, as the
designs estimated; battles that end earlier take less. Six single-launch Land jobs on Taurox that
ended at the timer on 9.0.3 or 9.0.4 took 1,292-1,347 s from job start to end (pilot-r4-01, the
two `gap-live-*-20261101` jobs and three bench jobs), and no siege has reached its timer, so the
Helmgart figure is unread. The last column gives the builds of the runs each battle page cites:
9.0.3 is Steam build 25823491 and 9.0.4 is 25961564, against the 9.0.5 pin, 26403568. The 9.0.5
patch includes battle balance changes, and equivalence with earlier results is unverified
([pins](integration.md#pins)), so a stage 1 reading on 9.0.5 replaces the older one it repeats.

| Step | What runs | Launches and game time | What it settles | Builds of the runs its page cites |
|---|---|---|---|---|
| L | Lobby-only readback (`scripts/wh3_lobby_readback.py`) | Two sessions on 2026-11-10, no battle | Alesia, Haengju and Izmail completed; Belgrade stopped before its first Flagellants recruited (readings above) | Build 26403568; the database values the pages quote were read on 2026-11-08 |
| 1 | Belgrade: 3 `hold` launches | About 1-1.25 h | The camp premise (its check 2) and construction | 9.0.3 (`bench-b9-assault-medium-ai10-20261014`) and 9.0.4 (the b12 siege jobs, pilot-r4); the `coord-suite-20261104` placements on 9.0.5 |
| 2 | Alesia: 1 `hold` of case a, then 5 more, 3 per case in all | 20-25 min, then about 1.7-2.1 h, plus 6 launches per restage (2-2.5 h; [its stage 1c](lines-eval.md#live-stages)) | Construction, visibility, the two fronts at once, the main effort on its side, the lines met at their front | 9.0.4 (the b12 Kislev reserve and siege reserve jobs); the Cannae window 1 placements on 9.0.5 |
| 3 | Haengju stages 1a-1e: 3 `hold` launches of `cth-emp-siege-a-v1` (1a, 1b), then 1 of `cth-emp-siege-a-all-v1` (1c) and 1 of the Eagle Gate screen `cth-emp-siege-a-all-gates-v1` (1d); the optional 1e adds 1 `hold` launch with one `emp_battering_ram` and one `emp_siege_tower_15m` | 1a-1d: 5 launches, about 100-125 min, plus 20-25 min for the optional 1e: 5-6 launches, about 100-150 min ([its page](haengju-eval.md#development-stages)) | The hold and release, teleporting in a siege, the engine's garrison start, ammunition across divisions (check 6 at 3 of 3), how far apart the divisions arrive with no hold (check 7), with 1d whether Eagle Gate replaces Helmgart, and with 1e which division mans each piece | 9.0.3 (`smoke-random-siege-skills-20261014-0511`) and 9.0.4 (`bench-b12-siege-baselines-20261016`, `bench-b12-siege-reserve-r2-20261016`) |
| 4 | Izmail stages 1 and 2: 2 `hold` launches, then 2-3 order probes | About 40-50 min, then at most 40-75 min if the probes run to the timer ([its page](escalade-eval.md#live-stages): about 1 h) | The fortification list, the engine starts, and a go or no-go: if no player unit reads `on_wall` in two attempts by two unit types, the battle stops | 9.0.3 (the 2026-10-14 siege attack and settlement smokes) and 9.0.4 (the b12 and b23 jobs); the Helmgart checkpoint case `siege-905-20261103` on 9.0.5 |

A proposal to change the marked order, for the owner (second look ER4, 2026-11-09; nothing above is
reordered): run one of Izmail's two stage 1 `hold` launches right after the readback, and keep
Belgrade's three `hold` launches as they are. In the one recorded siege the player attacked, the
garrison held its walls and all 1,000 tickets while our army stood idle, until the run was stopped
by hand at 730 s, so an idle attacker likely reaches the timer. That launch, about 20-25 min,
would read whether a siege ends at its timer with the defender winning, which Haengju's win,
Izmail's loss and Malta's return rest on and which no siege has shown. Before any Haengju launch
or climb it would also read `on_wall` for garrison units on the wall, the fortification list, the
ram's crew, `can_climb` and `can_siege`, and the ticket field. The same review drafted a list of
the engine assumptions the four battles rest on, each with its evidence and the launch that would
read it (ER0 in `runs/siege-evals-20261108/second-look.json`); it goes on this page only if the
owner asks.

The offline items these steps waited for are now on this branch: the readback step files,
`"private_record": true` on `emp-chd-camp-v1` and both lines declarations, and Haengju's Eagle Gate
declaration for 1d. Only the lobby readbacks above have run; no battle or Eagle Gate file has.
Still open offline: the camp's and the lines' readers
of the private record. Before any round each battle also needs the plan builder (portfolio S6) and
a boundary check on its own recorded first observation.

## Recognition and later versions

In every battle the witness plays the historical solution, and the battle pages, which tie each
scenario to its history and the winning branch, are in the public repository. A model that
recognises a battle could reach the witness's branch from memory, so a model's win on these
battles cannot separate recognition from a decision made on the spot until a recognition probe or
counter-history variants exist. Three options for the owner, none built:

(a) One counter-history variant per battle, where the historical branch should lose, with a
model's branch read on both: Belgrade's designed Z2 (`emp-chd-camp-z-v1`, an Infernal Guard beside
the east cannon), Haengju's all-at-once arm `cth-emp-siege-a-all-v1`, which removes the reason to
ration fire, Alesia with the heavy group in the town-side slot, and Izmail with an authored
garrison start once Haengju's stage 1 shows that teleporting works in a siege.

JUDGEMENT: Counter-history variants — Claude, 2026-11-09 (second look B2): one variant per battle
where history should lose. Without them a model's win cannot be told from recall; any
recognition reading of a model round rests on it.

(b) A text-only recognition probe: each model gets each battle's rendered first prompt and is
asked which historical battle, if any, it resembles. It makes paid calls and needs an owner budget.

JUDGEMENT: Recognition probe — Claude, 2026-11-09 (second look B2): a paid text-only probe asking
each model which battle a prompt resembles. Variants alone measure recognition only through
play; how often a model names a battle rests on it.

(c) One committed `split: held_out` variant per battle before any model round. Under
[guideline 3.2](evaluation-guidelines.md#32-reserve-held-out-variants-before-tuning-and-say-what-was-held-out)
held out is not secret, since the repository is public; it means that no model has played the
variant before its first evaluation round and that the variant is never used for a change. A
second map reserved before tuning, as
[camp-eval.md](camp-eval.md#variation) proposes for Belgrade (`battle_preset_wh3_nur_wastes_01_04`),
would extend that proposal to every battle.

JUDGEMENT: Held-out variants — Claude, 2026-11-09 (second look B2, D1): one split held_out variant
per battle, such as a second map, before any model round. Without one every model result is
on tuned battles; any transfer claim rests on it.

The set also uses few of WH3's own layers: no roster has a wizard or a flying unit, no witness
gives an ability order, and the five battles use two maps, Taurox for the three Land battles and
Helmgart for both sieges. Version 1 stays as built. The version 2 candidates add one WH3 factor
per battle, each as a new version whose primary contrast still changes one rule: a flying unit in
Haengju's last division, which ignores the wall, so fire must be split between fliers and
ladders; a wizard in Izmail's garrison; a caster in Alesia's relief group, whose spells change
which group is the main effort; and a flying mount for Belgrade's General, which can reach the
guns over the cover (no key checked). None is designed or built.

JUDGEMENT: Version 2 candidates — Claude, 2026-11-09 (second look D1): one WH3 factor per battle,
each a new version whose primary contrast changes one rule. Other factors, or none, change
what a version 2 measures; any version 2 build rests on it.

## Decisions for owner review

Six questions, with the recommendation first:

1. **Which battles form the set.** (a) The four built battles beside Cannae, with Malta kept as a
   design (recommended; this is what was built). (b) Build Malta as well now, which rests on three
   unobserved engine behaviours and repeats Belgrade's decision. (c) Drop Alesia because WH3 plays
   it as a Land battle, as [lines-eval.md question 1](lines-eval.md#decisions-for-owner-review)
   asks.
2. **The shared method rules.** (a) Accept rules 1-3 above for every battle: one primary contrast at
   two-sided Fisher p < 0.05, a frozen 4-of-5 gate at 5 s / 5 s, and premise checks with their error
   rates (recommended). (b) Decide them battle by battle on each page. (c) Another gate or timing
   cell for some battles.
3. **The first game window.** (a) The lobby-only readback and Belgrade's three `hold` launches,
   about 1-1.5 h (recommended): it settles every roster question and records the cheapest
   battle's premise in the private record, whose reader is still to build. (b) The readback alone,
   minutes: a check of the rosters and the lobby steps. (c) No game time yet. (d) The readback,
   one Izmail `hold` launch, then Belgrade's three, about 1.3-1.7 h, as the proposal under
   [Live order](#live-order) describes.
4. **The parked `llm.py` change.** (a) Keep it parked until Izmail's climb go or no-go passes, then
   merge it as its own logged version (recommended, as
   [escalade-eval.md question 4](escalade-eval.md#decisions-for-owner-review) says): no scripted
   stage needs it, and a battle that cannot climb would never cost the split. (b) Merge it now,
   so that the split of every `llm` card cell from its recorded launches lands with the Lua
   batch's split of every cell's setup identity. (c) Keep the siege attack for scripted
   controllers only. **Answered 2026-11-09:** "I approve models using siege orders"; it landed as
   v23 (rule 7 above).
5. **Confirmation rounds.** (a) None until a battle's gate passes, then one battle at a time at 16
   launches per arm, 32 launches and about 10.7-13.3 h of $0 game time each at 20-25 min a launch,
   less where battles end before the timer (recommended). (b) 10 per arm, power 0.426-0.474 for a
   50-point drop from a witness at 0.7-0.9. (c) Paired branches restored from a checkpoint just
   before the cue and compared with exact McNemar. This fits Belgrade only, the one battle whose
   arms give the same orders until the cue: Izmail's arms stage in different places, Alesia's and
   Haengju's differ from the first decision, so a branch before their cue is a branch at the start,
   and Haengju's held divisions would not survive a restore. Belgrade first needs its own
   checkpoint check case.
6. **Recognition and later versions.** The three options and the version 2 candidates in
   [Recognition and later versions](#recognition-and-later-versions), each marked there; the
   review makes no recommendation.

Each battle page lists its own questions; the markers on this page are the set-level ones.

## Sources

Every outside source the battle pages and the designs cite is listed, with what was read, in
[references](../references.md#historical-siege-evaluations-2026-11-08). In the repository:
`runs/siege-evals-20261108/designs.json` and `final-*.md` (the five designs and their judges),
`portfolio.md` (the review: overlaps, shared rules, build order and per-battle corrections),
`build-offline.json` and `lua-batch.json` (the build cards, reviews and planted wrong versions),
`parked/` (the `llm.py` change as it was parked, before v23), and `second-look.json` (the
2026-11-09 second look whose findings the grid, the round rules, the build column and the
recognition options answer). Game facts above are the battle pages' and the designs', each from
the recorded run or table they name.
