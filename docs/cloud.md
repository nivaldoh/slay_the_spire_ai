# Cloud usage

Cloud compute, storage and supporting services used by this repo. WH3 installation
details stay in the [GCP setup guide](twwarhammer3/gcp-client-setup.md).

## Current boundary

Owner, 2026-11-02 ([direction](owner-direction.md)):

- GCP project: **`wh3-benchmark`**.
- Budget: **$5 total**, including cleanup tests, and **one game-host session of at most
  3 hours**, installation included. Delete VM/disk at the deadline. This replaces $1;
  model API allowances remain separate. Establish cleanup before provisioning resources.
- The second Steam account has game access through **Boris Todbringer — Lords of the
  Endtimes** DLC (owner clarification, 2026-11-02), with most units locked. Do not assume
  a full WH3 base roster. Check recruitment on that client; Middenland Swordsmen and
  Spearmen returned selectable during the pilot's setup.

Setup on 2026-11-02: WSL login works; billing is enabled. Required Compute, Quotas, IAM,
IAP, Workflows and Billing APIs are enabled. Global GPU quota increased from 0 to 1;
regional L4 vWS quota is 1. Both cleanup cases passed once. Windows/GPU creation then
failed with capacity stockouts in `us-east1-b/c`, `us-central1-a/b/c` and `us-west1-a`.
No Windows VM was created; WH3 compatibility is untested. Final inventory has no VMs,
disks, reserved IPs, snapshots or custom images. Pilot workflows, firewall rule and service
accounts were removed; project, APIs and quota remain. Cleanup tests were estimated below
$0.03; actual billing is pending. Evidence: `runs/twwarhammer3/gcp/setup-20261102/`.

The CLI default was `pokeagent-metahorns`. Use explicit `--project=wh3-benchmark` on
resource commands and an explicit zone where applicable; do not rely on the default.

Resumed pilot, closed 2026-11-03 UTC: `wh3-compat-20261102b` in `asia-southeast1-a`
was created after seven stockouts. WH3 launched and one small battle ran; the agreed
connected/disconnected check is incomplete, so compatibility remains unverified.
The retry stayed at Start Battle: an input automation failure, not an observed game freeze.
Evidence was exported before deleting the VM; both VM and disk inventories are empty.
Native DELETE had been set for 04:00:23 UTC, backup cleanup for 04:05:23 UTC; neither
was extended. Quote: $1.30/hour; host subtotal plus the earlier $0.03 allowance is about $3.58.
Actual billing, traffic and tax remain unreconciled. No paid storage is retained.
Evidence: `runs/twwarhammer3/gcp/session-20261102b/`; [result and follow-ups](twwarhammer3/gcp-client-setup.md#pilot-result-2026-11-03).

## Before spending

- Name the resources, purpose, total cap, stop time with timezone, and cleanup method.
  Include setup, failed attempts, disks, licences, IPs, traffic and cleanup services in
  the estimate. Leave room for shutdown delays; do not plan to spend the entire cap.
- Reserve time for the complete measurement and evidence export inside both the game
  supervisor limit and cloud cutoff. Arm automatic phase switching before Start Battle;
  start timing only when the game reports Deployed and its clock advances.
- Budget alerts are notifications, not a stop. Billing reports lag; GCP spend caps do
  not cover Compute Engine. A stopped VM can still incur storage charges.
- Record resource names and IDs under `runs/twwarhammer3/gcp/`. Cleanup must target that
  session's resources, not unrelated resources or the whole project. Keep credentials
  out of Git and logs; restrict local secret files to their owner.
- For capacity fallback, price every allowed region. Try one VM at a time, keep the
  original deadline, and require an explicit empty VM/disk inventory before moving on.
  Permission, quota, timeout or unknown-inventory errors stop retries. The
  [runner](twwarhammer3/gcp-client-setup.md#region-fallback) previews without provisioning.

## Cleanup

JUDGEMENT: Cleanup — Codex, 2026-11-02: proposes deletion on completion or failure plus
a cloud-side deadline. Stopping and retaining disks preserves setup but keeps billing;
the deployment plan rests on this choice. Owner subsequently approved a $5 total,
at-most-3-hour session with automatic VM/disk deletion. Tested with Cloud Workflows;
the repeatable check method has not been agreed.

1. Give each VM a fixed `--termination-time` and `--instance-termination-action=DELETE`.
   Set every disposable disk's `autoDelete=true`; avoid retained images, snapshots and
   reserved IPs for the pilot.
2. Arm cleanup outside the VM and local controller before provisioning. It must also
   delete a stopped VM and any leftover resources from partial creation, retry temporary
   failures, and confirm removal. This pilot uses Cloud Workflows with deletion-only
   permissions and exact resource names.
3. Delete resources when the session finishes or fails; the deadline is the backup.
   Remote Desktop disconnection or low CPU use does not mean the game session is finished.
4. Read back the resource inventory after cleanup. Record any retained resource's cost
   and deletion deadline; retention needs owner direction. Reconcile delayed billing later.

Read cloud execution status, not just the CLI exit code: `gcloud workflows run` returned
exit 0 for a FAILED execution in the first dry run. Require `SUCCEEDED`, completed
delete operations and absent resources. A deletion deadline starts cleanup; it does not
promise that resource removal has finished at that instant.

GCP clears the scheduled termination timestamp when a VM stops. Its timer alone therefore
does not clean up stopped storage. Automatic termination can begin up to 30 seconds late.
The provider documents these behaviours; our cleanup remains unverified.
[Sources](references.md#cloud-usage-and-cleanup-2026-11-02).

## First cleanup check

JUDGEMENT: Cleanup check — Codex, 2026-11-02: proposes a disposable Linux VM without a GPU,
once left running and once stopped early, with the local controller disconnected.
Running-only would miss stopped-disk billing; the cleanup gate rests on both cases.

Keep the check and quote within the current total boundary. In both cases, require
the VM and its disk to be absent after cleanup; an accepted delete request or `TERMINATED`
VM status is insufficient. Keep resource IDs, deadline settings and completed operations
as evidence. Both cases passed once on 2026-11-03 UTC (Nov 2 locally): native deletion
removed the running VM/disk; the separate workflow removed the stopped VM/disk.
Both workflows succeeded and both resources returned 404. Independent review matched
resource IDs and completed operations. Evidence: `runs/twwarhammer3/gcp/setup-20261102/`.
This is evidence for the pilot, not an agreed verification method or a billing hard cap.
