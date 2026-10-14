# WH3 calibration and delay experiment plan

Declared 2026-10-14 before the new calibration candidates are played. Implements the
owner's first three next steps; progress/evidence are in
[benchmark-progress.md](benchmark-progress.md). The current acceptance job is a harness
check on one instance, not independent calibration data.

## Conditions kept fixed

- Original pinned Windows game, one controller at a time, unpaused 1x throughout.
- Explicit map, factions, units and player role; setup checks must pass on every trial.
- Very-hard tactical AI. The stat modifier is a separate declared factor: 1.0 or 1.1,
  set in the lobby and checked again in battle. Record starting unit stats privately to
  compare actual values, not just the preference or the preview text.
- Controller order randomized within each launch, with its seed and actual order saved.
  Rematches share an instance; fresh launches supply the independent sampling unit.
- Freeze a committed implementation before each experiment. Never pool across source
  revisions, scenario definitions or builds. A necessary fix starts a new comparison.
- A finite lobby timer shorter than the old 60 minutes will be selected only after its
  actual duration is read back. The episode wall cap exceeds it by at least 120 s.
  Engine outcomes at the timer stay `time_limit` in the benchmark report.

## Acceptance and inexpensive screening

Owner update, 2026-10-14: specialist challenges and faction-specific anchor units now
guide candidate selection; see [scenario-recipe.md](scenario-recipe.md). Complete the
already running Herald modifier screens and objective probes as diagnostics, then
screen cavalry/anti-large and caster-led prototypes before choosing the G1 candidate.
The unstarted 36-battle Herald draft plan is superseded. No G1/G2 trials have been played.
The original Herald design and its results below are retained as development evidence.

Finish the five-controller b1 job, including the imported external controller. Then
validate the new modifier setter/read-backs, coarse terrain and reachable alternatives,
and reject a deliberately misspelled recruitment card before scoring. Test the updated
interface with one Luna trial; all subsequent scripted experiments have no API cost.

The first candidate family is ranged protection: a Dwarf army with shooters against
fast Slaanesh flankers. The original Sigvald version has now lost with hold, Luna and
skills on the acceptance instance. The fallback replaces only Sigvald with the
selectable Shadow Herald. `dwf-sla-herald` and `dwf-sla-herald-hard` differ only in the
1.0/1.1 setting. Their rosters and a held-out Nurgle-wastes map are already declared in
the b2 branch. Do not use the held-out variant for choosing the lord, army strength,
timer or controller behavior.

Screen with one launch per development candidate, rotating `hold`, `attack_nearest`
and `skills`. This chooses difficulty, not a winner: a floor or ceiling calls for a
recorded roster/settings adjustment and a new named development variant. If this family
cannot separate the controllers, examine the existing settlement objective family and
its building-capable scripted baseline. Do not declare success from a single battle.

## G1: calibration

Once a specialist candidate has an intermediate difficulty and working required controls,
declare its competent reference and play six fresh launches per modifier, three
controllers once per launch: `hold`, `attack_nearest`, and that reference. `skills` is
the default when it can express the required tactics; a specialist task may use a
declared LLM, hybrid or specialist script instead. Freeze the choice before G1, not after
viewing its repeated results. Record rotation seeds `2026101401` through
`2026101406` for 1.0 and `2026101411` through `2026101416` for 1.1. The modifiers are
separate strata; matching a rotation seed would not make two launches the same instance.

Admission requires both:

1. The declared competent reference wins before the timer roughly 30–70% (2–4 of 6),
   counting timer endings as valid trials without including them in this decisive-win
   measure. Preserve and report the engine's result at the timer: a defender's timeout
   win is a legitimate game win, but does not satisfy this initial admission criterion.
2. That reference beats both trivial controllers on active-strength margin, with each paired
   instance interval above zero. This tests the better of the two trivial baselines.

Report outcomes, uncertainty, failure denominators, paired differences, protected-unit
survival, ownership/supplies where applicable, rejections, timings and throughput. Raw
surviving men and routing-adjusted strength both remain available; neither weights unit
value. These are development calibration results, not held-out model rankings. If
admission fails, recalibrate the development scenario; keep the failures in the record.

## G2: controlled information age

On the admitted scenario/settings, six fresh launches rotate the same competent reference at added ages
0, 6 and 10 s, using rotation seeds `2026101421` through `2026101426`. Natural latency
remains included. The original buffered snapshot supplies the order's basis sequence;
the engine clock supplies total information age at issuance. Initial buffer-fill time
is part of the declared condition. No pausing or slowing is allowed.

The primary contrast is 10 s minus 0 s active-strength margin. A 95% paired interval
below zero establishes sensitivity at that delay. The 6 s contrast is secondary and
exploratory. Otherwise report the interval and approximate detectable difference;
do not conclude that latency has no effect. Report decision rates as well as ages to
check the intended mechanism, and keep delay arms separate from ordinary live results.

## Completion evidence

The runbook must let another developer substitute a controller and obtain an auditable
paired report. Final evidence must include live acceptance, a refused broken setup,
modifier and terrain probes, admitted calibration (or continued development until one
is admitted), completed delay trials and their limits, preserved held-out variants,
tests, the committed results register/log and an updated session state. Large-model
comparisons, broader battle-type coverage and offensive sieges are later work; adding
siege attackers would require their gate/wall/equipment interface before admission.
