# Sources for WH3 tactics research

Source inspection: 2026-11-01. [Catalogue](tactics-reference.md) ·
[Evaluation designs](tactics-evaluation.md). Short excerpts below identify the supporting
passage, not tactical effectiveness in our game. The catalogue's recipes, matchup choices
and experimental contrasts are hypotheses inferred from these foundations.

## Historical examples

| Source | Supporting excerpt | Use and limits |
|---|---|---|
| [US National Park Service, The Battle of Cowpens](https://www.nps.gov/cowp/learn/historyculture/the-battle-of-cowpens.htm) | “he organized his troops into three lines” | Battlefield institution's historical account: successive lines, withdrawal, cavalry intervention and envelopment. It also describes a misunderstood withdrawal order; do not portray every action as preplanned |
| [National Army Museum, Battle of Waterloo](https://www.nam.ac.uk/explore/battle-waterloo) | “out of sight of the enemy and sheltered from artillery fire” | Museum account, Positions and Let battle commence: reverse-slope shelter and the danger of overextended cavalry pursuit. No WH3 projectile or morale formula follows |
| [English Heritage, Bumper English History Quiz, question 44](https://www.english-heritage.org.uk/members-area/members-magazine/quizzes/bumper-quiz-december-2020/) | “Inconsistencies in the sources mean that we can’t be sure” | Institutional summary of Hastings and feigned retreat; explicit uncertainty about the repeated feint. Supports an analogy, not an exact reconstruction |

These institutional histories are secondary historical accounts. The research does not
claim to have resolved disputed ancient or medieval tactics, and it does not apply WH3
performance to real warfare.

## Game mechanics and changes

CA blog posts are developer sources. Official Academy material below concerns WH2;
its indexed page text was readable, but direct fetches returned 403. That access limit
and the older game version weaken it as evidence of current WH3 behaviour. Community
forum posts on CA's domain are not developer documentation and are not treated as such.

| Source and version | Supporting excerpt | What it supports here |
|---|---|---|
| [CA Academy, Battle Deployment and Battle Terrain](https://academy.totalwar.com/battle-deployment-and-battle-terrain/), WH2 | “If your missile or artillery units are obstructed by an obstacle, they won’t be able to shoot at the enemy.” | Qualitative geometry and concealment foundation; indexed text only. No current height, water or forest multipliers adopted |
| [CA Academy, Dark Elves Battle Tactics](https://academy.totalwar.com/dark-elves-battle-tactics/), WH2 | “Murderous Prowess bar which tracks deaths on the battlefield” | An example of a trigger-based faction mechanic, not verification of current thresholds or custom-battle loadouts; indexed text only |
| [CA, Update 5.0.0](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/17-total-war-warhammer-iii-update-5-0-0), April 2024 | “Barrier Recharge Delay” | UI exposes healing and barrier quantities separately. Read Battle UI Updates; current readout correctness and bridge coverage still need checks |
| [CA, Patch 5.1.0](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/23), June 2024 | “Conquest mode is essentially a Land Battle but with one key twist!” | Central capture alternative, AI Domination, capture weight, overcast UI and flaming-hit healing suppression. Numeric settings are historical; read the actual mode/loadout before testing |
| [CA, Tides of Torment Meet Dechala](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/82), November 2025 | “adept at outflanking pinned enemies” | Exalted Hero of Slaanesh as a documented pin-and-flank example. Campaign bonuses described elsewhere on the page do not imply custom-battle availability |
| [CA, Update 8.0](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/98), May 2026 | “The unit can now activate both Yin and Yang Harmony” | Sky Lantern support changed; faction-level recipes need unit-specific checks |
| [CA, Bhashiva Character Pack overview](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/97), May 2026 | “the Tiger Warriors do not make use of Battle Harmony” | Concrete exception to treating all Cathay units as Harmony recipients |

The catalogue does not copy patch-specific charge timings, healing percentages, spell
costs, capture weights or resistance formulas. Many familiar mechanical details remain
explicit preconditions to check, especially bracing, charge extraction, crumbling versus
instability, spell targeting, hiding, terrain penalties and siege interactions. There is
no claim that a unit-by-unit database audit or live mechanics test was performed here.

## Repository and benchmark references

- [benchmark.md](benchmark.md): owner-governed task, timing, outcome and information rules.
- [benchmark-references.md](benchmark-references.md) and its BEHAVIOR, CARLA and SMACv2
  profiles: inspected source revisions, task construction and evaluation lessons.
  This research reuses those profiles; it does not reproduce their experiments.
- [tactic-cards.md](tactic-cards.md): historical screens and their failure cases; especially
  automated skirmishing, substitutes for the intended tactic and escort-only success.
  Those cards' admission rules do not replace the current general benchmark definition.
- [battle-types.md](battle-types.md) and [integration.md](integration.md): recorded mode
  capabilities and engine evidence, with their original scope limits.
- [mailbox.py](../../src/twwarhammer3/engine/mailbox.py),
  [protocol.py](../../src/twwarhammer3/protocol.py),
  [battle Lua](../../src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua): current
  fields, visibility boundary and orders, inspected as source rather than live effects.

## Search coverage and access limits

Search families used: official WH3 battle tactics/Academy; Tzeentch barrier; Slaanesh
flanking; Cathay Battle Harmony; Conquest/Domination and capture weight; siege changes;
Waterloo reverse slope; Cowpens; Hastings feigned retreat. Queries included
`site:academy.totalwar.com`, `site:community.creative-assembly.com`, and institution names.
The modding knowledge-base search returned a Valkia campaign-mod note, which does not
answer battle-tactics questions and was not used as tactical evidence.

Several old `totalwar.com/blog/` roster/siege pages, a manual fetch and a Wayback CDX
lookup were unavailable. They were replaced where possible by accessible developer patch
notes; no successful archive snapshot is claimed. Indexed Academy text supports only the
explicitly limited historical foundation above. No video transcript or visual/mechanics
claim was verified from screenshots. Community video descriptions supplied search leads,
not evidence for exact timings or current competitive strength.

This is a reusable reference and candidate evaluation design, not an exhaustive review
of every DLC, competitive ruleset, faction or tactic. For a selected experiment, inspect
the exact current loadout and recheck patch-sensitive mechanics in the pinned game.
