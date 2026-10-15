# WH3 Visual Battle Report

Status: implementation in progress, 2026-10-15. Phases 1 and 2 are implemented;
offline validation and the live recorder off/on audit passed. Recording now defaults
on, with `--no-record-replay` available. The phase 3 capture/name/report candidate is
implemented; its native probe confirmed capture and names, but measured a 43 ms
capture call and clamped camera placement. A passive capture follow-up and the
authorized Sol low acceptance still follow. It extends the [offline field report](field-report.md); calibration
stays stopped. The owner requested these live checks separately.

## Goal

Show AI engineers and researchers what a language model did while commanding a real-time
battle: what it was told, what it decided and why it said it did, how stale that state was
when the engine applied the orders, and what happened. The game's imagery and its own
vocabulary (unit names, morale effects such as "Attacked in the rear") provide the
Warhammer flavour; each claim links to recorded evidence. The output stays one
self-contained offline HTML file from `stats --report … --report-html FILE`.

## What the report must make visible

These distinguish this benchmark from turn-based or paused-game evaluations. Figures are
from the first G1 Sol trial (`bench-g1-cavalry-ai10-01-20261014/episode-0002`, a win).

1. **The battle does not wait.** Each batch reached the engine 5.1 s after the state it was
   based on (median; 90th percentile 7.2 s, maximum 11.1 s), while scripted baselines
   decide about once a second. Between consecutive decision states, friendly units moved
   22 m at the median and 49 m at the 90th percentile. Show the age of every decision and
   what moved in the meantime.
2. **A visual game, perceived as text.** The model sees coordinates, unit lists and a
   32×32 grid of 32 m passability cells; it never sees the game. Show its view beside the
   game's own imagery. Map rejected orders over that grid: 23 of the 29 rejected orders
   were `unreachable` moves.
3. **One model, many units.** Each reply orders the whole army (436 orders in 96
   decisions, nine of them with no new orders). **Trace audit correction:** 436 orders
   received acknowledgements; 441 were submitted. The last five have no acknowledgement
   before the recorded ending. Show which units received attention,
   which kept old orders while under fire, and which orders the engine dropped.
4. **The model's own memory and stated plan.** It rewrote its battle notes in 29
   decisions and gave a reason with each one. Show them verbatim beside the engine's
   record, labelled as stated rationale.
5. **The same battle, different commanders.** Paired rematches replay the same deployment
   for scripted baselines and models. Walk-nearest lost at 411 s, run-nearest at 248 s and
   Sol won at 528 s. Show their paths on one map.
6. **Resources and their cost.** Show abilities used (17 orders) and left ready, unspent
   winds of magic, supplies (owner interest in sieges), model cost ($0.79), tokens, and a
   latency split into provider processing, network and the harness tick.
7. **Engine-judged outcomes.** Show the engine result, the timer classification and
   failures as recorded, never as gameplay losses.

## The page

One scroll, in this order. Narrow screens stack the replay map above its panels.

1. **Verdict line.** Scenario, controller identity (model, effort, controller), engine
   outcome, battle time, margin, decisions, median information age and cost. Show the
   evidence status (development pilot, synthetic) and the featured-trial rule here.
2. **Briefing.** The opening overhead still (phase 3), the scenario brief from the
   manifest, both armies as lists with readable names and class symbols, protected units
   marked, role,
   battle type, objectives and timer.
3. **Battle replay** (centre of the report):
   - **Map.** One glyph per unit at its position, rotated to its bearing, with side
     colour, class symbol and remaining strength. Badges show `melee`, `under_fire`,
     `wavering` and `routing`; trails show the last 20 s. Arrows show orders to their
     move point or attack target: dashed between basis and application, solid
     afterwards, and red with the engine's code when rejected. A toggle switches the
     background between the game view (phase 3) and the **model's view**, the
     passability grid exactly as the prompt gave it. Auto-fit frames the action, with a
     whole-map toggle and no pan/zoom.
   - **Timeline.** Play/pause, 1×/4×/16×, a scrubber and keys for the previous/next
     decision or event. Each decision is a bar from its basis time to its application
     time; for a one-request-in-flight model, the bars tile the battle. A strip below
     shows winds of magic and other army resources, marking ability casts.
   - **Unit lanes.** One row per friendly unit, coloured by engine state (idle, moving,
     melee, under fire, wavering, routing, dead), with markers for each order the unit
     received and each ability cast. These lanes show parallel demands and the model's
     attention; enemy lanes start collapsed.
   - **Decision inspector.** Selecting a decision shows its basis state as a ghost and the
     first state after application as solid units, with displacement lines. It also
     lists the stated reason, the change to the battle notes, each order with its
     acknowledgement, the latency split, tokens and cost. One collapsed disclosure holds
     the exact prompt and raw reply in a fixed-height, scrolling monospace box. The
     system and rules prompt appears once per job, in the evidence section.
   - **Bookmarks.** Rule-based events with factual template captions, each linked to the
     frame showing it. Detectors cover first contact, each rout, rally or death of a unit,
     protected-unit and general losses, ability casts, rejected orders, objective
     ownership changes, and accepted attacks followed by idle or no target within 5 s
     while the target lives ("order lapsed"). They also mark the longest think, timer
     warnings and the end. Morale effects appear in the game's words.
