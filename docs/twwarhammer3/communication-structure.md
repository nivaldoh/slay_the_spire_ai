# Peer messages and a commander in one army

Draft for owner review, 2026-11-08. On the night of 2026-11-08 the owner asked for stages 0 to 3
with a $10 cap; the build, the runs and their results are in
[results so far](#results-so-far-night-of-2026-11-08) and `runs/comm-build-20261108/`. Stage 4 is
not approved. [Owner direction](../owner-direction.md):

> I think one interesting thing that we can study is battle performance for one-army multi-agent
> when the army's agents are allowed (and forced) to communicate directly with each other vs some
> kind of "captain" agents being forced to communicate exclusively with a commander that might
> potentially have access different information compared to them. We can test this initially
> with the Cannae battle, and later we can think about expanding the idea.

This study compares ways of passing messages inside one army. It runs three versions of one
team, called arms. In each arm five model captains split the army: each commands one group of
regiments and sees only what is near that group. In the peer arm the captains message each
other directly. In the two commander arms a captain may message only a sixth agent, the
commander, who commands no regiments and sees either less or more than the captains. The battle,
the groups, what each captain sees, the model and the plan stay the same in every arm. The first
battle is [Cannae battle C](cannae-communication.md), which already has the five groups, their
local views and a message router.

## The question

Does a team of five Haiku captains win more often when captains must message each other
directly than when every message must go through a commander? And does it matter whether that
commander sees only the captains' messages or the whole battlefield the army can see?

Two main comparisons answer it, and a third is exploratory:

- O against P, the comparison the owner asked for: captains talk only through a commander who
  sees more than any captain.
- R against P: captains talk only through a commander who sees nothing but their messages, so
  the team observes the same things as in P.
- O against R: what the commander's wider view adds on the same links.

Each comparison is between whole teams. R and O add a sixth model, a second step for every
message between captains, and one inbox that receives every captain's reports. O against R also
includes O's larger commander input, which makes its calls slower and costlier, and O's captains
being told that the commander sees more. Splitting these apart needs the
[later arms](#later-expansions).

Earlier studies found cases where a central position helped a group and cases where it hurt.
None of them compares message structures between LLM agents that each command part of one army
in a battle that keeps running while they think:

- Groups of five people solving a simple puzzle were faster when one central person collected
  the facts: on its best trials a wheel took about 32 s against 50 s for a circle (Leavitt 1951,
  as reported by Sidi 1970). On complex tasks decentralized groups did better, which reviews
  explain by "saturation", the load on the central position (Shaw, as summarized in course notes).
- In the ELICIT command-and-control game, 68 people in four groups were faster when organized
  without a leader than when organized in a hierarchy (time score 0.47 against 0.33, over 210
  identifications in all) at about the same accuracy (0.69 against 0.66), although the hierarchy
  still let peers share facts directly (Leweling and Nissen 2007). In a later validation, a
  coordinator who alone saw every team's data did badly with humans (effectiveness 0.34 against
  0.80 for open collaboration, 4 runs each) and well with software agents that reported reliably
  (0.97 against 0.99, 27 runs each) (Manso and Ruddy 2013).
- With GPT-4 robot planners, dialogue among per-robot models was the worst of four structures,
  and a central planner checked by per-robot models was the best (for example 25.0% against 82.5%
  success on one task, 40 runs per task) (Chen et al. 2024). A designated leader made teams of
  GPT-3.5 agents about 10% more efficient in a household task (Guo et al. 2024).
- Topology studies on offline LLM tasks found no structure best everywhere (MacNet, Qian et al.
  2024). In one research scenario a flat star scored like a full mesh, while an extra level of
  hierarchy did worse (MultiAgentBench, Zhu et al. 2025).
- The closest live-clock work is recent. ROAR (Wang et al. 2026) split control between models
  under a live clock, with no messages, and found split and central teams within one standard
  error. In TickingCollabBench (Yi et al. 2026) a central Minecraft model scored above per-bot
  models that negotiate by message on all three tasks with GPT-5.1, at real-time success rates of
  0.15 or less. GPTNT (Parekh et al. 2026) has messages under a live clock, but its roles split
  information, not units ([thesis papers](../thesis/papers.md), checked entries).
- In multi-agent RL, a master agent with the global state that messages local agents beat
  broadcast communication on StarCraft micro tasks (MS-MARL, Kong et al. 2017). In HAMMER, local
  agents that could not message each other but heard from a central agent with the full state
  beat independent learners on cooperative navigation and multi-agent walker tasks (Gupta et al.
  2021).

From these, a commander should help when the useful fact is simple to pool or only the commander
can see it. It should hurt when many groups report at once and the commander falls behind, when
a needed fact never reaches it, or when a fast handoff waits for the extra step. A peer mesh of
LLM captains may fail through chatter even with every link open. All of these are hypotheses for
WH3. Sources and their checking status are in
[references.md](../references.md#communication-structure-in-one-army-2026-11-08).

## What "forced" means

Until the owner answers question 1, the plan uses this meaning in every arm:

- The allowed links are the only way to send a message. In P a captain may address any other
  captain. In R and O a captain may address only the commander, and the commander any captain.
  C's other channels, signals and couriers, are off in all three arms.
- Every captain reply must carry one or two messages, each to an allowed recipient. The reply
  schema lists the allowed recipients and requires at least one message, and the parser checks
  both. A reply that breaks the rule is forfeited like any invalid reply: none of its orders are
  used, and the captain is asked next from a fresh view, with no re-ask. The router also rejects
  any message on a link outside the topology, with the reason `link`, as a second guard.

The commander may send zero to five messages per reply, because messages are its only output and
forcing it would add filler. The study counts submitted, accepted, delivered and read messages
separately. Captains in every arm still see allied regiments within their 160 m view, so watching
a neighbor move still works, and "exclusively" covers sent messages only.

JUDGEMENT: Forcing rule — Claude, 2026-11-08: one or two messages per captain reply in every arm,
commander zero to five. Exclusive links only or a time floor changes message volume; every
arm's results rest on it.

## The arms

| Arm | Who may message whom | What the commander sees |
|---|---|---|
| P, peers | Any captain to any other captain (20 directed links). No commander | No commander |
| R, relay commander | Each captain to the commander only; the commander to any captain (10 links) | Its inbox, the lobby roster, the plan, the battle clock, the map terrain, the battle's objectives, and each group's unit ids and starting point |
| O, overview commander | Same links as R | All of R's, plus every friendly regiment and every enemy the alliance can see (the view C's existing `global` arm gives) |

Three reference arms sit outside the comparison. M, muted, has P's links and forcing, but every
message is accepted and never delivered; M-O, muted overview, does the same with O's links and
views. Only scripted teams use them, as stage 2's controls for whether a witness's messages
matter. S, unlinked, is five model captains with no links and no
messages: the reference for whether messages help these captains at all, reported beside P, R
and O and outside the tests.

JUDGEMENT: Arm set — Claude, 2026-11-08: P, R and O, with O and R each against P under Holm.
Two arms, other contrasts or a fixed order (O against P first at 5%) change what a result can
say; the stage-4 design rests on it.

In all three arms:

- **Battle and groups.** Battle C v2: the map and placements of Cannae A v2
  (`emp-envelopment-a-v2`), where the enemy's four front Swordsmen are Greatswords. The five
  groups follow the authored slots (`GROUP_SLOTS`: `centre` f1-f4, `left_infantry` f5,
  `right_infantry` f6, `decisive_cavalry` f7-f8, `containing_cavalry` f9). The native AI plays at
  its declared Normal difficulty, the timer is 1,200 s, and the battle runs unpaused at 1x.
- **Captain view and orders.** Each captain sees its own regiments in full, allied regiments and
  alliance-visible enemies within 160 m of its group's anchor regiment, and the lobby roster. A
  new order must be legal both in the view the captain decided from and in its latest view. So a
  captain can move toward an enemy the commander reports, but can attack it only once that enemy
  is in the captain's own view.
- **Channel.** One addressed text channel with no added delay, at most 240 bytes per message and 64
  messages in flight per sender. A message reaches its recipient in the recipient's next model call
  after the dispatcher's next observation. The inbox holds everything delivered since the member's
  last call, oldest first, with no cap; with no delay the 64-message limit rarely binds. Courier
  rendezvous points and signal ranges are not used, because they would make the map's geometry part
  of each arm.
- **Model and scheduling.** `claude-haiku-5-5` at low effort for every agent on one backend, and
  the asynchronous team dispatcher with one pending call per agent and no team-wide wait. A
  captain never waits for the commander before acting.
- **Prompts.** One shared plan for all three arms: the current C plan with its channel paragraphs
  removed and "Tell nearby peers" replaced by "report through the links your rules allow". A new
  captain prompt replaces `local_command_prompt.md`, which describes signals and couriers and tells
  each member it is "one of five commanders". Each arm adds a short rules section that differs
  only in the allowed recipients and, for R and O, one true sentence on what the commander sees.
  The existing C arms keep their prompts byte for byte.
- **Army-wide facts every arm keeps.** Some inputs tell a captain about the rest of the army
  without any message, and all three arms keep them. In the one model battle a "Lord dead" or
  "Lord recently died" morale label reached a captain's own or allied rows in 103 of the 295
  requests where the commanding regiment f1 was out of view (68 on the captain's own units; the
  battle has no lord). The army-wide morale fraction (`morale.fraction`) also stepped down, and
  the exact battle clock and latency feedback reach every captain. The owner's open decision on
  the morale label applies to all arms at once.

These values rest on JUDGEMENT `src/twwarhammer3/battle/local_command.py` Local command
development profile (160 m view, 240 bytes) and Fast text control (64 slots), JUDGEMENT
`src/twwarhammer3/battle/local_team.py` Member message batch (two sends) and Local target
authority, JUDGEMENT `cannae-communication.md` Command groups and local knowledge, JUDGEMENT
`src/gameai/providers.py` Haiku first and Anthropic efforts, JUDGEMENT `cannae-eval.md`
Construction profile (Normal difficulty, 1,200 s timer), and JUDGEMENT? `cannae-communication.md`
Own-unit morale label.

JUDGEMENT: Text channel — Claude, 2026-11-08: one addressed text channel, no added delay, 240
bytes, signals and couriers off. C's bounded channels would add geometry and rendezvous to each
arm; every arm's delivery timing rests on it.

JUDGEMENT: Shared plan v2 — Claude, 2026-11-08: the C plan without its channel paragraphs, a new
captain prompt and a rules section per arm. A plan per arm or the old prompt changes what
captains attempt; every new arm's prompts rest on it.

The commander is a sixth team member with no regiments. Any order in its reply forfeits that
reply. Its prompt asks for intent, warnings and requests in short messages. It cannot die or be
cut off, while a captain whose regiments are all routing, shattered or dead stops sending and
receiving messages in every arm. A commander attached to a regiment that can be killed is a later
arm.

JUDGEMENT: Commander information — Claude, 2026-11-08: inbox only (R) or the existing global
projection (O), no regiments, cannot die. A headquarters view or a killable commander changes R
and O; the O-against-R reading rests on it.

JUDGEMENT: Commander prompt — Claude, 2026-11-08: Haiku low, asked for intent, warnings and
requests in short messages. Direct orders to captains or a stronger model change what R and O
measure; both commander arms rest on it.

## The battle: Cannae C

What exists ([C page](cannae-communication.md), [evaluation page](cannae-eval.md)):

- The router, the five-group split, the 160 m local views, the target rule (a captain may attack
  only an enemy in its own view) and the `global` view (everything the alliance can see) are
  built and have offline tests. No check of C's mechanics is agreed: the agreed Cannae shortcut
  challenges only report one C launch, with no pass rule. So all of it is unverified.
- The groups start far apart. The two cavalry wings are 340 m apart, and the containing
  cavalry's anchor is within 220 m of only right infantry. No anchor sees an enemy at deployment:
  the nearest is 185 m away.
- Before the night of 2026-11-08, four C battles had run, one launch each. On C v1 two scripted
  probe teams won (520.6 s and 481.2 s) although 8 of their 9 regiments never acted on a message,
  and one five-member Haiku team lost at 405.5 s ($0.9382392, 729 calls). On the harder v2 the
  silent local rush, a scripted team that sends no messages and attacks the nearest enemy in its
  local view, lost at 371.8 s. Its decisive Knights saw no enemy until 174.7 s and had no order
  until 175.9 s.
- The cross-group situation C was built for, the containing cavalry failing where the decisive
  cavalry cannot see it, had not happened in those four battles; the night's launches were not
  checked for it. In the one v2 battle (`c-silent-rush-01`) the containing cavalry stayed inside the
  decisive cavalry's view from its first fight at 212.2 s to its rout at 314.2 s, in 66 of the
  decisive cavalry's 67 inputs in that span.
- Before 2026-11-08 no team using local views had won C v2; the only win with C v2's forces and
  placements was the global-view script `WingSupport`, playing A v2, in one launch. That night the
  scripted witnesses won 4 of their 9 launches (overview 3 of 5, peer 1 of 4; see Results so far).

So on v1 messages are not needed to win, and an effect of the links there could not show that a
message carried a needed fact. v2 is harder, so messages may matter there, but two things need
showing first: that captains using messages can win it, and that a fact one group sees decides
something for another. The study therefore runs a $0 construction test on v2 (stage 2) before any
paid battle. If it fails, the next step is a redesign decision: for example groups placed beyond
each other's 160 m view, or a flank threat that only one group can see. C has no hidden events by
design, so the owner decides whether to add one.

JUDGEMENT: Test bed and gate — Claude, 2026-11-08: C v2 behind a $0 witness, foil and cue test,
v1 unused. v1 or a new variant changes whether results can show that a message carried a needed
fact; the start of stage 3 rests on it.

## Stages

Every stage after stage 0 needs the owner's go-ahead, a time window and, for paid stages, a dollar
cap. `--budget-usd` caps the WH3 Anthropic ledger's total including earlier jobs ($13.68 on 2026-11-08, after stage 3), so
each stage's flag is the ledger total at its start plus that stage's allowance.

Costs are estimates from the one paid C battle ($0.94 for a 405 s five-member battle). They assume
about $1.0 to $1.3 per P launch, $1.1 to $1.4 per R launch and $1.15 to $1.5 per O launch,
allowing for the sixth agent, forced messages, O's larger input and battles of up to about 520 s.
A battle that runs to the 1,200 s timer costs about three times as much as a 405 s one. The four C
launches took 7.7 to 10.2 minutes of wall time each, and a timer-length battle takes about 22.

| Stage | What runs | Launches | Cost | Game hours | Gate to the next stage |
|---|---|---|---|---|---|
| 0. Offline build | The code below, tests with planted wrong versions, `scripts/check.py` | 0 | $0 | 0 | Checks pass; the owner agrees the proposed checks and answers the questions |
| 1. Mechanics probes on v2 | One scripted launch per arm. In P a peer's fixed report releases a captain's move. In R and O captains send fixed reports and a scripted commander forwards one, whose message releases the move | 3 | $0 | about 0.5 | Each arm shows one traced chain: a sender's observation, an accepted message, the recipient's next call containing it, a changed order and its effect in the engine. No captain-to-captain delivery in R or O |
| 2. Construction test on v2 | Two scripted witnesses that win through the captains' local views by using messages, up to 5 launches each: one on peer links, run as P (for example the center reporting first contact to the cavalry), and one on commander links, run as O (a commander that sees the whole field directing the cavalry). No R witness is planned, so stage 2 does not show that a commander who sees only its inbox can lead a winning team. Three control teams (foils) that send no useful messages, up to 5 launches each and stopping at a first win: the silent local rush, a fixed timed schedule, and central concentration (every group joins the center's fight; the card gives details) | up to 25 | $0 | about 3 to 4.5 | Each witness wins at least 4 of 5. Every foil loses all its launches. In at least 2 witness launches a fact seen by one group and needed by another comes up (the cue), and the latest time a response still helps is measured in the engine |
| 3. Paid pilot | P, R and O with Haiku, 2 launches each, in two blocks of three | 6 | about $6.5 to $8.5 (about $20 at the timer) | about 1 | No harness failure. Forced-rule forfeits under 10% of each agent's calls. Zero captain-to-captain deliveries in R and O. Every recorded model input and router entry has its full-battlefield snapshot ([row 5](cannae-eval.md#proposed-deciding-checks-2026-11-05) of the proposed Cannae deciding checks, which scripted launches cannot show). Cost within 1.5 times the estimate. Prompts and revision are then frozen |
| 4. Scored comparison | P, R and O, 15 fresh launches each, in 15 blocks of one launch per arm, with a recorded random order and balanced first slots | 45 | about $50 to $65 (about $150 at the timer) | about 6 to 8 (about 16.5 at the timer) | Gives the comparison's result for these prompts at this revision, unverified unless the proposed checks are agreed and pass there. Follow-up work only if a contrast resolves and the owner agrees again |

