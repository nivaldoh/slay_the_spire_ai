# WH3 log

Dated history of the Total War: WARHAMMER III track, newest first: each controller
version, benchmark harness revision and notable job, with what changed, the jobs, their
outcomes and costs, and the decisions taken. Status is in [state.md](../state.md); the
reference pages are listed in the [README](README.md#pages), whose [Terms](README.md#terms)
define the labels: `vN` an `llm`/`commander` version, `v1.N` the `skills` executor, `bN` a
benchmark harness revision, G1 and G2 the calibration stages.

- Jobs are `runs/twwarhammer3/battle/<job>/`. Bare `reports/`, `calibration/`,
  `capability-probes/` and `visual-probes/` paths are under `runs/twwarhammer3/`
  ([runs/README.md](../../runs/README.md)); code paths such as `battle/llm.py` are under
  `src/twwarhammer3/`. Each episode is a row of [results.csv](results.csv);
  `uv run python -m twwarhammer3 digest <job>[/episode-NNNN]` reads a job's evidence.
- Until the 2026-10-14 benchmark work the scenario is `kho5-dwf5` unless an entry says
  otherwise: a custom battle on "An Ogre's Folly", Khorne (player: Herald of Khorne, Chaos
  Warriors, Bloodletters, Marauder Horsemen with throwing axes, Skullcannon) against
  Dwarfs under the game AI (Lord, Dwarf Warriors, Longbeards, Quarrellers, Grudge
  Thrower), unit size large, real time at speed 1. Before v13 a decision came 5 s of
  battle time after the previous orders applied; since v13 it starts as soon as they are
  acknowledged.
- The benchmark entries (b1-b9 and G1, 2026-10-14) are development screens: no scenario
  was admitted under the former rule, G1 is incomplete and G2 never ran. Win-rate admission
  was retired in the 2026-10-15 plan revision below. "Margin" is the active-strength margin
  and "clock ratio" battle time over wall time
  ([benchmark.md](benchmark-implementation.md#what-the-current-code-reports)).
- A new entry goes at the top, and "On main" is updated with it.



## 2026-11-01: native multiplayer observer smoke, one battle

Claude Code with the owner, $0, at `d499025` (no source change). The proposed observer
card (`runs/wh3-native-mp-20261030/card-observer-smoke.md`): coordinator and `worker --attach`
in WSL, `launch`, session edited to `observe`; the owner set up and played one single-player
1v1 by hand (Herald of Khorne and 2 Bloodletters each side, 20-minute timer) at 1x.
- Owner: every UI order was obeyed. mod.log: "loaded battle", no "inactive"; engine result won at 194.7 s.
- `native` in 161 of 162 observations (the one without is the `Loading` placeholder): mode
  observe, local alliance 1, local army 1, not multiplayer, not spectator, no errors; owners
  470 own, 470 enemy, 0 allied; 3 own and 3 enemy units of the roster's types.
- `compare-peers`: 162 observations, 0 native errors, 0 failed rows, 0 repeated times. Events
  reach the victory countdown; the coordinator closed with no failure and removed the token.
- Speed read 1 in 162 of 162; 191.1 s of battle time over 191.1 s of observation write times
  (NTFS, Windows clock).
- Owner: "The units did die rather quickly." Contact at about 138 s; each Bloodletters unit
  went from 75 men to 0 in about 44-56 s; ours fought on with morale at or below 0 from
  176.4 s, and no unit ever counted as routed.
- Notes: a destroyed unit can stay in `native.units` one observation after the evaluation counts
  it (e1 at 194.7 s). The coordinator closes on stdin EOF, so a background run must hold stdin
  open: attempt a1 closed at once; a2 is the run.
- Not run: the card's check of the check, so no live reading has caught a `take_control` plant.
  Unverified (n=1, no agreed check); nothing multiplayer was tested. Evidence:
  `runs/twwarhammer3/native-multiplayer/smoke/a2/` (mod.log copied there) and `smoke-logs/`.


## 2026-11-01: the code page shows WH3 only, renamed, and in the README

Claude Code, $0, no game. Owner: the Slay the Spire box "is just creating confusion"; "omit that
game and make it clear that we're talking about only WH3"; "multi-agent.html" no longer fits; the
README should show "at least some of these visuals".
- `docs/multi-agent.html` is now `docs/how-code-works.html` ("How the WH3 code works"), with
  `how-code-works-files.js`; links and current mentions follow (older log text keeps the name).
- The map drops the Spire box and its wire and says that game is not drawn. Its new "outside"
  list (Spire's paths) is skipped by `check.py`'s file-list flags and `diagram_files.py`, which no
  longer read docs/spire/AGENTS.md; a test case and a plant cover the skip.
- The README's WH3 section shows the map as a GIF of its moving dots, and stills of Basic vs GaP
  and the graph-battle replay (`docs/images/code-*`, 1.8 MB together).
- Checks: `check.py` passed; `func.js` 35/35 and `func2.js` 56/56 on the renamed page; the
  extended test fails on a `check.py` that ignores "outside". A reviewer found the old local
  path in the WH3 README, "no model call" overstated in the README (GaP may ask for target
  hints) and the stale-path check unpinned for left-out paths; all fixed. Unverified: your look.

## 2026-11-01: the "How the code works" page redesigned

Claude Code, $0, no game; two sessions, a PC reset between them. Owner's goal: the page looked
"disorganized and cluttered", with tabs that "seem disconnected" and slop like "Frozen 31 Oct";
"Less is more"; keep the overview's moving dots that compare timing; include something like the
GaP battle viewer.
- One bar groups the views as the map does: Map; One battle (job, decision, two members); Control
  methods (basic vs GaP, graph battle); Multiplayer; Factory. Each view's corner map lights and
  names its area; a story's last step offers the next view. Overview, Play loop and Team went (in
  Git at `72e5197`) with `scripts/diagram_replay.py`. The page is 266 KB, was 383 KB.
- Status lines ("Frozen 31 Oct", review dates, "not verified", "code changed since", trace rows)
  sit behind the one Sources switch. Multiplayer and Factory step like the stories, with no
  made-up clock, speed menu or slider, and larger type; the experiment loop has its own heading.
- The Map's wires carry teal dots at five kinds of rate, sourced and not to scale, switchable
  between a model and a graph controller: a request after every decision, 88 in the 335 s basic
  battle and 2017 in the 618 s GaP battle; 92 model calls in the first, none in the second.
- One graph battle gains "Whole battle" (`diagram_examples.py replay`): both members' current
  steps lit, one lane row per step (536 runs), 165 order batches (6 new), the story's 8 steps as
  bookmarks, the units' public positions once a second. 77 KB, against graph-view's 5.4 MB page.
- Checks: `check.py` passed (2555 tests); `runs/page-redesign-20261101/func.js` 35/35 and
  `runs/page-polish-20261101/func2.js` 56/56 assertions; each of 11 planted wrong versions fails
  at least one. Two fresh-eyes agents answered 12 of 12 questions from the page; a third judged
  its look. Reviewers found 3 wrong claims, then 3 regressions (timing notes hidden, steps
  demoted, a tall corner map) and a wrong caption at a flow's end; all fixed. Card not agreed
  (owner away). Unverified: whether the page teaches; your look. 4 `JUDGEMENT?:` markers (map dot
  speeds, replaced tabs, replay sampling, replay current step).

## 2026-11-01: control methods drawn on the "How the code works" page

Claude Code, $0, no game. Owner's goal: "Find a good way to represent different army control
methods that we will implement. For now we have the basic one, and then GaP. We need clean
visuals for those too."
- New tab "Control methods": one row group per method on one battle clock, with columns before,
  during and between battles; model calls purple; a card per method (where, who, what it writes,
  when it is done, calls, decisions, view age, example). Basic: knights3 (`llm_rules`, lost at
  335.2 s); GaP: `gap-initial-02-20261101` (lost at 618.2 s). One battle each, different code
  versions: no strength claim.
- New tab "One graph battle": the graphs that battle ran, drawn from its record (only steps that
  ran and exits taken, with counts); 8 steps from authoring to the cavalry's melee at 386.3 s.
- `diagram_examples.py` recipes `methods` and `graph` recompute every stated count and refuse a
  mismatch. `check.py` diagram flags also compare policy names, graph operations and controller
  versions with the code, read card, status and generated refs, flag each listed example's changed
  cited files and check story step ids; 13 plants.
- Five agent reviewers found 21 problems (2 wrong claims, 8 misleading, 3 rule breaks, 7 bugs,
  1 unsupported count); a skeptic confirmed each; all fixed and rechecked. Unverified: whether
  the views teach; your look. 15 new `JUDGEMENT?:` markers (colour, window, layout, examples);
  "GaP drawn in the page" replaces "No GaP view".

## 2026-11-01: corrected plan starts combat and cavalry joins; battle still lost

- One fresh 1x battle at `5c02d08`: `battle/gap-initiator-revised-01-20261101`.
  Same frozen skills, scenario and settings; only the previously authored line selector changed.
- Line first attack source 6.8 s, accepted 7.4 s; own matching melee 332.6 s;
  engage run 6 completes 332.9 s. Cavalry attacks after public contact (source 333.8 s),
  then reaches matching melee and charge run 1 completes at 383.9 s.
- Fixed physical criteria passed once: 161 accepted attacks, 0 invalid batches. The unchanged
  original contact assessor also passed; movement/no-order probes were not rerun.
- Engine lost at 666.8 s, before its timer expired; no infrastructure error. Seven skill
  failures recovered (five line deadlines, two cavalry eligibility losses); failures retained.
- Four live model calls, three adopted goals, one rejected reply (209-character reason
  exceeded frozen 200). Live cost $0.0011336; cumulative 27 calls/$0.0285739 of $5.
- Raw Windows clock ratio 1.000005; speed flags 1x. Game closed; postdoctor ready, PID query empty.
  Independent raw/register audit: `runs/gap-initiation-20261101/review/live-followup/report.txt`.
- [New battle viewer](http://localhost:8765/gap-fixed-live-20261101.html): six raw order/ack/effect
  browser checks passed; combined page checked six episodes/twelve graphs. Evidence in that run folder.
- This establishes this plan's contact/charge effects once, not superiority to non-GaP control,
  learning or general progress. No further candidate or battle is planned for this temporary fix.

## 2026-11-01: the actual author revision corrects the waiting infantry

- At committed `4f0c3fc`, `initiator-revised-01` is ready: three actual Haiku calls,
  no parse repairs, $0.0055201. Same task, library, ownership and live-goal settings.
- Exact graph change from `live-revised-01`: line select.mode engaged to nearest.
  Cavalry is identical. Its first public line view supplies an owned f1-to-e2 attack
  route; this is a starting-state check, not engine contact or a new gameplay result.
- Parent/episode files retain their hashes. Only permitted member feedback and first
  public views reached authoring; coordinator saw no battle evidence.
- The agreed command passed 52 cases on clean tracked `4f0c3fc`; independent replay
  matched. Before commit, the exact feature tree's full gate passed 2551, skipped 43
  (40 torch, 3 Windows opt-in), Ruff clean; one informational code-map citation flag.
- Cumulative WH3 Anthropic ledger: 23 calls, $0.0274403/$5; original 20-row prefix intact.
  Independent audit: `runs/gap-initiation-20261101/review/author-followup/report.txt`.
- Later docs-only gate hit an unchanged worker lease timeout; its isolated case passed.
  Failure/recheck: `runs/gap-initiation-20261101/`; worker code/tests were not edited.
- No new battle, learning or strength result. One fresh 1x diagnostic waits for a current
  PC window; the owner's answer is pending. No second author candidate planned.

## 2026-11-01: temporary author-initiation check catches circular waiting

- Owner approved temporarily: infantry must have a way to start combat; cavalry may wait.
  Author v4 adds `--starting-episode EPISODE --initiator line`; a rejected initiator reply
  uses the existing repair allowance. Revisions inherit the caller's declaration.
- Only first public member inputs reach the check. Saved artifacts bind the declared
  members, public view, graph, checker and source metadata. Legacy v3 without the new
  fields remains readable with the same frozen library; no old artifact is rewritten.
- Final focused set: 249 passed. Both actual stalled line graphs reject; both one-field
  nearest-target drafts produce owned f1-to-e2 attacks in the starting-state check.
- Review found malformed input reaching canned calls and proof removal/source-edit gaps;
  regressions failed before fixes. It also caught idle out-of-range artillery acceptance.
- Checker sweeps: initial 7/9, then 9/9; later 11/12 exposed a preprojection test gap.
  Final 12/12 caught (80 baseline), no hangs. Author v4: 21/21 caught; 3 semantic plants
  caught. Independent final report: `runs/gap-initiation-20261101/review/report-final.txt`.
- Semantics rest on JUDGEMENT `graph_initiation.py` Temporary initiation semantics:
  possible move/hold exits do not prove effects, universal progress, learning or strength.
  The later pinned pass and actual author follow-up are recorded above; no live effects claimed.
- Next: one actual revision of the stalled plan with this check and the original task,
  library/settings and cumulative $5 cap; stop on failure. A live rerun needs a current PC window.

## 2026-11-01: the "How the code works" page: map, three stories, flags (merged)

- Plan [how-code-works-plan.md](../how-code-works-plan.md) (answers 1a, 2a, 3a), merged as
  `c471b45` (pilot) and `45c2a39` (plan step 4): `multi-agent.html` opens on a 12-box map of the
  repo; stories "One play job", "One decision" and "Two members, one army" on recorded battles
  (knights3 at `b7e2dd1`, team probe 1 at `96bb137`); the five 10-31 tabs are frozen. File lists
  one per line (the WH3 README Code map, the Spire Layout); scripts write them and the battle
  excerpts into `docs/` and regenerate identically.
- `check.py` prints `diagram   N views flagged` (0 at `45c2a39`); 3 tests, 10 plants, 12 planted
  wrong versions caught. Five agent reviews found 23 wrong claims, 7 unsupported or misdirected,
  4 picture or rule failures and 4 flagging holes; all fixed.
- Quiz (n=1, unverified): with pictures 5/5 on the old tab and the new story; without pictures
  5/5, 5/5, 4/5 (old) and 3/5 (new): neither passes the plan's 2-of-5 control bar.
- Three-week replay (1014 commits): 1-2 of 2 views flagged each week, mostly by new `src/` files
  and example files; no cited line's text changed. One measured refresh: 50 calls. All work
  683 API calls, $0, no game. Your look and stop-or-continue wait:
  `runs/how-code-works-20261101/handoff.md`.

## 2026-11-01: live-author integration preserves a stalled plan through revision

- At frozen `87518f9`, author v3 produced `gap-20261101/live-initial-01` in 3 calls,
  no repairs, $0.0023761. The coordinator assigned already-engaged targets to the line;
  cavalry also waited for contact. Structural readiness did not establish the requested task.
- The fresh initial whole battle lost at its time limit, 1205.2 s, with 0 orders,
  0 runtime goal/model calls and 0 invalid/errors. Its public feedback alone reached
  `live-revised-01`: 3 calls, no repairs, $0.005348; authority/library/parent pins matched.
- Revision left the line graph unchanged and changed only cavalry's successful-charge
  exit from end to owned. That edge was never reached in the initial battle.
  The fresh revised whole battle also lost at 1205.2 s with no orders or live model calls.
- Raw jobs: `battle/gap-live-{initial,revised}-01-20261101`; artifacts are immutable.
  These are generated-plan task misses, not infrastructure failures or evidence of
  active live-goal integration. No strength, causal improvement or learning claim.
- Cumulative Anthropic ledger: $0.0219202 of $5, including the earlier dispatch probe.
  Independent audit: `runs/gap-continuation-20261101/review/integration02/`.
- Viewer now exposes engaged-only selection and explicit node limits from recorded graphs.
  Its raw-mode regression failed before the fix; 2 recorded browser cases, 31 reader cases
  and wrong-mode/wrong-time-unit plants passed review in `review/view-options/` there.
  Proposed next authoring check: public-state progress for a declared initiator; owner answer pending.

## 2026-11-01: live target preferences pass the agreed dispatch check

- Owner agreed the proposed live method; recorded/frozen at `87518f9`, runtime unchanged
  from `8ad194e`. The original checker was used without changing its criteria after agreement.
- Clean-checkout component command: 54 passed. One fresh live diagnostic passed: both
  Haiku members chose e1 then e3, with graph selection, accepted owned attacks and later
  public target readings. Cavalry readbacks: 13.4/43.7 s; line: 13.7/44.0 s.
- Recorded 56 accepted attack batches, 0 invalid, 282 samples at engine speed 1;
  Windows-clock ratio 1.0000201. Shutdown recorded no remaining game process.
  Diagnostic cutoff at 90.5 battle seconds: no gameplay outcome or skill-completion claim.
- Four real calls cost $0.0011568; cumulative ledger after the probe was $0.0141961 of $5.
  Independent recount matched raw requests, sources, orders, acknowledgements, readbacks,
  charges and cleanup: `runs/gap-continuation-20261101/review/live01/report.txt`.
- Raw evidence: `runs/twwarhammer3/graph-goals-live-20261101-01/`; checker/source hashes
  retained. Viewer now includes this episode (`reports/gap-live-20261101.html`), with
  four actual hint/order/ack browser cases passed. No strength or learning comparison.
- Next: the planned author-v3/full-battle/revision integration with live-goal members,
  preserving the existing task, scenario, immutable artifacts and cumulative cap.

## 2026-11-01: add live target-preference controllers, checked offline

- Added optional `graph_llm` leaves: a background model chooses a public target or none;
  each fixed graph and teammate continues. Only a later eligible selection uses the hint.
  An active skill keeps its target. Requests/hints retain controller, graph, battle,
  ownership, goal-run and source identities; stale/closed replies cannot steer orders.
- Mixed controllers/rotations share the job ledger; cleanup retains exchanges and costs.
  A new opt-in transport timeout keeps existing callers' default. Limits rest on
  JUDGEMENT `graph_goals.py` G4 Goal limits; the example has its own marked model/call cap.
- Author v3 preserves model authority in graph templates and freezes the updated source;
  old artifacts remain pinned to their original library. Viewer shows hint use/source rows.
- Offline checks: 372 focused cases, both saved battles in the existing browser check,
  and 2 synthetic goal-view browser cases passed. Guard sweeps initially caught 2/5 and
  6/18; added regressions catch 5/5 and 18/18. Separate expired-scope and blocking-wait
  plants fail. Raw outputs/review/exit gate: `runs/gap-continuation-20261101/`.
- No new game/API calls; original Anthropic spend remains $0.0130393 of $5. Proposed live
  steering check awaits the owner. This feature, live holding/firing, tactical strength
  and learning remain unverified. Viewer agreed method passed at `b8f8cb7`.

## 2026-11-01: inspect recorded GaP graphs and their battle execution

- Added offline `graph-view`: frozen member graphs, active/ready nodes, public positions,
  orders, acknowledgements and completion witnesses, with trace rows and source times.
  It keeps missing results/witnesses explicit and checks graph/battle/producer identities.
  Local preview: `runs/twwarhammer3/reports/gap-20261101.html` (both authored whole battles).
- Owner agreed the reader/browser check. Working-tree evidence: 31 reader cases, both
  members in both recorded battles, and 3 synthetic browser regressions passed. Eight
  reader regressions and the missing-witness browser case failed before their fixes.
- Independent review found collection-time, partial-ack, nested-proof and clipped-label
  bugs, then missing-witness wording; all fixed, final no findings. Guard-removal sweep
  initially caught 5/7; removed one redundant refusal and added missing-recording cases;
  final 6/6 caught. Wrong member binding and ack-as-completion plants also failed.
- Built wheel includes all 3 assets; browser passed without network requests/errors, and
  the preview URL returned HTTP 200 from Windows. Exit gate and checked revision: commit
  and `runs/gap-continuation-20261101/`. No game/model calls or strength claim in this change.
  Next: the planned live target-preference slice; its proposed check awaits the owner.

## 2026-11-01: complete the initial GaP author-battle-revision smoke

- At `d6dfe92`, author v2 generated both graphs in 3 Haiku calls ($0.0025157), then revised
  them from one completed battle in 3 calls ($0.006504). Cavalry adds an ownership refresh
  before charge and spells out the existing 60 s timeout; line stays identical. Frozen
  library/authority/parent pins and each member's public context pass independent review.
- Whole battles: initial lost at 618.2 s; revised lost at 460.7 s; both engine endings,
  zero invalid batches and zero battle model calls. Source `d6dfe92`, build 25961564;
  speed flags 1, recorded Windows ratios 1.0000 (ordinary play does not retain raw Windows
  timestamps to independently rebuild these ratios). No strength or learning claim.
- Total paid: 10 calls, $0.0130393 of $5, including failed v1; credentialless invocation
  made no call. All attempts/exchanges retained under `runs/twwarhammer3/gap-20261101/`.
  Battles: `runs/twwarhammer3/battle/gap-{initial-02,revised-01}-20261101/`.
- All 91 agreed component cases passed at `d6dfe92`; live effects remain the 3/3 pass at
  `d12be58`, with the failed 360 s run preserved. Graph/author refusal sweeps caught 6/6
  and 16/16; ack-as-success and missing fresh dispatch plants failed their named cases.
- Final independent review and exit gate: commit message. `runs/gap-implementation-20261031/`
  holds cards, checks, reviews and handoff. One intermediate doctor failed on WSL interop;
  retry and final doctor passed, all controllers stopped. Own scratch/worktree removed.
  Live holding/firing, charge bonus, multiplayer, restoration and learning stay unverified.

## 2026-11-01: live effects pass; first Haiku generation finds missing interface detail

- Extended live check passed 3/3 fresh probes at `d12be58`:
  `runs/twwarhammer3/graph-live-20261101-extended/`; independent recount agrees. Control
  covered 155.7 s without arrival; move arrived at 32.9 s, 22.5 s after waypoint creation;
  cavalry contacted selected `e2` at 390.5 s after accepted orders to an already-engaged
  visible target. All 23 cavalry batches accepted; all probes cleaned up. The contact
  battle lost at 441.2 s. This establishes the declared effects, not tactical strength.
- First author invocation stopped before a call because this shell lacked credentials;
  preserved in `gap-20261101/initial/`. Restored the documented key-file/workspace settings
  without reading the key. `initial-01/` then made 4 Haiku calls, costing $0.0040196:
  coordinator and line accepted, cavalry rejected for mode placement and an invented post.
- Author v2 now supplies literal input shapes and node-option placement, and explains that
  no named `current_post` exists. Validator, executor and repair limit stay unchanged.
  The new actual-prompt regression failed before the fix; 28 author cases pass. Independent
  review wording finding fixed; final no findings. Whole gate: commit message. A bounded
  fresh generation retry and between-battle revision still follow, within the same $5 cap.

## 2026-11-01: extend the contact observation window at the owner's approval

- Owner: "Yes, extend the contact limit and rerun", approving 360→540 s after the first
  probe ended before arrival. Preserved that failed run; every effect, identity and clock
  criterion stays the same. Supervisor allowance increased to contain the longer window.
- Same three fresh probes, no new scenario or tactics, $0, total cap 30 minutes. Existing
  component cases, independent review and exit gate: commit message. Rerun still follows.

## 2026-11-01: add multi-LLM graph authoring and whole-battle revision

- Built `wh3-graph-author-v1`: one coordinator and two specialists, frozen skill library,
  per-member public revision evidence and new immutable artifacts. Directory and generated
  file loading check readiness and library/controller pins before a battle. Other control
  methods keep their existing factories and dispatcher.
- 88 focused cases passed (25 new, 63 existing CLI/factory cases). Refusal sweep initially
  caught 8/16, then 16/16 after input and source-context regressions. Independent review found
  a missing-pin loader bypass; fixed, final review: no findings. Whole gate: commit message.
- One JUDGEMENT marker: author context/repair limits. Evidence/card/review:
  `runs/gap-implementation-20261031/` (including `author-review/` and refusal sweep logs).
  No real model call yet; the planned Haiku initial/revision smoke stays within $5 cumulative.
  Component evidence establishes no policy strength or learning.

## 2026-11-01: first graph live check — movement passes, contact stops before arrival

- Three fresh probes at `7c29d35`, all closed with no remaining game PIDs:
  `runs/twwarhammer3/graph-live-20261101/`. Overall check failed; no engine battle outcomes.
- No-order control passed (155.7 s of exposure, no arrival). Graph move passed: ack 10.7 s,
  arrival 32.9 s, 22.5 s after waypoint creation. Windows-clock ratios 1.000042 and 1.000022.
- Contact probe: line first melee at 336.8 s, cavalry attack source at 341 s, correct visible
  already-engaged target `e2`. Cavalry still approached when the 360 s wall cap stopped the
  probe (last battle reading 361.1 s); no own melee witness or charge completion observed.
- Contact/charge remains unverified. Asked the owner about a 540 s contact cap and a fresh
  rerun with identical effect criteria; no rerun before that answer. $0; no paid calls.

## 2026-11-01: add the initial graph live checker

- Added the agreed three-launch method: no-order control, graph movement, then independent
  line/cavalry contact and charge. Recount requires raw engine effects after matched
  acknowledgements and agreement between node completions and those raw witnesses.
- 28 hand-computed component cases pass, including idle drift, wrong target, pre-contact
  charge, rejected acknowledgement, missing effect and premature completion. Independent
  review found and fixed clock, battle identity, control-duration and pre-delivery arrival
  gaps; final review
  and exit gate: commit message; evidence `runs/gap-implementation-20261031/`.
- Added one JUDGEMENT marker for probe geometry and bounds. No game launched or model called
  by this change; live effects, holding/firing and strength remain unverified.

## 2026-11-01: initial GaP runtime and interchangeable controller composition

- Built the owner-approved bounded library over existing tactics, typed JSON graphs,
  public effect witnesses and independently dispatched graph members. `configured` composes
  graphs, scripts and direct models; one shared ledger covers mixed rotations and members.
  Hand-written contact/charge graphs are in `configs/twwarhammer3/graphs/`.
- Offline: 179 focused cases passed (including existing controller/team/play cases).
  Removing graph refusals initially exposed three missing cases; the added cases catch all
  six removals. Ack-as-success and skipping fresh dispatch each fail their named regression.
  Independent review found five bugs (budget, deadline, terminal no-op, cleanup retry,
  unrelated-shot witness); all fixed, third review: no findings. Exit gate: commit message.
- Added three delegated G4 JUDGEMENT markers (skill limits, graph limits, target choice).
  Existing ownership/projection choices remain marked. Evidence:
  `runs/gap-implementation-20261031/`. $0; zero live battles so far. Component checks do not
  establish live effects or strength. Author/revision tools and live feasibility still follow.

## 2026-10-31: record the owner's GaP plan decisions

- Updated the [plan](gap-plan.md) from the owner's fourteen answers: existing controller/team
  integration, independent progress, observation-only coordination, whole-battle revisions,
  a frozen pre-built library, permitted information and separate graphs for allied armies.
- Broader skill library comes first as a separately scoped workstream, using MORSL as a
  reference; initial execution limits are delegated tuning choices. Research comparisons,
  benchmark design and restoration remain deferred; exact library and battle scope stay open.
- Documentation only. No implementation, game runs, API spend or new agreed checks.
  Independent review and offline gate evidence are recorded in the commit and
  `runs/gap-owner-decisions-20261031/`. GaP behaviour and learning remain unverified.

## 2026-10-31: keep passive capture alive after malformed backend output

- A JSON list or deeply nested JSON raised in the passive worker before failure metadata
  and later capture requests. The worker now records unsupported result types and ordinary
  backend/decode errors as failed callbacks. Metadata writes and capture limits are unchanged.
- Review also found an empty reason for message-less OSError; exception classes now survive
  in reasons. Final six-case regression: before fix 3 failed/3 controls passed; after fix,
  capture/controller group 29 passed (23 before). No screenshots or Windows calls.
- Five wrong variants caught: dropped metadata/reasons 5 failures each, missing type/depth
  guards 1 each, stopping after one failure 6. Previous 187 registrations retained; 192 total,
  no full-192 replay. Constructor-refusal sites remain 0, not mutation-strength evidence.
- Cards/raw: `runs/test-quality-20261031/capture-backend-failures/`; independent review and
  final gate recorded in the commit. Card unagreed; no new verification method, live capture
  effect, game outcome or policy-strength claim. Existing adoption choices remain pending.


## 2026-10-31: reject replay identity before touching episode evidence

- Two wrong copiers passed all 15 capture/integration cases: copying before identity
  rejection, or checking the job while ignoring the battle header. Source is correct.
- Four added cases cover job/battle mismatch with absent or different existing destination
  bytes; source and destination must remain unchanged. All prior test definitions retained.
  Control: 19 passed; wrong copiers: 4 failed/15 passed and 2 failed/17 passed.
- Related capture/play/team checks: 165 passed. The two replay faults plus six handler faults
  bring registrations from 172 to 180; no full 180-entry replay is claimed.
- Card/raw evidence: `runs/test-quality-20261031/replay-identity/`; independent review and
  final gate recorded in the commit. Card unagreed; agreed-file adoption still pending.
  File checks only: no live recording, policy-strength or new verification-method claim.

## 2026-10-31: keep episode results when optional evidence copying fails

- A malformed replay header (`[]`) or numeric still filename raised during cleanup and
  discarded `result.json` after a fake engine win. Each optional copier now records an
  ordinary exception as existing `status=error` metadata, then saves the engine result.
- New integration tests: before fix 2 failed/1 valid control passed; final 7 passed,
  including deep-JSON errors and interrupt propagation. Related suites: 161 passed.
- Six wrong handlers caught: narrow IO catches fail 2/7 cases; consumed interrupts or
  shape-only catches fail 1/7. Review found and closed the initial deep-JSON test gap.
  Pre-change play-only sweep: 13/14 caught; the missed team guard already had a test in the
  team suite. Expanded sweep: 14/14 caught before and after, no hangs; baselines 108/115.
  Six new handler faults were replayed; all prior registrations are retained unchanged.
- Card/raw traces and checks: `runs/test-quality-20261031/capture-schema/`; independent review
  in `runs/test-quality-20261031/review/capture-schema/`, final gate in the commit.
- Offline only: 3,611 files in the two agent directories retained modification times.
  No live capture/gameplay effect established; card unagreed, feature unverified under the
  hard rule. Existing adoption questions remain pending; no new agreed check or scoring rule.

## 2026-10-31: test audit integrates factory changes through main 8076fc1

- Merged main `8076fc1` into the isolated testing draft; retained the audit status and main's
  stopped-controller status. All parent plant definitions retained exactly: 167 audit,
  144 main, 172 distinct in the union; this is preservation, not a fresh full replay.
- Gate/hook integration tests: 224 passed. Normal gate and independent review are recorded
  in the merge commit and `runs/test-quality-20261031/main807-integration/`.
- Existing test-edit and optional-CI adoption questions remain pending. Offline evidence;
  no new agreed method, game run, benchmark meaning or policy-strength claim. Card unagreed.

## On main

| Piece | Version | Defined in | Latest results |
|---|---|---|---|
| `llm` | v22 (2026-10-21) | `configs/twwarhammer3/system_prompt.md`, `battle/llm.py` | v22 tells a defender on a contact-scored card that the timer does not count (unplayed). v21 states that positions are unit centres and the melee flag decides contact (unplayed by `llm`). v20 shared-magic warning played once (GLM, `llm_rules`): over-spend after a pending spell halved. Tactical prompt's last mode campaign was v15 |
| `llm_rules` | shares `llm` v22 input; added in b3 (`51c1796`) | `configs/twwarhammer3/rules_prompt.md`, `battle/llm.py` | v21 chariot cohort: [b40 round](#2026-10-19-witness-v2-and-prompt-v21-harness-b40). v20 GLM/OpenRouter caster check won at 575 s; spell refusals after a pending spell 7 → 3 (v19 lost). M1 used v18 |
| `commander` | v8 (2026-10-21) | `configs/twwarhammer3/commander_prompt.md`, `battle/commander.py` | v8 the contact-scoring state line (unplayed); v7 shared-magic warning tested offline; latest live smoke remains b11 (Luna low, lost at 593 s) |
| `skills` executor | v1.2 (`55ab6b3`, 2026-10-13) | `battle/skills.py` (also `probe_abilities`) | `bench-b2-screen-ai10-20261014` won at 382 s; `bench-b2-screen-ai11-20261014` lost at 265 s |
| scripted baselines | `attack_nearest`, `rush_nearest` (b9), `hold` | `battle/scripted.py` | Latest: the [starting-set screen](#2026-10-22-the-starting-set-screen) (30 floor launches, 2026-10-22); first: `bench-g1-cavalry-ai10-01-20261014` |
| scripted team | v1 (`45fe7b0`, b49; input `team-v3` since b50) | `battle/team.py` | Agreed $0 movement/cleanup probes 4/4 at `3adbaa4` ([b50](#2026-10-28-model-team-reviewed-cleaned-and-checked-live-harness-b50)); messages and native multiplayer unimplemented |
| `team_llm_rules` | v22+t2 (2026-10-27): `llm_rules` per member plus the teammate's units and condition | `battle/team.py` (`ModelTeam`, `TeamLLM`), `battle/llm.py` | Unplayed; no agreed check yet |
| graph controllers | `wh3-graph-v1`, `wh3-skills-v1`, author v2 (2026-11-01) | `battle/graph.py`, `skill_contracts.py`, `configured.py`, `graph_author.py` | [Initial delivery](#2026-11-01-complete-the-initial-gap-author-battle-revision-smoke): 91 component cases; 3/3 live effect probes; authored and revised whole battles both lost. No strength/learning claim |
| benchmark harness | b52 (2026-10-31: observations carry the engine's game speed, `battle:current_battle_speed()`; team members' records say `running_at_close`; the card board leaves team episodes off; `cards.benchmark_outcome` v1 beside `cards.outcome`, unused); b51 (2026-10-29: 1x measured by the Windows clock from observation write times, in `result.json` and `digest`); b50 (2026-10-28: team cleanup statuses, member delays in digest, watch spend from model exchanges); b49 (2026-10-21: scripted-team timing, events and fault handling; b48 a scenario's `scoring` reaches the controller's `mode`; b47 the engine's ending kept through a late controller failure; b46 LineTeam kept targets and the reason cap; b45 the rank-5 line step; b44 LineTeam arms and the Orc Boyz knights step; b43 three Empire scenarios; b42 context setup, declared settings, correlated UI requests and session cleanup; b41 saved armies/XP), evaluator v2, track `obs-v4+terrain/act-v2/live-1x`, export schema 2 | `engine/mailbox.py`, `protocol.py`, `battle/play.py`, `setup.py`, `controllers.py`, `calibration.py`, `cards.py`, `report.py`, `export.py` | [The Empire set](#2026-10-20-the-empire-set-harness-b43) (45 launches; the rank-5 line battle is the first candidate team card); [integration verification](#2026-10-20-ui-and-lobby-integration-harness-b42) |
| replay recorder | v1, on by default (`--no-record-replay`) | `battle/capture.py` | `visual-sol-low-20261015` |
| battle checkpoints | v1 (2026-10-25) | `battle/checkpoint.py`, `engine/checkpoint_agent.js` | Land check at `6fdb271` and [`dcb8b5a`](#2026-10-28-overnight-restore-pauses-were-wsl-clock-steps-land-check-passes-at-dcb8b5a); [declared siege cases](#2026-10-25-siege-checkpoint-checks-pass-for-declared-cases) at `2e2acbe`; public tool v0.1.0 |
| checkpoint RL | merged 2026-10-28 (`6b942a3`) | `battle/rl.py`, `candidates.py`, `audit.py`, `confirm.py`, `checkpoint.py`, `gameai/lm.py`, mod export `twwarhammer3_inject` | Stage 1 and closed-loop checks agreed 2026-10-26 ([agreed-checks.md](../agreed-checks.md)); learning collapsed, held-out 0.76 ([2026-10-26](#2026-10-26-checkpoint-rl-implemented-and-run-stage-3-fails-the-policy-collapses); decision 11) |
| stills | imagery v3, opt-in (`--stills`) | `battle/capture.py`, `mod/script/_lib/mod/twwarhammer3_imagery.lua` | `visual-probes/close-imagery-r2-20261015` |
| report | core scenario index and battle development (2026-10-16) | `battle/report_html.py`, `report_assets/`, `replay.py`, `configs/twwarhammer3/report_notes.json` | Last suite build 2026-10-17 from `benchmark_jobs.json`: 140 jobs, 231 trials, 220 valid ([overnight tranche](#2026-10-17-overnight-tranche-harness-b18-b23)); the page shows the core scenarios only, the JSON and text every one |

## 2026-10-31: Anthropic provider added

Claude Code, under the owner's "Implement docs/anthropic-provider-plan.md"; no game.
`--provider anthropic` (both games) sends the Responses-shaped request to Anthropic's Messages
API through a translation in `gameai/llm.py` `post()`; Haiku 5.5, Sonnet 5.5 and Opus 5.5 at
low to max ([controllers](controllers.md#anthropic)). Ledgers `runs/twwarhammer3/anthropic-spend.jsonl`
and `runs/spire-anthropic-spend.jsonl` (created empty). The owner's key file held 10 bytes of
terminal escape codes before the key (HTTP 400, empty body; `runs/anthropic-provider/key-file-fix.md`);
stripped, and `api_key()` now refuses unprintable keys. The key is not scoped to a workspace: `GAMEAI_ANTHROPIC_WORKSPACE_ID` is
required. Reviewer round 1 found 529 resent for every provider, a docstring claiming an unrun
live check, a bundled marker and four uncaught wrong versions; all fixed, the plants now fail.
Paid smoke at `551b514` (`runs/anthropic-smoke/`, own ledger, $0.25 cap): $0.0211, 18 calls.
The Models API flags match `providers.py` (efforts low to max on all three; thinking off only
on Haiku `disabled`, Sonnet `between_tools`). All 15 model × effort calls (Spire schema, 256
tokens, no resends) returned 200 and completed in 1.0-3.0 s (WSL wall time); on that trivial prompt only
Haiku `max`, Sonnet `max` and Opus `xhigh`/`max` reported thinking tokens (36-185). One Haiku
`high` ask per game schema passed `json.loads` and the schema's field check on its first attempt
(Spire, WH3 `llm`, `commander`; real system prompts, synthetic situations, 2.1-5.9 s); not the
games' own parsers. Both WH3 ones returned a summary where the exporters look. All 18 ledger
rows equal list price × reported usage (recomputed by the rerun reviewer). Not shown: cut-off
replies (none occurred), refusals, 529s, latency under load, gameplay, and Anthropic's own
usage figures: `runs/anthropic-smoke/usage_compare.py` (free admin reads) found no rows in
the usage or cost report 10.5 minutes after the last call; rerun it a day later, as the plan says.

## 2026-10-31: multi-agent diagram page, measured replay (plan step 6)

Claude Code, $0, no game; built on a branch, since the plan makes the replay mode a separate
decision, then merged the same day: it changes no number and is the owner's to reverse. `scripts/diagram_replay.py` turns one recorded team episode's
trace.jsonl into a Team-tab flow in the page's step format, badged "measured", one step group
per request round in the trace's row order: `docs/multi-agent-replay.js` replays
`team-live-20261031e` probe 1 from 5.30 to 10.40 s (64 steps, 29 lane items). Battle times are
copied; a call's think span is its WSL duration scaled by a fit over the window's 12 input events
(1109 battle ms per WSL second), ending no later than the decide that collected it. Reviewer
rounds 1-2 found steps drawn before or after their cause, window edges, a crash on a window
without a member's input, think bars made of fit error and counter labels; all fixed. Cross-check (scratch `compare_replay.js`, which reads the trace itself): all
29 lane items of the hand-written probe flow match on recorded times (completions within 30 ms),
and every round's steps match the trace on 9 windows of probes 1-4; it catches 7 planted
generator bugs. A Chrome trace-event JSON of the lanes was written, not opened in Perfetto.

## 2026-10-31: multi-agent diagram page, Overview flow and links (plan step 5)

Claude Code, $0, no game. The Overview of [`docs/multi-agent.html`](../how-code-works.html) now
loops a dot on every built link and opens an area's tab on a click; its panel lists each area's
status and sources. The page is linked from the [Pages](README.md#pages) table and
[workflow.md](../workflow.md); [references.md](../references.md#diagram-viewers) lists the five
viewers it borrows from and the five it does not use. Reviewer: 10 Overview items confirmed;
28 reference facts, 27 confirmed, 1 marked checked without a re-fetch (dropped); one viewer
defect (stepping past the loop's end showed nothing), fixed. Plan steps 1-5 are built; the
replay mode (step 6) waits for the owner, and so does the look. Handoff:
`runs/multi-agent-diagram-20261031/handoff.md`.

## 2026-10-31: multi-agent diagram page, Play loop tab (plan step 2)

Claude Code, $0, no game. The Play loop tab of [`docs/multi-agent.html`](../how-code-works.html):
23 boxes, 32 wires, four flows. "One decision, one model controller" replays r25 of
`bench-b45-knights3-glm-low-l1-20261020` episode-0000 (GLM 5.3, low; one episode, not a
measurement; it ran at `b7e2dd1`, and the page names the parts that differ at `21f6204`: the
ledger hold and the hidden keys). The model call took 2.79 s; observation seq 71 was overwritten
unread and seq 72 was read by the play loop but never shown to the model; r25 was applied at
83.0 s and its 3300 ms delay went into the next prompt. Scripted, commander and the job and
episode lifecycle are drawn from the code. Reviewer: round 1, 145 claims: 137 confirmed,
7 wrong (seq 72 called unread, the old ledger drawn as holding, the menu-to-battle order,
provider errors all called forfeits), 1 unsupported, plus missing markers; round 2, 36 changed
items: 35 confirmed, 1 wrong; fixed after.

## 2026-10-31: multi-agent diagram page, Multiplayer tab (plan step 3)

Claude Code, $0, no game. The Multiplayer tab of [`docs/multi-agent.html`](../how-code-works.html):
21 boxes, 39 wires and four flows drawn from the code (start-up in its real order, one operator
command, close, compare-peers; illustrative, since no multiplayer battle has run). Its banner:
built offline, zero live multiplayer battles, one dry run on 2026-10-31 that reached the menu
and attached a worker. Reviewer: round 1, 170 items: 159 confirmed, 8 wrong (event order at
start-up, a heartbeat claimed to fail while close() still answers it, threads said never to wait),
3 unsupported, plus missing markers; round 2, 45 changed items: all confirmed.
Found on the way, not fixed: `link.py` documents that close() ends every lease, but a heartbeat
that arrives during close() is answered "renewed" and events can follow the "closed" record
(a scratch script showed the reply); no test covers it.

## 2026-10-31: multi-agent diagram page, Factory tab (plan step 4)

Claude Code, $0, no game. The Factory tab of [`docs/multi-agent.html`](../how-code-works.html): 23
boxes, 37 wires and two flows drawn from the code ("a normal change", "the WH3 experiment loop";
illustrative). It shows the gaps the plan names: git runs no hook on a merge that completes by
itself (the main session's Stop hook reruns check.py at the turn's end); main has no branch
protection or required checks (read-only GitHub API, 404 "Branch not protected"); CI runs after
a push and on each pull request; nothing makes a commit wait for the reviewer; version-review
adoption is unsettled. The viewer also gained tab banners, failed requests drawn as hollow red
dots, per-flow lane legends and markers, and a fixed tab order.
Reviewer: round 1, 101 items: 93 confirmed, 8 wrong (rules stated as facts, a flow that put the
commit before the review, a queue stop rule), plus missing markers; round 2, 49 changed items:
48 confirmed, 1 wrong; that and one missing marker fixed. Found on the way: the version-review
tie-break is untested (a planted mean-first sort passed all 7 tests).

## 2026-10-31: require nonempty evidence in collection assertions

Four capture faults passed all 4 original tests: disabled filename/path/battle-prefix
checks and omitted failed rows. The expanded 8-case group rejects them (4/2/2/5 failures)
using existing foreign files, separate parents and unchanged-destination bytes, plus
record count/identity checks. Existing valid-copy behavior still passes.
A never-update-follow-posts fault passed all 50 calibration cases; one added unit-set
assertion now rejects it. A second independently shaped fault is rejected too.
A ledger writer omitting successful check rows passed all 71 gate tests; explicit
declared-name sets now reject it (1 failed, 70 passed), while all 71 controls pass.
The saved Spire reference test now names its self-comparison as an acceptance control;
its assertions are retained. Focused groups pass 80 and 71 cases. No production edits.
Filtering long failure replies passed all 152 caller cases; an attempt/request-count
assertion now rejects it (1 failed, 151 passed), while all 152 controls pass.
Review caught a duplicated failure row that retained count; the trigger-sequence check
now rejects it. Eight new registered faults join the prior 159 unchanged. Cards,
before/after output and XML: `runs/test-quality-20261031/assertion-audit/`. These are
component/file-record checks, not live movement or screenshot verification; unagreed.

## 2026-10-31: run the old local-evidence cases from the audit worktree

Fourteen existing offline cases pass at `4856a6c`: saved siege/step-run wrong-value
controls, Land recount/classification, the old G1 replay, synthetic task regeneration
and the Spire v1 inventory reference. Eight stopped input roots were copied; all
328 files match SHA256/size before and after (656 original/copy checks). One embedded
late-rung path still reads the hashed original record; no paths or expectations changed.
Card, manifests, JUnit and raw output: `runs/test-quality-20261031/local-evidence-*`,
`local-extra-evidence.*`. These are recorded-case checks, not live-game or learning
verification. No game, model training, Windows call or paid request was started.

## 2026-10-31: invalid billing values cannot weaken the ledger cap

Private fake-response probes produced NaN spending and a negative cached-token charge;
both allowed an above-total reservation, including after reopening the private ledger.
Ledgers now reject invalid new/prior amounts without rewriting evidence; OpenAI usage
checks reject malformed counts, excess cached tokens and arithmetic overflow. The existing
invalid-cost path charges one reserved share, releases holds and stops before parsing or
retrying. Raw usage stays in the failed attempt; malformed usage is not totaled as tokens.
Added 32 cases; the first regression run failed 27 before the fix (69 passed), and the
expanded focused set passes 100. Valid token totals survive missing dollar cost. Sequential refusal sweeps caught all 4/11 old ledger/model
guards and all 5/16 after the change, with no hangs or misses. Five added registered faults
join the prior 154; one prior-charge plant target follows the validated constructor line.
Cards/output/review: `runs/test-quality-20261031/invalid-billing*`, `billing-*`,
`review/invalid-billing/`. No real API call or owner ledger was read or written. These are
component regressions, not live billing or price-estimate verification; the method is unagreed.

## 2026-10-31: browser checks handle empty facts and controlled route/navigation cases

The existing browser check timed out after correctly counting zero facts, then failed on
a recorded move already within the viewer's arrival region, then on a hidden single-scenario
index screenshot. It now reads facts only when present, runs the same pending-route assertions
on the existing invented demo, and captures the navigation appropriate to the scenario count.
All assertion expressions stay unchanged, as do app behavior, generator inputs and recorded jobs.
Route coverage rests on JUDGEMENT? `replay.js` Recent routes/Waypoint cutoff and the checker's
Route example: inherited display choices are marked, and demo selection awaits owner review.
Raw attempts/cards/review: `runs/test-quality-20261031/browser-*`, `review/browser-check/`.
The initial full-Chromium launch also failed on its long Unix socket path; the software
headless-shell run uses short `runs/tq-b` temporary storage. Windows native probes separately
passed 3 cases using private Python children (JobObject, locks, paths); no games launched.
Read-only doctor: ready, build 25961564, matching the pin. These are component/DOM checks;
collector semantics, real-game ownership and GPU rendering remain unverified.

## 2026-10-31: proposed CI jobs exercise the existing optional extras on CPU

The `check` job keeps its existing name and commands. A separate train/llm matrix installs
the locked extras, imports the required libraries explicitly, then runs the same gate.
Missing optional packages therefore fail a selected job before pytest can skip their tests.
CUDA is hidden, model loading stays offline, and Windows opt-ins are off. No runtime source,
dependency pin, assertion or benchmark definition changed. Pattern: PyTorch `lint.yml`.
Selection of both profiles rests on JUDGEMENT? `.github/workflows/check.yml` Optional CI;
it remains a draft for the owner's recurring-CI decision, not an agreed verification method.
Card, local profile commands, syntax check, Actions output and review live under
`runs/test-quality-20261031/optional-ci-*` and `review/optional-ci/`. No hardware or learning claim.

## 2026-10-31: cover uncaptured transport errors and mailbox publication locks

Fresh branch coverage identified two unexecuted error paths. Added cases require
an uncaptured transport failure to remain APIError with no parsing, retained uncertain
charges against the held reservation and released reservation; they also require whole-file
publication after a transient
replacement lock and visible failure with prior content intact after persistent locking.
The old 39 model cases accepted a removed re-raise; the old 17 mailbox cases accepted
immediate failure and suppressed final failure. Expanded model checks also cover the full uncertain-attempt limit.
Review found a positive-only spend assertion accepted undercharge; it now requires each
attempt's reserved share. Undercharge and ignored-count faults join the three initial faults
in the plants manifest,
with its previous 149 entries unchanged. No retry-count/delay constants are asserted.
Card/raw/review: `runs/test-quality-20261031/error-paths-*`, `review/error-paths/`.
Source, existing assertions and skips are unchanged. Simulated OS/transport faults provide
component evidence; actual Windows sharing, API billing and live behavior remain unverified.

## 2026-10-31: shared language/PPO fixtures leave collected test modules

The remaining five test-module import edges now point at four explicit support modules.
Twenty-five helper/fixture definitions moved; all 190 definitions in the eight affected
test files retain their ASTs, allowing only equivalent module-qualifier names.
PPO's combat-builder substitution and its collector remain in the same module globals.
CPU-train controls pass 622 tests with 22 skips before and after; recorded IDs/statuses
and the full locked-language suite are compared separately in the task artifacts.
Source, test assertions, skips and fixture scopes are unchanged. No blanket conftest or
autouse fixture was added. Pattern: Hugging Face datasets `tests/utils.py`.
Card/raw/review: `runs/test-quality-20261031/optional-helpers-*`, `review/optional-helpers/`.
These are refactor/component checks; engine behavior and learning remain unverified.

## 2026-10-31: separate capture-thread completion from copier polling in tests

The passive capture test copied evidence before joining its released screenshot worker.
A private replay delaying fake completion 2.2 seconds makes it hit the copier's real
2-second deadline; copying after context exit passes the same assertions.
A separate controlled-clock case publishes the sidecar during polling, preserving the
pending-callback check without a wall-clock race. A no-poll copier must fail that case.
Source, production deadlines and existing assertions stay unchanged. The worker's bounded
2-second event waits remain; this does not establish that all scheduling flakes are fixed.
Card/raw/review: `runs/test-quality-20261031/passive-capture-*`, `review/passive-capture/`.
Component evidence only; live screenshot behavior remains unverified.

## 2026-10-31: check archived source against the requested revision

The archive test covered only clean HEAD. A second real-Git case uses two commits
with changed, added, deleted and binary files, followed by dirty/untracked files.
Its expected paths and SHA-256 values come directly from known fixture bytes;
it never calls the production fingerprint function for its expected result.
The old case accepts three planted HEAD substitutions (path listing, bytes, both);
the expanded two-case suite passes unchanged source and rejects each wrong reader.
Raw/card/review: `runs/test-quality-20261031/archive-revision-*`, `review/archive-revision/`.
Existing tests, source, skips and dependencies are unchanged. This is component evidence;
archived live-training correctness remains unverified and the card was not owner-agreed.

## 2026-10-31: check local-model lease ownership at the loading boundary

Current source bypasses the lease for injected CPU loaders; a private-lock contention
probe agrees, rejecting the initial fixture-coupling suspicion.
All 37 existing policy cases accepted reversed selection, no default-loader lease,
and early lease release.
Two added private-lock cases require refusal before default weight loading, ownership
during loading/use, release on close, and an injected CPU model working while it is held.
Expanded policy run: 39 passed; the three wrong versions fail two, one and one cases.
Focused CPU policy/evaluation/catalog cases: 80 passed; review prompted the retention check.
Source, existing assertions and fixtures are unchanged; no actual GPU lease was held.
Raw runs, card and review: `runs/test-quality-20261031/gpu-*` and `review/gpu-selection/`.
The fault replay needs the CPU test environment; it is not in the default plants manifest,
whose ordinary environment lacks Torch. Hardware/CUDA behavior remains unverified.

## 2026-10-31: shared Spire evidence and catalog setup leaves collected tests

Shared builders/fixtures moved from `test_evidence.py` and `test_catalog.py` into
`combat_evidence.py` and `catalog_support.py`; seven consumers import support directly.
464 definitions match before/after, allowing only the named module qualifier renames.
Collected node IDs match in both environments: 422 default, 639 CPU train (import-time
skips are separate). No test, assertion or expected output was added or removed.
A dedicated environment installed the existing CPU train extra from the locked dependencies.
Combat/language/PPO runs before and after: 619 passed, 22 skipped each. Skips cover saved
engine evidence and missing optional language packages, not a Torch absence.
Raw collections, AST comparison, both runs, card and review: `runs/test-quality-20261031/`.
Full gate/main integration remain for the handoff. No source/game/prompt change, no learning
or live verification claim; five imports of optional training test modules still need audit.

## 2026-10-31: negative tests require the contract error type

Wrong-type `KeyError` variants passed the named checkpoint-injection and sampling negative
tests. They now require the parameter/protocol errors their callers handle, with separate
sampling seed/rejection tests and named checkpoint cases. The valid checkpoint control stays.
The export test's broad budget exception was already protected by a later exported-type
assertion; narrowing its earlier expectation improves readability, not coverage.
Focused run: 56 passed, two saved-checkpoint evidence cases skipped, including plant liveness.
Both formerly accepted variants now fail; the budget-type variant still fails, earlier.
Production source, error taxonomy and grid values are unchanged; two new plants preserve
these gaps. Grid use rests on JUDGEMENT `battle/checkpoint.py` dispatch, not a new agreement.
Card, before/after faults and review: `runs/test-quality-20261031/` in the isolated worktree.
Full gate and main integration remain for the handoff; no live effect or full coverage claim.

## 2026-10-31: testing audit finds attribution, budget and isolation gaps

Drafted in isolated `test-quality-audit` at parent `150ef84` while Claude runs live checks;
no production source, prompt, agreed method, game state or benchmark definition changed.
Cards, raw output and focused reviews: `runs/test-quality-20261031/` in that worktree.
Provenance: 20 cases pass. The old provenance test accepted six declared wrong versions;
the new cases reject all six. Independent review found the second-scope-entry gap, now
covered, and challenged a shortened default scope (five failures).
Retained budgets: two new tests plus 64 existing shared model/provider cases pass. Those
64 accepted both declared budget faults; additions reject both. Three more variants planted
by the reviewer also fail. These comparisons concern the named tests, not the whole old suite.
Spire helpers moved out of the lifecycle test: 275 test bodies and 87 helper definitions
unchanged; 415 collected node IDs unchanged. Focused run: 166 passed, one missing Torch
case and one missing original-engine-evidence case skipped.
Initial full gate: Ruff clean, 6 failed, 2073 passed, 69 skipped. Hook cleanup tests saw
Claude's live job and skipped their own stub. Isolating only the child's process scan
gives six focused passes; removing its production SIGTERM handler still fails as required.
Worktree gate: Ruff clean, 2079 passed, 69 skipped; main integration waits for live checks.
The handoff holds the raw output and final review. No live verification or whole-repo coverage
claim. Next: exception expectations (two wrong-type KeyError variants pass) and remaining helpers.
## 2026-10-31: multi-agent diagram page, step 1 (viewer, Overview, Team tab)

Claude Code, $0, no game; plan and evidence `runs/multi-agent-diagram-20261031/` (the owner's
decisions of 2026-10-31). [`docs/multi-agent.html`](../how-code-works.html) is one file of plain SVG and
JavaScript that opens from file://. It has tabs, a flow player that moves dots on one clock, lanes
and a side panel with each part's payload, status, judgement markers and source lines at `21f6204`.
Step 1 draws a boxes-only Overview and the Team tab (18 boxes, 26 wires). The scripted flow
replays 5.30-10.40 s of `team-live-20261031e` probe 1 by hand (one episode, not a measurement):
idle polls alternate with cavalry's no-ops while infantry waits 3 s, then the members alternate.
The model-team flow is drawn from the code, since that team has never played live.
Reviewer: round 1 checked 183 claims, 158 confirmed, 15 wrong (line refs, three stale statuses,
missing markers), 10 unsupported; round 2 found 30 of 32 changed items right; the last two and an
unsure-marker display were fixed. Numbers recounted from the traces (`team_numbers.py`).
Not checked: whether the page teaches well (the plan's stop for the owner's look; the run went
on under /goal). The page verifies no behaviour.

## 2026-10-31 (night): agreed live checks after the multiplayer merge; outcome readers; b52

Claude Code, 02:38-~09:50 (WSL clock), $0; brief, handoff, notes: `runs/overnight-20261031/`.
At `150ef84`: Land checkpoints passed (0 mismatches over 2,000/2,001 ticks, 9/9 readings per
restore, the changed restore diverged at 1303); scripted team 4/4; siege passed (4 states, 8
identical restores with 0 mismatches over 2,402-2,403 ticks, 194 readings); army setup failed
(the load phase's menu stopped after step 4 until the 600 s timeout; settings restored, all 7
fields). Observer smoke steps 1-4 dry run: worker hello matched build, exe and pack.
At `1cc4582` (all merges below): siege passed (8 identical restores, 0 mismatches over
2,400-2,404 ticks, 192 readings); army passed (save, load, reserves); team 3 of 4 (probe 3's
3 s delay lasted ~1 s of battle time while WSL's clocks jumped; Windows clock 1.0000); Land
failed at `35ade85` and at `2302d1e` (mod bytes of `150ef84`) on one unit's UI-card stats
(`StatList`) only: checksums, live readings and both restores equal.
Readers over 642 register rows differ on 3 timer wins, 8 controller failures, 5 wall caps;
none on the card's scenario (recounted). `cards.benchmark_outcome` v1 (`79834ad`, unused)
maps result.json to benchmark.md's outcome rows; 3 of 12 reader plants and 1 scorer plant
passed every test until 4 new tests. compare-peers fixes and a Lua-to-comparator seam test
(`b9e1cce`); b52: team episodes off the card board, `running_at_close` (`56d3937`), the engine
speed reading (`5067ba5`; probe 440/440 read 1). Plants 100 to 139, 139/139 caught at `1cc4582`.
Then `96bb137` (`play.py` keeps result.json on Ctrl-C during cleanup): all four checks passed (Land
0 mismatches and 9/9 readings; team 4/4; army; siege 8 identical restores, 194 readings).
The 10-30 factory items merged (`cbe73ea`: yes items once, Stop-hook log, scratch pruning,
one shared hook-test pass). Waiting: `wh3-team-report`, `team-check-battle-time`,
`land-check-stats-apart`, `gate-xdist`.
Unverified: the army stall's cause; a slowed battle's reading; any model team; real peers.

## 2026-10-31: factory checks require successful execution evidence

Owner: continue assessing the factory without manual review; essentially the whole codebase
is unreviewed. Workflow and both reviewers now trace consequential inherited assumptions to
a contract or independently checked example. Sync/text review cannot establish future compliance.
The normal gate refuses a zero pytest exit without a fresh named report, a passing test and
no reported errors/failures; incomplete runs issue no receipt or agreed-check credit.
Cards, references and raw output: `runs/factory-assessment-20261031/`.
Before: 4 regressions failed, control passed. First fix: 5 passed; integrated checks: 223 passed
before the review extension. Review found a named collection error counted as execution;
that and a contradictory failure report failed the first fix (2 cases). Revised cases: 7 passed.
The original 96 plants were caught at `9bd93dd`; four new variants were independently caught.
Final replay: 100/100 caught on copied working contents (`plants-after.json`, matching hashes).
Final gate: Ruff clean, 2106 passed, 43 skipped (`check-final.txt`, working contents, not HEAD).
Pushed `356e723`; CI passed clean there: 2058 passed, 69 skipped (no local evidence/Torch/Windows).
The earlier post-change replay was interrupted after the review finding and is not a pass.
No existing assertions, skips, agreed-check definitions or committed plants changed. The gate
warns about `pytest.skip` inside a new deliberately incomplete scratch fixture; no new suite skip.
Completion semantics rest on JUDGEMENT? `scripts/check.py` Completion evidence; checks proposed,
not agreed. Unverified: full collection, correct test expectations, fabricated reports, future
agent compliance and live effects. No game, Windows test process or paid API call.

## 2026-10-30 (afternoon): native multiplayer built offline, up to accounts and billing

The owner asked to implement the [plan](native-multiplayer.md) up to accounts and billing.
Built on branch `wh3-native-mp`, merged at `5d10e2a` ([status](native-multiplayer.md#implementation-status)):
platform detection (one code base for WSL and native Windows Python); the battle script's
`multiplayer` modes, `observe` (passive) and `control` (unqueued moves for the local army
only), with an evaluator-only `native` section; the coordinator/worker link and the
`coordinator`, `worker` and `compare-peers` commands. Five parts, each with an agent-written
card (not agreed), a review by a second agent and a fix round: 1 blocker (a lost status reply
could not be retried once the next command was queued) and 10 should-fixes, all resolved (one
by committing the marker it cited). Each bug fix has a test that fails on the old code (the
native lock's only in the opt-in Windows run, which check.py skips); test-only findings got
tests that fail on planted wrong versions. A final integration review and refusal sweep led to
`047c96d` (counts in the status).

Evidence, $0, no game, no account: 2 new opt-in tests on real Windows Python 3.13.1 (their two
files, 35 tests with the 3 opt-in ones, passed with `GAMEAI_TEST_WINDOWS=1`); one native run at
`b39a03d`, `--attach --mode control` on a fake bridge (move submitted, attack rejected; no
owned launch; timings in the status); WSL `flock` and native `msvcrt` locks on one file do not
exclude each other, and nothing enforces one kind of controller per PC. Mod pack sha256 changes
on merge, so single-player card-board setups split from earlier launches. Research (git-ignored,
checked by a second agent): price worksheet, lobby audit. check.py on this entry's content
(logged as `9faf92b` with this commit's 2 files), in the worktree: PASSED, Ruff clean,
1960 passed, 69 skipped (40 need torch; the rest local runs/ evidence or the Windows opt-in);
it lists 3 changes for the owner's yes (an agreed check's test file, a plant, a new skip).
Unverified: everything live (local_army values, ui_id across peers, replication, the cloud, the link).

## 2026-10-30: reuse completed passes and reject broken readers

Stop now adopts a completed normal gate pass on matching contents if lookup leaves its
identity unchanged, clearing old block flags without rerunning tests. A real current pass
previously still invoked the gate callback. Missing/stale/broken proof triggers checking;
an exit-0 checker without a matching record is incomplete. This uses the existing record.
Review probes found untracked directory/dangling links invisible to identity and reader
`SystemExit(0)` escaping validation. Identity now hashes tagged link targets; Stop falls
back on reader exits, preserves cancellation, and Git refuses an exiting checker import.
Cards: `runs/light-factory-20261030/reuse-card.md`, `identity-link-card.md` and
`guard-prep/reader-exit-card.md`. New cases failed first; integrated hook/sync tests:154 passed.
Fresh-context independent review: no findings, 23 new and 15 preserved cases passed; all
11 new wrong versions rejected at intended assertions. All85 earlier plants caught at `b6e42b0`.
Final gate: `runs/light-factory-20261030/reuse-check-final.log`; postcommit CLI smoke/handoff
alongside. Source/record semantics rest on JUDGEMENT? `scripts/check.py` Checked tree and
Concurrent passes, including private-notes exclusion. These checks remain proposed.
No game, Windows or paid API calls, $0. Native UI cancellation and deliberate bypasses remain
outside these component checks; final clean-revision offline proof and push/CI follow.

## 2026-10-30: exit-gate caller settings

Inherited `PYTEST_ADDOPTS` could select a passing test or file while omitting a failing test;
`PYTHONOPTIMIZE=1` could erase a failing assertion in an imported helper. Three actual CLI
fixtures passed, falsely credited an agreed directory check, and wrote records matching the
unchecked contents. The gate now removes those two settings from its subprocess environment.
Parent settings remain intact; the existing prompt-write and bytecode protections remain.
Card/reference: `runs/light-factory-20261030/env-card.md`, owner's full-suite rule, pytest
`Config._preparse` and local CPython behavior. Before: 3 new regressions failed. After:
16 focused cases passed; independent review found no issues and rejected both wrong variants
(2/1 intended failures). Actual CLI probes rejected all 3 cases, with no pass record/credit.
All 83 committed plants caught at `6955294`; the original prompt-protection plant is unchanged.
Final exit gate: `runs/light-factory-20261030/env-check-final.log`; raw audits/reviews alongside.
No game, Windows, paid API or benchmark changes; $0. Checks proposed, not agreed verification.
Controls cover these reproduced caller settings; deliberate plugin/config overrides are outside
this check. Next: final exact-revision offline check with saved evidence, then push/CI.

## 2026-10-30: exit-gate bytecode isolation

The ordinary exit gate could pass failing source or test edits when old `.pyc` files matched
their size and timestamp, then record the edited contents as checked. Two independent tiny
repositories reproduced the false passes; disabling bytecode writes alone still reused them.
Normal pytest now uses a fresh disposable `PYTHONPYCACHEPREFIX`, leaves shared caches intact
and removes its own prefix on return or a Python exception. No import hook or global deletion.
Card/reference: `runs/light-factory-20261030/bytecode-card.md`, workflow's final-state case,
CPython `Lib/importlib/_bootstrap_external.py` and local interpreter probes.
Before: five new regression cases failed. After: 13 focused cases passed; independent review
found no issues, three planted wrong versions failed their intended assertions (4/4/1).
All 80 committed plants caught at `94b0b8e`; new plants checked separately.
Final exit-gate output: `runs/light-factory-20261030/bytecode-check-final.log`; raw evidence
and reviews alongside. No game, Windows or paid API calls; $0. Checks proposed, not agreed.
Deliberate cache-setting overrides and plugin caches are outside these tests. Next: repeat
the offline gate at the final clean revision with saved-evidence copies; no live check claim.

## 2026-10-30: Stop-hook detection of live-check scripts

The Stop hook now recognizes the five direct live-check scripts as game jobs; their help
and evidence-recount commands stay offline. They directly own the game without a recognized
`-m` controller child, so the old guard missed all five. Card/reference:
`runs/light-factory-20261030/live-check-card.md`, agreed-check commands and their callers.
Before: 10 missed-command cases failed, 7 passed. Review found valid grouped Python flags
and abbreviated help/recount mismatches, then grouped `-hh`; added failing regressions and
used Python's standard `getopt` parser. Integrated hook/sync tests: 131 passed; review raw
outputs and five new plants are under `runs/light-factory-20261030/`.
All 75 committed plants caught at `77c2c03`; new wrong variants checked separately.
Final gate, with a fresh bytecode prefix: `runs/light-factory-20261030/live-check-final.log`.
No game/Windows/paid calls, $0. Component checks proposed, not agreed; actual battle timing
effects remain unverified. Arbitrary inline/wrapper launches remain outside recognition.
One invalid Python spelling conservatively overmatches; a second parser was not added.
Separate next card: stale bytecode can falsely pass the ordinary gate; reproduced on source
and test edits. A fresh cache directory per pytest run will close that demonstrated gap.

## 2026-10-30: commit guard adopted at the owner's yes

Owner: "Enable it (Recommended)". Adopted `commit-guard-draft` (`6958d6f`), configured
`core.hooksPath=scripts/githooks`. Git now refuses `git commit` without a current matching
`check.py` pass. Live no-record probe refused and left HEAD unchanged; raw `guard-live-refusal.log`.
Card: `runs/light-factory-20261030/guard-card.md`. Review found an old pass survived crashed
or interrupted runs; the repair clears it before normal work and after rejected arguments.
Help and plant replay retain the normal-run record. Five new abort/argument cases failed
before repair; final narrow repair tests: 10 passed; both new repair plants fail as intended.
Integration: 150 focused tests passed. The first run caught a TOML header lost resolving an
append conflict (1 failed, 145 passed); restored, retaining every original and added plant.
Symlink targets now count, including directory/dangling links; three retarget regressions
failed before repair, four symlink cases pass after. This covers shared skill directory links.
Concurrent passes rest on JUDGEMENT? `scripts/check.py` Concurrent passes: a genuinely passed
unchanged tree can retain that newer pass when another overlapping attempt aborts.
Final exit gate: `runs/light-factory-20261030/guard-check-final-complete.log`; reviews and raw outputs
are alongside. Checks proposed, not agreed verification; no game or paid API, $0.
Limits: explicit bypasses and other commit-making Git commands remain uncovered. Older
worktrees without the hook file need updating; the hash covers checkout contents, not an
older version left in the index. Draft-check logs archived before removing its merged worktree.

## 2026-10-30: Stop-hook interruption cleanup

The Stop hook kills and reaps its check process group on SIGINT or SIGTERM. Interruptions
are deferred only during process construction, until the child handle is available; the
original handlers are then restored and any pending signal delivered. Timeout behavior stays.
Card: `runs/light-factory-20261030/interrupt-card.md`; reference: check.py's plant-run cleanup.
Before the fix, both direct-signal tests failed with live children. Review found two more
startup windows and a leak in the regression's timeout cleanup; all were reproduced and fixed.
Hook/sync tests: 93 passed; six signal cases cover running checks, assigned handles and
constructor return. Independent review: real code 6 passed; no cleanup 6 failed; no SIGTERM
handler 3 passed/3 failed; no deferral 4 passed/2 failed. Every probe child removed.
Existing plants: 66/66 caught at `60f1eac`; three new plants exercised separately.
Final exit-gate output: `runs/light-factory-20261030/interrupt-check-final-atomic.log`.
Raw evidence/reviews in that folder; no game or paid API, $0. Proposed checks, not agreed.
Codex UI cancellation delivery and SIGKILL cleanup are not established; SIGKILL cannot run
Python cleanup. The approved commit guard is next; its review found a stale-record bug.

## 2026-10-30: Codex hook audit and concurrent-edit fix

Codex's live Bash hook refused one harmless `ruff format --help` probe. Its reviewer is
available and the refusal-sweep skill appears in its loaded catalog; agent-sync tests pass.
The Stop hook now rejects a passing run if the tree changed during it, caches no pass and
reports the final tree as unchecked. Its existing escape after one block is preserved.
Card: `runs/light-factory-20261030/card.md` (not separately agreed); reference: workflow's
final-state pilot case. New regression failed before the fix; hook/sync tests: 87 passed.
Independent reviewer: no findings; the new plant failed the regression (1 failure), real
code passed (1 test). Existing plants: 65/65 caught at `9c8e157`; new plant checked separately.
Offline suite: 1932 passed, 41 skipped (40 torch, 1 Windows opt-in). First exit gate failed
two Ruff line lengths, fixed; final gate output: `runs/light-factory-20261030/check-final.log`.
Raw evidence and review: `runs/light-factory-20261030/`. No game or paid API; $0.
Proposed checks, not agreed verification. Edits made and undone between fingerprints remain
undetected; this does not prove that every unchecked change is caught. Interruption cleanup
is the next separate card: direct-signal probes left check children alive, then removed them.

## 2026-10-30 (night): the light factory's checks checked

Claude Code, owner away ("light factory first ... more trust in these autonomous runs"); no game,
$0; merged at `c57098f` and after. Handoff, audit, reviews: `runs/overnight-20261030/`.
- Quick items: pid 159910 killed; the `d3ba6aa` Land pass recorded; 5 Spire log markers retired;
  `check.py` warns when state.md is over 120 lines (now 117, 120 with Codex's lines).
- The gate: 10 wrong versions of `check.py` and the hooks passed every test at `aefcaab`; new
  tests catch all 10. `tests/plants.toml` keeps 65 (65 caught at `607c431`); `--plants` copies
  saved evidence a plant names, so the siege spell-witness plant is kept.
- `check.py` names a linked worktree (64 skipped against 41) and a marker in log history; plant
  runs and the refusal sweep keep scratch in `runs/`; the Bash hook refuses pinned ruff formats;
  the version review counts a judge picking no candidate as missing.
- The reviewer's long-run question found the `ruff@` hole and 4 unreviewed commits on the 10-29
  run; its saved eval, rerun: 2 of 2 bugs found, no false alarm (3 cases).
- Land interview evidence notes, not answers: Q8, Q18, Q21, Q24, Q25, Q29, Q31 (`8eefc00`,
  `4d1d58c`, `bfad258`), each recounted by a second agent.
- `bed53ec` was committed on a FAILED check.py (fixed in `607c431`); a git pre-commit hook against
  that is a draft on branch `commit-guard-draft`, for the owner's yes.
check.py at `92ab398`, main checkout: PASSED, 1931 passed, 41 skipped; not at HEAD (Codex's
uncommitted docs). Not established: agreement on any check; the reviewer question beyond one run.

## 2026-10-30: native multiplayer plan refinement

Owner-requested documentation only: [plan](native-multiplayer.md) now specifies staged
setup, Google Cloud/airgpu runbooks, proposed fixtures/checks, Windows workers and private
transport, headless investigation, cost controls and later Tinker/Prime adapters.
Independent code audit found startup controller acquisition and unproved cross-peer
checksum/identity assumptions; the plan now requires passive observation and calibration.
Read-only executable/preferences inspection matched the pin and found visual-setting and
render-thread trace leads, not a working headless mode. Primary code reference: pinned PySC2
environment/multiplayer test; AI Arena is secondary. Sources: [references](../references.md).
Evidence/reviews: `runs/twwarhammer3/multiplayer-plan-20261030/`. Original 3 judgement markers
preserved; 7 proposals added (10 total). No check adopted or benchmark meaning changed.
Full gate at `75e9d09` with dirty documentation: Ruff clean, 1888 passed, 41 skipped
(40 missing torch, 1 actual-Windows opt-in); later final local-link check recorded in handoff.
Zero game launches, multiplayer battles, purchases, cloud resources or paid model calls.
Cloud compatibility, replication, unattended operation and headless performance remain
unverified. Plan awaits the owner's design/check direction before implementation.

## 2026-10-30: native multiplayer assessment

Owner-requested [feasibility draft](native-multiplayer.md): native LLM team battles with
unattended graphical clients look plausible; no supported headless route found. Read-only
inventory at `652e35d` matched installed build 25961564 and executable hash to the pin,
inspected six UI contexts and audited Lua ownership/timers. Current bridge refuses MP,
assumes army 1 and has no explicit network order path; native replication remains unknown.
Source audit independently repeated; official cost rates checked and arithmetic reviewed.
Evidence: `runs/twwarhammer3/multiplayer-assessment-20261030/`. Zero live multiplayer battles,
zero paid calls or cloud deployments. Proposed two-client checks are not agreed; no gameplay
result or results-register row. Client layout, probe scope and cost workload stay marked.

## 2026-10-29 (evening): the owner's light-factory answers carried out

Claude Code, after the owner answered the night's six decisions ([direction](../owner-direction.md)).
- `check.py` appends each run's agreed-check pytest results to `runs/checks/agreed-passes.jsonl`
  (`f4c2cd8`): the 7 commands run alone gave the record's counts. Entries with a live command
  are labelled "(pytest part only)"; a pass counts for a revision only if its files were HEAD's
  before and after the run.
- CI (`bcb874c`): `.github/workflows/check.yml`; the link test skips only links into
  `docs/thesis/`. A fresh clone on WSL with no git identity: 1821 passed, 64 skipped; a
  reviewer's runner-like clone (depth 1, empty HOME, no `/mnt/c`): 1833 passed, 64 skipped. On
  GitHub, 3 runs: passed at `da47cde` (1835 passed, 64 skipped); failed at `789043d` on a racy
  relay test (3 of 64 local runs under load failed it too; fixed in `e1d141c`, 0 of 128); passed
  at `e1d141c`. The capture and checkpoint-RL flakes in state.md's Known issues may hit CI too.
- Codex (`ae05c38`): `.codex/hooks.json` and `.codex/agents/reviewer.toml` mirror Claude Code's;
  `tests/test_agent_sync.py` checks the pairs and that each command finds its script without
  `CLAUDE_PROJECT_DIR`. The hook test now passes in a linked worktree (it failed 16 cases there).
- Small items (`11a5d6b`): the test-order fix, `gameai.lm.sample_index` deleted, two markers
  retired. Spire's end-turn allowance narrowed; `digest` warnings do not stop a queue.
- The owner's two process ideas ("Seems fine"): the marker list skips `docs/thesis/` (`a27c341`;
  the tree listed 3 problems, now 0), and `tests/plants.toml` keeps 44 planted wrong versions
  that `check.py --plants` replays at HEAD (`6c1273e`, fixed in `faf0805`): 44 of 44 caught at
  `faf0805`, each by a named test (`runs/checks/plants-20261029-224845-faf0805-161834.log`).
- Reviews: 5, with 21 findings (4, 2, 4, 3 and a three-angle workflow's 8, none refuted), all
  fixed but one limit (b51, below). Among the 8: six `check.py` plants had always counted as
  caught, because the stale-plant rule shared their test file. The planted wrong versions per
  area, all caught, are in `runs/light-factory-20261029-evening/` and `runs/plants-20261029/`.
- `runs/test-scratch/` was emptied by the owner (the permission check refused it to the agent).
Not established: Codex running the hooks (they wait for the owner's `/hooks` trust).

## 2026-10-29: 1x by the Windows clock (harness b51)

The owner's decision 2 (2026-10-29: "(a)", with the suggested 0.99-1.01 band). The mailbox
keeps each observation file's write time, read from the same open file (`os.fstat`). NTFS
stamps it from the Windows clock in 100 ns units, so WSL's slow clocks do not touch it. `play`
writes `windows_clock_s`, `windows_clock_ratio` (the battle's start to its last running
observation) and `windows_clock_range` (slowest and fastest stretch of at least 30 s; rests on
JUDGEMENT? `battle/play.py` 1x windows) to `result.json`. `digest` prints them and warns, on
the episode and above the job's table, when any of them leaves the band. `clock_ratio` (WSL
time) is unchanged.
- Offline probe, no game: four files written from Windows 5 s apart; two of the three gaps
  were within 0.01% of the Windows stopwatch, and the first was a cmdlet-load artefact
  (`runs/light-factory-20261029-evening/ntfs-mtime-probe.txt`).
- Tests: a 298 s battle with a 1.5 s pause reads 0.9950 overall, inside the band, and 0.9508
  in its stretch, so it warns; steady 1x reads 1.0000; a foreign or half-written file keeps the
  last time; a file the game replaces during the read keeps the read file's time. 13 planted
  wrong versions failed them (`plant-1x-round3.txt` there).
- Reviews (two rounds): a stretch ends at a controller read, so a 150 s model call still lets
  the same pause pass (0.9901). Not fixed: the line now prints the longest stretch and the
  marker states the limit. Plants reading the time by path, clearing it on a half-written
  file or closing stretches by battle time passed the tests then; tests now catch them.
  Battles under 30 s get no 1x reading (stamp and frame noise).
- Live, in the owner's window (2026-10-29 21:43, source `6f6b01b`, $0): `attack_nearest` on
  `emp-handgunners-grn-wolves-boyz`, lost by the engine at 418 s
  (`b51-1x-check-wolves-20261029`): 1.0000 battle s per Windows s over 413 s, 30 s stretches
  0.9998-1.0002 (longest 30.3 s), no warning. WSL's `clock_ratio` read 1.00005 over the same
  span. A first launch on `kho5-dwf5` failed lobby setup before any battle (it declares no
  funds: "cost 800, remaining 700"; job `b51-1x-check-20261029`).
Not established: one battle, one scenario, a scripted policy (model calls lengthen stretches);
no agreed check; that a real slowdown is caught (battles may not be slowed).

## 2026-10-29: refusal sweeps, boundary leaks and a decay check

Each refusal in a file was removed in turn (through the syntax tree, in a scratch worktree;
`runs/refusal-sweep-20261029/`), the suite rerun, then tests added for the misses. A skeptic
found cached bytecode had marked one Spire export site caught; every Python sweep was rerun
at `c358915` without caches (`head-summary.txt`), and 22 suspect earlier counts were rechecked
at their parent commits (`suspects-before.txt`): only that site was wrong.
- Caught now: WH3 `protocol.py` 38/38, `mailbox.py` 5/5 (3 by hanging), `play.py` 13/13,
  `setup.py` 40/40, `export.py` 17/17, `controllers.py` and `team.py` 15/15, `checkpoint.py`
  30/32 (one missed site is equivalent), `rl.py` 14/24, battle mod `error()` 39/39 and returned
  refusals 5/5, `pack.py` 2/3, `engine/runtime.py` 1/1; `gameai` 31 of 31 outside `windows.py`
  (2/5) and `lm.py` (1/4); Spire run loop,
  decisions, bridge and runtime 16/16, export 20/20.
- Left: Windows-only checks (3), the llm extra or a real model (`lm.py` 2, `rl.py` 9), an unused
  copy of `sample_index` in `lm.py`, the checkpoint agent's start, zstd, a synthetic draw;
  from the entry below, the siege spell witness, the step run's context rule, the win rate.
- Notable: a `None` reply crashed `protocol.py` (`b1aefe7`); corrupt traces stop exports
  (`a4a6011`); a choice the game did not offer is never sent (`82c8487`); the choice check
  behind each Spire training label is tested (`f00e88d`); a first checkpoint save off the
  reading grid is now refused before its source battle (`c358915`, a code fix).
- Spire's public boundary 3 → 6 of 7 planted leaks (`d50986f`); decay check: the ten
  2026-10-20 plants, rebuilt, are still caught (`runs/decay-check-20261029/`).
- Total (`runs/light-factory-20261029/tally.md`): 424 planted; the day's tests missed 215 (4
  equivalent or covered twice); new tests closed 190; 21 left. The 285 llm-extra tests that
  `check.py` skips pass in a separate environment (2140 passed, 1 skipped, at `6d3e612`).
Not established: live engine behaviour; that each refusal is the right rule.

## 2026-10-29: planted wrong versions against the agreed checks and results readers

The owner noted that agreed-checks.md is unreviewed; a check counts only after it fails on a
planted wrong version ([workflow](../workflow.md#checks-in-layers)). Plausible wrong versions
went into a scratch worktree (`runs/agreed-planted-20261029/`, `runs/readers-planted-20261029/`);
two reviewers reran the counts and planted 11 more.
- Five of the six offline agreed checks: their own commands caught 11 of 11. The sixth (engine
  ending kept) fails on its fix's parent `e041213`, as `b536ae6` records.
- Offline tests of the live checks' pass rules caught 3 of 12 (checkpoint, team, army), 1 of 8
  (siege) and 0 of 8 (step run, which no test loaded). New tests aimed at those misses and the
  reviewer's extra plants (`473fc5a`, `79626af`, `4c1fffa`, `24d9cd8`) catch 10 of 12, 12 of
  13 and 13 of 14: the gaps closed, not proof of strength on errors nobody planted. Two team
  plants are rejected by a second assertion on any acknowledgement the Lua produces; the
  siege spell witness and the step run's context rule stay uncovered.
- Results readers (`report.py`, `stats.py`): 5 of 13 caught, 12 after `dcbc588`; the
  win-rate denominator is left for the owner's scorer decision.
- The siege and step-run tests replay local evidence (skip without it) and add about 8 s to
  `check.py` (now about 27 s). Not established: that the pass rules are the right ones.

## 2026-10-29: light factory, stages 1-3

Owner, 2026-10-29: "Implement docs/light-factory-plan.md" (decisions 1 No, 2 Yes, 3 Yes); the
owner was away, so no card was agreed. Built: `scripts/check.py` (Ruff, the whole offline
suite, "needs your yes" warnings, a marker list), `tests/test_repo_rules.py`, an export leak
test, the review workflow's `incomplete` status, and `.claude/agents/reviewer.md`. The plan
became [workflow.md](../workflow.md); AGENTS.md went from 305 to 200 lines (its WH3 code map
moved to the [README](README.md#code-map)); the finished overnight plan and the 10-23 testing
findings moved into this log. Cards, planted runs and reviews: `runs/light-factory-20261029/`.
- Planted wrong versions: 7/7 mutations of the new code and 4/4 rule violations failed their
  tests; check.py exits 1 on a failing test or a Ruff error; an exporter that copies
  observations into rows fails only the new test (33 export tests passed it).
- Reviews: stage 1 found 4 real issues (an indented-away assert passed as a move; slugs taken
  for keys; a non-UTF-8 file crashed the warnings; a dropped "expand" clause); stage 3 found 6
  (a false claim that the team check times 1x by the Windows clock; a dropped "in force once
  the owner says yes"; sentences without a home; unmarked size rules); all fixed.
- Two markers (`overnight_allocation`, `first_frontier_pass`) moved with the finished overnight
  plan into this log, against judgement.md's "never ... log history"; only the owner retires them.
- Reviewer eval (n = 3, not told which cases were bugs): caught `b24df11`'s break and the
  10-23 dropped-ack fault with a failing scratch test; no findings on the clean `f653520`.
- The plan's "stills (none)" was wrong: a Lua test already feeds the stills director only
  visible units. Unverified: every new check is proposed, not agreed; hooks, skills and CI
  wait (stage 4); the experiment loop waits for a planned experiment (stage 5).

## 2026-10-28: checkpoint RL merged into main

Owner, 2026-10-28: "could we merge it now?" `wh3-checkpoint-rl` (22 commits) merged as
`6b942a3`; branch and worktrees removed (their `runs/` entries were links into the main
checkout's evidence, left intact). One conflict: AGENTS.md's old agreed-checks list; the two
owner-agreed checkpoint-RL checks moved to [agreed-checks.md](../agreed-checks.md). Spire's
`language/{policy,sampling,training}.py` stay as they were: its training audit requires them
byte-identical to recorded jobs, and the branch's move broke 11 audit tests; `gameai/lm.py`
keeps its own copies. The mod pack changes (injection export). Checks: main checkout full suite
1,633 passed, 41 skipped (torch); RL, checkpoint and language tests with the `llm` extra and
run evidence 348 passed; ruff passes. Decision 11's results and open choices are unchanged.

## 2026-10-28 afternoon: 44 judgement markers; stats keeps timing arms apart

Owner's `/goal` away window (13:07, 1-2 h); Claude Code; offline, $0, no game time. One
independent reviewer agent checked every batch; its findings are applied
(`runs/judgement-batch-20261028/review.md`).
- Markers: 44 over the play loop, controllers, report scoring, the mod, shared model code,
  post-training and Spire full runs ([register](../judgement.md#status-and-how-to-continue);
  a reason for every unmarked sweep candidate in `runs/judgement-batch-20261028/task.md`).
  Reviews found 5 wrong and 13 weak markers before they settled. No call decided.
- `stats` summary: added age and decision interval now split its groups (25 of 360 mixed
  them; 391 after). A regression failed before the fix. It also broke `test_wh3_play.py`'s
  exact row until `04e5adb`, a changed expectation in the agreed team suite (for review).
- Spire: the action and run-time limits have loop tests (each fails a plausible wrong
  version). Stale references fixed (agreed checks now in `agreed-checks.md`; "verified"
  wording without an agreed check); `state.md` trimmed to status (153 to 137 lines).
- Thesis (untracked notes): the EULA allows no data release without SEGA's answer
  ([note](../thesis/notes/release-terms.md)); a quadratic rout forecast beats the morale rule
  at matched recall but trades recall for precision at a fixed threshold
  (`runs/thesis-forecast-20261028/`); "3 of 5 moments flat" recounted and confirmed.
- Interview evidence (questions 13-17, 23 and 27, not answers): in 441 recorded battles 42% of
  friendly routs recovered but few stayed in action; wavering mostly lasts about 3 s; timer
  endings are rare (2-3%); no real healing seen (`runs/interview-evidence-20261028/`, every
  count rerun by the reviewer; a short-rout and a healing claim withdrawn).
- Unverified: all of it beyond the tests named; the full suite passes (1,562, 14 skipped).

## 2026-10-28 overnight: restore "pauses" were WSL clock steps; Land check passes at dcb8b5a

Owner's `/goal` night ([plan](#2026-10-28-overnight-the-saved-plan-moved-from-autonomymd-on-2026-10-29));
Claude Code, the only session; $0; one 12-minute game window. Evidence `runs/overnight-20261028/`;
two independent reviews (`review/`) reran the analyses and checked sources; corrections applied.

- Pauses: all 24 long WSL gaps in the 7 Stage 1 launches classify as WSL wall-clock steps, 0
  as stalls (the classifier passed 5 synthetic cases; 4 wrong versions each failed one).
  Battle time per Windows second was 0.9992-1.0002, and the unrestored source had the steps.
- Live: the agreed Land check (script as of `6cd5fbe`) passed at `dcb8b5a`: 0 mismatches over
  2,000 ticks, 9/9 readings, changed diverged at 1303, Replays unchanged. A Windows clock
  sidecar put WSL `monotonic` at about 0.936 s per Windows second and `time.time` steps at
  1.8-2.5 s every ~34 s, also without the game. Affected measures:
  [clocks](integration.md#clocks-measured-2026-10-28); nothing rescored; `JUDGEMENT?`
  `team_clock_band` marks the team check's band.
- Thesis ([index](../thesis/notes/README.md), untracked; 15 notes, 14 independently reviewed): in 441 recorded battles a
  morale < 0.5 rule warns 77% of routs 15-60 s ahead, so precision, not lead time, is open
  (a fitted model matched its precision in won battles, 5-fold job cross-validation);
  about 12% of 8,614 model decisions met a change they did not cause before applying.
  Shortlist and evidence: [directions](../thesis/directions.md#what-the-2026-10-28-checks-changed).
- Upkeep: inbox shortened (long items moved verbatim); prompts `TODO.md` answered; stale
  controller versions fixed; AGENTS.md points to the index. No branch, no `JUDGEMENT` batch.
- Questions, answered the same morning ([direction](../owner-direction.md)): direction 10
  stays a note; durations are measured in battle time ([clock rule](integration.md#clocks-measured-2026-10-28));
  `dcb8b5a` is recorded in agreed-checks.md; the team check's band stays, marked.

## 2026-10-28 overnight: the saved plan (moved from autonomy.md on 2026-10-29)

Saved 2026-10-28 at the owner's request; **ran that night** (02:39-04:35, at the owner's
explicit start). A rerun needs the owner's explicit start; record the start, return time and
game cutoff then. No clear game
window means offline work only. This is the selected mixed research/review plan, with $0
model spending and the conditional free timing diagnostic the owner selected. It does not
resume the stopped checkpoint-RL training or choose a thesis topic.

### Allocation and limits

Codex's time split (2026-10-28) within the owner's roughly ten-hour window; it was the marker
`overnight_allocation`, retired by the owner on 2026-10-29 after the plan ran. Another split
changes research depth versus review; these are planning ceilings, not required work counts or
verification thresholds.

| Allowance | Work and stopping point |
|---|---|
| 30 minutes | Recheck revision, processes, permissions, pending drafts and existing evidence. Record the task, responsible agent, absolute cutoff and one evidence directory under the main checkout's `runs/`. |
| 4 hours | Extend and challenge the thesis frontier map; retain a concise comparison and source-backed corrections. |
| 3 hours | Finish the bounded checkpoint timing investigation; at most 45 minutes of conditional live work, including cleanup. |
| 1 hour | Independent review of consequential research/timing claims, then targeted documentation, readability and workflow cleanup. |
| 1.5 hours | Consolidate results, run relevant checks, prepare up to three owner questions and leave the next concrete step. |

Ten hours is a maximum, not a target to fill. If timing work finishes early, use the remaining
research allowance for a named unresolved comparison. Stop when no permitted next step can
change a decision or finish useful work. Do not repeat unchanged audits to occupy the window.

Four unmerged draft branches were present at planning, above the older proposal's three-branch
cap. Preserve them; open no new runtime implementation branch in this plan. Attach findings
to the existing thesis/checkpoint work. No new dashboard, generic test framework, speculative
infrastructure or exhaustive repository sweep. New scripts need a named use in this plan.

### Thesis frontier

Codex's three areas (2026-10-28) for this first mixed night; it was the marker
`first_frontier_pass`, retired by the owner on 2026-10-29 after the night ran. A different
emphasis could surface other thesis candidates; this search does not rank or select the thesis,
and leaves the other documented directions open.

Start with the existing thesis notes and their research evidence; extend these comparisons:

- Checkpoint-based curricula and sample-efficient learning, including MARL and non-LLM
  policies. Distinguish demonstration-based starts such as
  [Backplay](https://arxiv.org/abs/1807.06919) from
  [reverse curriculum generation](https://proceedings.mlr.press/v78/florensa17a/florensa17a.pdf)
  and critical-state restarts such as [RICE](https://proceedings.mlr.press/v235/cheng24j.html).
  Restoration alone does not establish that a method's assumptions fit WH3.
- Heterogeneous teams, changing capabilities, coordination and unfamiliar teammates.
- Repeatable decision evaluation, counterfactual continuations and coordination under
  real execution delay. Keep decision-table evaluation distinct from closed-loop battles.

For each promising direction, record the closest primary sources and what they already
establish; the possible remaining contribution; WH3's useful properties and alternatives;
the robotics connection and its limits; required capabilities and missing evidence;
estimated game/data/compute cost; and the cheapest next step that could change the choice.
Check current literature and relevant methods/results, recording source versions, dates,
what was actually read and search limits. Abstract-only or inaccessible claims stay qualified.

Keep benchmark-only, learning-only and combined theses open. Distinguish centralized control
of several units from decentralized multi-agent learning. Treat the current support-prediction
proposal as one candidate. One failed training method cannot rule out RL, and an unsuccessful
literature search cannot establish novelty. Do not build an algorithm or collect a new dataset.
Update existing thesis pages; detailed evidence stays in the named `runs/` directory.

### Checkpoint timing investigation

Question: do the reported periodic pauses reflect simulation stalls, timestamp artifacts,
or evidence that cannot distinguish them? The planning review found a discrepancy between
WSL observation timestamps and simultaneous Windows native-tick timestamps in saved Stage 1
runs. This is a lead to reproduce, not a verified cause or proof of continuous 1x execution.

1. Recount the six completed attempts in `runs/twwarhammer3/rl/stage1-20261026/`, comparing
   observation battle times/`read_wall` with native ticks/Windows `wall_time`. Use the saved
   Land check `runs/twwarhammer3/checkpoint-check-20261025c/` as additional existing evidence.
   Preserve originals; retain a small reproducible recount and report counts, durations,
   largest gaps, offset changes, missing samples and concrete examples.
2. Trace timestamp producers and relevant consumers. Both existing wall timestamps use
   `time.time()`; native log timestamps come from the Windows Frida receiver, not directly
   from the simulation. Establish which written claims or timing measures depend on them;
   do not expand into a general timing rewrite or silently rescore old results.
3. Challenge the analysis with synthetic records: a wall-clock jump with continuous ticks
   and monotonic time; an elapsed-time gap without tick progress; missing/batched messages.
   It must distinguish supported cases or say "undetermined". Do not induce pauses in WH3.
4. If a named uncertainty remains, use the conditional live diagnostic below once. If the
   existing evidence resolves the question, skip live work.
5. Correct unsupported current statements and append a dated correction to historical
   claims, preserving the original evidence. Separate observed discrepancies, inferred
   causes and unresolved possibilities. Mark consequential choices at their proper sites.

The owner selected this diagnostic method on 2026-10-28:

- Run the unchanged [Land checkpoint check](../../tests/twwarhammer3/check_wh3_checkpoint.py)
  on main: source battle, two identical restores and one changed-order control. Its existing
  restoration verdict stays separate from the timing diagnostic; no RL branch is needed.
- Alongside it, a passive sidecar in the evidence directory samples Windows
  `time.time_ns()`/`time.perf_counter_ns()` at 10 Hz with sequence numbers. WSL records each
  received pair with `time.time_ns()`/`time.monotonic_ns()`. Keep native logs unchanged.
  Bound and clean up the sampler with the check; it sends no game controls.
- Compare within-clock elapsed intervals and offset changes with native tick progression
  and Lua battle time. Windows elapsed time is an independent clock reference; message
  arrival includes transport/scheduling delays. Sampling and receiver timestamps cannot
  establish absence of every simulation stall. Add no timing pass threshold.
- Allow one four-launch check, at most 45 minutes including cleanup, finished at least one
  hour before return. Do not start unless the whole bound fits. No automatic repeat.
  Respect harness refusals, unexpected closure and the existing safe-stop procedure. An
  unsupported checkpoint build blocks this diagnostic; report it without re-pinning.

If live work is unavailable or inconclusive, retain the offline result and exact remaining
uncertainty. Do not add a timing entry to agreed verification merely because the diagnostic
was permitted or passed its synthetic cases. The existing restoration method is unchanged.

### Checks and handoff

Use the behavior and independent references above; add no coverage-percentage target or
tests that merely mirror the implementation. Run focused checkpoint tests if their analysis
or checks change, documentation-link tests for documentation changes, and
`uv run --locked ruff check .`. Keep pytest scratch directories inside `runs/`. Report
commands, source revision/diff, input counts and passed/failed/skipped/unavailable checks.
Component tests do not establish live effects; new methods remain proposed unless agreed.

An independent reviewer challenges consequential research claims and timing conclusions.
Do not change benchmark meaning, scoring, observations, training gates, historical results
or agreed criteria without an owner decision. Cleanup stays within the touched material.
Assess workflow friction at handoff; retain only small, justified improvements and state
their observed benefit or uncertainty. Do not edit autonomy rules during the absence.

The morning handoff gives the research comparison and timing result, checks and limitations,
any small cleanup/workflow improvement, and up to three questions that unblock further work.
Keep the log summary within about 20 lines, link evidence, and update status with the next
step. Success is reduced uncertainty and manageable review effort, not hours occupied,
paper counts, test counts or newly created branches.

## 2026-10-28: Model team reviewed, cleaned and checked live (harness b50)

Owner, 2026-10-27: team work becomes a later arm on the Land Battle; rebase, clean and merge
`wh3-model-team` after one $0 live rerun; members see their teammate's condition
([direction](../owner-direction.md)). A read-only review (7 lenses, a skeptic each, a
completeness pass) kept 62 of 65 findings, none high; a second review of the changes kept 16
of 17 (`runs/twwarhammer3/review-team-20261027/`). Rebased onto `a938158`: one conflict in
`check_wh3_team.py`, resolved so its samples stay on `team.py`'s wall clock.
- b50: team tests moved to `tests/twwarhammer3/team/` (the owner's TODO); a failure
  collected at cleanup no longer replaces an earlier failure, and names its member; `digest`
  measures a member's delay from its own source state; the `--show` caption names the
  member; one forfeit rule and refusal acknowledgement; the unread `selected` event and
  `received_monotonic` dropped; `watch` counts every call's spend from model exchanges.
- `team_llm_rules` v22+t2 (input `team-v3`): ally rows add ammunition, fatigue and
  leadership with its largest effect (`team_member.txt` regenerated; other goldens unchanged).
- Checks at `3adbaa4`: full suite 1521 passed, 28 skipped; the agreed component files 123
  passed; ruff passed; each new or changed test fails on a mutant. Agreed live check 4/4 in
  about 12 minutes (`runs/twwarhammer3/team-live-20261027-rebased/`): clock ratio
  0.991-1.010, fast members 0.6 s, delayed 3.6-3.9 s, all truncated as designed, no game
  left. The saved runs of `45fe7b0` and `31823f3` recount 4/4. These rest on JUDGEMENT
  `team/check_wh3_team.py` member age witness and Movement witness.
- Markers added: five `JUDGEMENT` and two `JUDGEMENT?` in multi-agent-implementation.md,
  three in team-structures.md, one in the checker. Unverified: model members (never played
  live) and teamwork quality; the agreed files' moved paths and `project({...})` call sites
  await the owner's yes; on 2026-10-28 the owner let the assistant keep them and the other
  open items for now (state item 4). Merged after a second rebase onto `92ca8e2`, which
  changed docs only: the play-scope files are identical to `3adbaa4`'s.

## 2026-10-27: Thesis proposal revised; thesis pages moved to docs/thesis/

- Owner's request: improve the proposal, learn the possible directions and what WH3 offers
  robot learning, avoid hidden assumptions and overclaims. Moved both thesis pages to
  [docs/thesis/](../thesis/proposal.md) and added [directions](../thesis/directions.md) and
  [papers](../thesis/papers.md).
- Research workflow (7 researchers and a critic) and a review workflow (8 lenses: three
  citation checks, repo facts, assumptions, style, RPL and Stone readers); notes in
  `runs/thesis-research-20261027/`. Main finds: Barriga et al. 2019 already ran RL in
  Total War: WARHAMMER (pin-and-flank in a small scenario); Sellner and Simmons 2006 already
  predicted remaining durations to reassign running teams; robosuite's TwoArmPegInHole has
  no grippers, so the robot task must be built; RPL has no 2025–2026 multi-robot paper.
- The proposal now answers the owner's three in-page questions (training levels, senses of
  "unfamiliar", checkpoint use), adds reactive-repair and rule-ablation arms, a primary
  comparison, a timeline sketch and eight owner decisions. New markers: learning_level,
  support_label, heldout_senses, primary_comparison, timeline_gates, direction_ranking.
- Documentation only; no launches, paid calls or runtime changes. Checks: 72 doc-link tests
  passed, Ruff passed. These check links, not novelty or any research claim.

## 2026-10-27: Thesis proposal refocused on multi-agent coordination

- At the owner's request, rewrote the [proposal](../thesis/proposal.md) around learning when
  support between teammates will fail, and using those predictions to reassign work.
  Proposed collaborators are within RPL, with Peter Stone as the alternative supervisor.
- Checked primary sources for research overlap and current RPL membership. Adaptive
  allocation, learned feasibility and team generalization already have precedents;
  the proposed distinction and performance benefit remain unproven.
- Preserved the complete earlier proposal, findings and three judgement markers in the
  [memory investigation](../thesis/memory-investigation.md); updated its incoming links.
  Four new proposed choices are marked in the current proposal: coordination_question,
  coordination_method, coordination_experiment and coordination_transfer.
- Documentation only; no game launches, paid calls, training or runtime changes. New
  experiments and verification methods remain proposals.
- Checks: 69 documentation tests passed, zero failures/skips; Ruff and whitespace checks
  passed. These check links and repository hygiene, not research novelty or policy benefit.

## 2026-10-27: Memory thesis viability from recorded battles

- Memory-only overnight investigation; $0, no launches or runtime/register changes.
  [Proposal conclusion](../thesis/memory-investigation.md#conclusion-from-the-overnight-investigation-2026-10-27)
  contains the plan, methods, references, risks and next pilot; source baseline `a938158`.
- Census: 640 traces, 441 replay episodes/343 jobs, 175,694 frames. There were 767 completed
  visibility gaps in 159 episodes: median last-visible-to-return time 12.0 s, displacement
  30.5 m. Another 235 gaps are censored. No hidden-path or concealment-cause claim.
- 18,259 direct-model acknowledged decisions in 267 unpaused-config episodes: median engine
  observation age 4.4 s. Two-sighting extrapolation reduced median reappearance error to
  12.6 m but worsened its 95th percentile (112.5 → 134.1 m). Prediction, not gameplay.
- 34 sampled visibility bouts in 19 episodes fell wholly within a model request and were
  absent from policy inputs; 11 span multiple frames without fleeing flags. No harm claim.
- Evidence: `runs/twwarhammer3/thesis-memory-20261027/`; 2,173 input hashes unchanged;
  raw recount passed all 767 gaps/34 missed bouts and 100 sampled motion rows. Focused
  synthetic checks and doc links: 79 passed, none skipped; repo and analysis Ruff passed.
- New checks remain proposed; findings unverified under the owner's rule. No retrieval,
  ranking reversal, current commander, robot or policy-strength result. Wider primary-source
  research found overlap in retrieval latency, fresh-action checks and continuous collection.
  Recommendation: a memory-dependent decision audit with a motion-aware tracker baseline;
  rests on the proposal's marked direction/pilot choices and marked exploratory analysis.

## 2026-10-26: Checkpoint RL implemented and run: stage 3 fails, the policy collapses

Owner's goal: implement [the plan](checkpoint-rl-plan.md). Branch `wh3-checkpoint-rl` (unmerged;
changes the mod pack); evidence `runs/twwarhammer3/rl/`; choices made without the owner are in
`rl/plans/expansion-declaration.md`, each written before its result. 48 launches, $0. All
checks are proposals; nothing is verified under the hard rule.

- Stage 1 (7 launches): restores of a hold source's late rung matched the source after the
  handover (2,989 ticks, 297 observations, the ending); an order injected at tick 2102 applied
  at 210,400 ms as the grid rule predicts; identical attempts matched tick for tick. Passed
  after one rule change made on seeing the run (JUDGEMENT? `result_collapse`). Restored battles
  paused about 3 s every 35 s of battle time (corrected 2026-10-28: steps of the WSL wall
  clock, not pauses; [clocks](integration.md#clocks-measured-2026-10-28)). The agreed Land check passed again with the new
  mod (`d3ba6aa`, 0 mismatches, changed restore diverged at 1303); siege and team not re-run.
- Stage 2: the planned root was flat at rungs 2100 and 1200 (all win). Second root
  `emp-handgunners-grn-savage-orcs-hard` (hold lost at 347.3 s): rung 2700 has 3 winners and
  2 losers (`noop`, `fall_back_f2`), its repeat identical over 4,184 ticks.
- Stage 5 (14 launches): rung 2400 flat (all lose), skipped under a declared skip rule; rung
  2100 has 2 winners (`fall_back_f2`, `charge_f1`). Trained on 2700 and 2100 from the stage 4
  adapter (300 updates), mass at 2100 reached 0.375 (bar 0.8) and 2700 fell from 1.0 to 0.5.
  Not one action: starting saturated, Adam overshot into always choosing displayed slot 2
  (16/16 evaluation orderings), whichever candidate is shown there. The pre-launch checks
  refused the closed-loop launch, so the ladder ends there.
- Stage 4 (2 launches, run before stage 3): from 0.92 at the start, `exact_table@1` reached
  1.0 on the winners; a deranged control (rewarding `noop`) went 0.017 → 1.0 under 8 unseen
  orderings. The trained choice reproduced its audit attempt and won live; the control lost
  live, as required. The plan's first-order threshold (measured deviation 0) fails both runs
  on rounding; with a 1e-6 floor the main run passes and the control fails (6 of 54 updates).
- Stage 3 failed: the synthetic check (run with K 1, not 4, after measuring 0.41 s per
  ordering) collapsed onto `attack_nearest` within about 12 updates; held-out accuracy 0.42
  (the far share), training 0.49, bar 0.9. The one allowed re-run (300 more updates from its
  final adapter with a new optimizer, declared before running) left the policy unchanged (KL
  0.0000; gradient norm 1e-8): same 0.42/0.49. Both controls were stopped as moot. Stage 3 fails
  after its re-run, where the plan stops; the next step changes the method or its settings.
- Owner asked whether state is loaded wrongly: a 73-agent check (six lenses, three skeptics per
  claim; `rl/investigation-20261026/`) found no loading bug. Contexts match the Lua readings
  (0.05 m) and the source run; prompts carry the distance; scoring matches a slow reference
  (4e-6); adapters, reloads and hash chains are exact; every evaluation recounts. One records
  bug: `train()` wrote settings.K 4 for K 1 runs (fixed on the branch, `6d33b76`). Cause, by
  the evidence: the base model ignores the distance (P(fall_back) 0.063 near, 0.065 far) and
  the expected-reward gradient scales with the winner's probability, so far tasks dragged both
  classes onto `attack_nearest`. A skeptic's replay with −log π(winner) avoided the collapse
  but learned no near/far rule within about 110 updates (one seed).
- Simplest fix (owner: "Let's try the simplest fix. I'll leave it to your judgement"):
  `exact_table_log@1`, the log of the same expected reward (branch `887655d`; a 30-agent review
  confirmed the code and its tests now pin the divisor and the mean of logs, `69fc737`). Same
  start and settings: held-out 0.59–0.68 (bar 0.9), training 0.60–0.65; no collapse, and it
  picks `fall_back_f2` on 79% of near and 62% of far held-out tasks, against 62%/64% for its
  shuffled control (held-out 0.45–0.58, within its bar). Fails the check; a first attempt was
  killed by WSL's out-of-memory killer at update 86 while review agents ran beside it.
- Owner away ("use your best judgement and take note"): the plan's one re-run for the log
  method, at lr 1e-3 (owner's pick), went near-uniform (held-out 0.10–0.21). A declared 16-task
  diagnostic (training split only) fitted all 16 under 8 unseen orderings and reached 0.70–0.73
  on 184 unseen training tasks, but followed the spearmen's distance, not the handgunners'.
  The synthetic generator has that confound: an f1-only reader would score 0.90 training and
  0.93 held out, i.e. pass the gate without the intended rule. Stopped there, as declared.
- Then, still under that delegation, a de-confounded synthetic v2 (branch `5191f91`: half the
  tasks have the spearmen's distance class disagree with the label; v1 regenerates unchanged):
  the log method learned the training split (0.955–0.975) but reached 0.75–0.78 held out (bar
  0.9); its control stayed at 0.46–0.57. Generalisation finding: the plan stops before stage 4,
  so stages 4 and 5 for the log method were prepared but not run. Held out it is right on 0.99
  of far (150 m+) tasks but 0.66–0.71 of near ones, and 0.70–0.75 where the two units disagree.
  [Decisions](../state.md#owner-decisions-waiting).

## 2026-10-26: Checkpoint RL implementation plan

- Added [checkpoint-rl-plan.md](checkpoint-rl-plan.md), building on the handoff below. Owner
  (2026-10-26): plan only the first, simplest method, with a structure for testing and
  comparing later ones. The first method, `exact_table@1`, takes the exact expected reward
  over audited one-decision reward tables; tasks, task sets, a method registry, evaluation
  and comparison are shared by every method. Training actions reach the bridge mod at an
  exact engine tick through the agent's Lua hook and a new mod export, off the mod's 300 ms
  grid, so identical attempts are tick-identical and restore faults show in checksums.
- Checks: an eleven-launch live check of the step run; method-agnostic tests with a mapping
  control; a synthetic state-dependence check from the 338 recorded observations of the Land
  scenario (no game time) with a shuffled-reward control; an overfit check and a two-launch
  closed-loop check (the trained choice executed and compared with its audit attempt) with a
  deranged-table control. Sixteen JUDGEMENT markers; the owner decisions each stage waits on.
- Corrects the handoff where the code differs: the bridge mod starts during the fast rebuild;
  the agent's hooks reach the mod only through an export it does not have yet; no restore has
  reached an ending; the runner's limits are constants.
- Measured: handover about 50 s after the agent is ready (menu 29 s, load 14 s, rebuild 6 s),
  131–133 s per restore launch for 80 s of play, tick N = N × 100 ms
  (`checkpoint-check-20261025c/`); the mailbox apply delay is 300 ms in 34,645 of 35,041
  acknowledgements of the 33 zero-age `screen1-*` episodes (39 played); the mod's apply grid
  is 300 ms and, with `observe_ms` 1000 and no requests, it publishes every 1,200 ms.
- Ten mapping agents and five review rounds (thirty agents, each finding checked by a skeptic)
  checked the handoff and the drafts against the code. A chain design in an earlier draft and
  its markers `episode_form`, `descendant_check` and `chain_settings` were removed under the
  owner's words above. Documentation only, no runtime change, no launch, no training;
  everything in the plan is unverified.

## 2026-10-25: Checkpoint RL research handoff

- Added [checkpoint-rl.md](checkpoint-rl.md): a proposed local one-decision candidate
  policy, serial model/game phases, REINFORCE objective, collection contract and tests
  targeting likely numerical, attribution, timing, resource and split failures.
- Independent code/document review checked reuse, the objective and scope; clarified
  no-op evidence, cached-stat comparison and frozen-base tests. Corrected the stale
  checkpoint-limit sentence saying the completed siege check was still running.
- Six proposed judgement calls are marked in the handoff: `local_model`, `minimal_task`,
  `candidate_task`, `terminal_reward`, `candidate_reinforce`, `verification_plan`.
  None adopts a benchmark or new agreed verification method.
- Documentation-only checks: 66 document-link tests passed; Ruff and diff checks passed.
  No runtime change, game launch or training; WH3 RL implementation and learning remain unverified.

## 2026-10-25: Siege checkpoint checks pass for declared cases

- `2e2acbe`, `runs/twwarhammer3/siege-final-20261025b/`: 15 distinct completed logs,
  11 fresh launches and four reused with identical runtime, agent and full input/readings.
  Every planned tick/reading present; all games closed. All 812 WH3/doc-link tests and
  Ruff passed before the live check; committed-checker recount also passes.
- Helmgart defender 1 ram/1 tower, capital attacker 2 rams/0 towers, Helmgart defender
  1 ram/2 towers plus source-only field construction and scripted ownership changes.
  Four checkpoints: post-spell twice, open gate during construction at550, late at2200.
- Eight identical restores: zero mismatches over 2,400 planned native ticks each and
  194 live readings total. Changed orders at1200/1200/650/2300 first diverge at
  1207/1203/653/2303; no earlier drift. Raw cached-stat differences remain diagnostic
  under the owner's agreed method (12 of194 identical-restore readings).
- Positive witnesses: five living unit types, flying, ammo/damage, armour30→90→30 and
  expiry; ladder climbing; open/damaged/destroyed gates; equipment counts, construction,
  supply balances, scripted Key Building/Minor Supply Location owners in both armies.
- Independent direct-dictionary audit passes: 36,000 planned ticks and all 435 required
  readings present across 15 logs. Manual supplement below also passes. Eighteen known
  test replays archived unchanged; no game or replay-aside directory remains. $0.
- Coverage rests on JUDGEMENT `check_wh3_checkpoint_siege.py` `CASES` and
  `checkpoint_siege/ground_fire.lua` ground aim; other cases/builds remain unverified.
  Public-tool fixes are local, unreleased; a new release still needs its CLI smoke check.

## 2026-10-25: Recreated manual towers restore during construction and after completion

- The owner built two towers during `siege-check-20261025c/`'s first restore. Those new
  inputs invalidate its identical-order comparison; the timed run ended without saving
  after the clicks. Recreated the recorded slot/option choices from its tick-1100 parent.
- Source-only builds: slot1/option2 (2,000 supplies), slot0/option1 (500). The recreated
  tick-2050 choices, supplies and timers match the manual readings; original click ticks
  were inferred, not recorded. Saved construction at2050 and completed towers at3000.
- `fbdba3b`, seven launches: both identical restores at each checkpoint match all 3,300
  planned native ticks, 26/26 and 7/7 live readings respectively (66 readings total).
  No build commands were reissued. Changed orders at2150/3100 diverge at2154/3105.
- Independent `audit-2050.json` and `audit-3000.json` pass; cached stat differences retained
  separately. All seven games closed, no replay-aside directory remains; $0.
  Evidence: `runs/twwarhammer3/manual-towers-20261025/`. These recreated choices only;
  the remaining broad siege suite is still incomplete.

## 2026-10-25: Capital source needs an ammunition witness

- The first final-suite defender case passed, reusing its clean source. Capital restored
  exactly in both identical attempts (2,400 ticks/27 readings each); changed order at1200
  diverged at1203. The source never spent ammunition, so its required witness failed.
- Preserved `siege-final-20261025/`; this is missing coverage, not a restoration mismatch.
  Added a source-only cannon ground order and source-witness preflight before restores.
  Basic/field plans remain byte-identical. All 812 WH3/doc-link tests and Ruff pass;
  the new firing witness still needs its live check. Ground aim is marked as a judgement.

## 2026-10-25: Checkpoint review and siege checks in progress

- Agreed source/two identical/one changed restores, with positive unit/spell witnesses;
  added equipment counts, roles, field resources/supplies/owners, ladders and gates.
- Fixed save-during-rebuild and wrong-seed handover (two regressions), incomplete-trace
  false passes, and UTF-8 JSON decoding exposed by the capital siege (failed-before check).
  Existing Land evidence still passes the stricter recount. All 800 WH3/doc-link tests
  and Ruff pass before the live suite; focused regressions reject missing state witnesses.
- Public CLI draft writes metadata atomically and skips malformed records (3 tests pass);
  agent fixes copied by hand. Independent review found no further issue; not released.
- Original strict checks: Helmgart defender 1 ram/1 tower (source03), capital attacker
  2 rams/0 towers (source10); each exact pair matches all 2,400 planned ticks and 27 readings.
  Changed orders at 1200 diverge at 1209/1203. Spell armour 30→90→30, flying, damage,
  ammunition and supplies witnessed; source03CP1100 also has climbing and gate HP7548/9000.
- Field source11 has 1 ram/2 towers; CP550 has climbing, open intact gate and two towers
  constructing; CP2200 has climbing, destroyed gate and changed Key/Minor owners.
  Late restore matches 2,400 ticks/5 readings. Open restore matches all checksums, but four
  of 38 readings differ in cached infocard stats only; original strict failure retained.
- Owner chose live numeric morale/speed and armour/spell witnesses; cached stats reported
  separately. First expanded case (`e666012`) matched native/unit state but failed stale
  capture UI readings; all four launches preserved in `siege-check-20261025/`. Reader now
  asks updating `FillPercent` first: one restore matches all 27 siege readings
  (`siege-check-20261025b/`). Removed an extra all-unit cached-armour constraint; armour
  witnesses apply to the tested spell target, with unrelated infocard stats diagnostic.
  A failed case stops further launches. Interrupt cleanup now returns all replays before
  propagating the signal (four regressions failed before, pass after).
- The 15-launch rerun is next; capability speeds do not establish fatigue-adjusted speed.
  Evidence: `runs/twwarhammer3/checkpoint-siege-20261025/`, `checkpoint-review-20261025/`;
  $0. Three declared cases are marked as an agent judgement; no all-sieges claim.

## 2026-10-25: Battle checkpoints restore exactly through a fast rebuild

- Owner goal: battle checkpoint restoration for modders. $0, no production source/config
  change; lab tool `~/wh3-checkpoint-lab/ckpt/` (README, `FINDINGS.md` 2026-10-25 entries).
- A checkpoint is the game's replay file written mid-battle (setup and every input so far)
  plus the Lua random seed at tick 1. A restore loads it through the replay menu, clears the
  replay flag once the input session exists (live HUD, countdown clock, live scripts; the
  `debug_replay` switch covers the interface's own test) and sets the seed. It then rebuilds
  with inline ticks at about 9× real time: every rebuilt tick's native checksum must equal
  the saved one. At the checkpoint tick a live input provider replaces the replay one, and the
  loaded replay keeps recording. From then on the battle runs at 1x.
- Lab checks (`logs/ckpt-20261025/`): fixed later orders at fixed ticks in source and restores,
  then per-tick checksums plus Lua readings (position, facing, men, hit points, ammo, morale,
  abilities, winds of magic, kills, clock). 3-unit battle, checkpoints before contact and in
  melee; 20-unit battle with spells, AI shaman, artillery and cavalry. 22 completed restores
  had 0 checksum mismatches over the 200–1,951 ticks each ran after its checkpoint; readings
  differed only in Lua random draws (before the seed fix, and once from a wrong seed the tool
  passed). Five method variants failed or were refused by guards (in FINDINGS). Changed
  orders diverged (small battle from 1304 after an order at 1300; 20-unit battle from 1603
  after one at 1600). A tick-1 battle script's timers, orders and draws matched. Saves taken
  in restored battles restore exactly. Restored battles ended like the source.
- Standalone player tool, not published (`~/wh3-checkpoint-lab/release/wh3-battle-checkpoints/`):
  `save NAME` while playing; opening NAME from Replays restores it, checking each rebuilt tick
  against the checksums stored in the file. Lab tests through the harness (no orders, AI
  attacks): 3-unit battle restored twice, 20-unit battle once plus a chained save restored,
  each 0 mismatches over 2,200–2,400 ticks; an ordinary replay was left alone (700/700).
- Code merged into main (`battle/checkpoint.py`, `engine/checkpoint_agent.js`,
  [checkpoints.md](checkpoints.md)). Agreed check (owner, 2026-10-25) passed at `7b1e2ed`
  and at `6fdb271` (`runs/twwarhammer3/checkpoint-check-20261025c/`: 0 mismatches over 2,001
  ticks, 9/9 readings per restore; changed restore diverged at 1303). Not covered: real-time
  script timers, our bridge mod's state (fresh after a restore), the loading screen (shows
  the starting armies; parked by the owner), other battle types and builds.
  Owner, 2026-10-25: the rebuild may run above 1x before the handover; released the tool
  publicly (github.com/nivaldoh/wh3-battle-checkpoints, v0.1.0); check agreed once in the repo.

## 2026-10-24: Position, health and countdown restore witnesses

- Owner asked for movement, timer and health first, then stopped work for now. All 44
  continuation launches report closed; Windows process enumeration is empty. $0; no
  production source/config changes, commits or new agreed verification method.
- Direct simple01 saved swordsmen 83.419 m from their start at 32.8 s: health
  0.750080526, 68/90 soldiers. Two further movements displaced them 35.291/45.238 m,
  with lower health, before public teleport/heal calls in the same running battle.
- At two-second readback, position errors were 0.452/2.434 m; health was 1.0/0.505475044
  and soldiers 90/46. Neither attempt restored the saved values exactly. No tolerance
  adopted; these saved getters are useful failure witnesses, not full-state verification.
- Native countdown getter reads limit minus a mutable conflict-time field. Candidate
  direct restore has pointer/byte guards and independent Lua readback, but simple02 was
  interrupted during menu setup before battle: countdown writes and revised healing
  remain untested. Elapsed simulation time was not restored or cosmetically overwritten.
- Resume with countdown readback/advance/restore, then health and unit-centre discrepancies.
  Private evidence: `~/wh3-checkpoint-lab/REPORT.md`, `logs/resumed-20261024/`; no complete
  restore or impossibility proof. Broader projectile work waits behind these basic checks.
- Docs: 65 passed, none failed/skipped; Ruff and diff checks pass. These establish links
  and style, not checkpoint correctness. Profile scripts match their pre-probe hashes.

## 2026-10-24: Native worker boundary for checkpoint capture

- Direct projectile probes exposed an unsafe capture condition. Three source probes
  yielded no accepted active-effect pair: first the pending container was read, then
  duplicate slots and invalid environment headers were caught. Failures remain local.
- Source02 logged Lua/session work on thread 2680 and 130 primary constructor entries
  on17568. Its repeated module lookups also added overhead (native/wall ratio 0.767);
  the next observer caches definition identity. No pause or speed command was sent.
- Native code shows the session output flag is1 only after its step path joins and
  destroys the worker job. Phase01: 289 complete returns and 289 post-tick returns had
  null jobs and equal counters; 2,301 incomplete polls retained jobs. All checked headers
  looked valid in this cheap probe, so header validity alone cannot decide readiness.
- Source03 closed at 240.6 s: ready flag1, null worker job, equal counters at capture1900;
  14 projectile-class objects, all stationary there. Lua graph2,307,416 bytes; all1,900
  prefix hashes match. Offline mapping:44 permanents/1,579 light-pointer relocations.
- Source-derived target01 failed a timer metadata guard after graph installation;
  no accepted combined restore. Moving-projectile restoration remains untested. Evidence:
  `~/wh3-checkpoint-lab/REPORT.md` and `logs/resumed-20261024/` there.

## 2026-10-24: Checkpoint references and combined installation

- Five new $0 probes use the existing native replay capture and Lua graph, production
  sources unchanged. Fresh-process mapping covers 52 permanents, 38 native userdata,
  two threads and 1,587 light pointers. Detached decode retains the pending callback.
- First combined installation failed its native timer check: 40,350 ms instead of
  captured 40,250 ms. Corrected installation preserves the captured native deadline;
  both failure and correction remain in the lab evidence.
- Corrected run: all four native script-value maps and Lua CRT seed match at the boundary;
  callback pending at 70 s, fired by 90 s; stable through 180.2 s, 1,005/1,005 shared
  source hashes equal. Transient keys were restored; persistent maps already agreed.
- Second corrected installation: 899/899 hashes match before a new order at 90 s.
  Restored controller moves swordsmen 35.234 m; cavalry peer moves 0 m. Native hashes
  differ from tick 905; 4.8 m remains to the requested point, no arrival-precision claim.
- All 36 continuation launches closed, no native faults in these five probes, profile files
  unchanged. Real timers use a marked relative-clock choice; complete restores remain
  zero. Direct effects, soldier/order/AI state and full simulation RNG remain unverified.
- Docs: 65 checks pass after fixing a scratch-directory setup error; Ruff passes.
  No new agreed method. Next: native projectile lifecycle, then active-effect capture
  and repeated combined restores. Evidence: `~/wh3-checkpoint-lab/REPORT.md`, resumed logs.

## 2026-10-24: Native checkpoint continuation without deadline

- Owner removed the deadline; zero complete restores, no impossibility proof. Production
  code/configuration unchanged at `b0ac9e3`; private lab probes only, no paid models.
- ESF index covers 2,239 known caller regions (2,188 named); no complete codec pair found.
  Indirect routes remain. Two ownership probes show battle event/mod contexts share one Lua heap.
- Five movement handoffs: one guard refusal, two UI faults, two provider-only successes.
  Each success matched 400 prefix hashes and moved swordsmen 35.201 m; 851 shared hashes
  matched beyond the 600-entry recording. Lua sentinel absent in all 16 samples per success.
- Combat source/unchanged handoff: 2,403 hashes match, including 804 beyond the saved replay;
  ranged fire continued into melee, clock ratio 0.999983. Changed branch: fire-at-will off,
  ammo 1,455 vs 1,369 and changed combat. Native hashes exclude Lua state and are not complete-state proof.
- Lua graph/C-closure copies retain pending callbacks, shared upvalues and environments.
  Four isolated Lua RNG restores match the decoded recurrence; corrected handle inventories pass twice.
  Failures retained: DLL/float ABI, function environments, inline strings and `string.find` misuse.
- Two live Lua-root installations/refirings passed through 180.2 s after a late GC fault;
  the incremental-GC reference fails before the registry fix and passes after. Native time stayed advanced.
- Coherent capture: Lua 40 s/native next tick 401, with all 400 available source hashes matching
  its 401-entry replay. Native handle and timer rebinding remain; no direct effect-lifetime test.
- All 30 launches closed, $0, 1x. Evidence: `~/wh3-checkpoint-lab/{FINDINGS,REPORT}.md`,
  `logs/resumed-20261024/`. These diagnostics remain unverified under the owner's rule.

## 2026-10-24: Native checkpoint investigation

- Reused the committed Lua/harness sources at `b0ac9e3`; targeted Ghidra decompilation and
  Windows Frida probes on pinned Steam build 25961564. Report, addresses, hashes, scripts
  and private evidence: `~/wh3-checkpoint-lab/REPORT.md` and `FINDINGS.md`.
- Native replay writer produced six intermediate files; loading reconstructs tick zero.
  Two loads of the controlled Lua-witness file matched 591/591 and 593/593 native tick
  checksums (591 shared ticks equal), while its Lua marker was absent in 5/5 samples each.
  Source marker/callback control passed; shifted tick indexing produced 138 mismatches per
  load. These are diagnostic hashes, not full simulation traces or checkpoint verification.
- Two native XML exports held five unit records/91 elements each; only the moved unit's
  formation position/facing changed. Inspected multimodel, resync, drop-in and shroud paths
  did not supply a complete running-world reader/writer. Static coverage is bounded.
- 19 launches, 12 completed diagnostic windows, seven incomplete/failed; all closed, $0.
  Ordinary battles requested unpaused 1x; replay startup consumed about 50 native ticks
  quickly before steady 10 Hz, with no speed command issued. Invalid Lua controls were excluded.
  Original executable hash and two profile-script/154 save files match their baselines.
  No production code changed.
- No complete restore was attempted or verified. The stopping point rests on JUDGEMENT?
  `~/wh3-checkpoint-lab/FINDINGS.md` Search stopping point; it does not prove nonexistence.
  Repository documentation/style checks are recorded in the lab report; no agreed check added.

## 2026-10-24: Native checkpoint tool setup

Prepared `~/wh3-checkpoint-lab/SETUP.md`; preserved earlier notes and unrelated edits.
Reused Ghidra 12.1.4/JDK 25.0.5 and game copies; installed Universal Modder 0.2.0
(fal disabled), PyGhidra MCP 0.2.7 and Windows Frida 17.24.3. Codex 0.164.0 has goals;
the owner approved the lab launcher's session-only automatic approval review.
Static: one exported Lua function decompiled directly and through MCP; project retained.
Full executable analysis and code indexing remain unfinished. Native: one live attachment,
143 modules enumerated, detached; no hooks or restoration tested. Scope rests on
JUDGEMENT `~/wh3-checkpoint-lab/SETUP.md` Static witness.
Harness: existing `check_wh3_team.py` passed 4/4 fresh launches at `b0ac9e3`, $0, 1x;
clock ratios 1.054–1.056, all four games closed. Evidence: lab
`logs/setup-20261023/team-live/`. This rests on JUDGEMENT
`tests/twwarhammer3/check_wh3_team.py` Movement witness (existing motion can qualify).
Profile scripts match their backup; no source/runtime change or result-register row.
Checks: 65 documentation tests passed, Ruff passed, helper syntax checks passed.
New static/native smoke checks are not agreed verification methods; complete checkpoints
remain unverified. Restart action and permissions are in SETUP; no overnight goal started.

## 2026-10-23: Land Battle benchmark definition and plan

Owner: small mixed armies first; engine winner decides timer outcomes. Updated
[benchmark.md](benchmark.md) around battle success, army condition and separate diagnostics;
card admission and contact-only scoring stay historical. Recorded the direction and
reconciled the README, runbook, report/evaluation guidance, Empire/card pages and state.
Proposed first profile: see JUDGEMENT `benchmark.md` Starter armies, Starter settings and
Role coverage; no scenario/config or runtime change. Other new markers: Primary summary,
First diagnostics, First comparison, Launch sampling, Pilot size and Land Battle checks
(nine total). Their use remains proposed; the timer decision and small-army scope are agreed.
The plan names capture gaps, shared scoring, proposed checks, a free pilot, a bounded
comparison and evidence handoff; RL shaping is separate. Historical c1 remains untouched.
Validation: 64 documentation-link cases passed, no failures/skips; Ruff and diff checks
passed. Readbacks/configs checked against source; no game, API calls or new register rows.
New verification methods remain unagreed; no gameplay/readiness claim.

## 2026-10-23: Live-check audit and free army rerun

Compared the army, team and offline recount checks: [scope and gaps](#wh3-live-check-comparison-2026-10-23).
Army startup now refuses doctor blockers, prints warnings and checks for Spire before each
launch, restoration included. Both live checkers now use Windows paths for process matching.
Moved army orchestration tests out of Lua tests; renamed the unchecked restart-settings
observation and removed its persistence claim. Agreed acceptance assertions are unchanged.
The agreed army `--integration` check passed across four launches: ten saved units, three
mounts, ranks 0/1/3/9, attack/defence and relative leadership bonuses, recruitment refusals,
seven reserves, and exact original-settings restoration. Post-run: no WH3/Spire process or
session file. Build `25961564` matched its pin; $0, no scored battles or register rows.
Run: `runs/twwarhammer3/army-check-20261023-eval-review/`; sources are `4a6033f` plus the
recorded review diff. Executed checker SHA starts `0e0e6824709d`; its saved bytes match.
The later Windows-path correction has component evidence, not another live rerun.
Checks: 675 WH3 + 64 documentation cases passed, no failures/skips; Ruff passed after fixing
one import separator. Four guard cases failed before the first fix; three path cases failed
before the correction. Independent reviews found that path defect; no remaining blocker.
Evidence, executed checker and diffs: `runs/testing-wh3-live-20261023/`.
New marker: JUDGEMENT? `integration.md` Runtime speed fields; constant fields cannot detect
slowdown. Visibility, other order effects, rematches and model strength remain unverified;
new check methods remain proposed. No scoring choice or historical verdict was changed.

## 2026-10-23: WH3 eval and test consistency review

Offline follow-up on `4a6033f` plus the pending test cleanup. Fixed distinct job directories
being collapsed by basename; counted late captured model calls once in report latency and
kept transport failures separate from replies. Card output now distinguishes rows/launches,
cycle attempts/achieved movement and a timing proxy/measured age. Team recounts read only
unless given a new output file, which records the running checker and input-byte hashes.
The delayed-input regression now catches stale scoring totals with a current timestamp.
A six-case invented-job audit reproduced card/report/HTML/export disagreements;
[findings](#wh3-evaluations-and-tests-2026-10-23). Scoring rules and c1 stay fixed.
Review markers: `cards.py` Cycle signature, `report.py` Report denominator,
`report_assets/report.js` Timer wins, `export.py` Training split,
`check_wh3_team.py` Movement witness, and evaluation-guidelines.md Scorer version check.
Interpretation rests on those JUDGEMENT sites; none is approval of a new rule or check.
Checks: 670 WH3 + 64 documentation cases passed, no failures/skips; Ruff passed. Before-fix regressions
failed for launch identity, late-call accounting and recount overwrite; stale-total mutation
missed by the old test is now caught. Saved team evidence recounted 4/4 with original hashes
unchanged; c1 still admits (30 rows, 20 launches). Independent final review resolved its findings.
Evidence: `runs/testing-wh3-evals-20261023/` and `runs/testing-eval-review-20261023/`.
No game, paid call or full-browser check ran; new verification methods remain unagreed.

## 2026-10-23: WH3 test review

Test-only work on `4a6033f`: added foreign job/battle delivery and acknowledgement-identity
cases; execute Lua finish instead of searching its text. Controlled terminal-call timing,
registered commander-test worker cleanup, named Lua errors, and moved unchanged shared
mailbox/config out of `test_wh3_play.py`. Prompt writing now requires `WH3_WRITE_PROMPTS=1`;
a disposable regression reproduced `=0` overwriting expectations before the fix.
WH3 suite: 661 passed before, 664 after; 64 doc checks passed; zero failures/skips. Ruff passed.
All original test names remain; shared helper/config syntax is unchanged except its docstring.
Six deliberate faults were detected: unrelated ack accepted, terminal call charged to battle
time, replay omitted, result published early, foreign job accepted, old battle accepted.
The ack fault previously passed 115 cases; after, 1 failed/115 passed. The time fault failed
both cases. Each Lua fault failed 1/3 cases; baseline and valid swapped recording order passed 3/3.
A disposable teardown probe deliberately failed with two gated workers; its follow-up
confirmed both stopped, and an unfinished-wait probe failed as intended (1 failed, 2 passed).
Evidence/scripts: `runs/testing-wh3-review-20261023/`; [findings and guidance](#wh3-follow-up-2026-10-23).
New checks rest on JUDGEMENT `tests/twwarhammer3/test_wh3_play.py` Acknowledgement identity,
`tests/twwarhammer3/test_wh3_mailbox.py` Foreign-order check,
`tests/twwarhammer3/test_wh3_battle_lua.py` Terminal recording check; draft guidance rests on
JUDGEMENT `docs/testing.md` Agent review workflow (four new markers).
New verification methods remain unagreed. No runtime/prompt snapshots changed; no games,
paid calls or browser checks ran. Recount provenance remains a documented gap.

## 2026-10-23: testing review findings (moved from testing.md on 2026-10-29)

Initial review scope: file inventory and selected tests at `16ed4fe`, including the owner's local
review comments. There are 80 `test_*.py` files with 956 test function definitions; pytest
expands parameterized cases and skips unavailable modules, so these are not execution counts.

| Finding | Evidence and consequence |
|---|---|
| Useful tests already exist | [Bridge tests](../../tests/engine/test_bridge.py) exercise real sockets and the relay subprocess. [Mailbox tests](../../tests/twwarhammer3/test_wh3_mailbox.py) exercise files and Lua. They check these boundaries without launching a game. |
| Game ownership was hard to see | Spire's tests occupied six top-level directories plus two root files. The first cleanup moves those files to `tests/spire/`; the other directories still need organization. |
| Shared setup is hard to find | Twelve import statements originally pulled helpers or fixtures from other `test_*.py` modules; the two cleanups remove six. [pytest configuration](../../pyproject.toml) still supports the remaining cross-directory imports. |
| Some tests ask too many questions | The API-key test in [test_model.py](../../tests/gameai/test_model.py) checks key loading, a transient retry and redaction. The first episode test in [test_wh3_play.py](../../tests/twwarhammer3/test_wh3_play.py) also checks trace order and formatted digest text. Failures are harder to isolate. |
| Passing does not settle the rule | [Card tests](../../tests/twwarhammer3/test_wh3_cards.py) enforce admission choices that await the owner. Their interpretation rests on JUDGEMENT `src/twwarhammer3/battle/cards.py` chariot gate sizes. They can test implementation consistency without validating the choice. |
| The default run has important limits | Collection found 1,410 cases and skipped 11 whole modules because PyTorch was absent. The browser script and live-game checks are separate commands. No coverage measurement or CI workflow is configured in this checkout. |

The five sampled modules for model transport, sockets, mailbox, order validation and WH3
play passed **179 tests**, with no failures or skips. That establishes those examples pass
in this environment, not that every test has a sound expected result. Logs and collection:
`runs/testing-review-20261023/`. Line and branch coverage were not measured. The initial
lint check found four long lines in the owner's pre-existing TODO comments; wrapping them
preserved their wording and made lint pass. All 64 documentation checks passed, and the
Python example below ran successfully. Live-game, browser and optional training checks
were not run for this review.

### WH3 follow-up, 2026-10-23

The next review sampled WH3 boundary tests at `4a6033f` and ran all 661 WH3 cases before
changes. Independent reviewers challenged the tests with deliberately wrong implementations.
These findings concern test quality; no production defect was demonstrated by the mutations.

| Finding | Change or remaining gap |
|---|---|
| Dropping acknowledgement request matching still passed all 115 play/team/controller cases | Added a sequence with foreign, repeated and matching acknowledgements; it checks decisions, sent orders, feedback and delay. |
| Commenting out the terminal replay call still passed its source-text test | Execute production Lua and observe both recordings before publication, allowing either recording order; repeated finishing must not publish again. |
| Foreign job/battle rejection had no real-file Lua case | Added both identities and a subsequent valid request, checking rejected traffic cannot replace pending orders or reserve the next ID. |
| Terminal-call timing depended on finishing within 50 ms; commander cleanup followed assertions | Use a controlled clock and register worker finalizers when constructed. Bounded waits now report unfinished work. |
| `WH3_WRITE_PROMPTS=0` overwrote expectations; shared setup came from another test module | Only `=1` now writes. Verification runs without that flag. Moved the unchanged mailbox/config to the existing support module; no WH3 test imports another test module. |
| Team recount loses the old verdict without recording the new grader identity | Fixed in the eval/test follow-up below; the live acceptance rule is unchanged. |

Evidence, check counts and limits are in the [WH3 log](log.md#2026-10-23-wh3-test-review).
The three new cases and executable recording check remain proposed, not newly agreed verification.

### WH3 evaluations and tests, 2026-10-23

Compared the card board, text/JSON report, HTML view, register and model-decision export
using the same six invented outcomes. The reference is the documented contact-win rule
and the owner's 2026-10-21 phase rule for the **next** evaluator. The current readers differ:

| Case | Card | Text report | HTML view | Register / export |
|---|---|---|---|---|
| Contact win | Win | Win | Win | Raw win |
| Timer win | Loss | Non-win in denominator | Win | Raw win |
| Draw | Loss | Draw in denominator | Draw | Raw draw |
| Terminal failure in battle | Forfeit | Outside denominator | Omitted | Failure / no gameplay outcome |
| Constructor failure | Excluded | Outside denominator | Omitted | Failure / no decision rows |
| Cleanup failure after a recorded win | Forfeit | Outside denominator | Omitted | Failure / no gameplay outcome |

The last two cases still need the next evaluator: an unsuccessful construction attempt and
the preserved engine win, respectively. Export's inventory retains the complete result,
including `engine_ending`; its raw outcome fields are not card scores. A constructor with
no decision cannot supply a training row. HTML's completed-battle view was owner-directed;
adopting a benchmark view is a separate choice. Do not make a consistency test silently
choose one reader's rule, or freeze known discrepancies into new regression expectations.

Concrete fixes: launch identity now uses resolved directories, not basenames; recounts
preserve original verdicts and hash their checker and input bytes; late captured model
calls enter report timing once. The delayed-input test now varies hidden scoring totals,
so retaining stale totals fails even when the final timestamp is current. Card output
distinguishes controller/age rows from launches and calls cycles v1 an attempt count.

Owner review remains at the marked sites: the report denominator, HTML timer wins, export
training eligibility, cycle and movement witnesses, and the proposed scorer hash check.
The existing gate-size marker remains. Shared scoring needs a versioned adoption that
preserves c1. Remaining gaps include study/stage provenance, held-out enforcement,
condition identity, live visibility/order effects and agreed scorer examples; their scope
is in the [evaluation guide](evaluation-guidelines.md#12-where-to-enforce-first).

Evidence: `runs/testing-wh3-evals-20261023/reader_audit.py` and `reader-audit.json`;
the HTML predicate ran in Node, not a browser. Component checks and fault challenges are
recorded in the [log](log.md#2026-10-23-wh3-eval-and-test-consistency-review).
New checks remain proposed, not newly agreed. No game or policy-strength claim follows.

### WH3 live-check comparison, 2026-10-23

These checks answer different questions. Use the existing evidence before spending more
game time; a new battle is useful when it can resolve a named uncertainty.

| Check | Independent reference and what it can establish | What remains outside it |
|---|---|---|
| Army/setup `--integration` ($0, four launches) | Declared rosters/ranks versus lobby and battle readbacks; lobby attack/defence versus battle values; original versus restored settings | Order effects, visibility, rematch starts, graceful-exit persistence, real clock speed |
| Scripted team ($0, four launches) | Unit identity and positions after the matching acknowledgement, before its peer completes; battle-clock progress versus elapsed time | Attack/withdrawal/cast effects, hidden enemies, model-team performance; the movement rule rests on JUDGEMENT `tests/twwarhammer3/team/check_wh3_team.py` Movement witness |
| Card/reader recount ($0, no launch) | Recorded outcomes and independently labelled cases versus a declared scoring rule | Whether the original order caused the observed effect; a fresh game build or a changed scenario |

The army checker formerly ignored doctor blockers and hid executable-hash warnings; its
launch helper also omitted the Spire conflict check. New regressions reproduce these
failures and cover both refusal and a usable environment. Its orchestration tests now live
beside the checker rather than among Lua-script tests. Acceptance criteria are unchanged.

The old `persisted_settings` output was an observation, not an assertion. In the saved
`integration-review-20261019/live-r8` evidence it equals the original settings, although
the previous phase ended with disturbed settings. The new name, `restart_settings_observed`,
and docstring state that limit. Saved-army persistence has separate roster/rank assertions.

Remaining live work is the [proposed correctness checks](benchmark-implementation.md#correctness-checks-to-agree):
visibility needs a game-visible reference, and attack/withdrawal/cast effects need observed
effects, including an accepted order that fails to achieve them. The existing chariot
labels are the starting evidence for withdrawal. Changing their thresholds, the team
movement witness or the treatment of slow game clocks needs owner judgement. Paid model
calls are unnecessary for these engine checks; provider behavior and model-team strength
are separate studies. The current speed assertions rest on JUDGEMENT?
`docs/twwarhammer3/integration.md` Runtime speed fields. Live rerun evidence is in the
[log](log.md).

## 2026-10-23: native checkpoint feasibility

Owner requested a fresh assessment of native reverse engineering and tooling. Read-only:
no game launch, native module installation, executable modification or paid call.
Installed build `25961564` and executable SHA256 match `runtime.PINS`. PE inspection found
123 named Lua exports, including `luaL_register` and `lua_pushcclosure`; no root-level PDB
or COFF symbols. These are integration entry points, not battle-state save/load functions.
ASCII strings include `constant_random_seed`, `EMPIRE_REPLAY`, `SAVED_TICK` and `QUEUES`;
their names establish no complete serializer, RNG restoration or live behavior.
[memreader Plus](https://github.com/PKozdra/memreader_plus/tree/eae853af5b977ee36bc273c8e380745b2783a1f5)
has Lua registration, native calls and hooks in source. Its Lua hook callbacks skip other
threads; compatibility and checkpoint use were not tested here. No usable complete-state
loader was identified. Finding an existing paired serializer/loader remains a hypothesis;
building one would also require hidden simulation state, RNG streams and coherent timing.
[Ghidra](https://github.com/NationalSecurityAgency/ghidra) supports scripted/headless analysis;
not found on PATH or in checked tool directories. Available Java is 8; current upstream
instructions require JDK 25. Native instrumentation would run on Windows, alongside WH3.
No repeatable restoration check is agreed, no route adopted, no judgement markers added.
Documentation checks: 60 passed; lint failed on four pre-existing owner annotation lines.

## 2026-10-23: battle rewind investigation closed

Unsuccessful: no direct intermediate battle-state load or native RNG restoration was
achieved with the current harness. The implemented draft repeated an opening at 1x;
the owner correctly rejected that as a substitute for jumping into a saved state.
Ten scripted loads used about 33.5 minutes of ownership and $0. Three same-file loads
matched 1,100 ticks through contact/damage, but every load started at the beginning.
API/UI audits and two parsed replay files identified no usable complete-state loader.
This is a failed implementation attempt, not proof that all possible approaches are
impossible. The owner ended this session's investigation; decompilers are for another
session. No further reverse engineering or VM work is active.
Cleanup removed the unmerged `wh3-rewind` branch, its plan, probe files, test scratch
and owned runtime leftovers. The installed mod was rebuilt from unchanged `main`
sources. The detailed local evidence was deliberately removed during cleanup; these
historical counts do not establish a verified reset feature. No benchmark rows added.
Cleanup checks: 59 doc tests passed; installed pack contents match all five main mod
files. Global lint still flags unrelated owner annotation lines; those edits are retained.

## 2026-10-22: the script commands the AI's army

Owner request: a mode where the owner plays against the controllers ([plan](multi-agent-plan.md#d-single-client-steps)).
Branch `wh3-human-opponent` at `de37005`: a session switch `control: "enemy"` gives the
controllers the AI alliance's units and judges sight, role, sides and result from that
alliance. $0 probe, one launch per arm, nobody playing the player's army, 1x, scenario
`emp-helblaster-brt-raiders` checked side-swapped (both arms passed it: the AI's three
Bretonnian units as friendly, role attacker). Evidence and script:
`runs/twwarhammer3/human-opponent-probe/`. Reference: uncontrolled, this AI ran 30-93 m in
its first 11 s (`bench-b16-s4-floor-20261017`).
- `hold`: **failed** its preset rule (every unit within 5 m). At the first battle
  observation the three units were already running; they stopped within 3.6 s after 4-7 m
  and then stayed within 0.1 m for 130 s (clock ratio 1.0002).
- `rush_nearest`: passed. 518 polls, 0 refused results; melee, rout, rally and new attack
  orders, a new target after the first routed; ended at 158 s as `lost`, matching the final
  count (0 active units against the player's 2; clock ratio 1.0001).
Unverified: whether a person can command the player's army in this mode, sight beyond open
ground, abilities and magic (still read from the player's army), and anything beyond one
launch per arm.

## 2026-10-22: the starting-set screen

Overnight, decisions delegated ([direction](../owner-direction.md)); $0, game 02:37-07:28,
all scripted; evidence in `runs/twwarhammer3/away-20261022/` (TASK.md). Team live check
(agreed method) at the `wh3-model-team` tip `31823f3`: passed 4/4
(`runs/twwarhammer3/team-live-20261022-tip/`); main's checker recounts the same evidence
4/4. The agreed [starting-set screen](tactic-cards.md#the-starting-set-proposal-2026-10-21)
at `a6e3c0b`: 39 of 39 launches, every one ended by the engine (none by the timer), clock
ratio 0.99-1.01, 6 single orders refused by the engine. Contact wins of 3 launches per
arm (`read_screen.txt`): line `hold` 0, `attack_nearest` 1, `rush_nearest` 2, LineTeam 2;
expendables `hold` 0, `attack_nearest` 0, `rush_nearest` 0, SlaveTarpit 3 (all 3 with the
marker); rifle lane `hold` 1, `attack_nearest` 1, FlankLane 2; two threats `hold` 0,
`attack_nearest` 1. By the agreed reading rule the line and the rifle lane are parked, two
threats would get one step, and only the expendables card went on. The line's marker
shows in 7 of its 9 floor launches (criterion 4 flag). Delegated: the expendables shortcut OgresFirst
(SlaveTarpit's pins without its wait, a new `battle/shortcuts.py`; its test rejects two
mutants, dry run on 18 recorded episodes clean), played 3 launches from its branch at
`2d12f27`: won 3 of 3 by contact (139, 256, 298 s), none with the marker
(`shortcut_markers.txt`: ogres at the guns at 82-87 s, slaves on the halberds at 114-118 s;
in SlaveTarpit's wins, slaves at 90-91 s, ogres at 133-134 s). The card fails criterion
2, so no battle in the screen goes to confirmation. The branch is archived as
`archive/wh3-expendables-shortcut`; its 3 register rows are on main. Unverified: every gameplay outcome (3 launches per arm).

## 2026-10-22: second review, two team fixes and the screen reader

A five-area review with a skeptic per area (16 findings: 6 confirmed, 1 plausible, 9
refuted): `runs/twwarhammer3/review-20261022/`. Offline, $0. On `wh3-model-team`: a member's
batch was checked again on the state at dispatch, so one order made stale while it thought (an enemy gone from sight) refused its whole batch, where the single controller's
batch is checked on the state it decided on and the engine refuses only that order (in 179
past episodes about 0.4% of batches, 37 of 8,386, held such an attack; a rough count). The
team now checks each batch on its member's source view and the play loop skips its second
check for teams. A member other than the army owner whose units are all destroyed is no
longer asked. The agreed team test lost its outer-validation assertions (that path is
gone). Checks at `31823f3`: WH3 and gameai tests 781 passed, 2 skipped; ruff clean; 4 of the
new and changed tests fail on `73e2ccd` (the army-owner case and the trimmed expiry test
pass there). Two skeptics then reviewed the fixes: a stale comment, lost coverage of
`watch`'s refusal line (restored; it fails when that line is broken) and doc wording, all
fixed. `read_screen.py` now counts floor launches showing the card's marker and flags them
(it fires on the rank-0 line, where both floors show it). Not fixed: a call cut off at
cleanup is missing from the team's register cost (state item 6); a call interrupted by a
queue stop is never charged (cents per stop). Unverified: everything live.

## 2026-10-21 night: team code review and fixes on the branch

The owner asked for a careful review of the multi-agent code, then, with no time to review,
for fixes on my judgement ([directions](../owner-direction.md)). Offline, $0, no push. Five
reviewers, each finding checked by a skeptic: 28 findings (about 21 distinct), none refuted;
a review of the fixes (three reviewers, three skeptics) found one regression in them, fixed.
Evidence: `runs/twwarhammer3/review-multiagent-20261021/`. `wh3-model-team` is now `73e2ccd`
(two commits on `9689185`); main's code is unchanged. Fixed: a member's key, credit or
budget stop collected at cleanup was swallowed and the job went on; members could not aim
Ally abilities at the teammate's units; a forfeit at cleanup was recorded as one; the team
note denied the visible ally targets members do see; a bought or summoned unit ended the
episode (it now joins its member); team times used the monotonic clock, which WSL runs slow
(2 of 15 timed 3 s waits measured under 3 s on it, a false live-check failure); the live
check's age test compared the adapter with itself and `--recount` overwrote `checks.json`;
`report` and `export` now refuse or exclude team episodes; `watch` and `digest --at` show a
member's prompt at its source time. Three edits that passed every agreed test now fail
`test_wh3_team.py`. Checks at `73e2ccd`: full suite 1408 passed, 28 skipped; the four agreed
team files 122 passed; every new test fails on `9689185` or on my first draft; the saved
live evidence recounts 4/4. Parked for the owner
([state](../state.md#owner-decisions-waiting), item 6): two team rules. Not fixed: `watch`'s
spend omits uncertain-transport charges (not team code). Unverified: everything live; the
live check needs a rerun at the tip.

## 2026-10-21 evening: a plan for team structures

The owner asked for a careful plan of other team structures than the arbitrary two-model
split (one model per unit, per type, per group chosen by another LLM, and more) and of what
to visualize ([directions](../owner-direction.md)). Added [team-structures.md](team-structures.md):
six dimensions of variation, eight structures with question, estimated cost and verdict, the
call schedule (round-robin at equal compute for the screen), the code on top of `team.py`,
stages, views and risks. Built from three gatherers (16 prior-work sources, repo costs and
limits, visualization data), three drafts from different angles, a synthesis and an
adversarial critique of 19 items, most applied (`ts_critique.md`), and a final fact and coverage check; notes and $0 prototypes in
`runs/twwarhammer3/team-structures-20261021/`. Measured inputs: GLM-5.3 low costs
$0.0026-0.0030 a call at 10-20 calls a minute on the line (4 battles), 45-80% of its
decisions change no order, the mailbox takes about 3.3 batches a second (4 probes), unit
IDs were stable in 17/17 fresh line launches. Every team cost is an estimate. The plan's
first paid team step is now a structure screen (about $10) instead of a two-member 6 + 6.
Documentation only: no game, no spend; nothing here is verified.

## 2026-10-21 evening: a model team on a branch, offline

The owner was busy (18:47: "follow your best judgement and highlight any meaningful
decisions"), so offline work only, $0, no push. The starting-set screen's preflight passes at
HEAD (39 jobs, 0 problems) and `doctor` is ready (build 25961564); it waits for a free PC.
Branch `wh3-model-team` (`9689185`, nine commits) adds `team_llm_rules`: two `llm_rules`
members, the Knights against every other unit, sharing one ledger; the ledger holds each
call's reservation until it returns. Members get the single controller's fields and orders
for their own units, the teammate's units as public rows, its forfeit and budget rules, a
30 s bounded cleanup and per-member records. Built from a code map and design, then
reviewed (three reviewers, each verified): 9 findings fixed, one a leak of the teammate's
pending orders. Checks at the tip: full suite 1399 passed, 28 skipped; the four agreed team
files 121 passed; new tests fail on 31 deliberate mutations; existing goldens and policy
files unchanged. Decisions I took (undo: say so): no age limit for model members, like the
single controller; the Knights-versus-rest split; a 30 s cleanup wait; the agreed ledger test
now also covers `team_llm_rules`. Not done: report, export and card-board support for team
rows, and the live-check rerun the trace change needs. Unverified: everything live.

## 2026-10-21: Team plan and implementation review

The owner asked for a review that simplifies the team work and cuts slop. Four independent
reviews (code bugs, code and test simplification, doc slop, plan substance), each with an
adversarial verifier, a completeness critic, and two checks of the rewrite (facts, lost
content); scripts in `runs/twwarhammer3/review-team-20261021/`. No agreed test checked
oldest-first selection: selectors that ignore or reverse completion order passed all 120
tests at `45fe7b0`. `test_the_oldest_completed_batch_goes_first` (`e8d1eda`) fails on both
(`selector_mutation.txt` there); a no-op fixture teardown and a redundant dispatch check are
gone. Runtime code is unchanged, so the live check at `45fe7b0` still covers it; five small
code cleanups wait for the model-team change, which needs a live rerun anyway. Found: the
live check's per-sample speed test cannot fail (the mod writes `speed` 1 as a constant; the
clock ratio still catches gross slowdown), and its 0.25 m threshold is below the Knights'
idle jitter, so a stricter witness (idle before the order) is proposed, recount only. The
revised plan proposes divided against single control first (one card, 6 + 6 launches, about
$10), no separate 18-launch screen, and single-client steps before native multiplayer; team
timings must come from member events, as the outer loop measures polls. Implementation page
368 to 191 lines, plan 648 to 549. Checks: four agreed files 121 passed, WH3 plus doc links 718, ruff
clean. The plan's proposals and the model-team items remain unverified.

## 2026-10-21: First scripted team, harness b49

Added `battle/team.py`: two fixed unit owners, copied allowlisted inputs, independent
bounded script workers, one member batch per request, latency from each member's own source
and local refusals. Play drains member events through cleanup; card and digest mark
asynchronous team dispatch. `DelayInfantry`/`DelayCavalry` delay one member's first decision
by 3 s and move each unit 20 m forward on the existing Knights/Swordsmen scenario; no Lua,
prompt or mailbox change. Checks: 120 focused tests, WH3 plus doc links 717 passed, lint
passed; deliberately broken ownership, concurrency and source-age code each failed its test
(`runs/twwarhammer3/team-check-20261021/`). Review fixed incomplete-roster and constructor
fault classification and hardened the live witness against formation settling, self-reported
ownership or acks, unfinished workers and gross clock slowdown. Live at `45fe7b0`: 4/4 fresh
launches passed in about 12 minutes at $0, two with delayed infantry and two with delayed
cavalry. First qualifying samples were 0.42-1.76 m closer, 1.74-1.84 s before peer
completion (a later recount: 4.6-10.8 m and running at the last sample before it); 8/8
first-move raw acks matched; member age 600 ms fast, 3300-3900 ms delayed; clock ratios
0.9998-1.0006. All ended by diagnostic truncation, no game process left, no register rows;
a raw-sample recount found each of the 1,112 member calls ended exactly once. Build 25961564
matched the pin. Evidence: `runs/twwarhammer3/team-live-20261021/`. Unverified: models,
messages, native multiplayer, campaigns and teamwork quality.

## 2026-10-21: Multi-agent evaluation and implementation plans

Added [the evaluation plan](multi-agent-plan.md) (split army, native allied armies and 2v2,
then cooperative, mixed-interest and full multiplayer campaigns) and
[the implementation plan](multi-agent-implementation.md) (two scripted members first).
Source audit at `c2a7ae7`: the battle Lua refuses multiplayer and campaign battles; `scan()`
skips other local-alliance armies but its reinforcement loop does not; one mailbox request
is in flight; `Ledger.reserve()` holds no in-flight reservation, so parallel paid calls need
real reservations. Its 18-launch screen and 36-launch pilot were later replaced (review
entry above). Checks: doc links and ruff passed (logs in
`runs/twwarhammer3/multi-agent-plan-20261021/`). Documentation only.

## 2026-10-21: Subjective-evaluation resource review

Read [Wolfe's guide](https://cameronrwolfe.substack.com/p/subjective-evals) and added it to
the [evaluation sources](evaluation-guidelines.md#sources), with links to its uses and
WH3 limits. The guidelines now cover audits of false successes and failures, continued
reviewer calibration, new reference labels when criteria change, and judge repeats kept
separate from battle counts and tactic coverage. Product monitoring translates here to
finding development scenarios from live-job faults. Independent review caught and resolved
the need to replace reference labels after a criterion changes.
Evidence: `uv run --locked pytest -ra tests/test_doc_links.py
--basetemp=runs/subjective-evals-review-20261021/pytest-tmp` passed all 55 checks after
creating the missing scratch parent (first attempt: 54 passed, 1 setup error);
`uv run --locked ruff check .` passed. These check links and lint, not evaluation validity.
Documentation only; no battles, paid calls or scoring changes. New methods remain
proposed and unverified under the owner's hard rule.

## 2026-10-21: Prompt v22 / commander v8 and harness b48: contact scoring told to defenders

The owner's ruling ([directions](../owner-direction.md)): the cards count only contact
wins, so the model prompt now says so instead of promising a defender the timer win
([Empire decision 7](empire.md#decisions-taken-for-the-owners-review)). A scenario's new
top-level `scoring: "contact"` (set on the line and expendables cards and the rifle-lane
and two-threats probes) is copied by `play.py` into the policy's `mode` (b48);
`render_mode`, shared by `llm`, `llm_rules` and `commander`, then writes "if time runs out,
the game gives you the battle, but this benchmark counts only routing or destroying every
enemy unit before the timer". Every other scenario's prompt is unchanged, so the golden
prompts stay as they are; the card board's setup key leaves the field out, so scripted
floors still pool with recorded ones. Two regressions fail without the change and pass with
it; WH3 suite passed, ruff clean. Unverified: no live battle has run on v22 or b48.

## 2026-10-21: Harness b47, the agreed failure rule and the starting set's go-ahead

The owner, on return, agreed the three inbox recommendations
([directions](../owner-direction.md)). b47 (`b536ae6`, the reviewed branch commit `98b3013`
applied to `main`): `play.py` stores the engine's ending as `engine_ending` before the
acknowledgement and keeps it through a `close()` failure; which result counts, report
readings and interrupt handling are unchanged, so such an episode is still a
`policy_failure`. Regression
`test_a_controller_failure_after_the_ending_keeps_the_engine_result` fails on the parent
and passes; WH3 suite 633 passed, ruff clean. No recorded episode took either path (0 of
595). The [failure rule](benchmark-implementation.md#correctness-checks-to-agree) is agreed; scoring
construction failures and the kept ending by it is a later evaluator change. The starting
set's screen is agreed with its reading rule and markers and runs on the next free night;
the defender prompt change is approved as its own prompt version. Unverified: no live
battle has run on b47.

## 2026-10-21: A proposed starting set, the failure-rule recount and a blind c1 recount

Away window from 02:20, offline, $0, no game (no plan named); `runs/twwarhammer3/away-20261021/`.
- [Starting set](tactic-cards.md#the-starting-set-proposal-2026-10-21) (proposal): a
  five-part rule, three cards (chariot, rank-5 line, Skaven expendables; two blind agents
  chose them), a 39-launch $0 screen plan, a held-out map. Fixed 113 of 114 review finds
  and 132 stale facts; 18 policy-file texts kept (edits change recorded hashes).
- Failure rule: none of 595 episodes failed at construction, a late acknowledgement or
  `close()`, so the [proposed rule](benchmark-implementation.md#correctness-checks-to-agree) rescores
  nothing; unmerged branch `wh3-keep-engine-ending` (`98b3013`) keeps the engine's result.
- c1: a blind recount matched every outcome and the verdict (its cycle counts lacked the
  scorer's 1 s tolerance, now written); of 21 hand-picked engagements cycles v1 got 13,
  "all but the last" 10.
- For decisions: 16 of 17 model battles on five defending scenarios repeat the timer win;
  reasons over 300 characters flag 8 of 15 garbled replies; the 10 battles off wall time by
  over 5% predate b39; 1 of 17 line battles met the criteria for using the reserve.
- Checks: four campaign-safety tests, one that the rules prompt withholds card tactics; no
  new harness error in 411 episode logs; blind rebuilds of two markers matched 29 of 31
  verdicts; risk: campaigns run the stills script ([integration](integration.md)).
- Unverified: all gameplay counts (1-33 episodes a cell), markers and labels; three witness
  texts misstate their code (parked); the checking agents share one model family, so they
  test documents, not judgment.

## 2026-10-21: Autonomous-work strategy refined (proposal)

Revised [autonomy.md](../autonomy.md) around useful outcomes, existing evidence and bounded
work: three independently reviewable changes across sessions, no speculative dependency
stacks, one recommendation per decision, and a stop when no useful permitted step remains.
Aligned AGENTS/state and recorded the owner's request; standing delegation remains proposed.
Corrected queue deadline semantics, ordinary launch writes, new regressions within agreed
suites, source scopes/report grouping, save-file ownership and multi-launch check cleanup.
Two independent readers reviewed the strategy and source contracts; all 12 tabletop cases
matched the expected actions. This is document reasoning, not an agreed operational check.
Checks: 55 documentation tests passed, none failed or skipped; Ruff and diff whitespace
checks passed. Initial sandbox refusals of uv cache writes and subsequent passing outputs
are retained in `runs/autonomy-20261021/`, with the cases and review notes.
No runtime code, scores, agreed verification methods, game runs or paid model jobs changed.
Whether this reduces errors and owner review effort remains unverified; next is a bounded
offline trial after agreement, using existing recount/mutation evidence before new work.

## 2026-10-20: Evaluation guidelines rewritten after review

- Rewrote [evaluation-guidelines.md](evaluation-guidelines.md): 45 rules in 10 sections,
  each with a Check (exists / proposed with size / manual); a glossary; a study-plan key
  table; a failure table with today's and proposed treatment; a method table; common advice
  that does not apply; a ranked enforcement list; 12 owner decisions. Rules are numbered
  1.1-10.5; G1-G42 are retired (G1/G2 name calibration plans).
- Research: 18 readers (the 12 readings, related game benchmarks, three code maps, design
  docs, language) gave 537 findings, merged per topic. Eleven readings were read in full,
  Wolfe's LLM-as-a-Judge through section summaries (corrects the entry below).
- Review: 7 lenses gave 145 findings, 140 kept after a refuting pass; a final 3-agent check
  found 1 high and about 30 smaller issues, all fixed. Corrected errors include a paused
  battle marked as detected today (the mod always reports speed 1), detection chance
  confused with the smallest significant split, pooled witness cells, Wilson coverage
  (down to about 84%, not 85%), and a serving-fault loss the old example would have set aside.
- Checks: every statistic recomputed twice (`runs/twwarhammer3/eval-guidelines-review-20261020/numbers/`);
  `tests/test_doc_links.py` 54 passed; ruff passed. No code, score or agreed check changed;
  every proposed check and gameplay finding stays unverified. 10.1k words against 8.4k: the
  extra is per-rule checks, the failure table and the glossary.

## 2026-10-20: Evaluation guidelines from the research readings

- Added [evaluation-guidelines.md](evaluation-guidelines.md): 42 guidelines covering
  task definition, splits, real-time comparisons, failure accounting, statistics,
  human/LLM review, rubrics, training separation and research artifacts. Each area has
  proposed code checks; common evaluation practices have explicit WH3 adaptations.
- Read all twelve supplied sources and selected cited research; source tables identify
  their uses and limits. Three independent reviews checked statistics, judging and the
  benchmark contract. Corrected the withdrawal example, pairwise-judge handling, trial
  grouping description and failure/track boundaries; numerical examples checked.
- Checks: 54 documentation-link tests passed; `uv run --locked ruff check .` passed.
  Evidence: `runs/twwarhammer3/eval-guidelines-20261020/`. No code, score, historical
  cohort or agreed verification method changed; no battles or paid model runs.
- Live-game effects, judge accuracy and proposed safeguards remain unverified. The guide
  supplies methods for later agreement and execution, not new verification claims.

## 2026-10-20: Benchmark scope and release criteria

Consolidated the [scope](benchmark.md#scope): complete controllers on
declared live tactical tasks, intended users, outputs and explicit initial exclusions.
Separated a scenario declaration, admitted card, reusable path and frozen suite; aligned
the README and runbook. Added concrete quality criteria, a
[release route](benchmark-implementation.md#phases) and bounded candidate decisions.
Useful release and novel research are separate milestones; team recovery and training
are conditional studies. Existing cards and c1's rule are unchanged.
Independent scope/diff review found no new agreement or scoring conflict; clarified that
coordination research is not required for single-unit cards or a useful suite.
A separate primary-source review checked SMACv2, Realtime-Bench, GameWorld and DPT-Agent;
live clocks and hierarchy alone are not a novelty claim. This was a selective review.
Documentation only: no implementation, game or paid calls. 53 link checks passed, none
failed or skipped; Ruff and diff whitespace checks passed. Initial uv cache access was
blocked, then checks passed with access; logs: `runs/twwarhammer3/benchmark-scope-20261020/`.
Gameplay, proposed verification methods, suite usefulness and novelty remain unverified.

## 2026-10-20: Benchmark scoring boundaries and rerun plan

Refined the [definition](benchmark.md) after two independent code/document reviews.
Construction failure can be excluded for lacking a battle id; acknowledgement or cleanup
failure can prevent an engine ending from being preserved. Documented a proposed phase
rule and explicit checks; no code fix or live-frequency claim. Failure-stopped rotations
and budget-stopped battles need missing-outcome treatment before comparisons.
Failed confirmation cohorts remain evidence; unchanged gates cannot be retried to obtain
a pass, and later drift checks stay outside admission. Recalculated 10/14 Wilson bounds
(45–88%) and the 0/14 one-sided bound (0.193); c1's historical rule is unchanged.
Timing contrasts include the delayed opening and cannot establish rescue by faster serving.
Recovery adds a conditional fixed-time reserve comparison. The
[rerun plan](benchmark-run.md#independent-rerun-acceptance-proposal) names the evidence
handoff, recount and two-launch lifecycle check, with limited claims. Shortened the stale
scenario survey; history remains at `e75cba5`. Added Gaia2 scorer-validation and statistical
evaluation lessons, independently checked against the primary papers.
Documentation only; no source, scenario, prompt or result changed, no game or paid call.
53 link checks passed, none skipped; Ruff passed. Initial uv cache-permission failures
were retried with access; logs: `runs/twwarhammer3/benchmark-definition-20261020-r2/`.
New checks, gameplay effects and the independent live rerun remain unverified.

## 2026-10-20: Benchmark definition and proposed checks

Refined [benchmark.md](benchmark.md) into one current plan: define the choice, screen
shortcuts, confirm useful cards, compare controllers, then test reserved variations and
independent reruns. Proposed live-effect, information-boundary, signature and scoring
checks name an independent reference and a plausible wrong result. No method was agreed.
Preserved the chariot's frozen c1 rule; new 0/14 foil and 10/14 witness gates are proposals.
Separated terminal forfeits from retried decisions, card/report denominators, and accepted
orders from observed effects. The roughly 13 s `info age` is a proxy, not a tactic deadline.
Five primary research comparisons inform timing, shortcut tests and evaluation splits;
two independent reviews checked the sources and documentation against current code.
Shortened superseded calibration/novelty material; corrected difficulty/experience status
and recorded the Empire-first shortlist. No source, scenario, prompt or result changed;
no game or paid call ran. Link checks: 53 passed, after fixing the scratch parent and
retrying cache access; Ruff passed. No tests skipped. Gameplay and the proposed checks
remain unverified; independent live reruns are future work, not evidence from this edit.

## 2026-10-20: Research for robot team coordination

Expanded the [research guide](robot-team-research.md) around capability allocation,
recovery, execution during slow calls, plan adoption, evaluation and learning. Each source
has a concrete WH3 use and transfer limits; published results and preprints are identified.
The [experiment plan](robot-team-plan.md) now starts with the Empire evidence, preserves
the deferred Skaven candidate, and separates allocation, execution and adoption.
Its first gate asks whether recovery helps beyond fixed jobs and early commitment.
Corrected [post-training](../posttraining.md#beyond-supervised-fine-tuning): missing
behavior probabilities prevent some importance corrections, not every offline RL method.
Two independent source reviews checked the summaries and experiment wording. No controller,
scenario, agreed verification method or gameplay result changed; no game or paid call ran.
All 53 Markdown link tests and Ruff pass; an initial missing test scratch directory was
created before rerunning the link checks. These checks do not validate paper claims.
The research contribution and proposed interventions remain unverified.

## 2026-10-20: LineTeam kept targets and a reason cap (harness b46)

A review of the Empire night (report and findings in `runs/twwarhammer3/review-20261020/`)
confirmed 31 issues; b46 holds the fixes.
- `calibration.py`: `LineTeam`'s guns and waiting reserve keep their last target while
  it stays in their set (in the six b44/b45 launches the guns re-picked between enemies
  at almost the same distance every decision, 8-46 target changes a gun, and the reserve
  alternated in melee); the knights look their kept target up among all enemies (a
  rallied rider remnant had taken the archers target away) and finish a melee before
  riding back; `LineTeamReserve` measures from the most recent break, and its card says
  what the code does (the next target while a line unit is missing, the waiting rule once
  the line is whole). Three checks in `test_wh3_calibration.py` fail at `76ef7ed` and pass
  here; a fourth records the chaining the rule already had. Live effect unverified; the
  revised arms are unplayed.
- `llm.py`, `commander.py`: a reply's reason enters the prompt history cut at 300
  characters (`REASON_LIMIT`): the b44 wizard launch's 14,858-character garbled reason
  tripled the next two prompts. No healthy reason of the night's 3,110 accepted replies
  exceeded 273, so no fixture prompt changed; `llm` stays v21 unless the owner rules the
  cap a prompt version. The trace keeps the full reason.
- Pages corrected from the register and traces: model contact wins 7 of 29 (the page
  said 9, this log 8), 45 launches and 29 model episodes (39, 23), the rank-5 reserve
  arm's reading, Kimi's refusals and cost basis, the wizard anomaly as garbled replies
  (seven accepted in four launches), stale items on state.md, owner-direction.md,
  posttraining.md and the Spire README; the b43 entry and state.md shortened. 1,351
  tests and Ruff pass.

## 2026-10-20: The Empire set (harness b43)

The owner's night goal ([owner-direction.md](../owner-direction.md)) taken as the
[Empire set](empire.md), whose page holds the why, the scenarios, the per-launch readings,
the decisions and the risks. All of it is unverified; no check is agreed.
- b43 (`4fefd1c`, 02:37): three Empire scenarios declared, no code change (the line
  battle, riflemen against wolves and boyz, knights past a goblin spear screen). b44
  (`355c040` 04:01, `55bd657` 04:13): `LineTeam` and `LineTeamReserve` in `calibration.py`
  (the robot-team comparison's two scripted arms); knights battle stepped to Orc Boyz. b45
  (`9bb2abd`, 07:20): `emp-line-grn-raid-xp5`, the line battle at experience rank 5.
- Four queues in `calibration/empire-20261020/` (`plan.json` 17 launches, `plan-b.json`
  16, `plan-c.json` 6, `plan-d.json` 6 from 08:19 at `b7e2dd1`, recorded in `76ef7ed`):
  45 launches 02:37-09:00 local, every job exit 0; OpenRouter $8.84 of the night's $10
  cap, ledger $12.49 to $21.33. `review.py --units` there prints the per-launch table.
- **Contact wins** (single launches; readings on [empire.md](empire.md#results)): floors
  `hold` 0 of 3, `attack_nearest` 1 of 5 (its rank-0 line battle was a timer stalemate at
  1205 s, not a win), `rush_nearest` 0 of 2; GLM-5.3 low (`llm_rules` v21) 7 of 25, $6.14:
  hammer and anvil 2 of 2, wolves 1 of 2, Helblaster 1 of 2, rank-5 line 1 of 1, riflemen
  at 1.0 1 of 1, two-Dwarf crossfire 1 of 1, rank-0 line 0 of 3, the other steps 0 of 13;
  Kimi K3 low 0 of 3 on the line battle, $2.65; Qwen3.6 none 0 of 1 (the 20 v 20), $0.05;
  `LineTeam` 1 of 3 (rank 5), `LineTeamReserve` 0 of 3.
- The second wizard launch lost on garbled replies (gibberish text, no orders) from the
  pinned Decart backend, 5 decisions, scored as a loss; four more garbled replies were
  accepted at 11-53 s in knights2 l2, wolves l2 and pitched20 l1.
- Decisions and risks for the owner: [empire.md](empire.md#for-the-owner-to-decide).
  Defect found: LineTeam's guns flip targets (41-43 orders, 5-7 targets a battle); fixed
  in b46 with the knights' and reserve's target rules.

## 2026-10-20: UI and lobby integration (harness b42)

- `e32b1b5`: fixed recruitment/factions/settings use native contexts; mounts avoid sorted
  indices, permissions and funds are checked separately. Difficulty precedes the explicit
  AI modifier (its setter otherwise resets it). Owned sessions deactivate after teardown.
- Menu results carry request identity; foreign jobs and unsupported battle scheduling are
  rejected. Failures propagate; false branches skip promptly; missing startup XP fails setup
  without disabling the battle tick. Policy inputs/prompts and benchmark scenarios unchanged.
- Agreed live check passed: `uv run --locked python tests/twwarhammer3/check_wh3_army_setup.py
  --integration --output runs/twwarhammer3/integration-review-20261019/live-r8`.
  Four launches: ten saved units, duplicate Swordsmen/Captains, three mounts, ranks 0/1/3/9,
  zero warm recruitment, exact attack/defence and relative leadership XP bonuses; seven
  survival reserves. Disturbed settings reapplied; funds/DLC refusals preserved the roster;
  original settings restored. Unpaused 1x; no paid calls, scored outcomes or register rows.
- Evidence: `integration-review-20261019/`; r5's eight-unit old-click/context comparison
  matched types/ranks/stats. Earlier attempts exposed the difficulty reset, Captain XP
  refusal and checker-only exit/string-search errors. Live-r8 fingerprints match `e32b1b5`.
- 663 WH3/link tests passed, zero failed/skipped; Ruff passed. Ten plausible wrong component
  implementations were detected. One unchanged capture test timed out during a concurrent
  live run; its focused and full reruns passed after shutdown (failure log preserved).
- Leaner docs link canonical code contracts and list API candidates. Graceful-exit setting
  persistence, character/reinforcement XP, other modes and policy strength remain unverified.

## 2026-10-19: Saved armies and experience (harness b41)

Owner requested both lobby controls, with restart/load and lobby/battle rank checks agreed.
- Fixed armies use native `gameai-<digest>` presets keyed by army, settings and Steam build:
  first use recruits/saves, later launches load. Type/rank counts are checked before battle.
  Autogenerated armies/pools still rebuild; benchmark scenarios are unchanged.
- `experience: {"1": 3, "2": 9}` sets ranks by recruitment index, default zero, range 0–9.
  Assignment matches type/occurrence after recruitment and reads back every +/- operation.
  Private battle-start ranks are checked against declarations and across rematches.
- Agreed live check **passed at `c768460`**: `uv run --locked python
  tests/twwarhammer3/check_wh3_army_setup.py --output runs/twwarhammer3/army-controls-20261019/integrated-r4`.
  Two launches: save eight units, exercise increases/decreases, clear, restart, load with
  zero recruitment clicks; mounted lord and ranks 0/1/3/9 preserved at battle time 5.3 s, 1x.
  Swordsmen attack/defence 32/35/41 matched lobby and battle; leadership bonuses +3/+10
  matched relative to rank zero. All friendlies had a -4 leadership offset; cause unverified.
- Earlier probes stopped on class-sorted indices (r1) and unsupported direct lobby context
  lookup (r2); r3 reached battle but its absolute-leadership assertion exposed that offset.
  Evidence: `runs/twwarhammer3/army-controls-20261019/`. The corrected stat check rejects a
  deliberately removed rank-3 attack bonus. 225 focused tests passed, no skips; Ruff passed.
  No paid calls or scored outcomes. Other modes, reinforcement XP and policy strength remain
  unverified; this verifies configuration and XP stat effects in the declared diagnostic.

## 2026-10-19: Witness v2 and prompt v21 (harness b40)

Owner goal (evening): keep making progress on the benchmark; battles and some API spend
allowed; understand the results before drawing strong conclusions. Decided under delegation
from the [second-pass decisions](tactic-cards.md#second-pass-2026-10-19-evening-findings-and-the-version-2-decisions):
decisions 1 and 2 run tonight, 3-5 stay with the owner; the v1 rule and verdict are untouched.
Recounted first from the raw replays (my own script, two numbers corrected by the diff
review): all ten 5/5 and 8/8 witness losses ended 12-72 m from a map edge and the 3/3 loss
at 30 m; every win but one 120-432 m from it (the 0/0 l1 win ended 50 m from the south
edge). GLM's in-melee reasons at 20-30 m centre distance read "still hasn't connected" (l1,
117-120 s) and "broke contact" (l3, 121-124 s) with the melee flag shown, then "let it grind
rather than risk another failed disengage" (l1, 140 s) and "let the charge bonus work" for
10 s (l3), so the interface gap is real and is not GLM's only fault.
- b40 (`calibration.py`): `HitAndRunV2`, a disclosed control beside the admitted witness: on
  the first observed melee one batch, a run 150 m from where the unit stands away from the
  enemies' centre, turned in 45 degree steps to lie 100 m inside the map (or no nearer its
  edge than the unit) on clear ground, else the first clear point clamped inside, with the
  attack queued behind it; it re-arms once an observation shows the unit out of melee and
  30 m from where the batch was sent (the flag flickers inside one engagement in 1 of 13
  recorded ones); a unit still in melee where it stood 15 s later pulls out again; a refused
  point un-arms it so the next decision pulls out elsewhere. Its `pull_outs` count is not
  v1's `charges`, and a refused pull-out counts two invalid orders (the queued attack too).
  One test (the batch, two stale frames, re-arming, the charge run, the flicker, the stuck
  retry, the edge turn, the refused point, the blocked fallback); the hidden-enemy test
  covers it. `cards.py` labels a model cell with its prompt version, so the v21 cohort is its
  own row beside P5a's v20 (before, the board pooled them into one starred cell).
- `llm`/`llm_rules` v21: one Information sentence in both prompts (positions are unit
  centres; the "melee" flag, not the centre distance, says whether a unit is in contact).
  Diff review (three read-only agents, their findings recounted): a clause saying the flag
  clears only once the unit has left the fight was dropped, since the recorded replays show
  it off within 2-13 m of an enemy centre; v2's first draft fell silent where no retreat
  point passed the 100 m margin and the terrain blocks (162 of 4096 grid positions, most
  within 56 m of an edge), hence the fallback.
- Round `calibration/v2-20261019/plan.json` (one plan, `keep_going`): witness v2 at 5/5 and
  8/8 (5 launches each) and 2/2 (3, its sanity cell); GLM-5.3 low v21, 10 launches (about
  $1.70); then Kimi K3 low v21, 10 launches (P5's remainder, about $5); paid jobs stop the
  WH3 OpenRouter ledger at $20 (held $10.66; the account had $46.41). Reading rules fixed
  before the round: witness v2 against v1 per cell with Wilson intervals, no threshold; GLM
  v21 against the P5a cell, one-sided Fisher, a screen at n = 10; no verdict words. Results
  are appended below when the round ends. Unverified: no check agreed.

**Results** (23 launches 18:21-21:36 local, every job exit 0; the owner stopped the round
before the Kimi arm, whose 10 plans stay unrun; OpenRouter $1.83, ledger $12.49; per-episode
table from `calibration/v2-20261019/review.py`; all unverified, cells of 3-5 and 10):
- **Witness v2, 13 launches, $0: 2/2 3 of 3, 5/5 4 of 5, 8/8 4 of 5** (v1: 4 of 4, 2 of 8,
  0 of 4), at information ages 4.1, 9.5 and 13.1 s; cycles 3-9 (median 5), 5-11 pull-out
  batches a battle, all six chariots alive in 8 of 10 slow-cell battles. Its wins left 26-68
  of 180 enemy men; v1's slow-cell losses left 109-169. Its two losses (5/5 l3 at 341 s, 8/8
  l1 at 394 s) ended 347 and 184 m from the edge with 68-102 men left, so no stall. Pooled
  slow cells v2 8 of 10 against v1 2 of 12: one-sided Fisher 0.005 (8/8 alone 0.04, 5/5
  0.086). Reading: the tolerance curve was `SnapHitAndRun`'s; with this recipe the tactic
  tolerates at least 13 s of information age, three times the model cells' 3.4-4.2 s, so
  the chariot card is not a latency card at model paces and a model's loss on it is not
  explained by its order age.
- **GLM-5.3 low on v21, 10 launches, $1.83: 0 of 10** (v20: 1 of 10; one-sided Fisher 1.0),
  battles 206-566 s (median 242), every attempt on Decart serving `z-ai/glm-5.3-20260816`,
  the recorded prompt hash the v21 file's. The sentence changed the play, not the outcome:
  attack orders issued with the melee flag on fell from 56 in 10 battles (6 battles with 3
  or more) to 38 (4 battles with 3 or more: l7-l10, 3-12 each), enemy men left fell from a
  median of 143 (71-165) to 110 (59-138), and move-plus-queued-charge batches rose (0-7 a
  battle to 0-26). Every loss was a leadership rout with 4-6 of 6 chariots alive (minimum
  leadership shown 0-18% in 8 of the 9 battles measured, 34% in the ninth). Where it lost:
  pull-outs 4-45 m deep in 7 of 9 measured battles (the witnesses withdraw 77-150 m), often
  to the same 2-6 fixed points, which the Swordsmen advanced onto (l1 withdrew six times to
  (-160, 70) while the enemy stood at (-165, 78)); l5 sent 26 batches in 206 s, re-ordering
  the pull-out every decision. Reading: the second pass's interface gap explained GLM's
  re-attacks, not its losses, which are execution (withdrawal depth and re-planning), the
  gap the card is meant to measure; no "latency" or "knowledge" reading applies.
- Validity: build 25961564 throughout; witness v2's first batch was the intended move plus
  queued charge; a register row per episode; no forfeit, refusal of a retreat point or
  invalid batch from the witness (GLM: 0-3 invalid orders a battle). The default board now
  shows `llm_rules v20@...` and `llm_rules v21@...` as separate rows.
- Not done: the Kimi K3 arm (P5's remainder, 10 launches, about $5); decisions 3-5 of the
  second pass; whether v2 becomes the card's witness and at which cell is a new owner
  decision (the v1 rule and its admitted verdict stand). Owner notes for later: unit
  experience ranks as a knob, and the lobby's save and load army buttons to skip rebuilding
  both armies on every launch ([integration.md](integration.md#unverified)).

## 2026-10-19: Benchmark verifiability, second pass (harness b39)

Owner question repeated (afternoon). Eight read-only agents (two recounts of the 80 recorded
chariot battles from raw traces and replays, two literature sweeps, three critics, one
harness audit) plus the assistant's own recount, checked by a refuting agent; no game, no
paid call; nothing verified. Findings, the five owner decisions and the doc fixes (full cell
counts and achieved ages, cycles ranges, Orak v3, VideoGameBench, the Medieval II dataset,
two-sided Fisher): [tactic-cards.md](tactic-cards.md#second-pass-2026-10-19-evening-findings-and-the-version-2-decisions).
Superseded proposals: `git show 5c01b93:docs/twwarhammer3/tactic-cards.md`.
- The witness's tolerance curve reads as its recipe's: `SnapHitAndRun` stalls in its
  withdrawals (under 20% of its path becomes separation in the slow cells against 44-58% in
  the 2/2 wins) and nine of its ten 5/5 and 8/8 losses end within 35 m of the map edge (the
  foils and Qwen 250-290 m, GLM median 296 m). "The window closes between 3 and 5 s" and the
  "latency-bound" class are withdrawn; whether any recipe wins at 8 s of age is untested.
- GLM's 14 countermands reproduce when a queued later-batch attack counts (12 otherwise);
  12 of the 14 were decided at 2-29 m centre distance with the melee flag on in their basis,
  and the flag clears at a median of about 30 m: an interface gap (positions are centres,
  enemies carry no width) rather than a commitment failure, 10 of the 14 by their own
  reasons. Of the 11 ladder numbers, 4 reproduce only under other readings and 3 differ;
  cycles v1 stays the leak check and no ladder is built.
- b39 (`cards.py`, `play.py`; three new regressions, three tests extended): the verdict
  judges the witness on its first launches in start order (4 of 20 no longer admits) and
  prints only for named directories (the default board pooled exploration launches); a
  replay-less win is flagged; a cell's identity carries the served model strings, the
  requested observe/tick cadence and the routing pin, and an excluded launch never stars it;
  an information-age column (median order age plus half the decision gap) sorts the cells;
  the clock ratio stops at the last running observation (two GLM episodes read 0.971-0.973
  where their ack series gives 1.00). c1 still prints admitted. 546 WH3 tests and the 50
  link tests pass; ruff passes.

## 2026-10-19: Knowledge against execution: the protocol

Owner goal: a good solution for "knowledge against execution is not checked properly". A
14-agent pass (surveys of agent benchmarks, imitation and robotics evaluation, measurement
validity, repository feasibility; three designers, six critics, a judge), every number
recounted by my own script over the 64 recorded chariot battles; no game, no paid call;
nothing verified. Result: the ladder and the told arm, plan only; superseded by the
[second pass](#2026-10-19-benchmark-verifiability-second-pass-harness-b39) (text at
`git show 5c01b93:docs/twwarhammer3/tactic-cards.md`).
- Read orders, not text: a per-engagement ladder graded at the first decision whose basis
  showed melee (so latency cannot read as ignorance: the witness pulls out there in at least
  0.9 of observed engagements at every pace cell; its stale cells show unobserved and silent
  engagements instead), countermands split by what the controller believed, per-battle
  classes as the reading (GLM-5.3 low: won 1, countermanded 6, executed-lost 3; Qwen3.6 none
  never pulled out 5 of 5; foils never 20 of 20); cycles v2 is its by-product.
- Intervene once: `llm_card`, the rules prompt plus the witness's rule, 10 launches when a
  model lost; its contrast with the scored cell reads knowledge, direction only ($1.70, 2 h).
- Retired: the keyword screen; the local P4 probe (its first-contact grade matches the live
  first-decision reading, 18 of 30 against 18 of 33). Not adopted: live control bots as a
  gate, a depth rung in the score, thresholds read off model battles, verdict words at n = 10.
- Borrowed: BALROG and STOCKTAKE (knowing-doing rates; hints in the prompt may be ignored),
  AgentBoard (a progress ladder beside success), DAgger (grade on the policy's own states),
  known-groups validation and pre-registration (controls read before any model row).

## 2026-10-19: Benchmark verifiability review

Owner question: are knowing a tactic and executing it checked properly, is a card winnable
and skill-isolating, how to account for variable latency. A 15-agent review (three literature
briefs, engine capabilities, a code review, local data; three designers, six critics), every
number recounted by a second script; no game, no paid call; nothing is verified under the
hard rule. Proposals: card version 2, superseded by the
[second pass](#2026-10-19-benchmark-verifiability-second-pass-harness-b39) (text at
`git show 5c01b93:docs/twwarhammer3/tactic-cards.md`).
- Knowledge against execution: the live "stated the tactic" is a keyword screen in a scratch
  script; the uncommitted P4 offline probe measures the first-decision step the ladder of the
  later entry reads live. `cards.cycles`
  credits any applied move inside an engagement: over the 64 recorded chariot battles GLM-5.3
  low countermanded 14 of its 37 pull-outs with an attack before leaving melee (9 of its 30
  credited cycles), the witness 0 of 246; those engagements lasted 31 s median against 9 s.
  GLM's reaction to contact (4.5 s median) was not slower than the admitted witness's (5.1 s)
  and its achieved age profile (median 2.1 s, p90 3.3 s) lies between the witness's 2/2 and
  3/3 cells, which won 7 of 8: a commitment gap, not latency (10 battles, one night, one backend).
- The rule: 4 of 5 passes a 0.5 witness 19% of the time and fails a 0.8 witness 26%; 0 of 10
  bounds a foil below 0.26; the gate witness decides 3 times a second; each c1 foil's 10
  battles are 10 instances shared with the other foil; `outcome` changed after
  pre-registration (b35), no effect on c1. 10-launch model cells separate 0.1 from 0.8, not 0.4.
- Engine: no script seed, so a launch is never replayable; the mod's evacuation code can fix
  both sides' starts by teleport, unneeded here (starts within 1.6 m over 25 launches).
- Board, b38 (`cards.py`, two regressions that fail on b37): one episode per controller per
  launch, full model labels, the prompt hash in a model cell's identity, integer-ms cell
  keys, forfeits and p50/p90 age, planned launches that never ran (p2's fourth 0/5 launch),
  a verdict only with control cells, the merge constant in the rule line. No score or verdict
  changed: c1 still reads admitted. tactic-cards.md: the tolerance table replaces the
  model-pace reference row; two 2026-10-18 tables retired to git (`9df420f`).
- Borrowed: The World Won't Wait (action age as median and p95; held-out tasks), SMACv2 (an
  observation-blind control), Fishtest (sequential rules), Bowyer et al. (Wilson at small n).

## 2026-10-19: Robotics research notes

Owner requested research only, then concrete comparisons and codebase fit.
[robotics.md](robotics.md) connects 14 primary research
sources to generated feedback rules, planner/executor comparisons, action commitment,
learned micro control and adaptation tests. Refinement adds parameter-selection and bounded
correction baselines, assignment lifecycle, artifact identity and generator-level sampling.
Independent reviews checked repository fit, transfer claims and comparison validity.
Corrected latency.md's causal overclaim and failed-decision versus terminal-forfeit description.
No controller, scenario, prompt, result or version changed;
no game, training or paid model calls. Proposals and WH3 performance remain unverified.
Documentation checks: 50 link tests passed; `uv run --locked ruff check .` passed.

## 2026-10-19: Harness b37, mailbox and order boundaries

One bounded maintenance pass; owner agreed component verification, no game/API jobs.
- `bfcfd38`: per-mailbox request prefix fixes repeated `r1` being dropped on reattachment.
  Regression uses real files, the vendored JSON decoder and Lua `poll`; duplicate rejection stays.
- `f7b6c73`: reject non-finite numeric fields (including integers beyond Lua's finite range)
  even when the command ignores them. Preserve existing command diagnostics and invalid-batch
  feedback. The play-loop regression uses simulated observations, not the game.
- Before fixes: 6 intended failures, 106 passes. After fixes: 112 focused passes; the
  owner-agreed checks pass at `f7b6c73`. Disabling Lua duplicate rejection in memory makes
  the new test fail at its duplicate-delivery assertion. No mutation is retained.
- `uv run --locked pytest -q -ra`: baseline 1,264 passed; final 1,271 passed; both 14 skips
  (13 Torch-dependent Spire tests, 1 opt-in Windows process-ownership test). Ruff passed.
  An intermediate full run caught changed LLM retry text; fixed without changing its test.
- Shared guidance stays in AGENTS, imported by CLAUDE; add a short verification procedure,
  skip reporting and current command navigation. Codex 0.163.0's prompt renderer loads the
  complete file; Claude 2.1.303's installed import implementation was inspected (no model calls).
- Independent source/test and instruction reviews resolved; no remaining material findings.
  Only these component checks are verified. Game execution and policy strength remain unverified;
  no scoring, timing, visibility, track, evaluator or wire-schema changes, and no new results rows.

## 2026-10-19: Overnight round at b36: c1 finished, P2 cells, P5a

Owner goal (away until 10:00): overnight runs with valid, relevant results, at most $5 of
OpenRouter; decided under delegation. 50 launches, 01:57-09:11, plans, chain and
`summary.py` in `calibration/night-20261019/`; OpenRouter $1.78 (ledger $10.66). One plan
refused before launch: the chain lacked the key file. Cells are n = 3-10, post hoc, unverified.
- c1 (rule at `5396182`): foils lost 10 of 10 each, the witness won 4 of 5 at 5 s (5-8
  cycles): admitted under that rule. At model pace (5 s age, one decision per 5 s) it lost 5 of 5.
- P2, the witness by added age / decision interval: 0/0 won 4 of 4, 2/2 4 of 4, 3/3
  3 of 4, 5/0 4 of 5, 0/5 3 of 3, 5/5 0 of 5, 8/8 0 of 4. It tolerates stale information or a
  slow decision rate, not both: at model pace the window closes between 3 and 5 s.
- P5a, pinned, natural latency: GLM-5.3 low won 1 of 10 (199 s, 5 cycles), Qwen3.6 none 0 of
  5; median order age 2.1 and 2.7 s, inside the tolerated pace; $0.17 and $0.02 a battle.
  Every attempt went to the pinned backend; no forfeit or cut-off, so b35's forfeit path is
  unplayed. GLM stated the tactic before contact in 10 of 10, Qwen in 0 of 5 (keywords).
- Knowing against executing: GLM knew the tactic and decided at a pace the witness wins at,
  so by elimination it lost on execution; no measure tried shows how. Pull-out depth (GLM 47 m,
  witness 77-90 m) does not decide (the witness at 5/5 pulled out 77 m and lost all 5); refused
  moves hit the witness too; most losses (36 of 45) end in their longest contact, and before
  it losses held contact no longer than wins (medians 12.5 and 18 s). Two verifier agents
  checked the first 55 battles; their scripts, rerun on all 64, gave these numbers.
- Start and first target: once the cell is fixed they show nothing (at tolerated paces e1
  first won 14 of 15, e2 first 4 of 5), so the review's confound reads as tempo.
- Tooling (branch `wh3-queue-keep-going`, merged after the round): a plan can `keep_going`,
  `start_before` and stop on `PLAN-stop`, so a night is one plan, not 52 plans and a chain
  script; the card board counted a job twice when a replacement plan named the same output.

## 2026-10-19: Harness b36, pinned OpenRouter backends

Decided under delegation (owner away until 10:00; goal: overnight runs with valid results, at
most $5 of OpenRouter): owner decision 3 in [latency.md](latency.md#owner-decisions). Each
compared model goes to one backend with no fallback, the endpoints P3 checked live: GLM-5.3
on Decart, Kimi K3 on Sail Research, Qwen3.6 on Parasail (still fp8 or bf16); Step 5 preview
stays unpinned. Applies to both games. Unit tests only.

## 2026-10-19: Harness b35, the battle never waits

Owner decision 1 in [latency.md](latency.md#owner-decisions), merged on the owner's word. A
controller failure or truncation is a forfeit (a loss); a failed decision sends nothing and the
controller is asked again; a result during a call stands, its reply unsent; HTTP 401, 402 and
the ledger's own stop still stop the job. Re-scored, every recorded episode: 3 excluded become
forfeits, 6 invalid-reply losses are labelled forfeit. 1247 unit tests pass; unverified: no
game run.

## 2026-10-18: Open-loop probes P3 and P4 (no game)

Decided under delegation (owner: "$50.38 of credit ... spend it carefully"), capped at $3.03:
the plan's no-game stages ([latency.md](latency.md#staged-plan)). P3: OpenRouter pins through
`provider.only` on `/responses` held in 4 of 4 cells (Kimi K3 on Sail Research, GLM-5.3 on
Decart, Qwen3.6 on Parasail; 2 calls each; a pin to a non-serving provider got an uncharged
404), $0.03. P4: 70 moments frozen from the 22 scripted chariot battles at 1.1 (sha256
`2551d96f`), rendered by driving `LLMPolicy` (530 of 530 recorded prompts reproduced), notes and
history blanked, one reply each, plus 1 s and 12 s stated-delay variants; frozen automatic
grades, recomputed by a verifier; battle-start plans graded blind. In melee no model moved to
80 m (0-4 of 30); out of melee 15-29 of 30 re-charged; full plans: GLM-5.3 low 9 of 10, Kimi K3
low and high 6, Luna low and Qwen3.6 none 0. The stated delay changed nothing detectable (10
paired tests, none under p 0.05). OpenRouter $2.17 (Kimi K3 high's delay variants stopped at
10 of 60 on the cap), OpenAI $0.04 (Luna). Tool and evidence local in
`calibration/latency-review-20261018/probes/` (not committed); table in latency.md. All
exploratory past the frozen columns; nothing agreed.
- Offline follow-up ($0, recounted): in the 12 chariot 1.0 model battles pull-out depth does not
  separate outcomes (AUC 0.39, 3 + 6), gaps per minute does post hoc (0.96), and a younger
  median order age went with winning in 83% of pairs (corrects "speed does not separate").

## 2026-10-18: Latency program (plan only)

Owner notes (evening, away; [direction](../owner-direction.md)); plan in [latency.md](latency.md).
Read-only reviews, $0, each finding checked by a second agent; evidence local in
`calibration/latency-review-20261018/`. All unverified.
- Chariot card: foils score 0 cycles by construction; witness wins track the start
  configuration (4 discrete Swordsmen start pairs; near-tie starts won 7 of 8, others 1 of 6,
  post hoc) more than tempo; `verdict()` counts episodes, not launches; the model-pace gate was
  dropped against E2's own rule.
- Gap (30 model battles): wins only with the tactic stated before contact (5 of 10, else 0 of
  17); 4 of 5 slow decisive calls were retry loops; order ages omit calls never applied.
- The planner-executor design came from a "ChatGPT 6 Astra Pro" answer pasted on 2026-10-13;
  only `commander` was built.
- Corrected: witness cycles 6-9 (not 3-8), fixed-age witnesses 6 of 8 (not 5 of 5), read
  timeout 600 s (not 60 s).

## 2026-10-18: The chariot card, harness b32 to b34

Owner goal (afternoon, away, delegated): at least one good, reliable benchmark. 14 scripted
launches (16 battles), $0, every result unverified (no agreed check); [the card](tactic-cards.md#the-chariot-card-the-first-benchmark-card).
- b32 (`cabb246`) `HitAndRun`: leaves after 2 s of observed melee and rides away from both
  enemies (`CycleCharge` stuck about 30 s between them at 1.1). b33 (`f7db96a`)
  `SnapHitAndRun` (no dwell) and `battle/cards.py` with `twwarhammer3 card`: board from
  manifests and replays, the cycles signature, failure classes, verdict. b34 (`5396182`)
  pre-registers the rule.
- E1 (`calibration/e1`): `HitAndRun` won 3 of 3 at 5 s (no chariot lost) and lost 2 of 2 at
  model pace (5 s age, 5 s interval); `hold` lost on the timer (the AI defends), so it is no
  foil here. E2: `SnapHitAndRun` won 1 of 1 at 5 s and 2 of 3 at model pace.
- Under delegation (17:45 UTC, during E2's last launch): the model-pace witness is
  reported, not a gate.
- Round C1 (`calibration/c1`, 20 plans) stopped at the owner's return after 4: foils lost
  4 of 4, witness 1 of 1 at 5 s, 0 of 1 at model pace. Incomplete, not admitted.
- No model battle: the OpenRouter account holds $10 of credit with $9.62 used (the key's
  $50 limit is not the balance, which explains the HTTP 402); OpenAI has $0.57 left.

## 2026-10-18: Tactic cards, harness b28 to b30 and the overnight checks

Owner direction (night, then away until 13:00 UTC, delegated): define minimal battles each
won only by applying one tactic, run them overnight, find what only WH3 can test
([direction](../owner-direction.md), [definition and board](tactic-cards.md)). No check is
agreed, so every result is unverified; every battle is a row of the register.
- Built: b28 (`f063730`), b29 (`3ce750c`) and b30 (`bacd16f`): 11 card scenarios and steps
  in `scenarios.json`, and the diagnostics `PinThenRear`, `FireballSpam`, `PriorityStrike`,
  `CycleCharge`, `FlankLane` and `SlaveTarpit` in `battle/calibration.py`, each with a unit
  test. Panels drafted 22 cards (1 kept, 17 to revise, 4 dropped by adversarial critics)
  and surveyed other game benchmarks; a four-lens check corrected the board before commit.
- Ran: 63 single-episode launches (40 lost, 20 won, 2 policy failures, 1 budget stop) in
  seven chains (`calibration/n1` to `n7`; one-job plans chained so a failed job ends only
  itself), $3.60 on 21 model battles (register), 12:13 UTC last battle end.
- Chariot cycle (`grn-chariot-emp-swordsmen`): `CycleCharge` won 4 of 4 at 5 s with no
  chariot lost; models won 3 of 12 battles (Kimi K3 low, gpt-6.1-sol low, Kimi K3 high 1 of
  2), the first model wins on a small scenario, each with deliberate pull-outs and
  recharges; but foils lost only 3 of 4: rush-nearest's second launch won at 157 s without
  cycling, so the card leaks and needs a harder step.
- Expendables (`skv-ogres-slaves-emp-halberds-1`, after a one-halberd step): foils lost 2 of
  2, `SlaveTarpit` won 3 of 4; models won 1 of 5 (Kimi K3 low; GLM-5.3 high a policy failure).
- S1: gpt-6.1-sol low won at 305 s (a feint and a rear charge, alternated), the first model
  win on S1, while `PinThenRear` won 1 of 2 fresh and 0 of 2 at 5 s; Kimi K3 high lost
  (24 s order age). S5 is dropped as a spell-judgment card (`FireballSpam` won at modifiers
  1.0 and 1.1); flyers, giant and riflemen have no reliable witness yet (board).
- Higher reasoning modes at the 16,000-token cap: no battle ended in a policy failure on
  the chariot card (3 replies cut off at the cap), but GLM-5.3 high failed on the
  expendables card ("cannot fly" replies until its retries ran out); mean order age rose
  with the mode for Luna (4.8 to 8.8 s) and GLM-5.3 (3.1 to 7.7 s), not for Kimi K3.
- Process: N3 ended early by my error (I merged b30 during a running chain: one job stopped
  in setup, plans 12-19 never ran, among them S1's second fresh and 2 s launches); several
  plans were rewritten before they started, so some plan file names keep a replaced job.
  The two last repeats (N6) gave no result: gpt-6.1-sol stopped on the OpenAI cap
  (`budget_exhausted`, next call up to $0.567) and Kimi K3 low on an OpenRouter HTTP 402
  ("in_flight_budget_exhausted": the account's credits, not this project's ledger).
- **Harness b31** (`4c16944`) and N8 (`calibration/n8`, $0): the chariot card at modifier
  1.1 after its leak. Rush-nearest lost 2 of 2 (138, 154 s), attack-nearest lost 409 s,
  `CycleCharge` won 1 of 3 at 5 s (390 s; lost 327 and 255 s, N9): too hard for the
  witness, so the card sits between 1.0 and 1.1. 69 launches in all; last end 12:56 UTC.

## 2026-10-18: Harness b27, cleanup and the verification rule

Owner goal: improve the codebase first ([direction](../owner-direction.md)). No battles.
- Output cap 16,000 tokens (was 4,000) in `llm`, `llm_rules` and `commander`, for
  reasoning-on modes, and a 600 s socket read timeout (was 60 s; no OpenAI attempt so far
  took over 32 s). Unplayed: whether those modes now finish, and their latency.
- A Steam build other than the pin warns and is recorded (`deployment.steam_build_pinned`,
  doctor `warnings`); `watch` and the job `digest` repeat the warning. It no longer blocks.
- `play` refuses a ledger file that does not exist (a worktree or a typo would start at $0).
- The `wh3-version-review` judges also score "No change" (collect more evidence), and the
  judges' picks decide the returned winner.
- M1 re-checked: Sol 9/18 against Luna 1/18 pooled (Fisher p 0.007; 8/17 against 1/17,
  p 0.017, without the M1a caster launch); per scenario at most p 0.10 at three a side.
- Removed `BraceFacing`, which never played. S7's board status is now "timer win without
  contact"; the all-modes count is 34 configurations, not 26.
- Branches: 30 merged ones deleted; four stale drafts kept as `archive/*` tags.
Checks: the full test suite and ruff; none is an agreed verification method
([hard rule](../../AGENTS.md#verification-hard-rule)).

## 2026-10-17: Queue E3 (S5 and S7 wins), harness b26 and wrap-up

Queue E3 (`calibration/queue-e3-b25-20261017.json`, `d4338ea`, b25, $0). At 23:24 UTC the
owner asked to wrap up after the current battle; a docs-only commit moved HEAD, so the queue
started no further job after S5 (S3 Crossfire b24 and the L2 setup check remain unplayed).

| Job | Check | Outcome | Battle time | Notes |
|---|---|---|---|---|
| `bench-b25-s7-cornerhold-20261017` ep 0 | S7 Greatswords step, CornerHold, fresh | Won (timer) | 1205 s | The defender held to the timer |
| same, ep 1 | 5.41 s mean age | Won (timer) | 1205 s | |
| `bench-b25-s5-spell-20261017` ep 0 | S5 SpellWindow b25, fresh | Won | 440 s | b23's fresh episode lost on the timer |
| same, ep 1 | 5.41 s mean age | Won | 488 s | 1 invalid batch |

S5 now shows a fresh win: holding the wizard until each cast lands (b25) turned b23's
timer loss into a 440 s win. S7 with armour-piercing attackers shows wins at both ages
after its hold floor lost. Both are "win shown" on the board; their casts and hold geometry
were not reviewed beyond the outcomes, and a model screen is next for each.

**Harness b26** (`4ebf08e`): the fixes from a final review of the day's work (four area
reviewers and a completeness critic, every finding checked by an adversarial verifier).
- Transport (`gameai/llm.py`): a failed upstream response is resent unchanged up to twice
  on its own counter, so it no longer uses up the parse retries and blocks salvage; the
  cut-off notice needs `incomplete_details.reason == max_output_tokens` and a JSON error
  other than "Extra data". `battle/play.py` keeps an APIError's attempts in the failure, so
  the report counts a failed response that ends an episode.
- `SpellWindow` casts nothing while the wizard is in melee (it steps away first); the S9
  Trolls step inherits S9's family, so its split group stays with S9's earlier jobs.
- Data (`spire/fullrun/export.py`, `gameai/sft.py`, `scripts/sft_smoke.py`): Spire rows of the
  ten reserved evaluation seeds `HELDOUT01`-`HELDOUT10` (in any spelling the game reads as
  the same seed) are `held_out`; transport-failure attempts carry the contract's null fields;
  a request stopped mid-retry is labelled `Interrupted`. The builder gains `--require
  PATH=VALUE` on outcome and label fields, drops reasoning-on targets without reasoning text
  under `--reasoning`, and counts a target as retried only when its prompt changed. The smoke
  test reports validation loss before and after on fixed rows and an action-match rate.
- Docs: the owner's $50 OpenRouter allowance covers both OpenRouter ledgers (WH3 and Spire;
  $3.86 spent at 22:51 UTC); corrected counts in today's entries; Qwen3.6 in the controllers
  page; a CLI test of `spire play --provider`.

Checks after the merge: 1,241 tests and Ruff pass. The b26 smoke test on the cross-game Qwen
dataset (60 steps, Qwen3-0.6B) lowered the validation loss on the 55 rows of the unseen Spire
seed from 1.685 to 1.328; 16 of 16 decoded replies were valid JSON and 5 matched the
reference action. A schema-2 export of every finished WH3 episode (379 episodes, 15,085
rows, 681 of them from open-weight models) is in `exports/trace-v2-20261017`.

Open for the owner (also in [state.md](../state.md)): a training host and a route to play a
fine-tune back in both harnesses; a larger output allowance for reasoning-on modes; the
OpenAI-outputs terms question; whether Step 5 preview has open weights; intermediate steps
for S6, S8, S9 and S11.

## 2026-10-17: Queue E2 (Qwen3.6 on S1, step floors) and harness b25

Queue E2 (`calibration/queue-e2-b24-20261017.json`, `c8b221e`, b24): the WH3 half of the
post-training minimal test, then the five step floors declared in b24.

| Job | Check | Outcome | Battle time | Notes |
|---|---|---|---|---|
| `bench-b24-s1-qwen-none-20261017` ep 0 | S1, Qwen3.6-35B-A3B / none (`llm_rules`) | Lost | 172 s | 40 decisions, mean delay 4.2 s, 1 invalid reply, 1 refused order |
| same, ep 1 | S1, Qwen3.6 / none | Lost | 171 s | 41 decisions, mean delay 4.1 s, 2 invalid replies |
| `bench-b24-s6-floor-2-20261017` | S6 two Swordsmen, attack-nearest | Won | 461 s | Too easy at this step |
| `bench-b24-s7-floor-greatswords-20261017` | S7 two Greatswords, hold | Lost | 387 s | Not too easy; CornerHold is next |
| `bench-b24-s8-floor-2-20261017` | S8 two Trolls, hold | Won | 214 s | Too easy at this step |
| `bench-b24-s9-floor-trolls-20261017` | S9 Giant + Trolls, attack-nearest | Won | 328 s | Too easy at this step |
| `bench-b24-s11-floor-1-20261017` | S11 one Rock Lobber, attack-nearest | Won | 469 s | Too easy at this step |
| `bench-b24-s1-qwen-medium-20261017` | S1, Qwen3.6 / medium | Policy failure | 64 s | 2 decisions, mean delay 29.1 s; no valid reply within the 4,000-token cap |

Qwen3.6 with reasoning off played S1 for $0.05 in both battles ($0.07 with the reasoning-on
job's $0.019). The 84 reasoning-off attempts all went to fp8 or bf16 endpoints (routing
constraint; Parasail 80, AkashML 4; snapshot `qwen3.6-35b-a3b-20260415`), each request
recorded with the sampling and quantization filter; 3 invalid replies were retried and
every decision ended with an accepted reply (124-348 output tokens, 2.0-7.8 s per call).
With reasoning on, the battle ended at its third decision, as the live checks predicted.
The export and dataset of this job are part of the post-training test (Spire entry of the
same date, [posttraining.md](../posttraining.md)).

Four of the five step-downs overshot: S6, S8, S9 and S11 were too hard at their original
step and are too easy now. Each needs an intermediate step (for example the original
rosters at a lower AI stats modifier, or a weaker unit in place of the removed one); not
declared tonight. S7 with Greatswords holds.

**Harness b25** (`726770d`): two reviewed branches.
- `SpellWindow` (*delegated*, from the S5 review): after an acknowledged cast the wizard
  gets no other order until the spell shows its recharge (Fireball) or effect (Flame Storm),
  or 6 s pass; "not ready" alone is not a landing, because it also appears when the cast
  takes the magic. It flees during a hold only in melee, the post move is no longer re-sent
  after each cast, and Flame Storm is never aimed at an enemy heading at the wizard (within
  45 degrees). Replaying the b23 S5 episodes, casts followed by another wizard order within
  2.4 s drop from 172 to 1 (fresh) and from 28 to 0 (5 s).
- L2 (`ksl-ffa-grn-dwf-12`, scenario version 2; *delegated*): a fourth army, Empire with 12
  units (6,875 database cost, the same as the Greenskin and Dwarf sides), and funds 15,000,
  so the free-for-all lobby accepts it. A regression checks every free-for-all scenario
  declares four sides.

## 2026-10-17: Queue E1, harness b24 and post-training data capture

Owner goal (19:10 UTC, away, no questions possible): "Review the repo in terms of its
preparation for post-training experiments. Review whether we're collecting data properly,
check and improve the quality of related code, prepare the structure required to
fine-tune an open model with OpenRouter (and do an initial minimal test run for this, with
both games)." Shortly after: "While I'm away, see if you can run more of the planned TW3
games in the background". Choices marked *delegated* were made under these and are open
to review. The cross-game pipeline is on [posttraining.md](../posttraining.md).

Queue E1 (`calibration/queue-e1-b23-20261017.json`, `40c40f7`, b23, $0): the board's
ready checks, which needed no new code.

| Job | Check | Outcome | Battle time | Notes |
|---|---|---|---|---|
| `bench-b23-s3-crossfire-3-r3-20261017` ep 0 | S3 Crossfire, fresh | Lost (timer) | 1205 s | Guns fired 314 of 2,992 rounds; the dwarves kept 204 of 225 men; 1 refused move |
| same, ep 1 | 5.41 s mean age | Lost (rout) | 1162 s | No rounds fired; 219 of 225 men left; 14 refused moves, 13 of them off the map |
| `bench-b23-s5-spell-20261017` ep 0 | S5 SpellWindow, fresh | Lost (timer) | 1205 s | 177 Fireballs accepted, 4 landed; 72 of 80 magic spent; 116 of 180 enemy men left; spearmen routed at 360 s |
| same, ep 1 | 5.41 s mean age | Won | 524 s | 41 Fireballs ordered, 7 landed (about 98 kills); both Swordsmen units routed with 54 men left; the wizard unhurt |
| `bench-b23-l1-setup-20261017` | L1 setup, attack-nearest floor | Lost | 523 s | The 20-unit pitched battle set up and ended in an engine result |
| `bench-b23-l2-setup-20261017` | L2 setup | Setup failure | n/a | The lobby refused: "Free-For-All requires 4 teams"; L2 declares three sides |

S3 (`calibration/s3-crossfire-3-r3-review-20261017.json`): replaying the logged
observations through `Crossfire` reproduced every decision, so the play ran as disclosed,
and b23 cut refused moves from hundreds to 1 and 14. The play itself kept the guns silent.
At three units the AI sends free Dwarf Warriors after the guns; a gun shot only from its
post, which moved with the target's facing every tick, and ran 120 m from any enemy within
50 m without shooting. When the play did happen it worked: one gun on a flank post fired
246 rounds in 55 s. The spearmen carry the lordless army's commander flag, and their
captain's death cut every unit's morale. Separately, the two-cell step ring that moves a
destination off blocked ground was not clamped to the map, and `_clear` treated off-map
points as open.

S5 (`calibration/s5-spellwindow-review-20261017.json`): the play ran as disclosed (the
replay reproduced every decision), and the win counts as "win shown" with an S4-style
qualifier: Fireball kiting won, and the named spell-window choice never mattered. An `ok`
acknowledgement is not a cast. A Fireball spends its magic 1-4 s after the order applies,
and any later order to the wizard cancels it; `SpellWindow` re-sent its post or flee move
right after each cast, so none of the 192 Fireballs followed by another wizard order
within 2.4 s spent magic. All refusals were re-casts on cooldown (episode 1's from the 5 s
old view). Six Flame Storms at enemies running at the wizard used 78 magic for about 2
kills; Burning Head was never in range. Episode 0 lost mostly by chance: one Swordsmen unit
left the melee earlier and stronger to hunt the wizard. Next: hold the wizard until a
cast confirms, drop Flame Storm on moving targets, then a 0/5 s pair; a model screen only
after a fresh win. The cast-cancel fact could also enter the model prompt (a logged
version). The probe floor's single overnight cast is explained too: `probe_abilities`
casts only abilities whose target is exactly "Self" or "Around self", in melee, and every
fire spell targets an enemy or the ground.

L2 needs a fourth side (or a different battle type) before it can be played; not changed
tonight.

**Harness b24** (`87b370b`) merges four reviewed branches:
- Diagnostics (`battle/calibration.py`): every step ring stays on the map and off-map points
  count as blocked (CrossKite and HammerAnvil cards say so). *Delegated:* Crossfire fixes
  each gun's post when the pin starts; a gun with the pinned unit in range shoots it from
  where it stands; it shoots an enemy that comes within 50 m while that enemy stays in
  range, instead of running; without the spearmen, each gun shoots the nearest enemy in
  range or halts. Replays of every earlier diagnostic job through b24 change no decision
  except CrossKite's moves at the map edge. The guns will now mostly fire from their wait
  spot rather than from flank posts, so S3 tests fire past one's own melee more than
  crossfire geometry.
- E2 steps (`configs/twwarhammer3/scenarios.json`, `report_notes.json`; *delegated*, run
  as "planned games"): `emp-knights-emp-swordsmen-2` (S6, two enemy Swordsmen),
  `dwf-longbeards-emp-greatswords-2` (S7, two Greatswords replace two of four Swordsmen;
  funds 2,750), `dwf-thunderers-grn-trolls-2` (S8, two Trolls), `grn-giant-ksl-streltsi-trolls`
  (S9, the Giant plus one Troll unit, funds 2,400; MonsterTarget gives both monsters one
  target, so a loss says nothing about splitting them) and `dwf-cannon-grn-lobbers-1`
  (S11, one Rock Lobber). Costs come from the game database; each runs its floor first.
- Post-training (shared with Spire; [posttraining.md](../posttraining.md)):
  - Qwen3.6-35B-A3B (`qwen/qwen3.6-35b-a3b`), the open-weight model to fine-tune, is
    declared on OpenRouter. *Delegated:* efforts `none` and `medium` only. Live checks
    (2026-10-17, Spire and WH3 reply schemas, $0.0140 in all: $0.0097 in the Spire
    OpenRouter ledger, $0.0043 in WH3's): every effort value was accepted, `none` did not
    reason (76 and 273 output tokens, 3 s), and low to max reasoned 1.3k-4k tokens without
    scaling. It routes only to fp8 or bf16 endpoints (the cheapest is fp4) at $0.15/$1.00
    ceilings, with the model card's sampling sent explicitly (temperature 1.0, top_p 0.95).
  - Thinking-on Qwen exhausted the 4,000-token output cap in 2 of 5 live calls (both
    `medium`, one per game), which adds to the open output-allowance question.
  - Transport (`gameai/llm.py`): a failed upstream response (the Kimi m28 shape) is resent
    unchanged within the retry allowance and kept once in the attempts; a reply cut at
    the output limit that is not valid JSON gets a neutral cut-off retry notice; a body
    truncated during the read is retried and charged as uncertain.
  - Parsers (`battle/llm.py`, `commander.py`, `protocol.py`): off-schema replies (wrong
    top-level types, missing keys, huge integers, deep nesting) are retried and end as
    invalid or policy failures instead of infrastructure failures. Valid replies and the
    prompt fixtures are unchanged; commander assignments may still omit target and point.
  - Export schema 2 (`battle/export.py`, [traces.md](traces.md)): rows carry `game`,
    `group` (scenario family, else name; random draws by seed) and `split`; ids no longer
    depend on the checkout path; `error` is always null or `{type, message}`; the
    duplicate per-attempt system prompt is dropped (about 120 MB of the 567 MB export).
  - The report counts a provider's failed responses apart from rejected replies.

Validation: 1,204 tests pass and Ruff passes on `87b370b`. The new dataset builder and the
local smoke trainer ran end to end on the existing OpenRouter evidence (12 jobs, 597 rows,
575 kept; 475 GLM rows (reasoning on, trained without it) trained 30 LoRA steps on
Qwen3-0.6B, loss 1.81 to 1.62, adapter reloaded and verified, 4 of 4 decoded validation
replies valid JSON). By the student's tokenizer, WH3 rows are p50 4.9k and at most 7.0k
tokens.

## 2026-10-17: Overnight tranche, harness b18-b23

Owner goal (04:00 UTC, away until 13:00 UTC, no questions possible): "Continue the
Total War Warhammer 3 benchmark scenario implementation ... implement more things if you
finish earlier." This resumes the pending plan (small scenarios, then the GLM-5.3 / low
ladder). Choices marked *delegated* were made under that goal and are open to review.
Game jobs end before 13:00 UTC.

Queue A (`calibration/small-checks-b17-20261017.json`, `1117518`, $0):

| Job | Check | Outcome | Battle time | Notes |
|---|---|---|---|---|
| `bench-b17-s2y-floor-20261017` | S2 Mounted Yeomen floor, attack-nearest | Won | 326 s | Slayers left with 1 man; one archer unit caught at 203 s and destroyed with 346 arrows left, the other spent all 810 without melee |
| `bench-b17-s4-bodyguard-20261017` ep 0 | S4 Bodyguard, fresh | Lost | 219 s | Gun fired 36 of 594 rounds; crew routed at 139 s |
| same, ep 1 | S4 Bodyguard, 5.41 s mean age | Won | 503 s | Gun lost (routed 276 s); the Halberdiers routed both Yeomen units (2/45 left each), then the Men-at-arms |
| `bench-b17-swarm-slayers-check-20261017` | Swarm + two Slayers, CoordinatedRush | Lost | 429 s | Setup and engagement check: both Slayer units fought from 142/162 s and fell to 2 and 14 of 60; Rat Ogres and Doomwheel destroyed; 42% own / 67% enemy men left |

S2's weaker roster is still too easy under the floor rule. *Delegated:* the second step
is `brt-archers-dwf-slayers-hard`, the repository's `-hard` convention (AI stats
modifier 1.1, armies, map, timer and funds unchanged). It is the smallest step that
keeps the decision problem; the draft's Dwarf Warriors decoy adds a second question
and may make the battle unwinnable once the arrows are spent.

S4 now has a scripted win, but under delay and without the gun surviving, so the
escort's melee did the work. The fresh episode exposed a diagnostic defect: Bodyguard
re-picked the nearer of two almost equidistant riders on every decision. The gun was
re-ordered five times between 37 s and 39 s, and from 88 s the Halberdiers switched
targets about fifteen times. b18 keeps one target until it routs or another is 30 m
nearer the gun (disclosed on the card; regression test added). The 5 s episode
re-ordered less often, which may explain part of the difference. Review:
`calibration/s4-bodyguard-review-20261017.json`.

b18 adds the remaining draft candidates S3, S5 and S6 as development declarations
with disclosed diagnostics (`battle/calibration.py`), outside the core selection:

| Id | Scenario | Player / enemy (draft costs) | Funds | Diagnostic |
|---|---|---|---|---|
| S3 | `emp-handgunners-dwf-warriors` | Spearmen + 2 Handgunners (1,550) / 2 Dwarf Warriors (900) | 1,600 | `Crossfire`: spearmen pin the nearest unit; once it is in melee each gun takes a post 100 m away at its bearing +-80 degrees and shoots only it; fire-at-will off |
| S5 | `emp-wizard-emp-swordsmen` | Bright Wizard + Spearmen (600) / 2 Swordsmen (750), Empire mirror | 800 | `SpellWindow`: wizard 100 m behind its line; Burning Head along two enemies clear of friends, else Flame Storm on an unengaged enemy clear of friends, else Fireball |
| S6 | `emp-knights-emp-swordsmen` | Swordsmen + Empire Knights (1,225) / 3 Swordsmen (1,125), Empire mirror | 1,250 | `HammerAnvil`: infantry pins; knights wait, ride round to 70 m behind the pinned unit, charge, pull out after 8 s or a rout, repeat |

Queue B (`calibration/queue-b18-20261017.json`, `c3c3c29`):

| Job | Check | Outcome | Battle time | Notes |
|---|---|---|---|---|
| `bench-b18-s4-bodyguard-r2-20261017` ep 0 | S4 Bodyguard with target commitment, fresh | Lost | 269 s | Gun fired 30 rounds, routed at 93 s; Yeomen left 10 and 9 of 45 |
| same, ep 1 | 5.41 s mean age | Won | 534 s | Gun lost again (routed 188 s); both Yeomen units destroyed to 1 man, then the Men-at-arms routed |
| `bench-b18-s2-hard-floor-20261017` | S2 Yeomen floor at modifier 1.1 | Won | 330 s | 88 of 90 riders left; Slayers to 1 man with 1,144 arrows spent |

| `bench-b18-s1-glm-20261017` ep 0 | S1, GLM-5.3 / low (`llm_rules`) | Lost | 173 s | 30% own / 76% enemy men; $0.084; mean delay 4.3 s |
| same, ep 1 | S1, GLM-5.3 / low | Lost | 183 s | 29% / 71%; $0.083; 2 routing refusals |

GLM named the right play and did not execute it. Its first reasoning reads "Cycle-charge
from both sides. Move f1 to west flank, f2 to east flank, then converge", and its
notes plan "a simultaneous two-flank charge". The orders it sent were two direct
`attack` orders on the halberds from 530 m, which the engine carries out as a frontal
charge (approach 1-2 degrees off the enemy front), in both battles. The outcomes match
the frontal floors. S1 thus separates the disclosed flank (a fresh-observation win)
from this model's play, and the failure is executing a stated plan, not knowing it.
Review: `calibration/s1-glm-review-20261017.json`.

| `bench-b18-siege-anchor-glm-20261017` | Siege anchor, GLM-5.3 / low | Lost | 606 s | 31% / 46%; $0.456; mean delay 7.67 s (max 34.8 s); key building held throughout (victory_held 0.93) |

GLM's siege reference lost on morale, not on the objective: the army routed at 606 s
with about 600 s left on a timer that favours the defender. It held the outer wall and
gatehouse instead of trading territory: six of eight units never left their start
line. It charged the Bull Centaur reserve into Trolls at the gate at 62 s, seven
seconds after a note keeping it in reserve; the Centaurs routed at 327 s, and five more
units routed between 340 and 460 s before an army-losses shock broke the rest. It spent
5,364 of 6,000 supplies at 5 s on six cheap piercing towers 120 m or more behind its
line, then let income pile up unspent (4,255). Plan and orders diverged again: casts announced
as flight orders for a unit that cannot fly, a withdrawal sent as an attack, a reason
reading "placeholder", and two replies of 12-13k characters that repeated one order
until the JSON broke. The won `gpt-6.1-sol` battle (`bench-b12-m1c-siege-20261016`
episode 1) withdrew the whole army under its towers at 5 s, kept the reserve until
284 s and won at 538 s. On this anchor Sol 6.1 won 3/3, Sol 3/4, Luna 1/4, GLM 0/1.
GLM's siege ladder stops at the anchor; one more reference battle follows in queue C.

The swarm reference, `bench-b18-swarm-anchor-glm-20261017`, also lost: 536 s, 36% own /
49% enemy men left, 12 invalid orders, mean delay 7.8 s, $0.403. On this anchor Sol 6.1
won 3/3, Sol 2/3, Luna 0/4. With one battle per anchor, GLM-5.3 / low sits at or below
Luna on siege and swarm. *Delegated:* its added-factor steps (siege with three
cavalry, swarm with two Slayers) are not played with GLM, because a step above a lost
anchor says little. They wait for the stronger models, as planned. Queue C adds a
second reference battle on each anchor instead.

S3's first live check (`bench-b18-s3-floor-20261017`) passed setup: lordless Spearmen and two Handgunners at 1,600 funds against two Dwarf Warriors units. The attack-nearest floor won at 433 s: the Spearmen routed at 201 s with 29 of 90 left, but the guns kept firing (561 and 734 of 1,496 rounds spent), one gun unit routed briefly when caught in melee, and both dwarf units routed (9 and 45 of 75 left). Too easy under the floor rule. *Delegated:* step 2, `emp-handgunners-dwf-warriors-3`, adds a third Dwarf Warriors unit (the draft's first named step); funds stay 1,600.

S4's pattern repeated, but in both jobs the fresh episode was the first battle and the
delayed one the rematch, so delay and episode order are confounded. Queue C runs four
episodes with rotation seed 4 (5, 0, 0, 5 s) to separate them. In every S4 battle the
riders reached the gun around 70 s, after about 30-50 of its 594 rounds; the escort's
melee, not the gun, decided the wins.

Queue C's order check (`bench-b19-s4-bodyguard-order-20261017`, rotation seed 4) ran
5, 0, 0 and 5 s: won 548 s, lost 217 s, won 561 s, won 451 s. Across the three Bodyguard
jobs the 5 s arm won 4 of 4 and the fresh arm 1 of 4, so the delayed wins are not a
rematch effect. The two 5 s episodes of this job are identical in rounds fired (42),
gun rout time (96.7 s) and order count (11): with snapshots held to a fixed age, the
battle replayed exactly. Every Bodyguard battle lost the gun by 97-141 s after 37-42
rounds, so the escort's melee wins, not the gun's protection. S4 therefore has a
demonstrated executable win but does not yet test its named skill. A later step should
make the gun's survival decisive (for example a stronger infantry enemy that the escort
cannot beat alone). Review: `calibration/s4-bodyguard-order-review-20261017.json`.

S2 did not bind at either stat step: the game's own skirmish mode does the kiting, and
both attack-nearest floors won. *Delegated:* one last S2 step, the draft's named decoy
(`brt-archers-dwf-slayers-decoy`: one Dwarf Warriors unit added at modifier 1.0, funds
1,500), with `CrossKite` now preferring visible Slayers (disclosed). If its floor also
wins, or it looks unwinnable, S2 is set aside for the owner's review.

Queue B stopped at its seventh job: the S5 lobby refused readiness ("a player has
spent too much on their army setup") at 800 funds, although the database costs, read
with `scripts/wh3_db.py` from a freshly downloaded RPFM schema, sum to 600 (wizard 250,
spearmen 350) and 750. A character's lobby price evidently exceeds its database cost.
No battle started; the S6 floor did not run. Database costs otherwise match the draft
(Slayers 900, so the S2 decoy needs its 1,500 funds).

b19 (`wh3-b19-large`, merged between queues) adds:
- L1 `emp-pitched-grn-20`: the draft's 20-unit Empire and Greenskin armies with lords,
  Taurox, 2400 s; protected wizard and guns. Setup/scale check only; no scripted win
  is expected.
- L2 `ksl-ffa-grn-dwf-12`: three-way free-for-all on `ffa_04`, 2400 s, Kislev's 12
  drafted units against AI Greenskins and Dwarfs. The two AI rosters are new choices
  sized near the draft's totals. `setup.py` already adds AI slots to match the armies.
- S7 `dwf-longbeards-emp-swordsmen` (2 Longbeards defending against 4 Swordsmen) with
  the disclosed `CornerHold` diagnostic: take the nearest map corner the army reaches
  before the enemy, form a line of two facing the map centre, and hold.
- S2's decoy step and S3's three-unit step (above).
- Funds headroom where characters or exact totals risk the S5 refusal: S5 1,200, S7
  1,600, L1 12,000 (draft 10,500), L2 9,000 (7,500). Rosters are fixed, so funds only cap
  recruitment; the change is recorded in each `calibration_change`.

b20 (`wh3-b20-small2`) adds a second batch of small candidates for diversity, defined in
[small-scenarios-2.md](small-scenarios-2.md) with database costs and kept apart from
hypotheses. *Delegated:* the owner asked for many small one-or-two-skill battles, and
the first batch leaned on Empire, Dwarfs, Bretonnia and Kislev. The four declared ones
get only free setup/floor checks tonight:

| Id | Scenario | Skill | Player / enemy (database cost) | Funds |
|---|---|---|---|---|
| S8 | `dwf-thunderers-grn-trolls` (defend) | Focus fire against regeneration | 2 Thunderers + Dwarf Warriors (1,850) / 3 Trolls (2,250) | 2,500 |
| S9 | `grn-giant-ksl-streltsi` (attack) | A lone monster's target choice | Giant (1,400) / Kossar spears + Streltsi (1,350) | 1,600 |
| S10 | `skv-spears-sla-hellstriders` (defend) | Receiving cavalry: facing and bracing | 3 Clanrat Spearmen (975) / 2 Hellstriders, never rout (1,350) | 1,500 |
| S11 | `dwf-cannon-grn-lobbers` (attack) | Counter-battery before advancing | Cannon + Dwarf Warriors (1,250) / 2 Rock Lobbers + 2 Goblin Spearmen (1,750) | 1,950 |

S12 (rally and leadership) and S13 (fatigue) are defined but not declared; the draft
judges both weak. No diagnostics yet for S8-S11.

The S2 decoy floor (`bench-b19-s2-decoy-floor-20261017`) lost at 483 s: setup passed at
1,500 funds; attack-nearest split its orders between Slayers (387) and Warriors (273),
spent 1,595 of 1,620 arrows, took the Slayers to 1 man and the Warriors from 75 to 74.
One archer unit routed at 205 s and the other at 483 s. The first S2 floor loss;
`CrossKite` (Slayers first) at 0/5 s follows in queue D to test winnability, since the
Warriors must still be broken without arrows.

S3's three-unit floor (`bench-b19-s3-floor-3-20261017`) lost at 403 s: the Spearmen routed
at 194 s, the third dwarf unit reached a gun unit by 189 s, and the guns fired only
317 and 326 rounds each. The dwarves ended at 61, 68 and 73 of 75. The step binds the
floor; `Crossfire` at 0/5 s follows in queue D.

Queue C stopped at its fourth job, the GLM S4 screen (`bench-b19-s4-glm-20261017`): episode 0
lost at 191 s; episode 1 ended at 294 s as a policy failure ("No valid reply after declared
retries"). The last replies, from the "Decart" backend, degenerated into run-on text and
hit the output-token limit, while GLM's preceding notes described a winning defensive
melee with both Yeomen units broken. That episode is an infrastructure/policy failure,
not a gameplay outcome. The remaining queue C jobs move to queue D.

Serving backends matter for open-weight models. Across tonight's four GLM jobs OpenRouter
spread calls over 18 backends. The share of attempts that failed parsing or validation
ranged from about 5% (DeepInfra, PrimeIntellect) to about 42% (InferenceNet, Modal);
Sail Research and Wafer, the busiest, were near 21-23%. The counts include both
decision and exchange records, so their absolute numbers may double-count, but the
rates compare. A model's measured play therefore partly reflects which backend
served each call. Proposal for the owner, not implemented: pin an OpenRouter backend
order (or a quantization) per model for benchmark battles, recorded in the card, and
compare one battle per pinned backend before relying on GLM/Kimi/Step results.

Queue D1 (`calibration/queue-d1-b20-20261017.json`, `d69bbf3`, $0) began with the S2 decoy
`CrossKite` pair (`bench-b20-s2-decoy-kite-20261017`): lost at 256 s (fresh) and 255 s
(5.42 s age). It was the diagnostic's first live use, and it failed on terrain: one
flank post lay inside the Taurox map's central rock, and the engine refused 144 and 289
moves while the diagnostic retried them. The Slayers fell only to 36 and 54 of 60.
b21 rotates a post up to 45 degrees around the target when it lands on a restricted
cell or near a refused move (disclosed; regression added). The pair is re-run on b21.

The S3 `Crossfire` pair (`bench-b20-s3-crossfire-3-20261017`) failed the same way: 415 and
517 unreachable refusals for one gun's flank post. The guns fired 68 and 0 rounds while
the Spearmen were destroyed; lost at 992 s (fresh) and on the 1205 s timer (5.41 s age),
with the dwarves at 75, 75 and 69-73 of 75. b21 moves the post rotation into a shared
`SmallDiagnostic.open_point`, used by `CrossKite`, `Crossfire` and `HammerAnvil`
(disclosed on each card). Both diagnostics are re-run on b21.

Queue D1 setup floors (all lordless rosters recruited; `calibration/s*-floor*-review-20261017.json`):

| Job | Scenario | Floor | Outcome | Battle time | Notes |
|---|---|---|---|---|---|
| `bench-b20-s4-floor-2-20261017` | S4 step 2 (two Men-at-arms) | hold | Lost | 161 s | Gun routed at 122 s after 39 rounds; neither infantry unit engaged |
| `bench-b20-s6-floor-20261017` | S6 hammer and anvil | attack-nearest | Lost | 490 s | Knights routed at 393 s (7 of 45 left); enemy 76, 58, 22 of 90 |
| `bench-b20-s7-floor-20261017` | S7 corner defence | hold | Won | 469 s | Longbeards 69 and 70 of 75; all four Swordsmen routed |
| `bench-b20-s8-floor-20261017` | S8 Thunderers vs Trolls | hold | Lost | 136 s | All three Dwarf units routed with 71, 52 and 46 men left; Thunderers fired about 60 rounds each; no Troll died |
| `bench-b20-s10-floor-20261017` | S10 spears vs Hellstriders | hold | Won | 207 s | The AI charged braced fronts head-on; both rider units routed (9 and 15 of 45) |
| `bench-b20-s11-floor-20261017` | S11 counter-battery | attack-nearest | Lost | 509 s | Goblin Spearmen routed (3 and 26 of 120), but the two Rock Lobbers (24 and 29 of 33) broke the Warriors and the cannon crew |

Floor losses get their disclosed diagnostic at 0/5 s in queue D2 (S4 step 2, S6, S8, S11).
*Delegated:* the two floor wins climb one step each. S7 goes to six Swordsmen (database
2,250; funds 2,500), since enveloping two units needs numbers. S10 adds a third
Hellstriders unit (enemy 2,025; funds 2,250). S10's live run also contradicts the draft's
database reading that Hellstriders never rout (`immune_to_psychology`): both units were
reported routing.

D1's last two jobs: S9's attack-nearest floor (`bench-b20-s9-floor-20261017`) lost at 542 s.
The Giant broke the Kossar spears (68 to 2, routed at 272 s), then the untouched Streltsi
shot it until it routed. Target order is the question, so `MonsterTarget` follows at
0/5 s. The S5 lobby refused readiness again at 1,200 funds, and the blocking slot was the
player's own. b21 gives S5 3,000, and raises L1 to 15,000 and L2 to 11,000 before
their first lobbies. A character's lobby price is unknown; rosters stay fixed.

b21 (merged after D1) holds the shared post rotation, the S7 and S10 steps and these
funds changes. Queue D2 runs the follow-up diagnostics, then the S1 mode pilot, S5's
floors, and L1/L2 setup checks, cut before 12:45 UTC.

Queue D2's first lobby stalled at the maps tab (`MailboxTimeout`, step 4 of 85; no battle);
the unchanged jobs were re-queued as D2b on the same revision.

The S2 decoy `CrossKite` re-run on b21 (`bench-b21-s2-decoy-kite-r3-20261017`) lost again:
262 s (fresh) and 283 s (5.42 s age). Post rotation cut unreachable refusals to 13 and
40, but about 1,450 arrows per episode killed only 8 and 25 Slayers and one Warrior; no
rider entered melee. At about 257 s both units took an "Army losses" morale effect with
no men lost, their leadership fell from 1.0 to below zero within five seconds, and the engine
ended the battle when both routed at full strength. The first pair collapsed at a
similar time. The cause is not visible in the observation. CrossKite also shoots
from an 85-145 m band set for Horse Archers (140 m range) although Yeomen reach 125 m.
*Delegated:* S2 work stops tonight. Its two stat steps were too easy, and the decoy step
lost its floor but has no demonstrated win. A range-aware CrossKite, or dropping S2
(engine skirmish mode automates its kiting), is the owner's call.

The S3 `Crossfire` re-run on b21 (`bench-b21-s3-crossfire-3-r2-20261017`) lost both
episodes on the 1205 s timer. The guns fired 22 and 0 rounds, and the engine refused 156
and 434 moves. b21's fallback was the defect: with every rotated post refused or
restricted, `open_point` returned the first candidate, which was retried indefinitely.
b22 returns no post in that case: guns and archers shoot from where they stand, and
`HammerAnvil` skips a blocked waypoint and charges (disclosed; regression added).
b22 also adds `digest --units` (per-unit men, ammunition, first melee and rout times,
and engine refusals), replacing the ad-hoc review script used tonight. It merged while
the S4 step-2 job played its last episode; the remaining D2b jobs continue as D2c on b22.

S4 step 2's `Bodyguard` pair (`bench-b21-s4-bodyguard-2-20261017`, D2b) lost at 227 s (fresh) and
346 s (5.41 s age). The escort again broke both Yeomen units (14-15 and 1-5 of 45 left),
but the gun crew routed at 122 s and 84 s after only 18 and 45 rounds. The two Men-at-arms
units, nearly untouched, then beat the Halberdiers. The step does make the gun's survival
decisive, but this disclosed escort cannot keep the gun alive past the riders' arrival
around 70 s. No win is demonstrated; the original S4 keeps its escort-melee wins.

S6's `HammerAnvil` pair (`bench-b22-s6-hammer-20261017`, D2c on b22) lost at 402 s (fresh)
and on the 1205 s timer (5.41 s age), with 147 and 139 refused moves. This time the
refused point was its wait post beside the infantry, inside the Taurox map's central rock
where the fight formed; that post never passed through the rotation helper. b23 applies
one rule to every diagnostic move: a destination on a restricted cell or near a refused
move steps to the nearest open spot within two terrain cells, or the unit holds
(disclosed in `SmallDiagnostic`; regression added). D2c's remaining jobs continue on b23
as D2d, with an S6 re-run.

S8's `FocusFire` pair (`bench-b22-s8-focus-20261017`) lost at 147 s and 149 s. The Trolls
reached the line by about 70 s and lost no one (12 of 12 in every unit) after 66-120
rounds per gun unit; all Dwarf units routed by 149 s with 34-51 men left. Focus did not
change the result, and nothing shown so far wins. Proposal, not run: a step down to two
Trolls (enemy 1,500) before any model screen. Without a win the scenario fails the
winnability rule.

S11's `CounterBattery` pair (`bench-b23-s11-counter-20261017`, D2d on b23) lost at 346 s and
564 s. Counter-battery fire worked (the lobbers fell to 20/12 and 14/9 of 33, routing one
in the first episode and both in the second), but the lone Warriors and the cannon then
lost to the two 120-man Goblin Spearmen blocks. The floor showed the reverse (spearmen
routed, lobbers intact). At 1,750 against 1,250 neither target order wins. Proposal,
not run: one Rock Lobber instead of two.

S9's `MonsterTarget` pair (`bench-b23-s9-monster-20261017`) lost at 276 s and 242 s. The Giant
went for the Streltsi first (68 to 17 and 38) but routed early; the Kossar spears were
never engaged. The floor did the reverse and lost later: it destroyed the spears, then
the Streltsi shot it down. Neither target order wins at 1,400 against 1,350.
Proposal, not run: rebalance (a second monster, or one enemy unit fewer) before the
target-choice question can be tested.

S6's `HammerAnvil` re-run on b23 (`bench-b23-s6-hammer-r2-20261017`) had no refused moves,
which confirms the b23 fix, but lost at 493 s (fresh) and on the 1205 s timer (5.41 s age).
The pinning Swordsmen routed at 308 s and 277 s; the enemy kept 51% and 73% of its men.
The cycle charges did not outpace one unit's collapse against three. Proposal, not run:
two enemy Swordsmen (check the floor first, since it may then win).

S7's six-unit hold floor (`bench-b23-s7-floor-6-20261017`) won at 612 s: Longbeards 58 and 39
of 75, all six Swordsmen units routed (10-49 of 90 left). Numbers alone do not bind; the
next step should change the attackers' quality (armour-piercing Greatswords), not add
more Swordsmen. Not run tonight.

S10's three-rider hold floor (`bench-b23-s10-floor-3-20261017`) won at 216 s: the AI again
charged braced fronts head-on and all three Hellstrider units routed (17-18 of 45 left).
The candidate depends on an AI behaviour that makes it trivial; *delegated:* set aside
unless a different enemy changes that.

S5's lobby passed at 3,000 funds (`bench-b23-s5-floors-20261017`). The Bright Wizard became the
army's commanding unit (class `lord`) and starts with items: a power stone and a bound
blast item. That explains a lobby price above its database cost. Its Lore of Fire keys include
`wh_main_spell_fire_the_burning_head`, `..._flame_storm` and `..._fireball` (plus upgraded
versions), so `SpellWindow`'s substring matching applies; magic started at 12 current, 68
reserve. Both floors lost: `probe_abilities` at 656 s and attack-nearest at 544 s, with
about 80% of the enemy left. The probe cast only once (the power stone at 571 s), so the
probe floor did not test magic; the cause needs a look before `SpellWindow` runs.

S1 mode pilot, first configuration: GLM-5.3 / high (`bench-b23-s1-glm-high-20261017`) ended
as a policy failure after three decisions. Its fourth reply was retried three times
on one backend (Wafer). Each time, 12-13k characters of reasoning used the whole
4,000-token output cap and left no JSON reply. The first call (PrimeIntellect) had
finished in 1,935 tokens. Higher effort modes need a larger output allowance (or a
separate reasoning budget) before the all-modes matrix can be measured. That is a harness
setting, recorded for the owner, not a statement about the model's play. D2d stopped
there; the remaining pilot battles (Step 5 Preview low/high, Kimi K3 low) ran as a final
mini-queue, D2e.

Step 5 Preview's first battles (D2e): low (`bench-b23-s1-step-low-20261017`) lost S1 at 230 s
with 17% own / 68% enemy men left. It made only four decisions, with a mean order delay of
60.1 s: two direct attacks on the halberds at 5 s and 30 s, a third at 173 s and a
halt at 186 s. Its cost was $0.061. High (`bench-b23-s1-step-high-20261017`) failed before
its first decision. Three attempts each spent 13-14k characters of reasoning, filled the
4,000-token cap and returned no reply ($0.035). Both high-mode configurations tried
tonight fail on the same output allowance. Kimi K3 / low closes the pilot (D2f).

Kimi K3 / low (`bench-b23-s1-kimi-low-20261017`, D2f) ended at 102 s as an infrastructure
failure: OpenRouter returned a failed response (`APIError`). It had made 27 decisions,
with a mean delay of 3.58 s, the fastest model tonight, at $0.135. The pilot thus
completed one battle per configuration only for GLM low and Step low; all three
high-mode or Kimi attempts ended in policy or API failures. Game work ended at 12:34 UTC.
OpenRouter spend for the night: $1.9333 to $3.5445, within the $10 working ceiling; no
OpenAI calls.

Every new lordless roster recruited once funds allowed. S5 needed 3,000 because its wizard
becomes the commanding unit with items; its ability keys match `SpellWindow`. Database
costs came from `wh3_db.py`, using an RPFM schema downloaded to the session scratchpad
(not into the repository). The report labels every new diagnostic and carries provisional
notes. No model prompt or observation contract changed on `main`.

Summary, with every candidate's row on the
[status board](benchmark-implementation.md#history):
- Wins shown: S1 (flank, fresh) and S4 (escort melee, mostly at 5 s).
- Too easy at every step tried: S2 (until the decoy), S7 and S10.
- No win yet: S3, S5, S6, S8, S9 and S11. For S3 and S6 the diagnostics were defeated by
  terrain until b23. S8, S9 and S11 look too hard, and step-downs are proposed.
- Not yet run: L1 and L2.
- GLM-5.3 / low lost every model battle it completed (S1 x2, S4, both anchors), and two
  others ended in policy failures.
- Mode pilot: high efforts of GLM and Step exhaust the 4,000-token output cap, Step low
  decides about once a minute, and Kimi low hit an API failure.

Delegated choices are marked above. Proposals waiting on the owner: the `llm_rules`
v21 branch, the OpenRouter backend pin, larger output allowances for high modes, the
step-downs, and whether to drop S2 and S10.

Validation: the WH3 and documentation suites pass on `main` (515 tests), and Ruff and
`git diff --check` pass. Every battle ran unpaused at 1x (checked: episode wall time
matched battle time). Rebuilt `reports/benchmark.{html,json,txt}` (140 jobs, 231 trials,
220 valid) and `reports/overnight-20261017.{html,json,txt}` (tonight's 40 jobs, 55
trials, 51 valid). The read-only doctor reported ready after the last job.

## 2026-10-17: Harness b17, small-scenario checkpoint; work stopped

The owner cleared the active goal and asked to wrap up. The b16 queue completed at
00:52:54 UTC, with no controller left running. No further game or API jobs were started.
Seven scripted battles completed in this tranche, all at unpaused 1x and $0 API spend:

| Scenario / check | Outcome | Battle time | Own / enemy men left |
|---|---|---|---|
| S1 walking frontal floor | Lost | 356 s | 28% / 68% |
| S1 running frontal floor | Lost | 217 s | 19% / 59% |
| S1 disclosed flank, fresh observations | Won | 336 s | 62% / 42% (enemy routed) |
| S1 disclosed flank, 5 s added age | Lost | 384 s | 29% / 20% |
| S1 corrected flank, 5 s added age | Lost | 566 s | 28% / 28% |
| S2 horse-archer attack-nearest floor | Won | 352 s | 81% / 0% |
| S4 hold-position floor | Lost | 160 s | 59% / 81% |

The final S1 retry (`bench-b16-s1-flank-r2-20261017`, `a882872`) exercised the rally
withdrawal rule and reduced routing refusals from 13 to 3, but still lost at 566 s
(mean order age 5.41 s). Both cavalry units routed with 25/90 riders surviving against
25/90 halberdiers. This independent launch had different initial positions (up to
7.66 m), so the outcome change cannot be attributed solely to the script correction.
Reviews: `calibration/s1-flank-r2-review-20261017.json` and
`calibration/s1-r2-start-comparison-20261017.json`.

b17 saves changes already prepared while that queue ran: the weaker S2 player roster
(`brt-archers-dwf-slayers`, two Mounted Yeomen Archers), and Bodyguard's gun-range guard
and earlier 120 m interception. A regression checks that the gun stays put outside
range and halts if its target leaves range. These changes have no live validation yet.
Report notes record completed outcomes; the canonical jobs list adds all six new jobs,
including both episodes of the first S1 diagnostic. The small candidates remain outside
the core selection. No model prompt or observation contract changed.

Next session, when requested: a bounded GLM-5.3 / low S1 screen, without further S1 bot
tuning; the weaker S2 floor and, if it loses, the disclosed kiting checks; S4 Bodyguard
at 0/5 s age; then model checks for surviving candidates. The cheap-reference ladder
has not started: GLM siege/swarm anchors, then siege with three added cavalry, swarm
with two added Slayers (free engagement check first), and caster with three cannons.
Initial cumulative OpenRouter ceiling remains $10 within the owner's $50 cap; its
ledger is unchanged at $1.9333. No further OpenAI battle fits the $52 cap.

The bots calibrate an eventual model benchmark: confirm the game/interface works,
reject trivial setups, and demonstrate meaningful executable alternatives. Their
losses do not prove impossibility. S1 now has such an alternative, but its timing
robustness is unresolved; S2 needs the harder step and S4 still needs a tactical win.
No new small scenario is admitted, and the broader two-step plan remains incomplete.

Validation: 495 WH3/documentation tests passed, Ruff and `git diff --check` passed.
The read-only Windows doctor reported ready with no running game. Rebuilt
`reports/benchmark.{html,json,txt}` (100 jobs, 176 trials) and
`reports/small-calibration-20261017.{html,json,txt}` (6 jobs, all 7 new battles).
The core page remains unchanged in scope; development evidence stays in JSON/text
and the separate small report. OpenRouter spend rechecked at $1.9333.

## 2026-10-17: Harness b16, lordless roles and small-diagnostic routing feedback

The S1 probe exposed ordinary commanding regiments labelled as lords. The classifier
now reserves `lord` for a commanding character (`com` in the game's land_units class),
keeping ordinary cavalry, missile cavalry, infantry and artillery roles. The separate
`commander` flag stays true. The shipped API documentation says `unit_class()` reads
land_units; the database confirms `com` for Kairos, the Overseer and Dwarf Lord, and
`art_fld` for the Helblaster. No model prompt or field shape changes. The S2/S4 live
checks below confirm their commanding units keep the right roles before model calls.

The first S1 delayed diagnostic lost at 384 s (29% own / 20% enemy men left), with
mean order age 5.42 s and 13 routing refusals. It charged alone when its partner routed
and repeatedly retried orders using snapshots older than a routing acknowledgement.
The diagnostic now withdraws the remaining rider while a non-shattered partner can
rally; all three small diagnostics defer a routing unit until a snapshot newer than
that acknowledgement arrives. These are disclosed diagnostic changes, not model tactics.
Regressions cover both observed failures. A second S1 check remains development data.

Also prepared, without changing anchors: siege with three added cavalry units
(one Boar Boyz, two Wolf Riders); swarm with two added Slayers in place of the
inconclusive Gyrocopter factor; caster with three added Warp Lightning Cannons.
GLM-5.3 / low first needs the siege/swarm anchor references. The swarm factor gets a
free setup/engagement check before its model battle. The paid tranche will use a
cumulative OpenRouter ceiling of $10, within the owner's $50 cap ($1.9333 spent).
Expect roughly $0.10-0.60 per ordinary GLM battle, allowing longer losing battles.
One battle per named question, review before further spending; no OpenAI calls.

The report now recognises `FeintFlank`, `CrossKite` and `Bodyguard` as disclosed scripted
diagnostics, and has provisional small-scenario notes. They remain outside the core
selection while calibration runs. Earlier evidence retains its original source and
class labels; it is not rewritten.

Live S2 setup passed on `a882872`: both Horse Archers are `missile_cavalry`, including
the commanding first unit; the commanding Slayers are `infantry`. Each archer unit
starts with 810 arrows, skirmish and fire-at-will enabled. This verifies the class fix
for an ordinary commander. The S2 floor (`bench-b16-s2-floor-20261017`) won at 352 s, with 73/90 archers alive,
zero invalid orders. The first unit exhausted all 810 arrows and lost one rider in its
late melee finish; the second retained 241 arrows and 29/45 riders. It briefly entered
melee from 163 s but escaped without routing. The original setup is too easy under the
floor rule. Next is the draft's weaker-player step, two Mounted Yeomen Archers, before
any diagnostic/model spending. Review: `calibration/s2-floor-review-20261017.json`.

S4 setup also passed on `a882872`: the commanding Halberdiers are `infantry`, the
Helblaster is `artillery` (not commander), and the enemy's commanding Men-at-arms are
`infantry`, beside two cavalry units. The game reorders the recruitment list; the
first recruited gun did not become commander. The gun starts with 594 rounds and
fire-at-will enabled. The hold-position floor (`bench-b16-s4-floor-20261017`) lost
at 160 s with 59% of its men left against 81% of the enemy's, zero invalid orders.
The gun had used 42 rounds before entering melee around 80 s and fired no more;
its crew routed while the Halberdiers were still fighting. This supports testing the
named escort/targeting hypothesis. Review: `calibration/s4-floor-review-20261017.json`.
Prepared for b17 before its first live use, Bodyguard gains a range guard: it must not walk the gun
forward by ordering a ranged attack outside its range. It also intercepts at 120 m,
rather than the draft's 65 m, to allow for about 45 m of rider travel during five
seconds of observation age; this is disclosed diagnostic knowledge.

Latest pre-queue validation: 494 WH3 and documentation tests passed, Ruff and
`git diff --check` passed. The queue is frozen to `a882872`.

Validation before live checks: the complete WH3 suite passed with the class correction
(447 passed, 1 skipped); after routing/rally changes, 11 calibration tests and Ruff
passed. Exact existing model prompt fixtures remained unchanged. Final queue results are in
the b17 checkpoint above.

## 2026-10-17: Small-scenario checks and cheap-reference ladder (b15)

Owner goal: proceed with the small scenarios and GLM-5.3 / low ladder, in that order,
within the existing caps. No OpenAI battles are planned. The first small tranche is
S1/S2/S4; each gets a naive floor and a disclosed public-state diagnostic at 0 and 5 s
observation age before any model screen. Review outcomes before changing a roster or
buying a battle. Later small candidates remain subject to the same checks.

The S1 setup/floor check on `15c2462`,
`bench-b14-s1-floor-20261016`, completed: both armies were lordless, the lobby read back
1,100 funds, and the battle verified two Horse Raiders against one Halberdier unit.
The lone AI held until contact. `attack_nearest` lost at 356 s, with 28% of the player's
men and 68% of the enemy's remaining; zero invalid orders and $0 API spend. It walked
until contact at about 230 s, so `rush_nearest` is also needed before attributing a
diagnostic improvement to flanking rather than running.

b15 adds the S2 horse-archer/Slayer and S4 Helblaster-bodyguard declarations plus three
small diagnostics in `battle/calibration.py`: `FeintFlank`, `CrossKite` and `Bodyguard`.
Their controller cards disclose their geometry, target preferences and timers. They
use public visible units only; rejected movement orders can retry, routing units are
excluded, and ammunition exhaustion changes ranged orders to melee. No model prompt or
observation contract changes. Engine execution and winnability remain to be checked.

The running control on `77726f1`, `bench-b15-s1-rush-20261017`, also lost:
217 s, own men 19%, enemy men 59%, zero invalid orders. Both frontal baselines lose.
The free `FeintFlank` pair used 0 and 5 s added observation age, with rotation seed
0 (fresh first), same scenario and unchanged source. Added observation age tests stale
sensing, not the model's full decision cadence. Read-only execution summaries live in
`calibration/s1-{walk,rush}-review-20261017.json`.

S1 `FeintFlank`, first arm (fresh observations), won at 336 s with 62% of the cavalry
left and 42% of the halberdiers surviving but routed. Zero invalid orders. Five charge
phases were issued; after the first, one approach in each pair was 160-174 degrees off
the enemy front when ordered. These are approach angles, not a claim that every entity
landed a rear hit. Both frontal controls lost, so this establishes an executable
alternative, not its necessity or the scenario's maximum difficulty. The 5 s arm lost
at 384 s with mean order age 5.42 s (29% own / 20% enemy men left),
13 routing refusals. Source and conditions were unchanged within this diagnostic pair;
rosters, loadouts, strengths and resources matched on rematch. The next diagnostic
revision and class correction are recorded in b16 above.

The lordless roster also exposed a classification defect: the engine nominates the
first regiment as commander (`is_commanding_unit` true), and the old Lua classifier
labelled it `lord` even when it was Horse Raiders or Halberdiers. This does not affect
the S1 diagnostics, which use ids and positions, but could hide an artillery commander from
class-based selection and misdescribe ordinary commanders to models. S4 later proved
to nominate its Halberdiers, not the gun. b16 corrects this: only character-class
commanders become `lord`; ordinary regiments keep their combat class and the independent
commander flag. S2/S4 live checks verified the ordinary commanding-unit classes.

Initial validation: 39 calibration/setup tests passed. New tests check charge/withdraw
sequencing, hidden-enemy exclusion, refusal retries, ammunition exhaustion and cavalry
priority without input mutation. Live results follow here.

## 2026-10-16: README refresh and repository cleanup

Pushed the main README refresh (`ea590eb`): recorded replay animation, scenario index,
model-comparison figure and introductions to both games. The previews' date, source
report hash and battle are recorded in [reports.md](reports.md#readme-visuals).

The repository audit found no tracked build artifacts, empty files, exact duplicate
files or broken symlinks. Removed about 13 MB of temporary README captures and two
Windows `Zone.Identifier` sidecars. Deleted the fully merged local branches
`wh3-llm-range`, `wh3-llm-v17` and `wh3-obs-last-state`; the four branches with unmerged
work remain. The existing local plugin selection is preserved and excluded through
this checkout's `.git/info/exclude`, without changing shared ignore rules.

Shortened duplicate status/next-step text and corrected obsolete claims about OpenRouter
battles, the v20 live check and reasoning capture. Added the exporter and separate
OpenRouter ledger to the repository/evidence references. Saved runs (about 21 GB,
including about 16 GB of intermediate training checkpoints), historical reports and
unique branches remain; the three spend ledgers were checked byte-for-byte unchanged.
Engine cleanup that needs live validation remains deferred in [README.md](README.md#next).
No source, prompt, scenario or result-register changes; no game or paid API calls.

Validation: 44 documentation checks, Ruff and `git diff --check` passed. README assets
also passed the earlier desktop/phone layout and offline browser checks.

## 2026-10-16: Harness b14, offline trace export and model-exchange capture

Implemented the owner's trace-export goal. `twwarhammer3 export JOB [JOB ...] --output DIR`
writes one JSONL row per model request, all raw reply attempts, exact prompts including
retry feedback, validated order batches, engine acknowledgements, episode outcomes and
shared measures. Source manifests, environments, results and hashes are retained in
`sources.json`; `datacard.md` describes coverage and limitations. Filters select model,
controller/prompt version or exact system-prompt hash. The destination must be new and
outside source jobs. Hash mismatches, malformed traces and unfinished evidence fail
without publishing a partial export. [Usage and schema](traces.md).

Asynchronous commander replies are paired with their earlier prompts. Executor batches
belong to the adopted plan until the next adoption; initial default-skill ticks are not
model actions. Historical final replies and failed-call prompts that were never recorded
remain missing, not inferred from neighbouring turns. Old retry prompts are reconstructed
only with the recorded transport-source hash and revision available. Prompt versions from
old job names are labelled as such; exact prompt hashes and source revisions remain primary.

Future WH3 calls opt into exact request/output capture, including returned reasoning
items, transport failures and replies completed during commander shutdown. OpenAI
reasoning modes request `summary: auto`; OpenRouter retains returned output items without
a new routing parameter. Capture is off for Spire. Model input prompts remain v20 / v7,
and new manifests identify `model_exchange_version: 1`. Summary capture can affect API
cost/latency; the request setting is offline-tested and awaits its first paid call.
No game or paid API call ran, so the results register and ledgers are unchanged.

Artifact: `exports/trace-v1-20261016/`, selected by `exports/jobs-20261016.json`: 165 stopped
jobs, 304 episodes, 206 with model rows; **14,644 requests, 15,032 reply attempts and
25,504 executor/order batches**. Three unfinished source jobs were excluded explicitly in
`exports/excluded-20261016.json`. Missing-data counts: 24 historical unrecorded replies;
one failed direct call without its prompt (and therefore its retry prompt); 145 requests
with an unacknowledged execution step. Old traces do not contain reasoning output items.
An independent read of every row against the source JSONL verified prompt/reply identity,
commander ownership, orders, acknowledgements, outcomes and all 948 unchanged input files:
`exports/verify-20261016.py` and `exports/verification-20261016.json`.

Validation: `uv run ruff check .`; full suite 1,102 passed, 14 skipped, followed by 78
focused exporter/model/doc checks after the final filters and documentation. Regressions cover exact retry
inputs, late commander replies, failed calls, Spire's unchanged capture defaults, source
integrity, version/model/hash filters and export CLI behavior. No engine mechanic changed.
Small-scenario probes, further ladder battles, training and off-machine backups remain
outside this implementation.

## 2026-10-16: Owner decisions after ladder V1 (plan only)

The owner answered the open questions late on 2026-10-16 and asked for the plan to be
updated without implementation: try the small scenarios (S1 probe, then scripted
checks for S1, S2 and S4); continue the ladder with a cheaper reference model for now,
returning to expensive models later (GLM-5.3 / low proposed); write a trace exporter
and store reasoning text. Details and order:
[benchmark.md](benchmark-implementation.md#history).

## 2026-10-16: Difficulty ladder, first step (V1)

gpt-6.1-sol / low won all three battles on both anchors, with margin: siege defence at
538-587 s with 58-78% of its strength left, swarm command at 449-497 s with 50-52%.
gpt-6-sol also won the siege 3/3 and the swarm 2/3. Caster assault followed after the
v20 check below: gpt-6-sol and gpt-6.1-sol 3/3 each, GLM-5.3 one of two. Step 3 of the
[plan](benchmark-implementation.md#history) applies: a clear easy win motivates one harder
variant, changing one justified factor that presses on the family's scarce resource
rather than inflating stats. The anchors stay unchanged.

| Variant | Factor | Enemy cost | Question |
|---|---|---|---|
| `chd-reserve-grn-siege-flankers` | Enemy mobility: adds 2 Orc Boar Boyz and 2 Goblin Wolf Riders, the attacker's first cavalry | 9725 → 11625 (+20%), 20 units | Does one mobile reserve still cover the gun positions when fast units arrive early or by another route? |
| `skv-swarm-dwf-line-gyrocopters` | A threat the screen cannot block: adds 2 Gyrocopters | 8200 → 9800 (+20%), 11 units | Can the weapon teams, cannon and Warlock Engineer keep their protected time against flyers? |
| `tze-caster-skv-assault-cannon` | Pressure on the caster: adds a second Warp Lightning Cannon (projectile range 430 m, may target airborne units, 260 armour-piercing damage) | 3775 → 4725 (+25%), 11 units | Do casting position, flight and escort use still allow spell windows when the caster can be shot from long range? |

Funds caps, maps, timers, AI modifiers and the player rosters are unchanged; the lobby
lists every added card for those factions (`cards_slot1.txt` of the M1c jobs).

Tranche V1, decided under the owner's standing resume direction (continue calibration
within the existing budgets) and reviewable:
1. V1a, $0: one scripted battle per siege/swarm variant, `hold` on the siege (anchor:
   lost at 709 s) and `rush_nearest` on the swarm. Checks that the lobby takes the rosters,
   where the added units go and how fast a floor controller now loses. A setup failure or
   added units that never engage sends the variant back before any paid battle.
2. V1b: the caster variant's $0 check (`CasterSkirmish`, anchor: lost at 581 s, Kairos's
   barrier first down at 473 s), then one gpt-6.1-sol / low `llm_rules` v20 battle on each
   of the siege and swarm variants, with a cumulative OpenAI ceiling of **$50.00** (now
   $45.96). The anchors cost $0.90-1.11 per battle; a longer losing battle may cost up to
   about $2. M1c used v18, so the controller version also differs (v19/v20 changed only
   ability, routing and magic feedback).
3. V1c, after reviewing V1b: the caster variant's paid battle, if its check passes and
   budget remains.

Decision rule per variant, one battle each: a clear win with a similar margin says the
factor does not bind, so the next step is a different factor, not a repeat. A loss or
a narrow win, with the trace showing the added units forcing a reserve or protection
choice, makes the variant a candidate for the small frontier screen. A loss caused by
an interface failure, or by units the controller could not see or reach, sends it back.
One battle is not a ceiling estimate. Revised by the owner's difficulty target
(2026-10-16 evening, [benchmark.md](benchmark-implementation.md#owner-goals)):
a variant won with margin gets a further step; the family keeps its hardest step with a
demonstrated win, so a lost step needs a win (or is stepped back) before admission.

**V1a siege** (`bench-b13-v1a-siege-flankers-hold-20261016`, `f89a9b5`): the lobby took the
20-unit roster; `hold` lost at 708 s (anchor 709 s, an independent launch). The added
cavalry engaged: both Boar Boyz units charged the gate area and shattered under fire
(routing at about 150 s and 340 s); the Wolf Riders passed the line and reached the key
building's area (z ≈ 290-320) by 440-580 s, one unit at 17 of 60 men. Under a static
controller the infantry decides the timing; the riders put a threat behind the line,
which is the reserve question. Passes to V1b.

**V1a swarm** (`bench-b13-v1a-swarm-gyros-rush-20261016`, `f89a9b5`): the lobby took the
11-unit roster; `rush_nearest` lost at 314 s (anchor 288 s, independent launches). Both
Gyrocopters stayed airborne and closed to 8-60 m of the Doomwheel, Rat Ogres, slaves and
Warlord from about 90 s on. They were under fire in 479 samples yet ended with 17 of 18
men, so the Skaven ranged units barely hurt them. A win may then depend on breaking the
Dwarf army so the flyers rout with it, a risk to read in V1b rather than a reason to stop.
Passes to V1b.

**V1b, first attempt** (`672fc0e`, 20:06 UTC): stopped in the lobby before any battle or
API call. The caster variant's added `wh2_dlc12_skv_inf_warplock_jezzails_0` card was
found and double-clicked but did not recruit (10 enemy units, 11 expected). No scenario
had used `dlc12` content; The Prophet & the Warlock is presumably not owned on this
account. The variant now adds a second Warp Lightning Cannon, a `wh2_main` unit the
swarm anchor recruits, as `tze-caster-skv-assault-cannon`; V1b reruns as a new plan.

**V1b2 caster check** (`bench-b13-v1b2-caster-cannon-skirmish-20261016`, `82a2364`, $0):
the lobby took the roster; `CasterSkirmish` lost at 644 s (anchor 581 s). The added factor
binds on the caster: Kairos lost HP from 79 s and his barrier was down by about 96 s
(anchor: 491 s and 473 s), so the script spent most of the battle withdrawn to recover
and cast six spells instead of twelve, all with later active/recharge feedback. Kairos
was airborne throughout and died at 633 s with 20 magic left. Nothing attacked the
cannon (42 of 42 crew at the end), a play this script does not have. Review:
`calibration/cannon-caster-review-20261016.py` and JSON. Passes to V1c.

**V1b2 siege, paid** (`bench-b13-v1b2-siege-flankers-sol61-20261016`, `82a2364`, gpt-6.1-sol
/ low, `llm_rules` v20): **lost** at 629 s by army rout, 19% of its strength left against the
enemy's 54%; the key building was held throughout (victory point 81% of samples) and no
tickets were lost. 144 decisions, 8 invalid orders, mean delay 4.34 s, $1.20630000; the
OpenAI ledger is $47.17. The same model won all three anchor battles (v18).

Independent review (subagent, trace evidence; one battle, so causes are hypotheses).
All four cavalry units were visible from 5 s. They did not flank: they waited outside the
wall until the gate fell (about 230 s) and entered behind the trolls and Big 'Uns, striking
the centre at 270-305 s (Wolf Riders on f2, f3 and the lord; a Boar Boyz unit on the Bull
Centaur reserve f8 and f3). Enemy men within 60 m of the centre: 413 at 270 s and 532 at
330 s, against 0-137 and 284-405 in the anchor wins. The guns were reached only at 485-530 s,
after the line broke. The anchor wins also committed the lord and reserve to the central
melee (271-298 s), so the reserve choice did not separate them here. Candidate errors: the
Infernal Guard f4 sent west at 263 s (75 to 17 men, routed at 395 s), the lord fighting the
warboss (0.44 HP by 360 s), and Blunderbusses that received 26 attack orders each but fired
about 0.2 and 1.8 volleys. None is shown to decide the battle, so winnability with better
play is unclear. The model first named the cavalry at 484 s.

Interface: five `unit_routing` refusals went to units that were wavering when observed and
routed during the 3-7 s order delay; three `unreachable` moves were each followed by an
accepted move about 5 s later. f4's reported position jumped about 200 m between the centre
and (-200, -40) 19 times (the model saw 10), with enemies in melee at both sites; the unit
was split: the engine's `unit:position()` is "the centre position of the main squad of the
unit" (vanilla script docs), and the main squad switched between the two fights (9 jumps
over 100 m between consecutive samples, 131-515 s). The observation reports that faithfully
but does not say a unit is split; a candidate interface note, not a model error. Mean delay rose to 5.9 s (max 9.3 s) in the 250-530 s fight.

Reading against the difficulty target: the added cavalry binds through mass at the breach
rather than through reserve allocation, so the factor is partly stat pressure. The step is
not admissible until something wins it; the next choice is between a repeat on this step
and a smaller step (for example the two Wolf Riders only).

**V1b2 swarm, paid** (`bench-b13-v1b2-swarm-gyros-sol61-20261016`, `82a2364`, gpt-6.1-sol /
low, `llm_rules` v20): **won** at 535 s with 42% of its strength left (enemy 30%, nothing
active); 115 decisions, 9 invalid orders, mean delay 4.62 s, $1.08160000; OpenAI ledger
$48.25. The anchor wins took 449-497 s and kept 50-52%. The Gyrocopters ended with 6 of 18
men, out of the fight, so flyers did not block the ending. The model first named them at
296 s and aimed 19 orders at them, mostly from f13 and f14. The Warlock Engineer survived;
the Warp Lightning Cannon kept 15 of 42 crew. The step is demonstrated winnable and costs
margin, so the family climbs.

**V1c (plan, 20:55 UTC).** With $3.75 left under the OpenAI cap, one paid battle per family:
1. `tze-caster-skv-assault-cannon`, gpt-6.1-sol / low, first model battle on that step.
2. `chd-reserve-grn-siege-flankers` again, with Kimi K3 / low through OpenRouter: any
   engine-confirmed win shows the step is winnable, and it is Kimi's first battle (its
   schema check passed). A loss is not evidence against winnability. OpenRouter cumulative
   ceiling **$5.00** (now $0.84); Kimi's routing ceilings ($3/$15 per million) are about 1.5
   times Sol's prices, so roughly $1.5-2.5.
3. `skv-swarm-dwf-line-gyrocopters-4` (second step: four Gyrocopters, 8200 to 11400 of
   enemy cost, 13 units), gpt-6.1-sol / low. No separate scripted check: the unit already
   recruited and a lobby failure costs nothing, so it runs last.

OpenAI jobs run with the owner's hard cap, **$52.00**, as the ceiling; expected spend
$2.0-2.5. A battle cut off by that cap would be an incomplete trial, so the swarm runs
last. After V1c the OpenAI budget is effectively spent.

**V1c caster, paid** (`bench-b13-v1c-caster-cannon-sol61-20261016`, `4ec5772`, gpt-6.1-sol /
low): **won** at 577 s with 25% of its strength left (enemy 27%, nothing active); 117
decisions, 5 invalid orders, mean delay 4.9 s, $0.84370000. The model named the cannon at
96 s and sent every unit at it (nine orders over the battle, 44 ability orders in all);
Kairos's barrier was down by 206 s, he kept about 76% HP, and the cannon crew routed by
458 s. The step binds and is demonstrated winnable, so the family climbs.

**V1c siege, Kimi K3** (`bench-b13-v1c-siege-flankers-kimi-20261016`, OpenRouter, low):
**lost** at 659 s by army rout with 51% of its strength left (enemy 49%); the key building
was still held (98%) and tickets were untouched. 45 decisions, 51 calls, median call 7.0 s,
one of 81.5 s, mean order delay 14.52 s (Sol: 4-5 s); six rejected replies (two orders to
one unit, one unavailable `skirmish` behaviour); 5,010 supplies unspent; $0.99245377.
OpenRouter ledger $1.83109 of this tranche's $5. Kimi's first battle: it completes, but at
about three times Sol's latency, which itself costs a real-time battle. The four-unit
flanker step is now 0 of 2 and not admissible; the next siege test steps back to half the
dose (`chd-reserve-grn-siege-flankers-2`: one Boar Boyz and one Wolf Riders unit, 9725 to
10675, 18 units).

**V1c swarm, paid** (`bench-b13-v1c-swarm-gyros4-sol61-20261016`, gpt-6.1-sol / low): **won**
at 418 s with 50% of its strength left (enemy 33%, nothing active); 54 decisions, 1 invalid
order, mean delay 7.64 s, $0.66040000. OpenAI ledger $49.76 of $52. Doubling the
Gyrocopters did not make the battle harder than the two-Gyrocopter step (535 s, 42%) or
clearly harder than the anchor (449-497 s, 50-52%): that factor does not bind, and the
spread between single battles is as large as the step. The next swarm step needs a
different factor, not a larger dose.

**V1d (plan, 21:30 UTC).** Within both caps: `chd-reserve-grn-siege-flankers-2` with
gpt-6.1-sol / low (OpenAI cap $52; about $1.2), then `tze-caster-skv-assault-cannon-2`
(two Warp Lightning Cannons, 3775 to 5675, 12 units) with GLM-5.3 / low through OpenRouter
(cumulative ceiling $5; about $0.4). GLM won one of two caster anchors; a GLM win would show
the two-cannon step is winnable, a loss would not show the opposite. After V1d the OpenAI
remainder is about $1; further Sol battles need the owner's decision on that cap.

**V1d siege, paid** (`bench-b13-v1d-siege-flankers2-sol61-20261016`, `9f2ea74`, gpt-6.1-sol /
low): **won** at 422 s with 66% of its strength left (enemy 35%), the key building held in
every sample; 64 decisions, 4 invalid orders, mean delay 6.6 s, $0.61290000; OpenAI ledger
$50.37 of $52. Siege ladder so far: anchor won 3/3, two added flankers won (faster than
the anchor wins), four added flankers lost 2/2 (Sol, Kimi). The hardest step with a
demonstrated win is the two-flanker step; the difficulty rises steeply between two and
four units, or single battles vary that much. A three-unit step or a second Sol battle on
four would locate it, at about $1 each.

**V1d caster, GLM** (`bench-b13-v1d-caster-cannon2-glm-20261016`, OpenRouter, GLM-5.3 / low):
**lost** at 204 s, 13% of its strength left against the enemy's 87%; 26 decisions,
$0.09600000 (OpenRouter $1.93). GLM sent Kairos at a cannon from 5 s; his barrier was
full at 67 s and he was dead by about 201 s, and the army collapsed. A GLM loss does not
show the step is unwinnable.

**V1e (plan, 21:47 UTC).** The last OpenAI battle under the $52 cap: gpt-6.1-sol / low on
`tze-caster-skv-assault-cannon-2` ($0.45-1.24 per caster battle so far; $1.63 left). A win
makes two cannons the caster family's hardest demonstrated step; a loss leaves one cannon
as the hardest, with two cannons unadmitted. No other paid run follows without the owner.

**V1e caster, paid** (`bench-b13-v1e-caster-cannon2-sol61-20261016`, `af19035`, gpt-6.1-sol /
low): **won** at 370 s with 46% of its strength left (the enemy routed with 57% of its men);
62 decisions, 1 invalid order, mean delay 5.95 s, $0.49490000. OpenAI ledger $50.86 of
$52; no further OpenAI battle is planned. It aimed 23 orders at the two cannons; Kairos's
barrier was down by 232 s and he kept about 81% HP. GLM lost the same step at 204 s.

**Ladder V1 summary** (one battle per step unless noted; anchors from M1c, v18; the rest v20):

| Family | Anchor (gpt-6.1-sol) | Steps | Hardest step with a demonstrated win |
|---|---|---|---|
| Siege defence | won 3/3 | +2 flankers: won (422 s, 66%). +4 flankers: lost (Sol 629 s; Kimi 659 s) | `chd-reserve-grn-siege-flankers-2` |
| Swarm command | won 3/3 | +2 Gyrocopters: won (535 s, 42%). +4: won (418 s, 50%) | `skv-swarm-dwf-line-gyrocopters-4`; the factor does not bind |
| Caster assault | won 3/3 | +1 cannon: won (577 s, 25%). +2 cannons: won (370 s, 46%); GLM lost (204 s) | `tze-caster-skv-assault-cannon-2` |

Single battles vary as much as the steps, so these are development readings, not
difficulty estimates. Against the owner's target (as hard as possible while winnable):
siege's next question is a three-unit step or a second try at four; swarm needs a
different factor; caster can climb further. All need more Sol battles than the cap allows,
or a cheaper reference model. The other three families (cavalry assault 1/3 for
gpt-6.1-sol; defensive swarm and Kislev 0/3) already sit near or past the winnable edge.

**Per-model reasoning modes** (`ff8a091`, for the owner's all-modes coverage): efforts are
declared per model, with OpenRouter's catalogue lists (GLM `low`/`high`/`max`, Kimi
`none`/`low`/`high`/`max`, Step `low`/`medium`/`high`); an empty `/EFFORT` suffix now names
the effort in its error. Each new mode passed one reply-schema call ($0.0061; OpenRouter
ledger $1.9333); details in [controllers.md](controllers.md#openrouter). 491 tests pass.

**Report.** `configs/twwarhammer3/benchmark_jobs.json` gains tonight's 13 jobs (94 in all);
the siege, swarm and caster footnotes in `report_notes.json` now summarise the ladder and
GLM's v20 win. The canonical `reports/benchmark.html` was rebuilt (1m45s); the browser
checks were not rerun for this data-and-notes change.

**OpenAI reasoning modes.** One schema call per mode and model: gpt-6.1-sol and gpt-6-astra
reject `none` and the API lists their modes as `low`, `medium`, `high`, `xhigh`, `max`;
gpt-6-luna and gpt-6-sol add `none`; no model takes `minimal`. Every listed mode passed.
`providers.py` declares these per model (26 model-mode configurations with OpenRouter's).
$0.037; OpenAI ledger $50.90 of $52. Tests that used `max` as an invalid effort now use
`minimal`.

**Small focused candidates: S1 defined, not run.** A draft of seven small and two large
candidates from the game database is in [benchmark.md](benchmark-implementation.md#history)
(full draft: `calibration/micro-scenarios-draft-20261016.md`). Setup now accepts `lord:
false` on a side, so a lordless roster recruits its first card as an ordinary unit (the
lord card id ends in `:1`). S1, the owner's example, is defined as
`ksl-raiders-emp-halberds`: two Kislev Horse Raiders (attacking) against one Empire
Halberdiers unit, no lords, custom funds 1,100, Taurox map, 1200 s. Both cards appeared
in earlier lobbies. Unverified until a $0 lobby probe: the profile's "allow no lord"
setting for both slots, funds that small, and the AI's behaviour with one unit. After
that comes a scripted floor and a disclosed feint-and-flank diagnostic at 0 and 5 s
delay, before any model battle. Nothing runs until the owner has reviewed the draft.

## 2026-10-16: Live check of the v20 shared-magic warning

**Result.** `bench-b13-glm-v20-caster-20261016` (`ae55309`, 19:28-19:40 UTC) **won** at
575 s with 69% of its strength left (enemy 43% left, all routed); 80 decisions, 97
calls, $0.40868230, clock ratio 0.99999. OpenRouter ledger $0.83868719 of the $2.00 run
ceiling and the $50 allowance. The v19 battle on the same anchor lost at 566 s. One
battle each from independent launches, so the outcome is not attributed to v20.

| | v19 (lost) | v20 (won) |
|---|---:|---:|
| Paid spell orders | 31 | 23 |
| Decisions whose basis showed a same-snapshot paid spell (v20 warns) | 21 | 16 |
| ...of which ordered past the pool minus those pending costs | 12 | 4 |
| Spell refusals (`perform_special_ability`) | 7 | 4 |
| ...after a same-snapshot paid spell | 7 | 3 |
| Reply validation failures, of all calls | 17 / 105 | 18 / 97 |

The warning halved the over-spend rate (57% to 25% of warned decisions) but missed
the pre-set acceptance bar of at most two such refusals. All three remaining cases
saw the warning and still ordered a spell above the pending-adjusted pool (18 shown,
16 pending, Glean Magic; 9 and 9, Blue Fire 6; 6 and 5, Blue Fire 6). The fourth
refusal was an affordable Blue Fire with nothing pending, a different cause not
diagnosed here. Each refusal costs one order, not the battle. Decision: keep v20; a
pool display with pending costs deducted stays the candidate change if spell refusals
matter in the frontier screen, not before. Review:
`calibration/glm-v20-magic-review-20261016.py` and JSON (both battles, same rules).

The win matters for calibration: GLM-5.3 / low joins gpt-6-sol (3/3) and gpt-6.1-sol
(3/3) in winning the caster anchor, so this family also needs a harder ladder step
before a frontier screen tells us anything.

**Plan.** Question: does v20's shared-pool warning stop the model from issuing a paid spell
that the just-issued spells have already made unaffordable? In the v19 GLM battle
all seven special-ability refusals followed such a spell. One battle, `llm_rules` v20,
GLM-5.3 / low through OpenRouter, the unchanged `tze-caster-skv-assault` anchor, source
`ae55309` (b13). Same model and scenario as v19, so the comparison varies only the
feedback; it is one battle against one, an independent launch, so outcomes and
positions are not paired.

Cost: $0.42 for the v19 battle; the M1 repricing envelope is $0.46–$1.30. The cumulative
OpenRouter ceiling is **$2.00** (now $0.43000489), at most the 20-minute timer plus
setup. OpenAI is untouched. Measures: refusals after a just-issued paid spell, spell
commands issued and their later active/recharge readback, magic left at the end.
Decision: at most two such refusals with spells still cast accepts v20 for later
paid runs. Five or more means the label does not work; the next candidate would show
pending costs in the pool itself, an observation change logged as a new version.
A battle without casting is a regression to investigate before any other paid run.

## 2026-10-16: First OpenRouter battle and shared-magic feedback

`bench-b13-openrouter-glm-caster-20261016`, source `ba6d1c3`, completed normally through
OpenRouter: GLM-5.3 / low, `llm_rules` v19, engine loss at 566 s on the unchanged caster
anchor. There were 61 of 937 enemy soldiers still active (93.5% progress), with no
friendly soldiers active. Clock ratio 0.99995; 89 decisions, 105 API calls,
$0.42477343054 charged. The ledger now totals $0.43000489054, below this run's $3 cap
and the owner's separate $50 allowance. OpenAI remains $45.96/$52. No further paid
run is queued. This is an integration/development trial, not a model ranking or a
frontier-difficulty estimate.

Median API response time was 4.19 s. Calls used sixteen serving backends, all reporting
`z-ai/glm-5.3-20260816`. Seventeen replies failed parsing/action validation; retries
repaired most, and the existing salvage rule recovered one decision after three failed
attempts. One response was token-limited. All attempt charges sum to the result and
ledger delta. Eighty-two orders were accepted; seven special-ability errors and two
`target_dead` errors were engine refusals. The read-only audit is
`calibration/openrouter-battle-review-20261016.py` and JSON. Starts matched the free
caster script's roster, strength, resources and loadout, but positions differed by up
to 8.6 m, flagged normally; these are independent development launches.

**llm v20 / commander v7:** all seven special-ability refusals followed another paid
spell issued at the basis snapshot's timestamp. Each new spell looked affordable in
that snapshot; the refusal snapshot showed less magic than its cost. Example: Blue
Fire (6 magic) was just issued while the panel still showed 7; the next Harmonic
Convergence (5) failed, with 2 magic in the next reading. This identifies misleading
resource timing, without proving the engine's internal error cause. v19's per-ability
warning did not describe the shared pool.

The shared renderer now labels that pool as observed and lists the just-issued paid
spells, stating that costs may not yet be reflected and execution is unconfirmed. It
neither calculates a replacement balance nor filters orders. Later snapshots retain
their ordinary available-pool display. No scenario, transport, game speed or system
prompt changed. `calibration/magic-feedback-review-20261016.py` and JSON validate the
new warning against all seven states. The observed case has a regression test; all
existing golden prompts remain byte-identical. Changed model behavior remains untested.

The report collector now retains backend snapshot names and counts replies failing
validation separately from engine order refusals, including attempts retained by a
terminal policy failure. Response IDs prevent duplicate counts in repeated commander
metadata. Run settings exposes both fields; JSON retains the rejection reasons. Added
the fourth free diagnostic and the GLM battle to the explicit report selection, with
curated replay highlights for casting, the failed retreat point and stale magic.

Validation: 510 WH3/shared/documentation tests passed (one optional skip); Ruff,
Prettier and diff checks passed. The rebuilt report has 81 input jobs and 98 completed
battles across six candidate scenarios. Offline Chromium checks passed on recorded,
synthetic and copied reports, desktop and mobile, including the GLM snapshot and
17-of-105 reply-validation count in Run settings. Artifacts:
`report-checks/openrouter-calibration/`.

Next: inspect these recorded mechanisms before another paid allocation. Keep the
caster anchor unchanged; adaptive withdrawal, escort protection and spell execution
remain useful distinctions. All six candidate families remain provisional.

## 2026-10-16: Caster audit and one airborne-casting diagnostic

Completed `bench-b13-airborne-caster-20261016` on source `b1ab502`: engine loss at
581 s, clock ratio 1.0005, 55 accepted orders, no refusals, $0 API spend. All twelve
spell commands (one Firestorm, eleven Blue Fires) had later active/recharge feedback.
The catapult shattered at 268 s. The stationary escorts then collapsed; the last ground
unit routed at 448 s. Kairos's barrier first fell at 473 s and HP at 491 s while he
remained airborne at the fixed home position. The script could not recover there and
Kairos died before the ending, with 23 magic and 3.7 reserves remaining. The review is
`calibration/airborne-caster-review-20261016.py` and JSON. No harder variant is justified
by this loss: adaptive retreat and protecting the escorts remain unresolved. The
report selection and two replay highlights now retain this diagnostic.

Planned paid check (completed and reviewed above): **one** GLM-5.3 / low `llm_rules` v19 battle on the unchanged caster
anchor, through OpenRouter. Its question is whether the new route completes a real
battle with full prompts, valid replies, recorded routing/cost and normal live timing;
it is not a model ranking or a strongest-model ceiling estimate. Historical M1 caster
token workloads reprice to $0.46–$1.30 at GLM's routing ceilings, with caching charged
at full input price. This is a planning range, not a bound: tokenization, reasoning,
retries, speed and battle duration can change. Set the cumulative OpenRouter ledger
ceiling to **$3** (currently $0.00523146), one episode, at most the scenario's 20-minute
timer plus setup. An exhausted budget remains an incomplete trial. Inspect its trace
and provider metadata before any further paid allocation; no matrix is queued.
The repricing audit covers all 48 model episodes in M1's plans:
`calibration/provider-cost-envelope-20261016.py` and JSON. OpenAI's remainder is untouched.

Read the nine M1 caster episodes without new API calls. In the six Sol/gpt-6.1-sol wins,
Kairos lost no HP between consecutive samples whose endpoints both showed him airborne;
barrier losses still occurred. Other episodes show airborne-endpoint HP drops. Samples
cannot exclude intervening flight changes or attribute damage. The declared Warpfire
Thrower and Plagueclaw projectile records both permit airborne targets (ranges 80 m and
400 m). This rules out assuming flight immunity, while leaving safe airborne casting
as a useful hypothesis. Table hashes and limited attributes are in
`calibration/caster-projectiles-20261016.json`; no extracted game files are committed.

The trace audit (`calibration/caster-review-20261016.py` and JSON) found 250 issued spell
commands, of which 100 were followed by a sampled active/recharge state within 15 s.
Seven had no follow-up observation in that window. These are readback counts, not cast
success or damage; aliases, interruption, delayed execution and sparse sampling can
confound them. Accepted orders alone remain unsuitable as a spell-value score.

Added `CasterSkirmish` in `battle/calibration.py`: escorts hold their starting posts;
Kairos stays airborne, casts ordinary Blue Fire (artillery first) or Firestorm on a
visible cluster of at least three units, and returns during cooldown or to recover a
barrier below 25% (resumes at 80%). It allows five seconds for a cast command to execute.
The controller card discloses spell choices, thresholds and range margins. No scenario,
model prompt, budget or game-speed change. Its completed trial will appear as the
scripted "Airborne casting" diagnostic in the report.

The declared allowance was one episode on `tze-caster-skv-assault`, at most its 20-minute
timer plus setup, $0 API spend, with casts/readbacks, flight, barrier recovery and escort
survival reviewed before interpreting the outcome. A script loss does not establish
frontier difficulty. Validation before launching: 96 focused tests, Ruff and diff checks
passed; 507 orders validated on 938 recorded public snapshots from all nine episodes
(`calibration/caster-offline-20261016.json`). That offline check does not predict outcomes.

## 2026-10-16: Free siege/swarm calibration checks

The first tranche uses unchanged anchors and disclosed scripts, unpaused at 1x with
replay/stills, $0 API spend. Jobs use the prefix `bench-b13-` and suffix `-20261016`:

| Job middle | Controller | Source | Engine outcome | Battle seconds |
|---|---|---|---|---:|
| `central-defence` | CentralDefence | `1c03385` | lost | 614 |
| `coordinated-rush` | CoordinatedRush, speed estimate | `1c03385` | lost | 316 |
| `coordinated-follow` | CoordinatedRush, observed screen | `d85cae1` | lost | 440 |

The siege fallback issued 196 orders without a refusal. Seven units eventually reached
within 12 m of their assigned posts, but the left-side Infernal Guard and Fireglaives
never did. The two blunderbuss units spent only 165 of 3,600 rounds; the cannon spent
five of 25. The chosen central point was lost at 491 s. This does not establish an easy
central-defence strategy or justify making the scenario harder: withdrawal routes and
firing positions remain unresolved. No second siege run was needed to establish that
this diagnostic did not fully execute its intended concentration.

The first swarm script had 653 issued orders and three `unit_routing` refusals. Its
Doomwheel arrived before the screen; the following entry records that failure and the
one allowed repeat's corrected rule. Execution summaries are extracted read-only in
`calibration/tranche-review-20261016.py` and its JSON. Outcome and execution are separate:
a timing rule that failed to coordinate units cannot establish the value of coordination.

The repeat released both mobiles at the first observed screen contact, 143.9 s. The
Doomwheel entered melee at 156.5 s and routed at 180.5 s; the Rat Ogres entered at
162.8 s and routed at 167.9 s. It issued 1,056 orders with four `unit_routing` refusals.
The intended sequence now executed, but this frontal tactic still lost. Starts matched
in roster/resources/loadout, with positions differing by up to 3.3 m (flagged by the
normal comparison); the two sources also differ. The longer survival is not a controlled
improvement estimate. No further run is queued in this tranche and no scenario was
made harder from these losses. All three battle/wall clock ratios were within 0.4% of 1.

The cavalry review of M1b/M1c found identical recorded positions/bearings within each
launch (six and three episodes), including both wins and losses; there are two starting
geometries across launches. `calibration/cavalry-start-review-20261016.json` retains the
nine paths, geometry hashes and opening orders. Keep the current difficulty and inspect
route execution before buying repeats or increasing enemy strength.

The canonical report now includes 79 input jobs and displays 96 completed battles in
six provisional scenarios. The named calibration tactics appear as scripted scenario
diagnostics with their assumptions in Run settings and their replays available. The
report selection file is excluded from gameplay fingerprints, with a regression check,
so selecting more evidence does not invent a changed game/controller setup.

Validation: the WH3/shared/documentation suite passed 505 tests (two optional skips);
focused regressions for the subsequent diagnostic and fingerprint refinements passed.
Ruff, Prettier and `git diff --check` passed. Offline Chromium checks passed on the final
recorded, synthetic and copied reports, desktop and mobile. A regeneration without its
scenario notes initially expanded the page to historical scenarios and failed the layout
check; rerendering with the canonical notes restored the six-scenario selection.
Screenshots/downloads: `report-checks/openrouter-calibration/`.

The first new result appended the provider column to the register. All 292 historical
rows retain every previous field unchanged; new diagnostic rows have no model cost.

## 2026-10-16: Calibrate the scripted swarm timing rule

The first `CoordinatedRush` diagnostic lost at 316 s on the unchanged swarm anchor. It
released the Doomwheel at 10.7 s; it reached melee at 99.5 s and routed at 107.9 s, before
the first slave/clanrat contact at 144.5 s. The Rat Ogres released at 56.3 s, reached melee at
153.2 s and routed at 158.9 s. A straight-line estimate using advertised run speeds did
not synchronize the first commitment, so its outcome cannot test that intended tactic.

Revised only this diagnostic: mobile units follow 25 m behind the observed screen
centre, 30 m apart, and attack after observed screen contact. Posts update after 20 m of
screen progress, avoiding a new movement order every tick. If the screen is gone the
mobiles revert to run-nearest. No abilities or scenario changes. The saved first source
and controller card preserve the original rule; the repeat ran as `coordinated-follow` on `d85cae1` (results above).

Three focused tests and Ruff pass. On 451 recorded snapshots through 315.2 s, the new
rule produced 687 valid orders and released after observed contact. This offline check
cannot predict counterfactual arrival times or outcomes. Evidence:
`calibration/coordinated-follow-offline-20261016.json`. The broader WH3/shared/report
checks preceding this refinement passed: 505 tests, two optional skips.

## 2026-10-16: llm v19 and commander v6, ability issue feedback

M1's 54 traces contain 247 refused ability orders. In 155 cases the input still read
ready at exactly the prior issue timestamp; 151 of these received a special-ability
engine error, three found the unit routing and one lost its target. The mod's tick
applies pending orders before publishing the acknowledgement snapshot, so panel state
can lag that issue. This is now rendered as "panel ready; just issued, execution
unconfirmed". Subsequent active/recharge/blocked readings take precedence; later ready
readings are not suppressed. There is no inferred cooldown, automatic retry or order
filter, and issued still does not mean the effect occurred.

Commander v6 additionally lists one-shot orders being submitted beside its next API
request, since that request precedes their acknowledgement. All three system prompts
now state that routing/shattered units cannot accept unit orders, including abilities;
army orders remain independent. The observation/action contract and skills are unchanged.

Validation: the read-only `calibration/ability-feedback-review-20261016.py` and JSON
record all trace paths, counts and before-state examples; the new renderer marks all
155 same-timestamp cases. Targeted tests cover both unit/army rendering and precedence
of live ability feedback. The commander golden prompt changes only by the explicit
pending-order paragraph; both direct-controller golden inputs are unchanged. Model
behavior under these versions has not yet been tested in a paid battle. All 123 targeted
tests, Ruff and `git diff --check` passed.

## 2026-10-16: Two public-state calibration diagnostics

Added two small external controllers in `battle/calibration.py` for the first
[calibration tranche](benchmark-implementation.md#history). `CentralDefence`
gathers at the owned victory point nearest the starting garrison, using the existing
Skills executor for a melee line, shooters and lord. `CoordinatedRush` uses run-nearest
but holds the Doomwheel and Rat Ogres until their estimated contact time matches the
slave/clanrat screen. Each discloses its scenario knowledge and simple geometry in its
controller card. Neither buys API calls, uses evaluation state or changes the scenario.

These are mechanism diagnostics, not new general-purpose baselines. The first live
checks are pending; a failure of a fixed post or straight-line estimate cannot establish
that the scenario has no useful tactic. Five targeted tests passed, including the
existing nearest-enemy baselines; Ruff passed.

## 2026-10-16: Calibration cards and report interpretation

Reviewed all 54 episodes in M1a–d with a read-only extraction, saved as
`calibration/calibration-audit-20261016.py` and its JSON. Added six
[calibration cards](benchmark-implementation.md#history) with competing plays,
observed evidence, confounds and the smallest useful next check. The first tranche is
one free scripted siege diagnostic and one free swarm diagnostic on unchanged anchors;
a repeat is conditional on an unresolved mechanism, not a quota. No frontier matrix
or harder scenario is queued before that review.

Kislev is now labelled reinforcement defence in the report: Sol bought all seven initial
reserves in each M1 battle and still ended with 4,004–5,654 supplies. Its available
spawn-zone list first emptied at 229–240 s with 1,065–1,602 supplies. This supports an
access/deployment question, not established budget scarcity. The audit distinguishes
empty zone lists from temporary purchase refusal and unknown affordability. All six
candidate families and every earlier outcome remain retained.

Updated the report's stale two-screen notes to M1 findings and explicit untested
hypotheses. The introduction makes the collection provisional. OpenRouter model labels,
additional model colours and gateway/backend/routing details are ready for later battle
evidence; API schema checks are not inserted as battles. The canonical report was rebuilt
from its explicit 76-job selection, still showing 93 completed battles in six scenarios.

Validation: 158 targeted tests passed (one Windows-only test skipped), Ruff, Prettier
and `git diff --check` passed. Offline Chromium checks passed on recorded, synthetic and
copied reports, desktop and mobile (`report-checks/openrouter-calibration/`). The first
layout check caught an extra sentence pushing the map below the initial screen; moving
that information into the introduction restored the layout. The browser check now saves
a screenshot when that regression occurs. The read-only game doctor is ready; no game
has launched during this work.

## 2026-10-16: Harness b13, shared OpenRouter transport

Resumed after the owner requested proceeding with the goal. Added OpenRouter to the
existing Responses model loop, with three declared models (GLM-5.3, Kimi K3, Step 5
Preview), per-provider key loading, WH3 selection and separate cumulative spend ledger.
Vendor/model IDs survive rotation parsing. Controller cards, collector groups and the
register retain gateway/routing provenance. Prompt versions and the environment track
are unchanged; direct OpenAI remains the default.

Reservations now include schema/framing overhead and all transport retries. Uncertain
attempts receive conservative estimated charges; OpenRouter's reported cost supplies
normal charges, with missing costs stopping further calls. Enforced routing ceilings
prevent a different backend price from silently invalidating the estimate. The local
ledger is not crash-atomic; the provider key's $50 cap remains the account-wide backstop.

Validation before paid checks: all 1,053 tests passed (14 optional tests skipped), Ruff
and `git diff --check` passed. The first full-suite invocation had 26 socket permission
failures under the sandbox; the unrestricted rerun passed. No game launched.

Live schema checks (`d0187eb`, `capability-probes/openrouter-20261016/schema-01` and
`schema-step-02`) used WH3's full reply schema and parser, low effort, and a combined
$0.25 cap on the real OpenRouter ledger:

| Model | Result | Backend | Wall time | USD |
|---|---|---|---:|---:|
| GLM-5.3 | passed, 1,024-token allowance | Fireworks | 1.75 s | 0.00017748 |
| Kimi K3 | passed, 1,024-token allowance | Makora | 5.04 s | 0.00219147 |
| Step 5 Preview | incomplete, empty output at 1,024 tokens | DeepInfra | 27.61 s | 0.00267311 |
| Step 5 Preview | passed, normal 4,000-token allowance | InferenceNet | 10.28 s | 0.00018940 |

Total $0.00523146, including the failed attempt. Step's successful request used two
router attempts; both backend and allowance changed, so this does not isolate the cause
of the first failure. Backend snapshots in router metadata are retained in raw smoke
evidence and now in normal attempt records. The key-budget endpoint still reported zero
usage immediately after calls; local accounting uses each response's reported cost,
not this lagging endpoint. These tests establish API/schema compatibility, not tactical
ability or reliable battle latency. No game ran and the OpenAI ledger is unchanged.

## 2026-10-16: Cleanup and OpenRouter design only

The owner prepared an OpenRouter key and set a separate $50 budget, requested support
and three leading open-weight model checks, then clarified that this turn should stop
after cleanup/design. The [proposal](controllers.md#openrouter)
reuses the shared model loop with a small provider boundary; it records the model-ID
parser conflict, provider validation, routing provenance and spend-accounting work.
Unfinished provider code was removed when stopping at cleanup/design; no implementation
changes remain. A read-only authentication/budget check and catalogue lookup completed;
the key reported zero usage and $50 remaining. The request process read the `0600` key
file without printing its contents. Sanitized metadata is retained under
`runs/twwarhammer3/capability-probes/openrouter-20261016/`. No paid model calls, game runs
or changes to prompts/scenarios followed.

Documentation cleanup removed the long superseded implementation sequence in favor of
links to its log entries, corrected the current observation version and HTML order-age
definition, and removed the stale requirement for six battles in every comparison.
The latest-results table above now reflects M1. Recounting `episode-*/result.json` under
the saved M1a/b/c queue jobs gives 50 battles (48 model, two scripted), then M1d adds
four scripted battles; the old status/README total of 58 was incorrect. The M1c summary
also incorrectly said Sol won every swarm battle; its actual record is 2/3.

The tracked inventory contained no obvious build artifacts to remove. Run evidence,
ledgers, paused tracks, unique branches and untracked owner settings were preserved.
Validation: 100 focused model/controller/CLI/documentation tests and Ruff passed before
editing; all 43 documentation checks and `git diff --check` passed after cleanup. Scenario calibration
remains the separate planning proposal; the core is provisional.

## 2026-10-16: Matched round M1 on the retained core (plan)

The owner raised the WH3 API cap to $52 and asked that overnight work favor game runs.
The plan's next game-side step is a matched model comparison over the core families that
have only exploratory evidence. M1 holds the conditions fixed: harness b12 at one frozen
revision, `llm_rules` v18, low effort, gpt-6-sol against gpt-6-luna, three battles each per
scenario in one job (rotation interleaves them; rematches replay the recorded start),
very hard AI, unpaused 1x, natural latency. Earlier exploratory battles stay in the
report but in their own harness groups.

| Plan | Scenarios, in order | Battles | Expected spend |
|---|---|---|---|
| M1a | `chd-reserve-grn-siege`, `ksl-reserves-survival`, `skv-swarm-dwf-line` | 18 | about $10 |
| M1b (decided after the family audit) | `dwf-line-skv-swarm`, `tze-caster-skv-screen`; `brt-cavalry-emp-assault-hard` under b12 if time remains | up to 18 | about $10 |

Cavalry already has six Sol and six Luna battles from C1 (b10/b11), so it runs last. All
battles end before the owner returns (13:00 UTC). Three battles per model are a first
matched sample, not a stable ranking. Results follow in this entry.

**Family audit.** Before M1a's results, an independent read of the saved battles
recommended a core of cavalry, siege defence and swarm command, the caster family only
after an attacker-role screen, and demoting the swarm survival and Kislev scenarios
([benchmark.md](benchmark.md#scenario-design)). The owner decides; M1b was reordered to run
the retained families and the caster screen's completion first.

**M1a results** (`1f1083d`, 03:30-05:50 UTC, queue
`calibration/m1a-plan-20261016.json`; every rematch matched its recorded start beyond
geometry):

| Scenario | gpt-6-sol (low) | gpt-6-luna (low) |
|---|---|---|
| `chd-reserve-grn-siege` | won 3 of 3: 614, 840, 736 s; $4.14 | lost 3 of 3: 375, 542, 393 s; $0.13 |
| `skv-swarm-dwf-line` | won 367 and 393 s, lost 670 s; $3.04 | lost 3 of 3: 614, 546, 441 s; $0.17 |
| `tze-caster-skv-assault` (first screen) | won 492 s with 7% of its soldiers left; $0.82 | lost 750 s, army destroyed; $0.06 |

Luna's swarm battles had 59-71 rejected orders each against Sol's 3-19. The first
attacker-role caster battles were close and decided by play, so under the owner's
delegation the variant is completed to three battles per model in M1b rather than left
at two. M1a cost $8.36; ledger $25.27 of $52.

**M1a trace review** (independent; patterns from 2-3 battles per model, so causes are
hypotheses). Siege: Luna sent its Bull Centaur reserve into the trolls at 5 s (first unit
to rout every time, 87-132 s) and its lord fought alone at the east tower (routed at
231-260 s); Sol held or withdrew the reserve and kept the lord central (never routed).
Sol's blunderbusses fired 753-1661 rounds against Luna's 58-143. Tower builds and the
cannon did not separate them (Luna's 393 s loss copied Sol's build; at most 7 of 25
cannon shots in any battle). Swarm: Sol's wins committed the Doomwheel and Rat Ogres with
the slave screen (64-79 s; a western Doomwheel flank at 153 s); Luna sent them ahead,
and they broke before the screen arrived. Sol's loss reversed its own order. Caster
assault: casts are confirmed by pool drops (Luna 18, mostly Blue Fire; Sol 10); Sol
withdrew Kairos at about 253 s to rebuild its barrier and won narrowly; Luna's escorts
broke by 281 s. The choices were real and executable.

Rejected orders: Luna 371 against Sol 80. 220 went to routing units (90 already shown
routing, including 33 rally orders to its routing lord; the rules never say routing units
ignore orders); 87 were abilities whose readiness was stale: 70 re-cast an ability issued
no more than 2 s before the snapshot, which still read ready. That is an interface defect,
a candidate for the next harness version (it changes the observation, so not mid-round),
alongside stating in the rules that routing units ignore orders. One Luna siege call took
73 s over two transport attempts, leaving its last 54 s without orders (its army was
already mostly routing). No other infrastructure fault; every battle ended on an engine
result.

**M1b** (`0d530af`, started 05:54 UTC, queue `calibration/m1b-plan-20261016.json`): caster
assault 2+2 more, cavalry 3+3, siege scripted baselines (`hold`, `attack_nearest`), then
the two demotion candidates, `dwf-line-skv-swarm` and `ksl-reserves-survival`, 3+3 each.
The report rework merged before M1b (presentation files only, so the test-setup
fingerprint is unchanged and M1a/M1b pool).

**M1b results** (`0d530af`, 05:54-09:20 UTC; every job completed and every rematch matched
its start beyond geometry):

| Scenario | gpt-6-sol (low) | gpt-6-luna (low) |
|---|---|---|
| `tze-caster-skv-assault` (with the screen) | won 3 of 3: 492, 446, 484 s | won 351 s, lost 750 and 689 s |
| `brt-cavalry-emp-assault-hard` | won 380 s, lost 552 and 613 s | lost 3 of 3: 173, 195, 261 s |
| `dwf-line-skv-swarm` | lost 3 of 3: 489, 490, 578 s | lost 3 of 3: 672, 494, 494 s |
| `ksl-reserves-survival` | lost 3 of 3: 366, 368, 413 s | lost 3 of 3: 293, 337, 365 s |

Siege baselines: `attack_nearest` lost at 963 s, `hold` at 709 s. M1b cost $9.88 (Sol $9.47
over 10 battles, Luna $0.41 over 10); ledger $35.15 of $52. Across M1, three scenarios
separated the models (siege 3-0 against 0-3, swarm command 2-1 against 0-3, caster assault
3-0 against 1-2); cavalry under b12 repeated C1's pattern (Sol 1 of 3, Luna 0 of 3). The
two demotion candidates did not separate them: every survive-a-swarm battle lost between
489 and 672 s whoever commanded, and Kislev only by survival time (Sol 366-413 s, Luna
293-365 s). This supports the audit's recommendation; the selection remains the owner's.

**M1c (decided under the owner's overnight delegation, 09:21 UTC).** About three hours of
game time and $17 of budget remained. A third model on the scenarios that separate models
adds more than further repeats of the demotion candidates: gpt-6.1-sol (low,
`llm_rules` v18), three battles each on siege defence, swarm command, caster assault and
cavalry, same conditions, about $12 and 2.4 hours, ending before the owner returns.

**M1c results** (`f7aae2a`, 09:21-11:30 UTC, gpt-6.1-sol low, `llm_rules` v18; every battle
ended on an engine result): siege defence won 3 of 3 (538, 538, 587 s; $3.00), swarm
command won 3 of 3 (497, 449, 455 s; $2.65), caster assault won 3 of 3 (726, 396, 297 s;
$2.32), cavalry won 690 s and lost 786 and 1102 s ($2.84). M1c cost $10.81; ledger $45.96 of
$52. Across the four scenarios, gpt-6.1-sol won every siege, swarm and caster battle;
gpt-6-sol won every siege and caster battle and two of three swarm battles. Each won
one of three cavalry battles; gpt-6-luna won one caster assault.
Three battles per model are a first matched sample, in-sample for prompts developed on
these scenarios.

**Report rework (owner's notes 1-10 and 12).** Implemented on `wh3-report-notes` and merged as
`0d530af` after independent design, cold-reader and data reviews (the data review found one
defect, an order-age pooling bug, fixed with a regression test). The page shows only core
scenarios and completed battles, opens on a clickable index of scenario maps with score
bars, uses one hue per model with bars on a shared scale, gives each mode an icon, frames
the replay on the fighting, marks accepted ability orders with a ring and shows each
model's battle development and orders in "Same battle, different plans". Item 11
(OpenRouter) stays pending in [reports.md](reports.md#pending-report-notes).

Two report decisions after the first real-data build, taken under the owner's overnight
delegation and easy to revert (presentation only; the test-setup fingerprint excludes
report files and notes): the caster family's core scenario is now the attacker variant
`tze-caster-skv-assault` (the defender `tze-caster-skv-screen` becomes a variant), and siege
defence is scored like land battles (100 for a win, otherwise the enemy share dead or out
of the fight). Ownership time had scored Luna 99 with one win in four and Sol 98 with three;
it stays on the run card as a measure. The finding sentence now summarises every core
scenario with three or more battles per model under one test setup.

**M1d** (`9d052a1`, 11:37-11:59 UTC, no API calls): scripted baselines where Figure 3 had
none. Caster assault: `rush_nearest` lost at 314 s, `attack_nearest` at 261 s. Kislev
survival: `attack_nearest` lasted 222 s and `hold` 223 s, against 293-413 s for every
model battle.

The canonical `reports/benchmark.html` was rebuilt at 12:05 UTC from 76 listed jobs: 93
completed battles in six core scenarios on the page; offline browser checks passed at
`report-checks/benchmark`. With three models the finding paragraph lists every
scenario's record and reads long; a shorter form is a candidate for the owner's review.

## 2026-10-16: Evacuation deferred; controller version labels fixed

`bench-b12-skv-evacuation-20261016` (`a9ba045`; Luna then Sol, `llm_rules` low) stopped at
setup 0.3 s into its first battle, before any model call: "authored deployment failed for
friendly/f1". Diagnosed, not fixed: `start()` in the battle script measures the authored
placement in the same tick as `teleport_to_location`, so it recorded the native ambush
column, 42-318 m from the authored spots. The first observation, 0.3 s later, had every
friendly unit at its authored spot, infantry and cavalry still re-forming 5-13 m behind it,
which the 2 m tolerance would also refuse. A fix measures a moment later (the setup
already waits for late native state) with a tolerance for re-forming that still excludes
the native positions. No spend; the register keeps the row as `unsupported_or_invalid`.

**Owner decision (2026-10-16 03:20 UTC):** the custom evacuation scenario moves to the end
of the plan as a low-priority item. It stays specified and offline-tested but outside the
active core until resumed; six candidate families with live evidence remain. The failed
attempt joins the canonical report's job list.

Version labels: `controllers.VERSIONS` still said `llm`/`llm_rules` v17 and `commander` v4,
so the six b12 battles carry v17 in their controller cards although they ran v18 (their
source revisions identify the code; `results.csv` has no version column). The constant
now matches the "On main" table and a test compares them. Harness fingerprints hash the
sources, so no report grouping changed.

## 2026-10-16: Harness b12 and distinct scenario families

Implementation saved; live work stopped at the owner's request after six battles on
2026-10-16. Evacuation still needs original-engine validation. The owner approved a compact core of 6–8 unique decision
problems, a native siege/survival/conquest tranche and one authored evacuation pilot.
The [design audit](benchmark.md#scenario-design) records each question, plausible plays,
nearest family, novelty and evidence. Existing cavalry/caster revisions count once per
family; swarm attack/defence remain provisionally distinct. Old pilots remain evidence.
Deferred self-comparison definitions separate workload, neutral context, useful history,
factual representation and observation age.

b12 declares the four rosters, permits a recruitment-card namespace distinct from the
banner, and selects/verifies explicit reinforcement pools. Survival checks the selected
mode and disabled timer rather than the land-map type and stale hidden timer; its wall
limit still produces truncation. Lobby probes under `capability-probes/expansion-20261016/`
verified all five race card menus and the seven-unit Kislev pool. Failed probes preserve
an outdated Wood Elf faction key, a map-type mismatch, an unavailable survival role swap,
and the lobby's reordering of the reinforcement pool; none launched a battle or called a
model. Exact live battle checks and exploratory results follow below.

Validation before live screens: 385 WH3 tests passed; the full suite passed with
1017 tests and 14 optional-dependency skips after granting local-socket access. A further
reinforcement-order regression and the documentation checks passed (70 tests); Ruff passed.
The original native-mode golden prompts are byte-identical; evacuation has a new golden
mode fixture. Browser validation and live outcomes are recorded as they complete.

The observation contract becomes `obs-v4+terrain/act-v2/live-1x`: an optional public
`mode.custom` carries only the evacuation rules and friendly progress. Authored placements
stay in private setup. The script requests an engine ending on extraction, asset loss or
deadline; native outcomes and objective outcomes remain separate. Each rematch reloads
its objective state. `llm`/`llm_rules` v18 and `commander` v5 render these public rules;
existing native-mode prompt snapshots remain unchanged. Evaluator v2 soldier/unit counts
are unchanged; objective version 1 is separate.

The shared report uses tickets, ownership time and extraction counts for their respective
modes, and duration for endless survival. It keeps casualty measures but no longer presents
them as objective progress. The replay marks the public extraction circle.

The first live-screen job, `bench-b12-siege-reserve-20261016`, stopped before a battle
or model call: Helmgart's map metadata also says `land_normal`. The repaired setup reads
`BattleTypeRecordContext.Key` for every lobby mode and separately validates the declared
engine mode. The report retains this setup failure. The existing Empire inventory also
caught `great_cannon` as the exact evacuation card key before that scenario ran.
Offline browser checks passed at `report-checks/b12`.

First siege outcome (`bench-b12-siege-reserve-r2-20261016/episode-0000`, Sol low,
`llm_rules`): lost at 508 s, $0.9301, mean order age 5.16 s, 98 decisions and 19 rejected
orders. The setup matched 9 Chaos Dwarfs versus 16 Greenskins; initial supplies were 6000.
Victory-location ownership was 92% of observed time, key building 100%; 8 builds were
accepted and 2616 supplies remained. Enemy soldiers: 520 alive, 502 active of 1151
registered; own 151 alive of 419, none active at the rout.

Observed plays: four early magic towers, then additional cheaper construction; the Bull
Centaur reserve intercepted trolls outside the gate at 23 s and was withdrawn after heavy
losses; later orders tried to fall back toward retained points. The central supply point
fell before the key building. Through the first 112 moves, 96 were accepted (14 were
unreachable and 2 were refused on routing units); fallback was executable, though target
selection mattered. All 25 Magma Cannon shots remained at the end. Other missile units
also retained most ammunition. These are observed missed opportunities, not proof of an
alternative winning tactic. Luna's completed screen is recorded next.

The same job's Luna-low rematch won at 688 s ($0.0674), 110 decisions, mean order age
6.23 s and 21 rejected orders. Every recorded starting position and bearing matched;
resources/loadouts matched too. Victory ownership was 91.89%, key building 100%, eight
builds and 4103 supplies left. Luna fired the cannon (five shots already spent by 375 s)
and recovered the central supply point before the ending. Keep this as a distinct
exploratory family: reserve commitment, firing positions, construction and fallback were
all executable. One win and one loss do not establish a model ranking or a win-rate band.
The two battles cost $0.9975; ledger total is $15.3120.

Before survival, review of the old native trace found its reinforcement context empty at
5600 ms and populated at 6000 ms. b12 now waits up to five seconds of running battle time
for a declared pool to appear before the first policy call; an absent/wrong pool still
fails setup. This never pauses the battle. A requested custom ending must receive engine
confirmation within five seconds; a script error or missing confirmation is an unsupported
condition, never a fabricated win. The report now selects one core candidate per family,
labels variants/history, prints mean survival seconds, and frames the extraction circle.
Validation after these changes: 392 WH3 tests and Ruff passed. The canonical report now
includes both siege attempts; offline browser checks passed, including survival durations.


The first Kislev job (`bench-b12-kislev-reserves-20261016`) stopped in the lobby before
any battle or model call: its 14000 budget counted the reinforcement pool as well as the
starting army. Decoded base costs are 8500 + 6250 = 14750. Its declared lobby budget is
now 20000; the exact ten starting units and seven reserves are unchanged. Native supplies
and reinforcement prices are checked separately in battle. Conquest costs 6900 versus
7700, and evacuation 4450 versus 5200, within their declared budgets. The failed job is
retained in the canonical report list.


Completed survival retry (`bench-b12-kislev-reserves-r2-20261016`, `0746138`): Luna-low
lost at 322 s ($0.0315; 49 decisions, 35 rejected orders, mean age 6.52 s); Sol-low lost
at 406 s ($1.0023; 82 decisions, 38 rejected orders, mean age 4.91 s). Both verified the
same ten starting units, seven initial reserves and 1020 supplies at 6.8 s. Rematch
positions, bearings, resources and loadouts matched exactly. Native income continues
while the bridge waits; this is why the first balance is above 1000.

Luna first purchased at 130.8 s and brought in four cheap units; it lost spawn access
at 176.8 s and ended with 5875 supplies. Sol bought both 500-cost Kossars at 12.4/18 s;
observed balances fell 1020 -> 620 -> 240 despite income. It deployed all seven initial
reserves, including artillery at 131.6 s and bears at 186.4 s, then lost access at 254 s
and ended with 5165 supplies. The native pool subsequently changes, including returned
unit types and different costs; only the starting pool is pinned. New units registered
and accepted ordinary orders. Keep the family: reinforcement timing and keeping an
entry point open are available choices. Neither loss proves the roster unsolvable.
There is no wave forecast, healing or restock API in this version. Rejects were mainly
orders to routing units; Luna also tried unavailable lord abilities. They remain policy
errors in the evidence, not omitted trials. Job cost $1.0338; ledger $16.3458.

The full suite after the setup fixes passed: 1024 tests, 14 optional-dependency skips.


Completed Conquest screens (`bench-b12-slaanesh-conquest-20261016`, `21e45ee`): Sol-low
lost at 353 s ($0.5410; 83 decisions, one rejected order, mean age 4.24 s), Luna-low at
250 s ($0.0190; 39 decisions, 11 rejected orders, mean age 6.16 s). Recorded friendly starts/resources matched; enemies were not visible
at the initial snapshots.
Both captured the central point; Sol finished with 238/600 tickets against 40, Luna with
72/600 against 106. Their armies routed before the ticket target. Job cost $0.5600;
ledger total $16.9058.

**Demotion from the core.** The original Conquest brief assumed separated points. The
live state exposes only one at (256,0), as did the old Alpine Ridge pilot. The
[official Conquest description](https://community.creative-assembly.com/total-war/total-war-warhammer/blogs/23-total-war-warhammer-iii-patch-5-1-0)
also describes one central point. Native capture, raiding and retaking were executable,
but these trials do not meet their stated distributed-control question. Preserve them
as reference evidence and mark `core_candidate: false`; do not count a different mode
as unique by itself. Seven candidate families remain. A future Domination design can
use the three-point geometry already observed on Arnheim, but must pass its own novelty
and reinforcement-confound review. No extra scenario is added merely to fill the slot.
The report descriptions now specify the armies, objective and resource constraints of
all four new scenarios. The local numeric ticket goal is 600; the native help text's
older 500-ticket wording is not used for scoring.


The first evacuation attempt (`bench-b12-battery-evacuation-20261016`, `56ef648`) failed
readiness before a battle or model call: all eight AI recruitment clicks were silently
ignored. Lobby-only probe `capability-probes/expansion-20261016/r6-woodelf` confirmed that
the default faction is Anmyr, the available banner list contains only minor factions,
every Wood Elf unit card is inactive, and the resulting army list is empty. Card presence
was insufficient evidence of recruitability. The roster is marked unavailable, without
claiming a complete DLC ownership audit. Declared rosters now verify `UnitList.Size`
before readiness; the missing-army regression is covered offline.

The replacement `emp-battery-skv-evacuation` (scenario version 2) preserves the same
Empire escort, battery ids, public goal, deadline, map and authored positions. Its eight
opponents are a Warlord, two shielded Stormvermin, two poison Gutter Runners, two Night
Runner slingers and Rat Ogres, using existing selectable Skaven cards. Decoded base cost
is 5325 versus the escort's 4450. The installed attribute table confirms `stalk` on the
Gutter Runners. This substitutes available content while preserving the distinct moving-
asset and scouting problem; it adds no second family. The first failed attempt remains
in the report list.


At the owner's “wrap it up” request (2026-10-16 02:39 UTC), no more battles were launched.
The Skaven replacement and lobby recruitment-count guard passed 436 WH3/documentation
tests and Ruff. The earlier full suite passed 1024 tests with 14 optional-dependency skips;
the new regression adds one test. Six battles are complete in this tranche, plus three
preserved setup failures (siege metadata, survival budget, unavailable Wood Elves).
Spend added in the tranche: $2.5912; ledger $16.9058 of $25. No controller or queue remains
active. Next is original-engine validation of `emp-battery-skv-evacuation`, including its
scripted ending and rematch; neither that new roster nor the custom objective has yet run
in a battle. Do not present it as a proven seventh family. Later self-comparisons remain
specified only, with no new experiments launched.

The final canonical report was rebuilt with 61 jobs, 91 displayed battles in 22 scenarios
and six core families with live evidence (six older diagnostics remain inspectable
separately). Offline Chromium checks passed at `report-checks/b12`, including survival
durations, scenario navigation and standalone downloads. The custom marker is
offline-tested; there is no real evacuation replay yet.

## Index

- 2026-10-15: [Report: sections by game mode](#2026-10-15-report-sections-by-game-mode) ·
  [Report: one score per commander](#2026-10-15-report-one-score-per-commander) ·
  [Report redesign for outside readers](#2026-10-15-report-redesign-for-outside-readers) ·
  [Harness b11: common measures and one report](#2026-10-15-harness-b11-common-measures-and-one-report) ·
  [Integrate llm v17 and commander v4](#2026-10-15-integrate-llm-v17-and-commander-v4) ·
  [Prioritize scenario variety and shared measures](#2026-10-15-prioritize-scenario-variety-and-shared-measures) ·
  [Plan revision and preparation](#2026-10-15-plan-revision-and-preparation) ·
  [Calibration C1, launches 3 to 6](#2026-10-15-calibration-c1-launches-3-to-6) ·
  [Calibration C1, launches 1 and 2](#2026-10-15-calibration-c1-launches-1-and-2) ·
  [Skaven swarm screens](#2026-10-15-skaven-swarm-screens) ·
  [Harness b10, `llm` v16 and the calibration decisions](#2026-10-15-harness-b10-llm-v16-and-the-calibration-decisions) ·
  [Unit costs and attributes from the game database](#2026-10-15-unit-costs-and-attributes-from-the-game-database) ·
  [Skaven swarm drafts](#2026-10-15-skaven-swarm-drafts) ·
  [Several models in one job](#2026-10-15-several-models-in-one-job) ·
  [Queue stops on changed rematch starts](#2026-10-15-queue-stops-on-changed-rematch-starts) ·
  [Report redesign](#2026-10-15-report-redesign) ·
  [Track cleanup for agents and reviewers](#2026-10-15-track-cleanup-for-agents-and-reviewers) ·
  [Sol visual acceptance and closer action views](#2026-10-15-sol-visual-acceptance-and-closer-action-views) ·
  [Native imagery probe and passive capture](#2026-10-15-native-imagery-probe-and-passive-capture) ·
  [Recorder acceptance and imagery candidate](#2026-10-15-recorder-acceptance-and-imagery-candidate) ·
  [Visual replay v1 and recorder candidate](#2026-10-15-visual-replay-v1-and-recorder-candidate)
- 2026-10-14: [Offline benchmark field report v1](#2026-10-14-offline-benchmark-field-report-v1) ·
  [Partial G1 and owner-requested stop](#2026-10-14-partial-g1-and-owner-requested-stop) ·
  [Benchmark harness b9 (timer classification and running baseline)](#2026-10-14-benchmark-harness-b9-timer-classification-and-running-baseline) ·
  [Benchmark harness b8 (caster control)](#2026-10-14-benchmark-harness-b8-caster-control) ·
  [Benchmark harness b7 (snapshot age and cavalry attacker candidate)](#2026-10-14-benchmark-harness-b7-snapshot-age-and-cavalry-attacker-candidate) ·
  [Benchmark harness b6 (Pegasus pressure hypothesis)](#2026-10-14-benchmark-harness-b6-pegasus-pressure-hypothesis) ·
  [Benchmark harness b5 (draft while b4 screens ran)](#2026-10-14-benchmark-harness-b5-draft-while-b4-screens-ran) ·
  [Benchmark harness b4 (compact specialist prototypes)](#2026-10-14-benchmark-harness-b4-compact-specialist-prototypes) ·
  [Benchmark harness b3 (specialist interface and `llm_rules`)](#2026-10-14-benchmark-harness-b3-specialist-interface-and-llm_rules) ·
  [Benchmark harness b2 (terrain, lobby modifier, Herald screens)](#2026-10-14-benchmark-harness-b2-terrain-lobby-modifier-herald-screens) ·
  [Benchmark harness b1 (paired trials, acceptance rotation)](#2026-10-14-benchmark-harness-b1-paired-trials-acceptance-rotation) ·
  [Battle types, llm v15 and commander v3 (overnight)](#2026-10-14-battle-types-llm-v15-and-commander-v3-overnight)
- 2026-10-13: [Random-battle comparison, partial (into 2026-10-14)](#2026-10-13-random-battle-comparison-partial-into-2026-10-14) ·
  [Ability readiness and army abilities, llm v14 and commander v2 (`9bfee82`)](#2026-10-13-ability-readiness-and-army-abilities-llm-v14-and-commander-v2-9bfee82) ·
  [Controller comparison on `kho5-dwf5`, stopped for random battles (late)](#2026-10-13-controller-comparison-on-kho5-dwf5-stopped-for-random-battles-late) ·
  [Shooter re-send fix, executor v1.2 (`55ab6b3`)](#2026-10-13-shooter-re-send-fix-executor-v12-55ab6b3) ·
  [Random battles](#2026-10-13-random-battles) ·
  [Skills and commander v1](#2026-10-13-skills-and-commander-v1) ·
  [Unpaused 1x battles only](#2026-10-13-unpaused-1x-battles-only) ·
  [Automatic startup video skipping](#2026-10-13-automatic-startup-video-skipping) ·
  [v13, continuous decisions and expanded battle controls](#2026-10-13-v13-continuous-decisions-and-expanded-battle-controls) ·
  [Early findings (milestones, first night, mirror battles)](#2026-10-13-early-findings-milestones-first-night-mirror-battles) ·
  [v12, v6's melee rules with v10's fire rules](#2026-10-13-v12-v6s-melee-rules-with-v10s-fire-rules) ·
  [v11, the lords never fight alone](#2026-10-13-v11-the-lords-never-fight-alone) ·
  [v10, shooters hit infantry in the open](#2026-10-13-v10-shooters-hit-infantry-in-the-open) ·
  [v9, fight the enemy holding you](#2026-10-13-v9-fight-the-enemy-holding-you) ·
  [v8, answer the enemy's guns](#2026-10-13-v8-answer-the-enemys-guns) ·
  [Mirror battles (second session)](#2026-10-13-mirror-battles-second-session) ·
  [v7, the enemy lord only while he is losing the lords' race](#2026-10-13-v7-the-enemy-lord-only-while-he-is-losing-the-lords-race) ·
  [v6, show what each unit is really doing](#2026-10-13-v6-show-what-each-unit-is-really-doing) ·
  [v5, a hurt lord keeps fighting](#2026-10-13-v5-a-hurt-lord-keeps-fighting) ·
  [v4, one body, gang up on the enemy lord](#2026-10-13-v4-one-body-gang-up-on-the-enemy-lord) ·
  [v3, commit and focus (best so far)](#2026-10-13-v3-commit-and-focus-best-so-far) ·
  [v2, a battle doctrine (worse)](#2026-10-13-v2-a-battle-doctrine-worse) ·
  [Baseline after the lapse fix](#2026-10-13-baseline-after-the-lapse-fix) ·
  [v1, first LLM battles](#2026-10-13-v1-first-llm-battles) ·
  [First baseline](#2026-10-13-first-baseline)

## 2026-10-15: Report: sections by game mode

The owner: there is no divide between challenges and specialist scenarios (all are
challenges); the page needs one expandable section per battle type, with an empty
placeholder where nothing has run yet, before per-mode measures (objective time,
resources, reinforcements) come later. Changes:

- **Modes**: `report_html.MODES` lists the game's custom battle types in page order (land
  battles, siege defence, siege attack, minor settlement, survival, conquest, domination,
  ambush, chokepoint, subterranean, free-for-all; sieges split by the player's role, the
  lobby names checked against `probe-battle-types-20261014`). Each scenario gets its mode
  from its declaration; Figure 3 is one fold per mode, empty ones saying so. The notes'
  `group` field is gone; the pilots' challenge text is plain ("A pilot with Khorne's five
  units, run before the benchmark's setup checks...").
- **Review fixes** (an independent design, reader and data review of `df27399`):
  - Scores: a 99.8% loss printed as 100 (now capped at 99 unless won); 17 older pilot
    battles recorded casualties but not active strength, so their losses dropped out while
    wins scored 100 (they now count the enemy killed, labelled, with a regression test).
  - Figure 2 shows one map per model (settings pooled, †) and the page opens on Figure 1's
    scenario, so the replay and both figures show the same battle; Hold position, which
    never gives orders, is left out by name.
  - The score, order age and the +10% variant are defined once, as Figure 1's footnotes;
    the variant is "Cavalry assault, stronger enemy" (no "hard" beside "very hard"); the
    finding names its scenario; Figure 1 adds API cost per battle.
  - Template tells removed: the name-over-rule masthead (now one column), the kicker, heading
    rules, middle-dot strings, the "Featured battle" tag and panel eyebrows; Method is one
    column; the roster folds; the playing note's sentence sits under the note titles; the
    sans stack drops DIN Alternate (bold-only on macOS); serif text uses lining figures.
  - A shadowed `points` in the run card's measures, which the browser check caught, is
    fixed; unused code (`wilson`, `broken`, the `pin` export, four CSS variables) is gone.

Checks: `uv run pytest` (992) and `uv run ruff check .` pass; the browser check passes on
`reports/benchmark.html`, now also asserting the mode sections, the placeholders and every
Figure 3 model score against a recomputation.

A second independent review (structure, data, design) found the request met: no divide
left, 11 sections covering every lobby type, every score matching a recomputation, and no
generated-design tells left. Its follow-ups, applied: disclosure markers on the mode
sections, the scenario select grouped by mode, the page opening on Figure 1's scenario by
choice rather than notes order, the current scenario's fold opening, Figure 1's caption
naming the mode and saying Figures 2 and 3 pool all its battles, a † on Figure 3's scripted
cell when it spans harness versions (Charge nearest's 29 against Figure 1's 28), Figure 2
counting every battle and opening the earliest finished one, the casualty-only note
counting the 7 affected losses, and small type fixes (a two-line title, no hyphen break in
model names, aligned captions, no double rule, no pulsing dot).

Then six scenarios that had no question or challenge text got one (the Sigvald and Herald
Dwarf-gun defences, cavalry against halberds with and without the Pegasus general, Kairos
against Skaven screens): drafted from their declarations, recorded rosters and the game
database, each claim checked by an independent adversarial fact checker that corrected
every draft; they await the owner's review with the analyst notes. A final whole-page
review at `71d9988` found every requirement met but the one-minute view; so the finding now
opens the page under the title (with the army still on the first desktop screen), Figure
1's caption no longer claims Figure 2 shows its scenario, the run card names the setting
its record covers ("won 0 of 7 here with low reasoning"), the timeline's view-age band is
taller on a 0–15 s scale, Method explains the battle menu's "tactics" and "plans", and
Figure 3's scenario names look clickable.

## 2026-10-15: Report: one score per commander

The owner's review of the outside-reader redesign: it still looked generated (the header
above all), showed every attempt where one item per commander would do, repeated "+10%
enemy stats", and the real-time section was bloat. Changes:

- **Aggregation**: a commander's battles in a scenario become one score (per battle, 100
  for a win, else the percentage of the enemy army broken; the mean over finished
  battles, defined once in Method) shown as a bar with a worst-to-best line. Figure 1 (the
  C1 controlled comparison), Figure 2 (one map per commander: every battle's army track
  thin, their mean thick, with score, wins, order age and cost) and Figure 3 (each model's
  score in every scenario, the best scripted rule beside it) replace the per-battle marks,
  the per-battle route maps, the results rows and the matrix of marks. A finding sentence
  from Figure 1's numbers opens Results.
- **Cut**: "The battle doesn't wait for the model" (sawtooths, lede, inspection button and
  its placeholder; the added-delay experiment is now one line in Method). Latency stays
  as order age beside every score and in the replay (waiting counter, view-age band,
  Model's view, now on while the key maneuver autoplays).
- **Style**: a paper page around one dark replay panel; DIN-style lettering for headings
  and numbers, a book serif for prose; no icon, badge, nav, all-caps labels or cards; the
  replay is the page's first figure under a two-column masthead.
- **Text**: the hard variant is "Cavalry assault (hard)", its +10% stated once as Figure
  1's footnote (a notes `footnote` field); a battle that did not finish reads "Did not
  finish", its failure in Run settings.
- **Data**: `route` keeps one army centroid per 5 s instead of every unit's path; `timing`
  keeps order and plan ages only (26.3 MB page).

Checks: `uv run pytest` and `uv run ruff check .` pass; the offline browser check
(rewritten for the figures) passes on `reports/benchmark.html`. The moving army is on the
first screen at 1440×900, 1280×800, 1536×750, 1024×768 and 390×844.

## 2026-10-15: Report redesign for outside readers

The owner asked for a benchmark report that an AI researcher who knows nothing about the
game would stop to read: comparisons that read at a glance instead of "117 / 217 · 323 /
530", no run-set sections about code revisions, the real-time aspect easy to see and
compare, a less generic style, and lean code. [reports.md](reports.md#the-page) describes
the page. No game ran and no model was called; `reports/benchmark.html` is rebuilt from
the same 55 jobs.

What changed on the page:
- **Commanders, not run sets.** One row per commander (model, effort, prompt or scripted
  rule) per scenario. A row can span several harness versions; its name then carries a †
  and Run settings names each battle's. The collector's JSON and text keep the strict
  groups. A harness fingerprint hashes the job's source files except presentation, the
  scenario declaration without its prose, game build, track, timing and recorder/stills
  switches, so C1's two revisions (docs and report files only) count as one.
- **Enemy army broken**, one mark per battle on a shared 0–100% axis (filled won, hollow
  lost, a cross for did not finish), replaces the soldier-count tables: `1 −
  active/registered` of the enemy at the end, floored below 100%, "n/a" when the evaluator
  did not record it.
- **The headline** beside the title is the largest controlled comparison in the first
  notes group: the commanders shared by two or more launches of one harness. Today that is
  C1: 6 launches, gpt-6-sol 1/6, gpt-6-luna 0/6, both baselines 0/6, median order age
  5.7, 6.3, 0.3 and 0.3 s.
- **Same battle, different plans**: route maps of every battle, one column per commander
  over one framing. On the cavalry assault every gpt-6-sol battle loops around the halberd
  screen; every other commander's paths run straight at it.
- **Real time**: per commander, one minute of its first finished battle as a sawtooth of
  the age of its latest view (on the cavalry assault between about 3 and 14 s for gpt-6-sol
  and gpt-6-luna at low effort, up to 22 s for gpt-6-luna at medium effort, 0.3 to 1.8 s
  for the scripted baselines), the median and 90th-percentile order age, and the measured
  battle/wall clock ratio (0.98–1.00 there). The same view age is the replay timeline's
  lowest band and, behind "Model's view", outlines of the view behind the latest reply.
  "See what moved during one reply" pins the median-age reply, showing every unit that
  moved 5 m or more. The asynchronous commander is charted by its plans' age (only plan
  adoptions carry `plan_age_s`), not its executor's 0.3 s. A labelled placeholder names
  the deferred added-delay experiment.
- **Honesty**: the curated C1 battle (gpt-6-sol's one win in 6) states the commander's
  record and that it is not a typical result; Method says every scenario is in-sample
  development; pooled cells in All scenarios carry †; the 6 diagnostic-probe battles and 6
  setup-only launches are counted under "Not shown"; analyst notes are labelled as written
  with AI assistance; one note's causal wording ("broke the guns") became the observed
  sequence after checking the frames; battles that reached the 20:00 timer read "at the
  time limit" although b8 recorded them as `engine_result`; Method lists what a model
  actually receives, beside abridged verbatim lines of one message and its reply.
- **Style**: a dark stage and a light results page, one type scale, a neutral UI accent so
  blue and orange mean only the armies, the decision panel's repeated caveats said once,
  and on a phone the results keyed and the hero chart moved after the battle.
- **Size**: the embedded replays keep only the fields the page draws, coordinates to
  0.1 m: the suite page went from 35 MB to 27 MB.

Notes: `brt-cavalry-emp-assault-hard` is titled "Cavalry assault, stronger enemy (+10%
stats)"; both cavalry challenges explain why a frontal charge is risky (the halberd and
gun claims already checked in the game database); scenarios carry a `group`.

Reviews: three independent critiques (target reader, information design, rigor) and a
synthesis, then a second reader and rigor round on the rebuilt page, then an acceptance
review against each requirement of the request plus a maintainability review of the code.
Their findings were applied except a latency-against-outcome scatter, rejected because
speed is confounded with the model here; the added-delay experiment is the controlled test.
The acceptance round moved the battle onto the first desktop screen (the page opens on the
key maneuver's moment and plays it once in view), kept the decision panel's orders in view
with a two-line run card, capped route columns at three maps, put the view age on one
0–25 s scale everywhere, removed data the page never read and a duplicate model test, and
repaired a browser check that had stopped asserting routes. A last independent
re-verification (measured first screens, a newcomer read-through) led to: the challenge
text under the timeline and autoplay at a quarter of the map in view, so the moving army
is on the first screen at 1280×800 to 1536×750 and on phones; the cavalry pair renamed
"standard stats" and "+10% enemy stats"; the enemy AI's difficulty named; orders before
their age in the decision panel; and the featured battle's five analyst notes shortened
to 28–44 words each, with no new claims. A second re-verification found the decision panel
rebuilt every 0.1 s during playback, so normal clicks on its buttons were lost; it now
updates only the waiting counter between decisions. It also folded "what happened next",
moved the "queued steps continue" note into a tooltip, put the headline chart after the
viewer below 1081 px and stacked the results rows below 901 px (no sideways scroll on
tablets). A final check rated the lean-text item a pass (decision panels median 87 words
without orders, 104 with) and found commander-battle defects, now fixed: the pinned view
showed the unit skills' 0.3 s window as the model's view, and executor ticks repeated
"No reason was recorded" and a waiting line. Folds also stay open across decisions.

Validation: full `uv run pytest -q` and lint; prettier (width 100); the offline browser
check passed on the canonical page, a copy, the synthetic demo and the two-model pair page
at 1440 and 390 px, with no external requests or browser errors.

## 2026-10-15: Harness b11: common measures and one report

The owner authorized the first three plan steps. Alongside v17/commander v4 above,
evaluator v2 adds whole-unit registered/destroyed/alive/active counts, with routed,
leaving, absent and unreadable counts. Zero living entities is death; invalid targets
alone are not. Counts include later registered arrivals and deduplicate returning ids;
resurrection changes the current counts rather than accumulating kills. Existing soldier
totals, policy observations and the environment track stay unchanged. The evaluator
version is recorded in the manifest and evaluation; controller cards now record versions.

The report collector and HTML expose both sides' net headcount losses, survivors and
whole units, per-point engine-tick ownership duration/share, supplies, tickets, accepted
builds and purchases, duration, order age, API cost and failures. Failed runs retain
partial progress; missing historical counts stay unavailable. Historical snapshot-voting
shares are not presented as objective time. Scoring stays outside policy inputs and public
replay exports; no aggregate ranking or scenario-specific score was added.

`reports/benchmark.html` (with JSON/text) is built from the explicit
`configs/twwarhammer3/benchmark_jobs.json` list using `report --jobs-file`: 55
jobs, 91 started trials (85 engine outcomes), 19 scenarios and 10 battle types: cavalry,
swarms, specialist screens and historical mode pilots, including failed attempts. Older
mode pilots lacked declaration names; the selector now uses their saved config names
instead of putting every unnamed mode together. Source revisions, evaluator versions and
game builds remain separate evidence groups. A collapsible overview shows armies and
coverage; each scenario keeps its comparisons, run settings, notes and replays. Existing
scenario reports are retained. The single-file HTML is about 33 MiB. Related scenarios
have distinct readable titles. Matching controller class/prompt hashes across source
revisions no longer claim identical controllers: shared dependencies can change too.

Runtime prerequisite: Steam updated after C1 to 9.0.4.0, build 25961564 (complete install,
no staged bytes). The executable reports The Creative Assembly Ltd; SHA256
`9bd58c63bd7fc5c9909b3d3d9b6b7a6ae4eac784369bf91a9e53c3e9f42be496`. Updated the pins
and retained the prior build/hash in integration.md. `doctor` is ready. Older 9.0.3
trials retain their provenance and are not pooled with new-build checks.

Live validation: `bench-b11-measures-20261015`, source `c251401`, ran 17:39-18:00 UTC.
Luna low controlled both episodes of `dwf-line-skv-swarm`, unpaused 1x, added age zero,
Steam build 25961564. The rematch preserved roster, strength, loadout, resources and
positions; both episodes ended on engine losses. Total cost $0.09664; ledger $14.3146
of the $25 cap.

| Controller | Loss at | Friendly units destroyed / alive | Enemy units destroyed / alive | Soldiers remaining, friendly / enemy | USD |
|---|---:|---:|---:|---:|---:|
| commander v4 | 592.7 s | 2 / 5 | 0 / 20 | 71 / 1416 | 0.05376 |
| llm_rules v17 | 460.0 s | 1 / 6 | 0 / 20 | 155 / 1702 | 0.04289 |

Both started with 7 friendly units / 331 soldiers and 20 enemy units / 1961 soldiers.
At both losses every surviving friendly unit was routed, none active; the commander
episode also retained one living leaving unit. Initial/final evaluator v2 counters
reconciled. All 753 decision observations and 1046 replay frames exclude evaluation,
final and setup data. Clock ratios were 1.000 and 0.988. Range feedback appeared in both
live controllers. Neither battle triggered the last-sighting annotation; that case was
checked by rendering actual historical routed-enemy observations through v17.
Audits: `validation/b11-engine-check.json` and `validation/b11-v17-historical-rendering.json`.
Arrivals, returns, resurrection and unreadable counts have Lua regressions; those new
counters still need mode-specific engine evidence as the scenarios expand. These smoke
trials validate integration, not controller improvement or a model ranking.

Validation: full `uv run pytest -q` passed (990 passed, 14 skipped); lint passed.
Tests cover routing versus death, absence/withdrawal, late/returning units, failed reads,
resurrection, historical missing measures, point identity/duration, information boundaries,
explicit input lists and unnamed pilot navigation. Offline Chromium checks passed on the
canonical HTML and a copy: all 19 scenarios, replay navigation/downloads, historical
missing measures, both new whole-unit results, objective point/time fields, controller
versions, desktop and phone layouts. No external requests or browser errors.
Screenshots/downloads are in `report-checks/benchmark/`; test and audit artifacts are in
`validation/`. No new scenario or calibration campaign is included.

During validation the owner clarified scenario selection: difficulty is useful only
when there are meaningful plays. The plan and report guidance now require exploitable
advantages, manageable choices about disadvantages and room for those decisions to
change progress. Use the exploratory runs to inspect recognition and execution; redesign
or drop scenarios with no credible options, retaining their evidence. This applies to
existing cavalry/swarm challenges too, without reinstating a win-rate admission rule.

## 2026-10-15: Integrate llm v17 and commander v4

Merged `wh3-llm-v17` (`c1cc14b`) into current main. Shooter target lines now say how far
beyond range a target is and that the unit advances to shoot. Last-sighting memory keeps
wavering, routing and shattered state, explicitly labelled as the state when last seen.
The commander shares both rendering and memory, so this is `llm`/`llm_rules` v17 and
commander v4. No system prompt, executor or environment contract changed; the track stays
`obs-v3+terrain/act-v2/live-1x`.

Validation: 44 LLM/commander/prompt tests and all 349 WH3 tests passed; `uv run ruff check .`
passed. Golden prompts did not change (their cases do not trigger the new feedback).
The [b11 smoke check](#2026-10-15-harness-b11-common-measures-and-one-report) validates
the shared renderer and both controller versions in the game. Existing results and
register rows retain their original revisions.

## 2026-10-15: Prioritize scenario variety and shared measures

The owner refined the plan again, with implementation still out of scope: general
milestones (kills, survivors, objective time and similar measures) come first;
scenario-specific points are a possible later improvement. The immediate goal is more
battles that look and play very differently, including varied land armies, siege,
survival and conquest. Start each new scenario with 2-3 exploratory battles total;
deeper testing can follow later.

Updated the [implementation plan](benchmark-implementation.md#history), state, root/track
READMEs, battle-type next steps, runbook and report plan. The previous ten-battle proposal
across three scenarios is superseded; it was never launched. Keep the old calibration and
cavalry/swarm evidence, with no repeat campaign required before adding new modes.

The audit distinguishes content work from missing mechanics: siege defence, survival,
conquest and the other modes already ran end to end, mostly with the same small
Khorne/Dwarf armies. Distinctive rosters/maps/objectives are the next content work.
Siege attack's gate/wall/equipment gap does not block defence. Survival/domination hide
the lobby timer expected by the current strict benchmark declaration checks; adapt those
checks for the selected mode, without treating a controller wall limit as a game timer.

Common measures use existing headcounts and objective integrals first. Whole-unit
destruction/survival counts need minimal shared evaluation counters, not scenario-specific
scoring or a full per-unit event recorder. Historical missing counts stay unavailable.
Reporting expands incrementally at one canonical HTML entry point; scenario-specific
scores, complete model matrices and added-delay experiments remain later work.

No gameplay/source/configuration changes, branch merges, report builds, queues or paid
calls. Validation: `uv run pytest tests/test_doc_links.py -q` (43 passed),
`uv run ruff check .` and `git diff --check` passed.

## 2026-10-15: Plan revision and preparation

The owner requested planning, documentation updates and stale-file cleanup, with no
implementation of the five discussed changes. The
[plan](benchmark-implementation.md#history) now starts with hard cavalry/swarm challenges,
partial progress beside engine outcomes, model comparisons under declared conditions,
natural latency, and one canonical HTML report for the suite. The 30-70% admission gate
and automatic switch to AI ×1.0 after C1 are retired. Added-delay experiments and broader
scenario/model work are deferred. C1 and the swarm screens remain development evidence;
this preparation does not claim new experimental findings.

The implementation audit refined the plan:
- `wh3-llm-v17` changes controller memory/rendering only, not the environment's public
  observations, actions or timing; the earlier `obs-v4` description was wrong. The
  commander shares those functions, so integration needs both controller versions and
  their tests. The branch remains unmerged.
- Final evaluation totals already support casualties and active survivors by unit type,
  and objective integrals exist for applicable battle types. Exact per-unit milestones,
  HP/value scores and original-roster-only denominators need more recording. Routing is
  not destruction; report missing measurements explicitly. New derived measures will
  version the evaluator, without rewriting old results.
- Multi-scenario HTML already works. The missing pieces are a canonical report build,
  suite overview and progress presentation. Supporting assets may remain embedded;
  splitting them is conditional on measured size/loading, not a new requirement.

Updated the state, root/track READMEs, benchmark, runbook, controller candidates, battle-type
next steps and report docs. C1's six-launch completion and the swarm's actual Warlord
roster/protected Engineer are now consistent across them. Compressed obsolete calibration
discussion to historical summaries with its existing link anchors; the full former text
remains at `ae7ca31:docs/twwarhammer3/benchmark.md`. The original owner briefs are retained.

Cleanup under this request: pruned eight worktree records whose `/tmp` directories no
longer exist; deleted the merged branches `wh3-benchmark-b2`, `-b3`, `-b4`, `-b5`, `-b7`,
`-b8`, `-b9` and `wh3-visual-final`; deleted `wh3-visual-imagery` (`af8f76e`) after
`git cherry main wh3-visual-imagery` verified its only commit was patch-equivalent to
main's `ca397ab`. No working files or unique work were removed. Kept v17 and its
component branches, the unique older candidates, all saved runs/reports, queue plans,
register rows and ledgers. Old queues are explicitly historical, not next-run commands.

No source/configuration code changed, no report was rebuilt, no game ran and no paid
model call was made. Validation: `uv run pytest tests/test_doc_links.py -q` (43 passed),
`uv run ruff check .` and `git diff --check` passed. Game/source tests are reserved for
implementation; this change is documentation and repository housekeeping only.

## 2026-10-15: Calibration C1, launches 3 to 6

Launches 3-6 of C1 ran from about 11:05 to 13:10 UTC-3 (`bench-c1-cavalry-ai11-03-20261015`
to `-06-`, queue `runs/twwarhammer3/calibration/c1-plan-rest.json`, completed); their 16
register rows are committed with this entry. Over all six launches: `llm_rules` on Sol won
1 of 6, `llm_rules@gpt-6-luna`, run-nearest and walk-nearest 0 of 6 each; every battle
ended on the engine's result. WH3 ledger: $14.2179 of $25. The report
`reports/c1-cavalry-ai11.html` covers all six launches. The results have not been analysed
or read against the C1 rule yet: that waits for the owner.

## 2026-10-15: Calibration C1, launches 1 and 2

The first two of C1's six launches on `brt-cavalry-emp-assault-hard` (AI ×1.1), harness b10
and `llm` v16 (source `8434cd3`), each rotating the four controllers
([decisions](benchmark-implementation.md#history)); the morning queue ran them after
the swarm screens, unattended, and completed. Every battle ended on the engine's result;
none reached the timer.

| Launch | Controller | Outcome | Battle s | Own active | Enemy active | Order delay s | USD |
|---|---|---|---|---|---|---|---|
| `bench-c1-cavalry-ai11-01-20261015` | `llm_rules`, Sol | lost | 1017 | 0 | 0.570 | 5.58 | 1.4358 |
| | `llm_rules@gpt-6-luna` | lost | 298 | 0 | 0.530 | 5.14 | 0.0254 |
| | run-nearest | lost | 214 | 0 | 0.802 | 0.30 | 0 |
| | walk-nearest | lost | 325 | 0 | 0.875 | 0.30 | 0 |
| `bench-c1-cavalry-ai11-02-20261015` | `llm_rules`, Sol | **won** | 487 | 0.203 | 0 | 5.77 | 0.6706 |
| | `llm_rules@gpt-6-luna` | lost | 803 | 0 | 0.260 | 8.03 | 0.0484 |
| | run-nearest | lost | 244 | 0 | 0.692 | 0.30 | 0 |
| | walk-nearest | lost | 350 | 0 | 0.849 | 0.30 | 0 |

So far Sol 1 of 2, Luna 0 of 2, both baselines 0 of 2: within the admission band, far from
decided. Sol's battles cost $0.67 and $1.44 (the lost one lasted 17 minutes), more than
the ×1.0 runs; at that rate launches 3-6 cost about $4-6. The per-policy rotation recorded
each trial's own model end to end (manifest, card, register). The register rows of the
screens and these launches are committed with this entry. WH3 ledger: $10.0391 of $25.

Sol's win against its loss, from the traces (a read-only review): both openings went
south of the obstruction for the guns ("Advance the cavalry around the south side of the
central obstruction to approach the enemy flank" in the win), and the guns broke at
similar times (186-236 s and 197-226 s). After that the win kept fighting the halberdiers
until the last broke at 487 s (they fell from 360 to 93 men). The loss withdrew, and from
376 to 1002 s 100 of its 114 reasons were about finding the routed guns, which the
prompt's last-sighting memory listed at the map edges without saying they were fleeing;
the halberdiers lost 58 men and the army routed at 1005 s. Supported: continuing against
the halberdiers separated the two. Plausible, not shown: the last-sighting entries led the
search. Unsupported: the route or losses on the way in decided it (124 and 120 knights at
about 257 s). The report `reports/c1-cavalry-ai11.html` features Sol's win as the selected
example with two analyst notes written from its recorded events (`report_notes.json`; a
second reader confirmed the first and corrected the second, which missed a rally; the owner
has not reviewed them).

Luna's two battles, by the same kind of review: both opened with a straight charge at the
line ("Exploit cavalry speed to disrupt the cannon and handgunners while the lord engages
the enemy general." in the first), with no flanking route, and met the halberds first. In
the 298 s loss the Lord won its duel with the General but the knights broke against the
halberds; in the 803 s loss the Lord lost the duel, units were withdrawn from 115 s, the
Lord stood idle in a corner from 365 to 689 s, and the knights later killed the fleeing
General and shattered one halberd unit before routing. Supported: the straight approach
in both, unlike Sol's; that the withdrawals explain the longer battle is plausible only.

## 2026-10-15: Skaven swarm screens

Both swarm drafts ran one screen each under the owner's authorization, on harness b10
with `llm` v16 (source `8434cd3`): `bench-b10-screen-skv-swarm-r2-20261015` and
`bench-b10-screen-dwf-line-20261015`. The first attempt (`bench-b10-screen-skv-swarm-20261015`)
stopped in the lobby before any battle: the declared `wh2_main_skv_cha_grey_seer_ruin_0` has
no card (a caster with several lores has one, `_plague_0`). Setup now dumps every army's
cards to `cards_slot<N>.txt`; the Warlord leads instead, the Warlock Engineer is the caster.

Results (table in [benchmark.md](benchmark.md#scenario-design)): every player army was
routed. Luna lost the swarm attack at 457 s (enemy 0.706 active) and the Dwarf hold at
444 s (0.640); run-nearest lost the attack at 288 s (0.921) and `hold` the hold at 565 s
(0.529; 0.561 over the original force, since a summoned Skaven unit joins the total),
outlasting the model: the model's repeated attacks on an enemy cannon out of range pulled
its Organ Gun and shooters out of the line ([benchmark.md](benchmark.md#scenario-design),
[controllers.md](controllers.md#candidate-changes-for-the-next-version)). Both prototypes
are now `prototype_not_admitted`. Cost
$0.064, both Luna battles.

Order delay grows with the units in view, observed across unrelated runs (Luna low,
mean per battle, from results.csv; versions and battles differ, so this is a motivation
for the army-size experiment, not a measurement): about 5-7 s with 10 units on the field,
6.5-7.3 s with 24, 8.2 s with 27 and 9.2 s with 29.

The independent check of the analyst notes, under the owner's delegation, dropped none
and corrected six (a melee start at 4:04 not 4:05, all five units attacking the
handgunners, the opening plan's other targets, "no men lost" limited to the Lord and
knights, "new moves" not "re-issued routes", "about" on a sparse-frame time). It also
found that "in melee with X" trusted the target field alone; a melee fact now needs the
target recorded within 50 m.

## 2026-10-15: Harness b10, `llm` v16 and the calibration decisions

The owner, away until 11:00 (UTC-3), delegated the open WH3 decisions to the agent's
judgement and authorized the swarm screens. Decided and recorded:
- **`llm` v16** (`llm_rules` shares it): the `wh3-llm-fresh-move` fix is merged (`005a050`).
  A move applied at the observed instant reads "your move to (x, z) issued this instant",
  not "stopped N m short". Golden prompts are unchanged; prompt text differs only in that
  state.
- **Benchmark harness b10**: per-policy models (`NAME@MODEL[/EFFORT]`), the queue's
  start-change stop rule, v16, and the redesigned report. Track unchanged
  (`obs-v3+terrain/act-v2/live-1x`).
- **Calibration**: the options in [benchmark.md](benchmark-implementation.md#history)
  are adopted as block C1 on `brt-cavalry-emp-assault-hard`: `llm_rules` on Sol low
  (reference) and on Luna low, run-nearest and walk-nearest, rotated in each launch.
  Primary measure: the engine outcome before the timer. Two of the six launches run
  this morning (the time until the owner returns); the other four are a frozen plan.
- **Analyst notes**: accepted under the delegation after one more independent check,
  which corrected six of eight ([swarm screens entry](#2026-10-15-skaven-swarm-screens));
  the owner can still revise them.

## 2026-10-15: Unit costs and attributes from the game database

`scripts/wh3_db.py` decodes a table of the game's `db.pack` with RPFM's schema, read-only
([integration.md](integration.md#packs-and-loading)); a synthetic table tests it. Two uses
so far, no game run:
- **The swarm drafts fit their funds**: decoded `multiplayer_cost` totals are 7850
  (Skaven) and 8200 (Dwarfs) for `skv-swarm-dwf-line`, 6300 and 8350 for
  `dwf-line-skv-swarm`, under 12000; no unit exceeds its multiplayer cap. As a check, the
  taurox rosters that played under large funds decode to 10675 and 11525.
- **The report's unit text now rests on game data**, not only recorded base stats:
  Halberdiers have a +16 bonus against large units with charge defence and charge
  reflection against large, so their role reads "Anti-cavalry infantry"; 38 of the
  Questing Knights' 52 damage is armour-piercing and they are immune to psychology; Grail
  Knights have magical attacks and never tire; Mounted Yeomen Archers fire on the move;
  Great Cannons cannot run; both generals encourage nearby units. Weapon damage plus
  armour-piercing damage matches each unit's recorded `weapon_damage`, which cross-checks
  the decoding. Nothing decoded is committed.

## 2026-10-15: Skaven swarm drafts

Two specialist scenarios from the owner's 2026-10-14 steering ("commanding/fighting
Skaven swarms") are declared as drafts, never run: `skv-swarm-dwf-line` (20 Skaven, led by
a Grey Seer with a few weapon teams, attack 9 Dwarfs on a gun line) and
`dwf-line-skv-swarm` (7 Dwarfs hold against 20 Skaven; the defender wins at the timer).
Status `draft_not_screened`; rosters, protected units and the screens they need are in
[benchmark.md](benchmark.md#scenario-design). Every unit key exists in the game's English
localisation, read from `local_en.pack` without extracting anything; both declarations
pass `validate_declaration` and build their lobby steps offline. Unit costs are not
recorded anywhere, so whether both rosters fit the 12000 custom funds is the first thing a
screen checks. The report notes carry each scenario's question for when it runs. The
`setup.py` field reference no longer says `status` puts a scenario in the HTML report.

## 2026-10-15: Several models in one job

A model policy can name its own model and effort, `NAME@MODEL` or `NAME@MODEL/EFFORT`
(`controllers.policy_parts`), so one launch can rotate, say, `llm_rules` on Sol and
`llm_rules@gpt-6-luna` on the same battle instance; launches are the benchmark's sampling
unit, so model comparisons can now be paired within them. Bare names keep `--model` and
`--effort`; a name resolving to another's model and effort is refused as a duplicate.
Cards, results and the report keep the full name; the register records the base policy
with the model and effort played; the job saves one prompt per base policy. Reports of
existing jobs are byte-identical. No game ran and no model was called: an adversarial
review with fake jobs found six issues (a card-less trial named with the job's model, the
review workflow's stale prompt-file guidance, readers checking old suffixes against
today's prices, no browser test of suffixed names), all fixed with tests; the synthetic
pair report in `make_wh3_report_demo.py` now exercises suffixed names in the browser check.
`uv run pytest -q`: 974 passed, 14 skipped.

## 2026-10-15: Queue stops on changed rematch starts

`scripts/wh3_queue.py` now applies the recorded G1 start rule itself: after each job it
reads every episode's `start_comparison` and stops the plan (status failed) when a
rematch started with a missing or changed unit, or changed strength, loadout or
resources. Position and bearing flags alone stay in the result. A resumed calibration
no longer needs a separate audit for this; admission is still audited separately. No
game ran. Tests: `tests/twwarhammer3/test_wh3_queue.py` covers both kinds of change and a
geometry-only flag.

## 2026-10-15: Report redesign

The owner's brief ([WH3_report_redesign_guide_for_Codex.md](WH3_report_redesign_guide_for_Codex.md))
asked for a report that lets a newcomer watch an AI command an army, understand its
consequential decisions and compare results, with the bookkeeping moved out of the
reading path. The HTML page was rebuilt around that order (watch, what happened,
compare); [reports.md](reports.md) describes it. No game ran and no model was called.

The brief asked for its items to be mapped to the repository first:
- **From existing records**: readable names and roles (the game's onscreen names,
  checked against the English localisation, and comparisons checked against each
  episode's recorded `unit_base_stats`), orders in plain words with queued steps and
  rejections, what the recorded frames show after each batch, the information age per
  decision on the battle clock beside the model's wall-clock reply time, stable map
  framing, issued routes apart from observed trails, the engine outcome with the timer
  rule, and run sets compared in plain words (the two Sol runs share controller code and
  prompts; the later one added the recorder and stills).
- **Small additions**: `configs/twwarhammer3/report_notes.json` (scenario question and
  challenge, unit roles, the selected run and its analyst notes); the collector's
  `order_age_median_s` and `battle_ms`; replay payload fields (unit identities, `steps`,
  `summary`, `next`, key events).
- **Needs new instrumentation, runs or an owner decision, so not built**: a real-game
  clip (no video capture exists), unit artwork (the owner ruled out pack art on
  2026-10-14), unit attributes that are not recorded (anti-large and armour-piercing live
  in the game's database tables), response-to-visible-effect timing, and the army-size,
  context and delay experiments, now defined in
  [benchmark.md](benchmark-implementation.md#experiments-for-later).

What changed:
- The page leads with the scenario's question, the selected run (outcome, duration,
  "Single recorded battle"), one sentence of input conditions and the replay. Removed
  from it: the masthead, throughput and wall time, the scenario declaration, the stills
  wall, failed-capture placeholders, the margin chart, the trial and tactical tables and
  the evidence section. They stay in the JSON and text reports, Run settings and the
  downloads. The 15 unrun catalogue placeholders are gone, which settles the deferred
  item.
- The moment panel follows the replay clock and never shows a reply before it applied;
  it gives the model's stated reason as a quotation (with a key for the unit ids it
  uses), the orders, what happened next and how old the information was. Before/after
  inspection is an explicit, pinned mode that includes the orders' targets.
- Five analyst notes on `visual-sol-low-20261015` (one is the featured maneuver) and three
  on the G1 Sol trial, each checked against the records by two independent reviewers. The
  brief asks for human review: the owner has not reviewed them yet.
- The active-strength margin no longer appears on the page (the brief: it counts routing
  men as lost and weighs units equally); the collector still computes it.

Findings:
- **The state taken as a batch applies predates it.** Units that were just ordered still
  show idle there. The replay's "what happened next" now ignores that frame. The `llm`
  prompt called such units "stopped N m short of your move": in the G1 Sol battle the
  model re-issued all six routes three times in 26 s. The fix is on branch
  `wh3-llm-fresh-move` (`5959587`), unmerged: it changes prompt text, so it is a new
  controller version and part of the calibration discussion.
- The cavalry assault already separates controllers at ×1.0 on outcomes alone (Sol low
  3 of 3, Luna 0 of 2, scripted 0 of 7, across revisions); options for the owner are in
  [benchmark.md](benchmark-implementation.md#history).

Validation: `uv run pytest -q` 949 passed, 14 skipped (the `train`/`llm` extras and the opt-in
Windows test); `uv run ruff check .` and prettier (width 100) clean; the offline browser
check (`tests/twwarhammer3/check_wh3_report_browser.cjs`) passes on the three jobs and
the demo at 1440 and 390 px. Reviewers read screenshots against the brief's six reader
tasks; a data review rebuilt all 200 recorded episodes without a crash. The rebuilt page
is `reports/cavalry-assault.html` (1.7 MB).

## 2026-10-15: Track cleanup for agents and reviewers

The owner asked for the WH3 code and repository to be easier for agents and outside
reviewers to read and navigate: less bloat, redundancy and stale or confusing docs. An
audit of eight areas fed six code lanes and three docs lanes. No game ran and no model was
called; the work was uncommitted when this entry was written.

What changed in the code:
- CLI. `twwarhammer3 report JOB [JOB ...] --output STEM` writes `STEM.html`, `STEM.json`
  and `STEM.txt` and replaces `stats --report/--report-json/--report-html`. `stats
  --rebuild` is gone: it rebuilt only from `battle/`, so it dropped six visual-probe rows,
  re-added two interrupted episodes and rewrote 288 cells; the register is append-only
  history. New: `digest EPISODE --at SECONDS` (one decision in full: the prompt its reply
  answers, the raw reply, the orders and the engine's verdicts) and `watch JOB --next
  [--stall-minutes M]` (waits for the next episode result, the job's end, a stall or a job
  that never started, prints it and exits). `play` lost `--ledger`, `--results`,
  `--no-autostart` and `--no-menu`; `launch` lost `--interval-ms`, `--no-autostart` and
  `--no-menu`, and `play --attach` uses its own `--interval-ms`. `--episode-timeout`
  defaults to a declared scenario's timer plus 120 s (else 3900 s) and `--run-timeout` to
  8 h, or longer when the episodes need it.
- Job loop and scenarios. Scenario loading, lobby steps and benchmark checks moved from
  `battle/play.py` to `battle/setup.py`, whose docstring is the scenario field reference.
  A `scenarios.json` entry can inherit another with `base` (the file went from 1623 to
  576 lines; the resolved scenarios that manifests record are identical). A refused
  declaration, realism preference or uncommitted source scope no longer leaves a job
  directory, so the same `--output` can be retried. Model jobs snapshot
  their prompt as `<policy>_prompt.md`. Objective shares come only from the mod's tick
  integrals. The setup saves its menu dumps on every exit. `session.json` no longer
  carries `interval_ms`. `scripts/wh3_queue.py` runs a frozen plan of `play` jobs one at
  a time; the untracked `calibration/run-*.py` runners are evidence only.
- Controllers. `probe_move` is gone. `battle/controllers.py` holds the one table of model
  policies and their prompts. `llm.py` shares `split_valid`, `strengths`, `render_clock`
  and `invalid_reply` with the commander and lost its unreachable paused-battle sentence;
  `scripted.distance` is public. `tests/twwarhammer3/test_wh3_prompts.py` compares the
  exact rendered prompts of `llm` (whose input `llm_rules` shares) and `commander` with
  golden files: no prompt byte changed.
- Reports and capture. `battle/capture.py` replaces `imagery.py` and `recording.py`;
  `visual_probe.py` and `report_html.py`'s `--demo` entry are deleted, and the synthetic
  demo comes from `tests/twwarhammer3/make_wh3_report_demo.py`. The replay payload lost
  its derived duplicates and names controllers as the controller table does; `replay.css`
  merged into `report.css`; a report with stills fails loudly without Pillow. The replay
  verdict's median information age is now the collector's order-age median over
  non-empty batches: 5.25 s instead of 5.1 s for the G1 Sol trial, 4.2 s instead of
  3.9 s for `visual-sol-low-20261015`. The saved artifacts in `reports/` predate this.
- Tools. The job digest has a policy column and no longer crashes on random survival and
  free-for-all draws; the episode digest folds runs of decisions without new orders into
  one line (`no new orders xN until T s`). `watch` no longer crashes at a classic
  battle's result and shares the commander's report header. New register rows round
  `own_active` and `enemy_active` to 3 decimals. The `engine/mailbox.py` docstring is the
  bridge and observation reference; a job start also clears the previous job's per-battle
  replay, imagery, still and capture files from the bridge.
- Tests. lupa and Pillow joined the dev group, so plain `uv run pytest` runs the Lua and
  image tests (21 Lua tests skipped before). The six `test_wh3_lua_*.py` files became
  `test_wh3_battle_lua.py`, which loads battle-script definitions by name
  (`tests/twwarhammer3/wh3_lua.py`); `test_wh3_mod_scripts.py` compiles every mod script
  under Lua 5.1, replacing the manual parse step. `tests/test_doc_links.py` checks every
  relative link and anchor in the repository's Markdown. `uv sync --locked` now removes the
  `llm` and `train` extras' packages; restore them with `uv sync --locked --extra llm` (or
  `--extra train`).

Docs: `benchmark.md` is the benchmark as built, `benchmark-run.md` the runbook and the new
`reports.md` the report page. `benchmark-progress.md`, `calibration-plan.md`,
`scenario-recipe.md`, `field-report.md` and `visual-report-plan.md` were folded into them;
their text stays at `d606d39`. The owner's modding guide `guide.txt` (dated 2026-10-08,
unchanged since `001d1ce`) left the tree: `git show 001d1ce:docs/twwarhammer3/guide.txt`
restores it, and its API links are in integration.md "References". The README,
integration.md, controllers.md and battle-types.md are reference pages now: the README's
milestones, first-night and mirror sections and battle-types.md's per-job tables moved
into this log; integration.md is grouped by subject, with the "Expanded controller
interface", "Specialist unit state" and "Timer result transition" sections folded into
"Battle" and the "Unverified" heading shortened; controllers.md lists every registered
policy, drops the flying-unit gap fixed in `dde4cfe` and records three prompt/code
contradictions for the next version. This log is newest first throughout, with "On main"
above; `docs/state.md` is a short status page; AGENTS.md, the root README and
`runs/README.md` match the code.

Evidence moved (untracked, local): the outside controllers of recorded trials
(ExternalHold and the flight probe) from `/tmp/wh3-benchmark-controllers/` to
`capability-probes/external-controllers/`, and the old replay-demo generator to
`reports/make-wh3-replay-demo.py`.

Validation (2026-10-15, before the commit): `uv run pytest -q` passes with 14 skips (13
need the `train`/`llm` extras' torch, one is the opt-in Windows process-ownership test);
`uv run pytest tests/twwarhammer3` passes with none skipped; `uv run ruff check .` passes;
the review workflow parses as JavaScript.

Deferred, with the reason:
- Lua cleanups, each needing one engine smoke battle, and no game could run: the
  pause-mode leftovers (constant `speed` and `awaiting_orders`, session `speed` and
  `pause`, `mailbox.require_realtime`), dead paths (the `start` control,
  `state.applied_ms`, restart's fallback before a decision, the duplicate imagery
  throttle and `shot.backend`), the always-true session switches `enabled`, `autostart`
  and `menu`, splitting `apply_order` and `mode_section`, sharing the observation code,
  and moving the file helpers into `_lib`.
- Three prompt/code contradictions for the next `llm`/`commander` version
  ([controllers.md](controllers.md#candidate-changes-for-the-next-version)): prompt bytes
  change only with a logged version and regenerated golden prompts.
- `LLMPolicy.acknowledge` keeps its fallback for acknowledgements without `index`: about
  2,900 of 25,300 acknowledgement results in `battle/` traces (30 jobs before `863d10b`)
  lack it. The owner decides.
- Single-job reports still list the 15 unrun catalogue scenarios as placeholders
  (unchanged from `d606d39`); removing them is the owner's decision.
- `play --attach` request ids restart at `r1`, so a second attach job on the same battle
  can stall until its episode timeout; a per-mailbox id prefix fixes it.
- The 49 unrounded `own_active`/`enemy_active` values already in results.csv: the register
  is append-only history, so rewriting old rows is the owner's call.
- Stale `/tmp` worktrees and merged WH3 branches: the agent had no permission to remove
  them; the owner will, with `git worktree remove /tmp/wh3-benchmark-bN` for b2, b3, b4,
  b5, b7, b8 and b9 and `git worktree remove /tmp/wh3-visual-imagery`, then
  `git branch -d wh3-benchmark-b2 wh3-benchmark-b3 wh3-benchmark-b4 wh3-benchmark-b5
  wh3-benchmark-b7 wh3-benchmark-b8 wh3-benchmark-b9 wh3-visual-final` and
  `git branch -D wh3-visual-imagery` (patch-identical to `main`'s `ca397ab` per
  `git cherry`). Whether to archive the unmerged `wh3-fire-report` and `wh3-v4-info`
  (pre-v13 candidates) is the owner's call.

## 2026-10-15: Sol visual acceptance and closer action views

The separately authorized `visual-sol-low-20261015` on `7136d6a` ran `llm_rules`
(`gpt-6-sol`, low) on `brt-cavalry-emp-assault`, unpaused at 1x with default recording and
`--stills`. It won at 382.4 s: 92 decisions, four engine refusals, 4.11 s mean information
delay, $0.6292834; ledger $7.7949 of $25. This is visual acceptance, not a resumed
calibration or an extra G1 trial. The replay has 473 frames and 168 submitted orders (167
acknowledged, one unacknowledged at the end), and embeds every prompt and reply, 14
readable names and two stills (first melee at 179.9 s, ending at 382.4 s). The opening
foreground check failed and the first rout at 208.1 s was throttled; both are kept as
such. Passive grabs took 62.6 / 32.5 ms in the separate capture process. Recorder terminal
and public-id checks passed (`visual-probes/sol-recorder-acceptance.json`). The report
keeps the new trial, the G1 triple and the interrupted launch in separate views.

Owner follow-up (2026-10-15): closer, low oblique action views, ideally before a charge,
melee or projectiles, chosen from observed public motion, within the four-still cap.
Imagery v3 takes an observed closing gap within 100 m before melee, with incoming fire or
first melee as fallbacks for the same action slot. The camera sits about 28 m above the
focus terrain with a side offset; the opening stays overhead; the 30 s throttle remains;
captions do not infer charge intent.

The scripted `visual-probes/close-imagery-20261015` on `981eb2d` ran to its planned 90 s
cutoff (truncated, no engine result): the opening at 5.9 s and the first rout at 56.6 s
were captured, requested and actual camera coordinates matched, and grabs took
74.8 / 37.2 ms. Incoming fire at 16.1 s was throttled and used up the action slot, so
`8aaabcd` keeps that trigger and defers the capture until spacing permits, aimed at the
units under fire instead of the army centroid (regression test). The recheck
`visual-probes/close-imagery-r2-20261015` on `8aaabcd` ran to its 90 s cutoff with 279
decisions, none invalid, and no model spend; its last 0.124 s deadline surfaced as a
mailbox timeout, so it stays `truncated`. The opening at 5.9 s and incoming fire at 36.8 s
were captured (39.5 / 49.0 ms; the metadata keeps the initial 16.1 s trigger) and the
first rout at 59.0 s was throttled. The low view shows the missile cavalry and the
opposing line before the first observed melee at 71.0 s; camera placement matched within
0.001 m (`visual-probes/close-camera-acceptance.json`).

Artifacts: `reports/visual-report.html` (about 1.64 MB), `reports/close-camera.html` and
`reports/close-camera.png`; older images were not reconstructed. Validation: 1119
repository tests passed, one skipped (before the timing fix); the WH3 suite 273 passed with
Lua 5.1 and the report extra; Ruff passed; offline Chromium checked both reports' images,
evidence, downloads and 390 px layout. The requested visual-report work was complete;
calibration stayed stopped.

## 2026-10-15: Native imagery probe and passive capture

`visual-probes/imagery-20261015` on `f395275` ran the scripted Khorne-Dwarf probe at
unpaused 1x to its planned 90 s wall cutoff (truncated, no engine result). The native
`common.take_screenshot` wrote a 1920×1080 TGA (8,294,418 bytes) at 6.1 battle seconds in
43.007 ms. `UnitRecordContext.Name` and `UnitDetailsContext.Name` both returned "Herald of
Khorne"; the other two candidate fields returned nil. The engine kept the camera about 100 m above
ground instead of the requested 500 m and clamped its pitch (actual position in
`visual-probe-metadata.json`); no world/pixel registration is established.

`visual-probes/passive-imagery-20261015` on `081f30f` completed its 90 s cutoff with no
invalid decisions, ten names and two stills; first contact was throttled because it came
less than 30 s after the first rout. Passive grabs took 54.34 and 42.82 ms in the capture
process (PNG writes 296.66 and 256.36 ms) while the order loop continued; `stills.json`
keeps timing and failures. A wider camera height range still clamped the view; an in-game
diagnostic at 36.2 s enabled the cinematic-camera flag and reached the requested overhead
position exactly at 36.7 s, and the passive capture at 67.1 s showed the armies (probe
code, coordinates and image beside the job). Decisions: production uses that camera flag
(no cutscene, no change to unit controls, battle unpaused at 1x) and passive Windows
Pillow capture in a background thread with job, battle and foreground-process checks;
capture errors are presentation metadata, and nothing waits between decision and order.
Only the diagnostic probe used the native call. Images stay beside the grid, not on it.
No API spend in either probe. Engine facts:
[integration.md](integration.md#visual-recording-and-presentation-probed-2026-10-15).

## 2026-10-15: Recorder acceptance and imagery candidate

Owner-requested visual acceptance, not calibration. Source `581119e` ran sequential
`rush_nearest` cavalry probes at unpaused 1x: recorder off
(`visual-probes/recorder-off-20261015-r3`) lost at 391.7 s with no refusals; recorder on
(`visual-probes/recorder-on-20261015`) lost at 263.7 s with one `unit_routing` refusal
(the lord routed before the order applied). Not a controller comparison; both rows are in
the register. The first off attempt was refused before launch by timeout validation. The
r2 attempt stalled before the frontend timer; bringing the game forward unblocked it, but
the 900 s startup deadline expired after Start Battle: an infrastructure failure with zero
episodes, not a loss.

The recorder saved 260 frames (1,564,778 bytes) including the terminal result, at
0.9-1.2 s intervals around the 1 Hz target. All 104 timestamps shared with the trace had
matching public unit ids and types; no evaluation, setup or hidden final state entered the
recorder. Sample CPU time: mean 2.851 ms, median 2.991, p90 3.998, maximum 7.019.
Battle/wall ratios over the deployed span: 0.998213 off, 0.997703 on. One pair cannot
establish a precise overhead, but the cost supports recording by default, with
`--no-record-replay` (`visual-probes/recorder-acceptance.json`,
`visual-probes/analyze_recording.py`).

The imagery candidate added `--stills`, public-position camera triggers, readable names,
capture failure metadata and WebP embedding within the report size budget; featured trials
are the earliest completed, whatever their outcome. No API spend.

## 2026-10-15: Visual replay v1 and recorder candidate

Implemented phase 1 of the visual report plan (now [reports.md](reports.md); the plan is
`visual-report-plan.md` at `d606d39`) and the opt-in 1 Hz public recorder. The report keeps
the collector summaries, embeds gzip/base64 replay evidence and adds an SVG map, timing
and resource strips, unit lanes, exact prompts, stated reasons and notes, factual events
and shared-scale trial tracks. The recorder has its own visibility memory and per-battle
files, copied after each episode including interruptions; its version and settings enter
comparison compatibility.

The original G1 Sol trace has 441 submitted orders, 436 acknowledged, 29 rejected and five
unacknowledged at battle end; it confirms the enemy general's rout, not his death. All
three G1 payloads are under 160 KB compressed; nine trials fit under 20 MiB.

Owner decisions (2026-10-14): no unit art from the game's packs; exact prompts included,
collapsed in the inspector, with the system prompt shown once per job (this replaced the
field report's rule of leaving prompts out); scripted camera moves accepted during
unattended jobs. Design figures from the first G1 Sol trial: order age median 5.1 s by the
replay's measure (5.25 s as the collector's non-empty-batch median), 90th percentile 7.2 s,
maximum 11.1 s; between consecutive decision states friendly units moved 22 m (median) and
49 m (90th percentile); 17 ability orders, notes rewritten in 29 decisions, nine decisions
without new orders; prompts and replies 855 KB raw, 44 KB compressed. Replay frames per G1
trial: 423/302/98.

Validation: 1102 repository tests passed, one skipped (with the report dependency and the
Lua 5.1 runtime); Ruff passed; offline Chromium checked replay selection, playback,
keyboard, exact counts, synthetic exports, 390 px layout and the statistics, download and
print behaviour. Artifacts: `reports/visual-report.html`, `visual-report-demo.html`,
`visual-browser/`. No new rows or spend. The owner then asked for scripted recorder off/on
and imagery probes and a later Sol low check (about $0.80), as visual-report acceptance
separate from the stopped calibration.

## 2026-10-14: Offline benchmark field report v1

Added `stats --report JOB... --report-html FILE` (since 2026-10-15 `twwarhammer3
report`), calling the collector once beside the text and JSON outputs. One HTML file
embeds the assets and compact evidence: scenario briefs, selectable and sortable
controller comparisons, SVG timing, cost and added-age charts, tactical metrics,
expandable uncertainty, failure and provenance records, image and JSON downloads, and
printing. Different model/effort groups display together only under matching scenario,
source, game, interface and timing; their summaries and pairs stay separate.

`reports/field-report.html` came from the G1 cavalry 1.0 launch and the interrupted 1.1
setup, labelled **Development pilot: one independent launch**, with the interruption kept
at zero trials. Prior JSON values were unchanged; job definitions and provenance were
added. Catalogue entries give labelled unrun placeholders, never historical briefs. The
separate `field-report-demo.html` and a committed synthetic fixture used invented Demo
controller A/B/C results, 0/6/10 s arms and missing, failure, timer and repeat cases
(replaced on 2026-10-15 by `tests/twwarhammer3/make_wh3_report_demo.py`); synthetic
evidence cannot mix with recorded evidence.

Validation: reporting regressions, the WH3 suite, Ruff, and offline Chromium checks of the
summaries, filters, sorting, keyboard controls, 390 px layout, SVG/PNG/JSON downloads,
timer and missing metrics, setup interruptions and evidence separation, with screenshots,
a chart PNG and a three-page PDF inspected (browser artifacts in
`/tmp/wh3-report-browser/`). No games, API calls, register rows or ledger entries. Page:
[reports.md](reports.md).

## 2026-10-14: Partial G1 and owner-requested stop

G1 started at 21:56:01 UTC on committed `6763d0e`, with the declared Sol low `llm_rules`
reference, the walk- and run-nearest baselines, the compact six-versus-eight cavalry
attacker (`brt-cavalry-emp-assault`) and the original rotation seeds. The first 1.0
launch, `bench-g1-cavalry-ai10-01-20261014`, completed:

| Controller | Engine result | Battle seconds | Active margin | Refusals | API USD |
|---|---|---|---|---|---|
| Walk-nearest | Lost | 411.2 | -0.79623 | 0 | 0 |
| Run-nearest | Lost | 247.7 | -0.62830 | 1 | 0 |
| Sol low | Won | 528.2 | +0.54378 | 29 | 0.793363 |

Both rematch starts matched; clock ratios 1.00091, 1.00076 and 0.99333. Sol made 96
decisions and calls, 393565 input and 30155 output tokens (164065 cached, 9917
reasoning). Its refusals were 23 unreachable moves, five targets no longer visible and one
routing unit; it carried on with the normal feedback. It circled west and north, broke the
ranged line, drew the infantry apart and disengaged before re-engaging: a useful
specialist battle and one paired win, not admission. Report `reports/g1-cavalry-ai10-01.json`;
whole job 1373.64 s, 7.86 valid battles/hour.

At the owner's request to wrap up and discuss calibration separately, SIGINT stopped the
next job, `bench-g1-cavalry-ai11-01-20261014` (modifier 1.1), during frontend setup:
`interrupted` / `KeyboardInterrupt`, zero episodes, 64.48 wall seconds. The runner stopped
at 22:19:59 UTC and the owner then cleared the goal; the other ten planned launches never
started. This is an owner interruption, not a gameplay loss or an unexplained failure, and
the queue is not to be resumed silently. Combined report `reports/g1-cavalry.json` /
`.txt`, admission audit `reports/g1-cavalry-admission.json`, queue state
`calibration/g1-cavalry-plan-state.json`, stop note `calibration/g1-owner-stop.json`:
three valid of three started battles in two launched jobs, 1438.13 wall seconds including
the interrupted setup, 7.51 valid battles/hour. No scenario admitted, G1 incomplete, G2
unstarted, held-out maps untouched. Spend $7.1656 of $25. Further difficulty and latency
experiments wait for the owner's discussion
([benchmark.md](benchmark-implementation.md#history)).

## 2026-10-14: Benchmark harness b9 (timer classification and running baseline)

The b8 hold screen reached the timer with both armies intact. Its last finite countdown
sample was 945.679 ms remaining at 1204100 ms; the engine loss arrived at 1205200 ms,
154.321 ms past the implied deadline, with the remaining time reset to -1, so the
zero-only classifier recorded `ended_by=engine_result`. The engine loss is authoritative
and the timeout cause is inferred from its countdown; raw records are unchanged
(`reports/bench-b8-timer-classification-audit.json`).

Changes: `9f05777` samples the countdown on engine ticks, keeps its final deadline and
records its expiry apart from the engine outcome (regressions for unlimited timers,
disabled or extended countdowns and early results; replaying the recorded countdown
through the Lua helper identifies expiry). `33b7e2b` adds `rush_nearest`, AttackNearest
with the run flag. The calibration plan then took walk-nearest and run-nearest as the
cavalry attacker's tactical baselines and kept hold as its objective-failure control (an
untouched timer loss has raw margin zero); raw scoring, the 2-4/6 decisive-win criterion
and positive paired intervals against both active baselines were unchanged. After the b8
queue's evidence was committed as `4e4de1c`, b9 merged as `90a8796`. Validation: 223 WH3
tests with Lua and repository-wide Ruff.

Live on `a8fdf34`:
- `bench-b9-timer-acceptance-20261014`: hold lost at 1205.2 s with both armies intact, no
  refusals or API calls, clock ratio 0.999616. The raw countdown ends at -1, but the timer
  evidence gives deadline 1205045.875 ms and expired=true, so `ended_by=time_limit`. Whole
  job 1346.59 s, 2.67 valid trials/hour (`reports/bench-b9-timer-acceptance.json`).
- `bench-b9-assault-medium-ai10-20261014` (started 21:30:30 UTC): run-nearest's six
  initial run=true attacks were all accepted, and at 8.9 s each unit reported running,
  13.5-23.7 m from its 5.3 s start (`reports/bench-b9-rush-acceptance.json`). Run-nearest
  lost at 210.7 s (one refusal; the timer correctly unexpired, `ended_by=engine_result`).
  Luna `llm_rules` at medium effort lost at 214.4 s, margin -0.834 against the baseline's
  -0.791: matched start, 21 decisions, three routing refusals, $0.01520, clock 0.98169,
  mean issued order age 9.857 s; the halberds intercepted its direct attacks and its lord
  fought the general alone. Whole job 589.81 s, 12.21 valid trials/hour
  (`reports/bench-b9-assault-medium-ai10.json`).
- `bench-b9-assault-medium-ai11-20261014` (1.1): run-nearest lost at 256.7 s (margin
  -0.666, no refusals, clock 0.99837). Medium Luna lost at 341.7 s (-0.513): 35
  decisions, 13 refusals, matched start, clock 0.98596, 39 calls, $0.02566, mean order age
  9.339 s. It killed the general and routed the cannon and handgunners, then lost to the
  remaining halberds. Six ability refusals repeated accepted activations before readiness
  updated; three were dead targets and four routing units
  (`reports/bench-b9-luna-ability-refusals.json`, `reports/bench-b9-assault-medium-ai11.json`).
  Both screens: four valid of four started, 1354.34 wall seconds, 10.63 valid
  trials/hour, rematch starts matched. Spend $6.3723 of $25.

Decision before G1: freeze the compact cavalry attacker family and Sol low `llm_rules` as
the reference (b7's flanking win motivates it; the Luna low and medium screens did not
show competence), with walk- and run-nearest as baselines and source, prompt and rosters
fixed during calibration. Six launches per modifier on the original unused G1 seeds; if
both modifiers meet admission, G2 uses 1.1, else the passing one, else development
continues.

## 2026-10-14: Benchmark harness b8 (caster control)

Changes: `6b30737` adds the five-versus-ten caster attacker family (the defender's roster
and spellbook, only the role changes) with 1.0/1.1 settings and an untouched held-out map,
passing the declaration and setup-generation checks; the scenario recipe now also checks
objective incentives and the opponent's actual pressure. The b7 caster pilot had exposed
missing morale feedback and flight control: read-only UI queries at 793.3 and 836.2 s
reported that the flyers must attack by land, the corrected boolean query showed both
could toggle flight with no cooldown, and at 1070.9 s Kairos's largest effect was Army
losses and the fraction was -2.506; no query changed tactics or speed
(`capability-probes/benchmark-flight-toggle/`). `a0a7108` exposes friendly leadership
fraction and largest current effect plus flight availability and cooldown; both model
controllers accept `flight` orders, which the Lua checks against live state before the UI
command, and the requested state prevents reversing a completed change. The track became
`obs-v3+terrain/act-v2/live-1x` (b7 stays on its old contract). 215 WH3 tests with Lua,
Ruff and Lua 5.1 compilation passed; merged as `6a0fe53` after the b7 queue.

Live on `f179dbe`:
- `bench-b8-flight-probe-20261014` (`flight_probe:ProbeFlight`): both flyers grounded at
  7.9 s, still grounded after a repeated landing request at 8.2 s, airborne at 18.7 s once
  the cooldown expired; all six flight orders accepted. This checks completed transitions,
  not repeated requests mid-animation or every combat restriction
  (`reports/bench-b8-flight-acceptance.json`). The battle was lost at 372 s under
  AttackNearest, margin -0.486, two later refusals (dead target, routing unit), no spend,
  6.96 valid trials/hour (`reports/bench-b8-flight-probe.json`).
- `bench-b8-assault-screen-ai10-20261014` stopped at 19:56:04 UTC: attack-nearest received
  no new observation after sequence 1108 (340.7 s) for 60 s. Infrastructure failure: one
  refusal, 1108 decisions, no API calls, 545.74 wall seconds, no gameplay outcome; Luna,
  hold and the 1.1 screen unplayed. No Lua error in the mod log and no matching Windows
  application event; the cause is unresolved
  (`capability-probes/benchmark-b8-observation-stall/`,
  `reports/bench-b8-assault-screen-ai10-failure.json`).
- The retry `bench-b8-assault-screen-ai10-r2-20261014` (same implementation, scenario and
  rotation seed, no profile changes) recovered, which does not identify the stall's cause.
  Attack-nearest lost at 370 s (one refusal, margin -0.808, clock 0.9996). Luna
  `llm_rules` lost at 247 s (margin -0.589, clock 0.9976, matched start): it routed the
  cannon and both handgun units, but the lord and remaining cavalry lost to the general
  and halberdiers; 44 decisions, 12 refusals (six ability, six routing), 47 calls,
  $0.01922. All six ability refusals repeated an accepted activation on the immediate
  acknowledgement snapshot (`last_issued_ms` equal to its time while readiness still said
  true): readiness lag and repeated requests, not unsupported keys
  (`reports/bench-b8-luna-ability-refusals.json`). Hold lost at 1205 s with both armies
  intact (no refusals, matched start, clock 1.00004, raw margin 0), which exposed the timer
  label bug fixed in b9 and the limit of raw margin for idle attackers. With the failed
  first launch: 3 valid of 4 started, 2555.77 wall seconds, 4.23 valid trials/hour
  (`reports/bench-b8-assault-screen-ai10.json`, original timer label kept).
- `bench-b8-assault-screen-ai11-r2-20261014` (1.1): Luna lost at 271 s (45 decisions, 17
  refusals, margin -0.626, clock 0.9878, 49 calls, $0.02274), again routing the ranged
  units but losing to the general and halberdiers; hold lost at 1205 s with both armies
  intact (no refusals, matched start, clock 0.99992; raw label again `engine_result`, its
  countdown replicate appended to the timer audit); attack-nearest lost at 395 s (margin
  -0.868, no refusals, matched start). The queue completed at 21:05:37 UTC: 3 valid trials
  in 2055.85 wall seconds, 5.25 valid trials/hour. All cavalry screens with the failed
  attempt: 6 valid of 7 started, 4611.62 wall seconds, 4.68 valid trials/hour
  (`reports/bench-b8-assault-screen-ai11.json`, `reports/bench-b8-assault-development.json`,
  original timer labels kept beside the audit).
- The first 1.0 and 1.1 snapshots, both at 5.3 s, have all six player entries unchanged
  and all eight AI entries changed; the halberdiers' leadership 70→78, attack 26→29,
  defence 42→46, damage 28→31, charge 8→9 (`reports/bench-b8-cavalry-modifier-stats.json`):
  the applied settings, not a calibrated win rate.

No scenario admitted; ledger $6.3315.

## 2026-10-14: Benchmark harness b7 (snapshot age and cavalry attacker candidate)

Changes: `88de61a` and `2e643fe`, merged as `79d2f7d`, record the actual snapshot age
apart from the total order age, and keep start-comparison deltas plus a paired
sensitivity analysis without launches whose starts were flagged; primary results keep
every valid trial. Requested 0/6/10 s ages are minima (synchronous model calls can leave
gaps in the observation buffer); the runbook and CLI help say so. Recomputing the b4
traces keeps their primary samples and exposes the flagged cavalry launch in the secondary
comparison. `brt-cavalry-emp-assault` reverses the original foot-general candidate: the
same six cavalry units must defeat eight Empire units before the 1200 s timer, funds
capped at 8000, with 1.0/1.1 development settings and an untouched held-out map; a new
task, not pooled with the defender variants. 72 benchmark/play tests and Ruff passed after
the merge.

Sol low `llm_rules` pilots on `82f5626`:
- Caster `bench-b7-caster-sol-20261014` (`tze-caster-skv-screen`) lost at 1077 s: 281
  decisions, five refusals, margin -0.680, clock 0.9956, 282 calls, $1.78329; whole job
  1223.91 s, 2.94 valid trials/hour. It struck the artillery with spells, then withdrew and
  hid its escorts, planning a defender timeout win; after contact around 650 s the escorts
  were lost and the surviving flyers kept evading. An engine loss, not a timer ending
  (`reports/bench-b7-caster-sol.json`). Ground Pendulum was verified: accepted at 64.6 s,
  magic spent and cooldown visible at 70.9 s, while the immediate acknowledgement snapshot
  still showed pre-cast resources and readiness; exact damage attribution is not claimed.
  The b4 refused ground casts also lacked magic by acknowledgement after earlier casts
  took effect (11<16, 9<12), though their basis snapshots had enough
  (`reports/bench-b7-caster-ground-acceptance.json`,
  `reports/bench-b4-ground-refusal-resources.json`).
- Cavalry assault `bench-b7-assault-sol-20261014` (started 19:23:44 UTC) won at 432 s: 91
  decisions, one refusal, margin +0.433, mean action age 5.862 s, clock 0.9934, 92 calls,
  $0.62009; whole job 580.28 s, 6.20 valid trials/hour. Both handgun units and the cannon
  routed first; Sol then concentrated on the general while the remaining cavalry fought
  the halberdiers: a viable strategy, not admission (`reports/bench-b7-assault-sol.json`).

Both results are in the register; ledger $6.2895 of $25. Next was to screen Luna on the
same task before freezing a repeated reference, because 30 repetitions at Sol's cost would
leave almost no budget margin.

## 2026-10-14: Benchmark harness b6 (Pegasus pressure hypothesis)

`brt-cavalry-emp-pegasus` (1.0/1.1 development settings, untouched held-out map) keeps the
six-versus-eight roster and 8000 cap and replaces the enemy foot general with an Imperial
Pegasus mount. The frontend enemy-slot change and unit key passed; the Pegasus shows speed
105 and cost 1800 (a Griffon: 90 and 2050) against our cavalry's 84/92
(`capability-probes/benchmark-pressure-mounts/`). A faster flying enemy was meant to
pressure passive evasion; its AI behaviour was a hypothesis. Visible enemies now expose
walk/run speeds beside b5's flight fields, through the same queries as friendlies after
visibility filtering; the rules prompt states the facts without a strategy. 209 WH3 tests
with Lua, Ruff and Lua 5.1 compilation passed. The pilots were to try `gpt-6-sol` at low
effort as a stronger rules-only reference on the Pegasus and caster scenarios.

`bench-b6-pegasus-sol-20261014` on `1bd120b` hung after menu step 3 (opening custom
battle): Windows reported the game unresponsive while its CPU time grew, and the startup
deadline ended the job as `infrastructure_failure` after 903.87 s with zero episodes and
no model calls; the supervisor closed the game and the queue stopped
(`capability-probes/benchmark-startup-hang/`, `calibration/b6-startup-observations.jsonl`,
`reports/bench-b6-startup-failure.json`). The retry `bench-b6-pegasus-sol-r2-20261014`
(identical source and setup, no profile changes, started 18:51:24 UTC,
`calibration/b6-specialist-sol-r2-plan.json`) recovered. Its roster verified the
horse-mounted player lord and the airborne Pegasus general, with enemy speeds 10.5/10.5 m/s.
Sol moved for a flank, then chose to preserve a defender timeout win: at 385.6 s all six
friendly units were active with at least 93% health and the Pegasus was 367.7 m from the
nearest. Under the six-minute development review rule the pilot was interrupted for
inadequate pressure, not scored: 80 decisions, nine unreachable-move refusals, $0.46713,
clock 1.00004; the interrupted row is in the register (`calibration/b6-pegasus-review-rule.json`,
`calibration/b6-pegasus-retirement.json`, `reports/bench-b6-flight-speed-acceptance.json`,
`reports/bench-b6-pegasus-development.json`). The two launches used 1431.02 wall seconds
with no valid gameplay outcome; the runner stopped at 19:00:11 UTC, before the caster job.

## 2026-10-14: Benchmark harness b5 (draft while b4 screens ran)

The compact caster screen exposed missing flight information: the engine reports
Screamers as `inf_mel` despite `can_fly=true` and `is_currently_flying=true`, so the old
category rule rendered them as infantry. Flying non-commanders now take the flying
category (commanders keep their lord role), and units expose flight capability and
current airborne state, both in the initial-state comparison, without a prescribed tactic
(`dde4cfe`). A read-only query at 84.5 s verified Kairos and the Screamers airborne and
the three ground escorts not (`capability-probes/benchmark-specialist-flight/`). The b4
screen stayed on its frozen source. Timer-ended reports keep the engine's won/lost/draw
beside `time_limit`, with separate timeout-outcome counts and a "non-timer win rate"
label, so defender wins at the timer stay visible while the decisive-win criterion is
kept. Validation: 207 WH3 tests with Lua, Ruff and Lua 5.1 compilation; 25
report/setup/controller tests.

## 2026-10-14: Benchmark harness b4 (compact specialist prototypes)

Two development candidates, each with a 1.1 version and an untouched held-out map: six
Bretonnian cavalry units against eight Empire units (`brt-cavalry-emp-pikes`), and Kairos
with four escorts against ten Skaven units (`tze-caster-skv-screen`). The 8000 allowance
is a cap, not a target; both use explicit armies and default upgrades, and the cavalry
lord's Barded Warhorse is pinned. The frontend inventory verified the selectable cards and
excluded inactive DLC; the horse change returned `wh_main_brt_cha_lord_4` and Kairos
recruited with his default spellbook (`capability-probes/benchmark-specialist-rosters/`,
no battle). Scenario `mounts` maps recruitment indexes to mounted unit keys, with a lobby
read-back and a battle roster check; declared funds and settings now apply before
recruitment as well as being verified after. 69 benchmark/play tests and Ruff passed,
including refusal of a lord left on foot.

Screens on `e221324`:
- Caster `bench-b4-screen-caster-20261014`: Luna `llm_rules` lost at 963 s, hold at 613 s,
  attack-nearest at 301 s; margins -0.642/-0.771/-0.777; refusals 88/0/0; Luna $0.06841;
  whole job 2056.22 s, 5.25 valid trials/hour. Starts matched, including initial magic
  12/68; starting stats and nonzero barriers were captured. Unit-targeted spells used mana
  and entered cooldown; both unit-ground casts were refused, so that mechanic stayed
  unverified for Kairos (see b7). No reference won (`reports/bench-b4-screen-caster.json`,
  `reports/bench-b4-caster-interface-audit.json`).
- Cavalry `bench-b4-screen-cavalry-20261014`: hold lost at 415 s (margin -0.928, no
  refusals), attack-nearest at 262 s (-0.691, one refusal). That start was flagged: the
  missile cavalry displaced 4.826 m and the enemy lord turned 12 degrees in place, with
  resources, loadouts, roster and strength matching; the variation is kept for review, not
  dropped. Luna chose evasion for a timeout win; with the army untouched after several
  minutes the trial was interrupted at about 292 s to revise pressure and watchability: a
  legitimate defender strategy with **no gameplay outcome**, excluded from performance
  means, $0.01765 (`calibration/b4-cavalry-retirement.json`). Whole job 1148.78 s, two
  valid of three started, 6.27 valid trials/hour (`reports/bench-b4-screen-cavalry.json`).

A trace check measured Grail Knights at 2.01 m/s during the approach and 7.58 m/s just
before melee despite the walking setting: fast final movement, not a damage bonus
(`reports/bench-b4-cavalry-approach-check.json`). Next: a faster enemy anchor to pressure
evasive cavalry (b6).

## 2026-10-14: Benchmark harness b3 (specialist interface and `llm_rules`)

Draft commits `a9b066b` (missing-terrain gate, startup causes, whole-job throughput),
`7c71deb` (the `obs-v2+terrain` roster boundary), `6caacec` (ValueBase and Value kept
privately), `51c1796` (`llm_rules`), `2bdb0e5` (barrier and ability ranges) and `37f3ebf`
(starting resources):
- The missing terrain field seen in b2 acceptance fails setup before a controller acts.
  Unexpected startup or source errors keep their cause and are infrastructure failures;
  interruptions stay separate. Paired reports give valid trials per whole-job wall hour,
  counting setup, resets and failed jobs, or nothing when a job lacks final wall timing.
- Enemy registration could announce unseen arrivals, and an earlier sighting could reveal
  a later hidden death. `obs-v2+terrain` keeps the initial lobby roster public but adds
  later units only on sight; a death flag needs visibility. Scoring still uses private
  totals.
- The engine documentation says `CcoUnitStat.ValueBase` excludes modifiers and `Value` is
  current; startup keeps both privately. The b2 snapshots show that the AI difficulty
  bonuses already enter ValueBase (see b2).
- The owner's specialist-scenario direction exposed restrictive v15 tactical rules (stay
  in melee, cavalry wait behind infantry, all units advance together). `llm_rules` is the
  same direct controller, memory, ledger, observations, actions and timing with a separate
  rules-only prompt; `llm` stays. Rotation, prompt snapshots and hashes, model cards,
  digest and the register identify it.
- Specialist interface: current and maximum barrier HP, and owned abilities' cast range,
  effect radius and duration. A read-only probe during the 1.1 skills screen returned
  Dwarf barrier 0/0 and Rune cast ranges of 100 m with distinct durations and radii
  (`capability-probes/benchmark-specialist-interface`). Hidden enemies never enter
  unit_record.
- Starting fingerprints add friendly spell loadouts, initial strength, ammunition and
  barriers, and magic, supplies and tickets; a resource or loadout change flags a rematch
  even when positions match.

Recomputing the broken setup, the failed first b2 attempt and the retry gave 2 valid of 3
started trials in 0.38 job wall hours, 5.32 valid trials per hour
(`reports/bench-b3-report-preview.json`). An objective regression runs the Lua sampler
with ownership changes at unequal intervals: 25% held time where snapshot voting gives
40%. Validation: 1041 passed, 4 skipped in the main environment (the skipped Lua checks
passed separately); a fresh worktree passed 785 tests with 15 skips.

## 2026-10-14: Benchmark harness b2 (terrain, lobby modifier, Herald screens)

Read-only probes during b1 acceptance found the per-army AI modifier getter, stat previews
and terrain APIs. b2 sets and reads back the declared lobby modifier and checks it on
every army, and exposes coarse terrain and tested nearby destinations after an
unreachable move, without replacing the order; both model renderers receive them
(`obs-v1+terrain`), tactics otherwise unchanged. It records API wall latency, the returned
model and the optional provider processing header (WH3 only), keeps setup failures in
reports and separates partial traces from terminal failures. Herald development and
held-out candidates were declared before tuning. A frontend probe on `7c0abdb` set and
read AI modifiers 1.0/1.1 and the short 1200 s timer, which the Herald candidates declare.
Worktree checks: 1019 passed, 14 skipped; Ruff and Lua 5.1 parsing.

Setup failures, each with zero scored episodes:
- `bench-b2-terrain-20261014` (`587d501`): the enemy roster exceeded Default Funds. The
  operator copied its failed-setup dumps by hand. The funds probe
  (`capability-probes/benchmark-b2-funds`, 15:45:19 UTC) read only the Default/Custom
  options, verified custom 30000 and found that `funds_ultra` did not change the
  selection. The Herald candidates now pin custom 30000, and setup failures keep their menu
  dumps (54 relevant tests passed).
- `bench-b2-broken-setup-20261014` (`acb97f5`) refused the nonexistent card at recruitment
  step 37 and saved its map dump (hashes in
  `capability-probes/benchmark-b2-broken-setup/probe.json`).
- `bench-b2-acceptance-20261014` passed the corrected Herald setup (1.0, 1200 s, custom
  30000) and recorded both armies' starting stats, then stopped at the terrain diagnostic:
  the game lacks `math.huge`, so the grid was absent. The failed TerrainProbe trial is in
  the register; Luna was not played. The sampler now starts from its first corner (Lua 5.1
  regression). Full suite before the fix: 1033 passed, 1 skipped.

On `b476175` (the controller and queue exited at 17:15:50 UTC):
- Acceptance retry `bench-b2-acceptance-r2-20261014` (tool session 70797): at 5.5 s the
  engine refused f2's move to (-520, 130.6) and returned three tested nearby positions;
  TerrainProbe chose (-504, 130.6), which was accepted, and f2 moved 6.29 m in six seconds
  before the accepted halt (`capability-probes/benchmark-b2-controllers/navigation-proof.json`).
  It lost at 350 s (clock 1.0066). Luna (`llm` v15) lost at 442 s: its first call returned
  actual_model `gpt-6-luna` (an alias, not a pinned snapshot), provider processing
  7.280 s, call wall time 8.122 s, one transport attempt; 68 decisions, 14 refused orders,
  $0.03919. Its ability refusals were repeats during readiness lag (Whirlwind accepted at
  139.6 s, its retry refused at 145.3 s); the engine's "does not support this special
  ability" also appears in these temporary states (`reports/bench-b2-acceptance-r2.json`).
- Herald screens, one launch each. `bench-b2-screen-ai10-20261014` (started 16:17:05 UTC):
  hold lost at 448 s, skills won at 382 s, attack-nearest lost at 249 s; margins
  -0.412/+0.372/-0.710; invalid 0/0/5; whole job 1283.63 s, 8.41 valid trials/hour.
  `bench-b2-screen-ai11-20261014` (16:38:28): attack-nearest, hold and skills lost at
  242/266/265 s; margins -0.761/-0.658/-0.481; invalid 3/0/0; 967.02 s, 11.17 valid
  trials/hour. All rematch starts matched (`reports/bench-b2-screen-ai10.json`,
  `reports/bench-b2-screen-ai11.json`). Fresh snapshots at 5.2 s show the difficulty
  bonuses only in enemy stats, already in ValueBase: all 12 enemy entries change (about
  +10% melee attack and defence, weapon damage and charge, +8 leadership), all 12 player
  entries stay identical; at 1.1 the Marauders' attack went 28→31, defence 32→35, weapon
  damage 25→28, charge 6→7, leadership 60→68
  (`reports/bench-b2-starting-base-stat-comparison.json`). The first roster snapshots of
  the 1.0 screen and the acceptance retry, both at 5.2 s, had five unit positions more than
  1 m apart (up to 6.8 m): fresh launches vary.
- Objective probes (`probe_abilities`). `bench-b2-objectives-settlement-20261014`
  (16:54:35) lost at 244 s holding every point throughout, with nine accepted barricade
  builds and 204 supplies left; at its final snapshot eight built slots were destroyed and
  one still constructing, so build counts are accepted purchases, not surviving structures
  (`reports/bench-b2-settlement-objective-audit.json`).
  `bench-b2-objectives-domination-20261014` (17:00:42) lost at 776 s, tickets 0-1500, 514
  supplies left, 15 accepted purchases across nine types; the trace shows nine new
  friendly IDs and six old IDs restored from zero men, matching the purchases by type.
  Objective fields and register rows agree with the traces; the ownership-time
  reconstruction differs by at most the initial 300 ms sample gap
  (`reports/bench-b2-objective-audit.json`).

Ledger $3.3329. Owner steering then put specialist anchor-unit scenarios and faction
mechanics first ([benchmark.md](benchmark.md#scenario-design)): the unstarted Herald G1
plan was superseded, and cavalry/anti-large and caster-led candidates came before repeated
calibration.

## 2026-10-14: Benchmark harness b1 (paired trials, acceptance rotation)

Owner goal: complete paired benchmarks, difficulty and latency calibration and the
scenario interface fixes. b1 added recorded controller rotation and importable
controllers, strict benchmark setup checks, observation-age arms, private evaluation
totals excluding routing and shattered units, objective ownership integrated on game
ticks, reinforcement counts by type, trial failure and interruption accounting, and paired
reports with explicit denominators, uncertainty and missing pairs. Policies stayed `llm`
v15 and `commander` v3. Runbook: [benchmark-run.md](benchmark-run.md). Validation: 1030
tests passed, 1 skipped; Ruff; every mod script parses as Lua 5.1; the follow-up clock
and refusal edits passed 52 benchmark/play tests.

Acceptance `bench-b1-acceptance-20261014` on `5cad165` (started 14:54:39 UTC, frozen
development scenario `dwf-sla-taurox`): hold, Luna (`llm` v15), skills, attack_nearest and
the imported ExternalHold all ended on engine losses at 386, 824, 426, 262 and 386 s;
active margins -0.675, -0.002, -0.192, -0.594 and -0.675. All rematch start fingerprints
matched; clock ratios 0.9967 (hold) and 0.9985 (Luna). Luna cost $0.0594 (ledger
$3.2937); its 21 rejections were 9 unreachable moves, 7 routing units, 1 dead target and 4
spell refusals, and its later plan hid survivors for the defender's 60-minute timeout,
but Sigvald broke the remaining army first. The imported controller was
`/tmp/wh3-benchmark-controllers/external_controller.py` (sha256
`91410140291a601bab524e73a37755738d92d04b2e04339e965be00296957ea2`), now kept untracked at
`capability-probes/external-controllers/external_controller.py` beside the flight
diagnostic `flight_probe.py`. One instance verifies rotation and import, not ranking
confidence. Report: `reports/bench-b1-acceptance.json`.

Setup probe before b1: `runs/twwarhammer3/benchmark-probe-20261014` (`bench_probe.py`, run
from a clean worktree at `f2c8463`) built `dwf-sla-taurox` unattended. It selected and read
back the map ("Dread Crossing – Quest Battle"), pinned both factions, recruited all 24
cards by id and matched both rosters. Lobby read-backs: land_normal, 3600 s,
ai_level_very_hard, funds_large. Battle read-backs: IsDefender true, WillWinOnTimeout
true, UnitSize 0.75, BalanceOfPowerPercent 0.51 at 61 s. `hold` lost at 298 s (0.41 vs
0.65 men alive), and all five protected units were routing at the end. Its 965 empty
requests applied after 300 ms (954) or 600 ms (11). The protected units met melee 8.4,
13.2, 24.0, 46.2 and 47.4 s after an enemy came within 100 m. On the first rematch,
`attack_nearest` started from the same positions; the owner stopped it at 262 s.

## 2026-10-14: Battle types, llm v15 and commander v3 (overnight)

Owner goal (2026-10-14, away overnight): one minimal test scenario for each battle type
beyond the land battle (conquest, domination, free-for-all, ambush, chokepoint,
subterranean, minor settlement, siege, survival), as vertical slices toward the
benchmark. Reference: [battle-types.md](battle-types.md); engine facts in
[integration.md](integration.md#battle-types-probed-2026-10-14).

What changed (`0cf3646` to `aa5a62b` and after):
- Setup: `battle_type`, `attacker`, several or no enemy sides, reinforcing armies;
  lobby steps guarded by `when` expressions; the engine's type and the player's role
  checked at the first observation; a start click that starts nothing fails at once.
- State: the observation's `mode` (type, role, timeout winner, the game's objective
  text, capture points, tickets, gates, supplies, building slots, reinforcement pool and
  spawn zones); units of every enemy alliance and units that enter mid-battle.
- Orders: `build` (towers and barricades) and `reinforce` (pool units), both paid with
  supplies; `probe_abilities` uses both.
- Prompts (llm v15, commander v3): the Battle section, the two orders, and the
  objective rule, including the owner's siege notes (keep the victory points held,
  spend supplies).
- Three review workflows, each with reviewers per dimension and an adversarial verifier
  per finding. The first (30 findings, 24 confirmed, 10 distinct) found a validation
  crash, slot usability that always read false, shifting reinforcement ids and smaller
  defects (fixed in `c7287f4`). The second found a running mean that froze after about a
  thousand observations and a cost mismatch in the pool (`088a175`). The third found
  zone usability judged by one unit, double purchases of one pool entry and doc errors
  (`8f9d832`).
- Engine findings during the battles fixed the same night: purchased units never got
  ids, because the scan only ran with regular observations (`d62a751`); a reply invalid
  three times ended the battle (`9f08da8`); spawn zones refuse purchases (`89f3f8c`).
  A bridges field for the chokepoint (`2a0a1cd`) was removed again (`fcba267`): that
  map has no buildings, its crossings are terrain.
- Also: random draws per battle type (`9b0209f`), measures per episode (`ea646a3`,
  `7a40889`, `01e3abb`: victory points and the key building held, supplies left,
  tickets, builds and purchases) and three register columns (`ea66fef`).

Results, one battle each (per-job tables below):

| Scenario | `attack_nearest` | `probe_abilities` | Luna `llm` v15 | Luna `commander` v3 |
|---|---|---|---|---|
| conquest | won 510 s | | won 197 s | lost 403 s |
| domination | lost 742 s | lost 709 s | lost 1042 s (tickets 1156-1500) | lost 814 s |
| free-for-all | won 942 s | | policy failure; replay won 560 s | lost 909 s |
| ambush | won 173 s | | lost 699 s | truncated |
| chokepoint | won 369 s | | won 421 s | won 878 s |
| subterranean | lost 546 s | | won 391 s | won 503 s |
| minor settlement | lost 302 s | won 390 s | won 242 s | won 300 s |
| siege | won 510 s | won 430 s | won 368 s | won 450 s |
| survival | lost 198 s | lost 249 s | lost 292 s | lost 325 s |

One battle per cell separates nothing, but it shows each slice working. A siege with
the player attacking (`siege-attack-kho5-dwf5`) set up correctly but could not breach:
the gate stayed at 100% and the units idled outside the walls until the job was stopped
at 730 s; attacking needs gate and wall orders and siege equipment. LLM v15 cost
$0.32 for its ten battles; the commander $0.48.

"Strength left" is the men alive out of the initial men of every unit registered (at the
start, or when it entered), ours / the enemy's (every enemy army in the free-for-all).
Jobs before `e8eb0b6` and `d62a751` missed units that entered later. "Rejected" counts
the engine's rejections and orders refused by validation.

Smoke battles, `attack_nearest` (every unit at its nearest visible enemy, objectives ignored):

| Scenario | Job | Source | Result | Battle | Strength left | Rejected |
|---|---|---|---|---|---|---|
| conquest | `smoke-conquest-kho5-dwf5-attack_nearest-20261014-0245` | `aa5a62b` | won | 510 s | 29/197 / 78/235 | 0 |
| domination | `smoke-domination-kho5-dwf5-attack_nearest-20261014-0159` | `8b84632` | lost | 742 s | 0/197 / 207/235 | 0 |
| free-for-all | `smoke-ffa-kho5-dwf5-emp5-kho5-attack_nearest-20261014-0114` | `0cf3646` | won | 942 s | 103/197 / 36/669 | 3 |
| ambush | `smoke-ambush-kho5-dwf5-attack_nearest-20261014-0221` | `e8eb0b6` | won | 173 s | 162/197 / 117/235 | 0 |
| chokepoint | `smoke-chokepoint-kho5-dwf5-attack_nearest-20261014-0226` | `c7287f4` | won | 369 s | 72/197 / 55/235 | 5 |
| subterranean | `smoke-underground-kho5-dwf5-attack_nearest-20261014-0234` | `c7287f4` | lost | 546 s | 15/197 / 110/235 | 0 |
| minor settlement | `smoke-settlement-kho5-dwf5-attack_nearest-20261014-0214` | `e8eb0b6` | lost | 302 s | 43/197 / 121/235 | 1 |
| siege | `smoke-siege-kho5-dwf5-attack_nearest-20261014-0132` | `2dac47b` | won | 510 s | 117/197 / 82/235 | 0 |
| survival | `smoke-survival-kho5-attack_nearest-20261014-0154` | `1a5ec0c` | lost | 198 s | 38/197 / 434/448 | 1 |

- Before these, `probe-conquest-attack-20261014` (`12078dc`) played a conquest battle set
  up by hand with menu steps and was won at 331 s.
- The siege smoke had one tower built by hand mid-battle (the build-command probe), and
  the domination smoke one unit bought by hand (the purchase probe).
- The first survival job (`smoke-survival-kho5-attack_nearest-20261014-0143`) never
  started, because the lobby wants a reinforcing army; it was killed after 10 minutes.
- The free-for-all job predates the recorded `mode`; its trace shows `land_normal`.

`probe_abilities` (the `skills` executor plus abilities, builds and reinforcements) on the
four types with supplies:

| Scenario | Job | Source | Result | Battle | Strength left | Orders |
|---|---|---|---|---|---|---|
| siege | `smoke-siege-kho5-dwf5-probe_abilities-20261014-0255` | `aa5a62b` | won | 430 s | 133/197 / 109/235 | 8 towers built at 5.5 s (6000 supplies to 2000) |
| minor settlement | `smoke-settlement-kho5-dwf5-probe_abilities-20261014-0305` | `aa5a62b` | won | 390 s | 17/197 / 43/235 | 12 barricades and towers |
| domination | `smoke-domination-kho5-dwf5-probe_abilities-20261014-0313` | `aa5a62b` | lost | 709 s | 59/197 / 214/235 | 12 units bought, 7 refused at the zone; the bought units never got ids (fixed in `d62a751`) |
| survival | `smoke-survival-kho5-probe_abilities-20261014-0327` | `d62a751` | lost | 249 s | 227/611 / 1323/1405 | 6 units bought, each registered about 1 s later; 13 wave units registered as they came |

The probe won the minor settlement, which `attack_nearest` had lost, building as it went.

Luna `llm` v15 (`gpt-6-luna`, low; the source moved during the chain, each row names its revision):

| Scenario | Job | Source | Result | Battle | Strength left | Rejected | Objectives | Cost |
|---|---|---|---|---|---|---|---|---|
| conquest | `llm-luna-v15-conquest-kho5-dwf5-20261014-0453` | `89f3f8c` | won | 197 s | 162/197 / 102/235 | 4 | points held 12% | $0.014 |
| domination | `llm-luna-v15-domination-kho5-dwf5-20261014-0427` | `7a40889` | lost | 1042 s | 416/617 / 648/698 | 56 | points held 38%, supplies left 234, bought 21; tickets 1156 to the enemy's 1500 | $0.084 |
| free-for-all | `llm-luna-v15-ffa-kho5-dwf5-emp5-kho5-20261014-0335` | `ea646a3` | policy failure | | | 1 | | $0.014 |
| free-for-all | `llm-luna-v15-ffa-kho5-dwf5-emp5-kho5-20261014-0458` | `89f3f8c` | won | 560 s | 54/197 / 26/669 | 13 | | $0.039 |
| ambush | `llm-luna-v15-ambush-kho5-dwf5-20261014-0341` | `ea66fef` | lost | 699 s | 0/197 / 60/235 | 21 | | $0.042 |
| chokepoint | `llm-luna-v15-chokepoint-kho5-dwf5-20261014-0355` | `9f08da8` | won | 421 s | 75/197 / 24/235 | 28 | | $0.028 |
| subterranean | `llm-luna-v15-underground-kho5-dwf5-20261014-0404` | `088a175` | won | 391 s | 158/197 / 37/235 | 4 | | $0.026 |
| minor settlement | `llm-luna-v15-settlement-kho5-dwf5-20261014-0421` | `5cf042e` | won | 242 s | 118/197 / 94/235 | 5 | points held 100%, supplies left 796, built 5 | $0.020 |
| siege | `llm-luna-v15-siege-kho5-dwf5-20261014-0412` | `2a0a1cd` | won | 368 s | 120/197 / 69/235 | 8 | points held 100%, supplies left 2258, built 8 | $0.028 |
| survival | `llm-luna-v15-survival-kho5-20261014-0446` | `7a40889` | lost | 292 s | 450/737 / 1449/1555 | 10 | points held 20%, supplies left 2833, bought 7 | $0.024 |

- It read the Battle section and took and held capture points. In the siege it built 6
  towers in the first 30 s (6000 supplies to about 200), the last two at 74 s and 123 s;
  in the minor settlement 5 builds over the first 160 s. It called in reinforcements in
  domination (21) and survival (7) and commanded each new unit once it appeared.
- The owner's siege concern did not recur with the model: siege and minor settlement held
  every victory point throughout and were won. Survival ended with 2833 supplies unspent.
- The first free-for-all was a policy failure: the model ordered its lord's ability while
  it recharged, in three replies running, and the third invalid reply ended the battle.
  Since `9f08da8` a reply's valid orders are kept when the retries run out.
- Rejected orders: moves to unreachable points (17 each in ambush and chokepoint, across
  the river or off the forest path); purchases at zones that refuse them (34 in
  domination; zones marked since `89f3f8c` and `8f9d832`); orders to routing units; a few
  self abilities refused with "does not support this special ability".
- The first conquest job (`llm-luna-v15-conquest-kho5-dwf5-20261014-0333`) stopped before
  its battle: a merge during its lobby setup changed the source. The replay won by
  breaking the enemy, not on tickets.

Luna `commander` v3 (build and reinforce in its one-shot list):

| Scenario | Job | Source | Result | Battle | Strength left | Rejected | Objectives | Cost |
|---|---|---|---|---|---|---|---|---|
| conquest | `commander-luna-v3-conquest-kho5-dwf5-20261014-0611` | `01e3abb` | lost | 403 s | 51/197 / 100/235 | 0 | points held 38% | $0.022 |
| domination | `commander-luna-v3-domination-kho5-dwf5-20261014-0636` | `838044b` | lost | 814 s | 394/618 / 591/698 | 7 | points held 8%, supplies left 355, bought 15 | $0.058 |
| free-for-all | `commander-luna-v3-ffa-kho5-dwf5-emp5-kho5-20261014-0659` | `838044b` | lost | 909 s | 2/197 / 35/669 | 4 | | $0.052 |
| ambush | `commander-luna-v3-ambush-kho5-dwf5-20261014-0717` | `838044b` | truncated | | | 58 | | $0.183 |
| chokepoint | `commander-luna-v3-chokepoint-kho5-dwf5-20261014-0803` | `838044b` | won | 878 s | 1/197 / 73/235 | 53 | | $0.054 |
| subterranean | `commander-luna-v3-underground-kho5-dwf5-20261014-0820` | `fcba267` | won | 503 s | 34/197 / 102/235 | 17 | | $0.034 |
| minor settlement | `commander-luna-v3-settlement-kho5-dwf5-20261014-0629` | `838044b` | won | 300 s | 60/197 / 66/235 | 6 | points held 100%, key building 100%, supplies left 1060, built 5 | $0.022 |
| siege | `commander-luna-v3-siege-kho5-dwf5-20261014-0620` | `838044b` | won | 450 s | 171/197 / 19/235 | 4 | points held 100%, key building 100%, supplies left 3296, built 8 | $0.026 |
| survival | `commander-luna-v3-survival-kho5-20261014-0652` | `838044b` | lost | 325 s | 113/461 / 1515/1614 | 9 | points held 14%, supplies left 5980, bought 4 | $0.026 |

- It built 8 in the siege and 5 in the minor settlement, held the key building throughout
  both, and bought 15 units in domination and 4 in survival. Domination was lost with the
  points held 8% of the time.
- Almost every rejected order was a move to an unreachable point: 53 at the chokepoint,
  57 in the ambush, 17 underground.
- The ambush ended in a standoff, truncated by the job's 40-minute episode cap
  (`--episode-timeout 2400`): its last unit, the horsemen, stood hidden and idle against
  one enemy crossbow unit; as defender it would have won when the 60-minute battle limit
  ran out. It cost $0.18 for that reason. Types where time decides need an episode
  timeout above the battle's limit.

Siege attack: `siege-attack-kho5-dwf5` (added in `42b0c2f`), played by `probe_abilities`
in `smoke-siege-attack-kho5-dwf5-probe_abilities-20261014-0830` on `fcba267`, stopped by
hand at 730 s; the gate untouched at 100%, defenders on the walls holding every point and
all 1000 tickets, our units down to 63 of 197 men idle outside.

First four random battle-type draws, each played once by `skills` (which neither builds
nor buys; jobs `smoke-random-<type>-skills-20261014-*`), source `89f3f8c` for the siege,
`01e3abb` for the others:

| Draw | Seed | Map | Armies (units) | Result | Battle | Strength left | Objectives |
|---|---|---|---|---|---|---|---|
| `random-siege` | 632937498 | Gaean Vale (High Elves) | Chaos Dwarfs (15) defending against Dark Elves (20) | lost | 377 s | 207/734 / 400/858 | points held 100%, supplies left 9342 |
| `random-ffa` | 1161544204 | Moonlight Ridge | Daemons (10) against Lizardmen, Skaven and Slaanesh (42 in all) | lost | 1648 s | 275/403 / 46/2422 | |
| `random-survival` | 2113589463 | Endless Chaos Dwarfs | Ogre Kingdoms (14) against waves | lost | 514 s | 27/144 / 2340/3389 | points held 48%, supplies left 15449 |
| `random-domination` | 2063442117 | Toothgrass Hill | Wood Elves (6) against Lizardmen (11) | lost | 639 s | 6/327 / 1134/1262 | points held 0%, lost on tickets (0 to 1500), supplies left 10010 |

Each set up, played and ended on an engine result with no infrastructure failure. The
siege was lost with every victory point held (the army broke first). In the free-for-all
the last alliance standing was not ours although 275 of our men were alive (routing,
presumably). The spawn-zone `usable` field read true for all five domination zones.

Owner notes (2026-10-14): watching the siege smoke played by `attack_nearest`, the owner
saw the controller ignore the goal: every unit fought at the gate while enemy infantry
walked to the undefended key building, and the battle ended with more than 9,000
supplies unspent. The engine still scored it won (the enemy army broke). Both became
benchmark measures (victory points held over time, supplies left), both prompts now say
so, and the controllers can build and reinforce.

## 2026-10-13: Random-battle comparison, partial (into 2026-10-14)

Three seeds of the planned six, each played once by every controller (`9bfee82`, AI very
hard, autogenerated armies), then stopped at the owner's word to finish the engineering
first. All nine battles were lost:

| Seed: draw | `skills` | Luna `commander` v2 | Luna `llm` v14 |
|---|---|---|---|
| 2028855463: Dark Elves vs Nurgle | 434 s, 0.06 vs 0.34 | 299 s, 0.15 vs 0.56 | 618 s, 0.00 vs 0.31 |
| 1202868312: Daemons of Chaos vs Nurgle | 259 s, 0.00 vs 0.67 | 293 s, 0.00 vs 0.75 | 280 s, 0.00 vs 0.54 |
| 322117462: Dwarfs vs Slaanesh | 382 s, 0.31 vs 0.30 | 231 s, 0.43 vs 0.58 | 317 s, 0.46 vs 0.60 |

Cells show battle length and strength left (ours vs the enemy's). Costs: commander
$0.018-0.025 a battle, llm $0.025-0.040. The direct controller decided every 6-7 s
(49-89 decisions a battle).

Three paired draws separate nothing yet, and these draws at very hard (with the AI's
1.1 stats modifier) are hard for every controller. The remaining seeds are 264482191
(Ogre Kingdoms vs Slaanesh), 1355466036 (Daemons vs Greenskins) and 238913231 (Cathay
mirror). The chain script ran `play --scenario random --seed N --episodes 1` per
controller.

## 2026-10-13: Ability readiness and army abilities, llm v14 and commander v2 (`9bfee82`)

The script API has no ability cooldown getter, but the UI's context system has one
([integration.md](integration.md#ability-state-through-the-ui-context-system-probed-2026-10-13)).
Each friendly ability now carries:
- target type, magic cost and cooldown;
- `ready`, `active`, seconds of recharge left and uses left.

Army abilities, such as Khorne's three kill-unlocks, carry target, radius, unlock cost,
`unlocked` and `ready`. An `ability` order with unit `"army"` casts one. Validation
refuses an ability that is not ready, and both prompts describe the new state.

`watch` follows a job beside the game, and `play --show` puts each model reply in the
advisor window.

Engine check, `probe-abilities-random-s4` (`--policy probe_abilities`, seed 4: Khorne
(Arbaal) vs Dark Elves, autogenerated):
- The lord's and the hero's self abilities (Fight or Die, Potion of Toughness, Deadly
  Onslaught) were cast when ready and accepted. Afterwards the state showed them active
  and not ready, and the potion with 0 uses left.
- The army abilities showed locked, with costs 100/200/300.
- The battle was lost at 228 s with 31 points, so no army ability unlocked. The probe
  now runs on the `skills` executor (`46f94d0`), which earned 113 points on `kho5-dwf5`.

Second check, `probe-abilities-random-s245-20261014` (Khorne vs Skaven, seed 245):
- Horn of Khorne unlocked at 109 points and was cast at our largest unit's position at
  260 s. The engine accepted it, and its HUD timer counted 31 s active, then 90 s of
  recharge. The state now shows those phases (`739ce9c`).
- The lord's and hero's casts were accepted as before. The battle was lost at 337 s.

## 2026-10-13: Controller comparison on `kho5-dwf5`, stopped for random battles (late)

Six episodes each on the fixed Khorne vs Dwarfs battle, unpaused at 1x, AI very hard:

| Job | Source | Won | Mean battle s | Own left | Enemy left | Cost |
|---|---|---|---|---|---|---|
| `skills-v1.2-kho` | `cb12f6a` | 5/6 | 461 | 0.10 | 0.17 | $0 |
| `commander-luna-v1.2-kho` | `df390c1` | 5/6 | 329 | 0.27 | 0.33 | $0.12 |
| `llm-luna-v13-kho` (1 episode) | `df390c1` | 1/1 | 244 | 0.66 | 0.28 | $0.02 |

(Commander v1.2 is the v1 commander over executor v1.2; there was no v1.1 commander.)

- The scenario does not separate controllers: `skills`, the Luna commander and the v6
  direct controller all won 5 of 6 on it.
- Three `skills` episodes were identical (531 s, 0.10 vs 0.09 left). With a deterministic
  controller, a rematch replays the same battle, so its episodes are not independent
  samples.
- The commander's 34 engine rejections in 6 battles: 26 refused lord ability casts and 8
  unreachable moves.
- The owner asked why we were still playing small fixed battles, so the `llm` job was
  stopped after its first episode (won). The comparison moved to random draws: six
  seeds, each played once by every controller, so the draws are paired.

## 2026-10-13: Shooter re-send fix, executor v1.2 (`55ab6b3`)

Diagnosis from the Skaven trace: the four shooters spent most of their attack time moving,
with no target shown by the engine and no shots (779 such observations against 131
with shots). Many of those stretches were chases of fast chariots (Chaos Chariot,
Warwolves Chariot) kept in range for 15-42 s without a shot. The lapse rule read "no
target" as a dropped attack and re-sent it every 2 s. Two changes:
- an attack is not lapsed while the unit moves with no target and no move destination
  (closing in, finding a line of fire or evading as a skirmisher); it lapses when the
  unit is idle, shows another target, or stands without one. Replayed over the logged
  orders, this suppresses 118 of the 195 shooter re-sends;
- a shooter that fires no shot (ammunition unchanged) at a target in range for 15 s
  (30 s for artillery, whose reloads were up to about 20 s) skips that target for 30 s
  and picks another; its phase says so.

Validation, `skills-v1.2-random-a` (seed 255179936, same draw and the same
autogenerated armies): no shooter repeated an identical order more than 3 times in a row,
against stretches of up to 21 before. Orders per shooter fell from 69-102 in 415 s to
47-60 in 346 s; what remains is target switching as enemies enter and leave range.
Ammunition spent changed both ways (Night Runners 387 -> 162, Globadiers 96 -> 132,
Gutter Runners 1080 -> 880, Death Globes 146 -> 99), so one battle says nothing about
firing volume. Lost at 346 s with 0.40 of our men left against 0.70 (before: 0.35 vs
0.25 at 415 s). The draw is hard: fast Norscan cavalry and chariots against short-range
skirmishers.

## 2026-10-13: Random battles

Owner request: use the custom battle screen's Autogenerate army on random factions, and
randomize the map too. A UI probe (`runs/twwarhammer3/probe-random-army-20261013/`,
[integration.md](integration.md#frontend-automation)) found:
- the button `clear_autogen_parent/button_autogen`;
- the classic battle types' 380 maps;
- the faction list of each of 23 owned races (307 factions);
- the profile's fixed settings, including AI difficulty very hard.

`--scenario random [--seed N]` draws the map and both races from
`configs/twwarhammer3/custom_battle.json` and autogenerates both armies. The battle type
stays classic: sieges, capture points and survival need interface work first.

The first draw, `commander-luna-v1-random-s2-smoke`, was seed 2 on
`land_of_the_dead_01_04`. Dark Elves (Blessed Dread) had 13 units: a Dreadlord,
Corsairs, Executioners, Black Guard, Dark Riders, Cold One Knights, a Cold One chariot,
three Harpies, a Feral Manticore and a Reaper Bolt Thrower. Nurgle (Pallid Nurslings)
also had 13. The commander won at 407 s with 0.40 of its men left against 0.23, from 62
plans: mean plan age 6.5 s, think time 6.2 s, about 4,800 input tokens per call, $0.03.
All 9 rejections were refused lord ability casts. The trace was 5.5 MB.

A `skills` job on the same seed was stopped at the owner's word: a repeated draw shows
nothing new, and a job is one matchup. The draw also picked a faction for each side
(`5a2fc8d`), but the owner noted that a faction within a race only changes colours. The
next commit draws races only, a fresh seed per job. The mod reports the Harpies and the
Feral Manticore as infantry: its class mapping checks `can_fly` only for monsters.

Two fresh draws followed, each lost:

| Job | Draw | Outcome | Battle s | Own left | Enemy left | Notes |
|---|---|---|---|---|---|---|
| `skills-v1.1-random-a` (`900000a`) | Skaven (20 units) vs Norsca (13), `wh3_nur_wastes_01_04`, seed 255179936 | lost | 415 | 0.35 | 0.25 | 0 rejections |
| `commander-luna-v1-random-b` (`29c9325`) | Vampire Counts vs Lizardmen, `wh3_tze_wastes_02_01`, seed 369290826 | lost | 404 | 0.00 | 0.31 | 70 plans, plan age 5.6 s, $0.03 |

In the commander battle, 19 of 21 rejections were refused lord ability casts. A defect
to fix before the comparison: in the skills battle four Skaven missile units (Night
Runners, Gutter Runners, Globadiers, Death Globe Bombardiers) re-sent the same ranged
attack every 2 s for long stretches, 69-102 orders each. The engine never showed the
ordered target, probably for lack of line of sight, so the redirected-attack lapse rule
from `0f8eb39` fired on its 2-second repeat. A shooter should give up on a target the
engine keeps refusing and pick another.

## 2026-10-13: Skills and commander v1

Owner request: build the simplest design from a research summary (ChatGPT 6 Astra Pro,
2026-10-13), an asynchronous API-model commander over persistent scripted skills, and
document the other designs for later comparison
([controllers.md](controllers.md)). Code:
- `d2bf74a`: the skills executor (`--policy skills`), the commander
  (`--policy commander`), a `policy` column in the results register (rebuilt from
  `runs/`, identical except that column and blank model cells on scripted rows) and
  trace thinning for fast policies.
- `0f8eb39`: the fixes below.
- `5a2fc8d`: random battles.

The model's prompt is `configs/twwarhammer3/commander_prompt.md`; the direct controller
keeps `system_prompt.md`.

Smoke battles, one episode each on `kho5-dwf5`, unpaused at 1x, AI difficulty very hard
(found by the probe below; every earlier battle ran at it too):

| Job | Source | Outcome | Battle s | Own left | Enemy left | Plans | Mean plan age s | Cost |
|---|---|---|---|---|---|---|---|---|
| `skills-v1-kho-smoke` | `d2bf74a` | lost | 302 | 0.34 | 0.57 | | | $0 |
| `commander-luna-v1-kho-smoke` | `0f8eb39` | won | 355 | 0.53 | 0.28 | 53 | 6.5 | $0.02 |
| `commander-sol-v1-kho-smoke` (`gpt-6.1-sol`) | `0f8eb39` | won | 255 | 0.75 | 0.44 | 41 | 6.0 | $0.18 |
| `commander-astra-v1-kho-smoke` | `0f8eb39` | won | 309 | 0.64 | 0.26 | 59 | 5.1 | $1.17 |

All jobs ran at low effort. Mean order delay was 0.3 s (maximum 0.6 s) in every job,
against 4-11 s for the direct controller. The executor ran about 3 decisions a second,
and traces stayed at 1.6-2.5 MB per battle after thinning.

These battles show that the controller works, not that it is stronger: the direct
controller won 5 of 6 on this scenario at v6 and `attack_nearest` 3 of 3. The comparison
needs six or more episodes per controller
([controllers.md](controllers.md#comparing-controllers)).

- **skills v1** found a defect. The observation published with an acknowledgement still
  shows the previous target, and shoot preferred the observed target. After the enemy
  lord's melee flag flickered at 89 s, the Skullcannon alternated between two targets
  on every tick from 89 s until 185 s: 319 attack orders and no shots. `0f8eb39` makes every
  skill prefer the executor's own last target (regression test). A six-agent review
  (three reviewers, each with a verifier) confirmed eight more defects, all fixed in
  `0f8eb39`:
  - a charge whose named target is out of sight now acts as with no target;
  - without a post, charge halts the previous skill's order;
  - only an unreachable move drops its point;
  - an attack the game redirected counts as lapsed;
  - `describe_orders` no longer crashes on an ability with x but no z;
  - the prompt no longer annotates orders sent in the same tick;
  - the trace keeps the observation a failing decision saw.
- **Commander.** The first Luna plan arrived 7.2 s after its state. Meanwhile the
  default skills had the infantry engaging, the Skullcannon firing and the lord and
  horsemen waiting for melee. No assignment was ever dropped. Every engine rejection
  except two was an ability cast the engine refused ("does not support this special
  ability"): 7 for Luna, which repeated `deadly_onslaught`, and 2 each for Sol and
  Astra. Luna's other 2 were unreachable horsemen moves. The model still cannot tell ability cooldowns.
  The owner saw a Khorne army ability become available near the end of a battle and go
  unused. Army abilities are missing from the interface (state and orders) for every
  controller; this is a harness gap to fix, recorded in integration.md.
- **Latency and cost.** Sol and Astra at low effort spent only 25 and 10 reasoning
  tokens per call, against Luna's 341, so they were no slower: think time was 6.4 s
  for Luna, 5.8 s for Sol and 4.8 s for Astra. Astra's first call took 12.5 s. Total WH3
  spend after these jobs: $2.08 of the $25 ledger.

Every commander smoke call sent about 3,500 input tokens, about 2,100 of them cached.
Cost per call: about $0.0004 for Luna, $0.004 for Sol (`gpt-6.1-sol`) and $0.019 for
Astra, at the 2026-10-12 standard-tier prices per million input/cached/output tokens of
0.10/0.01/0.50, 2.00/0.10/10.00 and 10.00/1.00/50.00.

## 2026-10-13: Unpaused 1x battles only

The first diagnostic `play-smoke` used `--pause`; the owner rejected this and requires
all battles, including probes, to run unpaused at normal 1x. It remains labelled as a
paused diagnostic in local evidence and contributes no policy result. Code `1c56ec2`
removes automatic observation/order pauses from the Lua mod, sets the battle speed to
1x at deployment, and removes the CLI's pause/speed overrides. Python rejects paused
or altered-speed configurations, session writes, attached sessions and incompatible
live observations before a policy decision. The prompt and repository instructions
now explicitly require unpaused 1x. Historical results retain their recorded modes.

Validation: 95 WH3 tests and repository-wide Ruff pass, including rejection of stale
paused sessions and speed overrides. The replacement engine smoke is
`runs/twwarhammer3/skip-intro-20261013/play-smoke-realtime/`.
It reached a deployed five-versus-five battle, made 78 decisions and acknowledged
77 batches with zero invalid orders. Every decision observation reports speed 1 and
`awaiting_orders=false`; measured battle time advanced 23.4 s over 23.401 s of wall time.
The run ended at its 50-second diagnostic timeout, with no gameplay outcome measured
and no row added to the policy results register. Repeat installation preserved the
startup pack/preference bytes and mtimes. All probes are stopped, session files cleared,
and the final doctor reports ready with the startup skip installed.

## 2026-10-13: Automatic startup video skipping

Code `2793933`. `launch` and `play` install a separate auto-loaded PFH5 movie pack in
the game's `data/` directory and set `fe_game_intro_video_enabled false` in the existing
profile. The change persists for ordinary Steam launches. The pack replaces the five
startup movies and all 13 localized warning movies with twpatcher's 595-byte blank clip
(MIT attribution in `src/twwarhammer3/assets/LICENSE.twpatcher`). It leaves the main
cinematic intact for the viewer. Preparation refuses to change game files while WH3
is running, preserves all other preference bytes, and leaves matching startup files
untouched. Doctor reports the effective setting and actual/expected pack hashes;
deployment evidence includes them. No new CLI options or desktop input.

Before the skip, the frontend script loaded about 25 s after launch, but its real-time
callbacks did not run until the intro movies ended, about 2 minutes later.

Validation: 83 WH3 tests and repository-wide Ruff pass. Engine evidence is under
`runs/twwarhammer3/skip-intro-20261013/`. The baseline reached the visible Battle button
at 149.014 s; the patched launch at 17.735 s, saving 131.279 s in one comparison.
Without the project mod list, the menu is visible in the capture completed at 20.774 s,
and the game's Lua log shows no project scripts. These were direct executable launches
with Steam running; the Steam launcher UI was not exercised. The static loading splash
remains. All 18 overridden paths exist in the installed engine's `movies.pack`; the
installed 11,646-byte startup pack has SHA256
`87c3964bdbbb4d07feef70e7befcbb919753c948bff47182d78a42caa24c03f1`.
The live preference comparison changed only `true` to `false`, and attempting preparation
during the patched probe was refused before writing.

## 2026-10-13: v13, continuous decisions and expanded battle controls

Owner-requested controller change. Implementation starts at `863d10b`; final code
`6db8111`. Tactical rules remain based on v10, with command instructions updated.
The default post-application wait is 0 ms (was 5000); positive `--interval-ms` remains
an explicit pacing option. Terminal observations now record a matching acknowledgement
before ending the episode, and decision observations record `since_previous_applied_ms`.

The policy can select auto/melee/ranged attacks, queue moves and a final attack, choose
formation width, toggle supported fire-at-will/skirmish/guard/spacing/formed-attack
behaviors, and issue owned active abilities at self, friendly/visible enemy units or a
ground point. Python validation and Lua dispatch enforce the targets/capabilities.
Acknowledgements identify each order by index and distinguish queued from issued.
A rejected queued successor does not erase the preceding successful move from memory.
The prompt shows supported toggles, width, submitted queues, active ability keys,
permission and last issue times, plus the player's magic pool/reserve. Cooldowns and
uses remaining are explicitly unknown: `can_perform_special_ability` stays true after
casting. An ability/queue acknowledgement is not a completion report.

Validation: 71 WH3 tests pass; `ruff check src/twwarhammer3 tests/twwarhammer3` passes.
Real engine evidence is in `runs/twwarhammer3/capability-probes/` (ignored), with source
fingerprints, engine/pack pins, script copies, observations, requests, acknowledgements
and checks. `khorne-dwarfs-r3` verified toggles, a 20 m width, queued waypoints, ranged
fire followed by melee with 453 ammunition left, and rejection of successors to an
unreachable move. Foe Seeker raised the lord's walk/run speeds from 1.9/4.8 to 2.4/6.0.
Its 60-second Luna smoke made seven decisions, six acknowledged (zero invalid); every
next decision used the acknowledgement snapshot with 0 ms added gap. Mean think time
9.399 s, wall roundtrip 9.744 s; $0.003063. The final call ran across the episode timeout.

`wizard-r3` verified friendly Glittering Robe, enemy Plague of Rust and ground Searing
Doom orders with magic-pool decreases of 5, 4 and 6 respectively; a unit trying to use
another unit's ability was rejected. Earlier probes found the undocumented requirement
to pass a unit even for a self ability; the dispatcher now passes the caster. Spacing
and formed-attack toggles were unavailable on the tested armies and correctly omitted.
These are diagnostic battles with scripted prefixes, not comparable policy outcomes,
so they add no rows to the results register. See integration.md for the limits.

## 2026-10-13: Early findings (milestones, first night, mirror battles)

Moved from the track README on 2026-10-15. Milestones of the first day:

| Milestone | State | Evidence |
|---|---|---|
| 1 Mod loads | done | `runs/twwarhammer3/launch-m1/` |
| 1b Unattended custom battle | done | menu steps recruit both armies by double-click and start the battle; `runs/twwarhammer3/battle/*/menu.log` |
| 2 Roster readable | done | 5 v 5 units with positions, strength, fatigue, flags, targets in every observation |
| 3 Orders apply | done | attack, move (with facing) and halt through one unitcontroller per unit; acknowledgements carry the applied battle time |
| 4 Result | done | "lost" and "won" from the engine at VictoryCountdown, with both armies' true strength for evaluation |
| 5 Restart | done | rematch button and confirmation; 40 episodes in 14 jobs, none an infrastructure failure |
| 6 Scripted baselines | done | `attack_nearest`: 3 wins of 3 at about 345 s |
| 7 First LLM battles | done | v1: 1 win of 3 |
| 8 Autoresearch loop | stopped | v2 0/3, v3 3/5, v4 1/3 (1/3 paused), v5 4/6, v6 5/6, v7 2/6 (reverted); v8-v11 on mirror battles, no mirror win yet with guns |
| 9 Several scenarios | done | `configs/twwarhammer3/scenarios.json`: each side's race picked in the selector's popup; Khorne, Dwarf and Empire mirrors |

What the first night showed:
- The model can command a real-time battle through the mod: about one decision per 10 s
  of battle time, orders applied about 5 s after the state it saw, no invalid replies,
  about $0.01 per battle.
- The fixed script that sends every unit at its nearest enemy, walking, wins this battle
  every time. The model's early losses came from what it added: passivity (v1), retreats
  out of melee (v2), running everywhere and arriving tired, pairing its units off one to
  one, and above all leaving its lord to duel the enemy lord alone, or parking him while
  the enemy lord was nearly dead.
- Latency is not the gap: pausing the battle while the model thinks (orders applied 0.6 s
  after the state instead of 5.5 s) gave the same 1 of 3 for v4.
- The state must say what the game did with an order: the game retargets units on its
  own, and showing its choice as the model's order made the model believe plans were
  running that were not (v6 fixed this; 5 wins of 6).
- Still weak in every version: the Skullcannon and the missile horsemen. An attack order
  only makes a unit with ammunition shoot, and their fire killed almost nothing.

What the mirror battles showed (same army on both sides of the same map, player starting
north; 9 to 12 battles per mirror; wins and mean true strength left, ours/enemy, from
`python -m twwarhammer3 stats`):

| Version | Empire (guns, cannon, knights) | Dwarfs (crossbows, catapult) | Khorne (melee) |
|---|---|---|---|
| attack_nearest | 0/2, 26/82% | | |
| v6 | 0/3, 21/69% | 0/3, 25/53% | 2/3, 34/25%; replicate 0/3, 38/64% |
| v8 guns | 0/3, 31/70% | 0/2, 30/76% | |
| v9 melee | | 0/3, 35/65% | 1/3, 26/47% |
| v10 shooters | 0/3, 37/57% | 0/3, 42/68% | 0/3, 19/58% |
| v11 lords (reverted) | 0/3, 34/76% | | 0/3, 26/61% |
| v12 v6 + v10 fire (reverted) | | | 0/3, 16/55% |

- With guns, crossbows or artillery on both sides, Luna lost every battle (0 of 11 in the
  Empire mirror, 0 of 11 in the Dwarf mirror), and so did `attack_nearest` (Empire, 0 of
  2): the AI's missile units and artillery shot our units while they fought, and its
  missile infantry ended untouched (66-67 of 68 handgunners, 52-58 of 60 quarrellers).
- The profile's AI stats modifier was 1.1, so the AI's units are probably about 10%
  stronger and a mirror is not an even fight. The owner later authorized testing 1.0 and
  1.1 during benchmark calibration.
- Harness gaps found: enemy units' targets never reached the state (llm.py rendered a
  field the mod never sent), no record of what a fire order killed, an attack order
  replaces a move (a shooter walks straight at a target out of range), and units with
  ammunition could not be sent into melee. The decision delay grew from about 6 s to
  7-10 s as the prompt grew.

## 2026-10-13: v12, v6's melee rules with v10's fire rules

Change (prompt): v6's prompt with only v10's two fire bullets (shooters hit infantry in
the open until contact; artillery then fires at missile units, then artillery; missile
units never trade fire with enemy missile infantry; a shooter moves before it attacks).
v8's cavalry rules and v9's and v11's lord rules are left out. The mirrors split the
versions (v6 best in the Khorne mirror, v10 in the Empire mirror), and v10's fire rules
are the change with the clearest measured basis.

Job `llm-luna-v12-kho-20261013` (source `42a8af7`): lost at 225 s (11% against 59%), 271 s
(19% against 52%) and 265 s (19% against 54%).

The scenarios were less fixed than intended. Picking a race leaves the faction within it
to the game, and it varied between jobs on both sides: Khorne jobs played Khorne against
Arbaal's faction or Crimson Skull against Khorne (v12's enemy also deployed elsewhere),
Empire jobs Wissenland, Empire or Golden Order, Dwarf jobs Dwarfs, Karak Kadrin or the
Ancestral Throng. Every comparison between versions above carries that variation (the
first v6 Khorne job, 2 wins of 3, is the only one with wins and played Khorne against
Arbaal, as did v9-v11's). The next fix pins each side's faction in the scenario.

v12 was reverted (`main` runs v10) and the scenario steps now pin each side's faction
(`61c5f7f`). First battle with pinned factions, Khorne against Khorne, v10
(`llm-luna-v10-kho-pinned-20261013`, stopped after it at the owner's return): lost at
248 s (32% against 52%). The enemy deployed at about (-23, -295), as in v12's job, not at
(-148, -267) as with Arbaal's faction. Results before `61c5f7f` mix factions; versions
should be compared again with pinned factions.

## 2026-10-13: v11, the lords never fight alone

Change (prompt, net shorter), chosen by the review of v10's Empire losses and v9's fast
Khorne loss (all three judges): the lord bullet becomes one rule. Whenever the enemy
lord is within 20 m of ours or fights any of our units, at least the nearest melee unit
that is not cavalry must target him, even out of another melee, until he breaks; our
lord attacks only an enemy another unit is on, never arrives first, and stays in melee
once there. Gone: v9's 5-point condition (read literally, it forbade help in a losing
duel, since our own lord counts as a unit on him), the 35% hurt-lord clause and "he is
your best fighter", which is untrue against the AI's 1.1 stats modifier. The reviewers
measured our lord, alone against the enemy lord, losing health 3 to 8 times faster than
he did; he was the first unit to rout in the v10 Empire losses.

Job `llm-luna-v11-kho-20261013` (source `1eb75aa`): lost at 246 s (27% against 46%), 232 s
(28% against 63%) and 198 s (22% against 74%).

To check whether v8-v11 cost the Khorne mirror, v6 was replayed there from a worktree at
`6777a64` (same ledger and results file): `llm-luna-v6-kho-20261013b` lost at 214 s (44%
against 77%), 227 s (37% against 50%) and 185 s (34% against 65%). v6 in the Khorne
mirror: 2 wins of 6; v9 1 of 3, v11 0 of 3. The first v6 job's two wins look like luck
more than a better prompt; the newer prompts are not shown to be worse there.

Job `llm-luna-v11-emp-20261013`: lost at 160 s (39% against 79%), 249 s (20% against
77%) and 189 s (42% against 73%). v11 in all: 0 of 6, and the Empire margin went back to
-42 points from v10's -20, so v11 was reverted: `main` runs v10.

Job `llm-luna-v10-kho-20261013` (source `9c8f995`, the v10 prompt): lost at 298 s (25%
against 37%), 211 s (15% against 68%) and 194 s (18% against 70%).

Where the mirrors stand at the end of the session (mean strength left, ours minus the
enemy's, in points): v6 Empire -48, Dwarfs -28, Khorne -8 (2 wins of 6); v10 Empire -20,
Dwarfs -26, Khorne -39 (no win in 9). v8-v10 traded the melee mirror for the gun mirrors;
`main` keeps v10, and v6's prompt is at `6777a64` for comparison. Spend for the session
about $0.25 (ledger total $0.68).

## 2026-10-13: v10, shooters hit infantry in the open

Change (prompt), chosen by the review of two v9 Dwarf and two v8 Empire losses (all three
judges): the reviewers measured, over the gun mirrors, artillery killing about 2 men a
shot at infantry in the open, 1 in 2 shots at missile infantry and 1 in 3 at crews, and
missile units killing about 1 man per 100 shots at enemy missile infantry. So until the
enemy infantry reaches our line every shooter fires at it; after that artillery fires at
the enemy's missile units, then its artillery (replacing v8's counter-battery first); a
missile unit never trades fire with enemy missile infantry and shoots infantry not in
melee, or from 40-60 m to the side of a fight; a shooter moves to its spot before the
attack (an attack replaces a move and walks a shooter straight at a target out of
range: about 20 such orders cut a shooter's own move in 14 gun-mirror battles).

Job `llm-luna-v10-emp-20261013` (source `ffbc953`): lost at 237 s (37% against 71%), 296 s
(22% against 38%: the enemy's lowest yet in this mirror) and 254 s (51% against 63%).
Still no Empire win, but the margin has narrowed with each version: mean strength left,
ours against the enemy's, v6 21/69%, v8 31/70%, v10 37/57%.

Job `llm-luna-v10-dwf-20261013`: lost at 432 s (47% against 63%), 574 s (35% against 66%)
and 394 s (44% against 75%); mean 42/68%, against v9's 35/65% and v6's 25/53%.

## 2026-10-13: v9, fight the enemy holding you

Change (prompt), chosen by the review of the v6 Dwarf mirror losses and the Khorne
mirror loss (all three judges): after contact, a unit the game moved onto another enemy
stays on it; the enemy-lord rule sends units back to him only while he lost 5 or more
health since the last turn or none of ours is on him; no unit leaves a wavering enemy.
The reviewers counted 11-15 pulls onto the enemy lord per Dwarf battle while he stood
inside his own infantry, losing about 1.4 points a turn, and the enemy holding each
pulled unit hit its flank (f3 Longbeards 68→48 men against e3's 75→71 in one loss).

Job `llm-luna-v9-dwf-20261013` (source `d928965`): lost at 554 s (27% against 59%), 696 s
(33% against 49%) and 332 s (45% against 86%). Job `llm-luna-v9-kho-20261013`: lost at
205 s (25% against 70%), won at 218 s (35% against 36%), lost at 297 s (17% against 36%).
In the Khorne mirror v9 (with v8 under it) did worse than v6 (2 of 3, 34% against 25% on
average), and the mean delay rose from 7.2 s to 9.6 s as the prompt grew; which of v8 or
v9 cost the Khorne battles is not separated.

## 2026-10-13: v8, answer the enemy's guns

Change (prompt), chosen by the review of the Empire mirror (all three judges): artillery
fires first at enemy artillery in range ("never at small crews" had made the model take
the cannon off the enemy cannon, the game's own pick, at 5 s in all three battles);
missile infantry stands 40-60 m to the side of the melee line, never straight behind it
(the handgunners fired 167 rounds through our own melee for 2 kills); a shooter whose
target loses no men for two turns moves to a clear line or switches; cavalry shelled
while waiting ride wide onto the enemy artillery instead of shuffling about in its range;
cavalry are left out of the enemy-lord gang-up.

Job `llm-luna-v8-emp-20261013` (source `fbcdf99`): lost at 321 s (25% against 69%), 203 s
(30% against 83%) and 343 s (38% against 57%). The enemy cannon was hit hard each time
(7, 33 and 15 of 33 crew left, against 33 of 33 under v6) and our side kept more (25-38%
against v6's 8-37%), but the enemy handgunners still ended untouched (66-67 of 68).

Job `llm-luna-v8-dwf-20261013` (source `3879027`, stopped after two battles when v9 was
merged): lost at 487 s (33% against 77%) and 605 s (26% against 75%). The enemy Grudge
Thrower broke under counter-battery fire, but the enemy infantry kept more than under v6
(43-66%): shells that went at the enemy artillery no longer thinned its infantry, and the
melee was lost as before.

## 2026-10-13: Mirror battles (second session)

Scenarios are now named in `configs/twwarhammer3/scenarios.json` (each side's race,
faction and units; the menu steps pick the race in the selector's popup). Mirror battles
put the same army on both sides of the same map, the player starting north:
`kho5-kho5` (the Khorne army above), `dwf5-dwf5` (the Dwarf army above) and `emp5-emp5`
(Empire: General, Swordsmen, Handgunners, Empire Knights, Great Cannon).

Empire mirror, source `b1c9ce0`:
- `attack_nearest` (`attack-emp-mirror-20261013`): lost at 228 s and 232 s.
- v6 (`llm-luna-v6-emp-20261013`): lost at 270 s (8% against 71%), 242 s (19% against
  71%) and 246 s (37% against 65%). In every loss the enemy handgunners and cannon ended
  nearly untouched (64-66 of 68 men, 33 of 33) while ours were destroyed.

Khorne and Dwarf mirrors, v6, source `6777a64`:
- `llm-luna-v6-kho-20261013`: won at 265 s (39% against 17%), lost at 282 s (25% against
  33%), won at 247 s (37% against 25%).
- `llm-luna-v6-dwf-20261013`: lost at 499 s (31% against 66%), 576 s (24% against 50%) and
  629 s (20% against 43%).

v6 in the mirrors: 2 wins of 9, both in the melee-heavy Khorne mirror. The armies with
guns, crossbows and artillery beat the model every time.

## 2026-10-13: v7, the enemy lord only while he is losing the lords' race

Change (prompt): v4's always-on "every melee unit within 40 m attacks the enemy lord" is
gone. After contact the enemy lord stays the focus only while his health is below our
lord's or fell 5 points or more since the last turn; otherwise units leave melee targets
on the game's choice and switch to the nearby enemy closest to breaking.

Job `llm-luna-v7-20261013` (source `42d3054`): won at 451 s (10% against 27%), lost at
334 s (30% against 17%: our army broke with more men left than the enemy's), won at 376 s
(32% against 35%).

Replicate `llm-luna-v7-20261013b`: lost at 256 s (35% against 64%), lost at 278 s (32%
against 70%), lost at 434 s (22% against 29%). v7 in all: 2 wins of 6, against v6's 5 of
6, so v7 was reverted: `main` runs the v6 prompt. Without the standing order to pile onto
the enemy lord, the replicate's battles were lost fast; the race test seems to have taken
units off him too early. The next version starts again from v6.

## 2026-10-13: v6, show what each unit is really doing

Change (state rendering, `llm.py`, with the prompt's description of it): each friendly
target is marked as the ordered one ("target e1 3 m (your order, 95 s)") or the game's
choice with the order it replaced; a move the game dropped reads "stopped N m short of
your move"; a unit with no target or destination reads "no order" and shows its nearest
visible enemy; men and health show the change since the previous decision for both sides;
orders are forgotten once the game no longer carries them out. In the same merge, fixes
from a review of this session's code (not visible to the model in this scenario): flying
monsters labelled flying again, the restart fallback only before a decision, battle UI
probes through `menu.json`, `stats` grouping scripted rows by source revision.

Job `llm-luna-v6-20261013` (source `ac3c0bd`): won at 357 s (26% against 34%), won at
496 s (8% against 24%), lost at 428 s (12% against 38%).

Reviews: the new lines were used. The model put units back on the enemy lord after the
game had moved them ("game's choice") 6-8 times per episode, and the horsemen's attack
orders were no longer replaced over and over. But the always-on gang-up then misfired:
in the loss the Bloodletters and Chaos Warriors stood "on" the enemy lord for 80 s while
his health fell about 1 point a turn (he stood inside his own infantry), and the Dwarf
Warriors wavered untouched beside them; the Herald was sent back at him 24-26 points
behind. Support fire stayed useless (14 Skullcannon shots and 270 axes for about 2 kills
in the first win); the hurt-lord rule parked the Herald for most of two battles.

Replicate `llm-luna-v6-20261013b`: won at 462 s (16% against 34%), won at 381 s (51%
against 18%), won at 374 s (56% against 19%: the widest margins of any battle so far,
the baseline included). v6 in all: 5 wins of 6.

## 2026-10-13: v5, a hurt lord keeps fighting

Change (prompt): below 35% health the lord stays out of melee only while a healthier
enemy lord or hero is near, and goes back in as soon as that enemy has less health than
he has (v4 parked him for minutes while the enemy lord was nearly dead).

Job `llm-luna-v5-20261013` (source `33895de`): won at 333 s (64% of our men left, 29% of
the enemy's: a wider margin than any baseline battle), won at 343 s (36% against 36%),
lost at 417 s (10% against 48%).

Reviews: the wins came from the lord and both infantry units walking in together and
all three going onto the enemy lord in the same reply at contact (he routed at 162 s in
the first win, our lord at 58%); the hurt-lord rule mattered in the second win (the
Herald fought on at 42% once the lords' health was level). The loss turned on the lord
duel: the Herald's line move carried him past the engaged Chaos Warriors, he alone was
sent onto the enemy lord, and when the game retargeted him and the Bloodletters onto
other enemies the model read it as its own gang-up, leaving the enemy lord untouched at
80% for 90 s. The support units achieved little in all three: the Skullcannon's 12 shots
killed almost no one and the horsemen's attacks on the Quarrellers were replaced by the
game 7 times, each acknowledged as applied.

Replicate `llm-luna-v5-20261013b`: won at 333 s, won at 418 s, lost at 329 s (32% against
54%). v5 in all: 4 wins of 6.

## 2026-10-13: v4, one body, gang up on the enemy lord

Change (prompt): the lord and the melee units advance side by side at a walk; two or
three units on one enemy, the enemy lord first at contact; every melee unit within 40 m
attacks the enemy lord when he engages; our lord attacks only targets another unit is on
and parks 30-50 m behind the line below 35% health. From the v3 reviews: the Herald fought
the enemy lord with no other melee unit on him in all 28 such turns (the baseline had help
in 20 of 22), and the model paired its units off one to one.

Job `llm-luna-v4-20261013` (source `0547bfb`): lost at 603 s (9% of our men left, 32% of
the enemy's), lost at 488 s (7% against 40%), won at 355 s (44% against 39%, the closest
an LLM battle has come to the baseline's 45% against 33%). The model followed the
doctrine: it walked on 55 of 76 moves and attacks (v3: 34 of 140), met the enemy at 95 s
like the baseline (v3: 55-79 s) and helped its lord in 12 of 14 duel turns.

Reviews: in both losses the Herald was parked at 20-23% health for 18 and 23 straight
decisions while the enemy lord fell to 12-2% and the model itself called him "nearly
defeated" (v4's "bring him back only to finish a routing or nearly dead enemy" had no
threshold); in the win the enemy lord routed at about 160 s, earlier than in the
baseline. The support units still did little: the Skullcannon fired its 12 shots for at
most 3 kills, and the horsemen, ordered at the Quarrellers through the melee, stalled
behind it and routed, throwing 6-26 axes where the baseline's threw about 170 into the
Dwarf Warriors before contact. Moves to flank were acknowledged but the unit barely moved.

Pause-mode ablation, job `llm-luna-v4-pause-20261013` (same source, `--pause`: the battle
stops while the model thinks; orders apply 0.6 s of battle time after the state seen,
against 5.5 s in real time): lost at 232 s (37% against 71%), lost at 579 s (8% against
34%), won at 434 s (39% against 26%). One win of three, as in real time: the model's
latency is not what separates it from the baseline.

## 2026-10-13: v3, commit and focus (best so far)

Change (prompt): v2's withdrawal triggers replaced by a commit-and-focus doctrine: keep
units in melee and send help into the enemy's flank instead; focus the enemy closest to
breaking and the enemy lord; the lord leaves melee only below 35% health; spent missile
units fight in melee; cavalry wait until the lines lock; "back" means toward our start.

Job `llm-luna-v3-20261013` (source `2681d04`): lost at 303 s (38% of our men left, 49%
of the enemy's), won at 419 s (11% against 18%), won at 392 s (28% against 24%); mean
delay 4.5 s, think time back to v1's level.

Replicate `llm-luna-v3-20261013b`: lost at 257 s, won at 345 s. v3 in all: 3 wins of 5.

Reviews: the Herald fought the enemy lord with no other melee unit on him in all 28 such
turns (the baseline had help in 20 of 22 and its Herald survives); the model paired its
units off one to one at contact ("f1 e1, f2 e2, f3 e3", from "strongest against
strongest"); the game's automatic target is shown as if it were the order, so a unit
the game had retargeted looked busy; units with ammunition shoot when ordered to attack,
so the horsemen and the Skullcannon could not charge.

Across all episodes so far, the model orders `run` on about 90% of its moves and attacks
(v1: 62 of 67; v2: 296 of 324), while `attack_nearest` never runs; the baseline's units
always reach their first melee fresh, the model's often tired or exhausted.

## 2026-10-13: v2, a battle doctrine (worse)

Change (prompt): check every unit each turn and pull back units that waver, lose men
faster than their target, or are under fire with nothing to hit; pull the lord back
below 40% health; switch fire targets that lose no men; keep missile cavalry out of
enemy missile range; charge only once the lines are locked. State fixes in the same
version: "running" only while moving, a unit's class fixed at the start, enemy missile
range shown, dead units on one line, moves to unreachable points rejected.

Job `llm-luna-v2-20261013` (source `f807f64`): lost at 569 s (none of our men left,
77% of the enemy's), lost at 614 s (2% against 45%) and lost at 1226 s (10% against 20%,
66 rejected orders). The model turned "pull back"
into a slow general withdrawal: units left melee (which costs men and morale in Total
War) and the army drifted to the map corner, where about 25 moves per episode were
rejected as unreachable. Think time doubled to about 8 s with the longer prompt.
Reviews (two episodes): moves ordered to units in melee went from none in v1 to 14 and
10; after the withdrawals began the enemy lost almost no men; the lord flip-flopped
between committing and withdrawing over a 3-point health gap, and lost 42% health while
disengaging.

## 2026-10-13: Baseline after the lapse fix

`attack_nearest`, source `7b31ce9`, job `attack-b2-20261013`: won 3 of 3 at 346, 344 and
346 s, with 45% of our men left against 33% of the enemy's. A fixed policy gives nearly
the same battle every time; the model's variance comes from its own orders.

## 2026-10-13: v1, first LLM battles

Source `b615830`, job `llm-luna-v1-20261013`, `gpt-6-luna` low effort: won at 446 s,
lost at 503 s, lost at 366 s; 132 decisions, no invalid orders, mean delay 4.0 s between
the state seen and the orders applied (think time 3-6 s), $0.035 in all.

Reviews (one subagent per episode, `wh3-version-review` workflow): the Herald died in all
three episodes, each time sent into a fight at 21-38% health (twice at the enemy lord);
the Skullcannon spent all 36 of its shots across the episodes on the Grudge Thrower crew
and never killed one; the Marauder Horsemen were committed before the lines met and lost
missile duels to the Quarrellers; 83 of 132 replies gave no orders ("all units have
active orders", from the prompt's "leave out units that are carrying out your orders"),
including minutes when the lord bled out; "back toward the army" moves went to the
enemy side of the melee (no sense of the front). Misleading state: "running" on standing
units, the Skullcannon's class flipping with its ammunition, dead units listed with stale
flags, no enemy missile range, moves to unreachable points acknowledged as applied.

## 2026-10-13: First baseline

`attack_nearest` (every unit attacks its nearest visible enemy), source `60314c3`, job
`attack-m3-20261013`: lost at 344 s, won at 400 s. Before `c3c9177` the baseline did not
re-order units whose attack had lapsed, so units stood idle under fire for minutes; the
two episodes understate it.
