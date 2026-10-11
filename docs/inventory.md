# Bounded starter scenario inventory

`scripts/inventory_scenarios.py` implements the proposed development inventory in
[research.md](research.md#proposed-bounded-development-inventory-not-launched).
It has not been launched. Complete the active long training trial and frozen
evaluation before using the game runtime for this inventory.

From a clean, committed checkout, use a new output directory and the existing
audited heuristic reference run:

```sh
uv run python scripts/inventory_scenarios.py \
  --reference runs/baseline-heuristic-settled-20261011 \
  --output runs/starter-inventory-v1
```

The reference must contain canonical `SPIREAI1` heuristic episode zero: the frozen
v1 public start, matching protocol, engine/mod pins and unchanged heuristic source.
Both sentinels compare their entire action sequence, public transitions, prefix and
initial state with that reference. The script records reference evidence hashes
and freezes a public audited reference snapshot. It does not modify the reference.

The fixed discovery inputs are `SPIREINV01` through `SPIREINV12`, in numeric order.
The schedule contains a heuristic sentinel, twelve heuristic discoveries, at most
six heuristic repeats, at most three end-turn probes and a final sentinel. Repeats
use family order Cultist, Jaw Worm, two Louses, selecting the first two eligible
discovery seeds within each family. Probe the first admitted seed per family in
that order. This fixes at most 23 assignments; one additional attempt is reserved
for the first infrastructure failure, immediately repeating its same assignment.
The original failure stays recorded. A second infrastructure failure stops the
inventory. There are no replacement seeds, automatic resume or hidden retries.
Probe outcomes are recorded as observed. A complete end-turn win does not establish
DEATH coverage; missing death or power-timing observations remain evidence gaps.

Eligibility uses audited public evidence: normal first-floor MonsterRoom,
Ironclad A0, 80/80 HP, 199 gold and the recorded 100-gold Neow choice, the ten-card
unupgraded starter deck, only Burning Blood, empty potion slots, settled known
intents, and the declared supported ordered enemy IDs. The existing prefix remains
unchanged; its max-HP variants are rejected. Complete gameplay losses remain
eligible. A repeat must match the complete discovery replay; a failed repeat
never causes another candidate to fill its place. A probe that exposes unsupported
or inconsistent evidence removes that scenario from admissions without backfill.

The global limits are 24 reserved attempts and 1,800 seconds. Every attempt is an
ordinary one-episode rollout, with 500 actions, an episode timeout up to 180 seconds
and bridge timeout up to 45 seconds, both clipped to remaining time. A POSIX alarm
also interrupts blocking collection at the absolute deadline and unwinds the game
owner. Cleanup and evidence serialization may finish after the deadline; each
attempt records `collector_overrun_seconds`, and the parent records
`post_deadline_seconds`. No new collector starts after expiry. This script runs on
the WSL/Linux controller's main thread and requires its process alarm to be unused.

Before collection, the parent freezes source revision/fingerprints, driver and
research-contract hashes, the complete conditional schedule, reference evidence,
engine/mod pins and deadline. Each attempt reservation is written before child
files or a game can exist. Source, frozen inputs and prior child file hashes are
checked again between attempts. Child provenance, actual public start pins and
original trace consistency are verified independently of claimed outcomes.

```text
contract.json           exact fixed inputs, policies and limits
reference.json          frozen audited public reference and original evidence hashes
inventory.json          deadline, reservations, outcomes, rejection reasons, admissions
runs/attempt-NNNN/      ordinary rollout manifest, raw/public evidence and profile snapshot
```

All conditional assignments remain in `inventory.json`. Unavailable repeat/probe
slots are `not_scheduled`; budget or failure leaves explicit `unattempted` entries.
Every attempted record retains its configuration, timestamps, audit result and
child file hashes. Child manifests explicitly retain development purpose and
their frozen parent assignment, so later data export cannot mistake them for
unclassified rollouts. Ctrl-C preserves the reservation and child evidence before
propagating; a new invocation cannot overwrite or resume that directory. Source or
evidence mutation stops collection. A sentinel mismatch invalidates the inventory.

`admissions_valid` is true only when the whole schedule completes and both sentinels
verify. Any earlier admission entries in an incomplete inventory remain provisional.
The entries include start/composition pins, discovery trace SHA and discovery/repeat
paths. They are evidence for a later explicitly scheduled development catalog;
this script creates no executable catalog or training dataset. Inspect traces for
the exact mechanics listed in the research contract, retain minimal public
transitions where present, and report gaps. No generalization claim follows from
this inventory.

Python callers use `inventory(output, reference_run) -> dict`. The CLI exits zero
only for a complete valid inventory. Tests use the actual rollout/auditor with
mocked game communication and isolated runtime contexts; the optional local v1
reference test reads saved engine evidence without launching a game.
