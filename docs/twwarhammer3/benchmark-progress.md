# Benchmark implementation and experiments

Owner goal, 2026-10-14: complete the first three suggested next steps: make one or two
battle types credible benchmarks, calibrate difficulty/baselines and latency, and fix
the gaps required by those scenarios. This page tracks completion evidence; the design
is in [benchmark.md](benchmark.md) and the original acceptance brief in
[WH3_latency_aware_benchmark_requirements.md](WH3_latency_aware_benchmark_requirements.md).

## Acceptance checklist

- [ ] Frozen scenarios: explicit maps, factions, armies, roles, settings, content and
      development/held-out variants; setup read-backs reject mismatches before scoring.
- [x] One launch rotates named or importable controllers in a recorded random order;
      rematch start fingerprints show pairing quality. Existing single-policy jobs work.
- [x] Every started trial is recorded; only engine won/lost/draw count as gameplay
      outcomes. Refusals reach the controller. Evaluation-only strength totals exclude
      routing/shattered units and exist at non-gameplay endings too.
- [x] Reports show denominators, failures, uncertainty, paired instance differences,
      objectives, timing, rejections, costs and reproducibility limitations.
- [x] Document an independently runnable evaluation, including controller contract and
      setup requirements. Live acceptance includes an outside controller and Luna;
      a deliberately broken setup is rejected.
- [ ] Verify the AI stats modifier read-back and behavior at 1.0 and 1.1; select and
      document calibrated settings instead of assuming a 10% effect.
- [ ] Run paired scripted calibration across independent launches, tune development
      scenarios if all controllers hit floor/ceiling, and establish competent versus
      trivial separation with uncertainty. Keep held-out variants out of tuning.
- [ ] Run controlled 0/6/10 s delay trials with natural latency retained and battle
      always live at 1x. Report sensitivity or the detectable-effect limit of a null.
- [ ] Fix and engine-test the selected scenarios' terrain/path and control gaps;
      offensive siege variants require gate/wall orders and equipment before admission.
- [x] Align episode caps with game timers; finish time-weighted objective reporting,
      key-building register fields and reinforcement counts by unit type.
- [ ] Appropriate regression tests, lint, live evidence, version log/results register,
      session state, commits and final requirement-by-requirement completion audit.

## Current work

Owner steering now prioritizes specialist challenges with anchor units and faction
mechanics; [scenario-recipe.md](scenario-recipe.md) is part of candidate selection.
The unstarted Herald G1 plan was superseded before any G1/G2 trials. b2 diagnostics and
the specialist frontend inventory completed; b3 and b4 are merged. The first candidates
are compact: cavalry six versus eight, caster five versus ten, each with an 8000 cap
and unused funds. The serial screen on `e221324` stopped after five gameplay losses
and one deliberate exploratory interruption. Caster: Luna/hold/attack-nearest lost
963/613/301 s. Cavalry: hold/attack-nearest lost 415/262 s; Luna's untouched army was
retreating for a timeout win when interrupted at about 292 s. Do not call that trial a
win or loss. A faster enemy anchor is the next pressure hypothesis; the frontend mount
inventory is prepared. Also review a cavalry rematch's 4.826 m/12-degree formation
flag before freezing calibration. All resources/rosters matched. Completed harness
items above rely on b1/b2 engine
evidence and the regression checks below; they do not imply scenario admission.

Source `b476175` completed acceptance and the serial diagnostic queue. All four queue
jobs completed, and the queue/final controller exited successfully at 17:15:50 UTC.
The objective audits passed: the 15 domination purchases match nine new IDs plus six
old IDs restored from zero men, by type; final supplies, ownership and register rows
agree with traces. Settlement and domination ownership cases were all-held/never-held;
changing ownership is covered by the separate Lua sampler regression. Audit:
`runs/twwarhammer3/reports/bench-b2-objective-audit.json`.