4. **Same battle, other commanders.** Small multiples of unit tracks on the shared map, one
   per trial of the selected scenario, each with outcome, time and margin. Selecting one
   opens it in the replay.
5. **Comparison and evidence.** The field report's sections, unchanged: groups,
   uncertainty, timing charts, downloads and printing.

The featured trial is the earliest completed model trial; it is never chosen by outcome.
The reader can open any trial.

## Style

The field report's ivory and brass shell holds the text; the replay sits on a dark
canvas. Game screenshots provide most of the flavour. Two fixed,
colourblind-safe side colours apply throughout the map, lanes and charts; faction names
and colours appear only in the briefing. The page uses the field report's fonts and
contains no textures, lore text or invented quotes. All prose is plain and factual,
with game terms only where they are data.

## Honesty rules

- Positions come only from recorded frames. Missing intervals stay visible as gaps and
  are never interpolated.
- Enemies appear only while visible to the player; otherwise a timestamped last-seen
  marker remains.
- Issued, queued, acknowledged, rejected and dropped orders remain distinct from
  observed movement.
- Captions report events. The model's reasons and notes appear only as quoted, stated
  rationale. The report does not infer intent or claim that an event decided the battle,
  and no model writes the narration.
- Stills are presentation, not policy input. If one shows a unit the player could not
  see, it is labelled as such.
- Synthetic fixtures keep their label in the page and every export.

## Data

| Needed | Today | Added |
|---|---|---|
| Unit states | At each decision basis: about 1 s apart for scripted controllers, 5.1 s (median) for the Sol trial | 1 Hz frames throughout (phase 2) |
| Orders, acknowledgements, latency, reasons, notes, prompts, tokens, cost, provider processing time | `trace.jsonl` | — |
| Scenario brief, protected units, controller cards, paired trials | `manifest.json`, `result.json`, collector | — |
| Terrain | 32 m passability grid in each observation | — |
| Objective positions and ownership | Observation `mode`, tick-integrated ownership | — |
| Readable unit names | Type keys only | UI context lookup (phase 3) |
| Imagery | None | Stills (phase 3) |

**Recorder (phase 2).** The battle script already rewrites `observation.json` each
interval. Once per battle second, it also appends a compact public frame (ids,
positions, bearing, men, hp, morale fraction, state flags, target/destination and
resources) to a per-battle file in the bridge. The harness copies that file into the
episode directory. It records the player's view only and never feeds a policy: the
synchronous controller loop does not read the bridge while a model thinks, so this
covers exactly the interval the report needs. Recording is always on if its measured
cost is negligible. Otherwise, a session key switches it on, and the manifest records
that setting with the recorder version.