What ran on the night of 2026-11-08 differs from row 2: the fixed-schedule and central-concentration
foils did not run on C v2 (concentration ran only on Massed horse), the R witness was built but did
not run (it waited on a peer pass), and the muted controls and the rush with think time replaced
them; the card below records the round as run.

The prompts are tuned on the same battle that stages 3 and 4 score, and no launches are kept
aside as a separate test.

JUDGEMENT: Stage thresholds and size — Claude, 2026-11-08: witness 4 of 5, forfeits under 10%,
15 launches per arm. Other values change what passes and the power of stage 4; the go-ahead
for stages 3 and 4 rests on them.

## Stages 1 to 3 card (night of 2026-11-08)

Written by Claude under the owner's go-ahead ("Implement up to stage 3", $10). The owner has not
agreed this card (away card). Methodology review: `runs/comm-build-20261108/method-review.json`.

- **Decisions it informs.** Stage 1: whether the links, the commander and forced messages work
  live at 1x. Stage 2: whether C v2 can carry P, R and O, meaning a scripted team using messages
  can win through the captains' local views and the same team loses with its messages cut. Stage
  3: whether the model arms run cleanly enough to freeze prompts and revision for stage 4.
- **Stage labels.** Stage 1 and stage 3 are explore. Stage 2's gate round is a screen; witness
  development launches before it are explore, listed and kept, and never count toward the gate.
