# WH3 benchmark reports

`twwarhammer3 report` turns saved job directories into a text report, the collector's full
JSON and an HTML page that opens offline and holds its own CSS, scripts, evidence and
images. It runs no game and makes no API call. The page follows the owner's redesign brief
([WH3_report_redesign_guide_for_Codex.md](WH3_report_redesign_guide_for_Codex.md)): watch
the battle, understand the decisions, compare the results; the 2026-10-15 redesign aims it
at an AI researcher who knows nothing about the game and has a minute to spare: every
comparison is a small chart on a shared axis, latency is shown on the map and measured,
and bookkeeping stays in Run settings and the JSON. Statistics come from
`battle/report.py` ([definitions](benchmark.md#outcomes-measures-and-comparison)), the
replay from `battle/replay.py`, the presentation from `battle/report_html.py` and
`battle/report_assets/`, curated text from `configs/twwarhammer3/report_notes.json`, and
frames and stills from `battle/capture.py` during play ([integration.md](integration.md)).

## Suite report

The canonical entry point is `runs/twwarhammer3/reports/benchmark.html`, with `.json`
and `.txt` companions. Rebuild it from the explicit, versioned selection (run at the
repository root):

```bash
uv run python -m twwarhammer3 report --jobs-file configs/twwarhammer3/benchmark_jobs.json \
  --output runs/twwarhammer3/reports/benchmark
```

The selection retains the cavalry/G1/C1 and swarm evidence, specialist screens, battle-type
pilots and their failed/interrupted setup attempts. It excludes unrelated controller
tuning and presentation-camera probes. Add new jobs to that list as the suite grows;
never glob all local runs or select by outcome. The report JSON records every input job.
Existing scenario reports remain historical artifacts.

**All scenarios** lists every scenario by its notes `group` (challenges, specialist
screens, battle-type pilots) with its battle type, starting armies and one mark per battle
for each model and for the scripted baselines; select one to open it. Historical pilots use
their saved configuration's scenario name when their declaration predates names. No
current catalogue is substituted for historical setup. There is no aggregate score across
different armies or objectives.

Progress is the share of the enemy's registered soldiers dead or out of the fight (fleeing,
shattered, leaving or undeployed) when the battle ended: `1 - active/registered` from the
evaluation, unknown when either is missing. A win breaks the whole army in attack
scenarios; a defence can win with less. Failures keep their last observed progress. The
run card adds own soldiers left and, where recorded, units still fighting, objective time
and supplies, builds and purchases; absent measures are left out, never shown as zero.

Each challenge's question and notes should explain its potential plays: the army's useful
advantages, its disadvantages and consequential choices available to the controller.
Use the replay to distinguish opportunities it recognized, exploited or missed, and label
untested tactical ideas as hypotheses. Scenarios with no credible room for playmaking
should be redesigned or dropped from the active collection; retain their historical
results and explain the decision. Difficulty and spectacle alone do not establish value.

Evaluator v2 adds whole-unit counters; historical counts remain unavailable. Alive routed
units remain survivors; active units exclude routing, shattered, leaving and undeployed
units. The subsidiary states can overlap. Objective time uses engine-tick integrals only;
old snapshot-voting shares are not relabelled as time. Evaluator and controller versions
are in Run settings alongside the source revision, harness version and game build.
Evaluation data stays in the report, outside policy inputs and replay exports.

The HTML embeds its assets and compressed replays and opens directly from disk without a
server. Share or copy that file; the JSON/text companions retain the full collector output.
The browser check also opens a copied file offline, tests all scenarios, shared/missing
measures and replays, and checks desktop and phone layouts:

```bash
NODE_PATH=~/.cache/wh3-playwright/node_modules node tests/twwarhammer3/check_wh3_report_browser.cjs \
  runs/twwarhammer3/report-checks/benchmark --report runs/twwarhammer3/reports/benchmark
```

## Making a report

```bash
uv run python -m twwarhammer3 report runs/twwarhammer3/battle/JOB [JOB ...] \
  --output runs/twwarhammer3/reports/NAME
```

It prints the text report and writes `NAME.html`, `NAME.json` and `NAME.txt` (a stem:
`--output x.html` writes `x.html.html`). Pass every launch of a comparison: one job is one
instance, and paired intervals need several. Embedding stills needs Pillow (`uv sync
--locked`); without it nothing is written. Rebuild after editing the notes file. Share the
HTML file, not the evidence directory. Margin, throughput, the strict per-version groups,
paired intervals, detailed setup flags and statistical limitations remain in the text and
JSON. Failures and progress are also visible in the HTML.

## The page

A dark stage, then the results on a light page, then the method:

- **Masthead and pitch**: what the benchmark is in one sentence, its size (battles shown,
  scenarios, models, scripted baselines, dates) and, beside it, the **headline**: the
  first notes group's largest controlled comparison (the commanders shared by two launches
  of one harness, in the most such launches; C1 today), one mark per battle on the progress
  axis, its win counts and median order age. Its caption says "once per launch" only when
  that holds, names the enemy AI's difficulty and says when prompts were tuned on the
  scenario. In the single-column layout (below 1081 px) it follows the viewer.
