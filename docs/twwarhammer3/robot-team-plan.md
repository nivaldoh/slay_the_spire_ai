# Robot team research plan

Rough draft, 2026-10-20. Planning only; the proposed comparisons have not run and their
verification methods are not yet agreed.

**Can an agent keep a team working when one member can no longer do its job?** In WH3,
one unit can hold an enemy in place while another attacks elsewhere. If the first unit
breaks, the second unit's plan may stop making sense even though it is still healthy.
We want to test whether the controller notices, finds a workable replacement, or changes
the plan.

This develops the owner's idea of an army as detachable robot parts. Each unit already has
local control supplied by the game: movement, pathfinding and individual fighting. The
useful robotics connection is deciding how those units work together as their abilities
and availability change. The units have no mechanical joints; success here would not by
itself show that a controller works on physical robots.

## What might make this interesting

The team's useful abilities depend on its members' relationships. A weak unit can buy time
for a strong one. Losing that weak unit can remove an opportunity elsewhere. Replacing it
with a slower or tougher unit may require changing the timing of the whole plan.

Robotics already studies related problems. [EMOS](https://arxiv.org/abs/2410.22662)
uses language models to coordinate robots with different physical capabilities.
[Reactive Task Allocation and Planning](https://arxiv.org/abs/2110.08436) studies recovery
from failures and obstructions. [DPT-Agent](https://arxiv.org/abs/2502.11882) combines fast
local behavior with slower reasoning, and
[The World Won't Wait](https://arxiv.org/abs/2610.20665) evaluates agents while games
continue during inference.

The possible contribution here is a small, inspectable set of battles where an opponent
disrupts cooperation while existing orders keep running. We could identify whether a
failure came from choosing roles, carrying them out, or continuing a plan after its
conditions disappeared. This is a candidate research direction, not a claim of first use.

## A first battle to try

Start from the existing `skv-ogres-slaves-emp-halberds-1` scenario in
[scenarios.json](../../configs/twwarhammer3/scenarios.json). Keep its map and declared
settings: a normal land battle, player defending, no lords, AI stats modifier 1.0 and a
20-minute limit. Every battle runs unpaused at 1x.

| Side | Units | Proposed jobs |
|---|---|---|
| Player | One Rat Ogres unit | Reach and fight the Handgunners while the Halberdiers are occupied |
| Player | Two Skavenslaves units | One holds the Halberdiers; the other waits nearby to replace it |
| Enemy AI | One Halberdiers unit and one Handgunners unit | Their behavior remains controlled by the game |

The scene we hope to observe is concrete: the first slave unit is fighting the halberds,
the ogres are fighting the guns, and the reserve is still available. The first slave unit
routes: it breaks and flees. Can the reserve engage the halberds before they reach the
ogres? If it cannot, does the controller get the ogres out or choose another workable action?

The controller would place the reserve through ordinary movement orders. Its waiting
distance needs development runs; the current setup does not give us a proven arrangement
that produces this sequence. Do not add exact starting positions or a timed forced rout
to the experiment's description until those controls work.

There is some relevant experience, but no handover result:
the [expendables pilot](log.md#2026-10-18-tactic-cards-harness-b28-to-b30-and-the-overnight-checks)
recorded attack-nearest and hold each losing one battle, and `SlaveTarpit` winning 3/4.
That script sends **both** slave units to the single halberd unit. Its wins do not show
that keeping a reserve is useful. These small gameplay samples remain unverified.

The first practical question is whether reserving a unit ever creates a useful choice.
Sending both in immediately might be better, the ogres might finish before a replacement
is needed, or the first rout might break the rest of the army. Any of those findings could
make this a poor recovery task.

## What to compare

Use one shared local controller that can carry out an assignment: engage an enemy,
wait at a position, or withdraw. It must continue operating while a model thinks. Start
with written rules. Learning those movements or generating new control code would be a
separate comparison.

Then compare three ways of choosing assignments:

| Controller | What changes during the battle |
|---|---|
| Fixed assignments | Keeps the opening jobs. Local movement and ordinary checks for unavailable units or targets still run |
| Simple replacement rule | Starts with the same jobs; when the first screen routes, sends the reserve to the halberds |
| Model choosing assignments | Starts with the same jobs; can replace the screen, redirect the ogres, or abandon the plan |

Give all three the same public information about their army and visible enemies, local
controller and update rate. Explain the tactic to the model: this comparison concerns
changing an assignment, not recalling a game tactic. Record who changed each assignment
and when it took effect.
Keep the existing both-slaves-at-once script as a reference; beating an intentionally
restricted fixed plan is insufficient if that simpler approach still does better.

Allow other ways to win. A controller that finishes the guns before the screen breaks
may have made a better plan. Report that as a win without calling it evidence of recovery.

## What we would observe

Keep the engine's win, loss or draw as the main outcome. Also review the sequence around
the first screen's rout:

- Was the reserve still available, and were the guns still a threat?
- When did the controller see the rout, change the assignment and submit the new order?
- Did the replacement actually reach and occupy the halberds? Did the ogres continue their
  attack, withdraw successfully, or get caught?
- Did a late plan cancel a useful action already in progress?

An accepted attack order does not prove that the reserve held the enemy. Review the replay
alongside public positions and melee/routing flags. Before scoring handovers automatically,
agree examples of a successful handover and a failed one, including an accepted order that
arrives too late. The 1 Hz replay limits timing precision; a melee flag alone does not say
which unit an enemy is fighting.

Report whole-battle results for every assigned launch, including battles without a rout.
Natural routing depends on earlier decisions. Comparing only the battles where each
controller happened to lose its screen would not isolate its ability to recover.

## A small sequence of experiments

1. **Check that the battle poses the intended problem.** Review existing replays first.
   If worthwhile, propose a script-only pilot: three fresh launches each for sending the
   ogres around the halberds without a screen, both slaves together, and reserve replacement.
   Compare with the recorded simple-attack results; repeat that control if its setup differs.
   Nine planned launches would locate obvious problems, not establish reliable success
   rates. If replacement never matters or cannot work, revise or drop this setup before
   model runs.
2. **Test whether the model adds useful decisions.** Run the three assignment controllers
   above on one frozen setup. Decide the launch count, spending limit, stopping rule and
   minimum useful improvement before running. Randomize controller order across fresh
   launches; rematches are not extra independent samples. Keep development results separate.
3. **Change one team member.** Reserve a legal roster variation, such as replacing the
   reserve slaves with Clanrats, after checking recruitment and winnability. Compare
   controllers within that same variation. More wins with a stronger army alone would not
   show better adaptation. Keep the variation out of controller tuning.
4. **Test a disruption during play only if the earlier steps justify it.** A temporary
   loss of control, permanent removal, or delayed replacement could expose recovery more
   directly. Each needs a validated scenario mechanism and a reference that can recover.
   Test them separately; routing and death have different consequences.

A later timing experiment could delay only the planner while the local controller keeps
receiving fresh state. Today's `--delay-seconds` delays the whole policy's observations,
so it does not perform that comparison. Measure actual delays and include failed calls.
Our [chariot results](log.md#2026-10-19-witness-v2-and-prompt-v21-harness-b40) already caution
against treating every execution failure as a speed problem.

## Main risks and reasons to change course

- **The scene may be too easy or unrecoverable.** If both slaves together solve every
  variation, or the first rout reliably ends the battle, choose a different small task.
  The ogres may also outrun the halberds and reach the guns without a screen.
  Pin-then-rear is another candidate, but its existing results also need development.
- **A bad route can look like a bad plan.** Record starting positions and inspect terrain
  and friendly units that block movement. A fresh launch does not guarantee the same
  starting arrangement.
- **Morale may dominate the comparison.** In an earlier lordless expendables battle the
  game marked a slave unit as commander. Check that role and its consequences before
  interpreting a rout. The model prompt currently omits a commander field that scripts can
  see; the compared inputs must be made consistent.
- **The local rules may supply the useful decisions.** Changing assignment selection and
  movement logic together would hide where an improvement came from. The current
  `commander` is an architectural starting point, not a proven controller for this task;
  its [known constraints](robotics.md#2-make-the-planner-and-executor-independently-replaceable)
  need attention.
- **A simple replacement rule may be enough.** That would be a useful result. It would
  justify trying one harder choice or a new roster, not adding more model agents by default.
- **More units may only add noise.** Later compare a few independent fights with a few
  fights that depend on one another. This asks whether coordination, rather than unit
  count, is the difficulty.
- **WH3 may remain a game-specific result.** A stronger robotics claim would require
  trying the useful idea in a robot-team task, such as completing a delivery when one
  robot can no longer take its assigned route.

The immediate next step is the feasibility review of the expendables battle. Campaign
play, independent model teammates and large training runs can wait until a small battle
shows which decisions are worth studying. Implementation details and other controller
ideas remain in the [robotics notes](robotics.md).