Draft `9b73105` from `/tmp/wh3-benchmark-b3` was merged after the queue completed.
The subsequent b4 frontend inventory verified cards, mounts and default spell loadouts.
During the first caster battle, nonzero barriers, spell ranges, mana consumption,
cooldowns and private current starting stats are live-observed. A read-only query found
that Screamers' engine category is `inf_mel` despite being airborne; draft b5 `dde4cfe`
in `/tmp/wh3-benchmark-b5` corrects classification and exposes flight state. Its 207 WH3
tests, Ruff and Lua compilation pass. It is not installed into the running screen.
The b4 queue and game controller exited at 18:24:45 UTC; no controller is active.
Current process handles and next actions are in [../state.md](../state.md).
No scenario is admitted. The owner has
superseded the unstarted generic Herald calibration plan with specialist candidate
selection; the new candidate/reference must be frozen before G1/G2. The held-out Herald
map has not been used; neither have the new specialist held-out maps. API ledger was
$3.3329 before specialist screening; `twwarhammer3 spend` reads the current total.

## Implementation and live acceptance

Screening update (2026-10-14 16:39 UTC): `bench-b2-screen-ai10-20261014` completed
all three trials on `dwf-sla-herald` at 1.0. Hold lost at 448 s, skills won at 382 s,
attack-nearest lost at 249 s; active margins -0.412/+0.372/-0.710. Both rematch starts
matched, invalid orders 0/0/5. Whole-job throughput: 3 valid trials / 1283.63 s =
8.41 trials/hour. This supports repeated calibration, not admission from one instance.
Report: `runs/twwarhammer3/reports/bench-b2-screen-ai10.json` (computed with b3 reporting,
retaining the actual b2 experiment source). The 1.1 screen started at 16:38:28 UTC;
its process and queue are recorded in the session page.

The 1.1 screen subsequently completed: attack-nearest lost at 242 s, hold at 266 s,
skills at 265 s; margins -0.761/-0.658/-0.481. Matched rematch starts, invalid orders
3/0/0, full-job 967.02 s and 11.17 valid trials/hour. Report:
`runs/twwarhammer3/reports/bench-b2-screen-ai11.json`. Both modifier groups remain
one instance each. A read-only specialist-interface query at 95.3 s of the skills
trial returned Rune ranges/durations and barrier 0/0; no game orders or speed changes
were made by the probe. The settlement objective probe started at 16:54:35 UTC.

Draft b3 now ends at `37f3ebf` in `/tmp/wh3-benchmark-b3` (197 WH3 tests pass with Lua,
Ruff and Lua 5.1 parsing pass). To support the owner's new direction it adds:
- `llm_rules`, retaining the direct controller's actions/memory/timing/ledger while
  replacing the v15 tactical prescriptions with an independently recorded rules-only
  prompt. Original `llm` remains available. Factory, budget and prompt/model record tests pass.
- Barrier HP separate from health, and ability cast range/effect radius/duration. Rune
  and zero-barrier queries are live-proven; a nonzero barrier and caster spell use still
  need the specialist smoke. Probe: `capability-probes/benchmark-specialist-interface`.
- Starting strength/ammo/barriers, friendly ability loadouts and magic/supplies/tickets
  in rematch comparisons. Changed resources or spells flag pairing even with identical
  positions. Recomputing these checks on all six b2 screening traces found no mismatches
  within either launch (the old traces lack the newly added barrier/range fields).

All changes remain isolated from the running b2 queue. The new controller and interface
must pass live checks before the specialist calibration source is frozen.

The final draft source also passed 1041 tests in the main workspace's dependency
environment, with four skips: one local original-engine evidence case, the opt-in
Windows process-ownership test, and the two Lua tests. Those Lua tests passed in the
separate 197-test WH3 run with Lupa. A fresh worktree environment passed 785 tests with
15 skips before checking the fuller dependency environment. No live games were launched
by these test runs.

Settlement objective probe completed at source `b476175`: engine loss at 244 s, one
refusal, nine accepted `barricade_platform` builds, 204 supplies left. All five points,
including the key building, remained ours for the full recorded 238.8 s; holding them
did not prevent the army's loss. The trace independently reconstructs 238.5 s plus the
initial 300 ms sampling gap. The result and register fields agree. At the final snapshot
eight built slots were marked destroyed and one was still constructing, so build counts
are accepted purchases, not completed/surviving structures. Audit artifact:
`runs/twwarhammer3/reports/bench-b2-settlement-objective-audit.json`.
The domination probe started at 17:00:42 UTC and remains the queue's final job; its
reinforcement-by-type and changing-ownership checks are still pending.

