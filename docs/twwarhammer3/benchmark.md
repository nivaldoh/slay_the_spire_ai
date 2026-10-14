# A latency-aware battle benchmark for WH3

Written 2026-10-14 from the owner's brief,
[WH3_latency_aware_benchmark_requirements.md](WH3_latency_aware_benchmark_requirements.md).
The analysis below describes the pre-implementation state. Current implementation and
live evidence are in [benchmark-progress.md](benchmark-progress.md), the executable
contract in [benchmark-run.md](benchmark-run.md), and the declared experiments in
[calibration-plan.md](calibration-plan.md). Admission and latency results remain pending. Three reviewers checked a
first draft against the code and the run records, three more critiqued the idea itself
(validity, statistics, scope), and two audited the rewrite. Their corrections are folded
in.
- Part 1 is the analysis the brief asks for.
- Part 2 is the definition.
- Part 3 is one concrete scenario, with what a short setup probe in the game showed.
- Part 4 is whether the idea makes sense, and what to decide.

Evidence paths under `runs/` are local and not in Git.

## Summary

The acceptance question, from the brief:

> Can an independent user evaluate a different battle controller under the same declared
> scenario, information, action, and timing rules, and understand both its performance
> and the limitations of the comparison?

**Where the harness stands.** For someone working inside this repository, it is close.
It already has:
- unattended setup and live control through the mod;
- engine-reported outcomes;
- rematches that restart the same battle in about 20 s;
- a trace of every decision that carried orders.

Still missing:
- a scenario that is fully pinned and checked (one fixed battle silently changed maps);
- a way to plug in a controller without editing the CLI;
- a report with denominators and intervals.

**Does the idea make sense?** Yes, as a reproducible benchmark of real-time tactical
control. Each controller is measured with its whole latency, network included, because
real deployments pay it too (owner, 2026-10-14). Three things are not shown yet:
- **That latency changes outcomes on any scenario.** It has never been varied with
  everything else held fixed. The only test, pausing the battle during inference, found
  no effect, but three battles per arm could only have detected a very large one.
- **No scenario played so far shows competent control beating trivial play.** On
  `kho5-dwf5` the trivial `attack_nearest` won 4 of 5, as often as `skills` and the
  commander, while the `llm` won 17 of 33. Every other scenario was lost by nearly every
  controller. That includes the random draw behind the scenario proposed here: it was
  lost in all three earlier launches, and `hold` lost the one finished battle on its
  frozen version.
- **Credible comparisons are expensive in machine time.** Small designs, such as 5
  instances with 2 trials per controller, could only detect gaps of about 45-50 win-rate
  points. A 20-point gap needs up to 36 paired instances: 15-18 hours of game time per
  scenario, about 8-14 on average with sequential stopping. Using wins alone it would need
  about 100 battles per controller.

**Recommended next step.** The only API cost is one `llm` battle (a few cents) in M1's
acceptance job:
1. **A lean M1**: a setup gate, controller rotation with plug-in by import path, a report,
   and the delay line G2 needs.
2. **Two gate experiments on Part 3's scenario**, about 6 instances each:
   - calibration: does one of `hold`, `attack_nearest` and `skills` win 30-70%, and does
     `skills` beat the better of `hold` and `attack_nearest` on the paired margin?
   - latency sensitivity: does `skills` get worse when its information is made 6 or 10 s
     old? That shows whether the scenario can reveal latency differences between
     controllers.

Their results decide whether to build the rest, and which scenarios can show latency
effects.

**Later: robotics models.** The owner wants to test robotics models eventually. A
vision-language-action (VLA) model needs a visual track: a screenshot with each
observation, beside the existing text (2.3, 2.6).

## Part 1. Where the repository stands

### Requirements against what exists

Status: **confirmed** means verified in the game or measured in the records, and
*(code)* marks a property read from the source. **Partial** means present with a stated
gap, **missing** means absent, and **uncertain** means it needs an in-game check.

| Brief | What exists | Status |
|---|---|---|
| §1 Two armies, no campaign | Custom battles against the game AI (`battle/play.py`, the Lua mod) | confirmed |
| §1 Any controller design | `hold`, `attack_nearest`, `skills`, `llm` and `commander` share `decide`, `acknowledge` and `metadata` | confirmed *(code)*. In-process only; a new controller means editing the CLI |
| §1 Small reliable path first | Classic land battles only | confirmed |
| §2 Observation contract | Shape in `engine/mailbox.py`, rules in [README.md](README.md). Messages carry `schema: 1`, which never changed while fields were added; the contract has no name | partial |
| §2 Update timing | Published on the mod's tick, which fires every 300 ms of battle time. That means every 1.2 s, and at the tick that applies each batch, empty ones included. A controller that answers within a tick sees a new observation every 0.3 s; the newest file wins | confirmed |
| §2 Privileged enemy state | Enemy units appear only while `is_visible_to_alliance` holds and `is_hidden` does not (`is_hidden` itself is unverified). Their positions, men and health are exact, and the whole enemy roster's unit types come from the lobby | partial: filtered by visibility, numerically exact, not player-equivalent |
| §2 Scoring data kept out | `final` is published only with the result, after the last decision. Unseen-enemy information still leaks in three small ways (below) | partial |
| §2 Action meaning, targets, persistence | `move`, `attack`, `halt`, `behaviour`, `ability` and army `ability`; queued moves and attacks; rechecked by the engine ([integration.md](integration.md)) | confirmed |
| §2 What the game still does itself | Pathfinding, retargeting, fire at will and skirmish (both on by default where supported), melee responses, morale | partial: documented piecemeal |
| §2 Basic orders vs. helpers | The harness has no helpers. The `skills` executor, used by `skills` and `commander`, is one | confirmed *(code)*; no disclosure format |
| §2 No setup, debug or scoring powers as actions | Orders are limited to the five types. But any process that can reach the bridge directory can write `menu.json`, whose steps (UI clicks, context expressions) the battle script runs | partial, by convention |
| §2 Invalid orders visible | A batch that fails `validate_orders` is replaced by an empty request; the refusal goes to the trace but not to the controller. The engine rejects single orders with an error code in the acknowledgement. Both add to one `invalid` count. No harness refusal has happened yet, so every recorded `invalid` is an engine rejection | partial |
| §3 Battle continues during inference, 1x, no pause | `require_realtime` rejects paused or faster sessions, and the mod sets 1x at deployment. The observation's `speed` and `awaiting_orders` are constants, so checking them proves nothing. Battle time did track the system clock and the API server's timestamps | confirmed by measurement; not checked per episode |
| §3 What happens while busy | One request in flight; a blocking controller sees only the newest observation when it next reads | confirmed *(code)*, not declared |
| §3 Wall clock vs battle time | Battle clock: `time_ms`, `applied_ms`, `delay_ms`. Wall clock: `think_s`, `roundtrip_s`, trace `elapsed` and model call seconds, all from WSL's `time.monotonic()`. That clock ran slow: battle time, the system clock and the API server ran 0-11% ahead of it | partial: wall durations understated by up to 10%; no absolute read time |
| §3 Captured, requested, returned, delivered, applied | Captured: `time_ms`. Returned: `think_s`. Applied: `applied_ms`, at the mod's tick. When the mod read the request is not logged | partial |
| §3 Command took effect | The acknowledgement means "issued to the engine"; execution is not observed | missing |
| §3 Information age at application | `delay_ms` per batch: `applied_ms` minus the basis `time_ms`, both on the battle clock. For the commander, `plan_age_s` on the decision that adopts a plan; the executor's later orders have no link to their plan | confirmed (direct), partial (hybrid) |
| §3 Decision rate, stale decisions | Decisions are counted. A stale reply is applied as it is, with its basis recorded | partial |
| §3 Controlled added delay | Not built; delay injection is listed in [controllers.md](controllers.md) | missing |
| §3 Paused evaluation kept apart | Pausing was removed; the three paused episodes are labelled `paused` | confirmed (excluded by the owner) |
| §4 Battlefield | Pinned only when the scenario names a map. Otherwise the lobby keeps the map of the last started battle (drift below) | partial (defect) |
| §4 Forces | Explicit units in `scenarios.json`. Factions are pinned only since `61c5f7f` (16:26 UTC on 2026-10-13); random draws still leave them to the game | partial |
| §4 Starting arrangement | The map's default deployment. The harness ends deployment at 4.7 s, and the first observation, at 5.2 s, records the result. `teleport_to_location` is documented but untried | partial; arrangement uncertain |
| §4 Opponent settings | The AI stats modifier, realism and unit size are in each job's `environment.json`, and the 3600 s timer can be recovered from `remaining_ms`. Difficulty and funds were never recorded; the probe read them back for the first time | partial |
| §4 Objective, episode limits | Engine victory. The 3600 s wall-clock episode timeout starts 15-30 s before the battle loads and runs on WSL's slow clock, so at the recorded drift the game's 3600 s timer would usually end a battle first, recorded as won or lost. No battle has come near either limit (the longest took 1226 s) | partial |
| §4 Small capability suite, dev and held-out split | None | missing |
| §4 Known start, unattended reset | 65 rematches in 32 jobs, all unattended except the first. About 17 s to the new battle and 21 s to its first observation after deployment. Restarting an undecided battle is untried, yet today's loop already sends `restart` after a `policy_failure` or `truncated` episode | confirmed / uncertain |
| §5 Authoritative outcome | `battle_outcome_decided` and `victorious_alliance` at VictoryCountdown | confirmed |
| §5 Outcome classes | `won`, `lost`, `draw`, `truncated` (wall clock), `policy_failure`, `budget_exhausted`, `infrastructure_failure` (also any controller exception other than `PolicyFailure`, and exhausted API retries), `unsupported_or_invalid`, `interrupted`. A game-timer ending would be recorded as won or lost | partial |
| §5 Valid-trial and reliability denominators | The register gets a row only when an episode returns. Three episodes stopped by the operator and one job stopped before its first battle are missing; `stats --rebuild` gives 118 rows where the register has 116 | partial |
| §5 Secondary measures | `results.csv`: length, true strength left, decisions, invalid, delay, USD. Tokens only in `result.json` | partial |
| §6 Current LLM controller as a baseline | `llm` v14 and `commander` v2 run from committed source | confirmed |
| §6 Non-LLM reference | `hold`, `attack_nearest`, `skills` | confirmed |
| §6 Matched comparisons | The same random seeds in separate launches. In all three seeds the commander's launch had different factions | partial |
| §7 Versions and configuration | Manifest (revision, file hashes, pack hash, build pins); `environment.json` (preferences, hardware) | confirmed |
| §7 Model identity | Requested alias and response ids; the model id the API returns is not stored | partial |
| §7 Observations, commands, timestamps, errors | `trace.jsonl` keeps the observations that started logged decisions, plus the first, roster and result ones: 8-50% of those published. Quiet decisions of fast policies are thinned | partial |
| §7 What the controller knew | Prompt and basis observation for each logged decision | confirmed |
| §7 Rerun and recompute | `stats --rebuild` recomputes the register from `runs/`; reruns are by hand | partial |
| §8 Provider-independent tasks | Scenarios and the mailbox know nothing about models | confirmed *(code)* |
| §8 Natural vs. imposed endings | Engine result vs. the wall-clock `truncated` | partial |
| §8 Throughput | Not reported. From the records: 8.1 episodes an hour (below) | missing |

