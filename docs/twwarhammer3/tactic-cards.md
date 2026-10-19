# WH3 tactic cards

The benchmark definition the owner started on 2026-10-18, with the evolving card list. A
draft: written overnight under the owner's delegation, every check below is proposed and
none is agreed, so every result is unverified ([hard rule](../../AGENTS.md#verification-hard-rule)).
The contract, timing and outcome rules it builds on are in [benchmark.md](benchmark.md);
running jobs in [benchmark-run.md](benchmark-run.md).

## The chariot card: the first benchmark card

Built on 2026-10-18 while the owner was away (goal: "at least a single good, reliable
benchmark"), under delegation: the rule is the assistant's and not agreed, so its results
are unverified until the owner accepts a check. `battle/cards.py` holds the card, its
frozen signature and its admission rule; `twwarhammer3 card chariot [JOB_OR_PLAN_DIR ...]`
prints the board from manifests and replays, and the verdict for given jobs.

| Field | The chariot card |
|---|---|
| battle | `grn-chariot-emp-swordsmen-hard`: one Orc Boar Chariot unit (6 chariots, Greenskins, no lord) attacks two Empire Swordsmen units (90 men each) on Taurox; very hard AI, AI stats modifier 1.1, 1200 s timer; a battle takes 2-10 min |
| tactic | cycle charging: charge, pull out, charge again instead of grinding |
| why necessary | the chariot wins by routing the Swordsmen with repeated charge shock; in a long melee both units hold it and it routs, mostly with every chariot alive |
| foils | `attack_nearest` and `rush_nearest` at 0 s added age. `hold` is no foil: the AI defends, so standing still loses on the timer by the mode's rule (1205 s) |
| witness | `SnapHitAndRun` (rule disclosed in its card): attack the nearest enemy and keep it; on the first observation showing melee ride to 120 m from the enemies' centre, on its own side; charge again once 80 m from the target and 10 s after leaving |
| signature | **cycles**: engagements, other than the last, in which the controller's own move order took effect (melee runs from the 1 Hz replay, gaps under 3 s merged). Fixed before the confirmation round; a win with 0 cycles did not use the tactic, which is how the 1.0 card's rush-foil win reads |
| knowledge | withheld: the rules prompt states neither charge bonuses nor cycle charging |
| reference | the witness at model pace (5 s age and one decision per 5 s, `--interval-ms 5000`; models made about 0.2 decisions a second): reported, not a gate |

**Admission rule** (committed at `5396182` before the round; the model-pace gate was dropped
at 17:45 UTC, against E2's own rule): in fresh launches,
`attack_nearest` and `rush_nearest` each lose all of 10 (one win fails the card), and the
witness at 5 s added age wins at least 4 of 5, each win with at least one cycle. A foil
that wins 20% of its battles passes 10 straight losses 11% of the time; a witness that
wins half its battles passes 4 of 5 19% of the time.

**Score** per model and mode: wins over scored launches with a 95% Wilson interval, beside
the median cycles and order age. The battle never waits (`cards.outcome`, harness b35): a
controller failure (no valid reply, a provider error, an exception in its code) or a
truncation is a loss, labelled forfeit; game and setup failures, interrupts and operator
stops (the spend ledger and its safety stops, the account's key or credit: HTTP 401, 402) are
excluded and rerun. A foil's forfeit is no launch.

**Results at modifier 1.1** (2026-10-18, 22 scripted battles, $0; board:
`twwarhammer3 card chariot`). Exploration rounds E1 and E2 chose the witness and do not
count for admission:

| Control | Battles | Won | Note |
|---|---|---|---|
| `attack_nearest`, 0 s | 3 | 0 | 392-418 s |
| `rush_nearest`, 0 s | 4 | 0 | 138-161 s |
| `hold` | 1 | 0 | timer, 1205 s |
| `CycleCharge`, 5 s | 3 | 1 | stuck about 30 s between both units per charge |
| `HitAndRun` (2 s dwell), 5 s | 3 | 3 | no chariot lost |
| `HitAndRun`, model pace | 2 | 0 | its pull-outs applied about 14 s after contact |
| `SnapHitAndRun`, 5 s | 2 | 2 | one in E2, one in the round |
| `SnapHitAndRun`, model pace | 4 | 2 | won 467 and 625 s, lost 485 and 615 s (at 615 s one Swordsmen unit was routing as the chariot broke) |

Cycles read 0 on every foil battle, including the modifier 1.0 rush-foil win (by construction:
foils never order a move), and 6-9 on every witness win at 1.1 (witness losses read 2-8).
The confirmation round (`runs/twwarhammer3/calibration/c1`, 20 plans; 4 on 2026-10-18 at
b34, 16 on 2026-10-19 at b36) finished: foils lost 10 of 10 each, the witness won 4 of 5 at
5 s and 0 of 5 at model pace. **Admitted** under its pre-registered rule; no check is
agreed, so the card stays unverified. The start-configuration confound read as tempo, and
GLM-5.3 low won 1 of 10 ([log](log.md#2026-10-19-overnight-round-at-b36-c1-finished-p2-cells-p5a)).

**For post-training**: one unit, a fixed opponent and 2-10 minute battles make the card a
cheap environment with a binary reward (the win) and a shaping signal (cycles). Qwen3.6, the
planned student, exports through `twwarhammer3 export`; the witness is a free
demonstrator, but scripted decisions have no exported rows yet (they would need the
prompt the model would have seen at each decision).

### Card version 2 (draft, 2026-10-18 evening; not agreed)

Fixes for the review's findings, same battle; the full spec is local in
`runs/twwarhammer3/calibration/latency-review-20261018/readiness/`:
- **Start**: report each launch's start class (read from its first observation); starts cannot
  be fixed without new code.
- **Foils**: add a general-focus foil (attack the commander-flagged unit and keep it), one
  pull-out then grind, and a charge straight through.
- **Signature**: count a cycle only for a move ordered while in melee that gets the unit clear
  (30 m) before the next charge; freeze it with a test before the round.
- **Counting**: one control per launch, the first N launches in plan order, the plan list
  hashed in the card.
- **Held out**: the reserved `nur_wastes` map, once after admission.
- Open: models do not see the commander flag that scripted bots can read.

## What the benchmark measures

For outside AI researchers: which models, at which reasoning modes, can apply specific
tactics in a real-time battle that keeps moving while they think? Each test is a minimal
battle (a **card**) built so that it is won only by applying one intended tactic; a naive or
plausible wrong play loses. A few larger battles test scale and context length later.

Owner direction (2026-10-18): start from minimal battles that each test whether a model can
apply a certain tactic, and make the model win only if it uses that tactic correctly. The
list keeps evolving across five kinds, plus scale:

| Kind | Owner's example |
|---|---|
| Battle tactic | flanking, kiting |
| One unit used correctly | riflemen kept in positions with line of sight, or they deal too little damage and lose |
| Knowledge of a concept | when and how to sacrifice expendable units in armies of rats or undead |
| One key decision | flyers ignore irrelevant units to kill a well-defended Lord or spellcaster |
| A type of situation | defensive siege, offensive siege |
| Scale (later) | a large army against a large army, taxing context length |

## A card

| Field | Meaning |
|---|---|
| tactic and kind | the one thing tested, and which of the kinds above |
| setup | rosters (1-4 units a side where possible), map, battle type, role, timer, funds, AI modifier |
| why necessary | the mechanism that makes the obvious plays lose and the tactic win |
| foils | declared plays that must lose: the naive floors (`hold`, `attack_nearest`, `rush_nearest`) and at least one plausible wrong tactic |
| witness | a disclosed public-state bot (`battle/calibration.py`) that executes the tactic; later a model's or a person's win |
| signature | what the trace or replay shows when the tactic was used (charge contact angle, rounds fired with a clear lane, the flyer reaching the caster) |
| knob | what calibrates difficulty so the witness wins and the foils lose |
| knowledge | `disclosed` (the rules prompt states every mechanic the witness relies on) or `withheld` (the card tests the model's own game knowledge) |
| reaction window | how fast the tactic must react, against a 5-10 s model order age |

Necessity cannot be proven, only tested: a card is as good as its foil set. Every model win
is reviewed for the signature, and a win without it means the card leaks (the S4, S5 and S7
lessons below). The leak becomes a new foil and the card is revised.

## Proposed admission checks

None is agreed. Each would become a row in AGENTS.md's agreed methods once the owner
accepts it.

1. **Setup**: the existing lobby and first-observation checks pass (`battle/setup.py`).
2. **Foils lose**: every declared foil loses in each of its launches, two at least for the
   naive floors.
3. **Witness wins**: the witness wins by contact (not on the timer) in at least 3 of 4
   single-episode launches at 5 s added observation age (`--delay-seconds 5 --episodes 1`).
4. **Signature**: the witness's wins show the signature, and a measure of it separates
   the witness's wins from the foils' losses under a rule fixed in advance (for the chariot
   card, the longest run of melee frames; see the board below).
5. **Parity**: a `disclosed` card's rules prompt states every engine fact the witness
   relies on; otherwise the card is `withheld`.
6. **Held out**: a variant (another map or a mirrored start) is reserved before any
   model is tuned on the card.

## Score

The sampling unit is the launch: one new game start, one episode. A rematch restarts the
same instance, so repeats inside a launch are not extra samples. Per model and mode, per
card: contact wins over launches started, with a 95% Wilson interval. Policy failures and
truncations count as losses; infrastructure failures are listed and rerun. Across cards:
the mean of the per-card win rates, each card weighted once, beside the median order age,
the cost per battle and the failure rate. Each card also reports its signature measure
per battle, so a loss that attempted the tactic (Luna on the chariot card pulled out, then
stayed out of contact for minutes) reads differently from one that never tried it. A card whose witness
wins only with fresh information (S1 so far) is a **latency card**: it is reported beside
the order age and is not averaged with the others. Cards are controller-agnostic, so the same suite
later compares harnesses (owner, 2026-10-18: multi-agent delegation, MCP tools and other
features) as a third axis beside model and mode; a harness's own automation is disclosed in
its controller card. The active-strength margin is secondary: it
ranks floors wrongly on objective battles (on the siege `hold` scored +0.11, above every
Luna and GLM loss).

## The first checks (night of 2026-10-18)

Single-episode launches on the declared cards, counts as of the end of the night (the
[log entry](log.md#2026-10-18-tactic-cards-harness-b28-to-b30-and-the-overnight-checks) has
every battle). Foils and witnesses are free scripted controllers; model battles are paid.
Every cell is n = 1 to 4 launches, no check is agreed, OpenRouter backends were unpinned
(each attempt records its backend) and the rules prompt is v20, so every result is
unverified. An independent four-lens check of the draft against the register, traces and
replays corrected it before it was written here.

| Card | Kind | Foils (one launch each) | Witness | Models (natural latency, one battle each) | Status |
|---|---|---|---|---|---|
| chariot cycle (`grn-chariot-emp-swordsmen`) | battle tactic, one unit | attack-nearest lost 2 of 2 (462, 413 s); rush-nearest lost 154 s, then **won** 157 s without cycling (longest melee 55 frames) | `CycleCharge` at 5 s: won 4 of 4 (338, 204, 281, 309 s), no chariot lost | won: Kimi K3 low (232 s), gpt-6.1-sol low (256 s), Kimi K3 high 1 of 2 (139 s; its second launch lost at 182 s); lost: Qwen3.6 none and medium, Luna low and high, GLM-5.3 low and high, Step 5 low and high (the slowest four mostly by latency) | **leaks**: a naive foil won 1 of 2, so check 2 fails; step it harder (for example modifier 1.1) until rush-nearest loses while `CycleCharge` wins. Also missing a `hold` foil, the knowledge tag (withheld: the prompt does not state cycle charging) and a held-out variant. The first small scenario a model has won, though the leak lowers what those wins show |
| chariot cycle at modifier 1.1 (`grn-chariot-emp-swordsmen-hard`, b31, after the leak) | battle tactic, one unit | rush-nearest lost 2 of 2 (138, 154 s); attack-nearest lost 409 s | `CycleCharge` at 5 s won 1 of 3 (won 390 s; lost 327 and 255 s) | none yet | **too hard for the witness**: between 1.0 (a rush foil can win) and 1.1 (the witness mostly loses); next a finer step (a modifier between them is unverified) or another single factor |
| expendables, one halberd unit (`skv-ogres-slaves-emp-halberds-1`) | concept | attack-nearest lost 173 s; hold lost 337 s | `SlaveTarpit` at 5 s: won 3 of 4 (190, 243, 283 s; lost 319 s) | won: Kimi K3 low (308 s); its repeat ended at 102 s on an OpenRouter credit error (HTTP 402, infrastructure, recorded as a policy failure); lost: Luna high (649 s), Kimi K3 high (418 s: its order to pin the halberds applied 135 s late), Qwen3.6 none (240 s); GLM-5.3 high ended in a policy failure (461 s) | **candidate**: checks 1 and 3 met; each foil ran once; knowledge withheld; no held-out variant; the commander flag sits on a slave unit, so spending it costs the army's commander |
| S1 flank (`ksl-raiders-emp-halberds`) | battle tactic | attack-nearest (b14) and rush-nearest (b15) lost | `PinThenRear`: won 0 of 2 at 5 s (two timings); fresh 1 of 2 (the first timing won, the tighter one lost) | gpt-6.1-sol low **won** 305 s (3.6 s mean order age: one rider drew the halberds' facing while the other charged their rear, then they swapped); its repeat stopped at 40 s on the OpenAI cap (`budget_exhausted`, not a result); Kimi K3 high lost 419 s (24 s mean order age; it planned the same pincer); 0 of 9 before tonight (5 lost, 4 policy failures; b18-b24) | **candidate**: a model won where the scripted witnesses lost at 5 s, so the bots, not the card, set the 5 s limit; latency-sensitive (the same plan failed at 24 s) |
| flyers on the cannon (`tze-screamers-skv-cannon`, `-1`) | key decision | lost 3 of 3, and attack-nearest routed the cannon too (219 s, 261 s) | `PriorityStrike` at 5 s lost 2 of 2: it routed the cannon crew at about 100 s, which rallied, while its own rule turned the Screamers onto the screen | none | neither necessity nor sufficiency shown: test a witness that keeps the target until it is dead or keeps the flyers off the screen |
| riflemen lane (`emp-handgunners-grn-savage-orcs-hard`) | one unit | attack-nearest lost 212 s | `FlankLane` at 5 s: 1 of 2; the win fired as many rounds as the foil (277 against 274) | none | no reliable witness: line of sight is not observable, and walking to a lane cost firing time |
| giant target (`grn-giant-emp-*-handgunners`) | one unit | lost on both steps | `MonsterTarget` at 5 s: 0 of 3 across two steps | none | no win yet: on the halberd step the witness routed the guns (171 s) and then lost; on the spearmen step it never reached them |
| S5 caster (`emp-wizard-emp-swordsmen`, `-hard`) | one unit | floors lost | `SpellWindow` at 5 s won 2 of 2 | none | **dropped** as a spell-judgment card: `FireballSpam` (Fireball at the nearest enemy) won at modifiers 1.0 and 1.1 |

The chariot card's signature, a per-battle grade rather than a cause: the longest run of
consecutive 1 Hz replay frames in which the chariot carries the engine's melee flag
(whatever its movement flags), was at most 31 frames in all 7 wins that used the tactic (4 witness, 3 model) and at least 41 in all 12 losses (3 foils, 9 model battles); the one foil win (rush-nearest) had 55, so the measure flags a win without the tactic, which is its purpose. The threshold was read off these battles,
and merging brief exits from melee changes the numbers (by that count the witness's longest
engagement is about 33 s), so the rule needs fixing before it is a check. Luna / low pulled
out once at about 134 s and stayed out of contact for about 460 s (15 refused moves) before
grinding to a rout; Luna / high pulled out five times, but its fourth melee lasted 42 s.

What the night showed about the definition itself:
- **Foils first is cheap and decisive, and one launch per foil is too few.** One drafted
  card (riflemen) needed two roster steps on its first foil alone, a careless-play foil
  (`FireballSpam`) sank S5 after its witness had won 2 of 2, and the chariot card's
  rush-nearest foil lost its first launch and won its second (the last battle of the night).
- **A witness win is what tests sufficiency.** The two-halberd expendables card and the
  halberd giant step saw the tactic executed (the guns routed) and the battle still lost; a
  one-factor step gave the expendables card its first witness wins.
- **A model win can be read against the tactic.** Each of the 3 model wins on the chariot
  card was planned as cycle charging in the model's own notes (Kimi K3 high: "pull out
  southwest and immediately queue a re-charge"); two ordered pull-outs from melee, while Kimi
  K3 high's one move batch was decided between engagements, and on the expendables
  card Kimi K3 low routed the guns while the slaves held the halberds. Kimi K3 high also
  planned the right play on the expendables card and on S1, and lost both when its orders
  arrived 24-135 s late: knowing the tactic and executing it in time are separate results.
- **A model can beat the scripted witness.** On S1 gpt-6.1-sol alternated a feint and a
  rear charge and won, where both `PinThenRear` timings lost at 5 s; a witness's loss
  bounds the bot, not the card.
- **One launch is a screen, not a ranking.** Kimi K3 high won its first chariot launch and
  lost its second; per-cell results need several launches before they rank models.
- **Reasoning effort against order age, one battle per mode:** a higher mode raised the mean
  order age for Luna (4.8 to 8.8 s; medians 4.5 to 7.2 s) and GLM-5.3 (3.1 to 7.7 s), not
  for Kimi K3 (4.5 s both). Step 5 high's replies took 6 to 370 s (2 of 4 cut off at the
  16,000-token cap) and one order batch reached the game before the chariot routed at 139 s;
  Qwen3.6 medium's only applied order was 102 s old (4 of its 6 replies were rejected). No
  battle of a mode above low ended in a policy failure; 3 replies hit the cap.

## Design rules from S1-S11

What made the small scenarios fail the "won only with the tactic" property, as rules for a
new card (from the 2026-10-17 board and traces; each rests on 1-6 battles):
1. **Foils and witness on the same start**, at 0 and 5 s added age, with a "partial
   tactic" foil (S4's escort won while the gun it guards always fell).
2. **The tactic's resource must deliver the decisive damage**, and any substitute must
   fall short alone (S5's Fireball kiting won without the spell window).
3. **Close the timer**: the player attacks, or a defender's timeout needs forced contact
   (S7's corner hold won on the timer without contact).
4. **Neutralise engine automation and AI quirks**: run the floors with the default
   skirmish, fire-at-will and guard settings, and drop cards the AI makes trivial (S2:
   skirmish mode kites by itself; S10: the AI charges braced spears head-on).
5. **The window must outlast a 5-8 s order age**, or latency decides instead of the tactic
   (S1's halberds re-face in 3-5 s when unengaged).
6. **Open ground**: check every key point against the terrain grid (refusals on the
   Taurox rock broke S2, S3 and S6).
7. **Climb in fine steps from a witness win**: four of five unit-count step-downs went from
   too hard to too easy. The 1.1 modifier gives about +10% stats and +8 leadership; values
   below 1.0 are unverified.
8. **Control confounds**: a lordless army's commander flag sits on its first card and that
   captain's death cuts every unit's morale (S3); an "army losses" shock can rout a unit at
   full strength (S2). The flag does not always follow the first card: in the expendables
   card it went to a Skavenslaves unit although the Rat Ogres were listed first (b28).
9. **Sufficiency, not only necessity**: once the tactic succeeds, the rest of the battle
   must be winnable. On 2026-10-18 the two-halberd expendables witness routed the guns at
   160 s and the halberd giant witness at 171 s, and both still lost to the anti-large unit
   left standing while their foils also lost (n = 1 each). The witness is what tests this.
10. **A witness must not abandon a routing target**: a routed unit can rally (the cannon
   crew did); keep it until it is dead or off the field before switching.

## The card list (draft 1, 2026-10-18)

Drafted by four agents (one per kind) and attacked by four adversarial critics, each trying
to win every card without its tactic (read-only: traces, the game database, the
observation reference; the full panel output is not kept in the repository). Status:
*declared* (a scenario entry exists), *draft* (defined only) or *dropped*. The critic's
main objection is the risk to check first; "foils first" means the naive floors run before
any witness is written or counted.

**Battle tactics**

| Card | Tactic | Critic's main objection | Status |
|---|---|---|---|
| `pin-then-rear` (S1) | one rider pins the braced halberds in melee, the other then charges their rear; repeat | none found; a pinned block kept facing the pinning rider in 4 of 4 traced cycles, while an unengaged one re-faced in 1.2-3.6 s, so triggering on the pin tolerates a model's delay | declared (S1); see the board |
| `chariot-cycle` | a chariot charges, pulls out and charges again instead of grinding | grinding may win (armour 80); a move straight through the enemy may beat pulling out | declared; see the board |
| `cycle-charge-knights` | knights against Greatswords, the same cycle | `HammerAnvil` with no infantry never charges (a live defect in S6) | draft |
| `screen-the-gun` (S4) | an escort keeps riders off a Helblaster | the AI splits its riders, so one guard cannot screen; with one rider and more infantry it may hold | draft |
| `hand-kite` (S2) | kite Slayers by hand | arrows kill at 20-80 m, not at the kiting band; engine skirmish does it anyway | draft, needs a slower chaser |
| `anvil-rear-charge` | infantry pins, knights hit the rear | duplicates `pin-then-rear` | dropped |

**One unit used correctly**

| Card | Tactic | Critic's main objection | Status |
|---|---|---|---|
| `rifle-lane` | Handgunners keep a firing lane past their own Spearmen while faster Big 'Uns attack | a blocked lane cut fire to about 40% in the S3 floor, not to zero; the lane must decide the battle and should change more than once | declared, stepped to Savage Orcs at 1.1; see the board |
| `wizard-cast-and-hold` (S5) | a wizard's few spells land on enemies away from its own line, without cancelling them | Fireball at the nearest enemy (`FireballSpam`) may win, since the recharge, not the pool, limits casting; the prompt implies a move can accompany a cast | dropped as a spell-judgment card; see the board |
| `monster-target` | a Giant reaches the guns past the halberds | the old S9 roster made attack-nearest likely to win; Halberdiers plus Handgunners near cost parity | declared, two steps; see the board |
| `cannon-outrange` (S11) | a cannon fights from outside the Rock Lobbers' reach | the traces show the cannon stood inside the lobbers' range; grade time inside the band | draft |
| `giant-shooter-first`, `horse-archers-charge-crossbows` | earlier forms | merged into `monster-target`; a frontal charge wins | dropped |

**Knowledge of a concept, and one key decision**

| Card | Tactic | Critic's main objection | Status |
|---|---|---|---|
| `flyers-priority` | Screamers fly past halberd Stormvermin to kill the Warp Lightning Cannon shelling the ground unit | the drafted target, a 3,700 HP Grey Seer, kills Screamers; a fragile artillery target and a ground unit listed first (so the commander flag is not on a flyer) | declared, two steps; see the board |
| `slaves-hold-the-halberds` | Skavenslaves are spent to hold the halberds while the Rat Ogres strike the guns | the ogres outrun the halberds, so no pin is needed unless the anti-large threat can reach them; the first card carries the commander flag | declared, stepped to one halberd unit; see the board |
| `general-on-a-leash` | pull a Pegasus general out of melee before it dies | the general is too strong for the drafted enemy; needs a real lord-killer | draft |
| `undead-screen` | a Necromancer's Zombies are fed in as a screen; the army crumbles if he dies | Vampire Counts availability is unverified | draft, lobby probe first |
| `save-the-rounds`, `shoot-the-necromancer` | ammunition rationing; unbreakable undead | guns ended every traced battle with most rounds; the frontal floor likely wins | dropped |

**A type of situation**

| Card | Tactic | Critic's main objection | Status |
|---|---|---|---|
| `siege-keep-the-key` | concede the walls and hold the Key Building under towers | the AI gets inside without breaching the gate, so the breach is not a choke | draft; the existing `chd-reserve-grn-siege` (Sol-class 6/7, Luna 1/4) stands in |
| `siege-air-assault` | flyers skip the garrison for the one point that drains tickets | untested whether ground units climb the walls on a plain move | draft, probe first |
| `conquest-race-and-hold` | a fast unit captures first; the infantry holds the point without chasing | every conquest battle so far ended by rout before 600 tickets | draft |
| `domination-two-of-three` | hold two of three points with the least force | passive income and buy-backs decide the scripted foils | draft |
| `ffa-third-party` | strike the survivor after the AIs fight | a remnant of armoured Dwarfs cannot be finished: a draw | draft |
| `scale-ladder` | the same tactic at 1x, 2x and 3x army size | build it on a card that has passed; siege supplies do not scale | draft, blocked |

More candidates the critics found missing (not yet drafted): concentration of force,
re-facing against a flank attack, a lure into a kill zone, envelopment with a wide line,
counter-charging cavalry, unit rotation, dispersal under artillery, pursuit discipline,
holding fire to spare one's own screen, the minimum-range dead zone of artillery, a
hidden approach with Gutter Runners, fire against regeneration, magic against ethereal
units, matching armour-piercing units to armoured targets, reserve timing, terror against
low leadership, siege sallies, holding until reinforcements arrive, an AI ally, and long
battles that load the context.

## What only WH3 battles can test

From a survey of game and real-time agent benchmarks (2026-10-18, sources below, not
re-checked beyond their abstracts and pages). The gaps a real-time Total War benchmark
fills, as design targets rather than shown results:
- **Thinking costs battlefield time, network included, against an opponent, from
  structured state.** The StarCraft II language-model benchmarks pause the game, wait for
  the model or script the unit control ([TextStarCraft II](https://arxiv.org/html/2312.11865v3),
  [LLM-PySC2](https://arxiv.org/html/2411.05348v2), [Orak](https://arxiv.org/html/2506.03610v2):
  "we pause the StarCraft II game environment"); SMAC is lockstep and not built for language
  models ([SMACv2](https://arxiv.org/abs/2212.07489v2)). The real-time ones have no opponent
  or are pixel-based ([VideoGameBench](https://arxiv.org/abs/2505.18134v2)), are uncontrolled
  model-against-model fights ([LLM Colosseum](https://github.com/OpenGenerativeAI/llm-colosseum)),
  or count generated tokens instead of seconds
  ([Real-Time Reasoning Gym](https://arxiv.org/html/2511.04898v1)).
- **Reasoning mode as a measured axis**: every mode of every model on the same card, with
  the order age it produced, so thinking quality and slowness can be told apart.
- **Admission by tactic.** SMACv2 found that policies ignoring their observations won many
  original SMAC maps; no surveyed suite checks which skill produced a win. Foils and a
  witness per card close that gap.
- **Objectives other than killing** (holding a victory point, spending supplies), **morale**
  (armies break before they die; the general holds them together) and **magic** from a
  shared pool whose effects land seconds after the order and can be cancelled.
- **A fixed strong opponent in a commercial engine**: rematches restart the same battle
  against the very hard AI, a steadier yardstick than model-against-model Elo.
- **Real-time traces for post-training**, each decision with its delay; the Orak and
  PokeAgent datasets come from paused or turn-based play.

Closest prior work: "Commanding an Army with an LLM: A Hybrid Controller and Trace Dataset
for Medieval II: Total War" (an [IEEE DataPort](https://ieee-dataport.org/keywords/real-time-strategy-games)
abstract; full text not found): an LLM commands an army in real time through a modding
bridge with typed actions, 60 battles against the built-in AI. What separates this
benchmark: the measured delay axis, admission by tactic, and WH3's magic, flight and factions.

Ranked opportunities (uniqueness x what it measures x readiness), each a card family:

| Opportunity | WH3 mechanic | Minimal card idea | Readiness |
|---|---|---|---|
| A manoeuvre whose window is shorter than the order delay | charge defence and reflection against large; measured order age | two light cavalry against braced halberds (S1) | now |
| Morale as a second health bar | leadership, rear charges, rout cascades, the general's death | pin with one unit, rear-charge with another; a straight fight loses (S6) | intermediate step needed |
| A shared magic pool whose effects confirm late | Winds of Magic, delayed casts, friendly fire | a wizard's few spells must land away from its own line (S5) | now |
| Holding an objective on a budget | victory point worth half the tickets, priced towers | a defender too weak in the open holds only by the key building and towers | now (defence); attack needs gate and wall orders |
| Flight as a mode decision | take-off and landing with a cooldown; "you must attack by land" | flyers land to take a point and lift off whenever pikes close in | now (unverified under fire) |
| Splitting across capture points | Domination tickets, three points | an army losing any straight fight holds two points and screens the third | now |
| Third-party timing | free-for-all; the AIs fight each other | a small army wins only by striking the survivor of the other two | four teams needed |
| Long context while the clock runs | 20-unit armies, 2400 s | a 20 v 20 battle with a scored flank on one wing (L1) | setup works |

Rules disclosed or withheld: running a card with and without a mechanics card built from
the game database separates game knowledge from reasoning; recasting a card with another
faction's equivalent units tests transfer. Not unique to WH3 (keep few such cards): focus
fire and target choice (SMAC's core), kiting and protecting a fragile unit (StarCraft II
micro; the game's skirmish mode automates kiting), fog of war, build orders, win rate
against built-in difficulty levels.
