# First candidate: infantry support and cavalry timing

Implemented from the owner's supplied plan, 2026-11-04. **Development candidate,
unverified; first pilot failed setup before orders.** On 2026-11-04 the owner selected "Use the proposed
exploratory rule" for the procedure below, after setup and action-effect checks. It is now
listed in [agreed-checks.md](../agreed-checks.md). The second scenario waits.

Question: can a controller judge whether supporting infantry will remain effective long
enough for a cavalry manoeuvre to pay off? This candidate first asks whether commitment
timing changes outcome or army condition. It establishes neither novelty nor a need for
feedback, prediction or a particular model. Infantry rout time is endogenous: cavalry may
prevent it. Fresh launches are separate trajectories, not matched counterfactual branches.

## Declaration and executor

The owner's selected directions are manoeuvre timing, an Empire mirror, unrestricted
legal tactics, and timing affecting outcome or army condition. The current entry is
`configs/twwarhammer3/scenarios.json` → `emp-support-timing-v2`; v1 retains the failed pilot setup. Public task: win and preserve
the army where possible; engine timer wins count. The entry selects no benchmark scorer,
controller restriction, reserved split or ranking formula. Greatswords' superiority and
winnability are unknown until demonstrated.

JUDGEMENT: Starting geometry and settings — Codex, 2026-11-04, supplied plan: these are
construction defaults requiring live checks. Different spacing, widths or difficulty can
change the timing problem; the JSON declaration and its interpretation rest on this choice.

| Setting | Candidate value |
|---|---|
| Friendly | One Swordsmen and one Empire Knights regiment |
| Enemy | One Greatswords regiment, native AI, attacking |
| Characters/upgrades | Lordless, rank zero, no added equipment, spells or reinforcements |
| Mode/map | Land Battle; `battle_preset_qb_wh2_dlc17_taurox_rune_tortured_axes` |
| Lobby | Normal, AI modifier 1.0, large scale 0.75, 2,000 funds, 1,200 s timer, realism off |
| Friendly deployment (v2, owner-selected translation) | Swordsmen `(0,-160)`, facing 180°, width 40 m; Knights `(-100,-100)`, facing 180°, width 30 m |
| Enemy deployment (v2) | Greatswords `(0,-320)`, facing 0°, width 40 m |

`behaviour_defaults: true` reuses the friendly benchmark defaults without choosing a
benchmark profile: supported fire-at-will on, skirmish and defend off; supported toggles
of both armies are read back. Enemy toggles remain engine-controlled. Setup and terminal
condition records are retained privately. No policy-facing schema changes.

JUDGEMENT: Diagnostic design — Codex, 2026-11-04, supplied plan: three fresh launches per arm,
18 attempts in rotated interleaved blocks; schedule 30 s, delay 12 s, flank offsets 80 m
left then 60 m behind. Different values could change the contrast; these are not a search
for the best fixed policy or an isolation of model inference latency.

All arms use `battle/support_timing.py`'s one executor. It resolves types to unit IDs and
issues the infantry's persistent running melee attack at its first legal visible target.
It never uses setup, evaluation, replay frames or hidden enemy state. Cavalry treatments:

| Class | Trigger and orders |
|---|---|
| `Direct` | First legal observation: attack |
| `Opening` | First legal observation: flank |
| `Scheduled` | First legal observation at/after the proposed schedule: flank |
| `Contact` | Both public infantry records first show melee: flank |
| `Delayed` | Same cue: freeze the route, withhold it for the proposed battle-time delay |
| `NoneIntervention` | No cavalry orders or toggle changes; engine automation remains |

A flank is one batch: move left of the observed enemy, queued move behind that point,
queued melee attack against that same ID. Bearing 0 faces +z; left is then -x. The route
uses cue-time geometry, including in `Delayed`; it is not recomputed. No repeated attacks,
retargeting, route repair or automatic restart. The cue is an observable flag condition,
not independent proof that those regiments are fighting each other. Missing targets can
postpone submission; the trace retains actual cue/submission times. Rejected or incomplete
acknowledgements stop the attempt. An accepted but ineffective order stays visible in the
record and must be rejected by action-effect review, not treated as success.

JUDGEMENT: Executor details — Codex, 2026-11-04: running melee attacks and a single queued
route implement the supplied simple executor. Walking, waypoint-by-waypoint dispatch or
reissuing attacks could change arrival time and outcomes; all diagnostic results depend on
these details. No live feasibility claim follows from legal orders alone.

## Repeatable live check

Owner agreed 2026-11-04: "Use the proposed exploratory rule". The earlier JUDGEMENT markers
remain visible; the agreement does not establish that the candidate works.
Run from committed main after landing, with no other game controller/queue. Retain every
attempt and the full source/configuration/game/mod provenance. `doctor` is read-only; tell
the owner about any build mismatch and do not re-pin automatically.