### What the existing records show

**The register.** [results.csv](results.csv) holds 116 episodes, all ending with an engine
result: 39 won, 77 lost, 3 of them paused. It leaves out what did not return:
- three episodes the operator stopped (`llm-luna-v13-kho` episode 1,
  `skills-v1.1-random-s2-smoke` episode 0, `llm-luna-v10-kho-pinned` episode 1);
- one job stopped before its first battle (`skills-v1.2-rand-264482191`).

No episode in `runs/` ended in an infrastructure failure.

**A rematch restarts the same battle instance.** In 30 of the 32 jobs with a rematch,
every rematch started exactly where the first episode did: friendly and visible enemy
positions to 0.1 m and bearings to 1°. The two exceptions are the only episodes whose
deployment ended one 100 ms step later, at 4.8 s instead of 4.7 s, so their first
observation came at 5.3 s. In it, one unit stood 0.1 m away (`attack-m3`) and a lord had
turned 12° (`llm-luna-v12-kho`, episode 2). The snapshot depends on when the wall-clock
autostart fires.

**A new launch builds a different instance.** Among launches with the same factions:
- friendly units differ by up to 5 m and lord bearings by up to 48° (`kho5-dwf5`, 14
  launches);
- the AI's visible units differ by up to 2 m in three fixed scenarios, 146 m in the Khorne
  mirror, and 3-72 m in random draws.

Fixed scenarios left the faction to the game until `61c5f7f`. `kho5-dwf5`'s enemy was the
Ancestral Throng until then and the Dwarfs afterwards. Whether the engine's random seed
changes between launches is unverified.

**The engine replays a battle exactly when orders land on the same ticks.** In
`skills-v1.2-kho` (six episodes, five rematches):
- Episodes 0, 4 and 5 were identical at every logged time up to 530.7 s, and all won with
  0.10 vs 0.09 left.
- Episode 1 based its third batch on a later state (61.3 s instead of 61.0 s) and its
  fourth on an earlier one (72.7 s instead of 73.6 s). It diverged from 74 s and won at
  323 s.
- Episodes 2 and 3 each had one batch applied one tick later (253.6 s instead of 253.3 s,
  and 74.8 s instead of 74.5 s). They diverged from 255 s and 78 s, and episode 3 lost.

In `attack-b2`, episodes 0 and 2 were identical throughout (346.1 s, 0.45 vs 0.33).
Episode 1 had one batch land a tick later (251.5 s instead of 251.2 s) and ended 2.4 s
earlier, with 0.40 vs 0.29.

How it happens: the mod reads `orders.json` in a 200 ms wall-clock poll and applies the
orders at its next tick. The tick is a model-time callback set to 250 ms; it fires every
300 ms because the engine's clock advances in 100 ms steps. Wall-clock timing decides
which observation a decision starts from and which tick its orders reach, and a
difference of one tick (0.3 s) can change the battle. The script API also has a
"battle-synchronised" random number generator (`battle:random_number`), which fits a
deterministic simulation.

**The fixed `kho5-dwf5` battle changed maps.** That scenario names no map:
- Every launch up to 20:26 UTC on 2026-10-13 put the lord at (-208, 35), on "An Ogre's
  Folly".
- At 21:24 a random draw (seed 255179936) was played on
  `battle_preset_wh3_nur_wastes_01_04`.
- The next three `kho5-dwf5` jobs (`skills-v1.2-kho`, `commander-luna-v1.2-kho`,
  `llm-luna-v13-kho`) put him at (-50, -170). Their deployment zones match that draw's.

The lobby keeps the map of the last started battle, so the [log](log.md)'s late `kho5-dwf5`
comparison (`skills` 5/6, `commander` 5/6) was very likely played on the Nurgle wastes map.
Those jobs recorded no map.

**Autogenerated armies matched across launches except once, when the factions changed.**
Seeds 2, 2028855463, 255179936 and 322117462 gave identical rosters in every launch, and
Nurgle got the same army in 8 launches over 3 seeds and 3 maps. On seed 1202868312 the
player got 13 units in one launch and a different 12 in two others. In that launch the
game had also picked other factions. In all three paired seeds the commander's launch had
a different faction pair, for example Karak Kadrin against the Masque of Slaanesh on
322117462.

**Wall-clock durations are understated.** WSL's `time.monotonic()` times `think_s`,
`roundtrip_s`, trace `elapsed` and model calls, and it ran slow. Battle time, the system
clock and the timestamps in OpenAI's response ids ran 0-11% ahead of it (median 8%):
4.5-11% in the jobs through 16:26 UTC, and 0-4.5% from 19:40 UTC. Battle time agreed with
the system clock (median deviation 0.4%) and with the server, so the game ran at 1x.

**Throughput.** Jobs of three or more episodes played 84 unpaused episodes in 10.35 hours:
8.1 an hour, with battle time 83% of wall time. A completed one-episode job takes a median
409 s for a 317 s battle; 91-108 s go to launch, setup and shutdown.

**Unseen-enemy information leaks in three small ways:**
- A friendly unit's `target` is the engine's current target even when that enemy is out
  of sight. This happened in 20 logged observations in 10 episodes.
- The roster marks a unit seen earlier as `dead` when it dies out of sight.
- An attack on a unit that died out of sight is answered `target_dead`, not
  `target_not_visible`.

**The margin can contradict the outcome.** `own_left` minus `enemy_left` counts men in
routing and shattered units as alive. Its sign is opposite to the engine's outcome in 16
of the 108 real-time battles that recorded it: 13 wins with a negative margin and 3 losses
with a positive one. One more win had a margin of exactly 0.

**Information age by controller.**
- `llm` v14, over 185 batches: median 6.0 s, 90th percentile 9.2 s, maximum 19.2 s.
- `skills` and the commander's executor: 0.3 s, one tick.
- The Luna commander's plans: a median 6.0 s old when adopted, and 3.3-8.4 s for 80% of
  642 plans.