- **The battle**: the scenario's name and enemy AI difficulty, its question, then the viewer
  with the featured battle and the challenge under the timeline. Unless the reader prefers
  less motion, it opens on the key maneuver's moment and plays it once when a quarter of the
  map is in view ("Key maneuver" replays it with its lead-in). The run card: commander and
  detail on one line, the outcome and its record here († when pooled across harness
  versions), the measures, then the scenario and battle selects, one per row. It names
  the commander (model, then reasoning effort and prompt, or the scripted rule), the
  engine outcome with its duration, the commander's record here and the battle's measures;
  a curated pick adds that it was selected for its analyst notes, not as a typical result.
  The analyst notes follow as numbered chapters, labelled as written after the battle with
  AI assistance and checked against the records; the playing one shows its sentence. Then
  the order of battle and up to four game stills ("spectator camera, not what the model
  saw").
- **Same battle, different plans**: per commander, a column of route maps, one per
  battle (three, in order, until "+N more"): every friendly path over the whole battle (thinned to a point every 6 m, □ start,
  ● end, × destroyed) and each enemy unit where first seen, over one framing per scenario;
  wins are outlined. Commanders whose armies never moved are left out.
- **How far each commander got**: one row per commander. Columns: enemy army broken (one
  mark per battle on a shared 0–100% axis; filled won, hollow lost, a cross for did not
  finish; battles without the measure in an "n/a" slot), battles won out of finished
  battles (a 95% Wilson interval only from five finished battles of separate launches of
  one harness), order age as a box plot (10th–90th percentile whiskers, middle half boxed,
  median marked; for the asynchronous commander, its model plans' age, with the executor's
  in small type) and cost per started battle. Marks show their battle on hover and open it
  on click.
- **The battle doesn't wait for the model**: a sentence quoting one model's median order
  age and the median movement meanwhile, both from the same 1 Hz recorder battles; then per
  commander, one minute of its first finished battle as a sawtooth of the age of its latest
  view on the shared 0–25 s scale (each drop is a reply, kept orders included; a red caret
  marks a taller tooth), its median order age and 90th percentile for replies with new
  orders, and the battle/wall clock ratio range. "See what moved during one
  reply" pins, in the viewer, the median-age reply with orders inside the key maneuver
  (else the whole battle). A labelled placeholder names the planned added-delay experiment.
- **All scenarios**: groups from the notes (pilots folded), aligned columns, one mark per
  battle for each model and for the scripted baselines ("no baseline yet" where none ran);
  † marks a cell pooling different settings or harness versions, listed in its tooltip.
  On a phone each scenario is a block.
- **Method**: verbatim lines of one message (the first reply with orders that reports its
  previous delay, in the first scenario's featured battle), abridged by section, and its
  reply one order per line, with the size of the fixed system prompt; then
  what a model sees, real time, opponent and baselines, the progress measure, the
  development status of every scenario, rows and versions, and what is not shown
  (setup-only launches and diagnostic probe battles); Run settings, the report and replay
  JSON, and a link here.

A row holds every battle of one commander (model, effort, prompt or scripted rule, added
age) in a scenario. When battles ran under different harnesses its name carries a † (the
tooltip says how many versions, a footnote explains it once), and Run settings names each
battle's. A harness fingerprint covers the source
files in the job's scope except presentation (`report*`, `replay.py`, `digest.py`,
`watch.py`, `stats.py`, the notes and the scenario catalogue), the scenario declaration
without its prose, the game build, interface track and timing, and whether the recorder or
stills ran; jobs without file hashes use their source revision. The collector's JSON and
text keep the strict groups that never pool across any of these. Diagnostic probes
(`terrain_probe`, `flight_probe`, `probe_abilities`, external test controllers) test
tooling, not commanding: they stay in the data and the JSON, not on the page.

Outcomes are always the engine's; a battle that reached the scenario's timer reads "at the
time limit", whatever its job recorded as `ended_by` (b8 recorded those as
`engine_result`). Enemy army broken is printed rounded down
below 100%, so a loss never reads as a win.

