# WH3 Benchmark — Field Report

An offline HTML presentation of the existing benchmark collector. Open the generated
file directly in a browser; it needs no server, network, frontend build or API calls.
The HTML, CSS, JavaScript and compact evidence are embedded in that one shareable file.
The source assets live in `src/twwarhammer3/battle/report_assets/`; the exporter is
`battle/report_html.py`.

## Regenerate from saved evidence

From the repository root, this command recreates the initial cavalry report, including
the owner interruption during setup of the second job:

```bash
uv run python -m twwarhammer3 stats \
  --report runs/twwarhammer3/battle/bench-g1-cavalry-ai10-01-20261014 \
           runs/twwarhammer3/battle/bench-g1-cavalry-ai11-01-20261014 \
  --report-html runs/twwarhammer3/reports/field-report.html
```

The directory is created when necessary. Optionally add
`--report-json runs/twwarhammer3/reports/field-report.json` to save the collector's
full metrics, and redirect stdout to save the existing text report. The collector runs
once even when both export options are present. Each export option requires `--report`.

The initial result is **Development pilot: one independent launch**: three valid / three
started trials. Across all supplied jobs, the separate interrupted setup adds 64.48 s
and zero trials. Neither that interruption nor an unrun catalogue entry becomes a loss.
The controlled added-age view says **Not measured yet** until added-age trials exist.
This report does not resume calibration or establish admission.

## Reading and sharing

- Choose a scenario and compatible settings. Recorded manifests supply historical
  briefs, forces and status; current catalogue entries are explicitly unrun placeholders
  within the supplied report. Their presence says nothing about other saved jobs.
- Controller rows identify model, effort and controller (or a scripted baseline).
  Columns sort on activation; initial order is alphabetical. Checkboxes select chart,
  trial-table, JSON and printed rows. There is no overall score or ranked leaderboard.
- Switch between mean information age at order issuance, inference cost and controlled
  added age. Each point represents one valid trial with available metrics. Select with
  a click, Enter or Space for unrounded values; the table remains available without
  hovering. Missing metrics are unavailable, never plotted as zero.
- SVG and PNG downloads include scenario, development/demo status, sample counts,
  controller identities and relevant settings. Displayed JSON retains selected original
  evidence groups and pairs, plus job provenance and all-job throughput. Print / PDF
  includes the selected comparison, trial values and tactical results; expand additional
  evidence before printing to include it. Wide tables and charts scroll on narrow screens.

Evidence groups are never pooled. Groups differing only in requested model/effort can
appear side by side when scenario, source revision, game, interface and observation/tick/
pacing settings match. Missing provenance prevents cross-group comparison. Added ages
remain distinct rows within their original groups. No cross-model paired comparison is
invented across independent launches. Controller-card mismatches inside an already
aggregated row are refused instead of receiving a misleading single identity.

Rates, Wilson intervals, launch-clustered paired intervals and margins come from the
existing collector unchanged. Its non-timer win rate counts non-timer wins over **all
valid outcomes**, including time limits. Engine wins at the timer remain separate from
non-timer wins. Repeated valid trials of one controller in one launch withhold the Wilson
interval; one paired launch cannot provide a paired interval. Cost per attempted trial
uses the collector's recorded USD sum / started trial records, including failures, but
is withheld when cost records are incomplete. Scripted inference costs zero.

Supplies and reinforcement purchases have neutral labels. Accepted purchases do not
prove arrivals. Objective-control shares identify engine-time integration versus legacy
observation sampling. Job and paired identifiers are portable directory names; source
hashes and revisions remain available. The [visual replay](visual-report-plan.md) now
embeds compressed public replay frames and exact decision prompts/replies. Prompts
stay collapsed in the inspector; recorded system/rules prompts appear once per job in
the evidence section. Share the generated file, not the original evidence directory.

The replay opens the earliest completed model trial, independent of outcome. Its map
shows recorded positions, last sightings and submitted orders; lanes expose concurrent
unit states and controller attention. Scrubbing never interpolates missing frames.
Use the previous/next decision and event controls, or focus the map and use arrow keys,
brackets and Space. Narrow layouts stack the map above the inspector. Replay scenes
are excluded from printing; the existing statistical print view remains available.

Optional `play --stills` supplies game images and localised unit names. Opening uses
an overhead view; action stills use a closer oblique view, with an observed approach,
incoming fire or melee in the first action slot. Capture is passive and independent
of order submission. Images are never policy inputs, and failed or throttled captures
stay labelled. The game must be foreground for capture. The public grid remains the
map because world/pixel registration is unverified. Still images are capped at four
per featured controller trial and 256 KiB each; WSL conversion needs `--extra report`.

## Separate synthetic demonstration

`tests/fixtures/wh3_field_report_demo.json` contains **invented** Demo controller A/B/C
results, independent launches, 0/6/10-second conditions, objective/resource metrics,
a timer win, repeated rematches, a missing metric, a failure and a setup interruption.
It is marked synthetic at report, group and job levels. The exporter refuses a mixture
of recorded and synthetic evidence, and synthetic reports contain no catalogue entries.

```bash
uv run python -m twwarhammer3.battle.report_html \
  --demo tests/fixtures/wh3_field_report_demo.json \
  --output runs/twwarhammer3/reports/field-report-demo.html
```

The page and every export retain the synthetic label. This is a presentation fixture,
not a source of benchmark claims or an input to the results register.

## Verification

```bash
uv run pytest tests/twwarhammer3/test_wh3_report_html.py tests/twwarhammer3/test_wh3_benchmark.py
uv run ruff check .
```

An optional browser check uses Playwright installed outside this project. Generate both
HTML files above and the companion `field-report.json`, then run:

```bash
NODE_PATH=/path/to/playwright/node_modules node tests/twwarhammer3/check_wh3_report_browser.cjs \
  runs/twwarhammer3/reports/field-report.html \
  runs/twwarhammer3/reports/field-report-demo.html \
  /tmp/wh3-report-browser-checks
```

It opens local files with the browser offline, verifies original summary values,
selection, sorting, keyboard access, narrow layout, missing results, timer outcomes,
evidence separation, image/data downloads and printing. It saves screenshots and a PDF
outside the evidence directories for inspection. Playwright is only a validation tool;
the report itself has no third-party runtime dependency.
