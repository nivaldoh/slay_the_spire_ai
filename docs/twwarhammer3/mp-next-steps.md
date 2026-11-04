# Native multiplayer: plan for the next three steps

Draft, 2026-11-03, Claude, after the first two PC + VM battles
([log](log.md#2026-11-03-first-native-multiplayer-battles-pc-and-gcp-vm)). Nothing here is
agreed or has run. It plans three steps: (1) set up and start a match with no owner clicks,
(2) stop dropped observations and keep both clients' observation times equal, (3) a battle
hosted by the VM. Labels: checked (read or run on 2026-11-03), read (from a doc), inferred.

Order: step 2 and the offline parts of steps 1 and 3 first ($0, no game), then one PC
game window for the lobby map (step 1, $0), then one paid VM session that tests joining
and runs the VM-hosted battle (steps 1 and 3 together). The kept game disk
`wh3-mp-20261103d` is deleted at 2026-11-06 21:09 UTC, so that session must start before
then or the disk must be kept longer (decision 5).

JUDGEMENT?: Session grouping — Claude, 2026-11-03: offline work, one $0 PC window, then one
paid session for the join test and the VM-hosted battle. A separate join session costs a
second boot and VM hour; the cost figures below rest on this.

## Implementation status (2026-11-03)

Built and on main (`ea6f1c6`, `3f0da5b`, `256936d`); each new test fails on a planted wrong
version; nothing here is verified under the hard rule.
- Step 2: delete-sharing reads on Windows (`gameai.windows.open_shared`; opt-in test passed on
  the PC); the multiplayer observation grid. Live on the PC ($0, one human and an AI,
  `runs/twwarhammer3/native-multiplayer/tb2/`): regular readings stayed on the grid around
  three acknowledgements (one off-grid, at 29.6 s). Two clients sharing times: needs the VM.
- Step 1: `worker --menu`, `ready` (presses only a shown Start Battle, at most once), lobby
  map (`lobby-map-20261103/`), `map_steps`/`army_steps`/`host_steps`/`join_steps`,
  `lobby_ids`. Live on the PC: host_steps (with the open slot removed) went from the main menu
  to Ready with no clicks; the first `ready` pressed a hidden button of the same name (fixed);
  the second started the battle 0.5 s after the press. Joining: needs the VM.
  Corrections from the map: the host dialog has no friends-only setting (our lobbies were
  public with a password); AI slots need a lord even with "Start without Lord(s)".
- Step 3: `wh3_gcp.py --disk` (offline tests), cap $10. Session kit and brief:
  `runs/twwarhammer3/gcp/next-session-kit/` (auto-logon, one-coordinator starter, join map).
  Stopped before the VM, as the owner asked.

## Owner decisions

Answered 2026-11-03 ([direction](../owner-direction.md)); implementation not started:
1 yes ("Sure"); 2 yes; 3 left to Claude, who takes the proposed reverse SSH forward and
falls back to two coordinators with a two-directory `compare-peers`; 4 yes ("Seems fine");
5 keep the disk for now. The disk's deletion job is still armed for 2026-11-06 21:09 UTC;
cancelling or moving it is a cloud change not yet made.

JUDGEMENT: Worker link — Claude, 2026-11-03, delegated by the owner ("do whatever works
best"): reverse SSH forward in the IAP tunnel; two coordinators if it fails. Tailscale
would add an account; step 3's single-coordinator evidence rests on this.

1. **Control clients press their own Start Battle.** In multiplayer the battle Lua refuses
   `control: start` (checked: `twwarhammer3_battle.lua` handles `message.control`), so you
   clicked deployment's Start Battle on both clients. Proposed: in `control` mode only,
   during Deployment only, a `ready` request clicks that client's own `button_battle_start`
   (never `end_current_battle_phase`). "No" → you keep clicking it on both.
2. **Observation times in multiplayer.** Proposed: a fixed time grid in the multiplayer modes
   only (step 2). Single-player timing stays as it is, but edits to `src/gameai/` or
   `src/twwarhammer3/` outside the report's PRESENTATION files (these edits are) change the
   harness fingerprint, so later report groups split from earlier ones.
3. **Worker link for step 3** (plan decision 8). Proposed: one coordinator in WSL; the VM's
   worker reaches it through a reverse SSH forward inside the IAP SSH tunnel already used
   for the VM (no account; untested). "Tailscale" → an account. "Neither" → two
   coordinators as on 11-03, and `compare-peers` learns to read two directories.
4. **Auto-logon on the VM.** Proposed: Sysinternals Autologon for `wh3`, so after a boot
   the game runs in the console session without you opening Remote Desktop. It stores the
   VM's Windows password as an LSA secret that an administrator can read. Whether the
   console session draws the game with nobody connected is unknown; step 3 checks it.
5. **Disk lifetime.** The session must start before 2026-11-06 21:09 UTC, or say how many
   more days to keep the disk (about $0.83 a day).

## Step 1: lobby and start with no owner clicks

Goal: from two launches to both clients in a live battle with no owner input except, at
most, one Remote Desktop login per VM boot.

What we know (checked):
- The frontend script (`script/frontend/mod/twwarhammer3_frontend.lua`) runs click, key,
  dump and context-command steps from `menu.json`, but only when `session.json` has
  `"menu": true`. The worker's session has no `menu` field, so it stays inert.
  `twwarhammer3 menu` only needs a session file (no lock), so it works next to a worker.
- Single-player setup (`battle/setup.py`, `scenario_steps`) already sets each slot's
  subculture, faction and units through `CustomBattleLobbyContext.PlayerSlotList.At(n)`
  context commands. Whether the multiplayer lobby uses the same context is unknown.
- The host's `mp_log.txt` logs `created lobby id <id>` and `Steam ghost lobby created ...
  -> <id>`. In battle 2 the VM joined exactly the logged id (`10871584541481719461`) and the
  same ghost id (`109775243384324287`, which has the form of a Steam lobby id).
- Steam documents that friends-only lobbies are not in lobby searches (references.md,
  ISteamMatchmaking), yet in battle 2 the VM's game list showed ours (`found complete game
  10871584541481719461 (host Snaaaake) (compatibility: ok)`) and the VM joined it 5 s
  later. Whether that lobby was friends-only, and how it was listed, is unknown.
- In battle 1 the host's Steam overlay opened 37 s before the VM joined (an invite,
  inferred); the VM's log for that battle was not kept. Whether WH3 acts on an accepted
  invite is unknown.
- The host logs `created lobby id` several times per session (three in battle 1, two in
  battle 2, one at battle start with no ghost line), so a reader must pick the lobby
  the joiner sees.

Changes:
1. `worker --menu` (owned mode only) adds `"menu": true` to the published session. Test:
   the session has `menu` only with the flag; a planted worker that always sets it fails.
2. A $0 lobby map on the PC (one game window, about 45 minutes, no owner clicks): under
   `worker --menu`, dump the UI tree at each screen (main menu, multiplayer, custom battle,
   host dialog with its friends-only setting, lobby: slots, add AI, armies, ready, start)
   and test whether the lobby exposes `CustomBattleLobbyContext`. Also try one thing:
   starting a multiplayer battle with one human and one AI slot. If the game allows it,
   the PC alone is a $0 test bed for steps 1 and 2 (`is_multiplayer` true).
   Dumps go to `runs/twwarhammer3/native-multiplayer/lobby-map-<date>/`.
3. Step builders in `battle/setup.py`: `host_steps(scenario)` (host a friends-only lobby,
   set map, add the AI slot and its army, set the host's own army, wait for the second
   player, ready, start) and `join_steps(side)` (set the joiner's own slot army, ready).
   Each slot's army steps move out of `scenario_steps` into one shared function; a test
   checks `scenario_steps` output is unchanged for every entry of `scenarios.json`.
4. `lobby_ids(text)` reads the host's newest `mp_log.txt` and returns the last lobby id
   that has a ghost line (the lobby before battle start), with its ghost id.
5. Join on the second client, tried in this order in the paid session (the first that
   works is kept): (a) the game's own game list, as in battle 2: frontend steps open it,
   wait for the entry whose id `lobby_ids` returned, and join (its UI path comes from a
   dump taken on the VM in that session, since the PC alone cannot list its own lobby);
   (b) `steam.exe steam://joinlobby/1142710/<ghost id>/<host SteamID64>` with the game
   running (inferred to send the same event as an accepted invite); (c) launching the game
   with `+connect_lobby <ghost id>` (each start logs `Triggered platform launch invite`,
   so it looks for launch invites); (d) an invite sent by the host's frontend steps, if
   the lobby map finds an invite control.
6. Decision 1's `ready` request in the battle Lua, refused in `observe`, outside
   Deployment and in single player. Lua stub tests for each refusal.

Exit: one battle from both launches to Deployed on both clients with no owner clicks,
lobby settings read back on both. Stop: no join route works → keep the manual lobby,
save each route's log lines, and the rest of step 3 still runs with your clicks.

JUDGEMENT?: Join order — Claude, 2026-11-03: the game list first (seen working once), then
the Steam join link, the launch argument and an in-game invite. Another order changes which
route a short session reaches.

## Step 2: dropped observations and drifting times

What we know (checked):
- Dropped write: the VM's mod logged `rename failed: observation.json.tmp: File exists`
  once in each battle (107.3 s in battle 1, 117.9 s in battle 2). The Lua `publish` removes
  `observation.json` then renames the temporary file onto it. Inferred cause: a native
  Windows reader held the file without delete sharing at that moment (the worker's
  `Mailbox.read_observation` uses a plain Python `open`; so did the session's
  `b-obs.ps1` reads). On the PC (Windows 11, native Python, no game) a plain `open` reader
  reproduces it: the remove fails (error 32) and the rename raises `FileExistsError`
  (WinError 183, which the Lua logged as "File exists"); with `CreateFileW` and delete
  sharing both succeed and the new file is in place
  (`runs/twwarhammer3/native-multiplayer/share-test/`). Server 2022 is untested. The PC's
  mod.log was not saved; its observation stream has no gap over 1.2 s, while the VM's has
  one at each failure (106.1→108.5 s and 116.7→119.1 s).
- No acknowledgement is lost: every observation carries `orders = state.applied` until the
  next request, so the next observation still has it.
- Drift: an acknowledgement forces an observation and the tick loop then sets
  `next_observe_ms = now + observe_ms`, so each client's times move with its own orders.
  In battle 2 the clients shared times only up to 46.5 s, before any move.

Changes:
1. On native Windows, `read_observation` opens the file with `CreateFileW` and
   read, write and delete sharing (`ctypes`, then `msvcrt.open_osfhandle`). A Windows
   opt-in test (`GAMEAI_TEST_WINDOWS=1`) holds the file open while another handle removes
   and renames onto it, the way the Lua does; the current `open` fails it (as the PC check
   above did). Run it again on the VM (Server 2022) at the start of the paid session. If
   delete sharing does not free the name there, fall back to the Lua republishing on the
   next 200 ms poll.
2. In the multiplayer modes only, the regular observation keeps a fixed grid: the next
   time advances by `observe_ms` from the previous grid time, and a forced observation
   (acknowledgement) is published without moving it. Both clients' grids then start from
   the same battle clock. Lua stub test: forced publishes at arbitrary times leave the
   regular times on the grid; the current reset behaviour fails it.
3. `compare-peers` then compares grid times; forced ones appear in its `only` lists.
   With decision 3's single coordinator nothing else changes; with two coordinators,
   `compare-peers` takes two attempt directories instead of a hand-merged manifest.

Exit (offline): `check.py` passes, the Windows test passes on the PC, and both planted
versions fail. Exit (live, in step 3's battle): no `rename failed` line, and at least 90%
of grid times during the moving phases are compared, with no difference.

JUDGEMENT?: Grid scope — Claude, 2026-11-03: the fixed grid only in multiplayer modes, so
single-player observation timing and the benchmark stay unchanged. Changing it everywhere
would alter what every policy sees; decision 2 rests on it.

## Step 3: a battle hosted by the VM

Goal: the 11-03 battle-2 phases with the VM hosting and slot order swapped, each client's
army moved by its own driver, played to an ending the engine reports on both clients.

Changes before the session (offline):
1. `scripts/wh3_gcp.py --disk wh3-mp-20261103d`: boot that disk in its zone (us-west1-c)
   with `--disk=name=...,boot=yes,auto-delete=no`, no image and no bootstrap script; the
   backup workflow deletes the VM only, and the disk's expiry workflow stays as armed.
   `test_wh3_gcp.py`: the create command has no `--image`, keeps the disk, uses the disk's
   zone; a planted `auto-delete=yes` fails. Only one zone can boot this disk: on a stockout,
   retry every 10 minutes for at most 1 hour, then stop (moving zones needs a snapshot,
   which costs extra and needs your yes).
2. Decision 3's link: an `ssh -N -R 127.0.0.1:18080:127.0.0.1:<port>` with keep-alive
   inside the IAP SSH tunnel; B's worker uses `--coordinator http://127.0.0.1:18080`.
3. One driver script for both clients (from today's `phases.py`), sending through the one
   coordinator and reading only each client's own observations.

Session (paid, at most 2 hours):
1. 0:00-0:15: create the VM from the disk; read back build and manifest; run step 2's
   Windows test; set auto-logon (decision 4) and Steam start at logon; reboot.
2. 0:15-0:30: confirm the console session shows the game with nobody connected: one
   screenshot and the clock of a short single-player battle. If it does not draw, you log
   in over Remote Desktop once, as on 11-03.
3. 0:30-0:45: link hello from the VM's worker; step 1's join routes in order.
4. 0:45-1:30: the battle: B hosts (Middenland, slot 0), A joins (Empire), one AI army
   placed close enough to fight. Phases: 60 s idle, A-only move, B-only move, both
   together, B's driver held 10 s while A moves, then both armies advance on the AI army
   until the engine ends the battle.
5. 1:30-2:00: export, delete the VM (the disk stays until its expiry), inventory readback.

Exit (proposed): each phase moves only the named army on both clients; `compare-peers`
compares at least 30 grid times while units move, with no difference; holding B's driver
does not stop A; the engine reports the same ending on both clients; no desync line.
Evidence, one battle, not verification. Stop: builds differ → no lobby; a move appears on
one client only, or a desync → save logs and stop the battle part.

Money: at most 2 h × $1.131 = $2.26, plus the $1 reserve; the quote dates from
2026-11-03 00:38 UTC and needs a refresh first. Of the $10: about $2.06 compute on 11-03
(quote, unreconciled), about $2.7 storage for both disks until they expire, this session
at most $3.26, so about $8.0.
Your time: 0-10 minutes if auto-logon and joining work; otherwise about 15 minutes of
Remote Desktop and lobby clicks, as on 11-03.

JUDGEMENT?: Step 3 exits — Claude, 2026-11-03: at least 30 compared grid times while
moving, B held 10 s, an engine ending. Other bounds change what this battle shows.

## Later: a multiplayer-friendly mod API

Owner, 2026-11-03 ([direction](../owner-direction.md)): investigate changing the Lua side
(the mod, its API, possibly the game's script hooks) so actions such as Start Battle, lobby
setup and joining are exposed directly instead of found and clicked in the UI. The mod was
built for single player; on 11-03 a multiplayer `ready` pressed a hidden button of the same
name, the lobby needed UI paths mapped by hand, and an AI slot rejected "no lord". Questions
to answer first: which engine or context functions perform these actions without the UI;
which of them stay local to one client in multiplayer (and which would desync); and how to
test them without a second client (the one-human multiplayer battle on the PC). Not started.

## Not included

The agreed host check on the VM (25 minutes; add it to the session if you want it), 2v2,
attack and halt orders in multiplayer, the step 7 authority checks, model controllers, and
an agreed repeatable check for any of the above.
