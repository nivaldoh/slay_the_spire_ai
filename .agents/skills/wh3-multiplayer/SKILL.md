---
name: wh3-multiplayer
description: Use WH3 native multiplayer worker operations, Frida readiness/capture tools, or compare-peers evidence. Applies to native game clients and lifecycle diagnostics; single-client model teams use the multi-agent docs instead.
---

# WH3 native multiplayer

Read only the relevant section of [multiplayer tools](../../../docs/twwarhammer3/multiplayer-tools.md):

- **Worker operations**: coordinator envelopes, typed lobby operations, readiness, leave and acknowledgements.
- **Passive capture and direct adapter**: owned-PID Windows Frida capture, raw witnesses and command traces.
- **Compare saved captures (offline)**: `compare-peers --native`, generations, packet counts and verdict limits.

For live claims or the next experiment, read [foundation status](../../../docs/twwarhammer3/multiplayer-control-foundation.md#implementation-status).
Keep usage here separate from that evidence history; update the reference when an interface changes.
Local drivers under `runs/` are experiment scratch. Use the maintained modules described in the reference.
An offline evidence task needs no game launch. Live work follows `docs/state.md` Active work and the
repository's game-window rules; this skill grants no game time or cloud spending.