```bash
uv run --locked python -m twwarhammer3 doctor
uv run --locked python -m twwarhammer3.battle.support_timing runs/support-timing-live/translated-v2/plan.json
# Owner-agreed exploratory comparison, after setup/action-effect checks:
uv run --locked python scripts/wh3_queue.py runs/support-timing-live/translated-v2/plan.json
uv run --locked python -m twwarhammer3.battle.support_evidence runs/support-timing-live/translated-v2/plan.json runs/support-timing-live/translated-v2/annotations.json
uv run --locked python -m twwarhammer3 report runs/support-timing-live/translated-v2/block-* --output runs/support-timing-live/report
```

For the current verification session, `runs/support-verify/audit_play.py` wraps ordinary
`play` with passive Windows video/state capture and independent native API readings.
Its `reading.lua` enumerates native unit IDs instead of calling the mod's unit recorder.
The scripts and their hashes are retained with each attempt's `audit/instrumentation.json`.
They submit no orders or speed changes. This evidence is private to verification.

JUDGEMENT: Verification sampling — Codex, 2026-11-04: read three units every completed
100 ms engine tick, with the recorder's existing 30 fps video and 0.2 s Windows samples.
Coarser sampling costs less but widens event brackets. Check overhead and video fidelity
in the pilot, then freeze the same instrumentation for every comparison arm.

```bash
uv run --locked python runs/support-verify/audit_play.py --scenario emp-support-timing-v2 --policy twwarhammer3.battle.support_timing:Contact --episodes 1 --observe-ms 1000 --tick-ms 250 --interval-ms 0 --start-timeout 900 --episode-timeout 1320 --run-timeout 2280 --record-replay --output runs/support-timing-live/pilot-contact-02
# After independently checking the pilot, use the ordinary queue with the observer:
uv run --locked python runs/support-verify/audit_queue.py runs/support-timing-live/translated-v2/plan.json
```

Before the comparison, inspect the pilot's `audit/video/video.mkv`, Windows clock journal,
`audit/native/native.jsonl`, initial setup readback and first engine ending. Preserve the
pilot separately from the 18 attempts. A native/capture failure fails the instrumented job
while retaining its engine result. No normal ready signal alone proves useful recording.
Review video clock transitions against state samples; do not infer contact from distance,
or treat a later native read as the first-ending value. A disagreement stops the check.

The plan generator writes only files; it requires committed sources. It records every
attempt with a distinct directory, one episode per fresh launch, and `keep_going: false`.
Each `block-N-ARM/episode-0000/` retains trace, replay, result and mod log. Manifest and
lobby readbacks sit one level above. The queue state records failures and unstarted jobs.
Never silently replace a failure. Stop on a setup/executor defect, retain the evidence,
version a repair and freeze a new plan before restarting the affected comparison.

Before accepting any primary comparison, independently compare lobby and engine/video
readings against the declaration: recruitment, type-to-ID mapping, ranks, initial health
and entities, positions, facing, widths, visibility, supported toggles and usable routes.
Existing automatic placement checks allow their inherited tolerance; a pass alone does not
establish precise geometry or facing. Observe the actual movement, both waypoint legs and
cavalry contact. An acknowledgement proves submission only; proximity proves neither
contact nor a flank. Keep setup and action-effect notes in `runs/support-timing-live/check.md`,
with attempt names, IDs, battle-time brackets and evidence file/frame references.

The primary comparison is Contact versus Delayed. Review all six endings and confirm
independently that delayed cavalry contacted later, with support/contact timelines that
support the infantry–cavalry interaction. Missing cues, rejected/ineffective orders,
ambiguous contact or inadequate frames make the mechanism comparison inconclusive.
Direct, Opening, Scheduled and NoneIntervention remain controls even if they win easily.
A failed contrast does not authorize strengthening the enemy or increasing delays.

JUDGEMENT: Proposed readiness check — Codex, 2026-11-04, supplied plan: after setup and
order-effect checks, propose either 3/3 Contact wins and 0/3 Delayed wins, or identical
engine results across all six and every Contact attempt at least 0.10 higher in
`H = (Swordsmen HP fraction + Knights HP fraction) / 2` than every Delayed attempt.
Weights or a confidence-based rule could change acceptance; this is not an adopted rank.

`support_evidence` reports the proposed numerical contrast separately and **never marks
readiness verified**. Independent later-contact and interaction evidence is still required.
Three attempts per arm cannot establish a reliable effect size or controller ranking.
HP uses the engine's first-ending read, without filling missing units as dead. Terminal
entities, routing/shattered/departed flags and available morale are retained separately.
Observed cue, movement, melee and loss-of-support proxies carry intervals; missing frames
widen them, and same-interval events cannot be ordered. The support proxy is routing,
shattered or zero living entities; it cannot describe every way useful support ends.
Submission, acknowledgement, battle-time observation age and Windows file-write timestamps
remain separate. Existing WSL think-time values are not Windows latency measurements.

