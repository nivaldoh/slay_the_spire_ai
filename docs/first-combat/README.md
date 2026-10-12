# First-combat benchmark (2026-10-11, paused)

The project's first day built and verified the original-engine loop on fixed floor-1
combats, then compared scripted, PPO and local language-model policies there. All of it is
paused: the owner paused PPO on 2026-10-11 to advance language-model post-training, and on
2026-10-12 moved to [full runs with an API model](../fullrun/README.md). This page is the
summary. The files beside it are the detailed records, written as the work happened.

Code: `spire.combat`, `spire.ppo`, `spire.language`, plus `src/spire/protocol.py` and
`src/spire/policies.py`. Evidence: `runs/first-combat/` (local) and [results/](results/).

## The benchmark

- Ironclad, Ascension 0. Each attempt owns a fresh JVM, sends a seeded `START` from the main
  menu, takes a fixed Neow/map prefix (max HP, else exactly 100 gold; leftmost first-floor
  node) and settles the initial `DEBUG` intents with a logged `WAIT 60`. No arbitrary
  combat snapshot or reset exists.
- Observation contract `ironclad-starter-combat-v1` (`spire/protocol.py`): allowlisted
  public state, the draw pile as an unordered multiset, starter cards only, no potions.
- Single-scenario suite [louse_diagnostic_development_v1](../../configs/suites/louse_diagnostic_development_v1.json):
  two Louses on `SPIREAI1`, normalized start SHA-256 `177b2fcd…`, eight attempts.
- Three-scenario catalog [starter_three_encounter_development_v1](../../configs/suites/starter_three_encounter_development_v1.json):
  the Louses, Cultist `SPIREINV07` and Jaw Worm `SPIREINV09`, four policy seeds each.
  Admitted from an original-engine inventory and exact repeat traces.
- Only an engine-confirmed win or death is a gameplay outcome. `spire report` rebuilds every
  score from the saved evidence rather than a run's own summary.

## Results

Two-Louse diagnostic, eight attempts per policy on one game scenario:

| Policy | Wins | Mean final HP |
| --- | ---: | ---: |
| Uniform random | 8/8 | 68.00 |
| Starter heuristic | 8/8 | 77.00 |
| Initial neural policy | 8/8 | 72.75 |
| PPO pilot, 2 updates | 8/8 | 72.75 |
| PPO budget-64, 12 updates | 8/8 | 72.00 |
| Qwen3-0.6B, unchanged | 0 completed (8 invalid outputs) | — |
| Qwen3-0.6B, Louse SFT LoRA | 8/8 | 77.00 |

Three-scenario catalog, 12 attempts per policy; macro HP weights the scenarios equally:

| Policy | Wins | Macro HP | Louses | Cultist | Jaw Worm |
| --- | ---: | ---: | ---: | ---: | ---: |
| Heuristic | 12/12 | 76.00 | 77 | 71 | 80 |
| Random | 10/12 | 42.00 | 70.25 | 36.75 | 19 |
| Initial neural | 8/12 | 37.25 | 61.5 | 24.75 | 25.5 |
| Budget-64 neural | 9/12 | 35.67 | 60.25 | 21 | 25.75 |
| Qwen3-0.6B, unchanged | 0/12 (all invalid) | — | — | — | — |
| Louse SFT LoRA | 12/12 | 76.33 | 77 | 74 | 78 |
| Heuristic-relabel SFT | 12/12 | 63.67 | 77 | 41 | 73 |
| Relabel SFT + 1 REINFORCE update | 12/12 | 66.67 | 77 | 50 | 73 |

Sources: [baselines](results/baselines-development-v1.json),
[PPO pilot](results/ppo-pilot-development-v1.json),
[PPO budget-64](results/ppo-budget64-development-v1.json),
[language SFT](results/language-sft-development-v1.json),
[four-policy catalog](results/starter-three-encounter-development-v1.json),
[language catalog](results/language-catalog-development-v1.json),
[relabel](results/language-relabel-development-v1.json) and
[REINFORCE](results/language-rl-development-v1.json). Figures: [figures/](figures/).