The footer opens **Run settings** for the battle in the viewer (scenario and its status,
commander and its timing in plain words, harness, interface, recording and provenance;
collapsed, the declared brief and, for model runs only, the prompt the model received,
named by policy) and offers the report JSON and this replay JSON.

### The replay viewer

Map and moment panel stack below 1080 px; at 390 px the map starts on the first screen and
nothing scrolls sideways. The map draws the passability grid (north up, fixed framing per
replay) and each unit's side, role glyph, facing, label ("KR1"), strength and state, with
hollow last sightings of unseen enemies, 20 s trails and, faintly, the waypoints a unit
was ordered to and has not yet come within 30 m of, drawn from where it is; a selected unit
adds its observed path, standing orders (numbered waypoints, attack rings, rejected steps
red) and a card with role, state, orders and base stats. Controls: 1×, 4× or 16× playback
(the battle ran at 1×), decision (←/→) and event ([ ]) steps, scrubber, timeline strip.

The map's lower left names the two armies ("gpt-6-sol's army", "Game AI"). **Model's view**
beside it outlines every unit where it stood in the observation behind the latest reply
that reached the game (for the asynchronous commander, the latest adopted plan's older
view), joined by a line to where the unit is now, with "Outlines: where units stood N s
ago" in a caption; live markers recede meanwhile. It is off in ordinary playback. The
timeline labels its rows (notes, replies, events) and its lowest band is the same view
age, second by second, on the shared 0–25 s scale. The waiting line counts how long ago the
model was asked. Map labels that would overlap another are dropped, except the selected
unit's; the roster and hover still name every unit.

The moment panel shows the latest decision applied by the replay time, never a reply
before it was applied ("Waiting for the model's next reply" until then): the stated
reason, quoted and attributed; the orders in plain words ("Lord: run 320 m north-west,
then attack Great Cannons in melee"), "Keeping current orders" (its tooltip: queued steps
continue), or "orders refused by validation"; then, folded, up to six "what happened next"
facts from the recorded frames with their causation caveat. After the orders, one sentence
says how old the information was when the game accepted them, with the seen and accepted
times and the reply's wall-clock time (for the commander, its plan's age or the unit skills
following it). While playing, only the waiting counter updates between decisions, so the
panel's buttons and folds stay usable. Message, reply, timing detail
and cost stay collapsed. "See what moved while it waited" pins the reply: the ordered units,
their targets and every unit that moved 5 m or more, as outlines in the basis observation
and solid in the first frame after application, joined by straight lines. On wide screens
the panel is as tall as the map column and scrolls.

More than 1.5 × the sample interval past the last frame, the map says "No observation
recorded during this interval". A run without the 1 Hz recorder shows one notice instead:
positions update only when the controller observed the battle (about every N s). Its
sample interval is the median spacing of those observations (at least `observe_ms`), so
only unusually long gaps are flagged.

## Curated notes: `configs/twwarhammer3/report_notes.json`

Reader-facing text that is neither policy input nor recorded evidence. It is committed and
inside `twwarhammer3 play`'s source scope: editing it stops a running job, so draft it in
a worktree while one runs. Three maps:

