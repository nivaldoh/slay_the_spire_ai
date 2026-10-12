# Original-engine integration audit

Inspected 2026-10-11. This is evidence for the current bootstrap slice, not a
whole-game compatibility or simulator-equivalence claim.

## Runtime and source pins

The Windows Steam engine is build `10180494`, with `desktop-1.0.jar` SHA-256
`cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`.
The bundled Java actually executes as `1.8.0_144`; Windows Python executes as
`3.13.1`. The read-only doctor records fresh hashes, version probes, active
profile unlock information, resource availability, and setup blockers.

Runtime Workshop artifacts are copied to `C:\spire-agent\mods` and checked
against these hashes before launch:

| Artifact | Version | SHA-256 |
| --- | --- | --- |
| ModTheSpire.jar | 3.30.3 | `541b5e8a875d2a404a5a6d54f4a6f814284b0cf71acb9245239d9c5ef50ea604` |
| BaseMod.jar | 5.56.0 | `c3353c10e64c621b723e9fd7d0502dfa796f828b101b68513594a5f5ef83fbaf` |
| CommunicationMod.jar | 1.2.1 | `12b99249eccfd5245ddb0b6b7575e1a1dfba0ce0ed6fad5bd5bbd4a303897ef5` |

Source snapshots used for inspection are separately pinned; these are not a
claim that the Workshop binaries were reproduced from those revisions.