Boundary audit while the queue runs: the old Lua roster could announce later enemy
arrivals without sight, and `entry.seen` allowed a previously seen enemy's hidden death
to update the public roster. Draft `7c71deb` in `/tmp/wh3-benchmark-b3` corrects both and
names the changed contract `obs-v2+terrain`. The initial lobby roster stays public;
private scoring still sees all registered units. Lua regression covers hidden arrival,
first sighting, hidden death, observed death and retained knowledge. 192 WH3 tests pass
with Lua enabled, Ruff and Lua 5.1 parsing pass. The running b2 queue is unchanged;
merge and engine acceptance follow it, before G1/G2. The runbook also clarifies that
active-strength denominators include units summoned/reinforced during battle.

Prepared `runs/twwarhammer3/calibration/audit-objectives.py` for the queued metric probes:
recompute ownership from trace samples with transition brackets, compare final supplies,
count accepted build/purchase acknowledgements by type, and list observed arrivals.
It has not yet validated the pending probes.

A further setup audit read the extracted primary UI API documentation: `CcoUnitStat.ValueBase`
excludes modifiers/buffs/debuffs, while `Value` reports the current stat. Draft `6caacec`
retains both privately at startup. The b2 base-stat snapshots are insufficient evidence
of applied 1.0/1.1 bonuses; compare b3 current values under matched starting conditions.
The new expression parses as Lua 5.1; its engine values remain to be checked in b3.

The completed startup comparison adds direct evidence beyond that API description:
both 1.0/1.1 screen snapshots were taken at 5.2 s, and all 12 AI unit entries changed
while all 12 player entries stayed identical. UI ValueBase already incorporates these
AI settings: approximately +10% melee attack/defence, weapon damage and charge (integer
rounding), and +8 leadership. For example Marauders 28→31 attack, 32→35 defence,
25→28 damage, 6→7 charge and 60→68 leadership. Thus the broad inference that ValueBase
would exclude AI difficulty bonuses was too strong; current Value is still useful to
distinguish additional active effects. Evidence:
`runs/twwarhammer3/reports/bench-b2-starting-base-stat-comparison.json`.

- `5cad165` (main): first benchmark implementation. Full suite: 1030 passed, 1 skipped;
  Ruff and Lua 5.1 syntax checks pass. Added rotation/import controllers, strict setup,
  delayed public observations, active-strength scoring, tick-integrated objectives,
  interruption/failure records and paired reports. [Run instructions](benchmark-run.md).
- Completed job `runs/twwarhammer3/battle/bench-b1-acceptance-20261014` started
  2026-10-14 14:54:39 UTC. Controller PID 307322, tool session 9163. Rotation: hold,
  Luna llm, skills, attack_nearest, external_controller:ExternalHold. Five trials on
  one frozen instance; these are acceptance checks, not independent benchmark samples.
  The external module is `/tmp/wh3-benchmark-controllers/external_controller.py`;
  its hash is recorded per trial. Existing key-file location was recovered from prior
  job scripts; no credential values were printed or changed.
- Setup checks passed in the live game. `hold` lost at 386 s, no invalid orders,
  battle/system-wall clock ratio 0.9967. The first rematch started Luna's trial.
- Luna lost at 824 s ($0.0594), clock ratio 0.9985, initial rematch fingerprint unflagged.
  All enemies except Sigvald were routed or destroyed. Rejections: 9 unreachable moves,
  7 routing units, 1 dead target and 4 spell refusals. Its later plan hid survivors for
  the defender's 60-minute timeout; Sigvald broke the remaining army first. Calibration
  should use a separately declared shorter finite timer after its lobby option is probed.
- Read-only live probes (steps in `runs/twwarhammer3/capability-probes/benchmark-b1`,
  replies in the acceptance episode mod logs) found `CcoBattleArmy.AiStatsModifier`
  = 1.1 on both army contexts; this is the setting, not proof both sides get bonuses.
  `CcoUiUnitStatRecord.PreviewAiStatModifierString(1.1)` reports +10% melee attack,
  defence and weapon damage, and +8 leadership. Exact 1.0 behavior still needs its probe.
