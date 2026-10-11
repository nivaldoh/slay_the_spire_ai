# Heuristic-relabeled state coverage for language SFT

Declared before exporting the final datasets, training, or evaluating the new adapter.
The first SFT adapter memorized 21 unique public prompts from one Louse trajectory.
This experiment changes only the training data: the same public heuristic labels
every audited public state that any non-language behavior policy visited on the same
Louse start. The question is whether broader state coverage within one encounter
family transfers the heuristic's decision rule to public starts absent from training.

## Data

`heuristic_relabel` sources (see [demonstrations.md](demonstrations.md)) accept any
complete, independently audited run whose observation code is a committed known
public implementation. The label is the current `StarterHeuristicPolicy` applied to
the recorded public Decision. The recorded behavior action stays in origin metadata
and never becomes model input. This is DAgger-style aggregation of exploratory states
under a fixed teacher, not imitation of the behavior policies.

Selection is a fixed rule over `runs/` (`scripts/export_relabel_datasets.py`), with
no outcome, return or policy-quality filtering. Include every complete audited run with a single public start. Exclude
language-policy behavior, incomplete runs and pre-settle `SPIREAI1` starts:

- **Train:** every run starting at the pinned settled `SPIREAI1` two-Louse start
  `177b2fcd…`. Behavior policies are random, PPO neural (training and evaluation),
  heuristic and end-turn. A trial export produced 1,868 rows with 811 unique prompts
  and 1,057 duplicate rows. Duplicates keep their separate origins, so training
  samples states by visitation frequency.
- **Offline test (`offline_evaluation`, test split only):** every other single-start
  run: Cultist `SPIREINV07`, Jaw Worm `SPIREINV09`, and four 88-HP inventory starts
  (`SPIREINV01/04/05/11`). The trial export produced 930 rows and 513 unique prompts
  across six public starts. None shares a game seed or public start with training.
  These runs are earlier development evidence; they are held out from this training,
  not an untouched final test.

The final exports run from the committed exporter after the language catalog queue
ends. That queue's runs are language behavior and are excluded by rule. The label
distribution is skewed: in training, Defend is 62%, Strike 18%, end turn 17% and
Bash 4% of rows. Always answering choice 0 agrees with 70.7% of training rows and
59.2% of test rows. Agreement must be judged against that trivial baseline.

## Training

Same pinned Qwen3-0.6B, LoRA (rank 8, alpha 16, q/k/v/o, dropout 0), completion-only
loss, seed 0 and learning rate 0.0002 as the first adapter. Only the data and its
budget change: batch size 16, **234 updates** (3,744 example occurrences, about two
passes over the rows), padded sequence length 784 (longest measured prompt 765
tokens; the trainer rejects longer examples and never truncates), at most 2,935,296
padded tokens and 3,000 seconds. No validation split exists, and no intermediate
checkpoint is selected. Export, resume and audit rules are unchanged
([language-training.md](language-training.md)).

## Evaluation

1. **Offline agreement** (`scripts/offline_agreement.py`): for the unchanged base,
   the first adapter and the new adapter, compute greedy agreement with heuristic
   labels on every unique test prompt and every unique training prompt. Report it by
   public start, as row-weighted and prompt-weighted values, with policy failures and
   a label-versus-choice table. No game runs, and weights are verified frozen.
   `--training-dataset` rejects any prompt, public-start or seed-family overlap.
2. **Catalog gameplay:** run the new adapter once on
   `starter-three-encounter-development-v1` (12 slots, existing decoding/parser,
   1,800-second process cap, no retry). Compare it with the first adapter and the
   heuristic on the same catalog. Report per-scenario wins over policy attempts,
   failures, HP and turns.

## Decision rule

Adopt the new adapter as the language track's supervised base if test-prompt
agreement exceeds both the first adapter and the choice-0 baseline, and its
Cultist + Jaw Worm wins over policy attempts are at least the first adapter's, with
no infrastructure or evidence failures. Otherwise keep the first adapter and record
the result as negative. Agreement cannot exceed the teacher. Perfect imitation
reproduces the heuristic, which scored 12/12 wins and macro HP 76 on this catalog.

Outcome-based post-training (policy-gradient or rejection-sampling updates on
original-engine combat results) is the next step only once a supervised base
reliably reproduces the teacher outside its training start. It requires its own
contract for the rollout unit, reward, token-level loss mask and compute budget.

## Limitations

One training seed, one encounter family in training, and duplicate-weighted data.
Labels are heuristic actions, not optimal play. Catalog repeats are correlated greedy
replays of three scenarios. The Cultist and Jaw Worm scenarios already informed
earlier development comparisons. This study cannot establish held-out encounter
generalization (milestone D) or Act 1 competence (milestone F).
