# Evaluating WH3 as a multi-agent problem

Proposed plan, 2026-10-21. The first question is whether independently acting teammates
can coordinate a battle better, more cheaply, or more reliably than a single controller
given comparable resources. The eventual question is whether factions can cooperate and
compete over a multiplayer campaign, where battles, diplomacy and earlier commitments
change what later decisions are possible.

Start with two agents commanding separate groups in one army against the game AI. This
is a controlled development environment for team battles. Then establish native allied
armies and native 2v2 play as separate milestones. A split-army result does not establish
multiplayer support. Campaign evaluation follows a further set of gates; it is part of
this plan, rather than an assumed consequence of getting custom battles working.

The requested deliverable is a plan. The designs, counts and checks below are proposals,
not adopted benchmark rules or authorization for game runs. No new method is an agreed
verification method under [AGENTS.md](../../AGENTS.md#verification-hard-rule).
The existing [battle benchmark](benchmark.md#scope-and-first-release) keeps its scope.
This extension reuses its [evaluation guidelines](evaluation-guidelines.md) and the
[robot-team plan](robot-team-plan.md) where their assumptions apply.
The [implementation plan](multi-agent-implementation.md) turns the first stage into
small coding slices, beginning with ownership and dispatch for two scripted members.

## 1 Questions and claims

An agent has its own observations, persistent state during the episode, decision process
and authority to issue actions. Sharing model weights does not merge two agents; sharing
all their private memory and choosing all their actions centrally does. Several model
calls advising one final decision maker are a controller architecture, not evidence of
decentralized execution. Game-controlled soldiers and pathfinding are the environment's
local execution, not additional evaluated agents.

| Question | Comparison that could answer it | What a win alone cannot establish |
|---|---|---|
| Does division of control help? | One commander versus two independent commanders, same units, information regime, helpers and total budget | That the gain comes from coordination rather than parallel calls or shorter prompts |
| Does communication help? | The same two agents with and without the explicit message channel | That messages are truthful, necessary, or the cause of a particular maneuver |
| Can an agent work with an unfamiliar teammate? | Frozen agents paired with partners withheld from development, in both roles | That two copies of one jointly tuned controller generalize to new partners |
| Can the team recover? | Fixed roles and simple recovery rules versus adaptive assignment, on cases with useful alternatives | That a rout created a recoverable situation or a replacement order restored protection |
| Can a team adapt to an opponent? | A frozen population of opposing teams, with held-out opponents and side swaps | That beating the built-in AI transfers to model opponents |
| Can factions cooperate over time? | Campaign policies with declared objectives and partner variations, controlling tactical battle resolution | That territorial growth reflects cooperation or that promises caused compliance |

Keep these claims separate. A useful first result can be that a simple coordinated script
matches a model team, or that communication costs more time than it saves. WH3's potential
value is the combination of heterogeneous units, formation and morale dependencies,
continued execution during inference, and eventually persistent strategic consequences.
It is not established as uniquely difficult, a robotics benchmark, or a measure of general
intelligence.

## 2 What the current project actually supports

Code inspection at `c2a7ae7` gives the following starting point. These are implementation
facts, not new live verification results.

| Area | Current boundary | Needed for this plan |
|---|---|---|
| Game access | The battle mod's `load()` refuses multiplayer and campaign battles | A separately gated path with an agreed live check; deleting the guard is insufficient |
| Army enumeration | `scan()` initially skips other armies in the local alliance; its separate reinforcement loop lacks that filter. State is organized as friendly versus enemy | Explicit alliance, army, player and agent ownership; allied units without action authority |
| Controllers | Comma-separated policies rotate over episodes; `commander` is one planner over a skills executor | Concurrent independent agents in one episode, with separate histories and queues |
| Observations | One player's alliance visibility, friendly state and custom-battle enemy roster; one army/magic context | A per-agent information contract and resource ownership; campaign-specific disclosure |
| Transport | One battle mailbox and one policy action/acknowledgement loop | Multiplexed requests that cannot overwrite each other, with per-agent provenance |
| Evaluation | Engine outcome and existing card measures for one controlled side | One team outcome, per-agent reliability, opponent identity and client agreement |
| Campaign | No campaign policy loop in the WH3 package | Read-only state, legal actions, turn and battle transitions, save/reload and multiplayer synchronization |

References: [battle Lua](../../src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua)
(`load`, `scan`, `visible_to_player`, `observation`),
[play loop](../../src/twwarhammer3/battle/play.py),
[controllers](../../src/twwarhammer3/battle/controllers.py),
[mailbox contract](../../src/twwarhammer3/engine/mailbox.py) and
[integration facts](integration.md).
Current boundary weaknesses, including target/death information and unsandboxed outside
controllers, are recorded in the [information rule](evaluation-guidelines.md#45-give-controllers-only-listed-public-fields-and-test-by-changing-hidden-data).
They must be resolved or explicitly restrict the affected evaluation before it is scored.

SEGA's launch FAQ documents battle scenarios for 2–8 players and multiplayer campaigns
with simultaneous turns, with campaign-specific player limits. It also describes battle
side selection and gifting units to teammates during campaign battles. This establishes
a game feature to investigate, not control through our mod on the installed build.
[SEGA FAQ](https://support.sega.com/hc/en-gb/articles/4417717186833-TOTAL-WAR-WARHAMMER-III-FAQ).

## 3 Environments and agent boundaries

Keep the following conditions separately named in manifests and results. Agent count,
army count and client count are different quantities.

| Stage | Evaluated agents and authority | Opponent | Interpretation |
|---|---|---|---|
| Split army | Two agents own disjoint unit groups in one army on one client | Built-in AI | Division of control and communication; engineered ownership boundary |
| Native allied armies | Two agents each own one allied player army | Fixed built-in AI armies | Team battles with real army boundaries and their resource/morale effects |
| Native 2v2 | Four agents, one per player army, two teams | Frozen opposing agent teams | Cooperation within each team and competition between teams |
| Larger teams | Three or four agents per team, only where the mode supports it | Fixed population | Scaling after a two-agent mechanism is understood |
| Multiplayer campaign | One agent per player faction initially | Built-in factions, then other evaluated factions | Persistent cooperation, competition and diplomacy |

Use groups of units as the initial battle agents: for example, a holding group and a
mobile support group. One agent per regiment is a later scaling experiment, not the
default; it adds inference work and many action conflicts before demonstrating a useful
coordination problem. At every scale keep the total roster fixed when testing the effect
of agent count. Adding both agents and units measures a different change.

For the split-army pilot, assign ownership before deployment and keep it fixed. A routed
unit remains its owner's unit if it rallies. Dynamic reassignment, gifting and commander
replacement are separate conditions with explicit transfer rules. Give every group a
consequential choice; a team where one agent always waits is a useful foil, not compelling
evidence that multiple decision makers are needed.

Default to the information a player would legitimately get under the declared structured
interface. If native teammates share alliance sight, preserve that behavior. A deliberately
restricted local view is an additional experimental condition; do not call it native fog
of war. Begin with a common public battle view and independent intentions/memory, which
isolates coordination of actions. Add private scouting information only after its
collection and filtering have a live reference.

## 4 The proposed battle execution contract

The game continues unpaused at 1x. A teammate's slow inference must not stop the game or
prevent another teammate's ready order from being sent. Use one trusted session owner
and a simple dispatcher around independent agent workers. The dispatcher checks authority,
records events and routes orders; any tactical choice it makes becomes a disclosed part
of the controller.

### Observations and authority

Each observation identifies the session, episode, agent, alliance, army, ownership version,
snapshot sequence and battle time. It contains only allowlisted fields for that agent:
owned units, permitted allied state, currently visible enemies, legitimately known roster
information, public objectives, relevant resource pools and messages actually delivered.
Remembered enemy positions retain their observation time and an explicit stale status.
Do not broadcast evaluator totals, unseen movement/deaths, private teammate plans, another
team's messages, or campaign-wide rosters from the raw game state.

Each command names the observation and owned entity it acts on. Validate authority at
application time, not just when inference begins. A later transfer or new battle must
invalidate the old authority. IDs need army/client namespaces and cannot be reused across
episodes without an episode key. Reinforcements, summons, death, rout and rally need
declared identity and ownership rules before a scenario using them is admitted.

For the pilot, make shared army abilities and spending pools the responsibility of one
named agent, or omit them from the first scenario. Do not invent a global magic pool
across native armies: probe which resources the game actually shares. Later, compare a
fixed shared-resource rule with negotiated allocation. A hidden dispatcher that picks
the best spell is extra intelligence and cannot masquerade as neutral plumbing.

### Scheduling and failures

Start with at most one pending decision per agent. On completion, validate and send its
orders without a team-wide reasoning barrier. Serializing writes through the existing
mailbox is acceptable if other agents need wait only for transport, not for inference;
measure that queue delay. An agent continues with its standing orders while thinking.
Use a declared stable tie rule for requests ready together, balance agent identities
across trials, and record the actual order. A synchronous team-round controller can be a
separate comparison, with its waiting cost included.

Specify maximum reply age, per-agent queue size, order persistence, retry policy and the
response to an invalid or late reply. Initial recommendation: reject stale/unauthorized
commands, keep existing legal orders, return a reason, and let the agent reconsider from
a fresh snapshot. Fixed executors may continue only their disclosed behavior. A dead
worker does not silently gain an intelligent replacement. Deliberate failover is its own
controller configuration. Continue to an engine outcome where possible; otherwise apply
the declared failure rule.

At every episode boundary, reset agent memory, message inboxes, pending actions and
ownership/resource reservations. Cancel or quarantine unfinished calls, record their cost,
and reject late replies or acknowledgements from the previous episode. Only a named
adaptation condition may carry learned partner information across episodes. Record other
carryover, including provider caches and game state; read back the new battle's setup.

Record observation publication, delivery, request start, reply completion, validation,
dispatch, game acknowledgement and observed effect separately. Use battle time for game
events and a monotonic clock for local durations. In native multiplayer, measure client
clock offsets and timestamp uncertainty; never subtract unaligned wall clocks as if they
were one clock. Network lag and synchronized stalls remain in performance measurements;
record battle-to-wall-time progress. The harness never requests a pause or slower speed.

### Communication

All explicit inter-agent communication goes through a logged channel. Specify recipients,
message size, send rate, queue limit, delivery time, expiry and whether delivery can occur
while a recipient is thinking. With the initial single pending request, newly arrived
messages enter its next request; the trace distinguishes transport delivery from when the
model could use the message. Do not claim immediate reaction to a delivered message.

Start with bounded text messages and a small optional structure such as target, intended
action and intended time. No-message and message-enabled arms have the same battle view
and executor. Message generation, reading, summaries and retries all consume the team's
budget and time. A supplied message interpreter or task allocator must be disclosed.
Natural-language and fixed-vocabulary channels can be compared later.

No-message means no explicit messages, not an absence of all communication: agents may
infer intentions from visible movement and shared pre-battle instructions. Record the
coordination conventions provided in prompts. For a communication claim, use message
removal or declared delay/loss with the same controller and budget; an unrelated stronger
controller is not a communication ablation. Distinguish removing the channel at inference
time from separately training an agent to operate without it.

### Isolation and evidence

Agent workers receive only their own inputs and cannot read the evaluator's files, other
workers' memory or opponent channels. Passing separate Python dictionaries is a useful
component boundary, but not a security boundary for arbitrary submitted code. Begin with
trusted audited controllers and state that restriction; require process/file/network
isolation before claiming an adversarial or open-submission benchmark.

Keep the existing raw game and terminal evidence, plus one event stream keyed by session,
team, agent, request and message. Log ownership changes, message contents and deliveries,
rejections, resource decisions, model/executor order origins and all costs. Record the
versions and hashes of every agent, prompt, helper, backend, scenario, engine and scorer.
Export per-agent trajectories and the joint episode mapping. Privileged training data,
if later permitted for a central critic, stays marked and separate from execution inputs.

## 5 Tasks that make cooperation measurable

Start with two small land-battle families, then expand only when each adds a distinct
decision.
Freeze rosters, ranks, loadouts, legal deployment, funds, unit size, difficulty, map,
timer, sides, ownership and opponent. Change only named variables in each comparison.
Roster drafting and dynamic deployment become separate later tasks; they must not give
one evaluation arm a hidden pre-battle advantage.
Domination, survival and sieges are later conditions with their own objectives, resource
rules and checks; do not pool them with the initial land battles.

| Candidate | What teammates must coordinate | Credible alternatives and failure cases | Evidence to inspect |
|---|---|---|---|
| Hold and flank | One group fixes a threat while the other attacks an exposed side or waits | Both rush independently; flank commits before support; a fixed timed flank succeeds without messages | Order timing, actual contact/separation and team outcome; do not infer a charge bonus from a move order |
| Protect and relocate | One group protects ranged units while the other covers a threatened lane or withdrawal | Fixed roles; commit reserve early; move the guns instead; abandon a lost position | Exposure, replacement arrival or completed withdrawal, with unknown when recordings cannot decide |
| Two simultaneous threats | Groups allocate attention between threats competing for the same support | Both chase the same threat; fixed left/right roles; prioritize one and accept the other | Which threats were observed, commitments and resulting objective/team outcome |
| Joint resource choice | Agents coordinate scarce abilities, reinforcements or spending where actually shared | Fixed designated spender; first valid request; scripted reservation | Legal resource transitions and effect, not just duplicate requests avoided |
| Information sharing | A scout sees a consequential threat before a teammate can see it | A robust fixed plan works without scouting; information arrives too late | Sender's legitimate observation, message use and receiver's action; only under a verified visibility contract |

Use the first two as candidates, not assumed valid cards. The existing Empire line can
inform protect-and-relocate design, but the earlier review found a plausible replacement
opportunity in only **1 of 17 recorded battles**, using its declared criteria; it does
not establish a ready recovery test. See the [review and caveats](robot-team-plan.md#1-establish-a-recoverable-coordination-problem).
Do not discard trials with no disruption after seeing the outcome: earlier policy choices
affect whether a disruption occurs.

Each card needs a successful disclosed joint policy, meaningful weaker alternatives and
an independent outcome rule. Include a timed or fixed-assignment script to check whether
the scenario can be solved without responding to teammates. SMACv2 found that open-loop
policies could obtain non-trivial results in many original SMAC scenarios; our proposed
response is to test those shortcuts and reserve meaningful starting-state variations.
This is a design lesson, not a transfer result about WH3.
[SMACv2](https://proceedings.neurips.cc/paper_files/paper/2023/hash/764c18ad230f9e7bf6a77ffc2312c55e-Abstract-Datasets_and_Benchmarks.html).

Reserve legal map/geometry, role, roster and opponent variations before tuning. Introduce
only supported variation and record actual starting readbacks; a configuration seed is
not proof of a seeded engine or deterministic reset. Keep labels such as development,
confirmation and held-out in the evidence index. A test set repeatedly inspected for
improvements becomes development evidence.

## 6 Controllers and comparisons

The basic reference set should be small enough to understand. All arms use the same legal
orders and comparable disclosed local execution. Parameterize the same executor where
possible so that changing the planner does not also improve targeting or micro-control.

| Arm | Decision process | Purpose |
|---|---|---|
| Coordinated script | Fixed roles with a small declared conditional plan | Strong, cheap reference and feasibility witness |
| Independent simple scripts | Each group follows its own local rule | Measures whether any coordination beyond local competence is useful |
| Single commander | One policy controls all permitted units | Tests whether dividing decisions is worthwhile |
| Two agents without messages | Separate policies, histories and owned units | Tests division of control and implicit coordination |
| Two agents with messages | Same ownership and policies, bounded channel enabled | Primary candidate for explicit communication benefit |
| Hierarchical team, later | One planner delegates; workers execute under named authority | Tests hierarchy only after independent execution works |

For architecture claims, equalize a **total team** budget, not a per-agent budget. Fix the
model/backend, available information, total call/token or monetary cap, action-rate cap,
helpers and maximum concurrent requests. Count communication and coordinator calls.
Show actual usage and latency: equal caps do not guarantee equal work. Permit a central
controller a parallel-call helper with the same total resources when testing whether the
benefit is merely parallel inference. It remains a central controller and gets its own
disclosed identity. A central policy is a reference, not a mathematical upper bound.

Also report a practical comparison allowing each architecture its natural concurrency,
with success, dollars and elapsed time side by side. This asks which complete system is
useful, not which architecture is stronger at equal computation. Do not force slower
models to equal speed by pausing the game. Artificial delay studies are separately named
and applied to the intended channel only, keeping other observations fresh.

After the first comparison, freeze a small partner population: a fixed-role script, a
reactive script and separately developed model controllers. Evaluate a focal agent in
both roles with each partner, including combinations withheld from tuning. First-episode
performance tests unfamiliar-partner coordination; an explicitly permitted adaptation
sequence tests learning a partner. Reset cross-episode memory in the former and log it in
the latter. Two clones of one model are not independent evidence of broad compatibility.
Other-Play motivates this distinction because conventions learned together can fail with
new partners; its Hanabi results do not guarantee that its algorithm fits WH3.
[Other-Play](https://proceedings.mlr.press/v119/hu20a.html).

For native competition, freeze opponent versions and evaluate a matchup matrix with team
and map-side swaps. Include built-in AI references where legal. Do not update an opponent
during a scored evaluation or use opponents' private states for adaptation. Report
matchups directly; a single Elo-style ranking can conceal cycles where A beats B, B beats
C and C beats A. Best responses to a small opponent pool are evidence against that pool,
not proof of low exploitability or equilibrium play.

## 7 Outcomes and statistical design

For a cooperative battle, the primary observation is **one team outcome per match**.
Both agents winning is not two independent wins. Preserve the engine's result and ending
reason, then apply the card's declared rule. A contact card can require a win before the
timer; an objective-holding card may legitimately count a timer result. Tell every agent
the actual rule. Preserve valid engine endings through later worker or logging errors.

Use secondary measures to explain outcomes, not to replace them with an arbitrary
cooperation score:

- Coordination: duplicate commitments, conflicting orders, abandoned responsibilities,
  completed joint actions and successful or failed recoveries, each with a written event
  definition and an unknown category. Include purposeful retreat as a possible success.
- Communication: messages sent/delivered/available to a decision, useful response delay,
  bytes/tokens and cost. More messages or mutually agreeable text are not better teamwork.
- Timing: per-agent observation age at order application, time between useful orders,
  transport waiting, model latency, local executor cadence and battle-to-wall-time ratio.
- Reliability: invalid/stale/unauthorized orders, worker failures, provider failures,
  desynchronization and unfinished matches, with denominators for each agent and team.
- Efficiency: team cost per attempted match and cost per success, undefined at zero
  successes; show the individual agents' shares as diagnostics.

Individual kills, damage and survival are not default rewards: a holding unit can make
the winning contribution while losing most of its soldiers. Attribute contribution by
predeclared policy substitutions with matched conditions and complete outcome accounting.
These estimate effects of replacing that policy in that team, not an intrinsic value of
the agent. Exact Shapley values, counterfactual battle branches and causal judgments from
one replay are not available by assumption.

Plan one primary comparison at a time. Freeze controller identities, conditions, sample
size, minimum useful effect, analysis and stop rule before confirmation. Select the size
using pilot variability and power for that effect; do not promise that ten launches can
detect a modest advantage. Report counts, effect sizes and intervals, including negative
or unresolved findings. Multiple comparisons require a declared correction or exploratory
labels. Follow the [small-sample methods](evaluation-guidelines.md#7-use-statistics-that-fit-small-live-studies)
when their assumptions hold.

Use fresh launches as sampling clusters, keeping rematches together because they share an
engine instance. Independence across launches remains an assumption to justify from the
reset and sampling design. If arms share a launch, preserve the planned pairing and
balance fresh versus rematch slots. Same configuration on separate launches does not imply
shared RNG.
Native multiplayer adds several clients to **one session**, not independent samples;
paired side swaps remain clustered by the planned session/block. Define this unit again
for the native runner before using a binomial or paired test. When variants, teammates
and opponents vary, report them separately first; a suite average needs fixed weights and
uncertainty that respects repeated partners and shared scenarios.

Randomize and interleave arms in balanced time blocks, including the 18- and 36-launch
screens below; do not finish one arm on one night and another on the next. Record host
load, backend and time block. A build/mod change starts a separate condition and needs
reference checks before comparisons resume; never pool it silently into the earlier one.

Every planned trial has a disposition: unstarted, scored outcome, controller forfeit,
excluded infrastructure/setup fault, or unresolved cause. Frozen exclusions apply to all
arms. Controller slowness or a bad teammate is part of team performance, not an exclusion.
A worker failure that leaves the match running retains the eventual outcome and its
failure flag. Missing or conflicting client results are unresolved until reconciled;
never infer a win from the surviving client's silence. Record replacements without
erasing original attempts. Show bounds for incomplete planned comparisons, rather than
silently selecting complete pairs. These extensions need an agreed implementation of the
[failure rules](benchmark.md#correctness-checks-to-agree), not reuse of inconsistent current readers.

## 8 Verification before evaluation

Each row is a proposed repeatable check, with an independent reference and a plausible
wrong implementation it must detect. Agree the method before calling the capability
verified, then record its passing revision. Component checks establish routing and
filtering; live checks establish engine behavior. Neither alone establishes policy skill.

| Capability | Repeatable check and reference | Wrong behavior the check must catch |
|---|---|---|
| Ownership and identity | Two visibly distinct groups receive opposite commands; compare declared ownership, game/UI readback and observed movement. Repeat with swapped identities, rout/rally and a fresh episode | Agent A controls B's unit, or an old request controls a newly reused ID |
| Information boundary | Change only hidden state and private messages in component inputs; emitted policy inputs must be unchanged. In game compare a revealed/hidden enemy against each client's view | Hidden coordinates, death, target identity, another team's message or a new unlisted field leaks |
| Concurrent scheduling | Fast scripted worker and delayed worker act in the same 1x battle; check independent dispatch and observed motion. Swap identities and delay the other worker | Slowest worker becomes a team barrier, mailbox overwrite, duplicate execution or fixed identity priority |
| Message delivery | Send numbered messages with declared expiry/delay/drop; compare sender, router and recipient-input records | A dropped message arrives, an expired message looks current, or a message reaches the wrong team |
| Shared resources | Issue conflicting legal requests for one real pool; compare independent game/UI before/after values and effects | Double spending, wrong army charged or a hidden tactical arbiter |
| Reset and scoring | Known win/loss/timer/draw cases where the mode permits them; swapped sides; changed rematch; failure before and after ending. Compare engine/UI and all client logs | A surviving unit is mistaken for team victory, a failure erases a win, or a client is counted as another match |
| Native multiplayer | Identical declared builds/mods, two real clients first; one local order on each, observed on both; repeated fresh sessions and role/host swaps | Host-only control, divergent simulation, missing allied armies or duplicate script effects |
| Campaign transition | Save/reload a known state, perform one legal action, end a turn and enter/leave a battle; compare semantic fields and game UI on each client | Duplicate action, stale legal action, lost ownership, incorrect treasury/turn or wrong battle result application |

Use cheap component cases first, then a bounded script-only live probe for the named
behavior. Choose enough repeats to exercise the failure mode; a successful first launch
is only feasibility evidence. Include a deliberately broken filter/router or a known
bad recorded case to show that the check detects the specified error. Keep this work in
the existing Python/Lua test structure and ignored run evidence; avoid a generic new
framework before a concrete check needs it.

Human review, where needed, uses agreed success/failure/ambiguous examples, hidden
controller labels and a fixed sample across outcomes. A teammate saying "flank complete"
is a claim to check against game events. LLM reviews can locate evidence; they do not
certify execution or replace the owner's agreement on correctness.

## 9 Stages and concrete deliverables

### A Establish feasibility and the smallest contract

Choose the split-army ownership, observation and messaging rules. Inspect the installed
scripting references for the exact actions needed by the first two cards. Write one
bounded probe plan per uncertainty, naming expected readbacks, observed effects, maximum
game time and a stop condition. Do not widen the API merely because methods exist.

Deliverable: an agreed contract and check sheet, then recorded ownership, visibility and
scheduling probes. Stop before scoring if control crosses ownership, hidden state leaks,
another worker is blocked by inference, or the game cannot maintain the required timing.
The current single-agent path remains available as its own condition.

### B Establish that a team problem exists

Use the hold-and-flank and protect-and-relocate candidates. A concrete initial screen is
three scripted arms per family: coordinated conditional plan, independent local rules,
and fixed timed/role plan. Three fresh launches per arm per family give **18 launches**.
Use this to find broken scenarios, shortcuts and relevant event definitions, not to rank
controllers or certify rare failure rates. Record every attempted setup, including
excluded or unstarted ones, and limit changes to development cases.

Deliverable: two inspectable cards, or an explicit reason one was rejected. Advance only
when legal joint action can affect the outcome and the evidence can distinguish the
intended coordination from the strongest simple alternative. Do not tune difficulty
until the models all fail. Confirmation uses fresh evidence after the card and its
acceptance rule are frozen.

### C Compare two-agent behavior

First run a budgeted pilot with single commander, two agents without messages and two
agents with messages. Six fresh launches per arm per admitted family, for two families,
would be **36 launches**. This count sizes the pilot; it is not a powered final study.
Use its measured time, cost, variance and failure modes to propose a separate confirmation
size. Keep the strongest relevant scripts as contemporaneous references; their additional
launches must appear in the budget, rather than be hidden in the 36.

The recommended first primary contrast is messages enabled versus disabled for the same
two-agent controller. Central versus divided control is a separate comparison with the
resource controls in section 6. Freeze a held-out variant and at least one unfamiliar
partner before tuning. Deliverable: per-card outcomes, timings, costs, communication
ablation and inspected failures. Stop expansion if the interface or scenario, rather
than a controller choice, explains most failures.

### D Establish native team battles

Native multiplayer is a required milestone for claims about native multiplayer, even if
the split-army experiment is successful. Inventory available licensed clients, machines,
accounts, content/DLC and compatible builds. Determine whether permitted game-side
commands are synchronized through the engine. Client-local file polling or Lua callbacks
must not be assumed to produce identical multiplayer effects. Do not replace missing
multiplayer support with a single omniscient host and label it equivalent.

The community mirror of CA's generated [UI scripting documentation](https://chadvandy.github.io/tw_modding_resources/WH3/ui_scripting.html)
warns that changing game state from client-specific UI events can desynchronize a match.
Its [CampaignUI reference](https://chadvandy.github.io/tw_modding_resources/WH3/campaign/campaignui.html)
documents a campaign script event sent to all clients. That is a candidate to inspect in
the installed build, not evidence for a synchronized battle-order transport. The
feasibility probe must distinguish local UI actions from replicated game actions.

Start with two clients and one tiny interaction; then allied player armies against fixed
AI; then four controlled player slots for native 2v2. Each transition requires ownership,
visibility, outcome and synchronization checks. Freeze army-level resources, reinforcement
rules, deployment and disconnect behavior. Run role/host and side swaps. Scale the
opponent matrix only after complete sessions can be repeatedly recounted and rerun.

The current repository permits one game controller at a time across both games. A native
multi-client runner needs an explicit revised ownership arrangement: one supervised
experiment session, with child clients, per-client bridges and coordinated cleanup.
This plan does not authorize concurrent launches or purchase accounts/hardware. If the
engine control route fails, record the limiting evidence and estimate the separate cost
of a player-UI adapter; retain split-army findings under their narrower name.

### E Build campaign capability and then evaluate it

Use the campaign stages below. Passing custom-battle checks does not establish campaign
visibility, multiplayer turn behavior or save correctness. Deliver a small reproducible
multiplayer campaign task before a full-campaign comparison, and keep both in scope.

## 10 Multiplayer campaign evaluation

A campaign is a game between factions with partially shared interests and persistent
consequences. For fixed allies with a shared objective, use a common team result. For
independent factions, retain each faction's objective and outcome; do not collapse every
player into one cooperative reward. The interesting questions include resource aid,
division of fronts, coordinating reinforcements, negotiating commitments, responding to
an ally's loss and choosing when cooperation is no longer beneficial.

The first campaign agent should control one faction. Splitting economy, diplomacy and
battles among specialists inside a faction is a later architecture comparison. Otherwise
it becomes impossible to tell whether performance changed because of internal delegation
or interaction with other factions.

### Campaign progression

| Stage | Task and fixed conditions | Completion evidence |
|---|---|---|
| Read-only access and lifecycle | One chosen campaign and faction; inspect player-visible state, save/reload and loader behavior | Semantic readbacks match the UI; no hidden-faction leakage; instrumentation remains inactive outside its explicit session |
| One-faction action loop | Narrow legal actions, one turn boundary, one battle transition; scripted controller | Actions affect the intended faction once; stale/illegal requests are rejected; outcome and return-to-map agree |
| Two allied player factions | A short cooperative objective from a declared starting state; built-in opposition | Both real clients act, complete turns, resolve battles and reload consistently; shared victory/defeat rule is explicit |
| Bounded strategic tasks | Fixed turn horizon, several starts and roles, frozen battle resolver | Recountable objective results and comparison against strong simple faction scripts |
| Mixed interests | Independent objectives, negotiation and changing alliances where the selected campaign permits them | Per-faction outcomes and recorded commitments/actions; no shared private state or hidden objective leakage |
| Full multiplayer campaigns | Frozen campaign, factions, victory rules, crisis/endgame settings, turn/real-time caps and partner/opponent population | Complete campaign outcomes or explicitly censored attempts, with all interruptions and budgets accounted for |

Suitable bounded tasks might ask two allied factions to protect a vulnerable settlement
while preparing a joint attack, reinforce an ally without losing their own frontier, or
allocate an affordable transfer that enables a shared objective. Choose starts from the
actual supported campaign, with a disclosed setup procedure and readable game objectives.
Use multiple strategic situations, not dozens of branches from one favorable save.
Do not create speculative saves or scenarios until a specific test needs them.

### Information and legal actions

Campaign views must specify what is known about settlements, armies, treasury, income,
recruitment, movement, diplomacy, treaties, objectives and agent messages. Visibility and
alliance intelligence can differ from battles. A script's ability to query every faction
is not permission to show it to an agent. Remembered information needs timestamps/turns;
unseen armies and enemy finances stay hidden unless exposed by a legitimate game mechanic.

Build actions from the legal choices actually available to the faction: movement,
recruitment, building/research choices, diplomacy and turn completion, starting with the
small subset needed by the first task. Validate target identity, cost, prerequisites and
the state version again when applying the action. Record proposals separately from game
acceptance and eventual effect. A diplomatic message promising aid is not a money
transfer; a treaty accepted by the game is different from an unenforced promise.

Native simultaneous turns make ordering consequential. Probe which actions are allowed
while another player moves, negotiates or enters battle. Observe the game's readiness
and transition rules rather than inventing a serial turn loop and calling it native
simultaneous play. Record conflicts, rejected stale actions, turn locks and battle
interruptions. A deliberately serialized research condition can be useful if separately
labelled. Use a declared per-turn wall budget and timeout behavior; keep tactical battles
unpaused at 1x. A player refusing to end a turn must have a predeclared disposition.

### Separating campaign decisions from battle skill

Run two distinct tracks. For **strategic evaluation**, freeze the battle resolution
procedure across all agents: either the same tactical controller at the same settings or
a declared auto-resolve rule where supported. Auto-resolve can favor particular rosters,
so those results concern strategy under that resolver. Do not let one policy manually
fight only the battles it would lose under auto-resolve unless that choice is itself the
declared action space for every policy.

For **end-to-end evaluation**, let faction agents choose or invoke their battle team
under a common contract. Map campaign armies, reinforcements and gifted units to battle
ownership, then map casualties and results back. Recheck authority after every transfer
and transition. Preserve faction identity and permitted long-term memory. Report both
strategic and tactical failures; improvements in one cannot be attributed to the other
without a controlled substitution. Native campaign battle participation must be tested
on the selected campaign and build, not inferred from the custom-battle adapter.

### Campaign outcomes and social behavior

Primary results depend on the task: completion of a named cooperative objective by turn
H, or engine-confirmed faction/team victory in a full campaign. For a by-H objective,
reaching H without completion is non-success. For time to full-campaign victory, an
administrative horizon can be right-censoring: the victory time is still unknown. Also
report success by that cap, retaining unfinished campaigns in its denominator. Controller
failures, refusal to end a turn and controller-caused budget/time exhaustion follow the
frozen failure rule; they cannot disappear as benign censoring. Do not assume interruptions
are unrelated to policy strength. Report completion/defeat/failure/censored counts and
turns plus wall time. Territorial growth, income, army value and ally survival can be
useful diagnostics, but none is a universal
score across factions. Freeze any proxy's definition and weights before comparison and
keep it distinct from the actual objective.

For mixed-interest play, show each faction's result and the distribution across partners,
opponents and starting roles. Record offered agreements, acceptances, actual transfers,
joint operations and broken promises with precise conditions and unknowns. Negotiation
quality is not the eloquence or friendliness of the chat. Test dependence on communication
and partner behavior using interventions and partner swaps. Cooperation can be rational,
and declining an unfavorable deal need not be failure.

Hold out partner policies and strategic starting situations, as well as maps or factions.
Melting Pot treats other agents' behavior as part of the environment and evaluates
generalization across social situations; that motivates a population of allies and
opponents here. It does not prescribe a WH3 campaign reward.
[Melting Pot](https://arxiv.org/abs/2107.06857).

The sampling cluster is a campaign start/session under the declared design, not each
turn, army or battle; independence between starts also needs justification. Branches from
the same save share history and must be grouped or used as explicitly paired comparisons,
not counted as independent campaigns. Reloading
the same save does not establish deterministic continuation. Record campaign provenance,
turn, semantic state, RNG availability, agent memory, build/mod hashes and restore
behavior. Distinguish resuming an interrupted trial from retrying a failed decision or
starting another evaluation. No selective rollback after bad moves in a scored campaign.

### Campaign access conditions

Before a campaign launch, resolve the existing owner decisions on harness-created saves
and irreversible Steam achievements, as recorded in
[state](../state.md#owner-decisions-waiting) and the
[campaign infrastructure rules](../autonomy.md#wh3-campaign-infrastructure).
Use a dedicated test profile/save namespace if supported, protect existing saves, and
check loaders in both campaign and campaign-battle contexts. The known shared imagery
loader issue is documented in [integration](integration.md#packs-and-loading); a battle
guard alone does not make the whole mod inert in campaigns. New live access requires
that objective lifecycle work first. The request for a plan does not settle these effects.

## 11 Cost and implementation boundaries

Keep engineering feasibility, benchmark design and policy experiments as separate work
items with named stopping points. The first implementation should reuse `battle/play.py`,
the mailbox, protocol validation, controller interface and existing evidence readers.
Add per-agent ownership and dispatch only where the pilot needs them. Native clients need
their own bridge directories and identities; campaign state/actions should have a separate
contract within `twwarhammer3`, rather than overload battle unit orders. Do not move code
into `gameai` merely to anticipate another consumer.

Estimate resources from measured pilots:

- Game hours = planned sessions × measured setup/battle/recovery time, plus separately
  bounded feasibility and failure allowance. The old single-client throughput does not
  predict multi-client or campaign throughput.
- Model cost = all agents' calls, communication, coordination, retries and memory work,
  with a team cap and a study cap. Concurrent workers require atomic shared reservations;
  independent caps must not each spend the full remaining ledger allowance.
- Native hosting cost includes actual client count, compatible licenses/content and
  machine/network capacity. Measure contention and lag with the intended client count.
- Human time includes check agreement, fixed-sample trajectory review, disagreement
  resolution and independent recount/rerun, not just coding time.

No new spending amount is adopted here. The current shared ledgers/caps still apply, and
the reported near-exhausted OpenAI allowance is not a basis for scheduling a new paid
study. Freeze a complete bounded job plan after costs are known. Stop between sessions
before a cap; do not run the cheap arm to completion and silently leave the expensive arm
unfinished. A campaign needs a resume policy and enough budget for its declared horizon.

The release artifact should contain the condition definitions, agents and disclosed
helpers, scenario/setup recipes, agreed checks with revisions, frozen study plan, raw
attempt dispositions, outcome reader, per-card/matchup report and inspectable event traces.
Recount a sample independently, then rerun a named condition on another permitted setup
before claiming reproducibility beyond this machine. Share code and permitted derived
evidence, not proprietary game packs or campaign saves. No universal leaderboard is
needed for a useful first release.

## 12 Recommended first decisions

The concrete proposal to discuss is:

1. Use two agents with fixed unit ownership and the same public battle view for the
   split-army pilot, then native allied armies and native 2v2 as separate required steps.
2. Develop hold-and-flank and protect-and-relocate candidates; use the 18-launch scripted
   screen only after the ownership, visibility and scheduling checks are agreed and pass.
3. Make the first model question the benefit of a bounded message channel, with fixed
   total team resources and a central-controller reference. Set the dollar/game-time cap
   from observed feasibility costs before scheduling the proposed 36-launch pilot.
4. Reserve unfamiliar partners and at least one legal scenario variation before tuning;
   size a fresh confirmation study for a named useful effect after the pilot.
5. Treat native multiplayer setup and campaign lifecycle as capability gates. Use a
   provisional campaign/faction for access probes, then choose the evaluation campaign
   and factions from that evidence. Freeze a short cooperative task before mixed-interest
   and full-campaign evaluation.

The next implementable unit is the smallest split-army ownership/dispatch contract and
its proposed check sheet, together with a read-only inventory of native multiplayer
requirements. That work should settle whether two independent agents can act and be
measured correctly before any claim about superior teamwork.