## What was learned

- **The loop is trustworthy.** Seeded restarts reproduce the normalized start, fixed-action
  replays match transition for transition, and infrastructure failures stay separate from
  losses. Three engine defects were found and fixed on the way: unsettled `DEBUG` intents,
  a relay port inside Windows' excluded range, and localhost relay startup (now the direct
  WSL address). See [integration.md](../integration.md) and
  [relay-startup-mitigation.md](relay-startup-mitigation.md).
- **PPO did not learn to play.** The 12,498-parameter actor-critic updated every weight,
  but stayed nearly uniform (mean final entropy 0.999 of the maximum) and fell below random
  on catalog HP. A tenfold learning-rate run was declared and never launched.
- **Language SFT transfers outcomes more than the rule.** Louse-only SFT on 21 unique prompts
  matched the heuristic's catalog HP (76.33 against 76.00), but matched only 36 of 50
  heuristic decisions on the two unseen families. Relabeling more states raised held-out
  agreement to 75.2% yet lowered macro HP to 63.67; one REINFORCE update recovered 3 points.
- **The floor-1 catalog saturates.** The heuristic wins 12/12, so HP is the only signal.
  Claims about training need harder or held-out scenarios first.
- **Engine time dominates.** About 38 s per combat, mostly animation and JVM restarts; see
  the engine-speed section of [approaches.md](../approaches.md).

Against the milestones in section 10 of the [agent guide](../agent-guide.md): A (a working
original-engine loop) and B (a fixed-encounter diagnostic with baselines) are verified, C
(a learning loop) is verified computationally without a gameplay improvement, E (language
weight training) is verified narrowly, and D and F are incomplete.

## Open threads, if this track resumes

1. The stopped continuation's two-update adapter is unevaluated:
   `runs/first-combat/language-rl-relabel-continued-20261011/iteration-000/policy.json`
   (SHA-256 `7870257b…`). Evaluate it once on the catalog with the frozen greedy evaluator
   and compare with 63.67 (base) and 66.67 (one update).
2. The language track's next question awaits the owner: more REINFORCE iterations, RL from
   the stronger Louse-only adapter, or held-out scenarios first.
3. The PPO learning-rate experiment needs a new declaration; the launchers in
   `runs/first-combat/scripts/run_ppo_*.py` predate the package layout and their clock
   gate has expired.
4. Branch `integration/heldout-clip-continuation` holds three reviewed, unmerged commits:
   a PPO clipping-fraction diagnostic, held-out evaluation purpose propagation, and a
   bounded two-combat continuation (764 CPU tests passed there). It predates the package
   layout, so it needs a rebase before merging.
5. Declare held-out evaluation and the smallest noncombat expansion before collecting either.

Limits of everything above: starter cards only, no potions or noncombat policy, Neow
prefixes other than max HP or 100 gold unsupported, no snapshots or live combat resume.

## Evidence and tools

`runs/first-combat/` holds every run directory, the sidecar CLI logs, audits, configs and
declarations, and the one-off launch and summary scripts in `scripts/`. It moved there from
`runs/` on 2026-10-12. Records inside still name `/home/niv/repos/slay_the_spire_ai/runs/<name>`;
`spire report` and the evidence regressions work without them, but evaluating a frozen
language declaration or replaying a path-following audit needs the old paths back, as
temporary links:

```bash
for d in runs/first-combat/*/; do ln -s "first-combat/$(basename "$d")" runs/; done
# ... evaluate or audit ...
find runs -maxdepth 1 -type l -delete
```

Compact results in [results/](results/) also record paths from before the move
(`docs/results/…`, `runs/<name>`).

`spire/protocol.py` and `spire/policies.py` are frozen: demonstration export compares their
syntax tree with the recorded teacher sources, so editing them breaks that verification.

