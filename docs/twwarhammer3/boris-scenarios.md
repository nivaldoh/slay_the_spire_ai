# Boris Todbringer battle scenarios for the multiplayer VM

Scope clarification from the owner, 2026-11-05: this restricted-content catalogue concerns
multiplayer work using the second account on the VM. General local evals, including the
[Cannae proposal](cannae-eval.md), may use any faction and lords. The no-lord VM diagnostic
fixtures are also local to those checks; this catalogue already includes lord-led candidates.

The Boris-only account is enough to propose a varied benchmark: traditional Empire guns
and cavalry, the new Ulric infantry and support units, and Bretonnian opponents. The most
useful situations make one unit's success depend on another unit's timing, protection or
information. Simply giving each model a separate duel would test little cooperation.

This catalogue contains **26 proposed setups**, researched on 2026-11-03. Each gives both
armies, a terrain requirement, decisions worth testing and an alternative that could expose
a weak controller. These are design candidates, **unverified in game**: no new battle has
been run, no balance or winnability claimed, and no scenario, score or check adopted.
It extends the [tactics reference](tactics-reference.md) with concrete Boris-compatible
armies. [Sources and exact excerpts](boris-scenarios-sources.md) distinguish developer
facts, older mechanics documentation, competition rules and our hypotheses.

## What the purchase permits

