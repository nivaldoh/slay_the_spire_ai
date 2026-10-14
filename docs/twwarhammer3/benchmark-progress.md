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
worktree was clean. No game controller is running. First implementation stage: setup
checks, controller rotation, trial accounting and the paired report. Calibration and
interface probes follow on committed source; source edits during a live job use a
separate worktree. All live experiments are serialized across both games and use the
existing WH3 ledger, capped at $25 total. The owner authorized the three steps; testing
1.0 and 1.1 is within that calibration work.

No benchmark acceptance or calibration result is claimed yet.
