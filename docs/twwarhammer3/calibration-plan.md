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

Completed acceptance includes the five-controller b1 job with an imported external
controller, modifier setter/read-backs, coarse terrain and reachable alternatives,
a deliberately misspelled recruitment card rejected before scoring, and Luna trials.
The specialist candidates also need their particular flight/spell controls checked.
Any selected API reference uses the existing cumulative $25 WH3 ledger cap; its model,
effort and prompt are frozen with the experiment.

The earlier candidate family was ranged protection: a Dwarf army with shooters against
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

Starting-condition review before G1 (b4 development evidence): one cavalry rematch
flagged a 4.826 m missile-cavalry displacement and a 12-degree enemy-lord bearing change
at 5.3 s versus the reference's 5.2 s. Rosters, strength, loadouts and resources matched.
The game is already live at these snapshots; identical trajectories are not promised.
Keep the existing 1 m/10-degree flags and include every valid trial in the primary
comparison. Report flagged trials and their deltas explicitly, and give a secondary
paired comparison omitting launches with a flagged start. Do not replace such launches
or stop a queue solely for a geometry flag. A changed roster, strength, loadout or
resource stops subsequent jobs for investigation; retain its started trials and do not
silently pool a changed task. Freeze this handling with the candidate before G1.

Once a specialist candidate has an intermediate difficulty and working required controls,
declare its competent reference and play six fresh launches per modifier, three
controllers once per launch: two declared trivial baselines and that reference. `skills` is
the default when it can express the required tactics; a specialist task may use a
declared LLM, hybrid or specialist script instead. Freeze the choice before G1, not after
viewing its repeated results. Record rotation seeds `2026101401` through
`2026101406` for 1.0 and `2026101411` through `2026101416` for 1.1. The modifiers are
separate strata; matching a rotation seed would not make two launches the same instance.

Baseline amendment before G1, b8 development review (2026-10-14): on the cavalry
attacker, hold lost at the 1200 s timer with both armies intact. Its raw strength
margin is zero despite failing the objective, so it is an objective-failure control
rather than a useful tactical margin comparator for this role. Keep its screening
trials and engine outcomes. For this attacker family, the two G1 baselines are now
`attack_nearest` (walk) and `rush_nearest` (run); the latter changes only the run flag,
with no flanking, abilities or target priorities. It needs a live screen before G1.
Other families still default to hold/attack-nearest unless separately declared.
This changes neither the raw margin nor the admission threshold below; it replaces
the inactive comparator before any G1/G2 data are collected. The six launches per
modifier, rotation seeds and held-out separation remain unchanged.

### Frozen cavalry calibration (2026-10-14, after b9 screening)

The selected development family is `brt-cavalry-emp-assault` / `-hard`: six Bretonnian
cavalry units versus eight Empire units, the original foot general, 8000 funds cap,
1200 s timer, Taurox map, player attacking, very-hard tactical AI and modifiers 1.0/1.1.
The matching Nurgle-wastes held-out variant remains unplayed. Exact rosters/settings
are in the committed scenario definitions; setup checks run on every trial.

The reference is now frozen as `llm_rules`, `gpt-6-sol`, effort `low`, with the existing
rules-only prompt, actions, memory and natural inference latency. The b7 pilot won by
flanking the obstruction, breaking the ranged line and concentrating on the general.
Luna low and medium lost both modifier screens; medium sometimes chose useful targets
but did not establish competence. Sol's one win motivates this reference choice, not
admission or a measured intermediate win rate. G1 will establish those repeated results.
No prompt, roster or controller tuning will occur during G1 or G2.

Run the 12 launches above, alternating modifiers and rotating
`attack_nearest,rush_nearest,llm_rules` once per launch. Use `--episodes 3`, added age 0,
`--start-timeout 900 --episode-timeout 1320 --run-timeout 5400 --budget-usd 25 --show`.
The local frozen plan is `runs/twwarhammer3/calibration/g1-cavalry-plan.json`; it records
the full committed revision and driver hash before launch. All model calls share the
existing ledger ($6.3723 before G1); its cumulative $25 cap remains in force. An
infrastructure or resource/loadout failure stops later jobs for investigation, retaining
the started trials. Geometry flags alone do not stop it. No early stopping or reference
replacement based on gameplay outcomes is planned.

Evaluate admission separately per modifier. If both pass, select 1.1 for G2; if only
one passes, select that setting. If neither passes, record failure and continue
scenario development. G2 keeps the same reference/source and uses the previously
declared six rotation seeds. These are development comparisons, not held-out rankings.

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
The requested age is a minimum: observations read into the buffer can be farther apart
when synchronous model calls take time. Report the actual snapshot age at decision
alongside total age at issuance; do not describe these arms as exact 6/10 s delays.

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
