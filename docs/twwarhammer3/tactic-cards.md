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
| tolerance | the witness by added age / decision interval (c1 and P2, 3-5 launches a cell, unverified): 0/0 won 4 of 4, 2/2 4 of 4, 3/3 3 of 4, 5/0 4 of 5, 0/5 3 of 3, 5/5 0 of 5, 8/8 0 of 4. On the diagonal (age equal to interval, the regime a model is in) the window closes between 3 and 5 s; achieved ages run 0.4-0.9 s above nominal (2/2: 2.7 s, 3/3: 3.9 s). Models decide about 0.4 times a second; GLM-5.3 low's achieved profile (median 2.1 s, p90 3.3 s) sits between the 2/2 and 3/3 cells |

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

### Card version 2 (proposal, 2026-10-19; not agreed)

From the verifiability review ([log](log.md#2026-10-19-benchmark-verifiability-review)); each
item is an owner decision and none runs a game until agreed. The c1 verdict stays the
pre-registered v1 result; v2 is frozen before its own round and c1 is shown recomputed under it.
1. **Signature v2** is the ladder's cycle ([below](#knowledge-against-execution-the-ladder-and-the-told-arm-proposal-2026-10-19-not-agreed)):
   a non-last engagement with a pull-out and no countermand. `cards.cycles` today credits a
   pull-out the controller itself overrode (GLM-5.3 low: 9 of its 30 credited cycles; the
   witness 0 of 228). The draft's 30 m clearance clause is dropped: depth is a descriptor.
2. **A model-pace gate, pre-registered inside the tolerance.** Keep the v1 gate as admitted;
   add the witness at 2 s age and a 2 s interval in fresh launches, 10 of 14 (passes a 0.5
   witness 9% of the time, a 0.8 witness 87%; 8 of 10 would be 5.5% and 68%), stopped at
   the loss that decides it. Foils: the 10 instances stand (necessity is bounded by the foil
   set, not by n) plus the drafted wrong-tactic foils (one pull-out then grind, which GLM
   played in two losses; charge straight through) and an observation-blind cycler that reads
   only the clock and the first observation (SMACv2's test: a blind win means the card
   rewards a recipe, not reading the melee flag). One re-admission night, about 3 h, $0.
3. **Truncation.** Since b35 only the game or the harness can truncate (the loop never
   waits), so `truncated` should be excluded and rerun, not a forfeit; b35's wording says
   forfeit. One line and one assertion; unobserved so far (0 of 97 chariot episodes).
4. **Model cells.** 10 launches detect only gaps of about 0.6 (Fisher's exact at n = 10:
   power 0.84 for 0.1 against 0.8, 0.30 against 0.5, 0.15 against 0.4); no difference is
   claimed below 20 launches per cell and no ranking below 30; added-age or deadline cells
   for a model only after at least 5 of 10 natural-latency wins. A prompt or harness change
   starts a new cohort, never pooled (the board marks a mixed prompt hash); the review loop
   never tunes on scored jobs; the held-out map is declared when a tuning round is planned.
   On a game build change the admission round is rerun before any paid launch.
5. **The agreed check to propose.** `uv run --locked pytest -ra tests/twwarhammer3/test_wh3_cards.py`
   and `uv run python -m twwarhammer3 card chariot runs/twwarhammer3/calibration/c1` printing
   `Verdict: admitted` (skipped where `runs/` is absent). It rests on `runs/`, so backing up
   c1, p2 and p5a (owner decision 1) comes first.

Dropped from the 2026-10-18 draft: start classes (recorded starts differ by at most about
2 m on this card and showed no within-cell association in the three mixed cells, n 3-10;
`result.start` keeps the raw start), one control per launch (one episode per controller per
launch is the rule, enforced by the board since b38) and the hashed plan list (the plan files
and manifests record it; the board lists planned launches that never ran). Considered and
not adopted: a witness rematch inside every model launch (halves the night's model launches;
the witness at 0 s won every start seen), fixed starts by teleport (the mod's evacuation code
can place both sides, but the engine exposes no seed, so a launch is never replayable, and
the spread here is too small to matter), a witness paced by a model's recorded think times
(the diagonal cells bracket the current models; a `--delay-seconds D --interval-ms I` cell at
a model's p90 needs no code) and new offline probe moments (a memoryless probe cannot measure
commitment; the countermand count does, at $0).

### Knowledge against execution: the ladder and the told arm (proposal, 2026-10-19; not agreed)

How a card tells "did not know the tactic" from "could not execute it live"
([research and panel](log.md#2026-10-19-knowledge-against-execution-the-protocol)): read the
controller's applied orders on its own information, never its reply text, and intervene on
knowledge once. A plan; every number is a postdiction over the 64 recorded chariot battles.
- **The ladder** (`cards.ladder`, about 40 lines replacing the body of `cycles`; $0, read
  retroactively). Per engagement of the card unit: *observed* when some decision's basis
  showed it in melee, else *unobserved* (the engine ended the contact before the controller
  saw it: the latency share, witness 5/5 2 of 31, 8/8 1 of 17, GLM 0 of 43); the *pull-out*,
  graded at the first in-melee decision: an applied unqueued move whose destination lies
  farther from the nearest visible enemy in that basis than the unit stands (*first*), or at a
  later in-melee decision (*late*), else *none* (an approach or a refused move is none); a
  *countermand*: an unqueued attack applied after the pull-out before the engagement ends,
  split by the basis gap at that decision into *stuck* (within 5 m) and *believed clear*; a
  queued attack in the pull-out's own batch is counted apart; *silent*: an observed
  engagement of 10 s or more with no order applied. Printed, never scored: destination gap
  and gap at the first re-attack, reaction, health lost per engagement, order age at the
  first in-melee decisions. The reading is the **per-battle class** over the cell's launches:
  won with a cycle, won without one (a leak: the play becomes a foil), never pulled out,
  countermanded, executed-lost, forfeit.
- **Recount**: witness 0/0, 2/2 and 0/5 won all; 3/3 and 5/0 one executed-lost each; 5/5 and
  8/8 executed-lost 9 of 9 with 7 silent engagements, first-decision pull-outs in 16 of 24
  and 4 of 12 observed engagements, 0 countermands; foils never, 20 of 20; GLM-5.3 low won 1,
  countermanded 6, executed-lost 3 (pull-outs first 18, late 12, none 3 of 33 observed
  non-last engagements; countermands 3 stuck, 9 believed clear; 8 queued re-attacks);
  Qwen3.6 none never, 5 of 5. The local P4 probe's first-contact grade agrees with the live
  first-decision reading (GLM moved away 18 of 30 against 18 of 33), so the ladder gives it
  at $0 and the keyword screen and the probe retire as instruments.
- **The told arm**, the one intervention on knowledge: a base policy `llm_card` whose system
  prompt is the rules prompt plus a frozen "Card knowledge:" paragraph stating the witness's
  rule in the second person (attack the nearest enemy; on the first observation showing your
  unit in melee, move it to 120 m from the enemies' centre on your own side; charge again
  once 80 m from the target and 10 s after leaving), composed by `controllers.system_prompt`,
  saved and hashed as the job's prompt (the export's equality check holds), separated on the
  board and in the register by name; about 15 source lines. Only `llm_rules` gets a told
  twin: the `llm` and `commander` prompts advise against the tactic ("once a unit is in melee,
  keep it there"), so they are another cohort.
- **Arms per model and mode**, unpaused at 1x, no added-age model cells: U, the scored
  `llm_rules` cell at natural latency, 10 launches (GLM's 10 and Qwen's 5 are recorded); T,
  `llm_card`, 10 launches when U won at most 2 of 10 and forfeited under 3, skipped when U
  won 6 or more; a new model pairs them in one launch (`--policy llm_rules@m/e,llm_card@m/e
  --episodes 2`); the witness at 2/2 twice the same night as the drift control. Cost: 12
  launches, about 1.5-2 h, about $1.70 for GLM-5.3 low. Read as direction only, Fisher on
  launches (10 against 10 separates gaps near 0.6; smaller prints "not separated"):

| U reads (most launches) | T reads | Reading |
|---|---|---|
| won 6 of 10 or more, each with a cycle | skipped | knows and executes |
| executed-lost, unobserved and silent up, 0 countermands (the witness at 5/5, 8/8) | skipped | latency-bound |
| never pulled out (Qwen 5 of 5) | pull-outs appear, cycles or wins rise | the step was missing: knowledge |
| never pulled out | still none | recipe not adopted: unattributed |
| countermanded (GLM 6 of 10) | believed-clear countermands fall, wins rise | parameters and a standing rule were missing: a disclosure effect, since GLM's notes held the plan |
| countermanded | countermands persist | execution: it overrides its own pull-out under the clock |
| executed-lost at an age the witness wins | persists | the recipe ran and lost: card or pace residual; read the descriptors |
| any | T wins below U | the recipe hurts this model: flagged, not diagnosed |

- **Validation before any model row is read**: the recorded known groups through the same
  code (witness first-decision pull-outs in at least 0.9 of observed non-last engagements at
  every cell, 0 countermands; 5/5 and 8/8 class as executed-lost, never countermanded; foils
  never) and one synthetic fixture with positions and basis records: an approach move reads
  none; an away move then an unqueued attack reads countermand and cycle 0 where v1 reads 1;
  a queued attack in the same batch is no countermand; a 1 s flicker merges; no in-melee
  basis reads unobserved; the composed `llm_card` prompt equals the rules text plus the
  paragraph and the manifest hash is its sha256; one `llm_card` and one `llm_rules` row of a
  model form two unstarred cells. No live bots are required (PullOutOnce and the blind cycler
  stay in item 2); a shallow cycler (retreat 60 m from the nearest enemy, re-charge at 45 m,
  5 launches) is optional, to test whether depth matters at all.
- **Not separated**: knowledge from salience in T; ignoring the text from being unable to act
  on it; a wrong clearance belief applied reads countermand, and only T says whether the
  number fixes it; latency matched by constant-age cells, not the model's tail; 1 Hz replay;
  whether 80 m is necessary (GLM won at 49 m clearance); one night, one backend.
- **Owner check to propose**: `uv run --locked pytest -ra tests/twwarhammer3/test_wh3_cards.py
  tests/twwarhammer3/test_wh3_controllers.py`, and `uv run python -m twwarhammer3 card chariot`
  printing the known-group readings above and `Verdict: admitted` (skipped where `runs/` is
  absent); after the told night, the board over its plan directory printing `llm_card` and
  `llm_rules` as two cells with classes, wins and intervals.

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
