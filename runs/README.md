# Run evidence

Everything here except this file is local and ignored by Git. Evidence is never edited
after a job ends; summaries and audits are written beside a job, not inside it.

```
runs/
  llm-spend.jsonl     Slay the Spire's OpenAI spend ledger, shared by every `spire play` job
                      (ledger rules in AGENTS.md). Another game keeps runs/<game>/.
  fullrun/            Current track. One directory per `spire play` job, named
                      <model>-v<scaffolding>-<seed set>-<date> (e.g. llm-luna-v7-dev-20261012),
                      with its stdout and stderr beside it as <job>.log.
  first-combat/       Frozen 2026-10-11 evidence: rollouts, evaluations, catalogs, PPO and
                      language training runs, their sidecar logs, audits and declarations, and
                      scripts/ with the one-off launch and summary scripts that produced them.
  research-notes/     Source notes for docs/approaches.md, kept out of Git.
  twwarhammer3/       Total War: WARHAMMER III: llm-spend.jsonl (its own ledger), launch-*/
                      probe logs and UI tree dumps, and later battle/<job>/episode-NNNN/.
```

New tracks get their own folder (`runs/<track>/<job>`), and new games theirs
(`runs/<game>/<track>/<job>`). A job directory holds what its
runner wrote: `manifest.json` with the source revision, file fingerprints and
configuration; `environment.json`; and one subdirectory per run or episode with the raw
trace, result and game logs.

Records in `first-combat/` name their original `runs/<name>` paths; see
[docs/first-combat/README.md](../docs/first-combat/README.md#evidence-and-tools) before
re-evaluating or re-auditing them. Its two SFT jobs hold about 16 GB of intermediate
checkpoints (`checkpoints/*.pt`); the final adapters are under each job's `artifacts/`.
