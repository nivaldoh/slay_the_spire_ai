# Small focused candidates, second batch (draft, 2026-10-17)

Owner direction: mostly small battles that each test one or two skills, as difficult as
they can be while staying demonstrably winnable, diverse in armies and mechanics, each
answering a distinct question ([scenario mix](benchmark-implementation.md#owner-goals)).
S1-S7 ([first draft](benchmark-implementation.md#history)) cover
feint and flank, kiting, lines of fire, a fragile gun, spell timing, hammer and anvil and
a corner defence. This batch adds skills none of them test. Written under the owner's
overnight delegation (2026-10-17); every item is a definition until its live checks run.

Shared settings, as S1-S7: classic battle on the Taurox preset, very hard AI, modifier
1.0, unit scale 0.75, 1200 s timer, no lords. Every card below appears in a recorded
lobby dump (permission index 0) and is a `wh_main`, `wh2_main` or `wh3_main` unit. Costs
and statistics come from the game database through `scripts/wh3_db.py`; men are the
database size at unit scale 0.75. The S5 lobby refused 800 funds for a 600-cost
character army, so funds keep at least 10% headroom over the larger database army
cost. Rosters are fixed; funds only cap recruitment.

Checks per candidate, as before: the lordless setup, a naive scripted floor that should
lose, then one disclosed diagnostic of the hypothesised play at 0 and 5 s observation
age. A floor win means the step is too easy and climbs.

| Id | Scenario | Skill | Player (cost) | Enemy (cost) | Funds |
|---|---|---|---|---|---|
| S8 | `dwf-thunderers-grn-trolls` | focus fire against regeneration | 2 Thunderers, 1 Dwarf Warriors (1,850) | 3 Trolls (2,250) | 2,500 |
| S9 | `grn-giant-ksl-streltsi` | a lone monster's target choice | 1 Giant (1,400) | Kossars (spear), Streltsi (1,350) | 1,600 |
| S10 | `skv-spears-sla-hellstriders` | receiving cavalry: facing and bracing | 3 Clanrat Spearmen (975) | 2 Hellstriders (1,350) | 1,500 |
| S11 | `dwf-cannon-grn-lobbers` | counter-battery and when to advance | 1 Cannon, 1 Dwarf Warriors (1,250) | 2 Rock Lobbers, 2 Goblin Spearmen (1,750) | 1,950 |

S12 and S13 below are definitions only, not declared. Three disclosed diagnostics are
implemented in `battle/calibration.py` as `FocusFire`, `MonsterTarget` and
`CounterBattery`; their controller cards state every rule, and the paragraphs below
describe them as built. `BraceFacing` (S10) was removed on 2026-10-18 without ever
playing (S10 is set aside); it remains in Git history before that date.

## S8. Focus fire against regeneration

Player Dwarfs defend: 2 x `wh_main_dwf_inf_thunderers_0` (700, 60 men),
1 x `wh_main_dwf_inf_dwarf_warrior_0` (450, 75). Enemy Greenskins attack: 3 x
`wh_main_grn_mon_trolls` (750, 12 each).

Database facts: Trolls carry `wh_main_unit_passive_regeneration`, causes fear, MA 34,
MD 32, armour 40, morale 45; club 30 + 70 AP, splash up to 4 medium targets. Thunderer
rifles: 145 m, 5 + 17 AP, 13 s reload, low trajectory, 22 rounds; armour 80, 35% shield.
Dwarf Warriors: MD 40, armour 85, 55% shield, morale 70.

Hypotheses. Naive: fire at will spreads shots over three regenerating units, so none
breaks, and the trolls reach the guns. Winning: both gun units shoot the same troll unit
until it routs (morale 45), the warriors take the first contact in front of the guns,
and the guns step back from any troll that reaches them. Main risk: low troll morale may
make plain fire at will enough (trivial), or the clubs may overrun the warriors before
focus fire matters. Floor: `hold`. Diagnostic `FocusFire`: every shooter fires only at one
committed enemy (kept until it routs or leaves sight, then the visible enemy with the
lowest men fraction), holding while it is out of range; other units attack the enemy
nearest the guns; a gun with an enemy within 40 m moves 80 m away from it. Overlap: S3
also coordinates guns and a melee screen, but there the question is the line of fire,
not the target.

## S9. A lone Giant against a spear screen

Player Greenskins attack: 1 x `wh_main_grn_mon_giant` (1,400, single entity). Enemy
Kislev defend: 1 x `wh3_main_ksl_inf_kossars_1` (500, 68) and 1 x
`wh3_main_ksl_inf_streltsi_0` (850, 68).

Database facts: Giant MA 65, MD 30, armour 50, 15% missile resistance, causes terror;
club 200 + 500 AP, splash up to 7 targets. Kossars: spear 20 + 5 with +15 against
large, `charge_defense_vs_large`, `charge_reflection`; bows 140 m, 20 arrows. Streltsi:
rifles 145 m, 5 + 17 AP; gun-halberd 9 + 25 AP with no bonus against large; armour 70.

Hypotheses. Naive: charge the nearest unit, usually the braced spears in front, and
trade blows with anti-large while the Streltsi shoot. Winning: walk around the spears
onto the Streltsi (no anti-large bonus), rout them through terror, then take the Kossars
in the flank or rear. Main risk: the Giant may win any engagement (trivial), or the
armour-piercing rifles may kill it before it arrives (impossible); terror may decide
either way. Floor: `attack_nearest`. Diagnostic `MonsterTarget`: prefer a visible enemy
whose card key lacks spear, halberd, pike or `kossars_1` (the observation labels both
Kislev units `missile`, and the Giant `infantry`), walk first to a point 60 m past it on
the side away from the spears, then attack; leave a melee beside anti-large after 10 s. Overlap:
the mirror of S1, from the monster's side. The question is target choice for a single
entity, not a two-unit flank.

## S10. Receive the charge

Player Skaven defend: 3 x `wh2_main_skv_inf_clanrat_spearmen_0` (325, 120 each). Enemy
Slaanesh attack: 2 x `wh3_main_sla_cav_hellstriders_0` (675, 45 each).

Database facts: Clanrat Spearmen MA 18, MD 24, morale 45, `charge_defense_vs_large`,
`charge_reflection`, spear 18 + 5 with +9 against large, can brace. Hellstriders charge
bonus 40, MA 24, MD 26, 35% shield, `causes_fear`, `immune_to_psychology` (read here as
never routing; live battles showed they rout, [log](log.md#2026-10-17-overnight-tranche-harness-b18-b23)), spear-claw 20 + 8 with +10
against large.

Hypotheses. Naive: holding in the deployment line leaves flanks open; the riders circle
and charge rears, and fear plus rear charges rout morale-45 rats. Chasing riders
(`attack_nearest`) unbraces the spears and invites flank charges. Winning: stand in a
tight triangle or back-to-back block, turn the fronts toward the riders without moving
off position, and let a second spear unit counter-charge a rider unit stuck on the
first. Main risk: riders that never rout must all die to weak spears (unwinnable), or
the AI may charge braced fronts head-on (trivial). Floor: `hold`; also `attack_nearest`.
Diagnostic `BraceFacing` (removed unplayed, see above): posts in a triangle around the start (two 20 m
either side and 10 m forward, one 20 m behind); each unit turns to the nearest enemy
while it is over 60 m away, stands still when nearer, and attacks only a rider within
20 m of it or within 15 m of a neighbour in melee. Overlap: the defender's side of S1's problem;
the question is formation and facing discipline.

## S11. Counter-battery before the advance

Player Dwarfs attack: 1 x `wh_main_dwf_art_cannon` (800, 24 crew, 22 rounds, cannot run)
and 1 x `wh_main_dwf_inf_dwarf_warrior_0` (450, 75). Enemy Greenskins defend: 2 x
`wh_main_grn_art_goblin_rock_lobber` (550, 33 crew) and 2 x
`wh_main_grn_inf_goblin_spearmen` (325, 120).

Database facts: Rock Lobber crews have morale 40, MD 6, `expendable`, cannot run. Goblin
Spearmen MD 28, morale 50, 35% shield, `expendable`, anti-large attributes. Dwarf
Warriors run at 2.8 m/s (first draft, S3), with armour 85 and a 55% shield.

Hypotheses. Naive: the warriors march at the nearest goblins under two lobbers' fire and
the cannon shoots the nearest unit, the goblins in front. Winning: the cannon kills or
routs the lobber crews first while the warriors wait out of their range, then the
warriors advance on goblins with no supporting fire. Main risk: an earlier measurement put
artillery at about one crew kill per three shots, so 22 rounds may not silence two
lobbers; inaccurate lobbers may not threaten armoured, shielded dwarfs (trivial). Lowest
confidence of this batch. Floor: `attack_nearest`. Diagnostic `CounterBattery`:
the cannon shoots visible artillery first (moving to 90% of its range when out of
range); the warriors wait 30 m beside the gun while enemy artillery is visible, attacking
only an enemy within 60 m of it, then attack the nearest enemy. Overlap: S4 protects artillery, and
siege firing positions; here artillery is the target.

## Definitions not declared

S12, rally and leadership. A lord and two infantry units against three: withdraw a
wavering unit out of melee to rally near the lord, then return it. The observation shows
the UI leadership fraction and the largest morale effect, but a lord aura's radius is not
public, and a scripted rally rule depends on routing behaviour the earlier S1 retry found
fragile. Deferred until a live probe shows a rally window.

S13, fatigue. Infantry that runs the whole approach arrives tired against a fresh
defender. The observation has fatigue, but the AI's own pace decides most of the effect,
and the walk/run floors already differ in other scenarios. Weak as a standalone skill;
better measured as a factor in S6 or S10.

Considered again and still set aside: flyers diving on artillery (S4's skill),
chariot cycle charges (S1), hidden-unit ambush (the AI decides whether to hide).
