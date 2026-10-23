# WH3 repeatable battle situations

Owner direction, 2026-10-22: use checkpoints and controlled randomness for benchmarking
and training situations; research a small implementation and repeatable checks first.
The first deliverable is one chariot situation that can be reproduced and handed to a
controller. A complete battle checkpoint with restored engine RNG remains unverified.
The methods and acceptance rules below are **proposed, not yet agreed**.

## What we can preserve

Three different capabilities matter:

| Capability | Meaning | Current evidence |
|---|---|---|
| Complete checkpoint | Restore the simulation, RNG state, clock and pending work at a chosen moment | No documented API found |
| Replayed situation | Load a fixed initialization, repeat an opening, then change controller | Rematch exists; persistent replay and takeover need live checks |
| Authored situation | Respawn or place units with declared damage and ammunition | Several setters exist; this reconstructs a task rather than its combat history |

The installed-reference audit covered 49 battle HTML pages, 2,111 documented functions
(including libraries) and 548 UI contexts. The shipped army serialization functions save
unit type/identity and aggregate health. Loading applies casualties to fresh units; it
cannot restore an earlier battle. In one Lua 5.1 component experiment, saving 75 men,
damaging to 50 and loading left 25; loading onto a fresh 100 left 75. These are simulated
unit APIs, not live effects. Evidence: `runs/twwarhammer3/rewind-20261022/`, especially
`api-audit.json`, `health-roundtrip.json` and `findings.json`.

`math.randomseed` seeds Lua's generator. `bm:random_number` calls the separate native
battle generator; its documented interface has no seed/state setter. Our `--seed` picks
random-scenario maps and factions, not engine randomness. Even when an initialization is
repeatable, different actions may consume random draws differently. Call this a shared
initialization; claim restored RNG only if we establish an actual restoration mechanism.

The native replay tool inspected at `eb3042e` recognized one installed autosave and
calculated seven control-field changes in memory. It switches the selected participant
at loading, not at a chosen battle time. The original file stayed unchanged. Neither
game loading nor takeover has been tested. Exported battle XML describes setup; whether
it contains a useful initialization seed is also untested.

## First establish a usable reset

Use `grn-chariot-emp-swordsmen-hard`, scripted orders, no paid model, unpaused at 1x.
Proposed cap: 45 minutes of game ownership for this feasibility pass, at most ten battle
loads across the two routes below. Save logs and stop on the cap or a harness refusal.
Build only the diagnostic code each route needs on a local branch. This planning change
runs no game and changes no benchmark result or verification agreement.

**First try native replay because it could preserve an initialization across launches.**
Record one short reference opening with observations before contact and after melee has
caused damage. Preserve its native `.replay` under ignored `runs/` before another battle
overwrites the autosave. Fix the two observation times before any comparison.

1. Load that same file three times across two game-process launches. Compare the prefix
   through the later observation, including orders originally issued through Lua. A replay
   that omits our script's orders fails this route.
2. Try two contrasting scripted takeovers at the earlier, unobstructed point. Put a known
   later order in the source recording: after takeover, that order must not regain control.
   Check movement from subsequent positions as well as acknowledgements. Use a separate,
   explicit replay diagnostic switch; keep ordinary replay sessions inert.
3. Continue only if all three prefixes match, both takeovers visibly command the correct
   unit and the later recorded order stays suppressed. A successful byte conversion alone
   satisfies none of these requirements. Stop this route after the reference and five
   comparison loads if it fails; record the first mismatch or control conflict.

**If native replay fails, try a scheduled opening through rematch.** Use the remaining
four loads for three identical openings and one deliberate change. Send the entire opening
to Lua before it runs. Execute it with battle-model callbacks and the existing order
executor; WSL polling must not decide when individual opening orders apply.

Record both the absolute battle clock and the `Deployed` origin, plus the native model
tick interval. The documentation says the interval is 100 or 200 ms; read it in game.
The current mod's 250 ms callback is a separate sampling/application interval. Matching
milliseconds is insufficient if callback order differs: create and replay the reference
through the same application hook, preserving order within each batch. Refuse missed
ticks rather than catching up several commands at once. Do not silently shift the time
origin to hide a different deployment.

