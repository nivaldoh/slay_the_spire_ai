# Run evidence

Everything here except this file is local and ignored by Git. Evidence is never edited
after a job ends; summaries and audits are written beside a job, not inside it.

```
runs/
  llm-spend.jsonl     Slay the Spire's OpenAI spend ledger, shared by every `spire play` job
                      (ledger rules in AGENTS.md)
  fullrun/            Slay the Spire full-run track. One directory per `spire play` job,
                      named <model>-v<scaffolding>-<seed set>-<date> (e.g.
                      llm-luna-v7-dev-20261012), with its stdout and stderr beside it as
                      <job>.log.
  spire-openrouter-spend.jsonl  Slay the Spire's OpenRouter ledger (`spire play --provider
                      openrouter`); independent of the OpenAI cap
  fullrun-exports/    `spire export` datasets: decisions.jsonl, sources.json, datacard.md
  sft/                `python -m gameai.sft` datasets (both games) and their smoke-test
                      outputs; tokenizers/ holds pinned tokenizer files of student models
  first-combat/       Slay the Spire, frozen 2026-10-11 evidence: rollouts, evaluations,
                      catalogs, PPO and language training runs, their sidecar logs, audits
                      and declarations, and scripts/ with the one-off launch and summary
                      scripts that produced them.
  research-notes/     Source notes for docs/spire/approaches.md, kept out of Git.
  twwarhammer3/       Total War: WARHAMMER III
    llm-spend.jsonl   WH3 OpenAI spend ledger
    openrouter-spend.jsonl  WH3 OpenRouter spend ledger; independent of the OpenAI cap
    battle/           One directory per `twwarhammer3 play` job. A job started by hand has
                      <job>.log beside it; a queued job (scripts/wh3_queue.py) usually logs
                      to its plan's .log under calibration/ instead.
                      Version jobs are <policy>[-<model>]-v<version>-<scenario>-<date>
                      (e.g. commander-luna-v2-rand-322117462-20261013); the version after
                      -v (15, 1.2) fills the results register's harness column. Names
                      without a -v<N>- part leave it blank (bench-b13-glm-v20-... and
                      bench-b40-...-v21-... record 20 and 21), and `stats` groups those by
                      source revision: attack-... (the first scripted baselines),
                      bench-b<N>-..., bench-c1-... and bench-g1-... (benchmark screens and
                      calibration), smoke-... (battle types), probe-... (engine checks),
                      visual-sol-low-20261015.
    visual-probes/    Scripted recorder, camera and capture checks (play jobs) and their
                      audits
    calibration/      Benchmark queue plans and their state files, logs, stop and
                      retirement decisions, and the untracked runners and audit scripts
                      that produced them (run-g1.py, audit-g1.py, ...)
    capability-probes/ Engine and UI probes with their scripts and outputs;
                      external-controllers/ keeps the outside controllers recorded trials
                      imported (ExternalHold, the flight probe)
    reports/          `twwarhammer3 report` outputs (HTML, JSON, text), including the
                      canonical benchmark report and historical reports/demo generator
    report-checks/    Offline browser validation screenshots, downloads and copied reports
    exports/          Offline model-decision datasets: decisions.jsonl, sources.json and
                      a data card, plus selection lists and verification scripts/reports
    checkpoint-check-*/ Agreed battle-checkpoint checks: source/, restore-a/, restore-b/,
                      changed/ (agent log in native/, plan, manifest), checks.json and the
                      checkpoint replay itself
    rl/               Checkpoint RL (docs/twwarhammer3/checkpoint-rl-plan.md): plans/ (the
                      phases' JSON plans), stage1-*/ (the step-run check: checkpoints/<root>/
                      with source/ and one <tick>/record.json + replay per save, restores,
                      injected attempts, checks.json), audits/<name>/ (attempt-NNNN/ step runs
                      and table.json), tasks/ (task sets), runs/<name>/ (update records,
                      adapters with their declarations, eval-*.json), confirms/<name>/
    launch-*/         `twwarhammer3 launch` logs, deployment records and UI tree dumps
    probe-*/, ...     Frontend probes, the startup-skip evidence, the benchmark setup probe
                      and the first battle jobs from before battle/ existed
    vanilla/          Scripts and scripting docs extracted from the game's packs, read when
                      probing the engine. Proprietary: never commit or copy them into Git.
    <topic>-<date>/   Agents' review, research and away-window folders (e.g.
                      eval-guidelines-review-20261020, army-controls-20261019,
                      away-20261021): findings, check outputs and the scratch scripts
                      that the pages and log entries citing them rest on
  test-scratch/       pytest --basetemp scratch (see tests/README.md);
                      disposable (1.7 GB in 121 folders on 2026-10-28, a cleanup candidate;
                      inventory in judgement-batch-20261028/test-scratch-inventory.txt)
  uv-cache/           uv's package cache
  autonomy-<date>/    Reviews and checks behind docs/autonomy.md
  <topic>-<date>/     Cross-game reviews, research and away-window work (e.g.
                      judgement-sweep-20261023, overnight-20261028, thesis-forecast-20261028,
                      interview-evidence-20261028): scripts, outputs and reviews that the
                      pages citing them rest on
```

New tracks get their own folder: `runs/<track>/<job>` for Slay the Spire,
`runs/<game>/<track>/<job>` for other games. A job directory holds what its runner wrote:
`manifest.json` with the source revision, file fingerprints and configuration;
`environment.json`; the prompt of each API-model policy (WH3: `<base policy>_prompt.md`,
where single-policy jobs recorded before the 2026-10-15 cleanup, `visual-sol-low-20261015`
included, wrote `system_prompt.md`); and one subdirectory per
run or episode with the raw trace and result. A Spire `run-NNNN/` is one game launch and
holds its game logs. A WH3 `episode-NNNN/` is one battle (its `mod.log` beside the trace);
the game is launched once per job, so `game.log`, `menu.log`, `map_list.txt`,
`army_player.txt` and, in jobs from `8434cd3` (2026-10-15) to before `e32b1b5` (2026-10-20)
that listed their units, `cards_slot<N>.txt` (the recruitment cards each army's race offered)
sit in the job directory,
and later episodes are rematches of the same battle. WH3 episodes can also contain
`replay.jsonl` (public 1 Hz frames), `unit_names.json`, `imagery.json`, `stills.json`
and `still-<battle>-<trigger>.png` presentation captures. Replay exports embed derived
public data and exact prompts; images never become policy inputs. Missing/throttled
captures and malformed recorder lines remain evidence rather than being reconstructed.

Since WH3 harness b14 and Spire `87b370b` (2026-10-17), traces also contain
`model_exchange` events with exact API request bodies and returned output items, including
failed calls and late commander replies.
WH3's [offline exporter](../docs/twwarhammer3/traces.md) joins them to orders, acknowledgements
and outcomes. Historical gaps are labelled; source jobs and spend ledgers stay unchanged.

Records in `first-combat/` name their original `runs/<name>` paths; see
[docs/spire/first-combat/README.md](../docs/spire/first-combat/README.md#evidence-and-tools)
before re-evaluating or re-auditing them. Its two SFT jobs hold about 16 GB of
intermediate checkpoints (`checkpoints/*.pt`); the final adapters are under each job's
`artifacts/`.