[SEGA's September 2026 FAQ](https://support.sega.com/hc/en-gb/articles/51224684758929-Total-War-WARHAMMER-A-New-Player-Survival-Guide-FAQ)
says one End Times lord pack supplies that lord's core racial roster, new content and
associated Free-LC, plus Immortal Empires, the Prologue and Bretonnia. Players with different
collections can play multiplayer together; each commands content they own. Thus buying
Boris does **not** grant all four End Times factions or the WH3 base races.

The [Boris store description](https://store.steampowered.com/app/3589670/) explicitly says
WH3 ownership is unnecessary, despite Steam's generic base-game-required banner. It lists
Boris, Ar-Ulric Emil Valgeir, the Seneschal of the White Wolf, Priest of Ulric, seven new
regular units and three Regiments of Renown. Fervour, temple upgrades, campaign skills and
Elector State Trooper recruitment are campaign features; they are not assumed custom-battle
bonuses or recruitment rights here.

| Content group | Candidate pool and restrictions |
|---|---|
| Core Empire | Swordsmen; Spearmen, with and without shields; Halberdiers; Greatswords; Crossbowmen; Handgunners; Empire Knights; Reiksguard; both Demigryph variants; Pistoliers; both Outrider variants; Mortars; Great Cannons; Helblasters; Helstorms; ordinary Steam Tank; Luminark; core heroes/wizards. The [original official roster](https://wiki.totalwar.com/w/The_Empire_Army_Roster.html) establishes the foundation, not current account-level recruitment |
| Boris additions | Wolf-Kin, Hunting Hounds, Warriors of Ulric, Teutogen Guard, Knights of the White Wolf, Knights Panther, Celestial Hurricanum; characters above. Optional later variants can use Order of the Axe, Fellwolf Brotherhood and Hounds of Ulricsberg; none is needed in the base cards |
| Free content | Bretonnia supplies another roster without another purchase. Empire Free-LC may add wizard/hero choices, but do not require a particular free hero to start |
| Excluded paid Empire additions | No Free Company Militia, Flagellants or Knights of the Blazing Sun from [Grim and the Grave](https://store.steampowered.com/app/404013/); no Archers, Huntsmen or War Wagons from [Hunter and the Beast](https://store.steampowered.com/app/1074320/); no Nuln Ironsides, Hochland Long Rifles, Land Ship, Volley Gun Steam Tank or Black Rose knights from [Thrones of Decay](https://www.gamespress.com/THRONES-OF-DECAY-IS-OUT-NOW-FOR-TOTAL-WAR-WARHAMMER-III). Ordinary Crossbowmen, Outriders and Steam Tank are different units |

These are entitlement-based candidates. The second client's recorded probe established
recruitable Middenland Swordsmen and Spearmen only
([account evidence](gcp-client-setup.md#3-your-steam-session)); it did not audit this
pool. Before a run, inspect every exact unit, variant, mount, item and spell on that account.
Use the Empire/Middenland selection actually available there; do not infer Karl Franz or
Gelt access from the original Empire roster article.

**E** below means both armies use the Boris/core Empire pool. **B** adds Bretonnia, whose
custom-lobby availability still needs confirmation. **X** needs the other faction on an
account entitled to command it. The FAQ confirms unowned campaign enemies; it is not proof
that the restricted custom lobby can build every unowned AI army. For X, use the suitably
licensed peer or host after checking its roster. Never force locked units into a client.

Every card keeps Empire on one side. Evaluate the model both commanding Empire and facing
Empire where account permissions permit; move the controller between clients when needed.
Swapping controller ownership and swapping attacker/deployment sides are separate contrasts.
If both clients own only Boris, use E and, after the lobby check, B; X is an extension.

## What the metagame suggests testing

The useful competitive lessons are about matchups and incentives. They do not establish
a current faction ranking or an optimal list for this restricted collection.

* **Combined arms versus melee pressure.** The Empire's broad roster permits a fragile
  firing line protected by infantry, while Ulric units permit an aggressive alternative.
  Test both, so the suite does not equate good Empire play with standing behind guns.
* **Cavalry roles differ.** CA presents White Wolf knights as sustained melee cavalry and
  Panther knights as shock cavalry. A universal cycle-charge rule is therefore a hypothesis
  to challenge, not a benchmark answer. Hounds provide cheaper flanking and pursuit roles.
  [Boris overview](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/107).
* **Patch-sensitive synergy matters.** In 9.0.3, Crush the Weak changed to grow during
  sustained winning melee; Teutogen attacks and several new-unit prices also changed.
  Launch-era impressions cannot settle their present value. These cards were researched
  against the former 9.0.4 pin; reassess patch-sensitive claims on the [current build](integration.md#pins).
  [CA 9.0.3 notes](https://community.creative-assembly.com/total-war/total-war-warhammer/forums/7-patch-notes-amp-announcements/threads/16126-total-war-warhammer-iii-patch-9-0-3).
* **Support has an opportunity cost.** An October multiplayer balance proposal questions
  the cost of Ulric prayers and Teutogen performance. That is community judgement, predating
  9.0.3, rather than measured current strength. It motivates testing whether support earns
  its place and whether a supposedly specialised unit actually performs its role. Do not
  copy its suggested buffs into vanilla benchmark assumptions.
  [Community balance proposal](https://community.creative-assembly.com/total-war/total-war-warhammer/forums/15-multiplayer-battles/threads/16034-community-sourced-peer-reviewed-balance-recommendations-dlc-balance-for-lords-of-the-end-times).
* **Land, Conquest and Domination reward different decisions.** CA introduced Conquest's
  central objective partly to discourage corner camping. Domination adds distributed
  points and reinforcement choices. An army that trades efficiently can still lose on
  objectives. [CA 5.1](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/23).
* **Tournament conditions are part of the task.** Indexed 2026 Total Tavern event rules
  specify caps, funds, scale and tickets, and some use a tournament map mod. Those are
  event-specific rules, not vanilla defaults to inherit silently. The live pages exposed
  only loading shells during this research; no current tournament win-rate estimate is
  supported. [September event](https://totaltavern.com/tournaments/jxinqthz2ricyuajca8yn8ar),
  [June event](https://totaltavern.com/tournaments/a3ij06vmybgpiqq5wz2bdch4).

## Common setup and terrain proposals

JUDGEMENT: Catalogue settings — Codex, 2026-11-03: proposes the fixed-roster settings below.
Tournament-budget drafting would measure army selection too; these cards isolate control.
Adoption, balancing and any benchmark weighting remain the owner's decisions.

All counts mean regiment cards, not individual soldiers. **BT** means one Boris Todbringer;
**SW** means one Seneschal of the White Wolf. Each shorthand is a real, controllable lord
included in the roster. Both are proposed on foot, without optional purchases except where
stated. Other characters use the named mount, or foot when no mount is specified. Do not
replace an unavailable loadout silently. Lord effects remain part of these whole battles.

Proposed shared settings: rank zero, Ultra unit size, Normal AI with neutral stat modifiers,
no campaign progression, Land unless stated, unpaused 1x. Use the listed fixed armies and
record actual lobby costs including character equipment. Set funds high enough for those
armies, with no extra purchases; equal card counts are not equal power or equal cost.
Asymmetric diagnostic armies need calibration before any claim of balanced competition.
Normal AI, a human and a frozen scripted opponent are different comparison arms.

Use the initial benchmark's 20-minute engine timer and an episode cap at least 120 seconds
longer as a *candidate*, preserving engine timeout outcomes. Mode cards must pin their own
displayed timer, ticket goal, starting resources and reinforcement rules. Keep unused
optional items/spells off; record mandatory passives. Magic-dependent cards must freeze
starting winds/reserve and their exact selectable spell keys. Turn automatic skirmish off
for explicit retreat studies and record fire-at-will/guard settings; changing automation is
another arm, since native skirmish can perform the behaviour being attributed to a model.

JUDGEMENT: Terrain templates — Codex, 2026-11-03: proposes the geometry classes and candidate
maps below. A fixed familiar map versus unfamiliar terrain measures different knowledge;
terrain comparisons rest on the selected map, deployment and information treatment.

| Code | Required geometry | Candidate to inspect before freezing |
|---|---|---|
| Open | Clear central contact area, usable flanks and retreat space; no corner starts | The Flats of Kislev; the existing Taurox benchmark map is an implementation alternative |
| Forest | Open centre and separate wooded approach with a meaningful reveal boundary | Forest of Shadows |
| Ridge | Crest blocks low direct fire; alternate route reaches a firing position | Alpine Ridge |
| Crossing | Restricted crossing, room to stage outside it; water effect checked separately | Amaxon Plain, already used for the repo's chokepoint mode |
| Ambush | Column start and accessible ambusher deployment on more than one approach | Backwoods Path, existing ambush-mode example |
| Town | At least two usable approaches, junction and meaningful capture point | Osterwald, existing minor-settlement example |
| Fort | Wall/gate and inner objective with functioning access routes | Helmgart, existing siege example |
| Three points | Separated capture areas and at least one route for reinforcement interception | Arnheim, existing Domination example |

Candidate names are not assertions that their geometry is suitable. Inspect and pin the
exact lobby map key, mode, deployment rectangles, unit positions, bearings and widths.
Reuse known keys from [battle types](battle-types.md) where appropriate; do not substitute
a similarly named Workshop version. Distances should come from the inspected map and
actual weapon ranges, then be recorded rather than invented from a screenshot.

The current terrain observation is a coarse passability grid: **no height, tree, water or
projectile line-of-sight labels**. Ridge/forest/water tests can measure adaptation from
public battle feedback or declared familiar-map knowledge. Measuring recognition of new
terrain needs a new public-information track. Replay/stills can be evidence for the
evaluator, never extra policy perception. Older [CA terrain guidance](https://academy.totalwar.com/battle-deployment-and-battle-terrain/)
motivates these geometries but supplies no adopted WH3 numerical modifier.

## Scenario catalogue

| Cases | Main coverage | Content boundary |
|---|---|---|
| 01–02, 05–06 | Dependent attacks, cavalry roles, shooting geometry, target allocation | Empire pool |
| 03–04 | Bracing, reserves and simultaneous air/ground threats | Bretonnia |
| 07–10 | Scouting, terrain adaptation, passage order, pursuit | Empire pool |
| 11–14 | Support timing, melee synergy, spell resources, recovery | Empire pool; exact ability loadouts needed |
| 15–20, 26 | Ambush, artillery defence, monsters, undead, barriers, fast/hidden threats | Licensed cross-faction opponent |
| 21–23, 25 | Objectives, reinforcements, settlement paths, siege breach | Empire pool; mode/interface prerequisites |
| 24 | Assistance across independently owned armies | Empire and Bretonnia; native multiplayer prerequisites |

JUDGEMENT: Scenario recipes — Codex, 2026-11-03: proposes the armies, starts, role divisions
and contrasts in 01–26. Other compositions change difficulty and coordination dependence;
none is a selected benchmark task, prescribed winning tactic or weighted score.

Each team division is a proposed two-controller treatment unless stated otherwise.
Its first role owns the lord, unlisted units and army orders. The second owns only its
explicitly assigned units. These divisions need configuration work; they are not aliases
already accepted by `team_llm_rules`. Every card's diagnostic is additional evidence beside
the engine outcome, not a victory condition. Mechanics named as opportunities require the
admission checks at the end.

The recipes rest on JUDGEMENT `docs/twwarhammer3/boris-scenarios.md` Catalogue settings and
Terrain templates; the comparisons and first-selection proposal rest on its Scenario recipes.

Titles, tactical suggestions and failure contrasts are experimenter notes. Give the policy
the declared public roster, state and objectives; do not reveal the intended solution by
appending these cards to its prompt.

### 01 Hold contact while a flanker arrives

**E · Open.** Empire: BT, 2 Spearmen (Shields), 2 Crossbowmen, 1 Empire Knights.
Opponent: SW, 3 Swordsmen, 1 Halberdiers, 1 Crossbowmen.

Deploy holding troops centrally and cavalry on one wing with an open route. Put the enemy
halberds where they can protect a flank rather than already trapping the cavalry.
**Team:** line/fire controller and Knights controller. The question is whether the line
can maintain a useful engagement until the cavalry finds an opening, and whether the
cavalry declines a poor charge. Contrast with immediate frontal charging and a timed flank
that ignores actual contact. Record overlapping engagements, target identity, flanker
survival and damage to the line; being behind an enemy without fighting is not a flank.
Reverse the wing in a reserved deployment to test feedback instead of memorised routing.

### 02 Shock cavalry and sustained melee cavalry

**E · Open.** Empire: BT, 2 Spearmen (Shields), 1 Crossbowmen, 1 Knights Panther,
1 Knights of the White Wolf. Opponent: SW, 2 Halberdiers, 2 Swordsmen, 1 Handgunners.

Keep enough space to disengage and reapproach, with the enemy infantry types interleaved.
**Team:** lord/infantry/fire and both cavalry regiments. Test role-specific targeting and
the decision to stay in contact or withdraw. A foil applies the same repeated charge cycle
to both cavalry types; another leaves both engaged regardless of opposition. Record
genuine separation, time out of combat and condition, not attack-command counts. The
new cavalry roles and Crush the Weak make this more informative than two identical Knights.
Exchange the halberd and sword positions without changing the roster.

### 03 Bracing while a reserve intercepts

**B · Open.** Empire: BT, 3 Spearmen (Shields), 2 Handgunners,
1 Demigryph Knights (Halberds). Bretonnia: 1 Lord on barded warhorse,
2 Men-at-Arms (Shields), 3 Knights of the Realm, 2 Mounted Yeomen.

Place the guns behind a screen with room for a cavalry reserve to move between flanks.
**Team:** line/guns and Demigryph reserve. Fast Yeomen offer a tempting pursuit while the
knights approach elsewhere. Test whether protectors remain oriented and stationary when
needed and whether the reserve intercepts the actual bypass. Compare with chasing the
nearest light unit. Diagnose gun activity and survival as well as the reserve's losses.
Facing and a halt order do not prove the engine applied charge defence; that needs a
separate mechanics check. Swap the heavy attack between wings.

### 04 Air and ground attacks arrive together

**B · Open.** Empire: BT, 2 Halberdiers, 2 Handgunners, 1 Crossbowmen,
1 Great Cannon, 1 Empire Knights. Bretonnia: 1 Lord on Royal Pegasus,
2 Pegasus Knights, 2 Knights of the Realm, 3 Men-at-Arms (Shields).

Deploy artillery with lateral escape room; separate the flying and ground approaches.
**Team:** lord/melee/Knights and all shooting units. One role keeps threats from pinning
the guns while the other decides which threat merits fire. Compare with all shooters
following the flying lord while ground cavalry reaches them. Observe ground/air state,
actual landings, shots and which protected units survive. An airborne attacker cannot be
assumed pinned by ground halberds. Later exchange the timing of the two approaches.

### 05 Open a gun lane without opening the army

**E · Open.** Empire: BT, 2 Halberdiers, 2 Handgunners, 1 Crossbowmen, 1 Great Cannon.
Opponent: SW, 3 Swordsmen, 2 Greatswords, 1 Pistoliers.

Start with a compact infantry screen and space to create oblique or staggered lanes after
handover. **Team:** melee screen and all shooters. Test mutual accommodation: a gun
controller may reposition, while the infantry controller must keep the resulting gap safe.
Contrast with repeated attack orders from an obstructed position and with withdrawing the
whole screen. Record firing evidence, ammunition, target condition and enemy penetration.
Ammo spent alone does not establish hits or useful fire. The crossbows offer an alternative
to treating every missile unit as a direct-fire gun.

### 06 Allocate armour piercing and avoid overkill

**E · Open.** Empire: BT, 2 Spearmen (Shields), 2 Handgunners, 2 Crossbowmen,
1 Great Cannon. Opponent: SW, 3 Swordsmen, 2 Teutogen Guard, 1 ordinary Steam Tank.

Present armoured targets and cheaper infantry simultaneously. **Team:** lord/infantry/
Crossbowmen and Handgunners/cannon. The controllers must share target opportunities
without all firing at the same nearly defeated regiment or wasting their specialised
weapons while a threatening target remains. Compare nearest-target fire and permanent
focus on the tank. Record target changes and overlapping fire alongside losses and outcome;
net HP changes do not by themselves assign damage to a particular shooter. Rotate target
positions while keeping available target classes constant.

### 07 Scout a concealed approach

**E · Forest.** Empire: BT, 2 Spearmen (Shields), 2 Handgunners, 1 Mortars,
2 Hunting Hounds. Opponent: SW, 3 Warriors of Ulric, 2 Wolf-Kin, 1 Knights Panther.

Freeze alternative legal deployments in which a different enemy assault group uses the
wooded approach; both need to be genuinely hidden initially. **Team:** main body and hounds.
Test scouting cost, response to a reveal and protection against an unseen flank. Contrast
with rushing both hounds into combat and advancing on the same timed route in every case.
Log first public sightings and subsequent protection/movement. Disappearance means unknown
current position, not death. Current shared alliance visibility makes this an implicit
cooperation task; a future private-scout-message treatment is a different information track.

### 08 Reposition around a crest

**E · Ridge.** Empire: BT, 2 Spearmen (Shields), 2 Handgunners, 1 Crossbowmen,
1 Great Cannon. Opponent: SW, 3 Swordsmen, 2 Crossbowmen, 1 Mortars.

Begin below a crest with a reachable alternative firing position, outside immediate melee.
**Team:** screen and shooters. Test whether the screen covers a useful relocation without
abandoning the guns, and whether the fire controller recognises persistent lack of shooting.
Compare stationary attack spam and a whole-army rush over the crest. Freeze a companion
open-ground start using the same armies; the contrast changes geometry, not just a map name.
Label this feedback-based adaptation under the present observation contract. Do not claim
visual terrain reasoning or a measured elevation bonus without additional public fields.

### 09 Cross a bottleneck in a useful order

**E · Crossing.** Attacking Empire: BT, 2 Spearmen (Shields), 2 Warriors of Ulric,
2 Handgunners, 1 Knights Panther. Defender: SW, 2 Halberdiers, 2 Crossbowmen, 1 Mortars.

Deploy the attacker outside the narrow passage and the defender far enough back that
crossing is possible. **Team:** lord/infantry and guns/cavalry. Test staging, passage order,
temporary cover and whether a cavalry regiment waits for space instead of clogging the
infantry. Compare sending every unit through together. Record arrival order, time unable
to contribute and condition upon exit. A shallow-water variant is separate: check actual
movement/combat effects before attributing an outcome to water. Reverse roles as a distinct
defence task; unbalanced crossing geometry must not masquerade as poor attacking intelligence.

### 10 Pursue a rout without losing the next fight

**E · Open.** Empire: BT, 2 Warriors of Ulric, 2 Crossbowmen, 1 Hunting Hounds,
1 Empire Knights. Opponent: SW, 4 Swordsmen, 2 Crossbowmen, 1 Empire Knights.

Leave substantial space behind the enemy and a reserve protecting its archers.
**Team:** main body and hounds/Knights. Test the trade between finishing a routed unit,
stopping its rally and returning to protect the ongoing fight. Compare pursuing every
routing target to the boundary and never pursuing. Record rout/rally/shatter states and
subsequent participation; one early rout is not a kill. Enemy states can only support
online decisions while visible. If the opponent never offers a meaningful pursuit choice,
that pilot has not established this task's usefulness.

### 11 Synchronise Ulric support with a joint attack

**E · Open.** Empire: BT, 1 Priest of Ulric, 2 Warriors of Ulric, 1 Wolf-Kin,
2 Knights Panther. Opponent: SW, 3 Swordsmen, 2 Halberdiers, 1 Crossbowmen.

Deploy cavalry so a supported attack is possible but not automatic. **Team:** lord/priest/
infantry and cavalry. Freeze the priest's selectable Battle Howl loadout and tooltip before
use. Test whether support timing follows actual readiness and contact rather than a fixed
opening cast. Compare immediate activation and cavalry arriving after the effect expires.
Record ability effect windows, recipient positions and contact, not merely an accepted
cast. An Emil-for-priest variant would be a new roster condition, not evidence of better
communication with the same army.

### 12 Concentrate a local melee advantage

**E · Open.** Empire: BT, 2 Teutogen Guard, 2 Wolf-Kin, 1 Warriors of Ulric,
1 Crossbowmen. Opponent: SW, 3 Greatswords, 2 Spearmen (Shields), 2 Crossbowmen.

Give both sides a wide enough frontage to choose where to concentrate. **Team:** lord/
Teutogen/Warriors/Crossbowmen and Wolf-Kin. Test exploiting a supported local engagement
while protecting lightly armoured damage dealers from shooting. Compare even one-to-one
duels and committing Wolf-Kin first. Armour sundering and the changed Crush the Weak supply
mechanical hypotheses; actual debuff application and combat advantage need checks.
Record who reaches which engagement and who absorbs incoming fire. A blob that wins through
lord strength does not establish successful role coordination.

### 13 Combine a control effect with a firing opportunity

**E · Open.** Empire: BT, 1 Light Wizard, 1 Bright Wizard, 2 Spearmen (Shields), 2 Handgunners,
1 Celestial Hurricanum. Opponent: SW, 2 Warriors of Ulric, 2 Knights Panther,
2 Hunting Hounds.

Use selectable Net of Amyntok and Fireball loadouts, and separately record the Hurricanum's available
shots/abilities and their actual resource costs. **Team:** lord/infantry/Light Wizard and
Bright Wizard/guns/Hurricanum. Test whether an immobilisation/control window is spent on a target that
the fire group can actually reach. Compare casting before guns are ready and firing at a
different target. Log effect, shots and resource use; do not assume every Hurricanum ability
uses winds or that its launch-description effects share one mechanic. A resource-scarce
variant starts with insufficient winds for both wizards' intended casts: test whether
Fireball consumption prevents a more useful net. Freeze that resource condition separately.
This card waits for the exact ability contract, not just the unit's recruitability.

### 14 Rescue and return a valuable unit

**E · Open.** Empire: BT with selectable Talisman of Ulric, 1 Jade Wizard,
2 Spearmen (Shields), 1 Teutogen Guard, 1 ordinary Steam Tank, 1 Handgunners.
Opponent: SW, 2 Halberdiers, 2 Handgunners, 1 Great Cannon, 2 Swordsmen.

Freeze a legal Earth Blood loadout and recovery limits. **Team:** lord/infantry/guns and
Jade Wizard/tank. Test screening a damaged asset's exit, choosing a recovery recipient and
returning useful force while another sector is under pressure. Compare healing by lowest
HP fraction alone and never withdrawing. Distinguish HP recovery, entities lost and healing
cap; a healed regiment need not regain killed soldiers. Record protection costs and the
rest of the battle so a surviving but idle tank is not automatically credited as success.
Boris's item availability and actual custom-battle regeneration must be checked.

### 15 Reform an ambushed column

**X · Ambush.** Ambushed Empire: BT, 2 Spearmen (Shields), 2 Handgunners,
1 Mortars, 1 Empire Knights. Beastmen: 1 Beastlord, 3 Gor Herd (Shields),
2 Ungor Raiders, 2 Chaos Warhounds, 1 Minotaurs (Great Weapons).

Freeze the column order and legal ambusher positions so the initial threat direction varies
between declared cases. **Team:** lord/infantry/Knights and ranged/artillery. Test forming a
defensible group under pressure, rescuing a separated gun and deciding what cannot be saved.
Compare continuing the march and attacking nearest enemies independently. Record first
contact/reveal, time until guns contribute and losses by column position. This is a
formation-recovery task, distinct from 07's pre-contact scouting. The licensed Beastmen
side is required; Boris's lore rivalry grants no opponent unlock.

### 16 Approach a defended Dwarf battery

**X · Open with an optional Ridge condition.** Empire: BT, 2 Spearmen (Shields),
2 Wolf-Kin, 2 Handgunners, 1 Great Cannon, 2 Hunting Hounds.
Dwarfs: 1 Lord, 3 Dwarf Warriors, 2 Thunderers, 1 Cannon, 1 Grudge Thrower, 1 Slayers.

Keep the dwarf battery behind mutually supporting infantry with a navigable flank.
**Team:** main body and hounds. Test counterbattery choices, closing under fire and a raid
that creates value without simply feeding hounds to Slayers. Compare a frontal blob and a
solo unsupported raid. Record firing interruptions, approach losses and defenders displaced.
Facing Empire, a dwarf controller must avoid dismantling its defence to chase cheap hounds.
The terrain variant tests a different approach problem; do not pool its outcome with Open.

### 17 Prioritise a monster during a broad rush

**X · Open.** Empire: BT, 2 Halberdiers, 2 Handgunners,
1 Demigryph Knights (Halberds), 2 Warriors of Ulric, 1 Great Cannon.
Greenskins: 1 Orc Warboss on warboar, 3 Orc Boyz, 2 Goblin Wolf Riders,
1 Trolls, 1 Arachnarok Spider.

Separate the spider's approach from the light riders. **Team:** lord/Warriors/Halberdiers
and shooting/Demigryph group. Test allocation between a conspicuous large threat and
smaller units that can disable damage dealers. Compare everything focusing the spider
and the reserve chasing wolf riders. Record what the monster actually contacts and whether
fire remains productive. The chosen Trolls invite a morale-sensitive target decision, but
do not assume their rout timing or use a fixed HP threshold as proof of fear or terror.

### 18 Fight an army that does not flee like humans

**X · Open.** Empire: BT, 1 Bright Wizard, 2 Halberdiers, 2 Handgunners,
1 Luminark of Hysh, 1 Empire Knights. Vampire Counts: 1 Vampire Lord on barded nightmare,
3 Skeleton Spearmen, 2 Grave Guard, 2 Dire Wolves, 1 Cairn Wraiths.

Freeze Fireball and Invocation of Nehek where selectable. **Team:** lord/infantry/Knights
and wizard/shooters. Test identifying magical-damage opportunities, denying recovery and
choosing between a dangerous character and its supporting army. Compare wasting pursuit
orders on undead and shooting the cheapest nearby skeletons indefinitely. Crumbling,
physical resistance and healing are mechanic preconditions to check on these exact units;
do not reuse human rout metrics. Facing Empire tests whether the undead side can sustain
contact and protect its recovery source under ranged pressure.

### 19 Maintain pressure through barrier rotation

**X · Open.** Empire: BT, 2 Spearmen (Shields), 2 Handgunners,
2 Crossbowmen, 1 Pistoliers, 1 Empire Knights.
Tzeentch: 1 Herald of Tzeentch on foot, 3 Blue Horrors, 2 Pink Horrors,
2 Screamers, 1 Flamers.

Freeze the Herald's spell selection. Allow room for damaged Tzeentch units to retreat
behind fresh ones. **Team:** main line/fire and Pistoliers/Knights. Test maintaining useful
pressure on a reachable target without chasing into Flamers. Compare constantly switching
targets and tunnelling onto a withdrawn target. The opponent must actually rotate for this
to test regeneration denial. Barrier recharge is distinct from HP healing; the recorder and
model renderer have separate barrier fields ([interface](../../src/twwarhammer3/engine/mailbox.py)).
Check those fields on these units before crediting threshold timing, and treat absent
readings as unknown.

### 20 Respond to two fast threats without oscillating

**X · Open.** Empire: BT, 3 Spearmen (Shields), 2 Crossbowmen, 1 Handgunners,
1 Demigryph Knights (Halberds), 1 Mortars.
Slaanesh: 1 Herald of Slaanesh on foot, 3 Marauders of Slaanesh,
2 Daemonettes, 2 Seekers of Slaanesh, 1 Fiends of Slaanesh.

Give the fast units two separated approaches and room to disengage. **Team:** fixed
defenders/shooters and Demigryph reserve. Test commitment decisions when each new sighting
could lure the reserve away from its current job. Compare nearest-threat reassignment
every decision and never reallocating. Record reserve reversals, travel and arrival before
or after a breach. Vary the committed flank through a declared opponent policy. One static
AI rush would establish much less than adaptation to a feint; no inference about deception
follows from a unit merely moving sideways.

### 21 Leave a safe position to contest the objective

**E · Conquest, Alpine Ridge candidate.** Empire: BT, 2 Spearmen (Shields),
2 Handgunners, 1 Great Cannon, 1 Empire Knights.
Opponent: SW, 3 Warriors of Ulric, 1 Teutogen Guard, 2 Crossbowmen, 1 Hunting Hounds.

Start the gunline outside the central objective so it must eventually decide whether to
advance. **Team:** lord/line/fire and Knights. Test trading a comfortable firing position
for control, and supporting a contest rather than sending one regiment to die on the point.
Compare camping indefinitely and charging the whole army onto the point. Use actual point
lock/holder/tickets and engine ending; raw damage is insufficient. Reverse armies and
deployment roles separately. The historical Conquest ticket settings are not a substitute
for reading and pinning this lobby's current settings.

### 22 Reinforce the sector that changes the result

**E · Domination, Three points.** Each starting army: 1 SW, 2 Spearmen (Shields),
2 Crossbowmen, 1 Empire Knights. Each reinforcement pool: 2 Swordsmen, 1 Halberdiers,
1 Handgunners, 1 Knights Panther, 1 Hunting Hounds. Use identical pools on both sides.

Use the army's available deployment and capture zones; pin the starting funds, income,
ticket goal and current purchase costs. **Team:** lord/infantry/shooters with exclusive
purchase authority, and all cavalry/hounds, including arriving reinforcements. Test whether
arrival time and the threatened point matter more than simply buying the strongest unit.
Compare spending as soon as possible on the highest-cost available unit and reinforcing
the already-won sector. Record actual arrivals and ticket changes; a purchase acknowledgement
is insufficient. This requires a partition for new unit types. No generic unsummon order
is assumed, so it covers only part of competitive Domination play.

### 23 Coordinate two approaches inside a settlement

**E · Town, minor-settlement mode.** Attacking Empire: BT, 2 Warriors of Ulric,
2 Teutogen Guard, 2 Crossbowmen, 1 Knights Panther.
Defender: SW, 3 Spearmen (Shields), 2 Handgunners, 1 Mortars, 1 Empire Knights.

Freeze a defensive tower/barricade layout or a fixed construction policy and supply rule.
**Team:** lord/infantry and Crossbowmen/Knights. Test securing a junction before support
enters, recognising a blocked street and diverting pressure toward a second approach.
Compare the entire army entering the first lane and splitting into unsupported assaults.
Record reachable routes, held points and support arrival. Buildings and capture state
make this different from a generic choke. Defence is a separate role condition with its
own construction authority; changing the layout is a new scenario instance.

### 24 Rescue an allied army in a native team battle

**B · Open, native 2v2.** Allied Empire: BT, 2 Spearmen (Shields), 2 Handgunners,
1 Great Cannon. Allied Bretonnia: 1 Lord on barded warhorse,
2 Men-at-Arms (Shields), 2 Knights of the Realm, 1 Mounted Yeomen.
Enemy Empire: SW, 3 Warriors of Ulric, 1 Teutogen Guard, 1 Crossbowmen.
Enemy Bretonnia: 1 Lord on barded warhorse, 2 Knights of the Realm,
2 Peasant Bowmen, 1 Mounted Yeomen.

Place allied armies in adjacent sectors, far enough apart that help costs travel time.
**Team:** one model per allied army. Give the enemy a declared choice of concentrated
attack on either ally. Test giving up an easy local fight to save the team's exposed guns
or cavalry partner. Compare self-contained army play and both allies abandoning their
sector simultaneously. Score the alliance's engine outcome and report both armies'
condition. A two-member split of one army is a useful related experiment, but cannot
establish native ownership, separate army resources or multiplayer reliability. This card
needs native attack support and model-controller wiring beyond the current move-only
worker, as well as the [native multiplayer checks](native-multiplayer.md).

### 25 Breach a wall and exploit the opening

**E · Fort, siege.** Attacking Empire: BT, 2 Teutogen Guard, 2 Warriors of Ulric,
2 Handgunners, 1 Great Cannon, 1 Knights Panther.
Defender: SW, 3 Spearmen (Shields), 2 Handgunners, 2 Crossbowmen, 1 Mortars.

Pin gate/wall health, siege equipment, defender supplies and building choices. **Team:**
lord/infantry/Knights and guns/artillery. Test whether infantry waits for usable access,
shooters support the entry and the mobile unit exploits rather than blocks the breach.
Compare sending everyone to a closed gate and bombarding after a useful route exists.
Record actual breach, traversal and inner-objective contest. **Requires interface work:**
the present action set lacks generic gate/wall attacks and wall occupation. A human-opened
gate would be a separate post-breach task, not verification of this siege scenario.

### 26 Protect the rear against hidden and summoned threats

**X · Forest edge.** Empire: BT, 2 Spearmen (Shields), 2 Handgunners,
1 Mortars, 1 Empire Knights, 2 Hunting Hounds.
Skaven: 1 Grey Seer (Plague), 3 Clanrats (Shields), 2 Gutter Runners,
2 Rat Ogres, 1 Warp Lightning Cannon.

Freeze the Grey Seer's selectable Vermintide loadout and a legal concealed skirmisher
approach. **Team:** main body and Knights/hounds. Test reserving enough protection to
respond when a new enemy appears near the battery while another threat already occupies
the front. Compare sending all mobile units after the first revealed skirmisher. Track
public reveal/spawn, unit identity and protection response; summon lifetime and ownership
are admission checks. No campaign Menace Below charge is assumed. Disabling the summon
leaves a distinct hidden-skirmisher task and must be recorded as a different condition.

## Comparing one model with cooperating models

JUDGEMENT: Team contrasts — Codex, 2026-11-03: proposes the comparisons below to separate
coordination from extra inference and easier views. Other information or resource budgets
change the question; no communication protocol or budget matching rule is adopted.

For a selected card, keep roster, legal actions, opponent and realised deployment identical.
Compare a single controller with a fixed two-member partition. Report actual calls, tokens,
cost and observation-to-effect delay for both; two independent calls are not free extra
reasoning. Distinguish equal monetary budget from equal model-call budget and from equal
real-time opportunity. All still run at unpaused 1x.

The existing [model team](multi-agent-implementation.md) partitions Empire Knights from the
rest, supplies a limited ally view and has no explicit teammate-message channel. The generic
dispatcher supports two members partitioned by unit type. Most proposed splits require a
new configuration; splitting identical unit types by lane, dynamic ownership, three or more
roles, shared-resource negotiation and deliberate teammate delays require additional work.
The built-in team path currently refuses nonzero injected `delay_ms`/`interval_ms`.

For communication research, first compare implicit coordination through permitted state
with the same team plus a declared message channel. Then consider delayed/dropped messages
and changed enemy approaches. Fix message visibility, delivery times, size/cost and whether
messages share the model's token budget. Compare decisions and battle effects, not the
number of messages or eloquence of a plan. Shared alliance sightings alone cannot establish
private-information exchange. Different ally observations also confound a raw team/single
comparison; harmonise them or report the difference explicitly.

Use the [SMACv2 reference](benchmark-references/smacv2.md), specifically
`smacv2/env/starcraft2/distributions.py` and `wrapper.py` at the recorded revision, as the
research-repo pattern for explicit roster/start distributions. Reserve deployment and
opponent-behaviour variants before tuning, including a case where a tempting tactic is
wrong. Fresh draws from a familiar family and unfamiliar maps are different tests.
A timed-script baseline can expose tasks that need no observations; a capable human or
script reference can expose an impossible or trivial task. Neither requires every winner
to follow the tactical story in the card.

## Turning a proposal into an admitted battle

JUDGEMENT: Admission evidence — Codex, 2026-11-03: proposes the repeatable checks below.
Roster-only acceptance would miss mechanics, task difficulty and measurement errors;
claims of tactical discrimination depend on these checks, which are not yet owner-agreed.

1. **Freeze the instance.** Save account-specific recruitability, factions, exact unit keys,
   counts, mounts/items/spells, ranks, map/mode/key, positions/bearings/widths, settings,
   toggle states, funds, opponent policy and all relevant pools/objectives. Check lobby
   against first observation. Refuse substitutions and inherited lobby settings. Record
   source revision, engine build and mod hash; a changed build needs a separate report.
2. **Check the decisive mechanic.** Compare engine/UI evidence with observations and actual
   effects: blocked versus clear gunfire, braced versus moving defence, concealed versus
   revealed targets, successful versus late casts, HP versus barrier recovery, and completed
   versus merely accepted reinforcement. The exact comparison, repetitions and pass rule
   go to the owner before becoming an [agreed check](../agreed-checks.md).
3. **Show that the decision exists.** Pilot a competent reference and the card's plausible
   failure contrast under the same starts. Check whether the enemy actually offers the
   threat, whether both controllers can affect it, and whether a trivial lord rush or map
   corner defeats the intended question. Pilot results guide revision; they are not held-out
   model results. Choose repetitions and balance changes before collecting final results.
4. **Check the evidence reader.** Preserve timestamps and unit identity. Challenge it with
   accepted-but-ineffective orders, hidden enemies, a routed unit that rallies, and missing
   frames. Where no reliable detector exists, use declared replay annotation or report only
   available measures; never turn a suggestive position into a proven charge or screen.
5. **Freeze evaluation separately.** Engine won/lost/draw is the gameplay outcome; controller,
   protocol, timeout-cap and unsupported-setup failures keep their distinct records. Report
   attempts and failures, army condition, cost and delay by scenario and role. Do not average
   bespoke tactical counters into a new score or reuse the initial benchmark's arithmetic
   as if it were validated for these armies. Select aggregation, sample counts, held-outs
   and the meaning of a team gain before a benchmark run.

## A compact first selection to discuss

JUDGEMENT: First selection — Codex, 2026-11-03: proposes 01, 02, 05, 06, 07, 10, 11 and 21
for breadth within the Empire pool. A mode-first or cross-faction selection changes coverage;
this is an owner discussion option, not a scheduled experiment or an implementation order.

That selection covers dependent timing, cavalry-role choice, firing geometry, target
allocation, information gathering, pursuit, ability support and objective play. Add 03
and 04 after checking Bretonnia; add 16–20 for different enemy mechanics once the opposing
client is ready. Keep 22–26 visible as richer resource, urban, native-team and hidden-threat
tasks, with their stated dependencies. No required purchase follows from this catalogue.