- **Scripted timing.** Every scripted witness and foil captain sleeps 2.0 s inside its worker per
  decision, close to the Haiku captains' median think of 2.03 s in `c-model-smoke-02`; a scripted
  commander sleeps 3.0 s. The stage-1 probes at `5b7de0c` have no think time; they test mechanics
  only. Scripted members obey the same forcing rule as model captains.
- **Stage 2 gate round.** Revised at 04:05 local, after the two development launches and before any
  gate launch, because the overview witness won its development launch and the peer witness lost.
  `runs/comm-build-20261108/stage2.py` runs, in rounds shuffled from seed 20261108 + round: the
  overview witness (up to 5), the same witness on `emp-envelopment-c-muted-overview-v2`, where
  every message is accepted and never delivered (up to 5), the peer witness (up to 5), and the
  silent local rush with the 2.0 s think time (up to 5). Only if the peer witness passes, a second
  round runs the muted peer witness and the R witness (up to 5 each). Stopping: a witness stops at
  its fourth win or second loss; a foil at its first win. A witness passes at 4 of 5 when its muted
  control and the rush lose all their launches, and the cue occurs in at least 2 of its launches. A
  foil launch counts only if each group gave an accepted attack before the ending. A failed gate is
  kept and not rerun without a logged change.
- **Cue.** The first 1 Hz replay frame in which a centre regiment is in melee while no enemy is
  within 160 m of the decisive cavalry's anchor; latest useful time is not estimated tonight.
- **Stage 3.** P, R and O, two blocks of three in an order drawn from seed 20261108, plus one
  silent model launch (arm S, `emp-envelopment-c-unlinked-v2`) only if the budget rule allows.
  `--budget-usd 17.10` (WH3 Anthropic ledger $7.1042605 at start plus the owner's $10). A job starts
  only if the ledger total plus its arm's high estimate times 1.5 (P $1.95, R $2.10, O $2.25, S
  $1.95) is at most 17.10; otherwise the plan stops and later jobs are unstarted. Prompts are frozen
  before stage 3; a change during it applies to all arms and restarts the count.
- **Dispositions.** Engine win (timer included): win, with its ending shown. Engine loss or draw:
  non-win. Terminal controller failure: forfeit, non-win. Construction failure: non-win, shown
  apart. Error after the ending: the ending counts, the error is a reliability failure. A member's
  calls failing while the battle runs: the ending counts, flagged. Spend-cap stop mid-battle:
  "budget stop", excluded and not replaced. No engine outcome for a game or setup fault: one new
  launch at the end of the plan, applying by extension the agreed Cannae harder-B replacement rule;
  a second failure is a non-win. Every planned launch gets one disposition.
- **Limits.** Start 600 s, episode 1,320 s, job 2,000 s (the earlier C cards), unpaused 1x,
  `--stills`. Battle cutoff 11:15 local (-03:00): no plan starts a job it cannot finish by then.
- **Depends on.** The agreed direct model team check (2026-11-02) and the agreed scripted team
  check cover `team.py`, which this work does not edit. C's local views, router and the new links
  have no agreed check; everything here is unverified.
