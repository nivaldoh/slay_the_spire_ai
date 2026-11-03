# Sources for the Boris battle proposals

Inspected 2026-11-03 for the [scenario catalogue](boris-scenarios.md). Excerpts below locate
supporting passages; they do not establish live recruitability, tactical effectiveness or
current competitive rankings. The armies and experimental contrasts are original proposals.
The repository targets patch 9.0.4, Steam build 25961564 in
[runtime.py](../../src/twwarhammer3/engine/runtime.py); no game was launched for this research.

## Ownership and army content

| Source | Exact short excerpt | Scope and credibility |
|---|---|---|
| [SEGA new player FAQ](https://support.sega.com/hc/en-gb/articles/51224684758929-Total-War-WARHAMMER-A-New-Player-Survival-Guide-FAQ), updated 2026-09-24 | “A core roster of units from the race of the Legendary Lord”; “Every player receives Bretonnia for free” | Publisher's entitlement explanation. The ownership, Free-LC and multiplayer questions support Boris-only access and different collections playing together. It does not audit this Steam account or certify every custom AI slot |
| [Boris Steam listing](https://store.steampowered.com/app/3589670/), released 2026-09-24 | “Total War: WARHAMMER III ownership is not required.” | Publisher's product description explicitly resolves the generic Steam base-game banner. Lists four characters, seven regular units and three RoRs; campaign temple features are labelled separately |
| [CA Meet Boris](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/107), 2026-09-14 | “they’re at their best when trading blows” | Developer's White Wolf description; also describes Panther shock cavalry, Ulric support, hounds, Teutogen sundering, Wolf-Kin and Hurricanum. Qualitative launch design, not present costs or a matchup study. Web fetches were intermittent; direct HTML supplied the article text |
| [Official Empire roster](https://wiki.totalwar.com/w/The_Empire_Army_Roster.html), original WH1 reference | “a comprehensive and flexible mix of units” | Official historical core-roster reference. Establishes unit families, not modern account permissions or ownership of Karl Franz/Gelt through Boris |
| [The Grim and the Grave](https://store.steampowered.com/app/404013/), 2016 | “Free Company Militia” | Official product list separates this paid infantry and its other additions from the original core. Ignore user review opinions on the store page |
| [The Hunter and the Beast](https://store.steampowered.com/app/1074320/), 2019 | “War Wagon (Mortar)” | Official product list for Archers, Huntsmen and wagons. It is not permission to recruit them with Boris alone |
| [SEGA Thrones of Decay release](https://www.gamespress.com/THRONES-OF-DECAY-IS-OUT-NOW-FOR-TOTAL-WAR-WARHAMMER-III), 2024-04-30 | “Steam Tank Volley Gun, Nuln Ironsides, Hochland Long Rifles” | Publisher's press release hosted by Games Press. Distinguishes Elspeth's paid units from ordinary Steam Tanks and Handgunners; separately describes the free Gold Wizard |

The [second-account note](gcp-client-setup.md#3-your-steam-session) is local evidence of
Swordsmen/Spearmen recruitability, not evidence for all units in the catalogue. The older
statement that the second account owned the full base roster was superseded by the owner's
clarification in [owner-direction.md](../owner-direction.md). No local primary-account
roster dump was used to certify the second account.

## Mechanics and competitive context

| Source | Exact short excerpt | Scope and credibility |
|---|---|---|
| [CA patch 9.0.3](https://community.creative-assembly.com/total-war/total-war-warhammer/forums/7-patch-notes-amp-announcements/threads/16126-total-war-warhammer-iii-patch-9-0-3), 2026-10-09 | “only active while the unit is winning combat” | Staff patch notes, Empire section: revised Crush the Weak, Teutogen animation/attributes and unit pricing. Supersedes launch-era trigger advice. No numeric combat multiplier is adopted by the cards |
| [Multiplayer balance proposal](https://community.creative-assembly.com/total-war/total-war-warhammer/forums/15-multiplayer-battles/threads/16034-community-sourced-peer-reviewed-balance-recommendations-dlc-balance-for-lords-of-the-end-times), 2026-10-02 | “the various prayers of the Priest of Ulric end up costing more” | First-hand community proposal by CatholicAlcoholic, on CA's forum, not CA policy or a statistical study. Its Empire section questions support cost, Teutogen performance and Hurricanum aura range. Its proposed stat changes are not implemented rules; it predates 9.0.3 |
| [CA patch 5.1](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/23), 2024-06-24 | “a capture point in the centre of the map” | Developer source for Conquest's purpose, map names, Domination AI/reinforcements and displayed capture weight. Historical ticket numbers and costs were not copied into the proposals |
| [CA Academy terrain guide](https://academy.totalwar.com/battle-deployment-and-battle-terrain/), WH2 | “Units moving through shallow water receive a serious penalty” | Older official terrain tutorial, indexed text accessible; direct availability varies. Foundation for terrain experiments only. No specific WH3 speed/attack/forest multiplier or guaranteed firing arc is asserted |
| [CA interview at TheSixthAxis](https://www.thesixthaxis.com/2016/03/23/interview-creative-assembly-on-total-war-warhammers-vampire-counts-heroes-variety/), 2016-03-23 | “their units don’t rout, but they do crumble over time” | Direct statement by project lead Ian Roxburgh, a primary historical mechanics source. Motivates separate undead diagnostics; current exact crumbling/healing behaviour remains a live-check dependency |
| [CA patch 4.2](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/2), 2024 | “recharging their magical barriers” | Developer description of Tzeentch support establishes barrier recovery as a distinct mechanic. Not a source for recharge delay, every unit's barrier value, or the proposed army's strength |
| [Total Tavern September event](https://totaltavern.com/tournaments/jxinqthz2ricyuajca8yn8ar), scheduled 2026-09-21 | “Ultra Unit Scale”; “Unit Caps On” | Organiser's indexed event text gives settings. Direct page was a loading shell. Used only as an explicitly limited example of event-specific rules, not evidence of outcomes or the post-DLC metagame |
| [Total Tavern June event](https://totaltavern.com/tournaments/a3ij06vmybgpiqq5wz2bdch4), scheduled 2026-06-08 | “Total Tavern Tournament Map Pack version (Mod Required)” | Organiser's indexed text; direct page was a loading shell. Demonstrates why tournament map versions cannot silently substitute for vanilla. No leaderboard or replay statistics were recovered |

The community proposal is useful precisely as a source of testable doubts. Cost matters in
a capped competitive roster, while our fixed-army control tasks do not test drafting value.
Newer price changes cannot prove that a unit is now strong, or that a larger model benefits
from it. No tier list, current win rate, exact balance claim or video-only observation was
adopted. Custom-lobby spell/item selection, current unit tooltips and effect checks remain
explicit prerequisites for the magic, recovery and concealment cards.

## Repository interface and experimental design

Inspected at the catalogue's base revision `e449032`:

* [mailbox.py](../../src/twwarhammer3/engine/mailbox.py), unit and terrain contract:
  `barrier` is separate from HP; terrain rows describe clear/blocked movement cells.
* [llm.py](../../src/twwarhammer3/battle/llm.py), unit rendering, displays barrier values
  when supplied; an optional field is not guaranteed reliable evidence in every battle.
* [team.py](../../src/twwarhammer3/battle/team.py), `TeamPolicy`, `project` and `ModelTeam`:
  two members, type-based ownership, limited ally state and the fixed model partition.
  [Implementation notes](multi-agent-implementation.md) record the lack of explicit messages
  and the team path's injected-delay restriction.
* [battle-types.md](battle-types.md): existing example map names/keys and the missing siege
  entry orders. Previous mode examples do not establish these new roster recipes.
* [benchmark-initial.md](benchmark-initial.md): engine timer versus wall-clock caps.
  [benchmark.md](benchmark.md) and [tactics-evaluation.md](tactics-evaluation.md) govern
  information boundaries, outcomes and distinction between execution and useful tactics.
* [SMACv2 profile](benchmark-references/smacv2.md): reuse its inspected research-repo files,
  `distributions.py` and `wrapper.py` at `577ab5a`, for declared start/composition variation.
  This research does not rerun StarCraft experiments or import their sampling counts,
  hidden-state access, fixed-step clock or timeout semantics.

## Search coverage and limits

Query families used: `Lords of the End Times standalone Boris access roster`;
`Boris Todbringer Steam`; `SEGA new player FAQ`; `Meet Boris Todbringer`;
`Empire army roster`; `Patch 9.0.3 Crush the Weak`; `Empire End Times multiplayer`;
`Total Tavern 2026 rules`; `Everchosen 2026 rules`; `Tzeentch barrier`;
`Vampire Counts crumble`; and the three older Empire DLC names with their unit names.
Developer/publisher sources were prioritised. Search snippets led to full official pages
where accessible; the two tournament entries and older Academy text retain explicit
index-only limits. No claim rests on a search-result title alone.

`um kb search 'Total War Warhammer III'` returned a Valkia campaign-mod note. It has no
bearing on Boris ownership or battle balance. Direct fetches of some CA pages timed out;
the Boris and community-balance articles were recovered as HTML under the ignored
`runs/boris-scenarios/` research evidence. No archive snapshot, authenticated Discord
content, in-game screenshot, tournament replay or video transcript is claimed.