- **`scenarios`**, by scenario name, in page order: `title` names it, `group` places it
  in All scenarios (the first group is the masthead's), `question` heads the page,
  `challenge` states the task and its real objective. Without an entry: its `family` or
  name, the declared `brief`, and "Specialist screens" (with a family) or "Battle-type
  pilots".
- **`units`**, by unit type key: `name` is the game's onscreen name (checked against its
  English localisation), `short` the map label (numbered for duplicates), `role` a few
  words, `about` one sentence on how the unit differs, `glyph` one of `general`,
  `cavalry`, `missile_cavalry`, `infantry`, `polearm_infantry`, `missile_infantry`,
  `artillery`, `monster`, `unknown`. Every comparison in `about` must hold in the recorded
  base stats (`setup.unit_base_stats` in `result.json`), and every attribute (bonus
  against large, armour-piercing damage, fear immunity, firing on the move) in the game's
  database (`scripts/wh3_db.py`, [integration.md](integration.md#packs-and-loading)).
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

**Featured run**, per scenario: a battle with `selected: true`; else the earliest completed
model battle by job start, then episode; else the first battle. The chronological rules
never look at outcomes. A curated selection may be chosen for its moments, so the run card
states the commander's record in the scenario beside it and that it is not a typical
result.

## Timing

- **Durations** come from each battle's `battle_ms`, the engine's battle clock
  (`battle_s` only where it is missing).
- **Order age** (results and Real time): the battle-clock age of the observation behind
  each acknowledged batch of new orders when the game accepted it (`age_s` of replay
  decisions with orders), pooled over a row's battles; median, middle half and 10th–90th
  percentiles are shown. For the asynchronous commander the row shows its plans' age at
  adoption (`plan_age_s`), since its executor's 0.3 s says nothing about the model.
- **View age** (Real time sawtooth, the timeline's lowest band, Model's view): at each
  moment, how old the observation behind the latest applied reply is (empty replies
  included; a commander's plan view for the commander). It drops when a reply lands and
  grows by one second per second until the next, from `timing.replies` (view and
  application times, battle clock). The collector's `order_age_median_s` (the median of per-battle medians) stays in
  the JSON. `visual-sol-low-20261015`: 4.2 s over 45 batches; 3.9 s over all 91 applied
  replies, empty ones included.
- **Movement meanwhile** (Real time): per batch, the largest displacement of any unit
  seen in both its basis observation and the first frame at or after acknowledgement, from
  1 Hz recorder battles only (sparser frames would overstate it). It describes how much
  the battle changed, not a cause.
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
each featured battle and the earliest completed battle of each commander in each
scenario; the rest stay as
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
- The records hold no unit attributes. The cavalry-assault roster's attribute claims were
  checked in the game's database on 2026-10-15; other rosters need the same check before
  their notes describe attributes.
- Analyst notes exist only for runs in the notes file; the owner has not reviewed them yet.
- A capture fails when another window is in the foreground or Windows Python lacks Pillow.

## Saved reports

Under `runs/twwarhammer3/reports/` (local, not in Git), read from each JSON's `jobs`:

| Artifact | Jobs under `runs/twwarhammer3/` |
|---|---|
| `field-report.{html,json,txt}`, `g1-cavalry.{json,txt}`, `g1-cavalry-admission.json` | `battle/bench-g1-cavalry-ai10-01-20261014`, `battle/bench-g1-cavalry-ai11-01-20261014` |
| `g1-cavalry-ai10-01.{json,txt}` | `battle/bench-g1-cavalry-ai10-01-20261014` |
| `cavalry-assault.{html,json,txt}` | the redesigned page: `battle/visual-sol-low-20261015` and the two G1 jobs |
| `c1-cavalry-ai11.{html,json,txt}` | All six C1 launches: `battle/bench-c1-cavalry-ai11-0{1,2,3,4,5,6}-20261015` |
| `swarm-screens.{html,json,txt}` | `battle/bench-b10-screen-skv-swarm-r2-20261015`, `battle/bench-b10-screen-dwf-line-20261015`, and the setup-only first attempt |
| `visual-report.{html,json,txt}` | `battle/visual-sol-low-20261015` and the two G1 jobs |
| `visual-report-g1.{html,json}` | the two G1 jobs |
| `close-camera.{html,json,txt}`, `close-camera.png` | `visual-probes/close-imagery-r2-20261015` |
| `close-camera-first.{html,json,txt}` | `visual-probes/close-imagery-20261015` |
| `field-report-demo.html`, `visual-report-demo.html` | synthetic (the deleted fixture; `make-wh3-replay-demo.py` beside them) |
| `bench-b*.{json,txt,md}` | the b1-b9 screens and audits named in [log.md](log.md) |
| `visual-browser/` | browser check screenshots and exports |

All but `cavalry-assault`, `c1-cavalry-ai11` and `swarm-screens` predate the 2026-10-15 redesign: their HTML is the old page (verdict, margin chart,
evidence and definitions, unrun placeholders), and their JSON lacks `order_age_median_s`,
`battle_ms` and the jobs' `created_at`. Rebuilding one from the jobs listed overwrites it
unless given another stem.
