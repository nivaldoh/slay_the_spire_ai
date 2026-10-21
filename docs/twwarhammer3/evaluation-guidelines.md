# Guidelines for evaluating WH3 battle controllers

Each battle runs in real time (1x, never paused) against the game's own AI. A controller,
often an LLM with helper code, receives snapshots of the units it can see through a Lua
mod and sends move and attack orders while the battle continues; the battle ends when one
side breaks or the timer runs out. A card is a small frozen battle that tests one tactical
choice. The project has one human owner, who works with AI agents. An evaluation here
measures, for a declared controller on a frozen card under declared conditions, how often
it meets the card's success rule, how quickly and reliably it acts, what it costs, and
what the records show it did. It is useful when it lets someone make a named decision and
check why. These rules cover designing, running, scoring and reporting one, for us when
planning a study and for an outside researcher deciding whether to trust a result. The
benchmark is defined in [benchmark.md](benchmark.md), the cards in
[tactic-cards.md](tactic-cards.md), the commands in [benchmark-run.md](benchmark-run.md).

**Status (revised 2026-10-20).** Proposals. Nothing here is verified under the
[hard rule](../../AGENTS.md#verification-hard-rule): a check counts only once the owner
agrees it and it passes at a named revision. Most rules end with a **Check**: *exists*
(the code is there, but it is verified only if AGENTS.md lists it), *proposed* (not built,
with a rough size) or *manual* (a person does it).

## Before you start

**Before a scored run** (a confirmation or final study), fill the plan's `study` block
(proposed). Each key answers one question:

| Key | Question | Rule |
|---|---|---|
| `claim`, `decision` | What decision does it inform; what is the one-sentence claim? | [1.1](#11-write-the-claim-before-the-run) |
| `contrast`, `arms` | Which one part differs between the arms? | [1.3](#13-change-one-part-per-comparison-and-claim-only-that-part) |
| `cards` | Which card versions, checked by witness and foils on this build? | [2.7](#27-admit-a-card-only-from-a-frozen-confirmation-round), [4.4](#44-compare-only-matching-cells-and-recheck-references-after-a-change) |
| `stage` | Is this evaluation evidence, kept out of tuning? | [3.1](#31-mark-each-jobs-stage-and-tune-only-on-development-evidence) |
| `launches`, `order` | How many launches per arm; which rotation seed and first-slot balance? | [4.1](#41-count-launches-not-rematches), [4.2](#42-balance-who-plays-first-and-when) |
| `stop`, `replace`, `budget` | When does it stop, what gets a replacement, what may it spend? | [4.3](#43-freeze-the-whole-study-in-one-plan-file) |
| `primary`, `secondary` | Which success rule and scorer version decide it; which diagnostics sit beside it? | [5.1](#51-one-success-rule-per-card-in-one-function-told-to-the-controller) |
| `gain` | What gain would matter, and how likely is the plan to detect it? | [7.4](#74-decide-before-you-look) |
| `depends_on` | Which agreed checks (with revisions) does it rest on; what is unverified or open? | [1.1](#11-write-the-claim-before-the-run) |
| `exposure` | Which models tuned or designed each card and prompt version? | [3.3](#33-record-who-tuned-on-what) |

**Before a claim**, the saved files answer: what was compared, under which conditions;
whether the setup and information boundary held; where every planned trial went; whether
the interval method fits how the launches were run (paired or separate, one episode per
launch); and whether someone else could recount it. If not, narrow the claim or finish
the work.

## Words used here

[benchmark.md](benchmark.md#terms) defines scenario, variant, instance and track (its
"controller" means only the code); [README](README.md#terms) defines labels such as `v21`
(a model controller's prompt version) and `b36` (a harness revision).

| Word | Meaning |
|---|---|
| controller | Everything between an observation and an order: model and served backend, reasoning effort, reply token cap, prompt, memory, executor or skills, re-asks, salvage (keeping the valid orders of a partly invalid reply), retries and timeouts |
| harness | The benchmark's own code around the controller (play loop, mailbox, Lua mod, scorers). `bN` labels a repository revision and can also change controllers (b40 brought witness v2 and prompt v21). The register's column named `harness` is instead the `-vN-` number from the job name, blank when the name has none (most `bench-*` jobs) |
| card | A small frozen battle built around one tactical choice, with a success rule, a witness and foils ([fields](tactic-cards.md#a-card)) |
| contact win | An engine-reported win before the timer ([score](tactic-cards.md#score)) |
| witness | A disclosed controller, usually a script, showing the card can be won at a named added age and decision interval |
| foil, floor | A simple working controller testing a shortcut; floors are naive scripts that should lose, such as `hold` and `attack_nearest` |
| signature | A code check that the tactic was tried or happened; the chariot's, cycles v1, counts melee engagements other than the last in which a move order was applied |
| family | Cards and variants testing the same kind of tactical choice |
| launch | One game start; each benchmark `play` job makes exactly one, so job and launch name the same unit. The unit we count |
| rematch | A later episode of a launch; it restarts the launch's instance, so it is not an independent battle |
| trial, slot | One controller playing one episode; its position in the launch (slot 0 is the fresh start) |
| arm, cell | One condition in a comparison; one card, controller, added age and decision interval |
| board, reader | The table `twwarhammer3 card` prints, one row per cell; code that reads saved job files and prints counts (`card`, `report`, the HTML report, `stats`) |
| round, gate, c1 | Launches planned together to screen or admit a card; a pass/fail admission test ("foils lose 10 of 10"); c1 is the chariot card's confirmation round (`calibration/c1`, harness b34 and b36), not the older cavalry design C1 |
| stage | A job's purpose (proposed; not the scenario's `split`): `explore`; `confirm` (an admission round or planned comparison); `final` (frozen controllers on held-out variants or a released suite); `drift` (scripted reruns after a change). Confirm and final jobs are evaluation evidence |
| engine result, card result | `won`/`lost`/`draw` and how the battle ended; the card's success rule applied to it |
| failed decision | A model call that failed while the battle went on; the trace records it with kind `forfeit`, but it is not a forfeit |
| forfeit | A battle lost to a terminal controller failure; a loss |
| order age, added age | Battle time from the observation an order answered to its application; extra age a diagnostic arm adds to every observation |
| decision interval, gap | How often a controller is asked, as configured; the measured time between its decisions |
| manifest, ledger, register | A job's record of its setup and episodes; the append-only file of each API call's cost; `results.csv`, one row per episode |
| readback, wall cap, rotation | The game's report of the settings and army actually set up; the real-time limit on one episode; the order in which a job's controllers take turns over its episodes |
| unresolved | A comparison whose named test does not pass its declared threshold (p < 0.05 for one planned contrast; Holm-corrected when several pairs are compared) |

## 1. Define the question

### 1.1 Write the claim before the run

Write one sentence naming the decision, the one part that differs between arms, the card
versions and the conditions. Below it, list what the claim depends on: agreed checks with
their passing revisions, and every unverified or undecided part. Results cover the named
cards and conditions only, not general WH3 skill, campaigns, human-level play or robots.
Example: "On chariot card version X at natural latency on the pinned build, does adding
the cycle-charge paragraph to the rules prompt raise GLM-5.3 low's contact-win rate?
Depends on: the army check (agreed; passed at `e32b1b5`); cycles v1 (unverified); witness
v2 (open)."

- *Check:* proposed (small): `scripts/wh3_queue.py` refuses a confirm or final plan
  without `claim`, `contrast`, `cards` and `depends_on`; `card` and `report` print them
  once manifests record the plan ([4.3](#43-freeze-the-whole-study-in-one-plan-file)).
  Manual: the owner reads the claim first.

### 1.2 The controller is everything that acts in the battle; identify it by content

Identify every controller and every run's conditions by hashes of what actually ran, never
by labels such as `v21`. Every part of the controller sees only public inputs, its time
counts at 1x and its spend counts in the ledger, and changing any part makes a different
controller: `llm_rules` with two re-asks and salvage differs from the same prompt with
none, and in `commander` the skills executor picks targets and timing. A **condition key**
covers the harness files that act in every battle, the card's resolved scenario entry, the
Steam build and executable hash, the mod pack, track, timing, recorder settings, host
machine and network. A **controller identity** covers the controller's own files, prompt
hash, request settings, routing pin (the provider a request is pinned to) and served
model. Rows with different keys stay apart; a merge needs a written reason logged with the
result and never crosses game builds.

- *Why:* labels drift from content, and a pooled mix cannot be undone. Today the board
  misses harness code and the executable hash (a `skills.py` change keeps the commander's
  identity), `report` splits by whole commit, and `stats` by the job name's `-vN-` version
  or, when the name has none (most `bench-*` jobs), by commit.
- *Check:* proposed (medium): `condition_key()` and `controller_identity()` written into
  `results.csv` and used by every reader; a test that editing `report.py` or another
  scenario's entry keeps the key and editing `play.py` changes it. Proposed (small): a
  test pairing each `VERSIONS` label with the hashes of its system prompt and golden
  prompt files.

### 1.3 Change one part per comparison, and claim only that part

Check that every other part matched before reading a result.

| What changed | The result shows | It does not show |
|---|---|---|
| Model, all else the same | This model on this backend with these prompts and helpers | General intelligence |
| Prompt or advice | The effect of that text, length included | That the model lacked the knowledge |
| Executor or skills | The effect of the help | That the model chose the tactic |
| Reasoning effort | The effect of that mode, slower orders included | "Better reasoning", unless the faster mode is also run with added age equal to the slower mode's extra order age |
| Added age | Harm from that delay | That faster serving would rescue a loss |
| Told arm (witness recipe in words) | Whether losses are choice or execution | Anything about choice, if it also loses |
| One fine-tune per arm | That checkpoint's effect | A dataset's or reward's effect |

Each reasoning mode is its own controller (owner, 2026-10-16). Without a told arm, write
"tactic not shown", not "did not choose it".

- *Check:* proposed (small, after 1.2 and 4.3): `report` prints the identity parts that
  differ between arms and, given a study plan, refuses when a part outside `contrast`
  differs.

## 2. Build cards that test one choice

### 2.1 Write down the choice, and cover each tactic from both sides

Before any battle, write the situation, the choice, why it should change the result, the
success rule, a plausible wrong play and the simplest shortcut. Chariot: a chariot hits
hardest on the charge, so the right play is to leave melee and charge again rather than
keep grinding; wrong play `attack_nearest` (walk at the nearest visible enemy); shortcut
`rush_nearest` (the same at a run). Drop
or redesign a battle without credible alternative plays; more units alone do not make a
coordination card. Keep a coverage table listing what no card tests, and for each rewarded
tactic plan a card where it is the wrong play (cavalry against braced spears catches a
controller that always pulls out and charges). Variants add no coverage.

- *Check:* manual: the text lives in tactic-cards.md; code gets a field only with the check
  that reads it.

### 2.2 Tell the controller everything the scorer checks

The prompt states the objective, the deadline, what a timer ending counts as and any unit
that must survive. A variant may stay unseen; the success rule may not. Record whether each
prompt argues for, against or nothing about the tactic. Two live mismatches: the candidate
Empire line battle's prompt says on its `Battle:` line "if time runs out, you win", while
its outcome of record (empire.md decision 7, pending owner review) is the contact win; and
`system_prompt.md` says "a withdrawal only delays defeat" while `rules_prompt.md` is
silent, so an `llm` against `llm_rules` gap on the chariot card also measures that sentence.

- *Check:* proposed (small): each card lists `told` and `withheld` phrases; a test renders
  the card's opening prompt from a first observation recorded at its live start (the
  `Battle:` line comes from the game, not `scenarios.json`) and fails on a missing or
  leaked phrase.

### 2.3 Show the card can be won, at a named timing

Every "winnable" claim names the witness's added age, decision interval and launch count.
A witness sees only the public observation, uses the same orders and plays live at 1x.
When no witness has won at an order age and decision interval like a model's, that model's
loss says little about tactics; a witness losing at some timing shows only that this
script fails there. Example (unverified): in c1, chariot witness v1 won 4 of 5 at 5 s
added age deciding every tick (the admitting cell) but 0 of 5 at 5 s age with a 5 s
interval; it won 0 of 4 at 8 s age with an 8 s interval in the 2026-10-19 timing cells,
and witness v2 won 4 of 5 at both 5 s/5 s and 8 s/8 s (b40 round). Label a card
"single-author witness" until someone without the author's code reproduces a win. A person
playing through the game's interface sees more than the observation: a demonstration, not
a witness.

- *Check:* exists: the board keys witness cells by age and interval, prints each row's age
  p50/p90 and info age (median order age plus half the mean decision gap), and sorts by it.
  Proposed (small): a decision-gap column.

### 2.4 Attack each card with shortcuts, and keep wins by other tactics

Collect shortcut ideas from several sources (the designer, critic agents without the
witness code) and record each as lost, won or untested. Test, in order: the game's own
automation with no or naive orders (fire-at-will, skirmish, pursuit, pathing, morale); the
floors; a foil doing only part of the tactic; and, when reacting is claimed to matter, a
fixed-schedule foil replaying a witness win's orders on fresh launches. When a compared
controller uses an executor or skills, also run a foil through that helper with a trivial
plan, since the helper alone may win. Count a foil battle only if the foil carried out its
play: `attack_nearest` gives no order while no enemy is visible, so it can lose standing
still. Score the outcome, not the path: a win by another tactic stays a win. If such wins
show the card tests the wrong thing, make a new version; never add a requirement after
seeing them.

- *Check:* proposed (small): `verdict()` counts a foil launch only after an accepted attack
  and a melee engagement; a test that a model win with 0 cycles is a success while a
  witness win with 0 cycles fails the gate. Proposed (medium): a `fixed_schedule` policy.

### 2.5 Audit each card against known flaws

Before admission, answer each of tactic-cards.md's [design
rules](tactic-cards.md#design-rules-from-s1-s11) with evidence or "not checked", and check
that the start, difficulty and unit size match the declaration, that abandoning the
protected unit cannot win, and that the prompt and scorer agree. Label each surprising
screening result a card defect, harness fault, controller failure or unknown. When
different controllers fail at the same point, suspect the card: refused moves at one rock
on the Taurox map broke three earlier small scenarios (S2, S3, S6).

- *Check:* manual, on the card page. The start (readbacks, 4.6) and default behaviour
  (foils, 2.4) have code checks; prompt against scorer has a proposed one (2.2).

### 2.6 Set difficulty with the witness and foils, never with the compared models

Change one knob at a time from a witness win (experience ranks are finer than unit counts)
and rerun the foils after each step, since a knob can change which tactic works. Never keep
a card or pick a step because it separates the models you will compare, and never harden a
card until current models lose. A card every model loses while the witness wins stays in,
reported as unsolved (owner: as hard as possible while still demonstrably winnable).

- *Check:* manual; record design models ([3.3](#33-record-who-tuned-on-what)).

### 2.7 Admit a card only from a frozen confirmation round

Admission comes from new launches under a rule written beforehand: card version, witness
and foil cells, counts, stop rule and signature. Screening before that only finds broken
setups and shortcuts. Name the round's directories on the card, count only launches on code
containing the rule, keep failed rounds, and never rerun an unchanged gate until it passes.
An admission holds only for its scenario, build, pack and witness. Choose gate counts from
how often they err (the chance of the wrong verdict for a controller with that true rate):

| Gate | Passes by mistake | Fails by mistake |
|---|---|---|
| Foils lose 10 of 10 (c1) | A foil winning 20%: 11% | — |
| Witness wins 4 of 5 (c1) | A 50% witness: 19% | An 80% witness: 26% |
| Foils lose 14 of 14 (proposed) | A 10% foil: 23%; a 5% foil: 49% | — |
| Witness wins 10 of 14 (proposed) | A 50% witness: 9% | A 70% witness: 42% |

Rows assume independent launches; c1's two foils shared launches, so their joint pass
chance is not the product of their rows, and each played some rematches.

- *Check:* exists: `verdict()` judges the witness on its first launches in start order.
  Proposed (small): `gate_pass()` from exact binomial sums, printed by `verdict()`;
  `card NAME --round R` reads the round's declared directories and is the only way to print
  a verdict, while plain `card NAME` stays the all-jobs view, labelled exploratory.

## 3. Keep evaluation evidence apart from development

### 3.1 Mark each job's stage, and tune only on development evidence

Explore battles may be read, tuned on and exported for training. Confirm and final battles
are scored. Reading one to diagnose a fault is fine, but if it leads to a change, those
battles become development evidence and the changed version needs new evaluation
launches. Drift
jobs never enter admission or comparison counts. The `wh3-version-review` workflow, judges
that shape a controller, and training datasets use only explore jobs on non-held-out
scenarios: automated trace review is controller authoring.

- *Why:* today the chariot card is both tuned on and scored, its scored cohorts export as
  development rows, and the review workflow accepts any episode path.
- *Check:* proposed (small): `play` records the stage (default `explore`) and accepts
  `confirm` or `final` only with the plan hash the queue passes; `export` labels rows by
  stage and `gameai.sft` drops confirm, final and drift rows as it drops `held_out` ones (a
  fixture `final` job yields no training rows). Manual: workflow scripts cannot read files.
  Proposed (small): a command run before the workflow (such as
  `twwarhammer3 digest --review-check`) that refuses evaluation or held-out episodes.

### 3.2 Reserve held-out variants before tuning, and say what was held out

Before more model runs, prompt changes or training on a card, commit a variant that keeps
the same choice on another map or roster as its own `split: held_out` entry, checked with
the witness and foils only. Label each result by what the controller was not tuned on: a
tuned card (repeatability), a held-out variant (variant transfer) or an untouched family
(family transfer). "Held out" means not played by a model before its first evaluation round
and never used for a change. It is not secret: the repository is public and its authors
read every file.

- *Check:* proposed (small): `play` refuses a model policy on a `held_out` scenario unless
  the stage is confirm or final, and prints earlier model rounds on it; `setup.scenarios()`
  stops inheriting `split` and `status` through `base` (today the admitted chariot card
  resolves to `prototype_not_admitted`).

### 3.3 Record who tuned on what

A card counts as tuned on by every model with development rows on it. For each compared
model, report those rows and whether its battles shaped the prompt or controller version:
`llm_rules` v21 was written from GLM's chariot traces, so GLM is a tuning model under v21.
Record who authored each card, witness, foil set and prompt (the owner, or which agent
model), flag compared controllers from the same model family, and record when each card
version was first pushed. Do not headline each model at its best prompt version as one
ranking.

- *Check:* proposed (small): counts from `results.csv` once it has a stage column. Manual:
  each version's log entry names the jobs behind it.

## 4. Plan and run trials

### 4.1 Count launches, not rematches

Count one episode per controller per launch, the first, as `card` does; another rule (a
fixed number of rematches, averaged) must be declared. Never count rematches, decisions or
model calls as extra battles, or pick which repeat counts after seeing results. Rematches
may pair different controllers (the default, pending [decision
5](#13-owner-decisions-these-rules-need)); never use them to repeat one.

- *Why:* a rematch restarts the launch's instance (all 10 c1 rematch starts matched to
  0.0 m), and identical order timing has replayed long stretches exactly (3 of 6
  episodes of one skills job matched to 530 s; a Bodyguard pair matched through the
  gun's rout at 97 s, then diverged).
- *Check:* exists: `cards.battles` keeps one row per job, controller and added age.
  Proposed (small): the board prints launches apart from rows (c1 shows "30 launches" for
  20 jobs).

### 4.2 Balance who plays first, and when

Give each arm the fresh-start slot equally often, assigned at random, and put every arm in
every time block (a night, or one pass of the plan through every arm) so a stop leaves the
arms equal. Runs while the owner uses the PC are their own time block.

- *Why:* later slots are rematches, possibly on a warm provider cache. Shuffling each
  launch alone does not balance: with 10 launches there is a 34% chance one arm starts 7 or
  more times (c1's `rush_nearest` had 7 of 10). Provider speed and patches vary by night.
- *Check:* exists: a per-launch shuffle and a recorded slot. Proposed (small): the queue
  requires `--rotation-seed` in confirm jobs, computes first slots with `rotation()`,
  prints first-slot and time-block tables, and refuses or warns (decision 5) when
  first-slot counts differ by more than one.

### 4.3 Freeze the whole study in one plan file

Commit one queue plan listing every job, with its `study` block ([keys](#before-you-start)).
Each manifest records the plan's path and hash; only jobs in that plan, or in a replacement
plan naming its hash and the trial it replaces, count. Replacements follow a rule written
before any outcome; a retry inside a battle belongs to the controller and is not one. Plan
in game hours as well as dollars (about 8 episodes an hour), stop between jobs, and list
jobs a stop left unstarted: when money runs out mid-study, the costly model arms are left
short, so size the budget for the whole plan.

- *Check:* exists: the queue runs only at the plan's commit with `play`'s source scope
  clean, never retries a job and records stop causes. Proposed (small): it refuses a
  confirm or final plan without the keys named in 1.1, passes the plan hash to `play`, and,
  given a declared `usd_per_job`, stops before a job when the ledger total plus that amount
  would exceed the job's `--budget-usd`.

### 4.4 Compare only matching cells, and recheck references after a change

Pool cells only when their condition keys and controller identities match (or under a
logged written reason, never across builds), and compare cells only when their condition
keys match
([1.2](#12-the-controller-is-everything-that-acts-in-the-battle-identify-it-by-content)).
Never pool across game builds. The game AI is every card's opponent and Steam can change
it, so after a Steam build change, or a change to the play loop, mailbox, Lua mod or
scorer, run the foils and witness in a small drift job (scripts only, no API cost) before
new model comparisons; what counts as passing is an owner decision. A model reference cell
can catch large provider drift, never prove its absence.

- *Check:* exists: build warnings in `doctor`; stars on cells with mixed builds. Proposed
  (small): the shared key (c1 pools b34 and b36 jobs today); "unconfirmed on build X" until
  a drift job passes.

### 4.5 Give controllers only listed public fields, and test by changing hidden data

Build controller inputs from a nested allow list of public fields, unit records included;
an unknown field is dropped and recorded, and the queue stops before the next job, never
mid-battle. Test the boundary by changing only hidden data (`evaluation`, `final`,
`setup`, hidden enemies) and asserting every controller input stays the same, and check in
the game that Lua hides what the game hides (an enemy behind a hill). Declare or fix the
known leaks: a friendly unit's `target` can name an unseen enemy, `target_dead` reveals an
unseen death, and under an added-age arm acknowledgements arrive without the added delay.

- *Why:* today the boundary is a deny list of three keys, so new mod fields and the
  observation's `job` (the operator's job name) reach controllers.
- *Check:* proposed (small): the allow list and a two-run hidden-data test of
  `play_episode`. Proposed (medium): the same for the Lua observation builder, which also
  fails on a field the list does not name. Outside controllers are trusted by convention,
  not sandboxed.

### 4.6 Say what carries over between episodes, and measure it by slot

WH3 cannot rebuild a clean environment per trial, so isolation means reading back the
declared settings and starts. Reset: a new controller object per episode. Not reset: the
game process and profile, the engine instance, provider caches, an outside controller's
module state. Declare caching and warmup as controller parts, and report outcome, cached
tokens and call time by slot.

- *Check:* exists: failed lobby, army and battle readbacks end the job (the plan stops
  unless `keep_going`). A changed rematch start stops the plan only after its job ends,
  geometry flags never stop it, and the board still counts flagged rematches (which compare
  only enemies visible at first). Proposed (small): slot tables.

### 4.7 Check order effects live

An acknowledgement means the game accepted or queued an order, not that the unit moved,
left melee or got a charge bonus. Before a signature, milestone or "foil executed" check
backs a claim, run an agreed live check following a known order to its observed effect,
including an accepted order the game then blocks.

- *Check:* manual first (benchmark.md's [correctness row](benchmark.md#correctness-checks-to-agree)).

## 5. Score every planned trial

### 5.1 One success rule per card, in one function, told to the controller

Each card names its success rule, which reads only the engine result, how the battle ended
and declared task facts; the prompt states it
([2.2](#22-tell-the-controller-everything-the-scorer-checks)). Each card declares how
draws and timer endings count (a timer ending may be the success on a point-holding card).
Every reader printing a success rate calls one function or labels its number a diagnostic.
Today four readers use four rules: `cards.outcome` (timer wins and forfeits are losses;
the primary rate), `report` (timer wins are not wins; forfeits are dropped), the HTML
report (timer wins are wins; forfeits are dropped) and `stats` (raw counts, no rate).

- *Check:* proposed (medium): a `success` field per card and one `card_result()` in
  `cards.py`, whose value `report` writes into the page data and `results.csv` stores for
  `stats`. A fixture job (contact win, timer win, draw, forfeit, construction failure,
  rematch) gives one count in the board, the report and `stats`.

### 5.2 Freeze how every trial is scored

An observed engine result is stored once and never overwritten. Every trial without one
gets a single rule from a frozen table, applied alike to every arm. A slow or crashing
controller is not an infrastructure exclusion, and an unknown cause stays unknown until
investigated with controller names hidden. "Today" means current code and
[tactic-cards.md](tactic-cards.md#score).

| Event | Counts as today | Proposed or open |
|---|---|---|
| Engine ending | The card rule applied to it | — |
| Error after the ending (acknowledgement, `close()`, budget stop) | Can overwrite the ending | Keep the ending; log a reliability failure |
| Failed decision, battle continues | The eventual ending; lost time and cost count | — |
| Terminal controller failure; wall cap reached; game silent after the cap | Forfeit (a loss); a foil's forfeit does not count toward its admission launches | Owner: is silence after the cap in a timed battle a game fault? |
| Controller fails to construct | Excluded (no battle id yet) | Unsuccessful attempt |
| Failed setup check; game silent before the wall cap (no new battle state for 60 s, such as a frozen or accidentally paused game); operator stop; HTTP 401/402 | Invalid: excluded and rerun; the witness verdict takes the next scored launch | Replacement by a rule in the plan ([4.3](#43-freeze-the-whole-study-in-one-plan-file)) |
| Spend cap reached during a battle | Excluded, like an operator stop | Not yet scored, inside the 5.3 range; size budgets so it cannot happen |
| Missing provider cost (ledger safety stop) | Excluded as a budget stop | Owner decision |
| Request the game dropped | The eventual ending (the army keeps its last orders) | Owner decision |
| Provider outage across a launch | The eventual ending, or a forfeit on terminal failure | Owner decision |
| Leak, undeclared helper, a short accidental pause or wrong game speed | Not detected (the mod always reports speed 1, unpaused) | Invalid even if won; the battle-to-wall ratio ([6.2](#62-count-every-decision-per-battle-on-the-right-clock)) catches speed, its band an owner decision |
| Planned trial never started | Listed only when a plan's job has no manifest | Listed per arm with its reason |

- *Check:* proposed (small): an `engine_result` field set only from the observed result,
  with a regression test that fails before the fix. Manual, then a test: hand-label about
  ten real episodes before reading the code's answers (a verification method once agreed).

### 5.3 Give every planned trial one visible disposition

For each arm print planned, started, scored (forfeits included as losses, also shown
separately), excluded (with rule and replacement) and unstarted. The primary rate is
successes over scored launches; other rates are labelled diagnostics. With trials not yet
scored, print the range from all-lost to all-won (8 wins, 10 losses, 2 not yet scored:
8/20 to 10/20). Never drop a failed trial's partner to keep pairs: when failures decide
which pairs survive, the rest are easier.

- *Check:* exists: the board lists a plan's jobs that never started. Proposed (small):
  `battles()` reports unreadable manifests instead of skipping them and counts per arm the
  trials a stopped job never played; a fixture with a corrupt manifest and a stopped
  rotation shows both.

### 5.4 Missing evidence is unknown, and success stays primary

Every measure reports present, absent or unknown, with its evidence and its unknown share
per arm; if one arm has more unknowns, its known battles are a selected subset and the arms
no longer compare fairly. A controller with no orders stays in the timing table; cost per
success at 0 wins is undefined; a movement is credited to the model only after a model-made
order. Continuous measures (margin, objective share, survivors) are secondary, with written
formulas, and guide development only after past paired jobs show they pick the same winner
as success (the old raw margin, which counted routing men as alive, contradicted the outcome
in 16 of 108 battles).

- *Check:* proposed (small): `cycles()` returns unknown for a frame gap inside an engagement
  (today a gap of 3 s or more silently miscounts: it can hide a pull-out or add a cycle),
  with a regression test; each applied order records its origin (reply, executor rule,
  script).

## 6. Measure time and cost

### 6.1 Keep natural latency and declared limits in the result

The primary result includes real serving delay, retries and executor behaviour: a
controller that loses because it is slow has lost (owner, 2026-10-14). Never pause or slow
the game. An added-age arm is a diagnostic that only ages observations: report the age
achieved, and count each battle under its assigned arm. Declare the token cap, timeout,
retries, effort, wall cap and spend cap, and report per arm how often each was hit: Step 5
Preview (a hosted reasoning model) at high effort had 2 of 4 replies cut off at the
16,000-token cap, so call that arm cap-bound before calling the mode weak.

- *Check:* proposed (small): `report` shows per arm the share of calls ending at a limit
  and episodes truncated before the timer.

### 6.2 Count every decision, per battle, on the right clock

Latency covers every decision: applied, refused, failed, and in flight at the end (listed
separately); report gaps without fresh orders too. Summarise each battle first (median,
90th percentile, longest gap without fresh orders), then compare across battles, so a long
busy battle does not dominate. Measure wall durations with the system clock (WSL's
monotonic clock trails it by a median 6.5% over recorded episodes) and order ages with the
battle clock, and never subtract a time on one clock from a time on the other. Each
episode's battle-to-wall ratio stays in a declared band. Orders apply on 0.3 s ticks and
frames are 1 Hz, so smaller differences mean nothing. For `commander`, model latency is in
call times and plan age, not `think_s`.

- *Why:* today only acknowledged requests enter `delays_ms` (a 178.5 s call returning after
  the ending was missed), and `clock_ratio` stops at the last observation read before the
  final call (since b39, `e2777f4`), so it misses a stall during that call; before b39 a call
  returning after the ending lowered it.
- *Check:* proposed (small): `result.json` lists every decision (for `commander`, every
  model call) with its time and fate: applied, refused, failed, never acknowledged,
  returned after the ending, or running at close; a test whose simulated call returns after
  the result shows it there and in the median. The ratio comes from battle and wall time at
  the first and last acknowledgements; the HTML report uses per-battle medians.

### 6.3 Count all cost, and check it against the ledger

Cost covers every attempt (failed, excluded, retried), split by token type, with its source
(pinned price table, provider report or outside controller) and price date. Show cost per
success only with its win count, beside the $0 scripted rows. A study's ceiling is "ledger
total at start plus allowance", since `--budget-usd` caps the whole ledger; on OpenRouter
it must also leave room for the Spire ledger (the $50 covers both games).

- *Check:* proposed (small, read-only): each traced response appears once in the ledger
  with the same cost, and the ledger total over the job's window matches its recorded cost.

## 7. Use statistics that fit small live studies

WH3 studies run tens of launches, the cards were picked by hand, and rematches share their
launch. So count launches, report each card on its own, use small-sample methods and aim at
large effects. The numbers below were recomputed with a local script not in Git
(`runs/twwarhammer3/eval-guidelines-review-20261020/numbers/check_numbers.py`) and
independently by a reviewer; standard exact-binomial tools reproduce them.

### 7.1 Say what each number covers

A card rate estimates the chance this controller wins its counted episode of a launch of
this card version (fresh start or rematch, in the plan's mix) under these conditions:
build, host, timing, provider and period. Report every card and variant separately; the
interval covers repeat launches of these cards, not other tactics. Do not divide by the
witness rate: it is noisy and no ceiling (on S1 a model won its one battle at about 3.6 s
order age; the witness won 1 of 2 fresh and 0 of 2 at 5 s). A suite summary needs frozen
weights, and a missing card makes it missing.

- *Check:* exists: `report` never pools across its groups. Proposed (small, later): a
  suite function that refuses a missing card.

### 7.2 Use the named method for each situation

| Situation | Method | Example |
|---|---|---|
| One controller, one card | Wilson 95% | 4 of 5: 38-96%; 10 of 14: 45-88% |
| No wins, or a "rarely wins" gate | Exact one-sided 95% bound (for 0 of n: 1 − 0.05^(1/n)) | 0 of 10: below 26%; 0 of 14: below 20%; 1 of 10: below 39% |
| A and B on the same launches | Both / only A / only B / neither; exact McNemar; Newcombe paired interval with his corrected correlation | Both 0, only A 6, only B 2, neither 12: +20 points (−8 to +45), p = 0.29 |
| A and B on separate launches | Fisher exact; Newcombe interval for two rates | 0 of 10 against 5 of 10: p = 0.03 |
| One continuous value per launch (paired differences when arms share launches) | t interval; for skewed values such as latency, a sign-test interval for the median | — |

McNemar's test uses only the launches exactly one arm won; Newcombe's intervals bound a
difference of two rates and stay sensible at small counts; Fisher's test compares rates
from separate launches. Tests are two-sided at 5% with classic exact p-values, which are
cautious here (with no real difference, Fisher at 10 per arm rejects at most about 1.3% of
the time, far less when both rates are near 0); gate bounds are one-sided 95%. These
methods are our choice: Bowyer et al. recommend Bayesian intervals for A − B and find
Fisher too conservative at small n, and a Bayesian interval is allowed if its prior is
stated. Never report a normal (Wald) interval or a bootstrap at these sizes: Wald gives
0-0% for 0 of 10 and covers the truth only 51% of the time at 14 launches and a 5% rate; a
bootstrap of ten losses resamples only losses. Wilson averages about 95% coverage but can
fall to about 84% for true rates near 0 or 1, and it assumes one episode per launch. Print
the method with every interval; no interval covers a wrong scorer or leaked information.

- *Check:* exists: `report.wilson`, a t interval. Proposed (small): exact-bound, McNemar and
  Newcombe helpers tested against worked examples published with each method or a second
  implementation, not only this page's numbers; method names in board headers.

### 7.3 Compare A and B on shared launches, and say "unresolved" when it is

Report A, B and A − B with its interval and launch count, the four joint counts, unpaired
launches and why, and the correlation between arms. A comparison is resolved only when its
named two-sided test passes its declared threshold (p < 0.05 for the one primary
contrast); the interval beside it shows the size. They can disagree: 0 of 10 against 4 of
10 gives Newcombe +4 to +69 points but Fisher p = 0.09, so it is unresolved. Overlapping
separate intervals are not a test. Never write that two controllers perform the same: 20
launches cannot show two rates lie within a useful distance. Pairing mainly protects
against drift between nights; it gains precision only when both arms tend to win or lose
the same launches, and even then exact McNemar on 10 shared launches can be weaker than
Fisher on 10 per arm (20% against 70%, with A winning only where B wins: 38% against 43%).
A comparison with an older period is unpaired: say so, and run a reference controller in
both periods.

- *Check:* exists: `report` pairs the margin per launch and lists unpaired launches.
  Proposed (small): the 2×2 table and paired interval from the card outcome. Proposed (no
  API cost, if agreed): an A/A run (the witness as both arms, which should show no
  difference) on separate launches, since within one launch a fixed-age script may simply
  replay the battle.

### 7.4 Decide before you look

Before the first launch, fix n, the stop rule and one primary contrast; label the rest
exploratory or name a correction (such as Holm's, which lowers the p-value each contrast
must reach as more are tested). A run of many controllers on frozen cards reports each
controller's rate per card with its interval (28 to 53 points wide at 10 launches, widest
near 5 of 10) and orders two controllers only when their test passes after Holm's
correction over every pair shown. Print the chance the plan detects the gain you care
about, not only the smallest clear split: with 10 separate launches per arm (Fisher,
two-sided 5%), a true rise from 0% to 50% is found 62% of the time, 20% to 70% only 43%,
and finding a gap 8 times in 10 takes about 60-70 points (10% against 80%: 84%). Away from
zero a 5-win gap is not clear (3 of 10 against 8 of 10: p = 0.07). On 20 shared launches a
true net gain of 20 points is found only 12-20% of the time, and at least 6 launches won
by one arm only, with none by the other, are needed to pass. So confirm large changes and
treat 10-point prompt tweaks as exploratory. A gate may stop once no remaining launch can
change its verdict (the first foil win; the witness's fourth win, or its second loss, of
five); report the counts, not a rate interval. Never stop a comparison early because it
looks clear. Picking the best of many screens inflates it: 20 prompt versions each truly
winning 20%, with 5 launches each, show at least one with 3 or more wins of 5 with 70%
probability, so confirm a chosen version on fresh launches and report how many were
screened.

- *Check:* proposed (small): an exact `plan_power()` printed by the queue (gates use
  `gate_pass()`, 2.7); `report --primary` labels the primary row; "verdict incomplete"
  while planned launches are unfinished.

## 8. Read battles and interpret results

### 8.1 Scan every battle, then read a fixed sample, before counting a cell

Run a fault scan on every battle, wins included, then read at least one win and one loss
chosen by a fixed rule. The scan also looks for signs that the harness stopped play: a
request the game dropped (Lua only logs it; `play` keeps waiting for its acknowledgement
and never asks the controller again, so the army keeps its last orders and looks passive),
`mod.log` errors, repeated infrastructure failures in a launch. A flagged battle is
inspected, not dropped, and excluded only under the failure table; if reading shows a
problem with the evaluation itself, hold the result. Example: a wizard launch on the
Empire night (an overnight run of Empire battles) lost on garbled replies from its pinned
backend (7 calls averaging 88.9 s, against 1.6-5.8 s in the other 27 GLM and Kimi
launches). It stays GLM's loss, since serving belongs to the controller
([6.1](#61-keep-natural-latency-and-declared-limits-in-the-result)); the scan flags it so
the owner can decide whether that backend's later battles form a separately labelled
cohort.

- *Check:* proposed (small): `digest` prints failed decisions (today it skips them), and a
  `faults()` list flags failed decisions, invalid batches, refusals, cut-off replies, calls
  slower than a stated multiple of the arm's median, dropped or stale requests, `mod.log`
  errors, missing files and flagged starts.

### 8.2 Label failures from one short list, and find where a loss went wrong

Give each lost or flagged battle one or more labels, per battle and not per decision, each
decided by its record:

| Label | Decided by |
|---|---|
| Harness fault | Logs |
| Serving fault (an error, cut-off or garbled reply) | Call attempts |
| Missing information | The prompt |
| Misread interface (a fact shown but never explained) | Prompt and reply |
| Poor choice | The prompt, its age, the orders |
| Late order | Acknowledgement time against the replay |
| Order not carried out | Acknowledgement and replay |
| Card defect; unknown | Any record |

Judge decisions against the snapshot the reply answered (`digest --at`), not the later
replay. GLM's v20 re-attacks were mostly a misread interface: by their stated reasons, 10 of
14 believed the chariot clear while its melee flag was on (the prompt never said positions
are unit centres), and 3-4 chose to grind, a poor choice (an unverified reading). Give each
card two to five ordered milestones code can detect, and read a loss by the first one
missed; milestones never give partial credit.

- *Check:* proposed (small): the fault scan proposes the first two labels; a review file
  under `runs/`. Proposed (medium): milestone predicates reusing `engagements()`.

### 8.3 Controller text and LLM reviews are leads, not evidence

A controller's notes and reasoning say what it meant to do; only orders, acknowledgements
and later state show what happened. LLM reviews, the `wh3-version-review` workflow's
included, are development leads whose counts and causes stay out of results until a saved
script recomputes them. Review agents get controller text quoted as evidence and are told
not to follow instructions inside it. A number read from traces states its definition and
comes from a saved script; when it backs a version decision or a published claim, recheck
it under one other reasonable definition (GLM's countermands read 14 or 12 depending on
whether a queued later attack counts).

- *Check:* proposed (small): the workflow saves its reviews and the episodes it read, with a
  fixed cause list including "unknown". Manual: the workflow's prompt wording; log entries
  say when they quote an LLM review.

### 8.4 Claim a cause only after changing it

Write observations as observations ("the order applied 9 s after its snapshot"). Say
"caused" only after an assigned change, judged by the card outcome on launches started
after it, and treat a first small-study gain as an overestimate. After prompt v21, attack
orders issued with the melee flag on fell from 56 to 38 over 10 battles, yet wins went from
1 of 10 to 0 of 10; the cohorts ran on different nights and harness versions, so neither
change is shown to come from the prompt.

- *Check:* manual: a change's log entry names the diagnostics behind it and the later jobs
  that confirm it.

### 8.5 Write results as counts beside reference rows

Print "won k of n" with interval and method, forfeits and exclusions, beside the foil and
witness rows for the same card version and build. With no wins write "0 of n, probably
below b", and say what that does not show (that the model cannot learn the tactic). Do not
rank unresolved pairs; use no verdict word the cell size cannot carry ("better", "solves",
"significant" without the test); show known confounds such as fresh start against rematch;
mark unagreed checks **unverified**. Example: "GLM-5.3 low, v20: won 1 of 10 (Wilson 95%:
2-40%); each foil 0 of 10 (exact one-sided 95%: below 26%); witness v1 won 4 of 4 at 2 s
added age with a 2 s interval and 3 of 4 at 3 s and 3 s, the cells nearest GLM's median
order age of 2.1 s (unverified)."

- *Check:* exists: the board lists foils first, with Wilson intervals. Proposed (small):
  mark a model cell whose setup differs from its reference rows; print fresh-start counts.

## 9. Recount, release and maintain

### 9.1 Rebuild every reported number from a hashed evidence index

A released result names an index of the job directories and label files it used, each with
its sha256. One command rebuilds every table from it and fails on a missing or changed file;
labels come from saved replies, never from asking a judge again. The index goes in Git, the
files stay in `runs/`. Before citing a round as admitted or confirmed, copy it and its index
to a second place, log the location and hash, and recount once from the copy.

- *Why:* a recount is the only exact outside check, `runs/` has no off-machine copy, and
  today a missing replay changes the verdict.
- *Check:* proposed (small): `card` and `report` accept an index and hash what they read, as
  `export.py` already does; a test that deleting one replay makes the recount fail.

### 9.2 Version the scorer, correct in the open, and keep releases frozen

A frozen verdict names its rule and its scorer code version; the code applying the chariot
rule changed in five commits after registration (b35, b38, b39, b40 and `fab56b0`). When a
scorer, card or label proves wrong, keep the old output, publish the corrected one for
every affected controller and export, and say which claims change. New rules apply to
rounds started after them; older verdicts keep their rule and print one line naming the
rules they predate. A released suite is a fixed list of card versions plus a scorer
version; a harder card is a new version. Move cards to a regression pack once every
compared controller wins nearly every launch (the owner sets the number).

- *Check:* proposed (small): `scorer_version` per card, and a test hashing the syntax trees
  of `outcome` (later `card_result`), `jobs`, `battles`, `engagements`, `cycles`, `mixes`
  and `verdict`, with `MERGE_S` and the card's `CARDS` entry (the pattern that keeps
  `spire/protocol.py` stable).

### 9.3 Offer outside checks in three steps, and claim only what each shows

A **recount** from released evidence checks the analysis. An **interface check** (later,
once an outside controller is expected) feeds recorded public observations through the
simulated game API and checks order format and timing. A **rerun**
([proposal](benchmark-run.md#independent-rerun-acceptance-proposal)) on an owned copy checks
that the procedure works elsewhere. None reproduces trajectories or the exact win rate. The
prerequisites are in [benchmark-run.md](benchmark-run.md#before-a-run).

- *Check:* manual: log each completed step with date, revision and who ran it.

### 9.4 Publish a short summary page and a clean bundle

The summary page links rather than repeats. It covers intended use and what the cards leave
out; how cards were chosen; the controller contract; the plan; per-launch rows with every
disposition; every controller version run on final cards; per-card results with intervals,
timing and cost; how labels were made; the authorship and tuning records of
[3.3](#33-record-who-tuned-on-what) and who reviewed outcomes; limits (a bought game,
patches, hosted models, no seeds, few cards); and related work on the
[five closest-work points](benchmark.md#research-that-changes-the-design). One bundle step
builds public evidence: indexed files only, no game files or credentials, no model text from
providers the owner has not cleared, policy-visible fields marked, and a failure on
identifying data. Check the publisher's screenshot policy before sharing stills.

- *Check:* proposed (small, at the first public release): the bundle step with a deny-list
  scan, tested with a planted fake key.

## 10. Later: human review, LLM judges, rubrics and training rewards

None exists for the first release. Recommended: no LLM-derived label in a reported score.

### 10.1 Let code decide what records can decide

If recorded state answers a check, code decides; nobody overrides or averages it. People
answer what code cannot (whether a win used the card's choice, whether a loss was a harness
fault), never whether a battle was won. An LLM gets only questions that need reading text
("does the stated plan match the orders?"), never a tactical-quality score.

### 10.2 Give reviewers one question, one sheet and a fixed evidence packet

Each question gets a short versioned sheet (purpose, options, terms tied to recorded
fields, ordered yes / no / cannot-tell steps, things to ignore, worked examples and
near-misses), piloted on development battles and then frozen. Cut battles into fixed items
(one unit, question and time window). The first pass hides the outcome, verdicts, the
controller's stated reasons and arm names; reviewers can often still tell who played, so
ask them to guess and report how often they were right. Every answer cites its record or
gives a reason for "cannot tell" ("in melee" is the 1 Hz melee flag, which shows neither the
enemy fought nor a charge bonus).

- *Check:* exists: `digest --at` shows a decision without the ending. Proposed (small, when
  needed): a `--blind` flag and one label script.

### 10.3 Label independently, and report agreement in full

Two reviewers label a shared set alone, locked before anyone sees a code check's or judge's
output. Report the 2×2 counts, n, raw agreement and agreement on "yes" and on "no"; put
Cohen's kappa or Krippendorff's alpha only beside them (two reviewers each saying "yes" on 2
different items of 30 agree 87% overall and 0 of 4 on "yes"). List every disagreement with
its cause; tactical opinions stay notes, never majority facts. The owner's labels alone are
"designer, single reviewer", and agent reviews are not human labels. Batches picked to find
failures support no rates; a rate needs a recorded random sample.

### 10.4 Validate any automatic label against held-out human labels

Compare a code check or judge with human labels from distinct launches made without seeing
its output. Report with counts its true positive rate (TPR, real cases flagged) and true
negative rate (TNR, the share of non-cases it passed), per controller and card, beside
human-human agreement and an always-majority baseline: a judge calling everything
acceptable is 95% accurate when 5% are errors. Split example, tuning and test sets by
launch. Before use, test swapped order and renamed controllers, confident text without
matching orders, a good decision then a loss, a blocked acknowledged move, a recording
gap, and an instruction hidden in controller text. Version the judge, pin its sampling
across arms, and choose the judge model first (it mattered most in Autorubric). Correct a
judge-counted rate as (observed + TNR − 1) / (TPR + TNR − 1), clipped to 0-100% and
carrying the uncertainty of TPR and TNR: 20% observed with TPR 0.8 and TNR 0.9 becomes
14%.

### 10.5 Keep rubric items narrow and out of the score; a training signal cannot judge training

Each check says what happened, which fields show it, when it applies and what is recorded
when evidence is missing (pass, fail, not applicable or unknown, each rate counting only
battles where the item applies). Keep one to three items per card, check assumed mechanics
against game data rather than an LLM's game knowledge, and add no weighted rubric total to
an evaluation; a leak invalidates the trial rather than costing points. Anything used to
train or select data (items, judges, signatures, outcome filters such as
`--require outcome.gameplay_outcome=won`, which keeps timer wins) cannot show that training
worked: show gains on engine outcomes on frozen unseen cards, against the untrained model
and an outcome-only reward. Plan training and evaluation variants per family first, label
in-family scores "in-distribution", fix the checkpoint rule in advance, and look for reward
hacking (repeated harmless withdrawals, a bonus per cycle).

- *Check:* exists: `gameai.sft` drops `held_out` rows. Proposed (small, later): a
  reward-spec hash in the dataset manifest.

## 11. Common advice that does not apply, or works differently here

Six facts drive most differences. Battles run at 1x and never pause. No seed controls a
battle, and rematches restart their launch's instance. One game runs at a time on the
owner's PC, about 8 episodes an hour, mostly overnight. The cards are few and hand-built.
The game, its AI opponent and the hosted models change under us (Steam updates; pins warn
but never block). The authors are one owner and AI agents in a public repository.

| Common advice | Why not here | Instead |
|---|---|---|
| Start with 20-50 tasks; turn every failure into a task | Each card needs live screening and confirmation | A few cards; other failures become development scenarios or tests |
| Fresh container, fixed seed, exact replay | One Windows install keeps state; no seed controls a battle | Readbacks; pairing within launches; count launches |
| Pause while the model thinks | Thinking time is under test | Natural latency; added-age diagnostics |
| Equal compute across reasoning modes | At 1x, compute costs game time | Each mode is its own controller |
| Best of k (pass@k); many samples per task | One try per battle; rematches are not independent | First episode of each launch; pass^k (the chance that k fresh launches all win, estimated as C(c,k)/C(n,k) from c wins in n launches) only for a declared reliability question |
| Mean ± standard error for win rates, CLT, bootstrap, clustered errors | 5-20 launches, often all wins or all losses | The methods in [7.2](#72-use-the-named-method-for-each-situation) |
| Tasks as a random sample; domain averages; normalised scores | Hand-picked cards; the witness is no ceiling | Per-card counts beside reference rows |
| Keep items that separate models; harden until they fail | It tunes the suite to the compared models | Difficulty from witness and foils |
| Drop infrastructure and API errors as noise | Serving reliability is part of deployment | A frozen failure table |
| Hidden test sets, canaries, submission limits, text-overlap tests | The repository is public, so a variant is secret only while unpushed (decision 4); outputs are timed orders, not answer strings | "Not played by a model"; exposure records; push dates against model release dates; fresh variants; optionally a canary string at release |
| Lower temperature for tidy error bars | It changes the controller | Evaluate declared settings; a judge pins one setting across arms |
| LLM judges, pairwise preference, Elo | Code scores outcomes; the opponent is fixed; battles diverge | Code first; per-card rates |
| Crowd label models, kappa bands | One owner, few reviewers | Small double-labelled sets with every disagreement |
| Small subsets chosen from past results (tinyBenchmarks); filtering hard items as mislabels | They need many models and items; outcomes come from the engine | Run every card; audit scorer, setup and recording |
| Evaluate every commit, in parallel | One game at a time, on the owner's PC | `pytest` per change; drift jobs after a build or harness change |
| Freeze the environment | Steam updates; pins warn but never block | Record the build; drift jobs |
| A human baseline | A person plays through a different interface | Not planned; if added, a labelled reference row |

## 12. Where to enforce first

In order of how much a wrong result would cost; build each only when a planned study needs
it, and rely on one only after the owner agrees its check.

1. Observed endings never lost or overwritten ([5.2](#52-freeze-how-every-trial-is-scored)).
2. One `card_result()` for every reader ([5.1](#51-one-success-rule-per-card-in-one-function-told-to-the-controller)).
3. Every planned trial accounted for ([5.3](#53-give-every-planned-trial-one-visible-disposition), [4.1](#41-count-launches-not-rematches)).
4. A foil launch counts only after the foil acted ([2.4](#24-attack-each-card-with-shortcuts-and-keep-wins-by-other-tactics)).
5. The `study` block, stage, plan hash and first-slot tables ([4.2](#42-balance-who-plays-first-and-when), [4.3](#43-freeze-the-whole-study-in-one-plan-file), [3.1](#31-mark-each-jobs-stage-and-tune-only-on-development-evidence)).
6. The held-out guard ([3.2](#32-reserve-held-out-variants-before-tuning-and-say-what-was-held-out)) and the review check ([3.1](#31-mark-each-jobs-stage-and-tune-only-on-development-evidence)).
7. Condition key and controller identity ([1.2](#12-the-controller-is-everything-that-acts-in-the-battle-identify-it-by-content)).
8. Every model call in latency ([6.2](#62-count-every-decision-per-battle-on-the-right-clock)).
9. The public-field allow list and hidden-data test ([4.5](#45-give-controllers-only-listed-public-fields-and-test-by-changing-hidden-data)).
10. `scorer_version` ([9.2](#92-version-the-scorer-correct-in-the-open-and-keep-releases-frozen)).
11. The small-sample methods and paired table ([7.2](#72-use-the-named-method-for-each-situation), [7.3](#73-compare-a-and-b-on-shared-launches-and-say-unresolved-when-it-is)).
12. Failed decisions in `digest`, then the fault scan ([8.1](#81-scan-every-battle-then-read-a-fixed-sample-before-counting-a-cell)).
13. The `told` / `withheld` prompt test ([2.2](#22-tell-the-controller-everything-the-scorer-checks)).

Once built and agreed, code can catch missing fields, mixed versions, lost endings and leaks
of the fields its tests vary. It cannot show that a card tests its tactic, that an order had
its effect, or that a claim is fair; those need agreed live checks and reading.

## 13. Owner decisions these rules need

1. The defender prompt's "if time runs out, you win" (every defending battle, the line and
   expendables cards among them): decided 2026-10-21, change the prompt (a contact-scoring
   scenario field); timer wins stay uncounted.
2. The open failure-table rows ([5.2](#52-freeze-how-every-trial-is-scored)), construction
   failure (the failure rule was agreed 2026-10-21; its scoring is not implemented yet),
   whether draws count per card, and whether the battle-to-wall band invalidates a
   battle or only flags it. Recorded ratios (2026-10-21, 427 engine-ended episodes,
   `runs/twwarhammer3/away-20261021/clock_ratio.txt`): median 0.999, p5 0.985, p95 1.005;
   10 fall outside 0.95-1.05, all recorded before b39. Nine are model battles whose final
   call (29-760 s) returned after the ending, which the ratio then still counted; since
   b39 it stops at the last observation of the running battle (68 later episodes, 39 of
   them model battles, 0.981-1.009). The tenth, a scripted floor at 0.878 (`bench-b19-s2-decoy-floor-20261017`),
   went 22 s and then 43 s of system time between consecutive observations 0.3 s of battle
   time apart: a game stall, the accidental pause the band should catch, or a step of the
   WSL clock (its monotonic clock trails by a median 6.5%, so it cannot tell which). Gaps
   over 10 s mid-battle are rare: 2 in 286 scripted episodes (`stalls.txt`). Invalidating
   by the stored ratios would also discard those 9 for call latency; today's would not.
3. Which witness timing cell makes a card "demonstrably winnable", and witness v2 (already
   [pending](../state.md#owner-decisions-waiting)).
4. Whether the chariot card is also a training environment, which variant to reserve first,
   whether reserved variants stay unpushed until played, and how existing chariot model
   cohorts are staged (training-eligible or not).
5. Pairing within launches (the default) or one controller per launch; refuse or warn on
   unbalanced plans. Cost (2026-10-21, 307 completed jobs): a fresh launch adds a median
   117 s around its battles and each rematch about 30 s, so pairing three controllers per
   launch saves about 40 minutes of a 42-trial confirmation (about 13%).
6. An allow list that drops and records unknown fields, removing `job`, and aging
   acknowledgements under added age.
7. The method set in [7.2](#72-use-the-named-method-for-each-situation) as an agreed check;
   first episode per launch or a declared fixed number of rematches.
8. Whether a non-designer reviewer will exist, and keeping LLM labels out of scores.
9. Whether c1 keeps its verdict, printing one line that notes its b34/b36 harness mix and
   the later scorer changes. A blind recount from the docs and raw files reproduced its
   counts and verdict (2026-10-21, `runs/twwarhammer3/away-20261021/handoff-c1/`).
10. What a drift job must show to pass after a build or harness change.
11. Which providers' text and which stills may be published; where `runs/` is backed up.
12. Whether benchmark.md's Terms adopt this page's "controller", and whether
    tactic-cards.md's witness row drops "a person's win" (a demonstration, 2.3).

## Sources

Read on 2026-10-20: eleven of the twelve readings the owner assigned (all listed below) in
full text, Wolfe's
LLM-as-a-Judge through section summaries; most cited and related work in part (main
sections or abstracts); MMLU-Redux only through Wolfe. The rules apply these sources; the
studies do not show the rules work for WH3.

| Source | Used for | Limit |
|---|---|---|
| [Weng, High-Quality Human Data](https://lilianweng.github.io/posts/2024-02-05-human-data-quality/) | Reviewer training, agreement limits, rule versus opinion labels | Crowd scale |
| [Yan, Labeling Guidelines](https://eugeneyan.com/writing/labeling-guidelines/), with the Google and Bing rater guides it uses | The sheet layout in 10.2, an "unsure" option, revision while tracking agreement | Search-rating tie-breaks do not transfer |
| [Wolfe, LLM-as-a-Judge](https://cameronrwolfe.substack.com/p/llm-as-a-judge), [Zheng et al.](https://arxiv.org/html/2306.05685v4) | Judge setups; position, length and self-preference bias | Text tasks |
| [Husain, LLM-as-a-Judge](https://hamel.dev/blog/posts/llm-judge/index.html) (updated 2026-09) | Expert pass/fail labels, error analysis, true positive and negative rates, 20/40/40 judge splits | Product setting |
| [Yan, LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/) (2024), [Shankar et al.](https://arxiv.org/html/2404.12272) | Classification metrics over correlations; criteria drift while grading | Older text judges; freezing is our rule |
| [Wolfe, Rubric-Based Rewards](https://cameronrwolfe.substack.com/p/rubric-rl), [Rubrics as Rewards](https://arxiv.org/html/2507.17746v2) | Rubric rewards, reward hacking, not judging with the training judge | Rewards; LLM-written rubrics |
| [Autorubric](https://arxiv.org/html/2603.00077v3) (v3) | Narrow criteria, "cannot assess", judge model choice | No WH3 judge accuracy |
| [Wolfe, Statistics for LLM Evals](https://cameronrwolfe.substack.com/p/stats-llm-evals), [Miller, Error Bars](https://arxiv.org/html/2411.00640v1) | Paired differences, planning n | Large question pools |
| [Bowyer et al.](https://arxiv.org/html/2503.01747v3), [Card et al.](https://arxiv.org/abs/2010.06595), [Abadie et al.](https://arxiv.org/abs/1710.02926), [List et al.](https://www.nber.org/papers/w15701) | Small-sample intervals; power before the study; the design sets the unit; order effects | General statistics |
| [Wolfe, Anatomy of a Benchmark](https://cameronrwolfe.substack.com/p/llm-bench), [MMLU-Redux](https://arxiv.org/html/2406.04127v3), [BBEH](https://arxiv.org/abs/2502.19187), [GPQA](https://arxiv.org/abs/2311.12022), [IFBench](https://arxiv.org/abs/2507.02833) | Harder, fixed and broader items as new versions; item audits; saturation; reference-model bias; overfitting to a public test | Static question sets |
| [Wolfe, Agent Evaluation](https://cameronrwolfe.substack.com/p/agent-evals), [τ-bench](https://arxiv.org/html/2406.12045v1), [τ²-bench](https://arxiv.org/html/2506.07982), [Terminal-Bench 2.0](https://arxiv.org/html/2601.11868v1) | Model and scaffold judged together; pass^k; instructions matching tests; deliberate cheating | Containers with resets |
| [Anthropic, Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), [infrastructure noise](https://www.anthropic.com/research/infrastructure-noise) | Reference solutions, regression sets, reading transcripts, outcome grading, resource limits | Clean resets |
| [Agentic Benchmark Checklist](https://arxiv.org/html/2507.02825v1), [BetterBench](https://arxiv.org/html/2411.12990v1), [Bean et al.](https://arxiv.org/html/2511.04703v1), [Leaderboard Illusion](https://arxiv.org/html/2504.20879), [HAL](https://arxiv.org/html/2510.11977v1) | Task and outcome validity, floor and ceiling rows, measuring one skill, selective disclosure, cost beside accuracy | A checklist is not verification |
| [Röttger et al.](https://arxiv.org/html/2112.07475v2), [Zhang et al.](https://arxiv.org/html/2311.04345v1) | Rule versus opinion labels; reasons for disagreement | Subjective NLP labels |
| [BALROG](https://arxiv.org/html/2411.13543), [VideoGameBench](https://arxiv.org/html/2505.18134), [TextStarCraft II](https://arxiv.org/html/2312.11865v3), [LLM-PySC2](https://arxiv.org/html/2411.05348v2), [Real-Time Reasoning Agents](https://arxiv.org/html/2511.04898v1) | How game benchmarks handle pausing, seeds and timeouts | Most pause, count tokens as time or seed; VideoGameBench's main setting runs live |
| [tinyBenchmarks](https://arxiv.org/html/2402.14992v1), [Dataset Cartography](https://arxiv.org/html/2009.10795v2) | Why subset selection and label-noise filters do not apply | Need many models or a classifier |

Project research that changed the design: [benchmark.md](benchmark.md#research-that-changes-the-design).
