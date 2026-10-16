# WH3 benchmark reports

`twwarhammer3 report` turns saved job directories into a text report, the collector's full
JSON and an HTML page that opens offline and holds its own CSS, scripts, evidence and
images. It runs no game and makes no API call. The page follows the owner's redesign brief
([WH3_report_redesign_guide_for_Codex.md](WH3_report_redesign_guide_for_Codex.md)): watch
the battle, understand the decisions, compare the results. The 2026-10-15 redesigns aim it
at an AI researcher who knows nothing about the game and has a minute to spare: a paper
report around one live replay, one score per commander rather than every attempt, three
numbered figures, latency on the map and beside each score, and bookkeeping in Run settings
and the JSON. The 2026-10-16 revision (the owner's report notes) shows only the core
scenarios and their completed battles, opens on a visual index of them, gives each model
one hue and replaces the plans maps with battle development. Statistics come from
`battle/report.py` ([definitions](benchmark.md#outcomes-measures-and-comparison)), the
replay from `battle/replay.py`, the presentation from `battle/report_html.py` and
`battle/report_assets/`, curated text from `configs/twwarhammer3/report_notes.json`, and
frames and stills from `battle/capture.py` during play ([integration.md](integration.md)).

## Pending report notes

Owner feedback still to implement (the other notes of 2026-10-16 are in the page below):

11. Eventually add OpenRouter support for a broader selection of models alongside the
    existing OpenAI API support. This is future benchmark work, not a report feature.

Not done with the rest, and why:

- The paper page has no dark colour scheme; the model hues have a light and a dark step
  (paper figures, dark map and run card), each pair checked for colour-vision separation.
- The evacuation scenario (`emp-battery-skv-evacuation`, an ambush battle) has no
  completed battle yet, so it is absent; its mode would show the generic flag icon until
  ambush battles get their own.
- Ability rings follow accepted ability orders; the recorder's `abilities[].active` flags
  are not drawn (they stay in the job's `replay.jsonl` and feed "what happened next").

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

**The page shows the core scenarios** (`core_candidate: true` in the notes, one per
decision family, [scenario design](benchmark.md#scenario-design)) and only their
completed battles (an engine-reported win, loss or draw). Variants, historical pilots,
demoted scenarios (Conquest), diagnostic probes, setup failures and incomplete attempts
stay in the JSON and text and in the page's report download, not on the page, and their
replays are not embedded; the Method counts them in one line. A core scenario without a
completed battle is absent. A report whose notes mark no scenario as core (an ad hoc
report of other jobs, the synthetic demo) shows every scenario. Game modes come from
`report_html.MODES` (the game's custom battle types, sieges split by the player's role).
Historical pilots use their saved configuration's scenario name when their declaration
predates names. No current catalogue is substituted for historical setup. There is no
aggregate score across different armies or objectives.

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
are in Run settings alongside the source revision, test-setup (harness) version and game build.
Evaluation data stays in the report, outside policy inputs and replay exports.

The HTML embeds its assets and compressed replays and opens directly from disk without a
server. Share or copy that file; the JSON/text companions retain the full collector output.
The browser check also opens a copied file offline, switches every scenario from the
index, checks the page's battle selection, figures, measures, replays and ability rings,
and checks desktop and phone layouts:

```bash
NODE_PATH=~/.cache/wh3-playwright/node_modules node tests/twwarhammer3/check_wh3_report_browser.cjs \
  runs/twwarhammer3/report-checks/benchmark --report runs/twwarhammer3/reports/benchmark
```

Its screenshots include `desktop.png`, `phone.png`, `index.png`, `siege.png`,
`plans-siege.png`, `compare.png`, `suite.png` and `suite-phone.png`.

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

A paper page around one dark replay panel. Titles and prose use a book serif with lining
figures (Charter, Sitka or Cambria, Iowan, Noto Serif, Liberation Serif), labels and numbers
a sans (Bahnschrift or Segoe UI, the Apple system font, Roboto, Noto Sans, Ubuntu,
Liberation Sans); no fonts are embedded and no stack falls back to DejaVu. There are no
all-caps labels, badges, cards or middle-dot strings, and only Play carries an icon. Each
model keeps one hue everywhere (violet, green, then magenta and ochre, by model name; light
and dark steps), scripted rules are grey, the armies keep their sky blue and orange, and a
magenta ring marks an ordered ability on the map. Dek, finding and scenario text share one
measure (68ch). Plain words replace jargon: "rules-only prompt" or "prompt with tactical
tips", "test-setup version" (the harness fingerprint below), "endless waves"; the reasoning
effort is defined once, under Figure 1.

- **Masthead**: the title, one short paragraph on what the benchmark is and why it is
  small (battles take minutes of real time, so every scenario asks a different question),
  then the **scenario index**: one small dark map per scenario, cropped to its featured
  battle's starting positions (the units of the first frame) over the passability grid, its
  game-mode icon (land battle, siege defence, survival; a flag for other modes), short name
  (`short` in the notes) and a 4 px bar per model and one for the best rule on the
  scenario's scale, so the row itself compares. A thumbnail underlines its name on hover and
  focus; clicking opens the scenario and scrolls smoothly to the replay; the selected one
  is underlined. On a phone the index wraps to three columns. Then the finding: dates,
  battles and scenarios; the wins of each model, from its largest group of battles under
  one test setup, in every scenario where each model that played has at least three such
  battles ("gpt-6-sol won 1 of 6 cavalry assaults, 2 of 3 swarm assaults, …; gpt-6-luna won
  0, 0, 1 and 0", a later model's wins alone when its scenarios and battle counts match the
  first's, else named; scenarios nobody won close it: "Neither won any swarm defence or
  Kislev survival battle", with `noun` in the notes naming one battle); how many battles
  per model the other scenarios have; how old the models' and the rules' views were when
  their orders landed; and that prompts were developed on these scenarios (in-sample),
  said only here.
- **The battle**: a short declarative heading (`heading` in the notes), then the replay
  panel with large scenario and battle selects (battles by commander, outcome first; on a
  phone only the battle select, as the index picks scenarios), "Play key moment (3:06)" and
  "Play full battle". At 1440 × 900 the map's top is on the first screen; the paragraph
  naming the game mode, the enemy AI's difficulty and the scenario's challenge follows the
  replay. The page opens on Figure 1's scenario, so the replay and Figure 1 show the same
  battle. Unless the reader prefers less motion, the replay opens on the key moment and
  plays it once, with Model's view on, when a quarter of the map is in view. The run card
  names the commander (its hue, model, then reasoning effort and prompt, or the scripted
  rule), the engine outcome with its duration, the commander's record here and the battle's
  score with its outcome ("score 92 in a lost battle") and measures; a curated pick adds
  that it was selected for its analyst notes, not as a typical result. The analyst notes
  follow as a row of numbered titles with their times, the playing one's sentence under
  them, labelled once as written after the battle with AI assistance. Then the two armies
  (open; unit codes as plain bold text) and up to four game stills.
- **Results**, **Figure 1**: the largest controlled comparison (the commanders shared by
  two launches of one test setup, in the most such launches; C1 today), one row per
  commander: its score as a bar in its hue on the shared 0–100 scale with a line from its
  worst to its best battle and, on model rows, a tick at the best scripted rule's score; its
  record ("won 1 of 6"), median order age and the mean API cost per completed battle. The
  caption names the mode, says "once per launch" only when that holds, names the enemy AI's
  difficulty and says that Figure 3 pools every completed battle in the scenario (so its
  numbers can differ). Its footnotes are the only place the page defines the scenario's
  variant, the score (for the kinds of battle on the page only), the reasoning effort, order
  age and cost. Under it, one line gives each model's total API spend over every attempt in
  the report's input, incomplete ones included.
- **Same battle, different plans** (**Figure 2**), for the scenario in the replay: one
  panel per model (its settings pooled, † with what is pooled in its tooltip), two to a row,
  drawn at their width with labels of at least 12 px; scripted rules stay in Figures 1 and 3.
  On shared axes: the soldiers its army lost and the soldiers the enemy lost (only units its
  army saw, last count; a seen unit the roster marks dead loses all) over battle time, thin
  per battle and thick for the mean (`development` in the battle data, from the recorded
  frames), and strips of the orders the game accepted per 5 s by kind (move, attack,
  ability, build, reinforce, other), darker for more, with the mean count per battle. Where
  the models' routes part (some pair's mean positions at least 50 m apart at the median
  shared moment), each panel adds a map of its army's track in every battle and the mean in
  its hue (□ start, ● end) with the enemy where first seen; in the siege the routes overlap
  and the maps are left out. A panel opens the model's earliest battle here.
- **Every scenario** (**Figure 3**): a section per game mode with scenarios on the page,
  headed by its icon; per scenario, its armies by race and role ("9 Chaos Dwarf units
  defending against 16 Greenskin units"), a bar per model (its mean score over its completed
  battles there, then its record; "no battles yet" when it has none) and a grey bar for the
  best scripted rule ("no scripted baseline yet" where none ran), on one 0–100 scale per
  section, or a seconds axis for survival. The caption explains † once. A whole row opens
  its scenario; its name underlines on hover. On a phone the name sits above narrower bars.
- **Method**, one column: verbatim lines of one message (the first reply with orders that
  reports its previous delay, in the first scenario's featured battle), abridged by
  section, and its reply one order per line, with the size of the fixed system prompt;
  then what a model sees, real time, opponent and baselines, what counts as a scenario and
  one line on what is not shown (further battles and setup-only launches, kept in the JSON
  and text); Run settings, the report and replay JSON, and a link here.

**Score**: per completed battle, 100 for a win, else the share of the enemy's soldiers
dead, fleeing or otherwise out of the fight when it ended, in percent, in land battles and
siege defences (siege attacks and settlements score objective ownership time, conquest
and domination ticket progress, survival seconds survived); a commander's score is the
mean over its completed battles (battles without the measure are left out). Siege
defences scored ownership time until 2026-10-16, when lost defences scored 92–99 and the
score did not tell the commanders apart; the run card still shows the time each point
was held (key building and supply points by name), supplies left and builds. A
win is 100 even when a defender wins at the timer with the enemy largely intact. Printed
scores never round a loss up to 100 (a 99.8% loss reads 99). Battles that recorded
casualties only (older pilots, none of them on the page today) count the enemy killed,
not those who fled, a lower bound for those lost; Figure 3's caption says how many losses
when there are any.

A commander's figures hold all its battles (model, effort, prompt or scripted rule, added
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
commander and its timing in plain words, test-setup version, interface, recording and provenance;
collapsed, the declared brief and, for model runs only, the prompt the model received,
named by policy) and offers the report JSON and this replay JSON.

### The replay viewer

Map and moment panel stack below 1080 px; at 390 px nothing scrolls sideways and the map
starts within two screens, after the three-column index. The map draws the passability
grid (north up) in a fixed frame where the fighting happened: the 5th to 95th percentile of
every recorded position and the units' starting positions (those seen in the first 30 s),
with a 50 m margin, so a unit straying far off does not shrink the rest; "Show the whole
map" frames the terrain. It draws each unit's side, role glyph, facing, strength and state, with
hollow last sightings of unseen enemies, 20 s trails and, faintly, the waypoints a unit
was ordered to and has not yet come within 30 m of, drawn from where it is. Objectives are
small diamonds filled by their holder's colour (larger for victory points; name and holder
in the tooltip). A unit that a reply ordered to use an ability or spell, accepted by the
game, gets a magenta ring that fades over 5 s of battle time (static when paused), and its
line in the moment panel carries the same mark with the ability's name; a selected unit
adds its observed path, standing orders (numbered waypoints, attack rings, rejected steps
red) and a card with role, state, orders and base stats. Controls: 1×, 4× or 16× playback
(the battle ran at 1×), decision (←/→) and event ([ ]) steps, scrubber, timeline strip.

On desktop the replay panel is wider than the text column (up to 1640 px) and the map up to
the window's height less 150 px (at most 980 px). The analyst note's title on the map is
unboxed text. The controls row, under the map, holds Play (the one icon), the clock, Back
and Next for decisions and events, the replay speed, then the legend naming the two armies
("gpt-6-sol's army", "Game AI") and **Model's view**, which outlines every unit where it stood in the observation behind the latest reply
that reached the game (for the asynchronous commander, the latest adopted plan's older
view), joined by a line to where the unit is now, with "Outlines: where units stood N s
ago" under the controls; live markers recede meanwhile. It is on while the key moment autoplays, off otherwise until turned on. The
timeline labels its rows (notes, replies, events) and its lowest band is the same view
age, second by second, on a fixed 0–15 s scale with a dashed 5 s line. The waiting line
("Waiting 6.5 s for the model's next reply"; "Asking for..." at the moment of asking), plain
text, counts how long ago the model was asked. Unit labels ("KR1") appear for every unit only when at
most 12 markers are on the map; otherwise only for the selected and hovered units and a
watched note's units. Labels that would overlap another are dropped, except the selected
unit's; the roster and tooltips name every unit.

The moment panel shows the latest decision applied by the replay time, never a reply
before it was applied ("Waiting for the model's next reply" until then): the stated
reason, quoted and attributed; the orders in plain words ("Lord: run 320 m north-west,
then attack Great Cannons in melee") or "orders refused by validation" (a reply with no
orders says so in its heading, whose tooltip adds that queued steps continue); then,
folded, up to six "what happened next" facts from the recorded frames with their causation
caveat. After the orders, one sentence says how old the information was when the game
accepted them, with the seen and accepted times and the reply's wall-clock time (for the
commander, its plan's age or the unit skills following it). Folds stay as the reader left
them from one decision to the next, and while playing only the waiting counter updates
between decisions, so the panel stays usable. In commander battles, the unit skills' ticks
show no explanation section and no waiting line, and neither "See what moved" control is
offered (Model's view shows the plan's view). Message, reply, timing detail
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

- **`scenarios`**, by scenario name, in page order within each game mode (the first one
  opens the page): `title` names it, `heading` heads the page (short and declarative),
  `challenge` states the
  task and its real objective, `footnote` defines a variant once (under Figure 1), `short`
  names it in the masthead index, `noun` names one of its battles in the finding ("siege
  defence"), and `core_candidate: true` puts it on the page (the caster family's is
  `tze-caster-skv-assault` since 2026-10-16). The
  game mode comes from the declaration (`battle_type` and `attacker`). Without an entry:
  its `family` or name and the declared `brief`.
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
- **Order age** (Figure 1 and the finding): the battle-clock age of the observation behind
  each acknowledged batch of new orders when the game accepted it (`age_s` of replay
  decisions with orders), pooled over a commander's battles; the median is shown. For the
  asynchronous commander it is its plans' age at adoption (`plan_age_s`), since its
  executor's 0.3 s says nothing about the model.
- **View age** (the timeline's lowest band, Model's view): at each
  moment, how old the observation behind the latest applied reply is (empty replies
  included; a commander's plan view for the commander). It drops when a reply lands and
  grows by one second per second until the next (view and application times, battle
  clock). The collector's `order_age_median_s` (the median of per-battle medians) stays in
  the JSON. `visual-sol-low-20261015`: 4.2 s over 45 batches; 3.9 s over all 91 applied
  replies, empty ones included.
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