### Checked in the game for this analysis

A setup probe (`runs/twwarhammer3/benchmark-probe-20261014/`, Part 3) settled these:
- **Explicit 12-unit armies** can be recruited by card id without waiting for each card to
  read as visible. All 24 double-clicks found their cards. Legendary lords use the race's
  main faction key with `:1`, for example
  `wh_dlc01_chs_cha_prince_sigvald_the_magnificent:wh3_main_sla_slaanesh:1`.
- **Lobby settings can be read back** with `expression` steps on `CcoFrontendRoot`,
  through `CustomBattleLobbyContext.SettingsContext`:
  - `MapContext.Name` = "Dread Crossing – Quest Battle", a localized name; the selected
    map key is in the map list dump;
  - `MapContext.BattleTypeString` = `land_normal`;
  - `TimeLimitSeconds` = 3600;
  - `DifficultyLevelSettingContext.Key` = `ai_level_very_hard`;
  - `FundTypeSettingContext.Key` = `funds_large`;
  - `LocalBalanceOfPowerPercent` = nil.
- **Battle facts can be read back** with expression steps on `CcoBattleRoot`:
  - `PlayerAllianceContext.IsDefender` = true, `WillWinOnTimeout` = true and
    `TimeoutWinningAllianceIndex` = 0. **The player defends and wins if the timer runs
    out.**
  - `UnitSize` = 0.75; realism, lab mode, multiplayer and replay are all false.
  - `BalanceOfPowerPercent` = 0.51 at 61 s. The UI documentation describes it as a value
    "to show" the player how much they are winning, presumably the HUD's balance bar.
    Keeping it out of `obs-v1` is a choice.
  - `BattleNameText` is empty in a custom battle.
- **The first rematch restarted the same start.** The `attack_nearest` episode, which the
  owner stopped at 262 s, started exactly where `hold` did.

The AI stats modifier was not read back. The lobby also has its own AI stat slider, which
was never read.

### What is missing

1. **A pinned, checked scenario.** Today a missing map or faction is skipped silently, and
   so is a missing race when the army is autogenerated; the different battle is still
   scored. A missing unit card stops the setup only because of a 15 s wait that M1
   removes, so the gate must catch it.
2. **Matched comparisons and outside controllers.** That means rotating controllers across
   rematches in one launch, and plugging one in without editing the CLI.
3. **A report** with denominators, intervals, paired differences and a statement of
   limitations.
4. **Record fixes**:
   - pass the refusal reason to the controller;
   - store the model id the API returns;
   - register every started episode;
   - take wall times from a clock checked against battle time;
   - store the provider's processing time per call, so network and queueing time can be
     told apart from inference.
5. **A margin that agrees with the outcome** (routing units counted as lost) and exists at
   every ending.
6. **Evidence that latency matters** on a given scenario.
7. **A calibrated scenario**: one that some controller wins roughly 30-70% of the time,
   and on which `skills` beats the better of `hold` and `attack_nearest`.
8. **A visual observation** for vision models, robotics VLAs among them (later, owner
   direction): a screenshot beside the structured text (2.3).

### What still needs an in-game check

| Question | Why it matters | Probe |
|---|---|---|
| Does `battle_unitcontroller:teleport_to_location(pos, facing, width)` work during deployment, for both armies, with enemy units handed back to the AI by `release_control`? | Declared starting arrangements, for example for disengagement | A battle-script hook that teleports units from `session.json` at `Deployed`; compare the first observation with the request |
| Does restarting an undecided battle work (the `RestartBattle` fallback in `restart()`)? | Any ending without a result: a controller failure, a stall, an imposed limit | `hold` with a short limit, then `restart` |
| Does a new launch reseed the engine, or only change the deployment? | Whether launches are independent samples | Two launches of one scenario with `hold`; compare trajectories |
| Is a faction within a race only cosmetic? | The one autogenerated roster change came with a faction change | One instance per faction; compare rosters and unit stats |
| Does the visibility filter match what a player sees? | Labelling the observation honestly | Screenshots against observations at fixed times (owner present) |
| Does the custom-battle HUD show the balance bar? | Whether `BalanceOfPowerPercent` is player information | One screenshot in battle |
| Which value applies: the lobby's AI stat slider or the preference? | The opponent's strength, and G1's 1.0 arm | Set both, read the slider back at setup |
| Can the sides be swapped? `button_swap_attacker_defender` was found in a dump but never clicked | Roles, and swapped-side variants | Click it in the lobby, then read `IsDefender` in battle |
| How long does an order take to show its effect? | Turning "issued" into "took effect", with an uncertainty | Recorded moves: first observation showing movement toward the destination |

## Part 2. The definition

### 2.1 Terms

| Term | Meaning |
|---|---|
| scenario | A declared battle setup with its expected settings: an entry in `configs/twwarhammer3/scenarios.json` |
| variant | A scenario with one declared change (map, armies, sides), as its own entry. The unit of held-out evaluation |
| instance | The battle the game builds from a scenario in one launch, identified by the job. Every rematch restarts it from the same start, and the start fingerprint reports any difference (flagged above 1 m or 10°); the battle that follows can differ |
| trial (episode) | One controller playing one instance once |
| track | A named observation contract, action contract and timing policy, such as `obs-v1/act-v1/live-1x` |
| family | A set of scenarios that test the same capability (2.2) |
| controller | Code that turns observations into orders, with a recorded disclosure (2.6) |

### 2.2 Scenarios

A benchmark scenario is an entry in `configs/twwarhammer3/scenarios.json`, in the format
`play.scenario_steps` reads, plus three fields:
- `expect`: the values the setup gate checks;
- `protected`: the unit keys behind a family measure;
- `content`: the DLC packs the scenario needs.

The git revision versions it, since `scenarios.json` is part of the job's source
fingerprint. Part 3 has a full example.

**The setup gate** (M1). Any mismatch stops the job before a battle is scored, naming the
mismatch:

| Check | Source |
|---|---|
| Every menu step found its component | No `not found:` line in `menu.log`. Today a missing map or faction is skipped silently, and a missing unit card fails only because of the 15 s wait that M1 removes |
| The map | The selected key in the map list dump, not the localized name |
| Difficulty, funds, time limit, battle type | Lobby read-back (`expression` steps, as in the probe) |
| AI stats modifier, unit size, realism | `environment.json` (preferences), and the lobby's AI stat slider by read-back (untried; which of the two applies is still open) |
| Both rosters | The multiset of unit types in the first observation |
| Roles, unit scale | In-battle read-back: `IsDefender`, `WillWinOnTimeout`, `UnitSize` |

Unit cards are double-clicked without the current 15 s visibility wait, as the probe did.
The wait is unnecessary, and with 24 cards some sit scrolled out of the list. Map entries
in that position never read as visible; for cards this is untested. Setting the lobby
dropdowns by click is untried too, so until it is, the lobby state is a one-time manual
step that the gate checks.

The start fingerprint is reported, not enforced. It is each unit's displacement and
bearing change against the job's first episode, flagged above 1 m or 10°. The snapshot
depends on the autostart's timing, so a hard rule would discard real battles.

Rules:
- **Always pin the map.** The lobby keeps the last started map.
- **Freeze random draws before they enter a suite.** Copy the roster into explicit unit
  lists and pin each side to the race's main faction. Record any substitution where the
  lobby lists only a base card. Such a substitute can play differently: Part 3's Runelord
  `_1` → `_0` changes walk and run speed from 1.3/3.0 to 1.5/3.2.
- **Held-out means variants, not launches.** More launches of a tuned scenario are more
  development instances: "same scenario, new deployment". Generalization claims need
  variants that were never used in tuning: another map, other armies, or the sides
  swapped (untried).
- **Family measures come from declared unit keys**, never from the observation's `class`
  (2.3), and count routing and shattered units as lost, like the margin.

**Admission.** A scenario joins a suite only when:
1. **Competent beats trivial.** `skills` beats the better of `hold` and `attack_nearest`
   on the paired margin (2.11), with an instance-clustered interval that excludes zero.
   This is the brief's test.
2. **It is neither floor nor ceiling.** One of the three scripted controllers wins roughly
   30-70%. The levers are the AI stats modifier, funds and rosters.
3. **It is latency-sensitive** only if the latency check (2.5) shows degradation beyond
   noise. Every scenario reports each controller's whole latency; only a
   latency-sensitive one can show that latency changed an outcome.