- **Analysis.** `runs/comm-build-20261108/gates.py JOB...` prints per job the ending, the
  dispositions, the message funnel per link, link integrity, forced-rule compliance, the cue time
  and the traced chain for stage 1.

## Results so far (night of 2026-11-08)

All results below are unverified: no check of C's mechanics is agreed, and each arm has one to five
launches. Gate numbers come from `runs/comm-build-20261108/gates.py`, the pilot measures from
`pilot_measures.py` and the listening counts from `listening.py` in the same folder; each script's
docstring fixes its definitions.

**Stage 1, at `5b7de0c`, $0, unpaused 1x, three scripted probe launches on v2, plus one rerun at
`e174a7d`.** In every arm the release message reached left infantry, its move to x = 40 (about 42 m
east) was accepted, and its regiment moved 35 to 40 m east before its next order (peer: in left
infantry's input at 6.1 s, applied at 7.6 s; overview and relay: in its input at 7.9 s, applied at
9.7 s, after the commander forwarded the report). No captain-to-captain text was delivered in relay
or overview, every captain decision carried one message (apart from messages discarded at the
episode's close), and every input and router row had its global frame. All three lost (peer 329.9 s,
overview 474.5 s, relay 410.3 s), which is expected of a probe that rushes on v2. The relay and
overview probes sent no text outside their links, so the router's refusal of a captain-to-captain
send was not tested live; card D added such a send to the probe. The rerun, `s1b-relay-probe-01` at
`e174a7d`, refused right infantry's text to left infantry with reason `link`, delivered no text
outside its links, and repeated the release chain (input 8.2 s, applied 10.0 s, 38 m east before
its next order).

A second rerun, `s1c-overview-probe-01` at `65481c9`, refused right infantry's text to left
infantry with reason `link` in the overview arm, delivered no text outside its links, kept every
frame, and repeated the release chain (input 7.9 s, applied 9.7 s, 37 m east before its next order).

**Stage 2 witness development, at `5b7de0c`, $0, explore.** Both witnesses ran with no think time,
so they decided faster than the model arms. The peer witness lost at 269.7 s. The overview witness
won at 391.1 s, the first win with C v2's forces through the captains' local views; its commander's
orders reached the cavalry and Greatswords at 6 to 7 s, while the peer witness's first moves came at
18 to 21 s, after the center's first contact report.

**Stage 2 gate round, at `12a00f8`, $0, 2.0 s scripted think time (3.0 s for the commander).** 17
launches ran from `stage2.py` under the pre-registered order and stopping rules (`stage2-log.json`,
`stage2-gates.json`). No witness passed: the gate needs 4 of 5.

| Cell | Launches (ending, and `taken` for each loss) | Verdict |
|---|---|---|
| Overview witness | lost 586 s (90.4), won 582 s, won 414 s, lost 369 s (52.6) | fail, 2 of 4 |
| Overview witness with its mail cut | lost 367 s (33.5), 539 s (36.0), 362 s (38.8), 398 s (35.8), 697 s (68.5) | lost all 5 (4 executed) |
| Peer witness | lost 585 s (93.3), won 306 s, lost 455 s (71.5) | fail, 1 of 3 |
| Silent local rush, 2.0 s think time | lost 361 s (45.3), 336 s (50.5), 402 s (40.2), 302 s (30.6), 413 s (50.9) | lost all 5 |

- Neither witness won C v2 reliably through the captains' local views at model-like timing, so this
  battle is not shown to separate the arms, and the stage-3 pilot below cannot compare P, R and O.
  The pilot still says something about the models' play: each of its six P, R and O launches took
  less of the enemy (1.9 to 30.0) than each of the ten scripted launches without delivered messages
  at 2.0 s think time (30.6 to 68.5), at similar order ages; one launch per pilot cell, at
  different revisions, and a comparison chosen after looking at the results. The second round
  (muted peer witness, R witness) did not run.
- The overview witness with its mail cut ran the same code and views and lost all 5, 4 of them
  executed foil launches, while the witness won 2 of 4 (Fisher exact test, p about 0.17 against 0 of
  5; 0.43 against the 4 executed). With wins counted as 100, the witness's mean `taken` was 85.7 and
  the mail-cut witness's 42.5 (44.1 over the 4 executed). Of tonight's results, this gap is the
  clearest sign that the commander's target orders, chosen from its whole-field view and delivered
  through the router, change the outcome. Without them each captain holds and fights only enemies
  within 90 m (in the second muted launch the containing cavalry gave no order in 199 decisions), so
  the control is a holding team. It is an exploratory reading of 9 launches, and the stage-2 gate
  does not score `taken`.
- The second launch of the mail-cut witness does not count as a foil launch, because at least one
  group never attacked; the table, the Fisher test and the means above still include it.
- The cue detector fired in no witness launch before its ending. It fired only at the final frame of
  the overview witness's 582 s win and the peer witness's 306 s win, where every enemy near the
  decisive cavalry was routing, so no witness had it in 2 launches. It also fired at 34 to 36 s in
  all five rush launches and at 64.0 and 637.0 s in two mail-cut launches. Its definition needs work
  before it can gate anything.
- A redefined detector after the round (`gates.py` `wing_cue`, written before it was run): the
  first frame, before the ending and not the last one, where a cavalry regiment is in melee more
  than 160 m from the other cavalry group's anchor, and a "failing" version with that group at 75%
  or fewer of its starting men. Its expected behaviour was written down first: never at a final
  frame, the containing wing first on Massed horse's south and far draws, the decisive wing first
  on the north draw. It met all three on the 18 Massed horse launches (12 of 12 south and far
  launches fired for the containing wing at 30 to 63 s, 6 of 6 north launches for the decisive wing
  at 30 to 49 s, none at a final frame; `cue-check.json`). On C v2 the overview witness never had a
  cavalry wing fighting out of the other's sight, while every mail-cut launch did (at 94 to 150 s):
  the commander's orders kept its wings within sight of each other. This check is weak: the
  final-frame expectation holds by construction (the detector skips the last frame and frames after
  the ending), and which wing fights first follows from the Massed horse layout, so it shows the
  detector reports what the layout implies, not that it finds useful cues. The new detector is a
  proposal; the card's definition stands for tonight's gate. The card's own cue was never checked
  offline before the round, as the methodology review asked; run on `c-silent-rush-01` it fires at
  33.1 s, the same defect the round then showed.

JUDGEMENT?: Wing cue — Claude, 2026-11-08: the cue is a cavalry regiment in melee over 160 m from
the other wing's anchor (`gates.py` `wing_cue`). Another radius or a centre-based cue changes which
battles have a cue; any later cue gate rests on it.
- Every launch reached an engine ending, no text was delivered outside its arm's links, and every
  input and router row had its global frame.

**Stage 3 pilot, at `e174a7d`, Haiku 5.5 low, explore.** Seven launches ran in the card's order (P,
O, R, then O, R, P, then S) and cost $6.29 of the owner's $10 (WH3 Anthropic ledger $7.1042605 to
$13.3923583), $0.76 to $1.15 and 599 to 1,023 calls each. Every launch reached an engine ending and
lost; the card does not score outcomes in the pilot. No captain-to-captain text was delivered in R
or O, every input and router row had its global frame, and every captain decision carried its one
or two messages. Per launch (`pilot-measures.json`, `pilot-gates.json`):

