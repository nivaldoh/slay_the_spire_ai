# Google Cloud game client: setup guide

Pilot closed 2026-11-03 UTC: WH3 launched on a Windows/L4 VM in Singapore and one
small battle ran. The agreed connected/disconnected check is incomplete; unattended
operation remains unverified. Evidence was exported and VM/disk deleted.
Evidence: `runs/twwarhammer3/gcp/session-20261102b/`; [result](#pilot-result-2026-11-03).
This is the Google Cloud runbook for step 2 of
[native multiplayer](native-multiplayer.md#2-prepare-one-windows-client-using-the-selected-runbook).
Provider facts come from Google, Microsoft, NVIDIA and Valve pages read on 2026-11-02
and rechecked by a second agent
([references](../references.md#gcp-client-setup-guide-2026-11-02)).
The in-VM steps follow [gcloudrig](https://github.com/gcloudrig/gcloudrig) (`gcloudrig.psm1`,
`gcloudrig-boot.ps1`: a T4 vWS gaming VM on Compute Engine with Steam) and Parsec's archived
[Cloud Preparation Tool](https://github.com/parsec-cloud/Parsec-Cloud-Preparation-Tool)
(`PostInstall/PostInstall.ps1`). We do not copy their Defender or firewall shutdowns.

Read [cloud usage](../cloud.md) first: current project, budget, login/billing status and
cleanup requirements live there. The pilot approved on 2026-11-02 was $5 total and at most
3 hours, installation included. On 2026-11-03 the owner allowed $10 for now
([direction](../owner-direction.md), [cloud usage](../cloud.md)), read as a new cloud
allowance from $0; the direction does not say whether the 3-hour limit stands. Actual
commands and evidence: `runs/twwarhammer3/gcp/setup-20261102/`.

## Pilot result, 2026-11-03

**Incomplete; no compatibility pass.** Frozen game source `1fd0b6d`, Steam build
25961564, Windows Server 2022, g2-standard-4/L4 vWS, NVIDIA 596.86 with a licensed
RTX Virtual Workstation. Main-menu and deployment images rendered normally with RDP.
The UI showed Low at 1600×900; persisted preferences still showed the earlier settings.
Five Middenland Swordsmen per side, Small (30 men each), no lords, An Ogre's Folly,
player defending against attacking AI. This fixture rests on JUDGEMENT? Diagnostic
roster update in `runs/twwarhammer3/gcp/session-20261102b/brief.md`.

One battle reached the engine's won result. Its initial connected interval had a
mailbox read error; the disconnected interval ended with the battle before 120 seconds.
The subsequent attempt never left deployment: the input task reported success but did
not activate Start Battle. That is not an observed game freeze. The revised collector
waited for Deployed and counted none of this static screen as battle time.
No completed same-battle reconnect rendering check; zero multiplayer battles.

Evidence and independent review: `runs/twwarhammer3/gcp/session-20261102b/`, including
`pilot-evidence.zip`, `exported/`, and `review/final-evidence-review.md`.
VM/disk deleted at 03:55:54 UTC, before the fixed cutoff; final inventories are empty.
Pilot workflow, firewall, service accounts, role and SSH keys were removed; project,
APIs, quota and unrelated defaults remain. Quoted host subtotal plus earlier $0.03
allowance is about $3.58; actual billing, traffic and tax remain unreconciled.

Next: fix Start Battle input with engine confirmation, save/reuse graphics once, and
establish an unattended Windows graphics session. The pilot has not shown that WH3
can run without a graphics session. Before another paid run, prepare the whole timed
sequence and export, then obtain a new allowance; the closed session is not renewable.

## What you do

The approved pilot is closed; no VM is waiting for login. Another paid session requires
an allowance. The second Steam account has DLC-granted access with a limited roster.
For a future authorized session, wait until the assistant confirms Windows/Steam are ready, opens Remote Desktop and
copies its Windows password to your clipboard. You:

1. Sign in as `wh3`, pasting the password.
2. Open Steam, sign in with the **second account**, complete Steam Guard, and remember login.
3. Install WH3 in the default Steam folder. Close Remote Desktop and tell the assistant
   once the download starts. The download continues; the session clock also continues.

The assistant installs drivers/tools, checks the game and deletes the VM/disk afterward.

## Region fallback

[wh3_gcp.py](../../scripts/wh3_gcp.py) replaces the per-zone pilot scripts. It discovers
zones advertising both `g2-standard-4` and `nvidia-l4-vws`, then tries one zone per region
before second zones. The [regional quotes](../../configs/twwarhammer3/gcp-regions.json)
cover eight regions: three US, Belgium, Netherlands, London, Taiwan and Singapore.
The read-only preview on 2026-11-03 UTC found 22 supported zones; this is not live capacity.

Preview, with an absolute cutoff at most three hours away:

```bash
uv run python scripts/wh3_gcp.py --name wh3-session-001 \
  --deadline 'YYYY-MM-DDTHH:MM:SS+00:00' --spent-usd 0.03
```

Choose an unused session name. `--spent-usd` includes earlier spend or its conservative
allowance, not a fresh budget. `--regions us-east1,europe-west4,asia-east1` restricts and
orders the quoted regions. Add `--create --output runs/twwarhammer3/gcp/session-001`
only for a live session after the prerequisites below. Evidence records every attempt and
the selected zone; SSH/RDP must use that zone. A used output path or workflow name refuses reuse.

Each attempt first arms [cloud cleanup](../../scripts/gcp/cleanup.yaml), including deletion
calls against the absent target before waiting. Only an explicit stockout plus empty VM/disk
inventories permits another attempt. Other errors stop with the backup left armed; inspect
`state.json` and remove any resources promptly. Success stops the search. The five-minute
native deletion margin and cloud deadline never move. An exhausted search leaves only its
workflow definition, which can be removed after confirming no active execution or resources.

Costs include the host, Windows, workstation allowance, disk and IP. Regions exceeding the
total allowance after earlier spend and a $1 reserve are skipped. Quotes older than 24 hours
refuse use; refresh them from Google's Billing catalogue, retaining SKU IDs and rounding up.
Region order, quote age and reserve rest on the `JUDGEMENT` comments in the runner. These
estimates cannot enforce a provider dollar cap. Offline checks pass. One live sequence
made eight create attempts: seven stockouts, then Singapore success; each stockout had
empty VM/disk inventory before the next attempt. This is provisioning evidence only.

## Risks, most serious first

| Risk | What we know | What we would see | Fallback |
|---|---|---|---|
| GPU quota refused | Google states no default GPU quota; a forum post shows 0 for a new project. Its automated review weighs time on Google Cloud. Two forum posts report automatic refusals: one despite a long billing history, one for a personal project | The quota request comes back denied | airgpu or a second PC; asking again later may not help. Finding out costs $0 |
| WH3 will not run on Windows Server 2022 | This pilot launched WH3 and ran one small battle; full compatibility check incomplete | The game exits, hangs or shows errors at start | Add the missing pieces below (audio, Media Foundation, DirectX 2010). Google offers no Windows 10/11 images without your own licence, so a failure here means airgpu (also Server) or a PC |
| Nothing renders with nobody connected | Forum reports: after an RDP disconnect Windows stops drawing (black screen). Google does not document whether the L4's console session has a display | Screenshots go black; battle time falls behind Windows time | Run the game only in an auto-logged-on console session with the lock screen off. If the console has no usable display, add a virtual display driver ([parsec-vdd](https://github.com/nomi-san/parsec-vdd), Server 2019+; its display disappears about 1 s after its controlling app stops) |
| Wrong NVIDIA licence | A VM created without `nvidia-l4-vws` gets the "Virtual Applications" licence: one display, at most 1280x1024 | The licence reading (step 1) is not "NVIDIA RTX Virtual Workstation", "Licensed" | Delete and recreate the VM with the vWS accelerator |
| Too slow for 1x | `g2-standard-4` has 4 vCPUs. Google's own Windows example uses `g2-standard-8`; Steam recommends an i5-class CPU | Battle time runs slower than Windows time | Resize to `g2-standard-8` (more per hour) |
| No L4 free in the zone | Stockouts are separate from quota (`ZONE_RESOURCE_POOL_EXHAUSTED`) | The create fails | The region runner tries other quoted zones within the same allowance and deadline |
| Game builds differ between your PC and the VM | Your PC's WH3 is set to "always keep updated" | `doctor` on the VM reports a different build or executable hash from the PC | Set the VM to update only on launch. Multiplayer needs equal builds, and a re-pin needs your yes |
| Costs keep running | Budget alerts only notify; Google's spend caps do not cover Compute Engine. A stopped VM still bills its disk | The bill grows | Fixed DELETE deadline plus an independent cloud workflow; confirm both VM and disk are absent |
| Open to the internet | A new project's default network allows RDP and SSH from any address | — | Delete those two rules first; allow only Google's IAP range. Your Steam login stays on the VM until you remove the device in Steam or delete the VM |
| Windows SSH is a Preview feature | SSH through IAP is documented for Linux only | `gcloud compute ssh` fails | Startup scripts, which run as SYSTEM and log to the serial port, plus RDP |
| Native controller paths may fail | Native `launch` and `menu` ran in this VM; `play` and a real multiplayer worker remain untested here | A Python error on the VM | Fix on a branch; this is a code risk, not a cloud one |
| First-run game screens need clicks | Your PC passed them long ago | The battle never starts | Click through with `menu --dump`/`--click` and screenshots; else a second short RDP session for you |

## Costs

Google Billing catalogue, us-east1, read 2026-11-03 UTC (Nov 2 locally):

| Item | Per hour |
|---|---:|
| `g2-standard-4`, including its L4 | $0.707 |
| Windows Server, 4 vCPUs | $0.184 |
| Workstation licence allowance | $0.200 |
| 250 GiB pd-balanced | $0.035 |
| External IPv4 allowance | $0.005 |
| **Estimate** | **$1.131** |

Three hours: about **$3.39**, before traffic, tax and teardown. The pilot's $5 total also
included cleanup tests; the $10 of 2026-11-03 is noted at the top of this page. The
catalogue lists a $0.20 workstation SKU; its exact L4 billing mapping
is unconfirmed, so this estimate includes it. Do not add another L4 charge to the G2 bundle.
Billing reports lag; this is not a provider-enforced dollar cap. Evidence: `sku-selected.json`
and `game-host-card.md` in the run directory. The disk bills while a VM is stopped.

JUDGEMENT?: Region — agent writing the quote worksheet, 2026-10-30: us-east1, the nearest G2
region to São Paulo (from your UTC-3 time zone only). It has G2 in zones b and c; São Paulo
has no G2. Another region changes latency to your PC and the price.

São Paulo does list N1 with a T4 vWS (gcloudrig's setup, slower than an L4; Google lists T4
support ending 2027-08-01) and G4 (RTX PRO 6000 vWS). Either would cut latency to your PC;
neither is priced here.

Machine size rests on JUDGEMENT native-multiplayer.md Cloud candidate; the 250 GB disk on
JUDGEMENT native-multiplayer.md Cost workload.

## Steps

The assistant performs the steps below unless marked **You**. Project: `wh3-benchmark` (`$P`).
Use the selected VM name and zone from the region runner (`VM` and `ZONE` below).
The closed pilot used `wh3-compat-20261102b`, `asia-southeast1-a`; Windows user `wh3`,
repo `C:\wh3\repo`.
Before execution, supply explicit project/zone flags on resource commands, including
templates below that omit them. Leave the current default project untouched. Secrets go to
`runs/twwarhammer3/gcp/` with mode 600 and are never printed.

### 0. Before any money

Billing/login, APIs and global GPU quota 1 remain set. Regional quota may differ. Both
cheap cleanup cases passed once (running and stopped); evidence lives in the run directory.
The pilot removed its support resources. Before another `--create`, restore:

- `wh3-vm` service account with no project roles.
- `wh3-cleanup` service account, bound to a custom role with only
  `compute.instances.get`, `compute.instances.delete`, `compute.disks.get`,
  `compute.disks.delete`, `compute.zoneOperations.get`. Restore a soft-deleted role or
  use a new ID; do not grant Editor as a shortcut.
- `wh3-allow-iap`: default network, ingress TCP 22/3389 from `35.235.240.0/20`, target tag
  `wh3-worker`. Keep public default SSH/RDP rules removed.

Before another session, recheck quota, price, resource inventory and the owner's allowance.
Arm the independent deletion execution before creating the VM. A budget alert is only
a reminder; no alert was configured for this pilot.

JUDGEMENT?: VM service account — Claude Code, 2026-11-02: a service account with no roles.
Google adds the vWS licence itself when the VM has the vWS accelerator; whether the licence
also needs a role is not documented. If the licence reading fails, try the default account
before blaming the GPU.

### 1. Create the VM (billing starts)

The region runner first checks for leftover resources and arms `<session>-cleanup`.
It creates one `g2-standard-4` with `nvidia-l4-vws`, pinned Windows
Server 2022 image, 250 GiB auto-delete disk, IAP access, and the role-free `wh3-vm` account.
Native deletion starts five minutes before the supplied cutoff; independent cleanup starts
at the cutoff. These are fixed timestamps in `state.json`, not renewable limits.

First boot runs `windows-bootstrap.ps1`: SSH, Google's pinned NVIDIA installer, Media
Foundation, audio and Steam. **The driver script can return zero after an installer
warning.** Check GPU health after reboot; the bootstrap marker alone is insufficient.
`RUNNING` does not mean Windows setup is finished. In the Singapore pilot, SSH opened
then closed before authentication and RDP was unavailable during specialization; both
worked after its automatic reboot. Wait for the bootstrap marker and specialization
completion in serial output before diagnosing remote access or resetting the VM.

Then:
- Follow `get-serial-port-output` until the first boot finishes.
- Create `wh3` with `gcloud compute reset-windows-password VM --project=wh3-benchmark --zone=ZONE --user=wh3 --quiet
  --format='value(password)'` into a mode-600 file.
- Reboot once for the driver.
- Read `nvidia-smi -q` over SSH (`gcloud compute ssh VM --project=wh3-benchmark --zone=ZONE --tunnel-through-iap`). It should
  show "NVIDIA RTX Virtual Workstation" and "License Status : Licensed (Expiry: Permanent)".
  Google documents that reading for Linux only; on Windows it documents NVIDIA Control Panel
  > Help > System Information, which Claude Code can screenshot in the console session (step 2.9).
  If the VM is not licensed for vWS, delete and recreate it.

### 2. Prepare Windows over SSH

Reports (not Google's docs) say Google's SSH users and the user `reset-windows-password`
creates are administrators with an elevated shell; check with `net localgroup
administrators`. A program SSH starts runs in session 0, which has no desktop. So anything
with a window (Steam, the game, `play`, screenshots) runs as a scheduled task for `wh3` with an
interactive logon (`New-ScheduledTaskPrincipal -UserId wh3 -LogonType Interactive`, then
`Start-ScheduledTask`).

The pilot used an RDP-created interactive session (ID 2). Auto-logon, console display
startup and a virtual display driver were not installed or tested. The console steps
below remain proposals, not prerequisites already completed by the bootstrap.

1. **Auto-logon** of `wh3` to the console: download Sysinternals Autologon and run
   `Autologon64.exe /accepteula wh3 <computer name> <password>` (Microsoft documents
   `autologon user domain password`; the EULA flag comes from third-party scripts). It stores
   the password as an LSA secret, which an administrator can read. Fallback: the Winlogon
   registry values, which store it in plain text.
2. **Never lock or sleep:**
   - `DisableLockWorkstation=1` in `wh3`'s `HKCU\...\Policies\System` (Microsoft's "Remove
     Lock Computer" user policy) and under HKLM as Parsec's script does;
   - `powercfg` monitor and standby timeouts 0;
   - no screen saver.
3. **GPU in RDP sessions** (only for your setup session): `bEnumerateHWBeforeSW=1` under
   `HKLM\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services`. Without it, NVIDIA says
   Server RDP sessions do not use the GPU.
4. **Audio:** set the Windows Audio service (`Audiosrv`) to Automatic and start it. If WH3
   then fails without a sound device, install VB-CABLE silently, as Parsec's script does:
   import its signing certificate to TrustedPublisher, then run `VBCABLE_Setup_x64.exe -i -h`.
5. **Windows features:** `Install-WindowsFeature Server-Media-Foundation`. Only if the game
   asks: the June 2010 DirectX runtime (`DXSETUP.EXE /silent`) or a Visual C++ runtime
   (`vc_redist.x64.exe /install /quiet /norestart`).
6. **Windows Update:** no automatic updates or restarts on this test VM, so no reboot lands
   mid-battle.
7. **Steam:** `SteamSetup.exe /S`, plus a scheduled task that starts `steam.exe -silent`
   when `wh3` logs on.
8. **Repo:**
   - Python 3.13 (python.org installer, `/quiet InstallAllUsers=1 PrependPath=1`) and Git for
     Windows (`/VERYSILENT /NORESTART`).
   - `git clone -c core.autocrlf=false https://github.com/nivaldoh/slay_the_spire_ai
     C:\wh3\repo`, then check out the revision your PC uses.
   - Nothing else to install: the worker and `play` need only the standard library. Every
     repo command runs from `C:\wh3\repo` with `PYTHONPATH=C:\wh3\repo\src`, since nothing
     installs the package. `play` needs Git because it refuses uncommitted edits.
9. **Display:**
   - Reboot; confirm `wh3` is logged on to the console (`query user`).
   - In that session, list display adapters and modes and take a screenshot with a small
     PowerShell script (`System.Drawing` `CopyFromScreen`, not `play --stills`, which needs
     Pillow). Copy it back with `gcloud compute scp`.
   - If the Microsoft Basic Display Adapter is the primary display, disable it, as gcloudrig
     does; Parsec's script also disables Google's display adapter (GGA). Set 1920x1080.
   - Leave the VM's "display device" option off. Parsec's README says it adds a display that
     cannot be removed; Google documents turning it off with `--no-enable-display-device`.

JUDGEMENT?: Windows Update off — Claude Code, 2026-11-02: the test VM takes no updates, so a
reboot cannot interrupt a battle; it also stays unpatched while it exists. Delete the VM after
the pilot, or re-enable updates before keeping it longer.

### 3. Your Steam session

The assistant:
- starts an IAP tunnel in WSL for the current VM, with its explicit project and zone:
  `gcloud compute start-iap-tunnel VM 3389 --local-host-port=127.0.0.1:13389 --project=wh3-benchmark --zone=ZONE`;
- copies the `wh3` password into the Windows clipboard (`clip.exe`);
- opens Windows' built-in client from WSL: `mstsc.exe /v:127.0.0.1:13389`.
  The tunnel stays running in WSL; the desktop opens in Windows. No GCP CLI setup on
  Windows or Linux RDP client is needed. The pilot's RDP certificate was compared with
  its fingerprint read through authenticated SSH before the owner accepted the prompt.

**You:**
1. On **Windows Security**, choose **More choices → Use a different account** if needed.
   Username: **`.\wh3`**. Password: **Ctrl+V**, using the VM's generated Windows password
   the assistant just copied. Click **OK**. This is separate from your Steam login.
   If the clipboard changed, ask the assistant to copy the password again.
2. Once the Windows desktop opens, open Steam. Log in with the **second Steam account's
   own credentials**, complete Steam Guard, and remember the login.
3. In the Library, click Install on Total War: WARHAMMER III, in the default folder (the
   repo expects `C:\Program Files (x86)\Steam`).
4. Close the Remote Desktop window. The download carries on without you.

Give these instructions together at the handoff. Keep them in a pending status question
while the owner logs in; intervening tool output can hide earlier chat instructions
(owner, 2026-11-02). Never put the generated password in documentation or logs.

Use the second account on the VM. The local account stays on your PC.
The VM account has game access through Boris Todbringer — Lords of the Endtimes DLC
(owner clarification, 2026-11-02), not a full WH3 base roster. Confirm every unit and
faction on that client: its Khorne list exposed only Blood Keepers; Middenland Swordsmen
and Spearmen returned recruitable. Even `kho5-kho5` includes DLC20 cavalry. The local
account's roster availability is not evidence for this account.
Owner clarification, 2026-11-05: these content restrictions and the pilot's no-lord setup
apply to multiplayer VM work. General local evals may consider any faction and lords.

Do not reboot expecting automatic login unless auto-logon has actually been configured
and checked. The pilot needed the owner to open RDP; SSH alone did not create its desktop.
An existing interactive session can be driven through scheduled tasks over SSH. Starting
that session unattended after a fresh boot remains separate work.

JUDGEMENT?: Unattended display — Claude Code, 2026-11-02: an auto-logged-on console session
and a reboot after any RDP use, instead of moving the session back with `tscon` or running a
streaming host (Sunshine needs Windows 11, HP Anyware is licensed). If the console session
has no usable display, the fallback changes what the test measures.

### 4. Download and pin

1. Poll `appmanifest_1142710.acf` over SSH until the install finishes.
   Its downloaded-byte counters can lag during an active download (observed in this
   pilot). Check Steam's UI or `logs/content_log.txt` for live progress; require a
   completed install and actual executable before treating the host as ready.
2. Stop Steam, set `"AutoUpdateBehavior" "1"` (update only when launched), start Steam again.
3. Run `python -m twwarhammer3 doctor` on the VM: the build and `Warhammer3.exe` must
   match the [current runtime pin](integration.md#pins) and the PC. If either differs,
   stop and tell you.
4. Use the owner's selected Low preset and record actual resolution and unit size.
   Save the configuration through a graceful game exit, then reuse it. Check persistence
   once across a restart; do not revisit graphics on every launch unless it changed.
   Forced shutdown in this pilot left the file at Ultra even after live Apply showed Low.
   Low also selected Small units: the actual battle had 30 men per Swordsmen unit.

Optional, your choice: set your PC's WH3 to update only on launch too.

### 5. One-client test

Owner agreed 2026-11-02 ("Use this check"): one small unpaused battle, measuring
120 seconds with Remote Desktop connected and 120 seconds after disconnecting, then
reconnecting to confirm the game still renders. Pass: no crash or freeze, usable
screenshots, and battle time within 1% of Windows elapsed time in each interval.
This checks this VM configuration only; no pass yet. Use content actually recruitable
on the second account; DLC-granted game access does not unlock the full WH3 base roster.
Record the actual build, graphics, roster and Windows session;
do not replace a failed disconnected interval with a rebooted session and call it a pass.
Stop after this check or a diagnosed setup failure, as the owner requested.
Owner subsequently agreed a three-second limit: investigate longer spans without an
advancing game-time reading; recording gaps over three seconds are inconclusive.
Neither can pass on endpoint speed alone. Confirm an actual RDP viewer for the connected
interval; an active console is not a connected RDP session.

Keep local WH3 closed. Start the VM game without the mod first and save a readable
main-menu screenshot. Record GPU/driver/licence readings separately: these establish
the graphics setup, not that WH3 works. Then run the agreed battle check above, saving
the game-time readings and Windows timestamps for each interval, screenshots, and
the exact connection/disconnection times. An early ending gives insufficient evidence
for a missing interval; a stopped simulation must not disappear from the clock comparison.
Use no model calls. Arm the collector and timed disconnect before starting the battle.
Require the engine's Deployed phase and an advancing clock after the blue Start Battle
button; a successful input-task exit is not proof that the click took effect. Record from
Windows clocks, not WSL clocks. Keep transient mailbox read failures in the evidence;
bounded retries can recover sharing collisions without discarding time gaps. Capture off
the sampling thread. A capture failure alone does not establish a stopped simulation.
Export evidence and delete the VM/disk when done.

JUDGEMENT?: One-client test — Claude Code, 2026-11-02: one `attack_nearest` battle on
`kho5-dwf5` before and one after a stop and start, read by screenshots. The plan's
[host/display gate](native-multiplayer.md#verification-matrix) also attaches a remote viewer,
which here would take the session off the console. Another battle, count or viewer changes
what the test shows. `kho5-dwf5` uses Dwarfs, which your account owns; a WH3-only second
account may not.

That earlier proposed test is superseded by the owner's "Use this check" above; its
stop/start repetition and multiplayer continuation are outside this session. On failure,
keep evidence and name the failing layer (capacity, quota, OS, display, game or our code).

### 6. Finish and delete

1. Copy evidence to `runs/twwarhammer3/gcp/` before the cutoff.
2. Delete the pilot VM with its disk, then read back both resources: both must be absent.
3. Remove the pilot firewall rule. Cancel the sleeping backup only after confirming removal.

Keep `wh3-benchmark` itself. This pilot does not retain a paid disk, image or snapshot.
A later session needs a new allowance; restarting does not reset this session's budget.
