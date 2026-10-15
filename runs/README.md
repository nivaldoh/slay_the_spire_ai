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
  first-combat/       Slay the Spire, frozen 2026-10-11 evidence: rollouts, evaluations,
                      catalogs, PPO and language training runs, their sidecar logs, audits
                      and declarations, and scripts/ with the one-off launch and summary
                      scripts that produced them.
  research-notes/     Source notes for docs/spire/approaches.md, kept out of Git.
  twwarhammer3/       Total War: WARHAMMER III
    llm-spend.jsonl   Its own spend ledger, shared by every `twwarhammer3 play` job
    battle/           One directory per `twwarhammer3 play` job, with <job>.log beside it.
                      Version jobs are <policy>[-<model>]-v<version>-<scenario>-<date>
                      (e.g. commander-luna-v2-rand-322117462-20261013); the version after
                      -v (15, 1.2) fills the results register's harness column. Other
                      names leave it blank, and `stats` groups them by source revision:
                      attack-... (the first scripted baselines), bench-b<N>-... and
                      bench-g1-... (benchmark screens and calibration), smoke-... (battle
                      types), probe-... (engine checks), visual-sol-low-20261015.
    visual-probes/    Scripted recorder, camera and capture checks (play jobs) and their
                      audits
    calibration/      Benchmark queue plans and their state files, logs, stop and
                      retirement decisions, and the untracked runners and audit scripts
                      that produced them (run-g1.py, audit-g1.py, ...)
    capability-probes/ Engine and UI probes with their scripts and outputs;
                      external-controllers/ keeps the outside controllers recorded trials
                      imported (ExternalHold, the flight probe)
    reports/          `twwarhammer3 report` outputs (HTML, JSON, text), browser checks, and
                      the old replay-demo generator; they predate the 2026-10-15 cleanup
    launch-*/         `twwarhammer3 launch` logs, deployment records and UI tree dumps
    probe-*/, ...     Frontend probes, the startup-skip evidence, the benchmark setup probe
                      and the first battle jobs from before battle/ existed
    vanilla/          Scripts and scripting docs extracted from the game's packs, read when
                      probing the engine. Proprietary: never commit or copy them into Git.
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
`army_player.txt` and `cards_slot<N>.txt` (the recruitment cards each army's race offered)
sit in the job directory,
and later episodes are rematches of the same battle. WH3 episodes can also contain
`replay.jsonl` (public 1 Hz frames), `unit_names.json`, `imagery.json`, `stills.json`
and `still-<battle>-<trigger>.png` presentation captures. Replay exports embed derived
public data and exact prompts; images never become policy inputs. Missing/throttled
captures and malformed recorder lines remain evidence rather than being reconstructed.

Records in `first-combat/` name their original `runs/<name>` paths; see
[docs/spire/first-combat/README.md](../docs/spire/first-combat/README.md#evidence-and-tools)
before re-evaluating or re-auditing them. Its two SFT jobs hold about 16 GB of
intermediate checkpoints (`checkpoints/*.pt`); the final adapters are under each job's
`artifacts/`.