| Launch | Battle s | `taken` | USD | Forfeited replies | Delivered texts | Median age when read (s) | Median age via the commander (s) |
|---|---:|---:|---:|---|---:|---:|---:|
| P 1 | 349.1 | 26.7 | 0.82 | centre 4 | 621 | 3.3 | |
| P 2 | 316.3 | 30.0 | 0.81 | centre 1 | 645 | 3.3 | |
| R 1 | 265.6 | 23.8 | 0.76 | none | 834 | 3.9 | 6.6 |
| R 2 | 397.5 | 1.9 | 1.15 | centre 1 | 1,082 | 3.6 | 6.3 |
| O 1 | 250.3 | 17.4 | 0.77 | centre 2, decisive 1 | 804 | 3.6 | 6.3 |
| O 2 | 330.8 | 14.9 | 0.96 | centre 6 | 1,026 | 3.9 | 6.3 |
| S 1 | 396.5 | 30.6 | 1.01 | centre 1, decisive 56 | 0 | | |

- Gate: P, R and O passed. No launch had a forced-rule forfeit: all 72 forfeits were invalid orders
  (15 orders to another group's regiment, 57 attacks on an enemy outside the captain's view).
  Counting every forfeit, each agent in P, R and O stayed under the 10% limit (worst: O 2's center,
  6 of 130 calls, 4.6%), and cost stayed within 1.5 times the estimate. S, which is outside the
  gate, went over that limit: its decisive cavalry forfeited 56 of 220 replies. Each of those
  replies ordered the group's second regiment, f8, to attack the enemy Knights f8 was already
  fighting (e9 in 8 replies at 148 to 159 s, e10 in 48 at 252 to 316 s). Those Knights were 160 to
  297 m (median 287 m) from the anchor f7, outside the anchor's 160 m view, so the local target
  rule refused the whole reply. This refusal rests on JUDGEMENT
  `docs/twwarhammer3/cannae-communication.md` Command groups and local knowledge, JUDGEMENT
  `src/twwarhammer3/battle/local_command.py` Local command development profile (the 160 m view) and
  JUDGEMENT `src/twwarhammer3/battle/local_team.py` Local target authority (orders legal in the
  local view). The whole-reply refusal itself comes from `parse_reply` inside `api.ask`, with no
  retry and no partial salvage (`local_team.py`, `LocalModel`), which carried no marker until the
  one below.

JUDGEMENT?: No partial-order salvage — found by Claude, 2026-11-08 (Codex's rule of 2026-11-05,
`local_team.py` `LocalModel`): one illegal order forfeits the whole reply. Dropping only that order
changes forfeits and actions; S's 56 refused replies rest on it.

- Mail to the center in P: the center received 61% and 80% of delivered texts in the two P battles.
  The shared plan tells the infantry to support the center and says "one ordinary regiment
  commands", so the plan may have caused this.
- Age through the commander: in R, the newest captain report behind a commander text was a median
  6.6 and 6.3 s old when a captain read the text, against 3.3 s for P's captain-to-captain texts.
  O's commander texts drew on reports of the same age (6.3 s), but O's commander also saw the whole
  field in every input, and its texts were a median 3.9 s old, counted from that view, when a
  captain read them. Single steps in R and O took a median 3.6 to 3.9 s for captain reports read by
  the commander and 3.9 to 4.2 s for commander texts read by captains. The commander's inbox held a
  median 4 to 6 texts per call (at most 10), and its oldest text was a median 4.5 to 5.1 s old.
