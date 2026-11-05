# WH3 tactics for benchmark design

This reference connects battlefield tactics to situations we could evaluate in WH3.
It covers historical manoeuvres, Total War formations and control, Warhammer mechanics,
army composition, terrain and battle objectives. Read the catalogue for candidate
behaviours, then [evaluation designs](tactics-evaluation.md) for comparisons and evidence.

Research date: 2026-11-01. Sources establish historical examples and documented game
features; **the proposed tactics' effectiveness in our pinned WH3 build is unverified**.
This research used patch 9.0.4, build 25961564; the current runtime
[pin](integration.md#pins) is recorded separately. Earlier patch notes and WH2 Academy material are explicitly dated foundations,
not current numerical specifications. [Source notes](tactics-sources.md) record access limits.

The [benchmark definition](benchmark.md) governs: fixed armies and deployment, public
structured observations, persistent orders, unpaused 1x play, and engine-decided outcomes.
The historical [tactic cards](tactic-cards.md) retain their own rules and evidence.
Nothing here adopts a scenario, detector, score, sample count or gameplay experiment.

## How to use the catalogue

JUDGEMENT: Tactic catalogue — Codex, 2026-11-01: proposes the families and contrasts below.
A full-battle-only catalogue would cover different skills; candidate scenario coverage rests
on this selection. Adoption and any resulting benchmark weights remain with the owner.

Each entry gives a situation, an execution pattern, a counter or failure case, and an
observable comparison. These are design hypotheses, not scripts that must be followed to
win. A **foil** is a deliberately incomplete alternative used to isolate a choice, such as
charging before the infantry makes contact. A competent alternative may beat the named tactic.

IDs are for cross-reference, not difficulty rankings. A unit's role depends on its actual
weapon variant, abilities, mount and matchup. “Infantry”, “cavalry” and the harness's `class`
are insufficient to decide armour penetration, charge defence or psychology immunity.

| Decision family | Entries | Main question |
|---|---|---|
| Manoeuvre and coordination | H1–H8 | Can units create and exploit a local advantage without losing the rest of the battle? |
| Formation and engine control | T1–T8 | Can orders produce useful contacts, shots and disengagements? |
| Warhammer mechanics | W1–W8 | Can the controller coordinate magic, special units and faction resources? |
| Objectives and restricted maps | O1–O6 | Can it trade combat strength, position and time for the actual victory condition? |

## Historical manoeuvres adapted to WH3

Historical battles suggest patterns, not simulations to reproduce literally. At
[Cowpens](https://www.nps.gov/cowp/learn/historyculture/the-battle-of-cowpens.htm), successive
lines, withdrawal, cavalry intervention and returning militia contributed to envelopment;
one late withdrawal began with a misunderstood order. At
[Waterloo](https://www.nam.ac.uk/explore/battle-waterloo), Wellington sheltered troops behind
a ridge, while overextended British cavalry suffered a counterattack. English Heritage
describes a [feigned retreat at Hastings](https://www.english-heritage.org.uk/members-area/members-magazine/quizzes/bumper-quiz-december-2020/),
but notes uncertainty in the accounts. These examples motivate H1, H3–H6 and H8;
they do not establish a WH3 bonus or prove that an AI opponent will cooperate.

### H1 Pin and flank or hammer and anvil

Use a durable holding unit and a mobile attacker with an open route. Hold the target's
attention, travel around its formation, then attack its side or rear while the holding
unit remains engaged. An Empire infantry line and Knights are a candidate; a Slaanesh
holding element and fast flankers provide a contrasting roster. CA describes a similar
role for the [Exalted Hero of Slaanesh](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/82).
Failures include an early
charge, the holding line breaking, or an enemy reserve intercepting the flanker.
Compare coordinated contact with a frontal charge and an unsynchronised flank. Record
target-relative approach, overlapping contacts, both friendly units' condition and outcome.

### H2 Concentration and a refused flank

Put the main effort against one part of a wider enemy line while the other wing delays or
falls back. This adapts concentration and defeat in detail: local superiority matters more
than having every unit fighting immediately. Use elite melee plus cheaper holders, or a
mobile force against a dispersed army. An enemy that advances on the weak wing or shoots
the concentrated force can defeat it. Compare local concentration with even commitment;
record time until enemy support arrives and what the delaying wing loses. Merely piling
all units into one crowded melee is not evidence of useful concentration.

### H3 Double envelopment

A centre holds while two wings close on the enemy. It needs sufficient frontage, mobile
wings and a centre that can survive until closure. Compare with H1's single flank using
the same army: splitting the mobile force may reduce either wing's effectiveness. A
breakthrough through the centre or a reserve attacking one wing is the counterexample.
Record contact on both sides and the rear, closure timing, and the centre's condition.
WH3's monsters, flight and collision make a visual ring neither a sealed pocket nor proof
that enemies cannot escape.

### H4 Feigned withdrawal and bait

A fast unit approaches, draws a pursuer away from support, then withdraws through a
prepared interception or firing lane. Light cavalry and mobile shooters are candidates.
The pursuer must actually follow; simply retreating is not a successful feint. Compare
with harassment that never reverses direction and with a cautious opponent that refuses
pursuit. Record the enemy pursuer's separation from its support and the bait's survival.
Historical “deception” becomes an observed change in enemy movement here; we cannot infer
what the game AI believed.

### H5 Reserve and counterattack

Keep a capable unit uncommitted within reach of more than one threatened sector, then use
it to stop a breakthrough or strike an exposed attacker. Vary which flank is threatened
after the start to distinguish reactive allocation from memorised timing. Compare with
committing the same unit immediately. Record reserve travel, arrival relative to the
breach, protected-unit losses and any missed opportunity elsewhere. A reserve that arrives
too late, or remains idle while the army loses, has not succeeded by being preserved.

### H6 Defence in depth and fighting withdrawal

A forward screen buys time, retreats through prepared gaps, and leaves a second line to
receive the pursuit. Use mixed infantry and ranged units with room behind them. Compare
with a single line and with a retreat that leaves shooters uncovered. Watch for the first
line obstructing its own guns, being caught during withdrawal, or spreading a rout.
Measure retained firing opportunities, transitions between lines, health and remaining
space. Cowpens motivates the pattern; WH3 has no guarantee of orderly passage through
friendly formations or continued control of routing troops.

### H7 Concealment and ambush

Use a concealed approach to strike an exposed rear unit, or send a low-cost scout ahead
to reveal that threat before advancing the main force. Candidate units must actually have
the relevant hiding or stalking attributes. Compare covered and exposed routes and a
scout/no-scout pair. Success requires a visibility change and a useful interception, not
just standing in trees. Enemy roster knowledge remains public, but location knowledge does
not. Forest hiding, detection and the current visibility filter need checks before this
can measure information gathering rather than map memorisation.

### H8 Terrain shelter and disciplined pursuit

Use a ridge or obstacle to shelter a reserve, emerge when support is ready, then limit
pursuit so a local victory does not expose the army. Test shelter against an exposed start,
and pursuit followed by recall against unrestricted chasing. Direct-fire and arcing
weapons should be separate conditions: shelter against one may not stop the other.
Record incoming fire, emergence timing and returning combat power. Waterloo motivates both
questions. In the current interface, terrain height and projectile sightlines are missing;
a terrain-aware controller test needs the [information treatment](tactics-evaluation.md#what-the-harness-can-observe-and-command).

## Total War formations and control

The older official [deployment and terrain guide](https://academy.totalwar.com/battle-deployment-and-battle-terrain/)
describes flanking, obstructed shooting, high ground, concealment and shallow-water effects.
Those qualitative mechanics motivate the following hypotheses; specific formations and
their effectiveness are our proposals. In particular, a formation name is not an engine
bonus. “Checkerboard” and “chevron” describe placements that may create firing lanes.

### T1 Screening vulnerable damage dealers

Put a suitable interceptor between an approaching threat and guns, artillery or a caster;
keep the protected unit free to contribute. Use spears or halberds against a large attacker,
but test their actual matchup. The counter is a second threat, a flyer, or a fast bypass.
Compare protection against chasing the first attacker and against no screen. Record time
the threat spends engaging the screen, damage dealer survival and ammunition use.
The existing [card lessons](tactic-cards.md#design-rules-from-s1-s11) show why an escort's
victory cannot establish successful protection if the guarded gun still dies.

### T2 Firing lanes and staggered formations

Arrange direct-fire units with gaps between or beside the front line; use oblique infantry
sections or a staggered second line when geometry permits. Move an obstructed shooter
instead of repeatedly issuing the same attack. Test a solid infantry screen, clear lanes,
and a competent alternative such as flanking shooters. A gap wide enough for cavalry, a
crest, or friendly units drifting into the lane defeats the layout. Record shooting
opportunities and ammunition changes with visible target health, not orders alone.
Friendly fire and individual projectile hits need additional evidence.

### T3 Focus fire and target matching

Concentrate suitable weapons on a threat until it is neutralised, then retarget; use armour
piercing, anti-large, explosive or ordinary shots where the actual targets justify them.
Compare with nearest-target fire and with excessive concentration on a nearly defeated
unit. Shields, firing arc, projectile travel, small targets and wasted volleys can reverse
the expected advantage. Record target changes, ammunition, time to neutralise the chosen
threat and the health of neglected enemies. A unit's HP falling between observations does
not identify which shooter caused it.

### T4 Brace, absorb and countercharge

Face a charge-defence unit toward the incoming attack and allow it to settle, then commit
a separate counterattacker. Compare with moving into the charge and with a flank attack
that bypasses the prepared front. Charge defence, anti-large damage and bracing are
different properties; a spear icon alone proves none of them. Measure the actual approach,
movement state and first-contact losses. The harness has no checked per-entity bracing or
charge-bonus detector, so “halt acknowledged” cannot be the pass condition.

### T5 Cycle charging and chariot extraction

Attack a favourable target, disengage before the melee becomes unfavourable, reform, and
attack again. Chariots may need an exit beyond the target; shock cavalry may need to turn
and regain room. Compare with staying in melee and with withdrawing too soon to deliver
an effective attack. Dense formations, mass, terrain and trapped entities can prevent
extraction. Record contact episodes, separation, renewed approach, casualties and fatigue.
The [chariot card](tactic-cards.md#the-chariot-card-the-first-benchmark-card) is existing
task-specific evidence, not proof of universal charge timings.

### T6 Kiting and crossfire

Mobile shooters alternate firing with retreat while another unit threatens a different
angle. The candidate army needs speed, ammunition and space; faster pursuers, long-range
fire, nets and map edges are useful counters. Compare manual orders with the same starting
toggles and no orders, because built-in skirmish behaviour may already do the work.
Record firing/retreat intervals, separation, ammunition and objective progress. Survival
alone can be a losing strategy when time or capture points require commitment.

### T7 Formation width and spacing

Change width, depth and spacing to trade frontage and missile exposure against cohesion
and susceptibility to penetration. Compare spreading under bombardment with closing for
a narrow approach; include a melee rush that punishes excessive spacing. Large armies
may block their own routes while small armies cannot cover the same frontage. Record
arrivals, fragmentation, contact and losses; do not score the requested width as the
achieved shape. A per-unit centre and width cannot reconstruct every entity's position.

### T8 Fatigue, ammunition and pursuit economy

Walk when there is time, run when interception requires it, rest a reserve, and stop firing
at targets that are no longer worth the ammunition. Use a fast cheap unit for pursuit
while the main force returns to the objective. Compare with running everywhere and chasing
every router. The counterexample is urgency: careful preservation can surrender the battle.
Track friendly fatigue, ammunition, target re-engagement and outcome. Distinguish routing,
shattered, dead and merely out of sight. No score should reward unused ammunition without
also exposing the opportunity it failed to exploit.

## Warhammer mechanics

These entries require the listed abilities in the realised custom-battle loadout. Campaign
skills, technologies, summons and faction resources do not automatically exist there.
Official [5.0 notes](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/17-total-war-warhammer-iii-update-5-0-0)
document healing caps and barrier readouts; [5.1 notes](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/23)
document healing suppression from flaming attacks and mode-specific capture weight.
Neither supplies a current-build calibration for our evaluator.

### W1 Pin or slow then deliver a spell

Hold or slow a valuable target, wait for a favourable alignment, and cast a suitable
damage spell while it remains there. Compare coordinated casting with immediate casting,
and include dispersed or moving targets that punish waiting or an incorrect spell shape.
Manage the caster's range and safety, available magic, cooldowns and friendly exposure.
Record accepted casts, subsequent resource/ability changes and target health windows.
The same sequence can combine a net with gunfire. A spell marker or acknowledgement is
not proof of damage, and net health changes cannot assign damage to a particular spell.

### W2 Buff and debuff timing

Activate a melee buff, enemy debuff or faction army ability when relevant units are
actually fighting; save it if the engagement is about to end. Compare contact-triggered,
fixed-time and immediate activation using the same loadout. A feint, staggered enemy
arrival or caster interruption creates the negative case. Track overlap between the
ability window and useful contact, resource cost and outcome. Dark Elf Murderous Prowess
is an older [documented trigger example](https://academy.totalwar.com/dark-elves-battle-tactics/);
do not treat automatic passives as controller-issued casts.

### W3 Healing and barrier rotation

Withdraw a damaged unit while a second covers it, then return it after permitted healing
or barrier recovery. Tzeentch barrier units and armies with a healing caster are separate
variants: barrier recovery is not restored flesh or resurrected entities. Compare rotation
with continuous engagement. Pursuit, focus fire, a healing cap or loss of an objective
can make rotation worse. Record HP, barrier and living entities separately, including
time out of combat. Gains in net HP cannot reveal gross healing while damage continues.

### W4 Leadership pressure and recovery

Combine a flank, local casualties, a suitable fear/terror source or leadership debuff
against a vulnerable unit; protect or restore friendly leadership when a rout threatens.
Compare coordinated pressure with dispersed attacks, and include immune or unbreakable
targets where the proposed route to victory should fail. Undead crumbling and daemonic
instability require separate mechanics checks from ordinary routing; they are not safe
to collapse into one “morale damage” score. Record state transitions and remaining combat
power. Killing a lord is a possible intervention, not an automatic army-wide victory.

### W5 Flying attack and air defence

Fly around the front, attack an exposed battery or caster, and disengage before anti-large
support arrives. Contrast with ground-only approaches and with an escorted backline.
Flying attackers, interceptors and ground shooters create a coordination problem across
two movement layers. Confirm landing/take-off and ground contact through observations;
an airborne unit over a point is not necessarily contributing capture weight. Breath
attacks and other abilities need their own target/availability checks. An attack order
does not guarantee safe landing, and a retreat order may not free an engaged flyer.

### W6 Monsters supported by infantry

Use infantry to occupy enemy attacks while a large damage dealer engages a favourable
target, or screen a vulnerable monster from anti-large units and missiles. Lizardmen,
Ogres and monster-supported Chaos armies offer variants. Compare supported engagement
with sending the large unit first. The counter is anti-large concentration, unobstructed
shooting at a tall target, or congestion among friendly units. Record both components'
condition and useful contact. The claim to test is mutual support; overlapping unit
centres alone do not prove damage sharing or protection.

### W7 Summons and temporary units

Place an available summon where it interrupts shooting, screens a retreat or delays a
reinforcement, then exploit the temporary opening with permanent units. Compare with
summoning directly into the main melee and with never using the resource. A protected
target, poor placement, summoning delay or expiry can defeat the plan. Record appearance,
identity, contact and the original army's progress. Keep summoned entities separate from
starting forces in preservation metrics. Available summons, uses and decay rules must
be read from the selected loadout; the faction name is not enough.

### W8 Aura positioning and resistance matching

Keep support units within useful aura range while spacing the force against area damage;
use the appropriate damage type against the target's actual resistances. Cathay Harmony
is a formation-dependent example. Compare connected support with separation while keeping
the roster fixed. A vortex or attack from several directions may punish staying together.
The [8.0 notes](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/98)
change Sky Lantern support, while the [Bhashiva overview](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/97)
explicitly excludes Tiger Warriors from ordinary Battle Harmony. Validate each unit's
eligibility; do not award aura credit merely for proximity.

## Objectives and restricted maps

Use the realised mode's objective text and engine result. The
[battle-type interface](battle-types.md) exposes different points, gates, supplies and
reinforcement pools; these are not interchangeable tasks. Official
[5.1 notes](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/23)
introduced Conquest's central capture alternative and AI support for Domination.

### O1 Chokepoint control and breakthrough

Hold a crossing with a suitable front and ranged support, or synchronise an assault on
it with another route where one exists. Compare concentrated passage with staggered
entry and a detour. Artillery, spells and flyers can punish a packed defence or bypass
it. Record congestion, units actually across, and damage while waiting. If the map has
only one pass, a proposal requiring an outflank is invalid. Underground battles may
restrict manoeuvre differently; inspect each map rather than treating them all as tunnels.

### O2 Siege assault and diversion

Threaten more than one approach, concentrate on a viable entry, then send a force to the
relevant point while containing defenders. Compare with everyone taking one entrance.
A diversion only succeeds if defenders move and the main force exploits it. Record
gate state, entry, travel and point ownership, alongside losses. Explicit gate attacks,
wall targeting and siege-equipment control are gaps in the current order interface;
do not promise a full siege-assault benchmark from movement and unit attacks alone.
Ladders, tower rules and rebuild rules must be checked for the pinned build and map.

### O3 Settlement defence in depth

Choose which approaches to contest, keep a reserve near important points, and build
available defences where they support the actual fight. Compare static perimeter defence
with withdrawing to an inner line. Flying bypasses, divided attacks and capture pressure
test whether the reserve can respond. Record supplies spent, completed construction,
holder transitions and the engine result. A standing tower is not proof of useful fire;
an army that wins street fights can still lose its victory location.

### O4 Capture and rotation

In Conquest, trade position and combat for the central objective; in Domination, allocate
forces across points and reinforce threatened sectors. Compare nearest-enemy aggression,
an initial split that never adapts, and reactive rotation. Fast distraction units and
counter-rotation provide negative cases. Record actual ownership and ticket history,
travel time, accepted purchases and deployed units. Do not infer capture from distance
alone: lock state, contesting, unit eligibility and mode-specific weight matter.
Moving off a point to win a favourable fight can be the right choice.

### O5 Survival and resource scheduling

Clear a stage, capture what the mode requires, and arrange units for subsequent waves;
choose between affordable reinforcements and available construction. Compare immediate
spending with retaining a reserve for the next threat. Vary wave directions and resource
scarcity only through disclosed, controllable setup. Record stage progress, supplies,
permanent-unit condition and resource effects. Healing, ammunition purchases, upgrades or
other UI services are out of scope unless the bridge supports them. A survival score
cannot be substituted for the Land Battle winner.

### O6 Ambush escape and multiple opponents

For an ambushed force, reform a screen, protect vulnerable units and seek the actual
escape or victory objective; compare with attacking the nearest enemy in all directions.
Use the same idea of selective commitment in free-for-all: avoid a fight that lets another
opponent win uncontested. Record role-specific objectives, surviving assets, alliances and
who is engaging whom. A custom extraction objective is an authored extension, not a
universal native ambush rule. Team and free-for-all conditions also need separate failure
accounting; native multiplayer control remains [limited](native-multiplayer.md#implementation-status).

## Factions and army compositions

These are candidate loadouts and tests, not an exhaustive roster or a faction tier list.
They instantiate the catalogue's proposal: actual unit keys, DLC availability, costs,
traits, mounts and abilities must be checked in the lobby, database and start observation.
Race-wide labels hide substantial differences between legendary lords and subfactions.
Campaign recruitment, technology and economy are outside these fixed-army battles.

| Faction or roster family | Candidate composition and tactical question | Counter or contrasting composition |
|---|---|---|
| Empire | Spears/halberds, Handgunners, Knights, support character: T1/T2 plus H1 | Two mobile threats; an arcing-missile roster is a contrasting composition, not an isolated test of firing lanes |
| Dwarfs | Holding infantry, Thunderers and artillery: T2/T3/O1 | Flying or fast flankers; compare a mobile detachment with a compact defence |
| Bretonnia | Infantry holders, shock cavalry, support caster: H1/T5 | Prepared anti-large frontage; compare coordinated cavalry waves with one mass charge |
| High Elves | Spear/archer core plus cavalry or flying threat: H5/W5 | Ranged pressure on the support unit; trade a mobile reserve for more shooters |
| Dark Elves | Armour-piercing shooters, infantry, mobile flank: T3/W2 | Enemy delays contact or spreads; distinguish automatic Prowess from active timing |
| Wood Elves | Mobile missiles with a holding or fast interception element: H7/T6 | Faster pursuers and capture pressure; contrast open ground with cover |
| Kislev | Hybrid shooters plus a mobile reserve: T1/T6 | Force simultaneous melee threats; measure when hybrids stop firing to hold |
| Grand Cathay | Eligible Yin/Yang line and ranged support: W8/T2 | Separation or area damage; include a non-Harmony unit variant, not only the standard core |
| Greenskins | Cheap holders, melee damage, cavalry/chariot element: H2/T5/W2 | Disrupted concentration; check the actual army ability rather than assuming campaign WAAAGH resources |
| Beastmen | Mobile melee, chariots and a concealed approach: H7/T5 | Screening and revealed approaches; vanguard positioning is setup, not a current policy action |
| Skaven | Expendable screen, weapons teams, optional summon: T1/T2/W7 | Multiple bypass routes; compare screen protection with an alternative that sends damage dealers first |
| Lizardmen | Saurus/Skink support with a large attacker: W6/H5 | Anti-large and missiles; contrast a monster-heavy force with supported monsters |
| Vampire Counts | Holding infantry, mobile/flying damage, healing support: W3/W4/W5 | Leadership pressure and ranged focus; track crumbling separately from living-unit routing |
| Vampire Coast | Undead screen, guns and artillery: T2/W4 | Fast or aerial disruption; distinguish undead persistence from effective shooting |
| Tomb Kings | Skeleton line, constructs, selected support/summon: W6/W7 | Anti-large focus and delayed summon value; verify custom-battle resource availability |
| Khorne | Melee holders, fast attackers and selected ranged support: H1/H2 | Kiting and crossfire; vary whether a mobile reserve can reach the shooters |
| Slaanesh | Holding element and fast flank attackers: H1/H3/T5 | Protected flanks and sustained shooting; verify which units possess flanking attributes |
| Tzeentch | Barrier-bearing units, missiles and caster: W1/W3 | Continuous pursuit or focus fire prevents recovery; test HP and barrier separately |
| Nurgle | Durable holders, support/healing and a mobile threat: W3/W6 | Ranged pressure or split objectives; compare compact support with timely separation |
| Ogres | Large melee with small screening units and selected guns: W6/T4 | Prepared anti-large frontage and terrain bottlenecks; low entity count is not low army value |
| Chaos Dwarfs | Cheap screen, durable infantry, guns/artillery, large support: T1/T3/W6 | Mobile disruption; quantify the opportunity cost of protecting expensive shooters |
| Warriors of Chaos, Norsca, mixed Daemons | A declared mix of infantry, mobile threats, monsters and support: H2/W6/W8 | Test the actual roster rather than importing all four gods' mechanics into every unit |

Vary composition along meaningful axes: line-heavy versus mobile; many cheap units versus
few expensive ones; direct-fire versus arcing missiles; single entities versus formations;
caster/support dependence versus redundancy. Equal unit counts do not mean equal value,
and equal funds do not make a matchup fair. Preserve the army while testing a decision;
change the army in a separately reported generalisation or matchup study.

## Terrain and mode coverage

| Setting | What it changes in the proposed test | Essential check |
|---|---|---|
| Open, flat field | Travel distances, exposure, room for H1/H3/T6 | Legal bounds and unobstructed routes, not just a map label |
| Ridge or reverse slope | Visibility, firing lanes, sheltered approach | Height and weapon-specific line of fire; the current grid lacks them |
| Forest and woodland edge | Concealment and movement/fire interaction | Which units hide; actual visibility; attributes that change terrain effects |
| Shallows or marsh | Travel and combat conditions for particular units | Surface extent and unit-specific penalties; do not infer from visual colour |
| Narrow pass, bridge, underground | Frontage and route congestion | Passage width, alternate paths and reachable destinations |
| Settlement streets and walls | Entries, turns, towers and capture points | Pathfinding, objective roles, gate state and available order support |
| Map edge or corner | Limits routes and retreat space | Legal geometry; include as a robustness case, not a silent prohibition |
| Long or asymmetric map | Reinforcement travel, reserve placement and fatigue | Realised starts; rotate/mirror only when geometry remains comparable |

Land, Siege, Survival, Ambush and Conquest are already in the owner's intended scope.
Domination, minor settlements, chokepoints, underground and free-for-all are additional
research candidates represented in [battle-types.md](battle-types.md); their inclusion
is undecided. Separate attacker/defender roles, engine AI difficulty/stat modifiers and
human opponents. A landscape skin or weather label should become a test factor only
when it changes something measured or observed; do not assume rain alters gunpowder.

### Air relief development candidate, 2026-11-05

`brt-air-relief-v1` is a separate candidate, outside suites, using two ground pockets
and a central flying reserve. It is being prepared in the Cannae worktree while the main
checkout's B3 queue stays frozen. No follow-on game starts before that queue exits.

JUDGEMENT: Air relief development profile — Codex, 2026-11-05: proposes two ground
pockets and three central flying regiments against two native-AI groups. Other force
splits/spacing/routes change the decisions; no tactical-necessity claim follows.

The player has a foot Bretonnian Lord, four shielded Spearmen-at-Arms, four ordinary
Peasant Bowmen, two Pegasus Knights and one Royal Hippogryph Knights regiment. Each pocket
gets two spears/two bows; the Lord is west. The enemy has a foot Empire General in the
west, six Greatswords and four Handgunners, three/two per group. The publisher's
[Bretonnia page](https://store.steampowered.com/app/534330/Total_War_WARHAMMER__Bretonnia/)
lists the flying regiments; its historical description is not a current-build stat oracle.

JUDGEMENT: Air relief force freeze — Codex, 2026-11-05: selects six Greatswords/four
Handguns plus a General before any outcome, rather than the four/two draft. Base database
costs are 8,100 enemy/7,800 player; similar cost is a prior, not evidence of balance.

The full typed declaration fixes every placement, rank zero and default foot-lord
loadouts, normal AI/1.0 modifier, large units, 20,000 funds and a 1,200 s timer. It reuses
the pinned map; no new score or tactic requirement. Every legal engine win counts.
The first A terrain sample shows a positive-z island of path restrictions between the
pockets. Its 32 m grid/16 m sample squares cannot prove formation footprints, a blocked
crossing or an air travel advantage. First observe real movement, flight and engagements.
Native AI may combine its groups, or simple control may win; retain either finding.

JUDGEMENT: Air relief construction screen — Codex, 2026-11-05: selects one Hold/one
RushNearest attempt and at most one later public witness if time permits. Repeats or a
different control set change what can be concluded; these are construction attempts.

The conditional card first runs one Hold and one RushNearest attempt, $0, unpaused 1x,
with 600/1320/2000 s start/episode/job limits. Inspect recruitment, settings, foot mounts,
initial flight state, positions and actual routes; never treat an accepted order as arrival.
A public-interface allocation witness follows only if the setup works and time remains.
Begin the pilot queue by 11:45 UTC, start no pilot after 12:15 UTC, and start no optional
witness after 12:35 UTC; all game work ends before 13:25 UTC. Preserve missing attempts.
No model comparison or agreed readiness check. Raw card, read-only current-build database
rows and pinned decoder schema: `runs/cannae-build/research/`. Configuration follows the
SMACv2 `wrapper.py` explicit-environment pattern; no seeded engine replay is assumed.

## Limits that matter across tactics

The game handles entity movement, collision, combat, pathfinding and automatic responses.
A tactic can fail because the plan was wrong, the order arrived late, the route was blocked,
the engine refused it, or the observation omitted a necessary fact. Report those separately.
Repeatedly issuing orders can also interrupt useful execution; more orders are not more skill.

Corner defence, exhausting enemy ammunition with a fast character, baiting the AI into a
blob, repeated pull-through, and hiding until a timer ending are potential robustness
cases. Record them and their outcomes. The current definition permits engine-valid play
and counts timer wins; imposing competitive-house rules would require a new explicit
choice. Test objectives and measurements for such incentives before ranking controllers.

The [evaluation companion](tactics-evaluation.md) gives candidate comparisons, measurement
checks and links to BEHAVIOR, CARLA and SMACv2. The owner's follow-up is a shared
[WH3 knowledge skill](../owner-direction.md)
for Codex and Claude Code after this research; that skill is not yet built.