```bash
# Seeded first-combat episodes, a frozen suite evaluation, and an offline re-audit.
uv run python -m spire rollout --policy heuristic --episodes 2 --output runs/first-combat/heuristic-example
uv run python -m spire evaluate --policy random \
  --suite configs/suites/louse_diagnostic_development_v1.json --output runs/first-combat/random-dev
uv run python -m spire report runs/first-combat/random-dev runs/first-combat/heuristic-example

# Budgeted PPO; resume keeps the original absolute deadline, optimizer, RNGs and consumed episodes.
uv run --extra train python -m spire train --suite configs/suites/louse_diagnostic_development_v1.json \
  --output runs/first-combat/ppo-example --episodes 8 --batch-steps 64 --updates 2 --time-budget 900 --seed 0
uv run --extra train python -m spire train --resume --output runs/first-combat/ppo-example
uv run --extra train python -m spire evaluate --checkpoint <exported-policy.json> \
  --suite configs/suites/louse_diagnostic_development_v1.json --output runs/first-combat/ppo-eval

# Figures, with the external renderer they were verified on (Python 3.13.5, Matplotlib
# 3.11.0, NumPy 2.3.3, Pillow 12.3.0); SVGs are byte-reproducible, PNGs stay in runs/.
/home/niv/miniconda3/bin/python scripts/plot_results.py \
  --comparison docs/first-combat/results/ppo-budget64-development-v1.json \
  --distribution docs/first-combat/results/ppo-budget64-distribution-diagnostic.json \
  --gradients docs/first-combat/results/ppo-budget64-gradient-diagnostic.json \
  --output docs/first-combat/figures --png-directory runs/first-combat/diagnostic-figures
```

`evaluate --suite` also takes schema-2 catalogs and `--language-artifact` declarations;
see [catalogs.md](catalogs.md). Scripts:

| Script | Purpose |
| --- | --- |
| `scripts/inventory_scenarios.py` | Bounded original-engine scenario inventory (launches the game) |
| `scripts/audit_ppo_training.py` | Independent audit of a stopped PPO run |
| `scripts/audit_language_training.py` | Independent audit of a stopped SFT run |
| `scripts/export_relabel_datasets.py` | Heuristic-relabel train and test datasets from saved runs |
| `scripts/train_language.py`, `scripts/train_language_rl.py` | SFT and REINFORCE drivers (CUDA environment) |
| `scripts/offline_agreement.py` | Greedy agreement of a language artifact with the heuristic |
| `scripts/plot_results.py` | Figures from saved results (external Matplotlib environment) |

PPO code and tests run with `uv run --extra train`; language-model code with
`uv run --locked --extra llm` (CUDA torch; the two extras conflict). Qwen3-0.6B weights are
cached under `~/.cache/spire-models`.

## Records in this folder

| Record | Contents |
| --- | --- |
| [research.md](research.md) | Every experiment contract and decision, in order |
| [mechanics.md](mechanics.md), [inventory-mechanics.md](inventory-mechanics.md) | Original-engine mechanics fixtures and their regressions |
| [scenario-expansion.md](scenario-expansion.md), [inventory.md](inventory.md) | Encounter coverage review and the inventory that admitted the catalog |
| [catalogs.md](catalogs.md) | Schema-2 catalog format, scoring and frozen language policies |
| [learning.md](learning.md) | The PPO network and learner |
| [demonstrations.md](demonstrations.md) | Audited public-action demonstration export |
| [language.md](language.md), [language-training.md](language-training.md) | Local model choice, environments and the SFT runner |
| [language-experiment.md](language-experiment.md) | First SFT diagnostic and its result |
| [language-catalog-experiment.md](language-catalog-experiment.md) | Language catalog comparison contract |
| [language-relabel-experiment.md](language-relabel-experiment.md) | Heuristic-relabel SFT contract |
| [language-rl-experiment.md](language-rl-experiment.md) | REINFORCE post-training contract |
| [relay-startup-mitigation.md](relay-startup-mitigation.md) | Direct WSL-address relay evidence |
| [reset-probe.md](reset-probe.md) | Proposed in-JVM reset probe, never run |

Some records describe work as planned or not yet launched; [research.md](research.md) and
this page give the outcomes.
