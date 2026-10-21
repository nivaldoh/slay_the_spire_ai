# WH3 latency-aware battle benchmark

Current definition reviewed 2026-10-20; the checks below are proposals for the owner,
not newly agreed verification methods. Gameplay findings remain unverified under the
[hard rule](../../AGENTS.md#verification-hard-rule). The owner's brief is
[WH3_latency_aware_benchmark_requirements.md](WH3_latency_aware_benchmark_requirements.md).
How to run it: [benchmark-run.md](benchmark-run.md). The report: [reports.md](reports.md).
Design and review guidance: [evaluation-guidelines.md](evaluation-guidelines.md), covering
the supplied evaluation research, WH3 adaptations and proposed code enforcement.
What is running now: [docs/state.md](../state.md). Dated history: [log.md](log.md).
Evidence paths under `runs/` are local and not in Git.

## Purpose

Which controllers can carry out specific tactics while the battle keeps moving, and
what prevents the others from succeeding? Start with small, inspectable battles against
the game AI, mostly using Empire units; add larger coordination problems when they test
a distinct decision. Another developer must be able to substitute a controller and
interpret its results. The brief's acceptance question:

> Can an independent user evaluate a different battle controller under the same declared
> scenario, information, action, and timing rules, and understand both its performance
> and the limitations of the comparison?

Settled by the owner on 2026-10-14: each controller's whole latency, network included, is
part of its result, as it would be in a real deployment. A controller that loses because
it is slow has lost. Delay arms (below) are diagnostics beside that primary result.

## Scope and first release

The scope is **evaluation of complete battle controllers on a small, declared set of
real-time tactical tasks**. The intended user is a developer choosing or improving a
controller: they should be able to replace ours, measure success, cost and reliability,
and inspect a consequential failure. Results describe the controller, its helpers and
its serving conditions together. They do not rank a model's general intelligence.

This section consolidates the owner's brief and later directions. The release gates
below are proposals, not newly agreed checks or permission to implement or run them.

| Boundary | Initial benchmark | Outside the initial release |
|---|---|---|
| Battles | Declared custom battles against the built-in game AI; mostly small Empire tasks, other factions for a distinct challenge | Campaign, general WH3 mastery, every faction/mode, human or model opponents |
| Controller | Scripts, direct models and hybrids using the same public contract; disclose all tactical helpers | A required planner, multi-agent architecture, provider or training method |
| Interface | Structured, numerically exact state with the documented visibility limits; game pathfinding and combat remain active | Vision, mouse/keyboard play, player-equivalent perception or low-level robot control |
| Time | Unpaused 1x with natural end-to-end latency; assigned delay only as a separately labelled diagnostic | Paused reasoning, an equal-speed intelligence ranking or a guaranteed reaction deadline |
| Task coverage | Distinct consequential choices, with witnesses, credible wrong plays and inspected effects | A claim that every win uses one tactic, or that a large army alone tests context length |
| Results | Per-card outcomes and uncertainty, failure counts, achieved timing, cost and inspectable records | One composite leaderboard number or a ranking from selected successful trials |
| Delivery | Project code/configuration, accessible reference evidence and a runbook for the supported Windows/WSL installation with the required game content | Bundled game assets, general portability, parallel/cloud hosting, deterministic replay |

The **first reusable path** is one frozen card evaluated end to end, including another
developer's recount and rerun. The **initial suite release** is a frozen small set of
distinct cards that each pass that path, with reference controllers and results, exact
commands, evidence access and known limitations. Scenario declarations and a report
alone are not a release. A suite needs no aggregate score; its claims extend only
to the named cards and tested variations.

Latency, advice-versus-execution and team recovery are research questions studied using
that benchmark. Recovery earns a card if it adds a distinct, measurable problem; a
successful recovery architecture is not required to release useful tactic cards.
Training remains secondary: preserve usable traces and the controller boundary, but do
not make an Empire fine-tune, an RL adapter or a training gain a release dependency.

**Readiness today:** the interface and evaluation design are substantially specified;
the useful suite is not settled. The chariot was admitted under its historical rule but
remains unverified; the Empire line is a candidate, and the revised b46 arms are unplayed.
The correctness checks and independent rerun below are still pending. There is a path
to a useful benchmark, not evidence yet that all its intended claims will hold.

## What would make it good

The first four rows describe intended release quality; distinctiveness is a separate
research goal. None is established by this document. A useful suite can release without
a positive novelty or recovery result, and no milestone requires a particular model or
architecture to win.

| Aim | Evidence needed | Decision if the evidence fails |
|---|---|---|
| Strong | Repeated witness success at declared timing, credible shortcuts tested, and a comparison whose uncertainty can resolve its stated question | Keep an all-losing model screen exploratory; narrow the claim or change the candidate, rather than calling it frontier difficulty |
| Useful | Another developer can substitute a controller and answer a concrete choice about tactics, supplied advice, timing or helpers, with cost and failures visible | If every arm looks the same at the affordable sample size, report an inconclusive comparison; do not advertise a ranking |
| Reliable | Agreed setup, information-boundary, live-effect, scoring and signature checks pass at the released revisions; an independent recount/rerun works | Hold the affected card or claim out of the release; do not equate component tests with live correctness |
| Interesting | Inspected decisions change the battle in a way the named simple alternative does not explain; show at least one consequential success and failure | If a fixed opening, engine automation or abandoning the protected unit explains success, relabel the task or drop it |
| Distinctive | A concrete comparison with the closest benchmarks identifies a useful question this suite makes easier to test, supported by a completed WH3 study | Publish the narrower evaluation contribution if warranted; do not claim unique mechanics, first real-time agents or robot transfer |

Do not pick tasks because a preferred model wins, or keep hardening them until all
models fail. Freeze selection before the comparison. Inspect alternative winning plays:
they remain wins and may falsify the claimed skill requirement. A negative recovery or
latency result is useful when the design can distinguish it from a broken controller,
uninformative task or insufficient sample.

## The decisions the benchmark should support

| Question | Smallest useful comparison | What it does not establish |
|---|---|---|
| Can it apply the tactic? | Frozen card, winning reference and plausible wrong plays; review actions and subsequent state | A statement of the tactic is not its execution; finite foils cannot prove only one tactic can win |
| Does explaining the tactic help? | Same model/interface, rules alone versus the same rules plus the tactic | This is the effect of supplied advice; offline answers or reason text cannot isolate knowledge from execution |
| How sensitive is success to timing? | Same controller, one assigned timing change, achieved ages and decision gaps reported | Extra delay tests harm from that intervention; it cannot show that faster serving would rescue an existing loss |
| Can units recover their cooperation? | Fixed jobs, early reserve commitment and replacement above one executor; a timed release if replacement helps | More units or a reserve order alone do not demonstrate recovery |

Natural latency is the primary deployment condition, including retries and provider
behavior. A model comparison measures the model and its serving system together.
Changing a helper changes the controller being evaluated: disclose who chooses targets,
routes, withdrawals and replacement units. Model, prompt, executor and timing changes
need separate comparisons before attributing an improvement to one of them.

## From a candidate to a scored card

The [card definition and gates](tactic-cards.md#a-card) are the current proposal; older
calibration plans below are history, not competing admission rules.

1. **Define the choice.** Name the tactic, winning condition, credible alternative and
   simplest shortcut. Pin setup, public mechanics, automation, scorer and timing. Reserve
   a supported map or roster variation before tuning; reserve another group for selecting
   revisions if needed. New launches of a tuned setup are not held-out tasks.
2. **Screen cheaply.** Proposed default: three fresh launches per relevant foil and
   witness, stopping a candidate early on a shortcut win or unusable setup. These are
   feasibility observations, not reliable rates. Inspect default skirmish/fire-at-will,
   terrain, commander morale and whether a witness actually wins the whole battle.
3. **Confirm only useful candidates.** Freeze the rule, counts and stopping conditions;
   use new launches. A proposed gate is each foil 0/14 and witness at least 10/14,
   with its signature on reviewed wins, at a declared age and cadence. This is evidence
   of a useful separation, not guaranteed winnability: 10/14 has a 95% Wilson interval
   of about 45–88%; 0/14 gives a one-sided 95% upper bound of 0.19 for that foil.
   Stop on a foil win or the witness's fifth loss and retain the failed cohort.
   Repair a broken foil before counting it; a revised card needs a new version and
   confirmation cohort. Do not keep retrying an unchanged gate to obtain a pass.
   The chariot's frozen 0/10 and 4/5 historical rule stays attached to c1.
4. **Compare controllers.** Choose one primary contrast and the smallest useful win-rate
   gain before setting the sample budget. Ten launches is a screen, not a general
   ranking rule. Rotate order within matched launches, keep rematches grouped, retain
   every start and show uncertainty. If the affordable sample cannot answer the question,
   call it exploratory rather than running until a favorable result appears.
5. **Test the reserved variation and independent rerun.** Freeze the controller first.
   Report each variation separately; a changed roster may also change difficulty.
   If results guide another revision, that variation is development from then on.

The first reusable evaluation path needs a frozen card with reference results, the checks below,
and another user's documented
[recount and rerun](benchmark-run.md#independent-rerun-acceptance-proposal). An initial suite repeats
that path for a small set of distinct cards. Expand with distinct
cards, not a quota or a full model-by-mode grid before the cards are useful. A suite score
requires a fixed card list and coverage; missing cells are not zeroes and cherry-picked
subsets are not comparable. Keep per-card results primary, with cost and failures beside
them. A winning alternative remains a win; it challenges the card's interpretation.

Before a comparison, write one short plan: card/controller/scorer revisions, primary
contrast, useful effect size, launch count and order, exclusions/replacements, stopping
rule, reserved variations, and API/game-time ceilings. Include failed candidate versions
in the record. Later reference runs can detect drift but do not enlarge a frozen
confirmation cohort. If a cap stops an in-battle trial, the remaining complete cases
cannot support the planned ranking without addressing that missing outcome.

## Route to the first release

Proceed by the evidence each step produces, with no broad model grid or new architecture
as a prerequisite. The detailed card gates above supply the counts and stopping rules;
those proposed numbers still need agreement.

| Step | Concrete deliverable | What it unlocks |
|---|---|---|
| 1. Settle the contract | Agree the failure/denominator rule and correctness checks; select the next chariot witness/signature version without rewriting c1 | A well-defined next evaluation, not yet a verified card |
| 2. Close one reusable path | Freeze one card/controller/scorer package, pass its agreed checks, recount accessible evidence and complete the outside rerun | A usable single-card evaluation with explicit limits |
| 3. Earn breadth | Screen the [starting set](tactic-cards.md#the-starting-set-proposal-2026-10-21) (floors, then witnesses) for decisions distinct from the chariot; test the line battle's fixed jobs/early commitment/replacement comparison before calling it recovery | A justified small card list; neither Empire nor team framing grants admission |
| 4. Demonstrate usefulness | Freeze that list and one primary contrast, run the bounded confirmation/comparison and reserved variations, report uncertainty, failures, timing and cost | Reference results supporting a specific conclusion, or a clearly inconclusive study |
| 5. Release, then assess contribution | Package commands, versions, controller dependencies, reference evidence and rerun records; for a research claim, also complete the closest-work comparison below | A reusable suite; any further research claim is only as broad as the study supports |

Breadth screening may proceed alongside closing the first path; it need not wait for
another chariot model round. Before each candidate's next run, record the unresolved
question and the result that would retain, relabel or drop it, plus a time/spend cap.
If the cap expires without a useful separation, defer it. Another revision needs a named
failure and a new bounded plan, rather than indefinite calibration.

The immediate unresolved decisions are the chariot rule/version, the proposed checks
and failure rule, and which distinct Empire card earns confirmation. Exact suite
membership, a useful effect size and affordable launch count follow from those screens;
they are not settled by this scope review. The
[state page](../state.md#total-war-warhammer-iii) holds the current next actions.

## Correctness checks to agree

A passing reader or simulation test cannot establish that a tactic worked in the game.
Use requirements and independently inspected state as references, not the scorer's own
output. Reuse the agreed setup/component checks in AGENTS.md; the remaining checks below
still need owner agreement and later execution. No new test infrastructure is required
by this documentation change.

| Claim | Repeatable check and independent reference | Plausible wrong behavior it must catch |
|---|---|---|
| The declared battle starts | Reuse the agreed army/settings check on fresh launches; check map identity in the lobby and terrain/start evidence in battle. A rematch comparison is a proposed extension, not covered by that army check | Correct types at wrong ranks, inherited settings or changed resources; no independent battle map-key readback exists |
| The controller has only its declared information | Compare delivered inputs with an allowlist; alter only hidden scoring fields and check public inputs stay identical; separately inspect visibility in game | Scoring totals in prompts, hidden-enemy fields, extra script-only information |
| An order can cause the intended behavior | In an unpaused live check, follow a known move/withdrawal/cast from basis through acknowledgement to independently observed movement/contact/effect | Accepted but blocked movement, a queued order mistaken for immediate execution |
| The outcome and denominator are correct | Hand-classify engine win/loss/draw, timer win, retried and terminal failure, constructor failure, failure while acknowledging a terminal observation, cleanup failure, setup failure and operator stop; compare card/report output against the phase rule below | Timer survival counted as contact victory, a failed decision counted as terminal loss, a recorded ending overwritten or a broken controller disappearing |
| A signature means what it says | Label positive, negative and ambiguous replay/trace examples against a written behavior rule; check the reader and a deliberately wrong reading | A harmless move counted as withdrawal, automatic re-engagement credited to the model, missing replay counted as absence |
| Another user can reproduce the evaluation | Follow the runbook with one frozen outside controller; rebuild counts from raw files and repeat a declared launch | Undocumented manual steps, a missing ledger, silently pooled builds/prompts or duplicate rematches |

Existing commands check the chariot's component rules and reproduce the recorded c1 verdict:

```bash
uv run --locked pytest -ra tests/twwarhammer3/test_wh3_cards.py
uv run --locked python -m twwarhammer3 card chariot runs/twwarhammer3/calibration/c1
```

They do not satisfy the live-effect or independent-rerun rows. Keep unknown
signature evidence unknown; do not discard an otherwise scored battle because its replay
is missing. A patch or provider change creates a new declared condition, not silent
evidence that the old rates still apply.

For the information row, existing component tests cover the offline half: the play loop
strips `evaluation`, `final` and `setup` before any policy call
(`test_wh3_play.py::test_delayed_policy_gets_old_public_state_but_results_use_current_evaluation`),
the Lua side keeps hidden enemies out of the public state and never queries their
positions for stills (`test_wh3_battle_lua.py::test_hidden_arrivals_and_deaths_do_not_update_public_enemy_state`,
`::test_lua_presentation_never_queries_hidden_enemy_positions_or_policy_memory`), and every
scripted witness ignores hidden enemies
(`test_wh3_calibration.py::test_small_diagnostics_do_not_use_hidden_enemies_or_order_routers`).
They are not an agreed boundary check, and nothing checks visibility in game. Check row to
add on the owner's yes (proposed): "WH3 information boundary, component half: `uv run
--locked pytest -ra` on those four tests; in-game visibility unchecked."

For the next chariot signature, independently label a small set of real cases before
looking at the reader's verdict: a move followed by observed separation and renewed
contact; a move countermanded while still in melee; separation without a move order;
and a gap in the recording. Keep attempts, observed withdrawal and renewed contact
distinct. A melee flag alone cannot prove which enemy was hit or that a charge bonus
applied. Review disagreements against the evidence, then freeze examples for the reader
check. Deliberately misleading trace edits test the reader, not live game effects.
This proposed check does not redefine cycles v1.

Labelled examples (2026-10-21, `runs/twwarhammer3/away-20261021/chariot-labels/`, proposed):
agents picked 21 edge-case engagements from 20 chariot battles, and pairs of other agents
labelled them without the reader: 16 against a first rule whose gaps they exposed (`v1/`),
then all 21 against rule v2 (`rule.md`). Each pair agreed on every label. On v2's labels
cycles v1 was right on 13 and the wrong reading "every engagement but the last" on 10. v1
ignored all 3 engine exits but counted 5 attempts that never got clear (a pull-out order
while the chariot stayed in melee, or one it countermanded) and missed 3 pull-outs ordered
up to 5 s before contact, which v2 counts and v1's window does not. Hand-picked cases give
no rate. No chariot replay has a recording gap of 3 s or more (0 of 123; the largest is
1.2 s); in an edited copy, 5 s cut from one engagement split it and raised cycles v1 from 5
to 6, so a gap inside melee reads as an exit and nothing flags it (`gap-edit/`). v2's choices (the 5 s window, 60 m
of separation) need the owner's view before the examples are frozen. All agents are one
model family: this checks the written rule, not independent judgment.

**Proposed failure rule for the next evaluator.** Count a controller that fails to
construct on its assigned attempt as unsuccessful, separately from proven game/setup
failure. During a valid battle, terminal controller failure is a forfeit; a retried
decision consumes time. Once an engine ending is observed, preserve that result and
record later acknowledgement or cleanup errors as reliability failures. List unstarted
planned trials separately, never as losses. Agree and test this rule before adoption.
Current code differs: construction precedes recording a battle id, so the card reader
excludes that failure; acknowledgement or `close()` can fail before the final status is
stored or preserved. Historical c1 scoring stays fixed.

How often (recount 2026-10-21, `runs/twwarhammer3/away-20261021/failures.txt`): of 595
recorded episodes, none failed at construction, at the acknowledgement of an ending or at
`close()`, so the rule rescores no recorded episode. All 9 policy failures were in battle,
so the proposed rule scores them as today's reader does: it forfeits 8 and excludes an
HTTP 402 credit stop at b30 as an operator stop. The register still lists that stop and a
harness-probe `KeyError` at b2 as policy failures; correcting those rows stays a separate
decision. 18 jobs ended before any episode (10 setup failures), none of them in the c1
cohort. The local branch `wh3-keep-engine-ending` stores the engine's ending before the
acknowledgement and keeps it through a `close()` failure, without changing which result
counts.

Check row to add to AGENTS.md on the owner's yes (proposed): "WH3 engine ending kept after
a late controller failure: `uv run --locked pytest -ra
tests/twwarhammer3/test_wh3_play.py::test_a_controller_failure_after_the_ending_keeps_the_engine_result`
(fails on the parent of `b527584`); no game execution claim." The recount behind the rule
reruns with `uv run --locked python runs/twwarhammer3/away-20261021/failures.py`.

## Research that changes the design

Selective primary-source review, 2026-10-20; WH3 uses here are proposals:

| Source | Useful lesson for this plan | Limit |
|---|---|---|
| [Realtime-Bench](https://arxiv.org/html/2610.22155v2), October 2026 | Distinguish deployment time from assigned timing conditions and consistency from one successful run | Its paused/token clocks are not WH3 conditions; keep WH3 live at 1x |
| [The World Won't Wait / TORSI](https://arxiv.org/html/2610.20665), October 2026 | Separate feedback, revision selection and final evaluation; account for actions continuing during inference | Different paper from Realtime-Bench; its paused practice and saved states are not available here |
| [GameWorld](https://arxiv.org/html/2604.07429), April 2026 | Inspect state-based outcome rules and freeze the whole interface/budget before rerunning | Its live variant already studies inference during play; serialized state alone does not validate a WH3 tactic signature |
| [SMACv2](https://arxiv.org/abs/2212.07489) | Try a fixed schedule before claiming feedback or recovery is required | Randomized teams in StarCraft do not establish useful or reproducible WH3 variants |
| [LatencySensitiveBench](https://arxiv.org/html/2505.19481v1) | Faster calls can stop helping once action execution is the bottleneck | Its Street Fighter timing threshold is not a WH3 threshold |
| [Gaia2, §B.2.4](https://arxiv.org/html/2602.11964v1), February 2026 | Check the scorer with both known-validity perturbations and labeled real agent trajectories | Its 450-trajectory verifier study is not validation of WH3 signatures; uncertain labels and independent review here are our proposals |
| [Statistical Precipice](https://arxiv.org/html/2108.13264v4), NeurIPS 2021 | Match uncertainty to the comparison: repeated runs on fixed tasks differ from sampling more tasks | Neither bootstrap nor an aggregate score automatically makes a small, selected WH3 suite representative |

WH3's opportunity is the combination of inspectable tactics, morale, persistent orders
and units whose support can fail during inference. Live clocks and hierarchical control
already have prior work. [Robot-team research](robot-team-research.md) develops the
recovery comparisons and transfer limits; physical-robot benefit remains untested.

**Possible coordination research contribution:** a reproducible set of tactical cases
in which a controller must maintain or restore support between units while its observations
age, with evidence separating the chosen plan, the issued orders and the observed effects. For example,
"the reserve was ordered forward" differs from "it arrived before the gun was caught."
This could support a useful diagnosis that a battle win rate alone misses. It is a
hypothesis for the team branch, not an established novelty claim or a requirement for
single-unit cards such as the chariot.

Before a research release, compare the actual retained tasks with the closest work on
five concrete points: what continues during inference; what decisions the built-in
executor supplies; whether support can fail and be restored; what action/effect evidence
is available; and what an outside user can reproduce. Include Realtime-Bench/GameWorld
for live timing, SMACv2 for coordination and shortcut tests, and
[DPT-Agent](https://arxiv.org/abs/2502.11882) for asynchronous hierarchical game control.
Record overlaps and unanswered questions as well as differences, and refresh the search
at release. A different game or combination of familiar mechanics alone does not prove
novelty. If fixed jobs or a timed reserve solve the line battle, narrow its recovery
claim; the other tactic cards can still have value.

## Terms

| Term | Meaning |
|---|---|
| scenario | An entry in `configs/twwarhammer3/scenarios.json`; `expect` declares its benchmark setup, not admission or verification |
| candidate card | A proposed tactical question with a scenario, witness, wrong plays and an evidence rule; not yet admitted |
| scored card | A versioned card that passed its frozen admission rule; verification and release readiness are separate checks |
| variant | A scenario with one declared change (modifier, map, role) as its own entry; `split` is `development` or `held_out` |
| instance | The battle one launch builds; rematches aim to restart it and their starts are compared |
| trial | One controller playing an instance once (an episode) |
| track | A named observation contract, action contract and timing policy |
| controller | Code that turns observations into orders; its `card` records kind, source and disclosure |

## Observation and action contract

The track is `obs-v4+terrain/act-v2/live-1x` (`play.TRACK`); a trial with added age D
appends `+age-<D ms>ms`. A track versions the information and actions supplied by the
environment and its timing rules. Controller memory or prompt changes are controller
versions; scoring changes are evaluator versions. They need not create new tracks.
Results from different conditions can appear in the same report, labelled separately;
they are never pooled across tracks. History: `obs-v1/act-v1`
(b1), `obs-v1+terrain` (b2, terrain grid), `obs-v2+terrain` (b3, enemy roster boundary
fix), `obs-v3+terrain/act-v2` (b8, morale and flight), `obs-v4+terrain/act-v2`
(b12, optional public custom objectives). The code is the reference:
- `engine/mailbox.py` module docstring: the observation, the acknowledgement and every
  bridge file;
- `protocol.py`: the order types and `validate_orders`;
- `mod/script/battle/mod/twwarhammer3_battle.lua`: what is published, and the engine
  rejection codes;
- [integration.md](integration.md): engine facts behind them.

**Label: structured state; enemy units filtered by the engine's visibility tests;
numerically exact; not player-equivalent.** Enemy units appear only while
`is_visible_to_alliance` holds and `is_hidden` does not. The enemy roster the lobby showed
is public; later arrivals join it only on sight, and a death is reported only if the unit
is visible then. `evaluation`, `final` and `setup` hold hidden information, and the harness
strips them before a controller sees a snapshot.

Known limits:
- positions, men and health are exact, finer than a player reads them;
- enemy units' targets are not observed;
- a friendly unit's `target` can name an enemy that is out of sight, and an attack on an
  enemy that died out of sight is answered `target_dead`, not `target_not_visible`;
- `class` comes from the land-unit class and missile range, not the unit's role (flying
  non-lords read `flying`);
- `is_hidden` is unverified, and so is whether the filter matches what a player sees;
- the terrain grid samples 16 m squares every 32 m at deployment; it is not a path planner.

Actions: `move`, `attack`, `halt`, `behaviour`, `ability` and `flight` per unit; the unit
`"army"` casts army abilities and, paid with supplies, `build`s and `reinforce`s. The
game still decides pathfinding, formation, melee responses, fire at will and skirmish,
retargeting, morale and spell effects. The harness has no tactical helpers; the `skills`
executor belongs to the `skills` and `commander` controllers.

Failures are never repaired. A batch that fails `validate_orders` against its basis
observation is sent as no orders; the trace records it and `acknowledge` receives the
reason (`validation_error`). The engine rejects single orders with a code in the
acknowledgement. Both count as invalid; the report splits them. An acknowledgement means
issued or queued, not executed. Never actions: session settings, the `restart` control,
menu steps and bridge files.

## Timing and latency

`live-1x` is the only timing policy. The battle runs unpaused at 1x; `require_realtime`
refuses any other session and play refuses an observation that says otherwise.
- The mod ticks on a 250 ms model-time callback, which fires every 300 ms because the
  engine clock moves in 100 ms steps. It publishes every `observe_ms` (1000, so every
  1.2 s) and at the tick that applies each request, empty ones included.
- The harness reads `observation.json` every 100 ms of wall time; the mod reads
  `orders.json` every 200 ms and applies a request at its next tick. The floor is one
  tick: orders apply 0.3 s (sometimes 0.6 s) after the state a fast controller saw.
- One request is in flight; the next decision starts on the observation that carries its
  acknowledgement. Units keep their orders and the game's behaviour meanwhile, and a
  reply based on an old snapshot is applied as it is, with its basis recorded.

Recorded per decision: basis `seq` and `time_ms`, decision time, `applied_ms`, `delay_ms`
(information age when orders are issued/queued, battle clock), `think_s` and `roundtrip_s` (wall,
system clock). Model calls add wall seconds, provider processing time
(`openai-processing-ms`) and the returned model name; the commander adds `plan_age_s`.
Each episode records its battle/wall clock ratio. Network conditions are measured, not
controlled; rotating controllers within a launch spreads their variance.

**Added-age arms.** `--delay-seconds 0,6,10` crosses every controller with each age. The
controller decides on the newest buffered public snapshot at least D battle seconds old,
which stays its basis, so `delay_ms` remains the true age. The first D seconds fill the
buffer without decisions. D is a minimum: a blocking call leaves gaps in the buffer, so
the text and JSON reports give the actual snapshot age at decision beside the order
age. D = 0 is the natural latency, not zero latency. Arms are never pooled with each
other.

These arms change sensing age, not just inference duration. `--interval-ms` changes the
wait after acknowledgement; it is not an exact decision period. For a timing comparison,
change one of these at a time and report achieved age and gaps, including retries and
unfinished calls. Adding a wait to a fresh reply, or delaying only a planner above a
fresh-state executor, needs a different mechanism. Neither is implemented by the age flag.
The buffer also delays the first order: the present contrast includes the opening.
Isolating reactions after contact would need a shared opening and a declared activation
point, a proposed capability. Do not select battles by their observed latency to claim
causation: difficult states, retries and long replies can cause both delay and losses.

## Scenarios

A scenario is an entry in `configs/twwarhammer3/scenarios.json`; the `setup.py` module
docstring lists every field and the code that reads it. Manifests record the resolved
entry (after `base` inheritance), and the job's source fingerprint versions the file.

An entry with `expect` is a declared benchmark scenario; that alone establishes neither
card admission nor verification. `validate_declaration` requires a pinned map,
pinned factions and explicit rosters and every required `expect` key. Timed modes need a
finite timer (1200, 2400 or 3600 s) and an episode cap at least 120 s above it; native
timerless survival/domination require `time_limit_s: null` and `timer_enabled: false`.
Declared reinforcement pools must be explicit. All declarations refuse `--attach`. A declaration
error or a realism preference that differs from `expect.realism` stops play before the
job directory exists. Setup then checks, and any mismatch stops the job before a trial is
scored:
- the lobby: every menu step found its component, the selected map key, and read-backs of
  battle type, difficulty, unit scale, realism, funds (and amount), timer and AI stats
  modifier. Since b42 the steps apply these declared settings, difficulty before the
  explicit AI modifier; the pre-launch realism preference check still applies;
- the first battle observation: unit scale, realism, player role, every army's AI
  modifier, both rosters and experience ranks as multisets, both factions and the terrain grid.

The start fingerprint (positions, bearings, strength, ammunition, barriers, flight,
ability loadouts, magic, supplies, tickets) of every rematch is compared with the job's
first episode. It is flagged above 1 m or 10°, or on any strength, loadout or resource
change. Flags are reported, not enforced, because the snapshot depends on when the
wall-clock autostart fires.

Rules:
- **Always pin the map**: the lobby keeps the last started one.
- **Freeze random draws before use**: copy the rosters, pin each faction, record
  substitutions (`frozen_from`, `substitutions`).
- **Held-out means variants, not launches.** More launches of a tuned scenario are more
  development instances. Held-out entries (`-heldout-wastes`, another map) stay out of
  tuning.
- **Family measures use declared unit keys** (`protected`), never the observed `class`.

Declared families: ranged protection (`dwf-sla-taurox`, `dwf-sla-herald`), cavalry
against anti-large (`brt-cavalry-emp-pikes`, `-pegasus` and the attacking `-assault`) and
a caster-led force (`tze-caster-skv-screen` and the attacking `-assault`). All but
`dwf-sla-taurox` have a `-hard` variant at modifier 1.1 and a `-heldout-wastes` map. None
passed the former admission rule. Two Skaven swarm prototypes (`skv-swarm-dwf-line`,
`dwf-line-skv-swarm`) were screened on 2026-10-15; see [Scenario design](#scenario-design).

### Admission

The 30-70% reference win-rate gate and paired-margin admission test were retired by the
owner's 2026-10-15 direction. G1 and C1 remain development evidence. Difficulty is not
adjusted automatically to a reference model's win rate.

The current [card gates](#from-a-candidate-to-a-scored-card) supersede the older general
calibration proposals. An all-losing scenario can remain exploratory evidence when
controllers make different progress, but a scored tactic card needs a demonstrated
winning controller under the declared conditions. One win shows possibility, not reliable
winnability. Repeated witness wins, losing foils and reviewed tactic evidence answer
different questions. Existing labels such as `prototype_not_admitted` are legacy metadata.

## Scenario design

Prefer distinct decisions over different rosters. The owner's current direction is
mostly small Empire battles, with other factions for a specific challenge and a few
larger coordination problems. The earlier 6–8-family range was a planning guide, not a
quota or a settled suite. The [starting set](tactic-cards.md#the-starting-set-proposal-2026-10-21)
and [Empire evidence](empire.md#results) decide what to inspect next.

Candidates are questions, not admitted tasks or advice silently added to prompts.
Before a screen, name the public information needed, two credible plays, simplest
shortcut, observable effect and nearest existing card. Reject redundancy: a difficulty
step is usually a variant, and 20 v 20 changes combat balance, pathing and order volume
as well as context length. Reserve supported map or roster variations before tuning;
compare controllers within each variation rather than attributing a stronger army's wins
to generalization. Use the [card gates](#from-a-candidate-to-a-scored-card).

Keep broader questions available without making them release requirements: territorial
concession and reserve commitment in siege defence; reinforcement budgeting in survival;
distributed control in Domination. Their native objectives need declared success rules.
The old Conquest pilot had one central point, so it did not test distributed control;
the survival screen did not establish scarce supplies. Custom evacuation remains deferred
after a placement failure. Those observations do not establish good cards in those modes.

Earlier family audits, rosters and screening tables are history at
`git show e75cba5:docs/twwarhammer3/benchmark.md`, with runs in the
[b12 log](log.md#2026-10-16-harness-b12-and-distinct-scenario-families) and later entries.
Their retain/demote recommendations do not define today's suite. Check content availability
on the recipient's installation; a visible lobby card is not proof it can be recruited.

## Outcomes, measures and comparison

Trial statuses (`battle/play.py`):
- `won`, `lost`, `draw`: the engine's result, the only gameplay outcomes. `ended_by` is
  `time_limit` when the countdown expired (inferred from the last ticked deadline; see
  [integration.md](integration.md)); the report shows `time_limit` and keeps the engine
  result, so a defender's timeout win is not hidden.
- `truncated` (episode wall cap), `policy_failure` (terminal controller, construction or
  close failure), `budget_exhausted` (the WH3 ledger cap),
  `infrastructure_failure`, `unsupported_or_invalid` (a protocol or battle setup check
  failure) and `interrupted` (operator stop).

Every started trial is written to `result.json`, the manifest and the register. Any other
ending than an engine result stops the job; unplayed controllers stay unpaired. Show
planned, started and scored counts per arm with each missing partner's reason. Do not
discard a failure to balance pairs. Complete-pair comparisons are conditional on both
controllers finishing, which can select easier instances. If this prevents the planned
comparison, stop it or freeze a new cohort with one controller per launch, interleaved
across time; do not repeatedly replace only the incomplete pairs.

`battle/report.py` computes, per evidence group (same resolved scenario, source revision,
game build, track, recorder and imagery settings, observe/tick/interval, model and
effort; never pooled):
- outcomes per controller and added age, with valid trials (engine results) over started
  ones and the failures listed;
- the non-timer win rate (non-timer wins over all valid trials) with a 95% Wilson
  interval, withheld when a controller has repeats within one launch;
- the active-strength margin: own men neither routing nor shattered over own starting
  men, minus the same for the enemy, from hidden totals. Reinforcements and summons join
  the denominator; unit value is not weighted (the register's `own_left` and
  `enemy_left` count routing men as alive);
- paired differences: for each pair of controllers, the margin difference per launch
  (rematch repeats averaged within it), a Student-t 95% interval over launches, an
  approximate 80%-power detectable difference, the unpaired launches, and a sensitivity
  result without launches whose starts were flagged;
- per trial: order age at application (non-empty batches), snapshot age at decision, plan
  age, model call seconds and provider processing time, returned model names, decisions
  per battle second, rejections by validation or engine code, protected-unit survival,
  objective shares held (integrated on engine ticks), supplies left, accepted builds and
  reinforcements by type, tokens, USD, wall seconds and clock ratio;
- per controller, the median of its trials' median order ages in the collector; the HTML
  pools order batches (adopted plans for commander) to show its typical delay;
- throughput: valid trials per job wall hour, counting setup, resets and failed jobs.

The text and JSON reports end with the limitations stated in `report.collect`. The HTML
page shows outcomes, the typical order delay and cost per battle, and leaves the margin,
paired differences and limitations to those files ([reports.md](reports.md)).

The report's engine-completed-trial rate is a diagnostic. The tactic-card score includes
terminal controller failures as losses and is the primary rate for cards; show exclusions
and failed decisions beside it ([score](tactic-cards.md#score)). These denominators can
give different numbers from the same jobs. Native-objective cards must declare their
success rule before use; do not require enemy destruction for a point-capture objective.

Reproducibility means declared conditions are checked and differences are disclosed.
Starting fingerprints are compared, not proof of identical internal state. Records should
permit an independent recount; that still needs the rerun check above. Identical
trajectories, instances across launches, seeded engine randomness and branchable battle
replay are not established capabilities.

## Evidence behind the design

Measured on 2026-10-13/14 from the register and runs; the full analysis is Part 1 of
this page before its rewrite (`git show d606d39:docs/twwarhammer3/benchmark.md`):
- **A rematch restarts the same instance** (30 of 32 jobs matched to 0.1 m and 1°; the
  two exceptions ended deployment 100 ms later). **A new launch does not** (up to 5 m and
  48° apart over 14 `kho5-dwf5` launches). Launches are the sampling unit.
- **The engine replays a battle when orders land on the same ticks.** Three of six
  `skills-v1.2-kho` episodes were identical to 530 s; one batch applied a tick later
  diverged the rest. Repeats of a controller on one instance are correlated.
- **`kho5-dwf5` changed maps**: it named none and the lobby kept a random draw's map.
- **WSL's monotonic clock ran 0-11% slow**, so wall durations use the system clock.
- **The raw margin contradicted the outcome** in 16 of 108 battles (routing men counted
  as alive), hence the active margin.
- **Throughput**: about 8 episodes an hour; a one-episode job took a median 409 s for a
  317 s battle.
- **Information age**: `llm` v14 median 6.0 s (90th percentile 9.2 s); scripted controllers
  one tick; commander plans 6.0 s old when adopted. Pausing during inference (`llm` v4,
  3 battles per arm) showed no effect, but could only have detected a large one.
- **The setup probe** (`runs/twwarhammer3/benchmark-probe-20261014`, source `f2c8463`,
  `dwf-sla-taurox`) recruited 24 cards by id and read the lobby and battle settings back.
  `hold` lost at 298 s; its 965 empty requests applied after 0.3 s (954) or 0.6 s (11).
  Its protected units met melee 8.4, 13.2, 24.0, 46.2 and 47.4 s after an enemy came
  within 100 m: one reaction window shorter than a slow model's age plus period.
- **The AI stats modifier** changed only the AI units' stats in the b2 and b8 startup
  snapshots. Lobby options, modifier getters and terrain sampling are in
  [integration.md](integration.md).

## Implementation plan

The following dated plans explain earlier calibration. The current
[release route](#route-to-the-first-release) uses the
[card gates](#from-a-candidate-to-a-scored-card), [Empire candidates](empire.md) and
[robot-team feasibility check](robot-team-plan.md#a-small-sequence-of-experiments).
Their counts and historical admission statements do not override a frozen card rule.

### Current proposal: calibrate before a broad model comparison

Historical proposal, 2026-10-16; heading retained for existing links. The detailed
matrix estimates, ladders and tranche instructions are in git:
`git show f5af096:docs/twwarhammer3/benchmark.md`. The current
[sequence](#from-a-candidate-to-a-scored-card) replaces those operating instructions.

Owner goals that still guide selection:
- **Difficulty:** hard but demonstrably winnable, with meaningful choices. The earlier
  assistant rule of keeping the hardest step with one win established possibility only;
  reliable winnability needs repeated evidence. Do not harden a card until every model loses.
- **Scenario mix:** mostly small battles testing one or two distinct decisions, plus a
  few larger coordination/scale problems. Different factions or difficulty steps do not
  automatically add coverage.
- **Model coverage:** eventually compare the supported reasoning modes of each selected
  model on the retained suite. Recheck real provider modes before freezing a round.
  Schema acceptance does not establish that effort levels behave differently.
- **Budget:** choose repeats per question; do not begin with a broad paid matrix.
  Declare API and game-time ceilings, permit long losing battles and retain failures.
  Old cost estimates and ledger balances are historical, not current allowances.

The October 16 sequence was: inspect saved battles, fix essential feedback, draft a
small ladder, try free references, run a small strong-model screen, then freeze a suite.
It did not settle the core from M1. Custom evacuation stayed deferred; the one-point
Conquest pilot did not test its intended distributed-control question.
OpenRouter support and feedback changes are recorded in the
[b13 log](log.md#2026-10-16-harness-b13-shared-openrouter-transport) and
[magic-feedback review](log.md#2026-10-16-first-openrouter-battle-and-shared-magic-feedback).

### Calibration cards, 2026-10-16

Historical review of 54 saved M1a–d battles. The extraction is
`runs/twwarhammer3/calibration/calibration-audit-20261016.py` with its JSON alongside;
the [M1 review](log.md#2026-10-16-matched-round-m1-on-the-retained-core-plan) holds the
outcomes and turning points. These were hypotheses, not admitted tactic cards.

| Family | Question the review left open |
|---|---|
| Siege defence | Do reserve commitment and useful firing positions beat a simple central fallback? Some model wins used little blunderbuss fire, so firing that weapon was not necessary |
| Swarm command | Must screen and damage units arrive together, or does one simple coordinated advance suffice? The first scripts did not establish a winning reference |
| Caster assault | Does spell-window choice matter beyond repeatable cast/retreat behavior? Accepted casts and spent magic do not prove spell value |
| Cavalry assault | Is the safe flank reproducible through the public interface? Mixed outcomes from matching starts did not isolate route execution from timing |
| Defensive swarm | Can an executable defence improve on holding? All-losing model screens did not settle usefulness |
| Kislev survival | Is spending scarce, or is this spawn defence? Abundant remaining supplies argued against the original budgeting claim |

The first free tranche lost all three battles: central siege fallback at 614 s, swarm
speed estimate at 316 s and screen-following at 440 s
([live review](log.md#2026-10-16-free-siegeswarm-calibration-checks)). It exposed execution
limits rather than an easy solution; those losses did not establish frontier difficulty.
The audit also distinguished no spawn zone from an unaffordable purchase and unjudged
affordability. Missing values are not evidence of lost territory, ammunition spent is
not damage, and scoring-only totals are never diagnostic-policy inputs.

### Small focused candidates (draft, 2026-10-16 evening)

A first draft of the owner's [scenario mix](#current-proposal-calibrate-before-a-broad-model-comparison),
from the game database and earlier lobby card lists. These are definitions for the owner to
review, not admitted scenarios. Live checks began on 2026-10-17: S1's lordless setup
and low funds passed, both frontal floors lost, and its first flanking diagnostic won
with fresh observations but lost with 5 s added age. The corrected delayed S1 attempt
also lost; S2's floor won and S4's hold floor lost. Work stopped at the owner's request
after these seven battles ([checkpoint](log.md#2026-10-17-harness-b17-small-scenario-checkpoint-work-stopped)).
The full draft, with rosters, database facts
kept apart from hypotheses and the ladders, is `calibration/micro-scenarios-draft-20261016.md`.
Shared settings: classic battle, very hard AI, modifier 1.0, unit scale 0.75, 1200 s
timer, funds equal to the larger army's cost. Only base-game cards seen in earlier lobbies
are used (no DLC assumed).

| Id | Skill tested | Player | Enemy | Plausibility (database) and main risk |
|---|---|---|---|---|
| S1 | Feint and flank against braced anti-large (owner's example) | 2 Kislev Horse Raiders | 1 Empire Halberdiers | Riders 9.2 m/s, charge 40; halberds have charge defence and charge reflection vs large. Risk: the AI unit turns faster than any flank. Same skill as the cavalry family, so one of the two counts. |
| S2 | Ammunition as the clock (kiting) | 2 Kislev Horse Archers | 1 Dwarf Slayers | 140 m, 18 arrows a man; Slayers unbreakable, armour 0, 4.0 m/s. Arrows alone need about 21% to hit, so finishing charges matter. Risk: trivial or impossible by a small margin. |
| S3 | Crossfire, lines of fire | Spearmen with shields + 2 Handgunners | 2 Dwarf Warriors | Low-trajectory guns cannot fire over friends; dwarf shields 55%. Risk: shield arcs are game knowledge, not database facts. |
| S4 | Protect a fragile unit (player defends) | Helblaster + Halberdiers | 2 Mounted Yeomen + Men-at-arms | Helblaster 290 m, fires low, cannot run; riders cross its range in about 32 s. Risk: too much or too little firepower. |
| S5 | Spell window with scarce magic | Bright Wizard + Spearmen | 2 Swordsmen | Both damage spells also hit allies; about 12 magic at start. Overlaps the caster family. |
| S6 | Hammer and anvil, rout cascade | Swordsmen + Empire Knights | 3 Swordsmen | The `skills` executor's charge skill can serve as the check. Partly overlaps S1. |
| S7 | Terrain defence | 2 Longbeards (defending) | 4 Swordsmen | Weakest: the observation has blocked cells but no elevation; a hill test needs heights. Last or drop. |
| L1 | Small skills at scale, context length | Empire, 20 units | Greenskins, 20 units, 2400 s | Overlaps swarm command on order volume. |
| L2 | Three-way battle, two AI opponents | Kislev, 12 units | AI Greenskins and AI Dwarfs | Earlier five-unit free-for-alls show the AIs fight each other. Fallback: a three-point Domination. |

Prerequisites, each a $0 lobby or scripted check: armies without lords, custom funds
of 800-1,600, and how the AI behaves with one to three units. The S1 probe verified
lordless recruitment, 1,100 funds and a one-unit AI that held until contact. b16 also
corrects ordinary commanders being labelled as lords; S2's live roster confirms its
commander remains missile cavalry; S4 also verified its infantry commander and artillery.
Other small rosters still need their own checks. Winnability per candidate: a naive
scripted floor that should lose, then one
disclosed diagnostic encoding the hypothesised play at `delay_seconds` 0 and 5. A win at
5 s tests stale sensing (it does not reproduce a model's full decision cadence);
a floor win means the scenario is too easy and climbs. Suggested order: the lord/funds
probe, S1, S2 and S4, then S3, S5 and S6; S7 last. A second batch (S8-S11 declared,
S12-S13 defined only) covers focus fire, a lone monster, receiving cavalry and
counter-battery: [small-scenarios-2.md](small-scenarios-2.md).

### Small-scenario status after the overnight tranche (2026-10-17)

Superseded on 2026-10-18 by the tactic-card definition and its board in
[tactic-cards.md](tactic-cards.md#the-first-checks-night-of-2026-10-18); kept as the
record of S1-S11 before it.

One row per candidate. Floors are naive scripted controls that should lose. Diagnostics
are disclosed public-state plays, run at 0 and 5 s added observation age. Evidence and
delegated choices are in the
[overnight log entry](log.md#2026-10-17-overnight-tranche-harness-b18-b23). No
candidate is admitted. Statuses:
- "win shown": a diagnostic won (a scripted win; no model has won a small scenario).
- "too easy": a floor won.
- "no win yet": the floor and the diagnostic both lost.

| Id | Latest step | Floor | Diagnostic | Model battles | Status and next step |
|---|---|---|---|---|---|
| S1 feint and flank | `ksl-raiders-emp-halberds` | walk and run lost | FeintFlank won fresh, lost at 5 s (x2) | GLM-5.3 low 0/2: planned a two-flank charge, sent direct attacks | Win shown fresh only (0.3 s); both 5 s battles lost. Next: stronger models; `llm_rules` v21 draft states the attack route |
| S2 kiting | `brt-archers-dwf-slayers-decoy` | three earlier steps won; decoy lost | CrossKite lost x4 (terrain refusals; then a morale collapse at full strength) | none | No win yet. Set aside: engine skirmish mode automates the kiting. Range-aware CrossKite or drop |
| S3 lines of fire | `emp-handgunners-dwf-warriors-3` | 2-unit won; 3-unit lost | Crossfire lost x6; on b23 (E1) it ran as disclosed but the guns barely fired (314 and 0 rounds) | none | No win yet. Crossfire revised in b24 (guns shoot from where they stand, fixed posts). Next: a 0/5 s pair on b24 |
| S4 protect the gun | `emp-helblaster-brt-raiders` (step `-2`) | hold lost (both steps) | Bodyguard: original won 4/4 at 5 s, 1/4 fresh; step 2 lost x2 | GLM 0/1 plus one policy failure | Win shown on the original, but by the escort's melee; the gun always fell. The named skill is not yet tested |
| S5 spell window | `emp-wizard-emp-swordsmen` | ability probe and attack-nearest lost (at 3,000 funds; the probe casts only self abilities in melee) | b23 lost fresh, won at 5 s; b25 (cast hold) won fresh (440 s) and at 5 s (488 s) | none | Win shown at both ages. Next: a model screen |
| S6 hammer and anvil | `emp-knights-emp-swordsmen-2` | 3 Swordsmen lost; 2 Swordsmen won (b24) | HammerAnvil lost x4 at 3 Swordsmen | none | Too hard at three, too easy at two. Next: an intermediate step (e.g. three at a lower AI stats modifier) |
| S7 corner defence | `dwf-longbeards-emp-greatswords-2` | 4- and 6-Swordsmen steps won; 2 Greatswords + 2 Swordsmen lost (b24, 387 s) | CornerHold won fresh and at 5 s on the timer, without contact: both armies ended at 100%, the Longbeards hidden in a corner (b25) | none | Timer win without contact, not a demonstration. Next: a step where hiding to the timer cannot win, before any model screen |
| S8 focus vs regeneration | `dwf-thunderers-grn-trolls-2` | 3 Trolls lost; 2 Trolls won (b24, 214 s) | FocusFire lost x2 at 3 Trolls; no Troll died | none | Too hard at three, too easy at two. Next: an intermediate step |
| S9 monster target choice | `grn-giant-ksl-streltsi-trolls` | Giant alone lost; Giant + Trolls won (b24, 328 s) | MonsterTarget lost x2 with the Giant alone | none | Too easy with the Trolls. Next: Giant + Trolls against a second Streltsi unit, floor first |
| S10 receive the charge | `skv-spears-sla-hellstriders-3` | 2-rider and 3-rider won | none yet | none | Too easy: the AI charges braced spears head-on at any count tried. Set aside unless a different enemy (missile cavalry) changes its behaviour |
| S11 counter-battery | `dwf-cannon-grn-lobbers-1` | 2 Rock Lobbers lost; 1 won (b24, 469 s) | CounterBattery lost x2 at 2 Lobbers | none | Too hard at two, too easy at one. Next: an intermediate step |
| L1 / L2 | `emp-pitched-grn-20`, `ksl-ffa-grn-dwf-12` | L1 attack-nearest lost at 523 s; L2 refused by the lobby | n/a | none | L1 sets up. L2 needs a fourth side ("Free-For-All requires 4 teams") |

Across all of them, terrain defeated the first versions of the geometric diagnostics:
on the Taurox map, posts and waypoints often fell inside the central rock, and the
engine refused the moves. Since b23 every diagnostic move steps to open ground or holds.
Lobby prices for characters exceed their database costs, so character-led rosters
get funds headroom.

### Owner decisions and next tranche (2026-10-16 night)

The owner answered the three open questions. Item 3's exporter and exchange capture are
now implemented as [harness b14](traces.md). The owner resumed items 1 and 2 on
2026-10-17, then cleared the goal and requested a wrap-up after seven scripted battles.
Remaining checks and the cheap-reference ladder are pending, with no paid calls in
this tranche.

1. **Small scenarios: approved to try.** In order: a $0 lobby probe on S1 (both slots
   lordless, 1,100 custom funds, how the AI uses one unit); then for S1, S2 and S4 a naive
   scripted floor and one disclosed diagnostic of the hypothesised play at 0 and 5 s
   delay; then S3, S5 and S6; S7 last or dropped. A candidate that survives gets
   cheap-reference model battles and report notes. S1/S2/S4 declarations and their
   disclosed diagnostics are implemented as b15/b16. S3/S5/S6 remain later candidates.
2. **Ladder reference: a cheaper model for now.** Expensive models (gpt-6.1-sol, Astra,
   higher modes) return later. The cheap reference is GLM-5.3 / low through OpenRouter:
   $0.10-0.42 per battle, the only cheap model with a caster-anchor win, $48 left on its
   ledger. Step 5 Preview (lowest prices, unplayed) and Luna at higher modes ($0.04 per
   battle at low) are the alternatives, each worth one first battle. A cheap model's win
   shows a step is winnable. Its loss does not show the opposite, and its ladder will
   stop below the strongest models' limit. The expensive models later resume from the
   hardest step it won and climb further. Next steps on the ladder: siege with three added
   flankers, a new swarm factor (for example anti-large Slayers against the Doomwheel and
   Rat Ogres), caster with three cannons. GLM first needs a reference battle on each
   unchanged anchor, which it has only for the caster.
3. **Training data: write a trace exporter and store reasoning text.** The exporter is
   offline: one JSONL record per model decision with the system prompt, the exact user
   prompt, every raw reply attempt, the reasoning text when the provider returns it, the
   validated orders and the engine's per-order acknowledgements. Each record also carries
   the model, provider, effort, prompt version, source revision and scenario, plus the
   episode's outcome and measures, and the export comes with a data card. Reasoning text
   needs a small transport change before the next paid battles, so they carry it:
   OpenRouter can return the model's reasoning, and OpenAI returns at most a summary when
   asked. It is billed as reasoning tokens either way and never re-enters prompts.
   Prompt formats changed from v1 to v20, so exports are labelled and filterable by
   version. Provider terms (OpenAI's on training competing models) are checked before
   any use. Backing up `runs/` off this machine, recommended alongside, is still open.

Reasoning capture and the exporter are complete offline; the new capture request setting
has not had a paid API check. On resumption: a bounded GLM S1 screen (no more S1 bot
tuning), the prepared weaker S2 roster's floor/diagnostic checks, and S4's bodyguard
diagnostic. Review surviving candidates with GLM; then GLM siege/swarm reference
battles and the three named ladder steps. Expensive models and the all-modes matrix
remain later work. Scripted checks establish setup, executable plays and obvious
triviality; their losses do not establish that a scenario is impossible for a model.

## Earlier implementation sequence (2026-10-15)

The completed work and earlier decisions are recorded in the log:
[v17 / commander v4](log.md#2026-10-15-integrate-llm-v17-and-commander-v4),
[b11 shared measures and report](log.md#2026-10-15-harness-b11-common-measures-and-one-report),
[b12 scenario expansion](log.md#2026-10-16-harness-b12-and-distinct-scenario-families),
and [M1](log.md#2026-10-16-matched-round-m1-on-the-retained-core-plan).
The superseded implementation instructions remain in Git history; the active sequence
is the [calibration proposal](#implementation-plan). Measurement definitions are above;
report behavior is in [reports.md](reports.md).

## Calibration (stopped 2026-10-14)

Historical design, superseded by the implementation plan above. G1 proposed six launches
at each AI modifier (×1.0 and ×1.1), rotating Sol low `llm_rules`, walk-nearest and
run-nearest. Admission required Sol to win 2-4 of 6 before the timer and beat both
baselines on paired active margin with a 95% interval above zero. G2 would then rotate
0/6/10 s added ages on an admitted variant. The owner stopped G1 on 2026-10-14; it remains
partial, and G2 never ran. Outcomes and stop details are in the
[log](log.md#2026-10-14-partial-g1-and-owner-requested-stop).

Plans, state files, audits and runners under `runs/twwarhammer3/calibration/` remain
historical evidence; `scripts/wh3_queue.py` is the supported runner for future jobs.
The full former design and its estimates remain in git at `ae7ca31:docs/twwarhammer3/benchmark.md`.

## Calibration: options for the owner's discussion (2026-10-15)

Historical alternatives, adopted as C1 below and now superseded. They proposed engine
outcome as the primary measure, Sol as reference, adding Luna to the paired rotation,
and trying ×1.1 first. The options also proposed fixing fresh moves mislabelled as
stopped before running; that fix became v16. The original discussion remains at the
revision above; the [decision entry](log.md#2026-10-15-harness-b10-llm-v16-and-the-calibration-decisions)
records what was adopted.

## Calibration decided (2026-10-15)

Historical C1 design: six launches of `brt-cavalry-emp-assault-hard`, rotation seeds
2026101501-06, `llm` v16 on harness b10, added age 0, no stills. Every launch rotated
`llm_rules` on Sol low, `llm_rules@gpt-6-luna` low, run-nearest and walk-nearest.
The original rule admitted ×1.1 on Sol 2-4 wins with both baselines at zero, made it
harder on 5-6, and moved to ×1.0 on 0-1. It is no longer the next-run rule.

All six launches finished on 2026-10-15: Sol 1 of 6; Luna and both baselines 0 of 6,
all engine outcomes. The report is `runs/twwarhammer3/reports/c1-cavalry-ai11.html`.
[Launches 1-2](log.md#2026-10-15-calibration-c1-launches-1-and-2) include early trace
reviews; [launches 3-6](log.md#2026-10-15-calibration-c1-launches-3-to-6) complete the
register. The revised plan retains these trials as development evidence and does not
schedule an easier calibration block.

## Experiments the report should eventually present (definitions only)

These are definitions only; this tranche does not execute self-comparison series or
build a new experiment framework. Compare one model to itself with its exact model id,
effort, controller/prompt version, build, map, settings and non-treatment conditions fixed.
Use matched instances, rotate condition order, reset controller memory each episode and
retain all attempts, including infrastructure/policy failures. Record input/output/cached
tokens, response latency, observation age, cost, actions and objective progress.

| Axis | Change | Interpretation and controls |
|---|---|---|
| Army/control workload | Number of independently commanded units, with declared composition ratios | Also changes action volume, density, pathing, contact timing, combat balance and tokens. This is end-to-end scaling, not a pure context-length effect |
| Prompt-only neutral context | Additional non-tactical text, same battle/state/action space | Vary token count while holding facts and history fixed; record where text is inserted. Check that the text does not introduce advice or alter the task |
| Useful history | Relevant prior observations/actions at prescribed lengths | Tests memory value and interference; it changes information as well as length. Keep the history-selection rule fixed |
| Factual representation | Equivalent facts rendered compactly or verbosely | Test representation separately from adding new information; audit factual equivalence |
| Added observation age | Buffered observations at declared minimum ages | Already supported; distinct from slower generation or a longer prompt. Natural model latency remains measured, not an experimentally assigned dose |

Larger armies and longer prompts may be crossed later to separate their effects. First
screen feasibility and freeze the treatments; use objective measures appropriate to the
family, and do not infer reasoning limits solely from slower real-time play.

## Later

Built only when a result or the owner calls for it:
- **A visual track and robotics models** (owner direction, 2026-10-14): a game image with
  each observation for vision models and VLAs, as its own track. Today's stills are
  presentation only ([reports.md](reports.md)); the track needs per-decision capture,
  camera and timing rules, an adapter from robot actions to orders, and hardware cards.
- **Model against model, possibly in teams** (owner idea, 2026-10-14): the battle script
  drives both armies with per-side views (try first), or local multiplayer with one
  client per side (desync risk). Results become relative ratings.
- An equal-tempo `age-D/P` track (fixed application age and decision period) to separate
  reasoning from speed; per-controller USD caps; an `exec:` adapter for controllers not
  written in Python; a reduced observation track if player equivalence becomes a goal; a
  value-weighted margin; a reaction-window screen with a pass mark.
- Records not kept yet: each hybrid executor order's basis, when the mod read a request,
  and when an order's effect first showed.
- In-game checks still open: `teleport_to_location` starting arrangements, restarting an
  undecided battle (play never does: such an ending stops the job), whether a launch
  reseeds the engine, whether the visibility filter matches the player's view, and
  whether the HUD's balance-of-power bar (kept out of observations) is player information.
