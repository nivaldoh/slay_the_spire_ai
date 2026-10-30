# Native multiplayer feasibility and draft plan

Assessment, 2026-10-30, at `652e35d`. **Worth a small two-client experiment. Native team
battles look plausible; our current controller does not support them.** The main unknown
is whether a Lua order issued on one machine reaches the shared battle correctly.
An unattended graphical client looks much more practical than building a headless runtime.
No supported headless or dedicated battle server was found in the inspected interfaces.
That is a search result, not proof that removing rendering is impossible.

The owner requested exploration, a draft plan, costs and risks, with cloud design left open.
This adds a possible direction alongside the [existing multi-agent plan](multi-agent-plan.md),
without changing its benchmark or adopting the proposed checks below. No machines were
rented, accounts created or paid model calls made. **Zero live multiplayer battles** were
run: this workspace supplies no second licensed client. Multiplayer remains **unverified**.

## What the assessment established

The read-only inventory ran against the installed executable and shipped scripting/UI
documentation. Build **25961564** and executable SHA-256 matched the repository pin.
Evidence and rerunnable scripts: `runs/twwarhammer3/multiplayer-assessment-20261030/`.
The source audit was independently repeated; public sources were checked on 2026-10-30.

| Finding | Evidence | Meaning |
|---|---|---|
| The game supports team multiplayer | [SEGA FAQ](https://support.sega.com/hc/en-gb/articles/4417717186833-TOTAL-WAR-WARHAMMER-III-FAQ): battles for 2–8 players | Four player slots are within the advertised range; this does not prove our mod works there. |
| Our mod refuses multiplayer | [Battle Lua](../../src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua), `load()` | Add an explicit experimental path; deleting the guard alone is insufficient. |
| Local ownership has a documented API | Shipped `battle.html`: `local_alliance()`, `local_army()`; [CA reference mirror](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle.html) | Ownership likely needs an adapter, rather than new engine hooks. Availability in multiplayer still needs a live check. |
| Our ownership assumptions are wrong for allied player slots | `scan()` takes army 1; reinforcement registration can take allied units; `get_player_army()` in the shipped library also returns army 1 | Audit unit control, abilities, magic and reinforcements together. “Human-controlled” does not mean owned by this machine. |
| Useful lobby controls already exist | Shipped UI contexts: `CcoCustomBattleLobby.ToggleReady`, `LocalPlayerSlotContext`, `IsLocalPlayerHost`; slot `SwitchTeam`, `IsSynchronisedWithLobby`; `CcoNetworkPlayer.CurrentGameArmyContext` | Strong leads for unattended setup and identity checks. Method names are not evidence that a lobby can be created or joined. |
| Create/join remains open | No create/join method found in the six inspected UI contexts or the frontend script interface | Inspect the actual multiplayer screen bindings next. The search was not exhaustive. |
| External orders are not explicitly synchronized | Bridge reads a client-local file on a real/UI timer, then calls unit controllers on a model callback | The script has no explicit multiplayer broadcast/enqueue. Native replication of these calls is unknown. |
| Timers have different guarantees | Shipped timer documentation; [CA reference mirror](https://chadvandy.github.io/tw_modding_resources/WH3/battle/timer_manager.html): model timers synchronize; real/UI timers do not | A shared model callback does not make independently received commands identical or simultaneous. |

CA's [UI scripting documentation](https://chadvandy.github.io/tw_modding_resources/WH3/ui_scripting.html)
warns that local UI callbacks changing simulation state can cause a desync. This makes the
order path the first question to settle. The docs are CA-authored material on a community
mirror; the installed copy is the reference for this build. The
[modding knowledge-base search](https://github.com/rehan-remade/universal-modder) found no
relevant multiplayer implementation to reuse.

## What “without UI” can mean here

| Target | Assessment |
|---|---|
| LLMs use structured state and orders, with no image interpretation or mouse control during battle | Plausible extension of our existing bridge, conditional on synchronized orders. |
| Nobody operates the machines; Lua/UI contexts create, join, recruit and ready automatically | Plausible, unimplemented. The interface may still simulate component clicks inside the game; no human desktop operation is required after setup. |
| No UI subsystem, graphics device, desktop session or rendering loop exists | No demonstrated route. Lua runs inside the normal executable; our polling currently depends on its UI loop. Budget for graphics-capable clients. |
| A small dedicated process hosts the simulation and replaces all player clients | No supported executable/API found. Treat this as a separate engine research project. |

Peer-to-peer describes how clients connect; it does not imply a cheap headless server.
The exact WH3 transport and relay behavior have not been traced here. Steam's
[lobby APIs](https://partner.steamgames.com/doc/features/multiplayer/matchmaking) describe
Steam generally, not an interface our Lua mod can necessarily call or a way to construct
a valid WH3 battle session by itself.

For a conservative native 2v2 design, use **four game clients**, each owning one player
army. Each can run one LLM or the existing split-army team. Four clients with two LLMs per
army means eight LLM agents: client count and agent count are different costs.
Two clients on opposite sides, each with two LLMs sharing its army, would already give
LLM teams competing over a real network, but would still be a native 1v1 with split control.

## A small initial architecture

JUDGEMENT: Client layout — Codex, 2026-10-30: draft one isolated graphical client per
player slot, with a session coordinator; multi-client hosts or one client per side change
cost and army boundaries. No hosting design is adopted.

Each game client gets the same build/mod, a legitimate Steam account/license, a persistent
profile and a small local adapter. The adapter emits its permitted observation, validates
orders against its army, and submits them through whichever synchronized path the probe
establishes. Model inference can stay elsewhere; the game GPU need not also serve an LLM.

A coordinator assigns a common match ID, checks versions and rosters, starts the clients,
routes private teammate messages, collects per-client evidence and stops failed sessions.
It need not choose tactics or expose opponents' private observations. Keep evaluator state
out of policy inputs. Separate each client's mailbox and each team's messages; record
native player/army IDs as well as the existing local `f1`/`e1` aliases.

For implementation, follow Farama-Foundation/PettingZoo's
[`pettingzoo/test/parallel_test.py`](https://github.com/Farama-Foundation/PettingZoo/blob/main/pettingzoo/test/parallel_test.py)
for per-agent identity and episode-lifecycle checks. Its synchronous `step` is not a timing
model for this live bridge; an adapter must preserve independent progress at 1x.

Use one region initially, with a functioning virtual display/interactive graphics session
even when nobody is connected remotely. Test that disconnecting remote desktop leaves the
game and callbacks running. Start with one simultaneous match. The existing “one controller
at a time” rule needs a deliberate session-level exception before a multi-machine run;
one supervised coordinator should own all its participants.

Keep Windows for the first probe: the bridge and checkpoint tools target that executable.
The launcher currently runs from WSL, uses `fcntl` and fixed `/mnt/c` paths; copying it onto
a Windows VM is not enough. Either establish the required WSL environment or move the thin
process/mailbox adapter to native Windows. Do not assume WSL2 support on the chosen GPU VM.
Linux/Proton or packing several clients onto one host could reduce cost later, but introduce
additional compatibility and isolation questions before the first network order is proven.

## Draft experiments and decision points

JUDGEMENT: Probe scope — Codex, 2026-10-30: draft tiny base-game Land battles, scripts
before models, two clients before four. Richer modes or checkpoint resets change the work;
these procedures and their repeat counts still need owner agreement before verification.

1. **Get two ordinary clients into a private battle.** Confirm accounts/content, matching
   builds/mods, graphics drivers and 1x battle speed. Manual lobby operation is acceptable
   for this first capability test. Run an experimental read-only observer before giving it
   authority. Compare local alliance/army/player identity with each client's unit cards.
   Include two allied player slots against AI so a non-first local army is exercised.
   Exit: correct identity on both machines, including a host/slot swap.

2. **Test a command from one peer only.** Establish a normal UI-issued move as the native
   reference. Then issue a distinctive Lua move from just one peer while the other only
   observes. Compare both clients' unit motion and native checksums at aligned completed
   ticks, continuing long enough to expose delayed divergence; also inspect the replay.
   Repeat from the other peer and with halt/attack. Do not send identical Lua commands
   separately on both peers: that would hide a local-only mutation.
   Exit: both peers agree on the effect, with no duplicate order or desync.
   Checksums need independent field readings too: our checkpoint work found gaps in them.

3. **If Lua does not replicate, investigate one bounded alternative.** Trace a genuine UI
   move and a Lua move into the existing native input/session code. Try submitting a normal
   player order through the game's multiplayer input queue. Our checkpoint hooks provide
   a starting map, not this missing implementation. An alternative is an identical,
   tick-addressed command log executed by every peer; that requires validated ownership,
   ordering, delivery deadlines and deterministic iteration. Merely copying files or using
   model timers is insufficient. At 1x, late input must follow a declared rule; do not pause
   the battle while waiting for models or a coordinator.
   Exit: a traceable replicated command path, or a report that Lua-only control failed.
   Stop rather than making a rendering rewrite or a new network protocol part of this spike.

4. **Make the full lifecycle unattended.** Inspect create/join/invite/ready screen bindings;
   use shipped context methods where available and internal component actions where needed.
   Reverse engineer the specific missing transition only if ordinary frontend scripting
   cannot reach it. Check roster and slot readback, loading, deployment, ending and returning
   to the lobby. Exercise timeout, wrong mod/build, crash and disconnect. Record each
   attempt once, with results from all peers; preserve engine outcome and disconnect reason.
   A disconnect must not silently become an ordinary tactical loss in the research table.

5. **Grow to allied players, then native 2v2.** Give allied armies distinct scripted moves;
   delay one stream while the other acts. Reject an attempted teammate order. Compare each
   client's visibility against a hidden/revealed unit in game, including allied shared
   sight. Then use four player slots and two opposing teams. Swap host, sides and non-first
   army positions; run fresh sessions rather than relying only on rematches. Check resource
   ownership, team outcome agreement, duplicates and unattended recovery. The engine/UI and
   cross-peer recordings are the independent references; acknowledgements alone do not pass.

6. **Add LLMs after the scripted path works.** Freeze controller versions, latency rules,
   communication and budgets, then run a small demonstration. It establishes integration,
   not team strength. A scored study needs its own agreed question, opponents, side swaps,
   failure treatment and sample size. Existing split-army components are useful here, but
   the model team itself has not yet played live under an agreed check.

For a first repeatable check, propose exercising both command directions, a host swap,
an allied non-first slot, and fresh launches. Choose counts and comparison fields together
before implementing the check. None of these proposals was added to `agreed-checks.md`.
No paid LLM is needed to settle the first five stages' capability questions.

## What the checkpoint work helps with

The [checkpoint agent](checkpoints.md) already locates input/session machinery, native
checksums, replay recording and completed ticks on the pinned Windows executable. That
reduces the cost of tracing a network command and gives useful comparison tools.

It does **not** restore a multiplayer session: its replay handover switches to one live
input provider, without rebuilding peer membership, ownership or network state. Initially,
restart native matches through the lobby. Restoring all peers to the same checkpoint would
be a separate research problem with a simultaneous-handover check. A single-client restore
with two scripted sides can help study policies, but cannot establish native multiplayer.

## Rough costs in USD

These are planning calculations, not quotes or spending approval. Rates were checked
2026-10-30. Engineering/debugging time is the largest uncertain cost.

AWS's [published Windows example](https://docs.aws.amazon.com/solutions/latest/modular-cloud-studio-on-aws/cost.html)
uses **$0.71/client-hour** for `g4dn.xlarge` in its N. Virginia cost table. This is a solution
example, not a live EC2 Price List quote. Its [hardware](https://aws.amazon.com/ec2/instance-types/g4/)
is 4 vCPUs, 16 GiB RAM and one T4. WH3 performance is unmeasured; a larger CPU/GPU instance
may be needed to sustain 1x. Use graphics-capable drivers, not only a CUDA compute driver
([AWS driver guidance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/nvidia-GRID-driver.html)).

JUDGEMENT: Cost workload — Codex, 2026-10-30: examples use 250 GB/client, 10 hours or
30 min/match, $1–2/hour sensitivity, 60 calls/agent and 8k/1k tokens per call. Alternatives
change the bill; these are costing assumptions, not measurements or benchmark limits.

| Item | Two clients | Four clients |
|---|---:|---:|
| Compute for 10 allocated hours at the published $0.71 example | $14.20 | $28.40 |
| One [public IPv4](https://aws.amazon.com/vpc/pricing/) per client, $0.005/hour, 10 hours | $0.10 | $0.20 |
| 250 GB/client [gp3](https://aws.amazon.com/ebs/volume-types/) retained 10 hours, $0.08/GB-month, 30-day approximation | $0.56 | $1.11 |
| Same volumes retained a full month instead | $40 | $80 |
| Extra base-game copies if one existing license is reused, [US list $59.99](https://store.steampowered.com/app/1142710/Total_War_WARHAMMER_III/?cc=us&l=english) | $59.99 | $179.97 |

Use separate accounts and sufficient concurrent licenses; see
[Steam's multiple-client guidance](https://help.steampowered.com/en/faqs/view/48C1-A297-4839-8BB8).
The Windows game lists 120 GB free space, so a small local instance disk alone is insufficient
for the game plus Windows and update headroom. Start with base-game factions to avoid DLC
purchases. Login, activation and VM-image persistence still need a real-client test.

For sensitivity, **$1–2/client-hour** is an assumed allowance for a larger machine, not a
sourced quote. Ten hours then costs $20–40 for two clients or $40–80 for four, before other
items. Installation, lobby waits, debugging and failed matches consume the same allocated
hours. Stopped instances still retain paid volumes; avoid leaving four disks for a month
unintentionally. Bandwidth, snapshots, coordinator, tax and labor are excluded.

For four agents the illustrative workload totals **1.92 million input tokens and 0.24
million billed output tokens per match**. At current
[Anthropic rates](https://platform.claude.com/docs/en/about-claude/pricing):

| Price example | Input/output per million tokens | Inference per match |
|---|---:|---:|
| Haiku 5.5, prompts below 100k tokens | $0.10 / $0.50 | $0.312 |
| Sonnet 5.5 | $2 / $10 | $6.24 |
| Opus 5.5 | $4 / $20 | $12.48 |

These examples do not establish WH3 capability, latency, account access or provider support
in our harness. Input includes history; output includes billed reasoning. No caching or
batch discount is assumed. Eight agents approximately double inference at this workload.
For four clients allocated half an hour, the assumed $1–2 rate adds $2–4 compute per match.
Use that arithmetic rather than treating a ten-hour window as twenty completed battles.

Practical scale: a short scripted two-client pilot costs **tens of dollars in machine time,
plus about $60 if a second license is needed**. Four-player exploration adds about $180 in
licenses if one existing copy is reused. Inference can then be smaller or larger than the
machine bill. Re-quote hosts and choose a bounded pilot budget before provisioning.

## Main risks and when to stop

| Risk | Consequence and response |
|---|---|
| Lua orders mutate only one simulation | The decisive risk. Test one-peer input first; trace the native player-order queue if needed. If no usable route emerges, report Lua-only native control infeasible on this build. |
| Wrong army/resource authority or hidden-state leakage | Invalidates the experiment even if it finishes. Include allied non-first slots and visibility witnesses; do not forward evaluator observations. |
| Graphics/session or CPU limits | A remote-disconnected client may stop updating; the slowest peer can slow the match. Measure simulation time per each host's Windows clock at 1x, not only reported speed flags. |
| Lobby, transport and disconnect failures | Matchmaking/P2P labels do not guarantee cloud connectivity. Test same-region networking, loading, restart and abandoned-session cleanup before adding models. |
| Build, mod or native-hook drift | Pin and record every peer's build/mod; retain signature checks for hooks. Tell the owner about updates; do not silently re-pin. |
| Steam/content availability | Concurrent licenses, login/activation, DLC and GPU quotas can block the second client. Confirm them before building a four-client system. |
| LLM latency and token growth | More clients do not make model decisions faster. Keep live 1x, record input age and applied ticks, and price full histories/reasoning rather than only final orders. |
| Checkpoint expansion | Multi-peer restores could absorb the project before multiplayer works. Fresh lobby resets keep this off the initial critical path. |

If a graphics-free runtime is mandatory, this assessment does not support proceeding as a
small extension: the missing renderer-free runtime/session path is substantial new work.
If unattended graphical clients are acceptable, the best next evidence is the **two-client,
one-peer Lua order comparison**, with a manually created private lobby if necessary.
Cloud orchestration and LLM policy comparisons can follow that result.
