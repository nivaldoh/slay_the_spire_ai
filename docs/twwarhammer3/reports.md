# WH3 benchmark reports

`twwarhammer3 report` turns saved job directories into one report in three forms: the
text report (printed and saved), the collector's full JSON, and the HTML report, one
self-contained file that opens offline in a browser and holds its own CSS, scripts,
evidence and images. It runs no game and makes no API call. The statistics come from
`battle/report.py` (definitions in [benchmark.md](benchmark.md#outcomes-measures-and-comparison));
`battle/report_html.py` and `battle/report_assets/` present them without recomputing,
`battle/replay.py` derives the replay, and `battle/capture.py` records frames and stills
during play. Engine facts behind the capture are in [integration.md](integration.md).

## Making a report

```bash
uv run python -m twwarhammer3 report runs/twwarhammer3/battle/JOB [JOB ...] \
  --output runs/twwarhammer3/reports/NAME
```

It prints the text report and writes `NAME.txt`, `NAME.json` and `NAME.html`. Give the
stem without an extension (`--output x.html` writes `x.html.html`). Pass every launch of
a comparison: one job is one instance, and paired intervals need several. Jobs that
stopped in setup stay in the all-jobs table and the throughput. Embedding stills needs
Pillow, which `uv sync --locked` installs (dev group); without it the command stops
with "Embedding game stills needs Pillow" before writing anything. Share the HTML file,
not the evidence directory: it names jobs by directory name, not local path.

## What the HTML report shows

In page order:
1. **Verdict** of the featured trial: controller, outcome, battle time, active margin,
   decisions, submitted and acknowledged orders, median order age and cost. The featured
   trial is the view's earliest completed model trial (by job start, then episode),
   never chosen by outcome; without one, the first trial.
2. **The tactical problem**: a selector of scenario and compatible settings, the brief
   from the manifest, settings, both forces and the declaration, and game stills when
   they were captured.
3. **Battle replay**. A map of recorded positions, facing, strength and state badges
   (melee, under fire, wavering, routing), timestamped last sightings of enemies, and
   order arrows: dashed until applied, solid when acknowledged, red when rejected. The
   background is the model's passability grid. Play at 1×, 4× or 16×, a scrubber, and
   previous/next decision and event (keys Space, ←/→, [ and ]). Below: decision bars from
   basis to application, army resources, and one lane per unit (enemy lanes collapsed).
   The decision inspector shows the basis state and the first state after application,
   the stated reason and notes as quotes, each order with its acknowledgement, the latency
   parts, tokens and cost, and the exact prompt and raw reply, collapsed. Recorded events:
   first melee, routs, rallies, deaths (marking protected units and the general), ability
   casts, rejections, lapsed attacks, objective changes, timer marks, the longest think
   and the end.
4. **Same battle, other commanders**: every trial's tracks on one shared map.
5. **Controllers**: a sortable table per evidence group with outcomes (won, lost, draw,
   time limit), the non-timer win rate and its interval, failures, cost and wall time.
   Selected rows feed the charts and exports. There is no overall score or ranking.
6. **Timing and tactical results**: one point per valid trial for measured information
   age, inference cost or controlled added age, the exact trial values, and objectives,
   protected units and resources.
7. **Evidence and definitions**: paired comparisons and their uncertainty; failures,
   interruptions and setup flags; all supplied jobs; metric definitions and the
   collector's limitations; each job's system or rules prompt once; provenance.

Downloads: the displayed JSON, the chart as SVG or PNG, and one trial's replay evidence;
Print / PDF prints the statistics without the replay. Narrow screens stack the replay
map above its panels.

Comparison views: groups sit side by side only when they differ in model or effort
alone; their samples and pairs stay separate, and a group with missing provenance gets
its own view. Each scenario in `scenarios.json` that has a `status` (its own or inherited
through `base`) and is absent from the supplied jobs appears as an unrun catalogue
placeholder.

## Rules the page keeps

Owner decisions (2026-10-14): no unit art from the game's packs (stills, readable names
and class symbols carry the visuals); exact prompts included but collapsed, with the
system prompt once per job; scripted camera moves allowed during unattended jobs.
2026-10-15: closer, low oblique action views, ideally before a charge, melee or
projectiles, chosen from observed public motion and events, within the four-still cap.

Honesty rules:
- positions come only from recorded frames; gaps stay gaps and are never interpolated;
- enemies appear only while visible to the player, then as timestamped last sightings;
- issued, queued, acknowledged, rejected and dropped orders stay distinct from observed
  movement;
- captions report events; the model's reasons and notes appear only as quoted, stated
  rationale; no model writes narration, and no caption claims an event decided the battle;
- stills are presentation, never policy input, and failed or throttled captures stay
  labelled;
- synthetic evidence keeps its label in the page and every export, and cannot be mixed
  with recorded evidence.

## Recording and stills

`play --record-replay` (on by default; `--no-record-replay` turns it off) makes the
battle script append one public frame per battle second (positions, bearing, men, health,
morale, state flags, targets, destinations and army resources) to a per-battle bridge
file, copied into the episode as `replay.jsonl` when it ends. It keeps its own sighting
memory and reads no hidden state. Its measured cost (one scripted off/on pair, 2026-10-15):
2.851 ms of CPU per frame and battle/wall clock ratios of 0.998213 off and 0.997703 on;
260 frames came to 1.56 MB. Without the file, the replay uses the decision-basis
observations in `trace.jsonl`, about one per decision.

`play --stills` adds up to four images per battle and readable unit names
(`unit_names.json`, `stills.json`, `still-<battle>-<trigger>.png`). The slots: the
opening (overhead), one early action (visible opposing units closing within 100 m
before observed melee, else incoming fire or first melee), the first rout and the
ending. Captures are 30 battle seconds apart except the ending; an early action inside
that spacing is deferred, keeping its trigger time. The battle script moves the camera
(the camera only: no pause or slowdown) and a thread of the controller grabs the screen
through Windows Python with Pillow, outside the order loop, in about 40-75 ms. The game
must be in the foreground; otherwise the capture is recorded as failed. Stills are not
registered to the map. The report embeds them as WebP of at most 256 KiB, for one
trial per controller (the earliest completed), and keeps the others as metadata.

Size: a replay payload is under 160 KB compressed for the G1 trials, exact prompts
included; nine such trials fit well under 20 MiB (a test checks it). The visual report
with four trials and two stills is about 1.6 MB.

## Saved reports

Under `runs/twwarhammer3/reports/` (local, not in Git), read from each JSON's `jobs`:

| Artifact | Jobs under `runs/twwarhammer3/` |
|---|---|
| `field-report.{html,json,txt}`, `g1-cavalry.{json,txt}` | `battle/bench-g1-cavalry-ai10-01-20261014`, `battle/bench-g1-cavalry-ai11-01-20261014` |
| `g1-cavalry-ai10-01.{json,txt}` | `battle/bench-g1-cavalry-ai10-01-20261014` |
| `visual-report.{html,json}` | `battle/visual-sol-low-20261015` and the two G1 jobs |
| `visual-report-g1.{html,json}` | the two G1 jobs |
| `close-camera.{html,json,txt}`, `close-camera.png` | `visual-probes/close-imagery-r2-20261015` |
| `close-camera-first.{html,json,txt}` | `visual-probes/close-imagery-20261015` |
| `field-report-demo.html`, `visual-report-demo.html` | synthetic (the deleted fixture; `make-wh3-replay-demo.py` beside them) |
| `bench-b*.{json,txt,md}` | the b1-b9 screens and audits named in [log.md](log.md) |
| `visual-browser/` | browser check screenshots and exports |

They predate the 2026-10-15 cleanup. A rebuilt verdict shows the collector's median order
age (non-empty batches): 5.25 s instead of 5.1 s for the G1 Sol trial, 4.2 s instead of
3.9 s for `visual-sol-low-20261015`; replay labels name controllers as the table does.
To rebuild one (this overwrites it; choose another stem to keep the saved file):

```bash
uv run python -m twwarhammer3 report runs/twwarhammer3/battle/visual-sol-low-20261015 \
  runs/twwarhammer3/battle/bench-g1-cavalry-ai10-01-20261014 \
  runs/twwarhammer3/battle/bench-g1-cavalry-ai11-01-20261014 \
  --output runs/twwarhammer3/reports/visual-report
```

## Synthetic demo and checks

```bash
uv run python tests/twwarhammer3/make_wh3_report_demo.py runs/twwarhammer3/reports/report-demo.html
```

writes an HTML report from invented jobs (Demo controllers A, B and C over two launches
each at 0, 6 and 10 s added age, with a timer win, a repeated rematch, a missing metric,
a policy failure, a setup-only interruption and one invented replay). It goes through
`report.collect`, so it always matches the current collector, and every view says
synthetic. It is never benchmark evidence.

Tests: `uv run pytest tests/twwarhammer3` (the report, replay and capture tests include
the imagery Lua under Lua 5.1). The optional browser check uses Playwright installed
outside the project, once:

```bash
npm install --prefix ~/.cache/wh3-playwright playwright@1.61.1
~/.cache/wh3-playwright/node_modules/.bin/playwright install chromium
NODE_PATH=~/.cache/wh3-playwright/node_modules node tests/twwarhammer3/check_wh3_report_browser.cjs \
  /tmp/wh3-report-check runs/twwarhammer3/battle/visual-sol-low-20261015 \
  runs/twwarhammer3/battle/bench-g1-cavalry-ai10-01-20261014
```

It builds `recorded.{html,json,txt}` from the jobs (which need episode traces) and
`demo.html` in the output directory, opens both offline in headless Chromium and checks
them against the collector's JSON and the demo's invented values: replay counts and
keyboard navigation, selection, downloads, printing to PDF, the 390 px layout, unrun
placeholders, synthetic labels and stills. It leaves screenshots, downloads and the PDF
there; keep that directory outside the evidence directories.

## Known limits

- Stills are not registered to world coordinates; the replay map is the passability
  grid, with images beside it.
- Order arrows show submissions and acknowledgements, not execution; the engine only
  confirms issuing.
- Without the recorder, replay frames are only the decision-basis states.
- Single-job reports still list the 15 unrun catalogue scenarios as placeholders, as
  before the 2026-10-15 cleanup; removing them is the owner's decision.
- A capture fails when another window is in the foreground, and Windows Python without
  Pillow records every capture as failed.
- The latency parts in the inspector (call minus provider processing, roundtrip minus
  think) are wall-clock residuals: they include network, queueing and harness time and do
  not sum to the battle-clock information age.