A matching rematch opening establishes only repeatability within that launch. Without a
way to reload its initialization later, it can support local paired experiments but not
a persistent benchmark checkpoint. If neither route repeats contact and casualties,
stop the checkpoint implementation and use separately declared authored situations.
Respawn, health transfer or a Lua seed must not conceal a failed reproduction check.

## Build one small implementation after the probe

Implement whichever route passes; use the existing job, episode, mailbox and result
lifecycle. Start with one unit, move/attack/halt orders and one fixed fork time. The
opening is a fixed script; controllers first act at the fork with fresh memory and the
same public observation. This defines a situation task. Restoring arbitrary controller
memory or reproducing full-controller history can be a later, separate requirement.

Keep one situation JSON file containing:

- The resolved scenario and references/hashes for its source job and initialization file.
- The application clock, tick interval, ordered opening batches and chosen fork time.
- Expected start/prefix/fork observations, field precision and required readbacks.
- The reset method and honest RNG status: uncontrolled, opaque replay initialization,
  or restored engine state only if demonstrated. Include an explicit seed only if its
  effect has been established.

Native files remain local evidence. A missing or changed initialization file must refuse
the trial. Record the game's build, mod/source fingerprints and situation hash using the
existing provenance machinery. A build warning still follows the owner's current rule:
record and report it; its old repeatability evidence does not transfer to the new build.

Likely code changes are one `battle/checkpoints.py` module for loading/comparing the
situation, a small Lua opening driver if needed, and narrow integration in `play.py`,
`__main__.py` and the mailbox session contract. Begin with a diagnostic runner; add a
`play --situation FILE` option only after the route passes. Reuse `apply_order` and order
validation. Do not build a backend framework around unproven alternatives.

The episode has three stages: opening, comparison, ordinary live control. No controller
decision, acknowledgement callback or model request runs during the opening. At the fork,
save the observation once with the existing atomic publisher, keyed by job and battle.
The latest-observation mailbox can overwrite a transient fork before Python reads it;
retain this one snapshot until consumed and include it in reset cleanup. The first policy
decision uses that snapshot while the game continues at 1x; its full observation age is
recorded. Later decisions use the ordinary loop. Compare the declared state before
exposing it. A mismatch ends as a setup failure with
the first changed field; it is not a controller loss. Then retire the opening driver,
reject any leftover opening request and resume the existing acknowledgement loop. There
must be one order writer at a time. Controller thinking after the fork still takes real
time. An already ending battle never starts a controller.

Record opening time, controller time and total wall time separately. An applied queued
order means submission to the engine queue; its future execution remains ordinary game
state. Do not cancel such a queue invisibly when changing controllers. A situation either
declares that queue or chooses a fork without one.

## Proposed checks

Use the recorded script and native game readbacks as references. In the probe, sample
every model tick around contact and the fork. Compare discrete fields and application
ticks exactly; compare numeric values at their declared capture precision. Missing
required data fails the check. Keep the first mismatch, not only a summary hash. Matching
accessible fields demonstrates measured repeatability, not equality of hidden RNG or
per-soldier state. The existing start comparator's 1 m/10 degree thresholds are too loose
for this claim; reuse its field extraction where suitable, not those tolerances.
Ignore transport identities such as job, battle and request IDs when comparing physics;
preserve unit identities, targets, order sequence and model times.