**Imagery (phase 3).** One owner-approved probe in a short scripted battle answers:
- Does `common.take_screenshot` write a file, where, at what size, and at what
  frame-time cost at 1×? The fallback is the passive desktop capture from the
  [image-track notes](benchmark.md#23-observation-contract-obs-v1).
- Can `battle_camera` place an overhead view at deployment, and can a known camera
  height and field of view map world coordinates to pixels? If so, that shot is the map
  background. If not, the map keeps the passability grid, with the still shown beside it.
- Unattended, the camera remains where deployment leaves it. Action stills therefore need
  the script to aim it, at the centroid of the largest melee, on at most three throttled
  triggers (first contact, first rout and the end). Moving the camera changes only the
  display, not gameplay.
- Can the UI context return localised unit names? Prettified type keys are the
  fallback.

The harness resizes stills to WebP. That needs Pillow in an optional `report` extra,
since the base install has no dependencies. This capture should work later for the
planned `obs-v1+image` track, but that track is not built here.

## Code

- `battle/replay.py` (new) derives everything: an episode directory goes in, a compact
  replay payload of frames, decisions and events comes out. Event detectors are small
  functions tested with pytest. The digest's existing extraction is reused where they
  overlap.
- `report_assets/replay.js` (new) renders precomputed data with SVG and makes no
  decisions; there is no framework or build step. Payloads are gzip and base64, decoded
  by the browser's `DecompressionStream`.
- `report_html.py` embeds replay payloads beside the collector output, whose statistics
  stay unchanged. Compatibility checks gain the recorder version.
- The Lua change is one recorder function in the existing battle script and the
  harness's file copy. Phase 3 adds a camera/still function and a `play` switch for
  stills.

## Phases

Each phase ships on its own; the report can stop after any of them.

1. **Replay from existing traces.** No game run and no recording changes. The phase
   builds every section of the page from the decision-basis states already in
   `trace.jsonl`. "After application" uses the first observation carrying the
   acknowledgement, labelled as such. Unit names are prettified type keys. Validate on the
   three G1 cavalry trials and the synthetic fixture. Payload figures must match the
   trace: 96 decisions, 436 acknowledged orders (441 submitted), 29 rejections and
   $0.79336 for the Sol trial.
   Detectors are tested on known events, such as the general's rout in the Sol trial
   (the public trace does not confirm his death),
   and on a fixture where missing data must yield no caption. The existing Playwright
   check extends to the replay: keyboard, narrow layout and offline load.
2. **1 Hz recorder.** Unit tests use a fake bridge file to cover gaps, rematch
   restarts, interruption, terminal frames and stable unit ids across visibility changes.
   On owner request, one scripted cavalry battle runs with recording on and off to
   compare the clock ratio and frame cost; it stays unpaused at 1×.
3. **Imagery.** The probe above, then capture and unit names. On owner request, the
   probe runs in a scripted battle and one Sol low battle (about $0.80) checks the whole
   page on a model trial. Screenshot failures are recorded and never stop or delay
   gameplay or order submission.

Size budget: about 0.5 MB compressed replay per trial and stills only for the featured
trial of each controller. Nine trials must fit under 20 MiB without dropping any trial's
evidence. Exact prompts and replies are embedded for every model trial: the Sol trial's
96 come to 855 KB raw and 44 KB compressed.

## Left out on purpose

Unit art from the game files, pan/zoom, printed replay scenes, model-written narration,
hidden enemy positions,
reconstruction of historical runs beyond their traces, per-map pixel coordinates or
manual tracing, and desktop input of any kind. A separately stored ground-truth layer,
clearly labelled as hidden from the controller, could come later for ambush scenarios.

## Acceptance

Without opening logs, a reader can:
1. state the tactical problem and both forces;
2. see how old each decision's information was and what moved meanwhile;
3. see which units the model attended to, which it left and which orders failed;
4. read the model's stated plan and notes beside what the engine recorded;
5. compare the model with baselines on the same battle;
6. find the cost, latency split and statistical comparison.

## Owner decisions (2026-10-14)

1. **No unit art.** Screenshots, readable names and class symbols carry the visuals; no
   images are extracted from the game's packs.
2. **Exact prompts are included** without cluttering the page. They stay collapsed in
   the decision inspector, and the system prompt appears once per job. This replaces
   the field report's rule of leaving prompts out.
3. **Scripted camera moves** during unattended jobs are accepted.

## Implementation evidence (2026-10-14)

The generated offline artifact is `runs/twwarhammer3/reports/visual-report.html`;
`visual-report-demo.html` is explicitly synthetic. Both are self-contained and retain
the field report's statistics. `battle/replay.py` derives public frames, order identity,
events and timing; the SVG renderer includes keyboard navigation, lanes, resource
samples, exact prompts/replies, quoted notes and shared-scale trial tracks. Browser
evidence is under `runs/twwarhammer3/reports/visual-browser/`.

The G1 trace regression checks all three trials: 423/302/98 recorded frames; the Sol
trial's 96 decisions, 441 submissions, 436 acknowledgements, 29 rejections (23
unreachable), nine empty decisions, 29 note changes and $0.793363. It also checks that
the general's disappearance never becomes a death caption. Compressed replay payloads
are below 160 KB each, including exact prompts and replies. A nine-trial size check
is below the 20 MiB budget. No missing positions are interpolated.

Provider processing time is recorded; network-only latency and the exact harness tick
are not separately measured. The inspector therefore labels call-minus-provider and
roundtrip-minus-think as residuals and explains what they contain. It does not claim
that these wall-clock components sum to battle-clock information age.

The 1 Hz recorder now defaults on; `play --no-record-replay` disables it. The
owner-requested off/on checks averaged 2.851 ms total CPU per sample, with battle/wall
clock ratios 0.998213 off and 0.997703 on. This single pair supports low measured
cost, not a precise causal overhead estimate. The 260 frames included the terminal
result and matched public ids/types at all 104 timestamps shared with the trace.
Full audit: `runs/twwarhammer3/visual-probes/recorder-acceptance.json`. Recorder settings/version enter compatibility groups. The Lua recorder
has separate enemy sighting memory, so it cannot change policy knowledge, and flushes
its terminal frame before publishing the result. The harness copies a battle-specific
file after the episode; malformed final lines and gaps remain visible in the replay.

Prepared owner-requested probes (new output directories, committed sources required):

```bash
uv run --extra report python -m twwarhammer3.battle.visual_probe --case off \
  --output runs/twwarhammer3/visual-probes/recorder-off
uv run --extra report python -m twwarhammer3.battle.visual_probe --case on \
  --output runs/twwarhammer3/visual-probes/recorder-on
uv run --extra report python -m twwarhammer3.battle.visual_probe --case imagery \
  --output runs/twwarhammer3/visual-probes/imagery
```

These run sequentially with `rush_nearest`, unpaused at 1×, without paid model calls.
The short imagery probe measures an actual native screenshot and records camera
position/target and candidate UI name lookups. No world-to-pixel registration is claimed
before examining that evidence. If native capture blocks gameplay, use the passive
capture fallback. Production triggers are implemented behind `--stills`; the probe must establish
the native capture behavior before the authorized Sol low page check.