A cheap screen ranks scenarios for that check: the reaction-window share. From a `hold`
trace, take the protected units and measure the time from an enemy coming within 100 m to
melee. Count the share shorter than a slow controller's information age plus decision
period, about 12.5 s for the Luna `llm`. In the probe's `hold` battle the protected units
went to melee in:
- 8.4 s, the Grudge Thrower;
- 13.2 s and 46.2 s, the two Quarrellers;
- 24.0 s, the Thunderers;
- 47.4 s, the Irondrakes.

That is a share of 1 in 5. The screen has no pass mark yet.

Families, each tied to what the interface can express:

| Family | Instance shape | What should separate controllers |
|---|---|---|
| Ranged protection | Missile-heavy army against fast flankers (Part 3) | Keeping shooters screened and firing. Reaction windows of 8-47 s in the probe's `hold` battle, one in five under 12.5 s |
| Challenge (the owner's idea in [state.md](../state.md)) | A stronger enemy that one tactic beats, such as breaking its lord, holding a choke point or kiting slow infantry | Whether the controller finds and carries out the tactic. A family measure records it. AI-generated challenges pass the same admission |
| Coordinated attack | A melee army against a defensive line with artillery | Arriving together rather than piecemeal |
| Disengagement | Needs a declared starting contact | Only if teleport arrangements work |
| Frozen draws | Admitted random draws, larger armies (owner preference) | General control. Unlikely to be latency-sensitive |

### 2.3 Observation contract `obs-v1`

`obs-v1` is the dict the mod publishes now, passed unchanged to `decide`. Label:
**structured state, enemy units filtered by the engine's visibility tests, numerically
exact. Not player-equivalent.**

| Part | Keys |
|---|---|
| Header | `schema` (1), `job`, `battle`, `seq`, `phase`, `time_ms` (battle time at publication), `remaining_ms` (game timer), `armies` (both faction keys), and `speed` and `awaiting_orders` (constants 1 and false) |
| Friendly units | `id`, `type`, `class`, `commander`, `x`, `z` (0.1 m), `bearing`, `men`, `men0`, `hp`, `state` (flags), `range`, `ammo`, `ammo0`, `speed`, `fatigue`, `width`, `behaviours` (supported toggles with their state), `abilities`. When set: `target` (the engine's current target), `dest`, `attack_mode` and `command_queue` (the last queue submitted). Each ability has `key`, `can_use`, `ready`, `active`, `recharge_s`, `uses`, `target`, `mana`, `cooldown_s` and `last_issued_ms` |
| Visible enemy units | `id`, `type`, `class`, `commander`, `x`, `z`, `bearing`, `men`, `men0`, `hp`, `state`, `range`, shown only while `is_visible_to_alliance(player)` holds and `is_hidden` does not |
| Enemy roster | Every enemy unit's `id` and `type`, as the lobby showed them, and `dead` once a unit seen earlier is destroyed |
| Magic, army | Winds of Magic pool and reserve. Army abilities with unlock points and readiness |
| Acknowledgement | `request`, `based_on`, `applied_ms`, and per order `index`, `unit`, `ok`, plus `queued` (accepted) or `error` (rejected). It appears first on the tick that applies the batch, then in every publication until the next batch replaces it |

A key whose value is nil is absent, not null.

Update timing: on the mod's tick, every 300 ms of battle time. There is a periodic
publication every 1.2 s (`observe_ms` of 1000, rounded up to the tick), and one at the tick
that applies each batch, empty batches included.

Kept out until the episode ends:
- `final`;
- the setup read-backs;
- by choice, `BalanceOfPowerPercent`.

If evaluation series are wanted later, the mod appends them to a file the harness copies
into the episode. Controllers must not read it: by review in process, or by a sandbox out
of process.

Known limits, stated in every report:
- exact numbers;
- enemy targets are not observed;
- the three leaks in Part 1;
- `class` comes from the land-unit class and the missile range, not the unit's role. The
  Gyrocopter and the Ironbreakers read `missile`, and the Spawn, Fiends and Soul Grinder
  in Part 3's enemy army read `infantry`;
- `is_hidden` is unverified;
- the full enemy roster is known from the lobby.

A reduced track (`obs-v2`: rounded positions, men as a health band) would be named
separately and never pooled with `obs-v1`.

**A visual track for vision models: `obs-v1+image`** (later; owner direction,
2026-10-14). Robotics models such as vision-language-action (VLA) models take camera
images. This track adds a screenshot to each observation a controller decides on, beside
the unchanged structured text. It is a separate track, never pooled with text-only
results. It must declare:
- **The image.** A game screenshot at a declared resolution, with the HUD shown or hidden.
  The HUD may carry the balance-of-power bar, which `obs-v1` withholds. A top-down map
  rendered from `obs-v1` would be cheaper and exactly in sync, but it is not the game's
  picture, so it would be a different track.
- **The camera.** With no human at the controls, the battle camera stays where it starts,
  and the frame shows whatever that view holds. The battle script can place the camera
  through the game's `battle_camera` API, for example in a fixed overhead view or one that
  follows the army. That rule is part of the track.
- **Timing.** Each image records when it was captured, on the wall clock and as the battle
  time of the observation it goes with. Capture, encoding and upload add to the
  controller's latency, which counts like any other (2.5). A decision's basis is the older
  of its image and its structured state.
- **What it shows.** The frame shows what the game renders for the player. Whether enemies
  out of sight are also hidden on screen is the same open check as the visibility filter
  (Part 1).
- **Capture.** It stays passive, with no desktop input (owner rule).
  - A full-desktop capture through PowerShell's `CopyFromScreen` worked on the main menu
    in the startup-skip probe (`runs/twwarhammer3/skip-intro-20261013/`). Its helper has
    since been removed (`gameai/windows_desktop.py`, last at `e4ad8e8`).
  - Starting PowerShell for each frame is unlikely to keep up with an observation every
    1.2 s (unmeasured), so the track needs a capture process that keeps running on
    Windows.
  - To check in battle: that capture works with the game fullscreen, how long a frame
    takes, and how capture lines up with the mod's tick.
- **Cost.** API vision models bill image tokens, so each call records the image size and
  its tokens.

### 2.4 Action contract `act-v1`

| Order | Fields | Targets | Persistence and replacement |
|---|---|---|---|
| `move` | `x`, `z`, optional `facing`, `width`, `run`, `queue` | A reachable point (`can_reach_position`) | Replaces the current move, attack or halt unless `queue`. `queue` appends to the engine's queue after a move in the same batch |
| `attack` | `target`, `mode` (`auto`, `melee`, `ranged`), `run`, `queue` | An enemy visible in the basis observation, still alive and visible when applied | The engine drops it when the target dies or leaves sight, and the unit idles. `mode` sets the unit's melee toggle, which persists until the next non-queued attack; queued attacks leave it alone |
| `halt` | none | none | Replaces the current order |
| `behaviour` | `behaviour`, `enabled` | Keys the unit reports as supported | Stays until changed |
| `ability` | `ability`, and a friendly or visible enemy `target`, or `x`/`z`, or nothing (self) | Owned, ready abilities | One cast |
| `ability`, unit `"army"` | `ability`, and a `target` (cast at that unit's position when applied) or `x`/`z`; no self cast | Unlocked, ready army abilities | One cast |

What the game still decides: pathfinding, formation, fighting back in melee, fire at will
and skirmish, its own retargeting during an attack, morale and spell effects. Fire at will
and skirmish are on by default where supported; in Part 3's scenario, 7 units start with
fire at will and 5 with skirmish.

Failures are never repaired by the harness:
- **Contract refusal.** A batch that fails `validate_orders` against its basis observation
  is replaced by an empty request. The trace gets an `invalid` event with the error and
  the refused orders. M1 also passes the refusal to `acknowledge()`, so the controller
  learns why.
- **Engine rejection.** The mod refuses one order and reports a code in the
  acknowledgement: `unknown_unit`, `unit_dead`, `unit_routing`, `unreachable`,
  `unknown_target`, `target_dead`, `target_not_visible`, `no_ammunition`,
  `unavailable_behaviour`, `unavailable_ability`,
  `queue_predecessor_failed_or_missing` or `deployment`. Other engine errors pass through
  as their message.
- **Counts.** Today both add to one `invalid` count. Contract refusals equal `invalid`
  minus the engine rejections in the logged acknowledgements, and the report shows them
  separately.

Never actions: session settings, the `restart` and `start` controls, menu steps (UI
clicks, keys, context expressions), and reading or writing bridge files. Advisor text
(`say`) is display only, with `--show`.

### 2.5 Timing

**`live-1x`** is the only timing policy built:
- The battle runs unpaused at 1x.
- The harness reads `observation.json` every 100 ms of wall time.
- One request is in flight at a time, and the next decision starts on the observation
  that carries its acknowledgement.
- The mod reads `orders.json` every 200 ms of wall time and applies a request at its next
  tick (300 ms of battle time). A controller that answers within milliseconds therefore
  has its orders applied 0.3 s after the state it saw, sometimes 0.6 s: that is the floor.
- While a controller thinks, units keep their last orders and the game's own behaviour.
  Observations keep being overwritten.
- A reply based on an old observation is applied as it is, with its basis recorded.

**What counts as latency.** Each controller's whole latency is part of what the benchmark
measures (owner, 2026-10-14). Real deployments pay all of it, and in some real-life
settings it decides the outcome. It has four parts:
- model inference;
- the network to and from the provider, with the provider's queueing;
- the controller's own code;
- the harness's floor of one tick.

Primary results therefore come from `live-1x` with natural latency, and the delay tracks
below are diagnostics.

The records split the latency where it can be observed:
- the battle-time age at which orders take effect (`delay_ms`);
- each model call's wall time;
- the provider's own processing time. OpenAI documents an `openai-processing-ms` response
  header, so network and queueing time is the call time minus that.

Network conditions are measured, not controlled. They vary with the time of day and the
provider's load, which makes them a source of variance between trials. Interleaving
controllers within a launch spreads that variance over all of them. The deployment
belongs on the controller's card: provider and endpoint for an API model, or the machine
and GPU for a local one. A local model can therefore be compared with a cloud model on
the latency each one really has.

**Clocks.** Information age is measured on the battle clock (`delay_ms`), which is immune
to WSL's drift. Today wall durations (think time, model latency, throughput) come from
WSL's monotonic clock, which ran slow; the system clock agreed with battle time. M1 takes
wall durations from the system clock and records each episode's ratio of battle time to
wall time.

Recorded per decision:

| Quantity | Clock | Status |
|---|---|---|
| Basis observation (`seq`, `time_ms`) | Battle | exists |
| Applied (`applied_ms`) and information age (`delay_ms`) | Battle | exists |
| Decision time (`think_s`, from reading the observation to writing the request) | Wall | exists, on WSL's monotonic clock until M1. For the commander this is the executor's milliseconds |
| Model latency per call (`attempts[].seconds`) | Wall | exists, on WSL's monotonic clock until M1. This is the think time for model and hybrid controllers |
| Provider processing time per call (`openai-processing-ms` header) | Wall | M1. Call time minus processing time is the network and queueing time |
| Plan age when adopted (`plan_age_s`, commander) | Battle | exists |
| Plan basis for each later executor order of a hybrid | Battle | later |
| Observations not decided on | Battle | per episode, the final `seq` minus the decisions |
| Battle time at which the mod read the request | Battle | later |
| Effect onset (first observation showing the order's effect) | Battle | later, as an estimate. The interval is (previous observation, this one], up to 1.2 s wide for a blocking controller and 0.3 s for one deciding every tick, and the observation on the application tick cannot show the effect |

**The latency check** (gate experiment G2) measures what information age costs on a
scenario. That shows whether the scenario can reveal latency differences between
controllers; latency counts in the results either way. The delay line is built with M1
in `play._drive` and needs no mod change. It hands the policy the newest buffered observation
that is at least D old, and sends it as `based_on`, so `delay_ms` stays correct. A fast
controller keeps its 0.3 s decision period, so only the information age changes. Each
episode records its D.

Levels:
- D = 0, the natural 0.3 s;
- 6 s, the `llm`'s median;
- 10 s, about its 90th percentile.

`skills` plays each level once per launch, in random order, on about 6 instances (18
battles, about 2 hours). A scenario is latency-sensitive only if the per-instance paired
margin (D = 6 or 10 s against D = 0) degrades, with an instance-level interval that
excludes zero. A null result rules out only effects above G2's minimum detectable
difference, which its report states. These trials carry their D and are never pooled
with `live-1x`.

Later tracks are diagnostics. They separate reasoning from speed and never replace or pool
with the end-to-end `live-1x` results:
- **`age-D/P`**: apply each batch at its basis time plus D, with decision period P.
  - The name carries both axes, because with one request in flight a fixed age also fixes
    the period.
  - Equal-tempo comparisons need D above the slowest controller's 95th percentile, about
    10-12 s for Luna at low effort; trials with more than 5% overruns are flagged.
  - D is a multiple of 300 ms.
  - A declared, seeded application jitter of 0-3 ticks makes trials independent across
    seeds and reproducible within one.
- **`live-1x+D`** for any controller: add D to the natural delay, the delay line's
  mechanism. A run with D = 0 is not a zero-latency run.

### 2.6 Controllers

The in-process protocol stays as it is: `decide(observation) -> orders`,
`acknowledge(ack, latency)`, `metadata()`, an optional `close()`, and `totals` for API
calls, tokens and USD.

**Plug-in (M1).** `--policy package.module:Class` loads an outside controller, which must
be importable in the project's environment. The manifest records the module file's
sha256, and its git revision when it lives in a repository. Each episode gets a new
controller object.

Rules for every controller, stated on the "run it yourself" page:
1. **No state carried between episodes.** Rematches restart the same start, so carried
   state could memorize the AI's deployment.
2. **Asynchronous plans report their age.** A controller that plans asynchronously reports
   in `metadata()` each plan's age when it adopts it, as the commander does with
   `plan_age_s`. The basis behind every later batch comes later (2.5). Without that, its
   plan age is reported as unknown.
3. **Costs may be self-reported.** Costs and tokens are self-reported unless the model is
   called through `gameai.llm.Model` on the WH3 ledger.
4. **Results are auditable.** They are self-reported by whoever runs them, and auditable
   from the traces.

**Disclosure.** A `card` dict is recorded for each episode: kind, automation, memory,
model, timing and deployment. Deployment means the provider and endpoint for an API
model, or the machine and GPU for a local one. The built-in controllers' cards:

| Controller | Kind | Automation and memory | Timing |
|---|---|---|---|
| `hold` | scripted | No orders. Units stay under script unit controllers with the game's default toggles | none |
| `attack_nearest` | scripted | Each unit attacks its nearest visible enemy, walking. Re-sent when the nearest changes, when the order lapses or after a rejection | every observation |
| `skills` | scripted | The skills executor with class defaults ([controllers.md](controllers.md)) | every observation |
| `llm` | model | The `system_prompt.md` rules. Notes, its last 8 decisions with reasons, the engine's verdicts on its last batch, per-unit changes since its previous decision, its own orders vs the game's choices, last-seen enemies, the measured delay. Up to 2 re-asks on invalid replies, each a new call with the error appended. Up to 3 attempts per call on transient errors, 60 s timeout each | blocking |
| `commander` | hybrid | A model setting skills (`commander_prompt.md`) over the executor. Notes, last plans, last-seen enemies. 1 re-ask on unparseable replies. Clears invalid targets, drops invalid assignments and reports drops and rejections to the model. The same transport retries | asynchronous |

**Powers.** In-process controllers and child processes alike run as the same user and can
reach the bridge directory, so harness powers are out of reach only in a sandbox (another
user, or a container without `/mnt/c`). Until then this holds by review. An
out-of-process adapter (`exec:`, JSON lines over stdin and stdout) waits until someone has
a controller not written in Python.

**Robotics models** (later; owner direction, 2026-10-14). VLAs and other robot policies
are planned as controllers. They need:
- the visual track (2.3);
- an adapter from their action output (continuous end-effector actions or action tokens)
  to `act-v1` orders. The card discloses it as part of the controller, like any tactical
  helper;
- their hardware on the card. They usually run on a local GPU, so their latency has no
  network part, a real contrast with API models.

They are trained on robot camera views and arm actions, not battles, so a first test
measures transfer, and any fine-tuning becomes part of the controller. The timing tracks
suit them: acting on delayed observations while the next action chunk is computed is
the same problem as in robotics (real-time chunking, [controllers.md](controllers.md)).

### 2.7 Episode lifecycle

1. **Launch**: prepare the runtime (pinned build, mod pack, startup skip) under the runtime
   lock, one game at a time.
2. **Setup**: the frontend steps, then the setup gate (2.2).
3. **Start**: the harness ends deployment at 4.7 s; the controller cannot deploy. The
   first observation, at 5.2 s, is checked against the roster, and its fingerprint is
   reported.
4. **Play** until one of:
   - the engine's result;
   - the game timer: the benchmark sets the wall cap above it, and the report labels a
     result at `remaining_ms` 0 as `time_limit`;
   - a failure.
5. **Record** every started episode, including interrupted ones.
6. **Reset** by rematch, which keeps the instance. The battle reloads about 17 s after the
   restart request, and the next trial starts about 21 s after it (28 s in the probe).
   - Until the undecided restart is verified, any undecided ending (a controller failure,
     a wall-clock truncation, an imposed limit) ends the launch and the job.
   - M1 therefore removes `policy_failure` and `truncated` from `SCORED`, the set of
     statuses after which today's loop sends `restart` and plays the next episode.
   - Controllers not yet played on that instance get no trial there. The paired analysis
     uses only trials that share an instance, and the report lists incomplete instances.
7. **Next instance**: a new launch. It takes about 95 s with Autogenerate, 112 s for the
   10-unit `kho5-dwf5`, and about 160 s for a 24-card scenario.

The supported setup, all required:
- Windows with WSL2, and Windows Python 3.13 at `C:/Python313/python.exe`;
- Steam running and logged in;
- WH3 at the pinned build. Results belong to one build: after a patch, bump the pin, rerun
  the setup gate and the free scripted baselines, and never pool across builds;
- the content the scenario uses: its races, units and map;
- the default Steam library on `C:` and the runtime folder `C:/wh3-agent`. Both paths are
  hard-coded today and should become documented overrides;
- the profile's lobby state and preferences as the scenario declares them (one-time
  manual steps that the gate checks);
- a dedicated desktop, because the game runs fullscreen;
- no other game controller.

The harness leaves three changes in the install:
- a mod list file in the game folder, used only by harness launches;
- a startup movie pack in `data/`;
- one preference, the intro video.

The last two also apply to ordinary launches. Starting, resetting and stopping runs are
unattended.

### 2.8 Outcomes and failures

| Status | Today's status | Meaning | Valid trial |
|---|---|---|---|
| `won`, `lost`, `draw` | same | Engine result | yes |
| `time_limit` | `won` or `lost` | The game timer ran out. The engine's winner is recorded but never reported as a win | yes |
| `controller_failure` | `policy_failure`, plus controller exceptions now filed as `infrastructure_failure` | The controller raised, exhausted its re-asks, or exceeded its declared budget | no; counted in the reliability rate |
| `infrastructure_failure` | `infrastructure_failure`, `unsupported_or_invalid`, `truncated` | Bridge or mailbox timeout, game crash, unexpected restart, a game-side protocol error, a stall | no; reported |
| `interrupted` | `interrupted`, `budget_exhausted` (the ledger cap) | Operator stop or the API cap | no; reported |

M1 files controller exceptions, and provider errors after the transport retries, as
`policy_failure`, which the report shows as `controller_failure`.

Every rate has its denominator:
- **valid-trial performance**: outcomes over valid trials;
- **objective rate**: wins over valid trials plus controller failures;
- **reliability**: valid trials over started trials, with failures by class.

A trial lost to infrastructure is replayed by a new launch of the whole list, which is a
new instance, and the report lists every attempt.

### 2.9 Measures

Primary: outcome counts per scenario, controller and track, with Wilson intervals and the
list of trials. No composite score.

| Measure | Definition |
|---|---|
| Margin | Own minus enemy men alive over starting men, from `final`. Today routing men count as alive, and the sign is opposite to the outcome in 16 of 108 battles (Part 1). M1 adds a second total for both sides that counts routing and shattered units as lost, and publishes `final` at every ending. The second total is the margin used by admission (2.2), the paired test (2.11), G1 and G2. Weighting by unit value needs unit costs (later) |
| Family measure | From the declared `protected` keys, in the friendly records of the last observation, with routing and shattered units counted as lost |
| Information age | Per batch that carries orders (`delay_ms`; every order in a batch has the same age), on the battle clock: 50th and 90th percentiles. For hybrids also the plan age |
| Model latency | Per call, in wall seconds from the system clock (M1), split into the provider's processing time and the rest (network and queueing) |
| Decision rate | Decisions with orders per battle minute; observations not decided on, per episode |
| Rejections | Contract refusals per decision; engine rejections per 100 orders, by code |
| Model use | Calls, input, cached, output and reasoning tokens, and USD per battle |
| Throughput | Wall seconds per episode (setup, battle, reset) and episodes per hour |

Reporting rules:
- count effective samples: instances for deterministic controllers;
- give an instance-level bootstrap interval for margins;
- state the design's minimum detectable difference;
- mark a cell exploratory when its interval is wider than the declared minimum effect.

### 2.10 Records

What M1 adds to today's manifest, trace, `result.json` and register:
- every started episode registered, interrupted ones included;
- per episode: the policy, its slot in the launch, its `card` and the delay D; for an
  outside controller, its source hash and git revision;
- the refusal reason passed to the controller;
- the model id each response returns, and the provider's processing time per call;
- the setup gate's read-backs in the manifest;
- both sides' unit-card lists from the lobby;
- the second strength total in `final`;
- each episode's ratio of battle time to wall time.

The register stays rebuildable from `runs/`.

### 2.11 Comparison protocol

- **The unit of analysis is the instance.** Play one trial per controller per launch, in an
  order randomized per launch.
- **Repeats are correlated.** Repeats of a deterministic controller on one instance
  measure sensitivity to timing jitter, not skill. Of six `skills` episodes, three were
  identical, and the others diverged after small differences in when their orders landed.
- **Declare before running:**
  - two or three planned contrasts:
    - `skills` vs `attack_nearest`: is the executor useful?
    - `commander` vs `skills`: does the model add value?
    - `llm` vs `commander`: does the architecture matter?
  - the minimum effect of interest;
  - the test: the paired margin difference over instances, by t or bootstrap, with
    failures ranked worst;
  - a Holm correction.

  Claim a difference only when the margin and the win counts agree.
- **Size from the declared effect.** Estimates from the register, made with today's margin;
  recompute them on the second total from G1's runs before sizing any comparison:
  - a 20-point win-rate difference is about 0.12-0.14 of margin;
  - paired over instances, that needs about 17-28 instances per contrast, or 36 with Holm
    over three;
  - 36 instances times 4 controllers (`attack_nearest`, `skills`, `commander`, `llm`) is
    144 battles: about 15-18 hours, and about $1.90 with Luna;
  - using wins alone it needs about 97 battles per controller.
- **Stop sequentially.** Take four looks, about every 9 of 36 instances, with
  O'Brien-Fleming bounds and a futility stop. Expected size is 0.5-0.8 of the fixed
  design, about 8-14 hours.
- **Development loop.** Play the candidate against the incumbent in the same launches,
  screening at one-sided 0.10 and capped at 15-20 instances. Confirm on held-out
  variants. Three episodes per version, as the autoresearch loop used, cannot tell
  versions apart: identical v6 code scored -0.17 and +0.17 in two launches.
- **Budgets.** Each controller should get its own USD cap. That is not built: today every
  model controller draws on the WH3 ledger's single cap, and running out is
  `budget_exhausted`. An Astra commander costs about $1.17 a battle, so the ledger's
  remaining $22.56 covers about 19 Astra battles.

### 2.12 What reproducibility means here

Promised:
- the same declared scenario and settings, checked by the gate in every job;
- the same start for every controller within a launch, with the fingerprint reported. One
  of the 65 recorded rematches differed by more than 10° (a lord turned 12°);
- records that recompute every measure.

Not promised:
- identical trajectories under `live-1x`;
- identical instances across launches;
- replay of a whole job.

The game's own replay files are not used.

### 2.13 The path to reinforcement learning

The records keep every decision that carried orders, with its basis observation, its
acknowledgement and battle times, and a status that separates engine results from
failures. They do not keep the observations between decisions: a trace stores 8-50% of
those published (51 of about 281 for the `llm` on seed 322117462). A training adapter can
define transitions as (basis observation, orders, next basis observation), with the
elapsed battle time attached. At about 8 battles an hour on one machine, throughput, not
the interface, is what limits reinforcement learning here.

### 2.14 Plan

**M1, about 250 lines plus mocked tests:**
1. A Part 3 entry in `scenarios.json`, with `expect`, `protected` and `content`.
2. The setup gate (2.2), with card double-clicks without visibility waits.
3. `--policy a,b,c` plays each listed controller once per launch, in an order shuffled from
   a recorded seed. `--episodes` defaults to the number of names; a larger value repeats
   the list (correlated repeats, 2.11). Names or `package.module:Class`.
4. Record fixes:
   - the refusal reason to `acknowledge()`;
   - `response.model` and the `openai-processing-ms` header per call;
   - register every started episode;
   - a wall cap above the game timer;
   - wall times from the system clock, and each episode's clock ratio;
   - the second strength total in `final`, and `final` published at every ending;
   - controller exceptions, and provider errors after retries, filed as `policy_failure`;
   - `SCORED` without `policy_failure` and `truncated`;
   - per episode, the policy, its slot, its `card` and G2's delay D.
5. The G2 delay line (2.5).
6. The report, `stats --report JOB...`. Per scenario, controller and track:
   - instances and trials, and the list of trials;
   - outcomes with Wilson intervals, with a result at `remaining_ms` 0 labelled
     `time_limit`;
   - failures by class (2.8);
   - paired margin differences per instance, with an instance-level interval and the
     design's minimum detectable difference;
   - the family measure;
   - information age per batch with orders, and plan age for hybrids;
   - decision rate;
   - model latency;
   - rejections split;
   - tokens, USD and wall time.

   It ends with a fixed limitations footer: the observation label and its known limits
   (2.3), "issued, not took effect", the 0.3 s floor, the AI settings, the build,
   self-reported costs and the sample sizes.
7. A "run it yourself" page: the supported setup, the one-time manual steps, the
   controller rules and how to read the report.

M1 is done when:
- mocked tests pass for the gate, the rotation and the report's arithmetic;
- one unattended job (about 35 minutes, one `llm` battle) runs `hold`, `attack_nearest`,
  `skills`, `llm` and an outside `module:Class` controller on one instance of Part 3's
  scenario, and the report comes from `runs/`;
- a deliberately broken setup, such as a misspelt unit key, is refused before any battle
  is scored.

**Gate experiments**, no API cost, about 4-6 hours of game time together:
- **G1, calibration.** `hold`, `attack_nearest` and `skills`, once each per launch in
  random order, on about 6 instances of Part 3's scenario: about 2 hours per setting.
  - At 3 instances the paired interval would exclude zero only for a gap of about 0.4
    margin; at 6, for about 0.2.
  - Run it at the AI stats modifier 1.1, and at 1.0 if the owner agrees. The 1.0 arm uses
    a second scenario entry whose `expect` declares 1.0, with both the preference and the
    lobby's slider set by hand, since which one applies is open.
  - Does one of the three win 30-70%, and does `skills` beat the better of `hold` and
    `attack_nearest` on the paired margin?
- **G2, latency sensitivity.** As in 2.5: `skills` at D = 0, 6 and 10 s on about 6
  instances, about 2 hours. Does the paired margin degrade?

**Later, only if a result calls for it:**

| Item | Trigger |
|---|---|
| `age-D/P`, and `live-1x+D` for controllers other than G2's `skills` | G2 shows sensitivity, and controllers of different speeds need equal-tempo comparisons |
| Teleport starting arrangements | A family needs declared contact (disengagement) |
| An imposed battle-time limit | Battles run too long for the throughput budget, after the undecided restart is verified |
| A value-weighted margin and evaluation series | The two-total margin still disagrees with outcomes |
| Per-controller USD caps | A comparison with a costly model |
| The visual track (`obs-v1+image`) and robotics controllers (VLAs) | Owner direction (2026-10-14), after M1. Needs a candidate model, its action adapter, and frame capture checked in battle |
| The `exec:` adapter | A controller not written in Python |
| `obs-v2` | Player equivalence becomes a goal |
| A suite of families with held-out variants | One scenario passes admission |
| Model against model, possibly in teams | Owner idea (2026-10-14), some day; see below |

**Model against model, possibly in teams** (owner idea, 2026-10-14, for some day). Models
would fight each other instead of the game AI, perhaps several to a side. There are two
routes; both are untried:
1. **One game client.** The battle script takes control of the enemy army too, with the
   same unit controllers it uses for ours, and serves each side its own observation
   (`is_visible_to_alliance` for that side) and orders.
   - The custom battle screen can add armies to a side (`button_add_ai`), which gives
     teams, for example 2v2 with one model per army.
   - To check: that the game AI lets go of units the script takes, and what teammates may
     tell each other.
2. **Real multiplayer, hosted locally.** Each side runs its own game client with the mod,
   which needs separate Steam accounts and copies of the game.
   - The mod stays inert in multiplayer today (its `is_multiplayer` check).
   - The game's scripting notes warn that script actions that differ between clients
     cause desyncs, so orders fed in from outside on one client may break the battle.
   - This route is riskier, so try route 1 first.

Either way, both sides' latency counts. Results become relative to the opponents faced
(pairings, ratings) rather than win rates against one fixed AI.

## Part 3. A concrete scenario: `dwf-sla-taurox`

### The scenario

A Dwarf army that is half shooters faces a Slaanesh army of fast melee: chariots,
Hellstriders, Fiends and a Soul Grinder. It belongs to the ranged protection family.

The armies are frozen from random draw 322117462, which was played in three separate
launches on 2026-10-13 (three instances). Its Autogenerate gave the same 12-unit rosters
each time, all with the `_1` Runelord. One of the three launches had other factions:
Karak Kadrin against the Masque of Slaanesh. On those launches:
- `skills` lost at 382 s with 0.31 of its men alive, all of them routing, against 0.30;
- the Luna commander lost, 0.43 vs 0.58;
- the Luna `llm` lost, 0.46 vs 0.60.

With `hold`'s loss on the frozen version (below), every controller tried so far has lost.
Whether this scenario separates controllers is open until G1.

```json
"dwf-sla-taurox": {
  "map": "battle_preset_qb_wh2_dlc17_taurox_rune_tortured_axes",
  "expect": {"battle_type": "land_normal", "difficulty": "ai_level_very_hard",
             "funds": "funds_large", "time_limit_s": 3600, "unit_scale": 0.75,
             "realism": false, "ai_stats_modifier": "1.1", "player_defends": true},
  "player": {"subculture": "wh_main_sc_dwf_dwarfs", "faction": "wh_main_dwf_dwarfs",
             "units": ["wh_dlc06_dwf_cha_runelord_0", "wh_main_dwf_inf_longbeards",
                       "wh_main_dwf_inf_longbeards_1", "wh_main_dwf_inf_hammerers",
                       "wh_main_dwf_inf_ironbreakers", "wh3_dlc25_dwf_inf_doomseekers_ror",
                       "wh_main_dwf_inf_quarrellers_0", "wh_main_dwf_inf_quarrellers_1",
                       "wh_main_dwf_inf_irondrakes_0", "wh3_dlc25_dwf_inf_thunderers_ror",
                       "wh_main_dwf_veh_gyrocopter_1", "wh_main_dwf_art_grudge_thrower"]},
  "enemy": {"subculture": "wh3_main_sc_sla_slaanesh", "faction": "wh3_main_sla_slaanesh",
            "units": ["wh_dlc01_chs_cha_prince_sigvald_the_magnificent",
                      "wh3_main_sla_inf_marauders_1", "wh3_main_sla_inf_daemonette_0",
                      "wh3_dlc20_chs_inf_chaos_warriors_msla",
                      "wh3_dlc20_chs_inf_chaos_warriors_msla",
                      "wh3_dlc20_chs_inf_forsaken_msla", "wh3_main_sla_cav_hellstriders_1",
                      "wh3_main_sla_veh_seeker_chariot_0",
                      "wh3_dlc20_chs_cav_chaos_chariot_msla_ror",
                      "wh3_main_sla_mon_spawn_of_slaanesh_0",
                      "wh3_main_sla_mon_fiends_of_slaanesh_0",
                      "wh3_main_sla_mon_soul_grinder_0"]},
  "protected": ["wh_main_dwf_inf_quarrellers_0", "wh_main_dwf_inf_quarrellers_1",
                "wh_main_dwf_inf_irondrakes_0", "wh3_dlc25_dwf_inf_thunderers_ror",
                "wh_main_dwf_art_grudge_thrower"],
  "content": ["wh_dlc01", "wh_dlc06", "wh2_dlc17", "wh3_dlc20", "wh3_dlc25"]
}
```

Notes on the scenario:
- **The Runelord is a substitute.** The draw had `wh_dlc06_dwf_cha_runelord_1`, which has
  no card of its own (only `_0` is listed). It differs in battle: walk and run speed 1.3/3.0
  against 1.5/3.2, and footprint width 2.7 m against 1.2 m, with the same rune abilities.
  The earlier results on this draw were played with `_1`.
- **The map** reads in the lobby as "Dread Crossing – Quest Battle".
- **Settings** as read back: very hard, large funds and a 3600 s timer in the lobby; unit
  scale 0.75 and realism off in battle. The player defends and wins on timeout. The AI
  stats modifier is 1.1 in the profile's preferences; it was not read back.
- **Track**: `obs-v1/act-v1/live-1x`.

### Trials on this scenario

- **Controllers.** The five built-in ones with their cards (2.6), plus any controller
  loaded by import path.
- **One launch is one instance.** It plays each listed controller once, in a random order:
  about 25 minutes for the four controllers of 2.11's contrasts, and about 6 minutes more
  for each one added, such as `hold` or an outside controller.
- **G1** needs about 6 launches of `hold`, `attack_nearest` and `skills` per setting.
- **A reported comparison** is sized from its declared effect (2.11). For a 20-point
  difference that means up to 36 launches and 15-18 hours, about 8-14 on average with
  sequential stopping.
- **Held-out results** come from variants: the same armies on another map, or other armies
  against the same flankers. More launches of this scenario are not held out.
- **Each trial records:**
  - the setup gate's checks;
  - every logged observation and decision, with its basis and timing;
  - every acknowledgement with its rejections;
  - the status;
  - both strength totals at the end;
  - the protected units' share of men left;
  - model calls, tokens and cost.
- **The report** has one row per controller (2.9), plus a table of paired differences per
  instance, and ends with the limitations footer.

With M1 in place, another developer runs one launch, which is one instance, per command,
with a new output directory each time, then reports over all of them:

```bash
uv run python -m twwarhammer3 play --scenario dwf-sla-taurox \
    --policy hold,attack_nearest,skills,mypackage.controller:MyController \
    --output runs/twwarhammer3/battle/bench-dwf-sla-taurox-01   # -02, -03, ... one per instance
uv run python -m twwarhammer3 stats --report runs/twwarhammer3/battle/bench-dwf-sla-taurox-*
```

`mypackage` must be importable in the project's environment. Add `--budget-usd` when the
list includes `llm` or `commander`.

### What the setup probe showed

The probe was a hand-written driver, `bench_probe.py`, copied into
`runs/twwarhammer3/benchmark-probe-20261014/`. It ran from a clean worktree at
`f2c8463` and reused `play.scenario_steps`, `start_frontend` and `play_episode`. In one
launch it:
- built this scenario unattended;
- selected the map and read it back;
- pinned both factions;
- recruited all 24 cards;
- matched the declared roster on both sides.

The read-backs in Part 1 come from it.

Two battles ran before the owner stopped the probe, so the benchmark itself was not run:
- **`hold`** lost at 298 s, with 0.41 of its men alive against 0.65.
  - Its five protected units kept 0.55 of their men (123 of 225), counting routing men as
    alive. All five were routing at the end, so with routing units counted as lost the
    family measure is 0.
  - Its 965 empty requests were applied 0.3 s after the state they answered (954 at
    300 ms, 11 at 600 ms), for a controller that answers in 3 ms. That is `live-1x`'s
    floor: one tick.
  - With no orders, its Thunderers still fired, ammunition falling from 1320 to 1213: the
    game's own behaviour at work.
- **`attack_nearest`**, on the first rematch, started from exactly the same positions. The
  owner stopped it at 262 s, so it left a partial trace and no result.

Two battles show that the setup and the records work. One finished battle says little
about the scenario's difficulty. Together with the three earlier losses on the draw, it
points toward the floor, which G1 tests.

## Part 4. Does the idea make sense?

The reviewers agree on what is sound:
- pairing controllers on one instance inside a launch;
- measuring information age on the battle clock;
- the engine's own outcomes;
- keeping evaluation data out of observations;
- the honest labels (not player-equivalent; "issued, not took effect").

What would make the benchmark misleading, and what to do about each:

1. **Latency counts, but no scenario has yet shown it matters.**
   - By the owner's direction, each controller's whole latency, network included, is part
     of its result, as it would be in a real deployment. A slow controller that loses
     because it is slow has lost.
   - Under `live-1x`, each controller's latency is fixed by its design and deployment.
     Latency therefore moves together with the controller's identity, automation and
     decision rate. Why one controller beat another is then not separable from speed.
     G2 and the diagnostic tracks (2.5) separate the two.
   - The one manipulation, `llm` v4 live against paused, cut the age from 5.5 s to 0.6 s
     and found no difference: mean margins -0.17 and -0.16, 1 of 3 won each. With 3
     battles per arm it could only have detected effects of about 0.5-0.7 margin.
   - The game's own unit behaviour (fire at will, skirmish, melee responses) may absorb
     much of the reactive load: under `hold`, with no orders, the Thunderers still fired.
     How much it absorbs is unmeasured.
   - The ranged protection scenario has at least one short window. Under `hold`, the
     Grudge Thrower was in melee 8.4 s after a flanker came within 100 m, less than the
     `llm`'s 6 s age plus about 6.5 s period. The next shortest, 13.2 s, is just over that.

   G2 can show sensitivity if the effect is large. A null result rules out only effects
   above its minimum detectable difference. Below that, the scenario still measures
   controllers end to end, latency included. It just cannot show that a controller won or
   lost because of its speed. Scenarios with short reaction windows are the ones to look
   at for that.
2. **No scenario so far separates competent from trivial play.** Wins by scenario:
   - `kho5-dwf5`: the trivial `attack_nearest` won 4 of 5, as often as `skills` (5 of 7)
     and the commander (8 of 9), while the `llm` won 17 of 33;
   - the mirrors: lost by nearly every controller (`llm` 0 of 11 and 0 of 12 in the
     mirrors with guns, 3 of 19 in the Khorne mirror);
   - the random draws: lost by every controller in the paired comparison (9 of 9);
   - Part 3's draw: lost in all three earlier launches, and by `hold` in the one finished
     battle on its frozen version.

   The AI at very hard with a 1.1 stats modifier pushes battles toward the floor, and the
   modifier is the main lever (decision 2 below). But it cannot fix `kho5-dwf5`'s problem,
   which is trivial play matching competent play. G1 tests both.
3. **The margin needs fixing before it carries conclusions.** It counts routing men as
   alive and ignores unit value: Sigvald and the Soul Grinder are 1 man each out of 458.
   It is also missing when a trial ends without an engine result. M1's second total,
   published at every ending, fixes the first and the last of these.
4. **Statistics and cost.** Machine hours bind, not dollars:
   - about 8 battles an hour on one machine;
   - a credible 20-point comparison takes up to 15-18 hours per scenario with paired
     margins, about 8-14 on average with sequential stopping;
   - Luna costs about $0.02-0.04 a battle;
   - an Astra commander would use the WH3 ledger's remaining cap in about 19 battles.

   Small results stay exploratory, with their intervals shown.
5. **An independent user needs:**
   - the game at the pinned build, and every patch blocks runs until the pin moves;
   - the scenario's DLC content;
   - Windows with WSL2, Windows Python 3.13 at `C:/Python313`, and Steam running and
     logged in;
   - the Steam library on `C:` and the runtime folder `C:/wh3-agent`, both hard-coded
     today;
   - the lobby state and preferences the scenario declares, set by hand once (the gate
     checks them);
   - a dedicated desktop and no other game controller.

   They compare controllers within their own launches, against scripted baselines they
   run for free. The owner's numbers are context, not a leaderboard.
6. **Scope.** Named tracks as files, a card schema, an `exec:` adapter, delay tracks for
   every controller and suites all wait until a result needs them (2.14). M1 plus G1 and
   G2 is the smallest path that answers the acceptance question honestly.

Decisions for the owner:
1. **Go or no go.** Build M1 (about 250 lines plus mocked tests, including G2's delay
   line), check it with one acceptance job (about 35 minutes, one `llm` battle), then run
   G1 and G2 (about 4-6 hours of game time, no API cost)? If G1 finds no controller at
   30-70%, or `skills` no better than trivial play, the next step is recalibrating the
   scenario, not the rest of 2.14.
2. **The AI stats modifier.** Keep 1.1, or calibrate at 1.0? The README's "about 10%
   stronger" was never measured, and the lobby slider's value was never read.
3. **Roles.** The player defends and can wait while the AI must come to it; the passive
   `hold` was reached and beaten at 298 s. Keep that, or swap sides so the player must
   attack? Swapping is untried: the lobby's `button_swap_attacker_defender` was found but
   never clicked.
4. **Families.** Ranged protection and the owner's challenge battles first, with frozen
   draws as a general-control family?
5. **Model spend.** Luna only for now, or a budget for Sol or Astra commanders?
6. **Held-out variants.** Which maps and armies to lock away before any tuning?
7. **Robotics models, when their turn comes.** Which VLA or robot policy to try first, and
   should its picture be a game screenshot or a map rendered from the state (2.3)?

Settled on 2026-10-14: each controller's whole latency, network included, is part of what
the benchmark measures.