| Check | Observable requirement and reference | Deliberately wrong behavior it must detect |
|---|---|---|
| Opening schedule | Lua applies the declared batches, unit IDs and targets in order at the recorded model times | One-tick shift, wrong unit/target, duplicate or skipped batch |
| State comparison | Start and prefix witnesses agree through contact and damage; required fields include phase/time, positions, bearings, men/HP, targets, state, relevant ammo/cooldowns/resources and visibility | Change HP, delete a required field, reorder identities or shift the clock; every mutation must be reported |
| Takeover | After the fork, the correct unit visibly follows the new command and later opening/playback commands cannot reassert control | Acknowledged but unapplied order, replay override, simultaneous writers |
| Controller input | Fresh controller receives the preserved fork observation despite later mailbox updates; no calls before the fork, public fields only; alter private evidence and compare delivered inputs | Hidden checkpoint fields in a prompt, overwritten fork, warm-up model calls, memory carried from the preceding trial |
| Refusal and cleanup | Wrong source/initialization, missed tick, replay error, early engine ending and interruption leave evidence and no running opening callback | Falling back to an ordinary battle, consuming a stale fork/request after rematch, losing an engine ending |

Add focused cases to one `test_wh3_checkpoints.py` and existing play/mailbox tests, using
the real Lua driver under Lua 5.1. Test the contract rather than copying its implementation
into a fake driver. Existing fake-game tests cannot establish live command effects.

After implementation, run `uv run --locked pytest -ra tests/twwarhammer3/test_wh3_checkpoints.py
tests/twwarhammer3/test_wh3_play.py tests/twwarhammer3/test_wh3_mailbox.py` and
`uv run --locked ruff check .`. Put test scratch files under `runs/`. One live checker
should perform the selected route's repeated-load and takeover checks, including the
later-order trap. Record actual clock progression against wall time; the mod's constant
`speed: 1` field cannot independently detect a paused/slowed battle.

Once the one-situation check passes, check a second chariot opening from a separate
initialization. Freeze its case and acceptance fields before running it. Only then extend
to other units or orders. Add an AGENTS.md verification row only after the owner agrees
the concrete method; record revisions and counts whenever it passes.

## Use in benchmarks and training

Admit a situation with its reset method, measured repeatability and initialization
identity. Keep situation results distinguishable from complete battles. Preserve engine
outcomes, existing card success rules and all failed resets; choosing a fork does not
change what counts as a win. Report paired differences within each initialization,
controller delay, failure rate and trials per wall hour. Repeats and different forks
from the same initialization are correlated, not independent battle samples.

For training, first collect two scripted alternatives from an accepted fork, followed by
the same continuation controller. Use the existing trace/export path, recording the
situation, initialization, fork, action window, continuation, elapsed battle time and
terminal/truncation status. A training transition must cover the time to the next policy
decision, including inference delay; do not invent a fixed-duration step. Opening orders
are environment preparation, not student actions. Extend the export only when that
consumer exists; serving a trainable policy still depends on [posttraining.md](../posttraining.md#missing).

Keep a complete scenario family and all related initializations/forks in one data split.
Evaluate learning on fresh initializations and complete battles as well as repeated
training situations. [Go-Explore](https://arxiv.org/abs/2004.12919) supports the value of
returning to useful states and separately testing robustness; it establishes no WH3 gain.
Shared random inputs can reduce comparison noise, but [Wright and Ramsay](https://doi.org/10.1287/mnsc.25.7.649)
show that they need not do so. Measure the benefit rather than promising variance
reduction from one seed. No training algorithm, paid sweep or benchmark replacement is
needed to establish the reset capability.

## References

- Installed documentation and shipped libraries: [integration.md](integration.md#finding-another-capability).
- CA [battle clock, timers and native RNG](https://chadvandy.github.io/tw_modding_resources/WH3/battle/battle.html),
  [army serialization](https://chadvandy.github.io/tw_modding_resources/WH3/battle/script_unit.html#function:script_units:serialise_state),
  and [Lua randomness](https://chadvandy.github.io/tw_modding_resources/WH3/battle/lua.html#function:math:randomseed).
- Community replay tool [inspected source](https://raw.githubusercontent.com/WozniakP/WH3-Replay-Player-Switcher/eb3042e41e91e79357bf7c334ccf46f53816c62d/wh3_replay_switch.py).
- ALE's [explicit RNG-inclusive cloning](https://ale.farama.org/v0.11.2/release_notes/)
  illustrates the distinction between saved game state and saved RNG; it is not a WH3 API.