Offline challenges include swapped IDs, accepted but unexecuted orders, cavalry contact
after infantry rout, missing frames, and events in the same interval. Synthetic cases
establish reader/executor behavior, not an engine effect. Optional LLM/VLM tactic labels
remain outside scoring; use the [tactic-judge proposal](tactic-judges.md) only after comparison
with independently labelled recordings. No paid judge or policy call is part of this work.

## First live setup attempt

At `b3eb799`, `runs/support-timing-live/pilot-contact-01/` stopped as
`unsupported_or_invalid` with zero policy decisions and no engine ending. It is a setup
failure, not a loss or a timing comparison. The native reader independently measured the
Swordsmen 29.2068 m from requested `(0,0)` at 5,200 ms; the video shows the foot formation
along a cliff edge. Nearby coarse terrain samples are obstructed. The checker was not
loosened. The first planned 18 attempts remain unstarted; `plan-stop` prevents their launch.

The lobby and initial API readings matched the two friendly types and one Greatswords,
rank zero, declared settings and full health/entities. All three support defend mode,
which read false; fire-at-will/skirmish were unsupported. The enemy resumed native movement
and formation changes. This one attempt establishes no action-effect, ending-HP or timing
mechanism result. Review: `runs/support-verify/review/pilot-contact-01/`.

JUDGEMENT: Proposed placement repair — Codex, 2026-11-04: translate all starts by `(0,-160)`:
Swordsmen `(0,-160)`, Knights `(-100,-100)`, Greatswords `(0,-320)`. Relative geometry stays
fixed; terrain or a different translation can change the battle. The owner selected it
on 2026-11-04: "Use the proposed translation (Recommended)".

`runs/support-verify/geometry-proposal.png` plots that proposal against the saved grid.
The new positions and opening waypoints have nearby clear coarse samples, not proof of usable
formations/routes or absence of forests. Freeze a new source/plan and repeat
the pilot before the comparison. Preserve the original failed attempt and unstarted plan.

## Owner demonstration

The separate `battle/manual_demo.py` path sets/readbacks the same lobby and deployment,
uses the existing observer mode's temporary setup controllers, and releases them. It never
submits battle orders, starts deployment, pauses, changes speed or enables a paused model
controller. The owner starts the battle, waits for the setup readback, then plays. Only the
owner may pause. Live handover, capture and setup effects remain unverified. In particular, the observer
borrows controllers for teleport and defaults in one tick; the combined release/placement
path must pass the independent geometry check before a manual demonstration counts.

JUDGEMENT: Manual sampling — Codex, 2026-11-04: propose 30 fps window video and Windows
samples every 0.2 s; launch waits at most 60 s for video, finalization 10 s. Other sampling
or resource load changes evidence quality; recorder readiness and fidelity require live checks.

```bash
uv run --locked python -m twwarhammer3.battle.manual_demo record --output runs/support-timing-live/manual-01 --ffmpeg 'C:/Users/niv/AppData/Local/universal-modder/ffmpeg/bin/ffmpeg.exe' --timeout 3600
```

The installed Windows FFmpeg reports `gfxcapture` and `dup_frames` in its filter help
(`runs/support-timing/ffmpeg-gfxcapture.txt`); actual capture remains untested. The recorder
also requires libx264. The timeout
is an explicit Windows watchdog budget chosen for this session, including menus and owner
pauses. This command captures the owned game window, never focuses it or sends desktop
input. Files include `video.mkv`, video progress/log, Windows `capture.jsonl`, raw state
`trace.jsonl`, setup/engine ending, replay and manifest. An abort or failure is retained.
No audio or camera automation is needed. Before using it as evidence, inspect video for
black frames, gaps and correct window, and correlate visible battle clock with state samples.

A stopped clock may be a pause, a stalled script or a stalled game. It is not automatically
labelled as pause. Write independent video PTS labels (seconds from the beginning of the
video), including failed attempts, then attach them without rewriting the original record:

```json
{"reviewer":"owner","complete":true,"video_sha256":"SHA256_OF_VIDEO",
 "intervals":[{"start_s":12.0,"end_s":18.0,"evidence":"pause icon visible throughout"}]}
```

```bash
uv run --locked python -m twwarhammer3.battle.manual_demo label-pauses runs/support-timing-live/manual-01 runs/support-timing-live/manual-01-pause-input.json
```

An empty interval list explicitly means the reviewer inspected the complete video and
found no pause; absent labels mean unknown. A recorded manual win with checked setup and
pauses establishes human-demonstrated winnability only. Automated-interface feasibility
and the timing mechanism remain separate claims.
