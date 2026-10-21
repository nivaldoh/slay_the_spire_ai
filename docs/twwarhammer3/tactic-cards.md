# WH3 tactic cards

The tactic-card design the owner started on 2026-10-18, with the evolving card list. The
current plan and proposed verification are in [benchmark.md](benchmark.md). This remains a
draft: every new gameplay check below is proposed and
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
| mechanism hypothesis | repeated charges can rout the Swordsmen; the tested long-melee foils lost, mostly with every chariot alive. This does not exclude every other winning play |
| foils | `attack_nearest` and `rush_nearest` at 0 s added age. `hold` is no foil: the AI defends, so standing still loses on the timer by the mode's rule (1205 s) |
| witness | `SnapHitAndRun` (rule disclosed in its card): attack the nearest enemy and keep it; on the first observation showing melee ride to 120 m from the enemies' centre, on its own side; charge again once 80 m from the target and 10 s after leaving |
| signature | **cycles v1**: non-final melee engagements containing an accepted move order (1 Hz melee frames, gaps under 3 s merged; an order applied up to 1 s after an engagement's last melee frame counts, as the code frozen at `5396182` does). It counts pull-out attempts, not achieved separation or a proven new charge. Witness wins read 4-21 and losses 1-15; the count does not separate winning from losing |
| knowledge | withheld: the rules prompt states neither charge bonuses nor cycle charging |
| tolerance | The [b40 round](log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40) found witness v2 won 3/3 at configured 2 s age / 2 s interval, 4/5 at 5/5 and 4/5 at 8/8. V1 won 2/8 at 5/5 and 0/4 at 8/8. These are recipe-specific results, not a tactic-wide deadline. Actual timing rounds to the engine cadence; queued attacks execute later than their acknowledgement. The board's roughly 13 s `info age` at 8/8 is a summary proxy, not a measured reaction window ([timing](latency.md#measurements)). No causal attribution of model losses to latency follows |

**Admission rule** (committed at `5396182` before the round; the model-pace gate was
dropped at 17:45 UTC, against E2's own rule): in fresh launches, `attack_nearest` and
`rush_nearest` each lose all of 10 (one win fails the card), and the witness at 5 s added
age and no added interval wins at least 4 of its first 5, each win with at least one cycle.
Operating characteristics: a foil that wins 20% of its battles passes 10 straight losses
11% of the time (10 losses bound a foil below 0.26, one-sided 95%); a witness that wins
half its battles passes 4 of 5 19% of the time, and one that wins 80% fails it 26% of the
time. The gate witness decides about three times a second on 5 s-old information, a regime
no model is in; the tolerance row above is the evidence at model-like cadences. Each c1
foil launch rotated both foils, so each foil's 10 battles are on 10 instances shared with
the other foil (`attack_nearest` played the fresh start in 3, `rush_nearest` in 7; the rest
were rematches of the instance the other foil had just played). `cards.outcome` changed
after pre-registration (b35, forfeits) with no effect on c1, which has no forfeit.

**Score** per model and mode: wins over scored launches with a 95% Wilson interval, beside
the median cycles and order age. The battle never waits (`cards.outcome`, harness b35): a
terminal in-battle controller failure or truncation is a loss, labelled forfeit; a failed
decision that is retried consumes time and does not itself end the battle. Game and setup failures, interrupts and operator
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
GLM-5.3 low won 1 of 10 on prompt v20
([log](log.md#2026-10-19-overnight-round-at-b36-c1-finished-p2-cells-p5a)) and 0 of 10 on
v21, which tells it that positions are unit centres and the melee flag decides contact
([log](log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40)); Qwen3.6 none 0 of 5 (v20).
No model has won the card at a rate above its foils' bound.

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

**Version 2 decisions for the owner** (decisions 1 and 2 ran on 2026-10-19 evening under the
owner's "battles allowed" direction, [b40 log](log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40):
witness v2 won 4 of 5 at both 5/5 and 8/8, so the curve was the recipe's; GLM-5.3 low on the
amended prompt won 0 of 10, with fewer in-melee re-attacks and more damage, every loss a
leadership rout after 4-45 m pull-outs; decisions 3-5 remain, plus whether v2 becomes the
card's witness and at which cell):
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

For outside AI researchers: which controllers can apply specific tactics in a battle
that keeps moving while they think? Each small battle (a **card**) should make its
intended tactic consequential: a disclosed reference wins and naive or plausible wrong
plays lose. This is evidence against specified shortcuts, not proof that no other tactic
can win. Larger battles can test coordination; more units alone do not isolate context length.

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
| mechanism | why the tactic should matter; the simplest way to win without it, to test first |
| foils | declared plays that must lose: the naive floors (`hold`, `attack_nearest`, `rush_nearest`) and at least one plausible wrong tactic |
| witness | a disclosed public-state bot (`battle/calibration.py`) that executes the tactic; later a model's or a person's win |
| signature | observable action and subsequent effect, its source/resolution, and positive, negative and unknown cases; say when it measures only an attempt |
| knob | one declared difficulty change at a time, such as unit rank; keep the mechanism and a credible winning route |
| knowledge | mechanics supplied or withheld; separately declare whether the tactic is told; the reference and model must have the same permitted state |
| timing | configured age and interval, achieved order ages and gaps; any claimed opportunity/deadline needs an observable reference |
| frozen rule | card/scorer revision, success and failure treatment, foil/witness counts, stopping rule, evidence cohort and reserved variants |

Review every win for its signature. A win without the intended tactic stays a gameplay
win and challenges the card: it may be a shortcut, a valid alternative or a weak signature.
Preserve the old verdict and evidence; revise the interpretation or define a new card
version and foil before new confirmation. Do not erase a win or revise a rule mid-round.
An unknown signature is not evidence of absence. Do not reward more attempts as if they
were better tactics: cycles v1 is not a suitable training reward.

## Proposed admission checks

Use the [current gates](benchmark.md#from-a-candidate-to-a-scored-card) and
[correctness checks](benchmark.md#correctness-checks-to-agree). They replace the generic
3-of-4 witness gate and longest-melee-run signature proposed here on October 18; neither
is the chariot's frozen rule. New gameplay verification methods need owner agreement
before entering AGENTS.md. Agreement on a component test does not admit a tactic card.

A witness must win the whole task under the declared sensing and decision schedule.
It need not lose at slower settings; a robust recipe is useful evidence. If a fixed
schedule wins the reserved variants, a claim that feedback is essential needs revision.
Use a plausible partial-tactic foil where it matters (for example, an escort that wins
after abandoning the gun). Test simpler alternatives before strengthening the opponent.
The current gates supersede decision 3's older restart/pooling proposal: retain a genuine
foil win as counterevidence, revise the card before another confirmation, and keep later
drift checks separate from its frozen admission cohort. Do not keep retrying an unchanged
gate to obtain a pass.

## Score

The sampling unit is the launch; count at most one trial per controller/condition within
it. Rematches share the instance and are not extra independent samples. The primary rate
is wins/scored trials, with a 95% Wilson interval; show total starts, exclusions and
terminal forfeits explicitly. For example, 10 starts, 1 setup exclusion, 2 terminal
controller failures and 3 wins gives 3/9, not 3/7. Within-launch contrasts must retain
pairing; a per-cell Wilson interval alone is not an interval for the difference.
Report planned but unstarted trials too; a failure stops the rotation, so complete pairs
can be a selected subset. A budget-stopped battle needs missing-outcome treatment before
the cohort can support a ranking.
Launches are the best available sampling unit, but fresh starts do not establish
independent engine seeds or provider randomness. Intervals remain conditional on the
declared setup and sampling protocol.

Current classic cards use an engine win before the timer as success. Timer wins and
draws count as unsuccessful attempts and remain labelled. `cards.outcome` counts terminal
controller failures/truncations in battle as losses; game/setup failures and operator
stops are excluded and listed with any replacements. A recoverable failed call consumes
battle time but is not itself a terminal forfeit: score the final episode. No selective
reruns for slow or garbled replies. Any backend repair starts a separately labelled cohort.
Native-objective cards need their own declared success rule before use.
Construction and post-terminal errors need the proposed
[phase rule and checks](benchmark.md#correctness-checks-to-agree); current code does not
implement that proposal. Preserve the frozen historical verdicts.

Show signature evidence, p50/p90 issue age, decision gaps, pending/failed calls, cost and
failure counts beside each rate. The report's rate over engine-completed trials is a
different diagnostic. Ten trials can be a useful screen but do not establish a ranking;
neither a high win rate nor its interval establishes the tactic's necessity. Keep
conditions and card versions separate. Only a frozen suite with matching coverage can
also report an equal-weight mean over distinct cards; variants do not earn extra weight.
Strength margin remains secondary because routing, objectives and unit roles can make
it disagree with success. Controllers may use different helpers, but those helpers
belong to the controller's result and must be disclosed.

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
   too hard to too easy. Experience ranks are now supported per unit (b41), exercised by
   the agreed army check, and used in the Empire rank-5 candidate. They are a finer knob
   than adding a unit; they still change combat balance and morale. A stat adjustment
   must preserve the intended decision rather than simply favor the witness.
8. **Control confounds**: a lordless army's commander flag sits on its first card and that
   captain's death cuts every unit's morale (S3); an "army losses" shock can rout a unit at
   full strength (S2). The flag does not always follow the first card: in the expendables
   card it went to a Skavenslaves unit although the Rat Ogres were listed first (b28). In
   all 38 recorded lordless rosters it sat on the battle's first unit (`f1`), which differs
   from the declared first in 11 (2026-10-21, replay `commander` field). The battle's order
   looks cheapest first where costs are known (line battle: Spearmen 350, then Swordsmen
   375), so an added cheaper unit would likely take the flag (unverified).
9. **Sufficiency, not only necessity**: once the tactic succeeds, the rest of the battle
   must be winnable. On 2026-10-18 the two-halberd expendables witness routed the guns at
   160 s and the halberd giant witness at 171 s, and both still lost to the anti-large unit
   left standing while their foils also lost (n = 1 each). The witness is what tests this.
10. **A witness must not abandon a routing target**: a routed unit can rally (the cannon
   crew did); keep it until it is dead or off the field before switching.

## The card list (draft 1, 2026-10-18)

The statuses below are from that night; the [starting
set](#the-starting-set-proposal-2026-10-21) holds the current evidence and verdict for each
battle it names. Drafted by four agents (one per kind) and attacked by four adversarial
critics, each trying to win every card without its tactic (read-only: traces, the game
database, the observation reference; the full panel output is not kept in the repository).
Status: *declared* (a scenario entry exists), *draft* (defined only) or *dropped*. The
critic's main objection is the risk to check first; "foils first" means the naive floors
run before any witness is written or counted.

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

<a id="what-only-wh3-battles-can-test"></a>
## What WH3 adds

Live-clock evaluation, structured game state and slow planners over fast controllers
already exist. The [primary-source review](benchmark.md#research-that-changes-the-design)
replaces this page's October 18 novelty survey (kept in git at `f5af096`). WH3's useful
combination is tactical manoeuvre, morale, continuing orders, magic and changing support
between units. A literature review does not establish that this combination is unique.

## The starting set (proposal, 2026-10-21)

No set is agreed yet. This proposes the battles to take to confirmation first, by a rule
that can be checked against the record. Counts are episodes in `results.csv` (rematches
included, mostly single launches, all unverified), recounted by
`runs/twwarhammer3/away-20261021/evidence.py`; `markers/markers.py` beside it reads the
line, expendables and probe markers on all 42 recorded episodes of those battles (proposed
readers, not agreed checks), and `twwarhammer3 card chariot` reads the chariot's. Success
is a contact win: every enemy unit routed or destroyed before the timer. A defender's timer
win is recorded beside it, not counted ([Empire decision
7](empire.md#decisions-taken-for-the-owners-review)). Words: the floors are the naive
scripts `hold`, `attack_nearest` and `rush_nearest`; a shortcut is a named wrong play that
might still win; floors and scripted shortcuts are the foils that must lose. A witness is a
disclosed script that plays the tactic. Added age is the delay the harness adds to each
observation (`--delay-seconds`). A screen is a few cheap launches; a probe is a battle
screened for the owner, not a set card.

**What a card needs before confirmation.** All five must hold:
1. It tests a decision no other card in the set tests. New cards play Empire unless the
   decision needs another faction; the chariot and expendables cards keep theirs.
2. Every floor that applies has lost (`rush_nearest` where a charge could win by itself),
   and so has the card's named shortcut, scripted before confirmation (a floor counts where
   it is that shortcut).
3. A disclosed scripted witness, seeing only the public observation, has won at least half
   its launches at one declared added age and decision interval. A model's win shows the
   battle can be won but is not a witness.
4. The card has a marker: something in the replay and trace that the witness's wins show
   and the losing floors do not. A win without it stays a win and questions the card.
5. A battle lasts under about 10 minutes, so one card's confirmation fits in a night.

A battle that still fails 2 or 3 after one difficulty step is parked with its reason, not
hardened or softened further. The line, expendables and Helblaster battles have had theirs;
the rifle lane has had two. Two agents given this rule and the evidence, but not this
section, each chose the three cards below (`runs/twwarhammer3/away-20261021/rederive.txt`).

| Card and battle | What it tests, and its marker | So far | Missing before confirmation |
|---|---|---|---|
| Chariot, `grn-chariot-emp-swordsmen-hard` (attacks) | Charge, pull out and charge again instead of grinding. Marker: at least one pull-out attempt during melee (cycles v1) | `attack_nearest` 0/11, `rush_nearest` 0/12; SnapHitAndRun 5/6 in its admitted cell (5 s added age, 21/33 over all ages), HitAndRunV2 11/13; admitted under c1's rule | The agreed checks, failure rule and witness version ([state](../state.md#total-war-warhammer-iii), next step 1); no more delay sweeps without a new question |
| Line at rank 5, `emp-line-grn-raid-xp5` (7 v 7, defends) | Seven units keep their jobs: the line holds in guard mode, the guns stay behind it, the knights take the enemy cavalry. Proposed marker: the knights' first melee is against enemy cavalry. On this battle it fails both floors and passes both wins (LineTeam, GLM) and both other rank-5 losses (Kimi, LineTeamReserve); at rank 0 both floors pass it too, so it marks the knights' job, not the whole team's | `hold` 0/1, `attack_nearest` 0/1; LineTeam 1/1 at 0 s (b45; b46 unplayed); LineTeamReserve 0/1 | The rush floor; floors and LineTeam b46 at 3 launches; agreeing the marker ([Empire item 2](empire.md#for-the-owner-to-decide)); a decision on the commander flag, which sits on the Spearmen reserve in all 17 recorded battles (design rule 8); and a named shortcut (proposed: LineTeam with the knights held back, which tests whether their job decides it). Whether replacement helps stays a [team-plan](robot-team-plan.md#a-small-sequence-of-experiments) question |
| Expendables, `skv-ogres-slaves-emp-halberds-1` (defends) | Spend the Skavenslaves to hold the Halberdiers while the Rat Ogres kill the guns. Marker: the ogres fight, and the slaves fight the halberds before the ogres' first melee, which is not with the halberds. SlaveTarpit passes all 5 of its episodes and all 3 floor episodes fail, with one or two Halberdiers units | `hold` 0/1, `attack_nearest` 0/1; SlaveTarpit 3/4 at 5 s. Kimi K3 played a shortcut twice, ogres on the guns before slaves on the halberds: low won (87 s, then 127 s), high lost (179 s, then 334 s) | The rush floor; 3 launches per floor and witness; a foil for Kimi's shortcut (ogres at the guns at once) |

Only the line plays Empire. The owner asked for mostly Empire units, other factions for
specific challenges such as the Orc chariot ([2026-10-20](../owner-direction.md)); the
cheapest routes to more Empire cards are the two probes below: the rifle lane's screen
evidence for its reinstatement, and a witness for two threats.

Not in the starting set:
- **Rifle lane**, `emp-handgunners-grn-savage-orcs-hard` (defends): fire past one's own
  Spearmen through a clear lane. Its family took two steps (Big 'Uns, then Savage Orcs at
  1.0, where `attack_nearest` won, then 1.1) and `hold` never played against Savage Orcs.
  FlankLane won 1/2 at 5 s, and its lane marker (most rounds fired with the gun-to-target
  line clear of the Spearmen, FlankLane's own test) reads 90% and 100% against
  `attack_nearest`'s 12%; GLM-5.3 low lost 2/2 at 0%. Its floors and witness are in the
  screen, for the owner to reinstate it on that evidence.
- **Two threats**, `emp-handgunners-grn-wolves-boyz`: the Spearmen meet the fast Wolf
  Riders, the guns shoot with skirmish off and then turn to the Orc Boyz. Floors 0/2; no
  witness. The marker (the guns never in melee before the riders are shattered or gone)
  fails both floors and GLM-5.3's loss and passes its win (1/2). Its floors are in the
  screen; a witness written from GLM's winning plan would make GLM a designer of this card
  (evaluation guideline 3.3), so it waits for the owner.
- **Protect the gun**, `emp-helblaster-brt-raiders`: Bodyguard won 5/8, every win with
  the Helblaster at 0 crew, so a contact win does not test protection, and "win with the
  gun alive" has no witness win (GLM-5.3 low did it once in 4). Its step (`-2`, a second
  Men-at-arms) lost every launch: Bodyguard 0/2, `hold` 0/1, GLM 0/1. Parked.
- **Pin-then-rear**, `ksl-raiders-emp-halberds` (attacks): floors 0/2, but the current
  PinThenRear (tightened at b29) lost both its launches; its first version won 1 of 2 and
  FeintFlank 1 of 3, each win a single launch at 0 s.
- **Siege**, `chd-reserve-grn-siege` (the type-of-situation kind): Sol-class models won
  6/7 and Luna 1/4, but no script has won (CentralDefence 0/1).
- **20 v 20**, `emp-pitched-grn-20` (scale): every controller lost (3); a planner and
  executor harness comes first ([Empire item 5](empire.md#for-the-owner-to-decide)).
- **Parked**: the wizard (its wrong-play foil FireballSpam won 2/2); hammer and anvil (two
  Swordsmen: `attack_nearest` won; three: all 6 lost); three Dwarf Warriors (nothing won in
  9); knights against Orc Boyz (nothing won, and the commander flag on the only unit is a
  built-in morale shock); the Giant and the Screamers (no witness won).

**Cost of the first round**, at recorded job wall times (manifests' `wall_seconds`, each
battle's mean over its recorded launches, model ones included: 6.4-9.7 minutes a launch;
jobs follow each other within seconds):
- Screen, $0: 3 fresh launches of each floor and witness of the line, expendables,
  rifle-lane and two-threats battles (`rush_nearest` on the line and the expendables, where
  a charge could win; witnesses at their recorded age with no added interval: LineTeam 0 s,
  SlaveTarpit and FlankLane 5 s), in three rounds that each hold every arm, so a stop
  leaves the arms equal (evaluation guideline 4.2): 39 launches in about 5.1 h. The jobs
  are fixed in `runs/twwarhammer3/away-20261021/screen-plan.json`; its revision and start
  cutoff are set on the go-ahead. The queue cannot stop a card early. Offline, the three
  witnesses (LineTeam's b46 code included) decided on 9,674 recorded observations (the line
  at both ranks, both rifle variants, the expendables battle) without an exception or an
  invalid batch (`witness-dryrun.txt`; open loop, decisions only).
- Reading rule, fixed now: a floor's contact win parks that card (two threats would get one
  step instead). A card goes to confirmation when no floor won by contact, its witness won
  at least 2 of 3 with the marker on each win, and the rest of its Missing column is done,
  so a screen alone admits no card; any other result goes back to the owner, as do the two
  probes. The line card's marker is agreed with the go-ahead, before its screen is read. A
  floor's timer win is noted, not counted. A failed launch is not replaced: a cell with
  fewer than 3 scored launches is re-planned before it is read. Three launches are a cheap
  filter: a floor that wins 20% of its battles loses all 3 half the time (51%), and a
  witness that wins half passes 2 of 3 half the time, and one that wins 80% passes 90% of
  the time; confirmation does the rest. `read_screen.py` beside the plan prints the rule's
  verdict per card and every planned job without a scored episode; on every recorded launch
  (`--all`) it reproduces the line and expendables floor and witness counts.
- Confirmation at the [proposed gate](benchmark.md#from-a-candidate-to-a-scored-card) (each
  foil 0/14, witness at least 10/14): 56 launches for a card with three floors (the line
  and the expendables; 42 with two) plus 14 per shortcut foil: about 140 launches over two
  long nights, the line about 11 h, more than a night (pairing controllers in a launch
  saves about 13%). A 10-launch gate (foil bound 0.26 instead of 0.19) needs about 30%
  fewer.
- First model screen, 10 launches per card and model (a screen, not a ranking): GLM-5.3 low
  cost a median $0.19 a launch (45 since 10-19, `results.csv` usd), Kimi K3 low $0.63 (its
  3 line battles), Qwen3.6 $0.02 (6). About $26 of the $50 OpenRouter allowance is left
  (the account showed $24.26 used of $60 credit on 2026-10-21; the ledgers hold $2.68
  less), so GLM and Qwen on the three cards (about $10; a line battle costs GLM $0.23-0.58)
  fit and Kimi on all three does not; OpenAI is at its cap. Every supported reasoning mode
  of each model follows on the retained cards ([owner, 2026-10-16](../owner-direction.md)),
  not as the first matrix.

Before more model launches on a card, a held-out variant of it is reserved (evaluation
guideline 3.2; proposed: the same card on `battle_preset_wh3_nur_wastes_01_04`, the map of
the six earlier `-heldout-wastes` entries, listed in the lobby and used by one random battle but by
no card, checked by its witness and floors only), and the two defending cards need the [defender-prompt decision](../state.md#owner-decisions-waiting):
the model prompt promises a defender the timer win these cards do not count. The scripted
screen does not depend on either.
