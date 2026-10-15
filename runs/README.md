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
    battle/           One directory per `twwarhammer3 play` job, named
                      <policy>[-<model>]-v<version>-<scenario>-<date> (e.g.
                      commander-luna-v2-rand-322117462-20261013), with <job>.log beside it.
                      `play` and `stats --rebuild` record the name's `-v<version>-` (e.g.
                      v14, v1.2) as the results register's harness version.
    visual-probes/   Scripted recorder/camera/capture checks, with audits beside job folders
    reports/         Regenerated offline HTML/JSON reports and browser validation images
    launch-*/         `twwarhammer3 launch` logs, deployment records and UI tree dumps
    probe-*/, ...     Engine and frontend probes, the startup-skip evidence, and the first
                      battle jobs from before battle/ existed
    vanilla/          Scripts and scripting docs extracted from the game's packs, read when
                      probing the engine. Proprietary: never commit or copy them into Git.
```

New tracks get their own folder: `runs/<track>/<job>` for Slay the Spire,
`runs/<game>/<track>/<job>` for other games. A job directory holds what its runner wrote:
`manifest.json` with the source revision, file fingerprints and configuration;
`environment.json`; `system_prompt.md` for API-model policies; and one subdirectory per
run or episode with the raw trace and result. A Spire `run-NNNN/` is one game launch and
holds its game logs. A WH3 `episode-NNNN/` is one battle (its `mod.log` beside the trace);
the game is launched once per job, so `game.log` and `menu.log` sit in the job directory,
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