- `battle_boundaries()` returns four vectors, here (-512,+512), (+512,+512),
  (-512,-512), (+512,-512) in x/z. 1024 terrain-clearance queries at 32 m spacing
  found 832 clear 16 m squares in 0.03 CPU seconds. This is coarse terrain information,
  not unit-specific reachability or a guarantee that a narrow crossing is represented.
- Initial b2 draft (`38535c3`) was isolated in `/tmp/wh3-benchmark-b2`, branch `wh3-benchmark-b2`.
  It adds explicit lobby AI-modifier setting/read-back and per-army battle read-back,
  coarse terrain plus unit-specific reachable alternatives after rejected moves,
  opt-in API wall timing/model/header records (Spire default unchanged), and report
  improvements. Full worktree suite: 1019 passed, 14 skipped (local evidence absent);
  rechecking combat tests with the main evidence root gave 329 passed, 1 skipped.
  Follow-up targeted suite: 57 passed. These checks preceded the merge and the live fixes described below.
- b2 also freezes `dwf-sla-herald` (1.0), `dwf-sla-herald-hard` (1.1), and
  `dwf-sla-herald-heldout-wastes` (1.0, new map) before calibration. The replacement lord
  card `wh3_main_sla_cha_herald_of_slaanesh_shadow_0` is present in the earlier lobby dump.
  The held-out map must not guide tuning. These are fallback candidates if the original
  scenario remains at the floor; they were unplayed when declared.

The entries below retain the acceptance sequence and its failures. Current outstanding
work is summarized above; no scenario admission or calibration result is claimed yet.

### b1 completed

Five engine losses: hold 386 s, Luna 824 s, skills 426 s, attack_nearest 262 s,
external hold 386 s. Every rematch start matched; external hold reproduces the built-in
hold margin (-0.675). Active margins: attack_nearest -0.594, skills -0.192, Luna -0.002.
This one instance gives no paired uncertainty estimate. Acceptance report:
`runs/twwarhammer3/reports/bench-b1-acceptance.json`. The live process has exited.
The declared [calibration plan](calibration-plan.md) fixes screening, admission and
controlled delay experiments before those candidates are played.

### b2 frontend validation

Merged b2 as `7c0abdb` after b1 stopped. The standalone frontend probe
`runs/twwarhammer3/capability-probes/benchmark-b2-frontend` read the timer options
(1200, 2400, 3600 s and unlimited), set short and read 1200 s, and set/read both
1.0 and 1.1 AI modifiers. Its controller exited normally after SIGINT. Calibration
Herald variants now declare the verified 1200 s timer; b1 keeps its original 3600 s.
All declared timers are explicitly selected and verified, independent of prior profile.

### b2 battle setup finding

`bench-b2-terrain-20261014` on `587d501` stopped with `setup_failure`, zero episodes:
the CPU Herald army exceeded `funds_large`. Map/army dumps were copied from the bridge
by the operator because this failure path did not retain them automatically. No terrain
or modifier battle validation is claimed from it. A funds-options frontend probe
(`benchmark-b2-funds`, started 15:45:19 UTC) is running before the roster budget is revised.

The funds probe completed: this build offers `funds_large` (Default Funds) and
`funds_custom` only; `funds_ultra` did not change the selection and its assertion failed.
Selecting custom funds and setting 30000 both read back successfully. The three Herald
candidates now declare custom 30000, with unchanged units. Failed-setup dumps are now
saved when the current menu log confirms they were produced; stale bridge dumps are
excluded. Regression checks cover the refused budget and retained failure evidence.

### Broken-setup acceptance passed

`bench-b2-broken-setup-20261014` on `acb97f5` rejected
`deliberately_missing_benchmark_unit` at recruitment step 37. Manifest: setup_failure,
zero episodes; the current map dump was retained automatically. The diagnostic driver
and scenario hashes are in `capability-probes/benchmark-b2-broken-setup/probe.json`.
The b2 acceptance retry rotates TerrainProbe then Luna on the corrected Herald 1.0
scenario (`bench-b2-acceptance-20261014`, session 98256). TerrainProbe asserts that an
out-of-bounds move is refused, selects one reported alternative, checks its acceptance,
records movement after six seconds, then halts and holds. No scores from this diagnostic
controller will be used for scenario calibration.

### b2 battle read-back and terrain fix

