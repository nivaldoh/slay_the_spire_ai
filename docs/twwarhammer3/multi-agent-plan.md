# Evaluating WH3 as a multi-agent problem

Proposed plan, 2026-10-21, revised the same day after review. The first question is whether
independently acting teammates command a battle better, more cheaply or more reliably than
one controller with comparable resources. The eventual question is whether factions can
cooperate and compete over a multiplayer campaign, where battles, diplomacy and earlier
commitments change which later decisions are possible.

Status 2026-10-27: the [starting-set screen](log.md#2026-10-22-the-starting-set-screen)
parked the rank-5 line that §9 B and §12 name as the first card, and the owner made team
work a later arm on the Land Battle benchmark ([direction](../owner-direction.md)). The
Land Battle replaces §9 B's card; §9 C's structure screen and §12 decision 1 wait for that
battle's first team-vs-single result.

Start with two agents commanding separate groups of one army against the game AI. Then take
single-client steps (an allied AI army, model against model), then native allied armies and
2v2, then campaigns. Native multiplayer is deferred: there is no second machine for now
(owner, 2026-10-21). Each stage is its own claim: a split-army result says nothing about
native multiplayer or campaigns.

Status: a proposal. Of the checks below, only the scripted split-army team's are agreed
([AGENTS.md](../../AGENTS.md#verification-hard-rule)); no scoring, counts, spending or game
sessions are adopted. The [implementation page](multi-agent-implementation.md) describes the
team as built and its next code. The [evaluation guidelines](evaluation-guidelines.md) apply
throughout, and this page adds only what teams change. The options for who commands which
units (per class, per unit, planner-made groups) are in [team
structures](team-structures.md). Related designs: the [robot-team plan](robot-team-plan.md)
(recovery inside one controller), a specialist that owns fixed units ([controllers.md item
4](controllers.md#designs-not-built-yet)), a planner over a fast executor ([latency rung
5](latency.md#harnesses)) and model against model on one client (owner idea, 2026-10-14,
[benchmark.md](benchmark-implementation.md#later)).

## 1 Questions and claims

An agent has its own observations, memory within the episode, decision process and authority
to issue actions. Sharing model weights does not merge two agents; sharing all private
memory and choosing all actions centrally does. Several model calls advising one decision
maker are a controller architecture, not decentralized execution. Game-controlled soldiers
and pathfinding are the environment, not evaluated agents.

| Question | Comparison that could answer it | What a win alone cannot establish |
|---|---|---|
| Does division of control help? | One controller against two independent agents: same units, information, helpers and total budget | That the gain comes from coordination rather than parallel calls or shorter prompts |
| Does communication help? | The same two agents with and without the message channel | That messages are truthful, necessary or the cause of a particular maneuver |
| Can an agent work with an unfamiliar teammate? | Frozen agents paired with partners withheld from development, in both roles | That two copies of one jointly tuned controller generalize to new partners |
| Can the team recover? | Fixed roles and simple recovery rules against adaptive assignment, on cases with useful alternatives; the [robot-team plan](robot-team-plan.md#1-establish-a-recoverable-coordination-problem) first checks that such cases occur | That a rout created a recoverable situation or a replacement order restored protection |
| Can a team adapt to an opponent? | A frozen population of opposing teams, with held-out opponents and side swaps | That beating the built-in AI transfers to model opponents |
| Can factions cooperate over time? | Campaign policies with declared objectives and partner variations, battle resolution held fixed | That territorial growth reflects cooperation or that promises caused compliance |

Keep these claims separate. A useful first result can be negative: a simple coordinated
script matching a model team, or messages costing more time than they save. The project's
[survey](../spire/approaches.md#7-multi-agent-systems-and-swarms-breadth-helps-depth-does-not)
found that every multi-agent variant hurt a sequential planning task by 39-70%, while
centralized coordination helped a parallelizable one by 80.9%. A split army acts in parallel
but has no central coordinator, so neither result is assumed.

## 2 Starting point

Source audit at `c2a7ae7`, before the team was built:

| Area | Boundary at `c2a7ae7` | Needed |
|---|---|---|
| Game access | The battle mod's `load()` refuses multiplayer, replay, campaign, quest and tutorial battles | A separately gated path with an agreed live check; deleting the guard is not enough |
| Army enumeration | `scan()` registers only the local alliance's first army, but its reinforcement loop has no such filter; state is friendly against enemy | Alliance, army, player and agent ownership; allied units without action authority |
| Controllers | Comma-separated policies rotate over episodes; `commander` is one planner over a skills executor | Several independent agents in one episode, with separate histories |
| Observations | One alliance's view, friendly state and the custom-battle enemy roster; one army and magic context | A per-agent information contract and resource ownership; campaign disclosure |
| Transport | One battle mailbox with one request in flight | Requests from several agents that cannot overwrite each other, each traceable to its agent |
| Evaluation | Engine outcome and card measures for one controlled side | One team outcome, per-agent reliability, opponent identity and client agreement |
| Campaign | No campaign policy loop | Read-only state, legal actions, turn and battle transitions, save/reload and multiplayer sync |

Since `45fe7b0`, `team.py` covers the controller and transport rows for a scripted split
army: two members, one mailbox writer, one member batch per request and per-member events.
Sources: [battle Lua](../../src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua)
(`load`, `scan`, `visible_to_player`, `observation`), [play
loop](../../src/twwarhammer3/battle/play.py),
[controllers](../../src/twwarhammer3/battle/controllers.py), [mailbox
contract](../../src/twwarhammer3/engine/mailbox.py) and [integration facts](integration.md).
Known boundary weaknesses (target and death fields, unsandboxed outside controllers) are in
the [information
rule](evaluation-guidelines.md#45-give-controllers-only-listed-public-fields-and-test-by-changing-hidden-data);
a scored evaluation resolves them or states the restriction.

SEGA's [launch
FAQ](https://support.sega.com/hc/en-gb/articles/4417717186833-TOTAL-WAR-WARHAMMER-III-FAQ)
lists battles for 2-8 players, simultaneous-turn multiplayer campaigns (with their own
player limits), battle side selection and gifting units to teammates in campaign battles.
These are game features to probe; our mod cannot yet control them.

## 3 Environments and agent boundaries

| Stage | Agents and authority | Opponent | What it adds |
|---|---|---|---|
| Split army | Two agents own disjoint unit groups of one army, one client | Built-in AI | Division of control and communication, with an engineered ownership boundary |
| Allied AI army, one client | Agents also command an allied AI army's units, if the script can hold them | Built-in AI | Real army boundaries: which resources and morale effects are per army |
| Model against model, one client | The battle script drives both alliances, each side with its own view | Another evaluated team | Competition without multiplayer clients |
| Native allied armies | Two agents, each owning one allied player army | Fixed built-in AI armies | Team battles between players' armies |
| Native 2v2 | Four agents, one per player army, two teams | Frozen opposing teams | Cooperation within and competition between teams |
| Larger teams | Three or four agents per team, where the mode allows | Fixed population | Scaling after two agents are understood |
| Multiplayer campaign | One agent per player faction at first | Built-in factions, then evaluated factions | Persistent cooperation, competition and diplomacy |

Agent, army and client counts are different quantities; record each. The two single-client
stages need Lua work: `scan()` skips allied AI armies (none in our scenarios) and puts every
other alliance into `enemy` with no controller. The mod takes control of a non-player army's
units only briefly, to place them for custom deployment; holding them for a whole battle is
untested.

Use groups of units as the first agents, such as a holding group and a mobile group; one
agent per regiment is a later scaling experiment. Keep the total roster fixed when varying
the number of agents, since adding both agents and units measures a different change.

Fix ownership before deployment. A routed unit stays its owner's if it rallies. Dynamic
reassignment, gifting and commander replacement are separate conditions with explicit
transfer rules. Give every group a consequential choice: a team where one agent always waits
is a useful foil, not evidence that several decision makers are needed.

Default to the information a player gets through the declared structured interface; if
native teammates share alliance sight, keep that. A deliberately restricted local view is a
separate condition, never called native fog of war. Start with a common public battle view
and independent memory, which isolates coordination of actions; add private scouting only
after its collection and filtering have a live reference.

## 4 The battle execution contract

The game runs unpaused at 1x, and a slow teammate must not stop the game or delay another
teammate's ready order. One trusted session owner runs a simple dispatcher around
independent workers. Any tactical choice the dispatcher makes, such as picking the best
spell, is part of the controller and is disclosed ([guideline
1.2](evaluation-guidelines.md#12-the-controller-is-everything-that-acts-in-the-battle-identify-it-by-content)).

### Observations and authority

An observation names its battle, sequence and battle time, and, when a stage needs them, the
agent (from the first model member), alliance, army and client (native play) and an
ownership version (once transfers exist). It holds only that agent's allowlisted fields:
owned units, permitted allied state, visible enemies, legitimately known roster information,
public objectives, its resource pools and delivered messages. Remembered enemy positions
keep their time and are marked stale. Never pass on evaluator totals, unseen movement or
deaths, a teammate's private plans, another team's messages or campaign-wide rosters.

Each command is traceable to the observation and owned unit it acts on. Check authority when
an order is applied wherever the game allows (the mod's `apply_order` already rejects orders
for dead or routing units then). The scripted team checks ownership and a 5 s age at Python
dispatch and reports a late engine application as transport overage. A transfer or a new
battle invalidates old authority; IDs carry army and client namespaces and an episode key.
Reinforcements, summons, death, rout and rally need declared ownership rules before a
scenario uses them. In the pilot, shared army abilities and spending pools belong to one
named agent or stay out; probe which resources native armies actually share rather than
inventing a global pool, and later compare a fixed rule with negotiated allocation.

### Scheduling and failures

Each agent has at most one pending decision, sent when it completes, with no team-wide
barrier. One mailbox is fine if agents wait only for transport, not for each other's
inference; measure that wait. Standing orders continue while an agent thinks. Use a declared
stable tie rule, balance agent identities across trials and record the actual order; a
synchronous round-based team is a separate comparison that includes its waiting.

Declare the maximum reply age, queue size, order persistence, retries and the response to an
invalid or late reply. Default: reject stale or unauthorized commands with a reason, keep
existing legal orders and let the agent reconsider from a fresh snapshot. A dead worker gets
no silent intelligent replacement (failover is its own controller). Continue to an engine
outcome where possible, otherwise apply the failure rule.

At each episode boundary, reset memory, inboxes, pending actions and reservations; record
unfinished calls' cost and reject late replies. Only a named adaptation condition carries
partner information across episodes; record other carryover (provider caches, game state).
Timestamp publication, delivery, request start, reply, validation, dispatch, acknowledgement
and observed effect separately, in battle time for game events and a monotonic clock for
local durations. In native play, measure client clock offsets and never subtract unaligned
wall clocks; lag and synchronized stalls stay in the measurements.

### Communication

Explicit messages go through a logged channel with declared recipients, size, send rate,
queue limit, delivery time, expiry and whether delivery can happen while the recipient
thinks. A message reaches the recipient's next request; log delivery and first use
separately. Start with bounded text and a small optional structure (target, intended action,
intended time); fixed vocabularies can be compared later. Both arms have the same view and
executor, writing and reading messages count in the team's budget and time, and a supplied
message interpreter or task allocator is disclosed.

No-message means no explicit messages: agents can still read intentions from visible
movement and shared instructions, so record the conventions prompts provide. A communication
claim needs message removal, or declared delay or loss, with the same controller and budget;
removing the channel at inference differs from training without it.

### Isolation and evidence

Workers see only their own inputs, not evaluator files, other workers' memory or opponent
channels. Separate Python dictionaries are not a security boundary: use trusted, audited
controllers, and require process, file and network isolation before an open-submission or
adversarial benchmark. Keep the raw evidence plus one event stream keyed by session, team,
agent, request and message (ownership changes, messages, rejections, resource decisions,
order origins, costs). Record versions and hashes of every agent, prompt, helper, backend,
scenario, engine and scorer, since the team adapter's class hash does not describe a model
team, and export per-agent trajectories with the joint episode mapping. Privileged data for
a central critic, if allowed later, stays marked and apart from execution inputs.

## 5 Tasks that make cooperation measurable

Freeze rosters, ranks, loadouts, deployment, funds, unit size, difficulty, map, timer,
sides, ownership and opponent, and change only named variables. Roster drafting and dynamic
deployment are later tasks that must not give one arm a hidden pre-battle advantage.
Domination, survival and sieges are later conditions with their own rules, not pooled with
the first land battles.

| Candidate | What teammates must coordinate | Alternatives and failure cases | Evidence to inspect |
|---|---|---|---|
| Hold and flank | One group fixes a threat while the other attacks an exposed side or waits | Both rush independently; the flank commits before support; a fixed timed flank succeeds without messages | Order timing, actual contact and separation, team outcome; do not infer a charge bonus from a move order |
| Two simultaneous threats | Groups divide attention between threats competing for the same support | Both chase one threat; fixed left/right roles; prioritize one and accept the other | Which threats were seen, the commitments and the outcome |
| Protect and relocate | One group protects ranged units while the other covers a threatened lane or withdrawal | Fixed roles; commit the reserve early; move the guns; abandon a lost position | Exposure, replacement arrival or completed withdrawal, unknown when recordings cannot decide |
| Joint resource choice | Agents coordinate scarce abilities, reinforcements or spending where actually shared | A fixed designated spender; first valid request; scripted reservation | Legal resource transitions and their effect, not just duplicate requests avoided |
| Information sharing | A scout sees a consequential threat before a teammate can | A robust fixed plan works without scouting; information arrives too late | The sender's legitimate observation, message use and the receiver's action, under a verified visibility contract |

The proposed first candidate (§12, decision 2) is the rank-5 line (`emp-line-grn-raid-xp5`,
seven units keeping their jobs), split as the Knights against the line and guns: a
hold-and-flank and two-threats case already in the [starting
set](tactic-cards.md#the-starting-set-proposal-2026-10-21). Not first: Knights/Swordsmen has
two units, so one call already orders both (it stays for offline and setup checks; hammer
and anvil is parked). Protect-and-relocate waits for the robot-team plan: a replacement
opportunity appeared in only 1 of 17 recorded line battles, and Bodyguard's 5/8 Helblaster
wins all ended with the gun at 0 crew, so a contact win does not test protection. Do not
discard trials without a disruption after seeing the outcome; earlier choices affect whether
one happens.

A team card meets the [five-part card
rule](tactic-cards.md#the-starting-set-proposal-2026-10-21) plus one team foil: a timed or
fixed-assignment script that never responds to its teammate, to see whether the battle can
be won without coordinating.
[SMACv2](https://proceedings.neurips.cc/paper_files/paper/2023/hash/764c18ad230f9e7bf6a77ffc2312c55e-Abstract-Datasets_and_Benchmarks.html)
found open-loop policies did well on many original SMAC scenarios. Reserve map, role, roster
and opponent variations before tuning
([3.1](evaluation-guidelines.md#31-mark-each-jobs-stage-and-tune-only-on-development-evidence),
[3.2](evaluation-guidelines.md#32-reserve-held-out-variants-before-tuning-and-say-what-was-held-out));
a configuration seed is not proof of a seeded engine or deterministic reset.

## 6 Controllers and comparisons

All arms use the same legal orders and comparable disclosed local execution. Parameterize
one executor where possible, so that changing the planner does not also improve targeting.

| Arm | Decision process | Purpose |
|---|---|---|
| Coordinated script | Fixed roles with a small declared conditional plan, such as `LineTeam` on the line | Strong cheap reference and witness |
| Independent simple scripts | Each group follows its own local rule | Whether coordination beyond local competence is useful |
| Single controller | One policy controls every permitted unit (`llm_rules`; `commander` if kept) | Whether dividing decisions is worthwhile |
| Two agents without messages | Separate policies, histories and owned units | Division of control and implicit coordination |
| Two agents with messages | The same, with the bounded channel | Explicit communication benefit |
| Hierarchical team, later | One planner delegates; workers act under named authority ([latency rung 5](latency.md#harnesses)) | Hierarchy, once independent execution works |

Compare complete systems first: each architecture at its natural concurrency, with success,
dollars, calls and elapsed time side by side. Architecture claims need equal total team
resources: the same model and backend, information, total call, token or dollar cap,
action-rate cap, helpers and maximum concurrent requests, counting communication and
coordinator calls and showing actual use. A central controller may get a parallel-call
helper with the same total resources, under its own identity, to test whether the benefit is
only parallel inference. The natural split uses at least as many resources, so run the
equal-budget and helper arms only if the split wins. A central policy is a reference, not an
upper bound. Artificial delay studies are named separately and delay only the intended
channel.

After the first comparison, freeze a small partner population: a fixed-role script, a
reactive script and separately developed model controllers. Evaluate a focal agent in both
roles with each partner, including pairs withheld from tuning. First-episode results test
unfamiliar partners; a permitted adaptation sequence tests learning a partner (reset memory
in the former, log it in the latter). Two clones of one model are not evidence of broad
compatibility: [Other-Play](https://proceedings.mlr.press/v119/hu20a.html) shows conventions
learned together can fail with new partners.

Against opponents, freeze their versions and evaluate a matchup matrix with team and side
swaps, with built-in AI references where legal. Never update an opponent during scoring or
adapt from its private state. Report matchups directly: a single rating can hide cycles
where A beats B, B beats C and C beats A. Results against a small pool show strength against
that pool, not against unseen opponents.

## 7 Outcomes and statistics

The primary observation is one team outcome per match; both agents winning is not two wins.
Keep the engine's result and ending reason, apply the card's declared rule and tell every
agent that rule. A valid engine ending survives later worker or logging errors.

Secondary measures explain an outcome; they do not replace it with a cooperation score. Each
has a written event definition and an unknown category:
- Coordination: duplicate commitments, conflicting orders, abandoned responsibilities,
  completed joint actions and successful or failed recoveries (a purposeful retreat can be a
  success).
- Communication: messages sent, delivered and available to a decision, useful response
  delay, tokens and cost. More messages or agreeable text are not better teamwork.
- Timing: per-agent order age at application, time between useful orders, transport wait,
  model latency, executor cadence and battle-to-wall-time ratio. For a team these come from
  member feedback events; the outer loop's delay and decision count measure dispatcher polls
  (0.3 s in the scripted probes, against member ages up to 3.9 s).
- Reliability: invalid, stale or unauthorized orders, worker and provider failures,
  desynchronization and unfinished matches, with per-agent and team denominators.
- Efficiency: team cost per attempted match and per success (undefined at zero successes),
  with each agent's share as a diagnostic.

Individual kills, damage and survival are not rewards: a holding unit can make the winning
contribution while losing most of its men. Estimate contribution only by predeclared policy
substitutions under matched conditions; that gives the effect of replacing a policy in that
team, not an agent's intrinsic value.

Plan one primary comparison at a time. Freeze arms, sample size, minimum useful effect,
analysis and stop rule before confirmation, sized from pilot variability
([7](evaluation-guidelines.md#7-use-statistics-that-fit-small-live-studies),
[7.4](evaluation-guidelines.md#74-decide-before-you-look)). Count fresh launches with their
rematches and interleave arms in balanced time blocks
([4.1](evaluation-guidelines.md#41-count-launches-not-rematches),
[4.2](evaluation-guidelines.md#42-balance-who-plays-first-and-when)); a build or mod change
starts a new condition. What teams add: native clients in one session are one sample, so
define the sample unit again for the native runner; side swaps stay paired within their
session; a suite average needs fixed weights and uncertainty that respects repeated partners
and shared scenarios.

Every planned trial gets one disposition
([5.3](evaluation-guidelines.md#53-give-every-planned-trial-one-visible-disposition)). What
teams add: controller slowness or a bad teammate is team performance, not an exclusion; a
worker failure that leaves the match running keeps the eventual outcome with a flag; missing
or conflicting client results stay unresolved and are never inferred from a client's
silence. The failure rule is agreed
([benchmark.md](benchmark-implementation.md#correctness-checks-to-agree)); these team cases are proposed
additions, to be agreed before the evaluator implements it.

## 8 Verification before evaluation

Each row is a repeatable check with an independent reference and the wrong behavior it must
catch. A check counts only once the owner agrees it and it passes at a named revision.

| Capability | Check and reference | Wrong behavior it must catch | Status |
|---|---|---|---|
| Ownership and identity | Two visibly distinct groups receive opposite commands; compare declared ownership, game/UI readback and observed movement. Repeat with swapped identities, rout/rally and a fresh episode | Agent A controls B's unit, or an old request controls a newly reused ID | Partly covered: the scripted-team check at `45fe7b0` (binding by type, correct-unit orders and movement, 4 launches); opposite commands, swaps, UI readback, rout/rally and ID reuse not covered |
| Information boundary | Change only hidden state and private messages in component inputs; emitted policy inputs must be unchanged. In game, compare a revealed and a hidden enemy against each client's view | Hidden coordinates, death, target identity, another team's message or a new unlisted field leaks | Component filtering agreed, passed at `e8d1eda`; in-game comparison proposed |
| Concurrent scheduling | A fast scripted worker and a delayed worker act in the same 1x battle; check independent dispatch and observed motion. Swap identities and delay the other worker | The slowest worker becomes a team barrier, mailbox overwrite, duplicate execution or fixed identity priority | Agreed for scripted members: component checks passed at `e8d1eda` (with oldest-first selection), live at `45fe7b0` |
| Message delivery | Send numbered messages with declared expiry, delay and drop; compare sender, router and recipient-input records | A dropped message arrives, an expired message looks current, or a message reaches the wrong team | Proposed |
| Shared resources | Issue conflicting legal requests for one real pool; compare independent game/UI before and after values and effects | Double spending, the wrong army charged or a hidden tactical arbiter | Proposed |
| Reset and scoring | Known win, loss, timer and draw cases where the mode permits them; swapped sides; changed rematch; failure before and after the ending. Compare engine/UI and all client logs | A surviving unit mistaken for team victory, a failure erasing a win, or a client counted as another match | Component ending and cleanup agreed for the team; the rest proposed |
| Native multiplayer | Identical declared builds and mods, two real clients first; one local order on each, observed on both; repeated fresh sessions and role/host swaps | Host-only control, divergent simulation, missing allied armies or duplicate script effects | Proposed |
| Campaign transition | Save and reload a known state, perform one legal action, end a turn and enter and leave a battle; compare semantic fields and game UI on each client | Duplicate action, stale legal action, lost ownership, wrong treasury or turn, or a wrong battle result applied | Proposed |

Use cheap component cases first, then a bounded script-only live probe of the named
behavior, with enough repeats to exercise the failure. A deliberately broken filter or
router, or a known bad recording, must make the check fail. Human review uses agreed
success, failure and ambiguous examples, hidden controller labels and a fixed sample. A
teammate saying "flank complete" is a claim to check against game events, and LLM reviews
are
[leads](evaluation-guidelines.md#83-controller-text-and-llm-reviews-are-leads-not-evidence).

## 9 Stages

### A Feasibility: scripted ownership and scheduling checked

The ownership, scheduling, feedback and cleanup checks passed for two scripted members
(component at `e8d1eda`, live at `45fe7b0`) ([implementation
page](multi-agent-implementation.md#checks)). Still open: the in-game visibility comparison,
and an inventory of the actions the chosen card needs from the installed scripting
references (do not widen the API just because methods exist). Stop before scoring if control
crosses ownership, hidden state leaks, one worker's inference blocks another or the game
cannot keep the required timing.

### B Choose the card

Proposed (§12, decision 2): use the tactic-card process rather than a separate team screen.
On the rank-5 line, the agreed starting-set screen runs the floors and the `LineTeam`
witness (12 of its 39 launches); the card is chosen from it. Before any confirmation, the
card's named shortcut (`LineTeam` with the Knights held back, the not-yet-planned shortcut
screen) and the §5 team foil (a script whose groups never respond to each other, not yet
written) must also lose. Advance when legal joint action changes the outcome and the
evidence separates the intended coordination from the strongest simple alternative. Do not
tune difficulty until the models all fail; confirmation uses fresh evidence after the card
and its rule are frozen.

### C First comparison

Revised 2026-10-21: first a screen across team structures (the single controller, two
members, one per class, one per unit and planner-made groups, three launches each, about
$10), then a 6 + 6 pilot of at most one structure; see [team
structures](team-structures.md#6-stages). Reserve a held-out variant of the card before the
screen, as the tactic-card process does before a model screen; the pilot keeps the rules
below. Pilot on one card: a single `llm_rules` controller against the chosen structure,
without messages. Six fresh launches per arm, interleaved in one night, plus a few
same-night witness launches. Declare the stop rule first: if the split wins no more battles
than the single controller, report "no benefit observed at n=6 per arm" and size no
confirmation of divided control; otherwise freeze an unfamiliar partner and size a
confirmation for a named effect. Rough cost: about $7 when the chosen structure runs
round-robin (about one controller's calls; $0.58 on the one GLM-5.3 low rank-5 row) and
$10-14 at natural concurrency, and 2.5-3 hours (the line's two rank-5 model launches took
about 10 and 13 minutes). A message arm follows only if the split is at least even or loses
through visible coordination failures; the helper arm only if it wins (§6). Stop expanding
if the interface or scenario, rather than a controller choice, explains most failures.

### D Single-client steps

Before multiplayer clients, and under the one-controller rule: a custom battle with one
allied AI army, probing whether the script can keep control of its units for a whole battle
and which resources (winds of magic, army abilities, commander morale) are per army; then
model against model, with the battle script driving both alliances, each with its own view.

**The owner as the opponent** (owner request, 2026-10-22; manual testing, never a benchmark
row; parked by the owner the same day, to implement later from step 1). The owner plays the player's army with mouse and keyboard and their own camera; the
controllers command the AI's army through a session switch (`control: "enemy"`, branch
`wh3-human-opponent`). This shares model against model's prerequisite: holding a non-player
army and building its view. The $0 probe ([log](log.md#2026-10-22-the-script-commands-the-ais-army))
showed control through one whole battle but a 3.6 s start gap. Next, each step after the
one before it:
1. Take the AI's units over before its opening order, then repeat both probe arms (hold:
   every unit within 5 m for 120 s; attack: an engine result matching the final counts).
2. Give the controllers their own army's abilities, magic, reinforcements, supplies and
   build slots, or refuse such battles in this mode; refuse custom objectives at first.
3. A `play` option for the human seat: the switch, no autostart (the owner presses Start),
   no `--show` or stills, the side-swapped setup check, and register rows labelled with the
   human opponent and kept out of `stats`, `card` and `report`.
4. The owner's first battles against scripted controllers: they command every unit, a
   battle they win reads `lost`, and a unit hidden in woods stays out of the controllers'
   observation. Then model controllers through OpenRouter.

Proposed checks (not agreed): the step 1 probe and the step 4 battle.

### E Native team battles

Deferred: there is no second machine for now (owner, 2026-10-21), so this stage and the
campaign stages with two player factions wait; the single-client steps (§9 D) and
single-faction campaign stages do not. Native multiplayer is required for any
native-multiplayer claim. When a second machine exists, first inventory licensed clients,
accounts, content and compatible builds. Find out whether permitted game-side commands are
synchronized by the engine; client-local file polling or Lua callbacks need not produce
identical effects. The community mirror of CA's [UI scripting
documentation](https://chadvandy.github.io/tw_modding_resources/WH3/ui_scripting.html) warns
that changing game state from client-specific UI events can desynchronize a match, and its
[CampaignUI
reference](https://chadvandy.github.io/tw_modding_resources/WH3/campaign/campaignui.html)
documents a script event sent to all clients, a candidate to inspect. The probe separates
local UI actions from replicated game actions. Never replace missing support with one
omniscient host and call it equivalent.

Order: two clients with one tiny interaction, then allied player armies against fixed AI,
then four player slots for 2v2, each step with ownership, visibility, outcome and
synchronization checks. Freeze army resources, reinforcements, deployment and disconnect
handling; swap roles, host and sides; grow the opponent matrix only after whole sessions can
be recounted and rerun. The one-controller rule then needs a revised arrangement: one
supervised session with child clients, per-client bridges and coordinated cleanup. Nothing
here authorizes concurrent launches or buying accounts or hardware. If engine control fails,
record why, estimate a player-UI adapter and keep the split-army findings under their own
name.

### F Campaigns

Follow §10. Deliver a small reproducible multiplayer campaign task before a full-campaign
comparison; both stay in scope.

## 10 Multiplayer campaign evaluation

A campaign is a game between factions with partly shared interests and lasting consequences.
Fixed allies with a shared objective share one team result; independent factions keep their
own objectives and outcomes, never collapsed into one cooperative reward. The questions
include resource aid, dividing fronts, coordinating reinforcements, negotiating commitments,
responding to an ally's loss and deciding when cooperation stops paying. The first campaign
agent controls one faction; splitting economy, diplomacy and battles among specialists
inside a faction is a later architecture comparison.

| Stage | Task and fixed conditions | Completion evidence |
|---|---|---|
| Read-only access and lifecycle | One chosen campaign and faction; inspect player-visible state, save/reload and loader behavior | Semantic readbacks match the UI; no hidden-faction leakage; instrumentation stays inactive outside its explicit session |
| One-faction action loop | Narrow legal actions, one turn boundary, one battle transition; scripted controller | Actions affect the intended faction once; stale or illegal requests are rejected; outcome and return to the map agree |
| Two allied player factions | A short cooperative objective from a declared starting state; built-in opposition | Both real clients act, complete turns, resolve battles and reload consistently; the shared victory/defeat rule is explicit |
| Bounded strategic tasks | Fixed turn horizon, several starts and roles, frozen battle resolver | Recountable objective results, compared with strong simple faction scripts |
| Mixed interests | Independent objectives, negotiation and changing alliances where the campaign permits them | Per-faction outcomes and recorded commitments and actions; no shared private state or hidden objective leakage |
| Full multiplayer campaigns | Frozen campaign, factions, victory rules, crisis/endgame settings, turn and real-time caps and partner/opponent population | Complete campaign outcomes or explicitly censored attempts, with every interruption and budget accounted for |

Example bounded tasks: two allied factions protect a vulnerable settlement while preparing a
joint attack, reinforce an ally without losing their own frontier, or make an affordable
transfer that enables a shared objective. Choose starts from the actual campaign with a
disclosed setup and readable game objectives; use several strategic situations rather than
dozens of branches from one favorable save, and create saves only when a test needs them.

### Information and legal actions

A campaign view lists what is known about settlements, armies, treasury, income,
recruitment, movement, diplomacy, treaties, objectives and messages. A script that can query
every faction is not permission to show it; remembered information carries its turn, and
unseen armies and enemy finances stay hidden unless a game mechanic exposes them. Actions
come from the faction's legal choices (movement, recruitment, buildings and research,
diplomacy, ending the turn), starting with what the first task needs, and are rechecked
(target, cost, prerequisites, state version) when applied. Record proposal, acceptance and
effect separately: a promise of aid is not a transfer, and a treaty the game accepts differs
from an unenforced promise.

Simultaneous turns make ordering matter. Probe which actions are allowed while another
player moves, negotiates or fights, rather than inventing a serial turn loop and calling it
native (a deliberately serialized condition is labelled). Record conflicts, rejected stale
actions, turn locks and battle interruptions; declare a per-turn wall budget, timeout
behavior and a disposition for a player that never ends its turn. Tactical battles stay at
1x.

### Separating campaign decisions from battle skill

A strategic track holds battle resolution fixed for every agent: the same tactical
controller and settings, or a declared auto-resolve rule. Auto-resolve favors some rosters,
so those results concern strategy under that resolver, and no policy may fight by hand only
the battles it would lose on auto-resolve unless every policy may. An end-to-end track lets
faction agents invoke their battle team under a common contract: armies, reinforcements and
gifted units map to battle ownership, casualties map back, and authority is rechecked after
every transfer. Report strategic and tactical failures separately, and credit one for the
other only through a controlled substitution.

### Campaign outcomes and social behavior

The primary result is a named cooperative objective completed by turn H (reaching H without
it is non-success), or engine-confirmed victory in a full campaign. A campaign stopped at an
administrative cap has an unknown victory time (it is censored), so also report success by
the cap with unfinished campaigns in the denominator. Controller failures, refusing to end a
turn and controller-caused budget or time exhaustion follow the failure rule, not harmless
censoring. Report completion, defeat, failure and censored counts with turns and wall time.
Territory, income, army value and ally survival are diagnostics, frozen before a comparison.

With mixed interests, show each faction's result across partners, opponents and starting
roles, and record offers, acceptances, actual transfers, joint operations and broken
promises with their conditions. Negotiation quality is not eloquence or friendliness, and
declining an unfavorable deal need not be failure. Test dependence on communication and
partners with interventions and partner swaps; hold out partner policies and strategic
starts as well as maps and factions, as [Melting Pot](https://arxiv.org/abs/2107.06857) does
for social situations.

The sample unit is a campaign start or session, not a turn, army or battle. Branches of one
save share history and are grouped or paired, and reloading a save does not prove a
deterministic continuation. Record provenance, turn, semantic state, RNG availability, agent
memory, build and mod hashes and restore behavior. Resuming an interrupted trial differs
from retrying a decision; no selective rollback after bad moves.

### Campaign access conditions

Before any campaign launch: the owner's decisions on harness-created saves and irreversible
Steam achievements ([state](../state.md#owner-decisions-waiting), [campaign
rules](../autonomy.md#wh3-campaign-infrastructure)); a dedicated test profile or save
namespace if supported, with existing saves protected; and loaders checked in campaign and
campaign-battle contexts. Because of the shared imagery loader issue
([integration](integration.md#packs-and-loading)), the battle guard alone does not make the
mod inert in campaigns.

## 11 Cost and implementation boundaries

Native clients need their own bridge directories and identities; campaign state and actions
get their own contract in `twwarhammer3` rather than overloading battle unit orders.

Estimate resources from measured pilots:
- Game hours: planned sessions times measured setup, battle and recovery time, plus a
  bounded feasibility allowance; single-client throughput does not predict multi-client or
  campaign throughput.
- Model cost: every agent's calls, messages, coordination, retries and memory work, under a
  team cap and a study cap. Concurrent workers need real shared reservations (the ledger
  hold on the [implementation page](multi-agent-implementation.md#what-teampy-does)).
- Native hosting: client count, licenses and content, machine and network capacity; measure
  lag with the intended client count.
- Human time: agreeing checks, fixed-sample review, resolving disagreements and independent
  recount and rerun.

No new spending is adopted. The shared ledgers and caps apply, and the near-exhausted OpenAI
allowance is no basis for scheduling a paid study. Freeze a bounded job plan once costs are
known, and stop between sessions before a cap rather than leaving the expensive arm
unfinished. A campaign needs a resume policy and budget for its declared horizon. Releases
follow guidelines
[9.3](evaluation-guidelines.md#93-offer-outside-checks-in-three-steps-and-claim-only-what-each-shows)
and [9.4](evaluation-guidelines.md#94-publish-a-short-summary-page-and-a-clean-bundle),
adding per-agent traces and the joint mapping; share code and permitted derived evidence,
never game packs or campaign saves.

## 12 Decisions for the owner

1. The first model comparison (§9 C): a structure screen, then a 6 + 6 of at most one
   structure against a single `llm_rules` controller, after the starting-set screen ([team
   structures](team-structures.md)). Messages and helper arms depend on its result.
2. No separate team card screen (§9 B; the structure screen of §9 C is not one): the card
   comes from the starting-set screen, and its named shortcut and the team foil must lose
   before confirmation; protect-and-relocate and Knights/Swordsmen are not first cards.
3. The live witness change on the [implementation
   page](multi-agent-implementation.md#checks): require the fast unit to be idle before its
   order (recount only, no game time).
4. Settled (owner, 2026-10-21): no second machine for now, so native stages are deferred and
   the single-client steps (§9 D) come first.
5. Native multiplayer setup and the campaign lifecycle remain capability gates. Use a
   provisional campaign and faction for access probes, choose the evaluation campaign and
   factions from that evidence, and freeze a short cooperative task before mixed-interest
   and full campaigns.

Until the starting-set screen has run, the team needs no new code.
