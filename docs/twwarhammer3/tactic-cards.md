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
| signature | **cycles**: engagements, other than the last, in which the controller's own move order took effect (melee runs from the 1 Hz replay, gaps under 3 s merged). Fixed before the confirmation round; a win with 0 cycles did not use the tactic, which is how the 1.0 card's rush-foil win reads. It counts pull-out attempts: witness wins read 4-21 and witness losses 1-15, so it flags the tactic and does not separate wins from losses |
| knowledge | withheld: the rules prompt states neither charge bonuses nor cycle charging |
| tolerance | `SnapHitAndRun` by added age / decision interval, every launch of each cell on the board (3-8 a cell, unverified): 0/0 won 4 of 4, 0/5 3 of 3, 2/2 4 of 4, 3/3 3 of 4, 5/0 5 of 6, 5/5 2 of 8, 8/8 0 of 4. Added age and interval round up to the 1.2 s observation cadence: the 2/2 cell runs at 2.7 s age and period, 5/5 at 6.3 s. On one axis, the time-average age of the order in force (median order age plus half the decision gap; the board's `info age`), the cells order monotonically: 0.5 s 4/4, 3.5 s 3/3, 4.1 s 4/4, 5.6 s 5/6, 5.9 s 3/4, 9.5 s 2/8, 13.2 s 0/4. GLM-5.3 low sits at 3.4 s and Qwen3.6 none at 4.2 s, where the witness won 11 of 11. The slow cells' losses read as a withdrawal stall of this recipe, so the curve bounds the tactic's tolerance from below until witness v2 runs ([second pass](#second-pass-2026-10-19-evening-findings-and-the-version-2-decisions)) |

**Admission rule** (committed at `5396182` before the round; the model-pace gate was dropped
at 17:45 UTC, against E2's own rule): in fresh launches,
`attack_nearest` and `rush_nearest` each lose all of 10 (one win fails the card), and the
witness at 5 s added age wins at least 4 of 5, each win with at least one cycle. Operating
characteristics: a foil that wins 20% of its battles passes 10 straight losses 11% of the
time (10 losses bound a foil below 0.26, one-sided 95%); a witness that wins half its
battles passes 4 of 5 19% of the time, and one that wins 80% fails it 26% of the time. The
gate witness decides about three times a second on 5 s-old information, a regime no model
is in; the tolerance row above is the evidence at model-like cadences. Each c1 foil launch
rotated both foils, so each foil's 10 battles are on 10 instances shared with the other foil
(`attack_nearest` played the fresh start in 3, `rush_nearest` in 7; the rest were rematches
of the instance the other foil had just played). `cards.outcome` changed after
pre-registration (b35, forfeits) with no effect on c1, which has no forfeit.

**Score** per model and mode: wins over scored launches with a 95% Wilson interval, beside
the median cycles and order age. The battle never waits (`cards.outcome`, harness b35): a
controller failure (no valid reply, a provider error, an exception in its code) or a
truncation is a loss, labelled forfeit; game and setup failures, interrupts and operator
stops (the spend ledger and its safety stops, the account's key or credit: HTTP 401, 402) are
excluded and rerun. A foil's forfeit is no launch.

**Results at modifier 1.1** (board: `twwarhammer3 card chariot`). The exploration rounds
E1 and E2 (2026-10-18, 22 scripted battles, $0) chose the witness and do not count for
admission; their table is in git (`git show 9df420f:docs/twwarhammer3/tactic-cards.md`).
Cycles read 0 on every foil battle, including the modifier 1.0 rush-foil win (by construction:
foils never order a move), and at least 4 on every witness win at 1.1.
The confirmation round (`runs/twwarhammer3/calibration/c1`, 20 plans; 4 on 2026-10-18 at
b34, 16 on 2026-10-19 at b36) finished: foils lost 10 of 10 each, the witness won 4 of 5 at
5 s and 0 of 5 at model pace (2 of 8 with the three b33 launches of the same cell, which the
default board pools). **Admitted** under its pre-registered rule; no check is
agreed, so the card stays unverified. The start-configuration confound read as tempo, and
GLM-5.3 low won 1 of 10 ([log](log.md#2026-10-19-overnight-round-at-b36-c1-finished-p2-cells-p5a)).

**For post-training**: one unit, a fixed opponent and 2-10 minute battles make the card a
cheap environment with a binary reward (the win); cycles are a leak check, not a shaping
signal, since they count attempts. Qwen3.6, the
planned student, exports through `twwarhammer3 export`; the witness is a free
demonstrator, but scripted decisions have no exported rows yet (they would need the
prompt the model would have seen at each decision).

### Second pass (2026-10-19 evening): findings and the version 2 decisions

An independent pass over the 80 recorded chariot battles (eight read-only agents recounting
the previous pass's numbers from the raw traces and replays; the geometry readings in
findings 1 and 2 are the assistant's own recount, checked by a refuting agent;
[log](log.md#2026-10-19-benchmark-verifiability-second-pass-harness-b39)). Harness b39
carries the reader-side fixes. Nothing below ran a game or a paid call; every finding is a
postdiction over recorded files and unverified under the hard rule. It replaces the
2026-10-19 "card version 2" and "knowledge against execution" proposals, which are in git:
`git show 5c01b93:docs/twwarhammer3/tactic-cards.md`.

**Findings**
1. **The tolerance curve is this recipe's; whether it is the tactic's is untested.**
   `SnapHitAndRun` retreats to 120 m from the enemies' centroid, recomputed every decision
   from its stale basis, and re-charges only 80 m from its target. The share of the battle
   spent more than 10 s into a withdrawal with the target still under 80 m away rises from
   20-36% in the fast cells to 42-49% in the slow ones, where under 20% of the withdrawal
   path becomes separation from the chaser (44-58% in the 2/2 wins) and the chariot idles at
   re-issued points and at the map's 30 m clamp: nine of the ten 5/5 and 8/8 losses end
   within 35 m of the map edge (median 26 m, max 72 m; the foils and Qwen end 250-290 m from
   it, GLM 49-401 m), and at 8/8 its first pull-out applied after the engine had already ended
   the contact in 8 of 12 engagements. Fatigue, refused moves and the melee share do not
   separate these losses from wins, and `HitAndRun`'s two 5/5 losses ended far from the
   edge, so the edge is where the stall ends, not its cause. The curve therefore bounds the
   tactic's tolerance from below until a witness without the stall runs (whether any recipe
   wins at 8 s of age is untested): GLM's one win (199 s, re-charges at 24-35 m, move plus
   queued attack in one batch) was faster than every witness win (236-814 s).
2. **GLM's re-attacks are mostly an interface gap.** Its countermands read 14 when a queued
   later-batch attack counts (12 otherwise; the previous review's 14 reproduces only under
   that reading), and 12 of the 14 were decided at 2-29 m centre distance with the melee
   flag on in the model's own basis; the engine's flag clears at a median of about 30 m
   centre distance (p90 48 m), and GLM's reasons said "clear" or "broken contact" in about
   45 in-melee decisions (39-50 by the wording matched), four in five of them under 30 m. By
   their reasons, 10 of the 14 believed the chariot clear and 3-4 chose to grind knowing it
   was locked. The rules prompt never says positions are unit centres and enemy records
   carry no width, so the model overrides a flag it was shown with centre arithmetic;
   whether a prompt sentence fixes that is untested. Its other losses are judgment (grinding
   on its own leadership triggers for 20-80 s; alternating attack targets every decision in
   a final melee) and 10 refused moves over its 10 battles (in four of them). Qwen never
   pulls out and leaves 172 of 180 enemy men; the foils leave about 145; GLM 143, with one
   near-win at 71.
3. **The ladder and the told arm were definition-sensitive.** Of the 11 numbers behind them,
   4 reproduce only under other readings and 3 differ: the witness fails its own 0.9
   first-decision threshold (0.88 at 5/5; 0.33-0.83 once the pull-out must apply inside the
   engagement), the stuck/clear split reads 3/9 by engagement and 12/37 by order, the "31 s"
   median reads 40-50 s, and two 5 m shuffles turn Qwen's "never pulled out 5 of 5" into
   3 of 5. Cycles v1 stays the pre-registered leak check (0 of 26 wins lack one); no ladder is
   built, and "located the cause" is withdrawn.
4. **The admission code loosened the rule.** `verdict()` passed 4 wins among any number of
   launches, the default board judged exploration launches the rule excludes, and a win
   without a replay read as a no-cycle win. b39: the first launches of a cell decide in plan
   order, a verdict prints only for named directories, a replay-less win is flagged.
5. **Identity.** The served model version (`z-ai/glm-5.3-20260816` and
   `qwen/qwen3.6-35b-a3b-20260415` in every attempt), the requested observe/tick cadence and
   the routing pin were recorded but not in a cell's identity; b39 adds them. Not added: the
   loop's own revision (c1 spans b34 and b36, whose change, forfeits, never fired) and the
   served quantization, which the recorded OpenRouter metadata does not carry (whether the
   API can report it is unverified).
6. **Statistics.** 0 of 10 bounds a foil below 0.26, above every model rate scored, so a
   win's attribution rests on the signature; the 2/2 cell's 4 of 4 has a Wilson lower bound
   of 0.51; the Fisher powers quoted were two-sided; every pre-registered operating
   characteristic is arithmetically right. A rematch replays the engine's instance as far as
   recorded (10 rematch starts match to 0.0 m; three of six skills rematches were identical
   through 300 s), so the launch is the unit and pairing a witness rematch into model
   launches reduces no variance.
7. **Latency.** GLM thinks longer in melee (2.2 s against 1.8 s, from more output) and its
   order age at the first in-melee decision is p50 2.7 s, p90 3.9 s, max 5.4 s; 5 retried
   decisions applied 7-10 s after their basis, two inside an engagement. A constant-age
   witness cell cannot show that tail, but it rarely fell on the decisive decision.

**Version 2 decisions for the owner** (nothing runs until agreed):
1. **Witness v2**: compute the retreat point once per withdrawal, measure the retreat and the
   re-charge from the same reference, and try a queued re-attack in the pull-out batch (a few
   lines of `calibration.py`, a new disclosed control beside the admitted one); rerun 5/5 and
   8/8 with 5 launches each ($0, about 1.5 h). Until then no "latency card" or
   "latency-bound" reading.
2. **Interface**: one `rules_prompt.md` sentence (positions are unit centres; the melee flag,
   not the centre distance, says whether a unit is in contact), a new `llm_rules` version and
   cohort; optionally each visible enemy's ordered width (one Lua line, one smoke battle).
   Then GLM-5.3 low, 10 launches (about $1.70), before any told arm.
3. **Reference arms at their free size**: each foil 0 of 14 launches (bound 0.19; 20 gives
   0.14), and a foil win adds its play as a declared foil and restarts the round instead of
   ending the card; the witness gate 10 of 14 at 2/2, stopped at the 5th loss (passes a 0.5
   witness 9%, a 0.8 witness 87%); the 5/0 cell stays as tolerance evidence; 2-3 witness 2/2
   launches on every model night, pooled into that cell as the control and the drift check.
4. **Reporting**: counts and Wilson, "0 of n: below b" for empty cells, one pre-registered
   primary contrast per plan, no verdict words at n = 10; the held-out variant declared now,
   not when tuning starts; a prompt change adopted only if the validation cell improves.
5. **Dropped**: the ladder as a score and its thresholds, the stuck/clear split, the eight-row
   reading table, the told paragraph with its receding reference, truncation as a rule change
   (0 of 80 episodes), added-age model cells, the paired witness rematch and the model-paced
   witness (variable pace costs 0.2-0.4 s of expected reaction).

**Owner check to propose**: `uv run --locked pytest -ra tests/twwarhammer3/test_wh3_cards.py`
and `uv run python -m twwarhammer3 card chariot runs/twwarhammer3/calibration/c1` printing
the foil rows at 10 launches and 0 wins, the witness at 5 launches and 4 wins, and
`Verdict: admitted`, while the default board prints no verdict. It rests on `runs/`, so
backing up c1, p2 and p5a (142 MB) comes first.

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
truncations count as losses; infrastructure failures are listed and rerun. The board prints
each cell's forfeits, median cycles and order age as p50/p90, and a cell under 10 launches
is a screen. Across cards:
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

Single-episode launches on the eight declared cards (63 launches: foils, witnesses and one
model battle per mode, every cell n = 1-4, backends unpinned, rules prompt v20, nothing
agreed). The per-card table and its signature reading are in git
(`git show 9df420f:docs/twwarhammer3/tactic-cards.md`) and the
[log](log.md#2026-10-18-tactic-cards-harness-b28-to-b30-and-the-overnight-checks). What the
night showed about the definition itself:
- **Foils first is cheap and decisive, and one launch per foil is too few**: a careless-play
  foil (`FireballSpam`) sank S5 after its witness had won 2 of 2, and the chariot card's
  rush-nearest foil lost its first launch and won its second.
- **A witness win is what tests sufficiency**: two cards saw the tactic executed (the guns
  routed) and the battle still lost; a one-factor step gave the expendables card its wins.
- **A model win can be read against the tactic**: each of the 3 chariot model wins was
  planned as cycle charging in the model's notes and showed pull-outs; Kimi K3 high planned
  the right play on two other cards and lost both with orders 24-135 s late, so knowing the
  tactic and executing it in time are separate results.
- **A model can beat the scripted witness**: gpt-6.1-sol won S1 with a feint and a rear
  charge where both `PinThenRear` timings lost, so a witness's loss bounds the bot, not the card.
- **One launch is a screen, not a ranking**: Kimi K3 high won its first chariot launch and
  lost its second.
- **Reasoning effort against order age**: a higher mode raised the mean order age for Luna
  (4.8 to 8.8 s) and GLM-5.3 (3.1 to 7.7 s), not for Kimi K3; Step 5 high's replies took 6
  to 370 s, 2 of 4 cut off at the 16,000-token cap.

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
  [LLM-PySC2](https://arxiv.org/html/2411.05348v2), [Orak](https://arxiv.org/html/2506.03610v3):
  "we pause the StarCraft II game environment"; its v3 of April 2026 adds one live table, in
  which every model scores 0 at the hard level); SMAC is lockstep and not built for language
  models ([SMACv2](https://arxiv.org/abs/2212.07489v2)). The real-time ones have no opponent
  or are pixel-based ([VideoGameBench](https://arxiv.org/abs/2505.18134v3): one run per model
  and game, and a human reference played with a fixed 0.5 s delay, the one latency-matched
  human reference found), are uncontrolled
  model-against-model fights ([LLM Colosseum](https://github.com/OpenGenerativeAI/llm-colosseum)),
  or count generated tokens instead of seconds
  ([Real-Time Reasoning Gym](https://arxiv.org/html/2511.04898v1), which also fits wall-clock
  time to its token clock).
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
page; full text not found): an LLM commands an army in real time through a modding
bridge with typed actions, 60 battles against the built-in AI, paired with a fast reactive
layer of standing rules that fire between model calls, so its win rates (unquantified on the
page; the data needs a subscription) are not a pure model's. What separates this
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
