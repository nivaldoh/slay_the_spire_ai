# Terminal-Bench reference for benchmark content, checks and records

[Reference index](../benchmark-references.md). **Terminal-Bench** measures coding agents on
terminal tasks. The other profiles here are about how to build scenarios and scores; this one
is about how a benchmark repository organises its content, the checks on that content and its
results. It has no tactical or multi-agent content.

Repository: [harbor-framework/terminal-bench](https://github.com/harbor-framework/terminal-bench),
[licence](https://github.com/harbor-framework/terminal-bench/blob/cba65cd26f66fc022a8b3459d16c897ad722d1f2/LICENSE)
Apache-2.0. The program that runs agents is a separate package,
[Harbor](https://github.com/harbor-framework/harbor), which this repository installs and pins;
Harbor was inspected as a file listing only.

## What the repository holds

Read 2026-11-15 at
[`cba65cd26f66fc022a8b3459d16c897ad722d1f2`](https://github.com/harbor-framework/terminal-bench/tree/cba65cd26f66fc022a8b3459d16c897ad722d1f2)
(2026-11-14), the head of `main` on 2026-11-15 by `git ls-remote`; no release tag points
at it.

- `tasks/`: 66 task folders. Each has `instruction.md` (all the agent is told), `environment/`
  (all the agent is given), `solution/` (a reference solution), `tests/` (the grader, run in
  its own container), `task.toml` (configuration and version) and a `README.md`.
- `legacy/`: 90 task folders from earlier versions, in the older layout; 2 of them have a
  separate grader image.
- `scripts/checks/`: 29 check scripts with one rule each, and 64 deliberately failing fixture
  tasks: "Each folder fails exactly one check." By folder name, 22 of the 29 scripts have one.
- `leaderboard/`: one committed configuration per official run, one committed record per
  result, and one metric function shared by every tool that writes a score.
- `docs/`: four guides, the review rubrics and prompts.

Each task has a version whose level says what happens to earlier results: a change to what the
agent receives means "Run the agent again", a grader change means "Grade saved artifacts
again", and a metadata change means "Reuse previous results" (`CONTRIBUTING.md`, Task
Versioning and Changelogs). Every push to a task runs its reference solution, which must pass,
and an agent that does nothing, which must fail.

## Connections to WH3

These are connections to existing questions. They change no benchmark rule.

| Existing WH3 question | What this reference contributes |
|---|---|
| [Winnability evidence](../scenario-guidelines.md#winnability-evidence) | The same two controls for every task, run automatically: a reference solution that must pass and a do-nothing agent that must fail. Our battles take real time at 1x, so the automatic part does not transfer. |
| [Outcome and score](../benchmark.md#outcome-and-score) | One function computes the metric for every producer, and the rule for failed trials is written in one sentence. Its rule (errors count as failures) is a leaderboard rule; ours separates infrastructure failures from losses. |
| [Tracks and versions](../benchmark.md#observations-and-orders) | A three-level rule for whether earlier results must be replayed, can be re-read, or stand. |
| Hidden state ([Architecture](../../development.md#architecture)) | The grader runs in its own container and reads declared files, its own image and declared sidecar services. The reference solution and the grader are separate folders, so one cannot change the other. |
| [Checks of checks](../../workflow.md#checks-in-layers) | Failing fixtures for most checks, and a stated 100% catch rate for the model-run review, whose tested reviewer is the production reviewer. Close to our planted wrong versions. |

## Code to consult

| Pinned file | Entry points and use |
|---|---|
| [CONTRIBUTING.md](https://github.com/harbor-framework/terminal-bench/blob/cba65cd26f66fc022a8b3459d16c897ad722d1f2/CONTRIBUTING.md) | The task folder, `task.toml` fields, the version table and the changelog rules. |
| [docs/TASK_REVIEW_AUTOMATION.md](https://github.com/harbor-framework/terminal-bench/blob/cba65cd26f66fc022a8b3459d16c897ad722d1f2/docs/TASK_REVIEW_AUTOMATION.md) | What each static check enforces; the `WARN` and failure output contract; oracle and nop validation; cheat trials; regrading saved trials with a changed grader. |
| [scripts/checks/test-tasks/README.md](https://github.com/harbor-framework/terminal-bench/blob/cba65cd26f66fc022a8b3459d16c897ad722d1f2/scripts/checks/test-tasks/README.md) | Tables from the static, validation and analysis fixtures to the check each must fail and its local command; one shared command for the 34 rubric fixtures. |
| [scripts/rubric-regression/README.md](https://github.com/harbor-framework/terminal-bench/blob/cba65cd26f66fc022a8b3459d16c897ad722d1f2/scripts/rubric-regression/README.md) | `generate.py`: a model reviewer tested against planted failures, with an oracle and a nop run that test the plumbing without model calls. |
| [leaderboard/src/leaderboard/core/metrics.py](https://github.com/harbor-framework/terminal-bench/blob/cba65cd26f66fc022a8b3459d16c897ad722d1f2/leaderboard/src/leaderboard/core/metrics.py) | `compute_metrics` (accuracy and a per-task standard error), `compute_pass_at_k`, `submission_by_task` (disqualified trials joined as failures). |
| [docs/prompts/trial-analysis.toml](https://github.com/harbor-framework/terminal-bench/blob/cba65cd26f66fc022a8b3459d16c897ad722d1f2/docs/prompts/trial-analysis.toml) | Fixed questions asked of every trial: task specification, reward hacking, difficulty crux, near miss, refusals, low timeout; one more for cheat trials. |

## Limits that affect reuse

Its tasks are graded by a program on files the agent leaves behind, in containers that can be
rebuilt and run in parallel. A WH3 battle is graded by the engine, runs in one game window at
1x and cannot be replayed. Per-push oracle and nop runs, cheat trials and regrading through a
hosted service therefore do not transfer as built.

Its pipeline is made for many outside contributors: comment commands, labels and 21 GitHub
workflows. We have one owner and a local gate.

Its own duplicated statements have drifted where no check compares them. At this revision
`CONTRIBUTING.md`'s example sets `allow_internet = true`, which the check
`check-no-allow-internet-true` rejects, and three tracked files link to a `.claude/skills/`
file that is not tracked. The rubric regression workflow sits outside `.github/workflows/`, so
the tracked tree does not show its 100% rule running in CI.

One task was read in full (`wal-recovery-ordering`); the other 65, most check scripts and most
workflows were not. No task, check or Harbor command was run, and no published result was
reproduced. Statements about what its checks enforce come from its documentation. A comparison
of its layout with ours, with proposals that are unadopted and unverified, is in
`runs/terminal-bench-review-20261115/report.md`.
