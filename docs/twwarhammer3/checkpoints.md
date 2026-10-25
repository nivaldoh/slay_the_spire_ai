# Battle checkpoints

Save a running battle at a tick and later continue it from exactly that tick, as often as
needed: for benchmarks and training that start several attempts from one battle state.
Steam build 25961564 only; the agent checks the game's code bytes and refuses other builds.
The public release of the same tool for players and modders is
[github.com/nivaldoh/wh3-battle-checkpoints](https://github.com/nivaldoh/wh3-battle-checkpoints)
(v0.1.0, owner-approved 2026-10-25).

## How it works

The battle simulation is deterministic: the same setup and inputs, tick by tick, give the
same battle (the game's replays rely on this). A checkpoint is the game's replay file
written mid-battle (setup and every input so far) plus the Lua random seed at tick 1.

A restore opens that replay from the Replays menu. `engine/checkpoint_agent.js` then:

- recognises it (the replay's last recorded checksum matches the checkpoint record) and
  clears the battle's replay flag right after the input session is built, so the interface
  and battle scripts start as in a live battle (countdown clock, unit cards, our battle
  mod). The game's `debug_replay` switch, which makes the interface's replay test answer
  "live", is set for that battle too;
- sets the tick-1 Lua seed, so scripts draw the same random numbers;
- rebuilds fast with inline ticks (the engine's own fast-forward path) until 50 ticks before
  the checkpoint, checking every tick's native checksum against the replay's stored one;
- at the checkpoint tick, replaces the replay input with live input and makes the loaded
  replay the battle's recording, so the restored battle can be saved again.

The owner allowed the rebuild to run faster than 1x before the handover (2026-10-25); from
the handover on the battle runs at 1x.

`battle/checkpoint.py` runs a source battle or a restore through the normal harness, with
saves, Lua (orders, a battle script) and readings at exact completed ticks, and compares a
restore with its source. A restore opens the first entry of the Replays list, so for its run
the other replays wait in `replays/checkpoint-aside/` and are put back afterwards; the
check then moves its own checkpoint replay into its output folder. Frida runs under a Windows Python with `frida==17.*` installed
(`checkpoint.FRIDA_PYTHON`, `C:/wh3-agent/checkpoint-frida-venv`).

## The check

`tests/twwarhammer3/check_wh3_checkpoint.py` (agreed by the owner, 2026-10-25): a source
battle with a tick-1 battle script and orders before and after a checkpoint at tick 1200;
two restores with the same later orders; one restore with a changed order at tick 1300.
It passes when both restores match the source on every tick's checksum and every reading
(positions, men, hit points, ammunition, morale, abilities, clock, the script's timers,
orders and random draws), and the changed restore diverges after its changed order.
Passed at `7b1e2ed` (`runs/twwarhammer3/checkpoint-check-20261025b/`) and, after the merge
and the Replays-list fix, at `6fdb271` (`checkpoint-check-20261025c/`): 0 checksum
mismatches over 2,001 ticks and 9/9 equal readings per restore; the changed restore diverged
from tick 1303; a replay already in the list was set aside and returned unchanged.

## This repository and the public release

The public repository is a separate project with its own history: changes do not flow
between them through git, and a merge, pull or push between the two does not apply.

| Piece | This repository | Public repository |
|---|---|---|
| In-game agent | `engine/checkpoint_agent.js`, with test hooks (off unless a config is passed) | `checkpoint_agent.js`, the same code without the test hooks |
| Player command line (`save NAME`, restore from Replays) | not here | `wh3_checkpoints.py` |
| Harness runs, comparison, agreed check | `battle/checkpoint.py`, `check_wh3_checkpoint.py` | not there |

A fix to the agent made here must be copied there by hand, leaving out the test hooks; the
command-line tool can only be changed there. Before a new public release, run the agreed
check here and a manual save-and-restore with the command-line tool; publishing is the
owner's decision each time.

## Limits

- Real-time (wall-clock) script timers are not reproduced; our bridge mod starts fresh
  after a restore. The loading screen shows the starting armies (parked by the owner).
- Readings through Lua lag the simulation while it runs faster than 1x; compare them at 1x.
- Tested in custom land battles only; the evidence and its history are in the
  [log](log.md) (2026-10-25) and `~/wh3-checkpoint-lab/FINDINGS.md`.