The corrected Herald scenario passed every lobby and in-battle setup check on
`acb97f5`; both army modifier getters returned 1.0, and the private starting-stat string
contains both full rosters. The diagnostic then failed before issuing orders because
terrain was absent: `mod.log` reports the game has no `math.huge`. This was retained as
a policy failure with the last private evaluation, and Luna was left unplayed.
The sampler now initializes bounds from its first actual corner. A Lua 5.1 regression
removes `math.huge` and checks the grid geometry; it passes with `uv run --with lupa
pytest tests/twwarhammer3/test_wh3_lua_terrain.py`. Vanilla battle code uses the other
trigonometry APIs in the new navigation code. Full suite before this one-line Lua fix:
1033 passed, 1 skipped; Ruff clean. All mod scripts parse after the fix.

The corrected acceptance retry is `bench-b2-acceptance-r2-20261014` on `b476175`,
tool session 70797; it again rotates TerrainProbe then Luna. After it completes,
compare starting unit stats against the 1.1 screening arm, run the objective-mode
metrics probe(s), then screen/admit the calibrated family and execute G1/G2.

### Terrain and navigation passed in the engine

On `b476175`, `bench-b2-acceptance-r2-20261014` published a 32x32 terrain grid.
At 5.5 s the engine refused f2 moving to (-520, 130.6), returning three tested nearby
positions. TerrainProbe chose (-504, 130.6); the engine accepted it, f2 moved 6.29 m
over the six-second check, and navigation feedback cleared. The halt was accepted.
Proof event, starting stats and source are saved in
`capability-probes/benchmark-b2-controllers/navigation-proof.json`; trace remains the
authoritative record. The battle continues as hold; Luna is the next rematch.
This validates the selected classic scenario's terrain/path interface, not offensive
siege gate/wall controls or a general path planner.

### b2 acceptance telemetry and ability feedback

The terrain diagnostic ended on an engine loss at 350 s (clock ratio 1.0066), with
only its deliberate unreachable move rejected. Luna's first call on the rematch
records actual_model `gpt-6-luna`, provider processing 7.280 s, total call wall 8.122 s
and one transport attempt. Its prompt includes the terrain grid and sampling limits.
The returned name is still an alias, not proof of an immutable provider snapshot.

Luna's later ability refusals were inspected in the trace: Slowness and gyrocopter
bombs were accepted before repeat requests were refused, Whirlwind was accepted at
139.6 s and its retry refused at 145.3 s as its active/cooldown state appeared, and
Wrath and Ruin was refused after another rune but accepted later. The native error says
"does not support this special ability" even in these temporary states. This does not
justify marking the keys permanently unsupported or repairing the policy's requests.
The acknowledgement is issuance; UI readiness can lag it and change during inference.
The observations expose last-issued time and subsequent active/recharge state.

### b2 acceptance completed

`bench-b2-acceptance-r2-20261014`: two engine losses, diagnostic 350 s and Luna 442 s.
Rematch starts match. Luna: 68 decisions, 14 refused orders, $0.03919; ledger $3.3329.
Report: `runs/twwarhammer3/reports/bench-b2-acceptance-r2.json`. The 1.0 scripted screen
started at 16:17:05 UTC under the serial queue. These are screening data, separate from
the six-launch admission experiments. A b3 draft is isolated while this queue runs.

### Isolated b3 audit follow-up

`a9b066b` on branch `wh3-benchmark-b3` (`/tmp/wh3-benchmark-b3`) adds the missing-terrain
setup gate, preserves startup error causes and distinguishes them from interruptions,
and reports throughput using full job wall time including setup/reset/failure overhead.
Checks: 190 WH3 tests passed, 1 skipped; Ruff passed. Recomputing the broken setup,
failed first b2 attempt and successful retry gives 2 valid / 3 started trials in 0.38
job wall hours, 5.32 valid trials/h. This is aggregate pipeline throughput, not a policy
ranking. Preview report: `runs/twwarhammer3/reports/bench-b3-report-preview.json`.
Do not merge while the b2 queue runs; the queue pins `b476175`.

The 1.0 screen's first roster snapshot and acceptance's first snapshot are both at
5.2 s, but five unit positions differ by more than 1 m (maximum 6.8 m). Fresh starts
therefore vary in this pair; this alone does not prove statistical independence.
Within acceptance, rematch start fingerprints matched.
