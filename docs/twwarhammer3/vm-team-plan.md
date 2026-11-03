# Native team on the VM: plan

Draft, 2026-11-03, Claude, from read-only research (`runs/vm-team-plan-20261103/`, seven readers,
three drafts, four reviewers). Nothing here is agreed or has run; this page starts no game, VM or
spending. It orders the remaining [native multiplayer](native-multiplayer.md) steps for your PC and
one GCP VM. Labels: checked (read or run on 2026-11-03), read (from a doc), secondary (third
party), inferred.

2026-11-03 evening: S1 ran in a shorter form (identical mods first, no vanilla lobby;
[log](log.md#2026-11-03-first-native-multiplayer-battles-pc-and-gcp-vm)). The next steps
are planned in [mp-next-steps.md](mp-next-steps.md).

## End state

At one frozen revision on build 26403568 (patch 9.0.5), one WSL coordinator runs a private native
custom Land battle. Client A (your PC, main account) and client B (the VM, second account) each hold
one player army in alliance 1 against one built-in AI army. Each army is moved by its own move-only
script through its own worker. A's army moves left and B's moves right, and both screens and both
workers' readings show it; holding back B's script does not stop A; the battle runs unpaused at 1x
to the same engine ending on both clients, with no desync
([step 9](native-multiplayer.md#9-expand-to-native-allied-armies-then-four-clients)). Then the same
again with host and armies swapped. Lobbies are made by hand.

Not included: model agents, halt, attack, step 7's authority and visibility checks, 2v2, lobby
automation, play with no remote viewer, scores. `team_llm_rules` cannot run there yet: it needs
Empire Knights and attacks (`battle/team.py`), and in multiplayer the battle Lua accepts only plain
moves of own units (`twwarhammer3_battle.lua` `apply_order`; checked).

JUDGEMENT: End state — Claude, 2026-11-03: step 9's first scripted case, two host-swapped battles,
no step 7. A model demo, step 7 or a split army changes S2 and the session count; all rests on it.

## Owner decisions

0. **Before 2026-11-04 04:20 UTC: the leftover disk.** A cloud workflow then deletes disk
   `wh3-compat-20261103c` (checked: gcloud, `disk-expiry-summary.json`). It holds Windows, last seen
   running the NVIDIA installer, and no Steam login or game (`session-20261103c/handoff.md`; read).
   "Let it expire" (default) → S1 starts from a new VM. "Keep it" → $0.83 a day plus a runner
   change, to save about 5 minutes of setup.
1. **What "finished" means.** "Step 9's scripted case, two battles" → sessions S1 and S2. "Plus step
   7" → a third session. "Plus a model demo" → a third session after its own card: a move-only model
   controller, your stall rule and an information contract.
2. **Game updates.** Codex re-pinned to 9.0.5 at `21f8447` on your direction; one `rush_nearest`
   smoke there won at 1x (`c6bfb8b`; read). Steam auto-update is on for the PC (your earlier
   choice). "Update on launch only until S2 ends" → a hotfix cannot leave A and B on different
   builds mid-plan. "Leave it" → a hotfix blocks every worker hello and lobby until the next re-pin.
3. **Coordinator exception and PC game windows.** None is granted yet
   ([step 1](native-multiplayer.md#1-agree-the-first-implementationcheck-slice)). Example: "In S1 and
   S2, one session runs one owned worker per host plus coordinators that own no game, and nothing
   else runs on either host; PC windows of 45 min for O2 and 3 h each for S1 and S2" → every step
   can run. "No" → S1 can only do the vanilla lobby by hand. On the PC, only WSL controllers run
   (native and WSL locks do not exclude each other: `native-multiplayer.md`, Platform row).
4. **Mod route** (next section). Proposed: identical files for every Lua case, both clients vanilla
   once, one mixed join attempt. For the vanilla lobby, A's startup-skip movie pack leaves `data/`,
   so the startup movies play again (~131 s: `integration.md`, Packs and loading; read).
5. **Cloud money: set.** You allowed $10 for now and asked to keep costs low (2026-11-03; read
   here as a new allowance from $0). S1 (≤2.75 h, ≤$3.75) and S2 (≤3 h, ≤$3.39) at the $1.131/h
   quote ([costs](gcp-client-setup.md#costs)), each with $1 held back (rests on JUDGEMENT
   `scripts/wh3_gcp.py` Reserve), total ≤$9.14. Still yours: keeping S1's disk ≤24 h for S2, as
   you directed for the retry (branch `gcp-retry`, `owner-direction.md`; read). Then S2 must start
   within 21 h of S1's creation, and a failed S1 deletes the disk. If that zone has no free L4 by
   then (9 of 11 creates so far were stockouts; checked: both `provision/state.json`), S2 downloads
   the game again: either battle 2 moves to a later session beyond this $10, or S2 runs ≤4 h
   (3.8 h × $1.131 + $1 = $5.30; with S1's $3.75 + $1 that is $10.05, so only if S1's bill
   comes in lower or you allow it).
6. **Units: set to a restricted set.** You said a more limited set is fine (2026-11-03). The second
   account has only the Boris Todbringer DLC, which does not open every base-game faction, so the
   Khorne fixture (`native-multiplayer.md`, step 0) is out. Proposed: two
   `wh_main_emp_inf_swordsmen` per army (the pilot's units; rests on JUDGEMENT? Diagnostic roster
   update), Middenland on B, Empire on A, no lord, a base-game Land map; S2's AI army is two
   Swordsmen deployed far off. Checks then cover these units only. Whether a Boris-only account can
   play multiplayer is undocumented (its [store page](https://store.steampowered.com/app/3589670/)
   names only Immortal Empires; checked): S1 step (2) checks it, unless you prefer to sign that
   account into Steam on your PC first and open a lobby alone ($0; switches your PC's Steam login).
7. **Lobby: friends-only, by invite.** The two Steam accounts are already friends (you, 2026-11-03).
   No public lobby (step 8; `runs/twwarhammer3/native-multiplayer/lobby-static-audit.md`; read).
   How WH3 handles the invite is unknown (`references.md`, ISteamMatchmaking).
8. **Worker link (S2 only)** ([plan](native-multiplayer.md#proposed-worker-connection)). "Tailscale"
   → needs an account. "Reverse SSH forward (`-N -R` with keepalive) inside the pilot's IAP tunnel
   (`session-20261102b/remote.py`; checked)" → no account, untested; IAP closes connections idle
   for 1 h ([IAP](https://docs.cloud.google.com/iap/docs/using-tcp-forwarding); secondary).
9. **Licence: fine** (you, 2026-11-03).

## Modded and unmodded clients

The VM does not have to be unmodded. `prepare_runtime` (run by `launch`, `play` and owned workers)
installs the same mod pack, mod list and startup-skip movie pack on any host
(`engine/runtime.py`; checked). The first pilot did exactly that on the VM: the same pack hash
`51c54357…` as your PC, in a single-player battle (`session-20261102b`; checked). What we know:

- Each WH3 client logs a multiplayer version with five parts, `protocol, build, checksum, mod,
  data` (checked: your PC's `mp_log.txt`, copy in `runs/vm-team-plan-20261103/`). The game's text
  has join errors "Incompatible mod version", "Incompatible data" and "Host's game version differs
  from yours" (checked: `local_en` strings). Which field causes which error is inferred.
- `mod=0x1ec02ea8` in all four logged modded launches, across three builds and three different
  pack contents (checked; which pack each launch loaded is inferred), so `mod=` may not hash the
  pack's bytes. There is no log line from an unmodded launch. The game's `modified.log` lists the
  movie pack as an unknown file and our pack as a mod.
- Community reports (mostly multiplayer campaigns, some WH2) agree that players need the same mods
  to join; none says script-only or local packs are exempt (secondary). One WH3 player's advice
  ([Steam thread](https://steamcommunity.com/app/1142710/discussions/0/4302697675601825934/), 2024;
  secondary): with identical `modified` logs, the remaining causes are a movie-type mod in `data/`,
  a different mod version or a different game version. No source covers custom battles.
- CA's campaign library warns that changing a faction's state on one machine is likely to desync
  (checked: `lib_campaign_manager.lua`; for battle orders, inferred). Checkpoint restores without
  the Lua moves matched their source (read), which suggests Lua orders may travel as game commands.
- Unknown: the unmodded version line; whether the movie pack enters `data=`; whether the Boris-only
  account can play multiplayer; whether the game admits two identically modded clients; whether a
  Lua move from one client reaches the other; B's rosters and slots.

Options, best first:
1. **Identical files on both**: same revision, mod pack, mod list, movie pack and build. The only
   route we control.
2. **Both vanilla**: the [step 3](native-multiplayer.md#3-prove-ordinary-native-multiplayer-before-the-mod)
   baseline, no team control.
3. **Mixed** (your case): one join attempt shows the game's answer; no use for the team itself.
4. **The game's own mod route** (CA launcher profile or a Workshop item): no source says it is
   checked differently (inferred); publishing or a profile change needs your approval.
5. **Changing the game's checks**: the exe holds switches named `mp_mod_checksum_pass` and similar
   (checked: strings in `Warhammer3.exe`; whether a retail build reads them is unknown), or hiding
   packs. This gets around the game's own check (EULA §7(e)-(f)); not recommended, yours to decide.

JUDGEMENT?: Mod route and parity — Claude, 2026-11-03: 1 for every Lua case, 2 once, 3 as one join;
parity compared by hand, never refusing. Starting from 3-5 changes which sessions show team control.

Cheapest test that decides it: O2 ($0) shows which version fields our files change; only a real
lobby decides admission, so S1 tries vanilla, then mixed, then identical. (A second PC with WH3
would do the same at $0.) If identical is refused while vanilla joins: save the message, both
version lines and the parity readback; the Lua route stops there, and the choices are option 4, the
native order queue ([step 6](native-multiplayer.md#6-if-necessary-trace-one-bounded-alternative)) or
staying with single-client teams ([§9 D](multi-agent-plan.md#d-single-client-steps)). If even
vanilla fails: spend 10 minutes on checks, save the logs, end the session.

## Steps

O steps are offline or on your PC at $0; S steps are paid VM sessions. All battles run unpaused at
1x. Before O2, S1 and S2 the assistant checks that no other game job runs and commits an Active-work
line. From O3's source archive until each session's export, nothing lands in main that touches
`play`'s source scope (AGENTS.md, Commands), and the worker reads HEAD back before each hello. Each
paid session ends with export, deletion and an inventory readback ([cleanup](../cloud.md#cleanup));
the money figures leave out traffic and tax.

JUDGEMENT?: Session grouping — Claude, 2026-11-03: a single-player worker move in O2, two paid
sessions, S1's disk kept ≤24 h, O4 only after S1's probe. O4 before S1, or one long session,
changes cost and order.

**O1. Close the retry record** (assistant; you approve the commits, 5 min; no game). Now: correct
"GCP retry VM running" in `state.md`. After 04:20 UTC, with no play job running (the branch touches
`configs/twwarhammer3/`): land `gcp-retry` (`f038dc5`), resolving its conflicts in
`owner-direction.md` and `state.md`. Exit: empty instance and disk lists, support resources listed,
`check.py` passes; nothing billable left. Stop: a disk remains → report it.

**O2. Your PC on 9.0.5** (assistant; needs decision 3; 45 PC minutes, 10 of yours). Three launches
to the main menu, saving `mp_log.txt` and `modified.log` after each (the game overwrites them): (a)
`twwarhammer3 launch`; (b) Steam, no mod list; (c) as (b) with the movie pack moved out of `data/`.
Then (d): a coordinator for A only and an owned `worker --mode control`; you start a single-player
battle and the assistant moves one unit about 30 m. Exit: if `mod=` differs between (a) and (b),
mod lists must match; if `data=` differs between (b) and (c), the movie pack must be on both clients
or neither; if neither changes, only a lobby can tell. (d) passes if the worker reports `submitted`
and the unit moves: the owned worker and control mode have then run once live, in single player
(never before: `native-multiplayer.md`, Implementation status). Stop: (d) fails → fix it before S1.

**O3. S1 kit** (assistant, with a reviewer rerunning each check; you review the S1 card, 15 min; no
game). (a) A `git archive` of the frozen revision; check: its Windows `expected_manifest()` equals
WSL's, and a copy with Windows line endings differs. (b) A parity readback per host, since the hello
compares packs built from each checkout, not the installed files (`engine/worker.py`; checked):
build, exe, mod and movie-pack hashes, mod list, extra files in `data/`, DLC depots, the version
line and `modified.log`; check: a changed pack byte, a moved movie pack and another mod list each
show up. (c) Modded clients use the owned worker's session. (d) A recorder for B: a coordinator on
the VM and an owned observe worker (observe drops all orders: battle Lua; checked). (e) Retry kit,
fresh price quotes (the current ones expire 2026-11-04 00:38 UTC), retention scripts. Exit:
`check.py`, (a) and (b), offline only. Stop: a check fails.

**S1. Paid: lobbies and the first Lua move** (≤2.75 h). Needs decisions 1-4 and O1-O3.
Money: ≤2.75 h × $1.131 = $3.11, plus the kept disk ≤18.25 h × $0.035 = $0.64: ≤$3.75. You: about
90 min including Steam Guard; PC game about 1 h, A windowed.
1. 0:00-1:20: create the VM; you log in over RDP and to Steam and start the download (the pilot
   took 74 min from creation; checked); set B's updates to launch-only.
2. B launched from Steam: save its version line; you set Low graphics, open a lobby alone (decision
   6) and quit; parity readback; A as in O2 (c).
3. Vanilla lobby with A hosting: check that alliance 1 offers a second player army and an AI army;
   then the opposing fixture, one ordinary UI move from each side; you play it to its ending.
4. A relaunched as an owned control worker; B, still vanilla, tries to join once (skip after 1:55).
5. B relaunched as an owned observe worker; parity readback; identical-mod lobby; after 60 s idle
   the assistant moves A's test unit about 30 m to an empty point; you play it to its ending.
6. From 2:25: export, delete the VM.

Exit (proposed): (3) joined, both moves seen on both screens, one ending; (4) joined, or refused
with its text saved; (5) joined, parity equal, A's unit moves on both screens and B's reading shows
it ≥20 m toward the point within 30 000 ms of battle time after A's acknowledging observation, no
desync, one ending; B's time ratio recorded. This gives unverified evidence, one battle each, with A
hosting, on an unchecked host: of admission in the three cases, and of one client's Lua move
reaching the other. It says nothing about at-most-once delivery or B's moves. Stop: builds differ →
no lobby; (2) refused or (3) fails → 10 minutes, save logs, end; (5) refused → the fallback above;
(5) moves A's unit on A only, or desyncs → the Lua route fails on this build (step 5).

JUDGEMENT: S1 order and probe — Claude, 2026-11-03: vanilla, mixed, identical with the probe; 30 m
seen ≥20 m within 30 s of battle time; host check in S2. Another order or bound changes S1.

**O4. Link, drivers, S2 kit** (assistant, only if S1's probe passed; you review two cards, 20 min).
(a) The worker link (decision 8); the token copied with `gcloud compute scp --tunnel-through-iap`,
never printed. (b) One move-only driver per client in WSL, like `team.py`'s `_MoveOnce`, reading
only its own client's latest observation minus `HIDDEN_KEYS` (`protocol.py`; workers send
evaluator sections too: `engine/worker.py`; checked). Planted faults that must fail: A's order sent
to B, a stale `based_on`, B's silence blocking A, B's data or `native` section given to A. (c) The
`b39a03d` fake-game run (`runs/wh3-native-mp-20261030/`) repeated on Windows over the link, plus a
wrong token. (d) A runner path that boots from the kept disk. (e) A new archive. Exit: `check.py`
and (c), offline only. Stop: a planted fault passes.

JUDGEMENT?: Driver at the coordinator — Claude, 2026-11-03: both scripts in WSL. B's on the VM cuts
link delay from B's moves but adds a policy host; S2's timing evidence rests on it.

**S2. Paid: host check, link, team battles** (≤3 h). Needs S1's exits, O4, an agreed card and the
kept disk. Money: ≤3 h × $1.131 = $3.39. You: about 80 min, maybe Steam Guard again (inferred); PC
game about 1.5 h.
1. Create the VM on the kept disk, copy O4's archive, read the build back.
2. With A's game closed, the [agreed host check](gcp-client-setup.md#5-one-client-test) on B (25
   min; you may click Start Battle). Keep RDP reconnects few: NVIDIA known issue
   [3583766](https://docs.nvidia.com/vgpu/20.0/known-issues/bug-3583766-multiple-rdp-reconnections-use-all-frame-buffer.html)
   reports GPU memory running out after repeated reconnects on Server 2022 (checked).
3. The fake-game run from the VM.
4. Battle 1, A hosting, link hello read back: both armies in alliance 1 (B second), both in
   control. Phases: 60 s idle, A-only move, B-only move, A left and B right together, B's script
   held 10 s while A moves; then to the ending.
5. Battle 2: fresh launches, host and armies swapped.
6. Export, delete the VM and the disk.

Exit (proposed; this is the end state): the host check passes by its agreed procedure (for that VM
configuration only); no lease lapses; in both battles each phase moves only the named army, on both
screens and in both workers' readings; `compare-peers` compares ≥30 idle-phase times with no
mismatch (fewer is "unavailable", not a pass); no desync; holding B does not stop A; one ending.
Unverified evidence, two battles, one per host direction; catching misrouted orders rests on O4's
planted faults. Stop: a move reaches only one client, the wrong army moves, or a desync; a failed
host check → battles only if the card says so.

JUDGEMENT?: Phases — Claude, 2026-11-03: steps 4, 5 and 9 as phases of two battles; 60 s idle, ≥30
compared times, B held 10 s. A battle per step avoids carry-over but costs a session; S2 rests on it.

## Unverified at the end

Only the GCP host check is agreed, and only for the VM configuration where it passes. The O2-O4, S1
and S2 exits verify nothing until you agree them, and then only at the revisions where they passed;
this page changes neither the [agreed checks](../agreed-checks.md) nor the benchmark. Each case
rests on one or two battles, one build, one account pair and one fixture. Still open: at-most-once
delivery, observer passivity, step 7, halt, attack, other units and maps, latency, play without a
viewer, 2v2, strength, and the actual GCP billing. This plan rests on the JUDGEMENT markers in
`native-multiplayer.md` (Capability fixture, Probe scope, Worker link, Verification contract, Cost
workload), `gcp-client-setup.md`, `cloud.md` (Cleanup), `scripts/wh3_gcp.py` (Quote age, Reserve),
`engine/worker.py`, `engine/mailbox.py`, `engine/link.py` and `battle/peers.py`.
