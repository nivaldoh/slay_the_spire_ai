# WH3 team structures: who commands which units

Status 2026-10-27: the [starting-set screen](log.md#2026-10-22-the-starting-set-screen)
parked the rank-5 line this page plans on, and the owner made team work a later arm on the
Land Battle benchmark ([direction](../owner-direction.md)). The stages wait for that
battle's first team-vs-single result; costs and the card below refer to the parked line.

Proposed plan, 2026-10-21. The owner's request ([directions](../owner-direction.md)): two
LLMs for one army is an arbitrary split, useful as a comparison point; explore one model per
unit, one per type of unit, one per custom group chosen ahead of time by another LLM, and
more, and find what is worth visualizing about how an LLM team behaves. This page lays out
the options, what each would cost and answer, the code each needs, the views, and a staged
sequence. Nothing here is verified or scheduled, and no spending is adopted. The [evaluation
plan](multi-agent-plan.md) sets the rules every comparison follows; the [implementation
page](multi-agent-implementation.md) describes the team code. Working notes, drafts and the
$0 prototypes behind the numbers: `runs/twwarhammer3/team-structures-20261021/`.

Costs below are for GLM-5.3 low on the rank-5 line (`emp-line-grn-raid-xp5`, 7 Empire units
against 7 Greenskins), the first candidate card. "Measured" values come from recorded
battles, with their count; "estimated" values are arithmetic on those. No model team battle
has been played, so every team cost is an estimate.

## 1 What can vary

A team structure is a choice on each of these:
- **Who owns which units:** the whole army (one controller), two groups, one member per unit
  class (infantry, missile, cavalry), one per unit type key, or one per unit.
- **Who forms the groups:** a fixed rule (class, type, position), a random draw (a control),
  an LLM before the members act, or regrouping during the battle.
- **How members coordinate:** only through what they see of each other's units (today),
  written job notes, missions from a planner, messages, or dialogue.
- **When members call their model:** each continuously (every member keeps a call in
  flight), one call at a time for the whole team (round-robin), or on events (a unit
  engaged, men lost, target dead).
- **When the model decides:** throughout the battle, once before it with scripts carrying
  out the plan, or never (scripted).
- **Which models:** one model for every member, or a strong planner over cheap members.

## 2 What prior work suggests

Almost every study below is step-based: the world waits while the models think. WH3 runs
unpaused at 1x with no teammate barrier, so these results suggest designs; they do not
predict WH3 results. All eight were read in full or in their first 100,000 characters;
sources read only as abstracts, none of them in this table, are listed in the working notes.

| Source | Structure | Finding | For WH3 |
|---|---|---|---|
| [Chen et al. 2024](https://arxiv.org/html/2309.15943v1), multi-robot | One LLM per robot in dialogue; one central LLM; a central plan checked by per-robot LLMs | Per-robot dialogue was worst (BoxLift 52.5% success, 37 times the central planner's calls); per-robot checks of a central plan were best (100%) at about 15 times the calls | One model per unit that talks to its peers is the costliest, weakest design; a check layer over a plan did better |
| [SMART-LLM](https://arxiv.org/html/2309.10062v2) | An LLM forms robot coalitions once, before execution | Removing coalition forming dropped success 0.75 to 0.60; GPT-4 on complex tasks varied 0.48 ± 0.40 over 5 runs | The closest reference for LLM-chosen groups: repeat the call and compare with rule and random partitions |
| [LLM-PySC2](https://arxiv.org/html/2411.05348v1), StarCraft II | One LLM per unit team or role, with messages | Agents "struggle to allocate targets and coordinate attack and retreat timing", with or without a leader | Per-group LLMs coordinated badly in SC2; no single-controller comparison was made |
| [TextStarCraft II](https://arxiv.org/html/2312.11865v3), [SwarmBrain](https://arxiv.org/html/2401.17749) | One LLM for strategy; per-unit behaviour as scripts | The best-known LLM RTS results keep the model away from unit control | "One controller per unit" there is a rule, like our skills executor, not a model |
| [Scaling agent systems](https://arxiv.org/html/2512.08296v1) | Single, independent, centralized, decentralized, hybrid; 180 configurations | Independent agents amplified errors most (17.2 times); central checking cut that to 4.4 | One model per unit without messages is the "independent" design; expect it to lose, and say why |
| [Guo et al. 2024](https://arxiv.org/html/2403.12482v2) | No leader, a designated leader, elected leaders | A designated leader helped; elected leaders raised communication cost | A planner over members is worth one arm; leader elections are not |
| [MindAgent](https://arxiv.org/html/2309.09971v2) | One central dispatcher for 2-4 agents | Model capability mattered more than the number of agents | Never mix models to make a large team affordable; compare structures on one model |

## 3 The structures

| | Structure | Who decides | Question | Estimated $ per battle | Verdict |
|---|---|---|---|---|---|
| S0 | One `llm_rules` controller | One model orders all 7 units, about every 3 s | The reference for every split | $0.58 measured (1 battle on this card; $0.23-0.58 over 4 GLM line battles) | Keep |
| S1 | Two members: the Knights and the rest | `team_llm_rules`, built on the `wh3-model-team` branch | Does any division help? The owner's "arbitrary" comparison point | $0.58 round-robin; $1.11 when both call continuously | Keep, as a rung |
| S2 | One member per class: infantry (4), missile (2), cavalry (1) | Three members | Do narrower agents keep their jobs better? The owner's "one model per type" | $0.58 round-robin; $1.61 continuous | Keep |
| S3 | One member per unit (7) | Seven members | The owner's "one model per unit"; how attention, order age and cost change at 7 agents | $0.55 round-robin; $3.62 continuous | Keep round-robin; one continuous demonstration battle optional |
| S4 | Groups and missions from a planner LLM | One planner call on the first observation returns 2-4 groups, each with a one-line mission; one member per group | The owner's custom groups: does an LLM's grouping and plan beat fixed ones? | about $0.60 (the call is about $0.004) | Keep |
| S5 | Planner missions during the battle | The planner updates missions every 60 s; members carry them out | Does a live intent layer add anything beyond each member knowing its job? | about $0.6 round-robin; about $2.25 continuous | Later |
| S6 | LLM-written scripts | Before the battle, an LLM writes one small scripted policy per class; no model calls in battle | Can a model's plan work without live inference? | about $0.01 | Later: generated code needs a sandbox, which `team.py` is not |
| S7 | Scripted structures | `LineTeam`; independent role scripts that never read each other (the team foil); `LineTeam` with the Knights held back (the card's shortcut) | Does the card need coordination at all? | $0 | Keep, first |

S2 uses classes rather than unit type keys: a split by type key gives five members that
differ from S3 mainly by grouping the two Swordsmen and the two Handgunners. S4's members
get their group's mission line, which is the point of the owner's idea; a later arm can
separate membership from missions (below).

Variants to test with the structure held fixed, later: event-triggered calls; a stronger
planner over cheap members; a scripted check over members' orders before dispatch (the check
layer that did best in Chen et al.); messages ([plan
§4](multi-agent-plan.md#communication)).

Skipped: peer dialogue and debate (the costliest design even when the world waits); elected
leaders; LLM bidding for tasks (no source found, and a scripted auction can come later);
regrouping during a battle (`team.py` treats an ownership change as a fault, and transfers
need their own rules); 20 per-unit members on the 20-unit battle (the mailbox would give
each member a turn only every 6 s or more); synchronized team rounds.

Where the costs come from: on the 4 GLM line battles each call costs $0.0026-0.0030 and a
single controller makes 10-20 calls a minute. Each own unit adds about 93 tokens to a prompt
(a per-call fit over 24 GLM low battles), so trimming a member's prompt to its own units
saves only about 15%: call count drives cost. 45-80% of the single controller's decisions
changed no order (179 of 224 in the rank-5 battle); a per-unit infantry member calling at
that pace would make about 230 calls to give about 6 orders.

## 4 The schedule: continuous or round-robin

If every member keeps a call in flight, a 7-member team makes about 7 times the calls of one
controller, costs about 7 times as much, holds 7 ledger reservations ($0.31 each) and fills
about 70% of the mailbox's capacity (about 3.3 batches a second, measured on the four
scripted probes). It also changes two things at once: the number of decision makers and the
compute spent.

Round-robin keeps one call in flight for the whole team: the member whose last call is
oldest goes next, and its view is built when its call starts. The team then spends about
what one controller spends, and the comparison asks how splitting one model's call stream
changes play. That has a price: each unit gets a fresh decision less often (about every 20 s
per unit with 7 members, estimated), and one member's provider retry delays everyone.
Round-robin is also a team-wide wait by design, so it is its own named condition: the
[execution contract](multi-agent-plan.md#4-the-battle-execution-contract) asks for no
teammate barrier, and the agreed scheduling check does not cover it. Rotate which member
goes first across launches and record the order.

Choice: screen every structure round-robin, so the arms cost the same and differ only in how
units are divided; keep S1's continuous version as built; and offer one continuous S3 battle
as a demonstration of seven models acting at once (about $3.6, estimated $1.1-6.1). That
demonstration first needs a short check of how many calls the pinned backend serves at once;
its record there is 4,677 GLM calls, all made one at a time, none lost to HTTP 429 (two
needed transport retries after HTTP 409 or 429, which `post()` does not record).

What to expect, stated before any run: under the single controller (1 battle), the median
gap between acknowledged orders was 5.4 s for the guns, 15.5-15.9 s for the infantry and
19.8 s for the Knights. Round-robin per-unit control gives every unit about 20 s, so S3
should mainly hurt the guns: longer gaps between their orders and more time idle with a
target in range. If S3 does not show that, the measure or the reasoning is wrong.

## 5 Code needed on top of team.py

In build order, on a new branch from `main` once `wh3-model-team` is merged or discarded
(branches are at 3 of 3, and adding these items to it would join outcomes the owner should
accept separately). New scripts go in a new file, not `calibration.py`, whose hash
identifies `LineTeam` on the card board. Each check is proposed, not agreed.

1. **The team foil and the card's shortcut** as scripts in that new file: role scripts that
   never read each other, and `LineTeam` with the Knights held back. Check: each plays on
   recorded observations, and the foil's members never read a teammate's state.
2. **Team-correct replay, report and export**, before any team row reaches a page. Member
   ages from each member's own source time, frames only from the outer records, notes per
   member, a structure field so team and single rows of one model stay apart, and unique
   member exchange IDs so `export` stops failing. Check: on the four scripted probes the
   replay must show member ages of 3.3-3.9 s and 0.6 s; today it shows the dispatcher's 0.3
   s.
3. **One to seven members**, owning units by class, type or explicit unit ID, from a named
   arm spec recorded in the card and the register (so `stats` never pools arms), and one
   teammate note for any number of teammates, as a logged prompt version. Unit IDs f1-f7
   kept their type and start position (within 5 m) in all 17 recorded fresh launches of the
   line, so ID ownership is usable. Check on recorded line observations: partitions are
   disjoint, complete and stable, and a planted overlap or gap faults; offline, `LineTeam`
   split into members gives `LineTeam`'s orders except where it reads fields an ally row
   lacks (listed).
4. **Round-robin schedule.** Check with fake members and a fake clock: never two calls at
   once, every member called within N turns, and a view no older than one tick when its call
   starts; a planted "submit everyone to a one-worker pool" version must fail on view age.
5. **Planner call** for S4: one call on the first observation returning groups and missions,
   each unit exactly once; an invalid reply falls back to the class rule with the reason
   recorded; a `plan` event keeps the prompt, reply, cost and exchange ID. The member that
   owns the unit with the commander flag (the Spearmen in all 17 line launches) owns the
   army orders.
6. Later: planner missions during the battle (S5), event triggers, a check layer.

Freeze `team.py` before a paid night: every edit changes the team arms' identity. Rerun the
agreed live check once after items 3-4, not after each.

Budget caps: `--budget-usd` caps the WH3 ledger's cumulative total, and `wh3_queue.py`
freezes every job's arguments before the night. So each job's cap is the ledger total when
the plan is frozen, plus the planned spend of that job and every earlier one, plus $0.31 per
call that can be in flight. The account shows about 12% more than the ledgers (cause
unknown), so the last job's cap stays at or below the ledger total plus ($50 minus the
account's used total) / 1.13, about $44 today. The queue has no cost stop: the cost stop in
§6 is a `<plan>-stop` file written by whoever watches the night.

## 6 Stages

| Stage | What | Launches and cost | Decides |
|---|---|---|---|
| A | The agreed starting-set screen (a precondition, not part of this plan) | 39 launches, $0 | Whether the line stays a candidate (a screen alone admits no card; the line still needs its named shortcut, run in C, and the owner's commander-flag decision) |
| B | Offline, after A keeps the line (no new team code before the starting-set screen): code items 1-5 and the measure definitions; the $0 view prototypes can start now | none, $0 | Whether the code and the definitions are ready |
| C | $0 team night: the live-check rerun; the team foil and the card's shortcut, 3 each (the tactic-card page's shortcut screen, not yet planned); 7 fixed-delay scripted members round-robin, 2 | about 12 launches, $0 | Whether the card needs coordination ([§9 B](multi-agent-plan.md#b-choose-the-card): the foil and the shortcut must lose), and live round-robin timing at 7 members |
| D | Once a held-out variant of the card is reserved (as the tactic-card process requires before more model launches on a card), the structure screen: S0, S1, S2, S3 and S4 round-robin, 3 launches each, interleaved in one night, first launch of each arm in a block at the start | 15 launches, about $9-10 (up to about $17 at the high end of the measured spread), 3-5 h | Which structure, if any, is worth the F pilot; the first measured member call rates, costs and order ages |
| E | Planner variability: 10 planner calls on the recorded first observation | no game, about $0.04 | How much the planner's groups vary; if 8 of 10 equal the class rule, S4 differs from S2 mainly by its missions |
| F | A 6 + 6 pilot ([§9 C](multi-agent-plan.md#c-first-comparison)) of at most one structure against S0, plus a few same-night witness launches | 12 launches plus the witness launches, about $7-14 | Whether that structure is worth sizing a confirmation for on this card |
| G | Later, one question per night: S4's groups against random groups of the same sizes (which also make the planner call and discard it); missions against written job notes; S5; triggers with the structure fixed; the continuous S3 demonstration | about $3-7 each | Each its own question |

D is development evidence: three launches per arm make no outcome claim. It is read through
process measures (the unit attention interval, member order age, guns idle with a target in
range, calls a minute, cost per battle-minute) and the views below. Before D starts, write
down which measure and margin send a structure to F, or none, for the owner's review, as the
starting-set screen's reading rule was agreed before that screen ran. Stop D on a harness
fault, or when an arm's cost per battle-minute passes twice its estimate. `wh3_queue.py`
cannot stop one arm, so a fault stops the night, which is why each arm's first launch comes
early; that first block replaces the branch's planned single paid smoke battle. Model
launches on the rank-5 line took about 10 and 13 minutes (2 launches; 7-17 minutes over the
line's 7 model launches), and a battle can run to the 20-minute timer.

This replaces the evaluation plan's earlier first step, a 6 + 6 of S1 against S0 ([§9
C](multi-agent-plan.md#c-first-comparison)): the owner called that split arbitrary, and a
screen across structures tells more for less. F then pilots whichever structure D's written
rule picks, by the same stop rule.

Money: about $25.74 is left of the shared $50 OpenRouter allowance (by the account). The
starting-set model screen already planned ([tactic
cards](tactic-cards.md#the-starting-set-proposal-2026-10-21)) needs about $10 by the ledgers
(about $11.30 by the account) and D about $10, which leaves about $4. At D's high end (about
$17) the two do not fit together, so S1 leaves D first or the model screen shrinks; F and G
need a new allowance.

## 7 What to show

Each measure gets a written definition with an "unknown" category, and it must first tell
`LineTeam` apart from the team foil on scripted runs before it is used on models. A view is
a lead, not evidence: an engine-reported target is not proof of a fight, a shared target can
be deliberate focus fire, and an idle unit can be a planned reserve.

In build order:
1. **Member lanes**, one row per member along battle time: thinking, waiting for its turn
   and the time to engine application, with marks for forfeits, local refusals and calls
   discarded at the end. It shows who stalls and whether the call stream or the mailbox sets
   the pace. Data: the team `input`, `completed` and `feedback` events and the outer
   decision records; prototype at $0 on the four scripted probes.
2. **Unit attention timeline**: one row per unit, a tick for each call that owned the unit
   and a dot for each order (filled once acknowledged), so calls that changed nothing show.
   It shows how often each unit gets a fresh decision, the main difference between S0, S2
   and S3. Prototype at $0 now on the single-controller line traces.
3. **Who commanded what, and why**: units coloured by member on the existing replay map,
   each member's orders drawn when dispatched, and its quoted reason and notes on hover; the
   most model-specific behaviour a team shows. Data: the partition event, 1 Hz replay
   frames, decision records.
4. **The planner's groups and missions** drawn on the deployment map, beside where each
   group went; for repeated planner calls (E), a gallery of the partitions it chose.
5. **The structure ladder** for the report page: one row per model and structure with wins
   of n, $ per battle, calls a minute, median member order age and median unit attention
   interval, scores defined once in footnotes; and one battle under each structure shown
   side by side at the same moments.

Not built yet: a co-targeting strip (with the line split into 4 groups after the fact, a GLM
single-controller battle and a `LineTeam` battle each shared targets 39% of the time; both
are single controllers, so whether it separates coordinated from uncoordinated play waits
for the team foil); "orders crossing in flight" (nearly fixed by design under round-robin;
useful only for continuous arms); a mission board and a message graph until missions and
messages exist.

## 8 Choices made, for the owner's review

Taken under the owner's 2026-10-21 delegation; each is reversed by editing this page:
1. Superseded 2026-10-27: the owner made the first team battle a team-vs-single comparison
   on the Land Battle. (Was: the first paid team night is the structure screen D.)
2. JUDGEMENT: round-robin screen — assistant, 2026-10-21: every structure round-robin at one
   controller's call stream, not natural concurrency first (plan §6). Every arm's cost and
   order age rest on it; continuous per-unit control is one optional demonstration.
3. JUDGEMENT: one model per type — assistant, 2026-10-21: one member per class (3), not per
   type key (5). S2's member count and cost rest on it.
4. JUDGEMENT: planner missions — assistant, 2026-10-21: S4's groups also get missions;
   membership-only and random groups come later. What S4's result means rests on it.

The owner's call: the money (D and the model screen together use about all of what is left
at their central estimates and more at the high end; F needs more). Answered 2026-10-27:
merge `wh3-model-team` after one live-check rerun.

## 9 Risks

- **Small samples.** At three launches per arm, D shows mechanisms and costs, not which
  structure wins; at six, only a gap like 5 of 6 against 0 of 6 is clear.
- **The card may not need coordination.** C decides; if the foil wins, no paid team stage
  runs on this card.
- **Cost estimates** spread from 0.3 to 1.7 times per battle, and the account shows 12% more
  spend than the ledgers. Plan to the upper bound, and name the arm cut first (S1).
- **Round-robin ties division to slower attention per unit.** That is the treatment; report
  each arm's attention interval with its result.
- **A home advantage for S0.** The `llm_rules` prompt went through 22 versions tuned on
  single-controller evidence; members get it plus one note.
- **Prompt versions.** The teammate note and S4's missions are logged prompt versions. Never
  change the structure and the call schedule together.
- **IDs** were checked on 17 fresh launches at 5 s: all seven friendly units and the first
  three enemy units; every line job had one episode per launch, and rematches were not
  checked.
