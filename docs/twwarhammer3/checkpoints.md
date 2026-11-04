# Battle checkpoints

Save a running battle at a tick and later continue it from exactly that tick, as often as
needed: for benchmarks and training that start several attempts from one battle state.
The native hooks target 9.0.5 / Steam build 26403568, matching the normal
runtime [pin](integration.md#pins). The agent checks the game's code bytes and refuses
other builds. The agreed Land live-value check and all four declared siege states passed
on this build at `210e356`; historical passes below cover build 25961564.
Create new checkpoints on the updated build; compatibility with old-build replay files is
unverified, and checkpoint-RL library records retain their original executable/agent hashes.
The public release of the same tool for players and modders is
[github.com/nivaldoh/wh3-battle-checkpoints](https://github.com/nivaldoh/wh3-battle-checkpoints)
(v0.1.0, owner-approved 2026-10-25).
That public release still targets build 25961564; the 9.0.5 port here is not a public release.

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

Owner extension, 2026-11-03: use the same live-value rule as siege. Living units must supply
finite numeric morale percent and slow/fast movement capabilities. Only the cached
`units[*].stats` panel is excluded from exact comparison; all other fields and every native
checksum still match exactly. The full raw comparison and panel differences remain in
`checks.json` and the native logs. Movement capabilities do not establish fatigue-adjusted
effective speed. Earlier logs without these getters cannot pass the extended method; the
first strict 9.0.5 attempt stays failed ([log](log.md)). The extended method passed at
`210e356`: `runs/twwarhammer3/checkpoint-check-905-live-values-20261103/`, four completed
and closed launches. Both identical restores match all 2,000 planned native ticks and all
nine live readings each; every required numeric getter is present. The changed control
diverges at tick 1303. Recount and independent review agree; raw panels also match in this
fresh attempt. This establishes the declared Land case, not other scenarios or builds.

Passed at `7b1e2ed` (`runs/twwarhammer3/checkpoint-check-20261025b/`) and, after the merge
and the Replays-list fix, at `6fdb271` (`checkpoint-check-20261025c/`): 0 checksum
mismatches over 2,001 ticks and 9/9 equal readings per restore; the changed restore diverged
from tick 1303; a replay already in the list was set aside and returned unchanged.

## This repository and the public release

The public repository is a separate project with its own history: changes do not flow
between them through git, and a merge, pull or push between the two does not apply.

| Piece | This repository | Public repository |
|---|---|---|
| In-game agent | `engine/checkpoint_agent.js`, with test hooks (off unless a config is passed) | `checkpoint_agent.js`, build-25961564 version without the test hooks |
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
- Native checksums alone do not cover field construction/supplies: manual tower builds
  changed those readings without changing the checksums. Independent field readings are
  required alongside them.
- The Land and declared siege checks passed at their recorded revisions; their results
  do not extend to other maps, armies or equipment combinations.

## Siege check

`tests/twwarhammer3/check_wh3_checkpoint_siege.py` runs three declared cases: Helmgart
defender with one ram/one siege tower, capital attacker with two rams/no towers, and
Helmgart defender with one ram/two siege towers plus field construction and ownership
changes. Each saved state receives two identical restores and one changed-order control.
The field case saves an intact open gate during construction and a late state with a
destroyed gate and changed Key Building/Minor Supply Location owners. Climbing ladders,
mixed units, ammunition, damage and a spell's armour effect and expiry require positive
witnesses. Tower builds are source-only inputs and are not reissued during restores.
Ownership changes are recreated by the same tick-1 script in source and restores. This
tests those scripted ownership states, not storage of arbitrary owner changes as separate
replay inputs or normal capturing.

The owner agreed numeric live morale/speed readings and armour/spell witnesses on
2026-10-25, with cached infocard differences reported separately. The spell target's
armour/effect must match at handover; identical active-effect restores must also witness
expiry and baseline armour. Other units' cached armour stays diagnostic. All live readings
and every planned native checksum must match exactly. The speed getters describe movement
capability; the probe did not establish fatigue-adjusted effective speed. Raw cached
stats remain in the evidence: an earlier open-gate restore failed the original strict
comparison at four of 38 readings despite matching every native checksum and every
other reading field. The native stat-list getter has a refresh cache exceeding two seconds;
this supports a cache-age explanation without proving every stat difference harmless.

Passed on 9.0.5 / build 26403568 at `210e356`:
`runs/twwarhammer3/siege-905-20261103/`, 15 fresh completed/closed launches. All eight
identical restores match 2,400 planned native ticks each and all 194 live readings total;
all four changed-order controls diverge after their orders. Required siege, field,
ownership and spell/expiry witnesses pass. Cached panels differ in some restores and
remain recorded separately. Standalone recount and independent evidence review agree.
The battles were configured unpaused at 1x. Capital post-handover native-message receipt
windows measure about 0.981–0.984 simulation seconds per Windows second; these are receipt
timings, not continuous speed instrumentation. This establishes the declared cases only
and rests on JUDGEMENT `tests/twwarhammer3/check_wh3_checkpoint_siege.py` `CASES` and
`tests/twwarhammer3/checkpoint_siege/ground_fire.lua` ground aim. The separate source-only
manual-tower supplement below has not been rerun on 9.0.5.

Passed at `2e2acbe`: `runs/twwarhammer3/siege-final-20261025b/`, 15 distinct completed
logs (11 fresh launches plus four reused logs with identical runtime, agent and input
bytes). Eight identical restores match all 2,400 planned native ticks each and all 194 live
readings; four changed-order controls diverge after their orders. The standalone
`--recount` command also passes. Coverage rests on JUDGEMENT
`tests/twwarhammer3/check_wh3_checkpoint_siege.py` `CASES` and
`tests/twwarhammer3/checkpoint_siege/ground_fire.lua` ground aim; this establishes these
declared cases only.

The owner's manually selected tower options were recreated as source-only inputs and
saved during construction and after completion: `manual-towers-20261025/`, at `fbdba3b`.
Seven launches, four identical restores match 3,300 planned ticks each and 66 live
readings; both changed controls diverge afterward. The restored runs do not reissue the
builds. The original timed run ended without saving after the owner's clicks; the
recreated choices, balances and construction timers match its recorded samples.

Earlier evidence and retained failures: `runs/twwarhammer3/checkpoint-siege-20261025/`,
`siege-check-20261025*/`; [log](log.md). No paid model calls were used.