| Source | Inspected revision | License |
| --- | --- | --- |
| [ModTheSpire](https://github.com/kiooeht/ModTheSpire/tree/c6201995b8f5d97620cdb00f28a724a95b7742a6) | `c6201995b8f5d97620cdb00f28a724a95b7742a6` | MIT |
| [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod/tree/5e417eb189530986b9047a3c9426889fb261d146) | `5e417eb189530986b9047a3c9426889fb261d146` | MIT |
| [spirecomm](https://github.com/ForgottenArbiter/spirecomm/tree/f308452dcdef1e4813e5a78fa7a36f9a779058f9) | `f308452dcdef1e4813e5a78fa7a36f9a779058f9` (0.6.0) | MIT |

CommunicationMod and spirecomm source were inspected, not copied into the
project. No spirecomm strategy is part of the baseline.

CommunicationMod declares game version `11-30-2020`, whereas the installed
engine is the final 2022 build. The first launch successfully initialized all
three mods and produced live CommunicationMod state. This verifies the startup
path only; combat and reset claims require saved gameplay evidence.

## Protocol boundary

The [CommunicationMod protocol](https://github.com/ForgottenArbiter/CommunicationMod/blob/5e417eb189530986b9047a3c9426889fb261d146/README.md)
starts an external subprocess and waits for `ready` on its stdout. Messages in
both directions end with a newline. Stdout contains protocol messages only;
diagnostics go elsewhere. Windows runs a standard-library relay; WSL owns
policy selection and evidence collection. Loopback binding does not
make raw game state suitable for policy input.

- `START IRONCLAD 0 <seed>` operates from the main menu. It is a seeded full-run
  start, not an arbitrary combat reset. Reaching a fixed combat requires a
  declared noncombat prefix and a recorded combat-start state.
- `PLAY` uses a **one-based card index**. Monster target indices and potion
  slots are **zero-based**. Preserve raw target positions; removing dead
  monsters before numbering targets changes command meaning.
- `STATE` returns the current state even when unstable. A reply is not proof
  that the preceding gameplay action finished. Decisions require a stable
  command-ready state and must retain their observation/action identity. The
  mod has no command IDs or acknowledgments; permit one in-flight command.
- The mod may return an error object instead of a state. Timeouts, malformed
  messages, unsupported screens, and process failures are infrastructure
  outcomes; none should be counted as a gameplay loss.
- The raw draw pile iterates the actual internal ordered pile. Expose a
  canonical multiset without UUIDs. Drop the seed, current action, internal
  enemy move IDs/history/base damage, and unaudited reflected power fields.
  Retain damage/hit counts only for displayed attack intents.
- `GAME_OVER` includes unlock screens whose false victory value is a placeholder;
  only real death/victory screens prove run outcomes. Combat has no terminal
  flag: require prior combat followed by same-floor `COMPLETE` in a monster room.

The actual config path is
`%LOCALAPPDATA%\ModTheSpire\CommunicationMod\config.properties`.
`%APPDATA%` is the config fallback. Set `runAtGameStart=true` for unattended
launches; the default is false. Java properties escaping applies to `command`,
but its parser splits on whitespace without quote support. The relay executable
and script paths therefore need no spaces. Launch Java with
`-Dfile.encoding=UTF-8` for consistent stream encoding. The doctor reports
whether a command is present without printing its content or private profile
fields. Its success means readiness for a runtime probe; it never certifies a
handshake, completed combat, or reproducible reset from file presence.

## Metrics upload and profile effects

The first launch log, `C:\spire-agent\game-276144.log`, contains the loader's
successful `isModded` assignment at line 23 and the engine's own
`isModded=true` at line 93 (`2026-10-11 05:17:47.214` in that log).
[ModTheSpire's loader](https://github.com/kiooeht/ModTheSpire/blob/c6201995b8f5d97620cdb00f28a724a95b7742a6/src/main/java/com/evacipated/cardcrawl/modthespire/Loader.java)
sets the field; its `patches/IsModded.java` also preserves it during static
initialization.

Targeted inspection of the installed engine's `Metrics`, `Settings`,
`GameOverScreen`, `DeathScreen`, and `VictoryScreen` classes established:

- `Metrics.run()` skips both `UPLOAD_METRICS` and `UPLOAD_CRASH` when
  `Settings.isModded` is true. This is the decisive upload gate for this launch.
- Normal death submission also requires the Upload Data setting, initialized
  publisher integration, and a standard run. The engine's definition of a
  standard run excludes seeded runs, daily runs, and trials.
- `VictoryScreen` can start its metrics thread with Upload Data enabled; the
  `Metrics.run()` mod gate still applies.
- Steam leaderboard submission separately excludes modded, trial, and seeded
  runs. The observed Steam API initialization failure is additional context,
  not the justification for relying on the mod gate.
- Local run-history saving still executes. Unlock and profile changes remain
  possible and must be recorded as specified in [state.md](state.md).

The Upload Data setting was left unchanged. This audit supports disabled
engine run/crash metric uploads for this modded build; it is not a blanket
claim that the game or mods perform no network activity. Recheck after engine
or mod changes.

The audit used [CFR 0.152](https://www.benf.org/other/cfr/), SHA-256
`f686e8f3ded377d7bc87d216a90e9e9512df4156e75b06c655a16648ae8765b2`.
Extracted classes and decompiled output remain outside the repository at
`/tmp/spire-metrics-audit/`; no proprietary code or artifacts are committed.

## Acceleration candidates considered

[LudicrousSpeed](https://github.com/boardengineer/LudicrousSpeed/tree/0a24dd471ebd4f451923361eaaa922bc2c5e6880)
(`0a24dd471ebd4f451923361eaaa922bc2c5e6880`) and
[STSStateSaver](https://github.com/boardengineer/STSStateSaver/tree/00dbbcb7f1e67743797e4d7fb714cb899f7f2eaa)
(`00dbbcb7f1e67743797e4d7fb714cb899f7f2eaa`) were inspected but not adopted.
Neither inspected tree has a tracked license file; redistribution permission
was not established. Their build files target older engine/mod versions, so
compatibility with this setup is unverified.

LudicrousSpeed needs a custom controller and explicit initialization, replaces
the normal action loop, and skips effects/actions. STSStateSaver has save/load
APIs, but no CommunicationMod reset endpoint. Snapshots contain private RNG
and draw-order state and belong only on the environment side. Crucially,
`SaveStateMod.java` removes six potion types during startup: Gambler's Brew,
Liquid Memories, Smoke Bomb, Elixir, Cultist Potion, and Stance Potion. Loading
it unchanged would alter the benchmark's mechanics.

Keep the first experiment on the original action loop with the existing Fast
Mode setting and MTS launcher/intro bypasses. Measure seeded restart and combat
throughput before choosing acceleration. Any future snapshot/fast-execution
slice needs its own runtime compatibility and differential validation gate.

## Windows excluded-port regression

One frozen evaluation could not connect before gameplay: Linux selected port53899
from its ephemeral range, while Windows excludes TCP53849–53948. Native Windows
bind failed with10013 and relay connect logged10061. The runner now uses loopback
19876 under the existing exclusive ownership lock; TCP address reuse supports
consecutive clean episodes. Fifty Windows-to-WSL socket round trips passed. This
fix does not reconnect or retry commands within a game. A future local port
collision still fails instead of taking over another process.

Each launch now records the intended relay address and captures only the new suffix
of CommunicationMod's shared stderr log. See the preserved
[failure and probe evidence](first-combat/results/relay-startup-failure-audit.json). The policy
evaluation was restarted in a new directory with the same frozen artifact and
suite; earlier partial evidence remains invalid for a full-suite score.
