# Native multiplayer tools

Usage reference for the built tools. For current live evidence and outstanding checks, read
[foundation status](multiplayer-control-foundation.md#implementation-status); for future
architecture, read that page's proposed stages. These tools remain unverified under the
repository's hard rule. A command acknowledgement, native submission and peer agreement
are separate observations. `runs/wh3-mp-overnight-20261104/typed_run.py` is local experiment
scratch, not a maintained runner; its typed lifecycle has no live pass past `status`.

## Worker operations

[worker.py](../../src/twwarhammer3/engine/worker.py) documents process ownership, manifests,
acknowledgements and teardown. The coordinator takes one JSON line on stdin per command:

```json
{"client":"A","body":{"operation":"status"}}
```

Start it with `uv run python -m twwarhammer3 coordinator --match M --attempt A1 --clients A,B`.
It prints its URL and per-client token-file paths; keep stdin open. On each game host, use
the same source and mod with that client's token. An owned control worker is:

```bash
python -m twwarhammer3 worker --coordinator URL --token-file F --match M --attempt A1 --client A --mode control --menu --native-adapter --max-minutes N
```

This launches a real game. Use the repository's game window and controller ownership rules.
`--menu` enables typed frontend operations; `--native-adapter` adds the direct readiness
helper and native capture. Both require an owned session; the adapter also requires control
mode. An observe worker accepts no commands, including `status`. `--attach` instead borrows
an existing multiplayer bridge without launching or resetting it and accepts neither flag.
Wait for the worker's `session` event before sending frontend work, and its `adapter` ready
event before direct readiness. The coordinator's hello alone precedes mailbox reset.

The table gives each command's **body**. `S` means the scenario object from
`battle.setup.scenarios()[name]`, not its name string; replace it before serializing JSON.
`open_slot:true` reserves a teammate slot; `false` selects the one-human test bed.

| Body | Route and readback |
|---|---|
| `{"operation":"status"}` | Reports latest observation summary, menu availability and adapter availability; does not act. |
| `{"operation":"create_lobby","scenario":S,"open_slot":true}` | Requires `--menu`; fixed UI steps create the host lobby. Still uses the UI. |
| `{"operation":"configure","scenario":S,"open_slot":true}` | Requires `--menu` and an existing lobby; sets the host and AI armies through context steps. |
| `{"operation":"set_lobby_ready","ready":true}` | Requires `--menu`; reads the lobby flag and toggles only when needed. `false` requests unready. |
| `{"operation":"ready_deployment"}` | Requires `--native-adapter`; calls the engine sender on the game thread, without a component lookup. |
| `{"control":"ready"}` | Existing Lua route presses this client's Start Battle during deployment. |
| `{"control":"leave"}` | Lua calls `QuitToMainMenu`; the worker's `frontend` event witnesses frontend reload. |

Tactical commands still use `{"based_on":SEQ,"orders":[...]}` and allow only unqueued
`move` orders validated against the latest observation. There is no typed join operation.
Frontend step definitions are in [setup.py](../../src/twwarhammer3/battle/setup.py)
(`frontend_steps` in `worker.py` defines accepted bodies).

For Lua controls, `submitted` means the observation acknowledged the request; inspect its
`ack` results and later engine state. Frontend operations report their request's menu-log
completion, or a new battle for lobby readiness. For direct readiness, `submitted` means
the input-stream write offset increased; `refused`/`expired` become `rejected`. Missing or
unknown effects stop the worker. Read `command`, `adapter` and `frontend` evidence events,
not just the coordinator status. The anonymous `end_deployment_execute` count does not
identify which player became ready or show that every peer received it.

The adapter requires deployment phase 4, a current battle interface and a network battle.
Readiness timing rests on JUDGEMENT? `src/twwarhammer3/engine/multiplayer_adapter.js` Ready phase. This guard
has no live run yet; the earlier direct-call evidence used phase 0. The battle-interface
dependency also leaves headless use unproven.

## Passive capture and direct adapter

Run these modules under Windows Python with Frida installed (the existing environment is
`C:/wh3-agent/checkpoint-frida-venv/Scripts/python.exe`), with this checkout's `src` importable.
The caller owns the game PID. Attach before constructing the battle: existing sessions are
not recovered from memory. The passive command is:

```bash
python -m twwarhammer3.engine.multiplayer_probe --pid OWNED_PID --output FRESH_DIR --seconds N
```

It validates the actual executable hash and hook signatures and writes `manifest.json` and
`native.jsonl`. It launches/closes no game and submits no commands. A `STOP` file in the
capture directory requests detach; a zero exit means capture completed, not acceptance.

`engine.multiplayer_adapter` takes the same arguments, loads the passive agent first, then
adds the fixed `ready_deployment` operation. Its stdin accepts:

```json
{"operation":"ready_deployment","request":"UNIQUE_REQUEST_ID"}
```

Prefer the worker's `--native-adapter` integration for control. Its helper writes on Windows
and copies the capture on close to `worker-A/native/` under the attempt directory; coordinator
events are not a replacement for the full per-tick file. Capture events include:

| Event | Meaning |
|---|---|
| `completed_tick` | Tick/checksum after worker join; `phase` is the client-side copy, `sim_phase` the simulated phase. |
| `witness` | Raw unit rows at scheduled ticks and around captured command packets. Layout: `unitRow` in [multiplayer_probe.js](../../src/twwarhammer3/engine/multiplayer_probe.js). |
| `command_packet` | Command id, flags, stream offset and last completed tick; includes engine-generated commands. |
| `end_deployment_*` | Trace from Start Battle through sender, command and execution; execution includes ready count/countdown. |
| `battle_decided` | Engine ending tick and zero-based winning alliance; -1 means draw. |
| `operation_requested`, `operation_result` | Adapter request and its submission/refusal/expiry/unknown effect. |

Passive sender/packet hooks miss the adapter's direct call. Its `operation_result` records
the stream-offset change; the native comparator counts that as a readiness submission.
Raw witnesses include hidden state for evaluation only: never forward them to a policy.
Reinforcement armies are outside this walk; soldier hit-point sums and `sim_phase` still
need live evidence. Tick origins, unit identity and field comparability need peer calibration.

## Compare saved captures (offline)

```bash
uv run python -m twwarhammer3 compare-peers --native A=runs/CAPTURE_A/native.jsonl B=runs/CAPTURE_B/native.jsonl
```

Append `#GENERATION` to a path when its capture contains multiple battles (quote the whole
`A=PATH#GENERATION` argument). `--start T --end U` declares an inclusive completed-tick
interval; otherwise the interval spans all recorded clients' ticks. No nearest-tick match
or floating-point tolerance is used. `--packets A=ID:COUNT` checks a named command id's
submission count; enumerate the intended ids because the engine sends its own commands.
Comparator choices rest on the marked judgements in [peers.py](../../src/twwarhammer3/battle/peers.py)
and the foundation plan's Raw witness choice.

Read the JSON `verdict`: `conflict` means compared evidence differs; `inconclusive` means
evidence is missing/failed or phase comparability is unresolved; `agreed` covers only what
was compared, not synchronization correctness. The CLI exits zero for any readable verdict.
`compare-peers ATTEMPT_DIR` retains the older Lua-observation comparison by `time_ms`; it
does not compare completed engine ticks. `peers.py` documents both schemas and their limits.

Existing component checks: `tests/twwarhammer3/test_wh3_worker.py`,
`test_wh3_multiplayer_*.py` and `test_wh3_native_peers.py`. They exercise guards, bookkeeping
and comparison; they do not establish engine ABI correctness or two-client replication.
