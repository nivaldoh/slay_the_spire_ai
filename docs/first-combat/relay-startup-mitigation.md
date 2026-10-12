# Direct WSL endpoint startup mitigation

`runs/first-combat/qwen3-0.6b-sft-eval-20261011` stopped after two completed wins at 77 HP.
The third attempt failed before any observation or action reached the runner:
`BridgeTimeout: timed out waiting for relay connection`. Five of the eight
scheduled attempts remain unattempted. The original failure and incomplete
evaluation stay preserved; the two wins are not a completed suite result.

The failed attempt's original logs establish this sequence on 2026-10-11 UTC:

| Time | Evidence |
| --- | --- |
| 07:42:10.182 | CommunicationMod receives the relay's `ready`. The relay emits this only after Windows `socket.create_connection` returns. |
| 07:42:14.910 | The game writes its ready main-menu observation. |
| 07:42:40.215 | CommunicationMod reports the relay child died. The preserved stderr reports Windows error 10054, connection reset by peer. |
| Episode elapsed 46.209 seconds | The Linux runner records an accept timeout, zero actions and an infrastructure failure. |

The relay's configured inactivity timeout was 45 seconds. Its death roughly
30 seconds after `ready`, together with Linux never accepting, suggests a
problem between Windows connect and the Linux listener. The exact cause is
unproven. The previous listener closes after its single accept, and each later
episode rebinds `127.0.0.1:19876`, so the Windows/WSL localhost forwarding
lifecycle is a working hypothesis.

Microsoft's [WSL localhost implementation notes](https://github.com/microsoft/WSL/blob/master/doc/docs/technical-documentation/localhost.md)
describe NAT-mode bound-port monitoring and forwarding through `wslrelay.exe`.
Its [networking documentation](https://learn.microsoft.com/en-us/windows/wsl/networking#identify-ip-address)
also documents Windows clients connecting to the WSL instance's IP address.
These sources explain the alternative path; they do not establish the cause
of this recorded failure.

## Bounded socket evidence

With no game or model running, 40 disposable Windows-Python-to-Linux exchanges
all passed: ten loopback and ten direct-IP exchanges on a disposable port,
then ten of each using the production port 19876. Each accepted one connection,
closed its listener, exchanged an exact nonce, closed the connection and
rebound the same endpoint for the next trial. The failure did not recur.

The slowest loopback trials took 0.583 and 0.554 seconds; the direct-IP groups
took at most 0.100 and 0.099 seconds. These measurements include Windows process
startup and the complete exchange; they are not isolated network latencies or
evidence of a proven forwarding race. They show both paths working at probe time.

Five additional exchanges used the actual `BridgeServer`, current-address
discovery helper and Windows `windows_relay.py` on the direct address and port
19876. Each verified the `ready` handshake, exact UTF-8 state forwarding, the
reverse `STATE` command and expected cleanup on simulated game-stdin EOF.
No game launch, model load, runtime deployment, firewall change, service
restart or reconnection occurred.

The [compact evidence](results/windows-wsl-endpoint-probes.json) preserves the
probe summary, tested source hashes and original failure-file hashes. Its
local raw summary is `/tmp/spire-direct-wsl-network-proof-20261011.json`, SHA-256
`8791507a9988e62e5c737622e3ee664181f9a6f2821094caf0941688680d304a`.

## Implementation and validation boundary

Before each game deployment, `wsl_bridge_host()` reads `ip -4 -j address show
dev eth0`. It requires active `eth0` with exactly one global IPv4 address in a
private RFC1918 range. Missing, malformed, inactive, ambiguous or unsupported
addresses stop the attempt before deployment or launch. The runner binds that
exact discovered address at port 19876 and writes the same endpoint into the
relay configuration and `deployment.json`. It does not cache an IP, bind a
wildcard address, fall back to localhost, reconnect or retry a failed attempt.
The standalone `BridgeServer` keeps its loopback default.

This is a mitigation that bypasses the suspected forwarding path on the
observed WSL NAT setup. Other interface layouts and mirrored networking are
outside this discovery contract. Address changes between discovery and bind
produce a recorded infrastructure failure rather than an alternate route.

Focused validation: **106 tests passed, one optional Windows process-ownership
test skipped**, covering discovery failures, unchanged standalone bridge
behavior, exact listener/deployment agreement and discovery again for each
episode. Five actual standalone relay exchanges additionally passed.

Root's two declared original-engine controls then passed at source `f0736a7`:
both won at HP77 in 39.17/38.91 seconds, with all 21 commands and every public
transition exactly matching the existing heuristic reference. Both deployed the
direct guest address at port19876. See [control audit](results/direct-relay-control-20261011.json).
This verifies the changed transport on those complete fights. It does not prove
the original failure's exact cause or guarantee future startup reliability.
