# Proposed original-engine reset probe

Status: proposed on 2026-10-11; **not implemented or runtime-validated**. Run only
after the first neural pilot. The hypothesis is that returning to the main menu
inside one owned JVM can reduce reset time while preserving the existing first-
combat benchmark. This does not propose snapshots, a simulator, or faster combat
execution. The current `owned_jvm_restart_then_seeded_start` reset remains the
default and fallback.

## Evidence and limits

Targeted local inspection used engine build `10180494`, `desktop-1.0.jar` SHA-256
`cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`, and CFR 0.152,
SHA-256 `f686e8f3ded377d7bc87d216a90e9e9512df4156e75b06c655a16648ae8765b2`.
The exact installed mod hashes and separate source revisions are in
[integration.md](../integration.md). Decompiled files remain outside Git at
`/tmp/spire-metrics-audit/`; the following records findings, not proprietary code.

| Inspected path | Finding relevant to the proposal |
| --- | --- |
| Engine `CardCrawlGame.startOver()` / `updateFade()` | Starts a two-second global fade, then resets the dungeon and constructs a new menu; a two-second fade-in follows. The call itself is asynchronous. |
| Engine `AbstractDungeon.reset()` | Disposes the current room/monsters; clears action queues, rewards, effects, floor/act counters and score variables. |
| Engine `CardCrawlGame.updateFade()` | Clears seeds, trial/daily/endless/key flags and metric data; resets shop cost; refreshes unlocks; flushes profile-slot completion/playtime. It does not directly delete a live autosave or calculate death/abandon statistics. |
| Engine menu and dungeon constructors | The menu sets the player to null. A new start creates a fresh player, action manager and Exordium, rebuilding run lists/pools. Exordium normally writes the new Neow autosave. |
| Engine `DeathScreen` constructor | Actual death separately records statistics and deletes the autosave before returning to the menu. Calling reset after a combat win does not turn that win into a run death. |

The pinned [CommunicationMod return path](https://github.com/ForgottenArbiter/CommunicationMod/blob/5e417eb189530986b9047a3c9426889fb261d146/src/main/java/communicationmod/ChoiceScreenUtils.java#L870-L877)
already calls `startOver()` for game-over `PROCEED`.
Its [command executor](https://github.com/ForgottenArbiter/CommunicationMod/blob/5e417eb189530986b9047a3c9426889fb261d146/src/main/java/communicationmod/CommandExecutor.java)
checks command availability before dispatch, so a new trusted reset command
would need interception before that check. `START` reinitializes seeded RNGs
but does not explicitly clear `CardCrawlGame.loadingSave`; require it to be false.

The [state listener](https://github.com/ForgottenArbiter/CommunicationMod/blob/5e417eb189530986b9047a3c9426889fb261d146/src/main/java/communicationmod/GameStateListener.java)
reports menu readiness without waiting for the global fade timer. Its
`resetStateVariables()` also leaves the menu-presented latch and timeout intact.
Thus the existing ready flag alone cannot acknowledge this reset. Normal game
updates can continue during fade-out: arbitrary mid-action reset is outside scope.

This inspection does **not** establish cleanup of every engine/mod static field,
cache, subscriber, asynchronous save operation or retained reference. Repeated
same-JVM execution may expose state or memory leakage absent from a cold launch.
The existing two-loss/restart evidence in [mechanics.md](mechanics.md) uses fresh
JVMs and does not validate this proposal.

## Candidate protocol boundary

A small separate ModTheSpire patch could run on CommunicationMod's game update
thread and expose reset only to the trusted runner. It must never enter policy
observations, legal candidates, rewards, or PPO transitions. Preserve the current
engine action loop, Fast Mode, Upload Data setting, profile, prefix and scoring.

1. Persist and audit the completed episode before requesting reset. Require one
   acknowledged, settled benchmark terminal: prior combat followed by the same
   monster room `COMPLETE`, or actual engine `DEATH`. Require no command in flight
   and settled engine actions. Truncation, unsupported state, bridge error, or
   uncertain settling uses the unchanged JVM restart path.
2. Keep the owned JVM, relay and bridge connection alive under the runtime lock.
   Block intermediate states from reaching a new policy decision while resetting.
   Wait for a new menu, `CHAR_SELECT`, null player, and global `screenTimer == 0`;
   reset listener bookkeeping/timeout and emit exactly one completion response.
3. Give the next episode a fresh identity and reject old decisions, duplicate
   reset requests and stale responses. Send seeded `START` only after completion,
   then execute the existing prefix and initial intent-settling waits. The first
   combat observation must match the frozen suite fingerprint.
4. A reset timeout or disconnect invalidates the session. Preserve its evidence
   and cost; dispose the owned process, then use a fresh JVM and handshake for a
   separately recorded attempt. Do not reconnect to a possibly stale game or
   silently repeat a gameplay action.

No build or download accompanies this proposal. A later build can use a user-local
Java 8 JDK and the installed engine/MTS/BaseMod/CommunicationMod jars as compile
dependencies, packaging only new patch code and metadata. MTS and CommunicationMod
are MIT at the inspected pins; preserve notices for reused source. Keep proprietary
jars and decompiled code out of Git. The inspected local Java installation is a
JRE, so compiler availability is a separate preparation step.

## Bounded comparison and acceptance

Before execution, freeze source/configuration hashes, patch source and binary
hashes, engine/mod hashes, profile snapshot, command, and a candidate reset version
such as `owned_jvm_menu_reset_then_seeded_start-v1`. Use the existing
[development suite](../../configs/suites/louse_diagnostic_development_v1.json), public
observation contract and settled prefix. Keep this probe out of training data.

Proposed cap: **14 attempts and 10 minutes**, whichever comes first, with the
existing per-episode action/time caps. Stop at the first unexplained mismatch;
preserve it without retrying for a passing result. An incomplete budget-limited
probe leaves the proposal unverified.

- Run two cold-JVM references for each of two frozen action sequences: a known
  first-combat win and end-turn-only death. Pin their traces and action meanings.
- Run eight alternating win/loss episodes in one JVM, four of each. Validate each
  recorded action against the current legal candidates before sending it.
- Reserve two attempts for reset timeout/disconnect recovery and a fresh-JVM
  fallback. Unit-level fault tests must also cover duplicate reset, stale episode
  identity, and refusing reset from an unsettled or truncated episode.

Accept the gameplay-equivalence claim only if all repeated starts match the suite,
every normalized public transition and semantic legal-action set matches its cold
reference, and terminal outcome/health/turns agree exactly, including Burning Blood
healing and real death. Compare complete public observations with the existing
`normalized_observation_fingerprint`; trace timing and per-decision transport IDs
may differ outside that observation. Never add exclusions to conceal a mismatch.
Record profile snapshots before/after, including unlock changes, and investigate
any difference that could affect later starts. Do not restore profile files to
manufacture equality.

Measure reset-to-settled-combat time, combat time, total wall time, valid episodes
and transitions per second, failures, and process memory across repetitions.
Include initial JVM startup and recovery costs; report per-attempt timings as well
as aggregate throughput. Require a measured end-to-end improvement without failed
acceptance checks before considering adoption. This small probe cannot establish
long-run memory stability or equivalence outside the tested encounter/profile.

Any adoption requires a new reset protocol version and fresh random/heuristic
baselines and frozen-artifact evaluations under that version. Retain the old
results with their original protocol; never pool the two reset modes silently.
If any gate fails, leave the current JVM restart implementation and benchmark
unchanged and record the failed hypothesis.