- Unseen enemy ids: texts naming an enemy id that the sender had neither seen nor received in a
  text numbered 0 to 16 per R or O battle, and 41 and 0 in the two P battles. All 60 such texts
  were roster references or requests (58 from the containing cavalry, such as "Enemy knights e9/e10
  not yet visible", and 2 from the R 1 commander, "Report immediately on contact with e9/e10");
  none reported an unseen enemy as seen.

**Listening, $0.29, after the pilot.** From the P, R and O pilot battles, 17 recorded captain
inputs per arm that held delivered mail were each re-sent to Haiku twice as recorded and twice with
the mail removed (`listening.py`, `listening.json`). The run stored an empty order list and an
unparsed reply alike as null (91 of 204 replies). Five null replies cost $0.0090 to $0.0093, about
16,000 output tokens, which is the call's cap; they were cut off, and the script's rule excludes
them. The other 86 cost $0.0009 to $0.0014 and are read as empty order lists; this is unchecked,
because their text was not stored. Leaving out every comparison that includes one of those five
replies, orders differed this often:

| Replies compared | P | R | O |
|---|---|---|---|
| The two as-recorded re-asks | 3 of 17 | 2 of 17 | 10 of 16 |
| The two mail-removed re-asks | 2 of 14 | 7 of 17 | 8 of 16 |
| First as-recorded and first mail-removed | 6 of 15 | 5 of 17 | 10 of 16 |
| Second as-recorded and second mail-removed | 4 of 16 | 4 of 17 | 8 of 16 |

Only in P did as-recorded and mail-removed replies differ more often than both pairs of re-asks of
the same input. In R and O, re-asks of the same input varied as much as either comparison, so this
sample shows no effect of mail there. In P the as-recorded and mail-removed replies differed more
often than the re-asks (6 of 15 and 4 of 16 against 3 of 17 and 2 of 14), a gap this sample cannot
separate from re-ask noise (two-sided Fisher p about 0.24 and 0.66), and 4 of the 6 first-pair
differences set a reply counted as empty against one with orders. The counts come from
`listening.json` `summary_corrected_2`, a correction written after the run.

### Is the evaluation working? (2026-11-08)

What each piece of evidence establishes, at the revisions named. None is an agreed check, so all of
it stays unverified under the owner's rule until one is agreed (a proposal is in the handoff).

| Evidence | What it shows | Limit |
|---|---|---|
| Offline tests of the v2 arms (`test_wh3_local_topology.py`, `test_wh3_local_scripts.py`, `test_wh3_report_comm_arms.py`, `test_wh3_wing_horse.py`) | Links, forcing, commander scheduling and views, muted delivery, mail on forfeit, report classification and the Massed horse entries behave as specified | Component level; fake observations |
| Full plant replay, `scripts/check.py --plants` at `65481c9` | 418 of 420 planted wrong versions caught, including all 12 `local-v2-*` plants from tonight; the 2 misses are the known ones on the status page | Only the bugs someone thought to plant |
| Live probes at 1x (`s1-*`, `s1b-relay-probe-01`, `s1c-overview-probe-01`) | Messages travel from sender to engine effect in every arm, links refuse off-link sends live, and every input and router row has its global frame | One launch per arm |
| Stage-2 gate | It ran as pre-registered and kept its failure: no scripted witness reached 4 of 5 at model timing (2 of 4 and 1 of 3), so model losses there are not read as weak tactics. A losing witness shows only that these scripts fail there | Gate thresholds are Claude's (marked); the cue part was broken, and no replay or concentration foil ran on C v2 |
| Independent recounts (`review-night-1.json`, `review-night-2.json`, a final recheck) | Every number on this page was recomputed from raw records by a reviewer; their corrections are applied | Reviewers can share blind spots |
| Wing cue detector | Met three expectations written before it ran, on 18 Massed horse launches | A weak check (one expectation holds by construction, the others follow from the layout); a proposal (JUDGEMENT? Wing cue) |
| Report browser check (`check_wh3_report_browser.cjs`) | The page built from 18 night jobs matched the collector's JSON until line 310, where the check assumes a first decision with orders; the page correctly says "this reply" for an empty one (`replay.js` line 1266) | The check needs a team-battle case; not edited tonight |

## Measures

The primary measure is one engine team result per fresh launch. A won battle counts as a win,
including one the engine awards our side at the 1,200 s timer. An engine loss or draw is a
non-win. A terminal controller failure is a non-win labeled forfeit and reported per arm. A launch
that ends with no engine outcome because of a game or setup fault gets one new launch, using the
replacement rule this study borrows from the agreed Cannae harder-B check. All agents in one
battle together give one sample.

Secondary measures are descriptive. The experiment card defines each one before stage 4.

| Measure | Definition |
|---|---|
| Score, `taken`, `own`, `killed` | The score is 100 for an engine win and otherwise `taken`, the percent of enemy men dead, routed or gone at the ending (`suite.taken` is not 100 on every timer win, so the score sets it). Also the condition score of our army and the percent of enemy men dead. Each win's ending (rout or timer) is shown |
| Transport and resources | Per agent: time from reply completion to the engine's acknowledgement, the share of mailbox cycles taken by commander replies, and calls, tokens and delivered bytes per battle minute |
| Grounding | For each message naming a unit id: whether the sender could know it (its own view at the source time for captains, a report in its inbox for R, its view for O). Unmatched ids are counted as ungrounded |
| Fact reach | For each cue and each enemy id named in a message: the first frame any group saw it, when it entered the dependent captain's input, and by which path (direct, through the commander, or by sight) |
| Message funnel | Per link and agent: submitted, accepted, rejected by reason (link, size, slots, anchor), delivered, and read in the recipient's next call |
| Information age at use | For each read message, the recipient's call time minus the sender's observation time. In R and O also the two-step age: from the observation time of the newest captain report in the commander call that produced the message, to the call of the captain who read it |
| Commander load | At each commander call: inbox length, age of the oldest unread message and think time. Also the number of captain reports the commander never followed with any message |
| Cue response | Each time the cue (proposed: the wing cue in Results) comes up: time from the first observation by any group to the dependent group's first changed order, and whether that came before the latest useful time |
| Mail to each captain in P | Share of P's delivered texts received by each captain over time, to see whether one captain becomes a hub |
| Order age and reliability | Per agent: order age from member feedback events, invalid orders, forfeits and provider failures |
| Cost | Dollars, calls and tokens per launch, split between captains and commander, and dollars per win (undefined at zero wins) |
| Link integrity | Delivered captain-to-captain messages in R and O. It must be zero |

No combined coordination score is added. When the budget allows, a listening measure re-asks
the same model on a fixed sample of recorded captain inputs with and without their delivered
messages, so the change in orders shows whether messages changed decisions (after the causal
influence idea in Lowe et al. 2019). It tests a decision, not an outcome.

## Statistics

The unit is the fresh launch, and the arms share no launches. Each comparison uses a two-sided
Fisher exact test on wins, with a Newcombe 95% interval for the difference. Each arm gets a Wilson
95% interval, or at zero wins the exact one-sided bound (0 of 15 is below 18.1%). The two main
comparisons, O against P and R against P, are Holm-corrected. O against R and the secondary
measures are exploratory, and `taken` gets a t interval. These follow
[evaluation-guidelines.md](evaluation-guidelines.md) §7, whose adoption as an agreed method is
still open as item 7 of that page's
[owner decisions](evaluation-guidelines.md#13-owner-decisions-these-rules-need).

Each cell gives the exact power of the Fisher test at two-sided 5% and at 2.5%, the first Holm
step (`runs/communication-structure-20261108/power.py`):

| Launches per arm | 0%→30% | 0%→50% | 10%→50% | 20%→70% | 30%→60% |
|---|---|---|---|---|---|
| 10 | 0.15 / 0.05 | 0.62 / 0.38 | 0.30 / 0.21 | 0.43 / 0.41 | 0.12 / 0.12 |
| 15 | 0.48 / 0.28 | 0.94 / 0.85 | 0.54 / 0.44 | 0.68 / 0.56 | 0.23 / 0.15 |
| 20 | 0.76 / 0.58 | 0.99 / 0.98 | 0.74 / 0.63 | 0.85 / 0.80 | 0.35 / 0.29 |

At 15 launches per arm only large differences are likely to resolve. A comparison that does not
resolve is reported as unresolved, with no claim about which arm is better. The comparison stops
early only when no remaining launch can change a result. If none of the six pilot launches wins
(a true 20% win rate in every arm gives that about one time in four), the owner chooses before
stage 4 between a redesign and making `taken` the primary measure.

## Code changes

The smallest version, from a reading of the code at `cfe8ab5`:

- **Router links** (`battle/local_command.py`). An optional set of allowed links, with `None`
  keeping today's behavior, checked at each text send. Today only couriers can pass a received
  message on to another member, and the new mode turns couriers off along with signals. Rejections
  record a reason (link, size, slots, anchor) in the router's events, and in the acknowledgement
  only in the new mode, because acknowledgements reach every member's input. The 240-byte, 64-slot
  profile is passed per arm and never added to `PROFILE` or `FAST_PROFILE`, which every old input
  and card copies. This follows
  [MAGIC](https://github.com/CORE-Robotics-Lab/MAGIC/blob/0ad3a6126f46e475f8d46ab61e67fddbfe99e7d8/magic.py),
  where messages flow only along an adjacency matrix masked by which agents are alive, and
  [MARBLE](https://github.com/ulab-uiuc/MARBLE/blob/8d60fa17b5596b44458a52d4296061b9fc13d6f2/marble/agent/base_agent.py),
  which lists each agent's allowed recipients in its message tool. MARBLE's handler checks only
  that the sender has some link, so the router checks every sender and recipient pair itself.
- **The commander** (`battle/local_team.py`). Allow a sixth member named `commander` only under
  the new declaration. Pass it as the team's `army_owner`, so the rule that skips a member with no
  living men does not skip it. C views carry no army orders, so this grants no authority, and
  `team.py` stays untouched, along with the agreed checks whose tests use it (the two team checks
  and the GaP checks). Give the commander a router endpoint: a rendezvous entry and an anchor
  added after every `local.anchors` call, kept out of `local.project`, which would otherwise give
  R's commander a 160 m view around that point. Give it its own view (an empty local view for R,
  the existing global projection for O), its inbox at every call despite the living-men gate in
  `_view`, and a card line saying `army_owner` names it only so that it is asked.
- **Composition** (`battle/configured.py`). Accept the sixth member only under the new declaration
  (today a `local_team` node must name exactly the five groups), give the commander its own system
  prompt (today every model leaf of one type gets the same prompt), and record the new input
  version in the member cards.
- **Limits and forcing.** Per-member minimum and maximum message counts read from the call's rules
  block. In the Anthropic schema, `minItems: 1` (Anthropic accepts `minItems` of only 0 or 1) and
  the allowed recipients as an enum. The same counts and recipients are checked in the parser,
  since Anthropic notes that enum values can come back with different capitalization, and in the
  dispatcher.
- **Declarations and prompts.** A communication declaration version 2 carrying the topology, the
  commander's view and the limits. Scenario entries `emp-envelopment-c-peer-v2`,
  `emp-envelopment-c-relay-v2` and `emp-envelopment-c-overview-v2`, on which stage 1 also runs.
  Controller files for the model and probe teams. The shared plan v2, the captain prompt v2, the
  three rules sections and the commander prompt as new files. `local.project` takes the input
  version as an argument in place of its fixed `local-command-v1`.
- **Probes and witnesses.** Scripted probe captains and a scripted commander for stage 1, and the
  two scripted v2 witnesses for stage 2. The witnesses are the least certain part of the build.

These files are in `play`'s source scope, so the harness fingerprint moves for every WH3 job played
afterwards, and new C rows never pool with the four existing ones. The `local_team.py` edits also
change the controller identity of the C silent-rush launch that the agreed Cannae shortcut
challenges run, so that check's next C row will not pool with its earlier one. Land the change
as one logged version while no queue runs.

## Proposed checks

None of these is agreed. Each goes to [agreed-checks.md](../agreed-checks.md) only after the owner
agrees it.

| Check | Plausible wrong version it must catch |
|---|---|
| In R and O the router rejects a captain's message to another captain with the reason `link`, and the parser forfeits a reply naming such a recipient. A message to the commander is accepted. Every delivery's pair lies in the links logged at the start | The filter checks only that the sender has some link (MARBLE's gap), or the parser trusts the schema's enum |
| The commander is asked with no units, reads its inbox exactly once per call, and any order from it forfeits the reply | The skip for members without living men, or the living-men inbox gate, still applies |
| R's commander input is byte-identical under any change to units it cannot know about. O's never contains an enemy the alliance cannot see or any `evaluation`, `final` or `setup` field | R's commander gets a 160 m view around its endpoint, or O reads hidden state |
| A captain reply with no messages, or more than two, forfeits with no partial orders, and the Anthropic request carries `minItems: 1` | The parser accepts empty lists, or the minimum is enforced only on the wire |
| The four existing C arms keep their schema bytes, inputs and configuration digests | The new text profile or a rejection reason leaks into `PROFILE`, the rules block or the old arms' acknowledgements |
| Live at 1x: one traced chain per arm from observation to engine effect (stage 1), and every recorded model input and router entry has its full-battlefield snapshot (stage 3) | Component tests pass while live delivery, timing or recording fails |

## Risks

- **The commander's view.** On v2 no captain sees an enemy at the start, while O's commander sees
  every enemy the alliance sees. An O win may come from that view alone. R tests the links
  without it.
- **No wins.** Haiku lost all eight of its C battles (one on v1, seven in the v2 pilot); scripted
  witnesses won 4 of 9 local-view launches on v2. If every model arm stays near zero wins, the
  result is unresolved.
- **Chatter.** Forced messages may bury useful facts, and in R and O all captain mail lands in one
  inbox. The funnel and commander load measures show this, and question 1 offers a slower forcing
  rule.
- **Capacity between captains.** Captains send as many messages in R and O as in P, all to one
  inbox, and a fact reaches another captain only inside one of the commander's at most five
  messages per reply. So captain-to-captain capacity can be lower than in P. R and O captains also
  read less incoming mail, so their calls may be shorter.
- **Mailbox cycles and the extra step.** Each member's reply, including a commander reply with no
  orders, takes one round trip through the game's mailbox before the dispatcher can send the next,
  so a sixth member adds to that queue. A relayed fact also waits for the commander's current call
  and its own think time. Captains thought for a median 2.0 s in the one model battle; a
  commander's think time is unmeasured and likely longer in O. Both count as part of R and O and
  show in order age and information age.
- **Prompt differences.** The rules sections differ by arm, and O's captains are told that the
  commander sees more. Both are fixed and recorded with each arm.
- **Difficulty and drift.** C runs at Normal, below the owner's very-hard direction, and the owner
  decides whether this study may use it (it rests on JUDGEMENT `cannae-eval.md` Construction
  profile). How much the native AI varies between launches on v2 is unknown. Blocks spread each
  arm over time.
- **Budget.** The Anthropic key's $200 is shared by both games, and its three ledgers summed to $7.34 before stage 3
  (WH3 $7.10, Spire $0.21, provider smoke $0.02, each rounded). If every battle in stages 3 and 4
  ran to the timer they would cost about $160 to $170, leaving about $23 to $33 of the $192.66 then
  left.

## Massed horse variant (draft, 2026-11-08)

Claude's draft for owner review, from the design in `runs/comm-build-20261108/battles-research.json`
("Massed horse" and "Late horse"). Its kill test ran on 2026-11-08 at `4509dd4` (below); nothing
here is verified.

**The question.** In the one C v2 battle where it was measured (`c-silent-rush-01`), the containing
cavalry stayed inside the decisive cavalry's view from its first fight at 212.2 s to its rout at
314.2 s, in 66 of the decisive cavalry's 67 inputs in that span, so no fact had to travel between
the wings. Here both enemy Knights start on one friendly cavalry wing, 380 m from the other wing,
which cannot see that fight. Does the other wing learn of the threat in time to help, and does a
peer message carry the fact faster or more reliably than a relayed one?

**The battles** (`configs/twwarhammer3/scenarios.json`). Each is A v2's armies, map and settings
with the friendly Knights moved: the decisive pair to (65,-60) and (5,-60), the containing
regiment to (65,-440). Only the start of the two enemy Knights differs between the three:

- `emp-wing-horse-south-v1`: (250,-455) and (310,-455), on the containing wing.
- `emp-wing-horse-north-v1`: (250,-45) and (310,-45), on the decisive wing.
- `emp-wing-horse-south-far-v1`: (420,-470) and (480,-470), 170 m further east, so they may reach
  the containing wing later (unmeasured).

A run plan chooses the draw for each launch by its scenario name, which reaches no policy; the
enemy roster and every other start point are the same in all three. Each has a `silent` arm
(communication version 1, for the scripted foils) and `peer` and `muted` arms (version 2), named
`emp-wing-horse-<draw>-<arm>-v1`. C's groups, plan v2, witnesses and controller files are reused
unchanged. Relay, overview and unlinked arms are added only after a draw-matched witness passes.
Offline checks: `tests/twwarhammer3/test_wh3_wing_horse.py`.

**The fact that must travel.** On the south draws the containing captain sees the horse and the
decisive wing does not. The decisive wing must set off at least one ride before the containing
wing breaks: about 49 s for 380 m at the 7.8 m/s the designer read from traces. On the far draw
the fact is also when the horse arrive. On the north draw the decisive wing sees the horse, and
the containing wing must come north or strike the enemy infantry. The latest useful time is the
threatened wing's last able frame in rush and muted launches, minus the ride.

**Kill test** ($0, unpaused 1x, about 7.5 minutes a launch; run on 2026-11-08 at `4509dd4`, plan
`runs/comm-build-20261108/horse-kill.json`).
`CentralConcentration` (`cannae-local-concentrate.json`) and `ThinkingRush`
(`cannae-local-rush-think.json`) on the silent arm of each draw, six launches, before any witness
launch. A foil win ends the design, because it shows the cavalry can win with no message. Read
the 25 m placement match, each enemy Knights' first melee opponent, the threatened wing's last
able frame and the ending.

Result: all six foils lost, every group in each launch attacking and reaching melee (`gates.py`,
`horse-gates.json`): concentration lost the south draw at 333.4 s (`taken` 40.7), north at 331.9 s
(50.0) and far at 321.1 s (37.4); the rush with 2.0 s think time lost south at 475.0 s (58.6), north
at 359.3 s (44.9) and far at 393.5 s (56.3). One launch each, so no foil is shown unable to win; the
next step is the peer witness and its muted control on each draw. Only the endings are read so far;
the placements match within 8 m, and the other planned readings (first melee opponents, the
threatened wing's last able frame) are not yet read.

**Witness development** ($0, explore, at `3b84fa9`; plans `horse-witness.json` and
`horse-muted2.json`, readings `horse-witness-gates.json`). The peer witness ran twice on each draw
and the same witness with its messages cut (the muted arm) twice on each draw; every launch
executed.

| Draw | Peer witness | Muted witness |
|---|---|---|
| South | won 380 s; lost 387 s (61.2) | lost 648 s (81.9); lost 485 s (74.4) |
| North | won 593 s; lost 432 s (70.9) | lost 437 s (60.0); lost 578 s (78.0) |
| South-far | lost 362 s (53.1); lost 646 s (90.1) | lost 258 s (33.7); won 499 s |

The peer witness won 2 of 6 and the muted witness 1 of 6, with mean `taken` (wins as 100) of 79.2
against 71.3. So these launches do not separate the two, and the muted win shows the far draw can be
won without a delivered message. The second muted launch on each draw was added after the first
round, with its purpose recorded before it ran, to give both arms two launches per draw.

JUDGEMENT: Wing horse draw — Claude, 2026-11-08: which wing (and near or far) the enemy Knights
start on is chosen per launch, a hidden fact C otherwise excludes. A fixed side lets a team prepare
for it with no message; every `emp-wing-horse-*-v1` entry in `scenarios.json` rests on it.

JUDGEMENT: Wing horse geometry — Claude, 2026-11-08: friendly Knights wings 380 m apart, at
(65,-60)/(5,-60) and (65,-440). Closer wings see each other's fight; the cue and the deadline rest
on it.

JUDGEMENT: Wing horse force — Claude, 2026-11-08: A v2's harder enemy. A v1's Swordsmen front
(hold won 8 of 8 on `emp-envelopment-b-v2`, 2026-11-05) may win unaided; every result rests on it.

JUDGEMENT?: Wing horse plan — Claude, 2026-11-08: the arms reuse plan v2 unchanged, since its text
stays true. A plan naming the wing threat changes what captains attempt; the model arms rest on it.

## Later expansions

Each needs its own card.

- An open network with a commander: captains may message peers and the commander. Against R it
  isolates the link restriction, and against P the extra agent.
- A wheel, W: the centre captain is the hub for the other four, with five agents and no
  commander. Against P it changes only the links, the classic wheel against all-channel contrast;
  against R it shows what a hub without regiments adds.
- A union view, U: the commander sees the union of the five captains' views, between R and O.
  U against R measures automatic pooling against pooling by message, and O against U the
  information beyond every captain's 160 m.
- Paired branches from a battle checkpoint taken just before the cue, continued at 1x under each
  arm, once a restore check for C's armies passes. Pairing at the start adds nothing: in the
  register two controllers sharing one launch correlate at -0.18 on `taken` (109 pairs).
- A C variant with B3's seeded reserve, so the side of the threat varies by launch and only the
  nearest group sees it (a hidden event, which the owner decides).
- A peer arm with a delay matched to the commander's extra step.
- Equal-resource arms, with the commander's calls taken from the captains' budget.
- Commander variants: a view around a fixed headquarters point, a delayed global view (an
  information-boundary decision for the owner), a commander attached to a regiment that can be
  killed, a stronger model as commander with cheaper captains, and commander prompts that ask
  for direct orders compared with prompts that ask for intent.
- C's bounded channels (signals and couriers) with the link filter, so distance and rendezvous
  become part of the arm.
- Two levels of command (commander, wing leaders, captains) and partial links between captains.
- For stage 4, proposals from the methodology review for the owner: the score above as a primary
  with a Welch t interval (Fisher on wins has power 0.16 for 0% against 20% at 15 per arm), a fixed
  test order (O against P at 5% first, then R against P), and Boschloo's exact test in place of
  Fisher. Review: `runs/comm-build-20261108/method-review.json`.
- Other battles from the [coordination suite](benchmark.md#the-coordination-suite-suite-v1),
  larger armies, and allied armies in [native multiplayer](native-multiplayer.md).

## Questions for the owner

1. **What does "forced" mean?** Now: (a) is built and runs tonight. (a, recommended) The
   links are the only way to send messages, and every captain reply carries one or two; the
   commander is not forced. This is the most literal reading of "allowed (and forced)" and keeps
   forcing equal across arms. (b) Fixed links only, and captains may stay silent. Message volume
   is then left to the models. Unforced Haiku captains attached a message to 463 of 716 completed
   replies in the one model battle, but 435 of those were one-word signal codes, which these arms
   turn off, so how often unforced captains would write text is unknown and an arm could drift
   toward a silent team. (c) A time floor: each captain must send at least one message every 10
   battle seconds, enforced by the dispatcher. This gives less chatter than (a) but needs more
   code.
2. **Which arms go into the scored comparison?** Now: P, R and O are built; stage 4 waits for its
   own yes and cap. (a, recommended) P, R and O, 15 launches each (about $50 to $65, 6 to 8 game
   hours), with O and R each against P. R tests the links without a wider view and O with one. O
   against R is exploratory and also carries O's larger input and its captains' line about the
   commander. (b) P and O only, 20 each (about $43 to $56, 5 to 7 game hours). This is the
   comparison you asked for, with more power to resolve a true 0% against 30%: 0.76 at 20 launches
   and 5%, against 0.28 for option (a)'s 15 launches at Holm's first step of 2.5%. R would come
   later if O differs. (c) P and R only, 20 each (about $42 to $54, 5 to 7 game hours). This is
   the cheapest test of the links with the same team observations, best if the commander's view
   can wait, and it leaves "different information" untested.
3. **What may start after tonight?** Tonight's stages 0 to 3 ran under your go-ahead. (a,
   recommended) The offline build and checks, then the $0 probes and the v2 construction test in a
   window you name (about 3.5 to 5 game hours). The paid pilot and the scored comparison each wait
   for their own yes and cap. (b) v1 only, comparing how messages flow with no claim about results.
   This is the quickest look at forced messages in play, best if you doubt the study is worth a
   construction test, but it cannot show an effect on wins. (c) Design a new C variant first, with
   groups beyond each other's view or a threat only one group can see. This is best if you expect
   v2 to fail its test, since it skips about 4 game hours there, but it delays every live step and
   needs your decision on a hidden event.
