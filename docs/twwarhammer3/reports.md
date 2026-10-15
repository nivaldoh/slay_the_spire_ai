# WH3 benchmark reports

`twwarhammer3 report` turns saved job directories into a text report, the collector's full
JSON and an HTML page that opens offline and holds its own CSS, scripts, evidence and
images. It runs no game and makes no API call. The page follows the owner's redesign brief
([WH3_report_redesign_guide_for_Codex.md](WH3_report_redesign_guide_for_Codex.md)): watch
the battle, understand the decisions, compare the results. Statistics come from
`battle/report.py` ([definitions](benchmark.md#outcomes-measures-and-comparison)), the
replay from `battle/replay.py`, the presentation from `battle/report_html.py` and
`battle/report_assets/`, curated text from `configs/twwarhammer3/report_notes.json`, and
frames and stills from `battle/capture.py` during play ([integration.md](integration.md)).

## Making a report

```bash
uv run python -m twwarhammer3 report runs/twwarhammer3/battle/JOB [JOB ...] \
  --output runs/twwarhammer3/reports/NAME
```

It prints the text report and writes `NAME.html`, `NAME.json` and `NAME.txt` (a stem:
`--output x.html` writes `x.html.html`). Pass every launch of a comparison: one job is one
instance, and paired intervals need several. Embedding stills needs Pillow (`uv sync
--locked`); without it nothing is written. Rebuild after editing the notes file. Share the
HTML file, not the evidence directory. Margin, throughput, paired comparisons, failures,
setup flags, the all-jobs table, definitions and limitations are in the text and JSON only.

## The page

One scenario at a time (a select when several have battles; unrun catalogue scenarios
never appear), in three sections:

- **Watch a battle**: the scenario's question and challenge; the run line (featured-run
  tag, readable controller name such as `gpt-6-sol · low reasoning · rules-only prompt`,
  engine outcome with duration, "Won in 6:22" or "Lost at the time limit (20:00)", sample
  size); its conditions in one sentence (text observations, the battle running at 1×
  while the model thinks, enemies only while seen; a scripted rule); "Watch the featured
  maneuver" and "Watch the full battle" at 4×; a list of the scenario's battles; the viewer.
- **What happened**: the run's analyst notes as cards that play their moment, else its
  key events; embedded stills only, captioned "spectator camera at m:ss · not what the
  model saw"; collapsed, all recorded events and per-unit state timelines.
- **Compare results**: a table per run set, the featured run's set first: Model / setup;
  Battles won (engine wins over valid battles, time-limit and failed counts, a 95%
  interval only from five valid battles without a time-limit outcome); Typical order
  delay ([Timing](#timing)); Inference cost / battle (API cost over battles started,
  failed ones included); Replays. Footnotes define delay and cost, state the time-limit
  rule and call rows of one or two battles examples; a line counts setup-only launches.

A run set is a comparison view: groups sit side by side only when they differ in model or
effort alone, samples never pool, and a group with missing provenance gets its own set. A
later set's caption lists its differences from the first in plain words, without hashes
(code revision, game build, track, recorder or stills on or off, observation timing,
scenario definition), and whether controller code and prompts are identical, differ or
could not be compared; with no listed difference it is described as a separate launch.

The footer opens **Run settings** for the run in the viewer (scenario, controller and its
timing in plain words, interface, recording and provenance; collapsed, the declared brief
and, for model runs only, the prompt the model received, named by policy) and offers the
report JSON and this replay JSON.

### The replay viewer

Map and moment panel stack below 960 px; at 390 px the map starts on the first screen and
nothing scrolls sideways. The map draws the passability grid (north up, fixed framing per
replay) and each unit's side, role glyph, facing, label ("KR1"), strength and state, with
hollow last sightings of unseen enemies, 20 s trails and, faintly, the waypoints a unit
was ordered to and has not yet come within 30 m of, drawn from where it is; a selected unit
adds its observed path, standing orders (numbered waypoints, attack rings, rejected steps
red) and a card with role, state, orders and base stats. Controls: 1×, 4× or 16× playback
(the battle ran at 1×), decision (←/→) and event ([ ]) steps, scrubber, timeline strip.

The moment panel shows the latest decision applied by the replay time, never a reply
before it was applied ("Waiting for the model's next reply" until then): the stated
reason, quoted and attributed; the orders in plain words ("Lord: run 320 m north-west,
then attack Great Cannons in melee"), "Keeping current orders", or "orders refused by
validation"; up to six "what happened next" facts from the recorded frames; and how old
its battlefield view was. Prompt, reply, timing detail and cost stay collapsed. "Inspect:
what moved while waiting" draws the basis observation as outlines and the first frame
after application as solid markers, joined by straight lines.

More than 1.5 × the sample interval past the last frame, the map says "No observation
recorded during this interval". A run without the 1 Hz recorder shows one notice instead:
positions update only when the controller observed the battle (about every N s). Its
sample interval is the median spacing of those observations (at least `observe_ms`), so
only unusually long gaps are flagged.

## Curated notes: `configs/twwarhammer3/report_notes.json`

Reader-facing text that is neither policy input nor recorded evidence. It is committed and
inside `twwarhammer3 play`'s source scope: editing it stops a running job, so draft it in
a worktree while one runs. Three maps:

- **`scenarios`**, by scenario name: `title` names it, `question` heads the page,
  `challenge` states the task and its real objective. Without an entry: its `family` or
  name and the declared `brief`.
- **`units`**, by unit type key: `name` is the game's onscreen name (checked against its
  English localisation), `short` the map label (numbered for duplicates), `role` a few
  words, `about` one sentence on how the unit differs, `glyph` one of `general`,
  `cavalry`, `missile_cavalry`, `infantry`, `polearm_infantry`, `missile_infantry`,
  `artillery`, `monster`, `unknown`. Every comparison in `about` must hold in the recorded
  base stats (`setup.unit_base_stats` in `result.json`); claim nothing the records lack.
  Without an entry: the recorded name, initials as the label, role and glyph by class.
- **`runs`**, by `<job directory name>/<episode>`: `selected: true` features the run;
  `highlights` are its analyst notes:

  | Field | Meaning |
  |---|---|
  | `time_ms` | the moment on the battle clock; for orders, their issue time (`applied_ms`), where the panel shows them |
  | `lead_in_s` | seconds of replay before it, to see the situation develop |
  | `end_ms` | where "Watch" pauses (null: it plays on; the caption lasts 20 s) |
  | `title`, `text` | a short title and one sentence on why the moment matters |
  | `units` | roster ids (`f1`..., `e1`...), shown as chips |
  | `kind` | `plan`, `maneuver`, `turning_point`, `trouble` or `outcome` |
  | `feature` | true for the moment "Watch the featured maneuver" plays (else the first note) |
  | `refs` | backing records (`trace.jsonl:LINE`, `replay.jsonl:LINE`), never printed |

Analyst notes are curated after reviewing the records and labelled so (the current ones
were drafted by agents, checked against the records by two independent reviewers, and
await the owner's review): a few
per featured battle (a plan, a maneuver, trouble or a recovery when the records show it,
the outcome), with no manufactured balance. Check every time, name, distance and
quotation against the lines in `refs` (`digest JOB/episode-NNNN --at SECONDS` helps);
state no cause that timing alone suggests; quote the model only as its stated reason.

**Featured run**, per scenario: a battle with `selected: true` ("Selected example"); else
the earliest completed model battle by job start, then episode; else the first battle.
It is never chosen by outcome. Its run set comes first in Compare, and the other sets
are described by how they differ from it.

## Timing

- **Durations** come from each battle's `battle_ms`, the engine's battle clock
  (`battle_s` only where it is missing).
- **Typical order delay** (Compare): per battle, the median battle-clock age of the
  observation behind each batch of orders when the game acknowledged it, batches with
  orders only (`order_age_s`); across battles, the median of those medians
  (`order_age_median_s`). `visual-sol-low-20261015`: 4.2 s over 45 batches; 3.9 s over
  all 91 applied replies, empty ones included.
- **Per decision** (moment panel): that reply's observation age when applied (battle
  clock) and the model's reply time (`think_s`, wall clock; median 3.41 s in that battle).
- **Technical detail only**: provider processing, call minus provider and round trip
  minus reply; the two differences are wall-clock residuals, never called network time.

## Rules the page keeps

Owner decisions: no unit art from the game's packs; exact prompts included but collapsed;
scripted camera moves allowed during unattended jobs (2026-10-14); closer, low oblique
action views within the four-still cap, and the redesign brief, which keeps unrun
development candidates out of the report (2026-10-15). Honesty rules:
- positions come only from recorded frames, never interpolated; enemies only while
  visible to the player, then as timestamped last sightings;
- issued routes stay distinct from observed movement, and issued, queued, acknowledged,
  rejected and refused orders from each other; acknowledged is not carried out;
- no reply is shown before it was applied; unknown reads "not recorded", never zero;
- the model's words appear only as attributed quotations, analyst notes carry their
  label, "what happened next" makes no causal claim, and no model writes narration;
- stills are never policy input; synthetic evidence is labelled everywhere, never mixed.

## Recording and stills

`play --record-replay` (default on) makes the battle script write one frame of public unit
and army state per battle second, copied into the episode as `replay.jsonl`; it keeps its
own sighting memory and reads no hidden state. Cost (one off/on pair, 2026-10-15):
2.851 ms of CPU per frame, battle/wall clock ratios 0.998213 off and 0.997703 on, 1.56 MB
per 260 frames. Without it only `trace.jsonl`'s decision-basis observations remain.

`play --stills` adds readable unit names (`unit_names.json`) and up to four images per
battle (`stills.json`, `still-<battle>-<trigger>.png`): the opening (overhead), one early
action (visible opposing units closing within 100 m before observed melee, else incoming
fire or first melee), the first rout and the ending, 30 battle seconds apart except the
ending (an early action inside that spacing is deferred, keeping its trigger time). The
battle script moves only the camera; a controller thread grabs the screen through Windows
Python with Pillow, outside the order loop, in about 40-75 ms, and records a failure when
the game is not in the foreground. The report embeds them as WebP of at most 256 KiB for
one battle per controller in each run set (the earliest completed); the rest stay as
metadata. A G1 replay payload is about 140-165 KB compressed, nine fit well under 20 MiB
(a test checks it), and the visual report is about 1.7 MB.

## Synthetic demo and checks

```bash
uv run python tests/twwarhammer3/make_wh3_report_demo.py runs/twwarhammer3/reports/report-demo.html
```

writes a page from invented jobs through `report.collect`: Demo controllers A, B and C,
two launches each at 0, 6 and 10 s added age, with a time-limit loss, a repeated rematch,
a missing metric, a policy failure, a setup-only interruption, and one replay with a
rejected order and a refused batch. It is labelled SYNTHETIC DEMO in the page, the viewer
and every download, and is never benchmark evidence.

Tests: `uv run pytest tests/twwarhammer3`. The optional browser check needs Playwright
installed outside the project, once:

```bash
npm install --prefix ~/.cache/wh3-playwright playwright@1.61.1
~/.cache/wh3-playwright/node_modules/.bin/playwright install chromium
NODE_PATH=~/.cache/wh3-playwright/node_modules node tests/twwarhammer3/check_wh3_report_browser.cjs \
  OUTPUT_DIR runs/twwarhammer3/battle/JOB [JOB ...]
```

With the three jobs of `visual-report` it builds `recorded.{html,json,txt}` and `demo.html`
in OUTPUT_DIR (outside the evidence directories), checks both offline in headless Chromium
against the collector's JSON and the demo's values, and leaves screenshots there.

## Known limits

- Stills are not registered to world coordinates; the map is the passability grid.
- Routes and target rings show submissions and acknowledgements, not execution.
- Without the recorder (the G1 jobs) positions update only at the controller's
  observations (about every 5 s in the G1 Sol battle), so "what happened next" rests on
  sparse samples; its distances add straight lines between them.
- Role and about text can be checked only against base stats and onscreen names; the
  records hold no anti-large, armour-piercing or other attributes.
- Analyst notes exist only for runs in the notes file; the owner has not reviewed them yet.
- A capture fails when another window is in the foreground or Windows Python lacks Pillow.

## Saved reports

Under `runs/twwarhammer3/reports/` (local, not in Git), read from each JSON's `jobs`:

| Artifact | Jobs under `runs/twwarhammer3/` |
|---|---|
| `field-report.{html,json,txt}`, `g1-cavalry.{json,txt}`, `g1-cavalry-admission.json` | `battle/bench-g1-cavalry-ai10-01-20261014`, `battle/bench-g1-cavalry-ai11-01-20261014` |
| `g1-cavalry-ai10-01.{json,txt}` | `battle/bench-g1-cavalry-ai10-01-20261014` |
| `cavalry-assault.{html,json,txt}` | the redesigned page: `battle/visual-sol-low-20261015` and the two G1 jobs |
| `visual-report.{html,json,txt}` | `battle/visual-sol-low-20261015` and the two G1 jobs |
| `visual-report-g1.{html,json}` | the two G1 jobs |
| `close-camera.{html,json,txt}`, `close-camera.png` | `visual-probes/close-imagery-r2-20261015` |
| `close-camera-first.{html,json,txt}` | `visual-probes/close-imagery-20261015` |
| `field-report-demo.html`, `visual-report-demo.html` | synthetic (the deleted fixture; `make-wh3-replay-demo.py` beside them) |
| `bench-b*.{json,txt,md}` | the b1-b9 screens and audits named in [log.md](log.md) |
| `visual-browser/` | browser check screenshots and exports |

All but `cavalry-assault` predate the 2026-10-15 redesign: their HTML is the old page (verdict, margin chart,
evidence and definitions, unrun placeholders), and their JSON lacks `order_age_median_s`,
`battle_ms` and the jobs' `created_at`. Rebuilding one from the jobs listed overwrites it
unless given another stem.
