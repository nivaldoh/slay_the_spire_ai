# WH3 tactic cards

The benchmark definition the owner started on 2026-10-18, with the evolving card list. A
draft: written overnight under the owner's delegation, every check below is proposed and
none is agreed, so every result is unverified ([hard rule](../../AGENTS.md#verification-hard-rule)).
The contract, timing and outcome rules it builds on are in [benchmark.md](benchmark.md);
running jobs in [benchmark-run.md](benchmark-run.md).

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
4. **Signature**: the witness's wins show the signature.
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
the cost per battle and the failure rate. Cards are controller-agnostic, so the same suite
later compares harnesses (owner, 2026-10-18: multi-agent delegation, MCP tools and other
features) as a third axis beside model and mode; a harness's own automation is disclosed in
its controller card. The active-strength margin is secondary: it
ranks floors wrongly on objective battles (on the siege `hold` scored +0.11, above every
Luna and GLM loss).

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
   full strength (S2).

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
| `pin-then-rear` (S1) | one rider pins the braced halberds in melee, the other then charges their rear; repeat | none found; a pinned block kept facing the pinning rider in 4 of 4 traced cycles, while an unengaged one re-faced in 1.2-3.6 s, so triggering on the pin tolerates a model's delay | declared (S1); witness `PinThenRear` |
| `chariot-cycle` | a chariot charges, pulls out and charges again instead of grinding | grinding may win (armour 80); a move straight through the enemy may beat pulling out | declared; witness `CycleCharge` |
| `cycle-charge-knights` | knights against Greatswords, the same cycle | `HammerAnvil` with no infantry never charges (a live defect in S6) | draft |
| `screen-the-gun` (S4) | an escort keeps riders off a Helblaster | the AI splits its riders, so one guard cannot screen; with one rider and more infantry it may hold | draft |
| `hand-kite` (S2) | kite Slayers by hand | arrows kill at 20-80 m, not at the kiting band; engine skirmish does it anyway | draft, needs a slower chaser |
| `anvil-rear-charge` | infantry pins, knights hit the rear | duplicates `pin-then-rear` | dropped |

**One unit used correctly**

| Card | Tactic | Critic's main objection | Status |
|---|---|---|---|
| `rifle-lane` | Handgunners keep a firing lane past their own Spearmen while faster Big 'Uns attack | a blocked lane cut fire to about 40% in the S3 floor, not to zero; the lane must decide the battle and should change more than once | declared (`emp-handgunners-grn-bigguns`), foils first |
| `wizard-cast-and-hold` (S5) | a wizard's few spells land on enemies away from its own line, without cancelling them | Fireball at the nearest enemy (`FireballSpam`) may win, since the recharge, not the pool, limits casting; the prompt implies a move can accompany a cast | declared (S5); foil `FireballSpam` |
| `monster-target` | a Giant reaches the guns past the halberds | the old S9 roster made attack-nearest likely to win; Halberdiers plus Handgunners near cost parity | declared (`grn-giant-emp-halberds-handgunners`); witness `MonsterTarget` |
| `cannon-outrange` (S11) | a cannon fights from outside the Rock Lobbers' reach | the traces show the cannon stood inside the lobbers' range; grade time inside the band | draft |
| `giant-shooter-first`, `horse-archers-charge-crossbows` | earlier forms | merged into `monster-target`; a frontal charge wins | dropped |

**Knowledge of a concept, and one key decision**

| Card | Tactic | Critic's main objection | Status |
|---|---|---|---|
| `flyers-priority` | Screamers fly past halberd Stormvermin to kill the Warp Lightning Cannon shelling the ground unit | the drafted target, a 3,700 HP Grey Seer, kills Screamers; a fragile artillery target and a ground unit listed first (so the commander flag is not on a flyer) | declared (`tze-screamers-skv-cannon`); witness `PriorityStrike` |
| `slaves-hold-the-halberds` | Skavenslaves are spent to hold the halberds while the Rat Ogres strike the guns | the ogres outrun the halberds, so no pin is needed unless the anti-large threat can reach them; the first card carries the commander flag | declared (`skv-ogres-slaves-emp-halberds`), foils first |
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
