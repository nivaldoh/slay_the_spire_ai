# Benchmark implementation and experiments

Owner goal, 2026-10-14: complete the first three suggested next steps: make one or two
battle types credible benchmarks, calibrate difficulty/baselines and latency, and fix
the gaps required by those scenarios. This page tracks completion evidence; the design
is in [benchmark.md](benchmark.md) and the original acceptance brief in
[WH3_latency_aware_benchmark_requirements.md](WH3_latency_aware_benchmark_requirements.md).

## Acceptance checklist

- [ ] Frozen scenarios: explicit maps, factions, armies, roles, settings, content and
      development/held-out variants; setup read-backs reject mismatches before scoring.
- [ ] One launch rotates named or importable controllers in a recorded random order;
      rematch start fingerprints show pairing quality. Existing single-policy jobs work.
- [ ] Every started trial is recorded; only engine won/lost/draw count as gameplay
      outcomes. Refusals reach the controller. Evaluation-only strength totals exclude
      routing/shattered units and exist at non-gameplay endings too.
- [ ] Reports show denominators, failures, uncertainty, paired instance differences,
      objectives, timing, rejections, costs and reproducibility limitations.
- [ ] Document an independently runnable evaluation, including controller contract and
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
- [ ] Align episode caps with game timers; finish time-weighted objective reporting,
      key-building register fields and reinforcement counts by unit type.
- [ ] Appropriate regression tests, lint, live evidence, version log/results register,
      session state, commits and final requirement-by-requirement completion audit.

## Current work

Runtime doctor is ready (build 25823491, AI stats preference 1.1). The starting main
worktree was clean. The b1 acceptance job is complete. Calibration and
interface probes follow on committed source; source edits during a live job use a
separate worktree. All live experiments are serialized across both games and use the
existing WH3 ledger, capped at $25 total. The owner authorized the three steps; testing
1.0 and 1.1 is within that calibration work.

## Implementation and live acceptance

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
- Draft b2 (`38535c3`) is isolated in `/tmp/wh3-benchmark-b2`, branch `wh3-benchmark-b2`.
  It adds explicit lobby AI-modifier setting/read-back and per-army battle read-back,
  coarse terrain plus unit-specific reachable alternatives after rejected moves,
  opt-in API wall timing/model/header records (Spire default unchanged), and report
  improvements. Full worktree suite: 1019 passed, 14 skipped (local evidence absent);
  rechecking combat tests with the main evidence root gave 329 passed, 1 skipped.
  Follow-up targeted suite: 57 passed. These changes are not installed in
  the running game and still need live validation after this job ends.
- b2 also freezes `dwf-sla-herald` (1.0), `dwf-sla-herald-hard` (1.1), and
  `dwf-sla-herald-heldout-wastes` (1.0, new map) before calibration. The replacement lord
  card `wh3_main_sla_cha_herald_of_slaanesh_shadow_0` is present in the earlier lobby dump.
  The held-out map must not guide tuning. These are fallback candidates if the original
  scenario remains at the floor; none has been played yet.

No scenario admission or calibration result is claimed yet. Remaining work includes
completing the five-controller acceptance, the broken-setup check, validating b2,
freezing held-out variants, actual scripted calibration at both settings and 0/6/10 s
delay experiments, and final evidence/report/documentation audit.

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
